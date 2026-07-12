#!/usr/bin/env python3
"""RM-40 generated-form evaluation harness (offline; RM-38 structure reuse).

Evaluates the ONE new thing RM-40 adds: the precision/recall of *generated*
surfaces against a gold surface inventory, per paradigm slot-type. It reuses the
RM-38 discipline — the ``norm_strict`` (hamza-seat-preserving) join, hash-pinned
user-local data, abstention accounting, and the no-collapsed-score guard.

* ``--self-test`` runs on the committed synthetic fixtures only (no corpora);
  real gold-set runs wait for the pinned QuranMorph/EQTB corpora.
* Primary metric is per-slot **generated-form precision** (the fabrication rate's
  complement); recall is secondary and expected low (under-claim by design).
* **Fabrication** = a surface the generator emitted for a lemma with NO gold
  surface anywhere — counted separately from a recall miss, with a hard budget.
* No aggregate/headline score is ever produced (RM-38 §4).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import normalize_ar
from tools.rm38.validate import validate_no_collapsed_score

FIXTURES = ROOT / "fusha" / "morphology" / "fixtures"
GOLD_FIXTURE = FIXTURES / "rm40-eval-gold.jsonl"
EMITTED_FIXTURE = FIXTURES / "rm40-eval-emitted.jsonl"
MANIFEST = ROOT / "eval" / "rm40" / "data-manifest.json"
MODEL_CARD = ROOT / "eval" / "rm40" / "model-card.rm40.json"
MODEL_CARD_CLAIM = (
    "RM-40 paradigm-generated candidates; precision/recall vs QuranMorph+EQTB surfaces; "
    "per-slot; no aggregate; fabrication-budget=0; candidates-never-facts; QAC consult-only"
)


class FixtureError(ValueError):
    """A synthetic fixture is absent, unpinned, or tampered."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_fixture(path: Path, pin: Dict[str, Any]) -> str:
    expected = str(pin.get("sha256", "")).lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise FixtureError("invalid or missing sha256 pin for %s" % path)
    if not Path(path).is_file():
        raise FixtureError("fixture path is not a file: %s" % path)
    digest = sha256_file(path)
    if digest != expected:
        raise FixtureError("sha256 mismatch for %s: expected %s, got %s" % (path, expected, digest))
    return digest


def surface_matches(surface: str, gold_surfaces: Iterable[str]) -> bool:
    """Join on the strict key (keeps the hamza seat) — إيمان never matches أيمان."""
    key = normalize_ar.norm_strict(surface)
    return any(normalize_ar.norm_strict(g) == key for g in gold_surfaces)


def _ratio(numerator: int, denominator: int) -> Dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 6) if denominator else None,
    }


def evaluate_slot(
    *,
    emitted: List[Dict[str, Any]],
    abstained: List[Dict[str, Any]],
    gold_by_lemma: Dict[str, List[str]],
    slot_type: str,
) -> Dict[str, Any]:
    """Per-slot honesty block: precision, recall, fabrication, abstention.

    ``emitted`` rows are ``{lemma, surface}``; ``abstained`` rows are ``{lemma}``.
    Precision denominator is emitted-for-a-lemma-with-gold; a surface whose lemma
    has no gold inventory at all is a **fabrication**, not a recall miss.
    """
    matched = 0
    precision_denominator = 0
    fabrication = 0
    for row in emitted:
        lemma = str(row.get("lemma"))
        gold = gold_by_lemma.get(lemma)
        if not gold:
            fabrication += 1
            continue
        precision_denominator += 1
        if surface_matches(str(row.get("surface", "")), gold):
            matched += 1
    emitted_lemmas = {str(row.get("lemma")) for row in emitted}
    gold_surface_total = sum(len(v) for k, v in gold_by_lemma.items() if k in emitted_lemmas)
    recalled = 0
    for lemma in emitted_lemmas:
        for gold_surface in gold_by_lemma.get(lemma, []):
            if any(
                str(r.get("lemma")) == lemma and surface_matches(str(r.get("surface", "")), [gold_surface])
                for r in emitted
            ):
                recalled += 1
    return {
        "slot_type": slot_type,
        "emitted": len(emitted),
        "abstained": len(abstained),
        "precision": _ratio(matched, precision_denominator),
        "recall": _ratio(recalled, gold_surface_total),
        "fabrication_count": fabrication,
        "abstention": _ratio(len(abstained), len(emitted) + len(abstained)),
        "denominator_definition": "emitted surfaces for a lemma with a gold inventory; fabrications excluded from precision",
    }


def build_report(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    report = {
        "schema": "qamus.rm40_generation_eval.v1",
        "claim": MODEL_CARD_CLAIM,
        "per_slot": list(blocks),
        "fabrication_budget": 0,
        "join": "norm_strict",
    }
    validate_no_collapsed_score(report)
    return report


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _self_test() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pins = manifest.get("fixtures") or {}
    for name, path in (("gold", GOLD_FIXTURE), ("emitted", EMITTED_FIXTURE)):
        if name not in pins:
            raise FixtureError("manifest missing pin for %s" % name)
        verify_fixture(path, pins[name])

    if json.loads(MODEL_CARD.read_text(encoding="utf-8")).get("claim") != MODEL_CARD_CLAIM:
        raise FixtureError("model-card claim boundary drifted")

    gold_rows = _read_jsonl(GOLD_FIXTURE)
    gold_by_lemma = {str(r["lemma"]): list(r.get("surfaces") or []) for r in gold_rows}
    emitted_rows = _read_jsonl(EMITTED_FIXTURE)
    by_slot: Dict[str, List[Dict[str, Any]]] = {}
    for row in emitted_rows:
        by_slot.setdefault(str(row.get("slot_type", "present_active")), []).append(row)

    blocks = [
        evaluate_slot(emitted=rows, abstained=[], gold_by_lemma=gold_by_lemma, slot_type=slot)
        for slot, rows in sorted(by_slot.items())
    ]
    report = build_report(blocks)

    # Fabrication must be detected, not laundered into recall.
    fab = evaluate_slot(
        emitted=[{"lemma": "lex-nogold", "surface": "زَقَّمَ"}],
        abstained=[],
        gold_by_lemma={"lex-y": ["كَتَبَ"]},
        slot_type="present_active",
    )
    if fab["fabrication_count"] != 1 or fab["precision"]["denominator"] != 0:
        raise FixtureError("fabrication accounting drifted")

    # norm_strict join keeps the hamza seat.
    if surface_matches("إِيمَان", ["أَيْمَان"]):
        raise FixtureError("strict join wrongly merged hamza-seat variants")

    # Tampered pin must be refused.
    try:
        verify_fixture(GOLD_FIXTURE, {"sha256": "0" * 64})
    except FixtureError:
        pass
    else:  # pragma: no cover
        raise FixtureError("tamper guard did not fire")

    if not report["per_slot"]:
        raise FixtureError("no per-slot report produced")
    print("RM-40 evaluation harness self-test OK")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            _self_test()
            return 0
        parser.error("--self-test is required (real gold-set runs await pinned corpora)")
        return 2
    except (OSError, ValueError, FixtureError, json.JSONDecodeError) as exc:
        print("RM-40 evaluation refused: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
