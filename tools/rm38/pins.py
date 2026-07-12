from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PinError(ValueError):
    """A user-local source is absent, unpinned, stale, or tampered."""


def load_pins(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != "fusha/rm38-data-pins@1":
        raise PinError(f"unsupported pins schema: {path}")
    sources = data.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"quranmorph", "eqtb"}:
        raise PinError(f"pins file must define exactly quranmorph and eqtb: {path}")
    return data


def verify_pinned_file(path: Path, pin: dict[str, Any]) -> str:
    expected = str(pin.get("sha256", "")).lower()
    if expected == "to_pin" or not expected:
        raise PinError(f"refusing unpinned source (sha256=TO_PIN): {path}")
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise PinError(f"invalid expected sha256 for source: {path}")
    if not path.is_file():
        raise PinError(f"source path is not a file: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise PinError(f"sha256 mismatch for {path}: expected {expected}, got {digest}")
    expected_name = pin.get("filename")
    if expected_name not in (None, "", "TO_PIN") and path.name != expected_name:
        raise PinError(f"filename mismatch for {path}: expected {expected_name}")
    return digest
