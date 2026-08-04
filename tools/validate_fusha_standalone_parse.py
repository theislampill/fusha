#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the standalone Fusha parser MVP output.

This is the Mode C/preview gate: it checks source-clean JSON, qg class safety,
segment concatenation, clitic preservation, ambiguity preservation, and no fake
source certainty. It is intentionally stricter than a demo script because this
kernel feeds Qamus/RH-LIVE authoring later.
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402
from tools import fusha_standalone_parse as parser  # noqa: E402

SCHEMA = "fusha/standalone-parse@1"

PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}

ALLOWED_QG_CLASSES = {
    "qg-verb-prefix",
    "qg-verb",
    "qg-verb-stem",
    "qg-subject-pronoun",
    "qg-object-pronoun",
    "qg-possessive-pronoun",
    "qg-noun",
    "qg-noun-stem",
    "qg-adjective",
    "qg-dual-suffix",
    "qg-plural-suffix",
    "qg-derivative-prefix",
    "qg-proper-noun",
    "qg-pronoun",
    "qg-preposition",
    "qg-oath",
    "qg-comitative",
    "qg-particle",
    "qg-conjunction",
    "qg-negative",
    "qg-result",
    "qg-result-fa",
    "qg-lam",
    "qg-ma-particle",
    "qg-article",
    "qg-relative",
    "qg-vocative",
    "qg-exception",
    "qg-case",
    "qg-relation",
    # Train E follow-up defect A: honest class-neutral replacements emitted by
    # _scope_collision_segments when a class-presupposing affix/clitic role
    # degrades under a stem_identity collision (see docstring there).
    "qg-affix-undetermined",
    "qg-clitic-undetermined",
}

LEAK_RE = re.compile(
    r"(?:MCP|QAC|Tafsir|Quran\.com|Corpus|Tanzil|source[-_ ]?photo|/srv|C:\\|"
    r"process prose|external evidence|Ayat|i.?rab tafsir center)",
    re.I,
)

FIXTURES = [
    "إنما الأعمال بالنيات",
    "قال رسول الله",
    "من كان يؤمن بالله واليوم الآخر",
    "فسيكفيكهم",
    "بالكتاب",
    "وما",
    "لمّا",
    "إنما",
    "يستغفرون",
    "مستغفرين",
    "فأهلكناهم",
    "يسألك",
]


def _public_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"raw_input", "surface"}:
                continue
            yield from _public_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _public_strings(v)
    elif isinstance(obj, str):
        yield obj


def _segments_concat(token, key):
    for cand in token.get(key) or []:
        segs = cand.get("segments") if isinstance(cand, dict) else None
        if segs and "".join(s.get("surface", "") for s in segs) != token.get("surface"):
            return False
    return True


# Train E gap 3: roles a stem_identity collision must never retain because
# their role/label/gloss presupposes the disputed noun/verb/adjective class
# (the disputed stem itself, or an affix whose reading commits to a verb- or
# noun-shaped analysis). Production withholds/reclassifies these
# (tools/fusha_standalone_parse.py `_scope_collision_segments`); this asserts
# the restriction directly instead of trusting that surviving segments merely
# concatenating back to an ordered subset of the surface proves it.
#
# Train E follow-up defect B: this used to be a hand-typed duplicate of the
# parser's STEM_QG_ROLES | PRONOUN_CLITIC_QG_ROLES | CLASS_PRESUPPOSING_QG_ROLES
# union, which could silently drift from production. It is now a direct
# reference to the parser's own authoritative object -- not a copy -- so a
# future production change to that union propagates here automatically.
CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES = parser.CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES


def _retained_segments_ordered_subset(qg, surface):
    """True when each qg segment's surface appears in `surface` in left-to-right,
    non-overlapping order (Train E I2). A stem_identity collision withholds the
    disputed stem but preserves the surrounding affix/clitic segments in place, so
    the retained pieces cannot concatenate back to the full surface -- they must
    still land at the right, non-reordered, non-overlapping positions."""
    pos = 0
    for seg in qg:
        piece = seg.get("surface", "")
        if not piece:
            continue
        idx = surface.find(piece, pos)
        if idx == -1:
            return False
        pos = idx + len(piece)
    return True


def validate_record(rec):
    errors = []
    if rec.get("schema") != SCHEMA:
        errors.append("schema must be %s" % SCHEMA)
    if rec.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append("public_boundary must be source-clean qamus/authored/en")
    sb = rec.get("source_boundary") or {}
    if sb.get("original_preserved") is not True or sb.get("external_text_copied") is not False:
        errors.append("source_boundary must preserve original and forbid copied external text")
    if rec.get("input_mode") != "arbitrary_typing":
        errors.append("standalone MVP validator expects arbitrary_typing mode")
    if rec.get("raw_input") is None or rec.get("raw_input") == "":
        errors.append("raw_input required")
    if (rec.get("summary") or {}).get("live_writes") != 0:
        errors.append("live_writes must be 0")

    for s in _public_strings(rec):
        if LEAK_RE.search(s):
            errors.append("public string leaks provenance/process text: %r" % s[:80])
            break

    for tok in rec.get("tokens") or []:
        surf = tok.get("surface") or ""
        if tok.get("loc") is not None:
            errors.append("%s: arbitrary token carries source loc" % surf)
        if tok.get("confidence_gate") in {"certified", "auto_safe", "source_certified"}:
            errors.append("%s: arbitrary token claims source certainty" % surf)
        if not _segments_concat(tok, "segment_candidates"):
            errors.append("%s: segment candidate does not concatenate" % surf)
        qg = tok.get("qg_segments") or []
        collision = tok.get("collision") or {}
        # Train E I2: a collision-withheld token is not an ordinary complete
        # segmentation. Whole-token withholding (or a non-stem_identity scope)
        # projects no segments; stem_identity withholding retains the surrounding
        # affix/clitic segments in place while withholding the disputed stem, so
        # they can only be an ordered, non-overlapping SUBSET of the surface, never
        # a full concatenation. Ordinary (non-collision) tokens keep the original,
        # unweakened complete-concatenation check.
        if collision:
            if collision.get("scope") == "stem_identity":
                if not qg:
                    errors.append("%s: stem_identity collision withholding dropped all affix/clitic coverage" % surf)
                elif not _retained_segments_ordered_subset(qg, surf):
                    errors.append("%s: stem_identity collision retained segments are not an ordered subset of the surface" % surf)
                else:
                    leaked_roles = {seg.get("role") for seg in qg} & CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES
                    if leaked_roles:
                        errors.append(
                            "%s: stem_identity collision retained class-presupposing role(s) %s; "
                            "the disputed stem and any host-class-presupposing affix must be withheld "
                            "or reclassified, not merely form an ordered subset of the surface"
                            % (surf, sorted(leaked_roles))
                        )
                    # Train E follow-up defect A: a role can be honestly
                    # renamed (e.g. verb_prefix -> affix_undetermined) while
                    # its `class` still asserts the same disputed host
                    # category (qg-verb-prefix, qg-derivative-prefix,
                    # qg-plural-suffix, qg-object-pronoun, qg-subject-pronoun).
                    # Check `class` independently of `role` so a rename that
                    # forgets to also neutralize `class` is still caught.
                    leaked_classes = {seg.get("class") for seg in qg} & parser.CLASS_PRESUPPOSING_QG_CLASSES
                    if leaked_classes:
                        errors.append(
                            "%s: stem_identity collision retained class-presupposing class(es) %s "
                            "on a segment; renaming the role is not enough -- the class must also "
                            "be withheld or replaced with a class-neutral value"
                            % (surf, sorted(leaked_classes))
                        )
            elif collision.get("scope") == "shared_class_neutral_prefix":
                # Train E finding 2: a genuine competing_segmentation tie may
                # retain ONLY the exact-span, exact-ownership class-neutral
                # prefix/article every tied rival agreed on -- never the
                # disputed stem or any host-class-presupposing segment, even
                # though this scope is not a single-candidate stem_identity
                # withholding.
                if not qg:
                    errors.append("%s: shared_class_neutral_prefix scope must retain its shared segment(s)" % surf)
                elif not _retained_segments_ordered_subset(qg, surf):
                    errors.append("%s: shared_class_neutral_prefix retained segments are not an ordered subset of the surface" % surf)
                else:
                    non_neutral = {seg.get("role") for seg in qg} - parser.CLASS_NEUTRAL_QG_ROLES
                    if non_neutral:
                        errors.append(
                            "%s: shared_class_neutral_prefix scope retained non-class-neutral role(s) %s; "
                            "only the exact shared class-neutral span may survive a competing_segmentation tie"
                            % (surf, sorted(non_neutral))
                        )
            elif qg:
                errors.append("%s: collision withholding outside stem_identity/shared_class_neutral_prefix scope must project no qg_segments" % surf)
            hover_gloss = (tok.get("hover_preview") or {}).get("token_contribution_gloss")
            if hover_gloss is not None:
                errors.append("%s: collision-withheld token must not carry a public token_contribution_gloss, got %r" % (surf, hover_gloss))
        elif qg and "".join(seg.get("surface", "") for seg in qg) != surf:
            errors.append("%s: qg_segments do not concatenate" % surf)
        for seg in qg:
            if seg.get("class") not in ALLOWED_QG_CLASSES:
                errors.append("%s: unsupported qg class %r" % (surf, seg.get("class")))
        if tok.get("selected_preview") and not qg:
            errors.append("%s: selected_preview without qg_segments" % surf)
        if N.bare(surf) in {"وما", "ما", "لما", "انما"}:
            # I9: وما/لما can tie a prefix+ما split against a whole-token particle
            # reading, which now correctly abstains one tier stronger
            # (lexical_collision_requires_context, competing_segmentation) instead
            # of silently picking the split. That is still context-gated, not a
            # certified pick, so it belongs in the allowed set alongside the
            # single-segmentation pending/ambiguous/likely outcomes.
            if tok.get("confidence_gate") not in {
                "pending_context", "ambiguous", "likely_from_internal_pattern",
                "lexical_collision_requires_context",
            }:
                errors.append("%s: function particle not context-gated" % surf)
        if N.bare(surf).startswith("ب") and len(N.bare(surf)) > 2:
            if qg and not any(seg.get("class") == "qg-preposition" for seg in qg):
                errors.append("%s: bāʾ-host token lacks preposition segment" % surf)
        roles = [seg.get("role") for seg in qg]
        if any(r in roles for r in ("object_pronoun", "possessive_pronoun")):
            if not any(seg.get("class") in {"qg-object-pronoun", "qg-possessive-pronoun", "qg-pronoun"} for seg in qg):
                errors.append("%s: pronoun role lacks pronoun qg class" % surf)
            if not collision:
                headline = ((tok.get("hover_preview") or {}).get("token_contribution_gloss") or "").lower()
                if "pronoun" not in headline and not any(word in headline for word in ("you", "them", "him", "her", "it", "us", "me")):
                    errors.append("%s: hover headline hides attached pronoun contribution" % surf)
        if any(seg.get("class") == "qg-preposition" for seg in qg) and not collision:
            headline = ((tok.get("hover_preview") or {}).get("token_contribution_gloss") or "").lower()
            if not any(word in headline for word in ("by", "with", "in", "for", "to", "preposition")):
                errors.append("%s: hover headline hides attached preposition contribution" % surf)
        for cand in tok.get("morphology_candidates") or []:
            if cand.get("root") and cand.get("evidence_class") not in {"seed_lexicon", "pinned_pattern"}:
                errors.append("%s: root lacks seed/pinned evidence" % surf)
        if len(tok.get("segment_candidates") or []) > 1 and tok.get("confidence_gate") == "certified":
            errors.append("%s: ambiguous segmentation marked certified" % surf)
    return errors


def _self_test():
    failures = []
    for text in FIXTURES:
        rec = parser.parse_text(text)
        errs = validate_record(rec)
        if errs:
            failures.append("%s -> %s" % (text, errs[:3]))
    joined = parser.parse_text(" ".join(FIXTURES))
    if len(joined.get("tokens") or []) < len(FIXTURES):
        failures.append("joined fixtures should emit at least one token per fixture phrase")
    # فسيكفيكهم/فأهلكناهم/مستغفرين have a unique top-scored segmentation in the
    # smoke lexicon; يسألك and بالكتاب do NOT (see below) and were removed from
    # this list under Train E finding 1.
    for surface in ("فسيكفيكهم", "فأهلكناهم", "مستغفرين"):
        rec = parser.parse_text(surface)
        tok = (rec.get("tokens") or [{}])[0]
        if not tok.get("qg_segments"):
            failures.append("%s should expose qg_segments" % surface)
    # Component regressions from RH-LIVE ANDONs: future particle, imperfect prefix, subject/object pieces,
    # derivative prefix, and plural suffix must not disappear behind a host-only preview.
    # فأهلكناهم's inner نا is UNVOWELED and so genuinely ambiguous between subject and object
    # readings on the surface alone (see R1/F6 elsewhere in this repo); the corrected parser
    # exposes it honestly as clitic_undetermined rather than pinning the unvoweled form to
    # subject_pronoun, while the trailing هم still resolves to the unambiguous object_pronoun.
    role_expect = {
        "فسيكفيكهم": {"prefix_resumption_fa", "future_particle", "verb_prefix", "verb_stem", "object_pronoun"},
        "فأهلكناهم": {"prefix_resumption_fa", "verb_stem", "clitic_undetermined", "object_pronoun"},
        "مستغفرين": {"derivative_prefix", "adjective_stem", "plural_suffix"},
    }
    for surface, expected in role_expect.items():
        rec = parser.parse_text(surface)
        tok = (rec.get("tokens") or [{}])[0]
        roles = {seg.get("role") for seg in tok.get("qg_segments") or []}
        missing = expected - roles
        if missing:
            failures.append("%s qg roles missing %s; got %s" % (surface, sorted(missing), sorted(roles)))

    # Train E finding 1: يسألك ("ي+سأل+ك" split) and بالكتاب ("ب+ال+كتاب" split)
    # each also match their smoke seed_lexicon entry's own listed whole-token
    # form at an equally-tied top score (سأل lists يسألك directly; كِتَاب lists
    # بالكتاب directly). This is the same same-identity/different-ref shape as
    # بالله, so they now correctly abstain instead of exposing the prefix/
    # object-pronoun or preposition/article/stem roles those entries used to
    # demonstrate -- verb_prefix/verb_stem/object_pronoun coverage remains via
    # فسيكفيكهم above.
    for tied_surface in ("يسألك", "بالكتاب"):
        tied_rec = parser.parse_text(tied_surface)
        tied_tok = (tied_rec.get("tokens") or [{}])[0]
        tied_collision = tied_tok.get("collision") or {}
        if tied_collision.get("kind") != "competing_segmentation":
            failures.append(
                "finding1: %r must reach collision.kind=competing_segmentation, got %r"
                % (tied_surface, tied_collision.get("kind"))
            )
        if tied_tok.get("qg_segments"):
            failures.append("finding1: %r must clear qg_segments under competing_segmentation, got %r"
                             % (tied_surface, tied_tok.get("qg_segments")))
    # I9 (red-first): a tied top-scored function-inventory pair spanning >= 2
    # distinct segment_candidate_ref values (لما as ل+ما vs whole-token لَمَّا;
    # وما as و+ما vs whole-token وما) must abstain as competing_segmentation
    # instead of silently committing to the split reading. Every rival is
    # preserved (candidate_refs names both), the gate is the stronger
    # lexical_collision_requires_context tier, and no selected function/POS/
    # gloss survives.
    for i9_surface in ("لما", "وما"):
        i9_rec = parser.parse_text(i9_surface, db="largelexicon")
        i9_tok = (i9_rec.get("tokens") or [{}])[0]
        i9_collision = i9_tok.get("collision") or {}
        if i9_collision.get("kind") != "competing_segmentation":
            failures.append(
                "I9: %r must reach collision.kind=competing_segmentation, got %r"
                % (i9_surface, i9_collision.get("kind"))
            )
        if i9_tok.get("confidence_gate") != "lexical_collision_requires_context":
            failures.append("I9: %r must reach the lexical_collision_requires_context gate, got %r"
                             % (i9_surface, i9_tok.get("confidence_gate")))
        if i9_tok.get("qg_segments"):
            failures.append("I9: %r must clear qg_segments under competing_segmentation, got %r"
                             % (i9_surface, i9_tok.get("qg_segments")))
        if i9_tok.get("selected_preview") is not None:
            failures.append("I9: %r must clear selected_preview under competing_segmentation" % i9_surface)
        if len(i9_collision.get("candidate_refs") or []) < 2:
            failures.append("I9: %r must preserve >= 2 rival segment_candidate_ref values, got %r"
                             % (i9_surface, i9_collision.get("candidate_refs")))
        i9_top = (i9_tok.get("morphology_candidates") or [{}])[0]
        if i9_top.get("lemma") is not None or i9_top.get("pos") is not None or i9_top.get("root") is not None:
            failures.append("I9: %r selected candidate must have lemma/pos/root withheld, got lemma=%r pos=%r root=%r"
                             % (i9_surface, i9_top.get("lemma"), i9_top.get("pos"), i9_top.get("root")))
        if (i9_tok.get("hover_preview") or {}).get("token_contribution_gloss") is not None:
            failures.append("I9: %r must not carry a public token_contribution_gloss" % i9_surface)

    # I9 positive control: إنما has exactly one top-scored segmentation (the
    # pinned particle cluster) and must be completely unaffected.
    i9_control = parser.parse_text("إنما", db="largelexicon")
    i9_control_tok = (i9_control.get("tokens") or [{}])[0]
    if i9_control_tok.get("collision") is not None:
        failures.append("I9 control: إنما must not gain a collision, got %r" % i9_control_tok.get("collision"))

    # I9 hostile fixture (red-first, Train E finding 1): بالله ties two
    # DIFFERENT segment_candidate_ref values at top score (a bā'+Allah split
    # vs. a whole-token largelexicon match). A prior revision exempted this
    # because both rivals happen to resolve to the SAME identity
    # (lemma/pos/root agree) -- but same identity does not authorize choosing
    # one SEGMENTATION over another; the letters could still be owned either
    # way (bā' + Allah, or a single whole-token match with no bā' prefix at
    # all). This must reach collision/abstention exactly like لما/وما: both
    # rival refs preserved, no selected preview, no qg claim, and no
    # identity/function/meaning/gloss/certification output.
    ball_rec = parser.parse_text("بالله", db="largelexicon")
    ball_tok = (ball_rec.get("tokens") or [{}])[0]
    ball_collision = ball_tok.get("collision") or {}
    if ball_collision.get("kind") != "competing_segmentation":
        failures.append(
            "finding1: بالله must reach collision.kind=competing_segmentation "
            "even though its tied rivals share one identity, got %r" % ball_collision.get("kind")
        )
    if ball_tok.get("confidence_gate") != "lexical_collision_requires_context":
        failures.append("finding1: بالله must reach the lexical_collision_requires_context gate, got %r"
                         % ball_tok.get("confidence_gate"))
    if ball_tok.get("qg_segments"):
        failures.append("finding1: بالله must clear qg_segments under competing_segmentation, got %r"
                         % ball_tok.get("qg_segments"))
    if ball_tok.get("selected_preview") is not None:
        failures.append("finding1: بالله must clear selected_preview under competing_segmentation")
    if len(ball_collision.get("candidate_refs") or []) < 2:
        failures.append("finding1: بالله must preserve >= 2 rival segment_candidate_ref values, got %r"
                         % ball_collision.get("candidate_refs"))
    ball_top = (ball_tok.get("morphology_candidates") or [{}])[0]
    if ball_top.get("lemma") is not None or ball_top.get("pos") is not None or ball_top.get("root") is not None:
        failures.append("finding1: بالله selected candidate must have lemma/pos/root withheld, got lemma=%r pos=%r root=%r"
                         % (ball_top.get("lemma"), ball_top.get("pos"), ball_top.get("root")))
    if (ball_tok.get("hover_preview") or {}).get("token_contribution_gloss") is not None:
        failures.append("finding1: بالله must not carry a public token_contribution_gloss")

    # Train E finding 1, evidence floor (red-first): every tied top-scored
    # candidate being the engine's own no-evidence fallback
    # (evidence_class=surface_candidate, tools/fusha_pattern_engine.py, score
    # constant 1.0) proves an ABSENCE of evidence for either segmentation, not
    # a lexical collision. Firing competing_segmentation here used to strip
    # the token's own class-neutral prefix clitic and divert it into the
    # collision queue; it must instead keep the pre-existing `ambiguous`
    # posture with its ordinary (uncollided) qg_segments intact.
    for evidence_floor_surface in ("بفرتش", "وفرتش", "لفرتش", "كفرتش"):
        ef_rec = parser.parse_text(evidence_floor_surface, db="largelexicon")
        ef_tok = (ef_rec.get("tokens") or [{}])[0]
        ef_cands = ef_tok.get("morphology_candidates") or []
        if not ef_cands or any(c.get("evidence_class") != "surface_candidate" for c in ef_cands):
            failures.append(
                "evidence floor setup: %r must have only surface_candidate fallback morphology "
                "candidates to exercise this check, got %r"
                % (evidence_floor_surface, [c.get("evidence_class") for c in ef_cands])
            )
        if ef_tok.get("collision") is not None:
            failures.append(
                "evidence floor: %r (all tied candidates are no-evidence fallbacks) must not fire "
                "any collision, got %r" % (evidence_floor_surface, ef_tok.get("collision"))
            )
        # A prepositional prefix (ب/ل/ك) independently triggers the unrelated
        # jar_majrur pending_context vote regardless of collision status; only
        # وفرتش (a conjunction prefix, no jar_majrur vote) reaches ambiguous.
        # Either is the pre-existing (non-collision) posture this finding
        # must preserve -- the point is `lexical_collision_requires_context`
        # (and the qg-wiping that goes with it) must never fire here.
        if ef_tok.get("confidence_gate") not in {"ambiguous", "pending_context"}:
            failures.append(
                "evidence floor: %r must keep a pre-existing non-collision posture, got "
                "confidence_gate=%r" % (evidence_floor_surface, ef_tok.get("confidence_gate"))
            )
        ef_roles = {seg.get("role") for seg in ef_tok.get("qg_segments") or []}
        if "prefix_preposition" not in ef_roles and "prefix_conjunction" not in ef_roles:
            failures.append(
                "evidence floor: %r must not have its class-neutral prefix clitic wiped, got "
                "qg_segments roles %r" % (evidence_floor_surface, ef_roles)
            )

    # Train E finding 2 (red-first): a genuine competing_segmentation tie must
    # not blanket-delete a class-neutral prefix/article every tied rival
    # places at the EXACT same span with the EXACT same role and surface --
    # only the letters after it are actually contested. `_candidate_collision`
    # must attach an explicit scope and retain only that exact shared span,
    # never the disputed stem.
    shared_seg_cands = [
        {"segments": [
            {"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition", "label": "P", "gloss_contribution": "by/with/in"},
            {"role": "stem", "surface": "فرس", "class": "qg-noun-stem", "label": "N", "gloss_contribution": None},
        ]},
        {"segments": [
            {"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition", "label": "P", "gloss_contribution": "by/with/in"},
            {"role": "stem", "surface": "قرة", "class": "qg-noun-stem", "label": "N", "gloss_contribution": None},
        ]},
    ]
    shared_a = {"rank": 1, "pos": "noun", "lemma": "X", "root": None, "evidence_class": "largelexicon_full",
                "score": 6.0, "segment_candidate_ref": 0, "features": {}}
    shared_b = {"rank": 2, "pos": "noun", "lemma": "Y", "root": None, "evidence_class": "largelexicon_full",
                "score": 6.0, "segment_candidate_ref": 1, "features": {}}
    shared_collision = parser._candidate_collision("xy", shared_seg_cands, [shared_a, shared_b], shared_a)
    if not shared_collision or shared_collision.get("kind") != "competing_segmentation":
        failures.append("finding2: a shared class-neutral prefix tie must still fire competing_segmentation")
    if (shared_collision or {}).get("scope") != "shared_class_neutral_prefix":
        failures.append(
            "finding2: a prefix shared at the exact same span/role/surface by every tied rival "
            "must set collision.scope=shared_class_neutral_prefix, got %r"
            % (shared_collision or {}).get("scope")
        )
    shared_out = (shared_collision or {}).get("shared_segments") or []
    if {seg.get("role") for seg in shared_out} != {"prefix_preposition"}:
        failures.append("finding2: only the shared prefix_preposition span may be retained, got %r" % shared_out)
    if {seg.get("surface") for seg in shared_out} != {"ب"}:
        failures.append("finding2: shared segment surface must be the exact shared span 'ب', got %r" % shared_out)
    if any(seg.get("role") == "stem" for seg in shared_out):
        failures.append("finding2: the disputed stem must never be retained under a shared-prefix scope")

    # finding2 hostile (red-first): a class-neutral segment present in only
    # ONE rival (absent from the other) must never be retained.
    absent_seg_cands = [
        {"segments": [
            {"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition"},
            {"role": "stem", "surface": "فرس", "class": "qg-noun-stem"},
        ]},
        {"segments": [
            {"role": "stem", "surface": "بفرس", "class": "qg-noun-stem"},
        ]},
    ]
    absent_a = {"rank": 1, "pos": "noun", "lemma": "X", "root": None, "evidence_class": "largelexicon_full",
                "score": 6.0, "segment_candidate_ref": 0, "features": {}}
    absent_b = {"rank": 2, "pos": "noun", "lemma": "Y", "root": None, "evidence_class": "largelexicon_full",
                "score": 6.0, "segment_candidate_ref": 1, "features": {}}
    absent_collision = parser._candidate_collision("xy", absent_seg_cands, [absent_a, absent_b], absent_a)
    if (absent_collision or {}).get("scope") is not None:
        failures.append(
            "finding2: a class-neutral segment absent from one rival must never be retained "
            "(scope must stay unset), got scope=%r" % (absent_collision or {}).get("scope")
        )
    if (absent_collision or {}).get("shared_segments"):
        failures.append("finding2: no shared_segments may be recorded when a rival lacks the span")

    # finding2 hostile (red-first): same span, but a DIFFERENT role/surface in
    # each rival (a genuinely contested prefix, not an agreed one) must also
    # never be retained.
    mismatched_seg_cands = [
        {"segments": [
            {"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition"},
            {"role": "stem", "surface": "فرس", "class": "qg-noun-stem"},
        ]},
        {"segments": [
            {"role": "prefix_conjunction", "surface": "و", "class": "qg-conjunction"},
            {"role": "stem", "surface": "فرس", "class": "qg-noun-stem"},
        ]},
    ]
    mismatched_a = {"rank": 1, "pos": "noun", "lemma": "X", "root": None, "evidence_class": "largelexicon_full",
                    "score": 6.0, "segment_candidate_ref": 0, "features": {}}
    mismatched_b = {"rank": 2, "pos": "noun", "lemma": "Y", "root": None, "evidence_class": "largelexicon_full",
                    "score": 6.0, "segment_candidate_ref": 1, "features": {}}
    mismatched_collision = parser._candidate_collision("xy", mismatched_seg_cands, [mismatched_a, mismatched_b], mismatched_a)
    if (mismatched_collision or {}).get("scope") is not None:
        failures.append(
            "finding2: two rivals disagreeing on role/surface at the same span must never be "
            "retained, got scope=%r" % (mismatched_collision or {}).get("scope")
        )

    # Train E finding 3 (red-first): collision MEMBERSHIP is tie membership --
    # every morphology candidate tied at the top score is a disputed rival,
    # not just rank 1. Every co-tied rival must have lemma/root/pos/gloss_hint
    # withheld and be marked candidate-only/blocked; every rival record must
    # be preserved (none collapsed), and a non-tied lower-score rival must
    # keep its own identity untouched.
    for f3_surface in ("لما", "وما", "بالله"):
        f3_rec = parser.parse_text(f3_surface, db="largelexicon")
        f3_tok = (f3_rec.get("tokens") or [{}])[0]
        f3_cands = f3_tok.get("morphology_candidates") or []
        f3_top_score = max((float(c.get("score") or 0.0) for c in f3_cands), default=None)
        f3_tied = [c for c in f3_cands if float(c.get("score") or 0.0) == f3_top_score]
        if len(f3_tied) < 2:
            failures.append("finding3: %r must have >= 2 tied top-scored rivals to exercise this check" % f3_surface)
        for c in f3_tied:
            if c.get("lemma") is not None or c.get("pos") is not None or c.get("root") is not None or c.get("gloss_hint") is not None:
                failures.append(
                    "finding3: %r rank-%r co-tied rival must have lemma/pos/root/gloss_hint withheld, "
                    "got lemma=%r pos=%r root=%r gloss_hint=%r"
                    % (f3_surface, c.get("rank"), c.get("lemma"), c.get("pos"), c.get("root"), c.get("gloss_hint"))
                )
            if c.get("selection_status") != "candidate_only":
                failures.append(
                    "finding3: %r rank-%r co-tied rival must be marked candidate_only, got %r"
                    % (f3_surface, c.get("rank"), c.get("selection_status"))
                )
        f3_untied = [c for c in f3_cands if float(c.get("score") or 0.0) != f3_top_score]
        if not f3_untied:
            failures.append("finding3: %r must have a non-tied lower-score rival to exercise this check" % f3_surface)
        elif all(c.get("lemma") is None for c in f3_untied):
            failures.append(
                "finding3: %r non-tied lower-score rivals must keep their own identity, not be stripped"
                % f3_surface
            )
        if len(f3_cands) < len(f3_tied):
            failures.append("finding3: %r must preserve every rival record, not collapse them" % f3_surface)

    # rival-order mutation (red-first): reordering the tied morph_cands list
    # must not change the collision kind or the set of rival identities.
    ro_a = {"rank": 1, "pos": "particle", "lemma": "X", "root": None, "evidence_class": "largelexicon_full",
            "score": 6.5, "segment_candidate_ref": 0, "features": {}}
    ro_b = {"rank": 2, "pos": "particle", "lemma": "Y", "root": None, "evidence_class": "largelexicon_full",
            "score": 6.5, "segment_candidate_ref": 1, "features": {}}
    ro_forward = parser._candidate_collision("xy", [], [ro_a, ro_b], ro_a)
    ro_reversed = parser._candidate_collision("xy", [], [ro_b, ro_a], ro_a)
    if not ro_forward or not ro_reversed:
        failures.append("rival-order mutation: expected competing_segmentation to fire in both orders")
    elif (
        ro_forward.get("kind") != ro_reversed.get("kind")
        or ro_forward.get("candidate_refs") != ro_reversed.get("candidate_refs")
        or ro_forward.get("pos_values") != ro_reversed.get("pos_values")
        or set(ro_forward.get("lemma_values") or []) != set(ro_reversed.get("lemma_values") or [])
    ):
        failures.append("rival-order mutation: candidate ordering changed collision kind or rival identities: %r vs %r"
                         % (ro_forward, ro_reversed))

    # registry mutation (red-first): cap/route/order for a fired class must be
    # read from fusha/parser/collision-classes.json, not hand-duplicated. Mutate
    # the loaded registry in place and require the parser's own output to move
    # with it; restore afterwards so later assertions see the real registry.
    _registry_entry = parser._CLASS_BY_ID["competing_segmentation"]
    _saved_route = list(_registry_entry["route"])
    _saved_cap = _registry_entry["gate_effect"]["cap"]
    _saved_order = _registry_entry["filter_order"]
    try:
        _registry_entry["route"] = ["mutated_route_sentinel"]
        _registry_entry["gate_effect"] = {"cap": "pending_context"}
        _registry_entry["filter_order"] = 99
        mutated_collision = parser._candidate_collision("xy", [], [ro_a, ro_b], ro_a)
        if not mutated_collision or mutated_collision.get("route") != ["mutated_route_sentinel"]:
            failures.append(
                "registry mutation: _candidate_collision route did not follow the mutated registry entry, got %r"
                % (mutated_collision or {}).get("route")
            )
        mutated_rank, mutated_cap, mutated_order = parser._registry_vote("competing_segmentation")
        if mutated_cap != "pending_context" or mutated_order != 99:
            failures.append(
                "registry mutation: _registry_vote did not follow the mutated cap/filter_order, got cap=%r order=%r"
                % (mutated_cap, mutated_order)
            )
    finally:
        _registry_entry["route"] = _saved_route
        _registry_entry["gate_effect"] = {"cap": _saved_cap}
        _registry_entry["filter_order"] = _saved_order
    restored_rank, restored_cap, restored_order = parser._registry_vote("competing_segmentation")
    if restored_cap != _saved_cap or restored_order != _saved_order:
        failures.append("registry mutation: restoring the registry did not restore _registry_vote's output")

    # registry authority fail-closed (red-first, Train E finding 2): a fired
    # class missing from the registry, or missing its required cap/route/
    # filter_order, must raise a deterministic RegistryAuthorityError -- never
    # silently recreate a shadow authority via a hardcoded historical default.
    def _expect_registry_authority_error(label, fn):
        try:
            fn()
        except parser.RegistryAuthorityError:
            return
        failures.append("registry fail-closed: %s did not raise RegistryAuthorityError" % label)

    _removed_entry = parser._CLASS_BY_ID.pop("competing_segmentation")
    try:
        _expect_registry_authority_error(
            "_registry_vote with no registry entry for the fired class",
            lambda: parser._registry_vote("competing_segmentation"),
        )
        _expect_registry_authority_error(
            "_registry_route with no registry entry for the fired class",
            lambda: parser._registry_route("competing_segmentation"),
        )
        _expect_registry_authority_error(
            "_candidate_collision with no registry entry for the fired class",
            lambda: parser._candidate_collision("xy", [], [ro_a, ro_b], ro_a),
        )
    finally:
        parser._CLASS_BY_ID["competing_segmentation"] = _removed_entry

    _entry = parser._CLASS_BY_ID["competing_segmentation"]
    _saved_gate_effect = _entry["gate_effect"]
    _entry["gate_effect"] = {"cap": None}
    try:
        _expect_registry_authority_error(
            "_registry_vote with gate_effect.cap missing",
            lambda: parser._registry_vote("competing_segmentation"),
        )
    finally:
        _entry["gate_effect"] = _saved_gate_effect

    _saved_route_value = _entry["route"]
    _entry["route"] = None
    try:
        _expect_registry_authority_error(
            "_registry_route with route missing",
            lambda: parser._registry_route("competing_segmentation"),
        )
    finally:
        _entry["route"] = _saved_route_value

    _saved_order_value = _entry["filter_order"]
    _entry["filter_order"] = None
    try:
        _expect_registry_authority_error(
            "_registry_vote with filter_order missing",
            lambda: parser._registry_vote("competing_segmentation"),
        )
    finally:
        _entry["filter_order"] = _saved_order_value

    # sanity: the registry is restored and back to normal (behind, once the
    # fix lands, no exception should be raised here at all).
    parser._registry_vote("competing_segmentation")
    parser._registry_route("competing_segmentation")

    segs = [{"rank": 1, "segments": [{"role": "stem", "surface": "كتاب"}]}]
    morphs = [{"rank": 1, "pos": "noun", "evidence_class": "seed_lexicon", "segment_candidate_ref": 99}]
    selected, morph = parser._selected(segs, morphs)
    gate, collision = parser._gate("كتاب", segs, morph, [], morphs)
    if selected is not None or gate != "blocked" or not collision or collision.get("kind") != "dangling_segment_ref":
        failures.append("dangling segment_candidate_ref must block instead of selecting candidate 0")

    # Train E B1 (red-first): a source_risk_flags=[requires_nahw_function] candidate
    # whose scoped competitors span >=2 trichotomy classes must NOT be masked down to
    # pending_context by the source-risk cap; the stronger skeleton collision must win,
    # keep its collision descriptor, and still strip the withheld candidate's identity.
    b1_seg_cands = [{"rank": 1, "segments": [{"role": "stem", "surface": "بعض"}]}]
    b1_morph = {
        "rank": 1,
        "pos": "noun",
        "lemma": "بَعْض",
        "root": "ب ع ض",
        "gloss_hint": "some",
        "pattern": None,
        "evidence_class": "largelexicon_full",
        "segment_candidate_ref": 0,
        "features": {"source_risk_flags": ["requires_nahw_function"]},
        "collision": {
            "competing_entry_ids": ["e1", "e2"],
            "competitors": [
                {"entry_id": "e1", "pos": "noun", "root": "ب ع ض", "lemma": "بَعْض"},
                {"entry_id": "e2", "pos": "verb", "root": "ب ع ض", "lemma": "بَعَضَ"},
            ],
        },
    }
    b1_morphs = [b1_morph]
    b1_selected, b1_selected_morph = parser._selected(b1_seg_cands, b1_morphs)
    b1_gate, b1_collision = parser._gate(
        "بعض", b1_seg_cands, b1_selected_morph, [], b1_morphs, selected_seg=b1_selected,
    )
    if b1_gate != "lexical_collision_requires_context":
        failures.append(
            "B1: a source_risk_flags=[requires_nahw_function] candidate must not mask a "
            "stronger pos_trichotomy_conflict skeleton collision; got gate=%r" % b1_gate
        )
    if not b1_collision or b1_collision.get("kind") != "pos_trichotomy_conflict":
        failures.append("B1: the winning collision descriptor (pos_trichotomy_conflict) must be preserved")
    if (b1_morph.get("features") or {}).get("gate_cap_decided_by", {}).get("filter") != "source_requires_nahw_function":
        failures.append("B1: the masked source-risk cap must still carry typed decided_by evidence")
    b1_cand = dict(b1_morph)
    b1_cand["features"] = dict(b1_morph["features"])
    parser._strip_collision_identity(b1_cand, decided_by=b1_collision.get("kind") if b1_collision else None)
    if b1_cand.get("lemma") is not None or b1_cand.get("root") is not None or b1_cand.get("pos") is not None:
        failures.append("B1: identity must be stripped once the stronger skeleton collision wins")
    if b1_cand["features"].get("identity_withheld_decided_by", {}).get("filter") != "pos_trichotomy_conflict":
        failures.append("B1: identity withholding must carry typed decided_by evidence naming the winning filter")

    # Train E I4 (red-first): _selected can promote a richer multi-segment candidate
    # over the collapsed whole-token ref _skeleton_collision used to read directly.
    # Scope must be derived from the segment candidate _selected actually returned.
    i4_seg_cands = [
        {"rank": 1, "segments": [{"role": "stem", "surface": "بالكتب"}]},
        {"rank": 2, "segments": [
            {"role": "prefix_preposition", "surface": "ب"},
            {"role": "stem", "surface": "الكتب"},
        ]},
    ]
    i4_morph = {
        "rank": 1,
        "pos": "noun",
        "evidence_class": "largelexicon_sample",
        "segment_candidate_ref": 0,
        "features": {},
        "collision": {
            "competing_entry_ids": ["e1", "e2"],
            "competitors": [
                {"entry_id": "e1", "pos": "noun", "root": "ك ت ب", "lemma": "كِتَاب"},
                {"entry_id": "e2", "pos": "verb", "root": "ك ت ب", "lemma": "كَتَبَ"},
            ],
        },
    }
    i4_morphs = [i4_morph]
    i4_selected, i4_selected_morph = parser._selected(i4_seg_cands, i4_morphs)
    if len(i4_selected.get("segments") or []) < 2:
        failures.append("I4 setup: _selected must promote the richer multi-segment candidate")
    i4_skeleton = parser._skeleton_collision("بالكتب", i4_seg_cands, i4_selected_morph, selected_seg=i4_selected)
    if not i4_skeleton or i4_skeleton.get("scope") != "stem_identity":
        failures.append(
            "I4: skeleton collision scope must come from the segment candidate _selected "
            "returned, not the collapsed morph.segment_candidate_ref; got scope=%r"
            % ((i4_skeleton or {}).get("scope"))
        )

    # Train E I2 (red-first): Mode C validate_record must be collision-aware.
    # stem_identity withholding retains an ordered, non-contiguous-with-full-surface
    # affix subset (never the ordinary full concatenation); whole-token/other-scope
    # withholding retains none; a collision token must never carry a public gloss.
    def _base_record(qg_segments, collision):
        return {
            "schema": SCHEMA,
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "source_boundary": {"original_preserved": True, "external_text_copied": False, "quran_text_altered": False},
            "input_mode": "arbitrary_typing",
            "raw_input": "بهم",
            "summary": {"live_writes": 0},
            "tokens": [{
                "surface": "بهم",
                "loc": None,
                "confidence_gate": "lexical_collision_requires_context",
                "segment_candidates": [],
                "morphology_candidates": [],
                "collision": collision,
                "qg_segments": qg_segments,
                "hover_preview": {"token_contribution_gloss": None},
            }],
        }

    stem_identity_ok = _base_record(
        [{"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition"}],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    stem_identity_ok_errs = validate_record(stem_identity_ok)
    if stem_identity_ok_errs:
        failures.append(
            "I2: a valid stem_identity collision retaining an in-order affix subset "
            "must not be flagged by validate_record: %s" % stem_identity_ok_errs
        )

    stem_identity_bad = _base_record(
        [{"role": "prefix_preposition", "surface": "زز", "class": "qg-preposition"}],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    if not validate_record(stem_identity_bad):
        failures.append("I2: a stem_identity retained segment absent from the surface must be flagged")

    stem_identity_empty = _base_record([], {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"})
    if not validate_record(stem_identity_empty):
        failures.append("I2: stem_identity collision withholding must not drop ALL affix/clitic coverage")

    whole_token_leak = _base_record(
        [{"role": "stem", "surface": "بهم", "class": "qg-noun-stem"}],
        {"kind": "unsafe_bare_match"},
    )
    if not validate_record(whole_token_leak):
        failures.append(
            "I2: a whole-token (non-stem_identity) collision must reject leftover qg_segments, "
            "even when they happen to fully concatenate the surface"
        )

    gloss_leak = _base_record(
        [{"role": "prefix_preposition", "surface": "ب", "class": "qg-preposition"}],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    gloss_leak["tokens"][0]["hover_preview"]["token_contribution_gloss"] = "some gloss"
    if not validate_record(gloss_leak):
        failures.append("I2: a collision-withheld token carrying a public token_contribution_gloss must be flagged")

    # Train E gap 1 (red-first): a function_inventory candidate that OUTSCORES a
    # sibling lexicon candidate for the same segment_candidate_ref must not let a
    # real corpus pos_trichotomy_conflict evade detection just because scoring
    # picked the function-word reading. _skeleton_collision must reach the
    # sibling's collision.competitors even though the winning/selected morph
    # itself carries none.
    g1_seg_cands = [{"rank": 1, "segments": [{"role": "stem", "surface": "من"}]}]
    g1_function_cand = {
        "rank": 1,
        "pos": "particle",
        "lemma": "من",
        "root": None,
        "gloss_hint": "from/who/whom/conditional by voweling and context",
        "pattern": None,
        "evidence_class": "function_inventory",
        "score": 6.5,
        "segment_candidate_ref": 0,
        "features": {},
    }
    g1_lexicon_cand = {
        "rank": 2,
        "pos": "verb",
        "lemma": "مَنَّ",
        "root": "م ن ن",
        "gloss_hint": "to do someone a favour",
        "pattern": None,
        "evidence_class": "largelexicon_full",
        "score": 5.5,
        "segment_candidate_ref": 0,
        "features": {},
        "collision": {
            "competing_entry_ids": ["e1", "e2"],
            "competitors": [
                {"entry_id": "e1", "pos": "verb", "root": "م ن ن", "lemma": "مَنَّ"},
                {"entry_id": "e2", "pos": "particle", "root": None, "lemma": "مِنْ"},
            ],
        },
    }
    g1_morphs = [g1_function_cand, g1_lexicon_cand]
    g1_selected, g1_selected_morph = parser._selected(g1_seg_cands, g1_morphs)
    g1_gate, g1_collision = parser._gate(
        "من", g1_seg_cands, g1_selected_morph, [], g1_morphs, selected_seg=g1_selected,
    )
    if g1_gate != "lexical_collision_requires_context":
        failures.append(
            "gap1: a function_inventory candidate that outscores a sibling carrying a real "
            "pos_trichotomy_conflict must not bypass the collision gate; got gate=%r" % g1_gate
        )
    if not g1_collision or g1_collision.get("kind") != "pos_trichotomy_conflict":
        failures.append("gap1: the winning gate must expose the sibling's pos_trichotomy_conflict")

    g1_end_to_end = parser.parse_text("من", db="largelexicon")
    g1_tok = (g1_end_to_end.get("tokens") or [{}])[0]
    if g1_tok.get("confidence_gate") != "lexical_collision_requires_context":
        failures.append(
            "gap1 end-to-end: bare 'من' has a real corpus pos_trichotomy_conflict "
            "(verb مَنَّ vs particle مِنْ/مَنْ) and must not settle for gate=%r"
            % g1_tok.get("confidence_gate")
        )
    if (g1_tok.get("hover_preview") or {}).get("token_contribution_gloss") is not None:
        failures.append("gap1 end-to-end: bare 'من' must not project a gloss-bearing function-word hover")

    # Train E gap 2 (red-first): _scope_collision_segments must withhold or
    # honestly reclassify affix roles whose label/gloss presupposes the disputed
    # host class (verb_prefix, future_particle, derivative_prefix, plural_suffix),
    # not just subject/object pronoun roles.
    g2_qg = [
        {"role": "future_particle", "surface": "س", "class": "qg-particle", "label": "FUT", "gloss_contribution": "will"},
        {"role": "verb_prefix", "surface": "ي", "class": "qg-verb-prefix", "label": "PFX", "gloss_contribution": "imperfect marker"},
        {"role": "verb_stem", "surface": "كفي", "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": "suffice"},
        {"role": "object_pronoun", "surface": "كهم", "class": "qg-object-pronoun", "label": "OBJ", "gloss_contribution": "you all"},
    ]
    g2_out = parser._scope_collision_segments(g2_qg)
    g2_by_surface = {seg.get("surface"): seg for seg in g2_out}
    for leaked_surface, original_role in (("س", "future_particle"), ("ي", "verb_prefix")):
        seg = g2_by_surface.get(leaked_surface)
        if seg is None:
            failures.append("gap2: expected surface %r to survive (withheld or reclassified), but it vanished" % leaked_surface)
        elif seg.get("role") == original_role or seg.get("gloss_contribution"):
            failures.append(
                "gap2: surface %r kept its class-presupposing role/gloss (role=%r gloss=%r)"
                % (leaked_surface, seg.get("role"), seg.get("gloss_contribution"))
            )
    if "كفي" in g2_by_surface:
        failures.append("gap2: the disputed stem itself must still be withheld, not just re-labeled")

    # Train E gap 3 (red-first): validate_record must assert the semantic role
    # restriction directly -- surviving segments merely being an ordered subset
    # of the surface is not enough; a class-presupposing affix role surviving
    # under a stem_identity collision must be flagged even though it still
    # concatenates in order.
    def _leak_record(surface, qg_segments, collision):
        return {
            "schema": SCHEMA,
            "public_boundary": dict(PUBLIC_BOUNDARY),
            "source_boundary": {"original_preserved": True, "external_text_copied": False, "quran_text_altered": False},
            "input_mode": "arbitrary_typing",
            "raw_input": surface,
            "summary": {"live_writes": 0},
            "tokens": [{
                "surface": surface,
                "loc": None,
                "confidence_gate": "lexical_collision_requires_context",
                "segment_candidates": [],
                "morphology_candidates": [],
                "collision": collision,
                "qg_segments": qg_segments,
                "hover_preview": {"token_contribution_gloss": None},
            }],
        }

    class_presupposing_leak = _leak_record(
        "سيفعل",
        [
            {"role": "future_particle", "surface": "س", "class": "qg-particle"},
            {"role": "verb_prefix", "surface": "ي", "class": "qg-verb-prefix"},
        ],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    if not validate_record(class_presupposing_leak):
        failures.append(
            "gap3: a stem_identity collision retaining a class-presupposing role "
            "(future_particle/verb_prefix) must be flagged even though the segments "
            "still form an ordered subset of the surface"
        )

    reclassified_ok = _leak_record(
        "سيفعل",
        [
            {"role": "affix_undetermined", "surface": "س", "class": "qg-particle", "gloss_contribution": None},
            {"role": "affix_undetermined", "surface": "ي", "class": parser.NEUTRAL_AFFIX_QG_CLASS, "gloss_contribution": None},
        ],
        {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
    )
    if validate_record(reclassified_ok):
        failures.append("gap3: honestly reclassified affix_undetermined segments must not be flagged")

    # Train E follow-up defect A (red-first): a role degraded to
    # affix_undetermined/clitic_undetermined that still carries its ORIGINAL
    # class-presupposing class (qg-verb-prefix, qg-derivative-prefix,
    # qg-plural-suffix, qg-object-pronoun, qg-subject-pronoun) still asserts
    # the disputed host category through `class` alone; validate_record must
    # flag this even though `role` was honestly renamed.
    residual_class_cases = [
        ("qg-verb-prefix", "affix_undetermined"),
        ("qg-derivative-prefix", "affix_undetermined"),
        ("qg-plural-suffix", "affix_undetermined"),
        ("qg-object-pronoun", "clitic_undetermined"),
        ("qg-subject-pronoun", "clitic_undetermined"),
    ]
    for leaked_class, degraded_role in residual_class_cases:
        residual_class_leak = _leak_record(
            "سيفعل",
            [{"role": degraded_role, "surface": "س", "class": leaked_class, "gloss_contribution": None}],
            {"kind": "pos_trichotomy_conflict", "scope": "stem_identity"},
        )
        if not validate_record(residual_class_leak):
            failures.append(
                "defectA: a stem_identity collision segment renamed to role=%r but still "
                "carrying class=%r must be flagged (class alone asserts the disputed host "
                "category)" % (degraded_role, leaked_class)
            )

    # Train E follow-up defect A production check (red-first): the parser's
    # own _scope_collision_segments must neutralize `class`, not just `role`,
    # for every CLASS_PRESUPPOSING_QG_ROLES/PRONOUN_CLITIC_QG_ROLES segment.
    defect_a_in = [
        {"role": "verb_prefix", "surface": "ي", "class": "qg-verb-prefix", "label": "PFX", "gloss_contribution": "imperfect marker"},
        {"role": "derivative_prefix", "surface": "مست", "class": "qg-derivative-prefix", "label": "DER", "gloss_contribution": "Form X seeker/doer shape"},
        {"role": "plural_suffix", "surface": "ين", "class": "qg-plural-suffix", "label": "PL", "gloss_contribution": "masculine plural/oblique ending"},
        {"role": "object_pronoun", "surface": "هم", "class": "qg-object-pronoun", "label": "OBJ", "gloss_contribution": "them"},
        {"role": "subject_pronoun", "surface": "نا", "class": "qg-subject-pronoun", "label": "SUBJ", "gloss_contribution": "we"},
    ]
    defect_a_out = parser._scope_collision_segments(defect_a_in)
    for seg in defect_a_out:
        if seg.get("class") in parser.CLASS_PRESUPPOSING_QG_CLASSES:
            failures.append(
                "defectA production: _scope_collision_segments left a class-presupposing "
                "class %r on role %r (surface %r); class must also be withheld/reclassified"
                % (seg.get("class"), seg.get("role"), seg.get("surface"))
            )

    # Train E follow-up defect B (red-first): validate_fusha_standalone_parse.py
    # must not hand-copy the production role union; it must be the SAME object
    # production owns, so any future production change propagates automatically.
    if CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES is not parser.CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES:
        failures.append(
            "defectB: validator's CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES must be the same "
            "object as the parser's authoritative union, not a hand-copied duplicate"
        )

    # Train E follow-up defect B inventory guard (red-first): every role that
    # the splitter/pattern-engine paths can actually emit into qg_segments
    # (collected empirically by running production fixtures) must be
    # classified as withheld, degraded, or explicitly class-neutral. An
    # unclassified role must fail loudly rather than silently pass through.
    known_roles = (
        parser.CLASS_PRESUPPOSING_STEM_IDENTITY_ROLES
        | parser.CLASS_NEUTRAL_QG_ROLES
        | {"affix_undetermined", "clitic_undetermined"}
    )
    observed_roles = set()
    observed_classes = set()
    inventory_fixtures = list(FIXTURES) + ["من", "بعض"]
    for text in inventory_fixtures:
        for db in ("smoke", "largelexicon"):
            rec = parser.parse_text(text, db=db)
            for tok in rec.get("tokens") or []:
                for seg in tok.get("qg_segments") or []:
                    if seg.get("role") is not None:
                        observed_roles.add(seg.get("role"))
                    if seg.get("class") is not None:
                        observed_classes.add(seg.get("class"))
    unclassified_roles = observed_roles - known_roles
    if unclassified_roles:
        failures.append(
            "defectB inventory: production emitted role(s) %s not classified as withheld, "
            "degraded, or explicitly class-neutral; do not silently accept unknown roles"
            % sorted(unclassified_roles)
        )
    unallowed_classes = observed_classes - ALLOWED_QG_CLASSES
    if unallowed_classes:
        failures.append(
            "defectB inventory: production emitted class(es) %s missing from the validator's "
            "ALLOWED_QG_CLASSES" % sorted(unallowed_classes)
        )
    try:
        from tools import fusha_mode_a as _mode_a
        producer_unallowed = observed_classes - _mode_a.ALLOWED_QG_CLASSES
        if producer_unallowed:
            failures.append(
                "defectB inventory: production emitted class(es) %s missing from the producer's "
                "(fusha_mode_a) ALLOWED_QG_CLASSES; project_largelexicon_qamus_hover_candidates.py "
                "would misclassify these rows" % sorted(producer_unallowed)
            )
    except ImportError:
        failures.append("defectB inventory: could not import tools.fusha_mode_a to cross-check producer inventory")

    # Train E follow-up defect B fail-closed production check (red-first): an
    # untriaged role reaching _scope_collision_segments must be withheld, not
    # silently passed through assuming it is class-neutral.
    unknown_role_seg = [{"role": "totally_untriaged_future_role", "surface": "x", "class": "qg-noun"}]
    unknown_role_out = parser._scope_collision_segments(unknown_role_seg)
    if any(seg.get("surface") == "x" for seg in unknown_role_out):
        failures.append(
            "defectB production: _scope_collision_segments passed through an untriaged role "
            "unchanged instead of withholding it (fail-closed default)"
        )

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_fusha_standalone_parse self-test: fixtures parse; source-clean; qg-safe; clitics preserved")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate standalone Fusha parser JSON.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.path:
        ap.error("need path or --self-test")
    with open(args.path, encoding="utf-8") as fh:
        rec = json.load(fh)
    errs = validate_record(rec)
    for e in errs:
        print("FAIL " + e)
    print("checked 1 record, %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
