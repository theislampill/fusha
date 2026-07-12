#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rich-Hover Normalization Contract (norm@1) conformance checker.

Positive-spec complement to the C1-C5 defect classifier. Scans a rich-hover
whitelist snapshot and, for every row, decides conformance against the norm@1
clauses defined in docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md.

Deterministic, stdlib-only, read-only. Reports per-clause violation counts +
samples, the fully-conformant (zero-MUST-violation) headline, and overlap of
nonconforming rows with the known rich-seg debt manifest (KNOWN vs NEW debt).

Usage:
  check_rich_hover_norm.py --whitelist WL.jsonl [--debt-manifest M.jsonl] [--json OUT.json] [--samples N]
  check_rich_hover_norm.py --self-test
"""
import argparse
import collections
import hashlib
import io
import json
import re
import sys
import unicodedata

CONTRACT_VERSION = "norm@1"

# ---------------------------------------------------------------------------
# Canonical qg class set (docs/parser/qamus-grammar-v1-class-map.md, status=canonical).
CANONICAL_QG = {
    "qg-adjective", "qg-alternative", "qg-article", "qg-case", "qg-comitative",
    "qg-conditional", "qg-conjunction", "qg-demonstrative", "qg-derivative-prefix",
    "qg-dual-suffix", "qg-emphasis", "qg-exception", "qg-future-particle",
    "qg-interrogative", "qg-lam", "qg-ma-particle", "qg-negation", "qg-noun",
    "qg-noun-stem", "qg-number", "qg-oath", "qg-object-pronoun", "qg-particle",
    "qg-plural-suffix", "qg-possessive-pronoun", "qg-preposition", "qg-pronoun",
    "qg-proper-noun", "qg-question", "qg-referential-pronoun", "qg-relation",
    "qg-relative", "qg-result", "qg-result-fa", "qg-subject-pronoun", "qg-unknown",
    "qg-verb", "qg-verb-prefix", "qg-verb-stem", "qg-vocative",
}
LEGACY_QG = {"qg-negative"}  # SHOULD-not-emit legacy alias
# Root-BEARING content classes: derivable-root lexemes. Proper nouns and the generic
# qg-segment are deliberately EXCLUDED — a proper name (اللَّه) takes a proper-name rationale,
# not a triliteral root, and qg-segment is too ambiguous to assume content for a root demand.
CONTENT_CLASSES = {
    "qg-verb-stem", "qg-noun-stem", "qg-noun", "qg-adjective", "qg-verb",
}
# Non-canonical / generic classes (surfaced by N-SEG-02, not treated as root-bearing content).
GENERIC_CLASSES = {"qg-segment"}
# Rows carrying any of these are rootless-by-nature (proper name / vocative); the ROOT-hedge and
# same-surface consistency checks skip them and defer to N-ROOT-02 typed rationale.
ROOTLESS_BY_NATURE_CLASSES = {"qg-proper-noun", "qg-vocative"}
FUNCTION_CLASSES = {
    "qg-preposition", "qg-conjunction", "qg-article", "qg-particle", "qg-negation",
    "qg-ma-particle", "qg-relative", "qg-conditional", "qg-emphasis", "qg-lam",
    "qg-result-fa", "qg-result", "qg-vocative", "qg-oath", "qg-exception",
    "qg-future-particle", "qg-interrogative", "qg-question", "qg-demonstrative",
    "qg-alternative", "qg-comitative", "qg-pronoun", "qg-subject-pronoun",
    "qg-object-pronoun", "qg-possessive-pronoun", "qg-referential-pronoun",
    "qg-plural-suffix", "qg-dual-suffix", "qg-number", "qg-verb-prefix",
    "qg-derivative-prefix",
}

# ---------------------------------------------------------------------------
# N-LANG-01: internal meta-/process-language blocklist (case-insensitive substrings).
META_PHRASES = (
    "no unsupported public source label", "no unsupported public source",
    "no unsupported root", "no public root asserted", "visible piece accounted",
    "retained and accounted", "accounted for", "preserved where relevant",
    "exposes the visible", "not separately asserted", "root not certified",
    "root not asserted", "frozen row", "no lexical root added",
)
# leaked segment-label notation inside learner text, e.g. "FA:فَ", "TOK:حَقَّ", "ADJ:حَقِيقٌ".
LABEL_NOTATION_RE = re.compile(r"\b[A-Z]{1,6}:\S")

# N-ROOT-01 hedge phrases (declining a root with prose instead of asserting/typing it).
ROOT_HEDGE_PHRASES = (
    "no public root asserted", "no unsupported root", "root not certified",
    "root not asserted", "no lexical root", "not certified in frozen",
    "root uncertified", "no unsupported public source",
)
# N-PED-02 / N-LANG completeness hedges.
FEATURE_HEDGE_PHRASES = ("as context requires", "as the context requires")

# N-ROOT-02 recognized typed rootless rationale vocabulary (normalized stems).
TYPED_ROOTLESS_OK = ("function", "proper", "jamid", "jāmid", "pending", "particle_no_root")

# Root assertion regexes (mirror tools/validate_segment_completeness.py).
_ROOT_ARABIC_RE = re.compile(r"root\s+([؀-ۿ\s]+?)(?:·|\||\-| - |$)")
_ROOT_LATIN_RE = re.compile(r"root\s+[a-z](?:[\s\-][a-z]){1,}")

ARWORD = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
LATIN = re.compile(r"[A-Za-z]")


def _bare(s):
    """Fold combining diacritics and alif-wasla for surface reconstruction/grouping."""
    return "".join(c for c in (s or "") if not unicodedata.combining(c)).replace("ٱ", "ا")


def _rendered_fields(rec):
    fields = [
        rec.get("learner_explanation") or "",
        rec.get("token_contribution_gloss") or "",
        rec.get("contextual_phrase_gloss") or "",
        rec.get("morphline") or "",
    ]
    for s in rec.get("segments") or []:
        if isinstance(s, dict):
            fields.append(s.get("gloss_contribution") or "")
            fields.append(s.get("sarf_note") or "")
            fields.append(s.get("nahw_note") or "")
    return fields


def _root_asserted(rec):
    """True if a root is asserted anywhere as spaced Arabic radicals or a translit form."""
    top = rec.get("root")
    if isinstance(top, str) and len([x for x in top.split() if ARWORD.search(x)]) >= 2:
        return True
    m = rec.get("morphline") or ""
    hay = m
    for s in rec.get("segments") or []:
        if isinstance(s, dict):
            hay += " " + (s.get("sarf_note") or "")
    low = hay.lower()
    mm = _ROOT_ARABIC_RE.search(hay)
    if mm and [x for x in mm.group(1).split() if x]:
        return True
    if _ROOT_LATIN_RE.search(low):
        return True
    return False


def _rootless_by_nature(rec):
    """Proper name / vocative token: rootless-by-nature, exempt from ROOT-hedge & CONS checks."""
    if any(isinstance(s, dict) and s.get("class") in ROOTLESS_BY_NATURE_CLASSES
           for s in rec.get("segments") or []):
        return True
    raw = rec.get("surface") or ""
    d = "".join(c for c in raw if not unicodedata.combining(c))
    if d and d[0] == "ي" and len(d) > 1 and d[1] in ("ٰ", "ا"):  # vocative yāʾ (يَٰٓأَيُّهَا)
        return True
    blob = ((rec.get("morphline") or "") + " " +
            (rec.get("learner_explanation") or "")).lower()
    return any(m in blob for m in ("vocative", "proper name", "proper noun", "divine name"))


def _has_content_segment(rec):
    """A genuine root-bearing content segment, excluding proper-name/vocative rows."""
    if _rootless_by_nature(rec):
        return False
    return any(isinstance(s, dict) and s.get("class") in CONTENT_CLASSES
               for s in rec.get("segments") or [])


def _all_function(rec):
    segs = [s for s in (rec.get("segments") or []) if isinstance(s, dict)]
    return bool(segs) and all(s.get("class") in FUNCTION_CLASSES for s in segs)


def _typed_rootless_ok(rec):
    for key in ("no_root_reason", "not_clitic_reason", "rootless_rationale"):
        v = rec.get(key)
        if isinstance(v, str) and any(tok in v.lower() for tok in TYPED_ROOTLESS_OK):
            return True
    return False


# ---------------------------------------------------------------------------
# Per-row clause evaluation. Returns dict {clause_id: message} of violations.
def eval_row(rec):
    v = {}
    segs = [s for s in (rec.get("segments") or []) if isinstance(s, dict)]
    rendered = _rendered_fields(rec)
    learner = rec.get("learner_explanation") or ""
    root_asserted = _root_asserted(rec)
    content = _has_content_segment(rec)

    # ---- N-ROOT-01 (MUST): content row hedges the root instead of asserting it.
    if content and not root_asserted:
        blob = ((rec.get("morphline") or "") + " " +
                " ".join(s.get("sarf_note") or "" for s in segs)).lower()
        if any(h in blob for h in ROOT_HEDGE_PHRASES):
            v["N-ROOT-01"] = "content row declines root with hedge prose instead of asserting it"

    # ---- N-ROOT-02 (SHOULD): rootless row lacks a typed rationale (never silent).
    if not root_asserted and "N-ROOT-01" not in v:
        if not _typed_rootless_ok(rec):
            v["N-ROOT-02"] = "rootless row carries no typed rationale (function-word/proper-name/jamid-contested/pending)"

    # ---- N-LANG-01 (MUST): meta-/process-language in a rendered field.
    for f in rendered:
        fl = f.lower()
        if any(ph in fl for ph in META_PHRASES):
            v["N-LANG-01"] = "internal meta-/process-language rendered to the learner"
            break
    if "N-LANG-01" not in v and LABEL_NOTATION_RE.search(learner):
        v["N-LANG-01"] = "segment-label notation (e.g. FA:.. / TOK:.. / ADJ:..) leaked into learner text"

    # ---- N-LANG-02 (MUST): learner_explanation is an Arabic-prose dump.
    ws = [w for w in re.split(r"\s+", learner) if w]
    arn = sum(1 for w in ws if ARWORD.search(w) and not LATIN.search(w))
    lan = sum(1 for w in ws if LATIN.search(w))
    if arn + lan > 0:
        ratio = arn / (arn + lan)
        if (arn >= 6) or (arn >= 4 and ratio >= 0.6) or (lan < 3 and arn >= 3):
            v["N-LANG-02"] = "learner_explanation is Arabic-prose-dominated, not English"

    # ---- N-SEG-01 (MUST): segment surfaces reconstruct the token surface.
    if segs:
        concat = _bare("".join(s.get("surface") or "" for s in segs))
        if concat != _bare(rec.get("surface") or ""):
            v["N-SEG-01"] = "segment surfaces do not reconstruct the token surface"

    # ---- N-SEG-02 / N-COLOUR-01 (MUST): non-canonical qg class.
    bad = sorted({s.get("class") for s in segs
                  if s.get("class") not in CANONICAL_QG and s.get("class") not in LEGACY_QG})
    if bad:
        v["N-SEG-02"] = "non-canonical segment class(es): " + ", ".join(str(b) for b in bad)
    legacy = sorted({s.get("class") for s in segs if s.get("class") in LEGACY_QG})
    if legacy and "N-SEG-02" not in v:
        v["N-COLOUR-02"] = "legacy alias class(es): " + ", ".join(legacy)  # SHOULD

    # ---- N-PED-01 (MUST): every segment carries a non-empty gloss_contribution.
    if segs and any(not (s.get("gloss_contribution") or "").strip() for s in segs):
        v["N-PED-01"] = "a segment has an empty gloss_contribution"

    # ---- N-PED-02 (MUST): morphline hedges committed features.
    ml = (rec.get("morphline") or "").lower()
    if any(h in ml for h in FEATURE_HEDGE_PHRASES):
        v["N-PED-02"] = "morphline hedges features with 'as context requires'"

    return v


MUST_CLAUSES = ["N-ROOT-01", "N-LANG-01", "N-LANG-02", "N-SEG-01", "N-SEG-02",
                "N-PED-01", "N-PED-02", "N-CONS-01"]
SHOULD_CLAUSES = ["N-ROOT-02", "N-COLOUR-02"]


# ---------------------------------------------------------------------------
def _iter_rows(path):
    for line_no, line in enumerate(io.open(path, encoding="utf-8"), 1):
        line = line.rstrip("\n")
        s = line.strip()
        if not s:
            continue
        yield line_no, s, json.loads(s)


def raw_line_hash(line):
    """sha256 of the raw stripped whitelist line (rich-seg debt manifest convention)."""
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def load_debt(path):
    by_loc, by_lochash = {}, set()
    if not path:
        return by_loc, by_lochash
    for _n, _raw, r in _iter_rows(path):
        loc = r.get("canonical_location")
        if loc:
            by_loc[loc] = r.get("primary_class")
            by_lochash.add((loc, r.get("row_hash")))
    return by_loc, by_lochash


def scan(whitelist, debt_manifest=None, samples=4):
    by_loc, by_lochash = load_debt(debt_manifest)
    clause_counts = collections.Counter()
    clause_samples = collections.defaultdict(list)
    meta_phrase_counts = collections.Counter()
    rows = []              # (line_no, raw, rec, violations)
    surface_root = collections.defaultdict(lambda: {"asserted": False, "declined": []})
    total = 0

    for line_no, raw, rec in _iter_rows(whitelist):
        total += 1
        viol = eval_row(rec)
        rows.append((line_no, raw, rec, viol))
        if "N-LANG-01" in viol:
            blob = " ".join(_rendered_fields(rec)).lower()
            hit = [ph for ph in META_PHRASES if ph in blob]
            for ph in (hit or (["<label-notation>"] if LABEL_NOTATION_RE.search(
                    rec.get("learner_explanation") or "") else ["<other>"])):
                meta_phrase_counts[ph] += 1
        # accumulate same-bare-surface root state for N-CONS-01 (second pass).
        if _has_content_segment(rec):
            key = _bare(rec.get("surface") or "")
            if _root_asserted(rec):
                surface_root[key]["asserted"] = True
            elif "N-ROOT-01" in viol or "N-ROOT-02" in viol:
                surface_root[key]["declined"].append(len(rows) - 1)

    # N-CONS-01: a content row that declines its root while a same-bare-surface sibling asserts it.
    for key, st in surface_root.items():
        if st["asserted"] and st["declined"]:
            for idx in st["declined"]:
                rows[idx][3]["N-CONS-01"] = ("same-bare-surface sibling asserts a root that this "
                                             "content row declines")

    known_must = new_must = 0
    nonconf_rows = 0
    for line_no, raw, rec, viol in rows:
        for cid, msg in viol.items():
            clause_counts[cid] += 1
            if len(clause_samples[cid]) < samples:
                clause_samples[cid].append({"loc": rec.get("loc"),
                                            "surface": rec.get("surface"), "detail": msg})
        must_hit = [c for c in viol if c in MUST_CLAUSES]
        if must_hit:
            nonconf_rows += 1
            loc = rec.get("loc")
            rhash = raw_line_hash(raw)
            if (loc, rhash) in by_lochash or loc in by_loc:
                known_must += 1
            else:
                new_must += 1

    conformant = total - nonconf_rows
    return {
        "contract_version": CONTRACT_VERSION,
        "total_rows": total,
        "fully_conformant_rows": conformant,
        "nonconformant_rows_must": nonconf_rows,
        "conformance_pct": round(100.0 * conformant / total, 2) if total else 0.0,
        "clause_counts": dict(clause_counts),
        "clause_samples": {k: v for k, v in clause_samples.items()},
        "debt_overlap": {
            "debt_manifest_locs": len(by_loc),
            "nonconformant_must_in_known_debt": known_must,
            "nonconformant_must_new_debt": new_must,
        },
        "n_lang_01_phrase_breakdown": dict(meta_phrase_counts),
        "must_clauses": MUST_CLAUSES,
        "should_clauses": SHOULD_CLAUSES,
    }


def print_report(res):
    print("=" * 72)
    print("RICH-HOVER NORMALIZATION CONTRACT  %s  conformance scan" % res["contract_version"])
    print("=" * 72)
    print("total rows                 : %d" % res["total_rows"])
    print("fully norm@1-conformant    : %d  (%.2f%%)  [zero MUST violations]"
          % (res["fully_conformant_rows"], res["conformance_pct"]))
    print("nonconformant (>=1 MUST)   : %d" % res["nonconformant_rows_must"])
    ov = res["debt_overlap"]
    print("  of which KNOWN debt      : %d  (already in rich-seg-known-debt.jsonl)"
          % ov["nonconformant_must_in_known_debt"])
    print("  of which NEW debt        : %d  (only norm@1 sees these)"
          % ov["nonconformant_must_new_debt"])
    print("-" * 72)
    print("per-clause violation counts (MUST = headline; SHOULD = advisory):")
    order = res["must_clauses"] + res["should_clauses"]
    for cid in order:
        n = res["clause_counts"].get(cid, 0)
        tier = "MUST " if cid in res["must_clauses"] else "SHOULD"
        print("  [%s] %-12s %7d" % (tier, cid, n))
    for cid in sorted(res["clause_counts"]):
        if cid not in order:
            print("  [?    ] %-12s %7d" % (cid, res["clause_counts"][cid]))
    if res.get("n_lang_01_phrase_breakdown"):
        print("-" * 72)
        print("N-LANG-01 leaked-phrase breakdown:")
        for ph, n in sorted(res["n_lang_01_phrase_breakdown"].items(), key=lambda x: -x[1]):
            print("  %7d  %s" % (n, ph))
    print("-" * 72)
    for cid in order:
        s = res["clause_samples"].get(cid)
        if not s:
            continue
        print("samples %s:" % cid)
        for x in s:
            print("   %-10s %s  |  %s" % (x["loc"], x["surface"], x["detail"]))
    print("=" * 72)


# ---------------------------------------------------------------------------
def self_test():
    """Red-first: each drift shape trips its clause; the clean row passes."""
    clean = {  # حَقَّتْ 39:71:30 — the norm target
        "loc": "39:71:30", "surface": "حَقَّتْ",
        "morphline": "root ح ق ق · Form I perfect active · feminine subject marker",
        "learner_explanation": "This token contributes “became due”; the final تْ marks feminine agreement.",
        "token_contribution_gloss": "became due",
        "segments": [
            {"class": "qg-verb-stem", "label": "STEM", "surface": "حَقَّ",
             "gloss_contribution": "became due", "sarf_note": "sarf: Form I perfect active stem"},
            {"class": "qg-subject-pronoun", "label": "SUBJ", "surface": "تْ",
             "gloss_contribution": "feminine subject marker", "sarf_note": "sarf: 3fs perfect marker"}],
    }
    fahaqqa = {  # 38:14:6 — rootless-TOK hedge + qg-segment + label-notation leak
        "loc": "38:14:6", "surface": "فَحَقَّ",
        "morphline": "no public root asserted · FA:فَ + TOK:حَقَّ",
        "learner_explanation": "This word contributes \"so became due\". Visible pieces: FA:فَ + TOK:حَقَّ.",
        "token_contribution_gloss": "so became due",
        "segments": [
            {"class": "qg-result-fa", "label": "FA", "surface": "فَ", "gloss_contribution": "so/then"},
            {"class": "qg-segment", "label": "TOK", "surface": "حَقَّ",
             "gloss_contribution": "so became due"}],
    }
    haqiq = {  # 7:105:1 — meta-language leak + root hedge
        "loc": "7:105:1", "surface": "حَقيقٌ",
        "morphline": "adjectival token with visible nominative tanwin; no unsupported root added",
        "learner_explanation": "حَقيقٌ contributes \"bound\" here; visible pieces: ADJ:حَقيقٌ.",
        "token_contribution_gloss": "bound",
        "segments": [
            {"class": "qg-adjective", "label": "ADJ", "surface": "حَقيقٌ",
             "gloss_contribution": "bound",
             "sarf_note": "sarf: visible piece accounted; no unsupported public source label"}],
    }
    prose = {  # synthetic Arabic-prose-dump learner_explanation
        "loc": "9:9:9", "surface": "كلمة",
        "morphline": "root ك ل م",
        "learner_explanation": "هذه الكلمة تعني القول وهي اسم من الجذر",
        "token_contribution_gloss": "word",
        "segments": [{"class": "qg-noun-stem", "surface": "كلمة",
                      "gloss_contribution": "word"}],
    }
    emptygloss = {  # N-PED-01: empty gloss_contribution
        "loc": "1:1:1", "surface": "أَلِف", "morphline": "root x y z",
        "learner_explanation": "teaches the letter.",
        "segments": [{"class": "qg-noun-stem", "surface": "أَلِف", "gloss_contribution": ""}],
    }

    checks = [
        ("clean-haqqat passes", clean, None),
        ("fahaqqa rootless-generic -> N-ROOT-02", fahaqqa, "N-ROOT-02"),
        ("fahaqqa qg-segment -> N-SEG-02", fahaqqa, "N-SEG-02"),
        ("fahaqqa label-notation -> N-LANG-01", fahaqqa, "N-LANG-01"),
        ("haqiq meta-language -> N-LANG-01", haqiq, "N-LANG-01"),
        ("haqiq root hedge (adjective) -> N-ROOT-01", haqiq, "N-ROOT-01"),
        ("prose-dump -> N-LANG-02", prose, "N-LANG-02"),
        ("empty gloss -> N-PED-01", emptygloss, "N-PED-01"),
    ]
    ok = True
    for name, rec, expect in checks:
        viol = eval_row(rec)
        if expect is None:
            passed = not any(c in MUST_CLAUSES for c in viol)
        else:
            passed = expect in viol
        print("  %-42s %s%s" % (name, "PASS" if passed else "FAIL",
                                 "" if passed else "  got=%s" % sorted(viol)))
        ok = ok and passed

    # N-CONS-01 cross-row: a hedged sibling of a root-asserting same-surface row must trip.
    import tempfile, os
    a = dict(clean); a["surface"] = "حَقَّ"
    b = {"loc": "z:z:z", "surface": "حَقَّ",
         "morphline": "no public root asserted",
         "learner_explanation": "means became due.", "token_contribution_gloss": "due",
         "segments": [{"class": "qg-noun-stem", "surface": "حَقَّ",
                       "gloss_contribution": "due", "sarf_note": "no lexical root"}]}
    fd, tmp = tempfile.mkstemp(suffix=".jsonl")
    with io.open(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(a, ensure_ascii=False) + "\n")
        fh.write(json.dumps(b, ensure_ascii=False) + "\n")
    res = scan(tmp)
    os.unlink(tmp)
    cons = res["clause_counts"].get("N-CONS-01", 0) >= 1
    print("  %-42s %s" % ("entry-incoherent pair -> N-CONS-01", "PASS" if cons else "FAIL"))
    ok = ok and cons
    print("SELF-TEST:", "GREEN" if ok else "RED")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--whitelist", help="rich-hover whitelist .jsonl snapshot")
    ap.add_argument("--debt-manifest", help="qamus/reports/rich-seg-known-debt.jsonl (for overlap)")
    ap.add_argument("--json", help="write full result JSON here")
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.whitelist:
        ap.error("--whitelist is required unless --self-test")
    res = scan(args.whitelist, args.debt_manifest, args.samples)
    print_report(res)
    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
