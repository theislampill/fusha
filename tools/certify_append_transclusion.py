#!/usr/bin/env python3
"""Mechanically certify append candidates in the append queue only.

This tool does not modify a whitelist, compiler input, live application, or any
deployment surface. ``certified`` is a queue-level verdict about an append
candidate and nothing more.
"""

from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASELINE_SHA = "446a536a432cc819ddfcfcf1bd61dd7601996c94"
QUEUE_PATH = os.path.join(
    REPO, "qamus", "indexes", "largelexicon", "append-queue", "append-queue.jsonl")
REPORT_PATH = os.path.join(
    REPO, "qamus", "indexes", "largelexicon", "append-queue",
    "certification-wave-cal.report.json")
ENTRIES_PATH = os.path.join(REPO, "qamus", "data", "current", "entries.jsonl")
DENOMINATOR_GLOB = os.path.join(
    REPO, "qamus", "indexes", "largelexicon", "qword-denominator", "*.jsonl")
CROSSWALK_GLOB = os.path.join(
    REPO, "qamus", "indexes", "largelexicon", "qword-crosswalk", "*.jsonl")
PUBLIC_BOUNDARY = {"kind": "authored", "lang": "en", "src": "qamus"}
CARRIER_FIELDS = ("entry_id", "card_id", "qword_row_id", "row_id")
PLACEHOLDER_MARKERS = (
    "dry-run carrier preview", "dry run carrier preview", "placeholder", "todo",
    "tbd", "pending gloss",
)
ADDRESS_RE = re.compile(r"^entry:([^/]+)/usage/([1-9]\d*)/examples/([1-9]\d*)$")
BRACKET_INSERTION_RE = re.compile(r"\[[^\[\]]+\]")
TRANSLATOR_PAREN_RE = re.compile(
    r"\((?:i\.e\.|meaning|lit\.|literally|that is|O [^)]+)[^)]*\)", re.IGNORECASE)
PROOF_NAMES = {
    1: "exact_source_address_resolves",
    2: "example_ref_matches_ayah",
    3: "full_d13_carrier_complete",
    4: "dependency_hashes_match",
    5: "source_payload_certified",
    6: "placeholder_denylist_clear",
    7: "no_competing_source_or_sense",
    8: "no_improper_editorial_reproduction",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def stable_json(value, *, pretty=False):
    if pretty:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value):
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def denominator_row_hash(value):
    """Match the crosswalk SSOT's denominator-row fingerprint encoding."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def location_key(value):
    if isinstance(value, str) and re.fullmatch(r"[1-9]\d*:[1-9]\d*:[1-9]\d*", value):
        return tuple(int(part) for part in value.split(":"))
    return (sys.maxsize, sys.maxsize, sys.maxsize, str(value))


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError("malformed JSONL %s:%d: %s" % (path, line_number, exc)) from exc
    return rows


def load_sharded_map(pattern, key):
    result = {}
    for path in sorted(glob.glob(pattern)):
        for row in read_jsonl(path):
            row_id = row.get(key)
            if not row_id or row_id in result:
                raise ValueError("missing/duplicate %s %r in %s" % (key, row_id, path))
            result[row_id] = row
    return result


def index_rows(rows, key):
    result = {}
    for row in rows:
        row_id = row.get(key)
        if not row_id or row_id in result:
            raise ValueError("missing/duplicate %s %r" % (key, row_id))
        result[row_id] = row
    return result


def resolve_address(address, entries):
    match = ADDRESS_RE.fullmatch(address or "")
    if not match:
        return None
    entry_id, usage_text, example_text = match.groups()
    entry = entries.get(entry_id)
    if not entry:
        return None
    usage_index, example_index = int(usage_text), int(example_text)
    usages = entry.get("usage") or []
    if not 1 <= usage_index <= len(usages):
        return None
    examples = usages[usage_index - 1].get("examples") or []
    if not 1 <= example_index <= len(examples):
        return None
    return entry, examples[example_index - 1]


def text_has_placeholder(value):
    if not isinstance(value, str) or not value.strip():
        return True
    folded = " ".join(value.casefold().split())
    return any(marker in folded for marker in PLACEHOLDER_MARKERS)


def entry_gloss_values(entry):
    values = []
    for key in ("definition", "meaning", "gloss"):
        if key in entry:
            values.append((key, entry.get(key)))
    for index, sense in enumerate(entry.get("senses") or [], 1):
        for key, value in sense.items():
            if "gloss" in key.casefold():
                values.append(("senses/%d/%s" % (index, key), value))
    return values


def proof(number, failures, details=None):
    return {
        "proof": number,
        "name": PROOF_NAMES[number],
        "passed": not failures,
        "failure_codes": sorted(set(failures)),
        "details": details or {},
    }


def certify_row(row, entries, denominators, crosswalks):
    sources = row.get("content_sources") or []
    carrier_entry_ids = {
        carrier.get("entry_id") for carrier in row.get("bound_carriers") or []
        if carrier.get("entry_id")
    }
    resolved = []
    p1_failures = []
    for source in sources:
        value = resolve_address(source.get("address"), entries)
        if not value:
            p1_failures.append("P1_SOURCE_ADDRESS_UNRESOLVED")
        else:
            resolved.append((source.get("address"), value[0], value[1]))
            if (value[0].get("id") not in carrier_entry_ids or
                    source.get("entry_id") != value[0].get("id")):
                p1_failures.append("P1_SOURCE_ENTRY_MISMATCH")
    if not sources:
        p1_failures.append("P1_SOURCE_ADDRESS_MISSING")

    ayah = ":".join(str(row.get("canonical_location") or "").split(":")[:2])
    p2_failures = []
    if not resolved:
        p2_failures.append("P2_EXAMPLE_UNAVAILABLE")
    for _, _, example in resolved:
        if example.get("ref") != ayah:
            p2_failures.append("P2_EXAMPLE_REF_MISMATCH")

    carriers = row.get("bound_carriers") or []
    p3_failures = []
    if not carriers:
        p3_failures.append("P3_BOUND_CARRIER_MISSING")
    carrier_context = []
    for carrier in carriers:
        missing = [field for field in CARRIER_FIELDS if not carrier.get(field)]
        if missing:
            p3_failures.append("P3_CARRIER_FIELDS_MISSING")
        denominator = denominators.get(carrier.get("qword_row_id"))
        crosswalk = crosswalks.get(carrier.get("row_id"))
        if denominator is None:
            p3_failures.append("P3_DENOMINATOR_ROW_MISSING")
        if crosswalk is None:
            p3_failures.append("P3_CROSSWALK_ROW_MISSING")
        if crosswalk is not None and any(
                crosswalk.get(field) != carrier.get(field) for field in CARRIER_FIELDS):
            p3_failures.append("P3_CARRIER_CROSSWALK_MISMATCH")
        carrier_context.append((carrier, denominator, crosswalk))

    queue_hashes = row.get("dependency_hashes") or {}
    p4_failures = []
    checked_hashes = []
    if not carrier_context:
        p4_failures.append("P4_CARRIER_UNAVAILABLE")
    for carrier, denominator, crosswalk in carrier_context:
        if denominator is None or crosswalk is None:
            p4_failures.append("P4_DEPENDENCY_ROW_UNAVAILABLE")
            continue
        expected_binding = stable_hash(crosswalk)
        expected_denominator = denominator_row_hash(denominator)
        binding_key = "binding:%s" % carrier["row_id"]
        denominator_key = "source:%s" % carrier["qword_row_id"]
        checked_hashes.extend([
            {"key": binding_key, "sha256": expected_binding},
            {"key": denominator_key, "sha256": expected_denominator},
        ])
        if queue_hashes.get(binding_key) != expected_binding:
            p4_failures.append("P4_BINDING_HASH_MISMATCH")
        if queue_hashes.get(denominator_key) != expected_denominator:
            p4_failures.append("P4_DENOMINATOR_HASH_MISMATCH")
        crosswalk_dependencies = {
            dependency.get("id"): dependency.get("sha256")
            for dependency in crosswalk.get("source_dependencies") or []
            if dependency.get("id")
        }
        if crosswalk_dependencies.get(carrier["qword_row_id"]) != expected_denominator:
            p4_failures.append("P4_CROSSWALK_DENOMINATOR_HASH_MISMATCH")

    p5_failures = []
    if not resolved:
        p5_failures.append("P5_SOURCE_PAYLOAD_UNAVAILABLE")
    for _, _, example in resolved:
        if not isinstance(example.get("ar"), str) or not example["ar"].strip():
            p5_failures.append("P5_AUTHORED_AR_MISSING")
        if not isinstance(example.get("en"), str) or not example["en"].strip():
            p5_failures.append("P5_AUTHORED_EN_MISSING")
    for _, _, crosswalk in carrier_context:
        if crosswalk is None or crosswalk.get("public_boundary") != PUBLIC_BOUNDARY:
            p5_failures.append("P5_PUBLIC_BOUNDARY_MISMATCH")

    p6_failures = []
    for address, entry, example in resolved:
        for label, value in [("%s/ar" % address, example.get("ar")),
                             ("%s/en" % address, example.get("en"))] + entry_gloss_values(entry):
            if text_has_placeholder(value):
                p6_failures.append("P6_PLACEHOLDER_TEXT")
                break

    entry_ids = sorted({carrier.get("entry_id") for carrier in carriers if carrier.get("entry_id")})
    p7_failures = []
    if row.get("competing_analyses"):
        p7_failures.append("P7_COMPETING_ANALYSES_OUT_OF_SCOPE")
    if not entry_ids:
        p7_failures.append("P7_ENTRY_CLASS_MISSING")
    elif len(entry_ids) > 1:
        root_sections = {
            ((entries.get(entry_id) or {}).get("root"),
             (entries.get(entry_id) or {}).get("section")) for entry_id in entry_ids
        }
        example_texts = {(example.get("ar"), example.get("en")) for _, _, example in resolved}
        if len(root_sections) != 1 or len(example_texts) != 1 or len(resolved) != len(entry_ids):
            p7_failures.append("P7_MULTI_ENTRY_DISAGREEMENT")
    else:
        entry_classes = {
            entry_ids[0]: ((entries.get(entry_ids[0]) or {}).get("root"),
                           (entries.get(entry_ids[0]) or {}).get("section"))
        }

    p8_failures = []
    editorial_flags = []
    for address, _, example in resolved:
        english = example.get("en") or ""
        bracket_count = len(BRACKET_INSERTION_RE.findall(english))
        parentheticals = TRANSLATOR_PAREN_RE.findall(english)
        if bracket_count >= 2:
            editorial_flags.append({"address": address, "flag": "multiple_square_bracket_insertions"})
        if parentheticals:
            editorial_flags.append({"address": address, "flag": "translator_style_parenthetical"})
    if editorial_flags:
        p8_failures.append("P8_EDITORIAL_REPRODUCTION_FLAG")

    proofs = [
        proof(1, p1_failures, {"addresses": sorted(source.get("address") for source in sources
                                                   if source.get("address"))}),
        proof(2, p2_failures, {"expected_ayah": ayah}),
        proof(3, p3_failures, {"carrier_count": len(carriers)}),
        proof(4, p4_failures, {"checked_hashes": sorted(checked_hashes, key=lambda x: x["key"])}),
        proof(5, p5_failures, {"required_public_boundary": PUBLIC_BOUNDARY}),
        proof(6, p6_failures),
        proof(7, p7_failures, {"entry_ids": entry_ids}),
        proof(8, p8_failures, {"editorial_flags": editorial_flags}),
    ]
    failure_codes = sorted({code for item in proofs for code in item["failure_codes"]})
    certified = not failure_codes
    updated = copy.deepcopy(row)
    updated["review_state"] = "certified" if certified else "review_required"
    updated["certified"] = certified
    updated["certification_evidence"] = {
        "baseline_sha": BASELINE_SHA,
        "failure_codes": failure_codes,
        "proofs": proofs,
        "resolution_method": "direct_transclusion" if certified else "blocked",
        "source_addresses": sorted(address for address, _, _ in resolved),
    }
    return updated


def eligible_rows(queue):
    return sorted((row for row in queue
                   if row.get("primary_class") == "exact_certified_transclusion"
                   and row.get("binding_count") == 1),
                  key=lambda row: location_key(row.get("canonical_location")))


def render_queue(rows):
    ordered = sorted(rows, key=lambda row: location_key(row.get("canonical_location")))
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered).encode("utf-8")


def calibrate(queue, entries, denominators, crosswalks, limit=200):
    selected = eligible_rows(queue)[:limit]
    selected_locations = {row["canonical_location"] for row in selected}
    updated_by_location = {
        row["canonical_location"]: certify_row(row, entries, denominators, crosswalks)
        for row in selected
    }
    updated_queue = [updated_by_location.get(row.get("canonical_location"), copy.deepcopy(row))
                     for row in queue]
    proof_counts = {}
    failure_counts = Counter()
    method_counts = Counter()
    for row in updated_by_location.values():
        evidence = row["certification_evidence"]
        method_counts[evidence["resolution_method"]] += 1
        failure_counts.update(evidence["failure_codes"])
        for item in evidence["proofs"]:
            counts = proof_counts.setdefault(str(item["proof"]), {"passed": 0, "failed": 0})
            counts["passed" if item["passed"] else "failed"] += 1

    proof1_failures = proof_counts.get("1", {}).get("failed", 0)
    threshold = int(limit * 0.20)
    stop_triggered = proof1_failures > threshold
    wave_bytes = "".join(
        json.dumps(updated_by_location[loc], ensure_ascii=False, sort_keys=True) + "\n"
        for loc in sorted(selected_locations, key=location_key)).encode("utf-8")
    report = {
        "schema": "qamus.append_queue_certification_wave_report.v1",
        "artifact_scope": "append_candidate_queue_only",
        "baseline_sha": BASELINE_SHA,
        "generator": "python tools/certify_append_transclusion.py",
        "selection": {
            "class": "exact_certified_transclusion",
            "binding_count": 1,
            "limit": limit,
            "ordering": "numeric canonical_location S:A:W",
            "selected_count": len(selected),
            "first_location": selected[0]["canonical_location"] if selected else None,
            "last_location": selected[-1]["canonical_location"] if selected else None,
        },
        "proof_counts": proof_counts,
        "failure_code_counts": dict(sorted(failure_counts.items())),
        "resolution_method_counts": dict(sorted(method_counts.items())),
        "stop_condition": {
            "rule": "proof 1 failures > 20% of requested calibration limit",
            "proof_1_failures": proof1_failures,
            "threshold_rows": threshold,
            "triggered": stop_triggered,
        },
        "wave_sha256": sha256_bytes(wave_bytes),
    }
    return updated_queue, report, stop_triggered


def verify_baseline_sources():
    source_paths = [
        "qamus/data/current/entries.jsonl",
        "qamus/indexes/largelexicon/qword-denominator",
        "qamus/indexes/largelexicon/qword-crosswalk",
    ]
    result = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_SHA, "--", *source_paths],
        cwd=REPO, check=False)
    if result.returncode not in (0, 1):
        raise SystemExit("STOP: unable to verify baseline source paths")
    if result.returncode == 1:
        raise SystemExit("STOP: certification source paths differ from baseline %s" % BASELINE_SHA)
    return source_paths


def _fixture_context():
    example = {"ar": "إِنَّا أَعْطَيْنَاكَ", "en": "Indeed, We have granted you", "ref": "1:1"}
    entry = {
        "id": "e1", "root": "ع ط و", "section": "verb",
        "definition": "to grant", "meaning": "to grant",
        "senses": [{"ar": "أَعْطَى", "gloss": "to grant"}],
        "usage": [{"examples": [example]}],
    }
    denominator = {
        "row_id": "q1", "entry_id": "e1", "card_id": "e1:u1:e1",
        "qword_index": 1, "visible_surface": "إِنَّا",
    }
    crosswalk = {
        "row_id": "cw1", "entry_id": "e1", "card_id": "e1:u1:e1",
        "qword_row_id": "q1", "public_boundary": PUBLIC_BOUNDARY,
        "source_dependencies": [{"id": "q1", "kind": "qword_denominator_row",
                                 "sha256": denominator_row_hash(denominator)}],
    }
    row = {
        "schema": "qamus.append_queue_row.v1", "canonical_location": "1:1:1",
        "primary_class": "exact_certified_transclusion", "binding_count": 1,
        "bound_carriers": [{field: crosswalk[field] for field in CARRIER_FIELDS}],
        "content_sources": [{"address": "entry:e1/usage/1/examples/1", "entry_id": "e1"}],
        "dependency_hashes": {"binding:cw1": stable_hash(crosswalk),
                              "source:q1": denominator_row_hash(denominator)},
        "competing_analyses": [], "review_state": "pending", "certified": False,
    }
    return row, {"e1": entry}, {"q1": denominator}, {"cw1": crosswalk}


def _self_test():
    failures = []

    def check(name, condition):
        print(("ok   " if condition else "FAIL ") + name)
        if not condition:
            failures.append(name)

    row, entries, denominators, crosswalks = _fixture_context()
    good = certify_row(row, entries, denominators, crosswalks)
    check("all eight proofs certify an append candidate", good["certified"] is True)
    check("no deployment-readiness field is introduced",
          not any("deploy" in key or "ready" in key for key in good))

    cases = []
    bad = copy.deepcopy(row); bad["content_sources"][0]["address"] += "/missing"
    cases.append(("proof 1 unresolved address", bad, entries, denominators, crosswalks, 1))
    bad_entries = copy.deepcopy(entries); bad_entries["e1"]["usage"][0]["examples"][0]["ref"] = "1:2"
    cases.append(("proof 2 wrong ref", row, bad_entries, denominators, crosswalks, 2))
    bad = copy.deepcopy(row); bad["bound_carriers"][0]["card_id"] = None
    cases.append(("proof 3 missing carrier", bad, entries, denominators, crosswalks, 3))
    bad = copy.deepcopy(row); bad["dependency_hashes"]["source:q1"] = "0" * 64
    cases.append(("proof 4 hash mismatch", bad, entries, denominators, crosswalks, 4))
    bad_crosswalks = copy.deepcopy(crosswalks); bad_crosswalks["cw1"]["public_boundary"] = {}
    bad = copy.deepcopy(row); bad["dependency_hashes"]["binding:cw1"] = stable_hash(bad_crosswalks["cw1"])
    cases.append(("proof 5 public boundary", bad, entries, denominators, bad_crosswalks, 5))
    bad_entries = copy.deepcopy(entries); bad_entries["e1"]["usage"][0]["examples"][0]["en"] = "TBD"
    cases.append(("proof 6 placeholder trap", row, bad_entries, denominators, crosswalks, 6))

    row2 = copy.deepcopy(row)
    row2["binding_count"] = 2
    row2["bound_carriers"].append({"entry_id": "e2", "card_id": "e2:u1:e1",
                                    "qword_row_id": "q2", "row_id": "cw2"})
    entries2 = copy.deepcopy(entries); entries2["e2"] = copy.deepcopy(entries2["e1"])
    entries2["e2"].update({"id": "e2", "root": "خ ل ق", "section": "noun"})
    row2["content_sources"].append({"address": "entry:e2/usage/1/examples/1", "entry_id": "e2"})
    denom2 = copy.deepcopy(denominators); denom2["q2"] = copy.deepcopy(denom2["q1"])
    denom2["q2"].update({"row_id": "q2", "entry_id": "e2", "card_id": "e2:u1:e1"})
    cross2 = copy.deepcopy(crosswalks); cross2["cw2"] = copy.deepcopy(cross2["cw1"])
    cross2["cw2"].update({"row_id": "cw2", "entry_id": "e2", "card_id": "e2:u1:e1",
                           "qword_row_id": "q2", "source_dependencies": [{"id": "q2",
                           "kind": "qword_denominator_row",
                           "sha256": denominator_row_hash(denom2["q2"])}]})
    row2["dependency_hashes"].update({"binding:cw2": stable_hash(cross2["cw2"]),
                                      "source:q2": denominator_row_hash(denom2["q2"])})
    cases.append(("proof 7 multi-entry disagreement", row2, entries2, denom2, cross2, 7))
    bad_entries = copy.deepcopy(entries)
    bad_entries["e1"]["usage"][0]["examples"][0]["en"] = "[They] received [the gift]."
    cases.append(("proof 8 bracket editorial trap", row, bad_entries, denominators, crosswalks, 8))

    for name, test_row, test_entries, test_denominators, test_crosswalks, proof_number in cases:
        result = certify_row(test_row, test_entries, test_denominators, test_crosswalks)
        item = result["certification_evidence"]["proofs"][proof_number - 1]
        check(name, result["certified"] is False and item["passed"] is False)

    queue = [copy.deepcopy(row), dict(copy.deepcopy(row), canonical_location="1:1:2")]
    forward, report_forward, _ = calibrate(queue, entries, denominators, crosswalks, limit=2)
    reverse, report_reverse, _ = calibrate(list(reversed(queue)), entries, denominators, crosswalks, limit=2)
    check("proof 9 order-independent byte-identical queue output",
          render_queue(forward) == render_queue(reverse))
    check("proof 9 order-independent byte-identical report output",
          stable_json(report_forward, pretty=True) == stable_json(report_reverse, pretty=True))

    if failures:
        raise SystemExit("FAIL - %d certification self-test(s): %s" %
                         (len(failures), ", ".join(failures)))
    print("PASS - certification self-test (%d checks)" % 12)


def main():
    parser = argparse.ArgumentParser(
        description="Certify a deterministic calibration wave of append candidates")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--queue", default=QUEUE_PATH)
    parser.add_argument("--entries", default=ENTRIES_PATH)
    parser.add_argument("--denominator-glob", default=DENOMINATOR_GLOB)
    parser.add_argument("--crosswalk-glob", default=CROSSWALK_GLOB)
    parser.add_argument("--report", default=REPORT_PATH)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    if args.self_test:
        _self_test()
        return
    if not 1 <= args.limit <= 200:
        raise SystemExit("limit must be between 1 and 200")

    queue = read_jsonl(args.queue)
    baseline_source_paths = verify_baseline_sources()
    entries = index_rows(read_jsonl(args.entries), "id")
    denominators = load_sharded_map(args.denominator_glob, "row_id")
    crosswalks = load_sharded_map(args.crosswalk_glob, "row_id")
    updated, report, stop_triggered = calibrate(
        queue, entries, denominators, crosswalks, limit=args.limit)
    if report["selection"]["selected_count"] != args.limit:
        raise SystemExit("STOP: requested %d rows, selected %d" %
                         (args.limit, report["selection"]["selected_count"]))
    if stop_triggered:
        raise SystemExit("STOP: proof 1 failures exceed 20%%; no artifacts written")

    queue_bytes = render_queue(updated)
    reordered_bytes = render_queue(calibrate(
        list(reversed(queue)), dict(reversed(list(entries.items()))),
        dict(reversed(list(denominators.items()))), dict(reversed(list(crosswalks.items()))),
        limit=args.limit)[0])
    if queue_bytes != reordered_bytes:
        raise SystemExit("STOP: order-independence proof failed; no artifacts written")
    report["determinism"] = {
        "byte_identical_under_reordered_inputs": True,
        "queue_output_sha256": sha256_bytes(queue_bytes),
        "reordered_queue_output_sha256": sha256_bytes(reordered_bytes),
    }
    report["baseline_source_verification"] = {
        "paths": baseline_source_paths,
        "unchanged_from_baseline": True,
    }

    with io.open(args.queue, "wb") as handle:
        handle.write(queue_bytes)
    with io.open(args.report, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(stable_json(report, pretty=True))
    print("PASS - calibrated %d append candidates (%d direct, %d blocked)" % (
        args.limit, report["resolution_method_counts"].get("direct_transclusion", 0),
        report["resolution_method_counts"].get("blocked", 0)))


if __name__ == "__main__":
    main()
