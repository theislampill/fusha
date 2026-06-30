#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rich_hover_flywheel — deterministic rich-hover CANDIDATE generator (the gold-data flywheel front-end).

Given a SOURCE-ADDRESSED token (exact S:A:W), it produces a reviewable rich-hover candidate packet
(qamus/schemas/rich-hover-candidate.schema.json): a morphosyntax-token-shaped token (decision_state=rich_candidate)
+ the fusha_check verdict/issues + a gate + a blocker_status + a suggested_next_action. It then PROJECTS each candidate
into the existing certification-row shape so the output round-trips into tools/validate_rich_hover_certification.py
(validate_certification / validate_evidence) — proving the candidate FEEDS the certification queue. It NEVER certifies,
NEVER applies live, NEVER sets rich_certified, and only ever runs on source-addressed tokens (arbitrary text gets
diagnostics from fusha_text_check.py, not candidates). Identity stays exact quran:S:A:W + wbw:S:A:W; parse_key is a
grammar-family key, never identity. Public fields are source-clean {src:qamus,kind:authored,lang:en}; no external gloss
text. Dry-run: live_writes == 0. See parserplans/general-fusha-grammar-checker/{014,021,022}.

CLI:
  python3 tools/rich_hover_flywheel.py --in <source_tokens.jsonl> --out <-|path>   # emit candidates
  python3 tools/rich_hover_flywheel.py --self-test                                 # round-trips into the cert validator
  python3 tools/rich_hover_flywheel.py --emit-fixture <path.jsonl>                 # regenerate the committed fixture
  python3 tools/rich_hover_flywheel.py --explain-one <S:A:W>                       # one candidate, human-readable
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import fusha_check as FC  # noqa: E402
from tools.validate_morphosyntax_token_metadata import DISPLAY_CLASS_BY_ROLE, DISPLAY_LABEL_BY_ROLE  # noqa: E402

SCHEMA = "fusha/rich-hover-candidate@1"
_NOUN_POS = {"noun", "proper_noun", "adjective", "participle", "masdar"}

# force_state may only steer the candidate to a NON-CERTIFIED review state — never to rich_certified or live-apply.
_ALLOWED_FORCE_STATES = {"blocked", "pending", "preview_only", "token_only_override"}

# verdict.status -> (certification_state, suggested_next_action, default blocker_status)
_STATE_MAP = {
    "grounded": ("preview_only", "ready_for_cert_review", None),
    "needs_two_vote": ("pending", "route_to_two_vote", "function_attachment_unresolved"),
    "needs_human_review": ("pending", "route_to_human_source_review", "source_evidence_needed"),
    "unsafe_reasoning": ("pending", "route_to_scholar_irab_review", "weak_irab_reasoning"),
    "contradicted": ("pending", "route_to_two_vote", "function_attachment_unresolved"),
    "pending": ("pending", "hold_pending_blocker", "source_evidence_needed"),
    "out_of_scope": ("pending", "route_to_human_source_review", "source_evidence_needed"),
}


def _qg_class(role, pos):
    if role == "stem":
        return "qg-noun-stem" if pos in _NOUN_POS else "qg-verb-stem"
    return DISPLAY_CLASS_BY_ROLE.get(role, "qg-unknown")


def _parse_key(segments, pos):
    labels = []
    for s in segments:
        labels.append(DISPLAY_LABEL_BY_ROLE.get(s["role"], "X"))
    return "+".join(labels) or "X"


def _parse_components(segments):
    """Learner-facing parse rows (so the compact ASCII parse_key.key is not the only legend for a queue UI)."""
    return [{"label": DISPLAY_LABEL_BY_ROLE.get(s["role"], s["role"]),
             "value": s.get("gloss_contribution") or s["role"].replace("_", " ")} for s in segments]


def _contribution_explanation(segments):
    parts = []
    for s in segments:
        gc = s.get("gloss_contribution")
        if gc:
            parts.append("%s contributes “%s”" % (DISPLAY_LABEL_BY_ROLE.get(s["role"], s["role"]), gc))
        elif s["role"] != "stem":
            parts.append("%s is present and must be surfaced" % DISPLAY_LABEL_BY_ROLE.get(s["role"], s["role"]))
    return "; ".join(parts) + "." if parts else "Single lexical contribution."


def candidate_for(src):
    """Build a rich-hover candidate from a source-addressed token spec. src keys:
       loc, surface, pos, segments[{role,surface,gloss_contribution}], gloss, sarf?, nahw?, must_surface?, must_not?,
       claim_type?, claimed_value?, claimed_reasoning?, claimed_gate?, token_contribution?, force_state?, force_blocker?, card_address?
    """
    loc = src["loc"]
    ayah = ":".join(loc.split(":")[:2])
    surface = src["surface"]
    pos = src.get("pos", "noun")
    segments = src["segments"]
    res = FC.resolve_address("quran:" + loc)
    if res["scope"] != "in_scope_source_addressed":
        raise ValueError("rich_hover_flywheel runs only on source-addressed tokens; %s is %s" % (loc, res["scope"]))

    # build the per-token CheckUnit + claim, run the deterministic verifier (reuse, no fork)
    token = FC._tok(loc, surface, pos, segments, sarf=src.get("sarf"),
                    must_surface=src.get("must_surface"), must_not=src.get("must_not"),
                    nahw=src.get("nahw"), gloss=src.get("gloss", "(authored)"))
    claim = {
        "claim_id": "c1", "target": loc, "claim_type": src.get("claim_type", "hover_gloss"),
        "claimed_value": src.get("claimed_value", src.get("gloss", "")),
        "claimed_reasoning": src.get("claimed_reasoning"),
        "token_contribution": src.get("token_contribution"), "proposer": "model",
    }
    if src.get("claimed_gate"):
        claim["claimed_gate"] = src["claimed_gate"]
    unit = FC._unit("flywheel-%s" % loc.replace(":", "_"), "quran:" + ayah, "quran_ayah", surface, token, [claim])
    checked = FC.check_unit(json.loads(json.dumps(unit)))
    verdict = (checked.get("verdicts") or [{"status": "pending", "gate": "two_vote_required"}])[0]
    issues = checked.get("issues") or []

    cert_state, next_action, default_blocker = _STATE_MAP.get(verdict["status"], ("pending", "hold_pending_blocker", "source_evidence_needed"))
    # force_state is honored ONLY if it names a non-certified review state; anything else (incl. rich_certified,
    # or arbitrary --in injection) is ignored and the verdict-derived state stands. This layer never certifies.
    if src.get("force_state") in _ALLOWED_FORCE_STATES:
        cert_state = src["force_state"]
        next_action = "hold_pending_blocker" if cert_state == "blocked" else next_action
    blocker_status = None if verdict["status"] == "grounded" else (src.get("force_blocker") or default_blocker)

    qg_classes = [_qg_class(s["role"], pos) for s in segments]
    # learner route: the first parser issue's route, else a composition drill
    if issues:
        lr = {"lane": issues[0]["route_to"]["lane"], "procedure": issues[0]["route_to"]["procedure"]}
    else:
        lr = {"lane": "curriculum", "procedure": "curriculum/drills/hover-composition-and-routing.md"}

    cand = {
        "schema": SCHEMA,
        "source_unit": {"address": "quran:" + ayah, "kind": "quran_ayah", "scope": "in_scope_source_addressed"},
        "card_address": _redacted(src.get("card_address") or "quran:%s#word=%s" % (ayah, loc.split(":")[2])),
        "token_address": loc, "quran_loc": loc, "wbw_loc": "wbw:%s" % loc,
        "surface": surface, "displayed_surface": surface, "canonical_surface": surface,
        "display_local_to_canonical_crosswalk": None,
        "decision_state": "rich_candidate",
        "segments": [{"role": s["role"], "surface": s["surface"], "gloss_contribution": s.get("gloss_contribution")} for s in segments],
        "qg_segment_classes": qg_classes, "qg_palette": "qamus-grammar-v1",
        "parse_key": {"key": _parse_key(segments, pos),
                      "summary": _redacted(src.get("parse_summary") or ("Token: %s." % src.get("gloss", surface))),
                      "components": _parse_components(segments)},
        "hover_title": _redacted(src.get("gloss", surface)),
        "token_gloss": _redacted(src.get("gloss", "(authored)")),
        "token_contribution_explanation": _redacted(_contribution_explanation(segments)),
        "learner_route": lr,
        "parser_issues": issues,
        "verdict": {"status": verdict["status"], "gate": verdict["gate"], "reasoning_checked": verdict.get("reasoning_checked")},
        "gate": verdict["gate"],
        "public_boundary": {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                            "public_gloss_lang": "en", "external_source_names_public": False},
        "blocker_status": blocker_status,
        "suggested_next_action": next_action,
        "live_writes": 0,
        "_cert_state": cert_state,  # internal hint for to_cert_row; stripped before emit
    }
    # dry-run + segment-exactness invariants
    assert "".join(s["surface"] for s in cand["segments"]) == surface, "segments must concat to surface"
    return cand


def _redacted(s):
    return FC._redact(s) if isinstance(s, str) else s


def to_cert_row(cand):
    """Project a rich-hover candidate into the existing certification-row shape (validate_rich_hover_certification)."""
    seg_roles = [s["role"] for s in cand["segments"]]
    state = cand.get("_cert_state") or ("preview_only" if cand["verdict"]["status"] == "grounded" else "pending")
    # hard backstop: this layer NEVER emits rich_certified (renderer not owner-authorized). Clamp any stray state.
    if state not in {"preview_only", "pending", "blocked", "token_only_override", "renderer_requirement", "no_op"}:
        state = "pending"
    return {
        "tranche_id": "FLYWHEEL-CANDIDATE",
        "source_record": cand["card_address"],
        "quran_loc": "quran:%s" % cand["quran_loc"],
        "wbw_loc": cand["wbw_loc"],
        "surface": cand["displayed_surface"],
        "current_gloss": cand["token_gloss"],
        "source_decision_state": "rich_candidate",
        "certification_state": state,
        "parse_key": cand["parse_key"]["key"],
        "segment_roles": seg_roles,
        "public_payload": {"gloss": cand["token_gloss"], "src": "qamus", "kind": "authored", "lang": "en"},
        "gates": {
            "address": "pass", "public_boundary": "pass", "sarf": "pass", "nahw": "pass",
            "learner": "pass", "source_two_vote": "required_not_complete",
            "renderer": "fixture_not_live", "owner": "not_authorized",
        },
        "segment_surface_exact": True,
        "component_candidates_can_certify": False,
        "parse_key_primary_identity": False,
        "may_apply_live": False,
        "next_action": cand["suggested_next_action"],
    }


def _emit_candidate(cand):
    c = dict(cand)
    c.pop("_cert_state", None)
    return c


# ---------------------------------------------------------------------------
# regression sources (the required examples: عَلَيْنَا, وما, بِبَدْرٍ/بِسَلَامٍ, verb+obj, passive, dual/plural, phrase-vs-token, weak-iʿrāb, blocked)
# ---------------------------------------------------------------------------
def regression_sources():
    return [
        # 1. عَلَيْنَا — preposition + attached pronoun (the canonical motivating example), CLEAN.
        {"name": "alayna", "loc": "2:286:9", "surface": "عَلَيْنَا", "pos": "noun",
         "segments": [{"role": "preposition", "surface": "عَلَيْ", "gloss_contribution": "upon"},
                      {"role": "object_pronoun", "surface": "نَا", "gloss_contribution": "us"}],
         "gloss": "upon us", "must_surface": ["upon", "us"],
         "parse_summary": "Preposition ʿalā giving the relation over/upon + attached 1p pronoun nā (us)."},
        # 2. وما — waw + function-specific mā (function unresolved -> PENDING, not guessed).
        {"name": "wama", "loc": "3:7:27", "surface": "وَمَا", "pos": "particle",
         "segments": [{"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
                      {"role": "preventive_ma", "surface": "مَا", "gloss_contribution": None}],
         "gloss": "and …", "nahw": {"function": None},
         "parse_summary": "Conjunction wāw + multi-function mā; mā's function (negation/relative/interrogative) is unresolved."},
        # 3. بِبَدْرٍ — bāʾ + host place-name, CLEAN.
        {"name": "bibadr", "loc": "3:123:4", "surface": "بِبَدْرٍ", "pos": "proper_noun",
         "segments": [{"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "at"},
                      {"role": "stem", "surface": "بَدْرٍ", "gloss_contribution": "Badr"}],
         "gloss": "at Badr", "sarf": {"case": "genitive"}, "must_surface": ["at", "Badr"],
         "parse_summary": "Preposition bāʾ (at) + place-name Badr in the genitive."},
        # 4. بِسَلَٰمٍ — bāʾ + host, CLEAN.
        {"name": "bisalam", "loc": "11:48:4", "surface": "بِسَلَٰمٍ", "pos": "noun",
         "segments": [{"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "with"},
                      {"role": "stem", "surface": "سَلَٰمٍ", "gloss_contribution": "peace"}],
         "gloss": "with peace", "sarf": {"case": "genitive"}, "must_surface": ["with", "peace"],
         "parse_summary": "Preposition bāʾ (with) + noun salām (peace) in the genitive."},
        # 5. جَادَلُوكَ — verb + attached object pronoun, CLEAN.
        {"name": "jadaluka", "loc": "22:68:2", "surface": "جَادَلُوكَ", "pos": "verb",
         "segments": [{"role": "stem", "surface": "جَادَلُو", "gloss_contribution": "they argued"},
                      {"role": "object_pronoun", "surface": "كَ", "gloss_contribution": "with you"}],
         "gloss": "they argued with you", "sarf": {"voice": "active", "verb_form": "III"},
         "must_surface": ["they", "you"],
         "parse_summary": "Form III perfect verb (they argued) + attached 2ms object pronoun (you)."},
        # 6. قِيلَ — passive verb, CLEAN.
        {"name": "qila", "loc": "11:48:1", "surface": "قِيلَ", "pos": "verb",
         "segments": [{"role": "stem", "surface": "قِيلَ", "gloss_contribution": "it was said"}],
         "gloss": "it was said", "sarf": {"voice": "passive", "tense_aspect": "perfect"}, "must_surface": ["was said"],
         "parse_summary": "Form I passive perfect verb (it was said)."},
        # 7. ٱلْعَٰلَمِينَ — visible plural suffix, CLEAN.
        {"name": "alamin", "loc": "1:2:4", "surface": "ٱلْعَٰلَمِينَ", "pos": "noun",
         "segments": [{"role": "definite_article", "surface": "ٱلْ", "gloss_contribution": "the"},
                      {"role": "stem", "surface": "عَٰلَمِينَ", "gloss_contribution": "worlds"}],
         "gloss": "the worlds", "sarf": {"noun_number": "plural", "case": "genitive", "definiteness": "definite"},
         "must_surface": ["the", "worlds"],
         "parse_summary": "Definite article + sound plural noun (the worlds) in the genitive."},
        # 8. يَسْأَلُكَ — phrase-vs-token: the token contributes ‘asks you’, NOT ‘the people ask you’. CLEAN (token-level).
        {"name": "yasaluka", "loc": "33:63:1", "surface": "يَسْأَلُكَ", "pos": "verb",
         "segments": [{"role": "stem", "surface": "يَسْأَلُ", "gloss_contribution": "asks"},
                      {"role": "object_pronoun", "surface": "كَ", "gloss_contribution": "you"}],
         "gloss": "asks you", "sarf": {"voice": "active"}, "must_surface": ["ask", "you"], "must_not": ["the people"],
         "token_contribution": "asks you",
         "parse_summary": "Imperfect verb (asks) + attached 2ms object pronoun (you); the subject is a separate word."},
        # 9. weak iʿrāb — right case, no governor justification, marked auto_safe -> unsafe_reasoning.
        {"name": "weak-irab", "loc": "16:16:2", "surface": "وَبِٱلنَّجْمِ", "pos": "noun",
         "segments": [{"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
                      {"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "by"},
                      {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
                      {"role": "stem", "surface": "نَّجْمِ", "gloss_contribution": "star"}],
         "gloss": "and by the star", "sarf": {"case": "genitive", "definiteness": "definite"},
         "claim_type": "case_mood", "claimed_value": "genitive", "claimed_gate": "auto_safe",
         "parse_summary": "Genitive after the preposition bāʾ — the governing ʿāmil must be stated, not assumed."},
        # 10. لِمَا — lām + mā, function/attachment unresolved -> BLOCKED, must stay pending (not guessed).
        {"name": "lima-blocked", "loc": "2:213:37", "surface": "لِمَا", "pos": "particle",
         "segments": [{"role": "prefix_preposition", "surface": "لِ", "gloss_contribution": "for"},
                      {"role": "preventive_ma", "surface": "مَا", "gloss_contribution": None}],
         "gloss": "for …", "nahw": {"function": None}, "force_state": "blocked",
         "force_blocker": "function_attachment_unresolved",
         "parse_summary": "Preposition lām + mā whose relative/attachment function needs nahw review before any gloss."},
    ]


def _self_test():
    import tempfile
    failures = []
    cands = []
    for src in regression_sources():
        try:
            cands.append(candidate_for(src))
        except Exception as e:  # noqa: BLE001
            failures.append("%s: candidate_for raised %s" % (src["name"], e))
    # structural assertions
    for c in cands:
        nm = c["token_address"]
        if c["decision_state"] != "rich_candidate":
            failures.append("%s: decision_state must be rich_candidate" % nm)
        if "".join(s["surface"] for s in c["segments"]) != c["displayed_surface"]:
            failures.append("%s: segments do not concat to surface" % nm)
        if c["verdict"]["status"] != "grounded" and not c["blocker_status"]:
            failures.append("%s: non-grounded candidate must carry a blocker_status" % nm)
        if c["verdict"]["status"] == "grounded" and c["blocker_status"]:
            failures.append("%s: grounded candidate must not carry a blocker_status" % nm)
        for q in c["qg_segment_classes"]:
            if not q.startswith("qg-"):
                failures.append("%s: qg class %r out of palette" % (nm, q))
    # behaviour assertions on the required examples
    by_name = {s["name"]: candidate_for(s) for s in regression_sources()}
    if by_name["weak-irab"]["verdict"]["status"] != "unsafe_reasoning":
        failures.append("weak-irab: expected unsafe_reasoning (got %s)" % by_name["weak-irab"]["verdict"]["status"])
    if by_name["wama"]["verdict"]["status"] == "grounded":
        failures.append("wama: function-unresolved mā must not be grounded")
    if by_name["lima-blocked"]["_cert_state"] != "blocked":
        failures.append("lima-blocked: must project to certification_state=blocked")
    if by_name["bibadr"]["verdict"]["status"] != "grounded":
        failures.append("bibadr: clean preposition+host should be grounded")
    if by_name["alayna"]["verdict"]["status"] != "grounded":
        failures.append("alayna: clean preposition+pronoun should be grounded")
    # this layer NEVER certifies: an injected force_state=rich_certified must be clamped to a review state.
    _inj = next(s for s in regression_sources() if s["name"] == "bibadr")
    if to_cert_row(candidate_for(dict(_inj, force_state="rich_certified")))["certification_state"] == "rich_certified":
        failures.append("force_state=rich_certified must be clamped (this layer never certifies)")

    # THE ROUND-TRIP (D4): the projected cert rows are accepted by the existing certification validator.
    from tools import validate_rich_hover_certification as CERT
    rows = [to_cert_row(c) for c in cands]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        path = fh.name
    try:
        cert_errors = CERT.validate_certification(path)
    finally:
        os.unlink(path)
    if cert_errors:
        failures.append("ROUND-TRIP into validate_rich_hover_certification FAILED: %s" % cert_errors[:3])

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   rich_hover_flywheel self-test: %d candidates, segments exact, blocker discipline, "
              "and the projected cert rows round-trip into validate_rich_hover_certification" % len(cands))
    return 0 if not failures else 1


def emit_fixture(path):
    cands = [_emit_candidate(candidate_for(s)) for s in regression_sources()]
    with open(path, "w", encoding="utf-8") as fh:
        for c in cands:
            fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {
        "schema": SCHEMA, "generator": "tools/rich_hover_flywheel.py --emit-fixture",
        "count": len(cands),
        "verdicts": sorted({c["verdict"]["status"] for c in cands}),
        "note": "Rich-hover CANDIDATE fixtures generated from source-addressed tokens. Authored gloss/explanation; "
                "Qurʾānic surfaces verbatim; public {src:qamus,kind:authored,lang:en}; no external gloss text. The rows "
                "FEED the certification queue (validate_rich_hover_certification) and are never live-applied. parserplans 014/021/022.",
        "row_schema": ["schema", "token_address", "quran_loc", "wbw_loc", "displayed_surface", "segments",
                       "qg_segment_classes", "parse_key", "token_gloss", "verdict", "gate", "blocker_status",
                       "suggested_next_action", "public_boundary"],
    }
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d candidates -> %s (+ .meta.json)" % (len(cands), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Rich-hover candidate flywheel (dry-run; feeds the cert queue).")
    ap.add_argument("--in", dest="infile", help="source-token JSONL")
    ap.add_argument("--out", dest="outfile", default="-")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    ap.add_argument("--explain-one", dest="explain_one", help="emit one candidate for a S:A:W from the regression set")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    if a.explain_one:
        src = next((s for s in regression_sources() if s["loc"] == a.explain_one), None)
        if not src:
            print("no regression source for %s; available: %s" % (a.explain_one, [s["loc"] for s in regression_sources()]))
            return 1
        c = _emit_candidate(candidate_for(src))
        print(json.dumps(c, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not a.infile:
        ap.error("need --in, --self-test, --emit-fixture, or --explain-one")
    cands = []
    with open(a.infile, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cands.append(_emit_candidate(candidate_for(json.loads(line))))
    sink = sys.stdout if a.outfile == "-" else open(a.outfile, "w", encoding="utf-8")
    for c in cands:
        sink.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
