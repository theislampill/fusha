"""Manifest-backed readers for largelexicon source-clean fact tables."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


ROW_ID_RE = re.compile(r"^llx-qword-([0-9a-f]{12})-\d{2}-\d{2}-\d{3}$")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


@dataclass(frozen=True)
class LargelexiconQwordTable:
    """Reader for the source-clean Qamus qword denominator logical table."""

    root: Path
    manifest_path: Path
    manifest: dict[str, Any]
    entry_index: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "LargelexiconQwordTable":
        manifest_path = root / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.manifest.json"
        manifest = _read_json(manifest_path)
        entry_index_path = root / manifest["entry_index_path"]
        return cls(root=root, manifest_path=manifest_path, manifest=manifest, entry_index=_read_json(entry_index_path))

    def summary(self) -> dict[str, Any]:
        return {
            "schema": "qamus/largelexicon-qword-table-reader-summary@1",
            "table_id": self.manifest.get("table_id"),
            "row_count": self.manifest.get("row_count"),
            "shard_count": self.manifest.get("shard_count"),
            "entry_count": self.entry_index.get("entry_count"),
            "qamus_entry_count": self.manifest.get("qamus_entry_count"),
            "entries_with_qword_rows": self.manifest.get("entries_with_qword_rows"),
            "entries_without_qword_rows": self.manifest.get("entries_without_qword_rows") or [],
            "storage": self.manifest.get("storage"),
            "manifest_path": self.manifest_path.relative_to(self.root).as_posix(),
            "entry_index_path": self.manifest.get("entry_index_path"),
            "public_boundary": self.manifest.get("public_boundary"),
        }

    def _shard_path(self, rel: str) -> Path:
        return self.root / rel

    def iter_rows(self, *, limit: int | None = None) -> Iterator[dict[str, Any]]:
        yielded = 0
        for shard in self.manifest.get("shards") or []:
            for row in _iter_jsonl(self._shard_path(shard["path"])):
                yield row
                yielded += 1
                if limit is not None and yielded >= limit:
                    return

    def rows_for_entry(self, entry_id: str) -> Iterator[dict[str, Any]]:
        info = (self.entry_index.get("entries") or {}).get(entry_id)
        if not info:
            return
        for row in _iter_jsonl(self._shard_path(info["path"])):
            if row.get("entry_id") == entry_id:
                yield row

    def row_by_id(self, row_id: str) -> dict[str, Any] | None:
        match = ROW_ID_RE.match(row_id or "")
        if not match:
            return None
        for row in self.rows_for_entry(match.group(1)):
            if row.get("row_id") == row_id:
                return row
        return None
