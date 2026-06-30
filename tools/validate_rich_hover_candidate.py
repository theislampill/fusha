#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_rich_hover_candidate — conformance gate for rich-hover candidate packets (fusha/rich-hover-candidate@1).

Validates each candidate against qamus/schemas/rich-hover-candidate.schema.json, then enforces the required FAIL
conditions (parserplans/general-fusha-grammar-checker/022). A candidate FAILS if:

  1. no source address (token_address / quran_loc missing or not an exact S:A:W).
  2. no exact token/card edge (card_address or token_address missing/empty).
  3. no public_boundary, or a wrong one (not {src:qamus,kind:authored,lang:en,external:false}).
  4. a public field leaks a source/provenance/tool name or a local path (FC.LEAK_RE).
  5. a qg class is invented outside the qamus-grammar-v1 palette enum.
  6. a phrase-level translation is used as a token-level hover without a token-contribution explanation
     (token_contribution_explanation missing/empty while token_gloss is multi-word).
  7. a clitic/preposition/pronoun segment is collapsed into a host-only hover (a non-stem function segment with no
     gloss_contribution on a GROUNDED candidate that records no corresponding parser issue).
  8. a parser issue lacks a route (route_to).
  9. an iʿrāb/governor-sensitive parser issue is present while the candidate gate is auto_safe (no governor evidence).
 10. the candidate cannot route to a lane (learner_route.lane invalid OR suggested_next_action invalid OR
     decision_state != rich_candidate OR blocker discipline broken).

It also runs a ROUND-TRIP self-test: projecting a good candidate via rich_hover_flywheel.to_cert_row must be accepted
by tools/validate_rich_hover_certification.validate_certification (the candidate truly FEEDS the cert queue).

CLI:
  python3 tools/validate_rich_hover_candidate.py <candidates.jsonl>
  python3 tools/validate_rich_hover_candidate.py --self-test
Stdlib only; reuses the repo mini schema-validator + fusha_check.LEAK_RE. Exit non-zero on any violation.
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
from tools.validate_linguistic_decisions import validate_schema, _GATE_RANK  # noqa: E402
from tools import fusha_check as FC  # noqa: E402

SCHEMA_PATH = os.path.join(_REPO, "qamus", "schemas", "rich-hover-candidate.schema.json")
_SCHEMA = json.load(open(SCHEMA_PATH, encoding="utf-8"))
QG_ENUM = set(_SCHEMA["properties"]["qg_segment_classes"]["items"]["enum"])
_LANES = {"sarf", "nahw", "curriculum", "validator", "owner_review", "scholar_irab_review"}
_NEXT_ACTIONS = set(_SCHEMA["properties"]["suggested_next_action"]["enum"])
# iʿrāb/governor-sensitive issue classes that may never coexist with an auto_safe candidate gate (FAIL 9) — SHARED
# single source of truth (covers BOTH the source-addressed and the general vocabularies, so the two validators agree).
_TWO_VOTE_SENSITIVE = FC.IRAB_SENSITIVE_ISSUE_CLASSES
_LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")


def _public_strings(cand):
    yield "hover_title", cand.get("hover_title", "") or ""
    yield "token_gloss", cand.get("token_gloss", "") or ""
    yield "token_contribution_explanation", cand.get("token_contribution_explanation", "") or ""
    yield "card_address", cand.get("card_address", "") or ""  # a public source-graph edge field — must be leak-clean too
    pk = cand.get("parse_key") or {}
    yield "parse_key.key", pk.get("key", "") or ""
    yield "parse_key.summary", pk.get("summary", "") or ""
    for s in cand.get("segments") or []:
        yield "segment.gloss_contribution", s.get("gloss_contribution") or ""


def validate_candidate(cand):
    errors = []
    cid = cand.get("token_address", "?")
    for e in validate_schema(cand, _SCHEMA):
        errors.append(("schema", "%s: %s" % (cid, e)))

    # FAIL 1: exact source address
    if not _LOC_RE.match(str(cand.get("token_address") or "")) or not _LOC_RE.match(str(cand.get("quran_loc") or "")):
        errors.append(("1", "%s: missing/invalid exact S:A:W source address" % cid))
    if not str(cand.get("wbw_loc") or "").startswith("wbw:"):
        errors.append(("1", "%s: wbw_loc must start with wbw:" % cid))

    # FAIL 2: exact token/card edge
    if not (cand.get("card_address") or "").strip() or not (cand.get("token_address") or "").strip():
        errors.append(("2", "%s: missing token/card edge" % cid))

    # FAIL 3: public_boundary
    pb = cand.get("public_boundary") or {}
    if (pb.get("public_gloss_src"), pb.get("public_gloss_kind"), pb.get("public_gloss_lang")) != ("qamus", "authored", "en") \
            or pb.get("external_source_names_public") is not False:
        errors.append(("3", "%s: public_boundary is not {src:qamus,kind:authored,lang:en,external:false}" % cid))

    # FAIL 4: public leak
    for label, s in _public_strings(cand):
        if FC.LEAK_RE.search(s or ""):
            errors.append(("4", "%s: %s leaks an internal source name / path" % (cid, label)))

    # FAIL 5: invented qg class
    for q in cand.get("qg_segment_classes") or []:
        if q not in QG_ENUM:
            errors.append(("5", "%s: qg class %r is outside the qamus-grammar-v1 palette" % (cid, q)))
    if cand.get("qg_palette") not in (None, "qamus-grammar-v1"):
        errors.append(("5", "%s: qg_palette must be qamus-grammar-v1" % cid))

    # FAIL 6: phrase-translation-as-token without a contribution explanation
    expl = (cand.get("token_contribution_explanation") or "").strip()
    gloss = (cand.get("token_gloss") or "").strip()
    if not expl and len(gloss.split()) > 1:
        errors.append(("6", "%s: multi-word token_gloss without a token_contribution_explanation" % cid))

    # FAIL 7: a non-stem function segment with no gloss_contribution on a GROUNDED candidate is a collapsed clitic/
    # prep/pronoun (a grounded verdict carries no parser issue, so the dropped contribution is silent).
    status = (cand.get("verdict") or {}).get("status")
    issue_classes = {i.get("issue_class") for i in (cand.get("parser_issues") or [])}
    if status == "grounded":
        for s in cand.get("segments") or []:
            if s.get("role") != "stem" and not (s.get("gloss_contribution") or "").strip():
                errors.append(("7", "%s: function segment %r collapsed (no gloss_contribution) on a grounded candidate" % (cid, s.get("role"))))

    # FAIL 8: every parser issue routes
    for i in cand.get("parser_issues") or []:
        rt = i.get("route_to") or i.get("route") or {}
        if rt.get("lane") not in _LANES or not (rt.get("procedure") or "").strip():
            errors.append(("8", "%s: parser issue %s lacks a route" % (cid, i.get("issue_class"))))

    # FAIL 9: iʿrāb-sensitive issue + auto_safe gate
    if cand.get("gate") == "auto_safe" and (issue_classes & _TWO_VOTE_SENSITIVE):
        errors.append(("9", "%s: iʿrāb/governor-sensitive issue present but candidate gate=auto_safe" % cid))
    # FAIL 9 (gate↔verdict binding): the candidate's overall gate may not be weaker than its own verifier verdict.gate,
    # and a non-grounded verdict may never carry an auto_safe candidate gate (that would assert certainty the verdict denies).
    vgate = (cand.get("verdict") or {}).get("gate")
    if cand.get("gate") in _GATE_RANK and vgate in _GATE_RANK and _GATE_RANK[cand["gate"]] < _GATE_RANK[vgate]:
        errors.append(("9", "%s: candidate gate %s is weaker than its verdict.gate %s" % (cid, cand.get("gate"), vgate)))
    if status and status != "grounded" and cand.get("gate") == "auto_safe":
        errors.append(("9", "%s: non-grounded verdict (%s) but candidate gate=auto_safe" % (cid, status)))

    # FAIL 10: routability + decision-state + blocker discipline
    lr = cand.get("learner_route") or {}
    if lr.get("lane") not in _LANES or not (lr.get("procedure") or "").strip():
        errors.append(("10", "%s: learner_route cannot route (lane=%r)" % (cid, lr.get("lane"))))
    if cand.get("suggested_next_action") not in _NEXT_ACTIONS:
        errors.append(("10", "%s: suggested_next_action %r is not a known action" % (cid, cand.get("suggested_next_action"))))
    if cand.get("decision_state") != "rich_candidate":
        errors.append(("10", "%s: decision_state must be rich_candidate (never rich_certified/live)" % cid))
    if status == "grounded" and cand.get("blocker_status"):
        errors.append(("10", "%s: grounded candidate must not carry a blocker_status" % cid))
    if status and status != "grounded" and not cand.get("blocker_status"):
        errors.append(("10", "%s: non-grounded candidate must carry a blocker_status" % cid))

    # FAIL 5: exactly one qg display class per segment (a missing class = a segment with no colour role at render time)
    if len(cand.get("qg_segment_classes") or []) != len(cand.get("segments") or []):
        errors.append(("5", "%s: qg_segment_classes (%d) must align 1:1 with segments (%d)" % (
            cid, len(cand.get("qg_segment_classes") or []), len(cand.get("segments") or []))))

    # dry-run invariant
    if cand.get("live_writes", 0) != 0:
        errors.append(("1", "%s: live_writes != 0" % cid))
    # segment exactness
    if "".join(s.get("surface", "") for s in cand.get("segments") or []) != (cand.get("displayed_surface") or ""):
        errors.append(("7", "%s: segments do not concatenate to displayed_surface" % cid))
    return errors


def validate_file(path):
    n, all_errors, seen = 0, [], {}
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            n += 1
            row = json.loads(line)
            all_errors.extend(validate_candidate(row))
            # FAIL 20: the cert validator rejects duplicate (quran_loc, wbw_loc) pairs, so the candidate file must be unique too
            pair = (row.get("quran_loc"), row.get("wbw_loc"))
            if pair in seen:
                all_errors.append(("20", "%s: duplicate (quran_loc,wbw_loc) %r (first seen line %d)" % (row.get("token_address", "?"), pair, seen[pair])))
            seen[pair] = lineno
    return n, all_errors


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def _bad_candidates():
    from tools import rich_hover_flywheel as RHF
    good = RHF._emit_candidate(RHF.candidate_for(next(s for s in RHF.regression_sources() if s["name"] == "bibadr")))
    out = []

    b = json.loads(json.dumps(good)); b["token_address"] = ""; b["quran_loc"] = ""
    out.append(("1", b))

    b = json.loads(json.dumps(good)); b["card_address"] = ""
    out.append(("2", b))

    b = json.loads(json.dumps(good)); b["public_boundary"]["public_gloss_src"] = "external"
    out.append(("3", b))

    b = json.loads(json.dumps(good)); b["token_gloss"] = "at Badr (per the QAC tagset)"
    out.append(("4", b))

    b = json.loads(json.dumps(good)); b["qg_segment_classes"] = ["qg-rainbow", "qg-noun-stem"]
    out.append(("5", b))

    b = json.loads(json.dumps(good)); b["token_contribution_explanation"] = ""
    out.append(("6", b))

    # collapse the preposition segment on a grounded candidate (drop its contribution)
    b = json.loads(json.dumps(good))
    for s in b["segments"]:
        if s["role"] != "stem":
            s["gloss_contribution"] = None
    out.append(("7", b))

    b = json.loads(json.dumps(good))
    b["parser_issues"] = [{"issue_class": "host_only_preposition_hover", "gate": "two_vote_required"}]  # no route_to
    out.append(("8", b))

    b = json.loads(json.dumps(good))
    b["gate"] = "auto_safe"
    b["parser_issues"] = [{"issue_class": "weak_irab_reasoning", "gate": "two_vote_required",
                           "route_to": {"lane": "scholar_irab_review", "procedure": "nahw/procedures/irab-case-mood.md"}}]
    out.append(("9", b))

    b = json.loads(json.dumps(good)); b["decision_state"] = "rich_certified"
    out.append(("10", b))

    # FAIL 9 (gate↔verdict binding): a non-grounded verdict with an auto_safe candidate gate
    b = json.loads(json.dumps(good))
    b["gate"] = "auto_safe"
    b["verdict"] = {"status": "contradicted", "gate": "two_vote_required", "reasoning_checked": False}
    b["blocker_status"] = "function_attachment_unresolved"; b["parser_issues"] = []
    b["suggested_next_action"] = "route_to_two_vote"
    out.append(("9", b))

    # FAIL 5 (qg length): fewer display classes than segments
    b = json.loads(json.dumps(good)); b["qg_segment_classes"] = ["qg-preposition"]
    out.append(("5", b))
    return out


def _self_test():
    from tools import rich_hover_flywheel as RHF
    from tools import validate_rich_hover_certification as CERT
    import tempfile
    failures = []
    # good: the emitter's own candidates validate clean
    goods = [RHF._emit_candidate(RHF.candidate_for(s)) for s in RHF.regression_sources()]
    for c in goods:
        errs = validate_candidate(c)
        if errs:
            failures.append("good candidate %s should validate clean but: %s" % (c["token_address"], errs[:2]))
    # bad: each trips its condition
    for cond, c in _bad_candidates():
        conds = {x for x, _ in validate_candidate(c)}
        if cond not in conds:
            failures.append("bad candidate should trip FAIL %s but tripped %s" % (cond, sorted(conds)))
    # ROUND-TRIP: a validated good candidate projects to a cert row the cert validator accepts.
    rows = [RHF.to_cert_row(RHF.candidate_for(s)) for s in RHF.regression_sources()]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        path = fh.name
    try:
        cert_errors = CERT.validate_certification(path)
    finally:
        os.unlink(path)
    if cert_errors:
        failures.append("round-trip: validated candidates rejected by cert validator: %s" % cert_errors[:3])
    # FAIL 20 (file-level): two candidates sharing a (quran_loc, wbw_loc) must be rejected (the cert validator rejects dups)
    dup = RHF._emit_candidate(RHF.candidate_for(next(s for s in RHF.regression_sources() if s["name"] == "bibadr")))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        fh.write(json.dumps(dup, ensure_ascii=False) + "\n")
        fh.write(json.dumps(dup, ensure_ascii=False) + "\n")
        dpath = fh.name
    try:
        _, derrs = validate_file(dpath)
    finally:
        os.unlink(dpath)
    if not any(c == "20" for c, _ in derrs):
        failures.append("duplicate (quran_loc,wbw_loc) candidate pair must be rejected (FAIL 20)")
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_rich_hover_candidate self-test: emitter candidates clean; all FAIL conditions reject "
              "(incl. gate↔verdict binding + dup-pair); validated candidates round-trip into validate_rich_hover_certification")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate rich-hover candidate packets.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.path:
        ap.error("need a path or --self-test")
    n, errors = validate_file(a.path)
    for cond, msg in errors:
        print("FAIL [cond %s] %s" % (cond, msg))
    print("checked %d candidate(s), %d violation(s)" % (n, len(errors)))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
