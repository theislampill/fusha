#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone Fusha parser/checker MVP.

The output is a source-clean preview IR. It supports Qamus/RH-LIVE authoring,
learner tutoring, and arbitrary typing prototypes without claiming live/source
certification.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402
from tools import fusha_text_check as TC  # noqa: E402
from tools.fusha_clitic_splitter import split_clitics  # noqa: E402
from tools.fusha_pattern_engine import FUNCTION_WORDS, build_morphology, preview_segments  # noqa: E402
from tools.fusha_context_parser import token_context_candidates  # noqa: E402

SCHEMA = "fusha/standalone-parse@1"
PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}
CONTEXT_REQUIRED_FUNCTION_KEYS = {"ما", "وما", "لما", "انما", "إنما", "من", "لا", "إلا", "الا"}

_COLLISION_REGISTRY_PATH = os.path.join(_REPO, "fusha", "parser", "collision-classes.json")
with open(_COLLISION_REGISTRY_PATH, encoding="utf-8") as _cr_fh:
    _COLLISION_REGISTRY = json.load(_cr_fh)
HIGH_RISK_BARE_MATCH_SURFACES = set(_COLLISION_REGISTRY.get("high_risk_bare_match_surfaces") or [])
# I8 (partial): the registry is authoritative for a fired class's gate cap, route,
# and lattice tie-break order; the code below still decides WHETHER a class fires
# (trigger predicates stay reviewed code), it just stops hand-duplicating the
# literals the registry already names. `class_id` is the lookup key throughout.
_CLASS_BY_ID = {c["class_id"]: c for c in _COLLISION_REGISTRY.get("classes") or []}


class RegistryAuthorityError(RuntimeError):
    """A fired collision class's gate cap/route/filter_order must come from
    fusha/parser/collision-classes.json; there is no hardcoded historical
    fallback (Train E finding 2). A missing entry, or one missing a required
    field, for a class that just fired is a registry/code drift bug and must
    fail closed -- never silently recreate a shadow authority by reusing a
    superseded literal."""


def _registry_entry_or_raise(class_id):
    entry = _CLASS_BY_ID.get(class_id)
    if entry is None:
        raise RegistryAuthorityError(
            "collision class %r fired but has no entry in fusha/parser/collision-classes.json; "
            "the registry is the sole authority for gate cap/route/order, there is no fallback" % class_id
        )
    return entry


def _registry_vote(class_id):
    """(gate_rank, cap, filter_order) for a fired class, sourced from the registry.

    Fail closed: a missing registry entry, a missing/invalid
    `gate_effect.cap`, or a missing/non-int `filter_order` raises
    `RegistryAuthorityError` rather than silently substituting a hardcoded
    historical default.
    """
    entry = _registry_entry_or_raise(class_id)
    cap = (entry.get("gate_effect") or {}).get("cap")
    if cap not in GATE_RANK:
        raise RegistryAuthorityError(
            "collision class %r has no valid gate_effect.cap registered (got %r)" % (class_id, cap)
        )
    order = entry.get("filter_order")
    if not isinstance(order, int):
        raise RegistryAuthorityError(
            "collision class %r has no valid filter_order registered (got %r)" % (class_id, order)
        )
    return GATE_RANK[cap], cap, order


def _registry_route(class_id):
    """Route for a fired class, sourced from the registry. Fail closed: a
    missing registry entry, or a route that is not a registered list, raises
    `RegistryAuthorityError` rather than substituting a hardcoded default."""
    entry = _registry_entry_or_raise(class_id)
    route = entry.get("route")
    if not isinstance(route, list):
        raise RegistryAuthorityError(
            "collision class %r has no valid route registered (got %r)" % (class_id, route)
        )
    return list(route)


def _registry_canonical_unit_ids(class_id):
    entry = _CLASS_BY_ID.get(class_id)
    return list(entry.get("canonical_unit_ids") or []) if entry else []

# R4: noun|proper_noun -> ism, verb -> fil, particle -> harf.
POS_TRICHOTOMY = {"noun": "ism", "proper_noun": "ism", "verb": "fil", "particle": "harf"}
# Monotone gate lattice (Train E B1 repair): every _gate filter casts a vote
# capped at its own strength; the strongest (most-abstaining) vote wins. A
# weaker cap (e.g. source-risk pending_context) can demote the result when
# nothing stronger fires, but it can never mask a stronger vote that did fire.
GATE_RANK = {
    "blocked": 4,
    "lexical_collision_requires_context": 3,
    "pending_context": 2,
    "ambiguous": 1,
    "likely_from_internal_pattern": 0,
}
SOURCE_RISK_CAP_FILTER = "source_requires_nahw_function"
# R7 scoped collision: these qg roles carry the disputed stem's own reading
# and are withheld; everything else is affix/clitic layer and is preserved.
STEM_QG_ROLES = {"stem", "verb_stem", "adjective_stem"}
# cu-clitic-pronoun-role-discriminator: the clitic span survives but its role,
# which presupposes the disputed host category, degrades to undetermined.
PRONOUN_CLITIC_QG_ROLES = {"object_pronoun", "subject_pronoun"}
# R7 extension (Train E gap 2): these qg roles are affix labels/glosses that
# themselves assert the disputed host is a verb (verb_prefix, future_particle,
# derivative_prefix) or a noun/adjective carrying number morphology
# (plural_suffix). Their surface span survives (it is still visibly attached),
# but the role/label/gloss that would presuppose the disputed class degrades
# to undetermined, exactly like the pronoun-role discriminator above.
CLASS_PRESUPPOSING_QG_ROLES = {"verb_prefix", "future_particle", "derivative_prefix", "plural_suffix"}
# Train E follow-up defect A: the `class` values these degraded roles arrive
# with also assert the disputed host category on their own -- "qg-verb-prefix"
# names a VERB prefix, "qg-derivative-prefix"/"qg-plural-suffix" name
# derivational/number morphology, and "qg-object-pronoun"/"qg-subject-pronoun"
# name the pronoun as an argument OF A VERB. Renaming only `role` (leaving
# `class` untouched) still leaks the disputed identity. `qg-particle`
# (future_particle's class) is excluded: "س" is a particle regardless of
# which lexicon entry the disputed STEM resolves to, so that class asserts
# nothing about the disputed host.
CLASS_PRESUPPOSING_QG_CLASSES = {
    "qg-verb-prefix", "qg-derivative-prefix", "qg-plural-suffix",
    "qg-object-pronoun", "qg-subject-pronoun",
}
# Honest, class-neutral replacements: they name the segment as an affix or a
# clitic whose host is undetermined, without asserting verb/noun/adjective.
NEUTRAL_AFFIX_QG_CLASS = "qg-affix-undetermined"
NEUTRAL_CLITIC_QG_CLASS = "qg-clitic-undetermined"
# Roles that are independently licensed -- their class never presupposes the
# disputed stem_identity host category regardless of which lexicon entry
# wins (a preposition, conjunction, article, or a pinned function-particle
# cluster piece means the same thing either way) -- so they survive
# stem_identity scoping unchanged. This, together with STEM_QG_ROLES,
# PRONOUN_CLITIC_QG_ROLES, and CLASS_PRESUPPOSING_QG_ROLES above, is the
# COMPLETE triage of every role the clitic splitter / pattern engine can
# currently place into `qg_segments`. A role that lands in none of these
# buckets is untriaged, not neutral, and `_scope_collision_segments` below
# withholds it rather than assuming it is safe.
CLASS_NEUTRAL_QG_ROLES = {
    "prefix_conjunction", "prefix_resumption_fa", "prefix_preposition",
    "definite_article", "particle_inna", "ma_particle",
}
# Train E follow-up defect B: the ONE authoritative union of roles whose
# role/label/gloss/class presupposes the disputed stem_identity host
# category. `tools/validate_fusha_standalone_parse.py` imports this directly
# instead of hand-copying it, so the two can never silently drift apart.
CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES = (
    STEM_QG_ROLES | PRONOUN_CLITIC_QG_ROLES | CLASS_PRESUPPOSING_QG_ROLES
)


def _selected(seg_cands, morph_cands):
    if not morph_cands:
        return None, None
    morph = morph_cands[0]
    if morph.get("pos") == "particle":
        for cand in seg_cands:
            if cand.get("evidence_class") == "pinned_function_cluster":
                return cand, morph
    ref = morph.get("segment_candidate_ref", 0)
    if not isinstance(ref, int) or ref < 0 or ref >= len(seg_cands):
        morph["selection_status"] = "blocked"
        morph["selection_blocker"] = "dangling_segment_ref"
        morph["selection_blocker_detail"] = {
            "segment_candidate_ref": ref,
            "segment_candidate_count": len(seg_cands),
        }
        return None, morph
    selected = seg_cands[ref]
    selected_segments = selected.get("segments") or []
    selected_surface = "".join(seg.get("surface", "") for seg in selected_segments)
    selected_collapsed = len(selected_segments) == 1 and selected_segments[0].get("role") == "stem"
    rich_roles = {
        "prefix_preposition",
        "definite_article",
        "prefix_conjunction",
        "prefix_particle",
        "particle_inna",
        "ma_particle",
    }
    if selected_collapsed and morph.get("evidence_class") in {"largelexicon_sample", "largelexicon_full"}:
        for cand in seg_cands:
            segments = cand.get("segments") or []
            if len(segments) <= 1:
                continue
            if "".join(seg.get("surface", "") for seg in segments) != selected_surface:
                continue
            if any(seg.get("role") in rich_roles for seg in segments):
                return cand, morph
    return selected, morph


def _candidate_collision(surface, seg_cands, morph_cands, morph):
    """Top-score ties across `morph_cands`: an unsafe bare match, or `competing_segmentation`.

    Finding 1 (Train E repair): `competing_segmentation` fires whenever the
    tied top-scored candidates span >= 2 distinct `segment_candidate_ref`
    values, full stop -- i.e. the tie is between rival written SEGMENTATIONS
    (rival letter-ownership decompositions of the surface), never a same-
    segmentation identity question. A prior revision additionally required
    the tied candidates to disagree on identity (pos/lemma/root) before
    firing, which let `بالله` (a bā'+Allah split, ref 0, tied at top score
    against a whole-token largelexicon match, ref 1) silently commit to one
    segmentation whenever both rivals happened to resolve to the same
    lemma/pos/root. Same identity does not authorize choosing one
    segmentation over another -- the letters are still contested between two
    structurally different splits regardless of what either one resolves to.
    A same-ref tie (all tied candidates share one `segment_candidate_ref`,
    i.e. rival lexicon rows for the SAME segmentation, such as a same-ref
    `function_inventory` particle cluster tie) is not this filter's concern
    at all: that is R4/R5's job via `collision.competitors`, computed only
    over the selected stem's own competitors per R6.
    """
    if not morph:
        return None
    features = morph.get("features") or {}
    if features.get("match_basis") == "bare_match" and N.bare(surface) in HIGH_RISK_BARE_MATCH_SURFACES:
        return {
            "kind": "unsafe_bare_match",
            "surface": surface,
            "route": _registry_route("unsafe_bare_match"),
            "basis": features.get("match_basis"),
            "decided_by": "unsafe_bare_match",
            "reason": "bare-match largelexicon evidence is useful internally but not a public hover selection for this high-risk surface",
        }
    tops = []
    if morph_cands:
        best = max(float(c.get("score") or 0.0) for c in morph_cands)
        tops = [c for c in morph_cands if float(c.get("score") or 0.0) == best]
    if len(tops) < 2:
        return None
    refs = {c.get("segment_candidate_ref") for c in tops}
    if len(refs) <= 1:
        return None
    pos_values = {c.get("pos") for c in tops}
    lemmas = {c.get("lemma") for c in tops}
    return {
        "kind": "competing_segmentation",
        "surface": surface,
        "candidate_count_at_top_score": len(tops),
        "candidate_refs": sorted(int(ref) for ref in refs if ref is not None),
        "pos_values": sorted(str(v) for v in pos_values),
        "lemma_values": sorted(str(v) for v in lemmas if v is not None),
        "route": _registry_route("competing_segmentation"),
        "canonical_unit_ids": _registry_canonical_unit_ids("competing_segmentation"),
        "decided_by": "competing_segmentation",
    }


def _skeleton_collision(surface, seg_cands, morph, selected_seg=None, morph_cands=None):
    """R4/R5: classify the SELECTED candidate's own competitor set.

    Competitors come from morph["collision"]["competitors"], which
    fusha_pattern_engine.py scopes to the one stem this candidate was matched
    against (R6): never a union over other segmentation hypotheses, so a
    rejected split can never manufacture a competitor here.

    R4 extension (Train E gap 1): a `function_inventory` candidate carries no
    `collision` field of its own (it is not built via `_candidate_from_row`),
    so if it OUTSCORES a sibling lexicon candidate for the same stem, `morph`
    here (the selected/winning candidate) can be the function-word reading
    while the real corpus `pos_trichotomy_conflict`/`root_conflict` data sits
    on the outscored sibling. Which candidate wins scoring must never decide
    whether a corpus-defined collision gets reported, so when the selected
    candidate itself carries fewer than 2 competitors, this falls back to any
    sibling in `morph_cands` sharing the same `segment_candidate_ref` (the
    same stem, per R6 -- never a different segmentation hypothesis) that does
    carry >= 2 competitors.

    R7 scope is derived from `selected_seg` (the segment candidate `_selected`
    actually returned), not from `morph["segment_candidate_ref"]`: `_selected`
    can promote a richer multi-segment candidate over a collapsed whole-token
    largelexicon match for the same surface, and the withheld/preserved
    boundary must track that promotion, not the collapsed ref (Train E I4).
    `seg_cands`/`morph.segment_candidate_ref` remain a fallback for callers
    that have not yet resolved a selected segment candidate.
    """
    if not morph:
        return None
    collision_source = morph.get("collision") or {}
    competitors = collision_source.get("competitors") or []
    if len(competitors) < 2 and morph_cands:
        ref = morph.get("segment_candidate_ref")
        for cand in morph_cands:
            if cand is morph or cand.get("segment_candidate_ref") != ref:
                continue
            sibling_collision = cand.get("collision") or {}
            sibling_competitors = sibling_collision.get("competitors") or []
            if len(sibling_competitors) >= 2:
                collision_source = sibling_collision
                competitors = sibling_competitors
                break
    if len(competitors) < 2:
        return None
    classes = {POS_TRICHOTOMY.get(c.get("pos")) for c in competitors}
    classes.discard(None)
    if len(classes) >= 2:
        kind = "pos_trichotomy_conflict"
    else:
        roots = {c.get("root") for c in competitors if c.get("root")}
        kind = "root_conflict" if len(roots) >= 2 else None
    if not kind:
        return None
    if selected_seg is not None:
        seg_count = len(selected_seg.get("segments") or [])
    else:
        ref = morph.get("segment_candidate_ref")
        seg_count = 0
        if isinstance(ref, int) and 0 <= ref < len(seg_cands):
            seg_count = len(seg_cands[ref].get("segments") or [])
    scope = "stem_identity" if seg_count > 1 else "whole_token"
    return {
        "kind": kind,
        "scope": scope,
        "surface": surface,
        "route": _registry_route(kind),
        "competing_entry_ids": collision_source.get("competing_entry_ids") or [],
        "canonical_unit_ids": _registry_canonical_unit_ids(kind),
        "decided_by": kind,
    }


def _scope_collision_segments(qg_segments):
    """R7: under stem_identity scope, withhold the stem, keep the rest.

    R7 extension (Train E gap 2): a pronoun-role clitic degrades to
    `clitic_undetermined` because its span is genuinely still there, only its
    ROLE presupposes the disputed host class. The same reasoning applies to
    `CLASS_PRESUPPOSING_QG_ROLES` (verb_prefix/future_particle/
    derivative_prefix/plural_suffix): the letters are real surface material,
    but their role/label/gloss assert a specific verb- or noun-shaped analysis
    of the disputed stem, so they degrade to `affix_undetermined` rather than
    keeping a label that presupposes the class the collision leaves open.

    Train E follow-up defect A: renaming `role` alone is not enough. `class`
    values like `qg-verb-prefix`/`qg-derivative-prefix`/`qg-plural-suffix`/
    `qg-object-pronoun`/`qg-subject-pronoun` (see `CLASS_PRESUPPOSING_QG_CLASSES`)
    independently assert the same disputed host category, so both degraded
    branches below also overwrite `class` with the honest, class-neutral
    `NEUTRAL_AFFIX_QG_CLASS`/`NEUTRAL_CLITIC_QG_CLASS`.

    Genuinely class-neutral material (an independently licensed preposition,
    conjunction, article, or pinned function-particle-cluster piece --
    `CLASS_NEUTRAL_QG_ROLES`) is preserved unchanged. Train E follow-up
    defect B: a role that is in none of `STEM_QG_ROLES`,
    `PRONOUN_CLITIC_QG_ROLES`, `CLASS_PRESUPPOSING_QG_ROLES`, or
    `CLASS_NEUTRAL_QG_ROLES` is untriaged, not neutral -- it is withheld
    (dropped) rather than assumed safe to pass through, matching this
    module's "blank beats wrong" posture.
    """
    out = []
    for seg in qg_segments:
        role = seg.get("role")
        if role in STEM_QG_ROLES:
            continue
        if role in PRONOUN_CLITIC_QG_ROLES:
            seg = dict(seg)
            seg["role"] = "clitic_undetermined"
            seg["label"] = "UNDET"
            seg["gloss_contribution"] = None
            seg["class"] = NEUTRAL_CLITIC_QG_CLASS
            out.append(seg)
        elif role in CLASS_PRESUPPOSING_QG_ROLES:
            seg = dict(seg)
            seg["role"] = "affix_undetermined"
            seg["label"] = "UNDET"
            seg["gloss_contribution"] = None
            seg["class"] = NEUTRAL_AFFIX_QG_CLASS
            out.append(seg)
        elif role in CLASS_NEUTRAL_QG_ROLES:
            out.append(dict(seg))
        # else: an untriaged role is withheld outright (fail-closed) rather
        # than assumed class-neutral (Train E follow-up defect B).
    return out


def _strip_collision_identity(cand, decided_by=None, evidence_keys=None):
    """No lemma/root/pos/voice/number/gloss for a withheld/rival-tied candidate.

    `evidence_keys` names where the deciding evidence lives: R4/R5 (skeleton
    collision) decide from `collision.competitors`; `competing_segmentation`
    decides from the tied `morphology_candidates` set itself (there is no
    single stem's `collision.competitors` to point at -- the tie is across
    segmentations, not entries for one segmentation).
    """
    cand["lemma"] = None
    cand["root"] = None
    cand["pos"] = None
    cand["pattern"] = None
    cand["gloss_hint"] = None
    feats = cand.get("features")
    if isinstance(feats, dict):
        for key in ("voice", "verb_form", "number"):
            feats.pop(key, None)
        if decided_by:
            feats["identity_withheld_decided_by"] = {
                "filter": decided_by,
                "evidence_keys": list(evidence_keys or ["collision.competitors"]),
            }


def _function_needs_context(surface, morph):
    if not morph or morph.get("evidence_class") != "function_inventory":
        return False
    keys = {surface, N.norm_strict(surface), N.bare(surface)}
    return bool(keys & CONTEXT_REQUIRED_FUNCTION_KEYS & set(FUNCTION_WORDS))


def _gate(surface, seg_cands, morph, context, morph_cands=None, selected_seg=None):
    """Monotone gate lattice, most-abstaining-wins (Train E B1 repair).

    Every filter below casts a vote: (rank, gate_name, collision_or_None,
    tie_break_priority). The final gate is the highest-ranked vote; ties
    within a rank are broken by tie_break_priority (lower wins), preserving
    the previous evaluation order. This guarantees a weaker cap (source-risk
    pending_context) can never mask a stronger vote (a skeleton collision, an
    unsafe bare match, a segmentation/POS collision, or blocked) that also
    fired for the same candidate; it only demotes the result when nothing
    stronger fired.
    """
    bare = N.bare(surface)
    if not morph:
        return "blocked", None
    if morph.get("selection_blocker") == "dangling_segment_ref":
        return "blocked", {
            "kind": "dangling_segment_ref",
            "surface": surface,
            **(morph.get("selection_blocker_detail") or {}),
            "route": ["validator", "sarf"],
            "reason": "morphology candidate references a segment candidate that does not exist",
        }

    votes = []

    # source_provenance (R1): a CAP, not a mask. Typed decided_by evidence is
    # recorded on the candidate whenever the flag is present, independent of
    # whether this vote ends up winning the lattice. I8 (partial): cap and
    # tie-break order come from the registry, not a hardcoded literal.
    risk_flags = set((morph.get("features") or {}).get("source_risk_flags") or [])
    if "requires_nahw_function" in risk_flags:
        feats = morph.setdefault("features", {})
        feats["gate_cap_decided_by"] = {
            "filter": SOURCE_RISK_CAP_FILTER,
            "evidence_keys": ["features.source_risk_flags"],
        }
        rank, cap, order = _registry_vote(SOURCE_RISK_CAP_FILTER)
        votes.append((rank, cap, None, order))

    # skeleton_collision (R4/R5), scoped to the selected stem (R6/R7).
    skeleton = _skeleton_collision(surface, seg_cands, morph, selected_seg=selected_seg, morph_cands=morph_cands)
    if skeleton:
        rank, cap, order = _registry_vote(skeleton.get("kind"))
        votes.append((rank, cap, skeleton, order))

    collision = _candidate_collision(surface, seg_cands, morph_cands or [], morph)
    if collision:
        rank, cap, order = _registry_vote(collision.get("kind"))
        votes.append((rank, cap, collision, order))

    if _function_needs_context(surface, morph) or bare in {"ما", "وما", "لما", "انما", "إنما"}:
        votes.append((GATE_RANK["pending_context"], "pending_context", None, 1))

    if any(c.get("status") == "pending_context" for c in context):
        votes.append((GATE_RANK["pending_context"], "pending_context", None, 2))

    if len(seg_cands) > 1 and morph.get("evidence_class") not in {"seed_lexicon", "pinned_pattern"}:
        votes.append((GATE_RANK["ambiguous"], "ambiguous", None, 0))
    elif morph.get("evidence_class") in {"seed_lexicon", "pinned_pattern", "function_inventory", "largelexicon_sample", "largelexicon_full"}:
        votes.append((GATE_RANK["likely_from_internal_pattern"], "likely_from_internal_pattern", None, 0))
    else:
        votes.append((GATE_RANK["ambiguous"], "ambiguous", None, 1))

    votes.sort(key=lambda vote: (-vote[0], vote[3]))
    _rank, gate, winning_collision, _priority = votes[0]
    return gate, winning_collision


def _parse_key(qg, morph):
    labels = [seg.get("label") or seg.get("role", "SEG").upper() for seg in qg]
    pos = (morph or {}).get("pos") or "unknown"
    return {
        "key": "+".join(labels) if labels else "SURFACE",
        "summary": "%s candidate from %s" % (pos, (morph or {}).get("evidence_class", "surface")),
    }


def _hover(surface, qg, morph, context, gate):
    if gate == "lexical_collision_requires_context":
        return {
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "token_contribution_gloss": None,
            "morphline": "lexical collision requires context",
            "segments": qg,
            "context_notes": [c.get("explanation") for c in context],
            "learner_explanation": "Multiple analyses compete here; keep the token pending until source/context evidence selects one.",
        }
    features = (morph or {}).get("features") or {}
    # R2/R3: identity withheld at candidate build time; no public gloss either,
    # even if an affix qg segment still carries its own gloss fragment.
    identity_withheld = bool(features.get("entry_identity_status") or features.get("root_identity_status"))
    if identity_withheld:
        gloss = None
    else:
        segment_bits = [seg.get("gloss_contribution") for seg in qg if seg.get("gloss_contribution")]
        gloss = " + ".join(segment_bits) if segment_bits else (morph or {}).get("gloss_hint")
        if not gloss:
            gloss = "surface candidate"
    explanation = "Token preview preserves visible grammar pieces."
    if gate == "pending_context":
        explanation = "Context is needed before this can become a certified token hover."
    return {
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "token_contribution_gloss": gloss,
        "morphline": _parse_key(qg, morph)["summary"],
        "segments": qg,
        "context_notes": [c.get("explanation") for c in context],
        "learner_explanation": explanation,
    }


def _token(idx, wt, db="smoke"):
    surface = wt["surface"]
    segs = split_clitics(surface)
    morph = build_morphology(surface, segs, db=db)
    selected_seg, selected_morph = _selected(segs, morph)
    qg = preview_segments(surface, selected_seg, selected_morph) if selected_seg and selected_morph else []
    tok = {
        "index": idx,
        "ref": "tok:%d" % idx,
        "surface": surface,
        "loc": None,
        "span": {"start": wt.get("start"), "end": wt.get("end")},
        "normalization": {
            "norm_strict": N.norm_strict(surface),
            "bare": N.bare(surface),
        },
        "segment_candidates": segs,
        "morphology_candidates": morph,
        "context_candidates": [],
        "selected_preview": None,
        "qg_segments": qg,
        "hover_preview": None,
        "confidence_gate": "blocked",
        "blocker_class": None,
        "blocker_reason": None,
    }
    tok["selected_preview"] = {
        "segment_candidate_rank": selected_seg.get("rank") if selected_seg else None,
        "morphology_rank": selected_morph.get("rank") if selected_morph else None,
        "parse_key": _parse_key(qg, selected_morph),
    } if selected_seg and selected_morph else None
    return tok


def parse_text(text, document_id=None, db="smoke"):
    normalized, ops = TC.normalize_with_ops(text)
    wtokens = [wt for wt in TC.whitespace_tokens(text) if wt.get("kind") == "word"]
    tokens = [_token(i, wt, db=db) for i, wt in enumerate(wtokens)]
    ctx_by_idx = token_context_candidates(tokens)
    diagnostics = []
    for tok in tokens:
        ctx = ctx_by_idx.get(tok["index"], [])
        tok["context_candidates"] = ctx
        seg, morph = _selected(tok.get("segment_candidates") or [], tok.get("morphology_candidates") or [])
        gate, collision = _gate(
            tok["surface"], tok.get("segment_candidates") or [], morph, ctx,
            tok.get("morphology_candidates") or [], selected_seg=seg,
        )
        tok["confidence_gate"] = gate
        if collision:
            tok["collision"] = collision
            for cand in tok.get("morphology_candidates") or []:
                if cand.get("rank") == 1:
                    cand["selection_status"] = "candidate_only"
                    cand["selection_blocker"] = gate
                    if collision.get("kind") in {"pos_trichotomy_conflict", "root_conflict"}:
                        _strip_collision_identity(cand, decided_by=collision.get("kind"))
                    elif collision.get("kind") == "competing_segmentation":
                        # I9: none of the tied rival segmentations may be
                        # emitted as "the" selected function/POS/entry.
                        _strip_collision_identity(
                            cand, decided_by=collision.get("kind"),
                            evidence_keys=["morphology_candidates", "segment_candidate_ref"],
                        )
            if collision.get("scope") == "stem_identity":
                tok["qg_segments"] = _scope_collision_segments(tok.get("qg_segments") or [])
            else:
                tok["qg_segments"] = []
            tok["selected_preview"] = None
        if gate in {"pending_context", "ambiguous", "blocked", "lexical_collision_requires_context"}:
            blocked_class = "no_parse_candidate"
            if collision and collision.get("kind") == "dangling_segment_ref":
                blocked_class = "dangling_segment_ref"
            tok["blocker_class"] = {
                "pending_context": "context_sensitive",
                "ambiguous": "ambiguous_surface",
                "blocked": blocked_class,
                "lexical_collision_requires_context": "lexical_collision",
            }[gate]
            tok["blocker_reason"] = (
                "multiple high-risk analyses compete; no public hover projection selected"
                if gate == "lexical_collision_requires_context"
                else "morphology candidate references a missing segment candidate"
                if blocked_class == "dangling_segment_ref"
                else "standalone parser preview is not source-address certification"
            )
        tok["hover_preview"] = _hover(tok["surface"], tok.get("qg_segments") or [], morph, ctx, gate)
        for c in ctx:
            diagnostics.append({
                "target": tok["ref"],
                "issue_class": c.get("relation"),
                "gate": c.get("gate", "two_vote_required"),
                "route": "nahw" if "ma_" in c.get("relation", "") or "govern" in c.get("relation", "") else "sarf",
                "explanation": c.get("explanation"),
            })
    return {
        "schema": SCHEMA,
        "input_mode": "arbitrary_typing",
        "db": db,
        "document_id": document_id,
        "raw_input": text,
        "normalized_input": normalized,
        "normalization_ops": ops,
        "tokens": tokens,
        "diagnostics": diagnostics,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "source_boundary": {
            "original_preserved": True,
            "external_text_copied": False,
            "quran_text_altered": False,
        },
        "summary": {
            "live_writes": 0,
            "n_tokens": len(tokens),
            "n_pending_context": sum(1 for t in tokens if t["confidence_gate"] == "pending_context"),
            "n_ambiguous": sum(1 for t in tokens if t["confidence_gate"] == "ambiguous"),
            "n_lexical_collision": sum(1 for t in tokens if t["confidence_gate"] == "lexical_collision_requires_context"),
        },
    }


def emit_fixtures(path):
    from tools.validate_fusha_standalone_parse import FIXTURES  # noqa: E402
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for text in FIXTURES:
            fh.write(json.dumps(parse_text(text), ensure_ascii=False, sort_keys=True) + "\n")
    print("wrote %d fixtures -> %s" % (len(FIXTURES), path))


def main():
    ap = argparse.ArgumentParser(description="Standalone Fusha parser/checker MVP.")
    ap.add_argument("--text")
    ap.add_argument("--out")
    ap.add_argument("--emit-fixtures")
    ap.add_argument("--db", choices=["smoke", "largelexicon"], default="smoke")
    args = ap.parse_args()
    if args.emit_fixtures:
        emit_fixtures(args.emit_fixtures)
        return 0
    if args.text is None:
        ap.error("need --text or --emit-fixtures")
    rec = parse_text(args.text, db=args.db)
    data = json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(data + "\n")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
