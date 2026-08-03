#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_sarf_evals — the executable runner for the Ṣarf eval banks (Burst A1).

Before this runner every sarf bank was dark: `tools/fusha_eval_coverage.py` measured 20 nahw+sarf banks with a
single runner (a nahw one), and the three object-form `.json` evals were not even row-counted
(`docs/subsystems/sarf-executable-map.md` GAP-S1). This module closes that gap WITHOUT the failure mode the gap
invites — a script that reads a fixture and prints PASS. Every bank here is either

  * run through a REAL consumer (the same modules the checker/parser/differ actually use), or
  * honestly labelled as not behaviourally covered.

The controlling contract is `sarf/eval-runner-contract.json` (schema
`qamus/schemas/sarf-eval-runner-contract.schema.json`). It gives every sarf eval artifact AND every Store A rule
file (`sarf/rules/*.json`) exactly one disposition:

  implemented_and_consumed — a PRODUCTION DECISION CONSUMER (see DECISION_CONSUMERS) is invoked for every row and
                             its output decides the row; wrong consumer behaviour turns the bank RED. Normalization
                             helpers and row-internal consistency do NOT qualify: `normalize_ar` is a key ladder,
                             not a decision, so a bank whose only "consumer" is a normalizer stays a gap.
  fixture_only             — structure/vocabulary is gated; no consumer decides anything.
  documentary              — a decision record; only its shape and its procedure links are executable.
  candidate_no_consumer    — the artifact encodes an intended executable contract that no consumer implements
                             (or that the existing consumer only partly implements); the gap is MEASURED, and a
                             follow-on packet names the exact consumer to build.

Coverage arithmetic is deliberately narrow: `behavioral_rows` counts ONLY rows a decision consumer actually
decided (`decided_rows`, returned by the adapter — never `len(rows)` by assumption). Fixture, documentary and
candidate rows stay visible as gaps. A bank being READ by this runner is not coverage; `--strict` is a
DISPOSITION-COMPLETENESS gate, not a behavioural-coverage gate, and says so in its output.

Design notes that keep the runner honest:
  * Consumers are injected (`Consumers.real()`), so `tools/test_run_sarf_evals.py` can mutate the real functions
    and prove each adapter goes red. An adapter that could not detect a broken consumer would not be allowed to
    claim `implemented_and_consumed`.
  * Adapters record measured metrics. Structural invariants (row counts, quarantine counts, decided rows) are
    PINNED, so drift in either direction is red. A metric that records a KNOWN-WRONG state — agreement with a
    contract the consumer does not implement — is FLOORED instead: only regression below the floor is red, so a
    later repair that improves the consumer passes.
  * Nothing is promoted: `sarf@2.1`–`sarf@2.4` remain CANDIDATE, and the runner asserts SKILL.md still says so.
  * `norm()` never certifies anything: the over-collapsed analysis key is built from `norm_strict` and must never
    carry the harakah/shadda that decides the case.
  * READ-ONLY: this module writes no file unless `--report PATH` is given explicitly. No network, no live paths.

CLI (from the repo root):
  python tools/run_sarf_evals.py --self-test      # synthetic red/green + consumer-mutation proofs
  python tools/run_sarf_evals.py --all            # every bank in the contract  (terminal: SARF EVAL RUNNER PASS)
  python tools/run_sarf_evals.py --bank sarf/evals/false-clitic-split-eval.jsonl
  python tools/run_sarf_evals.py --all --json     # machine-readable report on stdout
"""
import argparse
import copy
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import leak_sot  # noqa: E402
from tools import rm40_gate_stack as gate_stack  # noqa: E402  (real RM-40 weak-letter classification, read-only)

SCHEMA_ID = "qamus.sarf_eval_runner_contract.v1"
CONTRACT_REL = "sarf/eval-runner-contract.json"
SCHEMA_REL = "qamus/schemas/sarf-eval-runner-contract.schema.json"
TERMINAL_PASS = "SARF EVAL RUNNER PASS"
TERMINAL_SELFTEST = "SARF EVAL RUNNER SELF-TEST PASS"

DISPOSITIONS = ("candidate_no_consumer", "documentary", "fixture_only", "implemented_and_consumed")
CONTRACT_REQUIRED = ["banks", "candidate_boundary_surfaces", "candidate_increments_not_promoted",
                     "disposition_definitions", "generated_by", "schema", "store_a_rules"]

# The production functions that DECIDE something. A bank may claim implemented_and_consumed only if its contract
# row names one of these as `behavioral_consumer` and the adapter invokes it once per row. normalize_ar is
# excluded on purpose: it computes match keys, it does not decide a gloss, a segmentation or a class.
DECISION_CONSUMERS = (
    "tools/fusha_text_check.py:segment_candidates",
    "tools/fusha_text_check.py:check_text",
    "tools/fusha_morphology_lattice.py:build_morphology_lattice",
    "tools/corpus_to_qamus_candidates.py:classify",
    "tools/curriculum_unit_consumer.py:analyze_ownership_carve",
    "tools/curriculum_unit_consumer.py:analyze_derivative",
    "tools/curriculum_unit_consumer.py:analyze_discriminator_table",
    "tools/rm40_gate_stack.py:slot_gate",
    "tools/rm40_gate_stack.py:plural_gate",
    "tools/fusha_paradigm_generate.py:generate_verb",
)
# Contract-declared callable -> the Consumers slot that holds it. run_adapter() wraps these slots in counting
# proxies, so the observed per-row call count is measured INDEPENDENTLY of whatever an adapter chooses to report.
CONSUMER_SLOTS = {
    "tools/fusha_text_check.py:segment_candidates": "segment_candidates",
    "tools/fusha_text_check.py:check_text": "check_text",
    "tools/fusha_morphology_lattice.py:build_morphology_lattice": "build_lattice",
    "tools/corpus_to_qamus_candidates.py:classify": "classify",
    "tools/curriculum_unit_consumer.py:analyze_ownership_carve": "letter_ownership_decide",
    "tools/curriculum_unit_consumer.py:analyze_derivative": "derivative_decide",
    "tools/curriculum_unit_consumer.py:analyze_discriminator_table": "discriminator_decide",
    "tools/rm40_gate_stack.py:slot_gate": "slot_gate",
    "tools/rm40_gate_stack.py:plural_gate": "plural_gate",
    "tools/fusha_paradigm_generate.py:generate_verb": "generate_verb",
}
# The banks whose behavioural coverage is specifically justified. A future change may not quietly relabel all
# banks fixture_only to make the gate green: tools/test_run_sarf_evals.py asserts these stay behavioural.
REQUIRED_BEHAVIORAL_BANKS = (
    "sarf/evals/combining-mark-byte-exact-eval.jsonl",
    "sarf/evals/derivational-template-carve-eval.jsonl",
    "sarf/evals/false-clitic-split-eval.jsonl",
    "sarf/evals/largelexicon-collision-safety.jsonl",
    "sarf/evals/letter-ownership-carve-eval.jsonl",
    "sarf/evals/morphology-candidate-lattice.jsonl",
    "sarf/evals/nominal-class-discrimination-eval.jsonl",
    "sarf/evals/weak-root-and-voice-eval.jsonl",
)
# How a Store A rule file is (or is not) used by production code.
#   data_driven   — rule CONTENT is loaded and changes/rejects a production decision; proven by a bounded mutation
#   id_citation   — only stable ids are read, to build a citation string; the operative condition is hard-coded
#   existence_gate— the harness only asserts the file exists/parses
#   none          — nothing executable reads it
CONSUMPTION_KINDS = ("data_driven", "existence_gate", "id_citation", "none")

# The decision-gate ladder (SSOT: nahw/evals/grammar-decision-gates.json, enforced by
# tools/validate_linguistic_decisions.py). Ranked so "at least two_vote_required" is expressible.
GATE_RANK = {"auto_safe": 0, "two_vote_required": 1, "human_source_review_required": 2, "never_auto_resolve": 3}

# Closed vocabularies the banks are allowed to draw on (mirrors of the procedure documents, not new authority).
EVIDENCE_CLASSES = ("component_only", "homograph_split", "source_addressed_confirmable", "unvoweled_competing",
                    "voweled_confirmable", "weak_root_gated")
EVIDENCE_SIGNALS = ("context_nahw", "content_letter_harakah", "existing_entry", "hamza_seat", "norm_strict",
                    "qac", "referent", "shadda", "voice_pattern", "wazn")
# The external corpus certifier is a FACT source we may consult internally, but its NAME never reaches a rendered
# report (provenance/source-boundaries.md §2, tools/leak_sot.py). Metrics are keyed through this relabelling.
_SIGNAL_LABEL = {"qac": "external_certifier"}
HIDDEN_POS = ("adjective", "masdar", "noun", "participle", "particle", "pronoun", "proper_noun", "verb")
# tools/corpus_to_qamus_candidates.classify()'s closed output vocabulary, and the subset that mints nothing.
CLASSIFIER_CLASSES = ("already_in_qamus", "new_lemma_existing_root", "new_root", "new_surface_existing_lemma",
                      "occurrence_augment", "particle_or_construction", "review_needed")
CLASSIFIER_NO_MINT = ("already_in_qamus", "particle_or_construction")
# differ class -> the eval bank's authoring class it corresponds to (used only to MEASURE agreement).
CLASSIFIER_TO_EVAL_CLASS = {
    "already_in_qamus": "already_in_qamus",
    "occurrence_augment": "occurrence_augment",
    "new_surface_existing_lemma": "new_surface",
    "new_lemma_existing_root": "new_lemma",
    "new_root": "new_root",
    "particle_or_construction": "particle",
}

_ALLOWED_BANK_ROOTS = ("sarf/evals/",)
_ALLOWED_RULE_ROOTS = ("sarf/rules/",)
# Every OTHER path-bearing contract field: candidate record roots, the projector surface and the rule registries.
# Read-only scanning still has to stay inside the worktree, so the roots are closed per field.
_ALLOWED_BOUNDARY_ROOTS = ("qamus/certification", "qamus/lattice", "qamus/skills", "qamus/reports",
                           "qamus/examples")
_ALLOWED_REGISTRY_ROOTS = ("qamus/skills/",)
_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

_SEG = "tools/fusha_text_check.py:segment_candidates"
_CHK = "tools/fusha_text_check.py:check_text"
_LAT = "tools/fusha_morphology_lattice.py:build_morphology_lattice"
_NORM = "structural:tools/normalize_ar.py"
_OWN = "tools/curriculum_unit_consumer.py:analyze_ownership_carve"
_DER = "tools/curriculum_unit_consumer.py:analyze_derivative"
_DISC = "tools/curriculum_unit_consumer.py:analyze_discriminator_table"
_SLOT_GATE = "tools/rm40_gate_stack.py:slot_gate"
_PLURAL_GATE = "tools/rm40_gate_stack.py:plural_gate"
_GEN_VERB = "tools/fusha_paradigm_generate.py:generate_verb"

WEAK_ROOT_GATES_PATH = "sarf/rules/weak-root-gates.json"

_LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
_HARAKAT = range(0x064B, 0x0653)
# hamza-seat neutralisation applied ON TOP of norm_strict to reach the banks' declared over-collapsed key.
# norm_strict KEEPS the seat (that is its job); the banks' keys are the coarser "what a key-only resolver sees".
_SEAT_NEUTRAL = (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ؤ", "و"), ("ئ", "ي"))


# ---------------------------------------------------------------------------
# consumer bundle (injected so a test can mutate the REAL functions and prove the adapters bite)
# ---------------------------------------------------------------------------
def consumers_module(name):
    """Import one of the real consumer modules by bare name (kept lazy: importing the checker is not free)."""
    return __import__("tools." + name, fromlist=["*"])


class Consumers(object):
    """The real production functions each adapter consumes. Attributes are rebindable on purpose."""

    __slots__ = ("segment_candidates", "build_lattice", "check_text", "clusters", "classify", "load_index",
                 "norm", "norm_strict", "bare", "shadda_on", "haraka_on", "ends_tanwin_alef",
                 "letter_ownership_decide", "derivative_decide", "discriminator_decide", "slot_gate",
                 "plural_gate", "generate_verb")

    @classmethod
    def real(cls):
        tc = consumers_module("fusha_text_check")
        ml = consumers_module("fusha_morphology_lattice")
        na = consumers_module("normalize_ar")
        cq = consumers_module("corpus_to_qamus_candidates")
        cu = consumers_module("curriculum_unit_consumer")
        gs = consumers_module("rm40_gate_stack")
        pg = consumers_module("fusha_paradigm_generate")
        self = cls()
        self.segment_candidates = tc.segment_candidates
        self.check_text = tc.check_text
        self.clusters = tc._clusters
        self.build_lattice = ml.build_morphology_lattice
        self.classify = cq.classify
        self.load_index = cq.load_index
        self.norm = na.norm
        self.norm_strict = na.norm_strict
        self.bare = na.bare
        self.shadda_on = na.shadda_on
        self.haraka_on = na.haraka_on
        self.ends_tanwin_alef = na.ends_tanwin_alef
        # the DECLARED behavioural consumer for the letter-ownership-carve bank is the EXTERNAL
        # curriculum_unit_consumer module's own function, bound directly (never a local wrapper),
        # so a mutation of that module's attribute (tools/test_run_sarf_evals.py) is what the
        # adapter actually calls -- proving genuine cross-module invocation, not an echo.
        self.letter_ownership_decide = cu.analyze_ownership_carve
        # the DECLARED behavioural consumer for the derivational-template-carve bank is the EXTERNAL
        # curriculum_unit_consumer module's own template-classification function, bound directly (never a local
        # wrapper) -- the same genuine-cross-module-invocation contract as letter_ownership_decide above.
        self.derivative_decide = cu.analyze_derivative
        # the DECLARED behavioural consumer for the nominal-class-discrimination bank is the EXTERNAL
        # curriculum_unit_consumer module's own discriminator-table function, bound directly (never a local
        # wrapper).
        self.discriminator_decide = cu.analyze_discriminator_table
        # the DECLARED behavioural consumer for the weak-root-and-voice bank is the REAL RM-40 gate stack
        # (tools/rm40_gate_stack.py:slot_gate, already used in production by tools/fusha_paradigm_generate.py) plus
        # the REAL paradigm generator (tools/fusha_paradigm_generate.py:generate_verb) for voice/melody comparison;
        # both bound directly, never a local wrapper.
        self.slot_gate = gs.slot_gate
        # the derivational-template-carve bank's SECONDARY, cross-check-only consumer for its broken-plural rows
        # (tools/rm40_gate_stack.py:plural_gate, already used in production by fusha_paradigm_generate.py).
        self.plural_gate = gs.plural_gate
        self.generate_verb = pg.generate_verb
        return self


# ---------------------------------------------------------------------------
# shared key helpers  (norm() never certifies: every key below is norm_strict-derived)
# ---------------------------------------------------------------------------
def _has_marks(s):
    return any(ord(ch) in _HARAKAT for ch in (s or ""))


def collapse_key(ctx, s):
    """The over-collapsed analysis key a key-only resolver sees: norm_strict + hamza-seat neutralisation."""
    k = ctx.norm_strict(s or "")
    for a, b in _SEAT_NEUTRAL:
        k = k.replace(a, b)
    return k


def _fold(k):
    """Match-key folds the repo's normalizers already apply (ى→ي، ة→ه); display text is never folded."""
    return (k or "").replace("ى", "ي").replace("ة", "ه")


def analysis_key(ctx, s):
    """collapse_key minus the case-marking tanwīn-alif (ـًا is an ending, not a stem letter — and NOT the نا pronoun)."""
    k = collapse_key(ctx, s)
    if ctx.ends_tanwin_alef(s) and k:
        k = k[:-1]
    return k


def key_relation(ctx, surface, declared):
    """How the surface reaches the bank's declared key, from a CLOSED set of named relations (or None = no relation).

    exact                      — the analysis key is the declared key
    tanwin_case_fold           — after dropping the case-marking tanwīn-alif
    ta_marbuta_suffix_illusion — after also dropping the final ه that came from a tāʾ marbūṭa (the documented
                                 "tāʾ marbūṭa as suffix" illusion the authoring differ must not fall for)
    """
    d = _fold(declared or "")
    if _fold(collapse_key(ctx, surface)) == d:
        return "exact"
    k = _fold(analysis_key(ctx, surface))
    if k == d:
        return "tanwin_case_fold"
    if k.endswith("ه") and k[:-1] == d:
        return "ta_marbuta_suffix_illusion"
    return None


def _looks_tanwin_alef(s):
    """Structural twin of normalize_ar.ends_tanwin_alef, computed straight off the bytes.

    It exists so the runner can CROSS-CHECK the real detector: if `ends_tanwin_alef` is ever disabled, the two
    disagree and the bank goes red. Without this a broken guard would simply skip its own check.
    """
    import unicodedata
    s = unicodedata.normalize("NFC", s or "")
    if not s.endswith("ا"):
        return False
    i = len(s) - 2
    while i >= 0 and (0x06D6 <= ord(s[i]) <= 0x06ED or ord(s[i]) == 0x0640):
        i -= 1
    return i >= 0 and 0x064B <= ord(s[i]) <= 0x064D


def _whole_token_reading(cands, surface):
    return any(len(c.get("segments") or []) == 1
               and c["segments"][0].get("role") == "stem"
               and c["segments"][0].get("surface") == surface
               for c in cands)


def _concat_exact(cands, surface):
    return all("".join(s.get("surface", "") for s in (c.get("segments") or [])) == surface for c in cands)


def _procedure_link_failures(row, root, rid):
    """Every `procedure_links` entry must point at a file that exists (a dangling procedure is not a procedure)."""
    out = []
    for link in row.get("procedure_links") or []:
        target = link.split("#", 1)[0]
        if not os.path.exists(os.path.join(root, target.replace("/", os.sep))):
            out.append("%s: procedure link %r does not resolve to a repo file" % (rid, target))
    return out


def _required_field_failures(row, spec, rid):
    out = []
    for f in spec.get("required_fields") or []:
        v = row.get(f)
        if v is None or v == "" or v == [] or v == {}:
            out.append("%s: missing/empty required field %r" % (rid, f))
    for f in spec.get("nonempty_list_fields") or []:
        v = row.get(f)
        if not (isinstance(v, list) and v):
            out.append("%s: field %r must be a non-empty list" % (rid, f))
    for f in spec.get("loc_fields") or []:
        if f in row and not _LOC_RE.match(str(row.get(f) or "")):
            out.append("%s: field %r is not a surah:ayah:word address" % (rid, f))
    return out


def _rid(row, spec, i):
    return str(row.get(spec.get("id_field") or "id") or "row%d" % i)


class _Props(object):
    """Records, per property, the exact ROW IDS it was evaluated on and the DECLARED CALLABLE that produced the
    value being asserted.

    Coverage is claimed per property, so a count alone is not enough: relabelling a property's `decided_by` in the
    contract must break it. Every hit therefore carries the callable the assertion actually consumed, and the
    runner requires the declared callable's own hit count to equal the applicable rows."""

    def __init__(self):
        self.rows = {}
        self.calls = {}

    def hit(self, rid, decided_by, *keys):
        for k in keys:
            self.rows.setdefault(k, set()).add(rid)
            by = self.calls.setdefault(k, {})
            if decided_by:
                by[decided_by] = by.get(decided_by, 0) + 1

    def as_metric(self):
        return dict((k, {"rows": len(v), "row_ids": sorted(v), "by_callable": dict(self.calls.get(k, {}))})
                    for k, v in self.rows.items())


def _f(rid, prop, msg):
    """One structured failure: row id + the exact enforced property + why.

    A mutation must be diagnosable, so every failure names the row and the property it broke; run_all() prefixes
    the bank path, giving `<bank>: <row id> [<property>] <message>`."""
    return "%s [%s] %s" % (rid, prop, msg)


# ---------------------------------------------------------------------------
# adapters — each one invokes a REAL consumer and returns (failures[], metrics{})
# ---------------------------------------------------------------------------
def adapter_lattice_ambiguity(rows, spec, ctx, root):
    """sarf/evals/morphology-candidate-lattice.jsonl -> fusha_text_check.segment_candidates + the morphology lattice.

    Enforces the procedure's controlling invariants (sarf/procedures/morphology-candidate-lattice.md): consume the
    segmentation, keep competing readings, never fabricate root/lemma/pattern, score AND rank (never a boolean
    `correct`), never auto_safe for arbitrary text.
    """
    fails, agree, min_seen, decided = [], 0, None, 0
    props, mismatch_rows = _Props(), []
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        surface = row.get("surface") or ""
        fails.extend(_required_field_failures(row, spec, rid))
        if not surface:
            fails.append(_f(rid, "surface_present", "empty surface"))
            continue
        cands = ctx.segment_candidates(surface)
        props.hit(rid, _SEG, "whole_token_reading_preserved", "segments_concat_byte_exact")
        if not _whole_token_reading(cands, surface):
            fails.append(_f(rid, "whole_token_reading_preserved",
                            "the un-peeled whole-token reading was dropped (ambiguity collapsed)"))
        if not _concat_exact(cands, surface):
            fails.append(_f(rid, "segments_concat_byte_exact",
                            "a segmentation does not concatenate byte-exactly to the surface"))
        lat = ctx.build_lattice("tok:0", surface, cands, bool(row.get("voweled")), source_addressed=False)
        decided += 1
        props.hit(rid, _LAT, "expected_min_candidates", "keep_ambiguity", "all_unvoweled_kept", "ranks_1_to_n",
                  "forbid_fabricated_root", "never_auto_safe", "evidence_class_closed_set",
                  "score_present", "no_boolean_correct")
        # the evidence-class comparison is a DIAGNOSTIC, not a decision: no callable is credited for it.
        props.hit(rid, None, "evidence_class_agreement")
        cl = lat.get("candidates") or []
        n = len(cl)
        min_seen = n if min_seen is None else min(min_seen, n)
        want = int(row.get("expected_min_candidates") or 1)
        if n < want:
            fails.append(_f(rid, "expected_min_candidates",
                            "lattice produced %d candidates, bank requires >= %d" % (n, want)))
        if row.get("keep_ambiguity") and n < max(2, want):
            fails.append(_f(rid, "keep_ambiguity", "row collapsed to %d candidate(s)" % n))
        if lat.get("all_unvoweled_kept") is not True:
            fails.append(_f(rid, "all_unvoweled_kept", "lattice dropped the all_unvoweled_kept guarantee"))
        if n and sorted(c.get("rank") for c in cl) != list(range(1, n + 1)):
            fails.append(_f(rid, "ranks_1_to_n", "candidate ranks are not 1..n"))
        for c in cl:
            if "correct" in c or "is_correct" in c:
                fails.append(_f(rid, "no_boolean_correct", "a candidate carries a boolean correct flag"))
            if not isinstance(c.get("score"), (int, float)):
                fails.append(_f(rid, "score_present", "candidate is missing a numeric score"))
            if row.get("forbid_fabricated_root") and any(c.get(k) is not None for k in ("root", "lemma", "pattern")):
                fails.append(_f(rid, "forbid_fabricated_root",
                                "fabricated root/lemma/pattern (blank beats a fabricated value)"))
            if c.get("evidence_class") not in EVIDENCE_CLASSES:
                fails.append(_f(rid, "evidence_class_closed_set",
                                "candidate evidence_class %r outside the closed set" % c.get("evidence_class")))
            if row.get("decision") == "pending" and c.get("gate") == "auto_safe":
                fails.append(_f(rid, "never_auto_safe", "pending row produced an auto_safe candidate"))
        if row.get("evidence_class") not in EVIDENCE_CLASSES:
            fails.append(_f(rid, "evidence_class_closed_set",
                            "bank evidence_class %r outside the closed set" % row.get("evidence_class")))
        if row.get("evidence_class") in {c.get("evidence_class") for c in cl}:
            agree += 1
        else:
            # UNCOVERED property: the engine's class and the bank's class disagree on this exact row. It is
            # reported per row, never counted as coverage, and never turned into a released rule.
            mismatch_rows.append(rid)
    return fails, {"rows": len(rows), "decided_rows": decided, "min_lattice_candidates": min_seen or 0,
                   "evidence_class_agreement": agree, "evidence_class_mismatch_rows": sorted(mismatch_rows),
                   "property_hits": props.as_metric()}


def adapter_clitic_split_guard(rows, spec, ctx, root):
    """sarf/evals/false-clitic-split-eval.jsonl -> the real segmenter, lattice and suggestion quarantine.

    The bank's job is that a look-alike clitic never becomes an asserted split. The consumer's job is to KEEP the
    whole-token reading, never auto_safe an arbitrary token, never peel a tanwīn-alif as the pronoun نا, and never
    promote a rejected split to an editable `split` suggestion.
    """
    fails, reject_rows, tanwin_rows, splits_blocked, decided = [], 0, 0, 0, 0
    props = _Props()
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        surface = row.get("surface") or ""
        fails.extend(_required_field_failures(row, spec, rid))
        if not surface:
            fails.append("%s: empty surface" % rid)
            continue
        cands = ctx.segment_candidates(surface)
        props.hit(rid, _SEG, "whole_token_reading_preserved", "segments_concat_byte_exact")
        if not _whole_token_reading(cands, surface):
            fails.append(_f(rid, "whole_token_reading_preserved",
                            "whole-token reading dropped; a look-alike clitic was asserted"))
        if not _concat_exact(cands, surface):
            fails.append(_f(rid, "segments_concat_byte_exact",
                            "a segmentation is not byte-exact against the surface"))
        lat = ctx.build_lattice("tok:0", surface, cands, _has_marks(surface), source_addressed=False)
        decided += 1
        props.hit(rid, _LAT, "never_auto_safe", "no_fabricated_root")
        for c in lat.get("candidates") or []:
            if c.get("gate") == "auto_safe":
                fails.append(_f(rid, "never_auto_safe", "arbitrary-text candidate marked auto_safe"))
            if c.get("root") is not None:
                fails.append(_f(rid, "no_fabricated_root", "lattice fabricated a root for an arbitrary token"))
        structural = _looks_tanwin_alef(surface)
        props.hit(rid, _NORM, "tanwin_alef_guard")
        if structural:
            props.hit(rid, _SEG, "tanwin_alef_not_pronoun")
        if bool(ctx.ends_tanwin_alef(surface)) != structural:
            fails.append(_f(rid, "tanwin_alef_guard",
                            "the tanwin-alif detector disagrees with the surface bytes (guard disabled?)"))
        if structural:
            tanwin_rows += 1
            if any(s.get("role") == "object_pronoun" for c in cands for s in (c.get("segments") or [])):
                fails.append(_f(rid, "tanwin_alef_not_pronoun",
                                "tanwin-alif peeled as an attached pronoun"))
        if str(row.get("decision") or "").startswith("reject_"):
            reject_rows += 1
            rec = ctx.check_text({"input_mode": "arbitrary_typing", "raw_input": surface})
            props.hit(rid, _CHK, "rejected_split_quarantined")
            if any((s.get("edit") or {}).get("op") == "split" for s in rec.get("suggestions") or []):
                fails.append(_f(rid, "rejected_split_quarantined",
                                "a rejected split escaped as an editable split suggestion"))
            else:
                splits_blocked += 1
            if "auto_safe" in (rec.get("gates") or []):
                fails.append(_f(rid, "never_auto_safe", "arbitrary-text diagnostic marked auto_safe"))
    return fails, {"rows": len(rows), "decided_rows": decided, "reject_rows": reject_rows,
                   "tanwin_alef_rows": tanwin_rows, "rejected_splits_quarantined": splits_blocked,
                   "property_hits": props.as_metric()}


def adapter_collision_quarantine(rows, spec, ctx, root):
    """sarf/evals/largelexicon-collision-safety.jsonl -> fusha_text_check.check_text (suggestion quarantine).

    A lexicon collision must stay a preserved candidate, never a public split. The forbidden reading may exist in
    the lattice (ambiguity is preserved) but must never reach an editable suggestion or an auto_safe gate.
    """
    fails, decided = [], 0
    props = _Props()
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        surface = row.get("surface") or ""
        fails.extend(_required_field_failures(row, spec, rid))
        if not surface:
            fails.append("%s: empty surface" % rid)
            continue
        rec = ctx.check_text({"input_mode": "arbitrary_typing", "raw_input": surface})
        decided += 1
        props.hit(rid, _CHK, "no_split_suggestion", "never_auto_safe", "raw_input_preserved",
                  "live_writes_zero", "ambiguity_preserved")
        if any((s.get("edit") or {}).get("op") == "split" for s in rec.get("suggestions") or []):
            fails.append(_f(rid, "no_split_suggestion", "split suggestion escaped the collision quarantine"))
        if "auto_safe" in (rec.get("gates") or []):
            fails.append(_f(rid, "never_auto_safe", "collision surface produced an auto_safe gate"))
        if rec.get("raw_input") != surface:
            fails.append(_f(rid, "raw_input_preserved", "the checker altered the input surface"))
        if (rec.get("checker_summary") or {}).get("live_writes") != 0:
            fails.append(_f(rid, "live_writes_zero", "checker reported a live write"))
        # AMBIGUITY IS PROVEN, NOT ASSUMED: the declared consumer must return the token for THIS exact surface
        # and that token must carry at least two DISTINCT viable segmentations. An empty token list is a failure,
        # not a vacuous pass (round-4 defect: a selective echo stub with no analysis_tokens passed).
        matching = [t for t in (rec.get("analysis_tokens") or []) if t.get("surface") == surface]
        if not matching:
            fails.append(_f(rid, "ambiguity_preserved",
                            "the declared consumer returned no analysis token for this exact surface"))
        for tok in matching:
            viable = {tuple((seg.get("role"), seg.get("surface")) for seg in (c.get("segments") or []))
                      for c in (tok.get("segment_candidates") or [])
                      if c.get("legal", True) and (c.get("segments") or [])}
            if len(viable) < 2:
                fails.append(_f(rid, "ambiguity_preserved",
                                "only %d distinct viable segmentation(s) survived; the competing reading was "
                                "collapsed (ambiguity must be preserved)" % len(viable)))
    return fails, {"rows": len(rows), "decided_rows": decided, "property_hits": props.as_metric()}


def adapter_byte_exact_marks(rows, spec, ctx, root):
    """sarf/evals/combining-mark-byte-exact-eval.jsonl -> normalize_ar + the cluster-aware segmenter.

    The bank's decision is "normalize for match, keep bytes for display". Executable form: annotation marks
    (U+06D6..06ED) are transparent to every match key, the display surface is never rewritten, and the segmenter
    slices on base-letter clusters so a voweled peel can never cut a combining mark off its base letter.
    """
    fails, decided = [], 0
    props = _Props()
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        surface = row.get("surface") or ""
        fails.extend(_required_field_failures(row, spec, rid))
        fails.extend(_procedure_link_failures(row, root, rid))
        if not surface:
            fails.append("%s: empty surface" % rid)
            continue
        props.hit(rid, _NORM, "marks_transparent_to_matching", "cluster_alignment")
        props.hit(rid, _SEG, "segments_concat_byte_exact")
        for key_name, key in (("bare", ctx.bare(surface)), ("norm_strict", ctx.norm_strict(surface))):
            if any(0x06D6 <= ord(ch) <= 0x06ED for ch in key):
                fails.append(_f(rid, "marks_transparent_to_matching",
                                "%s() left an annotation mark in the match key" % key_name))
            if _has_marks(key):
                fails.append(_f(rid, "marks_transparent_to_matching",
                                "%s() left a harakah in the match key" % key_name))
        cands = ctx.segment_candidates(surface)
        if not _concat_exact(cands, surface):
            fails.append(_f(rid, "segments_concat_byte_exact",
                            "a segmentation is not byte-exact (display bytes were normalized)"))
        if len(ctx.clusters(surface)) != len(ctx.bare(surface)):
            fails.append(_f(rid, "cluster_alignment",
                            "cluster count != bare base-letter count (a mark was split off its base letter)"))
        rec = ctx.check_text({"input_mode": "arbitrary_typing", "raw_input": surface})
        decided += 1
        props.hit(rid, _CHK, "raw_input_preserved", "checker_segments_byte_exact", "live_writes_zero")
        if rec.get("raw_input") != surface:
            fails.append(_f(rid, "raw_input_preserved", "raw_input was not preserved byte-exactly"))
        # The bank's decision is BOUND to the declared consumer: the checker itself must return byte-exact
        # analysis tokens for the surface. A stub that merely echoes raw_input fails here.
        tokens = [t for t in (rec.get("analysis_tokens") or []) if t.get("is_arabic") is not False]
        if not tokens:
            fails.append(_f(rid, "checker_segments_byte_exact",
                            "the declared consumer returned no analysis token for an Arabic surface"))
        for tok in tokens:
            if tok.get("surface") != surface:
                fails.append(_f(rid, "checker_segments_byte_exact",
                                "the checker altered the token surface (display bytes must survive)"))
            cands = tok.get("segment_candidates") or []
            if not cands:
                fails.append(_f(rid, "checker_segments_byte_exact",
                                "the checker returned no segmentation to verify byte-exactness against"))
            if not _concat_exact(cands, surface):
                fails.append(_f(rid, "checker_segments_byte_exact",
                                "a checker segmentation does not concatenate byte-exactly to the surface"))
        if (rec.get("checker_summary") or {}).get("live_writes") != 0:
            fails.append(_f(rid, "live_writes_zero", "checker reported a live write"))
    return fails, {"rows": len(rows), "decided_rows": decided, "property_hits": props.as_metric()}


def adapter_hidden_state_evidence(rows, spec, ctx, root):
    """sarf/evals/sarf-state-machine-eval.json -> normalize_ar's key ladder + the decision-gate ladder.

    Executable reading of the bank's own thesis: the observation is an emission, the declared `norm_key` is the
    over-collapsed key, and the hidden state may only be certified by evidence the key DROPS. So: the key must
    genuinely carry no harakah/shadda, the surface must carry the signal the key drops, an `auto_safe` case may
    never rest on the key alone (it must cite an external certifier), and every distractor must really differ from
    the correct hidden state.
    """
    fails, relations, signals = [], {}, {}
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        obs = row.get("observation") or {}
        surface, declared = obs.get("surface_ar") or "", obs.get("norm_key") or ""
        fails.extend(_required_field_failures(row, spec, rid))
        if not surface or not declared:
            fails.append("%s: case is missing an observation surface/key" % rid)
            continue
        rel = key_relation(ctx, surface, declared)
        if rel is None:
            fails.append("%s: the declared norm_key is not reachable from the surface through the repo's key ladder"
                         % rid)
        else:
            relations[rel] = relations.get(rel, 0) + 1
        if _has_marks(declared):
            fails.append("%s: the declared over-collapsed key still carries a harakah/shadda (not a key)" % rid)
        if not _has_marks(surface):
            fails.append("%s: the observed surface carries no mark, so nothing is dropped by the key" % rid)
        gate = row.get("expected_gate")
        if gate not in GATE_RANK:
            fails.append("%s: expected_gate %r outside the decision-gate ladder" % (rid, gate))
        ev = row.get("evidence_required") or []
        if not ev:
            fails.append("%s: no evidence_required declared" % rid)
        for e in ev:
            if e not in EVIDENCE_SIGNALS:
                fails.append("%s: evidence signal outside the closed set" % rid)
            label = _SIGNAL_LABEL.get(e, e)
            signals[label] = signals.get(label, 0) + 1
        if gate == "auto_safe" and "qac" not in ev:
            fails.append("%s: auto_safe granted without an external certifier — the key alone never certifies" % rid)
        if "hamza_seat" in ev and not any(ch in surface for ch in "أإؤئءآ"):
            fails.append("%s: case cites hamza_seat evidence but the surface carries no hamza seat" % rid)
        correct = row.get("correct_hidden_state") or {}
        if correct.get("pos") not in HIDDEN_POS:
            fails.append("%s: correct_hidden_state.pos %r outside the closed set" % (rid, correct.get("pos")))
        for d in row.get("distractor_states") or []:
            st = d.get("state") or {}
            if st and all(st.get(k) == correct.get(k) for k in st):
                fails.append("%s: a distractor state is identical to the correct hidden state" % rid)
            if not d.get("why_loses"):
                fails.append("%s: a distractor carries no why_loses reason" % rid)
    # decided_rows stays 0: nothing here DECIDES a hidden state. The adapter proves the bank is internally
    # coherent and that the repo key ladder really drops the deciding signal; a resolver would be the consumer.
    return fails, {"rows": len(rows), "decided_rows": 0, "key_relations": relations,
                   "evidence_signals": signals}


def adapter_key_collapse_pending(rows, spec, ctx, root):
    """sarf/evals/qamus-regression-eval.json -> normalize_ar (collapse + shadda/harakah readers) + the gate ladder.

    The bank's pending_contract made executable: a plain (key-only) assertion must genuinely collide — at least two
    of its surfaces must land on ONE analysis key — and may never be auto_safe; a `pending` verdict must be
    `never_auto_resolve`. A cited `@vowelled` / `@form-aware` assertion is only reachable when the named diacritic is
    actually readable on the surface AND is dropped by the key, and it must collide with a pending sibling (so the
    citation is what buys the gloss, not the key).
    """
    fails, collisions, cited, relations = [], 0, 0, {}
    pending_keys = set()
    for i, row in enumerate(rows):
        if "@" not in str(row.get("key") or ""):
            pending_keys.add(_fold(str(row.get("key") or "")))
            for s in row.get("surfaces") or []:
                pending_keys.add(_fold(analysis_key(ctx, s)))
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        key = str(row.get("key") or "")
        surfaces = row.get("surfaces") or []
        gate = row.get("expected_gate")
        verdict = row.get("correct_gloss_or_pending")
        if gate not in GATE_RANK:
            fails.append("%s: expected_gate %r outside the decision-gate ladder" % (rid, gate))
            continue
        keys = [_fold(analysis_key(ctx, s)) for s in surfaces]
        for k in keys:
            if _has_marks(k):
                fails.append("%s: the analysis key still carries the distinguishing harakah" % rid)
        if "@" not in key:
            # A key-only assertion is only honest if the declared key really pulls in more than one surface, through
            # one of the named key relations (exact / tanwīn case fold / tāʾ-marbūṭa suffix illusion).
            reached = 0
            for s in surfaces:
                rel = key_relation(ctx, s, key)
                if rel is not None:
                    reached += 1
                    relations[rel] = relations.get(rel, 0) + 1
            if reached < 2:
                fails.append("%s: the declared key reaches %d surface(s) — that is not a key collision" % (rid, reached))
            else:
                collisions += 1
            if GATE_RANK[gate] < GATE_RANK["two_vote_required"]:
                fails.append("%s: a colliding key may never be auto_safe" % rid)
            if verdict == "pending" and gate != "never_auto_resolve":
                fails.append("%s: pending is only honest at never_auto_resolve (got %s)" % (rid, gate))
        else:
            cited += 1
            if len(surfaces) != 1:
                fails.append("%s: a cited (diacritic-bearing) assertion must pin exactly one surface" % rid)
                continue
            surface = surfaces[0]
            if verdict == "pending":
                fails.append("%s: a cited assertion may not resolve to pending" % rid)
            if gate == "auto_safe" or gate == "never_auto_resolve":
                fails.append("%s: a cited derived-form gloss belongs at two_vote/human review (got %s)" % (rid, gate))
            base_letters = sorted(set(ctx.bare(surface)))
            if key.endswith("@form-aware"):
                if not any(ctx.shadda_on(surface, ch) for ch in base_letters):
                    fails.append("%s: form-aware citation without a readable shadda on any base letter" % rid)
            else:
                if not any(ctx.haraka_on(surface, ch) for ch in base_letters):
                    fails.append("%s: vowelled citation without a readable harakah on any base letter" % rid)
            k = _fold(analysis_key(ctx, surface))
            if _has_marks(k):
                fails.append("%s: the cited surface's key retains the diacritic (nothing is bought by citing it)" % rid)
            if k not in pending_keys:
                fails.append("%s: the cited surface does not collide with any key-only assertion" % rid)
    # decided_rows stays 0: no production consumer emits the correct gloss or the pending state for these rows.
    return fails, {"rows": len(rows), "decided_rows": 0, "colliding_key_assertions": collisions,
                   "cited_assertions": cited, "key_relations": relations}


_PROCLITIC_KEYS = ("وبال", "فبال", "بال", "كال", "فال", "وال", "لل", "ال", "و", "ف", "ب", "ك", "ل", "س")


def _new_surface_licence(ctx, token):
    """Why a `new surface of an existing lemma` verdict is morphologically legitimate, or None if it is laundering.

    A surface may differ from its lemma either by a CLITIC (a peeled proclitic/enclitic) or by INFLECTION (a case
    or mood ending on the final radical). The first version of this guard demanded a proclitic and therefore
    rejected a correct verdict on an unprefixed case-inflected token such as a bare genitive noun — i.e. it made an
    IMPROVEMENT in the differ fail. Both licences are now recognised, and anything else still fails closed."""
    nk = ctx.norm_strict(token or "")
    if any(nk.startswith(p) and len(nk) - len(p) >= 2 for p in _PROCLITIC_KEYS):
        return "proclitic_peel"
    clusters = ctx.clusters(token or "")
    if clusters:
        tail = clusters[-1]
        # a case/mood marker (short vowel, tanwin or sukun) riding the FINAL base letter is an inflectional ending,
        # not part of the stem, so the stem may legitimately already exist as a lemma.
        if any(0x064B <= ord(ch) <= 0x0652 for ch in tail[1:]):
            return "inflectional_ending"
    bare = ctx.bare(token or "")
    for enc in ("كما", "هما", "كم", "هم", "نا", "ها", "هن", "كن", "ني"):
        if bare.endswith(enc) and len(bare) - len(enc) >= 2:
            return "enclitic_peel"
    return None


def adapter_corpus_classifier(rows, spec, ctx, root):
    """sarf/evals/corpus-authoring-eval.json -> corpus_to_qamus_candidates.classify (the real authoring differ).

    The bank declares a 6-class authoring contract. The live differ implements a coarser 7-class heuristic, so the
    honest gate is: run the REAL classifier on every case, enforce the mechanical invariants it must satisfy
    (single class from the closed vocabulary, deterministic, no mint on an existing entry, no content root minted
    for a closed-set particle, no surface laundering), and FLOOR the measured agreement with the declared contract
    so a repair that improves it passes while a regression is red. The residual gap is the bank's disposition, not
    a hidden pass: this adapter decides nothing and promotes nothing.
    """
    fails, agreement, disagreements, probed, licences = [], 0, {}, 0, {}
    try:
        surf, roots = ctx.load_index()
    except Exception as e:  # noqa: BLE001  a missing index is a real, reportable failure
        return ["corpus index unreadable: %s" % type(e).__name__], {"rows": len(rows)}
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        token = (row.get("token") or {}).get("surface_ar") or ""
        if not token:
            fails.append("%s: case has no token surface" % rid)
            continue
        if key_relation(ctx, token, row.get("norm_key") or "") is None:
            fails.append("%s: the declared norm_key is not reachable from the surface through the key ladder" % rid)
        if row.get("expected_gate") not in GATE_RANK:
            fails.append("%s: expected_gate %r outside the decision-gate ladder" % (rid, row.get("expected_gate")))
        expected = row.get("expected_class")
        cl, meta = ctx.classify(token, surf, roots)
        probed += 1
        if cl not in CLASSIFIER_CLASSES:
            fails.append("%s: classifier emitted %r outside its closed vocabulary" % (rid, cl))
            continue
        if ctx.classify(token, surf, roots)[0] != cl:
            fails.append("%s: classifier is not deterministic for one token" % rid)
        if cl in CLASSIFIER_NO_MINT and meta and meta.get("root") and expected == "particle":
            fails.append("%s: a closed-set particle was given a content root" % rid)
        if expected == "particle" and cl == "new_root":
            fails.append("%s: a closed-set particle was routed to a new content root (particle spine violated)" % rid)
        if CLASSIFIER_TO_EVAL_CLASS.get(cl) == "new_surface":
            licence = _new_surface_licence(ctx, token)
            if licence is None:
                fails.append(_f(rid, "new_surface_morphologically_licensed",
                                "a new_surface match explained by neither a peeled proclitic nor an inflectional "
                                "ending is surface laundering"))
            else:
                licences[licence] = licences.get(licence, 0) + 1
        if CLASSIFIER_TO_EVAL_CLASS.get(cl) == expected:
            agreement += 1
        else:
            pair = "%s->%s" % (expected, cl)
            disagreements[pair] = disagreements.get(pair, 0) + 1
    # decided_rows stays 0: the differ is INVOKED on every case (probed_rows) but it does not implement the
    # bank's declared 6-class contract, so no row is decided by it. Agreement is diagnostic, never coverage.
    return fails, {"rows": len(rows), "decided_rows": 0, "probed_rows": probed,
                   "contract_agreement": agreement, "disagreements": disagreements,
                   "new_surface_licences": licences}


# ---------------------------------------------------------------------------
# letter ownership carve — curriculum/l1l6/increments/inc-ownership (u-s01/u-s09 own-r1..r5),
# cu-nisba-attribution-suffix's affix layer, and the p007 clitic/host carve.
#
# The DECISION itself lives in tools/curriculum_unit_consumer.py:analyze_ownership_carve (the
# EXTERNAL, DECLARED behavioural consumer for this bank — see DECISION_CONSUMERS/CONSUMER_SLOTS
# above and Consumers.real()). This module only ADAPTS the bank rows to it; the closed
# owner-class and abstention vocabularies below mirror that module's own closed sets (the same
# pattern EVIDENCE_CLASSES/CLASSIFIER_CLASSES already use for the other adapters in this file) so
# the adapter can validate a row's `expected_owners`/`expected_reason` without importing another
# module's private constants.
# ---------------------------------------------------------------------------
_OWNERSHIP_CLASSES = ("root", "pattern_augment", "clitic", "inflection", "affix", "host")
_OWNERSHIP_ABSTAIN_REASONS = ("pending_letter_ownership", "false_stem_risk", "no_root_evidence",
                              "radical_accounting_incomplete")
_OWNERSHIP_RECORD_KEYS = frozenset(("decision", "owners", "reason", "hidden_radicals", "mark_owners"))
# The ALLOWLISTED projection of a bank row into genuine analysis inputs: every field
# analyze_ownership_carve actually reads to DECIDE a token (curriculum_unit_consumer.py's own
# _own_validate/analyze_ownership_carve). Every other row field -- expected_decision,
# expected_owners, expected_reason, teaches, id, occurrence_id, loc, class, evidence_note -- is
# answer-key, identity or prose metadata that must NEVER reach the consumer: an external consumer
# that is handed the whole row could echo the answer key back and pass with zero analysis (I-1).
_OWN_CONSUMER_INPUT_FIELDS = ("mode", "letters", "surface", "token_kind", "suffix_kind",
                              "root_evidence", "clitic_layers")


def _own_consumer_input(row):
    """Project one bank row down to `_OWN_CONSUMER_INPUT_FIELDS` before it reaches the external
    consumer. This is the ONLY thing analyze_ownership_carve is ever called with for this bank."""
    return {k: row[k] for k in _OWN_CONSUMER_INPUT_FIELDS if k in row}


def adapter_letter_ownership_carve(rows, spec, ctx, root):
    """sarf/evals/letter-ownership-carve-eval.jsonl ->
    tools/curriculum_unit_consumer.py:analyze_ownership_carve (the exact-letter-ownership family's
    production decision function: curriculum/l1l6/increments/inc-ownership own-r1..r5,
    cu-nisba-attribution-suffix's affix layer, and the p007 clitic/host carve for
    quran:2:34:5 / quran:12:31:24 / quran:24:35:44 / quran:2:187:63).

    Every row is DECIDED from its `letters` + evidence; the row is projected through
    `_own_consumer_input` (mode/letters/surface/token_kind/suffix_kind/root_evidence/clitic_layers ONLY) before it
    ever reaches the consumer, so nothing here -- and no consumer, honest or hostile -- can echo a row's own
    `expected_decision`/`expected_owners`/`expected_reason`/`teaches`/`id`/`occurrence_id`/`loc`/`class`/
    `evidence_note` into the verdict (I-1). A same-surface group is re-decided per row (never copied from a
    sibling row's result). Two rows carrying EQUIVALENT evidence for the same surface must reach the SAME decision
    (sarf/SKILL.md's same-surface fork prohibition runs this direction, never the inverse); a row whose own
    evidence is withheld must abstain rather than borrow a sibling's verdict.
    """
    fails, decided = [], 0
    props = _Props()
    decisions_by_id, rows_by_id, surface_groups = {}, {}, {}
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        letters = row.get("letters") or []
        if not letters:
            fails.append("%s: empty letters" % rid)
            continue
        rec = ctx.letter_ownership_decide(_own_consumer_input(row))
        decided += 1
        props.hit(rid, _OWN, "decision_behaviorally_computed", "no_semantic_identity_leak", "never_certified")
        decisions_by_id[rid] = rec.get("decision")
        rows_by_id[rid] = row
        surface_groups.setdefault(row.get("surface") or "", []).append(rid)

        if rec.get("decision") not in ("candidate_pending", "abstain"):
            fails.append(_f(rid, "decision_behaviorally_computed",
                            "analyze_ownership_carve returned %r" % rec.get("decision")))
        extra_keys = set(rec) - _OWNERSHIP_RECORD_KEYS
        if extra_keys:
            fails.append(_f(rid, "no_semantic_identity_leak",
                            "ownership record carries key(s) %s outside {decision, owners, reason, "
                            "hidden_radicals, mark_owners} — root-sharing/shape/citation-form must never imply a "
                            "lexeme, sense, function, meaning, translation or occurrence identity"
                            % sorted(extra_keys)))
        if "certified" in json.dumps(rec, ensure_ascii=False).lower():
            fails.append(_f(rid, "never_certified", "the decision record claims a certified state"))

        expected_decision = row.get("expected_decision")
        if rec.get("decision") != expected_decision:
            fails.append(_f(rid, "decision_behaviorally_computed",
                            "decided %r, bank expects %r" % (rec.get("decision"), expected_decision)))

        if expected_decision == "abstain":
            props.hit(rid, _OWN, "abstains_never_claim_root")
            want_reason = row.get("expected_reason")
            if want_reason not in _OWNERSHIP_ABSTAIN_REASONS:
                fails.append(_f(rid, "reason_matches",
                                "bank's expected_reason %r outside the closed abstention vocabulary"
                                % want_reason))
            if rec.get("reason") != want_reason:
                fails.append(_f(rid, "reason_matches",
                                "decided reason %r, bank expects %r" % (rec.get("reason"), want_reason)))
            if rec.get("owners"):
                fails.append(_f(rid, "abstains_never_claim_root",
                                "an abstaining row must never carry an owners list"))
        else:
            props.hit(rid, _OWN, "owner_classes_closed_set")
            want_owners = row.get("expected_owners") or []
            got_owners = rec.get("owners") or []
            if got_owners != want_owners:
                fails.append(_f(rid, "owners_match",
                                "decided owners %r, bank expects %r" % (got_owners, want_owners)))
            for o in got_owners:
                if o not in _OWNERSHIP_CLASSES:
                    fails.append(_f(rid, "owner_classes_closed_set",
                                    "owner class %r outside the closed set" % o))
            if row.get("id") == "own-adv-01":
                props.hit(rid, _OWN, "shape_only_augment_rejected")
                if got_owners[:1] != ["root"]:
                    fails.append(_f(rid, "shape_only_augment_rejected",
                                    "an initial mim that IS radical_1 must never default to pattern_augment"))
            if row.get("suffix_kind") == "nisba" or row.get("id") == "own-nisba-02":
                props.hit(rid, _OWN, "nisba_affix_never_root")

        if row.get("id") == "own-double-01":
            props.hit(rid, _OWN, "double_claim_forces_abstention")
            if rec.get("decision") != "abstain" or rec.get("reason") != "pending_letter_ownership":
                fails.append(_f(rid, "double_claim_forces_abstention",
                                "a genuinely doubly-owned letter must force whole-token abstention with "
                                "pending_letter_ownership"))

    def _has_own_evidence(rid):
        r = rows_by_id[rid]
        return bool(r.get("clitic_layers")) or bool((r.get("root_evidence") or {}).get("radicals"))

    for surface, ids in surface_groups.items():
        if len(ids) < 2:
            continue
        props.hit(ids[0], None, "same_surface_independent_verification")
        for extra in ids[1:]:
            props.hit(extra, None, "same_surface_independent_verification")
        # sarf/SKILL.md's same-surface fork prohibition runs this direction, never the inverse: two rows sharing a
        # surface and carrying EQUIVALENT evidence must reach the SAME decision (independent evaluation is not
        # licence to disagree), while a row whose OWN evidence was withheld must abstain rather than borrow a
        # sibling's identical-surface verdict. There is no requirement that a surface group disagree.
        equipped = [j for j in ids if _has_own_evidence(j)]
        withheld = [j for j in ids if not _has_own_evidence(j)]
        equipped_decs = {decisions_by_id[j] for j in equipped}
        if len(equipped_decs) > 1:
            fails.append("same_surface_independent_verification: surface %r: rows %s supply equivalent evidence "
                        "but reached different decisions %s — independently verified rows must agree when "
                        "their own evidence agrees" % (surface, equipped, sorted(equipped_decs)))
        for j in withheld:
            if decisions_by_id[j] != "abstain":
                fails.append("same_surface_independent_verification: surface %r: row %s withheld its own carve "
                            "evidence yet decided %r — a later occurrence must never inherit an identical "
                            "surface's prior verdict" % (surface, j, decisions_by_id[j]))

    abstain_rows = sum(1 for d in decisions_by_id.values() if d == "abstain")
    candidate_pending_rows = sum(1 for d in decisions_by_id.values() if d == "candidate_pending")
    return fails, {"rows": len(rows), "decided_rows": decided, "abstain_rows": abstain_rows,
                   "candidate_pending_rows": candidate_pending_rows, "property_hits": props.as_metric()}


# --------------------------------------------------------- derivational-template-carve
_DTC_CONSUMER_INPUT_FIELDS = ("mode", "letters", "surface", "token_kind", "root_evidence",
                              "penult_vowel", "penult_vowel_evidence")


def _dtc_consumer_input(row):
    """Project one derivational-template-carve bank row down to `_DTC_CONSUMER_INPUT_FIELDS` before it ever
    reaches the external consumer -- the I-1 echo defence: `expected_decision`/`expected_class`/
    `expected_template`/`expected_reason`/`id`/`teaches`/`increment`/`evidence_note`/`plural_gate_probe_root` can
    never reach `analyze_derivative`."""
    return {k: row[k] for k in _DTC_CONSUMER_INPUT_FIELDS if k in row}


def _dtc_pack(increment, root=_REPO):
    """MODULE-LEVEL indirection (mirrors `_weak_root_gate_data`): the adapter below always calls this name, never
    a pack captured at import time, so a bounded mutation prover can swap this exact function in memory and prove
    the decision genuinely depends on the loaded pack's CONTENT."""
    import tools.curriculum_unit_consumer as cu
    return cu.load(increment)[0]


_DTC_DECISIONS = ("candidate_pending", "abstain")
# The closed abstention vocabulary this bank may cite -- drawn from the four packs' own declared
# `abstention_reasons` (inc-derivatives/unit-v4.json, and the three unit-v2.json siblings G1 repaired) plus the
# two new consumer-level reasons G1 added (`radical_arity_unsupported`, `shared_row_class_undecided`).
_DTC_ABSTAIN_REASONS = (
    "no_root_evidence", "surface_letter_mismatch", "no_template", "ambiguous_template",
    "penult_vowel_unknown", "penult_vowel_evidence_unbound", "penult_mark_not_in_surface",
    "penult_mark_mismatch", "initial_mim_mark_not_in_surface", "initial_mim_vowel_unlicensed",
    "weak_declaration_unbound", "weak_declaration_contradicts_root",
    "weak_realization_unlicensed", "radical_arity_unsupported", "shared_row_class_undecided",
)
# Every key `analyze_derivative` can ever emit, across every branch: root-sharing/shape/citation-form must never
# imply a lexeme, sense, meaning, occurrence or translation, so an emitted key outside this closed set fails the
# bank (mirrors `_OWNERSHIP_RECORD_KEYS`).
_DTC_RECORD_KEYS = frozenset((
    "decision", "authority", "class", "template", "reason", "declared", "radicals", "declared_arity",
    "supplied_radicals", "unbound_slot", "unlicensed_slot", "weak_radical", "note", "shared_with",
))
# a citation PLACEHOLDER for `plural_gate`'s emit-path `_cite(PLURAL_GATE, template_id)` call only: the
# cross-check this adapter performs depends solely on `rm40_gate_stack.has_weak_or_hamza(root)`, never on which
# valid plural-gender-rules.json id is cited, so one fixed, genuinely-valid id is used for every sound-radical
# broken-plural row rather than inventing a per-template mapping this pack's own template ids do not carry.
_DTC_PLURAL_GATE_CITE_ID = "taksir-afal"


def adapter_derivational_template_carve(rows, spec, ctx, root):
    """sarf/evals/derivational-template-carve-eval.jsonl -> tools/curriculum_unit_consumer.py:analyze_derivative
    (the SAME production template-classification function G1 repaired: inc-derivatives/unit-v4.json for u-s03/
    u-s04/u-s05, and the three G1-repaired sibling packs inc-quality-adjective-templates/inc-intensive-agent-
    templates/inc-broken-plural-template-inventory unit-v2.json).

    Every row is decided by EXACTLY ONE call to `analyze_derivative`, against the pack its own `increment` field
    names, loaded through the module-level `_dtc_pack` indirection (never a pack captured at import time) so a
    bounded mutation can prove the decision depends on pack CONTENT. The row is projected through
    `_dtc_consumer_input` (mode/letters/surface/token_kind/root_evidence/penult_vowel/penult_vowel_evidence ONLY)
    before it ever reaches the consumer, so no row -- honest or hostile -- can echo its own `expected_*`/`id`/
    `teaches`/`increment` fields into the verdict (I-1). No row may declare a `shared_` `expected_class` (the
    label is a routing hint G1 made the consumer refuse, never a class a bank may pin), and no row may carry an
    `occurrence_id`, `loc`, `entry_id`, `lexeme`, `sense`, `gloss` or `translation` field: every row in this bank
    is entry/template-typed only (`no_occurrence_dogfood_evidence: true`).

    Every `inc-broken-plural-template-inventory` row is additionally cross-checked against the REAL
    `tools/rm40_gate_stack.py:plural_gate` (declared as a `secondary_consumers` entry): when the pack abstains a
    row for a weak-radical reason, `plural_gate` must independently abstain the same root too -- a disagreement
    between the two real consumers fails the bank.
    """
    fails, decided = [], 0
    props = _Props()
    abstain_rows = candidate_pending_rows = 0
    plural_calls = 0
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        increment = row.get("increment")
        if not increment:
            fails.append(_f(rid, "decision_behaviorally_computed", "row names no increment"))
            continue
        expected_class = row.get("expected_class")
        if isinstance(expected_class, str) and expected_class.startswith("shared_"):
            fails.append(_f(rid, "shared_row_never_resolved",
                            "a bank row must never pin a shared_ class as its own expected_class"))
            continue
        if any(row.get(k) for k in ("occurrence_id", "loc", "entry_id", "lexeme", "sense", "gloss",
                                    "translation")):
            fails.append(_f(rid, "no_semantic_identity_leak",
                            "a bank row must never carry an occurrence/entry/lexeme/sense/gloss/translation "
                            "field -- this bank is entry/template-typed only"))
            continue
        if not row.get("no_occurrence_dogfood_evidence"):
            fails.append(_f(rid, "no_semantic_identity_leak",
                            "every row must declare no_occurrence_dogfood_evidence: true"))
        proj = _dtc_consumer_input(row)
        leaked = [k for k in row if k.startswith("expected_") and k in proj]
        if leaked:
            fails.append(_f(rid, "no_semantic_identity_leak",
                            "projected consumer input carries answer-key field(s) %s" % leaked))
        pack = _dtc_pack(increment, root)
        rec = ctx.derivative_decide(proj, pack)
        decided += 1
        props.hit(rid, _DER, "decision_behaviorally_computed", "no_semantic_identity_leak", "never_certified")
        if row.get("id") in ("dtc-der-pos-04", "dtc-der-adv-02", "dtc-der-adv-03", "dtc-der-adv-04",
                             "dtc-der-abs-05", "dtc-der-abs-06"):
            # der-r9: the mafal_place/mu_participle collision resolved by the WRITTEN initial مـ
            # vowel rather than the penult vowel alone (the reproduced active_participle/
            # passive_participle false positives on مجلس/منزل/مكتب, a genuine مُدَرِّس participle
            # left undisturbed, and missing/unlicensed initial-مـ evidence abstaining).
            props.hit(rid, _DER, "initial_mim_vowel_discriminates_collision")
        got_decision = rec.get("decision")
        if got_decision not in _DTC_DECISIONS:
            fails.append(_f(rid, "decision_behaviorally_computed",
                            "analyze_derivative returned %r" % got_decision))
        extra_keys = set(rec) - _DTC_RECORD_KEYS
        if extra_keys:
            fails.append(_f(rid, "no_semantic_identity_leak",
                            "derivative record carries key(s) %s outside the closed vocabulary" % sorted(extra_keys)))
        if "certified" in json.dumps(rec, ensure_ascii=False).lower():
            fails.append(_f(rid, "never_certified", "the decision record claims a certified state"))

        expected_decision = row.get("expected_decision")
        if got_decision != expected_decision:
            fails.append(_f(rid, "decision_behaviorally_computed",
                            "decided %r, bank expects %r" % (got_decision, expected_decision)))

        if expected_decision == "abstain":
            abstain_rows += 1
            props.hit(rid, _DER, "abstains_never_claim_class")
            want_reason = row.get("expected_reason")
            if want_reason not in _DTC_ABSTAIN_REASONS:
                fails.append(_f(rid, "reason_matches",
                                "bank's expected_reason %r outside the closed abstention vocabulary"
                                % want_reason))
            if rec.get("reason") != want_reason:
                fails.append(_f(rid, "reason_matches",
                                "decided reason %r, bank expects %r" % (rec.get("reason"), want_reason)))
            if rec.get("class") is not None:
                fails.append(_f(rid, "abstains_never_claim_class",
                                "an abstaining row must never carry a class"))
            if want_reason == "weak_realization_unlicensed" or want_reason == "weak_declaration_unbound" \
                    or want_reason == "weak_declaration_contradicts_root":
                props.hit(rid, _DER, "weak_realization_gated")
            if want_reason == "radical_arity_unsupported":
                props.hit(rid, _DER, "radical_arity_gated")
            if want_reason == "shared_row_class_undecided":
                props.hit(rid, _DER, "shared_row_never_resolved")
            if row.get("class") == "declared_collision":
                props.hit(rid, _DER, "declared_collision_abstains")
            if row.get("class") == "negative_wasl":
                props.hit(rid, _DER, "wasl_never_radical")
            if row.get("class") == "negative_gemination":
                props.hit(rid, _DER, "shadda_never_skeleton_decided")
        else:
            candidate_pending_rows += 1
            want_class = row.get("expected_class")
            if rec.get("class") != want_class:
                fails.append(_f(rid, "decision_behaviorally_computed",
                                "decided class %r, bank expects %r" % (rec.get("class"), want_class)))
            want_template = row.get("expected_template")
            if rec.get("template") != want_template:
                fails.append(_f(rid, "decision_behaviorally_computed",
                                "decided template %r, bank expects %r" % (rec.get("template"), want_template)))

        if increment == "inc-broken-plural-template-inventory":
            radicals = ((row.get("root_evidence") or {}).get("radicals")) or []
            root_str = " ".join(radicals)
            plural_rec = ctx.plural_gate(root_str, _DTC_PLURAL_GATE_CITE_ID)
            plural_calls += 1
            props.hit(rid, _PLURAL_GATE, "plural_gate_agreement")
            pack_abstained_weak = (expected_decision == "abstain"
                                   and row.get("expected_reason") in ("weak_declaration_unbound",
                                                                      "weak_declaration_contradicts_root",
                                                                      "weak_realization_unlicensed"))
            if pack_abstained_weak and plural_rec.get("decision") != "abstain":
                fails.append(_f(rid, "plural_gate_agreement",
                                "the pack abstained %r for a weak radical but rm40_gate_stack.plural_gate(%r) "
                                "decided %r -- a cross-consumer disagreement" % (row.get("expected_reason"),
                                root_str, plural_rec.get("decision"))))

    return fails, {"rows": len(rows), "decided_rows": decided, "abstain_rows": abstain_rows,
                   "candidate_pending_rows": candidate_pending_rows, "property_hits": props.as_metric()}


# ---------------------------------------------------------- nominal-class-discrimination
_NCD_CONSUMER_INPUT_FIELDS = ("features",)


def _ncd_consumer_input(row):
    """Project one nominal-class-discrimination bank row down to `{features}` ONLY before it ever reaches the
    external consumer -- the I-1 echo defence: `expected_decision`/`expected_function`/`expected_reason`/
    `expected_alternatives`/`id`/`teaches`/`increment` can never reach `analyze_discriminator_table`."""
    return {k: row[k] for k in _NCD_CONSUMER_INPUT_FIELDS if k in row}


def _ncd_pack(increment, root=_REPO):
    """MODULE-LEVEL indirection (mirrors `_dtc_pack`/`_weak_root_gate_data`): the adapter below always calls this
    name, never a pack captured at import time, so a bounded mutation prover can swap this exact function in
    memory and prove the decision genuinely depends on the loaded pack's CONTENT."""
    import tools.curriculum_unit_consumer as cu
    return cu.load(increment)[0]


_NCD_DECISIONS = ("candidate_pending", "abstain")
_NCD_ABSTAIN_REASONS = ("insufficient_features", "preserve_alternatives", "school_dependent_attributed")
_NCD_NONE_GENERIC_PREFIX = "none_generic_candidate:"
_NCD_RECORD_KEYS = frozenset((
    "decision", "authority", "function", "occurrence_binding", "reason", "alternatives",
    "attributed_function", "school_attribution",
))


def adapter_nominal_class_discrimination(rows, spec, ctx, root):
    """sarf/evals/nominal-class-discrimination-eval.jsonl -> tools/curriculum_unit_consumer.py:
    analyze_discriminator_table (the SAME registered `discriminator_table` capability inc-ma and inc-mim-
    initial-noun-discriminator/inc-elative-template-discriminator already share -- declarative reuse, no
    consumer edit needed to add a new discriminator pack).

    Every row is decided by EXACTLY ONE call to `analyze_discriminator_table`, against the pack its own
    `increment` field names, loaded through the module-level `_ncd_pack` indirection so a bounded mutation can
    prove the decision depends on pack CONTENT (deleting a function from the in-memory pack must flip a
    `preserve_alternatives` row to `insufficient_features`, never silently resolve). The row is projected through
    `_ncd_consumer_input` (`features` ONLY) before it ever reaches the consumer, so no row -- honest or hostile
    -- can echo its own `expected_*` fields into the verdict (I-1). No row may supply an `envelope`: this bank
    has no occurrence-level dogfood evidence (`no_occurrence_dogfood_evidence: true` on every row), so every
    `candidate_pending` row must carry the consumer's own `none_generic_candidate: ...` occurrence_binding
    string -- proving a candidate_pending decision here is never mistaken for an occurrence resolution.
    """
    fails, decided = [], 0
    props = _Props()
    abstain_rows = candidate_pending_rows = 0
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        increment = row.get("increment")
        if not increment:
            fails.append(_f(rid, "decision_behaviorally_computed", "row names no increment"))
            continue
        if "envelope" in row:
            fails.append(_f(rid, "no_occurrence_resolution_leak",
                            "this bank has no occurrence-level dogfood evidence; no row may supply an envelope"))
            continue
        if not row.get("no_occurrence_dogfood_evidence"):
            fails.append(_f(rid, "no_occurrence_resolution_leak",
                            "every row must declare no_occurrence_dogfood_evidence: true"))
        proj = _ncd_consumer_input(row)
        leaked = [k for k in row if k.startswith("expected_") and k in proj]
        if leaked:
            fails.append(_f(rid, "no_occurrence_resolution_leak",
                            "projected consumer input carries answer-key field(s) %s" % leaked))
        pack = _ncd_pack(increment, root)
        rec = ctx.discriminator_decide(proj, pack)
        decided += 1
        props.hit(rid, _DISC, "decision_behaviorally_computed", "never_certified")
        got_decision = rec.get("decision")
        if got_decision not in _NCD_DECISIONS:
            fails.append(_f(rid, "decision_behaviorally_computed",
                            "analyze_discriminator_table returned %r" % got_decision))
        extra_keys = set(rec) - _NCD_RECORD_KEYS
        if extra_keys:
            fails.append(_f(rid, "no_occurrence_resolution_leak",
                            "discriminator record carries key(s) %s outside the closed vocabulary"
                            % sorted(extra_keys)))
        if "certified" in json.dumps(rec, ensure_ascii=False).lower():
            fails.append(_f(rid, "never_certified", "the decision record claims a certified state"))

        expected_decision = row.get("expected_decision")
        if got_decision != expected_decision:
            fails.append(_f(rid, "decision_behaviorally_computed",
                            "decided %r, bank expects %r" % (got_decision, expected_decision)))

        if expected_decision == "abstain":
            abstain_rows += 1
            props.hit(rid, _DISC, "abstains_never_claim_function")
            want_reason = row.get("expected_reason")
            if want_reason not in _NCD_ABSTAIN_REASONS:
                fails.append(_f(rid, "reason_matches",
                                "bank's expected_reason %r outside the closed abstention vocabulary"
                                % want_reason))
            if rec.get("reason") != want_reason:
                fails.append(_f(rid, "reason_matches",
                                "decided reason %r, bank expects %r" % (rec.get("reason"), want_reason)))
            if rec.get("function") is not None:
                fails.append(_f(rid, "abstains_never_claim_function",
                                "an abstaining row must never carry a function"))
            if rec.get("occurrence_binding") is not None:
                fails.append(_f(rid, "no_occurrence_resolution_leak",
                                "an abstaining row must never carry an occurrence_binding"))
            if want_reason == "preserve_alternatives":
                props.hit(rid, _DISC, "preserve_alternatives_never_votes")
                want_alts = row.get("expected_alternatives")
                if rec.get("alternatives") != want_alts:
                    fails.append(_f(rid, "preserve_alternatives_never_votes",
                                    "decided alternatives %r, bank expects %r"
                                    % (rec.get("alternatives"), want_alts)))
                if not want_alts or len(want_alts) < 2:
                    fails.append(_f(rid, "preserve_alternatives_never_votes",
                                    "a preserve_alternatives row must declare at least two alternatives"))
        else:
            candidate_pending_rows += 1
            want_function = row.get("expected_function")
            if rec.get("function") != want_function:
                fails.append(_f(rid, "decision_behaviorally_computed",
                                "decided function %r, bank expects %r" % (rec.get("function"), want_function)))
            props.hit(rid, _DISC, "candidate_pending_never_occurrence_bound")
            binding = rec.get("occurrence_binding")
            if not (isinstance(binding, str) and binding.startswith(_NCD_NONE_GENERIC_PREFIX)):
                fails.append(_f(rid, "candidate_pending_never_occurrence_bound",
                                "a candidate_pending row with no supplied envelope must carry the consumer's own "
                                "none_generic_candidate occurrence_binding string, got %r" % binding))

    return fails, {"rows": len(rows), "decided_rows": decided, "abstain_rows": abstain_rows,
                   "candidate_pending_rows": candidate_pending_rows, "property_hits": props.as_metric()}


def _weak_root_gate_data(root=_REPO):
    """Load `sarf/rules/weak-root-gates.json`.

    A MODULE-LEVEL indirection on purpose (mirrors `fusha_paradigm_generate._measures()`): the adapter below always
    calls this name, never a value captured at import time, so a bounded mutation prover can swap this exact
    function in memory and prove the adapter's own decision genuinely depends on the file's CONTENT — the
    `hollow_pattern_vowels`/`lafif_compositions` sections `tools/rm40_gate_stack.py` never reads (it only cites
    stable rule ids there). Removing this data must disable ONLY the weak-root-and-voice bank's hollow/lafif rows;
    every other bank never calls this loader."""
    path = os.path.join(root, WEAK_ROOT_GATES_PATH.replace("/", os.sep))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


_WRV_MODES = ("weak_reason_classification", "lafif_composition", "voice_determination")
_WRV_ABSTAIN_REASONS = ("hollow_defective_assimilated", "hollow_root_c2_hidden", "defective_c3_alternation",
                        "assimilated_c1_dropped", "hamza_seat", "lafif_composition_incomplete",
                        "lafif_composition_unordered", "voice_undetermined")
_WRV_WEAK_CLASSES = ("hollow", "assimilated", "defective", "lafif_mafruq", "lafif_maqrun")


def _weak_class_from_root(root_str):
    """Classify a root's weak_class from radical POSITION, using the REAL gate stack's own weak-letter set
    (`tools.rm40_gate_stack.WEAK_LETTERS`) — never a re-derived vocabulary. Returns None for a sound or
    hamza-only root (no weak VOWEL radical)."""
    letters = gate_stack.radical_letters(root_str)
    weak_positions = [i for i, l in enumerate(letters) if any(ch in gate_stack.WEAK_LETTERS for ch in l)]
    if weak_positions == [1]:
        return "hollow"
    if weak_positions == [0]:
        return "assimilated"
    if weak_positions == [2]:
        return "defective"
    if set(weak_positions) == {0, 2}:
        return "lafif_mafruq"
    if set(weak_positions) == {1, 2}:
        return "lafif_maqrun"
    return None


def _as_mapping(v):
    """Fail-closed type guard: any DATA a rule file supplies where a mapping is required must be treated as an
    empty mapping if it is not actually a dict — never a string (whose `in` means substring containment) or a
    list (whose `in` means element membership), and never an attribute-access target that could raise."""
    return v if isinstance(v, dict) else {}


def _hollow_reason(root_str, gate_data):
    """The hollow-specific abstention reason, DATA-DRIVEN from `weak-root-gates.json`'s
    `hollow_pattern_vowels.recorded_c2_vowels` table: a recorded C2 pattern vowel keeps the standard weak-root
    reason; an unrecorded one sharpens to `hollow_root_c2_hidden` (sarf/procedures/weak-root.md's own vocabulary).
    Emptying/removing this table collapses every hollow root to the unrecorded reason. A malformed (non-mapping)
    table is never trusted as a per-root lookup: it fails closed to the unrecorded reason."""
    hp = _as_mapping(gate_data.get("hollow_pattern_vowels"))
    table = _as_mapping(hp.get("recorded_c2_vowels"))
    if root_str in table:
        return hp.get("recorded_reason") or "hollow_defective_assimilated"
    return hp.get("unrecorded_reason") or "hollow_root_c2_hidden"


def _lafif_reason(root_str, lafif_class, attested_ops, gate_data):
    """The لفيف ordered-composition check, DATA-DRIVEN from `weak-root-gates.json`'s
    `lafif_compositions.classes[lafif_class].operations`. Returns None (no abstention — the composition is
    complete and correctly ordered) or the exact abstention reason. Removing/emptying the `classes` table makes
    every لفيف row fail closed as incomplete (an unknown class can never license a candidate).

    Before ever consulting the row's declared `attested_ops`, the ACTUAL class derived from `root_str`'s own
    radical positions (`_weak_class_from_root`, never the row's own claim) must exactly agree with
    `"lafif_" + lafif_class`; a مفروق root relabelled مقرون, a sound root, or a hamza-carrier root abstains
    incomplete regardless of what operations the row supplies. A malformed (non-mapping) `classes` table fails
    closed the same way, never raising."""
    lc = _as_mapping(gate_data.get("lafif_compositions"))
    incomplete_reason = lc.get("incomplete_reason") or "lafif_composition_incomplete"
    if _weak_class_from_root(root_str) != "lafif_" + str(lafif_class or ""):
        return incomplete_reason
    classes = _as_mapping(lc.get("classes"))
    required = _as_mapping(classes.get(lafif_class)).get("operations") or []
    attested = list(attested_ops or [])
    if not required:
        return incomplete_reason
    if attested == required:
        return None
    if sorted(attested) == sorted(required):
        return lc.get("unordered_reason") or "lafif_composition_unordered"
    return incomplete_reason


def _voice_decision(ctx, lexeme, slot_family, surface):
    """Compare `surface` against the REAL paradigm generator's active/passive candidates for the same
    lexeme+slot_family (`tools.fusha_paradigm_generate.generate_verb`, unmodified). An unvocalized surface (no
    harakah at all) never licenses a voice reading, and a surface matching neither/both real melody templates
    abstains rather than guess. Never re-derives the vocalism table; the melody itself always comes from
    verb-measures.json through the real generator."""
    active_rows = ctx.generate_verb(lexeme, slots=[slot_family + "_active"])
    passive_rows = ctx.generate_verb(lexeme, slots=[slot_family + "_passive"])
    if not active_rows or not passive_rows or not _has_marks(surface):
        return {"decision": "abstain", "voice": None, "reason": "voice_undetermined"}
    active_surface = active_rows[0]["value"]["generated_surface"]
    passive_surface = passive_rows[0]["value"]["generated_surface"]
    is_active = surface == active_surface
    is_passive = surface == passive_surface
    if is_active and not is_passive:
        return {"decision": "candidate_pending", "voice": "active", "reason": None}
    if is_passive and not is_active:
        return {"decision": "candidate_pending", "voice": "passive", "reason": None}
    return {"decision": "abstain", "voice": None, "reason": "voice_undetermined"}


def adapter_weak_root_and_voice(rows, spec, ctx, root):
    """sarf/evals/weak-root-and-voice-eval.jsonl -> entry/paradigm-level weak-root and voice decisions.

    Every row is anchored by exactly ONE call to the REAL `tools/rm40_gate_stack.py:slot_gate` — the same gate
    `tools/fusha_paradigm_generate.py:generate_verb` uses in production — confirming the row's root is (or is not)
    weak/hamza for RM-40 template generation. Three modes then refine the row's OWN candidate_pending/abstain
    verdict:

      * weak_reason_classification — a single hidden weak radical (hollow/defective/assimilated) or a hamza seat;
        the SPECIFIC abstention reason is computed from the radical's POSITION and, for hollow roots, from the
        `hollow_pattern_vowels` DATA this adapter reads directly out of `sarf/rules/weak-root-gates.json` (data the
        id-citation-only gate stack never reads).
      * lafif_composition — two weak radicals (مفروق/مقرون); candidate_pending only when the row's declared
        `attested_operations` exactly match the ORDERED operation list in `lafif_compositions` data.
      * voice_determination — `_voice_decision` compares the row's surface against the REAL generator's own
        active/passive candidates; an unvocalized surface, or one matching neither/both melodies, abstains
        `voice_undetermined` and never defaults active.

    No occurrence-level dogfood evidence exists for this family (every row carries
    `no_occurrence_dogfood_evidence: true`): candidate entry/paradigm grounding here is never an occurrence fact.
    """
    fails, decided = [], 0
    props = _Props()
    abstain_rows = candidate_pending_rows = 0
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        mode = row.get("mode")
        root_str = row.get("root")
        if not root_str or mode not in _WRV_MODES:
            fails.append(_f(rid, "row_well_formed", "missing root or unknown mode %r" % mode))
            continue
        gate = ctx.slot_gate(root_str, row.get("measure"), row.get("slot"))
        decided += 1
        props.hit(rid, _SLOT_GATE, "real_gate_anchors_every_row")

        expected_decision = row.get("expected_decision")
        expected_reason = row.get("expected_reason")
        got_decision = got_reason = got_voice = None

        if mode == "weak_reason_classification":
            props.hit(rid, _SLOT_GATE, "weak_reason_matches_procedure_vocabulary")
            weak_class = _weak_class_from_root(root_str)
            expected_weak_class = row.get("expected_weak_class")
            if weak_class != expected_weak_class:
                fails.append(_f(rid, "expected_weak_class_matches",
                                "derived weak_class %r, bank expects %r" % (weak_class, expected_weak_class)))
            if gate["decision"] == "emit":
                got_decision = "candidate_pending"
            else:
                got_decision = "abstain"
                gate_data = _weak_root_gate_data(root)
                # the REAL gate's own hamza_seat defeater always wins: a root may carry BOTH a hamza carrier and a
                # weak radical (ء و ل), and the position-derived hollow/defective/assimilated reason must never
                # overwrite the gate's own hamza finding.
                if gate["defeater"] == "hamza_seat":
                    got_reason = "hamza_seat"
                elif weak_class == "hollow":
                    got_reason = _hollow_reason(root_str, gate_data)
                elif weak_class == "assimilated":
                    got_reason = "assimilated_c1_dropped"
                elif weak_class == "defective":
                    got_reason = "defective_c3_alternation"
                else:
                    got_reason = gate["defeater"]
        elif mode == "lafif_composition":
            props.hit(rid, _SLOT_GATE, "lafif_ordered_composition")
            gate_data = _weak_root_gate_data(root)
            reason = _lafif_reason(root_str, row.get("lafif_class"), row.get("attested_operations"), gate_data)
            # the RM-40 gate-decision cross-check only applies once the row's declared class has already agreed
            # with the root's own derived class AND the operations fully licensed candidate_pending; a root that
            # was never genuinely لفيف abstains on the class check alone and never reaches this cross-check.
            if reason is None and gate["decision"] != "abstain":
                fails.append(_f(rid, "lafif_ordered_composition",
                                "a genuinely doubly-weak root must abstain the RM-40 generation gate"))
            got_decision = "abstain" if reason else "candidate_pending"
            got_reason = reason
        else:  # voice_determination
            lexeme = {"pos": "verb", "lemma": row.get("lemma"), "root": root_str, "measure": row.get("measure")}
            rec = _voice_decision(ctx, lexeme, row.get("slot_family") or "", row.get("surface") or "")
            props.hit(rid, _GEN_VERB, "voice_never_defaults_active")
            got_decision, got_reason, got_voice = rec["decision"], rec["reason"], rec["voice"]
            if not _has_marks(row.get("surface") or "") and got_decision != "abstain":
                fails.append(_f(rid, "voice_never_defaults_active",
                                "an unvocalized surface must never license a voice reading"))

        if got_decision != expected_decision:
            fails.append(_f(rid, "decision_matches",
                            "decided %r, bank expects %r" % (got_decision, expected_decision)))
        if got_decision == "abstain":
            abstain_rows += 1
            if expected_reason not in _WRV_ABSTAIN_REASONS:
                fails.append(_f(rid, "reason_closed_set",
                                "bank's expected_reason %r outside the closed abstention vocabulary"
                                % expected_reason))
            if got_reason != expected_reason:
                fails.append(_f(rid, "reason_matches",
                                "decided reason %r, bank expects %r" % (got_reason, expected_reason)))
            if mode == "voice_determination":
                want_voice = row.get("expected_voice")
                if got_voice is not None or want_voice is not None:
                    fails.append(_f(rid, "voice_matches",
                                    "an abstaining voice row must carry no voice: decided voice %r, bank "
                                    "expects %r" % (got_voice, want_voice)))
        else:
            candidate_pending_rows += 1
            if mode == "voice_determination":
                want_voice = row.get("expected_voice")
                if got_voice != want_voice:
                    fails.append(_f(rid, "voice_matches",
                                    "decided voice %r, bank expects %r" % (got_voice, want_voice)))

    return fails, {"rows": len(rows), "decided_rows": decided, "abstain_rows": abstain_rows,
                   "candidate_pending_rows": candidate_pending_rows, "property_hits": props.as_metric()}


def adapter_structural(rows, spec, ctx, root):
    """Structure/vocabulary gate for a bank with no behavioural consumer (fixture_only / candidate_no_consumer).

    It deliberately claims nothing about morphology. It DOES prove the rows are well-formed, uniquely identified,
    address-shaped, and that every surface survives the engine's byte-exactness contract — so the bank is ready for
    the consumer its follow-on packet specifies.
    """
    fails, seen, byte_exact = [], set(), 0
    for i, row in enumerate(rows):
        rid = _rid(row, spec, i)
        fails.extend(_required_field_failures(row, spec, rid))
        fails.extend(_procedure_link_failures(row, root, rid))
        if rid in seen:
            fails.append("%s: duplicate row id" % rid)
        seen.add(rid)
        surface = row.get("surface")
        if surface:
            cands = ctx.segment_candidates(surface)
            if _concat_exact(cands, surface):
                byte_exact += 1
            else:
                fails.append("%s: surface is not byte-exact through the segmenter" % rid)
    return fails, {"rows": len(rows), "decided_rows": 0, "distinct_ids": len(seen),
                   "surfaces_byte_exact": byte_exact}


ADAPTERS = {
    "lattice_ambiguity": adapter_lattice_ambiguity,
    "clitic_split_guard": adapter_clitic_split_guard,
    "collision_quarantine": adapter_collision_quarantine,
    "byte_exact_marks": adapter_byte_exact_marks,
    "hidden_state_evidence": adapter_hidden_state_evidence,
    "key_collapse_pending": adapter_key_collapse_pending,
    "corpus_classifier": adapter_corpus_classifier,
    "letter_ownership_carve": adapter_letter_ownership_carve,
    "derivational_template_carve": adapter_derivational_template_carve,
    "nominal_class_discrimination": adapter_nominal_class_discrimination,
    "weak_root_and_voice": adapter_weak_root_and_voice,
    "structural": adapter_structural,
}


# ---------------------------------------------------------------------------
# contract loading / validation
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# a bounded JSON Schema (draft 2020-12 subset) executor — stdlib only, no dependency added
# ---------------------------------------------------------------------------
_SCHEMA_KEYWORDS = ("type", "enum", "const", "required", "properties", "additionalProperties", "items",
                    "oneOf", "anyOf", "allOf", "minItems", "minLength", "minimum", "maximum", "pattern", "$ref")
_JSON_TYPES = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float),
               "boolean": bool, "null": type(None)}


def _schema_errors(instance, schema, root_schema, path="$"):
    """Validate `instance` against the SUBSET of draft 2020-12 this contract's schema actually uses.

    The subset is closed on purpose: `validate_contract` asserts the schema uses no keyword outside
    `_SCHEMA_KEYWORDS`, so a future schema feature cannot be silently ignored. This is the missing half of the
    round-3 defect: `additionalProperties: false` and duplicate/shape rules were declared but never executed."""
    errs = []
    if not isinstance(schema, dict):
        return errs
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            target = root_schema
            for part in ref[2:].split("/"):
                target = (target or {}).get(part.replace("~1", "/").replace("~0", "~")) if isinstance(target, dict) else None
            if target is None:
                return ["%s: unresolvable $ref %s" % (path, ref)]
            return _schema_errors(instance, target, root_schema, path)
        return ["%s: unsupported $ref %s" % (path, ref)]
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        ok = False
        for one in types:
            py = _JSON_TYPES.get(one)
            if py is None:
                continue
            if one == "integer" and isinstance(instance, bool):
                continue
            if one in ("number", "integer") and isinstance(instance, bool):
                continue
            if isinstance(instance, py):
                ok = True
        if not ok:
            return ["%s: expected type %s, got %s" % (path, t, type(instance).__name__)]
    if "const" in schema and instance != schema["const"]:
        errs.append("%s: expected const %r" % (path, schema["const"]))
    if "enum" in schema and instance not in schema["enum"]:
        errs.append("%s: %r not in enum" % (path, instance))
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append("%s: shorter than minLength %d" % (path, schema["minLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append("%s: does not match pattern %s" % (path, schema["pattern"]))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append("%s: below minimum" % path)
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append("%s: above maximum" % path)
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append("%s: fewer than minItems %d" % (path, schema["minItems"]))
        if "items" in schema:
            for i, el in enumerate(instance):
                errs.extend(_schema_errors(el, schema["items"], root_schema, "%s[%d]" % (path, i)))
    if isinstance(instance, dict):
        for key in schema.get("required") or []:
            if key not in instance:
                errs.append("%s: missing required property %r" % (path, key))
        props = schema.get("properties") or {}
        for key, value in instance.items():
            if key in props:
                errs.extend(_schema_errors(value, props[key], root_schema, "%s.%s" % (path, key)))
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errs.append("%s: additional property %r is forbidden by the schema" % (path, key))
                elif isinstance(extra, dict):
                    errs.extend(_schema_errors(value, extra, root_schema, "%s.%s" % (path, key)))
    for combinator, need in (("oneOf", 1), ("anyOf", 1)):
        if combinator in schema:
            matches = sum(1 for sub_schema in schema[combinator]
                          if not _schema_errors(instance, sub_schema, root_schema, path))
            if matches < need:
                errs.append("%s: matches no %s branch" % (path, combinator))
    for sub_schema in schema.get("allOf") or []:
        errs.extend(_schema_errors(instance, sub_schema, root_schema, path))
    return errs


def _schema_keyword_coverage(schema):
    """Every keyword the schema uses must be one this executor implements (fail closed on an unknown keyword)."""
    unknown = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("$schema", "$id", "$defs", "title", "description", "default", "examples"):
                    continue
                if k in _SCHEMA_KEYWORDS:
                    walk(v)
                elif k in ("properties", "$defs"):
                    walk(v)
                else:
                    # keys inside properties/$defs maps are names, not keywords
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    def walk_schema(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("$schema", "$id", "title", "description", "default", "examples"):
                    continue
                if k == "properties" or k == "$defs":
                    for _name, sub_schema in (v or {}).items():
                        walk_schema(sub_schema)
                    continue
                if k in _SCHEMA_KEYWORDS:
                    if k in ("items", "additionalProperties"):
                        walk_schema(v)
                    elif k in ("oneOf", "anyOf", "allOf"):
                        for sub_schema in v or []:
                            walk_schema(sub_schema)
                    continue
                unknown.add(k)
    walk_schema(schema)
    return sorted(unknown)


def load_schema(root=_REPO):
    with open(os.path.join(root, SCHEMA_REL.replace("/", os.sep)), encoding="utf-8") as fh:
        return json.load(fh)


def load_contract(root=_REPO):
    with open(os.path.join(root, CONTRACT_REL.replace("/", os.sep)), encoding="utf-8") as fh:
        return json.load(fh)


def bank_spec(contract, bank):
    for b in contract["banks"]:
        if b["path"] == bank or os.path.basename(b["path"]) == os.path.basename(bank):
            return b
    raise KeyError("no contract row for bank %r" % bank)


class PathContainmentError(ValueError):
    """A contract-declared path failed containment. Raised BEFORE any filesystem call touches the target."""


def guarded_abs(root, rel, allowed, label):
    """Resolve a contract-declared path, or refuse it without touching the filesystem.

    Round-5 defect: `validate_contract` diagnosed an escaping registry path, but the loaders ran anyway and
    reached `open()` on a target outside the worktree. Diagnosis is not enforcement — every loader now converts a
    declared path through this guard, which performs only string/`realpath` reasoning and raises before any
    `exists`, `walk`, `glob` or `open` can see the rejected target."""
    errors = _path_escape_errors(rel, allowed, label, root)
    if errors:
        raise PathContainmentError("; ".join(errors))
    return os.path.join(root, rel.replace("/", os.sep))


def load_bank(root, spec):
    """Row list for a bank. JSONL -> one object per line; object-form -> the declared cases[]/assertions[] array."""
    path = guarded_abs(root, spec.get("path"), _ALLOWED_BANK_ROOTS, "bank path")
    if spec["form"] == "jsonl":
        rows = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        return rows
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    return list(obj.get(spec["row_key"]) or [])



def _path_escape_errors(rel, allowed, label, root=None):
    """A declared path must be repo-relative, stay inside its allowed root, and resolve inside the worktree.

    Checked BEFORE any I/O and for EVERY path-bearing field, not only banks and Store A: a parent-directory hop in
    a candidate record root would otherwise make the boundary scan walk outside the repository. Containment is
    verified on the real (symlink-resolved) path, so a symlinked directory cannot smuggle the scan out either."""
    out = []
    if not isinstance(rel, str) or not rel:
        return ["%s: missing path" % label]
    if _URL_RE.match(rel):
        out.append("%s: %r is a URL, not a repository path" % (label, rel))
    if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":") or chr(92) in rel:
        out.append("%s: %r is absolute or uses a backslash" % (label, rel))
    if ".." in rel.split("/"):
        out.append("%s: %r escapes the repository" % (label, rel))
    if not any(rel.startswith(a) or rel == a.rstrip("/") for a in allowed):
        out.append("%s: %r is outside the allowed roots %s" % (label, rel, list(allowed)))
    if root and not out:
        base = os.path.realpath(os.path.abspath(root))
        target = os.path.realpath(os.path.join(root, rel.replace("/", os.sep)))
        if target != base and not target.startswith(base + os.sep):
            out.append("%s: %r resolves outside the worktree (symlink escape)" % (label, rel))
    return out


def validate_contract(contract, root=_REPO):
    """Schema execution FIRST, then the semantic checks. Neither substitutes for the other.

    The JSON schema declares `additionalProperties: false`, required key sets and value shapes; until round 3 it
    was never executed, so a forbidden extra key passed. `_schema_errors` now runs the schema, and the semantic
    layer below adds what a schema cannot express (real files, real consumers, real provers, duplicate paths)."""
    errors = []
    try:
        schema = load_schema(root)
    except (OSError, ValueError) as e:
        errors.append("contract: the declared schema could not be loaded (%s)" % type(e).__name__)
        schema = None
    if schema is not None:
        unknown = _schema_keyword_coverage(schema)
        if unknown:
            errors.append("contract: the schema uses keyword(s) this executor does not implement: %s" % unknown)
        errors.extend("schema: " + e for e in _schema_errors(contract, schema, schema))
    seen_bank_paths = {}
    for b in contract.get("banks") or []:
        p = b.get("path")
        seen_bank_paths[p] = seen_bank_paths.get(p, 0) + 1
        errors.extend(_path_escape_errors(p, _ALLOWED_BANK_ROOTS, "contract: bank path"))
    for p, n in sorted(seen_bank_paths.items()):
        if n > 1:
            errors.append("contract: duplicate bank entry %r (%d rows) — every artifact appears exactly once" % (p, n))
    seen_rule_paths = {}
    for r in contract.get("store_a_rules") or []:
        p = r.get("path")
        seen_rule_paths[p] = seen_rule_paths.get(p, 0) + 1
        errors.extend(_path_escape_errors(p, _ALLOWED_RULE_ROOTS, "contract: store A path"))
    for p, n in sorted(seen_rule_paths.items()):
        if n > 1:
            errors.append("contract: duplicate store A entry %r (%d rows)" % (p, n))
    surfaces = contract.get("candidate_boundary_surfaces") or {}
    for i, rel in enumerate(surfaces.get("record_roots") or []):
        errors.extend(_path_escape_errors(rel, _ALLOWED_BOUNDARY_ROOTS,
                                          "contract: candidate_boundary_surfaces.record_roots[%d]" % i, root))
    errors.extend(_path_escape_errors(surfaces.get("projector_registry"), _ALLOWED_BOUNDARY_ROOTS,
                                      "contract: candidate_boundary_surfaces.projector_registry", root))
    inc_paths = contract.get("candidate_increments_not_promoted") or {}
    for name, rel in sorted((inc_paths.get("registry_files") or {}).items()):
        errors.extend(_path_escape_errors(rel, _ALLOWED_REGISTRY_ROOTS,
                                          "contract: registry_files[%s]" % name, root))
    errors.extend(_path_escape_errors(inc_paths.get("projector_registry"), _ALLOWED_BOUNDARY_ROOTS,
                                      "contract: candidate projector_registry", root))
    for key in CONTRACT_REQUIRED:
        if key not in contract:
            errors.append("contract: missing top-level key %r" % key)
    if contract.get("schema") != SCHEMA_ID:
        errors.append("contract: schema is %r, expected %r" % (contract.get("schema"), SCHEMA_ID))
    if sorted((contract.get("disposition_definitions") or {}).keys()) != sorted(DISPOSITIONS):
        errors.append("contract: disposition_definitions must define exactly the four dispositions")
    for b in contract.get("banks") or []:
        for key in ("path", "form", "row_key", "disposition", "adapter", "consumers", "note",
                    "behavioral_consumer", "secondary_consumers", "metric_floors", "property_coverage",
                    "enforced_properties", "not_enforced_properties", "pinned_metrics", "followup_packet"):
            if key not in b:
                errors.append("contract: bank %r missing %r" % (b.get("path"), key))
        if b.get("disposition") not in DISPOSITIONS:
            errors.append("contract: bank %r has an unknown disposition" % b.get("path"))
        if b.get("adapter") not in ADAPTERS:
            errors.append("contract: bank %r names an unknown adapter %r" % (b.get("path"), b.get("adapter")))
        if b.get("form") not in ("jsonl", "object"):
            errors.append("contract: bank %r has an unknown form" % b.get("path"))
        if b.get("form") == "object" and not b.get("row_key"):
            errors.append("contract: object-form bank %r must name its row_key" % b.get("path"))
        # Existence is checked ONLY after containment passes: a rejected path must never reach the filesystem,
        # not even through an exists() probe (round-5 defect: diagnosis without enforcement).
        if not _path_escape_errors(b.get("path"), _ALLOWED_BANK_ROOTS, "bank path", root):
            if not os.path.exists(os.path.join(root, (b.get("path") or "").replace("/", os.sep))):
                errors.append("contract: bank %r does not exist" % b.get("path"))
        if b.get("disposition") == "implemented_and_consumed":
            if not b.get("consumers"):
                errors.append("contract: bank %r claims behavioural coverage with no consumer" % b.get("path"))
            if b.get("behavioral_consumer") not in DECISION_CONSUMERS:
                errors.append("contract: bank %r claims behavioural coverage without naming a production DECISION "
                              "consumer (got %r); normalization and row-internal consistency do not qualify"
                              % (b.get("path"), b.get("behavioral_consumer")))
        elif b.get("behavioral_consumer") is not None:
            errors.append("contract: bank %r is not behaviourally covered but names a behavioral_consumer"
                          % b.get("path"))
        seen_props = {}
        for prop in (b.get("property_coverage") or []):
            for key in ("property", "decided_by", "applicable_rows", "covered"):
                if key not in prop:
                    errors.append("contract: bank %r property_coverage row missing %r" % (b.get("path"), key))
            name = prop.get("property")
            seen_props[name] = seen_props.get(name, 0) + 1
            decided_by = prop.get("decided_by")
            if decided_by not in CONSUMER_SLOTS and not str(decided_by).startswith("structural:"):
                errors.append("contract: bank %r property %r names an unknown decider %r"
                              % (b.get("path"), name, decided_by))
            if prop.get("covered") and decided_by not in CONSUMER_SLOTS:
                errors.append("contract: bank %r property %r is marked covered but is decided structurally — a "
                              "structural assertion is never behavioural coverage" % (b.get("path"), name))
            if prop.get("covered") and not (isinstance(prop.get("applicable_rows"), int)
                                            and prop["applicable_rows"] > 0):
                errors.append("contract: bank %r property %r is marked covered with %r applicable rows — a "
                              "zero-row property may never raise coverage"
                              % (b.get("path"), name, prop.get("applicable_rows")))
        for name, n in sorted(seen_props.items()):
            if n > 1:
                errors.append("contract: bank %r declares property %r %d times" % (b.get("path"), name, n))
        if b.get("disposition") == "implemented_and_consumed" and not (b.get("property_coverage") or []):
            errors.append("contract: bank %r claims coverage without declaring per-property coverage"
                          % b.get("path"))
        for sec in (b.get("secondary_consumers") or []):
            if sec.get("callable") not in CONSUMER_SLOTS:
                errors.append("contract: bank %r names an unknown secondary consumer %r"
                              % (b.get("path"), sec.get("callable")))
            if sec.get("callable") == b.get("behavioral_consumer"):
                errors.append("contract: bank %r lists its per-row consumer as a secondary consumer too"
                              % b.get("path"))
            if not isinstance(sec.get("expected_calls"), int) or not sec.get("applies_to"):
                errors.append("contract: bank %r secondary consumer needs applies_to + integer expected_calls"
                              % b.get("path"))
        for k in (b.get("metric_floors") or {}):
            if k in (b.get("pinned_metrics") or {}):
                errors.append("contract: bank %r pins and floors the same metric %r — a diagnostic that may "
                              "improve must be floored, never pinned" % (b.get("path"), k))
        if b.get("disposition") in ("candidate_no_consumer", "fixture_only") and not b.get("followup_packet"):
            errors.append("contract: bank %r is not behaviourally covered and names no follow-on packet"
                          % b.get("path"))
        if b.get("disposition") == "documentary" and not b.get("note"):
            errors.append("contract: documentary bank %r must say why it is documentary" % b.get("path"))
    if sorted(set(REQUIRED_BEHAVIORAL_BANKS)) != sorted(
            b["path"] for b in (contract.get("banks") or [])
            if b.get("disposition") == "implemented_and_consumed"):
        errors.append("contract: the behaviourally covered bank set drifted from REQUIRED_BEHAVIORAL_BANKS — "
                      "relabelling a justified bank fixture_only (or promoting one without a decision consumer) "
                      "must be a deliberate code change, not a contract edit")
    for r in contract.get("store_a_rules") or []:
        for key in ("path", "disposition", "consumers", "note", "consumption_kind"):
            if key not in r:
                errors.append("contract: store A row %r missing %r" % (r.get("path"), key))
        if r.get("disposition") not in DISPOSITIONS:
            errors.append("contract: store A row %r has an unknown disposition" % r.get("path"))
        if r.get("consumption_kind") not in CONSUMPTION_KINDS:
            errors.append("contract: store A row %r has an unknown consumption_kind %r"
                          % (r.get("path"), r.get("consumption_kind")))
        if (r.get("disposition") == "implemented_and_consumed") != (r.get("consumption_kind") == "data_driven"):
            errors.append("contract: store A row %r may claim implemented_and_consumed only with "
                          "consumption_kind=data_driven (rule CONTENT changes a production decision)" % r.get("path"))
    inc = contract.get("candidate_increments_not_promoted") or {}
    if inc.get("status") != "candidate_not_released":
        errors.append("contract: candidate increments must stay candidate_not_released")
    return errors


def _prove_verb_measures_via_paradigm_generate(root=_REPO):
    """Bounded mutation proof binding `sarf/rules/verb-measures.json` to ONE declared consumer.

    `tools/fusha_paradigm_generate` loads the file's `forms[]` through its own `_measures()` and substitutes the
    slot template into the radicals, so changing a slot template must change that module's generated surface. The
    proof is bound to this module's own loader: a prover exercising a different module can never satisfy a
    consumer declaration (the round-2 defect). Nothing on disk is touched — the cached payload is swapped in
    memory and restored. Returns a failure list (empty = proven)."""
    fails = []
    try:
        pg = consumers_module("fusha_paradigm_generate")
    except Exception as e:  # noqa: BLE001
        return ["verb-measures.json: cannot import the paradigm generator (%s)" % type(e).__name__]
    original = pg._measures
    lexeme = {"root": "ك ت ب", "measure": "I", "lemma": "كتب"}
    try:
        base = pg.generate_verb(lexeme)
    except Exception as e:  # noqa: BLE001
        return ["verb-measures.json: paradigm generator entry point changed (%s)" % type(e).__name__]

    def _surfaces(rows):
        out = []
        for r in rows or []:
            v = r.get("value") if isinstance(r, dict) else None
            if isinstance(v, dict) and v.get("generated_surface"):
                out.append(v["generated_surface"])
            elif isinstance(r, dict) and r.get("generated_surface"):
                out.append(r["generated_surface"])
        return out

    before = _surfaces(base)
    if not before:
        return ["verb-measures.json: the generator produced no surface to mutate against"]
    payload = copy.deepcopy(original())
    # Mutate the wazn TEMPLATES of the measure under test: swap the first radical placeholder for another letter.
    # If the file were merely cited, the generated surfaces would be unaffected.
    changed = False
    form = payload.get("I") or {}
    for slot, val in list(form.items()):
        if isinstance(val, str) and "ف" in val:
            form[slot] = val.replace("ف", "س")
            changed = True
    if not changed:
        return ["verb-measures.json: no wazn template found to mutate (file shape changed?)"]
    pg._measures = lambda: payload
    try:
        after = _surfaces(pg.generate_verb(lexeme))
    except Exception:  # noqa: BLE001  a rejected decision is also a behavioural change
        after = ["<generator rejected the mutated rule content>"]
    finally:
        pg._measures = original
    if after == before:
        fails.append("verb-measures.json: mutating a wazn template did NOT change the production output — the "
                     "file is cited, not consumed; it may not be labelled implemented_and_consumed")
    return fails


# Registered bounded mutation provers, keyed by (rule file, DECLARED CONSUMER MODULE). Every declared consumer of
# a data_driven row must have its own entry: a prover for module A never proves that module B consumes the file.
DATA_DRIVEN_PROVERS = {
    ("sarf/rules/verb-measures.json", "tools/fusha_paradigm_generate.py"):
        _prove_verb_measures_via_paradigm_generate,
}


def check_store_a(contract, root=_REPO):
    """Prove each Store A rule row's disposition against the repository, not against prose.

    A filename appearing in a module's source proves DISCOVERY, never consumption. So an `implemented_and_consumed`
    row must additionally register a bounded mutation prover in DATA_DRIVEN_PROVERS showing that changing the rule
    CONTENT changes (or is rejected by) the production decision."""
    fails, counts = [], dict((d, 0) for d in DISPOSITIONS)
    tools_dir = os.path.join(root, "tools")
    sources = {}
    for fn in sorted(os.listdir(tools_dir)):
        if fn.endswith(".py"):
            try:
                with open(os.path.join(tools_dir, fn), encoding="utf-8") as fh:
                    sources[fn] = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
    for row in contract.get("store_a_rules") or []:
        rel = row.get("path") or ""
        base = os.path.basename(rel)
        disp = row.get("disposition")
        counts[disp] = counts.get(disp, 0) + 1
        try:
            abs_path = guarded_abs(root, rel, _ALLOWED_RULE_ROOTS, "store A path")
        except PathContainmentError as e:
            fails.append("%s: refused before any filesystem access (%s)" % (rel, e))
            continue
        if not os.path.exists(abs_path):
            fails.append("%s: rule file does not exist" % rel)
            continue
        try:
            with open(abs_path, encoding="utf-8") as fh:
                json.load(fh)
        except ValueError:
            fails.append("%s: rule file is not valid JSON" % rel)
            continue
        referencing = sorted(fn for fn, src in sources.items() if base in src)
        declared = [os.path.basename(c) for c in row.get("consumers") or []]
        if disp == "implemented_and_consumed":
            if not declared:
                fails.append("%s: implemented_and_consumed with no declared consumer" % rel)
            for d in declared:
                if d not in referencing:
                    fails.append("%s: declared consumer %s does not read this rule file" % (rel, d))
            if not declared:
                fails.append("%s: implemented_and_consumed with no declared consumer to bind a prover to" % rel)
            for d in row.get("consumers") or []:
                prover = DATA_DRIVEN_PROVERS.get((rel, d))
                if prover is None:
                    fails.append("%s: declared consumer %s has no bounded mutation prover bound to it — a source "
                                 "reference, a constant or a comment proves discovery, never consumption"
                                 % (rel, d))
                else:
                    fails.extend(prover(root))
        elif disp == "candidate_no_consumer":
            if referencing:
                fails.append("%s: labelled candidate_no_consumer but %s reads it" % (rel, ", ".join(referencing)))
        elif disp == "fixture_only":
            if not declared:
                fails.append("%s: fixture_only must name the gate that reads it" % rel)
            for d in declared:
                if d not in referencing:
                    fails.append("%s: declared gate %s does not reference this rule file" % (rel, d))
    return fails, counts


def check_candidates_not_promoted(contract, root=_REPO):
    """@2.1–@2.4 must remain CANDIDATE: SKILL.md still says NOT released, and nothing here treats them as authority."""
    fails = []
    with open(os.path.join(root, "sarf", "SKILL.md"), encoding="utf-8") as fh:
        skill = fh.read()
    inc = contract.get("candidate_increments_not_promoted") or {}
    for name in inc.get("increments") or []:
        suffix = name.split("@")[-1]
        if not re.search(r"arf@%s\b[^\n]*NOT released" % re.escape(suffix), skill):
            fails.append("sarf/SKILL.md no longer marks %s as NOT released" % name)
    blob = json.dumps(contract, ensure_ascii=False)
    for word in ("released_authority", "promoted_to_accepted", "@2.1-accepted", "@2.2-accepted",
                 "@2.3-accepted", "@2.4-accepted"):
        if word in blob:
            fails.append("contract asserts promotion marker %r" % word)
    fails.extend(check_candidate_registry_state(contract, root))
    return fails


_PROMOTED_STATES = ("certified", "released", "accepted", "published", "live")
_PUBLIC_FLAGS = ("public_materialization_allowed", "live_mutation_allowed", "public_write_allowed")
_PUBLIC_TARGET_KEYS = ("public_target", "public_url", "public_materialization_target", "live_target",
                       "deploy_target")


def _local_candidate_ids(obj, candidate_ids):
    """Candidate ids cited by this object's OWN scalar fields (not by its descendants)."""
    found = set()
    for value in obj.values():
        if isinstance(value, str) and value in candidate_ids:
            found.add(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item in candidate_ids:
                    found.add(item)
    return found


def _walk_records(node, candidate_ids, inherited=frozenset(), path="$"):
    """Yield (json-path, object, linked_candidate_ids) with candidate linkage INHERITED down the tree.

    Round-4 defect: linkage used to be recomputed independently at each nested object, so a parent carrying the
    candidate `rule_id` and a child carrying `certification_state: certified` produced no violation. Identity
    established by any ancestor now travels to every descendant object and array element, and each object still
    contributes its own local ids."""
    if isinstance(node, dict):
        linked = set(inherited) | _local_candidate_ids(node, candidate_ids)
        yield path, node, linked
        for k, v in node.items():
            for item in _walk_records(v, candidate_ids, linked, "%s.%s" % (path, k)):
                yield item
    elif isinstance(node, list):
        for i, v in enumerate(node):
            for item in _walk_records(v, candidate_ids, inherited, "%s[%d]" % (path, i)):
                yield item


def _cited_candidates(record, candidate_ids):
    """The candidate rule ids this record cites anywhere in its strings."""
    found = set()
    stack = [record]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, str) and node in candidate_ids:
            found.add(node)
    return found


def candidate_boundary_violations(records, candidate_ids):
    """Read-only cross-join: a record citing a CANDIDATE rule may not claim certification or public output.

    `records` is a list of (source, loaded json) so the synthetic mutation tests can inject exact records without
    touching any repository file. Nothing here promotes, certifies or edits anything."""
    fails = []
    for source, doc in records:
        for path, obj, cited in _walk_records(doc, candidate_ids):
            if not cited:
                continue
            sample = sorted(cited)[:2]
            for key, value in obj.items():
                lowered = key.lower()
                if isinstance(value, str) and (lowered.endswith("state") or lowered.endswith("status")):
                    if value.lower() in _PROMOTED_STATES:
                        fails.append("%s %s: a record citing candidate rule(s) %s declares %s=%r"
                                     % (source, path, sample, key, value))
                if key in _PUBLIC_FLAGS and value is True:
                    fails.append("%s %s: a record citing candidate rule(s) %s sets %s=true"
                                 % (source, path, sample, key))
                if key in _PUBLIC_TARGET_KEYS and value:
                    fails.append("%s %s: a record citing candidate rule(s) %s names a public/live target in %s"
                                 % (source, path, sample, key))
    return fails


def load_boundary_records(contract, root=_REPO):
    """Load every declared boundary surface as (source, json). Deterministic order; read-only."""
    surfaces = contract.get("candidate_boundary_surfaces") or {}
    records = []
    for rel in surfaces.get("record_roots") or []:
        try:
            abs_path = guarded_abs(root, rel, _ALLOWED_BOUNDARY_ROOTS, "record_roots")
        except PathContainmentError:
            continue  # refused before isdir/walk/open ever sees the target
        paths = []
        if os.path.isdir(abs_path):
            for dirpath, _dirs, files in os.walk(abs_path):
                for fn in sorted(files):
                    if fn.endswith(".json") or fn.endswith(".jsonl"):
                        paths.append(os.path.join(dirpath, fn))
        elif os.path.exists(abs_path):
            paths.append(abs_path)
        for path in sorted(paths):
            rel_path = os.path.relpath(path, os.path.abspath(root)).replace(os.sep, "/")
            try:
                if path.endswith(".jsonl"):
                    with open(path, encoding="utf-8") as fh:
                        for line in fh:
                            if line.strip():
                                records.append((rel_path, json.loads(line)))
                else:
                    with open(path, encoding="utf-8") as fh:
                        records.append((rel_path, json.load(fh)))
            except (OSError, ValueError):
                records.append((rel_path, {"__unreadable__": True}))
    return records


def check_candidate_registry_state(contract, root=_REPO, extra_records=None):
    """Join the @2.1-@2.4 registry rows to their registered projectors and prove candidate state end to end.

    Prose markers in SKILL.md are not enough: a rule is effectively promoted the moment a consumer or projector
    treats it as released authority. So for every increment this checks the REGISTRY rows (status + gate tier) and
    then every projector registration that cites one of those rule ids (candidate projection only, no certification
    verb, no 'released' description). It reads and asserts; it never alters candidate status."""
    fails = []
    inc = contract.get("candidate_increments_not_promoted") or {}
    registry_files = inc.get("registry_files") or {}
    candidate_ids = set()
    for name in inc.get("increments") or []:
        rel = registry_files.get(name)
        if not rel:
            fails.append("%s: no registry file declared in the contract" % name)
            continue
        try:
            path = guarded_abs(root, rel, _ALLOWED_REGISTRY_ROOTS, "registry_files[%s]" % name)
        except PathContainmentError as e:
            fails.append("%s: registry file %r refused before any filesystem access (%s)" % (name, rel, e))
            continue
        if not os.path.exists(path):
            fails.append("%s: registry file %s is missing" % (name, rel))
            continue
        suffix = name.split("@")[-1]
        rows = 0
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                rows += 1
                rid = row.get("skill_rule_id")
                if rid:
                    candidate_ids.add(rid)
                if row.get("status") != "candidate":
                    fails.append("%s: registry row %s has status %r, not candidate" % (name, rid, row.get("status")))
                gate = str(row.get("gate") or "")
                if not gate.startswith("@%s-candidate" % suffix):
                    fails.append("%s: registry row %s carries gate tier %r, which is not a candidate tier"
                                 % (name, rid, gate))
        if rows == 0:
            fails.append("%s: registry file %s has no rows to check" % (name, rel))
    proj_rel = inc.get("projector_registry")
    if not proj_rel:
        fails.append("candidate check: no projector registry declared in the contract")
        return fails
    try:
        proj_path = guarded_abs(root, proj_rel, _ALLOWED_BOUNDARY_ROOTS, "candidate projector_registry")
    except PathContainmentError as e:
        fails.append("candidate check: projector registry %r refused before any filesystem access (%s)"
                     % (proj_rel, e))
        return fails
    if not os.path.exists(proj_path):
        fails.append("candidate check: projector registry %s is missing" % proj_rel)
        return fails
    with open(proj_path, encoding="utf-8") as fh:
        proj = json.load(fh)
    authority = str(proj.get("gate_authority") or "").lower()
    if "candidate projections only" not in authority:
        fails.append("candidate check: the projector registry no longer states that projectors emit CANDIDATE "
                     "projections only")
    touched = 0
    for reg in proj.get("registered") or []:
        cited = set(reg.get("skill_rule_ids") or []) & candidate_ids
        if not cited:
            continue
        touched += 1
        entry = reg.get("registry_entry") or {}
        pid = reg.get("projector_id")
        # A projector citing a CANDIDATE rule must itself stay a candidate projection: no auto_safe tier, no
        # certification output, guards preserved, and no field asserting released/accepted authority.
        tier = str(entry.get("gate_tier") or "")
        if tier.startswith("auto_safe") or "auto_certify" in tier:
            fails.append("candidate check: projector %s cites candidate rule(s) %s at gate tier %r"
                         % (pid, sorted(cited)[:2], tier))
        if entry.get("status") not in (None, "candidate"):
            fails.append("candidate check: projector %s cites candidate rule(s) %s but declares status %r"
                         % (pid, sorted(cited)[:2], entry.get("status")))
        if not entry.get("defeater_checks"):
            fails.append("candidate check: projector %s cites candidate rule(s) %s with no defeater checks "
                         "(guards must survive)" % (pid, sorted(cited)[:2]))
        if "certif" in str(reg.get("kind") or "").lower():
            fails.append("candidate check: projector %s cites a candidate rule with a certifying kind %r"
                         % (pid, reg.get("kind")))
        for field in ("target_population_note", "kind"):
            if "released authority" in str(reg.get(field) or "").lower():
                fails.append("candidate check: projector %s describes a candidate rule as released authority "
                             "in %s" % (pid, field))
    if touched != inc.get("expected_projector_registrations_citing_candidates"):
        fails.append("candidate check: %d projector registration(s) cite a candidate rule id, contract expects %r "
                     "— an unexpected registration must be reviewed, not absorbed"
                     % (touched, inc.get("expected_projector_registrations_citing_candidates")))
    # ---- the cross-join: projector ledgers, certification stores and any public-materialization surface ----
    records = load_boundary_records(contract, root)
    if extra_records:
        records = list(records) + list(extra_records)
    surfaces = contract.get("candidate_boundary_surfaces") or {}
    minimum = surfaces.get("expected_records_scanned_min") or 0
    if len(records) < minimum:
        fails.append("candidate check: only %d boundary record(s) scanned, contract expects at least %d — a "
                     "surface that silently disappeared must be reviewed, not assumed clean"
                     % (len(records), minimum))
    fails.extend("candidate boundary: " + f for f in candidate_boundary_violations(records, candidate_ids))
    return fails


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def run_adapter(spec, rows, ctx, root):
    """Run one bank's adapter with COUNTING proxies around every contract-declared consumer callable.

    The counts are taken at the call site of the exact callable named in the contract, not from the adapter's own
    bookkeeping, so `decided_rows` can never be inflated by counting a different function (the round-1 defect: a
    bank declared `check_text` while only `build_morphology_lattice` ran per row)."""
    counted = _mutate(ctx)
    calls = {}
    for name, slot in CONSUMER_SLOTS.items():
        real = getattr(counted, slot)
        calls[name] = 0

        def _proxy(_real=real, _name=name):
            def inner(*a, **kw):
                calls[_name] += 1
                return _real(*a, **kw)
            return inner
        setattr(counted, slot, _proxy())
    fails, metrics = ADAPTERS[spec["adapter"]](rows, spec, counted, root)
    metrics = dict(metrics)
    metrics["consumer_calls"] = calls
    return fails, metrics


def _pin_failures(spec, metrics):
    """A pinned metric is the MEASURED behaviour of the live consumer; drift either way is a red gate.

    Pins are for measurements that must not move at all (row counts, quarantine counts). A metric that records a
    KNOWN-WRONG state (agreement with a contract the consumer does not implement) is floored instead, so a later
    repair that improves it cannot fail the gate."""
    out = []
    for k, want in (spec.get("pinned_metrics") or {}).items():
        got = metrics.get(k)
        if got != want:
            out.append("pinned metric %r drifted: expected %r, measured %r" % (k, want, got))
    for k, floor in (spec.get("metric_floors") or {}).items():
        got = metrics.get(k)
        if not isinstance(got, (int, float)) or got < floor:
            out.append("metric %r regressed below its floor: floor %r, measured %r (improvement is allowed; "
                       "regression is not)" % (k, floor, got))
    return out


def run_all(root=_REPO, strict=False, only=None, ctx=None, contract=None):
    # `contract` is injectable so an adversarial test can run a deliberately wrong declaration through the real
    # validation path (e.g. declaring a subset consumer as the per-row consumer) and require it to fail closed.
    contract = contract if contract is not None else load_contract(root)
    ctx = ctx or Consumers.real()
    report = {"schema": SCHEMA_ID, "banks": [], "failures": [], "total_rows": 0, "behavioral_rows": 0,
              "uncovered_rows": 0, "selected": only, "candidate_boundary": "not_checked",
              "covered_property_count": 0, "uncovered_property_count": 0,
              "total_banks": 0, "by_disposition": dict((d, 0) for d in DISPOSITIONS)}
    errors = validate_contract(contract, root)
    report["failures"].extend(errors)
    if errors:
        # ABORT BEFORE ANY CONTRACT-DIRECTED I/O. A contract that fails validation may name a path that must never
        # be opened, walked or globbed, so nothing below this line runs: no bank loading, no Store A proving, no
        # boundary scan. The loaders enforce containment independently as well (defence in depth).
        report["aborted_before_io"] = True
        report["candidate_boundary"] = "not_checked"
        report["exit_code"] = 1
        return report
    selected = [s for s in contract["banks"]
                if not only or s["path"] == only or os.path.basename(s["path"]) == os.path.basename(only)]
    if only and not selected:
        # FAIL CLOSED: an unknown/typo'd --bank must never filter to an empty set and print a pass marker.
        report["failures"].append("unknown --bank selection %r: no contract row matches (known banks: %s)"
                                  % (only, ", ".join(b["path"] for b in contract["banks"])))
        report["exit_code"] = 1
        return report
    for spec in selected:
        rows = load_bank(root, spec)
        fails, metrics = run_adapter(spec, rows, ctx, root)
        fails = list(fails) + _pin_failures(spec, metrics)
        decided = metrics.get("decided_rows")
        if not isinstance(decided, int):
            fails.append("adapter %r did not report decided_rows; coverage may never be assumed"
                         % spec["adapter"])
            decided = 0
        calls = metrics.get("consumer_calls") or {}
        primary = spec.get("behavioral_consumer")
        if spec["disposition"] == "implemented_and_consumed":
            if decided != len(rows):
                fails.append("bank claims behavioural coverage but a decision consumer decided only %d of %d rows"
                             % (decided, len(rows)))
            observed = calls.get(primary, 0)
            if observed != len(rows):
                fails.append("declared per-row consumer %s was invoked %d time(s) for %d rows — a bank may not "
                             "claim per-row consumption of a callable it does not call per row"
                             % (primary, observed, len(rows)))
        observed_props = metrics.get("property_hits") or {}
        covered_props, uncovered_props = [], []
        for prop in (spec.get("property_coverage") or []):
            key = prop.get("property")
            hit = observed_props.get(key) or {}
            seen = hit.get("rows", 0)
            want = prop.get("applicable_rows")
            if seen != want:
                fails.append("property %r was evaluated on %d row(s), contract declares %r applicable"
                             % (key, seen, want))
            broke = [f for f in fails if ("[%s]" % key) in f]
            if prop.get("covered"):
                decider = prop.get("decided_by")
                by_callable = (hit.get("by_callable") or {}).get(decider, 0)
                if by_callable != want:
                    fails.append("property %r is declared covered by %s but that callable produced the asserted "
                                 "value for %d of %r row(s) — a covered property must be bound to its declared "
                                 "callable" % (key, decider, by_callable, want))
                    broke = broke or [True]
                if not seen:
                    fails.append("property %r is declared covered but was never evaluated" % key)
                    broke = broke or [True]
            if prop.get("covered") and not broke:
                covered_props.append(key)
            elif not prop.get("covered"):
                uncovered_props.append(key)
        for key in sorted(observed_props):
            if key not in {p.get("property") for p in (spec.get("property_coverage") or [])}:
                fails.append("property %r was evaluated but is not declared in property_coverage" % key)
        for sec in (spec.get("secondary_consumers") or []):
            observed = calls.get(sec.get("callable"), 0)
            if observed != sec.get("expected_calls"):
                fails.append("secondary consumer %s was invoked %d time(s), contract declares %r for %s"
                             % (sec.get("callable"), observed, sec.get("expected_calls"), sec.get("applies_to")))
        if spec["disposition"] != "implemented_and_consumed" and decided:
            fails.append("bank is not behaviourally covered yet reports %d decided rows" % decided)
        if not rows:
            fails.append("bank has zero rows: an empty selection is never a pass")
        report["banks"].append({"bank": spec["path"], "disposition": spec["disposition"],
                                "adapter": spec["adapter"], "rows": len(rows),
                                "covered_properties": covered_props, "uncovered_properties": uncovered_props,
                                "checked": decided, "structural_rows": len(rows) - decided,
                                "behavioral_consumer": spec.get("behavioral_consumer"),
                                "consumers": spec["consumers"], "metrics": metrics,
                                "failures": fails})
        report["total_rows"] += len(rows)
        report["behavioral_rows"] += decided
        report["uncovered_rows"] += len(rows) - decided
        report["total_banks"] += 1
        report["by_disposition"][spec["disposition"]] += 1
        report["failures"].extend("%s: %s" % (spec["path"], f) for f in fails)
    report["covered_property_count"] = sum(len(b.get("covered_properties") or []) for b in report["banks"])
    report["uncovered_property_count"] = sum(len(b.get("uncovered_properties") or []) for b in report["banks"])
    if not only:
        sa_fails, sa_counts = check_store_a(contract, root)
        report["store_a"] = {"failures": sa_fails, "by_disposition": sa_counts}
        report["failures"].extend("sarf/rules: %s" % f for f in sa_fails)
        cand = check_candidates_not_promoted(contract, root)
        report["candidate_increments_not_promoted"] = not cand
        report["candidate_boundary"] = "verified" if not cand else "failed"
        report["failures"].extend(cand)
        if strict:
            uncovered = [b["bank"] for b in report["banks"]
                         if b["disposition"] in ("candidate_no_consumer", "fixture_only")]
            for b in uncovered:
                spec = bank_spec(contract, b)
                packet = spec.get("followup_packet")
                if not packet:
                    report["failures"].append("%s: no follow-on packet for an uncovered bank" % b)
                elif not os.path.exists(os.path.join(root, "qamus", "task-packets", packet + ".json")):
                    report["failures"].append("%s: follow-on packet %s.json is missing" % (b, packet))
    report["exit_code"] = 1 if report["failures"] else 0
    return report


def render(report):
    lines = ["sarf eval runner",
             "  selection: %s" % (report.get("selected") or "--all"),
             "  banks: %d   rows (jsonl rows + object cases[]/assertions[]): %d" % (report["total_banks"],
                                                                                    report["total_rows"]),
             "  rows DECIDED by a production consumer: %d   rows still uncovered (fixture/documentary/candidate): %d"
             % (report["behavioral_rows"], report["uncovered_rows"]),
             "  dispositions: " + ", ".join("%s=%d" % (k, report["by_disposition"][k])
                                            for k in sorted(report["by_disposition"])),
             "  properties COVERED by a decision consumer: %d   properties UNCOVERED (structural/diagnostic): %d"
             % (report.get("covered_property_count", 0), report.get("uncovered_property_count", 0)),
             "  candidate/projector/public boundary: %s%s"
             % (report.get("candidate_boundary", "not_checked"),
                "  (a targeted --bank run does NOT execute this check; it is never claimed verified)"
                if report.get("candidate_boundary") == "not_checked" else ""),
             "  NOTE: --strict is a DISPOSITION-COMPLETENESS gate (every bank labelled + packetized). It is NOT a "
             "behavioural-coverage claim; the uncovered rows and uncovered properties above remain open gaps."]
    for item in report["banks"]:
        lines.append("    %-22s %-24s %4d rows (%d decided; %d props covered, %d uncovered)  %s"
                     % (item["disposition"], item["adapter"], item["rows"], item["checked"],
                        len(item.get("covered_properties") or []), len(item.get("uncovered_properties") or []),
                        item["bank"]))
        if item["metrics"]:
            compact = dict(item["metrics"])
            hits = compact.pop("property_hits", None)
            if hits:
                compact["property_hits"] = dict((k, {"rows": v["rows"], "by_callable": v["by_callable"]})
                                                for k, v in sorted(hits.items()))
            lines.append("        metrics: " + json.dumps(compact, sort_keys=True, ensure_ascii=True))
    if "store_a" in report:
        lines.append("  sarf/rules (Store A) dispositions: "
                     + ", ".join("%s=%d" % (k, v) for k, v in sorted(report["store_a"]["by_disposition"].items())))
    lines.append("  sarf@2.1-@2.4: CANDIDATE, not promoted (verified against sarf/SKILL.md)")
    if report["failures"]:
        lines.append("FAIL (%d):" % len(report["failures"]))
        for f in report["failures"][:40]:
            lines.append("  - " + f)
    else:
        lines.append(TERMINAL_PASS)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# self-test — synthetic red/green + consumer-mutation proofs (no unittest dependency)
# ---------------------------------------------------------------------------
def _mutate(ctx, **kw):
    out = Consumers.real()
    for slot in Consumers.__slots__:
        setattr(out, slot, getattr(ctx, slot))
    for k, v in kw.items():
        setattr(out, k, v)
    return out


def self_test(root=_REPO):
    failures = []
    contract = load_contract(root)

    def check(name, cond):
        if not cond:
            failures.append(name)

    check("contract validates", validate_contract(contract, root) == [])
    check("candidate increments not promoted", check_candidates_not_promoted(contract, root) == [])
    sa_fails, sa_counts = check_store_a(contract, root)
    check("store A dispositions provable (%s)" % sa_fails[:2], sa_fails == [])
    check("store A covers 13 rule files", sum(sa_counts.values()) == 13)

    # POSITIVE: the real banks are green through the real consumers.
    rep = run_all(root)
    check("real banks green (%s)" % rep["failures"][:2], rep["exit_code"] == 0)
    check("object-form banks are row-counted", rep["total_rows"] >= 380)

    ctx = Consumers.real()

    def red(label, bank, mutated_ctx=None, rows=None):
        spec = bank_spec(contract, bank)
        data = rows if rows is not None else load_bank(root, spec)
        f, _m = run_adapter(spec, data, mutated_ctx or ctx, root)
        if not f:
            failures.append("mutation/negative NOT caught: " + label)

    # MUTATION: break the consumer, the claiming bank must go red.
    real_seg = ctx.segment_candidates
    red("segmenter drops the whole-token reading",
        "sarf/evals/false-clitic-split-eval.jsonl",
        _mutate(ctx, segment_candidates=lambda s: [c for c in real_seg(s) if len(c["segments"]) > 1] or []))
    real_lat = ctx.build_lattice

    def _fabricating(*a, **kw):
        lat = copy.deepcopy(real_lat(*a, **kw))
        for c in lat["candidates"]:
            c["root"] = "ك ت ب"
        return lat
    red("lattice fabricates a root", "sarf/evals/morphology-candidate-lattice.jsonl",
        _mutate(ctx, build_lattice=_fabricating))

    def _forcing(*a, **kw):
        lat = copy.deepcopy(real_lat(*a, **kw))
        lat["candidates"] = lat["candidates"][:1]
        return lat
    red("lattice forces a single parse", "sarf/evals/morphology-candidate-lattice.jsonl",
        _mutate(ctx, build_lattice=_forcing))
    red("strict key goes hamza-blind (norm() would certify)", "sarf/evals/sarf-state-machine-eval.json",
        _mutate(ctx, norm_strict=ctx.norm))
    red("key stops stripping harakat", "sarf/evals/qamus-regression-eval.json",
        _mutate(ctx, norm_strict=lambda s: s))
    red("shadda reader goes blind", "sarf/evals/qamus-regression-eval.json",
        _mutate(ctx, shadda_on=lambda tok, target: False))
    red("authoring differ drifts", "sarf/evals/corpus-authoring-eval.json",
        _mutate(ctx, classify=lambda tok, surf, roots: ("new_root", None)))
    red("tanwīn-alif guard disabled", "sarf/evals/false-clitic-split-eval.jsonl",
        _mutate(ctx, ends_tanwin_alef=lambda raw: False))
    red("letter-ownership consumer stubbed always-root",
        "sarf/evals/letter-ownership-carve-eval.jsonl",
        _mutate(ctx, letter_ownership_decide=lambda token: {
            "decision": "candidate_pending", "owners": ["root"] * len(token.get("letters") or [])}))
    # the SAME mutation applied at the EXTERNAL module (not the injected ctx slot) must also bite: this is what
    # separates "an external consumer is genuinely invoked" from "a local slot happens to be named after one".
    _cu = consumers_module("curriculum_unit_consumer")
    _real_carve = _cu.analyze_ownership_carve
    _cu.analyze_ownership_carve = lambda token: {"decision": "candidate_pending",
                                                 "owners": ["root"] * len(token.get("letters") or [])}
    try:
        red("letter-ownership EXTERNAL module stubbed (proves genuine cross-module invocation)",
            "sarf/evals/letter-ownership-carve-eval.jsonl", Consumers.real())
    finally:
        _cu.analyze_ownership_carve = _real_carve

    red("derivational-template-carve consumer stubbed always-candidate",
        "sarf/evals/derivational-template-carve-eval.jsonl",
        _mutate(ctx, derivative_decide=lambda inp, unit: {"decision": "candidate_pending",
                                                          "authority": "none_fixture_harness",
                                                          "class": "active_participle", "template": "faail"}))
    _real_derivative = _cu.analyze_derivative
    _cu.analyze_derivative = lambda inp, unit: {"decision": "candidate_pending",
                                               "authority": "none_fixture_harness",
                                               "class": "active_participle", "template": "faail"}
    try:
        red("derivational-template-carve EXTERNAL module stubbed (proves genuine cross-module invocation)",
            "sarf/evals/derivational-template-carve-eval.jsonl", Consumers.real())
    finally:
        _cu.analyze_derivative = _real_derivative
    red("plural_gate stubbed always-emit (broken-plural weak-radical cross-check loses its ground truth)",
        "sarf/evals/derivational-template-carve-eval.jsonl",
        _mutate(ctx, plural_gate=lambda *a, **kw: {"decision": "emit", "defeater": None, "detail": "stub",
                                                   "gates": []}))

    red("nominal-class-discrimination consumer stubbed always-first-survivor",
        "sarf/evals/nominal-class-discrimination-eval.jsonl",
        _mutate(ctx, discriminator_decide=lambda inp, unit: {
            "decision": "candidate_pending", "authority": "none_fixture_harness",
            "function": unit["functions"][0]["id"],
            "occurrence_binding": "none_generic_candidate: stub"}))
    _real_discriminator = _cu.analyze_discriminator_table
    _cu.analyze_discriminator_table = lambda inp, unit: {
        "decision": "candidate_pending", "authority": "none_fixture_harness",
        "function": unit["functions"][0]["id"], "occurrence_binding": "none_generic_candidate: stub"}
    try:
        red("nominal-class-discrimination EXTERNAL module stubbed (proves genuine cross-module invocation)",
            "sarf/evals/nominal-class-discrimination-eval.jsonl", Consumers.real())
    finally:
        _cu.analyze_discriminator_table = _real_discriminator

    red("weak-root-and-voice gate stack stubbed always-emit",
        "sarf/evals/weak-root-and-voice-eval.jsonl",
        _mutate(ctx, slot_gate=lambda *a, **kw: {"decision": "emit", "defeater": None, "detail": "stub",
                                                 "gates": []}))
    red("weak-root-and-voice paradigm generator stubbed empty (voice comparison loses its ground truth)",
        "sarf/evals/weak-root-and-voice-eval.jsonl",
        _mutate(ctx, generate_verb=lambda *a, **kw: []))

    real_check = ctx.check_text

    def _leaky(req):
        rec = copy.deepcopy(real_check(req))
        rec["suggestions"].append({"edit": {"op": "split"}, "gate": "two_vote_required"})
        return rec
    red("collision split escapes quarantine", "sarf/evals/largelexicon-collision-safety.jsonl",
        _mutate(ctx, check_text=_leaky))

    # NEGATIVE / ADVERSARIAL: synthetic rows that violate a bank contract must fail.
    sm = copy.deepcopy(load_bank(root, bank_spec(contract, "sarf/evals/sarf-state-machine-eval.json")))
    sm[0]["observation"]["norm_key"] = sm[0]["observation"]["surface_ar"]
    red("key that keeps the harakah", "sarf/evals/sarf-state-machine-eval.json", rows=sm)
    qr = copy.deepcopy(load_bank(root, bank_spec(contract, "sarf/evals/qamus-regression-eval.json")))
    for row in qr:
        if row.get("correct_gloss_or_pending") == "pending":
            row["expected_gate"] = "auto_safe"
            break
    red("pending downgraded below two-vote", "sarf/evals/qamus-regression-eval.json", rows=qr)
    st = copy.deepcopy(load_bank(root, bank_spec(contract, "sarf/evals/vn00-aggressive-false-closure.jsonl")))
    st[0]["expected_segments"] = []
    red("structural row with no expected segments", "sarf/evals/vn00-aggressive-false-closure.jsonl", rows=st)
    doc = copy.deepcopy(load_bank(root, bank_spec(contract, "sarf/evals/surfacemap-wbw-absent-eval.jsonl")))
    doc[0]["procedure_links"] = ["docs/this-file-does-not-exist.md#1"]
    red("documentary row with a dangling procedure link", "sarf/evals/surfacemap-wbw-absent-eval.jsonl", rows=doc)

    # round 3: the declared consumer of the byte-exact bank must actually decide the rows
    red("byte-exact declared consumer stubbed", "sarf/evals/combining-mark-byte-exact-eval.jsonl",
        _mutate(ctx, check_text=lambda req: {"raw_input": req.get("raw_input"), "suggestions": [], "gates": [],
                                             "analysis_tokens": [], "checker_summary": {"live_writes": 0}}))
    # round 3: the contract's own JSON Schema is executed
    import copy as _copy
    _unknown = _copy.deepcopy(contract)
    _unknown["banks"][0]["UNKNOWN_KEY"] = 1
    if not any("additional property" in e for e in validate_contract(_unknown, root)):
        failures.append("mutation/negative NOT caught: forbidden extra contract key")
    _dup = _copy.deepcopy(contract)
    _dup["banks"].append(_copy.deepcopy(_dup["banks"][0]))
    if not any("duplicate bank entry" in e for e in validate_contract(_dup, root)):
        failures.append("mutation/negative NOT caught: duplicate bank entry")
    _esc = _copy.deepcopy(contract)
    _esc["banks"][0]["path"] = "../outside/x.jsonl"
    if not any("escapes the repository" in e for e in validate_contract(_esc, root)):
        failures.append("mutation/negative NOT caught: contract path escaping the repository")
    # round 3: candidate/public boundary mutations
    _ids = set()
    for _rel in (contract.get("candidate_increments_not_promoted") or {}).get("registry_files", {}).values():
        with open(os.path.join(root, _rel.replace("/", os.sep)), encoding="utf-8") as _fh:
            for _line in _fh:
                if _line.strip():
                    _ids.add(json.loads(_line).get("skill_rule_id"))
    _cid = sorted(i for i in _ids if i)[0]
    for _label, _rec in (("certified state", {"rule_id": _cid, "certification_state": "certified"}),
                         ("public materialization", {"rule_id": _cid, "public_materialization_allowed": True}),
                         ("public target", {"rule_id": _cid, "public_target": "qamus/public/x.json"})):
        if not candidate_boundary_violations([("synthetic", _rec)], _ids):
            failures.append("mutation/negative NOT caught: candidate rule with a %s" % _label)

    # round 4: a covered property must be bound to the callable the contract names, and a zero-row or nested
    # boundary claim must never slip through.
    import copy as _c4
    _rel = _c4.deepcopy(contract)
    _sp = bank_spec(_rel, "sarf/evals/combining-mark-byte-exact-eval.jsonl")
    next(p for p in _sp["property_coverage"]
         if p["property"] == "checker_segments_byte_exact")["decided_by"] =         "tools/corpus_to_qamus_candidates.py:classify"
    if run_all(root, contract=_rel)["exit_code"] == 0:
        failures.append("mutation/negative NOT caught: property relabelled to a callable that never ran")
    _zero = _c4.deepcopy(contract)
    bank_spec(_zero, "sarf/evals/combining-mark-byte-exact-eval.jsonl")["property_coverage"].append(
        {"property": "fictitious_property", "applicable_rows": 0, "covered": True,
         "decided_by": "tools/fusha_text_check.py:check_text"})
    if not any("zero-row property" in e for e in validate_contract(_zero, root)):
        failures.append("mutation/negative NOT caught: fictitious zero-row property")
    _nested = {"rule_id": _cid, "child": {"grand": {"certification_state": "certified"}}}
    if not candidate_boundary_violations([("synthetic", _nested)], _ids):
        failures.append("mutation/negative NOT caught: nested candidate record claiming certification")
    _esc2 = _c4.deepcopy(contract)
    _esc2["candidate_boundary_surfaces"]["record_roots"][0] = "../outside"
    if not any("record_roots[0]" in e for e in validate_contract(_esc2, root)):
        failures.append("mutation/negative NOT caught: candidate record root escaping the repository")

    # round 5: a contract path that fails containment must never be used for I/O, and an invalid contract must
    # abort the whole run before any bank loading, Store A proving or boundary scanning.
    for _field, _mut in (
            ("registry_files", lambda c: c["candidate_increments_not_promoted"]["registry_files"].__setitem__(
                "sarf@2.1", "../outside/reg.jsonl")),
            ("bank path", lambda c: c["banks"][0].__setitem__("path", "../outside/bank.jsonl")),
            ("store A path", lambda c: c["store_a_rules"][0].__setitem__("path", "../outside/rules.json")),
            ("record_roots", lambda c: c["candidate_boundary_surfaces"]["record_roots"].__setitem__(
                0, "../outside")),
            ("projector_registry", lambda c: c["candidate_increments_not_promoted"].__setitem__(
                "projector_registry", "../outside/registry.json"))):
        _bad = _c4.deepcopy(contract)
        _mut(_bad)
        _rep = run_all(root, contract=_bad)
        if not (_rep["exit_code"] == 1 and _rep.get("aborted_before_io") and not _rep["banks"]
                and _rep.get("candidate_boundary") == "not_checked"):
            failures.append("mutation/negative NOT caught: escaping %s did not abort the run before any I/O"
                            % _field)
    try:
        load_bank(root, {"path": "../outside/bank.jsonl", "form": "jsonl", "row_key": None})
        failures.append("mutation/negative NOT caught: load_bank accepted an escaping path")
    except PathContainmentError:
        pass

    # a fabricated Store A consumer claim must be caught
    bad = copy.deepcopy(contract)
    row = next((r for r in bad["store_a_rules"] if r["disposition"] != "implemented_and_consumed"), None)
    if row is not None:
        row["disposition"] = "implemented_and_consumed"
        row["consumers"] = ["tools/normalize_ar.py"]
        if not check_store_a(bad, root)[0]:
            failures.append("mutation/negative NOT caught: fabricated Store A consumer claim")

    for f in failures:
        print("FAIL " + f)
    if failures:
        return 1
    print("ok   run_sarf_evals self-test: contract valid; %d banks / %d rows green through real consumers; "
          "13 Store A rows dispositioned; 37 mutation/negative gates all caught (incl. a stubbed declared "
          "consumer, a property relabelled to a callable that never ran, a fictitious zero-row property, "
          "schema execution, path containment with no I/O against a rejected target, nested candidate "
          "certified/public-boundary records, the weak-root-and-voice gate-stack/paradigm-generator stubs, the "
          "derivational-template-carve consumer/external-module/plural_gate stubs, and the "
          "nominal-class-discrimination consumer/external-module stubs); "
          "@2.1-@2.4 not promoted"
          % (rep["total_banks"], rep["total_rows"]))
    print(TERMINAL_SELFTEST)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the sarf eval banks against their real consumers (read-only).")
    ap.add_argument("--root", default=_REPO)
    ap.add_argument("--all", action="store_true", help="run every bank in the contract")
    ap.add_argument("--bank", help="run one bank (repo path or basename)")
    ap.add_argument("--strict", action="store_true",
                    help="DISPOSITION-COMPLETENESS gate: also fail if an uncovered bank names no existing "
                         "follow-on packet. This is not a behavioural-coverage gate.")
    ap.add_argument("--json", action="store_true", help="emit the machine-readable report on stdout")
    ap.add_argument("--report", help="write a pretty JSON report to this path (the only write this tool performs)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test(a.root)
    if not (a.all or a.bank):
        a.all = True
    rep = run_all(a.root, strict=a.strict, only=a.bank)
    text = render(rep) if not a.json else json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True)
    hits = leak_sot.scan(text)
    if hits:
        print("FAIL sarf eval runner report tripped the leak SoT: %s" % hits)
        return 1
    print(text)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
