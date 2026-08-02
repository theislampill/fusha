#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consumer for the CONTEXT/REFERENT domain of nahw/rules/ — sense rivals, referent guards, jar-majrūr wording.

A separate bounded domain from the particle/diacritic consumer (tools/fusha_nahw_particle_rules.py). This one
answers only "which rival senses does this token keep?", "does the referent forbid this reading?", and "how does a
preposition+pronoun render once the referent is known?" — naḥw principles 2, 4 and 5.

  nahw/rules/context-sense-rules.json      -> context_sense_alternatives() / polyseme_quarantine_violations()
  nahw/rules/referent-guard-rules.json     -> referent_gloss() / proper_noun_verb_violations()
  nahw/rules/preposition-pronoun-rules.json-> preposition_pronoun_render() / root_guard_violation()
  nahw/rules/pronoun-attachment-rules.json -> attachment_role() / is_forbidden_attachment()

**Ambiguity-preserving by construction.** `context_sense_alternatives()` NEVER picks a sense: the rules' decision
tables are keyed on free-text `when` conditions, which this module refuses to interpret, so every rival reading is
returned and the decision is the file's own pending. Only the parts that are structurally decidable — the
quarantine table (surface -> blocked sibling sense), the referent tables under a CLOSED referent vocabulary, the
`renderings_by_referent` list, and the host-POS attachment map — resolve.

CLI:  python tools/fusha_nahw_context_rules.py --status | --self-test
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
from tools.fusha_nahw_particle_rules import (  # noqa: E402  (one typed-evidence contract)
    mint_fixture_observation, typed_observation,
)

# Referent, proper-vs-common and ambiguous attachment decisions are HUMAN/SCHOLAR routed by
# nahw/evals/grammar-decision-gates.json. Typed evidence can move them to `candidate`; nothing here resolves
# them, because `referent_sensitive_gloss` is two-vote and `proper_vs_common_noun` is human-source-review.
REFERENT_ROUTE = "human_source_review_required"
REFERENT_PROCEDURE = "nahw/procedures/referent-context.md"

RULES_DIR = os.path.join(_REPO, "nahw", "rules")
CONTEXT_SENSE_PATH = os.path.join(RULES_DIR, "context-sense-rules.json")
REFERENT_GUARD_PATH = os.path.join(RULES_DIR, "referent-guard-rules.json")
PREP_PRONOUN_PATH = os.path.join(RULES_DIR, "preposition-pronoun-rules.json")
PRONOUN_ATTACH_PATH = os.path.join(RULES_DIR, "pronoun-attachment-rules.json")

_CACHE = {}


def _load(path):
    if path not in _CACHE:
        with open(path, encoding="utf-8") as fh:
            _CACHE[path] = json.load(fh)
    return _CACHE[path]


def load_context_sense_rules():
    return _load(CONTEXT_SENSE_PATH)


def load_referent_guard_rules():
    return _load(REFERENT_GUARD_PATH)


def load_preposition_pronoun_rules():
    return _load(PREP_PRONOUN_PATH)


def load_pronoun_attachment_rules():
    return _load(PRONOUN_ATTACH_PATH)


def _same(a, b):
    return N.norm_strict(a or "") == N.norm_strict(b or "")


def _root_key(root):
    """A root's bare consonant skeleton, separator-insensitive (ل ي ن == ل-ي-ن)."""
    return N.norm(re.sub(r"[\s\-‐-―]+", "", root or ""))


def _english_head(text):
    """The English head of a rule field like 'angels (مَلَك)' or 'peace (سَلَام) as the headword sense'."""
    head = re.split(r"[(（]", text or "", 1)[0]
    head = re.split(r"\bas the\b", head, 1)[0]
    return head.strip(" /").lower()


# ---------------------------------------------------------------------------
# context-sense-rules.json — rivals preserved, prose conditions NOT executed
# ---------------------------------------------------------------------------
# A surface key is NOT a lexeme. norm_strict collapses harakāt and shadda, so Form II يُقَدِّرُ keys the same as
# Form I يَقْدِرُ, and passive أُتِيَ keys the same as active أَتَى. Each context-sense rule therefore declares the
# TRUSTED MORPHOLOGY that distinguishes its identity; without those fields the token stays pending and no rival
# table is offered at all. This is the executable form of "surface match NEVER authorizes reuse".
CONTEXT_SENSE_IDENTITY = {
    "qadara_contronym": {"pos": "verb", "derived_form": "I", "voice": "active", "lemma": "قَدَرَ"},
    "ataa_object_selected": {"pos": "verb", "derived_form": "I", "voice": "active", "lemma": "أَتَى"},
}


def morphology_match(rule_id, morphology):
    """Return (ok, defect). Trusted morphology must be present AND agree on every distinguishing field."""
    required = CONTEXT_SENSE_IDENTITY.get(rule_id)
    if required is None:
        return True, None
    if not isinstance(morphology, dict) or not morphology:
        return False, "morphology_absent"
    for field, expected in required.items():
        got = morphology.get(field)
        if got is None:
            return False, "morphology_field_absent:%s" % field
        if str(got) != str(expected):
            return False, "morphology_mismatch:%s" % field
    return True, None


def context_sense_alternatives(surface, morphology=None, rules=None):
    """Return the full rival reading set for a contronym / multi-sense token. Never selects a sense.

    The rules' `decision_table[].when` fields are natural-language context descriptions; interpreting them as
    code would be exactly the "generic naḥw resolver" the architecture forbids. So they are surfaced verbatim as
    documentary rivals, and the decision stays pending with the file's own reason code.

    A rule only applies when TRUSTED MORPHOLOGY confirms the lexeme identity (see CONTEXT_SENSE_IDENTITY);
    absent or disagreeing morphology yields pending with no rival table, never a same-surface match.
    """
    rules = rules or load_context_sense_rules()
    for rule in rules.get("rules", []):
        if not _same(rule.get("surface"), surface):
            continue
        ok, defect = morphology_match(rule["id"], morphology)
        if not ok:
            return {"rule_id": rule["id"], "surface": surface, "candidate_glosses": [],
                    "rival_readings": [], "decision": "pending",
                    "pending_reason": "identity_not_established", "morphology_defect": defect,
                    "required_morphology": dict(CONTEXT_SENSE_IDENTITY[rule["id"]]),
                    "prose_conditions_are_documentary": True,
                    "route": "sarf/procedures/verb-form.md", "status": "consumed"}
        rivals = []
        pending_reason = "context_sensitive_needs_nahw"
        for row in rule.get("decision_table", []):
            rivals.append({"when": row.get("when"), "contextual_choice": row.get("contextual_choice"),
                           "decision": row.get("decision"), "reason": row.get("reason"),
                           "reason_code": row.get("reason_code"),
                           "pending_reason": row.get("pending_reason")})
            if row.get("pending_reason"):
                pending_reason = row["pending_reason"]
        return {"rule_id": rule["id"], "surface": surface,
                "candidate_glosses": list(rule.get("candidate_glosses") or []),
                "context_signal": rule.get("context_signal"),
                "rival_readings": rivals, "decision": "pending", "pending_reason": pending_reason,
                "prose_conditions_are_documentary": True,
                "route": "nahw/procedures/referent-context.md", "status": "consumed"}
    nsr = rules.get("negation_sense_rule") or {}
    if nsr and _same(nsr.get("surface"), surface):
        return {"rule_id": nsr.get("id"), "surface": surface,
                "candidate_glosses": list(nsr.get("candidate_glosses") or []),
                "context_signal": nsr.get("context_signal"), "rival_readings": [],
                "decision": nsr.get("decision", "pending"),
                "pending_reason": nsr.get("pending_reason", "context_sensitive_needs_nahw"),
                "prose_conditions_are_documentary": True,
                "route": "nahw/procedures/negation.md", "status": "consumed"}
    return {"rule_id": None, "surface": surface, "candidate_glosses": [], "rival_readings": [],
            "decision": "out_of_domain", "prose_conditions_are_documentary": True,
            "status": "out_of_domain"}


def polyseme_quarantine_violations(surface, gloss, rules=None):
    """Structural guard: a lexically-near same-root sibling sense may never leak onto this token."""
    if not gloss:
        return []
    rules = rules or load_context_sense_rules()
    low = gloss.lower()
    out = []
    for row in (rules.get("polyseme_quarantines") or {}).get("entries", []):
        if not _same(row.get("surface"), surface):
            continue
        blocked = _english_head(row.get("blocked_sense", ""))
        if blocked and re.search(r"\b%s\b" % re.escape(blocked), low):
            out.append({"surface": row["surface"], "blocked_sense": row.get("blocked_sense"),
                        "correct": row.get("correct"), "context": row.get("context"),
                        "reason_code": row.get("reason_code", "multi_sense"),
                        "matched": blocked})
    return out


# ---------------------------------------------------------------------------
# referent-guard-rules.json — closed referent vocabulary, never inferred
# ---------------------------------------------------------------------------
# rule_id -> {closed referent class: the row's OWN `when_referent` value}. Keying on the row's verbatim
# discriminator rather than its array position means reordering the decision_table cannot silently re-pair a
# class with another row's gloss — the reordered-table mutation probe checks exactly that. `class_coverage_errors`
# additionally requires the mapping to be total and injective over the table.
REFERENT_CLASS_KEYS = {
    "halim_referent": {
        "human": "a human (e.g. Ibrāhīm in إِنَّ إِبْرَاهِيمَ لَأَوَّاهٌ حَلِيمٌ)",
        "allah": "Allah",
        "unidentified": "unidentified",
    },
    "salihan_proper_vs_common": {
        "deed": "an action / deed (e.g. عَمِلَ صَٰلِحًا)",
        "proper_noun": "the messenger sent to Thamūd",
        "unidentified": "unidentified",
    },
}
REFERENT_CLASSES = sorted({c for m in REFERENT_CLASS_KEYS.values() for c in m})


def _row_for_class(rule, referent_class):
    """The decision_table row whose own `when_referent` matches this class key. Position is never used."""
    key = REFERENT_CLASS_KEYS.get(rule["id"], {}).get(referent_class)
    if key is None:
        return None
    for row in rule.get("decision_table", []):
        if row.get("when_referent") == key:
            return row
    return None


def class_coverage_errors(rules=None):
    """Every referent class must map to exactly one row, and every row must be claimed by exactly one class."""
    rules = rules or load_referent_guard_rules()
    errs = []
    for rule in rules.get("rules", []):
        table = rule.get("decision_table")
        if not table:
            continue
        mapping = REFERENT_CLASS_KEYS.get(rule["id"])
        if mapping is None:
            errs.append("referent-guard-rules#%s has a decision_table but no explicit class keys" % rule["id"])
            continue
        keys = list(mapping.values())
        if len(set(keys)) != len(keys):
            errs.append("referent-guard-rules#%s maps two classes to the same row key" % rule["id"])
        table_keys = [row.get("when_referent") for row in table]
        if len(set(table_keys)) != len(table_keys):
            errs.append("referent-guard-rules#%s decision_table has duplicate when_referent values"
                        % rule["id"])
        for cls, key in mapping.items():
            if key not in table_keys:
                errs.append("referent-guard-rules#%s class %r maps to absent row key %r"
                            % (rule["id"], cls, key))
        for key in table_keys:
            if key not in keys:
                errs.append("referent-guard-rules#%s row %r is claimed by no class" % (rule["id"], key))
    return errs


def referent_gloss(surface, evidence=None, at=None, rules=None):
    """Read an attribute/homograph BY ITS REFERENT — never from a caller label.

    `evidence` must be a typed, source-addressed observation whose value is in this rule's closed referent
    vocabulary. Even with that evidence the result is a CANDIDATE routed to human/source review: referent-
    sensitive and proper-vs-common decisions are human-gated by the gates SSOT, so nothing here resolves them.
    All rival glosses are preserved either way.
    """
    rules = rules or load_referent_guard_rules()
    for rule in rules.get("rules", []):
        if not _same(rule.get("surface"), surface):
            continue
        classes = REFERENT_CLASS_KEYS.get(rule["id"], {})
        base = {"rule_id": rule["id"], "surface": surface,
                "candidate_glosses": list(rule.get("candidate_glosses") or []),
                "referent_vocabulary": sorted(classes),
                "gate": REFERENT_ROUTE, "route": REFERENT_PROCEDURE,
                "hard_guard": rule.get("hard_guard"), "status": "consumed"}
        coverage = class_coverage_errors(rules)
        if coverage:
            base.update({"decision": "pending", "pending_reason": "referent_unresolved",
                         "class_coverage_errors": coverage,
                         "reason": "the referent class map does not cover this rule's table exactly"})
            return base
        value, defect, art = typed_observation(evidence, set(classes),
                                               bind={"kind": "referent", "value": rule["id"]},
                                               surface=surface, at=at)
        base["at"] = at
        if defect:
            base.update({"decision": "pending", "pending_reason": "referent_unresolved",
                         "evidence_defect": defect, "evidence_id": None, "source_address": None,
                         "reason": "a referent must arrive as a validated observation artifact in %s"
                                   % sorted(classes)})
            return base
        row = _row_for_class(rule, value)
        if row is None:
            base.update({"decision": "pending", "pending_reason": "referent_unresolved",
                         "evidence_defect": "class_row_missing"})
            return base
        base.update({"referent_class": value,
                     "decision": "pending" if row.get("decision") != "resolved" else "candidate",
                     "gloss_candidate": row.get("contextual_choice"),
                     "evidence_id": art["evidence_id"], "source_address": art["source_address"],
                     "producer_trust": art["producer_trust"],
                     "reason": row.get("reason"), "pending_reason": row.get("pending_reason"),
                     "confidence": row.get("confidence")})
        return base
    return {"rule_id": None, "surface": surface, "decision": "out_of_domain", "status": "out_of_domain"}


def proper_noun_verb_violations(surface, gloss, rules=None):
    """POS guard: a proper noun is never glossed as its homographic verb (the file's own examples table)."""
    if not gloss:
        return []
    rules = rules or load_referent_guard_rules()
    low = gloss.strip().lower()
    out = []
    for rule in rules.get("rules", []):
        for ex in rule.get("examples", []):
            if not _same(ex.get("surface"), surface):
                continue
            wrong = (ex.get("wrong") or "").strip().lower()
            if wrong and (low == wrong or low.startswith("to ")):
                out.append({"rule_id": rule["id"], "surface": ex["surface"], "wrong": ex.get("wrong"),
                            "correct": ex.get("correct"),
                            "reason_code": ex.get("reason_code", "proper_name"),
                            "guard": rule.get("guard")})
    return out


def referent_general_guards(rules=None):
    return list((rules or load_referent_guard_rules()).get("general_guards") or [])


# ---------------------------------------------------------------------------
# preposition-pronoun-rules.json — wording by referent + the إِلَيْنَا root guard
# ---------------------------------------------------------------------------
# rule_id -> {closed referent class: renderings_by_referent index}
# Keyed on each rendering's OWN `referent` value, never on its array position (see REFERENT_CLASS_KEYS).
PP_REFERENT_KEYS = {
    "bihi": {"person_masc": "a person (masc.)", "thing": "a thing / abstraction",
             "belief_object": "belief object (آمَنَ بِهِ)"},
    "lahu": {"person_masc": "a person (masc.)", "thing": "a thing / abstraction",
             "allah": "Allah (لَهُ ٱلْمُلْك)"},
    "ilayna": {"first_person_plural": "1pl (us)"},
    "inda": {"physical_proximity": "physical proximity", "possession": "possession (عِنْدَهُ)",
             "allah": "Allah (عِندَ ٱللَّهِ)"},
}


def preposition_pronoun_render(surface, evidence=None, at=None, rules=None):
    """Render a preposition(+pronoun) by referent, from TYPED source-addressed evidence only.

    A caller-supplied referent label never renders. With typed evidence the result is a CANDIDATE at the
    referent-sensitive gate; the full `renderings_by_referent` list is always returned so no rival is lost.
    The one exception is a row the rule FILE itself resolves unconditionally with a single rendering
    (إِلَيْنَا), where there is no referent choice to make.
    """
    rules = rules or load_preposition_pronoun_rules()
    for rule in rules.get("rules", []):
        if not _same(rule.get("surface"), surface):
            continue
        classes = PP_REFERENT_KEYS.get(rule["id"], {})
        base = {"rule_id": rule["id"], "surface": surface, "lexeme": rule.get("lexeme"),
                "base_sense": rule.get("base_sense"),
                "renderings": list(rule.get("renderings_by_referent") or []),
                "referent_vocabulary": sorted(classes),
                "gate": "two_vote_required", "route": REFERENT_PROCEDURE,
                "hard_guard": rule.get("hard_guard"), "polyseme_guard": rule.get("polyseme_guard"),
                "status": "consumed"}
        if rule.get("decision") == "resolved" and len(rule.get("renderings_by_referent") or []) == 1:
            # the file itself resolves this row unconditionally (إِلَيْنَا): one rendering, no referent choice
            base.update({"decision": "resolved", "gloss": rule.get("default"), "reason": rule.get("reason"),
                         "gate": "auto_safe"})
            return base
        value, defect, art = typed_observation(evidence, set(classes),
                                               bind={"kind": "referent", "value": rule["id"]},
                                               surface=surface, at=at)
        base["at"] = at
        if defect:
            base.update({"decision": "pending",
                         "pending_reason": rule.get("pending_reason_when_unknown", "referent_unresolved"),
                         "evidence_defect": defect, "evidence_id": None, "source_address": None,
                         "reason": rule.get("reason")})
            return base
        key = classes[value]
        row = next((r for r in rule.get("renderings_by_referent", []) if r.get("referent") == key), None)
        if row is None:
            base.update({"decision": "pending", "pending_reason": "referent_unresolved",
                         "evidence_defect": "class_row_missing"})
            return base
        base.update({"decision": "candidate", "referent_class": value,
                     "gloss_candidate": row.get("gloss"), "reason": rule.get("reason"),
                     "evidence_id": art["evidence_id"], "source_address": art["source_address"],
                     "producer_trust": art["producer_trust"]})
        return base
    return {"rule_id": None, "surface": surface, "decision": "out_of_domain", "status": "out_of_domain"}


def root_guard_violation(surface, root, rules=None):
    """The hard guard: إِلَيْنَا is إِلَى + نا, never the root ل ي ن (norm() over-recalls to it)."""
    if not root:
        return None
    rules = rules or load_preposition_pronoun_rules()
    for rule in rules.get("rules", []):
        hg = rule.get("hard_guard")
        if not hg or not _same(rule.get("surface"), surface):
            continue
        # The forbidden root is quoted in the guard's `do_not` as separated radicals (ل-ي-ن / ل ي ن). Requiring a
        # separator between every letter keeps this a root-skeleton match, never an ordinary-word match.
        forbidden = re.findall(r"[ء-ي](?:[\s\-‐-―]+[ء-ي])+", hg.get("do_not") or "")
        for cand in forbidden:
            if _root_key(cand) == _root_key(root):
                return {"rule_id": rule["id"], "surface": surface, "root": root,
                        "do_not": hg.get("do_not"), "why": hg.get("why"),
                        "reason_code": hg.get("reason_code_if_mis_matched", "seat_collapsed")}
    return None


# ---------------------------------------------------------------------------
# pronoun-attachment-rules.json — what an enclitic IS, by host POS (GAP-N3)
# ---------------------------------------------------------------------------
HOST_POS_KEY = {"N": "noun_host", "noun": "noun_host", "P": "preposition_host",
                "preposition": "preposition_host", "V": "verb_host", "verb": "verb_host"}


def attachment_role(host_pos, rules=None):
    """The enclitic's role as a function of the HOST's POS — read from the rule file, not hard-coded."""
    rules = rules or load_pronoun_attachment_rules()
    key = HOST_POS_KEY.get(host_pos)
    if key is None:
        return ""
    return (rules.get("attachment") or {}).get(key, "")


def attachment_two_vote_triggers(rules=None):
    return list((rules or load_pronoun_attachment_rules()).get("two_vote_required") or [])


def attachment_forbidden(rules=None):
    return list((rules or load_pronoun_attachment_rules()).get("forbidden") or [])


# Each `forbidden` entry is bound to a structural test; the entry's own text is the reported reason.
def _f_verb_subject_na_possessive(surface, suffix, host_pos):
    return suffix == "نا" and HOST_POS_KEY.get(host_pos) == "verb_host"


def _f_tanwin_alef_is_not_na(surface, suffix, host_pos):
    return suffix == "نا" and N.ends_tanwin_alef(surface)


FORBIDDEN_ATTACHMENT_TESTS = [
    ("treat verb-subject", _f_verb_subject_na_possessive),
    ("treat tanwin-alef", _f_tanwin_alef_is_not_na),
]


def is_forbidden_attachment(surface, suffix, host_pos, rules=None):
    """Return the rule file's forbidden-entry text when a structural test fires, else None."""
    rules = rules or load_pronoun_attachment_rules()
    entries = attachment_forbidden(rules)
    for prefix, test in FORBIDDEN_ATTACHMENT_TESTS:
        if not test(surface, suffix, host_pos):
            continue
        for entry in entries:
            if entry.startswith(prefix):
                return {"forbidden": entry, "surface": surface, "suffix": suffix, "host_pos": host_pos,
                        "schema": rules.get("schema")}
    return None


# ---------------------------------------------------------------------------
# truthful status inventory (charter requirement 7)
# ---------------------------------------------------------------------------
# Authoritative FILE-level consumption status for this helper's rule files. `consumed` means a
# PRODUCTION record-validation path reads the file and a distinct on/off probe proves it (see
# tools/validate_nahw_skill.py RULES_CONSUMPTION, which asserts exact agreement with this map).
# A helper being able to READ a file is not consumption.
FILE_CONSUMPTION = {
    "nahw/rules/context-sense-rules.json": "consumed",
    "nahw/rules/referent-guard-rules.json": "consumed",
    "nahw/rules/preposition-pronoun-rules.json": "consumed",
    "nahw/rules/pronoun-attachment-rules.json": "fixture_gated",
}


def _file_status(path, executable=True):
    """A rule row can never claim more than its file's authoritative status."""
    status = FILE_CONSUMPTION.get(path, "fixture_gated")
    return status if executable else "documentary"


def rule_status():
    out = {}
    cs = load_context_sense_rules()
    _cs = "nahw/rules/context-sense-rules.json"
    out[_cs] = {
        **{r["id"]: _file_status(_cs, False) for r in cs.get("rules", [])},
        "polyseme_quarantines": _file_status(_cs),
        "negation_sense_rule": _file_status(_cs, False),
        "decision_table.when (prose)": "documentary",
    }
    rg = load_referent_guard_rules()
    _rg = "nahw/rules/referent-guard-rules.json"
    out[_rg] = {r["id"]: _file_status(_rg, bool(r.get("examples"))) for r in rg.get("rules", [])}
    out["nahw/rules/referent-guard-rules.json"]["general_guards"] = "documentary"
    pp = load_preposition_pronoun_rules()
    _pp = "nahw/rules/preposition-pronoun-rules.json"
    out[_pp] = {r["id"]: _file_status(_pp, bool(r.get("hard_guard"))) for r in pp.get("rules", [])}
    _pa = "nahw/rules/pronoun-attachment-rules.json"
    out[_pa] = {k: _file_status(_pa) for k in ("attachment", "forbidden", "two_vote_required")}
    return out


def _self_test():
    bad = []

    def eq(name, got, want):
        if got != want:
            bad.append("%s: got %r want %r" % (name, got, want))

    MORPH = {"pos": "verb", "derived_form": "I", "voice": "active", "lemma": "قَدَرَ"}
    a = context_sense_alternatives("يَقْدِرُ", MORPH)
    eq("contronym pending", a["decision"], "pending")
    eq("contronym rivals kept", len(a["candidate_glosses"]) >= 2, True)
    eq("contronym without morphology is not matched",
       context_sense_alternatives("يَقْدِرُ")["pending_reason"],
       "identity_not_established")
    eq("Form II does not inherit the Form I table",
       context_sense_alternatives("يُقَدِّرُ",
                                  dict(MORPH, derived_form="II"))["morphology_defect"],
       "morphology_mismatch:derived_form")
    eq("passive does not inherit the active table",
       context_sense_alternatives("أُتِي",
                                  {"pos": "verb", "derived_form": "I", "voice": "passive",
                                   "lemma": "أَتَى"})["morphology_defect"],
       "morphology_mismatch:voice")
    eq("quarantine angels", bool(polyseme_quarantine_violations("ٱلْمُلْك", "angels")), True)
    eq("quarantine clean", polyseme_quarantine_violations("ٱلْمُلْك", "sovereignty"), [])
    eq("referent class map is total and injective", class_coverage_errors(), [])
    HALIM = "حَلِيمٌ"
    EV = mint_fixture_observation("human", source_address="quran:2:26:20", quran_loc="2:26", word=20,
                                  surface=HALIM, target_kind="referent", target_value="halim_referent")
    eq("halim label alone never resolves", referent_gloss(HALIM, "human")["decision"], "pending")
    eq("halim typed artifact -> candidate only", referent_gloss(HALIM, EV, at="quran:2:26:20")["decision"], "candidate")
    eq("halim stays human-routed", referent_gloss(HALIM, EV, at="quran:2:26:20")["gate"], "human_source_review_required")
    eq("halim candidate carries the evidence id", referent_gloss(HALIM, EV, at="quran:2:26:20")["evidence_id"],
       EV["observation_id"])
    eq("halim no evidence", referent_gloss(HALIM)["decision"], "pending")
    eq("halim off-vocabulary referent",
       referent_gloss(HALIM, mint_fixture_observation(
           "martian", source_address="quran:2:26:20", quran_loc="2:26", word=20, surface=HALIM,
           target_kind="referent", target_value="halim_referent"), at="quran:2:26:20")["evidence_defect"],
       "observation_off_vocabulary")
    eq("halim observation cannot be reused for another rule",
       referent_gloss("صَٰلِحًا", EV,
                      at="quran:2:26:20")["evidence_defect"],
       "surface_mismatch")
    eq("muhammad verb", bool(proper_noun_verb_violations("مُحَمَّد", "to praise")), True)
    BIHI = "بِهِ"
    PPEV = mint_fixture_observation("thing", source_address="quran:2:26:20", quran_loc="2:26", word=20,
                                    surface=BIHI, target_kind="referent", target_value="bihi")
    eq("bihi label alone never renders", preposition_pronoun_render(BIHI, "thing")["decision"], "pending")
    eq("bihi typed artifact -> candidate", preposition_pronoun_render(BIHI, PPEV, at="quran:2:26:20")["decision"], "candidate")
    eq("bihi rivals preserved", len(preposition_pronoun_render(BIHI, PPEV, at="quran:2:26:20")["renderings"]) >= 3, True)
    eq("bihi unknown", preposition_pronoun_render(BIHI, None)["decision"], "pending")
    eq("referent evidence replayed at another occurrence is rejected",
       referent_gloss(HALIM, EV, at="quran:2:2:1")["evidence_defect"], "occurrence_not_current")
    eq("referent evidence without a caller occurrence never becomes a candidate",
       referent_gloss(HALIM, EV)["evidence_defect"], "caller_occurrence_absent")
    eq("pp-pronoun evidence replayed at another occurrence is rejected",
       preposition_pronoun_render(BIHI, PPEV, at="quran:2:2:1")["evidence_defect"],
       "occurrence_not_current")
    eq("ilayna root guard", bool(root_guard_violation("إِلَيْنَا", "ل ي ن")), True)
    eq("ilayna clean root", root_guard_violation("إِلَيْنَا", "أ ل ي"), None)
    eq("verb host not possessive", "NOT possessive" in attachment_role("V"), True)
    eq("tanwin alef guard", bool(is_forbidden_attachment("قُرْءَانًا", "نا", "N")), True)
    eq("possessive allowed", is_forbidden_attachment("أَعْمَالُنَا", "نا", "N"), None)
    for path, rows in rule_status().items():
        for rid, st in rows.items():
            if st not in ("consumed", "fixture_gated", "documentary", "candidate_only"):
                bad.append("%s#%s: untruthful status %r" % (path, rid, st))
    if bad:
        print("FAIL — fusha_nahw_context_rules self-test:")
        for b in bad:
            print("  -", b)
        return 1
    print("PASS — context/referent/preposition-pronoun consumer self-test "
          "(rivals preserved, quarantines enforced, referent vocabulary closed, attachment by host POS)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.status:
        print(json.dumps(rule_status(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return _self_test()


if __name__ == "__main__":
    sys.exit(main())
