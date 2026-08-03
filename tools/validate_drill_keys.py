#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_drill_keys — lint the machine answer-key fixtures for the OBJECTIVE prose drills (P1-4).

Each objective drill under `curriculum/drills/` gets a sibling answer-key file `curriculum/drills/keys/<drill>.keys.jsonl`
in the same answer-key schema as `curriculum/assessment/answer-key.schema.md`. This validator is the thin gate over
them. As of Train C, 8 of the drills under `curriculum/drills/` are keyed (see `curriculum/drills/keys/*.keys.jsonl`);
the remaining reading / composition / index drills are open-prose or routing and have no closed objective answer key —
author keys for those only if/when they gain objective items.

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
  * KC-ID RESOLUTION (Train C): an optional `kc_id` on a row must resolve in `curriculum/kc-catalog.json`.
  * KEY-FILE LOCALITY (Train C): a row's `kc_id` must own THIS key file via its KC's `drill_route` — a miss must
    route back to the drill the row lives in, not to some other KC's drill.
  * ASSESSMENT QUARANTINE (Train C, THE central invariant): no row in `curriculum/assessment/*.jsonl` may carry
    candidate provenance (a curriculum-candidate drill id or a curriculum/l1l6 provenance field) — an answer-visible
    candidate must never become an assessment item. Checked independently of any single key file.
  * BATCH NO-OCCURRENCE ASSERTION (Train C): the 14 Train-C re-authored rows carry `quran_example: null` (paradigm-
    level corrections with no occurrence evidence in this batch) — an explicit assertion over those ids, not a
    global rule (other rows may cite a real address).
  * ANSWER-KEY ROUND-TRIP (Train C repair): every row's own `expected_answer` and each `accepted_variants` entry
    must itself pass `tools/fusha_tutor_runtime.grade()` against the row's own `required_reasoning` — an authored
    correct answer that the ordinary runtime grader cannot pass would silently remediate a learner who typed
    exactly that accepted answer (this is what shipped PK-7/FW-18 broken: an `ordered_slots` phrase absent from
    an accepted variant). Applies to every shipped row in every key file, not just those two.

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
sys.path.insert(0, _REPO)
from tools import fusha_tutor_runtime as tutor_runtime  # noqa: E402  (the SAME grader a learner's answer runs through)

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

# Train C: the 14 re-authored rows carry NO occurrence evidence (paradigm-level corrections). Asserted explicitly
# over these ids only — not a global rule; other rows may legitimately cite a real quran_example address.
BATCH_NO_OCCURRENCE_IDS = frozenset({
    "HC-6-laam-sun-letter", "HC-7-laam-gemination-merge", "HC-8-nun-wiqaya-drop",
    "PK-6-dual-referent-count", "PK-7-dual-plural-oblique-overlap", "PK-8-sound-plural-rationality",
    "PK-9-mafaul-form-class-first", "PK-10-hollow-root-patient-skeleton", "PK-11-mim-noun-present-stem",
    "RP-12-masdar-not-uniform", "RP-13-weak-letter-radical-or-addition", "RP-14-root-not-just-consonant-count",
    "FW-17-waw-circumstance-or-oath", "FW-18-maa-suspends-government",
})

# Candidate-provenance field names that must never appear on a curriculum/assessment/*.jsonl row (the assessment
# quarantine — RED-8, the invariant this packet exists to prevent from being violated).
ASSESSMENT_PROVENANCE_FIELDS = frozenset({
    "kc_id", "drill_id", "source_misconception", "misconception_id", "candidate_id",
    "candidate_drill_id", "curriculum_l1l6_id", "candidate_provenance",
})


def _kc_catalog(repo_root=_REPO):
    path = os.path.join(repo_root, "curriculum", "kc-catalog.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {kc["kc_id"]: kc for kc in json.load(fh)}


def assessment_quarantine_violations(repo_root=_REPO):
    """RED-8: no row in curriculum/assessment/*.jsonl may carry candidate provenance. Written first, before any
    key row exists — this is the invariant everything else in this batch could violate."""
    import glob
    errors = []
    assessment_dir = os.path.join(repo_root, "curriculum", "assessment")
    for path in sorted(glob.glob(os.path.join(assessment_dir, "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    continue
                hit = ASSESSMENT_PROVENANCE_FIELDS & set(row)
                if hit:
                    errors.append("%s:%d: row carries candidate-provenance field(s) %s — assessment quarantine "
                                  "violation (an answer-visible candidate may never become an assessment item)"
                                  % (path, lineno, sorted(hit)))
    return errors


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
    own_drill_route = None
    if not m:
        errors.append("%s: filename must be <drill>.keys.jsonl" % path)
    else:
        drill_md = os.path.join(repo_root, "curriculum", "drills", m.group(1) + ".md")
        if not os.path.exists(drill_md):
            errors.append("%s: no matching drill curriculum/drills/%s.md (orphan key file)" % (path, m.group(1)))
        else:
            own_drill_route = "curriculum/drills/%s.md" % m.group(1)

    kc_catalog = _kc_catalog(repo_root)
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

        # Train C: kc_id resolution (RED-6) + key-file locality (RED-7) — an optional field; a row without it is
        # unaffected (no invention of a binding that was not authored).
        kc_id = row.get("kc_id")
        if kc_id is not None:
            kc = kc_catalog.get(kc_id)
            if kc is None:
                errors.append("%s:%d: kc_id %r does not resolve in curriculum/kc-catalog.json" % (path, lineno, kc_id))
            elif own_drill_route and kc.get("drill_route") != own_drill_route:
                errors.append("%s:%d: kc_id %r's drill_route %r is not this key file's own drill %r — a miss must "
                              "route back to the drill the row lives in" % (path, lineno, kc_id,
                                                                            kc.get("drill_route"), own_drill_route))

        # Train C: the batch's own no-occurrence-claim assertion (RED-9) — over these 14 ids only.
        if row["id"] in BATCH_NO_OCCURRENCE_IDS and qx is not None:
            errors.append("%s:%d: Train-C row %r must carry quran_example: null (no occurrence evidence in this "
                          "batch)" % (path, lineno, row["id"]))

        # LEAK SCAN via the SoT (catches forbidden field names + source/brand/path leakage).
        hits = leak_sot.scan(json.dumps(row, ensure_ascii=False))
        if hits:
            errors.append("%s:%d: row leaks internal/source term(s): %s" % (path, lineno, ", ".join(hits)))

        # REFERENTIAL: every cited path must exist on disk (dangling citation = real defect).
        for field in CITED_PATH_FIELDS:
            p = row[field]
            if p and not os.path.exists(os.path.join(repo_root, p)):
                errors.append("%s:%d: %s cites missing path %r" % (path, lineno, field, p))

        # ANSWER-KEY ROUND-TRIP (Train C repair, BLOCKER 2): the row's own expected_answer and every accepted
        # variant must themselves pass fusha_tutor_runtime.grade() against the row's own required_reasoning. A
        # row with no ordered_slots trivially passes (a form always content-matches itself); this is a real
        # regression guard only for rows that add ordered_slots (or any future grading constraint keyed off the
        # raw answer text rather than the matched form).
        _variants = row["accepted_variants"] if isinstance(row["accepted_variants"], list) else []
        _forms = [("expected_answer", row["expected_answer"])]
        _forms += [("accepted_variants[%d]" % i, v) for i, v in enumerate(_variants)]
        for _label, _form in _forms:
            _g = tutor_runtime.grade(row, {"answer": _form, "reasoning": list(row.get("required_reasoning") or [])})
            if not _g["passed"]:
                errors.append("%s:%d: %s %r does not pass fusha_tutor_runtime.grade() against its own row — an "
                              "authored correct answer must be gradeable" % (path, lineno, _label, _form))
            if not _g["reasoning_passed"]:
                errors.append("%s:%d: row %r's own required_reasoning does not pass fusha_tutor_runtime.grade() "
                              "when checked against %s %r" % (path, lineno, row["id"], _label, _form))

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

    # BROKEN 6 (RED-6): a kc_id that does not resolve in curriculum/kc-catalog.json must be caught.
    d7 = tempfile.mkdtemp()
    keys_dir7 = os.path.join(d7, "curriculum", "drills", "keys")
    os.makedirs(keys_dir7)
    open(os.path.join(d7, "curriculum", "drills", "quranic-function-words.md"), "w", encoding="utf-8").close()
    for proc in ("sarf/procedures/root-decision.md", "nahw/procedures/particle-decision.md"):
        pdir = os.path.join(d7, os.path.dirname(proc))
        os.makedirs(pdir, exist_ok=True)
        open(os.path.join(d7, proc), "w", encoding="utf-8").close()
    os.makedirs(os.path.join(d7, "curriculum"), exist_ok=True)
    json.dump([], open(os.path.join(d7, "curriculum", "kc-catalog.json"), "w", encoding="utf-8"))
    dangling_kc = dict(good, id="ST-dangle-kc", kc_id="kc-does-not-exist")
    fp7 = os.path.join(keys_dir7, "quranic-function-words.keys.jsonl")
    with open(fp7, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(dangling_kc, ensure_ascii=False) + "\n")
    if not any("kc_id" in e and "does not resolve" in e for e in validate(fp7, repo_root=d7)):
        failures.append("a dangling kc_id was accepted")

    # BROKEN 7 (RED-7): a kc_id whose KC's drill_route is NOT this key file's own drill must be caught.
    json.dump([{"kc_id": "kc-elsewhere", "drill_route": "curriculum/drills/morphology-foundations.md"}],
              open(os.path.join(d7, "curriculum", "kc-catalog.json"), "w", encoding="utf-8"))
    misrouted = dict(good, id="ST-misrouted-kc", kc_id="kc-elsewhere")
    with open(fp7, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(misrouted, ensure_ascii=False) + "\n")
    if not any("is not this key file's own drill" in e for e in validate(fp7, repo_root=d7)):
        failures.append("a kc_id routed to a different drill's key file was accepted")

    # BROKEN 8 (RED-9): a Train-C batch id with a non-null quran_example must be caught.
    json.dump([{"kc_id": "kc-elsewhere", "drill_route": "curriculum/drills/quranic-function-words.md"}],
              open(os.path.join(d7, "curriculum", "kc-catalog.json"), "w", encoding="utf-8"))
    batch_occurrence = dict(good, id="FW-17-waw-circumstance-or-oath", kc_id="kc-elsewhere",
                            quran_example="quran:1:1:1")
    with open(fp7, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(batch_occurrence, ensure_ascii=False) + "\n")
    if not any("must carry quran_example: null" in e for e in validate(fp7, repo_root=d7)):
        failures.append("a Train-C batch row with a non-null quran_example was accepted")

    # BROKEN 9 (RED-8, the assessment quarantine): a candidate-provenanced row in curriculum/assessment/*.jsonl
    # must be caught, independent of any single key file.
    d8 = tempfile.mkdtemp()
    os.makedirs(os.path.join(d8, "curriculum", "assessment"))
    with open(os.path.join(d8, "curriculum", "assessment", "level-checkpoints.sample.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "tainted", "kc_id": "kc-clitic-segmentation"}, ensure_ascii=False) + "\n")
    if not any("assessment quarantine violation" in e for e in assessment_quarantine_violations(repo_root=d8)):
        failures.append("a candidate-provenanced row in an assessment bank was accepted")
    # the REAL assessment banks must carry no candidate provenance today.
    real_quarantine_errs = assessment_quarantine_violations()
    if real_quarantine_errs:
        failures.append("real assessment banks fail the quarantine: %s" % real_quarantine_errs[:3])

    # BROKEN 10 (answer-key round-trip, BLOCKER 2): an accepted_variant that cannot itself pass
    # fusha_tutor_runtime.grade() (here, because an ordered_slots phrase appears in the wrong order in the
    # variant) must be caught. This is the exact class of defect that let PK-7's own authored accepted_variants
    # ship ungradeable — reusing `good`'s own expected_answer/accepted_variants text keeps the fixture honest.
    ungradeable = dict(good, id="ST-ungradeable", ordered_slots=["particle", "context"])
    d9, fp9 = _write([ungradeable], "quranic-function-words.keys.jsonl")
    if not any("does not pass fusha_tutor_runtime.grade()" in e for e in validate(fp9, repo_root=d9)):
        failures.append("an accepted_variant that cannot pass fusha_tutor_runtime.grade() was accepted")

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
              "address-only quran_example + Level-7 two-vote rule + kc_id resolution/locality + assessment "
              "quarantine + batch no-occurrence assertion + answer-key round-trip (own accepted forms pass the "
              "runtime grader); shipped key files validate clean")
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
    all_errors = list(assessment_quarantine_violations())
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
