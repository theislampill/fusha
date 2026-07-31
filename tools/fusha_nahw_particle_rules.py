#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consumer for the PARTICLE domain of nahw/rules/ — homograph harakāt, negation scope, state transitions.

Three rule files, one bounded domain (naḥw principles 1 and 3). This is deliberately NOT a general naḥw
resolver: it answers only "which reading does the CONTENT-LETTER diacritic license?", "what does the governing
negative do to the gloss?", and "may this reading take that syntactic role?".

  nahw/rules/particle-context-rules.json   -> resolve_particle_homograph()
  nahw/rules/negation-rules.json           -> negation_effect()
  nahw/rules/state-transition-rules.json   -> transition() / forbidden_gloss_violations()

**Prose is never executed.** Each rule's `when` / `reason` / `why_forbidden` text is documentary. Behaviour comes
from (a) a CLOSED discriminator registry keyed by rule id — the same idiom as the ṣarf increment discriminators in
tools/skill_fixtures/ — which reports structured observations from tools.normalize_ar, and (b) the rule DATA
(`members`, `decision_if_A/B`, `pending_fallback`, `governs`, `forbidden_gloss`, `two_vote_trigger`). A rule id with
no registered discriminator is reported `documentary`, never guessed at; rule_status() is the truthful inventory.

Fail-open is forbidden: an absent diacritic yields the file's own `pending_fallback`, never the frequent reading.

CLI:  python tools/fusha_nahw_particle_rules.py --status | --self-test
"""
import argparse
import json
import os
import unicodedata
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402

import hashlib  # noqa: E402
import re  # noqa: E402

RULES_DIR = os.path.join(_REPO, "nahw", "rules")
PARTICLE_RULES_PATH = os.path.join(RULES_DIR, "particle-context-rules.json")
NEGATION_RULES_PATH = os.path.join(RULES_DIR, "negation-rules.json")
STATE_RULES_PATH = os.path.join(RULES_DIR, "state-transition-rules.json")

_CACHE = {}


def _load(path):
    if path not in _CACHE:
        with open(path, encoding="utf-8") as fh:
            _CACHE[path] = json.load(fh)
    return _CACHE[path]


# ---------------------------------------------------------------------------
# typed, source-addressed observations — the ONLY thing that may move a state
# ---------------------------------------------------------------------------
# A caller label is not evidence, and neither is an address-SHAPED string. `trigger_observed=True`,
# `maa_function="negation"`, `referent_class="human"` and a free mood string are assertions BY the caller.
# Every state-moving input must be a validated, immutable OBSERVATION ARTIFACT:
#
#   {"observation_id": "obs:<hex>", "producer": "<authorized producer id>",
#    "evidence_class": "source_addressed", "source_address": "quran:2:284:1",
#    "occurrence": {"quran_loc": "2:284", "word": 1, "surface": "لِّلَّهِ"},
#    "target": {"kind": "token|state|referent|surface", "value": "<the exact thing under decision>"},
#    "observation": "<closed-vocabulary value>", "integrity": "<sha256 of the artifact minus integrity>"}
#
# Five independent checks, each of which alone fails the artifact closed:
#   1. SHAPE      — every field present; a bare boolean/string/label is rejected outright.
#   2. PRODUCER   — must be in OBSERVATION_PRODUCERS. A caller-minted producer is not evidence.
#   3. COORDINATE — `source_address` must resolve IN SCOPE against the repository's own authority
#                   (tools/fusha_check.resolve_address over qamus/indexes/current/quran-usage-spine-full.jsonl).
#                   quran:999:999:999 and an out-of-range word index both fail. No local coordinate
#                   authority is invented here, and \A..\Z anchoring rejects a newline-suffixed address.
#   4. BINDING    — `occurrence` and `target` must match the exact token/surface/state/referent under
#                   decision. Re-using an observation for another token, surface, from-state or referent
#                   fails closed.
#   5. INTEGRITY  — the artifact must hash to its own `integrity` value, so a mutated field is detectable.
#
# HONEST LIMIT. The repository has no signing observation producer and no per-word WRITTEN-SURFACE authority
# (the spine carries token counts and glosses, not surfaces). So `occurrence.surface` is bound and compared but
# cannot be *verified*, and every producer currently registered is a FIXTURE producer. A validated artifact can
# therefore only ever yield `candidate`; nothing here returns `resolved` from an observation. The missing
# producer + surface authority is packetized as TP-NAHW-A2-OBSERVATION-PRODUCER.
SOURCE_ADDRESS_RE = re.compile(r"\A(?:quran:\d{1,3}:\d{1,3}(?::\d{1,3})?|wbw:\d{1,3}:\d{1,3}:\d{1,3})\Z")
OBSERVATION_ID_RE = re.compile(r"\Aobs:[0-9a-f]{8,64}\Z")
EVIDENCE_CLASS_ACCEPTED = "source_addressed"
TARGET_KINDS = frozenset({"token", "state", "referent", "surface"})
# Closed producer registry. `trust` is deliberately `fixture`: no repository producer signs observations yet,
# so no observation may promote a decision beyond `candidate`.
OBSERVATION_PRODUCERS = {
    "nahw-a2-fixture-observer": {"trust": "fixture", "may_resolve": False},
}
OBSERVATION_REQUIRED_FIELDS = ("observation_id", "producer", "evidence_class", "source_address",
                               "occurrence", "target", "observation", "integrity")


def observation_integrity(artifact):
    """Deterministic content hash over the artifact minus its own `integrity` field."""
    body = {k: v for k, v in artifact.items() if k != "integrity"}
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _coordinate_in_scope(address):
    """Validate a canonical coordinate against the repository's own address authority (never a local table)."""
    from tools.fusha_check import resolve_address  # lazy: fusha_check imports this module's package peers
    return resolve_address(address).get("scope") == "in_scope_source_addressed"


def typed_observation(evidence, vocabulary=None, bind=None, surface=None, at=None):
    """Return (value, defect, artifact). `value` is non-None only for a fully validated observation artifact.

    `bind`    the exact thing under decision: {"kind": ..., "value": ...}; must equal artifact["target"].
    `surface` the written surface under decision; must equal artifact["occurrence"]["surface"].
    `at`      the CALLER-supplied current exact source address. An artifact is evidence about ONE occurrence,
              so a same-surface artifact replayed at a different address is rejected
              (`occurrence_not_current`). A consumer that can produce a candidate MUST supply it; omitting it
              yields `caller_occurrence_absent`, never a candidate.

    defect ∈ {absent, not_a_record, caller_label, artifact_incomplete, observation_id_invalid,
              producer_not_authorized, evidence_class_not_source_addressed, source_address_invalid,
              source_address_not_in_scope, occurrence_invalid, occurrence_address_mismatch,
              surface_mismatch, target_invalid, target_binding_mismatch, integrity_mismatch,
              observation_absent, observation_off_vocabulary}
    """
    # ROUND-10: the caller's CURRENT address must be an exact word-level Qur'anic coordinate. SOURCE_ADDRESS_RE
    # also admits an ayah-only address and word 0, neither of which names the word under decision.
    if at is not None:
        from tools.grade_grammar_reasoning import occurrence_defect  # noqa: PLC0415 (lazy: no import cycle)
        if not isinstance(at, str) or occurrence_defect(at) is not None:
            return None, "caller_occurrence_invalid", None
    if evidence is None:
        return None, "absent", None
    if isinstance(evidence, bool):
        return None, "caller_label", None          # a bare boolean is an assertion, never an observation
    if isinstance(evidence, str):
        return None, "caller_label", None          # an address-SHAPED string is not an observation
    if not isinstance(evidence, dict):
        return None, "not_a_record", None
    if any(f not in evidence for f in OBSERVATION_REQUIRED_FIELDS):
        return None, "artifact_incomplete", None
    if not OBSERVATION_ID_RE.match(str(evidence.get("observation_id") or "")):
        return None, "observation_id_invalid", None
    if evidence.get("producer") not in OBSERVATION_PRODUCERS:
        return None, "producer_not_authorized", None
    if evidence.get("evidence_class") != EVIDENCE_CLASS_ACCEPTED:
        return None, "evidence_class_not_source_addressed", None
    address = evidence.get("source_address")
    if not (isinstance(address, str) and SOURCE_ADDRESS_RE.match(address)):
        return None, "source_address_invalid", None
    if not _coordinate_in_scope(address):
        return None, "source_address_not_in_scope", None
    occ = evidence.get("occurrence")
    if not (isinstance(occ, dict) and occ.get("quran_loc") and occ.get("word") is not None
            and isinstance(occ.get("surface"), str) and occ["surface"].strip()):
        return None, "occurrence_invalid", None
    if address != "quran:%s:%s" % (occ["quran_loc"], occ["word"]):
        return None, "occurrence_address_mismatch", None
    # ROUND-10: norm_strict erases the harakāt, so حَلِيمٌ and حَلِيمٍ compared EQUAL and an artifact about
    # one written form was accepted as evidence about another. Evidence binds the exact written surface.
    if surface is not None:
        from tools.grade_grammar_reasoning import exact_surface_equal  # noqa: PLC0415 (lazy)
        if not exact_surface_equal(occ["surface"], surface):
            return None, "surface_mismatch", None
    target = evidence.get("target")
    if not (isinstance(target, dict) and target.get("kind") in TARGET_KINDS
            and isinstance(target.get("value"), str) and target["value"].strip()):
        return None, "target_invalid", None
    if bind is not None and (target.get("kind") != bind.get("kind")
                             or target.get("value") != bind.get("value")):
        return None, "target_binding_mismatch", None
    if evidence.get("integrity") != observation_integrity(evidence):
        return None, "integrity_mismatch", None
    value = evidence.get("observation")
    if not (isinstance(value, str) and value.strip()):
        return None, "observation_absent", None
    if vocabulary is not None and value not in vocabulary:
        return None, "observation_off_vocabulary", None
    # LAST: the artifact is internally valid — is it about the occurrence the caller is deciding RIGHT NOW?
    if at is None:
        # the consumer never named the occurrence it is deciding, so no artifact can be shown to be current
        return None, "caller_occurrence_absent", None
    if at != address:
        return None, "occurrence_not_current", None
    return value, None, {"evidence_id": evidence["observation_id"], "source_address": address,
                         "producer": evidence["producer"],
                         "producer_trust": OBSERVATION_PRODUCERS[evidence["producer"]]["trust"],
                         "may_resolve": OBSERVATION_PRODUCERS[evidence["producer"]]["may_resolve"],
                         "occurrence": dict(occ), "target": dict(target)}


def mint_fixture_observation(observation, *, source_address, quran_loc, word, surface, target_kind,
                             target_value, producer="nahw-a2-fixture-observer", observation_id=None):
    """Build a well-formed FIXTURE observation artifact (tests/fixtures only; never a production producer)."""
    art = {"observation_id": observation_id or ("obs:%s" % hashlib.sha256(
               ("%s|%s|%s|%s" % (source_address, surface, target_value, observation)).encode("utf-8")
           ).hexdigest()[:16]),
           "producer": producer, "evidence_class": EVIDENCE_CLASS_ACCEPTED,
           "source_address": source_address,
           "occurrence": {"quran_loc": quran_loc, "word": word, "surface": surface},
           "target": {"kind": target_kind, "value": target_value},
           "observation": observation}
    art["integrity"] = observation_integrity(art)
    return art


def load_particle_rules():
    return _load(PARTICLE_RULES_PATH)


def load_negation_rules():
    return _load(NEGATION_RULES_PATH)


def load_state_rules():
    return _load(STATE_RULES_PATH)


# ---------------------------------------------------------------------------
# closed discriminator registry — structured observations only, no prose parsing
# ---------------------------------------------------------------------------
def _seat(surface):
    """The hamza seat of the first letter as preserved by norm_strict (norm() deletes it entirely)."""
    s = N.norm_strict(surface)
    for ch in s:
        if ch in ("أ", "إ", "ٱ", "ا", "آ"):
            return ch
        if ch in ("و", "ف"):   # proclitic — keep scanning for the content letter
            continue
        break
    return ""


# ---------------------------------------------------------------------------
# ROUND-10: a homograph branch requires EVERY written mark its member needs
# ---------------------------------------------------------------------------
# Each discriminator used to read ONE signal and ignore the rest, so a token that carried the signal but
# CONTRADICTED the member's other required marks still resolved: مُن -> مَن, لَمَ -> لَمْ, لِمْ -> لِمَ,
# unvowelled أن -> أَنْ, إِنِّي -> "that I", أَنِّى/أَنَّي -> whichever branch the nūn's vowel suggested,
# كَل/كُلَا -> كَلَّا/كُلّ, نَعِم -> نَعَمْ. A missing mark is UNCERTAINTY, never positive evidence.
#
# The requirements below are the rule files' own `distinguish_by.also` lines made executable — the seat, the
# shadda, the sukūn, the content-letter haraka and the final yāʾ-vs-alif-maqṣūra shape — so this is
# enforcement of the committed rule data, not a new linguistic claim.
SUKUN = "\u0652"


def _mark_cluster(tok, target):
    """The harakāt cluster attached to the FIRST `target` base letter, or None when the letter is absent."""
    s = unicodedata.normalize("NFC", tok or "")
    for i, ch in enumerate(s):
        if ch == target:
            j, marks = i + 1, []
            while j < len(s) and 0x064B <= ord(s[j]) <= 0x0652:
                marks.append(s[j])
                j += 1
            return marks
    return None


def _has_mark(tok, target, mark):
    cluster = _mark_cluster(tok, target)
    return bool(cluster) and mark in cluster


def _final_base_letter(tok):
    """The last BASE letter, marks stripped. ى and ي are DIFFERENT letters and are never folded."""
    s = unicodedata.normalize("NFC", tok or "")
    for ch in reversed(s):
        if 0x064B <= ord(ch) <= 0x0655 or ch == "\u0670":
            continue
        return ch
    return ""


def _d_man_vs_min(surface):
    hm = N.haraka_on(surface, "م")
    obs = ["haraka(م)=%s" % (hm or "absent"), "shadda(ن)=%s" % N.shadda_on(surface, "ن")]
    if N.shadda_on(surface, "ن"):
        return None, obs + ["excluded: مَنَّ (verb 'to bestow') is outside this rule"]
    if "ن" not in N.bare(surface):
        return None, obs + ["nun_absent"]
    if hm == N.KASRA:
        return "B", obs
    if hm == N.FATHA:
        return "A", obs
    # ROUND-10: ḍamma is NOT fatḥa. مُن carries a mark that belongs to neither member, so it is a
    # contradiction, not a bare token, and it can never be positive evidence for مَن.
    return None, obs + ["haraka on mīm is neither fatḥa (مَن) nor kasra (مِن)"]


def _d_lam_vs_lima(surface):
    """لَمْ needs fatḥa on lām AND sukūn on mīm; لِمَ needs kasra on lām AND fatḥa on mīm."""
    hl = N.haraka_on(surface, "ل")
    hm = N.haraka_on(surface, "م")
    sukun_m = _has_mark(surface, "م", SUKUN)
    obs = ["haraka(ل)=%s" % (hl or "absent"), "haraka(م)=%s" % (hm or "absent"),
           "sukun(م)=%s" % sukun_m]
    if hl == N.FATHA and sukun_m:
        return "A", obs
    if hl == N.KASRA and hm == N.FATHA:
        return "B", obs
    return None, obs + ["the mīm mark does not confirm the member the lām mark suggests"]


def _d_an_vs_inna(surface):
    """Seat separates أ from إ; the SHADDA on the nūn separates light أَنْ/إِنْ from heavy أَنَّ/إِنَّ.

    ROUND-10: the seat GLYPH alone is not evidence — an unvowelled أن carries no haraka on the hamza at
    all, so it cannot testify to أَنْ/أَنَّ rather than إِنْ/إِنَّ written defectively. The seat letter must
    itself carry the vowel its member requires: fatḥa on أ, kasra on إ.
    """
    seat = _seat(surface)
    heavy = N.shadda_on(surface, "ن")
    obs = ["hamza_seat=%s" % (seat or "absent"), "shadda(ن)=%s" % heavy]
    if seat not in ("أ", "إ"):
        return None, obs
    if "ن" not in N.bare(surface):
        return None, obs + ["nun_absent"]
    seat_haraka = N.haraka_on(surface, seat)
    obs.append("haraka(%s)=%s" % (seat, seat_haraka or "absent"))
    required = N.FATHA if seat == "أ" else N.KASRA
    if seat_haraka != required:
        return None, obs + ["the hamza carries no confirming vowel; an unvowelled seat is uncertainty"]
    # ROUND-13: a nūn carrying a SHORT VOWEL is neither أَنْ/إِنْ (sukūn) nor أَنَّ/إِنَّ (shadda) — أَنِ,
    # أَنَ, إِنِ and إِنَ are contradicted, not merely unmarked, and must not resolve.
    nun_haraka = N.haraka_on(surface, "ن")
    obs.append("haraka(ن)=%s" % (nun_haraka or "absent"))
    if nun_haraka and not heavy:
        return None, obs + ["the nūn carries a short vowel: neither the sukūn of the light member nor the "
                            "shadda of the heavy one"]
    obs.append("weight=%s" % (an_family_weight(surface) or "unwritten"))
    return ("A" if seat == "أ" else "B"), obs


def an_family_weight(surface):
    """light | heavy | None — the weight of an ان-family token, and None whenever it is not WRITTEN.

    ROUND-13: "no shadda" was read as "light", so any unmarked nūn silently classified as أَنْ/إِنْ. Light
    is written with a sukūn and heavy with a shadda; a nūn carrying neither is unmarked, and a nūn carrying
    a short vowel instead (أَنِ, أَنَ, إِنِ, إِنَ) is neither member. Both answer None.
    """
    if "ن" not in N.bare(surface):
        return None
    if N.shadda_on(surface, "ن"):
        return "heavy"
    if _has_mark(surface, "ن", SUKUN):
        return "light"
    return None


def _d_anni_vs_anna(surface):
    """أَنِّي = أ seat + shadda + kasra on nūn + final yāʾ; أَنَّى = أ seat + shadda + fatḥa + final alif-maqṣūra.

    ROUND-10: the nūn's vowel alone decided the branch, so إِنِّي (an إ seat — inna + ī) was read as
    أَنَّ + ـِي, and أَنِّى / أَنَّي (right vowel, WRONG final letter) both resolved. Every mark the rule
    file names must agree, and ى is never folded to ي.
    """
    seat = _seat(surface)
    hn = N.haraka_on(surface, "ن")
    shadda = N.shadda_on(surface, "ن")
    final = _final_base_letter(surface)
    obs = ["hamza_seat=%s" % (seat or "absent"), "shadda(ن)=%s" % shadda,
           "haraka(ن)=%s" % (hn or "absent"), "final=%s" % (final or "absent")]
    if seat != "أ":
        return None, obs + ["this rule covers the أ seat only; an إ seat is the إِنَّ family"]
    if not shadda:
        return None, obs + ["both members carry a shadda on the nūn"]
    if hn == N.KASRA and final == "ي":
        return "A", obs
    if hn == N.FATHA and final == "ى":
        return "B", obs
    return None, obs + ["the final letter does not confirm the member the nūn vowel suggests"]


def _d_lima_vs_lamma(surface):
    sh = N.shadda_on(surface, "م")
    hl = N.haraka_on(surface, "ل")
    obs = ["shadda(م)=%s" % sh, "haraka(ل)=%s" % (hl or "absent")]
    if sh and hl == N.FATHA:
        return "A", obs
    if not sh and hl == N.KASRA:
        return "B", obs
    return None, obs + ["the lām vowel and the mīm shadda do not agree on one member"]


def _d_kull_vs_kalla(surface):
    """Both members carry a shadda on the lām; the kāf vowel then separates كُلّ from كَلَّا."""
    hk = N.haraka_on(surface, "ك")
    shadda_l = N.shadda_on(surface, "ل")
    obs = ["haraka(ك)=%s" % (hk or "absent"), "shadda(ل)=%s" % shadda_l]
    if not shadda_l:
        return None, obs + ["no shadda on the lām: neither كُلّ nor كَلَّا is written here"]
    if hk == N.DAMMA:
        return "A", obs
    # ROUND-13: كَلَّا is written with a final alif. كَلّ carries the kāf fatḥa and the lām shadda but not
    # the alif, so it is not that member.
    final = _final_base_letter(surface)
    obs.append("final=%s" % (final or "absent"))
    if hk == N.FATHA and final == "ا":
        return "B", obs
    return None, obs


def _d_nima_vs_naam(surface):
    """نِعْمَ = kasra on nūn + sukūn on ʿayn; نَعَمْ = fatḥa on nūn + fatḥa on ʿayn."""
    hn = N.haraka_on(surface, "ن")
    ha = N.haraka_on(surface, "ع")
    sukun_ayn = _has_mark(surface, "ع", SUKUN)
    obs = ["haraka(ن)=%s" % (hn or "absent"), "haraka(ع)=%s" % (ha or "absent"),
           "sukun(ع)=%s" % sukun_ayn]
    # ROUND-13: the MĪM decides the ending too — نِعْمَ ends in fatḥa, نَعَمْ in sukūn. نِعْمْ and نَعَمَ
    # each carry the right nūn/ʿayn marks with the WRONG final mark, and neither is its member.
    hm = N.haraka_on(surface, "م")
    sukun_mim = _has_mark(surface, "م", SUKUN)
    obs.append("haraka(م)=%s" % (hm or "absent"))
    obs.append("sukun(م)=%s" % sukun_mim)
    if hn == N.KASRA and sukun_ayn and hm == N.FATHA:
        return "A", obs
    if hn == N.FATHA and ha == N.FATHA and sukun_mim:
        return "B", obs
    return None, obs + ["the ʿayn and mīm marks do not confirm the member the nūn vowel suggests"]


DISCRIMINATORS = {
    "man_vs_min": _d_man_vs_min,
    "lam_vs_lima": _d_lam_vs_lima,
    "an_vs_inna": _d_an_vs_inna,
    "anni_vs_anna": _d_anni_vs_anna,
    "lima_vs_lamma": _d_lima_vs_lamma,
    "kull_vs_kalla": _d_kull_vs_kalla,
    "nima_vs_naam": _d_nima_vs_naam,
}


def _deproclitic(key):
    return key[1:] if key[:1] in ("و", "ف") and len(key) > 1 else key


def _norm_family(surface):
    """The rule-selection key: norm() with a leading و/ف proclitic stripped.

    norm() deletes the hamza seat outright (أَنْ -> 'ن'), so an alif is re-attached for the ان family; the SEAT
    itself is read separately by the discriminator, never by this key.
    """
    key = _deproclitic(N.norm(surface))
    if key and key[0] != "ا" and _seat(surface) in ("أ", "إ", "آ"):
        key = "ا" + key
    return key


def select_particle_rule(surface, rules=None):
    """Pick the rule whose `members` or `surface_norm` family covers this surface. Data-driven."""
    rules = rules or load_particle_rules()
    strict = N.norm_strict(surface)
    fam = _norm_family(surface)
    for rule in rules.get("rules", []):
        for member in rule.get("members", []):
            if N.norm_strict(member) == strict or _deproclitic(N.norm_strict(member)) == _deproclitic(strict):
                return rule
    for rule in rules.get("rules", []):
        if rule.get("surface_norm") and _deproclitic(rule["surface_norm"]) == fam:
            return rule
    return None


def resolve_particle_homograph(surface, rules=None):
    """Resolve a diacritic-homograph function word to its reading, or the file's own pending fallback.

    Returns {rule_id, branch, reading, gloss, decision, reason, pending_reason, evidence[], status}.
    """
    rules = rules or load_particle_rules()
    rule = select_particle_rule(surface, rules=rules)
    if rule is None:
        return {"rule_id": None, "branch": None, "decision": "pending", "reading": None, "gloss": None,
                "reason": None, "pending_reason": "no_rule", "evidence": [],
                "status": "out_of_domain", "surface": surface}
    rid = rule["id"]
    disc = DISCRIMINATORS.get(rid)
    if disc is None:
        return {"rule_id": rid, "branch": None, "decision": "pending", "reading": None, "gloss": None,
                "reason": None, "pending_reason": "no_discriminator", "evidence": [],
                "status": "documentary", "surface": surface}
    branch, obs = disc(surface)
    if branch is None:
        pf = rule.get("pending_fallback", {}) or {}
        return {"rule_id": rid, "branch": None, "decision": pf.get("decision", "pending"),
                "reading": None, "gloss": None, "reason": pf.get("note"),
                "pending_reason": pf.get("pending_reason", "homograph_haraka"), "evidence": obs,
                "status": "consumed", "surface": surface,
                "guard": rule.get("guard")}
    blk = rule.get("decision_if_%s" % branch, {}) or {}
    return {"rule_id": rid, "branch": branch, "decision": blk.get("decision", "pending"),
            "reading": blk.get("reading"), "gloss": blk.get("gloss"), "reason": blk.get("reason"),
            "pending_reason": None, "evidence": obs, "status": "consumed", "surface": surface,
            "guard": rule.get("guard")}


# ---------------------------------------------------------------------------
# negation-rules.json - the governing negative sets the gloss, after the homograph
# ---------------------------------------------------------------------------
# decision "resolved_with_context_else_pending" needs a syntactic OBSERVATION, and the observation vocabulary
# is closed. A caller label such as maa_function="negation" is an assertion, not evidence: it must arrive as a
# typed source-addressed observation record (see typed_observation). Even then these rows stay CANDIDATE at
# their released gate - the file itself never licenses an unreviewed resolution for them.
NEGATION_CONTEXT_REQUIRED = {
    # rule id -> (observation name, closed observation vocabulary, the value this rule requires)
    "laa_context": ("following_token_mood",
                    {"jussive", "indicative", "subjunctive", "nominal_indefinite_nasb"}, None),
    "maa_negation": ("maa_function",
                     {"negation", "relative", "interrogative", "masdariyya", "temporal",
                      "preventive_kaffa", "laysa_like"}, "negation"),
}
NEGATION_GATE = "two_vote_required"
# ROUND-7: negation rows used to be selected by norm_strict alone, so لِمَ ("why") fell through to the لَمْ
# jussive-negation row and resolved as lam_jussive. A row whose surface belongs to a diacritic-homograph family
# now applies ONLY when the particle consumer resolved that family to the bound branch.
NEGATION_ROW_HOMOGRAPH = {
    "lam_jussive": ("lam_vs_lima", "A"),
}


def negation_effect(surface, context=None, at=None, rules=None, particle_rules=None):
    """Apply nahw/rules/negation-rules.json. Homograph first (standing_order), then the negation effect.

    context maps an observation name to a TYPED, SOURCE-ADDRESSED observation record. A bare label, a bare
    boolean or an off-vocabulary value never resolves; it holds at the file's own pending reason.
    """
    rules = rules or load_negation_rules()
    context = context or {}
    strict = N.norm_strict(surface)
    row = None
    for r in rules.get("rules", []):
        if N.norm_strict(r["surface"]) == strict:
            row = r
            break
    if row is None:
        # the surface may still be an unresolved member of a homograph family this file covers
        pr = resolve_particle_homograph(surface, rules=particle_rules)
        if pr.get("rule_id") and pr.get("decision") == "pending":
            return {"rule_id": None, "decision": "pending", "pending_reason": pr["pending_reason"],
                    "reason": "standing_order: resolve the homograph before applying the negation effect",
                    "evidence": pr.get("evidence", []), "status": "consumed", "surface": surface}
        return {"rule_id": None, "decision": "out_of_domain", "pending_reason": None,
                "status": "out_of_domain", "surface": surface}

    # standing order: if this surface belongs to a homograph family, it must already be resolved
    pr = resolve_particle_homograph(surface, rules=particle_rules)
    if pr.get("rule_id") and pr.get("decision") == "pending":
        return {"rule_id": row["id"], "decision": "pending", "pending_reason": pr["pending_reason"],
                "reason": "standing_order: %s" % (rules.get("standing_order") or ""),
                "evidence": pr.get("evidence", []), "status": "consumed", "surface": surface}
    # the resolved reading must BE this row's particle, not merely share its norm_strict key
    bound = NEGATION_ROW_HOMOGRAPH.get(row["id"])
    if bound is not None and (pr.get("rule_id"), pr.get("branch")) != bound:
        return {"rule_id": row["id"], "decision": "pending", "pending_reason": "homograph_haraka",
                "homograph_mismatch": {"resolved": [pr.get("rule_id"), pr.get("branch")],
                                       "required": list(bound)},
                "reason": "the resolved reading is not this negation row's particle; a shared norm_strict key "
                          "is not identity",
                "evidence": pr.get("evidence", []), "status": "consumed", "surface": surface}

    need = NEGATION_CONTEXT_REQUIRED.get(row["id"])
    if need:
        name, vocabulary, required_value = need
        bind = {"kind": "token", "value": row["id"]}
        value, defect, art = typed_observation(context.get(name), vocabulary, bind=bind,
                                               surface=surface, at=at)
        base = {"rule_id": row["id"], "governs": row.get("governs"), "effect": row.get("effect"),
                "reason": row.get("guard"), "required_observation": name,
                "observation_vocabulary": sorted(vocabulary),
                "unresolved_alternatives": rival_analyses(vocabulary, selected=value,
                                                          gate=NEGATION_GATE, evidence_id=(art or {})
                                                          .get("evidence_id"), axis="maa_function"),
                "evidence": pr.get("evidence", []), "status": "consumed", "surface": surface,
                "at": at}
        if defect:
            base.update({"decision": "pending",
                         "pending_reason": row.get("pending_reason_when_unknown", "negation_scope"),
                         "evidence_defect": defect, "evidence_id": None, "source_address": None})
            return base
        base.update({"evidence_id": art["evidence_id"], "source_address": art["source_address"],
                     "producer": art["producer"], "producer_trust": art["producer_trust"]})
        if required_value is not None and value != required_value:
            # e.g. relative maa routed into the negation path: it is NOT negation here.
            base.update({"decision": "pending", "pending_reason": "maa_category_unresolved",
                         "observed": value, "out_of_scope_for_negation": True,
                         "route": "nahw/procedures/ma-function-decision.md"})
            return base
        # typed evidence present: the row becomes a CANDIDATE at its released gate, never an auto resolution.
        base.update({"decision": "candidate", "observed": value, "gate": NEGATION_GATE,
                     "gloss_candidate": row.get("gloss"), "pending_reason": None,
                     "route": "nahw/procedures/negation.md"})
        return base
    return {"rule_id": row["id"], "decision": "resolved", "governs": row.get("governs"),
            "effect": row.get("effect"), "gloss": row.get("gloss"), "reason": row.get("guard"),
            "pending_reason": None, "evidence": pr.get("evidence", []),
            "reason_code": rules.get("reason_code"), "status": "consumed", "surface": surface}


# ---------------------------------------------------------------------------
# state-transition-rules.json - role transitions + the forbidden-collision backstop
# ---------------------------------------------------------------------------
# Closed registry binding each forbidden_transition to the particle rule/branch it guards. The FROM side is
# structural (a resolved reading); the why_forbidden prose stays documentary.
FORBIDDEN_BINDINGS = {
    "min_not_man": ("man_vs_min", "B"),
    "lam_not_lima": ("lam_vs_lima", "A"),
    "lamma_not_lima": ("lima_vs_lamma", "A"),
    "anna_not_inna": ("an_vs_inna", "A"),
    "inna_not_an": ("an_vs_inna", "B"),
}
# The trigger each transition needs, as a closed observation vocabulary. A transition NEVER fires on a boolean.
TRANSITION_OBSERVATION_VOCAB = {
    "following_verb_nasb", "following_ism_nasb", "clause_initial_ism_nasb", "two_jussive_verbs",
    "following_sila_verb", "following_majrur_noun", "indefinite_noun_nasb", "mustathna_after_minhu",
    "second_noun_majrur_first_stripped", "past_verb_with_jawab",
}
TRANSITION_TRIGGERS = {
    "an_light_to_masdariyyah": "following_verb_nasb",
    "anna_heavy_to_emphatic_nasb_subject": "following_ism_nasb",
    "inna_heavy_to_tawkid": "clause_initial_ism_nasb",
    "in_light_to_conditional": "two_jussive_verbs",
    "man_relative_to_mubtada_or_object": "following_sila_verb",
    "min_preposition_to_jar_majrur": "following_majrur_noun",
    "la_indef_nasb_to_nafy_lil_jins": "indefinite_noun_nasb",
    "illa_to_istithna": "mustathna_after_minhu",
    "noun_noun_to_idafa": "second_noun_majrur_first_stripped",
    "lamma_temporal_to_zarf_clause": "past_verb_with_jawab",
}


def rival_analyses(vocabulary, *, selected, gate, evidence_id, axis):
    """Structured rival objects for the dependency-candidate-lattice `unresolved_alternatives[]` contract.

    Every rival keeps its own decision_status, gate, reason key slot and the evidence id that selected (or
    failed to select) it. A prose string is not a rival: dropping the selected role must still leave the rival
    set intact, which is what the removed-role mutation probe checks.
    """
    out = []
    for member in sorted(vocabulary):
        out.append({
            "axis": axis, "role": member,
            "decision_status": "unresolved" if selected is None else (
                "candidate_selected" if member == selected else "rejected_rival"),
            "selected": member == selected,
            "reason_key": None,                     # a registered reason key is required before selection
            "gate": gate, "evidence_id": evidence_id,
            "defeater": None if member == selected else "not observed at this address",
        })
    return out


# Each forbidden transition states the COLLISION it guards. Bind it to the homograph family that collision
# belongs to, so a transition's rivals are the siblings of ITS OWN collision — not every forbidden role in
# the file. Round-10 defect: the rival set was the global list, so a مِن/مَن transition carried أَنَّ/إِنَّ
# and لَمَّا/لِمَا roles as "rivals" it had no evidential relation to.
FORBIDDEN_COLLISION_FAMILY = {
    "min_not_man": "man_vs_min",
    "lam_not_lima": "lam_vs_lima",
    "lamma_not_lima": "lima_vs_lamma",
    "anna_not_inna": "an_vs_inna",
    "inna_not_an": "an_vs_inna",
}


def transition_rival_family(transition_id):
    """The homograph family whose forbidden siblings are THIS transition's authorized local rivals."""
    bound = TRANSITION_FROM_STATE.get(transition_id) or {}
    particle = bound.get("particle")
    return particle[0] if particle else None


def transition_rivals(row, rules, *, selected, evidence_id):
    """The transition's OWN local rival set.

    * gate values come from the registered ladder only (`candidate` was never a gate);
    * rivals are the target role, the file's own hold state, and the forbidden siblings of THIS
      transition's collision family — never the global forbidden list;
    * a rival is `rejected_rival` only when evidence actually defeats it. With no source-addressed
      observation nothing is defeated, so every unselected rival stays `unresolved`;
    * a transition with no authorized local rival lattice returns an exact unresolved BLOCKER rather than
      an invented rival set.
    """
    from tools import fusha_nahw_gate_rules as GATE      # noqa: PLC0415 (lazy: avoid an import cycle)
    trigger = row.get("two_vote_trigger")
    triggers = [trigger] if isinstance(trigger, str) and trigger else []
    gate = GATE.reconcile_required_gate("two_vote_required" if row.get("requires_two_vote") else None,
                                        triggers)
    family = transition_rival_family(row.get("id"))
    roles = [row.get("to_nahw_role")]
    els = (row.get("else") or {})
    if els.get("pending_reason"):
        roles.append("hold:%s" % els["pending_reason"])
    if family is None:
        # No particle family binds this transition, so the repository authorizes no rival lattice for it.
        # Preserve the blocker exactly instead of borrowing another collision's roles.
        return [{
            "axis": "nahw_role", "role": row.get("to_nahw_role"),
            "decision_status": "unresolved", "selected": False, "reason_key": None, "gate": gate,
            "evidence_id": evidence_id, "defeater": None,
            "rival_lattice": "absent",
            "blocker": ("no authorized local rival lattice: transition %r is bound by a from-state token, "
                        "not by a homograph collision, so this repository names no sibling roles for it"
                        % row.get("id")),
        }]
    # ROUND-13: only `forbidden_to` was carried, so the مَن transition listed the مَن relative role as its
    # own rival and never carried the مِن preposition sibling at all — rivalry was asymmetric. A forbidden
    # collision names BOTH ends, and each end is the other's rival.
    for forb in (rules or load_state_rules()).get("forbidden_transitions", []):
        if FORBIDDEN_COLLISION_FAMILY.get(forb.get("id")) != family:
            continue
        for end in ("forbidden_from", "forbidden_to"):
            if forb.get(end) and forb[end] not in roles:
                roles.append(forb[end])
    out = []
    for role in roles:
        if not role:
            continue
        is_selected = role == selected
        # An unselected rival is only REJECTED once evidence defeats it. Selection without a defeater
        # leaves the others standing, which is what keeps a lost rival visible.
        status = "candidate_selected" if is_selected else "unresolved"
        out.append({
            "axis": "nahw_role", "role": role,
            "decision_status": status, "selected": is_selected, "reason_key": None, "gate": gate,
            "evidence_id": evidence_id,
            "rival_lattice": "local:%s" % family,
            "defeater": None,
        })
    return out


# ROUND-7: a transition id could be applied to any surface (a self-test fired noun_noun_to_idafa on the
# unrelated demonstrative ذَٰلِكَ). Each transition now declares how its FROM-state is verified: either the
# particle consumer must resolve the caller's surface to the bound (rule, branch), or the caller must name the
# from-state token explicitly. Neither supplied => pending, never a candidate.
TRANSITION_FROM_STATE = {
    "an_light_to_masdariyyah": {"particle": ("an_vs_inna", "A"), "weight": "light"},
    "anna_heavy_to_emphatic_nasb_subject": {"particle": ("an_vs_inna", "A"), "weight": "heavy"},
    "inna_heavy_to_tawkid": {"particle": ("an_vs_inna", "B"), "weight": "heavy"},
    "in_light_to_conditional": {"particle": ("an_vs_inna", "B"), "weight": "light"},
    "man_relative_to_mubtada_or_object": {"particle": ("man_vs_min", "A")},
    "min_preposition_to_jar_majrur": {"particle": ("man_vs_min", "B")},
    "lamma_temporal_to_zarf_clause": {"particle": ("lima_vs_lamma", "A")},
    "la_indef_nasb_to_nafy_lil_jins": {"from_state": "laa_before_indefinite_nasb_noun"},
    "illa_to_istithna": {"from_state": "illa_exceptive_particle"},
    "noun_noun_to_idafa": {"from_state": "noun_followed_by_noun"},
}


def transition(transition_id, *, evidence=None, at=None, surface=None, from_state=None, rules=None):
    """Fire (or hold) a named state transition on a TYPED, SOURCE-ADDRESSED trigger observation.

    A bare boolean is rejected: transition(id, evidence=True) holds pending with
    evidence_defect="caller_label". A fired transition is a CANDIDATE role at the rule's own gate, never an
    auto-resolution.
    """
    rules = rules or load_state_rules()
    row = None
    for t in rules.get("transitions", []):
        if t.get("id") == transition_id:
            row = t
            break
    if row is None:
        return {"transition_id": transition_id, "decision": "unknown_transition", "status": "out_of_domain"}
    # FROM-STATE VERIFICATION (round-7). The caller must prove the token it is deciding really is in this
    # transition's from-state, either by supplying the written surface (which the particle consumer must resolve
    # to the bound rule/branch, and to the bound shadda weight where the ان family needs it) or by naming the
    # declared from-state token. Neither => pending.
    _fs = TRANSITION_FROM_STATE.get(transition_id) or {}
    _fs_defect = None
    if "particle" in _fs:
        if not surface:
            _fs_defect = "from_state_surface_absent"
        else:
            _res = resolve_particle_homograph(surface, rules=None)
            if (_res.get("rule_id"), _res.get("branch")) != _fs["particle"]:
                _fs_defect = "from_state_surface_mismatch"
            elif _fs.get("weight") and an_family_weight(surface) != _fs["weight"]:
                _fs_defect = "from_state_weight_mismatch"
    elif "from_state" in _fs:
        if from_state != _fs["from_state"]:
            _fs_defect = "from_state_absent" if not from_state else "from_state_mismatch"
    else:
        _fs_defect = "from_state_unmodelled"
    required = TRANSITION_TRIGGERS.get(transition_id)
    gate = "two_vote_required" if row.get("requires_two_vote") else "candidate"
    # The observation must be bound to THIS transition's from-state: an observation minted for another
    # transition (or another token) can never fire this one.
    bind = {"kind": "state", "value": transition_id}
    # ROUND-13: the caller surface was NOT passed, so an observation recorded on مَنْ could fire the مِنَ
    # preposition transition at the same address. The observation must be about the exact written word the
    # transition is being applied to.
    value, defect, art = typed_observation(evidence, TRANSITION_OBSERVATION_VOCAB, bind=bind, at=at,
                                           surface=surface)
    els = row.get("else", {}) or {}
    role = row.get("to_nahw_role")
    base = {"transition_id": transition_id, "from_observation": row.get("from_observation"),
            "required_observation": required, "to_nahw_role": role,
            "requires_two_vote": bool(row.get("requires_two_vote")),
            "two_vote_trigger": row.get("two_vote_trigger"), "gate": gate,
            "unresolved_alternatives": transition_rivals(row, rules, selected=None,
                                                         evidence_id=(art or {}).get("evidence_id")),
            "at": at, "status": "consumed"}
    base["from_state_defect"] = _fs_defect
    if _fs_defect or defect or value != required:
        base.update({"decision": els.get("decision", "pending"),
                     "pending_reason": els.get("pending_reason"), "note": els.get("note"),
                     "to_nahw_role": None, "candidate_role": role,
                     "evidence_id": None, "source_address": None,
                     "evidence_defect": defect or ("observation_does_not_match_trigger"
                                                   if not _fs_defect else None)})
        return base
    base.update({"decision": "candidate", "observed": value,
                 "unresolved_alternatives": transition_rivals(row, rules, selected=role,
                                                              evidence_id=art["evidence_id"]),
                 "evidence_id": art["evidence_id"], "source_address": art["source_address"],
                 "producer": art["producer"], "producer_trust": art["producer_trust"],
                 "reason": row.get("reason"), "confidence": row.get("confidence"),
                 "route": "nahw/procedures/irab-case-mood.md"})
    return base


# ---------------------------------------------------------------------------
# ROUND-10: a PUBLIC surface gloss must be occurrence truth, or it stays unresolved
# ---------------------------------------------------------------------------
# Two rule branches are deliberately DISJUNCTIVE: an_vs_inna A glosses "to / that" for both أَنْ and أَنَّ,
# and B glosses "indeed / verily (إِنَّ) — or — if (إِنْ)". A branch gloss is therefore not, by itself, a
# statement about one occurrence — publishing it would assert a reading the marks may not support. Where the
# shadda-borne weight separates the members, the member's OWN gloss is required; where it does not, the
# gloss stays unresolved.
#
# The member glosses below are the parenthesised attributions in the rule file's own branch-B gloss string,
# made machine-readable rather than re-derived.
AN_FAMILY_MEMBER_GLOSS = {
    ("A", "light"): ("to", "in order to", "that"),          # أَنْ maṣdariyyah / subjunctive
    ("A", "heavy"): ("that",),                              # أَنَّ emphatic complementiser
    ("B", "heavy"): ("indeed", "verily", "truly"),          # إِنَّ
    ("B", "light"): ("if",),                                # إِنْ conditional
}
# ROUND-13: مَن is one written word with three CONTEXTUAL functions — interrogative, relative and
# conditional. Vocalization separates مَن from مِن, but it does not choose among those three, and the rule
# file's own branch gloss ("who / whoever / he who") is a disjunction over them. A context-free public gloss
# must therefore abstain and keep the alternatives, exactly as the ان family does.
DISJUNCTIVE_BRANCHES = {("an_vs_inna", "A"), ("an_vs_inna", "B"), ("man_vs_min", "A")}


def _gloss_alternatives(text):
    """The rule file writes a branch gloss as slash-separated alternatives; split without inventing any."""
    out = []
    for part in re.split(r"[/|]| — or — ", text or ""):
        part = part.strip().strip(".")
        part = re.sub(r"\s*\([^)]*\)\s*", " ", part).strip()
        if part:
            out.append(part.lower())
    return out


def public_gloss_defect(surface, gloss, rules=None):
    """None only when the WRITTEN surface determines one member and `gloss` is that member's own gloss.

    Returns a closed defect string otherwise: surface_absent | gloss_absent | no_final_consumer |
    unresolved_homograph:<reason> | forbidden_reading | branch_gloss_is_disjunctive |
    gloss_not_the_resolved_member. Every one of them means "do not publish this as occurrence truth".
    """
    if not isinstance(surface, str) or not surface.strip():
        return "surface_absent"
    if not isinstance(gloss, str) or not gloss.strip():
        return "gloss_absent"
    res = resolve_particle_homograph(surface, rules=rules)
    if res.get("status") == "out_of_domain":
        return "no_final_consumer"
    if res.get("decision") != "resolved" or res.get("branch") is None:
        return "unresolved_homograph:%s" % (res.get("pending_reason") or "pending")
    if forbidden_gloss_violations(surface, gloss, particle_rules=rules):
        return "forbidden_reading"
    key = (res.get("rule_id"), res.get("branch"))
    if key in DISJUNCTIVE_BRANCHES:
        # Only the ان family has a WRITTEN disambiguator (the shadda-borne weight). For any other
        # disjunctive branch — مَن, whose three senses are interrogative, relative and conditional — the
        # written form does not choose, so a context-free gloss abstains and the alternatives are preserved.
        if res.get("rule_id") != "an_vs_inna":
            return "branch_gloss_is_disjunctive"
        weight = an_family_weight(surface)
        if weight is None:
            return "branch_gloss_is_disjunctive"
        allowed = AN_FAMILY_MEMBER_GLOSS.get((res["branch"], weight))
        if not allowed:
            return "branch_gloss_is_disjunctive"
    else:
        allowed = _gloss_alternatives(res.get("gloss"))
    offered = gloss.strip().lower().strip(".")
    if offered not in [a.lower() for a in allowed]:
        return "gloss_not_the_resolved_member"
    return None


def forbidden_gloss_violations(surface, gloss, rules=None, particle_rules=None):
    """The GAP-N3 backstop, made executable: a resolved reading may never carry its sibling's gloss.

    Keyed on the structured (rule_id, branch) binding + the rule file's own exact `forbidden_gloss` string —
    never on the `why_forbidden` prose.
    """
    if not gloss:
        return []
    rules = rules or load_state_rules()
    res = resolve_particle_homograph(surface, rules=particle_rules)
    if res.get("branch") is None:
        return []
    key = (res["rule_id"], res["branch"])
    low = gloss.lower()
    out = []
    for row in rules.get("forbidden_transitions", []):
        if FORBIDDEN_BINDINGS.get(row.get("id")) != key:
            continue
        for frag in [p.strip() for p in (row.get("forbidden_gloss") or "").split("/") if p.strip()]:
            # ROUND-7: a forbidden fragment must match on TOKEN/PHRASE boundaries. Substring matching made
            # "the day before" trip the fragment "for", and would let "from the whole group" trip "he who".
            if re.search(r"(?<!\w)%s(?!\w)" % re.escape(frag.lower()), low):
                out.append({"id": row["id"], "collision": row.get("collision"),
                            "forbidden_gloss": row.get("forbidden_gloss"),
                            "matched_fragment": frag,
                            "correct_instead": row.get("correct_instead"),
                            "why_forbidden": row.get("why_forbidden"),
                            "guard": row.get("guard"), "reason_code": row.get("reason_code"),
                            "surface": surface, "resolved_reading": res.get("reading")})
                break
    return out


# ---------------------------------------------------------------------------
# truthful status inventory (charter requirement 7)
# ---------------------------------------------------------------------------
# Authoritative FILE-level consumption status for this helper's rule files. `consumed` means a
# PRODUCTION record-validation path reads the file and a distinct on/off probe proves it (see
# tools/validate_nahw_skill.py RULES_CONSUMPTION, which asserts exact agreement with this map).
# A helper being able to READ a file is not consumption.
FILE_CONSUMPTION = {
    "nahw/rules/particle-context-rules.json": "consumed",
    "nahw/rules/negation-rules.json": "fixture_gated",
    "nahw/rules/state-transition-rules.json": "consumed",
}


def _file_status(path, executable=True):
    """A rule row can never claim more than its file's authoritative status."""
    status = FILE_CONSUMPTION.get(path, "fixture_gated")
    return status if executable else "documentary"


def rule_status():
    """Per-rule consumption status: consumed | fixture_gated | documentary | candidate_only."""
    out = {"nahw/rules/particle-context-rules.json": {}, "nahw/rules/negation-rules.json": {},
           "nahw/rules/state-transition-rules.json": {}}
    for rule in load_particle_rules().get("rules", []):
        out["nahw/rules/particle-context-rules.json"][rule["id"]] = _file_status(
            "nahw/rules/particle-context-rules.json", rule["id"] in DISCRIMINATORS)
    for row in load_negation_rules().get("rules", []):
        out["nahw/rules/negation-rules.json"][row["id"]] = _file_status(
            "nahw/rules/negation-rules.json")
    st = load_state_rules()
    for row in st.get("transitions", []):
        out["nahw/rules/state-transition-rules.json"][row["id"]] = _file_status(
            "nahw/rules/state-transition-rules.json", False)
    for row in st.get("forbidden_transitions", []):
        out["nahw/rules/state-transition-rules.json"]["forbidden:" + row["id"]] = _file_status(
            "nahw/rules/state-transition-rules.json", row.get("id") in FORBIDDEN_BINDINGS)
    return out


def _self_test():
    bad = []

    def eq(name, got, want):
        if got != want:
            bad.append("%s: got %r want %r" % (name, got, want))

    eq("مِنَ->B", resolve_particle_homograph("مِنَ")["branch"], "B")
    eq("مَن->A", resolve_particle_homograph("مَن")["branch"], "A")
    eq("bare من pending", resolve_particle_homograph("من")["decision"], "pending")
    eq("مَنَّ excluded", resolve_particle_homograph("مَنَّ")["branch"], None)
    eq("إِنَّ->B", resolve_particle_homograph("إِنَّ")["branch"], "B")
    eq("أَنَّ->A", resolve_particle_homograph("أَنَّ")["branch"], "A")
    eq("لَمَّا->A", resolve_particle_homograph("لَمَّا")["branch"], "A")
    eq("negation لَمْ", negation_effect("لَمْ")["decision"], "resolved")
    eq("negation مَا pending", negation_effect("مَا")["decision"], "pending")
    MAEV = mint_fixture_observation("negation", source_address="quran:4:157:5", quran_loc="4:157",
                                    word=5, surface="مَا", target_kind="token", target_value="maa_negation")
    eq("مَا caller label never resolves",
       negation_effect("مَا", {"maa_function": "negation"})["decision"], "pending")
    eq("مَا caller label defect",
       negation_effect("مَا", {"maa_function": "negation"})["evidence_defect"], "caller_label")
    eq("مَا address-shaped string is not evidence",
       negation_effect("مَا", {"maa_function": "quran:4:157:5"})["evidence_defect"], "caller_label")
    r = negation_effect("مَا", {"maa_function": MAEV}, at="quran:4:157:5")
    eq("مَا typed artifact -> candidate only", r["decision"], "candidate")
    eq("مَا candidate carries the evidence id", r["evidence_id"], MAEV["observation_id"])
    eq("مَا candidate carries the source address", r["source_address"], "quran:4:157:5")
    eq("مَا relative routed out of the negation path",
       negation_effect("مَا", {"maa_function": mint_fixture_observation(
           "relative", source_address="quran:4:157:5", quran_loc="4:157", word=5, surface="مَا",
           target_kind="token", target_value="maa_negation")}, at="quran:4:157:5")["decision"], "pending")
    eq("negation without a caller occurrence never becomes a candidate",
       negation_effect("مَا", {"maa_function": MAEV})["evidence_defect"], "caller_occurrence_absent")
    eq("same-surface observation replayed at another occurrence is rejected",
       negation_effect("مَا", {"maa_function": MAEV}, at="quran:2:26:20")["evidence_defect"],
       "occurrence_not_current")
    eq("impossible address rejected",
       negation_effect("مَا", {"maa_function": mint_fixture_observation(
           "negation", source_address="quran:999:999:999", quran_loc="999:999", word=999, surface="مَا",
           target_kind="token", target_value="maa_negation")}, at="quran:4:157:5")["evidence_defect"],
       "source_address_not_in_scope")
    eq("newline-suffixed address rejected",
       negation_effect("مَا", {"maa_function": dict(MAEV, source_address="quran:4:157:5\n")})[
           "evidence_defect"], "source_address_invalid")
    eq("surface-mismatched observation rejected",
       negation_effect("مَا", {"maa_function": mint_fixture_observation(
           "negation", source_address="quran:4:157:5", quran_loc="4:157", word=5, surface="لَا",
           target_kind="token", target_value="maa_negation")}, at="quran:4:157:5")["evidence_defect"], "surface_mismatch")
    eq("unrelated-target observation rejected",
       negation_effect("مَا", {"maa_function": mint_fixture_observation(
           "negation", source_address="quran:4:157:5", quran_loc="4:157", word=5, surface="مَا",
           target_kind="token", target_value="laa_context")})["evidence_defect"],
       "target_binding_mismatch")
    eq("caller-minted producer rejected",
       negation_effect("مَا", {"maa_function": mint_fixture_observation(
           "negation", source_address="quran:4:157:5", quran_loc="4:157", word=5, surface="مَا",
           target_kind="token", target_value="maa_negation", producer="me")},
                       at="quran:4:157:5")["evidence_defect"],
       "producer_not_authorized")
    eq("mutated artifact fails integrity",
       negation_effect("مَا", {"maa_function": dict(MAEV, observation="relative")},
                       at="quran:4:157:5")["evidence_defect"], "integrity_mismatch")
    eq("لَا garbage mood held",
       negation_effect("لَا", {"following_token_mood": mint_fixture_observation(
           "banana", source_address="quran:2:2:1", quran_loc="2:2", word=1, surface="لَا",
           target_kind="token", target_value="laa_context")}, at="quran:2:2:1")["evidence_defect"],
       "observation_off_vocabulary")
    eq("iḍāfa no evidence -> pending", transition("noun_noun_to_idafa")["decision"], "pending")
    eq("iḍāfa bare boolean rejected",
       transition("noun_noun_to_idafa", evidence=True)["evidence_defect"], "caller_label")
    TREV = mint_fixture_observation("second_noun_majrur_first_stripped", source_address="quran:2:2:1",
                                    quran_loc="2:2", word=1, surface="ذَٰلِكَ", target_kind="state",
                                    target_value="noun_noun_to_idafa")
    t = transition("noun_noun_to_idafa", evidence=TREV, at="quran:2:2:1",
                   from_state="noun_followed_by_noun")
    eq("iḍāfa typed evidence -> candidate only", t["decision"], "candidate")
    eq("iḍāfa candidate carries the evidence id", t["evidence_id"], TREV["observation_id"])
    eq("iḍāfa rivals are structured objects", all(isinstance(x, dict) and "role" in x
                                                  for x in t["unresolved_alternatives"]), True)
    eq("iḍāfa observation cannot fire another transition",
       transition("illa_to_istithna", evidence=TREV, at="quran:2:2:1",
                  from_state="illa_exceptive_particle")["evidence_defect"], "target_binding_mismatch")
    # ROUND-7 from-state binding: a transition may not be applied without proving the current from-state
    eq("transition without a from-state is pending",
       transition("noun_noun_to_idafa", evidence=TREV, at="quran:2:2:1")["from_state_defect"],
       "from_state_absent")
    eq("transition with the wrong from-state is pending",
       transition("noun_noun_to_idafa", evidence=TREV, at="quran:2:2:1",
                  from_state="illa_exceptive_particle")["from_state_defect"], "from_state_mismatch")
    eq("a particle-bound transition needs the written surface",
       transition("min_preposition_to_jar_majrur")["from_state_defect"], "from_state_surface_absent")
    eq("a particle-bound transition rejects an unrelated surface",
       transition("min_preposition_to_jar_majrur", surface="ذَٰلِكَ")["from_state_defect"],
       "from_state_surface_mismatch")
    eq("the ان family transition checks the shadda weight",
       transition("inna_heavy_to_tawkid", surface="إِنْ")["from_state_defect"],
       "from_state_weight_mismatch")
    # ROUND-7 semantic safety: form/context false passes
    eq("لِمَ never falls through to the negation row",
       negation_effect("لِمَ")["decision"], "pending")
    eq("لَمْ still resolves", negation_effect("لَمْ")["decision"], "resolved")
    eq("shadda separates light from heavy in the ان family",
       [an_family_weight(x) for x in ("أَنْ", "أَنَّ",
                                      "إِنْ", "إِنَّ")],
       ["light", "heavy", "light", "heavy"])
    eq("a forbidden fragment does not match inside a longer word",
       forbidden_gloss_violations("لَمَّا", "the day before"), [])
    eq("a forbidden phrase does not match across token boundaries",
       forbidden_gloss_violations("مَن", "from the whole group"), [])
    eq("transition without a caller occurrence never becomes a candidate",
       transition("noun_noun_to_idafa", evidence=TREV)["evidence_defect"], "caller_occurrence_absent")
    eq("transition observation replayed at another occurrence is rejected",
       transition("noun_noun_to_idafa", evidence=TREV, at="quran:2:26:20")["evidence_defect"],
       "occurrence_not_current")
    eq("a malformed caller occurrence is rejected",
       transition("noun_noun_to_idafa", evidence=TREV, at="2:2:1")["evidence_defect"],
       "caller_occurrence_invalid")
    eq("iḍāfa heuristic evidence rejected",
       transition("noun_noun_to_idafa",
                  evidence=dict(TREV, evidence_class="heuristic"), at="quran:2:2:1")["evidence_defect"],
       "evidence_class_not_source_addressed")
    eq("forbidden مِن/whoever", bool(forbidden_gloss_violations("مِنَ", "and whoever")), True)
    eq("licit مِن/from", forbidden_gloss_violations("مِنَ", "from / among"), [])
    # every rule in every consumed file must have a truthful status
    for path, rows in rule_status().items():
        for rid, st in rows.items():
            if st not in ("consumed", "fixture_gated", "documentary", "candidate_only"):
                bad.append("%s#%s: untruthful status %r" % (path, rid, st))
    if bad:
        print("FAIL — fusha_nahw_particle_rules self-test:")
        for b in bad:
            print("  -", b)
        return 1
    print("PASS — particle/negation/state-transition consumer self-test "
          "(7 homograph rules consumed, 5 negation rules, 10 transitions, 5 forbidden bindings)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true", help="print the per-rule consumption inventory")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--resolve", help="resolve a single surface")
    a = ap.parse_args()
    if a.status:
        print(json.dumps(rule_status(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if a.resolve:
        print(json.dumps(resolve_particle_homograph(a.resolve), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return _self_test()


if __name__ == "__main__":
    sys.exit(main())
