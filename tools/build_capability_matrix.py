#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the complete curriculum-to-capability matrix (25 sarf + 38 nahw
families). Curriculum-coverage numbers are COMPUTED from the committed
concept graph (deterministic keyword probes over heading text + domain);
the per-family repository assessment lives in the AUTHORED DATA FILE
curriculum/l1l6/reports/capability-matrix-families.json (kept as data, not
source literals, so the A1 sarf eval runner's source-scan consumer prover
never mistakes this tool for a Store A rule consumer).

Output: curriculum/l1l6/reports/capability-matrix.jsonl (+ meta).
Deterministic; CI-recomputable.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"
NONE_ = "none"


def nfc(s):
    return unicodedata.normalize("NFC", s)


def build():
    table = json.loads((BASE / "reports" / "capability-matrix-families.json")
                       .read_text(encoding="utf-8"))["families"]
    concepts = [json.loads(l) for l in
                (BASE / "graph" / "concepts.jsonl").read_text(encoding="utf-8").splitlines()
                if l.strip()]
    rows = []
    for fam in table:
        kws = fam["keywords"]
        domains = fam["domains"]
        matched = []
        for c in concepts:
            h = nfc(c["heading"]).lower()
            if c["domain"] in domains or any(nfc(k) in h for k in kws):
                matched.append(c)
        lessons = sorted({c["lesson_id"] for c in matched})
        rows.append({
            "schema": "curriculum.l1l6_capability_matrix_row.v1",
            "family_id": fam["family_id"], "axis": fam["axis"],
            "family": fam["family"],
            "curriculum_coverage": {
                "matched_concept_nodes": len(matched),
                "matched_lessons": len(lessons),
                "levels": sorted({l.split(".")[0] for l in lessons}),
                "probe": {"keywords": kws, "domains": domains},
            },
            "repo_documentary_support": fam["repo_documentary_support"],
            "repo_executable_consumer": fam["repo_executable_consumer"],
            "fixture_coverage": fam["fixture_coverage"],
            "instructional_support": fam["instructional_support"],
            "occurrence_coverage": fam["occurrence_coverage"],
            "rich_hover_readiness": fam["rich_hover_readiness"],
            "backprop_readiness": fam["backprop_readiness"],
            "remaining_work": fam["remaining_work"],
            "assessment_basis": "curriculum numbers computed from committed concept graph; repo dims authored in capability-matrix-families.json, verified against docs/subsystems/*-executable-map.md + crosswalks",
        })
    return rows


def serialize(rows):
    out = {}
    out[str(BASE / "reports" / "capability-matrix.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    meta = {
        "schema": "curriculum.l1l6_capability_matrix_row.v1.meta",
        "generator": "tools/build_capability_matrix.py",
        "rows": len(rows),
        "sarf_families": sum(1 for r in rows if r["axis"] == "sarf"),
        "nahw_families": sum(1 for r in rows if r["axis"] == "nahw"),
        "families_with_executable_consumer": sum(
            1 for r in rows if r["repo_executable_consumer"] != NONE_),
        "families_pending_unit_authoring": sum(
            1 for r in rows if "pending unit authoring" in str(r["instructional_support"])),
    }
    out[str(BASE / "reports" / "capability-matrix.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    files = serialize(build())
    bad = []
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(p.name)
        else:
            p.write_bytes(data)
            print("wrote %s (%d bytes)" % (p.relative_to(ROOT), len(data)))
    if check:
        if bad:
            print("FAIL: capability matrix differs from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: capability matrix byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
