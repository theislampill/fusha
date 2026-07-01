#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone-friendly clitic splitter.

This module wraps the existing mark-aware splitter in `fusha_text_check` and adds
stable labels/gloss hints for parser previews. It does not certify a split: it
keeps the whole-token reading and every legal candidate.
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

ROLE_META = {
    "prefix_conjunction": ("qg-conjunction", "CONJ", "and"),
    "prefix_resumption_fa": ("qg-result", "FA", "so/then"),
    "prefix_preposition": ("qg-preposition", "P", None),
    "prefix_particle": ("qg-particle", "FUT", "will"),
    "definite_article": ("qg-article", "ART", "the"),
    "object_pronoun": ("qg-object-pronoun", "OBJ", None),
    "stem": ("qg-noun-stem", "STEM", None),
}

SPECIAL_SEGMENTATIONS = {
    "انما": [
        ("particle_inna", "إن", "qg-particle", "INNA", "indeed/only"),
        ("ma_particle", "ما", "qg-ma-particle", "MA", "restriction particle"),
    ],
    "إنما": [
        ("particle_inna", "إن", "qg-particle", "INNA", "indeed/only"),
        ("ma_particle", "ما", "qg-ma-particle", "MA", "restriction particle"),
    ],
}


def _prep_gloss(surface):
    b = N.bare(surface)
    if b == "ب":
        return "by/with/in"
    if b == "ل":
        return "for/to/belongs to"
    if b == "ك":
        return "like/as"
    return "preposition"


def enrich_segment(seg):
    role = seg.get("role")
    surface = seg.get("surface", "")
    cls, label, gloss = ROLE_META.get(role, ("qg-relation", "SEG", None))
    if role == "prefix_preposition":
        gloss = _prep_gloss(surface)
    if role == "object_pronoun" and gloss is None:
        gloss = "attached pronoun"
    return {
        "role": role,
        "surface": surface,
        "class": cls,
        "label": label,
        "gloss_contribution": gloss,
    }


def _special_candidate(surface):
    key = N.norm_strict(surface)
    spec = SPECIAL_SEGMENTATIONS.get(key) or SPECIAL_SEGMENTATIONS.get(surface)
    if not spec:
        return None
    if "".join(part[1] for part in spec) != surface:
        return None
    return {
        "segments": [
            {
                "role": role,
                "surface": seg_surface,
                "class": cls,
                "label": label,
                "gloss_contribution": gloss,
            }
            for role, seg_surface, cls, label, gloss in spec
        ],
        "rank": 0,
        "score": 3.0,
        "legal": True,
        "single_letter_clitic": False,
        "evidence_class": "pinned_function_cluster",
    }


def split_clitics(surface):
    """Return candidate segmentations for `surface`, enriched for qg previews."""
    raw = TC.segment_candidates(surface)
    out = []
    for i, cand in enumerate(raw):
        segs = [enrich_segment(s) for s in cand.get("segments") or []]
        out.append({
            "segments": segs,
            "rank": cand.get("rank", i + 1),
            "score": cand.get("score"),
            "legal": cand.get("legal"),
            "single_letter_clitic": cand.get("single_letter_clitic", False),
            "evidence_class": "existing_mark_aware_splitter",
        })
    special = _special_candidate(surface)
    if special:
        out.append(special)
    seen = set()
    unique = []
    for cand in out:
        key = tuple((s["role"], s["surface"]) for s in cand["segments"])
        if key in seen:
            continue
        seen.add(key)
        assert "".join(s["surface"] for s in cand["segments"]) == surface
        unique.append(cand)
    unique.sort(key=lambda c: (0 if c.get("evidence_class") == "pinned_function_cluster" else 1,
                               0 if c.get("legal") else 1,
                               -len(c.get("segments") or [])))
    for idx, cand in enumerate(unique, 1):
        cand["rank"] = idx
    return unique


def main():
    ap = argparse.ArgumentParser(description="Emit clitic segmentation candidates for one token.")
    ap.add_argument("surface")
    args = ap.parse_args()
    print(json.dumps(split_clitics(args.surface), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
