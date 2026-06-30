#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_review_scheduler — a DETERMINISTIC review scheduler for the offline Fusha tutor (criticism 4).

WHY LEITNER (the DEFAULT, not SM-2/FSRS): the scheduler must be fully deterministic, reproducible, and parameter-free.
Leitner boxes are a pass/fail box ladder with fixed per-box intervals — no ease floats, no fitted parameters (FSRS
needs trained weights; deep-research confirms FSRS is unsuitable for a parameter-free offline tutor). SM-2 is also
deterministic but its ease-factor arithmetic is harder to audit; Leitner is the most auditable choice and maps
cleanly onto the repo's "a precise blank/PENDING beats a confident wrong" discipline.

SM-2-LITE (OPTIONAL, DEFAULT-OFF — mode="sm2"): an additive variant for callers who want graduated intervals.
It implements the canonical SuperMemo SM-2 spacing arithmetic (P. A. Woźniak, "Optimization of repetition spacing
in the practice of learning", SuperMemo SM-2, 1990 / supermemo.com/en/archives1990-2015/english/ol/sm2):
  * interval ladder: I(1)=1 day, I(2)=6 days, I(n)=round_up(I(n-1) * EF) for n>2;
  * ease factor EF starts at 2.5, updated by the SM-2 closed form EF' = EF + (0.1 - (5-q)*(0.08 + (5-q)*0.02)),
    floored at 1.3 (never below);
  * a sub-threshold response (SM-2's q<3) RESETS the repetition count so the next interval is I(1)=1.
It is DETERMINISTIC: q is derived from the SAME boolean grade outcome Leitner reads (full-pass -> q=5, hold -> q=3
no-advance, lapse -> q=1), NO fuzz, NO RNG, NO wall clock. SM-2 is purely additive — mode="leitner" stays
byte-identical to the original. State may carry ef/interval/reps for the sm2 path; box/due_day stay the API.

DETERMINISM CONTRACT (enforced by --self-test):
  * NO `random`, NO wall-clock inside the logic, NO interval fuzz. "now" is an explicit integer DAY INDEX passed by the
    caller. (deep-research wfns8dglb, 3-0: original SM-2 is RNG-free; Anki's SM-2 adds OPTIONAL fuzz — NOT adopted here.)
  * Identical (state, grade_result, now_day, mode) -> byte-identical next state. Two runs always agree.

THE HARD GATE (criticism 4 anti-pattern: "scheduler marking wrong-reason answers mastered") — enforced in BOTH modes:
  An item ADVANCES only on a FULL pass — `passed` AND `reasoning_passed` AND two-vote not pending AND no forbidden
  answer. A "right answer for the wrong reason" (passed but reasoning_failed) or a one-check hard-grammar item
  (two_vote_status == 'pending') is HELD (Leitner: same box; sm2: interval pinned to I(1)) and re-queued soon — it
  never climbs. A real miss (`passed` False) DEMOTES (Leitner: box 0; sm2: reps->0) and counts a lapse.

State is plain JSON (event-sourced / replayable by the runtime). This module only COMPUTES; it never writes files.
Stdlib only; dry-run. See parserplans/fusha-data-runtime-completion-pass/004 (P0-A).
"""
import argparse
import json
import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Box k -> interval in days until the item is due again. Box 0 = due next session (interval 0). Index = box number.
BOX_INTERVALS = (0, 1, 2, 4, 8, 16)
MAX_BOX = len(BOX_INTERVALS) - 1  # 5

# --- SM-2-lite constants (mode="sm2"; canonical SuperMemo SM-2, Woźniak 1990) ---
SM2_EF_INIT = 2.5    # initial ease factor for a fresh item
SM2_EF_FLOOR = 1.3   # EF is never allowed below this (SM-2 spec)
SM2_I1 = 1           # I(1) = 1 day
SM2_I2 = 6           # I(2) = 6 days
# SM-2 maps a quality q in 0..5 to an interval ladder; we derive q deterministically from the boolean grade outcome.
SM2_Q_FULL_PASS = 5  # full pass = perfect graded recall
SM2_Q_HOLD = 3       # right surface / owed reason / pending two-vote: at-threshold but NOT rewarded -> no advance
SM2_Q_LAPSE = 1      # a real miss = sub-threshold (q<3) -> reset

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


def _sm2_decision_to_quality(decision):
    """Deterministic map from the (shared) Leitner decision to an SM-2 quality grade q in 0..5.
    'promote' -> 5 (full pass); 'hold' -> 3 (at-threshold, no reward, no advance); 'lapse' -> 1 (sub-threshold)."""
    if decision == "promote":
        return SM2_Q_FULL_PASS
    if decision == "hold":
        return SM2_Q_HOLD
    return SM2_Q_LAPSE


def _sm2_ef_update(ef, q):
    """Canonical SM-2 closed-form ease-factor update (Woźniak 1990), floored at SM2_EF_FLOOR. Pure, deterministic.
    EF' = EF + (0.1 - (5-q)*(0.08 + (5-q)*0.02)); EF' = max(EF', 1.3)."""
    ef2 = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    return ef2 if ef2 >= SM2_EF_FLOOR else SM2_EF_FLOOR


def _sm2_interval(reps, prev_interval, ef):
    """SM-2 interval ladder: I(1)=1, I(2)=6, I(n)=round_up(I(n-1)*EF) for n>2. `reps` is the new repetition count
    (1-based: the count AFTER this successful review). Deterministic integer days, rounded UP (ceil) per spec."""
    if reps <= 1:
        return SM2_I1
    if reps == 2:
        return SM2_I2
    return math.ceil(int(prev_interval) * ef)  # round_up(I(n-1) * EF), per SM-2 spec; deterministic integer days


def schedule(state, grade_result, now_day, mode="leitner"):
    """Pure transition: (state, grade_result, now_day:int, mode) -> next state. Never mutates the input; never writes.

    mode="leitner" (DEFAULT, byte-identical to the original):
        promote -> box+1 (capped at MAX_BOX); hold -> same box, re-due after box-0 interval (soon);
        lapse -> box 0 + lapse. The new due_day = now_day + BOX_INTERVALS[new_box]. Deterministic.
    mode="sm2" (OPTIONAL SM-2-lite, additive): graduated SuperMemo SM-2 intervals on ef/interval/reps; the SAME hard
        gate applies — only a full pass advances the ladder; hold pins the interval to I(1) (no advance, refuses
        promotion exactly like Leitner); a real miss resets reps to 0 + counts a lapse. Deterministic, no fuzz/RNG.
    """
    if not isinstance(now_day, int):
        raise TypeError("now_day must be an explicit integer day index (no wall clock)")
    if mode not in ("leitner", "sm2"):
        raise ValueError("mode must be 'leitner' (default) or 'sm2', got %r" % (mode,))
    s = dict(state)
    decision = classify(grade_result)
    if mode == "leitner":
        box = int(s.get("box", 0))
        if decision == "promote":
            box = min(box + 1, MAX_BOX)
        elif decision == "hold":
            box = box                   # explicit: held, never promoted on wrong/owed reason
        else:  # lapse
            box = 0
            s["lapses"] = int(s.get("lapses", 0)) + 1
        # a held item should come back quickly (use box-0 interval, not its current box's long interval)
        interval = BOX_INTERVALS[0] if decision == "hold" else BOX_INTERVALS[box]
        s["box"] = box
        s["due_day"] = now_day + interval
        # `reps` in the Leitner path is a TOTAL review counter -> always +1.
        s["reps"] = int(s.get("reps", 0)) + 1
    else:  # mode == "sm2"
        q = _sm2_decision_to_quality(decision)
        ef = float(s.get("ef", SM2_EF_INIT))
        reps = int(s.get("reps", 0))          # SM-2 reps = count of CONSECUTIVE successful repetitions
        prev_interval = int(s.get("interval", 0))
        # MIGRATION GUARD: a state never sm2-scheduled (e.g. a Leitner state — it has no `interval` key, and its
        # `reps` is a TOTAL review counter, not SM-2 consecutive successes) must START the SM-2 ladder fresh. Without
        # this, prev_interval defaults to 0 and a promote with reps>2 computes ceil(0*EF)=0 -> a perpetually-due item.
        if "interval" not in s:
            reps = 0
            prev_interval = 0
        if decision == "promote":
            # a FULL pass advances the SM-2 ladder and rewards EF (q>=3 update).
            reps = reps + 1
            ef = _sm2_ef_update(ef, q)
            interval = int(_sm2_interval(reps, prev_interval, ef))
        elif decision == "hold":
            # right surface / owed reason / pending two-vote: REFUSE promotion exactly like Leitner. The SM-2
            # repetition count resets so the next interval is I(1), the item re-dues SOON, and EF is NOT rewarded.
            reps = 0
            interval = SM2_I1
            # EF left unchanged: a held item is neither a clean success (no reward) nor a counted lapse.
        else:  # lapse: sub-threshold (q<3) -> reset repetitions; EF still updated by the closed form (penalised).
            reps = 0
            ef = _sm2_ef_update(ef, q)
            interval = SM2_I1
            s["lapses"] = int(s.get("lapses", 0)) + 1
        s["ef"] = ef
        s["interval"] = interval
        s["due_day"] = now_day + interval
        s["reps"] = reps
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

    # 10. DEFAULT mode is byte-identical to explicit mode="leitner" (the additive guarantee)
    if (json.dumps(schedule(s0, gr(True), 10), sort_keys=True)
            != json.dumps(schedule(s0, gr(True), 10, mode="leitner"), sort_keys=True)):
        failures.append("default mode is not byte-identical to mode='leitner'")
    if json.dumps(schedule(s0, gr(True), 10), sort_keys=True) != json.dumps(a, sort_keys=True):
        failures.append("default Leitner output drifted from the original")

    # 11. an unknown mode is rejected (the sm2 path must not silently absorb a typo)
    try:
        schedule(new_state(), gr(True), 0, mode="fsrs")
        failures.append("schedule accepted an unknown mode")
    except ValueError:
        pass

    # ---- SM-2-lite (mode="sm2") assertions ----

    # 12. SM-2 determinism: identical inputs -> byte-identical output, twice
    s_sm = new_state()
    x = schedule(s_sm, gr(True), 100, mode="sm2")
    y = schedule(s_sm, gr(True), 100, mode="sm2")
    if json.dumps(x, sort_keys=True) != json.dumps(y, sort_keys=True):
        failures.append("non-deterministic sm2 schedule()")
    if s_sm != new_state():
        failures.append("sm2 schedule mutated the input state")

    # 13. full-pass interval ladder I(1)=1 -> I(2)=6 -> I(3)=round_up(6*EF). EF rises 2.5 -> 2.6 on q=5.
    p1 = schedule(new_state(), gr(True), 0, mode="sm2")
    if p1["interval"] != SM2_I1 or p1["reps"] != 1 or p1["due_day"] != 0 + SM2_I1:
        failures.append("sm2 first full pass should give I(1)=1, reps=1, got %s" % p1)
    if abs(p1["ef"] - 2.6) > 1e-9:
        failures.append("sm2 EF should rise to 2.6 on q=5 full pass, got %s" % p1["ef"])
    p2 = schedule(p1, gr(True), p1["due_day"], mode="sm2")
    if p2["interval"] != SM2_I2 or p2["reps"] != 2:
        failures.append("sm2 second full pass should give I(2)=6, reps=2, got %s" % p2)
    p3 = schedule(p2, gr(True), p2["due_day"], mode="sm2")
    expected_i3 = math.ceil(SM2_I2 * p2["ef"])  # round_up(6 * EF)
    if p3["interval"] != expected_i3 or p3["reps"] != 3:
        failures.append("sm2 third full pass should give round_up(6*EF)=%s, got %s" % (expected_i3, p3))
    if p3["interval"] <= p2["interval"]:
        failures.append("sm2 intervals must grow on consecutive full passes: %s !> %s"
                        % (p3["interval"], p2["interval"]))

    # 14. wrong-reason / pending two-vote does NOT advance the sm2 ladder (refuses promotion like Leitner):
    #     interval pinned to I(1), reps reset to 0, outcome 'hold', EF unchanged, no lapse counted.
    held_in = schedule(p3, gr(True), p3["due_day"], mode="sm2")          # advance once more first
    h_wr = schedule(held_in, gr(True, reasoning=False), 200, mode="sm2")
    if h_wr["last_outcome"] != "hold" or h_wr["interval"] != SM2_I1 or h_wr["reps"] != 0:
        failures.append("sm2 wrong-reason must HOLD (interval->I1, reps->0), got %s" % h_wr)
    if abs(h_wr["ef"] - held_in["ef"]) > 1e-9:
        failures.append("sm2 hold must not change EF, got %s vs %s" % (h_wr["ef"], held_in["ef"]))
    if h_wr.get("lapses", 0) != held_in.get("lapses", 0):
        failures.append("sm2 hold must not count a lapse")
    h_pv = schedule(p3, gr(True, two_vote="pending"), 210, mode="sm2")
    if h_pv["last_outcome"] != "hold" or h_pv["reps"] != 0:
        failures.append("sm2 pending two-vote must HOLD, got %s" % h_pv)

    # 15. q<3 (a real miss) RESETS repetitions to I(1) and counts a lapse
    miss = schedule(p3, gr(False), 220, mode="sm2")
    if miss["last_outcome"] != "lapse" or miss["reps"] != 0 or miss["interval"] != SM2_I1:
        failures.append("sm2 miss must reset reps->0 + interval->I(1), got %s" % miss)
    if miss["lapses"] != int(p3.get("lapses", 0)) + 1:
        failures.append("sm2 miss must count a lapse, got %s" % miss)

    # 16. EF is FLOORED at 1.3 — repeated misses must never drive EF below the floor
    low = {"box": 0, "due_day": 0, "reps": 0, "lapses": 0, "ef": 1.3, "interval": 1}
    floored = schedule(low, gr(False), 0, mode="sm2")
    if floored["ef"] < SM2_EF_FLOOR - 1e-12:
        failures.append("sm2 EF must be floored at 1.3, got %s" % floored["ef"])
    # drive many misses from default and confirm the floor holds
    st = new_state()
    for _ in range(20):
        st = schedule(st, gr(False), 0, mode="sm2")
    if st["ef"] < SM2_EF_FLOOR - 1e-12:
        failures.append("sm2 EF dropped below 1.3 after repeated misses, got %s" % st["ef"])

    # 17. MIGRATION GUARD: a Leitner-scheduled state (no `interval` key; `reps` is a total counter) switched into
    #     mode="sm2" must START the ladder fresh — interval >= 1 (never 0 -> perpetually due) on a promote.
    leit = {"box": 3, "due_day": 99, "reps": 5, "lapses": 0}   # a typical Leitner state, no interval/ef keys
    mig = schedule(leit, gr(True), 50, mode="sm2")
    if mig["interval"] < 1 or mig["due_day"] <= 50 or mig["reps"] != 1:
        failures.append("sm2 migration of a Leitner state must start fresh (interval>=1, reps=1), got %s" % mig)

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_review_scheduler self-test: deterministic Leitner (DEFAULT, unchanged); full-pass-only "
              "promotion; wrong-reason/pending-two-vote HOLD; miss demotes; caps; due-selection ordered; "
              "+SM-2-lite (mode='sm2', additive): deterministic, I(1)=1->I(2)=6->round_up(I*EF), hold/pending no-advance, "
              "q<3 resets reps, EF floored 1.3")
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
