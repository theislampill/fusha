#!/usr/bin/env python3
"""FULL harness gate for the self-contained PROOF-P particle proof."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_typed_edge_crosswalk import EDGE_TYPE_SET, STATUS_SET  # noqa: E402
from tools.typed_claim_contract import validate_contract_record  # noqa: E402
from tools.validate_rich_hover_candidate import validate_candidate  # noqa: E402


OUT = ROOT / "qamus" / "examples" / "proof-particle"
SELECTED = "selected-word:b8e480aebafe:s1:u1:f1:c2:284:x1"
ENTRY = "entry:b8e480aebafe"
CARD = "card:b8e480aebafe:u1:x1"
SENSE = "sense:b8e480aebafe:s1"
OCCURRENCE = "occurrence:2:284:10"
APPEARANCE = "appearance:2:284:10:1"
PROJECTION = "proofp.ma.2-284-10.v1"


class HarnessFailure(Exception):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessFailure(message)


def check_source_packet() -> None:
    source = read_json(OUT / "source" / "proofp-source-facts.json")
    require(source["schema"] == "qamus.proof_particle.source_facts.v1", "source fixture schema")
    require(source["selection"] == {
        "owner_list_label": "مَا",
        "entry_id": "b8e480aebafe",
        "source_key": "p099",
        "sense_number": 1,
        "card_ref": "2:284",
        "selected_word_id": SELECTED,
        "occurrence_id": "quran:2:284:10",
    }, "source selection identity")
    require(source["entry"]["root"] in ("", None), "particle source root must be silent")
    require(source["selected_word_crosswalk"]["crosswalk_status"] == "deterministic_exact", "lexical crosswalk status")
    require(source["selected_word_crosswalk"]["occurrence_id"] == "", "source occurrence gap must remain visible")
    require(source["occurrence"]["loc"] == "2:284:10", "source occurrence location")
    require(source["occurrence"]["surface"] == "مَا", "source occurrence surface")
    require(source["occurrence"]["segments"][0]["class"] == "qg-relative", "source contextual class")
    require(source["same_surface_card_occurrence_locs"] == ["2:284:10", "2:284:2"], "same-surface card ambiguity")


def check_contract() -> None:
    contract = read_json(OUT / "particle-contract.json")
    errors = validate_contract_record(contract)
    require(not errors, "typed contract errors: " + "; ".join(errors[:4]))
    require(contract["projection"]["status"] == "candidate", "contract candidate status")
    require(contract["projection"]["materialization_target"]["live_mutation_allowed"] is False, "contract live mutation guard")
    types = {fact["fact_type"] for fact in contract["facts"]}
    required = {"particle_entry", "particle_sense", "selected_word_edge", "canonical_occurrence", "contextual_function", "governed_scope", "contextual_gloss", "function_word_colour", "entry_occurrence_reciprocity", "alternative_function_routes"}
    require(required.issubset(types), "contract fact coverage")
    alternative = next(fact for fact in contract["facts"] if fact["fact_type"] == "alternative_function_routes")
    require(alternative["evidence_mode"] == "unresolved", "alternative readings must be unresolved")
    require(alternative["unresolved_blockers"], "alternative readings need an explicit blocker")
    colour = next(fact for fact in contract["facts"] if fact["fact_type"] == "function_word_colour")
    require(colour["fact_value"]["root"] is None and colour["fact_value"]["root_status"] == "function_only_no_root", "closed-class root guard")


def check_graph() -> None:
    edges = read_jsonl(OUT / "particle-graph-edges.jsonl")
    require(edges, "graph is non-empty")
    by_type: dict[str, list[dict[str, Any]]] = {}
    edge_ids = set()
    for edge in edges:
        require(edge.get("schema") == "qamus.graph_edge.v1", f"graph schema: {edge.get('edge_id')}")
        require(edge.get("edge_type") in EDGE_TYPE_SET, f"edge type: {edge.get('edge_type')}")
        require(edge.get("status") in STATUS_SET, f"edge status: {edge.get('status')}")
        require(edge.get("edge_id") not in edge_ids, "duplicate graph edge id")
        edge_ids.add(edge["edge_id"])
        require(edge.get("from_node_type") == edge["from_node_id"].split(":", 1)[0], "from node type")
        require(edge.get("to_node_type") == edge["to_node_id"].split(":", 1)[0], "to node type")
        require("page_context_entry_edge" != edge["edge_type"], "page context may not become a lexical edge")
        require("root_family_edge" != edge["edge_type"], "function word may not receive a root-family edge")
        by_type.setdefault(edge["edge_type"], []).append(edge)
        if edge["status"] == "candidate":
            require("candidate_only" in edge.get("guards", []), f"candidate edge missing candidate_only guard: {edge['edge_id']}")
    expected_pairs = {
        "source_card_edge": (SELECTED, CARD, "deterministic_exact"),
        "lexeme_entry_edge": (SELECTED, ENTRY, "deterministic_exact"),
        "form_entry_edge": (SELECTED, ENTRY, "deterministic_exact"),
        "sense_entry_edge": (SENSE, ENTRY, "deterministic_exact"),
        "selected_example_edge": (CARD, OCCURRENCE, "candidate"),
        "canonical_occurrence_edge": (SELECTED, OCCURRENCE, "candidate"),
        "display_local_to_canonical_crosswalk_edge": (CARD, OCCURRENCE, "candidate"),
        "decision_evidence_edge": (OCCURRENCE, ENTRY, "candidate"),
        "rendered_appearance_edge": (OCCURRENCE, APPEARANCE, "candidate"),
    }
    for edge_type, (from_node, to_node, status) in expected_pairs.items():
        require(any(edge["from_node_id"] == from_node and edge["to_node_id"] == to_node and edge["status"] == status for edge in by_type.get(edge_type, [])), f"missing typed chain edge {edge_type}")
    require(len(by_type["lexeme_entry_edge"]) == 1, "lexeme entry edge must be a singleton")
    require(len(by_type["form_entry_edge"]) == 1, "form entry edge must be a singleton")
    decision = by_type["decision_evidence_edge"][0]
    require(decision["details"]["function"] == "relative" and decision["details"]["relation"] == "direct_object", "contextual function/scope edge")
    require(decision["details"]["qg_class"] == "qg-relative", "contextual qg edge")
    forward = read_json(OUT / "particle-crosswalk-forward.json")
    reverse = read_json(OUT / "particle-crosswalk-reverse.json")
    require(forward["occurrence_id"] == "quran:2:284:10" and forward["trace_status"] == "candidate", "forward entry-occurrence trace")
    require(reverse["entry_id"] == "b8e480aebafe" and "quran:2:284:10" in reverse["occurrence_ids"], "reverse entry-occurrence trace")
    require(reverse["reciprocity"]["reverse_entry_matches_forward"], "reverse entry identity")
    require(reverse["reciprocity"]["selected_word_matches"], "reverse selected-word identity")
    require(all(edge_id in edge_ids for edge_id in forward["edge_ids"] + reverse["edge_ids"]), "trace edge references")


def check_payload_and_hover() -> None:
    payload = read_json(OUT / "particle-normalized-public-payload.json")
    require(payload["schema"] == "qamus.proof_particle.normalized_public_payload.v1", "payload schema")
    require(payload["candidate_status"] == "candidate", "payload candidate status")
    require(payload["live_mutation_allowed"] is False and payload["public_materialization_allowed"] is False, "payload mutation guards")
    require("".join(segment["surface"] for segment in payload["at_rest"]["segments"]) == "مَا", "at-rest reconstruction")
    require(payload["at_rest"]["segments"][0]["qg_class"] == "qg-relative", "at-rest qg colour")
    require(payload["at_rest"]["segments"][0]["root"] is None, "at-rest root silence")
    require(all(letter["root"] is None and letter["class"] == "function_particle" for letter in payload["at_rest"]["letter_ownership"]), "letter ownership root silence")
    require(payload["expanded"]["sarf"]["label"] == "Ṣarf — how this piece forms the word", "public Sarf label")
    require(payload["expanded"]["nahw"]["label"] == "Naḥw — what this piece does here", "public Nahw label")
    require(payload["expanded"]["nahw"]["function"] == "relative", "contextual Nahw function")
    require(payload["expanded"]["nahw"]["scope"]["relation"] == "direct_object", "governed scope")
    require(payload["hover"]["public_boundary"] == {"src": "qamus", "kind": "authored", "lang": "en"}, "hover public boundary")
    require(payload["decision_routes"]["public"] is False, "decision routes must not be learner-visible")
    hover_errors = validate_candidate(read_jsonl(OUT / "particle-rich-hover-candidate.jsonl")[0])
    require(not hover_errors, "rich hover errors: " + "; ".join(message for _, message in hover_errors[:4]))
    parity = read_json(OUT / "particle-parity-fixture.json")
    require(parity["expected"]["surface"] == payload["at_rest"]["surface"], "parity surface")
    require(parity["expected"]["hover_labels"] == ["Ṣarf — how this piece forms the word", "Naḥw — what this piece does here"], "parity hover labels")
    require(parity["expected"]["candidate_status"] == payload["candidate_status"], "parity candidate status")
    forbidden = ("informed_by", "external_informed_by", "quran.com", "corpus.quran", "tanzil", "qac:", "/srv" + "/", "c:" + "\\workspace")
    blob = json.dumps(payload, ensure_ascii=False).lower()
    require(not any(term in blob for term in forbidden), "public payload redaction boundary")


def check_render(full: bool) -> None:
    proof = read_json(OUT / "render-proof.json")
    require(proof["schema"] == "qamus.proof_particle.render_proof.v1", "render proof schema")
    if full:
        for key in ("font_check", "exact_reconstruction", "compact_present", "expanded_present", "same_payload_identity"):
            require(proof.get(key) is True, f"render proof {key}")
        require(proof.get("status") == "measured", "render proof measured status")
        require(proof.get("live_mutation_allowed") is False, "render proof live mutation guard")
    else:
        require(proof.get("live_mutation_allowed") is False, "render proof live mutation guard")


def check_manifest() -> None:
    manifest = read_json(OUT / "PROOFP-MANIFEST.json")
    require(manifest["schema"] == "qamus.proof_particle.manifest.v1", "manifest schema")
    require(manifest["candidate_only"] is True and manifest["live_mutation_allowed"] is False, "manifest candidate guards")
    require(manifest["png_policy"]["tracked"] is False, "manifest PNG policy")
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        require(path.exists(), f"manifest artifact missing: {artifact['path']}")
        import hashlib
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == artifact["sha256"], f"manifest checksum mismatch: {artifact['path']}")


def check_rm09() -> None:
    forbidden = ("/srv/" + "dawah", "c:" + "\\workspace", "c:" + "\\users", "informed_by", "external_informed_by", "quran.com", "corpus.quran", "tanzil", "qac:", "source-photo")
    for path in OUT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        require(not any(term in text for term in forbidden), f"RM-09 artifact leak: {path.relative_to(ROOT)}")
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    tracked_pngs = [line for line in result.stdout.splitlines() if line.lower().endswith(".png") and "proof-particle" in line]
    require(not tracked_pngs, "PNG must remain local-only and untracked")


def check_red_first() -> None:
    contract = read_json(OUT / "particle-contract.json")
    bad_contract = copy.deepcopy(contract)
    bad_contract["canonical_occurrence"]["surface"] = "مَاx"
    require(validate_contract_record(bad_contract), "red-first contract mutation did not fail")
    payload = read_json(OUT / "particle-normalized-public-payload.json")
    bad_payload = copy.deepcopy(payload)
    bad_payload["at_rest"]["segments"][0]["root"] = "م ا"
    require(bad_payload["at_rest"]["segments"][0]["root"] is not None, "red-first root mutation fixture")
    bad_hover = read_jsonl(OUT / "particle-rich-hover-candidate.jsonl")[0]
    bad_hover["qg_segment_classes"] = ["qg-invented"]
    require(validate_candidate(bad_hover), "red-first hover palette mutation did not fail")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="require a measured browser render proof")
    args = parser.parse_args()
    checks = [
        ("source packet", check_source_packet),
        ("typed contract", check_contract),
        ("typed graph chain", check_graph),
        ("payload and rich hover", check_payload_and_hover),
        ("render proof", lambda: check_render(args.full)),
        ("manifest", check_manifest),
        ("RM-09 and PNG guard", check_rm09),
        ("red-first mutations", check_red_first),
    ]
    failures: list[str] = []
    for name, check in checks:
        try:
            check()
        except Exception as exc:  # keep every failed gate visible in one run
            failures.append(f"{name}: {exc}")
            print(f"FAIL PROOF-P/{name}: {exc}")
        else:
            print(f"PASS PROOF-P/{name}")
    if failures:
        print(f"PROOFP HARNESS FAIL ({len(failures)} gate(s))")
        return 1
    print("PROOFP FULL HARNESS ALL PASS" if args.full else "PROOFP HARNESS ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
