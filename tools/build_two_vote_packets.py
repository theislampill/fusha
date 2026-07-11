#!/usr/bin/env python3
"""Build deterministic, evidence-complete Lane B calibration packets only.

The output contains fixed review evidence and a response schema. It does not
record votes, conclusions, ledger rows, crosswalk rows, or live mutations.
"""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import fact_ledger  # noqa: E402
from tools.compile_canonical_hover_whitelist_packet import (  # noqa: E402
    canonical_public_loc,
    public_content,
)


AUTHORITATIVE_BASELINE_SHA = "446a536a432cc819ddfcfcf1bd61dd7601996c94"
EXPECTED_BASELINE_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
EXPECTED_LOC_SURFACES_SHA256 = "f2e079dcdce01148074a238e3937314cf02222298f91f83ed66dcbb599697ca7"
TARGET_CLASSES = {"competing_lexical_senses", "unresolved_occurrence_ambiguity"}
NF_T10_1_AYAHS = {"2:274", "4:64", "12:37", "48:15"}
DEFAULT_CLASSIFICATION = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/laneb-classification.jsonl"
DEFAULT_QUEUE = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.jsonl"
DEFAULT_ENTRIES = ROOT / "qamus/data/current/entries.jsonl"
DEFAULT_BASELINE = ROOT.parent / "baseline-whitelist-972263b5.jsonl"
DEFAULT_LOC_SURFACES = ROOT.parent / "loc-surfaces-f2e079dc.jsonl"
DEFAULT_GATES = ROOT / "nahw/evals/grammar-decision-gates.json"
DEFAULT_FACT_SCHEMA = ROOT / "qamus/schemas/fact-ledger-row.schema.json"
DEFAULT_OUT = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/packets-cal-001.jsonl"
DEFAULT_MANIFEST = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/calibration-batch.manifest.json"

LOC_RE = re.compile(r"^(\d+):(\d+):(\d+)$")
CARD_RE = re.compile(r"^([^:]+):u(\d+):e(\d+)$")
GATE_TRIGGERS = {
    "competing_lexical_senses": ["multi_sense_root"],
    "unresolved_occurrence_ambiguity": ["advanced_nahw"],
}
RESPONSE_FIELDS = [
    "proposed_conclusion",
    "competing_alternatives",
    "sarf_evidence",
    "nahw_evidence",
    "source_address",
    "exact_reason",
    "gate",
    "abstention_or_blocker",
    "confidence",
    "evidence_hashes",
]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def loc_key(loc: str) -> tuple[int, int, int]:
    match = LOC_RE.fullmatch(str(loc))
    if not match:
        raise ValueError(f"invalid canonical location: {loc!r}")
    return tuple(int(part) for part in match.groups())


def ayah_of(loc: str) -> str:
    surah, ayah, _word = loc_key(loc)
    return f"{surah}:{ayah}"


def logical_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            row["__source_line__"] = line_no
            rows.append(row)
    return rows


def scrub_source_line(row: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in row.items() if key != "__source_line__"}


def row_source(path: Path, row: dict[str, Any], fragment: str = "") -> str:
    del row  # identity selectors, not physical line positions, survive input reordering
    if not fragment:
        raise ValueError("stable JSONL source addresses require an identity fragment")
    return f"{logical_path(path)}#{fragment}"


def canonical_rows_sha256(rows: Iterable[dict[str, Any]]) -> str:
    clean = [scrub_source_line(row) for row in rows]
    clean.sort(key=canonical_bytes)
    return stable_sha256(clean)


def index_unique(rows: Iterable[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} row missing {key}")
        if value in result:
            raise ValueError(f"duplicate {label} {key}: {value}")
        result[value] = row
    return result


def repeat_count(row: dict[str, Any]) -> int | None:
    for condition in row.get("evidence", {}).get("secondary_conditions", []):
        if isinstance(condition, str) and condition.startswith("surface_repeats_in_ayah:"):
            return int(condition.rsplit(":", 1)[1])
    return None


def root_pair(row: dict[str, Any]) -> tuple[str, str] | None:
    roots = sorted(
        {
            str(item.get("root") or "<unrecorded-root>")
            for item in row.get("evidence", {}).get("entry_evidence", [])
        }
    )
    if len(roots) != 2:
        return None
    return roots[0], roots[1]


def surah_round_robin(rows: Iterable[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    by_surah: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_surah[loc_key(row["canonical_location"])[0]].append(row)
    for values in by_surah.values():
        values.sort(key=lambda item: loc_key(item["canonical_location"]))
    selected: list[dict[str, Any]] = []
    depth = 0
    while len(selected) < count:
        progressed = False
        for surah in sorted(by_surah):
            values = by_surah[surah]
            if depth < len(values):
                selected.append(values[depth])
                progressed = True
                if len(selected) == count:
                    return selected
        if not progressed:
            break
        depth += 1
    raise ValueError(f"repeat-count stratum has {len(selected)} rows; requires {count}")


def select_calibration_rows(
    classifications: Iterable[dict[str, Any]],
    *,
    hardest_count: int = 5,
    lexical_count: int = 35,
    occurrence_per_bucket: int = 20,
) -> list[tuple[str, dict[str, Any]]]:
    eligible = [
        row
        for row in classifications
        if row.get("laneb_classification") in TARGET_CLASSES
        and ayah_of(row["canonical_location"]) not in NF_T10_1_AYAHS
    ]
    eligible.sort(key=lambda row: loc_key(row["canonical_location"]))

    hardest = sorted(
        eligible,
        key=lambda row: (
            -int(row.get("evidence", {}).get("candidate_count", 0)),
            loc_key(row["canonical_location"]),
        ),
    )[:hardest_count]
    used = {row["canonical_location"] for row in hardest}

    lexical: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for row in eligible:
        if row["canonical_location"] in used or row.get("laneb_classification") != "competing_lexical_senses":
            continue
        pair = root_pair(row)
        if pair is None or pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        lexical.append(row)
        used.add(row["canonical_location"])
        if len(lexical) == lexical_count:
            break
    if len(lexical) != lexical_count:
        raise ValueError(f"distinct-root-pair stratum has {len(lexical)} rows; requires {lexical_count}")

    occurrence: list[tuple[str, dict[str, Any]]] = []
    bucket_specs = (
        ("occurrence_repeat_2", lambda value: value == 2),
        ("occurrence_repeat_3", lambda value: value == 3),
        ("occurrence_repeat_gt3", lambda value: value is not None and value > 3),
    )
    for label, predicate in bucket_specs:
        candidates = [
            row
            for row in eligible
            if row["canonical_location"] not in used
            and row.get("laneb_classification") == "unresolved_occurrence_ambiguity"
            and predicate(repeat_count(row))
        ]
        chosen = surah_round_robin(candidates, occurrence_per_bucket)
        occurrence.extend((label, row) for row in chosen)
        used.update(row["canonical_location"] for row in chosen)

    result = [("hardest_highest_candidate_count", row) for row in hardest]
    result.extend(("competing_lexical_distinct_root_pair", row) for row in lexical)
    result.extend(occurrence)
    expected = hardest_count + lexical_count + 3 * occurrence_per_bucket
    if len(result) != expected or len({row["canonical_location"] for _label, row in result}) != expected:
        raise ValueError("calibration selection is incomplete or contains duplicate locations")
    return result


def load_gate_ssot(gate_path: Path, fact_schema_path: Path) -> dict[str, Any]:
    """Load and cross-check the gate SSOT through the ledger's own loader."""
    schema = fact_ledger.load_schema(fact_schema_path)
    two_vote_fact_types = sorted(fact_ledger._two_vote_fact_types(schema, gate_path))
    gates_doc = load_json(gate_path)
    gates = gates_doc.get("gates")
    if not isinstance(gates, dict) or not gates:
        raise ValueError("gate SSOT has no tiers")
    trigger_to_tier: dict[str, str] = {}
    for tier, spec in gates.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("rank"), int):
            raise ValueError(f"gate SSOT tier {tier!r} lacks an integer rank")
        for trigger in spec.get("trigger_when_ANY", []):
            prior = trigger_to_tier.get(trigger)
            if prior is None or gates[prior]["rank"] < spec["rank"]:
                trigger_to_tier[trigger] = tier
    for classification, triggers in GATE_TRIGGERS.items():
        if any(trigger not in trigger_to_tier for trigger in triggers):
            raise ValueError(f"gate SSOT lacks a tier for {classification}: {triggers}")
    return {
        "document": gates_doc,
        "trigger_to_tier": trigger_to_tier,
        "two_vote_fact_types": two_vote_fact_types,
    }


def gate_for(classification: str, gate_ssot: dict[str, Any], gate_path: Path) -> dict[str, Any]:
    triggers = GATE_TRIGGERS[classification]
    gates = gate_ssot["document"]["gates"]
    tiers = [gate_ssot["trigger_to_tier"][trigger] for trigger in triggers]
    tier = max(tiers, key=lambda value: gates[value]["rank"])
    return {
        "tier": tier,
        "rank": gates[tier]["rank"],
        "triggers": triggers,
        "requires": gates[tier].get("requires"),
        "source_address": f"{logical_path(gate_path)}#gates/{tier}",
        "loaded_via": "tools.fact_ledger._two_vote_fact_types",
    }


def choose_live_row(
    candidates: Iterable[dict[str, Any]], queue_row: dict[str, Any], loc: str
) -> dict[str, Any]:
    target = queue_row.get("live_payload_hash")
    matching = [row for row in candidates if stable_sha256(public_content(row)) == target]
    if not matching:
        raise ValueError(f"no live public row at {loc} matches queue hash {target}")
    matching.sort(key=lambda row: canonical_bytes(scrub_source_line(row)))
    return matching[0]


def entry_content_for_carrier(
    carrier: dict[str, Any], entry: dict[str, Any], entries_path: Path
) -> dict[str, Any]:
    card_id = carrier.get("card_id")
    match = CARD_RE.fullmatch(str(card_id))
    if not match or match.group(1) != entry.get("id"):
        raise ValueError(f"invalid carrier card_id for entry {entry.get('id')}: {card_id!r}")
    usage_index, example_index = int(match.group(2)), int(match.group(3))
    usages = entry.get("usage") or []
    if not (1 <= usage_index <= len(usages)):
        raise ValueError(f"carrier {card_id} usage lookup failed")
    examples = usages[usage_index - 1].get("examples") or []
    if not (1 <= example_index <= len(examples)):
        raise ValueError(f"carrier {card_id} example lookup failed")
    base = row_source(entries_path, entry, f"id={entry['id']}")
    matching_example = copy.deepcopy(examples[example_index - 1])
    if not isinstance(matching_example.get("ref"), str) or not matching_example["ref"]:
        raise ValueError(f"carrier {card_id} matching example lacks ref")
    return {
        "entry_source_address": base,
        "root": {
            "value": copy.deepcopy(entry.get("root")),
            "source_address": f"{base}/root",
        },
        "section": {
            "value": copy.deepcopy(entry.get("section")),
            "source_address": f"{base}/section",
        },
        "senses": [
            {
                "content": copy.deepcopy(sense),
                "source_address": f"{base}/senses/{index}",
            }
            for index, sense in enumerate(entry.get("senses") or [], 1)
        ],
        "matching_usage_examples": [
            {
                "content": matching_example,
                "usage_forms": copy.deepcopy(usages[usage_index - 1].get("forms") or []),
                "source_address": f"{base}/usage/{usage_index}/examples/{example_index}",
            }
        ],
    }


def response_schema(gate: dict[str, Any], evidence_hashes: dict[str, str]) -> dict[str, Any]:
    evidence_items = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["source_address", "exact_reason"],
            "properties": {
                "source_address": {"type": "string", "minLength": 1},
                "exact_reason": {"type": "string", "minLength": 1},
            },
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": RESPONSE_FIELDS,
        "properties": {
            "proposed_conclusion": {"type": ["string", "null"]},
            "competing_alternatives": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "sarf_evidence": copy.deepcopy(evidence_items),
            "nahw_evidence": copy.deepcopy(evidence_items),
            "source_address": {"type": "string", "minLength": 1},
            "exact_reason": {"type": "string", "minLength": 1},
            "gate": {"const": gate["tier"]},
            "abstention_or_blocker": {"type": ["string", "null"]},
            "confidence": {"enum": ["high", "medium", "low", "abstain"]},
            "evidence_hashes": {"const": copy.deepcopy(evidence_hashes)},
        },
    }


def build_packet(
    *,
    stratum: str,
    selection_rank: int,
    classification: dict[str, Any],
    queue_row: dict[str, Any],
    live_row: dict[str, Any],
    ayah_rows: list[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
    classification_path: Path,
    queue_path: Path,
    baseline_path: Path,
    loc_surfaces_path: Path,
    entries_path: Path,
    gate_path: Path,
    gate_ssot: dict[str, Any],
) -> dict[str, Any]:
    loc = classification["canonical_location"]
    if queue_row.get("canonical_location") != loc or canonical_public_loc(live_row) != loc:
        raise ValueError(f"source join mismatch at {loc}")
    live_public = public_content(live_row)
    if live_public.get("surface") != queue_row.get("source_normalization", {}).get("live_surface"):
        raise ValueError(f"live surface mismatch at {loc}")

    context = [
        {
            "loc": row["loc"],
            "surface": row["surface"],
            "source_address": row_source(loc_surfaces_path, row, f"loc={row['loc']}"),
        }
        for row in sorted(ayah_rows, key=lambda item: loc_key(item["loc"]))
    ]
    if loc not in {row["loc"] for row in context}:
        raise ValueError(f"loc-surfaces context lacks target {loc}")

    carriers: list[dict[str, Any]] = []
    for raw_carrier in queue_row.get("full_carrier_candidates") or []:
        carrier = {key: raw_carrier.get(key) for key in ("entry_id", "card_id", "qword_row_id", "row_id")}
        entry = entries.get(str(carrier["entry_id"]))
        if entry is None:
            raise ValueError(f"selected candidate entry lookup failed: {carrier['entry_id']}")
        carrier["carrier_source_address"] = row_source(
            queue_path,
            queue_row,
            f"canonical_location={loc}/full_carrier_candidates/row_id={carrier['row_id']}",
        )
        carrier["candidate_entry_content"] = entry_content_for_carrier(carrier, entry, entries_path)
        carriers.append(carrier)
    carriers.sort(key=canonical_bytes)
    gate = gate_for(classification["laneb_classification"], gate_ssot, gate_path)
    classification_content = scrub_source_line(classification)
    queue_content = scrub_source_line(queue_row)
    evidence_hashes = {
        "ayah_word_context_sha256": stable_sha256(context),
        "candidate_carriers_sha256": stable_sha256(carriers),
        "gate_ssot_sha256": sha256_file(gate_path),
        "laneb_classification_sha256": stable_sha256(classification_content),
        "live_public_content_sha256": stable_sha256(live_public),
        "queue_row_sha256": stable_sha256(queue_content),
    }
    packet = {
        "schema": "qamus.laneb_two_vote_calibration_packet.v1",
        "packet_id": f"laneb-cal-001:{selection_rank:03d}:{loc}",
        "calibration_stratum": stratum,
        "selection_rank": selection_rank,
        "canonical_location": loc,
        "live_surface": queue_row["source_normalization"]["live_surface"],
        "live_row_public_content": {
            "content": live_public,
            "source_address": row_source(baseline_path, live_row, f"loc={loc}"),
        },
        "ayah_word_context": context,
        "candidate_carriers": carriers,
        "laneb_classification": {
            "content": classification_content,
            "source_address": row_source(classification_path, classification, f"canonical_location={loc}"),
        },
        "queue_evidence": {
            "content": queue_content,
            "source_address": row_source(queue_path, queue_row, f"canonical_location={loc}"),
        },
        "gate": gate,
        "evidence_hashes": evidence_hashes,
        "required_response_schema": response_schema(gate, evidence_hashes),
        "packet_status": "evidence_packet_only_no_votes_no_conclusions",
    }
    validate_packet(packet)
    packet["packet_sha256"] = stable_sha256(packet)
    return packet


def validate_packet(packet: dict[str, Any]) -> None:
    required = {
        "canonical_location",
        "live_surface",
        "live_row_public_content",
        "ayah_word_context",
        "candidate_carriers",
        "laneb_classification",
        "queue_evidence",
        "gate",
        "evidence_hashes",
        "required_response_schema",
    }
    missing = sorted(required - set(packet))
    if missing:
        raise ValueError(f"packet missing fields: {missing}")
    gate = packet.get("gate")
    if not isinstance(gate, dict) or not gate.get("tier"):
        raise ValueError("packet missing gate tier")
    carriers = packet.get("candidate_carriers")
    if not isinstance(carriers, list) or not carriers:
        raise ValueError("packet has no candidate carriers")
    for index, carrier in enumerate(carriers):
        if any(not carrier.get(key) for key in ("entry_id", "card_id", "qword_row_id", "row_id")):
            raise ValueError(f"candidate carrier {index} lacks the full identity")
        content = carrier.get("candidate_entry_content")
        if not isinstance(content, dict):
            raise ValueError(f"candidate carrier {index} missing candidate content")
        for key in ("root", "section", "senses", "matching_usage_examples"):
            if key not in content:
                raise ValueError(f"candidate carrier {index} content missing {key}")
        examples = content.get("matching_usage_examples")
        if not isinstance(examples, list) or not examples:
            raise ValueError(f"candidate carrier {index} has no matching usage example")
        if any(not item.get("content", {}).get("ref") for item in examples):
            raise ValueError(f"candidate carrier {index} matching example lacks ref")
    response = packet.get("required_response_schema") or {}
    if response.get("required") != RESPONSE_FIELDS:
        raise ValueError("required response schema fields differ from the fixed contract")
    if response.get("properties", {}).get("gate", {}).get("const") != gate["tier"]:
        raise ValueError("required response schema gate differs from packet gate")
    if response.get("properties", {}).get("evidence_hashes", {}).get("const") != packet["evidence_hashes"]:
        raise ValueError("required response schema evidence hashes differ from packet evidence")
    if "packet_sha256" in packet:
        supplied = packet["packet_sha256"]
        unhashed = {key: value for key, value in packet.items() if key != "packet_sha256"}
        if supplied != stable_sha256(unhashed):
            raise ValueError("packet_sha256 mismatch")


def render_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    ordered = sorted(rows, key=lambda row: int(row.get("selection_rank", 0)))
    return b"".join(canonical_bytes(row) + b"\n" for row in ordered)


def input_pin(path: Path, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pin: dict[str, Any] = {"path": logical_path(path), "sha256": sha256_file(path)}
    if rows is not None:
        pin["row_count"] = len(rows)
        pin["canonical_rows_sha256"] = canonical_rows_sha256(rows)
    return pin


def current_head() -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise ValueError(f"cannot read git HEAD: {process.stderr.strip()}")
    return process.stdout.strip()


def repository_state_accepts_baseline(head: str, baseline: str, is_ancestor: bool) -> bool:
    return head == baseline or is_ancestor


def verify_repository_baseline() -> None:
    head = current_head()
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", AUTHORITATIVE_BASELINE_SHA, head],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if not repository_state_accepts_baseline(
        head, AUTHORITATIVE_BASELINE_SHA, process.returncode == 0
    ):
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"HEAD {head} does not descend from authoritative baseline "
            f"{AUTHORITATIVE_BASELINE_SHA}: {detail or 'merge-base rejected ancestry'}"
        )


def build(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = {
        "classification": Path(args.classification),
        "queue": Path(args.queue),
        "entries": Path(args.entries),
        "baseline_whitelist": Path(args.baseline),
        "loc_surfaces": Path(args.loc_surfaces),
        "grammar_gate_ssot": Path(args.gates),
        "fact_ledger_schema": Path(args.fact_schema),
    }
    for label, path in paths.items():
        if not path.is_file():
            raise ValueError(f"missing input {label}: {path}")
    verify_repository_baseline()
    if sha256_file(paths["baseline_whitelist"]) != EXPECTED_BASELINE_SHA256:
        raise ValueError("deployed baseline SHA-256 differs from the pinned queue input")
    if sha256_file(paths["loc_surfaces"]) != EXPECTED_LOC_SURFACES_SHA256:
        raise ValueError("loc-surfaces SHA-256 differs from f2e079dc pin")

    classifications = load_jsonl(paths["classification"])
    queue_rows = load_jsonl(paths["queue"])
    entry_rows = load_jsonl(paths["entries"])
    baseline_rows = load_jsonl(paths["baseline_whitelist"])
    loc_rows = load_jsonl(paths["loc_surfaces"])
    classifications_by_loc = index_unique(classifications, "canonical_location", "classification")
    queue_by_loc = index_unique(queue_rows, "canonical_location", "queue")
    entries = index_unique(entry_rows, "id", "entry")
    baseline_by_loc: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in baseline_rows:
        loc = canonical_public_loc(row)
        if loc:
            baseline_by_loc[loc].append(row)
    loc_by_ayah: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in loc_rows:
        loc_by_ayah[ayah_of(row["loc"])].append(row)

    population = [
        row
        for row in classifications
        if row.get("laneb_classification") in TARGET_CLASSES
    ]
    candidate_lookups = sum(
        len(row.get("evidence", {}).get("candidate_entry_ids", [])) for row in population
    )
    missing_lookups = sum(
        1
        for row in population
        for entry_id in row.get("evidence", {}).get("candidate_entry_ids", [])
        if entry_id not in entries
    )
    miss_rate = missing_lookups / candidate_lookups if candidate_lookups else 1.0
    if miss_rate > 0.01:
        raise ValueError(
            f"STOP: candidate entry lookup miss rate {miss_rate:.4%} exceeds 1%"
        )
    gate_ssot = load_gate_ssot(paths["grammar_gate_ssot"], paths["fact_ledger_schema"])
    selected = select_calibration_rows(classifications)

    packets: list[dict[str, Any]] = []
    for rank, (stratum, classification) in enumerate(selected, 1):
        loc = classification["canonical_location"]
        if loc not in classifications_by_loc or loc not in queue_by_loc or loc not in baseline_by_loc:
            raise ValueError(f"selected location lacks classification, queue, or live row: {loc}")
        live_row = choose_live_row(baseline_by_loc[loc], queue_by_loc[loc], loc)
        packet = build_packet(
            stratum=stratum,
            selection_rank=rank,
            classification=classification,
            queue_row=queue_by_loc[loc],
            live_row=live_row,
            ayah_rows=loc_by_ayah.get(ayah_of(loc), []),
            entries=entries,
            classification_path=paths["classification"],
            queue_path=paths["queue"],
            baseline_path=paths["baseline_whitelist"],
            loc_surfaces_path=paths["loc_surfaces"],
            entries_path=paths["entries"],
            gate_path=paths["grammar_gate_ssot"],
            gate_ssot=gate_ssot,
        )
        packets.append(packet)

    packet_bytes = render_jsonl(packets)
    stratum_counts = dict(sorted(collections.Counter(
        packet["calibration_stratum"] for packet in packets
    ).items()))
    class_counts = dict(sorted(collections.Counter(
        packet["laneb_classification"]["content"]["laneb_classification"]
        for packet in packets
    ).items()))
    manifest = {
        "schema": "qamus.laneb_two_vote_calibration_manifest.v1",
        "generator": "tools/build_two_vote_packets.py",
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "scope": "packets_only_no_votes_no_conclusions_no_ledger_writes_no_crosswalk_writes",
        "population": {
            "row_count": len(population),
            "class_counts": dict(sorted(collections.Counter(
                row["laneb_classification"] for row in population
            ).items())),
        },
        "selection_rule": {
            "pure_function": True,
            "randomness": "none",
            "excluded_ayahs": sorted(NF_T10_1_AYAHS, key=lambda value: tuple(map(int, value.split(":")))),
            "hardest": "First 5 eligible rows after sorting by candidate_count descending, then canonical location numerically ascending.",
            "competing_lexical_senses": "After hardest removal, scan canonical locations numerically; take the first row for each exactly-two-root signature until 35 distinct root pairs.",
            "unresolved_occurrence_ambiguity": "After prior strata removal, take 20 rows from each repeat bucket 2, 3, and >3 by numeric-surah round-robin; rows within each surah are numeric-location ordered.",
            "output_order": "hardest, lexical, repeat=2, repeat=3, repeat>3; selection_rank is contiguous 1..100.",
        },
        "gate_loading": {
            "loader": "tools.fact_ledger._two_vote_fact_types",
            "two_vote_fact_types": gate_ssot["two_vote_fact_types"],
            "classification_triggers": GATE_TRIGGERS,
        },
        "lookup_coverage": {
            "candidate_entry_lookup_count": candidate_lookups,
            "candidate_entry_lookup_miss_count": missing_lookups,
            "candidate_entry_lookup_miss_rate": miss_rate,
            "stop_threshold": 0.01,
        },
        "inputs": {
            label: input_pin(path, {
                "classification": classifications,
                "queue": queue_rows,
                "entries": entry_rows,
                "baseline_whitelist": baseline_rows,
                "loc_surfaces": loc_rows,
            }.get(label))
            for label, path in paths.items()
        },
        "output": {
            "path": logical_path(Path(args.out)),
            "rows": len(packets),
            "sha256": hashlib.sha256(packet_bytes).hexdigest(),
            "stratum_counts": stratum_counts,
            "population_class_counts": class_counts,
            "packet_sha256_rule": "SHA-256 of canonical compact JSON for the packet before adding packet_sha256.",
        },
        "required_response_fields": RESPONSE_FIELDS,
        "validation": {
            "self_test": "python tools/build_two_vote_packets.py --self-test",
            "rebuild": "python tools/build_two_vote_packets.py",
            "rollback": "git revert <commit>",
            "stop_conditions": [
                "candidate entry lookup failures exceed 1%",
                "gate SSOT lacks a tier for a selected decision trigger",
            ],
        },
    }
    return manifest, packets


def write_outputs(manifest: dict[str, Any], packets: list[dict[str, Any]], out: Path, manifest_path: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render_jsonl(packets))
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _synthetic_classification(
    loc: str, classification: str, candidates: int, roots: tuple[str, str], repeats: int | None
) -> dict[str, Any]:
    secondary = [] if repeats is None else [f"surface_repeats_in_ayah:{repeats}"]
    return {
        "canonical_location": loc,
        "laneb_classification": classification,
        "evidence": {
            "candidate_count": candidates,
            "entry_evidence": [{"root": root} for root in roots],
            "secondary_conditions": secondary,
        },
    }


def self_test() -> int:
    failures: list[str] = []
    missing_candidate_content = {
        "canonical_location": "2:1:1",
        "live_surface": "x",
        "live_row_public_content": {},
        "ayah_word_context": [],
        "candidate_carriers": [
            {"entry_id": "a", "card_id": "a:u1:e1", "qword_row_id": "q", "row_id": "r"}
        ],
        "laneb_classification": {},
        "queue_evidence": {},
        "gate": {"tier": "two_vote_required"},
        "evidence_hashes": {},
        "required_response_schema": {"required": RESPONSE_FIELDS},
    }
    missing_gate = copy.deepcopy(missing_candidate_content)
    missing_gate["candidate_carriers"][0]["candidate_entry_content"] = {
        "root": {}, "section": {}, "senses": [],
        "matching_usage_examples": [{"content": {"ref": "2:1"}}],
    }
    missing_gate["gate"] = {}
    for label, packet in (
        ("missing candidate content", missing_candidate_content),
        ("missing gate", missing_gate),
    ):
        try:
            validate_packet(packet)
        except ValueError:
            pass
        else:
            failures.append(f"validator accepted {label}")

    synthetic = [
        _synthetic_classification("2:1:1", "unresolved_occurrence_ambiguity", 99, ("a", "b"), 4),
        _synthetic_classification("3:1:1", "competing_lexical_senses", 2, ("c", "d"), None),
        _synthetic_classification("4:1:1", "competing_lexical_senses", 2, ("e", "f"), None),
        _synthetic_classification("5:1:1", "unresolved_occurrence_ambiguity", 2, ("g", "h"), 2),
        _synthetic_classification("6:1:1", "unresolved_occurrence_ambiguity", 2, ("i", "j"), 3),
        _synthetic_classification("7:1:1", "unresolved_occurrence_ambiguity", 2, ("k", "l"), 5),
    ]
    forward = select_calibration_rows(
        synthetic, hardest_count=1, lexical_count=1, occurrence_per_bucket=1
    )
    reverse = select_calibration_rows(
        reversed(synthetic), hardest_count=1, lexical_count=1, occurrence_per_bucket=1
    )
    projection = lambda rows: [(label, row["canonical_location"]) for label, row in rows]
    if projection(forward) != projection(reverse):
        failures.append("selection changed under input reordering")
    packet_rows = [
        {"selection_rank": 2, "value": "ب"},
        {"selection_rank": 1, "value": "ا"},
    ]
    if render_jsonl(packet_rows) != render_jsonl(reversed(packet_rows)):
        failures.append("packet bytes changed under input reordering")
    source_a = row_source(DEFAULT_ENTRIES, {"__source_line__": 1}, "id=entry-a")
    source_b = row_source(DEFAULT_ENTRIES, {"__source_line__": 999}, "id=entry-a")
    if source_a != source_b:
        failures.append("stable source address changed with physical input line")
    if not repository_state_accepts_baseline("descendant", AUTHORITATIVE_BASELINE_SHA, True):
        failures.append("verified descendant commit rejected its authoritative baseline")
    if repository_state_accepts_baseline("unrelated", AUTHORITATIVE_BASELINE_SHA, False):
        failures.append("unrelated commit accepted the authoritative baseline")
    live_a = {"loc": "2:1:1", "surface": "ا", "public_gloss": "first"}
    live_b = {"loc": "2:1:1", "surface": "ا", "public_gloss": "second"}
    target_queue = {"live_payload_hash": stable_sha256(public_content(live_b))}
    chosen_forward = choose_live_row([live_a, live_b], target_queue, "2:1:1")
    chosen_reverse = choose_live_row([live_b, live_a], target_queue, "2:1:1")
    if chosen_forward.get("public_gloss") != "second" or chosen_reverse != chosen_forward:
        failures.append("live row selection changed under duplicate input reordering")
    if failures:
        raise AssertionError("; ".join(failures))
    print("SELFTESTS=8 FAILURES=0")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--classification", default=DEFAULT_CLASSIFICATION)
    result.add_argument("--queue", default=DEFAULT_QUEUE)
    result.add_argument("--entries", default=DEFAULT_ENTRIES)
    result.add_argument("--baseline", default=DEFAULT_BASELINE)
    result.add_argument("--loc-surfaces", default=DEFAULT_LOC_SURFACES)
    result.add_argument("--gates", default=DEFAULT_GATES)
    result.add_argument("--fact-schema", default=DEFAULT_FACT_SCHEMA)
    result.add_argument("--out", default=DEFAULT_OUT)
    result.add_argument("--manifest", default=DEFAULT_MANIFEST)
    result.add_argument("--self-test", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        return self_test()
    manifest, packets = build(args)
    write_outputs(manifest, packets, Path(args.out), Path(args.manifest))
    print(json.dumps(manifest["output"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
