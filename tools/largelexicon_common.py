"""Shared helpers for the largelexicon implementation lane.

The largelexicon lane is source-addressed and source-clean. It expands from the
repo-owned Qamus dataset, emits reviewable samples in git, and writes full
generated outputs only when the caller asks for them. It does not touch live
Qamus and does not import external corpus text.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
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
PARSER_EVAL_DIR = ROOT / "fusha" / "parser" / "eval"
PARSER_MODEL_CARD_DIR = ROOT / "fusha" / "parser" / "model-cards"
REPORT_DIR = ROOT / "qamus" / "reports"

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
                "risk_flags": lemma["risk_flags"],
                "public_boundary": dict(PUBLIC_BOUNDARY),
            }
        )
    return rows


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
