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


def irab_rule_gate(rule_id, rules=None):
    """The effective gate for an iʿrāb-safety rule: the file's tier, strengthened by its own triggers."""
    row = _irab_row(rule_id, rules)
    if row is None:
        return "two_vote_required"          # unknown rule fails closed
    return _strongest(resolve_gate(row.get("gate")), required_gate(row.get("triggers") or []))


def irab_rule_hover(rule_id, rules=None):
    row = _irab_row(rule_id, rules)
    return (row or {}).get("hover")


# ---------------------------------------------------------------------------
# grammar-problems-gates.json
# ---------------------------------------------------------------------------
def topic_ids(rules=None):
    return sorted((rules or load_topic_gates()).get("by_topic", {}))


def topic_gate(topic, rules=None):
    """The gate as DECLARED in the topic map (unreconciled). Use effective_gate() for decisions."""
    row = (rules or load_topic_gates()).get("by_topic", {}).get(topic)
    return resolve_gate(row.get("gate")) if row else "two_vote_required"


def topic_hover(topic, rules=None):
    row = (rules or load_topic_gates()).get("by_topic", {}).get(topic)
    return (row or {}).get("hover")


def effective_gate(topic=None, triggers=(), declared=None, rules=None, irab_gates=None):
    """The gate a decision must actually carry: the strongest of topic map, SSOT triggers, and any declared tier."""
    gates = []
    if topic is not None:
        gates.append(topic_gate(topic, rules=rules))
        gates.append(required_gate(TOPIC_TRIGGERS.get(topic, ())))
    if triggers:
        gates.append(required_gate(triggers))
    if declared is not None:
        gates.append(resolve_gate(declared))
    return _strongest(*gates) if gates else "auto_safe"


# ---------------------------------------------------------------------------
# fail-closed contract check over both files
# ---------------------------------------------------------------------------
def validate_rule_files(irab_gates=None, topic_gates=None):
    """Report every way the two gate tables can be untrustworthy. Empty list == clean."""
    errs = []
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
