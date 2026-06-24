#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B2 candidate generator — host-lexeme decision requests for suffix/pronoun blockers.

The complement of build_suffix_pronoun_candidates.py: a possessed token (noun stem + possessive
enclitic) whose HOST stem is NOT in the Qamus dataset (stem_base_unknown). The verifier authors the
host noun's base gloss from sarf/nahw knowledge + QAC root (Qurʾānic nouns) and composes
"<possessor> <base>", or exact-blocks. Auto-applies NOTHING.

POS-gated (noun host only — a verb host's enclitic is subject/object, never possessive).
Tanwīn-alef guard (ـًا is not the pronoun نا).

Row: loc, surface, host_stem, suffix, possessor, person, number, ayah_text, qac_root, qac_pos.
Env: QAMUS_WBW_SERVICES, QAMUS_WBW_ARTIFACT, QAMUS_DATASET.
"""
import argparse, json, os, re, sys, collections
sys.path.insert(0, os.environ.get("QAMUS_WBW_SERVICES", "services"))
from qamus_wbw import expand as X
from qamus_wbw import normalize as N

DIAC = re.compile(r"[ً-ْٰـۖ-ۭ]")
def bare(s): return DIAC.sub("", (s or "")).replace("ٱ", "ا")
TANWIN_ALEF = re.compile(r"ً[ۖ-ۭ]*ا$")
# Only UNAMBIGUOUS multi-letter enclitics — bare ه/ك/ي collide with root radicals and
# preposition+pronoun (لَهُ "for him"), producing false splits. Multi-letter ones are reliable.
ENC = [("كُمَا","كما","your (you two)","2","dual"),("هُمَا","هما","their (those two)","3","dual"),
       ("كُمْ","كم","your","2","plural"),("كُنَّ","كن","your","2","plural-f"),
       ("هُمْ","هم","their","3","plural"),("هِمْ","هم","their","3","plural"),
       ("هُنَّ","هن","their","3","plural-f"),("هِنَّ","هن","their","3","plural-f"),
       ("نَا","نا","our","1","plural"),("هَا","ها","her","3","singular-f")]
# host stems that are actually preposition/particle + pronoun (not possessed nouns) — exclude
PARTICLE_HOSTS = {"ل","فل","ول","بل","عل","ال","ا","و","ف","وأ","فأ","أن","وأن","فأن","لأن","عن","من","ومن","فمن","ان","لكن"}

def split_enc(tok):
    if TANWIN_ALEF.search(tok or ""): return None  # tanwīn-alef is not the pronoun نا
    b = bare(tok)
    for vf, bs, poss, person, number in ENC:
        if b.endswith(bs) and len(b) > len(bs) + 2:  # host >= 3 letters
            host = b[:-len(bs)]
            if host.lstrip("وفبكل") in PARTICLE_HOSTS or host in PARTICLE_HOSTS:
                return None
            return host, bs, poss, person, number
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--dataset", default=os.environ.get("QAMUS_DATASET", "/tmp/entries.jsonl"))
    ap.add_argument("--out", required=True); ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args()
    d = json.load(open(a.artifact, encoding="utf-8")); verses, words = d["verses"], d["words"]
    X._load_qac_roots(); qpos = X._QAC_CACHE.get("pos", {}); qroot = X._QAC_CACHE.get("root", {})

    ds_keys = set()
    for line in open(a.dataset, encoding="utf-8"):
        e = json.loads(line)
        ds_keys.add(N.norm_strict(e.get("headword", "")))
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                for t in re.findall(r"[؀-ۿ]+", fstr): ds_keys.add(N.norm_strict(t))

    rows, seen_stem = [], collections.Counter()
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            if loc in words: continue
            sp = split_enc(tok)
            if not sp: continue
            stem, bs, poss, person, number = sp
            pos = qpos.get((ref, N.norm_strict(tok)))
            if pos == "V": continue  # POS-gate: verb host enclitic is subject/object
            s = bare(stem)
            # try stripping proclitics (و ف ب ك ل) and the article before the dataset check
            sp2 = s.lstrip("وفبكل")
            keys = {s, sp2,
                    s[2:] if s.startswith("ال") else s, sp2[2:] if sp2.startswith("ال") else sp2}
            keys = {k for k in keys if k and len(k) >= 2}
            if any(k in ds_keys for k in keys): continue  # has a dataset host -> handled by suffix lane
            qr = qroot.get((ref, N.norm_strict(tok)))
            rows.append({"loc": loc, "surface": tok, "host_stem": stem, "suffix": bs,
                         "possessor": poss, "person": person, "number": number,
                         "qac_root": qr, "qac_pos": pos, "ayah_text": " ".join(toks)})
            seen_stem[s] += 1
    # diversity: cap per host stem so many distinct lexemes are represented
    by_stem = collections.defaultdict(list)
    for r in rows: by_stem[bare(r["host_stem"])].append(r)
    sel = []
    for st in sorted(by_stem, key=lambda k: -len(by_stem[k])):
        sel.extend(by_stem[st][:3])
    sel = sel[:a.max]
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in sel: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"requests": len(sel), "distinct_host_stems": len(by_stem)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
