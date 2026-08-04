#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic, fail-closed FUSHA-BENCH v1 authority-integrity baseline.

The first version measures four axes independently.  It does not emit an
aggregate score, certify a fact, author Arabic, or write unless ``--write`` is
explicit.  Geometry and structured-hover gold are admitted only through the
canonical typed-fact certification store's effective state.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_corpus_fact_projection_batch as geometry_builder  # noqa: E402
from tools import fusha_tutor_runtime as tutor_runtime  # noqa: E402
from tools import leak_sot  # noqa: E402
from tools import validate_p007_pilot as pilot_validator  # noqa: E402
from tools.certify_typed_fact import TypedFactCertificationStore  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA = "fusha.bench_report.v1"
MANIFEST_SCHEMA = "fusha.bench_data_manifest.v1"
MODEL_CARD_SCHEMA = "fusha.bench_model_card.v1"
QUARANTINE_SCHEMA = "fusha.bench_tutor_quarantine.v1"
BENCHMARK_ID = "fusha-bench-v1"

DEFAULT_MANIFEST = ROOT / "eval" / "fusha-bench-v1" / "data-manifest.json"
DEFAULT_MODEL_CARD = ROOT / "eval" / "fusha-bench-v1" / "model-card.json"
DEFAULT_QUARANTINE = ROOT / "eval" / "fusha-bench-v1" / "tutor-quarantine.json"
DEFAULT_REPORT = ROOT / "eval" / "fusha-bench-v1" / "report" / "fusha-bench-report.json"

_QURAN_OCCURRENCE_RE = re.compile(r"^quran:\d+:\d+:\d+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AGGREGATE_KEYS = {"aggregate_score", "overall_score", "combined_score", "total_score"}


class BenchError(ValueError):
    """Raised when benchmark authority, isolation, or freshness fails closed."""


def read_json(path: os.PathLike[str] | str):
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise BenchError(f"{path}: top level must be an object")
    return value


def read_json_array(path: os.PathLike[str] | str):
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise BenchError(f"{path}: top level must be an array")
    if any(not isinstance(row, dict) for row in value):
        raise BenchError(f"{path}: every array row must be an object")
    return value


def read_jsonl(path: os.PathLike[str] | str):
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise BenchError(f"{path}:{line_number}: blank JSONL line")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BenchError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise BenchError(f"{path}:{line_number}: row must be an object")
            rows.append(row)
    return rows


def _pretty_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(root: os.PathLike[str] | str, path: os.PathLike[str] | str):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    root_path = Path(root).resolve()
    resolved = (root_path / candidate).resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise BenchError(f"artifact path escapes repository root: {path}") from exc
    return resolved


def contains_aggregate_score(value):
    if isinstance(value, dict):
        if any(str(key).lower() in _AGGREGATE_KEYS for key in value):
            return True
        return any(contains_aggregate_score(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_aggregate_score(item) for item in value)
    return False


def ensure_source_clean(value):
    hits = leak_sot.scan_obj(value)
    if hits:
        raise BenchError("source-boundary leak in benchmark output")


def _artifact_map(manifest):
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BenchError("manifest requires a non-empty artifacts list")
    result = {}
    paths = set()
    for row in artifacts:
        if not isinstance(row, dict):
            raise BenchError("manifest artifact rows must be objects")
        artifact_id = row.get("artifact_id")
        path = row.get("path")
        digest = row.get("sha256")
        role = row.get("role")
        if not all(isinstance(item, str) and item for item in (artifact_id, path, role)):
            raise BenchError("manifest artifact requires artifact_id, path, and role")
        if artifact_id in result:
            raise BenchError(f"duplicate artifact_id: {artifact_id}")
        if path in paths:
            raise BenchError(f"duplicate artifact path: {path}")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise BenchError(f"artifact {artifact_id} requires lowercase sha256")
        result[artifact_id] = row
        paths.add(path)
    return result


def axis_gold_artifact_ids(manifest):
    result = set()
    for axis in (manifest.get("axes") or {}).values():
        if isinstance(axis, dict):
            ids = axis.get("gold_artifact_ids") or []
            if not isinstance(ids, list):
                raise BenchError("gold_artifact_ids must be a list")
            result.update(ids)
    return result


def validate_manifest(manifest, *, root=ROOT):
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise BenchError(f"manifest schema must be {MANIFEST_SCHEMA}")
    if manifest.get("benchmark_id") != BENCHMARK_ID:
        raise BenchError(f"manifest benchmark_id must be {BENCHMARK_ID}")
    if contains_aggregate_score(manifest):
        raise BenchError("aggregate benchmark scores are forbidden")
    if manifest.get("aggregate_score_allowed") is not False:
        raise BenchError("manifest must set aggregate_score_allowed false")

    artifacts = _artifact_map(manifest)
    canary_ids = manifest.get("safety_canary_artifact_ids")
    if not isinstance(canary_ids, list) or not canary_ids:
        raise BenchError("manifest requires safety canary artifact ids")
    missing_canaries = sorted(set(canary_ids) - set(artifacts))
    if missing_canaries:
        raise BenchError("unknown safety canary artifacts: " + ", ".join(missing_canaries))
    if any(artifacts[item].get("role") != "safety_canary" for item in canary_ids):
        raise BenchError("every safety canary artifact must have role safety_canary")
    if set(canary_ids) & axis_gold_artifact_ids(manifest):
        raise BenchError("a safety canary may never be a gold artifact")

    axes = manifest.get("axes")
    expected_axes = {
        "ownership_geometry", "structured_hover", "contextual_translation", "tutor"
    }
    if not isinstance(axes, dict) or set(axes) != expected_axes:
        raise BenchError("manifest must define exactly the four FUSHA-BENCH v1 axes")
    for name in ("ownership_geometry", "structured_hover"):
        if axes[name].get("identity_join") != "exact_quran_occurrence_id":
            raise BenchError(f"{name} identity_join must be exact_quran_occurrence_id")
    translation = axes["contextual_translation"]
    if translation.get("status") != "not_scored_no_certified_gold" \
            or translation.get("denominator") != 0 \
            or translation.get("gold_artifact_ids") != []:
        raise BenchError("contextual translation has no certified translation gold")

    referenced = axis_gold_artifact_ids(manifest) | set(canary_ids)
    tutor = axes["tutor"]
    referenced.update(tutor.get("excluded_input_artifact_ids") or [])
    runtime_artifact_id = tutor.get("runtime_artifact_id")
    if not isinstance(runtime_artifact_id, str) or not runtime_artifact_id:
        raise BenchError("tutor axis requires a pinned ordinary runtime artifact")
    referenced.add(runtime_artifact_id)
    unknown = sorted(referenced - set(artifacts))
    if unknown:
        raise BenchError("axis references unknown artifacts: " + ", ".join(unknown))
    if artifacts[runtime_artifact_id].get("role") != "tutor_runtime_consumer":
        raise BenchError("tutor runtime artifact has the wrong role")

    for artifact_id, row in artifacts.items():
        path = _resolve(root, row["path"])
        if not path.is_file():
            raise BenchError(f"artifact missing: {artifact_id} ({row['path']})")
        found = _sha256_file(path)
        if found != row["sha256"]:
            raise BenchError(
                f"artifact {artifact_id} sha256 mismatch: found {found}, expected {row['sha256']}"
            )
    return artifacts


def _quran_addresses(fact):
    addresses = set()
    for item in (fact.get("dependencies") or {}).get("source_addresses") or []:
        address = item.get("address") if isinstance(item, dict) else None
        if isinstance(address, str) and address.startswith("quran:"):
            addresses.add(address)
    for span in fact.get("surface_spans") or []:
        loc = span.get("quran_loc") if isinstance(span, dict) else None
        if isinstance(loc, str):
            addresses.add(loc)
    return addresses


def validate_certified_fact(fact):
    fact_id = fact.get("fact_id") or "<missing-fact-id>"
    if not fact.get("fact_id") or not fact.get("fact_type"):
        raise BenchError("certified fact requires fact_id and fact_type")
    blockers = fact.get("unresolved_blockers")
    if not isinstance(blockers, list) or blockers:
        raise BenchError(f"{fact_id}: certified fact has unresolved blockers")
    rivals = fact.get("contradiction_records")
    if not isinstance(rivals, list):
        raise BenchError(f"{fact_id}: contradiction_records must be a list")
    if any(not isinstance(row, dict) or row.get("status") not in {"resolved", "rejected"}
           for row in rivals):
        raise BenchError(f"{fact_id}: certified fact has an unresolved rival")

    spans = fact.get("surface_spans")
    if not isinstance(spans, list) or not spans:
        raise BenchError(f"{fact_id}: certified fact requires exact surface spans")
    for span in spans:
        if not isinstance(span, dict):
            raise BenchError(f"{fact_id}: surface span must be an object")
        loc = str(span.get("quran_loc") or "")
        entry_scoped = fact.get("fact_type") == "particle_rootlessness" \
            and isinstance(span.get("entry_id"), str) and bool(span["entry_id"])
        if not _QURAN_OCCURRENCE_RE.fullmatch(loc) and not entry_scoped:
            raise BenchError(f"{fact_id}: surface span requires exact quran occurrence identity")
        if not isinstance(span.get("surface"), str) or not span["surface"]:
            raise BenchError(f"{fact_id}: surface span requires written surface")

    fact_type = fact["fact_type"]
    value = fact.get("fact_value")
    if not isinstance(value, dict):
        raise BenchError(f"{fact_id}: fact_value must be an object")
    if fact_type == "attachment_geometry":
        surface = unicodedata.normalize("NFC", value.get("surface_nfc") or "")
        component = unicodedata.normalize("NFC", value.get("component_surface") or "")
        span = value.get("char_span") or {}
        start, end = span.get("start"), span.get("end")
        if start != 0 or not isinstance(end, int) or not 0 < end < len(surface):
            raise BenchError(f"{fact_id}: attachment char span is not a proper prefix")
        if surface[start:end] != component:
            raise BenchError(f"{fact_id}: attachment char span does not slice component surface")
    elif fact_type == "surface_reconstruction_nfc":
        if value.get("nfc_identity") is not True:
            raise BenchError(f"{fact_id}: reconstruction does not assert NFC identity")
        if unicodedata.normalize("NFC", (value.get("clitic") or "") +
                                     (value.get("remainder") or "")) != \
                unicodedata.normalize("NFC", value.get("surface_nfc") or ""):
            raise BenchError(f"{fact_id}: reconstruction does not rebuild written surface")
    elif fact_type in {"contextual_function", "governor_relation", "case_mood_governor"}:
        if not isinstance(value.get("reason_key"), str) or not value["reason_key"].strip():
            raise BenchError(f"{fact_id}: certified contextual fact requires reason_key")

    addresses = _quran_addresses(fact)
    if not addresses or any(not _QURAN_OCCURRENCE_RE.fullmatch(item) for item in addresses):
        raise BenchError(f"{fact_id}: no exact Qurʾānic occurrence address")


def load_effective_certified_facts(*, root, store_dir, claims_path, allowed_fact_types):
    store_path = _resolve(root, store_dir)
    claims = read_jsonl(_resolve(root, claims_path))
    store = TypedFactCertificationStore(store_path)
    trail_errors = store.validate_trail()
    if trail_errors:
        raise BenchError("canonical certification trail invalid: " + "; ".join(trail_errors[:5]))
    state = store.state()
    statuses = store.status_by_id()
    certified_ids = {fact_id for fact_id, status in statuses.items() if status == "certified"}
    claims_by_id = {row.get("fact_id"): row for row in claims}
    if None in claims_by_id or len(claims_by_id) != len(claims):
        raise BenchError("claims require unique non-empty fact ids")
    if set(claims_by_id) != certified_ids:
        raise BenchError("claims must equal the exact effective certified fact set")
    facts = []
    for fact_id in sorted(certified_ids):
        claim = claims_by_id[fact_id]
        effective = (state.get(fact_id) or {}).get("fact")
        if claim != effective:
            raise BenchError(f"{fact_id}: claim differs from append-only effective fact payload")
        if claim.get("fact_type") not in allowed_fact_types:
            raise BenchError(f"{fact_id}: fact type is outside benchmark axis scope")
        validate_certified_fact(claim)
        facts.append(claim)
    return facts, statuses


def _ids_from_artifact(path):
    rows = read_jsonl(path)
    ids = set()
    for row in rows:
        item_id = row.get("id") or row.get("drill_id")
        if not isinstance(item_id, str) or not item_id:
            raise BenchError(f"{path}: authoring/runtime row lacks stable id")
        if item_id in ids:
            raise BenchError(f"{path}: duplicate stable id {item_id}")
        ids.add(item_id)
    return ids


def ensure_no_quarantine_overlap(probe_ids, input_id_sets):
    for source, input_ids in input_id_sets.items():
        overlap = sorted(set(probe_ids) & set(input_ids))
        if overlap:
            raise BenchError(
                f"tutor quarantine overlap with {source}: " + ", ".join(overlap[:5])
            )


def _validate_model_card(model_card):
    if model_card.get("schema") != MODEL_CARD_SCHEMA \
            or model_card.get("benchmark_id") != BENCHMARK_ID:
        raise BenchError("invalid FUSHA-BENCH model card")
    if contains_aggregate_score(model_card):
        raise BenchError("model card may not define an aggregate score")
    ensure_source_clean(model_card)


def _validate_quarantine(root, manifest, quarantine, artifacts):
    if quarantine.get("schema") != QUARANTINE_SCHEMA \
            or quarantine.get("benchmark_id") != BENCHMARK_ID:
        raise BenchError("invalid tutor quarantine manifest")
    probe_ids = quarantine.get("probe_ids")
    if not isinstance(probe_ids, list) or len(probe_ids) != 16 \
            or len(set(probe_ids)) != len(probe_ids):
        raise BenchError("tutor quarantine must contain exactly 16 unique probe ids")
    tutor = manifest["axes"]["tutor"]
    source_id = tutor.get("probe_artifact_id")
    source_rows = read_jsonl(_resolve(root, artifacts[source_id]["path"]))
    source_ids = {row.get("id") for row in source_rows}
    if set(probe_ids) != source_ids:
        raise BenchError("tutor quarantine ids do not equal the frozen placement probes")
    if quarantine.get("excluded_input_artifact_ids") != tutor.get("excluded_input_artifact_ids"):
        raise BenchError("tutor quarantine exclusion inventory differs from data manifest")
    input_sets = {}
    for artifact_id in quarantine["excluded_input_artifact_ids"]:
        role = artifacts[artifact_id].get("role")
        if role not in {"drill_authoring_input", "runtime_drill_input"}:
            raise BenchError(f"{artifact_id}: invalid tutor exclusion role")
        input_sets[artifact_id] = _ids_from_artifact(
            _resolve(root, artifacts[artifact_id]["path"])
        )
    ensure_no_quarantine_overlap(set(probe_ids), input_sets)
    return probe_ids, source_rows


def replay_tutor_probes(rows):
    """Replay frozen placement probes through the ordinary tutor grader.

    This scores runtime contract behavior, not learner ability.  Every probe
    must accept its authored answer and variants with the required reasoning,
    reject every forbidden answer, enforce the reason gate, and hold any
    two-vote row even when a caller self-declares agreement.
    """
    if not isinstance(rows, list) or not rows:
        raise BenchError("tutor runtime replay requires probe rows")
    seen = set()
    accepted_forms_checked = 0
    forbidden_answers_rejected = 0
    required_reason_gates_enforced = 0
    two_vote_rows_held = 0
    probe_passes = 0

    for row in rows:
        probe_id = row.get("id") if isinstance(row, dict) else None
        if not isinstance(probe_id, str) or not probe_id or probe_id in seen:
            raise BenchError("tutor runtime replay requires unique stable probe ids")
        seen.add(probe_id)
        expected = row.get("expected_answer")
        variants = row.get("accepted_variants")
        forbidden = row.get("forbidden_answers")
        reasons = row.get("required_reasoning")
        if not isinstance(expected, str) or not expected.strip():
            raise BenchError(f"{probe_id}: requires an expected answer")
        if not isinstance(variants, list) or any(not isinstance(v, str) or not v for v in variants):
            raise BenchError(f"{probe_id}: invalid accepted variants")
        if not isinstance(forbidden, list) or not forbidden \
                or any(not isinstance(v, str) or not v for v in forbidden):
            raise BenchError(f"{probe_id}: requires forbidden answers")
        if not isinstance(reasons, list) or not reasons \
                or any(not isinstance(v, str) or not v for v in reasons):
            raise BenchError(f"{probe_id}: requires reasoning gates")

        for answer in [expected] + variants:
            grade = tutor_runtime.grade(row, {"answer": answer, "reasoning": reasons})
            if not grade["content_mastered"] or grade["forbidden_hit"]:
                raise BenchError(f"{probe_id}: authored accepted form failed ordinary tutor runtime")
            if row.get("two_vote_required"):
                if grade["cleared"] or not grade["held_for_fact_gate"] \
                        or grade["two_vote_status"] != "pending":
                    raise BenchError(f"{probe_id}: two-vote probe was not held")
            elif not grade["cleared"] or grade["held_for_fact_gate"]:
                raise BenchError(f"{probe_id}: auto-safe probe did not clear")
            accepted_forms_checked += 1

        for answer in forbidden:
            grade = tutor_runtime.grade(row, {"answer": answer, "reasoning": reasons})
            if grade["content_mastered"] or not grade["forbidden_hit"]:
                raise BenchError(f"{probe_id}: forbidden answer was not rejected")
            forbidden_answers_rejected += 1

        no_reason = tutor_runtime.grade(row, {"answer": expected, "reasoning": []})
        if no_reason["content_mastered"] or no_reason["reasoning_passed"]:
            raise BenchError(f"{probe_id}: missing required reasoning was accepted")
        required_reason_gates_enforced += 1

        if row.get("two_vote_required"):
            declared = tutor_runtime.grade(
                row,
                {
                    "answer": expected,
                    "reasoning": reasons,
                    "second_check": {"conclusion_agrees": True, "reason_agrees": True},
                },
            )
            if declared["cleared"] or not declared["held_for_fact_gate"] \
                    or declared["second_check_declared"] is not True:
                raise BenchError(f"{probe_id}: self-declared two-vote evidence cleared the fact gate")
            two_vote_rows_held += 1
        probe_passes += 1

    return {
        "probe_passes": probe_passes,
        "expected_answers_accepted": probe_passes,
        "accepted_forms_checked": accepted_forms_checked,
        "forbidden_answers_rejected": forbidden_answers_rejected,
        "required_reason_gates_enforced": required_reason_gates_enforced,
        "two_vote_rows_held": two_vote_rows_held,
    }


def analyze_hover_projection_parity(projections, reverse_trace, certified_facts):
    """Derive appearance totals and prove every projection renders its exact facts."""
    if not projections or not reverse_trace or not certified_facts:
        raise BenchError("structured-hover projection/fact parity requires non-empty inputs")
    projection_by_occurrence = {}
    appearance_ids = set()
    appearance_count = 0
    for row in projections:
        projection = row.get("projection") or {}
        occurrence_id = projection.get("occurrence_id")
        projection_hash = row.get("projection_hash")
        if not isinstance(occurrence_id, str) or not _QURAN_OCCURRENCE_RE.fullmatch(occurrence_id):
            raise BenchError("projection lacks exact quran occurrence identity")
        if occurrence_id in projection_by_occurrence:
            raise BenchError(f"duplicate projection occurrence: {occurrence_id}")
        if not isinstance(projection_hash, str) or not _SHA256_RE.fullmatch(projection_hash):
            raise BenchError(f"{occurrence_id}: invalid projection hash")
        appearances = row.get("appearances")
        if not isinstance(appearances, list) or not appearances:
            raise BenchError(f"{occurrence_id}: projection requires appearances")
        for appearance in appearances:
            appearance_id = appearance.get("appearance_id") if isinstance(appearance, dict) else None
            if not isinstance(appearance_id, str) or not appearance_id or appearance_id in appearance_ids:
                raise BenchError(f"{occurrence_id}: invalid or duplicate appearance identity")
            if appearance.get("projection_hash") != projection_hash:
                raise BenchError(f"{occurrence_id}: appearance projection hash is stale")
            appearance_ids.add(appearance_id)
            appearance_count += 1
        projection_by_occurrence[occurrence_id] = row

    certified_by_id = {fact["fact_id"]: fact for fact in certified_facts}
    supporting_ids = {
        fact_id for fact_id, fact in certified_by_id.items()
        if fact.get("fact_type") == "particle_rootlessness"
    }
    trace_by_occurrence = {}
    rendered_union = set()
    for trace in reverse_trace:
        canonical = trace.get("canonical_occurrence")
        marker = "#p007:"
        if not isinstance(canonical, str) or marker not in canonical:
            raise BenchError("reverse trace lacks exact p007 occurrence identity")
        occurrence_id = "quran:" + canonical.split(marker, 1)[1]
        if not _QURAN_OCCURRENCE_RE.fullmatch(occurrence_id) or occurrence_id in trace_by_occurrence:
            raise BenchError("reverse trace has invalid or duplicate occurrence identity")
        expected_projection_id = "proj:p00slice:" + occurrence_id.removeprefix("quran:").replace(":", "_")
        if trace.get("projection_id") != expected_projection_id:
            raise BenchError(f"{occurrence_id}: reverse trace projection identity mismatch")
        rendered = trace.get("renders_from_facts")
        if not isinstance(rendered, list) or len(rendered) != len(set(rendered)):
            raise BenchError(f"{occurrence_id}: invalid renders_from_facts")
        occurrence_fact_ids = {
            fact_id for fact_id, fact in certified_by_id.items()
            if occurrence_id in _quran_addresses(fact)
            and fact.get("fact_type") != "particle_rootlessness"
        }
        expected = occurrence_fact_ids | supporting_ids
        if set(rendered) != expected:
            raise BenchError(f"{occurrence_id}: projection/fact parity mismatch")
        rendered_union.update(rendered)
        trace_by_occurrence[occurrence_id] = trace

    if set(projection_by_occurrence) != set(trace_by_occurrence):
        raise BenchError("projection/fact parity occurrence coverage mismatch")
    if rendered_union != set(certified_by_id):
        raise BenchError("projection/fact parity does not cover the effective certified fact set")
    return {
        "appearance_count": appearance_count,
        "rendered_fact_count": len(rendered_union),
        "projection_count": len(projection_by_occurrence),
    }


def ensure_hover_axis_matches_parity(axis, parity):
    if axis.get("appearances_dispositioned") != parity["appearance_count"]:
        raise BenchError("structured-hover stale appearance count")
    metric = axis.get("metric") or {}
    if metric.get("numerator") != parity["rendered_fact_count"]:
        raise BenchError("structured-hover stale projection/fact parity numerator")


def _artifact_path(artifacts, artifact_id, root):
    return _resolve(root, artifacts[artifact_id]["path"])


def build_report(*, root=ROOT, manifest_path=DEFAULT_MANIFEST,
                 model_card_path=DEFAULT_MODEL_CARD, quarantine_path=DEFAULT_QUARANTINE):
    root = Path(root).resolve()
    manifest = read_json(manifest_path)
    model_card = read_json(model_card_path)
    quarantine = read_json(quarantine_path)
    artifacts = validate_manifest(manifest, root=root)
    _validate_model_card(model_card)
    probe_ids, probe_rows = _validate_quarantine(root, manifest, quarantine, artifacts)
    tutor_replay = replay_tutor_probes(probe_rows)

    geometry = manifest["axes"]["ownership_geometry"]
    geometry_facts, _geometry_statuses = load_effective_certified_facts(
        root=root,
        store_dir=geometry["certification_store_dir"],
        claims_path=geometry["claims_path"],
        allowed_fact_types=set(geometry["allowed_fact_types"]),
    )
    rows, geometry_baseline, _context = geometry_builder.build_batch(
        reverse_universe_path=_artifact_path(artifacts, "geometry-reverse-universe", root),
        typed_facts_path=_artifact_path(artifacts, "geometry-typed-facts", root),
        events_path=_artifact_path(artifacts, "geometry-events", root),
    )
    committed_geometry = read_json(_artifact_path(
        artifacts, "geometry-projection-baseline", root
    ))
    if geometry_baseline != committed_geometry:
        raise BenchError("geometry projection baseline is stale")

    hover = manifest["axes"]["structured_hover"]
    pilot_dir = _resolve(root, hover["pilot_dir"])
    pilot_errors = pilot_validator.validate(str(pilot_dir))
    if pilot_errors:
        raise BenchError("p007 pilot validator failed: " + "; ".join(pilot_errors[:5]))
    hover_facts, hover_statuses = load_effective_certified_facts(
        root=root,
        store_dir=hover["certification_store_dir"],
        claims_path=hover["claims_path"],
        allowed_fact_types=set(hover["allowed_fact_types"]),
    )
    occurrence_scoped = [fact for fact in hover_facts
                         if fact["fact_type"] != "particle_rootlessness"]
    hover_occurrences = {
        address
        for fact in occurrence_scoped
        for address in _quran_addresses(fact)
    }
    active_rivals = sum(len(fact.get("contradiction_records") or []) for fact in hover_facts)
    review_required = sum(status == "review_required" for status in hover_statuses.values())
    hover_parity = analyze_hover_projection_parity(
        read_jsonl(_artifact_path(artifacts, "pilot-projections", root)),
        read_json_array(_artifact_path(artifacts, "pilot-reverse-trace", root)),
        hover_facts,
    )

    geometry_metric = {
        "name": "effective_certified_geometry_fact_integrity",
        "numerator": len(geometry_facts),
        "denominator": len(geometry_facts),
        "score": 1.0,
        "comparison": "baseline_no_previous_report",
        "delta": None,
    }
    hover_metric = {
        "name": "projection_effective_fact_parity",
        "numerator": hover_parity["rendered_fact_count"],
        "denominator": len(hover_facts),
        "score": hover_parity["rendered_fact_count"] / len(hover_facts),
        "comparison": "baseline_no_previous_report",
        "delta": None,
    }
    tutor_metric = {
        "name": "ordinary_tutor_runtime_replay",
        "numerator": tutor_replay["probe_passes"],
        "denominator": len(probe_ids),
        "score": tutor_replay["probe_passes"] / len(probe_ids),
        "comparison": "baseline_no_previous_report",
        "delta": None,
    }
    report = {
        "schema": SCHEMA,
        "benchmark_id": BENCHMARK_ID,
        "authority_commit": manifest["authority_commit"],
        "aggregate_score_allowed": False,
        "axes": {
            "ownership_geometry": {
                "status": "scored_authority_integrity",
                "identity_join": "exact_quran_occurrence_id",
                "gold_scope": "partial_attachment_geometry_only",
                "full_token_ownership_gold": False,
                "canonical_occurrences": geometry_baseline["population"]["occurrences"],
                "effectively_certified_facts": len(geometry_facts),
                "fact_type_counts": geometry_baseline["certification_store"]["fact_type_counts"],
                "appearances_dispositioned": len(rows),
                "projection_ready_appearances": geometry_baseline["downstream_dispositions"]
                    ["appearances"]["geometry_projection_ready"],
                "withheld_appearances": geometry_baseline["downstream_dispositions"]
                    ["appearances"]["appearance_surface_variant_mapping_required"],
                "metric": geometry_metric,
            },
            "structured_hover": {
                "status": "scored_projection_fact_parity",
                "identity_join": "exact_quran_occurrence_id",
                "gold_scope": "p007_pilot_structured_facts_only",
                "full_rich_hover_gold": False,
                "effectively_certified_facts": len(hover_facts),
                "occurrence_scoped_facts": len(occurrence_scoped),
                "supporting_entry_facts": len(hover_facts) - len(occurrence_scoped),
                "canonical_occurrences": len(hover_occurrences),
                "appearances_dispositioned": hover_parity["appearance_count"],
                "canonical_projections": hover_parity["projection_count"],
                "active_rivals": active_rivals,
                "review_required_historical_facts_excluded": review_required,
                "safety_canaries_scored_as_gold": 0,
                "metric": hover_metric,
            },
            "contextual_translation": {
                "status": "not_scored_no_certified_gold",
                "denominator": 0,
                "score": None,
            },
            "tutor": {
                "status": "scored_runtime_replay",
                "probe_count": len(probe_ids),
                "probe_ids": sorted(probe_ids),
                "quarantine_overlap_count": 0,
                "answers_exposed_to_authoring_inputs": 0,
                "learner_performance_scored": False,
                "runtime_replay": tutor_replay,
                "metric": tutor_metric,
            },
        },
        "limitations": [
            "v1 scores authority integrity and ordinary tutor runtime replay, not unconstrained model or learner accuracy",
            "contextual translation remains unscored until certified gold exists",
            "candidate payload examples are safety canaries and never benchmark truth",
        ],
    }
    if contains_aggregate_score(report):
        raise BenchError("aggregate score unexpectedly entered report")
    ensure_hover_axis_matches_parity(report["axes"]["structured_hover"], hover_parity)
    ensure_source_clean(report)
    return report


def _self_test():
    manifest = read_json(DEFAULT_MANIFEST)
    report = build_report()
    mutations = 0

    def rejected(mutator, expected):
        nonlocal mutations
        candidate = copy.deepcopy(manifest)
        mutator(candidate)
        try:
            validate_manifest(candidate, root=ROOT)
        except BenchError as exc:
            if expected not in str(exc):
                raise BenchError(f"mutation rejected for wrong reason: {exc}") from exc
            mutations += 1
            return
        raise BenchError(f"mutation was not rejected: {expected}")

    rejected(lambda value: value.__setitem__("aggregate_score", 1.0), "aggregate")
    rejected(
        lambda value: value["axes"]["contextual_translation"].__setitem__("denominator", 1),
        "certified translation gold",
    )
    rejected(
        lambda value: value["axes"]["ownership_geometry"].__setitem__(
            "identity_join", "normalized_surface"
        ),
        "exact_quran_occurrence_id",
    )
    rejected(
        lambda value: value["axes"]["structured_hover"]["gold_artifact_ids"].append(
            value["safety_canary_artifact_ids"][0]
        ),
        "safety canary",
    )
    rejected(
        lambda value: value["artifacts"][0].__setitem__("sha256", "0" * 64),
        "sha256 mismatch",
    )
    try:
        ensure_no_quarantine_overlap({"probe"}, {"input": {"probe"}})
    except BenchError:
        mutations += 1
    else:
        raise BenchError("quarantine overlap mutation was not rejected")
    try:
        ensure_source_clean({"note": "/srv/private/source"})
    except BenchError:
        mutations += 1
    else:
        raise BenchError("leak mutation was not rejected")
    stale_geometry = {
        "fact_id": "fact:self-test:stale-span",
        "fact_type": "attachment_geometry",
        "fact_value": {
            "surface_nfc": "لِلَّهِ",
            "component_surface": "لِ",
            "char_span": {"start": 0, "end": 1},
        },
        "surface_spans": [{"quran_loc": "quran:1:2:2", "surface": "لِلَّهِ"}],
        "unresolved_blockers": [],
        "contradiction_records": [],
    }
    try:
        validate_certified_fact(stale_geometry)
    except BenchError:
        mutations += 1
    else:
        raise BenchError("stale span mutation was not rejected")
    wrong_reason = {
        "fact_id": "fact:self-test:wrong-reason",
        "fact_type": "contextual_function",
        "fact_value": {"function": "particle", "reason_key": ""},
        "surface_spans": [{"quran_loc": "quran:1:2:2", "surface": "لِلَّهِ"}],
        "unresolved_blockers": [],
        "contradiction_records": [],
    }
    try:
        validate_certified_fact(wrong_reason)
    except BenchError:
        mutations += 1
    else:
        raise BenchError("wrong-reason mutation was not rejected")
    wrong_reason["fact_value"]["reason_key"] = "exact-reason"
    wrong_reason["contradiction_records"] = [{"status": "unresolved"}]
    try:
        validate_certified_fact(wrong_reason)
    except BenchError:
        mutations += 1
    else:
        raise BenchError("unresolved-rival mutation was not rejected")
    artifacts = validate_manifest(manifest, root=ROOT)
    hover = manifest["axes"]["structured_hover"]
    hover_facts, _ = load_effective_certified_facts(
        root=ROOT,
        store_dir=hover["certification_store_dir"],
        claims_path=hover["claims_path"],
        allowed_fact_types=set(hover["allowed_fact_types"]),
    )
    stale_projections = read_jsonl(_artifact_path(artifacts, "pilot-projections", ROOT))
    stale_projections[0]["appearances"][0]["projection_hash"] = "0" * 64
    try:
        analyze_hover_projection_parity(
            stale_projections,
            read_json_array(_artifact_path(artifacts, "pilot-reverse-trace", ROOT)),
            hover_facts,
        )
    except BenchError:
        mutations += 1
    else:
        raise BenchError("stale appearance projection mutation was not rejected")
    probe_rows = read_jsonl(_artifact_path(artifacts, "placement-probes", ROOT))
    probe_rows[0]["required_reasoning"] = []
    try:
        replay_tutor_probes(probe_rows)
    except BenchError:
        mutations += 1
    else:
        raise BenchError("missing tutor reason-gate mutation was not rejected")
    if contains_aggregate_score(report):
        raise BenchError("green report contains aggregate score")
    print(f"FUSHA-BENCH self-test: {mutations}/{mutations} mutations rejected; green baseline valid")
    return 0


def check_fresh(report_path=DEFAULT_REPORT):
    expected = build_report()
    path = Path(report_path)
    if not path.is_file() or path.read_bytes() != _pretty_bytes(expected):
        raise BenchError("committed FUSHA-BENCH report is not byte-for-byte fresh")
    return expected


def _check():
    check_fresh()
    print("FUSHA-BENCH check: committed report is fresh")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic FUSHA-BENCH v1 runner")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true",
                        help="permit writing the explicit --report-out path")
    parser.add_argument("--report-out", help="explicit report path; requires --write")
    args = parser.parse_args(argv)
    if args.report_out and not args.write:
        parser.error("--report-out requires --write; implicit writes are forbidden")
    if args.write and not args.report_out:
        parser.error("--write requires an explicit --report-out path")
    if args.check and (args.write or args.report_out):
        parser.error("--check is read-only and cannot be combined with output options")
    if args.self_test and (args.check or args.write or args.report_out):
        parser.error("--self-test cannot be combined with other modes")
    if args.self_test:
        return _self_test()
    if args.check:
        return _check()
    report = build_report()
    if args.write:
        output = Path(args.report_out).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(_pretty_bytes(report))
        print(f"FUSHA-BENCH report written: {output}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BenchError as exc:
        print(f"FUSHA-BENCH ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
