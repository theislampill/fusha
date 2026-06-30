#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_check — the source-addressed Fusha parser/checker (P0 + smallest P1 slice).

Consumes a CheckUnit (FPC-IR; qamus/schemas/parser-check-ir.schema.json) carrying a source-addressed token and a
PROPOSED analysis (a Claim from an untrusted proposer), and returns the same CheckUnit with grammar Issues +
per-claim Verdicts + a summary. It is the deterministic VERIFIER in front of any model/tutor proposer:
"a correct answer with wrong iʿrāb reasoning is unsafe" (GP0). Source-addressed only — unaddressed input is
`out_of_scope`, never a guess.

Pipeline (parserplans/000 §3): anchor gate -> 12 deterministic detectors -> gate gate -> reasoning gate ->
routing gate (every issue MUST route, else the checker self-fails). Dry-run: no live writes, no network, no /srv.

CLI:
  python3 tools/fusha_check.py --in <check_units.jsonl> --out <-|path>   # check a batch
  python3 tools/fusha_check.py --self-test                              # the 7 regression examples + all 12 classes
  python3 tools/fusha_check.py --emit-fixture <path.jsonl>              # regenerate the committed regression fixture

This module is the generator for qamus/examples/parser_check_regression.sample.jsonl.
See parserplans/015-cli-api-prototype.md. No external gloss text; public output is {src:qamus,kind:authored,lang:en}.
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
from tools import normalize_ar as N  # noqa: E402
from tools.validate_linguistic_decisions import required_gate, _GATE_RANK  # noqa: E402
from tools.leak_sot import LEAK_RE  # noqa: E402,F401  (P2: the SINGLE leak source-of-truth; re-exported so every FC.LEAK_RE consumer gets it)

SPINE_PATH = os.path.join(_REPO, "qamus", "indexes", "current", "quran-usage-spine-full.jsonl")
ADDR_PATH = os.path.join(_REPO, "qamus", "indexes", "current", "source-address-full.jsonl")

# Public-surface leak tripwire is now the canonical SoT in tools/leak_sot.py (re-exported as LEAK_RE above). NOT proof
# of independence — a paste tripwire. Covers internal-source NAMES, translation brands, provenance labels, and paths.

# iʿrāb/governor-sensitive issue classes (both the source-addressed and the general/arbitrary vocabularies) that may
# never be auto_safe without governor reasoning. SINGLE SOURCE OF TRUTH — both rich-hover/text-check validators import it.
IRAB_SENSITIVE_ISSUE_CLASSES = frozenset({
    "weak_irab_reasoning", "ma_function_unresolved_or_wrong", "host_only_preposition_hover", "passive_voice_hidden",
    "possible_governor_unresolved", "possible_case_or_mood_requires_context", "possible_particle_function",
    "governor_not_justified",  # P2: a case asserted without a justifying governor (right answer, wrong/absent reason)
})
# An ACTIVE reading = a subject pronoun immediately followed by a non-auxiliary verb ("he said", "they slew him").
# Used to flag passive_voice_hidden WITHOUT false-positiving on bare past-participle glosses ("slain", "taken").
ACTIVE_RE = re.compile(
    r"\b(he|she|it|they|we|i|you)\s+(?!was\b|were\b|is\b|are\b|been\b|being\b|am\b|will\b|had\b|has\b|have\b|be\b)[a-z]+",
    re.I,
)


def _redact(s):
    """Redact a string that trips the leak tripwire, so untrusted claim text can never echo into a committed field."""
    return "<redacted: leak tripwire>" if s and LEAK_RE.search(s) else s

# Reconcile the three repo gate vocabularies onto the canonical GP0 4-tier (parserplans/000 §5).
GATE_ALIAS = {
    "auto_safe": "auto_safe", "token_review": "auto_safe", "auto_safe_after_preview": "auto_safe",
    "two_vote_required": "two_vote_required",
    "human_review_required": "human_source_review_required",
    "owner_review_required": "human_source_review_required",
    "human_source_review_required": "human_source_review_required",
    "never_auto": "never_auto_resolve", "never_auto_resolve": "never_auto_resolve",
    "unknown": "two_vote_required", None: "auto_safe", "": "auto_safe",
}

# segment role -> issue class
_CLITIC_ROLES = {
    "prefix_conjunction", "prefix_comitative_waw", "prefix_resumption_fa", "prefix_coordination_fa",
    "prefix_result_fa", "prefix_supplemental_fa", "prefix_cause_fa", "definite_article",
}
_PREP_ROLES = {"prefix_preposition", "prefix_oath", "preposition"}
_PRONOUN_ROLES = {"object_pronoun", "subject_pronoun", "possessive_pronoun"}
_MA_POS = {"particle", "negative_particle", "relative", "interrogative", "preventive_particle", "subordinating_conjunction"}
_PARTICIPLE_DERIV = {"ism_fail", "ism_mafool", "sifa_mushabbaha", "sighat_mubalaghah", "ism_tafdil"}
_IRAB_CLAIMS = {"irab_role", "case_mood", "governor", "pp_attachment", "particle_function", "suffix_referent"}
_DEFAULT_TRIGGERS = {
    "case_mood": ["case_or_mood"], "irab_role": ["irab"], "governor": ["irab"],
    "pp_attachment": ["jar_majrur_ambiguous"], "particle_function": ["irab"],
    "suffix_referent": ["referent_sensitive_gloss"],
}

# issue class -> (lane, procedure path) — every path verified to exist on disk (routing-existence gate).
ISSUE_ROUTE = {
    "hidden_clitic_or_proclitic": ("sarf", "sarf/procedures/clitic-and-host-morphology.md"),
    "host_only_preposition_hover": ("sarf", "sarf/procedures/clitic-and-host-morphology.md"),
    "ma_function_unresolved_or_wrong": ("nahw", "nahw/procedures/ma-function-decision.md"),
    "phrase_translation_used_as_token_hover": ("curriculum", "curriculum/drills/hover-composition-and-routing.md"),
    "suffix_pronoun_missing": ("sarf", "sarf/procedures/clitic-and-host-morphology.md"),
    "passive_voice_hidden": ("sarf", "sarf/procedures/verb-form.md"),
    "dual_or_plural_suffix_hidden": ("sarf", "sarf/procedures/masdar-participle.md"),
    "derivative_or_participle_prefix_hidden": ("sarf", "sarf/procedures/masdar-participle.md"),
    "weak_irab_reasoning": ("scholar_irab_review", "nahw/procedures/irab-case-mood.md"),
    "graph_edge_missing": ("validator", "qamus/reports/source-address-model.md"),
    "display_local_canonical_crosswalk_missing": ("curriculum", "curriculum/drills/hover-composition-and-routing.md"),
    "source_clean_boundary_violation": ("validator", "provenance/source-boundaries.md"),
}
_PUBLIC_BOUNDARY = {
    "public_gloss_src": "qamus", "public_gloss_kind": "authored",
    "public_gloss_lang": "en", "external_source_names_public": False,
}

# ---------------------------------------------------------------------------
# address resolver (the edge-graph accelerator anchor) — read-only, cached
# ---------------------------------------------------------------------------
_SPINE = None
_ADDRS = None


def _load_graph():
    global _SPINE, _ADDRS
    if _SPINE is None:
        _SPINE = {}
        if os.path.exists(SPINE_PATH):
            with open(SPINE_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    _SPINE[r["ayah"]] = r.get("n_tokens", 0)
    if _ADDRS is None:
        _ADDRS = set()
        if os.path.exists(ADDR_PATH):
            with open(ADDR_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        _ADDRS.add(json.loads(line).get("address"))
                    except ValueError:
                        pass
    return _SPINE, _ADDRS


def resolve_address(address):
    """Return {scope, kind, detail}. scope=out_of_scope when the address is not a source-address graph node."""
    spine, addrs = _load_graph()
    a = (address or "").strip()
    m = re.match(r"^(?:quran:)?(\d{1,3}):(\d{1,3})(?::(\d{1,3}))?$", a) or re.match(r"^wbw:(\d{1,3}):(\d{1,3}):(\d{1,3})$", a)
    if m:
        s, v, w = m.group(1), m.group(2), m.group(3) if m.lastindex >= 3 else None
        ayah = "%s:%s" % (s, v)
        if ayah not in spine:
            return {"scope": "out_of_scope", "kind": "quran_ayah", "detail": "ayah %s not in spine" % ayah}
        if w is not None and int(w) > spine[ayah]:
            return {"scope": "out_of_scope", "kind": "quran_ayah", "detail": "word %s > n_tokens %d" % (w, spine[ayah])}
        return {"scope": "in_scope_source_addressed", "kind": "quran_ayah", "detail": "ayah %s (%d tokens)" % (ayah, spine[ayah])}
    if a.startswith("qamus:"):
        if a in addrs or a.split("#", 1)[0] in addrs:
            return {"scope": "in_scope_source_addressed", "kind": "qamus_entry", "detail": "graph node"}
        return {"scope": "out_of_scope", "kind": "qamus_entry", "detail": "not a graph node"}
    return {"scope": "out_of_scope", "kind": "quran_ayah", "detail": "unrecognized address"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _en(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _words(s):
    return [w for w in re.split(r"[^a-z]+", _en(s)) if len(w) >= 2]


def _surfaced(contribution, hover):
    """True iff any significant english word of `contribution` appears in `hover`."""
    hw = set(_words(hover))
    return any(w in hw for w in _words(contribution))


def _quran(loc):
    return loc if str(loc).startswith(("quran:", "wbw:", "qamus:")) else "quran:%s" % loc


def target_token(tokens_by_loc, target):
    """Resolve a claim target -> (token, matched). SHARED by the checker and the validator so they cannot drift.
    Strips quran:/wbw: prefixes and a trailing :G segment ref. A multi-token unit with no match returns (None, False)
    so an unmatched/unverifiable claim can never be silently certified."""
    key = str(target or "").replace("quran:", "").replace("wbw:", "").split(":G")[0]
    if key in tokens_by_loc:
        return tokens_by_loc[key], True
    if len(tokens_by_loc) == 1:
        return next(iter(tokens_by_loc.values())), True
    return None, False


def _mk_issue(cls, target_loc, claim_id=None, trigger=None, explanation="", gate=None,
              codes=None, expected=None, observed=None):
    lane, proc = ISSUE_ROUTE[cls]
    # canonical GP0 gate per class: a caller-supplied gate wins; boundary leaks never auto-resolve; anchor gaps go
    # to human/source review; everything else is grammar-affecting -> two_vote_required (never auto_safe).
    if cls == "source_clean_boundary_violation":
        g = "never_auto_resolve"
    elif cls in {"graph_edge_missing", "display_local_canonical_crosswalk_missing"}:
        g = "human_source_review_required"
    elif gate:
        g = gate
    else:
        g = "two_vote_required"
    return {
        "issue_id": "fusha.%s" % cls,
        "issue_class": cls,
        "severity": "block" if cls in {"source_clean_boundary_violation", "weak_irab_reasoning"} else "warn",
        "target_address": _quran(target_loc),
        "token_or_card_edge": _quran(target_loc),
        "trigger_address": _quran(trigger) if trigger else None,
        "claim_id": claim_id,
        "codes": codes or [],
        "gate": g,
        "route_to": {"lane": lane, "procedure": proc},
        "explanation": explanation or _default_explanation(cls),
        "expected": _redact(expected),
        "observed": _redact(observed),
        "confidence": "high",
        "evidence_labels": [],
        "public_boundary": dict(_PUBLIC_BOUNDARY),
    }


def _default_explanation(cls):
    return {
        "hidden_clitic_or_proclitic": "The written token carries a prefixed particle (e.g. wāw/fāʾ/bāʾ/the article); its contribution must appear, not be hidden inside the host gloss.",
        "host_only_preposition_hover": "A prefixed preposition (bāʾ/lām/kāf) forms a jar-majrūr; the hover must show the relation, not the host alone.",
        "ma_function_unresolved_or_wrong": "مَا is multi-function (negation, relative, interrogative, preventive); its function in this āyah must be resolved before glossing.",
        "phrase_translation_used_as_token_hover": "This single token does not contribute the whole phrase; the adjacent word's contribution must be recorded separately, not folded into the token hover.",
        "suffix_pronoun_missing": "An attached pronoun is a real grammatical piece of the written token; the hover must surface it or stay pending.",
        "passive_voice_hidden": "The verb is passive (the pattern, not an explicit agent, marks it); the hover must reflect the passive, not read as active.",
        "dual_or_plural_suffix_hidden": "A visible dual/plural ending must be reflected; a singular host gloss hides it.",
        "derivative_or_participle_prefix_hidden": "A derived participle/derivative is not a finite verb; the hover must reflect its nominal shape, not an infinitive verb.",
        "weak_irab_reasoning": "A correct ending without a justified governor (ʿāmil) is unsafe: an iʿrāb-sensitive decision needs the case/mood AND its governor, and a two-vote gate — never auto_safe.",
        "graph_edge_missing": "The target does not resolve to a source-address graph node; it is out of the source-addressed checker's scope.",
        "display_local_canonical_crosswalk_missing": "The display-local position differs from the canonical S:A:W and no crosswalk is recorded, so the token cannot be safely anchored.",
        "source_clean_boundary_violation": "A public-facing field names an internal source or is not {src:qamus,kind:authored,lang:en}; it must be source-clean before anything ships.",
    }.get(cls, "Grammar issue.")


# ---------------------------------------------------------------------------
# detectors (deterministic, source-clean predicates over token + claim + graph)
# ---------------------------------------------------------------------------
def _detect_token_claim(token, claim):
    """All token/claim-level detectors. Returns a list of issues (may be empty)."""
    issues = []
    loc = token.get("loc", "")
    cid = claim.get("claim_id") if claim else None
    hover = claim.get("claimed_value", "") if claim and claim.get("claim_type") == "hover_gloss" else ""
    sarf = token.get("sarf") or {}
    hover_contract = token.get("hover_contract") or {}
    must_surface = hover_contract.get("must_surface") or []
    must_not = hover_contract.get("must_not_surface") or []

    if hover:
        # (A) per-segment contribution omissions -> clitic / preposition / pronoun classes
        for seg in token.get("segments") or []:
            contrib = seg.get("gloss_contribution")
            role = seg.get("role")
            if not contrib or role == "stem":
                continue
            if _surfaced(contrib, hover):
                continue
            if role in _PREP_ROLES:
                issues.append(_mk_issue("host_only_preposition_hover", loc, cid, observed=hover, expected=contrib))
            elif role in _PRONOUN_ROLES:
                issues.append(_mk_issue("suffix_pronoun_missing", loc, cid, observed=hover, expected=contrib))
            elif role in _CLITIC_ROLES:
                issues.append(_mk_issue("hidden_clitic_or_proclitic", loc, cid, observed=hover, expected=contrib))
        # (B) passive hidden — fire only when the hover reads ACTIVE (subject + non-aux verb); a bare past-participle
        # gloss ("slain", "taken", "created") is a valid passive rendering and must NOT false-positive.
        if sarf.get("voice") == "passive" and ACTIVE_RE.search(_en(hover)):
            issues.append(_mk_issue("passive_voice_hidden", loc, cid, observed=hover, expected="passive reading"))
        # (C) dual/plural suffix hidden — drive from the authored must_surface (catches irregular plurals: men,
        # women, children), scoped to the NUMBER aspect (omissions covered by a function segment are not this class).
        if sarf.get("noun_number") in {"dual", "plural"} or sarf.get("number") in {"dual", "plural"}:
            _seg_contribs = [s.get("gloss_contribution") for s in token.get("segments") or []
                             if s.get("role") != "stem" and s.get("gloss_contribution")]
            omitted_number = [m for m in must_surface
                              if not _surfaced(m, hover) and not any(_surfaced(m, sc) for sc in _seg_contribs)]
            if omitted_number:
                issues.append(_mk_issue("dual_or_plural_suffix_hidden", loc, cid, observed=hover, expected=", ".join(omitted_number)))
        # (D) derivative/participle prefix hidden
        if sarf.get("derivative_type") in _PARTICIPLE_DERIV and re.search(r"\bto\s+\w+", _en(hover)):
            issues.append(_mk_issue("derivative_or_participle_prefix_hidden", loc, cid, observed=hover))
        # (E) mā function unresolved — match مَا as a STANDALONE token/segment (not the substring ما, which appears
        # inside كَلِمَات 'words' etc.), gated by a particle-ish POS.
        nahw_fn = (token.get("nahw") or {}).get("function")
        _ma_seg = any(N.bare(s.get("surface", "")) == "ما" for s in token.get("segments") or [])
        is_ma = (N.bare(token.get("surface", "")) == "ما" or _ma_seg) and (token.get("pos") in _MA_POS or _ma_seg)
        if is_ma and (not nahw_fn or nahw_fn in {"unresolved", "none"}):
            issues.append(_mk_issue("ma_function_unresolved_or_wrong", loc, cid, observed=hover))
        # (F) phrase-level translation used as token hover
        if not claim.get("token_contribution"):
            for item in must_not:
                if _surfaced(item, hover):
                    issues.append(_mk_issue("phrase_translation_used_as_token_hover", loc, cid, observed=hover, expected="token contribution only"))
                    break
        # (G) source-clean boundary on the claim hover
        if LEAK_RE.search(hover):
            issues.append(_mk_issue("source_clean_boundary_violation", loc, cid, observed="<redacted leak in claimed hover>"))

    # (H) iʿrāb reasoning / governor-justification gate
    if claim and claim.get("claim_type") in _IRAB_CLAIMS:
        triggers = claim.get("grammar_triggers") or _DEFAULT_TRIGGERS.get(claim["claim_type"], ["irab"])
        req = required_gate(triggers)
        claimed = GATE_ALIAS.get(claim.get("claimed_gate"), "auto_safe")
        if _GATE_RANK[claimed] < _GATE_RANK[req]:
            issues.append(_mk_issue("weak_irab_reasoning", claim.get("target", loc), cid,
                                    trigger=(claim.get("governor") or None), gate=req,
                                    codes=["two_vote_marked_auto_safe"],
                                    observed="gate=%s" % claimed, expected="gate>=%s" % req))
        elif not claim.get("claimed_reasoning"):
            issues.append(_mk_issue("weak_irab_reasoning", claim.get("target", loc), cid, gate=req,
                                    codes=["right_label_no_governor"],
                                    observed="no reasoning", expected="case/mood + justifying governor"))

    # (I) public-clean boundary on the token's public fields
    pb = token.get("public_boundary") or {}
    if (token.get("src"), token.get("kind"), token.get("lang")) != ("qamus", "authored", "en") or pb.get("external_source_names_public") is True:
        issues.append(_mk_issue("source_clean_boundary_violation", loc, cid, observed="token public boundary not src=qamus/kind=authored/lang=en"))
    for field in ("gloss", "learner_explanation"):
        if LEAK_RE.search(token.get(field, "") or ""):
            issues.append(_mk_issue("source_clean_boundary_violation", loc, cid, observed="leak in token.%s" % field))
    return issues


def _detect_segment_crosswalk(unit):
    issues = []
    fallback = (unit.get("tokens") or [{}])[0].get("loc")
    for seg in unit.get("segments") or []:
        dl = seg.get("display_local_loc")
        canon = seg.get("canonical_loc")
        if dl and canon and dl != canon and not seg.get("display_local_crosswalk"):
            tl = (seg.get("token_locs") or [None])[0] or fallback
            # a token-edge issue needs a token-level S:A:W; never emit an ayah-only address (schema-invalid).
            if not tl or not re.match(r"^(?:quran:)?\d{1,3}:\d{1,3}:\d{1,3}$", str(tl)):
                continue
            issues.append(_mk_issue("display_local_canonical_crosswalk_missing", tl))
    return issues


def _dedup(issues):
    seen, out = set(), []
    for i in issues:
        # include `expected` so two DISTINCT omitted pieces of the same class on one token (e.g. wāw + fāʾ both
        # dropped) are each reported instead of collapsing to one.
        k = (i["issue_class"], i["target_address"], i.get("claim_id"), i.get("expected"))
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


# ---------------------------------------------------------------------------
# verdict + the checker pipeline
# ---------------------------------------------------------------------------
def _verdict(scope, claim, claim_issues):
    classes = {i["issue_class"] for i in claim_issues}
    route = sorted({"%s:%s" % (i["route_to"]["lane"], i["route_to"]["procedure"]) for i in claim_issues})
    gate = "auto_safe"
    for i in claim_issues:
        if _GATE_RANK[i["gate"]] > _GATE_RANK[gate]:
            gate = i["gate"]
    # a boundary leak is never_auto_resolve regardless of scope (checked BEFORE the out_of_scope early-return).
    if "source_clean_boundary_violation" in classes:
        return {"status": "contradicted", "gate": "never_auto_resolve"}, route, True
    if scope == "out_of_scope":
        return {"status": "out_of_scope", "gate": "human_source_review_required"}, route, False
    if "weak_irab_reasoning" in classes:
        return {"status": "unsafe_reasoning", "gate": gate}, route, True
    if claim_issues:
        return {"status": "contradicted", "gate": gate}, route, bool(claim and claim.get("claimed_reasoning"))
    if claim and claim.get("claim_type") in _IRAB_CLAIMS:
        req = required_gate(claim.get("grammar_triggers") or _DEFAULT_TRIGGERS.get(claim["claim_type"], ["irab"]))
        if _GATE_RANK[req] >= _GATE_RANK["two_vote_required"]:
            return {"status": "needs_two_vote", "gate": req}, route, True
    return {"status": "grounded", "gate": "auto_safe"}, route, True


def check_unit(unit):
    """Adjudicate one CheckUnit; return it populated with issues[], verdicts[], summary."""
    su = unit.get("source_unit") or {}
    res = resolve_address(su.get("address", ""))
    scope = res["scope"]
    su["scope"] = scope
    tokens_by_loc = {t.get("loc"): t for t in unit.get("tokens") or []}
    issues, verdicts = [], []

    if scope == "out_of_scope":
        # anchor the issue at the token/claim that failed to resolve (a token-level S:A:W edge), not the ayah.
        toks = unit.get("tokens") or []
        claims0 = unit.get("claims") or []
        edge_loc = (toks[0].get("loc") if toks else None) or (str(claims0[0].get("target")).replace("quran:", "").replace("wbw:", "") if claims0 else None) or su.get("address", "")
        ge = _mk_issue("graph_edge_missing", edge_loc)
        issues.append(ge)

    issues.extend(_detect_segment_crosswalk(unit))

    for claim in unit.get("claims") or []:
        tok, matched = target_token(tokens_by_loc, claim.get("target", ""))
        if not matched:
            # an unmatched target is unverifiable — never certify it grounded.
            key = str(claim.get("target", "")).replace("quran:", "").replace("wbw:", "").split(":G")[0]
            unmatched = []
            if re.match(r"^\d{1,3}:\d{1,3}:\d{1,3}$", key):
                unmatched = [_mk_issue("graph_edge_missing", key, claim.get("claim_id"),
                                       observed="claim target %s resolves to no token in this unit" % key)]
            issues.extend(unmatched)
            verdicts.append({
                "claim_id": claim.get("claim_id"), "status": "needs_human_review",
                "gate": "human_source_review_required", "issue_ids": [i["issue_id"] for i in unmatched],
                "route_to": sorted({"%s:%s" % (i["route_to"]["lane"], i["route_to"]["procedure"]) for i in unmatched}),
                "reasoning_checked": False,
            })
            continue
        claim_issues = _dedup(_detect_token_claim(tok, claim))
        v, route, reasoning_checked = _verdict(scope, claim, claim_issues)
        if scope == "out_of_scope":
            route = sorted(set(route) | {"%s:%s" % (issues[0]["route_to"]["lane"], issues[0]["route_to"]["procedure"])}) if issues else route
        issues.extend(claim_issues)
        verdicts.append({
            "claim_id": claim.get("claim_id"),
            "status": v["status"],
            "gate": v["gate"],
            "issue_ids": [i["issue_id"] for i in claim_issues] + ([issues[0]["issue_id"]] if scope == "out_of_scope" else []),
            "route_to": route,
            "reasoning_checked": reasoning_checked,
        })

    issues = _dedup(issues)
    unit["issues"] = issues
    unit["verdicts"] = verdicts
    by_verdict, by_class = {}, {}
    for vd in verdicts:
        by_verdict[vd["status"]] = by_verdict.get(vd["status"], 0) + 1
    for i in issues:
        by_class[i["issue_class"]] = by_class.get(i["issue_class"], 0) + 1
    unit["summary"] = {"live_writes": 0, "by_verdict": by_verdict, "by_issue_class": by_class}
    unit.setdefault("public_boundary", dict(_PUBLIC_BOUNDARY))
    unit.setdefault("evidence", {"labels": [], "gate": None})
    # routing gate: every issue MUST route (else the checker is broken — fail loudly).
    for i in issues:
        rt = i.get("route_to") or {}
        if rt.get("lane") not in {"sarf", "nahw", "curriculum", "validator", "owner_review", "scholar_irab_review"} or not rt.get("procedure"):
            raise AssertionError("UNROUTABLE issue %s at %s — checker bug" % (i.get("issue_class"), i.get("target_address")))
    assert unit["summary"]["live_writes"] == 0, "ABORT: checker is dry-run; live_writes must be 0"
    return unit


# ---------------------------------------------------------------------------
# regression fixture (the 7 required examples + full 12-class coverage)
# ---------------------------------------------------------------------------
def _tok(loc, surface, pos, segments, sarf=None, must_surface=None, must_not=None, nahw=None, gloss="(authored)"):
    sn, sv, sw = loc.split(":")
    return {
        "loc": loc, "wbw_loc": "wbw:%s" % loc, "surface": surface, "key": surface, "gloss": gloss,
        "src": "qamus", "kind": "authored", "lang": "en", "decision_state": "rich_candidate", "pos": pos,
        "sarf": sarf or {}, "nahw": nahw or {"function": None}, "segments": segments,
        "hover_contract": {"must_surface": must_surface or [], "must_not_surface": must_not or [], "reason": None},
        "learner_explanation": "Token-level grammar contribution.",
        "public_boundary": dict(_PUBLIC_BOUNDARY),
    }


def _unit(uid, address, kind, surface, token, claims, segments=None):
    return {
        "schema": "fusha/parser-check-ir@1", "unit_id": uid,
        "source_unit": {"address": address, "kind": kind, "scope": "in_scope_source_addressed", "display_surface": surface},
        "segments": segments or [{"canonical_loc": "quran:%s" % ":".join(token["loc"].split(":")[:2]),
                                  "display_surface": surface, "display_local_loc": None,
                                  "display_local_crosswalk": None, "token_locs": ["quran:%s" % token["loc"]]}],
        "tokens": [token], "claims": claims, "issues": [], "verdicts": [],
        "public_boundary": dict(_PUBLIC_BOUNDARY), "evidence": {"labels": [], "gate": None},
        "summary": {"live_writes": 0, "by_verdict": {}, "by_issue_class": {}},
    }


def regression_units():
    """The committed regression set. Each entry: (input_unit, {verdict, must_have_classes})."""
    out = []

    # 1. وَمَا @ 3:7:27 — waw + function-specific مَا (one written token, not one opaque word).
    t = _tok("3:7:27", "وَمَا", "particle",
             [{"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
              {"role": "particle", "surface": "مَا", "gloss_contribution": None}],
             nahw={"function": None})
    c = {"claim_id": "c1", "target": "3:7:27", "claim_type": "hover_gloss", "claimed_value": "what",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-wama", "quran:3:7", "quran_ayah", "وَمَا", t, [c]),
                {"verdict": "contradicted", "classes": {"hidden_clitic_or_proclitic", "ma_function_unresolved_or_wrong"}}))

    # 2. بِبَدْرٍ @ 3:123:4 — bāʾ + host, not host-only ("Badr" alone is invalid).
    t = _tok("3:123:4", "بِبَدْرٍ", "noun",
             [{"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "at/by"},
              {"role": "stem", "surface": "بَدْرٍ", "gloss_contribution": "Badr"}],
             sarf={"case": "genitive"}, must_surface=["at", "Badr"], must_not=["Badr only"])
    c = {"claim_id": "c1", "target": "3:123:4", "claim_type": "hover_gloss", "claimed_value": "Badr",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-bibadr", "quran:3:123", "quran_ayah", "بِبَدْرٍ", t, [c]),
                {"verdict": "contradicted", "classes": {"host_only_preposition_hover"}}))

    # 3. جَادَلُوكَ @ 22:68:2 — verb + attached object pronoun (must surface "you").
    t = _tok("22:68:2", "جَادَلُوكَ", "verb",
             [{"role": "stem", "surface": "جَادَلُوا", "gloss_contribution": "they argued"},
              {"role": "object_pronoun", "surface": "كَ", "gloss_contribution": "with you"}],
             sarf={"voice": "active", "verb_form": "III"}, must_surface=["they", "you"], must_not=["to argue"])
    c = {"claim_id": "c1", "target": "22:68:2", "claim_type": "hover_gloss", "claimed_value": "to argue",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-jadaluka", "quran:22:68", "quran_ayah", "جَادَلُوكَ", t, [c]),
                {"verdict": "contradicted", "classes": {"suffix_pronoun_missing"}}))

    # 4. قِيلَ @ 11:48:1 — passive verb (must not read as active).
    t = _tok("11:48:1", "قِيلَ", "verb",
             [{"role": "stem", "surface": "قِيلَ", "gloss_contribution": "it was said"}],
             sarf={"voice": "passive", "tense_aspect": "perfect"}, must_surface=["was said"])
    c = {"claim_id": "c1", "target": "11:48:1", "claim_type": "hover_gloss", "claimed_value": "he said",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-qila", "quran:11:48", "quran_ayah", "قِيلَ", t, [c]),
                {"verdict": "contradicted", "classes": {"passive_voice_hidden"}}))

    # 5. ٱلْعَٰلَمِينَ @ 1:2:4 — visible plural suffix (must reflect plural).
    t = _tok("1:2:4", "ٱلْعَٰلَمِينَ", "noun",
             [{"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
              {"role": "stem", "surface": "عَٰلَمِينَ", "gloss_contribution": "worlds"}],
             sarf={"noun_number": "plural", "case": "genitive", "definiteness": "definite"},
             must_surface=["the", "worlds"], must_not=["world only"])
    c = {"claim_id": "c1", "target": "1:2:4", "claim_type": "hover_gloss", "claimed_value": "the world",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-alamin", "quran:1:2", "quran_ayah", "ٱلْعَٰلَمِينَ", t, [c]),
                {"verdict": "contradicted", "classes": {"dual_or_plural_suffix_hidden"}}))

    # 6. يَسْأَلُكَ @ 33:63:1 — phrase-vs-token (subject النَّاسُ is the NEXT word, not inside the token).
    t = _tok("33:63:1", "يَسْأَلُكَ", "verb",
             [{"role": "stem", "surface": "يَسْأَلُ", "gloss_contribution": "asks"},
              {"role": "object_pronoun", "surface": "كَ", "gloss_contribution": "you"}],
             sarf={"voice": "active"}, must_surface=["ask", "you"], must_not=["the people"])
    c = {"claim_id": "c1", "target": "33:63:1", "claim_type": "hover_gloss", "claimed_value": "the people ask you",
         "claimed_reasoning": None, "token_contribution": None, "proposer": "model"}
    seg = [{"canonical_loc": "quran:33:63", "display_surface": "يَسْأَلُكَ", "display_local_loc": None,
            "display_local_crosswalk": None, "token_locs": ["quran:33:63:1", "quran:33:63:2"]}]
    out.append((_unit("reg-yasaluka", "quran:33:63", "quran_ayah", "يَسْأَلُكَ", t, [c], segments=seg),
                {"verdict": "contradicted", "classes": {"phrase_translation_used_as_token_hover"}}))

    # 7. weak iʿrāb — right case, no governor justification, marked auto_safe (نَّجْمِ host of 16:16:2).
    t = _tok("16:16:2", "وَبِٱلنَّجْمِ", "noun",
             [{"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
              {"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "by"},
              {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
              {"role": "stem", "surface": "نَّجْمِ", "gloss_contribution": "star"}],
             sarf={"case": "genitive", "definiteness": "definite"})
    c = {"claim_id": "c1", "target": "16:16:2", "claim_type": "case_mood", "claimed_value": "genitive",
         "claimed_reasoning": None, "claimed_gate": "auto_safe", "proposer": "model"}
    out.append((_unit("reg-weak-irab", "quran:16:16", "quran_ayah", "وَبِٱلنَّجْمِ", t, [c]),
                {"verdict": "unsafe_reasoning", "classes": {"weak_irab_reasoning"}}))

    # 8. derivative/participle prefix hidden (مُعَلَّم participle treated as verb "to teach").
    t = _tok("44:14:3", "مُعَلَّمٌ", "participle",
             [{"role": "derivative_prefix", "surface": "مُ", "gloss_contribution": "one who is"},
              {"role": "stem", "surface": "عَلَّم", "gloss_contribution": "taught"}],
             sarf={"derivative_type": "ism_mafool"}, must_surface=["taught one", "instructed"])
    c = {"claim_id": "c1", "target": "44:14:3", "claim_type": "hover_gloss", "claimed_value": "to teach",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-participle", "quran:44:14", "quran_ayah", "مُعَلَّمٌ", t, [c]),
                {"verdict": "contradicted", "classes": {"derivative_or_participle_prefix_hidden"}}))

    # 9. out_of_scope / graph_edge_missing — surah 200 does not exist.
    t = _tok("200:1:1", "كلمة", "noun", [{"role": "stem", "surface": "كلمة", "gloss_contribution": "word"}])
    c = {"claim_id": "c1", "target": "200:1:1", "claim_type": "hover_gloss", "claimed_value": "word",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-oos", "quran:200:1", "quran_ayah", "كلمة", t, [c]),
                {"verdict": "out_of_scope", "classes": {"graph_edge_missing"}}))

    # 10. display_local_canonical_crosswalk_missing.
    t = _tok("2:255:1", "ٱللَّهُ", "proper_noun", [{"role": "stem", "surface": "ٱللَّهُ", "gloss_contribution": "Allah"}],
             must_surface=["Allah"])
    seg = [{"canonical_loc": "quran:2:255", "display_surface": "ٱللَّهُ", "display_local_loc": "wbw:2:255:99",
            "display_local_crosswalk": None, "token_locs": ["2:255:1"]}]
    c = {"claim_id": "c1", "target": "2:255:1", "claim_type": "hover_gloss", "claimed_value": "Allah",
         "claimed_reasoning": None, "proposer": "model"}
    out.append((_unit("reg-crosswalk", "quran:2:255", "quran_ayah", "ٱللَّهُ", t, [c], segments=seg),
                {"verdict": "grounded", "classes": {"display_local_canonical_crosswalk_missing"}}))

    # 11. source_clean_boundary_violation — a claim hover that names an internal source.
    t = _tok("1:1:1", "بِسْمِ", "noun",
             [{"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "in"},
              {"role": "stem", "surface": "سْمِ", "gloss_contribution": "the name of"}],
             must_surface=["in", "name"])
    c = {"claim_id": "c1", "target": "1:1:1", "claim_type": "hover_gloss",
         "claimed_value": "in the name of (per qac)", "claimed_reasoning": None, "proposer": "import"}
    out.append((_unit("reg-leak", "quran:1:1", "quran_ayah", "بِسْمِ", t, [c]),
                {"verdict": "contradicted", "classes": {"source_clean_boundary_violation"}}))

    # 12. GROUNDED — a correct hover that surfaces every piece (no issue).
    t = _tok("16:16:2", "وَبِٱلنَّجْمِ", "noun",
             [{"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
              {"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "by"},
              {"role": "definite_article", "surface": "ٱل", "gloss_contribution": "the"},
              {"role": "stem", "surface": "نَّجْمِ", "gloss_contribution": "star"}],
             sarf={"case": "genitive", "definiteness": "definite"},
             must_surface=["and", "by", "the", "star"])
    c = {"claim_id": "c1", "target": "16:16:2", "claim_type": "hover_gloss", "claimed_value": "and by the star",
         "claimed_reasoning": None, "proposer": "tutor"}
    out.append((_unit("reg-grounded", "quran:16:16", "quran_ayah", "وَبِٱلنَّجْمِ", t, [c]),
                {"verdict": "grounded", "classes": set()}))

    return out


# ---------------------------------------------------------------------------
# self-test + CLI
# ---------------------------------------------------------------------------
def _self_test():
    failures = []
    for unit_in, exp in regression_units():
        uid = unit_in["unit_id"]
        out = check_unit(json.loads(json.dumps(unit_in)))
        got_classes = {i["issue_class"] for i in out["issues"]}
        got_verdict = out["verdicts"][0]["status"] if out["verdicts"] else "(none)"
        if not exp["classes"].issubset(got_classes):
            failures.append("%s: missing issue classes %s (got %s)" % (uid, exp["classes"] - got_classes, got_classes))
        if got_verdict != exp["verdict"]:
            failures.append("%s: verdict %s != expected %s" % (uid, got_verdict, exp["verdict"]))
    # every one of the 12 classes must be exercised by the fixture
    all_seen = set()
    for unit_in, _ in regression_units():
        all_seen |= {i["issue_class"] for i in check_unit(json.loads(json.dumps(unit_in)))["issues"]}
    required12 = set(ISSUE_ROUTE)
    if all_seen != required12:
        failures.append("fixture does not exercise all 12 classes: missing %s" % (required12 - all_seen))
    # the milestone boundary: an unaddressed token is out_of_scope
    if resolve_address("quran:200:1:1")["scope"] != "out_of_scope":
        failures.append("resolver: surah 200 should be out_of_scope")
    if resolve_address("quran:1:1:1")["scope"] != "in_scope_source_addressed":
        failures.append("resolver: 1:1:1 should be in_scope")

    # --- review-hardening regressions (real-input cases the curated fixture would not exercise) ---
    # (a) a multi-token unit whose claim target matches no token must NOT be certified grounded.
    mt = _unit("rh-multitoken", "quran:1:1", "quran_ayah", "بِسْمِ",
               _tok("1:1:1", "بِسْمِ", "noun", [{"role": "stem", "surface": "بِسْمِ", "gloss_contribution": "in the name of"}]),
               [{"claim_id": "c1", "target": "1:1:99", "claim_type": "hover_gloss", "claimed_value": "x", "claimed_reasoning": None, "proposer": "model"}])
    mt["tokens"].append(_tok("1:1:2", "ٱللَّهِ", "proper_noun", [{"role": "stem", "surface": "ٱللَّهِ", "gloss_contribution": "Allah"}]))
    if check_unit(json.loads(json.dumps(mt)))["verdicts"][0]["status"] == "grounded":
        failures.append("multi-token unit with an unmatched claim target must not be grounded")
    # (b) a bare past-participle gloss on a passive verb must NOT false-positive passive_voice_hidden;
    #     an active reading ("he killed") MUST fire.
    _pt = _tok("11:48:1", "قُتِلَ", "verb", [{"role": "stem", "surface": "قُتِلَ", "gloss_contribution": "slain"}], sarf={"voice": "passive"})
    if any(i["issue_class"] == "passive_voice_hidden" for i in _detect_token_claim(_pt, {"claim_id": "c", "target": "11:48:1", "claim_type": "hover_gloss", "claimed_value": "slain"})):
        failures.append("passive participle gloss 'slain' must not false-positive passive_voice_hidden")
    if not any(i["issue_class"] == "passive_voice_hidden" for i in _detect_token_claim(_pt, {"claim_id": "c", "target": "11:48:1", "claim_type": "hover_gloss", "claimed_value": "he killed"})):
        failures.append("active gloss 'he killed' on a passive verb must fire passive_voice_hidden")
    # (c) two distinct omitted clitics of the same class on one token must yield two issues (not collapse).
    _dc = _tok("3:7:27", "وَفَكَلِمَة", "noun",
               [{"role": "prefix_conjunction", "surface": "وَ", "gloss_contribution": "and"},
                {"role": "prefix_resumption_fa", "surface": "فَ", "gloss_contribution": "so"},
                {"role": "stem", "surface": "كَلِمَة", "gloss_contribution": "word"}])
    _hc = [i for i in _dedup(_detect_token_claim(_dc, {"claim_id": "c", "target": "3:7:27", "claim_type": "hover_gloss", "claimed_value": "word"})) if i["issue_class"] == "hidden_clitic_or_proclitic"]
    if len(_hc) < 2:
        failures.append("two distinct omitted clitics (wāw + fāʾ) must yield two hidden_clitic issues, got %d" % len(_hc))
    # (d) a particle whose bare letters merely CONTAIN ما (e.g. كَلِمَات) must NOT fire ma_function.
    _km = _tok("2:30:5", "كَلِمَات", "noun", [{"role": "stem", "surface": "كَلِمَات", "gloss_contribution": "words"}], sarf={"noun_number": "plural"})
    if any(i["issue_class"] == "ma_function_unresolved_or_wrong" for i in _detect_token_claim(_km, {"claim_id": "c", "target": "2:30:5", "claim_type": "hover_gloss", "claimed_value": "words"})):
        failures.append("كَلِمَات must not false-positive ma_function (substring ما)")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_check self-test: 12 regression units, all 12 issue classes, out_of_scope boundary, dry-run")
    return 0 if not failures else 1


def emit_fixture(path):
    rows = [check_unit(json.loads(json.dumps(u))) for u, _ in regression_units()]
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {
        "schema": "fusha/parser-check-ir@1",
        "generator": "tools/fusha_check.py --emit-fixture",
        "row_schema": ["schema", "unit_id", "source_unit", "segments", "tokens", "claims", "issues", "verdicts",
                       "public_boundary", "evidence", "summary"],
        "count": len(rows),
        "covers_issue_classes": sorted(ISSUE_ROUTE),
        "note": "Regression fixture for the Fusha parser/checker. Qurʾānic surfaces verbatim; public output is "
                "{src:qamus,kind:authored,lang:en}; no external gloss text. See parserplans/009 + 015.",
    }
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d units -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Fusha source-addressed parser/checker (dry-run).")
    ap.add_argument("--in", dest="infile", help="CheckUnit JSONL to check")
    ap.add_argument("--out", dest="outfile", default="-", help="output JSONL ('-' = stdout)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    if not a.infile:
        ap.error("need --in, --self-test, or --emit-fixture")
    rows = []
    with open(a.infile, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(check_unit(json.loads(line)))
    sink = sys.stdout if a.outfile == "-" else open(a.outfile, "w", encoding="utf-8")
    for r in rows:
        sink.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
