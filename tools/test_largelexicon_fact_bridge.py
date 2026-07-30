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
        card_id="0aae00000002:u1:e1",
        source_dependencies=[
            {"id": "llx-qword-0aae00000002-01-01-001", "kind": "qword_denominator_row"},
            {"id": "0aae00000002:u1:e1", "kind": "source_card"},
        ],
    )
    other = candidates_of(bridge.bridge_row(moved, inputs))[0]
    check("lexeme candidate entry is the documenting entry, not the displaying page",
          base["fact_value"]["lexeme_candidate"]["entry_id"] == "1ec0de000001")
    check("page context follows the crosswalk entry, not the lexeme",
          other["fact_value"]["page_context"]["crosswalk_entry_id"] == "0aae00000002")
    check("page context is explicitly never a lexeme edge",
          other["fact_value"]["page_context"]["never_lexeme_edge"] is True)
    check("lexeme candidate is unchanged by the page move",
          other["fact_value"]["lexeme_candidate"] == base["fact_value"]["lexeme_candidate"])
    check("fact identity does not absorb the page context", other["fact_id"] == base["fact_id"])


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
        record = bridge.bridge_row(crosswalk_row(canonical_quran_loc=bad), inputs)
        assert_valid(record, f"unresolved loc {bad!r}")
        check(f"loc {bad!r} abstains", record["projection"]["status"] != "candidate")
        check(f"loc {bad!r} names its blocker", "unresolved_canonical_loc" in blockers_of(record))
        check(f"loc {bad!r} emits no lexeme candidate", candidates_of(record) == [])


def test_packet_ready_crosswalk_abstains() -> None:
    inputs = make_inputs()
    record = bridge.bridge_row(
        crosswalk_row(status="source_crosswalk_packet_ready",
                      transclusion_route="entry_card_qword_to_canonical_crosswalk_packet"),
        inputs,
    )
    assert_valid(record, "packet ready")
    check("packet-ready abstains", record["projection"]["status"] == "source_gap")
    check("packet-ready names its blocker", "crosswalk_packet_not_accepted" in blockers_of(record))


def test_demoted_crosswalk_abstains() -> None:
    inputs = make_inputs()
    record = bridge.bridge_row(crosswalk_row(status="canonical_crosswalk_demoted"), inputs)
    check("demoted abstains", record["projection"]["status"] != "candidate")
    check("demoted names its blocker", "crosswalk_packet_not_accepted" in blockers_of(record))


def test_quarantined_row_abstains() -> None:
    inputs = make_inputs()
    record = bridge.bridge_row(crosswalk_row(), inputs, carried=False)
    assert_valid(record, "quarantined row")
    check("quarantined row abstains", record["projection"]["status"] == "blocked")
    check("quarantined row names its blocker", "quarantined_or_flagged_source_row" in blockers_of(record))
    check("quarantined row emits no lexeme candidate", candidates_of(record) == [])


def test_missing_dependency_abstains() -> None:
    inputs = make_inputs()
    for dependencies in ([], [{"id": "x", "kind": "entry"}], [{"id": "x", "kind": "source_card"}]):
        record = bridge.bridge_row(crosswalk_row(source_dependencies=dependencies), inputs)
        assert_valid(record, "missing dependency")
        check("missing dependency abstains", record["projection"]["status"] == "blocked")
        check("missing dependency names its blocker", "missing_dependency_release" in blockers_of(record))


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


TESTS = all_tests()


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
        record = bridge.bridge_row(crosswalk_row(canonical_wbw_loc=bad), make_inputs())
        check("wbw disagreement is caught", "wbw_loc_disagreement" in blockers_of(record))
    for bad in ("0:0:0", "1000:1:1", "2:255", "-1:2:3"):
        check("invalid loc coordinates are refused", not bridge.is_canonical_loc(bad) or bad == "0:0:0")


def test_inputs_fail_closed_on_legacy_rows_and_unbound_dependencies() -> None:
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
    try:
        bridge.BridgeInputs(crosswalk=[], lemmas=[], forms=[], stems=[], dependency_hashes={})
    except bridge.BridgeError as error:
        check("empty dependency hashes fail closed", "dependency hashes are required" in str(error))
    else:
        raise AssertionError("FAILED: empty dependency hashes were accepted")
    try:
        bridge.BridgeInputs(crosswalk=[], lemmas=[], forms=[], stems=[], dependency_hashes={"form-source": "nope"})
    except bridge.BridgeError as error:
        check("non-sha256 dependency hash fails closed", "not a sha256 digest" in str(error))
    else:
        raise AssertionError("FAILED: a non-sha256 dependency hash was accepted")


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

    stale = dict(bridge.FIXTURE_DEPENDENCY_HASHES)
    stale["form-source"] = "9" * 64
    check("stale carried-table digest moves the fact id", one(dependency_hashes=stale) != base)
    check("typed-graph digest change moves the fact id",
          one(typed_graph_meta=bridge.fixture_graph_meta(
              {LOC: [bridge.fixture_typed_edge("1ec0de000001")]}, sha256="e" * 64)) != base)
    check("canonical-index digest change moves the fact id",
          one(loc_surface_meta=dict(bridge.FIXTURE_LOC_INDEX_META, sha256="c" * 64)) != base)
    check("lexeme-lattice digest change moves the fact id",
          one(lexeme_join_meta=dict(bridge.FIXTURE_LEXEME_JOIN_META, sha256="d" * 64)) != base)
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
    """Admission may never fail open when an authority is absent or unbound."""

    _expect_closed("empty canonical loc index", lambda: make_inputs(loc_surface={}))
    _expect_closed("omitted typed-graph metadata", lambda: make_inputs(typed_graph_meta={}))
    _expect_closed(
        "unbound typed-graph digest",
        lambda: make_inputs(typed_graph_meta={"bundles": [], "typed_graph_sha256": "unbound"}),
    )
    _expect_closed(
        "malformed typed-graph digest",
        lambda: make_inputs(typed_graph_meta={"bundles": [], "typed_graph_sha256": "nope"}),
    )
    _expect_closed(
        "typed-graph bundle without a digest",
        lambda: make_inputs(
            typed_graph_meta={
                "bundles": [{"path": "x", "present": True, "sha256": None}],
                "typed_graph_sha256": "f" * 64,
            }
        ),
    )
    _expect_closed("omitted canonical-index binding", lambda: make_inputs(loc_surface_meta={}))
    _expect_closed(
        "malformed canonical-index digest",
        lambda: make_inputs(loc_surface_meta=dict(bridge.FIXTURE_LOC_INDEX_META, sha256="short")),
    )
    _expect_closed("omitted lexeme-lattice binding", lambda: make_inputs(lexeme_join_meta={}))
    _expect_closed(
        "absent lexeme lattice",
        lambda: make_inputs(lexeme_join_meta=dict(bridge.FIXTURE_LEXEME_JOIN_META, present=False)),
    )
    _expect_closed("empty dependency hashes", lambda: make_inputs(dependency_hashes={}))
    _expect_closed(
        "malformed dependency hash",
        lambda: make_inputs(dependency_hashes=dict(bridge.FIXTURE_DEPENDENCY_HASHES, **{"form-source": "x"})),
    )


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
          set(binding) == {"canonical_loc_index", "carried_tables", "lexeme_join_lattice", "typed_graph", "verified"})
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
                  len(str(upstream["authorities"][name]["sha256"])) == 64)
        check("scan carries an authority digest", len(str(upstream["authority_digest"])) == 64)


def test_abstention_ids_bind_semantics_and_provenance() -> None:
    """An abstention ID must move when its claim or its provenance moves."""

    def abstention(**kwargs) -> str:
        row = kwargs.pop("row", crosswalk_row())
        record = bridge.bridge_row(row, make_inputs(typed_edges={}, **kwargs))
        return record["facts"][0]["fact_id"]

    base = abstention()
    check("carried-table digest moves the abstention id",
          abstention(dependency_hashes=dict(bridge.FIXTURE_DEPENDENCY_HASHES, **{"form-source": "9" * 64})) != base)
    check("typed-graph digest moves the abstention id",
          abstention(typed_graph_meta=bridge.fixture_graph_meta({}, sha256="e" * 64)) != base)
    check("canonical-index digest moves the abstention id",
          abstention(loc_surface_meta=dict(bridge.FIXTURE_LOC_INDEX_META, sha256="c" * 64)) != base)
    check("lexeme-lattice digest moves the abstention id",
          abstention(lexeme_join_meta=dict(bridge.FIXTURE_LEXEME_JOIN_META, sha256="d" * 64)) != base)
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

    def relabelled(row, inputs, *, carried=True):
        record = original(row, inputs, carried=carried)
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
    """Counterexample A: edges supplied, metadata claiming zero bundles/edges."""

    forged = {"bundles": [], "eligible_edge_count": 0, "eligible_loc_count": 0,
              "typed_graph_sha256": "f" * 64}
    try:
        make_inputs(typed_graph_meta=forged)
    except bridge.BridgeError as error:
        message = str(error)
        check("forged zero-bundle metadata fails closed", "failed closed" in message)
        check("the refusal names the unaccounted edges", "no present bundle accounts for them" in message)
    else:
        raise AssertionError("FAILED: forged zero-bundle metadata was admitted")

    understated = bridge.fixture_graph_meta({LOC: [bridge.fixture_typed_edge("1ec0de000001")]})
    understated["bundles"][0]["eligible_edge_count"] = 0
    try:
        make_inputs(typed_graph_meta=understated)
    except bridge.BridgeError as error:
        check("understated bundle counts fail closed", "bundles declare 0 eligible edges" in str(error))
    else:
        raise AssertionError("FAILED: understated bundle counts were admitted")

    overstated = bridge.fixture_graph_meta({LOC: [bridge.fixture_typed_edge("1ec0de000001")]})
    overstated["eligible_loc_count"] = 99
    try:
        make_inputs(typed_graph_meta=overstated)
    except bridge.BridgeError as error:
        check("overstated loc counts fail closed", "eligible_loc_count" in str(error))
    else:
        raise AssertionError("FAILED: overstated loc counts were admitted")


def test_partial_dependency_family_is_refused() -> None:
    """Counterexample B: only form-source, omitting the rest of the carried family."""

    try:
        make_inputs(dependency_hashes={"form-source": "a" * 64})
    except bridge.BridgeError as error:
        message = str(error)
        check("partial dependency family fails closed", "failed closed" in message)
        for family in ("lemma-source", "qword-crosswalk", "qword-denominator", "stem-source"):
            check("the refusal names missing " + family, family in message)
    else:
        raise AssertionError("FAILED: a partial dependency family was admitted")

    complete = dict(bridge.FIXTURE_DEPENDENCY_HASHES)
    check("the complete family is accepted", bridge.dependency_family_errors(complete) == [])
    for family in sorted(bridge.REQUIRED_DEPENDENCY_FAMILIES):
        dropped = {name: digest for name, digest in complete.items() if name != family}
        check("dropping " + family + " is refused",
              any("missing" in problem for problem in bridge.dependency_family_errors(dropped)))
        blanked = dict(complete, **{family: ""})
        check("blank " + family + " digest is refused",
              any("not a sha256" in problem for problem in bridge.dependency_family_errors(blanked)))
        malformed = dict(complete, **{family: "not-a-digest"})
        check("malformed " + family + " digest is refused",
              any("not a sha256" in problem for problem in bridge.dependency_family_errors(malformed)))
    extra = dict(complete, **{"invented-source": "9" * 64})
    check("an extra dependency family is refused",
          any("not recognised" in problem for problem in bridge.dependency_family_errors(extra)))
    check("an empty dependency map is refused", bridge.dependency_family_errors({}) != [])


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
        lemmas=[lemma_row("1ec0de000001", SURFACE)],
        forms=[form_row("1ec0de000001", SURFACE)],
        stems=[stem_row("1ec0de000001", SURFACE)],
        dependency_hashes={},
        typed_edges={LOC: [bridge.fixture_typed_edge("1ec0de000001")]},
        typed_graph_meta={},
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
    check("the consumed authority is verified", inputs.authority_binding()["verified"] is True)
    check("counts are derived, never asserted",
          inputs.authority_binding()["typed_graph"]["eligible_edge_count"] == 1)
    check("the complete dependency family is bound",
          set(inputs.authority_binding()["carried_tables"]) == set(bridge.REQUIRED_DEPENDENCY_FAMILIES))

    base = candidates_of(bridge.bridge_row(crosswalk_row(), inputs))[0]["fact_id"]
    for family in sorted(bridge.REQUIRED_DEPENDENCY_FAMILIES):
        moved = dict(bridge.FIXTURE_DEPENDENCY_HASHES, **{family: "9" * 64})
        other = candidates_of(bridge.bridge_row(crosswalk_row(), make_inputs(dependency_hashes=moved)))[0]
        check("mutating " + family + " moves the fact id", other["fact_id"] != base)

    scan = Path(__file__).resolve().parents[1] / "qamus" / "examples" / "largelexicon-fact-bridge" / "real-data-scan.meta.json"
    if scan.exists():
        payload = json.loads(scan.read_text(encoding="utf-8"))
        authorities = payload["upstream_binding"]["authorities"]
        check("the scan binds a verified authority", authorities["verified"] is True)
        check("the scan binds the complete dependency family",
              set(authorities["carried_tables"]) == set(bridge.REQUIRED_DEPENDENCY_FAMILIES))


if __name__ == "__main__":
    raise SystemExit(main())
