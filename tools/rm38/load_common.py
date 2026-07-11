from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable

from tools.rm38.pins import verify_pinned_file


def load_records(
    path: Path,
    pin: dict[str, Any],
    project: Callable[[dict[str, Any]], dict[str, Any]],
) -> list[dict[str, Any]]:
    verify_pinned_file(path, pin)
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    elif suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = payload if isinstance(payload, list) else payload.get("rows", [])
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(8192)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            except csv.Error:
                dialect = csv.excel_tab if suffix in {".tsv", ".tab"} else csv.excel
            rows = list(csv.DictReader(handle, dialect=dialect))
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"source must contain row objects: {path}")
    return [project(row) for row in rows]


def first(row: dict[str, Any], *names: str) -> Any:
    by_key = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = by_key.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def normalized_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    aliases = {
        "surface": ("surface", "uthmani", "uthmani_word", "word", "token", "arabic"),
        "unit_id": ("unit_id", "ayah_ref", "verse_ref", "location", "verse"),
        "token_id": ("token_id", "word_id", "id", "location"),
        "pos": ("pos", "pos_tag", "part_of_speech", "tag"),
        "lemma": ("lemma", "lemma_ar", "lexeme"),
        "root": ("root", "root_ar"),
        "governor": ("governor", "head", "head_id", "governor_id"),
        "relation": ("relation", "deprel", "dependency_relation"),
        "syntax_provenance": ("syntax_provenance", "parse_provenance", "provenance"),
    }
    for canonical, names in aliases.items():
        value = first(row, *names)
        if value is not None:
            output[canonical] = value
    if "unit_id" not in output:
        surah = first(row, "surah", "sura", "chapter")
        ayah = first(row, "ayah", "aya", "verse_number")
        if surah is not None and ayah is not None:
            output["unit_id"] = f"quran:{surah}:{ayah}"
    elif not str(output["unit_id"]).startswith("quran:"):
        parts = str(output["unit_id"]).replace("(", "").replace(")", "").split(":")
        if len(parts) >= 2 and all(part.isdigit() for part in parts[:2]):
            output["unit_id"] = f"quran:{parts[0]}:{parts[1]}"
    features = {}
    for feature in ("case", "mood", "voice", "aspect", "person", "number", "gender", "state",
                    "verb_form", "derivative_type"):
        value = first(row, feature, f"feature_{feature}", f"morph_{feature}")
        if value is not None:
            features[feature] = value
    if features:
        output["features"] = features
    segments = first(row, "segments", "segmentation", "morphemes")
    if isinstance(segments, str) and any(separator in segments for separator in ("+", "|")):
        separator = "+" if "+" in segments else "|"
        output["segments"] = [part for part in segments.split(separator) if part]
    return output
