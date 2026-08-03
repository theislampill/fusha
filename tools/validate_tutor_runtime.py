#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_tutor_runtime — prove the offline tutor runtime + Leitner scheduler honor their hard contracts.

This is the adversarial guard for tools/fusha_tutor_runtime.py + tools/fusha_review_scheduler.py. It FAILS if the
runtime ever:
  * grades from a self-reported correctness flag (a payload `passed`/`correct`/`cleared`/`score` must be ignored);
  * clears a `two_vote_required` row from inside the runtime at all (pending must HOLD, never clear) — a
    learner-supplied `second_check` Boolean is a declaration, not an occurrence-bound canonical vote
    artifact, so the runtime can grade answer/reasoning content but cannot independently clear a mandatory
    two-vote FACT gate;
  * promotes a "right answer for the wrong reason" (passed but reasoning incomplete) up the Leitner ladder;
  * persists progress or an event without the explicit `--write` flag;
  * is non-deterministic (a wall clock / RNG would break replay);
  * emits an event whose fields violate the tutor-event / tutor-progress-state JSON schemas;
  * leaks an internal/source term into an event text field;
  * records a wrong `missed[].error_reason` (must equal the row's `kc_id` when present, else stay null).

Stdlib only. CLI: --self-test (runs the full battery + meta-checks that the guard itself catches a broken grader).
See parserplans/fusha-data-runtime-completion-pass/004 (P0-C).
"""
import argparse
import inspect
import json
import os
import re
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import fusha_tutor_runtime as RT  # noqa: E402
from tools import fusha_review_scheduler as SCHED  # noqa: E402
from tools import leak_sot  # noqa: E402

_PROG_SCHEMA = json.load(open(os.path.join(_REPO, "qamus", "schemas", "tutor-progress-state.schema.json"), encoding="utf-8"))
_EVENT_SCHEMA = json.load(open(os.path.join(_REPO, "qamus", "schemas", "tutor-event.schema.json"), encoding="utf-8"))
_REMEDIATION_INDEX = os.path.join(_REPO, "curriculum", "drills", "dogfood-error-remediation-index.md")
_DRILL_KEYS = os.path.join(_REPO, "curriculum", "drills", "keys")

# a payload read of a self-reported correctness flag — must NOT appear in grade()'s source
_SELF_REPORT_READ = re.compile(r"""payload\s*(?:\.get\(|\[)\s*["'](?:passed|correct|is_correct|cleared|score|grade)["']""")


def _validate_obj(obj, schema, path="$"):
    """Minimal recursive JSON-schema check: type, required, enum, const, properties, additionalProperties
    (bool OR subschema), items. Sufficient for these flat schemas; not a general validator."""
    errs = []
    t = schema.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    if "object" in types or "properties" in schema or "additionalProperties" in schema:
        if not isinstance(obj, dict):
            return ["%s: expected object" % path]
        for r in schema.get("required", []):
            if r not in obj:
                errs.append("%s: missing required %r" % (path, r))
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in obj.items():
            if k in props:
                errs += _validate_obj(v, props[k], "%s.%s" % (path, k))
            elif addl is False:
                errs.append("%s: unexpected key %r" % (path, k))
            elif isinstance(addl, dict):
                errs += _validate_obj(v, addl, "%s.%s" % (path, k))
        return errs
    if "array" in types:
        if not isinstance(obj, list):
            return ["%s: expected array" % path]
        for i, it in enumerate(obj):
            errs += _validate_obj(it, schema.get("items", {}), "%s[%d]" % (path, i))
        return errs
    if "const" in schema and obj != schema["const"]:
        errs.append("%s: expected const %r" % (path, schema["const"]))
    if "enum" in schema and obj not in schema["enum"]:
        errs.append("%s: %r not in enum" % (path, obj))
    if types and not (obj is None and "null" in types):
        pymap = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
                 "array": list, "object": dict}
        if "integer" in types and isinstance(obj, bool):
            errs.append("%s: bool is not integer" % path)
        else:
            allowed = tuple(c for k in types for c in ((pymap[k],) if k in pymap else ()))
            if allowed and not isinstance(obj, allowed):
                errs.append("%s: expected %s" % (path, "/".join(types)))
    return errs


def _g(passed, reasoning=True, two_vote="n/a", forbidden=False):
    return {"passed": passed, "reasoning_passed": reasoning, "two_vote_status": two_vote,
            "forbidden_hit": forbidden, "grade": "x"}


def _reachable_kc_ids():
    out = set()
    for name in sorted(os.listdir(_DRILL_KEYS)):
        if not name.endswith(".keys.jsonl"):
            continue
        with open(os.path.join(_DRILL_KEYS, name), encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                kc_id = json.loads(line).get("kc_id")
                if kc_id:
                    out.add(kc_id)
    return out


def _validate_remediation_index(text=None, reachable=None):
    if text is None:
        text = open(_REMEDIATION_INDEX, encoding="utf-8").read()
    reachable = _reachable_kc_ids() if reachable is None else set(reachable)
    errs, seen = [], {}
    row_re = re.compile(r"^\|\s*`(kc-[^`]+)`\s*\|\s*`(emittable|documented_only)`\s*\|")
    for line in text.splitlines():
        if not line.startswith("| `kc-"):
            continue
        m = row_re.match(line)
        if not m:
            errs.append("Train C remediation row lacks a closed runtime posture: %s" % line)
            continue
        kc_id, posture = m.groups()
        if kc_id in seen:
            errs.append("duplicate Train C remediation kc_id %s" % kc_id)
            continue
        seen[kc_id] = posture
        expected = "emittable" if kc_id in reachable else "documented_only"
        if posture != expected:
            errs.append("Train C remediation %s is %s but runtime reachability requires %s" %
                        (kc_id, posture, expected))
    if not seen:
        errs.append("Train C remediation table has no posture-bearing KC rows")
    normalized = " ".join(text.split())
    if "treat the ids as equivalent only when the authoritative crosswalk explicitly pairs them" not in normalized:
        errs.append("remediation precedence does not defer equivalence to the authoritative crosswalk")
    if "it is not an equivalence assertion for either KC" not in normalized:
        errs.append("hidden_derivative_plural_piece is not explicitly withheld from KC equivalence")
    return errs


def validate():
    errs = []
    bank = RT._authored_bank()
    idx = RT._bank_index(bank)

    # 1. STATIC: grade() must not read a self-reported correctness flag from the payload.
    src = inspect.getsource(RT.grade)
    if _SELF_REPORT_READ.search(src):
        errs.append("grade() reads a self-reported correctness flag from the payload")

    # 2. BEHAVIOUR: a planted self-report must be ignored (wrong content -> not passed).
    g = RT.grade(idx["T1-objective"], {"answer": "totally wrong", "reasoning": [],
                                       "passed": True, "correct": True, "cleared": True, "score": 1.0})
    if g["passed"] or g["cleared"]:
        errs.append("a self-reported correctness flag was honored")

    # 3. two-vote: the runtime NEVER clears a two_vote_required row — one check or a declared agreeing
    #    second check both stay pending and held.
    one = RT.grade(idx["T2-hardgrammar"], {"answer": "man means who because the content letter carries fatha",
                                           "reasoning": ["content-letter harakah read"]})
    if one["two_vote_status"] != "pending" or one["cleared"]:
        errs.append("two-vote row cleared on a single check")
    two = RT.grade(idx["T2-hardgrammar"], {"answer": "man means who because the content letter carries fatha",
                                           "reasoning": ["content-letter harakah read"],
                                           "second_check": {"conclusion_agrees": True, "reason_agrees": True}})
    # ROUND-11: a DECLARED agreeing second check must NOT clear the row either. The Boolean carries no
    # occurrence, no canonical vote envelope and no reviewer identity; it is recorded, never believed.
    if two["two_vote_status"] != "pending" or two["cleared"] or two.get("second_check_declared") is not True:
        errs.append("two-vote row cleared on a DECLARED second check (a Boolean is not an independent "
                    "review artifact)")

    # 4. scheduler: only a FULL pass promotes; wrong-reason/pending/forbidden HOLD; miss demotes.
    base = {"box": 2, "due_day": 0, "reps": 3, "lapses": 0}
    if SCHED.schedule(base, _g(True), 0)["box"] != 3:
        errs.append("scheduler did not promote on a full pass")
    if SCHED.schedule(base, _g(True, reasoning=False), 0)["box"] != 2:
        errs.append("scheduler promoted a right-answer-wrong-reason")
    if SCHED.schedule(base, _g(True, two_vote="pending"), 0)["box"] != 2:
        errs.append("scheduler promoted a pending two-vote")
    if SCHED.schedule(base, _g(True, forbidden=True), 0)["box"] != 2:
        errs.append("scheduler promoted a forbidden-answer hit")
    if SCHED.schedule(base, _g(False), 0)["box"] != 0:
        errs.append("scheduler did not demote a miss to box 0")

    # 5. determinism: identical step() inputs -> identical event JSON, twice.
    payload = {"answer": "the article is al and the host noun is qalam",
               "reasoning": ["article identified as al", "host noun identified as qalam"]}
    e1 = RT.step(idx["T1-objective"], None, payload, 4)["event"]
    e2 = RT.step(idx["T1-objective"], None, payload, 4)["event"]
    if json.dumps(e1, sort_keys=True) != json.dumps(e2, sort_keys=True):
        errs.append("runtime is non-deterministic")

    # 6. schema conformance of a generated event + a folded progress state.
    errs += ["event schema: " + e for e in _validate_obj(e1, _EVENT_SCHEMA)]
    prog = RT.new_progress()
    RT.apply_event_to_progress(prog, idx["T1-objective"], RT.step(idx["T1-objective"], None, payload, 0), 0)
    errs += ["progress schema: " + e for e in _validate_obj(prog, _PROG_SCHEMA)]

    # 7. NO write without --write (run main over a temp dir, assert nothing persisted), then --write persists.
    with tempfile.TemporaryDirectory() as td:
        bp = os.path.join(td, "bank.jsonl")
        with open(bp, "w", encoding="utf-8") as fh:
            for r in bank:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        ap = os.path.join(td, "a.json")
        json.dump(payload, open(ap, "w", encoding="utf-8"))
        pp, lp = os.path.join(td, "p.json"), os.path.join(td, "e.jsonl")
        argv = ["--bank", bp, "--item", "T1-objective", "--answer", ap, "--progress", pp, "--event-log", lp, "--now", "0"]
        RT._run_main(argv)
        if os.path.exists(pp) or os.path.exists(lp):
            errs.append("runtime persisted a file WITHOUT --write")
        RT._run_main(argv + ["--write"])
        if not (os.path.exists(pp) and os.path.exists(lp)):
            errs.append("runtime did not persist with --write")

    # 8. source-clean event note.
    if leak_sot.is_leak(e1.get("note", "")):
        errs.append("event note leaks an internal/source term")

    # 9. Train C error_reason contract: a graded miss on a row carrying kc_id records that kc_id as
    #    progress.missed[].error_reason; a miss on a row WITHOUT kc_id still records null (no invention).
    bad_payload = {"answer": "totally wrong", "reasoning": []}
    row_with_kc = dict(idx["T1-objective"], id="TC-kc-miss", kc_id="kc-clitic-segmentation")
    prog_kc = RT.new_progress()
    RT.apply_event_to_progress(prog_kc, row_with_kc, RT.step(row_with_kc, None, bad_payload, 0), 0)
    miss_kc = next((m for m in prog_kc["missed"] if m["item_id"] == "TC-kc-miss"), None)
    if not miss_kc or miss_kc["error_reason"] != "kc-clitic-segmentation":
        errs.append("a miss on a kc_id-bearing row did not record the kc_id as error_reason: %r" % miss_kc)
    row_without_kc = dict(idx["T1-objective"], id="TC-no-kc-miss")
    prog_no = RT.new_progress()
    RT.apply_event_to_progress(prog_no, row_without_kc, RT.step(row_without_kc, None, bad_payload, 0), 0)
    miss_no = next((m for m in prog_no["missed"] if m["item_id"] == "TC-no-kc-miss"), None)
    if not miss_no or miss_no["error_reason"] is not None:
        errs.append("a miss on a row without kc_id invented a non-null error_reason: %r" % miss_no)
    errs += _validate_remediation_index()
    return errs


def _self_test():
    errs = validate()
    # meta: the static guard must CATCH a grader that reads a self-report flag.
    sample = 'def grade(row, payload):\n    return {"passed": payload.get("passed")}\n'
    if not _SELF_REPORT_READ.search(sample):
        errs.append("META: self-report guard failed to flag a payload.get('passed') read")
    # meta: schema checker must reject a malformed event (bad enum).
    bad = {"schema": "fusha/tutor-event@1", "seq": 0, "now_day": 0, "item_id": "x", "level": "1",
           "outcome": "NOPE", "grade": {"passed": True, "reasoning_passed": True, "two_vote_status": "n/a",
                                        "forbidden_hit": False, "cleared": True}, "box_before": 0, "box_after": 1}
    if not _validate_obj(bad, _EVENT_SCHEMA):
        errs.append("META: schema checker accepted a bad outcome enum")
    index_text = open(_REMEDIATION_INDEX, encoding="utf-8").read()
    bad_posture = index_text.replace("| `kc-hidden-proclitic` | `documented_only` |",
                                     "| `kc-hidden-proclitic` | `emittable` |", 1)
    if not _validate_remediation_index(bad_posture):
        errs.append("META: remediation index accepted an unreachable KC as emittable")
    bad_equivalence = index_text.replace("it is not an equivalence assertion for either KC",
                                         "it is an equivalence assertion for either KC", 1)
    if not _validate_remediation_index(bad_equivalence):
        errs.append("META: remediation index accepted a non-crosswalk KC equivalence")
    for e in errs:
        print("FAIL " + e)
    if not errs:
        print("ok   validate_tutor_runtime self-test: no self-report grading; the runtime never clears a "
              "two_vote_required row (a declared second_check Boolean is not an occurrence-bound canonical "
              "vote artifact); full-pass-only "
              "promotion; --write-gated; deterministic; event/progress schema-conformant; source-clean")
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description="Validate the offline tutor runtime + scheduler contracts.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    errs = validate()
    for e in errs:
        print("FAIL " + e)
    print("tutor runtime contract: %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
