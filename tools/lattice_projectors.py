#!/usr/bin/env python3
"""Transclusion-lattice projectors (T12).

Certified sarf/nahw SEGMENTATION facts (the deployed public-beta whitelist rows)
are projected deterministically onto byte-exact same-surface corpus occurrences
that are not yet covered. Registered projectors are data-driven (see
``qamus/lattice/registered-projectors.json``): a new @2.1 rule registers by
appending a JSON object whose ``class_predicate`` and ``guards`` resolve to the
named callables below -- no code change when the declarative set suffices.

Invariants (fail-closed):
  * READ-ONLY over the whitelist. Projectors NEVER write the whitelist; they emit
    CANDIDATE projection records compatible with the gated merge_rh_live_packet
    seam and the 2-vote review flow.
  * Forward-only: projections supersede, never overwrite (created_from lineage).
  * Every projection rides ``gate_tier=two_vote_required`` (positive) or
    ``never_auto_resolve`` (negative meta). The known-debt manifest ceiling and
    the renderer completeness gate remain the deploy authorities.
  * A guard violation BLOCKS (state=blocked); a homograph surface ROUTES to
    2-vote (never auto-projects); a Form V/VI derivational-taa' split is blocked
    by the rule-level negative meta-projector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "qamus" / "lattice" / "registered-projectors.json"
PROJECTOR_SCHEMA_PATH = ROOT / "qamus" / "schemas" / "projector-record.schema.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Harakat / tanwin / shadda / sukun / superscript-alef range dropped for
# letter-skeleton comparisons (the derivational-taa' skeleton test).
_MARKS = set(range(0x064B, 0x0653)) | {0x0670, 0x0640}
# Enclitic pronoun roles: a segment carrying one of these AFTER the host is a
# host+enclitic carve (object / subject-marker / possessive / attached pronoun).
_ENCLITIC_ROLE_TOKENS = ("pronoun", "subject_marker", "possessive")
_STEM_ROLES = {"verb_stem", "noun_stem", "proper_noun_stem", "proper_noun"}


class LatticeError(ValueError):
    """Raised when registration or projection fails closed."""


# --------------------------------------------------------------------------- #
# normalization / hashing
# --------------------------------------------------------------------------- #
def norm(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def skeleton(text: str) -> str:
    """Bare consonant skeleton (marks/tatweel removed) for the taa' test."""
    return "".join(ch for ch in norm(text) if ord(ch) not in _MARKS)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def analysis_of(row: Dict[str, Any]) -> Dict[str, Any]:
    """The certified analysis carried by a whitelist row (identity-bearing)."""
    segs = [
        {
            "segment_index": int(s.get("segment_index", i)),
            "role": s.get("role"),
            "label": s.get("label"),
            "surface": norm(s.get("surface", "")),
        }
        for i, s in enumerate(row.get("segments") or [])
    ]
    segs.sort(key=lambda s: s["segment_index"])
    return {"surface": norm(row.get("surface", "")), "segments": segs, "morphline": row.get("morphline", "")}


def row_hash(row: Dict[str, Any]) -> str:
    return _hash(analysis_of(row))


# --------------------------------------------------------------------------- #
# class predicates (named -> data-driven dispatch)
# --------------------------------------------------------------------------- #
def _roles(row: Dict[str, Any]) -> List[str]:
    return [s.get("role", "") for s in (row.get("segments") or [])]


def pred_c1_impf(row: Dict[str, Any]) -> bool:
    ml = row.get("morphline", "") or ""
    roles = _roles(row)
    return "imperfect" in ml and "verb_prefix" in roles and "verb_stem" in roles


def _is_enclitic_role(role: str) -> bool:
    role = role or ""
    return any(tok in role for tok in _ENCLITIC_ROLE_TOKENS) and not role.startswith("independent")


def pred_c5_enclitic(row: Dict[str, Any]) -> bool:
    segs = row.get("segments") or []
    if len(segs) < 2:
        return False
    ordered = sorted(segs, key=lambda s: int(s.get("segment_index", 0)))
    # An enclitic attaches after a host: a pronoun/subject-marker segment that is
    # not the leading segment, with a host (non-enclitic) segment before it.
    for pos, seg in enumerate(ordered):
        if pos > 0 and _is_enclitic_role(seg.get("role", "")):
            return True
    return False


def pred_any_candidate(row: Dict[str, Any]) -> bool:  # negative-meta placeholder
    return True


def pred_tranche1_morphology(policy: Dict[str, Any]) -> bool:
    return policy.get("fact_family") == "sarf"


def pred_tranche1_syntax(policy: Dict[str, Any]) -> bool:
    return policy.get("fact_family") == "nahw"


NAMED_PREDICATES: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "pred_c1_impf": pred_c1_impf,
    "pred_c5_enclitic": pred_c5_enclitic,
    "pred_any_candidate": pred_any_candidate,
    "pred_tranche1_morphology": pred_tranche1_morphology,
    "pred_tranche1_syntax": pred_tranche1_syntax,
}


# --------------------------------------------------------------------------- #
# guards / defeaters (named -> data-driven dispatch)
# Each guard(ctx) -> None (pass) or a dict {resolution, detail}.
#   resolution in {"blocked", "route_two_vote"}.
# --------------------------------------------------------------------------- #
def _form_token(morphline: str) -> Optional[str]:
    """Precisely extract the derived-form token (e.g. 'V', 'VI', 'VIII') from a
    morphline. Substring matching is WRONG here -- 'Form VI' is a substring of
    'Form VIII' and 'Form VII', which would falsely flag Form VIII prefixes."""
    for part in (morphline or "").split("·"):  # split on the middot separator
        part = part.strip()
        if part.startswith("Form "):
            return part[5:].split()[0].rstrip(",")
    return None


def _form56(morphline: str) -> bool:
    return _form_token(morphline) in {"V", "VI"}


def splits_derivational_ta(analysis: Dict[str, Any]) -> bool:
    """True iff a Form V/VI segmentation peels the DERIVATIONAL taa' off the stem.

    The derivational augment of Form V (tafaCCala) and Form VI (tafaaCala) is the
    stem-initial taa'. It is illegal to carve it as its own non-stem segment: the
    tell is a bare-taa' non-stem segment immediately preceding a stem whose own
    skeleton no longer begins with taa' (the stem lost its augment). This does NOT
    fire on a legitimate imperfect person-prefix (which precedes a stem that still
    begins with the derivational taa', e.g. tataCCa...) nor on a plural/feminine
    suffix taa', nor on Form VIII (excluded by the exact form token)."""
    if not _form56(analysis.get("morphline", "")):
        return False
    segs = sorted(analysis.get("segments") or [], key=lambda s: int(s.get("segment_index", 0)))
    for i, seg in enumerate(segs):
        role = seg.get("role", "") or ""
        if role in _STEM_ROLES:
            continue
        # D-1/D-3 (owner 2026-07-16): a taa' segment EXPLICITLY classed as a
        # derivational form-marker (house DER convention) is the desired rich
        # representation of the Form V/VI pattern augment -- distinguished from
        # root radicals and person-prefixes by its class, and therefore NOT an
        # illegal carving. Only misclassified carvings (person-prefix, clitic,
        # generic token classes) remain blocked below.
        if role.startswith("derivative_prefix") or (seg.get("class") or "") == "qg-derivative-prefix":
            continue
        if skeleton(seg.get("surface", "")) != "ت":  # not a bare taa'
            continue
        nxt = next((s for s in segs[i + 1:] if s.get("role") in _STEM_ROLES), None)
        if nxt is None:
            continue  # trailing taa' (e.g. subject/plural suffix) -- not the augment
        if not skeleton(nxt.get("surface", "")).startswith("ت"):
            return True  # taa' peeled off; the stem lost its derivational augment
    return False


def homograph_surface_ambiguity(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx["homograph"]:
        return {
            "resolution": "route_two_vote",
            "detail": "surface carries more than one distinct certified segmentation across the corpus",
        }
    return None


def surface_byte_exact(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if norm(ctx["target_surface"]) != norm(ctx["source_surface"]):
        return {"resolution": "blocked", "detail": "target surface is not NFC byte-exact with the certified source surface"}
    return None


def meta_form56_ta_split(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if splits_derivational_ta(ctx["projected_analysis"]):
        return {"resolution": "blocked", "detail": "Form V/VI derivational taa' would be split (rule-level negative projector)"}
    return None


def construction_match(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    # For a non-homograph byte-exact surface the certified construction transcludes
    # deterministically. When the surface is homographic the homograph guard has
    # already routed it to 2-vote, so this guard defers rather than double-blocking.
    return None


def tranche1_exact_surface(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx["source_row"].get("loc") != ctx["policy"].get("loc"):
        return {"resolution": "blocked", "detail": "source and policy locations differ"}
    if norm(ctx["source_row"].get("surface", "")) != norm(ctx["policy"].get("surface", "")):
        return {"resolution": "blocked", "detail": "source and policy surfaces differ"}
    return None


def tranche1_typed_status(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    status = ctx["policy"].get("status")
    allowed = {"candidate", "unresolved", "source_gap", "producer_pending", "syntax_pending"}
    if status not in allowed:
        return {"resolution": "blocked", "detail": "policy status is not a typed tranche status"}
    blocker = ctx["policy"].get("blocker")
    route = ctx["policy"].get("route")
    if status == "candidate" and (blocker is not None or route is not None):
        return {"resolution": "blocked", "detail": "candidate status cannot carry blocker or route"}
    if status != "candidate" and (not blocker or not isinstance(route, dict)):
        return {"resolution": "blocked", "detail": "queue status requires blocker and typed route"}
    return None


NAMED_GUARDS: Dict[str, Callable[[Dict[str, Any]], Optional[Dict[str, str]]]] = {
    "homograph_surface_ambiguity": homograph_surface_ambiguity,
    "surface_byte_exact": surface_byte_exact,
    "meta_form56_ta_split": meta_form56_ta_split,
    "construction_match": construction_match,
    "tranche1_exact_surface": tranche1_exact_surface,
    "tranche1_typed_status": tranche1_typed_status,
}


def run_tranche1_fixture_projector(
    projector: Dict[str, Any],
    source_row: Dict[str, Any],
    policy: Dict[str, Any],
    fact_ids: List[str],
) -> Dict[str, Any]:
    """Emit a bounded Q7 fixture candidate or typed queue record."""

    predicate = NAMED_PREDICATES[projector["class_predicate"]]
    if not predicate(policy):
        raise LatticeError("tranche fixture policy does not match projector family")
    if not fact_ids or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", value) for value in fact_ids):
        raise LatticeError("tranche fixture output requires valid fact_ids")
    ctx = {"source_row": source_row, "policy": policy}
    for guard_name in projector["guards"]:
        failure = NAMED_GUARDS[guard_name](ctx)
        if failure:
            raise LatticeError("%s: %s" % (guard_name, failure["detail"]))

    registry_entry = projector["registry_entry"]
    status = policy["status"]
    candidate = status == "candidate"
    loc = policy["loc"]
    return {
        "schema": "qamus.tranche1_projector_output.v1",
        "record_type": "candidate_projection" if candidate else "typed_queue_record",
        "loc": loc,
        "surface": source_row["surface"],
        "fact_ids": list(fact_ids),
        "status": status,
        "source_address": {
            "address": "quran:%s / wbw:%s" % (loc, loc),
            "source_kind": "quran_token",
        },
        "materialization_target": {
            "artifact": "public-hover-projections.jsonl" if candidate else "unresolved-queue.jsonl",
            "field": "segments" if candidate else "queue",
            "public_materialization_allowed": False,
            "live_mutation_allowed": False,
        },
        "producer": registry_entry["producer"],
        "projector_id": registry_entry["projector_id"],
        "version": registry_entry["version"],
        "blocker": policy.get("blocker"),
        "route": policy.get("route"),
        "live_mutation_allowed": False,
    }


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
def _validate_registry_entry(entry: Dict[str, Any]) -> List[str]:
    """Validate the embedded projector-record.v1 registry_entry against schema."""
    try:
        from tools import fact_ledger  # reuse the repo's tiny schema validator
    except Exception:
        sys.path.insert(0, str(ROOT))
        from tools import fact_ledger  # type: ignore
    with PROJECTOR_SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    errors: List[str] = []
    fact_ledger._validate_node(entry, schema, "$", errors, schema)
    return errors


def load_registry(path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        reg = json.load(handle)
    if reg.get("schema") != "qamus.lattice.registered_projectors.v1":
        raise LatticeError("unexpected registry schema")
    ids = set()
    for entry in reg.get("registered", []):
        pid = entry.get("projector_id")
        if pid in ids:
            raise LatticeError("duplicate projector_id: " + str(pid))
        ids.add(pid)
        if entry.get("class_predicate") not in NAMED_PREDICATES:
            raise LatticeError("unknown class_predicate for " + str(pid))
        for g in entry.get("guards", []):
            if g not in NAMED_GUARDS:
                raise LatticeError("unknown guard '%s' for %s" % (g, pid))
        re_errors = _validate_registry_entry(entry.get("registry_entry", {}))
        if re_errors:
            raise LatticeError("invalid registry_entry for %s: %s" % (pid, "; ".join(re_errors)))
        if entry["registry_entry"]["projector_id"] != pid:
            raise LatticeError("registry_entry projector_id mismatch for " + str(pid))
    return reg


# --------------------------------------------------------------------------- #
# projection engine
# --------------------------------------------------------------------------- #
def build_homograph_surfaces(whitelist_rows: Iterable[Dict[str, Any]]) -> set:
    """Surfaces bearing >1 distinct certified analysis anywhere in the corpus."""
    by_surface: Dict[str, set] = defaultdict(set)
    for row in whitelist_rows:
        by_surface[norm(row.get("surface", ""))].add(row_hash(row))
    return {surface for surface, hashes in by_surface.items() if len(hashes) > 1}


def _projected_record(
    *,
    projector: Dict[str, Any],
    source_row: Dict[str, Any],
    target_loc: str,
    target_surface: str,
    guards_evaluated: Dict[str, str],
    projection_state: str,
    review_route: str,
) -> Dict[str, Any]:
    src_analysis = analysis_of(source_row)
    projected = dict(src_analysis)
    projected["surface"] = norm(target_surface)
    target_hash = _hash({"loc": target_loc, "analysis": projected})
    return {
        "schema": "qamus.lattice.projection_record.v1",
        "projector_id": projector["projector_id"],
        "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
        "source_fact": {
            "loc": source_row.get("loc"),
            "row_hash": row_hash(source_row),
            "surface": src_analysis["surface"],
            "morphline": src_analysis["morphline"],
            "segments": src_analysis["segments"],
        },
        "target_loc": target_loc,
        "target_row_hash": target_hash,
        "projected_fact": {
            "surface": projected["surface"],
            "segments": projected["segments"],
            "morphline": projected["morphline"],
        },
        "guards_evaluated": guards_evaluated,
        "projection_state": projection_state,
        "review_route": review_route,
        "gate_tier": projector["registry_entry"]["gate_tier"],
        "evidence": [
            {
                "type": "certified_source_occurrence",
                "address": "quran:%s / wbw:%s" % (source_row.get("loc"), source_row.get("loc")),
                "detail": "byte-exact same-surface certified segmentation",
            }
        ],
        "created_note": "deterministic transclusion of certified segmentation to a same-surface uncovered occurrence; candidate only",
        "supersedes": None,
        "created_from": "projector:" + projector["projector_id"],
    }


def run_positive_projector(
    projector: Dict[str, Any],
    whitelist_rows: List[Dict[str, Any]],
    whitelist_locs: set,
    corpus_tokens: List[Tuple[str, str]],
    homograph_surfaces: set,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    predicate = NAMED_PREDICATES[projector["class_predicate"]]
    guards = [(name, NAMED_GUARDS[name]) for name in projector["guards"]]

    sources = [r for r in whitelist_rows if predicate(r)]
    # deterministic representative per surface = lowest loc (surah:ayah:word order)
    rep: Dict[str, Dict[str, Any]] = {}
    for row in sorted(sources, key=lambda r: _loc_key(r.get("loc", ""))):
        rep.setdefault(norm(row.get("surface", "")), row)
    certified_surfaces = set(rep)

    records: List[Dict[str, Any]] = []
    reachable = 0
    auto_candidates = 0
    routed_two_vote = 0
    blocked = Counter()
    for loc, surface in corpus_tokens:
        if loc in whitelist_locs:
            continue
        ns = norm(surface)
        if ns not in certified_surfaces:
            continue
        reachable += 1
        source_row = rep[ns]
        ctx = {
            "homograph": ns in homograph_surfaces,
            "target_surface": surface,
            "source_surface": source_row.get("surface", ""),
            "projected_analysis": {**analysis_of(source_row), "surface": ns},
        }
        guards_evaluated: Dict[str, str] = {}
        blocking = None
        routing = None
        for name, fn in guards:
            outcome = fn(ctx)
            if outcome is None:
                guards_evaluated[name] = "pass"
                continue
            guards_evaluated[name] = outcome["resolution"]
            if outcome["resolution"] == "blocked" and blocking is None:
                blocking = name
            elif outcome["resolution"] == "route_two_vote" and routing is None:
                routing = name
        if blocking:
            projection_state, review_route = "blocked", "none"
            blocked[blocking] += 1
        elif routing:
            projection_state, review_route = "candidate", "two_vote_disambiguation"
            routed_two_vote += 1
        else:
            projection_state, review_route = "candidate", "two_vote_required"
            auto_candidates += 1
        records.append(
            _projected_record(
                projector=projector,
                source_row=source_row,
                target_loc=loc,
                target_surface=surface,
                guards_evaluated=guards_evaluated,
                projection_state=projection_state,
                review_route=review_route,
            )
        )

    instrumentation = {
        "projector_id": projector["projector_id"],
        "kind": projector["kind"],
        "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
        "gate_tier": projector["registry_entry"]["gate_tier"],
        "certified_source_rows": len(sources),
        "distinct_certified_source_surfaces": len(certified_surfaces),
        "reachable_uncovered_rows": reachable,
        "auto_candidates": auto_candidates,
        "routed_two_vote": routed_two_vote,
        "blocked_by_guard": dict(blocked),
        "acceleration_rows_per_source_surface": round(
            (auto_candidates + routed_two_vote) / len(certified_surfaces), 4
        )
        if certified_surfaces
        else None,
    }
    return records, instrumentation


def run_negative_meta(
    projector: Dict[str, Any],
    candidate_records: List[Dict[str, Any]],
    whitelist_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Rule-level negative projector: scans the candidate stream AND the certified
    base, blocking / flagging any Form V/VI derivational-taa' split."""
    blocked_candidates = 0
    for rec in candidate_records:
        analysis = {
            "morphline": rec["projected_fact"]["morphline"],
            "segments": rec["projected_fact"]["segments"],
        }
        if splits_derivational_ta(analysis):
            rec["projection_state"] = "blocked"
            rec["review_route"] = "none"
            rec["guards_evaluated"]["meta_form56_ta_split"] = "blocked"
            blocked_candidates += 1
    base_violation_locs = sorted(
        (r.get("loc") for r in whitelist_rows if splits_derivational_ta(analysis_of(r))),
        key=_loc_key,
    )
    form56_base = sum(1 for r in whitelist_rows if _form56(r.get("morphline", "")))
    return {
        "projector_id": projector["projector_id"],
        "kind": projector["kind"],
        "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
        "gate_tier": projector["registry_entry"]["gate_tier"],
        "form56_certified_base_rows": form56_base,
        "certified_base_ta_split_violations": len(base_violation_locs),
        "certified_base_ta_split_locs": base_violation_locs,
        "candidate_projections_blocked": blocked_candidates,
        "clean_base_proof": not base_violation_locs,
        "note": (
            "certified-base rows where a Form V perfect derivational taa' is carved as a "
            "verb_prefix (stem lost its augment); FLAGGED for owner review under the "
            "never_auto_resolve gate -- the lattice does not modify certified content"
        ),
    }


def _loc_key(loc: str) -> Tuple[int, int, int]:
    try:
        a, b, c = (int(x) for x in loc.split(":"))
        return (a, b, c)
    except Exception:
        return (10**9, 10**9, 10**9)


def load_whitelist(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_corpus(path: Path) -> List[Tuple[str, str]]:
    tokens = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                obj = json.loads(line)
                tokens.append((obj["loc"], obj["surface"]))
    tokens.sort(key=lambda t: _loc_key(t[0]))
    return tokens


def project_all(
    whitelist_path: Path, corpus_path: Path, registry_path: Path = REGISTRY_PATH
) -> Dict[str, Any]:
    registry = load_registry(registry_path)
    whitelist_rows = load_whitelist(whitelist_path)
    whitelist_locs = {r["loc"] for r in whitelist_rows}
    corpus_tokens = load_corpus(corpus_path)
    homograph_surfaces = build_homograph_surfaces(whitelist_rows)

    all_records: List[Dict[str, Any]] = []
    positives: List[Dict[str, Any]] = []
    negative_reports: List[Dict[str, Any]] = []
    for entry in registry["registered"]:
        if entry["kind"] == "positive_transclusion":
            recs, instr = run_positive_projector(
                entry, whitelist_rows, whitelist_locs, corpus_tokens, homograph_surfaces
            )
            all_records.extend(recs)
            positives.append(instr)
    for entry in registry["registered"]:
        if entry["kind"] == "negative_meta":
            negative_reports.append(run_negative_meta(entry, all_records, whitelist_rows))

    return {
        "schema": "qamus.lattice.instrumentation.v1",
        "inputs": {
            "whitelist_rows": len(whitelist_rows),
            "whitelist_sha256_16": hashlib.sha256(whitelist_path.read_bytes()).hexdigest()[:16],
            "corpus_tokens": len(corpus_tokens),
            "uncovered_debt_tokens": len(corpus_tokens) - len(whitelist_locs & {t[0] for t in corpus_tokens}),
            "homograph_surfaces": len(homograph_surfaces),
        },
        "positive_projectors": positives,
        "negative_meta_projectors": negative_reports,
        "records": all_records,
    }


# --------------------------------------------------------------------------- #
# T13 ROOT-INHERITANCE / NOTE-NORMALIZATION / SUFFIX-SEGMENTATION projectors
#
# These extend the lattice with three new projector KINDS that operate WITHIN
# the certified whitelist (not against the uncovered corpus): they inherit a
# CERTIFIED root onto a rootless row by transclusion from an ATTESTED source
# (a qamus entry headword/usage.form, the row's own carrier entry when it is
# form-confirmed, or a certified same-surface / same-stem sibling), normalize
# internal-boilerplate segment notes into deterministic per-class pedagogy, and
# project a feminine-sound-plural / dual segmentation where the remainder is an
# attested stem. Candidate-generation ONLY; every projection stays
# certification_state=candidate until the 2-vote / review gate (DR-2: pattern
# alone NEVER certifies -- inheritance is only ever from an attested source).
# --------------------------------------------------------------------------- #
ENTRIES_DEFAULT = ROOT / "qamus" / "data" / "current" / "entries.jsonl"

# match key: NFC, drop harakat/tanwin/shadda/sukun + Qurʾanic annotation marks +
# tatweel, and map alif-wasla (ٱ) + dagger/superscript alef (ٰ) to plain alif ا.
# Deliberately root-PRESERVING: hamza carriers (أ إ آ) and alif-maqṣūra (ى) are
# kept distinct (they are radical-significant: أمن != امن).
_INH_MARKS = set(range(0x064B, 0x0653)) | set(range(0x06D6, 0x06EE)) | {0x0640}
_INH_ALIF = {0x0671: "ا", 0x0670: "ا"}


def match_key(text: str) -> str:
    t = norm(text)
    return "".join(_INH_ALIF.get(ord(c), c) for c in t if ord(c) not in _INH_MARKS)


_LEXHEAD_LABELS = {"STEM", "TOK"}
_PROPER_ROLES = {"proper_noun", "proper_name", "proper_noun_place"}
_DIVINE_ROLES = {"proper_divine_name", "proper_noun_allah"}
_DIVINE_KEYS = {match_key(x) for x in ("الله", "اللَّه", "الرحمن", "الرحيم")}


def is_lexical_head(seg: Dict[str, Any]) -> bool:
    """A segment that can carry a triliteral lexical root (stem / whole token /
    proper noun) -- as opposed to a clitic, particle or inflectional affix."""
    lab = (seg.get("label") or "").upper()
    role = seg.get("role") or ""
    return lab in _LEXHEAD_LABELS or role.endswith("_stem") or role in _PROPER_ROLES


def is_divine_seg(seg: Dict[str, Any]) -> bool:
    return (seg.get("role") or "") in _DIVINE_ROLES


_ROOT_RE = re.compile(r"root\s+([؀-ۿـ]+(?:\s+[؀-ۿـ]+){1,3})")


def morphline_root(morphline: str) -> Optional[str]:
    """The asserted triliteral/quadriliteral root carried by a morphline
    ('root ك ف ر · ...'), or None when the row asserts no public root."""
    m = _ROOT_RE.search(morphline or "")
    return m.group(1).strip() if m else None


# Entry categories that denote jāmid / frozen function lexemes (particles,
# pronouns, prepositions, letters-with-meaning, question words). A form match
# into one of these routes to human review rather than auto-inheritance.
_JAMID_CATS = {
    "Miscellaneous Particles", "Particles - pronouns", "Particles - demonstratives",
    "Particles - interrogatives", "Particles - relative_pronouns", "Particles - response",
    "Particles - negation", "Particles - urging_and_wishing", "Prepositions - preposition",
    "Question Words - question word", "Question Words - question particle",
    "Letters with Meaning",
}


def is_jamid_category(cat: str) -> bool:
    cat = cat or ""
    return any(cat == c or cat.startswith(c + " -") for c in _JAMID_CATS)


def derivational_pattern(form: str) -> Tuple[Optional[str], Optional[str]]:
    """Deterministic derived-form pattern label from an ATTESTED entry form
    surface. Returns (pattern_name, pos_label) or (None, None). Reads the shape
    of the attested form only -- it never invents morphology the entry does not
    carry (DR-2). Conservative: only the unambiguous mu-/ta- derivations."""
    f = norm(form)
    has_shadda = "ّ" in f
    if f[:1] == "م" and has_shadda:
        return ("مُفَعَّل", "Form II derived participle")
    if f[:2] == "تَ" and has_shadda:
        return ("تَفَعَّل", "Form V stem")
    if f[:2] == "تَ" and f[2:3] == "ا":
        return ("تَفَاعَل", "Form VI stem")
    if f[:1] == "م" and match_key(f)[:1] == "م":
        return ("مَفْعُول/مُفْعَل", "derived participle")
    return (None, None)


# --------------------------------------------------------------------------- #
# T13 predicates + inspectable guards (registered for the schema/registry check)
# --------------------------------------------------------------------------- #
def pred_rootless_lexhead(row: Dict[str, Any]) -> bool:
    if morphline_root(row.get("morphline", "")) is not None:
        return False
    return any(is_lexical_head(s) for s in (row.get("segments") or []))


_BOILERPLATE = (
    "visible piece accounted",
    "no unsupported public source label",
    "function/context contribution preserved",
)


def _is_boilerplate_note(note: str) -> bool:
    n = note or ""
    return any(b in n for b in _BOILERPLATE)


def pred_boilerplate_note(row: Dict[str, Any]) -> bool:
    for s in (row.get("segments") or []):
        if _is_boilerplate_note(s.get("sarf_note")) or _is_boilerplate_note(s.get("nahw_note")):
            return True
    return False


_FEMPL_KEYS = ("ات",)
_DUAL_KEYS = ("ان", "ين")


def pred_suffix_fempl(row: Dict[str, Any]) -> bool:
    if morphline_root(row.get("morphline", "")) is not None:
        return False
    segs = row.get("segments") or []
    if len(segs) != 1 or not is_lexical_head(segs[0]):
        return False
    k = match_key(row.get("surface", ""))
    return any(k.endswith(sfx) and len(k) > len(sfx) + 1 for sfx in _FEMPL_KEYS + _DUAL_KEYS)


# Inspectable guard callables (registry-validated names). The inheritance run
# implements routing internally (it needs multi-source context), so these are
# thin predicates over a ctx dict for the registry contract + unit inspection.
def root_homograph_ambiguity(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx.get("homograph"):
        return {"resolution": "route_two_vote", "detail": "surface bears more than one certified root/analysis"}
    return None


def cross_source_root_conflict(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx.get("conflict"):
        return {"resolution": "blocked", "detail": "attested sources assert different roots for this lexeme"}
    return None


def jamid_contested_review(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx.get("jamid"):
        return {"resolution": "route_two_vote", "detail": "jāmid / contested lexeme -- routed to human review"}
    return None


def within_root_ambiguity_guard(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx.get("within_root_ambiguity"):
        return {"resolution": "route_two_vote", "detail": "the lexeme's forms map to more than one candidate root"}
    return None


def divine_name_exclusion(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx.get("divine"):
        return {"resolution": "blocked", "detail": "divine-name token -- excluded from root inheritance"}
    return None


def radical_taa_homograph(ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if ctx.get("radical_taa"):
        return {"resolution": "route_two_vote", "detail": "trailing ـات may be a radical ت, not a plural suffix"}
    return None


NAMED_PREDICATES.update({
    "pred_rootless_lexhead": pred_rootless_lexhead,
    "pred_boilerplate_note": pred_boilerplate_note,
    "pred_suffix_fempl": pred_suffix_fempl,
})
NAMED_GUARDS.update({
    "root_homograph_ambiguity": root_homograph_ambiguity,
    "cross_source_root_conflict": cross_source_root_conflict,
    "jamid_contested_review": jamid_contested_review,
    "within_root_ambiguity_guard": within_root_ambiguity_guard,
    "divine_name_exclusion": divine_name_exclusion,
    "radical_taa_homograph": radical_taa_homograph,
})


# --------------------------------------------------------------------------- #
# entry + sibling indexes
# --------------------------------------------------------------------------- #
def load_entries(path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def build_entry_index(
    entries: Iterable[Dict[str, Any]]
) -> Tuple[Dict[str, set], Dict[str, Tuple[str, str]]]:
    """match_key(form) -> {(root, entry_id, category, form_surface)} and
    entry_id -> (root, category). Forms come from the headword (slash-split) and
    every usage[].forms entry -- the dictionary's own attestation of the lexeme."""
    form_root: Dict[str, set] = defaultdict(set)
    eid_root: Dict[str, Tuple[str, str]] = {}
    for d in entries:
        root = (d.get("root") or "").strip()
        if not root:
            continue
        eid_root[d.get("id")] = (root, d.get("category", ""))
        forms = set()
        for part in (d.get("headword", "") or "").split("/"):
            forms.add(part.strip())
        for u in (d.get("usage") or []):
            for fm in (u.get("forms") or []):
                for part in str(fm).split("/"):
                    forms.add(part.strip())
        for fm in forms:
            if fm:
                form_root[match_key(fm)].add((root, d.get("id"), d.get("category", ""), fm))
    return form_root, eid_root


def build_root_sibling_index(
    rows: Iterable[Dict[str, Any]]
) -> Tuple[Dict[str, set], Dict[str, set]]:
    """From certified (rooted) whitelist rows: match_key(surface) -> {roots} and
    match_key(lexical-head surface) -> {roots}."""
    surf: Dict[str, set] = defaultdict(set)
    stem: Dict[str, set] = defaultdict(set)
    for r in rows:
        root = morphline_root(r.get("morphline", ""))
        if not root:
            continue
        surf[match_key(r.get("surface", ""))].add(root)
        for s in (r.get("segments") or []):
            if is_lexical_head(s):
                stem[match_key(s.get("surface", ""))].add(root)
    return surf, stem




# Closed-class function words NEVER inherit a content root by surface join
# (Window-1 2026-07-16: the tier-0 join proposed م ن ن for the particle مِن
# from the entry مَنَّ, أ ل ل for لَا, ه م م for هُمْ -- 28/246 of a live
# tranche; every one refused downstream by the MCP مادة gate as حرف/اسم مبني.
# This is the projector-level port of the source-selection closed-class law:
# particles, personal/relative/demonstrative/interrogative pronouns are
# مبنيّ inventory items, not derivations of triliteral content roots).
# Normalized (match_key) bare forms; the و/ف proclitic is stripped before lookup.
_CLOSED_CLASS_FUNCTION_WORDS = frozenset((
    # prepositions / particles
    "من", "في", "عن", "علي", "الي", "حتي", "مع", "لا", "ما", "ان", "الا",
    "لم", "لن", "لو", "بل", "قد", "ثم", "او", "اذ", "اذا", "هل", "الم",
    "اما", "لما", "كي", "لكن", "ليت", "لعل", "سوف", "نعم", "بلي", "كلا",
    # personal pronouns
    "هو", "هي", "هم", "هن", "هما", "انت", "انتم", "انتن", "انا", "نحن",
    "اياك", "اياه", "اياهم", "ايانا",
    # relatives / demonstratives / interrogatives
    "الذي", "التي", "الذين", "اللاتي", "اللائي", "اللذان", "اللتان",
    "ذلك", "ذلكم", "هذا", "هذه", "هذان", "هاتان", "هولاء", "اولئك", "تلك",
    "كيف", "اين", "متي", "اني", "ايان", "كم", "من ذا",
))


def is_closed_class_function_word(key: str) -> bool:
    """True iff the normalized surface (optionally behind a و/ف proclitic)
    is a closed-class function word."""
    if key in _CLOSED_CLASS_FUNCTION_WORDS:
        return True
    for pre in ("و", "ف"):
        if key.startswith(pre) and key[len(pre):] in _CLOSED_CLASS_FUNCTION_WORDS:
            return True
    return False

# --------------------------------------------------------------------------- #
# P-ROOT-INHERIT
# --------------------------------------------------------------------------- #
def run_root_inherit(
    projector: Dict[str, Any],
    rows: List[Dict[str, Any]],
    form_root: Dict[str, set],
    eid_root: Dict[str, Tuple[str, str]],
    sib_surf: Dict[str, set],
    sib_stem: Dict[str, set],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    gate = projector["registry_entry"]["gate_tier"]
    records: List[Dict[str, Any]] = []
    root_by_loc: Dict[str, str] = {}
    instr = {
        "projector_id": projector["projector_id"],
        "kind": projector["kind"],
        "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
        "gate_tier": gate,
        "rootless_rows": 0,
        "rootless_function_nostem": 0,
        "rootless_lexhead_rows": 0,
        "divine_excluded": 0,
        "closed_class_function_excluded": 0,
        "authoring_no_attested_source": 0,
        "auto_by_tier": {"tier0": 0, "tierA": 0, "tierB": 0, "tierC": 0},
        "routed_by_guard": {"homograph": 0, "cross_source_conflict": 0,
                            "within_root_ambiguity": 0, "jamid_review": 0},
        "routed_by_tier": {"tier0": 0, "tierA": 0, "tierB": 0, "tierC": 0},
    }
    worked: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if morphline_root(row.get("morphline", "")) is not None:
            continue
        instr["rootless_rows"] += 1
        segs = row.get("segments") or []
        heads = [s for s in segs if is_lexical_head(s)]
        if not heads:
            instr["rootless_function_nostem"] += 1
            continue
        instr["rootless_lexhead_rows"] += 1
        surf = row.get("surface", "")
        ks = match_key(surf)
        if any(is_divine_seg(s) for s in segs) or ks in _DIVINE_KEYS:
            instr["divine_excluded"] += 1
            continue
        if is_closed_class_function_word(ks):
            instr["closed_class_function_excluded"] += 1
            continue
        match_keys = [ks] + [match_key(s.get("surface", "")) for s in heads]
        roots0: set = set()
        cats: set = set()
        matched_forms: Dict[str, List[str]] = defaultdict(list)
        for k in match_keys:
            for (rt, eid, cat, fm) in form_root.get(k, ()):
                roots0.add(rt)
                cats.add(cat)
                matched_forms[rt].append(fm)
        rootsB = set(sib_surf.get(ks, ()))
        rootsC: set = set()
        for k in match_keys:
            rootsC |= sib_stem.get(k, set())
        # carrier self-join: entry_id resolves AND a match_key of THIS row is a
        # form of that carrier entry (entry_id alone is only an example-context
        # link -- it is NOT an assertion about this lexeme; DR-2).
        eid = row.get("entry_id") or row.get("canonical_source_key")
        carrier_confirms = False
        if eid in eid_root:
            croot = eid_root[eid][0]
            for k in match_keys:
                if croot in {t[0] for t in form_root.get(k, ())}:
                    carrier_confirms = True
                    break

        tier: Optional[str] = None
        chosen: Optional[str] = None
        guard: Optional[str] = None
        if len(roots0) > 1:
            tier, guard = "tier0", "within_root_ambiguity"
        elif len(roots0) == 1:
            chosen = next(iter(roots0))
            tier = "tierA" if carrier_confirms else "tier0"
            if rootsB and chosen not in rootsB:
                guard = "cross_source_conflict" if len(rootsB) == 1 else "homograph"
        elif len(rootsB) == 1:
            tier, chosen = "tierB", next(iter(rootsB))
        elif len(rootsB) > 1:
            tier, guard = "tierB", "homograph"
        elif len(rootsC) == 1:
            tier, chosen = "tierC", next(iter(rootsC))
        elif len(rootsC) > 1:
            tier, guard = "tierC", "homograph"
        else:
            instr["authoring_no_attested_source"] += 1
            continue
        if guard is None and any(is_jamid_category(c) for c in cats if c):
            guard = "jamid_review"

        pattern = (None, None)
        if chosen and matched_forms.get(chosen):
            pattern = derivational_pattern(matched_forms[chosen][0])
        if guard:
            projection_state = "blocked" if guard == "cross_source_conflict" else "candidate"
            review_route = {
                "homograph": "two_vote_disambiguation",
                "cross_source_conflict": "never_auto_resolve",
                "within_root_ambiguity": "held_review",
                "jamid_review": "held_review",
            }[guard]
            instr["routed_by_guard"][guard] += 1
            instr["routed_by_tier"][tier] += 1
        else:
            projection_state = "candidate"
            review_route = "two_vote_required"
            instr["auto_by_tier"][tier] += 1

        evidence: List[Dict[str, Any]] = []
        if chosen:
            if tier in ("tier0", "tierA"):
                evidence.append({
                    "type": "entry_form_attestation",
                    "root": chosen,
                    "matched_forms": sorted(set(matched_forms.get(chosen, [])))[:5],
                    "carrier_self_join": carrier_confirms,
                    "detail": "qamus entry asserts this root for the attested headword/usage.form",
                })
            elif tier == "tierB":
                evidence.append({"type": "same_surface_certified_sibling", "root": chosen,
                                 "detail": "a certified whitelist row with the same surface asserts this root"})
            elif tier == "tierC":
                evidence.append({"type": "same_stem_certified_sibling", "root": chosen,
                                 "detail": "a certified whitelist row with the same lexical-head stem asserts this root"})
        else:
            evidence.append({"type": "ambiguity", "candidate_roots": sorted(roots0 | rootsB | rootsC),
                             "detail": "multiple attested sources -- routed, not auto-inherited"})
        rec = {
            "schema": "qamus.lattice.projection_record.v1",
            "projector_id": projector["projector_id"],
            "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
            "kind": "root_inheritance",
            "target_loc": row.get("loc"),
            "target_surface": norm(surf),
            "inherited": {
                "root": chosen,
                "tier": tier,
                "pattern": pattern[0],
                "pos": pattern[1],
            },
            "certification_state": "candidate",
            "gate_tier": gate,
            "guard": guard,
            "projection_state": projection_state,
            "review_route": review_route,
            "evidence": evidence,
            "created_note": (
                "root inherited by transclusion from an ATTESTED source (entry "
                "form/headword, form-confirmed carrier entry, or certified sibling); "
                "candidate until the review gate -- pattern alone never certifies (DR-2)"
            ),
            "created_from": "projector:" + projector["projector_id"],
        }
        records.append(rec)
        if chosen and guard is None:
            root_by_loc[row.get("loc")] = chosen
        if row.get("loc") in ("36:70:4", "16:3:1", "38:14:6", "7:54:23"):
            worked[row.get("loc")] = rec

    non_divine = instr["rootless_lexhead_rows"] - instr["divine_excluded"]
    auto = sum(instr["auto_by_tier"].values())
    routed = sum(instr["routed_by_guard"].values())
    instr["totals"] = {
        "auto_inheritable": auto,
        "review_routed": routed,
        "inheritable_total": auto + routed,
        "authoring_first": instr["authoring_no_attested_source"],
        "eligible_non_divine": non_divine,
        "inheritable_share_of_eligible": round((auto + routed) / non_divine, 4) if non_divine else None,
        "auto_share_of_eligible": round(auto / non_divine, 4) if non_divine else None,
    }
    return records, instr, worked


# --------------------------------------------------------------------------- #
# P-NOTE-NORMALIZE
# --------------------------------------------------------------------------- #
# Deterministic per-(role) replacement notes for internal-boilerplate segments.
_NOTE_TEMPLATES: Dict[str, Tuple[str, str]] = {
    "definite_article": ("definite article ال", "definiteness marker on the following noun"),
    "article": ("definite article ال", "definiteness marker on the following noun"),
    "masculine_plural_suffix": ("sound masculine plural suffix ـين/ـون (accusative/genitive)", "plural agreement"),
    "sound_plural_suffix": ("sound plural suffix", "plural agreement"),
    "feminine_plural_suffix": ("sound feminine plural suffix ـات", "plural agreement"),
    "dual_suffix": ("dual suffix ـان/ـين", "dual agreement"),
    "object_pronoun": ("attached object pronoun", "object inside this token"),
    "possessive_pronoun": ("attached possessive pronoun", "genitive possessor"),
    "subject_marker": ("attached subject marker", "subject agreement inside the verb"),
}
_STEM_ROLE_POS = {
    "participle_stem": "active participle",
    "active_participle_stem": "active participle",
    "verb_stem": "verb",
    "noun_stem": "noun",
    "nominal_stem": "noun",
    "adjective_stem": "adjective",
    "masdar_stem": "verbal noun (maṣdar)",
}


def run_note_normalize(
    projector: Dict[str, Any],
    rows: List[Dict[str, Any]],
    root_by_loc: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    gate = projector["registry_entry"]["gate_tier"]
    records: List[Dict[str, Any]] = []
    per_role: Dict[str, Dict[str, int]] = defaultdict(lambda: {"reachable": 0, "replaced": 0, "needs_root_chain": 0})
    total_reachable = 0
    total_replaced = 0
    total_need_chain = 0
    for row in rows:
        segs = row.get("segments") or []
        loc = row.get("loc")
        inherited_root = root_by_loc.get(loc)
        seg_repls = []
        for s in segs:
            role = s.get("role") or ""
            bp = _is_boilerplate_note(s.get("sarf_note")) or _is_boilerplate_note(s.get("nahw_note"))
            if not bp:
                continue
            total_reachable += 1
            per_role[role]["reachable"] += 1
            if is_lexical_head(s):
                if inherited_root:
                    pos = _STEM_ROLE_POS.get(role, "stem")
                    sarf = "sarf: %s from root %s" % (pos, inherited_root)
                    nahw = "nahw: lexical head of the token"
                    seg_repls.append({"segment_index": s.get("segment_index"), "role": role,
                                      "sarf_note": sarf, "nahw_note": nahw,
                                      "requires": "P-ROOT-INHERIT chain (root %s)" % inherited_root})
                    per_role[role]["replaced"] += 1
                    total_replaced += 1
                else:
                    per_role[role]["needs_root_chain"] += 1
                    total_need_chain += 1
                continue
            tpl = _NOTE_TEMPLATES.get(role)
            if not tpl:
                continue
            seg_repls.append({"segment_index": s.get("segment_index"), "role": role,
                              "sarf_note": "sarf: " + tpl[0], "nahw_note": "nahw: " + tpl[1]})
            per_role[role]["replaced"] += 1
            total_replaced += 1
        if seg_repls:
            records.append({
                "schema": "qamus.lattice.projection_record.v1",
                "projector_id": projector["projector_id"],
                "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
                "kind": "note_normalization",
                "target_loc": loc,
                "target_surface": norm(row.get("surface", "")),
                "certification_state": "candidate",
                "gate_tier": gate,
                "segment_notes": seg_repls,
                "created_note": "internal-boilerplate segment notes replaced by deterministic per-class pedagogy; candidate",
                "created_from": "projector:" + projector["projector_id"],
            })
    instr = {
        "projector_id": projector["projector_id"],
        "kind": projector["kind"],
        "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
        "gate_tier": gate,
        "boilerplate_segments_reachable": total_reachable,
        "segments_replaced": total_replaced,
        "stem_segments_needing_root_chain": total_need_chain,
        "by_role": {k: dict(v) for k, v in sorted(per_role.items())},
    }
    return records, instr


# --------------------------------------------------------------------------- #
# P-SUFFIX-FEMPL  (feminine sound plural ـات + dual/plural ـان/ـين segmentation)
# --------------------------------------------------------------------------- #
def run_suffix_fempl(
    projector: Dict[str, Any],
    rows: List[Dict[str, Any]],
    form_root: Dict[str, set],
    sib_surf: Dict[str, set],
    sib_stem: Dict[str, set],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    gate = projector["registry_entry"]["gate_tier"]
    records: List[Dict[str, Any]] = []
    instr = {
        "projector_id": projector["projector_id"],
        "kind": projector["kind"],
        "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
        "gate_tier": gate,
        "single_tok_rootless_rows": 0,
        "fempl": {"reachable": 0, "auto": 0, "guard_radical_taa": 0},
        "dual": {"reachable": 0, "auto": 0, "guard_radical_taa": 0},
        "no_attested_stem": 0,
    }
    for row in rows:
        if morphline_root(row.get("morphline", "")) is not None:
            continue
        segs = row.get("segments") or []
        if len(segs) != 1 or not is_lexical_head(segs[0]):
            continue
        instr["single_tok_rootless_rows"] += 1
        surf = row.get("surface", "")
        k = match_key(surf)
        chosen_sfx = None
        fam = None
        for sfx in _FEMPL_KEYS:
            if k.endswith(sfx) and len(k) > len(sfx) + 1:
                chosen_sfx, fam = sfx, "fempl"
                break
        if not chosen_sfx:
            for sfx in _DUAL_KEYS:
                if k.endswith(sfx) and len(k) > len(sfx) + 1:
                    chosen_sfx, fam = sfx, "dual"
                    break
        if not chosen_sfx:
            continue
        stem_key = k[: -len(chosen_sfx)]
        stem_roots = {t[0] for t in form_root.get(stem_key, ())}
        stem_roots |= sib_stem.get(stem_key, set()) | sib_surf.get(stem_key, set())
        if not stem_roots:
            instr["no_attested_stem"] += 1
            continue
        instr[fam]["reachable"] += 1
        # radical-ت homograph: the FULL surface is itself an attested rooted form
        # whose final radical is ت (the ـات is not a suffix, e.g. a ت-final root).
        radical_taa = any(t[0].split()[-1] == "ت" for t in form_root.get(k, ()))
        if radical_taa:
            instr[fam]["guard_radical_taa"] += 1
            projection_state, review_route, guard = "candidate", "two_vote_disambiguation", "radical_taa_homograph"
        else:
            instr[fam]["auto"] += 1
            projection_state, review_route, guard = "candidate", "two_vote_required", None
        suffix_role = "feminine_plural_suffix" if fam == "fempl" else "dual_or_plural_suffix"
        chosen_root = sorted(stem_roots)[0] if len(stem_roots) == 1 else None
        records.append({
            "schema": "qamus.lattice.projection_record.v1",
            "projector_id": projector["projector_id"],
            "skill_rule_ids": list(projector.get("skill_rule_ids", [])),
            "kind": "suffix_segmentation",
            "target_loc": row.get("loc"),
            "target_surface": norm(surf),
            "certification_state": "candidate",
            "gate_tier": gate,
            "guard": guard,
            "projection_state": projection_state,
            "review_route": review_route,
            "proposed_segments": [
                {"segment_index": 0, "label": "STEM", "role": "noun_stem", "match_key": stem_key,
                 "attested_stem_roots": sorted(stem_roots)},
                {"segment_index": 1, "label": ("PL-F" if fam == "fempl" else "PL/DL"),
                 "role": suffix_role, "match_key": chosen_sfx},
            ],
            "inherited_root": chosen_root,
            "evidence": [{"type": "attested_stem_remainder",
                          "detail": "surface minus the %s suffix matches an attested stem" % suffix_role,
                          "stem_match_key": stem_key, "roots": sorted(stem_roots)}],
            "created_note": "feminine-plural/dual segmentation projected from an attested stem remainder; candidate (closes the C5 tanwīn/niswa detector gap)",
            "created_from": "projector:" + projector["projector_id"],
        })
    return records, instr


# --------------------------------------------------------------------------- #
# inheritance run driver
# --------------------------------------------------------------------------- #
def inherit_all(
    whitelist_path: Path,
    entries_path: Path = ENTRIES_DEFAULT,
    registry_path: Path = REGISTRY_PATH,
) -> Dict[str, Any]:
    registry = load_registry(registry_path)
    rows = load_whitelist(whitelist_path)
    entries = load_entries(entries_path)
    form_root, eid_root = build_entry_index(entries)
    sib_surf, sib_stem = build_root_sibling_index(rows)

    all_records: List[Dict[str, Any]] = []
    root_inherit_instr: List[Dict[str, Any]] = []
    note_instr: List[Dict[str, Any]] = []
    suffix_instr: List[Dict[str, Any]] = []
    root_by_loc: Dict[str, str] = {}
    worked_examples: Dict[str, Dict[str, Any]] = {}

    for entry in registry["registered"]:
        if entry["kind"] == "root_inheritance":
            recs, instr, worked = run_root_inherit(entry, rows, form_root, eid_root, sib_surf, sib_stem)
            all_records.extend(recs)
            root_inherit_instr.append(instr)
            root_by_loc.update({loc: rec["inherited"]["root"]
                                for loc, rec in worked.items() if rec["inherited"]["root"]})
            worked_examples.update(worked)
            # accumulate clean auto roots for the note chain
            for rec in recs:
                if rec.get("kind") == "root_inheritance" and rec.get("guard") is None \
                        and rec["inherited"]["root"]:
                    root_by_loc[rec["target_loc"]] = rec["inherited"]["root"]
    for entry in registry["registered"]:
        if entry["kind"] == "note_normalization":
            recs, instr = run_note_normalize(entry, rows, root_by_loc)
            all_records.extend(recs)
            note_instr.append(instr)
        elif entry["kind"] == "suffix_segmentation":
            recs, instr = run_suffix_fempl(entry, rows, form_root, sib_surf, sib_stem)
            all_records.extend(recs)
            suffix_instr.append(instr)

    return {
        "schema": "qamus.lattice.inheritance_instrumentation.v1",
        "inputs": {
            "whitelist_rows": len(rows),
            "whitelist_sha256_16": hashlib.sha256(whitelist_path.read_bytes()).hexdigest()[:16],
            "entries": len(entries),
            "entry_form_keys": len(form_root),
            "rooted_sibling_surfaces": len(sib_surf),
        },
        "root_inheritance_projectors": root_inherit_instr,
        "note_normalization_projectors": note_instr,
        "suffix_segmentation_projectors": suffix_instr,
        "worked_examples": worked_examples,
        "records": all_records,
    }


# --------------------------------------------------------------------------- #
# GLOBAL BIDIRECTIONAL LEXEME JOIN (occurrence <-> entry)
#
# The whole occurrence corpus (whitelist rows) joined against ALL 2,092 qamus
# entries in both directions, keyed by the CANONICAL content-word normalizer
# vendored VERBATIM from the deployed word-by-word pipeline
# (services/qamus_wbw/normalize.py -- reuse, do NOT reinvent: a divergent key
# would silently disagree with the live wbw lookup). The join subsumes
# P-ROOT-INHERIT's tier-0/A as ONE index join and turns tiers into typed edges.
# --------------------------------------------------------------------------- #
def wbw_norm(s: str) -> str:
    """Canonical content-word match key -- copied verbatim from the deployed
    services/qamus_wbw/normalize.py::norm (checkout aligns with the wbw pipeline
    extended 2026-06 with usage.forms keys / host_lexeme / function-word splits).
    Strips tashkeel/tatweel/Qurʾanic annotation + dagger-alef->alif, folds hamza
    seats and ة/ى (content-word lenient; hamza homographs surface as multi-entry
    matches and route to 2-vote, exactly as the live pipeline handles them)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ىٰ", "ى")
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0652:
            continue
        if o == 0x0670:
            out.append("ا")
            continue
        if o == 0x0640:
            continue
        if 0x0653 <= o <= 0x0655:
            continue
        if 0x06D6 <= o <= 0x06ED:
            continue
        out.append(ch)
    s = "".join(out)
    s = s.replace("آ", "ا").replace("ٱ", "ا")
    s = s.replace("أ", "").replace("إ", "").replace("ء", "")
    s = s.replace("ؤ", "و").replace("ئ", "ي")
    s = s.replace("ى", "ي")
    s = s.replace("ة", "ه")
    s = s.replace(" ", "")
    return s


_MIN_JOIN_LEN = 3  # expand.py MIN_FORM_LEN: ignore very short forms (particles/clitics)


def _deproclitic_keys(nsurface: str) -> set:
    """Deterministic proclitic-stripped candidate keys on a NORMALIZED surface
    (mirrors the wbw pipeline's de-proclitic pass: و/ف conjunction, ب/ك/ل/ت/س
    prepositional/verbal proclitics, and the ال definite article). Matches found
    ONLY via these are typed as 'derived' edges and, when they add a second root,
    route to 2-vote -- they never widen the unambiguous auto bucket unchecked."""
    keys: set = set()
    s = nsurface
    for pfx in ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ك", "ل", "ت", "س"):
        if s.startswith(pfx) and len(s) - len(pfx) >= _MIN_JOIN_LEN:
            keys.add(s[len(pfx):])
    # a second proclitic layer (e.g. و + ب): strip one more leading و/ف then clitic
    if s[:1] in ("و", "ف") and len(s) > 1 and s[1:2] in ("ب", "ك", "ل", "ت", "س") and len(s) - 2 >= _MIN_JOIN_LEN:
        keys.add(s[2:])
    keys.discard(s)
    return keys


def entry_section(entry: Dict[str, Any]) -> Optional[str]:
    for sk in (entry.get("source_keys") or []):
        s = str(sk)
        if s[:1] in ("p", "v", "n"):
            return s[:1]
    return None


def build_lexeme_index(entries: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """wbw_norm(form) -> [{entry_id, root, section, category, edge_type, form}]. Edge
    types: headword / form (usage.forms) / sense (sense surface). Forms shorter than
    MIN_JOIN_LEN after normalization are skipped (clitic/particle false-hit guard)."""
    index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    seen: set = set()
    for d in entries:
        eid = d.get("id")
        root = (d.get("root") or "").strip() or None
        section = entry_section(d)
        cat = d.get("category", "")
        pairs: List[Tuple[str, str]] = []
        for part in (d.get("headword", "") or "").split("/"):
            if part.strip():
                pairs.append((part.strip(), "headword"))
        for u in (d.get("usage") or []):
            for fm in (u.get("forms") or []):
                for part in str(fm).split("/"):
                    if part.strip():
                        pairs.append((part.strip(), "form"))
        for s in (d.get("senses") or []):
            ar = (s.get("ar") or "").strip()
            if ar:
                pairs.append((ar, "sense"))
        for surface, etype in pairs:
            key = wbw_norm(surface)
            if len(key) < _MIN_JOIN_LEN:
                continue
            dedup = (key, eid, etype)
            if dedup in seen:
                continue
            seen.add(dedup)
            index[key].append({"entry_id": eid, "root": root, "section": section,
                               "category": cat, "edge_type": etype, "form": surface})
    return index


def build_lexeme_join(
    rows: List[Dict[str, Any]],
    entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    index = build_lexeme_index(entries)
    section_of = {d.get("id"): entry_section(d) for d in entries}
    edges: List[Dict[str, Any]] = []
    entry_occurrences: Dict[str, set] = defaultdict(set)

    n_rows = len(rows)
    matched_rows = 0
    rooted_rows = 0
    rootless_rows = 0
    # buckets
    coherent_rooted = 0          # row has a root AND an entry attests the same root
    conflict_rooted = 0          # row has a root but NO matched entry attests it (N-CONS-01 shape)
    inheritable_auto = 0         # rootless, single unambiguous matched root
    inheritable_multi = 0        # rootless, >1 matched root -> homograph/2-vote
    matched_no_root_info = 0     # matched only jamid/rootless entries
    per_section_edges: Counter = Counter()
    per_section_rows: Dict[str, set] = defaultdict(set)

    for r in rows:
        loc = r.get("loc")
        direct_keys = {wbw_norm(r.get("surface", ""))}
        for s in (r.get("segments") or []):
            if is_lexical_head(s):
                direct_keys.add(wbw_norm(s.get("surface", "")))
        derived_keys: set = set()
        for k in list(direct_keys):
            derived_keys |= _deproclitic_keys(k)
        derived_keys -= direct_keys
        rank = {"headword": 4, "form": 3, "sense": 2, "derived": 1}
        hits: Dict[str, Dict[str, Any]] = {}
        for k, is_derived in [(k, False) for k in direct_keys] + [(k, True) for k in derived_keys]:
            if len(k) < _MIN_JOIN_LEN:
                continue
            for e in index.get(k, ()):
                etype = "derived" if is_derived else e["edge_type"]
                cand = dict(e, edge_type=etype)
                prev = hits.get(e["entry_id"])
                if prev is None or rank[etype] > rank[prev["edge_type"]]:
                    hits[e["entry_id"]] = cand
        if not hits:
            continue
        matched_rows += 1
        row_root = morphline_root(r.get("morphline", ""))
        matched_roots = {e["root"] for e in hits.values() if e["root"]}
        for eid, e in hits.items():
            entry_occurrences[eid].add(loc)
            edges.append({
                "loc": loc,
                "entry_id": eid,
                "edge_type": e["edge_type"],
                "section": e["section"],
                "entry_root": e["root"],
                "row_root": row_root,
                "matched_form": e["form"],
                "surface": norm(r.get("surface", "")),
                "relation": ("root_confirms" if (row_root and e["root"] == row_root)
                             else "root_conflict" if (row_root and e["root"] and e["root"] != row_root)
                             else "root_inherit_candidate" if (not row_root and e["root"])
                             else "linkage_only"),
            })
            if e["section"]:
                per_section_edges[e["section"]] += 1
                per_section_rows[e["section"]].add(loc)
        if row_root is not None:
            rooted_rows += 1
            if row_root in matched_roots:
                coherent_rooted += 1
            elif matched_roots:
                conflict_rooted += 1
            else:
                matched_no_root_info += 1
        else:
            rootless_rows += 1
            if len(matched_roots) == 1:
                inheritable_auto += 1
            elif len(matched_roots) > 1:
                inheritable_multi += 1
            else:
                matched_no_root_info += 1

    entries_with_occ = sum(1 for eid in section_of if entry_occurrences.get(eid))
    orphan_entries = len(section_of) - entries_with_occ
    orphan_by_section: Counter = Counter()
    covered_by_section: Counter = Counter()
    for eid, sec in section_of.items():
        if entry_occurrences.get(eid):
            covered_by_section[sec] += 1
        else:
            orphan_by_section[sec] += 1

    instrumentation = {
        "schema": "qamus.lattice.lexeme_join.v1",
        "normalizer": "vendored services/qamus_wbw/normalize.py::norm (content-word key)",
        "inputs": {"whitelist_rows": n_rows, "entries": len(entries),
                   "lexeme_index_keys": len(index)},
        "occurrence_to_entry": {
            "rows_matching_at_least_one_entry": matched_rows,
            "match_coverage": round(matched_rows / n_rows, 4) if n_rows else None,
            "rooted_rows_matched": rooted_rows,
            "rootless_rows_matched": rootless_rows,
            "coherent_rooted_confirmed": coherent_rooted,
            "conflict_rooted_row_vs_entry": conflict_rooted,
            "inheritable_auto_single_root": inheritable_auto,
            "inheritable_multi_root_two_vote": inheritable_multi,
            "matched_no_root_information": matched_no_root_info,
            "per_section_rows": {s: len(v) for s, v in sorted(per_section_rows.items(), key=lambda x: str(x[0]))},
            "per_section_edges": dict(sorted(per_section_edges.items(), key=lambda x: str(x[0]))),
        },
        "entry_to_occurrence": {
            "entries_with_recognized_occurrence": entries_with_occ,
            "orphan_entries_no_occurrence": orphan_entries,
            "covered_by_section": dict(sorted(covered_by_section.items(), key=lambda x: str(x[0]))),
            "orphan_by_section": dict(sorted(orphan_by_section.items(), key=lambda x: str(x[0]))),
        },
        "edge_count": len(edges),
        "edge_types": dict(Counter(e["edge_type"] for e in edges)),
        "relation_counts": dict(Counter(e["relation"] for e in edges)),
    }
    return {"instrumentation": instrumentation, "edges": edges,
            "entry_occurrences": {k: sorted(v, key=_loc_key) for k, v in entry_occurrences.items()}}


# --------------------------------------------------------------------------- #
# self-test (red-first)
# --------------------------------------------------------------------------- #
def self_test() -> int:
    import tempfile

    results: Dict[str, Any] = {}

    # Registry loads and validates against the projector-record schema.
    registry = load_registry()
    results["registry_projectors"] = [e["projector_id"] for e in registry["registered"]]

    # --- fixtures -------------------------------------------------------------
    def wl_row(loc, surface, segments, morphline):
        return {"loc": loc, "surface": surface, "segments": segments, "morphline": morphline}

    impf_segs = [
        {"segment_index": 0, "role": "verb_prefix", "label": "PFX", "surface": "يَ"},
        {"segment_index": 1, "role": "verb_stem", "label": "STEM", "surface": "فْعَل"},
    ]
    # certified C1 source at 2:2:2, surface Y
    surfaceY = "يَفْعَل"
    src = wl_row("2:2:2", surfaceY, impf_segs, "root x y z · Form I imperfect active")
    # homograph: a DIFFERENT certified analysis for the same surface elsewhere
    homograph_twin = wl_row(
        "3:3:3", surfaceY,
        [{"segment_index": 0, "role": "noun_stem", "label": "N", "surface": surfaceY}],
        "root x y z · noun",
    )
    whitelist = [src]
    corpus = [("2:2:2", surfaceY), ("5:5:5", surfaceY), ("6:6:6", surfaceY)]

    c1 = registry["registered"][0]
    homs = build_homograph_surfaces(whitelist)
    recs, instr = run_positive_projector(c1, whitelist, {"2:2:2"}, corpus, homs)
    # RED-1: covered loc (2:2:2) must NOT project; 5:5:5 and 6:6:6 are reachable.
    t1 = instr["reachable_uncovered_rows"] == 2 and instr["auto_candidates"] == 2
    results["t1_covered_not_projected"] = t1

    # RED-2: homograph surface must route to 2-vote, never auto-project.
    homs2 = build_homograph_surfaces([src, homograph_twin])
    recs2, instr2 = run_positive_projector(c1, [src, homograph_twin], {"2:2:2", "3:3:3"}, corpus, homs2)
    t2 = instr2["auto_candidates"] == 0 and instr2["routed_two_vote"] == 2 and all(
        r["review_route"] == "two_vote_disambiguation" for r in recs2 if r["projection_state"] == "candidate"
    )
    results["t2_homograph_routes_two_vote"] = t2

    # RED-3: a Form V/VI derivational-taa' split MUST be blocked by the negative meta.
    bad_ta = wl_row(
        "7:7:7", "تفعل",
        [
            {"segment_index": 0, "role": "verb_prefix", "label": "PFX", "surface": "ت"},
            {"segment_index": 1, "role": "verb_stem", "label": "STEM", "surface": "فعل"},
        ],
        "root f C l · Form V perfect active",
    )
    split_detected = splits_derivational_ta(analysis_of(bad_ta))
    # feed a candidate carrying that split through the negative meta
    fake_candidate = _projected_record(
        projector=registry["registered"][0], source_row=bad_ta,
        target_loc="8:8:8", target_surface="تفعل",
        guards_evaluated={}, projection_state="candidate", review_route="two_vote_required",
    )
    neg = registry["registered"][2]
    neg_report = run_negative_meta(neg, [fake_candidate], whitelist)
    t3 = split_detected and fake_candidate["projection_state"] == "blocked" and neg_report["candidate_projections_blocked"] == 1
    results["t3_form56_ta_split_blocked"] = t3

    # GREEN: a correct Form V (taa' INSIDE the stem) must NOT be flagged.
    good_form5 = wl_row(
        "9:9:9", "تفعّل",
        [{"segment_index": 0, "role": "verb_stem", "label": "STEM", "surface": "تفعّل"}],
        "root f C l · Form V perfect active",
    )
    t4 = not splits_derivational_ta(analysis_of(good_form5))
    results["t4_correct_form5_not_flagged"] = t4

    # RED-4: surface non-exact must block (defensive; NFD vs NFC divergence).
    ctx_bad = {"homograph": False, "target_surface": "أ", "source_surface": "ا"}
    t5 = surface_byte_exact(ctx_bad) is not None
    results["t5_surface_nonexact_blocks"] = t5

    # RED-5: unknown guard / predicate registration fails closed.
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            bad = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            bad["registered"][0]["guards"].append("no_such_guard")
            json.dump(bad, fh, ensure_ascii=False)
            bad_path = Path(fh.name)
        try:
            load_registry(bad_path)
            t6 = False
        except LatticeError:
            t6 = True
        finally:
            bad_path.unlink(missing_ok=True)
    except Exception:
        t6 = False
    results["t6_unknown_guard_fails_closed"] = t6

    # RED-6: projectors never mutate the whitelist input list.
    before = _hash(whitelist)
    run_positive_projector(c1, whitelist, {"2:2:2"}, corpus, homs)
    t7 = _hash(whitelist) == before
    results["t7_whitelist_read_only"] = t7

    # ===================================================================== #
    # T13 root-inheritance / note-normalize / suffix-segmentation red-first
    # ===================================================================== #
    by_id = {e["projector_id"]: e for e in registry["registered"]}
    P_INH = by_id["sarf.root_inherit_transclusion.v1"]
    P_NOTE = by_id["sarf.note_normalize.v1"]
    P_SFX = by_id["sarf.suffix_fempl_segmentation.v1"]

    def entry(eid, root, headword, forms, category="Verbs with Derivatives"):
        return {"id": eid, "root": root, "headword": headword, "category": category,
                "usage": [{"forms": forms}]}

    def rootless_row(loc, surface, heads, roles=None, extra=None):
        segs = []
        for i, (surf, lab, role) in enumerate(heads):
            segs.append({"segment_index": i, "surface": surf, "label": lab, "role": role,
                         "sarf_note": "sarf: visible piece accounted; no unsupported public source label",
                         "nahw_note": "nahw: function/context contribution preserved where relevant"})
        r = {"loc": loc, "surface": surface, "morphline": "no public root asserted", "segments": segs}
        if extra:
            r.update(extra)
        return r

    def rooted_row(loc, surface, stem_surface, root):
        return {"loc": loc, "surface": surface, "morphline": "root %s · Form I perfect active" % root,
                "segments": [{"segment_index": 0, "surface": stem_surface, "label": "STEM", "role": "verb_stem"}]}

    # entries: كفر (with الكافرين form), a divine placeholder is via role, a jamid particle entry
    entries = [
        entry("e-kfr", "ك ف ر", "كَفَرَ", ["كَفَرَ", "الْكَافِرِينَ", "كَافِرٌ"]),
        entry("e-xlq", "خ ل ق", "خَلَقَ", ["خَلَقَ", "خُلُق"]),
        entry("e-hml-a", "ح م ل", "حَمَلَ", ["حَامِلَة"]),     # cross-source: two roots share a surface
        entry("e-hml-b", "ح م ل", "حِمْل", ["حِمْل"]),
        entry("e-jamid", "ل ك ت", "لَكِنْ", ["لَٰكِنَّ"], category="Miscellaneous Particles"),
        entry("e-qwl", "ق و ل", "قَالَ", ["قُلْ"]),
        entry("e-qll", "ق ل ل", "قَلَّ", ["قُلْ"]),            # within-root ambiguity: قُلْ maps to 2 roots
        entry("e-sxr", "س خ ر", "سَخَّرَ", ["مُسَخَّرَات", "مُسَخَّر"]),
    ]
    form_root, eid_root = build_entry_index(entries)

    # T8: boilerplate ART/STEM/PL row inherits root ك ف ر (tier0) and its ART note normalizes.
    kfr = rootless_row("36:70:4", "الْكَافِرِينَ",
                       [("الْ", "ART", "definite_article"), ("كَافِرِ", "STEM", "participle_stem"),
                        ("ينَ", "PL", "masculine_plural_suffix")])
    # T13-divine: a divine-name token row (role) must be excluded.
    divine = rootless_row("1:1:2", "ٱللَّهِ", [("ٱللَّهِ", "TOK", "proper_divine_name")])
    # T14-authoring: a lexeme with no attested source anywhere.
    orphan = rootless_row("9:9:9", "زقنبوت", [("زقنبوت", "TOK", "token")])
    # cross-source conflict: entry says ح م ل; a same-surface certified sibling says خ ل ق.
    conflict = rootless_row("2:2:2", "حَامِلَة", [("حَامِلَة", "TOK", "token")])
    conflict_sibling = rooted_row("5:5:5", "حَامِلَة", "حَامِلَة", "خ ل ق")
    # homograph: entry root ك ف ر but TWO different certified same-surface siblings assert 2 roots.
    homo = rootless_row("3:3:3", "عَيْن", [("عَيْن", "TOK", "token")])
    homo_sib1 = rooted_row("6:6:6", "عَيْن", "عَيْن", "ع ي ن")
    homo_sib2 = rooted_row("7:7:1", "عَيْن", "عَيْن", "غ ي ر")
    # within-root ambiguity: قُلْ maps to two roots via the entry index (ق و ل / ق ل ل).
    ambi = rootless_row("4:4:4", "قُلْ", [("قُلْ", "TOK", "token")])
    # jamid: matches a Miscellaneous-Particles entry only.
    jamid = rootless_row("8:8:8", "لَٰكِنَّ", [("لَٰكِنَّ", "TOK", "token")])

    inh_rows = [kfr, divine, orphan, conflict, conflict_sibling, homo, homo_sib1, homo_sib2, ambi, jamid]
    sib_surf, sib_stem = build_root_sibling_index(inh_rows)
    recs, instr, worked = run_root_inherit(P_INH, inh_rows, form_root, eid_root, sib_surf, sib_stem)
    by_loc = {r["target_loc"]: r for r in recs}

    results["t8_boilerplate_row_inherits_tier0"] = (
        by_loc["36:70:4"]["inherited"]["root"] == "ك ف ر"
        and by_loc["36:70:4"]["inherited"]["tier"] == "tier0"
        and by_loc["36:70:4"]["guard"] is None
        and by_loc["36:70:4"]["certification_state"] == "candidate"
    )
    results["t9_divine_excluded"] = "1:1:2" not in by_loc and instr["divine_excluded"] == 1
    results["t10_no_attested_source_not_projected"] = (
        "9:9:9" not in by_loc and instr["authoring_no_attested_source"] >= 1
    )
    results["t11_cross_source_conflict_blocked"] = (
        by_loc["2:2:2"]["guard"] == "cross_source_conflict"
        and by_loc["2:2:2"]["projection_state"] == "blocked"
        and by_loc["2:2:2"]["review_route"] == "never_auto_resolve"
    )
    results["t12_homograph_routes_two_vote"] = (
        by_loc["3:3:3"]["guard"] == "homograph"
        and by_loc["3:3:3"]["review_route"] == "two_vote_disambiguation"
        and by_loc["3:3:3"]["inherited"]["root"] is None
    )
    results["t13_within_root_ambiguity_held"] = (
        by_loc["4:4:4"]["guard"] == "within_root_ambiguity"
        and by_loc["4:4:4"]["review_route"] == "held_review"
    )
    results["t14_jamid_routed_review"] = (
        by_loc["8:8:8"]["guard"] == "jamid_review"
        and by_loc["8:8:8"]["review_route"] == "held_review"
    )

    # T15: note-normalize replaces the ART boilerplate note; STEM waits on the root chain
    # unless the root was inherited (it was, tier0 -> ك ف ر).
    root_by_loc = {r["target_loc"]: r["inherited"]["root"] for r in recs
                   if r.get("guard") is None and r["inherited"]["root"]}
    nrecs, ninstr = run_note_normalize(P_NOTE, [kfr], root_by_loc)
    note_for_kfr = nrecs[0]["segment_notes"] if nrecs else []
    art_note = next((n for n in note_for_kfr if n["role"] == "definite_article"), None)
    stem_note = next((n for n in note_for_kfr if n["role"] == "participle_stem"), None)
    results["t15_boilerplate_note_replaced"] = (
        art_note is not None and "definite article" in art_note["sarf_note"]
        and stem_note is not None and "root ك ف ر" in stem_note["sarf_note"]
    )
    # T16: a NON-boilerplate note must be left untouched.
    clean_row = {"loc": "1:2:3", "surface": "x", "morphline": "no public root asserted",
                 "segments": [{"segment_index": 0, "surface": "الْ", "label": "ART", "role": "definite_article",
                               "sarf_note": "sarf: a hand-authored certified note", "nahw_note": "nahw: authored"}]}
    nrecs2, _ = run_note_normalize(P_NOTE, [clean_row], {})
    results["t16_non_boilerplate_untouched"] = (nrecs2 == [])

    # T17: suffix-fempl projects مُسَخَّرَات-type; T18: radical-ت routes to 2-vote.
    sfx_rows = [
        rootless_row("7:54:23", "مُسَخَّرَٰتٍۭ", [("مُسَخَّرَٰتٍۭ", "TOK", "token")]),
    ]
    srecs, sinstr = run_suffix_fempl(P_SFX, sfx_rows, form_root, {}, {})
    results["t17_suffix_fempl_projects"] = (
        len(srecs) == 1 and srecs[0]["proposed_segments"][1]["role"] == "feminine_plural_suffix"
        and srecs[0]["inherited_root"] == "س خ ر"
    )
    # radical-ت: a surface whose full form is an attested ت-final-radical root must route.
    form_root_rad, _ = build_entry_index([entry("e-mwt", "م و ت", "مَاتَ", ["أَمْوَات"], "Verbs"),
                                          entry("e-byt", "ب ي ت", "بَيْت", ["بَيْت"], "Nouns")])
    # craft: surface بَيَات whose full key is attested with 3rd radical ت -> radical_taa guard
    form_root_rad["بيات"].add(("ح ي ت", "e-x", "Nouns", "بَيَات"))  # ت-final radical form attested
    rad_rows = [rootless_row("9:1:1", "بَيَات", [("بَيَات", "TOK", "token")])]
    # need a stem remainder attested too so it is reachable
    form_root_rad["بي"].add(("ب ي و", "e-y", "Nouns", "بَي"))
    rrecs, rinstr = run_suffix_fempl(P_SFX, rad_rows, form_root_rad, {}, {})
    results["t18_radical_taa_routes_two_vote"] = (
        len(rrecs) == 1 and rrecs[0]["guard"] == "radical_taa_homograph"
        and rrecs[0]["review_route"] == "two_vote_disambiguation"
    )

    # T19: match_key maps dagger-alef + wasla to plain alif but keeps hamza distinct.
    results["t19_match_key_root_preserving"] = (
        match_key("مُسَخَّرَٰتٍۭ") == match_key("مُسَخَّرَات")
        and match_key("أمن") != match_key("امن")
    )

    # T20: vendored wbw_norm is the deployed content key (dagger->alif, hamza folded).
    results["t20_wbw_norm_parity"] = (
        wbw_norm("مُسَخَّرَٰتٍۭ") == wbw_norm("مُسَخَّرَات") == "مسخرات"
        and wbw_norm("إِيمَٰن") == wbw_norm("أَيْمَٰن")  # hamza folds -> multi-entry -> 2-vote
    )

    # T21: global join -- occurrence<->entry both directions on a tiny fixture.
    j_entries = [
        entry("j-kfr", "ك ف ر", "كَفَرَ", ["الْكَافِرِينَ", "كَافِرٌ"]),
        entry("j-orphan", "ز ه ر", "زَهْرَة", ["زَهْرَة"], category="Plants & Fruits"),
    ]
    for e in j_entries:  # give them a section
        e["source_keys"] = ["v001"] if e["id"] == "j-kfr" else ["n001"]
    j_rows = [
        rootless_row("36:70:4", "الْكَافِرِينَ", [("الْكَافِرِينَ", "TOK", "token")]),
        rooted_row("6:6:6", "الْكَافِرِينَ", "الْكَافِرِينَ", "خ ل ق"),  # conflict: entry says ك ف ر
    ]
    jr = build_lexeme_join(j_rows, j_entries)
    ji = jr["instrumentation"]
    results["t21_join_bidirectional"] = (
        ji["occurrence_to_entry"]["rows_matching_at_least_one_entry"] == 2
        and ji["occurrence_to_entry"]["inheritable_auto_single_root"] == 1
        and ji["occurrence_to_entry"]["conflict_rooted_row_vs_entry"] == 1
        and ji["entry_to_occurrence"]["orphan_entries_no_occurrence"] == 1  # زهرة has no occurrence
        and ji["entry_to_occurrence"]["entries_with_recognized_occurrence"] == 1
    )

    # t22: closed-class function words never inherit content roots by surface
    # join (Window-1 2026-07-16: من proposed م ن ن from the entry مَنَّ -- red
    # before the guard, green after). Non-constant discriminator: the content
    # verb خَلَقَ with an identical evidence shape MUST still inherit.
    fw_row = {"loc": "2:49:3", "surface": "مِن",
              "morphline": "no public root asserted · TOK:مِن",
              "segments": [{"segment_index": 0, "surface": "مِن", "class": "qg-segment",
                            "role": "token", "label": "TOK", "gloss_contribution": "from"}]}
    cw_row = {"loc": "16:3:1", "surface": "خَلَقَ",
              "morphline": "no public root asserted · STEM:خَلَقَ",
              "segments": [{"segment_index": 0, "surface": "خَلَقَ", "class": "qg-verb-stem",
                            "role": "verb_stem", "label": "STEM", "gloss_contribution": "created"}]}
    fw_proj = {"projector_id": "sarf.root_inherit_transclusion.v1", "kind": "root_inheritance",
               "skill_rule_ids": [], "registry_entry": {"gate_tier": "two_vote_required"}}
    fw_recs, fw_instr, _fw = run_root_inherit(
        fw_proj, [fw_row], {match_key("مِن"): {("م ن ن", "vX", "verb", "مَنَّ")}}, {}, {}, {})
    cw_recs, _ci, _cw = run_root_inherit(
        fw_proj, [cw_row], {match_key("خَلَقَ"): {("خ ل ق", "v029", "verb", "خَلَقَ")}}, {}, {}, {})
    results["t22_closed_class_function_guard"] = (
        fw_recs == [] and fw_instr["closed_class_function_excluded"] == 1
        and len(cw_recs) == 1 and cw_recs[0]["inherited"]["root"] == "خ ل ق"
        and is_closed_class_function_word(match_key("وَمَا"))      # proclitic strip
        and not is_closed_class_function_word(match_key("مَال"))  # near-miss content word
    )

    # t23 (D-1/D-3 owner correction): a Form-V taa' EXPLICITLY classed as the
    # derivational form-marker (DER) is permitted rich segmentation; the same
    # surface shape classed as a person-prefix remains blocked (red stays red).
    der_row = {"morphline": "root و ك ل · Form V perfect active",
               "segments": [
                   {"segment_index": 0, "surface": "تَ", "class": "qg-derivative-prefix",
                    "role": "derivative_prefix_form_v", "label": "DER",
                    "gloss_contribution": "Form V marker"},
                   {"segment_index": 1, "surface": "وَكَّلْ", "class": "qg-verb-stem",
                    "role": "verb_stem", "label": "STEM", "gloss_contribution": "relied"}]}
    pfx_row = {"morphline": "root و ك ل · Form V perfect active",
               "segments": [
                   {"segment_index": 0, "surface": "تَ", "class": "qg-verb-prefix",
                    "role": "verb_prefix", "label": "PFX",
                    "gloss_contribution": "imperfect prefix"},
                   {"segment_index": 1, "surface": "وَكَّلْ", "class": "qg-verb-stem",
                    "role": "verb_stem", "label": "STEM", "gloss_contribution": "relied"}]}
    results["t23_der_taa_permitted_pfx_taa_blocked"] = (
        splits_derivational_ta(der_row) is False
        and splits_derivational_ta(pfx_row) is True
    )

    ok = all(v is True for k, v in results.items() if k.startswith("t"))
    print(json.dumps({"ok": ok, "results": results}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    lst = sub.add_parser("list", help="list registered projectors")
    lst.add_argument("--json", action="store_true")
    prj = sub.add_parser("project", help="run projectors against a whitelist + corpus index")
    prj.add_argument("--whitelist", required=True, type=Path)
    prj.add_argument("--corpus", required=True, type=Path)
    prj.add_argument("--out-instrumentation", type=Path)
    prj.add_argument("--out-ledger", type=Path)
    prj.add_argument("--max-ledger", type=int, default=0, help="cap ledger rows written (0 = all)")
    inh = sub.add_parser("inherit", help="run T13 root-inheritance / note-normalize / suffix-segmentation projectors")
    inh.add_argument("--whitelist", required=True, type=Path)
    inh.add_argument("--entries", type=Path, default=ENTRIES_DEFAULT)
    inh.add_argument("--out-instrumentation", type=Path)
    inh.add_argument("--out-ledger", type=Path)
    inh.add_argument("--max-ledger", type=int, default=0, help="cap ledger rows written (0 = all)")
    jn = sub.add_parser("join", help="global bidirectional occurrence<->entry lexeme join + edges")
    jn.add_argument("--whitelist", required=True, type=Path)
    jn.add_argument("--entries", type=Path, default=ENTRIES_DEFAULT)
    jn.add_argument("--out-instrumentation", type=Path)
    jn.add_argument("--out-edges", type=Path)
    jn.add_argument("--out-entry-occurrences", type=Path)
    sub.add_parser("self-test", help="red-first safety self-test")
    args = parser.parse_args(argv)

    if args.command == "self-test":
        return self_test()
    if args.command == "list":
        registry = load_registry()
        if args.json:
            print(json.dumps(registry, ensure_ascii=False, indent=2))
        else:
            for e in registry["registered"]:
                print("%s [%s] gate=%s rules=%s" % (
                    e["projector_id"], e["kind"], e["registry_entry"]["gate_tier"],
                    ",".join(e.get("skill_rule_ids", []))))
        return 0
    if args.command == "project":
        report = project_all(args.whitelist, args.corpus)
        records = report.pop("records")
        summary = {k: v for k, v in report.items()}
        if args.out_ledger:
            args.out_ledger.parent.mkdir(parents=True, exist_ok=True)
            n = 0
            with args.out_ledger.open("w", encoding="utf-8") as handle:
                for rec in records:
                    if args.max_ledger and n >= args.max_ledger:
                        break
                    handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
            summary["ledger_rows_written"] = n
            summary["ledger_rows_total"] = len(records)
        if args.out_instrumentation:
            args.out_instrumentation.parent.mkdir(parents=True, exist_ok=True)
            args.out_instrumentation.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.command == "inherit":
        report = inherit_all(args.whitelist, args.entries)
        records = report.pop("records")
        summary = {k: v for k, v in report.items()}
        if args.out_ledger:
            args.out_ledger.parent.mkdir(parents=True, exist_ok=True)
            n = 0
            with args.out_ledger.open("w", encoding="utf-8") as handle:
                for rec in records:
                    if args.max_ledger and n >= args.max_ledger:
                        break
                    handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
            summary["ledger_rows_written"] = n
            summary["ledger_rows_total"] = len(records)
        if args.out_instrumentation:
            args.out_instrumentation.parent.mkdir(parents=True, exist_ok=True)
            args.out_instrumentation.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.command == "join":
        rows = load_whitelist(args.whitelist)
        entries = load_entries(args.entries)
        result = build_lexeme_join(rows, entries)
        instr = result["instrumentation"]
        instr["inputs"]["whitelist_sha256_16"] = hashlib.sha256(args.whitelist.read_bytes()).hexdigest()[:16]
        if args.out_edges:
            args.out_edges.parent.mkdir(parents=True, exist_ok=True)
            with args.out_edges.open("w", encoding="utf-8") as handle:
                for e in result["edges"]:
                    handle.write(json.dumps(e, ensure_ascii=False) + "\n")
        if args.out_entry_occurrences:
            args.out_entry_occurrences.parent.mkdir(parents=True, exist_ok=True)
            with args.out_entry_occurrences.open("w", encoding="utf-8") as handle:
                for eid, locs in sorted(result["entry_occurrences"].items()):
                    handle.write(json.dumps({"entry_id": eid, "occurrences": locs}, ensure_ascii=False) + "\n")
        if args.out_instrumentation:
            args.out_instrumentation.parent.mkdir(parents=True, exist_ok=True)
            args.out_instrumentation.write_text(json.dumps(instr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(instr, ensure_ascii=False, indent=2))
        return 0
    parser.error("a command is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
