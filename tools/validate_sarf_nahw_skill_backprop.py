#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_sarf_nahw_skill_backprop — prove the sarf/nahw SKILLs stay aligned with the P1/P2/P2b engine.

The sarf/nahw skills were back-propagated from the grammar-checker engine; this gate fails if a skill drifts away from the
engine's contracts (forces an unvoweled parse, drops the right-answer-wrong-reason rule, resolves PP-attachment without evidence,
claims CEFR certification, leaks a source/path, or references a tool that does not exist). It is ADDITIVE to the existing
tools/validate_sarf_skill.py and tools/validate_nahw_skill.py (those stay the structural gate; this is the engine-alignment gate).

CLI: python3 tools/validate_sarf_nahw_skill_backprop.py | --self-test. Stdlib only; exit non-zero on any violation.
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import leak_sot  # noqa: E402

# tools/schemas a back-propagated skill cites — all must exist on disk (a dangling reference is a stale skill).
_REQUIRED_PATHS = [
    "tools/fusha_morphology_lattice.py", "tools/fusha_text_check.py", "tools/fusha_suggest.py",
    "tools/fusha_learner_feedback.py", "tools/fusha_cefr_gate.py", "tools/fusha_governor.py",
    "tools/validate_dependency_lattice.py", "tools/fusha_conflicts.py", "tools/fusha_check.py",
    "qamus/schemas/morphology-candidate-lattice.schema.json", "qamus/schemas/dependency-candidate-lattice.schema.json",
]
# a POSITIVE CEFR-certification CLAIM. Tightened to phrases that NEVER appear in a disclaimer, so the legitimate
# 'CEFR is scaffolding, not certification' / 'never asserts or certifies a learner's level' phrasing does NOT match.
_CERT_CLAIM = re.compile(r"official\s+cefr|cefr\s+certificate|cefr[- ]?certified|proficiency\s+certificate"
                         r"|officially\s+assess|assigns?\s+a\s+cefr\s+level|certif\w*\s+a\s+cefr\s+level", re.I)
# a real local-path / secret leak in instruction prose (source NAMES like 'QAC' are legitimately discussed as evidence/boundary).
_PATH_LEAK = re.compile(r"[A-Za-z]:\\\\|/srv/|/home/|/Users/|root\.txt")


def _read(rel):
    p = os.path.join(_REPO, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _rows(rel):
    out = []
    p = os.path.join(_REPO, rel)
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def check_skill_text(sarf_skill, nahw_skill):
    """Engine-alignment checks over the two SKILL.md bodies (pure; the self-test feeds broken text here)."""
    e = []
    s, n = sarf_skill.lower(), nahw_skill.lower()
    # --- sarf ---
    if "morphology candidate lattice" not in s:
        e.append("sarf/SKILL.md does not mention the morphology candidate lattice")
    if not any(m in s for m in ("never one forced parse", "never force one", "all readings", "competing reading")):
        e.append("sarf/SKILL.md does not state the ambiguity rule (implies one forced parse for unvoweled Arabic)")
    if "pending" not in s:
        e.append("sarf/SKILL.md does not route morphology uncertainty to pending/review")
    if "fusha_morphology_lattice.py" not in sarf_skill:
        e.append("sarf/SKILL.md does not reference the executable morphology tool (fusha_morphology_lattice.py)")
    if _CERT_CLAIM.search(sarf_skill):
        e.append("sarf/SKILL.md makes a CEFR certification/assessment claim")
    # --- nahw ---
    if "dependency candidate lattice" not in n and "governor/dependency" not in n and "governor / iʿrāb / dependency" not in n:
        e.append("nahw/SKILL.md does not mention the governor/dependency lattice")
    if "governor_not_justified" not in n or not any(m in n for m in ("right answer, wrong reason", "right-answer-wrong-reason", "wrong reason")):
        e.append("nahw/SKILL.md does not mention right-answer-wrong-reason / governor_not_justified")
    if "unresolved unless justified" not in n:
        e.append("nahw/SKILL.md does not keep PP-attachment unresolved (implies it can be resolved without evidence)")
    if "fusha_governor.py" not in nahw_skill:
        e.append("nahw/SKILL.md does not reference the executable governor tool (fusha_governor.py)")
    if _CERT_CLAIM.search(nahw_skill):
        e.append("nahw/SKILL.md makes a CEFR certification/assessment claim")
    return e


def check_disk():
    """File-existence + eval-content + leak checks against the real tree."""
    e = []
    # required procedures / references / evals exist
    for rel in ("sarf/procedures/morphology-candidate-lattice.md", "sarf/procedures/clitic-segmentation-and-ambiguity.md",
                "sarf/references/morphology-candidate-fields.md", "sarf/evals/morphology-candidate-lattice.jsonl",
                "nahw/procedures/governor-dependency-lattice.md", "nahw/procedures/irab-right-answer-wrong-reason.md",
                "nahw/procedures/suggestion-gating-for-irab.md", "nahw/references/dependency-candidate-fields.md",
                "nahw/evals/governor-dependency-lattice.jsonl", "nahw/evals/irab-right-answer-wrong-reason.jsonl"):
        if not os.path.exists(os.path.join(_REPO, rel)):
            e.append("missing required back-prop artifact: %s" % rel)
    # referenced tools/schemas exist
    for rel in _REQUIRED_PATHS:
        if not os.path.exists(os.path.join(_REPO, rel)):
            e.append("a back-propagated skill cites a missing path: %s" % rel)
    # sarf eval: an ambiguity-preserving case (>=2 candidates kept)
    s_rows = _rows("sarf/evals/morphology-candidate-lattice.jsonl")
    if not any(r.get("keep_ambiguity") is True and int(r.get("expected_min_candidates", 0)) >= 2 for r in s_rows):
        e.append("sarf morphology eval lacks an ambiguity-preserving case (>=2 candidates kept)")
    # nahw evals: PP-attachment unresolved + iḍāfa ambiguity + a governor_not_justified verdict
    g_rows = _rows("nahw/evals/governor-dependency-lattice.jsonl")
    if not any(r.get("pp_attachment") == "unresolved" for r in g_rows):
        e.append("nahw governor eval lacks a PP-attachment-unresolved case")
    if not any(r.get("keep_idafa_ambiguity") is True for r in g_rows):
        e.append("nahw governor eval lacks an iḍāfa-ambiguity-preserved case")
    if not any(r.get("auto_safe_forbidden") is True for r in g_rows):
        e.append("nahw governor eval lacks an iʿrāb-correction-not-auto-safe case")
    w_rows = _rows("nahw/evals/irab-right-answer-wrong-reason.jsonl")
    if not any(r.get("verdict") == "governor_not_justified" and r.get("right_answer_wrong_reason") is True for r in w_rows):
        e.append("nahw eval lacks a governor_not_justified / right-answer-wrong-reason case")
    # leak scan: eval authored fields (public-facing example proxy) + path/secret leak in new instruction files
    for rel in ("sarf/evals/morphology-candidate-lattice.jsonl", "nahw/evals/governor-dependency-lattice.jsonl",
                "nahw/evals/irab-right-answer-wrong-reason.jsonl"):
        for r in _rows(rel):
            for k, v in r.items():
                if isinstance(v, str) and leak_sot.is_leak(v):
                    e.append("%s row %s field %s leaks a source/provenance/path string" % (rel, r.get("id"), k))
    for rel in ("sarf/procedures/morphology-candidate-lattice.md", "sarf/procedures/clitic-segmentation-and-ambiguity.md",
                "sarf/references/morphology-candidate-fields.md", "nahw/procedures/governor-dependency-lattice.md",
                "nahw/procedures/irab-right-answer-wrong-reason.md", "nahw/procedures/suggestion-gating-for-irab.md",
                "nahw/references/dependency-candidate-fields.md"):
        if _PATH_LEAK.search(_read(rel)):
            e.append("%s contains a local-path / secret leak" % rel)
    return e


def validate():
    return check_skill_text(_read("sarf/SKILL.md"), _read("nahw/SKILL.md")) + check_disk()


def _self_test():
    failures = []
    # the real (post-edit) tree must be clean
    errs = validate()
    if errs:
        failures.append("real skill tree should pass but: %s" % errs[:3])
    # deliberately-broken skill text must trip the text checks (strip ALL case variants — the checks are case-insensitive)
    good_s, good_n = _read("sarf/SKILL.md"), _read("nahw/SKILL.md")

    def _strip(text, *phrases):
        for p in phrases:
            text = re.sub(re.escape(p), "X", text, flags=re.I)
        return text

    bad_cases = [
        ("sarf lattice", _strip(good_s, "morphology candidate lattice"), good_n),
        ("sarf ambiguity", _strip(good_s, "never one forced parse", "never force one", "all readings", "competing reading"), good_n),
        ("sarf tool ref", _strip(good_s, "fusha_morphology_lattice.py"), good_n),
        ("nahw governor lattice", good_s, _strip(good_n, "dependency candidate lattice", "governor/dependency", "governor / iʿrāb / dependency")),
        ("nahw raww", good_s, _strip(good_n, "governor_not_justified")),
        ("nahw pp unresolved", good_s, _strip(good_n, "unresolved unless justified")),
        ("nahw tool ref", good_s, _strip(good_n, "fusha_governor.py")),
        ("cert claim", good_s + "\nThis CEFR certificate proves the level.", good_n),
    ]
    for name, bs, bn in bad_cases:
        if not check_skill_text(bs, bn):
            failures.append("broken case %r should trip a text check but did not" % name)
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_sarf_nahw_skill_backprop self-test: skills aligned to the engine; ambiguity/governor/right-answer-wrong-reason/CEFR-scaffold/leak/path checks reject")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Prove sarf/nahw SKILLs stay aligned with the P1/P2/P2b engine.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    errs = validate()
    for m in errs:
        print("FAIL " + m)
    print("checked sarf/nahw skill back-prop: %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
