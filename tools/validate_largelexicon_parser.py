#!/usr/bin/env python3
"""Validate parser consumption of the largelexicon sample layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_standalone_parse import parse_text
from largelexicon_common import LEXICON_DIR, read_jsonl


SAMPLE = LEXICON_DIR / "lemma-source.sample.jsonl"
COLLISION_FIXTURES = Path(__file__).resolve().parents[1] / "fusha" / "parser" / "eval" / "largelexicon-collision-regressions.jsonl"


def _token(parsed: dict, index: int) -> dict:
    tokens = parsed.get("tokens") or []
    if index >= len(tokens):
        raise AssertionError(f"missing token index {index}")
    return tokens[index]


def _top(token: dict) -> dict:
    return (token.get("morphology_candidates") or [{}])[0]


def _parse_key(token: dict) -> str:
    return (((token.get("selected_preview") or {}).get("parse_key") or {}).get("key") or "")


def _hover_text(token: dict) -> str:
    hover = token.get("hover_preview") or {}
    fields = ("token_contribution_gloss", "morphline", "learner_explanation")
    return " ".join(str(hover.get(key) or "") for key in fields)


def _qg_roles(token: dict) -> set[str]:
    return {str(seg.get("role") or "") for seg in token.get("qg_segments") or []}


def _matches_forbidden(token: dict, rule: dict) -> bool:
    top = _top(token)
    if "pos" in rule and top.get("pos") != rule["pos"]:
        return False
    if "lemma" in rule and top.get("lemma") != rule["lemma"]:
        return False
    if "parse_key" in rule and _parse_key(token) != rule["parse_key"]:
        return False
    if "role" in rule and rule["role"] not in _qg_roles(token):
        return False
    if "hover_contains" in rule and rule["hover_contains"] not in _hover_text(token):
        return False
    return True


def _matches_allowed_top(token: dict, rule: dict) -> bool:
    top = _top(token)
    if "pos" in rule and top.get("pos") != rule["pos"]:
        return False
    if "lemma" in rule and top.get("lemma") != rule["lemma"]:
        return False
    if "lemma_contains" in rule and rule["lemma_contains"] not in str(top.get("lemma") or ""):
        return False
    return True


def _validate_collision_fixtures(errors: list[str]) -> None:
    if not COLLISION_FIXTURES.exists():
        errors.append("missing largelexicon collision regression fixtures")
        return
    for row in read_jsonl(COLLISION_FIXTURES):
        fixture_id = row.get("id") or "unknown-fixture"
        parsed = parse_text(row["text"], document_id=fixture_id, db="largelexicon")
        try:
            token = _token(parsed, int(row["target_token_index"]))
        except AssertionError as exc:
            errors.append(f"{fixture_id}: {exc}")
            continue
        if token.get("surface") != row.get("surface"):
            errors.append(f"{fixture_id}: expected surface {row.get('surface')!r}, got {token.get('surface')!r}")
        required = row.get("required_behavior") or {}
        allowed = required.get("allowed_top") or []
        if allowed and not any(_matches_allowed_top(token, rule) for rule in allowed):
            gate = token.get("confidence_gate")
            if gate not in set(required.get("or_gate") or []):
                errors.append(f"{fixture_id}: top candidate {json.dumps(_top(token), ensure_ascii=False)} not allowed and gate {gate!r} not accepted")
        if token.get("confidence_gate") not in set(required.get("or_gate") or [token.get("confidence_gate")]):
            errors.append(f"{fixture_id}: unexpected confidence_gate {token.get('confidence_gate')!r}")
        roles = _qg_roles(token)
        for role in required.get("required_roles") or []:
            if role not in roles:
                errors.append(f"{fixture_id}: missing required qg role {role!r}; got {sorted(roles)}")
        for role in required.get("forbidden_roles") or []:
            if role in roles:
                errors.append(f"{fixture_id}: forbidden qg role {role!r} projected")
        if required.get("hover_projection_must_not_use_forbidden_top"):
            for rule in row.get("forbidden_top") or []:
                if _matches_forbidden(token, rule):
                    errors.append(f"{fixture_id}: forbidden projection survived: {rule}")


def validate() -> list[str]:
    errors: list[str] = []
    if not SAMPLE.exists():
        return ["missing largelexicon lemma sample"]
    rows = read_jsonl(SAMPLE)
    probes = []
    for row in rows:
        forms = row.get("forms") or []
        forms = [form for form in forms if form and " " not in form.strip()]
        if row.get("root") and forms:
            probes.append((forms[0], row["entry_id"]))
        if len(probes) >= 8:
            break
    if len(probes) < 5:
        errors.append("need at least five rooted parser probes from largelexicon sample")
    for surface, entry_id in probes:
        parsed = parse_text(surface, document_id=f"largelexicon:{entry_id}", db="largelexicon")
        tokens = parsed.get("tokens") or []
        if len(tokens) != 1:
            errors.append(f"{surface}: expected one token parse")
            continue
        top = (tokens[0].get("morphology_candidates") or [{}])[0]
        if top.get("evidence_class") not in {"seed_lexicon", "largelexicon_sample", "largelexicon_full", "pinned_pattern"}:
            errors.append(f"{surface}: unexpected evidence_class {top.get('evidence_class')!r}")
        if parsed.get("summary", {}).get("live_writes") != 0:
            errors.append(f"{surface}: parser must report zero live_writes")
        if parsed.get("db") != "largelexicon":
            errors.append(f"{surface}: parser must preserve db=largelexicon")
    cluster = parse_text("إنما", document_id="largelexicon:function-cluster", db="largelexicon")
    qg = ((cluster.get("tokens") or [{}])[0].get("qg_segments") or [])
    roles = [seg.get("role") for seg in qg]
    if "particle_inna" not in roles or "ma_particle" not in roles:
        errors.append("إنما must preserve particle_inna + ma_particle segments under largelexicon")
    _validate_collision_fixtures(errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate largelexicon parser sample consumption.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate()
    print(json.dumps({"ok": not errors, "errors": errors, "self_test": bool(args.self_test)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
