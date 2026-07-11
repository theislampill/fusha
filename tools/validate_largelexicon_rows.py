#!/usr/bin/env python3
"""Validate the five largelexicon row families and build their release manifest.

The repository intentionally has no third-party ``jsonschema`` dependency. This
validator implements only the Draft 2020-12 keywords used by the five RM-22
schemas. It never rewrites source tables; current @1 migration defects are
counted by family and defect class.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
RELEASE_PATH = ROOT / "qamus" / "indexes" / "largelexicon" / "RELEASE.json"
ENTRIES_PATH = ROOT / "qamus" / "data" / "current" / "entries.jsonl"
HYGIENE_REPORT_PATH = ROOT / "qamus" / "indexes" / "largelexicon" / "hygiene-report.json"
VALIDATOR_VERSION = "1.0.0"
VALIDATOR_TOOL = "tools/validate_largelexicon_rows.py"
REPORT_SCHEMA = "qamus/largelexicon-row-validation-report@1"
RELEASE_SCHEMA = "qamus/largelexicon-release@1"
ROW_CONSTANT_FIELDS = frozenset(
    {
        "live_mutation_allowed",
        "public_boundary",
        "resolution_normalizer",
        "resolution_source",
        "resolution_wbw_lookup_built_at",
        "resolution_wbw_lookup_sha256",
        "source",
        "source_status",
    }
)


@dataclass(frozen=True)
class Family:
    name: str
    schema_path: str
    row_path: str | None = None
    manifest_path: str | None = None


FAMILIES = (
    Family(
        "lemma-source",
        "qamus/schemas/largelexicon-lemma-source.schema.json",
        row_path="fusha/lexicon/largelexicon/lemma-source.full.jsonl",
    ),
    Family(
        "form-source",
        "qamus/schemas/largelexicon-form-source.schema.json",
        row_path="fusha/lexicon/largelexicon/form-source.full.jsonl",
    ),
    Family(
        "stem-source",
        "qamus/schemas/largelexicon-stem-source.schema.json",
        row_path="fusha/morphology/data/largelexicon-stems.full.jsonl",
    ),
    Family(
        "qword-denominator",
        "qamus/schemas/largelexicon-qword-denominator.schema.json",
        manifest_path="qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json",
    ),
    Family(
        "qword-crosswalk",
        "qamus/schemas/largelexicon-qword-crosswalk.schema.json",
        manifest_path="qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json",
    ),
)


def review_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def family_paths(family: Family) -> list[Path]:
    if family.row_path:
        return [ROOT / family.row_path]
    manifest = read_json(ROOT / str(family.manifest_path))
    return [ROOT / shard["path"] for shard in manifest["shards"]]


def iter_family_rows(family: Family) -> Iterator[tuple[str, int, dict[str, Any]]]:
    for path in family_paths(family):
        relative = path.relative_to(ROOT).as_posix()
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if line.strip():
                    yield relative, line_no, json.loads(line)


def logical_table_sha256(family: Family) -> str:
    digest = hashlib.sha256()
    for path in family_paths(family):
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def type_matches(value: Any, expected: str | list[str]) -> bool:
    expected_types = [expected] if isinstance(expected, str) else expected
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return any(checks[item](value) for item in expected_types)


def schema_errors(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    inherited_defect: str | None = None,
) -> list[dict[str, str]]:
    defect = schema.get("x-defect-family", inherited_defect)
    errors: list[dict[str, str]] = []

    def add(keyword: str, message: str, *, error_path: str = path) -> None:
        errors.append(
            {
                "defect_family": defect or classify_keyword(keyword, error_path, message),
                "keyword": keyword,
                "message": message,
                "path": error_path,
            }
        )

    if "type" in schema and not type_matches(value, schema["type"]):
        add("type", f"expected {schema['type']!r}, got {type(value).__name__}")
        return errors
    if "const" in schema and value != schema["const"]:
        add("const", f"expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        add("enum", f"value {value!r} is not in enum")
    if "pattern" in schema and isinstance(value, str) and re.search(schema["pattern"], value) is None:
        add("pattern", f"value does not match {schema['pattern']!r}")
    if "minLength" in schema and isinstance(value, str) and len(value) < schema["minLength"]:
        add("minLength", f"string has fewer than {schema['minLength']} characters")
    if "minimum" in schema and isinstance(value, (int, float)) and value < schema["minimum"]:
        add("minimum", f"number is below {schema['minimum']}")
    if "minItems" in schema and isinstance(value, list) and len(value) < schema["minItems"]:
        add("minItems", f"array has fewer than {schema['minItems']} items")
    if "maxItems" in schema and isinstance(value, list) and len(value) > schema["maxItems"]:
        add("maxItems", f"array has more than {schema['maxItems']} items")
    if "minProperties" in schema and isinstance(value, dict) and len(value) < schema["minProperties"]:
        add("minProperties", f"object has fewer than {schema['minProperties']} properties")

    for subschema in schema.get("allOf", []):
        errors.extend(schema_errors(value, subschema, path, defect))
    if "anyOf" in schema:
        alternatives = [schema_errors(value, item, path, defect) for item in schema["anyOf"]]
        if all(alternative for alternative in alternatives):
            add("anyOf", "value does not satisfy any allowed alternative")
    if "not" in schema and not schema_errors(value, schema["not"], path, defect):
        add("not", "value satisfies a forbidden schema")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                add("required", f"missing required property {required!r}", error_path=f"{path}.{required}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    family = "row_constant" if key in ROW_CONSTANT_FIELDS else "additional_property"
                    errors.append(
                        {
                            "defect_family": family,
                            "keyword": "additionalProperties",
                            "message": f"additional property {key!r} is not allowed",
                            "path": f"{path}.{key}",
                        }
                    )
        for key, subschema in properties.items():
            if key in value:
                errors.extend(schema_errors(value[key], subschema, f"{path}.{key}", defect))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]", defect))
    return errors


def classify_keyword(keyword: str, path: str, message: str) -> str:
    if path == "$.schema" and keyword == "const":
        return "schema_version"
    if path == "$.risk_flags" and keyword == "maxItems":
        return "risk_flags"
    if keyword == "required":
        return "required_field"
    if keyword == "type":
        return "type"
    if keyword == "additionalProperties":
        return "additional_property"
    return "schema_constraint"


def validate_family(family: Family) -> dict[str, Any]:
    schema = read_json(ROOT / family.schema_path)
    defect_counts: Counter[str] = Counter()
    row_count = 0
    violation_count = 0
    for _path, _line_no, row in iter_family_rows(family):
        row_count += 1
        errors = schema_errors(row, schema)
        if errors:
            violation_count += 1
            defect_counts.update({error["defect_family"] for error in errors})
    pass_count = row_count - violation_count
    result: dict[str, Any] = {
        "defect_family_counts": dict(sorted(defect_counts.items())),
        "family": family.name,
        "pass": {"denominator": row_count, "numerator": pass_count},
        "row_count": row_count,
        "schema_path": family.schema_path,
        "violation": {"denominator": row_count, "numerator": violation_count},
    }
    if family.row_path:
        result["table_path"] = family.row_path
    else:
        result["manifest_path"] = family.manifest_path
        result["shard_count"] = len(family_paths(family))
    return result


def build_report() -> dict[str, Any]:
    families = [validate_family(family) for family in FAMILIES]
    row_count = sum(item["row_count"] for item in families)
    violation_count = sum(item["violation"]["numerator"] for item in families)
    hygiene = read_json(HYGIENE_REPORT_PATH)
    return {
        "audited_expectations": {
            "rm23_audited_counts": hygiene["audited_counts"],
            "rm23_head_measurements": hygiene["actual_counts"],
        },
        "families": families,
        "ok": violation_count == 0,
        "schema": REPORT_SCHEMA,
        "totals": {
            "pass": {"denominator": row_count, "numerator": row_count - violation_count},
            "row_count": row_count,
            "violation": {"denominator": row_count, "numerator": violation_count},
        },
        "validator": {"tool": VALIDATOR_TOOL, "version": VALIDATOR_VERSION},
    }


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def count_field(path: Path, field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                counts[json.loads(line).get(field)] += 1
    return dict(sorted(counts.items()))


def build_release(built_at: str, report: dict[str, Any]) -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", built_at):
        raise ValueError("--built-at must be an explicit UTC timestamp like 2026-07-11T14:05:10Z")
    reports = {item["family"]: item for item in report["families"]}
    tables: dict[str, Any] = {}
    for family in FAMILIES:
        validation = reports[family.name]
        _path, _line_no, first_row = next(iter_family_rows(family))
        item: dict[str, Any] = {
            "row_count": validation["row_count"],
            "source_row_schema": first_row.get("schema"),
            "schema_path": family.schema_path,
            "sha256": logical_table_sha256(family),
            "sha256_scope": "exact JSONL bytes in manifest order",
            "target_row_schema": read_json(ROOT / family.schema_path)["properties"]["schema"]["const"],
            "validation": {
                "defect_family_counts": validation["defect_family_counts"],
                "pass_rows": validation["pass"]["numerator"],
                "violation_rows": validation["violation"]["numerator"],
            },
        }
        if family.row_path:
            item.update({"path": family.row_path, "storage": "jsonl"})
        else:
            item.update(
                {
                    "manifest_path": family.manifest_path,
                    "shard_count": validation["shard_count"],
                    "storage": "sharded_jsonl_manifest",
                }
            )
        tables[family.name] = item
    lemma_path = ROOT / str(FAMILIES[0].row_path)
    source_pos = count_field(ENTRIES_PATH, "section")
    generated_pos = count_field(lemma_path, "pos")
    return {
        "built_at": built_at,
        "generator": {"tool": VALIDATOR_TOOL, "version": VALIDATOR_VERSION},
        "input": {
            "path": ENTRIES_PATH.relative_to(ROOT).as_posix(),
            "row_count": count_jsonl(ENTRIES_PATH),
            "sha256": sha256_file(ENTRIES_PATH),
        },
        "manifest_constants": {
            "live_mutation_allowed": False,
            "public_boundary": {"kind": "authored", "lang": "en", "src": "qamus"},
            "source_status": "qamus_current_authored",
        },
        "pos_mapping": {
            "disclosure": (
                "Re-measured at this release: generated lemma POS maps 970 verb and 966 noun, "
                "while source section/manifests map 947 verb and 1045 noun. The difference is "
                "classification, including 56 proper_noun rows, not entry-count drift."
            ),
            "generated_lemma_pos_counts": generated_pos,
            "source_section_manifest_counts": source_pos,
        },
        "schema": RELEASE_SCHEMA,
        "tables": tables,
        "validation_expectations": report["audited_expectations"],
        "validation_totals": report["totals"],
    }


def good_rows() -> dict[str, dict[str, Any]]:
    entry_id = "0123456789ab"
    surface = "كَتَبَ"
    root = "ك ت ب"
    return {
        "lemma-source": {
            "schema": "fusha/largelexicon/lemma-source@2",
            "entry_id": entry_id,
            "source_keys": ["v001"],
            "lemma": surface,
            "root": root,
            "no_root_reason": None,
            "pos": "verb",
            "forms": [surface],
            "gloss_hint": "to write",
            "risk_flags": [],
        },
        "form-source": {
            "schema": "fusha/largelexicon/form-source@2",
            "form_id": f"llx_form_{entry_id}_000",
            "entry_id": entry_id,
            "source_keys": ["v001"],
            "surface": surface,
            "surface_norm_strict": "كتب",
            "surface_bare": "كتب",
            "lemma": surface,
            "root": root,
            "no_root_reason": None,
            "pos": "verb",
            "risk_flags": [],
        },
        "stem-source": {
            "schema": "fusha/largelexicon/stem-source@2",
            "stem_id": f"llx_{entry_id}_000",
            "generation_key": f"qamus:{entry_id}:000",
            "entry_id": entry_id,
            "source_keys": ["v001"],
            "surface": surface,
            "surface_norm_strict": "كتب",
            "surface_bare": "كتب",
            "lemma": surface,
            "root": root,
            "no_root_reason": None,
            "pos": "verb",
            "pattern": "فَعَلَ",
            "form": "I",
            "features": {"aspect": "perfect"},
            "gloss_shape": "form_sensitive_verb",
            "gloss_hint": "to write",
            "visible_segments": [
                {"surface": surface, "role": "verb_stem", "qg_class": "qg-verb-stem", "gloss": "to write"}
            ],
            "qamus_entry_refs": ["v001"],
            "risk_flags": [],
        },
        "qword-denominator": {
            "schema": "qamus/largelexicon-qword-denominator@2",
            "row_id": f"llx-qword-{entry_id}-01-01-001",
            "entry_id": entry_id,
            "source_keys": ["v001"],
            "card_id": f"{entry_id}:u1:e1",
            "usage_index": 1,
            "example_index": 1,
            "qword_index": 1,
            "visible_surface": surface,
            "visible_surface_norm_strict": "كتب",
            "card_text_sha256": "0" * 64,
            "quran_ref": "2:1",
            "canonical_quran_loc": None,
            "canonical_wbw_loc": None,
            "route": "review",
            "status": "pending",
        },
        "qword-crosswalk": {
            "schema": "qamus/largelexicon-qword-crosswalk@2",
            "row_id": f"llx-crosswalk-llx-qword-{entry_id}-01-01-001",
            "qword_row_id": f"llx-qword-{entry_id}-01-01-001",
            "entry_id": entry_id,
            "source_keys": ["v001"],
            "card_id": f"{entry_id}:u1:e1",
            "usage_index": 1,
            "example_index": 1,
            "qword_index": 1,
            "visible_surface": surface,
            "visible_surface_norm_strict": "كتب",
            "quran_ref": "2:1",
            "canonical_quran_loc": None,
            "canonical_wbw_loc": None,
            "match_status": "pending",
            "status": "pending",
            "next_action": "review",
            "packet_class": None,
            "terminal_gate_code": None,
            "transclusion_route": "review",
            "source_dependencies": [{"kind": "entry", "id": entry_id}],
        },
    }


def run_self_test() -> int:
    schemas = {family.name: read_json(ROOT / family.schema_path) for family in FAMILIES}
    fixtures = good_rows()
    assertions = 0
    for family in FAMILIES:
        good = fixtures[family.name]
        assert not schema_errors(good, schemas[family.name]), family.name
        assertions += 1

        bad_surface = json.loads(json.dumps(good, ensure_ascii=False))
        surface_field = "lemma" if family.name == "lemma-source" else (
            "visible_surface" if family.name.startswith("qword-") else "surface"
        )
        bad_surface[surface_field] = "كَتَبَ كِتَابًا"
        surface_errors = schema_errors(bad_surface, schemas[family.name])
        assert any(error["defect_family"] == "surface_shape" for error in surface_errors), family.name
        assertions += 1

        escaped_surface = json.loads(json.dumps(bad_surface, ensure_ascii=False))
        if family.name == "lemma-source":
            escaped_surface["lemma_is_multiword"] = True
        else:
            escaped_surface["surface_is_multiword"] = True
        escaped_surface["multiword_reason"] = "intentional phrase fixture"
        assert not schema_errors(escaped_surface, schemas[family.name]), family.name
        assertions += 1

        bad_version = json.loads(json.dumps(good, ensure_ascii=False))
        bad_version["schema"] = bad_version["schema"].replace("@2", "@1")
        version_errors = schema_errors(bad_version, schemas[family.name])
        assert any(error["defect_family"] == "schema_version" for error in version_errors), family.name
        assertions += 1

        bad_risk = json.loads(json.dumps(good, ensure_ascii=False))
        bad_risk["risk_flags"] = ["quarantined_fixture"]
        risk_errors = schema_errors(bad_risk, schemas[family.name])
        assert any(error["defect_family"] == "risk_flags" for error in risk_errors), family.name
        assertions += 1

        bad_constant = json.loads(json.dumps(good, ensure_ascii=False))
        bad_constant["public_boundary"] = {"src": "qamus", "kind": "authored", "lang": "en"}
        constant_errors = schema_errors(bad_constant, schemas[family.name])
        assert any(error["defect_family"] == "row_constant" for error in constant_errors), family.name
        assertions += 1

    for family_name in ("lemma-source", "form-source", "stem-source"):
        bad_root = json.loads(json.dumps(fixtures[family_name], ensure_ascii=False))
        bad_root["root"] = "كَتَبَ"
        bad_root["no_root_reason"] = None
        root_errors = schema_errors(bad_root, schemas[family_name])
        assert any(error["defect_family"] == "root_shape_or_reason" for error in root_errors), family_name
        assertions += 1

        no_root = json.loads(json.dumps(fixtures[family_name], ensure_ascii=False))
        no_root["root"] = None
        no_root["no_root_reason"] = "fixture_has_no_root"
        assert not schema_errors(no_root, schemas[family_name]), family_name
        assertions += 1

    bad_stem = json.loads(json.dumps(fixtures["stem-source"], ensure_ascii=False))
    bad_stem["features"] = {}
    bad_stem["form"] = None
    bad_stem["pattern"] = None
    stem_errors = schema_errors(bad_stem, schemas["stem-source"])
    assert any(error["defect_family"] == "stem_annotation_completeness" for error in stem_errors)
    assertions += 1

    absent_stem = json.loads(json.dumps(fixtures["stem-source"], ensure_ascii=False))
    for field in ("pattern", "form", "features"):
        absent_stem.pop(field)
    assert not schema_errors(absent_stem, schemas["stem-source"])
    assertions += 1

    print(
        review_json(
            {
                "assertions": assertions,
                "families": [family.name for family in FAMILIES],
                "ok": True,
                "schema": "qamus/largelexicon-row-validator-self-test@1",
            }
        ),
        end="",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--built-at")
    parser.add_argument("--write-release", action="store_true")
    parser.add_argument("--check-release", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if (args.write_release or args.check_release) and not args.built_at:
        parser.error("--built-at is required with --write-release or --check-release")
    report = build_report()
    if args.write_release or args.check_release:
        release = build_release(args.built_at, report)
        expected = review_json(release)
        if args.write_release:
            RELEASE_PATH.write_text(expected, encoding="utf-8", newline="\n")
            report["release_ok"] = True
        if args.check_release:
            if not RELEASE_PATH.exists() or RELEASE_PATH.read_text(encoding="utf-8") != expected:
                report["release_error"] = "RELEASE.json is missing, stale, or non-deterministic"
                report["ok"] = False
                report["release_ok"] = False
            else:
                report["release_ok"] = True
    print(review_json(report), end="")
    if args.write_release or args.check_release:
        return 0 if report.get("release_ok") else 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
