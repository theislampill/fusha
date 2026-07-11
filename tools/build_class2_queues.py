#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build deterministic candidate-only C6+C7 class-2 review queues."""

import argparse
import hashlib
import io
import json
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / ".inputs"
OUTPUT_DIR = REPO / "qamus/indexes/largelexicon/append-queue/class2"
APPEND_QUEUE = REPO / "qamus/indexes/largelexicon/append-queue/append-queue.jsonl"
LOC_SURFACE = REPO / "qamus/indexes/quran-loc-surface/index.jsonl"
SURFACE_DETAIL = REPO / "qamus/indexes/current/by-normalized-surface-detail.json"

TANWIN_MARKS = frozenset("ًٌٍ")
TANWIN_HOST_WHITELIST = frozenset({"إذا", "يومئذ", "حينئذ"})
EXPECTED_TANWIN_LOCS = frozenset({
    "2:18:2", "2:219:7", "6:70:22", "9:8:8", "11:84:12",
    "46:11:18", "78:14:4", "89:19:4",
})
LILLAHI_NOTE = "lillahi_fused_divine_name"

SEGMENTATION_CONTENT_ADJUDICATIONS = {
    "3:193:3": "سمعنا is the verb 'we heard'; معنا was a deep-strip collision",
    "4:103:16": "كانت is a verb; انت was a proclitic-strip collision",
    "5:7:11": "سمعنا is the verb 'we heard'; معنا was a deep-strip collision",
    "7:163:5": "كانت is a verb; انت was a proclitic-strip collision",
    "8:71:9": "فأمكن is a verb; أم was a proclitic-strip collision",
    "12:6:12": "ءال is the content host; ال is not a segmented article here",
    "18:18:17": "لوليت is a verb; ليت was a proclitic-strip collision",
    "33:51:26": "كلهن is a nominal host plus pronoun; لهن was a strip collision",
    "73:9:5": "إلاه is a nominal divine-name host; إلا was a strip collision",
    "86:9:2": "تبلي is a verb; بلي was a proclitic-strip collision",
}

CONFLICT_CONTENT_ADJUDICATIONS = {
    "18:16:2": "O2's لكم surface does not match the canonical اعتزلتموهم target",
    "38:42:1": "O2's هذا surface does not match the canonical اركض target",
    "61:14:25": "the fatha on ب in بنى blocks a prepositional-baa split",
}


def read_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def location_key(location):
    return tuple(int(part) for part in location.split(":"))


def sha256_file(path):
    digest = hashlib.sha256()
    with io.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_tanwin_nominal(row):
    has_tanwin = any(mark in row.get("surface", "") for mark in TANWIN_MARKS)
    host_key = row.get("matched_key") or row.get("norm_strict")
    return has_tanwin and host_key not in TANWIN_HOST_WHITELIST


def strict_key(surface):
    key = "".join(
        ch for ch in surface
        if not (0x064B <= ord(ch) <= 0x0655 or ord(ch) == 0x0670
                or 0x06D6 <= ord(ch) <= 0x06ED)
    )
    return key.replace("ٱ", "ا").replace("ى", "ي").replace("ة", "ه")


def input_paths(input_dir):
    return {
        "function_targets": input_dir / "function-targets.jsonl",
        "funcword_taxonomy": input_dir / "funcword-taxonomy.jsonl",
        "rebind_evidence": input_dir / "rebind-evidence.jsonl",
        "append_queue": APPEND_QUEUE,
        "quran_loc_surface": LOC_SURFACE,
        "normalized_surface_detail": SURFACE_DETAIL,
    }


def compact_target(location, surface, normalized=None):
    target = {"canonical_location": location, "surface": surface}
    if normalized is not None:
        target["norm_strict"] = normalized
    return target


def conflict_criterion(location, taxonomy_row):
    if location in CONFLICT_CONTENT_ADJUDICATIONS:
        return "segmentation_stem", "content_host", CONFLICT_CONTENT_ADJUDICATIONS[location]
    if taxonomy_row.get("entry_exists"):
        return (
            "entry_coverage", "function",
            "canonical surface has the recorded function-entry coverage at %s"
            % taxonomy_row.get("entry_address"),
        )
    return (
        "segmentation_stem", "function",
        "canonical relational stem %s is preserved by O2 segmentation"
        % taxonomy_row.get("function_head"),
    )


def make_boundary_log(post_tanwin_function, f1, f2, c1, tanwin_locs):
    log = []
    for location in sorted(post_tanwin_function ^ set(f2), key=location_key):
        function_row = f1.get(location)
        taxonomy_row = f2.get(location)
        content_row = c1.get(location)
        boundary_note = None
        if location in tanwin_locs:
            criterion, partition = "tanwin", "content_host"
            detail = "tanwin_nominal_v1 overrides a function classification"
        elif function_row and function_row.get("norm_strict") == "لله":
            criterion, partition = "segmentation_stem", "function"
            detail = "segmentation stem له keeps the fused لله token in the pilot function boundary"
            boundary_note = LILLAHI_NOTE
        elif location in SEGMENTATION_CONTENT_ADJUDICATIONS:
            criterion, partition = "segmentation_stem", "content_host"
            detail = SEGMENTATION_CONTENT_ADJUDICATIONS[location]
        elif taxonomy_row and content_row:
            criterion, partition, detail = conflict_criterion(location, taxonomy_row)
        else:
            reason = function_row.get("your_gate_reason", "")
            criterion = "segmentation_stem" if "strip" in reason else "closed_class_key_match"
            partition = "function"
            detail = "O1 function key %s is retained under %s" % (
                function_row.get("matched_key"), reason)
        row = {
            "canonical_location": location,
            "criterion": criterion,
            "detail": detail,
            "o1_classification_after_tanwin": (
                "function" if location in post_tanwin_function else "non_function"
            ),
            "o1_original_classification": "function" if location in f1 else "content_host",
            "o2_classification": "function" if location in f2 else "non_function",
            "partition": partition,
            "resolution": "rule-resolved",
            "surface": (
                (function_row or {}).get("surface")
                or (taxonomy_row or {}).get("surface")
                or content_row["target"]["surface"]
            ),
        }
        if boundary_note:
            row["boundary_note"] = boundary_note
        log.append(row)
    return log


def make_function_row(location, canonical_surface, f1_row, f2_row, surface_detail):
    if f2_row:
        coverage = {
            "authoring_needed": not f2_row.get("entry_exists", False),
            "covering_entry_address": f2_row.get("entry_address"),
            "entry_id": f2_row.get("entry_id"),
        }
        evidence = {"function_head": f2_row.get("function_head"),
                    "source": "funcword-taxonomy.jsonl"}
        target = compact_target(location, canonical_surface, f2_row["surface_norm_strict"])
        particle_class = f2_row.get("particle_class")
        resolution_lane = f2_row.get("resolution_lane")
    else:
        hits = sorted(
            (hit for hit in surface_detail.get(f1_row["matched_key"], [])
             if hit.get("section") == "particle"),
            key=lambda hit: hit.get("eid", ""),
        )
        entry_id = hits[0]["eid"] if len(hits) == 1 else None
        coverage = {
            "authoring_needed": entry_id is None,
            "covering_entry_address": (
                "qamus/data/current/entries.jsonl#id=%s" % entry_id if entry_id else None
            ),
            "entry_id": entry_id,
        }
        evidence = {"matched_key": f1_row["matched_key"],
                    "reason": f1_row["your_gate_reason"],
                    "source": "function-targets.jsonl"}
        target = compact_target(location, canonical_surface, f1_row["norm_strict"])
        particle_class = "supplemental_function_target"
        resolution_lane = "nahw_function_decision"
    row = {
        "candidate_only": True,
        "coverage": coverage,
        "function_evidence": evidence,
        "particle_class": particle_class,
        "resolution_lane": resolution_lane,
        "review_state": "pending",
        "schema": "qamus.class2_funcword_candidate.v1",
        "target": target,
    }
    if f1_row and f1_row.get("norm_strict") == "لله":
        row["boundary_note"] = LILLAHI_NOTE
    return row


def make_rebind_row(location, canonical_surface, content_row, moved_function_row, append_row):
    if content_row:
        host = content_row["content_host"]
        target = dict(content_row["target"])
        target["surface"] = canonical_surface
        misbound = content_row["bound_candidates"]
        proposed = host.get("proposed_host_entries") or []
        abstention = host.get("abstention_class")
        source, rule = "rebind-evidence.jsonl", None
    else:
        target = compact_target(location, canonical_surface, moved_function_row["norm_strict"])
        misbound = {
            "bound_carriers": append_row.get("bound_carriers") or [],
            "competing_analyses": append_row.get("competing_analyses") or [],
            "source_address": (
                "qamus/indexes/largelexicon/append-queue/append-queue.jsonl"
                "#canonical_location=%s/competing_analyses" % location
            ),
        }
        proposed = []
        abstention = "boundary_reclassification_host_evidence_needed"
        source = "function-targets.jsonl"
        rule = "tanwin_nominal_v1" if is_tanwin_nominal(moved_function_row) else "segmentation_stem"
    row = {
        "abstention_class": abstention,
        "candidate_only": True,
        "evidence_source": source,
        "gate": "two_vote_required",
        "misbound_carriers": misbound,
        "proposed_host_entries": proposed,
        "review_state": "pending",
        "schema": "qamus.class2_rebind_candidate.v1",
        "target": target,
    }
    if rule:
        row["adjudication_rule"] = rule
    return row


def build_outputs(input_dir=INPUT_DIR):
    paths = input_paths(pathlib.Path(input_dir))
    function_rows = read_jsonl(paths["function_targets"])
    taxonomy_rows = read_jsonl(paths["funcword_taxonomy"])
    rebind_input = read_jsonl(paths["rebind_evidence"])
    rebind_meta, content_rows = rebind_input[0], rebind_input[1:]
    append_rows = [
        row for row in read_jsonl(paths["append_queue"])
        if row.get("primary_class") == "competing_analyses"
    ]
    loc_surface = {
        row["loc"]: row["surface"] for row in read_jsonl(paths["quran_loc_surface"])
    }
    surface_detail = json.loads(paths["normalized_surface_detail"].read_text(encoding="utf-8"))

    f1 = {row["canonical_location"]: row for row in function_rows}
    f2 = {row["loc"]: row for row in taxonomy_rows}
    c1 = {row["target"]["canonical_location"]: row for row in content_rows}
    append_by_loc = {row["canonical_location"]: row for row in append_rows}
    universe = set(append_by_loc)
    expected_populations = (1045, 1007, 2328, 3868)
    actual_populations = (len(f1), len(f2), len(c1), len(universe))
    if actual_populations != expected_populations:
        raise ValueError("input population drift: %r" % (actual_populations,))
    if set(f1) & set(c1):
        raise ValueError("O1 function and content inputs overlap")

    tanwin_locs = {location for location, row in f1.items() if is_tanwin_nominal(row)}
    if tanwin_locs != EXPECTED_TANWIN_LOCS:
        raise ValueError(
            "tanwin_nominal_v1 mismatch: expected=%s actual=%s" %
            (sorted(EXPECTED_TANWIN_LOCS, key=location_key),
             sorted(tanwin_locs, key=location_key))
        )
    original_conflicts = set(f2) & set(c1)
    if len(original_conflicts) != 19:
        raise ValueError("expected 19 O2-function/O1-content conflicts")

    content_from_f1 = tanwin_locs | set(SEGMENTATION_CONTENT_ADJUDICATIONS)
    conflict_to_content = set(CONFLICT_CONTENT_ADJUDICATIONS)
    conflict_to_function = original_conflicts - conflict_to_content
    function = (set(f1) - content_from_f1) | conflict_to_function
    content_host = (set(c1) - conflict_to_function) | content_from_f1
    remainder = universe - function - content_host
    pos_undetermined = {
        location for location in remainder
        if len(strict_key(loc_surface[location])) <= 2
        and not surface_detail.get(strict_key(loc_surface[location]))
    }
    decidable = remainder - pos_undetermined
    partition_sets = {
        "function": function,
        "content_host": content_host,
        "decidable": decidable,
        "pos_undetermined": pos_undetermined,
    }
    seen = set()
    for name in ("function", "content_host", "decidable", "pos_undetermined"):
        if seen & partition_sets[name]:
            raise ValueError("partition overlap at %s" % name)
        seen.update(partition_sets[name])
    if seen != universe:
        raise ValueError("partition does not cover the 3,868-row universe")
    counts = {name: len(locations) for name, locations in partition_sets.items()}
    expected_counts = {
        "function": 1043, "content_host": 2330,
        "decidable": 493, "pos_undetermined": 2,
    }
    if counts != expected_counts:
        raise ValueError("partition count drift: %r" % counts)
    if rebind_meta["classification_counts"]["decidable_as_posed"] != counts["decidable"]:
        raise ValueError("O1 decidable count drift")
    if rebind_meta["classification_counts"]["abstain_pos_undetermined"] != counts["pos_undetermined"]:
        raise ValueError("O1 POS-undetermined count drift")

    post_tanwin_function = set(f1) - tanwin_locs
    boundary_log = make_boundary_log(post_tanwin_function, f1, f2, c1, tanwin_locs)
    if len(boundary_log) != 76:
        raise ValueError("post-rule symmetric boundary difference is not 76")
    contested = [row for row in boundary_log if row["resolution"] == "contested"]
    conflict_log = []
    for location in sorted(original_conflicts, key=location_key):
        criterion, partition, detail = conflict_criterion(location, f2[location])
        conflict_log.append({
            "canonical_location": location,
            "criterion": criterion,
            "detail": detail,
            "o1_classification": "content_host",
            "o2_classification": "function",
            "partition": partition,
            "resolution": "rule-resolved",
            "surface": c1[location]["target"]["surface"],
            "tanwin_nominal_v1_applies": False,
        })

    funcword_queue = [
        make_function_row(
            location, loc_surface[location], f1.get(location), f2.get(location), surface_detail
        )
        for location in sorted(function, key=location_key)
    ]
    rebind_queue = [
        make_rebind_row(
            location, loc_surface[location], c1.get(location),
            f1.get(location) if location in content_from_f1 else None,
            append_by_loc[location],
        )
        for location in sorted(content_host, key=location_key)
    ]
    input_hashes = {
        name: {"path": path.relative_to(REPO).as_posix(), "sha256": sha256_file(path)}
        for name, path in sorted(paths.items())
    }
    tanwin_log = [
        {
            "adjudication_rule": "tanwin_nominal_v1",
            "canonical_location": location,
            "matched_key": f1[location]["matched_key"],
            "partition": "content_host",
            "surface": f1[location]["surface"],
        }
        for location in sorted(tanwin_locs, key=location_key)
    ]
    manifest = {
        "adjudication_log": {
            "adjudication_order": [
                "tanwin_nominal_v1", "closed_class_key_match",
                "entry_coverage", "segmentation_stem",
            ],
            "boundary_differences_after_rules_1_to_3": boundary_log,
            "conflict_rows": conflict_log,
            "contested": contested,
            "tanwin_nominal_v1": tanwin_log,
        },
        "candidate_only": True,
        "determinism": {
            "generator": "tools/build_class2_queues.py",
            "sort_key": "numeric canonical_location",
            "stdlib_only": True,
            "wall_clock_fields": False,
        },
        "input_hashes_sha256": input_hashes,
        "partition": {
            "counts": counts,
            "decidable_locations": sorted(decidable, key=location_key),
            "derivation": {
                "decidable": "remaining O1 nonqueue locations after the two POS-undetermined identities",
                "pos_undetermined": (
                    "remaining strict surface has at most two base letters and no committed "
                    "normalized-surface entry coverage; count must equal O1 metadata"
                ),
            },
            "pos_undetermined_locations": sorted(pos_undetermined, key=location_key),
            "sum": sum(counts.values()),
            "universe": "append-queue competing_analyses rows",
            "zero_overlap": True,
        },
        "prohibited_mutations": {
            "canonical_facts": 0, "crosswalk": 0, "ledger": 0,
            "public_whitelist": 0,
        },
        "schema": "qamus.class2_partition_manifest.v1",
    }
    disposition_counts = {
        "content_host": sum(row["partition"] == "content_host" for row in conflict_log),
        "function": sum(row["partition"] == "function" for row in conflict_log),
    }
    report = {
        "candidate_only": True,
        "conflict_row_dispositions": {
            "counts": disposition_counts,
            "rows": [
                {"canonical_location": row["canonical_location"],
                 "partition": row["partition"], "criterion": row["criterion"]}
                for row in conflict_log
            ],
        },
        "contested_count": len(contested),
        "generated_by": "tools/build_class2_queues.py",
        "partition_counts": counts,
        "partition_sum": sum(counts.values()),
        "rows_moved_by_tanwin_nominal_v1": len(tanwin_log),
        "schema": "qamus.class2_queue_summary.v1",
    }
    return {
        "funcword_queue": funcword_queue,
        "manifest": manifest,
        "partition_sets": partition_sets,
        "rebind_queue": rebind_queue,
        "report": report,
    }


def serialized_outputs(outputs):
    def jsonl(rows):
        return "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ).encode("utf-8")

    def pretty(value):
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

    return {
        "class2-partition.manifest.json": pretty(outputs["manifest"]),
        "class2-summary.report.json": pretty(outputs["report"]),
        "funcword-queue.jsonl": jsonl(outputs["funcword_queue"]),
        "rebind-queue.jsonl": jsonl(outputs["rebind_queue"]),
    }


class BuilderTests(unittest.TestCase):
    def test_tanwin_rule_catches_binding_eight_exactly(self):
        rows = read_jsonl(INPUT_DIR / "function-targets.jsonl")
        caught = {row["canonical_location"] for row in rows if is_tanwin_nominal(row)}
        self.assertEqual(caught, {
            "2:18:2", "2:219:7", "6:70:22", "9:8:8", "11:84:12",
            "46:11:18", "78:14:4", "89:19:4",
        })

    def test_prefixed_whitelist_host_is_not_tanwin_nominal(self):
        row = {
            "canonical_location": "30:4:10", "surface": "وَيَوْمَئِذٍ",
            "norm_strict": "ويومئذ", "matched_key": "يومئذ",
        }
        self.assertFalse(is_tanwin_nominal(row))

    def test_partition_is_exact_and_mutually_exclusive(self):
        outputs = build_outputs()
        sections = outputs["partition_sets"]
        names = ("function", "content_host", "decidable", "pos_undetermined")
        union = set()
        for name in names:
            self.assertFalse(union & sections[name])
            union.update(sections[name])
        self.assertEqual(len(union), 3868)
        self.assertEqual({name: len(sections[name]) for name in names}, {
            "function": 1043,
            "content_host": 2330,
            "decidable": 493,
            "pos_undetermined": 2,
        })

    def test_serialization_is_byte_identical(self):
        first = serialized_outputs(build_outputs())
        second = serialized_outputs(build_outputs())
        self.assertEqual(first, second)
        self.assertTrue(all(payload.endswith(b"\n") for payload in first.values()))

    def test_queue_targets_preserve_canonical_scripture_surface(self):
        canonical = {
            row["loc"]: row["surface"] for row in read_jsonl(LOC_SURFACE)
        }
        outputs = build_outputs()
        for queue_name in ("funcword_queue", "rebind_queue"):
            for row in outputs[queue_name]:
                target = row["target"]
                self.assertEqual(
                    target["surface"], canonical[target["canonical_location"]]
                )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out-dir", type=pathlib.Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(BuilderTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    outputs = serialized_outputs(build_outputs())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (args.out_dir / name).write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
