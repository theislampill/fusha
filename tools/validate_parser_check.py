#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_parser_check — conformance gate for Fusha parser/checker CheckUnits (FPC-IR).

Validates a CheckUnit JSONL against qamus/schemas/parser-check-ir.schema.json + grammar-issue.schema.json, then
enforces the six required FAIL conditions (parserplans/009 + 016):

  1. A parser/checker issue lacks a source address or an exact token/card edge.
  2. A public-facing field leaks source names / MCP/QAC/Tafsir labels / local paths / process prose.
  3. A two-vote / iʿrāb-sensitive issue is marked auto_safe.
  4. A clitic/preposition/suffix issue is collapsed into a host-only hover (a `grounded` verdict that silently
     drops a clitic/preposition/pronoun contribution, with no issue recorded).
  5. A phrase-level translation is used as a token-level hover without a token-contribution explanation
     (a `grounded` verdict whose hover surfaces a must_not_surface phrase, no token_contribution, no issue).
  6. A parser diagnostic cannot route to sarf / nahw / curriculum / validator / owner review / scholar-iʿrāb review.

CLI:
  python3 tools/validate_parser_check.py <check_units.jsonl>   # validate a file
  python3 tools/validate_parser_check.py --self-test           # good units pass; each of the 6 bad units rejected

Stdlib only; reuses the repo's mini schema validator. Exit non-zero on any violation.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools.validate_linguistic_decisions import validate_schema, _GATE_RANK  # noqa: E402
from tools import fusha_check as FC  # noqa: E402

IR_SCHEMA = os.path.join(_REPO, "qamus", "schemas", "parser-check-ir.schema.json")
ISSUE_SCHEMA = os.path.join(_REPO, "qamus", "schemas", "grammar-issue.schema.json")
_LANES = {"sarf", "nahw", "curriculum", "validator", "owner_review", "scholar_irab_review"}
# iʿrāb / two-vote-sensitive issue classes that may never be auto_safe (FAIL condition 3)
_TWO_VOTE_SENSITIVE = {"weak_irab_reasoning", "ma_function_unresolved_or_wrong", "host_only_preposition_hover",
                       "passive_voice_hidden"}
_CLITIC_SUFFIX = {"hidden_clitic_or_proclitic", "host_only_preposition_hover", "suffix_pronoun_missing"}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _public_strings(unit):
    """Yield (label, string) for every PUBLIC-facing field (what ships to a reader)."""
    for i in unit.get("issues") or []:
        yield "issue.explanation", i.get("explanation", "")
        # observed/expected are committed, reader-reachable fields; the checker echoes (redacted) claim text here.
        yield "issue.observed", i.get("observed", "") or ""
        yield "issue.expected", i.get("expected", "") or ""
    for t in unit.get("tokens") or []:
        for f in ("gloss", "learner_explanation"):
            yield "token.%s" % f, t.get(f, "") or ""
        pk = t.get("parse_key") or {}
        yield "token.parse_key", json.dumps(pk, ensure_ascii=False)
    # a hover that the unit ACCEPTS (grounded) is public; a rejected claim's hover is not
    grounded = {v["claim_id"] for v in unit.get("verdicts") or [] if v["status"] == "grounded"}
    for c in unit.get("claims") or []:
        if c.get("claim_id") in grounded and c.get("claim_type") == "hover_gloss":
            yield "accepted_hover", c.get("claimed_value", "")


def validate_unit(unit, schemas):
    """Return a list of (condition, message) violations for one CheckUnit."""
    ir_schema, issue_schema = schemas
    errors = []
    uid = unit.get("unit_id", "?")
    for e in validate_schema(unit, ir_schema):
        errors.append(("schema", "%s: %s" % (uid, e)))

    issues = unit.get("issues") or []
    for idx, issue in enumerate(issues):
        for e in validate_schema(issue, issue_schema):
            errors.append(("schema", "%s issue[%d]: %s" % (uid, idx, e)))
        # FAIL 1: source address + token/card edge required + non-empty
        if not (issue.get("target_address") or "").strip() or not (issue.get("token_or_card_edge") or "").strip():
            errors.append(("1", "%s issue[%d] %s lacks source address / token-card edge" % (uid, idx, issue.get("issue_class"))))
        # FAIL 3: two-vote/iʿrāb-sensitive issue marked auto_safe
        if issue.get("issue_class") in _TWO_VOTE_SENSITIVE and issue.get("gate") == "auto_safe":
            errors.append(("3", "%s issue[%d] %s is two-vote-sensitive but gate=auto_safe" % (uid, idx, issue.get("issue_class"))))
        # FAIL 6: diagnostic must route
        rt = issue.get("route_to") or {}
        if rt.get("lane") not in _LANES or not (rt.get("procedure") or "").strip():
            errors.append(("6", "%s issue[%d] %s cannot route (lane=%r procedure=%r)" % (uid, idx, issue.get("issue_class"), rt.get("lane"), rt.get("procedure"))))
        elif not os.path.exists(os.path.join(_REPO, rt["procedure"])):
            errors.append(("6", "%s issue[%d] route procedure %r does not exist on disk" % (uid, idx, rt["procedure"])))

    # FAIL 2: public-facing leak
    for label, s in _public_strings(unit):
        if FC.LEAK_RE.search(s or ""):
            errors.append(("2", "%s %s leaks an internal source name / path" % (uid, label)))
    pb = unit.get("public_boundary") or {}
    if (pb.get("public_gloss_src"), pb.get("public_gloss_kind"), pb.get("public_gloss_lang")) != ("qamus", "authored", "en") \
            or pb.get("external_source_names_public") is True:
        errors.append(("2", "%s public_boundary is not {src:qamus,kind:authored,lang:en,external:false}" % uid))

    # FAIL 4 + 5: a GROUNDED verdict must not silently drop a clitic/preposition/suffix piece (4) or use a
    # phrase-level hover without a token-contribution (5). Recompute detector issues; a grounded claim must be clean.
    tokens_by_loc = {t.get("loc"): t for t in unit.get("tokens") or []}
    recorded = {(i.get("issue_class"), i.get("claim_id")) for i in issues}
    for v in unit.get("verdicts") or []:
        if v.get("status") != "grounded":
            continue
        claim = next((c for c in unit.get("claims") or [] if c.get("claim_id") == v.get("claim_id")), None)
        if not claim:
            continue
        tok, _matched = FC.target_token(tokens_by_loc, claim.get("target", ""))  # SHARED resolver — cannot drift
        would = {i["issue_class"] for i in FC._detect_token_claim(tok, claim)} if tok else set()
        for cls in would & _CLITIC_SUFFIX:
            if (cls, claim.get("claim_id")) not in recorded:
                errors.append(("4", "%s grounded claim %s collapses %s into a host-only hover (issue not recorded)" % (uid, claim.get("claim_id"), cls)))
        if "phrase_translation_used_as_token_hover" in would and ("phrase_translation_used_as_token_hover", claim.get("claim_id")) not in recorded:
            errors.append(("5", "%s grounded claim %s uses a phrase-level hover as a token hover without a token-contribution" % (uid, claim.get("claim_id"))))
    return errors


def validate_file(path):
    schemas = (_load(IR_SCHEMA), _load(ISSUE_SCHEMA))
    n, all_errors = 0, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            all_errors.extend(validate_unit(json.loads(line), schemas))
    return n, all_errors


# ---------------------------------------------------------------------------
# self-test: the checker's own outputs pass; each of the 6 bad units is rejected by its condition
# ---------------------------------------------------------------------------
def _bad_units():
    """One deliberately-malformed CheckUnit per FAIL condition -> (condition, unit)."""
    base = lambda uid: {  # noqa: E731
        "schema": "fusha/parser-check-ir@1", "unit_id": uid,
        "source_unit": {"address": "quran:1:1", "kind": "quran_ayah", "scope": "in_scope_source_addressed", "display_surface": "x"},
        "segments": [{"canonical_loc": "quran:1:1", "token_locs": ["quran:1:1:1"]}],
        "tokens": [], "claims": [], "issues": [], "verdicts": [],
        "public_boundary": dict(FC._PUBLIC_BOUNDARY), "evidence": {"labels": [], "gate": None},
        "summary": {"live_writes": 0, "by_verdict": {}, "by_issue_class": {}},
    }
    out = []

    # cond 1: issue with empty target_address / token_or_card_edge
    u = base("bad-1")
    iss = FC._mk_issue("suffix_pronoun_missing", "1:1:1")
    iss["target_address"] = ""
    iss["token_or_card_edge"] = ""
    u["issues"] = [iss]
    out.append(("1", u))

    # cond 2: public leak in issue.explanation
    u = base("bad-2")
    iss = FC._mk_issue("suffix_pronoun_missing", "1:1:1")
    iss["explanation"] = "Per the QAC tagset, the suffix is an object pronoun."  # names QAC -> leak
    u["issues"] = [iss]
    out.append(("2", u))

    # cond 2b: an external-translation brand echoed into a committed issue.observed (the real licensing leak vector)
    u = base("bad-2b")
    iss = FC._mk_issue("suffix_pronoun_missing", "1:1:1")
    iss["observed"] = "Badr (Sahih International)"  # set directly to simulate an un-redacted echo
    u["issues"] = [iss]
    out.append(("2", u))

    # cond 3: two-vote-sensitive issue marked auto_safe
    u = base("bad-3")
    iss = FC._mk_issue("weak_irab_reasoning", "1:1:1")
    iss["gate"] = "auto_safe"
    u["issues"] = [iss]
    out.append(("3", u))

    # cond 4: grounded verdict collapses a preposition into host-only, no issue recorded
    u = base("bad-4")
    u["tokens"] = [FC._tok("1:1:1", "بِسْمِ", "noun",
                           [{"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "in"},
                            {"role": "stem", "surface": "سْمِ", "gloss_contribution": "name"}], must_surface=["in", "name"])]
    u["claims"] = [{"claim_id": "c1", "target": "1:1:1", "claim_type": "hover_gloss", "claimed_value": "name",
                    "claimed_reasoning": None, "proposer": "model"}]
    u["verdicts"] = [{"claim_id": "c1", "status": "grounded", "gate": "auto_safe", "issue_ids": [], "route_to": [], "reasoning_checked": True}]
    out.append(("4", u))

    # cond 5: grounded verdict uses a phrase-level hover (must_not_surface) without token_contribution, no issue
    u = base("bad-5")
    u["tokens"] = [FC._tok("33:63:1", "يَسْأَلُكَ", "verb",
                           [{"role": "stem", "surface": "يَسْأَلُ", "gloss_contribution": "asks"},
                            {"role": "object_pronoun", "surface": "كَ", "gloss_contribution": "you"}],
                           must_surface=["ask", "you"], must_not=["the people"])]
    u["source_unit"]["address"] = "quran:33:63"
    u["claims"] = [{"claim_id": "c1", "target": "33:63:1", "claim_type": "hover_gloss",
                    "claimed_value": "the people ask you", "claimed_reasoning": None, "token_contribution": None, "proposer": "model"}]
    u["verdicts"] = [{"claim_id": "c1", "status": "grounded", "gate": "auto_safe", "issue_ids": [], "route_to": [], "reasoning_checked": True}]
    out.append(("5", u))

    # cond 6: issue with an invalid route lane
    u = base("bad-6")
    iss = FC._mk_issue("suffix_pronoun_missing", "1:1:1")
    iss["route_to"] = {"lane": "banana", "procedure": "nowhere.md"}
    u["issues"] = [iss]
    out.append(("6", u))
    return out


def _self_test():
    schemas = (_load(IR_SCHEMA), _load(ISSUE_SCHEMA))
    failures = []
    # good units: the checker's own outputs must validate clean
    for unit_in, _ in FC.regression_units():
        out = FC.check_unit(json.loads(json.dumps(unit_in)))
        errs = validate_unit(out, schemas)
        if errs:
            failures.append("good unit %s should validate clean but: %s" % (out.get("unit_id"), errs[:2]))
    # bad units: each must be rejected by its specific condition
    for cond, unit in _bad_units():
        errs = validate_unit(unit, schemas)
        conds = {c for c, _ in errs}
        if cond not in conds:
            failures.append("bad unit %s should trip FAIL condition %s but tripped %s" % (unit.get("unit_id"), cond, sorted(conds)))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_parser_check self-test: 12 good units clean; all 6 FAIL conditions reject")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate Fusha parser/checker CheckUnits.")
    ap.add_argument("path", nargs="?", help="CheckUnit JSONL")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.path:
        ap.error("need a path or --self-test")
    n, errors = validate_file(a.path)
    for cond, msg in errors:
        print("FAIL [cond %s] %s" % (cond, msg))
    print("checked %d unit(s), %d violation(s)" % (n, len(errors)))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
