#!/usr/bin/env python3
"""Validate the loc-first largelexicon denominator join contract.

This guard exists because the RH-LIVE rollout repeatedly proved that raw
`qword_index`/position matching can look plausible while joining the wrong
visible token. The only durable join is source-addressed:

1. denominator row -> accepted crosswalk row by qword_row_id
2. public/source row -> accepted canonical quran/wbw loc
3. surface agreement is a safety check, never the primary identity

The tool can validate the committed table alone, or validate JSONL public rows
with `source_key`, `loc`/`data_loc`/`quran_loc`, and `surface`.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from largelexicon_common import PUBLIC_BOUNDARY  # noqa: E402
from largelexicon_table_reader import LargelexiconQwordTable  # noqa: E402
from normalize_ar import norm_strict  # noqa: E402

ACCEPTED = "canonical_crosswalk_accepted"


def _join_surface_key(surface: str) -> str:
    """Surface key for public/readback joins.

    `norm_strict` is right for many scripture-facing identity checks, but it
    intentionally drops harakat. That is too loose for public qword readback:
    common function-token collisions such as مِن/مَن must not collapse after a
    loc join. Keep Arabic vowel marks and hamza seats, while dropping only
    non-lexical Qur'anic annotation marks, tatweel, and whitespace.
    """

    import unicodedata

    out: list[str] = []
    for ch in unicodedata.normalize("NFC", surface or ""):
        o = ord(ch)
        if ch.isspace() or o == 0x0640 or 0x06D6 <= o <= 0x06ED:
            continue
        out.append(ch)
    return "".join(out).replace("ٱ", "ا")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_file"] = str(path)
            row["_line"] = line_no
            rows.append(row)
    return rows


def _row_label(row: dict[str, Any]) -> str:
    where = f"{row.get('_file')}:{row.get('_line')}: " if row.get("_file") and row.get("_line") else ""
    return where + str(row.get("row_id") or row.get("qword_row_id") or row.get("loc") or "<row>")


def _quran_ref_from_loc(loc: str | None) -> str | None:
    if not loc:
        return None
    parts = str(loc).split(":")
    if len(parts) < 2:
        return None
    return f"{parts[0]}:{parts[1]}"


def _public_loc(row: dict[str, Any]) -> str | None:
    for key in ("canonical_quran_loc", "canonical_wbw_loc", "quran_loc", "wbw_loc", "data_loc", "loc"):
        value = row.get(key)
        if value:
            return str(value)
    return None


def _public_surface(row: dict[str, Any]) -> str:
    for key in ("surface", "visible_surface", "qword_surface", "text"):
        value = row.get(key)
        if value:
            return str(value)
    return ""


def _source_keys(row: dict[str, Any]) -> set[str]:
    keys = row.get("source_keys")
    if isinstance(keys, list):
        return {str(k) for k in keys}
    key = row.get("source_key")
    return {str(key)} if key else set()


def _accepted_crosswalks(table: LargelexiconQwordTable) -> list[dict[str, Any]]:
    return [row for row in table.iter_crosswalk_rows() if row.get("status") == ACCEPTED]


def validate_materialized_table(root: Path = ROOT) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    table = LargelexiconQwordTable.from_repo(root)
    denominator_by_id = {row["row_id"]: row for row in table.iter_rows()}
    accepted = _accepted_crosswalks(table)
    seen_qword_ids: set[str] = set()
    for row in accepted:
        label = _row_label(row)
        qword_id = row.get("qword_row_id")
        denom = denominator_by_id.get(qword_id)
        if not denom:
            errors.append(f"{label}: accepted crosswalk row does not point to a denominator row")
            continue
        if qword_id in seen_qword_ids:
            errors.append(f"{label}: duplicate accepted crosswalk for qword row {qword_id}")
        seen_qword_ids.add(qword_id)
        if row.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append(f"{label}: public_boundary must stay source-clean")
        if row.get("entry_id") != denom.get("entry_id"):
            errors.append(f"{label}: entry_id mismatch between crosswalk and denominator")
        if row.get("card_id") != denom.get("card_id"):
            errors.append(f"{label}: card_id mismatch between crosswalk and denominator")
        if row.get("quran_ref") != denom.get("quran_ref"):
            errors.append(f"{label}: quran_ref mismatch between crosswalk and denominator")
        if not row.get("canonical_quran_loc") or not row.get("canonical_wbw_loc"):
            errors.append(f"{label}: accepted crosswalk requires canonical quran and wbw locs")
        if _quran_ref_from_loc(row.get("canonical_quran_loc")) != row.get("quran_ref"):
            errors.append(f"{label}: canonical_quran_loc does not match quran_ref")
        if _quran_ref_from_loc(row.get("canonical_wbw_loc")) != row.get("quran_ref"):
            errors.append(f"{label}: canonical_wbw_loc does not match quran_ref")
        if norm_strict(row.get("visible_surface") or "") != norm_strict(row.get("resolved_surface") or ""):
            errors.append(f"{label}: visible/resolved surface mismatch under norm_strict")
    status_counts = Counter(row.get("status") for row in table.iter_crosswalk_rows())
    return errors, {
        "denominator_rows": len(denominator_by_id),
        "accepted_crosswalk_rows": len(accepted),
        "crosswalk_status_counts": dict(status_counts),
    }


def join_public_rows(public_rows: Iterable[dict[str, Any]], root: Path = ROOT) -> tuple[list[str], dict[str, Any]]:
    """Join public rows by canonical loc + optional source/surface checks.

    This function intentionally ignores `qword_index` as an identity key. Rows
    lacking a canonical loc are reported as misses even if their qword_index
    numerically matches a denominator row.
    """

    errors: list[str] = []
    table = LargelexiconQwordTable.from_repo(root)
    accepted = _accepted_crosswalks(table)
    by_loc: dict[str, list[dict[str, Any]]] = {}
    for row in accepted:
        for loc_key in ("canonical_quran_loc", "canonical_wbw_loc"):
            loc = row.get(loc_key)
            if loc:
                by_loc.setdefault(str(loc), []).append(row)
    joined = 0
    misses = 0
    ambiguous = 0
    surface_mismatch = 0
    for row in public_rows:
        label = _row_label(row)
        loc = _public_loc(row)
        if not loc:
            misses += 1
            errors.append(f"{label}: public row lacks canonical loc; position/qword_index join is forbidden")
            continue
        matches = list(by_loc.get(loc) or [])
        keys = _source_keys(row)
        if keys:
            keyed = [match for match in matches if keys & _source_keys(match)]
            matches = keyed or matches
        if not matches:
            misses += 1
            errors.append(f"{label}: no accepted denominator crosswalk for loc {loc}")
            continue
        surface = _public_surface(row)
        if surface:
            surface_matches = [
                match
                for match in matches
                if _join_surface_key(match.get("visible_surface") or "") == _join_surface_key(surface)
            ]
            if surface_matches:
                matches = surface_matches
            else:
                surface_mismatch += 1
                errors.append(f"{label}: loc {loc} joined but surface {surface!r} disagrees with accepted denominator surface(s)")
                continue
        if len({match.get("qword_row_id") for match in matches}) > 1:
            ambiguous += 1
            errors.append(f"{label}: loc {loc} joins multiple denominator rows; require source_key/surface disambiguation")
            continue
        joined += 1
    return errors, {
        "public_rows": joined + misses + ambiguous + surface_mismatch,
        "joined": joined,
        "misses": misses,
        "ambiguous": ambiguous,
        "surface_mismatch": surface_mismatch,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        idx = root / "qamus" / "indexes" / "largelexicon"
        (idx / "qword-denominator").mkdir(parents=True)
        (idx / "qword-crosswalk").mkdir(parents=True)
        denom_rows = [
            {
                "row_id": "llx-qword-aaaaaaaaaaaa-01-01-001",
                "entry_id": "aaaaaaaaaaaa",
                "card_id": "aaaaaaaaaaaa:u1:e1",
                "quran_ref": "2:1",
                "qword_index": 1,
                "visible_surface": "مِن",
                "source_keys": ["p001"],
                "public_boundary": PUBLIC_BOUNDARY,
            },
            {
                "row_id": "llx-qword-aaaaaaaaaaaa-01-01-002",
                "entry_id": "aaaaaaaaaaaa",
                "card_id": "aaaaaaaaaaaa:u1:e1",
                "quran_ref": "22:18",
                "qword_index": 1,
                "visible_surface": "مَن",
                "source_keys": ["p001"],
                "public_boundary": PUBLIC_BOUNDARY,
            },
        ]
        cross_rows = [
            {
                "row_id": "llx-crosswalk-1",
                "qword_row_id": denom_rows[0]["row_id"],
                "entry_id": denom_rows[0]["entry_id"],
                "card_id": denom_rows[0]["card_id"],
                "quran_ref": "2:1",
                "canonical_quran_loc": "2:1:1",
                "canonical_wbw_loc": "2:1:1",
                "visible_surface": "مِن",
                "resolved_surface": "مِن",
                "source_keys": ["p001"],
                "status": ACCEPTED,
                "public_boundary": PUBLIC_BOUNDARY,
            },
            {
                "row_id": "llx-crosswalk-2",
                "qword_row_id": denom_rows[1]["row_id"],
                "entry_id": denom_rows[1]["entry_id"],
                "card_id": denom_rows[1]["card_id"],
                "quran_ref": "22:18",
                "canonical_quran_loc": "22:18:7",
                "canonical_wbw_loc": "22:18:7",
                "visible_surface": "مَن",
                "resolved_surface": "مَن",
                "source_keys": ["p001"],
                "status": ACCEPTED,
                "public_boundary": PUBLIC_BOUNDARY,
            },
        ]
        denom_path = idx / "qword-denominator" / "sample.jsonl"
        cross_path = idx / "qword-crosswalk" / "sample.jsonl"
        denom_path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in denom_rows) + "\n", encoding="utf-8")
        cross_path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in cross_rows) + "\n", encoding="utf-8")
        (idx / "qamus-qword-denominator.manifest.json").write_text(json.dumps({
            "table_id": "sample",
            "row_count": 2,
            "shard_count": 1,
            "qamus_entry_count": 1,
            "entries_with_qword_rows": 1,
            "entries_without_qword_rows": [],
            "storage": "jsonl",
            "entry_index_path": "qamus/indexes/largelexicon/qamus-qword-denominator.entry-shard-index.json",
            "public_boundary": PUBLIC_BOUNDARY,
            "shards": [{"path": "qamus/indexes/largelexicon/qword-denominator/sample.jsonl", "row_count": 2}],
        }, ensure_ascii=False), encoding="utf-8")
        (idx / "qamus-qword-denominator.entry-shard-index.json").write_text(json.dumps({
            "entry_count": 1,
            "entries": {"aaaaaaaaaaaa": {"path": "qamus/indexes/largelexicon/qword-denominator/sample.jsonl"}},
        }, ensure_ascii=False), encoding="utf-8")
        (idx / "qamus-qword-crosswalk.manifest.json").write_text(json.dumps({
            "row_count": 2,
            "shard_count": 1,
            "status_counts": {ACCEPTED: 2},
            "public_boundary": PUBLIC_BOUNDARY,
            "shards": [{"path": "qamus/indexes/largelexicon/qword-crosswalk/sample.jsonl", "row_count": 2}],
        }, ensure_ascii=False), encoding="utf-8")
        errors, report = validate_materialized_table(root)
        if errors:
            print(json.dumps({"ok": False, "errors": errors, **report}, ensure_ascii=False, indent=2))
            return 1
        public_ok = [{"loc": "2:1:1", "surface": "مِن", "source_key": "p001"}]
        errors, joined = join_public_rows(public_ok, root)
        if errors or joined["joined"] != 1:
            print(json.dumps({"ok": False, "errors": errors, **joined}, ensure_ascii=False, indent=2))
            return 1
        public_bad = [{"qword_index": 1, "surface": "مَن", "source_key": "p001"}]
        errors, joined = join_public_rows(public_bad, root)
        if not errors or "position/qword_index join is forbidden" not in errors[0]:
            print(json.dumps({"ok": False, "errors": errors, **joined}, ensure_ascii=False, indent=2))
            return 1
        surface_bad = [{"loc": "2:1:1", "surface": "مَن", "source_key": "p001"}]
        errors, joined = join_public_rows(surface_bad, root)
        if not errors or "surface" not in errors[0]:
            print(json.dumps({"ok": False, "errors": errors, **joined}, ensure_ascii=False, indent=2))
            return 1
    print("ok   validate_largelexicon_denominator_join self-test: loc-first join enforced; qword_index false-join rejected")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-rows", type=Path, help="optional JSONL public/readback rows to join by canonical loc")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors, report = validate_materialized_table(ROOT)
    if args.public_rows:
        public_errors, public_report = join_public_rows(_read_jsonl(args.public_rows), ROOT)
        errors.extend(public_errors)
        report.update(public_report)
    print(json.dumps({"ok": not errors, "errors": errors, **report}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    _argv = __import__("sys").argv
    _d11_read_only = any(flag in _argv[1:] for flag in ("--self-test", "--fixture"))
    if "--write" in _argv[1:]:
        _argv.remove("--write")
    elif not _d11_read_only:
        print("DRY RUN: would write cross_path; denom_path; idx / 'qamus-qword-crosswalk.manifest.json'; idx / 'qamus-qword-denominator.entry-shard-index.json'; idx / 'qamus-qword-denominator.manifest.json'; pass --write to apply")
        raise SystemExit(0)
    raise SystemExit(main())
