#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_morphology_lattice — the per-token ranked morphology CANDIDATE lattice (P2b deliverable A).

Builds, for one arbitrary Arabic token, the set of competing out-of-context morphological readings — NEVER a single
forced parse for unvoweled Arabic. Disambiguation is RANKING (analyze-then-rank: CAMeL Tools / MADAMIRA / CALIMA-Star,
deep-research R-MORPH-ANALYZE-RANK; ~12 analyses/word, R-MORPH-12): every candidate carries TWO distinct ordering fields
(`score` AND `rank`) and never a boolean `correct`. The lattice CONSUMES the clitic `segment_candidates` (each candidate's
`segment_candidate_ref` points back at a row) and never rebuilds a segmentation.

It is CONSERVATIVE and HONEST: without a full morphological analyzer, `root`/`lemma`/`pattern` and the deep `features` stay
null (blank beats a fabricated value); the deliverable is the POS/segmentation COMPETITION + evidence class + ranking +
ambiguity preservation + the closed-enum feature scaffold (P3 fills deep features with a learned/neural disambiguator).
Source-clean (`leak_sot.scan` every `ambiguity_reason`); dry-run. See
parserplans/general-fusha-grammar-checker-p2b-learning-cefr/001.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import normalize_ar as N  # noqa: E402
from tools import leak_sot  # noqa: E402
from tools.validate_linguistic_decisions import required_gate, _GATE_RANK  # noqa: E402
from tools.fusha_check import GATE_ALIAS  # noqa: E402

SCHEMA = "fusha/morphology-candidate-lattice@1"

# Local linguistic constants (mirror of the surface sets in fusha_text_check; kept local to avoid a circular import).
_PARTICLES = {"ما", "و", "ف", "لا", "إلا", "الا", "من", "لما", "ل", "أ", "إن", "أن", "إذا", "لو", "حتى", "كي",
              "لن", "لم", "قد", "بل", "ثم", "أو"}
_KNOWN_PREPS = {"من", "إلى", "الى", "على", "في", "عن", "مع", "حتى", "منذ", "مذ", "عند", "لدى", "لدن", "نحو",
                "دون", "خلال", "حول", "قبل", "بعد", "تحت", "فوق", "بين"}
_FEATURE_KEYS = ("verb_form", "voice", "aspect", "mood", "person", "number", "gender", "case", "state",
                 "derivative_type", "particle_function")
# POS classes for which a triliteral/quadriliteral ROOT is meaningful (particles/prepositions have no root).
_ROOT_BEARING_POS = ("noun", "proper_noun", "adjective", "participle", "masdar", "verb")


def _empty_features():
    return {k: None for k in _FEATURE_KEYS}


def _gate_for(triggers, source_addressed):
    g = GATE_ALIAS.get(required_gate(triggers), required_gate(triggers))
    # arbitrary / corpus text can never be auto_safe (this slice only populates the arbitrary path).
    if not source_addressed and _GATE_RANK[g] < _GATE_RANK["two_vote_required"]:
        g = "two_vote_required"
    return g


def _pos_candidates(stem_bare, roles, has_article, has_prep):
    """The competing coarse-POS readings for this segmentation's stem (closed pos enum subset)."""
    if stem_bare in _PARTICLES:
        return ["particle"]
    if stem_bare in _KNOWN_PREPS:
        return ["preposition"]
    if has_article or has_prep:
        # after al-/a preposition the stem is a noun-class word (noun/adjective collapsed to the coarse 'noun')
        return ["noun"]
    # a bare content stem genuinely underdetermines noun vs verb without an analyzer (R-MORPH-12) — keep BOTH, ranked.
    return ["noun", "verb"]


def _make_candidate(pos, seg_ref, *, voweled, source_addressed, n_pos, multi_proclitic, single_clitic,
                    has_article, stem_bare):
    feats = _empty_features()
    if has_article:
        feats["state"] = "definite"
    # static additive score (R-MORPH-PROB analogue): structural cues + voweling raise it; a lone single-letter peel lowers it.
    score = 1.0
    if voweled:
        score += 2.0
    if multi_proclitic:
        score += 1.0
    if single_clitic:
        score -= 1.0
    if pos == "particle":
        score += 2.0          # an exact function-word match is strong
    if pos in ("preposition",):
        score += 1.5
    if pos == "noun" and (has_article or stem_bare in ()):
        score += 1.0          # structurally favored noun reading
    if pos == "noun":
        score += 0.5          # nouns slightly more common than verbs as standalone tokens
    conf = "high" if score >= 3.0 else ("medium" if score >= 1.0 else "low")
    homograph = n_pos > 1
    if source_addressed and voweled and not homograph:
        evidence = "source_addressed_confirmable"
    elif voweled and not homograph:
        evidence = "voweled_confirmable"
    elif homograph:
        evidence = "homograph_split"
    elif len(stem_bare) <= 1:
        evidence = "component_only"
    else:
        evidence = "unvoweled_competing"
    triggers = []
    if homograph or not voweled:
        triggers.append("multi_sense_root")
    if any(ch in "أإؤئء" for ch in stem_bare):
        triggers.append("multi_sense_root")  # hamza-seat homograph risk
    reason = None
    if homograph:
        reason = "the same letters admit more than one part-of-speech reading; all are kept and ranked, none asserted"
    elif not voweled:
        reason = "unvoweled: the case/mood ending is not visible, so the reading stays a candidate"
    cand = {
        "lemma": None, "root": None, "pattern": None, "pos": pos, "features": feats,
        "confidence": conf, "ambiguity_reason": reason, "evidence_class": evidence,
        "gate": _gate_for(triggers, source_addressed), "rank": 0, "score": round(score, 3),
        "segment_candidate_ref": seg_ref,
    }
    return cand


def build_morphology_lattice(token_ref, surface, segment_cands, voweled, source_addressed=False,
                             qac=None, ayah_ref=None):
    """Return the lattice container {token_ref, candidates[], top_rank, n_candidates, all_unvoweled_kept} for one token.

    `segment_cands` is the token's `segment_candidates` (consumed, never rebuilt); each candidate's `segment_candidate_ref`
    is the integer index into it. >1 candidate ⇒ the caller keeps the token `pending` / `surface_only|candidate`.

    OPTIONAL real-data path (criticism 1): if the caller supplies a loaded `qac` adapter (a tools.qac_adapter.QacAdapter
    built from the USER's own local QAC export) AND `source_addressed` is True AND an `ayah_ref` (surah:ayah) is given,
    a confident QAC ROOT is attached as an occurrence-level FACT to the root-bearing candidates, with an internal
    `informed_by:["qac"]` breadcrumb (source-boundaries §1.2/§2 — fact only, never QAC text, stripped before publication).
    With no adapter (the default) every candidate keeps root=null and carries no breadcrumb — the output is
    BYTE-IDENTICAL to before. QAC is GPL v3 and is never vendored; only the user's local file is consulted.
    """
    cands = []
    for i, seg_cand in enumerate(segment_cands or []):
        segs = seg_cand.get("segments") or []
        stem = next((s for s in reversed(segs) if s.get("role") == "stem"), None)
        if stem is None:
            continue
        stem_bare = N.bare(stem.get("surface", ""))
        roles = {s.get("role") for s in segs}
        has_article = "definite_article" in roles
        has_prep = "prefix_preposition" in roles
        single_clitic = bool(seg_cand.get("single_letter_clitic"))
        multi_proclitic = (any((r or "").startswith("prefix_") or r == "definite_article" for r in roles)
                           and not single_clitic)
        pos_set = _pos_candidates(stem_bare, roles, has_article, has_prep)
        for pos in pos_set:
            cands.append(_make_candidate(pos, i, voweled=voweled, source_addressed=source_addressed,
                                         n_pos=len(pos_set), multi_proclitic=multi_proclitic,
                                         single_clitic=single_clitic, has_article=has_article, stem_bare=stem_bare))
    if not cands:
        # never empty for an Arabic token — fall back to a single honest 'unknown' candidate over the whole token.
        c = _make_candidate("unknown", 0, voweled=voweled, source_addressed=source_addressed, n_pos=1,
                            multi_proclitic=False, single_clitic=False, has_article=False, stem_bare=N.bare(surface))
        c["pos"] = "unknown"
        cands = [c]
    # RANK by descending score (stable); assign 1-based rank. score and rank are two DISTINCT fields (never a boolean).
    order = sorted(range(len(cands)), key=lambda j: -cands[j]["score"])
    for r, j in enumerate(order, 1):
        cands[j]["rank"] = r
    cands = [cands[j] for j in order]
    # OPTIONAL QAC fact consult (criticism 1). Purely additive + opt-in: with qac=None this block is skipped and the
    # output is byte-identical to the no-qac path. The root is an occurrence-level FACT; informed_by is an internal
    # breadcrumb (never QAC text). Only populated for a source-addressed token with a confident, leak-free root.
    if qac is not None and source_addressed and ayah_ref:
        try:
            qroot = (qac.get_root(ayah_ref, surface) or "").strip()
        except Exception:  # noqa: BLE001  a malformed adapter must never break the lattice
            qroot = ""
        if qroot and not leak_sot.is_leak(qroot):
            for c in cands:
                if c["pos"] in _ROOT_BEARING_POS:
                    c["root"] = qroot
                    c["informed_by"] = ["qac"]
    # leak scrub every public text field (ambiguity_reason); a hit forces never_auto_resolve + redaction.
    for c in cands:
        if c.get("ambiguity_reason") and leak_sot.is_leak(c["ambiguity_reason"]):
            c["ambiguity_reason"] = leak_sot.redact(c["ambiguity_reason"])
            c["gate"] = "never_auto_resolve"
    return {"token_ref": token_ref, "candidates": cands, "top_rank": 1, "n_candidates": len(cands),
            "all_unvoweled_kept": True}


# ---------------------------------------------------------------------------
# regression units + self-test
# ---------------------------------------------------------------------------
def _seg(surface, *roles_surfaces, single=False):
    return {"segments": [{"role": r, "surface": s, "gloss_contribution": None} for r, s in roles_surfaces],
            "rank": 0, "score": None, "legal": True, "single_letter_clitic": single}


def regression_units():
    """Authored arbitrary tokens (no Qurʾān copy). Each = (name, token_ref, surface, segment_cands, voweled, source_addressed)."""
    return [
        # unvoweled bare content word -> homograph (noun + verb), both kept
        ("unvoweled-homograph", "tok:0", "علم", [_seg("علم", ("stem", "علم"))], False, False),
        # voweled bare content word -> still 2 readings but higher confidence on rank-1
        ("voweled-content", "tok:0", "نورٌ", [_seg("نورٌ", ("stem", "نورٌ"))], True, False),
        # multi-letter proclitic (بال) over a noun stem -> noun, medium+
        ("multi-proclitic-noun", "tok:0", "بالقلم",
         [_seg("بالقلم", ("stem", "بالقلم")),
          _seg("بالقلم", ("prefix_preposition", "ب"), ("definite_article", "ال"), ("stem", "قلم"))], False, False),
        # lone single-letter peel (كـ) -> low-conf clitic reading kept alongside the radical reading
        ("single-letter-peel", "tok:0", "كتب",
         [_seg("كتب", ("stem", "كتب")),
          _seg("كتب", ("prefix_preposition", "ك"), ("stem", "تب"), single=True)], False, False),
        # exact particle (ما) -> particle reading
        ("particle", "tok:0", "ما", [_seg("ما", ("stem", "ما"))], False, False),
    ]


def _self_test():
    failures = []
    for name, ref, surface, segs, voweled, sa in regression_units():
        lat = build_morphology_lattice(ref, surface, segs, voweled, sa)
        cands = lat["candidates"]
        if not cands:
            failures.append("%s: empty lattice" % name); continue
        # >=1 always; ranks are 1..n; score+rank both present; no boolean 'correct'
        ranks = sorted(c["rank"] for c in cands)
        if ranks != list(range(1, len(cands) + 1)):
            failures.append("%s: ranks not 1..n (%s)" % (name, ranks))
        for c in cands:
            if "correct" in c or "is_correct" in c:
                failures.append("%s: candidate carries a boolean correct flag" % name)
            if not isinstance(c.get("score"), (int, float)) or not isinstance(c.get("rank"), int):
                failures.append("%s: score/rank must both be present and typed" % name)
            if c["gate"] == "auto_safe" and not sa:
                failures.append("%s: arbitrary candidate is auto_safe" % name)
            if set(c["features"].keys()) != set(_FEATURE_KEYS):
                failures.append("%s: features keys drifted" % name)
            if leak_sot.is_leak(c.get("ambiguity_reason") or ""):
                failures.append("%s: ambiguity_reason leaks" % name)
        if lat["all_unvoweled_kept"] is not True or lat["top_rank"] != 1 or lat["n_candidates"] != len(cands):
            failures.append("%s: container invariants broken" % name)
    # behaviour: unvoweled bare content word keeps >=2 (noun+verb) competing readings
    h = build_morphology_lattice("tok:0", "علم", [_seg("علم", ("stem", "علم"))], False, False)
    if len(h["candidates"]) < 2 or not any(c["evidence_class"] == "homograph_split" for c in h["candidates"]):
        failures.append("unvoweled-homograph: must keep >=2 competing readings (homograph_split)")
    # particle: top candidate is the particle reading
    p = build_morphology_lattice("tok:0", "ما", [_seg("ما", ("stem", "ما"))], False, False)
    if p["candidates"][0]["pos"] != "particle":
        failures.append("particle: top candidate should be 'particle'")

    # NON-VACUOUS auto_safe gate coverage: a voweled, article-bearing, non-homograph stem is the ONE shape whose
    # required_gate is auto_safe — so it actually exercises the arbitrary->two_vote_required UPGRADE (_gate_for).
    # The prior regression units all carry triggers, so none tested this. (a) ARBITRARY must be upgraded away from
    # auto_safe; (b) SOURCE-ADDRESSED keeps the legitimate auto_safe. Removing the upgrade flips (a) and FAILs here.
    asegs = [_seg("الْكِتَابُ", ("definite_article", "ال"), ("stem", "كِتَابُ"))]
    arb_as = build_morphology_lattice("tok:0", "الْكِتَابُ", asegs, True, source_addressed=False)
    if any(c["gate"] == "auto_safe" for c in arb_as["candidates"]):
        failures.append("arbitrary voweled article noun must be UPGRADED off auto_safe (two_vote_required)")
    if arb_as["candidates"][0]["gate"] != "two_vote_required":
        failures.append("arbitrary auto_safe-eligible token must become two_vote_required, got %s"
                        % arb_as["candidates"][0]["gate"])
    sa_as = build_morphology_lattice("tok:0", "الْكِتَابُ", asegs, True, source_addressed=True)
    if sa_as["candidates"][0]["gate"] != "auto_safe":
        failures.append("source-addressed voweled article noun should keep the legitimate auto_safe, got %s"
                        % sa_as["candidates"][0]["gate"])

    # OPTIONAL QAC consult (criticism 1). Uses a hand-written, in-memory, NON-QAC fixture (no QAC data shipped or
    # read from disk). Proves: default path stays null; wired path attaches the root FACT + informed_by; the
    # arbitrary (non-source-addressed) path is never populated even if an adapter is passed.
    from tools.qac_adapter import QacAdapter  # noqa: E402  (local import keeps the module import-light)
    fixture = [{"location": "0:0:1", "form": "كِتَابٌ", "tag": "N", "features": "STEM|POS:N|ROOT:كتب"}]  # synthetic
    qac = QacAdapter.from_rows(fixture)
    ksegs = [_seg("كِتَابٌ", ("stem", "كِتَابٌ"))]
    base = build_morphology_lattice("tok:0", "كِتَابٌ", ksegs, True, source_addressed=True)
    if any(c.get("root") is not None or "informed_by" in c for c in base["candidates"]):
        failures.append("QAC default path must keep root null and carry no informed_by")
    wired = build_morphology_lattice("tok:0", "كِتَابٌ", ksegs, True, source_addressed=True, qac=qac, ayah_ref="0:0:1")
    rb = [c for c in wired["candidates"] if c["pos"] in _ROOT_BEARING_POS]
    if not rb or not all(c.get("root") == "ك ت ب" and c.get("informed_by") == ["qac"] for c in rb):
        failures.append("QAC wired path must set root FACT + informed_by:['qac'] on root-bearing candidates")
    if any(c.get("informed_by") not in (None, ["qac"]) for c in wired["candidates"]):
        failures.append("QAC informed_by must be exactly ['qac'] when present")
    if any(leak_sot.is_leak(c.get("root") or "") for c in wired["candidates"]):
        failures.append("QAC root must be leak-free")
    arb = build_morphology_lattice("tok:0", "كِتَابٌ", ksegs, True, source_addressed=False, qac=qac, ayah_ref="0:0:1")
    if any(c.get("root") for c in arb["candidates"]):
        failures.append("QAC must not populate root for a non-source-addressed (arbitrary) token")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_morphology_lattice self-test: ranked candidate lattices; ambiguity kept; score+rank; never auto_safe; source-clean")
    return 0 if not failures else 1


def emit_fixture(path):
    rows = [build_morphology_lattice(ref, surface, segs, v, sa)
            for _n, ref, surface, segs, v, sa in regression_units()]
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {"schema": SCHEMA, "generator": "tools/fusha_morphology_lattice.py --emit-fixture", "count": len(rows),
            "note": "Morphology candidate lattices (authored arbitrary tokens; no Qurʾān copy). Ranking, not a forced "
                    "single parse; root/lemma/pattern null (conservative — P3 fills deep features). Source-clean; dry-run.",
            "row_schema": ["token_ref", "candidates", "top_rank", "n_candidates", "all_unvoweled_kept"]}
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d lattices -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Build per-token morphology candidate lattices (dry-run, ambiguity-preserving).")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    ap.error("need --self-test or --emit-fixture")


if __name__ == "__main__":
    sys.exit(main())
