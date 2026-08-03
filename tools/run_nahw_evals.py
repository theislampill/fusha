#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable runner for the naḥw eval banks that had none (GAP-N4/N5).

Five banks shipped with no runner at all; `validate_nahw_skill.py` only checked that rows exist. This runner
replaces existence with a MEASURED split. Some axes are replayed through a real consumer and compared; the rest
are compared against a COMMITTED per-case binding, or honestly classified fixture-only with a packet. The
summary line reports which is which, and a structural row check is never counted as behavioural closure. Every
non-quarantined row must carry an exact binding — a missing binding is a failure, never skipped coverage.

  state-machine     nahw/evals/nahw-state-machine-eval.json
                    Each case names `evidence`, a `correct_state` and a `wrong_state`. The runner replays the
                    surface through tools/fusha_nahw_particle_rules, then ABLATES the discriminating diacritic
                    and requires the engine to fall back to pending. The bank's own scoring rule — "a correct
                    gloss reached without the evidence is a reasoning_path_wrong FAIL even when the gloss
                    happens to be right" — is enforced, not merely quoted.

  hover-context     nahw/evals/hover-context-eval.json
                    Recomputes `norm_key` with tools.normalize_ar (catching a key that matches no key function),
                    verifies `same_key_surfaces` really collide for collision-reason rows, and re-derives `safe`
                    from whether the discriminating mark actually survives in the rendered surface.

  wrong-reasoning   nahw/evals/grammar-wrong-reasoning-cases.jsonl
                    Every GP-WR row is a right-answer/wrong-path trap. Each is graded through
                    grade_structured(): the honest reason key must pass and the trap must be blocked from
                    STRUCTURED evidence, with the gate held at two_vote or stricter.

  llx-collision     nahw/evals/largelexicon-function-collision-safety.jsonl
                    A short function-like surface must route to pending_context and must NOT surface the
                    forbidden lexical row (nahw/SKILL.md §9 collision safety).

  public-boundary   nahw/evals/public-boundary-scanner-eval.jsonl
                    Replays each gloss through tools/leak_sot.LEAK_RE (the single leak SoT) and asserts the
                    word-boundary behaviour: 'hypocrites' must not trip on 'ocr', 'see OCR scan' must.

  ma-function-occurrence   nahw/evals/ma-function-occurrence-eval.jsonl
                    Occurrence-specific contextual مَا relative-vs-negation discrimination. Each row supplies a
                    typed, source-addressed CONTEXTUAL FRAME (never the conclusion label) for one exact مَا
                    occurrence; tools.fusha_nahw_particle_rules.maa_context_frame() reads the frame_table on
                    particle-context-rules.json#maa_relative_vs_negation to decide candidate-or-pending. A
                    frame the table does not bind to exactly one function stays pending with both rivals
                    preserved. Every row is also replayed at every OTHER row's exact address to prove the
                    evidence cannot be reused across occurrences. Registered in BANKS, the default `--bank all`
                    route, `--self-test` AND A2_ARTIFACT_OWNERSHIP (implemented_and_consumed).

Rows whose contract defect is NOT mechanically repairable carry `contract_status` + `packet`; the runner keeps
them visible, excludes them from the gates they cannot satisfy, and fails if such a row lacks its packet
reference. Exit 0 = every bank green.

CLI:  python tools/run_nahw_evals.py [--bank all|state-machine|hover-context|wrong-reasoning|llx-collision|
                                      public-boundary|ma-function-occurrence] [--json]
"""
import argparse
import json
import os
import re
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import fusha_nahw_context_rules as CTX  # noqa: E402
from tools import fusha_nahw_gate_rules as GATE  # noqa: E402
from tools import fusha_nahw_particle_rules as PR  # noqa: E402
from tools import normalize_ar as N  # noqa: E402
from tools.grade_grammar_reasoning import grade_structured  # noqa: E402
from tools.leak_sot import LEAK_RE  # noqa: E402

EVAL_DIR = os.path.join(_REPO, "nahw", "evals")
PACKET_DIR = os.path.join(_REPO, "qamus", "task-packets")
LOC_SURFACE_INDEX_PATH = os.path.join(_REPO, "qamus", "indexes", "quran-loc-surface", "index.jsonl")
_LOC_SURFACE_INDEX = None


def _loc_surface_index():
    """I1: the SAME occurrence-identity authority the Train B governor banks use
    (tools/validate_dependency_lattice.py verify_occurrence_identity) — loc -> surface, byte-exact after NFC.
    Surface presence in a row's OWN claim is not occurrence authority; every address-bearing row must be
    checked against this committed index, not against itself."""
    global _LOC_SURFACE_INDEX
    if _LOC_SURFACE_INDEX is None:
        _LOC_SURFACE_INDEX = {}
        if os.path.exists(LOC_SURFACE_INDEX_PATH):
            with open(LOC_SURFACE_INDEX_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if row.get("loc"):
                        _LOC_SURFACE_INDEX[row["loc"]] = row.get("surface", "")
    return _LOC_SURFACE_INDEX


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _packet_exists(packet_id):
    return os.path.exists(os.path.join(PACKET_DIR, "%s.json" % packet_id))


# ---------------------------------------------------------------------------
# quarantine authority
# ---------------------------------------------------------------------------
# A quarantine SUPPRESSES a semantic comparison, so it needs a TYPED binding, not truthiness and not a raw
# substring. The packet is parsed as its actual structured artifact and must carry a machine-readable
# QUARANTINE-BINDING block naming the bank, the status, the exact row ids, the precise uncovered property and
# the permitted disposition. A fabricated file whose text merely mentions the bank and row id has no
# packet_id, no binding block and no NOT_DEPLOYED record, so it authorises nothing.
#
# SCHEMA NOTE (truthful): qamus/schemas/task-packet.schema.json is `additionalProperties: false` at every
# level, and this lane may not widen the shared schema. The typed binding therefore lives inside the allowed
# `candidate_population.selection_rule` string under a strict grammar, parsed from the JSON artifact.
#
# A quarantine may ONLY excuse an unimplemented semantic consumer. It can never excuse a gate: gate strength
# and trigger/gate compatibility are validated for every row BEFORE any quarantine early return.
QUARANTINE_STATUSES = {
    "state_vocab_pending": "the correct axis is not expressible under the released state vocabulary",
    "pending_norm_seat_semantics": "no repository key function collides the declared family",
    "no_consumer": "no naḥw consumer decides this row",
    "consumer_branch_ambiguous": "the consumer branch covers two readings and cannot decide this row",
}
QUARANTINE_PROPERTIES = {"state_axis_pair", "key_collision_family", "typed_state_and_gloss", "consumer_branch"}
QUARANTINE_DISPOSITIONS = {"excuse_semantic_consumer"}
QUARANTINE_BINDING_RE = re.compile(
    r"QUARANTINE-BINDING\s+bank=(?P<bank>[a-z][a-z-]*);\s*status=(?P<status>[a-z_]+);\s*"
    r"rows=(?P<rows>[A-Za-z0-9_]+(?:,[A-Za-z0-9_]+)*);\s*property=(?P<property>[a-z_]+);\s*"
    r"disposition=(?P<disposition>[a-z_]+)")
_PACKET_BINDINGS = {}


def _canonical_schema_errors(packet):
    """Canonical task-packet schema errors, delegated to the repository's single validator.

    ROUND-8: a quarantine SUPPRESSES a semantic comparison, so its authorizing artifact must be a valid task
    packet, not merely a JSON file carrying a plausible QUARANTINE-BINDING sentence. The Draft 2020-12 subset
    validator lives in tools/validate_task_packets.py and is REUSED here rather than re-implemented — a second
    schema checker would inevitably diverge from the first. The import is lazy so the two modules never form
    an import cycle (validate_task_packets is stdlib-only and does not import this runner).
    """
    from tools.validate_task_packets import canonical_schema_errors  # noqa: PLC0415 (lazy: no import cycle)
    return canonical_schema_errors(packet)


def packet_quarantine_bindings(packet_id):
    """Parse a packet as a structured artifact and return its typed quarantine bindings.

    Returns (bindings, errors). `bindings` maps (bank, row_id) -> {status, property, disposition}.
    """
    if packet_id in _PACKET_BINDINGS:
        return _PACKET_BINDINGS[packet_id]
    path = os.path.join(PACKET_DIR, "%s.json" % packet_id)
    errors, bindings = [], {}
    try:
        with open(path, encoding="utf-8") as fh:
            packet = json.load(fh)
    except (OSError, ValueError) as exc:
        _PACKET_BINDINGS[packet_id] = ({}, ["packet %s is not a readable JSON artifact (%s)"
                                            % (packet_id, exc)])
        return _PACKET_BINDINGS[packet_id]
    if not isinstance(packet, dict) or packet.get("packet_id") != packet_id:
        errors.append("packet %s does not declare a matching packet_id" % packet_id)
    if (packet.get("non_deployment") or {}).get("status") != "NOT_DEPLOYED":
        errors.append("packet %s is not a NOT_DEPLOYED task packet" % packet_id)
    schema_errors = _canonical_schema_errors(packet) if isinstance(packet, dict) else ["packet is not an object"]
    if schema_errors:
        # Fail closed on the WHOLE packet: an artifact that is not a valid task packet has no authority at
        # all, however plausible its binding sentence reads.
        _PACKET_BINDINGS[packet_id] = ({}, ["packet %s is not schema-valid against %s (%s)"
                                            % (packet_id, "qamus/schemas/task-packet.schema.json",
                                               schema_errors[0])])
        return _PACKET_BINDINGS[packet_id]
    rule = ((packet.get("candidate_population") or {}).get("selection_rule") or "")
    found = list(QUARANTINE_BINDING_RE.finditer(rule))
    if not found:
        errors.append("packet %s carries no QUARANTINE-BINDING block" % packet_id)
    for match in found:
        status, prop = match.group("status"), match.group("property")
        disposition = match.group("disposition")
        if status not in QUARANTINE_STATUSES:
            errors.append("packet %s binds an invalid status %r" % (packet_id, status))
            continue
        if prop not in QUARANTINE_PROPERTIES:
            errors.append("packet %s binds an unknown uncovered property %r" % (packet_id, prop))
            continue
        if disposition not in QUARANTINE_DISPOSITIONS:
            errors.append("packet %s binds a disposition %r outside the permitted set %s"
                          % (packet_id, disposition, sorted(QUARANTINE_DISPOSITIONS)))
            continue
        for row_id in match.group("rows").split(","):
            key = (match.group("bank"), row_id)
            if key in bindings:
                errors.append("packet %s binds %s twice — an ambiguous row mention is not authority"
                              % (packet_id, key))
                continue
            bindings[key] = {"status": status, "property": prop, "disposition": disposition}
    _PACKET_BINDINGS[packet_id] = (bindings, errors)
    return _PACKET_BINDINGS[packet_id]


def _pending_row(row, errors, bank):
    """True only when an AUTHORISED, typed packet binding covers exactly this bank + row + status."""
    status = row.get("contract_status")
    if not status:
        return False
    rid = row.get("id")
    if status not in QUARANTINE_STATUSES:
        errors.append("%s:%s contract_status %r is not in the closed quarantine vocabulary %s"
                      % (bank, rid, status, sorted(QUARANTINE_STATUSES)))
        return False
    packet = row.get("packet")
    if not packet:
        errors.append("%s:%s carries contract_status=%s with no packet reference" % (bank, rid, status))
        return False
    bindings, packet_errors = packet_quarantine_bindings(packet)
    if packet_errors:
        errors.append("%s:%s packet %s is not a valid quarantine authority: %s"
                      % (bank, rid, packet, packet_errors[0]))
        return False
    binding = bindings.get((bank, rid))
    if binding is None:
        errors.append("%s:%s packet %s has no typed QUARANTINE-BINDING for this bank+row — an unrelated "
                      "packet cannot authorise a quarantine" % (bank, rid, packet))
        return False
    if binding["status"] != status:
        errors.append("%s:%s packet %s binds status %r, the row declares %r"
                      % (bank, rid, packet, binding["status"], status))
        return False
    if not row.get("quarantine_reason"):
        errors.append("%s:%s quarantined without a stated reason" % (bank, rid))
    return True


# ---------------------------------------------------------------------------
# EXACT quarantine authority (round 8)
# ---------------------------------------------------------------------------
# Cardinality is not authority. "9 state rows + 12 hover rows" stays true if a row is swapped for another, if a
# packet binds a row twice, if a stale binding survives its row's release, or if a packet reaches across into a
# bank it does not own. The committed authority is therefore pinned EXACTLY here — bank, packet, status,
# uncovered property, permitted disposition and the precise row set — and compared in BOTH directions:
#   bank -> authority : every quarantined row in the bank file is authorised by exactly this table;
#   authority -> bank : every row this table names is really quarantined, under the named packet and status;
#   packet -> authority: every QUARANTINE-BINDING a packet declares is in this table, for a bank that packet owns.
# A missing, duplicate, stale, extra or cross-bank binding is a hard failure, never skipped coverage.
QUARANTINE_AUTHORITY = (
    {"bank": "state-machine", "packet": "TP-NAHW-A2-STATE-VOCAB", "status": "state_vocab_pending",
     "property": "state_axis_pair", "disposition": "excuse_semantic_consumer",
     "rows": ("anna_how_adverbial", "halim_referent_human", "in_nafiya_negating", "kulla_vs_kalla",
              "la_nafiya_lil_jins", "lamma_not_yet", "ma_relative_vs_negation", "nima_praise_verb",
              "salihan_proper_vs_deed")},
    {"bank": "hover-context", "packet": "TP-NAHW-A2-HOVER-KEY-SEAT", "status": "pending_norm_seat_semantics",
     "property": "key_collision_family", "disposition": "excuse_semantic_consumer",
     "rows": ("an_vs_inna_norm_collapses_seat_unsafe", "umm_vs_am_unsafe")},
    {"bank": "hover-context", "packet": "TP-NAHW-A2-TYPED-STATE-CONSUMER", "status": "no_consumer",
     "property": "typed_state_and_gloss", "disposition": "excuse_semantic_consumer",
     "rows": ("almulk_vowel_only_unsafe", "bihi_pronoun_referent_unsafe", "fihi_pronoun_safe_neutral",
              "halim_attribute_referent_unsafe", "ilayna_not_root_layn_safe", "muhammad_proper_no_verb_safe",
              "qul_imperative_safe", "salihan_proper_vs_common_unsafe", "yaqdiru_contronym_unsafe")},
    {"bank": "hover-context", "packet": "TP-NAHW-A2-TYPED-STATE-CONSUMER", "status": "consumer_branch_ambiguous",
     "property": "consumer_branch", "disposition": "excuse_semantic_consumer",
     "rows": ("in_conditional_referent_free_safe",)},
)


def authority_index(table=QUARANTINE_AUTHORITY):
    """(bank, row_id) -> the single committed authority block field set. Duplicate coverage is itself an error."""
    index, duplicates = {}, []
    for block in table:
        for row_id in block["rows"]:
            key = (block["bank"], row_id)
            if key in index:
                duplicates.append(key)
                continue
            index[key] = {"packet": block["packet"], "status": block["status"],
                          "property": block["property"], "disposition": block["disposition"]}
    return index, duplicates


def quarantine_authority_errors(bank, rows, table=QUARANTINE_AUTHORITY):
    """Exact two-way equality between a bank's quarantined rows and its packets' typed bindings.

    `rows` is the bank's row list. Returns a list of error strings (empty when the sets are exactly equal).
    """
    errs = []
    index, duplicates = authority_index(table)
    for dup_bank, dup_row in duplicates:
        errs.append("%s:%s is covered by more than one committed authority block" % (dup_bank, dup_row))
    expected = {rid: meta for (bnk, rid), meta in index.items() if bnk == bank}

    seen_ids = {}
    for row in rows:
        rid = row.get("id")
        seen_ids[rid] = seen_ids.get(rid, 0) + 1
    for rid, count in sorted(seen_ids.items()):
        if count > 1:
            errs.append("%s:%s appears %d times — row ids must be unique before any set comparison"
                        % (bank, rid, count))

    actual = {row.get("id"): row for row in rows if row.get("contract_status")}
    for rid in sorted(set(actual) - set(expected)):
        errs.append("%s:%s is quarantined but no committed authority block covers it — an unauthorised "
                    "quarantine is an extra binding, not coverage" % (bank, rid))
    for rid in sorted(set(expected) - set(actual)):
        errs.append("%s:%s is named by committed quarantine authority but the bank row is not quarantined — "
                    "a stale binding must be removed when its row is released" % (bank, rid))
    for rid in sorted(set(actual) & set(expected)):
        meta, row = expected[rid], actual[rid]
        if row.get("contract_status") != meta["status"]:
            errs.append("%s:%s declares contract_status %r; committed authority binds %r"
                        % (bank, rid, row.get("contract_status"), meta["status"]))
        if row.get("packet") != meta["packet"]:
            errs.append("%s:%s names authorizing packet %r; committed authority binds %r"
                        % (bank, rid, row.get("packet"), meta["packet"]))

    # packet -> authority: every binding a referenced packet declares must be in the table, for a bank that
    # packet owns. This is what catches a stale binding left behind in the packet and a cross-bank reach.
    owned = {}
    for block in table:
        owned.setdefault(block["packet"], set()).add(block["bank"])
    for packet_id in sorted({meta["packet"] for meta in expected.values()}):
        bindings, packet_errors = packet_quarantine_bindings(packet_id)
        for message in packet_errors:
            errs.append("%s: %s" % (bank, message))
        declared = {rid for (bnk, rid) in bindings if bnk == bank}
        authorised = {rid for rid, meta in expected.items() if meta["packet"] == packet_id}
        for rid in sorted(declared - authorised):
            errs.append("%s: packet %s declares a binding for row %s that no committed authority block "
                        "covers" % (bank, packet_id, rid))
        for rid in sorted(authorised - declared):
            errs.append("%s: packet %s is the committed authority for row %s but declares no typed binding "
                        "for it" % (bank, packet_id, rid))
        for (bnk, rid) in sorted(bindings):
            if bnk not in owned.get(packet_id, set()):
                errs.append("%s: packet %s binds rows in bank %s, which it does not own — a cross-bank "
                            "binding is not authority" % (bank, packet_id, bnk))
                continue
            if bnk != bank:
                continue
            meta = expected.get(rid)
            if meta is None:
                continue
            if bindings[(bnk, rid)]["property"] != meta["property"]:
                errs.append("%s:%s packet %s binds uncovered property %r; committed authority binds %r"
                            % (bank, rid, packet_id, bindings[(bnk, rid)]["property"], meta["property"]))
            if bindings[(bnk, rid)]["disposition"] != meta["disposition"]:
                errs.append("%s:%s packet %s binds disposition %r; committed authority binds %r"
                            % (bank, rid, packet_id, bindings[(bnk, rid)]["disposition"], meta["disposition"]))
            if bindings[(bnk, rid)]["status"] != meta["status"]:
                errs.append("%s:%s packet %s binds status %r; committed authority binds %r"
                            % (bank, rid, packet_id, bindings[(bnk, rid)]["status"], meta["status"]))
    return errs


# ---------------------------------------------------------------------------
# bank 1 — nahw-state-machine-eval.json
# ---------------------------------------------------------------------------
# EXACT per-case bindings, keyed by case id. Every non-quarantined row MUST appear here: a missing binding is a
# failure, never skipped coverage. Each binding restates the row's declared axes independently of the bank file,
# so mutating EITHER state axis (or the decision, gate or route) in the JSON is caught even though no typed
# state consumer exists yet. `identity` is the one axis a real consumer decides today: the (rule, branch) that
# tools/fusha_nahw_particle_rules resolves from the content-letter diacritic.
STATE_CASE_BINDINGS = {
    "man_relative_in_sila": {
        "correct_state": "relative_pronoun", "wrong_state": "preposition",
        "expected_decision": "resolved", "gate": "auto_safe", "identity": ("man_vs_min", "A")},
    "man_interrogative_fronted": {
        "correct_state": "interrogative_pronoun", "wrong_state": "relative_pronoun",
        "expected_decision": "two_vote", "gate": "human_source_review_required",
        "identity": ("man_vs_min", "A")},
    "min_preposition_kasra": {
        "correct_state": "preposition", "wrong_state": "relative_pronoun",
        "expected_decision": "resolved", "gate": "auto_safe", "identity": ("man_vs_min", "B")},
    "wa_min_proclitic_shift": {
        "correct_state": "preposition", "wrong_state": "relative_pronoun",
        "expected_decision": "resolved", "gate": "two_vote_required", "identity": ("man_vs_min", "B")},
    "lam_negation_jazm": {
        "correct_state": "negation_jazm", "wrong_state": "interrogative_lam",
        "expected_decision": "resolved", "gate": "auto_safe", "identity": ("lam_vs_lima", "A")},
    "lima_interrogative": {
        "correct_state": "interrogative_lam", "wrong_state": "negation_jazm",
        "expected_decision": "resolved", "gate": "auto_safe", "identity": ("lam_vs_lima", "B")},
    "lam_undiacritized_pending": {
        "correct_state": "pending", "wrong_state": "negation_jazm",
        "expected_decision": "pending", "gate": "never_auto_resolve", "identity": ("lam_vs_lima", None)},
    "lamma_temporal": {
        "correct_state": "temporal_lamma", "wrong_state": "lam_relative",
        "expected_decision": "resolved", "gate": "two_vote_required", "identity": ("lima_vs_lamma", "A")},
    "lima_relative_for_that_which": {
        "correct_state": "lam_relative", "wrong_state": "temporal_lamma",
        "expected_decision": "resolved", "gate": "auto_safe", "identity": ("lima_vs_lamma", "B")},
    "an_masdariyyah_subjunctive": {
        "correct_state": "subjunctive_masdariyyah", "wrong_state": "noun_clause_anna",
        "expected_decision": "resolved", "gate": "two_vote_required", "identity": ("an_vs_inna", "A")},
    "anna_noun_clause": {
        "correct_state": "noun_clause_anna", "wrong_state": "subjunctive_masdariyyah",
        "expected_decision": "resolved", "gate": "two_vote_required", "identity": ("an_vs_inna", "A")},
    "inna_emphatic": {
        "correct_state": "emphatic_particle", "wrong_state": "conditional_particle",
        "expected_decision": "resolved", "gate": "two_vote_required", "identity": ("an_vs_inna", "B")},
    "in_conditional": {
        "correct_state": "conditional_particle", "wrong_state": "emphatic_particle",
        "expected_decision": "two_vote", "gate": "two_vote_required", "identity": ("an_vs_inna", "B")},
    "an_undiacritized_seat_collapsed": {
        "correct_state": "pending", "wrong_state": "subjunctive_masdariyyah",
        "expected_decision": "pending", "gate": "never_auto_resolve", "identity": ("an_vs_inna", None)},
    "anni_vs_anna_how": {
        "correct_state": "noun_clause_anna", "wrong_state": "interrogative_pronoun",
        "expected_decision": "resolved", "gate": "two_vote_required", "identity": ("anni_vs_anna", "A")},
}
# Committed gate for every QUARANTINED state row. A quarantine excuses only the semantic consumer, so these
# gates are pinned here and compared before the quarantine early return: lowering one is a hard failure.
QUARANTINED_STATE_GATES = {
    "in_nafiya_negating": "human_source_review_required",
    "kulla_vs_kalla": "two_vote_required",
    "salihan_proper_vs_deed": "human_source_review_required",
    "halim_referent_human": "two_vote_required",
    "lamma_not_yet": "two_vote_required",
    "la_nafiya_lil_jins": "two_vote_required",
    "ma_relative_vs_negation": "human_source_review_required",
    "anna_how_adverbial": "human_source_review_required",
    "nima_praise_verb": "two_vote_required",
}
# ---------------------------------------------------------------------------
# ROUND-10: rows whose WRITTEN SURFACE cannot determine the identity the bank claims
# ---------------------------------------------------------------------------
# Homograph selection now requires every discriminating mark the rule file names, so a surface whose marks
# contradict each other fails closed. One committed bank row is in exactly that position, and the bank
# itself is internally inconsistent about it — this lane may not edit eval fixtures, so the contradiction is
# recorded here as an EXPLICIT BLOCKER rather than papered over with a resolved identity the orthography
# does not support.
#
# The row still has every other axis compared (state, rival, expected_decision, gate) and still runs the
# evidence-ablation mutation. What it no longer does is claim the consumer picked a branch: the consumer
# must fail closed, and that is asserted.
ORTHOGRAPHY_UNDETERMINED = {
    "anni_vs_anna_how": {
        "rule_id": "anni_vs_anna",
        "blocker": ("the bank row asserts 'final yāʾ ـِي, not alif-maqṣūra ـَى' but its own surface أَنِّى "
                    "ends in alif-maqṣūra, and nahw/evals/irab-polysemy-eval.jsonl#IP-015 reads the SAME "
                    "written string as the interrogative 'how'. The two banks disagree, so the written "
                    "surface determines no member: the consumer fails closed and no identity is claimed."),
        "owner": "TP-NAHW-A2-TYPED-STATE-CONSUMER",
    },
}
# Diacritics whose removal must destroy the discriminating evidence (the ablation mutation).
_MARKS = "ًٌٍَُِّْ"


def _ablate(surface):
    """Strip the harakāt AND fold the hamza seat — i.e. reduce the token to what norm() would have kept."""
    out = "".join(ch for ch in surface if ch not in _MARKS)
    return out.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")


def run_state_machine(errors, stats):
    bank = "state-machine"
    data = _json(os.path.join(EVAL_DIR, "nahw-state-machine-eval.json"))
    vocab = set(data.get("state_vocab", {}))
    cases = data.get("cases", [])
    # `identity_compared` = a REAL consumer decision (rule + branch from the diacritic) was compared.
    # `axes_compared` = state/rival/decision/gate axes compared against the committed per-case binding.
    # `state_comparison` stays fixture_only: no typed state/function consumer computes correct_state, so the
    # axes are compared against a committed expectation, not against an engine.
    stats[bank] = {"cases": len(cases), "identity_compared": 0, "axes_compared": 0, "ablated": 0,
                   "quarantined": 0, "orthography_undetermined": 0, "state_comparison": "fixture_only",
                   "packet": "TP-NAHW-A2-TYPED-STATE-CONSUMER"}
    seen = set()
    for c in cases:
        cid = c.get("id")
        for key in ("surface", "evidence", "correct_state", "wrong_state", "expected_decision", "gate"):
            if key not in c:
                errors.append("%s:%s missing required field %s" % (bank, cid, key))
        if c.get("correct_state") not in vocab:
            errors.append("%s:%s correct_state %r is outside state_vocab" % (bank, cid, c.get("correct_state")))
        if c.get("wrong_state") not in vocab:
            errors.append("%s:%s wrong_state %r is outside state_vocab" % (bank, cid, c.get("wrong_state")))
        if not c.get("evidence"):
            errors.append("%s:%s declares no evidence (a state without evidence is not testable)" % (bank, cid))

        # GATE SAFETY FIRST. A quarantine may excuse an unimplemented semantic consumer; it may NEVER
        # excuse a weaker gate. This runs for every row, quarantined or not, before any early return.
        effective = GATE.effective_gate(triggers=c.get("trigger") or (), declared=c.get("gate"))
        if GATE.gate_rank(effective) > GATE.gate_rank(c.get("gate")):
            errors.append("%s:%s declares gate %s but its triggers require %s (quarantine never excuses a "
                          "weaker gate)" % (bank, cid, c.get("gate"), effective))
        for binding_id, expected_gate in ((cid, (STATE_CASE_BINDINGS.get(cid) or {}).get("gate")),):
            if expected_gate and c.get("gate") != expected_gate:
                errors.append("%s:%s gate %r != committed binding %r" % (bank, binding_id, c.get("gate"),
                                                                         expected_gate))
        quarantined_gate = QUARANTINED_STATE_GATES.get(cid)
        if quarantined_gate and c.get("gate") != quarantined_gate:
            errors.append("%s:%s quarantined row gate %r != committed %r — a quarantine may not lower a gate"
                          % (bank, cid, c.get("gate"), quarantined_gate))

        if _pending_row(c, errors, bank):
            stats[bank]["quarantined"] += 1
            if not (c.get("note") or c.get("quarantine_reason")):
                errors.append("%s:%s quarantined without a stated reason" % (bank, cid))
            if c.get("correct_state") == c.get("wrong_state") and not c.get("note"):
                errors.append("%s:%s quarantined with coincident axes and no note" % (bank, cid))
            continue

        if c.get("correct_state") == c.get("wrong_state"):
            errors.append("%s:%s has correct_state == wrong_state and is NOT quarantined "
                          "(the negative gate is silently disabled)" % (bank, cid))
            continue

        binding = STATE_CASE_BINDINGS.get(cid)
        if binding is None:
            errors.append("%s:%s has no committed binding; every non-quarantined row must bind its exact "
                          "state, rival, decision and gate (missing bindings are failures, not coverage)"
                          % (bank, cid))
            continue
        seen.add(cid)
        stats[bank]["axes_compared"] += 1
        for axis in ("correct_state", "wrong_state", "expected_decision", "gate"):
            if c.get(axis) != binding[axis]:
                errors.append("%s:%s %s is %r, the committed binding says %r"
                              % (bank, cid, axis, c.get(axis), binding[axis]))

        rule_id, branch = binding["identity"]
        stats[bank]["identity_compared"] += 1
        res = PR.resolve_particle_homograph(c["surface"])
        if res.get("rule_id") != rule_id:
            errors.append("%s:%s engine selected rule %r, expected %r" % (bank, cid, res.get("rule_id"), rule_id))
            continue
        undetermined = ORTHOGRAPHY_UNDETERMINED.get(cid)
        if undetermined is not None:
            # The written surface determines no member. Assert the consumer FAILS CLOSED, keep the
            # ablation mutation, and count the row as an explicit blocker — never as a resolved identity.
            if res.get("rule_id") != undetermined["rule_id"]:
                errors.append("%s:%s undetermined row changed rule family to %r"
                              % (bank, cid, res.get("rule_id")))
            if res.get("branch") is not None or res.get("decision") != "pending":
                errors.append("%s:%s the written surface determines no member, but the consumer resolved "
                              "to branch %r/%s — a contradicted mark is not evidence"
                              % (bank, cid, res.get("branch"), res.get("decision")))
            stats[bank]["orthography_undetermined"] += 1
            abl = PR.resolve_particle_homograph(_ablate(c["surface"]))
            stats[bank]["ablated"] += 1
            if abl.get("decision") != "pending" or abl.get("branch") is not None:
                errors.append("%s:%s ablated surface still resolved (%s/%s)"
                              % (bank, cid, abl.get("decision"), abl.get("branch")))
            continue
        if res.get("branch") != branch:
            errors.append("%s:%s engine landed on branch %r, expected %r (correct_state=%s)"
                          % (bank, cid, res.get("branch"), branch, c.get("correct_state")))
            continue
        if branch is None:
            if res.get("decision") != "pending":
                errors.append("%s:%s evidence is absent but the engine resolved anyway" % (bank, cid))
            if c.get("expected_decision") != "pending":
                errors.append("%s:%s expected_decision must be pending when the evidence is absent" % (bank, cid))
            continue

        # MUTATION — ablate the discriminating mark: a right conclusion reached without the evidence is
        # reasoning_path_wrong, so the engine MUST fall back to pending.
        abl = PR.resolve_particle_homograph(_ablate(c["surface"]))
        stats[bank]["ablated"] += 1
        if abl.get("decision") != "pending":
            errors.append("%s:%s evidence-ablation did NOT force pending (got %s/%s) — a state reached "
                          "without its evidence is reasoning_path_wrong"
                          % (bank, cid, abl.get("decision"), abl.get("branch")))
        if abl.get("branch") is not None:
            errors.append("%s:%s ablated surface still resolved to branch %s" % (bank, cid, abl.get("branch")))

    stale = sorted(set(STATE_CASE_BINDINGS) - seen)
    if stale:
        errors.append("%s: committed bindings with no matching non-quarantined row: %s" % (bank, stale))
    # ROUND-8: exact two-way equality between the quarantined row set and its packets' typed bindings.
    errors.extend(quarantine_authority_errors(bank, cases))
    return bank


# ---------------------------------------------------------------------------
# bank 2 — hover-context-eval.json
# ---------------------------------------------------------------------------
KEY_FNS = {"norm": N.norm, "norm_strict": N.norm_strict, "bare": N.bare}
COLLISION_REASONS = {"homograph_haraka", "seat_collapsed"}
# EXACT per-case bindings for every non-quarantined hover row. `decision` is the consumer verdict that must be
# reproduced; for an unsafe row the consumer's `pending_reason` must equal the bank's EXACTLY.
# The GLOSS axis is deliberately absent: the particle rules' branch gloss is a disjunction over both members of
# the branch (e.g. "indeed / verily (إِنَّ) — or — if (إِنْ)"), so no consumer decides a row's final gloss today.
# Rows whose gloss or referent nothing decides are quarantined with contract_status=no_consumer.
# `reading` and `gloss` are the consumer's EXACT outputs for that branch, restated here so a scrambled or
# no-op consumer is caught. `safe` and `gate` are the bank verdicts the consumer decision must reproduce.
HOVER_CASE_BINDINGS = {
    "min_preposition_safe": {
        "gloss_if_safe": "from / among",
        "rule_id": "man_vs_min", "branch": "B", "decision": "resolved", "pending_reason": None,
        "safe": True, "gate": "auto_safe", "key_fn": "norm",
        "reading": "مِنْ — preposition", "gloss": "from / among / of"},
    "man_relative_safe_with_sila": {
        "gloss_if_safe": "who / whoever",
        "rule_id": "man_vs_min", "branch": "A", "decision": "resolved", "pending_reason": None,
        "safe": True, "gate": "auto_safe", "key_fn": "norm",
        "reading": "مَن — relative / interrogative pronoun", "gloss": "who / whoever / he who"},
    "man_bare_unsafe": {
        "gloss_if_safe": None,
        "rule_id": "man_vs_min", "branch": None, "decision": "pending",
        "pending_reason": "homograph_haraka", "safe": False, "gate": "never_auto_resolve",
        "key_fn": "norm", "reading": None, "gloss": None},
    "lam_negation_safe": {
        "gloss_if_safe": "did not",
        "rule_id": "lam_vs_lima", "branch": "A", "decision": "resolved", "pending_reason": None,
        "safe": True, "gate": "auto_safe", "key_fn": "norm",
        "reading": "لَمْ — negative particle + jazm", "gloss": "did not / has not"},
    "lam_bare_unsafe": {
        "gloss_if_safe": None,
        "rule_id": "lam_vs_lima", "branch": None, "decision": "pending",
        "pending_reason": "homograph_haraka", "safe": False, "gate": "never_auto_resolve",
        "key_fn": "norm", "reading": None, "gloss": None},
    "lamma_temporal_safe": {
        "gloss_if_safe": "when / after",
        "rule_id": "lima_vs_lamma", "branch": "A", "decision": "resolved", "pending_reason": None,
        "safe": True, "gate": "two_vote_required", "key_fn": "norm",
        "reading": "لَمَّا — temporal / 'not yet'", "gloss": "when / after / not yet"},
    "lima_relative_unsafe_when_bare_shadda": {
        "gloss_if_safe": None,
        "rule_id": "lima_vs_lamma", "branch": None, "decision": "pending",
        "pending_reason": "homograph_haraka", "safe": False, "gate": "never_auto_resolve",
        "key_fn": "norm", "reading": None, "gloss": None},
    "inna_strict_seat_safe": {
        "gloss_if_safe": "indeed / verily",
        "rule_id": "an_vs_inna", "branch": "B", "decision": "resolved", "pending_reason": None,
        "safe": True, "gate": "two_vote_required", "key_fn": "norm_strict",
        "reading": "إِنَّ (emphatic) or إِنْ (conditional/negative)",
        "gloss": "indeed / verily (إِنَّ) — or — if (إِنْ)"},
}
# HONEST LIMIT. The hover lookup that chooses norm vs norm_strict lives in the rendering layer, not in this
# repository, so a row's `key_fn` is a FIXTURE selection and is NOT evidence of production key selection. The
# runner reports the property as unconsumed instead of asserting it; closing it belongs to
# TP-NAHW-A2-HOVER-KEY-SEAT.
PRODUCTION_KEY_SELECTION = "no_production_authority"
# ROUND-7: a quarantined hover row could be weakened from human_source_review_required to two_vote_required
# because quarantine returned before any gate comparison. Every quarantined row's committed gate is pinned
# here and compared BEFORE the early return, exactly as the state-machine bank already does. A quarantine may
# excuse an unimplemented semantic consumer; it may never excuse a weaker gate.
QUARANTINED_HOVER_GATES = {
    "an_vs_inna_norm_collapses_seat_unsafe": "never_auto_resolve",
    "umm_vs_am_unsafe": "never_auto_resolve",
    "bihi_pronoun_referent_unsafe": "two_vote_required",
    "fihi_pronoun_safe_neutral": "auto_safe",
    "halim_attribute_referent_unsafe": "two_vote_required",
    "salihan_proper_vs_common_unsafe": "human_source_review_required",
    "muhammad_proper_no_verb_safe": "auto_safe",
    "almulk_vowel_only_unsafe": "never_auto_resolve",
    "yaqdiru_contronym_unsafe": "two_vote_required",
    "qul_imperative_safe": "auto_safe",
    "ilayna_not_root_layn_safe": "auto_safe",
    "in_conditional_referent_free_safe": "two_vote_required",
}


def run_hover_context(errors, stats):
    bank = "hover-context"
    data = _json(os.path.join(EVAL_DIR, "hover-context-eval.json"))
    cases = data.get("cases", [])
    stats[bank] = {"cases": len(cases), "bound": 0, "safe": 0, "unsafe": 0, "quarantined": 0, "mutated": 0,
                   "consumer_gloss_axis": "compared_against_consumer",
                   "bank_gloss_if_safe_axis": "committed_binding_only_no_production_owner",
                   "key_selection": PRODUCTION_KEY_SELECTION,
                   "packet": "TP-NAHW-A2-TYPED-STATE-CONSUMER"}
    seen = set()
    for c in cases:
        cid, surface = c.get("id"), c.get("surface")
        for key in ("surface", "norm_key", "safe", "reason", "gate"):
            if key not in c:
                errors.append("%s:%s missing required field %s" % (bank, cid, key))
        key_fn_name = c.get("key_fn", "norm")
        key_fn = KEY_FNS.get(key_fn_name)
        if key_fn is None:
            errors.append("%s:%s key_fn %r is not a normalize_ar key function" % (bank, cid, key_fn_name))
            continue
        if key_fn(surface) != c.get("norm_key"):
            errors.append("%s:%s norm_key %r != %s(surface)=%r"
                          % (bank, cid, c.get("norm_key"), key_fn_name, key_fn(surface)))

        # GATE SAFETY FIRST — before any quarantine early return
        _pinned = QUARANTINED_HOVER_GATES.get(cid)
        if _pinned and c.get("gate") != _pinned:
            errors.append("%s:%s quarantined row gate %r != committed %r — a quarantine may not lower a gate"
                          % (bank, cid, c.get("gate"), _pinned))
        quarantined = _pending_row(c, errors, bank)
        if quarantined:
            stats[bank]["quarantined"] += 1
            if not c.get("quarantine_reason"):
                errors.append("%s:%s quarantined without a stated reason" % (bank, cid))

        # a collision-reason row must actually collide with at least one listed sibling
        if c.get("pending_reason") in COLLISION_REASONS and not quarantined:
            same = [s for s in (c.get("same_key_surfaces") or []) if key_fn(s) == c.get("norm_key")]
            if not same:
                errors.append("%s:%s pending_reason=%s but no same_key_surfaces actually share the key %r "
                              "under %s" % (bank, cid, c.get("pending_reason"), c.get("norm_key"), key_fn_name))

        # gate consistency: an unsafe row may never sit at auto_safe; a safe row may never sit at never_auto
        if c.get("safe") is True:
            stats[bank]["safe"] += 1
            if GATE.gate_rank(c.get("gate")) >= GATE.gate_rank("never_auto_resolve"):
                errors.append("%s:%s safe=true with gate %s" % (bank, cid, c.get("gate")))
        else:
            stats[bank]["unsafe"] += 1
            if c.get("gate") == "auto_safe":
                errors.append("%s:%s safe=false but gate auto_safe" % (bank, cid))
            if not c.get("pending_reason"):
                errors.append("%s:%s safe=false with no pending_reason" % (bank, cid))

        if quarantined:
            continue

        binding = HOVER_CASE_BINDINGS.get(cid)
        if binding is None:
            errors.append("%s:%s is not quarantined and has no committed consumer binding — an unconsumed "
                          "row may not be counted as coverage" % (bank, cid))
            continue
        seen.add(cid)
        stats[bank]["bound"] += 1
        res = PR.resolve_particle_homograph(surface)
        if res.get("rule_id") != binding["rule_id"] or res.get("branch") != binding["branch"]:
            errors.append("%s:%s consumer returned %s/%s, the committed binding says %s/%s"
                          % (bank, cid, res.get("rule_id"), res.get("branch"),
                             binding["rule_id"], binding["branch"]))
            continue
        # EXACT consumer-output comparison: decision, pending reason, reading and gloss
        for axis in ("decision", "pending_reason", "reading", "gloss"):
            if res.get(axis) != binding[axis]:
                errors.append("%s:%s consumer %s is %r, the committed binding says %r"
                              % (bank, cid, axis, res.get(axis), binding[axis]))
        # EXACT bank-verdict comparison: safe, gate, declared key function, pending reason
        for axis in ("safe", "gate", "pending_reason"):
            if c.get(axis) != binding[axis]:
                errors.append("%s:%s bank %s is %r, the committed binding says %r"
                              % (bank, cid, axis, c.get(axis), binding[axis]))
        # `gloss_if_safe` is the bank's teaching gloss. No production consumer owns it (the particle rules'
        # branch gloss is a disjunction over both branch members), so it is compared against the COMMITTED
        # binding and reported as bank-owned, never counted as a consumer decision.
        if c.get("gloss_if_safe") != binding["gloss_if_safe"]:
            errors.append("%s:%s bank gloss_if_safe %r != committed %r"
                          % (bank, cid, c.get("gloss_if_safe"), binding["gloss_if_safe"]))
        if c.get("key_fn", "norm") != binding["key_fn"]:
            errors.append("%s:%s bank key_fn %r != committed %r"
                          % (bank, cid, c.get("key_fn", "norm"), binding["key_fn"]))
        engine_safe = res.get("decision") == "resolved"
        if engine_safe != bool(c.get("safe")):
            errors.append("%s:%s bank says safe=%s but the consumer says %s (%s)"
                          % (bank, cid, c.get("safe"), res.get("decision"),
                             ";".join(res.get("evidence") or [])))
        # ADVERSARIAL: strip the marks from a safe row — it must become unsafe
        if engine_safe:
            stats[bank]["mutated"] += 1
            if PR.resolve_particle_homograph(_ablate(surface)).get("decision") != "pending":
                errors.append("%s:%s stripping the harakāt did not make the hover unsafe" % (bank, cid))

    stale = sorted(set(HOVER_CASE_BINDINGS) - seen)
    if stale:
        errors.append("%s: committed bindings with no matching non-quarantined row: %s" % (bank, stale))
    # ROUND-8: exact two-way equality between the quarantined row set and its packets' typed bindings.
    errors.extend(quarantine_authority_errors(bank, cases))
    # a neutered consumer must not silently collapse the bound or mutation counts to zero
    expected_mutations = sum(1 for b in HOVER_CASE_BINDINGS.values() if b["decision"] == "resolved")
    if stats[bank]["bound"] != len(HOVER_CASE_BINDINGS):
        errors.append("%s: bound %d of %d committed bindings"
                      % (bank, stats[bank]["bound"], len(HOVER_CASE_BINDINGS)))
    if stats[bank]["mutated"] != expected_mutations:
        errors.append("%s: ran %d harakat-stripping mutations, expected %d - a consumer that stops "
                      "resolving silently removes the adversarial axis"
                      % (bank, stats[bank]["mutated"], expected_mutations))
    return bank


# ---------------------------------------------------------------------------
# bank 3 — grammar-wrong-reasoning-cases.jsonl
# ---------------------------------------------------------------------------
def run_wrong_reasoning(errors, stats):
    bank = "wrong-reasoning"
    rows = _jsonl(os.path.join(EVAL_DIR, "grammar-wrong-reasoning-cases.jsonl"))
    stats[bank] = {"cases": len(rows), "classification": "fixture_only",
                   "packet": "TP-NAHW-A2-TYPED-WR-BANK", "routing_checked": 0}
    for r in rows:
        rid = r.get("id")
        for key in ("expected_answer", "expected_reasoning", "wrong_reasoning_trap", "why_trap_wrong",
                    "required_gate", "hover_safety", "topic"):
            if key not in r:
                errors.append("%s:%s missing required field %s" % (bank, rid, key))
        if GATE.gate_rank(r.get("required_gate")) < GATE.gate_rank("two_vote_required"):
            errors.append("%s:%s a right-answer/wrong-reason trap may never sit below two_vote (got %s)"
                          % (bank, rid, r.get("required_gate")))
        if r.get("hover_safety") == "auto_safe":
            errors.append("%s:%s hover_safety auto_safe on a wrong-reasoning trap" % (bank, rid))

        # FIXTURE-ONLY, and honestly so. Every GP-WR row states its expected_reasoning and its trap as ENGLISH
        # PROSE. There is no registered reason key, no per-row case/mood, and no structured governor evidence in
        # the bank, so grade_structured() cannot be given anything real to grade. Inventing "<id>:expected" and
        # "<id>:trap" keys would only prove that two invented strings differ — it would NOT evaluate the
        # grammatical reasoning, and it would fabricate keys outside the governed registry.
        # Behavioural closure for this bank therefore requires a TYPED bank: see TP-NAHW-A2-TYPED-WR-BANK.
        # What IS checked here is the routing contract the prose rows can actually support.
        if r.get("reason_key") or r.get("expected_reason_keys"):
            errors.append("%s:%s carries reason-key fields; the bank is typed and this runner must be "
                          "upgraded from fixture-only to structured grading" % (bank, rid))
        for key in ("expected_reasoning", "wrong_reasoning_trap", "why_trap_wrong"):
            if not str(r.get(key) or "").strip():
                errors.append("%s:%s %s is empty (a trap row with no stated path is untestable)"
                              % (bank, rid, key))
        if str(r.get("expected_reasoning")) == str(r.get("wrong_reasoning_trap")):
            errors.append("%s:%s the honest path and the trap are the same text" % (bank, rid))
        stats[bank]["routing_checked"] += 1
    return bank


# ---------------------------------------------------------------------------
# bank 4 — largelexicon-function-collision-safety.jsonl
# ---------------------------------------------------------------------------
# EXACT typed binding per LLX row: the consumer must return this forbidden-reading id, and the bank's own
# `forbidden` text must be the committed one. Unrelated non-empty text is not a forbidden reading.
LLX_CASE_BINDINGS = {
    "nahw-llx-function-001": {"forbidden_reading_id": "llx-forbidden-man-manna-verb",
                              "forbidden": "verb مَنَّ as arbitrary-text hover"},
    "nahw-llx-function-002": {"forbidden_reading_id": "llx-forbidden-illa-illan-noun",
                              "forbidden": "noun إِلًّا as arbitrary-text hover"},
    "nahw-llx-function-003": {"forbidden_reading_id": "llx-forbidden-wama-default-ma",
                              "forbidden": "single default mā gloss without function"},
}


def _norm_text(value):
    """NFC + whitespace/case-insensitive comparison of a short expectation string."""
    return unicodedata.normalize("NFC", " ".join((value or "").split())).casefold()


def run_llx_collision(errors, stats):
    bank = "llx-collision"
    rows = _jsonl(os.path.join(EVAL_DIR, "largelexicon-function-collision-safety.jsonl"))
    stats[bank] = {"cases": len(rows), "routed": 0}
    from tools.fusha_context_parser import collision_status  # local import: parser owns the routing table
    for r in rows:
        rid, surface = r.get("id"), r.get("surface")
        for key in ("surface", "expected_gate", "forbidden"):
            if key not in r:
                errors.append("%s:%s missing required field %s" % (bank, rid, key))
        status = collision_status(surface)
        if status is None:
            errors.append("%s:%s surface %r is not routed by the collision table — a bare function-like "
                          "surface must never fall through to the first lexicon row" % (bank, rid, surface))
            continue
        stats[bank]["routed"] += 1
        if status.get("status") != r.get("expected_gate"):
            errors.append("%s:%s routed as %r, bank expects %r"
                          % (bank, rid, status.get("status"), r.get("expected_gate")))
        if status.get("gate") == "auto_safe":
            errors.append("%s:%s a lexical-collision surface may never be auto_safe" % (bank, rid))
        binding = LLX_CASE_BINDINGS.get(rid)
        if binding is None:
            errors.append("%s:%s has no committed forbidden-reading binding" % (bank, rid))
            continue
        # the consumer must return the EXACT typed forbidden-reading id, and the bank's own `forbidden`
        # value must be the committed one — unrelated non-empty text is not a forbidden reading
        if status.get("forbidden_reading_id") != binding["forbidden_reading_id"]:
            errors.append("%s:%s consumer forbidden_reading_id %r != committed %r"
                          % (bank, rid, status.get("forbidden_reading_id"), binding["forbidden_reading_id"]))
        if _norm_text(r.get("forbidden")) != _norm_text(binding["forbidden"]):
            errors.append("%s:%s bank forbidden %r != committed %r"
                          % (bank, rid, r.get("forbidden"), binding["forbidden"]))
        if not status.get("forbidden_reading"):
            errors.append("%s:%s routed without naming the forbidden lexical row" % (bank, rid))
        # the particle consumer must independently refuse to resolve the bare surface
        res = PR.resolve_particle_homograph(surface)
        if res.get("rule_id") and res.get("decision") != "pending":
            errors.append("%s:%s the bare surface resolved to %s instead of pending"
                          % (bank, rid, res.get("branch")))
    return bank


# ---------------------------------------------------------------------------
# bank 5 — public-boundary-scanner-eval.jsonl
# ---------------------------------------------------------------------------
def run_public_boundary(errors, stats):
    bank = "public-boundary"
    rows = _jsonl(os.path.join(EVAL_DIR, "public-boundary-scanner-eval.jsonl"))
    stats[bank] = {"cases": len(rows), "leaks": 0, "clean": 0}
    for r in rows:
        rid, gloss = r.get("id"), r.get("gloss")
        for key in ("gloss", "should_leak", "why"):
            if key not in r:
                errors.append("%s:%s missing required field %s" % (bank, rid, key))
        hit = bool(LEAK_RE.search(gloss or ""))
        if hit != bool(r.get("should_leak")):
            errors.append("%s:%s leak scanner returned %s, bank expects %s (gloss=%r)"
                          % (bank, rid, hit, r.get("should_leak"), gloss))
        stats[bank]["leaks" if r.get("should_leak") else "clean"] += 1
    if stats[bank]["clean"] < 1 or stats[bank]["leaks"] < 1:
        errors.append("%s: the bank must carry both positive and negative rows" % bank)
    return bank


# ---------------------------------------------------------------------------
# bank 6 — particle-function + irab-polysemy (were existence-checked only)
# ---------------------------------------------------------------------------
# Particles in these banks whose reading is fixed by a content-letter diacritic: the consumer must agree with the
# bank, so a mis-edited row or a broken discriminator shows up here rather than in production.
PF_HOMOGRAPH_BRANCH = {"مَن": ("man_vs_min", "A"), "مِن": ("man_vs_min", "B"),
                       "لِمَ": ("lam_vs_lima", "B"), "كَلَّا": ("kull_vs_kalla", "B")}


def run_function_polysemy(errors, stats):
    bank = "function-polysemy"
    pf = _jsonl(os.path.join(EVAL_DIR, "particle-function-eval.jsonl"))
    ip = _jsonl(os.path.join(EVAL_DIR, "irab-polysemy-eval.jsonl"))
    stats[bank] = {"pf_cases": len(pf), "ip_cases": len(ip), "pf_homograph_checked": 0,
                   "ip_host_only_checked": 0}
    seen = set()
    for r in pf:
        rid = r.get("id")
        if rid in seen:
            errors.append("%s:%s duplicate particle-function id" % (bank, rid))
        seen.add(rid)
        for key in ("particle", "functions", "context_function", "loc", "gloss", "why"):
            if key not in r:
                errors.append("%s:%s missing required field %s" % (bank, rid, key))
                break
        else:
            # `functions` is the particle's FUNCTION INVENTORY and `context_function` is the finer per-occurrence
            # label; they are separate vocabularies, so membership is deliberately not asserted here. What is
            # asserted is that a row cannot be function-blind: an inventory and a committed contextual label
            # must both be present and non-empty.
            if not (isinstance(r["functions"], list) and r["functions"]
                    and all(isinstance(f, str) and f.strip() for f in r["functions"])):
                errors.append("%s:%s functions must be a non-empty list of labels" % (bank, rid))
            if not (isinstance(r["context_function"], str) and r["context_function"].strip()):
                errors.append("%s:%s context_function is empty (the row commits to no function)" % (bank, rid))
            if not str(r["loc"]).count(":") >= 2:
                errors.append("%s:%s loc %r is not a surah:ayah:word address" % (bank, rid, r["loc"]))
            binding = PF_HOMOGRAPH_BRANCH.get(r["particle"])
            if binding:
                stats[bank]["pf_homograph_checked"] += 1
                res = PR.resolve_particle_homograph(r["particle"])
                if (res.get("rule_id"), res.get("branch")) != binding:
                    errors.append("%s:%s the consumer reads %s as %s/%s, the bank assumes %s/%s"
                                  % (bank, rid, r["particle"], res.get("rule_id"), res.get("branch"),
                                     binding[0], binding[1]))
    seen = set()
    for r in ip:
        rid = r.get("id")
        if rid in seen:
            errors.append("%s:%s duplicate irab-polysemy id" % (bank, rid))
        seen.add(rid)
        for key in ("surface", "loc", "reading", "gloss", "why"):
            if key not in r:
                errors.append("%s:%s missing required field %s" % (bank, rid, key))
        if not r.get("reject_host_only_gloss"):
            continue
        stats[bank]["ip_host_only_checked"] += 1
        # BEHAVIOUR: the executable half of "a bare label is not pedagogically complete". A row that rejects a
        # host-only gloss and DECLARES a composition must name the host's role and give every declared
        # proclitic/suffix contribution a non-empty label — an empty label is a bare slot, which is exactly the
        # defect the flag exists to forbid. Rows with no composition block are structural-only by design
        # (validate_nahw_skill.py requires the block on IP-026…IP-034), so presence is not asserted here.
        comp = r.get("composition")
        if isinstance(comp, dict):
            if not comp.get("host_role"):
                errors.append("%s:%s declares a composition but no host_role" % (bank, rid))
            for field in ("proclitic_functions", "suffix_roles"):
                vals = comp.get(field) or []
                if not isinstance(vals, list):
                    errors.append("%s:%s composition.%s must be a list" % (bank, rid, field))
                    continue
                for val in vals:
                    if not (isinstance(val, str) and val.strip()):
                        errors.append("%s:%s composition.%s carries an empty label (a bare slot)"
                                      % (bank, rid, field))
        att = r.get("attachment")
        if isinstance(att, dict) and not att.get("relation"):
            errors.append("%s:%s declares an attachment with no relation" % (bank, rid))
        # a preposition/pronoun row must not leak a referent decision it has not made
        for v in CTX.polyseme_quarantine_violations(r["surface"], r.get("gloss")):
            errors.append("%s:%s gloss carries the quarantined sibling sense %r"
                          % (bank, rid, v.get("blocked_sense")))
    return bank


# ---------------------------------------------------------------------------
# bank 7 — ma-function-occurrence-eval.jsonl (occurrence-specific contextual مَا discrimination)
# ---------------------------------------------------------------------------
# Every row supplies a typed, source-addressed CONTEXTUAL FRAME observation (never the conclusion label) for
# one exact مَا occurrence, and PR.maa_context_frame() — reading nahw/rules/particle-context-rules.json's own
# `maa_relative_vs_negation#frame_table` — says which function(s) that frame licenses. A unique frame must
# reach `candidate` with exactly the bank's expected function; a non-unique frame must stay `pending` with
# BOTH declared rival functions still unresolved. Every row's evidence is additionally replayed at every OTHER
# row's exact address to prove it cannot be reused across occurrences (same surface never authorises reuse).
#
# REGISTRATION: this bank is invoked (registered in BANKS, exercised by `--bank ma-function-occurrence`,
# the DEFAULT `--bank all` / no-flag route, and `--self-test`) and IS registered in A2_ARTIFACT_OWNERSHIP below,
# with a matching entry in tools/fusha_eval_coverage.py's own independent allowlist. Every row is decided by
# the real consumer (PR.maa_context_frame): each row's function candidate — or its exact pending/rival/defect
# outcome for a non-unique frame — is checked, so `decided` counts every row, never only the candidate-reaching
# ones.
#
# M5 (author-circularity disclosure): each row's `frame` and the rule's own `frame_table` binding it to a
# function are authored by the SAME party, from no mechanical extraction source (see
# nahw/rules/particle-context-rules.json#maa_relative_vs_negation's own `author_circularity_disclosure`); this
# bank therefore cannot fail unless the frame_table or this consumer itself breaks — it is candidate-only,
# fixture-producer trust, exactly like every other typed observation this file mints.
def run_ma_function_occurrence(errors, stats):
    bank = "ma-function-occurrence"
    rows = _jsonl(os.path.join(EVAL_DIR, "ma-function-occurrence-eval.jsonl"))
    stats[bank] = {"cases": len(rows), "candidates": 0, "pending": 0, "decided": 0, "consumer_calls": 0,
                   "replay_checks": 0}
    addresses = [r["source_address"] for r in rows if r.get("source_address")]
    maa_rule = next((r for r in (PR.load_particle_rules().get("rules") or [])
                     if r.get("id") == "maa_relative_vs_negation"), None) or {}
    for r in rows:
        rid = r.get("id")
        for key in ("surface", "quran_loc", "word", "source_address", "frame", "expected_decision"):
            if key not in r:
                errors.append("%s:%s missing required field %s" % (bank, rid, key))
        surface, at = r.get("surface"), r.get("source_address")
        # I1: verify this row's own claimed (loc, surface) against the committed loc-surface index — the same
        # authority contract the governor banks use — BEFORE trusting the row's evidence at all. A missing or
        # mismatching index entry is a failure regardless of what the frame/decision fields say: surface
        # presence in the row's own data was never occurrence authority (e.g. a mutated row claiming word 34 of
        # 5:116 is مَا, when the index shows فِى, must fail here even though the frame vocabulary is well-formed).
        loc = "%s:%s" % (r.get("quran_loc"), r.get("word")) if r.get("quran_loc") is not None \
            and r.get("word") is not None else None
        indexed_surface = _loc_surface_index().get(loc) if loc else None
        if indexed_surface is None:
            errors.append("%s:%s loc %r has no qamus/indexes/quran-loc-surface/index.jsonl entry" % (bank, rid, loc))
        elif unicodedata.normalize("NFC", indexed_surface) != unicodedata.normalize("NFC", surface or ""):
            errors.append("%s:%s surface %r does not match qamus/indexes/quran-loc-surface/index.jsonl at "
                          "loc=%r (%r)" % (bank, rid, surface, loc, indexed_surface))
        evidence = PR.mint_fixture_observation(r.get("frame"), source_address=at, quran_loc=r.get("quran_loc"),
                                               word=r.get("word"), surface=surface, target_kind="token",
                                               target_value="maa_relative_vs_negation")
        res = PR.maa_context_frame(surface, evidence=evidence, at=at)
        stats[bank]["consumer_calls"] += 1
        stats[bank]["decided"] += 1
        if res.get("decision") == "candidate":
            stats[bank]["candidates"] += 1
        elif res.get("decision") == "pending":
            stats[bank]["pending"] += 1
        if res.get("decision") != r.get("expected_decision"):
            errors.append("%s:%s decision %r != expected %r"
                          % (bank, rid, res.get("decision"), r.get("expected_decision")))
        if res.get("decision") == "resolved":
            errors.append("%s:%s reached resolved from typed evidence; candidate posture only" % (bank, rid))
        if r.get("expected_decision") == "candidate":
            if res.get("function_candidate") != r.get("expected_function"):
                errors.append("%s:%s function_candidate %r != expected %r"
                              % (bank, rid, res.get("function_candidate"), r.get("expected_function")))
        else:
            expected_rivals = set(r.get("expected_rivals") or [])
            got_unresolved = {x["role"] for x in (res.get("unresolved_alternatives") or [])
                              if x.get("decision_status") == "unresolved"}
            if expected_rivals:
                if not expected_rivals <= got_unresolved:
                    errors.append("%s:%s expected rivals %s not all preserved unresolved (got %s)"
                                  % (bank, rid, sorted(expected_rivals), sorted(got_unresolved)))
                # INDEPENDENT of the eval row's own (possibly incomplete) expected_rivals fixture: cross-check
                # against the RULE ARTIFACT's own declared functions for the observed frame, so an under-listed
                # fixture can never mask a production regression that silently drops a real rival.
                observed_frame = res.get("observed_frame")
                frame_row = next((fr for fr in (maa_rule.get("frame_table") or [])
                                  if fr.get("frame") == observed_frame), None)
                artifact_rivals = set((frame_row or {}).get("functions")
                                      or ([frame_row["function"]] if (frame_row or {}).get("function") else []))
                if not artifact_rivals <= got_unresolved:
                    errors.append("%s:%s rule-artifact rivals %s not all preserved unresolved (got %s) — an "
                                  "eval-row fixture must never mask a dropped real rival"
                                  % (bank, rid, sorted(artifact_rivals), sorted(got_unresolved)))
                if any(x.get("selected") for x in (res.get("unresolved_alternatives") or [])):
                    errors.append("%s:%s an ambiguous frame must select no winner" % (bank, rid))
            if r.get("expected_defect") and res.get("evidence_defect") != r.get("expected_defect"):
                errors.append("%s:%s evidence_defect %r != expected %r"
                              % (bank, rid, res.get("evidence_defect"), r.get("expected_defect")))
        # exact-address binding: an otherwise-VALID row's evidence replayed at every OTHER row's address must
        # fail closed. Gated on the row's OWN evidence having actually validated at its own address
        # (res["evidence_id"] is not None) — NOT on the mere presence of `expected_defect`, since a row can
        # carry valid evidence that is only ambiguous at the FRAME level (e.g. ma-occ-005, expected_defect=
        # maa_category_unresolved) and such a row's replay-rejection is still real and must still be checked.
        # An already-invalid row (e.g. off-vocabulary — evidence_id is None) is skipped: its own address
        # already fails for a different, unrelated reason, so the replay defect would never surface there.
        if res.get("evidence_id") is not None:
            for other in addresses:
                if other == at:
                    continue
                replay = PR.maa_context_frame(surface, evidence=evidence, at=other)
                stats[bank]["replay_checks"] += 1
                if replay.get("evidence_defect") != "occurrence_not_current":
                    errors.append("%s:%s evidence replayed at %s was not rejected as occurrence_not_current "
                                  "(%r)" % (bank, rid, other, replay.get("evidence_defect")))
    if stats[bank]["candidates"] < 1 or stats[bank]["pending"] < 1:
        errors.append("%s: the bank must carry both a candidate-reaching row and a pending row" % bank)
    return bank


BANKS = {
    "function-polysemy": run_function_polysemy,
    "state-machine": run_state_machine,
    "hover-context": run_hover_context,
    "wrong-reasoning": run_wrong_reasoning,
    "llx-collision": run_llx_collision,
    "public-boundary": run_public_boundary,
    "ma-function-occurrence": run_ma_function_occurrence,
}


# ---------------------------------------------------------------------------
# contract-shaped runner result (serialized integration with tools/fusha_eval_coverage.py)
# ---------------------------------------------------------------------------
# A1's coverage reporter takes execution evidence ONLY from an invoked runner result. Round-7 defect: this
# runner USED to report `consumer_calls` by copying its own `decided` counter, so a no-op bank that merely
# incremented a stat was credited with behavioural coverage without ever calling the consumer. Counts are now
# taken by COUNTING PROXIES installed around the exact allow-listed callable at its real call site — the same
# pattern as tools/run_sarf_evals.run_adapter — so a bank that never calls its consumer reports zero.
NAHW_RUNNER_SCHEMA = "qamus.nahw_eval_runner_contract.v1"

# EXACT artifact -> (execution group, allowed consumer, declared disposition). This is the ownership map: a
# result item for any other artifact, or naming any other consumer or disposition, is rejected by the reporter.
# `decided_stat` names the stat holding the rows the consumer actually decided; `quarantine_stat` the rows a
# typed quarantine excused. Seven execution GROUPS decide eight physical artifacts (function-polysemy covers
# two).
A2_ARTIFACT_OWNERSHIP = {
    "nahw/evals/public-boundary-scanner-eval.jsonl": {
        "group": "public-boundary", "consumer": "tools/leak_sot.py:LEAK_RE.search",
        "disposition": "implemented_and_consumed", "decided_stat": ("leaks", "clean"),
        "quarantine_stat": None},
    "nahw/evals/largelexicon-function-collision-safety.jsonl": {
        "group": "llx-collision", "consumer": "tools/fusha_context_parser.py:collision_status",
        "disposition": "implemented_and_consumed", "decided_stat": ("routed",), "quarantine_stat": None},
    "nahw/evals/hover-context-eval.json": {
        # 8 of 20 rows are decided by the consumer; 12 are quarantined under typed packet authority, and the
        # bank's own gloss_if_safe has no production owner. NOT implemented_and_consumed.
        "group": "hover-context",
        "consumer": "tools/fusha_nahw_particle_rules.py:resolve_particle_homograph",
        "disposition": "fixture_only", "decided_stat": ("bound",), "quarantine_stat": "quarantined"},
    "nahw/evals/nahw-state-machine-eval.json": {
        # identity is a real consumer decision; the typed grammatical STATE has no consumer at all.
        "group": "state-machine",
        "consumer": "tools/fusha_nahw_particle_rules.py:resolve_particle_homograph",
        "disposition": "fixture_only", "decided_stat": ("identity_compared",),
        "quarantine_stat": "quarantined"},
    "nahw/evals/grammar-wrong-reasoning-cases.jsonl": {
        "group": "wrong-reasoning", "consumer": None, "disposition": "fixture_only",
        "decided_stat": (), "quarantine_stat": None},
    "nahw/evals/particle-function-eval.jsonl": {
        "group": "function-polysemy",
        "consumer": "tools/fusha_nahw_particle_rules.py:resolve_particle_homograph",
        "disposition": "fixture_only", "decided_stat": ("pf_homograph_checked",), "quarantine_stat": None},
    "nahw/evals/irab-polysemy-eval.jsonl": {
        "group": "function-polysemy", "consumer": None, "disposition": "fixture_only",
        "decided_stat": (), "quarantine_stat": None},
    "nahw/evals/ma-function-occurrence-eval.jsonl": {
        # every row's exact outcome (candidate function, or the exact pending/rival/defect for a non-unique or
        # invalid-evidence frame) is decided and checked against the real consumer; no row is quarantined and
        # no axis of this bank's own claim is unowned.
        "group": "ma-function-occurrence",
        "consumer": "tools/fusha_nahw_particle_rules.py:maa_context_frame",
        "disposition": "implemented_and_consumed", "decided_stat": ("decided",), "quarantine_stat": None},
}
# Axes this lane does NOT own. Reported, never counted as coverage.
UNOWNED_AXES = {
    "hover-context": {"bank_gloss_if_safe": "committed_binding_only_no_production_owner",
                      "key_selection": "no_production_authority"},
    "state-machine": {"typed_state": "no_typed_state_consumer"},
    "wrong-reasoning": {"structured_reason": "prose_only_bank"},
}
# consumer id -> (module attribute holder, attribute name, kind). `regex_search` wraps a compiled pattern whose
# .search is the consumed callable; `function` wraps the callable itself.
CONSUMER_SLOTS = {
    "tools/leak_sot.py:LEAK_RE.search": (__name__, "LEAK_RE", "regex_search"),
    "tools/fusha_context_parser.py:collision_status": ("tools.fusha_context_parser", "collision_status",
                                                       "function"),
    "tools/fusha_nahw_particle_rules.py:resolve_particle_homograph": ("tools.fusha_nahw_particle_rules",
                                                                      "resolve_particle_homograph",
                                                                      "function"),
    "tools/fusha_nahw_particle_rules.py:maa_context_frame": ("tools.fusha_nahw_particle_rules",
                                                             "maa_context_frame", "function"),
}


class _CountingRegex(object):
    """Proxy around a compiled pattern that counts real .search() calls and delegates everything else."""

    def __init__(self, real, bump):
        self._real, self._bump = real, bump

    def search(self, *a, **kw):
        self._bump()
        return self._real.search(*a, **kw)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _install_counters(calls):
    """Install counting proxies at the exact allow-listed call sites. Returns a restore callable."""
    import importlib
    restore = []
    for consumer, (holder, attr, kind) in CONSUMER_SLOTS.items():
        mod = sys.modules[holder] if holder in sys.modules else importlib.import_module(holder)
        real = getattr(mod, attr)
        restore.append((mod, attr, real))
        calls.setdefault(consumer, 0)

        def _bump(_c=consumer):
            calls[_c] += 1

        if kind == "regex_search":
            setattr(mod, attr, _CountingRegex(real, _bump))
        else:
            def _proxy(_real=real, _b=_bump):
                def inner(*a, **kw):
                    _b()
                    return _real(*a, **kw)
                return inner
            setattr(mod, attr, _proxy())

    def _restore():
        for mod, attr, real in restore:
            setattr(mod, attr, real)
    return _restore


def _bank_rows(root, rel):
    """Row count for an eval artifact, matching the coverage reporter's own counting rules.

    Raises ValueError with a contract-shaped message on malformed/trailing JSON so the runner fails closed
    instead of silently reporting a zero denominator.
    """
    path = os.path.join(root, rel.replace("/", os.sep))
    if rel.endswith(".jsonl"):
        rows = 0
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except ValueError as exc:
                    raise ValueError("%s line %d is not valid JSON (%s)" % (rel, lineno, exc))
                rows += 1
        return rows
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise ValueError("%s is not a single valid JSON document (%s)" % (rel, exc))
    if not isinstance(obj, dict):
        raise ValueError("%s is not a JSON object" % rel)
    for key in ("cases", "assertions"):
        if isinstance(obj.get(key), list):
            return len(obj[key])
    raise ValueError("%s carries no cases[]/assertions[] rows" % rel)


def run_all(root=_REPO):
    """Run every execution group and return the contract-shaped result the coverage reporter invokes.

    `consumer_calls` are OBSERVED at the allow-listed callable, never copied from a decided counter.
    Fail-closed: a root other than this runner's own repository yields exit_code 1 with a stated failure.
    """
    result = {"schema": NAHW_RUNNER_SCHEMA, "banks": [], "failures": [], "exit_code": 0, "total_rows": 0,
              "behavioral_rows": 0, "quarantined_rows": 0, "unowned_axes": UNOWNED_AXES,
              "ownership": {k: v["consumer"] for k, v in A2_ARTIFACT_OWNERSHIP.items()}}
    if os.path.abspath(root) != os.path.abspath(_REPO):
        result["failures"].append("run_all is bound to its own repository root; refusing root %r" % root)
        result["exit_code"] = 1
        return result
    errors = []
    stats, per_group_calls = {}, {}
    for name in sorted(BANKS):
        calls = {}
        restore = _install_counters(calls)
        try:
            BANKS[name](errors, stats)
        finally:
            restore()
        per_group_calls[name] = calls
    by_group = {}
    for err in errors:
        by_group.setdefault(err.split(":", 1)[0], []).append(err)
    for rel in sorted(A2_ARTIFACT_OWNERSHIP):
        own = A2_ARTIFACT_OWNERSHIP[rel]
        group = own["group"]
        gstats = stats.get(group) or {}
        try:
            rows = _bank_rows(root, rel)
        except (OSError, ValueError) as exc:
            result["failures"].append("bank %s is unreadable (%s)" % (rel, exc))
            result["exit_code"] = 1
            continue
        decided = sum(int(gstats.get(k) or 0) for k in own["decided_stat"])
        quarantined = int(gstats.get(own["quarantine_stat"]) or 0) if own["quarantine_stat"] else 0
        observed = (per_group_calls.get(group) or {}).get(own["consumer"], 0) if own["consumer"] else 0
        result["banks"].append({
            "bank": rel, "rows": rows, "checked": decided,
            "failures": list(by_group.get(group) or []),
            "disposition": own["disposition"],
            "behavioral_consumer": own["consumer"],
            "metrics": {"consumer_calls": ({own["consumer"]: observed} if own["consumer"] else {}),
                        "quarantined": quarantined, "runner_bank": group,
                        "unowned_axes": UNOWNED_AXES.get(group, {})},
        })
        result["total_rows"] += rows
        result["quarantined_rows"] += quarantined
        if (own["disposition"] == "implemented_and_consumed" and rows
                and decided == rows and observed >= rows and not quarantined
                and not UNOWNED_AXES.get(group)):
            result["behavioral_rows"] += rows
    result["failures"].extend(errors)
    if errors:
        result["exit_code"] = 1
    # An explicit success flag the reporter can require, derived here rather than inferred there.
    result["ok"] = (result["exit_code"] == 0 and not result["failures"])
    return result


def _self_test():
    """Run every bank and assert the contract-shaped result is internally consistent. Exit 1 on violation."""
    errors, stats = [], {}
    for name in sorted(BANKS):
        BANKS[name](errors, stats)
    result = run_all(_REPO)
    if not result.get("ok"):
        errors.extend("run_all: %s" % f for f in (result.get("failures") or ["result not ok"]))
    banks = [b["bank"] for b in result.get("banks") or []]
    if sorted(banks) != sorted(A2_ARTIFACT_OWNERSHIP):
        errors.append("run_all covered %s, expected the %d committed artifacts"
                      % (sorted(banks), len(A2_ARTIFACT_OWNERSHIP)))
    if len(set(banks)) != len(banks):
        errors.append("run_all returned duplicate artifact items")
    for item in result.get("banks") or []:
        own = A2_ARTIFACT_OWNERSHIP[item["bank"]]
        if item["disposition"] != own["disposition"]:
            errors.append("%s disposition %r != committed %r"
                          % (item["bank"], item["disposition"], own["disposition"]))
        if item["behavioral_consumer"] != own["consumer"]:
            errors.append("%s consumer %r != committed %r"
                          % (item["bank"], item["behavioral_consumer"], own["consumer"]))
        if item["rows"] != _bank_rows(_REPO, item["bank"]):
            errors.append("%s row denominator %r is not the independently counted row count"
                          % (item["bank"], item["rows"]))
    if result.get("total_rows") != sum(b["rows"] for b in result.get("banks") or []):
        errors.append("run_all total_rows is not the sum of its item rows")
    if errors:
        print("FAIL — %d naḥw eval self-test violation(s):" % len(errors))
        for e in errors[:20]:
            print("  -", e)
        return 1
    print("PASS — naḥw eval self-test: %d rows across %d execution groups over %d artifacts; "
          "dispositions, consumer ownership and row denominators all match the committed map; "
          "behavioural credit %d rows, quarantined %d rows"
          % (result["total_rows"], len(BANKS), len(A2_ARTIFACT_OWNERSHIP),
             result["behavioral_rows"], result["quarantined_rows"]))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bank", default="all", choices=["all"] + sorted(BANKS))
    ap.add_argument("--json", action="store_true", help="emit the stats object instead of prose")
    # ROUND-13: `--self-test` is the repository-wide convention for "run your own gates and exit non-zero on
    # any violation". This runner already does exactly that over every bank, so the flag runs the full set
    # (never a subset) and additionally asserts the contract-shaped run_all() result is internally sound.
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="run every bank plus the contract-result invariants; exit 1 on any violation")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    names = sorted(BANKS) if a.bank == "all" else [a.bank]
    errors, stats = [], {}
    for name in names:
        BANKS[name](errors, stats)
    if a.json:
        # exactly ONE JSON document on stdout, no trailing prose, correct exit code
        print(json.dumps({"stats": stats, "errors": errors, "ok": not errors},
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 1 if errors else 0
    else:
        for name in names:
            print("  %-16s %s" % (name, json.dumps(stats.get(name, {}), sort_keys=True)))
    if errors:
        print("FAIL — %d naḥw eval violation(s):" % len(errors))
        for e in errors:
            print("  -", e)
        return 1
    total = sum(v for s in stats.values() for k, v in s.items() if k == "cases" or k.endswith("_cases"))
    # ROUND-7: this aggregate is NOT "real consumer decisions" — it mixes distinct denominators (identity
    # comparisons, ablation mutations, harakat-stripping mutations, routing events, leak-scanner decisions,
    # homograph cross-checks, occurrence-frame decisions and occurrence-replay probes) and it omits the hover
    # base comparisons. It is reported under a precise name and its exact formula is asserted in
    # tools/check_regressions.py. Row-level coverage lives in run_all().
    consumer_events = sum(v for s in stats.values() for k, v in s.items()
                          if k in ("identity_compared", "ablated", "mutated", "routed", "leaks", "clean",
                                   "pf_homograph_checked", "decided", "replay_checks"))
    fixture_only = sorted(n for n in names if stats.get(n, {}).get("classification") == "fixture_only"
                          or stats.get(n, {}).get("state_comparison") == "fixture_only")
    quarantined = sum(s.get("quarantined", 0) for s in stats.values())
    print("PASS — %d naḥw eval row(s) across %d bank(s). "
          "Consumer-invocation events (mixed denominators: identity+ablation+mutation+routing+scanner+"
          "homograph+occurrence-decision+occurrence-replay): %d. Quarantined rows (excluded from any closure "
          "claim): %d. Banks whose semantic comparison is FIXTURE-ONLY pending a typed consumer/bank: %s. "
          "Structural row checks are NOT behavioural closure."
          % (total, len(names), consumer_events, quarantined, ", ".join(fixture_only) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
