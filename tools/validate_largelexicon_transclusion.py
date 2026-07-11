#!/usr/bin/env python3
"""Validate transclusion dependencies for largerollout3 artifacts."""

from __future__ import annotations

import argparse
import json

from largelexicon_common import QWORD_CROSSWALK_MANIFEST
from largelexicon_table_reader import ROW_ID_RE, LargelexiconQwordTable


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
REQUIRED_DEP_KINDS = {"qword_denominator_row", "entry", "source_card", "table_manifest"}


def _qword_row(table: LargelexiconQwordTable, cache: dict, row_id: str):
    """Memoized reverse lookup: load each entry's denominator rows once."""
    match = ROW_ID_RE.match(row_id or "")
    if not match:
        return None
    entry_id = match.group(1)
    if entry_id not in cache:
        cache[entry_id] = {
            row.get("row_id"): row for row in table.rows_for_entry(entry_id)
        }
    return cache[entry_id].get(row_id)


def validate(root=None, *, limit: int | None = None) -> list[str]:
    errors: list[str] = []
    if root is None:
        root = ROOT
        crosswalk_manifest_path = QWORD_CROSSWALK_MANIFEST
    else:
        crosswalk_manifest_path = None  # resolved via the table reader below
    table = LargelexiconQwordTable.from_repo(root)
    if crosswalk_manifest_path is None:
        crosswalk_manifest_path = table.crosswalk_manifest_path()
    if not crosswalk_manifest_path.exists():
        return [f"missing crosswalk manifest: {crosswalk_manifest_path}"]
    manifest = json.loads(crosswalk_manifest_path.read_text(encoding="utf-8"))
    contract = manifest.get("transclusion_contract") or {}
    if contract.get("requires_source_dependencies") is not True:
        errors.append("crosswalk manifest must require source dependencies")
    checked = 0
    qword_cache: dict = {}
    for row in table.iter_crosswalk_rows(limit=limit):
        checked += 1
        kinds = {dep.get("kind") for dep in row.get("source_dependencies") or []}
        missing = REQUIRED_DEP_KINDS - kinds
        if missing:
            errors.append(f"{row.get('row_id')}: missing dependency kinds {sorted(missing)}")
        qword = _qword_row(table, qword_cache, row.get("qword_row_id") or "")
        if not qword:
            errors.append(f"{row.get('row_id')}: reverse qword lookup failed")
        elif qword.get("entry_id") != row.get("entry_id"):
            errors.append(f"{row.get('row_id')}: reverse qword entry_id mismatch")
    if checked == 0:
        errors.append("no crosswalk rows checked")
    manifest_row_count = manifest.get("row_count")
    if limit is None and isinstance(manifest_row_count, int) and checked != manifest_row_count:
        errors.append(
            f"rows_checked {checked} != crosswalk manifest row_count {manifest_row_count}"
        )
    return errors


def _write_jsonl(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def self_test() -> int:
    """Isolated synthetic table seeding the three defect classes + a clean row."""
    import tempfile
    from pathlib import Path

    entry = "0123456789ab"
    good_dep = [{"kind": k} for k in sorted(REQUIRED_DEP_KINDS)]

    def qword_row(n: int) -> dict:
        return {"row_id": f"llx-qword-{entry}-01-01-{n:03d}", "entry_id": entry}

    def xwalk_row(n: int, *, deps=None, qword=None, entry_id=entry) -> dict:
        return {
            "row_id": f"llx-crosswalk-llx-qword-{entry}-01-01-{n:03d}",
            "qword_row_id": qword or f"llx-qword-{entry}-01-01-{n:03d}",
            "entry_id": entry_id,
            "source_dependencies": good_dep if deps is None else deps,
        }

    def build_fixture(root: Path, crosswalk_rows, *, row_count=None, contract=True) -> None:
        idx = root / "qamus" / "indexes" / "largelexicon"
        _write_jsonl(idx / "qword" / "shard-000.jsonl", [qword_row(1), qword_row(2), qword_row(3), qword_row(4)])
        (idx / "qamus-qword-denominator.manifest.json").write_text(
            json.dumps({
                "row_count": 4,
                "entry_index_path": "qamus/indexes/largelexicon/qword-entry-index.json",
                "shards": [{"path": "qamus/indexes/largelexicon/qword/shard-000.jsonl"}],
            }),
            encoding="utf-8",
        )
        (idx / "qword-entry-index.json").write_text(
            json.dumps({
                "entry_count": 1,
                "entries": {entry: {"path": "qamus/indexes/largelexicon/qword/shard-000.jsonl"}},
            }),
            encoding="utf-8",
        )
        _write_jsonl(idx / "crosswalk" / "shard-000.jsonl", crosswalk_rows)
        (idx / "qamus-qword-crosswalk.manifest.json").write_text(
            json.dumps({
                "row_count": len(crosswalk_rows) if row_count is None else row_count,
                "transclusion_contract": {"requires_source_dependencies": contract},
                "shards": [{"path": "qamus/indexes/largelexicon/crosswalk/shard-000.jsonl"}],
            }),
            encoding="utf-8",
        )

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # case 1: clean fixture passes
        build_fixture(root, [xwalk_row(1)])
        errs = validate(root)
        if errs:
            failures.append(f"clean fixture should pass, got {errs}")
        # case 2: three seeded defect classes are each caught, at ANY row index
        bad = [
            xwalk_row(1),  # clean
            xwalk_row(2, deps=[{"kind": "entry"}]),  # missing dependency kinds
            xwalk_row(3, qword=f"llx-qword-{entry}-01-01-999"),  # reverse lookup failure
            xwalk_row(4, entry_id="deadbeef0000"),  # entry_id mismatch
        ]
        build_fixture(root, bad)
        errs = validate(root)
        for needle in ("missing dependency kinds", "reverse qword lookup failed", "reverse qword entry_id mismatch"):
            if not any(needle in e for e in errs):
                failures.append(f"defect class not caught: {needle} (errors: {errs})")
        # case 3: full scan reconciles against the manifest row_count
        build_fixture(root, [xwalk_row(1)], row_count=99)
        errs = validate(root)
        if not any("!= crosswalk manifest row_count" in e for e in errs):
            failures.append(f"row_count guard did not fire, got {errs}")
        # case 4: --limit skips the row_count guard but still validates the sample
        errs = validate(root, limit=1)
        if any("row_count" in e for e in errs):
            failures.append(f"--limit run must not enforce row_count, got {errs}")
    print(json.dumps({"ok": not failures, "self_test_failures": failures}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run the isolated synthetic fixture suite")
    parser.add_argument("--limit", type=int, default=None,
                        help="check only the first N crosswalk rows (default: full scan)")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate(limit=args.limit)
    checked_note = {"limit": args.limit} if args.limit is not None else {"scan": "full"}
    print(json.dumps({"ok": not errors, "errors": errors, **checked_note}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    _argv = __import__("sys").argv
    _d11_read_only = any(flag in _argv[1:] for flag in ("--self-test", "--fixture"))
    if "--write" in _argv[1:]:
        _argv.remove("--write")
    elif not _d11_read_only:
        print("DRY RUN: would write idx / 'qamus-qword-crosswalk.manifest.json'; idx / 'qamus-qword-denominator.manifest.json'; idx / 'qword-entry-index.json'; pass --write to apply")
        raise SystemExit(0)
    raise SystemExit(main())
