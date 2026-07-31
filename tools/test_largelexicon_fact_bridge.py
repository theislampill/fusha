#!/usr/bin/env python3
"""Behavioural tests for the A3 largelexicon typed bridge.

Every test is a mutation: it takes the one fixture that legitimately produces a
candidate and breaks exactly one precondition, then asserts the bridge abstains
with the precise blocker instead of guessing. Fixtures are in-memory so the suite
runs without touching the 253k-row committed tables.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import fact_projectors, largelexicon_fact_bridge as bridge, typed_claim_contract


LOC = bridge.FIXTURE_LOC
SURFACE = bridge.FIXTURE_SURFACE
NORM = bridge.FIXTURE_NORM
OTHER_SURFACE = bridge.FIXTURE_NORM_TWIN

# The fixture builders live beside the bridge so the committed fixtures and this
# suite can never describe two different bridges.
crosswalk_row = bridge.fixture_crosswalk_row
form_row = bridge.fixture_form_row
lemma_row = bridge.fixture_lemma_row
stem_row = bridge.fixture_stem_row
make_inputs = bridge.fixture_inputs


def inputs_for(row: dict, **kwargs):
    """Inputs whose validated carried authority contains EXACTLY this row.

    Carried-ness is authority membership, not a flag, so a test that bridges a
    mutated row must supply that row (and its matching denominator row) as the
    authority it belongs to; otherwise it is measuring the membership guard
    instead of the guard under test.
    """

    kwargs.setdefault("crosswalk", [row])
    kwargs.setdefault("denominator", [bridge.fixture_denominator_row(
        row_id=str(row.get("qword_row_id")),
        entry_id=str(row.get("entry_id")),
        card_id=str(row.get("card_id")),
    )])
    try:
        return make_inputs(**kwargs)
    except bridge.BridgeError:
        # A row that cannot pass the target schema can never be a member of any
        # carried authority; the membership guard is then the honest blocker.
        return make_inputs(**{key: value for key, value in kwargs.items()
                              if key not in ("crosswalk", "denominator")})


def blockers_of(record: dict) -> set[str]:
    return {
        blocker["blocker_id"]
        for fact in record["facts"]
        for blocker in fact.get("unresolved_blockers") or []
    }


def candidates_of(record: dict) -> list[dict]:
    return [fact for fact in record["facts"] if fact["fact_type"] == "largelexicon_lexeme_candidate"]


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError("FAILED: " + name)


def assert_valid(record: dict, name: str) -> None:
    errors = bridge.validate_records([record])
    check(f"{name} produces a valid typed-claim record ({errors[:2]})", not errors)


# --------------------------------------------------------------------------- #
# the one accepted case
# --------------------------------------------------------------------------- #
def test_accepted_single_candidate() -> None:
    inputs = make_inputs()
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "accepted single candidate")
    check("accepted record is a candidate projection", record["projection"]["status"] == "candidate")
    check("accepted record preserves exactly one candidate", len(candidates_of(record)) == 1)
    fact = candidates_of(record)[0]
    check("accepted fact is candidate, never certified", fact["certification"]["status"] == "candidate")
    check("accepted evidence is never certified", fact["evidence"]["status"] == "source_addressed_candidate")
    check("accepted record is never learner visible", record["projection"]["learner_visible"] is False)
    check("accepted record forbids public materialization",
          record["projection"]["materialization_target"]["public_materialization_allowed"] is False)
    check("accepted record forbids live mutation",
          record["projection"]["materialization_target"]["live_mutation_allowed"] is False)
    check("accepted record has no claim", record["projection"]["claim"] is None)
    check("candidate binds the canonical loc", record["canonical_occurrence"]["occurrence_id"] == f"quran:{LOC}")
    check("candidate records dependency hashes",
          any("qword-crosswalk@sha256:" in item["address"] for item in fact["dependencies"]["source_addresses"]))


def test_lexeme_identity_is_not_the_crosswalk_entry() -> None:
    """Mutating only the page-context entry_id must not change the lexeme claim."""

    inputs = make_inputs()
    base = candidates_of(bridge.bridge_row(crosswalk_row(), inputs))[0]
    moved = crosswalk_row(
        entry_id="0aae00000002",
        row_id="llx-crosswalk-llx-qword-0aae00000002-01-01-001",
        qword_row_id="llx-qword-0aae00000002-01-01-001",
        card_id="0aae00000002:u1:e1",
        source_dependencies=[
            {"id": "llx-qword-0aae00000002-01-01-001", "kind": "qword_denominator_row"},
            {"id": "0aae00000002:u1:e1", "kind": "source_card"},
        ],
    )
    # The moved row is a member of ITS OWN carried authority, with the matching
    # denominator row; only the displaying page differs.
    moved_inputs = make_inputs(
        crosswalk=[moved],
        denominator=[bridge.fixture_denominator_row(
            row_id="llx-qword-0aae00000002-01-01-001",
            entry_id="0aae00000002",
            card_id="0aae00000002:u1:e1",
        )],
    )
    other = candidates_of(bridge.bridge_row(moved, moved_inputs))[0]
    check("lexeme candidate entry is the documenting entry, not the displaying page",
          base["fact_value"]["lexeme_candidate"]["entry_id"] == "1ec0de000001")
    check("page context follows the crosswalk entry, not the lexeme",
          other["fact_value"]["page_context"]["crosswalk_entry_id"] == "0aae00000002")
    check("page context is explicitly never a lexeme edge",
          other["fact_value"]["page_context"]["never_lexeme_edge"] is True)
    check("lexeme candidate is unchanged by the page move",
          other["fact_value"]["lexeme_candidate"] == base["fact_value"]["lexeme_candidate"])
    # The LEXICAL claim is untouched by the page move...
    check("lexical identity does not absorb the page context",
          bridge.lexeme_identity_digest(other) == bridge.lexeme_identity_digest(base))
    # ...while the whole-fact id legitimately moves, because page context and the
    # sealed authority are part of the recomputable content (round-6 requirement).
    check("the whole-fact id still tracks page context and authority",
          other["fact_id"] != base["fact_id"])
    check("both ids remain recomputable from their own content",
          bridge.recompute_fact_id(other) == other["fact_id"]
          and bridge.recompute_fact_id(base) == base["fact_id"])


# --------------------------------------------------------------------------- #
# mutation tests — each breaks one precondition and must abstain precisely
# --------------------------------------------------------------------------- #
def test_collision_abstains_and_preserves_every_candidate() -> None:
    forms = [form_row("1ec0de000001", SURFACE), form_row("1ec0de000002", SURFACE, "001")]
    inputs = make_inputs(forms=forms, lemmas=[lemma_row("1ec0de000001", SURFACE), lemma_row("1ec0de000002", SURFACE)],
                         stems=[stem_row("1ec0de000001", SURFACE), stem_row("1ec0de000002", SURFACE)])
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "collision")
    check("collision abstains", record["projection"]["status"] == "unresolved")
    check("collision preserves BOTH candidates", len(candidates_of(record)) == 2)
    check("collision names its blocker", blockers_of(record) == {"lexical_collision_requires_context"})
    check("collision records a tension", len(record.get("tension_records") or []) == 1)
    check("collision tension is unresolved", record["tension_records"][0]["status"] == "unresolved")
    check("collision never marks a winner",
          all(fact["certification"]["status"] == "candidate" for fact in candidates_of(record)))
    check("collision declares rank is not preference",
          all(fact["fact_value"]["candidate_rank_is_not_preference"] for fact in candidates_of(record)))


def test_multi_match_beyond_two_still_abstains() -> None:
    forms = [form_row(f"1ec0de00000{index}", SURFACE, f"00{index}") for index in (1, 2, 3)]
    inputs = make_inputs(forms=forms, lemmas=[lemma_row(f"1ec0de00000{index}", SURFACE) for index in (1, 2, 3)], stems=[])
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "multi match")
    check("three-way match abstains", record["projection"]["status"] == "unresolved")
    check("three-way match preserves all three", len(candidates_of(record)) == 3)
    check("three-way match names its blocker", blockers_of(record) == {"lexical_collision_requires_context"})


def test_page_context_only_abstains() -> None:
    """The displaying entry has a carried lemma row but documents no such form."""

    inputs = make_inputs(forms=[], lemmas=[lemma_row("0aae00000000", "شَيْء")], stems=[])
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "page context only")
    check("page-context-only abstains", record["projection"]["status"] == "unresolved")
    check("page-context-only names its blocker", blockers_of(record) == {"page_context_only_no_lexical_edge"})
    check("page-context-only emits no lexeme candidate", candidates_of(record) == [])


def test_root_only_abstains() -> None:
    edges = {LOC: [{"loc": LOC, "entry_id": "1ec0de000009", "edge_type": "headword", "relation": "root_confirms",
                    "row_root": "ا ل ه"}]}
    inputs = make_inputs(forms=[], lemmas=[], stems=[], graph_edges=edges)
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "root only")
    check("root-only abstains", record["projection"]["status"] == "unresolved")
    check("root-only names its blocker", blockers_of(record) == {"root_family_relation_not_lexeme_identity"})
    check("root-only emits no lexeme candidate", candidates_of(record) == [])


def test_non_certified_graph_edge_only_abstains() -> None:
    edges = {LOC: [{"loc": LOC, "entry_id": "1ec0de000009", "edge_type": "form", "relation": "linkage_only"}]}
    inputs = make_inputs(forms=[], lemmas=[], stems=[], graph_edges=edges)
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "candidate edge only")
    check("candidate-edge-only abstains", record["projection"]["status"] == "unresolved")
    check("candidate-edge-only names its blocker", blockers_of(record) == {"non_certified_graph_edge_only"})
    edge_records = record["facts"][0]["fact_value"]["candidate_graph_edges"]
    check("graph edges are labelled never-certified",
          all(item["status"] == "candidate_edge_never_certified" for item in edge_records))


def test_graph_edge_never_upgrades_a_candidate() -> None:
    """A candidate edge alongside a real form row stays candidate evidence only."""

    edges = {LOC: [{"loc": LOC, "entry_id": "1ec0de000001", "edge_type": "headword", "relation": "root_confirms",
                    "row_root": "ا ل ه"}]}
    inputs = make_inputs(graph_edges=edges)
    fact = candidates_of(bridge.bridge_row(crosswalk_row(), inputs))[0]
    check("graph edge does not certify", fact["certification"]["status"] == "candidate")
    check("graph edge is carried as a root-family relation",
          fact["fact_value"]["root_family_relations"][0]["status"] == "candidate_edge_never_certified")
    check("root is flagged as relation not identity", fact["fact_value"]["lexeme_candidate"]["root_is_relation_not_identity"])


def test_unresolved_loc_abstains() -> None:
    inputs = make_inputs()
    for bad in (None, "missing-loc|2:255", "sarf:surface:الله", "2:255", ""):
        bad_row = crosswalk_row(canonical_quran_loc=bad)
        record = bridge.bridge_row(bad_row, inputs_for(bad_row))
        assert_valid(record, f"unresolved loc {bad!r}")
        check(f"loc {bad!r} abstains", record["projection"]["status"] != "candidate")
        check(f"loc {bad!r} names its blocker", "unresolved_canonical_loc" in blockers_of(record))
        check(f"loc {bad!r} emits no lexeme candidate", candidates_of(record) == [])


def test_packet_ready_crosswalk_abstains() -> None:
    inputs = make_inputs()
    packet_ready = crosswalk_row(status="source_crosswalk_packet_ready",
                                 transclusion_route="entry_card_qword_to_canonical_crosswalk_packet")
    record = bridge.bridge_row(packet_ready, inputs_for(packet_ready))
    assert_valid(record, "packet ready")
    check("packet-ready abstains", record["projection"]["status"] == "source_gap")
    check("packet-ready names its blocker", "crosswalk_packet_not_accepted" in blockers_of(record))


def test_demoted_crosswalk_abstains() -> None:
    inputs = make_inputs()
    demoted = crosswalk_row(status="canonical_crosswalk_demoted")
    record = bridge.bridge_row(demoted, inputs_for(demoted))
    check("demoted abstains", record["projection"]["status"] != "candidate")
    check("demoted names its blocker", "crosswalk_packet_not_accepted" in blockers_of(record))


def test_quarantined_row_abstains() -> None:
    inputs = make_inputs()
    record = bridge.bridge_row(crosswalk_row(), make_inputs(crosswalk=[], non_carried_crosswalk=[crosswalk_row()]))
    assert_valid(record, "quarantined row")
    check("quarantined row abstains", record["projection"]["status"] == "blocked")
    check("quarantined row names its blocker", "quarantined_or_flagged_source_row" in blockers_of(record))
    check("quarantined row emits no lexeme candidate", candidates_of(record) == [])


def test_missing_dependency_abstains() -> None:
    for dependencies in ([{"id": "x", "kind": "entry"}], [{"id": "x", "kind": "source_card"}]):
        thin = crosswalk_row(source_dependencies=dependencies)
        record = bridge.bridge_row(thin, inputs_for(thin))
        assert_valid(record, "missing dependency")
        check("missing dependency abstains", record["projection"]["status"] == "blocked")
        check("missing dependency names its blocker", "missing_dependency_release" in blockers_of(record))
    # An empty dependency list cannot even pass the target schema, so such a row
    # is not a member of any carried authority and is blocked one gate earlier.
    empty = crosswalk_row(source_dependencies=[])
    record = bridge.bridge_row(empty, inputs_for(empty))
    check("dependency-less row is refused by the membership gate",
          "row_not_in_validated_carried_authority" in blockers_of(record))
    check("dependency-less row emits no candidate", candidates_of(record) == [])


def test_norm_only_match_abstains() -> None:
    """norm_only_match is a never_auto_resolve trigger: it may never resolve."""

    inputs = make_inputs(forms=[form_row("1ec0de000001", OTHER_SURFACE)], lemmas=[], stems=[])
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "norm only")
    check("norm-only abstains", record["projection"]["status"] == "blocked")
    check("norm-only names its blocker", blockers_of(record) == {"norm_only_surface_match"})
    check("norm-only emits no lexeme candidate", candidates_of(record) == [])


def test_no_support_abstains() -> None:
    inputs = make_inputs(forms=[], lemmas=[], stems=[])
    record = bridge.bridge_row(crosswalk_row(), inputs)
    assert_valid(record, "no support")
    check("no-support abstains", record["projection"]["status"] == "producer_pending")
    check("no-support names its blocker", blockers_of(record) == {"no_carried_lexical_support"})


def test_distinct_identity_kinds_stay_distinct() -> None:
    inputs = make_inputs()
    fact = candidates_of(bridge.bridge_row(crosswalk_row(), inputs))[0]
    value = fact["fact_value"]
    check("lexeme identity is its own field", "lexeme_candidate" in value)
    check("form realization is its own field", "form_realization" in value)
    check("stem segmentation is its own field", "stem_segmentation" in value)
    check("occurrence is its own field", "occurrence" in value)
    check("page context is its own field", "page_context" in value)
    check("root family is its own field", "root_family_relations" in value)
    check("form id is not the entry id", value["form_realization"]["form_id"] != value["lexeme_candidate"]["entry_id"])
    check("stem id is not the form id", value["stem_segmentation"]["stem_id"] != value["form_realization"]["form_id"])
    check("occurrence loc is not an entry id", value["occurrence"]["canonical_quran_loc"] == LOC)
    check("page-context entry differs from the lexeme entry",
          value["page_context"]["crosswalk_entry_id"] != value["lexeme_candidate"]["entry_id"])


# --------------------------------------------------------------------------- #
# registration and certification boundary
# --------------------------------------------------------------------------- #
def test_projector_is_registered_fail_closed() -> None:
    contract = fact_projectors.REGISTRY.contract(fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID)
    check("bridge projector is registered never_auto_resolve", contract["gate_tier"] == "never_auto_resolve")
    check("bridge projector declares its defeater guard", contract["defeater_checks"] == ["largelexicon_bridge_abstention_guard"])
    gates = fact_projectors.load_gate_tiers()
    check("never_auto_resolve exists in the gate SSOT", "never_auto_resolve" in gates)
    check("never_auto_resolve is the strictest rank",
          gates["never_auto_resolve"]["rank"] == max(item["rank"] for item in gates.values()))
    # The enforcing registry is tools/fact_projectors.py. The transclusion-lattice
    # registry keys @2.1 SKILL-RULE projectors to released sarf@2 / nahw@2 rule ids
    # through declarative predicates in tools/lattice_projectors.py; the bridge has
    # no skill rule ids and no declarative class predicate, so it is deliberately
    # NOT registered there rather than registered behind a placeholder predicate.
    lattice = json.loads((Path(__file__).resolve().parents[1] / "qamus" / "lattice" / "registered-projectors.json")
                         .read_text(encoding="utf-8"))
    entries = {item["projector_id"] for item in lattice["registered"]}
    check("bridge is not registered behind a placeholder lattice predicate",
          fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID not in entries)
    check("every lattice entry still keys real skill rules or a declarative predicate",
          all(item.get("class_predicate") for item in lattice["registered"]))


def test_registry_run_returns_candidate_or_abstention_only() -> None:
    inputs = make_inputs()
    result = fact_projectors.REGISTRY.run(
        fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID, crosswalk_row=crosswalk_row(), inputs=inputs
    )
    check("registry run yields a candidate", result["status"] == "candidate")
    check("registry run forbids materialization", result["materialization_allowed"] is False)
    check("registry run forbids certification", result["certification_allowed"] is False)
    collision_inputs = make_inputs(
        forms=[form_row("1ec0de000001", SURFACE), form_row("1ec0de000002", SURFACE, "001")], lemmas=[], stems=[]
    )
    abstained = fact_projectors.REGISTRY.run(
        fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID, crosswalk_row=crosswalk_row(), inputs=collision_inputs
    )
    check("registry run abstains on collision", abstained["status"] == "abstained")
    check("registry abstention names the blocker", abstained["blockers"] == ["lexical_collision_requires_context"])
    check("registry abstention emits no resolved candidate", abstained["candidate"] is None)
    check("registry abstention still preserves both fact ids", len(abstained["preserved_candidate_fact_ids"]) == 2)


def test_never_auto_resolve_cannot_be_certified() -> None:
    """A never_auto_resolve contract must have no certification path at all."""

    class _Store:
        def __init__(self, row):
            self.row = row

        def query(self, fact_id=None):
            return [self.row] if fact_id == self.row["fact_id"] else []

    row = {"fact_id": "sha256:" + "0" * 64, "fact_type": "largelexicon_lexeme_candidate"}
    votes = [
        {"voter_id": "a", "independent": True, "vote": "approve"},
        {"voter_id": "b", "independent": True, "vote": "approve"},
    ]
    try:
        fact_projectors.review_and_materialize(_Store(row), row["fact_id"], votes, "target", {})
    except fact_projectors.ProjectorValidationError as error:
        check("never_auto_resolve refuses certification even with two votes",
              "never_auto_resolve" in str(error))
    else:
        raise AssertionError("FAILED: never_auto_resolve candidate was certified")


def test_committed_fixtures_match_the_bridge() -> None:
    directory = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "largelexicon-fact-bridge"
    path = directory / "bridge-fixtures.jsonl"
    if not path.exists():
        return
    committed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors = bridge.validate_records(committed)
    check(f"committed fixtures are valid typed claims ({errors[:2]})", not errors)
    check("committed fixtures certify nothing",
          all(fact["certification"]["status"] != "certified" for record in committed for fact in record["facts"]))
    check("committed fixtures are never learner visible",
          all(record["projection"]["learner_visible"] is False for record in committed))
    check("committed fixtures cover every blocker",
          {blocker for record in committed for blocker in blockers_of(record)} == set(bridge.BLOCKER_STATUS))


def all_tests():
    """Collected at call time so appended tests can never be silently skipped."""

    return [value for name, value in sorted(globals().items()) if name.startswith("test_")]


# The frozen snapshot below is retained only for direct callers; the harness
# collects dynamically via all_tests(). EXPECTED_MINIMUM_TESTS and CRITICAL_PROBES
# are the contract the harness asserts.
TESTS = all_tests()
EXPECTED_MINIMUM_TESTS = 59
CRITICAL_PROBES = (
    "test_candidate_admission_requires_complete_authority",
    "test_carried_membership_binds_the_exact_row_body",
    "test_dependency_ids_bind_to_the_denominator_authority",
    "test_typed_edge_requires_reconstructible_content",
    "test_authority_digests_are_recomputed_not_trusted",
    "test_canonical_loc_requires_positive_coordinates",
    "test_certifier_refuses_never_auto_resolve_producer",
    "test_no_validation_bypass_can_return_a_candidate",
    "test_typed_graph_evidence_is_mandatory",
    "test_no_first_row_winner",
    "test_projector_identity_cannot_shed_a_fact_type_gate",
    "test_registry_two_vote_gate_requires_a_bundle",
    "test_stale_content_addressed_fact_id_is_refused",
    "test_authority_is_sealed_not_caller_declared",
    "test_duplicate_identities_are_refused_in_every_family",
    "test_invented_denominator_cannot_be_source_card_authority",
    "test_repository_metadata_binds_the_exact_parsed_content",
    "test_typed_edge_identity_and_endpoints_are_exact",
    "test_reader_boundary_is_stable",
)


def main() -> int:
    tests = all_tests()
    for test in tests:
        test()
    print(
        json.dumps(
            {"ok": True, "schema": "qamus/largelexicon-fact-bridge-tests@1", "tests": len(tests)},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0




# --------------------------------------------------------------------------- #
# defect-round-1 repairs
# --------------------------------------------------------------------------- #
def test_typed_graph_evidence_is_mandatory() -> None:
    """Exact surface is discovery only; a same-surface form elsewhere abstains."""

    record = bridge.bridge_row(crosswalk_row(), make_inputs(typed_edges={}))
    check("no typed edge abstains", record["projection"]["status"] == "source_gap")
    check("no typed edge names its blocker", blockers_of(record) == {"missing_typed_graph_evidence"})
    check("no typed edge emits no candidate", candidates_of(record) == [])

    other_loc = bridge.fixture_typed_edge("1ec0de000001", loc="9:9:9")
    elsewhere = bridge.bridge_row(crosswalk_row(), make_inputs(typed_edges={"9:9:9": [other_loc]}))
    check("a typed edge at another loc does not support this occurrence",
          blockers_of(elsewhere) == {"missing_typed_graph_evidence"})

    wrong_surface = bridge.fixture_typed_edge("1ec0de000001", surface=OTHER_SURFACE)
    surface_mismatch = bridge.bridge_row(crosswalk_row(), make_inputs(typed_edges={LOC: [wrong_surface]}))
    check("a same-surface form elsewhere does not support this occurrence",
          blockers_of(surface_mismatch) == {"missing_typed_graph_evidence"})

    wrong_entry = bridge.bridge_row(
        crosswalk_row(), make_inputs(typed_edges={LOC: [bridge.fixture_typed_edge("1ec0de000009")]})
    )
    check("a typed edge to another entry does not establish identity",
          blockers_of(wrong_entry) == {"typed_edge_identity_disagreement"})


def test_candidate_status_typed_edge_never_supports_identity() -> None:
    for status in ("candidate", "ambiguous", "source_gap", "rejected"):
        edge = bridge.fixture_typed_edge("1ec0de000001", status=status)
        check("typed edge status " + status + " is not structurally eligible",
              bridge.typed_edge_errors(edge) != [])


def test_occurrence_loc_is_never_manufactured() -> None:
    check("card address is not an occurrence loc",
          bridge.occurrence_loc_of("selected-word:1ec0de000001:s1:u1:f1:c2:284:x1") is None)
    check("explicit occurrence loc is read",
          bridge.occurrence_loc_of("selected-word:x:s1:u1:f1:c28:50:x12:o28:50:12") == "28:50:12")


def test_loc_must_agree_with_the_canonical_index() -> None:
    absent = bridge.bridge_row(crosswalk_row(), make_inputs(loc_surface={"1:1:1": "x"}))
    check("absent loc is blocked", blockers_of(absent) == {"loc_not_in_canonical_index"})
    mismatch = bridge.bridge_row(crosswalk_row(), make_inputs(loc_surface={LOC: OTHER_SURFACE}))
    check("loc/surface disagreement is blocked", blockers_of(mismatch) == {"loc_surface_disagreement"})
    for bad in ("0:0:0", "9:9:9", ""):
        drifted = crosswalk_row(canonical_wbw_loc=bad)
        record = bridge.bridge_row(drifted, inputs_for(drifted))
        check("wbw disagreement is caught", "wbw_loc_disagreement" in blockers_of(record))
    for bad in ("0:0:0", "1000:1:1", "2:255", "-1:2:3"):
        check("invalid loc coordinates are refused", not bridge.is_canonical_loc(bad) or bad == "0:0:0")


def test_inputs_fail_closed_on_legacy_rows_and_unbound_dependencies() -> None:
    """Legacy rows, unvalidated edges and loose caller authority all fail closed."""

    legacy = form_row("1ec0de000001", SURFACE)
    legacy["schema"] = "fusha/largelexicon/form-source@1"
    for name, kwargs in (
        ("legacy @1 form row", {"forms": [legacy]}),
        ("unvalidated typed edge", {"typed_edges": {LOC: [{"schema": "other"}]}}),
    ):
        try:
            make_inputs(**kwargs)
        except bridge.BridgeError as error:
            check(name + " fails closed", "failed closed" in str(error))
        else:
            raise AssertionError("FAILED: " + name + " was accepted")

    # Loose caller rows are no longer an accepted authority shape at all.
    try:
        bridge.BridgeInputs(crosswalk=[], lemmas=[], forms=[], stems=[], dependency_hashes={})
    except TypeError:
        pass
    else:
        raise AssertionError("FAILED: BridgeInputs accepted loose caller rows")
    try:
        bridge.BridgeInputs({"not": "a seal"})
    except bridge.BridgeError as error:
        check("a non-seal is refused", "SealedAuthority" in str(error))
    else:
        raise AssertionError("FAILED: a non-seal was accepted as authority")

def test_fact_id_is_content_addressed_over_the_claim() -> None:
    base = candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs()))[0]["fact_id"]

    def one(**kwargs):
        return candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs(**kwargs)))[0]["fact_id"]

    mutated_pos = form_row("1ec0de000001", SURFACE)
    mutated_pos["pos"] = "verb"
    check("POS change moves the fact id", one(forms=[mutated_pos]) != base)
    mutated_root = form_row("1ec0de000001", SURFACE)
    mutated_root.update({"root": "ا ل ه", "no_root_reason": None})
    check("root change moves the fact id", one(forms=[mutated_root]) != base)
    mutated_lemma = lemma_row("1ec0de000001", SURFACE)
    mutated_lemma["lemma"] = OTHER_SURFACE
    check("lemma change moves the fact id", one(lemmas=[mutated_lemma]) != base)
    check("stem change moves the fact id", one(stems=[]) != base)
    check("typed-edge change moves the fact id",
          one(typed_edges={LOC: [bridge.fixture_typed_edge("1ec0de000001", edge_type="form_entry_edge")]}) != base)

    check("carried-table content change moves the fact id",
          one(forms=[form_row("1ec0de000001", SURFACE), form_row("1ec0de000002", SURFACE, "001")])
          != base)
    # Digests are recomputed from content, so identity moves when CONTENT moves.
    wider_index = {LOC: SURFACE, "2:255:2": OTHER_SURFACE}
    check("canonical-index content change moves the fact id", one(loc_surface=wider_index) != base)
    lattice = {LOC: [{"loc": LOC, "entry_id": "1ec0de000009", "edge_type": "form", "relation": "linkage_only"}]}
    check("lexeme-lattice content change moves the fact id", one(graph_edges=lattice) != base)
    both_edges = {LOC: [bridge.fixture_typed_edge("1ec0de000001"),
                        bridge.fixture_typed_edge("1ec0de000001", edge_type="form_entry_edge")]}
    check("typed-graph content change moves the fact id", one(typed_edges=both_edges) != base)
    root_edge = {LOC: [{"loc": LOC, "entry_id": "1ec0de000001", "edge_type": "headword",
                        "relation": "root_confirms", "row_root": "ا ل ه"}]}
    check("root-family relation change moves the fact id", one(graph_edges=root_edge) != base)


def test_no_first_row_winner() -> None:
    forms = [form_row("1ec0de000001", SURFACE), form_row("1ec0de000002", SURFACE, "001")]
    record = bridge.bridge_row(crosswalk_row(), make_inputs(forms=forms, lemmas=[], stems=[]))
    flipped = bridge.bridge_row(crosswalk_row(), make_inputs(forms=list(reversed(forms)), lemmas=[], stems=[]))
    check("input order does not pick a winner", record["projection"]["status"] == "unresolved")
    check("reversed input order abstains identically", flipped["projection"]["status"] == "unresolved")
    check("the same candidate fact ids are preserved either way",
          sorted(f["fact_id"] for f in candidates_of(record))
          == sorted(f["fact_id"] for f in candidates_of(flipped)))


def test_unregistered_projector_fails() -> None:
    for unknown in ("largelexicon.not_registered.v1", "", "sarf.made_up.v9"):
        try:
            fact_projectors.REGISTRY.run(unknown, crosswalk_row=crosswalk_row(), inputs=make_inputs())
        except fact_projectors.ProjectorValidationError as error:
            check("unknown projector is refused", "unregistered projector" in str(error))
        else:
            raise AssertionError("FAILED: unregistered projector ran")
    try:
        fact_projectors.REGISTRY.contract("largelexicon.not_registered.v1")
    except fact_projectors.ProjectorValidationError:
        pass
    else:
        raise AssertionError("FAILED: unknown contract was returned")


def test_committed_fixtures_respect_the_public_boundary() -> None:
    directory = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "largelexicon-fact-bridge"
    text = (directory / "bridge-fixtures.jsonl").read_text(encoding="utf-8")
    committed = [json.loads(line) for line in text.splitlines() if line.strip()]
    check("committed fixtures are boundary-clean", bridge.public_fixture_errors(committed) == [])
    windows_path = "from C:" + chr(92) + "private"
    for name, mutate in (
        ("informed_by", lambda r: r[0]["facts"][0].update({"informed_by": ["qac"]})),
        ("gloss prose", lambda r: r[0]["facts"][0]["fact_value"].update({"gloss_text": "a copied gloss"})),
        ("ocr field", lambda r: r[0]["facts"][0]["fact_value"].update({"ocr_text": "scanned"})),
        ("external label", lambda r: r[0]["facts"][0]["evidence"].update({"summary": "checked against qac"})),
        ("url", lambda r: r[0]["facts"][0]["evidence"].update({"summary": "see https://example.test/x"})),
        ("absolute path", lambda r: r[0]["facts"][0]["evidence"].update({"summary": "from /srv/private/x"})),
        ("windows path", lambda r: r[0]["facts"][0]["evidence"].update({"summary": windows_path})),
    ):
        broken = copy.deepcopy(committed)
        mutate(broken)
        check(name + " is rejected in a public fixture", bridge.public_fixture_errors(broken) != [])


def test_full_output_may_not_target_a_tracked_path() -> None:
    check("default output is under out/", "out" in bridge.DEFAULT_OUTPUT.parts)
    check("materialization target is not a tracked path",
          bridge.MATERIALIZATION_TARGET["artifact"].startswith("out/"))
    try:
        bridge.main(["--limit", "1", "--out", "qamus/examples/largelexicon-fact-bridge/leak.jsonl"])
    except SystemExit as error:
        check("tracked output destination is refused", "gitignored out/" in str(error))
    else:
        raise AssertionError("FAILED: a tracked output destination was accepted")


# --------------------------------------------------------------------------- #
# defect-round-2 repairs
# --------------------------------------------------------------------------- #
def _expect_closed(name, build) -> None:
    try:
        build()
    except bridge.BridgeError as error:
        check(name + " fails closed", "failed closed" in str(error))
    else:
        raise AssertionError("FAILED: " + name + " was admitted")


def test_candidate_admission_requires_complete_authority() -> None:
    """Admission may never fail open when an authority is absent or unsealed."""

    _expect_closed("empty canonical loc index", lambda: make_inputs(loc_surface={}))
    _expect_closed("unvalidated typed edge", lambda: make_inputs(typed_edges={LOC: [{"schema": "x"}]}))
    _expect_closed("legacy denominator row",
                   lambda: make_inputs(denominator=[{"row_id": "x", "card_id": "y"}]))

    import inspect

    seal_params = set(inspect.signature(bridge.SealedAuthority.seal_fixture).parameters)
    forbidden = seal_params & {"binding", "bundles", "sha256", "path", "verified",
                               "dependency_hashes", "loc_surface_meta", "typed_graph_meta"}
    check("the seal accepts no caller binding, digest or path claim", not forbidden)

    binding = make_inputs().authority_binding()
    check("the seal marks itself verified only after recomputation", binding["verified"] is True)
    check("the seal records its origin", binding["origin"] == "fixture")
    check("the seal recomputes every carried-table digest",
          set(binding["carried_tables"]) == set(bridge.CARRIED_FAMILY_IDENTITY))
    for family, digest in binding["carried_tables"].items():
        check("carried digest for %s is a sha256" % family, len(digest) == 64)

def test_edge_map_key_must_agree_with_the_encoded_loc() -> None:
    """An edge filed under one loc whose node encodes another is a mis-binding."""

    mismatched = {LOC: [bridge.fixture_typed_edge("1ec0de000001", loc="9:9:9")]}
    _expect_closed("mismatched edge-map key", lambda: make_inputs(typed_edges=mismatched))
    check("edge-key disagreement is reported precisely",
          any("map key disagrees" in problem for problem in bridge._edge_key_errors(mismatched)))
    check("agreeing edge-map key is accepted",
          bridge._edge_key_errors({LOC: [bridge.fixture_typed_edge("1ec0de000001")]}) == [])


def test_authority_binding_is_carried_into_facts_and_scan() -> None:
    inputs = make_inputs()
    binding = inputs.authority_binding()
    check("binding names every authority",
          {"canonical_loc_index", "carried_tables", "lexeme_join_lattice", "typed_graph"} <= set(binding))
    check("the consumed authority object is verified", binding["verified"] is True)
    check("authority digest is a sha256", len(inputs.authority_digest()) == 64)
    fact = candidates_of(bridge.bridge_row(crosswalk_row(), inputs))[0]
    check("candidate binds the typed-graph digest",
          fact["fact_value"]["occurrence"]["canonical_quran_loc"] == LOC)
    scan = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "largelexicon-fact-bridge" / "real-data-scan.meta.json"
    if scan.exists():
        payload = json.loads(scan.read_text(encoding="utf-8"))
        upstream = payload["upstream_binding"]
        check("scan binds every authority", set(upstream["authorities"]) == set(binding))
        check("scan authority is verified", upstream["authorities"]["verified"] is True)
        for name in ("canonical_loc_index", "lexeme_join_lattice"):
            check(name + " is hashed into the scan",
                  len(str(upstream["authorities"][name]["content_sha256"])) == 64)
        check("scan carries an authority digest", len(str(upstream["authority_digest"])) == 64)


def test_abstention_ids_bind_semantics_and_provenance() -> None:
    """An abstention ID must move when its claim or its provenance moves."""

    def abstention(**kwargs) -> str:
        row = kwargs.pop("row", crosswalk_row())
        record = bridge.bridge_row(row, make_inputs(typed_edges={}, **kwargs))
        return record["facts"][0]["fact_id"]

    base = abstention()
    check("carried-table content moves the abstention id",
          abstention(stems=[]) != base)
    check("canonical-index content moves the abstention id",
          abstention(loc_surface={LOC: SURFACE, "2:255:2": OTHER_SURFACE}) != base)
    check("lexeme-lattice content moves the abstention id",
          abstention(graph_edges={LOC: [{"loc": LOC, "entry_id": "1ec0de000009", "edge_type": "form",
                                         "relation": "linkage_only"}]}) != base)
    graph = {LOC: [{"loc": LOC, "entry_id": "1ec0de000009", "edge_type": "form", "relation": "linkage_only"}]}
    check("blocker graph evidence moves the abstention id",
          abstention(forms=[], lemmas=[], stems=[], graph_edges=graph) != base)
    other_surface = crosswalk_row(visible_surface=OTHER_SURFACE)
    check("surface moves the abstention id", abstention(row=other_surface) != base)


def test_public_fixture_keys_are_checked_at_every_depth() -> None:
    probes = (
        {"nested": {"qac": True}},
        {"nested": {"tafsir": 1}},
        {"nested": {"informed_by": []}},
        {"a": {"b": {"https://example.test/x": 1}}},
        {"a": {"C:" + chr(92) + "private": 1}},
        {"a": {"/srv/private/x": 1}},
        {"deep": [{"more": {"ocr": "x"}}]},
    )
    for probe in probes:
        check("nested prohibited key is rejected: " + json.dumps(probe, ensure_ascii=False),
              bridge.public_fixture_errors(probe) != [])
    legitimate = {
        "schema": "qamus.typed_claim_contract.v1",
        "facts": [{"fact_type": "largelexicon_lexeme_candidate", "surface_spans": [{"role": "written_token"}]}],
        "projection": {"materialization_target": {"artifact": "out/largelexicon-fact-bridge/typed-claims.jsonl"}},
    }
    check("legitimate schema keys stay accepted", bridge.public_fixture_errors(legitimate) == [])


def test_projector_reports_the_enclosed_evidence_mode() -> None:
    result = fact_projectors.REGISTRY.run(
        fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID,
        crosswalk_row=crosswalk_row(),
        inputs=make_inputs(),
    )
    fact = [f for f in result["typed_claim_record"]["facts"]
            if f["fact_type"] == "largelexicon_lexeme_candidate"][0]
    check("wrapper evidence mode equals the enclosed fact's",
          result["candidate"]["evidence_mode"] == fact["evidence_mode"])
    check("wrapper does not relabel as normalized or certified",
          result["evidence_mode"] not in {"normalized_lexical_body", "certified"})
    check("enclosed fact is not relabelled", fact["evidence_mode"] == "direct_source_attestation")

    original = bridge.bridge_row

    def relabelled(row, inputs):
        record = original(row, inputs)
        for item in record["facts"]:
            if item["fact_type"] == "largelexicon_lexeme_candidate":
                item["evidence_mode"] = "normalized_lexical_body"
        return record

    bridge.bridge_row = relabelled
    try:
        mismatched = fact_projectors.REGISTRY.run(
            fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID,
            crosswalk_row=crosswalk_row(),
            inputs=make_inputs(),
        )
        check("a relabelled fact is reported as-is, never silently normalized",
              mismatched["candidate"]["evidence_mode"] == "normalized_lexical_body"
              and mismatched["typed_claim_record"]["facts"][0]["evidence_mode"] == "normalized_lexical_body")
    finally:
        bridge.bridge_row = original


def test_full_carried_table_output_refuses_tracked_paths() -> None:
    import promote_largelexicon_target_schema as promoter

    for name, destination in (
        ("tracked index path", promoter.ROOT / "qamus" / "indexes" / "tracked-probe"),
        ("repository root", promoter.ROOT),
        ("traversal escape", promoter.ROOT / "out" / ".." / "qamus"),
        ("absolute outside root", Path(promoter.ROOT.anchor) / "tmp" / "a3-probe"),
    ):
        for api in (
            lambda d: promoter.emit_carried(d, {}),
            lambda d: promoter.emit_ledgers(d, {"flagged": [], "quarantined": []}),
            promoter.assert_ignored_output_root,
        ):
            try:
                api(destination)
            except promoter.PromotionError as error:
                check(name + " is refused", "gitignored out/" in str(error))
            else:
                raise AssertionError("FAILED: " + name + " was accepted for full output")
    check("the authorized ignored root is accepted",
          promoter.assert_ignored_output_root(promoter.DEFAULT_CARRIED_DIR).is_relative_to(
              (promoter.ROOT / "out").resolve()))


# --------------------------------------------------------------------------- #
# defect-round-3 repairs: no forged or bypassed authority binding
# --------------------------------------------------------------------------- #
def test_forged_zero_bundle_metadata_is_refused() -> None:
    """Bundle counts are derived from the sealed edges; they cannot be declared."""

    import inspect

    params = set(inspect.signature(make_inputs).parameters)
    check("no typed_graph_meta parameter survives", "typed_graph_meta" not in params)

    edges = {LOC: [bridge.fixture_typed_edge("1ec0de000001")]}
    binding = make_inputs(typed_edges=edges).authority_binding()["typed_graph"]
    check("eligible edge count is derived", binding["eligible_edge_count"] == 1)
    check("eligible loc count is derived", binding["eligible_loc_count"] == 1)
    declared = sum(item["eligible_edge_count"] for item in binding["bundles"])
    check("bundle counts equal the sealed edge multiset", declared == 1)

    empty = make_inputs(typed_edges={}).authority_binding()["typed_graph"]
    check("an empty graph reports zero, not a forged count", empty["eligible_edge_count"] == 0)
    check("the two graph digests differ with content",
          binding["edge_content_sha256"] != empty["edge_content_sha256"])

def test_partial_dependency_family_is_refused() -> None:
    """Every carried family must be present and validated in the seal."""

    import inspect

    seal_params = inspect.signature(bridge.SealedAuthority.seal_fixture).parameters
    for family in ("crosswalk", "denominator", "forms", "lemmas", "stems"):
        check("the seal requires the %s family" % family, family in seal_params)
    binding = make_inputs().authority_binding()
    check("all five carried families are bound",
          set(binding["carried_tables"]) == set(bridge.CARRIED_FAMILY_IDENTITY))
    check("row counts are recorded per family",
          set(binding["carried_row_counts"]) == set(bridge.CARRIED_FAMILY_IDENTITY))

    # A family whose rows do not validate cannot be sealed at all.
    bad = form_row("1ec0de000001", SURFACE)
    bad["schema"] = "fusha/largelexicon/form-source@1"
    _expect_closed("legacy row in a carried family", lambda: make_inputs(forms=[bad]))

def test_no_validation_bypass_can_return_a_candidate() -> None:
    """Counterexample C: the old validate_rows=False escape hatch is gone."""

    import inspect

    signature = inspect.signature(bridge.BridgeInputs.__init__)
    check("BridgeInputs exposes no validation bypass flag", "validate_rows" not in signature.parameters)
    check("BridgeInputs is candidate capable", bridge.BridgeInputs.candidate_capable is True)
    check("DiagnosticInputs is structurally candidate incapable",
          bridge.DiagnosticInputs.candidate_capable is False)

    diagnostic = bridge.DiagnosticInputs(
        crosswalk=[],
        forms=[form_row("1ec0de000001", SURFACE)],
        typed_edges={LOC: [bridge.fixture_typed_edge("1ec0de000001")]},
        loc_surface={},
    )
    check("diagnostic construction records why it is unverified", diagnostic.input_errors != [])
    check("diagnostic authority is not verified", diagnostic.authority["verified"] is False)
    record = bridge.bridge_row(crosswalk_row(), diagnostic)
    assert_valid(record, "diagnostic abstention")
    check("diagnostic inputs emit no candidate", candidates_of(record) == [])
    check("diagnostic inputs abstain", record["projection"]["status"] == "blocked")
    check("diagnostic inputs name their blocker",
          blockers_of(record) == {"unverified_diagnostic_inputs"})

    result = fact_projectors.REGISTRY.run(
        fact_projectors.LARGELEXICON_BRIDGE_PROJECTOR_ID,
        crosswalk_row=crosswalk_row(),
        inputs=diagnostic,
    )
    check("the projector wrapper cannot return a candidate from diagnostic inputs",
          result["status"] == "abstained" and result["candidate"] is None)
    check("the diagnostic wrapper is not certification capable",
          result["certification_allowed"] is False and result["materialization_allowed"] is False)


def test_verified_authority_is_bound_into_ids_and_scan() -> None:
    inputs = make_inputs()
    binding = inputs.authority_binding()
    check("the consumed authority is verified", binding["verified"] is True)
    check("counts are derived, never asserted",
          binding["typed_graph"]["eligible_edge_count"] == 1)
    check("the complete carried family is bound",
          set(binding["carried_tables"]) == set(bridge.CARRIED_FAMILY_IDENTITY))

    base = candidates_of(bridge.bridge_row(crosswalk_row(), inputs))[0]["fact_id"]
    # Mutating any carried family's CONTENT moves the recomputed digest and the id.
    moved_forms = [form_row("1ec0de000001", SURFACE), form_row("1ec0de000002", SURFACE, "001")]
    other = candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs(forms=moved_forms)))
    check("carried-content change moves the fact id",
          all(fact["fact_id"] != base for fact in other))
    check("stem content change moves the fact id",
          candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs(stems=[])))[0]["fact_id"] != base)

    scan = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "largelexicon-fact-bridge" / "real-data-scan.meta.json"
    if scan.exists():
        payload = json.loads(scan.read_text(encoding="utf-8"))
        authorities = payload["upstream_binding"]["authorities"]
        check("the scan binds a verified authority", authorities["verified"] is True)
        check("the scan binds every carried family",
              set(authorities["carried_tables"]) == set(bridge.CARRIED_FAMILY_IDENTITY))
        check("the scan records a release-origin seal", authorities["origin"] == "release")

def test_carried_membership_binds_the_exact_row_body() -> None:
    """A detached or drifted row can never be bridged, whatever its row_id says."""

    detached = crosswalk_row()
    record = bridge.bridge_row(detached, make_inputs(crosswalk=[]))
    check("a detached row emits no candidate", candidates_of(record) == [])
    check("a detached row names the membership blocker",
          "row_not_in_validated_carried_authority" in blockers_of(record))

    authority = make_inputs()
    for label, mutate in (
        ("schema downgrade", lambda r: r.update({"schema": "qamus/largelexicon-qword-crosswalk@1"})),
        ("invented field", lambda r: r.update({"invented_field": "x"})),
        ("surface drift", lambda r: r.update({"visible_surface": OTHER_SURFACE})),
        ("match_status forgery", lambda r: r.update({"match_status": "forged"})),
        ("dependency swap", lambda r: r.update({"source_dependencies": [
            {"id": "llx-qword-0aae00000000-01-01-001", "kind": "qword_denominator_row"}]})),
    ):
        drifted = copy.deepcopy(crosswalk_row())
        mutate(drifted)
        record = bridge.bridge_row(drifted, authority)
        check("post-validation %s emits no candidate" % label, candidates_of(record) == [])
        check("post-validation %s is blocked" % label,
              record["projection"]["status"] in {"blocked", "source_gap", "unresolved", "producer_pending"})

    check("membership is body-addressed, not id-addressed",
          authority.carried_membership(crosswalk_row()) == "carried")
    check("an altered body loses membership",
          authority.carried_membership(crosswalk_row(usage_index=9))
          == "row_not_in_validated_carried_authority")
    check("a dispositioned row is named as such",
          make_inputs(crosswalk=[], non_carried_crosswalk=[crosswalk_row()])
          .carried_membership(crosswalk_row()) == "quarantined_or_flagged_source_row")

    import inspect
    check("bridge_row exposes no caller-defaulted carried trust path",
          "carried" not in inspect.signature(bridge.bridge_row).parameters)


def test_dependency_ids_bind_to_the_denominator_authority() -> None:
    """Correct kind labels with bogus ids must not admit a candidate."""

    bogus = crosswalk_row(source_dependencies=[
        {"id": "llx-qword-ffffffffffff-99-99-999", "kind": "qword_denominator_row"},
        {"id": "ffffffffffff:u9:e9", "kind": "source_card"},
    ])
    record = bridge.bridge_row(bogus, inputs_for(bogus))
    check("bogus dependency ids emit no candidate", candidates_of(record) == [])
    check("bogus dependency ids name the authority blocker",
          "dependency_id_not_in_authority" in blockers_of(record))

    wrong_card = crosswalk_row(source_dependencies=[
        {"id": "llx-qword-0aae00000000-01-01-001", "kind": "qword_denominator_row"},
        {"id": "0aae00000000:u9:e9", "kind": "source_card"},
    ])
    record = bridge.bridge_row(wrong_card, inputs_for(wrong_card))
    check("a source-card id that is not the denominator row's card is refused",
          "dependency_id_not_in_authority" in blockers_of(record))

    record = bridge.bridge_row(crosswalk_row(), make_inputs(denominator=[]))
    check("an absent denominator authority is an honest source gap",
          "source_card_authority_unavailable" in blockers_of(record))
    check("an absent denominator authority emits no candidate", candidates_of(record) == [])


def test_typed_edge_requires_reconstructible_content() -> None:
    """An accepted-looking edge without reconstructible content is not authority."""

    for label, mutate in (
        ("empty evidence", lambda e: e.update({"evidence": []})),
        ("missing evidence", lambda e: e.pop("evidence", None)),
        ("empty guards", lambda e: e.update({"guards": []})),
        ("missing guards", lambda e: e.pop("guards", None)),
        ("no producer", lambda e: e.pop("producer", None)),
        ("producer without version", lambda e: e.update({"producer": {"id": "x"}})),
        ("no edge id", lambda e: e.pop("edge_id", None)),
        ("edge id is not content-shaped", lambda e: e.update({"edge_id": "edge:not-the-content-hash"})),
        ("page context relation", lambda e: e.update({"edge_type": "page_context_entry_edge"})),
        ("root family relation", lambda e: e.update({"edge_type": "root_family_edge"})),
        ("candidate status", lambda e: e.update({"status": "candidate"})),
        ("no occurrence loc", lambda e: e.update({"from_node_id": "selected-word:x:s1:u1:f1:c2:255"})),
    ):
        edge = bridge.fixture_typed_edge("1ec0de000001")
        mutate(edge)
        check("hollow typed edge (%s) is structurally rejected" % label,
              bridge.typed_edge_errors(edge) != [])
        try:
            record = bridge.bridge_row(crosswalk_row(), make_inputs(typed_edges={LOC: [edge]}))
        except bridge.BridgeError:
            continue
        check("hollow typed edge (%s) emits no candidate" % label, candidates_of(record) == [])

    check("the content-bound fixture edge is accepted",
          bridge.typed_edge_errors(bridge.fixture_typed_edge("1ec0de000001")) == [])


def test_authority_digests_are_recomputed_not_trusted() -> None:
    """Digests are recomputed by the seal; there is nothing left to declare."""

    import inspect

    params = set(inspect.signature(make_inputs).parameters)
    for forbidden in ("loc_surface_meta", "lexeme_join_meta", "typed_graph_meta", "dependency_hashes"):
        check("no %s parameter survives" % forbidden, forbidden not in params)

    binding = make_inputs().authority_binding()
    check("the canonical index digest is recomputed",
          binding["canonical_loc_index"]["content_sha256"]
          == bridge._content_sha256({LOC: SURFACE}))
    check("the aggregate graph digest is derived from its parts",
          binding["typed_graph"]["typed_graph_sha256"] == bridge._content_sha256(
              {key: value for key, value in binding["typed_graph"].items()
               if key != "typed_graph_sha256"}))
    check("the authority digest covers the whole binding",
          binding["authority_sha256"] == bridge._content_sha256(
              {key: value for key, value in binding.items() if key != "authority_sha256"}))

    # Same-count content substitution changes the recomputed digest.
    drifted = make_inputs(loc_surface={LOC: OTHER_SURFACE}).authority_binding()
    check("same-count loc-surface drift moves the digest",
          drifted["canonical_loc_index"]["content_sha256"]
          != binding["canonical_loc_index"]["content_sha256"])
    check("same-count loc-surface drift moves the authority digest",
          drifted["authority_sha256"] != binding["authority_sha256"])

def test_canonical_loc_requires_positive_coordinates() -> None:
    check("0:0:0 is structurally impossible", not bridge.is_canonical_loc("0:0:0"))
    check("0:1:1 is structurally impossible", not bridge.is_canonical_loc("0:1:1"))
    check("2:255:0 is structurally impossible", not bridge.is_canonical_loc("2:255:0"))
    check("a real loc is structural", bridge.is_canonical_loc("2:255:1"))
    for bad in ("0:0:0", "999:999:999", "114:7:99"):
        row = crosswalk_row(canonical_quran_loc=bad, canonical_wbw_loc=bad)
        record = bridge.bridge_row(row, inputs_for(row))
        check("loc %s emits no candidate" % bad, candidates_of(record) == [])
        check("loc %s abstains precisely" % bad,
              blockers_of(record) & {"unresolved_canonical_loc", "loc_not_in_canonical_index"})


def test_certifier_refuses_never_auto_resolve_producer() -> None:
    """The authoritative store must refuse a real emitted bridge fact."""

    import tempfile
    from tools import certify_typed_fact as certifier

    fact = copy.deepcopy(candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs()))[0])
    tier, projector_id, basis = certifier.producing_projector_gate(fact)
    check("the producing projector resolves to never_auto_resolve", tier == "never_auto_resolve")
    check("resolution comes from repository authority, not the fact",
          basis in {"registered projector_id", "registered output_fact_type"})

    # Even with the projector_id stripped, the output fact type still resolves.
    stripped = copy.deepcopy(fact)
    stripped["rule_projector"] = dict(stripped["rule_projector"], projector_id="not.registered.v9")
    check("a renamed projector_id cannot shed the gate",
          certifier.producing_projector_gate(stripped)[0] == "never_auto_resolve")
    check("a claimed weaker tier on the fact is ignored", certifier.gate_refusal(fact) is not None)

    fact["dependent_projection_ids"] = ["llxbridge:probe:projection"]
    with tempfile.TemporaryDirectory() as tmp:
        store = certifier.TypedFactCertificationStore(Path(tmp))
        store.register(fact, contract_id="llxbridge-probe", actor="probe",
                       timestamp="2026-07-30T00:00:00Z")
        store.transition(fact["fact_id"], "review_required", actor="probe",
                         timestamp="2026-07-30T00:00:01Z", reason="probe")
        try:
            store.transition(fact["fact_id"], "certified", actor="probe",
                             timestamp="2026-07-30T00:00:02Z", reason="probe")
        except certifier.CertificationError as error:
            check("the authoritative store refuses certification",
                  "never_auto_resolve" in str(error))
        else:
            raise AssertionError("FAILED: a never_auto_resolve fact reached certified")


def test_duplicate_registration_cannot_weaken_a_gate() -> None:
    shadow = copy.deepcopy(fact_projectors.LARGELEXICON_BRIDGE_CONTRACT)
    shadow["projector_id"] = "largelexicon.duplicate_shadow.v1"
    shadow["gate_tier"] = "auto_safe"
    registry = fact_projectors.ProjectorRegistry()
    registry.register(copy.deepcopy(fact_projectors.LARGELEXICON_BRIDGE_CONTRACT),
                      fact_projectors.project_largelexicon_carried_lexeme)
    try:
        registry.register(shadow, fact_projectors.project_largelexicon_carried_lexeme)
    except fact_projectors.ProjectorValidationError as error:
        check("a conflicting gate re-registration is refused", "ambiguous" in str(error))
    else:
        raise AssertionError("FAILED: a duplicate projector claimed the output at a weaker gate")
    check("the strictest registered gate is reported",
          fact_projectors.REGISTRY.gate_tier_for_output_fact_type("largelexicon_lexeme_candidate")
          == "never_auto_resolve")
    check("sibling producers at the same tier remain legal",
          fact_projectors.REGISTRY.gate_tier_for_output_fact_type("formation_evidence")
          == "two_vote_required")


def test_target_reader_import_and_custom_target_isolation() -> None:
    import subprocess
    import tempfile
    from tools.largelexicon_table_reader import LargelexiconTargetTables

    repo_root = Path(__file__).resolve().parents[1]
    code = ("import sys; sys.path.insert(0, r'%s');\n"
            "from tools.largelexicon_table_reader import LargelexiconTargetTables;\n"
            "print('IMPORT_OK')\n" % str(repo_root))
    proc = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(repo_root.parent),
                          capture_output=True, text=True)
    check("the package imports from the repository parent (%s)" % proc.stderr.strip()[-90:],
          "IMPORT_OK" in proc.stdout)

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "target-schema"
        target.mkdir(parents=True)
        real = repo_root / "qamus" / "indexes" / "largelexicon" / "target-schema" / "TARGET-RELEASE.json"
        release = json.loads(real.read_text(encoding="utf-8"))
        release["tables"]["lemma-source"]["carried_sha256"] = "0" * 64
        (target / "TARGET-RELEASE.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tables = LargelexiconTargetTables.open(target_dir=target)
        check("the reader retains the exact validated target dir",
              tables.target_dir is not None and Path(tables.target_dir).resolve() == target.resolve())
        try:
            tables.carried("lemma-source")
        except Exception as error:  # noqa: BLE001
            check("carried() reads the retained release, not the default one",
                  "lemma-source" in str(error) or "carried" in str(error))
        else:
            raise AssertionError("FAILED: carried() silently read the default release")

    default_tables = LargelexiconTargetTables.open()
    check("the default reader keeps target_dir unset", default_tables.target_dir is None)


# --------------------------------------------------------------------------- #
# defect-round-6 repairs: sealed authority, exact identity, bound certifier
# --------------------------------------------------------------------------- #
def _emitted_candidates(build) -> list:
    try:
        record = build()
    except bridge.BridgeError:
        return []
    return candidates_of(record)


def _a_candidate_fact() -> dict:
    return copy.deepcopy(candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs()))[0])


def _try_certify(fact: dict, *, bundle=None) -> str:
    import tempfile
    from tools import certify_typed_fact as certifier

    with tempfile.TemporaryDirectory() as tmp:
        store = certifier.TypedFactCertificationStore(Path(tmp))
        try:
            store.register(fact, contract_id="round6", actor="t", timestamp="2026-07-30T00:00:00Z")
            store.transition(fact["fact_id"], "review_required", actor="t",
                             timestamp="2026-07-30T00:00:01Z", reason="t")
            store.transition(fact["fact_id"], "certified", actor="t",
                             timestamp="2026-07-30T00:00:02Z", reason="t", two_vote_bundle=bundle)
        except certifier.CertificationError as error:
            return str(error)
        return "CERTIFIED"


def test_projector_identity_cannot_shed_a_fact_type_gate() -> None:
    """A known projector id with a mismatched output fact type must never certify."""

    from tools import certify_typed_fact as certifier

    base = _a_candidate_fact()
    for projector_id in ("sarf.documented_form.v1", "nahw.particle_function.v1"):
        fact = copy.deepcopy(base)
        fact["rule_projector"] = dict(fact["rule_projector"], projector_id=projector_id)
        fact["dependent_projection_ids"] = ["llxbridge:test:projection"]
        outcome = _try_certify(fact)
        check("substituting %s does not certify" % projector_id, outcome != "CERTIFIED")

        # The gate resolution itself must not select the substituted projector's tier.
        probe = copy.deepcopy(base)
        probe["rule_projector"] = dict(probe["rule_projector"], projector_id=projector_id)
        tier, _pid, basis = certifier.producing_projector_gate(probe)
        check("%s is reported as a projector/fact_type mismatch" % projector_id,
              basis.startswith("projector/fact_type mismatch"))
        check("%s still resolves the fact-type gate" % projector_id, tier == "never_auto_resolve")
        check("%s is refused by the gate" % projector_id, certifier.gate_refusal(probe) is not None)


def test_registry_two_vote_gate_requires_a_bundle() -> None:
    """A registry-resolved two_vote_required gate demands a canonical bundle."""

    from tools import certify_typed_fact as certifier

    fact = _a_candidate_fact()
    fact["fact_type"] = "particle_function"
    fact["rule_projector"] = dict(fact["rule_projector"], projector_id="nahw.particle_function.v1")
    fact["producer"] = {"id": "tools/other_producer.py", "version": "1.0.0"}
    fact["dependent_projection_ids"] = ["llxbridge:test:projection"]
    fact["fact_id"] = "sha256:" + "3" * 64
    tier, _pid, _basis = certifier.producing_projector_gate(fact)
    check("the registry resolves two_vote_required", tier == "two_vote_required")
    outcome = _try_certify(fact)
    check("a registry two_vote gate without a bundle does not certify", outcome != "CERTIFIED")
    check("the refusal names the missing bundle",
          "two-vote" in outcome or "two_vote" in outcome)


def test_stale_content_addressed_fact_id_is_refused() -> None:
    """Relabelling projector, fact type or claim may not retain the original id."""

    base = _a_candidate_fact()
    check("the emitted id is recomputable", bridge.recompute_fact_id(base) == base["fact_id"])
    for label, mutate in (
        ("fact type", lambda f: f.update({"fact_type": "formation_evidence"})),
        ("projector", lambda f: f.update({"rule_projector": dict(
            f["rule_projector"], projector_id="sarf.fam2.lexical_formation.v1")})),
        ("semantic claim", lambda f: f.update({"fact_value": dict(
            f["fact_value"], relabelled_semantic_claim=True)})),
    ):
        fact = copy.deepcopy(base)
        original = fact["fact_id"]
        mutate(fact)
        fact["fact_id"] = original
        check("a relabelled %s no longer recomputes to the stale id" % label,
              bridge.recompute_fact_id(fact) != original)
        outcome = _try_certify(fact)
        check("a stale id for a relabelled %s is refused" % label, outcome != "CERTIFIED")
        check("the refusal names the identity mismatch for %s" % label,
              "content-addressed fact id" in outcome)


def test_same_type_projector_gate_cannot_be_weakened() -> None:
    shadow = copy.deepcopy(fact_projectors.LARGELEXICON_BRIDGE_CONTRACT)
    shadow["projector_id"] = "largelexicon.same_type_shadow.v1"
    shadow["gate_tier"] = "auto_safe"
    registry = fact_projectors.ProjectorRegistry()
    registry.register(copy.deepcopy(fact_projectors.LARGELEXICON_BRIDGE_CONTRACT),
                      fact_projectors.project_largelexicon_carried_lexeme)
    try:
        registry.register(shadow, fact_projectors.project_largelexicon_carried_lexeme)
    except fact_projectors.ProjectorValidationError as error:
        check("a same-type weaker gate is refused", "ambiguous" in str(error))
    else:
        raise AssertionError("FAILED: a same-type projector weakened the gate")
    check("the live registry still reports the strict gate",
          fact_projectors.REGISTRY.gate_tier_for_output_fact_type("largelexicon_lexeme_candidate")
          == "never_auto_resolve")


def test_authority_is_sealed_not_caller_declared() -> None:
    """Only a seal is authority; loose rows and direct construction are refused."""

    try:
        bridge.BridgeInputs({"verified": True, "carried_tables": {}})
    except bridge.BridgeError as error:
        check("a caller-shaped authority dict is refused", "SealedAuthority" in str(error))
    else:
        raise AssertionError("FAILED: a caller dict was accepted as authority")

    try:
        bridge.SealedAuthority(object(), origin="forged", families={}, loc_surface={},
                               typed_edges={}, lexeme_join={}, bundles=[], non_carried_crosswalk=[])
    except bridge.BridgeError as error:
        check("a seal cannot be forged directly", "may only be produced" in str(error))
    else:
        raise AssertionError("FAILED: a SealedAuthority was forged directly")

    seal = make_inputs().authority_seal
    check("the fixture seal names its origin", seal.origin == "fixture")
    check("the release seal is a distinct factory",
          hasattr(bridge.SealedAuthority, "from_release"))
    binding = seal.binding
    check("verified is set by the seal, not by a caller", binding["verified"] is True)
    check("the authority digest covers the binding",
          binding["authority_sha256"] == bridge._content_sha256(
              {k: v for k, v in binding.items() if k != "authority_sha256"}))


def test_duplicate_identities_are_refused_in_every_family() -> None:
    """Conflicting duplicate bodies must never become authority."""

    row_a = crosswalk_row()
    row_b = crosswalk_row(visible_surface=OTHER_SURFACE)  # same row_id, different body
    _expect_closed("two crosswalk bodies under one row_id",
                   lambda: make_inputs(crosswalk=[row_a, row_b]))

    form_a = form_row("1ec0de000001", SURFACE)
    form_b = form_row("1ec0de000001", SURFACE)
    form_b["pos"] = "verb"
    _expect_closed("two form bodies under one form_id", lambda: make_inputs(forms=[form_a, form_b]))

    lemma_a = lemma_row("1ec0de000001", SURFACE)
    lemma_b = lemma_row("1ec0de000001", OTHER_SURFACE)
    _expect_closed("two lemma bodies under one entry_id", lambda: make_inputs(lemmas=[lemma_a, lemma_b]))

    stem_a = stem_row("1ec0de000001", SURFACE)
    stem_b = copy.deepcopy(stem_a)
    stem_b["gloss_hint"] = "a conflicting gloss"
    _expect_closed("two stem bodies under one stem_id", lambda: make_inputs(stems=[stem_a, stem_b]))

    den_a = bridge.fixture_denominator_row()
    den_b = bridge.fixture_denominator_row(quran_ref="9:9")
    _expect_closed("two denominator bodies under one row_id",
                   lambda: make_inputs(denominator=[den_a, den_b]))

    # An exact duplicate is also refused: an authority set has one row per identity.
    _expect_closed("an exactly duplicated crosswalk row",
                   lambda: make_inputs(crosswalk=[row_a, copy.deepcopy(row_a)]))

    # Distinct surviving analyses under ONE entry id remain unresolved, never merged.
    twins = [form_row("1ec0de000001", SURFACE), form_row("1ec0de000001", SURFACE, "001")]
    record = bridge.bridge_row(crosswalk_row(), make_inputs(forms=twins, lemmas=[], stems=[]))
    check("same-entry rivals do not silently collapse to a blocker-free candidate",
          record["projection"]["status"] != "candidate" or blockers_of(record))


def test_invented_denominator_cannot_be_source_card_authority() -> None:
    _expect_closed("a two-field invented denominator",
                   lambda: make_inputs(denominator=[{"row_id": "llx-qword-0aae00000000-01-01-001",
                                                     "card_id": "0aae00000000:u1:e1"}]))
    _expect_closed("a legacy @1 denominator row",
                   lambda: make_inputs(denominator=[dict(bridge.fixture_denominator_row(),
                                                         schema="qamus/largelexicon-qword-denominator@1")]))


def test_repository_metadata_binds_the_exact_parsed_content() -> None:
    """Loaders return content and binding together; they cannot be paired by a caller."""

    import inspect

    params = set(inspect.signature(make_inputs).parameters)
    for forbidden in ("loc_surface_meta", "lexeme_join_meta", "typed_graph_meta", "dependency_hashes"):
        check("no %s parameter exists on the sealed path" % forbidden, forbidden not in params)
    seal_params = set(inspect.signature(bridge.SealedAuthority.seal_fixture).parameters)
    for forbidden in ("binding", "bundles", "sha256", "path"):
        check("the seal accepts no %s claim" % forbidden, forbidden not in seal_params)

    edges, bundles = bridge._load_typed_graph_sealed()
    declared = sum(item["eligible_edge_count"] for item in bundles)
    actual = sum(len(items) for items in edges.values())
    check("the sealed bundle count equals the parsed edge multiset", declared == actual)
    for bundle in bundles:
        if bundle["present"]:
            path = Path(__file__).resolve().parents[1] / bundle["path"]
            import hashlib
            check("bundle %s digest is the file digest" % bundle["path"],
                  bundle["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest())

    binding = make_inputs().authority_binding()
    check("the aggregate graph digest is derived, not supplied",
          binding["typed_graph"]["typed_graph_sha256"] == bridge._content_sha256(
              {k: v for k, v in binding["typed_graph"].items() if k != "typed_graph_sha256"}))
    check("same-count loc-surface substitution changes the digest",
          make_inputs(loc_surface={LOC: OTHER_SURFACE}).authority_binding()["canonical_loc_index"]["content_sha256"]
          != binding["canonical_loc_index"]["content_sha256"])


def test_typed_edge_identity_and_endpoints_are_exact() -> None:
    good = bridge.fixture_typed_edge("1ec0de000001")
    check("the fixture edge id is the canonical derivation",
          good["edge_id"] == bridge.canonical_edge_id(
              {k: v for k, v in good.items() if k != "edge_id"}))

    stale = copy.deepcopy(good)
    stale["details"] = dict(stale["details"], mutated=True)
    check("a stale well-shaped edge id is rejected", bridge.typed_edge_errors(stale) != [])

    zeroed = copy.deepcopy(good)
    zeroed["edge_id"] = "edge:" + "0" * 24
    check("an all-zero well-shaped edge id is rejected", bridge.typed_edge_errors(zeroed) != [])

    for label, node_type, node_id in (
        ("card declaring a selected-word node", "card", good["from_node_id"]),
        ("selected-word declaring a card node", "selected-word", "card:0aae00000000:u1:x1:o2:255:1"),
        ("appearance node", "appearance", good["from_node_id"]),
    ):
        edge = copy.deepcopy(good)
        edge["from_node_type"] = node_type
        edge["from_node_id"] = node_id
        edge["edge_id"] = bridge.canonical_edge_id({k: v for k, v in edge.items() if k != "edge_id"})
        check("endpoint mismatch (%s) is rejected" % label, bridge.typed_edge_errors(edge) != [])

    twin = bridge.fixture_typed_edge("1ec0de000002")
    twin["edge_id"] = good["edge_id"]
    _expect_closed("two edges sharing one edge id",
                   lambda: make_inputs(typed_edges={LOC: [good, twin]}))
    _expect_closed("an exactly duplicated edge",
                   lambda: make_inputs(typed_edges={LOC: [good, copy.deepcopy(good)]}))


def test_reader_boundary_is_stable() -> None:
    """One module identity, and a relative target dir resolved at open time."""

    import importlib
    import os
    import tempfile

    flat = importlib.import_module("largelexicon_table_reader")
    packaged = importlib.import_module("tools.largelexicon_table_reader")
    check("the reader has one module identity", flat is packaged)
    check("the reader has one class identity",
          flat.LargelexiconTargetTables is packaged.LargelexiconTargetTables)

    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        target = base / "target-schema"
        target.mkdir(parents=True)
        real = repo_root / "qamus" / "indexes" / "largelexicon" / "target-schema" / "TARGET-RELEASE.json"
        release = json.loads(real.read_text(encoding="utf-8"))
        release["tables"]["lemma-source"]["carried_sha256"] = "0" * 64
        (target / "TARGET-RELEASE.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cwd = os.getcwd()
        try:
            os.chdir(base)
            tables = packaged.LargelexiconTargetTables.open(target_dir=Path("target-schema"))
        finally:
            os.chdir(cwd)
        retained = Path(tables.target_dir)
        check("a relative target dir is retained absolutely", retained.is_absolute())
        check("the retained dir is the one that was validated",
              retained.resolve() == target.resolve())
        try:
            tables.carried("lemma-source")
        except Exception as error:  # noqa: BLE001
            check("carried() reads the retained release, never the default",
                  "lemma-source" in str(error) or "carried" in str(error))
        else:
            raise AssertionError("FAILED: carried() fell back to the default release")

    default_tables = packaged.LargelexiconTargetTables.open()
    check("the default reader keeps target_dir unset", default_tables.target_dir is None)


if __name__ == "__main__":
    raise SystemExit(main())
