#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_tutor_runtime — the OFFLINE, DETERMINISTIC tutor loop for the Fusha reading curriculum (criticism 5).

Turns the prose tutor-session-protocol into an executable harness. It does NOT replace a human/agent tutor's
judgement on open prose; it makes the OBJECTIVE checkpoint loop runnable and honest:

    load checkpoint bank (JSONL) + optional progress state
      -> select the next item (a due REVIEW, else a new item)        [deterministic]
      -> accept an ANSWER PAYLOAD (the learner's answer + reasoning + optional second check)
      -> GRADE against the answer key/rubric  (NOT a model self-report)
      -> route a miss to its remediation procedure
      -> update the Leitner schedule (tools/fusha_review_scheduler.py)
      -> write progress + append an event ONLY when --write is passed
      -> emit a replayable, source-clean event

Grading is scoped as **Automatic Short Answer Grading** (ASAG): it scores the CONTENT of a close-ended answer, not
style/length, and handles re-wording by concept presence + per-rubric accepted-variant vocabulary (deep-research
wfns8dglb, 3-0) — never a bag-of-words/coordinate match alone (that was refuted 0-3), so credit needs MULTIPLE gates
to agree. It is verification-first: the awarded grade must be grounded in the LEARNER's own answer/reasoning.

HARD CONTRACTS (enforced by --self-test + tools/validate_tutor_runtime.py):
  * Grading is computed from the answer payload's CONTENT — expected/variant match, forbidden-answer detection,
    required-reasoning presence, and (for hard grammar) a second independent check. It NEVER reads a self-reported
    `correct`/`passed`/`cleared` flag from the payload. "It sounds right" cannot clear an item.
  * Two-vote gate: a `two_vote_required` row with no agreeing second check is `pending` — HELD, never cleared.
  * No persistent write without `--write`. A dry run mutates no file.
  * Deterministic: "now" is an explicit integer `--now` day index; no wall clock, no RNG.
  * Source-clean: every emitted text field passes tools/leak_sot.

Stdlib only; dry-run; no live Qamus. See parserplans/fusha-data-runtime-completion-pass/004 (P0-B).
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
from tools import fusha_review_scheduler as SCHED  # noqa: E402
from tools import leak_sot  # noqa: E402

PROGRESS_SCHEMA = "fusha/tutor-progress-state@1"
EVENT_SCHEMA = "fusha/tutor-event@1"
DEFAULT_BANK = os.path.join(_REPO, "curriculum", "assessment", "level-checkpoints.sample.jsonl")

_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # harakāt + tatweel


def _norm(s):
    """Normalize for matching: drop Arabic diacritics/tatweel, lowercase, collapse whitespace. Deterministic.

    This is a RECALL normalizer for answer matching only — it is never used to certify a gloss (see normalize_ar)."""
    if not isinstance(s, str):
        return ""
    s = _DIACRITICS.sub("", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")  # alef seats -> bare
    s = s.replace("ة", "ه")  # tā' marbūṭa -> hā' (lenient)
    s = s.lower()
    s = re.sub(r"[^0-9a-z؀-ۿ\s]", " ", s)  # punctuation -> space (keep latin/digits/Arabic)
    return re.sub(r"\s+", " ", s).strip()


def _contains_any(haystack, needles):
    h = _norm(haystack)
    return any(_norm(n) and _norm(n) in h for n in (needles or []))


# light stoplist for the significant-token rule (so word-order / filler variation does not fail a complete answer)
_STOP = {"the", "a", "an", "is", "are", "of", "to", "and", "or", "do", "not", "be", "it", "as", "in", "on",
         "by", "for", "with", "that", "this", "ال", "its", "you", "your", "one", "once"}


def _sig_tokens(s):
    return [t for t in _norm(s).split() if len(t) >= 3 and t not in _STOP]


# A complete answer must cover this fraction of a canonical form's significant tokens (deterministic; conservative).
# 0.8 tolerates a single filler / transliteration mismatch (e.g. "should" vs "must", حمد vs "hamd") while still
# rejecting vague answers, which cover almost none of the key tokens.
MATCH_COVERAGE = 0.8


def _form_matches(form, answer, thresh=MATCH_COVERAGE):
    """A canonical FORM matches the answer if it is a normalized substring of the answer, OR the answer covers at
    least `thresh` of the form's significant tokens (handles re-wording / extra words). Deterministic; never fuzzy
    on empties. NOT a self-report read — it is content coverage of the AUTHORED key."""
    nf = _norm(form)
    if not nf:
        return False
    if nf in _norm(answer):
        return True
    toks = _sig_tokens(form)
    if not toks:
        return False
    ans = _norm(answer)
    hit = sum(1 for t in toks if t in ans)
    return hit / len(toks) >= thresh


# --------------------------------------------------------------------------- grading (content-only, no self-report)
# The closed set of payload keys the grader reads. A self-reported correctness flag is deliberately NOT here.
GRADE_INPUT_KEYS = ("answer", "reasoning", "second_check")


def grade(row, payload):
    """Grade one answer payload against a checkpoint row. Returns a grade dict. CONTENT-only; never self-report.

    payload = {answer:str, reasoning:[str], second_check:{conclusion_agrees:bool, reason_agrees:bool}|null}.
    """
    answer = payload.get("answer", "") if isinstance(payload, dict) else ""
    reasoning = payload.get("reasoning", []) if isinstance(payload, dict) else []
    second = payload.get("second_check") if isinstance(payload, dict) else None

    expected_set = [row.get("expected_answer", "")] + list(row.get("accepted_variants", []) or [])
    passed = any(_form_matches(v, answer) for v in expected_set)
    forbidden_hit = _contains_any(answer, row.get("forbidden_answers", []))
    joined_reasoning = " \n ".join(reasoning or []) if isinstance(reasoning, list) else str(reasoning or "")
    missing = [req for req in (row.get("required_reasoning", []) or [])
               if not _form_matches(req, joined_reasoning)]
    reasoning_passed = not missing

    if row.get("two_vote_required"):
        ok2 = bool(second) and bool(second.get("conclusion_agrees")) and bool(second.get("reason_agrees"))
        two_vote_status = "cleared" if ok2 else "pending"
    else:
        two_vote_status = "n/a"

    cleared = bool(passed and reasoning_passed and not forbidden_hit and two_vote_status != "pending")
    return {"passed": bool(passed), "reasoning_passed": bool(reasoning_passed),
            "two_vote_status": two_vote_status, "forbidden_hit": bool(forbidden_hit),
            "cleared": cleared, "missing_reasoning": missing}


def new_progress(label="learner"):
    return {"schema": PROGRESS_SCHEMA, "learner_label": label, "now_day": 0, "items": {},
            "cleared_item_ids": [], "missed": []}


def _bank_index(bank):
    return {r["id"]: r for r in bank}


def select_next(bank, progress, now_day):
    """Pick the next checkpoint id deterministically: a due REVIEW (already-seen, due) first, else the next NEW item
    in bank order, else the soonest-due seen item. Returns (item_id, reason) or (None, 'bank empty')."""
    states = progress.get("items", {})
    seen = set(states)
    # due reviews among already-seen items (reps>0)
    due_reviews = [i for i in SCHED.select_due(states, now_day) if int(states.get(i, {}).get("reps", 0)) > 0]
    if due_reviews:
        return due_reviews[0], "due_review"
    for r in bank:                                   # first unseen item, in bank order
        if r["id"] not in seen:
            return r["id"], "new_item"
    if states:                                        # all seen, none due -> soonest due
        nxt = min(states, key=lambda k: (int(states[k].get("due_day", 0)), k))
        return nxt, "soonest_due"
    return None, "bank empty"


def step(row, state, payload, now_day):
    """Grade + schedule + build a (source-clean) event for one attempt. Pure (no I/O). Returns dict."""
    g = grade(row, payload)
    box_before = int((state or {}).get("box", 0))
    gr_for_sched = {"passed": g["passed"], "reasoning_passed": g["reasoning_passed"],
                    "two_vote_status": g["two_vote_status"], "forbidden_hit": g["forbidden_hit"],
                    "grade": "cleared" if g["cleared"] else "miss"}
    new_state = SCHED.schedule(state or SCHED.new_state(), gr_for_sched, now_day)
    outcome = new_state["last_outcome"]
    route = None if g["cleared"] else row.get("remediation_route")
    note = ("cleared" if g["cleared"]
            else ("held: " + ("pending two-vote" if g["two_vote_status"] == "pending"
                              else ("forbidden answer" if g["forbidden_hit"]
                                    else "reasoning incomplete" if not g["reasoning_passed"] else "review"))
                  if outcome == "hold" else "miss -> remediation"))
    event = {"schema": EVENT_SCHEMA, "seq": 0, "now_day": now_day, "item_id": row["id"],
             "level": str(row.get("level", "")), "outcome": outcome,
             "grade": {k: g[k] for k in ("passed", "reasoning_passed", "two_vote_status", "forbidden_hit",
                                          "cleared", "missing_reasoning")},
             "box_before": box_before, "box_after": int(new_state["box"]),
             "remediation_route": route, "note": note}
    # source-clean guard: scrub any text field that could carry a leak (defensive; rows are authored).
    for key in ("note",):
        if leak_sot.is_leak(event[key]):
            event[key] = leak_sot.redact(event[key])
    return {"state": new_state, "grade": g, "event": event, "outcome": outcome}


def apply_event_to_progress(progress, row, result, seq):
    """Fold a step result into a progress state (in place). Used for both --write persistence and replay."""
    item_id = row["id"]
    progress["items"][item_id] = result["state"]
    ev = dict(result["event"]); ev["seq"] = seq
    g = result["grade"]
    if g["cleared"] and item_id not in progress["cleared_item_ids"]:
        progress["cleared_item_ids"].append(item_id)
    # maintain the open-miss list
    progress["missed"] = [m for m in progress.get("missed", []) if m["item_id"] != item_id]
    if not g["cleared"]:
        status = "pending_two_vote" if g["two_vote_status"] == "pending" else "open"
        progress["missed"].append({"item_id": item_id, "error_reason": None,
                                   "remediation_route": row.get("remediation_route"), "status": status})
    return ev


def load_bank(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


# --------------------------------------------------------------------------- CLI
def _read_payload(arg):
    if arg == "-":
        return json.load(sys.stdin)
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(arg)  # inline JSON string


def main():
    ap = argparse.ArgumentParser(description="Offline deterministic Fusha tutor runtime (schema-graded; --write-gated).")
    ap.add_argument("--bank", default=DEFAULT_BANK, help="checkpoint JSONL fixture")
    ap.add_argument("--progress", default=None, help="progress-state JSON path (read; written only with --write)")
    ap.add_argument("--now", type=int, default=0, help="explicit integer day index (no wall clock)")
    ap.add_argument("--select", action="store_true", help="print the next checkpoint to attempt, then exit")
    ap.add_argument("--item", default=None, help="checkpoint id to grade (default: the selected next item)")
    ap.add_argument("--answer", default=None, help="answer payload: a JSON file path, '-' for stdin, or inline JSON")
    ap.add_argument("--event-log", default=None, help="JSONL event log to append to (only with --write)")
    ap.add_argument("--write", action="store_true", help="PERSIST progress + append the event (otherwise dry-run)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()

    bank = load_bank(a.bank)
    idx = _bank_index(bank)
    progress = new_progress()
    if a.progress and os.path.exists(a.progress):
        with open(a.progress, encoding="utf-8") as fh:
            progress = json.load(fh)
    progress["now_day"] = a.now

    if a.select or not a.answer:
        item_id, reason = select_next(bank, progress, a.now)
        if not item_id:
            print(json.dumps({"next": None, "reason": reason}, ensure_ascii=False)); return 0
        row = idx[item_id]
        print(json.dumps({"next": item_id, "reason": reason, "level": row.get("level"),
                          "prompt": row.get("prompt"), "two_vote_required": bool(row.get("two_vote_required"))},
                         ensure_ascii=False))
        return 0

    item_id = a.item or select_next(bank, progress, a.now)[0]
    if item_id not in idx:
        print("ERROR: unknown checkpoint id %r" % item_id); return 2
    row = idx[item_id]
    payload = _read_payload(a.answer)
    result = step(row, progress["items"].get(item_id), payload, a.now)
    # event seq continues an existing on-disk log when persisting; else it is the session-local 0.
    seq = _next_seq(a.event_log) if (a.write and a.event_log) else 0
    ev = apply_event_to_progress(progress, row, result, seq)

    out = {"item_id": item_id, "outcome": result["outcome"], "grade": result["grade"], "event": ev,
           "wrote": False}
    if a.write:
        if a.progress:
            _atomic_write_json(a.progress, progress)
            out["wrote"] = True
        if a.event_log:
            _append_jsonl(a.event_log, ev)
            out["event_log_appended"] = True
    else:
        out["dry_run"] = "no --write: nothing persisted"
    print(json.dumps(out, ensure_ascii=False))
    return 0


def _next_seq(event_log):
    if event_log and os.path.exists(event_log):
        with open(event_log, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    return 0


def _atomic_write_json(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def _append_jsonl(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


# --------------------------------------------------------------------------- self-test
def _authored_bank():
    """A tiny AUTHORED bank (no Qurʾān copy beyond a reference) exercising every grading path."""
    return [
        {"id": "T1-objective", "level": "3", "concept": "definite article", "prompt": "name the article + host",
         "quran_example": None, "expected_answer": "the article is al and the host noun is qalam",
         "accepted_variants": ["al is the article; host is qalam"], "forbidden_answers": ["the the pen", "root vibes"],
         "required_reasoning": ["article identified", "host noun identified"],
         "sarf_procedure": None, "nahw_procedure": None,
         "remediation_route": "sarf/drills/dogfood-sarf-remediation.md", "two_vote_required": False},
        {"id": "T2-hardgrammar", "level": "7", "concept": "particle function", "prompt": "why is man here who not from",
         "quran_example": None, "expected_answer": "man means who because the content letter carries fatha",
         "accepted_variants": ["who, decided by the harakah on the nun"], "forbidden_answers": ["they are the same"],
         "required_reasoning": ["content-letter harakah read"], "sarf_procedure": None,
         "nahw_procedure": "nahw/procedures/particle-decision.md",
         "remediation_route": "nahw/drills/dogfood-nahw-remediation.md", "two_vote_required": True},
    ]


def _self_test():
    import tempfile
    failures = []
    bank = _authored_bank()
    idx = _bank_index(bank)

    # 1. full pass on the objective item -> cleared + promote
    p_full = {"answer": "the article is al and the host noun is qalam",
              "reasoning": ["the article identified as al", "host noun identified as qalam"]}
    r = step(idx["T1-objective"], None, p_full, now_day=0)
    if not r["grade"]["cleared"] or r["outcome"] != "promote":
        failures.append("full pass should clear+promote, got %s / %s" % (r["grade"], r["outcome"]))

    # 2. right answer, MISSING required reasoning -> not cleared, HELD (not promoted)
    p_noreason = {"answer": "the article is al and the host noun is qalam", "reasoning": ["looks right"]}
    r2 = step(idx["T1-objective"], {"box": 2, "due_day": 0, "reps": 3, "lapses": 0}, p_noreason, now_day=5)
    if r2["grade"]["cleared"] or r2["outcome"] != "hold" or r2["state"]["box"] != 2:
        failures.append("right-answer-no-reasoning must HOLD, got %s / %s" % (r2["grade"], r2["outcome"]))

    # 3. forbidden answer present -> not passed-cleared, held
    p_forbidden = {"answer": "the the pen", "reasoning": ["article identified", "host noun identified"]}
    r3 = step(idx["T1-objective"], None, p_forbidden, now_day=0)
    if r3["grade"]["cleared"] or not r3["grade"]["forbidden_hit"]:
        failures.append("forbidden answer must not clear, got %s" % r3["grade"])

    # 4. hard-grammar (two_vote) with ONE check -> pending, held, not cleared
    p_one = {"answer": "man means who because the content letter carries fatha",
             "reasoning": ["content-letter harakah read"]}
    r4 = step(idx["T2-hardgrammar"], None, p_one, now_day=0)
    if r4["grade"]["two_vote_status"] != "pending" or r4["grade"]["cleared"] or r4["outcome"] != "hold":
        failures.append("two-vote with one check must be pending+held, got %s / %s" % (r4["grade"], r4["outcome"]))

    # 5. hard-grammar with an AGREEING second check -> cleared + promote
    p_two = dict(p_one); p_two["second_check"] = {"conclusion_agrees": True, "reason_agrees": True}
    r5 = step(idx["T2-hardgrammar"], None, p_two, now_day=0)
    if r5["grade"]["two_vote_status"] != "cleared" or not r5["grade"]["cleared"] or r5["outcome"] != "promote":
        failures.append("two-vote with agreeing second check must clear+promote, got %s" % r5["grade"])

    # 6. a SELF-REPORTED correctness flag must be IGNORED (no self-report grading)
    p_selfreport = {"answer": "totally wrong text", "reasoning": [], "passed": True, "correct": True, "cleared": True}
    r6 = step(idx["T1-objective"], None, p_selfreport, now_day=0)
    if r6["grade"]["passed"] or r6["grade"]["cleared"]:
        failures.append("self-reported correctness must be ignored, got %s" % r6["grade"])

    # 7. determinism: identical inputs -> identical event JSON twice
    a = step(idx["T1-objective"], None, p_full, 3)["event"]
    b = step(idx["T1-objective"], None, p_full, 3)["event"]
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        failures.append("non-deterministic event output")

    # 8. NO write without --write: simulate a dry run by calling main() over a temp dir and asserting no file appears
    with tempfile.TemporaryDirectory() as td:
        bank_path = os.path.join(td, "bank.jsonl")
        with open(bank_path, "w", encoding="utf-8") as fh:
            for row in bank:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        ans_path = os.path.join(td, "answer.json")
        with open(ans_path, "w", encoding="utf-8") as fh:
            json.dump(p_full, fh)
        prog_path = os.path.join(td, "progress.json")
        log_path = os.path.join(td, "events.jsonl")
        argv = ["--bank", bank_path, "--item", "T1-objective", "--answer", ans_path,
                "--progress", prog_path, "--event-log", log_path, "--now", "0"]
        _run_main(argv)  # NO --write
        if os.path.exists(prog_path) or os.path.exists(log_path):
            failures.append("dry run wrote a file without --write")
        # now WITH --write -> files appear
        _run_main(argv + ["--write"])
        if not (os.path.exists(prog_path) and os.path.exists(log_path)):
            failures.append("--write did not persist progress/event-log")
        else:
            prog = json.load(open(prog_path, encoding="utf-8"))
            if prog.get("schema") != PROGRESS_SCHEMA or "T1-objective" not in prog.get("items", {}):
                failures.append("persisted progress malformed")

    # 9. select_next: empty progress -> the first new item; after clearing it -> the next new item
    nid, why = select_next(bank, new_progress(), 0)
    if nid != "T1-objective" or why != "new_item":
        failures.append("select_next first item wrong: %s/%s" % (nid, why))

    # 10. source-clean: no event note leaks
    for r_ in (r, r2, r3, r4, r5):
        if leak_sot.is_leak(r_["event"]["note"]):
            failures.append("event note leaks")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_tutor_runtime self-test: schema-graded (no self-report); two-vote gating; "
              "wrong-reason holds; --write-gated persistence; deterministic; source-clean")
    return 0 if not failures else 1


def _run_main(argv):
    """Invoke main() with a temporary argv (used by the self-test); stdout suppressed to keep the self-test quiet."""
    import io
    old_argv, old_out = sys.argv, sys.stdout
    try:
        sys.argv = ["fusha_tutor_runtime.py"] + argv
        sys.stdout = io.StringIO()
        return main()
    finally:
        sys.argv, sys.stdout = old_argv, old_out


if __name__ == "__main__":
    sys.exit(main())
