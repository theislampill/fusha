#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_sarf_nahw_curriculum_drills_readmes — prove the curriculum/drills/README surfaces stay engine-aligned.

A corrective gate: the prior skill back-prop neglected `sarf/curriculum`, `sarf/drills`, `nahw/curriculum`, `nahw/drills`, and the
repo READMEs. This validator fails if those surfaces drift from the P1/P2/P2b engine contracts — i.e. a named dir loses its
engine-aligned content, a README overclaims (CEFR certification / live-coverage-from-tooling), names a stale branch stack, leaks a
local-path/secret, or a cited tool/schema/procedure path does not exist. It is ADDITIVE to the existing skill validators.

CLI: python3 tools/validate_sarf_nahw_curriculum_drills_readmes.py | --self-test. Stdlib only; exit non-zero on any violation.
"""
import argparse
import glob
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Per named dir: every marker (lower-case substring) must appear somewhere in the dir's concatenated .md content.
_DIR_MARKERS = {
    "sarf/curriculum": ["candidate", "pending", "fusha_morphology_lattice"],
    "sarf/drills": ["candidate lattice", "pending", "fusha_morphology_lattice"],
    "nahw/curriculum": ["governor", "governor_not_justified", "fusha_governor", "pending"],
    "nahw/drills": ["governor", "governor_not_justified", "fusha_governor"],
}
# also require an explicit ambiguity/right-answer-wrong-reason phrasing somewhere in each side
_SARF_AMBIGUITY = ("never force one", "blank beats", "decision: pending", "keep every", "keep both", "candidate set")
_NAHW_RAWW = ("right answer, wrong reason", "right-answer-wrong-reason", "governor_not_justified")
_NAHW_PP = ("pp-attachment", "pp_attachment", "prep_attachment_unclear", "unresolved unless", "attachment) stays unresolved",
            "stays unresolved")

# a POSITIVE CEFR-certification CLAIM (must NOT match the 'scaffolding, not certification' disclaimer)
_CERT_CLAIM = re.compile(r"official\s+cefr|cefr\s+certificate|cefr[- ]?certified|proficiency\s+certificate"
                         r"|officially\s+assess|assigns?\s+a\s+cefr\s+level|certif\w*\s+a\s+cefr\s+level", re.I)
# a live-coverage-progress-from-tooling overclaim (line-level; a negation on the line clears it)
_COVERAGE_CLAIM = re.compile(r"(increase|improv|advanc|boost|gain|rais)\w*[^.\n]*\bcoverage\b", re.I)
_NEGATION = re.compile(r"\bnot\b|\bnever\b|\bno\s+live\b|isn['’]?t|\bwithout\b", re.I)
# a real local-path / secret leak (source NAMES like QAC/Tafsir are legitimately discussed as internal evidence)
_PATH_LEAK = re.compile(r"[A-Za-z]:\\\\|/srv/|/home/|/Users/|root\.txt")

# the latest CONCRETE committed Fusha branch-stack tip the capability README must still name (anti-stale check).
# Bump this each time the stack advances; the data/runtime pass advanced it past 17e5419 to 8fcad75 (the
# curriculum/drills/README back-prop commit, named in README as the last link before the current branch).
_CURRENT_STACK_TIP = "8fcad75"

# tool/schema/procedure paths the new curriculum/drills/READMEs cite — all must exist (a dangling citation = stale doc)
_CITED_PATHS = [
    "tools/fusha_morphology_lattice.py", "tools/fusha_text_check.py", "tools/fusha_governor.py",
    "tools/fusha_suggest.py", "tools/fusha_learner_feedback.py", "tools/fusha_cefr_gate.py",
    "sarf/procedures/morphology-candidate-lattice.md", "sarf/procedures/clitic-segmentation-and-ambiguity.md",
    "sarf/references/morphology-candidate-fields.md", "sarf/evals/morphology-candidate-lattice.jsonl",
    "nahw/procedures/governor-dependency-lattice.md", "nahw/procedures/irab-right-answer-wrong-reason.md",
    "nahw/procedures/suggestion-gating-for-irab.md", "nahw/references/dependency-candidate-fields.md",
    "nahw/evals/governor-dependency-lattice.jsonl", "nahw/evals/irab-right-answer-wrong-reason.jsonl",
    "curriculum/cefr-fusha-instruction.md",
]
# READMEs to sweep (real ones; dist/ and out/ are generated and excluded)
_REAL_READMES = [
    "README.md", "sarf/README.md", "nahw/README.md", "tools/README.md", "curriculum/README.md", "qamus/README.md",
    "corpora/README.md", "provenance/README.md", "sources/README.md", "sources/tafsir_mcp/README.md",
    "qamus/data/current/README.md", "qamus/candidates/nawawi40/README.md", "qamus/candidates/qamus_2092/README.md",
]
_TOUCHED = [  # files this thread edited — leak/overclaim checks focus here
    "README.md", "curriculum/README.md", "sarf/README.md", "nahw/README.md",
    "sarf/curriculum/drills-beginner.md", "sarf/drills/root-detection.md",
    "nahw/curriculum/drills-beginner.md", "nahw/drills/irab-case-mood.md",
]


def _read(rel):
    p = os.path.join(_REPO, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _dir_text(rel):
    return "\n".join(_read(os.path.relpath(p, _REPO)) for p in sorted(glob.glob(os.path.join(_REPO, rel, "*.md"))))


def check_dirs(dir_text=None):
    """No-neglect: each named dir carries its engine-aligned content. `dir_text` override feeds the self-test broken snippets."""
    e = []
    get = (lambda d: dir_text[d]) if dir_text is not None else (lambda d: _dir_text(d).lower())
    for d, markers in _DIR_MARKERS.items():
        t = get(d)
        for m in markers:
            if m not in t:
                e.append("%s lacks engine-aligned content (missing %r)" % (d, m))
    if not any(p in get("sarf/curriculum") + get("sarf/drills") for p in _SARF_AMBIGUITY):
        e.append("sarf curriculum/drills lack an explicit ambiguity-preserving rule (never-force-one / blank-beats-wrong / decision:pending)")
    if not any(p in get("nahw/curriculum") + get("nahw/drills") for p in _NAHW_RAWW):
        e.append("nahw curriculum/drills lack a right-answer-wrong-reason / governor_not_justified case")
    if not any(p in get("nahw/curriculum") + get("nahw/drills") for p in _NAHW_PP):
        e.append("nahw curriculum/drills lack a PP-attachment-unresolved / iḍāfa-ambiguity case")
    return e


def check_readmes():
    e = []
    for rel in _REAL_READMES:
        txt = _read(rel)
        if not txt:
            continue
        if _CERT_CLAIM.search(txt):
            e.append("%s makes a CEFR certification/assessment claim" % rel)
        for ln in txt.splitlines():
            if _COVERAGE_CLAIM.search(ln) and not _NEGATION.search(ln):
                e.append("%s overclaims live coverage progress from tooling (%r)" % (rel, ln.strip()[:70]))
    # the capability README must name the current branch-stack tip (anti-stale)
    if _CURRENT_STACK_TIP not in _read("README.md"):
        e.append("root README.md does not name the current branch-stack tip %s (stale stack)" % _CURRENT_STACK_TIP)
    return e


def check_leaks_and_paths():
    e = []
    for rel in _TOUCHED:
        if _PATH_LEAK.search(_read(rel)):
            e.append("%s contains a local-path / secret leak" % rel)
    for rel in _CITED_PATHS:
        if not os.path.exists(os.path.join(_REPO, rel)):
            e.append("a curriculum/drill/README cites a missing path: %s" % rel)
    return e


def validate():
    return check_dirs() + check_readmes() + check_leaks_and_paths()


def _self_test():
    failures = []
    if validate():
        failures.append("real tree should pass but: %s" % validate()[:3])
    # broken dir snippets must trip check_dirs
    good = {d: _dir_text(d).lower() for d in _DIR_MARKERS}
    base = dict(good)
    b = dict(base); b["sarf/curriculum"] = b["sarf/curriculum"].replace("candidate", "x")
    if not check_dirs(b):
        failures.append("a sarf/curriculum missing 'candidate' should trip")
    b = dict(base); b["nahw/drills"] = b["nahw/drills"].replace("governor_not_justified", "x"); b["nahw/curriculum"] = b["nahw/curriculum"].replace("governor_not_justified", "x")
    if not check_dirs(b):
        failures.append("nahw missing governor_not_justified should trip")
    b = dict(base); b["nahw/curriculum"] = b["nahw/curriculum"].replace("fusha_governor", "x"); b["nahw/drills"] = b["nahw/drills"].replace("fusha_governor", "x")
    if not check_dirs(b):
        failures.append("nahw missing the fusha_governor tool ref should trip")
    # cert + coverage regexes
    if not _CERT_CLAIM.search("issued an official CEFR certificate"):
        failures.append("cert regex should catch an official CEFR certificate")
    if _CERT_CLAIM.search("CEFR is scaffolding, not certification; the engine never certifies a learner's level"):
        failures.append("cert regex must NOT match the disclaimer")
    if not (_COVERAGE_CLAIM.search("this tooling increased live Qamus coverage") and not _NEGATION.search("this tooling increased live Qamus coverage")):
        failures.append("coverage overclaim should be caught")
    if _NEGATION.search("this is tooling, not live Qamus coverage progress") is None:
        failures.append("the disclaimer line should be cleared by the negation check")
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_sarf_nahw_curriculum_drills_readmes self-test: 4 named dirs engine-aligned; READMEs no-cert / no-coverage-overclaim / current-stack / leak-free; cited paths exist")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Prove sarf/nahw curriculum + drills + READMEs stay engine-aligned.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    errs = validate()
    for m in errs:
        print("FAIL " + m)
    print("checked curriculum/drills/README back-prop: %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
