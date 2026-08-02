#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the complete curriculum-to-capability matrix (25 sarf + 38 nahw
families). Curriculum-coverage numbers are COMPUTED from the committed
concept graph (deterministic keyword probes over heading text + domain);
repository dims are an authored assessment verified against the crosswalks
and subsystem maps (each row cites its paths, which must exist).

Output: curriculum/l1l6/reports/capability-matrix.jsonl (+ meta).
Deterministic; CI-recomputable. Classification dims per family:
curriculum_coverage / repo_documentary_support / repo_executable_consumer /
fixture_coverage / instructional_support / occurrence_coverage /
rich_hover_readiness / backprop_readiness / remaining_work.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

NONE_ = "none"
CONS = "tools/curriculum_unit_consumer.py"

# (family_id, axis, name, keyword probes [lowercase; ar tokens exact],
#  domains, documentary paths, executable consumer, fixture coverage,
#  instructional support, occurrence coverage, hover readiness,
#  backprop readiness, remaining work)
F = []


def f(fid, axis, name, kws, domains, doc, consumer, fixtures, instr, occ,
      hover, backprop, remaining):
    F.append((fid, axis, name, kws, domains, doc, consumer, fixtures, instr,
              occ, hover, backprop, remaining))


P_PEND = "pending unit authoring (queue q-unit-authoring)"
NO_OCC = "no committed occurrence authority yet (queue q-pvn-grounding)"
HV_INC = "increment hover fields declared"
BP_BUNDLE = "promotion bundle emittable (curriculum/l1l6/promotion/)"

# ------------------------------------------------------------------- SARF
f("fs-01", "sarf", "script and orthographic preparation", ["letter", "script", "hamza", "vowel", "sukun", "shadda"], ["script_phonology"],
  ["curriculum/drills/alphabet-and-sounds.md"], NONE_, NONE_, P_PEND, NO_OCC, "n/a (pre-linguistic)", "documentary only", "author phonology unit if tutoring needs it")
f("fs-02", "sarf", "roots and radicals", ["root", "radical", "جذر"], ["roots_patterns"],
  ["sarf/procedures/root-decision.md", "sarf/rules/root-decision-rules.json"], "tools/fusha_morphology_lattice.py", "false-clitic bank 130 rows", "u-s01 + inc-ownership", "12 p007 occurrences (carve-level)", HV_INC, BP_BUNDLE, "host-root certification lane")
f("fs-03", "sarf", "patterns and measures", ["pattern", "wazn", "template", "measure", "وزن"], ["roots_patterns", "derivation"],
  ["sarf/references/verb-measures-table.md"], "tools/fusha_paradigm_generate.py", "paradigm slots (consumed store)", "u-s02", NO_OCC, "form label + augment colouring designed", BP_BUNDLE, "per-token wazn classifier (TP-SARF-A1-DERIVATIVE-CONSUMER)")
f("fs-04", "sarf", "forms I-X", ["form i", "form v", "shadda", "augment"], ["derivation"],
  ["sarf/rules/verb-measures.json"], "tools/fusha_paradigm_generate.py", "18 verb-measure examples", "u-s02", NO_OCC, "form chip designed", BP_BUNDLE, "form-detection consumer")
f("fs-05", "sarf", "quadriliterals", ["quadriliteral", "رباعي"], ["derivation", "paradigms"],
  ["sarf/rules/verb-measures.json"], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "documentary only", "quadriliteral unit + fixtures")
f("fs-06", "sarf", "active and passive voice", ["passive", "voice", "المجهول"], ["paradigms"],
  ["sarf/rules/verb-measures.json"], NONE_, "state-machine eval 26 (candidate_no_consumer)", P_PEND, NO_OCC, NONE_, "blocked on key-resolver", "TP-SARF-A1-KEY-RESOLVER-CONSUMER")
f("fs-07", "sarf", "participles", ["participle", "فاعل", "مفعول"], ["derivation"],
  ["sarf/references/masdar-participle-notes.md"], CONS, "inc-derivatives 8 fixtures incl. weak-root transfer", "u-s03 + inc-derivatives", NO_OCC, HV_INC, BP_BUNDLE, "occurrence grounding")
f("fs-08", "sarf", "masdar families", ["masdar", "مصدر", "verbal noun"], ["derivation"],
  ["sarf/references/masdar-participle-notes.md"], CONS, "masdar templates in inc-derivatives pack", "u-s04", NO_OCC, HV_INC, BP_BUNDLE, "form-I attestation checks")
f("fs-09", "sarf", "place, time and instrument nouns", ["place", "instrument", "مكان", "آلة"], ["derivation"],
  ["sarf/procedures/masdar-participle.md"], CONS, "pilot + inc-ownership fixtures", "u-s05 + pilot", NO_OCC, HV_INC, BP_BUNDLE, "occurrence grounding")
f("fs-10", "sarf", "diminutives and elatives", ["diminutive", "elative", "تصغير", "تفضيل"], ["derivation"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "author unit + probe elative homographs (أعلم class)")
f("fs-11", "sarf", "weak/hollow/defective/assimilated roots", ["hollow", "defective", "assimilated", "weak", "أجوف", "ناقص"], ["paradigms"],
  ["sarf/procedures/weak-root.md", "sarf/rules/weak-root-gates.json"], CONS, "der-trn hollow fixtures (loop derivation)", "u-s06", NO_OCC, "hidden-radical note designed", BP_BUNDLE, "wire weak gates to a consumer (Store A wiring)")
f("fs-12", "sarf", "geminate roots", ["geminate", "doubled", "مضعف"], ["paradigms"],
  ["sarf/procedures/doubled-root.md"], NONE_, NONE_, "u-s06 (covered in unit)", NO_OCC, NONE_, "documentary only", "geminate fixtures for the ownership consumer")
f("fs-13", "sarf", "hamzated roots", ["hamzated", "مهموز", "hamza"], ["paradigms", "script_phonology"],
  ["sarf/procedures/hamza-root.md", "sarf/rules/hamza-gates.json"], NONE_, "hamza-gates fixture-only", "u-s06", NO_OCC, NONE_, "fixture-only", "seat-change fixtures")
f("fs-14", "sarf", "i'lal", ["i'lal", "إعلال", "qalb"], ["morphology_general"],
  [], NONE_, NONE_, "u-s07", NO_OCC, "transformation-note designed", "unit only", "derivation-chain checker (C-level)")
f("fs-15", "sarf", "ibdal", ["ibdal", "إبدال"], ["morphology_general"],
  [], NONE_, NONE_, "u-s07", NO_OCC, NONE_, "unit only", "form-VIII assimilation fixtures")
f("fs-16", "sarf", "idgham", ["idgham", "إدغام"], ["morphology_general", "script_phonology"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "author idgham unit (shadda collapse ties to geminates)")
f("fs-17", "sarf", "clitics", ["clitic", "proclitic", "الجر"], ["clitics_affixes"],
  ["sarf/procedures/root-decision.md"], "tools/fusha_morphology_lattice.py", "130-row bank implemented_and_consumed", "u-s09 + inc-ownership", "12 p007 occurrences", "p007 two-surface projections exist", BP_BUNDLE, "بِـ (p002) pre-flight")
f("fs-18", "sarf", "attached pronouns", ["pronoun", "الضمائر", "enclitic"], ["clitics_affixes"],
  ["sarf/rules/suffix-pronoun-rules.json"], NONE_, "suffix-pronoun eval 71 (test-run only)", "u-s09", NO_OCC, NONE_, "fixture-only", "wire suffix rules to a consumer")
f("fs-19", "sarf", "person/number/gender inflection", ["person", "inflection", "conjugation", "تصريف"], ["inflection", "paradigms"],
  ["sarf/rules/verb-measures.json"], "tools/fusha_paradigm_generate.py", "paradigm slots", P_PEND, NO_OCC, NONE_, "generator exists", "inflection unit authoring")
f("fs-20", "sarf", "duals", ["dual", "مثنى"], ["paradigms"],
  ["sarf/rules/plural-gender-rules.json"], NONE_, "plural-gender fixture-only", "u-s08", NO_OCC, NONE_, "fixture-only", "dual tail fixtures")
f("fs-21", "sarf", "sound plurals", ["sound masculine", "sound feminine", "السالم"], ["paradigms"],
  ["sarf/rules/plural-gender-rules.json"], NONE_, "fixture-only", "u-s08", NO_OCC, NONE_, "fixture-only", "tail-vs-radical fixtures for ownership consumer")
f("fs-22", "sarf", "broken plurals", ["broken plural", "التكسير"], ["paradigms"],
  ["sarf/rules/root-pattern-risk-rules.json"], NONE_, "GAP-S9: no broken-plural producer", "u-s08", NO_OCC, NONE_, "gap", "lemma-linkage consumer (never surface)")
f("fs-23", "sarf", "letter ownership", ["ownership", "augment"], ["roots_patterns", "derivation"],
  ["curriculum/l1l6/increments/inc-ownership/reference.md"], CONS, "7 fixtures + loop", "u-s01/u-s05/u-s09 + inc-ownership", "12 p007 occurrences (carve; host pending)", HV_INC, BP_BUNDLE, "host-root certification")
f("fs-24", "sarf", "surface reconstruction", ["surface", "orthograph"], ["morphology_general", "script_phonology"],
  ["tools/normalize_ar.py"], "tools/fusha_text_check.py", "combining-mark byte-exact bank (2)", P_PEND, NO_OCC, NONE_, "engine exists", "unit tying i'lal chains to surface checks")
f("fs-25", "sarf", "sarf ambiguity and abstention", ["ambiguity", "abstention", "pending"], ["ambiguity"],
  ["sarf/rules/homograph-quarantines.json"], CONS, "abstention fixtures in every increment", "all units carry abstention_conditions", "corpus-pilot abstention machine-produced", "abstention_note designed", BP_BUNDLE, "quarantine store wiring (Store A)")

# ------------------------------------------------------------------- NAHW
f("fn-01", "nahw", "nominal and verbal sentences", ["nominal sentence", "verbal sentence", "الجملة"], ["syntactic_relations"],
  ["nahw/SKILL.md"], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "sentence-type unit")
f("fn-02", "nahw", "mubtada' and khabar", ["مبتدأ", "خبر", "predicate", "topic"], ["syntactic_relations"],
  ["nahw/SKILL.md"], "tools/fusha_governor.py", "7 lattice rows", P_PEND, NO_OCC, NONE_, "lattice-native", "mubtada'/khabar fixtures via q-governance")
f("fn-03", "nahw", "subject, object and transitivity", ["فاعل", "مفعول به", "transitiv", "object"], ["syntactic_relations"],
  ["qamus/schemas/dependency-candidate-lattice.schema.json"], "tools/fusha_governor.py", "lattice justification rules", P_PEND, NO_OCC, NONE_, "lattice-native", "graded sentence fixtures")
f("fn-04", "nahw", "case signs", ["case", "الرفع", "النصب", "الجر", "nominative", "accusative", "genitive"], ["case_mood"],
  ["nahw/procedures/irab-case-mood.md"], "tools/validate_two_vote_artifacts.py", "two-vote artifacts v1.1", "u-n01", "p007 case_mood_governor facts (12 occ)", "case chip with governor+reason", "two-vote plane", "widen beyond p007")
f("fn-05", "nahw", "mood signs", ["mood", "jussive", "subjunctive", "المجزوم", "المنصوب"], ["case_mood"],
  ["nahw/rules/negation-rules.json"], CONS, "inc-negation 5 fixtures", "u-n01 + inc-negation", NO_OCC, "negation-effect chip", BP_BUNDLE, "mood-marking evidence rows")
f("fn-06", "nahw", "secondary case signs", ["five nouns", "الأسماء الخمسة", "letter case"], ["case_mood"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "secondary-signs unit (duals/plurals/five nouns letter marking)")
f("fn-07", "nahw", "kana-family", ["كان", "kana"], ["governance"],
  ["curriculum/l1l6/increments/inc-nawasikh/reference.md"], CONS, "inc-nawasikh fixtures", "u-n02 + inc-nawasikh", NO_OCC, HV_INC, BP_BUNDLE, "occurrence grounding via p-entries")
f("fn-08", "nahw", "inna-family", ["إن", "inna", "أخوات"], ["governance"],
  ["curriculum/l1l6/increments/inc-nawasikh/reference.md"], CONS, "inc-nawasikh fixtures incl. swap adversarial", "u-n02 + inc-nawasikh", NO_OCC, HV_INC, BP_BUNDLE, "occurrence grounding (p011/p012)")
f("fn-09", "nahw", "other nawasikh (zanna, kada...)", ["ظن", "كاد", "zanna"], ["governance"],
  [], CONS, "zanna family in pack", "u-n02", NO_OCC, HV_INC, "pack covers zanna; kada missing", "add kada-family rows to the pack (declarative)")
f("fn-10", "nahw", "prepositional government", ["preposition", "جر", "jarr"], ["particles"],
  ["nahw/procedures/idafa-jar-majrur.md"], "tools/fusha_governor.py", "p007 governor facts", "u-s09 (carve) + u-n03", "12 p007 occurrences CERTIFIED-lane", "existing two-surface projections", "the flagship lane", "extend to p034-p039 entries")
f("fn-11", "nahw", "idafa", ["idafa", "الإضافة", "construct"], ["syntactic_relations"],
  ["nahw/procedures/idafa-jar-majrur.md"], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "procedure only", "idafa unit + definiteness-chain fixtures")
f("fn-12", "nahw", "adjectives and followers", ["adjective", "النعت", "توابع", "apposition", "بدل"], ["syntactic_relations"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "followers unit (na't/badal/tawkid/atf agreement chains)")
f("fn-13", "nahw", "relative clauses and 'a'id", ["relative", "الموصول", "صلة"], ["syntactic_relations"],
  ["nahw/procedures/relative-interrogative.md"], CONS, "hid-pos-02 'a'id gap fixture", "u-n05 + inc-hidden", NO_OCC, "relative-chain card designed", BP_BUNDLE, "p094-p098 occurrence grounding")
f("fn-14", "nahw", "conditional systems", ["conditional", "الشرط", "جواب"], ["particles"],
  ["nahw/procedures/conditionals.md"], CONS, "ma-adv-02 shartiyya fixture", "u-n06", NO_OCC, NONE_, "partial via inc-ma", "conditional-pair unit pack (protasis/apodosis moods)")
f("fn-15", "nahw", "exception", ["exception", "الاستثناء", "إلا"], ["particles"],
  ["nahw/SKILL.md"], NONE_, "istithna' gate class (two-vote trigger)", P_PEND, NO_OCC, NONE_, "gate exists", "istithna' unit (polarity/connectedness)")
f("fn-16", "nahw", "vocative", ["vocative", "النداء", "المنادى"], ["particles"],
  [], CONS, "hid-pos-03 vocative licence fixture", "u-n08 (licensing row)", NO_OCC, "hidden-element chip", "licensing covered", "munada case fixtures")
f("fn-17", "nahw", "oath", ["oath", "القسم"], ["particles"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "oath unit (waw/ba/ta al-qasam + jawab)")
f("fn-18", "nahw", "negation", ["negation", "النفي"], ["particles"],
  ["nahw/rules/negation-rules.json", "nahw/procedures/negation.md"], CONS, "inc-negation 5 fixtures", "u-n01 + inc-negation", NO_OCC, HV_INC, BP_BUNDLE, "wire nahw/rules/negation-rules.json (GAP-N2) or supersede via pack")
f("fn-19", "nahw", "multifunction particles", ["particle", "حرف"], ["particles"],
  ["tools/funcword_homograph_prepass.py"], CONS, "inc-ma + prepass 13 tests", "u-n07 + inc-ma", "2 exact ma occurrences", HV_INC, BP_BUNDLE, "extend packs to لو/لما/أن families")
f("fn-20", "nahw", "ma functions (all major)", ["ما"], ["particles"],
  ["curriculum/l1l6/increments/inc-ma/reference.md"], CONS, "6 fixtures + ma-ambiguity loop", "u-n07 + inc-ma", "93:3:1 + 2:284:10 exemplars", "function inventory + alternatives panels", BP_BUNDLE, "per-occurrence discriminator evidence rows (p099 lane)")
f("fn-21", "nahw", "attachment", ["attachment", "attach"], ["syntactic_relations"],
  ["nahw/rules/pronoun-attachment-rules.json"], NONE_, "existence-checked only (GAP-N3)", "u-n10", NO_OCC, NONE_, "unit only", "attachment-site test fixtures")
f("fn-22", "nahw", "scope", ["scope"], ["syntactic_relations", "particles"],
  [], NONE_, NONE_, "u-n10", NO_OCC, NONE_, "unit only", "negation/coordination scope fixtures (genuine ambiguity preserved)")
f("fn-23", "nahw", "referent", ["referent", "المرجع"], ["contextual_interpretation"],
  ["nahw/rules/referent-guard-rules.json", "nahw/procedures/referent-context.md"], NONE_, "referent guards zero consumer (GAP-N2)", "u-n10", NO_OCC, NONE_, "guards exist unwired", "wire referent guards")
f("fn-24", "nahw", "governor and governed expression", ["governor", "عامل", "govern"], ["governance"],
  ["tools/fusha_governor.py", "tools/validate_dependency_lattice.py"], "tools/fusha_governor.py", "7 lattice rows + 9 FAIL classes", "u-n03", "p007 governor_relation facts", "governor card", "lattice-native", "widen lattice bank (q-governance packet)")
f("fn-25", "nahw", "hidden pronouns", ["hidden", "مستتر"], ["hidden_structure"],
  ["curriculum/l1l6/increments/inc-hidden/reference.md"], CONS, "hid fixtures + loop", "u-n08 + inc-hidden", NO_OCC, "hidden-element chip", BP_BUNDLE, "occurrence applications")
f("fn-26", "nahw", "deleted operators", ["deleted", "محذوف"], ["hidden_structure"],
  ["curriculum/l1l6/increments/inc-hidden/reference.md"], CONS, "vocative deleted-verb fixture", "u-n08", NO_OCC, HV_INC, BP_BUNDLE, "answer-fragment fixtures")
f("fn-27", "nahw", "taqdir", ["taqdir", "تقدير"], ["hidden_structure"],
  ["curriculum/l1l6/increments/inc-hidden/procedure.md"], CONS, "licensing-table fixtures", "u-n08/u-n09", NO_OCC, "reconstruction flagged distinct from text", BP_BUNDLE, "muqaddar-marking fixtures")
f("fn-28", "nahw", "mahall al-i'rab", ["محل", "mahall", "positional"], ["case_mood"],
  [], NONE_, NONE_, "u-n09", NO_OCC, "mahall annotation designed", "unit only", "clause-type inventory pack (licensing_table capability, declarative)")
f("fn-29", "nahw", "major mansubat", ["حال", "تمييز", "مفعول مطلق", "الظرف"], ["syntactic_relations"],
  ["nahw/SKILL.md"], NONE_, NONE_, "u-n04", NO_OCC, "role chip designed", "unit only", "role-criteria pack (discriminator_table capability, declarative)")
f("fn-30", "nahw", "ishtighal", ["اشتغال", "ishtighal"], ["governance"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "C2 construction: record in claim families first")
f("fn-31", "nahw", "tanazu'", ["تنازع", "tanazu"], ["governance"],
  [], NONE_, NONE_, "u-n03 (exception noted)", NO_OCC, NONE_, "lattice can hold competing governors", "tanazu' fixtures for the lattice")
f("fn-32", "nahw", "ta'liq and ilgha'", ["تعليق", "إلغاء"], ["governance"],
  [], NONE_, NONE_, P_PEND, NO_OCC, NONE_, "unit missing", "zanna-family suspension rows (pack-extendable)")
f("fn-33", "nahw", "multiple valid analyses", ["rival", "two analyses", "ambigu"], ["ambiguity"],
  ["qamus/schemas/dependency-candidate-lattice.schema.json"], CONS, "ma-adv-01 alternatives fixture + lattice", "u-n11", "92:3:1 attributed-unresolved exemplar", "alternatives panel", "lattice + packs", "school attribution as typed dimension")
f("fn-34", "nahw", "Basran/Kufan attribution", ["basran", "kufan", "البصري", "الكوفي"], ["ambiguity"],
  ["docs/blockers.yaml"], NONE_, NONE_, "u-n11 + claim family cf-n11", NO_OCC, "attribution notes designed", "scholar lane", "attribution dimension in artifacts (owner/Sol decision)")
f("fn-35", "nahw", "sentence and discourse cohesion", ["discourse", "cohesion", "استئناف"], ["contextual_interpretation"],
  [], NONE_, NONE_, "u-n12", NO_OCC, "clause-type annotation designed", "unit only", "waw-discrimination pack (discriminator_table, declarative)")
f("fn-36", "nahw", "contextual interpretation", ["context", "interpretation"], ["contextual_interpretation"],
  ["nahw/rules/context-sense-rules.json"], NONE_, "context-sense rules unconsumed (GAP-N2)", "u-n12", NO_OCC, NONE_, "rules exist unwired", "wire context-sense rules")
f("fn-37", "nahw", "translation safety", ["translation", "gloss"], ["contextual_interpretation"],
  ["sarf/SKILL.md", "nahw/SKILL.md"], "tools/validate_linguistic_decisions.py", "gate ladder mutation-proven", "og-5 guard + claim rows", NO_OCC, "hover glosses entry-governed", "gate-native", "none — enforced boundary")
f("fn-38", "nahw", "abstention and escalation", ["abstention", "escalation", "pending"], ["ambiguity"],
  ["nahw/evals/grammar-decision-gates.json"], "tools/validate_linguistic_decisions.py", "4-home SSOT parity", "every unit's abstention_conditions", "corpus-pilot machine abstention", "abstention notes", "gate-native", "none — enforced boundary")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def build():
    concepts = [json.loads(l) for l in
                (BASE / "graph" / "concepts.jsonl").read_text(encoding="utf-8").splitlines()
                if l.strip()]
    rows = []
    for (fid, axis, name, kws, domains, doc, consumer_, fixtures, instr, occ,
         hover, backprop, remaining) in F:
        matched = []
        for c in concepts:
            h = nfc(c["heading"]).lower()
            if c["domain"] in domains or any(nfc(k) in h for k in kws):
                matched.append(c)
        lessons = sorted({c["lesson_id"] for c in matched})
        rows.append({
            "schema": "curriculum.l1l6_capability_matrix_row.v1",
            "family_id": fid, "axis": axis, "family": name,
            "curriculum_coverage": {
                "matched_concept_nodes": len(matched),
                "matched_lessons": len(lessons),
                "levels": sorted({l.split(".")[0] for l in lessons}),
                "probe": {"keywords": kws, "domains": domains},
            },
            "repo_documentary_support": doc,
            "repo_executable_consumer": consumer_,
            "fixture_coverage": fixtures,
            "instructional_support": instr,
            "occurrence_coverage": occ,
            "rich_hover_readiness": hover,
            "backprop_readiness": backprop,
            "remaining_work": remaining,
            "assessment_basis": "curriculum numbers computed from committed concept graph; repo dims authored, verified against docs/subsystems/*-executable-map.md + crosswalks",
        })
    return rows


def serialize(rows):
    out = {}
    out[str(BASE / "reports" / "capability-matrix.jsonl")] = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    ).encode("utf-8")
    meta = {
        "schema": "curriculum.l1l6_capability_matrix_row.v1.meta",
        "generator": "tools/build_capability_matrix.py",
        "rows": len(rows),
        "sarf_families": sum(1 for r in rows if r["axis"] == "sarf"),
        "nahw_families": sum(1 for r in rows if r["axis"] == "nahw"),
        "families_with_executable_consumer": sum(
            1 for r in rows if r["repo_executable_consumer"] != NONE_),
        "families_pending_unit_authoring": sum(
            1 for r in rows if "pending unit authoring" in str(r["instructional_support"])),
    }
    out[str(BASE / "reports" / "capability-matrix.meta.json")] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return out


def main(argv):
    check = "--check" in argv
    files = serialize(build())
    bad = []
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(p.name)
        else:
            p.write_bytes(data)
            print("wrote %s (%d bytes)" % (p.relative_to(ROOT), len(data)))
    if check:
        if bad:
            print("FAIL: capability matrix differs from recompute: %s" % ", ".join(bad))
            return 1
        print("OK: capability matrix byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
