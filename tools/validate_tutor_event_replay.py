#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_tutor_event_replay — REPLAY a tutor event log and prove it reconstructs the persisted progress (P1-6).

Event sourcing only holds if the append-only event log is the truth: replaying the events over the SAME bank +
answer payloads must rebuild the EXACT progress state the runtime persisted. This validator checks that invariant
for tools/fusha_tutor_runtime.py — and, just as importantly, FAILs when the log has been TAMPERED (a flipped grade,
a re-ordered `seq`, an edited box, a substituted item) so a falsified history cannot pass as authentic.

WHAT IT PROVES (all enforced by --self-test):
  * REPLAY DETERMINISM — folding each event's recomputed `step()` (recorded now_day + the matching answer payload)
    into a fresh new_progress() yields progress BYTE-IDENTICAL to the runtime's persisted JSON.
  * EVENT FIDELITY — the event the runtime emitted must equal the event replay recomputes from the payload (same
    grade, outcome, box_before/after, route, note). A tampered grade/box/outcome is therefore caught.
  * LOG WELL-FORMEDNESS — `seq` is 0,1,2,… contiguous; each event validates against the tutor-event schema's
    required shape; every item_id exists in the bank; `box_before` chains from the prior box for that item.
  * SOURCE-CLEAN — every emitted text field still passes tools/leak_sot (a tampered note can't smuggle a leak in).

It is a CHECKER: it COMPUTES and compares, never writes a live file and never mutates the bank/log. The replay is
done purely in memory via the runtime's own step()/apply_event_to_progress()/new_progress() — single source of the
folding logic, so the validator can never drift from the runtime it certifies.

Stdlib only; deterministic (no wall clock, no RNG; now_day comes from each event). No network, no writes, no live
Qamus. CLI: --bank B --event-log L --progress P --payloads PAY.json | --self-test.
See parserplans/fusha-data-runtime-completion-pass/004 (P1-6).
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import fusha_tutor_runtime as RT  # noqa: E402
from tools import leak_sot  # noqa: E402

# the recorded-vs-recomputed event fields that must agree for the history to be authentic
_EVENT_KEYS = ("schema", "now_day", "item_id", "level", "outcome", "grade",
               "box_before", "box_after", "remediation_route", "note")
# every text field of an event that must stay source-clean
_TEXT_KEYS = ("item_id", "level", "remediation_route", "note")
# the closed schema of a tutor-event (mirrors qamus/schemas/tutor-event.schema.json `required`)
_REQUIRED = ("schema", "seq", "now_day", "item_id", "level", "outcome", "grade", "box_before", "box_after")
_OUTCOMES = ("promote", "hold", "lapse")


def _canon(obj):
    """Deterministic canonical JSON for byte-identity comparison (matches the runtime's persisted sort_keys form)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _shape_errors(ev):
    """Schema-shape errors for one event (required keys, enum, non-negative ints, grade sub-shape). Pure."""
    errs = []
    for k in _REQUIRED:
        if k not in ev:
            errs.append("seq %s: missing required field %r" % (ev.get("seq"), k))
    if ev.get("schema") != RT.EVENT_SCHEMA:
        errs.append("seq %s: schema %r != %r" % (ev.get("seq"), ev.get("schema"), RT.EVENT_SCHEMA))
    if ev.get("outcome") not in _OUTCOMES:
        errs.append("seq %s: outcome %r not in %s" % (ev.get("seq"), ev.get("outcome"), _OUTCOMES))
    for k in ("seq", "now_day", "box_before", "box_after"):
        v = ev.get(k)
        if not isinstance(v, int) or v < 0:
            errs.append("seq %s: %s must be a non-negative int, got %r" % (ev.get("seq"), k, v))
    g = ev.get("grade")
    if not isinstance(g, dict):
        errs.append("seq %s: grade must be an object" % ev.get("seq"))
    else:
        for gk in ("passed", "reasoning_passed", "two_vote_status", "forbidden_hit", "cleared"):
            if gk not in g:
                errs.append("seq %s: grade missing %r" % (ev.get("seq"), gk))
    return errs


def replay(bank, events, payloads):
    """Replay an event log into a fresh progress state, recomputing each event from its payload.

    bank      : list of checkpoint rows (as load_bank returns).
    events    : list of recorded event dicts (the on-disk log, in file order).
    payloads  : {seq(int): answer-payload dict} — the learner answer for each event (the runtime does NOT store the
                raw payload in the event, by design/source-cleanliness, so replay must be given them to re-grade).

    Returns (progress, errors). `progress` is the reconstructed state; `errors` lists every fidelity/shape/order
    violation found (empty => the log is an authentic, replayable record).
    """
    idx = RT._bank_index(bank)
    progress = RT.new_progress()
    errors = []
    last_box = {}  # item_id -> last box_after we replayed (to chain box_before)

    for pos, rec in enumerate(events):
        errors.extend(_shape_errors(rec))
        seq = rec.get("seq")
        if seq != pos:
            errors.append("event #%d has seq %r (expected contiguous %d)" % (pos, seq, pos))
        item_id = rec.get("item_id")
        if item_id not in idx:
            errors.append("seq %s: item_id %r is not in the bank" % (seq, item_id))
            continue
        if pos not in payloads and seq not in payloads:
            errors.append("seq %s: no answer payload supplied for replay" % seq)
            continue
        payload = payloads.get(pos, payloads.get(seq))
        row = idx[item_id]

        # box_before must chain from the prior replayed box for this item (0 if first time seen)
        expect_before = last_box.get(item_id, 0)
        if rec.get("box_before") != expect_before:
            errors.append("seq %s: box_before %r breaks the chain (expected %d)"
                          % (seq, rec.get("box_before"), expect_before))

        # recompute the step from the SAME state replay holds, the recorded now_day, and the payload
        state = progress["items"].get(item_id)
        result = RT.step(row, state, payload, rec.get("now_day"))
        recomputed = dict(result["event"]); recomputed["seq"] = pos

        # EVENT FIDELITY: recorded event must equal what replay recomputes (catches a flipped grade/box/outcome/note)
        for k in _EVENT_KEYS:
            if _canon(rec.get(k)) != _canon(recomputed.get(k)):
                errors.append("seq %s: field %r tampered — recorded %s != replay %s"
                              % (seq, k, _canon(rec.get(k)), _canon(recomputed.get(k))))

        # SOURCE-CLEAN: a tampered text field can't carry a leak past the boundary
        for tk in _TEXT_KEYS:
            val = rec.get(tk)
            if isinstance(val, str) and leak_sot.is_leak(val):
                errors.append("seq %s: field %r leaks (%s)" % (seq, tk, leak_sot.scan(val)))

        # fold into progress exactly as the runtime does (single source of the folding logic)
        RT.apply_event_to_progress(progress, row, result, pos)
        last_box[item_id] = recomputed["box_after"]

    return progress, errors


def validate(bank_path, event_log_path, progress_path, payloads_path):
    """Compare the replayed progress against the runtime's persisted progress. Returns a list of errors (empty=ok)."""
    bank = RT.load_bank(bank_path)
    events = [json.loads(l) for l in open(event_log_path, encoding="utf-8") if l.strip()]
    with open(progress_path, encoding="utf-8") as fh:
        persisted = json.load(fh)
    with open(payloads_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    payloads = {int(k): v for k, v in raw.items()}

    progress, errors = replay(bank, events, payloads)
    # the persisted state carries the last now_day; align it before the byte-identity compare (replay tracks per-event
    # now_day but new_progress starts at 0 — the runtime stamps now_day from --now at write time).
    progress["now_day"] = persisted.get("now_day", progress.get("now_day"))
    if _canon(progress) != _canon(persisted):
        errors.append("replayed progress != persisted progress (event log does not reconstruct state)")
        errors.append("  replay   : %s" % _canon(progress))
        errors.append("  persisted: %s" % _canon(persisted))
    return errors


# --------------------------------------------------------------------------- self-test
def _self_test():
    import tempfile
    failures = []
    bank = RT._authored_bank()

    # A small AUTHORED session, driven through the runtime with --write so it produces a REAL persisted
    # progress + event log; we then prove replay reconstructs it byte-for-byte.
    # Three attempts: full-pass the objective item (promote), then a held re-review of it (right answer, no reasoning),
    # then a two-vote hard-grammar item with an agreeing second check (promote). Covers promote + hold + two-vote.
    attempts = [
        ("T1-objective", 0,
         {"answer": "the article is al and the host noun is qalam",
          "reasoning": ["the article identified as al", "host noun identified as qalam"]}),
        ("T1-objective", 1,
         {"answer": "the article is al and the host noun is qalam", "reasoning": ["looks right"]}),
        ("T2-hardgrammar", 2,
         {"answer": "man means who because the content letter carries fatha",
          "reasoning": ["content-letter harakah read"],
          "second_check": {"conclusion_agrees": True, "reason_agrees": True}}),
    ]

    with tempfile.TemporaryDirectory() as td:
        bank_path = os.path.join(td, "bank.jsonl")
        with open(bank_path, "w", encoding="utf-8") as fh:
            for row in bank:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        prog_path = os.path.join(td, "progress.json")
        log_path = os.path.join(td, "events.jsonl")
        payloads = {}
        for item_id, now, payload in attempts:
            ans_path = os.path.join(td, "answer.json")
            with open(ans_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            RT._run_main(["--bank", bank_path, "--item", item_id, "--answer", ans_path,
                          "--progress", prog_path, "--event-log", log_path,
                          "--now", str(now), "--write"])
        # the seq of each event is its line index; record payloads by seq
        for seq, (_id, _now, payload) in enumerate(attempts):
            payloads[seq] = payload
        payloads_path = os.path.join(td, "payloads.json")
        with open(payloads_path, "w", encoding="utf-8") as fh:
            json.dump({str(k): v for k, v in payloads.items()}, fh)

        # 1. CLEAN replay: reconstructed progress == persisted progress, byte-identical
        errs = validate(bank_path, log_path, prog_path, payloads_path)
        if errs:
            failures.append("clean replay should pass, got: %s" % errs[:4])

        # also assert true byte-identity directly (belt & suspenders against the validate() now_day alignment)
        bank_rows = RT.load_bank(bank_path)
        events = [json.loads(l) for l in open(log_path, encoding="utf-8") if l.strip()]
        persisted = json.load(open(prog_path, encoding="utf-8"))
        replayed, rerrs = replay(bank_rows, events, payloads)
        replayed["now_day"] = persisted["now_day"]
        if rerrs:
            failures.append("clean in-memory replay reported errors: %s" % rerrs[:4])
        if _canon(replayed) != _canon(persisted):
            failures.append("replayed progress not byte-identical to persisted")

        # 2. TAMPERED grade: flip a recorded `cleared` -> replay must DETECT the mismatch
        t_events = [dict(e) for e in events]
        t_events[0] = dict(t_events[0]); t_events[0]["grade"] = dict(t_events[0]["grade"])
        t_events[0]["grade"]["cleared"] = not t_events[0]["grade"]["cleared"]
        _, terrs = replay(bank_rows, t_events, payloads)
        if not any("tampered" in e for e in terrs):
            failures.append("a flipped grade.cleared was NOT detected")

        # 3. TAMPERED box: bump box_after on event 0 -> chain + fidelity break must be caught
        b_events = [dict(e) for e in events]
        b_events[0] = dict(b_events[0]); b_events[0]["box_after"] = b_events[0]["box_after"] + 3
        _, berrs = replay(bank_rows, b_events, payloads)
        if not berrs:
            failures.append("a tampered box_after was NOT detected")

        # 4. RE-ORDERED log: swap two events so seq is non-contiguous -> must be caught
        if len(events) >= 2:
            r_events = [dict(events[1]), dict(events[0])] + [dict(e) for e in events[2:]]
            _, rerrs2 = replay(bank_rows, r_events, payloads)
            if not any("seq" in e for e in rerrs2):
                failures.append("a re-ordered (non-contiguous seq) log was NOT detected")

        # 5. SUBSTITUTED item: point event 0 at a different bank id -> box_before chain + fidelity break
        s_events = [dict(e) for e in events]
        s_events[0] = dict(s_events[0]); s_events[0]["item_id"] = "T2-hardgrammar"
        _, serrs = replay(bank_rows, s_events, payloads)
        if not serrs:
            failures.append("a substituted item_id was NOT detected")

        # 6. UNKNOWN item: an item_id not in the bank -> caught, no crash
        u_events = [dict(e) for e in events]
        u_events[0] = dict(u_events[0]); u_events[0]["item_id"] = "NOPE-not-in-bank"
        _, uerrs = replay(bank_rows, u_events, payloads)
        if not any("not in the bank" in e for e in uerrs):
            failures.append("an unknown item_id was NOT detected")

        # 7. TAMPERED note carrying a leak -> source-clean guard catches it
        l_events = [dict(e) for e in events]
        l_events[0] = dict(l_events[0]); l_events[0]["note"] = "see qac tagset /srv/secret"
        _, lerrs = replay(bank_rows, l_events, payloads)
        if not any("leak" in e for e in lerrs):
            failures.append("a leak-bearing tampered note was NOT detected")

        # 8. MISSING payload: drop a payload -> replay must report it (can't reconstruct without the answer)
        _, perrs = replay(bank_rows, events, {0: payloads[0]})
        if not any("no answer payload" in e for e in perrs):
            failures.append("a missing payload was NOT reported")

        # 9. DETERMINISM: two independent replays produce byte-identical progress
        r1, _ = replay(bank_rows, events, payloads)
        r2, _ = replay(bank_rows, events, payloads)
        if _canon(r1) != _canon(r2):
            failures.append("replay is non-deterministic")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_tutor_event_replay self-test: clean log replays byte-identical to persisted progress; "
              "tampered grade/box/order/item/leak-note + missing payload all detected; deterministic; source-clean")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(
        description="Replay a tutor event log and assert it reconstructs the persisted progress (event sourcing).")
    ap.add_argument("--bank", default=RT.DEFAULT_BANK, help="checkpoint JSONL the session ran against")
    ap.add_argument("--event-log", help="JSONL event log to replay")
    ap.add_argument("--progress", help="persisted progress-state JSON to compare against")
    ap.add_argument("--payloads", help="JSON {seq: answer-payload} for the events (runtime does not store payloads)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not (a.event_log and a.progress and a.payloads):
        ap.error("need --event-log, --progress and --payloads (or --self-test)")
    errs = validate(a.bank, a.event_log, a.progress, a.payloads)
    for e in errs:
        print("FAIL " + e)
    print("tutor event replay: %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
