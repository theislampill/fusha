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
    surface index; the closest committed proxy for live payload posture)
  * ``qamus/lattice/particle-occurrence-matrix.jsonl``    (candidate particle
    fact/function lattice; the closest committed proxy for Nahw/colour/hover
    fact identity)

The manifest never fabricates closure: every disposition is either grounded
in one of the above committed authorities or reports an explicit reason it
could not be measured.  No network, no live mutation.  Deterministic:
same committed inputs -> byte-identical output.
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
BUILDER_VERSION = "1.0.0"

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
CERTIFIED_MATCH_TIERS = {"exact", "strict", "strict_word_unique"}
RECALL_ONLY_TIERS = {"loose", "loose_word_unique"}
ARTICLE_RE = re.compile(r"^(?P<conj>[وف])?(?P<article>ال)")
PLURAL_SUFFIXES = ("ات", "ون", "ين")  # ات, ون, ين
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
# Letter ownership (surface-pattern heuristic; general, not hand-authored)
# ---------------------------------------------------------------------------

def analyze_letter_ownership(displayed_surface):
    b = bare(displayed_surface or "")
    match = ARTICLE_RE.match(b)
    if match:
        article = {
            "present": True,
            "leading_conjunction": match.group("conj"),
            "stem_after_article": b[match.end():],
        }
    else:
        article = {"present": False, "leading_conjunction": None, "stem_after_article": None}

    plural_suffix = None
    stem_before = None
    for suffix in PLURAL_SUFFIXES:
        if b.endswith(suffix) and len(b) > len(suffix):
            plural_suffix = suffix
            stem_before = b[: -len(suffix)]
            break
    plural = {"suffix": plural_suffix, "stem_before_suffix": stem_before}
    reason = (
        f"article={'present' if article['present'] else 'absent'}"
        f"; plural_suffix={plural_suffix or 'none'}"
    )
    return {"article": article, "plural": plural, "status": "measured", "reason": reason}


# ---------------------------------------------------------------------------
# Disposition computation
# ---------------------------------------------------------------------------

def _disp(status, reason, **extra):
    out = {"status": status, "reason": reason}
    out.update(extra)
    return out


def compute_exact_binding(row, entries_by_id):
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_entry_binding")
    entry_id = str(row.get("entry_id") or "").strip()
    if not entry_id:
        return _disp("unresolved", "displayed word appearance carries no entry_id")
    entry = entries_by_id.get(entry_id)
    if entry is None:
        return _disp("unresolved", f"entry_id {entry_id!r} not found in entries.jsonl")
    expected_prefix = SECTION_PREFIX.get(entry["section"])
    row_type = row.get("entry_type")
    if expected_prefix is not None and row_type != expected_prefix:
        return _disp(
            "class_trust_violation",
            f"universe entry_type={row_type!r} but entries.jsonl section="
            f"{entry['section']!r} (expected entry_type={expected_prefix!r})",
        )
    return _disp("bound", f"entry_id resolved to entries.jsonl section={entry['section']!r}")


def compute_surface(row):
    match_basis = row.get("match_basis")
    if match_basis == "not_a_word":
        return _disp("not_applicable", "quranic pause annotation is not a displayed word")
    if not str(row.get("displayed_surface") or "").strip():
        return _disp("missing_surface", "empty displayed_surface field on a word row")
    if match_basis in CERTIFIED_MATCH_TIERS:
        return _disp("certified_tier", f"match_basis={match_basis} is a certification-eligible tier")
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


def compute_nahw(row, attachments):
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_syntax", fact_id=None,
                     function_candidates=None)
    if not attachments:
        return _disp(
            "authority_not_joined_in_closed_inputs",
            "no committed per-token Nahw fact/candidate source is joined for this "
            "appearance (particle-occurrence-matrix has no matching row)",
            fact_id=None, function_candidates=None,
        )
    fact_ids = sorted({r.get("matrix_id") for _, r in attachments if r.get("matrix_id")})
    function_sets = sorted({tuple(r.get("function_candidates") or []) for _, r in attachments})
    certified_values = sorted({r.get("certified") for _, r in attachments})
    all_certified = certified_values and all(v not in (None, "none") for v in certified_values)
    status = "certified" if all_certified else "candidate_uncertified"
    reason = (
        f"{len(attachments)} particle-matrix attachment(s); certified={certified_values}; "
        f"{len(function_sets)} distinct function_candidate set(s)"
    )
    return _disp(status, reason, fact_id=fact_ids, function_candidates=[list(s) for s in function_sets])


def compute_sarf(row, entries_by_id):
    if row.get("word_class") == "pause_mark":
        return _disp("not_applicable", "pause_mark_token_has_no_morphology", fact_id=None)
    entry_id = str(row.get("entry_id") or "").strip()
    entry = entries_by_id.get(entry_id)
    section = entry["section"] if entry else None
    if section != "verb":
        return _disp(
            "not_applicable_non_verb_class",
            f"sarf verbal-morphology facts are scoped to verb-class entries "
            f"(owning entry section={section!r})",
            fact_id=None,
        )
    return _disp(
        "authority_not_joined_in_closed_inputs",
        "no committed per-token sarf segmentation source is joined in this manifest's "
        "closed authority (the whitelist that carries sarf_facts is not a repo artifact); "
        "deferred to the Train A/B sarf fact projector",
        fact_id=None,
    )


def compute_colour_and_hover(row, attachments, appearance_index_row):
    if row.get("word_class") == "pause_mark":
        pause_disp = _disp("not_applicable", "pause_mark_token_has_no_display_payload", fact_id=None)
        return dict(pause_disp), dict(pause_disp)

    fact_id = None
    status = "not_available"
    reason = (
        "no committed colour/hover fact source is joined for this appearance in closed "
        "authority; deferred to the rich-colour/rich-hover batches this manifest feeds"
    )
    if attachments:
        fact_ids = sorted({r.get("matrix_id") for _, r in attachments if r.get("matrix_id")})
        fact_id = fact_ids[0] if len(fact_ids) == 1 else fact_ids
        certified_values = sorted({r.get("certified") for _, r in attachments})
        if certified_values and all(v not in (None, "none") for v in certified_values):
            status = "certified"
            reason = "derived from a certified particle-occurrence-matrix candidate fact"
        else:
            status = "candidate_available_uncertified"
            reason = (
                f"derived from {len(attachments)} uncertified particle-occurrence-matrix "
                f"candidate fact(s) (certified={certified_values}); not yet live payload"
            )
    elif appearance_index_row is not None:
        reason = (
            "occurrence is present in the reader occurrence-appearances index but carries "
            "no colour/hover-bearing fact in this manifest's closed authority"
        )

    colour = _disp(status, reason, fact_id=fact_id)
    hover = _disp(status, reason, fact_id=fact_id)
    if colour["fact_id"] != hover["fact_id"]:  # pragma: no cover - structural invariant
        raise AssertionError("colour/hover fact identity diverged by construction")
    return colour, hover


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
            "no live revocation dependency is recorded there",
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
        return _disp("not_applicable", "no canonical occurrence to carry a live payload (pause mark or unaligned word)")
    if appearance_index_row is None:
        return _disp(
            "no_reader_index_record",
            "occurrence not present in qamus/indexes/occurrence-appearances.jsonl reader "
            "surface; no live payload evidence is available in closed authority",
        )
    surface_kinds = {a.get("surface_kind") for a in appearance_index_row.get("appearances") or []}
    if "reader" in surface_kinds:
        return _disp("reader_surface_live", "reader index carries a reader-surface_kind appearance at this loc")
    return _disp(
        "entry_example_only_not_reader_live",
        "reader index carries only entry_example surface_kind appearances at this loc",
    )


def compute_next_action(word_class, exact_binding, surface, is_fork, payload, nahw, sarf, colour, hover):
    if word_class == "pause_mark":
        return "no_action_non_word_token"
    if exact_binding["status"] != "bound":
        return "repair_entry_binding"
    if surface["status"] in ("unaligned", "ambiguous_alignment", "reference_unparsed", "missing_surface"):
        return "resolve_canonical_alignment"
    if is_fork:
        return "adjudicate_page_local_fork"
    if payload["status"] == "no_reader_index_record":
        return "attach_reader_surface_evidence"
    pending_facts = {"authority_not_joined_in_closed_inputs"}
    if nahw["status"] in pending_facts or sarf["status"] in pending_facts:
        return "await_train_ab_fact_projection"
    if colour["status"] in ("not_available", "candidate_available_uncertified") or \
            hover["status"] in ("not_available", "candidate_available_uncertified"):
        return "author_rich_colour_hover_batch"
    return "ready_for_rich_projection"


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

    # Selected-identity fork detection: same canonical_loc selected by >1 distinct entry.
    selected_entries_by_loc = defaultdict(set)
    for row in universe_rows:
        if row.get("selected") and row.get("canonical_loc"):
            selected_entries_by_loc[row["canonical_loc"]].add(row["entry_id"])
    fork_locs = {loc: sorted(ids) for loc, ids in selected_entries_by_loc.items() if len(ids) > 1}

    output_rows = []
    stats = Counter()
    canary_rows_by_source_key = defaultdict(list)
    seen_appearance_ids = set()

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

        exact_binding = compute_exact_binding(row, entries_by_id)
        surface = compute_surface(row)
        letter_ownership = (
            analyze_letter_ownership(row.get("displayed_surface"))
            if word_class != "pause_mark"
            else {"article": {"present": None, "leading_conjunction": None, "stem_after_article": None},
                  "plural": {"suffix": None, "stem_before_suffix": None},
                  "status": "not_applicable", "reason": "pause_mark_token_has_no_letters"}
        )
        nahw = compute_nahw(row, attachments)
        sarf = compute_sarf(row, entries_by_id)
        colour, hover = compute_colour_and_hover(row, attachments, appearance_index_row)
        reverse_trace = compute_reverse_trace(row)
        revocation_dependency = compute_revocation_dependency(row, appearance_index_row)
        payload = compute_payload(row, appearance_index_row)

        is_fork = bool(canonical_loc and canonical_loc in fork_locs and row.get("selected"))
        next_action = compute_next_action(
            word_class, exact_binding, surface, is_fork, payload, nahw, sarf, colour, hover,
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
                "exact_binding": exact_binding,
                "surface": surface,
                "letter_ownership": letter_ownership,
                "sarf": sarf,
                "nahw": nahw,
                "colour": colour,
                "hover": hover,
                "reverse_trace": reverse_trace,
                "revocation_dependency": revocation_dependency,
                "payload": payload,
                "next_action": next_action,
            },
            "page_local_fork": {
                "is_fork": is_fork,
                "conflicting_entry_ids": fork_locs.get(canonical_loc, []) if is_fork else [],
            },
        }
        output_rows.append(out_row)
        stats["total_rows"] += 1
        stats[f"word_class:{out_row['word_class']}"] += 1
        stats[f"exact_binding:{exact_binding['status']}"] += 1
        stats[f"surface:{surface['status']}"] += 1
        stats[f"nahw:{nahw['status']}"] += 1
        stats[f"sarf:{sarf['status']}"] += 1
        stats[f"colour:{colour['status']}"] += 1
        stats[f"hover:{hover['status']}"] += 1
        stats[f"payload:{payload['status']}"] += 1
        stats[f"revocation_dependency:{revocation_dependency['status']}"] += 1
        stats[f"next_action:{next_action}"] += 1
        if letter_ownership["article"]["present"]:
            stats["letter_ownership:article_present_rows"] += 1
        if letter_ownership["plural"]["suffix"]:
            stats["letter_ownership:plural_suffix_rows"] += 1
        if is_fork:
            stats["page_local_fork:affected_rows"] += 1
        source_key = row.get("source_key")
        if source_key in CANARY_SOURCE_KEYS:
            canary_rows_by_source_key[source_key].append(out_row)

    stats["page_local_fork:selected_multi_entry_locs"] = len(fork_locs)
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

    # AL-DHAKAR / AL-UNTHA definite-article ownership: measured within P099's own
    # example fragments (92:3 "وما خلق الذكر والأنثى"), general article-detection rule.
    article_hits = [
        {"appearance_id": r["appearance_id"], "displayed_surface": r["displayed_surface"],
         "article": r["dispositions"]["letter_ownership"]["article"]}
        for r in p099_rows
        if r["dispositions"]["letter_ownership"]["article"]["present"]
        and r["dispositions"]["letter_ownership"]["article"]["stem_after_article"] in ("ذكر", "أنثى")
    ]
    report["al_dhakar_al_untha_article_ownership"] = {
        "matched_rows": article_hits,
        "status": "measured" if article_hits else "blocked",
        "reason": (
            "definite-article prefix separately measured from stem for AL-DHAKAR/AL-UNTHA "
            "tokens in P099's own 92:3 example"
            if article_hits else
            "no AL-DHAKAR/AL-UNTHA token found among P099's displayed tokens"
        ),
    }

    # AL-SAMAWAT plural/inflection ownership: measured within P099's own 2:284 example.
    plural_hits = [
        {"appearance_id": r["appearance_id"], "displayed_surface": r["displayed_surface"],
         "plural": r["dispositions"]["letter_ownership"]["plural"]}
        for r in p099_rows
        if r["dispositions"]["letter_ownership"]["plural"]["suffix"] == "ات"
        and r["dispositions"]["letter_ownership"]["article"]["present"]
    ]
    report["al_samawat_plural_ownership"] = {
        "matched_rows": plural_hits,
        "status": "measured" if plural_hits else "blocked",
        "reason": (
            "plural suffix separately measured from stem for AL-SAMAWAT in P099's own "
            "2:284 example"
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
    violations = 0
    for row in rows:
        colour = row["dispositions"]["colour"]
        hover = row["dispositions"]["hover"]
        if colour["fact_id"] != hover["fact_id"] or colour["status"] != hover["status"]:
            violations += 1
    return {"checked_rows": len(rows), "violations": violations}


def build_baseline(rows, stats, context, inputs, output_hash):
    section_counts = context["section_counts"]
    entries_by_id = context["entries_by_id"]
    universe_row_count = stats["total_rows"]
    word_rows = stats.get("word_class:word", 0)
    pause_rows = stats.get("word_class:pause_mark", 0)

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
            "aligned_word_rows": stats.get("surface:certified_tier", 0)
            + stats.get("surface:recall_tier_only", 0),
            "unaligned_word_rows": stats.get("surface:unaligned", 0)
            + stats.get("surface:reference_unparsed", 0)
            + stats.get("surface:ambiguous_alignment", 0),
        },
        "disposition_counts": {
            key: value for key, value in sorted(stats.items())
            if ":" in key and key.split(":", 1)[0] in (
                "exact_binding", "surface", "nahw", "sarf", "colour", "hover",
                "payload", "revocation_dependency", "next_action",
            )
        },
        "letter_ownership": {
            "article_present_rows": stats.get("letter_ownership:article_present_rows", 0),
            "plural_suffix_rows": stats.get("letter_ownership:plural_suffix_rows", 0),
        },
        "page_local_fork": {
            "selected_multi_entry_locs": stats.get("page_local_fork:selected_multi_entry_locs", 0),
            "affected_rows": stats.get("page_local_fork:affected_rows", 0),
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

    fork_rows = [r for r in rows if r["page_local_fork"]["is_fork"]]
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
    "page-local-fork appearances (lowest appearance_id first); (3) up to 20 unaligned-word "
    "appearances; (4) up to 20 pause-mark appearances; (5) a fixed-stride fill of remaining "
    "rows across the full manifest until the target sample size is reached. No random sampling."
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
