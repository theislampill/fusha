#!/usr/bin/env python3
"""Query the full Project-Xanadu source-address graph — offline, from the committed repo.

Answers the 10 canonical graph queries with no live server access.

  python3 tools/query_source_address_graph.py --token 2:139:2        # Q1 entry supports this word
  python3 tools/query_source_address_graph.py --entry b10a1ee04666 --dependents   # Q2 words depending on entry
  python3 tools/query_source_address_graph.py --entry b10a1ee04666 --ayat         # Q3 āyāt using entry
  python3 tools/query_source_address_graph.py --entry b10a1ee04666 --photo        # Q4 source photo/page
  python3 tools/query_source_address_graph.py --root "ع م ل"                       # Q5 entries sharing root
  python3 tools/query_source_address_graph.py --homograph لم                       # Q6 rejected-by-homograph
  python3 tools/query_source_address_graph.py --blocker stem_base_unknown          # Q7 pending sharing blocker
  python3 tools/query_source_address_graph.py --repairs                            # Q8 repairs->tokens
  python3 tools/query_source_address_graph.py --procedures                         # Q9 sarf/nahw rule usage
  python3 tools/query_source_address_graph.py --unverified-fields --limit 10       # Q10 source-unverified fields
"""
import argparse, json, os, sys, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT,"qamus","indexes","current")

def norm_strict(s):
    if not s: return ""
    s=unicodedata.normalize("NFC",s).replace("ىٰ","ى"); out=[]
    for ch in s:
        o=ord(ch)
        if 0x064B<=o<=0x0652: continue
        if o==0x0670: out.append("ا"); continue
        if o==0x0640: continue
        if 0x0653<=o<=0x0655: continue
        if 0x06D6<=o<=0x06ED: continue
        out.append(ch)
    return "".join(out).replace("آ","ا").replace("ٱ","ا").replace("ى","ي").replace("ة","ه").replace(" ","")

def L(name): return json.load(open(os.path.join(IDX,name),encoding="utf-8"))
def Lj(name, key):
    d={}
    for line in open(os.path.join(IDX,name),encoding="utf-8"):
        line=line.strip()
        if line:
            r=json.loads(line); d[r[key]]=r
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--token"); ap.add_argument("--entry"); ap.add_argument("--root")
    ap.add_argument("--homograph"); ap.add_argument("--blocker")
    ap.add_argument("--dependents",action="store_true"); ap.add_argument("--ayat",action="store_true")
    ap.add_argument("--photo",action="store_true"); ap.add_argument("--repairs",action="store_true")
    ap.add_argument("--procedures",action="store_true"); ap.add_argument("--unverified-fields",action="store_true")
    ap.add_argument("--limit",type=int,default=20)
    a=ap.parse_args(); out=None
    if a.token:  # Q1
        spine=Lj("quran-usage-spine-full.jsonl","ayah")
        sa=":".join(a.token.split(":")[:2]); w=int(a.token.split(":")[2])
        v=spine.get(sa,{}); tok=next((t for t in v.get("tokens",[]) if t["w"]==w),None)
        out={"token":a.token,"supporting_entries":v.get("entries",[]),"token_state":tok}
    elif a.entry and a.dependents:  # Q2
        sa_full=Lj("source-address-full.jsonl","address")
        spine=Lj("quran-usage-spine-full.jsonl","ayah")
        ayat=[k.split("#usage=")[1] for k in sa_full if k.startswith(f"qamus:{a.entry}#usage=")]
        deps=[]
        for sa in ayat:
            for t in spine.get(sa,{}).get("tokens",[]):
                if t["state"]=="resolved": deps.append({"loc":f"{sa}:{t['w']}","gloss":t["gloss"]})
        out={"entry":a.entry,"n_ayat":len(ayat),"dependent_resolved_tokens":len(deps),"sample":deps[:a.limit]}
    elif a.entry and a.ayat:  # Q3
        sa_full=Lj("source-address-full.jsonl","address")
        ayat=[k.split("#usage=")[1] for k in sa_full if k.startswith(f"qamus:{a.entry}#usage=")]
        out={"entry":a.entry,"ayat":sorted(ayat)}
    elif a.entry and a.photo:  # Q4
        sa_full=Lj("source-address-full.jsonl","address")
        sp=[{"address":k,**v} for k,v in sa_full.items() if k.startswith("source-photo:") and v.get("entry")==a.entry]
        out={"entry":a.entry,"source_photo":sp}
    elif a.entry:
        sa_full=Lj("source-address-full.jsonl","address")
        out={"entry":a.entry,"node":sa_full.get(f"qamus:{a.entry}")}
    elif a.root:  # Q5
        out={"root":a.root,"entries":L("by-root.json").get(a.root,[])}
    elif a.homograph:  # Q6
        bl=L("decision-backlinks-full.json")["by_homograph_key"]
        k=norm_strict(a.homograph)
        out={"homograph_key":k,"links":bl.get(k,{"resolved":[],"pending_ambiguous":[]})}
    elif a.blocker:  # Q7
        bl=L("decision-backlinks-full.json")["by_blocker"]
        out={"blocker":a.blocker,**bl.get(a.blocker,{"count":0,"sample":[]})}
    elif a.repairs:  # Q8
        out=L("decision-backlinks-full.json")["by_repair"]
        out={"repairs":{k:out[k] for k in list(out)[:a.limit]},"total":len(out)}
    elif a.procedures:  # Q9
        out={"procedures":L("decision-backlinks-full.json")["by_procedure"]}
    elif a.unverified_fields:  # Q10
        fa=Lj("qamus-entry-field-addresses.jsonl","entry_id")
        un=[]; total=0
        for eid in fa:
            for f,meta in fa[eid].get("fields",{}).items():
                if not meta["source_verified"]:
                    total+=1
                    if len(un)<a.limit: un.append(meta["address"])
        out={"unverified_field_count":total,"sample":un}
    else:
        ap.print_help(); sys.exit(1)
    print(json.dumps(out,ensure_ascii=False,indent=1))

if __name__=="__main__":
    main()
