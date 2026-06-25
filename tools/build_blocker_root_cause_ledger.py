#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3 (closure-2092) — second-order BLOCKER ROOT-CAUSE ledger.

The four coarse blockers (stem_base_unknown / source_entry_unverified /
same_surface_polysemy_requires_i3rab / proper_noun_no_qamus_entry) say WHICH bucket a pending
token is in. They do not say WHAT it actually needs. This tool maps every pending token from its
coarse blocker to ONE specific root cause from a controlled vocabulary, with the evidence that
decides it (QAC root/POS, whether a Qamus entry hosts the surface, whether the QAC root already has
an entry, clitic structure, homograph status, occurrence yield).

Read-only. Imports the official audit module so the coarse blocker is computed identically (no drift).

Inputs (staged, public-safe):
  out/hover_stage/wbw-lookup.json                  verses/words/pending
  out/hover_stage/fusha-hover-token-decisions.jsonl
  out/hover_stage/qac-roots.tsv      loc(S:A:W) -> root           (precise per-token root)
  out/hover_stage/qac-tokroots.tsv   (S:A, surface) -> root, POS  (N/P/V)
  qamus/indexes/current/by-normalized-surface.json   norm surface -> [entry_id]
  qamus/indexes/current/by-root.json                 'r a d' radicals -> [entry_id]
  qamus/data/current/entries.jsonl                   entry_id -> forms/refs/senses/root

Outputs:
  qamus/reports/closure-2092/blocker-root-cause-ledger.jsonl     one row per pending token
  qamus/reports/closure-2092/blocker-root-cause-ledger.md        readable rollup
  qamus/reports/closure-2092/blocker-root-cause-summary.json     coarse->root-cause counts + yield
"""
import json, os, sys, collections, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT, "out", "hover_stage"))
IDX = os.path.join(ROOT, "qamus", "indexes", "current")
DATA = os.path.join(ROOT, "qamus", "data", "current")
OUTDIR = os.path.join(ROOT, "qamus", "reports", "closure-2092")

import audit_all_hover_tokens as A   # reuse norm/clitic/blocker logic verbatim

# Function words (norm_strict keys) whose pending always reduces to a nahw function decision.
FN = {"ما","وما","فما","ان","وان","فان","لم","لما","ولما","فلما","من","ومن","فمن","ام","او","لو","ولو",
      "ال","بل","قد","ها","ذا","اذ","واذ","فاذ","اذا","واذا","لا","ولا","فلا","الا","ألا","ثم","حتى","اذن",
      "لن","كل","كلا","انّ","ليت","لعل","لكن","لكنّ","كي","لكي","اي","أيّ","نعم","بلى","قط","لمّا"}

# Conservative known proper-noun surfaces (norm_strict) — Qurʾanic names/places/peoples.
PROPER = {"ادم","نوح","ابراهيم","اسماعيل","اسحاق","يعقوب","يوسف","موسي","هارون","عيسي","مريم","داود",
          "سليمان","ايوب","يونس","زكريا","يحيي","الياس","اليسع","ادريس","لوط","شعيب","صالح","هود","ذو",
          "محمد","احمد","فرعون","هامان","قارون","جالوت","طالوت","عاد","ثمود","مدين","بابل","مصر","سبا",
          "قريش","بدر","حنين","الكعبه","مكه","يثرب","الطور","الصفا","المروه","عرفات","جبريل","ميكال",
          "هاروت","ماروت","ابليس","يأجوج","مأجوج","اسرائيل","بنياسرايل","تبع","الروم","لقمان","عزير",
          "نمرود","الاحقاف","الجودي","سيناء"}

# nominal-derivative morphological prefix/pattern hints (heuristic, surface-norm_strict)
def looks_nominal_derivative(nk):
    # ism faail (faaعil) / istif3al masdar / mufaaعalah etc — cheap surface hints
    if nk.startswith("م") and len(nk) >= 4:   # maf3al/mif3al/mufaa3il families
        return True
    if nk.startswith("است") and len(nk) >= 5: # istif3al
        return True
    if nk.endswith("ون") or nk.endswith("ين") or nk.endswith("ات"):  # sound plurals
        return True
    return False

def root_concat(qac_root):
    if not qac_root: return ""
    return qac_root.replace(" ", "")

def root_flat(cc):
    return (cc.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ء", "")
              .replace("ؤ", "و").replace("ئ", "ي").replace("ى", "ي"))

def root_key_variants(cc):
    if not cc:
        return []
    keys = [cc, root_flat(cc)]
    # QAC sometimes records final hamza-seat weak roots as ...أ while the entry root is ...ء.
    if cc.endswith("أ"):
        alt = cc[:-1] + "ء"
        keys.extend([alt, root_flat(alt)])
    out = []
    for k in keys:
        if k and k not in out:
            out.append(k)
    return out

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    wbw = json.load(open(os.path.join(STAGE, "wbw-lookup.json"), encoding="utf-8"))
    words, verses, pending = wbw["words"], wbw["verses"], wbw["pending"]
    decisions = {}
    dp = os.path.join(STAGE, "fusha-hover-token-decisions.jsonl")
    if os.path.exists(dp):
        for ln in open(dp, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                d = json.loads(ln); decisions[d["loc"]] = d

    by_norm = json.load(open(os.path.join(IDX, "by-normalized-surface.json"), encoding="utf-8"))
    by_lemma = json.load(open(os.path.join(IDX, "by-lemma.json"), encoding="utf-8"))
    by_root = json.load(open(os.path.join(IDX, "by-root.json"), encoding="utf-8"))
    # by-root keyed by concatenated radicals (to match QAC concatenated roots), + hamza-flattened
    by_root_cc = {}
    for r, ids in by_root.items():
        cc = r.replace(" ", "")
        for key in root_key_variants(cc):
            by_root_cc.setdefault(key, set()).update(ids)

    # entries: forms(norm_strict set), refs(set of S:A), root, headword
    ent = {}
    for ln in open(os.path.join(DATA, "entries.jsonl"), encoding="utf-8"):
        e = json.loads(ln)
        forms = set()
        refs = set()
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                # split multi-token forms by space, consistent with the surface index (build_surface_index)
                for t in str(fstr).split():
                    forms.add(A.norm_strict(t))
            for ex in (u.get("examples") or []):
                if ex.get("ref"):
                    refs.add(str(ex["ref"]))
        forms.add(A.norm_strict(e.get("headword", "")))
        ent[e["id"]] = {"root": e.get("root", ""), "headword": e.get("headword", ""),
                        "forms": forms, "refs": refs, "nsenses": len(e.get("senses", []))}

    # QAC: loc->root (precise), (ayah,nk)->POS, (ayah,nk)->root
    roots_by_loc = {}
    for ln in open(os.path.join(STAGE, "qac-roots.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 2:
            roots_by_loc[p[0]] = p[1]
    pos_by_as = {}
    root_by_as = {}
    for ln in open(os.path.join(STAGE, "qac-tokroots.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 4:
            ay, surf, rt, pos = p[0], p[1], p[2], p[3].strip()
            nk = A.norm_strict(surf)
            pos_by_as[(ay, nk)] = pos
            root_by_as[(ay, nk)] = rt

    # homograph map: surface norm_strict -> distinct QAC roots seen across ALL tokens
    surf_roots = collections.defaultdict(set)
    surf_count = collections.Counter()      # pending occurrence count per surface
    for sa, wlist in verses.items():
        for i, surface in enumerate(wlist, 1):
            loc = f"{sa}:{i}"
            nk = A.norm_strict(surface)
            r = root_by_as.get((sa, nk))
            if r:
                surf_roots[nk].add(root_concat(r))
            if loc not in words:
                surf_count[nk] += 1

    def coarse_blocker(loc, surface):
        """Replicate audit_all_hover_tokens classification exactly."""
        if loc not in pending:
            hosts = A.lemma_entry_for(surface, by_norm, by_lemma)
            return ("source_entry_unverified" if hosts else "stem_base_unknown", "untagged")
        code = pending[loc]
        blk, _ = A.BLOCKER_MAP.get(code, ("stem_base_unknown", ""))
        if code == "form":
            if not A.lemma_entry_for(surface, by_norm, by_lemma):
                blk = "stem_base_unknown"
        elif code == "proper":
            if A.lemma_entry_for(surface, by_norm, by_lemma):
                blk = "same_surface_polysemy_requires_i3rab"
        return (blk, code)

    rows = []
    for sa in sorted(verses, key=lambda x: (int(x.split(":")[0]), int(x.split(":")[1]))):
        for i, surface in enumerate(verses[sa], 1):
            loc = f"{sa}:{i}"
            if loc in words:
                continue
            nk = A.norm_strict(surface)
            blk, code = coarse_blocker(loc, surface)
            qroot_loc = roots_by_loc.get(loc)
            qroot_surface = root_by_as.get((sa, nk))
            qroot = qroot_surface
            qcc = root_concat(qroot)
            qpos = pos_by_as.get((sa, nk))
            host_ids = A.lemma_entry_for(surface, by_norm, by_lemma)  # entry hosts the surface?
            # F3 fix: flatten the QAC root (hamza/weak) before by-root lookup, exactly as entry roots are
            # flattened into by_root_cc — else أتي/رأي miss the existing أَتَى/رَأَى entries and get
            # misrouted to missing_qamus_entry. by_root_cc already carries both raw and flattened keys.
            root_id_set = set()
            for key in root_key_variants(qcc):
                root_id_set.update(by_root_cc.get(key, set()))
            root_ids = sorted(root_id_set) if qcc else []
            is_homograph = len(surf_roots.get(nk, set())) > 1
            is_fn = nk in FN
            is_proper = nk in PROPER or (qroot and nk.replace("ال", "") in PROPER)
            cnt = surf_count.get(nk, 1)
            has_enclitic = (code == "suffix")
            has_proclitic = (code in ("pre", "article"))

            rc = "unclassified"
            unlock = None          # what action unlocks it
            yield_kind = "per_loc" # per_loc | family | entry
            safe_tier = None       # A_safe | B_sense_select | C_pos_or_collision (for form-variant lanes)

            # entry the surface's QAC root resolves to (for POS/sense safety tiering)
            _eid = (root_ids[0] if root_ids else (host_ids[0] if host_ids else None))
            _nsenses = ent.get(_eid, {}).get("nsenses", 0) if _eid else 0

            def _form_tier():
                # A: verb token, single-sense root, collision-free -> verb gloss very likely applies (2-vote confirm)
                # B: multi-sense root -> needs per-loc sense selection
                # C: noun/participle token (verbal entry gloss would be a POS mismatch) or homograph collision
                def _entry_root_matches(eid):
                    if not (eid and qcc):
                        return False
                    entry_keys = set(root_key_variants(root_concat(ent.get(eid, {}).get("root"))))
                    token_keys = set(root_key_variants(qcc))
                    return bool(entry_keys & token_keys)
                if not qcc or qpos != "V" or not _entry_root_matches(_eid):
                    return "C_pos_or_collision"
                if is_homograph: return "C_pos_or_collision"
                if qpos == "N": return "C_pos_or_collision"   # entry glosses are verbal -> noun needs authored gloss
                if _nsenses <= 1: return "A_safe"
                return "B_sense_select"

            # F1: is the surface itself already a stored form/headword of EITHER the entry the QAC root
            # resolves to OR the entry the surface hosts to? If so it is a live index/resolver miss, not
            # authoring (the form already exists in an entry; it just was not in the headword-only index).
            _re = ent.get(root_ids[0]) if root_ids else None
            _he = ent.get(host_ids[0]) if host_ids else None
            already_present = bool((_re and nk in _re["forms"]) or (_he and nk in _he["forms"]))

            if blk == "stem_base_unknown":
                if is_proper:
                    rc = "proper_name_or_named_entity"; yield_kind = "family"; unlock = "token_or_entry"
                elif qpos == "P" or is_fn:
                    rc = "particle_or_pronoun_misclassified_as_stem"; unlock = "token"
                elif has_enclitic and qpos == "V":
                    # F2: a verb's enclitic is an object/subject pronoun, NOT a possessed-noun host.
                    rc = "verb_clitic_object_or_subject_candidate"; unlock = "token"
                elif has_enclitic and not host_ids:
                    rc = "host_lexeme_possessive_candidate"; yield_kind = "family"; unlock = "host_entry_or_token"
                elif already_present:
                    rc = "already_entry_form_present_index_miss"; unlock = "reindex_or_resolver"
                elif root_ids:
                    rc = "missing_form_variant_on_existing_entry"; yield_kind = "entry"
                    unlock = "author_form_gloss"; safe_tier = _form_tier()
                elif qcc and not root_ids:
                    rc = "missing_qamus_entry_candidate"; yield_kind = "family"; unlock = "new_entry"
                elif looks_nominal_derivative(nk):
                    rc = "nominal_derivative_candidate"; yield_kind = "family"; unlock = "new_entry_or_token"
                elif is_homograph:
                    rc = "context_i3rab_required"; unlock = "token"
                elif cnt <= 1 and not qcc:
                    rc = "truly_low_frequency_tail"; unlock = "token"
                else:
                    rc = "source_entry_required_before_resolution"; unlock = "source"

            elif blk == "source_entry_unverified":
                tgt = host_ids[0] if host_ids else None
                emeta = ent.get(tgt) if tgt else None
                forms_nl = {A.norm_lenient(x) for x in emeta["forms"]} if emeta else set()
                if qpos == "P" or is_fn:
                    # F4: function-word / particle material is a token/particle decision, NOT form authoring.
                    rc = "function_word_not_form_work"; unlock = "token"
                elif already_present:
                    # F1: the surface is already a stored form/headword -> live index/resolver miss, not authoring.
                    rc = "already_entry_form_present_index_miss"; unlock = "reindex_or_resolver"
                elif emeta and nk not in emeta["forms"] and A.norm_lenient(surface) not in forms_nl:
                    rc = "forms_array_missing_surface"; yield_kind = "entry"
                    unlock = "author_form_gloss"; safe_tier = _form_tier()
                elif emeta and sa not in emeta["refs"]:
                    rc = "quran_refs_missing_or_incomplete"; yield_kind = "entry"; unlock = "add_quran_ref"
                elif emeta and emeta["nsenses"] == 0:
                    rc = "sense_missing_or_ambiguous"; yield_kind = "entry"; unlock = "add_sense"
                else:
                    rc = "source_photo_visual_needed"; yield_kind = "entry"; unlock = "source_photo"

            elif blk == "same_surface_polysemy_requires_i3rab":
                if is_fn:
                    rc = "particle_function"; unlock = "token"
                elif is_homograph:
                    rc = "content_homograph"; unlock = "token"
                elif is_proper:
                    rc = "proper_vs_common"; unlock = "token"
                elif qpos == "V":
                    rc = "verb_form_or_voice"; unlock = "token"
                else:
                    rc = "genuinely_ambiguous_pending"; unlock = "token_or_scholar"

            elif blk == "proper_noun_no_qamus_entry":
                rc = "token_addressable_proper_noun"; unlock = "token"

            rows.append({
                "loc": loc, "surface": surface, "nk": nk,
                "coarse_blocker": blk, "pending_code": code, "root_cause": rc,
                "qac_root": qcc or None, "qac_pos": qpos,
                "qac_surface_match": bool(qroot_surface),
                "qac_loc_surface_conflict": bool(qroot_surface and qroot_loc and root_concat(qroot_loc) != qcc),
                "host_entry": host_ids[0] if host_ids else None,
                "root_entry": root_ids[0] if root_ids else None,
                "homograph": is_homograph, "function_word": is_fn, "proper": bool(is_proper),
                "surface_pending_count": cnt, "unlock": unlock, "yield_kind": yield_kind,
                "safe_tier": safe_tier,
            })

    # summary: coarse -> root_cause counts + family yield
    summ = collections.defaultdict(lambda: collections.Counter())
    tier_c = collections.Counter()
    for r in rows:
        summ[r["coarse_blocker"]][r["root_cause"]] += 1
        if r.get("safe_tier"):
            tier_c[r["safe_tier"]] += 1
    # yield families: group family-unlockable causes by (root_cause, family_key)
    fam = collections.defaultdict(lambda: {"tokens": 0, "members": set()})
    for r in rows:
        if r["yield_kind"] in ("family", "entry"):
            key = r["root_entry"] or r["host_entry"] or r["qac_root"] or r["nk"]
            fk = (r["root_cause"], key)
            fam[fk]["tokens"] += 1
    fam_rows = sorted(([rc, k, v["tokens"]] for (rc, k), v in fam.items()), key=lambda x: -x[2])

    _cov = round(100.0 * (49900 - len(rows)) / 49900, 2)
    with open(os.path.join(OUTDIR, "blocker-root-cause-ledger.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"_generator": "tools/build_blocker_root_cause_ledger.py",
                            "_source": "out/hover_stage/wbw-lookup.json", "_coverage_pct": _cov,
                            "_rows": len(rows)}, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    out_summary = {
        "_generator": "tools/build_blocker_root_cause_ledger.py",
        "total_pending": len(rows),
        "by_coarse_blocker": {k: dict(v) for k, v in summ.items()},
        "form_variant_safe_tier": dict(tier_c),
        "family_unlock_top50": [{"root_cause": rc, "family": k, "tokens": t} for rc, k, t in fam_rows[:50]],
        "family_unlock_total_tokens": sum(t for _, _, t in fam_rows),
        "family_unlock_count": len(fam_rows),
    }
    with open(os.path.join(OUTDIR, "blocker-root-cause-summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out_summary, f, ensure_ascii=False, sort_keys=True, indent=2); f.write("\n")

    # readable MD
    md = ["# Blocker root-cause ledger (closure-2092)", "",
          f"Generated by `tools/build_blocker_root_cause_ledger.py` from the staged artifact "
          f"(coverage {_cov}%). Every one of the **{len(rows):,}** pending tokens is mapped from its coarse "
          "blocker to a specific root cause with deciding evidence.", "",
          "Row schema (JSONL): `loc, surface, nk, coarse_blocker, pending_code, root_cause, qac_root, "
          "qac_pos, host_entry, root_entry, homograph, function_word, proper, surface_pending_count, "
          "unlock, yield_kind`.", ""]
    for blk in ("stem_base_unknown", "source_entry_unverified",
                "same_surface_polysemy_requires_i3rab", "proper_noun_no_qamus_entry"):
        sub = summ.get(blk)
        if not sub: continue
        tot = sum(sub.values())
        md += [f"## `{blk}` — {tot:,} tokens", "", "| root cause | tokens |", "|---|---:|"]
        for rc, c in sub.most_common():
            md.append(f"| `{rc}` | {c:,} |")
        md.append("")
    md += ["## Top family-unlock levers (one repair unlocks N tokens)", "",
           "| root cause | family key | tokens unlocked |", "|---|---|---:|"]
    for rc, k, t in fam_rows[:30]:
        md.append(f"| `{rc}` | `{k}` | {t} |")
    md += ["", f"Family/entry-unlockable tokens total: **{sum(t for _,_,t in fam_rows):,}** "
           f"across **{len(fam_rows):,}** families.", ""]
    open(os.path.join(OUTDIR, "blocker-root-cause-ledger.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))

    print("ROOT-CAUSE LEDGER OK rows=%d" % len(rows))
    for blk, sub in summ.items():
        print(blk, "=>", dict(sub.most_common()))
    print("form_variant_safe_tier =>", dict(tier_c))
    print("family-unlock tokens=%d families=%d" % (sum(t for _,_,t in fam_rows), len(fam_rows)))

if __name__ == "__main__":
    main()
