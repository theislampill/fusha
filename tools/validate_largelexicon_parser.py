#!/usr/bin/env python3
"""Validate parser consumption of the largelexicon sample layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_largelexicon_cli import _token_safety
from fusha_standalone_parse import parse_text
from largelexicon_common import LEXICON_DIR, read_jsonl


SAMPLE = LEXICON_DIR / "lemma-source.sample.jsonl"
FORM_TABLE = LEXICON_DIR / "form-source.full.jsonl"
COLLISION_FIXTURES = Path(__file__).resolve().parents[1] / "fusha" / "parser" / "eval" / "largelexicon-collision-regressions.jsonl"
POS_TRICHOTOMY = {"noun": "ism", "proper_noun": "ism", "verb": "fil", "particle": "harf"}


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


def _hover_gloss(token: dict) -> object:
    return (token.get("hover_preview") or {}).get("token_contribution_gloss")


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
        top = _top(token)
        features = top.get("features") or {}
        collision = token.get("collision") or {}
        gate = token.get("confidence_gate")
        allowed = required.get("allowed_top") or []
        if allowed and not any(_matches_allowed_top(token, rule) for rule in allowed):
            if gate not in set(required.get("or_gate") or []):
                errors.append(f"{fixture_id}: top candidate {json.dumps(top, ensure_ascii=False)} not allowed and gate {gate!r} not accepted")
        if "or_gate" in required and gate not in set(required["or_gate"]):
            errors.append(f"{fixture_id}: unexpected confidence_gate {gate!r}, expected one of {required['or_gate']}")
        if gate in set(required.get("forbid_confidence_gate") or []):
            errors.append(f"{fixture_id}: forbidden confidence_gate {gate!r} was reached")
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
        if required.get("forbid_hover_gloss") and _hover_gloss(token):
            errors.append(f"{fixture_id}: hover gloss must be withheld, got {_hover_gloss(token)!r}")
        if "require_collision_kind" in required and collision.get("kind") != required["require_collision_kind"]:
            errors.append(f"{fixture_id}: expected collision_kind {required['require_collision_kind']!r}, got {collision.get('kind')!r}")
        if "require_collision_scope" in required and collision.get("scope") != required["require_collision_scope"]:
            errors.append(f"{fixture_id}: expected collision_scope {required['require_collision_scope']!r}, got {collision.get('scope')!r}")
        if "require_competitor_entry_ids_min" in required:
            ids = collision.get("competing_entry_ids") or []
            if len(ids) < required["require_competitor_entry_ids_min"]:
                errors.append(f"{fixture_id}: expected >= {required['require_competitor_entry_ids_min']} competing_entry_ids, got {len(ids)}")
        for key, value in (required.get("require_features") or {}).items():
            if features.get(key) != value:
                errors.append(f"{fixture_id}: expected features.{key} == {value!r}, got {features.get(key)!r}")
        for key in required.get("forbid_features") or []:
            if features.get(key):
                errors.append(f"{fixture_id}: forbidden feature {key!r} present with value {features.get(key)!r}")
        for key, value in (required.get("require_top") or {}).items():
            if top.get(key) != value:
                errors.append(f"{fixture_id}: expected top.{key} == {value!r}, got {top.get(key)!r}")
        if "require_source_risk_flags" in required:
            have = set(features.get("source_risk_flags") or [])
            need = set(required["require_source_risk_flags"])
            if not need.issubset(have):
                errors.append(f"{fixture_id}: expected source_risk_flags {sorted(need)} subset of {sorted(have)}")
        if "require_risk" in required and features.get("match_risk") != required["require_risk"]:
            errors.append(f"{fixture_id}: expected match_risk {required['require_risk']!r}, got {features.get('match_risk')!r}")
        if "require_route" in required:
            routes = _token_safety(parsed).get("routes") or []
            if required["require_route"] not in routes:
                errors.append(f"{fixture_id}: expected route {required['require_route']!r} in {routes}")


def _validate_match_basis_never_norm(errors: list[str]) -> None:
    import inspect

    from fusha_pattern_engine import _match_basis

    source = inspect.getsource(_match_basis)
    if "N.norm(" in source or ".norm(" in source.replace("norm_strict", ""):
        errors.append("cu-hamza-seat-selection: _match_basis must never call norm(), only norm_strict/bare")


def _validate_trichotomy_conflict_corpus_invariant(errors: list[str]) -> None:
    """No form in a pos_trichotomy_conflict may be projected with a non-null lemma/root/pos."""
    if not FORM_TABLE.exists():
        return
    by_key: dict[str, dict[str, dict]] = {}
    for row in read_jsonl(FORM_TABLE):
        surface = row.get("surface")
        entry_id = row.get("entry_id")
        if not surface or not entry_id:
            continue
        key = surface
        by_key.setdefault(key, {})[entry_id] = row
    checked = 0
    for surface, entries in by_key.items():
        if checked >= 40:
            break
        if len(entries) < 2:
            continue
        classes = {POS_TRICHOTOMY.get(r.get("pos")) for r in entries.values()}
        classes.discard(None)
        if len(classes) < 2:
            continue
        checked += 1
        parsed = parse_text(surface, document_id=f"trichotomy-invariant:{surface}", db="largelexicon")
        tokens = parsed.get("tokens") or []
        if len(tokens) != 1:
            continue
        top = (tokens[0].get("morphology_candidates") or [{}])[0]
        collision = tokens[0].get("collision") or {}
        if collision.get("kind") != "pos_trichotomy_conflict":
            continue
        if top.get("lemma") is not None or top.get("root") is not None or top.get("pos") is not None:
            errors.append(
                f"corpus invariant: {surface!r} is pos_trichotomy_conflict but top candidate still carries "
                f"lemma={top.get('lemma')!r} root={top.get('root')!r} pos={top.get('pos')!r}"
            )


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
    _validate_match_basis_never_norm(errors)
    _validate_trichotomy_conflict_corpus_invariant(errors)
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
