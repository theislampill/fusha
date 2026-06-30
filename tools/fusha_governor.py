#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_governor — the governor / iʿrāb / dependency CANDIDATE lattice (P2 deliverable B).

Builds an ʿāmil→maʿmūl (governor→governed) candidate lattice over a unit and detects "right case, wrong/absent
governor". It is CONSERVATIVE and AMBIGUITY-PRESERVING: only the layer-1-safe heuristic resolves (a standalone
preposition governs the following noun in the genitive); PP-attachment (which head the prepositional phrase attaches
to) stays UNRESOLVED; iḍāfa is a candidate with kept alternatives; coordinating wāw is correctly HEADLESS (each
governed node has at most one head — deep-research F6). For arbitrary/unvoweled input the case ending is not visible,
so even the safe rule yields a heuristic CANDIDATE (decision pending), never a confirmed reading. It NEVER asserts a
single governor for an ambiguous token, and a heuristic edge NEVER overrides source-addressed certainty.

The case/mood-as-a-consequence-of-a-stated-governor + the rule that justifies it is an engineering synthesis (treebanks
store head-pointer + relation label but not case-as-consequence — deep-research REFUTED that), so `assigned_case_mood`
+ `governor_justification` + `justification_rule` are produced here. A proposed iʿrāb claim that asserts a case with no
justifying governor is flagged `governor_not_justified` (right_answer_wrong_reason) → routes to scholar/iʿrāb review;
this class is registered in the shared `fusha_check.IRAB_SENSITIVE_ISSUE_CLASSES` so it can never be auto_safe.

Dry-run: live_writes==0; public fields source-clean {src:qamus,kind:authored,lang:en}; all text scanned via leak_sot.
CLI: --self-test | --emit-fixture <path> | --in <units.jsonl> --out <-|path>.
See parserplans/general-fusha-grammar-checker-p2/002-governor-irab-dependency-lattice.md.
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
from tools import leak_sot  # noqa: E402
from tools.validate_linguistic_decisions import required_gate  # noqa: E402

SCHEMA = "fusha/dependency-candidate-lattice@1"
_PUBLIC_BOUNDARY = {"public_gloss_src": "qamus", "public_gloss_kind": "authored",
                    "public_gloss_lang": "en", "external_source_names_public": False}

# Standalone (non-proclitic) Arabic prepositions that govern the FOLLOWING noun in the genitive. (Proclitic bi/li/ka
# live INSIDE a token and are handled by the segment/morphology layer, not the cross-token dependency lattice.)
KNOWN_PREPS = {"من", "إلى", "الى", "على", "في", "عن", "مع", "حتى", "منذ", "مذ", "عند", "لدى", "لدن", "نحو",
               "دون", "خلال", "حول", "قبل", "بعد", "تحت", "فوق", "أمام", "وراء", "خلف", "بين"}
_NOUN_POS = {"noun", "proper_noun", "adjective", "participle", "masdar", "pronoun", "demonstrative"}
# signals that the NAMED governor is a preposition (which can only ever assign the genitive)
_PREP_SIGNALS = ("preposition", "ḥarf jarr", "harf jarr", "حرف جر", "by the preposition", "jarr particle")
# governor/role terms (English + transliteration + Arabic) that count as NAMING a governing element / iʿrāb basis
_GOVERNOR_TERMS = ("govern", "governed by", "governing", "ʿāmil", "amil", "عامل", "because of the",
                   "by the preposition", "by the verb", "muḍāf", "idafa", "iḍāfa",
                   "fāʿil", "faail", "fail", "mafʿūl", "mafool", "mubtadaʾ", "mubtada", "khabar",
                   "majrūr", "majrur", "marfūʿ", "marfu", "manṣūb", "mansub",
                   "فاعل", "مفعول", "مبتدأ", "خبر", "مجرور", "مرفوع", "منصوب")

_ROUTE = {
    "jar_majrur": ("nahw", "nahw/procedures/idafa-jar-majrur.md"),
    "idafa_dependent": ("nahw", "nahw/procedures/idafa-jar-majrur.md"),
    "pp_attachment": ("nahw", "nahw/procedures/pp-attachment-review.md"),
    "coordination": ("nahw", "nahw/procedures/particle-decision.md"),
    "governor_not_justified": ("scholar_irab_review", "nahw/procedures/irab-case-mood.md"),
}


def _clean(s):
    return leak_sot.redact(s) if isinstance(s, str) else s


def _mk_edge(edge_id, dependent, rel_label, rel_label_ar, justification, justification_rule, *,
             candidate_head=None, headless=False, governor_type="none", assigned_case_mood=None,
             confidence="medium", evidence_class="heuristic", unresolved=None, contradiction=False,
             raww=False, decision_status="pending", triggers=None):
    lane, proc = _ROUTE.get(justification_rule if justification_rule == "governor_not_justified" else rel_label,
                            ("nahw", "nahw/procedures/irab-case-mood.md"))
    gate = required_gate(triggers or ["irab"])  # iʿrāb-sensitive → never auto_safe (two_vote+)
    return {
        "edge_id": edge_id, "dependent": dependent, "candidate_head": candidate_head, "headless": headless,
        "governor_type": governor_type, "rel_label": rel_label, "rel_label_ar": _clean(rel_label_ar),
        "assigned_case_mood": assigned_case_mood, "governor_justification": _clean(justification),
        "justification_rule": justification_rule, "justification_confidence": confidence,
        "evidence_class": evidence_class, "unresolved_alternatives": unresolved or [],
        "contradiction_marker": contradiction, "right_answer_wrong_reason_marker": raww,
        "decision_status": decision_status, "gate": gate, "route_to": {"lane": lane, "procedure": proc},
    }


def _is_prep(tok):
    pos = (tok.get("pos") or "").lower()
    return pos in {"preposition"} or N.bare(tok.get("surface", "")) in KNOWN_PREPS


def _is_noun(tok):
    return (tok.get("pos") or "").lower() in _NOUN_POS


def build_dependency_lattice(unit):
    """unit = {input_mode, source_unit:{address,scope}, tokens:[{ref,surface,pos?,case_visible?}], claims?:[...]}."""
    mode = unit.get("input_mode", "arbitrary_typing")
    source_addressed = mode == "source_addressed"
    toks = unit.get("tokens") or []
    edges = []
    eid = 0

    def nxt():
        nonlocal eid
        eid += 1
        return "e%d" % eid

    for i, t in enumerate(toks):
        ref = t.get("ref", "tok:%d" % i)
        # (1) standalone preposition -> following noun in the genitive (LAYER-1 SAFE)
        if _is_prep(t) and i + 1 < len(toks) and _is_noun(toks[i + 1]):
            dep = toks[i + 1]
            dep_ref = dep.get("ref", "tok:%d" % (i + 1))
            case_visible = dep.get("case_visible")
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
        # (3) iḍāfa CANDIDATE: noun + noun (not a prep+noun already handled) -> muḍāf ilayh, but kept ambiguous
        elif _is_noun(t) and i + 1 < len(toks) and _is_noun(toks[i + 1]) and not _is_prep(t):
            dep = toks[i + 1]
            dep_ref = dep.get("ref", "tok:%d" % (i + 1))
            # A bare noun+noun is genuinely AMBIGUOUS: iḍāfa (2nd genitive) OR a nominal sentence mubtadaʾ+khabar
            # (2nd NOMINATIVE) OR ṣifa/badal. Do NOT assert a case in arbitrary mode (the ending is not visible and the
            # construction is undetermined); only a source-addressed visible ending confirms it. Keep ALL readings.
            edges.append(_mk_edge(nxt(), dep_ref, "idafa_dependent", "muḍāf ilayh (candidate)",
                                  "The second noun MAY be the muḍāf ilayh (genitive by the iḍāfa construct), but the pair could equally be a nominal sentence (mubtadaʾ + khabar, the second nominative) or a ṣifa/badal; all readings kept, none asserted.",
                                  "idafa_governs_genitive", candidate_head=ref, governor_type="noun",
                                  assigned_case_mood=(dep.get("case_visible") if source_addressed else None),
                                  confidence="low", evidence_class=("source_addressed" if source_addressed and dep.get("case_visible") else "heuristic"),
                                  unresolved=[{"reading": "iḍāfa: muḍāf ilayh (genitive)", "rel_label": "idafa_dependent", "case": "genitive"},
                                              {"reading": "nominal sentence: mubtadaʾ + khabar (predicate nominative)", "rel_label": "subject", "case": "nominative"},
                                              {"reading": "ṣifa (adjective, agrees in case)", "rel_label": "sifa"},
                                              {"reading": "badal (apposition, agrees in case)", "rel_label": "badal"}],
                                  decision_status="pending", triggers=["idafa_ambiguous"]))
        # (4) coordinating wāw is correctly HEADLESS (F6: at most one head; some segments have none)
        elif N.bare(t.get("surface", "")) == "و" and (t.get("pos") or "").lower() in {"conjunction", "particle", ""}:
            edges.append(_mk_edge(nxt(), ref, "coordination", "wāw al-ʿaṭf",
                                  "A coordinating wāw has no governor of its own; it links what follows to what precedes.",
                                  "coordination_no_governor", candidate_head=None, headless=True, governor_type="none",
                                  assigned_case_mood=None, confidence="medium", evidence_class="heuristic",
                                  decision_status="resolved", triggers=["irab"]))

    # (5) governor_not_justified: a proposed iʿrāb claim that asserts a case with NO justifying governor
    for c in unit.get("claims") or []:
        if c.get("claim_type") in {"case_mood", "governor", "irab_role"} and c.get("claimed_value"):
            gov = (c.get("claimed_governor") or "").strip()
            reason = (c.get("claimed_reasoning") or "")
            cv = c.get("claimed_value")
            blob = (gov + " " + reason).lower()
            ev = "source_addressed" if source_addressed else "heuristic"
            # (D) a stated PREPOSITION governor paired with a NON-genitive case is a CONTRADICTION — a preposition only
            # ever assigns the genitive, so the named governor is WRONG for the asserted case (right answer, wrong reason).
            if any(p in blob for p in _PREP_SIGNALS) and cv not in ("genitive", "none", None):
                edges.append(_mk_edge(nxt(), c.get("target", "tok:0"), "none", "ʿāmil mukhālif li-l-iʿrāb",
                                      "A preposition governs the genitive, not the %s; the named governing element contradicts the asserted case." % cv,
                                      "governor_not_justified", candidate_head=None, governor_type="none",
                                      assigned_case_mood=cv, confidence="high", evidence_class=ev,
                                      raww=True, decision_status="pending", triggers=["irab", "case_or_mood"]))
                continue
            # (M) justified only if a governor token is NAMED or the reasoning uses a recognized governor/role term
            # (English, transliteration, OR Arabic); otherwise the case is asserted with no ʿāmil → flag (absent governor).
            mentions_governor = bool(gov) or any(w in reason.lower() for w in _GOVERNOR_TERMS)
            if not mentions_governor:
                edges.append(_mk_edge(nxt(), c.get("target", "tok:0"), "none", "ʿāmil ghayr mubayyan",
                                      "The case “%s” is asserted without naming the governing element (ʿāmil); a correct ending with no justified governor is unsafe." % cv,
                                      "governor_not_justified", candidate_head=None, governor_type="none",
                                      assigned_case_mood=cv, confidence="high", evidence_class=ev,
                                      raww=True, decision_status="pending", triggers=["irab", "case_or_mood"]))

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
        # 5. coordinating wāw — headless (correct)
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
              "PP-attachment unresolved; wāw headless; right-answer-wrong-reason flagged; ambiguity preserved; never auto_safe" % len(regression_units()))
    return 0 if not failures else 1


def emit_fixture(path):
    rows = [build_dependency_lattice(u) for u in regression_units()]
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    meta = {
        "schema": SCHEMA, "generator": "tools/fusha_governor.py --emit-fixture", "count": len(rows),
        "note": "Governor/iʿrāb dependency CANDIDATE lattices. Conservative (layer-1-safe prep→genitive; PP-attachment "
                "unresolved; iḍāfa ambiguous; wāw headless; right-answer-wrong-reason flagged). Authored; Qurʾānic "
                "surfaces verbatim; source-clean {src:qamus,kind:authored,lang:en}; never auto_safe; live_writes==0. parserplans p2/002.",
    }
    with open(path.replace(".jsonl", "") + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %d lattices -> %s (+ .meta.json)" % (len(rows), path))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Fusha governor/dependency candidate lattice (dry-run, conservative).")
    ap.add_argument("--in", dest="infile")
    ap.add_argument("--out", dest="outfile", default="-")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", dest="emit")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.emit:
        return emit_fixture(a.emit)
    if not a.infile:
        ap.error("need --in, --self-test, or --emit-fixture")
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
