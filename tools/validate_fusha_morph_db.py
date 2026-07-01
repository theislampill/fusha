"""Validate the dependency-free Fusha morphology database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MORPH_ROOT = ROOT / "fusha" / "morphology"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def _id_map(rows: list[dict[str, Any]], key: str, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not value:
            errors.append(f"{label}:{row.get('_line_no')}: missing {key}")
            continue
        if value in seen:
            errors.append(f"{label}:{row.get('_line_no')}: duplicate {key} {value}")
        seen[value] = row
    return seen


def validate(root: Path = MORPH_ROOT) -> list[str]:
    errors: list[str] = []
    data = root / "data"
    required_files = {
        "prefixes": data / "prefixes.jsonl",
        "stems": data / "stems.sample.jsonl",
        "suffixes": data / "suffixes.jsonl",
        "compat_prefix_stem": data / "compatibility-prefix-stem.jsonl",
        "compat_stem_suffix": data / "compatibility-stem-suffix.jsonl",
        "patterns": data / "patterns.jsonl",
        "particles": data / "particles.jsonl",
    }
    missing = [name for name, path in required_files.items() if not path.exists()]
    if missing:
        return [f"missing morphology data file: {name}" for name in missing]

    prefixes = read_jsonl(required_files["prefixes"])
    stems = read_jsonl(required_files["stems"])
    suffixes = read_jsonl(required_files["suffixes"])
    patterns = read_jsonl(required_files["patterns"])
    particles = read_jsonl(required_files["particles"])
    prefix_stem = read_jsonl(required_files["compat_prefix_stem"])
    stem_suffix = read_jsonl(required_files["compat_stem_suffix"])

    prefix_by_id = _id_map(prefixes, "prefix_id", "prefixes", errors)
    stem_by_id = _id_map(stems, "stem_id", "stems", errors)
    suffix_by_id = _id_map(suffixes, "suffix_id", "suffixes", errors)
    _id_map(patterns, "pattern_id", "patterns", errors)
    _id_map(particles, "particle_id", "particles", errors)

    for row in prefixes:
        for key in ["surface", "kind", "qg_default_class", "compat_tags", "source"]:
            if key not in row:
                errors.append(f"prefixes:{row.get('_line_no')}: missing {key}")
        if row.get("source") != "repo_authored":
            errors.append(f"prefixes:{row.get('_line_no')}: source must be repo_authored")

    for row in stems:
        for key in ["surface", "pos", "gloss_shape", "visible_segments", "source"]:
            if key not in row:
                errors.append(f"stems:{row.get('_line_no')}: missing {key}")
        if row.get("source") != "repo_authored":
            errors.append(f"stems:{row.get('_line_no')}: source must be repo_authored")
        surface = "".join(seg.get("surface", "") for seg in row.get("visible_segments", []))
        if surface and surface != row.get("surface"):
            errors.append(f"stems:{row.get('_line_no')}: visible segments do not concatenate to surface")
        if row.get("pos") == "proper_name" and row.get("root"):
            errors.append(f"stems:{row.get('_line_no')}: proper_name must not invent a root")

    for row in suffixes:
        for key in ["surface", "kind", "qg_default_class", "compat_tags", "source"]:
            if key not in row:
                errors.append(f"suffixes:{row.get('_line_no')}: missing {key}")
        if row.get("source") != "repo_authored":
            errors.append(f"suffixes:{row.get('_line_no')}: source must be repo_authored")

    for row in prefix_stem:
        if row.get("prefix_id") not in prefix_by_id:
            errors.append(f"compat-prefix-stem:{row.get('_line_no')}: unknown prefix_id {row.get('prefix_id')}")
        if row.get("stem_id") not in stem_by_id:
            errors.append(f"compat-prefix-stem:{row.get('_line_no')}: unknown stem_id {row.get('stem_id')}")

    for row in stem_suffix:
        if row.get("stem_id") not in stem_by_id:
            errors.append(f"compat-stem-suffix:{row.get('_line_no')}: unknown stem_id {row.get('stem_id')}")
        if row.get("suffix_id") not in suffix_by_id:
            errors.append(f"compat-stem-suffix:{row.get('_line_no')}: unknown suffix_id {row.get('suffix_id')}")

    required_surfaces = {"لَهُمْ", "تَعْبُدُوا۟", "ٱلْمُبْطِلُونَ", "أَيَّانَ", "وَجِبْرِيلَ"}
    represented = {row["surface"] for row in stems} | {row["surface"] for row in particles}
    missing_surfaces = sorted(required_surfaces - represented)
    if missing_surfaces:
        errors.append(f"required smoke surfaces missing: {missing_surfaces}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Fusha morphology DB.")
    parser.add_argument("--root", default=str(MORPH_ROOT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.root))
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "root": args.root}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
