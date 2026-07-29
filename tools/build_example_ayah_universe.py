#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the canonical example-ayah occurrence universe.

One row per DISPLAYED-WORD APPEARANCE across every example card of every
committed Qamus entry (all sections: p/v/n), joined to canonical Quran word
locations via a three-tier deterministic alignment (exact surface, strict
normalized, loose orthographic) with per-word fallback.  A companion
occurrence rollup preserves the unique-occurrence grain (never collapse the
unique-occurrence vs appearance denominators).

Extends — does not replace — the existing machinery:

* ``qamus/indexes/occurrence-appearances.jsonl`` stays the canonical
  reader/entry-example appearance index over the whitelist surface; this
  universe adds the per-displayed-word grain (context words included) that the
  whitelist-derived index cannot see, and backlinks into it (``wbw_present``,
  ``appearance_index_entry_linked``).
* VN tranche labels reuse the VNMAP derived proposal map
  (``tools/build_entry_card_word_ledger._proposal_tranche_map``); particle
  entries take their owner-approved P-00..P-03 label from
  ``qamus/data/particle-tranche-membership.json``. The VN-side labels are the
  balanced-partition DERIVED PROPOSAL in the ``VNPROP-xx`` namespace (renamed
  from bare ``VN-xx`` per the 2026-07-29 owner ruling, VN-UNLOCK-PROOF
  Finding 0); they are NOT the contract window ids ``VN-00``..``VN-23``.

All inputs are committed, public-safe repo artifacts; no network, no live
mutation.  Reproducible: same inputs -> byte-identical outputs.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.normalize_ar import norm_strict  # noqa: E402
from tools.build_entry_card_word_ledger import _proposal_tranche_map  # noqa: E402

SCHEMA = "qamus.example_ayah_universe.v1"
BUILDER_VERSION = "1.0.0"

DEFAULT_ENTRIES = os.path.join(REPO_ROOT, "qamus", "data", "current", "entries.jsonl")
DEFAULT_LOC_SURFACE = os.path.join(
    REPO_ROOT, "qamus", "indexes", "quran-loc-surface", "index.jsonl")
DEFAULT_APPEARANCE_INDEX = os.path.join(
    REPO_ROOT, "qamus", "indexes", "occurrence-appearances.jsonl")
DEFAULT_MEMBERSHIP = os.path.join(
    REPO_ROOT, "qamus", "data", "particle-tranche-membership.json")
DEFAULT_OUTPUT = os.path.join(
    REPO_ROOT, "qamus", "lattice", "example-ayah-universe.jsonl")

# Quranic annotation marks (pause marks, small high/low signs, sajdah etc.)
# rendered inside example fragments but absent from the Tanzil word index.
_ANNOTATION_RE = re.compile(r"[ۖ-ۭ]")
# Combining marks + Quranic annotation range, for the loose orthographic tier.
_COMBINING_RE = re.compile(r"[ً-ٰۖ-ۭ࣓-ࣿٓ-ٕ]")
_LOC_RE = re.compile(r"^\d+:\d+:\d+$")
_SOURCE_KEY_RE = re.compile(r"^([pvn])0*(\d+)$")


def strict_key(word):
    """Hamza-seat-preserving strict key with annotation marks removed."""
    return norm_strict(_ANNOTATION_RE.sub("", word or ""))


def loose_key(word):
    """Loose orthographic key: recall tier only, never a certification basis."""
    w = word or ""
    w = w.replace("ىٰ", "ا")  # alif-maqsura + dagger alif -> alif
    w = _COMBINING_RE.sub("", w)
    for src, dst in (
        ("ٱ", "ا"), ("أ", "ا"), ("إ", "ا"),
        ("آ", "ا"), ("ى", "ي"), ("ؤ", "و"),
        ("ئ", "ي"), ("ء", ""), ("ـ", ""),
        ("ة", "ت"),
    ):
        w = w.replace(src, dst)
    return w


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            yield value


def _entry_type(entry):
    for key in entry.get("source_keys") or []:
        match = _SOURCE_KEY_RE.fullmatch(str(key).strip())
        if match:
            return match.group(1)
    section = str(entry.get("section") or "").strip().lower()
    return {"particle": "p", "verb": "v", "noun": "n"}.get(section, "?")


def _entry_source_key(entry):
    for key in entry.get("source_keys") or []:
        if _SOURCE_KEY_RE.fullmatch(str(key).strip()):
            return str(key).strip()
    return ""


def _parse_ref(ref):
    """Return (surah, ayah, word_or_None) or None."""
    value = str(ref or "").strip()
    for prefix in ("quran:", "wbw:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    parts = value.split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    return (numbers[0], numbers[1], numbers[2] if len(numbers) == 3 else None)


def load_ayah_index(loc_surface_rows):
    ayat = defaultdict(list)
    for row in loc_surface_rows:
        loc = str(row.get("loc") or "")
        if not _LOC_RE.fullmatch(loc):
            raise ValueError(f"invalid loc in loc-surface index: {loc!r}")
        surah, ayah, word = (int(part) for part in loc.split(":"))
        ayat[(surah, ayah)].append((word, str(row.get("surface") or "")))
    for key in ayat:
        ayat[key].sort()
    return ayat


def _contiguous_offsets(fragment_keys, ayah_keys):
    n = len(fragment_keys)
    if n == 0 or n > len(ayah_keys):
        return []
    return [
        index for index in range(len(ayah_keys) - n + 1)
        if ayah_keys[index:index + n] == fragment_keys
    ]


def align_card(words, ayah_tokens):
    """Align displayed word tokens against one ayah's (word_no, surface) list.

    Returns (assignments, card_basis) where assignments[i] is
    (word_no or None, match_basis).  Tiers: contiguous exact -> contiguous
    strict -> contiguous loose -> per-word unique strict -> per-word unique
    loose -> unaligned.
    """
    surfaces = [surface for _no, surface in ayah_tokens]
    numbers = [no for no, _surface in ayah_tokens]
    for tier, key_fn in (
        ("exact", lambda w: w),
        ("strict", strict_key),
        ("loose", loose_key),
    ):
        fragment_keys = [key_fn(word) for word in words]
        ayah_keys = [key_fn(surface) for surface in surfaces]
        offsets = _contiguous_offsets(fragment_keys, ayah_keys)
        if len(offsets) == 1:
            offset = offsets[0]
            assignments = []
            for position, word in enumerate(words):
                token_index = offset + position
                if word == surfaces[token_index]:
                    basis = "exact"
                elif strict_key(word) == strict_key(surfaces[token_index]):
                    basis = "strict" if tier != "exact" else "exact"
                else:
                    basis = "loose"
                assignments.append((numbers[token_index], basis))
            return assignments, f"contiguous_{tier}"
        if len(offsets) > 1:
            return ([(None, "ambiguous")] * len(words)), f"ambiguous_{tier}"

    assignments = []
    strict_index = defaultdict(list)
    loose_index = defaultdict(list)
    for no, surface in ayah_tokens:
        strict_index[strict_key(surface)].append(no)
        loose_index[loose_key(surface)].append(no)
    for word in words:
        candidates = strict_index.get(strict_key(word), [])
        if len(candidates) == 1:
            assignments.append((candidates[0], "strict_word_unique"))
            continue
        loose_candidates = loose_index.get(loose_key(word), [])
        if len(loose_candidates) == 1:
            assignments.append((loose_candidates[0], "loose_word_unique"))
        elif candidates or loose_candidates:
            assignments.append((None, "ambiguous"))
        else:
            assignments.append((None, "unaligned"))
    return assignments, "per_word_fallback"


def _usage_forms(usage):
    keys = set()
    for form in usage.get("forms") or []:
        for part in str(form).split("/"):
            key = strict_key(part.strip())
            if key:
                keys.add(key)
    return keys


def _sense_index(usage, ordinal):
    sense = usage.get("sense")
    if isinstance(sense, int) and sense > 0:
        return sense
    return ordinal + 1


def build_universe(entries, ayat, appearance_index, membership, tranche_map):
    """Return (appearance_rows, occurrence_rows, meta)."""
    appearance_by_loc = {}
    for record in appearance_index:
        appearance_by_loc[record["loc"]] = set(record.get("entry_relationships") or [])

    particle_tranche = {
        row["entry_id"]: row["tranche"] for row in membership.get("membership") or []
    }

    rows = []
    occurrence_states = defaultdict(lambda: {"appearance_ids": [], "entry_ids": set(),
                                             "selected": 0, "context": 0})
    stats = Counter()
    card_basis_hist = Counter()
    match_basis_hist = Counter()
    pages = set()
    cards = 0

    for entry in sorted(entries, key=lambda e: str(e.get("id") or "")):
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        source_key = _entry_source_key(entry)
        entry_type = _entry_type(entry)
        if entry_type == "p":
            tranche = particle_tranche.get(entry_id)
            tranche_kind = "P"
        else:
            tranche = tranche_map.get(entry_id)
            tranche_kind = "VN"
        has_card = False
        for usage_index, usage in enumerate(entry.get("usage") or []):
            sense_index = _sense_index(usage, usage_index)
            form_keys = _usage_forms(usage)
            for card_index, example in enumerate(usage.get("examples") or []):
                cards += 1
                has_card = True
                fragment = str(example.get("ar") or "")
                tokens = fragment.split()
                fragment_hash = hashlib.sha256(
                    fragment.encode("utf-8")).hexdigest()[:12]
                backlink = (
                    f"qamus:{entry_id}#field=usage[{usage_index}]"
                    f".examples[{card_index}]"
                )
                ref = _parse_ref(example.get("ref"))
                ayah_tokens = ayat.get((ref[0], ref[1])) if ref else None
                word_tokens = [
                    (position, token) for position, token in enumerate(tokens)
                    if strict_key(token) or loose_key(token)
                ]
                if ref and ayah_tokens:
                    assignments, card_basis = align_card(
                        [token for _p, token in word_tokens], ayah_tokens)
                elif ref:
                    assignments = [(None, "ayah_missing")] * len(word_tokens)
                    card_basis = "ayah_missing"
                else:
                    assignments = [(None, "ref_unparsed")] * len(word_tokens)
                    card_basis = "ref_unparsed"
                card_basis_hist[card_basis] += 1
                assignment_by_position = {
                    word_tokens[i][0]: assignments[i]
                    for i in range(len(word_tokens))
                }
                for position, token in enumerate(tokens):
                    appearance_id = (
                        f"{entry_id}:u{usage_index}:x{card_index}:w{position}"
                    )
                    display_local_loc = f"u{usage_index}.x{card_index}.w{position}"
                    is_word = position in assignment_by_position
                    row = {
                        "appearance_id": appearance_id,
                        "entry_id": entry_id,
                        "source_key": source_key,
                        "entry_type": entry_type,
                        "sense_index": sense_index,
                        "usage_index": usage_index,
                        "card_index": card_index,
                        "card_ref": str(example.get("ref") or ""),
                        "source_card_backlink": backlink,
                        "display_local_loc": display_local_loc,
                        "displayed_surface": token,
                        "displayed_fragment_hash": fragment_hash,
                        "card_token_count": len(tokens),
                    }
                    if tranche:
                        row["tranche_kind"] = tranche_kind
                        row["tranche"] = tranche
                    if not is_word:
                        row["word_class"] = "pause_mark"
                        row["match_basis"] = "not_a_word"
                        stats["pause_mark_tokens"] += 1
                        rows.append(row)
                        continue
                    stats["displayed_words"] += 1
                    word_no, basis = assignment_by_position[position]
                    row["match_basis"] = basis
                    match_basis_hist[basis] += 1
                    selected = strict_key(token) in form_keys
                    row["selected"] = selected
                    if selected:
                        stats["selected_words"] += 1
                    else:
                        stats["context_words"] += 1
                    if word_no is not None and ref:
                        loc = f"{ref[0]}:{ref[1]}:{word_no}"
                        row["canonical_loc"] = loc
                        wbw_present = loc in appearance_by_loc
                        row["wbw_present"] = wbw_present
                        if wbw_present:
                            row["appearance_index_entry_linked"] = (
                                entry_id in appearance_by_loc[loc]
                            )
                        row["crosswalk"] = "resolved"
                        stats["aligned_words"] += 1
                        state = occurrence_states[loc]
                        state["appearance_ids"].append(appearance_id)
                        state["entry_ids"].add(entry_id)
                        state["selected" if selected else "context"] += 1
                    else:
                        row["canonical_loc"] = None
                        row["crosswalk"] = "missing"
                        row["blockers"] = [f"alignment_{basis}"]
                        stats["unaligned_words"] += 1
                    rows.append(row)
        if has_card:
            pages.add(entry_id)

    def _loc_sort(loc):
        return tuple(int(part) for part in loc.split(":"))

    occurrence_rows = []
    for loc in sorted(occurrence_states, key=_loc_sort):
        state = occurrence_states[loc]
        occurrence_rows.append({
            "occurrence_id": f"quran:{loc}",
            "canonical_loc": loc,
            "appearance_count": len(state["appearance_ids"]),
            "appearance_ids": state["appearance_ids"],
            "entry_ids": sorted(state["entry_ids"]),
            "selected_appearances": state["selected"],
            "context_appearances": state["context"],
        })

    meta = {
        "schema": SCHEMA,
        "builder": {"id": "build_example_ayah_universe", "version": BUILDER_VERSION},
        "inputs": {
            "entries": "qamus/data/current/entries.jsonl",
            "loc_surface": "qamus/indexes/quran-loc-surface/index.jsonl",
            "appearance_index": "qamus/indexes/occurrence-appearances.jsonl",
            "particle_membership": "qamus/data/particle-tranche-membership.json",
        },
        "totals": {
            "entries": len({str(e.get("id") or "") for e in entries} - {""}),
            "pages_with_cards": len(pages),
            "cards": cards,
            "displayed_tokens": len(rows),
            "displayed_words": stats["displayed_words"],
            "pause_mark_tokens": stats["pause_mark_tokens"],
            "selected_words": stats["selected_words"],
            "context_words": stats["context_words"],
            "aligned_words": stats["aligned_words"],
            "unaligned_words": stats["unaligned_words"],
            "unique_occurrences": len(occurrence_rows),
            "appearances_at_occurrences": sum(
                row["appearance_count"] for row in occurrence_rows),
        },
        "card_alignment_basis": dict(sorted(card_basis_hist.items())),
        "word_match_basis": dict(sorted(match_basis_hist.items())),
        "notes": [
            "One row per displayed-token appearance; pause-mark tokens carry "
            "word_class=pause_mark and are excluded from word/occurrence "
            "denominators.",
            "The occurrence rollup (.occurrences.jsonl) preserves the "
            "unique-occurrence grain; unique_occurrences and "
            "appearances_at_occurrences are DIFFERENT denominators by design.",
            "loose/loose_word_unique bases are recall-tier candidates only; "
            "they are never a certification basis.",
            "The displayed fragment text is addressable via "
            "source_card_backlink into the committed entry store; "
            "displayed_fragment_hash = sha256(ar)[:12].",
        ],
        "derived_fields": {
            "occurrence_id": "'quran:' + canonical_loc (aligned rows only)",
            "wbw_loc": "canonical_loc when wbw_present is true",
            "rendered_span_target": (
                "'rendered-span:' + (source_key or entry_id) + ':' + "
                "display_local_loc + ':' + canonical_loc (aligned rows only)"
            ),
            "crosswalk": (
                "'resolved' == display_local_to_canonical crosswalk present; "
                "'missing' == display_local_to_canonical_crosswalk_missing"
            ),
        },
    }
    return rows, occurrence_rows, meta


def write_jsonl(rows, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")))
            handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", default=DEFAULT_ENTRIES)
    parser.add_argument("--loc-surface", default=DEFAULT_LOC_SURFACE)
    parser.add_argument("--appearance-index", default=DEFAULT_APPEARANCE_INDEX)
    parser.add_argument("--membership", default=DEFAULT_MEMBERSHIP)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    entries = list(_read_jsonl(args.entries))
    ayat = load_ayah_index(_read_jsonl(args.loc_surface))
    appearance_index = list(_read_jsonl(args.appearance_index))
    with open(args.membership, encoding="utf-8") as handle:
        membership = json.load(handle)
    tranche_map = _proposal_tranche_map(entries)

    rows, occurrence_rows, meta = build_universe(
        entries, ayat, appearance_index, membership, tranche_map)

    output = os.path.abspath(args.output)
    base, _ext = os.path.splitext(output)
    write_jsonl(rows, output)
    write_jsonl(occurrence_rows, base + ".occurrences.jsonl")
    with open(base + ".meta.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    print("example-ayah universe built")
    print(json.dumps(meta["totals"], ensure_ascii=False, sort_keys=True))
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
