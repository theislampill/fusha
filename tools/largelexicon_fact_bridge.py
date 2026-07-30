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
    return len(parts) == 3 and all(part.isdigit() and 1 <= len(part) <= 3 and int(part) >= 0 for part in parts)


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


def typed_edge_errors(edge: dict[str, Any]) -> list[str]:
    """Closed structural contract for an eligible canonical typed lexeme/form edge."""

    problems: list[str] = []
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


def load_loc_surface_index(path: Path | None = None) -> dict[str, str]:
    """The committed canonical loc → written-surface index."""

    source = path or LOC_SURFACE_INDEX
    index: dict[str, str] = {}
    if not source.exists():
        return index
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                index[str(row["loc"])] = str(row["surface"])
    return index


def load_lexeme_join_edges(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Index the candidate lexeme-join lattice by loc. Candidate edges only."""

    source = path or LEXEME_JOIN_EDGES
    edges: dict[str, list[dict[str, Any]]] = {}
    if not source.exists():
        return edges
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                edges.setdefault(str(row.get("loc")), []).append(row)
    return edges


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


class BridgeInputs:
    """Carried target-schema rows plus canonical typed graph evidence, gate-checked."""

    def __init__(
        self,
        *,
        crosswalk: Iterable[dict[str, Any]],
        lemmas: Iterable[dict[str, Any]],
        forms: Iterable[dict[str, Any]],
        stems: Iterable[dict[str, Any]],
        dependency_hashes: dict[str, str],
        graph_edges: dict[str, list[dict[str, Any]]] | None = None,
        typed_edges: dict[str, list[dict[str, Any]]] | None = None,
        typed_graph_meta: dict[str, Any] | None = None,
        loc_surface: dict[str, str] | None = None,
        validate_rows: bool = True,
    ) -> None:
        if validate_rows:
            errors = _input_errors(crosswalk, lemmas, forms, stems, dependency_hashes, typed_edges or {})
            if errors:
                raise BridgeError("bridge inputs failed closed: " + "; ".join(errors[:5]))
        self.typed_edges = dict(typed_edges or {})
        self.typed_graph_meta = dict(typed_graph_meta or {"typed_graph_sha256": "unbound", "bundles": []})
        self.loc_surface = dict(loc_surface or {})
        self.crosswalk = list(crosswalk)
        self.lemmas = {str(row["entry_id"]): row for row in lemmas}
        self.forms = list(forms)
        self.stems = list(stems)
        self.dependency_hashes = dict(dependency_hashes)
        self.graph_edges = dict(graph_edges or {})
        self._forms_by_surface: dict[str, list[dict[str, Any]]] = {}
        self._forms_by_norm: dict[str, list[dict[str, Any]]] = {}
        for row in self.forms:
            self._forms_by_surface.setdefault(str(row.get("surface")), []).append(row)
            self._forms_by_norm.setdefault(str(row.get("surface_norm_strict")), []).append(row)
        self._stems_by_key: dict[tuple[str, str], dict[str, Any]] = {
            (str(row.get("entry_id")), str(row.get("surface"))): row for row in self.stems
        }

    @classmethod
    def from_release(cls, *, locs: set[str] | None = None) -> "BridgeInputs":
        tables = LargelexiconTargetTables.open()
        crosswalk = tables.carried("qword-crosswalk")
        if locs is not None:
            crosswalk = [row for row in crosswalk if str(row.get("canonical_quran_loc")) in locs]
        typed_edges, typed_graph_meta = load_typed_graph()
        return cls(
            crosswalk=crosswalk,
            lemmas=tables.carried("lemma-source"),
            forms=tables.carried("form-source"),
            stems=tables.carried("stem-source"),
            dependency_hashes=tables.dependency_hashes(),
            graph_edges=load_lexeme_join_edges(),
            typed_edges=typed_edges,
            typed_graph_meta=typed_graph_meta,
            loc_surface=load_loc_surface_index(),
        )

    def accepted_typed_edges(self, loc: str, surface: str) -> list[dict[str, Any]]:
        """Accepted typed edges at this loc whose written surface agrees exactly."""

        return [
            edge
            for edge in self.typed_edges.get(loc, [])
            if str((edge.get("details") or {}).get("surface")) == surface
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


def _source_evidence(structured: dict[str, Any], addresses: list[dict[str, str]]) -> dict[str, Any]:
    return {"source_addresses": addresses, "structured_source_fact": structured}


def _dependencies(hashes: dict[str, str], extra: list[dict[str, str]]) -> dict[str, Any]:
    addresses = [
        {
            "address": f"qamus/indexes/largelexicon/target-schema/TARGET-RELEASE.json#{family}@sha256:{digest}",
            "source_kind": "corpus_record",
        }
        for family, digest in sorted(hashes.items())
    ]
    return {"fact_ids": [], "source_addresses": addresses + extra}


def _guards(names: Iterable[str]) -> list[dict[str, str]]:
    return [{"guard_id": name, "reason": GUARD_REASONS[name]} for name in names]


def _candidate_fact(
    *,
    row: dict[str, Any],
    form: dict[str, Any],
    lemma: dict[str, Any] | None,
    stem: dict[str, Any] | None,
    graph_edges: list[dict[str, Any]],
    typed_edges: list[dict[str, Any]],
    typed_graph_meta: dict[str, Any],
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
    core = {
        "canonical_loc": loc,
        "dependency_digests": dict(sorted(hashes.items())),
        "fact_type": "largelexicon_lexeme_candidate",
        "form_realization": fact_value["form_realization"],
        "lexeme_candidate": fact_value["lexeme_candidate"],
        "plane": "typed_claim",
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "rule_projector": {"projector_id": PROJECTOR_ID, "rule_id": RULE_ID, "version": PRODUCER_VERSION},
        "stem_segmentation": fact_value["stem_segmentation"],
        "surface": surface,
        "typed_graph_evidence": fact_value["typed_graph_evidence"],
        "typed_graph_sha256": typed_graph_meta.get("typed_graph_sha256"),
    }
    return {
        "certification": {
            "reason": "carried-table lookup is candidate evidence; only the certifier may certify",
            "status": "candidate",
        },
        "contradiction_records": [],
        "defeaters": [],
        "dependencies": _dependencies(
            hashes,
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
        "fact_id": _fact_id(core),
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
    }


def _abstention_fact(
    *,
    row: dict[str, Any],
    blockers: list[str],
    hashes: dict[str, str],
    loc: str | None,
    graph_edges: list[dict[str, Any]],
    observed: dict[str, Any],
) -> dict[str, Any]:
    surface = str(row.get("visible_surface") or "")
    address = f"largelexicon:qword-crosswalk@2:{row.get('row_id')}"
    core = {
        "blockers": sorted(blockers),
        "fact_type": "largelexicon_bridge_abstention",
        "plane": "typed_claim",
        "producer": PRODUCER_ID,
        "row_id": str(row.get("row_id")),
    }
    fact_value = {
        "abstained": True,
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
    return {
        "certification": {"reason": "; ".join(BLOCKER_REASONS[name] for name in blockers), "status": "blocked"},
        "contradiction_records": [],
        "defeaters": [
            {"defeater_id": name, "fact_ids": [], "reason": BLOCKER_REASONS[name]} for name in blockers
        ],
        "dependencies": _dependencies(hashes, [{"address": address, "source_kind": "corpus_record"}]),
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
        "fact_id": _fact_id(core),
        "fact_type": "largelexicon_bridge_abstention",
        "fact_value": fact_value,
        "guards": _guards(["loc_first_canonical_address", "carried_target_schema_rows_only", "release_dependency_bound"]),
        "ownership": {
            "primary": {"owner_id": "sarf", "owner_type": "skill"},
            "secondary": [{"owner_id": "largelexicon", "owner_type": "lookup_substrate"}],
        },
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "rule_projector": {"projector_id": PROJECTOR_ID, "rule_id": RULE_ID, "version": PRODUCER_VERSION},
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
    }


def _worst_status(blockers: list[str]) -> str:
    order = ["blocked", "source_gap", "producer_pending", "unresolved"]
    statuses = {BLOCKER_STATUS[name] for name in blockers}
    for candidate in order:
        if candidate in statuses:
            return candidate
    return "unresolved"


def bridge_row(row: dict[str, Any], inputs: BridgeInputs, *, carried: bool = True) -> dict[str, Any]:
    """Bridge one crosswalk row into exactly one typed-claim contract record."""

    hashes = inputs.dependency_hashes
    loc_value = row.get("canonical_quran_loc")
    loc = str(loc_value) if is_canonical_loc(loc_value) else None
    graph_edges = inputs.graph_edges.get(loc or "", [])
    blockers: list[str] = []

    if not carried:
        blockers.append("quarantined_or_flagged_source_row")
    dependency_kinds = {str(item.get("kind")) for item in row.get("source_dependencies") or []}
    if not REQUIRED_DEPENDENCY_KINDS.issubset(dependency_kinds):
        blockers.append("missing_dependency_release")
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
            row=row, blockers=blockers, hashes=hashes, loc=loc, graph_edges=graph_edges, observed=observed
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
            hashes=hashes,
            candidate_count=len(exact),
            loc=str(loc),
        )
        for form in exact
    ]
    if len(entry_ids) > 1:
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


def public_fixture_errors(node: Any, path: str = "$") -> list[str]:
    """Recursively reject prohibited public classes in a committed fixture."""

    from largelexicon_common import FORBIDDEN_PUBLIC_SUBSTRINGS, match_forbidden_labels

    problems: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).lower() in PROHIBITED_FIXTURE_KEYS:
                problems.append(f"{path}.{key}: prohibited field class in a committed public fixture")
            problems.extend(public_fixture_errors(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            problems.extend(public_fixture_errors(value, f"{path}[{index}]"))
    elif isinstance(node, str):
        for pattern in PROHIBITED_VALUE_PATTERNS:
            if pattern.search(node):
                problems.append(f"{path}: prohibited URL or absolute/private path in a public fixture")
                break
        labels = match_forbidden_labels(node.lower(), FORBIDDEN_PUBLIC_SUBSTRINGS)
        if labels:
            problems.append(f"{path}: external source label(s) {sorted(labels)} in a public fixture")
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
            if fact.get("rule_projector", {}).get("projector_id") != PROJECTOR_ID:
                errors.append(f"{label}.facts[{fact_index}]: fact is not attributed to the registered bridge projector")
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

    return {
        "schema": TYPED_GRAPH_SCHEMA,
        "edge_id": f"edge:fixture:{entry_id}:{loc}",
        "edge_type": edge_type,
        "from_node_id": f"selected-word:{entry_id}:s1:u1:f1:o{loc}",
        "from_node_type": "selected-word",
        "to_node_id": f"entry:{entry_id}",
        "to_node_type": "entry",
        "status": status,
        "details": {"surface": surface},
        "producer": {"id": "fixture", "version": "1.0.0"},
    }


def fixture_inputs(
    *, forms=None, lemmas=None, stems=None, graph_edges=None, typed_edges=None, loc_surface=None
) -> BridgeInputs:
    entry = "1ec0de000001"
    form_rows = [fixture_form_row(entry, FIXTURE_SURFACE)] if forms is None else forms
    if typed_edges is None:
        # Default: one accepted typed edge per documenting entry, so the accepted
        # and collision fixtures exercise the typed-graph join rather than skip it.
        typed_edges = {
            FIXTURE_LOC: [
                fixture_typed_edge(entry_id)
                for entry_id in sorted({str(row["entry_id"]) for row in form_rows})
            ]
        }
        if not typed_edges[FIXTURE_LOC]:
            typed_edges = {}
    return BridgeInputs(
        crosswalk=[],
        lemmas=[fixture_lemma_row(entry, FIXTURE_SURFACE)] if lemmas is None else lemmas,
        forms=form_rows,
        stems=[fixture_stem_row(entry, FIXTURE_SURFACE)] if stems is None else stems,
        dependency_hashes=FIXTURE_DEPENDENCY_HASHES,
        graph_edges=graph_edges or {},
        typed_edges=typed_edges,
        typed_graph_meta={
            "bundles": [
                {"path": "fixture://typed-edges", "schema": TYPED_GRAPH_SCHEMA, "sha256": "f" * 64,
                 "row_count": 1, "eligible_edge_count": 1, "present": True}
            ],
            "eligible_edge_count": 1,
            "eligible_loc_count": 1,
            "typed_graph_sha256": "f" * 64,
        },
        loc_surface={FIXTURE_LOC: FIXTURE_SURFACE} if loc_surface is None else loc_surface,
    )


def fixture_scenarios() -> list[tuple[str, dict[str, Any], BridgeInputs, bool]]:
    """``(scenario, crosswalk_row, inputs, carried)`` covering every closed blocker."""

    twin = [fixture_form_row("1ec0de000001", FIXTURE_SURFACE), fixture_form_row("1ec0de000002", FIXTURE_SURFACE, "001")]
    return [
        ("accepted_single_candidate", fixture_crosswalk_row(), fixture_inputs(), True),
        (
            "lexical_collision_requires_context",
            fixture_crosswalk_row(),
            fixture_inputs(
                forms=twin,
                lemmas=[fixture_lemma_row("1ec0de000001", FIXTURE_SURFACE), fixture_lemma_row("1ec0de000002", FIXTURE_SURFACE)],
                stems=[fixture_stem_row("1ec0de000001", FIXTURE_SURFACE)],
            ),
            True,
        ),
        (
            "page_context_only_no_lexical_edge",
            fixture_crosswalk_row(),
            fixture_inputs(forms=[], lemmas=[fixture_lemma_row("0aae00000000", "شَيْء")], stems=[]),
            True,
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
            True,
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
            True,
        ),
        ("unresolved_canonical_loc", fixture_crosswalk_row(canonical_quran_loc="missing-loc|2:255"), fixture_inputs(), True),
        (
            "crosswalk_packet_not_accepted",
            fixture_crosswalk_row(
                status="source_crosswalk_packet_ready",
                transclusion_route="entry_card_qword_to_canonical_crosswalk_packet",
            ),
            fixture_inputs(),
            True,
        ),
        ("quarantined_or_flagged_source_row", fixture_crosswalk_row(), fixture_inputs(), False),
        ("missing_dependency_release", fixture_crosswalk_row(source_dependencies=[]), fixture_inputs(), True),
        (
            "norm_only_surface_match",
            fixture_crosswalk_row(),
            fixture_inputs(forms=[fixture_form_row("1ec0de000001", FIXTURE_NORM_TWIN)], lemmas=[], stems=[]),
            True,
        ),
        ("no_carried_lexical_support", fixture_crosswalk_row(), fixture_inputs(forms=[], lemmas=[], stems=[]), True),
        ("missing_typed_graph_evidence", fixture_crosswalk_row(), fixture_inputs(typed_edges={}), True),
        (
            "typed_edge_identity_disagreement",
            fixture_crosswalk_row(),
            fixture_inputs(typed_edges={FIXTURE_LOC: [fixture_typed_edge("1ec0de000009")]}),
            True,
        ),
        (
            "loc_not_in_canonical_index",
            fixture_crosswalk_row(),
            fixture_inputs(loc_surface={"1:1:1": "بِسْمِ"}),
            True,
        ),
        (
            "loc_surface_disagreement",
            fixture_crosswalk_row(),
            fixture_inputs(loc_surface={FIXTURE_LOC: FIXTURE_NORM_TWIN}),
            True,
        ),
        ("wbw_loc_disagreement", fixture_crosswalk_row(canonical_wbw_loc="9:9:9"), fixture_inputs(), True),
    ]


def build_fixtures() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = []
    scenarios = []
    for scenario, row, inputs, carried in fixture_scenarios():
        record = bridge_row(row, inputs, carried=carried)
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
