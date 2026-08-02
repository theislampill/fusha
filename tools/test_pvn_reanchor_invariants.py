#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable P/V/N product re-anchor invariants.

The first bounded canary is the already-supported quran:61:5:4 occurrence.
It introduces no new linguistic conclusion. The checks bind its website
candidate payload to the canonical surface, the exact evidence-backed
opening/host geometry, and the authoritative P/V/N appearance universe.

This hand-built v1.2 payload can prove exact local surface, a separate
appearance-binding hash, evidence-bounded neutral spans, appearance fanout
declaration, and reverse-link identity. It does not prove that four
concrete appearance envelopes consume the projection, nor that revocation
propagates to them; those are A4 acceptance gaps. It also does not prove
renderer support or the unsupported candidate host-internal boundary.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_website_payload as website_validator


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


OCCURRENCE_ID = "quran:61:5:4"
BOUND_APPEARANCE_ID = "01133eb5431b:u0:x1:w3"
BOUND_PAGE_ID = "entry:01133eb5431b"
UNRESOLVED_PRIMARY_TEXT = (
    "Analysis unresolved; candidate analyses are listed only as alternatives."
)
PAYLOAD_PATH = (
    ROOT
    / "qamus"
    / "examples"
    / "website-payloads"
    / "multi_entry_liqawmihi_61_5_4.payload.json"
)
UNIVERSE_PATH = (
    ROOT / "qamus" / "lattice" / "example-ayah-universe.occurrences.jsonl"
)
APPEARANCE_UNIVERSE_PATH = (
    ROOT / "qamus" / "lattice" / "example-ayah-universe.jsonl"
)
PILOT_PROJECTIONS_PATH = (
    ROOT / "qamus" / "examples" / "p007-li-pilot" / "projections.jsonl"
)
P007_REVERSE_UNIVERSE_PATH = (
    ROOT / "qamus" / "lattice" / "p007-reverse-universe.jsonl"
)

PUBLIC_WORKFLOW_TERMS = re.compile(
    r"(?i)(?:"
    r"quran\.com|corpus\.quran\.com|\bqac\b|quranic arabic corpus|"
    r"tanzil|sunnah\.com|"
    r"\breviewer(?:-private)?\b|\btwo[- ]vote\b|\bcandidate mode\b|"
    r"\bpacket\b|\bsource row\b|\bclassification row\b|\brung[- ]?\d+\b|"
    r"\bworkflow\b|\bprivate path\b|\bmcp\b|"
    r"(?:^|[\s\"'])/srv/|[A-Z]:\\"
    r")"
)
PAYLOAD_PRIVATE_OR_EXTERNAL_TERMS = re.compile(
    r"(?i)(?:"
    r"quran\.com|corpus\.quran\.com|\bqac\b|quranic arabic corpus|"
    r"tanzil|sunnah\.com|"
    r"\breviewer-private\b|(?:^|[\s\"'])/srv/|[A-Z]:\\"
    r")"
)


def _jsonl_row(path: Path, key: str, value: str) -> dict:
    matches = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            candidate = row.get("projection", row)
            if candidate.get(key) == value:
                matches.append(row)
    if len(matches) != 1:
        raise AssertionError(
            f"{path.relative_to(ROOT)} must contain exactly one "
            f"{key}={value!r} row; found {len(matches)}"
        )
    return matches[0]


def _learner_fields(projection: dict) -> list[str]:
    """Return only renderer-facing learner prose, never opaque trace ids."""
    values = [
        projection.get("whole_word_gloss"),
        projection.get("learner_explanation"),
        projection.get("rootless_pedagogy"),
    ]
    unresolved = projection.get("unresolved")
    if isinstance(unresolved, dict):
        values.append(unresolved.get("message"))
    for segment in projection.get("segments", []):
        values.extend(
            segment.get(key)
            for key in ("gloss", "sarf_note", "nahw_note")
        )
    for card in projection.get("hover_cards", []):
        values.extend(
            card.get(key)
            for key in (
                "contextual_gloss",
                "contextual_function",
                "sarf_note",
                "nahw_note",
                "reason",
                "unresolved",
            )
        )
        values.extend(card.get("alternatives", []))
    return [value for value in values if isinstance(value, str)]


def _all_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            item
            for child in value.values()
            for item in _all_strings(child)
        ]
    if isinstance(value, list):
        return [item for child in value for item in _all_strings(child)]
    return []


def _rehash(payload: dict) -> None:
    payload["projection_hash"] = website_validator.projection_hash(
        payload["projection"]
    )
    for appearance in payload["reverse_links"]["occurrence_to_appearances"]:
        appearance["projection_hash"] = payload["projection_hash"]
    if hasattr(website_validator, "appearance_binding_hash"):
        payload["appearance_binding_hash"] = (
            website_validator.appearance_binding_hash(payload)
        )


def _fork_first_appearance_map_morpheme(payload: dict) -> None:
    appearance = payload["appearance"]
    rows = appearance.setdefault(
        "canonical_to_appearance_span_map",
        [
            {
                "appearance_char_end": 2,
                "appearance_char_start": 0,
                "canonical_char_end": 2,
                "canonical_char_start": 0,
                "morpheme_occurrence_id": "m:61:5:4:li",
                "segment_index": 0,
            },
        ],
    )
    rows[0]["morpheme_occurrence_id"] = "m:wrong"


def _add_phantom_reverse_appearance(payload: dict) -> None:
    payload["reverse_links"]["occurrence_to_appearances"].append(
        {
            "appearance_id": "phantom:appearance",
            "page_id": "example:phantom",
            "page_kind": "example_card",
            "projection_hash": payload["projection_hash"],
        }
    )


class PvnReanchorInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
        cls.universe = _jsonl_row(
            UNIVERSE_PATH, "occurrence_id", OCCURRENCE_ID
        )
        cls.bound_appearance = _jsonl_row(
            APPEARANCE_UNIVERSE_PATH,
            "appearance_id",
            BOUND_APPEARANCE_ID,
        )
        cls.pilot_row = _jsonl_row(
            PILOT_PROJECTIONS_PATH, "occurrence_id", OCCURRENCE_ID
        )
        cls.pilot = cls.pilot_row["projection"]
        cls.p007_reverse = _jsonl_row(
            P007_REVERSE_UNIVERSE_PATH, "occurrence_id", OCCURRENCE_ID
        )

    def test_website_surface_and_visible_spans_come_from_canonical_pilot(
        self,
    ) -> None:
        projection = self.payload["projection"]
        self.assertEqual(projection["surface"], self.pilot["surface"])

        website_segments = [
            (
                row["surface"],
                row["char_start"],
                row["char_end"],
                row["renderer_class"],
            )
            for row in projection["segments"]
        ]
        geometry_supported_segments = [
            ("لِ", 0, 2, "qg-unresolved"),
            ("قَوْمِهِۦ", 2, 11, "qg-unresolved"),
        ]
        self.assertEqual(website_segments, geometry_supported_segments)

        self.assertEqual(
            [row["component_surface"] for row in projection["hover_cards"]],
            [row["surface"] for row in projection["segments"]],
        )

    def test_envelope_binds_exact_authoritative_appearance_geometry(
        self,
    ) -> None:
        payload = self.payload
        appearance = payload["appearance"]
        projection = payload["projection"]

        self.assertEqual(payload["schema_version"], "1.2.0")
        self.assertEqual(appearance["appearance_id"], BOUND_APPEARANCE_ID)
        self.assertEqual(appearance["page_id"], BOUND_PAGE_ID)
        self.assertEqual(appearance["page_kind"], "entry")
        self.assertEqual(
            appearance["binding_state"],
            "candidate_requires_renderer_capability_acceptance",
        )
        self.assertEqual(
            appearance["displayed_surface"],
            self.bound_appearance["displayed_surface"],
        )
        self.assertEqual(
            appearance["displayed_surface"],
            projection["surface"],
        )
        self.assertEqual(self.bound_appearance["canonical_loc"], "61:5:4")
        self.assertEqual(self.bound_appearance["crosswalk"], "resolved")
        self.assertEqual(self.bound_appearance["match_basis"], "exact")

        expected_map = [
            {
                "appearance_char_end": 2,
                "appearance_char_start": 0,
                "canonical_char_end": 2,
                "canonical_char_start": 0,
                "morpheme_occurrence_id": "mocc:p007:61:5:4",
                "segment_index": 0,
            },
            {
                "appearance_char_end": 11,
                "appearance_char_start": 2,
                "canonical_char_end": 11,
                "canonical_char_start": 2,
                "morpheme_occurrence_id": None,
                "segment_index": 1,
            },
        ]
        self.assertEqual(
            appearance["canonical_to_appearance_span_map"],
            expected_map,
        )
        binding_basis = {
            "appearance_id": BOUND_APPEARANCE_ID,
            "artifact_id": payload["artifact_id"],
            "binding_state": (
                "candidate_requires_renderer_capability_acceptance"
            ),
            "canonical_to_appearance_span_map": expected_map,
            "displayed_surface": projection["surface"],
            "normalization": "NFC",
            "occurrence_id": OCCURRENCE_ID,
            "page_id": BOUND_PAGE_ID,
            "page_kind": "entry",
            "projection_hash": payload["projection_hash"],
        }
        canonical = json.dumps(
            binding_basis,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            payload["appearance_binding_hash"],
            hashlib.sha256(canonical).hexdigest(),
        )

    def test_validator_rejects_cross_source_appearance_mismatch(
        self,
    ) -> None:
        bad = copy.deepcopy(self.payload)
        bad["appearance"]["appearance_id"] = "3041d6f44a27:u11:x1:w3"
        bad["appearance"]["page_id"] = "entry:3041d6f44a27"
        if hasattr(website_validator, "appearance_binding_hash"):
            bad["appearance_binding_hash"] = (
                website_validator.appearance_binding_hash(bad)
            )
        errors = website_validator.validate_payload(bad)
        self.assertTrue(
            any("appearance_binding" in error for error in errors),
            msg=errors,
        )

    def test_candidate_primary_plane_is_neutral_and_identity_bound(
        self,
    ) -> None:
        projection = self.payload["projection"]
        morphemes = {
            row["segment_index"]: row
            for row in projection["morpheme_spans"]
        }
        self.assertEqual(
            projection["whole_word_gloss"],
            "unresolved",
        )
        self.assertEqual(
            projection["learner_explanation"],
            UNRESOLVED_PRIMARY_TEXT,
        )
        self.assertEqual(len(projection["segments"]), len(projection["hover_cards"]))
        for index, (segment, card) in enumerate(
            zip(projection["segments"], projection["hover_cards"])
        ):
            morpheme = morphemes.get(index)
            expected_morpheme_id = (
                morpheme["morpheme_occurrence_id"]
                if morpheme is not None
                else None
            )
            self.assertEqual(segment["semantic_class"], "unresolved")
            self.assertEqual(segment["renderer_class"], "qg-unresolved")
            self.assertEqual(segment["gloss"], "unresolved")
            self.assertEqual(segment["sarf_note"], UNRESOLVED_PRIMARY_TEXT)
            self.assertEqual(segment["nahw_note"], UNRESOLVED_PRIMARY_TEXT)
            self.assertEqual(card["segment_index"], index)
            self.assertEqual(
                card["morpheme_occurrence_id"],
                expected_morpheme_id,
            )
            self.assertEqual(card["component_surface"], segment["surface"])
            self.assertEqual(card["contextual_gloss"], "unresolved")
            self.assertIsNone(card["particle_identity"])
            self.assertIsNone(card["contextual_function"])
            self.assertEqual(card["sarf_note"], UNRESOLVED_PRIMARY_TEXT)
            self.assertEqual(card["nahw_note"], UNRESOLVED_PRIMARY_TEXT)
            self.assertIsNone(card["governor"])
            self.assertIsNone(card["governed_expression"])
            self.assertIsNone(card["scope"])
            self.assertIsNone(card["attachment"])
            self.assertEqual(card["reason"], UNRESOLVED_PRIMARY_TEXT)
            self.assertTrue(card["alternatives"])
            self.assertTrue(
                all(
                    alternative.startswith("Candidate only:")
                    for alternative in card["alternatives"]
                )
            )
            self.assertIsNone(card["entry_link"])

    def test_validator_rejects_candidate_primary_semantic_claims(
        self,
    ) -> None:
        mutations = (
            (
                "whole-word translation",
                lambda payload: payload["projection"].__setitem__(
                    "whole_word_gloss", "to his people"
                ),
            ),
            (
                "semantic colour",
                lambda payload: payload["projection"]["segments"][0].update(
                    {
                        "semantic_class": "jarr_clitic_lam",
                        "renderer_class": "qg-particle-jarr-clitic",
                    }
                ),
            ),
            (
                "primary contextual function",
                lambda payload: payload["projection"]["hover_cards"][0].__setitem__(
                    "contextual_function", "genitive preposition"
                ),
            ),
            (
                "primary root claim",
                lambda payload: payload["projection"]["hover_cards"][1].__setitem__(
                    "sarf_note", "The root is q w m."
                ),
            ),
            (
                "primary governor claim",
                lambda payload: payload["projection"]["hover_cards"][1].__setitem__(
                    "governor",
                    {
                        "loc": OCCURRENCE_ID,
                        "relation": "local governor",
                        "surface": "لِ",
                    },
                ),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                _rehash(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any("candidate_public_plane" in error for error in errors),
                    msg=errors,
                )

    def test_validator_rejects_invalid_certification_plane_states(
        self,
    ) -> None:
        mutations = (
            (
                "missing plane key",
                lambda payload: payload["projection"]["certification"][
                    "plane"
                ].pop("translation"),
            ),
            (
                "extra plane key",
                lambda payload: payload["projection"]["certification"][
                    "plane"
                ].__setitem__("case", "unresolved"),
            ),
            (
                "typoed states with settled-looking primary claims",
                lambda payload: (
                    payload["projection"]["certification"].__setitem__(
                        "plane",
                        {
                            key: "certifed"
                            for key in payload["projection"][
                                "certification"
                            ]["plane"]
                        },
                    ),
                    payload["projection"].__setitem__(
                        "whole_word_gloss", "to his people"
                    ),
                    payload["projection"]["segments"][0].update(
                        {
                            "semantic_class": "jarr_clitic_lam",
                            "renderer_class": "qg-particle-jarr-clitic",
                        }
                    ),
                ),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                _rehash(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any("candidate_public_plane" in error for error in errors),
                    msg=errors,
                )

    def test_validator_rejects_colour_hover_morpheme_identity_forks(
        self,
    ) -> None:
        mutations = (
            (
                "hover segment index",
                lambda payload: payload["projection"]["hover_cards"][0].__setitem__(
                    "segment_index", 1
                ),
            ),
            (
                "hover morpheme id",
                lambda payload: payload["projection"]["hover_cards"][0].__setitem__(
                    "morpheme_occurrence_id", "m:wrong"
                ),
            ),
            (
                "hover component surface",
                lambda payload: payload["projection"]["hover_cards"][0].__setitem__(
                    "component_surface", "ل"
                ),
            ),
            (
                "appearance map morpheme id",
                _fork_first_appearance_map_morpheme,
            ),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                _rehash(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any("identity_parity" in error for error in errors),
                    msg=errors,
                )

    def test_validator_rejects_malformed_morpheme_spans_and_missing_geometry(
        self,
    ) -> None:
        mutations = (
            (
                "morpheme segment index",
                lambda payload: payload["projection"]["morpheme_spans"][0].__setitem__(
                    "segment_index", 9
                ),
                "morpheme_spans",
            ),
            (
                "morpheme negative start",
                lambda payload: payload["projection"]["morpheme_spans"][0].__setitem__(
                    "char_start", -1
                ),
                "morpheme_spans",
            ),
            (
                "morpheme span mismatch",
                lambda payload: payload["projection"]["morpheme_spans"][0].__setitem__(
                    "char_end", 1
                ),
                "morpheme_spans",
            ),
            (
                "duplicate morpheme id",
                lambda payload: payload["projection"]["morpheme_spans"].append(
                    copy.deepcopy(
                        payload["projection"]["morpheme_spans"][0]
                    )
                ),
                "morpheme_spans",
            ),
            (
                "missing geometry evidence",
                lambda payload: payload["projection"].__setitem__(
                    "evidence_refs", []
                ),
                "geometry_evidence",
            ),
        )
        for name, mutate, needle in mutations:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                _rehash(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any(needle in error for error in errors),
                    msg=errors,
                )

    def test_validator_scans_every_learner_plane_for_private_source_prose(
        self,
    ) -> None:
        mutations = (
            lambda p: p["projection"].__setitem__(
                "whole_word_gloss", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"].__setitem__(
                "learner_explanation", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["segments"][0].__setitem__(
                "gloss", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["segments"][0].__setitem__(
                "sarf_note", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["segments"][0].__setitem__(
                "nahw_note", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0].__setitem__(
                "contextual_gloss", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0].__setitem__(
                "contextual_function", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0].__setitem__(
                "sarf_note", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0].__setitem__(
                "nahw_note", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0].__setitem__(
                "reason", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0].__setitem__(
                "unresolved", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["hover_cards"][0]["alternatives"].append(
                "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"]["unresolved"].__setitem__(
                "message", "Quranic Arabic Corpus says this"
            ),
            lambda p: p["projection"].__setitem__(
                "rootless_pedagogy", "Quranic Arabic Corpus says this"
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(field_index=index):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                _rehash(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any("public_boundary" in error for error in errors),
                    msg=errors,
                )

    def test_validator_rejects_private_paths_and_machine_topology(
        self,
    ) -> None:
        forbidden = (
            "C:" + "/Users/alice/private.json",
            "copied from " + "C:" + "/Users/alice/private.json",
            r"\\fileserver\share\private.json",
            r"copied from \\fileserver\share\private.json",
            "~/private.json",
            "/home/alice/private.json",
            "copied from /home/alice/private.json",
            "//fileserver/share/private.json",
            "192.168.1.40",
            "builder endpoint 192.168.1.40 is private",
        )
        for value in forbidden:
            with self.subTest(value=value):
                bad = copy.deepcopy(self.payload)
                bad["provenance"]["source_refs"].append(value)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any("machine_topology" in error for error in errors),
                    msg=errors,
                )
        legal = copy.deepcopy(self.payload)
        legal["provenance"]["source_refs"].append(
            "https://example.org/qamus/ref"
        )
        self.assertFalse(
            website_validator.validate_payload(legal),
        )

    def test_validator_fails_closed_on_shape_binding_and_reverse_mutations(
        self,
    ) -> None:
        mutations = (
            (
                "scalar projection",
                lambda payload: payload.__setitem__(
                    "projection", "not-an-object"
                ),
                "projection_shape",
                False,
            ),
            (
                "missing binding hash",
                lambda payload: payload.pop("appearance_binding_hash"),
                "appearance_binding",
                False,
            ),
            (
                "gapped local map",
                lambda payload: payload["appearance"][
                    "canonical_to_appearance_span_map"
                ][1].__setitem__("appearance_char_start", 3),
                "appearance_binding",
                True,
            ),
            (
                "combining-mark split",
                lambda payload: payload["appearance"][
                    "canonical_to_appearance_span_map"
                ][0].__setitem__("appearance_char_end", 1),
                "appearance_binding",
                True,
            ),
            (
                "missing reverse hash",
                lambda payload: payload["reverse_links"][
                    "occurrence_to_appearances"
                ][0].pop("projection_hash"),
                "hash_fork",
                False,
            ),
            (
                "phantom reverse row",
                _add_phantom_reverse_appearance,
                "appearance_binding",
                False,
            ),
            (
                "informed_by key",
                lambda payload: payload["projection"]["hover_cards"][0].__setitem__(
                    "informed_by", "hidden"
                ),
                "public_boundary",
                True,
            ),
            (
                "build host key",
                lambda payload: payload["appearance"].__setitem__(
                    "build_host", "builder-17"
                ),
                "public_boundary",
                False,
            ),
            (
                "separator-hidden source key",
                lambda payload: payload["appearance"].__setitem__(
                    "qac_source", None
                ),
                "public_boundary",
                False,
            ),
        )
        for name, mutate, needle, rehash in mutations:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                if rehash:
                    _rehash(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any(needle in error for error in errors),
                    msg=errors,
                )

    def test_validator_rejects_reverse_entry_state_and_identity_forks(
        self,
    ) -> None:
        def add_phantom_entry(payload):
            row = copy.deepcopy(
                payload["reverse_links"]["entry_to_occurrences"][0]
            )
            row["entry_id"] = "phantom-entry"
            payload["reverse_links"]["entry_to_occurrences"].append(row)

        mutations = (
            (
                "phantom reverse entry",
                add_phantom_entry,
            ),
            (
                "candidate state promoted in reverse only",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0].__setitem__("link_state", "certified"),
            ),
            (
                "relation kind lost in reverse",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0].pop("relation_kind"),
            ),
            (
                "edge evidence lost in reverse",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0].__setitem__("evidence_refs", []),
            ),
            (
                "wrong occurrence id",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0]["occurrences"][0].__setitem__(
                    "occurrence_id", "quran:61:5:5"
                ),
            ),
            (
                "wrong canonical surface",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0]["occurrences"][0].__setitem__(
                    "surface", "لِقَوْمِهِ"
                ),
            ),
            (
                "wrong location",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0]["occurrences"][0].__setitem__("loc", "61:5:5"),
            ),
            (
                "wrong projection hash",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0]["occurrences"][0].__setitem__(
                    "projection_hash", "0" * 64
                ),
            ),
            (
                "missing appearance page",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0]["occurrences"][0]["page_refs"].pop(),
            ),
            (
                "extra occurrence",
                lambda payload: payload["reverse_links"][
                    "entry_to_occurrences"
                ][0]["occurrences"].append(
                    copy.deepcopy(
                        payload["reverse_links"]["entry_to_occurrences"][0][
                            "occurrences"
                        ][0]
                    )
                ),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.payload)
                mutate(bad)
                errors = website_validator.validate_payload(bad)
                self.assertTrue(
                    any("reverse_entry_parity" in error for error in errors),
                    msg=errors,
                )

    def test_candidate_plane_rejects_coordinated_certified_entry_promotion(
        self,
    ) -> None:
        bad = copy.deepcopy(self.payload)
        forward = bad["projection"]["entry_links"][0]
        reverse = bad["reverse_links"]["entry_to_occurrences"][0]
        for row in (forward, reverse):
            row["relation_kind"] = "certified_entry"
            row["link_state"] = "certified"
            row["evidence_refs"] = ["opaque:invented-certification"]
        _rehash(bad)
        for reverse_row in bad["reverse_links"]["entry_to_occurrences"]:
            for occurrence in reverse_row["occurrences"]:
                occurrence["projection_hash"] = bad["projection_hash"]
        errors = website_validator.validate_payload(bad)
        self.assertTrue(
            any("candidate_public_plane" in error for error in errors),
            msg=errors,
        )

    def test_shorter_appearance_cannot_shift_morpheme_letter_ownership(
        self,
    ) -> None:
        bad = copy.deepcopy(self.payload)
        bad["appearance"].update(
            {
                "appearance_id": "3041d6f44a27:u11:x1:w3",
                "displayed_surface": "لِقَوْمِهِ",
                "page_id": "entry:3041d6f44a27",
            }
        )
        span_map = bad["appearance"]["canonical_to_appearance_span_map"]
        span_map[0]["appearance_char_end"] = 4
        span_map[1]["appearance_char_start"] = 4
        span_map[1]["appearance_char_end"] = 10
        _rehash(bad)
        errors = website_validator.validate_payload(bad)
        self.assertTrue(
            any("letter ownership" in error for error in errors),
            msg=errors,
        )

    def test_authoritative_shorter_appearance_preserves_ownership(
        self,
    ) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["appearance"].update(
            {
                "appearance_id": "3041d6f44a27:u11:x1:w3",
                "displayed_surface": "لِقَوْمِهِ",
                "page_id": "entry:3041d6f44a27",
            }
        )
        span_map = candidate["appearance"][
            "canonical_to_appearance_span_map"
        ]
        span_map[1]["appearance_char_end"] = 10
        _rehash(candidate)
        self.assertEqual(
            website_validator.validate_payload(candidate),
            [],
        )

    def test_private_workflow_prose_is_rejected_outside_learner_fields(
        self,
    ) -> None:
        bad = copy.deepcopy(self.payload)
        bad["provenance"]["built_by"] = "two-vote workflow output"
        errors = website_validator.validate_payload(bad)
        self.assertTrue(
            any("public_boundary" in error for error in errors),
            msg=errors,
        )

    def test_context_pages_do_not_become_entry_identity(self) -> None:
        entry_links = {
            (
                row["entry_id"],
                row["relation_kind"],
                row["segment_index"],
            )
            for row in self.payload["projection"]["entry_links"]
        }
        self.assertEqual(
            entry_links,
            {
                ("b10a1ee04666", "candidate_entry", 0),
                ("65d3d5c51f24", "candidate_entry", None),
            },
        )
        self.assertTrue(
            {"01133eb5431b", "3041d6f44a27", "7f1f8b8e29e6"}.isdisjoint(
                {row[0] for row in entry_links}
            )
        )

    def test_authoritative_pvn_appearance_fanout_declares_one_projection_hash(
        self,
    ) -> None:
        expected_ids = self.p007_reverse["appearances"]["ids"]
        reverse = self.payload["reverse_links"]["occurrence_to_appearances"]
        entry_rows = [row for row in reverse if row["page_kind"] == "entry"]
        actual_ids = [row["appearance_id"] for row in entry_rows]

        self.assertEqual(len(actual_ids), len(set(actual_ids)))
        self.assertEqual(set(actual_ids), set(expected_ids))
        self.assertEqual(
            len(actual_ids), self.p007_reverse["appearances"]["count"]
        )

        projection_hash = self.payload["projection_hash"]
        canonical = json.dumps(
            self.payload["projection"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            projection_hash, hashlib.sha256(canonical).hexdigest()
        )
        for row in entry_rows:
            entry_id = row["appearance_id"].split(":", 1)[0]
            self.assertEqual(row["page_id"], f"entry:{entry_id}")
            self.assertEqual(row["projection_hash"], projection_hash)

        self.assertEqual(
            {
                row["appearance_id"]
                for row in self.pilot_row["appearances"]
            },
            set(expected_ids),
        )
        self.assertEqual(
            {
                row["projection_hash"]
                for row in self.pilot_row["appearances"]
            },
            {self.pilot_row["projection_hash"]},
        )

    def test_p007_reverse_universe_surface_and_appearance_alignment(
        self,
    ) -> None:
        projection = self.payload["projection"]
        self.assertEqual(self.p007_reverse["surface"], projection["surface"])
        self.assertEqual(
            self.p007_reverse["universe_surface"], projection["surface"]
        )
        self.assertEqual(self.p007_reverse["universe_alignment"], "nfc_exact")
        self.assertEqual(
            self.p007_reverse["appearances"]["ids"],
            self.universe["appearance_ids"],
        )
        self.assertEqual(
            self.p007_reverse["appearances"]["count"],
            self.universe["appearance_count"],
        )

    def test_contextual_translation_and_external_attachment_abstain(
        self,
    ) -> None:
        projection = self.payload["projection"]
        self.assertEqual(
            projection["whole_word_gloss"],
            "unresolved",
        )
        self.assertNotRegex(
            projection["learner_explanation"], r"(?i)\bM(?:u|o)sa\b"
        )
        self.assertEqual(
            projection["certification"]["plane"]["contextual_meaning"],
            "unresolved",
        )
        self.assertEqual(
            projection["certification"]["plane"]["translation"],
            "unresolved",
        )
        self.assertEqual(
            projection["certification"]["plane"]["referent"], "unresolved"
        )

        for card in projection["hover_cards"]:
            self.assertIsNone(card["governor"])
        self.assertNotIn(
            "قال",
            json.dumps(
                projection["hover_cards"],
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

    def test_root_and_root_family_are_explicitly_unresolved(self) -> None:
        projection = self.payload["projection"]
        self.assertIsNone(projection["root"])
        self.assertEqual(
            projection["certification"]["status"], "unresolved"
        )
        self.assertEqual(
            projection["certification"]["plane"]["root"], "unresolved"
        )
        self.assertNotIn(
            "root_family_of_entry",
            {row["relation_kind"] for row in projection["entry_links"]},
        )
        self.assertRegex(
            projection["unresolved"]["message"], r"(?i)\broot\b"
        )
        self.assertEqual(projection["unresolved"]["candidate_count"], 2)
        self.assertEqual(
            projection["unresolved"]["candidates"],
            [
                "opening-span clitic analysis",
                "host-internal stem and attached-pronoun analysis",
            ],
        )

    def test_public_learner_fields_have_no_source_or_workflow_leak(
        self,
    ) -> None:
        for value in _all_strings(self.payload):
            self.assertIsNone(
                PAYLOAD_PRIVATE_OR_EXTERNAL_TERMS.search(value),
                msg=f"private or external-source language in payload: {value!r}",
            )
        for value in _learner_fields(self.payload["projection"]):
            self.assertIsNone(
                PUBLIC_WORKFLOW_TERMS.search(value),
                msg=f"private/source/workflow language in learner field: {value!r}",
            )

    def test_reverse_page_refs_cover_reader_and_every_pvn_appearance(
        self,
    ) -> None:
        expected_pages = {"reader:61:5"} | {
            f"entry:{appearance_id.split(':', 1)[0]}"
            for appearance_id in self.universe["appearance_ids"]
        }
        reverse_rows = self.payload["reverse_links"]["entry_to_occurrences"]
        forward_rows = self.payload["projection"]["entry_links"]
        edge_keys = {
            "entry_id",
            "evidence_refs",
            "link_state",
            "relation_kind",
            "segment_index",
            "sense_id",
            "sense_state",
        }
        self.assertEqual(
            {
                json.dumps(
                    {key: row[key] for key in edge_keys},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for row in reverse_rows
            },
            {
                json.dumps(
                    {key: row[key] for key in edge_keys},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for row in forward_rows
            },
        )
        self.assertTrue(
            all(row["relation_kind"] == "candidate_entry"
                for row in reverse_rows)
        )
        self.assertTrue(
            all(row["link_state"] == "candidate"
                for row in reverse_rows)
        )
        self.assertTrue(
            all(row["sense_state"] == "unresolved"
                for row in reverse_rows)
        )
        self.assertTrue(
            all(row["evidence_refs"] for row in reverse_rows)
        )
        for entry_row in reverse_rows:
            matched = []
            for occurrence in entry_row["occurrences"]:
                if occurrence["occurrence_id"] == OCCURRENCE_ID:
                    matched.append(occurrence)
            self.assertEqual(len(matched), 1)
            self.assertEqual(
                matched[0]["surface"], self.payload["projection"]["surface"]
            )
            self.assertEqual(matched[0]["loc"], "61:5:4")
            self.assertEqual(set(matched[0]["page_refs"]), expected_pages)
            self.assertEqual(
                len(matched[0]["page_refs"]),
                len(expected_pages),
            )
            self.assertEqual(
                matched[0]["projection_hash"],
                self.payload["projection_hash"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
