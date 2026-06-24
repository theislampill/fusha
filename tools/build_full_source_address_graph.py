#!/usr/bin/env python3
"""P1 — Project-Xanadu full source-address graph (read-only, from committed artifacts).

Builds the COMPLETE address graph over the committed public-safe dataset (P0) + the full
hover-token audit (P3) + the token-decision layer + repair candidates + source-photo
verification. Every Qamus entry, field, usage āyah, hover token, decision, repair, and
source-photo locator gets a stable address; links are bidirectional; 0 orphans.

Address families:
  qamus:<id>                         entry
  qamus:<id>#field=<path>            entry field (root, headword, senses[i].gloss, forms, ...)
  qamus:<id>#usage=<S:A>             entry's cited āyah
  qamus:<id>#source_key=<sk>         source-scope tie
  quran:<S:A>  quran:<S:A:W>         āyah / token
  wbw:<S:A:W>#artifact=<sha>         hover artifact token
  decision:<state_id>                token decision
  repair:<batch>#<addr>              repair candidate
  source-photo:<locator>#entry=<sk>  source-photo locator

Inputs (committed unless noted):
  qamus/data/current/entries.jsonl, qamus/indexes/current/*.json
  qamus/reports/hover-token-audit-full.jsonl
  out/hover_stage/fusha-hover-token-decisions.jsonl   (staged; reproducible)
  qamus/candidates/repairs/*.jsonl
  qamus/reports/source-photo-verified-samples.jsonl

Outputs:
  qamus/indexes/current/source-address-full.json
  qamus/indexes/current/decision-backlinks-full.json
  qamus/indexes/current/quran-usage-spine-full.json
  qamus/indexes/current/qamus-entry-field-addresses.json
  qamus/reports/xanadu-completion-report.md
  qamus/reports/source-address-usage-report.md
"""
import glob, json, os, sys, unicodedata
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT,"qamus","data","current")
IDX = os.path.join(ROOT,"qamus","indexes","current")
REPORTS = os.path.join(ROOT,"qamus","reports")
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT,"out","hover_stage"))
SOURCE_SHA = "65797d7d5599fadd"

def norm_strict(s):
    if not s: return ""
    s = unicodedata.normalize("NFC", s).replace("ىٰ","ى")
    out=[]
    for ch in s:
        o=ord(ch)
        if 0x064B<=o<=0x0652: continue
        if o==0x0670: out.append("ا"); continue
        if o==0x0640: continue
        if 0x0653<=o<=0x0655: continue
        if 0x06D6<=o<=0x06ED: continue
        out.append(ch)
    return "".join(out).replace("آ","ا").replace("ٱ","ا").replace("ى","ي").replace("ة","ه").replace(" ","")

def jload(p, default=None):
    if not os.path.exists(p): return default
    return json.load(open(p,encoding="utf-8"))

def jdump(o,p,**kw):
    with open(p,"w",encoding="utf-8") as f:
        json.dump(o,f,ensure_ascii=False,sort_keys=True,separators=(",",":"),**kw)

def main():
    entries = {}
    for line in open(os.path.join(DATA,"entries.jsonl"),encoding="utf-8"):
        line=line.strip()
        if line:
            e=json.loads(line); entries[e["id"]]=e
    by_ref = jload(os.path.join(IDX,"by-quran-ref.json"),{})
    by_root = jload(os.path.join(IDX,"by-root.json"),{})

    # audit rows -> token states
    audit = {}
    for line in open(os.path.join(REPORTS,"hover-token-audit-full.jsonl"),encoding="utf-8"):
        r=json.loads(line); audit[r["quran_loc"]]=r

    # token decisions
    decisions = {}
    dpath = os.path.join(STAGE,"fusha-hover-token-decisions.jsonl")
    if os.path.exists(dpath):
        for line in open(dpath,encoding="utf-8"):
            line=line.strip()
            if line:
                d=json.loads(line); decisions[d["loc"]]=d

    # repairs
    repairs = []
    for f in sorted(glob.glob(os.path.join(ROOT,"qamus","candidates","repairs","*.jsonl"))):
        batch=os.path.splitext(os.path.basename(f))[0]
        for line in open(f,encoding="utf-8"):
            line=line.strip()
            if line:
                try: rec=json.loads(line)
                except: continue
                rec["_batch"]=batch; repairs.append(rec)

    # source-photo verified
    photo_verified = {}  # source_key or entry_id -> info
    spf = os.path.join(REPORTS,"source-photo-verified-samples.jsonl")
    if os.path.exists(spf):
        for line in open(spf,encoding="utf-8"):
            line=line.strip()
            if line:
                try: rec=json.loads(line)
                except: continue
                k = rec.get("entry_id") or rec.get("source_key") or rec.get("headword")
                if k: photo_verified[k]=rec

    # ---- 1. source-address-full + field addresses ----
    addresses = {}        # address -> node
    field_addr = {}       # entry_id -> {field: {address, source_verified}}
    for eid,e in entries.items():
        a = f"qamus:{eid}"
        sks = e.get("source_keys") or []
        verified = any((sk in photo_verified) for sk in sks) or (eid in photo_verified)
        addresses[a] = {"type":"entry","headword":e.get("headword",""),"root":e.get("root",""),
                        "section":e.get("section",""),"source_keys":sks,
                        "n_examples":sum(len(u.get("examples",[])) for u in e.get("usage",[])),
                        "source_photo_verified":verified}
        fa = {}
        for fld in ("headword","root","translit","definition"):
            addr=f"qamus:{eid}#field={fld}"; addresses[addr]={"type":"field","entry":eid,"field":fld}
            fa[fld]={"address":addr,"source_verified":verified}
        for i,s in enumerate(e.get("senses",[])):
            addr=f"qamus:{eid}#field=senses[{i}].gloss"; addresses[addr]={"type":"field","entry":eid,"field":f"senses[{i}].gloss"}
            fa[f"senses[{i}].gloss"]={"address":addr,"source_verified":verified}
        for u in e.get("usage",[]):
            if u.get("forms"):
                addr=f"qamus:{eid}#field=usage[sense={u.get('sense')}].forms"; addresses[addr]={"type":"field","entry":eid,"field":"forms"}
        for sk in sks:
            addr=f"qamus:{eid}#source_key={sk}"; addresses[addr]={"type":"source_key","entry":eid,"source_key":sk}
            # source-photo locator
            pl = photo_verified.get(sk) or photo_verified.get(eid)
            page = (pl or {}).get("page") if pl else None
            sp=f"source-photo:{page or 'unlocated'}#entry={sk}"
            addresses[sp]={"type":"source_photo","entry":eid,"source_key":sk,
                           "page":page,"status":"verified" if pl else "locator_only"}
        seen=set()
        for u in e.get("usage",[]):
            for ex in u.get("examples",[]):
                sa=":".join(str(ex.get("ref","")).split(":")[:2])
                if sa and sa[0].isdigit() and sa not in seen:
                    addr=f"qamus:{eid}#usage={sa}"; addresses[addr]={"type":"usage","entry":eid,"ayah":sa}
                    seen.add(sa)
        field_addr[eid]=fa

    jdump({"schema":"fusha/source-address-full@1","source_sha":SOURCE_SHA,
           "address_count":len(addresses),"addresses":addresses},
          os.path.join(IDX,"source-address-full.json"))
    jdump({"schema":"fusha/qamus-entry-field-addresses@1","entry_count":len(field_addr),
           "entries":field_addr}, os.path.join(IDX,"qamus-entry-field-addresses.json"))

    # ---- 2. quran-usage-spine-full ----
    spine = {}
    for sa, wlist in sorted(((k,v) for k,v in (jload(os.path.join(STAGE,"wbw-lookup.json"),{}).get("verses",{})).items()),
                            key=lambda x:(int(x[0].split(":")[0]),int(x[0].split(":")[1]))):
        toks=[]
        res=pend=0
        for i,surf in enumerate(wlist,1):
            loc=f"{sa}:{i}"; ar=audit.get(loc,{})
            st=ar.get("decision_state","pending")
            if st=="resolved": res+=1
            else: pend+=1
            toks.append({"w":i,"state":st,"blocker":ar.get("blocker"),
                         "gloss":ar.get("public_gloss")})
        spine[sa]={"entries":by_ref.get(sa,[]),"n_tokens":len(wlist),
                   "resolved":res,"pending":pend,"tokens":toks}
    jdump({"schema":"fusha/quran-usage-spine-full@1","source_sha":SOURCE_SHA,
           "ayat":len(spine),"spine":spine}, os.path.join(IDX,"quran-usage-spine-full.json"))

    # ---- 3. decision-backlinks-full ----
    # decision -> entry_contexts ; homograph key -> resolved/pending locs ; blocker -> locs ;
    # repair -> entries+tokens ; procedure -> decisions
    backlinks = {"by_decision":{}, "by_homograph_key":{}, "by_blocker":defaultdict(list),
                 "by_repair":{}, "by_procedure":defaultdict(list)}
    key_resolved=defaultdict(list); key_pending=defaultdict(list)
    for loc,d in decisions.items():
        sa=":".join(loc.split(":")[:2])
        ec=by_ref.get(sa,[])
        proc = "suffix-pronoun-state/pronoun-attachment" if ("stem" in d and "suffix" in d) else "surface-state-transition/particle-state-split"
        backlinks["by_decision"][d.get("state_id",loc)]={
            "loc":loc,"surface":d.get("surface"),"gloss":d.get("gloss"),
            "entry_contexts":ec,"procedure":proc,
            "informed_by":(d.get("internal_provenance") or {}).get("informed_by")}
        backlinks["by_procedure"][proc].append(loc)
        if d.get("key"): key_resolved[d["key"]].append(loc)
    # pending ambig grouped by norm key (query #6/#7)
    for loc,ar in audit.items():
        if ar.get("decision_state")=="pending":
            backlinks["by_blocker"][ar["blocker"]].append(loc)
            if ar["blocker"]=="same_surface_polysemy_requires_i3rab":
                key_pending[norm_strict(ar.get("surface_ar",""))].append(loc)
    for k in set(list(key_resolved)+list(key_pending)):
        backlinks["by_homograph_key"][k]={"resolved":key_resolved.get(k,[]),
                                          "pending_ambiguous":key_pending.get(k,[])}
    for r in repairs:
        addr=r.get("source_address","?")
        # extract entry id from "live-entry:<id>#..." or "qamus:<id>#..."
        eid=None
        for pre in ("live-entry:","qamus:"):
            if str(addr).startswith(pre):
                eid=addr[len(pre):].split("#")[0]; break
        affected=[]
        if eid:
            for sa in {":".join(str(ex.get('ref','')).split(':')[:2]) for u in entries.get(eid,{}).get("usage",[]) for ex in u.get("examples",[])}:
                affected.append(f"quran:{sa}")
        backlinks["by_repair"][f"repair:{r.get('_batch')}#{addr}"]={
            "entry":eid,"field":addr,"certifiable":r.get("certifiable"),
            "status":r.get("status"),"blocker":r.get("blocker"),
            "affects_ayat":affected[:30],"n_affected_ayat":len(affected)}
    backlinks["by_blocker"]=dict(backlinks["by_blocker"])
    backlinks["by_procedure"]=dict(backlinks["by_procedure"])
    # trim blocker lists in the persisted graph (full lists live in P3 by-blocker report)
    for k in backlinks["by_blocker"]:
        backlinks["by_blocker"][k]={"count":len(backlinks["by_blocker"][k]),
                                    "sample":backlinks["by_blocker"][k][:25]}
    for k in backlinks["by_procedure"]:
        backlinks["by_procedure"][k]={"count":len(backlinks["by_procedure"][k]),
                                      "sample":backlinks["by_procedure"][k][:25]}
    jdump({"schema":"fusha/decision-backlinks-full@1","source_sha":SOURCE_SHA,
           **backlinks}, os.path.join(IDX,"decision-backlinks-full.json"))

    # ---- orphan check ----
    orphans=0
    for a,node in addresses.items():
        if node["type"] in ("field","usage","source_key","source_photo") and node.get("entry") not in entries:
            orphans+=1
    # spine entries must exist
    spine_orphans=sum(1 for v in spine.values() for eid in v["entries"] if eid not in entries)

    # ---- reports ----
    rep=[]
    rep.append("# Project-Xanadu source-address completion report\n")
    rep.append(f"source_sha `{SOURCE_SHA}` · entries {len(entries):,} · addresses **{len(addresses):,}** · "
               f"āyāt {len(spine):,} · decisions {len(decisions)} · repairs {len(repairs)}\n")
    rep.append(f"**Orphan links: {orphans+spine_orphans}** (address→entry {orphans}, spine→entry {spine_orphans}).\n")
    rep.append("## The 10 graph queries (all answerable; see query_source_address_graph.py)\n")
    qs=[
     "1. Which entry supports this hover word? → spine[S:A].entries + token gloss (query --token S:A:W)",
     "2. Which hover words depend on this entry? → query --entry <id> --dependents (āyāt→tokens)",
     "3. Which āyāt use this entry? → entry usage addresses qamus:<id>#usage=<S:A>",
     "4. Which source photo/page supports this entry? → source-photo:<locator>#entry=<sk>",
     "5. Which entries share this root? → by-root / query --root",
     "6. Which decisions were rejected because of this homograph? → by_homograph_key[key].pending_ambiguous",
     "7. Which pending words share this blocker? → by_blocker[blocker] (full list in P3 by-blocker)",
     "8. Which repairs affect which tokens? → by_repair[*].affects_ayat",
     "9. Which sarf/nahw rule was used for this decision? → by_decision[*].procedure",
     "10. Which entry fields remain source-unverified? → qamus-entry-field-addresses (source_verified=false)",
    ]
    rep+= [f"- {q}" for q in qs]
    nverif=sum(1 for e in entries for fa in [field_addr[e]] for f in fa if not fa[f]["source_verified"])
    nentry_verif=sum(1 for e in entries if addresses[f"qamus:{e}"]["source_photo_verified"])
    rep.append(f"\nEntries with a source-photo-verified field: {nentry_verif:,} / {len(entries):,} "
               f"(the rest carry `source-photo:unlocated#entry=<sk>` locators for P7).\n")
    open(os.path.join(REPORTS,"xanadu-completion-report.md"),"w",encoding="utf-8").write("\n".join(rep))

    usage=[]
    usage.append("# Source-address usage report\n")
    usage.append("How each address family is used to keep decisions de-duplicated and traceable.\n")
    usage.append(f"- entry addresses: {sum(1 for n in addresses.values() if n['type']=='entry'):,}")
    usage.append(f"- field addresses: {sum(1 for n in addresses.values() if n['type']=='field'):,}")
    usage.append(f"- usage(āyah) addresses: {sum(1 for n in addresses.values() if n['type']=='usage'):,}")
    usage.append(f"- source_key addresses: {sum(1 for n in addresses.values() if n['type']=='source_key'):,}")
    usage.append(f"- source-photo locators: {sum(1 for n in addresses.values() if n['type']=='source_photo'):,}")
    usage.append(f"- token decisions addressed: {len(decisions)}")
    usage.append(f"- homograph keys tracked: {len(backlinks['by_homograph_key'])}")
    usage.append(f"- repair addresses: {len(backlinks['by_repair'])}\n")
    open(os.path.join(REPORTS,"source-address-usage-report.md"),"w",encoding="utf-8").write("\n".join(usage))

    print(f"GRAPH OK addresses={len(addresses)} ayat={len(spine)} decisions={len(decisions)} "
          f"repairs={len(repairs)} orphans={orphans+spine_orphans}")
    print("address types:", dict(Counter(n['type'] for n in addresses.values())))
    print("homograph keys:", len(backlinks["by_homograph_key"]), "entry-verified:", nentry_verif)
    assert orphans+spine_orphans==0, "ORPHAN LINKS PRESENT"
    print("INVARIANT OK: 0 orphan links")

if __name__=="__main__":
    main()
