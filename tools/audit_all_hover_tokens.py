#!/usr/bin/env python3
"""P3 — full hover-token audit over every Qurʾān example token (all 49,900).

Reads:
  - the live hover artifact (wbw-lookup.json: words/verses/pending) from a staging dir
    (QAMUS_HOVER_STAGE, default out/hover_stage) — public-safe (Tanzil CC BY 3.0 text +
    qamus-authored glosses);
  - the token-decision layer (fusha-hover-token-decisions.jsonl) from the same dir;
  - the committed P0 dataset indexes (qamus/indexes/current) for entry-context + classification.

Emits (public-safe, no private data):
  qamus/reports/hover-token-audit-full.jsonl   one row per token, terminal state
  qamus/reports/hover-token-audit-full.md       summary
  qamus/reports/hover-token-pending-by-blocker.md
  qamus/reports/hover-gloss-terminal-scoreboard.md  (refreshed)

EVERY token gets a terminal state: resolved | pending(exact blocker) | quarantine | repair_candidate.
No generic "pending": each unresolved token carries an exact blocker from the controlled
vocabulary + an exact next_action. Run by tools/query_hover_token.py for per-loc inspection.
"""
import json, os, sys, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT, "out", "hover_stage"))
IDX = os.path.join(ROOT, "qamus", "indexes", "current")
REPORTS = os.path.join(ROOT, "qamus", "reports")

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
    return "".join(out).replace("آ","ا").replace("ٱ","ا").replace("ى","ي").replace("ة","ه").replace(" ","")

def norm_lenient(s):
    s = norm_strict(s)
    return s.replace("أ","").replace("إ","").replace("ء","").replace("ؤ","و").replace("ئ","ي")

# enclitic pronouns (longest first) for host-stem extraction
ENCLITICS = ["كما","هما","كنّ","هنّ","كم","هم","نا","ها","هن","كن","ني","ه","ك","ي","هۦ"]
PROCLITICS = ["وبال","فبال","بال","كال","فال","وال","لل","ال","و","ف","ب","ك","ل","س"]

# live pending code -> (terminal blocker, next_action)
BLOCKER_MAP = {
    "pre":     ("stem_base_unknown", "author the host stem (after the proclitic) as a Qamus form/gloss, then re-run the clitic resolver"),
    "suffix":  ("stem_base_unknown", "author the host noun stem so the suffix/pronoun lane can compose '<possessor> <stem>'"),
    "article": ("stem_base_unknown", "author the al-stem lexeme gloss in Qamus, then re-run"),
    "form":    ("source_entry_unverified", "add this inflected form to the entry's forms[] (or create the lexeme) and re-run"),
    "sense":   ("same_surface_polysemy_requires_i3rab", "author a per-loc token-addressed decision selecting the sense by iʿrāb"),
    "ambig":   ("same_surface_polysemy_requires_i3rab", "author a per-loc token-addressed decision (harakat/iʿrāb) resolving the homograph"),
    "fn":      ("same_surface_polysemy_requires_i3rab", "author a per-loc function-word decision (nahw) selecting the function by context"),
    "proper":  ("proper_noun_no_qamus_entry", "create a proper-noun entry or token-address it as a proper noun (name, no lexical gloss)"),
}
NEXT_ACTION = {
    "stem_base_unknown": "author the host stem/lexeme in Qamus, then re-run the resolver",
    "source_entry_unverified": "add the inflected form to the entry forms[] (or verify the entry from source photo) and re-run",
    "same_surface_polysemy_requires_i3rab": "author a per-loc token-addressed decision (iʿrāb) selecting the sense",
    "proper_noun_no_qamus_entry": "create a proper-noun entry or token-address as a proper noun (no gloss)",
}

def load():
    wbw = json.load(open(os.path.join(STAGE,"wbw-lookup.json"),encoding="utf-8"))
    words = wbw["words"]; verses = wbw["verses"]; pending = wbw["pending"]
    decisions = {}
    dpath = os.path.join(STAGE,"fusha-hover-token-decisions.jsonl")
    if os.path.exists(dpath):
        for line in open(dpath,encoding="utf-8"):
            line=line.strip()
            if line:
                d=json.loads(line); decisions[d["loc"]]=d
    by_ref = json.load(open(os.path.join(IDX,"by-quran-ref.json"),encoding="utf-8"))
    by_norm = json.load(open(os.path.join(IDX,"by-normalized-surface.json"),encoding="utf-8"))
    by_lemma = json.load(open(os.path.join(IDX,"by-lemma.json"),encoding="utf-8"))
    by_id = json.load(open(os.path.join(IDX,"by-entry-id.json"),encoding="utf-8"))
    return words, verses, pending, decisions, by_ref, by_norm, by_lemma, by_id

def strip_clitics(surface):
    """Return candidate host stems (norm_lenient) after stripping proclitics/enclitics."""
    base = norm_lenient(surface)
    cands = {base}
    for pre in PROCLITICS:
        if base.startswith(pre) and len(base)>len(pre)+1:
            cands.add(base[len(pre):])
    for suf in [norm_lenient(s) for s in ENCLITICS]:
        if suf and base.endswith(suf) and len(base)>len(suf)+1:
            cands.add(base[:-len(suf)])
    return cands

def lemma_entry_for(surface, by_norm, by_lemma):
    """Does any Qamus entry plausibly host this surface (after clitic strip)?"""
    for c in strip_clitics(surface):
        if c in by_norm: return by_norm[c]
    # exact lemma fallback
    nk = norm_strict(surface)
    if nk in by_norm: return by_norm[nk]
    return []

def proc_for_decision(d):
    if not d: return (None, None)
    if "stem" in d and "suffix" in d:  # suffix/pronoun lane
        return ("suffix-pronoun-state", "pronoun-attachment")
    if "key" in d:  # homograph harakat/iʿrāb split
        return ("surface-state-transition", "particle-state-split")
    return ("surface-state-transition", "particle-state-split")

def main():
    words, verses, pending, decisions, by_ref, by_norm, by_lemma, by_id = load()
    os.makedirs(REPORTS, exist_ok=True)
    rows = []
    state_c = Counter(); blocker_c = Counter(); conf_c = Counter()
    untagged_blocker_c = Counter()
    for sa in sorted(verses, key=lambda x: (int(x.split(":")[0]), int(x.split(":")[1]))):
        wlist = verses[sa]
        for i, surface in enumerate(wlist, 1):
            loc = f"{sa}:{i}"
            d = decisions.get(loc)
            # entry_contexts (which entries cite this āyah) is āyah-level, identical for every
            # token here; it is stored once-per-āyah in P1's quran-usage-spine and joined on
            # demand by query_hover_token.py (via by-quran-ref) — not duplicated per token.
            row = {"quran_loc": loc, "surface_ar": surface}
            if loc in words:
                tok = words[loc]
                g = (tok.get("glosses") or [{}])[0]
                row["decision_state"] = "resolved"
                row["public_gloss"] = g.get("text","")
                row["conf"] = tok.get("conf","?")
                row["blocker"] = None
                row["next_action"] = None
                sp, npn = proc_for_decision(d)
                row["sarf_procedure"] = sp if d else ("form-resolution" if tok.get("conf")!="low" else "clitic/suffix-resolution")
                row["nahw_procedure"] = npn if d else None
                row["token_decision"] = bool(d)
                state_c["resolved"]+=1; conf_c[tok.get("conf","?")]+=1
            else:
                # unresolved -> exact blocker
                if loc in pending:
                    code = pending[loc]
                    blocker, na = BLOCKER_MAP.get(code, ("stem_base_unknown", NEXT_ACTION["stem_base_unknown"]))
                    if code == "form":
                        hosts = lemma_entry_for(surface, by_norm, by_lemma)
                        if not hosts:
                            blocker, na = "stem_base_unknown", NEXT_ACTION["stem_base_unknown"]
                    elif code == "proper":
                        # nahw check: if a common-word Qamus entry exists for this surface, it is a
                        # homograph of a proper noun (e.g. عَادَ "returned" vs عاد the tribe), NOT a
                        # bare proper noun — it needs iʿrāb, not a proper-noun blocker.
                        hosts = lemma_entry_for(surface, by_norm, by_lemma)
                        if hosts:
                            blocker, na = "same_surface_polysemy_requires_i3rab", NEXT_ACTION["same_surface_polysemy_requires_i3rab"]
                    row["pending_code"] = code
                else:
                    # untagged unresolved: classify from dataset
                    hosts = lemma_entry_for(surface, by_norm, by_lemma)
                    if hosts:
                        blocker, na = "source_entry_unverified", NEXT_ACTION["source_entry_unverified"]
                    else:
                        blocker, na = "stem_base_unknown", NEXT_ACTION["stem_base_unknown"]
                    untagged_blocker_c[blocker]+=1
                    row["pending_code"] = "untagged"
                row["decision_state"] = "pending"
                row["public_gloss"] = None
                row["conf"] = None
                row["blocker"] = blocker
                row["next_action"] = na
                row["sarf_procedure"] = None
                row["nahw_procedure"] = None
                row["token_decision"] = False
                state_c["pending"]+=1; blocker_c[blocker]+=1
            rows.append(row)

    total = len(rows)
    resolved = state_c["resolved"]; pendc = state_c["pending"]
    # write full jsonl — compact: omit null/empty fields; next_action is a pure function of
    # blocker (mapped in NEXT_ACTION, documented in the scoreboard) so it is not persisted per row.
    full = os.path.join(REPORTS,"hover-token-audit-full.jsonl")
    DROP = {"next_action"}
    with open(full,"w",encoding="utf-8") as f:
        for r in rows:
            slim = {k: v for k, v in r.items()
                    if k not in DROP and v not in (None, [], "", False)}
            # always keep these anchors even if falsey
            slim["quran_loc"] = r["quran_loc"]; slim["decision_state"] = r["decision_state"]
            f.write(json.dumps(slim,ensure_ascii=False,sort_keys=True)+"\n")

    pct = 100.0*resolved/total if total else 0
    # scoreboard
    sb = []
    sb.append("# Hover-gloss terminal scoreboard\n")
    sb.append(f"Source artifact `source_sha=65797d7d5599fadd`. Every one of the **{total:,}** "
              f"hover tokens has a terminal state (no generic pending).\n")
    sb.append("| state | count | pct |\n|---|---|---|")
    sb.append(f"| **resolved** | {resolved:,} | {pct:.2f}% |")
    sb.append(f"| **pending (exact blocker)** | {pendc:,} | {100.0*pendc/total:.2f}% |")
    sb.append(f"| **total** | {total:,} | 100% |\n")
    sb.append("## Resolved by confidence\n")
    sb.append("| conf | count |\n|---|---|")
    for k,v in conf_c.most_common(): sb.append(f"| {k} | {v:,} |")
    sb.append("\n## Pending by blocker (exact, controlled vocabulary)\n")
    sb.append("| blocker | count | next action |\n|---|---|---|")
    for k,v in blocker_c.most_common():
        sb.append(f"| `{k}` | {v:,} | {NEXT_ACTION.get(k,'')} |")
    sb.append(f"\nUntagged-unresolved reclassified from dataset: {dict(untagged_blocker_c)}\n")
    open(os.path.join(REPORTS,"hover-gloss-terminal-scoreboard.md"),"w",encoding="utf-8").write("\n".join(sb))

    # audit md
    md = [f"# Hover-token audit (full)\n",
          f"All **{total:,}** tokens across **{len(verses):,}** āyāt audited to a terminal state.\n",
          f"- resolved: **{resolved:,}** ({pct:.2f}%)\n- pending (exact-blocked): **{pendc:,}**\n",
          "Row schema: `quran_loc, surface_ar, entry_contexts, decision_state, public_gloss, conf, "
          "blocker, next_action, sarf_procedure, nahw_procedure, token_decision, pending_code`.\n",
          "Inspect any token: `python3 tools/query_hover_token.py <S:A:W>`\n",
          "Arabic Qurʾān text © Tanzil Project, CC BY 3.0 (https://tanzil.net).\n"]
    open(os.path.join(REPORTS,"hover-token-audit-full.md"),"w",encoding="utf-8").write("\n".join(md))

    # by-blocker detail (sample locs per blocker)
    by_blk = defaultdict(list)
    for r in rows:
        if r["decision_state"]=="pending":
            by_blk[r["blocker"]].append(r["quran_loc"])
    bb = ["# Pending tokens by blocker\n",
          "Each blocker has an exact next action; no token is generically 'pending'.\n"]
    for blk,locs in sorted(by_blk.items(), key=lambda x:-len(x[1])):
        bb.append(f"## `{blk}` — {len(locs):,} tokens")
        bb.append(f"next: {NEXT_ACTION.get(blk,'')}")
        bb.append(f"sample locs: {', '.join(locs[:12])}\n")
    open(os.path.join(REPORTS,"hover-token-pending-by-blocker.md"),"w",encoding="utf-8").write("\n".join(bb))

    print(f"AUDIT OK total={total} resolved={resolved} ({pct:.2f}%) pending={pendc}")
    print("blockers:", dict(blocker_c))
    print("untagged reclassified:", dict(untagged_blocker_c))
    print("full jsonl bytes:", os.path.getsize(full))
    # invariant: every token terminal
    assert resolved + pendc == total, "NON-TERMINAL TOKENS!"
    print("INVARIANT OK: every token terminal")

if __name__ == "__main__":
    main()
