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


NAMED_PREDICATES: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "pred_c1_impf": pred_c1_impf,
    "pred_c5_enclitic": pred_c5_enclitic,
    "pred_any_candidate": pred_any_candidate,
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


NAMED_GUARDS: Dict[str, Callable[[Dict[str, Any]], Optional[Dict[str, str]]]] = {
    "homograph_surface_ambiguity": homograph_surface_ambiguity,
    "surface_byte_exact": surface_byte_exact,
    "meta_form56_ta_split": meta_form56_ta_split,
    "construction_match": construction_match,
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
    parser.error("a command is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
