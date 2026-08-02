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
    # class 2: the ma exemplars
    for loc, kind, payload in MA_OCCURRENCES:
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
            "surface": None,
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
            print("FAIL: precise links differ from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: precise links byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
