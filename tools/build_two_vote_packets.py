#!/usr/bin/env python3
"""Build deterministic, evidence-complete Lane B calibration packets only.

The output contains fixed review evidence and a response schema. It does not
record votes, conclusions, ledger rows, crosswalk rows, or live mutations.
"""

from __future__ import annotations

import argparse
import collections
import copy
import dataclasses
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
from tools.fusha_text_check import segment_candidates  # noqa: E402
from tools.normalize_ar import bare, norm, norm_strict  # noqa: E402
from tools.compile_canonical_hover_whitelist_packet import (  # noqa: E402
    canonical_public_loc,
    public_content,
)


AUTHORITATIVE_BASELINE_SHA = "3f23dd4adab3222d1e8277bc5a1097186dc08f6d"
WAVE_02_AUTHORITATIVE_BASELINE_SHA = "c0c4ea7c0fba5457177b70a97655e204165ed083"
WAVE_03_AUTHORITATIVE_BASELINE_SHA = "2defdc9eb65656fc93f0cd9ff5a73c6b68da1b61"
EXPECTED_BASELINE_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
EXPECTED_LOC_SURFACES_SHA256 = "f2e079dcdce01148074a238e3937314cf02222298f91f83ed66dcbb599697ca7"
EXPECTED_V1_PACKET_SHA256 = "95788fabc0ba7b65558d03b2d0854f361e507dfaeaa6ec3d43732a1b7985b311"
EXPECTED_WAVE_02_PACKET_SHA256 = "9bd56a11af30b6c0bf3181a960da4cf1ece8ea15ec66d62ed2b6759b0d58dc65"
TARGET_CLASSES = {"competing_lexical_senses", "unresolved_occurrence_ambiguity"}
NF_T10_1_AYAHS = {"2:274", "4:64", "12:37", "48:15"}
DEFAULT_CLASSIFICATION = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/laneb-classification.jsonl"
DEFAULT_QUEUE = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.jsonl"
DEFAULT_ENTRIES = ROOT / "qamus/data/current/entries.jsonl"
DEFAULT_BASELINE = ROOT.parent / "baseline-whitelist-972263b5.jsonl"
DEFAULT_LOC_SURFACES = ROOT.parent / "loc-surfaces-f2e079dc.jsonl"
DEFAULT_GATES = ROOT / "nahw/evals/grammar-decision-gates.json"
DEFAULT_FACT_SCHEMA = ROOT / "qamus/schemas/fact-ledger-row.schema.json"
DEFAULT_HOMOGRAPH_KEYS = ROOT / "qamus/indexes/largelexicon/homograph-keys.json"
DEFAULT_V1_PACKETS = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/packets-cal-001.jsonl"
DEFAULT_OUT = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/packets-cal-002.jsonl"
DEFAULT_MANIFEST = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/calibration-batch-v2.manifest.json"
DEFAULT_WAVE_OUT = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/packets-wave-02.jsonl"
DEFAULT_WAVE_MANIFEST = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/wave-02-batch.manifest.json"
DEFAULT_WAVE_02_PACKETS = DEFAULT_WAVE_OUT
DEFAULT_WAVE_03_OUT = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/packets-wave-03.jsonl"
DEFAULT_WAVE_03_MANIFEST = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/two-vote/wave-03-batch.manifest.json"

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


@dataclasses.dataclass(frozen=True)
class Wave4Exclusions:
    locations: set[str]
    review_fact_ids: set[str]


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


def verify_wave_4_queue_pin(
    queue_path: Path, queue_manifest_path: Path, required_manifest_sha256: str
) -> None:
    """Refuse Wave 4 unless both the manifest bytes and its queue state match."""
    actual_manifest_sha256 = sha256_file(queue_manifest_path)
    if actual_manifest_sha256 != required_manifest_sha256:
        raise ValueError(
            "STOP: queue manifest SHA-256 differs from the required post-repair pin: "
            f"expected {required_manifest_sha256}, got {actual_manifest_sha256}"
        )
    manifest = load_json(queue_manifest_path)
    pinned_queue_sha256 = manifest.get("queue_sha256")
    actual_queue_sha256 = sha256_file(queue_path)
    if pinned_queue_sha256 != actual_queue_sha256:
        raise ValueError(
            "STOP: queue SHA-256 differs from the state pinned by the required queue manifest: "
            f"expected {pinned_queue_sha256}, got {actual_queue_sha256}"
        )


def load_wave_4_strata(path: Path) -> dict[str, int]:
    """Load caller-owned Wave 4 class counts; the mixed batch must total 250."""
    document = load_json(path)
    if not isinstance(document, dict) or set(document) != TARGET_CLASSES:
        raise ValueError(
            "STOP: wave-4 strata must contain exactly " + ", ".join(sorted(TARGET_CLASSES))
        )
    if any(not isinstance(count, int) or count < 0 for count in document.values()):
        raise ValueError("STOP: wave-4 stratum counts must be non-negative integers")
    if sum(document.values()) != 250:
        raise ValueError("STOP: wave-4 strata must total exactly 250 rows")
    return document


def load_excluded_locations(paths: Iterable[Path]) -> set[str]:
    """Load canonical locations from caller-owned JSON or JSONL exclusion lists."""
    excluded: set[str] = set()
    for path in paths:
        if path.suffix == ".jsonl":
            rows: Any = load_jsonl(path)
        else:
            rows = load_json(path)
            if isinstance(rows, dict):
                rows = rows.get("locations", rows.get("rows"))
        if not isinstance(rows, list):
            raise ValueError(f"STOP: exclusion list must be a JSON array or JSONL rows: {path}")
        for row in rows:
            loc = row if isinstance(row, str) else row.get("canonical_location", row.get("loc"))
            if not isinstance(loc, str) or not LOC_RE.fullmatch(loc):
                raise ValueError(f"STOP: exclusion row lacks a canonical location in {path}: {row!r}")
            excluded.add(loc)
    return excluded


def _row_review_fact_ids(row: dict[str, Any]) -> set[str]:
    rebind_provenance = row.get("rebind_provenance")
    values = {
        row.get("review_fact_id"),
        row.get("ledger_fact_id"),
        rebind_provenance.get("review_fact_id")
        if isinstance(rebind_provenance, dict)
        else None,
    }
    return {value for value in values if isinstance(value, str) and value}


def load_wave_4_exclusions(paths: Iterable[Path]) -> Wave4Exclusions:
    """Load prior selections by both location and stable review-fact identity."""
    locations: set[str] = set()
    review_fact_ids: set[str] = set()
    for path in paths:
        document: Any = load_jsonl(path) if path.suffix == ".jsonl" else load_json(path)
        if isinstance(document, dict):
            rows = document.get("locations", document.get("rows"))
        else:
            rows = document
        if not isinstance(rows, list):
            raise ValueError(f"STOP: exclusion list must be a JSON array or JSONL rows: {path}")
        for row in rows:
            if isinstance(row, str):
                loc = row
            elif isinstance(row, dict):
                loc = row.get("canonical_location", row.get("loc"))
                review_fact_ids.update(_row_review_fact_ids(row))
            else:
                loc = None
            if not isinstance(loc, str) or not LOC_RE.fullmatch(loc):
                raise ValueError(f"STOP: exclusion row lacks a canonical location in {path}: {row!r}")
            locations.add(loc)
    return Wave4Exclusions(locations=locations, review_fact_ids=review_fact_ids)


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


def select_wave_rows(
    classifications: Iterable[dict[str, Any]],
    *,
    excluded_locations: set[str],
    lexical_mapping_quality: dict[str, tuple[int, int]],
    occurrence_mapping_quality: dict[str, bool],
    lexical_count: int = 90,
    occurrence_count: int = 160,
) -> list[tuple[str, dict[str, Any]]]:
    """Select wave membership only; scores never express a semantic verdict."""
    eligible = [
        row for row in classifications
        if row.get("laneb_classification") in TARGET_CLASSES
        and row["canonical_location"] not in excluded_locations
        and ayah_of(row["canonical_location"]) not in NF_T10_1_AYAHS
    ]
    lexical = [row for row in eligible if row["laneb_classification"] == "competing_lexical_senses"]
    occurrence = [
        row for row in eligible
        if row["laneb_classification"] == "unresolved_occurrence_ambiguity"
    ]
    lexical.sort(key=lambda row: (
        -lexical_mapping_quality.get(row["canonical_location"], (0, 0))[0],
        -lexical_mapping_quality.get(row["canonical_location"], (0, 0))[1],
        root_pair(row) or ("~", "~"),
        loc_key(row["canonical_location"]),
    ))
    occurrence.sort(key=lambda row: (
        0 if occurrence_mapping_quality.get(row["canonical_location"], False) else 1,
        loc_key(row["canonical_location"]),
    ))
    if len(lexical) < lexical_count or len(occurrence) < occurrence_count:
        raise ValueError(
            "STOP: wave underfill: "
            f"eligible lexical={len(lexical)}/{lexical_count}, "
            f"occurrence={len(occurrence)}/{occurrence_count}"
        )
    selected = lexical[:lexical_count] + occurrence[:occurrence_count]
    return [(row["laneb_classification"], row) for row in selected]


def select_proportional_lexicographic_rows(
    classifications: Iterable[dict[str, Any]],
    *,
    excluded_locations: set[str],
    batch_size: int = 500,
) -> list[tuple[str, dict[str, Any]]]:
    """Allocate exact class quotas by largest remainder, then select lexicographically."""
    eligible = [
        row for row in classifications
        if row.get("laneb_classification") in TARGET_CLASSES
        and row["canonical_location"] not in excluded_locations
        and ayah_of(row["canonical_location"]) not in NF_T10_1_AYAHS
    ]
    if len(eligible) < batch_size:
        raise ValueError(
            f"STOP: wave underfill: eligible rows={len(eligible)}/{batch_size}"
        )
    by_class: dict[str, list[dict[str, Any]]] = {
        classification: [] for classification in sorted(TARGET_CLASSES)
    }
    for row in eligible:
        by_class[row["laneb_classification"]].append(row)
    total = len(eligible)
    quotas = {
        classification: len(rows) * batch_size // total
        for classification, rows in by_class.items()
    }
    unallocated = batch_size - sum(quotas.values())
    remainder_order = sorted(
        by_class,
        key=lambda classification: (
            -(len(by_class[classification]) * batch_size % total),
            classification,
        ),
    )
    for classification in remainder_order[:unallocated]:
        quotas[classification] += 1
    selected: list[tuple[str, dict[str, Any]]] = []
    for classification, rows in by_class.items():
        rows.sort(key=lambda row: row["canonical_location"])
        selected.extend((classification, row) for row in rows[:quotas[classification]])
    if len(selected) != batch_size:
        raise ValueError("STOP: proportional wave selection did not fill the batch")
    return selected


def select_wave_4_rows(
    classifications: Iterable[dict[str, Any]],
    *,
    queue_by_loc: dict[str, dict[str, Any]],
    excluded_locations: set[str],
    excluded_review_fact_ids: set[str],
    strata: dict[str, int],
) -> list[tuple[str, dict[str, Any]]]:
    """Select a 250-row mixed Wave 4 from caller-supplied residual strata.

    Wave 3 nearly exhausted the occurrence-ambiguity priority slice. The
    post-NF-T10-1 residual therefore determines both class counts and exclusions
    at execution time; neither is encoded in this tooling. Within each requested
    class, canonical-location ordering makes membership deterministic. Packet
    construction and its frozen response format remain unchanged.
    """
    by_class = {classification: [] for classification in sorted(TARGET_CLASSES)}
    for row in classifications:
        classification = row.get("laneb_classification")
        loc = row["canonical_location"]
        queue_row = queue_by_loc.get(loc)
        review_fact_ids = _row_review_fact_ids(row)
        if queue_row is not None:
            review_fact_ids.update(_row_review_fact_ids(queue_row))
        if (
            classification in by_class
            and loc not in excluded_locations
            and not review_fact_ids.intersection(excluded_review_fact_ids)
            and queue_row is not None
            and queue_row.get("primary_resolution_family") == "multiple_qword_candidates"
            and queue_row.get("provenance_state") == "unresolved_candidate"
            and queue_row.get("review_state") == "pending"
            and queue_row.get("data_quality_quarantine") is not True
        ):
            by_class[classification].append(row)
    selected: list[tuple[str, dict[str, Any]]] = []
    for classification, rows in by_class.items():
        rows.sort(key=lambda row: loc_key(row["canonical_location"]))
        required = strata[classification]
        if len(rows) < required:
            raise ValueError(
                "STOP: wave-4 stratum underfill: "
                f"{classification} eligible={len(rows)}/{required}"
            )
        selected.extend((classification, row) for row in rows[:required])
    return selected


def render_wave_4_selection_artifact(
    selected: Iterable[tuple[str, dict[str, Any]]],
) -> bytes:
    """Project membership only; never carry source-row semantic fields."""
    records = [
        {
            "schema": "qamus.wave_4_ordering_selection.v1",
            "selection_basis": "ordering_only",
            "selection_rank": rank,
            "stratum": stratum,
            "canonical_location": row["canonical_location"],
        }
        for rank, (stratum, row) in enumerate(selected, 1)
    ]
    return render_jsonl(records)


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


def build_occurrence_mapping(
    carrier: dict[str, Any],
    matching_example: dict[str, Any],
    ayah_context: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Map an indexed example token to every matching ayah occurrence by a ±2 window."""
    try:
        qword_index = int(str(carrier["qword_row_id"]).rsplit("-", 1)[1])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid carrier qword_row_id: {carrier.get('qword_row_id')!r}") from exc
    content = matching_example.get("content") or {}
    raw_tokens = str(content.get("ar") or "").split()
    if not 1 <= qword_index <= len(raw_tokens):
        raise ValueError(
            f"carrier {carrier.get('qword_row_id')} qword index exceeds its example token count"
        )
    candidate_surface = raw_tokens[qword_index - 1]
    candidate_key = norm_strict(candidate_surface)
    if not candidate_key:
        raise ValueError(f"carrier {carrier.get('qword_row_id')} points at punctuation, not a word")

    example_words = [
        (raw_index, token, norm_strict(token))
        for raw_index, token in enumerate(raw_tokens, 1)
        if norm_strict(token)
    ]
    try:
        example_word_index = next(
            index for index, (raw_index, _surface, _key) in enumerate(example_words)
            if raw_index == qword_index
        )
    except StopIteration as exc:
        raise ValueError(f"carrier {carrier.get('qword_row_id')} has no word-level example token") from exc
    example_window = example_words[
        max(0, example_word_index - 2):example_word_index + 3
    ]
    example_window_keys = [item[2] for item in example_window]

    context = sorted((copy.deepcopy(row) for row in ayah_context), key=lambda row: loc_key(row["loc"]))
    same_surface_indexes = [
        index for index, row in enumerate(context)
        if norm_strict(str(row.get("surface") or "")) == candidate_key
    ]
    if not same_surface_indexes:
        raise ValueError(
            f"example surface {candidate_surface!r} has no norm_strict occurrence in ayah context"
        )
    fingerprints: list[dict[str, Any]] = []
    fingerprint_matches: list[str] = []
    for index in same_surface_indexes:
        words = context[max(0, index - 2):index + 3]
        word_projection = [
            {
                "loc": word["loc"],
                "surface": word["surface"],
                "source_address": word["source_address"],
            }
            for word in words
        ]
        matches = [norm_strict(word["surface"]) for word in words] == example_window_keys
        if matches:
            fingerprint_matches.append(context[index]["loc"])
        fingerprints.append(
            {
                "loc": context[index]["loc"],
                "matches_example_fingerprint": matches,
                "window": word_projection,
                "window_sha256": stable_sha256(word_projection),
            }
        )
    example_source = matching_example.get("source_address")
    if not isinstance(example_source, str) or not example_source:
        raise ValueError("matching example lacks a stable source address")
    return {
        "candidate_surface": {
            "value": candidate_surface,
            "norm_strict": candidate_key,
            "source_address": f"{example_source}/ar#whitespace-token={qword_index}",
        },
        "example_window_fingerprint": {
            "surfaces": [item[1] for item in example_window],
            "norm_strict_surfaces": example_window_keys,
            "source_address": f"{example_source}/ar#word-window={example_word_index + 1}:plus-minus-2",
        },
        "example_occurrence_candidates": [context[index]["loc"] for index in same_surface_indexes],
        "fingerprint_match_candidates": fingerprint_matches,
        "mapping_status": "unique" if len(fingerprint_matches) == 1 else "ambiguous",
        "occurrence_fingerprints": fingerprints,
    }


def sourced(value: Any, source_address: str) -> dict[str, Any]:
    return {"value": copy.deepcopy(value), "source_address": source_address}


def build_morphology_record(
    *,
    target_loc: str,
    target_surface: str,
    target_source_address: str,
    carriers: Iterable[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
    entries_path: Path,
    homograph_index: dict[str, list[tuple[int, dict[str, Any]]]],
    homograph_path: Path,
) -> dict[str, Any]:
    """Expose deterministic morphology evidence without selecting or inventing a reading."""
    if not target_surface or not norm_strict(target_surface):
        return {"available": False}
    normalization = {
        "available": True,
        "input": sourced(target_surface, target_source_address),
        "analyses": {
            "bare": sourced(bare(target_surface), "tools/normalize_ar.py#bare"),
            "norm": sourced(norm(target_surface), "tools/normalize_ar.py#norm"),
            "norm_strict": sourced(norm_strict(target_surface), "tools/normalize_ar.py#norm_strict"),
        },
    }

    raw_segments = segment_candidates(target_surface)
    segment_records: list[dict[str, Any]] = []
    stem_keys: dict[int, set[str]] = collections.defaultdict(set)
    for candidate_index, candidate in enumerate(raw_segments, 1):
        candidate_source = f"tools/fusha_text_check.py#segment_candidates/{candidate_index}"
        segments = []
        for segment_index, segment in enumerate(candidate.get("segments") or [], 1):
            segment_source = f"{candidate_source}/segments/{segment_index}"
            segments.append(
                {
                    "role": sourced(segment.get("role"), f"{segment_source}/role"),
                    "surface": sourced(segment.get("surface"), target_source_address),
                }
            )
            if segment.get("role") == "stem" and segment.get("surface"):
                stem_keys[candidate_index].add(norm_strict(segment["surface"]))
        segment_records.append(
            {
                "candidate_index": sourced(candidate_index, candidate_source),
                "legal": sourced(bool(candidate.get("legal")), f"{candidate_source}/legal"),
                "single_letter_clitic": sourced(
                    bool(candidate.get("single_letter_clitic")),
                    f"{candidate_source}/single_letter_clitic",
                ),
                "segments": segments,
            }
        )

    lexical_candidates: list[dict[str, Any]] = []
    seen_entry_usages: set[tuple[str, int]] = set()
    for carrier in sorted(carriers, key=canonical_bytes):
        entry_id = str(carrier.get("entry_id") or "")
        entry = entries.get(entry_id)
        match = CARD_RE.fullmatch(str(carrier.get("card_id") or ""))
        if entry is None or match is None or match.group(1) != entry_id:
            continue
        usage_index = int(match.group(2))
        identity = (entry_id, usage_index)
        if identity in seen_entry_usages:
            continue
        seen_entry_usages.add(identity)
        usages = entry.get("usage") or []
        if not 1 <= usage_index <= len(usages):
            continue
        base = row_source(entries_path, entry, f"id={entry_id}")
        for form_index, form in enumerate(usages[usage_index - 1].get("forms") or [], 1):
            form_key = norm_strict(str(form))
            matching_segment_indexes = sorted(
                index for index, keys in stem_keys.items() if form_key and form_key in keys
            )
            for segment_index in matching_segment_indexes:
                form_source = f"{base}/usage/{usage_index}/forms/{form_index}"
                candidate: dict[str, Any] = {
                    "entry_id": sourced(entry_id, f"{base}/id"),
                    "documented_form": sourced(form, form_source),
                    "segment_candidate_index": sourced(
                        segment_index,
                        f"tools/fusha_text_check.py#segment_candidates/{segment_index}",
                    ),
                }
                if entry.get("headword"):
                    candidate["lemma"] = sourced(entry["headword"], f"{base}/headword")
                if entry.get("root"):
                    candidate["root"] = sourced(entry["root"], f"{base}/root")
                pos_field = "section" if entry.get("section") else "category"
                if entry.get(pos_field):
                    candidate["pos"] = sourced(entry[pos_field], f"{base}/{pos_field}")
                lexical_candidates.append(candidate)
    lexical_candidates.sort(key=canonical_bytes)

    homograph_flags: list[dict[str, Any]] = []
    for _row_index, row in homograph_index.get(norm(target_surface), []):
        base = f"{logical_path(homograph_path)}#keys/norm_key={row.get('norm_key')}"
        homograph_flags.append(
            {
                "risk_flag": sourced(
                    row.get("__risk_flag__"),
                    f"{logical_path(homograph_path)}#risk_flag",
                ),
                "norm_key": sourced(row.get("norm_key"), f"{base}/norm_key"),
                "root_count": sourced(row.get("root_count"), f"{base}/root_count"),
                "roots": [
                    sourced(root, f"{base}/roots/root={root}")
                    for root in sorted(set(row.get("roots") or []))
                ],
            }
        )
    homograph_flags.sort(key=canonical_bytes)
    return {
        "available": True,
        "target_loc": sourced(target_loc, target_source_address),
        "normalization_analyses": normalization,
        "segment_candidates": {
            "available": bool(segment_records),
            "candidates": segment_records,
        },
        "lemma_root_pos_candidates": {
            "available": bool(lexical_candidates),
            "candidates": lexical_candidates,
        },
        "homograph_flags": {
            "available": bool(homograph_flags),
            "flags": homograph_flags,
        },
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
    homograph_path: Path,
    homograph_index: dict[str, list[tuple[int, dict[str, Any]]]],
    gate_path: Path,
    gate_ssot: dict[str, Any],
    packet_id_prefix: str = "laneb-cal-002",
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
        carrier.update(
            build_occurrence_mapping(
                carrier,
                carrier["candidate_entry_content"]["matching_usage_examples"][0],
                context,
            )
        )
        carriers.append(carrier)
    carriers.sort(key=canonical_bytes)
    carriers_uniquely_addressing_target = sorted(
        {
            str(carrier["entry_id"])
            for carrier in carriers
            if carrier["mapping_status"] == "unique"
            and carrier["fingerprint_match_candidates"] == [loc]
        }
    )
    target_context = next(row for row in context if row["loc"] == loc)
    morphology_record = build_morphology_record(
        target_loc=loc,
        target_surface=queue_row["source_normalization"]["live_surface"],
        target_source_address=target_context["source_address"],
        carriers=carriers,
        entries=entries,
        entries_path=entries_path,
        homograph_index=homograph_index,
        homograph_path=homograph_path,
    )
    gate = gate_for(classification["laneb_classification"], gate_ssot, gate_path)
    classification_content = scrub_source_line(classification)
    queue_content = scrub_source_line(queue_row)
    evidence_hashes = {
        "ayah_word_context_sha256": stable_sha256(context),
        "candidate_carriers_sha256": stable_sha256(carriers),
        "gate_ssot_sha256": sha256_file(gate_path),
        "laneb_classification_sha256": stable_sha256(classification_content),
        "live_public_content_sha256": stable_sha256(live_public),
        "morphology_record_sha256": stable_sha256(morphology_record),
        "queue_row_sha256": stable_sha256(queue_content),
    }
    packet = {
        "schema": "qamus.laneb_two_vote_calibration_packet.v2",
        "packet_id": f"{packet_id_prefix}:{selection_rank:03d}:{loc}",
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
        "mapping_status": "unique" if carriers_uniquely_addressing_target else "ambiguous",
        "carriers_uniquely_addressing_target": carriers_uniquely_addressing_target,
        "morphology_record": morphology_record,
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
        "mapping_status",
        "carriers_uniquely_addressing_target",
        "morphology_record",
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
    if packet.get("mapping_status") not in {"unique", "ambiguous"}:
        raise ValueError("packet missing a valid mapping_status")
    uniquely_addressing = packet.get("carriers_uniquely_addressing_target")
    if not isinstance(uniquely_addressing, list):
        raise ValueError("packet missing carriers_uniquely_addressing_target")
    morphology = packet.get("morphology_record")
    if not isinstance(morphology, dict) or not isinstance(morphology.get("available"), bool):
        raise ValueError("packet missing morphology_record availability")
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
        if carrier.get("mapping_status") not in {"unique", "ambiguous"}:
            raise ValueError(f"candidate carrier {index} lacks a valid mapping_status")
        occurrences = carrier.get("example_occurrence_candidates")
        fingerprints = carrier.get("occurrence_fingerprints")
        if not isinstance(occurrences, list) or not occurrences:
            raise ValueError(f"candidate carrier {index} has no occurrence candidates")
        if not isinstance(fingerprints, list) or [item.get("loc") for item in fingerprints] != occurrences:
            raise ValueError(f"candidate carrier {index} fingerprints differ from occurrence candidates")
        matches = carrier.get("fingerprint_match_candidates")
        expected_status = "unique" if isinstance(matches, list) and len(matches) == 1 else "ambiguous"
        if carrier["mapping_status"] != expected_status:
            raise ValueError(f"candidate carrier {index} mapping status differs from fingerprints")
    derived_unique_entries = sorted(
        {
            str(carrier["entry_id"])
            for carrier in carriers
            if carrier["mapping_status"] == "unique"
            and carrier["fingerprint_match_candidates"] == [packet["canonical_location"]]
        }
    )
    if uniquely_addressing != derived_unique_entries:
        raise ValueError("carriers_uniquely_addressing_target differs from carrier mappings")
    expected_packet_status = "unique" if derived_unique_entries else "ambiguous"
    if packet["mapping_status"] != expected_packet_status:
        raise ValueError("packet mapping_status differs from target-addressing carriers")
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


def verify_repository_baseline(baseline: str = AUTHORITATIVE_BASELINE_SHA) -> None:
    head = current_head()
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", baseline, head],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if not repository_state_accepts_baseline(
        head, baseline, process.returncode == 0
    ):
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"HEAD {head} does not descend from authoritative baseline "
            f"{baseline}: {detail or 'merge-base rejected ancestry'}"
        )


def build(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    wave_four_mode = getattr(args, "wave", None) == 4
    paths = {
        "classification": Path(args.classification),
        "queue": Path(args.queue),
        "entries": Path(args.entries),
        "baseline_whitelist": Path(args.baseline),
        "loc_surfaces": Path(args.loc_surfaces),
        "homograph_keys": Path(args.homograph_keys),
        "v1_packets": Path(args.v1_packets),
        "grammar_gate_ssot": Path(args.gates),
        "fact_ledger_schema": Path(args.fact_schema),
    }
    if args.batch == "wave-03":
        paths["wave_02_packets"] = Path(args.wave_02_packets)
    if wave_four_mode:
        paths["queue_manifest"] = Path(args.queue_manifest)
        paths["strata"] = Path(args.strata)
        for index, path in enumerate(args.exclude_locations, 1):
            paths[f"exclude_locations_{index}"] = Path(path)
    for label, path in paths.items():
        if not path.is_file():
            raise ValueError(f"missing input {label}: {path}")
    baseline_by_batch = {
        "calibration": AUTHORITATIVE_BASELINE_SHA,
        "wave-02": WAVE_02_AUTHORITATIVE_BASELINE_SHA,
        "wave-03": WAVE_03_AUTHORITATIVE_BASELINE_SHA,
    }
    verify_repository_baseline(
        WAVE_03_AUTHORITATIVE_BASELINE_SHA if wave_four_mode else baseline_by_batch[args.batch]
    )
    if wave_four_mode:
        verify_wave_4_queue_pin(
            paths["queue"], paths["queue_manifest"], args.queue_manifest_sha256
        )
    if sha256_file(paths["baseline_whitelist"]) != EXPECTED_BASELINE_SHA256:
        raise ValueError("deployed baseline SHA-256 differs from the pinned queue input")
    if sha256_file(paths["loc_surfaces"]) != EXPECTED_LOC_SURFACES_SHA256:
        raise ValueError("loc-surfaces SHA-256 differs from f2e079dc pin")
    if sha256_file(paths["v1_packets"]) != EXPECTED_V1_PACKET_SHA256:
        raise ValueError("v1 packet SHA-256 differs from 95788fab lineage pin")
    if args.batch == "wave-03" and sha256_file(paths["wave_02_packets"]) != EXPECTED_WAVE_02_PACKET_SHA256:
        raise ValueError("wave-02 packet SHA-256 differs from 9bd56a11 lineage pin")

    classifications = load_jsonl(paths["classification"])
    queue_rows = load_jsonl(paths["queue"])
    entry_rows = load_jsonl(paths["entries"])
    baseline_rows = load_jsonl(paths["baseline_whitelist"])
    loc_rows = load_jsonl(paths["loc_surfaces"])
    homograph_doc = load_json(paths["homograph_keys"])
    v1_packets = load_jsonl(paths["v1_packets"])
    wave_02_packets = load_jsonl(paths["wave_02_packets"]) if args.batch == "wave-03" else []
    classifications_by_loc = index_unique(classifications, "canonical_location", "classification")
    queue_by_loc = index_unique(queue_rows, "canonical_location", "queue")
    entries = index_unique(entry_rows, "id", "entry")
    v1_by_loc = index_unique(v1_packets, "canonical_location", "v1 packet")
    homograph_index: dict[str, list[tuple[int, dict[str, Any]]]] = collections.defaultdict(list)
    for index, row in enumerate(homograph_doc.get("keys") or [], 1):
        key = row.get("norm_key")
        if isinstance(key, str) and key:
            indexed_row = copy.deepcopy(row)
            indexed_row["__risk_flag__"] = homograph_doc.get("risk_flag")
            homograph_index[key].append((index, indexed_row))
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
    wave_mode = args.batch in {"wave-02", "wave-03"} or wave_four_mode
    wave_three_mode = args.batch == "wave-03"
    occurrence_mapping_quality: dict[str, bool] = {}
    lexical_mapping_quality: dict[str, tuple[int, int]] = {}
    if wave_mode:
        if wave_four_mode:
            wave_4_exclusions = load_wave_4_exclusions(
                paths[label] for label in paths if label.startswith("exclude_locations_")
            )
            excluded_locations = wave_4_exclusions.locations
            excluded_review_fact_ids = wave_4_exclusions.review_fact_ids
        else:
            excluded_locations = set(v1_by_loc)
            excluded_locations.update(packet["canonical_location"] for packet in wave_02_packets)
        for row in population:
            loc = row["canonical_location"]
            if loc in excluded_locations or (
                not wave_four_mode and ayah_of(loc) in NF_T10_1_AYAHS
            ):
                continue
            if row["laneb_classification"] == "competing_lexical_senses":
                entry_ids = row.get("evidence", {}).get("candidate_entry_ids", [])
                usage_count = sum(bool(entries.get(str(entry_id), {}).get("usage")) for entry_id in entry_ids)
                lexical_mapping_quality[loc] = (int(root_pair(row) is not None), usage_count)
                continue
            queue_row = queue_by_loc.get(loc)
            context = [
                {
                    "loc": item["loc"],
                    "surface": item["surface"],
                    "source_address": row_source(paths["loc_surfaces"], item, f"loc={item['loc']}"),
                }
                for item in loc_by_ayah.get(ayah_of(loc), [])
            ]
            uniquely_maps_target = False
            for carrier in (queue_row or {}).get("full_carrier_candidates") or []:
                entry = entries.get(str(carrier.get("entry_id")))
                if entry is None:
                    continue
                content = entry_content_for_carrier(carrier, entry, paths["entries"])
                mapping = build_occurrence_mapping(
                    carrier, content["matching_usage_examples"][0], context
                )
                if mapping["fingerprint_match_candidates"] == [loc]:
                    uniquely_maps_target = True
                    break
            occurrence_mapping_quality[loc] = uniquely_maps_target
        if wave_four_mode:
            selected = select_wave_4_rows(
                classifications,
                queue_by_loc=queue_by_loc,
                excluded_locations=excluded_locations,
                excluded_review_fact_ids=excluded_review_fact_ids,
                strata=load_wave_4_strata(paths["strata"]),
            )
        elif wave_three_mode:
            selected = select_proportional_lexicographic_rows(
                classifications,
                excluded_locations=excluded_locations,
            )
        else:
            selected = select_wave_rows(
                classifications,
                excluded_locations=excluded_locations,
                lexical_mapping_quality=lexical_mapping_quality,
                occurrence_mapping_quality=occurrence_mapping_quality,
            )
    else:
        selected = select_calibration_rows(classifications)
        selected_identity = [
            (rank, stratum, row["canonical_location"])
            for rank, (stratum, row) in enumerate(selected, 1)
        ]
        v1_identity = [
            (int(packet["selection_rank"]), packet["calibration_stratum"], packet["canonical_location"])
            for packet in sorted(v1_packets, key=lambda item: int(item["selection_rank"]))
        ]
        if selected_identity != v1_identity:
            raise ValueError("STOP: selected calibration rows differ from the pinned v1 packet lineage")

    packets: list[dict[str, Any]] = []
    for rank, (stratum, classification) in enumerate(selected, 1):
        loc = classification["canonical_location"]
        if loc not in classifications_by_loc or loc not in queue_by_loc or loc not in baseline_by_loc:
            raise ValueError(f"selected location lacks classification, queue, or live row: {loc}")
        live_row = choose_live_row(baseline_by_loc[loc], queue_by_loc[loc], loc)
        pinned_context = (v1_by_loc.get(loc) or {}).get("ayah_word_context") or []
        rebuilt_context = [
            {
                "loc": row["loc"],
                "surface": row["surface"],
                "source_address": row_source(paths["loc_surfaces"], row, f"loc={row['loc']}"),
            }
            for row in sorted(loc_by_ayah.get(ayah_of(loc), []), key=lambda item: loc_key(item["loc"]))
        ]
        if not wave_mode and pinned_context != rebuilt_context:
            raise ValueError(
                f"STOP: pinned v1 ayah_word_context is insufficient or differs from loc-surfaces at {loc}"
            )
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
            homograph_path=paths["homograph_keys"],
            homograph_index=homograph_index,
            gate_path=paths["grammar_gate_ssot"],
            gate_ssot=gate_ssot,
            packet_id_prefix=(
                "laneb-wave-04" if wave_four_mode else (
                    f"laneb-{args.batch}" if wave_mode else "laneb-cal-002"
                )
            ),
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
    packet_mapping_counts = dict(sorted(collections.Counter(
        packet["mapping_status"] for packet in packets
    ).items()))
    carrier_mapping_counts = dict(sorted(collections.Counter(
        carrier["mapping_status"]
        for packet in packets
        for carrier in packet["candidate_carriers"]
    ).items()))
    occurrence_packets = [
        packet for packet in packets
        if packet["calibration_stratum"].startswith("occurrence_")
        or packet["calibration_stratum"] == "unresolved_occurrence_ambiguity"
    ]
    gate_counts = dict(sorted(collections.Counter(
        packet["gate"]["tier"] for packet in packets
    ).items()))
    occurrence_mapping_counts = dict(sorted(collections.Counter(
        packet["mapping_status"] for packet in occurrence_packets
    ).items()))
    manifest = {
        "schema": "qamus.laneb_two_vote_calibration_manifest.v2",
        "generator": "tools/build_two_vote_packets.py",
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "scope": "packets_only_no_votes_no_conclusions_no_ledger_writes_no_crosswalk_writes",
        "lineage": {
            "parent_path": logical_path(paths["v1_packets"]),
            "parent_sha256": EXPECTED_V1_PACKET_SHA256,
            "same_rows_verified": True,
            "identity_fields": ["selection_rank", "calibration_stratum", "canonical_location"],
        },
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
                "v1_packets": v1_packets,
                "wave_02_packets": wave_02_packets,
            }.get(label))
            for label, path in paths.items()
        },
        "output": {
            "path": logical_path(Path(args.out)),
            "rows": len(packets),
            "sha256": hashlib.sha256(packet_bytes).hexdigest(),
            "stratum_counts": stratum_counts,
            "population_class_counts": class_counts,
            "packet_mapping_status_counts": packet_mapping_counts,
            "carrier_mapping_status_counts": carrier_mapping_counts,
            "gate_distribution": gate_counts,
            "occurrence_ambiguity_packet_mapping_status_counts": occurrence_mapping_counts,
            "occurrence_ambiguity_unique_with_fingerprints": sum(
                packet["mapping_status"] == "unique" for packet in occurrence_packets
            ),
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
                "pinned v1 ayah_word_context is insufficient or differs from loc-surfaces",
                "loc-surfaces SHA-256 differs from f2e079dc pin",
                "v1 packet SHA-256 differs from 95788fab lineage pin",
            ],
        },
    }
    if wave_mode:
        selected_occurrence = [
            row["canonical_location"] for label, row in selected
            if label == "unresolved_occurrence_ambiguity"
        ]
        residual_occurrence = [
            row["canonical_location"] for row in population
            if row["laneb_classification"] == "unresolved_occurrence_ambiguity"
            and row["canonical_location"] not in excluded_locations
            and (wave_four_mode or ayah_of(row["canonical_location"]) not in NF_T10_1_AYAHS)
            and row["canonical_location"] not in set(selected_occurrence)
        ]
        def unique_rate(locations: list[str]) -> float:
            return sum(occurrence_mapping_quality.get(loc, False) for loc in locations) / len(locations) if locations else 0.0
        manifest.update({
            "schema": "qamus.laneb_two_vote_wave_manifest.v1",
            "authoritative_baseline_sha": (
                WAVE_03_AUTHORITATIVE_BASELINE_SHA
                if wave_four_mode
                else baseline_by_batch[args.batch]
            ),
        })
        if wave_four_mode:
            strata = load_wave_4_strata(paths["strata"])
            manifest["lineage"] = {
                "queue_manifest_required_sha256": args.queue_manifest_sha256,
                "excluded_by": "canonical_location",
                "exclude_location_inputs": [
                    input_pin(paths[label])
                    for label in paths if label.startswith("exclude_locations_")
                ],
                "excluded_unique_locations": len(excluded_locations),
                "excluded_promoted_review_fact_ids": len(excluded_review_fact_ids),
            }
            manifest["selection_rule"] = {
                "purpose": "membership_selection_only_never_semantic_adjudication",
                "pure_function": True,
                "randomness": "none",
                "wall_clock_inputs": "none",
                "batch_size": 250,
                "strata_input": input_pin(paths["strata"]),
                "stratum_counts": strata,
                "excluded_previously_packeted_and_quarantined_locations": len(excluded_locations),
                "allocation": "Caller-supplied post-repair residual class counts; tooling requires an exact 250-row total.",
                "within_stratum": "Canonical location numeric ascending.",
                "underfill": "STOP if any caller-supplied stratum cannot be filled.",
                "output_order": "Class name ascending, then canonical location numeric ascending; selection_rank 1..250.",
            }
        elif wave_three_mode:
            eligible_counts = dict(sorted(collections.Counter(
                row["laneb_classification"] for row in population
                if row["canonical_location"] not in excluded_locations
                and ayah_of(row["canonical_location"]) not in NF_T10_1_AYAHS
            ).items()))
            manifest["lineage"] = {
                "excluded_by": "canonical_location",
                "excluded_calibration": {
                    "path": logical_path(paths["v1_packets"]),
                    "rows": len(v1_packets),
                    "sha256": EXPECTED_V1_PACKET_SHA256,
                },
                "excluded_wave_02": {
                    "path": logical_path(paths["wave_02_packets"]),
                    "rows": len(wave_02_packets),
                    "sha256": EXPECTED_WAVE_02_PACKET_SHA256,
                },
                "excluded_unique_locations": len(excluded_locations),
            }
            manifest["population"].update({
                "eligible_after_exclusions": sum(eligible_counts.values()),
                "eligible_after_exclusions_class_counts": eligible_counts,
            })
            manifest["selection_rule"] = {
                "purpose": "membership_selection_only_never_semantic_adjudication",
                "pure_function": True,
                "randomness": "none",
                "wall_clock_inputs": "none",
                "batch_size": 500,
                "excluded_ayahs": sorted(NF_T10_1_AYAHS, key=lambda value: tuple(map(int, value.split(":")))),
                "excluded_previously_packeted_locations": len(excluded_locations),
                "allocation": "Largest-remainder proportional allocation over the two remaining class populations; ties break by class name ascending.",
                "competing_lexical_senses": "Take the first 179 eligible canonical_location strings in ascending lexicographic order.",
                "unresolved_occurrence_ambiguity": "Take the first 321 eligible canonical_location strings in ascending lexicographic order.",
                "underfill": "STOP if fewer than 500 eligible rows remain.",
                "output_order": "competing_lexical_senses then unresolved_occurrence_ambiguity; lexicographic canonical_location order within each stratum; selection_rank 1..500.",
            }
        else:
            manifest["lineage"] = {
                "excluded_calibration_path": logical_path(paths["v1_packets"]),
                "excluded_calibration_sha256": EXPECTED_V1_PACKET_SHA256,
                "excluded_by": "canonical_location",
            }
            manifest["selection_rule"] = {
                "purpose": "membership_selection_only_never_semantic_adjudication",
                "pure_function": True,
                "randomness": "none",
                "wall_clock_inputs": "none",
                "excluded_ayahs": sorted(NF_T10_1_AYAHS, key=lambda value: tuple(map(int, value.split(":")))),
                "excluded_calibration_locations": len(v1_by_loc),
                "competing_lexical_senses": "Lexicographic score: distinct two-root pair first, then count of candidate entries carrying usage evidence descending, root-pair text ascending, canonical location numeric ascending; take exactly 90.",
                "unresolved_occurrence_ambiguity": "Run the existing fingerprint mapper for every eligible row; unique target-addressing carrier first, then canonical location numeric ascending; take exactly 160.",
                "underfill": "STOP if either exact stratum cannot be filled.",
                "output_order": "90 competing_lexical_senses then 160 unresolved_occurrence_ambiguity; intrinsic score order; selection_rank 1..250.",
            }
        manifest["output"].update({
            "selected_occurrence_unique_mapping_rate": unique_rate(selected_occurrence),
            "selected_occurrence_unique_mapping_rows": sum(occurrence_mapping_quality.get(loc, False) for loc in selected_occurrence),
            "residual_occurrence_rows": len(residual_occurrence),
            "residual_occurrence_unique_mapping_rate": unique_rate(residual_occurrence),
            "residual_occurrence_unique_mapping_rows": sum(occurrence_mapping_quality.get(loc, False) for loc in residual_occurrence),
        })
        manifest["validation"]["rebuild"] = (
            "python tools/build_two_vote_packets.py --wave 4 <required inputs>"
            if wave_four_mode
            else f"python tools/build_two_vote_packets.py --batch {args.batch}"
        )
        manifest["validation"]["stop_conditions"].append(
            "a caller-supplied wave-4 stratum cannot be filled"
            if wave_four_mode
            else (
                "fewer than 500 eligible rows remain"
                if wave_three_mode
                else "fewer than 90 lexical or 160 occurrence rows remain eligible"
            )
        )
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
    with tempfile.TemporaryDirectory() as temp_dir:
        fixture_dir = Path(temp_dir)
        fixture_queue = fixture_dir / "queue.jsonl"
        fixture_manifest = fixture_dir / "queue.manifest.json"
        fixture_queue.write_text('{"canonical_location":"2:1:1"}\n', encoding="utf-8")
        fixture_manifest.write_text(
            json.dumps({"queue_sha256": sha256_file(fixture_queue)}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            verify_wave_4_queue_pin(
                fixture_queue,
                fixture_manifest,
                "0" * 64,
            )
        except ValueError as exc:
            if "STOP" not in str(exc) or "queue manifest SHA-256" not in str(exc):
                failures.append("wave-4 wrong queue-manifest pin lacked the required STOP reason")
        else:
            failures.append("wave-4 accepted a queue manifest outside the required SHA pin")
        accepted_pin = sha256_file(fixture_manifest)
        verify_wave_4_queue_pin(fixture_queue, fixture_manifest, accepted_pin)
        fixture_queue.write_text('{"canonical_location":"2:1:2"}\n', encoding="utf-8")
        try:
            verify_wave_4_queue_pin(fixture_queue, fixture_manifest, accepted_pin)
        except ValueError as exc:
            if "STOP" not in str(exc) or "queue SHA-256" not in str(exc):
                failures.append("wave-4 stale queue bytes lacked the required STOP reason")
        else:
            failures.append("wave-4 accepted queue bytes outside the pinned manifest state")
        strata_path = fixture_dir / "strata.json"
        strata_path.write_text(
            json.dumps(
                {
                    "competing_lexical_senses": 249,
                    "unresolved_occurrence_ambiguity": 1,
                }
            ),
            encoding="utf-8",
        )
        if load_wave_4_strata(strata_path) != {
            "competing_lexical_senses": 249,
            "unresolved_occurrence_ambiguity": 1,
        }:
            failures.append("wave-4 strata were not loaded from the caller-owned input")
        prior_packets = fixture_dir / "prior.jsonl"
        quarantine = fixture_dir / "quarantine.json"
        prior_packets.write_text('{"canonical_location":"2:1:1"}\n', encoding="utf-8")
        quarantine.write_text(json.dumps({"locations": ["2:1:2"]}), encoding="utf-8")
        if load_excluded_locations([prior_packets, quarantine]) != {"2:1:1", "2:1:2"}:
            failures.append("wave-4 did not combine parameterized prior-packet and quarantine lists")
    repeated_window = [
        {"loc": f"2:1:{index}", "surface": surface, "source_address": f"fixture#loc={index}"}
        for index, surface in enumerate(
            ["قَبْلَ", "قَبْلَ", "عَلَىٰ", "بَعْدَ", "بَعْدَ"] * 2,
            1,
        )
    ]
    ambiguous_mapping = build_occurrence_mapping(
        {"qword_row_id": "llx-qword-fixture-01-01-003"},
        {
            "content": {"ar": "قَبْلَ قَبْلَ عَلَىٰ بَعْدَ بَعْدَ", "ref": "2:1"},
            "source_address": "fixture#usage/1/examples/1",
        },
        repeated_window,
    )
    if ambiguous_mapping["mapping_status"] != "ambiguous":
        failures.append("repeated verbatim example window was not marked ambiguous")
    if ambiguous_mapping["fingerprint_match_candidates"] != ["2:1:3", "2:1:8"]:
        failures.append("ambiguous mapping did not preserve both matching positions")
    reordered_mapping = build_occurrence_mapping(
        {"qword_row_id": "llx-qword-fixture-01-01-003"},
        {
            "content": {"ar": "قَبْلَ قَبْلَ عَلَىٰ بَعْدَ بَعْدَ", "ref": "2:1"},
            "source_address": "fixture#usage/1/examples/1",
        },
        reversed(repeated_window),
    )
    if canonical_bytes(ambiguous_mapping) != canonical_bytes(reordered_mapping):
        failures.append("occurrence mapping changed under context reordering")
    morphology = build_morphology_record(
        target_loc="2:1:1",
        target_surface="وَكِتَابٌ",
        target_source_address="fixture#loc=2:1:1",
        carriers=[{"entry_id": "entry-a", "card_id": "entry-a:u1:e1"}],
        entries={
            "entry-a": {
                "id": "entry-a",
                "headword": "كِتَاب",
                "root": "ك ت ب",
                "section": "noun",
                "usage": [{"forms": ["كِتَابٌ"], "examples": [{"ref": "2:1"}]}],
            }
        },
        entries_path=DEFAULT_ENTRIES,
        homograph_index={},
        homograph_path=ROOT / "qamus/indexes/largelexicon/homograph-keys.json",
    )
    lexical = morphology.get("lemma_root_pos_candidates", {})
    if not lexical.get("available") or not lexical.get("candidates"):
        failures.append("documented usage form did not produce a morphology candidate")
    elif any(
        not field.get("source_address")
        for field in lexical["candidates"][0].values()
        if isinstance(field, dict) and "value" in field
    ):
        failures.append("morphology candidate field lacks a source address")
    homograph_row = {
        "__risk_flag__": "norm_homograph",
        "norm_key": norm("وَكِتَابٌ"),
        "root_count": 2,
        "roots": ["ك ت ب", "و ك ب"],
    }
    homograph_a = build_morphology_record(
        target_loc="2:1:1",
        target_surface="وَكِتَابٌ",
        target_source_address="fixture#loc=2:1:1",
        carriers=[],
        entries={},
        entries_path=DEFAULT_ENTRIES,
        homograph_index={norm("وَكِتَابٌ"): [(1, homograph_row)]},
        homograph_path=DEFAULT_HOMOGRAPH_KEYS,
    )
    homograph_b = build_morphology_record(
        target_loc="2:1:1",
        target_surface="وَكِتَابٌ",
        target_source_address="fixture#loc=2:1:1",
        carriers=[],
        entries={},
        entries_path=DEFAULT_ENTRIES,
        homograph_index={norm("وَكِتَابٌ"): [(99, homograph_row)]},
        homograph_path=DEFAULT_HOMOGRAPH_KEYS,
    )
    if canonical_bytes(homograph_a) != canonical_bytes(homograph_b):
        failures.append("homograph morphology changed under input row reordering")
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
    missing_enrichment = copy.deepcopy(missing_gate)
    missing_enrichment["gate"] = {"tier": "two_vote_required"}
    missing_enrichment["required_response_schema"] = {
        "required": RESPONSE_FIELDS,
        "properties": {
            "gate": {"const": "two_vote_required"},
            "evidence_hashes": {"const": {}},
        },
    }
    for label, packet in (
        ("missing candidate content", missing_candidate_content),
        ("missing gate", missing_gate),
        ("missing v2 enrichment", missing_enrichment),
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
    calibration_locs = {"3:1:1", "5:1:1"}
    wave_forward = select_wave_rows(
        synthetic,
        excluded_locations=calibration_locs,
        lexical_mapping_quality={"4:1:1": (2, 2)},
        occurrence_mapping_quality={"6:1:1": True, "7:1:1": False},
        lexical_count=1,
        occurrence_count=1,
    )
    wave_reverse = select_wave_rows(
        reversed(synthetic),
        excluded_locations=calibration_locs,
        lexical_mapping_quality={"4:1:1": (2, 2)},
        occurrence_mapping_quality={"6:1:1": True, "7:1:1": False},
        lexical_count=1,
        occurrence_count=1,
    )
    if projection(wave_forward) != projection(wave_reverse):
        failures.append("wave selection changed under input reordering")
    if projection(wave_forward) != [
        ("competing_lexical_senses", "4:1:1"),
        ("unresolved_occurrence_ambiguity", "6:1:1"),
    ]:
        failures.append("wave selection did not honor exclusions and mapping preference")
    proportional_fixture = [
        _synthetic_classification(loc, classification, 2, ("a", "b"), None)
        for classification, locations in (
            ("competing_lexical_senses", ["9:1:1", "10:1:1", "2:1:1", "3:1:1"]),
            (
                "unresolved_occurrence_ambiguity",
                ["8:1:1", "11:1:1", "4:1:1", "5:1:1", "6:1:1", "7:1:1"],
            ),
        )
        for loc in locations
    ]
    wave_three_forward = select_proportional_lexicographic_rows(
        proportional_fixture,
        excluded_locations={"2:1:1"},
        batch_size=5,
    )
    wave_three_reverse = select_proportional_lexicographic_rows(
        reversed(proportional_fixture),
        excluded_locations={"2:1:1"},
        batch_size=5,
    )
    if projection(wave_three_forward) != projection(wave_three_reverse):
        failures.append("proportional lexicographic selection changed under input reordering")
    if projection(wave_three_forward) != [
        ("competing_lexical_senses", "10:1:1"),
        ("competing_lexical_senses", "3:1:1"),
        ("unresolved_occurrence_ambiguity", "11:1:1"),
        ("unresolved_occurrence_ambiguity", "4:1:1"),
        ("unresolved_occurrence_ambiguity", "5:1:1"),
    ]:
        failures.append("wave-3 selection did not preserve exact proportional strata and lexicographic order")
    try:
        select_wave_rows(
            synthetic,
            excluded_locations={row["canonical_location"] for row in synthetic},
            lexical_mapping_quality={},
            occurrence_mapping_quality={},
            lexical_count=1,
            occurrence_count=1,
        )
    except ValueError as exc:
        if "STOP" not in str(exc) or "underfill" not in str(exc):
            failures.append("wave underfill did not emit the required STOP reason")
    else:
        failures.append("wave selection accepted underfill")
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
    print("SELFTESTS=20 FAILURES=0")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--classification", default=DEFAULT_CLASSIFICATION)
    result.add_argument("--queue", default=DEFAULT_QUEUE)
    result.add_argument("--entries", default=DEFAULT_ENTRIES)
    result.add_argument("--baseline", default=DEFAULT_BASELINE)
    result.add_argument("--loc-surfaces", default=DEFAULT_LOC_SURFACES)
    result.add_argument("--homograph-keys", default=DEFAULT_HOMOGRAPH_KEYS)
    result.add_argument("--v1-packets", default=DEFAULT_V1_PACKETS)
    result.add_argument("--wave-02-packets", default=DEFAULT_WAVE_02_PACKETS)
    result.add_argument("--wave", type=int, choices=(4,))
    result.add_argument("--queue-manifest")
    result.add_argument("--queue-manifest-sha256")
    result.add_argument("--strata")
    result.add_argument("--exclude-locations", action="append", default=[])
    result.add_argument("--gates", default=DEFAULT_GATES)
    result.add_argument("--fact-schema", default=DEFAULT_FACT_SCHEMA)
    result.add_argument("--out", default=DEFAULT_OUT)
    result.add_argument("--manifest", default=DEFAULT_MANIFEST)
    result.add_argument("--self-test", action="store_true")
    result.add_argument("--batch", choices=("calibration", "wave-02", "wave-03"), default="calibration")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        return self_test()
    if args.wave == 4:
        if args.batch != "calibration":
            raise ValueError("STOP: --wave 4 cannot be combined with --batch")
        required = {
            "--queue-manifest": args.queue_manifest,
            "--queue-manifest-sha256": args.queue_manifest_sha256,
            "--strata": args.strata,
            "--exclude-locations": args.exclude_locations,
        }
        missing = [flag for flag, value in required.items() if not value]
        if missing:
            raise ValueError("STOP: --wave 4 requires " + ", ".join(missing))
        if Path(args.out) == DEFAULT_OUT or Path(args.manifest) == DEFAULT_MANIFEST:
            raise ValueError("STOP: --wave 4 requires explicit --out and --manifest paths")
    if args.batch == "wave-02" and Path(args.out) == DEFAULT_OUT:
        args.out = DEFAULT_WAVE_OUT
    if args.batch == "wave-02" and Path(args.manifest) == DEFAULT_MANIFEST:
        args.manifest = DEFAULT_WAVE_MANIFEST
    if args.batch == "wave-03" and Path(args.out) == DEFAULT_OUT:
        args.out = DEFAULT_WAVE_03_OUT
    if args.batch == "wave-03" and Path(args.manifest) == DEFAULT_MANIFEST:
        args.manifest = DEFAULT_WAVE_03_MANIFEST
    manifest, packets = build(args)
    write_outputs(manifest, packets, Path(args.out), Path(args.manifest))
    print(json.dumps(manifest["output"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
