#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first behavioural gates for tools/run_sarf_evals.py (Burst A1 — sarf eval runner architecture).

These tests are the reason the runner is allowed to claim anything. They are written so that a runner which
merely echoes the fixture files CANNOT pass:

  * POSITIVE    — the real sarf banks run green through the REAL consumers (fusha_text_check.segment_candidates,
                  fusha_morphology_lattice.build_morphology_lattice, fusha_text_check.check_text,
                  corpus_to_qamus_candidates.classify, normalize_ar's key/harakah helpers).
  * NEGATIVE    — synthetic rows that violate a bank contract must FAIL the adapter (not be waved through).
  * ADVERSARIAL — rows that look right but break a controlling invariant (fabricated root, collapsed ambiguity,
                  auto_safe on arbitrary text, a key that still carries the distinguishing harakah) must FAIL.
  * MUTATION    — the consumers themselves are monkeypatched into wrong behaviour; every adapter that CLAIMS to
                  consume them must go RED. This is what separates `implemented_and_consumed` from `fixture_only`.

Plus the lane's standing invariants: every sarf eval artifact carries exactly one truthful disposition, object-form
`cases[]`/`assertions[]` are row-counted like JSONL rows, and no @2.1–@2.4 candidate increment is treated as released.

Run: python -m unittest tools.test_run_sarf_evals -v
"""
import copy
import glob
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools import run_sarf_evals as R  # noqa: E402  (the module under test)


def _ctx():
    """A fresh consumer bundle (real consumers) that a test may mutate without leaking into other tests."""
    return R.Consumers.real()


def _spec(bank):
    return R.bank_spec(R.load_contract(_ROOT), bank)


def _rows(bank):
    return R.load_bank(_ROOT, _spec(bank))


def _run(bank, rows=None, ctx=None):
    """Run one bank's adapter, returning (failures, metrics)."""
    return R.run_adapter(_spec(bank), rows if rows is not None else _rows(bank), ctx or _ctx(), _ROOT)


# ---------------------------------------------------------------------------
# contract / disposition invariants
# ---------------------------------------------------------------------------
class ContractInvariants(unittest.TestCase):

    def test_contract_is_structurally_valid(self):
        errors = R.validate_contract(R.load_contract(_ROOT), _ROOT)
        self.assertEqual(errors, [], "contract structural errors: %s" % errors)

    def test_contract_declared_keys_match_the_schema_twin(self):
        """The JSON schema is the declarative twin of validate_contract(); they must not drift."""
        schema = json.load(open(os.path.join(_ROOT, "qamus", "schemas",
                                             "sarf-eval-runner-contract.schema.json"), encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema"]["const"], R.SCHEMA_ID)
        self.assertEqual(sorted(schema["$defs"]["disposition"]["enum"]), sorted(R.DISPOSITIONS))
        self.assertEqual(sorted(schema["required"]), sorted(R.CONTRACT_REQUIRED))

    def test_every_sarf_eval_artifact_has_exactly_one_disposition(self):
        contract = R.load_contract(_ROOT)
        on_disk = sorted(f for f in os.listdir(os.path.join(_ROOT, "sarf", "evals"))
                         if f.endswith(".jsonl") or f.endswith(".json"))
        declared = [os.path.basename(b["path"]) for b in contract["banks"]]
        self.assertEqual(sorted(declared), on_disk,
                         "every sarf/evals artifact must be dispositioned exactly once")
        self.assertEqual(len(declared), len(set(declared)), "duplicate bank rows in the contract")
        for b in contract["banks"]:
            self.assertIn(b["disposition"], R.DISPOSITIONS)

    def test_store_a_rule_rows_are_dispositioned_and_their_consumers_are_real(self):
        """A Store A rule row may only claim implemented_and_consumed if a named module actually reads the file."""
        contract = R.load_contract(_ROOT)
        on_disk = sorted(f for f in os.listdir(os.path.join(_ROOT, "sarf", "rules")) if f.endswith(".json"))
        declared = [os.path.basename(r["path"]) for r in contract["store_a_rules"]]
        self.assertEqual(sorted(declared), on_disk)
        failures, metrics = R.check_store_a(contract, _ROOT)
        self.assertEqual(failures, [], "store A disposition errors: %s" % failures)
        self.assertGreaterEqual(metrics["implemented_and_consumed"], 1)

    def test_store_a_false_consumer_claim_is_caught(self):
        """ADVERSARIAL: claiming a consumer that does not reference the rule file must FAIL."""
        contract = copy.deepcopy(R.load_contract(_ROOT))
        row = next(r for r in contract["store_a_rules"] if r["disposition"] != "implemented_and_consumed")
        row["disposition"] = "implemented_and_consumed"
        row["consumers"] = ["tools/normalize_ar.py"]  # a real module that never reads sarf/rules/
        failures, _ = R.check_store_a(contract, _ROOT)
        self.assertTrue(failures, "a fabricated consumer claim must be caught")

    def test_behavioural_disposition_requires_named_real_consumers(self):
        contract = R.load_contract(_ROOT)
        for b in contract["banks"]:
            if b["disposition"] == "implemented_and_consumed":
                self.assertTrue(b["consumers"], "%s claims coverage with no consumer" % b["path"])
                for mod in b["consumers"]:
                    self.assertTrue(os.path.exists(os.path.join(_ROOT, mod)), "missing consumer %s" % mod)
                self.assertTrue(b["enforced_properties"], "%s enforces nothing" % b["path"])

    def test_candidate_increments_are_not_promoted(self):
        """@2.1–@2.4 stay CANDIDATE: the contract must record them as unreleased and SKILL.md must still say so."""
        contract = R.load_contract(_ROOT)
        inc = contract["candidate_increments_not_promoted"]
        self.assertEqual(sorted(inc["increments"]), ["sarf@2.1", "sarf@2.2", "sarf@2.3", "sarf@2.4"])
        self.assertEqual(inc["status"], "candidate_not_released")
        failures = R.check_candidates_not_promoted(contract, _ROOT)
        self.assertEqual(failures, [], "candidate promotion detected: %s" % failures)

    def test_row_counting_covers_jsonl_and_object_forms(self):
        contract = R.load_contract(_ROOT)
        counted = {}
        for b in contract["banks"]:
            counted[os.path.basename(b["path"])] = len(R.load_bank(_ROOT, b))
        # object-form banks must be counted through cases[] / assertions[], not treated as 1 row or 0
        self.assertEqual(counted["sarf-state-machine-eval.json"], 26)
        self.assertEqual(counted["qamus-regression-eval.json"], 11)
        self.assertEqual(counted["corpus-authoring-eval.json"], 14)
        self.assertEqual(counted["false-clitic-split-eval.jsonl"], 130)
        self.assertEqual(sum(counted.values()), R.run_all(_ROOT)["total_rows"])


# ---------------------------------------------------------------------------
# POSITIVE — the real banks, through the real consumers
# ---------------------------------------------------------------------------
class RealBanksPass(unittest.TestCase):

    def test_run_all_is_green(self):
        rep = R.run_all(_ROOT)
        self.assertEqual(rep["failures"], [], "real sarf banks failed: %s" % rep["failures"][:5])
        self.assertEqual(rep["exit_code"], 0)
        self.assertGreaterEqual(rep["total_rows"], 380)

    def test_behavioural_banks_actually_decide_every_row(self):
        rep = R.run_all(_ROOT)
        for item in rep["banks"]:
            if item["disposition"] == "implemented_and_consumed":
                self.assertEqual(item["checked"], item["rows"],
                                 "%s claims behavioural coverage but decided %d/%d rows"
                                 % (item["bank"], item["checked"], item["rows"]))
                self.assertIn(item["behavioral_consumer"], R.DECISION_CONSUMERS)
            else:
                self.assertEqual(item["checked"], 0,
                                 "%s is not behaviourally covered but reports %d decided rows"
                                 % (item["bank"], item["checked"]))

    def test_checked_is_not_always_true(self):
        """The old reporter set checked == rows unconditionally. Structural banks must report zero."""
        rep = R.run_all(_ROOT)
        structural = [b for b in rep["banks"] if b["disposition"] != "implemented_and_consumed"]
        self.assertTrue(structural)
        self.assertTrue(all(b["checked"] == 0 for b in structural))
        self.assertEqual(rep["behavioral_rows"] + rep["uncovered_rows"], rep["total_rows"])
        self.assertLess(rep["behavioral_rows"], rep["total_rows"],
                        "uncovered rows must stay visible as gaps")

    def test_required_behavioural_banks_cannot_all_be_relabelled(self):
        """A future change may not make the gate green by calling every bank fixture_only."""
        contract = R.load_contract(_ROOT)
        behavioural = {b["path"] for b in contract["banks"]
                       if b["disposition"] == "implemented_and_consumed"}
        self.assertEqual(behavioural, set(R.REQUIRED_BEHAVIORAL_BANKS))
        for path in R.REQUIRED_BEHAVIORAL_BANKS:
            self.assertGreater(len(R.load_bank(_ROOT, R.bank_spec(contract, path))), 0)

    def test_downgraded_banks_are_not_claimed_as_coverage(self):
        """The two key/hidden-state banks have no decision consumer and must stay uncovered."""
        contract = R.load_contract(_ROOT)
        for path in ("sarf/evals/sarf-state-machine-eval.json", "sarf/evals/qamus-regression-eval.json",
                     "sarf/evals/corpus-authoring-eval.json"):
            spec = R.bank_spec(contract, path)
            self.assertEqual(spec["disposition"], "candidate_no_consumer")
            self.assertIsNone(spec["behavioral_consumer"])
            self.assertTrue(spec["followup_packet"])


class PassThroughAndTargetedMutation(unittest.TestCase):
    """Non-circular proof: the consumer really is called for every row, and ONE wrong result fails precisely."""

    def _counting(self, ctx, attr):
        real = getattr(ctx, attr)
        calls = []

        def wrapper(*a, **kw):
            calls.append(a[0] if a else None)
            return real(*a, **kw)
        setattr(ctx, attr, wrapper)
        return calls

    def test_pass_through_counts_the_contract_declared_callable_exactly(self):
        """Round-2 defect 2: count the EXACT callable the contract declares, not a convenient neighbour."""
        contract = R.load_contract(_ROOT)
        for bank in R.REQUIRED_BEHAVIORAL_BANKS:
            spec = R.bank_spec(contract, bank)
            declared = spec["behavioral_consumer"]
            slot = R.CONSUMER_SLOTS[declared]
            ctx = _ctx()
            calls = self._counting(ctx, slot)
            rows = _rows(bank)
            failures, metrics = _run(bank, rows, ctx)
            self.assertEqual(failures, [], "%s: a pass-through wrapper must stay green (%s)" % (bank, failures[:2]))
            self.assertEqual(len(calls), len(rows),
                             "%s: declared consumer %s ran %d times for %d rows"
                             % (bank, declared, len(calls), len(rows)))
            self.assertEqual(metrics["decided_rows"], len(rows))
            # and the runner's own independent proxy must agree with the test-owned counter
            self.assertEqual(metrics["consumer_calls"][declared], len(rows))

    def test_conditional_consumer_applicability_is_declared_and_counted(self):
        """A checker invoked only on a subset may not be sold as the per-row consumer."""
        bank = "sarf/evals/false-clitic-split-eval.jsonl"
        spec = R.bank_spec(R.load_contract(_ROOT), bank)
        rows = _rows(bank)
        _f, metrics = _run(bank, rows)
        calls = metrics["consumer_calls"]
        self.assertEqual(spec["behavioral_consumer"],
                         "tools/fusha_morphology_lattice.py:build_morphology_lattice")
        self.assertEqual(calls[spec["behavioral_consumer"]], len(rows))
        secondary = spec["secondary_consumers"]
        self.assertTrue(secondary)
        for sec in secondary:
            self.assertEqual(calls[sec["callable"]], sec["expected_calls"])
            self.assertLess(sec["expected_calls"], len(rows), "a subset consumer must declare a subset")
        self.assertTrue(any("reject_" in sec["applies_to"] for sec in secondary))

    def test_declaring_a_subset_consumer_as_the_per_row_consumer_fails(self):
        """ADVERSARIAL: the exact round-1 overclaim — declare check_text, which runs on 29 of 130 rows."""
        contract = copy.deepcopy(R.load_contract(_ROOT))
        spec = R.bank_spec(contract, "sarf/evals/false-clitic-split-eval.jsonl")
        spec["behavioral_consumer"] = "tools/fusha_text_check.py:check_text"
        spec["secondary_consumers"] = []
        rep = R.run_all(_ROOT, contract=contract)
        joined = " ".join(rep["failures"])
        self.assertIn("was invoked 29 time(s) for 130 rows", joined)
        self.assertEqual(rep["exit_code"], 1)

    def test_one_wrong_result_fails_with_exact_row_and_property(self):
        """Mutate the consumer for exactly ONE row; the failure must name that row and the enforced property."""
        bank = "sarf/evals/false-clitic-split-eval.jsonl"
        rows = _rows(bank)
        target = rows[0]["id"]
        target_surface = rows[0]["surface"]
        ctx = _ctx()
        real = ctx.segment_candidates

        def one_bad(surface):
            cands = real(surface)
            if surface == target_surface:
                return [c for c in cands if len(c["segments"]) > 1] or []
            return cands
        ctx.segment_candidates = one_bad
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(failures)
        self.assertTrue(all(f.startswith(target + " ") for f in failures),
                        "only the mutated row may fail, got %s" % failures[:3])
        self.assertTrue(any("[whole_token_reading_preserved]" in f for f in failures),
                        "the failure must name the enforced property, got %s" % failures[:3])

    def test_one_wrong_collision_result_fails_with_exact_row_and_property(self):
        bank = "sarf/evals/largelexicon-collision-safety.jsonl"
        rows = _rows(bank)
        target = rows[1]
        ctx = _ctx()
        real = ctx.check_text

        def one_bad(req):
            rec = copy.deepcopy(real(req))
            if req.get("raw_input") == target["surface"]:
                rec["suggestions"].append({"edit": {"op": "split"}, "gate": "two_vote_required"})
            return rec
        ctx.check_text = one_bad
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(all(f.startswith(target["id"] + " ") for f in failures), failures[:3])
        self.assertTrue(any("[no_split_suggestion]" in f for f in failures), failures[:3])

    def test_one_wrong_byte_exact_result_fails_with_exact_row_and_property(self):
        bank = "sarf/evals/combining-mark-byte-exact-eval.jsonl"
        rows = _rows(bank)
        target = rows[0]
        ctx = _ctx()
        real = ctx.check_text

        def one_bad(req):
            rec = copy.deepcopy(real(req))
            if req.get("raw_input") == target["surface"]:
                rec["raw_input"] = rec["raw_input"].replace("\u06df", "")
            return rec
        ctx.check_text = one_bad
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(failures)
        self.assertTrue(all(f.startswith(target["id"] + " ") for f in failures), failures[:3])
        self.assertTrue(any("[raw_input_preserved]" in f for f in failures), failures[:3])

    def test_one_wrong_lattice_result_fails_with_exact_row_and_property(self):
        bank = "sarf/evals/morphology-candidate-lattice.jsonl"
        rows = _rows(bank)
        target_surface = rows[0]["surface"]
        target_id = rows[0]["id"]
        ctx = _ctx()
        real = ctx.build_lattice

        def one_bad(token_ref, surface, segs, voweled, source_addressed=False, **kw):
            lat = copy.deepcopy(real(token_ref, surface, segs, voweled, source_addressed=source_addressed, **kw))
            if surface == target_surface:
                for c in lat["candidates"]:
                    c["root"] = "ك ت ب"
            return lat
        ctx.build_lattice = one_bad
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(failures)
        self.assertTrue(all(f.startswith(target_id + " ") for f in failures), failures[:3])
        self.assertTrue(any("[forbid_fabricated_root]" in f for f in failures), failures[:3])


# ---------------------------------------------------------------------------
# NEGATIVE + ADVERSARIAL — bad rows must fail, not be waved through
# ---------------------------------------------------------------------------
class NegativeAndAdversarial(unittest.TestCase):

    def test_lattice_row_demanding_impossible_candidate_count_fails(self):
        rows = copy.deepcopy(_rows("sarf/evals/morphology-candidate-lattice.jsonl"))
        rows[0]["expected_min_candidates"] = 99
        failures, _ = _run("sarf/evals/morphology-candidate-lattice.jsonl", rows)
        self.assertTrue(failures)

    def test_clitic_bank_row_with_non_concatenating_surface_fails(self):
        rows = copy.deepcopy(_rows("sarf/evals/false-clitic-split-eval.jsonl"))
        rows[0]["surface"] = ""   # an empty surface cannot carry the whole-token reading
        failures, _ = _run("sarf/evals/false-clitic-split-eval.jsonl", rows)
        self.assertTrue(failures)

    def test_state_machine_key_that_keeps_the_harakah_fails(self):
        """ADVERSARIAL: a declared over-collapsed key that still carries the distinguishing harakah is not a key."""
        rows = copy.deepcopy(_rows("sarf/evals/sarf-state-machine-eval.json"))
        rows[0]["observation"]["norm_key"] = rows[0]["observation"]["surface_ar"]
        failures, _ = _run("sarf/evals/sarf-state-machine-eval.json", rows)
        self.assertTrue(failures)

    def test_state_machine_auto_safe_without_an_external_certifier_fails(self):
        """ADVERSARIAL: auto_safe granted on the collapsed key alone (no qac/wazn) must be rejected."""
        rows = copy.deepcopy(_rows("sarf/evals/sarf-state-machine-eval.json"))
        row = next(r for r in rows if r["expected_gate"] != "auto_safe")
        row["expected_gate"] = "auto_safe"
        row["evidence_required"] = ["norm_strict"]
        failures, _ = _run("sarf/evals/sarf-state-machine-eval.json", rows)
        self.assertTrue(failures)

    def test_regression_bank_pending_downgraded_to_auto_resolve_fails(self):
        """ADVERSARIAL: a colliding key whose gate is relaxed below two-vote must fail (pending is a PASS state)."""
        rows = copy.deepcopy(_rows("sarf/evals/qamus-regression-eval.json"))
        row = next(r for r in rows if r["correct_gloss_or_pending"] == "pending")
        row["expected_gate"] = "auto_safe"
        failures, _ = _run("sarf/evals/qamus-regression-eval.json", rows)
        self.assertTrue(failures)

    def test_regression_bank_cited_gloss_without_the_named_diacritic_fails(self):
        rows = copy.deepcopy(_rows("sarf/evals/qamus-regression-eval.json"))
        row = next(r for r in rows if "@" in r["key"])
        row["surfaces"] = [R.consumers_module("normalize_ar").bare(row["surfaces"][0])]  # strip every mark
        failures, _ = _run("sarf/evals/qamus-regression-eval.json", rows)
        self.assertTrue(failures)

    def test_corpus_bank_key_mismatch_fails(self):
        rows = copy.deepcopy(_rows("sarf/evals/corpus-authoring-eval.json"))
        rows[0]["norm_key"] = "زززز"
        failures, _ = _run("sarf/evals/corpus-authoring-eval.json", rows)
        self.assertTrue(failures)

    def test_structural_bank_missing_required_field_fails(self):
        rows = copy.deepcopy(_rows("sarf/evals/vn00-aggressive-false-closure.jsonl"))
        rows[0]["expected_segments"] = []
        failures, _ = _run("sarf/evals/vn00-aggressive-false-closure.jsonl", rows)
        self.assertTrue(failures)

    def test_documentary_bank_with_a_dangling_procedure_link_fails(self):
        rows = copy.deepcopy(_rows("sarf/evals/surfacemap-wbw-absent-eval.jsonl"))
        rows[0]["procedure_links"] = ["docs/this-file-does-not-exist.md#1"]
        failures, _ = _run("sarf/evals/surfacemap-wbw-absent-eval.jsonl", rows)
        self.assertTrue(failures)


# ---------------------------------------------------------------------------
# MUTATION — break the CONSUMER, not the bank; every claiming adapter must go red
# ---------------------------------------------------------------------------
class ConsumerMutations(unittest.TestCase):

    def test_segmenter_that_drops_the_whole_token_reading_turns_clitic_banks_red(self):
        ctx = _ctx()
        real = ctx.segment_candidates
        ctx.segment_candidates = lambda s: [c for c in real(s) if len(c["segments"]) > 1] or real(s)[1:]
        for bank in ("sarf/evals/false-clitic-split-eval.jsonl",
                     "sarf/evals/morphology-candidate-lattice.jsonl"):
            failures, _ = _run(bank, ctx=ctx)
            self.assertTrue(failures, "%s survived a segmenter that collapses ambiguity" % bank)

    def test_segmenter_that_breaks_byte_exactness_turns_banks_red(self):
        ctx = _ctx()
        real = ctx.segment_candidates

        def mangled(s):
            cands = copy.deepcopy(real(s))
            cands[0]["segments"][0]["surface"] = cands[0]["segments"][0]["surface"].replace("ٱ", "ا")
            return cands
        ctx.segment_candidates = mangled
        failures, _ = _run("sarf/evals/combining-mark-byte-exact-eval.jsonl", ctx=ctx)
        self.assertTrue(failures, "a normalizing (non byte-exact) segmenter must fail the byte-exact bank")

    def test_lattice_that_fabricates_a_root_turns_the_lattice_bank_red(self):
        ctx = _ctx()
        real = ctx.build_lattice

        def fabricating(*a, **kw):
            lat = copy.deepcopy(real(*a, **kw))
            for c in lat["candidates"]:
                c["root"] = "ك ت ب"
            return lat
        ctx.build_lattice = fabricating
        failures, _ = _run("sarf/evals/morphology-candidate-lattice.jsonl", ctx=ctx)
        self.assertTrue(failures, "a fabricated root must fail (blank beats a fabricated value)")

    def test_lattice_that_forces_one_parse_turns_the_lattice_bank_red(self):
        ctx = _ctx()
        real = ctx.build_lattice

        def forcing(*a, **kw):
            lat = copy.deepcopy(real(*a, **kw))
            lat["candidates"] = lat["candidates"][:1]
            lat["n_candidates"] = 1
            return lat
        ctx.build_lattice = forcing
        failures, _ = _run("sarf/evals/morphology-candidate-lattice.jsonl", ctx=ctx)
        self.assertTrue(failures, "forcing a single parse must fail the ambiguity contract")

    def test_lattice_that_auto_safes_arbitrary_text_turns_the_lattice_bank_red(self):
        ctx = _ctx()
        real = ctx.build_lattice

        def unsafe(*a, **kw):
            lat = copy.deepcopy(real(*a, **kw))
            for c in lat["candidates"]:
                c["gate"] = "auto_safe"
            return lat
        ctx.build_lattice = unsafe
        failures, _ = _run("sarf/evals/morphology-candidate-lattice.jsonl", ctx=ctx)
        self.assertTrue(failures, "arbitrary-text candidates may never be auto_safe")

    def test_checker_that_lets_a_collision_split_escape_turns_the_collision_bank_red(self):
        ctx = _ctx()
        real = ctx.check_text

        def leaky(req):
            rec = copy.deepcopy(real(req))
            rec["suggestions"].append({"edit": {"op": "split"}, "gate": "two_vote_required"})
            return rec
        ctx.check_text = leaky
        failures, _ = _run("sarf/evals/largelexicon-collision-safety.jsonl", ctx=ctx)
        self.assertTrue(failures, "a split suggestion on a collision surface must fail quarantine")

    def test_norm_strict_that_drops_hamza_seats_turns_the_state_machine_red(self):
        """norm() never certifies: if the strict key stops preserving the hamza seat, the bank must go red."""
        ctx = _ctx()
        ctx.norm_strict = ctx.norm
        failures, _ = _run("sarf/evals/sarf-state-machine-eval.json", ctx=ctx)
        self.assertTrue(failures, "a hamza-blind strict key must fail the hidden-state bank")

    def test_key_that_stops_stripping_harakat_turns_the_regression_bank_red(self):
        ctx = _ctx()
        ctx.norm_strict = lambda s: s
        for bank in ("sarf/evals/qamus-regression-eval.json", "sarf/evals/sarf-state-machine-eval.json"):
            failures, _ = _run(bank, ctx=ctx)
            self.assertTrue(failures, "%s survived a key that keeps the distinguishing harakah" % bank)

    def test_shadda_detector_that_always_says_no_turns_the_regression_bank_red(self):
        ctx = _ctx()
        ctx.shadda_on = lambda tok, target: False
        failures, _ = _run("sarf/evals/qamus-regression-eval.json", ctx=ctx)
        self.assertTrue(failures, "a blind shadda detector must fail the cited form-aware assertions")

    def test_tanwin_alef_guard_disabled_turns_the_clitic_bank_red(self):
        ctx = _ctx()
        ctx.ends_tanwin_alef = lambda raw: False
        real = ctx.segment_candidates

        def peeling(s):
            cands = copy.deepcopy(real(s))
            if s.endswith("ا"):
                cands.append({"segments": [{"role": "stem", "surface": s[:-2]},
                                           {"role": "object_pronoun", "surface": s[-2:]}],
                              "rank": 0, "score": None, "legal": True, "single_letter_clitic": False})
            return cands
        ctx.segment_candidates = peeling
        failures, _ = _run("sarf/evals/false-clitic-split-eval.jsonl", ctx=ctx)
        self.assertTrue(failures, "tanwīn-alif peeled as the pronoun نا must fail")

    def test_classifier_drift_turns_the_corpus_bank_red(self):
        """The measured agreement with the intended differ contract is PINNED; drift (either way) is a red gate."""
        ctx = _ctx()
        ctx.classify = lambda tok, surf, roots: ("new_root", None)
        failures, _ = _run("sarf/evals/corpus-authoring-eval.json", ctx=ctx)
        self.assertTrue(failures, "classifier drift must be caught by the pinned agreement metric")

    def test_classifier_that_mints_on_an_existing_entry_turns_the_corpus_bank_red(self):
        ctx = _ctx()
        ctx.classify = lambda tok, surf, roots: ("already_in_qamus", {"entry_id": "fake", "root": "ك ت ب"})
        failures, _ = _run("sarf/evals/corpus-authoring-eval.json", ctx=ctx)
        self.assertTrue(failures)


# ---------------------------------------------------------------------------
# self-test + CLI surface (what the harness and golden commands invoke)
# ---------------------------------------------------------------------------
class RunnerCli(unittest.TestCase):

    def test_self_test_mode_is_green(self):
        self.assertEqual(R.self_test(_ROOT), 0)

    def test_all_bank_mode_exit_zero_and_prints_terminal_marker(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = R.main(["--all", "--root", _ROOT])
        self.assertEqual(rc, 0)
        self.assertIn(R.TERMINAL_PASS, buf.getvalue())

    def test_unknown_bank_selection_fails_closed(self):
        """A typo must not filter to an empty set and print a pass marker."""
        import io as _io
        import contextlib
        for bogus in ("sarf/evals/does-not-exist.jsonl", "false-clitic-split-eval.jsonl.typo", "nonsense"):
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = R.main(["--bank", bogus, "--root", _ROOT])
            self.assertEqual(rc, 1, "unknown bank %r must exit 1" % bogus)
            self.assertNotIn(R.TERMINAL_PASS, buf.getvalue())
            self.assertIn("unknown --bank selection", buf.getvalue())

    def test_targeted_pass_names_the_bank_and_a_nonzero_row_count(self):
        import io as _io
        import contextlib
        bank = "sarf/evals/false-clitic-split-eval.jsonl"
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = R.main(["--bank", bank, "--root", _ROOT])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn(bank, out)
        self.assertIn("130 rows (130 decided;", out)
        self.assertIn(R.TERMINAL_PASS, out)

    def test_zero_row_bank_is_never_a_pass(self):
        rep = R.run_all(_ROOT, only="sarf/evals/false-clitic-split-eval.jsonl", ctx=_ctx())
        self.assertEqual(rep["exit_code"], 0)
        self.assertGreater(rep["total_rows"], 0)
        empty = copy.deepcopy(R.bank_spec(R.load_contract(_ROOT), "sarf/evals/false-clitic-split-eval.jsonl"))
        failures, metrics = R.run_adapter(empty, [], _ctx(), _ROOT)
        self.assertEqual(metrics["decided_rows"], 0)

    def test_store_a_behavioural_claim_needs_a_mutation_prover(self):
        """A filename reference proves discovery; only a bounded content mutation proves consumption."""
        contract = copy.deepcopy(R.load_contract(_ROOT))
        row = next(r for r in contract["store_a_rules"] if r["path"] == "sarf/rules/hamza-gates.json")
        row["disposition"] = "implemented_and_consumed"
        row["consumption_kind"] = "data_driven"
        failures, _ = R.check_store_a(contract, _ROOT)
        self.assertTrue(any("mutation prover" in f for f in failures), failures[:3])

    def test_only_data_driven_store_a_rows_claim_consumption(self):
        contract = R.load_contract(_ROOT)
        for r in contract["store_a_rules"]:
            if r["disposition"] == "implemented_and_consumed":
                self.assertEqual(r["consumption_kind"], "data_driven")
                # every DECLARED consumer must have its own prover bound to it, not just the rule file
                for consumer in r["consumers"]:
                    self.assertIn((r["path"], consumer), R.DATA_DRIVEN_PROVERS)
            else:
                self.assertNotEqual(r["consumption_kind"], "data_driven")
        self.assertNotIn("tools/investigate_gap_residue.py",
                         [c for r in contract["store_a_rules"] for c in r["consumers"]])

    def test_corpus_improvement_is_accepted_not_rejected(self):
        """Round-2 defect 1: moving the unprefixed case-inflected row to the expected class must be GREEN."""
        bank = "sarf/evals/corpus-authoring-eval.json"
        spec = _spec(bank)
        rows = _rows(bank)
        target = next(r for r in rows if r["expected_class"] == "new_surface")
        token = target["token"]["surface_ar"]
        base_failures, base_metrics = _run(bank, rows)
        self.assertEqual(base_failures, [])
        ctx = _ctx()
        real = ctx.classify
        ctx.classify = (lambda t, surf, roots:
                        ("new_surface_existing_lemma", None) if t == token else real(t, surf, roots))
        failures, metrics = _run(bank, rows, ctx)
        self.assertEqual(failures, [],
                         "an improvement on the unprefixed inflectional row must not fail: %s" % failures[:3])
        self.assertGreater(metrics["contract_agreement"], base_metrics["contract_agreement"])
        self.assertGreaterEqual(metrics["contract_agreement"], spec["metric_floors"]["contract_agreement"])
        self.assertIn("inflectional_ending", metrics["new_surface_licences"])
        # and the bank stays candidate-mode: improvement never promotes the six-class contract
        self.assertEqual(spec["disposition"], "candidate_no_consumer")
        self.assertEqual(metrics["decided_rows"], 0)

    def test_agreement_is_floored_not_pinned(self):
        """Only regression below a floor may be red; improvement must pass."""
        spec = _spec("sarf/evals/corpus-authoring-eval.json")
        self.assertIn("contract_agreement", spec["metric_floors"])
        self.assertNotIn("contract_agreement", spec["pinned_metrics"])
        self.assertNotIn("disagreements", spec["pinned_metrics"])
        lattice = _spec("sarf/evals/morphology-candidate-lattice.jsonl")
        self.assertIn("evidence_class_agreement", lattice["metric_floors"])
        self.assertNotIn("evidence_class_agreement", lattice["pinned_metrics"])
        improved = dict(spec["pinned_metrics"]); improved["contract_agreement"] = 99
        regressed = dict(spec["pinned_metrics"]); regressed["contract_agreement"] = 0
        self.assertEqual(R._pin_failures(spec, improved), [], "improvement above the floor must never be red")
        self.assertTrue(R._pin_failures(spec, regressed), "regression below the floor must be red")

    def test_unlicensed_new_surface_still_fails(self):
        """The laundering guard must survive the round-2 relaxation."""
        bank = "sarf/evals/corpus-authoring-eval.json"
        rows = copy.deepcopy(_rows(bank))
        rows[0]["token"]["surface_ar"] = "زززز"
        rows[0]["norm_key"] = "زززز"
        ctx = _ctx()
        ctx.classify = lambda t, surf, roots: ("new_surface_existing_lemma", None)
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(any("[new_surface_morphologically_licensed]" in f for f in failures), failures[:3])

    def test_store_a_prover_is_bound_to_the_declared_consumer(self):
        """Round-2 defect 3: a prover for module A may not satisfy a declaration naming module B."""
        contract = copy.deepcopy(R.load_contract(_ROOT))
        row = next(r for r in contract["store_a_rules"] if r["path"] == "sarf/rules/verb-measures.json")
        self.assertEqual(row["consumers"], ["tools/fusha_paradigm_generate.py"])
        # the demonstrated replacement: swap the declared consumer for the module that only holds a constant
        row["consumers"] = ["tools/rm40_gate_stack.py"]
        failures, _ = R.check_store_a(contract, _ROOT)
        self.assertTrue(any("no bounded mutation prover bound to it" in f for f in failures),
                        "replacing the declared consumer must fail closed, got %s" % failures[:3])

    def test_rm40_is_not_claimed_as_a_verb_measures_consumer(self):
        contract = R.load_contract(_ROOT)
        row = next(r for r in contract["store_a_rules"] if r["path"] == "sarf/rules/verb-measures.json")
        self.assertNotIn("tools/rm40_gate_stack.py", row["consumers"])

    def test_coverage_declaration_alone_never_manufactures_a_runner(self):
        """Round-2 defect 4: the coverage self-test carries the no-runner and comment-only probes."""
        from tools import fusha_eval_coverage as COV
        self.assertEqual(COV._self_test(), 0)
        rep = COV.report(_ROOT)
        for item in rep["items"]:
            if item["has_behavioral_runner"]:
                self.assertTrue(item["has_runner"], "%s: behavioural coverage without an invoked runner result"
                                % item["bank"])
                self.assertGreater(item["rows"], 0)
                self.assertEqual(item["decided_rows"], item["rows"])
        declared_only = [i["bank"] for i in rep["items"]
                         if i["declared_disposition"] and not i["has_behavioral_runner"]]
        self.assertTrue(declared_only, "expected declared-but-not-covered banks to stay visible")

    # ---------------- round 3 counterexamples ----------------

    def test_byte_exact_bank_fails_when_its_declared_consumer_is_stubbed(self):
        """Round-3 defect 1: a stub check_text that only echoes raw_input must NOT yield a green bank."""
        bank = "sarf/evals/combining-mark-byte-exact-eval.jsonl"
        rows = _rows(bank)
        ctx = _ctx()
        ctx.check_text = lambda req: {"raw_input": req.get("raw_input"), "suggestions": [], "gates": [],
                                      "analysis_tokens": [], "checker_summary": {"live_writes": 0}}
        failures, metrics = _run(bank, rows, ctx)
        self.assertTrue(failures, "a stubbed declared consumer must fail the bank")
        self.assertTrue(all("[checker_segments_byte_exact]" in f for f in failures), failures[:3])
        self.assertTrue(any(f.startswith(rows[0]["id"] + " ") for f in failures), failures[:3])
        self.assertEqual(metrics["property_hits"]["checker_segments_byte_exact"]["rows"], len(rows))

    def test_byte_exact_single_row_destructive_mutation_names_bank_row_and_property(self):
        bank = "sarf/evals/combining-mark-byte-exact-eval.jsonl"
        rows = _rows(bank)
        target = rows[1]
        ctx = _ctx()
        real = ctx.check_text

        def one_bad(req):
            rec = copy.deepcopy(real(req))
            if req.get("raw_input") == target["surface"]:
                for tok in rec.get("analysis_tokens") or []:
                    tok["segment_candidates"] = []
            return rec
        ctx.check_text = one_bad
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(failures)
        self.assertTrue(all(f.startswith(target["id"] + " ") for f in failures), failures[:3])
        self.assertTrue(any("[checker_segments_byte_exact]" in f for f in failures), failures[:3])
        rep = R.run_all(_ROOT)
        item = next(b for b in rep["banks"] if b["bank"] == bank)
        self.assertIn("marks_transparent_to_matching", item["uncovered_properties"])
        self.assertIn("cluster_alignment", item["uncovered_properties"])

    def test_property_granular_coverage_does_not_hide_the_lattice_mismatch(self):
        """Round-3 defect 2: a successful assertion may not hide the two evidence-class mismatches."""
        rep = R.run_all(_ROOT)
        item = next(b for b in rep["banks"] if "morphology-candidate-lattice" in b["bank"])
        self.assertIn("evidence_class_agreement", item["uncovered_properties"])
        self.assertNotIn("evidence_class_agreement", item["covered_properties"])
        self.assertEqual(item["metrics"]["evidence_class_mismatch_rows"], ["MCL-002", "MCL-005"])
        spec = _spec("sarf/evals/morphology-candidate-lattice.jsonl")
        prop = next(p for p in spec["property_coverage"] if p["property"] == "evidence_class_agreement")
        self.assertFalse(prop["covered"])
        self.assertTrue(prop["decided_by"].startswith("structural:"))
        self.assertIn("TP-SARF-A1-LATTICE-EVIDENCE-CLASS", prop["note"])
        self.assertGreater(rep["uncovered_property_count"], 0)

    def test_a_structural_property_may_never_be_marked_covered(self):
        contract = copy.deepcopy(R.load_contract(_ROOT))
        spec = R.bank_spec(contract, "sarf/evals/morphology-candidate-lattice.jsonl")
        prop = next(p for p in spec["property_coverage"] if p["property"] == "evidence_class_agreement")
        prop["covered"] = True
        errors = R.validate_contract(contract, _ROOT)
        self.assertTrue(any("decided structurally" in e for e in errors), errors[:3])

    def test_candidate_boundary_catches_certified_public_and_target_records(self):
        """Round-3 defect 3: synthetic certified-state / public-allowed / public-target mutations must fail."""
        contract = R.load_contract(_ROOT)
        ids = set()
        for rel in contract["candidate_increments_not_promoted"]["registry_files"].values():
            with open(os.path.join(_ROOT, rel.replace("/", os.sep)), encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        ids.add(json.loads(line)["skill_rule_id"])
        cid = sorted(ids)[0]
        for label, record in (
                ("certified", {"rule_id": cid, "certification_state": "certified"}),
                ("public_allowed", {"rule_id": cid, "public_materialization_allowed": True}),
                ("public_target", {"rule_id": cid, "public_target": "qamus/public/whatever.json"}),
                ("nested", {"projection": {"skill_rule_ids": [cid], "status": "released"}})):
            hits = R.candidate_boundary_violations([("synthetic", record)], ids)
            self.assertTrue(hits, "%s mutation was not caught" % label)
            # and through the full check, so the wiring (not just the predicate) is proven
            full = R.check_candidate_registry_state(contract, _ROOT, extra_records=[("synthetic", record)])
            self.assertTrue(any("candidate boundary" in f for f in full), "%s: %s" % (label, full[:2]))
        # a record that cites nothing candidate-linked is not a violation
        self.assertEqual(R.candidate_boundary_violations(
            [("synthetic", {"rule_id": "not-a-candidate", "certification_state": "certified"})], ids), [])

    def test_candidate_boundary_scans_the_real_declared_surfaces(self):
        contract = R.load_contract(_ROOT)
        records = R.load_boundary_records(contract, _ROOT)
        self.assertGreaterEqual(len(records),
                                contract["candidate_boundary_surfaces"]["expected_records_scanned_min"])
        sources = {src for src, _doc in records}
        self.assertTrue(any(src.startswith("qamus/certification/") for src in sources))
        self.assertIn("qamus/lattice/registered-projectors.json", sources)
        self.assertEqual(R.check_candidate_registry_state(contract, _ROOT), [])

    def test_targeted_run_never_claims_the_boundary_was_verified(self):
        rep = R.run_all(_ROOT, only="sarf/evals/false-clitic-split-eval.jsonl")
        self.assertEqual(rep["candidate_boundary"], "not_checked")
        text = R.render(rep)
        self.assertIn("candidate/projector/public boundary: not_checked", text)
        self.assertNotIn("boundary: verified", text)
        full = R.run_all(_ROOT)
        self.assertEqual(full["candidate_boundary"], "verified")

    def test_contract_schema_is_actually_executed(self):
        """Round-3 defect 4: unknown keys, duplicate entries and path escapes must all fail."""
        base = R.load_contract(_ROOT)
        self.assertEqual(R.validate_contract(base, _ROOT), [])
        unknown = copy.deepcopy(base)
        unknown["banks"][0]["UNKNOWN_KEY"] = 1
        self.assertTrue(any("additional property 'UNKNOWN_KEY' is forbidden" in e
                            for e in R.validate_contract(unknown, _ROOT)))
        top = copy.deepcopy(base)
        top["not_in_schema"] = True
        self.assertTrue(any("additional property 'not_in_schema' is forbidden" in e
                            for e in R.validate_contract(top, _ROOT)))
        dup = copy.deepcopy(base)
        dup["banks"].append(copy.deepcopy(dup["banks"][0]))
        self.assertTrue(any("duplicate bank entry" in e for e in R.validate_contract(dup, _ROOT)))
        dup_rule = copy.deepcopy(base)
        dup_rule["store_a_rules"].append(copy.deepcopy(dup_rule["store_a_rules"][0]))
        self.assertTrue(any("duplicate store A entry" in e for e in R.validate_contract(dup_rule, _ROOT)))
        for bad_path in ("../outside/x.jsonl", "/etc/passwd", "nahw/evals/x.jsonl"):
            esc = copy.deepcopy(base)
            esc["banks"][0]["path"] = bad_path
            errs = R.validate_contract(esc, _ROOT)
            self.assertTrue(any("escapes the repository" in e or "outside the allowed roots" in e
                                or "is absolute" in e for e in errs), "%s: %s" % (bad_path, errs[:3]))
        wrong_type = copy.deepcopy(base)
        wrong_type["banks"][0]["pinned_metrics"] = "not-an-object"
        self.assertTrue(any("expected type object" in e for e in R.validate_contract(wrong_type, _ROOT)))

    def test_schema_executor_implements_every_keyword_the_schema_uses(self):
        self.assertEqual(R._schema_keyword_coverage(R.load_schema(_ROOT)), [])

    def test_followon_packets_match_the_machine_truth(self):
        """Round-3 defect 5: a packet may not contradict the runner it is derived from."""
        contract = R.load_contract(_ROOT)
        packets = {}
        for path in sorted(glob.glob(os.path.join(_ROOT, "qamus", "task-packets", "TP-SARF-A1-*.json"))):
            with open(path, encoding="utf-8") as fh:
                pkt = json.load(fh)
            packets[pkt["packet_id"]] = pkt
        # every followup_packet a bank or rule row names must exist
        referenced = {b["followup_packet"] for b in contract["banks"] if b["followup_packet"]}
        referenced |= {r.get("followup_packet") for r in contract["store_a_rules"] if r.get("followup_packet")}
        self.assertTrue(referenced <= set(packets), "dangling followup packet: %s" % (referenced - set(packets)))
        # sizes must match the measured population
        rep = R.run_all(_ROOT)
        rows_by_bank = {b["bank"]: b["rows"] for b in rep["banks"]}
        self.assertEqual(packets["TP-SARF-A1-DERIVATIVE-CONSUMER"]["candidate_population"]["this_packet_size"],
                         rows_by_bank["sarf/evals/nominal-derivative-error-eval.jsonl"])
        self.assertEqual(packets["TP-SARF-A1-VN00-HOVER-CONSUMER"]["candidate_population"]["this_packet_size"],
                         rows_by_bank["sarf/evals/vn00-public-visual-andon.jsonl"]
                         + rows_by_bank["sarf/evals/vn00-aggressive-false-closure.jsonl"])
        self.assertEqual(packets["TP-SARF-A1-KEY-RESOLVER-CONSUMER"]["candidate_population"]["this_packet_size"],
                         rows_by_bank["sarf/evals/sarf-state-machine-eval.json"]
                         + rows_by_bank["sarf/evals/qamus-regression-eval.json"])
        uncovered_rules = [r for r in contract["store_a_rules"]
                           if r["disposition"] != "implemented_and_consumed"]
        self.assertEqual(packets["TP-SARF-A1-STORE-A-WIRING"]["candidate_population"]["this_packet_size"],
                         len(uncovered_rules))
        lattice = next(b for b in rep["banks"] if "morphology-candidate-lattice" in b["bank"])
        self.assertEqual(packets["TP-SARF-A1-LATTICE-EVIDENCE-CLASS"]["candidate_population"]["this_packet_size"],
                         len(lattice["metrics"]["evidence_class_mismatch_rows"]))
        for pid, pkt in packets.items():
            joined = " ".join(pkt["guards"])
            self.assertIn("authorizes NO certification", joined, "%s: missing the no-authority guard" % pid)
            # the linguistic sources of truth stay immutable, the narrow machinery is writable
            prohibited = pkt["inputs"]["prohibited_files"]
            for immutable in ("sarf/evals/", "sarf/rules/", "qamus/skills/", "qamus/lattice/",
                              "qamus/certification/"):
                self.assertIn(immutable, prohibited, "%s: %s must stay immutable" % (pid, immutable))
            permitted = pkt["inputs"]["permitted_write_files"]
            for needed in ("tools/run_sarf_evals.py", "tools/test_run_sarf_evals.py",
                           "tools/check_regressions.py", "docs/golden-commands.md"):
                self.assertIn(needed, permitted, "%s: %s must be writable to wire a consumer" % (pid, needed))
            self.assertFalse(set(permitted) & set(prohibited), "%s: write-scope overlap" % pid)
            for cmd in pkt["commands"] + pkt["acceptance_tests"]:
                run = cmd["run"]
                self.assertTrue(run.startswith("python "), "%s: %r is not an exact command" % (pid, run))
                for token in run.split():
                    if token.startswith(("tools/", "qamus/", "sarf/", "docs/")) and not token.endswith(","):
                        if "test_" in token or token.endswith(".py"):
                            self.assertTrue(os.path.exists(os.path.join(_ROOT, token))
                                            or token.startswith("tools/test_")
                                            or "fusha_wazn_match" in token or "sarf_rule_consumers" in token
                                            or "fusha_key_resolver" in token
                                            or "validate_vn00_hover_projection" in token
                                            or "corpus_to_qamus_candidates" in token,
                                            "%s: command references a missing tool %r" % (pid, token))

    # ---------------- round 4 counterexamples ----------------

    def test_relabelling_a_property_callable_breaks_coverage(self):
        """Round-4 defect 1: a covered property must be bound to the callable the contract names."""
        contract = copy.deepcopy(R.load_contract(_ROOT))
        spec = R.bank_spec(contract, "sarf/evals/combining-mark-byte-exact-eval.jsonl")
        prop = next(p for p in spec["property_coverage"] if p["property"] == "checker_segments_byte_exact")
        prop["decided_by"] = "tools/corpus_to_qamus_candidates.py:classify"
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertTrue(any("must be bound to its declared callable" in f for f in rep["failures"]),
                        rep["failures"][:3])
        item = next(b for b in rep["banks"] if "combining-mark" in b["bank"])
        self.assertNotIn("checker_segments_byte_exact", item["covered_properties"])

    def test_a_fictitious_zero_row_property_cannot_raise_coverage(self):
        base = R.run_all(_ROOT)
        contract = copy.deepcopy(R.load_contract(_ROOT))
        spec = R.bank_spec(contract, "sarf/evals/combining-mark-byte-exact-eval.jsonl")
        spec["property_coverage"].append({"property": "fictitious_property", "applicable_rows": 0,
                                          "covered": True,
                                          "decided_by": "tools/fusha_text_check.py:check_text"})
        errors = R.validate_contract(contract, _ROOT)
        self.assertTrue(any("zero-row property may never raise coverage" in e for e in errors), errors[:3])
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertLessEqual(rep["covered_property_count"], base["covered_property_count"])

    def test_a_duplicate_property_row_is_rejected(self):
        contract = copy.deepcopy(R.load_contract(_ROOT))
        spec = R.bank_spec(contract, "sarf/evals/morphology-candidate-lattice.jsonl")
        spec["property_coverage"].append(copy.deepcopy(spec["property_coverage"][0]))
        self.assertTrue(any("declares property" in e and "2 times" in e
                            for e in R.validate_contract(contract, _ROOT)))

    def test_every_enforced_lattice_property_has_a_contract_row_and_a_counter(self):
        """score_present and no_boolean_correct were enforced without a declaration or a counter."""
        rep = R.run_all(_ROOT)
        item = next(b for b in rep["banks"] if "morphology-candidate-lattice" in b["bank"])
        hits = item["metrics"]["property_hits"]
        spec = _spec("sarf/evals/morphology-candidate-lattice.jsonl")
        declared = {p["property"] for p in spec["property_coverage"]}
        for key in ("score_present", "no_boolean_correct"):
            self.assertIn(key, declared)
            self.assertIn(key, hits)
            self.assertEqual(hits[key]["rows"], item["rows"])
            self.assertIn(key, item["covered_properties"])
        self.assertEqual(set(hits), declared, "declared and observed property sets must match exactly")
        for key, hit in hits.items():
            self.assertEqual(len(hit["row_ids"]), hit["rows"], "%s: row ids must be recorded" % key)

    def test_ambiguity_preservation_is_not_vacuous(self):
        """Round-4 defect 2: a selective echo stub with empty analysis_tokens must fail that exact row."""
        bank = "sarf/evals/largelexicon-collision-safety.jsonl"
        rows = _rows(bank)
        target = rows[1]
        ctx = _ctx()
        real = ctx.check_text

        def selective(req):
            if req.get("raw_input") == target["surface"]:
                return {"raw_input": req["raw_input"], "suggestions": [], "gates": [],
                        "analysis_tokens": [], "checker_summary": {"live_writes": 0}}
            return real(req)
        ctx.check_text = selective
        failures, _ = _run(bank, rows, ctx)
        self.assertTrue(failures, "an empty-token echo stub must not pass vacuously")
        self.assertTrue(all(f.startswith(target["id"] + " ") for f in failures), failures[:3])
        self.assertTrue(any("[ambiguity_preserved]" in f for f in failures), failures[:3])

        # and a token that survives with a single segmentation is also a collapse
        def collapsed(req):
            rec = copy.deepcopy(real(req))
            if req.get("raw_input") == target["surface"]:
                for tok in rec.get("analysis_tokens") or []:
                    tok["segment_candidates"] = (tok.get("segment_candidates") or [])[:1]
            return rec
        ctx.check_text = collapsed
        failures2, _ = _run(bank, rows, ctx)
        self.assertTrue(any("[ambiguity_preserved]" in f and f.startswith(target["id"] + " ")
                            for f in failures2), failures2[:3])

    def test_nested_candidate_linkage_is_inherited(self):
        """Round-4 defect 3: a parent's candidate id must reach descendant objects and array elements."""
        contract = R.load_contract(_ROOT)
        ids = set()
        for rel in contract["candidate_increments_not_promoted"]["registry_files"].values():
            with open(os.path.join(_ROOT, rel.replace("/", os.sep)), encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        ids.add(json.loads(line)["skill_rule_id"])
        cid = sorted(ids)[0]
        cases = {
            "child certified": {"rule_id": cid, "child": {"certification_state": "certified"}},
            "grandchild certified": {"rule_id": cid, "a": {"b": {"c": {"status": "released"}}}},
            "array public flag": {"rule_id": cid, "rows": [{"public_materialization_allowed": True}]},
            "deep public target": {"skill_rule_ids": [cid],
                                   "p": [{"q": {"public_target": "qamus/public/x.json"}}]},
        }
        for label, record in cases.items():
            hits = R.candidate_boundary_violations([("synthetic", record)], ids)
            self.assertTrue(hits, "%s was not caught" % label)
        # object-local ids still work, and an unlinked subtree stays clean
        self.assertTrue(R.candidate_boundary_violations(
            [("synthetic", {"x": {"rule_id": cid, "certification_state": "certified"}})], ids))
        self.assertEqual(R.candidate_boundary_violations(
            [("synthetic", {"unrelated": {"certification_state": "certified"}})], ids), [])

    def test_every_path_bearing_contract_field_is_contained(self):
        """Round-4 defect 4: candidate record roots and registries must be contained, not only banks/Store A."""
        base = R.load_contract(_ROOT)
        for bad in ("../outside", "/etc", "qamus/certification/../../..", "https://example.invalid/x"):
            contract = copy.deepcopy(base)
            contract["candidate_boundary_surfaces"]["record_roots"][0] = bad
            errors = R.validate_contract(contract, _ROOT)
            self.assertTrue(any("record_roots[0]" in e for e in errors), "%s: %s" % (bad, errors[:3]))
            # and the loader must refuse to perform I/O against it
            records = R.load_boundary_records(contract, _ROOT)
            self.assertLess(len(records), len(R.load_boundary_records(base, _ROOT)))
        for field, value in (("projector_registry", "../outside/registry.json"),):
            contract = copy.deepcopy(base)
            contract["candidate_boundary_surfaces"][field] = value
            self.assertTrue(any(field in e for e in R.validate_contract(contract, _ROOT)))
        contract = copy.deepcopy(base)
        contract["candidate_increments_not_promoted"]["registry_files"]["sarf@2.1"] = "../outside/reg.jsonl"
        self.assertTrue(any("registry_files[sarf@2.1]" in e for e in R.validate_contract(contract, _ROOT)))
        # a symlink that resolves outside the worktree is refused even with a clean-looking relative path
        import tempfile
        with tempfile.TemporaryDirectory() as outside:
            link = os.path.join(_ROOT, "qamus", "certification", "_a1_symlink_probe")
            try:
                os.symlink(outside, link)
            except (OSError, NotImplementedError, AttributeError):
                # Symlinks are not creatable in every environment, so the CONTAINMENT BRANCH is still exercised
                # deterministically by simulating a path that resolves outside the worktree.
                real = os.path.realpath

                def escaping(p, _real=real, _out=outside):
                    return _out if "_a1_symlink_probe" in str(p) else _real(p)
                os.path.realpath = escaping
                try:
                    errs = R._path_escape_errors("qamus/certification/_a1_symlink_probe",
                                                 R._ALLOWED_BOUNDARY_ROOTS, "probe", _ROOT)
                    self.assertTrue(any("symlink escape" in e for e in errs), errs)
                finally:
                    os.path.realpath = real
                return
            try:
                errs = R._path_escape_errors("qamus/certification/_a1_symlink_probe",
                                             R._ALLOWED_BOUNDARY_ROOTS, "probe", _ROOT)
                self.assertTrue(any("symlink escape" in e for e in errs), errs)
            finally:
                os.remove(link)

    def test_coverage_refuses_a_failed_or_foreign_runner_result(self):
        """Round-4 defect 5: a failed, schema-invalid or out-of-repo runner yields no behavioural coverage."""
        from tools import fusha_eval_coverage as COV
        for mutate in (lambda r: dict(r, exit_code=1),
                       lambda r: dict(r, failures=["schema invalid"], exit_code=1),
                       lambda r: dict(r, schema="wrong.schema.v9"),
                       lambda r: dict(r, banks=[])):
            results = COV.runner_results(_ROOT, invoke=lambda m, e, root, _m=mutate: _m(
                getattr(m, e["callable"])(root)))
            self.assertFalse(any(COV.behavioral_coverage(v) for v in results.values()))

        class _Outside(object):
            __file__ = os.path.join(os.sep, "elsewhere", "tools", "run_sarf_evals.py")
        self.assertFalse(COV.module_in_root(_Outside(), _ROOT))
        self.assertTrue(COV.module_in_root(R, _ROOT))
        # the honest baseline still reports coverage
        self.assertTrue(any(v.get("runner_ok") for v in COV.runner_results(_ROOT).values()))

    def test_store_a_packet_scopes_every_non_consumed_rule(self):
        """Round-4 defect 6: the packet's scoped set must equal the machine inventory it claims to close."""
        contract = R.load_contract(_ROOT)
        non_consumed = sorted(r["path"] for r in contract["store_a_rules"]
                              if r["disposition"] != "implemented_and_consumed")
        with open(os.path.join(_ROOT, "qamus", "task-packets", "TP-SARF-A1-STORE-A-WIRING.json"),
                  encoding="utf-8") as fh:
            pkt = json.load(fh)
        self.assertEqual(pkt["candidate_population"]["this_packet_size"], len(non_consumed))
        self.assertEqual(pkt["candidate_population"]["universe_size"], len(contract["store_a_rules"]))
        self.assertTrue(set(non_consumed) <= set(pkt["inputs"]["input_files"]),
                        "missing inputs: %s" % sorted(set(non_consumed) - set(pkt["inputs"]["input_files"])))
        self.assertNotIn("seven", pkt["title"].lower())
        self.assertIn("sarf/rules/", pkt["inputs"]["prohibited_files"])

    def test_a1_packet_inventory_is_derived_not_hardcoded(self):
        contract = R.load_contract(_ROOT)
        referenced = {b["followup_packet"] for b in contract["banks"] if b["followup_packet"]}
        referenced |= {r.get("followup_packet") for r in contract["store_a_rules"] if r.get("followup_packet")}
        on_disk = {os.path.basename(p)[:-len(".json")]
                   for p in glob.glob(os.path.join(_ROOT, "qamus", "task-packets", "TP-SARF-A1-*.json"))}
        self.assertEqual(on_disk, referenced)

    # ---------------- round 5: rejected paths are never touched ----------------

    def _tripwire(self, *forbidden):
        """Intercept every filesystem primitive and RECORD any attempt against a forbidden absolute target.

        The probe is hostile on purpose: it fails if `open`, `exists`, `isdir`, `listdir`, `walk` or `glob` is
        called on the rejected path, not merely if a validation message was emitted."""
        import builtins
        import glob as globmod
        hits = []
        targets = tuple(os.path.normcase(os.path.abspath(f)) for f in forbidden)

        def watched(name, fn, argno=0):
            def wrapper(*a, **kw):
                if len(a) > argno:
                    try:
                        probe = os.path.normcase(os.path.abspath(str(a[argno])))
                    except Exception:  # noqa: BLE001  a non-path argument is not our business
                        probe = ""
                    if any(probe == tgt or probe.startswith(tgt + os.sep) for tgt in targets):
                        hits.append("%s(%s)" % (name, a[argno]))
                return fn(*a, **kw)
            return wrapper

        saved = {"open": builtins.open, "exists": os.path.exists, "isdir": os.path.isdir,
                 "listdir": os.listdir, "walk": os.walk, "glob": globmod.glob}
        builtins.open = watched("open", saved["open"])
        os.path.exists = watched("exists", saved["exists"])
        os.path.isdir = watched("isdir", saved["isdir"])
        os.listdir = watched("listdir", saved["listdir"])
        os.walk = watched("walk", saved["walk"])
        globmod.glob = watched("glob", saved["glob"])

        def restore():
            builtins.open = saved["open"]
            os.path.exists = saved["exists"]
            os.path.isdir = saved["isdir"]
            os.listdir = saved["listdir"]
            os.walk = saved["walk"]
            globmod.glob = saved["glob"]
        self.addCleanup(restore)
        return hits

    def _outside(self, *parts):
        """An absolute path just outside the worktree — exactly what a `..` hop would reach."""
        return os.path.join(os.path.dirname(os.path.abspath(_ROOT)), *parts)

    def test_escaping_registry_file_is_never_opened(self):
        """The reproduced round-5 counterexample: an escaping registry path reached open() after validation."""
        poison = self._outside("outside", "reg.jsonl")
        hits = self._tripwire(poison, self._outside("outside"))
        contract = copy.deepcopy(R.load_contract(_ROOT))
        contract["candidate_increments_not_promoted"]["registry_files"]["sarf@2.1"] = "../outside/reg.jsonl"

        # 1. the whole run must abort before any contract-directed loading
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertTrue(rep.get("aborted_before_io"))
        self.assertEqual(rep["banks"], [], "no bank may be loaded from an invalid contract")
        self.assertEqual(rep["candidate_boundary"], "not_checked")
        self.assertTrue(any("registry_files[sarf@2.1]" in f for f in rep["failures"]), rep["failures"][:3])

        # 2. and the loader refuses independently, even when called directly
        fails = R.check_candidate_registry_state(contract, _ROOT)
        self.assertTrue(any("refused before any filesystem access" in f for f in fails), fails[:3])

        # 3. the hostile assertion: the rejected target was never touched
        self.assertEqual(hits, [], "filesystem access attempted on a rejected path: %s" % hits)

    def test_escaping_bank_path_is_never_opened(self):
        poison = self._outside("outside", "bank.jsonl")
        hits = self._tripwire(poison, self._outside("outside"))
        contract = copy.deepcopy(R.load_contract(_ROOT))
        contract["banks"][0]["path"] = "../outside/bank.jsonl"
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertTrue(rep.get("aborted_before_io"))
        self.assertEqual(rep["banks"], [])
        with self.assertRaises(R.PathContainmentError):
            R.load_bank(_ROOT, {"path": "../outside/bank.jsonl", "form": "jsonl", "row_key": None})
        self.assertEqual(hits, [], "filesystem access attempted on a rejected bank path: %s" % hits)

    def test_escaping_store_a_path_is_never_opened(self):
        poison = self._outside("outside", "rules.json")
        hits = self._tripwire(poison, self._outside("outside"))
        contract = copy.deepcopy(R.load_contract(_ROOT))
        contract["store_a_rules"][0]["path"] = "../outside/rules.json"
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertTrue(rep.get("aborted_before_io"))
        fails, _ = R.check_store_a(contract, _ROOT)
        self.assertTrue(any("refused before any filesystem access" in f for f in fails), fails[:3])
        self.assertEqual(hits, [], "filesystem access attempted on a rejected Store A path: %s" % hits)

    def test_escaping_record_root_is_never_walked(self):
        poison = self._outside("outside")
        hits = self._tripwire(poison)
        contract = copy.deepcopy(R.load_contract(_ROOT))
        contract["candidate_boundary_surfaces"]["record_roots"][0] = "../outside"
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertTrue(rep.get("aborted_before_io"))
        records = R.load_boundary_records(contract, _ROOT)
        self.assertLess(len(records), len(R.load_boundary_records(R.load_contract(_ROOT), _ROOT)))
        self.assertEqual(hits, [], "the boundary scan walked a rejected root: %s" % hits)

    def test_escaping_projector_registry_is_never_opened(self):
        poison = self._outside("outside", "registry.json")
        hits = self._tripwire(poison, self._outside("outside"))
        contract = copy.deepcopy(R.load_contract(_ROOT))
        contract["candidate_increments_not_promoted"]["projector_registry"] = "../outside/registry.json"
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        fails = R.check_candidate_registry_state(contract, _ROOT)
        self.assertTrue(any("refused before any filesystem access" in f for f in fails), fails[:3])
        self.assertEqual(hits, [], "filesystem access attempted on a rejected projector registry: %s" % hits)

    def test_absolute_url_and_backslash_paths_are_refused_without_io(self):
        for rel in ("/etc/passwd", "C:/Windows/system.ini", "https://example.invalid/reg.jsonl",
                    "qamus\\skills\\reg.jsonl"):
            with self.assertRaises(R.PathContainmentError):
                R.guarded_abs(_ROOT, rel, R._ALLOWED_REGISTRY_ROOTS, "probe")
        # a legitimate path still resolves
        self.assertTrue(R.guarded_abs(_ROOT, "qamus/skills/rule-registry-increment-21.jsonl",
                                      R._ALLOWED_REGISTRY_ROOTS, "probe").endswith("rule-registry-increment-21.jsonl"))

    def test_validation_failure_aborts_before_any_loading(self):
        """Any invalid contract — not only a path one — must stop before bank loading and the boundary scan."""
        contract = copy.deepcopy(R.load_contract(_ROOT))
        contract["banks"][0]["UNKNOWN_KEY"] = 1
        rep = R.run_all(_ROOT, contract=contract)
        self.assertEqual(rep["exit_code"], 1)
        self.assertTrue(rep.get("aborted_before_io"))
        self.assertEqual(rep["banks"], [])
        self.assertEqual(rep["total_rows"], 0)
        self.assertEqual(rep["candidate_boundary"], "not_checked")
        self.assertNotIn("store_a", rep)
        # the honest baseline still runs everything
        good = R.run_all(_ROOT)
        self.assertFalse(good.get("aborted_before_io"))
        self.assertEqual(good["candidate_boundary"], "verified")

    def test_candidate_registry_and_projector_state(self):
        self.assertEqual(R.check_candidate_registry_state(R.load_contract(_ROOT), _ROOT), [])

    def test_candidate_registry_promotion_is_caught(self):
        """Mutating a registry row out of candidate status must fail the gate."""
        import tempfile
        import shutil
        contract = copy.deepcopy(R.load_contract(_ROOT))
        with tempfile.TemporaryDirectory() as d:
            for rel in ("qamus/skills", "qamus/lattice", "sarf"):
                os.makedirs(os.path.join(d, rel.replace("/", os.sep)), exist_ok=True)
            for name, rel in contract["candidate_increments_not_promoted"]["registry_files"].items():
                shutil.copy(os.path.join(_ROOT, rel.replace("/", os.sep)),
                            os.path.join(d, rel.replace("/", os.sep)))
            shutil.copy(os.path.join(_ROOT, "qamus", "lattice", "registered-projectors.json"),
                        os.path.join(d, "qamus", "lattice", "registered-projectors.json"))
            victim = os.path.join(d, contract["candidate_increments_not_promoted"]["registry_files"]["sarf@2.1"]
                                  .replace("/", os.sep))
            lines = open(victim, encoding="utf-8").read().splitlines()
            row = json.loads(lines[0])
            row["status"] = "accepted"
            lines[0] = json.dumps(row, ensure_ascii=False)
            open(victim, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            failures = R.check_candidate_registry_state(contract, d)
            self.assertTrue(any("not candidate" in f for f in failures), failures[:3])

    def test_runner_writes_nothing(self):
        """Read-only: the runner reports, it never authors a bank row or mutates an artifact."""
        before = {}
        evals = os.path.join(_ROOT, "sarf", "evals")
        for fn in sorted(os.listdir(evals)):
            before[fn] = os.path.getsize(os.path.join(evals, fn))
        R.run_all(_ROOT)
        after = {fn: os.path.getsize(os.path.join(evals, fn)) for fn in sorted(os.listdir(evals))}
        self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# letter-ownership carve — the exact-letter-ownership family (curriculum/l1l6/increments/inc-ownership,
# cu-nisba-attribution-suffix, and the p007 clitic/host carve for quran:2:34:5 / quran:12:31:24)
# ---------------------------------------------------------------------------
_LOB = "sarf/evals/letter-ownership-carve-eval.jsonl"


class LetterOwnershipCarve(unittest.TestCase):
    """Red-first gates for the new letter-ownership bank: every row is DECIDED by
    tools/run_sarf_evals.py:decide_letter_ownership, never echoed from its own `expected_*` fields."""

    def test_bank_is_registered_implemented_and_consumed(self):
        contract = R.load_contract(_ROOT)
        spec = R.bank_spec(contract, _LOB)
        self.assertEqual(spec["disposition"], "implemented_and_consumed")
        self.assertEqual(spec["behavioral_consumer"], "tools/run_sarf_evals.py:decide_letter_ownership")
        self.assertIn(spec["behavioral_consumer"], R.DECISION_CONSUMERS)
        self.assertIn(_LOB, R.REQUIRED_BEHAVIORAL_BANKS)
        rows = _rows(_LOB)
        self.assertEqual(len(rows), 17)
        failures, metrics = _run(_LOB, rows)
        self.assertEqual(failures, [], "letter-ownership bank failed: %s" % failures[:5])
        self.assertEqual(metrics["decided_rows"], len(rows))
        self.assertEqual(metrics["consumer_calls"][spec["behavioral_consumer"]], len(rows))

    def test_single_row_expected_owner_mutation_names_bank_row_and_property(self):
        """RED-FIRST: mutating exactly one row's expected owners must fail naming that row and property."""
        rows = copy.deepcopy(_rows(_LOB))
        target = next(r for r in rows if r["id"] == "own-adv-01")
        target["expected_owners"] = ["pattern_augment", "root", "root"]
        failures, _m = _run(_LOB, rows)
        self.assertTrue(failures)
        self.assertTrue(all(f.startswith("own-adv-01 ") for f in failures), failures[:3])
        self.assertTrue(any("[owners_match]" in f for f in failures), failures[:3])

    def test_breaking_the_declared_consumer_turns_the_bank_red(self):
        """MUTATION: replace decide_letter_ownership with an always-root stub; the bank must go red."""
        ctx = _ctx()
        ctx.letter_ownership_decide = lambda token: {"decision": "candidate_pending",
                                                     "owners": ["root"] * len(token.get("letters") or [])}
        failures, _m = _run(_LOB, ctx=ctx)
        self.assertTrue(failures, "a stubbed decide_letter_ownership must fail the bank")

    def test_doubly_owned_and_unownable_tokens_abstain_the_whole_token(self):
        rows = _rows(_LOB)
        by_id = {r["id"]: r for r in rows}
        ctx = _ctx()
        for rid, reason in (("own-abs-01", "no_root_evidence"), ("own-abs-02", "pending_letter_ownership"),
                            ("own-fsr-01", "false_stem_risk"), ("own-double-01", "pending_letter_ownership"),
                            ("own-carve-no-borrow", "no_root_evidence")):
            rec = ctx.letter_ownership_decide(by_id[rid])
            self.assertEqual(rec["decision"], "abstain", "%s must abstain" % rid)
            self.assertEqual(rec["reason"], reason, "%s: wrong abstention reason" % rid)
            self.assertFalse(rec.get("owners"), "%s: an abstaining row must never carry an owners list" % rid)

    def test_shape_only_mim_is_never_forced_to_pattern_augment(self):
        """own-adv-01 class: an initial mim that IS radical_1 must be root, never a shape-only augment guess."""
        rows = _rows(_LOB)
        row = next(r for r in rows if r["id"] == "own-adv-01")
        ctx = _ctx()
        rec = ctx.letter_ownership_decide(row)
        self.assertEqual(rec["decision"], "candidate_pending")
        self.assertEqual(rec["owners"][0], "root")

        mutated = copy.deepcopy(row)
        mutated["expected_owners"] = ["pattern_augment", "root", "root"]
        failures, _m = _run(_LOB, [mutated])
        self.assertTrue(any("[owners_match]" in f for f in failures), failures[:3])

    def test_nisba_final_geminated_ya_is_affix_never_root(self):
        rows = _rows(_LOB)
        by_id = {r["id"]: r for r in rows}
        ctx = _ctx()
        pos = ctx.letter_ownership_decide(by_id["own-nisba-01"])
        self.assertEqual(pos["owners"][-2:], ["affix", "affix"])
        neg = ctx.letter_ownership_decide(by_id["own-nisba-02"])
        self.assertEqual(neg["owners"][-1], "root",
                        "a bare surface ending in ya without a declared suffix_kind must not default to affix")

    def test_same_surface_needs_its_own_host_verification(self):
        """Identical surface carves identically only within one occurrence's OWN evidence."""
        rows = _rows(_LOB)
        by_id = {r["id"]: r for r in rows}
        surfaces = {by_id[i]["surface"] for i in ("own-carve-24-35-44", "own-carve-2-187-63", "own-carve-no-borrow")}
        self.assertEqual(len(surfaces), 1, "the three rows must share one identical surface")
        ctx = _ctx()
        a = ctx.letter_ownership_decide(by_id["own-carve-24-35-44"])
        b = ctx.letter_ownership_decide(by_id["own-carve-2-187-63"])
        c = ctx.letter_ownership_decide(by_id["own-carve-no-borrow"])
        self.assertEqual(a["decision"], "candidate_pending")
        self.assertEqual(b["decision"], "candidate_pending")
        self.assertEqual(a["owners"], b["owners"])
        self.assertEqual(c["decision"], "abstain",
                         "withheld evidence on an identical surface must never borrow a sibling row's carve")

    def test_occurrence_dogfood_matches_p007_repository_evidence(self):
        """quran:2:34:5 and quran:12:31:24 are grounded in qamus/examples/p007-li-pilot/*.jsonl (read-only locator)."""
        with open(os.path.join(_ROOT, "qamus", "examples", "p007-li-pilot", "typed-facts.jsonl"),
                  encoding="utf-8") as fh:
            facts = [json.loads(l) for l in fh if l.strip()]
        seg_2_34_5 = next(f for f in facts if f["fact_id"] == "fact:p00slice:2_34_5:seg")
        seg_12_31_24 = next(f for f in facts if f["fact_id"] == "fact:p00slice:12_31_24:seg")
        rows = _rows(_LOB)
        by_id = {r["id"]: r for r in rows}
        row_2_34_5 = by_id["own-carve-2-34-5"]
        row_12_31_24 = by_id["own-carve-12-31-24"]
        self.assertEqual(row_2_34_5["occurrence_id"], "quran:2:34:5")
        self.assertEqual(row_12_31_24["occurrence_id"], "quran:12:31:24")
        self.assertEqual("".join(row_2_34_5["letters"][:1]), seg_2_34_5["fact_value"]["clitic"][:1])
        self.assertEqual("".join(row_12_31_24["letters"][:1]), seg_12_31_24["fact_value"]["clitic"][:1])
        ctx = _ctx()
        self.assertEqual(ctx.letter_ownership_decide(row_2_34_5)["owners"], row_2_34_5["expected_owners"])
        self.assertEqual(ctx.letter_ownership_decide(row_12_31_24)["owners"], row_12_31_24["expected_owners"])

    def test_analyses_stay_candidate_and_never_certify(self):
        rows = _rows(_LOB)
        ctx = _ctx()
        for row in rows:
            rec = ctx.letter_ownership_decide(row)
            self.assertIn(rec["decision"], ("candidate_pending", "abstain"))
            self.assertNotIn("certified", json.dumps(rec, ensure_ascii=False).lower())
            self.assertTrue(set(rec) <= {"decision", "owners", "reason", "hidden_radicals"},
                            "%s: ownership record must never carry a lexeme/sense/meaning key: %r"
                            % (row["id"], sorted(rec)))
        spec = R.bank_spec(R.load_contract(_ROOT), _LOB)
        self.assertIsNone(spec["followup_packet"])


if __name__ == "__main__":
    unittest.main()
