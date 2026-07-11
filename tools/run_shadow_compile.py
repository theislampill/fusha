#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_shadow_compile — T9B operational SHADOW runner (Shadow Flywheel Activation Program).

ARCHITECTURAL COMMITMENT: this tool compiles the canonical hover whitelist from pinned,
recorded inputs and compares it against the deployed baseline — and NOTHING else. It
never replaces, feeds, mutates, or shadow-writes the public whitelist; never touches
Qamus request handling; never changes a database; never serves any artifact publicly.
A green shadow run is evidence, not adoption (ADR-003 G8 adoption remains an explicit
owner decision).

Operation
    python tools/run_shadow_compile.py --config <external-config.json>
    python tools/run_shadow_compile.py --self-test

The config file lives OUTSIDE the repository (operator-private). Nothing
production-specific is committed here; every path arrives via the config. Fields:

    {
      "schema": "fusha.shadow_run_config.v1",
      "live_whitelist": "<path to the deployed whitelist jsonl>",   (required)
      "records_dir":    "<private dir for immutable run records>",  (required)
      "repo_root":      "<fusha checkout>",            (optional; default: this repo)
      "expected_source_head": "<sha or null>",         (optional pin; alert on mismatch)
      "leak_local_overlay": "<path or null>",          (optional; explicit-only, never defaulted)
      "sample_size": 25,                               (optional)
      "keep_rowdiff_runs": 8,                          (optional; row-level diff retention)
      "snapshot_every": 10                             (optional; immutable snapshot cadence)
    }

Records (all under records_dir, mode 0o400 after write):
    shadow-ledger.jsonl        append-only one-line summary per run (kept forever)
    run-<UTC>/record.json      full run record, sha256-chained to the previous record
    run-<UTC>/g8-*.json[l]     reporter outputs; row-level diffs pruned to keep_rowdiff_runs
    snapshots/…                every snapshot_every-th record copied, kept forever
    expected-changes.jsonl     operator-appended explanations: rows
                               {"live_whitelist_sha256": "…", "reason": "…", "utc": "…"}
                               a baseline-hash change is EXPLAINED iff a row names the
                               new hash; crosswalk-input changes are explained by the
                               repo commit itself (source_head changes are recorded).
    ALERT-<UTC>.json           written when any alert fires (exit code 1)

Alert classes (owner-mandated):
    reproducibility_failure       in-run double compile produced different packet hashes
    packet_hash_drift             identical inputs vs previous run, different packet hash
    unexpected_modify             public modify count > 0
    unexpected_conflict_blocked   public conflict or blocked count > 0
    leak_false_block              leak false-block count > 0
    no_op_decrease                covered no-op locations decreased (unexplained)
    live_only_increase            live-only gap grew without a recorded content change
    schema_mismatch               consumed/produced schemas differ from the accepted set
    source_head_mismatch          repo head differs from the configured pin
    binding_disappearance         a previously-present full-carrier binding_id vanished
                                  while inputs were identical (any input change is
                                  reported with counts instead)
Known append / live-only queue rows do NOT alert; only unexplained count or identity
changes do.

The compiler-input construction mirrors the harness G1 gate + the T7/G8 parity method:
shared-with-live locations carry the live public payload (projected to the contract
segment shape); modeled-only locations carry the synthetic carrier preview and are
counted as content-pending. Duplication with tools/check_regressions.py G1 is
deliberate: the harness stays self-contained; this tool is the operational path.
"""
import argparse
import glob
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = os.path.dirname(HERE)

ACCEPTED_SCHEMAS_CONSUMED = [
    "qamus.canonical_hover_payload.v2",
    "qamus.canonical_hover_occurrence_binding.v2",
    "qamus.canonical_hover_exception.v2",
    "qamus.rh_live_whitelist_row.legacy-or-v1",
]
ACCEPTED_SCHEMAS_PRODUCED = [
    "qamus.rh_live_whitelist_row.v1",
    "qamus.compile_report.v2",
]

RECORD_SCHEMA = "fusha.shadow_run_record.v1"
CONFIG_SCHEMA = "fusha.shadow_run_config.v1"


def sha256_file(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def utc_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def load_config(path):
    """Fail-closed config loader: exit 2 on any missing/invalid field."""
    try:
        cfg = json.load(io.open(path, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - deliberate fail-closed boundary
        print("CONFIG ERROR: cannot read %s: %s" % (path, exc))
        raise SystemExit(2)
    if cfg.get("schema") != CONFIG_SCHEMA:
        print("CONFIG ERROR: schema must be %s" % CONFIG_SCHEMA)
        raise SystemExit(2)
    for req in ("live_whitelist", "records_dir"):
        if not cfg.get(req):
            print("CONFIG ERROR: %s is required" % req)
            raise SystemExit(2)
    if not os.path.isfile(cfg["live_whitelist"]):
        print("CONFIG ERROR: live_whitelist not found: %s" % cfg["live_whitelist"])
        raise SystemExit(2)
    cfg.setdefault("repo_root", DEFAULT_REPO)
    cfg.setdefault("expected_source_head", None)
    cfg.setdefault("leak_local_overlay", None)
    cfg.setdefault("sample_size", 25)
    cfg.setdefault("keep_rowdiff_runs", 8)
    cfg.setdefault("snapshot_every", 10)
    if cfg["leak_local_overlay"] and not os.path.isfile(cfg["leak_local_overlay"]):
        print("CONFIG ERROR: leak_local_overlay configured but missing: %s"
              % cfg["leak_local_overlay"])
        raise SystemExit(2)
    return cfg


def git_head(repo_root):
    run = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                         capture_output=True, text=True)
    return run.stdout.strip() if run.returncode == 0 else None


def contract_segments(live_segments):
    segs = []
    for seg in live_segments:
        qg = (seg.get("qg_class") or seg.get("class") or "")
        if qg.startswith("qg-"):
            qg = qg[3:]
        segs.append({
            "role": seg.get("role"), "surface": seg.get("surface"),
            "qg_class": (qg.replace("-", "_") or "unknown"),
            "gloss": seg.get("gloss", seg.get("gloss_contribution")),
        })
    return segs


def construct_input_rows(repo_root, live_by_loc, public_content, canonical_public_loc,
                         crosswalk_glob=None):
    """Harness-G1 construction + T7/G8 live-content parity for shared locations."""
    rows, pending, shared = [], 0, 0
    pattern = crosswalk_glob or os.path.join(
        repo_root, "qamus", "indexes", "largelexicon", "qword-crosswalk", "*.jsonl")
    for path in sorted(glob.glob(pattern)):
        for src in read_jsonl(path):
            if src.get("status") != "canonical_crosswalk_accepted":
                continue
            surface = src["visible_surface_norm_strict"]
            dep_blob = json.dumps(src.get("source_dependencies") or [],
                                  ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":"))
            deps = [{"id": src["row_id"],
                     "sha256": hashlib.sha256(dep_blob.encode("utf-8")).hexdigest()}]
            loc = src["canonical_wbw_loc"]
            live = live_by_loc.get(
                canonical_public_loc({"canonical_wbw_loc": loc}) or loc)
            visible_surface = src["visible_surface"]
            live_segs = (live or {}).get("segments") or []
            if live is not None and live_segs:
                visible_surface = live.get("surface") or visible_surface
                pc = public_content(live)
                segs = contract_segments(live_segs)
                payload = {
                    "src": pc.get("src") or "qamus",
                    "kind": pc.get("kind") or "authored",
                    "lang": pc.get("lang") or "en",
                    "token_contribution_gloss": pc.get("public_gloss"),
                    "contextual_phrase_gloss": pc.get("contextual_phrase_gloss"),
                    "morphline": pc.get("morphline"),
                    "segments": segs,
                    "learner_explanation": pc.get("learner_explanation"),
                }
                surface = "".join(s.get("surface") or "" for s in segs) or surface
                shared += 1
            else:
                payload = {
                    "src": "qamus", "kind": "authored", "lang": "en",
                    "token_contribution_gloss": "dry-run carrier preview",
                    "contextual_phrase_gloss": None, "morphline": "STEM",
                    "segments": [{"role": "STEM", "surface": surface,
                                  "qg_class": "unknown", "gloss": "dry-run"}],
                    "learner_explanation": "dry-run carrier preview",
                }
                pending += 1
            rows.append({
                "schema": "qamus.canonical_hover_compiler_input.v1",
                "source_key": "qamus", "source_row_id": src["row_id"],
                "source_artifact_sha256": src["resolution_wbw_lookup_sha256"],
                "source_dependencies": deps,
                "surface_norm": surface, "root": None, "pos": "unknown",
                "pattern": None, "lemma_status": "missing",
                "sarf_certification": "missing", "nahw_certification": "missing",
                "public_payload": payload,
                "canonical_quran_loc": src["canonical_quran_loc"],
                "canonical_wbw_loc": loc,
                "entry_id": src["entry_id"], "card_id": src["card_id"],
                "qword_row_id": src["qword_row_id"],
                "visible_surface": visible_surface,
                "source_dependency_sha256": hashlib.sha256(json.dumps(
                    deps, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")).hexdigest(),
            })
    return rows, shared, pending


def run_pipeline(repo_root, rows, live_whitelist, workdir, sample_size, env_extra=None):
    """Write input rows, build, compile TWICE (in-run reproducibility), G8 report.

    Returns (compile_report, g8_summary, packet_sha_1, packet_sha_2, paths).
    """
    env = dict(os.environ)
    env.pop("FUSHA_LEAK_LOCAL", None)
    env.pop("FUSHA_LEAK_PRODUCTION", None)
    if env_extra:
        env.update(env_extra)
    rows_path = os.path.join(workdir, "compiler_input_rows.jsonl")
    with io.open(rows_path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    empty_exceptions = os.path.join(workdir, "exceptions.empty.jsonl")
    io.open(empty_exceptions, "w").close()

    def cli(args, label):
        run = subprocess.run([sys.executable] + args, capture_output=True,
                             text=True, cwd=repo_root, env=env)
        if run.returncode != 0:
            print("PIPELINE ERROR (%s):" % label)
            print((run.stdout or "")[-2000:])
            print((run.stderr or "")[-2000:])
            raise SystemExit(2)

    bdir = os.path.join(workdir, "build")
    os.makedirs(bdir, exist_ok=True)
    cli([os.path.join(repo_root, "tools", "build_canonical_hover_payload_table.py"),
         "--input", rows_path, "--outdir", bdir], "build")

    packet_shas, cdirs = [], []
    for attempt in ("compile-1", "compile-2"):
        cdir = os.path.join(workdir, attempt)
        os.makedirs(cdir, exist_ok=True)
        cli([os.path.join(repo_root, "tools",
                          "compile_canonical_hover_whitelist_packet.py"),
             "--payloads", os.path.join(bdir, "canonical_payloads.jsonl"),
             "--bindings", os.path.join(bdir, "occurrence_bindings.jsonl"),
             "--exceptions", empty_exceptions,
             "--baseline", live_whitelist, "--outdir", cdir], attempt)
        report = json.load(io.open(os.path.join(cdir, "compile_report.json"),
                                   encoding="utf-8"))
        packet_shas.append(report["packet_sha256"])
        cdirs.append(cdir)

    cdir = cdirs[0]
    for name in ("occurrence_bindings.jsonl", "repair_candidates.jsonl"):
        src_p = os.path.join(bdir, name)
        dst_p = os.path.join(cdir, name)
        if os.path.exists(src_p) and not os.path.exists(dst_p):
            shutil.copyfile(src_p, dst_p)
    cli([os.path.join(repo_root, "tools", "report_g8_adoption_packet.py"),
         "--compile-dir", cdir, "--baseline", live_whitelist,
         "--outdir", workdir, "--sample-size", str(sample_size)], "g8-report")

    compile_report = json.load(io.open(os.path.join(cdir, "compile_report.json"),
                                       encoding="utf-8"))
    g8_summary = json.load(io.open(os.path.join(workdir, "g8-summary.json"),
                                   encoding="utf-8"))
    build_conflicts = os.path.join(bdir, "build_conflicts.jsonl")
    n_build_conflicts = len(read_jsonl(build_conflicts)) \
        if os.path.exists(build_conflicts) else 0
    return (compile_report, g8_summary, packet_shas[0], packet_shas[1],
            {"workdir": workdir, "compile_dir": cdir, "build_dir": bdir,
             "build_conflicts": n_build_conflicts})


def binding_id_set(build_dir):
    ids = set()
    path = os.path.join(build_dir, "occurrence_bindings.jsonl")
    for row in read_jsonl(path):
        ids.add(row.get("binding_id") or row.get("row_id")
                or json.dumps([row.get("canonical_wbw_loc"), row.get("qword_row_id")],
                              sort_keys=True))
    return ids


def load_previous(records_dir):
    ledger = os.path.join(records_dir, "shadow-ledger.jsonl")
    if not os.path.exists(ledger):
        return None
    rows = read_jsonl(ledger)
    return rows[-1] if rows else None


def load_expected_changes(records_dir):
    path = os.path.join(records_dir, "expected-changes.jsonl")
    if not os.path.exists(path):
        return []
    return read_jsonl(path)


def evaluate_alerts(record, prev, expected_changes):
    """Owner-mandated alert classes. Returns (alerts, explained)."""
    alerts, explained = [], []
    counts = record["counts"]

    if record["packet_sha256_run1"] != record["packet_sha256_run2"]:
        alerts.append({"class": "reproducibility_failure",
                       "detail": "in-run double compile disagreed"})
    if counts["modify"] > 0:
        alerts.append({"class": "unexpected_modify", "count": counts["modify"]})
    if counts["conflict"] > 0 or counts["blocked"] > 0:
        alerts.append({"class": "unexpected_conflict_blocked",
                       "conflict": counts["conflict"], "blocked": counts["blocked"]})
    if counts["leak_false_block"] > 0:
        alerts.append({"class": "leak_false_block",
                       "count": counts["leak_false_block"]})
    if record["schemas_consumed"] != ACCEPTED_SCHEMAS_CONSUMED \
            or record["schemas_produced"] != ACCEPTED_SCHEMAS_PRODUCED:
        alerts.append({"class": "schema_mismatch",
                       "consumed": record["schemas_consumed"],
                       "produced": record["schemas_produced"]})
    if record["expected_source_head"] \
            and record["fusha_commit"] != record["expected_source_head"]:
        alerts.append({"class": "source_head_mismatch",
                       "head": record["fusha_commit"],
                       "expected": record["expected_source_head"]})

    if prev is None:
        return alerts, explained

    inputs_identical = (
        prev.get("live_whitelist_sha256") == record["live_whitelist_sha256"]
        and prev.get("input_rows_sha256") == record["input_rows_sha256"]
        and prev.get("fusha_commit") == record["fusha_commit"])
    baseline_changed = prev.get("live_whitelist_sha256") != record["live_whitelist_sha256"]
    baseline_explained = baseline_changed and any(
        row.get("live_whitelist_sha256") == record["live_whitelist_sha256"]
        for row in expected_changes)
    inputs_changed_recorded = (not inputs_identical) and (
        baseline_explained or prev.get("input_rows_sha256") != record["input_rows_sha256"]
        or prev.get("fusha_commit") != record["fusha_commit"])

    if inputs_identical and prev.get("packet_sha256_run1") \
            and prev["packet_sha256_run1"] != record["packet_sha256_run1"]:
        alerts.append({"class": "packet_hash_drift",
                       "previous": prev["packet_sha256_run1"],
                       "current": record["packet_sha256_run1"]})
    prev_counts = prev.get("counts") or {}
    if counts["no_op"] < prev_counts.get("no_op", 0):
        item = {"class": "no_op_decrease", "previous": prev_counts.get("no_op"),
                "current": counts["no_op"]}
        if inputs_changed_recorded:
            explained.append({**item, "explained_by": "recorded input change"})
        else:
            alerts.append(item)
    if counts["remove_or_unrepresented"] > prev_counts.get(
            "remove_or_unrepresented", counts["remove_or_unrepresented"]):
        item = {"class": "live_only_increase",
                "previous": prev_counts.get("remove_or_unrepresented"),
                "current": counts["remove_or_unrepresented"]}
        if inputs_changed_recorded:
            explained.append({**item, "explained_by": "recorded content change"})
        else:
            alerts.append(item)
    if inputs_identical and prev.get("binding_count") is not None \
            and record["binding_count"] < prev["binding_count"]:
        alerts.append({"class": "binding_disappearance",
                       "previous": prev["binding_count"],
                       "current": record["binding_count"]})
    return alerts, explained


def prune_rowdiffs(records_dir, keep):
    run_dirs = sorted(d for d in glob.glob(os.path.join(records_dir, "run-*"))
                      if os.path.isdir(d))
    for old in run_dirs[:-keep] if keep > 0 else []:
        for heavy in ("g8-rowdiff.jsonl", "compiler_input_rows.jsonl"):
            path = os.path.join(old, heavy)
            if os.path.exists(path):
                os.chmod(path, 0o600)
                os.remove(path)
        for sub in ("build", "compile-1", "compile-2"):
            path = os.path.join(old, sub)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)


def shadow_run(cfg):
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.perf_counter()
    repo_root = cfg["repo_root"]
    sys.path.insert(0, repo_root)
    from tools import compile_canonical_hover_whitelist_packet as compile_mod

    records_dir = cfg["records_dir"]
    os.makedirs(records_dir, exist_ok=True)
    stamp = utc_stamp()
    run_dir = os.path.join(records_dir, "run-%s" % stamp)
    os.makedirs(run_dir, exist_ok=True)

    live_rows = read_jsonl(cfg["live_whitelist"])
    live_sha = sha256_file(cfg["live_whitelist"])
    live_by_loc = {}
    for row in live_rows:
        loc = compile_mod.canonical_public_loc(row)
        if loc:
            live_by_loc.setdefault(loc, row)

    rows, shared, pending = construct_input_rows(
        repo_root, live_by_loc, compile_mod.public_content,
        compile_mod.canonical_public_loc, cfg.get("crosswalk_glob"))
    if not rows:
        print("PIPELINE ERROR: zero accepted crosswalk rows constructed")
        raise SystemExit(2)

    env_extra = None
    if cfg["leak_local_overlay"]:
        env_extra = {"FUSHA_LEAK_PRODUCTION": "1",
                     "FUSHA_LEAK_LOCAL": cfg["leak_local_overlay"]}
    (compile_report, g8_summary, sha1, sha2, paths) = run_pipeline(
        repo_root, rows, cfg["live_whitelist"], run_dir, cfg["sample_size"],
        env_extra)

    cls = g8_summary["classifications"]
    input_rows_sha = sha256_file(os.path.join(run_dir, "compiler_input_rows.jsonl"))
    prev = load_previous(records_dir)
    record = {
        "schema": RECORD_SCHEMA,
        "started_utc": started,
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "fusha_commit": git_head(repo_root),
        "expected_source_head": cfg["expected_source_head"],
        "compiler_version": compile_report.get("compiler_version"),
        "schemas_consumed": compile_report.get("schemas_consumed"),
        "schemas_produced": compile_report.get("schemas_produced"),
        "live_whitelist_sha256": live_sha,
        "live_rows": len(live_rows),
        "input_rows_sha256": input_rows_sha,
        "input_bindings": len(rows),
        "input_identities": compile_report.get("input_artifacts"),
        "binding_count": compile_report.get("input_bindings"),
        "packet_sha256_run1": sha1,
        "packet_sha256_run2": sha2,
        "counts": {
            "no_op": cls["no_op"]["count"],
            "append": cls["append"]["count"],
            "remove_or_unrepresented": cls["remove_or_unrepresented"]["count"],
            "modify": cls["modify"]["count"],
            "conflict": cls["conflict"]["count"],
            "blocked": cls["blocked"]["count"],
            "leak_false_block": g8_summary["leak_false_block"]["count"],
            "build_carrier_conflicts": paths["build_conflicts"],
        },
        "content_method": {"shared_live_parity": shared,
                           "pending_placeholder": pending},
        "prev_record_sha256": (prev or {}).get("record_sha256"),
    }
    alerts, explained = evaluate_alerts(record, prev, load_expected_changes(records_dir))
    record["alerts"] = alerts
    record["explained"] = explained

    record_path = os.path.join(run_dir, "record.json")
    blob = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1)
    with io.open(record_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(blob)
    record_sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    os.chmod(record_path, 0o400)

    ledger_row = {k: record[k] for k in (
        "schema", "started_utc", "ended_utc", "fusha_commit", "compiler_version",
        "live_whitelist_sha256", "input_rows_sha256", "binding_count",
        "packet_sha256_run1", "counts", "prev_record_sha256")}
    ledger_row["record_sha256"] = record_sha
    ledger_row["run_dir"] = os.path.basename(run_dir)
    ledger_row["alert_count"] = len(alerts)
    with io.open(os.path.join(records_dir, "shadow-ledger.jsonl"), "a",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(ledger_row, ensure_ascii=False, sort_keys=True) + "\n")

    ledger_rows = read_jsonl(os.path.join(records_dir, "shadow-ledger.jsonl"))
    if cfg["snapshot_every"] > 0 and len(ledger_rows) % cfg["snapshot_every"] == 0:
        snap_dir = os.path.join(records_dir, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        shutil.copyfile(record_path, os.path.join(
            snap_dir, "record-%s.json" % stamp))
    prune_rowdiffs(records_dir, cfg["keep_rowdiff_runs"])

    if alerts:
        alert_path = os.path.join(records_dir, "ALERT-%s.json" % stamp)
        with io.open(alert_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"run": os.path.basename(run_dir), "alerts": alerts,
                       "record_sha256": record_sha}, fh,
                      ensure_ascii=False, sort_keys=True, indent=1)
        print("SHADOW RUN ALERT(S): %d — %s" % (
            len(alerts), ", ".join(a["class"] for a in alerts)))
        print("record: %s (sha %s)" % (record_path, record_sha[:16]))
        return 1
    print("SHADOW RUN OK — no_op=%d append=%d live_only=%d modify=%d conflict=%d "
          "blocked=%d leak_fb=%d build_conflicts=%d packet=%s"
          % (record["counts"]["no_op"], record["counts"]["append"],
             record["counts"]["remove_or_unrepresented"], record["counts"]["modify"],
             record["counts"]["conflict"], record["counts"]["blocked"],
             record["counts"]["leak_false_block"],
             record["counts"]["build_carrier_conflicts"], sha1[:16]))
    print("record: %s (sha %s)" % (record_path, record_sha[:16]))
    return 0


# --------------------------------------------------------------------------- #
# self-test: synthetic fixtures only; no production paths, no repo dataset.
# --------------------------------------------------------------------------- #

def _self_test():
    failures = []

    def check(name, cond):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    base_record = {
        "packet_sha256_run1": "aa", "packet_sha256_run2": "aa",
        "schemas_consumed": list(ACCEPTED_SCHEMAS_CONSUMED),
        "schemas_produced": list(ACCEPTED_SCHEMAS_PRODUCED),
        "expected_source_head": None, "fusha_commit": "headsha",
        "live_whitelist_sha256": "live1", "input_rows_sha256": "in1",
        "binding_count": 100,
        "counts": {"no_op": 50, "append": 10, "remove_or_unrepresented": 5,
                   "modify": 0, "conflict": 0, "blocked": 0,
                   "leak_false_block": 0, "build_carrier_conflicts": 2},
    }
    prev = {"live_whitelist_sha256": "live1", "input_rows_sha256": "in1",
            "fusha_commit": "headsha", "packet_sha256_run1": "aa",
            "binding_count": 100, "record_sha256": "r0",
            "counts": dict(base_record["counts"])}

    alerts, _ = evaluate_alerts(dict(base_record), dict(prev), [])
    check("clean steady-state run raises no alert", alerts == [])

    rec = json.loads(json.dumps(base_record)); rec["packet_sha256_run2"] = "bb"
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("in-run double-compile disagreement -> reproducibility_failure",
          any(a["class"] == "reproducibility_failure" for a in alerts))

    rec = json.loads(json.dumps(base_record))
    rec["packet_sha256_run1"] = rec["packet_sha256_run2"] = "bb"
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("identical inputs + different packet hash -> packet_hash_drift",
          any(a["class"] == "packet_hash_drift" for a in alerts))

    rec = json.loads(json.dumps(base_record)); rec["counts"]["modify"] = 3
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("public modify>0 -> unexpected_modify",
          any(a["class"] == "unexpected_modify" for a in alerts))

    rec = json.loads(json.dumps(base_record)); rec["counts"]["blocked"] = 1
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("public blocked>0 -> unexpected_conflict_blocked",
          any(a["class"] == "unexpected_conflict_blocked" for a in alerts))

    rec = json.loads(json.dumps(base_record)); rec["counts"]["leak_false_block"] = 1
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("leak false-block -> leak_false_block",
          any(a["class"] == "leak_false_block" for a in alerts))

    rec = json.loads(json.dumps(base_record))
    rec["schemas_produced"] = ["something.else.v9"]
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("schema set change -> schema_mismatch",
          any(a["class"] == "schema_mismatch" for a in alerts))

    rec = json.loads(json.dumps(base_record))
    rec["expected_source_head"] = "pinned"; rec["fusha_commit"] = "other"
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("pinned head mismatch -> source_head_mismatch",
          any(a["class"] == "source_head_mismatch" for a in alerts))

    rec = json.loads(json.dumps(base_record)); rec["counts"]["no_op"] = 40
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("no_op decrease with identical inputs -> alert",
          any(a["class"] == "no_op_decrease" for a in alerts))

    rec = json.loads(json.dumps(base_record))
    rec["counts"]["remove_or_unrepresented"] = 9
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("live-only increase, identical inputs, no expected-change row -> alert",
          any(a["class"] == "live_only_increase" for a in alerts))

    rec = json.loads(json.dumps(base_record))
    rec["counts"]["remove_or_unrepresented"] = 9
    rec["live_whitelist_sha256"] = "live2"
    rec["packet_sha256_run1"] = rec["packet_sha256_run2"] = "cc"
    alerts, explained = evaluate_alerts(
        rec, dict(prev), [{"live_whitelist_sha256": "live2",
                           "reason": "accepted content deploy"}])
    check("live-only increase EXPLAINED by expected-change row -> no alert, recorded",
          not any(a["class"] == "live_only_increase" for a in alerts)
          and any(e["class"] == "live_only_increase" for e in explained))
    check("baseline change does not fake packet_hash_drift",
          not any(a["class"] == "packet_hash_drift" for a in alerts))

    rec = json.loads(json.dumps(base_record)); rec["binding_count"] = 99
    alerts, _ = evaluate_alerts(rec, dict(prev), [])
    check("binding disappearance under identical inputs -> alert",
          any(a["class"] == "binding_disappearance" for a in alerts))

    alerts, _ = evaluate_alerts(dict(base_record), None, [])
    check("first run (no previous record) evaluates baseline-free", alerts == [])

    # --- end-to-end micro-pipeline over synthetic fixtures ------------------ #
    tmp = tempfile.mkdtemp(prefix="fusha-shadow-selftest-")
    try:
        cw_dir = os.path.join(tmp, "crosswalk")
        os.makedirs(cw_dir)
        cw_row = {
            "status": "canonical_crosswalk_accepted",
            "row_id": "llx-crosswalk-selftest-0001",
            "visible_surface": "كِتَاب", "visible_surface_norm_strict": "كِتَاب",
            "resolution_wbw_lookup_sha256": hashlib.sha256(b"st").hexdigest(),
            "source_dependencies": [],
            "canonical_quran_loc": "1:1:1", "canonical_wbw_loc": "1:1:1",
            "entry_id": "e-selftest", "card_id": "c-selftest:u1:e1",
            "qword_row_id": "llx-qword-selftest-0001",
        }
        with io.open(os.path.join(cw_dir, "part-000.jsonl"), "w",
                     encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(cw_row, ensure_ascii=False) + "\n")
        live_path = os.path.join(tmp, "live.jsonl")
        live_row = {
            "loc": "1:1:1", "surface": "كِتَاب",
            "public_gloss": "book", "contextual_phrase_gloss": "book",
            "morphline": "STEM", "learner_explanation": "a book",
            "segments": [{"role": "STEM", "surface": "كِتَاب",
                          "class": "qg-noun", "gloss_contribution": "book"}],
            "src": "qamus", "kind": "authored", "lang": "en",
        }
        with io.open(live_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(live_row, ensure_ascii=False) + "\n")

        sys.path.insert(0, DEFAULT_REPO)
        from tools import compile_canonical_hover_whitelist_packet as cmod
        live_by_loc = {cmod.canonical_public_loc(live_row): live_row}
        rows, shared, pending = construct_input_rows(
            DEFAULT_REPO, live_by_loc, cmod.public_content,
            cmod.canonical_public_loc,
            crosswalk_glob=os.path.join(cw_dir, "*.jsonl"))
        check("synthetic construction: 1 row, live-parity payload",
              len(rows) == 1 and shared == 1 and pending == 0)
        workdir = os.path.join(tmp, "run")
        os.makedirs(workdir)
        report, summary, sha_a, sha_b, paths = run_pipeline(
            DEFAULT_REPO, rows, live_path, workdir, 5)
        check("synthetic pipeline: double compile reproducible", sha_a == sha_b)
        check("synthetic pipeline: shared loc classifies no_op",
              summary["classifications"]["no_op"]["count"] == 1
              and summary["classifications"]["modify"]["count"] == 0)
        check("synthetic pipeline: no build carrier conflicts",
              paths["build_conflicts"] == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("\n%d SELF-TEST FAILURE(S)" % len(failures))
        return 1
    print("\nSHADOW RUNNER SELF-TEST PASS")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="external shadow-run config JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.config:
        parser.error("--config is required unless --self-test is used")
    raise SystemExit(shadow_run(load_config(args.config)))


if __name__ == "__main__":
    main()
