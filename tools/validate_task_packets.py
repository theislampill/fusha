#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable twin of qamus/schemas/task-packet.schema.json (qamus.task_packet.v1).

A task packet is a self-contained work order a weaker/cheaper model executes
WITHOUT chat context. Red-first named checks:

- packet_shape: required keys, closed vocabulary, id pattern
- id_collision: packet_id unique across the packet directory, and matching
  its filename stem
- write_scope_conflict: prohibited_files must not overlap permitted_write_files
  (prefix-aware), and expected_outputs must fall inside permitted_write_files
- server_path_leak: no absolute/server filesystem path anywhere (RM-09)
- canary_classes: at least one positive AND one adversarial canary
- method_not_conclusion: guards must carry the method-transfer rule for any
  packet whose model class is below 'certifier'
- non_deployment: status literally NOT_DEPLOYED with a substantive statement
- self_containment: commands, acceptance tests, escalation route and
  definition of done all present and non-trivial

Usage:
    python tools/validate_task_packets.py PACKET.json [...]
    python tools/validate_task_packets.py            # qamus/task-packets/*.json
    python tools/validate_task_packets.py --self-test

Repo style: hand-rolled named validators, no jsonschema dependency,
red-first self-test gated in tools/check_regressions.py (TASKPACKET block).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PACKETS_DIR = ROOT / "qamus" / "task-packets"

SCHEMA_ID = "qamus.task_packet.v1"
PACKET_ID_RE = re.compile(r"^TP-[A-Z0-9]+(-[A-Z0-9]+)*$")
MODEL_CLASSES = frozenset({"certifier", "standard", "deterministic", "cheap"})
# RM-09: no server filesystem paths in any packet string.
SERVER_PATH_RE = re.compile(
    r"(?:/var/www|/srv/|/home/[a-z]|/etc/|[A-Za-z]:\\\\|[A-Za-z]:\\)"
)

REQUIRED_TOP = (
    "schema", "packet_id", "title", "model_class", "scope", "inputs",
    "tools_required", "commands", "candidate_population", "expected_outputs",
    "evidence_policy", "guards", "defeaters", "canaries", "acceptance_tests",
    "non_deployment", "escalation_trigger", "definition_of_done",
)

METHOD_GUARD_MARKER = "method"  # guards must mention method-vs-conclusion


def _walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_strings(v)


def _is_list_of_str(x, min_items=1):
    return (isinstance(x, list) and len(x) >= min_items
            and all(isinstance(i, str) and i.strip() for i in x))


def _covered_by(path, prefixes):
    """True if repo path `path` is covered by any prefix (dir prefixes end in /)."""
    for p in prefixes:
        if p.endswith("/") and path.startswith(p):
            return True
        if path == p:
            return True
    return False


def check_packet_shape(packet, errors):
    for key in REQUIRED_TOP:
        if key not in packet:
            errors.append("packet_shape: missing top-level key %r" % key)
    if packet.get("schema") != SCHEMA_ID:
        errors.append("packet_shape: schema is %r, expected %r"
                      % (packet.get("schema"), SCHEMA_ID))
    pid = packet.get("packet_id")
    if not (isinstance(pid, str) and PACKET_ID_RE.fullmatch(pid)):
        errors.append("packet_shape: packet_id %r does not match TP-… pattern"
                      % pid)
    if packet.get("model_class") not in MODEL_CLASSES:
        errors.append("packet_shape: model_class %r not in %s"
                      % (packet.get("model_class"), sorted(MODEL_CLASSES)))
    scope = packet.get("scope")
    if not isinstance(scope, dict):
        errors.append("packet_shape: scope must be an object")
    else:
        for key in ("summary", "entry_id", "family", "tranche"):
            if key not in scope:
                errors.append("packet_shape: scope missing %r" % key)
    for key, min_items in (("tools_required", 1), ("guards", 1),
                           ("defeaters", 1), ("definition_of_done", 1)):
        if key in packet and not _is_list_of_str(packet.get(key), min_items):
            errors.append("packet_shape: %s must be a non-empty list of "
                          "non-empty strings" % key)
    commands = packet.get("commands")
    if not (isinstance(commands, list) and commands):
        errors.append("self_containment: commands must be a non-empty list")
    else:
        for i, cmd in enumerate(commands):
            if not (isinstance(cmd, dict) and cmd.get("purpose")
                    and cmd.get("run")):
                errors.append("self_containment: commands[%d] needs purpose "
                              "and an exact run line" % i)
    tests = packet.get("acceptance_tests")
    if not (isinstance(tests, list) and tests):
        errors.append("self_containment: acceptance_tests must be non-empty")
    else:
        for i, t in enumerate(tests):
            if not (isinstance(t, dict) and t.get("name") and t.get("run")
                    and t.get("pass_condition")):
                errors.append("self_containment: acceptance_tests[%d] needs "
                              "name, run, pass_condition" % i)
    esc = packet.get("escalation_trigger")
    if not (isinstance(esc, dict) and _is_list_of_str(esc.get("conditions"))
            and isinstance(esc.get("route"), str) and esc.get("route")):
        errors.append("self_containment: escalation_trigger needs conditions[] "
                      "and a route")
    pop = packet.get("candidate_population")
    if not isinstance(pop, dict):
        errors.append("packet_shape: candidate_population must be an object")
    else:
        for key in ("universe_size", "this_packet_size", "selection_rule",
                    "population_source"):
            if key not in pop:
                errors.append("packet_shape: candidate_population missing %r"
                              % key)
    ev = packet.get("evidence_policy")
    if not (isinstance(ev, dict) and ev.get("statement")
            and isinstance(ev.get("verbatim_required"), bool)
            and ev.get("fabrication_rule")):
        errors.append("packet_shape: evidence_policy needs statement, "
                      "verbatim_required (bool), fabrication_rule")


def check_write_scope(packet, errors):
    inputs = packet.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("packet_shape: inputs must be an object")
        return
    for key in ("input_files", "permitted_write_files", "prohibited_files"):
        if not _is_list_of_str(inputs.get(key)):
            errors.append("packet_shape: inputs.%s must be a non-empty list"
                          % key)
            return
    permitted = inputs["permitted_write_files"]
    prohibited = inputs["prohibited_files"]
    for p in prohibited:
        if _covered_by(p, permitted) or any(
                _covered_by(w, [p]) for w in permitted):
            errors.append(
                "write_scope_conflict: %r is both prohibited and covered by "
                "permitted_write_files — the write scope must be unambiguous"
                % p)
    for out in packet.get("expected_outputs") or []:
        if isinstance(out, dict) and isinstance(out.get("path"), str):
            if not _covered_by(out["path"], permitted):
                errors.append(
                    "write_scope_conflict: expected output %r is outside "
                    "permitted_write_files" % out["path"])
        else:
            errors.append("packet_shape: expected_outputs entries need "
                          "path + description")


def check_server_paths(packet, errors):
    for s in _walk_strings(packet):
        if SERVER_PATH_RE.search(s):
            errors.append(
                "server_path_leak: string %r contains a server/absolute "
                "filesystem path (RM-09: packets are public repo artifacts)"
                % (s[:80],))
            return


def check_canaries(packet, errors):
    canaries = packet.get("canaries")
    if not isinstance(canaries, dict):
        errors.append("canary_classes: canaries must be an object")
        return
    for cls in ("positive", "adversarial"):
        rows = canaries.get(cls)
        if not (isinstance(rows, list) and rows):
            errors.append("canary_classes: at least one %s canary is "
                          "required" % cls)
            continue
        for i, c in enumerate(rows):
            if not (isinstance(c, dict) and c.get("id")
                    and c.get("expectation")):
                errors.append("canary_classes: canaries.%s[%d] needs id + "
                              "expectation" % (cls, i))


def check_method_not_conclusion(packet, errors):
    if packet.get("model_class") == "certifier":
        return
    guards = packet.get("guards") or []
    if not any(isinstance(g, str) and METHOD_GUARD_MARKER in g.lower()
               for g in guards):
        errors.append(
            "method_not_conclusion: a packet executable below certifier "
            "class must carry a guard stating that the METHOD transfers and "
            "linguistic conclusions never do")


def check_non_deployment(packet, errors):
    nd = packet.get("non_deployment")
    if not isinstance(nd, dict) or nd.get("status") != "NOT_DEPLOYED":
        errors.append("non_deployment: status must be literally NOT_DEPLOYED")
        return
    if not (isinstance(nd.get("statement"), str)
            and len(nd["statement"]) >= 20):
        errors.append("non_deployment: a substantive candidate-mode statement "
                      "is required")


CHECKS = (
    check_packet_shape,
    check_write_scope,
    check_server_paths,
    check_canaries,
    check_method_not_conclusion,
    check_non_deployment,
)


def validate_packet(packet):
    errors = []
    for check in CHECKS:
        check(packet, errors)
    return errors


def validate_files(paths):
    all_errors = {}
    seen_ids = {}
    for path in paths:
        path = Path(path)
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            all_errors[str(path)] = ["packet_shape: unreadable JSON (%s)" % exc]
            continue
        errors = validate_packet(packet)
        pid = packet.get("packet_id")
        if isinstance(pid, str):
            if pid in seen_ids:
                errors.append("id_collision: packet_id %r already used by %s"
                              % (pid, seen_ids[pid]))
            else:
                seen_ids[pid] = path.name
            if path.stem != pid:
                errors.append("id_collision: filename stem %r must equal "
                              "packet_id %r" % (path.stem, pid))
        if errors:
            all_errors[str(path)] = errors
    return all_errors


def _minimal_green():
    return {
        "schema": SCHEMA_ID,
        "packet_id": "TP-SELFTEST-GREEN",
        "title": "Self-test green packet",
        "model_class": "cheap",
        "scope": {"summary": "Self-test scope, no real population.",
                  "entry_id": None, "family": None, "tranche": None},
        "inputs": {
            "input_files": ["qamus/README.md"],
            "permitted_write_files": ["qamus/reports/selftest/"],
            "prohibited_files": ["qamus/data/"],
        },
        "tools_required": ["python3"],
        "commands": [{"purpose": "list repo root files",
                      "run": "git ls-files | head", "expect": "exit 0"}],
        "candidate_population": {
            "universe_size": None, "this_packet_size": None,
            "selection_rule": "not a population packet (doc check)",
            "population_source": "qamus/README.md"},
        "expected_outputs": [{"path": "qamus/reports/selftest/out.md",
                              "description": "self-test output file"}],
        "evidence_policy": {
            "statement": "No linguistic claims are made; no evidence needed.",
            "verbatim_required": False,
            "fabrication_rule": "Never invent evidence; if a needed file is "
                                "missing, stop and escalate."},
        "guards": ["The METHOD transfers; linguistic conclusions never do."],
        "defeaters": ["None applicable — structural self-test packet."],
        "canaries": {
            "positive": [{"id": "selftest:pos",
                          "expectation": "the command exits 0 and lists files"}],
            "adversarial": [{"id": "selftest:adv",
                             "expectation": "a missing input file must abort "
                                            "the run, not be skipped"}],
        },
        "acceptance_tests": [{"name": "noop", "run": "git ls-files | head",
                              "pass_condition": "exit code 0"}],
        "non_deployment": {
            "status": "NOT_DEPLOYED",
            "statement": "Nothing here mutates a live surface; candidate mode."},
        "escalation_trigger": {
            "conditions": ["any input file missing or unreadable"],
            "route": "stop; write a stop-report to qamus/reports/selftest/ "
                     "and hand back to the certifier lane"},
        "definition_of_done": ["output file exists and acceptance test passed"],
    }


def self_test():
    failures = []

    def check(name, cond):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    green = _minimal_green()
    check("green: minimal packet validates", not validate_packet(green))

    def red(name, mutate, needle):
        packet = _minimal_green()
        mutate(packet)
        errors = validate_packet(packet)
        check("red: " + name,
              any(needle in e for e in errors))

    red("missing canaries flagged",
        lambda p: p.pop("canaries"), "packet_shape")
    red("empty adversarial canaries flagged",
        lambda p: p["canaries"].update(adversarial=[]), "canary_classes")
    red("bad packet id flagged",
        lambda p: p.update(packet_id="tp-lower"), "packet_shape")
    red("prohibited/permitted overlap flagged",
        lambda p: p["inputs"].update(
            prohibited_files=["qamus/reports/selftest/"]),
        "write_scope_conflict")
    red("output outside write scope flagged",
        lambda p: p["expected_outputs"].append(
            {"path": "docs/INDEX.md", "description": "smuggled write"}),
        "write_scope_conflict")
    red("server path leak flagged (RM-09)",
        lambda p: p["guards"].append("read /var/www/html/secret"),
        "server_path_leak")
    red("windows path leak flagged (RM-09)",
        lambda p: p["commands"].append(
            {"purpose": "bad", "run": "type C:\\secrets\\x.txt"}),
        "server_path_leak")
    red("missing method guard flagged",
        lambda p: p.update(guards=["be careful"]), "method_not_conclusion")
    red("non-deployment status flagged",
        lambda p: p["non_deployment"].update(status="DEPLOYED"),
        "non_deployment")
    red("missing escalation route flagged",
        lambda p: p["escalation_trigger"].pop("route"), "self_containment")
    red("empty commands flagged",
        lambda p: p.update(commands=[]), "self_containment")

    # id collision across files (directory-level check)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "TP-SELFTEST-GREEN.json"
        b = Path(td) / "TP-SELFTEST-GREEN-2.json"
        a.write_text(json.dumps(_minimal_green()), encoding="utf-8")
        dup = _minimal_green()
        b.write_text(json.dumps(dup), encoding="utf-8")
        errs = validate_files([a, b])
        check("red: cross-file id collision + stem mismatch flagged",
              any("id_collision" in e for errors in errs.values()
                  for e in errors))

    if failures:
        print("TASK PACKET SELF-TEST FAIL")
        return 1
    print("TASK PACKET SELF-TEST PASS")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    paths = [Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        # Task packets are the uppercase TP-*.json files. Other artifacts in
        # the directory (e.g. the tp-p007-ds-w1-covered-locs.json coverage
        # manifest, schema qamus.coverage_manifest.v1) are packet INPUTS,
        # not packets, and carry their own schemas. The startswith check is
        # case-sensitive on purpose (glob is case-insensitive on Windows).
        paths = sorted(p for p in PACKETS_DIR.glob("*.json")
                       if p.name.startswith("TP-"))
        if not paths:
            print("no packets found in %s" % PACKETS_DIR)
            return 1
    all_errors = validate_files(paths)
    ok = True
    for path in paths:
        errors = all_errors.get(str(path))
        if errors:
            ok = False
            print("FAIL " + str(path))
            for e in errors:
                print("  - " + e)
        else:
            print("ok   " + str(path))
    print("TASK PACKET VALIDATION " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
