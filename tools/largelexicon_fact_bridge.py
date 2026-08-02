#!/usr/bin/env python3
"""The smallest correct typed bridge from carried largelexicon rows to typed claims.

What this bridge does
---------------------
For one canonical Qurʾānic occurrence, addressed **loc-first** from a carried
target-schema crosswalk row, it collects the carried lemma/form/stem rows whose
written surface is byte-exactly the occurrence surface, and emits a
``qamus.typed_claim_contract.v1`` record holding those preserved candidates.

What this bridge is NOT
-----------------------
It is not a disambiguator and it never certifies anything. In particular it never
treats any of the following as a lexical claim:

* the crosswalk ``entry_id`` — that is the entry page whose card DISPLAYS the
  word (page context), not a claim that the word instantiates that entry's
  lexeme;
* a surface match after normalisation — ``norm_only_match`` is a
  ``never_auto_resolve`` trigger in the gate SSOT, so it abstains, never resolves;
* a shared root or a root-family relation — root sharing never implies entry
  identity;
* a candidate graph edge from the lexeme-join lattice — a candidate edge is not
  a certified edge;
* the first row of a candidate list — zero, one, and many candidates are all
  preserved as-is, and a collision abstains with a precise blocker.

Every emitted record is candidate-or-unresolved, learner-invisible, and carries
its source addresses plus the exact carried-table dependency hashes, so a stale
or validation-red target release invalidates it mechanically.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import promote_largelexicon_target_schema as promoter  # noqa: E402,F401
from largelexicon_table_reader import LargelexiconTargetTables  # noqa: E402
from tools import typed_claim_contract  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
LEXEME_JOIN_EDGES = ROOT / "qamus" / "lattice" / "lexeme-join-edges.jsonl"
LOC_SURFACE_INDEX = ROOT / "qamus" / "indexes" / "quran-loc-surface" / "index.jsonl"
# Committed bundles that may carry canonical typed lexeme/form edges. Membership is
# declared, never discovered, and every bundle is hashed into the dependency record.
TYPED_GRAPH_BUNDLES = (
    "qamus/examples/proof-verb/typed-edge-graph.jsonl",
    "qamus/examples/proof-noun-sufaha/typed-edge-graph.jsonl",
    "qamus/examples/proof-particle/particle-graph-edges.jsonl",
    "qamus/examples/p007-li-pilot/transclusion-edges.jsonl",
)
TYPED_GRAPH_SCHEMA = "qamus.graph_edge.v1"
LEXICAL_EDGE_TYPES = frozenset({"lexeme_entry_edge", "form_entry_edge"})
# A candidate edge is not a certified edge: only these statuses may support identity.
ACCEPTED_EDGE_STATUSES = frozenset({"certified", "deterministic_exact"})
# An occurrence loc is read ONLY from an unambiguous o<S>:<A>:<W> segment. A card
# address (c<S>:<A>) is an ayah reference, not a token occurrence, and is never
# promoted into one.
OCCURRENCE_LOC_RE = re.compile(r"(?:^|:)o(\d{1,3}):(\d{1,3}):(\d{1,3})(?::|$)")
PRODUCER_ID = "tools/largelexicon_fact_bridge.py"
PRODUCER_VERSION = "1.0.0"
PROJECTOR_ID = "largelexicon.carried_lexeme_candidate.v1"
RULE_ID = "largelexicon-carried-loc-first-exact-surface-candidate"
# Abstentions are a distinct registered output with their own never_auto_resolve
# contract, so their refusal rests on a real producer gate rather than on a
# projector/fact-type incoherence report.
ABSTENTION_PROJECTOR_ID = "largelexicon.bridge_abstention.v1"
ABSTENTION_RULE_ID = "largelexicon-carried-admission-refusal"
CONTRACT_PREFIX = "llxbridge"
ACCEPTED_CROSSWALK_STATUS = "canonical_crosswalk_accepted"
ACCEPTED_TRANSCLUSION_ROUTE = "entry_card_qword_to_canonical_crosswalk_accepted"
FORBIDDEN_BINDING_PREFIXES = ("missing-loc|", "sarf:surface:")
REQUIRED_DEPENDENCY_KINDS = frozenset({"qword_denominator_row", "source_card"})

DEFAULT_OUTPUT = ROOT / "out" / "largelexicon-fact-bridge" / "typed-claims.jsonl"
# Prohibited classes for committed public fixtures: internal provenance labels,
# source/gloss prose carriers, OCR fields, external source names, URLs and paths.
PROHIBITED_FIXTURE_KEYS = (
    "informed_by", "source_prose", "gloss_text", "source_text", "translation",
    "tafsir", "ocr", "ocr_text", "scan_text", "source_quotation", "external_source",
)
PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"(?:/srv/|/var/www/|/home/[a-z]/)", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\"),
)

MATERIALIZATION_TARGET = {
    "artifact": "out/largelexicon-fact-bridge/typed-claims.jsonl",
    "field": "facts",
    "live_mutation_allowed": False,
    "public_materialization_allowed": False,
}

# Closed blocker vocabulary. Every abstention names exactly one of these, and the
# projection status it maps to. Nothing here is ever "resolved by picking one".
BLOCKER_STATUS = {
    "quarantined_or_flagged_source_row": "blocked",
    "row_not_in_validated_carried_authority": "blocked",
    "dependency_id_not_in_authority": "blocked",
    "source_card_authority_unavailable": "source_gap",
    "unverified_diagnostic_inputs": "blocked",
    "missing_dependency_release": "blocked",
    "norm_only_surface_match": "blocked",
    "loc_not_in_canonical_index": "blocked",
    "loc_surface_disagreement": "blocked",
    "wbw_loc_disagreement": "blocked",
    "unresolved_canonical_loc": "source_gap",
    "crosswalk_packet_not_accepted": "source_gap",
    "missing_typed_graph_evidence": "source_gap",
    "no_carried_lexical_support": "producer_pending",
    "page_context_only_no_lexical_edge": "unresolved",
    "root_family_relation_not_lexeme_identity": "unresolved",
    "non_certified_graph_edge_only": "unresolved",
    "typed_edge_identity_disagreement": "unresolved",
    "lexical_collision_requires_context": "unresolved",
}

BLOCKER_REASONS = {
    "quarantined_or_flagged_source_row": "the crosswalk row did not carry onto the target schema",
    "row_not_in_validated_carried_authority": (
        "this exact row body is not a member of the validated carried crosswalk authority; a detached, "
        "altered, schema-downgraded or invented row can never be bridged"
    ),
    "dependency_id_not_in_authority": (
        "a declared source dependency id does not resolve in the validated denominator authority; "
        "a correct kind label is not a membership proof"
    ),
    "source_card_authority_unavailable": (
        "the target release supplies no authority able to prove this row's source-card membership"
    ),
    "unverified_diagnostic_inputs": (
        "these inputs were built for diagnostics and were never verified, so they are "
        "structurally unable to support a candidate"
    ),
    "missing_dependency_release": "the crosswalk row lacks its qword-denominator and source-card dependencies",
    "norm_only_surface_match": "only a normalized surface match exists; norm() never certifies identity",
    "unresolved_canonical_loc": "no canonical quran loc; a diagnostic binding key is never reuse authority",
    "crosswalk_packet_not_accepted": "the crosswalk row is packet-ready or demoted, not an accepted address",
    "no_carried_lexical_support": "no carried lemma/form/stem row documents this exact written surface",
    "page_context_only_no_lexical_edge": "the entry only displays this word on a card; page context is never a lexical claim",
    "root_family_relation_not_lexeme_identity": "support is root agreement only; root sharing never implies entry identity",
    "non_certified_graph_edge_only": "support is a candidate graph edge only; a candidate edge is not a certified edge",
    "lexical_collision_requires_context": "more than one entry documents this exact surface; context must decide",
    "missing_typed_graph_evidence": (
        "no canonical typed lexeme/form edge with accepted status agrees with this occurrence loc, "
        "written surface and entry; exact surface is discovery only"
    ),
    "typed_edge_identity_disagreement": "a typed edge exists at this loc but its surface or entry does not agree",
    "loc_not_in_canonical_index": "the canonical loc is absent from the committed quran loc-surface index",
    "loc_surface_disagreement": "the written surface disagrees with the canonical loc-surface index",
    "wbw_loc_disagreement": "the canonical wbw loc does not agree with the canonical quran loc",
}

GUARD_REASONS = {
    "loc_first_canonical_address": "the occurrence is addressed by canonical quran loc, not by surface or position",
    "carried_target_schema_rows_only": "every consumed row passed the unchanged target schema as a carried row",
    "byte_exact_written_surface": "candidates matched the written surface byte-exactly, never after normalization",
    "crosswalk_entry_id_is_page_context": "the crosswalk entry_id was recorded as page context and never as a lexical edge",
    "root_family_never_lexeme_edge": "root agreement was recorded as a relation and never resolved an identity",
    "candidate_edge_never_certified": "graph support was recorded as candidate evidence and never as certification",
    "release_dependency_bound": "the carried-table digests are recorded so a stale release invalidates this record",
}


class BridgeError(RuntimeError):
    """Raised when the bridge cannot run against a trustworthy input set."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_body_digest(row: dict[str, Any]) -> str:
    """Deterministic digest of an exact canonical row body."""

    return hashlib.sha256(_canonical(row).encode("utf-8")).hexdigest()


def canonical_line_bytes(value: Any) -> bytes:
    return _canonical(value).encode("utf-8") + b"\n"


def _fact_id(core: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(core).encode("utf-8")).hexdigest()


def review_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def is_canonical_loc(value: Any) -> bool:
    if not isinstance(value, str) or any(value.startswith(prefix) for prefix in FORBIDDEN_BINDING_PREFIXES):
        return False
    parts = value.split(":")
    # Coordinates are 1-based everywhere in the corpus: surah, ayah and word all
    # start at 1, so 0:0:0 is structurally impossible, never merely absent.
    return len(parts) == 3 and all(part.isdigit() and 1 <= len(part) <= 3 and int(part) >= 1 for part in parts)


GUARD_REASONS.update(
    {
        "canonical_typed_edge_required": "identity required an accepted canonical typed lexeme/form edge, not a surface match",
        "canonical_loc_surface_verified": "the loc and its written surface were verified against the committed canonical index",
        "typed_graph_digest_bound": "the typed-graph bundle digests are recorded so graph drift fails freshness",
    }
)


def occurrence_loc_of(node_id: str) -> str | None:
    """Read an unambiguous occurrence loc from a node id, or nothing."""

    match = OCCURRENCE_LOC_RE.search(str(node_id or ""))
    return ":".join(match.groups()) if match else None


EDGE_ID_RE = re.compile(r"^edge:[0-9a-f]{16,}$")
EDGE_ID_DIGEST_LENGTH = 24
# Only these source-node kinds carry an occurrence; a card is an ayah reference.
OCCURRENCE_BEARING_NODE_TYPES = frozenset({"selected-word", "occurrence", "morpheme-occurrence"})
NODE_TYPE_PREFIX = {
    "selected-word": "selected-word:",
    "occurrence": "occurrence:",
    "morpheme-occurrence": "mocc:",
}


def edge_content_digest(edge: dict[str, Any]) -> str:
    """Deterministic digest of an edge's content, excluding its own identifier."""

    body = {key: value for key, value in edge.items() if key != "edge_id"}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def canonical_edge_id(edge: dict[str, Any]) -> str:
    """The one edge id derivable from this exact governed edge content."""

    return "edge:" + edge_content_digest(edge)[:EDGE_ID_DIGEST_LENGTH]


def typed_edge_errors(edge: dict[str, Any]) -> list[str]:
    """Closed content contract for an eligible canonical typed lexeme/form edge.

    An edge only establishes lexeme/entry identity when it is RECONSTRUCTIBLE:
    a content-shaped identifier, a named producer, an accepted non-candidate
    status on a lexeme/form relation, an exact occurrence node, an exact written
    surface, at least one evidence address, and at least one guard. Page context,
    surface resemblance, root family and lookup labels are excluded by
    ``LEXICAL_EDGE_TYPES`` and can never satisfy this contract.
    """

    problems: list[str] = []
    if not isinstance(edge, dict):
        return ["edge is not a record"]
    if edge.get("schema") != TYPED_GRAPH_SCHEMA:
        problems.append("schema is not " + TYPED_GRAPH_SCHEMA)
    if edge.get("edge_type") not in LEXICAL_EDGE_TYPES:
        problems.append("edge_type is not a lexeme/form identity edge")
    if edge.get("status") not in ACCEPTED_EDGE_STATUSES:
        problems.append("status is not an accepted (non-candidate) status")
    if edge.get("to_node_type") != "entry" or not str(edge.get("to_node_id", "")).startswith("entry:"):
        problems.append("edge does not terminate on an entry node")
    if not str((edge.get("details") or {}).get("surface") or ""):
        problems.append("edge carries no written surface")
    if not edge.get("from_node_id"):
        problems.append("edge carries no source node")
    if occurrence_loc_of(edge.get("from_node_id")) is None:
        problems.append("edge carries no unambiguous occurrence loc")
    edge_id = str(edge.get("edge_id") or "")
    if not EDGE_ID_RE.fullmatch(edge_id):
        problems.append("edge_id is absent or is not a content-shaped identifier")
    elif edge_id != canonical_edge_id(edge):
        # A well-shaped but stale or all-zero id is not derived from this content.
        problems.append("edge_id is not the canonical derivation of this edge content")
    from_node_type = str(edge.get("from_node_type") or "")
    if from_node_type not in OCCURRENCE_BEARING_NODE_TYPES:
        problems.append("from_node_type %r does not carry an occurrence" % from_node_type)
    elif not str(edge.get("from_node_id") or "").startswith(NODE_TYPE_PREFIX[from_node_type]):
        problems.append("from_node_id does not agree with the declared from_node_type")
    producer = edge.get("producer")
    if not isinstance(producer, dict) or not producer.get("id") or not producer.get("version"):
        problems.append("edge carries no identified producer")
    evidence = edge.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        problems.append("edge carries no evidence")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict) or not str(item.get("address") or ""):
                problems.append(f"evidence[{index}] carries no source address")
                break
    guards = edge.get("guards")
    if not isinstance(guards, list) or not guards or not all(str(item) for item in guards):
        problems.append("edge carries no guards")
    return problems


def load_typed_graph(paths: Iterable[str] | None = None) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Index accepted canonical typed lexeme/form edges by occurrence loc.

    Only edges that pass the closed contract AND carry an unambiguous occurrence
    loc are eligible. Nothing is inferred: a card-level address is not turned into
    a token occurrence, and a candidate-status edge never becomes support.
    """

    index: dict[str, list[dict[str, Any]]] = {}
    bundles: list[dict[str, Any]] = []
    for relative in sorted(paths if paths is not None else TYPED_GRAPH_BUNDLES):
        path = ROOT / relative
        entry = {
            "eligible_edge_count": 0,
            "path": relative,
            "present": path.exists(),
            "row_count": 0,
            "schema": TYPED_GRAPH_SCHEMA,
            "sha256": None,
        }
        if path.exists():
            payload = path.read_bytes()
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            for line in payload.decode("utf-8").splitlines():
                if not line.strip():
                    continue
                edge = json.loads(line)
                entry["row_count"] += 1
                if typed_edge_errors(edge):
                    continue
                loc = occurrence_loc_of(edge.get("from_node_id"))
                if loc is None:
                    continue
                index.setdefault(loc, []).append(edge)
                entry["eligible_edge_count"] += 1
        bundles.append(entry)
    digest = hashlib.sha256(_canonical(bundles).encode("utf-8")).hexdigest()
    return index, {
        "bundles": bundles,
        "eligible_edge_count": sum(item["eligible_edge_count"] for item in bundles),
        "eligible_loc_count": len(index),
        "typed_graph_sha256": digest,
    }


def _file_digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def load_loc_surface_index(path: Path | None = None) -> tuple[dict[str, str], dict[str, Any]]:
    """The committed canonical loc → written-surface index, plus its binding."""

    source = path or LOC_SURFACE_INDEX
    index: dict[str, str] = {}
    if source.exists():
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    index[str(row["loc"])] = str(row["surface"])
    return index, {
        "path": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source),
        "present": source.exists(),
        "row_count": len(index),
        "sha256": _file_digest(source),
    }


def load_lexeme_join_edges(path: Path | None = None) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Index the candidate lexeme-join lattice by loc, plus its binding.

    These are CANDIDATE edges only; the lattice never supports identity. It is
    still hashed into the authority binding because it steers abstention routing,
    so lattice drift must invalidate downstream records.
    """

    source = path or LEXEME_JOIN_EDGES
    edges: dict[str, list[dict[str, Any]]] = {}
    rows = 0
    if source.exists():
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    rows += 1
                    edges.setdefault(str(row.get("loc")), []).append(row)
    return edges, {
        "path": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source),
        "present": source.exists(),
        "row_count": rows,
        "sha256": _file_digest(source),
    }


REQUIRED_DEPENDENCY_FAMILIES = frozenset(
    {"form-source", "lemma-source", "qword-crosswalk", "qword-denominator", "stem-source"}
)


def dependency_family_errors(dependency_hashes: dict[str, str]) -> list[str]:
    """The carried dependency family must be exactly complete and well formed.

    A partial binding (for example ``form-source`` alone) cannot invalidate a
    record when the crosswalk, denominator, lemma or stem table drifts, so a
    candidate resting on it would be unfalsifiable. Missing, extra, empty and
    malformed families are all refused.
    """

    problems: list[str] = []
    if not isinstance(dependency_hashes, dict) or not dependency_hashes:
        return ["carried-table dependency hashes are required"]
    supplied = set(dependency_hashes)
    missing = sorted(REQUIRED_DEPENDENCY_FAMILIES - supplied)
    extra = sorted(supplied - REQUIRED_DEPENDENCY_FAMILIES)
    if missing:
        problems.append("carried dependency families are missing: " + ",".join(missing))
    if extra:
        problems.append("carried dependency families are not recognised: " + ",".join(extra))
    for family, digest in sorted(dependency_hashes.items()):
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            problems.append(f"dependency hash for {family} is not a sha256 digest")
    return problems


def verify_authority(
    *,
    dependency_hashes: dict[str, str],
    typed_edges: dict[str, list[dict[str, Any]]],
    typed_graph_meta: dict[str, Any],
    loc_surface: dict[str, str],
    loc_surface_meta: dict[str, Any],
    lexeme_join: dict[str, list[dict[str, Any]]],
    lexeme_join_meta: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Derive the VERIFIED authority object, reconciled against the supplied data.

    Candidate admission consumes this object, never the caller's parallel
    assertions: counts are recomputed from the rows, edges and index actually
    supplied, and any caller-declared count that disagrees is a refusal. Metadata
    claiming zero bundles or zero eligible edges while edges are supplied is
    therefore rejected instead of believed.
    """

    problems: list[str] = dependency_family_errors(dependency_hashes)

    if not loc_surface:
        problems.append("the canonical loc-surface index is empty; candidate admission has no loc authority")
    derived_index_rows = len(loc_surface)
    derived_lattice_rows = sum(len(rows) for rows in (lexeme_join or {}).values())
    derived_edges = sum(len(edges) for edges in (typed_edges or {}).values())
    derived_locs = len(typed_edges or {})

    def _meta(name: str, meta: dict[str, Any], derived_rows: int, content: Any) -> dict[str, Any]:
        content_digest = hashlib.sha256(_canonical(content).encode("utf-8")).hexdigest()
        if not isinstance(meta, dict) or not meta.get("present"):
            problems.append(f"{name}: authority binding is missing")
            return {"content_sha256": content_digest, "path": None, "present": False,
                    "row_count": derived_rows, "sha256": None}
        declared = str(meta.get("sha256"))
        if not re.fullmatch(r"[0-9a-f]{64}", declared):
            problems.append(f"{name}: authority digest is missing or malformed")
        if "row_count" in meta and meta.get("row_count") != derived_rows:
            problems.append(
                "%s: declared row_count %r disagrees with the %d supplied rows"
                % (name, meta.get("row_count"), derived_rows)
            )
        # A digest is only authority when it is RECOMPUTED. A declared repository
        # path must exist and hash to the declared digest; anything else must
        # match the deterministic digest of the content actually supplied, so a
        # well-shaped invented digest, a nonexistent path, and same-count content
        # drift are all refused.
        declared_path = str(meta.get("path") or "")
        if declared_path and "://" not in declared_path:
            candidate_path = ROOT / declared_path
            if not candidate_path.exists():
                problems.append(f"{name}: declared authority path does not exist: {declared_path}")
            else:
                actual = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
                if actual != declared:
                    problems.append(f"{name}: declared digest does not match the file at {declared_path}")
        elif declared != content_digest:
            problems.append(
                f"{name}: declared digest does not match the deterministic digest of the supplied content"
            )
        return {
            "content_sha256": content_digest,
            "path": meta.get("path"),
            "present": True,
            "row_count": derived_rows,
            "sha256": meta.get("sha256"),
        }

    index_binding = _meta("canonical_loc_index", loc_surface_meta, derived_index_rows,
                          dict(sorted((loc_surface or {}).items())))
    lattice_binding = _meta("lexeme_join_lattice", lexeme_join_meta, derived_lattice_rows,
                            {key: (lexeme_join or {})[key] for key in sorted(lexeme_join or {})})

    bundles: list[dict[str, Any]] = []
    if not isinstance(typed_graph_meta, dict):
        problems.append("typed_graph: metadata is missing")
        typed_graph_meta = {}
    digest = str(typed_graph_meta.get("typed_graph_sha256"))
    if digest == "unbound" or not re.fullmatch(r"[0-9a-f]{64}", digest):
        problems.append("typed_graph: digest is unbound, missing or malformed")
    declared_bundles = typed_graph_meta.get("bundles")
    if not isinstance(declared_bundles, list):
        problems.append("typed_graph: bundle list is missing")
        declared_bundles = []
    declared_eligible = sum(
        int(bundle.get("eligible_edge_count") or 0)
        for bundle in declared_bundles
        if isinstance(bundle, dict)
    )
    for index, bundle in enumerate(declared_bundles):
        if not isinstance(bundle, dict):
            problems.append(f"typed_graph: bundle[{index}] is not a record")
            continue
        if bundle.get("present") and not re.fullmatch(r"[0-9a-f]{64}", str(bundle.get("sha256"))):
            problems.append(f"typed_graph: bundle[{index}] digest is malformed")
        bundles.append(bundle)
    if derived_edges and not [item for item in bundles if item.get("present")]:
        problems.append(
            "typed_graph: %d eligible edges were supplied but no present bundle accounts for them"
            % derived_edges
        )
    if bundles and declared_eligible != derived_edges:
        problems.append(
            "typed_graph: bundles declare %d eligible edges but %d were supplied"
            % (declared_eligible, derived_edges)
        )
    for key in ("eligible_edge_count", "eligible_loc_count"):
        declared = typed_graph_meta.get(key)
        actual = derived_edges if key == "eligible_edge_count" else derived_locs
        if declared is not None and declared != actual:
            problems.append(f"typed_graph: declared {key} {declared!r} disagrees with the supplied edges ({actual})")
    # Recompute every bundle digest: a declared repository path must exist and hash
    # to its declared digest; a synthetic bundle must match the deterministic
    # content digest of the edges actually supplied at those locs.
    edge_content = {
        loc: [edge_content_digest(edge) for edge in (typed_edges or {}).get(loc, [])]
        for loc in sorted(typed_edges or {})
    }
    supplied_content_digest = hashlib.sha256(_canonical(edge_content).encode("utf-8")).hexdigest()
    for index, bundle in enumerate(bundles):
        declared_path = str(bundle.get("path") or "")
        declared_digest = str(bundle.get("sha256") or "")
        if declared_path and "://" not in declared_path:
            candidate_path = ROOT / declared_path
            if not candidate_path.exists():
                problems.append(f"typed_graph: bundle[{index}] path does not exist: {declared_path}")
            elif hashlib.sha256(candidate_path.read_bytes()).hexdigest() != declared_digest:
                problems.append(f"typed_graph: bundle[{index}] digest does not match {declared_path}")
        elif bundle.get("present") and declared_digest != supplied_content_digest:
            problems.append(
                f"typed_graph: bundle[{index}] digest does not match the deterministic digest of the supplied edges"
            )

    authority = {
        "canonical_loc_index": index_binding,
        "carried_tables": dict(sorted((dependency_hashes or {}).items())),
        "lexeme_join_lattice": lattice_binding,
        "typed_graph": {
            "bundles": bundles,
            "edge_content_sha256": supplied_content_digest,
            "eligible_edge_count": derived_edges,
            "eligible_loc_count": derived_locs,
            "typed_graph_sha256": typed_graph_meta.get("typed_graph_sha256"),
        },
        "verified": not problems,
    }
    return authority, problems


def _edge_key_errors(typed_edges: dict[str, list[dict[str, Any]]]) -> list[str]:
    """The edge-map key must equal the loc encoded in every edge it holds."""

    problems: list[str] = []
    for loc, edges in sorted(typed_edges.items()):
        for index, edge in enumerate(edges):
            encoded = occurrence_loc_of(edge.get("from_node_id"))
            if encoded != loc:
                problems.append(
                    "typed edge %s[%d]: map key disagrees with the loc encoded in from_node_id (%r)"
                    % (loc, index, encoded)
                )
    return problems


_TARGET_SCHEMA_CONST = {
    "qword-crosswalk": "qamus/largelexicon-qword-crosswalk@2",
    "lemma-source": "fusha/largelexicon/lemma-source@2",
    "form-source": "fusha/largelexicon/form-source@2",
    "stem-source": "fusha/largelexicon/stem-source@2",
}


def _input_errors(
    crosswalk: Iterable[dict[str, Any]],
    lemmas: Iterable[dict[str, Any]],
    forms: Iterable[dict[str, Any]],
    stems: Iterable[dict[str, Any]],
    dependency_hashes: dict[str, str],
    typed_edges: dict[str, list[dict[str, Any]]],
) -> list[str]:
    """Fail closed on legacy rows, empty dependency hashes and unvalidated edges.

    Direct invocation and the registry path share this gate, so a caller cannot
    slip an @1 row or an unhashed dependency in through the projector registry.
    """

    import validate_largelexicon_rows as rows_validator

    errors: list[str] = []
    schemas = {family.name: rows_validator.read_json(ROOT / family.schema_path) for family in rows_validator.FAMILIES}
    for family_name, rows in (
        ("qword-crosswalk", crosswalk),
        ("lemma-source", lemmas),
        ("form-source", forms),
        ("stem-source", stems),
    ):
        for index, row in enumerate(rows):
            if row.get("schema") != _TARGET_SCHEMA_CONST[family_name]:
                errors.append(f"{family_name}[{index}]: row is not {_TARGET_SCHEMA_CONST[family_name]}")
                continue
            row_errors = rows_validator.schema_errors(row, schemas[family_name])
            if row_errors:
                errors.append(f"{family_name}[{index}]: row fails the target schema ({row_errors[0]['defect_family']})")
    if not dependency_hashes:
        errors.append("dependency hashes are required; an unbound consumer cannot be invalidated")
    for family_name, digest in sorted(dependency_hashes.items()):
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            errors.append(f"dependency hash for {family_name} is not a sha256 digest")
    for loc, edges in sorted(typed_edges.items()):
        for index, edge in enumerate(edges):
            problems = typed_edge_errors(edge)
            if problems:
                errors.append(f"typed edge {loc}[{index}]: {problems[0]}")
    return errors


_SEAL_TOKEN = object()

CARRIED_FAMILY_IDENTITY = {
    "qword-crosswalk": "row_id",
    "qword-denominator": "row_id",
    "form-source": "form_id",
    "lemma-source": "entry_id",
    "stem-source": "stem_id",
}


def _validate_family(family_name: str, rows: list[dict[str, Any]]) -> list[str]:
    """Schema-validate one carried family and reject ambiguous identities.

    This is the ONE production validation path. A fixture seal runs it over its
    exact bytes too, so a fixture cannot reach a candidate through a weaker gate.
    """

    import validate_largelexicon_rows as rows_validator

    problems: list[str] = []
    family = next((item for item in rows_validator.FAMILIES if item.name == family_name), None)
    if family is None:
        return ["unknown carried family: " + family_name]
    schema = rows_validator.read_json(ROOT / family.schema_path)
    expected = schema["properties"]["schema"]["const"]
    identity_field = CARRIED_FAMILY_IDENTITY[family_name]
    bodies: dict[str, str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"{family_name}[{index}]: row is not a record")
            continue
        if row.get("schema") != expected:
            problems.append(f"{family_name}[{index}]: row is not {expected}")
            continue
        row_errors = rows_validator.schema_errors(row, schema)
        if row_errors:
            problems.append(
                f"{family_name}[{index}]: row fails the target schema ({row_errors[0]['defect_family']})"
            )
            continue
        identity = str(row.get(identity_field))
        digest = row_body_digest(row)
        seen = bodies.get(identity)
        if seen is None:
            bodies[identity] = digest
        elif seen != digest:
            problems.append(
                f"{family_name}: {identity_field} {identity} carries two conflicting bodies"
            )
        else:
            problems.append(f"{family_name}: {identity_field} {identity} is duplicated")
    return problems


class SealedAuthority:
    """A self-verified, content-bound authority snapshot.

    Nothing a caller *asserts* has authority: there is no accepted ``verified``
    Boolean, digest string, row count, path label or membership set. Every digest
    in a seal is recomputed here from the exact content the seal itself holds,
    and the only two ways to obtain one are:

    * :meth:`from_release` — production. It loads the carried families, the
      canonical loc-surface index, the typed-graph bundles and the candidate
      lattice ITSELF, from the release and the repository, and hashes the exact
      bytes it read. No content or metadata crosses the boundary from a caller.
    * :meth:`seal_fixture` — tests. It takes exact in-memory content, runs the
      SAME validation path, and hashes exactly those bytes. It refuses to accept
      any repository path claim or caller digest, so a fixture can never borrow
      genuine repository metadata for unrelated content.
    """

    def __init__(self, token: Any, *, origin: str, families: dict[str, list[dict[str, Any]]],
                 loc_surface: dict[str, str], typed_edges: dict[str, list[dict[str, Any]]],
                 lexeme_join: dict[str, list[dict[str, Any]]], bundles: list[dict[str, Any]],
                 non_carried_crosswalk: list[dict[str, Any]],
                 released_carried_sha256: dict[str, str] | None = None,
                 carried_scope: dict[str, str] | None = None) -> None:
        if token is not _SEAL_TOKEN:
            raise BridgeError(
                "a SealedAuthority may only be produced by from_release() or seal_fixture()"
            )
        self.origin = origin
        self.families = families
        self.loc_surface = loc_surface
        self.typed_edges = typed_edges
        self.lexeme_join = lexeme_join
        self.non_carried_crosswalk = non_carried_crosswalk
        released_carried_sha256 = dict(released_carried_sha256 or {})
        carried_scope = dict(carried_scope or {name: "unknown" for name in families})
        edge_content = {
            loc: sorted(edge_content_digest(edge) for edge in typed_edges[loc])
            for loc in sorted(typed_edges)
        }
        self.binding = {
            "canonical_loc_index": {
                "content_sha256": _content_sha256(dict(sorted(loc_surface.items()))),
                "row_count": len(loc_surface),
            },
            # Order-independent: the authority is the SET of carried rows, so the
            # digest is taken over a canonical ordering. Iteration order (which the
            # scan window depends on) is preserved separately.
            "carried_tables": {
                name: _content_sha256(sorted(
                    families[name],
                    key=lambda row: (str(row.get(CARRIED_FAMILY_IDENTITY[name])), row_body_digest(row)),
                )) for name in sorted(families)
            },
            # Whether each sealed family is the WHOLE released family or a filtered
            # subset. A subset digest may never be published as a whole-family fact.
            "carried_scope": dict(sorted(carried_scope.items())),
            # The release's own declared per-family digest, verbatim, so a
            # TARGET-RELEASE fragment address always names a digest that exists
            # at that file address.
            "released_carried_sha256": dict(sorted(released_carried_sha256.items())),
            "carried_row_counts": {name: len(families[name]) for name in sorted(families)},
            "lexeme_join_lattice": {
                "content_sha256": _content_sha256(
                    {key: lexeme_join[key] for key in sorted(lexeme_join)}
                ),
                "row_count": sum(len(rows) for rows in lexeme_join.values()),
            },
            "origin": origin,
            "typed_graph": {
                "bundles": bundles,
                "edge_content_sha256": _content_sha256(edge_content),
                "eligible_edge_count": sum(len(edges) for edges in typed_edges.values()),
                "eligible_loc_count": len(typed_edges),
            },
        }
        # The aggregate digest is derived from the recomputed parts, never supplied.
        self.binding["typed_graph"]["typed_graph_sha256"] = _content_sha256(
            self.binding["typed_graph"]
        )
        self.binding["verified"] = True
        self.binding["authority_sha256"] = _content_sha256(self.binding)

    @staticmethod
    def _seal(origin: str, *, families: dict[str, list[dict[str, Any]]], loc_surface: dict[str, str],
              typed_edges: dict[str, list[dict[str, Any]]], lexeme_join: dict[str, list[dict[str, Any]]],
              bundles: list[dict[str, Any]], non_carried_crosswalk: list[dict[str, Any]],
              released_carried_sha256: dict[str, str] | None = None,
              carried_scope: dict[str, str] | None = None) -> "SealedAuthority":
        problems: list[str] = []
        for name in sorted(CARRIED_FAMILY_IDENTITY):
            problems.extend(_validate_family(name, families.get(name, [])))
        problems.extend(_validate_family("qword-crosswalk", non_carried_crosswalk))
        problems.extend(_edge_key_errors(typed_edges))
        for loc, edges in sorted(typed_edges.items()):
            for index, edge in enumerate(edges):
                edge_problems = typed_edge_errors(edge)
                if edge_problems:
                    problems.append(f"typed edge {loc}[{index}]: {edge_problems[0]}")
        seen_edge_ids: dict[str, str] = {}
        for loc in sorted(typed_edges):
            for edge in typed_edges[loc]:
                edge_id = str(edge.get("edge_id"))
                digest = edge_content_digest(edge)
                if edge_id in seen_edge_ids and seen_edge_ids[edge_id] != digest:
                    problems.append(f"typed edge {edge_id} is reused for two different bodies")
                elif edge_id in seen_edge_ids:
                    problems.append(f"typed edge {edge_id} is duplicated")
                seen_edge_ids[edge_id] = digest
        if not loc_surface:
            problems.append("the canonical loc-surface index is empty; admission has no loc authority")
        if problems:
            raise BridgeError("authority seal failed closed: " + "; ".join(problems[:5]))
        return SealedAuthority(
            _SEAL_TOKEN, origin=origin, families=families, loc_surface=loc_surface,
            typed_edges=typed_edges, lexeme_join=lexeme_join, bundles=bundles,
            non_carried_crosswalk=non_carried_crosswalk,
            released_carried_sha256=released_carried_sha256,
            carried_scope=carried_scope,
        )

    @classmethod
    def from_release(cls, *, locs: set[str] | None = None) -> "SealedAuthority":
        """Production seal. Everything is loaded and hashed here, by this method."""

        tables = LargelexiconTargetTables.open()
        crosswalk = tables.carried("qword-crosswalk")
        if locs is not None:
            crosswalk = [row for row in crosswalk if str(row.get("canonical_quran_loc")) in locs]
        families = {
            "qword-crosswalk": crosswalk,
            "qword-denominator": tables.carried("qword-denominator"),
            "form-source": tables.carried("form-source"),
            "lemma-source": tables.carried("lemma-source"),
            "stem-source": tables.carried("stem-source"),
        }
        typed_edges, bundles = _load_typed_graph_sealed()
        release = tables.release
        declared = {
            name: str(release["tables"][name]["carried_sha256"])
            for name in families
            if name in release.get("tables", {})
        }
        scope = {
            name: ("whole_released_family"
                   if len(families[name]) == release["tables"][name]["carried_row_count"]
                   else "filtered_subset")
            for name in families
            if name in release.get("tables", {})
        }
        return cls._seal(
            "release",
            families=families,
            loc_surface=_load_loc_surface_sealed(),
            typed_edges=typed_edges,
            lexeme_join=_load_lexeme_join_sealed(),
            bundles=bundles,
            non_carried_crosswalk=[],
            released_carried_sha256=declared,
            carried_scope=scope,
        )

    @classmethod
    def seal_fixture(cls, *, crosswalk: Iterable[dict[str, Any]], denominator: Iterable[dict[str, Any]],
                     forms: Iterable[dict[str, Any]], lemmas: Iterable[dict[str, Any]],
                     stems: Iterable[dict[str, Any]], loc_surface: dict[str, str],
                     typed_edges: dict[str, list[dict[str, Any]]] | None = None,
                     lexeme_join: dict[str, list[dict[str, Any]]] | None = None,
                     non_carried_crosswalk: Iterable[dict[str, Any]] | None = None) -> "SealedAuthority":
        """Explicit fixture seal over exact in-memory bytes. No path or digest claims."""

        edges = {loc: list(items) for loc, items in (typed_edges or {}).items() if items}
        bundles = [{
            "eligible_edge_count": sum(len(items) for items in edges.values()),
            "origin": "fixture",
            "path": None,
            "present": True,
            "schema": TYPED_GRAPH_SCHEMA,
        }]
        # A fixture seal declares NO release digest: fixture authority is
        # fixture-only and may never emit a TARGET-RELEASE fragment address.
        return cls._seal(
            "fixture",
            released_carried_sha256={},
            carried_scope={name: "fixture_only" for name in CARRIED_FAMILY_IDENTITY},
            families={
                "qword-crosswalk": list(crosswalk),
                "qword-denominator": list(denominator),
                "form-source": list(forms),
                "lemma-source": list(lemmas),
                "stem-source": list(stems),
            },
            loc_surface=dict(loc_surface),
            typed_edges=edges,
            lexeme_join={key: list(value) for key, value in (lexeme_join or {}).items()},
            bundles=bundles,
            non_carried_crosswalk=list(non_carried_crosswalk or []),
        )


def _load_loc_surface_sealed() -> dict[str, str]:
    """Parse the canonical loc-surface index from the repository, atomically."""

    index: dict[str, str] = {}
    if LOC_SURFACE_INDEX.exists():
        with LOC_SURFACE_INDEX.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    index[str(row["loc"])] = str(row["surface"])
    return index


def _load_lexeme_join_sealed() -> dict[str, list[dict[str, Any]]]:
    edges: dict[str, list[dict[str, Any]]] = {}
    if LEXEME_JOIN_EDGES.exists():
        with LEXEME_JOIN_EDGES.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    edges.setdefault(str(row.get("loc")), []).append(row)
    return edges


def _load_typed_graph_sealed() -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Parse the named bundles and return the exact eligible edge multiset + bindings."""

    index: dict[str, list[dict[str, Any]]] = {}
    bundles: list[dict[str, Any]] = []
    for relative in sorted(TYPED_GRAPH_BUNDLES):
        path = ROOT / relative
        entry = {
            "eligible_edge_count": 0,
            "origin": "repository",
            "path": relative,
            "present": path.exists(),
            "row_count": 0,
            "schema": TYPED_GRAPH_SCHEMA,
            "sha256": None,
        }
        if path.exists():
            payload = path.read_bytes()
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            for line in payload.decode("utf-8").splitlines():
                if not line.strip():
                    continue
                edge = json.loads(line)
                entry["row_count"] += 1
                if typed_edge_errors(edge):
                    continue
                loc = occurrence_loc_of(edge.get("from_node_id"))
                if loc is None:
                    continue
                index.setdefault(loc, []).append(edge)
                entry["eligible_edge_count"] += 1
        bundles.append(entry)
    return index, bundles


class BridgeInputs:
    """Carried target-schema rows plus canonical typed graph evidence, gate-checked.

    Constructing this class IS the gate: rows, edge-map keys, the carried
    dependency family and every authority are verified, and a failure raises.
    ``DiagnosticInputs`` is the only non-validating variant and it is structurally
    unable to yield a candidate.
    """

    candidate_capable = True

    def __init__(self, authority: "SealedAuthority") -> None:
        if not isinstance(authority, SealedAuthority):
            raise BridgeError(
                "candidate-capable inputs require a SealedAuthority; loose caller rows, digests, "
                "row counts, path labels and verified flags carry no authority"
            )
        self.authority_seal = authority
        self.authority = copy.deepcopy(authority.binding)
        self.input_errors: list[str] = []
        self.typed_edges = authority.typed_edges
        self.typed_graph_meta = self.authority["typed_graph"]
        self.loc_surface = authority.loc_surface
        self.loc_surface_meta = self.authority["canonical_loc_index"]
        self.lexeme_join_meta = self.authority["lexeme_join_lattice"]
        self.crosswalk = authority.families["qword-crosswalk"]
        self.forms = authority.families["form-source"]
        self.stems = authority.families["stem-source"]
        self.lemmas = {str(row["entry_id"]): row for row in authority.families["lemma-source"]}
        self.dependency_hashes = dict(self.authority["carried_tables"])
        self.graph_edges = authority.lexeme_join
        self._forms_by_surface: dict[str, list[dict[str, Any]]] = {}
        self._forms_by_norm: dict[str, list[dict[str, Any]]] = {}
        for row in self.forms:
            self._forms_by_surface.setdefault(str(row.get("surface")), []).append(row)
            self._forms_by_norm.setdefault(str(row.get("surface_norm_strict")), []).append(row)
        self._stems_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for row in self.stems:
            self._stems_by_key[(str(row.get("entry_id")), str(row.get("surface")))] = row
        # Content-addressed membership over the EXACT sealed row bodies.
        self._carried_bodies = {row_body_digest(row) for row in self.crosswalk}
        self._carried_row_ids = {str(row.get("row_id")) for row in self.crosswalk}
        self._non_carried_bodies = {row_body_digest(row) for row in authority.non_carried_crosswalk}
        self._non_carried_row_ids = {str(row.get("row_id")) for row in authority.non_carried_crosswalk}
        self.denominator = authority.families["qword-denominator"]
        self._denominator_by_id = {str(row.get("row_id")): row for row in self.denominator}

    @classmethod
    def from_release(cls, *, locs: set[str] | None = None) -> "BridgeInputs":
        """Production entry point: the seal loads and hashes everything itself."""

        return cls(SealedAuthority.from_release(locs=locs))

    def authority_binding(self) -> dict[str, Any]:
        """The VERIFIED authority object: every consumed index, lattice, bundle and table."""

        return copy.deepcopy(self.authority)

    def authority_digest(self) -> str:
        return hashlib.sha256(_canonical(self.authority_binding()).encode("utf-8")).hexdigest()

    def carried_membership(self, row: dict[str, Any]) -> str:
        """``"carried"`` only for an exact member of the validated carried authority."""

        digest = row_body_digest(row)
        if digest in self._carried_bodies:
            return "carried"
        if digest in self._non_carried_bodies or str(row.get("row_id")) in self._non_carried_row_ids:
            return "quarantined_or_flagged_source_row"
        if str(row.get("row_id")) in self._carried_row_ids:
            # Right identity, wrong body: the row drifted after validation.
            return "row_not_in_validated_carried_authority"
        return "row_not_in_validated_carried_authority"

    def dependency_authority_blockers(self, row: dict[str, Any]) -> list[str]:
        """Bind the row's declared dependency IDs to the validated denominator authority.

        A correct ``kind`` label proves nothing. The declared
        ``qword_denominator_row`` id must resolve in the carried denominator, and
        the declared ``source_card`` id must equal that denominator row's own
        ``card_id`` — which is the only source-card membership the target release
        can actually prove.
        """

        if not self.denominator:
            return ["source_card_authority_unavailable"]
        declared = {}
        for item in row.get("source_dependencies") or []:
            declared.setdefault(str(item.get("kind")), []).append(str(item.get("id")))
        denominator_ids = declared.get("qword_denominator_row") or []
        card_ids = declared.get("source_card") or []
        rows = [self._denominator_by_id.get(item) for item in denominator_ids]
        if not denominator_ids or any(item is None for item in rows):
            return ["dependency_id_not_in_authority"]
        authoritative_cards = {str(item.get("card_id")) for item in rows if item}
        if not card_ids or any(item not in authoritative_cards for item in card_ids):
            return ["dependency_id_not_in_authority"]
        if str(row.get("card_id")) not in authoritative_cards:
            return ["dependency_id_not_in_authority"]
        if str(row.get("qword_row_id")) not in set(denominator_ids):
            return ["dependency_id_not_in_authority"]
        return []

    def accepted_typed_edges(self, loc: str, surface: str) -> list[dict[str, Any]]:
        """Accepted typed edges at this loc whose written surface agrees exactly.

        The edge-map key, the occurrence loc encoded in ``from_node_id``, and the
        candidate occurrence loc must all agree: a map keyed at one location whose
        edge encodes another is a mis-binding, never support.
        """

        return [
            edge
            for edge in self.typed_edges.get(loc, [])
            if str((edge.get("details") or {}).get("surface")) == surface
            and occurrence_loc_of(edge.get("from_node_id")) == loc
        ]

    def exact_surface_forms(self, surface: str) -> list[dict[str, Any]]:
        return sorted(
            self._forms_by_surface.get(surface, []), key=lambda row: (str(row["entry_id"]), str(row["form_id"]))
        )

    def norm_only_forms(self, surface: str, norm_strict: str) -> list[dict[str, Any]]:
        return sorted(
            (row for row in self._forms_by_norm.get(norm_strict, []) if str(row.get("surface")) != surface),
            key=lambda row: (str(row["entry_id"]), str(row["form_id"])),
        )

    def stem_for(self, entry_id: str, surface: str) -> dict[str, Any] | None:
        return self._stems_by_key.get((entry_id, surface))


class DiagnosticInputs(BridgeInputs):
    """Unsealed inputs for diagnostics ONLY.

    ``candidate_capable`` is False, so :func:`bridge_row` short-circuits to an
    abstention carrying ``unverified_diagnostic_inputs``. There is no code path
    from this class to a candidate fact or a candidate projector wrapper.
    """

    candidate_capable = False

    def __init__(self, **unsealed: Any) -> None:  # noqa: D401 - deliberately permissive
        self.authority_seal = None
        self.unsealed = unsealed
        self.input_errors = ["inputs were never sealed; diagnostics only"]
        self.authority = {"origin": "unsealed", "verified": False}
        self.typed_edges = dict(unsealed.get("typed_edges") or {})
        self.typed_graph_meta = {"origin": "unsealed", "verified": False}
        self.loc_surface = dict(unsealed.get("loc_surface") or {})
        self.loc_surface_meta = {"origin": "unsealed", "verified": False}
        self.lexeme_join_meta = {"origin": "unsealed", "verified": False}
        self.crosswalk = list(unsealed.get("crosswalk") or [])
        self.forms = list(unsealed.get("forms") or [])
        self.stems = list(unsealed.get("stems") or [])
        self.lemmas = {}
        self.dependency_hashes = dict(unsealed.get("dependency_hashes") or {})
        self.graph_edges = dict(unsealed.get("graph_edges") or {})
        self._forms_by_surface = {}
        self._forms_by_norm = {}
        self._stems_by_key = {}
        self._carried_bodies = set()
        self._carried_row_ids = set()
        self._non_carried_bodies = set()
        self._non_carried_row_ids = set()
        self.denominator = []
        self._denominator_by_id = {}


def _source_evidence(structured: dict[str, Any], addresses: list[dict[str, str]]) -> dict[str, Any]:
    return {"source_addresses": addresses, "structured_source_fact": structured}


SEAL_ADDRESS_PREFIX = "sealed-authority:largelexicon-carried"


def _dependencies(authority: dict[str, Any], extra: list[dict[str, str]]) -> dict[str, Any]:
    """Bind BOTH provenance truths without letting either impersonate the other.

    A ``TARGET-RELEASE.json#{family}@sha256:{digest}`` address is a claim that the
    digest is *readable at that file address*, so it must always carry the
    release-DECLARED ``carried_sha256``. The stronger recomputed digest of the
    exact sealed row set is a different fact — and under a filtered run it is a
    SUBSET digest — so it travels under its own ``sealed-authority:`` address that
    makes no file-fragment claim, alongside the seal scope and origin.
    """

    declared = authority.get("released_carried_sha256") or {}
    sealed = authority.get("carried_tables") or {}
    scope = authority.get("carried_scope") or {}
    addresses: list[dict[str, str]] = []
    for family in sorted(set(declared) | set(sealed)):
        release_digest = declared.get(family)
        if release_digest:
            addresses.append({
                "address": (
                    "qamus/indexes/largelexicon/target-schema/TARGET-RELEASE.json"
                    f"#{family}@sha256:{release_digest}"
                ),
                "source_kind": "corpus_record",
            })
        seal_digest = sealed.get(family)
        if seal_digest:
            addresses.append({
                "address": "%s:%s:%s@sha256:%s" % (
                    SEAL_ADDRESS_PREFIX, family, scope.get(family, "unknown"), seal_digest,
                ),
                "source_kind": "corpus_record",
            })
    return {"fact_ids": [], "source_addresses": addresses + extra}


def _guards(names: Iterable[str]) -> list[dict[str, str]]:
    return [{"guard_id": name, "reason": GUARD_REASONS[name]} for name in names]


IDENTITY_CORE_FIELDS = (
    "dependencies",
    "evidence_mode",
    "fact_type",
    "fact_value",
    "producer",
    "rule_projector",
    "source_address",
    "surface_spans",
)


def identity_core(fact: dict[str, Any]) -> dict[str, Any]:
    """The exact semantic + provenance payload a bridge fact id is derived from."""

    return {"plane": "typed_claim", **{name: fact.get(name) for name in IDENTITY_CORE_FIELDS}}


def lexeme_identity_digest(fact: dict[str, Any]) -> str:
    """Digest of the LEXICAL claim alone: lexeme, form, stem and occurrence.

    Page context is deliberately excluded, so this value proves that moving the
    displaying page changes nothing about what the fact claims lexically, even
    though the whole-fact id legitimately moves with its page context and
    authority binding.
    """

    value = fact.get("fact_value") or {}
    return _content_sha256({
        "form_realization": value.get("form_realization"),
        "lexeme_candidate": value.get("lexeme_candidate"),
        "occurrence": value.get("occurrence"),
        "stem_segmentation": value.get("stem_segmentation"),
    })


def recompute_fact_id(fact: dict[str, Any]) -> str:
    """Recompute a bridge fact's content-addressed id from the fact itself.

    Changing the projector, the fact type or any semantic claim moves this value,
    so a relabelled fact that kept its original ``fact_id`` is detectable by any
    consumer, including the certifier.
    """

    return _fact_id(identity_core(fact))


def _stamp_identity(fact: dict[str, Any]) -> dict[str, Any]:
    fact["fact_id"] = recompute_fact_id(fact)
    return fact


def _candidate_fact(
    *,
    row: dict[str, Any],
    form: dict[str, Any],
    lemma: dict[str, Any] | None,
    stem: dict[str, Any] | None,
    graph_edges: list[dict[str, Any]],
    typed_edges: list[dict[str, Any]],
    typed_graph_meta: dict[str, Any],
    authority_binding: dict[str, Any],
    hashes: dict[str, str],
    candidate_count: int,
    loc: str,
) -> dict[str, Any]:
    surface = str(row["visible_surface"])
    entry_id = str(form["entry_id"])
    root_family = [
        {
            "edge_relation": str(edge.get("relation")),
            "edge_type": str(edge.get("edge_type")),
            "entry_id": str(edge.get("entry_id")),
            "row_root": edge.get("row_root"),
            "status": "candidate_edge_never_certified",
        }
        for edge in graph_edges
        if str(edge.get("entry_id")) == entry_id
    ]
    fact_value = {
        "candidate_rank_is_not_preference": True,
        "candidates_preserved": candidate_count,
        "form_realization": {
            "documented_surface": str(form["surface"]),
            "entry_id": entry_id,
            "form_id": str(form["form_id"]),
            "match_basis": "byte_exact_written_surface",
        },
        "lexeme_candidate": {
            "entry_id": entry_id,
            "lemma": (lemma or {}).get("lemma"),
            "pos": form.get("pos"),
            "root": form.get("root"),
            "root_is_relation_not_identity": True,
        },
        "occurrence": {"canonical_quran_loc": loc, "surface": surface},
        "page_context": {
            "card_id": str(row["card_id"]),
            "crosswalk_entry_id": str(row["entry_id"]),
            "never_lexeme_edge": True,
        },
        "root_family_relations": root_family,
        "stem_segmentation": None
        if stem is None
        else {
            "stem_id": str(stem["stem_id"]),
            "visible_segment_count": len(stem.get("visible_segments") or []),
        },
    }
    fact_value["authority_binding"] = authority_binding
    fact_value["typed_graph_evidence"] = [
        {
            "edge_id": edge.get("edge_id"),
            "edge_type": edge["edge_type"],
            "from_node_id": edge["from_node_id"],
            "status": edge["status"],
            "surface": (edge.get("details") or {}).get("surface"),
            "to_node_id": edge["to_node_id"],
        }
        for edge in typed_edges
    ]
    # Content-addressed over the whole semantic claim: mutating POS, root, lemma,
    # form, stem, a typed edge, a dependency digest, or the projector identity all
    # change the fact id.
    return _stamp_identity({
        "certification": {
            "reason": "carried-table lookup is candidate evidence; only the certifier may certify",
            "status": "candidate",
        },
        "contradiction_records": [],
        "defeaters": [],
        "dependencies": _dependencies(
            authority_binding,
            [
                {"address": f"largelexicon:qword-crosswalk@2:{row['row_id']}", "source_kind": "corpus_record"},
                {"address": f"largelexicon:form-source@2:{form['form_id']}", "source_kind": "corpus_record"},
                *[
                    {
                        "address": "%s#%s@sha256:%s" % (item["path"], TYPED_GRAPH_SCHEMA, item["sha256"]),
                        "source_kind": "corpus_record",
                    }
                    for item in typed_graph_meta.get("bundles", [])
                    if item.get("sha256")
                ],
            ],
        ),
        "dependent_fact_ids": [],
        "dependent_projection_ids": [],
        "derivation_chain": [],
        "evidence": {
            "confidence": "unknown",
            "evidence_ids": [f"llx-form-{form['form_id']}", f"llx-crosswalk-{row['row_id']}"],
            "status": "source_addressed_candidate",
            "summary": (
                "a carried target-schema form row documents this exact written surface and an accepted "
                "canonical typed lexeme/form edge agrees at this occurrence loc"
            ),
        },
        # Honest mode: there is no certified lexical input and no derivation chain
        # here, so this is a source-addressed candidate, not a normalized lexical body.
        "evidence_mode": "direct_source_attestation",
        "fact_id": "",
        "fact_type": "largelexicon_lexeme_candidate",
        "fact_value": fact_value,
        "guards": _guards(
            [
                "loc_first_canonical_address",
                "carried_target_schema_rows_only",
                "byte_exact_written_surface",
                "crosswalk_entry_id_is_page_context",
                "root_family_never_lexeme_edge",
                "candidate_edge_never_certified",
                "release_dependency_bound",
                "canonical_typed_edge_required",
                "canonical_loc_surface_verified",
                "typed_graph_digest_bound",
            ]
        ),
        "ownership": {
            "primary": {"owner_id": "sarf", "owner_type": "skill"},
            "secondary": [{"owner_id": "largelexicon", "owner_type": "lookup_substrate"}],
        },
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "rule_projector": {"projector_id": PROJECTOR_ID, "rule_id": RULE_ID, "version": PRODUCER_VERSION},
        "source": {"source_id": f"largelexicon:form-source@2:{form['form_id']}", "source_kind": "corpus_record"},
        "source_address": {
            "address": f"largelexicon:form-source@2:{form['form_id']}",
            "source_kind": "corpus_record",
        },
        "source_evidence": _source_evidence(
            {
                "carried_form_row": {
                    "entry_id": entry_id,
                    "form_id": str(form["form_id"]),
                    "surface": str(form["surface"]),
                },
                "carried_crosswalk_row": {
                    "canonical_quran_loc": loc,
                    "row_id": str(row["row_id"]),
                    "status": str(row["status"]),
                },
            },
            [
                {"address": f"quran:{loc}", "source_kind": "quran_token"},
                {"address": f"largelexicon:form-source@2:{form['form_id']}", "source_kind": "corpus_record"},
            ],
        ),
        "surface_spans": [
            {"end": len(surface), "role": "written_token", "span_id": f"{loc}:token", "start": 0, "surface": surface}
        ],
        "unresolved_blockers": [],
    })


def _abstention_fact(
    *,
    row: dict[str, Any],
    blockers: list[str],
    hashes: dict[str, str],
    loc: str | None,
    graph_edges: list[dict[str, Any]],
    observed: dict[str, Any],
    authority_binding: dict[str, Any],
) -> dict[str, Any]:
    surface = str(row.get("visible_surface") or "")
    address = f"largelexicon:qword-crosswalk@2:{row.get('row_id')}"
    fact_value = {
        "abstained": True,
        "authority_binding": authority_binding,
        "blockers": sorted(blockers),
        "candidate_graph_edges": [
            {
                "edge_relation": str(edge.get("relation")),
                "entry_id": str(edge.get("entry_id")),
                "status": "candidate_edge_never_certified",
            }
            for edge in graph_edges
        ],
        "canonical_quran_loc": loc,
        "observed": observed,
        "page_context": {
            "card_id": row.get("card_id"),
            "crosswalk_entry_id": row.get("entry_id"),
            "never_lexeme_edge": True,
        },
    }
    span_surface = surface if surface and not surface.isspace() else "؟"
    return _stamp_identity({
        "certification": {"reason": "; ".join(BLOCKER_REASONS[name] for name in blockers), "status": "blocked"},
        "contradiction_records": [],
        "defeaters": [
            {"defeater_id": name, "fact_ids": [], "reason": BLOCKER_REASONS[name]} for name in blockers
        ],
        "dependencies": _dependencies(authority_binding, [{"address": address, "source_kind": "corpus_record"}]),
        "dependent_fact_ids": [],
        "dependent_projection_ids": [],
        "derivation_chain": [],
        "evidence": {
            "confidence": "unknown",
            "evidence_ids": [f"llx-crosswalk-{row.get('row_id')}"],
            "status": "blocked",
            "summary": "the bridge abstained; the precise blockers are recorded rather than guessed away",
        },
        "evidence_mode": "unresolved",
        "fact_id": "",
        "fact_type": "largelexicon_bridge_abstention",
        "fact_value": fact_value,
        "guards": _guards(["loc_first_canonical_address", "carried_target_schema_rows_only", "release_dependency_bound"]),
        "ownership": {
            "primary": {"owner_id": "sarf", "owner_type": "skill"},
            "secondary": [{"owner_id": "largelexicon", "owner_type": "lookup_substrate"}],
        },
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "rule_projector": {"projector_id": ABSTENTION_PROJECTOR_ID, "rule_id": ABSTENTION_RULE_ID, "version": PRODUCER_VERSION},
        "source": {"source_id": address, "source_kind": "corpus_record"},
        "source_address": {"address": address, "source_kind": "corpus_record"},
        "source_evidence": _source_evidence(
            {"carried_crosswalk_row": {"row_id": str(row.get("row_id")), "status": row.get("status")}},
            [{"address": address, "source_kind": "corpus_record"}],
        ),
        "surface_spans": [
            {
                "end": len(span_surface),
                "role": "written_token",
                "span_id": f"{row.get('row_id')}:token",
                "start": 0,
                "surface": span_surface,
            }
        ],
        "unresolved_blockers": [{"blocker_id": name, "reason": BLOCKER_REASONS[name]} for name in blockers],
    })


def _worst_status(blockers: list[str]) -> str:
    order = ["blocked", "source_gap", "producer_pending", "unresolved"]
    statuses = {BLOCKER_STATUS[name] for name in blockers}
    for candidate in order:
        if candidate in statuses:
            return candidate
    return "unresolved"


def bridge_row(row: dict[str, Any], inputs: BridgeInputs) -> dict[str, Any]:
    """Bridge one crosswalk row into exactly one typed-claim contract record.

    Carried-ness is NOT a caller assertion. The row's canonical body digest must
    be an exact member of the validated carried crosswalk authority held by
    ``inputs``; a row that is detached, altered, schema-downgraded, invented or
    dispositioned elsewhere abstains and can never emit a candidate.
    """

    hashes = inputs.dependency_hashes
    if not getattr(inputs, "candidate_capable", False):
        # Diagnostic inputs are never verified, so they can only ever abstain.
        return _record(
            row=row,
            loc=None,
            surface=str(row.get("visible_surface") or ""),
            facts=[
                _abstention_fact(
                    row=row,
                    blockers=["unverified_diagnostic_inputs"],
                    hashes=hashes,
                    loc=None,
                    graph_edges=[],
                    observed={"input_errors": list(getattr(inputs, "input_errors", []))[:5]},
                    authority_binding=inputs.authority_binding(),
                )
            ],
            status="blocked",
            unresolved="blocked",
        )
    loc_value = row.get("canonical_quran_loc")
    loc = str(loc_value) if is_canonical_loc(loc_value) else None
    graph_edges = inputs.graph_edges.get(loc or "", [])
    blockers: list[str] = []

    membership = inputs.carried_membership(row)
    if membership != "carried":
        blockers.append(membership)
    dependency_kinds = {str(item.get("kind")) for item in row.get("source_dependencies") or []}
    if not REQUIRED_DEPENDENCY_KINDS.issubset(dependency_kinds):
        blockers.append("missing_dependency_release")
    else:
        blockers.extend(inputs.dependency_authority_blockers(row))
    if loc is None:
        blockers.append("unresolved_canonical_loc")
    if row.get("status") != ACCEPTED_CROSSWALK_STATUS or row.get("transclusion_route") != ACCEPTED_TRANSCLUSION_ROUTE:
        blockers.append("crosswalk_packet_not_accepted")

    surface = str(row.get("visible_surface") or "")
    norm_strict = str(row.get("visible_surface_norm_strict") or "")
    exact = [] if blockers else inputs.exact_surface_forms(surface)
    entry_ids = sorted({str(form["entry_id"]) for form in exact})

    # The canonical loc must exist and agree with the committed index on the exact
    # written surface, and the wbw loc must agree with the quran loc.
    if loc is not None and inputs.loc_surface:
        canonical_surface = inputs.loc_surface.get(loc)
        if canonical_surface is None:
            blockers.append("loc_not_in_canonical_index")
        elif canonical_surface != surface:
            blockers.append("loc_surface_disagreement")
    if loc is not None and str(row.get("canonical_wbw_loc") or "") != loc:
        blockers.append("wbw_loc_disagreement")

    if not blockers and not exact:
        norm_only = inputs.norm_only_forms(surface, norm_strict) if norm_strict else []
        if norm_only:
            blockers.append("norm_only_surface_match")
        elif str(row.get("entry_id")) in inputs.lemmas:
            blockers.append("page_context_only_no_lexical_edge")
        elif graph_edges and all(str(edge.get("relation")) != "exact_form" for edge in graph_edges):
            blockers.append(
                "root_family_relation_not_lexeme_identity"
                if any(str(edge.get("relation")) == "root_confirms" for edge in graph_edges)
                else "non_certified_graph_edge_only"
            )
        else:
            blockers.append("no_carried_lexical_support")

    # Exact surface is DISCOVERY ONLY. Identity additionally requires an accepted
    # canonical typed lexeme/form edge agreeing on loc, written surface and entry.
    typed_edges: list[dict[str, Any]] = []
    supported: dict[str, list[dict[str, Any]]] = {}
    if not blockers and exact:
        typed_edges = inputs.accepted_typed_edges(str(loc), surface)
        for edge in typed_edges:
            entry = str(edge["to_node_id"]).split(":", 1)[1]
            if entry in entry_ids:
                supported.setdefault(entry, []).append(edge)
        if not typed_edges:
            blockers.append("missing_typed_graph_evidence")
        elif not supported:
            blockers.append("typed_edge_identity_disagreement")
        else:
            exact = [form for form in exact if str(form["entry_id"]) in supported]
            entry_ids = sorted(supported)

    observed = {
        "accepted_typed_edge_count": len(typed_edges),
        "exact_surface_entry_ids": entry_ids,
        "graph_edge_count": len(graph_edges),
        "typed_graph_sha256": inputs.typed_graph_meta.get("typed_graph_sha256"),
        "visible_surface": surface,
    }

    if blockers:
        fact = _abstention_fact(
            row=row,
            blockers=blockers,
            hashes=hashes,
            loc=loc,
            graph_edges=graph_edges,
            observed=observed,
            authority_binding=inputs.authority_binding(),
        )
        status = _worst_status(blockers)
        return _record(row=row, loc=loc, surface=surface, facts=[fact], status=status, unresolved=status)

    facts = [
        _candidate_fact(
            row=row,
            form=form,
            lemma=inputs.lemmas.get(str(form["entry_id"])),
            stem=inputs.stem_for(str(form["entry_id"]), str(form["surface"])),
            graph_edges=graph_edges,
            typed_edges=supported[str(form["entry_id"])],
            typed_graph_meta=inputs.typed_graph_meta,
            authority_binding=inputs.authority_binding(),
            hashes=hashes,
            candidate_count=len(exact),
            loc=str(loc),
        )
        for form in exact
    ]
    # More than one surviving ANALYSIS is unresolved, even when the rivals share an
    # entry id: two documented forms of one entry are still two distinct claims and
    # neither may be selected.
    if len(facts) > 1:
        collision = ["lexical_collision_requires_context"]
        for fact in facts:
            fact["unresolved_blockers"] = [
                {"blocker_id": name, "reason": BLOCKER_REASONS[name]} for name in collision
            ]
            fact["defeaters"] = [
                {"defeater_id": name, "fact_ids": sorted(item["fact_id"] for item in facts), "reason": BLOCKER_REASONS[name]}
                for name in collision
            ]
        return _record(
            row=row,
            loc=loc,
            surface=surface,
            facts=facts,
            status="unresolved",
            unresolved="unresolved",
            tension={
                "fact_ids": sorted(fact["fact_id"] for fact in facts),
                "resolution_requirement": "context evidence or two-vote adjudication must decide between the preserved candidates",
                "statement": "more than one entry documents this exact written surface at this occurrence",
                "status": "unresolved",
                "tension_id": f"{CONTRACT_PREFIX}-collision-{loc}",
            },
        )
    return _record(row=row, loc=loc, surface=surface, facts=facts, status="candidate", unresolved=None)


def _record(
    *,
    row: dict[str, Any],
    loc: str | None,
    surface: str,
    facts: list[dict[str, Any]],
    status: str,
    unresolved: str | None,
    tension: dict[str, Any] | None = None,
) -> dict[str, Any]:
    occurrence_loc = loc or "0:0:0"
    record: dict[str, Any] = {
        "canonical_occurrence": {
            "card_id": str(row.get("card_id")),
            "occurrence_id": f"quran:{occurrence_loc}",
            "quran_loc": occurrence_loc,
            "surface": surface or "؟",
            "surface_length": len(surface or "؟"),
            "wbw_loc": f"wbw:{occurrence_loc}",
        },
        "contract_id": f"{CONTRACT_PREFIX}:{row.get('row_id')}",
        "contract_version": "1.0.0",
        "facts": facts,
        "projection": {
            "claim": None,
            "learner_visible": False,
            "materialization_target": dict(MATERIALIZATION_TARGET),
            "projection_id": f"{CONTRACT_PREFIX}:{row.get('row_id')}:projection",
            "status": status,
            "unresolved_status": unresolved,
        },
        "record_type": "projection_input" if status == "candidate" else "unresolved_projection",
        "schema": "qamus.typed_claim_contract.v1",
    }
    if tension is not None:
        record["tension_records"] = [tension]
    return record


def _public_string_errors(text: str, path: str) -> list[str]:
    """Forbidden-label, URL and absolute/private-path checks for one public string."""

    from largelexicon_common import FORBIDDEN_PUBLIC_SUBSTRINGS, match_forbidden_labels

    problems: list[str] = []
    for pattern in PROHIBITED_VALUE_PATTERNS:
        if pattern.search(text):
            problems.append(f"{path}: prohibited URL or absolute/private path in a public fixture")
            break
    labels = match_forbidden_labels(text.lower(), FORBIDDEN_PUBLIC_SUBSTRINGS)
    if labels:
        problems.append(f"{path}: external source label(s) {sorted(labels)} in a public fixture")
    if text.lower() in PROHIBITED_FIXTURE_KEYS:
        problems.append(f"{path}: prohibited field class name in a committed public fixture")
    return problems


def public_fixture_errors(node: Any, path: str = "$") -> list[str]:
    """Recursively reject prohibited public classes in a committed fixture."""

    problems: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).lower() in PROHIBITED_FIXTURE_KEYS:
                problems.append(f"{path}.{key}: prohibited field class in a committed public fixture")
            # Keys are public payload too: run the SAME forbidden-label, URL and
            # path logic over every key at every depth, not just over values.
            problems.extend(_public_string_errors(str(key), f"{path}.{key}<key>"))
            problems.extend(public_fixture_errors(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            problems.extend(public_fixture_errors(value, f"{path}[{index}]"))
    elif isinstance(node, str):
        problems.extend(_public_string_errors(node, path))
    return problems


def validate_records(records: Iterable[dict[str, Any]]) -> list[str]:
    """Contract validation plus the bridge's own never-certify invariants."""

    errors: list[str] = []
    for index, record in enumerate(records):
        label = f"record[{index}]"
        errors.extend(f"{label}: {item}" for item in typed_claim_contract.validate_contract_record(record))
        projection = record.get("projection") or {}
        if projection.get("learner_visible") is not False:
            errors.append(f"{label}: bridge output must never be learner-visible")
        target = projection.get("materialization_target") or {}
        if target.get("public_materialization_allowed") is not False or target.get("live_mutation_allowed") is not False:
            errors.append(f"{label}: bridge output must never allow public materialization or live mutation")
        for fact_index, fact in enumerate(record.get("facts") or []):
            certification = (fact.get("certification") or {}).get("status")
            if certification not in {"candidate", "blocked"}:
                errors.append(f"{label}.facts[{fact_index}]: certification status {certification!r} is not candidate-or-blocked")
            if (fact.get("evidence") or {}).get("status") == "certified":
                errors.append(f"{label}.facts[{fact_index}]: bridge evidence may never be certified")
            projector_id = fact.get("rule_projector", {}).get("projector_id")
            if projector_id not in {PROJECTOR_ID, ABSTENTION_PROJECTOR_ID}:
                errors.append(f"{label}.facts[{fact_index}]: fact is not attributed to a registered bridge projector")
            expected_projector = (PROJECTOR_ID if fact.get("fact_type") == "largelexicon_lexeme_candidate"
                                  else ABSTENTION_PROJECTOR_ID)
            if projector_id != expected_projector:
                errors.append(f"{label}.facts[{fact_index}]: {fact.get('fact_type')} must be attributed to {expected_projector}")
    return errors


def run(*, locs: set[str] | None = None, limit: int | None = None) -> dict[str, Any]:
    inputs = BridgeInputs.from_release(locs=locs)
    rows = inputs.crosswalk if limit is None else inputs.crosswalk[:limit]
    records = [bridge_row(row, inputs) for row in rows]
    errors = validate_records(records)
    if errors:
        raise BridgeError("bridge emitted invalid typed-claim records: " + "; ".join(errors[:5]))
    return {"records": records, "summary": summarize(records)}


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    blockers: dict[str, int] = {}
    candidate_counts: dict[str, int] = {}
    for record in records:
        status = record["projection"]["status"]
        statuses[status] = statuses.get(status, 0) + 1
        preserved = sum(1 for fact in record["facts"] if fact["fact_type"] == "largelexicon_lexeme_candidate")
        key = str(preserved)
        candidate_counts[key] = candidate_counts.get(key, 0) + 1
        for fact in record["facts"]:
            for blocker in fact.get("unresolved_blockers") or []:
                blockers[blocker["blocker_id"]] = blockers.get(blocker["blocker_id"], 0) + 1
    return {
        "blocker_counts": dict(sorted(blockers.items())),
        "certified_records": 0,
        "learner_visible_records": 0,
        "preserved_candidate_histogram": dict(sorted(candidate_counts.items())),
        "projection_status_counts": dict(sorted(statuses.items())),
        "record_count": len(records),
    }


# --------------------------------------------------------------------------- #
# behavioural fixtures — one scenario per accepted case and per closed blocker
# --------------------------------------------------------------------------- #
FIXTURE_DIR = ROOT / "qamus" / "examples" / "largelexicon-fact-bridge"
FIXTURE_LOC = "2:255:1"
FIXTURE_SURFACE = "ٱللَّهُ"
FIXTURE_NORM = "الله"
FIXTURE_NORM_TWIN = "اللَّهُ"
FIXTURE_DEPENDENCY_HASHES = {
    "form-source": "a" * 64,
    "lemma-source": "b" * 64,
    "qword-crosswalk": "c" * 64,
    "qword-denominator": "d" * 64,
    "stem-source": "e" * 64,
}
assert set(FIXTURE_DEPENDENCY_HASHES) == set(REQUIRED_DEPENDENCY_FAMILIES)


def fixture_crosswalk_row(**overrides: Any) -> dict[str, Any]:
    """A carried, accepted crosswalk row. ``entry_id`` is the DISPLAYING page."""

    row = {
        "schema": "qamus/largelexicon-qword-crosswalk@2",
        "row_id": "llx-crosswalk-llx-qword-0aae00000000-01-01-001",
        "qword_row_id": "llx-qword-0aae00000000-01-01-001",
        "entry_id": "0aae00000000",
        "source_keys": ["n001"],
        "card_id": "0aae00000000:u1:e1",
        "usage_index": 1,
        "example_index": 1,
        "qword_index": 1,
        "visible_surface": FIXTURE_SURFACE,
        "visible_surface_norm_strict": FIXTURE_NORM,
        "quran_ref": "2:255",
        "canonical_quran_loc": FIXTURE_LOC,
        "canonical_wbw_loc": FIXTURE_LOC,
        "match_status": "resolved_arabic_surface_match",
        "status": ACCEPTED_CROSSWALK_STATUS,
        "next_action": None,
        "packet_class": None,
        "terminal_gate_code": None,
        "transclusion_route": ACCEPTED_TRANSCLUSION_ROUTE,
        "source_dependencies": [
            {"id": "llx-qword-0aae00000000-01-01-001", "kind": "qword_denominator_row"},
            {"id": "0aae00000000", "kind": "entry"},
            {"id": "0aae00000000:u1:e1", "kind": "source_card"},
        ],
    }
    row.update(overrides)
    return row


def fixture_denominator_row(**overrides: Any) -> dict[str, Any]:
    """The carried denominator row the fixture crosswalk row declares as its dependency."""

    row = {
        "schema": "qamus/largelexicon-qword-denominator@2",
        "row_id": "llx-qword-0aae00000000-01-01-001",
        "entry_id": "0aae00000000",
        "source_keys": ["n001"],
        "card_id": "0aae00000000:u1:e1",
        "usage_index": 1,
        "example_index": 1,
        "qword_index": 1,
        "visible_surface": FIXTURE_SURFACE,
        "visible_surface_norm_strict": FIXTURE_NORM,
        "card_text_sha256": "0" * 64,
        "quran_ref": "2:255",
        "canonical_quran_loc": FIXTURE_LOC,
        "canonical_wbw_loc": FIXTURE_LOC,
        "route": "accepted",
        "status": "accepted",
    }
    row.update(overrides)
    return row


def fixture_form_row(entry_id: str, surface: str, form_index: str = "000") -> dict[str, Any]:
    return {
        "schema": "fusha/largelexicon/form-source@2",
        "form_id": f"llx_form_{entry_id}_{form_index}",
        "entry_id": entry_id,
        "source_keys": ["n002"],
        "surface": surface,
        "surface_norm_strict": FIXTURE_NORM,
        "surface_bare": FIXTURE_NORM,
        "lemma": surface,
        "root": None,
        "no_root_reason": "proper_name_no_root",
        "pos": "proper_noun",
        "risk_flags": [],
    }


def fixture_lemma_row(entry_id: str, surface: str) -> dict[str, Any]:
    return {
        "schema": "fusha/largelexicon/lemma-source@2",
        "entry_id": entry_id,
        "source_keys": ["n002"],
        "lemma": surface,
        "root": None,
        "no_root_reason": "proper_name_no_root",
        "pos": "proper_noun",
        "forms": [surface],
        "gloss_hint": "the divine name",
        "risk_flags": [],
    }


def fixture_stem_row(entry_id: str, surface: str) -> dict[str, Any]:
    return {
        "schema": "fusha/largelexicon/stem-source@2",
        "stem_id": f"llx_{entry_id}_000",
        "generation_key": f"qamus:{entry_id}:000",
        "entry_id": entry_id,
        "source_keys": ["n002"],
        "surface": surface,
        "surface_norm_strict": FIXTURE_NORM,
        "surface_bare": FIXTURE_NORM,
        "lemma": surface,
        "root": None,
        "no_root_reason": "proper_name_no_root",
        "pos": "proper_noun",
        "gloss_shape": "proper_noun",
        "gloss_hint": "the divine name",
        "visible_segments": [
            {"surface": surface, "role": "proper_noun", "qg_class": "qg-noun", "gloss": "the divine name"}
        ],
        "qamus_entry_refs": ["n002"],
        "risk_flags": [],
    }


def fixture_typed_edge(
    entry_id: str,
    *,
    surface: str = FIXTURE_SURFACE,
    loc: str = FIXTURE_LOC,
    status: str = "deterministic_exact",
    edge_type: str = "lexeme_entry_edge",
) -> dict[str, Any]:
    """A schema-shaped canonical typed lexeme/form edge carrying an occurrence loc."""

    body = {
        "schema": TYPED_GRAPH_SCHEMA,
        "edge_type": edge_type,
        "from_node_id": f"selected-word:{entry_id}:s1:u1:f1:o{loc}",
        "from_node_type": "selected-word",
        "to_node_id": f"entry:{entry_id}",
        "to_node_type": "entry",
        "status": status,
        "details": {"surface": surface},
        "producer": {"id": "tools.fixture_typed_edge", "version": "1.0.0"},
        "evidence": [{"address": f"entry:{entry_id}:headword", "method": "entry_headword"}],
        "guards": ["orthography_guard_v1", "page_context_origin_false"],
    }
    # The identifier is derived from the content, so any content mutation either
    # breaks the id binding or changes the recomputed authority digest.
    return dict(body, edge_id=canonical_edge_id(body))


def _content_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def fixture_loc_index_meta(loc_surface: dict[str, str]) -> dict[str, Any]:
    """Synthetic canonical-index binding, digest-bound to the supplied index."""

    return {
        "path": "fixture://quran-loc-surface",
        "present": True,
        "sha256": _content_sha256(dict(sorted(loc_surface.items()))),
    }


def fixture_lexeme_join_meta(lexeme_join: dict[str, list[dict[str, Any]]] | None) -> dict[str, Any]:
    """Synthetic lattice binding, digest-bound to the supplied lattice."""

    lattice = lexeme_join or {}
    return {
        "path": "fixture://lexeme-join-edges",
        "present": True,
        "sha256": _content_sha256({key: lattice[key] for key in sorted(lattice)}),
    }


def fixture_graph_meta(
    typed_edges: dict[str, list[dict[str, Any]]] | None, *, sha256: str | None = None
) -> dict[str, Any]:
    """Bundle metadata that honestly accounts for the edges actually supplied.

    The bundle digest is the deterministic content digest of those edges, so
    same-count content drift under unchanged metadata is refused.
    """

    edges = typed_edges or {}
    supplied = sum(len(items) for items in edges.values())
    content = {
        loc: [edge_content_digest(edge) for edge in edges[loc]] for loc in sorted(edges)
    }
    digest = sha256 or _content_sha256(content)
    return {
        "bundles": [
            {
                "eligible_edge_count": supplied,
                "path": "fixture://typed-edges",
                "present": True,
                "row_count": supplied,
                "schema": TYPED_GRAPH_SCHEMA,
                "sha256": digest,
            }
        ],
        "eligible_edge_count": supplied,
        "eligible_loc_count": len(edges),
        "typed_graph_sha256": digest,
    }


FIXTURE_LOC_INDEX_META = fixture_loc_index_meta({FIXTURE_LOC: FIXTURE_SURFACE})
FIXTURE_LEXEME_JOIN_META = fixture_lexeme_join_meta({})


def fixture_inputs(
    *,
    forms=None,
    lemmas=None,
    stems=None,
    graph_edges=None,
    typed_edges=None,
    loc_surface=None,
    crosswalk=None,
    denominator=None,
    non_carried_crosswalk=None,
) -> BridgeInputs:
    """Inputs over an EXPLICITLY sealed fixture authority built from exact bytes.

    There is deliberately no digest, path-label, row-count or verified-flag
    parameter: a fixture supplies content only, and the seal recomputes every
    binding through the same validation path production uses.
    """

    entry = "1ec0de000001"
    form_rows = [fixture_form_row(entry, FIXTURE_SURFACE)] if forms is None else list(forms)
    if typed_edges is None:
        typed_edges = {
            FIXTURE_LOC: [
                fixture_typed_edge(entry_id)
                for entry_id in sorted({str(row["entry_id"]) for row in form_rows})
            ]
        }
        if not typed_edges[FIXTURE_LOC]:
            typed_edges = {}
    return BridgeInputs(SealedAuthority.seal_fixture(
        crosswalk=[fixture_crosswalk_row()] if crosswalk is None else list(crosswalk),
        denominator=[fixture_denominator_row()] if denominator is None else list(denominator),
        forms=form_rows,
        lemmas=[fixture_lemma_row(entry, FIXTURE_SURFACE)] if lemmas is None else list(lemmas),
        stems=[fixture_stem_row(entry, FIXTURE_SURFACE)] if stems is None else list(stems),
        loc_surface={FIXTURE_LOC: FIXTURE_SURFACE} if loc_surface is None else dict(loc_surface),
        typed_edges=typed_edges,
        lexeme_join=graph_edges or {},
        non_carried_crosswalk=non_carried_crosswalk or [],
    ))


def fixture_scenarios() -> list[tuple[str, dict[str, Any], BridgeInputs, bool]]:
    """``(scenario, crosswalk_row, inputs)`` covering every closed blocker.

    Carried-ness is expressed by AUTHORITY, not by a flag: a dispositioned row is
    supplied through ``non_carried_crosswalk`` and is simply absent from the
    validated carried set.
    """

    twin = [fixture_form_row("1ec0de000001", FIXTURE_SURFACE), fixture_form_row("1ec0de000002", FIXTURE_SURFACE, "001")]
    return [
        ("accepted_single_candidate", fixture_crosswalk_row(), fixture_inputs()),
        (
            "lexical_collision_requires_context",
            fixture_crosswalk_row(),
            fixture_inputs(
                forms=twin,
                lemmas=[fixture_lemma_row("1ec0de000001", FIXTURE_SURFACE), fixture_lemma_row("1ec0de000002", FIXTURE_SURFACE)],
                stems=[fixture_stem_row("1ec0de000001", FIXTURE_SURFACE)],
            ),
        ),
        (
            "page_context_only_no_lexical_edge",
            fixture_crosswalk_row(),
            fixture_inputs(forms=[], lemmas=[fixture_lemma_row("0aae00000000", "شَيْء")], stems=[]),
        ),
        (
            "root_family_relation_not_lexeme_identity",
            fixture_crosswalk_row(),
            fixture_inputs(
                forms=[],
                lemmas=[],
                stems=[],
                graph_edges={
                    FIXTURE_LOC: [
                        {"loc": FIXTURE_LOC, "entry_id": "1ec0de000009", "edge_type": "headword", "relation": "root_confirms", "row_root": "ا ل ه"}
                    ]
                },
            ),
        ),
        (
            "non_certified_graph_edge_only",
            fixture_crosswalk_row(),
            fixture_inputs(
                forms=[],
                lemmas=[],
                stems=[],
                graph_edges={
                    FIXTURE_LOC: [{"loc": FIXTURE_LOC, "entry_id": "1ec0de000009", "edge_type": "form", "relation": "linkage_only"}]
                },
            ),
        ),
        (
            "unresolved_canonical_loc",
            fixture_crosswalk_row(canonical_quran_loc="missing-loc|2:255"),
            fixture_inputs(crosswalk=[fixture_crosswalk_row(canonical_quran_loc="missing-loc|2:255")]),
        ),
        (
            "crosswalk_packet_not_accepted",
            fixture_crosswalk_row(
                status="source_crosswalk_packet_ready",
                transclusion_route="entry_card_qword_to_canonical_crosswalk_packet",
            ),
            fixture_inputs(crosswalk=[fixture_crosswalk_row(
                status="source_crosswalk_packet_ready",
                transclusion_route="entry_card_qword_to_canonical_crosswalk_packet",
            )]),
        ),
        (
            "quarantined_or_flagged_source_row",
            fixture_crosswalk_row(),
            fixture_inputs(crosswalk=[], non_carried_crosswalk=[fixture_crosswalk_row()]),
        ),
        (
            "missing_dependency_release",
            fixture_crosswalk_row(source_dependencies=[{"id": "0aae00000000", "kind": "entry"}]),
            fixture_inputs(crosswalk=[
                fixture_crosswalk_row(source_dependencies=[{"id": "0aae00000000", "kind": "entry"}])
            ]),
        ),
        (
            "norm_only_surface_match",
            fixture_crosswalk_row(),
            fixture_inputs(forms=[fixture_form_row("1ec0de000001", FIXTURE_NORM_TWIN)], lemmas=[], stems=[]),
        ),
        ("no_carried_lexical_support", fixture_crosswalk_row(), fixture_inputs(forms=[], lemmas=[], stems=[])),
        ("missing_typed_graph_evidence", fixture_crosswalk_row(), fixture_inputs(typed_edges={})),
        (
            "typed_edge_identity_disagreement",
            fixture_crosswalk_row(),
            fixture_inputs(typed_edges={FIXTURE_LOC: [fixture_typed_edge("1ec0de000009")]}),
        ),
        (
            "loc_not_in_canonical_index",
            fixture_crosswalk_row(),
            fixture_inputs(loc_surface={"1:1:1": "بِسْمِ"}),
        ),
        (
            "loc_surface_disagreement",
            fixture_crosswalk_row(),
            fixture_inputs(loc_surface={FIXTURE_LOC: FIXTURE_NORM_TWIN}),
        ),
        (
            "wbw_loc_disagreement",
            fixture_crosswalk_row(canonical_wbw_loc="9:9:9"),
            fixture_inputs(crosswalk=[fixture_crosswalk_row(canonical_wbw_loc="9:9:9")]),
        ),
        ("row_not_in_validated_carried_authority", fixture_crosswalk_row(), fixture_inputs(crosswalk=[])),
        (
            "dependency_id_not_in_authority",
            fixture_crosswalk_row(source_dependencies=[
                {"id": "llx-qword-ffffffffffff-99-99-999", "kind": "qword_denominator_row"},
                {"id": "ffffffffffff:u9:e9", "kind": "source_card"},
            ]),
            fixture_inputs(crosswalk=[fixture_crosswalk_row(source_dependencies=[
                {"id": "llx-qword-ffffffffffff-99-99-999", "kind": "qword_denominator_row"},
                {"id": "ffffffffffff:u9:e9", "kind": "source_card"},
            ])]),
        ),
        ("source_card_authority_unavailable", fixture_crosswalk_row(), fixture_inputs(denominator=[])),
        (
            "unverified_diagnostic_inputs",
            fixture_crosswalk_row(),
            DiagnosticInputs(
                crosswalk=[],
                lemmas=[fixture_lemma_row("1ec0de000001", FIXTURE_SURFACE)],
                forms=[fixture_form_row("1ec0de000001", FIXTURE_SURFACE)],
                stems=[fixture_stem_row("1ec0de000001", FIXTURE_SURFACE)],
                dependency_hashes={},
                typed_edges={FIXTURE_LOC: [fixture_typed_edge("1ec0de000001")]},
                typed_graph_meta={},
                loc_surface={},
            ),
        ),
    ]


def build_fixtures() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = []
    scenarios = []
    for scenario, row, inputs in fixture_scenarios():
        record = bridge_row(row, inputs)
        record["contract_id"] = f"{CONTRACT_PREFIX}:fixture:{scenario}"
        record["projection"]["projection_id"] = f"{CONTRACT_PREFIX}:fixture:{scenario}:projection"
        records.append(record)
        scenarios.append(
            {
                "blockers": sorted(
                    {
                        blocker["blocker_id"]
                        for fact in record["facts"]
                        for blocker in fact.get("unresolved_blockers") or []
                    }
                ),
                "preserved_candidates": sum(
                    1 for fact in record["facts"] if fact["fact_type"] == "largelexicon_lexeme_candidate"
                ),
                "projection_status": record["projection"]["status"],
                "scenario": scenario,
            }
        )
    errors = validate_records(records)
    if errors:
        raise BridgeError("fixture records are invalid: " + "; ".join(errors[:3]))
    boundary = public_fixture_errors(records)
    if boundary:
        raise BridgeError("fixture records breach the public boundary: " + "; ".join(boundary[:3]))
    payload = b"".join(_canonical(record).encode("utf-8") + b"\n" for record in records)
    meta = {
        "blocker_vocabulary": sorted(BLOCKER_STATUS),
        "certified_records": 0,
        "generator": PRODUCER_ID + " --write-fixtures",
        "learner_visible_records": 0,
        "note": "in-memory behavioural fixtures; no committed table row is reproduced here",
        "projector_id": PROJECTOR_ID,
        "public_boundary_clean": True,
        "row_count": len(records),
        "scenarios": scenarios,
        "schema": "qamus/largelexicon-fact-bridge-fixtures-meta@1",
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    return records, meta


def write_fixtures(directory: Path | None = None) -> dict[str, Any]:
    target = directory or FIXTURE_DIR
    target.mkdir(parents=True, exist_ok=True)
    records, meta = build_fixtures()
    (target / "bridge-fixtures.jsonl").write_bytes(
        b"".join(_canonical(record).encode("utf-8") + b"\n" for record in records)
    )
    (target / "bridge-fixtures.meta.json").write_text(review_json(meta), encoding="utf-8", newline="\n")
    return meta


def check_fixtures(directory: Path | None = None) -> list[str]:
    target = directory or FIXTURE_DIR
    records, meta = build_fixtures()
    expected = b"".join(_canonical(record).encode("utf-8") + b"\n" for record in records)
    problems: list[str] = []
    rows_path = target / "bridge-fixtures.jsonl"
    meta_path = target / "bridge-fixtures.meta.json"
    if not rows_path.exists() or rows_path.read_bytes() != expected:
        problems.append("bridge-fixtures.jsonl is missing or stale")
    if not meta_path.exists() or meta_path.read_text(encoding="utf-8") != review_json(meta):
        problems.append("bridge-fixtures.meta.json is missing or stale")
    return problems


SCAN_LIMIT = 2000


def scan_report() -> dict[str, Any]:
    """A bounded, deterministic run over real committed rows (evidence, not fixtures)."""

    inputs = BridgeInputs.from_release()
    rows = inputs.crosswalk[:SCAN_LIMIT]
    records = [bridge_row(row, inputs) for row in rows]
    errors = validate_records(records)
    if errors:
        raise BridgeError("bridge emitted invalid typed-claim records: " + "; ".join(errors[:5]))
    summary = summarize(records)
    release = promoter.read_release()
    return {
        "upstream_binding": {
            "authorities": inputs.authority_binding(),
            "authority_digest": inputs.authority_digest(),
            "carried_table_sha256": dict(sorted(inputs.dependency_hashes.items())),
            "target_release_sha256": hashlib.sha256(
                promoter.release_path().read_bytes()
            ).hexdigest(),
            "typed_graph": inputs.typed_graph_meta,
            "typed_release_losslessness": release["losslessness"],
        },
        "generator": PRODUCER_ID + " --write-scan",
        "note": (
            "bounded run over the first %d carried crosswalk rows in manifest order; "
            "no row content is reproduced, only counts" % SCAN_LIMIT
        ),
        "projector_id": PROJECTOR_ID,
        "scan_limit": SCAN_LIMIT,
        "schema": "qamus/largelexicon-fact-bridge-scan@2",
        "summary": summary,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locs", nargs="*", help="restrict the run to these canonical quran locs")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None, help="write the typed-claim records as JSONL")
    parser.add_argument("--write-fixtures", action="store_true")
    parser.add_argument("--check-fixtures", action="store_true")
    parser.add_argument("--write-scan", action="store_true")
    parser.add_argument("--check-scan", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.write_scan or args.check_scan:
        report = scan_report()
        path = FIXTURE_DIR / "real-data-scan.meta.json"
        rendered = review_json(report)
        if args.write_scan:
            FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8", newline="\n")
        elif not path.exists() or path.read_text(encoding="utf-8") != rendered:
            raise SystemExit("real-data scan report is stale or non-deterministic")
        print(rendered, end="")
        return 0
    if args.write_fixtures:
        print(review_json(write_fixtures()), end="")
        return 0
    if args.check_fixtures:
        problems = check_fixtures()
        print(review_json({"ok": not problems, "problems": problems}), end="")
        return 1 if problems else 0
    destination = args.out or DEFAULT_OUTPUT
    if not destination.resolve().is_relative_to((ROOT / "out").resolve()):
        raise SystemExit("full typed-claim output must be written under the gitignored out/ tree")
    result = run(locs=set(args.locs) if args.locs else None, limit=args.limit)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"".join(canonical_line_bytes(r) for r in result["records"]))
    print(review_json(result["summary"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
