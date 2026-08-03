#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the corpus occurrence/appearance/projection coverage manifest.

Train D atomic component 1: the deterministic population spine consumed by
later rich-colour/rich-hover batches.  One row per displayed token appearance
in ``qamus/lattice/example-ayah-universe.jsonl`` (117,117 rows, including
pause marks), joined against:

  * ``qamus/data/current/entries.jsonl``                 (2,092 P/N/V entries)
  * ``qamus/lattice/example-ayah-universe.occurrences.jsonl`` (canonical grain)
  * ``qamus/indexes/occurrence-appearances.jsonl``        (reader/entry_example
    surface index; the closest committed proxy for reader-payload posture)
  * ``qamus/lattice/particle-occurrence-matrix.jsonl``    (candidate particle
    function lattice; NOT a colour, hover or Nahw fact source)

This is a coverage manifest, not a linguistic fact producer. Every disposition
is either grounded in one of the above committed authorities or reports an
explicit reason it could not be measured -- and a disposition that only ever
recognises an orthographic *shape* signal (an article-looking prefix, a
plural-looking suffix, a particle *candidate* relation) must say so, never
claim the stronger fact it is not entitled to (letter/morpheme ownership,
lexeme binding, certification, a colour/hover fact, occurrence-bound Nahw, or
live state). No network, no live mutation. Deterministic: same committed
inputs -> byte-identical output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.normalize_ar import bare  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA = "qamus.corpus_projection_manifest.v1"
BUILDER_ID = "build_corpus_projection_manifest"
BUILDER_VERSION = "2.0.0"

DEFAULT_ENTRIES = os.path.join(REPO_ROOT, "qamus", "data", "current", "entries.jsonl")
DEFAULT_UNIVERSE = os.path.join(REPO_ROOT, "qamus", "lattice", "example-ayah-universe.jsonl")
DEFAULT_UNIVERSE_OCC = os.path.join(
    REPO_ROOT, "qamus", "lattice", "example-ayah-universe.occurrences.jsonl")
DEFAULT_APPEARANCE_INDEX = os.path.join(
    REPO_ROOT, "qamus", "indexes", "occurrence-appearances.jsonl")
DEFAULT_PARTICLE_MATRIX = os.path.join(
    REPO_ROOT, "qamus", "lattice", "particle-occurrence-matrix.jsonl")
DEFAULT_BASELINE_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "reports", "corpus-projection-baseline.json")
DEFAULT_SAMPLE_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "examples", "corpus-projection-manifest.sample.jsonl")
DEFAULT_SAMPLE_META_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "examples", "corpus-projection-manifest.sample.meta.json")

SECTION_PREFIX = {"particle": "p", "noun": "n", "verb": "v"}

# String-alignment tiers only. These are never a certification (governed by
# docs/certification-authority.md) -- they describe how the displayed
# fragment matches a canonical Quran location, nothing about a governed fact.
ALIGNMENT_MATCH_TIER_STATUS = {
    "exact": "alignment_tier_exact",
    "strict": "alignment_tier_strict",
    "strict_word_unique": "alignment_tier_strict_word_unique",
}
RECALL_ONLY_TIERS = {"loose", "loose_word_unique"}

ARTICLE_RE = re.compile(r"^(?P<conj>[وف])?(?P<article>ال)")
KBL_PROCLITIC_RE = re.compile(r"^[كبل](?=ال)")
ARABIC_LETTER_RE = re.compile(r"[؀-ۿ]")
PLURAL_SUFFIXES = ("ات", "ون", "ين")  # ات, ون, ين
DEFINITE_ARTICLE_CANDIDATE = "definite article al-"
NAHW_UNCOVERED_SUBFACTS = ["case_ending", "governor_relation", "syntactic_role", "agreement"]
CANARY_SOURCE_KEYS = ("p009", "p099")
SAMPLE_SIZE_DEFAULT = 480


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_rows(rows):
    """Hash the canonical (sorted-key, compact) JSON serialization of ``rows``."""
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(
            row, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_jsonl(rows, output_path):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ))
            handle.write("\n")


def write_pretty_json(obj, output_path):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


# ---------------------------------------------------------------------------
# Input loaders
# ---------------------------------------------------------------------------

def load_entries(path):
    by_id = {}
    section_counts = Counter()
    for row in _read_jsonl(path):
        entry_id = str(row.get("id") or "").strip()
        if not entry_id:
            raise ValueError(f"entries.jsonl row missing id: {row!r}")
        if entry_id in by_id:
            raise ValueError(f"duplicate entry id in entries.jsonl: {entry_id}")
        section = row.get("section")
        by_id[entry_id] = {
            "id": entry_id,
            "section": section,
            "headword": row.get("headword"),
            "root": row.get("root"),
            "source_keys": list(row.get("source_keys") or []),
            "sense_count": len(row.get("senses") or []),
        }
        section_counts[section] += 1
    return by_id, dict(section_counts)


def load_universe_occurrences(path):
    by_loc = {}
    for row in _read_jsonl(path):
        loc = str(row.get("canonical_loc") or "").strip()
        if not loc:
            continue
        by_loc[loc] = row
    return by_loc


def load_appearance_index(path):
    by_loc = {}
    for row in _read_jsonl(path):
        loc = str(row.get("loc") or "").strip()
        if not loc:
            continue
        by_loc[loc] = row
    return by_loc


def load_particle_matrix(path):
    """Return (by_key, by_appearance): the direct self-join key and the
    reverse context-appearance index, kept structurally distinct so a
    particle's own candidate/entry relation is never merged with the
    context appearances that merely host it (required for the P009/WAW
    fanout invariant)."""
    by_key = {}
    by_appearance = defaultdict(list)
    for row in _read_jsonl(path):
        source_key = str(row.get("particle_source_key") or "").strip()
        loc = str(row.get("canonical_loc") or "").strip()
        if not source_key or not loc:
            continue
        by_key[(source_key, loc)] = row
        for appearance_id in row.get("appearance_ids") or []:
            by_appearance[appearance_id].append(row)
    return by_key, dict(by_appearance)


# ---------------------------------------------------------------------------
# Orthographic shape recall (surface-pattern heuristic; general, not
# hand-authored). This is NOT letter or morpheme ownership: it is a shape
# recall signal over the bare orthographic form only, and must never claim to
# be "measured" ownership.
# ---------------------------------------------------------------------------

def analyze_letter_ownership(displayed_surface):
    b = bare(displayed_surface or "")
    if not b or not ARABIC_LETTER_RE.search(b):
        return {
            "article": {"present": False, "leading_conjunction": None, "stem_after_article": None},
            "plural": {"suffix": None, "stem_before_suffix": None},
            "segmentation_consistent": True,
            "status": "not_measured",
            "reason": "displayed_surface bare() form is empty or contains no Arabic letters",
            "not_a_morpheme_ownership_claim": True,
        }

    match = ARTICLE_RE.match(b)
    plural_source = b
    if match:
        article = {
            "present": True,
            "leading_conjunction": match.group("conj"),
            "stem_after_article": b[match.end():],
        }
        # Analyze the plural suffix on the post-article remainder only, so the
        # same leading letters are never assigned to both the article and the
        # plural stem.
        plural_source = article["stem_after_article"]
    elif KBL_PROCLITIC_RE.match(b):
        # ك/ب/ل immediately followed by 'ال' -- could be a jarr/kaf-comparative
        # proclitic swallowing the article, or could be a lexeme-initial
        # ك/ب/ل before an unrelated 'ال'. This shape signal cannot resolve the
        # boundary, so it is reported as undetermined rather than as a false
        # negative (article absent) or a false positive (article present).
        article = {
            "present": "undetermined_proclitic_present",
            "leading_conjunction": None,
            "stem_after_article": None,
        }
    else:
        article = {"present": False, "leading_conjunction": None, "stem_after_article": None}

    plural_suffix = None
    stem_before = None
    for suffix in PLURAL_SUFFIXES:
        if plural_source.endswith(suffix) and len(plural_source) > len(suffix):
            plural_suffix = suffix
            stem_before = plural_source[: -len(suffix)]
            break
    plural = {"suffix": plural_suffix, "stem_before_suffix": stem_before}

    both_signals_fire = bool(article["present"]) and plural_suffix is not None
    segmentation_consistent = not both_signals_fire

    reason = (
        f"article={article['present']!r}; plural_suffix={plural_suffix or 'none'}; "
        "orthographic shape recall only, not a morpheme-ownership measurement"
    )
    return {
        "article": article,
        "plural": plural,
        "segmentation_consistent": segmentation_consistent,
        "status": "shape_recall_only",
        "reason": reason,
        "not_a_morpheme_ownership_claim": True,
    }


# ---------------------------------------------------------------------------
# Disposition computation
# ---------------------------------------------------------------------------

def _disp(status, reason, **extra):
    out = {"status": status, "reason": reason}
    out.update(extra)
    return out


def _not_joined_plane(row, status, reason, pause_reason):
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", pause_reason)
    return _disp(status, reason)


def compute_card_owner_binding(row, entries_by_id):
    """The card-owner entry's own binding -- proves nothing about the
    displayed token's lexeme (see compute_token_lexeme_binding)."""
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_entry_binding")
    entry_id = str(row.get("entry_id") or "").strip()
    if not entry_id:
        return _disp("owner_entry_unresolved", "displayed word appearance carries no entry_id")
    entry = entries_by_id.get(entry_id)
    if entry is None:
        return _disp("owner_entry_unresolved", f"entry_id {entry_id!r} not found in entries.jsonl")
    expected_prefix = SECTION_PREFIX.get(entry["section"])
    row_type = row.get("entry_type")
    if expected_prefix is not None and row_type != expected_prefix:
        return _disp(
            "owner_class_trust_violation",
            f"universe entry_type={row_type!r} but entries.jsonl section="
            f"{entry['section']!r} (expected entry_type={expected_prefix!r})",
        )
    return _disp(
        "owner_entry_resolved",
        f"card-owner entry_id resolved to entries.jsonl section={entry['section']!r}",
    )


def compute_token_lexeme_binding(row):
    """The displayed TOKEN's own lexeme/entry/sense identity -- distinct from
    the card-owner entry, which describes only the card the token appears on."""
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_lexeme")
    if row.get("selected"):
        return _disp(
            "bound_selected_token",
            "this appearance is the card-owner entry's own selected word; the card owner's "
            "lexeme/entry/sense is this token's lexeme/entry/sense",
        )
    return _disp(
        "token_lexeme_not_determined",
        "this appearance is a context token; its own lexeme/entry/sense is not determined by "
        "this manifest (card_owner_binding describes the card owner, never this displayed token)",
    )


def compute_surface(row):
    match_basis = row.get("match_basis")
    if match_basis == "not_a_word":
        return _disp("not_applicable", "quranic pause annotation is not a displayed word")
    if not str(row.get("displayed_surface") or "").strip():
        return _disp("missing_surface", "empty displayed_surface field on a word row")
    if match_basis in ALIGNMENT_MATCH_TIER_STATUS:
        status = ALIGNMENT_MATCH_TIER_STATUS[match_basis]
        return _disp(
            status,
            f"match_basis={match_basis} is a string-alignment tier; not a certification "
            "(certification is governed by docs/certification-authority.md)",
        )
    if match_basis in RECALL_ONLY_TIERS:
        return _disp(
            "recall_tier_only",
            f"match_basis={match_basis} is a loose orthographic match; "
            "repo policy: never a certification basis",
        )
    if match_basis == "ambiguous":
        return _disp("ambiguous_alignment", "word matched more than one canonical candidate")
    if match_basis == "ref_unparsed":
        return _disp("reference_unparsed", "example ref could not be parsed to a card_ref")
    if match_basis == "unaligned":
        return _disp("unaligned", "word could not be aligned to any canonical Quran location")
    return _disp("unknown_match_basis", f"unrecognized match_basis={match_basis!r}")


def _particle_attachments(row, particle_by_key, particle_by_appearance):
    attachments = []
    source_key = row.get("source_key")
    canonical_loc = row.get("canonical_loc")
    if source_key and canonical_loc:
        self_row = particle_by_key.get((source_key, canonical_loc))
        if self_row is not None:
            attachments.append(("self", self_row))
    for context_row in particle_by_appearance.get(row.get("appearance_id"), []):
        attachments.append(("context", context_row))
    return attachments


def compute_particle_candidate_refs(attachments):
    """A particle-occurrence-matrix candidate relation, carried honestly as a
    non-projection reference -- never a colour fact, a hover fact, an
    occurrence-bound Nahw fact, nor evidence that any of those exist."""
    refs = []
    for kind, matrix_row in attachments:
        matrix_id = matrix_row.get("matrix_id")
        if not matrix_id:
            continue
        refs.append({
            "matrix_id": matrix_id,
            "attachment_kind": kind,
            "function_candidates": list(matrix_row.get("function_candidates") or []),
            "certified": matrix_row.get("certified"),
            "not_a_colour_fact": True,
            "not_a_hover_fact": True,
            "not_an_occurrence_bound_nahw_fact": True,
            "not_evidence_that_any_of_those_facts_exist": True,
        })
    return refs


def compute_particle_function_candidates_at_loc(row, attachments, refs):
    """Renamed from the old (misnamed) 'nahw' plane: partial particle
    function-candidate evidence at this location only -- never occurrence
    bound, never a certified fact (all committed particle-matrix rows carry
    certified='none')."""
    if row.get("word_class") == "pause_mark":
        return _disp(
            "not_applicable", "pause_mark_token_has_no_particle_candidate_relation",
            fact_id=None, function_candidates=None,
        )
    if not attachments:
        return _disp(
            "authority_not_joined_in_closed_inputs",
            "no committed particle-occurrence-matrix row attaches to this appearance",
            fact_id=None, function_candidates=None,
        )
    fact_ids = sorted({r["matrix_id"] for r in refs})
    function_sets = sorted({tuple(r["function_candidates"]) for r in refs})
    return _disp(
        "candidate_only_partial_function_evidence",
        f"{len(attachments)} particle-matrix attachment(s); {len(function_sets)} distinct "
        "function_candidate set(s); partial function-candidate evidence only, not an "
        "occurrence-bound Nahw fact and not a colour/hover fact",
        fact_id=(fact_ids[0] if len(fact_ids) == 1 else fact_ids) if fact_ids else None,
        function_candidates=[list(s) for s in function_sets],
    )


def compute_nahw(row):
    """The real occurrence-bound Nahw plane (case ending, governor relation,
    syntactic role, agreement). No committed source in closed authority joins
    any of these; see particle_function_candidates_at_loc for the partial
    candidate evidence that does exist."""
    if row.get("word_class") == "pause_mark":
        return _disp(
            "not_applicable", "pause_mark_token_has_no_syntax",
            uncovered_subfacts=None,
        )
    return _disp(
        "occurrence_bound_nahw_not_joined_in_closed_inputs",
        "no committed occurrence-bound Nahw fact source (case ending, governor relation, "
        "syntactic role, agreement) is joined in this manifest's closed authority; the "
        "particle-occurrence-matrix supplies function candidates only",
        uncovered_subfacts=list(NAHW_UNCOVERED_SUBFACTS),
    )


def compute_sarf(row):
    """Branches on the TOKEN's own determined class, never on the card
    owner's section. The token's own class is determined only when this
    appearance IS the card-owner entry's own selected word."""
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_morphology", fact_id=None)
    if not row.get("selected"):
        return _disp(
            "token_class_not_determined",
            "this appearance is a context token; its own class (verb/noun/particle) is not "
            "determined by this manifest, so no class-scoped morphology disposition can be "
            "computed for it",
            fact_id=None,
        )
    return _disp(
        "authority_not_joined_in_closed_inputs",
        "no committed per-token sarf segmentation source is joined in this manifest's closed "
        "authority for any token class; deferred to the Train A/B sarf fact projector",
        fact_id=None,
    )


def compute_colour_and_hover(row):
    """Colour and hover are independently, honestly empty: no colour fact and
    no hover fact is joined anywhere in closed authority. A particle-matrix
    candidate relation is never promoted into either plane (see
    particle_function_candidate_refs / particle_function_candidates_at_loc for
    that candidate evidence)."""
    if row.get("word_class") == "pause_mark":
        pause_disp = _disp("not_applicable", "pause_mark_token_has_no_display_payload", fact_id=None)
        return dict(pause_disp), dict(pause_disp)
    colour = _disp("not_available", "no_colour_fact_joined_in_closed_inputs", fact_id=None)
    hover = _disp("not_available", "no_hover_fact_joined_in_closed_inputs", fact_id=None)
    return colour, hover


def compute_cross_plane_conflict(row, orthographic_shape_recall, attachments):
    """Report, never silently reconcile: orthographic shape recall and the
    particle-matrix 'definite article al-' candidate are two independent
    signals and sometimes disagree."""
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_article_or_candidate_signal")
    shape_article = orthographic_shape_recall["article"]["present"] is True
    candidate_article = any(
        DEFINITE_ARTICLE_CANDIDATE in (matrix_row.get("function_candidates") or [])
        for _kind, matrix_row in attachments
    )
    if shape_article != candidate_article:
        return _disp(
            "article_shape_vs_candidate_disagreement",
            f"orthographic_shape_recall.article.present={shape_article} vs particle-matrix "
            f"{DEFINITE_ARTICLE_CANDIDATE!r} candidate={candidate_article}; reported, never "
            "silently reconciled",
        )
    return _disp(
        "none",
        "orthographic shape recall and the particle-matrix definite-article candidate agree "
        "(both present or both absent) for this appearance",
    )


def compute_appearance_identity(row, occ_row):
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_canonical_appearance_identity")
    canonical_loc = row.get("canonical_loc")
    if canonical_loc and occ_row is not None:
        return _disp(
            "canonical_occurrence_identified",
            f"appearance resolves to canonical_loc={canonical_loc!r} in "
            "example-ayah-universe.occurrences.jsonl",
        )
    return _disp(
        "canonical_occurrence_not_identified",
        "this displayed word could not be aligned to a canonical Quran occurrence in closed "
        "authority (see surface for the alignment disposition)",
    )


def compute_reverse_trace(row):
    backlink = row.get("source_card_backlink")
    if backlink:
        return _disp("traceable", f"source_card_backlink={backlink}", source_card_backlink=backlink)
    return _disp("untraceable", "row carries no source_card_backlink", source_card_backlink=None)


def compute_revocation_dependency(row, appearance_index_row):
    if row.get("word_class") == "pause_mark" or not row.get("canonical_loc"):
        return _disp("not_applicable", "no canonical occurrence to depend on (pause mark or unaligned word)")
    entry_id = row.get("entry_id")
    if appearance_index_row is None:
        return _disp(
            "occurrence_absent_from_reader_index",
            "canonical_loc is not present in qamus/indexes/occurrence-appearances.jsonl; "
            "no revocation dependency is recorded there",
        )
    entry_relationships = appearance_index_row.get("entry_relationships") or []
    if entry_id in entry_relationships:
        return _disp(
            "linked_to_reader_index",
            "reader occurrence-appearances index carries entry_relationships for this entry; "
            "a card edit must trigger an occurrence-appearance rebuild",
        )
    return _disp(
        "occurrence_present_no_entry_link",
        "occurrence exists in the reader index but is not attributed to this entry there",
    )


def compute_payload(row, appearance_index_row):
    if row.get("word_class") == "pause_mark" or not row.get("canonical_loc"):
        return _disp("not_applicable", "no canonical occurrence to carry a payload record (pause mark or unaligned word)")
    if appearance_index_row is None:
        return _disp(
            "no_reader_index_record",
            "occurrence not present in qamus/indexes/occurrence-appearances.jsonl reader "
            "surface; no payload evidence is available in closed authority",
        )
    surface_kinds = {a.get("surface_kind") for a in appearance_index_row.get("appearances") or []}
    if "reader" in surface_kinds:
        return _disp(
            "reader_surface_recorded_in_committed_index",
            "reader index carries a reader-surface_kind appearance at this loc; this is a "
            "repository record of a past out-of-repo snapshot, not current live state "
            "(LIVE_QAMUS_MUTATION: NOT_AUTHORIZED)",
        )
    return _disp(
        "entry_example_only_no_reader_surface_recorded",
        "reader index carries only entry_example surface_kind appearances at this loc",
    )


def compute_pending_actions(word_class, card_owner_binding, surface, transclusion, payload,
                             sarf, nahw, colour, hover):
    if word_class == "pause_mark":
        return ["no_action_non_word_token"]
    actions = []
    if card_owner_binding["status"] != "owner_entry_resolved":
        actions.append("repair_card_owner_binding")
    if surface["status"] in ("unaligned", "ambiguous_alignment", "reference_unparsed", "missing_surface"):
        actions.append("resolve_canonical_alignment")
    if transclusion["fork_status"] == "divergent_colour_fact_id_present":
        actions.append("adjudicate_divergent_projection_identity")
    if payload["status"] == "no_reader_index_record":
        actions.append("attach_reader_surface_evidence")
    pending_fact_statuses = {"authority_not_joined_in_closed_inputs", "token_class_not_determined"}
    if sarf["status"] in pending_fact_statuses or \
            nahw["status"] == "occurrence_bound_nahw_not_joined_in_closed_inputs":
        actions.append("await_train_ab_fact_projection")
    if colour["status"] == "not_available" or hover["status"] == "not_available":
        actions.append("author_rich_colour_hover_batch")
    if not actions:
        actions.append("ready_for_rich_projection")
    return actions


def _hashable_fact_id(fact_id):
    if isinstance(fact_id, list):
        return tuple(sorted(fact_id))
    return fact_id


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_manifest(entries_path, universe_path, universe_occ_path, appearance_index_path,
                    particle_matrix_path):
    entries_by_id, section_counts = load_entries(entries_path)
    universe_rows = list(_read_jsonl(universe_path))
    occ_by_loc = load_universe_occurrences(universe_occ_path)
    appearance_by_loc = load_appearance_index(appearance_index_path)
    particle_by_key, particle_by_appearance = load_particle_matrix(particle_matrix_path)

    # Multi-entry transclusion fanout detection: same canonical_loc selected
    # by more than one distinct entry. This is transclusion fanout, not a
    # fork, unless the entries' own projection identities (colour fact_id)
    # actually diverge.
    selected_entries_by_loc = defaultdict(set)
    for row in universe_rows:
        if row.get("selected") and row.get("canonical_loc"):
            selected_entries_by_loc[row["canonical_loc"]].add(row["entry_id"])
    fork_locs = {loc: sorted(ids) for loc, ids in selected_entries_by_loc.items() if len(ids) > 1}

    output_rows = []
    stats = Counter()
    canary_rows_by_source_key = defaultdict(list)
    seen_appearance_ids = set()
    fork_signal_by_loc = defaultdict(lambda: {"colour_fact_ids": set(), "bare_surfaces": set(),
                                               "raw_surfaces": set()})
    fanout_rows_by_loc = defaultdict(list)

    for index, row in enumerate(universe_rows):
        appearance_id = row.get("appearance_id")
        if not appearance_id:
            raise ValueError(f"universe row at index {index} is missing appearance_id")
        if appearance_id in seen_appearance_ids:
            raise ValueError(f"duplicate appearance_id in example-ayah-universe.jsonl: {appearance_id}")
        seen_appearance_ids.add(appearance_id)
        word_class = row.get("word_class")
        canonical_loc = row.get("canonical_loc")
        occ_row = occ_by_loc.get(canonical_loc) if canonical_loc else None
        appearance_index_row = appearance_by_loc.get(canonical_loc) if canonical_loc else None
        attachments = _particle_attachments(row, particle_by_key, particle_by_appearance)
        particle_refs = [] if word_class == "pause_mark" else compute_particle_candidate_refs(attachments)

        card_owner_binding = compute_card_owner_binding(row, entries_by_id)
        token_lexeme_binding = compute_token_lexeme_binding(row)
        surface = compute_surface(row)
        orthographic_shape_recall = (
            analyze_letter_ownership(row.get("displayed_surface"))
            if word_class != "pause_mark"
            else {"article": {"present": None, "leading_conjunction": None, "stem_after_article": None},
                  "plural": {"suffix": None, "stem_before_suffix": None},
                  "segmentation_consistent": True,
                  "status": "not_applicable", "reason": "pause_mark_token_has_no_letters",
                  "not_a_morpheme_ownership_claim": True}
        )
        morpheme_ownership = _not_joined_plane(
            row, "not_joined_in_closed_inputs",
            "no committed morpheme-ownership fact source (distinct from orthographic shape "
            "recall) is joined in this manifest's closed authority",
            "pause_mark_token_has_no_morpheme_ownership",
        )
        sarf = compute_sarf(row)
        nahw = compute_nahw(row)
        particle_function_candidates_at_loc = compute_particle_function_candidates_at_loc(
            row, attachments, particle_refs)
        contextual_meaning = _not_joined_plane(
            row, "not_joined_in_closed_inputs",
            "no committed contextual-meaning fact source is joined in this manifest's closed authority",
            "pause_mark_token_has_no_contextual_meaning",
        )
        translation = _not_joined_plane(
            row, "not_joined_in_closed_inputs",
            "no committed translation fact source is joined in this manifest's closed authority",
            "pause_mark_token_has_no_translation",
        )
        colour, hover = compute_colour_and_hover(row)
        cross_plane_conflict = compute_cross_plane_conflict(row, orthographic_shape_recall, attachments)
        appearance_identity = compute_appearance_identity(row, occ_row)
        reverse_trace = compute_reverse_trace(row)
        certification = _not_joined_plane(
            row, "no_certification_record_joined",
            "no governed_fact.certification record is joined in this manifest's closed "
            "authority; certification is written only by the certification/revocation skill "
            "per docs/certification-authority.md, never by this component",
            "pause_mark_token_has_no_certification",
        )
        revocation_dependency = compute_revocation_dependency(row, appearance_index_row)
        payload = compute_payload(row, appearance_index_row)
        live_state = _disp(
            "not_measured",
            "no live query is authorized or performed by this component "
            "(LIVE_QAMUS_MUTATION: NOT_AUTHORIZED)",
        )

        is_fanout = bool(canonical_loc and canonical_loc in fork_locs and row.get("selected"))
        transclusion = {
            "is_transclusion_fanout": is_fanout,
            "fork_status": "not_applicable",
            "conflicting_entry_ids": fork_locs.get(canonical_loc, []) if is_fanout else [],
        }
        surface_conflict = _disp(
            "not_applicable",
            "surface_conflict is only measurable across multiple entries selecting the same "
            "canonical occurrence; this appearance is not part of a multi-entry transclusion "
            "fanout",
        )

        pending_actions = compute_pending_actions(
            word_class, card_owner_binding, surface, transclusion, payload, sarf, nahw, colour, hover,
        )

        out_row = {
            "appearance_id": row.get("appearance_id"),
            "entry_id": row.get("entry_id"),
            "entry_type": row.get("entry_type"),
            "source_key": row.get("source_key"),
            "card_ref": row.get("card_ref"),
            "card_index": row.get("card_index"),
            "card_token_count": row.get("card_token_count"),
            "usage_index": row.get("usage_index"),
            "sense_index": row.get("sense_index"),
            "tranche": row.get("tranche"),
            "tranche_kind": row.get("tranche_kind"),
            "display_local_loc": row.get("display_local_loc"),
            "canonical_loc": canonical_loc,
            "occurrence_id": (f"quran:{canonical_loc}" if canonical_loc else None),
            "displayed_surface": row.get("displayed_surface"),
            "word_class": word_class or "word",
            "selected": row.get("selected"),
            "crosswalk": row.get("crosswalk"),
            "match_basis": row.get("match_basis"),
            "blockers": row.get("blockers") or [],
            "denominators": {
                "displayed_token_index": index,
                "canonical_occurrence_appearance_count": (occ_row or {}).get("appearance_count"),
                "canonical_occurrence_selected_appearances": (occ_row or {}).get("selected_appearances"),
                "canonical_occurrence_context_appearances": (occ_row or {}).get("context_appearances"),
                "canonical_occurrence_entry_ids": sorted((occ_row or {}).get("entry_ids") or []),
            },
            "dispositions": {
                "card_owner_binding": card_owner_binding,
                "token_lexeme_binding": token_lexeme_binding,
                "surface": surface,
                "surface_conflict": surface_conflict,
                "orthographic_shape_recall": orthographic_shape_recall,
                "morpheme_ownership": morpheme_ownership,
                "sarf": sarf,
                "nahw": nahw,
                "particle_function_candidates_at_loc": particle_function_candidates_at_loc,
                "contextual_meaning": contextual_meaning,
                "translation": translation,
                "colour": colour,
                "hover": hover,
                "cross_plane_conflict": cross_plane_conflict,
                "appearance_identity": appearance_identity,
                "reverse_trace": reverse_trace,
                "certification": certification,
                "revocation_dependency": revocation_dependency,
                "payload": payload,
                "live_state": live_state,
                "pending_actions": pending_actions,
            },
            "particle_function_candidate_refs": particle_refs,
            "multi_entry_transclusion_fanout": transclusion,
        }
        output_rows.append(out_row)
        if is_fanout:
            fork_signal_by_loc[canonical_loc]["colour_fact_ids"].add(_hashable_fact_id(colour["fact_id"]))
            fork_signal_by_loc[canonical_loc]["bare_surfaces"].add(bare(row.get("displayed_surface") or ""))
            fork_signal_by_loc[canonical_loc]["raw_surfaces"].add(row.get("displayed_surface") or "")
            fanout_rows_by_loc[canonical_loc].append(out_row)

        stats["total_rows"] += 1
        stats[f"word_class:{out_row['word_class']}"] += 1
        stats[f"card_owner_binding:{card_owner_binding['status']}"] += 1
        stats[f"token_lexeme_binding:{token_lexeme_binding['status']}"] += 1
        stats[f"surface:{surface['status']}"] += 1
        stats[f"orthographic_shape_recall:{orthographic_shape_recall['status']}"] += 1
        stats[f"morpheme_ownership:{morpheme_ownership['status']}"] += 1
        stats[f"sarf:{sarf['status']}"] += 1
        stats[f"nahw:{nahw['status']}"] += 1
        stats[f"particle_function_candidates_at_loc:{particle_function_candidates_at_loc['status']}"] += 1
        stats[f"contextual_meaning:{contextual_meaning['status']}"] += 1
        stats[f"translation:{translation['status']}"] += 1
        stats[f"colour:{colour['status']}"] += 1
        stats[f"hover:{hover['status']}"] += 1
        stats[f"cross_plane_conflict:{cross_plane_conflict['status']}"] += 1
        stats[f"appearance_identity:{appearance_identity['status']}"] += 1
        stats[f"certification:{certification['status']}"] += 1
        stats[f"payload:{payload['status']}"] += 1
        stats[f"live_state:{live_state['status']}"] += 1
        stats[f"revocation_dependency:{revocation_dependency['status']}"] += 1
        for action in pending_actions:
            stats[f"pending_actions:{action}"] += 1
        if orthographic_shape_recall["article"]["present"] is True:
            stats["orthographic_shape_recall:article_present_rows"] += 1
        if orthographic_shape_recall["article"]["present"] == "undetermined_proclitic_present":
            stats["orthographic_shape_recall:article_undetermined_proclitic_rows"] += 1
        if orthographic_shape_recall["plural"]["suffix"]:
            stats["orthographic_shape_recall:plural_suffix_rows"] += 1
        if is_fanout:
            stats["multi_entry_transclusion_fanout:affected_rows"] += 1
        source_key = row.get("source_key")
        if source_key in CANARY_SOURCE_KEYS:
            canary_rows_by_source_key[source_key].append(out_row)

    # Second pass: resolve fork_status/surface_conflict for the multi-entry
    # transclusion-fanout population now that every entry's own colour
    # fact_id and displayed surface at each fork loc is known.
    for loc, out_rows_at_loc in fanout_rows_by_loc.items():
        signal = fork_signal_by_loc[loc]
        colour_divergent = len(signal["colour_fact_ids"]) > 1
        if len(signal["bare_surfaces"]) > 1:
            surf_status = "divergent_bare_surface_at_same_loc"
        elif len(signal["raw_surfaces"]) > 1:
            surf_status = "divergent_marks_only"
        else:
            surf_status = "none"
        fork_status = (
            "divergent_colour_fact_id_present" if colour_divergent
            else "no_divergent_projection_identity_in_closed_inputs"
        )
        for out_row in out_rows_at_loc:
            out_row["multi_entry_transclusion_fanout"]["fork_status"] = fork_status
            out_row["dispositions"]["surface_conflict"] = _disp(
                surf_status,
                "displayed-surface agreement across the entries selecting this canonical "
                "occurrence" if surf_status == "none" else
                "same canonical occurrence, divergent displayed surfaces across the entries "
                "selecting it -- reported, never silently reconciled",
            )
            out_row["dispositions"]["pending_actions"] = compute_pending_actions(
                out_row["word_class"], out_row["dispositions"]["card_owner_binding"],
                out_row["dispositions"]["surface"], out_row["multi_entry_transclusion_fanout"],
                out_row["dispositions"]["payload"], out_row["dispositions"]["sarf"],
                out_row["dispositions"]["nahw"], out_row["dispositions"]["colour"],
                out_row["dispositions"]["hover"],
            )
            stats[f"multi_entry_transclusion_fanout:fork_status:{fork_status}"] += 1
            stats[f"surface_conflict:{surf_status}"] += 1

    fork_status_locs = Counter()
    surface_conflict_locs = Counter()
    for loc, out_rows_at_loc in fanout_rows_by_loc.items():
        fork_status_locs[out_rows_at_loc[0]["multi_entry_transclusion_fanout"]["fork_status"]] += 1
        surface_conflict_locs[out_rows_at_loc[0]["dispositions"]["surface_conflict"]["status"]] += 1
    for status, count in fork_status_locs.items():
        stats[f"multi_entry_transclusion_fanout:fork_status_locs:{status}"] = count
    for status, count in surface_conflict_locs.items():
        stats[f"surface_conflict:locs:{status}"] = count

    stats["multi_entry_transclusion_fanout:selected_multi_entry_locs"] = len(fork_locs)
    stats["entries:total"] = len(entries_by_id)
    for section, count in section_counts.items():
        stats[f"entries:section:{section}"] = count

    context = {
        "entries_by_id": entries_by_id,
        "section_counts": section_counts,
        "fork_locs": fork_locs,
        "canary_rows_by_source_key": dict(canary_rows_by_source_key),
        "particle_by_key": particle_by_key,
        "particle_by_appearance": particle_by_appearance,
    }
    return output_rows, dict(stats), context


# ---------------------------------------------------------------------------
# Canary metrics (general assertions, not hand-authored per-word overrides)
# ---------------------------------------------------------------------------

def compute_canary_report(context):
    entries_by_id = context["entries_by_id"]
    canary_rows = context["canary_rows_by_source_key"]
    particle_by_key = context["particle_by_key"]

    report = {}

    p099_rows = canary_rows.get("p099", [])
    p099_entry_id = next((r["entry_id"] for r in p099_rows), None)
    p099_entry = entries_by_id.get(p099_entry_id) if p099_entry_id else None
    report["p099"] = {
        "entry_id": p099_entry_id,
        "sense_count": p099_entry["sense_count"] if p099_entry else None,
        "displayed_token_count": len(p099_rows),
        "cards": sorted({r["card_ref"] for r in p099_rows if r["card_ref"]}),
    }

    p009_rows = canary_rows.get("p009", [])
    p009_entry_id = next((r["entry_id"] for r in p009_rows), None)
    p009_candidate_locs = sorted({loc for (sk, loc) in particle_by_key if sk == "p009"})
    p009_context_appearance_total = sum(
        sum((row.get("page_appearances") or {}).values())
        for (sk, _loc), row in particle_by_key.items() if sk == "p009"
    )
    report["p009"] = {
        "entry_id": p009_entry_id,
        "own_page_displayed_token_count": len(p009_rows),
        "candidate_occurrence_count": len(p009_candidate_locs),
        "context_appearance_total": p009_context_appearance_total,
        "note": "candidate_occurrence_count/context_appearance_total are the particle's own "
                "candidate/entry relation, kept structurally separate from own_page_displayed_"
                "token_count (P009's own example-card context appearances).",
    }

    # AL-DHAKAR / AL-UNTHA definite-article shape recall: measured within P099's own
    # example fragments (92:3 "وما خلق الذكر والأنثى"), general article-detection rule.
    article_hits = [
        {"appearance_id": r["appearance_id"], "displayed_surface": r["displayed_surface"],
         "article": r["dispositions"]["orthographic_shape_recall"]["article"]}
        for r in p099_rows
        if r["dispositions"]["orthographic_shape_recall"]["article"]["present"] is True
        and r["dispositions"]["orthographic_shape_recall"]["article"]["stem_after_article"] in ("ذكر", "أنثى")
    ]
    report["al_dhakar_al_untha_article_ownership"] = {
        "matched_rows": article_hits,
        "status": "measured" if article_hits else "blocked",
        "reason": (
            "definite-article prefix separately recalled from stem for AL-DHAKAR/AL-UNTHA "
            "tokens in P099's own 92:3 example (shape recall only, not a morpheme-ownership claim)"
            if article_hits else
            "no AL-DHAKAR/AL-UNTHA token found among P099's displayed tokens"
        ),
    }

    # AL-SAMAWAT plural/inflection shape recall: measured within P099's own 2:284 example.
    plural_hits = [
        {"appearance_id": r["appearance_id"], "displayed_surface": r["displayed_surface"],
         "plural": r["dispositions"]["orthographic_shape_recall"]["plural"]}
        for r in p099_rows
        if r["dispositions"]["orthographic_shape_recall"]["plural"]["suffix"] == "ات"
        and r["dispositions"]["orthographic_shape_recall"]["article"]["present"] is True
    ]
    report["al_samawat_plural_ownership"] = {
        "matched_rows": plural_hits,
        "status": "measured" if plural_hits else "blocked",
        "reason": (
            "plural suffix separately recalled from stem for AL-SAMAWAT in P099's own "
            "2:284 example (shape recall only, not a morpheme-ownership claim)"
            if plural_hits else
            "no AL-SAMAWAT-shaped token found among P099's displayed tokens"
        ),
    }

    # MA (p099) same-surface occurrence-bound function/hover disambiguation deficit.
    p099_function_sets = sorted({
        tuple(row.get("function_candidates") or [])
        for (sk, _loc), row in particle_by_key.items() if sk == "p099"
    })
    distinct_variants = len(p099_function_sets)
    report["ma_function_disambiguation_deficit"] = {
        "distinct_function_candidate_variants": distinct_variants,
        "status": "blocked" if distinct_variants <= 1 else "differentiated",
        "reason": (
            "every p099 (MA) occurrence in particle-occurrence-matrix currently carries the "
            "same undifferentiated homograph function_candidates list; occurrence-bound "
            "function/hover disambiguation is not yet provable from committed authority"
            if distinct_variants <= 1 else
            f"{distinct_variants} distinct function_candidate sets observed across p099 occurrences"
        ),
    }

    return report


def verify_colour_hover_identity(rows):
    """Report what was actually compared. Equality of two null fact_ids is
    NOT a comparison and must not be counted as checked; a candidate
    reference is not a colour/hover fact and must not be counted as
    checked either."""
    both_present_compared = 0
    both_absent_not_compared = 0
    candidate_only_not_compared = 0
    violations = 0
    for row in rows:
        colour = row["dispositions"]["colour"]
        hover = row["dispositions"]["hover"]
        if colour["status"] != hover["status"] or colour["fact_id"] != hover["fact_id"]:
            violations += 1
            continue
        if colour["fact_id"] is not None and hover["fact_id"] is not None:
            both_present_compared += 1
        elif row.get("particle_function_candidate_refs"):
            candidate_only_not_compared += 1
        else:
            both_absent_not_compared += 1
    return {
        "both_present_compared": both_present_compared,
        "both_absent_not_compared": both_absent_not_compared,
        "candidate_only_not_compared": candidate_only_not_compared,
        "violations": violations,
    }


def build_baseline(rows, stats, context, inputs, output_hash):
    section_counts = context["section_counts"]
    entries_by_id = context["entries_by_id"]
    universe_row_count = stats["total_rows"]
    word_rows = stats.get("word_class:word", 0)
    pause_rows = stats.get("word_class:pause_mark", 0)

    aligned_word_rows = (
        stats.get("surface:alignment_tier_exact", 0)
        + stats.get("surface:alignment_tier_strict", 0)
        + stats.get("surface:alignment_tier_strict_word_unique", 0)
        + stats.get("surface:recall_tier_only", 0)
    )

    baseline = {
        "generator": {"id": BUILDER_ID, "version": BUILDER_VERSION, "schema": SCHEMA},
        "inputs": inputs,
        "entry_totals": {
            "total_entries": len(entries_by_id),
            "particle": section_counts.get("particle", 0),
            "noun": section_counts.get("noun", 0),
            "verb": section_counts.get("verb", 0),
        },
        "manifest_totals": {
            "total_rows": universe_row_count,
            "word_rows": word_rows,
            "pause_mark_rows": pause_rows,
            "aligned_word_rows": aligned_word_rows,
            "unaligned_word_rows": stats.get("surface:unaligned", 0)
            + stats.get("surface:reference_unparsed", 0)
            + stats.get("surface:ambiguous_alignment", 0),
        },
        "disposition_counts": {
            key: value for key, value in sorted(stats.items())
            if ":" in key and key.split(":", 1)[0] in (
                "card_owner_binding", "token_lexeme_binding", "surface", "surface_conflict",
                "orthographic_shape_recall", "morpheme_ownership", "sarf", "nahw",
                "particle_function_candidates_at_loc", "contextual_meaning", "translation",
                "colour", "hover", "cross_plane_conflict", "appearance_identity", "certification",
                "revocation_dependency", "payload", "live_state", "pending_actions",
                "multi_entry_transclusion_fanout",
            )
        },
        "orthographic_shape_recall_counts": {
            "article_present_rows": stats.get("orthographic_shape_recall:article_present_rows", 0),
            "article_undetermined_proclitic_rows":
                stats.get("orthographic_shape_recall:article_undetermined_proclitic_rows", 0),
            "plural_suffix_rows": stats.get("orthographic_shape_recall:plural_suffix_rows", 0),
        },
        "multi_entry_transclusion_fanout": {
            "selected_multi_entry_locs":
                stats.get("multi_entry_transclusion_fanout:selected_multi_entry_locs", 0),
            "affected_rows": stats.get("multi_entry_transclusion_fanout:affected_rows", 0),
        },
        "canaries": compute_canary_report(context),
        "colour_hover_identity_invariant": verify_colour_hover_identity(rows),
        "full_output": {
            "row_count": len(rows),
            "sha256": output_hash,
        },
        "verification": {},
    }

    expected_entries = 2092
    expected_p, expected_n, expected_v = 100, 1045, 947
    baseline["verification"]["entries_set_equality"] = (
        baseline["entry_totals"]["total_entries"] == expected_entries
        and baseline["entry_totals"]["particle"] == expected_p
        and baseline["entry_totals"]["noun"] == expected_n
        and baseline["entry_totals"]["verb"] == expected_v
    )
    baseline["verification"]["universe_row_count_equality"] = (
        universe_row_count == 117117 and word_rows == 109471 and pause_rows == 7646
    )
    baseline["verification"]["occurrence_count_equality"] = (
        baseline["manifest_totals"]["aligned_word_rows"] == 109018
        and baseline["manifest_totals"]["unaligned_word_rows"] == 453
    )
    return baseline


# ---------------------------------------------------------------------------
# Sample selection (deterministic, bounded)
# ---------------------------------------------------------------------------

def select_sample(rows, context, sample_size):
    fork_locs = context["fork_locs"]
    selected_ids = []
    seen = set()

    def take(candidates):
        for row in candidates:
            key = row["appearance_id"]
            if key not in seen:
                seen.add(key)
                selected_ids.append(key)

    canary_rows = [r for r in rows if r.get("source_key") in CANARY_SOURCE_KEYS]
    take(canary_rows)

    fork_rows = [r for r in rows if r["multi_entry_transclusion_fanout"]["is_transclusion_fanout"]]
    take(sorted(fork_rows, key=lambda r: r["appearance_id"])[:60])

    unaligned_rows = [r for r in rows if r["dispositions"]["surface"]["status"] == "unaligned"]
    take(sorted(unaligned_rows, key=lambda r: r["appearance_id"])[:20])

    pause_rows = [r for r in rows if r["word_class"] == "pause_mark"]
    take(sorted(pause_rows, key=lambda r: r["appearance_id"])[:20])

    if len(selected_ids) < sample_size:
        remainder = sample_size - len(selected_ids)
        stride = max(1, len(rows) // max(remainder, 1))
        for i in range(0, len(rows), stride):
            if len(selected_ids) >= sample_size:
                break
            key = rows[i]["appearance_id"]
            if key not in seen:
                seen.add(key)
                selected_ids.append(key)

    order = {row["appearance_id"]: index for index, row in enumerate(rows)}
    selected_ids.sort(key=lambda appearance_id: order[appearance_id])
    by_id = {row["appearance_id"]: row for row in rows}
    return [by_id[appearance_id] for appearance_id in selected_ids]


SAMPLE_SELECTION_RULE = (
    "Deterministic, bounded, order-preserving selection over the full manifest (source order "
    "from example-ayah-universe.jsonl): (1) every P009/P099 canary appearance; (2) up to 60 "
    "multi-entry-transclusion-fanout appearances (lowest appearance_id first); (3) up to 20 "
    "unaligned-word appearances; (4) up to 20 pause-mark appearances; (5) a fixed-stride fill of "
    "remaining rows across the full manifest until the target sample size is reached. No random "
    "sampling."
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", default=DEFAULT_ENTRIES)
    parser.add_argument("--universe", default=DEFAULT_UNIVERSE)
    parser.add_argument("--universe-occurrences", default=DEFAULT_UNIVERSE_OCC)
    parser.add_argument("--appearance-index", default=DEFAULT_APPEARANCE_INDEX)
    parser.add_argument("--particle-matrix", default=DEFAULT_PARTICLE_MATRIX)
    parser.add_argument("--output", help="full manifest JSONL output path (normally under out/, gitignored)")
    parser.add_argument("--baseline-output", default=DEFAULT_BASELINE_OUTPUT)
    parser.add_argument("--sample-output", default=DEFAULT_SAMPLE_OUTPUT)
    parser.add_argument("--sample-meta-output", default=DEFAULT_SAMPLE_META_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE_DEFAULT)
    parser.add_argument("--skip-baseline", action="store_true",
                        help="do not write the committed baseline/sample artifacts (used by tests)")
    parser.add_argument("--check", action="store_true",
                        help="rebuild in-memory and verify byte-identical to an existing --output")
    args = parser.parse_args(argv)

    input_paths = {
        "entries": args.entries,
        "universe": args.universe,
        "universe_occurrences": args.universe_occurrences,
        "appearance_index": args.appearance_index,
        "particle_matrix": args.particle_matrix,
    }
    input_hashes = {name: sha256_file(path) for name, path in input_paths.items()}

    rows, stats, context = build_manifest(
        args.entries, args.universe, args.universe_occurrences,
        args.appearance_index, args.particle_matrix,
    )
    output_hash = sha256_rows(rows)

    if args.check:
        if not args.output or not os.path.exists(args.output):
            print("CHECK FAIL - no existing --output file to compare against")
            return 1
        existing_hash = sha256_file(args.output)
        rebuilt_serialized = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ).encode("utf-8")
        rebuilt_hash = hashlib.sha256(rebuilt_serialized).hexdigest()
        if existing_hash != rebuilt_hash:
            print("CHECK FAIL - rebuilt manifest does not match existing --output byte-for-byte")
            print(f"existing_sha256={existing_hash}")
            print(f"rebuilt_sha256={rebuilt_hash}")
            return 1
        print("CHECK PASS - deterministic rebuild matches existing --output byte-for-byte")
        print(f"rows={len(rows)} sha256={rebuilt_hash}")
        return 0

    if args.output:
        write_jsonl(rows, args.output)
        meta = {
            "schema": SCHEMA,
            "builder": {"id": BUILDER_ID, "version": BUILDER_VERSION},
            "inputs": input_hashes,
            "row_count": len(rows),
            "sha256": output_hash,
        }
        write_pretty_json(meta, args.output + ".meta.json")
        print(f"full manifest written: {os.path.abspath(args.output)}")
        print(f"rows={len(rows)} sha256={output_hash}")

    if not args.skip_baseline:
        baseline = build_baseline(rows, stats, context, input_hashes, output_hash)
        write_pretty_json(baseline, args.baseline_output)
        print(f"baseline written: {os.path.abspath(args.baseline_output)}")

        sample_rows = select_sample(rows, context, args.sample_size)
        write_jsonl(sample_rows, args.sample_output)
        sample_meta = {
            "schema": SCHEMA,
            "builder": {"id": BUILDER_ID, "version": BUILDER_VERSION},
            "source_full_manifest_sha256": output_hash,
            "source_full_manifest_row_count": len(rows),
            "sample_row_count": len(sample_rows),
            "sample_selection_rule": SAMPLE_SELECTION_RULE,
            "sample_sha256": sha256_rows(sample_rows),
        }
        write_pretty_json(sample_meta, args.sample_meta_output)
        print(f"sample written: {os.path.abspath(args.sample_output)} rows={len(sample_rows)}")

    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
