from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.rm38.load_common import load_records, normalized_row


def load_quranmorph(path: Path, pin: dict[str, Any]) -> list[dict[str, Any]]:
    return load_records(path, pin, normalized_row)
