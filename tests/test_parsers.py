from __future__ import annotations


import pandas as pd
import pytest

from lib.errors import ValidationError
from lib.parsers import parse_landkreis_prefix, validate_parser_output


def test_validate_parser_output_normalizes_and_deduplicates() -> None:
    df = pd.DataFrame(
        [
            {"ags": "123456", "wk_nr": "7", "wk_name": " North "},
            {"ags": "00123456", "wk_nr": 7, "wk_name": "North"},
        ]
    )

    result = validate_parser_output(
        df,
        parser_name="test_parser",
        allow_multi_wk_per_ags=False,
    )

    assert result.to_dict(orient="records") == [
        {"ags": "00123456", "wk_nr": 7, "wk_name": "North"}
    ]


def test_validate_parser_output_rejects_split_ags_when_disallowed() -> None:
    df = pd.DataFrame(
        [
            {"ags": "01001000", "wk_nr": 1, "wk_name": "A"},
            {"ags": "01001000", "wk_nr": 2, "wk_name": "B"},
        ]
    )

    with pytest.raises(ValidationError, match="map to multiple Wahlkreise"):
        validate_parser_output(
            df,
            parser_name="test_parser",
            allow_multi_wk_per_ags=False,
        )


def test_parse_landkreis_prefix_expands_using_cached_plz_ags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import lib.municipality as municipality

    monkeypatch.setattr(
        municipality,
        "load_plz_ags_mapping",
        lambda _path: pd.DataFrame(
            [
                {"plz": "10000", "ags": "12010001", "overlap": 1.0},
                {"plz": "10001", "ags": "12010002", "overlap": 1.0},
                {"plz": "20000", "ags": "13000001", "overlap": 1.0},
            ]
        ),
    )

    config = {
        "landkreis_prefix_mapping": [
            {"ags_prefix": "12010", "wk_nr": 3, "wk_name": "Berlin-Nord"},
        ]
    }

    result = parse_landkreis_prefix(None, config)

    assert result.to_dict(orient="records") == [
        {"ags": "12010001", "wk_nr": 3, "wk_name": "Berlin-Nord"},
        {"ags": "12010002", "wk_nr": 3, "wk_name": "Berlin-Nord"},
    ]
