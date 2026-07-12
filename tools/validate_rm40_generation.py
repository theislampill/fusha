#!/usr/bin/env python3
"""RM-40 generated-candidate validator (stdlib only, fail-closed).

Enforces the candidates-never-facts invariants and the plane-disjointness
firewall between generated candidates and the sourced lookup/evidence baseline:

* schema conformance against ``paradigm-generated-candidate.schema.json``;
* ``certification_state == candidate``, ``generation_used is True``,
  ``source == paradigm_generated``, ``supersedes is None``, non-empty
  ``provenance.rule_chain`` naming the paradigm + gates;
* plane pollution — a row marked ``qamus_current_authored`` that also carries
  ``generation_used`` (or vice versa) fails closed;
* the committed baseline stem table contains ZERO generated markers, and its
  allowlist entry declares ``table_role: lookup_evidence_baseline``;
* no generated (lemma, slot) may equal a documented baseline form (no-overwrite);
* committed generation artifacts contain no corpus/source prose (leak scanner).

``--self-test`` runs entirely on synthetic fixtures; no user data required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fact_ledger
from tools import leak_sot
from tools import normalize_ar

SCHEMA_PATH = ROOT / "qamus" / "schemas" / "paradigm-generated-candidate.schema.json"
BASELINE_FULL = ROOT / "fusha" / "morphology" / "data" / "largelexicon-stems.full.jsonl"
ALLOWLIST = ROOT / "fusha" / "lexicon" / "largelexicon" / "source-clean-table-allowlist.json"
FIXTURES = ROOT / "fusha" / "morphology" / "fixtures"
GENERATED_SAMPLE = ROOT / "fusha" / "morphology" / "data" / "generated-candidates.sample.jsonl"
GENERATED_MARKERS = {"paradigm_generated"}


class GenerationValidationError(ValueError):
    """Raised when a generated candidate or its plane guarantees fail closed."""


def _load_schema() -> Dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_schema(row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    schema = _load_schema()
    fact_ledger._validate_node(row, schema, "$", errors, schema)
    return errors


def validate_invariants(row: Dict[str, Any]) -> List[str]:
    """Structural + candidates-never-facts invariants (does not touch disk)."""
    errors: List[str] = []
    if row.get("certification_state") != "candidate":
        errors.append("certification_state must be 'candidate'")
    if row.get("generation_used") is not True:
        errors.append("generation_used must be exactly true")
    if row.get("source") != "paradigm_generated":
        errors.append("source must be 'paradigm_generated', never a sourced-baseline marker")
    if row.get("supersedes") is not None:
        errors.append("supersedes must be null; a generated row may never supersede a sourced fact")
    provenance = row.get("provenance") or {}
    chain = provenance.get("rule_chain")
    if not isinstance(chain, list) or not chain or not all(isinstance(x, str) and x for x in chain):
        errors.append("provenance.rule_chain must be a non-empty list naming the paradigm + gates")
    if provenance.get("actor") != "sarf.paradigm_generated.v1":
        errors.append("provenance.actor must be the RM-40 generator id")
    if not provenance.get("paradigm_id"):
        errors.append("provenance.paradigm_id is required")
    return errors


def check_plane_pollution(row: Dict[str, Any]) -> bool:
    """True when a row mixes the two planes (a fail-closed condition).

    A generated marker with a sourced-baseline ``source`` — or a sourced marker
    carrying ``generation_used`` — is plane pollution.
    """
    generation_used = bool(row.get("generation_used"))
    source = row.get("source")
    if generation_used and source != "paradigm_generated":
        return True
    if source == "qamus_current_authored" and generation_used:
        return True
    return False


def validate_row(row: Dict[str, Any]) -> List[str]:
    errors = validate_schema(row)
    errors += validate_invariants(row)
    if check_plane_pollution(row):
        errors.append("plane pollution: sourced/generated markers mixed on one row")
    return errors


def check_baseline_disjoint(baseline_path: Path = BASELINE_FULL, allowlist_path: Path = ALLOWLIST) -> List[str]:
    """The sourced baseline must carry zero generated markers and declare its role."""
    errors: List[str] = []
    path = Path(baseline_path)
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                if obj.get("generation_used") is not None:
                    errors.append("baseline row %d carries a generation_used marker" % number)
                if obj.get("source") in GENERATED_MARKERS:
                    errors.append("baseline row %d carries a generated source marker" % number)
    allow = json.loads(Path(allowlist_path).read_text(encoding="utf-8"))
    stem = [t for t in allow.get("tables") or [] if str(t.get("path", "")).endswith("largelexicon-stems.full.jsonl")]
    if not stem:
        errors.append("allowlist has no largelexicon-stems.full.jsonl entry")
    elif stem[0].get("table_role") != "lookup_evidence_baseline":
        errors.append("baseline allowlist entry must declare table_role=lookup_evidence_baseline")
    return errors


def check_no_overwrite(generated_rows: Iterable[Dict[str, Any]], baseline_forms: Iterable[Dict[str, Any]]) -> List[str]:
    """No generated (lemma, slot) surface may equal a documented baseline form."""
    errors: List[str] = []
    index: Dict[tuple, set] = {}
    for form in baseline_forms or []:
        key = (str(form.get("lemma")), form.get("slot"))
        index.setdefault(key, set()).add(normalize_ar.norm_strict(str(form.get("surface", ""))))
    for row in generated_rows:
        subject = row.get("subject") or {}
        lemma, slot = str(subject.get("lemma")), subject.get("slot")
        surfaces = {row.get("value", {}).get("surface_norm_strict")}
        surfaces |= {alt.get("surface_norm_strict") for alt in row.get("competing_alternatives") or []}
        baseline_surfaces = index.get((lemma, slot), set()) | index.get((lemma, None), set())
        if surfaces & baseline_surfaces:
            errors.append("generated %s/%s overwrites a documented baseline form" % (lemma, slot))
    return errors


def check_no_corpus(paths: Iterable[Path]) -> List[str]:
    """Committed generation artifacts must contain no source/corpus prose."""
    errors: List[str] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        hits = leak_sot.scan(text)
        if hits:
            errors.append("%s trips the source-leak scanner: %s" % (path.name, ",".join(hits)))
    return errors


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _self_test() -> None:
    fixture = FIXTURES / "rm40-generated-candidates.jsonl"
    rows = _read_jsonl(fixture)
    if not rows:
        raise GenerationValidationError("generated-candidate fixture is empty")
    for row in rows:
        errors = validate_row(row)
        if errors:
            raise GenerationValidationError("valid fixture rejected: " + "; ".join(errors))

    # A row with supersedes set must fail closed.
    bad = dict(rows[0])
    bad["supersedes"] = "sha256:" + "a" * 64
    if not validate_invariants(bad):
        raise GenerationValidationError("supersedes guard did not fire")

    # Plane pollution must fail closed.
    polluted = dict(rows[0])
    polluted["source"] = "qamus_current_authored"
    if not check_plane_pollution(polluted):
        raise GenerationValidationError("plane-pollution guard did not fire")

    # The committed baseline must be disjoint and role-declared.
    baseline_errors = check_baseline_disjoint()
    if baseline_errors:
        raise GenerationValidationError("baseline disjointness failed: " + "; ".join(baseline_errors))

    # No-overwrite: a generated surface equal to a documented baseline form fails.
    first = rows[0]
    faux_baseline = [{
        "lemma": first["subject"]["lemma"],
        "slot": first["subject"]["slot"],
        "surface": first["value"]["generated_surface"],
    }]
    if not check_no_overwrite([first], faux_baseline):
        raise GenerationValidationError("no-overwrite guard did not fire")

    # No corpus prose in any committed generation artifact.
    corpus_errors = check_no_corpus([GENERATED_SAMPLE, fixture])
    if corpus_errors:
        raise GenerationValidationError("; ".join(corpus_errors))

    print("RM-40 generation validator self-test OK")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            _self_test()
            return 0
        errors = check_baseline_disjoint() + check_no_corpus([GENERATED_SAMPLE, FIXTURES / "rm40-generated-candidates.jsonl"])
        if errors:
            for error in errors:
                print("ERROR " + error, file=sys.stderr)
            return 1
        print("RM-40 generation validation OK")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("RM-40 generation validation failed: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
