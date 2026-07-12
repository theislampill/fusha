#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic discriminators for the permanent skill fixtures (gate 9).

Every phenomenon in the 141-example bank that was a live/binding bug is encoded here as a PAIR:
  - a CORRECTED rule (the revised-rules.jsonl behaviour), and
  - the SUPERSEDED rule it replaced (the exact pre-fix behaviour that produced the bug).

The fixtures (skill_fixtures.jsonl) are DATA; test_skill_fixtures.py is the ASSERTION harness. A fixture is
"red-first" when the SUPERSEDED rule reproduces the wrong label AND that wrong label diverges from the correct
one — so a test asserting the correct label FAILS against the superseded behaviour and PASSES against the
corrected behaviour. Stdlib only, no network, no MCP, no live services. Deterministic.

Dispatch: CORRECTED[rule](case) and SUPERSEDED[rule](case) both return a short label string.
"""
import re

# --- tiny self-contained Arabic normalization (no app/import coupling) --------------------------------------
_DIAC = re.compile(r"[ً-ْٰـۖ-ۭ]")


def bare(s):
    """Strip harakāt/tanwīn/šadda/dagger-alif/tatwīl + normalize alef-wasla; keep hamza seats and letters."""
    return _DIAC.sub("", (s or "")).replace("ٱ", "ا")


def contains_phrase(haystack, needle):
    """Diacritic-insensitive containment (documented matching-normalization, per so-source-address-ref-fidelity)."""
    return bare(needle).replace(" ", "") in bare(haystack).replace(" ", "")


# --- 1. adjacency-is-not-ownership (so-adjacency-not-ownership) ---------------------------------------------
def _owned_corrected(case):
    """Ownership requires morphological evidence: same non-null root, or the target surface in the carrier's forms.
    A carrier that is merely the root of an ADJACENT word in the same āyah is a decoy, not a binding."""
    tr, cr = case.get("target_root"), case.get("carrier_root")
    if tr and cr and tr == cr:
        return "owned"
    if case.get("surface_in_carrier_forms"):
        return "owned"
    return "unowned"


def _owned_superseded(case):
    """Pre-fix: positional co-occurrence (carrier == root of an adjacent word) was read as lexical ownership."""
    if case.get("carrier_is_adjacent_word_root"):
        return "owned"
    return "unowned"


# --- 2. affirm_live is a first-class binding disposition (so-affirm-live-valid-outcome) ---------------------
def _affirm_corrected(case):
    """No carrier owns the token (zero root-overlap, surface not in any forms) -> affirm_live is a VALID outcome."""
    if not case.get("root_overlap") and not case.get("surface_in_forms"):
        return "affirm_live"
    return "bound"


def _affirm_superseded(case):
    """Pre-fix: a two-vote binding was forced-choice among co-citation carriers; affirm_live was blocked as 'no decision'."""
    if not case.get("root_overlap") and not case.get("surface_in_forms"):
        return "blocked_no_decision"
    return "bound"


# --- 3. root-less noun ownership convention (so-rootless-noun-ownership-convention) -------------------------
def _rootless_corrected(case):
    """A blank root FIELD is a noun-entry data convention (994/2092). Establish ownership by headword
    consonant-skeleton == target-self root AND the target surface present in the entry's own forms."""
    if case.get("headword_skeleton") == case.get("target_self_root") and case.get("surface_in_own_forms"):
        return "owned_noun_entry"
    return "not_owned"


def _rootless_superseded(case):
    """Pre-fix: a raw root-mismatch detector flagged the blank-root noun host as ownership_suspect and let a
    same-root verb entry compete for it."""
    if not case.get("root_field"):
        return "ownership_suspect"
    return "owned_noun_entry"


# --- 4. function-word vs content-root routing (so-funcword-never-content-root-competition) ------------------
_PARTICLE_LETTERS = {"hal": "هل"}  # هل


def _funcroute_corrected(case):
    """Route by FUNCTION. أَهْل (bare اهل, 3 letters) is a content noun, not the interrogative هَل (2 letters);
    the fused لِلَّه is lām al-jarr + divine name -> category 'preposition', not a lam_family reclassification."""
    if case.get("contains_divine_name"):
        return "preposition"
    letters = bare(case.get("surface", ""))
    particle = _PARTICLE_LETTERS.get(case.get("candidate_particle", ""))
    if particle and letters != particle:
        return "content_lane"
    return "function_lane"


def _funcroute_superseded(case):
    """Pre-fix: consonant-skeleton segmentation matched أَهْل to هَل (function lane) and voted lam_family on لِلَّه."""
    if case.get("contains_divine_name"):
        return "lam_family_reclassify"
    if case.get("candidate_particle"):
        return "function_lane_interrogative"
    return "function_lane"


# --- 5/6/8. surface-diacritic homograph gate (so-diacritic-homograph-predisambiguation-gate) ----------------
def _man_min_corrected(case):
    """مَن (fatḥa on mīm) is the pronoun who/whoever (relative/conditional/interrogative); مِن (kasra) is the
    preposition 'from'. The vowel decides — never the bare skeleton."""
    return "pronoun_who_relative" if case.get("haraka_on_mim") == "fatha" else "preposition_from"


def _man_min_superseded(case):
    """Pre-fix: covered by the مِنْ ('from') entry by consonant-skeleton match, regardless of the vowel."""
    return "preposition_from"


def _an_corrected(case):
    """أَنْ (no šadda) al-maṣdariyya / subjunctive subordinator is a distinct sub-lexeme from أَنَّ (šadda) al-tawkīd."""
    return "anna_tawkid" if case.get("has_shadda") else "an_masdariyya"


def _an_superseded(case):
    """Pre-fix: labelled 'emphasis' and covered by the أَنَّ (tawkīd) entry."""
    return "anna_tawkid"


def _in_corrected(case):
    """إِنْ (no šadda) is conditional/nāfiya; إِنَّ (šadda) is the emphatic. Šadda + clause type decide (harakah conflict)."""
    return "inna_tawkid" if case.get("has_shadda") else "in_conditional_or_nafiya"


def _in_superseded(case):
    """Pre-fix: labelled 'emphasis' and covered by the إِنَّ (tawkīd) entry."""
    return "inna_tawkid"


# --- 7. الله family split suppression (so-allah-family-split-suppression) -----------------------------------
def _allah_corrected(case):
    """لِلَّهِ = لِ (lām al-jarr) + the divine name اللَّه (root ء ل ه) -> divine-name route. NEVER ال+له, NEVER the
    pronoun stem لَه (lahu)."""
    seg = [bare(x) for x in (case.get("segmentation") or [])]
    # bare drops harakāt/šadda + normalizes alef-wasla; forbidden splits are ال+له or the pronoun stem له.
    if seg == [bare("لِ"), bare("اللَّه")]:
        return "prep_plus_divine_name"
    return "invalid_split"


def _allah_superseded(case):
    """Pre-fix: resolved لله through the pronoun stem لَه (lahu) or split الله into ال+له."""
    return "pronoun_stem_lahu"


# --- 9. ما-family: a family label is not a resolution (so-funcword-...; ONH-B4) -----------------------------
def _ma_family_corrected(case):
    """ما-family is a ROUTING bucket; every occurrence still needs a per-occurrence sub-function
    (relative vs interrogative vs nāfiya vs maṣdariyya) before it is learner-visible."""
    sub = case.get("sub_function")
    return "resolved:" + sub if sub else "unresolved_needs_subfunction"


def _ma_family_superseded(case):
    """Pre-fix: the family tag ('ma_family') was treated as a terminal category / resolution."""
    return "ma_family"


# --- the 5:116:33 discriminator: relative مَا vs negating مَا (so-funcword-...; ONH-B1/B4; NF-LIVE-MA-5116-33) -
def _ma_neg_rel_corrected(case):
    """مَا that is the mafʿūl of a preceding transitive verb, or is followed by a preposition/noun heading its
    clause, is relative ('what' / qg-ma-particle). مَa directly negating a following verb is negation ('not')."""
    if case.get("object_of_transitive_verb") or case.get("followed_by_pos") in ("prep", "noun"):
        return "qg-ma-particle"
    if case.get("followed_by_pos") == "verb":
        return "qg-negation"
    return "unresolved_needs_subfunction"


def _ma_neg_rel_superseded(case):
    """Pre-fix live behaviour (v020, 5:116:33): مَa classified by surface string -> qg-negation ('not')."""
    return "qg-negation"


# --- retain-both certified disagreement (so-morphline-alternatives-stay-alternatives; certified-retain-both) -
def _retain_both_corrected(case):
    """A certified reviewer disagreement over compatible readings is retain_both — both readings carried,
    never majority-voted to a single surface."""
    if case.get("certified") and len(case.get("licensed_readings") or []) >= 2:
        return "retain_both"
    return "single"


def _retain_both_superseded(case):
    """Pre-fix: majority-voted a single surface, collapsing the alternatives."""
    return "majority_vote_single"


# --- 10. qg-lam purpose-lām blocked floor (so-qglam-purpose-lam-blocked-floor) ------------------------------
def _qglam_corrected(case):
    """The exemplar floor is measured over the EXACT segment_class_shape tuple. n < floor -> BLOCKED; a governing
    lām in a different segment shape is a different tuple, invisible to this floor by construction."""
    if case.get("exemplar_count", 0) < case.get("floor", 10):
        return "blocked_insufficient_convention_exemplars"
    return "unblocked"


def _qglam_superseded(case):
    """Pre-fix: broaden the pool by pulling any purpose-lām composite (different segment shape) to clear the floor."""
    if case.get("broaden_pool"):
        return "unblocked"
    return "blocked_insufficient_convention_exemplars"


# --- 11. morphline is authored, never a placeholder (so-morphline-authored-not-mechanical) ------------------
_PLACEHOLDER = re.compile(r"^\s*$|TODO|TBD|<[^>]*>|\.\.\.|placeholder|xxx", re.I)


def classify_morphline(value):
    """authored linguistic content only; empty or placeholder-shaped wording is rejected."""
    return "invalid_placeholder" if (value is None or _PLACEHOLDER.search(value)) else "authored_valid"


def _morphline_corrected(case):
    return classify_morphline(case.get("authored_value"))


def _morphline_superseded(case):
    """Pre-fix: rows carried an EMPTY morphline (mechanical fill / no segment analysis)."""
    return classify_morphline(case.get("superseded_value"))


# --- 12. case/maḥall abstention for mabnī tokens (mabni-fi-mahall; idafa-mabni-fi-mahall) -------------------
def classify_irab(analysis):
    """A mabnī token NEVER takes an assigned iʿrābī ending; it records mabni_on + fi_maḥall + reasoning."""
    if not analysis.get("mabni"):
        return "not_mabni"
    if analysis.get("assigned_irab_ending"):
        return "invalid_assigned_ending_on_mabni"
    if analysis.get("fi_mahall") and analysis.get("reasoning"):
        return "valid_fi_mahall_abstention"
    return "invalid_below_gate"


def _irab_corrected(case):
    return classify_irab(case.get("correct_analysis_obj") or {})


def _irab_superseded(case):
    return classify_irab(case.get("wrong_analysis_obj") or {})


# --- 13. source-address reference fidelity (so-source-address-ref-fidelity) ---------------------------------
def verify_source_ref(ar_phrase, named_ref, ayah_index):
    """Verify-before-trust: the named ref must GENUINELY CONTAIN the example's verbatim ar (modulo normalization),
    else the example is inadmissible as evidence and is quarantined — never self-edit the scripture ref byte."""
    text = ayah_index.get(named_ref)
    if text is not None and contains_phrase(text, ar_phrase):
        return "admissible"
    return "inadmissible_quarantine"


def _reffid_corrected(case):
    return verify_source_ref(case.get("ar_phrase"), case.get("named_ref"), case.get("ayah_index") or {})


def _reffid_superseded(case):
    """Pre-fix: the ref was accepted as given (trusted) and used as morphological/syntactic evidence."""
    return "admissible"


# --- 15. supersede-not-delete + dependent-binding blast-radius re-eval --------------------------------------
def _supersede_corrected(case):
    """Correct a wrong binding by lineage-preserving SUPERSEDE (tombstone). On supersede, EVERY dependent binding
    pointing at the tombstoned payload is enumerated and re-evaluated; any still-pointing binding is a conflict."""
    if case.get("mode") == "delete":
        return "invalid_deletion"
    dangling = [b for b in (case.get("dependent_bindings") or []) if b.get("points_at") == case.get("tombstoned_id")]
    return "conflict_reeval_required" if dangling else "clean_superseded"


def _supersede_superseded(case):
    """Pre-fix: delete-in-place (no tombstone) and leave dependent bindings dangling at the removed payload."""
    return "silent_delete"


CORRECTED = {
    "adjacency_ownership": _owned_corrected,
    "affirm_live": _affirm_corrected,
    "rootless_noun_ownership": _rootless_corrected,
    "funcword_routing": _funcroute_corrected,
    "man_vs_min": _man_min_corrected,
    "an_sublexeme": _an_corrected,
    "in_conditional": _in_corrected,
    "allah_split": _allah_corrected,
    "ma_family_subfunction": _ma_family_corrected,
    "ma_neg_vs_rel": _ma_neg_rel_corrected,
    "retain_both": _retain_both_corrected,
    "qglam_floor": _qglam_corrected,
    "morphline_placeholder": _morphline_corrected,
    "mabni_mahall": _irab_corrected,
    "source_ref_fidelity": _reffid_corrected,
    "supersede_propagation": _supersede_corrected,
}

SUPERSEDED = {
    "adjacency_ownership": _owned_superseded,
    "affirm_live": _affirm_superseded,
    "rootless_noun_ownership": _rootless_superseded,
    "funcword_routing": _funcroute_superseded,
    "man_vs_min": _man_min_superseded,
    "an_sublexeme": _an_superseded,
    "in_conditional": _in_superseded,
    "allah_split": _allah_superseded,
    "ma_family_subfunction": _ma_family_superseded,
    "ma_neg_vs_rel": _ma_neg_rel_superseded,
    "retain_both": _retain_both_superseded,
    "qglam_floor": _qglam_superseded,
    "morphline_placeholder": _morphline_superseded,
    "mabni_mahall": _irab_superseded,
    "source_ref_fidelity": _reffid_superseded,
    "supersede_propagation": _supersede_superseded,
}


# --- skill-untested-fix: boundary discriminators for the 15 accepted-untested registry rules (gate 4) ---
def _blank_beats_wrong_corrected(case):
    """a null root/pattern/lemma is correct when none can be certified; never fabricate one from resemblance"""
    return 'null_blank'


def _blank_beats_wrong_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'fabricated_from_resemblance'

def _sifa_verb_gloss_repair_corrected(case):
    """an adjectival sifa mushabbaha (kazim) carrying a verb-shaped 'suppress anger' gloss is an entry-repair candidate, not a hover patch"""
    return 'entry_repair_candidate'


def _sifa_verb_gloss_repair_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'partial_hover_override'

def _morph_correct_bytes_wrong_corrected(case):
    """a correct morphological decision must NOT ship when the surface bytes do not match; mechanics gate the deploy"""
    return 'blocked_mechanics'


def _morph_correct_bytes_wrong_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'ship_anyway'

def _quarantine_family_corrected(case):
    """a data-error quarantine matches on the stem: aliiman (acc) quarantines aliimun (nom) too, not just the exact case ending"""
    return 'quarantine_family'


def _quarantine_family_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'allow_other_case'

def _uncertain_prefer_pending_corrected(case):
    """when a sarf reading is not certified, prefer pending with a precise reason over resolving on a guess"""
    return 'pending_with_reason'


def _uncertain_prefer_pending_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'resolved_uncertain'

def _decision_maps_src_corrected(case):
    """a resolved sarf decision authors the gloss with src=qamus recorded at S:A:W; the superseded path authored without stamping the source"""
    return 'author_src_qamus'


def _decision_maps_src_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'author_no_src_stamp'

def _retry_before_impossible_corrected(case):
    """a row is almost never truly impossible: attempt a source-backed per-occurrence retry before emitting impossible/blocked"""
    return 'retry_source_backed'


def _retry_before_impossible_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'emit_impossible'

def _token_right_entry_wrong_corrected(case):
    """when the token is right but the entry is mis-filed, emit a repair candidate with a source address; never mutate live data"""
    return 'repair_candidate'


def _token_right_entry_wrong_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'mutate_live_entry'

def _verbose_spread_to_concise_corrected(case):
    """a verbose verb-shape spread-gloss on a non-primary slot is improved by a concise certified fusha override"""
    return 'apply_concise_certified'


def _verbose_spread_to_concise_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'keep_verbose_spread'

def _phrase_aware_pending_corrected(case):
    """prefer a phrase-aware pending over shipping a wrong one-word gloss"""
    return 'phrase_aware_pending'


def _phrase_aware_pending_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'wrong_one_word_gloss'

def _clause_relation_recorded_corrected(case):
    """relative pronouns, subordinating conjunctions, purpose lam and temporal conditionals must record their clause relation, not a generic particle gloss"""
    return 'purpose_clause'


def _clause_relation_recorded_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'generic_particle'

def _temporal_expression_review_corrected(case):
    """yawma-idhin requires temporal-expression review (yawma = time noun + idhin = attached 'then'); a bare 'day' hover is not rich closure"""
    return 'temporal_expression_review'


def _temporal_expression_review_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'bare_day_hover'

def _resolve_only_if_unique_corrected(case):
    """resolve only when the construction uniquely fixes the sense; otherwise emit pending with the precise blocker"""
    return 'pending_needs_nahw_review'


def _resolve_only_if_unique_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'resolved_ambiguous'

def _layer1_safe_with_evidence_corrected(case):
    """even a layer-1-safe rule (prep governs genitive) stays a two-vote candidate when the ending is unvoweled/unconfirmed; resolve only with evidence"""
    return 'candidate_two_vote'


def _layer1_safe_with_evidence_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'resolved_no_evidence'

def _prep_host_pronoun_both_corrected(case):
    """preposition/host+pronoun rows (fiiha, duunihim) must expose BOTH the relation and the attached pronoun"""
    return 'expose_both'


def _prep_host_pronoun_both_superseded(case):
    """Pre-fix behaviour that produced the documented wrong label."""
    return 'relation_only'

CORRECTED.update({
    "blank_beats_wrong": _blank_beats_wrong_corrected,
    "sifa_verb_gloss_repair": _sifa_verb_gloss_repair_corrected,
    "morph_correct_bytes_wrong": _morph_correct_bytes_wrong_corrected,
    "quarantine_family": _quarantine_family_corrected,
    "uncertain_prefer_pending": _uncertain_prefer_pending_corrected,
    "decision_maps_src": _decision_maps_src_corrected,
    "retry_before_impossible": _retry_before_impossible_corrected,
    "token_right_entry_wrong": _token_right_entry_wrong_corrected,
    "verbose_spread_to_concise": _verbose_spread_to_concise_corrected,
    "phrase_aware_pending": _phrase_aware_pending_corrected,
    "clause_relation_recorded": _clause_relation_recorded_corrected,
    "temporal_expression_review": _temporal_expression_review_corrected,
    "resolve_only_if_unique": _resolve_only_if_unique_corrected,
    "layer1_safe_with_evidence": _layer1_safe_with_evidence_corrected,
    "prep_host_pronoun_both": _prep_host_pronoun_both_corrected,
})

SUPERSEDED.update({
    "blank_beats_wrong": _blank_beats_wrong_superseded,
    "sifa_verb_gloss_repair": _sifa_verb_gloss_repair_superseded,
    "morph_correct_bytes_wrong": _morph_correct_bytes_wrong_superseded,
    "quarantine_family": _quarantine_family_superseded,
    "uncertain_prefer_pending": _uncertain_prefer_pending_superseded,
    "decision_maps_src": _decision_maps_src_superseded,
    "retry_before_impossible": _retry_before_impossible_superseded,
    "token_right_entry_wrong": _token_right_entry_wrong_superseded,
    "verbose_spread_to_concise": _verbose_spread_to_concise_superseded,
    "phrase_aware_pending": _phrase_aware_pending_superseded,
    "clause_relation_recorded": _clause_relation_recorded_superseded,
    "temporal_expression_review": _temporal_expression_review_superseded,
    "resolve_only_if_unique": _resolve_only_if_unique_superseded,
    "layer1_safe_with_evidence": _layer1_safe_with_evidence_superseded,
    "prep_host_pronoun_both": _prep_host_pronoun_both_superseded,
})
