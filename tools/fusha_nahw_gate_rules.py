#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consumer for the GATE domain of nahw/rules/ — iʿrāb safety tiers and the GrammarProblems topic map.

  nahw/rules/irab-safety-gates.json     -> irab_rule_gate() / irab_rule_triggers()
  nahw/rules/grammar-problems-gates.json-> topic_gate() / topic_hover()

Both files are gate TABLES; the gate ladder itself is owned by nahw/evals/grammar-decision-gates.json (the SSOT
whose four-home parity tools/test_gate_ssot.py already mutation-proves). This consumer therefore never invents a
tier — it reads the table and then reconciles it with the SSOT **monotonically upward**:

    effective_gate = max(gate declared in the rules file, gate the SSOT triggers require)

Strengthening only. A rules-file row can make a decision stricter than the SSOT, never laxer, so a stale or
under-gated table can never open a hole — and `validate_rule_files()` reports the divergence instead of hiding it.
`proper_vs_common` is the live example: the topic map says two_vote, the SSOT trigger `proper_vs_common_noun` says
human_source_review_required, and the effective gate is the SSOT's.

CLI:  python tools/fusha_nahw_gate_rules.py --status | --self-test
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools.fusha_check import resolve_gate  # noqa: E402
from tools.validate_linguistic_decisions import GRAMMAR_GATE_TRIGGERS, _GATE_RANK, required_gate  # noqa: E402

RULES_DIR = os.path.join(_REPO, "nahw", "rules")
IRAB_GATES_PATH = os.path.join(RULES_DIR, "irab-safety-gates.json")
TOPIC_GATES_PATH = os.path.join(RULES_DIR, "grammar-problems-gates.json")

SSOT_TRIGGERS = {t for tiers in GRAMMAR_GATE_TRIGGERS.values() for t in tiers}
HOVER_VOCAB = {"never_auto", "pending_if_reason_uncertain", "safe_if_cited"}

# Closed topic -> SSOT-trigger map. A topic with no SSOT trigger contributes nothing extra (the file's own gate
# stands); it is never silently promoted or demoted.
TOPIC_TRIGGERS = {
    "irab": ("irab",),
    "case_mood": ("case_or_mood",),
    "nafy_lil_jins": ("nafy_lil_jins",),
    "istithna": ("istithna",),
    "proper_vs_common": ("proper_vs_common_noun",),
    "idafa": ("idafa_ambiguous",),
    "conditional": (),
    "negation": (),
    "jar_majrur": (),
    "particles": (),
    "mubtada_khabar": (),
    "verb_measure": (),
}

_CACHE = {}


def _load(path):
    if path not in _CACHE:
        with open(path, encoding="utf-8") as fh:
            _CACHE[path] = json.load(fh)
    return _CACHE[path]


def load_irab_safety_gates():
    return _load(IRAB_GATES_PATH)


def load_topic_gates():
    return _load(TOPIC_GATES_PATH)


def gate_rank(gate):
    return _GATE_RANK.get(resolve_gate(gate), 1)


def _strongest(*gates):
    best = "auto_safe"
    for g in gates:
        if g and gate_rank(g) > gate_rank(best):
            best = resolve_gate(g)
    return best


# ---------------------------------------------------------------------------
# irab-safety-gates.json
# ---------------------------------------------------------------------------
def irab_rule_ids(rules=None):
    return [r["id"] for r in (rules or load_irab_safety_gates()).get("rules", [])]


def _irab_row(rule_id, rules=None):
    for r in (rules or load_irab_safety_gates()).get("rules", []):
        if r.get("id") == rule_id:
            return r
    return None


def irab_rule_triggers(rule_id, rules=None):
    row = _irab_row(rule_id, rules)
    return tuple(row.get("triggers") or ()) if row else ()


IRAB_GATE_FLOOR = "two_vote_required"


# ROUND-15: `tools/fusha_check.resolve_gate` and the topic tables are dict lookups, so an unhashable raw
# value (a list, dict or set) raised TypeError straight out of this module's public API — an unreadable gate
# input is not a safe one, and it must never surface as an exception either. Every public entry point below
# validates its raw inputs FIRST and answers the strict tier. `tools/fusha_check.resolve_gate` itself is
# unchanged (it is outside this lane); this module simply never hands it a value it cannot look up, and
# re-exports the guarded form under the same name so `GATE.resolve_gate` is safe for callers too.
_UPSTREAM_RESOLVE_GATE = resolve_gate
STRICT_GATE = "never_auto_resolve"


def gate_value_defect(value):
    """None when `value` is something a gate table can be keyed by at all (a non-empty string, or None)."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return "gate_value_not_a_string"
    return None


def resolve_gate(declared):
    """Guarded resolve_gate: an unreadable value is the STRICT tier — never an exception, never auto_safe.

    `resolve_gate(None)` keeps its documented fail-closed default (two_vote_required) from upstream.
    """
    if gate_value_defect(declared) is not None:
        return STRICT_GATE
    return _UPSTREAM_RESOLVE_GATE(declared)


def irab_rule_gate(rule_id, rules=None):
    """The effective gate for an iʿrāb-safety rule: the file's tier, strengthened by its own triggers."""
    if gate_value_defect(rule_id) is not None:
        return STRICT_GATE                  # ROUND-15: an unreadable rule id is not a safe one
    row = _irab_row(rule_id, rules)
    if row is None:
        return "two_vote_required"          # unknown rule fails closed
    # ROUND-13: required_gate() answers auto_safe for a trigger list it cannot read, so a malformed trigger
    # in the table collapsed the whole ladder. Reconcile through the checked path instead.
    # ROUND-14: every iʿrāb decision carries a two_vote_required FLOOR. A row that declares auto_safe and
    # lists no triggers used to answer auto_safe — an iʿrāb call with no stated risk is not a safe one.
    # Additional risk may strengthen this; nothing may weaken it.
    if declared_gate_defect(row.get("gate")) is not None:
        return "never_auto_resolve"
    return _strongest(IRAB_GATE_FLOOR, resolve_gate(row.get("gate")),
                      reconcile_required_gate(row.get("gate"), list(row.get("triggers") or [])))


def irab_rule_hover(rule_id, rules=None):
    row = _irab_row(rule_id, rules)
    return (row or {}).get("hover")


# ---------------------------------------------------------------------------
# grammar-problems-gates.json
# ---------------------------------------------------------------------------
def topic_ids(rules=None):
    return sorted((rules or load_topic_gates()).get("by_topic", {}))


def topic_gate(topic, rules=None):
    """ROUND-15: a malformed raw topic (list/dict/set) is the STRICT tier, never an exception."""
    if gate_value_defect(topic) is not None:
        return STRICT_GATE
    return _topic_gate_checked(topic, rules=rules)


def _topic_gate_checked(topic, rules=None):
    """The gate as DECLARED in the topic map (unreconciled). Use effective_gate() for decisions."""
    row = (rules or load_topic_gates()).get("by_topic", {}).get(topic)
    return resolve_gate(row.get("gate")) if row else "two_vote_required"


def topic_hover(topic, rules=None):
    row = (rules or load_topic_gates()).get("by_topic", {}).get(topic)
    return (row or {}).get("hover")


def effective_gate(topic=None, triggers=(), declared=None, rules=None, irab_gates=None):
    """The gate a decision must actually carry: the strongest of topic map, SSOT triggers and declared tier.

    ROUND-13: this public entry point used the fail-OPEN path, so `triggers=["not_a_trigger"]` with a
    declared `auto_safe` answered auto_safe — an unreadable risk statement was treated as an absence of
    risk. It now delegates to reconcile_required_gate(), which holds on a malformed, non-list, duplicated
    or unknown trigger set. A caller-declared tier can still only STRENGTHEN.
    """
    # ROUND-14: validate the RAW inputs before any lookup or coercion. `declared=[]` used to raise
    # TypeError out of this public API, and a non-list `triggers` fell through to auto_safe.
    # ROUND-15: the raw TOPIC is validated too — it reaches a dict lookup in both branches below.
    if gate_value_defect(topic) is not None:
        return STRICT_GATE
    if declared_gate_defect(declared) is not None:
        return "never_auto_resolve"
    # an EMPTY non-list (e.g. {}) is falsy, so it must be validated on its type, not on its truthiness
    if triggers is not None and not isinstance(triggers, (list, tuple)):
        return "never_auto_resolve"
    if triggers and trigger_set_defect(list(triggers)) is not None:
        return "never_auto_resolve"
    gates = []
    if topic is not None:
        gates.append(topic_gate(topic, rules=rules))
        gates.append(required_gate(TOPIC_TRIGGERS.get(topic, ())))
    if triggers:
        gates.append(reconcile_required_gate(declared, list(triggers)))
    elif declared is not None:
        gates.append(resolve_gate(declared))
    return _strongest(*gates) if gates else "auto_safe"


# ---------------------------------------------------------------------------
# ROUND-10: reconcile the required gate UPWARD from the SSOT, fail closed on bad triggers
# ---------------------------------------------------------------------------
# effective_gate() takes the strongest of what it is given, but required_gate() answers "auto_safe" for a
# trigger list it does not recognise, so a caller could declare auto_safe and pass a misspelled, duplicated
# or non-list trigger set and have the whole ladder collapse to auto_safe. A trigger set that cannot be
# validated is not an absence of risk; it is an unreadable risk statement.
#
# GRAMMAR-AFFECTING axes may never end up at auto_safe: the SSOT tiers already put irab, case_or_mood,
# reasoning_path_wrong, referent_sensitive_gloss, jar_majrur_ambiguous, idafa_ambiguous, nafy_lil_jins and
# istithna above it, and this function refuses to return a gate below the SSOT answer for them.
GRAMMAR_AFFECTING_TRIGGERS = frozenset({
    "irab", "case_or_mood", "advanced_nahw", "istithna", "nafy_lil_jins", "idafa_ambiguous",
    "jar_majrur_ambiguous", "referent_sensitive_gloss", "multi_sense_root", "reasoning_path_wrong",
    "ambiguous_grammar", "proper_vs_common_noun", "qac_pos_conflict",
})


def trigger_set_defect(triggers):
    """None when `triggers` is a well-formed, non-duplicated, fully recognised SSOT trigger list."""
    if triggers is None:
        return "trigger_list_absent"
    if isinstance(triggers, (str, bytes)) or not isinstance(triggers, (list, tuple)):
        return "trigger_list_not_a_list"
    items = list(triggers)
    if any(not isinstance(t, str) or not t.strip() for t in items):
        return "trigger_not_a_string"
    if len(set(items)) != len(items):
        return "trigger_list_has_duplicates"
    unknown = sorted(t for t in items if t not in SSOT_TRIGGERS)
    if unknown:
        return "trigger_not_in_ssot:%s" % ",".join(unknown)
    return None


def declared_gate_defect(declared):
    """None when `declared` is a value the gate ladder can even look up.

    ROUND-14: `resolve_gate()` hashes its argument, so a list or dict raised
    `TypeError: unhashable type` out of a public API. A gate value that cannot be read is not a weak gate;
    it is an unreadable one.
    """
    if declared is None:
        return None
    if not isinstance(declared, str) or not declared.strip():
        return "declared_gate_not_a_string"
    return None


def reconcile_required_gate(declared, triggers, topic=None, rules=None):
    """The gate that must actually be carried — never weaker than the SSOT answer, fail-closed on bad input.

    A malformed, non-list, duplicated or unknown trigger set yields `never_auto_resolve`: the risk statement
    could not be read, so nothing may be auto-resolved on it. A caller-declared tier can only STRENGTHEN.
    """
    # ROUND-15: the raw topic reaches a dict lookup here too.
    if declared_gate_defect(declared) is not None or gate_value_defect(topic) is not None:
        return "never_auto_resolve"
    defect = trigger_set_defect(triggers)
    if defect is not None:
        return "never_auto_resolve"
    ssot = required_gate(triggers)
    declared_gate = resolve_gate(declared) if declared is not None else "auto_safe"
    gates = [ssot, declared_gate]
    if topic is not None:
        gates.append(topic_gate(topic, rules=rules))
        gates.append(required_gate(TOPIC_TRIGGERS.get(topic, ())))
    strongest = _strongest(*gates)
    if set(triggers) & GRAMMAR_AFFECTING_TRIGGERS and gate_rank(strongest) < gate_rank("two_vote_required"):
        # defence in depth: a grammar-affecting axis is never an auto_safe decision, whatever the tables say
        return "two_vote_required"
    return strongest


# ---------------------------------------------------------------------------
# fail-closed contract check over both files
# ---------------------------------------------------------------------------
# The exact committed rule-id set of nahw/rules/irab-safety-gates.json, read from the file at authoring time
# and pinned here so a dropped or duplicated row is a failure rather than a silently missing gate.
EXPECTED_IRAB_RULE_IDS = frozenset({
    "irab_assignment", "idafa_jar_majrur_ambiguous", "istithna", "mood_tense_flip",
    "nafy_lil_jins", "referent_sensitive",
})


def irab_rule_id_defects(rules=None):
    """The irab-safety table must carry EXACTLY its committed unique rule-id set — no missing, no duplicate.

    ROUND-10: callers read the table by id, so a dropped row silently removes a gate and a duplicated row
    makes which gate applies depend on iteration order. Both are failures, not omissions.
    """
    rows = (rules or load_irab_safety_gates()).get("rules") or []
    ids = [r.get("id") for r in rows]
    errs = []
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errs.append("irab-safety-gates: duplicate rule ids %s" % dupes)
    missing = sorted(EXPECTED_IRAB_RULE_IDS - set(ids))
    extra = sorted(set(i for i in ids if i) - EXPECTED_IRAB_RULE_IDS)
    if missing:
        errs.append("irab-safety-gates: missing committed rule ids %s" % missing)
    if extra:
        errs.append("irab-safety-gates: uncommitted rule ids %s" % extra)
    return errs


def validate_rule_files(irab_gates=None, topic_gates=None):
    """Report every way the two gate tables can be untrustworthy. Empty list == clean."""
    errs = list(irab_rule_id_defects(irab_gates))
    ig = irab_gates or load_irab_safety_gates()
    for row in ig.get("rules", []):
        rid = row.get("id", "?")
        declared = resolve_gate(row.get("gate"))
        trigs = tuple(row.get("triggers") or ())
        unknown = [t for t in trigs if t not in SSOT_TRIGGERS]
        if unknown:
            errs.append("irab-safety-gates#%s: trigger(s) %s not in the gates SSOT" % (rid, unknown))
        if declared == "auto_safe":
            errs.append("irab-safety-gates#%s: an iʿrāb-affecting rule may never declare auto_safe" % rid)
        need = required_gate(trigs)
        if gate_rank(declared) < gate_rank(need):
            errs.append("irab-safety-gates#%s: declared %s is weaker than its triggers require (%s)"
                        % (rid, declared, need))
        if row.get("hover") and row["hover"] not in HOVER_VOCAB:
            errs.append("irab-safety-gates#%s: hover %r outside the vocabulary %s"
                        % (rid, row["hover"], sorted(HOVER_VOCAB)))

    tg = topic_gates or load_topic_gates()
    by_topic = tg.get("by_topic", {})
    for topic in sorted(by_topic):
        if topic not in TOPIC_TRIGGERS:
            errs.append("grammar-problems-gates#%s: topic is not bound to the SSOT trigger map "
                        "(add it to TOPIC_TRIGGERS or remove it)" % topic)
            continue
        hover = by_topic[topic].get("hover")
        if hover and hover not in HOVER_VOCAB:
            errs.append("grammar-problems-gates#%s: hover %r outside the vocabulary %s"
                        % (topic, hover, sorted(HOVER_VOCAB)))
        # an auto_safe topic may not carry a never_auto hover, and vice versa
        if topic_gate(topic, rules=tg) == "auto_safe" and hover == "never_auto":
            errs.append("grammar-problems-gates#%s: gate auto_safe contradicts hover never_auto" % topic)
    for topic in TOPIC_TRIGGERS:
        if topic not in by_topic:
            errs.append("grammar-problems-gates: topic %r is bound in TOPIC_TRIGGERS but absent from the "
                        "file" % topic)
    return errs


def gate_divergences(rules=None):
    """Topics whose declared tier is weaker than the SSOT — reported, never silently applied downward."""
    out = []
    for topic in topic_ids(rules):
        declared = topic_gate(topic, rules=rules)
        eff = effective_gate(topic=topic, rules=rules)
        if gate_rank(eff) > gate_rank(declared):
            out.append({"topic": topic, "declared": declared, "effective": eff,
                        "ssot_triggers": list(TOPIC_TRIGGERS.get(topic, ()))})
    return out


# Authoritative FILE-level consumption status for this helper's rule files. `consumed` means a
# PRODUCTION record-validation path reads the file and a distinct on/off probe proves it (see
# tools/validate_nahw_skill.py RULES_CONSUMPTION, which asserts exact agreement with this map).
# A helper being able to READ a file is not consumption.
FILE_CONSUMPTION = {
    "nahw/rules/irab-safety-gates.json": "fixture_gated",
    "nahw/rules/grammar-problems-gates.json": "fixture_gated",
}


def _file_status(path, executable=True):
    """A rule row can never claim more than its file's authoritative status."""
    status = FILE_CONSUMPTION.get(path, "fixture_gated")
    return status if executable else "documentary"


def rule_status():
    return {
        "nahw/rules/irab-safety-gates.json": {
            rid: _file_status("nahw/rules/irab-safety-gates.json") for rid in irab_rule_ids()},
        "nahw/rules/grammar-problems-gates.json": {
            **{t: _file_status("nahw/rules/grammar-problems-gates.json") for t in topic_ids()},
            "by_difficulty (prose `when`)": "documentary",
        },
    }


def _self_test():
    bad = []

    def eq(name, got, want):
        if got != want:
            bad.append("%s: got %r want %r" % (name, got, want))

    eq("contract clean", validate_rule_files(), [])
    for rid in irab_rule_ids():
        if irab_rule_gate(rid) == "auto_safe":
            bad.append("%s resolved to auto_safe" % rid)
    eq("irab topic", effective_gate(topic="irab"), "two_vote_required")
    eq("proper_vs_common lifted", effective_gate(topic="proper_vs_common"), "human_source_review_required")
    eq("never_auto terminal", effective_gate(triggers=["norm_only_match", "irab"]), "never_auto_resolve")
    eq("jar_majrur declared", topic_gate("jar_majrur"), "auto_safe")
    eq("jar_majrur_ambiguous trigger", effective_gate(triggers=["jar_majrur_ambiguous"]), "two_vote_required")
    div = gate_divergences()
    eq("one known divergence", [d["topic"] for d in div], ["proper_vs_common"])
    mutated = json.loads(json.dumps(load_irab_safety_gates()))
    mutated["rules"][0]["gate"] = "auto_safe"
    eq("mutation caught", bool(validate_rule_files(irab_gates=mutated)), True)
    if bad:
        print("FAIL — fusha_nahw_gate_rules self-test:")
        for b in bad:
            print("  -", b)
        return 1
    print("PASS — gate consumer self-test (6 iʿrāb rules + 12 topics consumed; SSOT reconciliation is "
          "monotonically upward; %d declared divergence reported)" % len(div))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--divergences", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.status:
        print(json.dumps(rule_status(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if a.divergences:
        print(json.dumps(gate_divergences(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return _self_test()


if __name__ == "__main__":
    sys.exit(main())
