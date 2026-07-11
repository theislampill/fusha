#!/usr/bin/env python3
"""Validate and report fail-safe hygiene for Qamus largelexicon ingest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import largelexicon_common as common  # noqa: E402

AUTHORITATIVE_BASELINE_SHA = "576627cb8be1eadffe5e38f43f11e5df736f160e"
BASELINE_ACCEPTED_IDENTITY_ROWS = 88347
BASELINE_ACCEPTED_IDENTITY_SHA256 = "b53b1f9728c47afc47567b7b6c56103c79dc022330bd154dfc410016df3aed5d"
GENERATOR = "python tools/validate_largelexicon_hygiene.py --write"


class HygieneSelfTest(unittest.TestCase):
    def test_root_shape_and_build_normalization(self) -> None:
        self.assertEqual(common.normalize_build_root("ص هـ ر"), "ص ه ر")
        self.assertEqual(common.normalize_build_root("ر أ ى"), "ر أ ي")
        self.assertTrue(common.is_root_shape("ص ه ر"))
        self.assertFalse(common.is_root_shape("خَبَالًا"))

    def test_dual_roots_and_malformed_root_route(self) -> None:
        self.assertEqual(common.root_hygiene("ز ك و / ز ك ي")["roots"], ["ز ك و", "ز ك ي"])
        malformed = common.root_hygiene("س ن ن / و / ه")
        self.assertEqual(malformed["roots"], [])
        self.assertIn("malformed_root", malformed["risk_flags"])
        self.assertEqual(malformed["no_root_reason"], "malformed_root")

    def test_surface_gate_and_alternate_split(self) -> None:
        self.assertEqual(common.split_surface_alternates("نَفْس / النَّفْس"), ["نَفْس", "النَّفْس"])
        self.assertTrue(common.is_single_arabic_token("شَطْـَٔهُ"))
        self.assertFalse(common.is_single_arabic_token("حَاشَ لِلَّه"))

    def test_gloss_bearing_surface_is_quarantined(self) -> None:
        result = common.surface_hygiene("قَبُول | acceptance")
        self.assertEqual(result["surfaces"], [])
        self.assertEqual(result["route"], "entry_repair_queue")
        self.assertIn("gloss_bearing_surface", result["risk_flags"])

    def test_range_reference_representation(self) -> None:
        self.assertEqual(
            common.quran_ref_hygiene("69:1-3"),
            {
                "ref": "69:1-3",
                "ref_kind": "range",
                "surah": 69,
                "ayah_start": 1,
                "ayah_end": 3,
                "risk_flags": ["range_reference"],
            },
        )

    def test_norm_homograph_inventory(self) -> None:
        entries = [
            {"id": "a", "root": "ق ل ل", "headword": "قُلَّ", "senses": [], "usage": []},
            {"id": "b", "root": "ق و ل", "headword": "قُلْ", "senses": [], "usage": []},
        ]
        inventory = common.build_homograph_key_inventory(entries)
        self.assertEqual([item["norm_key"] for item in inventory], ["قل"])
        self.assertEqual(inventory[0]["roots"], ["ق ل ل", "ق و ل"])

    def test_inventory_is_deterministic(self) -> None:
        entries = [
            {"id": "b", "root": "ق و ل", "headword": "قُلْ", "senses": [], "usage": []},
            {"id": "a", "root": "ق ل ل", "headword": "قُلَّ", "senses": [], "usage": []},
        ]
        forward = common.build_homograph_key_inventory(entries)
        reverse = common.build_homograph_key_inventory(list(reversed(entries)))
        self.assertEqual(
            json.dumps(forward, ensure_ascii=False, sort_keys=True),
            json.dumps(reverse, ensure_ascii=False, sort_keys=True),
        )

    def test_review_json_is_deterministic(self) -> None:
        left = review_json({"b": 2, "a": ["ي", "ا"]})
        right = review_json({"a": ["ي", "ا"], "b": 2})
        self.assertEqual(left, right)
        self.assertTrue(left.endswith("\n"))


def run_self_test() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HygieneSelfTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def review_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _root_audit(entries: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {
        "dual_root_rows": 0,
        "final_radical_alif_maqsura_normalized": 0,
        "malformed_root_rows": 0,
        "parenthesized_root_rows": 0,
        "raw_root_shape_failures": 0,
        "slash_composite_root_rows": 0,
        "tatweel_heh_root_rows_normalized": 0,
        "verbatim_word_copy_root_rows": 0,
    }
    queue: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda item: item["id"]):
        source = (entry.get("root") or "").strip()
        if not source:
            continue
        result = common.root_hygiene(source)
        if len(result["roots"]) > 1:
            counts["dual_root_rows"] += 1
        components = source.split("/")
        if any(
            common.is_root_shape(" ".join(component.replace("ـ", "").split()))
            and " ".join(component.replace("ـ", "").split()).endswith(" ى")
            for component in components
        ):
            counts["final_radical_alif_maqsura_normalized"] += 1
        if common.is_root_shape(source):
            continue
        counts["raw_root_shape_failures"] += 1
        if "/" in source:
            defect_class = "slash_composite_root"
            counts["slash_composite_root_rows"] += 1
        elif "ـ" in source:
            defect_class = "tatweel_heh_notation"
            counts["tatweel_heh_root_rows_normalized"] += 1
        elif "(" in source or ")" in source:
            defect_class = "parenthesized_root"
            counts["parenthesized_root_rows"] += 1
        else:
            defect_class = "verbatim_word_copy_root"
            counts["verbatim_word_copy_root_rows"] += 1
        if "malformed_root" in result["risk_flags"]:
            counts["malformed_root_rows"] += 1
        queue.append(
            {
                "entry_id": entry["id"],
                "headword": entry.get("headword"),
                "root_source": source,
                "defect_class": defect_class,
                "root": result["root"],
                "roots": result["roots"],
                "no_root_reason": result["no_root_reason"],
                "risk_flags": result["risk_flags"],
                "route": "entry_repair_queue" if result["risk_flags"] else "normalized_at_build_time",
            }
        )
    return counts, queue


def _surface_audit(entries: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {
        "gloss_bearing_surface_rows": 0,
        "non_single_token_surface_rows": 0,
    }
    queue: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda item: item["id"]):
        for source in common.raw_forms_for_entry(entry):
            if common.is_single_arabic_token(source):
                continue
            result = common.surface_hygiene(source)
            flags = common.unique_keep_order(["non_single_token_surface", *result["risk_flags"]])
            counts["non_single_token_surface_rows"] += 1
            if "gloss_bearing_surface" in flags:
                counts["gloss_bearing_surface_rows"] += 1
            queue.append(
                {
                    "entry_id": entry["id"],
                    "surface_source": source,
                    "accepted_surfaces": result["surfaces"],
                    "rejected_parts": result["rejected"],
                    "risk_flags": flags,
                    "route": result["route"],
                }
            )
    queue.sort(key=lambda item: (item["entry_id"], item["surface_source"]))
    return counts, queue


def _range_audit(entries: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    total_references = 0
    excluded_qwords = 0
    queue: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda item: item["id"]):
        for usage_index, usage in enumerate(entry.get("usage") or [], start=1):
            for example_index, example in enumerate(usage.get("examples") or [], start=1):
                total_references += 1
                result = common.quran_ref_hygiene(example.get("ref"))
                if result["ref_kind"] != "range":
                    continue
                qword_count = len([item for item in (example.get("ar") or "").split() if item])
                excluded_qwords += qword_count
                queue.append(
                    {
                        "card_id": f"{entry['id']}:u{usage_index}:e{example_index}",
                        "entry_id": entry["id"],
                        "qword_count_excluded_from_identity_acceptance": qword_count,
                        "ref": result["ref"],
                        "ref_kind": result["ref_kind"],
                        "range": {
                            "surah": result["surah"],
                            "ayah_start": result["ayah_start"],
                            "ayah_end": result["ayah_end"],
                        },
                        "risk_flags": result["risk_flags"],
                        "route": "range_reference_review",
                    }
                )
    return {
        "example_reference_rows": total_references,
        "range_reference_cards": len(queue),
        "range_qword_rows_excluded_from_identity_acceptance": excluded_qwords,
    }, queue


def _accepted_crosswalk_identity() -> dict[str, Any]:
    identities: list[list[Any]] = []
    range_rows = 0
    range_rows_with_identity = 0
    for path in sorted(common.QWORD_CROSSWALK_SHARD_DIR.glob("*.jsonl")):
        for row in common.read_jsonl(path):
            if "-" in str(row.get("quran_ref") or ""):
                range_rows += 1
                range_rows_with_identity += int(bool(row.get("canonical_quran_loc")))
            if not row.get("canonical_quran_loc") or not row.get("canonical_wbw_loc"):
                continue
            identities.append(
                [
                    row.get("row_id"),
                    row.get("entry_id"),
                    row.get("card_id"),
                    row.get("qword_index"),
                    row.get("canonical_quran_loc"),
                    row.get("canonical_wbw_loc"),
                ]
            )
    identities.sort(key=lambda item: item[0] or "")
    text = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in identities)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "row_count": len(identities),
        "sha256": digest,
        "baseline_row_count": BASELINE_ACCEPTED_IDENTITY_ROWS,
        "baseline_sha256": BASELINE_ACCEPTED_IDENTITY_SHA256,
        "unchanged_from_authoritative_baseline": (
            len(identities) == BASELINE_ACCEPTED_IDENTITY_ROWS
            and digest == BASELINE_ACCEPTED_IDENTITY_SHA256
        ),
        "range_crosswalk_rows": range_rows,
        "range_crosswalk_rows_with_accepted_identity": range_rows_with_identity,
    }


def build_artifacts(entries: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    homograph_keys = common.build_homograph_key_inventory(entries)
    root_counts, root_queue = _root_audit(entries)
    surface_counts, surface_queue = _surface_audit(entries)
    range_counts, range_queue = _range_audit(entries)
    identity = _accepted_crosswalk_identity()
    actual_counts = {
        "entries": len(entries),
        **root_counts,
        **surface_counts,
        **range_counts,
        "norm_homograph_keys": len(homograph_keys),
    }
    homograph_payload = {
        "schema": "qamus/largelexicon-homograph-keys@1",
        "generated_by": GENERATOR,
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "source": common.repo_rel(common.QAMUS_ENTRIES),
        "source_sha256": common.sha256_file(common.QAMUS_ENTRIES),
        "normalization": {
            "key_function": "tools.normalize_ar.norm",
            "purpose": "broad recall defeater only; never certifies root, sense, or hover identity",
            "surface_build_normalization": "strip tatweel before generated lookup keys; preserve source/display text",
        },
        "risk_flag": "norm_homograph",
        "key_count": len(homograph_keys),
        "keys": homograph_keys,
    }
    report_payload = {
        "schema": "qamus/largelexicon-hygiene-report@1",
        "generated_by": GENERATOR,
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "source": common.repo_rel(common.QAMUS_ENTRIES),
        "source_sha256": common.sha256_file(common.QAMUS_ENTRIES),
        "mode": "flag_and_report_only_until_authorized_regeneration",
        "normalization_policy": {
            "root_shape_gate": "^[ء-ي]( [ء-ي]){1,4}$",
            "root_tatweel": "strip tatweel at build time, including heh notation هـ -> ه",
            "root_final_radical": "map final-radical ى to ي only for otherwise valid 2-5-radical roots",
            "surface_tatweel": "strip tatweel from generated lookup surfaces only",
            "source_and_display_text": "read-only and byte-preserved",
        },
        "audited_counts": {
            "verbatim_word_copy_root_rows": 118,
            "slash_composite_root_rows": 7,
            "gloss_bearing_surface_rows": 35,
            "non_single_token_surface_rows": 263,
            "range_reference_cards": 16,
            "range_qword_rows_excluded_from_identity_acceptance": 147,
            "norm_homograph_keys_minimum": 23,
        },
        "actual_counts": actual_counts,
        "accepted_crosswalk_identity": identity,
        "homograph_inventory": {
            "path": common.repo_rel(common.HOMOGRAPH_KEYS),
            "key_count": len(homograph_keys),
            "risk_flag": "norm_homograph",
        },
        "queues": {
            "root_hygiene": root_queue,
            "surface_hygiene": surface_queue,
            "range_references": range_queue,
        },
    }
    return homograph_payload, report_payload


def write_artifacts(entries: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    homographs, report = build_artifacts(entries)
    common.write_json(common.HOMOGRAPH_KEYS, homographs)
    common.write_json(common.HYGIENE_REPORT, report)
    return homographs, report


def check_artifacts(entries: list[dict[str, Any]]) -> list[str]:
    expected_homographs, expected_report = build_artifacts(entries)
    errors: list[str] = []
    for path, expected in (
        (common.HOMOGRAPH_KEYS, expected_homographs),
        (common.HYGIENE_REPORT, expected_report),
    ):
        if not path.exists():
            errors.append(f"missing generated artifact: {common.repo_rel(path)}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != review_json(expected):
            errors.append(f"stale or non-deterministic artifact: {common.repo_rel(path)}")
    identity = expected_report["accepted_crosswalk_identity"]
    if not identity["unchanged_from_authoritative_baseline"]:
        errors.append("STOP: currently accepted crosswalk identity differs from the authoritative baseline")
    if identity["range_crosswalk_rows_with_accepted_identity"]:
        errors.append("range-reference rows must not carry accepted crosswalk identity")
    if expected_homographs["key_count"] < 23:
        errors.append("norm homograph inventory fell below the audited minimum of 23")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    entries = common.iter_entries()
    if args.write:
        homographs, report = write_artifacts(entries)
    else:
        homographs, report = build_artifacts(entries)
    errors = check_artifacts(entries)
    summary = {
        "ok": not errors,
        "errors": errors,
        "homograph_key_count": homographs["key_count"],
        "actual_counts": report["actual_counts"],
        "accepted_crosswalk_identity": report["accepted_crosswalk_identity"],
    }
    print(review_json(summary), end="")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
