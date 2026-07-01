"""Shared helpers for the largelexicon implementation lane.

The largelexicon lane is source-addressed and source-clean. It expands from the
repo-owned Qamus dataset, emits reviewable samples in git, and writes full
generated outputs only when the caller asks for them. It does not touch live
Qamus and does not import external corpus text.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import normalize_ar as N  # noqa: E402
QAMUS_ENTRIES = ROOT / "qamus" / "data" / "current" / "entries.jsonl"
QAMUS_ENTRIES_MIN = ROOT / "qamus" / "data" / "current" / "entries.min.jsonl"
LEXICON_DIR = ROOT / "fusha" / "lexicon" / "largelexicon"
MORPH_EXAMPLE_DIR = ROOT / "fusha" / "morphology" / "examples"
MORPH_DATA_DIR = ROOT / "fusha" / "morphology" / "data"
PARSER_EVAL_DIR = ROOT / "fusha" / "parser" / "eval"
PARSER_MODEL_CARD_DIR = ROOT / "fusha" / "parser" / "model-cards"
REPORT_DIR = ROOT / "qamus" / "reports"
QAMUS_LARGELX_DIR = ROOT / "qamus" / "indexes" / "largelexicon"
ALLOWLIST = LEXICON_DIR / "source-clean-table-allowlist.json"
LEMMA_SAMPLE = LEXICON_DIR / "lemma-source.sample.jsonl"
FORM_SAMPLE = LEXICON_DIR / "form-source.sample.jsonl"
LEMMA_FULL = LEXICON_DIR / "lemma-source.full.jsonl"
FORM_FULL = LEXICON_DIR / "form-source.full.jsonl"
STEM_SAMPLE = MORPH_EXAMPLE_DIR / "largelexicon-stems.sample.jsonl"
STEM_FULL = MORPH_DATA_DIR / "largelexicon-stems.full.jsonl"
QWORD_DENOMINATOR_FULL = QAMUS_LARGELX_DIR / "qamus-qword-denominator.full.jsonl"
QWORD_DENOMINATOR_MANIFEST = QAMUS_LARGELX_DIR / "qamus-qword-denominator.manifest.json"
QWORD_DENOMINATOR_ENTRY_INDEX = QAMUS_LARGELX_DIR / "qamus-qword-denominator.entry-shard-index.json"
QWORD_DENOMINATOR_SOURCE_REPAIR = QAMUS_LARGELX_DIR / "qamus-qword-denominator.source-card-repair.json"
QWORD_DENOMINATOR_SHARD_DIR = QAMUS_LARGELX_DIR / "qword-denominator"
QWORD_CROSSWALK_MANIFEST = QAMUS_LARGELX_DIR / "qamus-qword-crosswalk.manifest.json"
QWORD_CROSSWALK_SHARD_DIR = QAMUS_LARGELX_DIR / "qword-crosswalk"
SOURCE_CARD_REPAIR_DIR = ROOT / "qamus" / "repairs" / "source-card-examples"
SOURCE_CARD_REPAIR_WORKLIST = SOURCE_CARD_REPAIR_DIR / "source-card-repair-worklist.jsonl"
SOURCE_CARD_REPAIR_META = SOURCE_CARD_REPAIR_DIR / "source-card-repair-worklist.meta.json"
FULL_TABLE_META = QAMUS_LARGELX_DIR / "source-clean-fact-tables.meta.json"

PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}
SOURCE_STATUS = "qamus_current_authored"
SCHEMA_PREFIX = "fusha/largelexicon"

FORBIDDEN_PUBLIC_SUBSTRINGS = {
    "mcp",
    "tafsir",
    "qac",
    "quran.com",
    "quranic arabic corpus",
    "/srv/",
    "c:\\",
    "source photo",
    "source-photo",
    "ocr",
}

KNOWN_QWORD_SOURCE_CARD_REPAIR_HINTS = {
    "n993": {
        "source_photo_page_image": "pg443.jpeg",
        "candidate_quran_ref": "42:47",
        "note": "Owner-supplied source card shows Qur'anic usage absent from qamus/data/current/entries.jsonl.",
    }
}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_value(*args: str) -> str:
    try:
        out = subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, encoding="utf-8")
        return out.strip()
    except Exception:
        return "unknown"


def freshness(status: str = "active", stale_after: str = "qamus_data_or_source_schema_change") -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "generated_by": "tools.largelexicon_common",
        "source_head": git_value("rev-parse", "HEAD"),
        "source_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "supersedes": [],
        "stale_after": stale_after,
        "status": status,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = (value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def split_headword(headword: str) -> list[str]:
    parts = re.split(r"\s*/\s*|\s+؛\s+|\s+,\s+", headword or "")
    return unique_keep_order(parts)


def forms_for_entry(entry: dict[str, Any]) -> list[str]:
    forms: list[str] = []
    forms.extend(split_headword(entry.get("headword", "")))
    for sense in entry.get("senses") or []:
        forms.extend(split_headword(sense.get("ar", "")))
    for usage in entry.get("usage") or []:
        forms.extend(usage.get("forms") or [])
    return unique_keep_order(forms)


def section_to_pos(section: str, tags: Iterable[str] = ()) -> str:
    text = " ".join([section or "", *(tags or [])]).lower()
    if "particle" in text:
        return "particle"
    if "verb" in text:
        return "verb"
    if "proper" in text or "name" in text:
        return "proper_noun"
    if "noun" in text:
        return "noun"
    return "unknown"


def no_root_reason(entry: dict[str, Any], pos: str) -> str | None:
    if entry.get("root"):
        return None
    if pos == "particle":
        return "function_only_no_root"
    if pos == "proper_noun":
        return "proper_name_no_root"
    return "qamus_entry_no_root_recorded"


def gloss_hint(entry: dict[str, Any]) -> str:
    for sense in entry.get("senses") or []:
        gloss = (sense.get("gloss") or "").strip()
        if gloss:
            return gloss
    return (entry.get("meaning") or entry.get("definition") or entry.get("gloss") or "").strip()


def qg_class_for_pos(pos: str) -> str:
    return {
        "particle": "qg-particle",
        "verb": "qg-verb-stem",
        "proper_noun": "qg-proper-noun",
        "noun": "qg-noun-stem",
    }.get(pos, "qg-noun-stem")


def entry_to_lemma(entry: dict[str, Any]) -> dict[str, Any]:
    pos = section_to_pos(entry.get("section", ""), entry.get("tags") or [])
    forms = forms_for_entry(entry)
    root = (entry.get("root") or "").strip() or None
    return {
        "schema": f"{SCHEMA_PREFIX}/lemma-source@1",
        "entry_id": entry["id"],
        "source_keys": entry.get("source_keys") or [],
        "lemma": entry.get("headword"),
        "root": root,
        "no_root_reason": no_root_reason(entry, pos),
        "pos": pos,
        "forms": forms,
        "gloss_hint": gloss_hint(entry),
        "source_status": SOURCE_STATUS,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "risk_flags": risk_flags(entry, pos, forms),
    }


def form_rows_for_lemmas(lemmas: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lemma in lemmas:
        for index, form in enumerate(lemma.get("forms") or []):
            rows.append(
                {
                    "schema": f"{SCHEMA_PREFIX}/form-source@1",
                    "form_id": f"llx_form_{lemma['entry_id']}_{index:03d}",
                    "entry_id": lemma["entry_id"],
                    "source_keys": lemma["source_keys"],
                    "surface": form,
                    "surface_norm_strict": N.norm_strict(form),
                    "surface_bare": N.bare(form),
                    "lemma": lemma["lemma"],
                    "root": lemma["root"],
                    "no_root_reason": lemma["no_root_reason"],
                    "pos": lemma["pos"],
                    "source_status": lemma["source_status"],
                    "public_boundary": lemma["public_boundary"],
                    "risk_flags": lemma.get("risk_flags") or [],
                }
            )
    return rows


def risk_flags(entry: dict[str, Any], pos: str, forms: list[str]) -> list[str]:
    flags: list[str] = []
    if not entry.get("root"):
        flags.append("no_root_recorded")
    if pos == "particle":
        flags.append("requires_nahw_function")
    if pos == "unknown":
        flags.append("unknown_pos")
    if len(forms) == 0:
        flags.append("no_listed_forms")
    if any("/" in (entry.get("headword") or "") for _ in [0]):
        flags.append("compound_headword")
    return flags


def stem_rows_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    lemma = entry_to_lemma(entry)
    rows: list[dict[str, Any]] = []
    for index, form in enumerate(lemma["forms"]):
        surface = form.strip()
        if not surface:
            continue
        rows.append(
            {
                "schema": f"{SCHEMA_PREFIX}/stem-source@1",
                "stem_id": f"llx_{entry['id']}_{index:03d}",
                "generation_key": f"qamus:{entry['id']}:{index:03d}",
                "entry_id": entry["id"],
                "source_keys": entry.get("source_keys") or [],
                "surface": surface,
                "surface_norm_strict": N.norm_strict(surface),
                "surface_bare": N.bare(surface),
                "lemma": lemma["lemma"],
                "root": lemma["root"],
                "no_root_reason": lemma["no_root_reason"],
                "pos": lemma["pos"],
                "pattern": None,
                "form": None,
                "gloss_shape": gloss_shape(lemma["pos"]),
                "gloss_hint": lemma["gloss_hint"],
                "visible_segments": [
                    {
                        "surface": surface,
                        "role": role_for_pos(lemma["pos"]),
                        "qg_class": qg_class_for_pos(lemma["pos"]),
                        "gloss": lemma["gloss_hint"] or surface,
                    }
                ],
                "features": {},
                "qamus_entry_refs": entry.get("source_keys") or [],
                "source": "qamus_current_authored",
                "source_status": "qamus_current_authored",
                "risk_flags": lemma["risk_flags"],
                "public_boundary": dict(PUBLIC_BOUNDARY),
            }
        )
    return rows


def qword_denominator_rows(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact all-visible-qword denominator rows for Qamus-owned example cards.

    The row preserves bidirectional handles without repeating full translation
    prose or importing any external source payload. It is a denominator and
    routing table, not a deployable hover table.
    """
    rows: list[dict[str, Any]] = []
    for entry in entries:
        for usage_index, usage in enumerate(entry.get("usage") or [], start=1):
            for example_index, example in enumerate(usage.get("examples") or [], start=1):
                card_id = f"{entry['id']}:u{usage_index}:e{example_index}"
                card_text = example.get("ar") or ""
                words = [word for word in card_text.split() if word]
                for qword_index, surface in enumerate(words, start=1):
                    rows.append(
                        {
                            "schema": "qamus/largelexicon-qword-denominator@1",
                            "row_id": f"llx-qword-{entry['id']}-{usage_index:02d}-{example_index:02d}-{qword_index:03d}",
                            "entry_id": entry["id"],
                            "source_keys": entry.get("source_keys") or [],
                            "card_id": card_id,
                            "usage_index": usage_index,
                            "example_index": example_index,
                            "qword_index": qword_index,
                            "visible_surface": surface,
                            "visible_surface_norm_strict": N.norm_strict(surface),
                            "card_text_sha256": sha256_text(card_text),
                            "quran_ref": example.get("ref"),
                            "canonical_quran_loc": None,
                            "canonical_wbw_loc": None,
                            "route": "qamus_executor_source_crosswalk",
                            "status": "denominator_needs_source_address_crosswalk",
                            "source_status": SOURCE_STATUS,
                            "public_boundary": dict(PUBLIC_BOUNDARY),
                            "live_mutation_allowed": False,
                        }
                    )
    return rows


def _source_key_parts(source_key: str) -> tuple[str, int]:
    match = re.match(r"^([pvn])(\d+)$", source_key or "")
    if not match:
        return ("z", 0)
    return (match.group(1), int(match.group(2)))


def _source_key_sort_key(source_key: str) -> tuple[int, int, str]:
    prefix, number = _source_key_parts(source_key)
    prefix_order = {"p": 0, "v": 1, "n": 2}.get(prefix, 9)
    return (prefix_order, number, source_key or "")


def _format_source_key(prefix: str, number: int) -> str:
    width = 3 if number < 1000 else 4
    return f"{prefix}{number:0{width}d}"


def _primary_source_key(row: dict[str, Any]) -> str:
    keys = row.get("source_keys") or []
    if not keys:
        return "z000"
    return sorted(keys, key=_source_key_sort_key)[0]


def qword_shard_label(row: dict[str, Any], shard_size: int = 40) -> tuple[str, dict[str, Any]]:
    source_key = _primary_source_key(row)
    prefix, number = _source_key_parts(source_key)
    if prefix == "z" or number <= 0:
        return "misc", {"prefix": "misc", "start": None, "end": None}
    start = ((number - 1) // shard_size) * shard_size + 1
    end = start + shard_size - 1
    if prefix == "p":
        end = min(end, 100)
    elif prefix == "v":
        end = min(end, 947)
    elif prefix == "n":
        end = min(end, 1045)
    label = f"{_format_source_key(prefix, start)}-{_format_source_key(prefix, end)}"
    return label, {"prefix": prefix, "start": start, "end": end}


def _qword_row_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _source_key_sort_key(_primary_source_key(row)),
        row.get("entry_id") or "",
        row.get("usage_index") or 0,
        row.get("example_index") or 0,
        row.get("qword_index") or 0,
        row.get("row_id") or "",
    )


def write_qword_denominator_shards(
    rows: Iterable[dict[str, Any]], *, shard_size: int = 40, all_entries: Iterable[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Write qword denominator shards plus manifest and entry reverse index.

    This preserves Project-Xanadu-style bidirectionality: the logical table is
    still one addressable denominator, but each entry can jump directly to its
    shard and every shard is hash/count guarded.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ranges: dict[str, dict[str, Any]] = {}
    for row in sorted(rows, key=_qword_row_sort_key):
        label, range_info = qword_shard_label(row, shard_size=shard_size)
        grouped[label].append(row)
        ranges[label] = range_info
    all_entry_lookup = {entry["id"]: entry for entry in (all_entries or [])}
    all_entry_id_set = set(all_entry_lookup)

    if QWORD_DENOMINATOR_FULL.exists():
        QWORD_DENOMINATOR_FULL.unlink()
    QWORD_DENOMINATOR_SHARD_DIR.mkdir(parents=True, exist_ok=True)
    for stale in QWORD_DENOMINATOR_SHARD_DIR.glob("*.jsonl"):
        stale.unlink()

    shards: list[dict[str, Any]] = []
    entry_index: dict[str, dict[str, Any]] = {}
    total_rows = 0
    for label in sorted(grouped, key=lambda value: _source_key_sort_key(value.split("-")[0] if "-" in value else value)):
        shard_rows = grouped[label]
        shard_path = QWORD_DENOMINATOR_SHARD_DIR / f"{label}.jsonl"
        write_jsonl(shard_path, shard_rows)
        total_rows += len(shard_rows)
        entry_ids = sorted({row["entry_id"] for row in shard_rows})
        source_keys = sorted({_primary_source_key(row) for row in shard_rows}, key=_source_key_sort_key)
        for entry_id in entry_ids:
            rows_for_entry = [row for row in shard_rows if row["entry_id"] == entry_id]
            entry_index[entry_id] = {
                "path": repo_rel(shard_path),
                "row_count": len(rows_for_entry),
                "source_keys": rows_for_entry[0].get("source_keys") or [],
                "first_row_id": rows_for_entry[0].get("row_id"),
                "last_row_id": rows_for_entry[-1].get("row_id"),
            }
        shards.append(
            {
                "path": repo_rel(shard_path),
                "schema": "qamus/largelexicon-qword-denominator@1",
                "row_count": len(shard_rows),
                "sha256": sha256_file(shard_path),
                "first_row_id": shard_rows[0].get("row_id"),
                "last_row_id": shard_rows[-1].get("row_id"),
                "source_key_range": ranges[label],
                "first_source_key": source_keys[0] if source_keys else None,
                "last_source_key": source_keys[-1] if source_keys else None,
                "entry_count": len(entry_ids),
            }
        )

    common_freshness = freshness(status="active", stale_after="qamus_entries_or_largelexicon_schema_change")
    entries_with_rows = set(entry_index)
    entries_without_rows = sorted(all_entry_id_set - entries_with_rows)
    source_card_repairs = []
    for entry_id in entries_without_rows:
        entry = all_entry_lookup.get(entry_id) or {}
        source_card_repairs.append(
            {
                "schema": "qamus/largelexicon-qword-source-card-repair@1",
                "entry_id": entry_id,
                "source_keys": entry.get("source_keys") or [],
                "headword": entry.get("headword"),
                "section": entry.get("section"),
                "forms": forms_for_entry(entry) if entry else [],
                "total_uses": entry.get("total_uses"),
                "repair_hint": next(
                    (
                        KNOWN_QWORD_SOURCE_CARD_REPAIR_HINTS[source_key]
                        for source_key in (entry.get("source_keys") or [])
                        if source_key in KNOWN_QWORD_SOURCE_CARD_REPAIR_HINTS
                    ),
                    None,
                ),
                "reason": "qamus_current_entry_has_no_usage_example_rows_for_qword_denominator",
                "source_status": SOURCE_STATUS,
                "public_boundary": dict(PUBLIC_BOUNDARY),
                "live_mutation_allowed": False,
                "next_action": "repair source-card/example edge from source photo or canonical source, then regenerate qword denominator shards",
            }
        )
    source_card_repair_obj = {
        "schema": "qamus/largelexicon-qword-source-card-repair-list@1",
        **common_freshness,
        "table_id": "qamus-qword-denominator",
        "row_count": len(source_card_repairs),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "repairs": source_card_repairs,
    }
    write_json(QWORD_DENOMINATOR_SOURCE_REPAIR, source_card_repair_obj)
    manifest = {
        "schema": "qamus/largelexicon-qword-denominator-manifest@1",
        **common_freshness,
        "table_id": "qamus-qword-denominator",
        "table_schema": "qamus/largelexicon-qword-denominator@1",
        "storage": "sharded_jsonl_manifest",
        "primary_key": "row_id",
        "row_count": total_rows,
        "shard_count": len(shards),
        "qamus_entry_count": len(all_entry_id_set) if all_entry_id_set else len(entries_with_rows),
        "entries_with_qword_rows": len(entries_with_rows),
        "entries_without_qword_rows": entries_without_rows,
        "shard_strategy": f"qamus_source_key_prefix_ordinal_ranges_{shard_size}",
        "entry_index_path": repo_rel(QWORD_DENOMINATOR_ENTRY_INDEX),
        "source_card_repair_path": repo_rel(QWORD_DENOMINATOR_SOURCE_REPAIR),
        "legacy_monolith_replaced": repo_rel(QWORD_DENOMINATOR_FULL),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "claim_boundary": "Source-clean Qamus qword denominator only; not live Qamus progress.",
        "bidirectional_contract": {
            "forward_keys": [
                "entry_id",
                "source_keys",
                "card_id",
                "usage_index",
                "example_index",
                "qword_index",
                "visible_surface",
                "quran_ref",
            ],
            "reverse_keys": [
                "row_id",
                "entry_id",
                "card_id",
                "card_text_sha256",
            ],
            "crosswalk_keys": [
                "canonical_quran_loc",
                "canonical_wbw_loc",
                "route",
                "status",
            ],
        },
        "shards": shards,
    }
    entry_index_obj = {
        "schema": "qamus/largelexicon-qword-entry-shard-index@1",
        **common_freshness,
        "table_id": "qamus-qword-denominator",
        "manifest_path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
        "entry_count": len(entry_index),
        "qamus_entry_count": len(all_entry_id_set) if all_entry_id_set else len(entries_with_rows),
        "entries_with_qword_rows": len(entries_with_rows),
        "entries_without_qword_rows": entries_without_rows,
        "row_count": total_rows,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "entries": dict(sorted(entry_index.items())),
    }
    write_json(QWORD_DENOMINATOR_MANIFEST, manifest)
    write_json(QWORD_DENOMINATOR_ENTRY_INDEX, entry_index_obj)
    return manifest


def full_table_allowlist() -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA_PREFIX}/source-clean-table-allowlist@1",
        **freshness(status="active", stale_after="qamus_entries_or_largelexicon_schema_change"),
        "claim_boundary": (
            "Only source-clean Qamus-authored generated fact tables are committed. "
            "Raw QAC/MCP/Quran.com/Tafsir payloads remain private evidence/cache data."
        ),
        "runtime_dependency_policy": "dependency_free; no external package or live API required at parse time",
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "tables": [
            {
                "path": repo_rel(LEMMA_FULL),
                "schema": f"{SCHEMA_PREFIX}/lemma-source@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 2092,
                "source": "qamus_current_authored",
            },
            {
                "path": repo_rel(FORM_FULL),
                "schema": f"{SCHEMA_PREFIX}/form-source@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 7000,
                "source": "qamus_current_authored",
            },
            {
                "path": repo_rel(STEM_FULL),
                "schema": f"{SCHEMA_PREFIX}/stem-source@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 7000,
                "source": "qamus_current_authored",
            },
            {
                "path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
                "schema": "qamus/largelexicon-qword-denominator-manifest@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 100000,
                "source": "qamus_current_authored",
                "storage": "sharded_jsonl_manifest",
                "entry_index_path": repo_rel(QWORD_DENOMINATOR_ENTRY_INDEX),
            },
            {
                "path": repo_rel(QWORD_CROSSWALK_MANIFEST),
                "schema": "qamus/largelexicon-qword-crosswalk-manifest@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 100000,
                "source": "qamus_current_authored",
                "storage": "sharded_jsonl_manifest",
                "denominator_manifest_path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
            },
        ],
        "private_only_sources": [
            "qac_raw_tsv",
            "mcp_raw_response",
            "quran_foundation_raw_response",
            "quran_com_raw_response",
            "source_photo_or_ocr_dump",
        ],
    }


def role_for_pos(pos: str) -> str:
    return {
        "particle": "function_token",
        "verb": "verb_stem",
        "proper_noun": "proper_name_host",
        "noun": "noun_host",
    }.get(pos, "surface_host")


def gloss_shape(pos: str) -> str:
    return {
        "particle": "function_token_requires_nahw",
        "verb": "form_sensitive_verb",
        "proper_noun": "proper_name",
        "noun": "nominal",
    }.get(pos, "surface_candidate")


def iter_entries(path: Path = QAMUS_ENTRIES) -> list[dict[str, Any]]:
    return read_jsonl(path)


def inventory(entries: list[dict[str, Any]]) -> dict[str, Any]:
    pos_counts = Counter(section_to_pos(e.get("section", ""), e.get("tags") or []) for e in entries)
    form_counts = [len(forms_for_entry(e)) for e in entries]
    empty_root = sum(1 for e in entries if not (e.get("root") or "").strip())
    return {
        "schema": f"{SCHEMA_PREFIX}/source-inventory@1",
        **freshness(),
        "source_files": {
            "entries": str(QAMUS_ENTRIES.relative_to(ROOT)),
            "entries_min": str(QAMUS_ENTRIES_MIN.relative_to(ROOT)),
        },
        "counts": {
            "entries": len(entries),
            "empty_root_entries": empty_root,
            "rooted_entries": len(entries) - empty_root,
            "listed_forms": sum(form_counts),
            "max_forms_per_entry": max(form_counts) if form_counts else 0,
        },
        "pos_counts": dict(sorted(pos_counts.items())),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "claim_boundary": "Qamus-authored source inventory only; not a general Arabic parser, not live Qamus progress.",
    }


def public_boundary_errors(row: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    boundary = row.get("public_boundary") or {}
    for key, value in PUBLIC_BOUNDARY.items():
        if boundary.get(key) != value:
            errors.append(f"{label}: public_boundary.{key} must be {value!r}")
    text = json.dumps(row, ensure_ascii=False).lower()
    for forbidden in FORBIDDEN_PUBLIC_SUBSTRINGS:
        if forbidden in text:
            errors.append(f"{label}: forbidden public/source leak substring {forbidden!r}")
    return errors
