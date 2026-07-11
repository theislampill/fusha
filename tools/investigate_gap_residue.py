#!/usr/bin/env python3
"""Investigate T10 Lane C residue and design Lane D morphline repair candidates.

This tool is deliberately read-only over the queue, denominator, crosswalk, Qamus
dataset, and deployed-baseline snapshot.  It writes only the three review artifacts
named by the T10 Lane C+D execution brief.
"""

from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import normalize_ar as N  # noqa: E402


AUTHORITATIVE_BASELINE_SHA = "bf6d7fc9c9ae40704ad6d82be5becbd946267f1c"
QUEUE_PATH = ROOT / "qamus/indexes/largelexicon/crosswalk-gap/crosswalk-gap-queue.jsonl"
DENOMINATOR_DIR = ROOT / "qamus/indexes/largelexicon/qword-denominator"
DENOMINATOR_MANIFEST = ROOT / "qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json"
ENTRIES_PATH = ROOT / "qamus/data/current/entries.jsonl"
BY_ENTRY_ID_PATH = ROOT / "qamus/indexes/current/by-entry-id.json"
DEFAULT_OUTDIR = ROOT / "qamus/indexes/largelexicon/crosswalk-gap"
LANE_C_NAME = "lane-c-dispositions.jsonl"
LANE_D_NAME = "lane-d-morphline-plan.jsonl"
SUMMARY_NAME = "lane-cd.summary.json"

LANE_C_DISPOSITIONS = {
    "blocked_on_owner_dataset_correction",
    "missing_entry_authoring_required",
    "missing_card_or_qword_source",
    "normalization_failure",
    "invalid_live_row_proposed_removal",
}
LANE_D_VERDICTS = {
    "deterministically_derivable",
    "requires_authoring",
    "intentionally_empty_hypothesis",
}
LANE_A_MORPHLINE_SKIPS = ("7:11:7", "7:39:3")
PLACEHOLDER_RE = re.compile(r"^(?:STEM|PFX|SUFF|ART|N|V|FUNC|TOKEN|HOST)$", re.I)
LOC_RE = re.compile(r"^(\d+):(\d+):(\d+)$")

# Owner-supplied NF-T10-1 facts.  These are consumed as authoritative context;
# this tool verifies the local joins around them but does not attempt to rediscover
# or reinterpret their ownership decision.
OWNER_DATASET_DEPENDENCIES = {
    "2:274:1": (
        "NF-T10-1 text-variant dependency: owner must reconcile the 2:274 "
        "live-store spelling/token text with the dataset example before crosswalk repair"
    ),
    "4:64:9": (
        "NF-T10-1 wrong-reference dependency: correct entry 1c5f7c9c8e05 "
        "usage2/example11 ref 4:46 -> 4:64, then rebuild denominator and crosswalk"
    ),
    "4:64:10": (
        "NF-T10-1 wrong-reference dependency: correct entry 1c5f7c9c8e05 "
        "usage2/example11 ref 4:46 -> 4:64, then rebuild denominator and crosswalk"
    ),
    "12:37:1": (
        "NF-T10-1 live-only-example dependency: owner must add/reconcile the "
        "12:37 example in the dataset, then rebuild denominator and crosswalk"
    ),
    "48:15:1": (
        "NF-T10-1 live-only-example dependency: owner must add/reconcile the "
        "48:15 example in the dataset, then rebuild denominator and crosswalk"
    ),
}

# Same-ayah source rows that demonstrate a strict normalization miss rather than
# absence of a source card.  Row ids are stable, hash-pinned denominator evidence.
NORMALIZATION_LINKS = {
    "20:14:10": "llx-qword-ca43414f9b01-01-17-002",
    "28:31:19": "llx-qword-c59a0161fac8-02-15-003",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def loc_key(loc: str) -> tuple[int, int, int]:
    match = LOC_RE.fullmatch(loc or "")
    if not match:
        raise ValueError(f"invalid canonical location: {loc!r}")
    return tuple(int(part) for part in match.groups())


def row_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        loc_key(row["canonical_location"] if "canonical_location" in row else row["loc"]),
        row.get("entry_id") or "",
        row.get("card_id") or "",
        row.get("qword_row_id") or "",
    )


def quran_ref(loc: str) -> str:
    surah, ayah, _word = loc.split(":")
    return f"{surah}:{ayah}"


def git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("cannot determine git HEAD: " + proc.stderr.strip())
    return proc.stdout.strip()


def baseline_is_ancestor() -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", AUTHORITATIVE_BASELINE_SHA, "HEAD"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    return proc.returncode == 0


def entry_surface_fields(entry: dict[str, Any]) -> Iterable[tuple[str, str]]:
    headword = entry.get("headword")
    if isinstance(headword, str):
        yield "headword", headword
    for sense_index, sense in enumerate(entry.get("senses") or []):
        if isinstance(sense.get("ar"), str):
            yield f"senses[{sense_index}].ar", sense["ar"]
    for usage_index, usage in enumerate(entry.get("usage") or []):
        for form_index, form in enumerate(usage.get("forms") or []):
            if isinstance(form, str):
                yield f"usage[{usage_index}].forms[{form_index}]", form


def compact_carriers(rows: Iterable[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    carriers = [{
        "qword_row_id": row.get("row_id"),
        "entry_id": row.get("entry_id"),
        "card_id": row.get("card_id"),
        "quran_ref": row.get("quran_ref"),
        "visible_surface": row.get("visible_surface"),
        "visible_surface_norm_strict": row.get("visible_surface_norm_strict"),
    } for row in rows]
    carriers.sort(key=canonical_json)
    return carriers[:limit]


def evidence_by_join(evidence: list[dict[str, Any]], join: str) -> dict[str, Any] | None:
    return next((item for item in evidence if item.get("join") == join), None)


def validate_lane_c_disposition(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "canonical_location", "live_surface", "investigation_evidence",
        "disposition", "proposed_next_action",
    ):
        if row.get(field) in (None, "", []):
            errors.append(f"{field} must be non-empty")
    if row.get("disposition") not in LANE_C_DISPOSITIONS:
        errors.append(f"disposition outside enum: {row.get('disposition')!r}")
    evidence = row.get("investigation_evidence")
    if not isinstance(evidence, list) or not evidence:
        return errors or ["investigation_evidence must be a non-empty list"]
    if any(not isinstance(item, dict) or not item.get("join") or not item.get("result")
           for item in evidence):
        errors.append("every evidence item must name join and result")

    exact = evidence_by_join(evidence, "denominator_exact_ayah_norm_strict")
    if not exact or exact.get("match_count") != 0:
        errors.append("no-candidate disposition requires a proven zero exact denominator join")

    disposition = row.get("disposition")
    if disposition == "blocked_on_owner_dataset_correction":
        dependency = row.get("owner_dataset_dependency")
        if not isinstance(dependency, str) or "NF-T10-1" not in dependency:
            errors.append("owner-blocked row requires its exact NF-T10-1 dependency")
    elif disposition == "missing_entry_authoring_required":
        host = evidence_by_join(evidence, "qamus_entry_surface_host")
        if not host or host.get("match_count") != 0:
            errors.append("missing-entry disposition requires a zero entry-host join")
    elif disposition == "missing_card_or_qword_source":
        global_join = evidence_by_join(evidence, "denominator_global_norm_strict")
        if not global_join or global_join.get("match_count", 0) < 1:
            errors.append("missing-source disposition requires entry-host proof from qword sources")
    elif disposition == "normalization_failure":
        alternate = evidence_by_join(evidence, "same_ayah_alternate_norm")
        if not alternate:
            errors.append("normalization failure requires same-ayah alternate-norm evidence")
        elif alternate.get("live_norm_strict") == alternate.get("source_norm_strict"):
            errors.append("normalization failure must show two different strict norms")
    elif disposition == "invalid_live_row_proposed_removal":
        corpus = evidence_by_join(evidence, "canonical_corpus_location")
        if not corpus or corpus.get("location_present") is not False:
            errors.append("proposed removal requires explicit invalid-location evidence")
    return errors


def validate_morphline_candidate(value: Any, observed_values: set[str]) -> list[str]:
    if value is None or not str(value).strip():
        return ["derived morphline candidate must be non-empty"]
    candidate = str(value).strip()
    if PLACEHOLDER_RE.fullmatch(candidate) and candidate not in observed_values:
        return [f"unobserved placeholder-like morphline is forbidden: {candidate!r}"]
    return []


def build_lane_c(
    queue_rows: list[dict[str, Any]],
    denominator_rows: list[dict[str, Any]],
    entries: list[dict[str, Any]],
    corpus_by_loc: dict[str, str],
) -> list[dict[str, Any]]:
    qd_by_id = {row["row_id"]: row for row in denominator_rows}
    qd_by_ayah: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    qd_by_strict: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in denominator_rows:
        qd_by_ayah[row.get("quran_ref")].append(row)
        qd_by_strict[row.get("visible_surface_norm_strict")].append(row)

    entry_hosts: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for entry in entries:
        for field_path, surface in entry_surface_fields(entry):
            entry_hosts[N.norm_strict(surface)].append({
                "entry_id": entry["id"], "field_path": field_path, "surface": surface,
            })

    output: list[dict[str, Any]] = []
    lane_rows = [row for row in queue_rows
                 if row.get("primary_resolution_family") == "no_qword_candidate"]
    if len(lane_rows) != 10:
        raise RuntimeError(f"expected 10 no_qword_candidate rows, found {len(lane_rows)}")

    for queue_row in sorted(lane_rows, key=row_sort_key):
        loc = queue_row["canonical_location"]
        ayah = quran_ref(loc)
        source_norm = queue_row["source_normalization"]["norm_strict"]
        live_surface = queue_row["source_normalization"]["live_surface"]
        exact = [row for row in qd_by_ayah[ayah]
                 if row.get("visible_surface_norm_strict") == source_norm]
        if exact:
            raise RuntimeError(f"queue drift: {loc} now has exact denominator candidates")
        global_matches = qd_by_strict[source_norm]
        hosts = entry_hosts[source_norm]
        evidence: list[dict[str, Any]] = [{
            "join": "denominator_exact_ayah_norm_strict",
            "attempted_key": f"{ayah}|{source_norm}",
            "match_count": 0,
            "result": "missed: no qword-denominator row has both this ayah and strict surface key",
        }, {
            "join": "denominator_global_norm_strict",
            "attempted_key": source_norm,
            "match_count": len(global_matches),
            "sample_matches": compact_carriers(global_matches),
            "result": (
                "matched elsewhere: qamus entry/card sources host the surface, but not at this ayah"
                if global_matches else
                "missed globally: no qword-denominator source hosts this strict surface"
            ),
        }, {
            "join": "qamus_entry_surface_host",
            "attempted_key": source_norm,
            "match_count": len(hosts),
            "sample_matches": sorted(hosts, key=canonical_json)[:12],
            "result": (
                "matched an authored entry field under norm_strict"
                if hosts else "missed entry headword, sense surface, and usage forms under norm_strict"
            ),
        }, {
            "join": "canonical_corpus_location",
            "attempted_key": loc,
            "location_present": loc in corpus_by_loc,
            "corpus_surface": corpus_by_loc.get(loc),
            "result": (
                "matched the pinned corpus location"
                if loc in corpus_by_loc else
                "missed: the pinned corpus index has no row at this deployed location"
            ),
        }]

        row: dict[str, Any] = {
            "schema": "qamus.lane_c_disposition.v1",
            "canonical_location": loc,
            "live_surface": live_surface,
            "live_norm_strict": source_norm,
            "investigation_evidence": evidence,
        }
        if loc in OWNER_DATASET_DEPENDENCIES:
            row.update({
                "disposition": "blocked_on_owner_dataset_correction",
                "owner_dataset_dependency": OWNER_DATASET_DEPENDENCIES[loc],
                "proposed_next_action": (
                    "Owner resolves the named NF-T10-1 dataset dependency; then rebuild "
                    "entries, denominator, crosswalk, and this investigation before any repair."
                ),
            })
        elif loc in NORMALIZATION_LINKS:
            alternate = qd_by_id.get(NORMALIZATION_LINKS[loc])
            if not alternate or alternate.get("quran_ref") != ayah:
                raise RuntimeError(f"normalization evidence missing or drifted for {loc}")
            alternate_evidence = {
                "join": "same_ayah_alternate_norm",
                "attempted_key": ayah,
                "qword_row_id": alternate["row_id"],
                "entry_id": alternate["entry_id"],
                "card_id": alternate["card_id"],
                "live_surface": live_surface,
                "live_norm_strict": source_norm,
                "source_surface": alternate["visible_surface"],
                "source_norm_strict": alternate["visible_surface_norm_strict"],
                "live_norm_recall": N.norm(live_surface),
                "source_norm_recall": N.norm(alternate["visible_surface"]),
                "result": "matched a same-ayah source row only under an alternate orthographic key",
            }
            evidence.append(alternate_evidence)
            row.update({
                "disposition": "normalization_failure",
                "proposed_next_action": (
                    "Review the displayed-text/source-card orthography and define an owner-approved, "
                    "hamza-safe exact crosswalk rule; do not broaden norm_strict globally."
                ),
            })
        elif global_matches:
            same_ayah = sorted(qd_by_ayah[ayah], key=lambda item: item["row_id"])
            evidence.append({
                "join": "same_ayah_source_inventory",
                "attempted_key": ayah,
                "match_count": len(same_ayah),
                "sample_matches": compact_carriers(same_ayah),
                "result": "same-ayah cards exist, but none emits this exact qword surface key",
            })
            row.update({
                "disposition": "missing_card_or_qword_source",
                "proposed_next_action": (
                    "Author or repair the exact-address example/qword source row through the owner "
                    "dataset lane, then rebuild denominator and crosswalk; do not bind from global surface alone."
                ),
            })
        elif not hosts:
            row.update({
                "disposition": "missing_entry_authoring_required",
                "proposed_next_action": (
                    "Author a reviewed Qamus entry candidate for this surface before creating any card, "
                    "qword denominator row, or crosswalk binding."
                ),
            })
        else:
            # An entry-field host without a qword source is still the missing-source lane.
            row.update({
                "disposition": "missing_card_or_qword_source",
                "proposed_next_action": (
                    "Add a reviewed example/card and qword source for the existing entry, then rebuild "
                    "denominator and crosswalk."
                ),
            })

        errors = validate_lane_c_disposition(row)
        if errors:
            raise RuntimeError(f"unsafe Lane C classification for {loc}: {errors}")
        output.append(row)
    return output


def segment_shape(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple((segment.get("class") or segment.get("qg_class") or "")
                 for segment in (row.get("segments") or []))


def convention_study(baseline_rows: list[dict[str, Any]]) -> dict[str, Any]:
    nonempty = [row for row in baseline_rows if str(row.get("morphline") or "").strip()]
    observed = {str(row["morphline"]).strip() for row in nonempty}
    shapes: dict[tuple[str, ...], collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for row in nonempty:
        shapes[segment_shape(row)][str(row["morphline"]).strip()] += 1

    target_shapes = (("qg-preposition",), ("qg-noun",), ("qg-lam",))
    distribution = []
    for shape in target_shapes:
        variants = shapes.get(shape, collections.Counter())
        distribution.append({
            "segment_class_shape": list(shape),
            "row_count": sum(variants.values()),
            "distinct_morphlines": len(variants),
            "top_morphlines": [
                {"morphline": value, "count": count}
                for value, count in variants.most_common(10)
            ],
        })

    rich_examples = []
    for row in sorted(nonempty, key=lambda item: loc_key(item.get("loc") or item.get("wbw_loc", "").replace("wbw:", ""))):
        segments = row.get("segments") or []
        if not segments or not all(
            (segment.get("class") or segment.get("qg_class"))
            and segment.get("role") and segment.get("label")
            for segment in segments
        ):
            continue
        rich_examples.append({
            "loc": row.get("loc") or str(row.get("wbw_loc")).replace("wbw:", ""),
            "surface": row.get("surface") or row.get("ar"),
            "ordered_segments": [{
                "class": segment.get("class") or segment.get("qg_class"),
                "role": segment.get("role"),
                "label": segment.get("label"),
            } for segment in segments],
            "morphline": row["morphline"],
        })
        if len(rich_examples) == 12:
            break
    if len(rich_examples) < 10:
        raise RuntimeError("convention study could not find 10 concrete rich examples")

    return {
        "result": "consistent_semantic_relationship_without_deterministic_text_projection",
        "relationship_observed": (
            "Non-empty morphlines describe the whole token's grammatical composition and "
            "elaborate facts represented by ordered segment classes/roles. They are narrative "
            "descriptions, not a canonical role-token serialization."
        ),
        "derivation_limit": (
            "Identical segment-class shapes map to many morphline strings, so class alone cannot "
            "select exact text. The target rows also have blank role and label fields; their coarse "
            "qg class does not certify the missing morphology/function details."
        ),
        "stop_condition_triggered": False,
        "stop_condition_reason": (
            "A consistent semantic relationship is observed, so the no-relationship stop does not "
            "trigger. Exact candidates remain non-derivable and route to requires_authoring."
        ),
        "nonempty_rows": len(nonempty),
        "empty_rows": len(baseline_rows) - len(nonempty),
        "distinct_nonempty_morphlines": len(observed),
        "target_shape_distribution": distribution,
        "concrete_examples": rich_examples,
        "observed_morphlines": observed,
    }


def build_lane_d(
    queue_rows: list[dict[str, Any]],
    denominator_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    study: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_by_loc = {row.get("loc") or str(row.get("wbw_loc", "")).replace("wbw:", ""): row
                       for row in baseline_rows}
    qd_by_ayah_norm: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in denominator_rows:
        qd_by_ayah_norm[(row.get("quran_ref"), row.get("visible_surface_norm_strict"))].append(row)

    targets: dict[str, list[dict[str, Any]]] = {}
    for queue_row in queue_rows:
        if queue_row.get("primary_resolution_family") != "in_crosswalk_morphline_repair":
            continue
        targets[queue_row["canonical_location"]] = list(queue_row["full_carrier_candidates"])
    if len(targets) != 13:
        raise RuntimeError(f"expected 13 in-crosswalk morphline locations, found {len(targets)}")

    for loc in LANE_A_MORPHLINE_SKIPS:
        live = baseline_by_loc.get(loc)
        if not live:
            raise RuntimeError(f"Lane A morphline skip absent from baseline: {loc}")
        matches = qd_by_ayah_norm[(quran_ref(loc), N.norm_strict(live.get("surface") or live.get("ar") or ""))]
        if len(matches) != 1:
            raise RuntimeError(f"Lane A morphline skip {loc} expected one qword source, found {len(matches)}")
        source = matches[0]
        targets[loc] = [{
            "entry_id": source["entry_id"],
            "card_id": source["card_id"],
            "qword_row_id": source["row_id"],
            "row_id": source["row_id"],
        }]

    observed_values = study["observed_morphlines"]
    output: list[dict[str, Any]] = []
    for loc in sorted(targets, key=loc_key):
        live = baseline_by_loc.get(loc)
        if not live:
            raise RuntimeError(f"target missing from baseline: {loc}")
        if live.get("morphline") != "":
            raise RuntimeError(f"target morphline is no longer empty: {loc}: {live.get('morphline')!r}")
        segments = live.get("segments") or []
        public_gloss = (live.get("public_gloss") or live.get("token_contribution_gloss")
                        or live.get("gloss"))
        learner = live.get("learner_explanation") or live.get("learner")
        if not segments or not public_gloss or not learner:
            raise RuntimeError(f"preflight drift: {loc} fails more than empty morphline")

        target_facts = [{
            "segment_index": segment.get("segment_index"),
            "surface": segment.get("surface"),
            "class": segment.get("class") or segment.get("qg_class"),
            "role": segment.get("role"),
            "label": segment.get("label"),
            "gloss_contribution": segment.get("gloss_contribution", segment.get("gloss")),
        } for segment in segments]
        # No candidate is emitted: coarse class plus blank role/label is insufficient.
        derived_candidate = None
        if derived_candidate is not None:
            errors = validate_morphline_candidate(derived_candidate, observed_values)
            if errors:
                raise RuntimeError(f"unsafe morphline candidate for {loc}: {errors}")
        for carrier in targets[loc]:
            output.append({
                "schema": "qamus.lane_d_morphline_plan.v1",
                "loc": loc,
                "entry_id": carrier["entry_id"],
                "card_id": carrier["card_id"],
                "qword_row_id": carrier.get("qword_row_id") or carrier.get("row_id"),
                "current_live_morphline": "",
                "candidate_only": True,
                "derivability_verdict": "requires_authoring",
                "exact_derivation_rule": None,
                "derived_candidate_value": None,
                "evidence": {
                    "live_segments": target_facts,
                    "public_gloss_present": True,
                    "learner_explanation_present": True,
                    "convention_study_result": study["result"],
                },
                "reason": (
                    "The live row supplies only a coarse segment class; role and label are blank. "
                    "The convention study shows no one-to-one class-to-morphline text projection, "
                    "so an exact value requires reviewed morphology/function authoring."
                ),
                "review_route": "RM-20 morphline authoring and review lane",
            })
    output.sort(key=row_sort_key)
    if len(output) != 32:
        raise RuntimeError(f"expected 32 Lane D binding rows, found {len(output)}")
    if any(row["derivability_verdict"] not in LANE_D_VERDICTS for row in output):
        raise RuntimeError("Lane D verdict outside enum")
    return output


def repair_wave_design() -> dict[str, Any]:
    return {
        "wave_id": "RM-20",
        "recommended_fact_type": "morphline_rendering",
        "fact_type_recommendation": (
            "Add morphline_rendering as a new open-registry fact type in "
            "qamus/schemas/fact-ledger-row.schema.json. Do not overload gloss_contribution: "
            "a morphline is structured morphology/function rendering, not English gloss text."
        ),
        "fact_ledger_step": {
            "tool": "tools/fact_ledger.py",
            "schema": "qamus/schemas/fact-ledger-row.schema.json",
            "subject_type": "surface_occurrence",
            "required_carrier": ["loc", "entry_id", "card_id", "qword_row_id"],
            "candidate_value": "the reviewed non-empty morphline string",
            "evidence_types": ["deterministic_derivation", "two_vote"],
            "materialization_target": "canonical hover public_payload.morphline",
        },
        "gate_step": {
            "gate_ssot": [
                "nahw/rules/two-vote-required-rules.json",
                "nahw/rules/grammar-problems-gates.json",
                "sarf/rules/verb-measure-gates.json",
                "tools/fact_ledger.py",
            ],
            "deterministic_gate": (
                "Allowed only when a versioned projection rule consumes certified, non-empty ordered "
                "segment roles plus required sarf/nahw facts and reproduces an observed convention."
            ),
            "two_vote_gate": (
                "Required for authored narrative morphlines or any function, case/mood, referent, "
                "derivative, attachment, or other grammar-sensitive claim; both votes must agree on value and reason."
            ),
            "current_lane_result": "all 32 bindings require authoring; none qualifies for deterministic projection",
        },
        "compiler_step": {
            "builder": "tools/build_canonical_hover_payload_table.py",
            "builder_outputs": ["canonical_payloads.jsonl", "occurrence_bindings.jsonl"],
            "validators": [
                "tools/validate_canonical_hover_payload_table.py",
                "tools/validate_renderer_completeness_gate.py",
            ],
            "compiler": "tools/compile_canonical_hover_whitelist_packet.py",
            "compiler_output": "whitelist_append_replace.jsonl",
            "rule": (
                "Project the certified fact into a canonical payload and full-carrier binding, then "
                "compile a replacement packet against the hash-pinned baseline. Never hand-edit the live whitelist."
            ),
        },
        "supersedes_step": {
            "fact_edge": "fact-ledger revision.supersedes points to the prior fact_id",
            "binding_edge": (
                "qamus/schemas/canonical-hover-occurrence-binding.schema.json supersedes points to "
                "the prior binding id when the RM-20 replacement binding is created"
            ),
            "wave_lineage": (
                "Record RM-20 as the repair-wave lineage on the review/compile report and retain prior_payload_hash "
                "in the compiler replacement packet."
            ),
        },
    }


def build_summary(
    lane_c: list[dict[str, Any]],
    lane_d: list[dict[str, Any]],
    study: dict[str, Any],
    baseline_path: Path,
    loc_surfaces_path: Path,
    denominator_files: list[Path],
) -> dict[str, Any]:
    lane_c_counts = collections.Counter(row["disposition"] for row in lane_c)
    lane_d_counts = collections.Counter(row["derivability_verdict"] for row in lane_d)
    study_public = {key: value for key, value in study.items() if key != "observed_morphlines"}
    return {
        "schema": "qamus.lane_cd_summary.v1",
        "authoritative_baseline_sha": AUTHORITATIVE_BASELINE_SHA,
        "source_lineage": "generated from inputs frozen at the authoritative baseline",
        "status": "investigation_complete_design_only",
        "mutation_boundary": (
            "No crosswalk, denominator, entries, whitelist, or production data was written. "
            "All Lane D rows are candidate_only."
        ),
        "generator": (
            "python tools/investigate_gap_residue.py --baseline <hash-pinned-whitelist.jsonl> "
            "--loc-surfaces <hash-pinned-loc-surfaces.jsonl>"
        ),
        "input_sha256": {
            "baseline_whitelist": sha256_file(baseline_path),
            "loc_surfaces": sha256_file(loc_surfaces_path),
            "crosswalk_gap_queue": sha256_file(QUEUE_PATH),
            "entries_jsonl": sha256_file(ENTRIES_PATH),
            "by_entry_id_index": sha256_file(BY_ENTRY_ID_PATH),
            "qword_denominator_manifest": sha256_file(DENOMINATOR_MANIFEST),
            "qword_denominator_shards": {
                path.name: sha256_file(path) for path in denominator_files
            },
        },
        "input_counts": {
            "crosswalk_gap_queue_rows": 5521,
            "lane_c_queue_rows": len(lane_c),
            "lane_d_locations": len({row["loc"] for row in lane_d}),
            "lane_d_bindings": len(lane_d),
        },
        "lane_c": {
            "per_disposition_counts": dict(sorted(lane_c_counts.items())),
            "outside_enum_count": sum(row["disposition"] not in LANE_C_DISPOSITIONS for row in lane_c),
        },
        "lane_d": {
            "per_verdict_counts": dict(sorted(lane_d_counts.items())),
            "candidate_only_rows": sum(row["candidate_only"] is True for row in lane_d),
        },
        "morphline_convention_study": study_public,
        "stop_conditions": {
            "no_consistent_segment_morphline_relationship": False,
            "lane_c_disposition_outside_enum": False,
            "triggered": False,
        },
        "repair_wave_design": repair_wave_design(),
    }


def render_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return ("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)).encode("utf-8")


def render_pretty_json(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_or_check(path: Path, content: bytes, check: bool) -> None:
    if check:
        if not path.exists() or path.read_bytes() != content:
            raise RuntimeError(f"generated artifact is stale: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(content)


def generate(baseline_path: Path, loc_surfaces_path: Path, outdir: Path, check: bool) -> None:
    if not baseline_is_ancestor():
        raise RuntimeError(
            f"authoritative baseline {AUTHORITATIVE_BASELINE_SHA} is not an ancestor of HEAD {git_head()}"
        )
    queue_rows = read_jsonl(QUEUE_PATH)
    if len(queue_rows) != 5521:
        raise RuntimeError(f"expected 5,521 queue rows, found {len(queue_rows)}")
    denominator_files = sorted(DENOMINATOR_DIR.glob("*.jsonl"))
    denominator_rows = [row for path in denominator_files for row in read_jsonl(path)]
    entries = read_jsonl(ENTRIES_PATH)
    by_entry_id = json.loads(BY_ENTRY_ID_PATH.read_text(encoding="utf-8"))
    if set(by_entry_id) != {entry["id"] for entry in entries}:
        raise RuntimeError("by-entry-id index and entries.jsonl id sets differ")
    baseline_rows = read_jsonl(baseline_path)
    corpus_rows = read_jsonl(loc_surfaces_path)
    corpus_by_loc = {row["loc"]: row["surface"] for row in corpus_rows}
    if len(corpus_by_loc) != len(corpus_rows):
        raise RuntimeError("loc-surfaces input contains duplicate canonical locations")

    lane_c = build_lane_c(queue_rows, denominator_rows, entries, corpus_by_loc)
    study = convention_study(baseline_rows)
    lane_d = build_lane_d(queue_rows, denominator_rows, baseline_rows, study)
    summary = build_summary(
        lane_c, lane_d, study, baseline_path, loc_surfaces_path, denominator_files,
    )
    write_or_check(outdir / LANE_C_NAME, render_jsonl(lane_c), check)
    write_or_check(outdir / LANE_D_NAME, render_jsonl(lane_d), check)
    write_or_check(outdir / SUMMARY_NAME, render_pretty_json(summary), check)
    action = "verified" if check else "generated"
    print(f"PASS - {action} Lane C={len(lane_c)} Lane D={len(lane_d)}")


def self_test() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool) -> None:
        print(("ok   " if condition else "FAIL ") + label)
        if not condition:
            failures.append(label)

    evidence_free = {
        "canonical_location": "1:1:1",
        "live_surface": "كِتَاب",
        "disposition": "missing_card_or_qword_source",
        "investigation_evidence": [],
        "proposed_next_action": "repair source",
    }
    check(
        "RED-FIRST: evidence-free Lane C disposition is rejected",
        bool(validate_lane_c_disposition(evidence_free)),
    )
    valid_lane_c = dict(evidence_free)
    valid_lane_c["investigation_evidence"] = [{
        "join": "denominator_exact_ayah_norm_strict", "match_count": 0,
        "result": "missed",
    }, {
        "join": "denominator_global_norm_strict", "match_count": 1,
        "result": "matched elsewhere",
    }]
    check(
        "evidenced missing-source Lane C disposition passes",
        validate_lane_c_disposition(valid_lane_c) == [],
    )

    observed = {"ART+STEM", "PFX+STEM"}
    check(
        "RED-FIRST: empty morphline derivation is rejected",
        bool(validate_morphline_candidate("", observed)),
    )
    check(
        "RED-FIRST: unobserved STEM-like placeholder is rejected",
        bool(validate_morphline_candidate("STEM", observed)),
    )
    check(
        "observed non-placeholder morphline candidate passes",
        validate_morphline_candidate("ART+STEM", observed) == [],
    )
    check(
        "Lane C disposition enum is exact",
        len(LANE_C_DISPOSITIONS) == 5,
    )
    if failures:
        print(f"SELF-TEST FAIL ({len(failures)} failures)")
        return 1
    print("PASS - investigate_gap_residue self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--loc-surfaces", type=Path)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.baseline or not args.loc_surfaces:
        parser.error("--baseline and --loc-surfaces are required unless --self-test")
    generate(args.baseline.resolve(), args.loc_surfaces.resolve(), args.outdir.resolve(), args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
