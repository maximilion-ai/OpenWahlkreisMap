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


def parse_sachsen(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    """Parse Sachsen election results Excel to extract AGS→Wahlkreis mapping.

    Sheet 'LW24_endgErgebnisse_GE&TG' has both Gemeinde (GE) and Teilgemeinde (TG)
    rows. TG rows have 9-digit AGS for cities split across multiple WK (Chemnitz,
    Leipzig, Dresden, Zwickau). We truncate these to 8-digit parent Gemeinde AGS
    so they match the PLZ-AGS mapping — the join then distributes overlap equally
    across WK within that city (same approach as NRW split cities).
    """
    sheet = "LW24_endgErgebnisse_GE&TG"
    log.info("Parsing Sachsen election results: %s (sheet=%s)", path.name, sheet)

    df = pd.read_excel(path, sheet_name=sheet, header=0)
    # Filter to GE and TG rows (col 'Ebene.1' due to duplicate column name)
    df = df[df["Ebene.1"].isin(["GE", "TG"])].copy()

    result = df[["AGS", "WK-Nr", "WK-Name"]].copy()
    result.columns = ["ags", "wk_nr", "wk_name"]
    result = result.dropna(subset=["ags", "wk_nr"])

    # Normalize AGS: truncate 9-digit TG codes to 8-digit Gemeinde, zero-pad shorter
    result["ags"] = result["ags"].astype(str).str.strip().str[:8].str.zfill(8)
    result["wk_nr"] = result["wk_nr"].astype(int)
    result["wk_name"] = result["wk_name"].astype(str).str.strip()

    # Do NOT deduplicate — split cities have same 8-digit AGS in multiple WK
    result = validate_parser_output(
        result,
        parser_name="parse_sachsen",
        allow_multi_wk_per_ags=True,
    )
    log.info("Parsed %d AGS-to-WK entries (%d unique WK, %d unique AGS)",
             len(result), result["wk_nr"].nunique(), result["ags"].nunique())
    return result


def parse_brandenburg(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    """Parse Brandenburg LT-Wahlkreiseinteilung2024 sheet.

    Complex layout: WK number in col 0 (only on first row of group, needs ffill),
    WK name in col 1, Gemeinde name in col 5, 12-digit Regionalschlüssel in col 6.
    AGS derived from RS: first 5 digits + last 3 digits. Filter out Amt-level rows
    (which have 9-digit RS) and keep only Gemeinde rows (12-digit RS).
    """
    log.info("Parsing Brandenburg: %s", path.name)
    df = pd.read_excel(path, sheet_name="LT-Wahlkreiseinteilung2024", header=None, skiprows=5)

    # Forward-fill WK number and name
    df.iloc[:, 0] = df.iloc[:, 0].ffill()
    df.iloc[:, 1] = df.iloc[:, 1].ffill()

    # Filter to rows with Regionalschlüssel (col 6)
    df = df.dropna(subset=[df.columns[6]])

    # Keep only Gemeinde-level rows (12-digit RS, not 9-digit Amt rows)
    df["rs_str"] = df.iloc[:, 6].astype(int).astype(str)
    df = df[df["rs_str"].str.len() >= 12].copy()

    # Derive 8-digit AGS: first 5 digits + last 3 digits of 12-digit RS
    df["ags"] = df["rs_str"].str[:5] + df["rs_str"].str[-3:]

    result = pd.DataFrame()
    result["ags"] = df["ags"]
    result["wk_nr"] = df.iloc[:, 0].astype(int)
    result["wk_name"] = df.iloc[:, 1].astype(str).str.strip()

    result = validate_parser_output(
        result,
        parser_name="parse_brandenburg",
        allow_multi_wk_per_ags=True,
    )

    log.info("Parsed %d AGS-to-WK entries (%d unique WK, %d unique AGS)",
             len(result), result["wk_nr"].nunique(), result["ags"].nunique())
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
