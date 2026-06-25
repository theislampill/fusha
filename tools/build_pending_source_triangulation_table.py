#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BULK CLOSURE Phase 1 — one source-triangulated row per remaining pending hover token.

Joins the blocker root-cause ledger (per-token QAC root/POS + entry links + homograph/proper/function
flags) with the Qamus entries (form->sense map + sense glosses) and the live verses (surface_ar +
āyah context). Classifies every pending token into a lane, marks deterministic-resolvable rows, and
proposes a concise AUTHORED gloss for the deterministic subset (from the Qamus sense, never copied).

Outputs:
  qamus/reports/closure-2092/pending-source-triangulation-table.jsonl   (one row per pending token)
  qamus/reports/closure-2092/pending-source-triangulation-summary.md/.json
Read-only. No external wording copied; proposed glosses derive from the Qamus entry's own sense gloss.
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
LED = os.path.join(ROOT, "qamus", "reports", "closure-2092", "blocker-root-cause-ledger.jsonl")
STAGE = os.environ.get("QAMUS_HOVER_STAGE", os.path.join(ROOT, "out", "hover_stage"))
OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092")

H = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
def norm(s):
    s = H.sub("", s or "")
    for a, b in (("ٱ", "ا"), ("أ", "ا"), ("إ", "ا"),
                 ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        s = s.replace(a, b)
    return s.strip()

VERB_GLOSS = re.compile(r"^to\s+\w", re.I)  # sense gloss shaped like a verb infinitive
CONSTRUCT_NORM_KEYS = {"ذو", "ذا", "ذي", "ذات", "ذوات"}

# root_cause -> (suggested_lane, match_type, sarf_proc, nahw_proc)
LANE = {
 "already_entry_form_present_index_miss": ("index_or_form_variant", "exact_form", "procedures/hover-application.md", None),
 "missing_form_variant_on_existing_entry": ("form_variant", "root_match", "procedures/verb-form.md", None),
 "forms_array_missing_surface": ("form_variant", "usage_form", "procedures/noun-plural-gender.md", None),
 "verb_clitic_object_or_subject_candidate": ("verb_clitic", "root_match", "procedures/verb-form.md", "procedures/preposition-pronoun.md"),
 "host_lexeme_possessive_candidate": ("host_lexeme", "root_match", "procedures/noun-plural-gender.md", "procedures/idafa-jar-majrur.md"),
 "function_word_not_form_work": ("token_irab", "collision", None, "procedures/particle-decision.md"),
 "particle_or_pronoun_misclassified_as_stem": ("token_irab", "collision", None, "procedures/particle-decision.md"),
 "content_homograph": ("token_irab", "collision", "procedures/homograph-risk.md", "procedures/irab-case-mood.md"),
 "same_surface_polysemy_requires_i3rab": ("token_irab", "collision", "procedures/homograph-risk.md", "procedures/irab-case-mood.md"),
 "verb_form_or_voice": ("token_irab", "root_match", "procedures/verb-form.md", "procedures/irab-case-mood.md"),
 "missing_qamus_entry_candidate": ("new_entry_proposal", "no_entry", "procedures/root-decision.md", None),
 "quran_refs_missing_or_incomplete": ("source_entry_repair", "root_match", None, None),
 "source_entry_required_before_resolution": ("source_entry_repair", "no_entry", None, None),
 "source_photo_visual_needed": ("source_photo", "no_entry", None, None),
 "genuinely_ambiguous_pending": ("scholar_review", "collision", "procedures/homograph-risk.md", "procedures/referent-context.md"),
 "truly_low_frequency_tail": ("token_irab", "root_match", None, None),
 "proper_vs_common": ("reject_unsafe", "collision", "procedures/proper-noun.md", "procedures/referent-context.md"),
 "particle_function": ("token_irab", "collision", None, "procedures/particle-decision.md"),
}

def main():
    ent = {}
    for ln in open(DATA, encoding="utf-8"):
        e = json.loads(ln); ent[e["id"]] = e
    # form(normalized) -> {entry_id: set(sense_n)}
    fsmap = {}
    sense_gloss = {}  # (entry_id, sense_n) -> gloss
    for eid, e in ent.items():
        for u in e.get("usage", []):
            sn = u.get("sense")
            for f in (u.get("forms") or []):
                fsmap.setdefault(norm(f), {}).setdefault(eid, set()).add(sn)
        for s in e.get("senses", []):
            sense_gloss[(eid, s.get("n"))] = s.get("gloss")
    verses = {}
    wp = os.path.join(STAGE, "wbw-lookup.json")
    if os.path.exists(wp):
        verses = json.load(open(wp, encoding="utf-8")).get("verses", {})

    def surface_at(loc):
        sa = ":".join(loc.split(":")[:2]); i = int(loc.split(":")[2])
        wl = verses.get(sa, [])
        return wl[i - 1] if 0 < i <= len(wl) else ""
    def ayah(loc):
        return " ".join(verses.get(":".join(loc.split(":")[:2]), []))
    def construct_sensitive(nk, entry):
        headword = (entry or {}).get("headword") if entry else ""
        return norm(nk) in CONSTRUCT_NORM_KEYS or norm(headword) in CONSTRUCT_NORM_KEYS

    rows = []
    for ln in open(LED, encoding="utf-8"):
        ln = ln.strip()
        if not ln or '"root_cause"' not in ln:
            continue
        r = json.loads(ln)
        rc = r.get("root_cause")
        lane, match_type, sarf_p, nahw_p = LANE.get(rc, ("token_irab", "collision", None, None))
        eid = r.get("root_entry") or r.get("host_entry")
        e = ent.get(eid)
        nk = r.get("nk"); qp = r.get("qac_pos"); loc = r["loc"]
        homograph = bool(r.get("homograph")); function_word = bool(r.get("function_word")); proper = bool(r.get("proper"))
        # POS agreement (sense-level if known, else entry-section). This must be
        # known before auto gating; an exact form on a different POS entry is not
        # deterministic hover material.
        sec = e.get("section") if e else None
        pos_agree = "unknown"
        if qp in ("N", "V", "P") and sec:
            secqp = {"noun": "N", "verb": "V", "particle": "P"}.get(sec)
            pos_agree = "agree" if secqp == qp else ("mismatch" if secqp in ("N", "V", "P") else "unknown")
        # sense mapping for this surface on its entry
        senses = sorted(fsmap.get(norm(nk), {}).get(eid, set())) if eid else []
        det = False; det_reason = ""; proposed = None; risk = "medium"; gate = "two_vote"
        if eid and match_type in ("exact_form", "usage_form") and senses:
            if homograph:
                det_reason = "homograph — per-loc context required"
            elif function_word or proper:
                det_reason = "function/proper — context required"
            elif qp not in ("N", "V"):
                det_reason = "non-content POS requires function/context review"
            elif pos_agree == "mismatch":
                det_reason = "entry section POS mismatch — needs authored repair/review"
            elif not r.get("qac_root"):
                det_reason = "source root unavailable — deterministic auto-rule disabled"
            elif construct_sensitive(nk, e):
                det_reason = "ذو/ذات construct is context-sensitive — needs iḍāfa review"
            elif len(senses) != 1:
                det_reason = "form maps to %d senses — ambiguous" % len(senses)
            else:
                g = sense_gloss.get((eid, senses[0]))
                # POS-at-sense check: noun token must not get a verb-shaped ("to ...") gloss
                if not g:
                    det_reason = "sense has no gloss"
                elif qp == "N" and VERB_GLOSS.match(g.strip()):
                    det_reason = "cross-POS: noun token, verb-shaped sense gloss — needs nominal authoring"
                elif qp == "V" and not VERB_GLOSS.match(g.strip()):
                    det_reason = "cross-POS: verb token, nominal sense gloss — needs verbal authoring"
                else:
                    det = True; det_reason = "single sense, POS-agree, no homograph"; proposed = g.strip()
                    risk = "low"; gate = "auto_rule"
        match_type2 = match_type
        if eid and not senses and match_type in ("exact_form", "usage_form"):
            match_type2 = "root_match"
        if det:
            lane = "auto_resolve_deterministic"
        elif lane == "index_or_form_variant":
            lane = "form_variant"
        affected_field_path = None
        if lane == "new_entry_proposal":
            gate = "owner"; risk = "high"
        elif lane == "source_entry_repair":
            gate = "source"; risk = "high"
            affected_field_path = {
                "quran_refs_missing_or_incomplete": "usage[].examples[].ref",
                "source_entry_required_before_resolution": "entry",
            }.get(rc, "entry")
        elif lane == "source_photo":
            gate = "source"; risk = "high"
        elif lane == "scholar_review":
            gate = "scholar"; risk = "scholar"
        elif lane == "reject_unsafe":
            gate = "scholar"; risk = "scholar"
        if det:
            gate = "auto_rule"; risk = "low"

        if det:
            blocker = det_reason
        elif lane == "new_entry_proposal":
            blocker = "%s: owner approval required for new-entry proposal" % rc
        elif lane == "source_entry_repair":
            blocker = "%s: source-entry repair required at %s" % (rc, affected_field_path)
        elif lane == "source_photo":
            blocker = "%s: source photo visual review required" % rc
        elif lane == "scholar_review":
            blocker = "%s: scholar review required for ambiguous context" % rc
        elif lane == "reject_unsafe":
            blocker = "%s: unsafe proper/common collision; keep pending/rejected" % rc
        else:
            blocker = "%s: requires %s with %s gate" % (rc, lane, gate)

        rows.append({
            "loc": loc, "surface_ar": surface_at(loc) or "", "nk": nk, "strict_nk": norm(nk),
            "blocker": r.get("coarse_blocker"), "root_cause": rc,
            "qac_root": r.get("qac_root"), "qac_pos": qp,
            "qamus_entry_candidate": eid, "qamus_entry_headword": (e.get("headword") if e else None),
            "qamus_entry_match_type": match_type2,
            "form_senses": senses, "pos_agreement": pos_agree,
            "qac_evidence": "available" if r.get("qac_root") else "unavailable",
            "quran_adapter_evidence": "unavailable",  # per-word source adapter not fetched in this offline bulk table
            "sarf_procedure": sarf_p, "nahw_procedure": nahw_p,
            "suggested_lane": lane,
            "deterministic_resolvable": det, "deterministic_reason": det_reason,
            "proposed_gloss": proposed,
            "risk": risk, "gate": gate,
            "public_payload_allowed": ("yes" if (det or lane in ("form_variant","host_lexeme","token_irab","verb_clitic")) else "no"),
            "public_provenance_clean": True,
            **({"affected_field_path": affected_field_path} if affected_field_path else {}),
            "ayah_context": ayah(loc)[:200],
            "blocker_if_not_resolved": blocker,
        })

    rows.sort(key=lambda r: (not r["deterministic_resolvable"], r["suggested_lane"], r["loc"]))
    with open(os.path.join(OUT, "pending-source-triangulation-table.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lane_c = collections.Counter(r["suggested_lane"] for r in rows)
    det_c = sum(1 for r in rows if r["deterministic_resolvable"])
    gate_c = collections.Counter(r["gate"] for r in rows)
    summ = {"_generator": "build_pending_source_triangulation_table", "total_pending": len(rows),
            "deterministic": det_c, "by_lane": dict(lane_c), "by_gate": dict(gate_c),
            "public_payload_allowed": sum(1 for r in rows if r["public_payload_allowed"] == "yes")}
    json.dump(summ, open(os.path.join(OUT, "pending-source-triangulation-summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    md = ["# Pending source-triangulation table — summary\n",
          f"**{len(rows):,} pending tokens**, one triangulated row each. **Deterministic-resolvable: {det_c}.**\n",
          "## By suggested lane\n| lane | count |\n|---|---:|"]
    for k, v in lane_c.most_common(): md.append(f"| {k} | {v:,} |")
    md.append("\n## By gate\n| gate | count |\n|---|---:|")
    for k, v in gate_c.most_common(): md.append(f"| {k} | {v:,} |")
    open(os.path.join(OUT, "pending-source-triangulation-summary.md"), "w", encoding="utf-8").write("\n".join(md))
    print("TRIANGULATION TABLE:", len(rows), "rows | deterministic:", det_c)
    print("by lane:", dict(lane_c))
    print("by gate:", dict(gate_c))

if __name__ == "__main__":
    main()
