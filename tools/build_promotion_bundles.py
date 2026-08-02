#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a complete Sol-reviewable promotion bundle for EVERY discovered
increment — the curriculum evidence pre-assembled so promotion review never
has to rediscover it.

Bundle contents per increment: candidate reference/procedure/learner-ladder
paths, latest machine pack (embedded), fixtures by class (positive /
adversarial / abstention / transfer), occurrence applications (from the
occurrence bridge), rich-hover fields, the EXPECTED skill-registry entry
shape (candidate rows, one per pack rule, gate tier proposal), expected
mirror impact, exact consumer, exact regression command, rollback condition.

Output: curriculum/l1l6/promotion/<inc>.bundle.json (+ bundles meta).
Nothing here edits any Sol-owned skill file; bundles are inputs to Sol's
review, never applied automatically. Deterministic; stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]




def _full_registry_row(inc, pack_file, pack, rule, inc_dir, loop):
    """A COMPLETE candidate registry row carrying every field of the
    current-main rule-registry schema (Sol repair 9) — abbreviated
    expectation shapes are retired. Guards travel as a full payload with a
    content hash."""
    guards = json.loads((inc_dir / "guards.json").read_text(encoding="utf-8"))
    guard_payload = guards["guards"]
    guard_hash = hashlib.sha256(
        json.dumps(guard_payload, ensure_ascii=False, sort_keys=True)
        .encode("utf-8")).hexdigest()
    fixtures_path = "curriculum/l1l6/increments/%s/fixtures.jsonl" % inc
    fx = [json.loads(l) for l in
          (inc_dir / "fixtures.jsonl").read_text(encoding="utf-8").splitlines()
          if l.strip()]
    pos = [f["fixture_id"] for f in fx if f["class"] in ("positive", "transfer")]
    neg = [f["fixture_id"] for f in fx if f["class"] in ("adversarial", "abstention")]
    return {
        "skill_rule_id": "curr-%s-%s" % (inc.replace("inc-", ""), rule["id"]),
        "skill": "sarf" if pack.get("unit_ref", "").startswith(("u-s", "cu-"))
                 and pack.get("capability") in ("letter_ownership",
                                                "template_classification")
                 else "nahw",
        "skill_version": "@curriculum-candidate",
        "status": "candidate",
        "gate": ("@curriculum-candidate:redfirst+loop-measured" if loop
                 else "@curriculum-candidate:redfirst"),
        "fact_family": pack.get("capability"),
        "scope": {"unit_ref": pack.get("unit_ref"), "increment": inc,
                  "statement": rule["text"]},
        "abstention_condition": "; ".join(pack.get("abstention_reasons", []))
                                or "insufficient evidence -> abstain",
        "positive_examples": pos,
        "negative_or_boundary_examples": neg,
        "evidence_addresses": [
            "curriculum/l1l6/increments/%s/%s" % (inc, pack_file),
            "curriculum/l1l6/qualification/ (contributing lessons via canonical-units)"],
        "defeaters": [g["guard"] for g in guard_payload],
        "guards_payload": guard_payload,
        "guards_hash": guard_hash,
        "relationships": {"unit_ref": pack.get("unit_ref"),
                          "harness": "tools/curriculum_unit_consumer.py (NON-AUTHORITATIVE)"},
        "code_references": ["tools/curriculum_unit_consumer.py"],
        "test_references": [fixtures_path],
        "provenance": "curriculum/l1l6/increments/%s/%s" % (inc, pack_file),
    }

def build():
    inc_dir = BASE / "increments"
    bridge = _jsonl(BASE / "reports" / "occurrence-bridge.jsonl")
    loops = json.loads((BASE / "loop" / "loops-manifest.json")
                       .read_text(encoding="utf-8"))["loops"]
    units = _jsonl(BASE / "units" / "instructional-units.jsonl")
    bundles = {}
    for d in sorted(p for p in inc_dir.iterdir() if p.is_dir()):
        inc = d.name
        packs = sorted(d.glob("unit-v*.json"),
                       key=lambda p: int(p.stem.split("-v")[1]))
        pack = json.loads(packs[-1].read_text(encoding="utf-8"))
        prev_pack = packs[-2].name if len(packs) > 1 else None
        fixtures = _jsonl(d / "fixtures.jsonl")
        by_class = {}
        for f in fixtures:
            by_class.setdefault(f["class"], []).append(f["fixture_id"])
        unit_recs = [u for u in units if inc in u.get("machine_increments", [])]
        loop = next((l for l in loops if l["increment"] == inc), None)
        rules = pack.get("rules", [])
        bundles["%s.bundle.json" % inc] = {
            "schema": "curriculum.l1l6_promotion_bundle.v1",
            "increment": inc,
            "capability": pack.get("capability"),
            "status": "candidate_awaiting_sol_review",
            "candidate_reference": "curriculum/l1l6/increments/%s/reference.md" % inc,
            "candidate_procedure": "curriculum/l1l6/increments/%s/procedure.md" % inc,
            "learner_explanation_ladder": {
                u["unit_id"]: u["explanation_ladder"] for u in unit_recs},
            "machine_unit_pack": pack,
            "fixtures_by_class": {k: sorted(v) for k, v in sorted(by_class.items())},
            "occurrence_applications": sorted(
                r["bridge_id"] for r in bridge if r["increment"] == inc),
            "rich_hover_fields": json.loads(
                (d / "hover-fields.json").read_text(encoding="utf-8"))["fields"],
            "candidate_registry_rows": [
                _full_registry_row(inc, packs[-1].name, pack, r, d, loop)
                for r in rules],
            "registry_row_schema_source": "key set of qamus/skills/rule-registry.jsonl rows (current main); validated field-for-field by tools/validate_curriculum_l1l6.py",
            "expected_mirror_impact": [
                "qamus/skills/rule-registry (candidate rows only, Sol-applied)",
                "sarf/ or nahw/ drills (staged explanation adoption, Sol-applied)",
                "no live surface, no certified store",
            ],
            "exact_consumer": "tools/curriculum_unit_consumer.py",
            "exact_regression_command":
                "python tools/curriculum_unit_consumer.py --increment %s" % inc,
            "flywheel_evidence": ("curriculum/l1l6/loop/%s/loop-record.json" % loop["loop"]
                                  if loop else "no recorded loop yet (fixtures-only evidence)"),
            "rollback_condition": (
                "revert to %s (kept committed; the loops manifest pins both packs), "
                "rerun the regression command, expect the recorded pre-repair "
                "defect set" % prev_pack if prev_pack else
                "remove the increment dir; discovery drops it; no other artifact mutates"),
            "no_auto_promotion": True,
        }
    return bundles


def serialize(bundles):
    out = {}
    for name, obj in sorted(bundles.items()):
        out[str(BASE / "promotion" / name)] = (
            json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    out[str(BASE / "promotion" / "bundles.meta.json")] = (json.dumps({
        "schema": "curriculum.l1l6_promotion_bundle.v1.meta",
        "generator": "tools/build_promotion_bundles.py",
        "bundles": sorted(bundles),
        "note": "review inputs for Sol; nothing applied automatically",
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    (BASE / "promotion").mkdir(parents=True, exist_ok=True)
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
            print("FAIL: promotion bundles differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: promotion bundles byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
