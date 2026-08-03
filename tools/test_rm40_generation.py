#!/usr/bin/env python3
"""Red-first tests for RM-40 staged paradigm-licensed morphology generation.

Every test is authored before its implementation. The design contract is
`.lane-inputs/rm40-staged-design-review.md` section 6.2 (twelve checklist
items). Candidates are NEVER facts: generated forms are candidate-only, live in
a store provably disjoint from the sourced lookup/evidence baseline, carry
paradigm + rule-chain provenance, and can never enter the live whitelist path.

All fixtures are synthetic. No Qurʾān text is copied here.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_append_queue
from tools import fact_projectors
from tools import fusha_paradigm_generate as gen
from tools import rm40_eval_harness as ev
from tools import rm40_gate_stack as gates
from tools import validate_rm40_generation as val

BASELINE_FULL = ROOT / "fusha" / "morphology" / "data" / "largelexicon-stems.full.jsonl"
ALLOWLIST = ROOT / "fusha" / "lexicon" / "largelexicon" / "source-clean-table-allowlist.json"

# Synthetic lexeme specs (sound triliteral roots only, no Qurʾān provenance).
SOUND_IV = {"pos": "verb", "lemma": "أَكْتَبَ", "root": "ك ت ب", "measure": "IV"}
SOUND_I = {"pos": "verb", "lemma": "كَتَبَ", "root": "ك ت ب", "measure": "I"}
HOLLOW_I = {"pos": "verb", "lemma": "قَالَ", "root": "ق و ل", "measure": "I"}
HAMZA_I = {"pos": "verb", "lemma": "أَمَنَ", "root": "ء م ن", "measure": "I"}
BROKEN_PLURAL = {"pos": "noun", "lemma": "قَلَم", "root": "ق ل م", "plural_template_id": "taksir-afal"}


def emit_one(spec, slot):
    rows = gen.generate_verb(spec, slots=[slot])
    return rows


class Test01AbstainOnWeakRoot(unittest.TestCase):
    def test_hollow_root_present_slot_emits_no_candidate(self):
        rows = emit_one(HOLLOW_I, "present_active")
        self.assertEqual([], rows, "hollow root ق و ل must abstain, not fabricate a template surface")
        decision = gates.slot_gate(HOLLOW_I["root"], HOLLOW_I["measure"], "present_active")
        self.assertEqual("abstain", decision["decision"])


class Test02AbstainOnHamzaSeat(unittest.TestCase):
    def test_hamza_radical_slot_abstains(self):
        rows = emit_one(HAMZA_I, "present_active")
        self.assertEqual([], rows, "hamza-seat radical must abstain — the template cannot pick the seat")

    def test_generated_strict_key_collision_abstains(self):
        # Two vocalised surfaces that collapse to the same strict key are a homograph collision.
        self.assertTrue(gates.strict_key_collision("نَزَّلَ", ["نَزَلَ"]))
        self.assertFalse(gates.strict_key_collision("كَتَبَ", ["ضَرَبَ"]))


class Test03BrokenPluralIsTwoVoteCandidate(unittest.TestCase):
    def test_broken_plural_row_is_candidate_and_contract_is_two_vote(self):
        rows = gen.generate_noun_plural(BROKEN_PLURAL)
        self.assertTrue(rows, "a sound broken-plural template should license a candidate")
        row = rows[0]
        self.assertEqual("candidate", row["certification_state"])
        self.assertEqual("two_vote_required", fact_projectors.SARF_GENERATED_CONTRACT["gate_tier"])
        self.assertNotEqual("auto_safe", fact_projectors.SARF_GENERATED_CONTRACT["gate_tier"])


class Test04NoOverwriteOfSourcedFact(unittest.TestCase):
    def test_generator_abstains_when_baseline_form_already_resolves(self):
        baseline = [{"lemma": SOUND_IV["lemma"], "slot": "present_active", "surface": "يُكْتِبُ"}]
        rows = gen.generate_verb(SOUND_IV, slots=["present_active"], baseline_forms=baseline)
        self.assertEqual([], rows, "a documented baseline form must win; generation only fills gaps")

    def test_row_with_supersedes_fails_closed(self):
        row = emit_one(SOUND_IV, "present_active")[0]
        row = dict(row)
        row["supersedes"] = "sha256:" + "a" * 64
        errors = val.validate_invariants(row)
        self.assertTrue(any("supersedes" in e for e in errors))


class Test05PlaneDisjointness(unittest.TestCase):
    def test_sourced_marker_with_generation_used_fails_closed(self):
        row = emit_one(SOUND_IV, "present_active")[0]
        polluted = dict(row)
        polluted["source"] = "qamus_current_authored"
        errors = val.validate_invariants(polluted)
        self.assertTrue(any("source" in e for e in errors))
        self.assertTrue(val.check_plane_pollution(polluted))

    def test_baseline_table_carries_zero_generated_markers(self):
        # Structural firewall over the real committed baseline table.
        self.assertEqual([], val.check_baseline_disjoint(BASELINE_FULL, ALLOWLIST))

    def test_baseline_allowlist_declares_lookup_evidence_baseline_role(self):
        allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        stem = [t for t in allow["tables"] if t["path"].endswith("largelexicon-stems.full.jsonl")][0]
        self.assertEqual("lookup_evidence_baseline", stem.get("table_role"))


class Test06CompetingFormsPreserved(unittest.TestCase):
    def test_two_licensed_seats_kept_as_competing_semantic_tie(self):
        # Form I present has three lexically-selected vowel patterns; the paradigm
        # licenses all — never collapse to a single certified surface.
        rows = gen.generate_verb(SOUND_I, slots=["present_active"])
        self.assertTrue(rows)
        row = rows[0]
        self.assertTrue(row["semantic_tie"])
        self.assertGreaterEqual(len(row["competing_alternatives"]), 1)
        self.assertTrue(all(alt.get("semantic_tie") for alt in row["competing_alternatives"]))


class Test07RuleChainProvenance(unittest.TestCase):
    def test_every_generated_row_names_paradigm_and_gates(self):
        row = emit_one(SOUND_IV, "present_active")[0]
        chain = row["provenance"]["rule_chain"]
        self.assertTrue(chain and all(isinstance(x, str) and x for x in chain))
        self.assertTrue(any("verb-measures" in x for x in chain))
        self.assertEqual("fusha/verb-measures@1", row["provenance"]["paradigm_id"])

    def test_missing_rule_chain_fails_closed(self):
        row = dict(emit_one(SOUND_IV, "present_active")[0])
        row["provenance"] = dict(row["provenance"])
        row["provenance"]["rule_chain"] = []
        errors = val.validate_invariants(row)
        self.assertTrue(any("rule_chain" in e for e in errors))


class Test08FabricationDetected(unittest.TestCase):
    def test_emitted_surface_with_no_gold_counts_as_fabrication_not_recall_miss(self):
        # Design §4.3: a fabrication is an emitted surface whose LEMMA has no gold
        # surface anywhere (a hard-budget metric), distinct from a precision miss
        # (wrong form for a known lemma) and never laundered into recall.
        gold = {"lex-x": ["كَتَبَ"]}
        emitted = [{"lemma": "lex-nogold", "surface": "زَقَّمَ"}]  # lemma absent from gold entirely
        block = ev.evaluate_slot(emitted=emitted, abstained=[], gold_by_lemma=gold, slot_type="present_active")
        self.assertEqual(1, block["fabrication_count"])
        self.assertEqual(0, block["precision"]["denominator"])  # fabrications excluded from precision
        self.assertEqual(0, block["recall"]["denominator"])  # and never counted as a recall miss
        self.assertNotIn("recall_miss", block)


class Test09NotDeployEligible(unittest.TestCase):
    def test_generated_row_never_enters_whitelist_even_if_materialized(self):
        generated = {"generation_used": True, "certification_state": "materialized", "source": "paradigm_generated"}
        self.assertFalse(build_append_queue.is_generation_deploy_eligible(generated))
        baseline = {"generation_used": False, "certification_state": "materialized", "source": "qamus_current_authored"}
        self.assertTrue(build_append_queue.is_generation_deploy_eligible(baseline))


class Test10PrecisionDenominatorHonesty(unittest.TestCase):
    def test_report_prints_numerator_denominator_abstention_and_no_aggregate(self):
        gold = {"lex-a": ["يُكْتِبُ"]}
        emitted = [{"lemma": "lex-a", "surface": "يُكْتِبُ"}]
        block = ev.evaluate_slot(emitted=emitted, abstained=[{"lemma": "lex-b"}], gold_by_lemma=gold,
                                 slot_type="present_active")
        for key in ("numerator", "denominator", "value"):
            self.assertIn(key, block["precision"])
        self.assertIn("abstention", block)
        report = ev.build_report([block])
        # reuse the RM-38 structural guard: no collapsed headline score anywhere
        from tools.rm38.validate import validate_no_collapsed_score
        validate_no_collapsed_score(report)


class Test11NormStrictJoinNotNorm(unittest.TestCase):
    def test_hamza_seat_variants_do_not_match_under_strict_join(self):
        self.assertFalse(ev.surface_matches("إِيمَان", ["أَيْمَان"]))  # strict keeps the seat
        self.assertTrue(ev.surface_matches("يُكْتِبُ", ["يُكْتِبُ"]))


class Test12ManifestHashAndNoData(unittest.TestCase):
    def test_tampered_fixture_hash_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "f.jsonl"
            fixture.write_text('{"lemma":"x","surfaces":["كَتَبَ"]}\n', encoding="utf-8")
            good = ev.sha256_file(fixture)
            ev.verify_fixture(fixture, {"sha256": good})  # accepts
            with self.assertRaises(ev.FixtureError):
                ev.verify_fixture(fixture, {"sha256": "0" * 64})

    def test_no_corpus_prose_in_committed_generation_artifacts(self):
        errors = val.check_no_corpus([
            ROOT / "fusha" / "morphology" / "data" / "generated-candidates.sample.jsonl",
            ROOT / "fusha" / "morphology" / "fixtures" / "rm40-generated-candidates.jsonl",
        ])
        self.assertEqual([], errors)


class Test13SelfTestsRunOffline(unittest.TestCase):
    def test_validator_and_harness_self_tests_pass(self):
        for script in ("validate_rm40_generation.py", "rm40_eval_harness.py"):
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / script), "--self-test"],
                cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)


# ---------------------------------------------------------------------------
# u-s08 noun plural/gender lexeme-link Train A batch: broken-plural template
# inventory, rare/second-order licensing, plural-of-plural, and the lexical
# feminine registry (tools/rm40_gate_stack.py + tools/fact_projectors.py).
# ---------------------------------------------------------------------------
EVAL_PATH = ROOT / "sarf" / "evals" / "plural-gender-operationalization-eval.jsonl"
LOC_SURFACE_INDEX_PATH = ROOT / "qamus" / "indexes" / "quran-loc-surface" / "index.jsonl"


def _load_eval_rows():
    rows = []
    with EVAL_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_loc_surface_index():
    index = {}
    with LOC_SURFACE_INDEX_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                row = json.loads(line)
                index[row["loc"]] = row["surface"]
    return index


def _eval_occurrence(row):
    occ = row["occurrence"]
    return {"identity": {"loc": occ["loc"]}, "surface": occ["surface"]}


def _run_eval_row(row, rules_payload=None):
    """Run one eval row through the consumer it declares; returns (status, reason)."""
    if row["gate"] == "plural_lexeme_link":
        if row["consumer"] == "gate":
            decision = gates.broken_plural_lexeme_link_gate(
                row.get("root"),
                row.get("template_id"),
                attested_pair=row.get("attested_pair", False),
                rare_license_ok=row.get("rare_license_ok", True),
                plural_of_plural_base_attested=row.get("plural_of_plural_base_attested", True),
                rules_payload=rules_payload,
            )
            status = "candidate" if decision["decision"] == "emit" else "abstained"
            return status, decision["defeater"]
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_PLURAL_LEXEME_LINK_PROJECTOR_ID,
            occurrence=_eval_occurrence(row),
            root=row.get("root"),
            template_id=row.get("template_id"),
            attested_plurals=row.get("attested_plurals", []),
            rare_license_ok=row.get("rare_license_ok", True),
            plural_of_plural_base_attested=row.get("plural_of_plural_base_attested", True),
        )
        reason = None if result["status"] == "candidate" else result["abstention"]["reason"]
        return result["status"], reason
    if row["gate"] == "lexical_gender":
        result = fact_projectors.REGISTRY.run(
            fact_projectors.NOUN_LEXICAL_GENDER_PROJECTOR_ID,
            occurrence=_eval_occurrence(row),
            gender_registry_entry=row.get("gender_registry_entry"),
        )
        reason = None if result["status"] == "candidate" else result["abstention"]["reason"]
        return result["status"], reason
    raise ValueError("unknown gate in eval row: " + row["gate"])


class Test14PluralTemplateIdHasNoDefault(unittest.TestCase):
    def test_generate_noun_plural_abstains_when_template_id_missing(self):
        noun = {"pos": "noun", "lemma": "قَلَم", "root": "ق ل م"}
        rows = gen.generate_noun_plural(noun)
        self.assertEqual([], rows, "a missing plural_template_id must abstain, never default to taksir-afal")

    def test_gate_abstains_with_plural_template_id_missing_defeater(self):
        decision = gates.broken_plural_lexeme_link_gate("ق ل م", None, attested_pair=True)
        self.assertEqual("abstain", decision["decision"])
        self.assertEqual("plural_template_id_missing", decision["defeater"])


class Test15SoundPluralSuffixIsNotRootOrTemplate(unittest.TestCase):
    def test_msl_and_mfl_ids_are_not_broken_plural_templates(self):
        self.assertFalse(gates.is_broken_plural_template_id("msl-nominative"))
        self.assertFalse(gates.is_broken_plural_template_id("mfl-sound"))
        self.assertTrue(gates.is_broken_plural_template_id("taksir-afal"))

    def test_gate_abstains_for_a_sound_plural_id(self):
        decision = gates.broken_plural_lexeme_link_gate("س ل م", "msl-nominative", attested_pair=True)
        self.assertEqual("abstain", decision["decision"])
        self.assertEqual("sound_plural_suffix_not_broken_template", decision["defeater"])


class Test16RarePluralRequiresClosedLexemeLicense(unittest.TestCase):
    def test_broken_plural_without_attested_pair_abstains(self):
        decision = gates.broken_plural_lexeme_link_gate("ق ل م", "taksir-afal", attested_pair=False)
        self.assertEqual("abstain", decision["decision"])
        self.assertEqual("no_attested_lexeme_pair", decision["defeater"])

    def test_unlicensed_lexeme_abstains_licensed_lexeme_emits(self):
        unlicensed = gates.broken_plural_lexeme_link_gate(
            "ك ل ب", "taksir-nisa-suppletive-rare", attested_pair=True, rare_license_ok=False
        )
        self.assertEqual("abstain", unlicensed["decision"])
        self.assertEqual("rare_plural_unlicensed", unlicensed["defeater"])

        licensed = gates.broken_plural_lexeme_link_gate(
            "م ر أ", "taksir-nisa-suppletive-rare", attested_pair=True, rare_license_ok=True
        )
        self.assertEqual("emit", licensed["decision"])


class Test17PluralOfPluralRequiresAttestedBase(unittest.TestCase):
    def test_unattested_base_abstains_attested_base_emits(self):
        unattested = gates.broken_plural_lexeme_link_gate(
            "ب ي ت", "taksir-jam-al-jam-fuulaat", attested_pair=True,
            plural_of_plural_base_attested=False,
        )
        self.assertEqual("abstain", unattested["decision"])
        self.assertEqual("plural_of_plural_base_unattested", unattested["defeater"])

        attested = gates.broken_plural_lexeme_link_gate(
            "ب ي ت", "taksir-jam-al-jam-fuulaat", attested_pair=True,
            plural_of_plural_base_attested=True,
        )
        self.assertEqual("emit", attested["decision"])


class Test18ExampleLocMustMatchRecordedSurface(unittest.TestCase):
    def test_fixed_and_new_rule_examples_surface_match_the_canonical_authority(self):
        index = _load_loc_surface_index()
        payload = json.loads((ROOT / "sarf" / "rules" / "plural-gender-rules.json").read_text(encoding="utf-8"))
        by_id = {p["id"]: p for p in payload["patterns"]}
        for pattern_id in (
            "msl-nominative", "taksir-afal", "taksir-fiaal", "taksir-nisa-suppletive-rare",
        ):
            pattern = by_id[pattern_id]
            loc = pattern["example_loc"]
            self.assertEqual(
                pattern["example"], index.get(loc),
                "%s's example does not surface-match the canonical authority at %s" % (pattern_id, loc),
            )

    def test_second_order_pattern_honestly_declares_no_corpus_attestation(self):
        payload = json.loads((ROOT / "sarf" / "rules" / "plural-gender-rules.json").read_text(encoding="utf-8"))
        pattern = next(p for p in payload["patterns"] if p["id"] == "taksir-jam-al-jam-fuulaat")
        self.assertIsNone(pattern["example_loc"])
        self.assertIsNone(pattern["example"])
        self.assertEqual("not_attested_in_corpus", pattern["example_loc_status"])

    def test_dogfood_occurrences_surface_match_the_canonical_authority(self):
        index = _load_loc_surface_index()
        for row in _load_eval_rows():
            occ = row.get("occurrence")
            if occ is None or row.get("loc_surface_deliberately_mismatched"):
                continue
            self.assertEqual(
                occ["surface"], index.get(occ["loc"]),
                "eval row %s's occurrence does not surface-match the canonical authority" % row["id"],
            )

    def test_deliberately_mismatched_row_is_declared_and_still_abstains(self):
        rows = {row["id"]: row for row in _load_eval_rows()}
        row = rows["plg-eval-19-loc-surface-mismatch-abstains"]
        self.assertTrue(row["loc_surface_deliberately_mismatched"])
        status, reason = _run_eval_row(row)
        self.assertEqual("abstained", status)
        self.assertEqual("loc_surface_mismatch", reason)


class Test19PluralRuleMutationTurnsOneEvalRowRed(unittest.TestCase):
    def test_all_rows_match_their_declared_expectation(self):
        for row in _load_eval_rows():
            with self.subTest(row=row["id"]):
                status, reason = _run_eval_row(row)
                self.assertEqual(row["expected_status"], status)
                self.assertEqual(row.get("expected_reason"), reason)

    def test_flipping_requires_attested_base_turns_exactly_one_row_red(self):
        rows = _load_eval_rows()
        baseline = {row["id"]: _run_eval_row(row) for row in rows}
        for row in rows:
            self.assertEqual(
                (row["expected_status"], row.get("expected_reason")), baseline[row["id"]]
            )

        mutated_payload = copy.deepcopy(gates._load_plural_gender_rules())
        pattern = next(
            p for p in mutated_payload["patterns"] if p["id"] == "taksir-jam-al-jam-fuulaat"
        )
        self.assertTrue(pattern["requires_attested_base"])
        pattern["requires_attested_base"] = False

        flipped = []
        for row in rows:
            payload_for_row = mutated_payload if row.get("consumer") == "gate" else None
            result = _run_eval_row(row, rules_payload=payload_for_row)
            expected = (row["expected_status"], row.get("expected_reason"))
            if result != expected:
                flipped.append(row["id"])
        self.assertEqual(["plg-eval-11-jam-al-jam-base-unattested-abstains"], flipped)


if __name__ == "__main__":
    unittest.main(verbosity=2)
