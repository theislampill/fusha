#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the three dogfood-acceleration ledger contracts against their schemas.

Covers:
  * qamus/schemas/dogfood-event-ledger.schema.json        (JSONL, one flywheel event per row)
  * qamus/schemas/acceleration-ledger.schema.json         (JSONL, one tranche/family metric row)
  * qamus/schemas/vn-compounding-impact-report.schema.json (JSON, one per-tranche report)

The repository intentionally has no third-party ``jsonschema`` dependency; this
validator implements only the Draft 2020-12 keywords those three schemas use.

Beyond schema shape it enforces the honesty rules the schemas document:
  * every metric object carries measurement_basis (schema-required);
  * measurement_basis=not_measured  => value must be null;
  * measurement_basis in {measured, estimated} => value must be non-null;
  * a row/report claiming acceleration (acceleration_claimed=true) must cite at
    least one NON-rowcount metric with measurement_basis=measured — acceleration
    is never claimed from row counts alone;
  * every artifact/evidence path must exist in the repository;
  * dogfood event chains must start at defect_found, keep timestamps
    non-decreasing, and resolve caused_by_event references within the file.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(ROOT, "qamus", "schemas")

EVENT_SCHEMA = "dogfood-event-ledger.schema.json"
ACCEL_SCHEMA = "acceleration-ledger.schema.json"
IMPACT_SCHEMA = "vn-compounding-impact-report.schema.json"

# Committed samples validated by default (and by the regression harness).
DEFAULT_TARGETS = (
    ("event", "qamus/examples/dogfood_event_ledger_vn01_crosswalk_false_gate.sample.jsonl"),
    ("accel", "qamus/examples/acceleration_ledger_vn02.sample.jsonl"),
    ("impact", "qamus/examples/vn_compounding_impact_report_vn02.sample.json"),
)

# Metrics that are pure row/artifact counts. A measured value here proves output
# volume, not acceleration. Acceleration claims must cite something outside
# these sets: a rate, a time, a reduction, or coverage reach.
ACCEL_ROWCOUNT_METRICS = frozenset({
    "candidate_population",
    "certified_population",
    "manual_reviews",
    "projector_generated_rows",
    "hand_authored_rows",
    "rules_added",
    "fixtures_added",
    "later_rows_unlocked",
    "blockers_converted_to_fast_path",
    "public_regressions_prevented",
})
ACCEL_NON_ROWCOUNT_METRICS = frozenset({
    "review_minutes",
    "two_vote_rate",
    "abstention_rate",
    "false_projection_rate",
    "candidate_to_certified_conversion_time",
    "compiler_reach_before",
    "compiler_reach_after",
})
IMPACT_NON_ROWCOUNT_METRICS = frozenset({
    ("automation_outcomes", "review_reduction_pct"),
    ("graph_outcomes", "forward_trace_rate"),
    ("graph_outcomes", "reverse_trace_rate"),
})
IMPACT_SECTIONS = (
    "content_outcomes",
    "graph_outcomes",
    "skill_outcomes",
    "automation_outcomes",
    "pedagogy_outcomes",
)


def load_schema(name):
    with io.open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_ref(ref, root_schema):
    if not ref.startswith("#/"):
        raise ValueError("unsupported $ref: %s" % ref)
    node = root_schema
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _type_matches(value, expected):
    expected_types = [expected] if isinstance(expected, str) else expected
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return any(checks[name](value) for name in expected_types)


def schema_errors(value, schema, root_schema, path="$"):
    """Minimal Draft 2020-12 checker for the keywords these schemas use."""
    if "$ref" in schema:
        return schema_errors(value, _resolve_ref(schema["$ref"], root_schema), root_schema, path)
    errors = []

    def add(message):
        errors.append("%s: %s" % (path, message))

    if "type" in schema and not _type_matches(value, schema["type"]):
        add("expected type %r, got %s" % (schema["type"], type(value).__name__))
        return errors
    if "const" in schema and value != schema["const"]:
        add("expected const %r" % (schema["const"],))
    if "enum" in schema and value not in schema["enum"]:
        add("value %r not in enum" % (value,))
    if "pattern" in schema and isinstance(value, str) and re.search(schema["pattern"], value) is None:
        add("value %r does not match %r" % (value, schema["pattern"]))
    if "minLength" in schema and isinstance(value, str) and len(value) < schema["minLength"]:
        add("string shorter than %d" % schema["minLength"])
    if "minimum" in schema and isinstance(value, (int, float)) and not isinstance(value, bool) \
            and value < schema["minimum"]:
        add("number below %s" % schema["minimum"])
    if "minItems" in schema and isinstance(value, list) and len(value) < schema["minItems"]:
        add("array shorter than %d" % schema["minItems"])
    if "maxItems" in schema and isinstance(value, list) and len(value) > schema["maxItems"]:
        add("array longer than %d" % schema["maxItems"])
    if "minProperties" in schema and isinstance(value, dict) and len(value) < schema["minProperties"]:
        add("object has fewer than %d properties" % schema["minProperties"])
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                add("missing required property %r" % required)
        additional = schema.get("additionalProperties", True)
        for key in value:
            if key in properties:
                errors.extend(schema_errors(value[key], properties[key], root_schema,
                                            "%s.%s" % (path, key)))
            elif additional is False:
                add("additional property %r is not allowed" % key)
            elif isinstance(additional, dict):
                errors.extend(schema_errors(value[key], additional, root_schema,
                                            "%s.%s" % (path, key)))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], root_schema,
                                        "%s[%d]" % (path, index)))
    return errors


def repo_path_exists(relpath):
    return os.path.exists(os.path.join(ROOT, str(relpath).replace("/", os.sep)))


def check_paths_exist(row, field, prefix, errors, allow_missing=()):
    for relpath in row.get(field) or []:
        if str(relpath) in allow_missing:
            continue
        if not repo_path_exists(relpath):
            errors.append("%s: %s references missing repo path %s" % (prefix, field, relpath))


def check_metric_honesty(metric, prefix, errors):
    if not isinstance(metric, dict):
        return
    basis = metric.get("measurement_basis")
    value = metric.get("value")
    if basis == "not_measured" and value is not None:
        errors.append("%s: measurement_basis=not_measured requires value null" % prefix)
    if basis in ("measured", "estimated") and value is None:
        errors.append("%s: measurement_basis=%s requires a non-null value" % (prefix, basis))


def _iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                yield line_no, json.loads(line)


def validate_event_ledger(path):
    schema = load_schema(EVENT_SCHEMA)
    errors, rows = [], []
    try:
        for line_no, row in _iter_jsonl(path):
            rows.append((line_no, row))
    except Exception as exc:
        return 0, ["%s: bad JSONL (%s)" % (path, exc)]
    if not rows:
        return 0, ["%s: zero events" % path]
    seen_ids = set()
    prev_ts = None
    for line_no, row in rows:
        prefix = "line %d" % line_no
        errors.extend("%s %s" % (prefix, err) for err in schema_errors(row, schema, schema))
        if isinstance(row, dict):
            event_id = row.get("event_id")
            if event_id in seen_ids:
                errors.append("%s: duplicate event_id %r" % (prefix, event_id))
            seen_ids.add(event_id)
            ts = row.get("timestamp_utc")
            if prev_ts is not None and isinstance(ts, str) and ts < prev_ts:
                errors.append("%s: timestamp_utc %s decreases (chain must be ordered)" % (prefix, ts))
            if isinstance(ts, str):
                prev_ts = ts
            check_paths_exist(row, "artifact_paths", prefix, errors)
    first_row = rows[0][1]
    if isinstance(first_row, dict) and first_row.get("loop_stage") != "defect_found":
        errors.append("line %d: event chain must start at defect_found" % rows[0][0])
    for line_no, row in rows:
        cause = isinstance(row, dict) and row.get("caused_by_event")
        if cause and cause not in seen_ids:
            errors.append("line %d: caused_by_event %r not found in file" % (line_no, cause))
    return len(rows), errors


def validate_accel_ledger(path):
    schema = load_schema(ACCEL_SCHEMA)
    errors, count = [], 0
    try:
        rows = list(_iter_jsonl(path))
    except Exception as exc:
        return 0, ["%s: bad JSONL (%s)" % (path, exc)]
    if not rows:
        return 0, ["%s: zero acceleration rows" % path]
    for line_no, row in rows:
        count += 1
        prefix = "line %d" % line_no
        errors.extend("%s %s" % (prefix, err) for err in schema_errors(row, schema, schema))
        if not isinstance(row, dict):
            continue
        metrics = row.get("metrics") or {}
        for name, metric in metrics.items() if isinstance(metrics, dict) else ():
            check_metric_honesty(metric, "%s metrics.%s" % (prefix, name), errors)
        check_paths_exist(row, "evidence_paths", prefix, errors)
        if row.get("acceleration_claimed") is True and isinstance(metrics, dict):
            cited = [
                name for name in ACCEL_NON_ROWCOUNT_METRICS
                if isinstance(metrics.get(name), dict)
                and metrics[name].get("measurement_basis") == "measured"
                and metrics[name].get("value") is not None
            ]
            if not cited:
                errors.append(
                    "%s: acceleration_claimed=true but no non-rowcount metric has "
                    "measurement_basis=measured — acceleration may not be claimed "
                    "from row counts alone" % prefix)
    return count, errors


def validate_impact_report(path):
    schema = load_schema(IMPACT_SCHEMA)
    errors = []
    try:
        with io.open(path, encoding="utf-8") as handle:
            report = json.load(handle)
    except Exception as exc:
        return 0, ["%s: bad JSON (%s)" % (path, exc)]
    errors.extend(schema_errors(report, schema, schema))
    if not isinstance(report, dict):
        return 1, errors
    for section in IMPACT_SECTIONS:
        block = report.get(section)
        if not isinstance(block, dict):
            continue
        for name, metric in block.items():
            check_metric_honesty(metric, "%s.%s" % (section, name), errors)
    check_paths_exist(report, "evidence_paths", "report", errors)
    if report.get("acceleration_claimed") is True:
        cited = []
        for section, name in IMPACT_NON_ROWCOUNT_METRICS:
            metric = (report.get(section) or {}).get(name) if isinstance(report.get(section), dict) else None
            if isinstance(metric, dict) and metric.get("measurement_basis") == "measured" \
                    and metric.get("value") is not None:
                cited.append("%s.%s" % (section, name))
        if not cited:
            errors.append(
                "report: acceleration_claimed=true but no non-rowcount metric "
                "(review_reduction_pct / trace rates) has measurement_basis=measured — "
                "acceleration may not be claimed from row counts alone")
    return 1, errors


VALIDATORS = {
    "event": validate_event_ledger,
    "accel": validate_accel_ledger,
    "impact": validate_impact_report,
}


def _metric(value, basis, **extra):
    metric = {"value": value, "measurement_basis": basis}
    metric.update(extra)
    return metric


def _good_event(event_id="dogfood-event:selftest.defect", stage="defect_found",
                ts="2026-07-06T10:00:00Z"):
    return {
        "schema": "qamus.dogfood_event.v1",
        "event_id": event_id,
        "timestamp_utc": ts,
        "tranche": "VN-01",
        "family": "source_crosswalk_false_gate",
        "loop_stage": stage,
        "occurrence_locs": ["quran:33:63:1"],
        "artifact_paths": ["docs/vn-tranche-completion-playbook.md"],
        "counts": {"rows_affected": 1627},
    }


def _good_accel_metrics():
    metrics = {}
    for name in ACCEL_ROWCOUNT_METRICS:
        metrics[name] = _metric(1, "measured")
    for name in ACCEL_NON_ROWCOUNT_METRICS:
        metrics[name] = _metric(None, "not_measured")
    metrics["compiler_reach_before"] = _metric(62.17, "measured", unit="percent")
    metrics["compiler_reach_after"] = _metric(100.0, "measured", unit="percent")
    return metrics


def _good_accel_row():
    return {
        "schema": "qamus.acceleration_ledger.v1",
        "ledger_id": "acceleration:selftest.vn02",
        "tranche": "VN-02",
        "family": "rich_hover",
        "window": "v095-v141 + n0091-n0135",
        "acceleration_claimed": True,
        "metrics": _good_accel_metrics(),
        "evidence_paths": ["docs/vn-tranche-completion-playbook.md"],
    }


def self_test():
    failures = []

    def expect(label, condition):
        status = "ok" if condition else "FAIL"
        print("  [%s] %s" % (status, label))
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="accel-ledger-") as tmpdir:
        def write(name, text):
            path = os.path.join(tmpdir, name)
            with io.open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            return path

        # --- dogfood event ledger ---
        good_chain = [
            _good_event(),
            dict(_good_event("dogfood-event:selftest.fact", "typed_fact",
                             "2026-07-06T11:00:00Z"),
                 caused_by_event="dogfood-event:selftest.defect"),
        ]
        path = write("events.good.jsonl",
                     "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in good_chain))
        count, errors = validate_event_ledger(path)
        expect("good event chain validates", count == 2 and not errors)

        bad = _good_event()
        bad["loop_stage"] = "vibes"
        path = write("events.badstage.jsonl", json.dumps(bad, ensure_ascii=False) + "\n")
        expect("RED: unknown loop_stage rejected", bool(validate_event_ledger(path)[1]))

        bad = _good_event()
        bad["artifact_paths"] = ["docs/this-file-does-not-exist-xyz.md"]
        path = write("events.badpath.jsonl", json.dumps(bad, ensure_ascii=False) + "\n")
        expect("RED: missing artifact path rejected", bool(validate_event_ledger(path)[1]))

        bad = _good_event(stage="deploy")
        path = write("events.nostart.jsonl", json.dumps(bad, ensure_ascii=False) + "\n")
        expect("RED: chain not starting at defect_found rejected",
               bool(validate_event_ledger(path)[1]))

        # --- acceleration ledger ---
        path = write("accel.good.jsonl", json.dumps(_good_accel_row(), ensure_ascii=False) + "\n")
        count, errors = validate_accel_ledger(path)
        expect("good acceleration row validates", count == 1 and not errors)

        bad = _good_accel_row()
        del bad["metrics"]["review_minutes"]["measurement_basis"]
        path = write("accel.nobasis.jsonl", json.dumps(bad, ensure_ascii=False) + "\n")
        expect("RED: metric missing measurement_basis rejected",
               bool(validate_accel_ledger(path)[1]))

        bad = _good_accel_row()
        # Row counts all "measured", every non-rowcount metric unmeasured, yet
        # acceleration claimed: the exact dishonesty this ledger exists to block.
        for name in ACCEL_NON_ROWCOUNT_METRICS:
            bad["metrics"][name] = _metric(None, "not_measured")
        bad["acceleration_claimed"] = True
        path = write("accel.rowcount.jsonl", json.dumps(bad, ensure_ascii=False) + "\n")
        errors = validate_accel_ledger(path)[1]
        expect("RED: acceleration claimed from row counts alone rejected",
               any("row counts alone" in err for err in errors))

        bad = _good_accel_row()
        bad["metrics"]["manual_reviews"] = _metric(12, "not_measured")
        path = write("accel.dishonest.jsonl", json.dumps(bad, ensure_ascii=False) + "\n")
        expect("RED: not_measured metric with a value rejected",
               bool(validate_accel_ledger(path)[1]))

    # --- committed samples must validate (schema+samples ship together) ---
    for kind, relpath in DEFAULT_TARGETS:
        full = os.path.join(ROOT, relpath.replace("/", os.sep))
        if not os.path.exists(full):
            expect("committed sample present: %s" % relpath, False)
            continue
        count, errors = VALIDATORS[kind](full)
        for err in errors[:10]:
            print("    -", err)
        expect("committed sample validates: %s" % relpath, count >= 1 and not errors)

    if failures:
        print("SELF-TEST FAIL (%d)" % len(failures))
        return 1
    print("PASS — acceleration ledger validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--kind", choices=sorted(VALIDATORS), help="validate one file of this kind")
    parser.add_argument("path", nargs="?", help="file to validate when --kind is given")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if args.kind:
        if not args.path:
            parser.error("path is required with --kind")
        count, errors = VALIDATORS[args.kind](args.path)
        targets = [(args.kind, args.path, count, errors)]
    else:
        targets = []
        for kind, relpath in DEFAULT_TARGETS:
            full = os.path.join(ROOT, relpath.replace("/", os.sep))
            count, errors = VALIDATORS[kind](full)
            targets.append((kind, relpath, count, errors))
    failed = False
    for kind, relpath, count, errors in targets:
        print("%s: %s — %d record(s)" % (kind, relpath, count))
        if errors:
            failed = True
            for err in errors[:40]:
                print("  -", err)
    if failed:
        print("FAIL")
        raise SystemExit(1)
    print("PASS — acceleration ledgers are schema-valid and honesty rules hold")


if __name__ == "__main__":
    main()
