#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rule-based context candidates for the standalone parser MVP."""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402

STANDALONE_PREPS = {"من", "إلى", "الى", "على", "في", "عن", "مع", "حتى", "بين"}


def token_context_candidates(tokens):
    """Annotate each token with conservative context candidates."""
    by_index = {t["index"]: [] for t in tokens}
    for i, tok in enumerate(tokens):
        surface = tok.get("surface", "")
        bare = N.bare(surface)
        qg = tok.get("qg_segments") or []
        if any(seg.get("class") == "qg-preposition" for seg in qg):
            by_index[tok["index"]].append({
                "relation": "jar_majrur_inside_token",
                "status": "pending_context",
                "gate": "two_vote_required",
                "explanation": "attached preposition must govern the host; keep preposition plus host visible",
            })
        if bare in STANDALONE_PREPS and i + 1 < len(tokens):
            by_index[tok["index"]].append({
                "relation": "preposition_governs_next",
                "target": "tok:%d" % tokens[i + 1]["index"],
                "status": "candidate",
                "gate": "two_vote_required",
                "explanation": "standalone preposition candidate governing the following token",
            })
        if bare in {"ما", "وما"}:
            by_index[tok["index"]].append({
                "relation": "ma_function_pending",
                "status": "pending_context",
                "gate": "two_vote_required",
                "alternatives": ["negative", "relative", "interrogative", "conditional", "source/oath context"],
                "explanation": "mā must be decided by function, not by one English gloss",
            })
        if bare in {"انما", "إنما"}:
            by_index[tok["index"]].append({
                "relation": "restriction_particle_cluster",
                "status": "candidate",
                "gate": "two_vote_required",
                "explanation": "innamā restricts or emphasizes by context; keep the cluster visible",
            })
        if bare in {"لما", "لم"}:
            by_index[tok["index"]].append({
                "relation": "lam_particle_mood_or_time",
                "status": "pending_context",
                "gate": "two_vote_required",
                "explanation": "lām/mā cluster and mood/time function require context",
            })
        if any(seg.get("role") == "object_pronoun" for seg in qg):
            by_index[tok["index"]].append({
                "relation": "attached_object_or_complement",
                "status": "candidate",
                "gate": "two_vote_required",
                "explanation": "attached pronoun changes the token contribution and cannot be hidden",
            })
    return by_index


def main():
    ap = argparse.ArgumentParser(description="Context candidates for standalone parser JSON.")
    ap.add_argument("path")
    args = ap.parse_args()
    with open(args.path, encoding="utf-8") as fh:
        rec = json.load(fh)
    print(json.dumps(token_context_candidates(rec.get("tokens") or []), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
