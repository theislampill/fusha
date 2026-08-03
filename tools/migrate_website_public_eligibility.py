#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded fail-closed migration for four legacy website samples missing
``projection.public_projection_eligible``.

Round F4a of the website-evidence fail-closed repair. Exactly four
committed ``qamus/examples/website-payloads/*.payload.json`` samples fail
the global validator's ``public_projection_eligible`` check
(``tools/validate_website_payload.py::check_evidence_resolution``) for one
reason only: they are hand-assembled, already non-authoritative
(``certification.status`` in ``candidate``/``unresolved``) samples that
predate the field and simply omit it. This tool rewrites only those four
payloads to an honest, validator-compatible posture:

- ``projection.public_projection_eligible`` becomes explicit ``false``
  (added, never toggled from an existing legal value -- there is none to
  toggle, since every target currently omits the key entirely).
- ``projection_hash`` and every ``reverse_links.occurrence_to_appearances[*]
  .projection_hash`` are recomputed together from the transformed
  projection, so the hash-fork guard (contract §5) stays green.

Every other field -- certification, unresolved, provenance, evidence_refs,
occurrence identity, exact surface, spans, entry links, and hover content
-- is byte-preserved: this migration adds one honesty flag and repropagates
its two derived hashes, nothing else.

The target set is an explicit closed manifest (filename to pinned
schema/schema_version/payload_kind/occurrence_id/artifact_id/
certification.status), never a directory scan: an unlisted payload is
never touched, and a listed payload whose identity has drifted from its
pin is refused rather than best-effort mutated. A payload already
certified, or already carrying a ``public_projection_eligible`` value other
than absent or ``false``, is refused rather than mutated -- this tool is
only for already non-authoritative samples that simply omit the field.
``quran:61:5:4`` (the frozen 1.2.0 candidate safety canary) can never
appear in the manifest.

Usage:
    python tools/migrate_website_public_eligibility.py --check
    python tools/migrate_website_public_eligibility.py --apply
    python tools/migrate_website_public_eligibility.py --self-test
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_website_payload  # noqa: E402

SAMPLES_DIR = validate_website_payload.SAMPLES_DIR

# Explicit closed target manifest: filename -> pinned identity, including the
# pinned certification.status (nested, so not a top-level envelope field but
# still part of the identity this migration refuses to drift against). No
# directory scan ever substitutes for this list, and no payload outside it
# is read or written by --check/--apply.
TARGET_MANIFEST: Dict[str, Dict[str, str]] = {
    "no_entry_link_17_78_3.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:17:78:3",
        "artifact_id": "artifact:rh:17:78:3",
        "certification_status": "candidate",
    },
    "noun_libuulatihinna_24_31_23.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:24:31:23",
        "artifact_id": "artifact:rh:24:31:23",
        "certification_status": "candidate",
    },
    "unresolved_ma_2_284_2.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:2:284:2",
        "artifact_id": "artifact:proofp:2:284:2",
        "certification_status": "unresolved",
    },
    "verb_ituni_12_59_5.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:12:59:5",
        "artifact_id": "artifact:fb1:12:59:5",
        "certification_status": "candidate",
    },
}

# The frozen 1.2.0 candidate safety canary this round must never disturb. A
# structural guarantee, re-asserted at import time and in --self-test: no
# manifest entry may ever pin this occurrence.
FROZEN_CANDIDATE_OCCURRENCE_ID = "quran:61:5:4"


class TargetShapeError(ValueError):
    """Refused rather than best-effort mutated: unknown or drifted shape."""


for _filename, _identity in TARGET_MANIFEST.items():
    if _identity["occurrence_id"] == FROZEN_CANDIDATE_OCCURRENCE_ID:
        raise TargetShapeError(
            "manifest integrity: %s pins the frozen candidate safety canary "
            "%s, which can never enter this migration's target set"
            % (_filename, FROZEN_CANDIDATE_OCCURRENCE_ID)
        )
del _filename, _identity


def _dump_canonical(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_canonical(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(_dump_canonical(payload), encoding="utf-8", newline="\n")


def _verify_identity(
    filename: str, payload: Dict[str, Any], identity: Dict[str, str]
) -> None:
    if not isinstance(payload, dict):
        raise TargetShapeError("%s: payload must be a JSON object" % filename)
    envelope_keys = (
        "schema", "schema_version", "payload_kind", "occurrence_id",
        "artifact_id",
    )
    mismatches = [
        "%s=%r (expected %r)" % (key, payload.get(key), identity[key])
        for key in envelope_keys
        if payload.get(key) != identity[key]
    ]
    projection = payload.get("projection")
    certification = (
        projection.get("certification") if isinstance(projection, dict)
        else None
    )
    actual_status = (
        certification.get("status") if isinstance(certification, dict)
        else None
    )
    if actual_status != identity["certification_status"]:
        mismatches.append(
            "projection.certification.status=%r (expected %r)"
            % (actual_status, identity["certification_status"])
        )
    occurrence_id = payload.get("occurrence_id")
    if occurrence_id == FROZEN_CANDIDATE_OCCURRENCE_ID:
        mismatches.append(
            "occurrence_id %r is the frozen candidate safety canary and can "
            "never enter this migration's target set" % occurrence_id
        )
    if mismatches:
        raise TargetShapeError(
            "%s: identity does not match the pinned target manifest (%s)"
            % (filename, "; ".join(mismatches))
        )


def transform_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fail-closed rewrite. Refuses an unrecognised shape."""

    if not isinstance(payload, dict):
        raise TargetShapeError("payload must be a JSON object")
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        raise TargetShapeError("payload.projection must be an object")
    certification = projection.get("certification")
    status = (
        certification.get("status") if isinstance(certification, dict)
        else None
    )
    if status == "certified":
        raise TargetShapeError(
            "payload.projection.certification.status is 'certified' -- "
            "this migration is only for already non-authoritative samples"
        )
    if "public_projection_eligible" in projection \
            and projection["public_projection_eligible"] is not False:
        raise TargetShapeError(
            "payload.projection.public_projection_eligible is %r -- only "
            "an absent key or explicit false may be migrated"
            % (projection["public_projection_eligible"],)
        )
    reverse = payload.get("reverse_links")
    appearances = (
        reverse.get("occurrence_to_appearances")
        if isinstance(reverse, dict)
        else None
    )
    if not isinstance(appearances, list):
        raise TargetShapeError(
            "payload.reverse_links.occurrence_to_appearances must be an "
            "array"
        )

    result = copy.deepcopy(payload)
    result_projection = result["projection"]
    result_projection["public_projection_eligible"] = False
    # certification, unresolved, evidence_refs, entry_links, segments,
    # hover_cards, root, and every other field are left exactly as
    # deep-copied: this migration adds one honesty flag only.

    new_hash = validate_website_payload.projection_hash(result_projection)
    result["projection_hash"] = new_hash
    for appearance in result["reverse_links"]["occurrence_to_appearances"]:
        if not isinstance(appearance, dict):
            raise TargetShapeError(
                "reverse_links.occurrence_to_appearances row must be an "
                "object"
            )
        appearance["projection_hash"] = new_hash
    return result


def _load_target(
    filename: str, payload_dir: Path
) -> Tuple[Dict[str, Any], bytes]:
    path = payload_dir / filename
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    _verify_identity(filename, payload, TARGET_MANIFEST[filename])
    return payload, raw


def check(payload_dir: Path = SAMPLES_DIR) -> List[str]:
    """Return the sorted list of manifest filenames not yet migrated."""

    stale = []
    for filename in TARGET_MANIFEST:
        payload, raw = _load_target(filename, payload_dir)
        expected = _dump_canonical(transform_payload(payload)).encode("utf-8")
        if raw != expected:
            stale.append(filename)
    return stale


def apply_migration(payload_dir: Path = SAMPLES_DIR) -> List[str]:
    """Rewrite every manifest target in place; return the filenames touched."""

    written = []
    for filename in TARGET_MANIFEST:
        payload, raw = _load_target(filename, payload_dir)
        transformed = transform_payload(payload)
        expected = _dump_canonical(transformed).encode("utf-8")
        if raw != expected:
            _write_canonical(payload_dir / filename, transformed)
            written.append(filename)
    return written


# --------------------------------------------------------------------------- #
# self-test -- synthetic fixtures only, never the tracked samples
# --------------------------------------------------------------------------- #

# Projection kind per manifest target, mirroring each real sample's shape
# closely enough to exercise the same validator checks (segment
# reconstruction, rootless pedagogy, entry-link discipline); self-test
# fixtures are built fresh in memory, never read from the tracked samples.
_SELF_TEST_PROJECTION_KIND: Dict[str, str] = {
    "no_entry_link_17_78_3.payload.json": "noun_word",
    "noun_libuulatihinna_24_31_23.payload.json": "noun_word",
    "unresolved_ma_2_284_2.payload.json": "particle_clitic_word",
    "verb_ituni_12_59_5.payload.json": "verb_word",
}


def _synthetic_valid_payload(filename: str) -> Dict[str, Any]:
    """A full validator-green fixture for one manifest target, minus the
    single field this migration adds -- reproducing the exact real-world
    red (public_projection_eligible only) that --check/--apply repair."""

    identity = TARGET_MANIFEST[filename]
    occurrence_id = identity["occurrence_id"]
    kind = _SELF_TEST_PROJECTION_KIND[filename]
    status = identity["certification_status"]
    surface = "قَالَ"
    root = None if kind == "particle_clitic_word" else "ق و ل"
    rootless_pedagogy = (
        "This particle has no root: it is a tool word, complete as it is."
        if kind == "particle_clitic_word" else None
    )
    projection = {
        "occurrence_id": occurrence_id,
        "surface": surface,
        "normalization": "NFC",
        "kind": kind,
        "segments": [
            {
                "segment_index": 0,
                "surface": surface,
                "char_start": 0,
                "char_end": len(surface),
                "semantic_class": "selftest_class",
                "renderer_class": "qg-selftest",
                "gloss": "selftest gloss",
                "sarf_note": "Sarf - selftest note.",
                "nahw_note": "Nahw - selftest note.",
            },
        ],
        "whole_word_gloss": "selftest gloss",
        "learner_explanation": "selftest learner explanation.",
        "entry_links": [],
        "entry_link_state": "none_yet",
        "morpheme_spans": [
            {
                "morpheme_occurrence_id": "morph:selftest:%s" % occurrence_id,
                "segment_index": 0,
                "char_start": 0,
                "char_end": len(surface),
            },
        ],
        "root": root,
        "rootless_pedagogy": rootless_pedagogy,
        "hover_cards": [
            {
                "component_surface": surface,
                "contextual_gloss": "selftest gloss",
                "particle_identity": None,
                "contextual_function": None,
                "sarf_note": "Sarf - selftest note.",
                "nahw_note": "Nahw - selftest note.",
                "governor": None,
                "governed_expression": None,
                "scope": None,
                "attachment": None,
                "alternatives": [],
                "reason": "selftest reason",
                "unresolved": None,
                "entry_link": None,
            },
        ],
        "unresolved": None,
        "certification": {
            "status": status,
            "plane": {"segmentation": status},
        },
        "evidence_refs": ["fact:selftest:%s" % occurrence_id],
    }
    projection_digest = validate_website_payload.projection_hash(projection)
    return {
        "schema": identity["schema"],
        "schema_version": identity["schema_version"],
        "payload_kind": identity["payload_kind"],
        "occurrence_id": occurrence_id,
        "artifact_id": identity["artifact_id"],
        "appearance": {
            "appearance_id": "app:selftest:%s" % occurrence_id,
            "page_id": "reader:selftest",
            "page_kind": "reader",
        },
        "projection": projection,
        "projection_hash": projection_digest,
        "reverse_links": {
            "occurrence_to_appearances": [
                {
                    "appearance_id": "app:selftest:%s" % occurrence_id,
                    "page_id": "reader:selftest",
                    "page_kind": "reader",
                    "projection_hash": projection_digest,
                },
            ],
            "entry_to_occurrences": [],
        },
        "provenance": {
            "provenance_class": "illustrative-constructed",
            "built_by": "selftest-builder v1",
            "source_refs": ["fact:selftest:%s" % occurrence_id],
        },
    }


def _run(label: str, condition: bool, failures: List[str]) -> None:
    print(("ok   " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def self_test() -> int:
    failures: List[str] = []

    # manifest integrity: exactly the four specified targets, and the
    # frozen candidate canary can never be pinned.
    _run(
        "manifest is exactly the four specified targets",
        set(TARGET_MANIFEST) == {
            "no_entry_link_17_78_3.payload.json",
            "noun_libuulatihinna_24_31_23.payload.json",
            "unresolved_ma_2_284_2.payload.json",
            "verb_ituni_12_59_5.payload.json",
        },
        failures,
    )
    _run(
        "manifest never pins the frozen candidate safety canary",
        all(
            identity["occurrence_id"] != FROZEN_CANDIDATE_OCCURRENCE_ID
            for identity in TARGET_MANIFEST.values()
        ),
        failures,
    )

    # 1. per-target: red witness, transform, preservation, hash propagation,
    #    validator-green, idempotency.
    for filename, identity in TARGET_MANIFEST.items():
        fixture = _synthetic_valid_payload(filename)
        _verify_identity(filename, fixture, identity)  # must not raise

        pre_errors = validate_website_payload.validate_payload(fixture)
        _run(
            "%s: fixture reproduces the real red -- public_projection_"
            "eligible is the only failing check" % filename,
            pre_errors == [
                "public_projection_eligible: certification.status %r is "
                "non-authoritative and projection.public_projection_"
                "eligible must be explicit false; got None"
                % identity["certification_status"]
            ],
            failures,
        )

        transformed = transform_payload(fixture)
        _run(
            "%s: public_projection_eligible becomes explicit false"
            % filename,
            transformed["projection"]["public_projection_eligible"]
            is False,
            failures,
        )

        expected_projection = copy.deepcopy(fixture["projection"])
        expected_projection["public_projection_eligible"] = False
        actual_projection = copy.deepcopy(transformed["projection"])
        _run(
            "%s: every other projection field is byte-preserved" % filename,
            actual_projection == expected_projection,
            failures,
        )
        _run(
            "%s: certification, unresolved, and evidence_refs are "
            "preserved exactly" % filename,
            transformed["projection"]["certification"]
            == fixture["projection"]["certification"]
            and transformed["projection"]["unresolved"]
            == fixture["projection"]["unresolved"]
            and transformed["projection"]["evidence_refs"]
            == fixture["projection"]["evidence_refs"],
            failures,
        )
        _run(
            "%s: provenance is preserved exactly" % filename,
            transformed["provenance"] == fixture["provenance"],
            failures,
        )

        recomputed = validate_website_payload.projection_hash(
            transformed["projection"]
        )
        _run(
            "%s: projection_hash is recomputed from the transformed "
            "projection" % filename,
            transformed["projection_hash"] == recomputed
            and transformed["projection_hash"] != fixture["projection_hash"],
            failures,
        )
        _run(
            "%s: every reverse appearance carries the same recomputed "
            "hash" % filename,
            all(
                app["projection_hash"] == recomputed
                for app in transformed["reverse_links"][
                    "occurrence_to_appearances"
                ]
            ),
            failures,
        )

        post_errors = validate_website_payload.validate_payload(transformed)
        _run(
            "%s: validator is green after transformation" % filename,
            post_errors == [],
            failures,
        )

        twice = transform_payload(transformed)
        _run(
            "%s: already-transformed input is byte-stable under a second "
            "pass (idempotent)" % filename,
            _dump_canonical(twice) == _dump_canonical(transformed),
            failures,
        )

    # 2. refusal cases -- built from one representative fixture.
    filename = "unresolved_ma_2_284_2.payload.json"
    identity = TARGET_MANIFEST[filename]
    base = _synthetic_valid_payload(filename)

    drifted_occurrence = copy.deepcopy(base)
    drifted_occurrence["occurrence_id"] = "quran:99:99:99"
    drifted_occurrence["projection"]["occurrence_id"] = "quran:99:99:99"
    try:
        _verify_identity(filename, drifted_occurrence, identity)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a drifted occurrence_id is refused, not best-effort mutated",
        refused,
        failures,
    )

    drifted_artifact = copy.deepcopy(base)
    drifted_artifact["artifact_id"] = "artifact:drifted:0:0:0"
    try:
        _verify_identity(filename, drifted_artifact, identity)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a drifted artifact_id is refused, not best-effort mutated",
        refused,
        failures,
    )

    drifted_status = copy.deepcopy(base)
    drifted_status["projection"]["certification"]["status"] = "candidate"
    try:
        _verify_identity(filename, drifted_status, identity)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a drifted certification.status is refused, not best-effort "
        "mutated",
        refused,
        failures,
    )

    certified = copy.deepcopy(base)
    certified["projection"]["certification"]["status"] = "certified"
    try:
        transform_payload(certified)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "certification.status=certified is refused rather than mutated -- "
        "this tool is only for already non-authoritative samples",
        refused,
        failures,
    )

    for illegal_value in (True, "false", 0, None):
        illegal = copy.deepcopy(base)
        illegal["projection"]["public_projection_eligible"] = illegal_value
        try:
            transform_payload(illegal)
            refused = False
        except TargetShapeError:
            refused = True
        _run(
            "an existing public_projection_eligible value of %r (neither "
            "absent nor false) is refused" % (illegal_value,),
            refused,
            failures,
        )

    already_false = copy.deepcopy(base)
    already_false["projection"]["public_projection_eligible"] = False
    already_false["projection_hash"] = validate_website_payload.projection_hash(
        already_false["projection"]
    )
    for row in already_false["reverse_links"]["occurrence_to_appearances"]:
        row["projection_hash"] = already_false["projection_hash"]
    try:
        transform_payload(already_false)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "an existing public_projection_eligible value of False is not "
        "refused (already-migrated input is legal)",
        not refused,
        failures,
    )

    missing_reverse_key = copy.deepcopy(base)
    del missing_reverse_key["reverse_links"]["occurrence_to_appearances"]
    try:
        transform_payload(missing_reverse_key)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a missing reverse_links.occurrence_to_appearances key is refused",
        refused,
        failures,
    )

    non_list_reverse = copy.deepcopy(base)
    non_list_reverse["reverse_links"]["occurrence_to_appearances"] = {
        "not": "a list"
    }
    try:
        transform_payload(non_list_reverse)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a non-list reverse_links.occurrence_to_appearances is refused",
        refused,
        failures,
    )

    missing_reverse_links = copy.deepcopy(base)
    del missing_reverse_links["reverse_links"]
    try:
        transform_payload(missing_reverse_links)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a missing reverse_links object is refused",
        refused,
        failures,
    )

    tampered_canary = copy.deepcopy(base)
    tampered_canary["occurrence_id"] = FROZEN_CANDIDATE_OCCURRENCE_ID
    tampered_canary["projection"]["occurrence_id"] = (
        FROZEN_CANDIDATE_OCCURRENCE_ID
    )
    try:
        _verify_identity(filename, tampered_canary, identity)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a tampered occurrence_id of quran:61:5:4 is refused under a "
        "target filename",
        refused,
        failures,
    )

    # 3. --apply on an isolated temp directory touches only the four
    #    manifest filenames; a non-target payload (including one carrying
    #    quran:61:5:4) is byte-untouched.
    with tempfile.TemporaryDirectory(
        prefix="website-public-eligibility-selftest-"
    ) as tmp:
        tmp_dir = Path(tmp)
        for target_filename in TARGET_MANIFEST:
            _write_canonical(
                tmp_dir / target_filename,
                _synthetic_valid_payload(target_filename),
            )
        non_target_filename = "multi_entry_liqawmihi_61_5_4.payload.json"
        non_target_payload = {
            "schema": "qamus.website_projection_payload.v1",
            "occurrence_id": FROZEN_CANDIDATE_OCCURRENCE_ID,
            "note": "non-target fixture; must never be read or written",
        }
        non_target_before = _dump_canonical(non_target_payload)
        (tmp_dir / non_target_filename).write_text(
            non_target_before, encoding="utf-8", newline="\n"
        )

        pre_check_stale = check(tmp_dir)
        _run(
            "--check reports all four synthetic targets stale before apply",
            sorted(pre_check_stale) == sorted(TARGET_MANIFEST),
            failures,
        )

        written = apply_migration(tmp_dir)
        _run(
            "--apply writes exactly the four manifest targets",
            sorted(written) == sorted(TARGET_MANIFEST),
            failures,
        )
        non_target_after = (tmp_dir / non_target_filename).read_text(
            encoding="utf-8"
        )
        _run(
            "a non-target payload (including one carrying quran:61:5:4) is "
            "byte-untouched",
            non_target_after == non_target_before,
            failures,
        )
        _run(
            "--check is green immediately after --apply",
            check(tmp_dir) == [],
            failures,
        )

        again = apply_migration(tmp_dir)
        _run(
            "a second --apply is a no-op (idempotent on disk)",
            again == [],
            failures,
        )

    if failures:
        print("\n%d SELF-TEST CASE(S) FAILED" % len(failures))
        return 1
    print("\nALL SELF-TEST CASES PASSED")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--payload-dir", type=Path, default=SAMPLES_DIR)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            return self_test()
        if args.check:
            stale = check(args.payload_dir)
            if stale:
                print(
                    "WEBSITE PUBLIC ELIGIBILITY MIGRATION CHECK: STALE (%d) "
                    "- %s" % (len(stale), ", ".join(sorted(stale)))
                )
                return 1
            print(
                "WEBSITE PUBLIC ELIGIBILITY MIGRATION CHECK: PASS (%d/%d "
                "payloads match the canonical fail-closed transformation)"
                % (len(TARGET_MANIFEST), len(TARGET_MANIFEST))
            )
            return 0
        written = apply_migration(args.payload_dir)
        print(
            "WEBSITE PUBLIC ELIGIBILITY MIGRATION APPLIED (%d/%d payloads "
            "written; %d already current)"
            % (
                len(written),
                len(TARGET_MANIFEST),
                len(TARGET_MANIFEST) - len(written),
            )
        )
        return 0
    except TargetShapeError as exc:
        print("WEBSITE PUBLIC ELIGIBILITY MIGRATION REFUSED: %s" % exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
