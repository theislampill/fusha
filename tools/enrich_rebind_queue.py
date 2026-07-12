#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic root-lookup enrichment of the class-2 content-host rebind queue.

Reads the frozen v1 queue (append-queue/class2/rebind-queue.jsonl, 2,330 rows) and
emits an ENRICHED, candidate-only v2 artifact next to it:

  * rebind-queue.v2.jsonl        - one enriched row per v1 row (same order)
  * rebind-queue.v2.report.json  - completeness before/after + calibration agreement
  * rebind-queue.v2.manifest.json- sha256 pins for every input + the two outputs

Design boundary (RM-40, D-08):
  * candidate-generation only. The read-only Qamus dataset, the v1 queue, and every
    committed index are NEVER mutated. No paradigm generation: roots are DERIVED by
    LOOKUP against committed surfaces (documented forms, clitic-segmented stems) and,
    as a labelled recall fallback, by matching a committed root's radicals as an
    ordered subsequence of the observed surface skeleton against by-root.json.
  * ambiguity preserving: every row lists ALL derived candidate roots and ALL
    proposed host entries; nothing is force-picked. Homograph rows surface every
    competing root.

The enrichment fixes the two O1 calibration defects:
  1. proposed_host_entries EMPTY / decoy-only -> populated by root lookup.
  2. existing carriers that gloss a NEIGHBOURING token -> flagged neighbor_distractor
     using the build_two_vote_packets example-window fingerprint plus root agreement.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.normalize_ar import bare, norm_strict  # noqa: E402
from tools.fusha_text_check import segment_candidates  # noqa: E402

# ---------------------------------------------------------------------------
# committed inputs (all sha-pinned in the manifest)
# ---------------------------------------------------------------------------
V1_QUEUE = "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.jsonl"
LOC_SURFACE = "qamus/indexes/quran-loc-surface/index.jsonl"
ENTRIES = "qamus/data/current/entries.jsonl"
BY_ROOT = "qamus/indexes/current/by-root.json"
BY_NORM_SURFACE = "qamus/indexes/current/by-normalized-surface.json"
APPEND_QUEUE = "qamus/indexes/largelexicon/append-queue/append-queue.jsonl"
CROSSWALK_GLOB = "qamus/indexes/largelexicon/qword-crosswalk/*.jsonl"

OUT_QUEUE = "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.v2.jsonl"
OUT_REPORT = "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.v2.report.json"
OUT_MANIFEST = "qamus/indexes/largelexicon/append-queue/class2/rebind-queue.v2.manifest.json"

V2_SCHEMA = "qamus.class2_rebind_candidate.v2"

# Confidence ranks: lower number == stronger derivation evidence.
CONFIDENCE_RANK = {
    "documented_form_exact": 0,
    "norm_strict_surface_fallback": 1,
    "clitic_segmented_form": 2,
    "root_skeleton_strict": 3,
    "root_skeleton_weak_folded": 4,
}

# Tiers that anchor to a documented surface (verbatim form or a legal clitic-peel of
# it) rather than to a fuzzy skeleton/co-occurrence. A host reached by one of these is
# treated as an existing_entry_rebind; otherwise the host is candidate-only.
SURFACE_ANCHORED_TIERS = frozenset({
    "documented_form_exact",
    "clitic_segmented_form",
    "norm_strict_surface_fallback",
})

# Arabic weak / hamza-bearing letters folded to a single class for the recall tier.
_WEAK = set("اويىءأإؤئآ")

_QWORD_RE = re.compile(r"llx-qword-([0-9a-fA-F]+)-(\d+)-(\d+)-(\d+)")


# ---------------------------------------------------------------------------
# io helpers (deterministic)
# ---------------------------------------------------------------------------
def _p(rel):
    return os.path.join(ROOT, rel)


def read_jsonl(rel):
    with io.open(_p(rel), encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_json(rel):
    with io.open(_p(rel), encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(rel):
    digest = hashlib.sha256()
    with io.open(_p(rel), "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def write_jsonl_bytes(rows):
    buf = io.StringIO()
    for row in rows:
        buf.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        buf.write("\n")
    return buf.getvalue().encode("utf-8")


def write_json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def loc_key(loc):
    return tuple(int(part) for part in str(loc).split(":"))


# ---------------------------------------------------------------------------
# morphology surfaces (lookup only)
# ---------------------------------------------------------------------------
def _cls(ch):
    return "W" if ch in _WEAK else ch


def skeleton(surface):
    """Class-folded consonant skeleton of the display surface (weak/hamza -> W)."""
    return [_cls(ch) for ch in bare(norm_strict(surface))]


def _radical_alternatives(root):
    """Split a by-root key like 'ص و ب / ص ي ب' into candidate radical lists."""
    out = []
    for alt in str(root).split("/"):
        letters = [tok for tok in alt.strip().split() if tok]
        if letters:
            out.append(letters)
    return out


def _subsequence(needle, haystack):
    i = 0
    for ch in haystack:
        if i < len(needle) and ch == needle[i]:
            i += 1
    return i == len(needle)


def _skeleton_match(radicals, folded_skel, weak_folded):
    """True if the radicals appear (order-preserving) inside the surface skeleton.

    strict  : exact letters (geminate collapse only) against a folded skeleton.
    weak    : additionally fold weak/hamza radicals to W and allow hollow/defective
              medial-or-final weak elision. Recall tier; always labelled.
    """
    if weak_folded:
        rad = [_cls(x) for x in radicals]
    else:
        # strict tier still compares against the folded skeleton, so fold hamza/alif
        # seats on the radical too, but keep و / ي distinct from other letters.
        rad = [("W" if x in "اأإآ" else x) for x in radicals]
    variants = [rad]
    if len(rad) >= 2 and rad[-1] == rad[-2]:
        variants.append(rad[:-1])
    if len(rad) >= 3 and rad[0] == rad[1]:
        variants.append([rad[0]] + rad[2:])
    if weak_folded and len(rad) >= 3 and rad[-1] == "W":
        variants.append(rad[:-1])
    if weak_folded and len(rad) >= 3 and rad[1] == "W":
        variants.append([rad[0]] + rad[2:])
    return any(_subsequence(v, folded_skel) for v in variants)


class Morphology:
    """Committed lookup surfaces used to derive candidate roots for a surface."""

    def __init__(self, entries, by_root, by_norm_surface):
        self.by_root = by_root
        self.by_norm_surface = by_norm_surface
        self.entry = {e["id"]: e for e in entries}
        # documented-FORM surface (headword / usage forms / sense headwords) -> {root}/{eid}
        self.form_roots = defaultdict(set)
        self.form_eids = defaultdict(set)
        # root -> its radical alternatives (only real triliteral-ish roots)
        self.root_radicals = {}
        for root in by_root:
            alts = [a for a in _radical_alternatives(root) if 2 <= len(a) <= 5]
            if alts:
                self.root_radicals[root] = alts
        for entry in entries:
            root = entry.get("root") or ""
            eid = entry["id"]
            for surface in self._documented_forms(entry):
                for key in (norm_strict(surface), bare(surface)):
                    if key:
                        if root:
                            self.form_roots[key].add(root)
                        self.form_eids[key].add(eid)

    @staticmethod
    def _documented_forms(entry):
        """Verbatim lexeme surfaces the entry documents (NOT the ayah quote words)."""
        yield str(entry.get("headword") or "")
        for piece in str(entry.get("headword") or "").split("/"):
            yield piece
        for sense in entry.get("senses") or []:
            for piece in str(sense.get("ar") or "").split("/"):
                yield piece
        for usage in entry.get("usage") or []:
            for form in usage.get("forms") or []:
                yield str(form)

    def derive(self, surface):
        """Return {root: sorted[methods]} derived for a display surface, plus
        direct norm_strict surface-fallback entry ids (root-less hosts)."""
        methods = defaultdict(set)
        ns = norm_strict(surface)
        br = bare(surface)

        # T1 documented-form exact (whole surface documented verbatim as a lexeme form)
        for key in (ns, br):
            for root in self.form_roots.get(key, ()):
                methods[root].add("documented_form_exact")

        # T2 clitic-segmented documented form (legal peel, then documented-form lookup)
        for cand in segment_candidates(surface):
            for seg in cand["segments"]:
                if seg["role"] != "stem":
                    continue
                stem = seg["surface"]
                for key in (norm_strict(stem), bare(stem)):
                    if not key or key == ns:
                        continue
                    for root in self.form_roots.get(key, ()):
                        methods[root].add("clitic_segmented_form")

        # T3/T4 root-skeleton subsequence against the committed root inventory
        folded = skeleton(surface)
        for root, alts in self.root_radicals.items():
            hit_strict = any(_skeleton_match(a, folded, weak_folded=False) for a in alts)
            hit_weak = any(_skeleton_match(a, folded, weak_folded=True) for a in alts)
            if hit_strict:
                methods[root].add("root_skeleton_strict")
            elif hit_weak:
                methods[root].add("root_skeleton_weak_folded")

        # norm_strict surface fallback -> direct entry hit (root-less particles/nouns)
        fallback_eids = set()
        for eid in self.by_norm_surface.get(ns, ()):
            fallback_eids.add(eid)
        for eid in self.form_eids.get(ns, ()):
            fallback_eids.add(eid)
        return {r: sorted(m) for r, m in methods.items()}, sorted(fallback_eids)


# ---------------------------------------------------------------------------
# example-window fingerprint (reused from build_two_vote_packets)
# ---------------------------------------------------------------------------
class Fingerprinter:
    def __init__(self, entries, loc_surface_rows, crosswalk_locs):
        self.entry = {e["id"]: e for e in entries}
        self.crosswalk_locs = crosswalk_locs  # qword_row_id -> canonical_quran_loc
        self.ayah_words = defaultdict(dict)   # "s:a" -> {w: surface}
        for row in loc_surface_rows:
            s, a, w = row["loc"].split(":")
            self.ayah_words["%s:%s" % (s, a)][int(w)] = row["surface"]

    def _target_window(self, loc):
        s, a, w = loc.split(":")
        w = int(w)
        words = self.ayah_words.get("%s:%s" % (s, a), {})
        return [norm_strict(words[i]) for i in sorted(words) if abs(i - w) <= 2]

    def _carrier_window(self, qword_row_id):
        match = _QWORD_RE.search(qword_row_id or "")
        if not match:
            return None
        eid, ui, ei, qi = match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4))
        entry = self.entry.get(eid)
        if not entry:
            return None
        try:
            example = entry["usage"][ui - 1]["examples"][ei - 1]
        except (IndexError, KeyError, TypeError):
            return None
        words = str(example.get("ar") or "").split()
        if not (1 <= qi <= len(words)):
            return None
        window = words[max(0, qi - 1 - 2): qi - 1 + 3]
        return [norm_strict(tok) for tok in window]

    def covers_target(self, qword_row_id, target_loc):
        """True if the carrier's example ±2 window matches the target ayah window
        AND the crosswalk resolves the carrier to the target loc."""
        cw = self._carrier_window(qword_row_id)
        if cw is None:
            return None
        window_match = cw == self._target_window(target_loc)
        resolved = self.crosswalk_locs.get(qword_row_id)
        return bool(window_match and (resolved is None or resolved == target_loc))


# ---------------------------------------------------------------------------
# candidate assembly
# ---------------------------------------------------------------------------
def _first_words(text, n=4):
    return " ".join(str(text or "").split()[:n])


def _entry_refs(entry):
    refs = []
    for usage in entry.get("usage") or []:
        for example in usage.get("examples") or []:
            ref = example.get("ref")
            if ref and ref not in refs:
                refs.append(ref)
    return refs


def _sense_summaries(entry):
    out = []
    for sense in entry.get("senses") or []:
        out.append({
            "n": sense.get("n"),
            "gloss_first_words": _first_words(sense.get("gloss"), 4),
        })
    return out


def build_proposed_entry(eid, entry, methods, distractor, distractor_reason, fingerprint_covers):
    best = min((CONFIDENCE_RANK.get(m, 9) for m in methods), default=9)
    conf = next((k for k, v in CONFIDENCE_RANK.items() if v == best), None) if methods else None
    proposal = {
        "entry_id": eid,
        "headword": entry.get("headword"),
        "root": entry.get("root") or "",
        "section": entry.get("section"),
        "entry_source_address": "%s#id=%s" % (ENTRIES, eid),
        "by_root_address": "%s#%s" % (BY_ROOT, entry.get("root") or ""),
        "derivation_methods": sorted(methods),
        "match_confidence": conf,
        "sense_glosses": _sense_summaries(entry),
        "example_refs": _entry_refs(entry),
        "neighbor_distractor": bool(distractor),
    }
    if distractor:
        proposal["neighbor_distractor_reason"] = distractor_reason
    if fingerprint_covers is not None:
        proposal["fingerprint_covers_target"] = fingerprint_covers
    return proposal


def bound_carrier_index(append_queue_rows):
    """loc -> list of bound carrier dicts (from the append-queue source of truth)."""
    index = {}
    for row in append_queue_rows:
        loc = row.get("canonical_location") or row.get("loc")
        if loc:
            index[loc] = row.get("bound_carriers") or []
    return index


def enrich_row(row, morph, fp, bound_by_loc, loc_surface_map):
    loc = row["target"]["canonical_location"]
    surface = loc_surface_map.get(loc, row["target"].get("surface"))
    ns = norm_strict(surface or "")

    derived, fallback_eids = morph.derive(surface or "")
    derived_roots = sorted(derived)

    # existing candidates: queue proposed_host_entries + append-queue bound carriers
    existing_carriers = {}
    for prop in row.get("proposed_host_entries") or []:
        eid = prop.get("entry_id")
        if eid:
            existing_carriers.setdefault(eid, {}).update({"queue_proposed": True})
    for carrier in row["misbound_carriers"].get("bound_carriers") or bound_by_loc.get(loc, []):
        eid = carrier.get("entry_id")
        if eid:
            existing_carriers.setdefault(eid, {})["qword_row_id"] = carrier.get("qword_row_id")

    proposals = {}
    # 1. candidates populated by derived-root lookup (true-host lane)
    for root in derived_roots:
        for eid in morph.by_root.get(root, ()):
            entry = morph.entry.get(eid)
            if not entry:
                continue
            methods = set(derived[root])
            proposals[eid] = build_proposed_entry(
                eid, entry, methods, distractor=False,
                distractor_reason=None, fingerprint_covers=None)

    # 2. root-less surface fallback (particles / proper nouns / broken plurals)
    for eid in fallback_eids:
        if eid in proposals:
            continue
        entry = morph.entry.get(eid)
        if not entry:
            continue
        proposals[eid] = build_proposed_entry(
            eid, entry, {"norm_strict_surface_fallback"}, distractor=False,
            distractor_reason=None, fingerprint_covers=None)

    # 3. retain existing carriers; flag neighbor_distractor
    for eid, meta in existing_carriers.items():
        entry = morph.entry.get(eid)
        if not entry:
            continue
        carrier_root = entry.get("root") or ""
        covers = None
        qrid = meta.get("qword_row_id")
        if qrid:
            covers = fp.covers_target(qrid, loc)
        # A rooted carrier glosses the target only if its lexeme root is a derived
        # target root; otherwise it glosses a neighbouring token (its example window
        # coinciding with the target ayah is not enough - the SAME ayah is cited).
        # A root-less carrier (particle/proper noun) falls back to the fingerprint.
        if carrier_root:
            root_agrees = carrier_root in derived
            distractor = not root_agrees
        else:
            root_agrees = False
            distractor = covers is not True
        reason = None
        if distractor:
            if carrier_root:
                reason = "carrier root %s not among derived target roots" % carrier_root
            elif covers is False:
                reason = "root-less carrier example-window does not cover the target token"
            else:
                reason = "root-less carrier glosses a neighbouring token"
        if eid in proposals:
            # derived host that was also already bound: keep as true host, attach fp
            if covers is not None:
                proposals[eid]["fingerprint_covers_target"] = covers
            proposals[eid]["previously_bound"] = True
            continue
        methods = set(derived.get(carrier_root, ())) if root_agrees else set()
        proposals[eid] = build_proposed_entry(
            eid, entry, methods, distractor=distractor,
            distractor_reason=reason, fingerprint_covers=covers)
        proposals[eid]["previously_bound"] = True

    ordered = sorted(
        proposals.values(),
        key=lambda p: (
            1 if p["neighbor_distractor"] else 0,
            min((CONFIDENCE_RANK.get(m, 9) for m in p["derivation_methods"]), default=9),
            p["entry_id"],
        ),
    )
    true_hosts = [p for p in ordered if not p["neighbor_distractor"]]

    def _anchored(prop):
        return bool(set(prop["derivation_methods"]) & SURFACE_ANCHORED_TIERS)

    anchored_hosts = [p for p in true_hosts if _anchored(p)]

    # routing class (honest confidence grading):
    #  * surface-anchored host present  -> existing_entry_rebind
    #  * only skeleton/co-occurrence host -> candidate, confirm at vote
    #  * no host at all after fallback   -> requires_authoring (no-host lane)
    if anchored_hosts:
        routing = "existing_entry_rebind"
        review_gate = "two_vote_existing_rebind"
    elif true_hosts:
        routing = "existing_entry_rebind_candidate"
        review_gate = "two_vote_existing_rebind"
    else:
        routing = "requires_authoring"
        review_gate = "authoring_new_entry_gate"

    # host_roots = every competing root among true hosts (full recall set; the
    # homograph traps are required to emit ALL competing roots here).
    host_roots = sorted({p["root"] for p in true_hosts if p["root"]})
    # A meaningful homograph fires only when >=2 DISTINCT lexeme roots each surface-anchor
    # (skeleton-tier co-derivations are recall candidates, not competing readings).
    anchored_roots = sorted({p["root"] for p in anchored_hosts if p["root"]})
    homograph = len(anchored_roots) > 1

    out = dict(row)
    out["schema"] = V2_SCHEMA
    out["candidate_only"] = True
    out["target"] = dict(row["target"])
    out["target"]["surface"] = surface
    out["target"]["norm_strict"] = ns
    out["enrichment"] = {
        "derived_target_roots": [
            {"root": r, "derivation_methods": derived[r]} for r in derived_roots
        ],
        "root_derivation_boundary": "lookup_only_no_generation_rm40",
        "proposed_host_entries": ordered,
        "true_host_candidate_count": len(true_hosts),
        "surface_anchored_host_count": len(anchored_hosts),
        "neighbor_distractor_count": sum(1 for p in ordered if p["neighbor_distractor"]),
        "host_roots": host_roots,
        "surface_anchored_host_roots": anchored_roots,
        "homograph_multiple_roots": homograph,
        "routing_class": routing,
        "review_gate": review_gate,
        "authoring_review_recommended": routing != "existing_entry_rebind",
        "no_host_after_surface_fallback": routing == "requires_authoring",
    }
    return out


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def build():
    v1_rows = read_jsonl(V1_QUEUE)
    loc_surface_rows = read_jsonl(LOC_SURFACE)
    entries = read_jsonl(ENTRIES)
    by_root = read_json(BY_ROOT)
    by_norm_surface = read_json(BY_NORM_SURFACE)
    append_rows = read_jsonl(APPEND_QUEUE)

    crosswalk_files = sorted(glob.glob(_p(CROSSWALK_GLOB)))
    crosswalk_locs = {}
    for path in crosswalk_files:
        with io.open(path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rec = json.loads(line)
                qrid = rec.get("qword_row_id")
                if qrid:
                    crosswalk_locs[qrid] = rec.get("canonical_quran_loc")

    loc_surface_map = {r["loc"]: r["surface"] for r in loc_surface_rows}
    morph = Morphology(entries, by_root, by_norm_surface)
    fp = Fingerprinter(entries, loc_surface_rows, crosswalk_locs)
    bound_by_loc = bound_carrier_index(append_rows)

    out_rows = [enrich_row(r, morph, fp, bound_by_loc, loc_surface_map) for r in v1_rows]
    out_rows.sort(key=lambda r: loc_key(r["target"]["canonical_location"]))

    # completeness accounting
    def has_true_host(v2row):
        return v2row["enrichment"]["true_host_candidate_count"] > 0

    def v1_had_candidate(v1row):
        return bool(v1row.get("proposed_host_entries"))

    before = sum(1 for r in v1_rows if v1_had_candidate(r))
    after = sum(1 for r in out_rows if has_true_host(r))
    anchored_after = sum(
        1 for r in out_rows if r["enrichment"]["surface_anchored_host_count"] > 0
    )
    routing_counts = defaultdict(int)
    for r in out_rows:
        routing_counts[r["enrichment"]["routing_class"]] += 1

    report = {
        "schema": "qamus/class2-rebind-enrichment-report@1",
        "candidate_only": True,
        "root_derivation_boundary": "lookup_only_no_generation_rm40",
        "total_rows": len(out_rows),
        "completeness": {
            "v1_rows_with_any_candidate": before,
            "v1_rows_with_any_candidate_pct": round(100.0 * before / len(v1_rows), 2),
            "v2_rows_with_true_host_candidate": after,
            "v2_rows_with_true_host_candidate_pct": round(100.0 * after / len(out_rows), 2),
            "v2_rows_with_surface_anchored_host": anchored_after,
            "v2_rows_with_surface_anchored_host_pct": round(100.0 * anchored_after / len(out_rows), 2),
            "note": (
                "true_host_candidate includes the labelled root-skeleton recall tier; "
                "surface_anchored_host is the higher-confidence subset (documented form, "
                "legal clitic-peel, or norm_strict surface hit)."
            ),
        },
        "routing_class_counts": dict(sorted(routing_counts.items())),
        "homograph_rows": sum(1 for r in out_rows if r["enrichment"]["homograph_multiple_roots"]),
    }
    return v1_rows, out_rows, report


def calibration_agreement(out_rows, cal_path):
    """Return the agreement stats against the O1 calibration ABSENT-host group."""
    by_loc = {r["target"]["canonical_location"]: r for r in out_rows}
    with io.open(cal_path, encoding="utf-8") as handle:
        cal = [json.loads(line) for line in handle if line.strip()]
    absent = [
        r for r in cal
        if r.get("disposition") == "existing_entry_rebind" and r.get("carrier_completeness") is False
    ]
    agreed, shortfalls = [], []
    for row in absent:
        loc = row["canonical_location"]
        host = row["proposed_host_identity"]
        gt_root = row["root_lemma_sense_evidence"]["root"]
        v2 = by_loc.get(loc)
        eids = set()
        roots = set()
        if v2:
            for prop in v2["enrichment"]["proposed_host_entries"]:
                eids.add(prop["entry_id"])
                if prop["root"]:
                    roots.add(prop["root"])
        if host in eids or gt_root in roots:
            agreed.append(loc)
        else:
            shortfalls.append({"loc": loc, "gt_root": gt_root, "host": host})
    return {
        "absent_host_calibration_rows": len(absent),
        "surfaced_correct_host": len(agreed),
        "target_threshold": 55,
        "meets_threshold": len(agreed) >= 55,
        "agreed_locs": sorted(agreed, key=loc_key),
        "shortfalls": shortfalls,
    }


def homograph_evidence(out_rows, locs):
    by_loc = {r["target"]["canonical_location"]: r for r in out_rows}
    out = {}
    for loc in locs:
        v2 = by_loc.get(loc)
        if not v2:
            out[loc] = {"present": False}
            continue
        out[loc] = {
            "present": True,
            "surface": v2["target"]["surface"],
            "derived_roots": [d["root"] for d in v2["enrichment"]["derived_target_roots"]],
            "host_roots": v2["enrichment"]["host_roots"],
            "homograph_flagged": v2["enrichment"]["homograph_multiple_roots"],
        }
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the v2 artifact, report and manifest")
    parser.add_argument("--calibration", default=".lane-inputs/rebind-review-cal.jsonl",
                        help="optional O1 calibration file for the agreement report")
    args = parser.parse_args(argv)

    v1_rows, out_rows, report = build()

    cal_path = _p(args.calibration) if not os.path.isabs(args.calibration) else args.calibration
    if os.path.exists(cal_path):
        report["calibration_agreement"] = calibration_agreement(out_rows, cal_path)
    report["homograph_traps"] = homograph_evidence(out_rows, ["2:264:7", "3:36:16", "3:14:7"])

    queue_bytes = write_jsonl_bytes(out_rows)
    report_bytes = write_json_bytes(report)

    manifest = {
        "schema": "qamus/class2-rebind-enrichment-manifest@1",
        "generator": "tools/enrich_rebind_queue.py",
        "candidate_only": True,
        "inputs": {rel: sha256_file(rel) for rel in sorted([
            V1_QUEUE, LOC_SURFACE, ENTRIES, BY_ROOT, BY_NORM_SURFACE, APPEND_QUEUE,
        ])},
        "crosswalk_shard_count": len(sorted(glob.glob(_p(CROSSWALK_GLOB)))),
        "outputs": {
            OUT_QUEUE: sha256_bytes(queue_bytes),
            OUT_REPORT: sha256_bytes(report_bytes),
        },
        "row_count": len(out_rows),
    }
    manifest_bytes = write_json_bytes(manifest)

    if args.write:
        with io.open(_p(OUT_QUEUE), "wb") as handle:
            handle.write(queue_bytes)
        with io.open(_p(OUT_REPORT), "wb") as handle:
            handle.write(report_bytes)
        with io.open(_p(OUT_MANIFEST), "wb") as handle:
            handle.write(manifest_bytes)

    summary = {
        "wrote": bool(args.write),
        "completeness": report["completeness"],
        "routing_class_counts": report["routing_class_counts"],
        "calibration_agreement": report.get("calibration_agreement", {}).get("surfaced_correct_host"),
        "queue_sha256": manifest["outputs"][OUT_QUEUE],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
