"""Manifest-backed readers for largelexicon source-clean fact tables.

``LargelexiconQwordTable`` reads the committed @1 sharded storage. Consumers that
need TARGET-SCHEMA rows must go through :class:`LargelexiconTargetTables`, which
regenerates the carried rows behind the release freshness gate: a stale,
validation-red, mixed-version, or schema-drifted release raises instead of
handing back rows.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

# The largelexicon tool family imports flat sibling modules. Keep that working
# whether this module is loaded as ``largelexicon_table_reader`` or, from the
# repository boundary, as ``tools.largelexicon_table_reader``.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ONE canonical module identity. Importing this module flat and as
# ``tools.largelexicon_table_reader`` must not produce two classes, or an
# isinstance/identity check on the reader silently depends on import style.
_CANONICAL_MODULE = "tools.largelexicon_table_reader"
if __name__ != _CANONICAL_MODULE:
    import importlib

    _canonical = sys.modules.get(_CANONICAL_MODULE) or importlib.import_module(_CANONICAL_MODULE)
    sys.modules[__name__] = _canonical


ROW_ID_RE = re.compile(r"^llx-qword-([0-9a-f]{12})-\d{2}-\d{2}-\d{3}$")
TARGET_FAMILIES = ("lemma-source", "form-source", "stem-source", "qword-denominator", "qword-crosswalk")


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

    def crosswalk_manifest_path(self) -> Path:
        return self.root / "qamus" / "indexes" / "largelexicon" / "qamus-qword-crosswalk.manifest.json"

    def crosswalk_manifest(self) -> dict[str, Any] | None:
        path = self.crosswalk_manifest_path()
        if not path.exists():
            return None
        return _read_json(path)

    def crosswalk_summary(self) -> dict[str, Any]:
        manifest = self.crosswalk_manifest()
        if not manifest:
            return {
                "schema": "qamus/largelexicon-qword-crosswalk-summary@1",
                "available": False,
                "manifest_path": self.crosswalk_manifest_path().relative_to(self.root).as_posix(),
            }
        return {
            "schema": "qamus/largelexicon-qword-crosswalk-summary@1",
            "available": True,
            "manifest_path": self.crosswalk_manifest_path().relative_to(self.root).as_posix(),
            "row_count": manifest.get("row_count"),
            "shard_count": manifest.get("shard_count"),
            "status_counts": manifest.get("status_counts") or {},
            "public_boundary": manifest.get("public_boundary"),
        }

    def iter_crosswalk_rows(self, *, limit: int | None = None) -> Iterator[dict[str, Any]]:
        manifest = self.crosswalk_manifest()
        if not manifest:
            return
        yielded = 0
        for shard in manifest.get("shards") or []:
            for row in _iter_jsonl(self._shard_path(shard["path"])):
                yield row
                yielded += 1
                if limit is not None and yielded >= limit:
                    return

    def crosswalk_for_qword(self, qword_row_id: str) -> dict[str, Any] | None:
        for row in self.iter_crosswalk_rows():
            if row.get("qword_row_id") == qword_row_id:
                return row
        return None


@dataclass(frozen=True)
class LargelexiconTargetTables:
    """Fail-closed reader for the derived carried target-schema tables.

    Carried rows are regenerated from the immutable @1 tables rather than stored a
    second time; the released digest is re-checked on every read so a drifted
    regeneration is an error, never silently-different data.
    """

    release: dict[str, Any]
    target_dir: Path | None = None

    @classmethod
    def open(cls, *, target_dir: Path | None = None) -> "LargelexiconTargetTables":
        from promote_largelexicon_target_schema import assert_release_usable, read_release

        release = read_release(target_dir)
        assert_release_usable(release)
        # The exact directory that was validated is retained and used by every
        # later read: validating one release and then reading another is a
        # silent authority swap, so the target dir travels with the reader.
        # Resolve ONCE, at open time: a later chdir must not be able to redirect
        # reads to a different release.
        return cls(release=release,
                   target_dir=Path(target_dir).resolve() if target_dir is not None else None)

    def summary(self) -> dict[str, Any]:
        return {
            "schema": "qamus/largelexicon-target-table-reader-summary@1",
            "families": {
                name: {
                    "carried_row_count": table["carried_row_count"],
                    "carried_sha256": table["carried_sha256"],
                    "disposition_counts": table["disposition_counts"],
                    "target_row_schema": table["target_row_schema"],
                }
                for name, table in sorted(self.release["tables"].items())
            },
            "losslessness": self.release["losslessness"],
            "release_path": "qamus/indexes/largelexicon/target-schema/TARGET-RELEASE.json",
        }

    def carried(self, family_name: str) -> list[dict[str, Any]]:
        from promote_largelexicon_target_schema import carried_table

        if family_name not in TARGET_FAMILIES:
            raise KeyError("unknown target family: " + family_name)
        return carried_table(family_name, target_dir=self.target_dir)

    def dependency_hashes(self) -> dict[str, str]:
        """Exact digests a downstream typed claim must record as dependencies."""

        return {
            name: table["carried_sha256"] for name, table in sorted(self.release["tables"].items())
        }
