#!/usr/bin/env python3
"""Validate parser consumption of the largelexicon sample layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_clitic_splitter import split_clitics
from fusha_largelexicon_cli import _token_safety
from fusha_pattern_engine import FUNCTION_WORDS
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


def _trichotomy_conflict_candidates(rows: list[dict]) -> list[tuple[str, str]]:
    """Corpus-defined antecedent: surfaces with >= 2 entries spanning >= 2 trichotomy classes.

    Grouped by `surface_norm_strict` (falling back to the raw surface), matching the
    same key `_lexicon_match` uses to compute competitors -- grouping by the exact
    diacritized `surface` string under-counts entries that differ only in harakah and
    silently drops real corpus conflicts (Train E B2). Selection of both the group key
    and its representative surface is deterministic (sorted), never insertion-order or
    file-order dependent.
    """
    by_key: dict[str, dict[str, dict]] = {}
    for row in rows:
        surface = row.get("surface")
        entry_id = row.get("entry_id")
        if not surface or not entry_id or " " in surface.strip():
            continue
        key = row.get("surface_norm_strict") or surface
        by_key.setdefault(key, {})[entry_id] = row
    candidates = []
    for key, entries in by_key.items():
        if len(entries) < 2:
            continue
        classes = {POS_TRICHOTOMY.get(r.get("pos")) for r in entries.values()}
        classes.discard(None)
        if len(classes) < 2:
            continue
        representative = min(entries.items(), key=lambda item: (item[0], item[1].get("surface") or ""))[1]
        candidates.append((key, representative.get("surface")))
    candidates.sort(key=lambda item: item[0])
    return candidates


def _check_trichotomy_invariant_rows(rows: list[dict], parse_fn, max_checked: int = 40) -> list[str]:
    """For every deterministically selected corpus-defined conflict surface, require
    EITHER the parser exposes `pos_trichotomy_conflict` OR its top candidate carries a
    null lemma/root/pos. Under-firing (the parser silently failing to detect a real
    corpus conflict) is a reported failure, never a skipped/passed row (Train E B2)."""
    errors: list[str] = []
    checked = 0
    for key, surface in _trichotomy_conflict_candidates(rows):
        if checked >= max_checked:
            break
        checked += 1
        parsed = parse_fn(surface, key)
        tokens = parsed.get("tokens") or []
        if len(tokens) != 1:
            errors.append(
                f"corpus invariant: {surface!r} (key {key!r}) is a multi-entry multi-trichotomy "
                f"surface but did not parse to exactly one token (got {len(tokens)})"
            )
            continue
        top = (tokens[0].get("morphology_candidates") or [{}])[0]
        collision = tokens[0].get("collision") or {}
        if collision.get("kind") != "pos_trichotomy_conflict":
            errors.append(
                f"corpus invariant: {surface!r} (key {key!r}) is a multi-entry multi-trichotomy surface "
                f"but the parser did not expose pos_trichotomy_conflict (got collision.kind="
                f"{collision.get('kind')!r}, confidence_gate={tokens[0].get('confidence_gate')!r})"
            )
            continue
        if top.get("lemma") is not None or top.get("root") is not None or top.get("pos") is not None:
            errors.append(
                f"corpus invariant: {surface!r} is pos_trichotomy_conflict but top candidate still carries "
                f"lemma={top.get('lemma')!r} root={top.get('root')!r} pos={top.get('pos')!r}"
            )
    return errors


def _validate_trichotomy_conflict_corpus_invariant(errors: list[str]) -> None:
    """No form in a pos_trichotomy_conflict may be projected with a non-null lemma/root/pos."""
    if not FORM_TABLE.exists():
        return

    def parse_fn(surface: str, key: str) -> dict:
        return parse_text(surface, document_id=f"trichotomy-invariant:{key}", db="largelexicon")

    errors.extend(_check_trichotomy_invariant_rows(read_jsonl(FORM_TABLE), parse_fn))


def _check_function_inventory_corpus_agreement_rows(rows: list[dict], parse_fn, max_checked: int = 40) -> list[str]:
    """Train E gap 1: a `function_inventory` candidate is manufactured directly
    (never via `_candidate_from_row`), so it carries no `collision` field of its
    own. When its fixed score (6.5) outscores a sibling lexicon candidate for
    the same bare key, the production parse path must still surface a real
    corpus `pos_trichotomy_conflict` for that key -- which candidate wins
    scoring must never decide whether a corpus-defined collision is reported.
    For every corpus-defined multi-trichotomy surface whose deterministic
    `surface_norm_strict` key ALSO names a `FUNCTION_WORDS` entry, this parses
    the exact bare key text (what a learner types, not the diacritized corpus
    form) and requires `pos_trichotomy_conflict` there too; under-firing is a
    reported failure, never a skipped row.

    Scoped (like R6) to keys with exactly ONE clitic-split segmentation
    hypothesis: a key such as `لما` also has a real `ل + ما` split candidate
    tied for top score, which is a distinct, legitimate segmentation-ambiguity
    question (already exempted by `_candidate_collision`'s function-cluster
    tie handling, e.g. `إنما`/`انما`) -- not the same-stem, same-segmentation
    scoring conflict gap 1 targets. Widening this check across segmentation
    hypotheses would re-introduce exactly what R6 forbids (importing a
    different, unselected split's competitor data into the selected reading).
    """
    errors: list[str] = []
    checked = 0
    for key, surface in _trichotomy_conflict_candidates(rows):
        if key not in FUNCTION_WORDS:
            continue
        if len(split_clitics(key)) != 1:
            continue
        if checked >= max_checked:
            break
        checked += 1
        parsed = parse_fn(key)
        tokens = parsed.get("tokens") or []
        if len(tokens) != 1:
            errors.append(
                f"function-inventory corpus agreement: {key!r} (corpus form {surface!r}) did not "
                f"parse to exactly one token (got {len(tokens)})"
            )
            continue
        collision = tokens[0].get("collision") or {}
        if collision.get("kind") != "pos_trichotomy_conflict":
            errors.append(
                f"function-inventory corpus agreement: bare {key!r} shares a real corpus "
                f"pos_trichotomy_conflict with {surface!r} but the production parse path did not "
                f"expose it (got collision.kind={collision.get('kind')!r}, "
                f"confidence_gate={tokens[0].get('confidence_gate')!r}) -- the function_inventory "
                f"reading must not win scoring and hide a corpus-defined trichotomy collision"
            )
    return errors


def _validate_function_inventory_corpus_agreement(errors: list[str]) -> None:
    """The production parse path and the corpus trichotomy invariant must agree
    fail-closed: a corpus-defined noun/verb/particle collision must not become
    a gloss-bearing function-word result merely because that candidate wins
    scoring (Train E gap 1)."""
    if not FORM_TABLE.exists():
        return

    def parse_fn(key: str) -> dict:
        return parse_text(key, document_id=f"function-inventory-corpus-agreement:{key}", db="largelexicon")

    errors.extend(_check_function_inventory_corpus_agreement_rows(read_jsonl(FORM_TABLE), parse_fn))


def _self_test_function_inventory_corpus_agreement_fails_closed() -> list[str]:
    """Red-first (Train E gap 1): the agreement checker must FAIL when the
    production parse path under-fires on a corpus-defined multi-trichotomy
    surface whose key is also a function word, and must not flag a
    correctly-abstained one."""
    failures: list[str] = []
    rows = [
        {"surface": "مَنَّ", "surface_norm_strict": "من", "entry_id": "self-test-1", "pos": "verb"},
        {"surface": "مِنْ", "surface_norm_strict": "من", "entry_id": "self-test-2", "pos": "particle"},
    ]

    def under_firing_parse_fn(key: str) -> dict:
        return {
            "tokens": [
                {
                    "morphology_candidates": [{"lemma": "من", "root": None, "pos": "particle"}],
                    "collision": {},
                    "confidence_gate": "pending_context",
                }
            ]
        }

    if not _check_function_inventory_corpus_agreement_rows(rows, under_firing_parse_fn):
        failures.append(
            "function-inventory corpus agreement checker must report an error when the "
            "production parse path under-fires pos_trichotomy_conflict for a bare function-word "
            "key that shares a real corpus trichotomy conflict, not skip it silently"
        )

    def firing_parse_fn(key: str) -> dict:
        return {
            "tokens": [
                {
                    "morphology_candidates": [{"lemma": None, "root": None, "pos": None}],
                    "collision": {"kind": "pos_trichotomy_conflict"},
                    "confidence_gate": "lexical_collision_requires_context",
                }
            ]
        }

    if _check_function_inventory_corpus_agreement_rows(rows, firing_parse_fn):
        failures.append("function-inventory corpus agreement checker must not flag a correctly-abstained key")
    return failures


def _self_test_trichotomy_invariant_fails_closed() -> list[str]:
    """Red-first (Train E B2): the invariant checker must FAIL when the parser
    under-fires on a corpus-defined multi-entry multi-trichotomy surface, and must
    detect entries that share a norm_strict key under different raw diacritics --
    the two failure modes the un-repaired checker silently passed through."""
    failures: list[str] = []
    rows = [
        {"surface": "غَزَّى", "surface_norm_strict": "غزي", "entry_id": "self-test-1", "pos": "noun"},
        {"surface": "غَزِيَ", "surface_norm_strict": "غزي", "entry_id": "self-test-2", "pos": "verb"},
    ]
    if len(_trichotomy_conflict_candidates(rows)) != 1:
        failures.append(
            "trichotomy invariant candidate selection must group differently-diacritized "
            "surfaces sharing one surface_norm_strict key"
        )

    def under_firing_parse_fn(surface: str, key: str) -> dict:
        return {
            "tokens": [
                {
                    "morphology_candidates": [{"lemma": "غَزَّى", "root": "غ ز و", "pos": "noun"}],
                    "collision": {},
                    "confidence_gate": "likely_from_internal_pattern",
                }
            ]
        }

    if not _check_trichotomy_invariant_rows(rows, under_firing_parse_fn):
        failures.append(
            "trichotomy invariant checker must report an error when the parser under-fires "
            "pos_trichotomy_conflict on a corpus-defined conflict surface, not skip it silently"
        )

    def firing_parse_fn(surface: str, key: str) -> dict:
        return {
            "tokens": [
                {
                    "morphology_candidates": [{"lemma": None, "root": None, "pos": None}],
                    "collision": {"kind": "pos_trichotomy_conflict"},
                    "confidence_gate": "lexical_collision_requires_context",
                }
            ]
        }

    if _check_trichotomy_invariant_rows(rows, firing_parse_fn):
        failures.append("trichotomy invariant checker must not flag a correctly-abstained conflict surface")
    return failures


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
    errors.extend(_self_test_trichotomy_invariant_fails_closed())
    _validate_function_inventory_corpus_agreement(errors)
    errors.extend(_self_test_function_inventory_corpus_agreement_fails_closed())
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
