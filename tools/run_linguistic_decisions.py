#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F12 — runner: apply sarf+nahw rules to enriched candidate tokens, emit linguistic-decision JSONL.

Loads three inputs, applies a rule set, and writes one linguistic-decision record per candidate token
(schema: qamus/schemas/linguistic-decision.schema.json). It is the DRY-RUN brain that turns a batch of
pending hover tokens into authored_gloss | pending | quarantine | repair_candidate decisions, with the
sarf/nahw reasoning attached for a human reviewer. NOTHING here is live: no network, no writes outside the
chosen --out file, never a publish.

Inputs
------
  --index    qamus/indexes/existing_qamus_index.json
             The 2,092-entry de-dup ground truth, a dict keyed by source-address
             (qamus:v###/n###/p###). Used to confirm a root/POS the candidate claims and to find a
             same-key homograph quarantine (e.g. ٱلْمُلْك "dominion" must not borrow مَلَك "angel").
  --candidates  an enriched candidate JSON (list, or {"tokens":[...]} / {"candidates":[...]}). Each token:
             {norm_strict, surface, qac_root, qac_pos, ayah, qamus_glosses[]} plus optional
             {loc, nearby_tokens, referent}. `ayah` carries the surrounding āyah text (for the nahw
             context rules); `qamus_glosses` is the candidate gloss list the hover layer would offer.
  --rules    the sarf/nahw rule JSON (see DEFAULT_RULES for the shape + the live regression set). Declares
             the homograph, POS-guard, same-root-polyseme, referent-guard, and tanwīn-alef rules. If
             omitted, the built-in DEFAULT_RULES (which encode the real qamus-highlight fixes) are used.

Output
------
  A JSONL stream of linguistic-decision objects. Each is authored_gloss | pending | quarantine |
  repair_candidate, carrying source_address, surface, root/POS evidence, the sarf reason, the nahw reason
  when the call was context-sensitive, a confidence, INTERNAL provenance, public_export_allowed (true only
  for a clean authored_gloss), and review_status=needs_human_review. `--out -` writes to stdout.

Doctrine (encoded, not invented — these are the qamus-highlight facts)
---------------------------------------------------------------------
  * Diacritic homographs are decided on the CONTENT letter's harakah, which may sit after a و/ف proclitic:
    مَن(fatḥa 'who') ≠ مِن(kasra 'from', incl. وَمِنَ); لِمَا ≠ لَمَّا(shadda on mīm); كُلّ(ḍamma) ≠ كَلَّا(fatḥa);
    نِعْمَ(kasra) ≠ نَعَمْ; أَنِّي(kasra) ≠ أَنَّى; لَمْ ≠ لِمَ. Read the content letter, never the first letter.
  * POS guard: no "to …" verb gloss on a QAC noun/proper-noun (رَسُولًا ≠ 'to send'; ٱبْن/بَنَات ≠ 'to build').
  * Same-root polyseme quarantine: ٱلْمُلْك ≠ 'angels'; أَنْهَٰر ≠ 'daytime'; ٱلْإِسْلَٰم ≠ 'peace';
    عِنْد ≠ 'stubborn'; تَحْرِير ≠ 'heat'; ثالث ≠ 'three'.
  * Referent guard: حَلِيمٌ for Ibrāhīm = 'forbearing', not a divine Name; صَٰلِحًا ≠ the Prophet Ṣāliḥ.
  * tanwīn-alef is not a نا suffix (قُرْءَانًا).
  * Prefer PENDING over a wrong gloss. A blank is recoverable; a confident scripture error is not.

stdlib only. Run the self-test:  python tools/run_linguistic_decisions.py --fixture
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tools.normalize_ar import (  # noqa: E402  (single shared module — never re-implement)
    norm, norm_strict, bare, haraka_on, shadda_on, is_man_who, ends_tanwin_alef,
    KASRA, FATHA, DAMMA,
)

# ---------------------------------------------------------------------------
# DEFAULT rule set. A --rules file may override/extend any list. Every datum
# here is a REGRESSION the qamus-highlight pass actually hit — facts to capture,
# not text to invent. No external gloss is embedded; the "wrong" strings are the
# bad glosses we REFUSE, the "gloss" strings are short authored corrections.
# ---------------------------------------------------------------------------
DEFAULT_RULES = {
    "ruleset_version": "fusha-lingrules/1",
    # Diacritic-sensitive function words. Each gives the content letter to read and
    # the harakah that selects each reading; the runner uses the shared harakāt
    # helpers (never the first letter) so a و/ف proclitic cannot fool it.
    "homographs": [
        {
            "id": "man_vs_min", "family_norm": "من", "content_letter": "م",
            "readings": [
                {"when": "is_man_who", "gloss": "who / whoever", "lemma": "مَن", "pos": "particle"},
                {"when": "kasra", "gloss": "from / among", "lemma": "مِن", "pos": "particle"},
            ],
            "refuse": ["from"], "note": "مَن(fatḥa) vs مِن(kasra, incl. وَمِنَ)",
        },
        {
            "id": "lam_vs_lima", "family_norm": "لم", "content_letter": "ل",
            "readings": [
                {"when": "kasra", "gloss": "why", "lemma": "لِمَ", "pos": "particle"},
                {"when": "not_kasra", "gloss": "(did) not", "lemma": "لَمْ", "pos": "particle"},
            ],
            "refuse": [], "note": "لَمْ vs لِمَ — kasra on the lām selects 'why'",
        },
        {
            "id": "lima_vs_lamma", "family_norm": "لما", "content_letter": "م",
            "readings": [
                {"when": "shadda", "gloss": "when", "lemma": "لَمَّا", "pos": "particle"},
                {"when": "no_shadda", "gloss": "for / that which", "lemma": "لِمَا", "pos": "particle"},
            ],
            "refuse": [], "note": "لَمَّا(shadda on mīm) vs لِمَا",
        },
        {
            "id": "kull_vs_kalla", "family_norm": "كلا", "content_letter": "ك",
            "readings": [
                {"when": "damma", "gloss": "all / each", "lemma": "كُلّ", "pos": "noun"},
                {"when": "fatha", "gloss": "nay / but no", "lemma": "كَلَّا", "pos": "particle"},
            ],
            "refuse": [], "note": "كُلّ(ḍamma) vs كَلَّا(fatḥa) on the kāf",
        },
        {
            "id": "nima_vs_naam", "family_norm": "نعم", "content_letter": "ن",
            "readings": [
                {"when": "kasra", "gloss": "how excellent / what a good", "lemma": "نِعْمَ", "pos": "verb"},
                {"when": "fatha", "gloss": "yes", "lemma": "نَعَمْ", "pos": "particle"},
            ],
            "refuse": [], "note": "نِعْمَ(kasra) vs نَعَمْ(fatḥa)",
        },
        {
            "id": "anni_vs_anna", "family_norm": "اني", "content_letter": "ن",
            "readings": [
                {"when": "kasra", "gloss": "that I", "lemma": "أَنِّي", "pos": "particle"},
                {"when": "fatha", "gloss": "how / whence", "lemma": "أَنَّى", "pos": "particle"},
            ],
            "refuse": [], "note": "أَنِّي(kasra) vs أَنَّى(fatḥa)",
        },
    ],
    # POS guard: a "to …" verb gloss is forbidden on a QAC noun / proper noun.
    "pos_guard": {
        "verb_gloss_prefixes": ["to "],
        "noun_pos_tags": ["N", "PN", "ADJ", "noun", "proper_noun", "adjective"],
        "examples": ["رَسُولًا≠'to send'", "ٱبْن/بَنَات≠'to build'"],
    },
    # Same-root polysemes: a tempting cousin meaning that must be QUARANTINED (not
    # auto-glossed) because it belongs to a different lemma on the same skeleton.
    "polyseme_quarantine": [
        {"surface_norm": "الملك", "forbid": ["angels", "angel"], "correct": "sovereignty / dominion",
         "note": "مُلْك ≠ مَلَك"},
        {"surface_norm": "انهار", "forbid": ["daytime"], "correct": "rivers", "note": "نَهْر ≠ نَهَار"},
        {"surface_norm": "الاسلام", "forbid": ["peace"], "correct": "submission / Islām",
         "note": "إِسْلَام (root س ل م) ≠ the bare 'peace' sense"},
        {"surface_norm": "عند", "forbid": ["stubborn", "obstinate"], "correct": "with / at / in the sight of",
         "note": "عِنْد (preposition) ≠ عَنِيد 'stubborn'"},
        {"surface_norm": "تحرير", "forbid": ["heat"], "correct": "freeing (manumission)",
         "note": "تَحْرِير (maṣdar ḥarrara) ≠ حَرّ 'heat'"},
        {"surface_norm": "ثالث", "forbid": ["three"], "correct": "third", "note": "ثالِث (ordinal) ≠ ثَلاث 'three'"},
    ],
    # Referent guard: a gloss that depends on WHO the verse is about.
    "referent_guard": [
        {"surface_norm": "حليم", "forbid_when_referent_not": "Allah",
         "forbid": ["one of Allah's Names", "divine name"], "correct": "forbearing",
         "note": "حَلِيمٌ of Ibrāhīm is a human attribute, not a Name"},
        {"surface_norm": "صالحا", "forbid": ["Prophet Salih", "the prophet salih"],
         "correct": "righteous (deed)", "note": "صَٰلِحًا descriptive ≠ the proper name unless context supports it"},
    ],
    # tanwīn-alef is not a نا pronoun suffix.
    "tanwin_alef_not_suffix": True,
}


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_index(path):
    if not path or not os.path.exists(path):
        return {}
    return json.load(io.open(path, encoding="utf-8"))


def load_rules(path):
    if not path:
        return json.loads(json.dumps(DEFAULT_RULES))  # deep copy
    return json.load(io.open(path, encoding="utf-8"))


def load_candidates(path):
    data = json.load(io.open(path, encoding="utf-8"))
    if isinstance(data, list):
        return data
    for key in ("tokens", "candidates", "items"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError("candidate file must be a JSON list or {tokens|candidates|items:[...]}")


def index_by_norm_strict(index):
    """Map norm_strict(surface) and norm_strict(form) -> list of source-address keys."""
    by = {}
    for addr, rec in index.items():
        keys = [rec.get("norm_strict")] + [norm_strict(f) for f in (rec.get("forms") or [])]
        for k in keys:
            if k:
                by.setdefault(k, [])
                if addr not in by[k]:
                    by[k].append(addr)
    return by


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def quran_loc_to_address(loc):
    """'2:62:8' -> 'quran:2:62:8'. Accepts an already-prefixed address unchanged."""
    if not loc:
        return None
    loc = str(loc).strip()
    if loc.startswith("quran:"):
        return loc
    return "quran:" + loc


def _harakah_match(when, tok, content_letter):
    """Evaluate a homograph reading guard against the token's harakāt (content-letter aware)."""
    if when == "is_man_who":
        return is_man_who(tok)
    if when == "kasra":
        return haraka_on(tok, content_letter) == KASRA
    if when == "not_kasra":
        return haraka_on(tok, content_letter) != KASRA
    if when == "fatha":
        return haraka_on(tok, content_letter) == FATHA
    if when == "damma":
        return haraka_on(tok, content_letter) == DAMMA
    if when == "shadda":
        return shadda_on(tok, content_letter)
    if when == "no_shadda":
        return not shadda_on(tok, content_letter)
    return False


def _gloss_in(needle_list, glosses):
    """Case-insensitive membership of any forbidden gloss inside the candidate gloss list."""
    low = [(g or "").strip().lower() for g in (glosses or [])]
    return [n for n in (needle_list or []) if (n or "").strip().lower() in low]


# leading proclitics that ride on a content word: و/ف (conj), لَ (emphatic), بـ/كـ/لـ (prep), ال (article)
def _norm_variants(surface):
    """The norm key plus proclitic-stripped variants, so a rule keyed on the bare content word
    (e.g. 'حليم', 'الملك') still matches a surface that carries وَ/فَ/لَ/بِـ/كَـ/لِـ or the article."""
    n = norm(surface)
    variants = {n}
    rest = n
    # peel single-letter proclitics, then the definite article, in any order
    changed = True
    while changed and len(rest) > 2:
        changed = False
        for pre in ("و", "ف", "ل", "ب", "ك"):
            if rest.startswith(pre) and len(rest) > 2:
                rest = rest[1:]
                variants.add(rest)
                changed = True
                break
        if rest.startswith("ال") and len(rest) > 3:
            rest = rest[2:]
            variants.add(rest)
            changed = True
    return variants


def _rule_matches_surface(rule_norm, surface):
    """True if the rule's content-word norm matches the surface directly OR after peeling proclitics."""
    return rule_norm in _norm_variants(surface)


# ---------------------------------------------------------------------------
# the decision engine
# ---------------------------------------------------------------------------
def decide(token, rules, index, by_ns, idx):
    """Return a single linguistic-decision dict for one enriched candidate token."""
    surface = token.get("surface") or token.get("surface_ar") or ""
    ns = token.get("norm_strict") or norm_strict(surface)
    n = norm(surface)
    qac_root = (token.get("qac_root") or "").strip()
    qac_pos = (token.get("qac_pos") or "").strip()
    ayah = token.get("ayah") or ""
    glosses = token.get("qamus_glosses") or []
    referent = token.get("referent")
    nearby = token.get("nearby_tokens") or ([w for w in str(ayah).split() if w] if ayah else [])
    loc = token.get("loc")
    address = quran_loc_to_address(loc) or ("wbw:" + ns)

    sarf = {"risk_flags": []}
    nahw = {}
    if nearby:
        nahw["nearby_tokens"] = nearby[:8]

    decision = {"type": "pending", "gloss_en_authored": None,
                "pending_reason": "source_evidence_needed", "confidence": "low"}
    public_export = False
    root_ar = qac_root or None
    pos = _qac_pos_to_enum(qac_pos)
    sarf_reason = ""
    nahw_reason = ""

    # ---- 1. tanwīn-alef is not a نا suffix -------------------------------
    if rules.get("tanwin_alef_not_suffix", True) and ends_tanwin_alef(surface):
        sarf["risk_flags"].append("tanwin_alef")
        sarf_reason = ("final alef is ʾalif al-tanwīn (ـًا), not the pronoun نا — do not decompose")

    # ---- 2. diacritic homographs (content-letter harakah) ----------------
    # Match the homograph family on the norm key WITH any leading و/ف proclitic stripped,
    # so وَمِنَ (norm "ومن") still resolves to the من family. The harakāt helpers then read
    # the CONTENT letter — which sits after the proclitic — never the first letter.
    n_deproclitic = n[1:] if n[:1] in ("و", "ف") and len(n) > 1 else n
    for hg in rules.get("homographs", []):
        if n != hg.get("family_norm") and n_deproclitic != hg.get("family_norm"):
            continue
        sarf["risk_flags"].append("hamza_sensitive")
        cl = hg.get("content_letter")
        chosen = None
        for reading in hg.get("readings", []):
            if _harakah_match(reading.get("when"), surface, cl):
                chosen = reading
                break
        nahw["context_rule"] = "content_letter_harakah:" + hg.get("id", "")
        if chosen:
            pos = _qac_pos_to_enum(chosen.get("pos")) or pos
            root_ar = None  # function words are rootless
            sarf_reason = ("harakah on the content letter %s selects %s (%s); read the content "
                           "letter, not the first — %s" % (cl, chosen.get("lemma"), chosen.get("gloss"),
                                                           hg.get("note", "")))
            nahw_reason = "disambiguated by the harakāt cluster on %s within %r" % (cl, ayah or surface)
            # If the candidate gloss list offers the REFUSED reading, this is a repair candidate.
            bad = _gloss_in(hg.get("refuse"), glosses)
            if bad:
                return _mk(idx, address, surface, root_ar, None, pos, sarf, nahw,
                           dict(type="repair_candidate", gloss_en_authored=chosen.get("gloss"),
                                pending_reason="hamza_sensitive_homograph", confidence="high"),
                           sarf_reason, nahw_reason, token, public_export=False)
            return _mk(idx, address, surface, root_ar, None, pos, sarf, nahw,
                       dict(type="authored_gloss", gloss_en_authored=chosen.get("gloss"),
                            pending_reason=None, confidence="high"),
                       sarf_reason, nahw_reason, token, public_export=True)
        # ambiguous harakāt — cannot read the content letter confidently
        sarf_reason = "homograph %s but the content-letter harakah is unreadable; PENDING" % hg.get("id")
        return _mk(idx, address, surface, None, None, pos, sarf, nahw,
                   dict(type="pending", gloss_en_authored=None,
                        pending_reason="hamza_sensitive_homograph", confidence="low"),
                   sarf_reason, nahw_reason, token, public_export=False)

    # ---- 3. POS guard: no verb gloss on a noun/proper-noun ---------------
    pg = rules.get("pos_guard", {})
    noun_tags = set(t.lower() for t in pg.get("noun_pos_tags", []))
    verb_prefixes = pg.get("verb_gloss_prefixes", ["to "])
    if qac_pos and qac_pos.lower() in noun_tags:
        sarf["risk_flags"].append("verb_on_noun_risk")
        offending = [g for g in glosses
                     if any((g or "").strip().lower().startswith(p) for p in verb_prefixes)]
        if offending:
            sarf_reason = ("QAC POS is %s (a noun/name): a 'to …' verb gloss %r is wrong (e.g. %s)"
                           % (qac_pos, offending, ", ".join(pg.get("examples", []))))
            return _mk(idx, address, surface, root_ar, _lemma(token), pos, sarf, nahw,
                       dict(type="quarantine", gloss_en_authored=None,
                            pending_reason="pos_mismatch", confidence="high"),
                       sarf_reason, nahw_reason, token, public_export=False)

    # ---- 4. referent guard ----------------------------------------------
    for rg in rules.get("referent_guard", []):
        if not _rule_matches_surface(rg.get("surface_norm"), surface):
            continue
        forbidden = _gloss_in(rg.get("forbid"), glosses)
        need_ref = rg.get("forbid_when_referent_not")
        triggered = bool(forbidden) and (need_ref is None or (referent != need_ref))
        if triggered:
            sarf["risk_flags"].append("sense_selection_required")
            nahw["context_rule"] = "referent_guard"
            sarf_reason = "referent-sensitive sense; %s" % rg.get("note", "")
            nahw_reason = ("the verse referent (%s) forbids %r; authored sense is %r"
                           % (referent or "unspecified", forbidden, rg.get("correct")))
            return _mk(idx, address, surface, root_ar, _lemma(token), pos, sarf, nahw,
                       dict(type="repair_candidate", gloss_en_authored=rg.get("correct"),
                            pending_reason="context_sensitive_needs_nahw", confidence="medium"),
                       sarf_reason, nahw_reason, token, public_export=False)

    # ---- 5. same-root polyseme quarantine -------------------------------
    for pq in rules.get("polyseme_quarantine", []):
        if not _rule_matches_surface(pq.get("surface_norm"), surface):
            continue
        forbidden = _gloss_in(pq.get("forbid"), glosses)
        if forbidden:
            sarf["risk_flags"].append("multi_sense_root")
            sarf_reason = "same-root polyseme: %s — refuse %r, author %r" % (
                pq.get("note", ""), forbidden, pq.get("correct"))
            return _mk(idx, address, surface, root_ar, _lemma(token), pos, sarf, nahw,
                       dict(type="repair_candidate", gloss_en_authored=pq.get("correct"),
                            pending_reason="multi_sense_root", confidence="medium"),
                       sarf_reason, nahw_reason, token, public_export=False)

    # ---- 6. clean single-gloss authored case ----------------------------
    confirmed_addrs = by_ns.get(ns, [])
    if len(glosses) == 1 and glosses[0] and confirmed_addrs:
        rec = index.get(confirmed_addrs[0], {})
        root_ar = root_ar or (rec.get("root") or None)
        pos = pos or _section_to_pos(rec.get("section"))
        sarf_reason = sarf_reason or ("single authored sense; norm_strict matches Qamus entry %s"
                                      % confirmed_addrs[0])
        return _mk(idx, confirmed_addrs[0], surface, root_ar, _lemma(token), pos, sarf, nahw,
                   dict(type="authored_gloss", gloss_en_authored=glosses[0],
                        pending_reason=None, confidence="high"),
                   sarf_reason, nahw_reason, token, public_export=True,
                   matched_entry=confirmed_addrs[0])

    # ---- 7. default: PENDING (prefer a blank to a wrong gloss) -----------
    if len(glosses) > 1:
        decision = dict(type="pending", gloss_en_authored=None,
                        pending_reason="multi_sense_root", confidence="low")
        sarf_reason = sarf_reason or "multiple candidate glosses, none disambiguated — PENDING"
        sarf["risk_flags"].append("sense_selection_required")
    elif not confirmed_addrs:
        decision = dict(type="pending", gloss_en_authored=None,
                        pending_reason="source_evidence_needed", confidence="low")
        sarf_reason = sarf_reason or "no Qamus norm_strict match; needs source evidence — PENDING"
    return _mk(idx, address, surface, root_ar, _lemma(token), pos, sarf, nahw,
               decision, sarf_reason, nahw_reason, token, public_export=public_export)


_NEVER_T = {"norm_only_match", "ocr_only_evidence", "external_gloss_copied", "reasoning_path_wrong", "qac_pos_conflict"}
_HUMAN_T = {"ambiguous_grammar", "source_corpus_conflict", "suspected_qamus_entry_error", "proper_vs_common_noun", "quran_ref_uncertain"}
_TWOVOTE_T = {"irab", "case_or_mood", "istithna", "nafy_lil_jins", "idafa_ambiguous", "jar_majrur_ambiguous",
              "multi_sense_root", "referent_sensitive_gloss", "advanced_nahw", "depth_deep", "format_essay",
              "bloom_analysis_or_higher"}


def _required_gate(triggers):
    """GP0 gate (mirrors validate_linguistic_decisions / grammar-decision-gates.json)."""
    t = set(triggers or [])
    if t & _NEVER_T:
        return "never_auto_resolve"
    if t & _HUMAN_T:
        return "human_source_review_required"
    if t & _TWOVOTE_T:
        return "two_vote_required"
    return "auto_safe"


def _triggers_from(sarf, nahw, decision):
    """Derive GP0 grammar_triggers from the sarf/nahw evidence on this decision."""
    t = []
    rf = set(sarf.get("risk_flags") or [])
    if "multi_sense_root" in rf or "sense_selection_required" in rf:
        t.append("multi_sense_root")
    if (nahw.get("context_rule") or "").startswith("referent_guard"):
        t.append("referent_sensitive_gloss")
    if decision.get("type") == "quarantine" and decision.get("pending_reason") == "pos_mismatch":
        t.append("reasoning_path_wrong")
    return sorted(set(t))


def _lemma(token):
    return token.get("lemma") or token.get("lemma_ar") or None


def _qac_pos_to_enum(tag):
    if not tag:
        return "unknown"
    t = tag.strip().lower()
    return {
        "n": "noun", "noun": "noun", "pn": "proper_noun", "proper_noun": "proper_noun",
        "v": "verb", "verb": "verb", "adj": "adjective", "adjective": "adjective",
        "particle": "particle", "p": "particle", "masdar": "masdar", "participle": "participle",
    }.get(t, "unknown")


def _section_to_pos(section):
    return {"verb": "verb", "noun": "noun", "particle": "particle"}.get((section or "").lower(), "unknown")


def _mk(idx, address, surface, root_ar, lemma_ar, pos, sarf, nahw, decision,
        sarf_reason, nahw_reason, token, public_export, matched_entry=None):
    """Assemble one schema-valid linguistic-decision object."""
    # de-dupe risk_flags, drop the empty sarf object key if nothing useful
    sarf = dict(sarf)
    sarf["risk_flags"] = sorted(set(sarf.get("risk_flags") or []))
    prov = {
        "qamus_entries": [matched_entry] if matched_entry else [],
        "qac": bool(token.get("qac_root") or token.get("qac_pos")),
        "quran_text_verified": bool(token.get("ayah")),
        "external_informed_by": _internal_informed_by(token),
    }
    # Optional INTERNAL Tafsir MCP evidence (a build-tool witness; never public, never a skill dependency).
    mcp_ev = token.get("mcp") or token.get("mcp_evidence")
    if mcp_ev:
        prov["mcp"] = mcp_ev
        prov["external_informed_by"] = sorted(set((prov.get("external_informed_by") or []) + ["tafsir-mcp"]))
    rec = {
        "decision_id": "lingdec-%06d" % idx,
        "source_address": address,
        "surface_ar": surface,
        "root_ar": root_ar,
        "lemma_ar": lemma_ar,
        "pos": pos or "unknown",
        "sarf": sarf,
        "nahw": nahw,
        "decision": {
            "type": decision["type"],
            "gloss_en_authored": decision.get("gloss_en_authored"),
            "pending_reason": decision.get("pending_reason"),
            "confidence": decision.get("confidence", "low"),
        },
        "internal_provenance": prov,
        "mcp_used": bool(mcp_ev),
        # public export is allowed ONLY for a clean authored_gloss with a gloss present
        "public_export_allowed": bool(public_export and decision["type"] == "authored_gloss"
                                      and decision.get("gloss_en_authored")),
        "review_status": "needs_human_review",
        # sarf/nahw reasons live in nahw.context_rule + an internal note carried OUT-OF-BAND
        # of the public surface; they are kept on the decision via the schema's nahw/sarf objects.
    }
    if sarf_reason:
        rec["sarf"]["reason"] = sarf_reason
    if nahw_reason:
        rec["nahw"]["reason"] = nahw_reason
    # GP0 gate stamping: triggers -> required gate; reasoning carries the iʿrāb/morphology reason
    triggers = _triggers_from(rec["sarf"], rec["nahw"], rec["decision"])
    rec["grammar_triggers"] = triggers
    rec["gate"] = _required_gate(triggers)
    rec["reasoning"] = sarf_reason or nahw_reason or None
    return rec


def _internal_informed_by(token):
    """INTERNAL provenance labels only. Never copied to a public record. We name evidence we
    consulted (qac, the verbatim āyah text) — we never embed external gloss text."""
    labels = []
    if token.get("qac_root") or token.get("qac_pos"):
        labels.append("qac")
    if token.get("ayah"):
        labels.append("quran-text")
    return labels


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def run(candidates, rules, index, start_id=1):
    by_ns = index_by_norm_strict(index)
    out = []
    idx = start_id
    for token in candidates:
        out.append(decide(token, rules, index, by_ns, idx))
        idx += 1
    return out


def _write(records, out_path):
    if out_path == "-":
        for r in records:
            sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
        return
    with io.open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# --fixture self-test (tiny inline example; no external files needed)
# ---------------------------------------------------------------------------
def _fixture():
    index = {
        "qamus:v044#root=س م ع": {
            "source_address": "qamus:v044#root=س م ع", "surface_ar": "سَمِعَ",
            "norm_strict": "سمع", "root": "س م ع", "section": "verb",
            "forms": ["سَمِعُوا"], "glosses": ["to hear"],
        },
    }
    candidates = [
        # 1. مَن 'who' — fatḥa on mīm, refused gloss 'from' present -> repair_candidate, who/whoever
        {"norm_strict": "من", "surface": "مَنْ", "qac_root": "", "qac_pos": "particle",
         "ayah": "مَنْ ءَامَنَ", "qamus_glosses": ["from", "whoever"], "loc": "2:62:8"},
        # 2. وَمِنَ 'and from' — kasra on mīm under و proclitic; refused 'and whoever' absent -> authored 'from / among'
        {"norm_strict": "ومن", "surface": "وَمِنَ", "qac_root": "", "qac_pos": "particle",
         "ayah": "وَمِنَ ٱلنَّاسِ", "qamus_glosses": ["from / among"], "loc": "2:8:1"},
        # 3. رَسُولًا is a noun (QAC N) but a 'to send' verb gloss is offered -> quarantine (pos_mismatch)
        {"norm_strict": "رسولا", "surface": "رَسُولًا", "qac_root": "ر س ل", "qac_pos": "N",
         "ayah": "رَّسُولًۭا يَتْلُوا", "qamus_glosses": ["to send", "a messenger"], "loc": "65:11:3"},
        # 4. ٱلْمُلْك polyseme: 'angels' is the cousin مَلَك sense -> repair to 'sovereignty / dominion'
        {"norm_strict": "الملك", "surface": "ٱلْمُلْكَ", "qac_root": "م ل ك", "qac_pos": "N",
         "ayah": "وَءَاتَىٰهُ ٱللَّهُ ٱلْمُلْكَ", "qamus_glosses": ["angels", "sovereignty"], "loc": "2:251:9"},
        # 5. حَلِيمٌ referent is Ibrāhīm, not Allah -> repair to 'forbearing'
        {"norm_strict": "حليم", "surface": "لَحَلِيمٌ", "qac_root": "ح ل م", "qac_pos": "ADJ",
         "ayah": "إِنَّ إِبْرَٰهِيمَ لَحَلِيمٌ", "qamus_glosses": ["one of Allah's Names", "forbearing"],
         "referent": "Ibrahim", "loc": "11:75:3"},
        # 6. clean single authored sense that matches the index by norm_strict -> authored_gloss, exportable
        {"norm_strict": "سمع", "surface": "سَمِعَ", "qac_root": "س م ع", "qac_pos": "V",
         "ayah": "سَمِعَ ٱللَّهُ", "qamus_glosses": ["to hear"], "loc": "58:1:1"},
        # 7. قُرْءَانًا — tanwīn-alef, multi-gloss -> pending, tanwin_alef risk flagged
        {"norm_strict": "قرءانا", "surface": "قُرْءَانًا", "qac_root": "ق ر ا", "qac_pos": "N",
         "ayah": "إِنَّا جَعَلْنَٰهُ قُرْءَٰنًا عَرَبِيًّۭا", "qamus_glosses": ["a recitation", "a Qur'an"], "loc": "12:2:4"},
    ]
    records = run(candidates, DEFAULT_RULES, index)
    by_addr = {r["source_address"]: r for r in records}

    def g(addr):
        return by_addr[addr]

    # 1. مَن -> repair_candidate, who, never collapses to 'from'
    r1 = records[0]
    assert r1["decision"]["type"] == "repair_candidate", r1["decision"]
    assert "who" in (r1["decision"]["gloss_en_authored"] or ""), r1
    assert r1["public_export_allowed"] is False
    # 2. وَمِنَ -> authored 'from / among', NOT 'and whoever'
    r2 = records[1]
    assert r2["decision"]["type"] == "authored_gloss", r2["decision"]
    assert "from" in r2["decision"]["gloss_en_authored"], r2
    assert "who" not in r2["decision"]["gloss_en_authored"].lower(), "وَمِنَ must not gloss as 'whoever'"
    assert r2["public_export_allowed"] is True
    # 3. رَسُولًا -> quarantine, no 'to …' gloss survives
    r3 = records[2]
    assert r3["decision"]["type"] == "quarantine" and r3["decision"]["gloss_en_authored"] is None, r3
    assert "verb_on_noun_risk" in r3["sarf"]["risk_flags"], r3["sarf"]
    # 4. ٱلْمُلْك -> repair, never 'angels'
    r4 = records[3]
    assert r4["decision"]["type"] == "repair_candidate", r4
    assert "angel" not in (r4["decision"]["gloss_en_authored"] or "").lower(), r4
    assert "dominion" in r4["decision"]["gloss_en_authored"], r4
    # 5. حَلِيمٌ -> repair, 'forbearing', referent guard fired
    r5 = records[4]
    assert r5["decision"]["type"] == "repair_candidate", r5
    assert r5["decision"]["gloss_en_authored"] == "forbearing", r5
    # 6. سَمِعَ -> clean authored_gloss, exportable, matched the index entry
    r6 = records[5]
    assert r6["decision"]["type"] == "authored_gloss" and r6["public_export_allowed"] is True, r6
    assert r6["source_address"] == "qamus:v044#root=س م ع", r6["source_address"]
    # 7. قُرْءَانًا -> pending, tanwin_alef flagged, not decomposed
    r7 = records[6]
    assert r7["decision"]["type"] == "pending", r7
    assert "tanwin_alef" in r7["sarf"]["risk_flags"], r7["sarf"]
    # global invariant: no public-exportable record carries internal provenance in a public field
    for r in records:
        if r["public_export_allowed"]:
            blob = json.dumps(r["decision"], ensure_ascii=False).lower()
            assert "qac" not in blob and "informed_by" not in blob and "tanzil" not in blob, r
    # every record validates against the in-tree schema shape (required keys + enum)
    for r in records:
        for k in ("decision_id", "source_address", "surface_ar", "decision"):
            assert k in r, ("missing %s" % k, r)
        assert r["decision"]["type"] in ("authored_gloss", "pending", "quarantine", "repair_candidate")
    print("run_linguistic_decisions fixture OK — %d decisions "
          "(%d authored, %d pending, %d quarantine, %d repair); "
          "مَن/مِن never collapsed, no 'to …' on a noun, مُلْك≠angels, حَلِيم=forbearing" % (
              len(records),
              sum(1 for r in records if r["decision"]["type"] == "authored_gloss"),
              sum(1 for r in records if r["decision"]["type"] == "pending"),
              sum(1 for r in records if r["decision"]["type"] == "quarantine"),
              sum(1 for r in records if r["decision"]["type"] == "repair_candidate"),
          ))


def main():
    ap = argparse.ArgumentParser(description="Apply sarf+nahw rules to enriched candidate tokens "
                                             "and emit linguistic-decision JSONL (dry-run, no writes/network).")
    ap.add_argument("--candidates", help="enriched candidate JSON (list or {tokens:[...]})")
    ap.add_argument("--index", default="qamus/indexes/existing_qamus_index.json",
                    help="existing Qamus index (de-dup ground truth)")
    ap.add_argument("--rules", default=None, help="sarf/nahw rule JSON (default: built-in DEFAULT_RULES)")
    ap.add_argument("--out", default="-", help="output JSONL path, or '-' for stdout")
    ap.add_argument("--start-id", type=int, default=1, help="first decision_id number")
    ap.add_argument("--fixture", action="store_true", help="run the inline self-test and exit")
    a = ap.parse_args()

    if a.fixture:
        _fixture()
        return
    if not a.candidates:
        ap.error("--candidates is required (or pass --fixture for the self-test)")

    index = load_index(a.index)
    rules = load_rules(a.rules)
    candidates = load_candidates(a.candidates)
    records = run(candidates, rules, index, start_id=a.start_id)
    _write(records, a.out)
    if a.out != "-":
        counts = {}
        for r in records:
            counts[r["decision"]["type"]] = counts.get(r["decision"]["type"], 0) + 1
        sys.stderr.write("wrote %d decisions to %s %s\n" % (len(records), a.out, json.dumps(counts)))


if __name__ == "__main__":
    main()
