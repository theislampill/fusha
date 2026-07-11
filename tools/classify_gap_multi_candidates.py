#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministically classify T10 Lane B crosswalk-gap candidates.

This is an offline analysis tool.  It reads the committed gap queue, qword
denominator, and current Qamus entry indexes, then writes classification evidence
only.  It never mutates the queue, crosswalk, entries, or a live system.

Usage:
    python tools/classify_gap_multi_candidates.py --queue <queue.jsonl> \
        --outdir <crosswalk-gap-dir>
    python tools/classify_gap_multi_candidates.py --self-test
"""

import argparse
import collections
import glob
import hashlib
import io
import json
import os
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

ROW_SCHEMA = "qamus.laneb_classification_row.v1"
SUMMARY_SCHEMA = "qamus.laneb_classification_summary.v1"
TARGET_FAMILY = "multiple_qword_candidates"
EXPECTED_QUEUE_SHA256 = (
    "b79fe9b5422eafca7d53b450a5adee166a6b4f682f8e82cb600ccb4db06bbe8c"
)
EXPECTED_ROW_COUNT = 5447

CLASS_NAMES = (
    "same_occurrence_multi_entry_co_citation",
    "same_entry_multi_card",
    "same_card_multi_qword",
    "equivalent_payload_distinct_provenance",
    "competing_lexical_senses",
    "competing_sarf_analyses",
    "competing_nahw_analyses",
    "normalization_collision",
    "unresolved_occurrence_ambiguity",
)
CLASS_NUMBER = {name: index for index, name in enumerate(CLASS_NAMES, 1)}


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("%s:%d is not a JSON object" % (path, line_number))
            rows.append(value)
    return rows


def sha256_file(path):
    digest = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_label(path):
    absolute = os.path.abspath(path)
    try:
        relative = os.path.relpath(absolute, REPO)
    except ValueError:
        return absolute.replace("\\", "/")
    if relative == ".." or relative.startswith(".." + os.sep):
        return absolute.replace("\\", "/")
    return relative.replace("\\", "/")


def canonical_jsonl_bytes(rows):
    ordered = sorted(rows, key=lambda row: row["canonical_location"])
    return ("".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in ordered
    )).encode("utf-8")


def _sense_surfaces(entry):
    surfaces = []
    for sense in entry.get("senses") or []:
        if isinstance(sense, dict) and sense.get("ar"):
            surfaces.append(str(sense["ar"]))
    return sorted(set(surfaces))


def classify_row(queue_row, denominator_by_row_id, entries_by_id):
    """Return exactly one Lane B classification plus its mechanical evidence."""
    if queue_row.get("primary_resolution_family") != TARGET_FAMILY:
        raise ValueError("classify_row received a non-Lane-B row")

    carriers = sorted(
        queue_row.get("full_carrier_candidates") or [],
        key=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True),
    )
    if len(carriers) < 2:
        raise ValueError("Lane B row has fewer than two carrier candidates")

    candidate_details = []
    for carrier in carriers:
        row_id = carrier.get("row_id") or carrier.get("qword_row_id")
        denominator = denominator_by_row_id.get(row_id)
        if denominator is None:
            raise KeyError("missing qword denominator row %r" % row_id)
        candidate_details.append({
            "card_id": carrier.get("card_id"),
            "card_text_sha256": denominator.get("card_text_sha256"),
            "entry_id": carrier.get("entry_id"),
            "qword_row_id": carrier.get("qword_row_id") or row_id,
            "row_id": row_id,
            "visible_surface": denominator.get("visible_surface"),
            "visible_surface_norm_strict": denominator.get(
                "visible_surface_norm_strict"),
        })
    candidate_details.sort(key=lambda value: value["row_id"] or "")

    entry_ids = sorted({
        detail["entry_id"] for detail in candidate_details if detail["entry_id"]
    })
    card_ids = sorted({
        detail["card_id"] for detail in candidate_details if detail["card_id"]
    })
    qword_row_ids = sorted({
        detail["qword_row_id"] for detail in candidate_details
        if detail["qword_row_id"]
    })
    equivalence_classes = sorted(set(
        queue_row.get("candidate_equivalence_classes") or []))
    declared_entry_ids = sorted(set(queue_row.get("candidate_entry_ids") or []))
    declared_card_ids = sorted(set(queue_row.get("candidate_card_ids") or []))
    declared_qword_row_ids = sorted(set(
        queue_row.get("candidate_qword_row_ids") or []))
    declared_count = queue_row.get("candidate_count")
    declarations = (
        ("candidate_equivalence_classes", equivalence_classes, entry_ids),
        ("candidate_entry_ids", declared_entry_ids, entry_ids),
        ("candidate_card_ids", declared_card_ids, card_ids),
        ("candidate_qword_row_ids", declared_qword_row_ids, qword_row_ids),
    )
    for field, declared, derived in declarations:
        if declared != derived:
            raise ValueError("%s disagrees with carrier evidence" % field)
    if declared_count != len(candidate_details):
        raise ValueError("candidate_count disagrees with carrier evidence")
    entry_evidence = []
    for entry_id in entry_ids:
        entry = entries_by_id.get(entry_id)
        if entry is None:
            raise KeyError("missing entry %r" % entry_id)
        entry_evidence.append({
            "entry_id": entry_id,
            "root": entry.get("root") or "",
            "section": entry.get("section") or "",
            "sense_surfaces": _sense_surfaces(entry),
        })

    roots = sorted({entry["root"] for entry in entry_evidence})
    sections = sorted({entry["section"] for entry in entry_evidence})
    roots_agree = len(roots) <= 1
    sections_agree = len(sections) <= 1
    hashes = sorted({
        detail["card_text_sha256"] for detail in candidate_details
        if detail["card_text_sha256"]
    })
    candidate_surfaces = sorted({
        detail["visible_surface"] for detail in candidate_details
        if detail["visible_surface"]
    })
    candidate_norms = sorted({
        detail["visible_surface_norm_strict"] for detail in candidate_details
        if detail["visible_surface_norm_strict"]
    })
    equivalent_payload = len(qword_row_ids) >= 2 and len(hashes) == 1
    unique = queue_row.get("ayah_surface_unique")
    secondary = sorted(set(queue_row.get("secondary_conditions") or []))

    lexical_conflicts = []
    if len(entry_ids) >= 2 and not roots_agree:
        lexical_conflicts.append("candidate_entry_roots_differ")
    if len(entry_ids) >= 2 and not sections_agree:
        lexical_conflicts.append("candidate_entry_sections_differ")

    # Safety prerequisites narrow the numbered taxonomy: explicit normalization
    # failure and repeated-occurrence ambiguity cannot be superseded by payload
    # equivalence.  Class 1's owner-specified root/section downgrade similarly
    # routes to class 5 before accepting co-citation.
    if "live_surface_not_in_ayah_index" in secondary:
        classification = "normalization_collision"
        reason = "live surface is absent from the ayah surface index"
    elif unique is False:
        classification = "unresolved_occurrence_ambiguity"
        reason = "the normalized surface repeats in the ayah"
    elif unique is True and len(entry_ids) >= 2 and lexical_conflicts:
        classification = "competing_lexical_senses"
        reason = "; ".join(lexical_conflicts)
    elif unique is True and len(entry_ids) >= 2:
        classification = "same_occurrence_multi_entry_co_citation"
        reason = "unique ayah occurrence; multiple entries share root and section"
    elif unique is True and len(entry_ids) == 1 and len(card_ids) >= 2:
        classification = "same_entry_multi_card"
        reason = "unique ayah occurrence; one entry has multiple candidate cards"
    elif (unique is True and len(entry_ids) == 1 and len(card_ids) == 1
          and len(qword_row_ids) >= 2):
        classification = "same_card_multi_qword"
        reason = "unique ayah occurrence; one card has multiple qword rows"
    elif equivalent_payload:
        classification = "equivalent_payload_distinct_provenance"
        reason = "distinct qword rows carry one identical card-text hash"
    else:
        raise ValueError(
            "no deterministic Lane B class for %s" %
            queue_row.get("canonical_location"))

    return {
        "canonical_location": queue_row["canonical_location"],
        "classification_number": CLASS_NUMBER[classification],
        "classification_reason": reason,
        "evidence": {
            "ayah_surface_unique": unique,
            "candidate_card_ids": card_ids,
            "candidate_count": len(candidate_details),
            "candidate_details": candidate_details,
            "candidate_entry_ids": entry_ids,
            "candidate_equivalence_classes": equivalence_classes,
            "candidate_norm_strict_values": candidate_norms,
            "candidate_qword_row_ids": qword_row_ids,
            "candidate_visible_surfaces": candidate_surfaces,
            "entry_evidence": entry_evidence,
            "equivalent_payload_distinct_provenance": equivalent_payload,
            "lexical_conflict_signals": lexical_conflicts,
            "roots": roots,
            "roots_agree": roots_agree,
            "sections": sections,
            "sections_agree": sections_agree,
            "secondary_conditions": secondary,
            "source_normalization": queue_row.get("source_normalization") or {},
        },
        "laneb_classification": classification,
        "schema": ROW_SCHEMA,
    }


def _load_inputs(queue_path):
    denominator_paths = sorted(glob.glob(os.path.join(
        REPO, "qamus", "indexes", "largelexicon", "qword-denominator", "*.jsonl")))
    entries_path = os.path.join(REPO, "qamus", "data", "current", "entries.jsonl")
    entry_index_path = os.path.join(
        REPO, "qamus", "indexes", "current", "by-entry-id.json")
    if not denominator_paths:
        raise ValueError("no qword denominator JSONL inputs found")

    denominator_by_row_id = {}
    for path in denominator_paths:
        for row in read_jsonl(path):
            row_id = row.get("row_id")
            if not row_id or row_id in denominator_by_row_id:
                raise ValueError("missing or duplicate denominator row_id %r" % row_id)
            denominator_by_row_id[row_id] = row

    entry_rows = read_jsonl(entries_path)
    entries_by_id = {row.get("id"): row for row in entry_rows if row.get("id")}
    if len(entries_by_id) != len(entry_rows):
        raise ValueError("entries.jsonl has a missing or duplicate id")
    with io.open(entry_index_path, encoding="utf-8") as fh:
        entry_index = json.load(fh)
    if not isinstance(entry_index, dict):
        raise ValueError("by-entry-id.json is not an object")

    queue_rows = read_jsonl(queue_path)
    lane_rows = [
        row for row in queue_rows
        if row.get("primary_resolution_family") == TARGET_FAMILY
    ]
    candidate_entry_ids = sorted({
        carrier.get("entry_id")
        for row in lane_rows
        for carrier in row.get("full_carrier_candidates") or []
        if carrier.get("entry_id")
    })
    missing_entries = sorted(
        entry_id for entry_id in candidate_entry_ids
        if entry_id not in entries_by_id or entry_id not in entry_index
    )
    miss_rate = (float(len(missing_entries)) / len(candidate_entry_ids)
                 if candidate_entry_ids else 0.0)
    if miss_rate > 0.01:
        raise ValueError(
            "STOP: entry lookup miss rate %.4f exceeds 1%% (%d/%d)" %
            (miss_rate, len(missing_entries), len(candidate_entry_ids)))
    if missing_entries:
        raise ValueError(
            "entry lookup is incomplete for classification: %s" % missing_entries)

    index_mismatches = []
    for entry_id in candidate_entry_ids:
        source = entries_by_id[entry_id]
        indexed = entry_index[entry_id]
        for field in ("root", "section"):
            if (source.get(field) or "") != (indexed.get(field) or ""):
                index_mismatches.append("%s:%s" % (entry_id, field))
    if index_mismatches:
        raise ValueError(
            "entry source/index root-section mismatch: %s" % index_mismatches[:20])

    input_paths = [os.path.abspath(queue_path)] + denominator_paths + [
        entries_path, entry_index_path]
    input_sha256 = {
        repo_label(path): sha256_file(path) for path in sorted(input_paths)
    }
    coverage = {
        "candidate_entry_id_count": len(candidate_entry_ids),
        "candidate_entry_lookup_miss_count": len(missing_entries),
        "candidate_entry_lookup_miss_rate": miss_rate,
        "denominator_row_count": len(denominator_by_row_id),
    }
    return (lane_rows, denominator_by_row_id, entries_by_id,
            input_sha256, coverage)


def build_classification(queue_path):
    (lane_rows, denominator_by_row_id, entries_by_id,
     input_sha256, coverage) = _load_inputs(queue_path)

    queue_sha = sha256_file(queue_path)
    if queue_sha != EXPECTED_QUEUE_SHA256:
        raise ValueError(
            "queue sha256 mismatch: expected %s, got %s" %
            (EXPECTED_QUEUE_SHA256, queue_sha))
    if len(lane_rows) != EXPECTED_ROW_COUNT:
        raise ValueError(
            "Lane B row count mismatch: expected %d, got %d" %
            (EXPECTED_ROW_COUNT, len(lane_rows)))

    output_rows = [
        classify_row(row, denominator_by_row_id, entries_by_id)
        for row in lane_rows
    ]
    output_rows.sort(key=lambda row: row["canonical_location"])
    locations = [row["canonical_location"] for row in output_rows]
    if len(locations) != len(set(locations)):
        raise ValueError("duplicate canonical_location in Lane B output")

    counts = collections.Counter(
        row["laneb_classification"] for row in output_rows)
    class_counts = {name: counts.get(name, 0) for name in CLASS_NAMES}
    classified_sum = sum(class_counts.values())
    assert classified_sum == len(lane_rows) == EXPECTED_ROW_COUNT

    representatives = {
        name: [
            row["canonical_location"] for row in output_rows
            if row["laneb_classification"] == name
        ][:5]
        for name in CLASS_NAMES
    }
    class_one = [
        row for row in output_rows
        if row["laneb_classification"] ==
        "same_occurrence_multi_entry_co_citation"
    ]
    roots_breakdown = {
        "false": sum(not row["evidence"]["roots_agree"] for row in class_one),
        "true": sum(row["evidence"]["roots_agree"] for row in class_one),
    }
    terms = [str(class_counts[name]) for name in CLASS_NAMES]
    sum_proof = "SUM PROOF: %s = %d (expected %d)" % (
        " + ".join(terms), classified_sum, EXPECTED_ROW_COUNT)
    summary = {
        "class_counts": class_counts,
        "class_order": list(CLASS_NAMES),
        "classification_artifact": (
            "qamus/indexes/largelexicon/crosswalk-gap/laneb-classification.jsonl"),
        "generator": "tools/classify_gap_multi_candidates.py",
        "input_sha256": input_sha256,
        "lookup_coverage": coverage,
        "mechanical_signal_notes": {
            "competing_nahw_analyses": (
                "No structured deterministic nahw-analysis claim exists in the inputs; no rows assigned."),
            "competing_sarf_analyses": (
                "No structured deterministic verb-form or sarf-analysis claim exists in the inputs; no rows assigned."),
            "normalization_collision": (
                "Assigned only for explicit live_surface_not_in_ayah_index; raw vowel or mark differences sharing norm_strict were retained as evidence, not guessed to be lexical collisions."),
            "precedence": (
                "Explicit normalization failure and repeated-occurrence ambiguity are safety prerequisites; root or section disagreement downgrades otherwise eligible class-1 rows to class 5."),
        },
        "processed_primary_resolution_family": TARGET_FAMILY,
        "processed_row_count": len(output_rows),
        "representative_canonical_locations": representatives,
        "roots_agree_breakdown_inside_class_1": roots_breakdown,
        "schema": SUMMARY_SCHEMA,
        "sum_proof": sum_proof,
    }
    return output_rows, summary


def write_outputs(outdir, rows, summary):
    os.makedirs(outdir, exist_ok=True)
    rows_path = os.path.join(outdir, "laneb-classification.jsonl")
    summary_path = os.path.join(outdir, "laneb-classification.summary.json")
    with io.open(rows_path, "wb") as fh:
        fh.write(canonical_jsonl_bytes(rows))
    summary = dict(summary)
    summary["classification_artifact_sha256"] = sha256_file(rows_path)
    with io.open(summary_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, sort_keys=True, indent=2)
        fh.write("\n")
    return rows_path, summary_path, summary


def _self_test():
    # RED-FIRST EVIDENCE: this fixture was first run while classify_row returned
    # "unimplemented"; the observed failure began "co-citation: expected ...".
    entries = {
        "e1": {"id": "e1", "root": "ك ت ب", "section": "verb", "senses": []},
        "e2": {"id": "e2", "root": "ك ت ب", "section": "verb", "senses": []},
        "e3": {"id": "e3", "root": "ق ر أ", "section": "verb", "senses": []},
    }
    denominator = {
        "q1": {"row_id": "q1", "card_text_sha256": "a" * 64,
               "visible_surface": "كَتَبَ", "visible_surface_norm_strict": "كتب"},
        "q2": {"row_id": "q2", "card_text_sha256": "b" * 64,
               "visible_surface": "كَتَبَ", "visible_surface_norm_strict": "كتب"},
    }

    def fixture(loc, unique=True, entry_ids=("e1", "e2"), secondary=()):
        carriers = [
            {"entry_id": entry_id, "card_id": "c%d" % index,
             "qword_row_id": "q%d" % index, "row_id": "q%d" % index}
            for index, entry_id in enumerate(entry_ids, 1)
        ]
        return {
            "ayah_surface_unique": unique,
            "candidate_card_ids": sorted({c["card_id"] for c in carriers}),
            "candidate_count": len(carriers),
            "candidate_entry_ids": sorted(set(entry_ids)),
            "candidate_equivalence_classes": sorted(set(entry_ids)),
            "candidate_qword_row_ids": sorted({c["qword_row_id"] for c in carriers}),
            "canonical_location": loc,
            "full_carrier_candidates": carriers,
            "primary_resolution_family": TARGET_FAMILY,
            "secondary_conditions": list(secondary),
            "source_normalization": {
                "join_key": "1:1|كتب", "live_surface": "كَتَبَ",
                "norm_strict": "كتب",
            },
        }

    cases = [
        ("co-citation", fixture("1:1:1"),
         "same_occurrence_multi_entry_co_citation"),
        ("root disagreement downgrade", fixture("1:1:2", entry_ids=("e1", "e3")),
         "competing_lexical_senses"),
        ("repeats in ayah", fixture("1:1:3", unique=False),
         "unresolved_occurrence_ambiguity"),
        ("normalization condition", fixture(
            "1:1:4", unique=None, secondary=("live_surface_not_in_ayah_index",)),
         "normalization_collision"),
    ]
    failures = []
    first = []
    for name, row, expected in cases:
        actual = classify_row(row, denominator, entries)
        first.append(actual)
        if actual["laneb_classification"] != expected:
            failures.append(
                "%s: expected %s, got %s" %
                (name, expected, actual["laneb_classification"]))

    second = [
        classify_row(row, denominator, entries)
        for _name, row, _expected in reversed(cases)
    ]
    if canonical_jsonl_bytes(first) != canonical_jsonl_bytes(second):
        failures.append("determinism: output differs under input reordering")

    if failures:
        for failure in failures:
            print("FAIL", failure)
        return 1
    for name, _row, _expected in cases:
        print("ok  ", name)
    print("ok   determinism byte-identical under input reordering")
    print("classify_gap_multi_candidates self-test OK")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--queue")
    parser.add_argument("--outdir")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not args.queue or not args.outdir:
        parser.error("--queue and --outdir are required unless --self-test is used")

    rows, summary = build_classification(args.queue)
    rows_path, summary_path, summary = write_outputs(args.outdir, rows, summary)
    print("class counts:")
    for name in CLASS_NAMES:
        print("  %s: %d" % (name, summary["class_counts"][name]))
    print(summary["sum_proof"])
    print("rows -> %s" % rows_path)
    print("summary -> %s" % summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
