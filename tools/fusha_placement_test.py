#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_placement_test — the OFFLINE, DETERMINISTIC placement-test runner for the Fusha reading ladder (P1-3).

Turns curriculum/placement-test.md (a self-scoring prose test, sections A-H → rungs 1-8) into an executable harness
that maps an ANSWER PAYLOAD to a starting rung. It does NOT trust the learner's self-report: it grades the CONTENT of
each answer (expected/variant match, forbidden-answer detection, required-reasoning presence, two-vote for hard items)
by reusing tools.fusha_tutor_runtime.grade — exactly the same content-only grader the tutor loop uses, so a
self-reported `passed`/`correct`/`cleared` flag in the payload is ignored.

Placement rule (faithful to placement-test.md "Scoring → starting level"):
    Find the FIRST (lowest) rung the learner did not fully clear; that rung is the start. The ladder is built so each
    rung's machinery is assumed by the next, so a gap below sinks the rungs above — clearing a higher section does NOT
    raise you past an earlier miss. Equivalently the runner recommends the highest CONTIGUOUS prefix of rungs the
    learner cleared, then starts them at the next rung. Clear every rung in the bank → "ready" (top rung + 1).

HARD CONTRACTS (enforced by --self-test):
  * Grading is content-only via fusha_tutor_runtime.grade; a payload `passed`/`correct`/`cleared` flag is IGNORED.
  * A rung counts as cleared ONLY if EVERY item at that rung cleared (a section is failed on any miss — placement-test.md
    "H (any miss)"). This is a deliberately CONSERVATIVE simplification: any per-section partial-credit threshold a
    prose section might allow (e.g. "4 of 5") is intentionally NOT modeled — under-placing a learner is safe (they
    start a rung lower and climb), over-placing is not. Strictness here errs toward review, never past a gap.
  * The recommendation is the lowest UNCLEARED rung; a later cleared rung never lifts you past an earlier gap.
  * Deterministic: no wall clock, no RNG; "now" (if ever needed) is passed in as an explicit int.
  * Source-clean: every emitted text field passes tools/leak_sot.

Stdlib only; dry-run; no live Qamus. Style-matched to tools/fusha_tutor_runtime.py + tools/fusha_checkpoint_coverage.py.
See parserplans/fusha-data-runtime-completion-pass (P1-3).
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
from tools import fusha_tutor_runtime as RT  # noqa: E402  (reuse grade()/_form_matches)
from tools import leak_sot  # noqa: E402

RESULT_SCHEMA = "fusha/placement-result@1"
DEFAULT_BANK = os.path.join(_REPO, "curriculum", "assessment", "placement-test.sample.jsonl")
READY_LABEL = "ready"  # the learner cleared every rung in the bank


def _rung(row):
    """The integer rung a row belongs to (the roadmap level its placement section maps to). Deterministic."""
    v = row.get("rung")
    if isinstance(v, bool):  # guard: bool is an int subclass
        return None
    if isinstance(v, int):
        return v
    nums = re.findall(r"\d+", str(v if v is not None else ""))
    return int(nums[0]) if nums else None


def load_bank(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _payload_for(item_id, answers):
    """Pull the answer payload for one item from the answers map; default to an empty (unanswered) payload.

    answers = {item_id: {answer, reasoning, second_check}}. A missing item is treated as UNANSWERED (a miss), never
    as a pass — silence does not clear a rung."""
    p = (answers or {}).get(item_id)
    return p if isinstance(p, dict) else {"answer": "", "reasoning": []}


def grade_bank(bank, answers):
    """Grade every item (content-only, via RT.grade) and group cleared/missed by rung. Pure; no I/O.

    Returns {by_rung: {rung: {total, cleared, items:[{id, cleared, reasons}]}}, rungs:[sorted rungs]}."""
    by_rung = {}
    for row in bank:
        r = _rung(row)
        if r is None:
            continue  # a row with no parseable rung cannot place; skip it from the ladder (reported by coverage tools)
        payload = _payload_for(row["id"], answers)
        g = RT.grade(row, payload)
        bucket = by_rung.setdefault(r, {"total": 0, "cleared": 0, "items": []})
        bucket["total"] += 1
        if g["cleared"]:
            bucket["cleared"] += 1
        # a compact, source-clean miss-reason (never echoes the learner's free text)
        reasons = []
        if not g["passed"]:
            reasons.append("answer did not match the key")
        if g["forbidden_hit"]:
            reasons.append("a forbidden answer was given")
        if not g["reasoning_passed"]:
            reasons.append("required reasoning missing")
        if g["two_vote_status"] == "pending":
            reasons.append("held: second independent check missing")
        bucket["items"].append({"id": row["id"], "cleared": bool(g["cleared"]),
                                "reasons": [] if g["cleared"] else reasons})
    return {"by_rung": by_rung, "rungs": sorted(by_rung)}


def recommend(graded):
    """Recommend a starting rung from a graded bank. Deterministic, faithful to placement-test.md scoring.

    A rung is CLEARED iff every item at that rung cleared. The recommendation is the lowest rung that is NOT cleared —
    a later cleared rung can never lift the learner past an earlier gap. If every rung clears, the learner is `ready`
    (top rung + 1). Returns (start_rung:int|None, label, cleared_prefix:[rungs])."""
    rungs = graded["rungs"]
    if not rungs:
        return None, "no_rungs", []
    by_rung = graded["by_rung"]
    cleared_prefix = []
    for r in rungs:
        b = by_rung[r]
        if b["total"] > 0 and b["cleared"] == b["total"]:
            cleared_prefix.append(r)
        else:
            # first uncleared rung is the start; stop — gaps below sink the rungs above
            return r, "start_at_rung", cleared_prefix
    # every rung cleared -> ready for the rung after the top
    return rungs[-1] + 1, READY_LABEL, cleared_prefix


def run_placement(bank, answers):
    """Full deterministic placement: grade -> recommend -> assemble a source-clean result object. Pure; no I/O."""
    graded = grade_bank(bank, answers)
    start_rung, label, cleared_prefix = recommend(graded)
    rung_summary = []
    for r in graded["rungs"]:
        b = graded["by_rung"][r]
        rung_summary.append({"rung": r, "total": b["total"], "cleared": b["cleared"],
                             "passed": b["total"] > 0 and b["cleared"] == b["total"],
                             "items": b["items"]})
    if label == READY_LABEL:
        note = "cleared every rung in the bank; ready for the rung above the top"
    elif label == "start_at_rung":
        note = "start at the lowest rung not fully cleared; gaps below sink the rungs above"
    else:
        note = "no placeable rungs in the bank"
    result = {"schema": RESULT_SCHEMA, "start_rung": start_rung, "placement": label,
              "cleared_prefix": cleared_prefix, "rungs_evaluated": graded["rungs"],
              "rung_summary": rung_summary, "note": note}
    # source-clean guard (defensive: rows are authored, but never echo a leak in an emitted field)
    if leak_sot.is_leak(result["note"]):
        result["note"] = leak_sot.redact(result["note"])
    return result


def _read_answers(arg):
    if arg == "-":
        return json.load(sys.stdin)
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(arg)  # inline JSON string


def main():
    ap = argparse.ArgumentParser(description="Offline deterministic Fusha placement-test runner (content-graded; no self-report).")
    ap.add_argument("--bank", default=DEFAULT_BANK, help="placement-test JSONL fixture")
    ap.add_argument("--answers", default=None,
                    help="answer payload map {item_id: {answer, reasoning, second_check}}: JSON file, '-' stdin, or inline JSON")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    bank = load_bank(a.bank)
    answers = _read_answers(a.answers) if a.answers else {}
    result = run_placement(bank, answers)
    print(json.dumps(result, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- self-test
def _authored_bank():
    """A tiny AUTHORED placement bank (rungs 1-3, two items at rung 2) exercising every placement path. No Qurʾān copy."""
    return [
        {"id": "QA1", "rung": 1, "section": "A", "prompt": "name the article + host",
         "quran_example": None, "expected_answer": "the article is al and the host noun is qalam",
         "accepted_variants": ["al is the article; host is qalam"], "forbidden_answers": ["the the pen"],
         "required_reasoning": ["article identified", "host noun identified"], "two_vote_required": False},
        {"id": "QB1", "rung": 2, "section": "B", "prompt": "gloss min",
         "quran_example": None, "expected_answer": "from", "accepted_variants": ["it means from"],
         "forbidden_answers": ["who"], "required_reasoning": ["from given as the gloss"], "two_vote_required": False},
        {"id": "QB2", "rung": 2, "section": "B", "prompt": "why is man here who not from",
         "quran_example": None, "expected_answer": "man means who because the content letter carries fatha",
         "accepted_variants": ["who, decided by the harakah on the nun"], "forbidden_answers": ["they are the same"],
         "required_reasoning": ["content-letter harakah read"], "two_vote_required": True},
        {"id": "QC1", "rung": 3, "section": "C", "prompt": "gender of mualima",
         "quran_example": None, "expected_answer": "feminine by the ta marbuta",
         "accepted_variants": ["feminine, ta marbuta marks it"], "forbidden_answers": ["masculine"],
         "required_reasoning": ["feminine stated", "ta marbuta named"], "two_vote_required": False},
    ]


def _ans(answer, reasoning, second_check=None):
    p = {"answer": answer, "reasoning": reasoning}
    if second_check is not None:
        p["second_check"] = second_check
    return p


def _self_test():
    failures = []
    bank = _authored_bank()

    # known-GOOD full set (every item cleared, two-vote item has an agreeing second check) -> READY at top+1
    good = {
        "QA1": _ans("the article is al and the host noun is qalam",
                    ["the article identified as al", "the host noun identified as qalam"]),
        "QB1": _ans("it means from", ["from given as the gloss"]),
        "QB2": _ans("man means who because the content letter carries fatha", ["the content-letter harakah read"],
                    {"conclusion_agrees": True, "reason_agrees": True}),
        "QC1": _ans("feminine by the ta marbuta", ["feminine stated", "the ta marbuta named"]),
    }
    res = run_placement(bank, good)
    if res["placement"] != READY_LABEL or res["start_rung"] != 4 or res["cleared_prefix"] != [1, 2, 3]:
        failures.append("known-good full set must map to ready/top+1, got %s/%s/%s"
                        % (res["placement"], res["start_rung"], res["cleared_prefix"]))

    # WEAK set: rung-1 cleared, rung-2 fails (vague answers) -> start at rung 2, prefix [1]
    weak = dict(good)
    weak["QB1"] = _ans("not sure maybe who", ["dunno"])
    weak["QB2"] = _ans("i think they are the same", ["no reason"])
    res2 = run_placement(bank, weak)
    if res2["start_rung"] != 2 or res2["placement"] != "start_at_rung" or res2["cleared_prefix"] != [1]:
        failures.append("weak rung-2 set must start at rung 2, got %s/%s" % (res2["start_rung"], res2["cleared_prefix"]))

    # GAP-BELOW: rung-1 fails but a HIGHER rung is cleared -> still placed at rung 1 (a later clear can't lift past a gap)
    gap = dict(good)
    gap["QA1"] = _ans("totally wrong", [])
    res3 = run_placement(bank, gap)
    if res3["start_rung"] != 1 or res3["cleared_prefix"] != []:
        failures.append("a gap at rung 1 must place at rung 1 despite higher clears, got %s/%s"
                        % (res3["start_rung"], res3["cleared_prefix"]))

    # PARTIAL rung: ONE of two rung-2 items missed -> the whole rung is failed (placement-test.md: any miss fails)
    partial = dict(good)
    partial["QB1"] = _ans("who", ["from given as the gloss"])  # wrong answer (forbidden), reasoning present
    res4 = run_placement(bank, partial)
    if res4["start_rung"] != 2:
        failures.append("a single miss in rung 2 must fail the rung, got start %s" % res4["start_rung"])

    # SELF-REPORT IGNORED: a payload claiming passed/correct/cleared with a wrong answer must NOT clear
    selfrep = dict(good)
    selfrep["QB1"] = {"answer": "completely wrong", "reasoning": [], "passed": True, "correct": True, "cleared": True}
    res5 = run_placement(bank, selfrep)
    if res5["start_rung"] != 2:
        failures.append("a self-reported pass with a wrong answer must be ignored, got start %s" % res5["start_rung"])

    # TWO-VOTE without a second check: the hard rung-2 item is HELD -> rung 2 not cleared -> start at rung 2
    onecheck = dict(good)
    onecheck["QB2"] = _ans("man means who because the content letter carries fatha", ["the content-letter harakah read"])
    res6 = run_placement(bank, onecheck)
    if res6["start_rung"] != 2:
        failures.append("two-vote item with no second check must hold the rung, got start %s" % res6["start_rung"])

    # UNANSWERED items count as misses, never passes (empty answers map -> start at the lowest rung)
    res7 = run_placement(bank, {})
    if res7["start_rung"] != 1 or res7["cleared_prefix"] != []:
        failures.append("an empty answer set must place at the lowest rung, got %s/%s"
                        % (res7["start_rung"], res7["cleared_prefix"]))

    # DETERMINISM: identical inputs -> identical result JSON twice
    if json.dumps(run_placement(bank, good), sort_keys=True) != json.dumps(run_placement(bank, good), sort_keys=True):
        failures.append("non-deterministic placement output")

    # SOURCE-CLEAN: nothing emitted leaks (notes + every miss reason)
    for r_ in (res, res2, res3, res4, res5, res6, res7):
        if leak_sot.is_leak(r_["note"]):
            failures.append("result note leaks")
        for rs in r_["rung_summary"]:
            for it in rs["items"]:
                for reason in it["reasons"]:
                    if leak_sot.is_leak(reason):
                        failures.append("miss reason leaks: %r" % reason)

    # the SHIPPED sample must load, place an empty set at rung 1, and emit no leak
    sample = DEFAULT_BANK
    if os.path.exists(sample):
        sb = load_bank(sample)
        sres = run_placement(sb, {})
        if not sb:
            failures.append("shipped placement sample is empty")
        if sb and (sres["start_rung"] != sorted({_rung(r) for r in sb if _rung(r) is not None})[0]):
            failures.append("shipped sample empty-answer placement is not the lowest rung")
        if leak_sot.scan_obj(sres):
            failures.append("shipped sample result leaks: %s" % leak_sot.scan_obj(sres)[:3])
        # GUARD (adversarial F1): no shipped row may be CLEARED by a degenerate ONE-TOKEN answer. The passed-form +
        # required-reasoning together must need >1 discriminating token, so a vague answer that merely echoes one key
        # word ("from"/"root"/...) cannot clear a rung. For each row, try every significant token of its accepted
        # forms (and the empty answer) as a one-word answer+reasoning and assert grade() does NOT clear.
        for row in sb:
            toks = set()
            for f in [row.get("expected_answer", "")] + list(row.get("accepted_variants") or []):
                toks.update(RT._sig_tokens(f))
            for t in list(toks) + [""]:
                if RT.grade(row, {"answer": t, "reasoning": [t]})["cleared"]:
                    failures.append("placement row %r is single-token-clearable by %r (weak fixture)"
                                    % (row.get("id"), t))
                    break

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_placement_test self-test: content-graded (no self-report); rung cleared iff all items clear; "
              "lowest-uncleared-rung start; gap-below sinks higher clears; two-vote held; deterministic; source-clean")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
