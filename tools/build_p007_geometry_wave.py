#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P007_GEOMETRY_WAVE — geometry-only certification + authoritative reverse universe.

Owner boundary (rung-1, clitic-host scope note): this wave certifies ONLY
mechanical facts about the 454 ``deterministic-attachment-geometry`` p007 rows —
exact attachment geometry (clitic char span + base-letter span), NFC surface
reconstruction, and the token/host boundary. It NEVER certifies p007 identity,
function, sense, governor, governed expression, case, scope or meaning: those
facets stay candidate with their evidence-policy routing recorded on the
reverse-universe rows.

Emits (deterministic; stdlib only; candidate mode — no live surface touched):

* ``qamus/certification/p007-geometry-wave/typed-facts.jsonl`` — 454 x 3
  geometry typed facts (attachment_geometry / surface_reconstruction_nfc /
  token_host_boundary) with full evidence bundles over committed in-repo
  sources (matrix row + quran-loc-surface universe alignment + NFC
  reconstruction proof).
* ``qamus/certification/p007-geometry-wave/events.jsonl`` — append-only
  hash-chained certification event trail written THROUGH
  ``tools/certify_typed_fact.TypedFactCertificationStore`` (register ->
  review_required -> certified; the reconstruction/boundary facts certify on
  the deterministic-derivation rung over their certified geometry input).
  Never rebuilt if present.
* ``qamus/lattice/p007-reverse-universe.jsonl`` — the authoritative full p007
  reverse universe: one row per matrix row (2,999) with the owner's full row
  schema (canonical loc, surfaces, morpheme span, host, candidate/certified
  edges, sense/function/governor/governed/case/attachment states, evidence
  policy + MCP evidence refs, review state, projection state, every page
  appearance by P/V/N, reverse trace refs, exact blocker).
* ``qamus/lattice/p007-reverse-universe.meta.json`` — sidecar with the 11
  honest P007_* state tallies (recomputed, never asserted, by
  ``tools/validate_p007_universe.py``).
* ``qamus/certification/p007-geometry-wave/spot-check-worksheet.json`` —
  codepoint worksheet for the 20-row manual spot check (the reviewed verdicts
  live in ``spot-check.json``).

Universe alignment authority: ``qamus/indexes/quran-loc-surface/index.jsonl``.
Matrix surfaces that differ from it are classified into honest alignment tiers
(nfc_exact / annotation_variant / orthography_variant_rasm_equal); a row that
does not reach rasm equality is a hard error and is never certified.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.certify_typed_fact import TypedFactCertificationStore  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCOPE = "P007_GEOMETRY_WAVE"
ENTRY_ID = "b10a1ee04666"
SOURCE_KEY = "p007"
SENSE_N = 2
ACTOR = "lane:p007-geometry-wave"
TS = "2026-07-29T00:00:00Z"
CONTRACT_ID = "fd:p007geo:attachment-geometry-wave"
PRODUCER = {"id": "tools.build_p007_geometry_wave", "version": "1"}

LATTICE = os.path.join(ROOT, "qamus", "lattice")
WAVE_DIR = os.path.join(ROOT, "qamus", "certification", "p007-geometry-wave")
CLASSIFICATION = os.path.join(LATTICE, "p007-population-classification.jsonl")
MATRIX = os.path.join(LATTICE, "particle-occurrence-matrix.jsonl")
LOC_INDEX = os.path.join(ROOT, "qamus", "indexes", "quran-loc-surface", "index.jsonl")
AYAH_UNIVERSE = os.path.join(LATTICE, "example-ayah-universe.jsonl")
MCP_REFS = os.path.join(LATTICE, "p007-mcp-evidence-refs.jsonl")
PILOT_DIR = os.path.join(ROOT, "qamus", "examples", "p007-li-pilot")
UNIVERSE_OUT = os.path.join(LATTICE, "p007-reverse-universe.jsonl")
META_OUT = os.path.join(LATTICE, "p007-reverse-universe.meta.json")

GEOMETRY_PARTITION = "deterministic-attachment-geometry"
GEOMETRY_FACT_TYPES = ("attachment_geometry", "surface_reconstruction_nfc",
                       "token_host_boundary")

# Quranic annotation signs (small waqf/tajwid marks) — orthographic layer only.
_ANNOTATION = frozenset(chr(cp) for cp in range(0x06D6, 0x06EE))
_TATWEEL = "ـ"


def nfc(text):
    return unicodedata.normalize("NFC", text)


def _is_mark(ch):
    return unicodedata.combining(ch) != 0 or ch in _ANNOTATION


def rasm(text, dagger="expand"):
    """Skeleton letters: strip marks/annotation, normalize seat orthography.

    Mechanical only — maps wasla->alef, alef-maqsura->ya, a tatweel seat
    carrying hamza-above to the free hamza letter, and the dagger alef either
    to a full alef letter (``dagger='expand'``, e.g. فتيٰن = فتيان) or to a
    plain vowel mark (``dagger='drop'``, e.g. شوىٰ = شوى) — the sign is
    orthographically ambiguous between the two committed encodings, so
    alignment accepts either rendering."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == _TATWEEL:
            j = i + 1
            seated_hamza = False
            while j < n and _is_mark(text[j]):
                if text[j] == "ٔ":
                    seated_hamza = True
                j += 1
            if seated_hamza:
                out.append("ء")
            i = j
            continue
        if ch == "ٰ":
            if dagger == "expand":
                out.append("ا")
            i += 1
            continue
        if _is_mark(ch):
            i += 1
            continue
        if ch == "ٱ":
            ch = "ا"
        elif ch == "آ":
            # alef-madda vs plain alef is a mark-layer difference (e.g. the
            # committed encodings لَآ / لَا of the same token)
            ch = "ا"
        elif ch == "ى":
            ch = "ي"
        out.append(ch)
        i += 1
    return "".join(out)


def strip_annotation(text):
    return "".join(ch for ch in text if ch not in _ANNOTATION)


def alignment_tier(universe_surface, matrix_surface):
    a, b = nfc(universe_surface), nfc(matrix_surface)
    if a == b:
        return "nfc_exact"
    if strip_annotation(a) == strip_annotation(b):
        return "annotation_variant"
    for dagger_a in ("expand", "drop"):
        for dagger_b in ("expand", "drop"):
            if rasm(a, dagger_a) == rasm(b, dagger_b):
                return "orthography_variant_rasm_equal"
    return "misaligned"


def clitic_geometry(universe_surface):
    """Deterministic read-off of the attachment geometry from the NFC surface.

    Returns None (with a reason) when the read-off is NOT deterministic; a
    geometry row failing this is a hard error upstream."""
    s = nfc(universe_surface)
    if not s or s[0] != "ل":
        return None, "first base letter is not lam"
    k = 1
    while k < len(s) and _is_mark(s[k]):
        k += 1
    clitic, remainder = s[:k], s[k:]
    if not remainder:
        return None, "no host remainder after the clitic"
    if "ِ" not in clitic:
        return None, "no kasra sign inside the clitic span"
    return {
        "surface_nfc": s,
        "component_surface": clitic,
        "char_span": {"start": 0, "end": k},
        "base_letter_span": {"start": 0, "end": 1},
        "kasra_sign_present": True,
        "assimilation_shadda_in_span": "ّ" in clitic,
        "host_remainder_surface": remainder,
        # Uthmani rasm skeleton: the dagger alef is a vowel sign, never a
        # skeleton letter (e.g. فِتْيَٰنِ counts ف ت ي ن = 4 + ه).
        "host_base_letter_count": len(rasm(remainder, dagger="drop")),
    }, None


def loc_sort_key(canonical_loc):
    return tuple(int(part) for part in canonical_loc.split(":"))


def loc_us(canonical_loc):
    return canonical_loc.replace(":", "_")


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")))
            handle.write("\n")


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=1)
        handle.write("\n")


def load_loc_index():
    index = {}
    with io.open(LOC_INDEX, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                index[row["loc"]] = row["surface"]
    return index


def load_appearance_classes():
    classes = {}
    with io.open(AYAH_UNIVERSE, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                appearance_id = row.get("appearance_id")
                if appearance_id:
                    classes[appearance_id] = (row.get("entry_type") or "").upper()
    return classes


# ---------------------------------------------------------------------------
# typed facts (geometry only)
# ---------------------------------------------------------------------------

def fact_ids_for(canonical_loc):
    key = loc_us(canonical_loc)
    return {
        "geom": "fact:p007geo:%s:geom" % key,
        "recon": "fact:p007geo:%s:recon" % key,
        "bound": "fact:p007geo:%s:bound" % key,
    }


def _source_addresses(canonical_loc, matrix_id):
    return [
        {"address": "quran:%s" % canonical_loc, "source_kind": "quran_token"},
        {"address": "qamus/lattice/particle-occurrence-matrix.jsonl#%s" % matrix_id,
         "source_kind": "review_artifact"},
        {"address": "qamus/indexes/quran-loc-surface/index.jsonl#%s" % canonical_loc,
         "source_kind": "review_artifact"},
        {"address": "qamus/lattice/p007-population-classification.jsonl#%s" % matrix_id,
         "source_kind": "review_artifact"},
    ]


_GUARDS = [
    {"guard_id": "p007geo.candidate_mode",
     "reason": "wave-local store; no live surface mutation is authorized by this fact"},
    {"guard_id": "p007geo.owner_boundary",
     "reason": "geometry-only wave: certifies attachment geometry, spans, NFC "
               "reconstruction and the token/host boundary ONLY — never p007 "
               "identity, function, sense, governor, governed expression, "
               "case, scope or meaning"},
]


def _defeaters(canonical_loc, matrix_id):
    return [
        {"defeater_id": "loc-surface-index-changed:%s" % canonical_loc,
         "condition": "qamus/indexes/quran-loc-surface/index.jsonl no longer "
                      "carries this exact surface at %s" % canonical_loc},
        {"defeater_id": "matrix-row-changed:%s" % matrix_id,
         "condition": "qamus/lattice/particle-occurrence-matrix.jsonl row %s "
                      "no longer aligns (>= rasm equality) with the universe "
                      "surface" % matrix_id},
    ]


def build_fact(canonical_loc, matrix_id, fact_kind, fact_type, fact_value,
               evidence_mode, *, chain_input=None, dependents=None):
    ids = fact_ids_for(canonical_loc)
    addresses = _source_addresses(canonical_loc, matrix_id)
    fact = {
        "fact_id": ids[fact_kind],
        "fact_type": fact_type,
        "fact_value": fact_value,
        "surface_spans": [{"quran_loc": "quran:%s" % canonical_loc,
                           "surface": fact_value.get("surface_nfc") or fact_value.get("surface")}],
        "ownership": {
            "primary": {"owner_id": "p007-geometry-wave", "owner_type": "lane_candidate"},
            "secondary": [{"owner_id": "tools.certify_typed_fact",
                           "owner_type": "transition_engine"}],
        },
        "source": {
            "kind": "deterministic_read_off",
            "detail": "mechanical derivation from the committed matrix row + "
                      "quran-loc-surface universe alignment + NFC reconstruction proof",
        },
        "source_address": addresses[0],
        "certification": {"status": "candidate",
                          "reason": "registered by the p007 geometry wave; "
                                    "certification only via the transition engine"},
        "evidence": {"status": "candidate", "confidence": "deterministic",
                     "evidence_ids": ["p007geo:evidence:%s:%s" % (canonical_loc, fact_kind)],
                     "summary": "deterministic geometry read-off for %s" % canonical_loc},
        "evidence_mode": evidence_mode,
        "source_evidence": {
            "source_addresses": addresses,
            "structured_source_fact": fact_value,
        },
        "derivation_chain": [],
        "dependencies": {"fact_ids": [], "source_addresses": addresses},
        "contradiction_records": [],
        "guards": _GUARDS,
        "defeaters": _defeaters(canonical_loc, matrix_id),
        "unresolved_blockers": [],
        "dependent_fact_ids": list(dependents or []),
        "dependent_projection_ids": ["proj:p007geo:%s" % loc_us(canonical_loc)],
        "producer": PRODUCER,
    }
    if chain_input:
        fact["dependencies"]["fact_ids"] = [chain_input]
        fact["derivation_chain"] = [{
            "step_id": "p007geo.%s.%s" % (fact_kind, loc_us(canonical_loc)),
            "operation": "deterministic re-application of the certified "
                         "attachment-geometry span to the same NFC surface",
            "input_fact_ids": [chain_input],
            "output": "derived %s over the certified clitic span" % fact_type,
        }]
    return fact


def build_geometry_facts(geometry_rows, loc_index):
    facts = []
    errors = []
    for row in geometry_rows:
        loc = row["canonical_loc"]
        matrix_id = row["matrix_id"]
        universe_surface = loc_index.get(loc)
        if universe_surface is None:
            errors.append("%s: no universe surface in the loc index" % loc)
            continue
        geometry, reason = clitic_geometry(universe_surface)
        if geometry is None:
            errors.append("%s: geometry not deterministic: %s" % (loc, reason))
            continue
        tier = alignment_tier(universe_surface, row["surface"])
        if tier == "misaligned":
            errors.append("%s: matrix surface does not reach rasm equality "
                          "with the universe surface" % loc)
            continue
        ids = fact_ids_for(loc)
        geom_value = {
            "surface_nfc": geometry["surface_nfc"],
            "component_surface": geometry["component_surface"],
            "char_span": geometry["char_span"],
            "base_letter_span": geometry["base_letter_span"],
            "kasra_sign_present": geometry["kasra_sign_present"],
            "assimilation_shadda_in_span": geometry["assimilation_shadda_in_span"],
            "lam_vowel": row.get("lam_vowel"),
        }
        recon_value = {
            "surface_nfc": geometry["surface_nfc"],
            "clitic": geometry["component_surface"],
            "remainder": geometry["host_remainder_surface"],
            "nfc_identity": True,
            "universe_alignment": tier,
            "matrix_surface_nfc": nfc(row["surface"]),
        }
        bound_value = {
            "surface_nfc": geometry["surface_nfc"],
            "boundary_char_index": geometry["char_span"]["end"],
            "boundary_base_letter_index": 1,
            "host_remainder_surface": geometry["host_remainder_surface"],
            "host_base_letter_count": geometry["host_base_letter_count"],
            "host_base_letter_basis": "uthmani rasm skeleton (dagger alef is "
                                      "a vowel sign, not a skeleton letter)",
            "claim_scope": "attachment geometry only — no host identity, "
                           "function, sense or meaning claim",
        }
        facts.append(build_fact(loc, matrix_id, "geom", "attachment_geometry",
                                geom_value, "direct_source_attestation",
                                dependents=[ids["recon"], ids["bound"]]))
        facts.append(build_fact(loc, matrix_id, "recon", "surface_reconstruction_nfc",
                                recon_value,
                                "deterministic_derivation_from_certified_facts",
                                chain_input=ids["geom"]))
        facts.append(build_fact(loc, matrix_id, "bound", "token_host_boundary",
                                bound_value,
                                "deterministic_derivation_from_certified_facts",
                                chain_input=ids["geom"]))
    return facts, errors


class _CachedStore(TypedFactCertificationStore):
    """Same engine, cached event list (the trail is written through the parent
    class; only the O(n^2) re-read is avoided). The committed trail is still
    validated by ``tools/certify_typed_fact.py --validate`` afterwards."""

    def __init__(self, directory):
        super().__init__(directory)
        self._cache = super()._events()

    def _events(self):
        return self._cache

    def _append_event(self, event):
        written = super()._append_event(event)
        self._cache.append(json.loads(json.dumps(written, ensure_ascii=False,
                                                 sort_keys=True)))
        return written


def certify_facts(facts, store_dir):
    store = _CachedStore(store_dir)
    for fact in facts:
        store.register(fact, contract_id=CONTRACT_ID, actor=ACTOR, timestamp=TS)
    by_kind = {}
    for fact in facts:
        by_kind.setdefault(fact["fact_id"].rsplit(":", 1)[-1], []).append(fact)
    # geometry facts first (the derivation inputs), then the derived facts.
    for kind in ("geom", "recon", "bound"):
        for fact in by_kind.get(kind, []):
            store.transition(fact["fact_id"], "review_required", actor=ACTOR,
                             timestamp=TS,
                             reason="deterministic evidence bundle assembled")
            store.transition(fact["fact_id"], "certified", actor=ACTOR,
                             timestamp=TS, packet_dir=ROOT,
                             reason="mechanical basis complete: matrix row + "
                                    "universe alignment + NFC reconstruction proof")
    return len(store.certified_fact_ids())


# ---------------------------------------------------------------------------
# reverse universe
# ---------------------------------------------------------------------------

EVIDENCE_POLICY_BY_PARTITION = {
    GEOMETRY_PARTITION: "direct_source",
    "direct-source-attested-function": "direct_source",
    "two-vote-required": "two_vote",
    "scholar-required": "scholar_adjudication",
    "rejected-false-candidate": "none",
}


def pilot_locations():
    with io.open(os.path.join(PILOT_DIR, "locations.json"), encoding="utf-8") as handle:
        locations = json.load(handle)
    return {occ["occurrence_id"].split(":", 1)[1]: occ
            for occ in locations["occurrences"]}


def _facet(state, policy, refs=None):
    facet = {"state": state, "evidence_policy": policy}
    if refs:
        facet["refs"] = refs
    return facet


def build_universe_row(cls_row, matrix_row, loc_index, appearance_classes,
                       pilot_by_loc, mcp_refs_by_loc):
    loc = cls_row["canonical_loc"]
    partition = cls_row["partition"]
    is_geometry = partition == GEOMETRY_PARTITION
    is_pilot = loc in pilot_by_loc
    universe_surface = loc_index.get(loc)
    tier = (alignment_tier(universe_surface, matrix_row["surface"])
            if universe_surface is not None else "no_universe_surface")

    morpheme_span = None
    geometry_certification = {"state": "none"}
    if is_geometry:
        geometry, _reason = clitic_geometry(universe_surface)
        ids = fact_ids_for(loc)
        morpheme_span = {
            "component_surface": geometry["component_surface"],
            "char_span": geometry["char_span"],
            "base_letter_span": geometry["base_letter_span"],
            "host_remainder_surface": geometry["host_remainder_surface"],
        }
        geometry_certification = {
            "state": "certified",
            "fact_ids": [ids["geom"], ids["recon"], ids["bound"]],
            "store": "qamus/certification/p007-geometry-wave/events.jsonl",
        }

    by_class = {"P": 0, "V": 0, "N": 0}
    for appearance_id in matrix_row.get("appearance_ids", []):
        page_class = appearance_classes.get(appearance_id)
        if page_class not in by_class:
            raise SystemExit("appearance %s has unknown page class %r"
                             % (appearance_id, page_class))
        by_class[page_class] += 1

    mcp_refs = [ref["ref"] for ref in mcp_refs_by_loc.get(loc, [])]
    pilot_key = loc_us(loc)
    if is_pilot:
        mcp_refs.append("qamus/examples/p007-li-pilot/mcp-evidence.jsonl#analyze_word:%s" % loc)

    # --- facet states (evidence-policy routing recorded, never certified here)
    policy = EVIDENCE_POLICY_BY_PARTITION[partition]
    route = cls_row.get("route")
    if is_pilot:
        pilot_fact = "qamus/examples/p007-li-pilot/certification/events.jsonl#fact:p00slice:%s" % pilot_key
        entry_edge = {"state": "certified", "entry_id": ENTRY_ID,
                      "ref": "qamus/examples/p007-li-pilot/transclusion-edges.jsonl#mocc:p007:%s" % loc}
        sense_edge = {"state": "certified", "entry_id": ENTRY_ID, "sense_n": SENSE_N,
                      "ref": entry_edge["ref"]}
        attachment = _facet("certified", "direct_source", [pilot_fact + ":seg"])
        function = _facet("certified", "direct_source", [pilot_fact + ":func"])
        governor = _facet("certified", "two_vote", [pilot_fact + ":gov"])
        governed = _facet("certified", "two_vote", [pilot_fact + ":case"])
        case = _facet("certified", "two_vote", [pilot_fact + ":case"])
    elif partition == "rejected-false-candidate":
        entry_edge = {"state": "rejected", "entry_id": ENTRY_ID,
                      "defeater": cls_row.get("defeater")}
        sense_edge = {"state": "rejected", "entry_id": ENTRY_ID,
                      "defeater": cls_row.get("defeater")}
        attachment = _facet("rejected", "none")
        function = _facet("rejected", "none")
        governor = _facet("not_applicable", "none")
        governed = _facet("not_applicable", "none")
        case = _facet("not_applicable", "none")
    else:
        entry_edge = {"state": "candidate", "entry_id": ENTRY_ID}
        sense_edge = {"state": "candidate", "entry_id": ENTRY_ID}
        attachment = _facet("geometry_certified" if is_geometry else "candidate",
                            policy)
        function = _facet("pending", policy)
        governor = _facet("pending", "two_vote")
        governed = _facet("pending", "two_vote")
        case = _facet("pending", "two_vote")

    # --- exact blocker
    if partition == "rejected-false-candidate":
        blocker = None
    elif is_pilot:
        blocker = ("owner gate: candidate projection NOT deployed; entry, sense, "
                   "function, governor and case are pilot-certified — deployment "
                   "is the only remaining gate")
    elif is_geometry:
        blocker = ("function/sense certification blocked: no direct-source MCP "
                   "attestation captured for this occurrence yet (geometry is "
                   "certified; identity/function sit OUTSIDE the geometry-wave "
                   "owner boundary)")
    elif partition == "direct-source-attested-function":
        blocker = ("blocked: requires 1 direct-source MCP attestation "
                   "(route: %s)" % route)
    elif partition == "two-vote-required":
        blocker = ("blocked: requires a validate_two_vote_artifacts-passing "
                   "two-vote bundle (route: %s)" % route)
    else:
        blocker = ("blocked: requires owner/scholar adjudication "
                   "(route: %s)" % route)

    reverse_trace_refs = ["qamus/lattice/p007-population-classification.jsonl#%s"
                          % cls_row["matrix_id"]]
    if is_geometry:
        reverse_trace_refs.append(
            "qamus/certification/p007-geometry-wave/typed-facts.jsonl#fact:p007geo:%s:geom"
            % pilot_key)
    if is_pilot:
        reverse_trace_refs.append(
            "qamus/examples/p007-li-pilot/reverse-trace.json#proj:p00slice:%s" % pilot_key)

    if is_pilot:
        projection_state = "candidate-projection-not-deployed"
    elif is_geometry:
        projection_state = "geometry-certified-projection-pending"
    else:
        projection_state = "none"

    return {
        "schema": "qamus.p007_reverse_universe.v1",
        "scope": SCOPE,
        "matrix_id": cls_row["matrix_id"],
        "occurrence_id": cls_row["occurrence_id"],
        "canonical_loc": loc,
        "particle_entry_id": ENTRY_ID,
        "particle_source_key": SOURCE_KEY,
        "surface": nfc(matrix_row["surface"]),
        "universe_surface": nfc(universe_surface) if universe_surface else None,
        "universe_alignment": tier,
        "partition": partition,
        "route": route,
        "defeater": cls_row.get("defeater"),
        "rung1_eligible": cls_row.get("rung1_eligible"),
        "host_visible": matrix_row.get("host_visible"),
        "morpheme_span": morpheme_span,
        "edges": {
            "entry_candidate_edge": {"entry_id": ENTRY_ID,
                                     "state": entry_edge["state"] if entry_edge["state"] != "certified" else "superseded_by_certified"},
            "entry_certified_edge": entry_edge if entry_edge["state"] == "certified" else {"state": "none"},
            "sense_edge": sense_edge,
            "attachment": attachment,
            "function": function,
            "governor": governor,
            "governed_expression": governed,
            "case": case,
        },
        "geometry_certification": geometry_certification,
        "evidence_policy": policy,
        "mcp_evidence_refs": mcp_refs,
        "review_state": partition,
        "projection_state": projection_state,
        "appearances": {
            "count": matrix_row.get("appearance_count"),
            "ids": matrix_row.get("appearance_ids", []),
            "by_page_class": by_class,
        },
        "reverse_trace_refs": reverse_trace_refs,
        "blocker": blocker,
        "mode": "candidate",
    }


def build_meta(rows, fact_count, pilot_count):
    partitions = {}
    for row in rows:
        partitions[row["partition"]] = partitions.get(row["partition"], 0) + 1
    geometry_rows = partitions.get(GEOMETRY_PARTITION, 0)
    direct_rows = partitions.get("direct-source-attested-function", 0)
    return {
        "schema": "qamus.p007_reverse_universe_meta.v1",
        "scope": SCOPE,
        "builder": PRODUCER,
        "mode": "candidate — no live mutation; geometry certification only",
        "rows": len(rows),
        "appearances_total": sum(row["appearances"]["count"] for row in rows),
        "appearances_by_page_class": {
            page_class: sum(row["appearances"]["by_page_class"][page_class] for row in rows)
            for page_class in ("P", "V", "N")
        },
        "inputs": {
            "classification": "qamus/lattice/p007-population-classification.jsonl",
            "matrix": "qamus/lattice/particle-occurrence-matrix.jsonl",
            "loc_surface_index": "qamus/indexes/quran-loc-surface/index.jsonl",
            "ayah_universe": "qamus/lattice/example-ayah-universe.jsonl",
            "mcp_evidence_refs": "qamus/lattice/p007-mcp-evidence-refs.jsonl",
            "pilot": "qamus/examples/p007-li-pilot/",
            "geometry_store": "qamus/certification/p007-geometry-wave/events.jsonl",
        },
        "state_tallies": {
            "P007_OCCURRENCES_DISCOVERED": {
                "complete": True, "rows": len(rows),
                "basis": "all p007 matrix rows carried into the reverse universe"},
            "P007_CANDIDATES_DISPOSITIONED": {
                "complete": True, "rows": len(rows), "partitions": partitions},
            "P007_ENTRY_LINKS_CERTIFIED": {
                "rows": pilot_count,
                "basis": "P007_LI_NOUN_HOST_PILOT entry edges — nothing else at entry level"},
            "P007_SENSE_EDGES_CERTIFIED": {
                "rows": pilot_count,
                "basis": "P007_LI_NOUN_HOST_PILOT sense-2 edges"},
            "P007_GEOMETRY_CERTIFIED": {
                "rows": geometry_rows, "facts": fact_count, "wave": SCOPE,
                "basis": "mechanical attachment geometry / reconstruction / "
                         "boundary ONLY — not identity, function or sense"},
            "P007_FUNCTION_CERTIFIED": {
                "rows": pilot_count, "basis": "pilot contextual_function facts"},
            "P007_GOVERNOR_CASE_CERTIFIED": {
                "rows": pilot_count, "basis": "pilot governor/case facts (two-vote rung)"},
            "P007_DIRECT_SOURCE_FUNCTION_QUEUE": {
                "rows": direct_rows + geometry_rows - pilot_count,
                "components": {
                    "direct-source-attested-function": direct_rows,
                    "deterministic-attachment-geometry function queue": geometry_rows - pilot_count,
                }},
            "P007_TWO_VOTE_QUEUE": {"rows": partitions.get("two-vote-required", 0)},
            "P007_SCHOLAR_QUEUE": {"rows": partitions.get("scholar-required", 0)},
            "P007_REJECTED_CLOSED": {"rows": partitions.get("rejected-false-candidate", 0)},
        },
        "honesty": [
            "Geometry certification is NOT entry/sense/function certification: "
            "entry-level certified stays at the pilot 12.",
            "Every tally above is recomputed (never trusted) by "
            "tools/validate_p007_universe.py.",
            "The pilot 12 are a subset of the %d geometry rows; queue tallies "
            "subtract them exactly once." % 0,
        ],
    }


SPOT_CHECK_LOCS = [
    "1:2:2", "2:2:7", "2:34:5", "2:118:23", "2:187:63", "3:138:3", "4:11:5",
    "5:3:9", "7:11:9", "9:120:3", "12:62:2", "17:78:3", "20:14:11", "23:20:9",
    "24:35:44", "33:5:2", "37:46:3", "43:56:4", "64:16:9", "70:16:2",
]


def build_spot_worksheet(geometry_rows, loc_index):
    by_loc = {row["canonical_loc"]: row for row in geometry_rows}
    rows = []
    for loc in SPOT_CHECK_LOCS:
        cls_row = by_loc.get(loc)
        if cls_row is None:
            raise SystemExit("spot-check loc %s is not a geometry row" % loc)
        surface = nfc(loc_index[loc])
        geometry, _reason = clitic_geometry(surface)
        rows.append({
            "canonical_loc": loc,
            "surface_nfc": surface,
            "codepoints": ["%04X" % ord(ch) for ch in surface],
            "computed": {
                "component_surface": geometry["component_surface"],
                "char_span": geometry["char_span"],
                "base_letter_span": geometry["base_letter_span"],
                "host_remainder_surface": geometry["host_remainder_surface"],
                "host_base_letter_count": geometry["host_base_letter_count"],
            },
        })
    return {
        "schema": "qamus.p007_geometry_spot_worksheet.v1",
        "scope": SCOPE,
        "note": "codepoint worksheet for the 20-row manual spot check; the "
                "reviewed verdicts live in spot-check.json",
        "rows": rows,
    }


def generate(write_store=True):
    cls_rows = read_jsonl(CLASSIFICATION)
    cls_rows.sort(key=lambda row: loc_sort_key(row["canonical_loc"]))
    matrix_by_id = {row["matrix_id"]: row for row in read_jsonl(MATRIX)
                    if row.get("particle_source_key") == SOURCE_KEY}
    loc_index = load_loc_index()
    appearance_classes = load_appearance_classes()
    mcp_refs_by_loc = {}
    for ref in read_jsonl(MCP_REFS):
        mcp_refs_by_loc.setdefault(ref["canonical_loc"], []).append(ref)
    pilot_by_loc = pilot_locations()

    geometry_rows = [row for row in cls_rows if row["partition"] == GEOMETRY_PARTITION]
    facts, errors = build_geometry_facts(geometry_rows, loc_index)
    if errors:
        for error in errors:
            print("ERROR " + error, file=sys.stderr)
        raise SystemExit("geometry read-off failed for %d row(s)" % len(errors))

    os.makedirs(WAVE_DIR, exist_ok=True)
    write_jsonl(os.path.join(WAVE_DIR, "typed-facts.jsonl"), facts)

    events_path = os.path.join(WAVE_DIR, "events.jsonl")
    if write_store and not os.path.exists(events_path):
        certified = certify_facts(facts, WAVE_DIR)
        print("certification store written: %d facts certified" % certified)
    else:
        print("certification store present — not rebuilt (append-only)")

    universe_rows = []
    for cls_row in cls_rows:
        matrix_row = matrix_by_id.get(cls_row["matrix_id"])
        if matrix_row is None:
            raise SystemExit("classification row %s has no matrix row" % cls_row["matrix_id"])
        universe_rows.append(build_universe_row(
            cls_row, matrix_row, loc_index, appearance_classes,
            pilot_by_loc, mcp_refs_by_loc))
    write_jsonl(UNIVERSE_OUT, universe_rows)

    meta = build_meta(universe_rows, len(facts), len(pilot_by_loc))
    # honesty note index 2 carries the geometry-row count
    meta["honesty"][2] = ("The pilot 12 are a subset of the %d geometry rows; "
                          "queue tallies subtract them exactly once."
                          % len(geometry_rows))
    write_json(META_OUT, meta)

    worksheet = build_spot_worksheet(geometry_rows, loc_index)
    write_json(os.path.join(WAVE_DIR, "spot-check-worksheet.json"), worksheet)

    return {
        "universe_rows": len(universe_rows),
        "geometry_rows": len(geometry_rows),
        "typed_facts": len(facts),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-store", action="store_true",
                        help="emit facts/universe only; never touch the event trail")
    args = parser.parse_args(argv)
    stats = generate(write_store=not args.no_store)
    print("P007_GEOMETRY_WAVE artifacts written:")
    for key, value in sorted(stats.items()):
        print("  %s: %d" % (key, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
