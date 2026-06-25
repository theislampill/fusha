#!/usr/bin/env python3
# LEGACY: superseded by the tools/ generators (canonical machine index is existing_qamus_index.min.json; canonical graph is qamus/indexes/current/*-full.jsonl). Kept for reference; not the current canonical generator.
# -*- coding: utf-8 -*-
"""Diff the Nawawī-40 lexeme candidates against the existing Qamus index — stage 2.

Reads:
  --index   qamus/indexes/existing_qamus_index.json  (built by build_existing_qamus_index.py;
            a dict keyed by qamus:vNNN/nNNN/pNNN, each record carrying surface_ar / norm /
            norm_strict / bare / root / forms / lemma_candidate / pos_category / class …)
  --lex     corpora/nawawi40/out/nawawi40.lexeme_candidates.jsonl  (built by catalogue_nawawi40.py)

Classifies every candidate into exactly one bucket:
  already_in_qamus                  — surface (or one of an entry's forms) matches at the
                                      hamza-aware norm_strict key. Highest confidence; no work.
  new_surface_for_existing_lemma    — norm_strict is new, but the candidate's root letters
                                      (derived structurally, NOT from norm()) match a root that
                                      Qamus already has → likely a new inflected form to fold in.
  new_lemma_existing_root           — root is in Qamus but no surface/form key matches and the
                                      structural shape suggests a different lemma on that root.
  new_root_or_unknown_root          — no plausible Qamus root match at all → genuinely new lexis.
  particle_or_construction_candidate— short function word / proclitic-glued cluster. These are
                                      diacritic homographs (مَن/مِن، لِمَا/لَمَّا …) — flagged for the
                                      harakah-aware checker, never auto-certified here.
  uncertain_needs_review            — ambiguous; PENDING beats a wrong call.

GUARDRAILS BAKED IN (the qamus-highlight regressions):
  * Matching certifies ONLY at norm_strict (hamza seat kept). norm() is used for recall hints,
    never to declare "already_in_qamus" — إيمان must not collapse to أيمان, إِلَيْنَا must not
    look like root ل ي ن.
  * Short tokens (<= MIN_CONTENT letters of content) are routed to the particle bucket so the
    downstream harakah checker decides them, not a bare-letter match.
  * Root inference is deliberately conservative: a candidate is only tied to a Qamus root when
    its consonant skeleton CONTAINS that root's letters in order. Weak/hamzated roots stay
    uncertain rather than risk a verb gloss landing on a noun (رَسُولًا ≠ 'to send').
  * No gloss text is produced here — this is a routing pass only.

stdlib-only. Requires tools/normalize_ar.py. NO network, NO live writes.
  python qamus/scripts/diff_against_qamus.py \
      --index qamus/indexes/existing_qamus_index.json \
      --lex   corpora/nawawi40/out/nawawi40.lexeme_candidates.jsonl \
      --out   corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl
"""
import argparse
import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools import normalize_ar as N

SCRIPT_VERSION = "nawawi40-diff/1"

# A surface this short (in CONTENT letters after stripping proclitics) is almost always a
# particle / function word whose identity is a harakah, not letters — defer to the checker.
MIN_CONTENT = 3

# proclitics that glue onto the front of an Arabic content word (و ف ب ك ل + al-)
_PROCLITIC = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ك", "ل", "س", "أ")
# enclitic object/possessive pronouns at the tail
_ENCLITIC = ("هما", "هم", "هن", "كما", "كم", "كن", "ها", "نا", "ني", "هو", "ه", "ك", "ي")

# Arabic "weak" / hamza letters: roots containing them are unreliable under skeletonization,
# so we will NOT assert a root tie on their basis (keeps أ/ا/و/ي/ء confusions out).
_WEAK = set("اوىيءأإؤئ")


def skeleton(surface):
    """Conservative consonant skeleton of a surface form: bare() (marks gone, letters kept
    distinct) with leading proclitics and trailing enclitics peeled. Used ONLY to PROPOSE a
    root tie — never to certify a sense. Returns the stripped bare string."""
    b = N.bare(surface)
    changed = True
    while changed and len(b) > 3:
        changed = False
        for p in _PROCLITIC:
            if b.startswith(p) and len(b) - len(p) >= 3:
                b = b[len(p):]
                changed = True
                break
    changed = True
    while changed and len(b) > 3:
        changed = False
        for e in _ENCLITIC:
            if b.endswith(e) and len(b) - len(e) >= 3:
                b = b[:-len(e)]
                changed = True
                break
    return b


def contains_in_order(skel, root_letters):
    """True if every root letter appears in skel in order (subsequence). Conservative root tie."""
    it = iter(skel)
    return all(any(c == rl for c in it) for rl in root_letters)


def root_is_reliable(root_letters):
    """A root we are willing to assert a tie on: 3–4 letters, no weak/hamza letter (those make
    skeleton matching produce false positives like tying a noun to a hollow verb)."""
    return 3 <= len(root_letters) <= 4 and not any(l in _WEAK for l in root_letters)


def content_len(surface):
    """Rough count of content letters after peeling clitics — used for the particle gate."""
    return len(skeleton(surface))


def build_lookups(index):
    """Build the match structures from the Qamus index dict."""
    by_norm_strict = collections.defaultdict(list)   # norm_strict key -> [record]
    by_norm = collections.defaultdict(list)          # lenient -> [record] (recall hint only)
    roots = {}                                        # bare(root no spaces) -> [record]
    root_letter_sets = []                             # [(letters, record)]
    for addr, r in index.items():
        rec = dict(r)
        rec["_addr"] = addr
        ns = r.get("norm_strict") or ""
        if ns:
            by_norm_strict[ns].append(rec)
        # an entry's inflected forms are also valid match surfaces
        for f in r.get("forms") or []:
            fns = N.norm_strict(f)
            if fns:
                by_norm_strict[fns].append(rec)
        nm = r.get("norm") or ""
        if nm:
            by_norm[nm].append(rec)
        root = (r.get("root") or "").replace(" ", "")
        if root:
            rl = N.bare(root)
            roots.setdefault(rl, []).append(rec)
            letters = [c for c in rl if c.strip()]
            if letters:
                root_letter_sets.append((letters, rec))
    return by_norm_strict, by_norm, roots, root_letter_sets


def classify(cand, L):
    """Return (bucket, evidence-dict) for one lexeme candidate."""
    by_norm_strict, by_norm, roots, root_letter_sets = L
    surface = cand["surface_ar"]
    ns = cand.get("norm_strict") or N.norm_strict(surface)
    nm = cand.get("norm") or N.norm(surface)

    # 1) exact hamza-aware match = already in Qamus (the ONLY auto-certify path)
    hits = by_norm_strict.get(ns)
    if hits:
        return "already_in_qamus", {
            "match_key": "norm_strict",
            "matched": [h["_addr"] for h in hits][:6],
            "matched_root": [h.get("root") for h in hits][:6],
        }

    # 2) particle / short function word / clitic cluster → defer to harakah checker
    if content_len(surface) < MIN_CONTENT:
        # surface lenient recall: does a Qamus PARTICLE share the lenient key? (hint only)
        plenient = [h["_addr"] for h in by_norm.get(nm, []) if h.get("class") == "p"]
        return "particle_or_construction_candidate", {
            "reason": "short content skeleton — diacritic homograph; harakah-aware checker decides",
            "lenient_particle_hits": plenient[:6],
        }

    # 3) structural root tie (conservative, order-preserving, no weak letters)
    skel = skeleton(surface)
    skel_letters = [c for c in skel if c.strip()]
    tied = []
    for letters, rec in root_letter_sets:
        if not root_is_reliable(letters):
            continue
        if contains_in_order(skel_letters, letters):
            tied.append((letters, rec))
    if tied:
        # dedupe by entry root, keep best (shortest skeleton delta = tightest fit first)
        tied.sort(key=lambda t: (len(skel_letters) - len(t[0]), t[1]["_addr"]))
        addrs, seen = [], set()
        for letters, rec in tied:
            if rec["_addr"] not in seen:
                seen.add(rec["_addr"])
                addrs.append(rec["_addr"])
        # is the lemma itself (not just the root) already present at a different surface?
        # If a same-root entry shares the lenient key, it's likely just a new SURFACE of it.
        same_lemma = [h["_addr"] for h in by_norm.get(nm, [])]
        if same_lemma:
            return "new_surface_for_existing_lemma", {
                "lenient_lemma_hits": same_lemma[:6],
                "tied_roots": addrs[:6],
                "note": "lenient key matches an existing entry; verify hamza/harakah before folding",
            }
        return "new_lemma_existing_root", {
            "tied_roots": addrs[:6],
            "skeleton": skel,
            "note": "root present in Qamus; appears to be a new lemma on it — needs review",
        }

    # 4) lenient-only recall hint with no reliable root tie → still uncertain, never certify
    lenient = by_norm.get(nm, [])
    if lenient:
        return "uncertain_needs_review", {
            "lenient_hits": [h["_addr"] for h in lenient][:6],
            "note": "lenient match only (norm()); hamza/weak-letter risk — do NOT auto-fold",
        }

    # 5) nothing plausible → new lexis
    return "new_root_or_unknown_root", {
        "skeleton": skel,
        "note": "no reliable Qamus root contains this skeleton in order",
    }


def main():
    ap = argparse.ArgumentParser(description="Classify Nawawī-40 candidates against existing Qamus.")
    ap.add_argument("--index", default="qamus/indexes/existing_qamus_index.json")
    ap.add_argument("--lex", required=True, help="nawawi40.lexeme_candidates.jsonl")
    ap.add_argument("--out", required=True, help="output diff jsonl path")
    a = ap.parse_args()

    index = json.load(open(a.index, encoding="utf-8"))
    L = build_lookups(index)

    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    counts = collections.Counter()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

    with open(a.lex, encoding="utf-8") as lf, open(a.out, "w", encoding="utf-8") as of:
        for line in lf:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            bucket, evidence = classify(cand, L)
            counts[bucket] += 1
            rec = {
                "corpus": cand.get("corpus"),
                "surface_ar": cand["surface_ar"],
                "norm": cand.get("norm"),
                "norm_strict": cand.get("norm_strict"),
                "bare": cand.get("bare"),
                "frequency": cand.get("frequency"),
                "refs": cand.get("refs"),
                "classification": bucket,
                "evidence": evidence,
                "provenance": cand.get("provenance"),
                "classified_by": SCRIPT_VERSION,
                "generated": generated,
            }
            of.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("wrote %s" % a.out)
    for b in ("already_in_qamus", "new_surface_for_existing_lemma", "new_lemma_existing_root",
              "new_root_or_unknown_root", "particle_or_construction_candidate",
              "uncertain_needs_review"):
        print("  %-34s %d" % (b, counts.get(b, 0)))


if __name__ == "__main__":
    main()
