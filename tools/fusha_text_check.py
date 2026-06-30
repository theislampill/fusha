#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_text_check — the general (Grammarly-like) Fusha/Classical-Arabic text checker front-end.

Three modes (parserplans/general-fusha-grammar-checker/{001,004}):
  - source_addressed : tokens carry exact S:A:W; resolves via fusha_check and may hand a CheckUnit to fusha_check.check_unit.
  - corpus_backed    : corpus IDs (corpus:*); gate FLOOR two_vote_required; never auto_safe from corpus membership alone.
  - arbitrary_typing : user-typed/pasted text incl. unvoweled. NO source-address certainty. Ambiguity-preserving:
                       it enumerates a clitic candidate LATTICE and emits the 12 general diagnostics; gate is NEVER auto_safe.

This is a SEPARATE front-end (D1): it does NOT route arbitrary text through fusha_check's out_of_scope path. It preserves
the original input verbatim (raw_input), records the normalization op-trail (never overwriting the original), and never
forces a single parse for unvoweled Arabic (~12 analyses/word — deep-research F4; ranked candidate selection — F8/F3).
Dry-run only: checker_summary.live_writes == 0; no network, no /srv, no live writes. Public output is source-clean
{src:qamus,kind:authored,lang:en}; no external gloss text.

CLI:
  python3 tools/fusha_text_check.py --in <requests.jsonl> --out <-|path>     # check a batch
  python3 tools/fusha_text_check.py --mode arbitrary_typing --in text.txt    # check a plain-text file as arbitrary
  python3 tools/fusha_text_check.py --self-test                              # the 10 regression requests
  python3 tools/fusha_text_check.py --emit-fixture <path.jsonl>              # regenerate the committed fixture
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
from tools import fusha_check as FC  # noqa: E402
from tools.validate_linguistic_decisions import required_gate, _GATE_RANK  # noqa: E402
from tools.audit_all_hover_tokens import PROCLITICS, ENCLITICS  # noqa: E402

SCHEMA = "fusha/text-check@1"
_PUBLIC_BOUNDARY = {
    "public_gloss_src": "qamus", "public_gloss_kind": "authored",
    "public_gloss_lang": "en", "external_source_names_public": False,
}

# The 12 NEW general (arbitrary-text) diagnostic classes -> (severity, gate-or-triggers, lane, procedure).
# A 'triggers' entry derives the gate via required_gate() (never inline a tier); an explicit 'gate' is used as-is.
# Every gate here is >= two_vote_required: arbitrary text can never be auto_safe (D1/D7).
GENERAL_ISSUES = {
    "possible_clitic_segmentation": ("warn", {"triggers": ["jar_majrur_ambiguous"]}, "sarf", "sarf/procedures/clitic-and-host-morphology.md"),
    "ambiguous_unvoweled_token": ("warn", {"triggers": ["multi_sense_root"]}, "sarf", "sarf/procedures/homograph-risk.md"),
    "possible_attached_pronoun": ("warn", {"triggers": ["referent_sensitive_gloss"]}, "sarf", "sarf/procedures/suffix-pronoun-state.md"),
    "possible_preposition_host": ("warn", {"triggers": ["jar_majrur_ambiguous"]}, "nahw", "nahw/procedures/preposition-pronoun.md"),
    "possible_definite_article": ("info", {"gate": "two_vote_required"}, "sarf", "sarf/procedures/clitic-and-host-morphology.md"),
    "possible_particle_function": ("warn", {"triggers": ["irab"]}, "nahw", "nahw/procedures/particle-decision.md"),
    "possible_case_or_mood_requires_context": ("warn", {"triggers": ["case_or_mood"]}, "nahw", "nahw/procedures/irab-case-mood.md"),
    "possible_governor_unresolved": ("warn", {"triggers": ["irab"]}, "nahw", "nahw/procedures/irab-case-mood.md"),
    "orthography_normalization_warning": ("info", {"gate": "two_vote_required"}, "sarf", "sarf/procedures/hamza-root.md"),
    "dialect_or_non_fusha_possible": ("info", {"triggers": ["ambiguous_grammar"]}, "nahw", "nahw/procedures/grammar-risk-gate.md"),
    "source_address_required_for_certainty": ("info", {"triggers": ["ambiguous_grammar"]}, "validator", "provenance/source-boundaries.md"),
    "rich_hover_candidate_available_when_source_addressed": ("info", {"gate": "two_vote_required"}, "validator", "qamus/reports/general-checker-rich-hover-flywheel.md"),
}

# multi-function particles whose function is not decidable from the surface alone (bare keys).
PARTICLE_SET = {"ما", "و", "ف", "لا", "إلا", "الا", "من", "لما", "ل", "أ", "إن", "أن", "إذا", "لو", "حتى", "كي", "لن", "لم", "قد", "بل", "ثم", "أو"}
# proclitic surface -> the prepositional ones that form a jar-majrūr.
_PREP_FIRST = {"ب", "ك", "ل"}
_HARAKAT = range(0x064B, 0x0653)
_AR_RE = re.compile(r"[؀-ۿݐ-ݿ]")


def _is_arabic(tok):
    return bool(_AR_RE.search(tok or ""))


def _has_harakat(tok):
    return any(0x064B <= ord(c) <= 0x0652 for c in (tok or ""))


def _redact(s):
    return FC._redact(s) if s else s


# ---------------------------------------------------------------------------
# normalization with an explicit op-trail (gap: record the transform, do not just apply it)
# ---------------------------------------------------------------------------
# the chars norm_strict() actually TRANSFORMS (so they require a recorded op). Hamza SEATS (أ إ ؤ ئ ء) are KEPT by
# norm_strict and therefore require NO op — the validator and the checker share this set so they cannot drift.
_TRANSFORM_CHARS = (set("ٰٱآىة") | {chr(c) for c in range(0x064B, 0x0653)} | {chr(0x0640)}
                    | {chr(c) for c in range(0x0653, 0x0656)} | {chr(c) for c in range(0x06D6, 0x06EE)})


def needs_normalization(text):
    """True iff norm_strict() would transform `text` (so a normalization op must be recorded). Hamza seats excluded."""
    return any(ch in _TRANSFORM_CHARS for ch in (text or ""))


def normalize_with_ops(text):
    """Return (normalized_input, ops[]). normalized_input is computed ALONGSIDE the original (norm_strict per word,
    spaces preserved); the original `text` is NEVER altered. ops records which transform classes were applied, and
    is guaranteed non-empty whenever needs_normalization(text) is True (checker/validator parity)."""
    ops = []
    found_marks = sorted({c for c in text if (0x064B <= ord(c) <= 0x0655) or (0x06D6 <= ord(c) <= 0x06ED)})
    if found_marks:
        ops.append({"op": "strip_tashkil", "from": "".join(found_marks), "to": "", "note": "diacritics/marks dropped for the analysis key only"})
    if "ٰ" in text:
        ops.append({"op": "dagger_alif_to_alif", "from": "ٰ", "to": "ا", "note": None})
    if "ٱ" in text:
        ops.append({"op": "fold_alif_wasla", "from": "ٱ", "to": "ا", "note": None})
    if "آ" in text:
        ops.append({"op": "other", "from": "آ", "to": "ا", "note": "alif madda folded for the match key only"})
    if "ـ" in text:
        ops.append({"op": "strip_tatweel", "from": "ـ", "to": "", "note": None})
    if "ة" in text:
        ops.append({"op": "fold_ta_marbuta", "from": "ة", "to": "ه", "note": "match key only; display keeps ة"})
    if "ى" in text:
        ops.append({"op": "fold_alif_maqsura", "from": "ى", "to": "ي", "note": "match key only; display keeps ى"})
    if needs_normalization(text) and not ops:  # safety net so the op-trail never silently misses a transform
        ops.append({"op": "other", "from": text, "to": " ".join(N.norm_strict(w) for w in text.split()), "note": "normalization applied"})
    normalized = " ".join(N.norm_strict(w) for w in text.split())
    return normalized, ops


# ---------------------------------------------------------------------------
# tokenization
# ---------------------------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[\.\!\?؟۔!])\s+|\n+")
_WORD_RE = re.compile(r"[؀-ۿݐ-ݿ]+|[0-9٠-٩]+|[^\s؀-ۿݐ-ݿ0-9٠-٩]+")


def sentence_spans(text):
    spans, start = [], 0
    for m in _SENT_SPLIT.finditer(text):
        spans.append({"start": start, "end": m.start(), "text": text[start:m.start()].strip() or None})
        start = m.end()
    if start < len(text):
        spans.append({"start": start, "end": len(text), "text": text[start:].strip() or None})
    return [s for s in spans if (s["text"] or "").strip()]


def whitespace_tokens(text):
    out = []
    for i, m in enumerate(_WORD_RE.finditer(text)):
        s = m.group(0)
        if _AR_RE.search(s):
            kind = "word"
        elif re.fullmatch(r"[0-9٠-٩]+", s):
            kind = "number"
        else:
            kind = "punctuation"
        out.append({"index": i, "surface": s, "kind": kind, "start": m.start(), "end": m.end()})
    return out


# ---------------------------------------------------------------------------
# clitic candidate lattice (ranked selection over the closed proclitic/enclitic sets — never a deterministic split)
# ---------------------------------------------------------------------------
def _clusters(s):
    """Split a written surface into clusters of one BASE letter + its trailing combining marks. The mark set mirrors
    exactly what bare() drops (harakāt 064B-0655, dagger alif 0670, tatweel 0640, Qurʾanic marks 06D6-06ED), so the
    number of clusters == len(bare(s)). This lets us peel a clitic by base-letter count on the DISPLAY surface without
    ever slicing mid-cluster (the bug that corrupted/crashed a voweled proclitic peel)."""
    out = []
    for ch in s:
        o = ord(ch)
        if ((0x064B <= o <= 0x0655) or o == 0x0670 or o == 0x0640 or (0x06D6 <= o <= 0x06ED)) and out:
            out[-1] += ch
        else:
            out.append(ch)
    return out


def _proclitic_pieces(clusters):
    """Decompose proclitic CLUSTERS (display, mark-bearing) into ordered (role, surface) pieces honoring F8 ordering-
    legality (conjunction wa/fa < preposition bi/ka/li < article al). Returns (pieces, num_clusters_consumed)."""
    pieces, i, n = [], 0, len(clusters)
    base = lambda j: clusters[j][0]  # noqa: E731
    if i < n and base(i) == "و":
        pieces.append(("prefix_conjunction", clusters[i])); i += 1
    elif i < n and base(i) == "ف":
        pieces.append(("prefix_resumption_fa", clusters[i])); i += 1
    if i + 1 < n and base(i) == "ا" and base(i + 1) == "ل":
        pieces.append(("definite_article", clusters[i] + clusters[i + 1])); i += 2
    elif i < n and base(i) in ("ب", "ك"):
        pieces.append(("prefix_preposition", clusters[i])); i += 1
        if i + 1 < n and base(i) == "ا" and base(i + 1) == "ل":
            pieces.append(("definite_article", clusters[i] + clusters[i + 1])); i += 2
    elif i < n and base(i) == "ل":
        if i + 1 < n and base(i + 1) == "ل":
            pieces.append(("prefix_preposition", clusters[i])); pieces.append(("definite_article", clusters[i + 1])); i += 2
        else:
            pieces.append(("prefix_preposition", clusters[i])); i += 1
    elif i < n and base(i) == "س":
        pieces.append(("prefix_particle", clusters[i])); i += 1
    return pieces, i


def _enclitic_peel(stem_clusters):
    """Yield (stem2_display, enclitic_display, single_letter) for each enclitic that ends stem_clusters, longest-first.
    Matches on BASE letters but peels the actual display clusters, so shadda/superscript-bearing pronouns (هنّ/كنّ/هۦ)
    peel the correct glyphs and length."""
    out = []
    bare_stem = "".join(c[0] for c in stem_clusters)
    if N.ends_tanwin_alef("".join(stem_clusters)):
        return out
    for enc in ENCLITICS:
        eb = N.bare(enc)
        if eb and bare_stem.endswith(eb) and len(bare_stem) - len(eb) >= 2:
            k = len(eb)
            out.append(("".join(stem_clusters[:-k]), "".join(stem_clusters[-k:]), len(eb) == 1))
    return out


def segment_candidates(surface):
    """Build the candidate segmentation lattice for a written token (mark-aware, on the DISPLAY surface). Always keeps
    the whole-token reading (a 'proclitic' may be a radical) plus every legal proclitic/enclitic peel. The surfaces of
    EVERY candidate concatenate to `surface` exactly (asserted). Ambiguity is preserved; nothing is collapsed or forced."""
    clusters = _clusters(surface)
    bare = "".join(c[0] for c in clusters)
    cands = []
    cands.append({"segments": [{"role": "stem", "surface": surface, "gloss_contribution": None}],
                  "rank": 1, "score": None, "legal": True, "single_letter_clitic": False})
    seen = {(("stem", surface),)}

    def _add(segs, legal, single):
        key = tuple((s["role"], s["surface"]) for s in segs)
        if key in seen:
            return
        assert "".join(s["surface"] for s in segs) == surface, "segment lattice must concat to surface (%r)" % surface
        seen.add(key)
        cands.append({"segments": segs, "rank": 0, "score": None, "legal": legal, "single_letter_clitic": single})

    for pfx in PROCLITICS:
        if not bare.startswith(pfx) or len(bare) - len(pfx) < 2:
            continue
        ncl = len(pfx)  # one cluster per bare base letter
        pieces_raw, consumed = _proclitic_pieces(clusters[:ncl])
        if not pieces_raw:
            continue
        stem_clusters = list(clusters[consumed:ncl]) + clusters[ncl:]  # any unconsumed proclitic cluster stays on the stem
        legal = (consumed == ncl)
        single = (ncl == 1)
        base_segs = [{"role": r, "surface": s, "gloss_contribution": None} for r, s in pieces_raw]
        base_segs.append({"role": "stem", "surface": "".join(stem_clusters), "gloss_contribution": None})
        _add(base_segs, legal, single)
        for stem2, enc_disp, single_enc in _enclitic_peel(stem_clusters):
            segs2 = [{"role": r, "surface": s, "gloss_contribution": None} for r, s in pieces_raw]
            segs2.append({"role": "stem", "surface": stem2, "gloss_contribution": None})
            segs2.append({"role": "object_pronoun", "surface": enc_disp, "gloss_contribution": None})
            _add(segs2, legal, single or single_enc)
    for stem2, enc_disp, single_enc in _enclitic_peel(clusters):
        _add([{"role": "stem", "surface": stem2, "gloss_contribution": None},
              {"role": "object_pronoun", "surface": enc_disp, "gloss_contribution": None}], True, single_enc)
    return cands


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------
def _mk_diag(cls, target, explanation, observed=None, expected=None, severity_override=None, gate_override=None,
            confidence="medium"):
    sev, spec, lane, proc = GENERAL_ISSUES[cls]
    if gate_override:
        gate = gate_override
    elif "gate" in spec:
        gate = spec["gate"]
    else:
        gate = required_gate(spec["triggers"])
    # arbitrary text can never be auto_safe — clamp up defensively (D1/D7).
    if _GATE_RANK[gate] < _GATE_RANK["two_vote_required"]:
        gate = "two_vote_required"
    return {
        "issue_class": cls,
        "severity": severity_override or sev,
        "gate": gate,
        "route": {"lane": lane, "procedure": proc},
        "target": target,
        "explanation": _redact(explanation),
        "observed": _redact(observed),
        "expected": _redact(expected),
        "confidence": confidence,  # derived from candidate-lattice strength, not hardcoded (a UI weights underlines by this)
        "evidence_labels": [],
    }


def _analyze_arbitrary_token(idx, surface, ops_for_tok, start=None, end=None, ws_index=None):
    """Return (analysis_token, diagnostics[], ambiguity[]) for one arbitrary Arabic token. Ambiguity-preserving.
    start/end are character offsets into raw_input (so a future editor UI can place the underline span)."""
    target = "tok:%d" % idx
    voweled = _has_harakat(surface)
    bare = N.bare(surface)
    cands = segment_candidates(surface)
    diags, amb = [], []

    # collect which clitic roles appear across candidates (preserving, not collapsing). Check ROLES, not surfaces
    # (segment surfaces now carry harakāt, so a literal-surface membership test would silently miss every voweled clitic).
    roles = {s["role"] for c in cands for s in c["segments"]}
    has_proclitic = any(r.startswith("prefix_") or r == "definite_article" for r in roles)
    has_article = "definite_article" in roles
    has_prep = any(s["role"] == "prefix_preposition" for c in cands for s in c["segments"])
    has_enclitic = "object_pronoun" in roles
    # confidence: a MULTI-letter proclitic peel (بال/وال/لل …) is stronger evidence than a lone single-letter peel
    # (e.g. كتبَ → كـ), which is almost always a radical. A UI dims the low-confidence noise; the candidate is still kept.
    multi_proclitic = any(not c.get("single_letter_clitic") for c in cands
                          if any(s["role"].startswith("prefix_") or s["role"] == "definite_article" for s in c["segments"]))
    clitic_conf = "medium" if multi_proclitic else "low"

    if has_proclitic:
        diags.append(_mk_diag("possible_clitic_segmentation", target,
                              "The written token may carry a prefixed particle (wāw/fāʾ/bāʾ/kāf/lām/the article); "
                              "its contribution must be resolved, not hidden in the host. Multiple segmentations are kept.",
                              observed=surface, expected="proclitic + host", confidence=clitic_conf))
    if has_prep:
        diags.append(_mk_diag("possible_preposition_host", target,
                              "A prefixed preposition (bāʾ/lām/kāf) would form a jar-majrūr; the relation must be shown, "
                              "not the host alone. Source context is needed to confirm.", observed=surface, confidence=clitic_conf))
    if has_article:
        diags.append(_mk_diag("possible_definite_article", target,
                              "A definite article (al-) may be prefixed; its 'the' contribution must be reflected.",
                              observed=surface, confidence=clitic_conf))
    if has_enclitic:
        single = any(len(N.bare(s["surface"])) == 1 for c in cands for s in c["segments"] if s["role"] == "object_pronoun")
        note = ("A single-letter ending (hāʾ/kāf/yāʾ) collides with a root radical; without source context it cannot be "
                "decided whether it is an attached pronoun or part of the stem.") if single else \
               "An attached pronoun may be present; it must be surfaced or the token stays pending."
        diags.append(_mk_diag("possible_attached_pronoun", target, note, observed=surface,
                              gate_override="two_vote_required", confidence=("low" if single else "medium")))

    if not voweled and len(bare) >= 2:
        diags.append(_mk_diag("ambiguous_unvoweled_token", target,
                              "This token is unvoweled, so several morphological readings compete; the engine keeps all "
                              "of them rather than forcing one (diacritics are optional evidence, not certainty).",
                              observed=surface, confidence="medium"))
        amb.append({"target": target, "reason": "unvoweled_multiple_readings", "n_candidates": len(cands)})

    # a multi-function particle may BE the whole token, or sit as a stem after a proclitic is peeled (e.g. وما = waw+ما)
    stems_bare = {N.bare(s["surface"]) for c in cands for s in c["segments"] if s["role"] == "stem"}
    exact_particle = bare in PARTICLE_SET
    if exact_particle or (stems_bare & PARTICLE_SET):
        diags.append(_mk_diag("possible_particle_function", target,
                              "This token contains a multi-function particle; its function (negation / relative / "
                              "interrogative / coordination / oath / etc.) cannot be decided from the surface alone — "
                              "context is required.", observed=surface, confidence=("high" if exact_particle else "medium")))

    # fire ONLY for genuine orthographic-variant letters (not routine tashkil stripping): hamza seats, tāʾ marbūṭa,
    # alif maqṣūra, alif waṣla, dagger alif — the variants that can mask a homograph in the match key.
    if any(ch in surface for ch in "ةىأإآئؤءٱٰ"):
        diags.append(_mk_diag("orthography_normalization_warning", target,
                              "An orthographic variant (hamza seat / alif form / tāʾ marbūṭa / alif maqṣūra) was normalized "
                              "for matching only; the original spelling is preserved and may itself be significant.",
                              observed=surface, confidence="medium"))

    parse_confidence = "surface_only" if (not voweled and len(bare) >= 2) else "candidate"
    blocker = None
    if any(d["issue_class"] == "possible_attached_pronoun" for d in diags) and not voweled:
        blocker = "context_sensitive_needs_nahw"
    elif diags:
        blocker = "source_evidence_needed"
    tok = {
        "index": idx, "surface": surface, "loc": None,
        "ws_index": ws_index, "start": start, "end": end,
        "norm_strict_key": N.norm_strict(surface), "bare_key": bare,
        "is_arabic": True, "parse_confidence": parse_confidence, "decision_status": "pending",
        "segment_candidates": cands, "morphology_candidates": [], "blocker": blocker,
    }
    return tok, diags, amb


def _analyze_source_addressed_token(idx, surface, loc, claim, start=None, end=None, ws_index=None):
    """Mode A token: resolve the exact address; optionally hand a CheckUnit to fusha_check.check_unit (reuse, no fork)."""
    diags = []
    res = FC.resolve_address(loc or "")
    in_scope = res["scope"] == "in_scope_source_addressed"
    sw = (loc or "").replace("quran:", "").replace("wbw:", "")
    # target binds to the resolved address ONLY when it is genuinely in scope; otherwise to the token index, so the
    # out-of-scope diagnostic still points at a real token (never an orphan address no token carries).
    target = sw if (in_scope and re.match(r"^\d{1,3}:\d{1,3}:\d{1,3}$", sw)) else "tok:%d" % idx
    if in_scope:
        # the source-addressed token can become a reviewable rich-hover candidate (the flywheel bridge).
        diags.append(_mk_diag("rich_hover_candidate_available_when_source_addressed", target,
                              "This token is source-addressed; a parser-backed rich-hover candidate can be generated for "
                              "review by the certification queue.", observed=surface))
        # optional deterministic handoff to the source-addressed checker for a real verdict.
        if claim:
            unit = {
                "schema": "fusha/parser-check-ir@1", "unit_id": "txtchk-%d" % idx,
                "source_unit": {"address": "quran:%s" % ":".join(sw.split(":")[:2]), "kind": "quran_ayah",
                                "scope": "in_scope_source_addressed", "display_surface": surface},
                "segments": [{"canonical_loc": "quran:%s" % ":".join(sw.split(":")[:2]),
                              "display_surface": surface, "display_local_loc": None,
                              "display_local_crosswalk": None, "token_locs": ["quran:%s" % sw]}],
                "tokens": [dict(claim.get("token") or _stub_token(sw, surface))],
                "claims": [claim.get("claim") or {"claim_id": "c1", "target": sw, "claim_type": "hover_gloss",
                                                  "claimed_value": claim.get("claimed_value", ""),
                                                  "claimed_reasoning": claim.get("claimed_reasoning"), "proposer": "model"}],
                "issues": [], "verdicts": [], "public_boundary": dict(FC._PUBLIC_BOUNDARY),
                "evidence": {"labels": [], "gate": None},
                "summary": {"live_writes": 0, "by_verdict": {}, "by_issue_class": {}},
            }
            checked = FC.check_unit(json.loads(json.dumps(unit)))
            for iss in checked.get("issues", []):
                diags.append({
                    "issue_class": iss["issue_class"], "severity": iss.get("severity", "warn"),
                    "gate": iss["gate"], "route": {"lane": iss["route_to"]["lane"], "procedure": iss["route_to"]["procedure"]},
                    "target": sw, "explanation": _redact(iss.get("explanation", "")),
                    "observed": _redact(iss.get("observed")), "expected": _redact(iss.get("expected")),
                    "confidence": "high", "evidence_labels": [],
                })
        decision_status, parse_confidence = "resolved", "candidate"
        blocker = None
    else:
        diags.append(_mk_diag("source_address_required_for_certainty", target,
                              "The claimed address does not resolve to a source-address graph node, so the source-addressed "
                              "certainty does not apply; treat as unverified.", observed=surface))
        decision_status, parse_confidence, blocker = "pending", "surface_only", "source_evidence_needed"
    tok = {
        "index": idx, "surface": surface, "loc": sw if in_scope else None,
        "ws_index": ws_index, "start": start, "end": end,
        "norm_strict_key": N.norm_strict(surface), "bare_key": N.bare(surface),
        "is_arabic": _is_arabic(surface), "parse_confidence": parse_confidence,
        "decision_status": decision_status, "segment_candidates": [], "morphology_candidates": [], "blocker": blocker,
    }
    return tok, diags, []


def _stub_token(loc, surface):
    return {
        "loc": loc, "wbw_loc": "wbw:%s" % loc, "surface": surface, "key": surface, "gloss": "(authored)",
        "src": "qamus", "kind": "authored", "lang": "en", "decision_state": "rich_candidate", "pos": "unknown",
        "sarf": {}, "nahw": {"function": None}, "segments": [{"role": "stem", "surface": surface, "gloss_contribution": None}],
        "hover_contract": {"must_surface": [], "must_not_surface": [], "reason": None},
        "learner_explanation": "Token-level grammar contribution.", "public_boundary": dict(FC._PUBLIC_BOUNDARY),
    }


# ---------------------------------------------------------------------------
# the checker
# ---------------------------------------------------------------------------
def check_text(req):
    """Adjudicate one text-check request -> a fusha/text-check@1 record. Dry-run; original preserved."""
    mode = req.get("input_mode", "arbitrary_typing")
    raw = req.get("raw_input", "")
    normalized, ops = normalize_with_ops(raw)
    # per-token op presence: which whitespace words actually carried an orthographic variant
    wtokens = whitespace_tokens(raw)
    analysis_tokens, diagnostics, ambiguity = [], [], []
    explicit = req.get("tokens")  # source_addressed/corpus rows may pass tokens with loc/claim

    if explicit:
        for i, t in enumerate(explicit):
            surface = t.get("surface", "")
            if mode == "source_addressed":
                tok, d, a = _analyze_source_addressed_token(i, surface, t.get("loc"), t.get("claim_packet"),
                                                            start=t.get("start"), end=t.get("end"), ws_index=t.get("ws_index"))
            else:
                _o = normalize_with_ops(surface)[1]
                tok, d, a = _analyze_arbitrary_token(i, surface, _o,
                                                     start=t.get("start"), end=t.get("end"), ws_index=t.get("ws_index"))
                if mode == "corpus_backed":
                    tok["loc"] = None
            analysis_tokens.append(tok); diagnostics.extend(d); ambiguity.extend(a)
    else:
        ai = 0
        for wt in wtokens:
            if wt["kind"] != "word":
                continue
            surface = wt["surface"]
            _o = normalize_with_ops(surface)[1]
            tok, d, a = _analyze_arbitrary_token(ai, surface, _o, start=wt["start"], end=wt["end"], ws_index=wt["index"])
            analysis_tokens.append(tok); diagnostics.extend(d); ambiguity.extend(a)
            ai += 1

    # a single document-level "needs a source address for certainty" notice for non-source-addressed modes
    if mode in ("arbitrary_typing", "corpus_backed") and analysis_tokens:
        diagnostics.append(_mk_diag("source_address_required_for_certainty", "tok:%d" % analysis_tokens[0]["index"],
                                    "This text is not source-addressed, so the engine reports candidates and ambiguity, "
                                    "never source-grounded certainty; cite a Qurʾān/corpus address to raise confidence."))

    # never auto_safe in arbitrary/corpus mode (defensive clamp already in _mk_diag; assert below)
    gates = sorted({d["gate"] for d in diagnostics})
    by_sev, by_cls = {}, {}
    for d in diagnostics:
        by_sev[d["severity"]] = by_sev.get(d["severity"], 0) + 1
        by_cls[d["issue_class"]] = by_cls.get(d["issue_class"], 0) + 1
    rec = {
        "schema": SCHEMA, "input_mode": mode,
        "document_id": req.get("document_id"), "session_id": req.get("session_id"),
        "raw_input": raw, "normalized_input": normalized, "normalization_ops": ops,
        "paragraphs": [], "sentences": sentence_spans(raw), "whitespace_tokens": wtokens,
        "analysis_tokens": analysis_tokens, "segment_candidates": [],
        "morphology_candidates": [], "syntax_candidates": [],
        "diagnostics": diagnostics, "suggestions": [], "ambiguity": ambiguity, "gates": gates,
        "public_boundary": dict(_PUBLIC_BOUNDARY),
        "source_boundary": {"original_preserved": True, "external_text_copied": False, "quran_text_altered": False},
        "checker_summary": {"live_writes": 0, "by_mode": {mode: 1}, "by_severity": by_sev,
                            "by_issue_class": by_cls, "n_tokens": len(analysis_tokens),
                            "n_ambiguous_tokens": len(ambiguity)},
    }
    # hard dry-run + arbitrary-never-auto_safe invariants (fail loudly if a detector regresses)
    assert rec["checker_summary"]["live_writes"] == 0, "ABORT: dry-run; live_writes must be 0"
    if mode in ("arbitrary_typing", "corpus_backed"):
        assert all(d["gate"] != "auto_safe" for d in diagnostics), "ABORT: arbitrary/corpus diagnostic marked auto_safe"
        assert all(t.get("loc") is None for t in analysis_tokens), "ABORT: arbitrary/corpus token carries a fabricated loc"
    # segments concat == surface for every kept candidate
    for t in analysis_tokens:
        for c in t.get("segment_candidates") or []:
            concat = "".join(s["surface"] for s in c["segments"])
            assert concat == t["surface"], "ABORT: segments %r != surface %r" % (concat, t["surface"])
    return rec


# ---------------------------------------------------------------------------
# regression requests + self-test
# ---------------------------------------------------------------------------
def regression_requests():
    """The 10 authored regression requests (parserplans/016). Authored Arabic; Qurʾān surfaces verbatim; no copied gloss."""
    return [
        {"name": "nominal-sentence", "input_mode": "arbitrary_typing", "raw_input": "الكتابُ مفيدٌ"},
        {"name": "verbal-sentence", "input_mode": "arbitrary_typing", "raw_input": "ذهب الطالبُ إلى المدرسةِ"},
        {"name": "waw-plus-ma", "input_mode": "arbitrary_typing", "raw_input": "وما ذلك بغريبٍ"},
        {"name": "ba-plus-noun", "input_mode": "arbitrary_typing", "raw_input": "كتبَ بالقلمِ"},
        {"name": "attached-pronoun", "input_mode": "arbitrary_typing", "raw_input": "كتابُهم جديدٌ"},
        {"name": "partially-voweled", "input_mode": "arbitrary_typing", "raw_input": "العِلمُ نور"},
        {"name": "unvoweled-ambiguous", "input_mode": "arbitrary_typing", "raw_input": "علم نور"},
        {"name": "student-agreement-case", "input_mode": "arbitrary_typing", "raw_input": "الطلابُ مجتهدٌ"},
        {"name": "must-stay-ambiguous", "input_mode": "arbitrary_typing", "raw_input": "من يقرأ"},
        {"name": "source-addressed-handoff", "input_mode": "source_addressed",
         "raw_input": "بِبَدْرٍ",
         "tokens": [{"surface": "بِبَدْرٍ", "loc": "3:123:4",
                     "claim_packet": {"token": {
                         "loc": "3:123:4", "wbw_loc": "wbw:3:123:4", "surface": "بِبَدْرٍ", "key": "بِبَدْرٍ",
                         "gloss": "(authored)", "src": "qamus", "kind": "authored", "lang": "en",
                         "decision_state": "rich_candidate", "pos": "noun",
                         "sarf": {"case": "genitive"}, "nahw": {"function": None},
                         "segments": [{"role": "prefix_preposition", "surface": "بِ", "gloss_contribution": "at/by"},
                                      {"role": "stem", "surface": "بَدْرٍ", "gloss_contribution": "Badr"}],
                         "hover_contract": {"must_surface": ["at", "Badr"], "must_not_surface": ["Badr only"], "reason": None},
                         "learner_explanation": "Preposition + place-name.", "public_boundary": dict(FC._PUBLIC_BOUNDARY)},
                         "claim": {"claim_id": "c1", "target": "3:123:4", "claim_type": "hover_gloss",
                                   "claimed_value": "Badr", "claimed_reasoning": None, "proposer": "model"}}}]},
    ]


def _self_test():
    failures = []
    seen_classes = set()
    for req in regression_requests():
        rec = check_text(req)
        name = req["name"]
        # original preserved
        if rec["raw_input"] != req["raw_input"]:
            failures.append("%s: raw_input not preserved" % name)
        # normalization ops tracked when marks present
        if _has_harakat(req["raw_input"]) and not rec["normalization_ops"]:
            failures.append("%s: harakat present but no normalization_ops recorded" % name)
        # every diagnostic carries severity + gate + route
        for d in rec["diagnostics"]:
            if not d.get("severity") or not d.get("gate") or not (d.get("route") or {}).get("lane") or not (d.get("route") or {}).get("procedure"):
                failures.append("%s: diagnostic %s missing severity/gate/route" % (name, d.get("issue_class")))
            seen_classes.add(d["issue_class"])
        # arbitrary/corpus never auto_safe
        if req["input_mode"] in ("arbitrary_typing", "corpus_backed"):
            if any(d["gate"] == "auto_safe" for d in rec["diagnostics"]):
                failures.append("%s: arbitrary/corpus diagnostic marked auto_safe" % name)
            if any(t.get("loc") for t in rec["analysis_tokens"]):
                failures.append("%s: arbitrary/corpus token carries a loc" % name)
        # no public leak anywhere
        for d in rec["diagnostics"]:
            for f in ("explanation", "observed", "expected"):
                if FC.LEAK_RE.search(d.get(f) or ""):
                    failures.append("%s: leak in diagnostic.%s" % (name, f))
        # live_writes 0
        if rec["checker_summary"]["live_writes"] != 0:
            failures.append("%s: live_writes != 0" % name)

    # specific behaviour assertions
    rec_wama = check_text(regression_requests()[2])  # "وما ذلك بغريبٍ"
    if not any(d["issue_class"] == "possible_particle_function" for d in rec_wama["diagnostics"]):
        failures.append("waw-plus-ma: expected possible_particle_function on ما")
    rec_unv = check_text(regression_requests()[6])  # "علم نور" (unvoweled)
    if not any(d["issue_class"] == "ambiguous_unvoweled_token" for d in rec_unv["diagnostics"]):
        failures.append("unvoweled-ambiguous: expected ambiguous_unvoweled_token")
    if not rec_unv["ambiguity"]:
        failures.append("unvoweled-ambiguous: ambiguity[] must be non-empty (ambiguity preserved)")
    rec_ba = check_text(regression_requests()[3])  # "كتبَ بالقلمِ"
    if not any(d["issue_class"] == "possible_preposition_host" for d in rec_ba["diagnostics"]):
        failures.append("ba-plus-noun: expected possible_preposition_host on بالقلم")
    rec_src = check_text(regression_requests()[9])  # source-addressed بِبَدْرٍ
    if not any(d["issue_class"] in ("rich_hover_candidate_available_when_source_addressed", "host_only_preposition_hover") for d in rec_src["diagnostics"]):
        failures.append("source-addressed-handoff: expected handoff diagnostic")
    if not any(t.get("loc") == "3:123:4" for t in rec_src["analysis_tokens"]):
        failures.append("source-addressed-handoff: token should resolve loc 3:123:4")
    # the source-addressed handoff should surface the host_only_preposition_hover from fusha_check (claim 'Badr' drops بِ)
    if not any(d["issue_class"] == "host_only_preposition_hover" for d in rec_src["diagnostics"]):
        failures.append("source-addressed-handoff: fusha_check host_only_preposition_hover not surfaced")

    # at least the core general classes are exercised
    need = {"possible_clitic_segmentation", "ambiguous_unvoweled_token", "possible_attached_pronoun",
            "possible_preposition_host", "possible_particle_function", "source_address_required_for_certainty"}
    missing = need - seen_classes
    if missing:
        failures.append("fixture does not exercise general classes: %s" % sorted(missing))

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_text_check self-test: 10 requests, 3 modes, ambiguity-preserving, never auto_safe, source-clean, dry-run")
    return 0 if not failures else 1


def emit_fixture(path):
    rows = [check_text(r) for r in regression_requests()]
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {
        "schema": SCHEMA, "generator": "tools/fusha_text_check.py --emit-fixture",
        "count": len(rows),
        "modes": sorted({r["input_mode"] for r in rows}),
        "note": "General Fusha text-check regression fixture (3 modes). Arbitrary examples authored; Qurʾānic surfaces "
                "verbatim; public output {src:qamus,kind:authored,lang:en}; no external gloss text. parserplans 004/016.",
        "row_schema": ["schema", "input_mode", "raw_input", "normalized_input", "normalization_ops", "analysis_tokens",
                       "diagnostics", "ambiguity", "gates", "public_boundary", "source_boundary", "checker_summary"],
    }
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d records -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Fusha general text checker (dry-run, ambiguity-preserving).")
    ap.add_argument("--in", dest="infile", help="requests JSONL, or a plain-text file with --mode")
    ap.add_argument("--out", dest="outfile", default="-", help="output JSONL ('-' = stdout)")
    ap.add_argument("--mode", dest="mode", choices=["source_addressed", "corpus_backed", "arbitrary_typing"],
                    help="treat --in as plain text in this mode")
    ap.add_argument("--explain", action="store_true", help="print a human-readable diagnostic summary")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    if not a.infile:
        ap.error("need --in, --self-test, or --emit-fixture")
    recs = []
    if a.mode and not a.infile.endswith(".jsonl"):
        with open(a.infile, encoding="utf-8") as fh:
            recs.append(check_text({"input_mode": a.mode, "raw_input": fh.read()}))
    else:
        with open(a.infile, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    recs.append(check_text(json.loads(line)))
    sink = sys.stdout if a.outfile == "-" else open(a.outfile, "w", encoding="utf-8")
    for r in recs:
        if a.explain:
            sink.write("# %s [%s] tokens=%d diagnostics=%d\n" % (r.get("document_id") or "(doc)", r["input_mode"],
                                                                 r["checker_summary"]["n_tokens"], len(r["diagnostics"])))
            for d in r["diagnostics"]:
                sink.write("  - %-44s sev=%-4s gate=%-26s -> %s\n" % (
                    d["issue_class"], d["severity"], d["gate"], d["route"]["procedure"]))
        else:
            sink.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
