from __future__ import annotations

from pathlib import Path

import pytest

from download_landtag import verify_checksum


def test_verify_checksum_accepts_matching_hash(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello\n", encoding="utf-8")

    verify_checksum(path, "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03")


def test_verify_checksum_rejects_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        verify_checksum(path, "deadbeef")
