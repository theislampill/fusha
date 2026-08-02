#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic CANDIDATE-mode flywheel runner.

Executes the full loop for ANY discovered increment (no hard-coding to a
family list — increments and packs are directory-discovered, dispatch is by
registered capability):

  select qualified unit -> load prerequisites and guards -> invoke the real
  candidate consumer on the positive/adversarial/transfer population ->
  preserve rivals and abstentions -> record defects by capability -> emit a
  bounded backprop proposal -> apply an EXPLICITLY SUPPLIED candidate repair
  pack -> rerun the full and transfer populations -> measure improvement and
  regressions -> emit downstream occurrence/P-V-N work pointers.

Improvement-class discipline: the runner verifies every claimed class
against actual consumer evidence —
  linguistic_consumer_improvement : >=1 decision changed run1->run2 into a
                                    match (transfer rows count double-proof)
  fixture_only_improvement        : fixture set changed, decisions did not
  instructional_improvement       : explanation/hover artifacts differ
                                    between packs (recorded, not claimed as
                                    consumer gain)
  corpus_coverage_improvement     : new exact occurrence links unlocked
                                    (requires a links evidence file)
  site_payload_improvement        : never claimable here (owner-gated plane)
No flywheel gain is reported without a downstream consumer invocation.

The runner mutates nothing certified and nothing live; outputs are loop
records under curriculum/l1l6/loop/<loop-name>/.

Usage:
  python tools/curriculum_flywheel_runner.py --loop <name> --increment <inc>
      --baseline <unit-vA.json> --repaired <unit-vB.json> [--write]
  python tools/curriculum_flywheel_runner.py --manifest [--write]  # all loops
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"
LOOP = BASE / "loop"

sys.path.insert(0, str(ROOT / "tools"))
import curriculum_unit_consumer as consumer  # noqa: E402


def run_loop(name, inc, baseline, repaired):
    unit_rows = [json.loads(l) for l in
                 (BASE / "units" / "instructional-units.jsonl")
                 .read_text(encoding="utf-8").splitlines() if l.strip()]
    unit_rec = next((u for u in unit_rows if inc in u.get("machine_increments", [])), None)
    guards = json.loads((BASE / "increments" / inc / "guards.json")
                        .read_text(encoding="utf-8"))

    run1 = consumer.run(inc, baseline)
    run2 = consumer.run(inc, repaired)
    by_id1 = {r["fixture_id"]: r for r in run1["results"]}
    by_id2 = {r["fixture_id"]: r for r in run2["results"]}

    defects = [{"fixture_id": fid, "class": r["class"],
                "expected": r["expected"], "actual": r["actual"]}
               for fid, r in sorted(by_id1.items()) if not r["match"]]
    improvements = sorted(fid for fid in by_id1
                          if not by_id1[fid]["match"] and by_id2[fid]["match"])
    regressions = sorted(fid for fid in by_id1
                         if by_id1[fid]["match"] and not by_id2[fid]["match"])
    transfer_improved = sorted(fid for fid in improvements
                               if by_id1[fid]["class"] == "transfer")
    rivals_preserved = sorted(
        fid for fid, r in by_id2.items()
        if r["actual"].get("reason") in ("preserve_alternatives",) and r["match"])
    abstentions_preserved = sorted(
        fid for fid, r in by_id2.items()
        if r["actual"].get("decision") == "abstain" and r["match"])

    classes = []
    if improvements and not regressions:
        classes.append("linguistic_consumer_improvement")
    if not improvements and run1["fixtures"] != run2["fixtures"]:
        classes.append("fixture_only_improvement")
    b = json.loads((BASE / "increments" / inc / baseline).read_text(encoding="utf-8"))
    r_ = json.loads((BASE / "increments" / inc / repaired).read_text(encoding="utf-8"))
    if b.get("rules") != r_.get("rules") or b.get("functions") != r_.get("functions") \
            or b.get("licensing_table") != r_.get("licensing_table"):
        classes.append("instructional_improvement")

    return {
        "schema": "curriculum.l1l6_flywheel_loop.v1",
        "loop": name,
        "increment": inc,
        "capability": r_.get("capability"),
        "unit_ref": unit_rec["unit_id"] if unit_rec else None,
        "guards_loaded": [g["id"] for g in guards["guards"]],
        "baseline_pack": baseline,
        "repaired_pack": repaired,
        "run1": run1,
        "run2": run2,
        "defects_recorded": defects,
        "improvements": improvements,
        "transfer_improvements": transfer_improved,
        "regressions": regressions,
        "rivals_preserved": rivals_preserved,
        "abstentions_preserved": abstentions_preserved,
        "improvement_classes_verified": sorted(classes),
        "site_payload_improvement": "never_claimable_here_owner_gated",
        "backprop_proposal": {
            "target": "curriculum/l1l6/promotion/ bundle for %s" % inc,
            "content": "repair %s -> %s with the recorded defect set as adversarial evidence"
                       % (baseline, repaired),
            "no_auto_promotion": True,
        },
        "downstream_work": {
            "occurrence_grounding": "queue q-pvn-grounding rows for lessons mapped to %s" % inc,
            "hover_pedagogy": "queue q-hover-pedagogy rows for linked entries",
        },
        "status": "candidate",
    }


def serialize_loop(rec):
    d = LOOP / rec["loop"]
    return {str(d / "loop-record.json"):
            (json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True)
             + "\n").encode("utf-8")}


def load_manifest():
    return json.loads((LOOP / "loops-manifest.json").read_text(encoding="utf-8"))


def main(argv):
    write = "--write" in argv
    if "--manifest" in argv:
        manifest = load_manifest()
        rc = 0
        for row in manifest["loops"]:
            rec = run_loop(row["loop"], row["increment"],
                           row["baseline_pack"], row["repaired_pack"])
            ok = (len(rec["run1"]["results"]) and
                  rec["run1"]["mismatches"] == row["expected_run1_mismatches"] and
                  rec["run2"]["mismatches"] == 0 and not rec["regressions"])
            files = serialize_loop(rec)
            for path, data in files.items():
                p = Path(path)
                if write:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(data)
                elif not p.exists() or p.read_bytes() != data:
                    print("STALE %s" % p.relative_to(ROOT))
                    rc = 1
            print("%-18s run1=%d/%d defects  run2=%d  transfer+%d  classes=%s %s"
                  % (row["loop"], rec["run1"]["mismatches"],
                     rec["run1"]["fixtures"], rec["run2"]["mismatches"],
                     len(rec["transfer_improvements"]),
                     ",".join(rec["improvement_classes_verified"]), "OK" if ok else "FAIL"))
            rc = rc if ok else 1
        return rc
    # single loop
    def arg(name):
        return argv[argv.index(name) + 1]
    rec = run_loop(arg("--loop"), arg("--increment"), arg("--baseline"), arg("--repaired"))
    files = serialize_loop(rec)
    for path, data in files.items():
        if write:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(data)
            print("wrote %s" % Path(path).relative_to(ROOT))
        else:
            sys.stdout.write(data.decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
