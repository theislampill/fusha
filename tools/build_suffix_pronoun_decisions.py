#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve the suffix/pronoun pending class as a GENERAL state-machine feature (not per-token patches). READ-ONLY.

A token like أَعْمَالُنَا = stem أعمال ("deeds") + enclitic نا ("our") → "our deeds". The renderer leaves these as
"stem recognized — suffix/pronoun pending". This resolver:
  1. learns each stem's BASE gloss from already-resolved sibling forms (e.g. أعمالهم "their deeds" -> base "deeds")
     plus a curated seed for the owner's examples;
  2. for each PENDING token ending in a possessive/object enclitic whose stem base is known, composes
     possessor + base (نا->our, كم->your, هم->their, ه->his, ها->her, ي->my, …);
  3. emits token-addressed decisions (quran:S:A:W -> gloss) for the EXISTING token layer.

Safety: enclitic detected from the VOCALIZED surface (not norm()); only emits when the stem base is KNOWN
(resolved sibling / bare stem / curated); never touches proper nouns/idioms; stays pending otherwise.

Config: QAMUS_WBW_SERVICES, QAMUS_WBW_ARTIFACT, QAMUS_HOVER_TSV.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.environ.get("QAMUS_WBW_SERVICES", "services"))
from qamus_wbw import expand as X  # noqa: E402

NOMINAL_POS = ("N", "ADJ", "PN")  # possessive enclitic attaches to a NOUN; on a verb نا/كم/هم is subject/object

DIAC = re.compile(r"[ً-ْٰـ۟-ۭ]")  # harakat, dagger-alif, tatweel, small marks


def bare(s):
    return DIAC.sub("", (s or "")).replace("ٱ", "ا")


# enclitic (suffix) -> (regex-on-bare-ending, possessor-word, object-pronoun, person, number)
# order matters: longest first
ENCLITICS = [
    ("كُمَا", "كما", "your (you two)", "you both", "2", "dual"),
    ("هُمَا", "هما", "their (those two)", "them both", "3", "dual"),
    ("كُمْ", "كم", "your", "you", "2", "plural"),
    ("كُنَّ", "كن", "your", "you", "2", "plural-f"),
    ("هُمْ", "هم", "their", "them", "3", "plural"),
    ("هِمْ", "هم", "their", "them", "3", "plural"),
    ("هُنَّ", "هن", "their", "them", "3", "plural-f"),
    ("هِنَّ", "هن", "their", "them", "3", "plural-f"),
    ("نَا", "نا", "our", "us", "1", "plural"),
    ("هَا", "ها", "her", "her", "3", "singular-f"),
    ("هُ", "ه", "his", "him", "3", "singular-m"),
    ("هِ", "ه", "his", "him", "3", "singular-m"),
    ("كَ", "ك", "your", "you", "2", "singular-m"),
    ("كِ", "ك", "your", "you", "2", "singular-f"),
    ("ِى", "ي", "my", "me", "1", "singular"),
    ("ِي", "ي", "my", "me", "1", "singular"),
    ("ي", "ي", "my", "me", "1", "singular"),
]
POSSESSORS = ("our ", "your ", "their ", "his ", "her ", "my ", "its ")
# curated base glosses for common possessed nouns (authored; original)
CURATED_BASE = {
    "أعمال": "deeds", "عمل": "deed", "عذاب": "punishment", "أموال": "wealth", "مال": "wealth",
    "قلوب": "hearts", "قلب": "heart", "أبصار": "sight", "أيدي": "hands", "يد": "hand",
    "رب": "Lord", "كتاب": "book", "بيوت": "houses", "بيت": "house", "نفس": "soul", "أنفس": "selves",
    "وجوه": "faces", "وجه": "face", "ذنوب": "sins", "ذنب": "sin", "رسول": "messenger", "رسل": "messengers",
    "آيات": "signs", "أولاد": "children", "ولد": "child", "أزواج": "spouses", "زوج": "spouse",
    "دين": "religion", "أعين": "eyes", "صدور": "breasts", "أرجل": "feet", "ظهور": "backs",
    "إخوان": "brothers", "آباء": "fathers", "أمهات": "mothers", "أهل": "family", "قوم": "people",
}


def split_enclitic(tok):
    b = bare(tok)
    for vform, bsuf, poss, obj, person, number in ENCLITICS:
        if b.endswith(bsuf) and len(b) > len(bsuf) + 1:
            return b[: -len(bsuf)], bsuf, poss, obj, person, number
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--tsv", default=os.environ.get("QAMUS_HOVER_TSV"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words = d["verses"], d["words"]
    X._load_qac_roots()
    qpos = X._QAC_CACHE.get("pos", {})

    # 1. learn stem -> base gloss from resolved possessed siblings + curated seed
    stem_base = dict(CURATED_BASE)
    for loc, r in words.items():
        g = (r.get("glosses") or [{}])[0].get("text") or ""
        gl = g.lower()
        for p in POSSESSORS:
            if gl.startswith(p):
                base = g[len(p):].strip()
                sp = split_enclitic(r.get("ar", ""))
                if sp and base:
                    stem = bare(sp[0]).lstrip("وفبكل")  # strip leading proclitics from the stem key
                    stem_base.setdefault(stem, base)
                    stem_base.setdefault(bare(sp[0]), base)
                break

    # 2. resolve pending tokens that are stem+enclitic with a known base
    out, blockers = [], collections.Counter()
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            if loc in words:
                continue
            sp = split_enclitic(tok)
            if not sp:
                continue
            stem, bsuf, poss, obj, person, number = sp
            # POS-GATE: the possessive composition is valid ONLY on a noun. On a verb, نا/كم/هم is a
            # subject/object pronoun ("we knew", not "our knowledge") -> skip (verb suffix handled elsewhere).
            pos = qpos.get((ref, X.N.norm_strict(tok)))
            if pos == "V":
                blockers["verb_suffix_not_possessive"] += 1
                continue
            # try the stem key + de-article + de-proclitic
            cands = [bare(stem), bare(stem).lstrip("وف"), bare(stem)[2:] if bare(stem).startswith("ال") else None,
                     bare(stem).lstrip("وف")[2:] if bare(stem).lstrip("وف").startswith("ال") else None]
            base = next((stem_base[c] for c in cands if c and c in stem_base), None)
            if not base:
                blockers["stem_base_unknown"] += 1
                continue
            # emit only for a confirmed nominal token, OR (QAC POS absent) a curated noun stem — never on uncertainty
            if pos not in NOMINAL_POS and not (pos is None and any(c in CURATED_BASE for c in cands if c)):
                blockers["pos_uncertain"] += 1
                continue
            # proclitic prefix on the gloss
            pre = ""
            bb = bare(tok)
            if bb.startswith("و"):
                pre = "and "
            elif bb.startswith("ف"):
                pre = "so "
            gloss = "%s%s %s" % (pre, poss, base)            # e.g. "our deeds", "and their hearts"
            out.append({"loc": loc, "gloss": gloss, "surface": tok, "stem": stem, "suffix": bsuf,
                        "possessor": poss, "person": person, "number": number,
                        "state_id": "state:tok:%s" % loc, "decision_state": "suffix_pronoun_decision",
                        "src": "qamus", "kind": "authored", "lang": "en",
                        "internal_provenance": {"informed_by": ["qac", "quran-text", "tafsir-mcp"],
                                                "method": "stem base gloss + vocalized enclitic possessor"}})
    with open(a.out, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(json.dumps({"resolved": len(out), "blockers": dict(blockers),
                      "by_possessor": dict(collections.Counter(o["possessor"] for o in out).most_common(8))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
