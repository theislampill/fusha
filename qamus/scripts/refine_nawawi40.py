#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SN8 — refine the Nawawī-40 diff with the upgraded sarf/nahw skills.

The stage-2 diff (diff_against_qamus.py) is deliberately conservative: it refuses to
tie a candidate to any Qamus root containing a weak/hamza letter, so weak-root hadith
forms (رَوَاهُ ر-و-ي, أَقَامَ ق-و-م) land in `new_root_or_unknown_root` even when Qamus
HAS the root. That is the dominant false-positive source.

This refinement adds, review-only and never auto-certifying:
  * weak-aware root recovery (و/ي may surface as ا/ى or elide) -> re-buckets recovered
    forms out of `new_root_or_unknown_root`;
  * a wazn-based POS guess (verb / maṣdar / participle / particle);
  * a Fusha-learning priority (root already in Qurʾān-Qamus = high reuse) and a
    Ṣaḥīḥayn-recurrence likelihood (hadith-technical vocabulary that will recur);
  * before/after counts.

Reads the committed index + the (git-ignored, regenerable) diff output. NO live writes.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools import normalize_ar as N

_WEAK = set("اوىيءأإؤئ")
# hadith-isnād / technical vocabulary — low Qamus priority, high Ṣaḥīḥayn-recurrence
HADITH_TECH = set("روى رواه حدث حدثنا اخبرنا اخبر سمع اسناد سند متن صحيح حسن ضعيف "
                  "راوي رواة حديث سنه باب كتاب".split())
# wazn POS hints on the bare skeleton
WAZN = [
    ("masdar", re.compile(r"^است.{3}$|^ا.تعا.$|^ت.{2}ي.$|^ا.{2}ا.$")),
    ("ism_fa3il", re.compile(r"^.ا.[ةي]?$|^م.{2,3}$")),
    ("ism_maf3ul", re.compile(r"^م.{2}و.$")),
    ("verb_form_x", re.compile(r"^است.{3,}")),
    ("verb_derived", re.compile(r"^ت.{3,}|^ان.{3,}|^ا.ت.{2,}")),
]


def weak_tie(skel_letters, root_letters):
    """STRICT recovery: every root letter must match a skeleton letter in order (NO elision).
    A weak root letter may match any weak surface reflex (ا/ى/و/ي/ء seats); a non-weak letter
    must match exactly. Plus a length guard: the skeleton may exceed the root by at most 2
    (short derived-form augments) and never be shorter. Requires >=2 non-weak anchors. This is
    a precise candidate proposal, never a certification — a human/QAC confirms the root."""
    nonweak = [l for l in root_letters if l not in _WEAK]
    if len(nonweak) < 2:
        return False
    if not (0 <= len(skel_letters) - len(root_letters) <= 2):
        return False
    i = 0
    for rl in root_letters:
        matched = False
        while i < len(skel_letters):
            sc = skel_letters[i]
            i += 1
            if (rl in _WEAK and sc in _WEAK) or (rl not in _WEAK and sc == rl):
                matched = True
                break
        if not matched:
            return False
    return True


def pos_guess(bare):
    for name, pat in WAZN:
        if pat.match(bare):
            return name
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="qamus/indexes/existing_qamus_index.json")
    ap.add_argument("--diff", default="corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl")
    ap.add_argument("--out", default="corpora/nawawi40/out/nawawi40.diff_refined.jsonl")
    a = ap.parse_args()

    index = json.load(open(a.index, encoding="utf-8"))
    # weak-INCLUSIVE root letter sets (the conservative pass excluded these)
    weak_roots = []
    qamus_root_bares = set()
    for addr, r in index.items():
        root = (r.get("root") or "").replace(" ", "")
        if root:
            rb = N.bare(root)
            qamus_root_bares.add(rb)
            letters = [c for c in rb if c.strip()]
            if 3 <= len(letters) <= 4 and any(l in _WEAK for l in letters):
                weak_roots.append((letters, addr, r.get("root")))

    before = collections.Counter()
    after = collections.Counter()
    recovered = 0
    rows = []
    for line in open(a.diff, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        before[rec["classification"]] += 1
        bucket = rec["classification"]
        bare = rec.get("bare") or N.bare(rec["surface_ar"])
        skel_letters = [c for c in bare if c.strip()]
        rec["pos_guess"] = pos_guess(bare)
        rec["hadith_technical"] = bare in HADITH_TECH or any(
            t in HADITH_TECH for t in (rec.get("norm", ""), bare))

        # Weak-root HINT only — NOT a re-bucket. Subsequence-matching against weak roots was
        # measured at ~50% precision (وَمَنْ→أمن, هُرَيْرَةَ→هور were spurious), so we DO NOT assert
        # a root or change the classification: the conservative diff was right to defer these.
        # We flag a candidate hint for the human/QAC reviewer to confirm or reject.
        if bucket in ("new_root_or_unknown_root", "uncertain_needs_review"):
            hints = []
            for letters, addr, root in weak_roots:
                if weak_tie(skel_letters, letters):
                    hints.append(root)
                    if len(hints) >= 3:
                        break
            if hints:
                rec["weak_root_hint"] = hints
                rec["weak_root_hint_confidence"] = ("low — UNCONFIRMED; ~half of sampled ties were "
                                                    "spurious; QAC/human must confirm the root")
                recovered += 1

        # Fusha-learning priority + Ṣaḥīḥayn recurrence likelihood (classification unchanged)
        root_known = bucket in (
            "already_in_qamus", "new_surface_for_existing_lemma", "new_lemma_existing_root")
        freq = rec.get("frequency") or 0
        rec["priority"] = ("high" if (root_known and freq >= 2) else
                           "medium" if root_known or freq >= 2 else "low")
        rec["recurs_likely_sahihayn"] = bool(rec["hadith_technical"]) or freq >= 3

        rec["classification_refined"] = bucket
        rec["refined_by"] = "nawawi40-refine/1"
        after[bucket] += 1
        rows.append(rec)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "total": sum(before.values()),
        "classification": dict(before),
        "note": ("classification is UNCHANGED from the conservative diff — automated weak-root "
                 "tying measured ~50% precision, so it is NOT used to re-bucket or assert roots; "
                 "it only adds reviewer signals."),
        "weak_root_hints_flagged": recovered,
        "weak_root_hint_precision_note": "low/unconfirmed — QAC or human confirms each",
        "pos_guess": dict(collections.Counter(r["pos_guess"] for r in rows)),
        "priority": dict(collections.Counter(r["priority"] for r in rows)),
        "hadith_technical": sum(1 for r in rows if r["hadith_technical"]),
        "recurs_likely_sahihayn": sum(1 for r in rows if r["recurs_likely_sahihayn"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    with open(os.path.join(os.path.dirname(a.out), "nawawi40.refine_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


if __name__ == "__main__":
    main()
