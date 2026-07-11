#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_crosswalk_gap_queue — T10 durable queue over the live-only location gap.

Builds one canonical row per deployed-whitelist location that the accepted crosswalk
does not model (the G8 `remove_or_unrepresented` class), carrying candidate source
identities, carrier candidates, normalization, dependency hashes, family
classification, and review state. The queue is the T10 program's row-level ledger:
locations leave it only through a recorded resolution (mechanical proof, review
decision, or explicit exception), never silently.

Determinism: inputs are hash-pinned in the emitted QUEUE manifest; iteration is
sorted; output is byte-stable for identical inputs (self-test proves it under input
reordering).

Usage:
    python tools/build_crosswalk_gap_queue.py --baseline <deployed whitelist jsonl> \
        --outdir <dir> [--loc-surfaces <jsonl of {loc, surface} corpus rows>]
    python tools/build_crosswalk_gap_queue.py --self-test

Lane assignment (primary_resolution_family):
    in_crosswalk_morphline_repair   loc IS modeled but every binding fail-closed on
                                    empty live morphline (Lane D)
    unique_qword_candidate          exactly one qword-denominator row matches
                                    (ayah, norm_strict surface) (Lane A candidate)
    multiple_qword_candidates       >1 matching row (Lane B)
    no_qword_candidate              no matching row (Lane C)

Lane A auto-resolution is NOT performed here — this tool only builds the queue and
proves the preconditions it can prove. Mechanical acceptance requires the full
owner-mandated proof set, including āyah-surface uniqueness: without a
`--loc-surfaces` corpus index the row is flagged
`ayah_surface_uniqueness_unverified` and stays ineligible (fail-closed).

The deployed row itself is never treated as sufficient provenance; candidates come
from the qamus qword-denominator tables and must later carry the full D-13 carrier
through the ordinary crosswalk acceptance discipline.
"""
import argparse
import glob
import hashlib
import io
import json
import os
import sys
import tempfile
import collections

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

QUEUE_SCHEMA = "qamus.crosswalk_gap_queue_row.v1"
MANIFEST_SCHEMA = "qamus.crosswalk_gap_queue_manifest.v1"


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sha256_file(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon_loc(loc):
    if isinstance(loc, str) and loc.startswith("wbw:"):
        return loc[4:]
    return loc


def payload_shape(live_row):
    segs = live_row.get("segments") or []
    if not segs:
        return "no_segments"
    if any("qg_class" in s for s in segs):
        return "contract_segments"
    if any("class" in s or "gloss_contribution" in s for s in segs):
        return "css_segments"
    return "bare_segments"


def morphline_state(live_row):
    if "morphline" not in live_row:
        return "missing"
    val = live_row.get("morphline")
    if val is None or val == "":
        return "empty"
    return "present"


def build_queue(repo_root, baseline_path, loc_surfaces_path=None,
                crosswalk_glob=None, denominator_glob=None):
    """Returns (manifest, queue_rows). Pure function of its hash-pinned inputs."""
    from tools import normalize_ar as N
    from tools import compile_canonical_hover_whitelist_packet as compile_mod

    cw_glob = crosswalk_glob or os.path.join(
        repo_root, "qamus", "indexes", "largelexicon", "qword-crosswalk", "*.jsonl")
    qd_glob = denominator_glob or os.path.join(
        repo_root, "qamus", "indexes", "largelexicon", "qword-denominator", "*.jsonl")

    # modeled locations + per-loc accepted bindings and their required-field state
    modeled_bindings = collections.defaultdict(list)
    cw_files = sorted(glob.glob(cw_glob))
    for path in cw_files:
        for row in read_jsonl(path):
            if row.get("status") == "canonical_crosswalk_accepted":
                modeled_bindings[canon_loc(row.get("canonical_wbw_loc"))].append(row)

    # deployed baseline
    live_by_loc = {}
    for row in read_jsonl(baseline_path):
        loc = compile_mod.canonical_public_loc(row)
        if loc:
            live_by_loc.setdefault(loc, row)

    # qword-denominator candidates keyed by (ayah_ref, norm_strict surface)
    qd_index = collections.defaultdict(list)
    qd_files = sorted(glob.glob(qd_glob))
    for path in qd_files:
        for row in read_jsonl(path):
            key = (row.get("quran_ref"), row.get("visible_surface_norm_strict"))
            qd_index[key].append(row)

    # optional corpus loc->surface index (āyah-surface uniqueness proofs)
    corpus_by_ayah = None
    if loc_surfaces_path:
        corpus_by_ayah = collections.defaultdict(list)
        for row in read_jsonl(loc_surfaces_path):
            loc = canon_loc(row.get("loc"))
            if loc:
                s, a, _w = loc.split(":")
                corpus_by_ayah["%s:%s" % (s, a)].append(
                    (loc, N.norm_strict(row.get("surface") or "")))

    # live-only = live locs whose location is not modeled by the accepted crosswalk,
    # PLUS modeled locs whose every binding fails the compiler's required-field gate
    # (the empty-morphline family — modeled but dropped fail-closed).
    def binding_payload_ok(live_row):
        # mirrors builder _has_required over the LIVE payload the compile would carry
        pc = compile_mod.public_content(live_row)
        return bool((live_row.get("segments") or [])) and bool(pc.get("morphline")) \
            and bool(pc.get("public_gloss")) and bool(pc.get("learner_explanation"))

    queue = []
    for loc in sorted(live_by_loc):
        live = live_by_loc[loc]
        modeled = modeled_bindings.get(loc)
        if modeled and binding_payload_ok(live):
            continue  # modeled and compilable -> not in the gap
        if modeled and not binding_payload_ok(live):
            family = "in_crosswalk_morphline_repair"
        else:
            family = None  # resolved below by candidate count

        surface = live.get("ar") or live.get("surface") or ""
        s, a, _w = loc.split(":")
        norm = N.norm_strict(surface)
        cands = qd_index.get(("%s:%s" % (s, a), norm), [])
        if family is None:
            family = ("unique_qword_candidate" if len(cands) == 1 else
                      "multiple_qword_candidates" if len(cands) > 1 else
                      "no_qword_candidate")

        secondary = []
        if family == "in_crosswalk_morphline_repair":
            secondary.append("has_accepted_crosswalk_bindings:%d" % len(modeled))
            if cands:
                secondary.append("has_qword_candidates:%d" % len(cands))
        ayah_key = "%s:%s" % (s, a)
        if corpus_by_ayah is None or ayah_key not in corpus_by_ayah:
            secondary.append("ayah_surface_uniqueness_unverified")
            unique_in_ayah = None
        else:
            positions = [l for (l, n) in corpus_by_ayah[ayah_key] if n == norm]
            if not positions:
                # the āyah is indexed but the live surface matches no corpus word —
                # a normalization/rasm mismatch, its own diagnostic (NOT uniqueness)
                secondary.append("live_surface_not_in_ayah_index")
                unique_in_ayah = None
            else:
                unique_in_ayah = len(positions) == 1 and positions[0] == loc
                if not unique_in_ayah:
                    secondary.append("surface_repeats_in_ayah:%d" % len(positions))

        carriers = [{"entry_id": c.get("entry_id"), "card_id": c.get("card_id"),
                     "qword_row_id": c.get("qword_row_id") or c.get("row_id"),
                     "row_id": c.get("row_id")} for c in cands]
        carriers.sort(key=lambda c: json.dumps(c, sort_keys=True))
        eq_classes = sorted({c["entry_id"] for c in carriers if c["entry_id"]})
        dep_hashes = {c.get("row_id"): c.get("card_text_sha256") for c in cands
                      if c.get("row_id")}

        pc = compile_mod.public_content(live)
        queue.append({
            "schema": QUEUE_SCHEMA,
            "canonical_location": loc,
            "live_payload_hash": hashlib.sha256(json.dumps(
                pc, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest(),
            "live_payload_shape": payload_shape(live),
            "candidate_entry_ids": sorted({c["entry_id"] for c in carriers if c["entry_id"]}),
            "candidate_card_ids": sorted({c["card_id"] for c in carriers if c["card_id"]}),
            "candidate_qword_row_ids": sorted({c["qword_row_id"] for c in carriers if c["qword_row_id"]}),
            "full_carrier_candidates": carriers,
            "source_normalization": {"live_surface": surface, "norm_strict": norm,
                                      "join_key": "%s:%s|%s" % (s, a, norm)},
            "dependency_hashes": {k: dep_hashes[k] for k in sorted(dep_hashes)},
            "morphline_state": morphline_state(live),
            "provenance_state": ("in_crosswalk_conflicted"
                                  if family == "in_crosswalk_morphline_repair"
                                  else "unresolved_candidate"),
            "candidate_count": len(cands),
            "candidate_equivalence_classes": eq_classes,
            "ayah_surface_unique": unique_in_ayah,
            "primary_resolution_family": family,
            "secondary_conditions": secondary,
            "review_state": "pending",
            "review_votes": [],
            "blocker_or_exception": None,
            "resolution_commit": None,
            "shadow_effect": None,
        })

    fam_counts = collections.Counter(r["primary_resolution_family"] for r in queue)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "baseline_sha256": sha256_file(baseline_path),
        "baseline_rows": len(live_by_loc),
        "crosswalk_files": {os.path.basename(p): sha256_file(p) for p in cw_files},
        "denominator_files": {os.path.basename(p): sha256_file(p) for p in qd_files},
        "loc_surfaces_sha256": (sha256_file(loc_surfaces_path)
                                 if loc_surfaces_path else None),
        "queue_rows": len(queue),
        "family_counts": dict(sorted(fam_counts.items())),
        "modeled_locations": len(modeled_bindings),
    }
    return manifest, queue


def write_outputs(outdir, manifest, queue):
    os.makedirs(outdir, exist_ok=True)
    qpath = os.path.join(outdir, "crosswalk-gap-queue.jsonl")
    with io.open(qpath, "w", encoding="utf-8", newline="\n") as fh:
        for row in queue:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = dict(manifest)
    manifest["queue_sha256"] = sha256_file(qpath)
    mpath = os.path.join(outdir, "crosswalk-gap-queue.manifest.json")
    with io.open(mpath, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, sort_keys=True, indent=1)
        fh.write("\n")  # repo artifact-ergonomics gate: trailing newline required
    return qpath, mpath, manifest


# --------------------------------------------------------------------------- #
# self-test — synthetic fixtures only
# --------------------------------------------------------------------------- #

def _self_test():
    failures = []

    def check(name, cond):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    tmp = tempfile.mkdtemp(prefix="gapqueue-selftest-")
    try:
        cw_dir = os.path.join(tmp, "cw"); os.makedirs(cw_dir)
        qd_dir = os.path.join(tmp, "qd"); os.makedirs(qd_dir)

        def w(path, rows):
            with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

        # accepted crosswalk models loc 1:1:1 only
        w(os.path.join(cw_dir, "a.jsonl"), [{
            "status": "canonical_crosswalk_accepted", "canonical_wbw_loc": "1:1:1",
            "row_id": "cw1", "entry_id": "e1", "card_id": "c1", "qword_row_id": "q1"}])
        # denominator: unique candidate for 1:1:2; two candidates for 1:1:3;
        # none for 1:1:4; candidate for the morphline loc 1:1:5
        w(os.path.join(qd_dir, "d.jsonl"), [
            {"quran_ref": "1:1", "visible_surface_norm_strict": "كتاب",
             "row_id": "qd1", "entry_id": "e2", "card_id": "c2:u1:e1",
             "qword_row_id": "q2", "card_text_sha256": "aa"},
            {"quran_ref": "1:1", "visible_surface_norm_strict": "رحيم",
             "row_id": "qd2", "entry_id": "e3", "card_id": "c3:u1:e1",
             "qword_row_id": "q3", "card_text_sha256": "bb"},
            {"quran_ref": "1:1", "visible_surface_norm_strict": "رحيم",
             "row_id": "qd3", "entry_id": "e4", "card_id": "c4:u1:e1",
             "qword_row_id": "q4", "card_text_sha256": "cc"},
        ])

        def live(loc, surface, morphline="STEM"):
            return {"loc": loc, "surface": surface, "public_gloss": "g",
                    "contextual_phrase_gloss": "g", "morphline": morphline,
                    "learner_explanation": "x",
                    "segments": [{"role": "STEM", "surface": surface,
                                  "class": "qg-noun", "gloss_contribution": "g"}]}
        baseline = os.path.join(tmp, "live.jsonl")
        w(baseline, [
            live("1:1:1", "بِسْمِ"),                 # modeled + compilable -> NOT in queue
            live("1:1:2", "كِتَاب"),                 # unique candidate
            live("1:1:3", "رَحِيم"),                 # two candidates
            live("1:1:4", "غَرِيب"),                 # no candidate
        ])

        m, q = build_queue(REPO, baseline, crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                           denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        fam = {r["canonical_location"]: r["primary_resolution_family"] for r in q}
        check("modeled+compilable loc excluded from queue", "1:1:1" not in fam)
        check("unique candidate family", fam.get("1:1:2") == "unique_qword_candidate")
        check("multiple candidate family", fam.get("1:1:3") == "multiple_qword_candidates")
        check("no candidate family", fam.get("1:1:4") == "no_qword_candidate")
        row2 = next(r for r in q if r["canonical_location"] == "1:1:2")
        check("owner column set complete on every row", all(
            k in row2 for k in ("canonical_location", "live_payload_hash",
            "live_payload_shape", "candidate_entry_ids", "candidate_card_ids",
            "candidate_qword_row_ids", "full_carrier_candidates",
            "source_normalization", "dependency_hashes", "morphline_state",
            "provenance_state", "candidate_count", "candidate_equivalence_classes",
            "primary_resolution_family", "secondary_conditions", "review_state",
            "review_votes", "blocker_or_exception", "resolution_commit",
            "shadow_effect")))
        check("carrier candidate carries entry/card/qword ids",
              row2["full_carrier_candidates"] == [{"entry_id": "e2",
              "card_id": "c2:u1:e1", "qword_row_id": "q2", "row_id": "qd1"}])
        check("dependency hash pinned", row2["dependency_hashes"] == {"qd1": "aa"})
        check("no corpus index -> uniqueness unverified (fail-closed for Lane A)",
              "ayah_surface_uniqueness_unverified" in row2["secondary_conditions"]
              and row2["ayah_surface_unique"] is None)

        # morphline family: modeled loc whose live payload has empty morphline
        w(baseline, [live("1:1:1", "بِسْمِ", morphline="")])
        m2, q2 = build_queue(REPO, baseline, crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                             denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        check("modeled + empty morphline -> in_crosswalk_morphline_repair",
              len(q2) == 1 and q2[0]["primary_resolution_family"] ==
              "in_crosswalk_morphline_repair"
              and q2[0]["morphline_state"] == "empty"
              and q2[0]["provenance_state"] == "in_crosswalk_conflicted")

        # RED-FIRST false-unique-match fixture: the surface occurs at TWO positions
        # in the āyah — a naive unique-candidate join would auto-resolve; the corpus
        # index must mark it repeats and NOT unique.
        w(baseline, [live("1:1:2", "كِتَاب")])
        locsurf = os.path.join(tmp, "corpus.jsonl")
        w(locsurf, [{"loc": "1:1:2", "surface": "كِتَاب"},
                    {"loc": "1:1:6", "surface": "كِتَٰب"}])  # same norm_strict, other position
        m3, q3 = build_queue(REPO, baseline, loc_surfaces_path=locsurf,
                             crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                             denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        check("RED-FIRST: repeated surface in ayah -> ayah_surface_unique False + flagged",
              q3[0]["ayah_surface_unique"] is False
              and any(c.startswith("surface_repeats_in_ayah:2")
                      for c in q3[0]["secondary_conditions"]))
        # āyah absent from the index -> unverified (NOT counted as repeats)
        w(locsurf, [{"loc": "2:1:1", "surface": "الم"}])
        m3b, q3b = build_queue(REPO, baseline, loc_surfaces_path=locsurf,
                               crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                               denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        check("ayah absent from corpus index -> unverified, not repeats",
              q3b[0]["ayah_surface_unique"] is None and
              "ayah_surface_uniqueness_unverified" in q3b[0]["secondary_conditions"])
        # āyah present but surface unmatched -> normalization diagnostic
        w(locsurf, [{"loc": "1:1:9", "surface": "مختلف"}])
        m3c, q3c = build_queue(REPO, baseline, loc_surfaces_path=locsurf,
                               crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                               denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        check("ayah indexed but live surface unmatched -> live_surface_not_in_ayah_index",
              q3c[0]["ayah_surface_unique"] is None and
              "live_surface_not_in_ayah_index" in q3c[0]["secondary_conditions"])
        # and the positive control: genuinely unique in āyah
        w(locsurf, [{"loc": "1:1:2", "surface": "كِتَاب"}])
        m4, q4 = build_queue(REPO, baseline, loc_surfaces_path=locsurf,
                             crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                             denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        check("unique-in-ayah positive control proves True",
              q4[0]["ayah_surface_unique"] is True)

        # determinism under input reordering: reverse the denominator file rows
        rows = read_jsonl(os.path.join(qd_dir, "d.jsonl"))
        w(os.path.join(qd_dir, "d.jsonl"), list(reversed(rows)))
        m5, q5 = build_queue(REPO, baseline, loc_surfaces_path=locsurf,
                             crosswalk_glob=os.path.join(cw_dir, "*.jsonl"),
                             denominator_glob=os.path.join(qd_dir, "*.jsonl"))
        check("byte-identical queue under input reordering",
              json.dumps(q4, sort_keys=True, ensure_ascii=False)
              == json.dumps(q5, sort_keys=True, ensure_ascii=False))

        # manifest pins every input hash
        check("manifest hash-pins baseline + every input file",
              m4["baseline_sha256"] and m4["loc_surfaces_sha256"]
              and len(m4["crosswalk_files"]) == 1 and len(m4["denominator_files"]) == 1)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("\n%d SELF-TEST FAILURE(S)" % len(failures))
        return 1
    print("\nGAP-QUEUE BUILDER SELF-TEST PASS")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", help="deployed whitelist jsonl")
    parser.add_argument("--outdir", help="output directory")
    parser.add_argument("--loc-surfaces", help="corpus loc->surface jsonl (uniqueness proofs)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.baseline or not args.outdir:
        parser.error("--baseline and --outdir are required unless --self-test")
    manifest, queue = build_queue(REPO, args.baseline, args.loc_surfaces)
    qpath, mpath, manifest = write_outputs(args.outdir, manifest, queue)
    print("queue rows: %d  families: %s" % (manifest["queue_rows"],
          json.dumps(manifest["family_counts"])))
    print("queue -> %s (sha %s)" % (qpath, manifest["queue_sha256"][:16]))
    print("manifest -> %s" % mpath)


if __name__ == "__main__":
    main()
