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

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_curriculum_pvn_links as pvn_links  # noqa: E402


class OccurrenceBridgeFailClosed(ValueError):
    """Refused rather than best-effort bridged: link-to-payload drift or an
    unbindable payload posture."""


def _jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def payload_unresolved_dependencies(binding):
    """Explicit dependency naming a non-certified source's posture, plus
    the existing future-occurrence discriminator dependency."""
    deps = []
    if binding["certification_status"] != "certified":
        deps.append(
            "source payload certification_status=%s "
            "(unresolved_state=%s); public_projection_eligible=%s — this "
            "occurrence is not publicly deliverable pending re-certification"
            % (binding["certification_status"], binding["unresolved_state"],
               binding["public_projection_eligible"]))
    deps.append(
        "per-occurrence discriminator features (following form, "
        "clause type) as declared evidence for any FURTHER "
        "occurrence beyond the payload exemplars")
    return deps


def build_payload_bound_fields(link, payload_file):
    """The payload-authority row fields for one ma occurrence link.

    Copies (never reconstructs a different subset of) the precise link's
    payload_binding, but only after verifying it exactly matches a fresh
    binding recomputed from the current committed payload — refusing
    (OccurrenceBridgeFailClosed) on any link-to-payload drift.
    """
    occ = link.get("occurrence_id")
    pl = json.loads((ROOT / payload_file).read_text(encoding="utf-8"))
    if pl.get("occurrence_id") != occ:
        raise OccurrenceBridgeFailClosed("payload/occ drift: %s" % occ)
    recomputed = pvn_links.build_payload_binding(payload_file, pl)
    link_binding = link.get("payload_binding")
    if not isinstance(link_binding, dict):
        raise OccurrenceBridgeFailClosed(
            "%s: precise link carries no payload_binding to verify against "
            "the current payload" % occ)
    mismatches = sorted(k for k in recomputed if link_binding.get(k) != recomputed[k])
    if mismatches:
        raise OccurrenceBridgeFailClosed(
            "%s: link-to-payload binding drift in field(s) %s — the "
            "precise link's payload_binding no longer matches the current "
            "payload" % (occ, ", ".join(mismatches)))

    apps = pl["reverse_links"]["occurrence_to_appearances"]
    plane = (pl["projection"].get("certification") or {}).get("plane", {})
    return {
        "surface": pl["projection"]["surface"],
        "payload_binding": dict(link_binding),
        "appearances": {
            "rows": apps,
            "count": len(apps),
            "page_relation_note": "appearance ids are page-scoped renderings from the committed payload's reverse links; page relations are the payload's own (verbatim)",
            "single_hash_parity": {a["projection_hash"] for a in apps}
                                  == {pl["projection_hash"]},
        },
        "required_fact_planes": plane,
        "required_sarf_facts": [],
        "required_sarf_facts_note": (
            "rootless particle per the payload (root: null); no sarf "
            "fact is required for this occurrence"),
        "required_nahw_facts": sorted(pl["projection"].get("evidence_refs") or []),
        "required_nahw_facts_note": (
            "the payload's function-plane evidence refs, verbatim — "
            "declared dependencies only; an unresolved/review-required "
            "occurrence's evidence refs are never treated as a backing "
            "fact by presence alone"),
        "unresolved_dependencies": payload_unresolved_dependencies(recomputed),
    }


def build():
    units = _jsonl(BASE / "units" / "instructional-units.jsonl")
    # recomputed in-process (never read back from the committed output file)
    # so an ma occurrence's payload_binding is always verified against the
    # current payload, never against a possibly-stale link on disk.
    plinks = pvn_links.build()
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
        if link.get("surface") is not None:
            row["surface"] = link["surface"]
        payload_files = [p for p in (link.get("promotion_evidence", {})
                                     .get("existing") or [])
                         if p.endswith(".payload.json")]
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
        elif occ and payload_files:
            # committed website-payload authority (Sol fix-request round 2,
            # finding 4): the payload's EXACT surface, appearances, fact
            # planes and binding are preserved — never degraded to
            # surface:null / zero appearances
            row.update(build_payload_bound_fields(link, payload_files[0]))
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


# --------------------------------------------------------------------------- #
# self-test -- synthetic fixtures only, never the tracked payload/link files
# --------------------------------------------------------------------------- #

def _run(label, condition, failures):
    print(("ok   " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def self_test():
    failures = []

    ma_file = "qamus/examples/website-payloads/ma_nafiya_93_3_1.payload.json"
    real_pl = json.loads((ROOT / ma_file).read_text(encoding="utf-8"))
    correct_binding = pvn_links.build_payload_binding(ma_file, real_pl)
    good_link = {
        "occurrence_id": real_pl["occurrence_id"],
        "payload_binding": correct_binding,
    }

    fields = build_payload_bound_fields(good_link, ma_file)
    _run("unresolved/review-required payload posture propagates into the "
        "bridge row",
        fields["payload_binding"]["certification_status"] == "unresolved"
        and fields["payload_binding"]["public_projection_eligible"] is False,
        failures)
    _run("evidence refs remain dependencies (sorted required_nahw_facts, "
        "never asserted as a backing fact)",
        fields["required_nahw_facts"]
        == sorted(real_pl["projection"]["evidence_refs"])
        and "fact backing this occurrence" not in fields["required_nahw_facts_note"]
        and "never" in fields["required_nahw_facts_note"],
        failures)
    _run("a non-certified posture adds an explicit unresolved dependency "
        "naming status/state/eligibility",
        any(
            "certification_status=unresolved" in dep
            and "public_projection_eligible=False" in dep
            for dep in fields["unresolved_dependencies"]
        )
        and any("FURTHER" in dep for dep in fields["unresolved_dependencies"]),
        failures)

    # binding drift is rejected by the bridge.
    drifted_link = {
        "occurrence_id": real_pl["occurrence_id"],
        "payload_binding": {**correct_binding, "public_projection_eligible": True},
    }
    try:
        build_payload_bound_fields(drifted_link, ma_file)
        rejected = False
    except OccurrenceBridgeFailClosed:
        rejected = True
    _run("link-to-payload binding drift is rejected by the bridge",
        rejected, failures)

    missing_binding_link = {"occurrence_id": real_pl["occurrence_id"]}
    try:
        build_payload_bound_fields(missing_binding_link, ma_file)
        rejected = False
    except OccurrenceBridgeFailClosed:
        rejected = True
    _run("a link carrying no payload_binding is rejected, not "
        "best-effort bridged", rejected, failures)

    # quran:61:5:4 and p007 non-ma paths are not rewritten by these
    # ma-specific checks: the real build() never attaches a payload_binding
    # to a class-1 pilot-occurrence bridge row.
    rows, _readiness = build()
    frozen = [r for r in rows if r.get("occurrence_id") == "quran:61:5:4"]
    _run("quran:61:5:4 (p007 pilot occurrence) bridge row carries no "
        "ma-specific payload_binding",
        bool(frozen) and all("payload_binding" not in r for r in frozen),
        failures)
    p007_rows = [r for r in rows if r.get("source_key") == "p007"]
    _run("p007 bridge rows carry no payload_binding",
        bool(p007_rows) and all("payload_binding" not in r for r in p007_rows),
        failures)

    if failures:
        print("\n%d SELF-TEST CASE(S) FAILED" % len(failures))
        return 1
    print("\nALL SELF-TEST CASES PASSED")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    check = "--check" in argv
    try:
        files = serialize(*build())
    except OccurrenceBridgeFailClosed as exc:
        print("OCCURRENCE BRIDGE REFUSED: %s" % exc)
        return 1
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
