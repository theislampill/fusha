#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build V/N grounding plans for the canonical units, READ-ONLY over
repository authority:

- a curated CANDIDATE_HEADWORDS table names standard citation-form exemplars
  per morphology unit (independently selected textbook forms, never
  lesson-distinctive words);
- each headword resolves to an entry by EXACT citation-form identity against
  qamus/data/current/entries.jsonl (harakat-stripped skeleton equality of the
  entry's own headword — identity matching, NOT root/surface similarity);
- resolved entries pull up to 3 SELECTED occurrences from the committed
  example-ayah universe (the entry's own selected words on its own card),
  each verified against qamus/indexes/quran-loc-surface (canonical surface
  NFC-equality); diverging witnesses are downgraded to card_display_only
  and never ground a canonical occurrence;
- every canonical unit ends in a closed grounding state:
    exact_v_candidates / exact_n_candidates / occurrence_plan_ready /
    authority_blocked (named missing evidence) / not_applicable_with_reason /
    sol_integration_blocked (needs the merged A2 dependency plane).

Output: curriculum/l1l6/canonical/vn-grounding.jsonl (+ meta).
Deterministic; stdlib only; nothing certified.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"
HARAKAT_RE = re.compile("[ً-ْٰۖ-ۭـ]")

# unit -> standard exemplar citation forms (clean-room textbook forms)
CANDIDATE_HEADWORDS = {
    "u-s02": ["نَزَّلَ", "أَنْزَلَ", "اِسْتَغْفَرَ"],
    "u-s03": ["كَاتِب", "مَكْتُوب", "عَالِم"],
    "u-s04": ["تَعْلِيم", "إِحْسَان", "قِتَال"],
    "u-s05": ["مَسْجِد", "مِيزَان", "مِفْتَاح"],
    "u-s06": ["قَالَ", "بَاعَ", "هَدَى", "رَدَّ"],
    "u-s08": ["رِجَال", "كُتُب", "مُسْلِمُونَ"],
    "cu-broken-plural-template-inventory": ["رِجَال", "كُتُب", "أَقْلَام"],
    "cu-quality-adjective-templates": ["كَرِيم", "عَظِيم", "شَدِيد"],
    "cu-intensive-agent-templates": ["غَفَّار", "صَبَّار"],
    "cu-elative-template-discriminator": ["أَكْبَر", "أَحْسَن", "خَيْر"],
    "cu-voice-melody-templates": ["خُلِقَ", "قِيلَ"],
    "cu-mim-initial-noun-discriminator": ["مَسْجِد", "مَغْرِب", "مِفْتَاح"],
    "cu-diminutive-template-family": ["عُبَيْد"],
    "cu-plural-of-plural-layer": ["بُيُوتَات"],
    "cu-marra-hayah-discriminator": ["سَجْدَة", "قِتْلَة"],
    "cu-collective-unit-noun-classes": ["شَجَر", "شَجَرَة", "تَمْر"],
    "cu-suffix-abstract-noun": ["جَاهِلِيَّة"],
    "cu-numeral-polarity-licensing": ["ثَلَاثَة", "سَبْع"],
    "cu-hamza-carrier-licensing": ["سَأَلَ", "قُرْءَان", "بِئْر"],
    "cu-perfect-person-ending-discriminator": ["كَتَبَ", "قَالَ"],
    "cu-hollow-shortening-selector": ["قَالَ", "كَانَ", "بَاعَ"],
    "cu-geminate-jussive-variants": ["رَدَّ", "ظَنَّ"],
    "cu-weak-rule-composition": ["رَأَى", "وَقَى"],
    "cu-imperative-stem-derivation": ["اُكْتُبْ", "قُلْ"],
}


def skel(s):
    return HARAKAT_RE.sub("", s)


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    units = _jsonl(BASE / "canonical" / "canonical-units.jsonl")
    by_skel = {}
    with (ROOT / "qamus" / "data" / "current" / "entries.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            hw = r.get("headword") or ""
            for piece in re.split(r"\s*/\s*", hw):
                if piece:
                    by_skel.setdefault(skel(piece), []).append(
                        {"entry_id": r["id"],
                         "source_keys": sorted(r.get("source_keys", [])),
                         "headword": hw})
    # SAME-ENTRY selected-witness join (Sol architecture repair): an entry
    # occurrence claim requires an appearance row of THAT entry's own card
    # with selected:true — the existence of a selected appearance on some
    # OTHER entry's card never authorizes this entry (12:43:6 canary: the
    # بقرات token appears on the سبع card as context and must never bind).
    #
    # CANONICAL-SURFACE verification (Sol fix-request round 2, finding 3): a
    # card's displayed surface may use a different orthographic convention
    # than the canonical text (wasla, dagger alif, quranic marks — e.g. the
    # 12:43:5 card shows سَبْعُ while the canonical surface is سَبْعَ). Every
    # witness is therefore verified against the committed canonical
    # loc->surface index; only NFC-equal witnesses ground a canonical
    # occurrence. A diverging witness is kept but DOWNGRADED to
    # card_display_only — establishing an orthography-normalization
    # equivalence would be a linguistic policy decision this programme may
    # not make (linguistic_review_blocked), so the row abstains from the
    # canonical claim instead.
    import unicodedata as _ud
    canonical_by_loc = {}
    with (ROOT / "qamus" / "indexes" / "quran-loc-surface" / "index.jsonl"
          ).open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            canonical_by_loc[r["loc"]] = r["surface"]
    witnesses_by_entry = {}
    with (ROOT / "qamus" / "lattice" / "example-ayah-universe.jsonl"
          ).open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if not r.get("selected"):
                continue  # context appearances NEVER become entry occurrences
            if not r.get("canonical_loc"):
                continue  # a witness requires an EXACT occurrence identity
            eid = r["entry_id"]
            witnesses_by_entry.setdefault(eid, [])
            if len(witnesses_by_entry[eid]) < 3:
                canonical = canonical_by_loc.get(r["canonical_loc"])
                verified = (canonical is not None
                            and _ud.normalize("NFC", canonical)
                            == _ud.normalize("NFC", r["displayed_surface"]))
                w = {
                    "occurrence_id": "quran:" + r["canonical_loc"],
                    "appearance_id": r["appearance_id"],
                    "surface": r["displayed_surface"],
                    "canonical_surface": canonical,
                    "canonical_surface_verified": verified,
                    "selected": True,
                    "evidence": r.get("source_card_backlink"),
                }
                if verified:
                    w["relation"] = "entry_selected_word"
                    w["witness_scope"] = "canonical_occurrence"
                else:
                    w["relation"] = "entry_selected_word_card_display_only"
                    w["witness_scope"] = "card_display_only"
                    w["scope_note"] = (
                        "card orthography diverges from the canonical surface "
                        "(or the loc is absent from the canonical index): "
                        "canonical equality is NOT established by this "
                        "programme — orthography-normalization equivalence is "
                        "a linguistic policy decision (linguistic_review_"
                        "blocked); this witness supports card display only "
                        "and never grounds a canonical occurrence")
                witnesses_by_entry[eid].append(w)

    rows = []
    for u in sorted(units, key=lambda x: x["unit_id"]):
        uid = u["unit_id"]
        row = {"schema": "curriculum.l1l6_vn_grounding_row.v1",
               "unit_id": uid, "axis": u["axis"], "status": "candidate"}
        hws = CANDIDATE_HEADWORDS.get(uid)
        if hws:
            resolved, ambiguous, unresolved = [], [], []
            for hw in hws:
                import unicodedata
                hw_nfc = unicodedata.normalize("NFC", hw)
                hits = by_skel.get(skel(hw), [])
                vn_hits = [h for h in hits
                           if any(k[0] in "vn" for k in h["source_keys"])]
                # FULL citation-form identity: the exemplar must NFC-equal one
                # of the entry's own /-split headword variants, harakat and
                # all. A skeleton-only hit is root/shape resemblance — exactly
                # the og-1 inference this builder prohibits — and is recorded
                # as unresolved, never bound.
                exact = [h for h in vn_hits if any(
                    unicodedata.normalize("NFC", piece.strip()) == hw_nfc
                    for piece in re.split(r"\s*/\s*", h["headword"]))]
                if len(exact) == 1:
                    h = exact[0]
                    resolved.append({
                        "candidate_headword": hw,
                        "entry_id": h["entry_id"],
                        "source_keys": [k for k in h["source_keys"]
                                        if k[0] in "vn"],
                        "match_basis": "full citation-form NFC identity (harakat included) against the entry's own headword — NOT skeleton, NOT similarity",
                        "selected_witnesses": witnesses_by_entry.get(h["entry_id"], []),
                        "witness_rule": "every witness is an appearance of THIS entry's own card with selected:true (exact appearance_id + surface + backlink); context appearances are excluded by construction; each witness is additionally verified against the canonical loc->surface index — only canonical_surface_verified witnesses ground a canonical occurrence, diverging witnesses are downgraded to card_display_only",
                    })
                elif len(exact) > 1:
                    ambiguous.append({
                        "candidate_headword": hw,
                        "state": "ambiguous_entry_identity",
                        "candidate_entry_ids": sorted(h["entry_id"] for h in exact),
                        "note": "more than one store entry carries this exact citation form; alternatives preserved (no arbitrary first-hit binding); resolution needs entry-sense evidence",
                    })
                else:
                    note = (" (skeleton-level matches exist in the store but "
                            "identity requires the full citation form — og-1 "
                            "forbids binding them)") if vn_hits else ""
                    unresolved.append(hw + note)
            kinds = {k[0] for r_ in resolved for k in r_["source_keys"]}
            if not resolved:
                row["blocker"] = ("no curated exemplar resolves by exact "
                                  "citation-form identity in the entry store "
                                  "(tried: %s); extension path: widen the "
                                  "exemplar list with store-attested citation "
                                  "forms — identity matching only, never "
                                  "similarity" % " / ".join(unresolved))
            row.update({
                "grounding_state": ("exact_vn_candidates" if resolved
                                     else "authority_blocked"),
                "v_candidates": sum(1 for r_ in resolved
                                    for k in r_["source_keys"] if k[0] == "v"),
                "n_candidates": sum(1 for r_ in resolved
                                    for k in r_["source_keys"] if k[0] == "n"),
                "resolved": resolved,
                "ambiguous_identity": ambiguous,
                "unresolved_headwords": unresolved,
                "required_sarf_facts": "root + template identity per exemplar (evidence ladder; the unit's pack classifies, never certifies)",
                "required_nahw_facts": "per-occurrence function/case facts remain two-vote gated",
                "evidence_for_promotion": "per-occurrence evidence rows on the listed occurrence ids; entry-sense selection stays entry-governed",
                "abstention_conditions": "no exact citation-form match -> no link (unresolved recorded); shared root NEVER implies entry identity (og-1)",
            })
        elif u["axis"] == "nahw":
            row.update({
                "grounding_state": "sol_integration_blocked",
                "blocker": "occurrence grounding for syntax units requires per-occurrence governor/dependency evidence from the merged Burst-A2 nahw plane (Sol-owned, merged to main after this branch's base); candidate lattices exist but occurrence selection without that plane would be surface-similarity inference, which is prohibited",
            })
        elif u["axis"] == "cross" or u.get("capability_family") == "instructional_only":
            row.update({
                "grounding_state": "not_applicable_with_reason",
                "reason": "cross-axis/instructional unit: grounds through the units it composes with (pedagogy plane), not through direct entry links",
            })
        else:
            row.update({
                "grounding_state": "authority_blocked",
                "blocker": "no curated standard exemplar yet resolves for this sarf unit; extension path: widen CANDIDATE_HEADWORDS with independently selected citation forms and re-run (identity matching only)",
            })
        rows.append(row)

    meta = {
        "schema": "curriculum.l1l6_vn_grounding_row.v1.meta",
        "generator": "tools/build_vn_grounding.py",
        "units": len(rows),
        "state_histogram": {s: sum(1 for r in rows if r["grounding_state"] == s)
                            for s in sorted({r["grounding_state"] for r in rows})},
        "units_with_exact_v": sum(1 for r in rows if r.get("v_candidates", 0) > 0),
        "units_with_exact_n": sum(1 for r in rows if r.get("n_candidates", 0) > 0),
        "total_v_candidates": sum(r.get("v_candidates", 0) for r in rows),
        "total_n_candidates": sum(r.get("n_candidates", 0) for r in rows),
        "units_with_occurrences": sum(
            1 for r in rows
            if any(w.get("canonical_surface_verified")
                   for x in r.get("resolved", [])
                   for w in x.get("selected_witnesses", []))),
        "witnesses_total": sum(
            len(x.get("selected_witnesses", []))
            for r in rows for x in r.get("resolved", [])),
        "witnesses_canonical_verified": sum(
            1 for r in rows for x in r.get("resolved", [])
            for w in x.get("selected_witnesses", [])
            if w.get("canonical_surface_verified")),
        "witnesses_card_display_only": sum(
            1 for r in rows for x in r.get("resolved", [])
            for w in x.get("selected_witnesses", [])
            if not w.get("canonical_surface_verified")),
        "card_display_only_note": (
            "card_display_only witnesses diverge from the canonical "
            "loc->surface index (orthographic convention); they never ground "
            "a canonical occurrence — equivalence, if any, is a Sol/scholar "
            "policy decision (linguistic_review_blocked)"),
    }
    return rows, meta


def serialize(rows, meta):
    out = {}
    out[str(BASE / "canonical" / "vn-grounding.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    out[str(BASE / "canonical" / "vn-grounding.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    files = serialize(*build())
    bad = []
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(p.name)
        else:
            p.write_bytes(data)
            print("wrote %s (%d bytes)" % (p.relative_to(ROOT), len(data)))
    if check:
        if bad:
            print("FAIL: vn grounding differs: %s" % ", ".join(bad))
            return 1
        print("OK: vn grounding byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
