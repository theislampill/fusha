#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone Fusha parser/checker MVP.

The output is a source-clean preview IR. It supports Qamus/RH-LIVE authoring,
learner tutoring, and arbitrary typing prototypes without claiming live/source
certification.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402
from tools import fusha_text_check as TC  # noqa: E402
from tools.fusha_clitic_splitter import split_clitics  # noqa: E402
from tools.fusha_pattern_engine import FUNCTION_WORDS, build_morphology, preview_segments  # noqa: E402
from tools.fusha_context_parser import token_context_candidates  # noqa: E402

SCHEMA = "fusha/standalone-parse@1"
PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}
CONTEXT_REQUIRED_FUNCTION_KEYS = {"ما", "وما", "لما", "انما", "إنما", "من", "لا", "إلا", "الا"}
HIGH_RISK_BARE_MATCH_SURFACES = {"إله", "اله"}


def _selected(seg_cands, morph_cands):
    if not morph_cands:
        return None, None
    morph = morph_cands[0]
    if morph.get("pos") == "particle":
        for cand in seg_cands:
            if cand.get("evidence_class") == "pinned_function_cluster":
                return cand, morph
    ref = morph.get("segment_candidate_ref", 0)
    if ref >= len(seg_cands):
        ref = 0
    selected = seg_cands[ref]
    selected_segments = selected.get("segments") or []
    selected_surface = "".join(seg.get("surface", "") for seg in selected_segments)
    selected_collapsed = len(selected_segments) == 1 and selected_segments[0].get("role") == "stem"
    rich_roles = {
        "prefix_preposition",
        "definite_article",
        "prefix_conjunction",
        "prefix_particle",
        "particle_inna",
        "ma_particle",
    }
    if selected_collapsed and morph.get("evidence_class") in {"largelexicon_sample", "largelexicon_full"}:
        for cand in seg_cands:
            segments = cand.get("segments") or []
            if len(segments) <= 1:
                continue
            if "".join(seg.get("surface", "") for seg in segments) != selected_surface:
                continue
            if any(seg.get("role") in rich_roles for seg in segments):
                return cand, morph
    return selected, morph


def _candidate_collision(surface, seg_cands, morph_cands, morph):
    if not morph:
        return None
    features = morph.get("features") or {}
    if features.get("match_basis") == "bare_match" and N.bare(surface) in HIGH_RISK_BARE_MATCH_SURFACES:
        return {
            "kind": "unsafe_bare_match",
            "surface": surface,
            "route": ["sarf", "nahw"],
            "basis": features.get("match_basis"),
            "reason": "bare-match largelexicon evidence is useful internally but not a public hover selection for this high-risk surface",
        }
    tops = []
    if morph_cands:
        best = max(float(c.get("score") or 0.0) for c in morph_cands)
        tops = [c for c in morph_cands if float(c.get("score") or 0.0) == best]
    if len(tops) < 2:
        return None
    if all(c.get("evidence_class") == "function_inventory" and c.get("pos") == "particle" for c in tops):
        return None
    pos_values = {c.get("pos") for c in tops}
    lemmas = {c.get("lemma") for c in tops}
    roots = {c.get("root") for c in tops}
    refs = {c.get("segment_candidate_ref") for c in tops}
    if len(pos_values) > 1 or len(lemmas) > 1 or len(roots) > 1:
        return {
            "kind": "segmentation_or_pos_collision",
            "surface": surface,
            "candidate_count_at_top_score": len(tops),
            "candidate_refs": sorted(int(ref) for ref in refs if ref is not None),
            "pos_values": sorted(str(v) for v in pos_values),
            "route": ["sarf", "nahw"],
        }
    return None


def _function_needs_context(surface, morph):
    if not morph or morph.get("evidence_class") != "function_inventory":
        return False
    keys = {surface, N.norm_strict(surface), N.bare(surface)}
    return bool(keys & CONTEXT_REQUIRED_FUNCTION_KEYS & set(FUNCTION_WORDS))


def _gate(surface, seg_cands, morph, context, morph_cands=None):
    bare = N.bare(surface)
    if not morph:
        return "blocked", None
    collision = _candidate_collision(surface, seg_cands, morph_cands or [], morph)
    if collision:
        return "lexical_collision_requires_context", collision
    if _function_needs_context(surface, morph) or bare in {"ما", "وما", "لما", "انما", "إنما"}:
        return "pending_context", None
    if any(c.get("status") == "pending_context" for c in context):
        return "pending_context", None
    if len(seg_cands) > 1 and morph.get("evidence_class") not in {"seed_lexicon", "pinned_pattern"}:
        return "ambiguous", None
    if morph.get("evidence_class") in {"seed_lexicon", "pinned_pattern", "function_inventory", "largelexicon_sample", "largelexicon_full"}:
        return "likely_from_internal_pattern", None
    return "ambiguous", None


def _parse_key(qg, morph):
    labels = [seg.get("label") or seg.get("role", "SEG").upper() for seg in qg]
    pos = (morph or {}).get("pos") or "unknown"
    return {
        "key": "+".join(labels) if labels else "SURFACE",
        "summary": "%s candidate from %s" % (pos, (morph or {}).get("evidence_class", "surface")),
    }


def _hover(surface, qg, morph, context, gate):
    if gate == "lexical_collision_requires_context":
        return {
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "token_contribution_gloss": "candidate analysis pending",
            "morphline": "lexical collision requires context",
            "segments": [],
            "context_notes": [c.get("explanation") for c in context],
            "learner_explanation": "Multiple analyses compete here; keep the token pending until source/context evidence selects one.",
        }
    segment_bits = [seg.get("gloss_contribution") for seg in qg if seg.get("gloss_contribution")]
    gloss = " + ".join(segment_bits) if segment_bits else (morph or {}).get("gloss_hint")
    if not gloss:
        gloss = "surface candidate"
    explanation = "Token preview preserves visible grammar pieces."
    if gate == "pending_context":
        explanation = "Context is needed before this can become a certified token hover."
    return {
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "token_contribution_gloss": gloss,
        "morphline": _parse_key(qg, morph)["summary"],
        "segments": qg,
        "context_notes": [c.get("explanation") for c in context],
        "learner_explanation": explanation,
    }


def _token(idx, wt, db="smoke"):
    surface = wt["surface"]
    segs = split_clitics(surface)
    morph = build_morphology(surface, segs, db=db)
    selected_seg, selected_morph = _selected(segs, morph)
    qg = preview_segments(surface, selected_seg, selected_morph) if selected_seg and selected_morph else []
    tok = {
        "index": idx,
        "ref": "tok:%d" % idx,
        "surface": surface,
        "loc": None,
        "span": {"start": wt.get("start"), "end": wt.get("end")},
        "normalization": {
            "norm_strict": N.norm_strict(surface),
            "bare": N.bare(surface),
        },
        "segment_candidates": segs,
        "morphology_candidates": morph,
        "context_candidates": [],
        "selected_preview": None,
        "qg_segments": qg,
        "hover_preview": None,
        "confidence_gate": "blocked",
        "blocker_class": None,
        "blocker_reason": None,
    }
    tok["selected_preview"] = {
        "segment_candidate_rank": selected_seg.get("rank") if selected_seg else None,
        "morphology_rank": selected_morph.get("rank") if selected_morph else None,
        "parse_key": _parse_key(qg, selected_morph),
    } if selected_seg and selected_morph else None
    return tok


def parse_text(text, document_id=None, db="smoke"):
    normalized, ops = TC.normalize_with_ops(text)
    wtokens = [wt for wt in TC.whitespace_tokens(text) if wt.get("kind") == "word"]
    tokens = [_token(i, wt, db=db) for i, wt in enumerate(wtokens)]
    ctx_by_idx = token_context_candidates(tokens)
    diagnostics = []
    for tok in tokens:
        ctx = ctx_by_idx.get(tok["index"], [])
        tok["context_candidates"] = ctx
        seg, morph = _selected(tok.get("segment_candidates") or [], tok.get("morphology_candidates") or [])
        gate, collision = _gate(tok["surface"], tok.get("segment_candidates") or [], morph, ctx, tok.get("morphology_candidates") or [])
        tok["confidence_gate"] = gate
        if collision:
            tok["collision"] = collision
            for cand in tok.get("morphology_candidates") or []:
                if cand.get("rank") == 1:
                    cand["selection_status"] = "candidate_only"
                    cand["selection_blocker"] = gate
            tok["qg_segments"] = []
            tok["selected_preview"] = None
        if gate in {"pending_context", "ambiguous", "blocked", "lexical_collision_requires_context"}:
            tok["blocker_class"] = {
                "pending_context": "context_sensitive",
                "ambiguous": "ambiguous_surface",
                "blocked": "no_parse_candidate",
                "lexical_collision_requires_context": "lexical_collision",
            }[gate]
            tok["blocker_reason"] = (
                "multiple high-risk analyses compete; no public hover projection selected"
                if gate == "lexical_collision_requires_context"
                else "standalone parser preview is not source-address certification"
            )
        tok["hover_preview"] = _hover(tok["surface"], tok.get("qg_segments") or [], morph, ctx, gate)
        for c in ctx:
            diagnostics.append({
                "target": tok["ref"],
                "issue_class": c.get("relation"),
                "gate": c.get("gate", "two_vote_required"),
                "route": "nahw" if "ma_" in c.get("relation", "") or "govern" in c.get("relation", "") else "sarf",
                "explanation": c.get("explanation"),
            })
    return {
        "schema": SCHEMA,
        "input_mode": "arbitrary_typing",
        "db": db,
        "document_id": document_id,
        "raw_input": text,
        "normalized_input": normalized,
        "normalization_ops": ops,
        "tokens": tokens,
        "diagnostics": diagnostics,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "source_boundary": {
            "original_preserved": True,
            "external_text_copied": False,
            "quran_text_altered": False,
        },
        "summary": {
            "live_writes": 0,
            "n_tokens": len(tokens),
            "n_pending_context": sum(1 for t in tokens if t["confidence_gate"] == "pending_context"),
            "n_ambiguous": sum(1 for t in tokens if t["confidence_gate"] == "ambiguous"),
            "n_lexical_collision": sum(1 for t in tokens if t["confidence_gate"] == "lexical_collision_requires_context"),
        },
    }


def emit_fixtures(path):
    from tools.validate_fusha_standalone_parse import FIXTURES  # noqa: E402
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for text in FIXTURES:
            fh.write(json.dumps(parse_text(text), ensure_ascii=False, sort_keys=True) + "\n")
    print("wrote %d fixtures -> %s" % (len(FIXTURES), path))


def main():
    ap = argparse.ArgumentParser(description="Standalone Fusha parser/checker MVP.")
    ap.add_argument("--text")
    ap.add_argument("--out")
    ap.add_argument("--emit-fixtures")
    ap.add_argument("--db", choices=["smoke", "largelexicon"], default="smoke")
    args = ap.parse_args()
    if args.emit_fixtures:
        emit_fixtures(args.emit_fixtures)
        return 0
    if args.text is None:
        ap.error("need --text or --emit-fixtures")
    rec = parse_text(args.text, db=args.db)
    data = json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(data + "\n")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
