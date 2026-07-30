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
PRODUCER_ID = "tools/largelexicon_fact_bridge.py"
PRODUCER_VERSION = "1.0.0"
PROJECTOR_ID = "largelexicon.carried_lexeme_candidate.v1"
RULE_ID = "largelexicon-carried-loc-first-exact-surface-candidate"
CONTRACT_PREFIX = "llxbridge"
ACCEPTED_CROSSWALK_STATUS = "canonical_crosswalk_accepted"
ACCEPTED_TRANSCLUSION_ROUTE = "entry_card_qword_to_canonical_crosswalk_accepted"
FORBIDDEN_BINDING_PREFIXES = ("missing-loc|", "sarf:surface:")
REQUIRED_DEPENDENCY_KINDS = frozenset({"qword_denominator_row", "source_card"})

MATERIALIZATION_TARGET = {
    "artifact": "qamus/examples/largelexicon-fact-bridge/typed-claims.jsonl",
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
    "unresolved_canonical_loc": "source_gap",
    "crosswalk_packet_not_accepted": "source_gap",
    "no_carried_lexical_support": "producer_pending",
    "page_context_only_no_lexical_edge": "unresolved",
    "root_family_relation_not_lexeme_identity": "unresolved",
    "non_certified_graph_edge_only": "unresolved",
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


def _fact_id(core: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(core).encode("utf-8")).hexdigest()


def review_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def is_canonical_loc(value: Any) -> bool:
    if not isinstance(value, str) or any(value.startswith(prefix) for prefix in FORBIDDEN_BINDING_PREFIXES):
        return False
    parts = value.split(":")
    return len(parts) == 3 and all(part.isdigit() and 1 <= len(part) <= 3 and int(part) >= 0 for part in parts)


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


class BridgeInputs:
    """Carried target-schema rows plus candidate graph evidence, gate-checked."""

    def __init__(
        self,
        *,
        crosswalk: Iterable[dict[str, Any]],
        lemmas: Iterable[dict[str, Any]],
        forms: Iterable[dict[str, Any]],
        stems: Iterable[dict[str, Any]],
        dependency_hashes: dict[str, str],
        graph_edges: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
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
        return cls(
            crosswalk=crosswalk,
            lemmas=tables.carried("lemma-source"),
            forms=tables.carried("form-source"),
            stems=tables.carried("stem-source"),
            dependency_hashes=tables.dependency_hashes(),
            graph_edges=load_lexeme_join_edges(),
        )

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
    core = {
        "fact_type": "largelexicon_lexeme_candidate",
        "form_id": str(form["form_id"]),
        "loc": loc,
        "plane": "typed_claim",
        "producer": PRODUCER_ID,
        "surface": surface,
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
            ],
        ),
        "dependent_fact_ids": [],
        "dependent_projection_ids": [],
        "derivation_chain": [],
        "evidence": {
            "confidence": "unknown",
            "evidence_ids": [f"llx-form-{form['form_id']}", f"llx-crosswalk-{row['row_id']}"],
            "status": "source_addressed_candidate",
            "summary": "a carried target-schema form row documents this exact written surface for this entry",
        },
        "evidence_mode": "normalized_lexical_body",
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

    observed = {
        "exact_surface_entry_ids": entry_ids,
        "graph_edge_count": len(graph_edges),
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
        "row_id": "llx-crosswalk-llx-qword-page0000page-01-01-001",
        "qword_row_id": "llx-qword-page0000page-01-01-001",
        "entry_id": "page0000page",
        "source_keys": ["n001"],
        "card_id": "page0000page:u1:e1",
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
            {"id": "llx-qword-page0000page-01-01-001", "kind": "qword_denominator_row"},
            {"id": "page0000page", "kind": "entry"},
            {"id": "page0000page:u1:e1", "kind": "source_card"},
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


def fixture_inputs(*, forms=None, lemmas=None, stems=None, graph_edges=None) -> BridgeInputs:
    entry = "lexeme000001"
    return BridgeInputs(
        crosswalk=[],
        lemmas=[fixture_lemma_row(entry, FIXTURE_SURFACE)] if lemmas is None else lemmas,
        forms=[fixture_form_row(entry, FIXTURE_SURFACE)] if forms is None else forms,
        stems=[fixture_stem_row(entry, FIXTURE_SURFACE)] if stems is None else stems,
        dependency_hashes=FIXTURE_DEPENDENCY_HASHES,
        graph_edges=graph_edges or {},
    )


def fixture_scenarios() -> list[tuple[str, dict[str, Any], BridgeInputs, bool]]:
    """``(scenario, crosswalk_row, inputs, carried)`` covering every closed blocker."""

    twin = [fixture_form_row("lexeme000001", FIXTURE_SURFACE), fixture_form_row("lexeme000002", FIXTURE_SURFACE, "001")]
    return [
        ("accepted_single_candidate", fixture_crosswalk_row(), fixture_inputs(), True),
        (
            "lexical_collision_requires_context",
            fixture_crosswalk_row(),
            fixture_inputs(
                forms=twin,
                lemmas=[fixture_lemma_row("lexeme000001", FIXTURE_SURFACE), fixture_lemma_row("lexeme000002", FIXTURE_SURFACE)],
                stems=[fixture_stem_row("lexeme000001", FIXTURE_SURFACE)],
            ),
            True,
        ),
        (
            "page_context_only_no_lexical_edge",
            fixture_crosswalk_row(),
            fixture_inputs(forms=[], lemmas=[fixture_lemma_row("page0000page", "شَيْء")], stems=[]),
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
                        {"loc": FIXTURE_LOC, "entry_id": "lexeme000009", "edge_type": "headword", "relation": "root_confirms", "row_root": "ا ل ه"}
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
                    FIXTURE_LOC: [{"loc": FIXTURE_LOC, "entry_id": "lexeme000009", "edge_type": "form", "relation": "linkage_only"}]
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
            fixture_inputs(forms=[fixture_form_row("lexeme000001", FIXTURE_NORM_TWIN)], lemmas=[], stems=[]),
            True,
        ),
        ("no_carried_lexical_support", fixture_crosswalk_row(), fixture_inputs(forms=[], lemmas=[], stems=[]), True),
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
    payload = b"".join(_canonical(record).encode("utf-8") + b"\n" for record in records)
    meta = {
        "blocker_vocabulary": sorted(BLOCKER_STATUS),
        "certified_records": 0,
        "generator": PRODUCER_ID + " --write-fixtures",
        "learner_visible_records": 0,
        "note": "in-memory behavioural fixtures; no committed table row is reproduced here",
        "projector_id": PROJECTOR_ID,
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

    result = run(limit=SCAN_LIMIT)
    summary = result["summary"]
    return {
        "generator": PRODUCER_ID + " --write-scan",
        "note": (
            "bounded run over the first %d carried crosswalk rows in manifest order; "
            "no row content is reproduced, only counts" % SCAN_LIMIT
        ),
        "projector_id": PROJECTOR_ID,
        "scan_limit": SCAN_LIMIT,
        "schema": "qamus/largelexicon-fact-bridge-scan@1",
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
    result = run(locs=set(args.locs) if args.locs else None, limit=args.limit)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(b"".join(_canonical(record).encode("utf-8") + b"\n" for record in result["records"]))
    print(review_json(result["summary"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
