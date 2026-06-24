#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit reviewable candidate payloads from the Nawawī-40 diff — stage 3 (final pilot step).

Reads the diff jsonl (from diff_against_qamus.py) and splits it into three review-ready
streams. NOTHING here is published. Every record is status:"candidate",
review_status:"needs_review", source_scope:["nawawi40"]. The downstream human/owner review
is the gate; this script only stages the work and NEVER duplicates an existing Qamus entry.

Reads:
  --diff    corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl
  --index   qamus/indexes/existing_qamus_index.json   (to attach the existing entry an
            augment should hang off, and to hard-block duplicates)

Writes (to --out):
  nawawi40.new_entries.candidate.jsonl
      One proposed NEW Qamus entry per genuinely new lemma/root
      (buckets new_lemma_existing_root, new_root_or_unknown_root). Carries an EMPTY
      structured shell matching the Qamus schema (root/headword/senses/usage) for a human
      to fill. An authored DRAFT gloss is included ONLY when --draft-glosses is passed and a
      safe heuristic applies; it is marked draft + gloss_source:"authored-draft" and is NEVER
      copied from any external dictionary. Default: gloss left empty (PENDING > wrong gloss).
  nawawi40.occurrence_augments.candidate.jsonl
      For new_surface_for_existing_lemma: a proposal to ADD this surface/occurrence to an
      EXISTING entry (no new entry), pinned to that entry's source_address.
  nawawi40.review_queue.jsonl
      Every candidate that needs a human eye, including the particle/homograph and uncertain
      buckets, with the routing reason. already_in_qamus is NOT queued (no work).

PUBLIC-ARTIFACT RULE: any record that could ever surface in the public hover artifact carries
{"src":"qamus","kind":"authored"} provenance and a draft gloss is authored-only. External
references may appear solely as `informed_by` labels (named, never quoted).

stdlib-only. Requires tools/normalize_ar.py. NO network, NO live writes.
  python qamus/scripts/make_candidate_payloads.py \
      --diff  corpora/nawawi40/out/nawawi40.diff_against_quran_qamus.jsonl \
      --index qamus/indexes/existing_qamus_index.json \
      --out   qamus/candidates/nawawi40
"""
import argparse
import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools import normalize_ar as N

SCRIPT_VERSION = "nawawi40-payloads/1"

NEW_ENTRY_BUCKETS = {"new_lemma_existing_root", "new_root_or_unknown_root"}
AUGMENT_BUCKETS = {"new_surface_for_existing_lemma"}
# buckets that go to the human queue (everything except a clean already_in_qamus)
QUEUE_SKIP = {"already_in_qamus"}


def empty_entry_shell():
    """A new-entry shell mirroring the Qamus entry schema fields, all blank for a human."""
    return {
        "root": "",                 # to be confirmed by reviewer (space-separated radicals)
        "headword": "",
        "translit": "",
        "section": "",
        "category": "",             # Verbs / Nouns / Particles … (reviewer sets)
        "definition": "",
        "total_uses": None,         # cross-corpus count is reviewer/aggregator work
        "senses": [],               # [{"gloss": "...", "kind": "authored", "src": "qamus"}]
        "usage": [],                # [{"forms": [...], "examples": [{"ref": "...", "text": ""}]}]
        "notes": "",
        "tags": "",                 # comma-string by Qamus convention
    }


def safe_draft_gloss(cand):
    """Optional, conservative authored DRAFT gloss. Returns "" unless a SAFE pattern applies.
    Deliberately tiny: we refuse to guess part-of-speech-sensitive glosses. Never copies
    external text. The only thing we are willing to assert is a neutral placeholder describing
    the form, leaving the meaning to the human (PENDING beats a wrong gloss)."""
    # We do NOT auto-author meanings. A draft gloss here would risk landing a verb gloss on a
    # noun or a name (رَسُولًا ≠ 'to send'; مُحَمَّد ≠ 'to praise'). Return empty by design;
    # the flag exists so a future, vetted heuristic can slot in without changing callers.
    return ""


def main():
    ap = argparse.ArgumentParser(description="Stage Nawawī-40 candidate payloads (no publish).")
    ap.add_argument("--diff", required=True)
    ap.add_argument("--index", default="qamus/indexes/existing_qamus_index.json")
    ap.add_argument("--out", required=True, help="output directory for candidate jsonl files")
    ap.add_argument("--draft-glosses", action="store_true",
                    help="attach conservative authored DRAFT glosses where a safe heuristic "
                         "applies (default off; never copies external gloss text)")
    a = ap.parse_args()

    index = json.load(open(a.index, encoding="utf-8"))
    # duplicate guard: every norm_strict key already covered by Qamus (surface + forms)
    existing_keys = set()
    addr_by_norm = collections.defaultdict(list)
    for addr, r in index.items():
        for key in [r.get("norm_strict")] + [N.norm_strict(f) for f in (r.get("forms") or [])]:
            if key:
                existing_keys.add(key)
        if r.get("norm"):
            addr_by_norm[r["norm"]].append(addr)

    os.makedirs(a.out, exist_ok=True)
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    p_new = os.path.join(a.out, "nawawi40.new_entries.candidate.jsonl")
    p_aug = os.path.join(a.out, "nawawi40.occurrence_augments.candidate.jsonl")
    p_q = os.path.join(a.out, "nawawi40.review_queue.jsonl")

    counts = collections.Counter()
    seen_new_keys = set()   # in-run dedupe of proposed new entries by norm_strict

    f_new = open(p_new, "w", encoding="utf-8")
    f_aug = open(p_aug, "w", encoding="utf-8")
    f_q = open(p_q, "w", encoding="utf-8")
    try:
        for line in open(a.diff, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            bucket = cand.get("classification")
            ns = cand.get("norm_strict") or N.norm_strict(cand["surface_ar"])

            base_prov = {
                "source_scope": ["nawawi40"],
                "refs": cand.get("refs") or [],
                "frequency": cand.get("frequency"),
                "classification": bucket,
                "informed_by": [],           # name external evidence here; NEVER quote it
                "staged_by": SCRIPT_VERSION,
                "generated": generated,
                "access_method": (cand.get("provenance") or {}).get("access_method", ""),
            }

            # --- review queue: everything that needs a human eye ---
            if bucket not in QUEUE_SKIP:
                counts["queued"] += 1
                f_q.write(json.dumps({
                    "surface_ar": cand["surface_ar"],
                    "norm": cand.get("norm"),
                    "norm_strict": ns,
                    "bare": cand.get("bare"),
                    "classification": bucket,
                    "evidence": cand.get("evidence"),
                    "frequency": cand.get("frequency"),
                    "refs": cand.get("refs"),
                    "status": "candidate",
                    "review_status": "needs_review",
                    "source_scope": ["nawawi40"],
                    "routing_note": _routing_note(bucket),
                    "provenance": base_prov,
                }, ensure_ascii=False) + "\n")

            # --- occurrence augments for existing lemmas ---
            if bucket in AUGMENT_BUCKETS:
                # attach to the existing entry/entries the diff tied it to
                ev = cand.get("evidence") or {}
                targets = ev.get("lenient_lemma_hits") or ev.get("tied_roots") or []
                targets = [t for t in targets if t in index]
                counts["augment"] += 1
                f_aug.write(json.dumps({
                    "op": "add_occurrence",
                    "target_entries": targets,                 # source_address keys in Qamus
                    "target_source_address": [index[t]["source_address"] for t in targets],
                    "surface_ar": cand["surface_ar"],
                    "norm_strict": ns,
                    "refs": cand.get("refs"),
                    "frequency": cand.get("frequency"),
                    "status": "candidate",
                    "review_status": "needs_review",
                    "source_scope": ["nawawi40"],
                    "duplicate_of_existing_surface": ns in existing_keys,
                    "note": "propose adding this surface/occurrence to the existing entry; "
                            "verify hamza+harakah before folding",
                    "provenance": base_prov,
                }, ensure_ascii=False) + "\n")

            # --- new entry candidates (genuinely new lemma/root) ---
            if bucket in NEW_ENTRY_BUCKETS:
                if ns in existing_keys:
                    counts["new_blocked_dup_qamus"] += 1
                    continue                                   # never duplicate Qamus
                if ns in seen_new_keys:
                    counts["new_blocked_dup_run"] += 1
                    continue                                   # collapse repeats within the run
                seen_new_keys.add(ns)
                shell = empty_entry_shell()
                draft = safe_draft_gloss(cand) if a.draft_glosses else ""
                if draft:
                    shell["senses"] = [{
                        "gloss": draft,
                        "kind": "authored",
                        "src": "qamus",
                        "draft": True,
                        "gloss_source": "authored-draft",
                    }]
                # seed the first observed surface as a usage form for the reviewer
                shell["usage"] = [{
                    "forms": [cand["surface_ar"]],
                    "examples": [{"ref": r, "text": ""} for r in (cand.get("refs") or [])[:8]],
                }]
                counts["new_entry"] += 1
                f_new.write(json.dumps({
                    "candidate_surface_ar": cand["surface_ar"],
                    "norm": cand.get("norm"),
                    "norm_strict": ns,
                    "bare": cand.get("bare"),
                    "classification": bucket,
                    "evidence": cand.get("evidence"),
                    "status": "candidate",
                    "review_status": "needs_review",
                    "source_scope": ["nawawi40"],
                    "public_provenance": {"src": "qamus", "kind": "authored"},
                    "entry": shell,
                    "frequency": cand.get("frequency"),
                    "refs": cand.get("refs"),
                    "provenance": base_prov,
                }, ensure_ascii=False) + "\n")
    finally:
        f_new.close()
        f_aug.close()
        f_q.close()

    print("wrote %s (%d new-entry candidates)" % (p_new, counts["new_entry"]))
    print("wrote %s (%d occurrence augments)" % (p_aug, counts["augment"]))
    print("wrote %s (%d queued for review)" % (p_q, counts["queued"]))
    if counts["new_blocked_dup_qamus"] or counts["new_blocked_dup_run"]:
        print("dedupe: blocked %d already-in-Qamus + %d in-run repeats"
              % (counts["new_blocked_dup_qamus"], counts["new_blocked_dup_run"]))


def _routing_note(bucket):
    return {
        "new_surface_for_existing_lemma":
            "verify hamza/harakah, then fold as a new occurrence on the existing entry",
        "new_lemma_existing_root":
            "root exists in Qamus; confirm this is a distinct lemma before creating an entry",
        "new_root_or_unknown_root":
            "no Qamus root match; confirm radicals and author an original entry",
        "particle_or_construction_candidate":
            "diacritic homograph — decide with the harakah-aware checker (normalize_ar), "
            "never by bare letters",
        "uncertain_needs_review":
            "lenient match only; weak/hamza-letter risk — do not auto-fold",
    }.get(bucket, "review")


if __name__ == "__main__":
    main()
