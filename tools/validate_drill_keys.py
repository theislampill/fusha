#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_drill_keys — lint the machine answer-key fixtures for the OBJECTIVE prose drills (P1-4).

Each objective drill under `curriculum/drills/` (function-words, root-pattern, morphology-foundations,
sentence-foundations) gets a sibling answer-key file `curriculum/drills/keys/<drill>.keys.jsonl` in the same
answer-key schema as `curriculum/assessment/answer-key.schema.md`. This validator is the thin gate over them.

DEFERRED (P1 keyed the 4 objective drills above; these 7 are NOT yet keyed — they are reading / composition / index
drills whose grading is open-prose or routing, not a closed objective answer key): alphabet-and-sounds,
ayah-reading-drills, hover-composition-and-routing, nawawi40-reading-drills, parse-key-and-color-layer,
qamus-entry-drills, dogfood-error-remediation-index. Author keys for these only if/when they gain objective items.

It reuses the `validate_curriculum_assessment` shape (REQUIRED-field set, hard-grammar vs objective detection by
HARD_TERMS, the per-file "at least one two-vote hard-grammar row" rule, the Level-7+ hard-row two-vote rule) and adds:
  * LEAK SCAN via the single source of truth `tools/leak_sot.py` (not a private term list — so it can never drift from
    the canonical detector). Every serialized row is scanned, catching forbidden field NAMES too.
  * REFERENTIAL cited-path check (like fusha_checkpoint_coverage): every cited sarf_procedure / nahw_procedure /
    remediation_route path must EXIST on disk — a dangling citation is a real defect and FAILs.
  * REFERENTIAL drill-binding check: a `<drill>.keys.jsonl` filename must name an existing `curriculum/drills/<drill>.md`
    (a key file with no drill is an orphan), and every row's remediation_route must point at a real curriculum drill or
    a real sarf/nahw procedure/drill.
  * quran_example, when non-null, must be a source ADDRESS (`quran:S:A:W` / `qamus:...`), never inline scripture text —
    addresses are pointers, not copied text.

It authors nothing and grades no learner. Stdlib only; dry-run; deterministic (no clock, no network, no randomness).
CLI: <keys.jsonl ...> | --self-test. See parserplans/fusha-data-runtime-completion-pass (P1-4).
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leak_sot  # the single source of truth for public-boundary leak detection

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Same answer-key contract as curriculum/assessment (answer-key.schema.md / validate_curriculum_assessment).
REQUIRED = {
    "id", "level", "concept", "prompt", "quran_example", "expected_answer",
    "accepted_variants", "forbidden_answers", "required_reasoning",
    "sarf_procedure", "nahw_procedure", "remediation_route", "two_vote_required",
}
LIST_FIELDS = ("accepted_variants", "forbidden_answers", "required_reasoning")
CITED_PATH_FIELDS = ("sarf_procedure", "nahw_procedure", "remediation_route")

# Hard-grammar trigger terms — identical to validate_curriculum_assessment.HARD_TERMS so the two banks agree on what
# "hard grammar" means (a hard row must carry two_vote_required=true; Level-7+ hard rows MUST).
HARD_TERMS = (
    "iʿrāb", "case", "mood", "particle", "PP", "pronoun", "exception",
    "vocative", "oath", "token-only", "component", "preposition",
)

# A non-null quran_example must be a source ADDRESS, not inline scripture text (addresses are pointers, never copied
# text — keeps the public boundary clean). quran:S[:A[:W]] or a qamus:v###/n### study handle.
_ADDRESS_RE = re.compile(r"^(?:quran:\d+(?::\d+){0,2}|qamus:[vn]?\w+)$")


def _level_numbers(value):
    return [int(m) for m in re.findall(r"\d+", str(value))]


def _load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("%s:%d: invalid JSON: %s" % (path, lineno, exc))
            if not isinstance(row, dict):
                raise ValueError("%s:%d: row must be an object" % (path, lineno))
            row["_line"] = lineno
            rows.append(row)
    return rows


def validate(path, repo_root=_REPO):
    errors = []
    rows = _load_jsonl(path)
    if not rows:
        return ["%s: no rows" % path]

    name = os.path.basename(path)
    # filename must be <drill>.keys.jsonl AND name an existing curriculum drill (no orphan key file).
    m = re.match(r"^(.+)\.keys\.jsonl$", name)
    if not m:
        errors.append("%s: filename must be <drill>.keys.jsonl" % path)
    else:
        drill_md = os.path.join(repo_root, "curriculum", "drills", m.group(1) + ".md")
        if not os.path.exists(drill_md):
            errors.append("%s: no matching drill curriculum/drills/%s.md (orphan key file)" % (path, m.group(1)))

    ids = set()
    hard_rows = 0
    two_vote_hard_rows = 0
    for row in rows:
        lineno = row.pop("_line")
        missing = REQUIRED - set(row)
        if missing:
            errors.append("%s:%d: missing fields: %s" % (path, lineno, ", ".join(sorted(missing))))
            continue
        if row["id"] in ids:
            errors.append("%s:%d: duplicate id %r" % (path, lineno, row["id"]))
        ids.add(row["id"])
        for field in LIST_FIELDS:
            if not isinstance(row[field], list) or not row[field]:
                errors.append("%s:%d: %s must be a nonempty list" % (path, lineno, field))
        if not isinstance(row["two_vote_required"], bool):
            errors.append("%s:%d: two_vote_required must be boolean" % (path, lineno))

        # quran_example: null or a source address (never inline scripture text).
        qx = row["quran_example"]
        if qx is not None:
            if not isinstance(qx, str) or not _ADDRESS_RE.match(qx.strip()):
                errors.append("%s:%d: quran_example must be null or a source address (quran:S:A:W / qamus:...), "
                              "not inline text: %r" % (path, lineno, qx))

        # LEAK SCAN via the SoT (catches forbidden field names + source/brand/path leakage).
        hits = leak_sot.scan(json.dumps(row, ensure_ascii=False))
        if hits:
            errors.append("%s:%d: row leaks internal/source term(s): %s" % (path, lineno, ", ".join(hits)))

        # REFERENTIAL: every cited path must exist on disk (dangling citation = real defect).
        for field in CITED_PATH_FIELDS:
            p = row[field]
            if p and not os.path.exists(os.path.join(repo_root, p)):
                errors.append("%s:%d: %s cites missing path %r" % (path, lineno, field, p))

        # hard-grammar detection mirrors validate_curriculum_assessment (whole-row substring, case-insensitive).
        blob = json.dumps(row, ensure_ascii=False).lower()
        is_hard = any(term.lower() in blob for term in HARD_TERMS)
        is_level_7_plus = any(L >= 7 for L in _level_numbers(row["level"]))
        if is_hard:
            hard_rows += 1
            if row["two_vote_required"]:
                two_vote_hard_rows += 1
            if is_level_7_plus and not row["two_vote_required"]:
                errors.append("%s:%d: Level 7+ hard-grammar row must set two_vote_required=true" % (path, lineno))

    if hard_rows == 0:
        errors.append("%s: expected at least one hard-grammar row" % path)
    if two_vote_hard_rows == 0:
        errors.append("%s: expected at least one two_vote_required hard-grammar row" % path)
    return errors


def _self_test():
    import tempfile
    failures = []

    good = {
        "id": "ST-good", "level": "7", "concept": "particle function",
        "prompt": "Why is the particle function context-dependent?",
        "quran_example": "quran:2:3:5", "expected_answer": "The particle must be classified by context.",
        "accepted_variants": ["context decides the particle"], "forbidden_answers": ["always one gloss"],
        "required_reasoning": ["particle function named"],
        "sarf_procedure": None, "nahw_procedure": "nahw/procedures/particle-decision.md",
        "remediation_route": "curriculum/drills/quranic-function-words.md", "two_vote_required": True,
    }
    objective = dict(good, id="ST-obj", level="4", concept="agent pattern", two_vote_required=False,
                     prompt="Name the pattern of the active participle.", quran_example=None,
                     nahw_procedure=None, sarf_procedure="sarf/procedures/root-decision.md",
                     remediation_route="curriculum/drills/morphology-foundations.md")

    def _write(rows, fname):
        d = tempfile.mkdtemp()
        # write inside a fake curriculum/drills/keys layout so the orphan + drill checks resolve against a real drill
        keys_dir = os.path.join(d, "curriculum", "drills", "keys")
        os.makedirs(keys_dir)
        # mirror the two drills we cite so the orphan/path checks pass against this temp repo root
        for drill in ("quranic-function-words", "morphology-foundations"):
            open(os.path.join(d, "curriculum", "drills", drill + ".md"), "w", encoding="utf-8").close()
        for proc in ("sarf/procedures/root-decision.md", "nahw/procedures/particle-decision.md"):
            pdir = os.path.join(d, os.path.dirname(proc))
            os.makedirs(pdir, exist_ok=True)
            open(os.path.join(d, proc), "w", encoding="utf-8").close()
        fp = os.path.join(keys_dir, fname)
        with open(fp, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        return d, fp

    # GOOD fixture: a hard two-vote row + an objective row, against a temp repo with the cited paths present.
    d, fp = _write([good, objective], "quranic-function-words.keys.jsonl")
    errs = validate(fp, repo_root=d)
    if errs:
        failures.append("clean fixture rejected: %s" % errs)

    # BROKEN 1: a Level-7 hard-grammar row with two_vote_required=false must be rejected.
    weak = dict(good, id="ST-weak", two_vote_required=False)
    d2, fp2 = _write([weak], "quranic-function-words.keys.jsonl")
    if not any("Level 7+ hard-grammar row" in e for e in validate(fp2, repo_root=d2)):
        failures.append("a weak Level-7 hard-grammar row was accepted")

    # BROKEN 2: a leak (source brand) must be caught by the SoT scan.
    leaky = dict(objective, id="ST-leak", expected_answer="per tafsir, the active participle pattern")
    d3, fp3 = _write([good, leaky], "morphology-foundations.keys.jsonl")
    if not any("leaks internal/source" in e for e in validate(fp3, repo_root=d3)):
        failures.append("a source-leak row was accepted")

    # BROKEN 3: a dangling cited path must be caught.
    dangling = dict(objective, id="ST-dangle", remediation_route="curriculum/drills/does-not-exist.md")
    d4, fp4 = _write([good, dangling], "morphology-foundations.keys.jsonl")
    if not any("cites missing path" in e for e in validate(fp4, repo_root=d4)):
        failures.append("a dangling cited path was accepted")

    # BROKEN 4: inline scripture text in quran_example (not an address) must be caught.
    inline = dict(objective, id="ST-inline", quran_example="بِسْمِ ٱللَّهِ")
    d5, fp5 = _write([good, inline], "morphology-foundations.keys.jsonl")
    if not any("quran_example must be null or a source address" in e for e in validate(fp5, repo_root=d5)):
        failures.append("inline-text quran_example was accepted")

    # BROKEN 5: an orphan key file (no matching drill) must be caught.
    d6, fp6 = _write([good, objective], "no-such-drill.keys.jsonl")
    if not any("orphan key file" in e for e in validate(fp6, repo_root=d6)):
        failures.append("an orphan key file was accepted")

    # the SHIPPED key files must validate clean (real regression guard).
    keys_dir = os.path.join(_REPO, "curriculum", "drills", "keys")
    if os.path.isdir(keys_dir):
        for fn in sorted(os.listdir(keys_dir)):
            if fn.endswith(".keys.jsonl"):
                shipped_errs = validate(os.path.join(keys_dir, fn))
                if shipped_errs:
                    failures.append("shipped %s has errors: %s" % (fn, shipped_errs[:3]))

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_drill_keys self-test: schema + leak-SoT scan + dangling-citation + orphan-drill + "
              "address-only quran_example + Level-7 two-vote rule; shipped key files validate clean")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate drill answer-key fixtures (schema + leak SoT + cited-path refs).")
    ap.add_argument("paths", nargs="*", help="<drill>.keys.jsonl files")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.paths:
        ap.error("provide at least one <drill>.keys.jsonl path or --self-test")
    all_errors = []
    for path in a.paths:
        all_errors.extend(validate(path))
    if all_errors:
        print("DRILL KEYS VALIDATION FAIL")
        for err in all_errors:
            print("  -", err)
        return 1
    print("DRILL KEYS OK - %d file(s)" % len(a.paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
