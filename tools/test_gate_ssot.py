#!/usr/bin/env python3
"""Mutation-prove grammar trigger SSOT parity and grammar-topic routing."""

from __future__ import annotations

import ast
import collections
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import run_grammar_evals  # noqa: E402


DEFAULT_HOMES = {
    "ssot": ROOT / "nahw" / "evals" / "grammar-decision-gates.json",
    "two_vote_rules": ROOT / "nahw" / "rules" / "two-vote-required-rules.json",
    "decisions_validator": ROOT / "tools" / "validate_linguistic_decisions.py",
    "regression_harness": ROOT / "tools" / "check_regressions.py",
}
TIERS = (
    "two_vote_required",
    "human_source_review_required",
    "never_auto_resolve",
)
JSON_RULE_KEYS = {
    "two_vote_required": "two_vote_triggers",
    "human_source_review_required": "human_review_triggers",
    "never_auto_resolve": "never_auto_triggers",
}


def _python_trigger_lists(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "GRAMMAR_GATE_TRIGGERS"
                   for target in node.targets):
                value = ast.literal_eval(node.value)
                return {tier: list(value[tier]) for tier in TIERS}
    raise AssertionError(f"{path}: missing GRAMMAR_GATE_TRIGGERS verified copy")


def load_four_homes(homes: dict[str, Path] | None = None) -> dict[str, dict[str, list[str]]]:
    homes = homes or DEFAULT_HOMES
    ssot = json.loads(homes["ssot"].read_text(encoding="utf-8"))
    rules = json.loads(homes["two_vote_rules"].read_text(encoding="utf-8"))
    if rules.get("trigger_source") != "../evals/grammar-decision-gates.json":
        raise AssertionError("two_vote_rules missing verified-copy trigger_source")
    return {
        "ssot": {tier: list(ssot["gates"][tier]["trigger_when_ANY"]) for tier in TIERS},
        "two_vote_rules": {tier: list(rules[JSON_RULE_KEYS[tier]]) for tier in TIERS},
        "decisions_validator": _python_trigger_lists(homes["decisions_validator"]),
        "regression_harness": _python_trigger_lists(homes["regression_harness"]),
    }


def assert_four_way_trigger_equality(homes: dict[str, Path] | None = None) -> None:
    copies = load_four_homes(homes)
    fingerprints = {
        home: json.dumps(triggers, ensure_ascii=False, separators=(",", ":"))
        for home, triggers in copies.items()
    }
    counts = collections.Counter(fingerprints.values())
    if len(counts) != 1:
        majority, _ = counts.most_common(1)[0]
        drifted = [home for home, fingerprint in fingerprints.items() if fingerprint != majority]
        raise AssertionError(
            f"{', '.join(drifted)} trigger-list drift from grammar-decision-gates.json"
        )


def _strict_case(topic: str, gate: str) -> dict[str, str]:
    return {
        "id": f"RM27-{topic}",
        "level": "qatr_al_nada",
        "bloom": "analysis",
        "format": "objective",
        "depth": "deep",
        "topic": topic,
        "question_ar": "سؤال اختباري",
        "question_en": "Synthetic gate-routing probe",
        "expected_answer": "answer",
        "expected_reasoning": "reason",
        "hover_safety": gate,
        "required_gate": gate,
    }


class GateSsotTests(unittest.TestCase):
    def test_all_four_trigger_homes_equal_ssot_lists(self) -> None:
        assert_four_way_trigger_equality()

    def _assert_home_mutation_is_caught(self, name: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            homes = {}
            for home, source in DEFAULT_HOMES.items():
                target = temp_root / source.name
                shutil.copyfile(source, target)
                homes[home] = target

            target = temp_root / f"{name}-{homes[name].name}"
            shutil.copyfile(homes[name], target)
            text = target.read_text(encoding="utf-8")
            text = text.replace('"advanced_nahw"', '"advanced_nahw_mutated"', 1)
            target.write_text(text, encoding="utf-8")
            homes[name] = target
            with self.assertRaisesRegex(AssertionError, name):
                assert_four_way_trigger_equality(homes)

    def test_ssot_trigger_mutation_is_caught(self) -> None:
        self._assert_home_mutation_is_caught("ssot")

    def test_two_vote_rules_trigger_mutation_is_caught(self) -> None:
        self._assert_home_mutation_is_caught("two_vote_rules")

    def test_decisions_validator_trigger_mutation_is_caught(self) -> None:
        self._assert_home_mutation_is_caught("decisions_validator")

    def test_regression_harness_trigger_mutation_is_caught(self) -> None:
        self._assert_home_mutation_is_caught("regression_harness")

    def test_previously_omitted_topics_reject_auto_safe_and_accept_routed(self) -> None:
        for topic in ("negation_mood", "ism_fail_ism_maful_operation"):
            with self.subTest(topic=topic, route="auto_safe"):
                errors = run_grammar_evals.topic_gate_errors([_strict_case(topic, "auto_safe")])
                self.assertTrue(any(topic in error and "requires >= two_vote" in error
                                    for error in errors), errors)
            with self.subTest(topic=topic, route="two_vote_required"):
                self.assertEqual(
                    [],
                    run_grammar_evals.topic_gate_errors(
                        [_strict_case(topic, "two_vote_required")]
                    ),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
