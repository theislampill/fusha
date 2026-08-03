#!/usr/bin/env python3
"""RM-40 paradigm-generation gate stack (stdlib only, deterministic).

The generator's DEFAULT output is abstention. A licensed paradigm slot is only
emitted when its radicals are sound (no weak letter, no hamza seat), the slot is
not a forbidden samāʿī cell (Form-I maṣdar), and no strict-key homograph
collision fires. Every place a paradigm could over-license, this stack abstains
rather than downgrade-and-keep — the sourced evidence baseline already carries
the irregular attested forms, so generation only needs the safe regular cells.

The gate ids emitted here name real rules in ``sarf/rules/*.json`` and are
carried forward into each candidate's ``provenance.rule_chain``.
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import normalize_ar

RULES_DIR = ROOT / "sarf" / "rules"

# Weak radicals (ʾiʿlāl letters) and hamza seats: a template cannot deterministically
# choose the seat or recover a mutated/hidden radical, so any of these forces abstention.
WEAK_LETTERS = set("اوىي")
HAMZA_CARRIERS = set("ءأإؤئآ")
ABSTAIN_RADICALS = WEAK_LETTERS | HAMZA_CARRIERS

WEAK_ROOT_GATE = "weak-root-gates.json"
HAMZA_GATE = "hamza-gates.json"
VERB_MEASURE_GATE = "verb-measure-gates.json"
MASDAR_GATE = "masdar-participle-gates.json"
PLURAL_GATE = "plural-gender-rules.json"
VERB_MEASURES = "verb-measures.json"


class GateError(ValueError):
    """Raised when the gate stack cannot verify a cited rule id."""


@lru_cache(maxsize=None)
def _rule_ids(filename: str) -> frozenset[str]:
    """Return the set of stable rule ids declared in a sarf rules file."""
    payload = json.loads((RULES_DIR / filename).read_text(encoding="utf-8"))
    ids: set[str] = set()
    for key in ("rules", "patterns", "projector_contract"):
        for entry in payload.get(key) or []:
            if isinstance(entry, dict) and entry.get("id"):
                ids.add(entry["id"])
    for entry in payload.get("norm_collapses") or []:
        if isinstance(entry, dict) and entry.get("id"):
            ids.add(entry["id"])
    return frozenset(ids)


def _cite(filename: str, rule_id: str) -> str:
    """Build a verified rule-chain citation ``file#rule_id`` (fails closed if absent)."""
    if rule_id not in _rule_ids(filename):
        raise GateError("unknown rule id %s in %s" % (rule_id, filename))
    return "%s#%s" % (filename, rule_id)


def radical_letters(root: str) -> List[str]:
    """Split a space-delimited root string (e.g. ``ك ت ب``) into radicals."""
    return [part for part in str(root or "").split() if part]


def has_weak_or_hamza(root: str) -> bool:
    return any(ch in ABSTAIN_RADICALS for radical in radical_letters(root) for ch in radical)


def strict_key_collision(surface: str, others: Iterable[str]) -> bool:
    """True if ``surface`` collapses onto a DIFFERENT surface under the strict key.

    Mirrors ``fact_projectors.homograph_norm_key_collision`` for generated forms:
    two distinct vocalised surfaces sharing a strict key are a homograph the
    template cannot adjudicate, so the caller must abstain.
    """
    key = normalize_ar.norm_strict(surface)
    for other in others:
        if other != surface and normalize_ar.norm_strict(other) == key:
            return True
    return False


def slot_gate(root: str, measure: str, slot: str) -> Dict[str, Any]:
    """Decide emit vs abstain for a verb (root, measure, slot).

    Returns ``{decision, defeater, detail, gates}``. ``gates`` is the verified
    rule-chain (only meaningful on an emit).
    """
    if has_weak_or_hamza(root):
        # A hollow/defective/assimilated radical, or a hamza seat, is not
        # deterministically fixed by the template.
        gate = HAMZA_GATE if any(ch in HAMZA_CARRIERS for r in radical_letters(root) for ch in r) else WEAK_ROOT_GATE
        defeater = "hamza_seat" if gate == HAMZA_GATE else "hollow_defective_assimilated"
        # hamza-gates.json ids are collapse names; cite the weak-root gate that owns the tier.
        cite_file, cite_id = (WEAK_ROOT_GATE, defeater)
        return {
            "decision": "abstain",
            "defeater": defeater,
            "detail": "weak/hamza radical cannot be templated deterministically",
            "gates": [_cite(cite_file, cite_id)],
        }
    if slot == "masdar" and str(measure).upper() == "I":
        # Form-I maṣdar is samāʿī (learned per verb); the paradigm declares it non-deducible.
        return {
            "decision": "abstain",
            "defeater": "form_i_masdar_samai",
            "detail": "Form-I maṣdar is samāʿī — forbidden to generate",
            "gates": [_cite(MASDAR_GATE, "masdar_nominal")],
        }
    return {
        "decision": "emit",
        "defeater": None,
        "detail": "sound triliteral radicals; regular %s slot" % slot,
        "gates": [
            _cite(WEAK_ROOT_GATE, "weak_root_qac_agrees"),
            _cite(VERB_MEASURE_GATE, "form_dominant_sense_keyclean"),
        ],
    }


def plural_gate(root: str, template_id: str) -> Dict[str, Any]:
    """Decide emit vs abstain for a broken-plural noun template.

    Broken plurals are the highest over-generation risk (lexically selected).
    A sound-radical singular licenses a candidate; the plural-gender guard is
    carried verbatim ("proposes a class; never certifies"). Weak/hamza radicals
    abstain like the verb path.

    This gates PARADIGM GENERATION only (can a root's radicals be safely
    template-substituted into a NEW candidate surface). Classifying an already
    OBSERVED occurrence against documented entry evidence is a distinct,
    stricter gate — see ``broken_plural_lexeme_link_gate`` below.
    """
    if has_weak_or_hamza(root):
        return {
            "decision": "abstain",
            "defeater": "weak_or_hamza_root",
            "detail": "weak/hamza radical in a broken-plural singular",
            "gates": [_cite(WEAK_ROOT_GATE, "hollow_defective_assimilated")],
        }
    return {
        "decision": "emit",
        "defeater": None,
        "detail": "broken plural proposes a class; never certifies the singular",
        "gates": [_cite(PLURAL_GATE, template_id)],
    }


@lru_cache(maxsize=1)
def _load_plural_gender_rules() -> Dict[str, Any]:
    return json.loads((RULES_DIR / PLURAL_GATE).read_text(encoding="utf-8"))


def _plural_gender_rules(rules_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return the plural-gender-rules.json payload, or a caller-supplied override.

    The override exists ONLY so a mutation test can prove a gate genuinely
    depends on the rule file's CONTENT (see ``sarf/evals/plural-gender-
    operationalization-eval.jsonl``'s mutation row); ``_cite`` below always
    validates ids against the real committed file regardless.
    """
    return rules_payload if rules_payload is not None else _load_plural_gender_rules()


def is_broken_plural_template_id(template_id: str, rules_payload: Dict[str, Any] | None = None) -> bool:
    """True only for a 'taksir' (broken-plural) pattern id.

    False for a known msl/mfl (sound-plural, inflectional) id and for any
    unrecognised id — a sound-plural suffix is never a root or a template
    (plural-gender-rules.json#sound-plural-is-inflection-not-template).
    """
    for pattern in _plural_gender_rules(rules_payload).get("patterns") or []:
        if pattern.get("id") == template_id:
            return pattern.get("kind") == "taksir"
    return False


def broken_plural_lexeme_link_gate(
    root: str | None,
    template_id: str | None,
    *,
    attested_pair: bool,
    rare_license_ok: bool = True,
    plural_of_plural_base_attested: bool = True,
    rules_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Decide emit vs abstain for CLASSIFYING an already-observed broken plural.

    Every requirement below is a hard abstain, never a default or a best guess
    (plural-gender-rules.json#projector_contract carries the rule text this
    function enforces):

    * a missing ``template_id`` never defaults to any pattern
      (``plural_template_id_missing``);
    * an msl/mfl id is inflectional, never a broken-plural template
      (``sound_plural_suffix_not_broken_template``);
    * root evidence must actually be supplied (``no_root_evidence``);
    * the observed surface must exactly pair with a documented entry
      plural-form/lemma link (``no_attested_lexeme_pair``);
    * a rare/second-order template needs the lexeme on its own closed
      ``licensed_lexemes`` list (``rare_plural_unlicensed``);
    * a jamʿ-al-jamʿ (plural-of-plural) template needs its BASE plural
      independently attested (``plural_of_plural_base_unattested``).
    """
    if not template_id:
        return {
            "decision": "abstain",
            "defeater": "plural_template_id_missing",
            "detail": "no plural_template_id was supplied; a missing id is never defaulted to any template",
            "gates": [],
        }
    payload = _plural_gender_rules(rules_payload)
    pattern = next(
        (p for p in payload.get("patterns") or [] if p.get("id") == template_id), None
    )
    if pattern is None:
        raise GateError("unknown plural-gender-rules.json pattern id: " + template_id)
    if pattern.get("kind") != "taksir":
        return {
            "decision": "abstain",
            "defeater": "sound_plural_suffix_not_broken_template",
            "detail": (
                "%s is a sound-plural (%s) inflectional ending, never a root or a "
                "broken-plural template" % (template_id, pattern.get("kind"))
            ),
            "gates": [_cite(PLURAL_GATE, template_id)],
        }
    if not radical_letters(root or ""):
        return {
            "decision": "abstain",
            "defeater": "no_root_evidence",
            "detail": "no root evidence was supplied for this occurrence",
            "gates": [_cite(PLURAL_GATE, template_id)],
        }
    if not attested_pair:
        return {
            "decision": "abstain",
            "defeater": "no_attested_lexeme_pair",
            "detail": (
                "an observed broken plural needs root evidence AND an exact lemma/"
                "entry plural-form link; shape resemblance alone never certifies"
            ),
            "gates": [_cite(PLURAL_GATE, template_id)],
        }
    if pattern.get("rarity") in ("rare", "second_order") and not rare_license_ok:
        return {
            "decision": "abstain",
            "defeater": "rare_plural_unlicensed",
            "detail": (
                "template %s is %s and this lexeme is outside its closed "
                "licensed_lexemes list" % (template_id, pattern.get("rarity"))
            ),
            "gates": [_cite(PLURAL_GATE, template_id)],
        }
    if pattern.get("requires_attested_base") and not plural_of_plural_base_attested:
        return {
            "decision": "abstain",
            "defeater": "plural_of_plural_base_unattested",
            "detail": (
                "template %s is a plural-of-plural; its BASE plural must itself be "
                "an attested form, not merely the observed surface" % template_id
            ),
            "gates": [_cite(PLURAL_GATE, template_id)],
        }
    return {
        "decision": "emit",
        "defeater": None,
        "detail": "attested lexeme pair, template kind, and license/base checks all pass",
        "gates": [_cite(PLURAL_GATE, template_id)],
    }


def lexical_gender_gate(
    gender_registry_entry: str | None,
    rules_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Decide emit vs abstain for asserting a noun's lexical gender.

    Gender is asserted ONLY from an explicit registry/entry fact — never from
    the presence or absence of tā' marbūṭa (plural-gender-rules.json
    #projector_contract:lexical-gender-registry-only). شَجَرَة (has ة) and
    شَمْس (has none) both require the SAME gate.
    """
    if gender_registry_entry not in ("masculine", "feminine"):
        return {
            "decision": "abstain",
            "defeater": "lexical_gender_registry_missing",
            "detail": (
                "gender must come from an explicit registry/entry fact, never "
                "inferred from ta marbuta presence or absence"
            ),
            "gates": [],
        }
    return {
        "decision": "emit",
        "defeater": None,
        "detail": "gender read from the explicit registry/entry fact",
        "gates": [_cite(PLURAL_GATE, "lexical-gender-registry-only")],
    }


def _self_test() -> None:
    hollow = slot_gate("ق و ل", "I", "present_active")
    assert hollow["decision"] == "abstain", hollow
    hamza = slot_gate("ء م ن", "I", "present_active")
    assert hamza["decision"] == "abstain", hamza
    masdar_i = slot_gate("ك ت ب", "I", "masdar")
    assert masdar_i["decision"] == "abstain", masdar_i
    sound = slot_gate("ك ت ب", "IV", "present_active")
    assert sound["decision"] == "emit", sound
    assert all("#" in g for g in sound["gates"])
    assert strict_key_collision("نَزَّلَ", ["نَزَلَ"]) is True
    assert strict_key_collision("كَتَبَ", ["ضَرَبَ"]) is False
    assert plural_gate("ق ل م", "taksir-afal")["decision"] == "emit"
    assert plural_gate("ق و ل", "taksir-afal")["decision"] == "abstain"
    try:
        _cite(VERB_MEASURES, "does-not-exist")
    except GateError:
        pass
    else:  # pragma: no cover
        raise AssertionError("unknown rule id did not fail closed")
    print("RM-40 gate stack self-test OK")


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
