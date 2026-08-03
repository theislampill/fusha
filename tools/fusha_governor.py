#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_governor — the governor / iʿrāb / dependency CANDIDATE lattice (P2 deliverable B).

Builds an ʿāmil→maʿmūl (governor→governed) candidate lattice over a unit and detects "right case, wrong/absent
governor". It is CONSERVATIVE and AMBIGUITY-PRESERVING: only the layer-1-safe heuristic resolves (a standalone
preposition governs the following noun in the genitive, and — since TRAIN-B-NAHW-GOVERNOR-REASON-PLANE — a ẓarf
annexation head governs its muḍāf ilayh in the genitive by iḍāfa); PP-attachment (which head the prepositional
phrase attaches to) stays UNRESOLVED; iḍāfa is a candidate with kept alternatives; coordinating wāw is correctly
HEADLESS (each governed node has at most one head — deep-research F6) and, absent supplied sense features, no
longer resolves at all. For arbitrary/unvoweled input the case ending is not visible, so even the safe rule
yields a heuristic CANDIDATE (decision pending), never a confirmed reading. It NEVER asserts a single governor
for an ambiguous token, and a heuristic edge NEVER overrides source-addressed certainty.

The case/mood-as-a-consequence-of-a-stated-governor + the rule that justifies it is an engineering synthesis (treebanks
store head-pointer + relation label but not case-as-consequence — deep-research REFUTED that), so `assigned_case_mood`
+ `governor_justification` + `justification_rule` are produced here. A proposed iʿrāb claim that asserts a case with no
justifying governor is flagged `governor_not_justified` (right_answer_wrong_reason) → routes to scholar/iʿrāb review;
this class is registered in the shared `fusha_check.IRAB_SENSITIVE_ISSUE_CLASSES` so it can never be auto_safe.

TRAIN-B-NAHW-GOVERNOR-REASON-PLANE (G3-G6) adds, ALL still candidate/pending — one plane, one question (WHICH
element governs this one, and by which rule):
  * G3 surface-key integrity — the trigger layer now strips the وَ/فَ proclitic and folds the لَآ maddah before
    keying a family lookup (D1/D4), and the light/heavy لكن members no longer share a key (D2): only a GEMINATE
    لكنّ is inna_family; a light لكنْ is a recognized NON-governing preverbal member (positive evidence, never
    silence). لا is discriminated by the FOLLOWING token's category/mood, never mapped unconditionally to
    la_jins; with no such evidence the outcome is an abstention.
  * G4 nawāsikh regime discrimination — the regime is established BEFORE any case expectation is emitted; a
    kāna-pattern read under an inna-family head is a contradiction_marker=True/pending violation, never a
    correction (D3); an unknown/syncretic exponent abstains (marking_unknown) rather than resolving (F3/F12).
  * G5 coordination case-following — a bare wāw no longer resolves (D6 withdrawn: it abstains or preserves
    alternatives); a conjunct's case is a CONSEQUENCE of the element it is joined to, never a fixed rule of the
    connector, and the joined-to head must be SUPPLIED. A following token explicitly typed adjective is never
    swept into the noun+noun iḍāfa-candidate branch merely because "adjective" is also a member of the noun POS
    set: it surfaces as an unresolved sifa/badal candidate instead (F9 repair).
  * G6 hidden structure / maḥall / the ẓarf ʿāmil-kind correction — mabni/mabni_on/fi_mahall_case_mood are
    populated from a closed, positively enumerated licensing inventory (reject_reconstruction is the default);
    the 15 ẓarf/annexation heads misclassified as ḥurūf jarr (D7) now emit governor kind idafa, never
    'majrūr bi-ḥarf jarr', while the genuine ḥurūf jarr (KNOWN_PREPS) are unchanged.

Dry-run: live_writes==0; public fields source-clean {src:qamus,kind:authored,lang:en}; all text scanned via leak_sot.
CLI: --self-test | --emit-fixture <path> | --run-bank <path> | --in <units.jsonl> --out <-|path>.
See parserplans/general-fusha-grammar-checker-p2/002-governor-irab-dependency-lattice.md.
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
from tools import leak_sot  # noqa: E402
from tools.validate_linguistic_decisions import required_gate  # noqa: E402
# tools/fusha_nahw_particle_rules.py already solves proclitic-stripping (_deproclitic) and light/heavy shadda
# weight (an_family_weight) for the particle-homograph domain; there is no import cycle (that module's only
# references to this package's grammar-reasoning peers are LAZY, inside function bodies), so this is a citing
# import, not a second copy of the rule (packet TRAIN-B-NAHW-GOVERNOR-REASON-PLANE, G3).
from tools.fusha_nahw_particle_rules import _deproclitic as _pr_deproclitic, an_family_weight  # noqa: E402

SCHEMA = "fusha/dependency-candidate-lattice@1"
_PUBLIC_BOUNDARY = {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                    "public_gloss_lang": "en", "external_source_names_public": False}

# Standalone (non-proclitic) Arabic prepositions that govern the FOLLOWING noun in the genitive. (Proclitic bi/li/ka
# live INSIDE a token and are handled by the segment/morphology layer, not the cross-token dependency lattice.)
# GENUINE ḥurūf jarr only. The 15 ẓarf/annexation heads (nouns of place/time that take a muḍāf ilayh) used to be
# folded in here (D7); they now live in ZARF_IDAFA_HEADS below and emit governor kind idafa, never a ḥarf-jarr
# reading — nahw/rules/preposition-pronoun-rules.json#inda already classifies عِندَ this way; this is agreement,
# not a new claim.
KNOWN_PREPS = {"من", "إلى", "الى", "على", "في", "عن", "مع", "حتى", "منذ", "مذ"}
ZARF_IDAFA_HEADS = {"عند", "لدى", "لدن", "نحو", "دون", "خلال", "حول", "قبل", "بعد", "تحت", "فوق",
                    "أمام", "وراء", "خلف", "بين"}
_NOUN_POS = {"noun", "proper_noun", "adjective", "participle", "masdar", "pronoun", "demonstrative"}
_NUMBER_POS = {"number", "numeral"}
_NUMBER_WORDS = {"ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة", "عشرون", "ثلاثون",
                 "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون", "مائة", "مئه", "ألف"}
_KANA_FAMILY = {"كان", "ليس", "صار", "أصبح", "أمسى", "أضحى", "ظل", "بات"}
# Members whose light/heavy distinction is NOT modeled here (unlike لكن — see _family_key/_trigger_family) keep
# their pre-existing, unconditional mapping: test_rm26_nahw.py:test_nhp_08 pins undiacritized 'إن' -> inna_family.
_TRIGGER_FAMILIES = {
    "لم": "jussive", "إن": "inna_family", "أن": "inna_family", "كأن": "inna_family",
    "ليت": "inna_family", "لعل": "inna_family",
    "إلا": "istithna", "هل": "hal", "يا": "vocative",
}
# A closed, positively enumerated inventory of preverbal particles that are recognized triggers but do NOT
# govern anything: "no governor" becomes positive evidence, distinct from a surface that is simply not in any
# inventory at all (token_not_in_inventory — silently no edge, exactly as before).
NONGOVERNING_PREVERBAL = {"قد", "سوف"}

# Nawāsikh regime table: which case each regime governs on its ism/khabar, and the rule/governor-kind that
# justifies it. Discrimination (which regime) always precedes emitting either expectation (packet invariant).
_NASIKH_REGIME = {
    "inna_family": {"ism": "accusative", "khabar": "nominative",
                    "ism_rule": "nasikh_governs_ism_nasb", "khabar_rule": "nasikh_governs_khabar_raf3"},
    "kana_family": {"ism": "nominative", "khabar": "accusative",
                    "ism_rule": "kana_governs_ism_raf3", "khabar_rule": "kana_governs_khabar_nasb"},
}

# A closed, positively enumerated licence for a hidden/elided element. reject_reconstruction is the DEFAULT for
# any construction not named here (validator FAIL 17 refuses any OTHER licensing_construction string outright).
HIDDEN_ELEMENT_LICENSING_INVENTORY = {
    "kana_family_hidden_ism", "inna_family_hidden_ism", "imperative_verb",
    "relative_clause_object_gap", "vocative_ya_noun",
}
_HIDDEN_CONSTRUCTION_TABLE = {
    "imperative_verb": {"type": "mustatir_pronoun", "obligatory": True},
    "relative_clause_object_gap": {"type": "elided_aid", "obligatory": False},
    "vocative_ya_noun": {"type": "elided_vocative_verb", "obligatory": True},
}

# Claim lint is type-driven: a named governor kind must license the claimed case/mood. Text is only a compatibility
# adapter for older rows, and negated mentions do not count as naming a governor.
GOVERNOR_TYPE_LICENSED_CASES = {
    "preposition": {"genitive"},
    "idafa": {"genitive"},
    "verb": {"nominative", "accusative"},
    "verb_subject": {"nominative"},
    "verb_object": {"accusative"},
    "mubtada_khabar": {"nominative"},
    "jussive_particle": {"jussive"},
    "subjunctive_particle": {"subjunctive"},
    "inna_family_ism": {"accusative"},
    "inna_family_khabar": {"nominative"},
    "kana_family_ism": {"nominative"},
    "kana_family_khabar": {"accusative"},
    "la_jins_ism": {"accusative"},
}
_GOVERNOR_TYPE_PATTERNS = {
    "preposition": (r"\bpreposition\b", r"ḥarf jarr", r"harf jarr", r"حرف جر", r"jarr particle"),
    "idafa": (r"muḍāf", r"mudaf", r"iḍāfa", r"idafa", r"مضاف"),
    "verb_subject": (r"fāʿil", r"faail", r"\bفاعل\b"),
    "verb_object": (r"mafʿūl", r"mafool", r"\bمفعول\b"),
    "mubtada_khabar": (r"mubtada", r"khabar", r"مبتدأ", r"خبر"),
    "jussive_particle": (r"jussive particle", r"jussive governor", r"حرف جزم"),
    "subjunctive_particle": (r"subjunctive particle", r"subjunctive governor", r"حرف نصب"),
}
_NEGATED_MENTION = re.compile(
    r"(?:\bnot\b|\bno\b|\bwithout\b|\bdoes\s+not\b|\bdid\s+not\b|ليس|غير|بدون|لا)"
    r"(?:\s+\S+){0,5}\s*$",
    re.I,
)

_ROUTE = {
    "jar_majrur": ("nahw", "nahw/procedures/idafa-jar-majrur.md"),
    "idafa_dependent": ("nahw", "nahw/procedures/idafa-jar-majrur.md"),
    "pp_attachment": ("nahw", "nahw/procedures/pp-attachment-review.md"),
    "coordination": ("nahw", "nahw/procedures/coordination-case-following.md"),
    "matuf": ("nahw", "nahw/procedures/coordination-case-following.md"),
    "matuf_alayh": ("nahw", "nahw/procedures/coordination-case-following.md"),
    "atf_bayan": ("nahw", "nahw/procedures/coordination-case-following.md"),
    "ism_nasikh": ("nahw", "nahw/procedures/nawasikh-government.md"),
    "khabar_nasikh": ("nahw", "nahw/procedures/nawasikh-government.md"),
    "hidden_subject": ("nahw", "nahw/procedures/hidden-structure-and-taqdir.md"),
    "zarf_idafa_head": ("nahw", "nahw/procedures/hidden-structure-and-taqdir.md"),
    "governor_not_justified": ("scholar_irab_review", "nahw/procedures/irab-case-mood.md"),
}


def _clean(s):
    return leak_sot.redact(s) if isinstance(s, str) else s


def _mk_edge(edge_id, dependent, rel_label, rel_label_ar, justification, justification_rule, *,
             candidate_head=None, headless=False, governor_type="none", assigned_case_mood=None,
             confidence="medium", evidence_class="heuristic", unresolved=None, contradiction=False,
             raww=False, decision_status="pending", triggers=None, claim_id=None, trigger_particle=None,
             trigger_family=None, abstention_reason=None, suppressed_rule=None, mabni=None, mabni_on=None,
             fi_mahall_case_mood=None, governing_regime=None, regime_evidence=None, hidden_element=None,
             analysis_attribution=None, head_case=None, head_governor_type=None, frame_kind=None):
    lane, proc = _ROUTE.get(justification_rule if justification_rule == "governor_not_justified" else rel_label,
                            ("nahw", "nahw/procedures/irab-case-mood.md"))
    gate = required_gate(triggers or ["irab"])  # iʿrāb-sensitive → never auto_safe (two_vote+)
    edge = {
        "edge_id": edge_id, "dependent": dependent, "candidate_head": candidate_head, "headless": headless,
        "governor_type": governor_type, "rel_label": rel_label, "rel_label_ar": _clean(rel_label_ar),
        "assigned_case_mood": assigned_case_mood, "governor_justification": _clean(justification),
        "justification_rule": justification_rule, "justification_confidence": confidence,
        "evidence_class": evidence_class, "unresolved_alternatives": unresolved or [],
        "contradiction_marker": contradiction, "right_answer_wrong_reason_marker": raww,
        "decision_status": decision_status, "gate": gate, "route_to": {"lane": lane, "procedure": proc},
    }
    optional = {
        "claim_id": claim_id, "trigger_particle": trigger_particle, "trigger_family": trigger_family,
        "abstention_reason": abstention_reason, "suppressed_rule": suppressed_rule, "mabni": mabni,
        "mabni_on": mabni_on, "fi_mahall_case_mood": fi_mahall_case_mood, "governing_regime": governing_regime,
        "regime_evidence": regime_evidence, "hidden_element": hidden_element,
        "analysis_attribution": analysis_attribution, "head_case": head_case,
        "head_governor_type": head_governor_type, "frame_kind": frame_kind,
    }
    edge.update({key: value for key, value in optional.items() if value is not None})
    return edge


def _is_prep(tok):
    surface = tok.get("surface", "")
    if N.bare(surface) == "من" and N.haraka_on(surface, "م") == N.FATHA and N.is_man_who(surface):
        return False
    pos = (tok.get("pos") or "").lower()
    bare = N.bare(surface)
    return pos in {"preposition"} or bare in KNOWN_PREPS or bare in ZARF_IDAFA_HEADS


def _is_noun(tok):
    return (tok.get("pos") or "").lower() in _NOUN_POS | _NUMBER_POS


def _is_number_word(tok):
    return (tok.get("pos") or "").lower() in _NUMBER_POS or N.bare(tok.get("surface", "")) in _NUMBER_WORDS


def _family_key(surface):
    """The trigger-family lookup key: proclitic-stripped, hamza-preserving, maddah-folded.

    G3/D1: 'وَلَٰكِنَّ' must key as 'لكن', not 'ولكن' (the missed _TRIGGER_FAMILIES entry that dropped 112
    وَلَٰكِن-family tokens silently). G3/D4: 'لَآ' must key as 'لا' (the maddah glyph folded) so F7 is recognised
    — but the fold is applied ONLY at this lookup, never to N.bare/N.norm generally, so no other decision moves.
    """
    key = _pr_deproclitic(N.bare(surface))
    return key.replace("آ", "ا")


def _la_family(next_tok):
    """لا discriminated by the FOLLOWING token's category (G3/D4): never an unconditional la_jins mapping.

    following=noun -> la_jins (family recognised; the fuller mabni/maḥall construction needs separate supplied
    exponent evidence — see _la_jins_address_edges). following=verb -> la_nahiya (jussive) or la_nafiya
    (indicative/subjunctive, non-operative). No evidence at all, or an unrecognised category -> None (abstain).
    """
    if next_tok is None:
        return None
    npos = (next_tok.get("pos") or "").lower()
    if npos in _NOUN_POS:
        return "la_jins"
    if npos == "verb":
        mood = (next_tok.get("mood_visible") or "").lower()
        if mood == "jussive":
            return "la_nahiya"
        if mood in ("indicative", "subjunctive"):
            return "la_nafiya"
    return None


def _trigger_family(tok, next_tok=None):
    pos = (tok.get("pos") or "").lower()
    if pos not in {"particle", "conjunction", ""}:
        return None
    function = (tok.get("function") or tok.get("particle_function") or "").lower()
    if "jussive" in function or function in {"prohibition", "conditional"}:
        return "jussive"
    key = _family_key(tok.get("surface", ""))
    if key == "لا":
        return _la_family(next_tok)
    if key == "لكن":
        # G3/D2: the light and heavy members must not share a key. Parity: the weight verdict here MUST equal
        # fusha_nahw_particle_rules.an_family_weight() for the same surface (both read the shadda/sukūn on the
        # nūn; this literally calls that function, so parity holds by construction).
        weight = an_family_weight(tok.get("surface", ""))
        if weight == "heavy":
            return "inna_family"
        if weight == "light":
            return "nongoverning_preverbal"
        return "regime_undetermined"
    if key in NONGOVERNING_PREVERBAL:
        return "nongoverning_preverbal"
    return _TRIGGER_FAMILIES.get(key)


def _affirmed_pattern(text, pattern):
    for match in re.finditer(pattern, text, re.I):
        if not _NEGATED_MENTION.search(text[max(0, match.start() - 60):match.start()]):
            return True
    return False


def _claim_governor_type(claim):
    explicit = (claim.get("claimed_governor_type") or "").strip().lower()
    if explicit:
        return explicit if explicit in GOVERNOR_TYPE_LICENSED_CASES else None
    text = "%s %s" % (claim.get("claimed_governor") or "", claim.get("claimed_reasoning") or "")
    for governor_type, patterns in _GOVERNOR_TYPE_PATTERNS.items():
        if any(_affirmed_pattern(text, pattern) for pattern in patterns):
            return governor_type
    return None


# ---------------------------------------------------------------------------
# G4: nawāsikh regime discrimination (address-bearing path — real, supplied token evidence)
# ---------------------------------------------------------------------------
def _norm_case(value):
    return {"raf3": "nominative", "nasb": "accusative", "jarr": "genitive", "jazm": "jussive",
            "nominative": "nominative", "accusative": "accusative", "genitive": "genitive",
            "jussive": "jussive", "unknown": "unknown"}.get(value, value)


def _nasikh_case_edge(nxt, dep_ref, trigger_ref, family, role, case_visible, exponent_syncretic):
    spec = _NASIKH_REGIME[family]
    rel = "ism_nasikh" if role == "ism" else "khabar_nasikh"
    expected = spec[role]
    rule = spec["%s_rule" % role]
    gtype = "verb" if family == "kana_family" else "particle"
    triggers = ["irab", "case_or_mood"]
    if exponent_syncretic:
        return _mk_edge(nxt(), dep_ref, rel, "%s (marking unknown)" % rel,
                        "The %s ending is shared between more than one case/mood (syncretic); the exponent "
                        "alone does not confirm %s, so no case is asserted." % (role, expected),
                        rule, candidate_head=trigger_ref, governor_type=gtype, assigned_case_mood=None,
                        confidence="low", evidence_class="source_addressed", decision_status="pending",
                        triggers=triggers, trigger_family=family, governing_regime=family,
                        regime_evidence="supplied: %s exponent is case/mood-syncretic" % role,
                        abstention_reason="marking_unknown")
    if case_visible and case_visible != expected:
        return _mk_edge(nxt(), dep_ref, rel, "%s (contradiction)" % rel,
                        "The visible %s ending (%s) contradicts the %s regime's expectation (%s); a consistency "
                        "violation, never a correction." % (role, case_visible, family, expected),
                        rule, candidate_head=trigger_ref, governor_type=gtype, assigned_case_mood=None,
                        confidence="high", evidence_class="source_addressed", contradiction=True,
                        decision_status="pending", triggers=triggers, trigger_family=family,
                        governing_regime=family,
                        regime_evidence="supplied: %s_marking=%s under regime=%s" % (role, case_visible, family))
    return _mk_edge(nxt(), dep_ref, rel, "%s (%s)" % (rel, expected),
                    "The %s of this %s clause is governed in %s." % (role, family, expected),
                    rule, candidate_head=trigger_ref, governor_type=gtype,
                    assigned_case_mood=(expected if case_visible == expected else None),
                    confidence=("high" if case_visible == expected else "low"), evidence_class="source_addressed",
                    decision_status="pending", triggers=triggers, trigger_family=family, governing_regime=family,
                    regime_evidence="supplied: %s_marking=%s" % (role, case_visible or "unknown"))


def _nasikh_hidden_ism_edges(nxt, trigger_ref, family, khabar_head_tok):
    spec = _NASIKH_REGIME[family]
    gtype = "verb" if family == "kana_family" else "particle"
    ism_edge = _mk_edge(nxt(), trigger_ref, "hidden_subject", "الاسم مستتر",
                        "The %s ism is not written; it is a hidden (mustatir) pronoun, obligatorily licensed by "
                        "this construction." % family,
                        "hidden_element_licensed", candidate_head=trigger_ref, headless=True, governor_type=gtype,
                        assigned_case_mood=None, confidence="medium", evidence_class="source_addressed",
                        decision_status="pending", triggers=["irab", "case_or_mood"], trigger_family=family,
                        governing_regime=family,
                        regime_evidence="supplied: no written ism token; the following token heads a shibh "
                                       "al-jumla khabar",
                        hidden_element={"type": "mustatir_pronoun",
                                        "licensing_construction": "%s_hidden_ism" % family, "obligatory": True})
    khabar_edge = _mk_edge(nxt(), khabar_head_tok.get("ref"), "khabar_nasikh", "شبه الجملة خبر",
                           "The prepositional phrase serves as the khabar; a phrase carries no declensional "
                           "exponent, so no case ending is asserted — only the positional (maḥall) slot.",
                           "mahall_positional_case", candidate_head=trigger_ref, governor_type=gtype,
                           assigned_case_mood=None, confidence="medium", evidence_class="source_addressed",
                           mabni=True, fi_mahall_case_mood=spec["khabar"], decision_status="pending",
                           triggers=["irab", "case_or_mood"], trigger_family=family, governing_regime=family,
                           regime_evidence="supplied: khabar realized as a shibh al-jumla, no nasb exponent")
    return [ism_edge, khabar_edge], []


def _nasikh_address_edges(nxt, toks, i, family):
    """None => insufficient evidence; the caller falls back to the legacy unmodeled-construction abstention."""
    if i + 1 >= len(toks):
        return None
    trigger_ref = toks[i].get("ref", "tok:%d" % i)
    ism_tok = toks[i + 1]
    ism_pos = (ism_tok.get("pos") or "").lower()
    if ism_pos not in _NOUN_POS:
        if i + 2 < len(toks) and _is_prep(ism_tok):
            return _nasikh_hidden_ism_edges(nxt, trigger_ref, family, ism_tok)
        return None
    ism_case = ism_tok.get("case_visible")
    if ism_case is None and not ism_tok.get("exponent_syncretic"):
        return None
    ism_ref = ism_tok.get("ref")
    edges = [_nasikh_case_edge(nxt, ism_ref, trigger_ref, family, "ism", ism_case, ism_tok.get("exponent_syncretic"))]
    consumed = [i + 1]
    idx = i + 2
    while idx < len(toks) and (toks[idx].get("pos") or "").lower() in _NOUN_POS:
        khabar_tok = toks[idx]
        edges.append(_nasikh_case_edge(nxt, khabar_tok.get("ref"), trigger_ref, family, "khabar",
                                       khabar_tok.get("case_visible"), khabar_tok.get("exponent_syncretic")))
        consumed.append(idx)
        idx += 1
    return edges, consumed


def _la_jins_address_edges(nxt, toks, i):
    if i + 1 >= len(toks):
        return None
    ism_tok = toks[i + 1]
    if (ism_tok.get("pos") or "").lower() not in _NOUN_POS:
        return None
    if ism_tok.get("definiteness") != "indefinite" or ism_tok.get("exponent") != "fatha_no_tanwin":
        return None
    trigger_ref = toks[i].get("ref")
    ism_ref = ism_tok.get("ref")
    edges = [_mk_edge(nxt(), ism_ref, "ism_nasikh", "اسم لا النافية للجنس (مبني على الفتح، في محل نصب)",
                      "لا of genus negates the entire genus; its ism is indefinite and built on the fatḥa (no "
                      "declensional exponent), occupying the accusative maḥall.",
                      "la_jins_governs_ism_mabni_fath", candidate_head=trigger_ref, governor_type="particle",
                      assigned_case_mood=None, confidence="high", evidence_class="source_addressed", mabni=True,
                      mabni_on="fatha", fi_mahall_case_mood="accusative", decision_status="pending",
                      triggers=["irab", "case_or_mood"], trigger_family="la_jins", governing_regime="la_jins",
                      regime_evidence="supplied: ism is indefinite, built on the fatḥa, no tanwīn")]
    for t in toks[i + 2:]:
        if t.get("rivals"):
            edges.append(_rivals_edge(nxt, t))
            break
    return edges, [i + 1]


def _rivals_edge(nxt, tok):
    alts = list(tok.get("rivals") or [])
    return _mk_edge(nxt(), tok.get("ref"), "none", "أوجه معتبرة متعددة",
                    "This token carries more than one attested grammatical analysis; both are preserved with no "
                    "selection and no school named.",
                    "not_determinable", governor_type="none", assigned_case_mood=None, confidence="low",
                    evidence_class="source_addressed", decision_status="pending", triggers=["ambiguous_grammar"],
                    unresolved=[{"reading": a} for a in alts],
                    analysis_attribution={"status": "analysis_dependent", "alternatives": alts,
                                          "party_source_ref": None})


def _la_nafiya_edge(nxt, ref):
    return _mk_edge(nxt(), ref, "none", "لا نافية غير عاملة",
                    "لا here negates a statement over an imperfect verb that keeps its default mood; it is "
                    "non-operative and assigns no case or mood (neither prohibitive nor lil-jins).",
                    "non_governing_use_abstention", governor_type="none", assigned_case_mood=None,
                    confidence="medium", evidence_class="source_addressed", decision_status="pending",
                    triggers=["ambiguous_grammar"], trigger_family="la_nafiya", governing_regime="la_nafiya",
                    abstention_reason="non_governing_use")


def _la_nahiya_edge(nxt, ref, verb_tok):
    return _mk_edge(nxt(), verb_tok.get("ref"), "none", "لا الناهية تجزم الفعل المضارع",
                    "لا of prohibition governs the following imperfect verb in the jussive.",
                    "operating_particle_governs_mood", candidate_head=ref, governor_type="particle",
                    assigned_case_mood="jussive", confidence="high", evidence_class="source_addressed",
                    decision_status="pending", triggers=["irab", "case_or_mood"], trigger_family="la_nahiya",
                    governing_regime="la_nahiya")


def _nongoverning_edge(nxt, ref):
    return _mk_edge(nxt(), ref, "none", "أداة غير عاملة",
                    "This particle is a recognized member of the closed non-governing preverbal inventory; "
                    "'no governor' is positive evidence here, not silence.",
                    "non_governing_use_abstention", governor_type="none", assigned_case_mood=None,
                    confidence="medium", evidence_class="heuristic", decision_status="pending",
                    triggers=["ambiguous_grammar"], trigger_family="nongoverning_preverbal",
                    governing_regime="nongoverning", abstention_reason="non_governing_use")


def _regime_undetermined_edge(nxt, ref):
    return _mk_edge(nxt(), ref, "none", "نظام الحكم غير محدد",
                    "The written form does not carry the mark distinguishing this particle's governing regime "
                    "from its non-governing counterpart; no family is asserted.",
                    "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                    confidence="low", evidence_class="heuristic", decision_status="pending",
                    triggers=["ambiguous_grammar"], trigger_family="regime_undetermined",
                    governing_regime="regime_undetermined", abstention_reason="regime_undetermined")


def _zarf_idafa_edges(nxt, head_tok, head_ref, dep_tok, dep_ref, case_visible, source_addressed):
    edges = []
    syncretic = bool(dep_tok.get("exponent_syncretic"))
    if source_addressed and (case_visible == "genitive" or (case_visible is None and syncretic)):
        conf = "high" if case_visible == "genitive" else "medium"
        note = ("the visible kasra confirms the genitive" if case_visible == "genitive" else
               "the annexation construction is categorical; the dependent's exponent is nasb/jarr-syncretic and "
               "is NOT read as confirmation — the ẓarf correction is not rescued by an exponent read")
        edges.append(_mk_edge(nxt(), dep_ref, "idafa_dependent", "مضاف إليه (بعد ظرف)",
                              "The ẓarf “%s” is a NOUN heading an annexation (iḍāfa), not a ḥarf jarr; %s." %
                              (head_tok.get("surface", ""), note),
                              "zarf_idafa_governs_genitive", candidate_head=head_ref, governor_type="noun",
                              assigned_case_mood="genitive", confidence=conf, evidence_class="source_addressed",
                              decision_status="pending", triggers=["irab", "case_or_mood"],
                              governing_regime="zarf_idafa",
                              regime_evidence="supplied: head is a ẓarf/annexation noun, not a ḥarf jarr"))
    elif source_addressed and case_visible and case_visible != "genitive":
        edges.append(_mk_edge(nxt(), dep_ref, "idafa_dependent", "مضاف إليه (بعد ظرف)",
                              "The ẓarf requires the genitive by annexation, but the visible ending is %s — a "
                              "contradiction to review." % case_visible,
                              "zarf_idafa_governs_genitive", candidate_head=head_ref, governor_type="noun",
                              assigned_case_mood="genitive", confidence="high", evidence_class="source_addressed",
                              contradiction=True, decision_status="pending", triggers=["irab", "case_or_mood"],
                              governing_regime="zarf_idafa"))
    else:
        edges.append(_mk_edge(nxt(), dep_ref, "idafa_dependent", "مضاف إليه (بعد ظرف)",
                              "The ẓarf heads an annexation; the ending is not visible/confirmed in this mode.",
                              "zarf_idafa_governs_genitive", candidate_head=head_ref, governor_type="noun",
                              assigned_case_mood=None, confidence="low", evidence_class="heuristic",
                              decision_status="pending", triggers=["irab", "case_or_mood"],
                              governing_regime="zarf_idafa"))
    edges.append(_mk_edge(nxt(), head_ref, "zarf_idafa_head", "الظرف نفسه",
                          "This packet does not model the ẓarf's own case or the head it attaches to; that "
                          "question is left open.",
                          "not_determinable", headless=True, governor_type="none", assigned_case_mood=None,
                          confidence="low", evidence_class="heuristic", decision_status="pending",
                          triggers=["ambiguous_grammar"],
                          abstention_reason="the ẓarf head's own case/attachment is not modeled by this packet"))
    return edges


# ---------------------------------------------------------------------------
# G4-G6: construction-typed dispatch (frame_kind=constructed — abstract feature patterns, no real occurrence)
# ---------------------------------------------------------------------------
def _h_nawasikh(nxt, dep_ref, f):
    regime = f.get("regime")
    triggers = ["irab", "case_or_mood"]
    if regime == "zanna_family":
        sense = f.get("sense")
        if sense != "judgemental":
            return [_mk_edge(nxt(), dep_ref, "none", "فعل ظنّ (حس أم قلب؟)",
                             "ẓanna-family verbs also carry a literal-perception sense taking a single object; "
                             "the two-accusative expectation is not asserted without a supplied judgemental "
                             "sense.",
                             "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                             confidence="low", evidence_class="heuristic", decision_status="pending",
                             triggers=["ambiguous_grammar"], trigger_family="zanna_family",
                             abstention_reason="sense_dependent_gate")]
        first, second = _norm_case(f.get("first_object_marking")), _norm_case(f.get("second_object_marking"))
        contradiction = second != "accusative"
        return [_mk_edge(nxt(), dep_ref, "none", "مفعولا ظنّ",
                         ("The kāna pattern (second object %s) appears where ẓanna's judgemental sense expects "
                          "TWO accusative objects; a consistency violation, no case assigned." % second)
                         if contradiction else
                         "ẓanna in the judgemental sense governs both objects in the accusative.",
                         "nasikh_governs_ism_nasb", governor_type="verb", assigned_case_mood=None,
                         confidence="high", evidence_class="heuristic", contradiction=contradiction,
                         decision_status="pending", triggers=triggers, trigger_family="zanna_family",
                         governing_regime="zanna_family",
                         regime_evidence="supplied: first_object_marking=%s, second_object_marking=%s, sense=%s"
                                        % (first, second, sense))]
    if f.get("bracketing") == "ambiguous":
        return [_mk_edge(nxt(), dep_ref, "none", "تعدد النواسخ المتراكبة",
                         "More than one abrogator is stacked and the clause bracketing is not supplied; no "
                         "scope is assigned.",
                         "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic", decision_status="pending",
                         triggers=["ambiguous_grammar"], abstention_reason="bracketing_ambiguous")]
    if f.get("polarity_licenser") == "absent":
        return [_mk_edge(nxt(), dep_ref, "none", "ناسخ مقيّد بقرينة سلبية",
                         "This kāna-sister requires a supplied negative-polarity licenser; none is supplied, so "
                         "the family expectation is not applied.",
                         "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic", decision_status="pending",
                         triggers=["ambiguous_grammar"], abstention_reason="licenser_absent")]
    spec = _NASIKH_REGIME.get(regime)
    if spec is None:
        return [_mk_edge(nxt(), dep_ref, "none", "نظام غير محدد", "The governing regime is not established.",
                         "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic", decision_status="pending",
                         triggers=["ambiguous_grammar"], governing_regime="regime_undetermined",
                         abstention_reason="regime_undetermined")]
    ism_marking, khabar_marking = _norm_case(f.get("ism_marking")), _norm_case(f.get("khabar_marking"))
    if ism_marking == "unknown":
        return [_mk_edge(nxt(), dep_ref, "ism_nasikh", "الاسم (العلامة غير معروفة)",
                         "The regime is known but the ism's marking is not supplied as a determinate value.",
                         spec["ism_rule"], governor_type="verb" if regime == "kana_family" else "particle",
                         assigned_case_mood=None, confidence="low", evidence_class="heuristic",
                         decision_status="pending", triggers=triggers, trigger_family=regime,
                         governing_regime=regime, abstention_reason="marking_unknown")]
    contradiction = ism_marking != spec["ism"] or (khabar_marking is not None and khabar_marking != spec["khabar"])
    return [_mk_edge(nxt(), dep_ref, "ism_nasikh", "نمط الناسخ",
                     ("The kāna pattern (ism %s, khabar %s) appears under a %s head; a consistency violation, "
                      "not a correction. No case is assigned." % (ism_marking, khabar_marking, regime))
                     if contradiction else
                     "The %s regime governs its ism in %s and its khabar in %s." % (regime, spec["ism"], spec["khabar"]),
                     spec["ism_rule"], governor_type="verb" if regime == "kana_family" else "particle",
                     assigned_case_mood=None, confidence="high", evidence_class="heuristic",
                     contradiction=contradiction, decision_status="pending", triggers=triggers,
                     trigger_family=regime, governing_regime=regime,
                     regime_evidence="supplied: ism_marking=%s, khabar_marking=%s, regime=%s"
                                     % (f.get("ism_marking"), f.get("khabar_marking"), regime))]


def _h_negation(nxt, dep_ref, f):
    if not f:
        return [_mk_edge(nxt(), dep_ref, "none", "لا بلا سياق",
                         "This shape has no default function; no evidence distinguishes negation from "
                         "prohibition or any other reading.",
                         "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic", decision_status="pending",
                         triggers=["ambiguous_grammar"], abstention_reason="insufficient_features")]
    if f.get("following_category") == "imperfect_verb" and f.get("following_mood") == "unvocalised_vowel_exponent":
        return [_mk_edge(nxt(), dep_ref, "none", "لا نافية أم ناهية",
                         "The following imperfect verb's mood exponent is not vocalised; statement negation and "
                         "prohibition both remain live.",
                         "regime_undetermined_abstention", governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic",
                         unresolved=[{"reading": "nafiya_statement"}, {"reading": "nahiya_prohibitive"}],
                         decision_status="pending", triggers=["ambiguous_grammar"])]
    return []


def _h_nongoverning(nxt, dep_ref, f):
    return [_mk_edge(nxt(), dep_ref, "none", "أداة غير عاملة",
                     "This preverbal token is a recognized non-governing inventory member; adjacency to the "
                     "following %s verb is not government." % (f.get("following_mood") or ""),
                     "non_governing_use_abstention", governor_type="none", assigned_case_mood=None,
                     confidence="medium", evidence_class="heuristic", decision_status="pending",
                     triggers=["ambiguous_grammar"], trigger_family="nongoverning_preverbal",
                     governing_regime="nongoverning", abstention_reason="non_governing_use")]


def _h_coordination(nxt, dep_ref, f):
    triggers_amb = ["ambiguous_grammar"]
    if f.get("particle") == "disputed_member":
        return [_mk_edge(nxt(), dep_ref, "coordination", "أداة عطف مختلف فيها",
                         "Whether this token functions as a coordinator at all is analysis-dependent; both "
                         "readings are preserved with no winner and no school named.",
                         "non_governing_use_abstention", headless=True, governor_type="none",
                         assigned_case_mood=None, confidence="low", evidence_class="heuristic",
                         decision_status="pending", triggers=triggers_amb, trigger_family="atf_candidate",
                         analysis_attribution={"status": "analysis_dependent",
                                               "alternatives": ["coordinating particle", "non-coordinating use"],
                                               "party_source_ref": None})]
    if f.get("connector") == "absent":
        return [_mk_edge(nxt(), dep_ref, "none", "لا أداة عطف",
                         "No connector is present; shared case is not, by itself, a coordination signature.",
                         "non_governing_use_abstention", governor_type="none", assigned_case_mood=None,
                         confidence="medium", evidence_class="heuristic", decision_status="pending",
                         triggers=triggers_amb, abstention_reason="not_coordination")]
    if f.get("connector_reading") == "clause_level":
        return [_mk_edge(nxt(), dep_ref, "coordination", "عطف جمل",
                         "This connector joins two CLAUSES; there is no head case for a clause-level connector "
                         "to follow.",
                         "non_governing_use_abstention", headless=True, governor_type="none",
                         assigned_case_mood=None, confidence="medium", evidence_class="heuristic",
                         decision_status="pending", triggers=triggers_amb, governing_regime="nongoverning",
                         abstention_reason="non_governing_use")]
    if f.get("connector_reading") == "coordination" and f.get("conjunct_marking") == "unknown":
        head_case = _norm_case(f.get("head_marking"))
        return [_mk_edge(nxt(), dep_ref, "matuf", "المعطوف (العلامة غير معروفة)",
                         "The head's case is known, but the conjunct's own marking is not supplied; the head's "
                         "case is never copied onto an unconfirmed conjunct.",
                         "coordination_follows_matuf_alayh_case", governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic", decision_status="pending",
                         triggers=["irab", "case_or_mood"], governing_regime="coordination", head_case=head_case,
                         abstention_reason="marking_unknown")]
    return []


def _h_waw(nxt, dep_ref, f):
    sense_features = ("following_nominal_case", "joint_performance", "preceding_role_saturation",
                      "preceding_verbal_governor", "second_governor")
    if not any(k in f for k in sense_features):
        return [_mk_edge(nxt(), dep_ref, "coordination", "واو محتملة",
                         "Clause-initial position alone licenses no sense for a wāw; sense requires supplied "
                         "syntactic features.",
                         "non_governing_use_abstention", headless=True, governor_type="none",
                         assigned_case_mood=None, confidence="low", evidence_class="heuristic",
                         decision_status="pending", triggers=["ambiguous_grammar"],
                         abstention_reason="insufficient_features")]
    if f.get("second_governor") == "absent":
        return [_mk_edge(nxt(), dep_ref, "coordination", "واو عطف أو معية",
                         "The following naṣb nominal could be a coordinated object of the preceding verb, or an "
                         "accompaniment (maʿiyya) object of an implied verb of joint performance; both readings "
                         "are preserved.",
                         "non_governing_use_abstention", headless=True, governor_type="none",
                         assigned_case_mood=None, confidence="low", evidence_class="heuristic",
                         unresolved=[{"reading": "coordination"}, {"reading": "maiyya"}],
                         decision_status="unresolved", triggers=["ambiguous_grammar"])]
    return []


def _h_hidden(nxt, dep_ref, f):
    construction = f.get("construction")
    entry = _HIDDEN_CONSTRUCTION_TABLE.get(construction)
    if entry is None:
        return [_mk_edge(nxt(), dep_ref, "none", "بنية بلا عنصر محذوف مرخّص",
                         "No enumerated construction licenses a hidden element here; reconstruction is refused "
                         "by default.",
                         "not_determinable", governor_type="none", assigned_case_mood=None, confidence="low",
                         evidence_class="heuristic", decision_status="pending", triggers=["ambiguous_grammar"],
                         abstention_reason="reject_reconstruction")]
    edge = _mk_edge(nxt(), dep_ref, "hidden_subject" if entry["type"] == "mustatir_pronoun" else "none",
                    "عنصر محذوف مرخّص",
                    "This construction is a positively enumerated licence for a hidden element (%s)." % construction,
                    "hidden_element_licensed", headless=True, governor_type="none", assigned_case_mood=None,
                    confidence="medium", evidence_class="heuristic", decision_status="pending",
                    triggers=["irab", "case_or_mood"], governing_regime="hidden_structure",
                    hidden_element={"type": entry["type"], "licensing_construction": construction,
                                    "obligatory": entry["obligatory"]})
    if construction == "vocative_ya_noun":
        edge["analysis_attribution"] = {"status": "analysis_dependent",
                                        "alternatives": ["elided verb أُنَادِي", "elided verb أَدْعُو"],
                                        "party_source_ref": None}
    return [edge]


def _h_rivals(nxt, dep_ref, f):
    if f.get("pair") == "referentially_identical":
        return [_mk_edge(nxt(), dep_ref, "none", "بدل أو عطف بيان",
                         "The second member is referentially identical and rigid; badal and atf_bayan both "
                         "license this configuration and neither is selected.",
                         "not_determinable", governor_type="none", assigned_case_mood=None, confidence="low",
                         evidence_class="heuristic", unresolved=[{"reading": "badal"}, {"reading": "atf_bayan"}],
                         decision_status="pending", triggers=["ambiguous_grammar"],
                         analysis_attribution={"status": "both_licensed", "alternatives": ["badal", "atf_bayan"],
                                               "party_source_ref": None})]
    if f.get("two_verbs") and f.get("one_argument"):
        return [_mk_edge(nxt(), dep_ref, "none", "تنازع العاملين",
                         "Two verbs compete for one argument (tanāzuʿ); both governor assignments are attributed "
                         "on this one edge and neither is selected.",
                         "not_determinable", governor_type="none", assigned_case_mood=None, confidence="low",
                         evidence_class="heuristic",
                         unresolved=[{"candidate_head_kind": "verb_1", "governor_type": "verb_subject"},
                                    {"candidate_head_kind": "verb_2", "governor_type": "verb_subject"}],
                         decision_status="unresolved", triggers=["ambiguous_grammar"],
                         analysis_attribution={"status": "both_licensed",
                                               "alternatives": ["governed by verb_1", "governed by verb_2"],
                                               "party_source_ref": None})]
    return []


def _h_zarf(nxt, dep_ref, f):
    if f.get("dependent_omitted"):
        return [_mk_edge(nxt(), dep_ref, "zarf_idafa_head", "الظرف نفسه",
                         "The ẓarf's own case/attachment question is not answered by this packet; no dependent "
                         "is supplied to annex.",
                         "not_determinable", headless=True, governor_type="none", assigned_case_mood=None,
                         confidence="low", evidence_class="heuristic", decision_status="pending",
                         triggers=["ambiguous_grammar"],
                         abstention_reason="the ẓarf head's own case/attachment is not modeled by this packet")]
    if f.get("head_class") == "zarf_idafa_head":
        marking = _norm_case(f.get("dependent_marking"))
        return [_mk_edge(nxt(), dep_ref, "idafa_dependent", "مضاف إليه (بعد ظرف)",
                         "The ẓarf is a NOUN heading an annexation; the genitive follows from iḍāfa, never from "
                         "a ḥarf-jarr reading, which is refused.",
                         "zarf_idafa_governs_genitive", governor_type="noun", assigned_case_mood="genitive",
                         confidence="medium", evidence_class="heuristic", decision_status="pending",
                         triggers=["irab", "case_or_mood"], governing_regime="zarf_idafa",
                         regime_evidence="supplied: dependent_marking=%s, head_class=zarf_idafa_head" % marking)]
    return []


_CONSTRUCTION_HANDLERS = {
    "nawasikh": _h_nawasikh, "negation": _h_negation, "nongoverning": _h_nongoverning,
    "coordination": _h_coordination, "waw": _h_waw, "hidden": _h_hidden, "rivals": _h_rivals, "zarf": _h_zarf,
}


def _constructed_lattice_edges(nxt, unit):
    family = unit.get("construction_family")
    handler = _CONSTRUCTION_HANDLERS.get(family)
    if handler is None:
        return []
    toks = unit.get("tokens") or [{"ref": "tok:0", "surface": "x"}]
    dep_ref = toks[0].get("ref", "tok:0")
    return handler(nxt, dep_ref, unit.get("features") or {}) or []


def build_dependency_lattice(unit):
    """unit = {input_mode, source_unit:{address,scope}, tokens:[{ref,surface,pos?,case_visible?}], claims?:[...]}.

    A CONSTRUCTED fixture (frame_kind=='constructed' + construction_family set) is an abstract feature pattern
    with no real occurrence; it is dispatched separately (see _constructed_lattice_edges) and never walks real
    tokens. Everything else (including every ADDRESS-BEARING TRAIN-B frame) walks the tokens exactly as before.
    """
    mode = unit.get("input_mode", "arbitrary_typing")
    source_addressed = mode == "source_addressed"
    toks = unit.get("tokens") or []
    edges = []
    eid = 0

    def nxt():
        nonlocal eid
        eid += 1
        return "e%d" % eid

    constructed = unit.get("frame_kind") == "constructed" and unit.get("construction_family")
    if constructed:
        edges.extend(_constructed_lattice_edges(nxt, unit))

    nasikh_suppressed_pairs = set()
    if not constructed:
        for i, tok in enumerate(toks):
            ref = tok.get("ref", "tok:%d" % i)
            next_tok = toks[i + 1] if i + 1 < len(toks) else None
            kana_key = _family_key(tok.get("surface", ""))
            is_kana_trigger = kana_key in _KANA_FAMILY and (tok.get("pos") or "").lower() == "verb"
            family = "kana_family" if is_kana_trigger else _trigger_family(tok, next_tok)
            if not family:
                continue
            if family in ("inna_family", "kana_family"):
                if i + 2 < len(toks):
                    nasikh_suppressed_pairs.add((i + 1, i + 2))
                richer = _nasikh_address_edges(nxt, toks, i, family)
                if richer is not None:
                    richer_edges, consumed = richer
                    for a, b in zip(consumed, consumed[1:]):
                        nasikh_suppressed_pairs.add((a, b))
                    edges.extend(richer_edges)
                    continue
                edges.append(_mk_edge(
                    nxt(), ref, "abstained_unmodeled_construction", "تركيب غير ممثَّل",
                    "The %s trigger is recognized, but its ism/khabar dependency is not modeled from the "
                    "supplied evidence; a nearby noun pair is not treated as iḍāfa." % family,
                    "unmodeled_construction_abstention", governor_type="verb" if family == "kana_family" else "particle",
                    decision_status="pending", triggers=["ambiguous_grammar"], trigger_particle=ref,
                    trigger_family=family,
                    abstention_reason="recognized trigger with no licensed construction rule",
                    suppressed_rule="idafa" if family == "kana_family" else None,
                ))
                continue
            if family == "la_jins":
                richer = _la_jins_address_edges(nxt, toks, i)
                if richer is not None:
                    richer_edges, consumed = richer
                    for a, b in zip(consumed, consumed[1:]):
                        nasikh_suppressed_pairs.add((a, b))
                    edges.extend(richer_edges)
                    continue
                edges.append(_mk_edge(
                    nxt(), ref, "abstained_unmodeled_construction", "تركيب غير ممثَّل",
                    "The trigger particle is recognized, but this governor construction is not modeled; the "
                    "lattice abstains instead of emitting an empty parse.",
                    "unmodeled_construction_abstention", governor_type="particle", decision_status="pending",
                    triggers=["ambiguous_grammar"], trigger_particle=ref, trigger_family=family,
                    abstention_reason="recognized trigger particle with no licensed construction rule",
                ))
                continue
            if family == "la_nafiya":
                edges.append(_la_nafiya_edge(nxt, ref))
                continue
            if family == "la_nahiya":
                edges.append(_la_nahiya_edge(nxt, ref, next_tok))
                continue
            if family == "nongoverning_preverbal":
                edges.append(_nongoverning_edge(nxt, ref))
                continue
            if family == "regime_undetermined":
                edges.append(_regime_undetermined_edge(nxt, ref))
                continue
            # legacy fallback (jussive / istithna / hal / vocative — unchanged from before this packet)
            edges.append(_mk_edge(
                nxt(), ref, "abstained_unmodeled_construction", "تركيب غير ممثَّل",
                "The trigger particle is recognized, but this governor construction is not modeled; the lattice "
                "abstains instead of emitting an empty parse.",
                "unmodeled_construction_abstention", governor_type="particle", decision_status="pending",
                triggers=["ambiguous_grammar"], trigger_particle=ref, trigger_family=family,
                abstention_reason="recognized trigger particle with no licensed construction rule",
            ))

    if not constructed:
        for i, t in enumerate(toks):
            ref = t.get("ref", "tok:%d" % i)
            # (0) G5/D5: a token-internal connector/governor (fused proclitic) is OUTSIDE this cross-token
            # lattice's declared layer; name the boundary instead of asserting a cross-token iḍāfa case.
            if i + 1 < len(toks) and toks[i + 1].get("coordination_layer") == "token_internal":
                dep = toks[i + 1]
                edges.append(_mk_edge(nxt(), dep.get("ref", "tok:%d" % (i + 1)), "coordination", "عطف داخل الكلمة",
                                      "The connector and/or its governor are token-internal (fused proclitics), "
                                      "outside this cross-token dependency lattice's declared layer; no "
                                      "cross-token case claim is made.",
                                      "non_governing_use_abstention", headless=True, governor_type="none",
                                      assigned_case_mood=None, confidence="low",
                                      evidence_class=("source_addressed" if source_addressed else "heuristic"),
                                      decision_status="pending", triggers=["ambiguous_grammar"],
                                      abstention_reason="cross_token_layer_boundary"))
            # (1) standalone preposition / ẓarf-annexation-head -> following noun (LAYER-1 SAFE)
            elif _is_prep(t) and i + 1 < len(toks) and _is_noun(toks[i + 1]):
                dep = toks[i + 1]
                dep_ref = dep.get("ref", "tok:%d" % (i + 1))
                case_visible = dep.get("case_visible")
                if N.bare(t.get("surface", "")) in ZARF_IDAFA_HEADS:
                    edges.extend(_zarf_idafa_edges(nxt, t, ref, dep, dep_ref, case_visible, source_addressed))
                    continue
                if source_addressed and case_visible == "genitive":
                    ev, conf, dec = "source_addressed", "high", "resolved"
                elif source_addressed and case_visible and case_visible != "genitive":
                    # the ending CONTRADICTS the rule (a preposition's noun must be genitive) -> contradiction, review.
                    edges.append(_mk_edge(nxt(), dep_ref, "jar_majrur", "majrūr bi-ḥarf jarr",
                                          "The preposition requires the genitive, but the visible ending is %s — a contradiction to review." % case_visible,
                                          "preposition_governs_genitive", candidate_head=ref, governor_type="particle",
                                          assigned_case_mood="genitive", confidence="high", evidence_class="source_addressed",
                                          contradiction=True, decision_status="pending", triggers=["irab", "case_or_mood"]))
                    continue
                else:
                    ev, conf, dec = "heuristic", "medium", "pending"  # arbitrary/unvoweled: rule known, ending unconfirmed
                edges.append(_mk_edge(nxt(), dep_ref, "jar_majrur", "majrūr bi-ḥarf jarr",
                                      "The preposition “%s” governs the following noun in the genitive (jar-majrūr)." % t.get("surface", ""),
                                      "preposition_governs_genitive", candidate_head=ref, governor_type="particle",
                                      assigned_case_mood="genitive", confidence=conf, evidence_class=ev,
                                      decision_status=dec, triggers=["irab"]))
                # (2) LAYER-2: which head the resulting PP attaches to stays UNRESOLVED (never forced)
                edges.append(_mk_edge(nxt(), ref, "pp_attachment", "taʿalluq al-jārr wa-l-majrūr",
                                      "The head the prepositional phrase attaches to (verb / nominal / hidden ḥāl or ṣifa) is not determinable from the surface; left unresolved.",
                                      "pp_attachment_unresolved", candidate_head=None, governor_type="none",
                                      assigned_case_mood=None, confidence="low", evidence_class="heuristic",
                                      unresolved=[{"candidate_head_kind": "verb"}, {"candidate_head_kind": "nominal"},
                                                  {"candidate_head_kind": "hidden_hal_or_sifa"}],
                                      decision_status="unresolved", triggers=["ambiguous_grammar"]))
            # (2.5) G5/adjective-guard: a FOLLOWING token explicitly typed adjective is a ṣifa (or, more rarely,
            # a badal) candidate, never a muḍāf ilayh — an adjective agrees with the noun it modifies rather than
            # being independently governed, so bearing the same (even genitive) case never licenses an iḍāfa
            # reading. This must be checked BEFORE the general noun+noun iḍāfa branch below, since "adjective" is
            # also a member of _NOUN_POS and would otherwise be swept into that ambiguous candidate.
            elif (_is_noun(t) and i + 1 < len(toks) and (toks[i + 1].get("pos") or "").lower() == "adjective"
                  and not _is_prep(t) and (i, i + 1) not in nasikh_suppressed_pairs):
                dep = toks[i + 1]
                dep_ref = dep.get("ref", "tok:%d" % (i + 1))
                edges.append(_mk_edge(nxt(), dep_ref, "sifa", "صفة أو بدل (يتبع الموصوف في الإعراب)",
                                      "The following token is explicitly typed adjective; an adjective agrees with "
                                      "(follows the case of) the noun it modifies rather than being independently "
                                      "governed, so it is never emitted as a muḍāf ilayh merely because it follows "
                                      "a noun and bears the same case.",
                                      "not_determinable", candidate_head=None, headless=True, governor_type="none",
                                      assigned_case_mood=None, confidence="low",
                                      evidence_class=("source_addressed" if source_addressed else "heuristic"),
                                      unresolved=[{"reading": "ṣifa (adjective, agrees in case with its mawṣūf)", "rel_label": "sifa"},
                                                  {"reading": "badal (apposition, agrees in case with its mubdal minhu)", "rel_label": "badal"}],
                                      decision_status="pending", triggers=["ambiguous_grammar"]))
            # (3) iḍāfa CANDIDATE: noun + noun (not a prep+noun already handled, and not an adjective — see (2.5))
            # -> muḍāf ilayh, but kept ambiguous
            elif (_is_noun(t) and i + 1 < len(toks) and _is_noun(toks[i + 1])
                  and (toks[i + 1].get("pos") or "").lower() != "adjective" and not _is_prep(t)
                  and (i, i + 1) not in nasikh_suppressed_pairs):
                dep = toks[i + 1]
                dep_ref = dep.get("ref", "tok:%d" % (i + 1))
                # A bare noun+noun is genuinely AMBIGUOUS: iḍāfa (2nd genitive) OR a nominal sentence mubtadaʾ+khabar
                # (2nd NOMINATIVE) OR ṣifa/badal. Do NOT assert a case in arbitrary mode (the ending is not visible and the
                # construction is undetermined); only a source-addressed visible ending confirms it. Keep ALL readings.
                alternatives = [{"reading": "iḍāfa: muḍāf ilayh (genitive)", "rel_label": "idafa_dependent", "case": "genitive"},
                                {"reading": "nominal sentence: mubtadaʾ + khabar (predicate nominative)", "rel_label": "subject", "case": "nominative"},
                                {"reading": "ṣifa (adjective, agrees in case)", "rel_label": "sifa"},
                                {"reading": "badal (apposition, agrees in case)", "rel_label": "badal"}]
                if _is_number_word(t):
                    alternatives.append({"reading": "number specification: tamyīz", "rel_label": "tamyiz",
                                         "case": dep.get("case_visible") or "depends_on_number_class"})
                case_visible = dep.get("case_visible")
                case_conflict = bool(source_addressed and case_visible and case_visible != "genitive")
                justification = (
                    "The visible %s ending conflicts with an iḍāfa-dependent reading, which requires the genitive; the rule refuses to certify iḍāfa and keeps alternatives for review." % case_visible
                    if case_conflict else
                    "The second noun MAY be the muḍāf ilayh (genitive by the iḍāfa construct), but the pair could equally be a nominal sentence (mubtadaʾ + khabar, the second nominative), a ṣifa/badal, or a licensed number-tamyīz reading; all applicable readings are kept."
                )
                edges.append(_mk_edge(nxt(), dep_ref, "idafa_dependent", "muḍāf ilayh (candidate)",
                                      justification,
                                      "idafa_governs_genitive", candidate_head=ref, governor_type="noun",
                                      assigned_case_mood=(case_visible if source_addressed and not case_conflict else None),
                                      confidence="low", evidence_class=("source_addressed" if source_addressed and case_visible else "heuristic"),
                                      unresolved=alternatives, contradiction=case_conflict,
                                      decision_status="pending", triggers=["idafa_ambiguous", "case_or_mood"] if case_conflict else ["idafa_ambiguous"]))
            # (4) coordinating wāw is correctly HEADLESS (F6: at most one head; some segments have none). D6
            # WITHDRAWN: a bare wāw with no supplied sense features no longer resolves — it abstains.
            elif N.bare(t.get("surface", "")) == "و" and (t.get("pos") or "").lower() in {"conjunction", "particle", ""}:
                edges.append(_mk_edge(nxt(), ref, "coordination", "wāw al-ʿaṭf",
                                      "A coordinating wāw links what follows to what precedes and has no governor of its own; with no supplied sense feature its function among coordination/maʿiyya/oath readings is not determined.",
                                      "non_governing_use_abstention", candidate_head=None, headless=True, governor_type="none",
                                      assigned_case_mood=None, confidence="medium", evidence_class="heuristic",
                                      decision_status="pending", triggers=["ambiguous_grammar"],
                                      abstention_reason="insufficient_features"))

    # (5) governor_not_justified: a proposed iʿrāb claim that asserts a case with NO justifying governor
    for c in unit.get("claims") or []:
        if c.get("claim_type") in {"case_mood", "governor", "irab_role"} and c.get("claimed_value"):
            cv = c.get("claimed_value")
            ev = "source_addressed" if source_addressed else "heuristic"
            governor_type = _claim_governor_type(c)
            licensed = GOVERNOR_TYPE_LICENSED_CASES.get(governor_type, set())
            if governor_type and cv not in licensed and cv not in ("none", None):
                edges.append(_mk_edge(nxt(), c.get("target", "tok:0"), "none", "ʿāmil mukhālif li-l-iʿrāb",
                                      "The named governor type “%s” does not license %s; it licenses %s." %
                                      (governor_type, cv, ", ".join(sorted(licensed)) or "no case/mood"),
                                      "governor_not_justified", candidate_head=None, governor_type="none",
                                      assigned_case_mood=cv, confidence="high", evidence_class=ev,
                                      raww=True, decision_status="pending", triggers=["irab", "case_or_mood"],
                                      claim_id=c.get("claim_id")))
                continue
            if not governor_type:
                edges.append(_mk_edge(nxt(), c.get("target", "tok:0"), "none", "ʿāmil ghayr mubayyan",
                                      "The case “%s” is asserted without naming the governing element (ʿāmil); a correct ending with no justified governor is unsafe." % cv,
                                      "governor_not_justified", candidate_head=None, governor_type="none",
                                      assigned_case_mood=cv, confidence="high", evidence_class=ev,
                                      raww=True, decision_status="pending", triggers=["irab", "case_or_mood"],
                                      claim_id=c.get("claim_id")))

    frame_kind = unit.get("frame_kind")
    if frame_kind:
        for e in edges:
            e.setdefault("frame_kind", frame_kind)

    n_unresolved = sum(1 for e in edges if e["decision_status"] in ("unresolved", "pending"))
    by_dec = {}
    for e in edges:
        by_dec[e["decision_status"]] = by_dec.get(e["decision_status"], 0) + 1
    su = unit.get("source_unit") or {"address": "", "scope": ("in_scope_source_addressed" if source_addressed else "arbitrary")}
    lattice = {
        "schema": SCHEMA, "input_mode": mode, "source_unit": su,
        "tokens": [{"ref": t.get("ref", "tok:%d" % i), "surface": t.get("surface", ""),
                    "pos": t.get("pos"), "case_visible": t.get("case_visible")} for i, t in enumerate(toks)],
        "edges": edges,
        "summary": {"live_writes": 0, "n_edges": len(edges), "n_unresolved": n_unresolved, "by_decision": by_dec},
        "public_boundary": dict(_PUBLIC_BOUNDARY),
        "source_boundary": {"heuristic_never_overrides_source": True, "quran_text_altered": False},
    }
    # hard invariants
    assert lattice["summary"]["live_writes"] == 0, "dry-run: live_writes must be 0"
    for e in edges:
        # an ambiguous edge (kept alternatives) must NOT be 'resolved'; a resolved edge needs a head or headless
        if e["unresolved_alternatives"] and e["decision_status"] == "resolved":
            raise AssertionError("ambiguous edge marked resolved")
        if e["decision_status"] == "resolved" and not (e["candidate_head"] or e["headless"]):
            raise AssertionError("resolved edge without a head and not headless")
        assert e["gate"] != "auto_safe", "governor edge may never be auto_safe"
    return lattice


# ---------------------------------------------------------------------------
# regression units (authored; Qurʾānic surfaces verbatim; no copied gloss)
# ---------------------------------------------------------------------------
def regression_units():
    return [
        # 1. source-addressed STANDALONE preposition -> majrūr noun, governor KNOWN (genitive confirmed) -> resolved.
        # VERIFIED against 2:7: word 3 عَلَىٰ is a ḥarf jarr (standalone token); word 4 قُلُوبِهِمْ is اسم مجرور — the
        # sign of jarr is the VISIBLE kasra — governed by عَلَىٰ. (Proclitic preps like بِبَدْرٍ are ONE written word and
        # are handled by the segment/morphology layer, NOT this cross-token dependency lattice.)
        {"name": "prep-majrur-known", "input_mode": "source_addressed",
         "source_unit": {"address": "quran:2:7", "scope": "in_scope_source_addressed"},
         "tokens": [{"ref": "2:7:3", "surface": "عَلَىٰ", "pos": "preposition"},
                    {"ref": "2:7:4", "surface": "قُلُوبِهِمْ", "pos": "noun", "case_visible": "genitive"}]},
        # 3. arbitrary prep -> majrūr, ending NOT visible -> heuristic candidate, pending (never resolved)
        {"name": "prep-majrur-arbitrary", "input_mode": "arbitrary_typing",
         "tokens": [{"ref": "tok:0", "surface": "في", "pos": "preposition"},
                    {"ref": "tok:1", "surface": "المدرسة", "pos": "noun"}]},
        # 4. iḍāfa candidate (noun + noun) — kept ambiguous (ṣifa/badal alternatives), pending
        {"name": "idafa-candidate", "input_mode": "arbitrary_typing",
         "tokens": [{"ref": "tok:0", "surface": "كتاب", "pos": "noun"},
                    {"ref": "tok:1", "surface": "الطالب", "pos": "noun"}]},
        # 5. coordinating wāw — headless (correct). D6 WITHDRAWN: no supplied sense feature -> abstains
        # (insufficient_features), never resolves. Headless stays true.
        {"name": "coordination-headless", "input_mode": "arbitrary_typing",
         "tokens": [{"ref": "tok:0", "surface": "و", "pos": "conjunction"},
                    {"ref": "tok:1", "surface": "الشمس", "pos": "noun"}]},
        # 6. right-answer-wrong-reason: a claim asserts accusative with NO governor named -> governor_not_justified
        {"name": "weak-governor-claim", "input_mode": "source_addressed",
         "source_unit": {"address": "quran:2:255", "scope": "in_scope_source_addressed"},
         "tokens": [{"ref": "2:255:1", "surface": "اللَّهُ", "pos": "proper_noun", "case_visible": "nominative"}],
         "claims": [{"claim_id": "c1", "target": "2:255:1", "claim_type": "case_mood", "claimed_value": "nominative",
                     "claimed_governor": None, "claimed_reasoning": None}]},
        # 7. governor JUSTIFIED claim (names the governor) -> NO governor_not_justified
        {"name": "governor-justified-claim", "input_mode": "source_addressed",
         "source_unit": {"address": "quran:1:2", "scope": "in_scope_source_addressed"},
         "tokens": [{"ref": "1:2:2", "surface": "لِلَّهِ", "pos": "noun", "case_visible": "genitive"}],
         "claims": [{"claim_id": "c1", "target": "1:2:2", "claim_type": "case_mood", "claimed_value": "genitive",
                     "claimed_governor": "the preposition lām", "claimed_reasoning": "genitive because governed by the preposition lām"}]},
    ]


def _self_test():
    failures = []
    for u in regression_units():
        lat = build_dependency_lattice(u)
        nm = u["name"]
        for e in lat["edges"]:
            if e["gate"] == "auto_safe":
                failures.append("%s: edge auto_safe" % nm)
            if e["unresolved_alternatives"] and e["decision_status"] == "resolved":
                failures.append("%s: ambiguous edge resolved" % nm)
            for f in ("governor_justification", "rel_label_ar"):
                if leak_sot.is_leak(e.get(f) or ""):
                    failures.append("%s: leak in %s" % (nm, f))
        if lat["summary"]["live_writes"] != 0:
            failures.append("%s: live_writes != 0" % nm)
    by = {u["name"]: build_dependency_lattice(u) for u in regression_units()}
    # behaviour
    if not any(e["decision_status"] == "resolved" and e["rel_label"] == "jar_majrur" for e in by["prep-majrur-known"]["edges"]):
        failures.append("prep-majrur-known: a known-genitive prep edge should resolve")
    if any(e["decision_status"] == "resolved" and e["rel_label"] == "jar_majrur" for e in by["prep-majrur-arbitrary"]["edges"]):
        failures.append("prep-majrur-arbitrary: unvoweled prep edge must NOT resolve (ending unconfirmed)")
    if not any(e["rel_label"] == "pp_attachment" and e["decision_status"] == "unresolved" for e in by["prep-majrur-known"]["edges"]):
        failures.append("prep-majrur-known: PP attachment must stay unresolved")
    if not any(e["headless"] for e in by["coordination-headless"]["edges"]):
        failures.append("coordination-headless: wāw must be headless")
    # G5/D6 WITHDRAWN: the packet's single_permitted_expectation_change — headless stays true, but a bare wāw
    # with no supplied sense feature no longer resolves; it abstains(insufficient_features).
    if any(e["decision_status"] == "resolved" for e in by["coordination-headless"]["edges"]):
        failures.append("coordination-headless: a bare wāw with no supplied sense feature must NOT resolve (D6 withdrawn)")
    if not any(e.get("abstention_reason") == "insufficient_features" for e in by["coordination-headless"]["edges"]):
        failures.append("coordination-headless: must abstain(insufficient_features)")
    if not any(e["right_answer_wrong_reason_marker"] for e in by["weak-governor-claim"]["edges"]):
        failures.append("weak-governor-claim: must flag governor_not_justified (right answer wrong reason)")
    if any(e["right_answer_wrong_reason_marker"] for e in by["governor-justified-claim"]["edges"]):
        failures.append("governor-justified-claim: a justified governor must NOT be flagged")
    if not any(e["unresolved_alternatives"] for e in by["idafa-candidate"]["edges"]):
        failures.append("idafa-candidate: must keep alternative readings")
    # D: a stated-but-WRONG governor (a preposition claimed to assign accusative) must be flagged (review finding D)
    _d = build_dependency_lattice({"input_mode": "source_addressed", "source_unit": {"address": "q", "scope": "in_scope_source_addressed"},
                                   "tokens": [{"ref": "t1", "surface": "X", "pos": "noun", "case_visible": "accusative"}],
                                   "claims": [{"claim_id": "c", "target": "t1", "claim_type": "case_mood", "claimed_value": "accusative",
                                               "claimed_governor": "the preposition min", "claimed_reasoning": "accusative because governed by the preposition min"}]})
    if not any(e["right_answer_wrong_reason_marker"] for e in _d["edges"]):
        failures.append("D: a preposition claimed to assign accusative must be flagged (right answer, wrong reason)")
    # M: a claim justified with Arabic role nomenclature (فاعل مرفوع) and no separate governor field must NOT be false-flagged
    _m = build_dependency_lattice({"input_mode": "source_addressed", "source_unit": {"address": "q", "scope": "in_scope_source_addressed"},
                                   "tokens": [{"ref": "t1", "surface": "X", "pos": "noun", "case_visible": "nominative"}],
                                   "claims": [{"claim_id": "c", "target": "t1", "claim_type": "case_mood", "claimed_value": "nominative",
                                               "claimed_governor": "", "claimed_reasoning": "فاعل مرفوع"}]})
    if any(e["right_answer_wrong_reason_marker"] for e in _m["edges"]):
        failures.append("M: a claim justified with Arabic role nomenclature (fāʿil marfūʿ) must NOT be flagged")
    # K: an arbitrary iḍāfa edge must NOT assert a case and must keep the nominal-sentence (nominative khabar) reading
    _ie = next(e for e in by["idafa-candidate"]["edges"] if e["rel_label"] == "idafa_dependent")
    if _ie["assigned_case_mood"] is not None:
        failures.append("K: arbitrary iḍāfa edge must not assert a case (iḍāfa-genitive vs nominal-sentence-nominative undetermined)")
    if not any(a.get("case") == "nominative" for a in _ie["unresolved_alternatives"]):
        failures.append("K: iḍāfa edge must keep the nominal-sentence (nominative khabar) alternative")
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_governor self-test: %d units; layer-1-safe prep→genitive resolves only when confirmed; "
              "PP-attachment unresolved; wāw headless (never resolves); right-answer-wrong-reason flagged; "
              "ambiguity preserved; never auto_safe" % len(regression_units()))
    return 0 if not failures else 1


def emit_fixture(path):
    rows = [build_dependency_lattice(u) for u in regression_units()]
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {
        "schema": SCHEMA, "generator": "tools/fusha_governor.py --emit-fixture", "count": len(rows),
        "note": "Governor/iʿrāb dependency CANDIDATE lattices. Conservative (layer-1-safe prep→genitive; PP-attachment "
                "unresolved; iḍāfa ambiguous; wāw headless and abstains; right-answer-wrong-reason flagged). Authored; "
                "Qurʾānic surfaces verbatim; source-clean {src:qamus,kind:authored,lang:en}; never auto_safe; "
                "live_writes==0. parserplans p2/002.",
    }
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d lattices -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def run_bank(path):
    """Run every row of a bank JSONL through the ordinary consumer (build_dependency_lattice), reporting only
    crashes/hard-invariant breaks. Behavioural expectations are asserted by tools/test_nahw_governor_families.py
    and (for occurrence identity) tools/validate_dependency_lattice.py --verify-occurrence-identity; a row that
    merely runs without raising is NOT proof of correctness on its own."""
    n, fails = 0, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n += 1
            try:
                build_dependency_lattice(row)
            except Exception as exc:  # noqa: BLE001
                fails += 1
                print("FAIL %s: %s" % (row.get("id", "?"), exc))
    print("ran %d bank row(s) from %s, %d failure(s)" % (n, path, fails))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description="Fusha governor/dependency candidate lattice (dry-run, conservative).")
    ap.add_argument("--in", dest="infile")
    ap.add_argument("--out", dest="outfile", default="-")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    ap.add_argument("--run-bank", dest="bank")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    if a.bank:
        return run_bank(a.bank)
    if not a.infile:
        ap.error("need --in, --self-test, --run-bank, or --emit-fixture")
    rows = []
    with open(a.infile, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(build_dependency_lattice(json.loads(line)))
    sink = sys.stdout if a.outfile == "-" else open(a.outfile, "w", encoding="utf-8")
    for r in rows:
        sink.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
