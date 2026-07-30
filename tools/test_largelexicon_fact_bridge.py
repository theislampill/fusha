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
    drifted = bridge.BridgeInputs(
        crosswalk=[], lemmas=[lemma_row("1ec0de000001", SURFACE)], forms=[form_row("1ec0de000001", SURFACE)],
        stems=[stem_row("1ec0de000001", SURFACE)], dependency_hashes=stale,
        typed_edges={LOC: [bridge.fixture_typed_edge("1ec0de000001")]},
        typed_graph_meta={"bundles": [], "typed_graph_sha256": "f" * 64},
        loc_surface={LOC: SURFACE},
    )
    check("stale dependency digest moves the fact id",
          candidates_of(bridge.bridge_row(crosswalk_row(), drifted))[0]["fact_id"] != base)


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


if __name__ == "__main__":
    raise SystemExit(main())
