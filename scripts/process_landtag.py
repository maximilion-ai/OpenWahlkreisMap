"""
Generic Landtag processor — config-driven PLZ-to-Wahlkreis mapping.

Supports two processing methods:
  - spatial: Polygon intersection with official Wahlkreis geometries
  - municipality_join: PLZ→AGS→Wahlkreis via VG250 municipality boundaries,
    for states that publish no Wahlkreis geometry

Usage:
  python3 scripts/process_landtag.py --build-plz-ags [--force]
  python3 scripts/process_landtag.py --state berlin
  python3 scripts/process_landtag.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

from lib.errors import DataPipelineError, SourceDataError, ValidationError
from lib.geo import (
    compute_intersections,
    determine_primary,
    filter_plz_by_bbox,
    load_constituency_polygons,
    load_plz_polygons,
)
from lib.municipality import (
    build_plz_ags_mapping,
    join_plz_to_wahlkreis,
    load_plz_ags_mapping,
)
from lib.output import write_csv, write_json
from lib.parsers import get_parser, validate_parser_output

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

RAW_PLZ_PATH = PROJECT_DIR / "raw" / "plz" / "plz-5stellig.geojson"
VG250_GEM_PATH = PROJECT_DIR / "raw" / "municipality" / "VG250_GEM.shp"
PLZ_AGS_CACHE = PROJECT_DIR / "raw" / "municipality" / "plz-ags-mapping.parquet"
CONFIGS_DIR = PROJECT_DIR / "configs" / "landtag"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Cache PLZ GeoDataFrame across multiple state runs
_plz_gdf_cache = None


def get_plz_gdf():
    """Load PLZ GeoDataFrame (cached for multi-state runs)."""
    global _plz_gdf_cache
    if _plz_gdf_cache is None:
        _plz_gdf_cache = load_plz_polygons(RAW_PLZ_PATH)
    return _plz_gdf_cache


# ---------------------------------------------------------------------------
# Processing methods
# ---------------------------------------------------------------------------

def process_spatial(config: dict) -> dict:
    """Process a state using spatial intersection (Tier 1)."""
    raw_dir = PROJECT_DIR / "raw" / "landtag" / config["download"]["raw_subdir"]
    source_file = config["download"].get("source_file")
    wk_source = raw_dir / source_file if source_file else raw_dir

    # Load constituency polygons
    col_map = config.get("columns")
    # Convert null values to None for auto-detection
    if col_map and all(v is None for v in col_map.values()):
        col_map = None

    names = config.get("names")
    if isinstance(names, str):
        names_df = pd.read_csv(PROJECT_DIR / names, dtype={"wk_nr": int, "wk_name": str})
        names = dict(zip(names_df["wk_nr"], names_df["wk_name"]))

    wk_gdf = load_constituency_polygons(
        wk_source,
        fmt=config["download"].get("format", "shapefile"),
        col_map=col_map,
        names=names,
        wk_nr_pattern=config.get("wk_nr_pattern"),
        expected_count=config["expected_wk_count"],
    )

    # Filter PLZ to state bounding box
    plz_gdf = get_plz_gdf()
    state_plz = filter_plz_by_bbox(plz_gdf, wk_gdf)

    # Compute intersections
    intersections = compute_intersections(state_plz, wk_gdf, rescue_slivers=False)

    # Build mapping
    mapping = determine_primary(intersections, config["period_id"])
    return mapping


def process_municipality_join(config: dict) -> dict:
    """Process a state using municipality join (Tier 2)."""
    state = config["state"]

    # Load PLZ-AGS mapping
    if not PLZ_AGS_CACHE.exists():
        raise RuntimeError("PLZ-AGS mapping not found. Run: make process-landtag-plz-ags")
    plz_ags_df = load_plz_ags_mapping(PLZ_AGS_CACHE)

    # Parse state's constituency-municipality data
    parser_name = config["parser"]
    parser = get_parser(config)
    if parser_name == "landkreis_prefix":
        ags_wk_lookup = parser(None, config)
    else:
        raw_dir = PROJECT_DIR / "raw" / "landtag" / config["download"]["raw_subdir"]
        source_file = config["download"].get("source_file")
        patterns = {"excel": ["*.xlsx", "*.xls"], "csv": ["*.csv"]}[config["download"].get("format", "excel")]
        files = [raw_dir / source_file] if source_file else sorted(f for pat in patterns for f in raw_dir.glob(pat))
        if not files:
            raise FileNotFoundError(f"No {patterns} source file found in {raw_dir}")
        ags_wk_lookup = parser(files[0], config)

    ags_wk_lookup = validate_parser_output(
        ags_wk_lookup,
        parser_name=f"process_municipality_join:{parser_name}",
        allow_multi_wk_per_ags=bool(config.get("allow_multi_wk_per_ags", True)),
    )

    # A municipality missing from the lookup would silently hand its PLZ shares
    # to the neighbouring municipalities, so require every one of the state's.
    state_ags = set(ags_wk_lookup["ags"])
    land_codes = {ags[:2] for ags in state_ags}
    unassigned = sorted(set(plz_ags_df.loc[plz_ags_df["ags"].str[:2].isin(land_codes), "ags"]) - state_ags)
    if unassigned:
        raise ValidationError(f"{state}: {len(unassigned)} municipalities have no Wahlkreis, e.g. {unassigned[:5]}")

    # Filter PLZ-AGS to this state's AGS codes
    state_plz_ags = plz_ags_df[plz_ags_df["ags"].isin(state_ags)].copy()

    if len(state_plz_ags) == 0:
        raise RuntimeError(f"No PLZ-AGS matches for state {state} — check AGS format")

    # Join PLZ → AGS → Wahlkreis
    mapping = join_plz_to_wahlkreis(state_plz_ags, ags_wk_lookup, config["period_id"])
    return mapping


# ---------------------------------------------------------------------------
# State processing orchestration
# ---------------------------------------------------------------------------

def load_config(state_slug: str) -> dict:
    """Load YAML config for a state."""
    config_path = CONFIGS_DIR / f"{state_slug}.yaml"
    if not config_path.exists():
        available = [p.stem for p in CONFIGS_DIR.glob("*.yaml")]
        raise SourceDataError(f"Config not found: {config_path}. Available configs: {available}")

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def process_state(state_slug: str) -> bool:
    """Process a single state. Returns True on success."""
    config = load_config(state_slug)
    state = config["state"]
    method = config["method"]

    log.info("")
    log.info("=" * 60)
    log.info("Processing %s (%s, method=%s, %d WK expected)",
             config["state_name"], config.get("parliament", "Landtag"),
             method, config["expected_wk_count"])
    log.info("=" * 60)

    t0 = time.time()

    # Dispatch by method
    if method == "spatial":
        mapping = process_spatial(config)
    elif method == "municipality_join":
        mapping = process_municipality_join(config)
    else:
        log.error("Unknown method: %s", method)
        return False

    mapping_checksum = config.get("mapping_checksum_sha256")
    if mapping_checksum:
        actual_checksum = hashlib.sha256(
            json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if actual_checksum != mapping_checksum:
            raise ValidationError(
                f"Mapping checksum mismatch for {state}: expected {mapping_checksum}, got {actual_checksum}"
            )
        log.info("Mapping checksum OK")

    # Write output
    output_dir = PROJECT_DIR / "data" / "landtag" / state
    meta = {
        "election": config["election"],
        "constituencies": config["expected_wk_count"],
        "sources": config.get("sources", []),
    }
    write_json(mapping, output_dir / "plz-wahlkreis.json", meta)
    write_csv(mapping, output_dir / "plz-wahlkreis.csv")

    # Summary
    elapsed = time.time() - t0
    n_plz = len(mapping)
    all_wk = {wk["nr"] for entry in mapping.values() for wk in entry["wahlkreise"]}
    multi_wk = sum(1 for entry in mapping.values() if len(entry["wahlkreise"]) > 1)

    log.info("")
    log.info("--- %s Summary ---", config["state_name"])
    log.info("PLZ processed:     %d", n_plz)
    log.info("Wahlkreise covered: %d / %d", len(all_wk), config["expected_wk_count"])
    log.info("Multi-assignment:  %d PLZ", multi_wk)
    log.info("Processing time:   %.1f seconds", elapsed)

    if len(all_wk) != config["expected_wk_count"]:
        log.warning("WARNING: Expected %d WK, got %d", config["expected_wk_count"], len(all_wk))
        return False

    return True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_build_plz_ags(force: bool = False) -> None:
    """Build the PLZ-to-AGS mapping shared by the municipality-join states."""
    inputs = [p for p in (RAW_PLZ_PATH, VG250_GEM_PATH) if p.exists()]
    if (
        PLZ_AGS_CACHE.exists()
        and not force
        and all(p.stat().st_mtime <= PLZ_AGS_CACHE.stat().st_mtime for p in inputs)
    ):
        log.info("PLZ-AGS mapping is up to date at %s", PLZ_AGS_CACHE)
        return

    if not VG250_GEM_PATH.exists():
        raise SourceDataError(
            f"VG250 Gemeinden shapefile not found at {VG250_GEM_PATH}. "
            "Run 'make download-landtag' first."
        )

    t0 = time.time()
    plz_gdf = get_plz_gdf()
    result = build_plz_ags_mapping(plz_gdf, VG250_GEM_PATH, PLZ_AGS_CACHE)

    # Validate
    n_plz = result["plz"].nunique()
    bad_ags = result[result["ags"].str.len() != 8]
    elapsed = time.time() - t0

    log.info("")
    log.info("=== PLZ-AGS Mapping Summary ===")
    log.info("PLZ mapped:    %d", n_plz)
    log.info("Gemeinden:     %d", result["ags"].nunique())
    log.info("Total pairs:   %d", len(result))
    log.info("Build time:    %.1f seconds", elapsed)

    if len(bad_ags) > 0:
        raise ValidationError(f"INVALID: {len(bad_ags)} rows with non-8-digit AGS codes")


def cmd_process_all() -> None:
    """Process all states with configs."""
    configs = sorted(CONFIGS_DIR.glob("*.yaml"))
    if not configs:
        log.error("No configs found in %s", CONFIGS_DIR)
        sys.exit(1)

    log.info("Found %d state configs", len(configs))
    results = {}

    for config_path in configs:
        slug = config_path.stem
        try:
            success = process_state(slug)
            results[slug] = "OK" if success else "WARN"
        except Exception as e:
            log.error("FAILED: %s — %s", slug, e)
            results[slug] = "FAIL"

    # Print summary
    log.info("")
    log.info("=" * 60)
    log.info("=== All States Summary ===")
    for slug, status in sorted(results.items()):
        icon = "✓" if status == "OK" else "⚠" if status == "WARN" else "✗"
        log.info("  %s %s: %s", icon, slug, status)

    n_ok = sum(1 for s in results.values() if s == "OK")
    n_fail = sum(1 for s in results.values() if s != "OK")
    log.info("")
    log.info("Completed: %d/%d succeeded, %d failed", n_ok, len(results), n_fail)

    if n_fail > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Landtag PLZ-to-Wahlkreis processor")
    parser.add_argument("--build-plz-ags", action="store_true",
                        help="Build PLZ-AGS mapping from VG250")
    parser.add_argument("--force", action="store_true",
                        help="Force rebuild of cached data")
    parser.add_argument("--state", type=str,
                        help="Process a single state (slug from configs/landtag/)")
    parser.add_argument("--all", action="store_true",
                        help="Process all states with configs")

    args = parser.parse_args()

    try:
        if args.build_plz_ags:
            cmd_build_plz_ags(force=args.force)
        elif args.state:
            success = process_state(args.state)
            if not success:
                sys.exit(1)
        elif args.all:
            cmd_process_all()
        else:
            parser.print_help()
            sys.exit(1)
    except DataPipelineError as exc:
        log.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
