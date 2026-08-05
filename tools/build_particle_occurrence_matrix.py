#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the complete particle-occurrence CANDIDATE matrix for p001-p100.

Consumes the example-ayah universe (tools/build_example_ayah_universe.py) and
the owner-approved P-00..P-05 membership table (renumber 2026-08-05).  Emits one row per
particle-entry x candidate-occurrence: every canonical occurrence in the
universe whose corpus-facing displayed surface could realise the particle,
either as a free word (exact / normalized match) or as a visible clitic
prefix on a host (heuristic CANDIDATE only).

Nothing here is a certification: ``certified`` is always ``"none"``,
``function_candidates`` is a candidate lattice (never a winner), and
homograph-capable rows carry their scholar-2-vote blocker.  Candidate
discovery deliberately uses normalization for recall and marks the match
basis on every row.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.build_example_ayah_universe import (  # noqa: E402
    loose_key, strict_key, _read_jsonl)

SCHEMA = "qamus.particle_occurrence_matrix.v1"
BUILDER_VERSION = "1.0.0"

DEFAULT_UNIVERSE = os.path.join(
    REPO_ROOT, "qamus", "lattice", "example-ayah-universe.jsonl")
DEFAULT_MEMBERSHIP = os.path.join(
    REPO_ROOT, "qamus", "data", "particle-tranche-membership.json")
DEFAULT_ENTRIES = os.path.join(REPO_ROOT, "qamus", "data", "current", "entries.jsonl")
DEFAULT_FUNCWORD_RULES = os.path.join(
    REPO_ROOT, "nahw", "rules", "funcword-homograph-prepass-rules.json")
DEFAULT_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "lattice", "particle-occurrence-matrix.jsonl")

# Single-letter proclitics whose entry headwords end with tatweel; the strict
# key of the clitic is matched as a PREFIX of the token's strict key.  This is
# a recall heuristic: every hit is a candidate, never a determination.
_CLITIC_SOURCE_KEYS = {
    "p002": "ب",   # bi-
    "p003": "ت",   # oath ta-
    "p004": "س",   # future sa-
    "p005": "ف",   # fa-
    "p006": "ك",   # ka-
    "p007": "ل",   # li-/la-
    "p009": "و",   # wa-
    "p010": "ال",  # definite article
}
# p001 (interrogative hamza) and p008 (emphatic nun) are affix-shaped but not
# strict-prefix discoverable without morphology; they participate as free
# matches only and their discovery gap is reported.
_AFFIX_NOT_DISCOVERABLE = {"p001", "p008"}

# Proclitic letters that may precede a free particle inside one displayed
# token (e.g. وَكَأَيِّن hosts كَأَيِّن behind wa-).  Recall tier only.
_PROCLITIC_LETTERS = ("و", "ف", "ب", "ك", "ل", "س")


def _proclitic_strips(token_key):
    """Yield (carried_prefix, remainder) for up to two stripped proclitics."""
    seen = set()
    frontier = [("", token_key)]
    for _depth in range(2):
        next_frontier = []
        for carried, rest in frontier:
            for letter in _PROCLITIC_LETTERS:
                if rest.startswith(letter) and len(rest) > len(letter):
                    candidate = (carried + letter, rest[len(letter):])
                    if candidate not in seen:
                        seen.add(candidate)
                        next_frontier.append(candidate)
                        yield candidate
        frontier = next_frontier

PAGE_CLASSES = ("selected_on_p", "context_on_p", "context_on_v", "context_on_n")


def _load_membership(path):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload.get("membership") or []
    if len(rows) != 100:
        raise ValueError(f"membership must have 100 rows, found {len(rows)}")
    return rows


def _entry_forms(entry):
    """Strict keys of every declared surface form + headword variants + senses."""
    keys = set()
    for headword_part in str(entry.get("headword") or "").split("/"):
        key = strict_key(headword_part.strip())
        if key:
            keys.add(key)
    for usage in entry.get("usage") or []:
        for form in usage.get("forms") or []:
            for part in str(form).split("/"):
                key = strict_key(part.strip())
                if key:
                    keys.add(key)
    for sense in entry.get("senses") or []:
        key = strict_key(str(sense.get("ar") or ""))
        if key:
            keys.add(key)
    return keys


def _sense_candidates(entry):
    return [
        {"n": sense.get("n"), "ar": sense.get("ar"), "gloss": sense.get("gloss")}
        for sense in entry.get("senses") or []
    ]


def _load_funcword_rules(path):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    surface_rules = defaultdict(list)
    for rule in payload.get("rules") or []:
        rule_id = rule.get("rule_id")
        for surface in rule.get("exact_surfaces") or []:
            surface_rules[surface].append(rule_id)
    return surface_rules


def _function_candidates(membership_row):
    family = str(membership_row.get("function_family") or "")
    candidates = [family]
    if family.startswith("homograph:"):
        detail = family[len("homograph:"):].strip()
        for part in re.split(r"[/,]| vs ", detail):
            part = part.strip(" ()")
            if part and part not in candidates:
                candidates.append(part)
    return candidates


def build_matrix(universe_rows, membership, entries_by_id, funcword_rules):
    """Return (matrix_rows, meta)."""
    particles = []
    for row in membership:
        entry = entries_by_id.get(row["entry_id"])
        if entry is None:
            raise ValueError(f"membership entry missing from store: {row['entry_id']}")
        free_keys = _entry_forms(entry)
        particles.append({
            "membership": row,
            "entry": entry,
            "free_keys": free_keys,
            "loose_free_keys": {loose_key(key) for key in free_keys} - {""},
            "clitic_prefix": _CLITIC_SOURCE_KEYS.get(row["source_key"]),
            "senses": _sense_candidates(entry),
        })

    particle_entry_ids = {p["membership"]["entry_id"] for p in particles}
    states = {}
    stats = Counter()
    unaligned_candidates = Counter()

    for urow in universe_rows:
        if urow.get("word_class") == "pause_mark":
            continue
        token_key = strict_key(urow.get("displayed_surface") or "")
        if not token_key:
            continue
        loc = urow.get("canonical_loc")
        host_entry_type = urow.get("entry_type")
        host_entry_id = urow.get("entry_id")
        raw_surface = urow.get("displayed_surface") or ""
        for particle in particles:
            mrow = particle["membership"]
            source_key = mrow["source_key"]
            match = None
            if token_key in particle["free_keys"]:
                basis = "exact" if raw_surface in {
                    part.strip()
                    for usage in particle["entry"].get("usage") or []
                    for form in usage.get("forms") or []
                    for part in str(form).split("/")
                } else "normalized"
                match = {"kind": "free", "basis": basis, "host": None}
            elif particle["clitic_prefix"]:
                prefix = particle["clitic_prefix"]
                if (token_key.startswith(prefix)
                        and len(token_key) > len(prefix)):
                    match = {
                        "kind": "clitic",
                        "basis": "clitic_prefix_normalized",
                        "host": token_key[len(prefix):],
                    }
            if match is None and loose_key(raw_surface) in particle["loose_free_keys"]:
                match = {"kind": "free", "basis": "loose", "host": None}
            if match is None and not particle["clitic_prefix"]:
                for carried, remainder in _proclitic_strips(token_key):
                    if remainder in particle["free_keys"]:
                        match = {
                            "kind": "free_with_proclitic",
                            "basis": "normalized_after_proclitic_strip",
                            "host": None,
                            "carried_proclitic": carried,
                        }
                        break
            if match is None:
                continue
            if not loc:
                unaligned_candidates[source_key] += 1
                stats["unaligned_candidate_appearances"] += 1
                continue
            if host_entry_type == "p":
                if host_entry_id == mrow["entry_id"] and urow.get("selected"):
                    page_class = "selected_on_p"
                else:
                    page_class = "context_on_p"
            elif host_entry_type == "v":
                page_class = "context_on_v"
            else:
                page_class = "context_on_n"
            key = (source_key, loc)
            state = states.get(key)
            if state is None:
                state = states[key] = {
                    "surface": raw_surface,
                    "match": match,
                    "classes": Counter(),
                    "appearance_ids": [],
                    "on_own_page": False,
                }
            state["classes"][page_class] += 1
            state["appearance_ids"].append(urow["appearance_id"])
            if host_entry_id == mrow["entry_id"]:
                state["on_own_page"] = True
            stats["candidate_appearances"] += 1

    by_particle = {p["membership"]["source_key"]: p for p in particles}
    rows = []
    for (source_key, loc) in sorted(
            states,
            key=lambda k: (k[0], tuple(int(x) for x in k[1].split(":")))):
        state = states[(source_key, loc)]
        particle = by_particle[source_key]
        mrow = particle["membership"]
        blockers = []
        if mrow.get("scholar_two_vote_required"):
            blockers.append("homograph_requires_scholar_two_vote")
        if state["match"]["kind"] == "clitic":
            blockers.append("clitic_host_segmentation_unverified")
        if state["match"]["basis"] in ("normalized", "clitic_prefix_normalized",
                                       "normalized_after_proclitic_strip"):
            blockers.append("match_basis_normalized_requires_diacritic_check")
        if state["match"]["basis"] == "loose":
            blockers.append("match_basis_loose_requires_orthography_check")
        if state["match"]["kind"] == "free_with_proclitic":
            blockers.append("carried_proclitic_segmentation_unverified")
        row = {
            "matrix_id": f"{source_key}:{loc}",
            "particle_entry_id": mrow["entry_id"],
            "particle_source_key": source_key,
            "headword": mrow["headword"],
            "tranche": mrow["tranche"],
            "canonical_loc": loc,
            "occurrence_id": f"quran:{loc}",
            "surface": state["surface"],
            "match_kind": state["match"]["kind"],
            "match_basis": state["match"]["basis"],
            "clitic_or_free_candidate": (
                "clitic" if state["match"]["kind"] == "clitic" else "free"),
            "host_visible": state["match"]["host"],
            "carried_proclitic": state["match"].get("carried_proclitic"),
            "candidate_entry": mrow["entry_id"],
            "candidate_senses": particle["senses"],
            "page_appearances": {
                cls: state["classes"].get(cls, 0) for cls in PAGE_CLASSES
                if state["classes"].get(cls, 0)
            },
            "appearance_count": sum(state["classes"].values()),
            "appearance_ids": state["appearance_ids"],
            "certified": "none",
            "function_candidates": _function_candidates(mrow),
            "homograph_alternatives": sorted({
                rule_id
                for surface, rule_ids in funcword_rules.items()
                if strict_key(surface) == strict_key(state["surface"])
                for rule_id in rule_ids
            }),
            "evidence_status": (
                "candidate_linked" if state["on_own_page"] else "discovered"),
        }
        if blockers:
            row["blockers"] = blockers
        rows.append(row)

    per_particle = defaultdict(Counter)
    per_tranche = defaultdict(Counter)
    for particle in particles:
        per_particle[particle["membership"]["source_key"]]["occurrences"] += 0
        per_tranche[particle["membership"]["tranche"]]["occurrences"] += 0
    for row in rows:
        source_key = row["particle_source_key"]
        tranche = row["tranche"]
        per_particle[source_key]["occurrences"] += 1
        per_tranche[tranche]["occurrences"] += 1
        for cls, count in row["page_appearances"].items():
            per_particle[source_key][cls] += count
            per_tranche[tranche][cls] += count

    meta = {
        "schema": SCHEMA,
        "builder": {"id": "build_particle_occurrence_matrix",
                    "version": BUILDER_VERSION},
        "inputs": {
            "universe": "qamus/lattice/example-ayah-universe.jsonl",
            "membership": "qamus/data/particle-tranche-membership.json",
            "entries": "qamus/data/current/entries.jsonl",
            "funcword_rules": "nahw/rules/funcword-homograph-prepass-rules.json",
        },
        "totals": {
            "particles": len(particles),
            "matrix_rows": len(rows),
            "candidate_appearances": stats["candidate_appearances"],
            "unaligned_candidate_appearances":
                stats["unaligned_candidate_appearances"],
            "page_class_appearances": {
                cls: sum(row["page_appearances"].get(cls, 0) for row in rows)
                for cls in PAGE_CLASSES
            },
        },
        "per_tranche": {k: dict(v) for k, v in sorted(per_tranche.items())},
        "per_particle": {k: dict(v) for k, v in sorted(per_particle.items())},
        "unaligned_candidates_by_particle": dict(sorted(
            unaligned_candidates.items())),
        "affix_not_discoverable": sorted(_AFFIX_NOT_DISCOVERABLE),
        "notes": [
            "CANDIDATE lattice only: no row is certified; function_candidates "
            "is a list, never a winner; clitic-vs-free is a heuristic "
            "candidate classification pending segmentation evidence.",
            "Candidate scope is the example-ayah universe (displayed words on "
            "all 2,092 entry pages), NOT the whole corpus and NOT only the "
            "984 rendered particle-page context spans.",
            "p001 (interrogative hamza) and p008 (emphatic nun) are "
            "affix-shaped and not strict-prefix discoverable; they surface "
            "as free matches only (discovery gap recorded).",
        ],
    }
    return rows, meta


def write_jsonl(rows, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")))
            handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", default=DEFAULT_UNIVERSE)
    parser.add_argument("--membership", default=DEFAULT_MEMBERSHIP)
    parser.add_argument("--entries", default=DEFAULT_ENTRIES)
    parser.add_argument("--funcword-rules", default=DEFAULT_FUNCWORD_RULES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    membership = _load_membership(args.membership)
    entries_by_id = {
        str(entry.get("id") or ""): entry
        for entry in _read_jsonl(args.entries)
    }
    funcword_rules = _load_funcword_rules(args.funcword_rules)
    rows, meta = build_matrix(
        _read_jsonl(args.universe), membership, entries_by_id, funcword_rules)

    output = os.path.abspath(args.output)
    base, _ext = os.path.splitext(output)
    write_jsonl(rows, output)
    with open(base + ".meta.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    print("particle occurrence matrix built")
    print(json.dumps(meta["totals"], ensure_ascii=False, sort_keys=True))
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
