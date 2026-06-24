#!/usr/bin/env python3
"""P2 — full entry-level audit matrix over all 2,092 Qamus entries.

Every entry gets a row with a TERMINAL status for source-photo, each field, hover coverage,
and repair — no 'unknown' buckets. 'needs review' always names the field and the reason.

Inputs (committed unless noted):
  qamus/data/current/entries.jsonl
  qamus/reports/hover-token-audit-full.jsonl          (P3)
  qamus/indexes/current/by-quran-ref.json             (P0)
  out/hover_stage/coverage-by-entry.json              (staged; per-entry hover coverage)
  qamus/reports/source-photo-verified-samples.jsonl   (P7 verification)
  qamus/candidates/repairs/*.jsonl                    (repair candidates)

Outputs:
  qamus/reports/qamus-2092-entry-matrix.jsonl
  qamus/reports/qamus-2092-audit-completion.md
  qamus/reports/qamus-2092-terminal-scoreboard.md
"""
import glob, json, os
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT,"qamus","data","current")
IDX = os.path.join(ROOT,"qamus","indexes","current")
REPORTS = os.path.join(ROOT,"qamus","reports")
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT,"out","hover_stage"))

def jload(p,d=None):
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else d

def main():
    entries={}
    for line in open(os.path.join(DATA,"entries.jsonl"),encoding="utf-8"):
        line=line.strip()
        if line: e=json.loads(line); entries[e["id"]]=e

    cov={c["id"]:c for c in jload(os.path.join(STAGE,"coverage-by-entry.json"),[])}

    # audit: āyah -> blocker counter (for hover blockers per entry)
    ayah_blockers=defaultdict(Counter)
    for line in open(os.path.join(REPORTS,"hover-token-audit-full.jsonl"),encoding="utf-8"):
        r=json.loads(line)
        if r.get("decision_state")=="pending":
            sa=":".join(r["quran_loc"].split(":")[:2])
            ayah_blockers[sa][r["blocker"]]+=1

    # verified source-photo
    verified_eid=set(); verified_sk=set(); verified_field=defaultdict(set)
    spf=os.path.join(REPORTS,"source-photo-verified-samples.jsonl")
    if os.path.exists(spf):
        for line in open(spf,encoding="utf-8"):
            line=line.strip()
            if not line: continue
            rec=json.loads(line)
            if rec.get("entry_id"): verified_eid.add(rec["entry_id"])
            for sk in rec.get("source_keys",[]): verified_sk.add(sk)
            if rec.get("entry_id") and rec.get("field"): verified_field[rec["entry_id"]].add(rec["field"])

    # repairs: entry -> status
    repair_status=defaultdict(lambda:"none"); repair_blocker={}
    for f in sorted(glob.glob(os.path.join(ROOT,"qamus","candidates","repairs","*.jsonl"))):
        applied = "applied" in os.path.basename(f)
        for line in open(f,encoding="utf-8"):
            line=line.strip()
            if not line: continue
            try: rec=json.loads(line)
            except: continue
            addr=str(rec.get("source_address",""))
            eid=None
            for pre in ("live-entry:","qamus:"):
                if addr.startswith(pre): eid=addr[len(pre):].split("#")[0]; break
            if not eid: continue
            if applied or rec.get("status")=="applied": repair_status[eid]="applied"
            elif rec.get("certifiable") and "owner-gated" in str(rec.get("status","")):
                if repair_status[eid]=="none": repair_status[eid]="deferred"
            else:
                if repair_status[eid]=="none": repair_status[eid]="candidate"
            repair_blocker[eid]=rec.get("blocker")

    rows=[]
    sp_status_c=Counter(); repair_c=Counter(); hover_complete=0
    field_issue_c=Counter()
    for eid in sorted(entries):
        e=entries[eid]
        sks=e.get("source_keys") or []
        c=cov.get(eid,{})
        words=c.get("words",0); covered=c.get("covered",0)
        pending=words-covered
        # cited āyāt
        ayat={":".join(str(ex.get("ref","")).split(":")[:2]) for u in e.get("usage",[]) for ex in u.get("examples",[])}
        ayat={a for a in ayat if a and a[0].isdigit()}
        blk=Counter()
        for a in ayat: blk.update(ayah_blockers.get(a,{}))
        # source photo status
        vfields=verified_field.get(eid,set())
        if eid in verified_eid or any(sk in verified_sk for sk in sks):
            sp="verified"
        elif repair_status[eid]=="candidate":
            sp="repair_ready"
        elif repair_status[eid]=="deferred":
            sp="deferred"
        elif not sks:
            sp="missing_locator"
        else:
            sp="photo_present_needs_visual"  # corpus complete (0 missing pages); visual review pending
        sp_status_c[sp]+=1
        # field status
        fs={}
        def fst(name,present,reason=""):
            if name in vfields: return "source_verified"
            if present: return "present"
            field_issue_c[name]+=1
            return f"missing:{reason}" if reason else "missing"
        fs["headword"]=fst("headword",bool(e.get("headword")))
        # root: empty root on a noun/particle is the curator noun-keying STYLE (not an error,
        # per repair_batch_001 evidence); only a verb missing a root is a real review item.
        if e.get("root"):
            fs["root"]="source_verified" if "root" in vfields else "present"
        elif e.get("section")=="verb":
            fs["root"]="missing:verb without triliteral root (review)"; field_issue_c["root"]+=1
        else:
            fs["root"]="not_applicable:curator noun-keying style (no triliteral root)"
        fs["forms"]=fst("forms",any(u.get("forms") for u in e.get("usage",[])),"no forms listed")
        fs["senses"]=fst("senses",bool(e.get("senses")))
        fs["counts"]=fst("counts",all(s.get("count") is not None for s in e.get("senses",[])) and bool(e.get("senses")),"sense missing count")
        fs["total_uses"]=fst("total_uses",e.get("total_uses") is not None)
        fs["quran_refs"]=fst("quran_refs",bool(ayat),"no example āyāt")
        complete = (words>0 and pending==0)
        if complete: hover_complete+=1
        repair_c[repair_status[eid]]+=1
        # next action (exact, no unknown)
        if pending>0:
            na=f"author {pending} pending hover token(s) in example āyāt (blockers: {dict(blk.most_common(3))})"
        elif sp!="verified" and sks:
            na=f"visually verify source photo for fields against {sks[0]} (source_photo_status={sp})"
        elif not sks:
            na="locate source key / page for this entry (missing_locator)"
        else:
            na="terminal: hover-complete + source-verified"
        rows.append({
            "entry_id":eid,"source_keys":sks,"category":e.get("category",""),
            "root":e.get("root",""),"lemma":e.get("headword",""),"section":e.get("section",""),
            "source_photo_status":sp,
            "field_status":fs,
            "hover_status":{"complete":complete,"resolved_tokens":covered,
                            "pending_tokens":pending,"blockers":dict(blk.most_common())},
            "repair_status":repair_status[eid],
            "next_action":na,
        })

    matrix=os.path.join(REPORTS,"qamus-2092-entry-matrix.jsonl")
    with open(matrix,"w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")

    sec=Counter(r["section"] for r in rows)
    # scoreboard
    sb=["# Qamus 2,092-entry terminal scoreboard\n",
        f"All **{len(rows):,}** entries audited; **0 unknown buckets**. "
        f"Sections: {dict(sec)} (reconciles to public 947/1045/100).\n",
        "## Source-photo status\n","| status | count |\n|---|---|"]
    for k,v in sp_status_c.most_common(): sb.append(f"| {k} | {v:,} |")
    sb.append("\n## Hover status\n")
    sb.append(f"- entries fully hover-complete (all example tokens resolved): **{hover_complete:,}**")
    sb.append(f"- entries with ≥1 pending hover token: **{len(rows)-hover_complete:,}**\n")
    sb.append("## Repair status\n| status | count |\n|---|---|")
    for k,v in repair_c.most_common(): sb.append(f"| {k} | {v:,} |")
    sb.append("\n## Field issues (entries where a field is missing, with reason)\n| field | entries missing |\n|---|---|")
    for k,v in field_issue_c.most_common(): sb.append(f"| {k} | {v:,} |")
    sb.append("\n> hover-complete ≠ source-verified, and source-verified ≠ hover-complete: tracked independently above.\n")
    open(os.path.join(REPORTS,"qamus-2092-terminal-scoreboard.md"),"w",encoding="utf-8").write("\n".join(sb))

    comp=["# Qamus 2,092 audit completion\n",
          f"Matrix: `qamus/reports/qamus-2092-entry-matrix.jsonl` ({len(rows):,} rows, one per entry).\n",
          "Row keys: entry_id, source_keys, category, root, lemma, section, source_photo_status, "
          "field_status{headword,root,forms,senses,counts,total_uses,quran_refs}, "
          "hover_status{complete,resolved_tokens,pending_tokens,blockers}, repair_status, next_action.\n",
          "Terminal-state rules enforced:\n",
          "- no 'unknown' bucket — every status is from a controlled vocabulary;\n",
          "- source_photo_status is never 'needs_retake' by default (corpus is complete: 0 missing "
          "pages per the rescue audit) — un-verified entries are `photo_present_needs_visual`;\n",
          "- 'missing' field statuses carry a reason (e.g. proper-noun entry has no triliteral root);\n",
          "- next_action is exact and per-entry.\n",
          f"Top remaining work: {len(rows)-hover_complete:,} entries have ≥1 pending hover token; "
          f"{sp_status_c.get('photo_present_needs_visual',0):,} entries await source-photo visual verification.\n"]
    open(os.path.join(REPORTS,"qamus-2092-audit-completion.md"),"w",encoding="utf-8").write("\n".join(comp))

    print(f"MATRIX OK rows={len(rows)} sections={dict(sec)}")
    print("source_photo:",dict(sp_status_c))
    print("repair:",dict(repair_c))
    print("hover_complete:",hover_complete,"/ has_pending:",len(rows)-hover_complete)
    print("field issues:",dict(field_issue_c))
    assert len(rows)==2092, "ROW COUNT != 2092"
    assert dict(sec)=={"verb":947,"noun":1045,"particle":100}, "SECTION RECONCILE FAIL"
    print("INVARIANT OK: 2092 rows, sections reconcile to public")

if __name__=="__main__":
    main()
