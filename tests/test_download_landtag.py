from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

import download_landtag
from download_landtag import download_state, verify_checksum


def test_verify_checksum_accepts_matching_hash(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello\n", encoding="utf-8")

    verify_checksum(path, "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03")


def test_verify_checksum_rejects_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        verify_checksum(path, "deadbeef")


def manual_config(checksum: str) -> dict:
    return {
        "state": "sachsen",
        "state_name": "Sachsen",
        "download": {
            "mode": "manual",
            "filename": "wk.zip",
            "checksum_sha256": checksum,
            "format": "shapefile",
            "raw_subdir": "sachsen",
            "notes": "Request it from the Landeswahlleiter.",
        },
    }


def test_manual_source_fails_with_notes_when_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(download_landtag, "LANDTAG_RAW_DIR", tmp_path)

    with pytest.raises(RuntimeError, match="place wk.zip in .*Request it from the Landeswahlleiter"):
        download_state(manual_config("unused"))


def test_manual_source_extracts_and_keeps_the_placed_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(download_landtag, "LANDTAG_RAW_DIR", tmp_path)
    archive = tmp_path / "sachsen" / "wk.zip"
    archive.parent.mkdir()
    with zipfile.ZipFile(archive, "w") as zf:
        for ext in ("shp", "shx", "dbf", "prj"):
            zf.writestr(f"wk.{ext}", "x")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()

    assert download_state(manual_config(checksum)) is True
    assert sorted(p.name for p in archive.parent.iterdir()) == [
        "wk.dbf", "wk.prj", "wk.shp", "wk.shx", "wk.zip",
    ]
