#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the curriculum corpus pilot: candidate instructional envelopes for
canonical Quranic occurrences, derived ENTIRELY from committed p007 pilot
authority (typed facts, projections, reverse index, event trail) — no new
linguistic conclusion is introduced.

Occurrences: quran:2:34:5 (li + Adam, diptote jarr=fatha host) and
quran:61:5:4 (li + qawmihi, the multi-entry canary with an existing website
payload). The REUSABLE LESSON (clitic carve + evidence-required letter
ownership, units u-s09/u-s01, increment inc-ownership) is applied to both
occurrences by the same rules — the second occurrence is the reuse proof.

Honesty invariants:
- every fact cited comes from qamus/examples/p007-li-pilot/ with its
  certification posture copied verbatim, never upgraded;
- host-INTERNAL letter ownership is NOT certified by the repo, so the real
  consumer (tools/curriculum_unit_consumer.py) is invoked and its
  no_root_evidence ABSTENTION is recorded — unresolved state preserved,
  not papered over;
- colour segments and hover cards are read from the SAME projection record;
  hover components are ALIGNED to segments by component surface within that
  record (a CANDIDATE alignment — authoritative same-fact identity is Sol
  adapter work, never claimed here) and the projection hash shared by every
  appearance travels with the envelope;
- every depended-on fact's certification is consumed as a REPLAYED effective
  state; any invalid dependency withholds the envelope's learner-facing
  artifact classes at build time (fail-closed; no cascade claim);
- the website envelope for 61:5:4 references the EXISTING payload sample;
  for 2:34:5 (no payload exists) a candidate_payload_shape is derived and
  explicitly marked non-deliverable.

Deterministic: byte-identical output on rerun. Stdlib only. Writes ONLY
curriculum/l1l6/corpus-pilot/.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P007 = ROOT / "qamus" / "examples" / "p007-li-pilot"
OUT = ROOT / "curriculum" / "l1l6" / "corpus-pilot"

sys.path.insert(0, str(ROOT / "tools"))
import curriculum_unit_consumer as consumer  # noqa: E402
from certify_typed_fact import TypedFactCertificationStore  # noqa: E402

TARGETS = ("quran:2:34:5", "quran:61:5:4")
HARAKAT_RE = re.compile("[ً-ْٰۖ-ۭ]")


def bare_letters(surface):
    return [ch for ch in HARAKAT_RE.sub("", surface)]


VALID_EFFECTIVE_STATUSES = ("certified", "candidate")
WITHHELD_ARTIFACT_CLASSES = [
    "learner_projection_fields",
    "colour_and_hover_bindings",
    "letter_ownership_presentation",
    "website_envelope",
    "appearance_enumeration",
    "derived_fixture_candidates",
    "disposition_and_readiness_metrics",
]


def _effective_certification(fact_ids, certification_dir=None):
    """Consume the authoritative certifier's validated folded state.

    No local transition semantics are permitted here.  A structurally invalid
    or semantically illegal event trail fails closed for every dependency.
    """
    store_dir = Path(certification_dir or (P007 / "certification"))
    store = TypedFactCertificationStore(store_dir)
    errors = store.validate_trail()
    if errors:
        return ({fid: {"effective_status": "invalid_event_trail",
                       "event_count": 0}
                 for fid in fact_ids}, errors)
    statuses = store.status_by_id()
    counts = store.event_counts_by_id()
    return ({fid: {
                "effective_status": statuses.get(fid, "no_event_in_trail"),
                "event_count": counts.get(fid, 0),
            }
            for fid in fact_ids}, [])


def _canonical_loc_surface():
    idx = {}
    p = ROOT / "qamus" / "indexes" / "quran-loc-surface" / "index.jsonl"
    if p.exists():
        with p.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                idx[r["loc"]] = r["surface"]
    return idx


def _canonical_binding(canonical_idx, target, surface, _ud):
    """Bind the envelope's written surface to the canonical loc surface and
    DECLARE the outcome (Sol fix-request round 2, finding 2). Where the
    committed p007 pilot projection encodes the word differently from the
    canonical index (an orthographic-encoding difference in main's own
    artifacts), the divergence is REPORTED — this branch does not decide
    that two encodings are the same word, which is a normalization policy
    call for the Sol projection plane."""
    loc = target.replace("quran:", "")
    canonical = canonical_idx.get(loc)
    verified = (canonical is not None
                and _ud.normalize("NFC", canonical)
                == _ud.normalize("NFC", surface))
    out = {
        "canonical_index": "qamus/indexes/quran-loc-surface/index.jsonl",
        "canonical_surface": canonical,
        "projection_surface": surface,
        "verified": verified,
    }
    if not verified:
        out["divergence"] = {
            "class": "orthographic_encoding_difference_between_committed_main_artifacts",
            "detail": ("the committed p007 pilot projection and the canonical "
                       "loc-surface index encode this occurrence's surface "
                       "differently (both are current-main artifacts); this "
                       "branch REPORTS the divergence and does not assert "
                       "that the two encodings are equal"),
            "ownership": "sol_adapter_required (adp-occurrence-appearance-projection: canonical surface normalization is the projection plane's call)",
            "consequence": ("the envelope is anchored to the p007 projection "
                            "surface it was built from; no canonical-surface "
                            "equality claim is made for it"),
        }
    return out


def build(certification_dir=None):
    import unicodedata as _ud
    canonical_idx = _canonical_loc_surface()
    facts = [json.loads(l) for l in
             (P007 / "typed-facts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    projections = [json.loads(l) for l in
                   (P007 / "projections.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    reverse_index = json.loads((P007 / "entry-reverse-index.json").read_text(encoding="utf-8"))
    payload_614 = json.loads(
        (ROOT / "qamus" / "examples" / "website-payloads" /
         "multi_entry_liqawmihi_61_5_4.payload.json").read_text(encoding="utf-8"))

    rootless = [f for f in facts if f["fact_type"] == "particle_rootlessness"]
    envelopes = {}
    for target in TARGETS:
        tf = [f for f in facts
              if any(s.get("quran_loc") == target for s in f.get("surface_spans", []))]
        proj_row = next(p for p in projections
                        if p["projection"]["occurrence_id"] == target)
        proj = proj_row["projection"]
        surface = proj["surface"]
        seg_fact = next(f for f in tf if f["fact_type"] == "clitic_host_segmentation")

        # CERTIFICATION fail-close (Sol fix-request round 2, finding 5): the
        # envelope's learner-facing planes exist ONLY while every depended-on
        # fact's authoritative effective state is valid. Invalid trails,
        # illegal transitions, unknown facts, and non-available dependency
        # states all fail closed. Revocation cascades belong exclusively to
        # TypedFactCertificationStore.
        dep_fids = sorted({f["fact_id"] for f in tf + rootless})
        eff, trail_errors = _effective_certification(
            dep_fids, certification_dir=certification_dir)
        blocking = {fid: st for fid, st in eff.items()
                    if st["effective_status"] not in VALID_EFFECTIVE_STATUSES}
        cert_dep = {
            "effective_states": eff,
            "basis": "tools.certify_typed_fact.TypedFactCertificationStore validated trail and folded effective state",
            "trail_valid": not trail_errors,
            "trail_errors": trail_errors,
            "depends_on_fact_ids": dep_fids,
            "invalidation_rule": (
                "fail-closed withholding by THIS builder: while the "
                "authoritative event trail is invalid or any depended-on "
                "fact's effective state is outside %s, "
                "the envelope's learner-facing artifact classes %s are "
                "WITHHELD (not emitted). Revocation and dependent-fact "
                "cascades are performed only by TypedFactCertificationStore; "
                "this consumer never invents transitions."
                % (list(VALID_EFFECTIVE_STATUSES), WITHHELD_ARTIFACT_CLASSES)),
        }
        if blocking:
            envelopes[target] = {
                "schema": "curriculum.l1l6_corpus_pilot_envelope.v1",
                "status": "withheld_invalid_dependency",
                "occurrence_id": target,
                "withheld": True,
                "withheld_artifact_classes": list(WITHHELD_ARTIFACT_CLASSES),
                "blocking_dependencies": blocking,
                "certification_dependency": cert_dep,
                "withholding_note": (
                    "learner projections, colour/hover bindings, website "
                    "envelope, appearance enumeration, fixture derivations "
                    "and readiness metrics for this occurrence are WITHHELD "
                    "until every dependency's effective state is valid "
                    "again; nothing is served from a revoked or unknown "
                    "certification state"),
                "boundaries": ["og-1", "og-2", "og-6",
                               "no certification minted by this envelope",
                               "no live surface touched"],
            }
            continue

        # CANDIDATE span alignment (claim narrowed per Sol fix-request
        # round 2, finding 13): each segment is bound to the fact ids that
        # own it; each hover card is ALIGNED to a segment by its
        # component_surface WITHIN this single projection record and copies
        # that segment's fact ids. This is a candidate alignment, NOT
        # authoritative same-fact identity — shared fact ids minted at
        # projection time are the Sol projection/certifier adapter's work.
        # Segments without a hover component are reported UNCOVERED (no
        # alignment claim is made for them).
        clitic_fact_ids = sorted(f["fact_id"] for f in tf + rootless)
        seg_fact_bindings = []
        for s_ in proj["segments"]:
            if s_["role"].startswith("jarr_clitic"):
                seg_fact_bindings.append({
                    "surface": s_["surface"], "role": s_["role"],
                    "fact_ids": clitic_fact_ids})
            else:
                seg_fact_bindings.append({
                    "surface": s_["surface"], "role": s_["role"],
                    "fact_ids": [f["fact_id"] for f in tf
                                 if f["fact_type"] == "clitic_host_segmentation"],
                    "note": "host span owned by the carve fact only; "
                            "host-internal facts pending (unresolved state)"})
        hover_bindings = []
        covered = set()
        for h in proj.get("hover_cards", []):
            match = next((b for b in seg_fact_bindings
                          if b["surface"] == h["component_surface"]), None)
            hover_bindings.append({
                "component_surface": h["component_surface"],
                "fact_ids": match["fact_ids"] if match else [],
                "traces_to_segment_facts": bool(match)})
            if match:
                covered.add(match["surface"])
        uncovered = [b["surface"] for b in seg_fact_bindings
                     if b["surface"] not in covered]

        # appearance-level parity: one hash everywhere
        hashes = {a["projection_hash"] for a in proj_row["appearances"]}
        hash_parity = hashes == {proj_row["projection_hash"]}

        # the honest machine abstention on host-internal ownership: the repo
        # certifies the CARVE, not the host's internal root/pattern split
        consumer_unit, _ = consumer.load("inc-ownership", "unit-v2.json")
        consumer_result = consumer.analyze_ownership(
            {"surface": surface, "letters": bare_letters(surface),
             "token_kind": "noun"}, consumer_unit)

        envelopes[target] = {
            "schema": "curriculum.l1l6_corpus_pilot_envelope.v1",
            "status": "candidate",
            "occurrence_id": target,
            "surface": surface,
            "canonical_surface_binding": _canonical_binding(
                canonical_idx, target, surface, _ud),
            "withheld": False,
            "withheld_artifact_classes_on_invalid_dependency":
                list(WITHHELD_ARTIFACT_CLASSES),
            "certification_dependency": cert_dep,
            "repository_authority": {
                "typed_facts": sorted(
                    [{"fact_id": f["fact_id"], "fact_type": f["fact_type"],
                      "certification_status_verbatim": f["certification"]["status"],
                      "source_file": "qamus/examples/p007-li-pilot/typed-facts.jsonl"}
                     for f in tf + rootless], key=lambda r: r["fact_id"]),
                "certification_event_trail": "qamus/examples/p007-li-pilot/certification/events.jsonl",
                "projection_source": "qamus/examples/p007-li-pilot/projections.jsonl",
                "projection_hash": proj_row["projection_hash"],
            },
            "letter_ownership": {
                "clitic_morpheme": {
                    "surface": seg_fact["fact_value"]["clitic"],
                    "class": "clitic (jarr lam)",
                    "rootlessness": "per particle_rootlessness fact (repo)",
                },
                "host": {
                    "surface": seg_fact["fact_value"]["carve"][1],
                    "internal_ownership": "UNRESOLVED — the repository certifies the carve, not the host's root/pattern letter split; preserved as pending",
                    "consumer_verdict": consumer_result,
                    "resolution_path": "host root certification via the sarf evidence ladder, then inc-ownership rules (packet TP-CURR-ROOTPATTERN-PROMOTION)",
                },
            },
            "sarf_facts": [f["fact_id"] for f in tf
                           if f["fact_type"] == "clitic_host_segmentation"] +
                          [f["fact_id"] for f in rootless],
            "nahw_facts": [f["fact_id"] for f in tf
                           if f["fact_type"] in ("contextual_function",
                                                 "governor_relation",
                                                 "case_mood_governor")],
            "colour_and_hover": {
                "derived_from_single_projection_record": True,
                "segments": proj["segments"],
                "segment_fact_bindings": seg_fact_bindings,
                "hover_fact_bindings": hover_bindings,
                "alignment_basis": (
                    "CANDIDATE span alignment: hover components are matched "
                    "to segments by component_surface WITHIN this one "
                    "projection record and copy that segment's fact ids; "
                    "authoritative same-fact identity (shared fact ids "
                    "minted by the certifier/projection plane) is Sol "
                    "adapter work and is NOT claimed here"),
                "covered_segments": sorted(covered),
                "uncovered_segments": uncovered,
                "uncovered_note": ("segments without a hover component are "
                                    "REPORTED, not papered over: no parity "
                                    "claim exists for them until the hover "
                                    "plane carries their fact ids"
                                    if uncovered else None),
            },
            "appearances": {
                "rows": proj_row["appearances"],
                "count": len(proj_row["appearances"]),
                "single_hash_parity": hash_parity,
            },
            "reverse_trace": {
                "entry_id": reverse_index["entry_id"],
                "occurrence_listed": target in json.dumps(reverse_index),
                "source_file": "qamus/examples/p007-li-pilot/entry-reverse-index.json",
            },
            "website_envelope": (
                {"kind": "existing_payload_reference",
                 "artifact_id": payload_614["artifact_id"],
                 "schema": payload_614["schema"],
                 "source_file": "qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json"}
                if target == "quran:61:5:4" else
                {"kind": "candidate_payload_shape",
                 "schema": "qamus.website_projection_payload.v1",
                 "occurrence_id": target,
                 "projection_hash": proj_row["projection_hash"],
                 "deliverable": False,
                 "note": "shape-compatible candidate; NOT a payload for delivery — payload production stays with the established website-handoff lane"}),
            "reusable_lesson": {
                "units": ["u-s09", "u-s01"],
                "increment": "curriculum/l1l6/increments/inc-ownership/",
                "lesson": "carve the jarr clitic, own letters only under evidence, abstain on the rest",
                "reuse_note": "the SAME rules process both occurrences; nothing token-specific was copied between them (method transfer, og-2)",
            },
            "unresolved_states": [
                "host_internal_letter_ownership (consumer abstains: no certified host root in the pilot store)",
            ],
            "boundaries": ["og-1", "og-2", "og-6",
                           "no certification minted by this envelope",
                           "no live surface touched"],
        }
    return envelopes


def serialize(envelopes):
    out = {}
    for target, env in envelopes.items():
        name = "envelope-%s.json" % target.replace("quran:", "").replace(":", "-")
        out[str(OUT / name)] = (json.dumps(env, ensure_ascii=False, indent=2,
                                           sort_keys=True) + "\n").encode("utf-8")
    meta = {
        "schema": "curriculum.l1l6_corpus_pilot_envelope.v1.meta",
        "generator": "tools/build_curriculum_corpus_pilot.py",
        "occurrences": sorted(envelopes),
        "reuse_demonstration": "one reusable lesson (inc-ownership rules) applied to both occurrences; second occurrence = reuse proof",
        "authority": "qamus/examples/p007-li-pilot/ (facts, projections, reverse index, event trail) — no new linguistic conclusions",
    }
    out[str(OUT / "corpus-pilot.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    OUT.mkdir(parents=True, exist_ok=True)
    files = serialize(build())
    bad = []
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(p.name)
        else:
            p.write_bytes(data)
            print("wrote %s" % p.relative_to(ROOT))
    if check:
        if bad:
            print("FAIL: corpus-pilot artifacts differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: corpus-pilot artifacts byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
