#!/usr/bin/env python3
# LEGACY: superseded by the tools/ generators (canonical machine index is existing_qamus_index.min.json; canonical graph is qamus/indexes/current/*-full.jsonl). Kept for reference; not the current canonical generator.
"""SN6 — turn the upgraded sarf/nahw knowledge into Qamus/hover CANDIDATES.

Review-only. No live writes. Reads committed evidence (verb-measure examples,
the knowledge base, the 2,092 index, the live authored batch) and emits three
deduped candidate files under qamus/candidates/qamus_2092/:

    sarfnahw_hover_candidates.jsonl          (authored hover glosses, evidence-backed)
    sarfnahw_entry_repair_candidates.jsonl   (POS/gloss-shape repairs; NO mutation)
    sarfnahw_review_queue.jsonl              (homograph/multi-sense -> human review)

Each hover candidate carries the public_record that WOULD ship ({src,kind,lang,text})
plus internal evidence (sarf/nahw/qamus) and a public_export_allowed flag. The
public artifact never carries the evidence or any external source name.
"""
import os
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import normalize_ar as N                                 # noqa: E402

IDX = os.path.join(ROOT, "qamus", "indexes", "existing_qamus_index.json")
KB = os.path.join(ROOT, "corpora", "sarfnahw", "knowledge_base.json")
VM_EX = os.path.join(ROOT, "sarf", "examples", "verb-measure-examples.jsonl")
LIVE_BATCH = os.path.join(ROOT, "qamus", "candidates", "qamus_2092", "authored_gloss_batch_001.jsonl")
OUT = os.path.join(ROOT, "qamus", "candidates", "qamus_2092")

# function words whose surface is a known diacritic-homograph -> never surface-key export
HOMOGRAPH_SURFACES = {"ما", "من", "لما", "ان", "اني", "كلا", "نعم", "لم", "ذكر"}
# unambiguous adverbs/prepositions safe to author surface-wide
SAFE_FUNCTION = {"قبل", "بعد", "فوق", "تحت", "بين", "وراء", "امام", "خلف", "عند", "حول", "منذ"}


def load_jsonl(p):
    out = []
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def main():
    idx = json.load(open(IDX, encoding="utf-8"))
    kb = json.load(open(KB, encoding="utf-8"))
    vm = load_jsonl(VM_EX)
    live = {r.get("norm_strict", "") for r in load_jsonl(LIVE_BATCH)}

    # index lookups: norm_strict -> entry, bare -> entry, root set
    by_ns, by_bare, roots = {}, {}, set()
    for k, v in idx.items():
        if v.get("norm_strict"):
            by_ns.setdefault(v["norm_strict"], k)
        if v.get("bare"):
            by_bare.setdefault(v["bare"], k)
        if v.get("root"):
            roots.add(v["root"].replace(" ", ""))

    hover, repairs, review = [], [], []
    seen = set()

    # ---- 1. verb-form hover candidates (from the authored verb-measure examples) ----
    for ex in vm:
        surf = ex.get("surface")
        if not surf:
            continue
        ns = N.norm_strict(surf)
        bare = N.bare(surf)
        if ns in seen:
            continue
        seen.add(ns)
        already_live = ns in live
        homograph = bare in HOMOGRAPH_SURFACES
        entry = by_ns.get(ns) or by_bare.get(bare)
        root = ex.get("root", "")
        root_known = root.replace(" ", "") in roots if root else False
        rec = {
            "source_address": ("quran:%s" % ex["quran"]) if ex.get("quran") else "form-aware-authored",
            "surface_ar": surf,
            "quran_loc": ex.get("quran") or None,
            "root_ar": root or None,
            "pos": ex.get("form") if ex.get("form") in ("masdar", "ism_fa3il", "ism_maf3ul") else "verb",
            "public_record": {"src": "qamus", "kind": "authored", "lang": "en", "text": ex.get("gloss", "")},
            "internal_provenance": {
                "qamus_entries": [entry] if entry else [],
                "informed_by": ["qac", "qamus"],
                "quran_text_verified": False,
                "note": "owner verifies the āyah",
            },
            "sarf_evidence": "Form %s; %s" % (ex.get("form", "?"), ex.get("decision", "")),
            "nahw_evidence": "",
            "decision": "authored_gloss",
            "confidence": "high" if root_known else "medium",
            "public_export_allowed": (not homograph) and (not already_live),
            "review_status": "needs_human_review",
            "dedup": {"already_live": already_live, "qamus_root_known": root_known,
                      "homograph_risk": homograph},
        }
        if homograph:
            rec["decision"] = "pending"
            rec["pending_reason"] = "hamza_sensitive_homograph"
            review.append(rec)
        else:
            hover.append(rec)

    # ---- 2. function-word hover candidates (from the KB inventory) ----
    for c in kb.get("concepts", []):
        if c.get("topic") not in ("preposition", "pronoun", "particle"):
            continue
        for e in c.get("examples", []):
            surf = e.get("surface_ar")
            gloss = (e.get("gloss_en") or "").strip()
            if not surf or not gloss:
                continue
            ns, bare = N.norm_strict(surf), N.bare(surf)
            if ns in seen:
                continue
            seen.add(ns)
            homograph = bare in HOMOGRAPH_SURFACES
            safe = bare in SAFE_FUNCTION
            already_live = ns in live
            rec = {
                "source_address": "form-aware-authored",
                "surface_ar": surf, "quran_loc": None, "root_ar": None, "pos": c["topic"],
                "public_record": {"src": "qamus", "kind": "authored", "lang": "en", "text": gloss},
                "internal_provenance": {"qamus_entries": [], "informed_by": ["qamus"],
                                        "note": "corpus-attested function word; harakāt-guarded"},
                "sarf_evidence": "", "nahw_evidence": "%s (corpus-attested)" % c["topic"],
                "decision": "authored_gloss" if (safe and not homograph) else "pending",
                "confidence": "high" if safe else "medium",
                "public_export_allowed": safe and (not homograph) and (not already_live),
                "review_status": "needs_human_review",
                "dedup": {"already_live": already_live, "homograph_risk": homograph, "safe_adverb": safe},
            }
            if homograph or not safe:
                rec["pending_reason"] = "homograph_haraka" if homograph else "context_sensitive_needs_nahw"
                review.append(rec)
            else:
                hover.append(rec)

    # ---- 3. entry-repair candidates: noun/particle entry carrying a 'to <verb>' gloss ----
    for k, v in idx.items():
        gl = v.get("glosses") or []
        cat = (v.get("pos_category") or "").lower()
        cls = v.get("class")
        if gl and isinstance(gl, list):
            g0 = str(gl[0]).strip()
            if (cls == "n" or "noun" in cat or "particle" in cat) and re.match(r"^to\s+\w", g0.lower()):
                repairs.append({
                    "source_address": v.get("source_address", k),
                    "entry_id": v.get("entry_id"), "headword": v.get("headword"),
                    "pos_category": v.get("pos_category"),
                    "field_path": "glosses[0]",
                    "current": g0[:80],
                    "issue": "pos_mismatch: a noun/adjective entry carries a 'to <verb>' (finite-verb) gloss",
                    "sarf_evidence": "صفة مشبهة / ism — gloss shape should be nominal/adjectival "
                                     "('one who …', '…-ing'), not 'to …' (see masdar-participle-notes.md)",
                    "proposed_direction": "reshape to a nominal/adjectival gloss; do NOT change the root",
                    "decision": "repair_candidate", "review_status": "needs_human_review",
                    "live_write": False,
                })

    # ---- 4. review-queue: plural-coverage opportunities (broken plurals -> entry plural field) ----
    plural_ops = 0
    for c in kb.get("concepts", []):
        if c.get("topic") != "plural_pattern":
            continue
        for e in c.get("examples", [])[:4]:
            sg, pl = e.get("singular_ar"), e.get("plural_ar")
            if not sg or not pl:
                continue
            sg_entry = by_bare.get(N.bare(sg)) or by_ns.get(N.norm_strict(sg))
            if sg_entry:
                pl_in = N.bare(pl) in by_bare
                review.append({
                    "kind": "plural_coverage", "singular_ar": sg, "plural_ar": pl,
                    "singular_entry": sg_entry, "plural_indexed": pl_in,
                    "sarf_evidence": "%s (%s)" % (c["arabic_label"], c["concept_id"].split(":")[-1]),
                    "action": "ensure the entry's plural field / forms[] includes this plural so the "
                              "plural token resolves to the singular lemma",
                    "decision": "review", "review_status": "needs_human_review", "live_write": False,
                })
                plural_ops += 1

    def dump(name, rows):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump("sarfnahw_hover_candidates.jsonl", hover)
    dump("sarfnahw_entry_repair_candidates.jsonl", repairs)
    dump("sarfnahw_review_queue.jsonl", review)

    exportable = sum(1 for r in hover if r.get("public_export_allowed"))
    summary = {
        "hover_candidates": len(hover), "exportable_now": exportable,
        "entry_repair_candidates": len(repairs),
        "review_queue": len(review), "plural_coverage_ops": plural_ops,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    main()
