#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline regression test for the suffix/pronoun lane invariants (no server/QAC needed).

Exercises the eval bank nahw/evals/suffix-pronoun-eval.jsonl against the load-bearing guards the
live resolver enforces:
  - tanwīn-alef (ـًا) is NOT the pronoun نا  (قُرْءَانًا, بُنْيَٰنًا → not_a_suffix)
  - a verb host's enclitic is subject/object, never possessive (عَلِمْنَا ≠ "our knowledge")
  - a norm_strict homograph must not borrow a wrong lemma (ذِكْر ≠ ذَكَر)
  - a preposition+pronoun is a phrase, not a possessed noun (فَمِنكُم = "from you")
  - a verb+object suffix enters explicit object-pronoun review, not possessive completion
  - valid possessives compose <possessor> <base> with the right enclitic
Fails closed (exit 1) on any violation.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(ROOT, "nahw", "evals", "suffix-pronoun-eval.jsonl")

DIAC = re.compile(r"[ً-ْٰـۖ-ۭ]")
def bare(s): return DIAC.sub("", (s or "")).replace("ٱ", "ا")
# tanwīn-fatḥ (ً U+064B) immediately before a final alef (possibly with small marks) = tanwīn-alef, not نا
TANWIN_ALEF = re.compile(r"ً[ۖ-ۭ]*ا$")

ENC = {"كما","هما","كم","كن","هم","هن","نا","ها","ه","ك","ي"}
POSS = {
    "نا": ("our",),
    "كم": ("your",),
    "هم": ("their",),
    "ه": ("his", "its"),
    "ها": ("her", "its"),
    "ك": ("your",),
    "ي": ("my",),
    "هما": ("their",),
    "كما": ("your",),
    "هن": ("their",),
    "كن": ("your",),
}

def is_tanwin_alef(surface):
    return bool(TANWIN_ALEF.search(surface or ""))

def main():
    cases = [json.loads(l) for l in open(EVAL, encoding="utf-8") if l.strip()]
    fails = []
    seen_classes = set()
    for c in cases:
        sid, surf, st = c["id"], c["surface"], c["expect_state"]
        host = c.get("host_pos")
        seen_classes.add(st)
        # 1. tanwīn-alef guard
        if st == "not_a_suffix":
            if not is_tanwin_alef(surf):
                fails.append(f"{sid}: expected tanwīn-alef guard to fire on {surf} (not the نا pronoun)")
            continue
        # 2. valid possessive must be a real enclitic on a noun and NOT tanwīn-alef
        if st == "suffix_pronoun_decision":
            if is_tanwin_alef(surf):
                fails.append(f"{sid}: {surf} is tanwīn-alef, must not be a possessive")
            if host != "N":
                fails.append(f"{sid}: possessive composed on non-noun host {host}")
            suf = c.get("suffix")
            if suf not in ENC:
                fails.append(f"{sid}: suffix {suf} not a recognized enclitic")
            poss = POSS.get(suf, ())
            eg = (c.get("expect_gloss") or "")
            # gloss must start with the possessor word (allowing 'and '/'so ' proclitic)
            core = eg.replace("and ", "").replace("so ", "")
            if poss and core and not any(core.startswith(p) for p in poss):
                fails.append(f"{sid}: gloss '{eg}' does not start with one of {poss}")
            continue
        # 2b. verb host with object suffix: explicit review state, never possessive
        if st == "verb_object_pronoun_review":
            if host != "V":
                fails.append(f"{sid}: verb object review composed on non-verb host {host}")
            if c.get("expect_gloss") is not None:
                fails.append(f"{sid}: verb object review must keep null gloss until token hover is certified")
            suf = c.get("suffix")
            if suf not in ENC:
                fails.append(f"{sid}: suffix {suf} not a recognized enclitic")
            continue
        # 3. verb host → never possessive
        if st == "pending" and host == "V":
            if c.get("expect_gloss") is not None:
                fails.append(f"{sid}: verb host {surf} must have null gloss (subject, not possessive)")
            continue
        # 4. homograph rejection
        if st == "rejected_homograph":
            if c.get("expect_gloss") is not None:
                fails.append(f"{sid}: rejected homograph {surf} must have null gloss")
            continue
        # 5. preposition+pronoun is a phrase, not a possessed noun
        if st == "preposition_pronoun":
            if host == "N":
                fails.append(f"{sid}: preposition case wrongly tagged noun host")
            continue
        fails.append(f"{sid}: unknown expect_state {st}")

    # coverage assertions: the user-named classes must be present
    surfaces = {c["surface"] for c in cases}
    need = ["أَعْمَالُنَا","أَعْمَالُكُمْ","أَعْمَالَهُمْ","رَبِّكُمْ","كِتَابَهُمْ","قُلُوبِهِمْ","أَمْوَالَهُمْ","أَيْدِيهِمْ"]
    for s in need:
        if s not in surfaces:
            fails.append(f"missing named class: {s}")
    # required negative classes
    for need_state in ("pending","not_a_suffix","rejected_homograph","verb_object_pronoun_review"):
        if need_state not in seen_classes:
            fails.append(f"missing required negative class: {need_state}")

    print(f"suffix-pronoun eval: {len(cases)} cases; classes={sorted(seen_classes)}")
    if fails:
        print("FAIL:")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("PASS - tanwin-alef guard, verb-exclusion, homograph-rejection, preposition-phrase, and all named possessive classes hold")

if __name__ == "__main__":
    main()
