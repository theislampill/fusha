#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate transclusion source-SELECTION decisions (the L15 canary lesson).

Transclusion reuses an already-authored per-word analysis (a "source" whitelist
row for a surface form) at a DIFFERENT Qur'an location with the same surface.
The first live canary exposed the bug: the ad-hoc selector scored candidates by
(clean, then MAXIMUM segment count), so for an indivisible word an over-segmented
WRONG analysis out-ranked the correct single-segment one:
  * مُوسَىٰ (7:127:7) an ʿalam was split [qg-derivative-prefix, qg-noun-stem]
    (a false مُـ prefix) instead of one [qg-proper-noun].
  * ٱلَّذِى (43:83:7) a frozen relative pronoun was split [qg-article, qg-noun-stem]
    (a false definite article) instead of one [qg-relative].
The correct analyses already existed in the whitelist MAJORITY (Musa 9/15,
alladhi 34/48) — they simply lost to a more-segmented minority.

The fix, enforced here, is a principled selector: choose the CANONICAL / MAJORITY
class-signature (by OCCURRENCE COUNT, never by segment length), prefer an exact
source-address, never a generic `qg-segment` fallback where a specific class is
determinable, honour a closed-class allow-list (relative pronouns → one
qg-relative), and BLOCK (do not fan out) on ambiguity or fallback-only.

Hard properties enforced (not just the schema):
  1. chosen_signature must be one of the candidates (never invent an analysis).
  2. `majority_class_signature` basis: chosen must be the UNIQUE modal fallback-free
     signature by occurrence count; an over-segmented minority FAILs (the canary bug).
  3. no generic `qg-segment` fallback may be CHOSEN when a fallback-free candidate
     exists (نِسَآءَهُمْ: qg-noun-stem beats the generic fallback).
  4. relative-pronoun surfaces (closed class) must resolve to one [qg-relative].
  5. a `qg-article` segment must be followed by a real noun/adjective stem, never
     wrap a frozen pronoun or a verb.
  6. every class is a canonical qamus-grammar-v1 qg class (read from the schema);
     `qg-segment` is recognised only as the known generic fallback token.
  7. public fields stay source-clean (reuses the canonical FORBIDDEN_LABELS list).

`choose_source()` is the reference selector (exercised by --self-test on the four
canary cases). Dry-run; deterministic; source-clean. No live Qamus is inspected
or mutated. See docs/source-selection-policy.md.
"""
import argparse
import collections
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "qamus", "schemas", "source-selection-decision.schema.json")
SAMPLE_PATH = os.path.join(ROOT, "qamus", "examples", "source_selection.sample.jsonl")
# the canonical qg-class allow-list lives in the morphosyntax-token schema (single source)
QG_SCHEMA_PATH = os.path.join(ROOT, "qamus", "schemas", "morphosyntax-token.schema.json")

sys.path.insert(0, ROOT)
from tools.validate_public_private_boundary import FORBIDDEN_LABELS  # noqa: E402

with io.open(SCHEMA_PATH, encoding="utf-8") as _h:
    _SCHEMA = json.load(_h)
REQUIRED = _SCHEMA["required"]
_PROPS = _SCHEMA["properties"]
SELECTION_BASES = _PROPS["selection_basis"]["enum"]

with io.open(QG_SCHEMA_PATH, encoding="utf-8") as _h:
    _QG = json.load(_h)
# canonical qg classes; qg-segment is the known runtime GENERIC FALLBACK (deliberately
# NOT in the canonical enum) — recognised so a candidate may list it, gated so it is
# never CHOSEN where a specific class is determinable.
CANONICAL_QG = set(_QG["properties"]["display"]["properties"]["segments"]["items"]["properties"]["class"]["enum"])
GENERIC_FALLBACK = "qg-segment"
VALID_QG = CANONICAL_QG | {GENERIC_FALLBACK}
STEM_CLASSES = {"qg-noun-stem", "qg-noun", "qg-adjective", "qg-proper-noun"}

# Coarse grammatical family of a segment class. Used ONLY to tell an over-segmentation
# VARIANT of one word (safe to majority-vote: e.g. مُوسَىٰ as [qg-proper-noun] vs the false
# [qg-derivative-prefix, qg-noun-stem]) apart from a genuine same-surface HOMOGRAPH (must be
# authored per-occurrence, never majority-voted: e.g. مَا as relative vs negative vs maṣdariyya).
# Affixes are skipped when finding a signature's head content class.
_AFFIX_CLASSES = {"qg-article", "qg-derivative-prefix", "qg-verb-prefix", "qg-case",
                  "qg-dual-suffix", "qg-plural-suffix", "qg-possessive-pronoun",
                  "qg-object-pronoun", "qg-subject-pronoun", "qg-lam", "qg-result-fa"}
_FAMILY = {
    "qg-proper-noun": "nominal", "qg-noun": "nominal", "qg-noun-stem": "nominal", "qg-adjective": "nominal",
    "qg-verb": "verbal", "qg-verb-stem": "verbal",
    "qg-relative": "relative",
    "qg-demonstrative": "pronoun",
    "qg-pronoun": "pronoun", "qg-possessive-pronoun": "pronoun",
    "qg-object-pronoun": "pronoun", "qg-subject-pronoun": "pronoun",
    "qg-negative": "particle", "qg-negation": "particle", "qg-preposition": "particle",
    "qg-conjunction": "particle", "qg-ma-particle": "particle", "qg-particle": "particle",
    "qg-oath": "particle", "qg-vocative": "particle", "qg-exception": "particle",
    "qg-result": "particle", "qg-relation": "particle", "qg-comitative": "particle",
}
FUNCTION_FAMILIES = {"relative", "pronoun", "particle"}

PUBLIC_FIELDS = ("surface", "surface_norm", "note")

# closed-class relative pronouns → exactly one qg-relative segment (never article+noun).
_DIAC = "".join(chr(c) for c in list(range(0x064B, 0x0653)) + [0x0670, 0x0640])


def _norm(s):
    """Strip harakat / superscript-alif / tatweel and fold the alif/hamza variants."""
    s = s or ""
    s = "".join(ch for ch in s if ch not in _DIAC)
    for a in "أإآٱ":
        s = s.replace(a, "ا")
    s = s.replace("ى", "ي")  # fold alif maqsura -> ya
    return s


# Scoped to the Qurʾānic-attested definite relative pronouns (closed class). Archaic
# emphatic-dual forms (اللتيا/اللذيا) do not occur in the corpus and are intentionally omitted.
RELATIVE_ALLOWLIST = {_norm(x) for x in (
    "الذي", "التي", "الذين", "اللذان", "اللذين", "اللتان", "اللتين",
    "اللاتي", "اللائي", "اللواتي",
)}


def _sig(seq):
    return tuple(seq or [])


def _fallback_free(candidates):
    return [c for c in candidates if GENERIC_FALLBACK not in (c.get("class_signature") or [])]


def _majority_signature(candidates):
    """Modal class-signature by OCCURRENCE COUNT among fallback-free candidates.
    Returns (signature_list, unique:boolean) or (None, False) if none/tie."""
    agg = collections.defaultdict(int)
    for c in _fallback_free(candidates):
        agg[_sig(c.get("class_signature"))] += int(c.get("count") or 1)
    if not agg:
        return None, False
    ranked = sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(ranked) >= 2 and ranked[0][1] == ranked[1][1]:
        return list(ranked[0][0]), False  # tie -> not unique
    return list(ranked[0][0]), True


def _family(signature):
    """Grammatical family of a signature's HEAD content class (affixes skipped)."""
    for c in signature:
        if c not in _AFFIX_CLASSES and c != GENERIC_FALLBACK:
            return _FAMILY.get(c, c)
    return _FAMILY.get(signature[0], signature[0]) if signature else None


def _homograph_block(candidates):
    """A same-surface set whose fallback-free candidates carry more than one DISTINCT
    analysis is a homograph that must be authored per-occurrence — never majority-voted —
    when a function-word family is involved (relative/pronoun/particle: e.g. مَا) OR when the
    analyses span more than one grammatical family (e.g. a noun-vs-verb homograph). A single
    content family with several segmentation variants (مُوسَىٰ) is NOT a homograph."""
    sigs = {_sig(c.get("class_signature")) for c in _fallback_free(candidates)}
    if len(sigs) <= 1:
        return None
    fams = {_family(s) for s in sigs}
    if (fams & FUNCTION_FAMILIES) or len(fams) > 1:
        return "ambiguous_homograph_surface"
    return None


def choose_source(surface, candidates):
    """Reference selector: the CORRECT heuristic (majority/canonical, never most-segmented).
    Returns {"chosen_signature", "selection_basis"} or {"block": <reason>}."""
    norm = _norm(surface)
    if norm in RELATIVE_ALLOWLIST:
        for c in candidates:
            if _sig(c.get("class_signature")) == ("qg-relative",):
                return {"chosen_signature": ["qg-relative"], "selection_basis": "canonical_allowlist"}
        return {"block": "relative_canonical_absent"}
    ff = _fallback_free(candidates)
    if not ff:
        return {"block": "only_generic_fallback"}  # nothing specific to reuse -> author it
    hb = _homograph_block(candidates)
    if hb:
        return {"block": hb}  # genuine homograph -> author per-occurrence, never majority-vote
    sig, unique = _majority_signature(candidates)
    if not unique:
        return {"block": "ambiguous_no_majority"}
    return {"chosen_signature": sig, "selection_basis": "majority_class_signature"}


def _article_structure_ok(signature):
    """A qg-article must be immediately followed by a real noun/adjective stem."""
    for i, cls in enumerate(signature):
        if cls == "qg-article":
            if i + 1 >= len(signature) or signature[i + 1] not in STEM_CLASSES:
                return False
    return True


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_row(row):
    errors = []
    if not isinstance(row, dict):
        return ["source-selection decision must be a JSON object"]

    for field in REQUIRED:
        if field not in row:
            errors.append("missing required field %r" % field)
    if row.get("schema") != "qamus.source_selection_decision.v1":
        errors.append("schema must be 'qamus.source_selection_decision.v1'")
    if row.get("selection_basis") not in SELECTION_BASES:
        errors.append("selection_basis=%r not in %s" % (row.get("selection_basis"), SELECTION_BASES))
    if "public_safe" in row and not isinstance(row.get("public_safe"), bool):
        errors.append("public_safe must be a boolean")
    extra = set(row) - set(_PROPS)
    if extra:
        errors.append("unexpected field(s): %s" % sorted(extra))
    if errors:
        return errors  # structural failures make the semantic checks meaningless

    candidates = row.get("candidates") or []
    cand_sigs = [_sig(c.get("class_signature")) for c in candidates]
    chosen = _sig(row.get("chosen_signature"))
    fanout = row.get("fanout_allowed", True)

    # (6) every class must be canonical (or the recognised generic fallback)
    for cls in set(chosen) | {c for s in cand_sigs for c in s}:
        if cls not in VALID_QG:
            errors.append("unknown qg class %r (not in qamus-grammar-v1)" % cls)

    # (1) chosen must be one of the candidates (never invent an analysis)
    if chosen not in cand_sigs:
        errors.append("chosen_signature %s is not among the candidates %s"
                      % (list(chosen), [list(s) for s in cand_sigs]))

    # (5) qg-article must wrap a real noun/adjective stem
    if not _article_structure_ok(chosen):
        errors.append("qg-article must be followed by a noun/adjective stem, not %s" % list(chosen))

    norm = _norm(row.get("surface_norm") or row.get("surface"))

    # (4) relative-pronoun surfaces must resolve to exactly one qg-relative
    if norm in RELATIVE_ALLOWLIST and chosen != ("qg-relative",):
        errors.append("relative pronoun surface must be a single [qg-relative], got %s" % list(chosen))

    # (3) no generic fallback may be CHOSEN when a fallback-free candidate exists
    if fanout and GENERIC_FALLBACK in chosen and _fallback_free(candidates):
        errors.append("chose generic %r over a determinable specific analysis" % GENERIC_FALLBACK)

    basis = row.get("selection_basis")
    if basis == "majority_class_signature":
        # (homograph guard) a genuine same-surface homograph may not be majority-voted at all
        if _homograph_block(candidates):
            errors.append("ambiguous homograph surface: author per-occurrence, do not majority-vote "
                          "(fallback-free candidates span multiple analyses/families)")
        else:
            # (2) the anti-most-segmented rule: chosen must be the UNIQUE modal fallback-free signature
            maj, unique = _majority_signature(candidates)
            if not unique:
                errors.append("majority_class_signature basis but candidates have no unique majority")
            elif chosen != _sig(maj):
                errors.append("chosen %s is not the majority class-signature %s (over-segmented minority?)"
                              % (list(chosen), list(maj)))
    elif basis == "source_address_exact":
        loc = row.get("chosen_source_loc")
        if not loc:
            errors.append("source_address_exact basis requires chosen_source_loc")
        else:
            at_loc = [c for c in candidates if c.get("source_loc") == loc]
            if not at_loc:
                errors.append("chosen_source_loc %r is not a candidate source_loc %s"
                              % (loc, sorted(l for l in {c.get("source_loc") for c in candidates} if l)))
            elif not any(_sig(c.get("class_signature")) == chosen for c in at_loc):
                # the cited occurrence must actually carry the chosen analysis (no self-inconsistency)
                errors.append("chosen_signature %s does not match the candidate authored at %s (self-inconsistent)"
                              % (list(chosen), loc))
            else:
                # an exact cite may NOT launder a known over-segmented minority when a clear,
                # non-homograph majority exists (the canary bug through a side door)
                maj, unique = _majority_signature(candidates)
                if unique and _sig(maj) != chosen and not _homograph_block(candidates):
                    errors.append("source_address_exact cites non-majority %s while a clear majority %s "
                                  "exists and the surface is not a homograph (over-segmentation laundering)"
                                  % (list(chosen), list(maj)))
    elif basis == "canonical_allowlist":
        if norm not in RELATIVE_ALLOWLIST:
            errors.append("canonical_allowlist basis only valid for a closed-class allow-list surface")

    public_blob = json.dumps({k: row.get(k) for k in PUBLIC_FIELDS}, ensure_ascii=False).lower()
    for label in FORBIDDEN_LABELS:
        if label in public_blob:
            errors.append("public field leaks forbidden label %r" % label)
    return errors


def validate_rows(rows):
    errors = []
    for index, row in enumerate(rows):
        for err in validate_row(row):
            errors.append("row[%d]: %s" % (index, err))
    return errors


def _decision(surface, surface_norm, candidates, chosen, basis, **extra):
    row = {
        "schema": "qamus.source_selection_decision.v1",
        "surface": surface, "surface_norm": surface_norm,
        "candidates": candidates, "chosen_signature": chosen,
        "selection_basis": basis, "public_safe": True,
    }
    row.update(extra)
    return row


def self_test():
    # ---- choose_source() on the four canary cases ----
    # 1. مُوسَىٰ: proper-noun majority (9) beats the over-segmented mu-prefix minority (1)
    musa = [{"class_signature": ["qg-proper-noun"], "count": 9},
            {"class_signature": ["qg-derivative-prefix", "qg-noun-stem"], "count": 1},
            {"class_signature": ["qg-segment"], "count": 5}]
    r = choose_source("مُوسَىٰ", musa)
    if r.get("chosen_signature") != ["qg-proper-noun"]:
        print("SELF-TEST FAIL Musa choose_source ->", r); return 1
    # 2. ٱلَّذِى: relative allow-list -> single qg-relative (not article+noun)
    alladhi = [{"class_signature": ["qg-relative"], "count": 34},
               {"class_signature": ["qg-article", "qg-noun-stem"], "count": 13}]
    r = choose_source("ٱلَّذِى", alladhi)
    if r.get("chosen_signature") != ["qg-relative"] or r.get("selection_basis") != "canonical_allowlist":
        print("SELF-TEST FAIL alladhi choose_source ->", r); return 1
    # 3. نِسَآءَهُمْ: fallback-free noun-stem preferred over the generic fallback
    nisa = [{"class_signature": ["qg-noun-stem", "qg-possessive-pronoun"], "count": 2},
            {"class_signature": ["qg-segment", "qg-possessive-pronoun"], "count": 1}]
    r = choose_source("نِسَآءَهُمْ", nisa)
    if r.get("chosen_signature") != ["qg-noun-stem", "qg-possessive-pronoun"]:
        print("SELF-TEST FAIL nisa choose_source ->", r); return 1
    # 4. a GENUINELY segmented verb: the multi-segment majority must be KEPT (not collapsed)
    verb = [{"class_signature": ["qg-verb-stem", "qg-subject-pronoun", "qg-object-pronoun"], "count": 3},
            {"class_signature": ["qg-verb"], "count": 1}]
    r = choose_source("اقْتَرَفْتُمُوهَا", verb)
    if r.get("chosen_signature") != ["qg-verb-stem", "qg-subject-pronoun", "qg-object-pronoun"]:
        print("SELF-TEST FAIL genuine-segmentation choose_source ->", r); return 1
    # block cases
    if choose_source("رَجُلٌ", [{"class_signature": ["qg-segment"], "count": 3}]).get("block") != "only_generic_fallback":
        print("SELF-TEST FAIL only_generic_fallback not blocked"); return 1
    # homograph across families (noun vs verb) -> author per-occurrence, not majority
    if choose_source("عَيْنٌ", [{"class_signature": ["qg-noun-stem"], "count": 5},
                                {"class_signature": ["qg-verb-stem"], "count": 3}]).get("block") != "ambiguous_homograph_surface":
        print("SELF-TEST FAIL noun/verb homograph not blocked"); return 1
    # function-word homograph (مَا relative vs negative vs masdariyya) -> author per-occurrence
    ma = [{"class_signature": ["qg-relative"], "count": 400},
          {"class_signature": ["qg-negative"], "count": 120},
          {"class_signature": ["qg-ma-particle"], "count": 100}]
    if choose_source("مَا", ma).get("block") != "ambiguous_homograph_surface":
        print("SELF-TEST FAIL ma homograph not blocked ->", choose_source("مَا", ma)); return 1
    # tie WITHIN one content family (segmentation variants, equal count) -> no unique majority
    if choose_source("قَامَ", [{"class_signature": ["qg-verb-stem"], "count": 2},
                                {"class_signature": ["qg-verb-prefix", "qg-verb-stem"], "count": 2}]).get("block") != "ambiguous_no_majority":
        print("SELF-TEST FAIL ambiguous_no_majority not blocked"); return 1

    # ---- validate_row() accept side ----
    good = [
        _decision("مُوسَىٰ", "موسى", musa, ["qg-proper-noun"], "majority_class_signature"),
        _decision("ٱلَّذِى", "الذي", alladhi, ["qg-relative"], "canonical_allowlist"),
        _decision("نِسَآءَهُمْ", "نساءهم", nisa, ["qg-noun-stem", "qg-possessive-pronoun"], "majority_class_signature"),
        _decision("اقْتَرَفْتُمُوهَا", "اقترفتموها", verb,
                  ["qg-verb-stem", "qg-subject-pronoun", "qg-object-pronoun"], "majority_class_signature"),
    ]
    for g in good:
        if validate_row(g):
            print("SELF-TEST FAIL good decision:", g["surface"], validate_row(g)); return 1

    # ---- validate_row() reject side (each one violation) ----
    # over-segmented minority chosen over the majority (the canary bug)
    bad = _decision("مُوسَىٰ", "موسى", musa, ["qg-derivative-prefix", "qg-noun-stem"], "majority_class_signature")
    if not any("majority class-signature" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL Musa over-segmentation not caught"); return 1
    # relative pronoun mis-classed as article+noun
    bad = _decision("ٱلَّذِى", "الذي", alladhi, ["qg-article", "qg-noun-stem"], "majority_class_signature")
    if not any("single [qg-relative]" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL alladhi article+noun not caught"); return 1
    # generic fallback chosen where a specific class is determinable
    bad = _decision("نِسَآءَهُمْ", "نساءهم", nisa, ["qg-segment", "qg-possessive-pronoun"], "majority_class_signature")
    if not any("generic" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL nisa generic fallback not caught"); return 1
    # qg-article wrapping a verb stem
    bad = _decision("س", "س", [{"class_signature": ["qg-article", "qg-verb-stem"], "count": 1}],
                    ["qg-article", "qg-verb-stem"], "majority_class_signature")
    if not any("qg-article must be followed" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL article-structure not caught"); return 1
    # invented analysis (not among candidates)
    bad = _decision("قَالَ", "قال", [{"class_signature": ["qg-verb-stem"], "count": 5}],
                    ["qg-verb"], "majority_class_signature")
    if not any("not among the candidates" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL invented-analysis not caught"); return 1
    # public leak in a public field
    bad = _decision("قَالَ", "informed_by qac", [{"class_signature": ["qg-verb-stem"], "count": 5}],
                    ["qg-verb-stem"], "majority_class_signature")
    if not any("forbidden label" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL public leak not caught"); return 1
    # homograph surface majority-voted -> reject (a function-word homograph cannot be canonicalized)
    bad = _decision("مَا", "ما", ma, ["qg-relative"], "majority_class_signature")
    if not any("homograph" in e for e in validate_row(bad)):
        print("SELF-TEST FAIL ma homograph decision not caught"); return 1
    # source_address_exact self-inconsistency: cite one loc but keep another candidate's signature
    musa_locs = [{"class_signature": ["qg-proper-noun"], "count": 9, "source_loc": "20:9:2"},
                 {"class_signature": ["qg-derivative-prefix", "qg-noun-stem"], "count": 1, "source_loc": "7:127:7"}]
    launder = _decision("مُوسَىٰ", "موسى", musa_locs, ["qg-derivative-prefix", "qg-noun-stem"],
                        "source_address_exact", chosen_source_loc="20:9:2")
    if not any("self-inconsistent" in e for e in validate_row(launder)):
        print("SELF-TEST FAIL source_address_exact self-inconsistency not caught"); return 1
    # source_address_exact cannot launder a self-consistent over-segmented minority over a clear majority
    launder2 = _decision("مُوسَىٰ", "موسى", musa_locs, ["qg-derivative-prefix", "qg-noun-stem"],
                         "source_address_exact", chosen_source_loc="7:127:7")
    if not any("laundering" in e for e in validate_row(launder2)):
        print("SELF-TEST FAIL source_address_exact over-segmentation laundering not caught"); return 1

    # file-backed reject fixtures: every row MUST fail
    reject_path = os.path.join(ROOT, "qamus", "examples", "source_selection.reject.sample.jsonl")
    if os.path.exists(reject_path):
        for i, r in enumerate(read_jsonl(reject_path)):
            if not validate_row(r):
                print("SELF-TEST FAIL reject fixture row %d unexpectedly passed" % i); return 1

    print("PASS - source-selection validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate transclusion source-selection decisions.")
    parser.add_argument("path", nargs="?", help="JSONL of source-selection decision rows")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        parser.error("path is required unless --self-test is used")
    errors = validate_rows(read_jsonl(args.path))
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  - " + err)
        raise SystemExit(1)
    print("PASS - source-selection decisions prefer the canonical/majority class-signature")


if __name__ == "__main__":
    main()
