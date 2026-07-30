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

The host-POS and forbidden-attachment judgments are read from nahw/rules/pronoun-attachment-rules.json through
tools/fusha_nahw_context_rules (A2 wiring, GAP-N3): that rule file used to be existence-checked only, so editing
it changed nothing. Now a wrong attachment table breaks this test.

Fails closed (exit 1) on any violation.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
EVAL = os.path.join(ROOT, "nahw", "evals", "suffix-pronoun-eval.jsonl")

from tools import fusha_nahw_context_rules as CTX  # noqa: E402

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
        # 0. the rule file decides what an enclitic IS, by host POS (nahw/rules/pronoun-attachment-rules.json)
        role = CTX.attachment_role(host)
        if host in ("N", "V", "P") and not role:
            fails.append(f"{sid}: pronoun-attachment-rules.json has no attachment entry for host {host}")
        if host == "V" and "NOT possessive" not in role:
            fails.append(f"{sid}: the verb-host rule no longer forbids a possessive reading ({role!r})")
        # 1. tanwīn-alef guard
        if st == "not_a_suffix":
            if not is_tanwin_alef(surf):
                fails.append(f"{sid}: expected tanwīn-alef guard to fire on {surf} (not the نا pronoun)")
            if CTX.is_forbidden_attachment(surf, "نا", host) is None:
                fails.append(f"{sid}: pronoun-attachment-rules forbidden table did not fire on {surf}")
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
            if CTX.is_forbidden_attachment(surf, suf, host) is not None:
                fails.append(f"{sid}: a valid possessive tripped the forbidden-attachment table")
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
    # ROUND-7 negative gate: the verb-host نا prohibition must be LOAD-BEARING. Removing or weakening the
    # rule row must make this test fail, so the guard can never quietly disappear from
    # nahw/rules/pronoun-attachment-rules.json. The rule data is mutated IN MEMORY only.
    import copy as _copy

    if CTX.is_forbidden_attachment("عَلِمْنَا", "نا", "V") is None:
        fails.append("verb-host نا is not forbidden: a verb enclitic may never be read as possessive")
    _weak = _copy.deepcopy(CTX.load_pronoun_attachment_rules())
    _weak["forbidden"] = [f for f in _weak.get("forbidden", [])
                          if not f.startswith("treat verb-subject")]
    if CTX.is_forbidden_attachment("عَلِمْنَا", "نا", "V", rules=_weak) is not None:
        fails.append("the verb-host نا guard fired even with its rule row removed (hard-coded, not consumed)")
    _blunt = _copy.deepcopy(CTX.load_pronoun_attachment_rules())
    _blunt["attachment"]["verb_host"] = "possessive (our X)"
    if "NOT possessive" in CTX.attachment_role("V", rules=_blunt):
        fails.append("attachment_role ignored a weakened verb_host rule (hard-coded, not consumed)")

    # the rule file's two-vote triggers must survive (an ambiguous host POS is never auto-decided)
    triggers = CTX.attachment_two_vote_triggers()
    if not any("ambiguous host" in t for t in triggers):
        fails.append("pronoun-attachment-rules.json no longer routes an ambiguous host POS to two-vote")
    if not any("referent" in t for t in triggers):
        fails.append("pronoun-attachment-rules.json no longer routes a referent-sensitive pronoun to two-vote")

    print(f"suffix-pronoun eval: {len(cases)} cases; classes={sorted(seen_classes)}")
    if fails:
        print("FAIL:")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("PASS - tanwin-alef guard, verb-exclusion, homograph-rejection, preposition-phrase, and all named possessive classes hold")

if __name__ == "__main__":
    main()
