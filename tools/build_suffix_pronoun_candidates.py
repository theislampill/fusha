#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P4 candidate generator — dataset-sourced suffix/pronoun resolutions for verification.

Extends the suffix/pronoun resolver: for each PENDING token that is noun-stem + possessive
enclitic whose host lemma is a NOUN entry in the committed Qamus dataset (but had no resolved
sibling / curated base), emit a CANDIDATE with full context so a /fusha-sarf + /fusha-nahw
verifier can certify (POS noun? sense correct? number correct? possessive not subject/object?
referent-safe?) before any apply.

Auto-applies NOTHING. Output: candidates JSONL (loc, surface, stem, possessor, base_source,
base_gloss_singular, ayah_text, entry_senses, qac_pos). Read-only.

Env: QAMUS_WBW_SERVICES, QAMUS_WBW_ARTIFACT, QAMUS_DATASET (entries.jsonl).
"""
import argparse, json, os, re, sys, collections


def load_qamus_wbw():
    """Lazily load (expand, normalize) through the public-safe seam (tools/qamus_wbw_adapter).

    Call inside main()/first use, never at module top level, so imports + --help still work on a public clone
    (the private qamus_wbw package is not shipped). The guarded direct import below stays detectable by
    validate_public_runnability.py; on a clone it raises the adapter's actionable SystemExit (naming
    QAMUS_WBW_SERVICES) — never a bare ModuleNotFoundError."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # ensure tools/ on path for the adapter
    import qamus_wbw_adapter
    sd = qamus_wbw_adapter.services_dir()
    if sd and sd not in sys.path:
        sys.path.insert(0, sd)
    try:
        from qamus_wbw import expand as X  # noqa: E402  (intentional lazy, guarded import via the seam)
        from qamus_wbw import normalize as N  # noqa: E402
    except ModuleNotFoundError as exc:
        raise SystemExit("ERROR: " + (qamus_wbw_adapter._GUIDANCE % qamus_wbw_adapter.DEFAULT_ENV)) from exc
    return X, N


DIAC = re.compile(r"[ً-ْٰـۖ-ۭ]")
def bare(s): return DIAC.sub("", (s or "")).replace("ٱ", "ا")

ENC = [("كُمَا","كما","your (you two)","2","dual"),("هُمَا","هما","their (those two)","3","dual"),
       ("كُمْ","كم","your","2","plural"),("كُنَّ","كن","your","2","plural-f"),
       ("هُمْ","هم","their","3","plural"),("هِمْ","هم","their","3","plural"),
       ("هُنَّ","هن","their","3","plural-f"),("هِنَّ","هن","their","3","plural-f"),
       ("نَا","نا","our","1","plural"),("هَا","ها","her","3","singular-f"),
       ("هُ","ه","his","3","singular-m"),("هِ","ه","his","3","singular-m"),
       ("كَ","ك","your","2","singular-m"),("كِ","ك","your","2","singular-f"),
       ("ِى","ي","my","1","singular"),("ِي","ي","my","1","singular")]

CURATED = {"أعمال","عمل","عذاب","أموال","مال","قلوب","قلب","أبصار","أيدي","يد","رب","كتاب","بيوت","بيت",
           "نفس","أنفس","وجوه","وجه","ذنوب","ذنب","رسول","رسل","آيات","أولاد","ولد","أزواج","زوج","دين",
           "أعين","صدور","أرجل","ظهور","إخوان","آباء","أمهات","أهل","قوم"}
POSS = ("our ","your ","their ","his ","her ","my ","its ")

def split_enc(tok):
    b = bare(tok)
    for vf,bs,poss,person,number in ENC:
        if b.endswith(bs) and len(b) > len(bs)+1:
            return b[:-len(bs)], bs, poss, person, number
    return None

def clean_gloss(g):
    g = (g or "").strip()
    g = re.sub(r"^\((lit\.?,?\s*)?", "", g).strip("() ")
    return g.split(";")[0].split(",")[0].strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--dataset", default=os.environ.get("QAMUS_DATASET","/tmp/entries.jsonl"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    X, N = load_qamus_wbw()
    d = json.load(open(a.artifact, encoding="utf-8")); verses, words = d["verses"], d["words"]
    X._load_qac_roots(); qpos = X._QAC_CACHE.get("pos", {})

    ds_head = {}   # norm_strict(headword) -> (gloss, senses[], headword)
    ds_form = {}   # norm_strict(form) -> (gloss, senses[], headword)  [for plurals]
    for line in open(a.dataset, encoding="utf-8"):
        e = json.loads(line)
        if e.get("section") != "noun": continue
        senses = [{"gloss": s.get("gloss"), "ar": s.get("ar")} for s in e.get("senses",[])]
        base = clean_gloss(e.get("definition") or (e.get("senses") or [{}])[0].get("gloss",""))
        hk = N.norm_strict(e.get("headword",""))
        if hk: ds_head.setdefault(hk, (base, senses, e.get("headword")))
        for u in e.get("usage",[]):
            for fstr in (u.get("forms") or []):
                for t in re.findall(r"[؀-ۿ]+", fstr):
                    k = N.norm_strict(t)
                    if k and k != hk: ds_form.setdefault(k, (base, senses, e.get("headword")))
        for s in e.get("senses",[]):
            k = N.norm_strict(s.get("ar",""))
            if k and k != hk: ds_form.setdefault(k, (base, senses, e.get("headword")))

    # learned sibling/curated stem set (to skip what the live resolver already handles)
    stem_known = set(CURATED)
    for loc,r in words.items():
        g = (r.get("glosses") or [{}])[0].get("text") or ""
        for p in POSS:
            if g.lower().startswith(p):
                sp = split_enc(r.get("ar",""))
                if sp: stem_known.add(bare(sp[0]).lstrip("وفبكل")); stem_known.add(bare(sp[0]))
                break

    cands = []
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i+1)
            if loc in words: continue
            sp = split_enc(tok)
            if not sp: continue
            stem, bsuf, poss, person, number = sp
            pos = qpos.get((ref, N.norm_strict(tok)))
            if pos == "V": continue   # POS-gate: verb suffix is subject/object, not possessive
            s = bare(stem)
            keys = [s, s.lstrip("وف"), s[2:] if s.startswith("ال") else None,
                    s.lstrip("وف")[2:] if s.lstrip("وف").startswith("ال") else None]
            keys = [k for k in keys if k]
            if any(k in stem_known for k in keys): continue   # already resolved by live resolver
            hit = next(((k,"headword",ds_head[k]) for k in keys if k in ds_head), None) \
               or next(((k,"form",ds_form[k]) for k in keys if k in ds_form), None)
            if not hit: continue
            key, src, (base, senses, headword) = hit
            ayah_text = " ".join(toks)
            cands.append({"loc": loc, "surface": tok, "stem": stem, "suffix": bsuf,
                          "possessor": poss, "person": person, "number": number,
                          "base_source": src, "base_gloss_singular": base,
                          "host_headword": headword, "entry_senses": senses,
                          "qac_pos": pos, "ayah_text": ayah_text})
    with open(a.out, "w", encoding="utf-8") as f:
        for c in cands: f.write(json.dumps(c, ensure_ascii=False)+"\n")
    print(json.dumps({"candidates": len(cands),
                      "by_source": dict(collections.Counter(c["base_source"] for c in cands)),
                      "distinct_stems": len({bare(c["stem"]) for c in cands})}, ensure_ascii=False))

if __name__ == "__main__":
    main()
