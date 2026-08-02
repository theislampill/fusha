#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic occurrence-link and appearance-enumeration interface.

For ANY instructional unit, enumerate from COMMITTED AUTHORITY ONLY (the
p007 pilot store, the website-payload exemplars, the precise-links file and
the entry store) — never from root or surface similarity, never a quran:*
wildcard:

  exact candidate canonical occurrences · exact P/V/N entries · every
  authoritative page appearance (with its page-relation kind) · required
  sarf/nahw facts · unresolved dependencies · expected colour + hover
  components · promotion evidence · abstention conditions.

Outputs (curriculum/l1l6/reports/):
  occurrence-bridge.jsonl (+meta)  one row per (unit, occurrence|entry) with
                                   the full enumeration
  pvn-readiness.json               the 226-lesson rollup with honest
                                   denominators and per-class reasons/next
                                   actions

Deterministic; CI-recomputable; stdlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"
P007 = ROOT / "qamus" / "examples" / "p007-li-pilot"


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    units = _jsonl(BASE / "units" / "instructional-units.jsonl")
    plinks = _jsonl(BASE / "links" / "pvn-precise-links.jsonl")
    ledger = _jsonl(BASE / "reports" / "absorption-ledger.jsonl")
    facts = _jsonl(P007 / "typed-facts.jsonl")
    projections = _jsonl(P007 / "projections.jsonl")
    proj_by_occ = {p["projection"]["occurrence_id"]: p for p in projections}
    facts_by_occ = {}
    for fct in facts:
        for s in fct.get("surface_spans", []):
            loc = s.get("quran_loc")
            if loc:
                facts_by_occ.setdefault(loc, []).append(fct)

    hover_keys = {}
    for d in sorted((BASE / "increments").iterdir()):
        hp = d / "hover-fields.json"
        if hp.exists():
            hover_keys[d.name] = [f["key"] for f in
                                  json.loads(hp.read_text(encoding="utf-8"))["fields"]]
    abst = {}
    for d in sorted((BASE / "increments").iterdir()):
        packs = sorted(d.glob("unit-v*.json"),
                       key=lambda p: int(p.stem.split("-v")[1]))
        if packs:
            abst[d.name] = json.loads(packs[-1].read_text(encoding="utf-8")
                                      ).get("abstention_reasons", [])

    rows = []
    for link in plinks:
        unit_id = link["unit_ref"]
        inc = link["increment"]
        occ = link.get("occurrence_id")
        row = {
            "schema": "curriculum.l1l6_occurrence_bridge_row.v1",
            "bridge_id": "br-" + link["link_id"],
            "unit_ref": unit_id,
            "increment": inc,
            "entry_id": link["entry_id"],
            "source_key": link["source_key"],
            "entry_kind": link["source_key"][0],  # p/v/n from the store key
            "occurrence_id": occ,
            "status": "candidate",
            "expected_colour_components": (
                ["seg per owner class (compiled from facts)"] if inc == "inc-ownership"
                else ["function-class colouring (candidate)"]),
            "expected_hover_components": hover_keys.get(inc, []),
            "promotion_evidence": link["promotion_evidence"],
            "abstention_conditions": sorted(set(
                abst.get(inc, []) + [link["ambiguity_abstention"]])),
            "linkage_basis": link["linkage_basis"],
        }
        if occ and occ in proj_by_occ:
            pr = proj_by_occ[occ]
            row["appearances"] = {
                "rows": pr["appearances"],
                "count": len(pr["appearances"]),
                "page_relation_note": "appearance ids are page-scoped renderings; the p007 entry page is entry-identity, all others are context-only appearances (per the pilot reverse index scope)",
                "single_hash_parity": {a["projection_hash"] for a in
                                       pr["appearances"]} == {pr["projection_hash"]},
            }
            row["required_sarf_facts"] = sorted(
                f["fact_id"] for f in facts_by_occ.get(occ, [])
                if f["fact_type"] == "clitic_host_segmentation")
            row["required_nahw_facts"] = sorted(
                f["fact_id"] for f in facts_by_occ.get(occ, [])
                if f["fact_type"] in ("contextual_function", "governor_relation",
                                      "case_mood_governor"))
            row["unresolved_dependencies"] = [
                "host_internal_letter_ownership (host-root certification pending)"]
        elif occ:
            row["appearances"] = {"rows": [], "count": 0,
                                  "page_relation_note": "no committed projection row for this occurrence; appearances enumerable only after its projection artifact exists"}
            row["required_sarf_facts"] = []
            row["required_nahw_facts"] = []
            row["unresolved_dependencies"] = [
                "per-occurrence discriminator evidence not yet recorded"]
        else:
            row["unresolved_dependencies"] = [
                "entry-level link: occurrence selection requires per-occurrence evidence rows"]
        rows.append(row)
    rows.sort(key=lambda r: r["bridge_id"])

    # ---- 226-lesson readiness rollup ----
    classes = {"exact_occurrences": [], "entry_links": [], "family_links": [],
               "no_corpus_bridge": []}
    p_lessons, v_lessons, n_lessons = set(), set(), set()
    linked_kinds_by_unit = {}
    for r in rows:
        linked_kinds_by_unit.setdefault(r["unit_ref"], set()).add(r["entry_kind"])
    for row in ledger:
        classes[row["pvn_opportunity"]].append(row["lesson_id"])
        kinds = set()
        for u in row["semantic_units_domain_associated"]:
            kinds |= linked_kinds_by_unit.get(u, set())
        if "p" in kinds:
            p_lessons.add(row["lesson_id"])
        if "v" in kinds:
            v_lessons.add(row["lesson_id"])
        if "n" in kinds:
            n_lessons.add(row["lesson_id"])
    readiness = {
        "schema": "curriculum.l1l6_pvn_readiness.v1",
        "lessons_total": len(ledger),
        "lessons_with_exact_occurrence_candidates": len(classes["exact_occurrences"]),
        "lessons_with_entry_level_links": len(classes["entry_links"]),
        "lessons_with_family_level_links_only": len(classes["family_links"]),
        "lessons_with_p_links": len(p_lessons),
        "lessons_with_v_links": len(v_lessons),
        "lessons_with_n_links": len(n_lessons),
        "lessons_with_no_corpus_bridge": len(classes["no_corpus_bridge"]),
        "no_bridge_lessons": sorted(classes["no_corpus_bridge"]),
        "reasons_and_next_actions": {
            "exact_occurrences": "committed pilot/payload authority exists; next: widen fact coverage per occurrence (q-pvn-grounding downstream)",
            "entry_links": "entry resolved in the store; next: per-occurrence evidence rows to reach exact links (q-pvn-grounding)",
            "family_links": "domain association only; next: entry-level resolution through unit->entry plans (never surface similarity)",
            "no_corpus_bridge": "no repo-authoritative bridge exists for these lessons' domains yet; next: author units (q-unit-authoring), then entry plans",
            "v_and_n_links_zero_note": "all current precise links are P-entries — the honest state: verb/noun entry bridges await v/n-entry link plans grounded in their own authority stores",
        },
        "wildcard_free": all("*" not in (r.get("occurrence_id") or "") for r in rows),
    }
    return rows, readiness


def serialize(rows, readiness):
    out = {}
    out[str(BASE / "reports" / "occurrence-bridge.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    out[str(BASE / "reports" / "occurrence-bridge.meta.json")] = (json.dumps({
        "schema": "curriculum.l1l6_occurrence_bridge_row.v1.meta",
        "generator": "tools/build_curriculum_occurrence_bridge.py",
        "rows": len(rows),
        "occurrence_rows": sum(1 for r in rows if r["occurrence_id"]),
        "entry_rows": sum(1 for r in rows if not r["occurrence_id"]),
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out[str(BASE / "reports" / "pvn-readiness.json")] = (
        json.dumps(readiness, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    files = serialize(*build())
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
            print("FAIL: occurrence bridge differs from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: occurrence bridge byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
