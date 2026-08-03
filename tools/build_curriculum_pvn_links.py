#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build PRECISE curriculum->P/V/N candidate links from committed repo data.

Three link classes, all status=candidate, none inferable from surface/root
similarity (og-guarded):

1. occurrence links — the 12 p007 pilot occurrences (exact quran:s:a:w,
   entry_id from the pilot reverse index, promotion evidence = the
   occurrence's typed-fact ids + event trail);
2. ma occurrence links — the two committed website-payload exemplars for
   مَا (nafiya 93:3:1, relative 2:284:10), linked to inc-ma with
   preserve-alternatives abstention conditions;
3. entry links — particle entries named by the instructional units, with
   entry_id resolved from qamus/data/current/entries.jsonl (never from
   surface similarity), expected hover components from the increments'
   hover-field keys, and explicit promotion-evidence requirements.

Deterministic; stdlib only; writes ONLY curriculum/l1l6/links/pvn-precise-*.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P007 = ROOT / "qamus" / "examples" / "p007-li-pilot"
OUT = ROOT / "curriculum" / "l1l6" / "links"

# entry-level link plan: (source_key, unit, increment, hover_component,
#                         ambiguity/abstention condition)
ENTRY_PLAN = [
    ("p002", "u-s09", "inc-ownership", "owner_colour_segments", "clitic بِـ carve needs per-occurrence host verification (بِـ pre-flight queue exists)"),
    ("p007", "u-s09", "inc-ownership", "owner_colour_segments", "host-internal ownership unresolved until host-root certification"),
    ("p011", "u-n02", "inc-nawasikh", "abrogator_card", "أنّ vs إنّ selection is position-governed; unpointed -> abstain"),
    ("p012", "u-n02", "inc-nawasikh", "abrogator_card", "lightened إنْ does not govern (non_governing_use)"),
    ("p013", "u-n06", "inc-nawasikh", "abrogator_card", "أنْ masdariyya vs mukhaffafa collision; content-letter harakah + clause type required"),
    ("p014", "u-n06", "inc-ma", "function_inventory_panel", "إنْ shartiyya vs nafiya (rare) -> preserve alternatives"),
    ("p023", "u-n07", "inc-ma", "function_inventory_panel", "لَمَّا temporal vs jazima vs istithna'iyya — three regimes, occurrence-local"),
    ("p024", "u-n02", "inc-nawasikh", "swap_warning", "shadda distinguishes governing لكنّ from coordinating لكنْ"),
    ("p029", "u-n02", "inc-nawasikh", "abrogator_card", "kaf of كأنّ is not the preposition ك (no false split)"),
    ("p034", "u-n07", "inc-ma", "function_inventory_panel", "مِنْ vs مَنْ content-letter harakah guard"),
    ("p056", "u-n07", "inc-ma", "function_inventory_panel", "لا nafiya vs nahiya vs jinsiyya — following-form evidence required"),
    ("p057", "u-n01", "inc-nawasikh", "review_flag", "لَمْ vs لِمَ homograph gate before any jussive claim"),
    ("p058", "u-n01", "inc-nawasikh", "review_flag", "لَنْ subjunctive claim needs the following-verb marking"),
    ("p060", "u-n06", "inc-ma", "function_inventory_panel", "لَوْ counterfactual vs masdariyya (after ودّ) — clause evidence"),
    ("p061", "u-n02", "inc-nawasikh", "abrogator_card", "لعلّ governs as inna-family; trajji sense is entry-side"),
    ("p063", "u-n02", "inc-nawasikh", "abrogator_card", "ليت governs as inna-family; tamanni sense is entry-side"),
    ("p094", "u-n05", "inc-hidden", "hidden_element_chip", "elided 'a'id licence rows apply inside the sila"),
    ("p095", "u-n05", "inc-hidden", "hidden_element_chip", "agreement with feminine heads incl. non-human plurals"),
    ("p097", "u-n05", "inc-hidden", "hidden_element_chip", "الذين with human plurals; sila completeness check"),
    ("p099", "u-n07", "inc-ma", "alternatives_panel", "og-3: no default function; genuine splits stay attributed-unresolved (92:3:1 exemplar)"),
    ("p100", "u-n07", "inc-ma", "function_inventory_panel", "مَنْ interrogative vs shartiyya vs mawsula — apodosis/clause evidence"),
]

MA_OCCURRENCES = [
    ("quran:93:3:1", "ma_nafiya", "qamus/examples/website-payloads/ma_nafiya_93_3_1.payload.json"),
    ("quran:2:284:10", "ma_relative", "qamus/examples/website-payloads/ma_relative_2_284_10.payload.json"),
]


class PayloadBindingFailClosed(ValueError):
    """Refused rather than best-effort bound: dishonest or unreadable payload posture."""


def build_payload_binding(payload_file, pl):
    """The authoritative curriculum payload_binding for one ma exemplar.

    Carries the source payload's effective publication/certification
    posture (never only artifact id/hash) so no downstream consumer can
    infer deliverability from link presence or projection hash alone.
    Refuses (PayloadBindingFailClosed) rather than best-effort binding a
    payload whose posture is internally dishonest.
    """
    projection = pl.get("projection")
    if not isinstance(projection, dict):
        raise PayloadBindingFailClosed(
            "%s: payload.projection must be an object" % payload_file)
    certification = projection.get("certification") or {}
    status = certification.get("status")
    plane = certification.get("plane")
    if not isinstance(plane, dict):
        raise PayloadBindingFailClosed(
            "%s: projection.certification.plane must be an object" % payload_file)

    projection_hash = pl.get("projection_hash")
    appearances = (pl.get("reverse_links") or {}).get("occurrence_to_appearances")
    if not isinstance(appearances, list) or not appearances:
        raise PayloadBindingFailClosed(
            "%s: reverse_links.occurrence_to_appearances must be a "
            "non-empty array" % payload_file)
    reverse_hashes = {a.get("projection_hash") for a in appearances
                      if isinstance(a, dict)}
    if reverse_hashes != {projection_hash}:
        raise PayloadBindingFailClosed(
            "%s: projection_hash %r does not match its reverse appearance "
            "hashes %r" % (payload_file, projection_hash, sorted(
                h for h in reverse_hashes if h)))

    evidence_refs = projection.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        raise PayloadBindingFailClosed(
            "%s: projection.evidence_refs must be a list" % payload_file)

    eligible = projection.get("public_projection_eligible")
    if not isinstance(eligible, bool):
        raise PayloadBindingFailClosed(
            "%s: projection.public_projection_eligible must be an explicit "
            "boolean" % payload_file)

    if status != "certified":
        if eligible is not False:
            raise PayloadBindingFailClosed(
                "%s: certification_status %r is not certified but "
                "public_projection_eligible is %r, not explicit false"
                % (payload_file, status, eligible))
        certified_planes = sorted(k for k, v in plane.items()
                                  if v == "certified")
        if certified_planes:
            raise PayloadBindingFailClosed(
                "%s: certification_status %r is not certified but plane "
                "member(s) %s are still certified"
                % (payload_file, status, certified_planes))

    unresolved = projection.get("unresolved")
    if isinstance(unresolved, dict):
        unresolved_state = unresolved.get("state")
    elif unresolved is None:
        unresolved_state = None
    else:
        raise PayloadBindingFailClosed(
            "%s: projection.unresolved must be an object or null"
            % payload_file)
    if status != "certified" and unresolved_state is None:
        raise PayloadBindingFailClosed(
            "%s: certification_status %r is not certified but carries no "
            "projection.unresolved.state — a non-certified payload is "
            "never a genuinely settled source" % (payload_file, status))

    provenance_class = (pl.get("provenance") or {}).get("provenance_class")
    if not isinstance(provenance_class, str) or not provenance_class:
        raise PayloadBindingFailClosed(
            "%s: provenance.provenance_class must be a non-empty string"
            % payload_file)

    return {
        "payload_file": payload_file,
        "artifact_id": pl["artifact_id"],
        "projection_hash": projection_hash,
        "schema": pl["schema"],
        "certification_status": status,
        "public_projection_eligible": eligible,
        "unresolved_state": unresolved_state,
        "provenance_class": provenance_class,
        # verbatim ordered dependencies — never authority by presence alone
        "evidence_refs": list(evidence_refs),
    }


def build():
    entries_by_key = {}
    with (ROOT / "qamus" / "data" / "current" / "entries.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            for sk in r.get("source_keys", []):
                entries_by_key[sk] = {"entry_id": r["id"], "headword": r.get("headword")}

    facts = [json.loads(l) for l in
             (P007 / "typed-facts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    reverse_index = json.loads((P007 / "entry-reverse-index.json").read_text(encoding="utf-8"))
    p007_entry_id = reverse_index["entry_id"]

    rows = []
    # class 1: the 12 pilot occurrences
    by_loc = {}
    for fct in facts:
        for s in fct.get("surface_spans", []):
            loc = s.get("quran_loc")
            if loc:
                by_loc.setdefault(loc, {"surface": s.get("surface"), "fact_ids": []})
                by_loc[loc]["fact_ids"].append(fct["fact_id"])
    for loc in sorted(by_loc):
        d = by_loc[loc]
        rows.append({
            "schema": "curriculum.l1l6_pvn_precise_link.v1",
            "link_id": "pl-occ-" + loc.replace("quran:", "").replace(":", "-"),
            "link_class": "occurrence",
            "status": "candidate",
            "unit_ref": "u-s09",
            "increment": "inc-ownership",
            "entry_id": p007_entry_id,
            "source_key": "p007",
            "occurrence_id": loc,
            "surface": d["surface"],
            "expected_hover_component": "owner_colour_segments",
            "promotion_evidence": {
                "existing": sorted(d["fact_ids"]),
                "trail": "qamus/examples/p007-li-pilot/certification/events.jsonl",
                "needed_for_promotion": "host-root certification via the sarf evidence ladder before host-internal ownership colouring",
            },
            "ambiguity_abstention": "host_internal_letter_ownership unresolved (consumer abstains no_root_evidence)",
            "linkage_basis": "committed pilot store (never surface similarity)",
        })
    # class 2: the ma exemplars — the payload is READ, never paraphrased:
    # its exact surface, artifact identity and projection hash travel with
    # the link (Sol fix-request round 2, finding 4: surface:null degraded
    # the committed payload binding)
    for loc, kind, payload in MA_OCCURRENCES:
        pl = json.loads((ROOT / payload).read_text(encoding="utf-8"))
        assert pl["occurrence_id"] == loc, "payload/loc drift: %s" % payload
        rows.append({
            "schema": "curriculum.l1l6_pvn_precise_link.v1",
            "link_id": "pl-ma-" + loc.replace("quran:", "").replace(":", "-"),
            "link_class": "occurrence",
            "status": "candidate",
            "unit_ref": "u-n07",
            "increment": "inc-ma",
            "entry_id": entries_by_key["p099"]["entry_id"],
            "source_key": "p099",
            "occurrence_id": loc,
            "surface": pl["projection"]["surface"],
            "payload_binding": build_payload_binding(payload, pl),
            "expected_hover_component": "function_inventory_panel",
            "promotion_evidence": {
                "existing": [payload],
                "needed_for_promotion": "per-occurrence discriminator features (following form, clause type) recorded as declared evidence + review",
            },
            "ambiguity_abstention": "if more than one function survives its discriminators the link stays preserve_alternatives (og-3); kind hint from payload: %s" % kind,
            "linkage_basis": "committed website-payload exemplar (never surface similarity)",
        })
    # class 3: entry-level plans
    for sk, unit, inc, hover, ambig in ENTRY_PLAN:
        ent = entries_by_key.get(sk)
        if ent is None:
            raise SystemExit("source_key %s not in entry store" % sk)
        rows.append({
            "schema": "curriculum.l1l6_pvn_precise_link.v1",
            "link_id": "pl-ent-%s" % sk,
            "link_class": "entry",
            "status": "candidate",
            "unit_ref": unit,
            "increment": inc,
            "entry_id": ent["entry_id"],
            "source_key": sk,
            "occurrence_id": None,
            "surface": ent["headword"],
            "expected_hover_component": hover,
            "promotion_evidence": {
                "existing": [],
                "needed_for_promotion": "per-occurrence evidence rows on this entry's canonical occurrences; iʿrāb-bearing facts additionally need the two-vote gate",
            },
            "ambiguity_abstention": ambig,
            "linkage_basis": "entry-store source_key resolution (never surface similarity)",
        })
    return rows


def serialize(rows):
    out = {}
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    out[str(OUT / "pvn-precise-links.jsonl")] = body.encode("utf-8")
    meta = {
        "schema": "curriculum.l1l6_pvn_precise_link.v1.meta",
        "generator": "tools/build_curriculum_pvn_links.py",
        "rows": len(rows),
        "classes": {
            "occurrence": sum(1 for r in rows if r["link_class"] == "occurrence"),
            "entry": sum(1 for r in rows if r["link_class"] == "entry"),
        },
        "note": "supersedes the broad lk-* families in pvn-candidate-links.jsonl for precision; the lk file remains as the family-level rationale. ALL rows candidate; no link derives from root or surface similarity.",
    }
    out[str(OUT / "pvn-precise-links.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


# --------------------------------------------------------------------------- #
# self-test -- synthetic fixtures only, never the tracked payloads
# --------------------------------------------------------------------------- #

def _synthetic_ma_payload(status, eligible, plane_function, unresolved_state,
                          evidence_refs=("ref:a", "ref:z")):
    proj_hash = "1" * 64
    return {
        "artifact_id": "artifact:selftest:1",
        "schema": "qamus.website_projection_payload.v1",
        "projection_hash": proj_hash,
        "reverse_links": {
            "occurrence_to_appearances": [
                {"appearance_id": "app:selftest:1", "projection_hash": proj_hash},
            ],
        },
        "provenance": {"provenance_class": "illustrative-from-live"},
        "projection": {
            "certification": {
                "status": status,
                "plane": {"function": plane_function, "segmentation": "candidate"},
            },
            "public_projection_eligible": eligible,
            "evidence_refs": list(evidence_refs),
            "unresolved": (
                {"state": unresolved_state} if unresolved_state is not None
                else None
            ),
        },
    }


def _run(label, condition, failures):
    print(("ok   " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def self_test():
    failures = []

    # 1. unresolved/review-required posture propagates into the binding.
    stale = _synthetic_ma_payload(
        status="unresolved", eligible=False, plane_function="review_required",
        unresolved_state="certification_evidence_unresolved",
        evidence_refs=("ref:zzz", "ref:aaa"))
    binding = build_payload_binding("selftest.payload.json", stale)
    _run("unresolved posture propagates into the payload binding",
        binding["certification_status"] == "unresolved"
        and binding["public_projection_eligible"] is False
        and binding["unresolved_state"] == "certification_evidence_unresolved"
        and binding["provenance_class"] == "illustrative-from-live",
        failures)

    # 2. evidence refs remain verbatim-ordered dependencies, never authority.
    _run("evidence refs are carried verbatim-ordered, not sorted/deduped "
        "into authority",
        binding["evidence_refs"] == ["ref:zzz", "ref:aaa"],
        failures)

    # 3. a certified-plane residue on a non-certified payload is rejected.
    residue = _synthetic_ma_payload(
        status="unresolved", eligible=False, plane_function="certified",
        unresolved_state="certification_evidence_unresolved")
    try:
        build_payload_binding("selftest.payload.json", residue)
        rejected = False
    except PayloadBindingFailClosed:
        rejected = True
    _run("a certified-plane residue on a non-certified payload is rejected",
        rejected, failures)

    # 4. public eligibility true on a non-certified payload is rejected.
    over_eligible = _synthetic_ma_payload(
        status="unresolved", eligible=True, plane_function="review_required",
        unresolved_state="certification_evidence_unresolved")
    try:
        build_payload_binding("selftest.payload.json", over_eligible)
        rejected = False
    except PayloadBindingFailClosed:
        rejected = True
    _run("public_projection_eligible=true on a non-certified payload is "
        "rejected", rejected, failures)

    # 5. missing/non-list evidence_refs is refused.
    no_refs = _synthetic_ma_payload(
        status="unresolved", eligible=False, plane_function="review_required",
        unresolved_state="certification_evidence_unresolved")
    no_refs["projection"]["evidence_refs"] = None
    try:
        build_payload_binding("selftest.payload.json", no_refs)
        rejected = False
    except PayloadBindingFailClosed:
        rejected = True
    _run("missing/non-list evidence_refs is refused", rejected, failures)

    # 6. a projection hash that does not match its reverse appearance
    #    hashes is refused.
    forked = _synthetic_ma_payload(
        status="unresolved", eligible=False, plane_function="review_required",
        unresolved_state="certification_evidence_unresolved")
    forked["reverse_links"]["occurrence_to_appearances"][0]["projection_hash"] = "2" * 64
    try:
        build_payload_binding("selftest.payload.json", forked)
        rejected = False
    except PayloadBindingFailClosed:
        rejected = True
    _run("a projection hash forked from its reverse appearance hashes is "
        "refused", rejected, failures)

    # 7. a genuinely settled (certified) source needs no unresolved state.
    settled = _synthetic_ma_payload(
        status="certified", eligible=True, plane_function="certified",
        unresolved_state=None)
    settled_binding = build_payload_binding("selftest.payload.json", settled)
    _run("a genuinely settled certified source carries unresolved_state=null",
        settled_binding["unresolved_state"] is None, failures)

    # 8. quran:61:5:4 and the p007 non-ma occurrence paths are untouched by
    #    these ma-specific checks: real build() never attaches a
    #    payload_binding to a class-1 pilot-occurrence row.
    rows = build()
    frozen = [r for r in rows if r.get("occurrence_id") == "quran:61:5:4"]
    _run("quran:61:5:4 (p007 pilot occurrence) is present and carries no "
        "ma-specific payload_binding",
        bool(frozen) and all("payload_binding" not in r for r in frozen),
        failures)
    p007_rows = [r for r in rows if r.get("source_key") == "p007"
                and r.get("link_class") == "occurrence"]
    _run("p007 occurrence-class rows carry no payload_binding",
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
        files = serialize(build())
    except PayloadBindingFailClosed as exc:
        print("PVN PRECISE LINKS REFUSED: %s" % exc)
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
            print("FAIL: precise links differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: precise links byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
