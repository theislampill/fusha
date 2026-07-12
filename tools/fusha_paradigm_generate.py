#!/usr/bin/env python3
"""RM-40 paradigm-licensed candidate generation (stdlib only, deterministic).

Given a KNOWN lexeme (root + measure — in production a *certified* ledger fact),
synthesise the regular paradigm cells the sourced evidence baseline lacks. Every
output is a CANDIDATE, never a fact:

* ``certification_state`` is always ``candidate``;
* ``generation_used`` is always ``true`` and ``source`` is ``paradigm_generated``
  (never ``qamus_current_authored``) — the two planes stay provably disjoint;
* ``supersedes`` is always ``null`` — a generated row may never supersede a
  sourced baseline fact, and the generator abstains when a documented form
  already resolves the (lemma, slot);
* competing licensed surfaces are preserved (``semantic_tie``), never collapsed;
* provenance carries the paradigm id and the verified rule chain.

Generation is gated by :mod:`tools.rm40_gate_stack`: weak roots, hamza seats,
Form-I maṣdar, and strict-key homographs abstain. Output rows validate against
``qamus/schemas/paradigm-generated-candidate.schema.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import normalize_ar
from tools import rm40_gate_stack as gates

PARADIGM_ID = "fusha/verb-measures@1"
PLURAL_PARADIGM_ID = "fusha/plural-gender-rules@1"
ACTOR = "sarf.paradigm_generated.v1"
METHOD = "paradigm_licensed_generation"
SCHEMA = "qamus.paradigm_generated_candidate.v1"
FIXED_CREATED_AT = "2026-07-11T00:00:00Z"

VERB_MEASURES_PATH = ROOT / "sarf" / "rules" / "verb-measures.json"
PLACEHOLDERS = "فعل"


@lru_cache(maxsize=1)
def _measures() -> Dict[str, Dict[str, Any]]:
    payload = json.loads(VERB_MEASURES_PATH.read_text(encoding="utf-8"))
    return {str(form["form"]).upper(): form for form in payload.get("forms") or []}


def substitute(template: str, radicals: List[str]) -> str:
    """Fill a wazn template (ف/ع/ل placeholders) with radicals in one pass.

    Uses ``str.translate`` so a root that itself contains ف/ع/ل is never
    re-substituted. Non-placeholder scaffolding (augments, harakāt, shadda) is
    preserved verbatim.
    """
    if len(radicals) < 3:
        raise ValueError("triliteral substitution needs three radicals")
    table = {ord(PLACEHOLDERS[i]): radicals[i] for i in range(3)}
    return template.translate(table)


def _slot_templates(measure_form: Dict[str, Any], slot: str) -> List[str]:
    raw = str(measure_form.get(slot) or "").strip()
    if not raw or "—" in raw or "sam" in raw or "irregular" in raw:
        return []
    return [part.strip() for part in raw.split("/") if part.strip()]


def _candidate_id(subject: Dict[str, Any], value: Dict[str, Any]) -> str:
    core = {"subject": subject, "generated_surface": value["generated_surface"]}
    digest = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return "sha256:" + digest


def _build_row(
    *,
    subject: Dict[str, Any],
    surfaces: List[str],
    wazns: List[str],
    rule_chain: List[str],
    paradigm_id: str,
    input_source: str,
) -> Dict[str, Any]:
    primary_surface, primary_wazn = surfaces[0], wazns[0]
    competing = [
        {
            "generated_surface": surf,
            "surface_norm_strict": normalize_ar.norm_strict(surf),
            "wazn": wazn,
            "semantic_tie": True,
        }
        for surf, wazn in zip(surfaces[1:], wazns[1:])
    ]
    semantic_tie = len(surfaces) > 1
    value = {
        "generated_surface": primary_surface,
        "surface_norm_strict": normalize_ar.norm_strict(primary_surface),
        "wazn": primary_wazn,
    }
    row = {
        "schema": SCHEMA,
        "candidate_id": _candidate_id(subject, value),
        "certification_state": "candidate",
        "generation_used": True,
        "source": "paradigm_generated",
        "subject": subject,
        "value": value,
        "competing_alternatives": competing,
        "semantic_tie": semantic_tie,
        "provenance": {
            "actor": ACTOR,
            "method": METHOD,
            "paradigm_id": paradigm_id,
            "rule_chain": list(rule_chain),
            "input_source": input_source,
            "created_at": FIXED_CREATED_AT,
        },
        "supersedes": None,
    }
    return row


def _baseline_resolves(baseline_forms: Iterable[Dict[str, Any]], lemma: str, slot: str, surface: str) -> bool:
    key = normalize_ar.norm_strict(surface)
    for form in baseline_forms or []:
        if str(form.get("lemma")) != str(lemma):
            continue
        if form.get("slot") not in (None, slot):
            continue
        if normalize_ar.norm_strict(str(form.get("surface", ""))) == key:
            return True
    return False


def generate_verb(
    lexeme: Dict[str, Any],
    slots: Optional[List[str]] = None,
    baseline_forms: Iterable[Dict[str, Any]] = (),
    input_source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate candidate rows for a known verb lexeme's regular paradigm cells."""
    root = lexeme["root"]
    measure = str(lexeme["measure"]).upper()
    radicals = gates.radical_letters(root)
    form = _measures().get(measure)
    if form is None or len(radicals) != 3:
        return []
    slots = slots or ["past_active", "present_active", "masdar", "ism_fa3il", "ism_maf3ul"]
    source_ref = input_source or ("synthetic:%s:%s" % (lexeme["lemma"], measure))
    rows: List[Dict[str, Any]] = []
    for slot in slots:
        decision = gates.slot_gate(root, measure, slot)
        if decision["decision"] != "emit":
            continue
        templates = _slot_templates(form, slot)
        if not templates:
            continue
        surfaces = [substitute(t, radicals) for t in templates]
        # A generated surface that strict-key collides with a DIFFERENT baseline
        # documented form must defer to the sourced fact (abstain).
        if any(
            _baseline_resolves(baseline_forms, lexeme["lemma"], slot, surf)
            for surf in surfaces
        ):
            continue
        rule_chain = [
            "%s#form:%s#slot:%s" % (gates.VERB_MEASURES, measure, slot),
            *decision["gates"],
        ]
        rows.append(
            _build_row(
                subject={
                    "pos": "verb",
                    "lemma": lexeme["lemma"],
                    "root": root,
                    "measure": measure,
                    "slot": slot,
                },
                surfaces=surfaces,
                wazns=templates,
                rule_chain=rule_chain,
                paradigm_id=PARADIGM_ID,
                input_source=source_ref,
            )
        )
    return rows


# Broken-plural templates keyed to plural-gender-rules.json ids (skeleton wazns).
_PLURAL_TEMPLATES = {
    "taksir-afal": "أَفْعَال",
}


def generate_noun_plural(
    noun: Dict[str, Any],
    baseline_forms: Iterable[Dict[str, Any]] = (),
    input_source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate a broken-plural candidate (candidate + two-vote by contract).

    Broken plurals are lexically selected, so this PROPOSES a class and never
    certifies the singular (plural-gender-rules.json guard, carried verbatim).
    """
    root = noun["root"]
    template_id = noun.get("plural_template_id", "taksir-afal")
    radicals = gates.radical_letters(root)
    template = _PLURAL_TEMPLATES.get(template_id)
    if template is None or len(radicals) != 3:
        return []
    decision = gates.plural_gate(root, template_id)
    if decision["decision"] != "emit":
        return []
    surface = substitute(template, radicals)
    if _baseline_resolves(baseline_forms, noun["lemma"], "broken_plural", surface):
        return []
    source_ref = input_source or ("synthetic:%s:plural" % noun["lemma"])
    rule_chain = ["%s#%s" % (gates.PLURAL_GATE, template_id), *decision["gates"]]
    return [
        _build_row(
            subject={
                "pos": "noun",
                "lemma": noun["lemma"],
                "root": root,
                "measure": None,
                "slot": "broken_plural",
            },
            surfaces=[surface],
            wazns=[template],
            rule_chain=rule_chain,
            paradigm_id=PLURAL_PARADIGM_ID,
            input_source=source_ref,
        )
    ]


def write_candidates(store_dir: Path, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Append generated candidates to their own disjoint store + manifest."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    shard = store_dir / "candidates.jsonl"
    with shard.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "schema": "qamus.paradigm_generated_candidate_manifest.v1",
        "store_role": "generated_candidates",
        "disjoint_from": "fusha/morphology/data/largelexicon-stems.full.jsonl",
        "rows_appended": len(rows),
        "generation_used": True,
        "source": "paradigm_generated",
    }
    (store_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _self_test() -> None:
    sound = generate_verb(
        {"pos": "verb", "lemma": "أَكْتَبَ", "root": "ك ت ب", "measure": "IV"},
        slots=["present_active"],
    )
    assert len(sound) == 1, sound
    assert sound[0]["value"]["generated_surface"] == "يُكْتِبُ", sound[0]["value"]
    assert sound[0]["source"] == "paradigm_generated"
    assert sound[0]["generation_used"] is True
    assert sound[0]["supersedes"] is None
    assert sound[0]["provenance"]["rule_chain"]

    competing = generate_verb(
        {"pos": "verb", "lemma": "كَتَبَ", "root": "ك ت ب", "measure": "I"},
        slots=["present_active"],
    )
    assert competing and competing[0]["semantic_tie"] is True, competing
    assert len(competing[0]["competing_alternatives"]) >= 1

    assert generate_verb(
        {"pos": "verb", "lemma": "قَالَ", "root": "ق و ل", "measure": "I"},
        slots=["present_active"],
    ) == []
    assert generate_verb(
        {"pos": "verb", "lemma": "كَتَبَ", "root": "ك ت ب", "measure": "I"},
        slots=["masdar"],
    ) == []

    plural = generate_noun_plural({"pos": "noun", "lemma": "قَلَم", "root": "ق ل م", "plural_template_id": "taksir-afal"})
    assert plural and plural[0]["certification_state"] == "candidate", plural
    print("RM-40 paradigm generator self-test OK")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        return 0
    parser.error("--self-test is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
