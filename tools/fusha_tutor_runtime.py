#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_tutor_runtime — the OFFLINE, DETERMINISTIC tutor loop for the Fusha reading curriculum (criticism 5).

Turns the prose tutor-session-protocol into an executable harness. It does NOT replace a human/agent tutor's
judgement on open prose; it makes the OBJECTIVE checkpoint loop runnable and honest:

    load checkpoint bank (JSONL) + optional progress state
      -> select the next item (a due REVIEW, else a new item)        [deterministic]
      -> accept an ANSWER PAYLOAD (the learner's answer + reasoning + an optional DECLARED second check,
         which is recorded but never treated as an independent review)
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
  * Two-vote gate: a `two_vote_required` row is ALWAYS `pending` — HELD, never cleared from inside the runtime.
    The runtime grades answer and reasoning content; it cannot independently clear a mandatory two-vote FACT
    gate, because a learner-supplied `second_check` Boolean is a declaration, not an occurrence-bound
    canonical vote artifact. Clearing such a row needs a separately governed runtime contract that consumes
    external, occurrence-bound vote artifacts; until then the checkpoint stays held.
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
from tools import kc_catalog  # noqa: E402
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


def _ordered_slots_ok(slots, answer):
    """RELATION-DIRECTION guard: every slot substring must appear in the answer AND in the given order. Token-coverage
    matching (_form_matches) is order-blind, so an answer that reverses a relation ("the noun governs the preposition"
    vs "the preposition governs the noun") shares the same bag of words and would falsely match. Requiring the slots in
    sequence makes the direction load-bearing. A row with no `ordered_slots` is unconstrained (returns True) — the guard
    is purely additive. Deterministic; normalizes with the same recall normalizer used for answer matching."""
    if not slots:
        return True
    ans = _norm(answer)
    pos = -1
    for s in slots:
        ns = _norm(s)
        if not ns:
            continue
        idx = ans.find(ns, pos + 1)
        if idx < 0:
            return False
        pos = idx
    return True


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
    # Content coverage of the authored key AND (when the row declares them) the relational slots in order — so an
    # answer that inverts the relation cannot clear on the shared bag of words alone. Ordered-slot matching is additive:
    # a row without `ordered_slots` is graded exactly as before.
    passed = any(_form_matches(v, answer) for v in expected_set) and _ordered_slots_ok(row.get("ordered_slots"), answer)
    forbidden_hit = _contains_any(answer, row.get("forbidden_answers", []))
    joined_reasoning = " \n ".join(reasoning or []) if isinstance(reasoning, list) else str(reasoning or "")
    missing = [req for req in (row.get("required_reasoning", []) or [])
               if not _form_matches(req, joined_reasoning)]
    reasoning_passed = not missing

    if row.get("two_vote_required"):
        # ROUND-11: a mandatory two-vote FACT gate is never cleared from inside the tutoring runtime.
        # `second_check` is a learner-supplied declaration: {"conclusion_agrees": true, "reason_agrees": true}
        # carries no exact Qurʾānic occurrence, no canonical vote envelope, no reviewer or session identity,
        # no frozen worklist hash, no model proof and no evidence that the two checks were isolated from each
        # other. Reading it as an independent review promoted a hard-grammar checkpoint on a self-report.
        #
        # The runtime can grade answer and reasoning CONTENT. It cannot independently clear a two-vote fact
        # gate, so such a row is HELD as pending until a separately governed runtime contract can consume
        # canonical, occurrence-bound external vote artifacts. That contract is not invented here.
        # ROUND-13: a truthy NON-mapping second_check (JSON true, 1, "yes", [1]) raised AttributeError on
        # .get(). Malformed evidence fails closed; it never crashes and never counts as a declaration.
        declared = (isinstance(second, dict) and bool(second.get("conclusion_agrees"))
                    and bool(second.get("reason_agrees")))
        two_vote_status = "pending"
        second_check_declared = declared
    else:
        two_vote_status = "n/a"
        second_check_declared = None

    # ROUND-13: LEARNER MASTERY and FACT READINESS are different questions and are reported separately.
    # `content_mastered` is what the learner demonstrated: right answer, required reasoning, no forbidden
    # path. `cleared` additionally needs the fact gate, which this runtime can never satisfy. A held row is
    # therefore NOT content ignorance, and nothing downstream may treat it as a miss.
    content_mastered = bool(passed and reasoning_passed and not forbidden_hit)
    held_for_fact_gate = bool(content_mastered and two_vote_status == "pending")
    cleared = bool(content_mastered and two_vote_status != "pending")
    return {"passed": bool(passed), "reasoning_passed": bool(reasoning_passed),
            "two_vote_status": two_vote_status, "forbidden_hit": bool(forbidden_hit),
            # reported for transparency ONLY: what the learner declared, never what was proven
            "second_check_declared": second_check_declared,
            "content_mastered": content_mastered, "held_for_fact_gate": held_for_fact_gate,
            "cleared": cleared, "missing_reasoning": missing}


# --------------------------------------------------------------------------- grammar-reasoning bridge (DEFAULT-OFF)
# OPTIONAL delegation to tools/grade_grammar_reasoning (the GrammarProblems eval grader). It is DEFAULT-OFF: the
# grading path above (grade/step) is the runtime's SOURCE OF TRUTH and is never altered by this bridge. When the
# caller opts in (bridge_grade=True / --grammar-bridge), the runtime additionally translates its OWN computed grade
# into the eval grader's `judgment` shape and asserts the two graders AGREE on the shared reasoning gate. They are
# two views of the same invariant: a grammar decision clears only when the final answer AND the reasoning hold,
# and a decision that needs two independent occurrence-bound reviews clears in NEITHER grader without them —
# so on a two_vote_required row both refuse, which is what makes them agree. The bridge is an agreement
# CHECK, not a second opinion that can override the runtime
# — a disagreement is surfaced (and, in --self-test, fails) rather than silently re-grading.
#
# Shared-gate mapping (runtime grade `g` for `row` -> grade_grammar_reasoning judgment):
#   final_ok       <- g["passed"]                         (final answer matches the authored key)
#   reasoning_ok   <- g["reasoning_passed"] and not g["forbidden_hit"]
#                                                          (required reasoning present AND no forbidden path taken)
#   two-vote gate  -> NOT translated. ROUND-11: the runtime holds every two_vote_required row as pending, and
#       the eval grader requires canonical, occurrence-bound vote artifacts that a tutoring checkpoint does
#       not have. The bridge therefore sends NO two-vote assertion at all. Both graders refuse the row for
#       the same reason, so they agree; the gate is still REQUIRED (the case keeps required_gate=
#       two_vote_required — it is never relabelled auto_safe).
#   evidence_cited / source_address  -> the runtime checkpoint schema carries NO evidence-rung/source-address field,
#       so the bridge runs the eval grader with its EVIDENCE gate neutralized (case-driven, satisfied) and compares
#       ONLY on the gates both graders actually compute. This keeps the comparison honest: we never claim the runtime
#       checked an evidence rung it has no input for.
def _grammar_bridge_case(row):
    """Build the grade_grammar_reasoning `case` for a runtime row. `required_gate` is two_vote_required iff the row
    is two-vote, else auto_safe (the runtime has no never_auto / human-review checkpoint kind)."""
    return {"id": str(row.get("id", "")),
            "required_gate": "two_vote_required" if row.get("two_vote_required") else "auto_safe"}


def _grammar_bridge_judgment(g):
    """Translate a runtime grade dict `g` (from grade()) into a grade_grammar_reasoning `judgment`. Evidence is
    neutralized (the runtime checkpoint schema has no evidence rung/source-address) so the shared comparison is only
    over the answer + reasoning + two-vote gates both graders compute."""
    # ROUND-11: no `two_vote_done` is sent. A declared Boolean is not evidence, and the runtime has no
    # canonical vote artifact to offer, so the two-vote gate is left unproven on purpose.
    return {"final_ok": bool(g["passed"]),
            "reasoning_ok": bool(g["reasoning_passed"]) and not bool(g["forbidden_hit"]),
            "evidence_cited": True, "source_address": "n/a-runtime-checkpoint"}


def grammar_bridge_check(row, g):
    """Run the OPTIONAL grammar-reasoning bridge over an already-computed runtime grade `g` for `row`.

    Returns {agree: bool, runtime_cleared: bool, eval_pass: bool, eval_block_reason: str|None}. `agree` is True when
    the runtime's `cleared` verdict matches the eval grader's `pass` verdict on the shared gates. This NEVER mutates
    `g`; the runtime grade remains the source of truth. Import is lazy so the default-off path has zero coupling."""
    from tools import grade_grammar_reasoning as GGR  # noqa: PLC0415 (lazy: keep default path decoupled)
    case = _grammar_bridge_case(row)
    judgment = _grammar_bridge_judgment(g)
    ev = GGR.grade(case, judgment)
    return {"agree": bool(ev["pass"]) == bool(g["cleared"]),
            "runtime_cleared": bool(g["cleared"]), "eval_pass": bool(ev["pass"]),
            "eval_block_reason": ev["block_reason"]}


def new_progress(label="learner"):
    return {"schema": PROGRESS_SCHEMA, "learner_label": label, "now_day": 0, "items": {},
            "cleared_item_ids": [], "missed": []}


def _bank_index(bank):
    return {r["id"]: r for r in bank}


def select_next(bank, progress, now_day, interleave=False):
    """Pick the next checkpoint id deterministically: a due REVIEW (already-seen, due) first, else the next NEW item
    in bank order, else the soonest-due seen item. Returns (item_id, reason) or (None, 'bank empty').

    interleave=True round-robins the due reviews across their roadmap levels (via the scheduler's interleave option),
    so a cumulative-review session does not replay one level in a block. Default (False) keeps the single-priority
    order. The chosen item is unchanged in kind; only the ORDER of equally-due reviews differs."""
    states = progress.get("items", {})
    seen = set(states)
    level_of = {r["id"]: str(r.get("level", "")) for r in bank}
    # due reviews among already-seen items (reps>0)
    due_reviews = [i for i in SCHED.select_due(states, now_day, interleave=interleave,
                                               group_key=(lambda i: level_of.get(i, "")) if interleave else None)
                   if int(states.get(i, {}).get("reps", 0)) > 0]
    # ROUND-13: a row awaiting external certification can NEVER clear, so it stays in box 0, is always the
    # most overdue, and used to be served ahead of every unseen item forever. Genuine reviews still come
    # first; unclearable fact-held rows yield to new content and are only offered when nothing else is.
    # An item whose BANK ROW carries a two-vote fact gate can never be cleared here, so it is permanently
    # due. Derive that from the bank rather than from a new state key (the progress schema is canonical).
    # ROUND-14: only a CONTENT-CORRECT fact hold may yield to new material. A wrong answer to a two-vote
    # row is a genuine learner miss and keeps normal due-review priority — the fact gate must not erase
    # learner error. An open miss is recorded in `progress.missed` (a fact hold deliberately is not), so
    # that list distinguishes the two cases without adding a key to the canonical progress schema.
    _fact_gated = {r["id"] for r in bank if r.get("two_vote_required")}
    _cleared = set(progress.get("cleared_item_ids") or [])
    _open_misses = {m.get("item_id") for m in (progress.get("missed") or [])}
    blocked = [i for i in due_reviews
               if i in _fact_gated and i not in _cleared and i not in _open_misses]
    live_reviews = [i for i in due_reviews if i not in blocked]
    if live_reviews:
        return live_reviews[0], "due_review"
    for r in bank:                                   # first unseen item, in bank order
        if r["id"] not in seen:
            return r["id"], "new_item"
    if blocked:
        return blocked[0], "due_review_awaiting_fact_certification"
    if states:                                        # all seen, none due -> soonest due
        nxt = min(states, key=lambda k: (int(states[k].get("due_day", 0)), k))
        return nxt, "soonest_due"
    return None, "bank empty"


def step(row, state, payload, now_day):
    """Grade + schedule + build a (source-clean) event for one attempt. Pure (no I/O). Returns dict."""
    g = grade(row, payload)
    box_before = int((state or {}).get("box", 0))
    # ROUND-13: the label said "miss" for a content-correct row held only by the fact gate. The scheduler
    # reads the typed fields (and correctly answers `hold`), but the label itself was untrue and is what a
    # reader sees. A fact hold is now labelled `held`, never `miss`.
    gr_for_sched = {"passed": g["passed"], "reasoning_passed": g["reasoning_passed"],
                    "two_vote_status": g["two_vote_status"], "forbidden_hit": g["forbidden_hit"],
                    "grade": ("cleared" if g["cleared"]
                              else ("held" if g["held_for_fact_gate"] else "miss"))}
    new_state = SCHED.schedule(state or SCHED.new_state(), gr_for_sched, now_day)
    outcome = new_state["last_outcome"]
    # ROUND-13: remediation teaches a learner something they got wrong. A fact hold is not that.
    route = None if (g["cleared"] or g["held_for_fact_gate"]) else row.get("remediation_route")
    note = ("cleared" if g["cleared"]
            else ("held: " + ("content mastered; awaiting external two-vote certification of the fact "
                              "(not a learner miss)" if g["held_for_fact_gate"]
                              else "pending two-vote" if g["two_vote_status"] == "pending"
                              else ("forbidden answer" if g["forbidden_hit"]
                                    else "reasoning incomplete" if not g["reasoning_passed"] else "review"))
                  if outcome == "hold" else "miss -> remediation"))
    event = {"schema": EVENT_SCHEMA, "seq": 0, "now_day": now_day, "item_id": row["id"],
             "level": str(row.get("level", "")), "outcome": outcome,
             # NOTE: the event `grade` block is fixed by qamus/schemas/tutor-event.schema.json, which this
             # lane may not edit, so the round-13 content_mastered / held_for_fact_gate axes are reported on
             # the returned grade dict, in `note`, and on progress.awaiting_fact_certification instead.
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
    # ROUND-13: `missed` is the open-MISS list — it drives remediation and reads as learner ignorance. A
    # content-correct row held only by the external fact gate belongs on its own list instead.
    # The progress object is fixed by its canonical schema (not editable in this lane), so the hold is
    # recorded by ABSENCE from `missed` plus the event note, never by a new progress key.
    if g["held_for_fact_gate"]:
        pass
    elif not g["cleared"]:
        status = "pending_two_vote" if g["two_vote_status"] == "pending" else "open"
        # Train C: a row that names its own KC (curriculum/drills/keys/*.kc_id) reports that KC as the
        # pending-reason code; a row with no kc_id keeps the prior null (no reason invented).
        progress["missed"].append({"item_id": item_id, "error_reason": row.get("kc_id"),
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
    ap.add_argument("--grammar-bridge", action="store_true",
                    help="ADDITIVE: also report agreement with tools/grade_grammar_reasoning (does not change grading)")
    ap.add_argument("--interleave", action="store_true",
                    help="round-robin due reviews across roadmap levels (a cumulative-review session; default off)")
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
        item_id, reason = select_next(bank, progress, a.now, interleave=a.interleave)
        if not item_id:
            print(json.dumps({"next": None, "reason": reason}, ensure_ascii=False)); return 0
        row = idx[item_id]
        print(json.dumps({"next": item_id, "reason": reason, "level": row.get("level"),
                          "row_type": row.get("row_type", "checkpoint"),
                          "prompt": row.get("prompt"), "two_vote_required": bool(row.get("two_vote_required"))},
                         ensure_ascii=False))
        return 0

    item_id = a.item or select_next(bank, progress, a.now, interleave=a.interleave)[0]
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
    if a.grammar_bridge:  # additive only: the grade above is unchanged; this just reports cross-grader agreement.
        out["grammar_bridge"] = grammar_bridge_check(row, result["grade"])
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
        # Adversarial RELATION-INVERSION row: a right/governed pair whose DIRECTION is the whole point. Its
        # `ordered_slots` pin the relational order ("preposition ... governs ... noun") so an inverted answer with the
        # same bag of words cannot clear on token coverage alone; `forbidden_answers` also names the flipped phrasing.
        {"id": "T3-relation-inversion", "level": "6", "concept": "governor direction (which word governs which)",
         "prompt": "State which word is the governor and which is governed, in that order.",
         "quran_example": None,
         "expected_answer": "the preposition governs the noun, so the noun is the governed word",
         "accepted_variants": ["the preposition is the governor and governs the noun"],
         "forbidden_answers": ["the noun governs the preposition", "the noun is the governor and the preposition is governed"],
         "required_reasoning": ["governor named", "governed word named"],
         "ordered_slots": ["preposition", "governs", "noun"],
         "sarf_procedure": None, "nahw_procedure": "nahw/procedures/irab-case-mood.md",
         "remediation_route": "nahw/drills/dogfood-nahw-remediation.md", "two_vote_required": False},
    ]


def _load_kc_catalog_by_id():
    return kc_catalog.load_kc_catalog_by_id(_REPO)


def _check_kc_gate_row(row, kc_by_id=None):
    """CATALOG-GATE RULE: a kc_id-bearing drill-key row's required posture is decided by its OWN KC's
    `default_gate` in curriculum/kc-catalog.json:
      * default_gate == "auto_safe": the row may clear on content + reasoning alone (two_vote_required must be
        false, and a full-content-correct answer must actually CLEAR + PROMOTE).
      * default_gate != "auto_safe" (two_vote_required / human_source_review_required / never_auto_resolve, or a
        dangling/missing kc_id): the row MUST set two_vote_required=true and stays pending/HELD even on a
        full-content-correct answer with a DECLARED agreeing second_check.

    Returns a list of failure strings (empty when the row conforms). Pure; no I/O beyond an optionally-supplied
    catalog map."""
    if kc_by_id is None:
        kc_by_id = _load_kc_catalog_by_id()
    kc = kc_by_id.get(row.get("kc_id"))
    gate = kc.get("default_gate") if kc else None
    failures = []
    if gate == "auto_safe":
        if row.get("two_vote_required"):
            failures.append("auto_safe KC row %s (kc=%s) must NOT set two_vote_required=true" %
                            (row["id"], row.get("kc_id")))
            return failures
        payload = {"answer": row["expected_answer"], "reasoning": list(row.get("required_reasoning") or [])}
        r = step(row, None, payload, now_day=0)
        if not r["grade"]["cleared"] or r["outcome"] != "promote":
            failures.append("auto_safe KC row %s (kc=%s) should clear on content+reasoning, got %s / %s" %
                            (row["id"], row.get("kc_id"), r["grade"], r["outcome"]))
    else:
        if not row.get("two_vote_required"):
            failures.append("KC row %s (kc=%s, gate=%r) is not auto_safe, so it must be two_vote_required" %
                            (row["id"], row.get("kc_id"), gate))
            return failures
        payload = {"answer": row["expected_answer"], "reasoning": list(row.get("required_reasoning") or []),
                   "second_check": {"conclusion_agrees": True, "reason_agrees": True}}
        r = step(row, None, payload, now_day=0)
        if r["grade"]["cleared"] or r["grade"]["two_vote_status"] != "pending" or r["outcome"] != "hold":
            failures.append("two_vote_required row %s cleared/promoted despite its KC's non-auto_safe gate, "
                            "got %s / %s" % (row["id"], r["grade"], r["outcome"]))
    return failures


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

    # 5. ROUND-11: hard-grammar with a DECLARED agreeing second check -> still pending + HELD.
    # The Boolean is a learner declaration, not an independent occurrence-bound review, so it may not clear
    # or promote a two_vote_required row. It is reported as `second_check_declared` and nothing more.
    p_two = dict(p_one); p_two["second_check"] = {"conclusion_agrees": True, "reason_agrees": True}
    r5 = step(idx["T2-hardgrammar"], None, p_two, now_day=0)
    if (r5["grade"]["two_vote_status"] != "pending" or r5["grade"]["cleared"]
            or r5["outcome"] != "hold" or r5["grade"].get("second_check_declared") is not True):
        failures.append("a DECLARED second check must not clear or promote a two-vote row, got %s / %s"
                        % (r5["grade"], r5["outcome"]))

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

    # 7b. RELATION-INVERSION guard (ASAG): an answer with the right bag of words but the relation REVERSED must not
    #     clear. The correct-direction answer clears; a forbidden-listed inversion is caught; and a PARAPHRASED
    #     inversion not in forbidden_answers is still caught by ordered-slot matching (order, not just membership).
    ok_dir = step(idx["T3-relation-inversion"], None,
                  {"answer": "the preposition governs the noun, so the noun is the governed word",
                   "reasoning": ["governor named", "governed word named"]}, now_day=0)
    if not ok_dir["grade"]["cleared"]:
        failures.append("correct-direction relation answer should clear, got %s" % ok_dir["grade"])
    inv_forbidden = step(idx["T3-relation-inversion"], None,
                         {"answer": "the noun governs the preposition and the preposition is governed",
                          "reasoning": ["governor named", "governed word named"]}, now_day=0)
    if inv_forbidden["grade"]["cleared"]:
        failures.append("relation-inverted answer (forbidden-listed) must NOT clear, got %s" % inv_forbidden["grade"])
    inv_paraphrase = step(idx["T3-relation-inversion"], None,
                          {"answer": "here the noun governs, and the preposition is the word governed by it",
                           "reasoning": ["governor named", "governed word named"]}, now_day=0)
    if inv_paraphrase["grade"]["passed"] or inv_paraphrase["grade"]["cleared"]:
        failures.append("ordered-slot guard must fail a paraphrased relation inversion, got %s" % inv_paraphrase["grade"])

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

    # 11. grammar-reasoning BRIDGE (default-off, opt-in). (a) the default grading path is BYTE-IDENTICAL whether or
    #     not the bridge is consulted: grade() never imports/calls the bridge, so a fresh grade equals r["grade"].
    g_again = grade(idx["T1-objective"], p_full)
    if json.dumps(g_again, sort_keys=True) != json.dumps(r["grade"], sort_keys=True):
        failures.append("bridge presence changed the default grade() output (must be byte-identical)")
    # (b) the bridge AGREES with the built-in grader on every shared case — cleared<->eval pass.
    for tag, row_, g_ in (("full-pass", idx["T1-objective"], r["grade"]),
                          ("no-reasoning", idx["T1-objective"], r2["grade"]),
                          ("forbidden", idx["T1-objective"], r3["grade"]),
                          ("two-vote-pending", idx["T2-hardgrammar"], r4["grade"]),
                          ("two-vote-declared-only", idx["T2-hardgrammar"], r5["grade"]),
                          ("self-report-ignored", idx["T1-objective"], r6["grade"])):
        b = grammar_bridge_check(row_, g_)
        if not b["agree"]:
            failures.append("grammar bridge DISAGREES on %s: runtime_cleared=%s eval_pass=%s (%s)"
                            % (tag, b["runtime_cleared"], b["eval_pass"], b["eval_block_reason"]))
    # (c) the bridge correctly mirrors the load-bearing GrammarProblems case: a right answer with WRONG reasoning
    #     must NOT pass the eval grader (and the runtime did not clear it either) -> they agree on a HOLD.
    g_wrong_reason = grade(idx["T1-objective"], p_noreason)
    bb = grammar_bridge_check(idx["T1-objective"], g_wrong_reason)
    if g_wrong_reason["cleared"] or bb["eval_pass"] or not bb["agree"]:
        failures.append("bridge must agree-on-HOLD for right-answer-wrong-reason, got %s / %s" % (g_wrong_reason, bb))

    # 12. CUMULATIVE-REVIEW row type + interleaved selection: a row carrying row_type="cumulative_review" is graded by
    #     CONTENT exactly like any checkpoint (row_type is descriptive, never a grading input); and select_next accepts
    #     interleave=True (a cumulative-review session round-robins due reviews across roadmap levels via the scheduler).
    cum_row = {"id": "CUM-1", "level": "8", "row_type": "cumulative_review",
               "concept": "cumulative review across prior levels",
               "prompt": "recall the article, the passive, and mā's function together",
               "expected_answer": "the article marks definiteness, the passive keeps its voice, and ma is decided by context",
               "accepted_variants": ["definiteness from the article; passive voice kept; ma function from context"],
               "forbidden_answers": ["these never interact"], "required_reasoning": ["three prior concepts recalled"],
               "two_vote_required": False}
    rc = step(cum_row, None, {"answer": "the article marks definiteness, the passive keeps its voice, and ma is decided by context",
                              "reasoning": ["three prior concepts recalled"]}, now_day=0)
    if not rc["grade"]["cleared"]:
        failures.append("cumulative_review row must grade by content like any row, got %s" % rc["grade"])
    cum_bank = [{"id": "L3a", "level": "3"}, {"id": "L3b", "level": "3"},
                {"id": "L5a", "level": "5"}, {"id": "L5b", "level": "5"}]
    prog_cum = {"items": {r["id"]: {"box": 1, "due_day": 0, "reps": 2, "lapses": 0} for r in cum_bank}}
    nid, why = select_next(cum_bank, prog_cum, 5, interleave=True)
    if nid is None or why != "due_review":
        failures.append("interleaved select_next should pick a due review, got %s/%s" % (nid, why))
    # interleave must not change the SET of reachable items — same next-pick invariants as the default path
    if select_next(cum_bank, prog_cum, 5, interleave=False)[1] != "due_review":
        failures.append("default select_next should also pick a due review for the cumulative bank")

    # 13. CATALOG-GATE RULE (replaces the earlier blanket "every kc_id row is two-vote" rule): a kc_id-bearing
    #     drill-key row's required posture is decided by ITS OWN KC's `default_gate` in curriculum/kc-catalog.json,
    #     not by a flat assumption that every KC is hard-gated. A KC gated `auto_safe` may clear normally on
    #     content + reasoning (full-pass -> cleared + promote); a KC gated anything else (two_vote_required,
    #     human_source_review_required, never_auto_resolve) must set two_vote_required=true on its rows and stays
    #     pending/HELD even on a full-content-correct answer with a DECLARED agreeing second_check.
    _keys_dir = os.path.join(_REPO, "curriculum", "drills", "keys")
    _kc_rows = [row for fn in os.listdir(_keys_dir) if fn.endswith(".keys.jsonl")
                for row in load_bank(os.path.join(_keys_dir, fn)) if row.get("kc_id")]
    if not _kc_rows:
        failures.append("no kc_id-bearing drill-key row found (Train C binding missing)")
    for row in _kc_rows:
        failures.extend(_check_kc_gate_row(row))

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_tutor_runtime self-test: schema-graded (no self-report); a two_vote_required row "
              "is always HELD pending — the runtime grades answer/reasoning CONTENT but cannot "
              "independently clear a mandatory two-vote FACT gate, and a declared second_check Boolean is "
              "recorded, never believed; "
              "wrong-reason holds; --write-gated persistence; deterministic; source-clean; "
              "grammar-bridge default-off (grade byte-identical) + agrees with built-in grader")
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
