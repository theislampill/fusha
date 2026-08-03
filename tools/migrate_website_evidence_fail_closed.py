#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded fail-closed migration for four unsupported certified website samples.

Round E1 of the website-evidence fail-closed repair. Exactly four committed
``qamus/examples/website-payloads/*.payload.json`` samples claim
``certification.status: "certified"`` while one or more of their
``evidence_refs`` fail to resolve to current repository certification
authority (see ``tools/website_evidence_resolver.py``). This tool rewrites
only those four payloads to an honest, validator-compatible non-authoritative
posture:

- ``projection.certification.status`` becomes ``"unresolved"`` -- the only
  status contract section 10.2 and ``check_unresolved_and_rootless`` accept
  alongside a non-null ``projection.unresolved`` object.
- Every ``certification.plane`` member that was ``"certified"`` becomes
  ``"review_required"``; already ``"candidate"``/other members are preserved.
- ``projection.unresolved`` becomes a non-null, schema-shaped
  (``state``/``message``/``candidate_count``/``candidates``) object that
  honestly names the evidence gap and a bounded next action, without private
  topology or source prose.
- ``projection.public_projection_eligible`` becomes ``false``.
- ``provenance.provenance_class`` becomes ``"illustrative-from-live"`` (re-
  expressed from an already-rich live/candidate row; facts not yet
  certified -- contract section 8), the closed vocabulary's honest
  non-authoritative class for these hand-assembled contract samples.
- ``projection_hash`` and every ``reverse_links.occurrence_to_appearances[*]
  .projection_hash`` are recomputed together from the transformed projection.

Occurrence identity, exact surface, spans, entry links, hover content, source
refs, evidence refs, and reverse appearance identities are byte-preserved:
this migration changes publication/certification posture only, never
linguistic conclusions.

The target set is an explicit closed manifest (filename to pinned
schema/schema_version/payload_kind/occurrence_id/artifact_id), never a
directory scan: an unlisted payload is never touched, and a listed payload
whose identity has drifted from its pin is refused rather than best-effort
mutated. ``quran:61:5:4`` (the frozen 1.2.0 candidate safety canary) can never
appear in the manifest.

Usage:
    python tools/migrate_website_evidence_fail_closed.py --check
    python tools/migrate_website_evidence_fail_closed.py --apply
    python tools/migrate_website_evidence_fail_closed.py --self-test
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

# Explicit closed target manifest: filename -> pinned identity. No directory
# scan ever substitutes for this list, and no payload outside it is read or
# written by --check/--apply.
TARGET_MANIFEST: Dict[str, Dict[str, str]] = {
    "ma_nafiya_93_3_1.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.1.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:93:3:1",
        "artifact_id": "artifact:canary:93:3:1",
    },
    "ma_relative_2_284_10.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.1.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:2:284:10",
        "artifact_id": "artifact:proofp:2:284:10",
    },
    "noun_rajulayni_2_282_59.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:2:282:59",
        "artifact_id": "artifact:vncanary:2:282:59",
    },
    "verb_qamu_2_20_13.payload.json": {
        "schema": "qamus.website_projection_payload.v1",
        "schema_version": "1.0.0",
        "payload_kind": "occurrence_projection",
        "occurrence_id": "quran:2:20:13",
        "artifact_id": "artifact:vncanary:2:20:13",
    },
}

# The frozen 1.2.0 candidate safety canary this round must never disturb. A
# structural guarantee, re-asserted at import time and in --self-test: no
# manifest entry may ever pin this occurrence.
FROZEN_CANDIDATE_OCCURRENCE_ID = "quran:61:5:4"

UNRESOLVED_STATE = "certification_evidence_unresolved"
UNRESOLVED_MESSAGE = (
    "Repository certification evidence for this occurrence has not "
    "resolved to current certification authority; certification status is "
    "held at unresolved pending re-review."
)
UNRESOLVED_NEXT_ACTION = (
    "Re-certify against currently authoritative repository evidence before "
    "any public certified delivery."
)
NON_AUTHORITATIVE_PROVENANCE_CLASS = "illustrative-from-live"


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
    mismatches = [
        "%s=%r (expected %r)" % (key, payload.get(key), expected)
        for key, expected in identity.items()
        if payload.get(key) != expected
    ]
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

    result = copy.deepcopy(payload)
    projection = result.get("projection")
    if not isinstance(projection, dict):
        raise TargetShapeError("payload.projection must be an object")
    certification = projection.get("certification")
    if not isinstance(certification, dict) or not isinstance(
        certification.get("plane"), dict
    ):
        raise TargetShapeError(
            "payload.projection.certification.plane must be an object"
        )
    reverse = result.get("reverse_links")
    appearances = (
        reverse.get("occurrence_to_appearances")
        if isinstance(reverse, dict)
        else None
    )
    if not isinstance(appearances, list) or not appearances:
        raise TargetShapeError(
            "payload.reverse_links.occurrence_to_appearances must be a "
            "non-empty array"
        )
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        raise TargetShapeError("payload.provenance must be an object")

    new_plane = {
        key: ("review_required" if value == "certified" else value)
        for key, value in certification["plane"].items()
    }
    projection["certification"] = {
        **certification,
        "status": "unresolved",
        "plane": new_plane,
    }
    projection["unresolved"] = {
        "state": UNRESOLVED_STATE,
        "message": UNRESOLVED_MESSAGE,
        "candidate_count": 1,
        "candidates": [UNRESOLVED_NEXT_ACTION],
    }
    projection["public_projection_eligible"] = False
    # evidence_refs, entry_links, segments, hover_cards, source_refs and
    # every other linguistic/evidence field are left exactly as deep-copied:
    # this migration changes publication/certification posture only.
    result["projection"] = projection

    new_hash = validate_website_payload.projection_hash(projection)
    result["projection_hash"] = new_hash
    for appearance in appearances:
        if not isinstance(appearance, dict):
            raise TargetShapeError(
                "reverse_links.occurrence_to_appearances row must be an "
                "object"
            )
        appearance["projection_hash"] = new_hash

    result["provenance"] = {
        **provenance,
        "provenance_class": NON_AUTHORITATIVE_PROVENANCE_CLASS,
    }
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

def _synthetic_stale_payload(filename: str) -> Dict[str, Any]:
    identity = TARGET_MANIFEST[filename]
    return {
        **identity,
        "occurrence_id": identity["occurrence_id"],
        "appearance": {
            "appearance_id": "app:selftest:1",
            "page_id": "reader:selftest",
            "page_kind": "reader",
        },
        "projection": {
            "occurrence_id": identity["occurrence_id"],
            "surface": "X",
            "certification": {
                "status": "certified",
                "plane": {
                    "function": "certified",
                    "segmentation": "candidate",
                },
            },
            "unresolved": None,
            "evidence_refs": [
                "fact:selftest:sha256:" + "0" * 64,
                "unregistered-scheme:selftest:1",
            ],
        },
        "projection_hash": "0" * 64,
        "reverse_links": {
            "occurrence_to_appearances": [
                {
                    "appearance_id": "app:selftest:1",
                    "page_id": "reader:selftest",
                    "page_kind": "reader",
                    "projection_hash": "0" * 64,
                }
            ],
            "entry_to_occurrences": [],
        },
        "provenance": {
            "provenance_class": "certified",
            "built_by": "selftest-builder v1",
            "source_refs": ["fact:selftest:sha256:" + "0" * 64],
        },
    }


def _run(label: str, condition: bool, failures: List[str]) -> None:
    print(("ok   " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def self_test() -> int:
    failures: List[str] = []

    # manifest integrity: the frozen candidate canary can never be pinned.
    _run(
        "manifest never pins the frozen candidate safety canary",
        all(
            identity["occurrence_id"] != FROZEN_CANDIDATE_OCCURRENCE_ID
            for identity in TARGET_MANIFEST.values()
        ),
        failures,
    )

    # 1. stale certified input is transformed.
    filename = "ma_nafiya_93_3_1.payload.json"
    stale = _synthetic_stale_payload(filename)
    transformed = transform_payload(stale)
    projection = transformed["projection"]
    _run(
        "certification.status becomes unresolved",
        projection["certification"]["status"] == "unresolved",
        failures,
    )
    _run(
        "certified plane member becomes review_required; candidate preserved",
        projection["certification"]["plane"]
        == {"function": "review_required", "segmentation": "candidate"},
        failures,
    )
    _run(
        "unresolved becomes a non-null schema-valid object",
        isinstance(projection["unresolved"], dict)
        and bool(projection["unresolved"].get("message", "").strip())
        and projection["unresolved"].get("candidate_count")
        == len(projection["unresolved"].get("candidates") or []),
        failures,
    )
    _run(
        "public_projection_eligible is false",
        projection["public_projection_eligible"] is False,
        failures,
    )
    _run(
        "evidence_refs are preserved exactly",
        projection["evidence_refs"] == stale["projection"]["evidence_refs"],
        failures,
    )
    _run(
        "provenance_class becomes the honest non-authoritative class",
        transformed["provenance"]["provenance_class"]
        == NON_AUTHORITATIVE_PROVENANCE_CLASS,
        failures,
    )
    recomputed = validate_website_payload.projection_hash(projection)
    _run(
        "projection_hash is recomputed from the transformed projection",
        transformed["projection_hash"] == recomputed
        and transformed["projection_hash"] != stale["projection_hash"],
        failures,
    )
    _run(
        "every reverse appearance carries the same recomputed hash",
        all(
            app["projection_hash"] == recomputed
            for app in transformed["reverse_links"]["occurrence_to_appearances"]
        ),
        failures,
    )

    # 2. already-transformed input is byte-stable (idempotent).
    twice = transform_payload(transformed)
    _run(
        "already-transformed input is byte-stable under a second pass",
        _dump_canonical(twice) == _dump_canonical(transformed),
        failures,
    )

    # 3. refuses an unknown/divergent target shape rather than mutating it.
    divergent = _synthetic_stale_payload(filename)
    divergent["occurrence_id"] = "quran:99:99:99"
    try:
        _verify_identity(filename, divergent, TARGET_MANIFEST[filename])
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a divergent occurrence identity is refused, not best-effort mutated",
        refused,
        failures,
    )

    missing_plane = _synthetic_stale_payload(filename)
    del missing_plane["projection"]["certification"]["plane"]
    try:
        transform_payload(missing_plane)
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "an unknown shape (missing certification.plane) is refused",
        refused,
        failures,
    )

    # 4. quran:61:5:4 cannot enter the target set, even under a tampered
    #    manifest filename or a same-named non-target file on disk.
    tampered = _synthetic_stale_payload(filename)
    tampered["occurrence_id"] = FROZEN_CANDIDATE_OCCURRENCE_ID
    tampered["projection"]["occurrence_id"] = FROZEN_CANDIDATE_OCCURRENCE_ID
    try:
        _verify_identity(filename, tampered, TARGET_MANIFEST[filename])
        refused = False
    except TargetShapeError:
        refused = True
    _run(
        "a tampered occurrence_id of quran:61:5:4 is refused under a "
        "target filename",
        refused,
        failures,
    )

    # 5. --apply on an isolated temp directory touches only the four
    #    manifest filenames; a non-target payload (including one carrying
    #    quran:61:5:4) is byte-untouched.
    with tempfile.TemporaryDirectory(
        prefix="website-evidence-fail-closed-selftest-"
    ) as tmp:
        tmp_dir = Path(tmp)
        for target_filename in TARGET_MANIFEST:
            _write_canonical(
                tmp_dir / target_filename,
                _synthetic_stale_payload(target_filename),
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
                    "WEBSITE EVIDENCE FAIL-CLOSED MIGRATION CHECK: STALE (%d) - %s"
                    % (len(stale), ", ".join(sorted(stale)))
                )
                return 1
            print(
                "WEBSITE EVIDENCE FAIL-CLOSED MIGRATION CHECK: PASS (%d/%d "
                "payloads match the canonical fail-closed transformation)"
                % (len(TARGET_MANIFEST), len(TARGET_MANIFEST))
            )
            return 0
        written = apply_migration(args.payload_dir)
        print(
            "WEBSITE EVIDENCE FAIL-CLOSED MIGRATION APPLIED (%d/%d payloads "
            "written; %d already current)"
            % (
                len(written),
                len(TARGET_MANIFEST),
                len(TARGET_MANIFEST) - len(written),
            )
        )
        return 0
    except TargetShapeError as exc:
        print("WEBSITE EVIDENCE FAIL-CLOSED MIGRATION REFUSED: %s" % exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
