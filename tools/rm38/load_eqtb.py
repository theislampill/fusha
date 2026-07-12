from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.rm38.load_common import first, load_records, normalized_row


_PROHIBITED_EXPRESSIVE_COLUMNS = ("gloss", "translation", "english", "meaning")


def _project(row: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in row.items():
        normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
        if any(term in normalized_key for term in _PROHIBITED_EXPRESSIVE_COLUMNS):
            continue
        safe[key] = value
    output = normalized_row(safe)
    uthmani = first(safe, "uthmani", "uthmani_word", "uthmani_surface", "uthmanic")
    if uthmani is not None:
        output["surface"] = uthmani
        output["orthography"] = "uthmani"
    return output


def load_eqtb(path: Path, pin: dict[str, Any]) -> list[dict[str, Any]]:
    """Load morphology/syntax facts while dropping all gloss/translation columns immediately."""
    return load_records(path, pin, _project)
