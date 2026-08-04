#!/usr/bin/env python3
"""Red-first tests for tranche-001 T1 coherent ordinary-tutor coverage of the derivation/template runtime batch.

Pins the exact 22 misconception ids named by this batch and verifies they still resolve to the COMMITTED public
evidence they must reverse-trace to: curriculum/l1l6/drills-candidates/drill-candidates.jsonl (per-misconception
drill candidate spec, never trusted without independent re-verification) and curriculum/l1l6/misconceptions/
misconception-registry.jsonl (per-misconception disposition/violated-capability record). Unlike the earlier
derivation/ownership tranche, this batch's 22 ids do NOT share one exact capability pair -- they span the
remaining derivation/template runtime plane (template_classification, discriminator_table, inc-derivatives,
inc-negation, licensing_table) -- so the source-truth tests check self-consistency between the two committed
files and membership in that plane's capability universe, never an invented uniform pair.

The batch must then produce three NEW, currently-absent artifacts:
  * curriculum/drills/keys/tranche-001-derivation-template-runtime.keys.jsonl -- exactly 22 ORIGINAL ordinary
    fusha_tutor_runtime rows (never copied from the candidate specs, never assessment/benchmark material), one
    primary row per misconception id (T1DT-01..T1DT-22), every row two_vote_required, occurrence-neutral
    (quran_example: null) and public-ineligible, covering every one of the 22 target ids and no id outside it.
  * curriculum/drills/tranche-001-derivation-template-runtime.md -- the lesson/remediation surface every row's
    remediation_route must point at.
  * a small coherent family of NEW KCs appended to the combined KC catalog (via curriculum/kc-catalog.d/
    tranche-001-derivation-template.jsonl, an append-safe shard), with non-overlapping curriculum_misconception_ids
    coverage that exactly partitions the 22 target ids, each exercised by at least two bank rows, and each gated
    non-auto_safe (so every row stays two-vote held, never auto-cleared).

mc-0094 defect pin: mc-0094 is currently listed under the LEGACY kc_id `kc-dictionary-infinitive-leakage`
(curriculum/kc-catalog.json). That legacy KC's own topic (glossing an inflected token with the dictionary's
"to ..." entry form) is unrelated to what mc-0094 is actually about (deriving a verbal noun from its own
template rather than copying the finite verb's surface alteration), and its `drill_route` points at a different,
pre-existing file (curriculum/drills/root-pattern-practice.md), not this batch's new lesson. Reusing it here
would both misdirect remediation AND fail tools/validate_drill_keys.py's KC-locality invariant. This file pins
both defects and asserts this batch's own bank uses a new, route-local, semantically correct KC for mc-0094
instead.

This file is RED by construction: none of the three artifacts exist yet, so every test below either fails on a
missing path or (for the source-truth class) exercises only what is ALREADY committed. Runtime behaviour
(correct-answer-plus-wrong-reason hold, wrong-answer remediation, two-vote hold) is checked through the REAL
tools/fusha_tutor_runtime.py interfaces (load_bank/grade/step/_load_kc_catalog_by_id/_check_kc_gate_row) -- never
a reimplementation of that grading logic.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tools/ itself, so "import fusha_tutor_runtime" works
import kc_catalog

DRILL_CANDIDATES = _REPO / "curriculum" / "l1l6" / "drills-candidates" / "drill-candidates.jsonl"
MISCONCEPTIONS = _REPO / "curriculum" / "l1l6" / "misconceptions" / "misconception-registry.jsonl"
LEGACY_KC_CATALOG = _REPO / "curriculum" / "kc-catalog.json"
NEW_BANK = _REPO / "curriculum" / "drills" / "keys" / "tranche-001-derivation-template-runtime.keys.jsonl"
NEW_BANK_REL = "curriculum/drills/keys/tranche-001-derivation-template-runtime.keys.jsonl"
NEW_LESSON = _REPO / "curriculum" / "drills" / "tranche-001-derivation-template-runtime.md"
NEW_LESSON_REL = "curriculum/drills/tranche-001-derivation-template-runtime.md"
NEW_SHARD = _REPO / "curriculum" / "kc-catalog.d" / "tranche-001-derivation-template.jsonl"

# ---------------------------------------------------------------------------
# the exact 22-id target set named by this round. Re-checked below against BOTH committed files, never trusted
# from this list alone.
# ---------------------------------------------------------------------------
TARGET_IDS = sorted([
    "mc-0035", "mc-0085", "mc-0094", "mc-0152", "mc-0351", "mc-0370", "mc-0424", "mc-0440", "mc-0446",
    "mc-0452", "mc-0466", "mc-0506", "mc-0574", "mc-0629", "mc-0656", "mc-0693", "mc-0794", "mc-0818",
    "mc-0880", "mc-0881", "mc-0887", "mc-0892",
], key=lambda s: int(s.split("-")[1]))

# the derivation/template runtime plane's capability universe -- NOT one exact pair (unlike the earlier
# derivation/ownership tranche). Every target id's capability_link must be a non-empty subset of this set.
CAP_UNIVERSE = frozenset({"template_classification", "discriminator_table", "inc-derivatives", "inc-negation",
                          "licensing_table"})

# lesson bindings named by the round instructions (a cluster may serve more than one lesson) -- checked as a
# SUBSET relation against the committed manifestations (this repo advances lesson coverage; it never asserts
# whole-lesson or whole-unit closure). Matches the six contributing lessons named by the round:
# L2.M4.02, L4.M4.04, L5.M4.01, L6.M3.01, L6.M3.07, L6.M6.04.
EXPECTED_LESSON_BY_ID = {
    "mc-0035": {"L6.M3.01"},
    "mc-0085": {"L4.M4.04"},
    "mc-0094": {"L5.M4.01"},
    "mc-0152": {"L4.M4.04"},
    "mc-0351": {"L4.M4.04"},
    "mc-0370": {"L6.M6.04"},
    "mc-0424": {"L6.M3.01"},
    "mc-0440": {"L6.M6.04"},
    "mc-0446": {"L6.M6.04"},
    "mc-0452": {"L6.M3.07"},
    "mc-0466": {"L6.M6.04"},
    "mc-0506": {"L6.M3.07"},
    "mc-0574": {"L6.M3.07"},
    "mc-0629": {"L2.M4.02"},
    "mc-0656": {"L6.M3.01"},
    "mc-0693": {"L2.M4.02"},
    "mc-0794": {"L6.M3.07"},
    "mc-0818": {"L6.M6.04"},
    "mc-0880": {"L6.M3.01"},
    "mc-0881": {"L4.M4.04"},
    "mc-0887": {"L6.M3.07"},
    "mc-0892": {"L4.M4.04"},
}
EXPECTED_CONTRIBUTING_LESSONS = frozenset({"L2.M4.02", "L4.M4.04", "L5.M4.01", "L6.M3.01", "L6.M3.07", "L6.M6.04"})

# the new KC ids this batch will define. Chosen now (stable, kebab-case, prefixed kc-t1-derivation- family) so
# the future authoring round and this pinned test agree on the exact identifiers. None collide with any KC id
# already present in the combined catalog (checked below, not merely asserted).
NEW_KC_IDS = [
    "kc-t1-derivation-noun-final-class-declension",
    "kc-t1-derivation-passive-voice-construction",
    "kc-t1-derivation-root-template-letter-discipline",
    "kc-t1-derivation-idafa-masdar-argument-case",
    "kc-t1-derivation-participle-usage-licensing",
    "kc-t1-derivation-terminology-category-discipline",
]

NEW_ROW_IDS = ["T1DT-%02d" % n for n in range(1, 23)]

REQUIRED_ROW_FIELDS = (
    "id", "level", "concept", "prompt", "expected_answer", "accepted_variants", "forbidden_answers",
    "required_reasoning", "explanation", "kc_id", "sarf_procedure", "nahw_procedure",
    "remediation_route", "two_vote_required",
    "curriculum_misconception_ids", "quran_example", "public_eligible", "occurrence_status",
)

# the canonical validate_drill_keys.py answer-key schema fields (tools/validate_drill_keys.py REQUIRED).
CANONICAL_KEY_SCHEMA_FIELDS = ("id", "level", "concept", "prompt", "quran_example", "expected_answer",
                               "accepted_variants", "forbidden_answers", "required_reasoning",
                               "sarf_procedure", "nahw_procedure", "remediation_route", "two_vote_required")
PROCEDURE_FIELDS = ("sarf_procedure", "nahw_procedure")

FORBIDDEN_SUBSTRINGS = (
    "curriculum/assessment", "eval/fusha-bench", "fusha-bench-v1", "benchmark",
    "candidate_not_runtime_integrated", "curriculum.l1l6_drill_candidate", "drills-candidates/drill-candidates",
    "qamus_certified", '"certified": true', "public_release", "closes_unit", "closes_lesson",
    "unit_closure", "lesson_closure", "mastery achieved", "fact certified", "http://", "https://",
    "c:" + "\\\\", "c:" + "/users", "/" + "users/",
)

EXPECTED_OCCURRENCE_STATUS = "no_committed_occurrence_evidence"


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _drills_by_misconception():
    return {r["misconception_link"]: r for r in _jsonl(DRILL_CANDIDATES)}


def _misconceptions_by_id():
    return {r["misconception_id"]: r for r in _jsonl(MISCONCEPTIONS)}


def _blob(row):
    return json.dumps(row, ensure_ascii=False)


def _assert_no_forbidden(testcase, blob, label):
    low = blob.lower()
    for bad in FORBIDDEN_SUBSTRINGS:
        testcase.assertNotIn(bad.lower(), low, "%s: forbidden substring %r" % (label, bad))


class TargetSetSourceTruthTests(unittest.TestCase):
    """The 22-id target set is re-verified against the COMMITTED candidate + registry files, never trusted from
    the hardcoded list above alone."""

    def test_target_set_has_exactly_22_unique_ids(self):
        self.assertEqual(len(TARGET_IDS), 22)
        self.assertEqual(len(set(TARGET_IDS)), 22)
        self.assertEqual(len(EXPECTED_LESSON_BY_ID), 22)

    def test_every_target_id_resolves_in_the_committed_drill_candidates_file(self):
        drills = _drills_by_misconception()
        for mc_id in TARGET_IDS:
            row = drills.get(mc_id)
            self.assertIsNotNone(row, "%s missing from drill-candidates.jsonl" % mc_id)
            self.assertEqual(row["drill_id"], "dr-" + mc_id)
            self.assertEqual(row["status"], "candidate_not_runtime_integrated")
            caps = frozenset(row["capability_link"])
            self.assertTrue(caps, "%s: capability_link must be non-empty" % mc_id)
            self.assertTrue(caps.issubset(CAP_UNIVERSE),
                             "%s: capability_link %r is outside the derivation/template runtime plane %r"
                             % (mc_id, sorted(caps), sorted(CAP_UNIVERSE)))

    def test_every_target_id_resolves_in_the_committed_misconception_registry(self):
        registry = _misconceptions_by_id()
        for mc_id in TARGET_IDS:
            row = registry.get(mc_id)
            self.assertIsNotNone(row, "%s missing from misconception-registry.jsonl" % mc_id)
            self.assertEqual(row["disposition"], "candidate_fixture")
            self.assertTrue(frozenset(row["violated_capabilities"]).issubset(CAP_UNIVERSE),
                             "%s: registry violated_capabilities %r outside the plane %r"
                             % (mc_id, row["violated_capabilities"], sorted(CAP_UNIVERSE)))

    def test_drill_candidate_and_registry_capability_links_agree_per_id(self):
        """Self-consistency between the two committed files (never asserted as a uniform pair)."""
        drills = _drills_by_misconception()
        registry = _misconceptions_by_id()
        for mc_id in TARGET_IDS:
            self.assertEqual(frozenset(drills[mc_id]["capability_link"]),
                              frozenset(registry[mc_id]["violated_capabilities"]),
                              "%s: drill-candidate capability_link disagrees with registry violated_capabilities"
                              % mc_id)

    def test_every_target_id_carries_at_least_one_of_its_named_lessons_in_committed_manifestations(self):
        registry = _misconceptions_by_id()
        for mc_id in TARGET_IDS:
            manifest_lessons = {m["lesson_id"] for m in registry[mc_id]["manifestations"]}
            expected = EXPECTED_LESSON_BY_ID[mc_id]
            self.assertTrue(expected & manifest_lessons,
                             "%s: none of the round-named lessons %r found among committed manifestations %r"
                             % (mc_id, sorted(expected), sorted(manifest_lessons)))

    def test_contributing_lessons_match_the_six_named_by_the_round(self):
        union = set()
        for lessons in EXPECTED_LESSON_BY_ID.values():
            union |= lessons
        self.assertEqual(union, set(EXPECTED_CONTRIBUTING_LESSONS))


class Mc0094KcMismappingDefectTests(unittest.TestCase):
    """Pins the mc-0094 defect named by the round: the legacy kc-dictionary-infinitive-leakage KC (already
    listing mc-0094) is semantically mismatched AND route-foreign, so this batch must author its OWN
    route-local KC for mc-0094 rather than reuse it. This test class depends only on ALREADY-COMMITTED data."""

    def test_legacy_kc_dictionary_infinitive_leakage_lists_mc_0094_today(self):
        rows = json.loads(LEGACY_KC_CATALOG.read_text(encoding="utf-8"))
        legacy = next((r for r in rows if r["kc_id"] == "kc-dictionary-infinitive-leakage"), None)
        self.assertIsNotNone(legacy, "legacy KC kc-dictionary-infinitive-leakage missing from kc-catalog.json")
        self.assertIn("mc-0094", legacy["curriculum_misconception_ids"])

    def test_legacy_kc_drill_route_is_not_this_batchs_new_lesson(self):
        rows = json.loads(LEGACY_KC_CATALOG.read_text(encoding="utf-8"))
        legacy = next(r for r in rows if r["kc_id"] == "kc-dictionary-infinitive-leakage")
        self.assertNotEqual(legacy["drill_route"], NEW_LESSON_REL,
                             "legacy KC's drill_route unexpectedly already points at this batch's new lesson")

    def test_legacy_kc_plain_rule_does_not_describe_mc_0094s_own_content(self):
        rows = json.loads(LEGACY_KC_CATALOG.read_text(encoding="utf-8"))
        legacy = next(r for r in rows if r["kc_id"] == "kc-dictionary-infinitive-leakage")
        registry = _misconceptions_by_id()
        mc = registry["mc-0094"]
        # the legacy KC's own topic is a hover-gloss defect (dictionary infinitive on an inflected token); mc-0094
        # is a masdar-template-derivation defect (weak radical placement, not glossing an inflected token).
        self.assertIn("infinitive", legacy["plain_rule"].lower())
        self.assertNotIn("masdar", legacy["plain_rule"].lower())
        self.assertNotIn("verbal-noun", legacy["plain_rule"].lower())
        self.assertIn("verbal-noun", mc["why_wrong"].lower())


class NewKcPlanTests(unittest.TestCase):
    """This worker's own KC plan is well-formed (self-check; does not depend on future files)."""

    def test_a_small_coherent_kc_family_is_chosen(self):
        self.assertGreaterEqual(len(NEW_KC_IDS), 3)
        self.assertLessEqual(len(NEW_KC_IDS), 8)
        self.assertEqual(len(NEW_KC_IDS), len(set(NEW_KC_IDS)))
        for kc_id in NEW_KC_IDS:
            self.assertRegex(kc_id, r"^kc-t1-derivation-[a-z0-9-]+$")

    def test_no_new_kc_id_collides_with_a_pre_existing_kc_id(self):
        """The new ids must not collide with anything that existed BEFORE this batch's own shard -- the legacy
        catalog plus any OTHER shard. This batch's own shard (NEW_SHARD) is excluded from the comparison set
        because it is expected to define exactly these ids once authored; checking it against itself would make
        this assertion vacuously fail for every worker that actually completes the batch."""
        pre_existing = set()
        for row in kc_catalog._read_legacy(_REPO / "curriculum" / "kc-catalog.json"):
            pre_existing.add(row["kc_id"])
        shard_dir = _REPO / "curriculum" / "kc-catalog.d"
        if shard_dir.is_dir():
            for path in sorted(shard_dir.glob("*.jsonl"), key=lambda item: item.name):
                if path.resolve() == NEW_SHARD.resolve():
                    continue
                for row in kc_catalog._read_shard(path):
                    pre_existing.add(row["kc_id"])
        collide = pre_existing & set(NEW_KC_IDS)
        self.assertEqual(collide, set(), "new KC id(s) already present before this batch's own shard: %s" % collide)


class FutureKcCatalogTests(unittest.TestCase):
    """The combined KC catalog (legacy + curriculum/kc-catalog.d/*.jsonl shards) must gain this batch's KCs with
    non-overlapping coverage of TARGET_IDS, routed to the new markdown remediation surface."""

    def _catalog_by_id(self):
        return kc_catalog.load_kc_catalog_by_id(_REPO)

    def test_shard_file_exists(self):
        self.assertTrue(NEW_SHARD.exists(), "%s does not exist yet" % NEW_SHARD)

    def test_every_new_kc_id_is_present_in_the_catalog(self):
        by_id = self._catalog_by_id()
        missing = [kc_id for kc_id in NEW_KC_IDS if kc_id not in by_id]
        self.assertEqual(missing, [], "not yet defined in the combined KC catalog: %s" % missing)

    def test_every_new_kc_has_the_required_fields_a_non_auto_safe_gate_and_routes_to_the_new_lesson(self):
        by_id = self._catalog_by_id()
        required_fields = ("kc_id", "arabic_grammar_name", "plain_rule", "trigger_condition", "expected_feature",
                            "typical_error_feature", "default_gate", "grammar_topic",
                            "curriculum_misconception_ids", "drill_route")
        for kc_id in NEW_KC_IDS:
            kc = by_id[kc_id]
            for field in required_fields:
                self.assertIn(field, kc, "%s missing field %r" % (kc_id, field))
            self.assertNotEqual(kc["default_gate"], "auto_safe",
                                 "%s must stay non-auto_safe so its rows stay two_vote_required" % kc_id)
            self.assertIsInstance(kc["curriculum_misconception_ids"], list)
            self.assertGreaterEqual(len(kc["curriculum_misconception_ids"]), 2,
                                     "%s must cover at least 2 misconceptions" % kc_id)
            self.assertEqual(kc["drill_route"], NEW_LESSON_REL,
                              "%s must route to the new markdown remediation surface" % kc_id)

    def test_new_kc_coverage_exactly_and_disjointly_partitions_the_22_target_ids(self):
        by_id = self._catalog_by_id()
        seen = set()
        union = set()
        for kc_id in NEW_KC_IDS:
            ids = set(by_id[kc_id]["curriculum_misconception_ids"])
            overlap = ids & seen
            self.assertEqual(overlap, set(), "%s overlaps another new KC on %s" % (kc_id, sorted(overlap)))
            outside = ids - set(TARGET_IDS)
            self.assertEqual(outside, set(), "%s covers ids outside the 22-id target set: %s"
                              % (kc_id, sorted(outside)))
            seen |= ids
            union |= ids
        self.assertEqual(union, set(TARGET_IDS), "new-KC coverage does not exactly equal the 22 target ids")

    def test_mc_0094_is_covered_by_a_new_local_kc_not_the_legacy_dictionary_infinitive_leakage_kc(self):
        by_id = self._catalog_by_id()
        owners = [kc_id for kc_id in NEW_KC_IDS if "mc-0094" in by_id[kc_id]["curriculum_misconception_ids"]]
        self.assertEqual(len(owners), 1, "mc-0094 must be covered by exactly one new local KC, got %s" % owners)
        self.assertNotEqual(owners[0], "kc-dictionary-infinitive-leakage")

    def test_new_kc_text_fields_carry_no_forbidden_vocabulary(self):
        by_id = self._catalog_by_id()
        for kc_id in NEW_KC_IDS:
            _assert_no_forbidden(self, _blob(by_id[kc_id]), kc_id)


class FutureBankStructureTests(unittest.TestCase):
    """curriculum/drills/keys/tranche-001-derivation-template-runtime.keys.jsonl must exist with exactly 22
    original rows (T1DT-01..T1DT-22), one primary row per misconception id. RED until authored."""

    def _rows(self):
        return _jsonl(NEW_BANK)

    def test_bank_file_exists_with_exactly_22_unique_rows_with_the_pinned_ids(self):
        self.assertTrue(NEW_BANK.exists(), "%s does not exist yet" % NEW_BANK_REL)
        rows = self._rows()
        self.assertEqual(len(rows), 22)
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate row ids in the new bank")
        self.assertEqual(sorted(ids), sorted(NEW_ROW_IDS))

    def test_every_row_carries_the_three_canonical_key_schema_fields(self):
        for row in self._rows():
            for field in CANONICAL_KEY_SCHEMA_FIELDS:
                self.assertIn(field, row, "%s missing canonical key-schema field %r" % (row.get("id"), field))
            self.assertIsInstance(row["concept"], str)
            self.assertTrue(row["concept"].strip(), "%s: concept must be a non-empty string" % row["id"])
            self.assertTrue(
                row["sarf_procedure"] is not None or row["nahw_procedure"] is not None,
                "%s: at least one of sarf_procedure/nahw_procedure must be non-null" % row["id"])

    def test_every_non_null_procedure_path_exists_on_disk(self):
        for row in self._rows():
            for field in PROCEDURE_FIELDS:
                path = row[field]
                if path is None:
                    continue
                self.assertTrue((_REPO / path).exists(),
                                 "%s: %s cites missing path %r" % (row["id"], field, path))

    def test_every_row_carries_the_required_fields_and_is_two_vote_occurrence_neutral_and_public_ineligible(self):
        for row in self._rows():
            for field in REQUIRED_ROW_FIELDS:
                self.assertIn(field, row, "%s missing field %r" % (row.get("id"), field))
            self.assertIs(row["two_vote_required"], True, "%s must be two_vote_required" % row["id"])
            self.assertIsNone(row["quran_example"], "%s: occurrence-neutral rows use quran_example: null" % row["id"])
            self.assertIs(row["public_eligible"], False, "%s must be public-ineligible" % row["id"])
            self.assertEqual(row["occurrence_status"], EXPECTED_OCCURRENCE_STATUS)
            self.assertEqual(row["remediation_route"], NEW_LESSON_REL,
                              "%s must remediate to the new lesson surface" % row["id"])
            self.assertIn(row["kc_id"], NEW_KC_IDS, "%s uses a KC outside this batch's new KCs" % row["id"])
            self.assertGreaterEqual(len(row["curriculum_misconception_ids"]), 1)
            self.assertGreaterEqual(len(row.get("accepted_variants") or []), 0)
            self.assertGreaterEqual(len(row.get("forbidden_answers") or []), 1,
                                     "%s needs at least one forbidden (wrong-reasoning) answer" % row["id"])
            self.assertGreaterEqual(len(row.get("required_reasoning") or []), 1)

    def test_bank_coverage_exactly_equals_the_22_target_ids_with_no_unrelated_id_laundered_in(self):
        rows = self._rows()
        covered = set()
        for row in rows:
            covered |= set(row["curriculum_misconception_ids"])
        self.assertEqual(covered, set(TARGET_IDS),
                          "bank coverage != target set; missing=%s extra=%s"
                          % (sorted(set(TARGET_IDS) - covered), sorted(covered - set(TARGET_IDS))))

    def test_every_row_is_a_single_id_primary_row_no_id_appears_twice(self):
        """One primary row per misconception id: each row's own curriculum_misconception_ids is a singleton,
        and the 22 singletons partition the 22 target ids."""
        rows = self._rows()
        seen = []
        for row in rows:
            ids = row["curriculum_misconception_ids"]
            self.assertEqual(len(ids), 1, "%s: a primary row must carry exactly one misconception id" % row["id"])
            seen.append(ids[0])
        self.assertEqual(sorted(seen), TARGET_IDS)

    def test_every_new_kc_is_exercised_by_at_least_two_rows_and_no_stray_kc_is_used(self):
        rows = self._rows()
        counts = {}
        for row in rows:
            counts[row["kc_id"]] = counts.get(row["kc_id"], 0) + 1
        self.assertEqual(set(counts), set(NEW_KC_IDS), "row KC usage does not match the new KC set exactly")
        under = {kc: n for kc, n in counts.items() if n < 2}
        self.assertEqual(under, {}, "these new KCs are exercised by fewer than 2 rows: %s" % under)

    def test_mc_0094_row_uses_a_new_local_kc_never_the_legacy_dictionary_infinitive_leakage_kc(self):
        rows = self._rows()
        row = next(r for r in rows if r["curriculum_misconception_ids"] == ["mc-0094"])
        self.assertIn(row["kc_id"], NEW_KC_IDS)
        self.assertNotEqual(row["kc_id"], "kc-dictionary-infinitive-leakage")

    def test_no_row_carries_forbidden_vocabulary_or_a_candidate_schema_leak(self):
        for row in self._rows():
            _assert_no_forbidden(self, _blob(row), row.get("id"))
            self.assertNotIn("prompt_specification", row)
            self.assertNotIn("expected_rubric", row)
            self.assertNotIn("capability_link", row)

    def test_bank_and_catalog_kc_assignments_are_mutually_consistent(self):
        catalog_by_id = kc_catalog.load_kc_catalog_by_id(_REPO)
        for row in self._rows():
            kc = catalog_by_id.get(row["kc_id"])
            self.assertIsNotNone(kc, "%s: kc_id %r not in combined KC catalog" % (row["id"], row["kc_id"]))
            allowed = set(kc["curriculum_misconception_ids"])
            got = set(row["curriculum_misconception_ids"])
            self.assertTrue(got.issubset(allowed),
                             "%s: misconception ids %s not all listed under its own KC %s"
                             % (row["id"], sorted(got - allowed), row["kc_id"]))


class DrillKeysValidatorRealInterfaceTests(unittest.TestCase):
    """Runs the REAL tools/validate_drill_keys.validate() against this bank (never a reimplementation of its
    schema/leak/cited-path/hard-grammar checks)."""

    def test_validate_drill_keys_accepts_this_bank_with_zero_errors(self):
        import validate_drill_keys as vdk
        errors = vdk.validate(str(NEW_BANK))
        self.assertEqual(errors, [], "validate_drill_keys.validate() rejected the bank: %s" % errors)

    def test_validate_drill_keys_recognizes_at_least_one_two_vote_hard_grammar_row(self):
        import validate_drill_keys as vdk
        rows = _jsonl(NEW_BANK)
        hard_rows = 0
        two_vote_hard_rows = 0
        for row in rows:
            blob = json.dumps(row, ensure_ascii=False).lower()
            is_hard = any(term.lower() in blob for term in vdk.HARD_TERMS)
            if is_hard:
                hard_rows += 1
                if row.get("two_vote_required"):
                    two_vote_hard_rows += 1
        self.assertGreater(hard_rows, 0, "validate_drill_keys would report 'expected at least one hard-grammar row'")
        self.assertGreater(two_vote_hard_rows, 0,
                           "validate_drill_keys would report 'expected at least one two_vote_required hard-grammar "
                           "row'")


class FutureLessonSurfaceTests(unittest.TestCase):
    """curriculum/drills/tranche-001-derivation-template-runtime.md must exist and honestly disclaim assessment/
    certification status, without claiming whole-unit or whole-lesson closure. RED until authored."""

    def test_lesson_file_exists(self):
        self.assertTrue(NEW_LESSON.exists(), "%s does not exist yet" % NEW_LESSON_REL)

    def test_lesson_mentions_every_new_kc_and_carries_no_forbidden_vocabulary(self):
        text = NEW_LESSON.read_text(encoding="utf-8")
        for kc_id in NEW_KC_IDS:
            self.assertIn(kc_id, text, "lesson never mentions %s" % kc_id)
        _assert_no_forbidden(self, text, "lesson")

    def test_lesson_carries_an_explicit_non_assessment_non_certification_disclaimer(self):
        low = NEW_LESSON.read_text(encoding="utf-8").lower()
        assessment_disclaimed = ("never assessment" in low or "not assessment" in low
                                  or "never usable as independent assessment" in low)
        certification_disclaimed = ("never certification" in low or "not certification" in low
                                     or "not certified" in low or "no certification" in low
                                     or "never assessment or certification" in low)
        self.assertTrue(assessment_disclaimed, "lesson must disclaim assessment use")
        self.assertTrue(certification_disclaimed, "lesson must disclaim certification/closure claims")

    def test_lesson_does_not_claim_whole_unit_or_whole_lesson_closure(self):
        low = NEW_LESSON.read_text(encoding="utf-8").lower()
        for bad in ("closes this lesson", "closes this unit", "completes the lesson", "completes the unit",
                    "unit is now closed", "lesson is now closed"):
            self.assertNotIn(bad, low, "lesson must not claim whole-unit/whole-lesson closure")

    def test_lesson_explains_why_mc_0094_does_not_reuse_the_legacy_kc(self):
        text = NEW_LESSON.read_text(encoding="utf-8")
        self.assertIn("kc-dictionary-infinitive-leakage", text,
                       "lesson must name and explain why the legacy mismapped KC is not reused for mc-0094")


class RuntimeBehaviourTests(unittest.TestCase):
    """Ordinary fusha_tutor_runtime bank loading, correct-answer-plus-wrong-reason hold, wrong-answer
    remediation, and two-vote hold behaviour, all through the REAL tools/fusha_tutor_runtime.py interfaces
    (never a reimplementation). RED until the bank + KC catalog entries exist."""

    def test_bank_loads_through_the_real_runtime_loader(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        self.assertEqual(len(rows), 22)

    def test_every_row_passes_the_real_catalog_gate_check(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        kc_by_id = ftr._load_kc_catalog_by_id()
        for row in rows:
            failures = ftr._check_kc_gate_row(row, kc_by_id)
            self.assertEqual(failures, [], "%s failed the real catalog-gate check: %s" % (row["id"], failures))

    def test_correct_answer_and_correct_reasoning_is_held_for_the_two_vote_fact_gate_not_cleared(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertTrue(result["grade"]["passed"])
        self.assertTrue(result["grade"]["reasoning_passed"])
        self.assertTrue(result["grade"]["held_for_fact_gate"])
        self.assertFalse(result["grade"]["cleared"])
        self.assertEqual(result["outcome"], "hold")
        self.assertIsNone(result["event"]["remediation_route"])

    def test_correct_answer_with_missing_required_reasoning_is_rejected_and_routed_to_remediation(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": row["expected_answer"], "reasoning": []}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertFalse(result["grade"]["reasoning_passed"])
        self.assertFalse(result["grade"]["content_mastered"])
        self.assertEqual(result["outcome"], "hold")
        self.assertEqual(result["event"]["remediation_route"], row["remediation_route"])

    def test_wrong_answer_is_rejected_and_routed_to_remediation(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        row = rows[0]
        payload = {"answer": "this is not the expected answer at all", "reasoning": list(row["required_reasoning"])}
        result = ftr.step(row, None, payload, now_day=0)
        self.assertFalse(result["grade"]["passed"])
        self.assertEqual(result["outcome"], "lapse")
        self.assertEqual(result["event"]["remediation_route"], row["remediation_route"])

    def test_every_row_labelled_with_missing_required_reasoning_is_rejected(self):
        """Negative-boundary contract: a correct label with missing required reasoning must be rejected for
        EVERY row in this bank, not just the first -- required_reasoning is load-bearing on all 22 items."""
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            payload = {"answer": row["expected_answer"], "reasoning": []}
            result = ftr.step(row, None, payload, now_day=0)
            self.assertFalse(result["grade"]["reasoning_passed"],
                              "%s: missing-reasoning answer unexpectedly passed reasoning" % row["id"])
            self.assertFalse(result["grade"]["content_mastered"],
                              "%s: missing-reasoning answer unexpectedly counted as mastered" % row["id"])

    def test_every_row_rejects_at_least_one_forbidden_answer_via_the_real_grader(self):
        """Negative-boundary contract: each row's own forbidden_answers must be recognised as forbidden by the
        real grader when offered as the learner's answer text."""
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            forbidden = row["forbidden_answers"][0]
            payload = {"answer": forbidden, "reasoning": list(row["required_reasoning"])}
            g = ftr.grade(row, payload)
            self.assertTrue(g["forbidden_hit"], "%s: forbidden answer %r not detected by the real grader"
                             % (row["id"], forbidden))


class F10EnglishWrongReasonTripwires(unittest.TestCase):
    """F10: every derivation row must carry a REACHABLE English wrong-reason tripwire (the pre-existing
    forbidden_answers were Arabic-only prose, unreachable in the row's own English-answer register), and the
    tripwire must actually fire — the real grader must reject it — when submitted as the learner's answer."""

    def test_every_row_carries_at_least_one_english_forbidden_answer(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        missing = [row["id"] for row in rows
                  if not any(re.search(r"[a-zA-Z]{4}", f) for f in row["forbidden_answers"])]
        self.assertEqual(missing, [], "rows with no English-register forbidden answer: %s" % missing)

    def test_every_rows_english_tripwire_fires_via_the_real_grader(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            english_forbidden = [f for f in row["forbidden_answers"] if re.search(r"[a-zA-Z]{4}", f)]
            for forbidden in english_forbidden:
                with self.subTest(id=row["id"]):
                    g = ftr.grade(row, {"answer": forbidden, "reasoning": []})
                    self.assertFalse(g["content_mastered"],
                                    "%s: English wrong-reason tripwire did not fire: %r"
                                    % (row["id"], forbidden[:60]))
                    self.assertTrue(g["forbidden_hit"],
                                   "%s: English tripwire not detected as forbidden by the real grader"
                                   % row["id"])


class F2ExactDiacriticContractGuard(unittest.TestCase):
    """F2: every row whose authored correct form and an authored forbidden form collide under the lenient
    recall normalizer (differ ONLY by a vowel/shadda/case-ending diacritic) must opt into `exact_surface_forms`,
    and the exact contract must actually reject that colliding forbidden form while still accepting the gold
    form."""

    def test_every_diacritic_colliding_row_declares_exact_surface_forms(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        missing = [row["id"] for row in rows
                  if ftr.diacritic_only_collision(row) and not row.get("exact_surface_forms")]
        self.assertEqual(missing, [],
                         "rows whose expected/forbidden collide under the lenient normalizer (differ only by "
                         "diacritics) but do not declare exact_surface_forms: %s" % missing)

    def test_exact_surface_forms_rows_reject_their_own_colliding_forbidden_text(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            if not row.get("exact_surface_forms"):
                continue
            for forbidden in row["forbidden_answers"]:
                if ftr._norm(forbidden) in {ftr._norm(row["expected_answer"])} | {
                        ftr._norm(v) for v in row.get("accepted_variants") or []}:
                    with self.subTest(id=row["id"]):
                        g = ftr.grade(row, {"answer": forbidden, "reasoning": list(row["required_reasoning"])})
                        self.assertFalse(g["passed"],
                                        "%s: exact_surface_forms must reject the diacritic-colliding forbidden "
                                        "text %r" % (row["id"], forbidden[:60]))

    def test_exact_surface_forms_rows_still_accept_their_own_gold_form(self):
        import fusha_tutor_runtime as ftr
        rows = ftr.load_bank(str(NEW_BANK))
        for row in rows:
            if not row.get("exact_surface_forms"):
                continue
            with self.subTest(id=row["id"]):
                g = ftr.grade(row, {"answer": row["expected_answer"], "reasoning": list(row["required_reasoning"])})
                self.assertTrue(g["passed"], "%s: exact_surface_forms must still accept the gold answer" % row["id"])


if __name__ == "__main__":
    unittest.main()
