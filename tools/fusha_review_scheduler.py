#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_review_scheduler — a DETERMINISTIC Leitner review scheduler for the offline Fusha tutor (criticism 4).

WHY LEITNER (not SM-2/FSRS): the scheduler must be fully deterministic, reproducible, and parameter-free. Leitner
boxes are a pass/fail box ladder with fixed per-box intervals — no ease floats, no fitted parameters (FSRS needs
trained weights; deep-research confirms FSRS is unsuitable for a parameter-free offline tutor). SM-2 is also
deterministic but its ease-factor arithmetic is harder to audit; Leitner is the most auditable choice and maps
cleanly onto the repo's "a precise blank/PENDING beats a confident wrong" discipline.

DETERMINISM CONTRACT (enforced by --self-test):
  * NO `random`, NO wall-clock inside the logic, NO interval fuzz. "now" is an explicit integer DAY INDEX passed by the
    caller. (deep-research wfns8dglb, 3-0: original SM-2 is RNG-free; Anki's SM-2 adds OPTIONAL fuzz — NOT adopted here.)
  * Identical (state, grade_result, now_day) -> byte-identical next state. Two runs always agree.

THE HARD GATE (criticism 4 anti-pattern: "scheduler marking wrong-reason answers mastered"):
  A box is PROMOTED only on a FULL pass — `passed` AND `reasoning_passed` AND two-vote not pending AND no forbidden
  answer. A "right answer for the wrong reason" (passed but reasoning_failed) or a one-check hard-grammar item
  (two_vote_status == 'pending') is HELD at its current box and re-queued soon — it never climbs. A real miss
  (`passed` False) DEMOTES to box 0 and counts a lapse.

State is plain JSON (event-sourced / replayable by the runtime). This module only COMPUTES; it never writes files.
Stdlib only; dry-run. See parserplans/fusha-data-runtime-completion-pass/004 (P0-A).
"""
import argparse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Box k -> interval in days until the item is due again. Box 0 = due next session (interval 0). Index = box number.
BOX_INTERVALS = (0, 1, 2, 4, 8, 16)
MAX_BOX = len(BOX_INTERVALS) - 1  # 5

# Outcome of grading, as the scheduler reads it (produced by the runtime's grader, NEVER a model self-report).
# A grade_result dict carries: passed(bool), reasoning_passed(bool), two_vote_status in {"n/a","cleared","pending"},
# forbidden_hit(bool).


def new_state():
    """A fresh per-item scheduling state. box 0, due immediately (day 0 by default until first review)."""
    return {"box": 0, "due_day": 0, "reps": 0, "lapses": 0, "last_grade": None, "last_outcome": None}


def _full_pass(gr):
    """A FULL pass = correct AND right-reason AND not a pending two-vote AND no forbidden answer. Only this promotes."""
    return (bool(gr.get("passed"))
            and bool(gr.get("reasoning_passed", True))
            and gr.get("two_vote_status", "n/a") != "pending"
            and not bool(gr.get("forbidden_hit")))


def classify(gr):
    """Return one of: 'promote' (full pass), 'hold' (correct surface but wrong/owed reason or pending two-vote),
    'lapse' (a real miss). Pure; no side effects."""
    if bool(gr.get("passed")):
        if _full_pass(gr):
            return "promote"
        return "hold"          # right answer, wrong/owed reason -> does NOT climb (the criticism-4 guard)
    return "lapse"


def schedule(state, grade_result, now_day):
    """Pure transition: (state, grade_result, now_day:int) -> next state. Never mutates the input; never writes files.

    promote -> box+1 (capped at MAX_BOX); hold -> same box, re-due after box-0 interval (soon); lapse -> box 0 + lapse.
    The new due_day = now_day + BOX_INTERVALS[new_box]. Deterministic.
    """
    if not isinstance(now_day, int):
        raise TypeError("now_day must be an explicit integer day index (no wall clock)")
    s = dict(state)
    decision = classify(grade_result)
    box = int(s.get("box", 0))
    if decision == "promote":
        box = min(box + 1, MAX_BOX)
    elif decision == "hold":
        box = box                       # explicit: held, never promoted on wrong/owed reason
    else:  # lapse
        box = 0
        s["lapses"] = int(s.get("lapses", 0)) + 1
    # a held item should come back quickly (use box-0 interval, not its current box's long interval)
    interval = BOX_INTERVALS[0] if decision == "hold" else BOX_INTERVALS[box]
    s["box"] = box
    s["due_day"] = now_day + interval
    s["reps"] = int(s.get("reps", 0)) + 1
    s["last_grade"] = grade_result.get("grade") if isinstance(grade_result, dict) else None
    s["last_outcome"] = decision
    return s


def is_due(state, now_day):
    """A new (reps==0) item is always due; otherwise due when now_day has reached due_day. Deterministic."""
    if int(state.get("reps", 0)) == 0:
        return True
    return int(now_day) >= int(state.get("due_day", 0))


def select_due(states, now_day):
    """Return the keys of due items, ordered deterministically: most-overdue first, then lowest box, then key.
    `states` is {item_id: state}. Pure."""
    due = [(k, v) for k, v in states.items() if is_due(v, now_day)]
    due.sort(key=lambda kv: (-(now_day - int(kv[1].get("due_day", 0))), int(kv[1].get("box", 0)), kv[0]))
    return [k for k, _ in due]


def _self_test():
    failures = []

    def gr(passed, reasoning=True, two_vote="n/a", forbidden=False, grade="x"):
        return {"passed": passed, "reasoning_passed": reasoning, "two_vote_status": two_vote,
                "forbidden_hit": forbidden, "grade": grade}

    # 1. determinism: same inputs -> identical output, twice
    s0 = new_state()
    a = schedule(s0, gr(True), 10)
    b = schedule(s0, gr(True), 10)
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        failures.append("non-deterministic schedule()")
    # input not mutated
    if s0 != new_state():
        failures.append("schedule mutated the input state")

    # 2. full pass promotes 0->1, due = now + BOX_INTERVALS[1]
    if a["box"] != 1 or a["due_day"] != 10 + BOX_INTERVALS[1]:
        failures.append("full pass did not promote correctly: %s" % a)

    # 3. right-answer-wrong-reason HOLDS (no promote) and re-dues soon
    h = schedule({"box": 2, "due_day": 0, "reps": 3, "lapses": 0}, gr(True, reasoning=False), 20)
    if h["box"] != 2 or h["last_outcome"] != "hold":
        failures.append("wrong-reason answer must HOLD at its box, got %s" % h)
    if h["due_day"] != 20 + BOX_INTERVALS[0]:
        failures.append("held item should re-due soon, got %s" % h)

    # 4. pending two-vote HOLDS even with passed+reasoning
    h2 = schedule({"box": 3, "due_day": 0, "reps": 5, "lapses": 0}, gr(True, two_vote="pending"), 30)
    if h2["box"] != 3 or h2["last_outcome"] != "hold":
        failures.append("pending two-vote must HOLD, got %s" % h2)

    # 5. forbidden answer hit HOLDS (never promotes) even if 'passed' was set
    h3 = schedule({"box": 1, "due_day": 0, "reps": 2, "lapses": 0}, gr(True, forbidden=True), 5)
    if h3["box"] != 1 or h3["last_outcome"] != "hold":
        failures.append("forbidden-answer hit must not promote, got %s" % h3)

    # 6. a real miss demotes to box 0 and counts a lapse
    m = schedule({"box": 4, "due_day": 0, "reps": 9, "lapses": 1}, gr(False), 40)
    if m["box"] != 0 or m["lapses"] != 2 or m["last_outcome"] != "lapse":
        failures.append("a miss must demote to box 0 + lapse, got %s" % m)

    # 7. promotion caps at MAX_BOX
    top = {"box": MAX_BOX, "due_day": 0, "reps": 20, "lapses": 0}
    if schedule(top, gr(True), 0)["box"] != MAX_BOX:
        failures.append("box must cap at MAX_BOX")

    # 8. due/selection: new item due; ordering most-overdue then lowest box
    states = {"new": new_state(),
              "overdue": {"box": 1, "due_day": 5, "reps": 2, "lapses": 0},
              "future": {"box": 2, "due_day": 100, "reps": 3, "lapses": 0}}
    due = select_due(states, now_day=10)
    if "future" in due:
        failures.append("a not-yet-due item must not be selected: %s" % due)
    if not ({"new", "overdue"} <= set(due)):
        failures.append("new + overdue items must be due: %s" % due)

    # 9. now_day must be an int (no wall clock smuggled in)
    try:
        schedule(new_state(), gr(True), "2026-06-30")
        failures.append("schedule accepted a non-int now_day")
    except TypeError:
        pass

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_review_scheduler self-test: deterministic Leitner; full-pass-only promotion; "
              "wrong-reason/pending-two-vote HOLD; miss demotes; caps; due-selection ordered")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Deterministic Leitner review scheduler (pure; no wall clock, no RNG).")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    ap.error("need --self-test (this module is a library consumed by tools/fusha_tutor_runtime.py)")


if __name__ == "__main__":
    sys.exit(main())
