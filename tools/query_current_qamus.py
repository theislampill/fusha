#!/usr/bin/env python3
"""Offline query tool for the committed public-safe Qamus dataset.

Works from the public repo with NO live server access. Loads the committed indexes
and entries.jsonl, answers the common lookups an agent (Claude/Codex) needs when
authoring entries, hover glosses, or corpus->Qamus candidates.

Examples:
  python3 tools/query_current_qamus.py --id c59a0161fac8
  python3 tools/query_current_qamus.py --root "أ م ن"
  python3 tools/query_current_qamus.py --lemma آمَنَ
  python3 tools/query_current_qamus.py --surface اعمالنا        # norm_strict join (hover key)
  python3 tools/query_current_qamus.py --ref 2:13               # entries citing this ayah
  python3 tools/query_current_qamus.py --section particle --limit 5
  python3 tools/query_current_qamus.py --stats
"""
import argparse, json, os, sys, unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Arabic-safe on Windows consoles
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current")
IDX = os.path.join(ROOT, "qamus", "indexes", "current")

def norm_strict(s):
    if not s: return ""
    s = unicodedata.normalize("NFC", s).replace("ىٰ", "ى")
    out=[]
    for ch in s:
        o=ord(ch)
        if 0x064B<=o<=0x0652: continue
        if o==0x0670: out.append("ا"); continue
        if o==0x0640: continue
        if 0x0653<=o<=0x0655: continue
        if 0x06D6<=o<=0x06ED: continue
        out.append(ch)
    s="".join(out).replace("آ","ا").replace("ٱ","ا").replace("ى","ي").replace("ة","ه").replace(" ","")
    return s

_ENTRIES=None
def load_entries():
    global _ENTRIES
    if _ENTRIES is None:
        _ENTRIES={}
        with open(os.path.join(DATA,"entries.jsonl"),encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if line:
                    e=json.loads(line); _ENTRIES[e["id"]]=e
    return _ENTRIES

def jidx(name):
    return json.load(open(os.path.join(IDX,name+".json"),encoding="utf-8"))

def show(eid, full=False):
    e=load_entries().get(eid)
    if not e: return {"id":eid,"error":"not found"}
    if full: return e
    return {"id":e["id"],"headword":e.get("headword"),"root":e.get("root"),
            "section":e.get("section"),"definition":e.get("definition"),
            "senses":[s.get("gloss") for s in e.get("senses",[])],
            "n_examples":sum(len(u.get("examples",[])) for u in e.get("usage",[]))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--id"); ap.add_argument("--root"); ap.add_argument("--lemma")
    ap.add_argument("--surface"); ap.add_argument("--ref"); ap.add_argument("--source-key")
    ap.add_argument("--section"); ap.add_argument("--limit",type=int,default=20)
    ap.add_argument("--full",action="store_true"); ap.add_argument("--stats",action="store_true")
    a=ap.parse_args()
    out=None
    if a.stats:
        man=json.load(open(os.path.join(DATA,"entry-manifest.json"),encoding="utf-8"))
        out=man
    elif a.id:
        out=show(a.id,a.full)
    elif a.root:
        ids=jidx("by-root").get(a.root,[])
        out={"root":a.root,"count":len(ids),"entries":[show(i) for i in ids[:a.limit]]}
    elif a.lemma:
        ids=jidx("by-lemma").get(a.lemma,[])
        out={"lemma":a.lemma,"entries":[show(i,a.full) for i in ids[:a.limit]]}
    elif a.surface:
        key=norm_strict(a.surface)
        ids=jidx("by-normalized-surface").get(key,[])
        out={"surface":a.surface,"norm_strict":key,"count":len(ids),
             "entries":[show(i,a.full) for i in ids[:a.limit]]}
    elif a.ref:
        ids=jidx("by-quran-ref").get(a.ref,[])
        out={"ref":a.ref,"count":len(ids),"entries":[show(i) for i in ids[:a.limit]]}
    elif a.source_key:
        ids=jidx("by-source-key").get(a.source_key,[])
        out={"source_key":a.source_key,"entries":[show(i) for i in ids[:a.limit]]}
    elif a.section:
        bc=jidx("by-category")["by_section"].get(a.section,[])
        out={"section":a.section,"count":len(bc),"entries":[show(i) for i in bc[:a.limit]]}
    else:
        ap.print_help(); sys.exit(1)
    print(json.dumps(out,ensure_ascii=False,indent=1))

if __name__=="__main__":
    main()
