"""State-specific data parsers for Landtag constituency data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from .errors import SourceDataError, ValidationError

log = logging.getLogger(__name__)


def validate_parser_output(
    df: pd.DataFrame,
    *,
    parser_name: str,
    allow_multi_wk_per_ags: bool,
) -> pd.DataFrame:
    """Validate and normalize parser output before municipality joins."""
    required = ["ags", "wk_nr", "wk_name"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SourceDataError(f"{parser_name}: missing required columns {missing}")

    result = df[required].copy()
    result = result.dropna(subset=["ags", "wk_nr", "wk_name"])
    result["ags"] = result["ags"].astype(str).str.strip().str.zfill(8)
    result["wk_nr"] = result["wk_nr"].astype(int)
    result["wk_name"] = result["wk_name"].astype(str).str.strip()

    bad_ags = result[~result["ags"].str.fullmatch(r"\d{8}")]
    if not bad_ags.empty:
        raise ValidationError(f"{parser_name}: found {len(bad_ags)} rows with invalid AGS codes")

    result = result.drop_duplicates(subset=["ags", "wk_nr", "wk_name"])
    multi_assignments = result.groupby("ags")["wk_nr"].nunique()
    split_ags = multi_assignments[multi_assignments > 1]
    if not allow_multi_wk_per_ags and not split_ags.empty:
        sample = ", ".join(split_ags.index[:5])
        raise ValidationError(
            f"{parser_name}: {len(split_ags)} AGS codes map to multiple Wahlkreise "
            f"but this parser is configured for single-assignment sources. Sample: {sample}"
        )

    if not split_ags.empty:
        log.info("%s: %d AGS codes span multiple Wahlkreise", parser_name, len(split_ags))

    if result.empty:
        raise ValidationError(f"{parser_name}: parser returned no usable rows")

    return result


def parse_landkreis_prefix(path: Path | None, config: dict[str, Any]) -> pd.DataFrame:
    """Parse a CSV mapping AGS prefixes (Landkreis level) to Wahlkreise.

    Used for states where constituencies = collections of Landkreise (e.g., Saarland).
    The mapping may come either from a CSV file with columns ags_prefix, wk_nr, wk_name
    or from config.landkreis_prefix_mapping. It expands prefixes to all Gemeinde AGS
    codes that start with each prefix.
    """
    if path is not None:
        log.info("Parsing Landkreis-prefix CSV: %s", path.name)
        df = pd.read_csv(path, dtype=str)
    else:
        rows = config.get("landkreis_prefix_mapping", [])
        if not rows:
            raise SourceDataError("parse_landkreis_prefix: no CSV path and no landkreis_prefix_mapping in config")
        log.info("Parsing Landkreis-prefix mapping from config")
        df = pd.DataFrame(rows, columns=["ags_prefix", "wk_nr", "wk_name"])

    # Load full PLZ-AGS mapping to get all Gemeinde AGS codes
    from .municipality import load_plz_ags_mapping
    from pathlib import Path as P
    cache = P(__file__).parent.parent.parent / "raw" / "municipality" / "plz-ags-mapping.parquet"
    plz_ags = load_plz_ags_mapping(cache)

    rows = []
    for _, prefix_row in df.iterrows():
        prefix = prefix_row["ags_prefix"]
        wk_nr = int(prefix_row["wk_nr"])
        wk_name = prefix_row["wk_name"]
        # Find all unique AGS codes with this prefix
        matching = plz_ags[plz_ags["ags"].str.startswith(prefix)]["ags"].unique()
        for ags in matching:
            rows.append({"ags": ags, "wk_nr": wk_nr, "wk_name": wk_name})

    result = validate_parser_output(
        pd.DataFrame(rows),
        parser_name="parse_landkreis_prefix",
        allow_multi_wk_per_ags=bool(config.get("allow_multi_wk_per_ags", False)),
    )
    log.info("Expanded %d prefixes to %d AGS-to-WK entries (%d unique WK)",
             len(df), len(result), result["wk_nr"].nunique())
    return result


def get_parser(config: dict) -> callable:
    """Get the parser function for a state config.

    The config's 'parser' field names a parse_<name> function in this module.
    """
    parser_name = config["parser"]
    func = globals().get(f"parse_{parser_name}")
    if func is None:
        raise ValueError(f"Unknown parser: {parser_name} (expected parse_{parser_name} in parsers.py)")
    return func
