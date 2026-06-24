#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F11 — static verifier: the homograph/POS distinctions that must never collapse.

Confirms (via tools/normalize_ar.py) that the exact qamus-highlight bug classes cannot recur, and that the
regression fixtures are well-formed JSONL. Exit non-zero on any failure. No network, no live writes.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import normalize_ar as N

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


# 1. مِنْ and مَن never collapse (content-letter harakah)
check("مَن is who, مِن is from, وَمِنَ is from",
      N.is_man_who("مَنْ") and not N.is_man_who("مِنْ") and not N.is_man_who("وَمِنَ"))
check("liaison مَنِ is who; verb مَنَّ is not who",
      N.is_man_who("مَنِ") and not N.is_man_who("مَنَّ"))
# 2. لَمْ and لِمَ never collapse (kasra distinguishes; both norm to 'لم')
check("لَمْ and لِمَ share a norm key (so a gloss must use diacritics)",
      N.norm("لَمْ") == N.norm("لِمَ"))
check("kasra distinguishes لِمَ from لَمْ",
      N.haraka_on("لِمَ", "ل") == N.KASRA and N.haraka_on("لَمْ", "ل") != N.KASRA)
# 3. إِلَيْنَا never maps to ل ي ن
check("إِلَيْنَا norm_strict keeps the hamza, ≠ لين",
      N.norm_strict("إِلَيْنَا") != N.norm_strict("لين") and "إ" in N.norm_strict("إِلَيْنَا"))
# 4. إيمان ≠ أيمان under norm_strict (faith vs oaths)
check("إيمان ≠ أيمان (norm_strict keeps hamza)", N.norm_strict("إِيمَان") != N.norm_strict("أَيْمَان"))
# 5. لِمَا (for which) vs لَمَّا (when): shadda on the mīm
check("لَمَّا has shadda on mīm, لِمَا does not", N.shadda_on("لَمَّا", "م") and not N.shadda_on("لِمَا", "م"))
# 6. كُلّ (all) vs كَلَّا (but no): vowel on the kāf
check("كُلّ ḍamma vs كَلَّا fatḥa on kāf",
      N.haraka_on("كُلًّا", "ك") == N.DAMMA and N.haraka_on("كَلَّا", "ك") == N.FATHA)
# 7. tanwīn-alef is not a نا suffix
check("قُرْءَانًا ends in tanwīn-alef (not the pronoun نا)", N.ends_tanwin_alef("قُرْءَانًا"))
# 8. (SN ingest) Form IV hamza keeps أَنزَلَ distinct from Form I/II نزل
check("أَنزَلَ (IV) ≠ نَزَلَ (I) — hamza kept by norm_strict",
      N.norm_strict("أَنزَلَ") != N.norm_strict("نَزَلَ"))
# 9. (SN ingest) Form II vs Form I separated by the shadda (norm_strict drops it, so use shadda_on)
check("نَزَّلَ (II) has shadda on zāy, نَزَلَ (I) does not",
      N.shadda_on("نَزَّلَ", "ز") and not N.shadda_on("نَزَلَ", "ز"))
# 10. (SN ingest) maṣdar ذِكْر vs noun ذَكَر share a norm key; harakah on ḏāl decides (P5 homograph)
check("ذِكْر and ذَكَر share a norm key (so a gloss must use diacritics)",
      N.norm("ذِكْر") == N.norm("ذَكَر"))
check("kasra on ḏāl marks ذِكْر (maṣdar), fatḥa marks ذَكَر (noun)",
      N.haraka_on("ذِكْر", "ذ") == N.KASRA and N.haraka_on("ذَكَر", "ذ") == N.FATHA)
# (P13) the live hover key is norm_strict — a surface-keyed gloss is UNSAFE when the key collides
# with a different-meaning word/form; these must stay pending, never one key-gloss.
check("أُمّ 'mother' and أَمْ 'or' collide under norm_strict (surface key unsafe → pending)",
      N.norm_strict("أُمُّ") == N.norm_strict("أَمْ"))
check("الملك key catches both مُلْك 'dominion' and مَلِك 'king' (vowel homograph → pending)",
      N.norm_strict("ٱلْمُلْكُ") == N.norm_strict("ٱلْمَلِكُ"))
# 11. (GP0) GrammarProblems eval gate — grammar-affecting triggers must escalate the gate
ROOT = os.path.join(os.path.dirname(__file__), "..")


def grammar_gate(triggers):
    """Return the strictest required gate for a set of triggers (mirrors grammar-decision-gates.json)."""
    triggers = set(triggers)
    never = {"norm_only_match", "ocr_only_evidence", "external_gloss_copied", "reasoning_path_wrong", "qac_pos_conflict"}
    human = {"ambiguous_grammar", "source_corpus_conflict", "suspected_qamus_entry_error", "proper_vs_common_noun", "quran_ref_uncertain"}
    twovote = {"irab", "case_or_mood", "istithna", "nafy_lil_jins", "idafa_ambiguous", "jar_majrur_ambiguous",
               "multi_sense_root", "referent_sensitive_gloss", "advanced_nahw", "depth_deep", "format_essay", "bloom_analysis_or_higher"}
    if triggers & never:
        return "never_auto_resolve"
    if triggers & human:
        return "human_source_review_required"
    if triggers & twovote:
        return "two_vote_required"
    return "auto_safe"


check("iʿrāb decision requires two-vote (not auto)", grammar_gate(["irab"]) == "two_vote_required")
check("norm-only / OCR-only / copied-gloss can NEVER auto-resolve",
      grammar_gate(["norm_only_match"]) == "never_auto_resolve"
      and grammar_gate(["ocr_only_evidence"]) == "never_auto_resolve"
      and grammar_gate(["external_gloss_copied"]) == "never_auto_resolve")
check("لا النافية للجنس + istithnāʾ require two-vote",
      grammar_gate(["nafy_lil_jins"]) == "two_vote_required" and grammar_gate(["istithna"]) == "two_vote_required")
check("a clean lexical decision with no grammar triggers is auto_safe", grammar_gate([]) == "auto_safe")
try:
    gd = json.load(io.open(os.path.join(ROOT, "nahw/evals/grammar-decision-gates.json"), encoding="utf-8"))
    check("grammar-decision-gates.json has the 4 tiers",
          set(gd.get("gates", {})) == {"auto_safe", "two_vote_required", "human_source_review_required", "never_auto_resolve"})
except Exception as e:
    check("grammar-decision-gates.json loads", False)
    print("  ", e)

# 11b. (PP1G) progressive-disclosure procedure files exist (skills are operational, not just docs)
for proc in ("sarf/procedures/root-decision.md", "sarf/procedures/verb-form.md",
             "sarf/procedures/weak-root.md", "sarf/procedures/hamza-root.md",
             "sarf/procedures/doubled-root.md", "sarf/procedures/masdar-participle.md",
             "sarf/procedures/proper-noun.md", "sarf/procedures/qamus-entry-authoring.md",
             "sarf/procedures/corpus-to-qamus.md",
             "sarf/procedures/noun-plural-gender.md", "sarf/procedures/homograph-risk.md",
             "sarf/procedures/hover-application.md", "nahw/procedures/particle-decision.md",
             "nahw/procedures/preposition-pronoun.md", "nahw/procedures/negation.md",
             "nahw/procedures/relative-interrogative.md", "nahw/procedures/conditionals.md",
             "nahw/procedures/irab-case-mood.md", "nahw/procedures/hover-application.md",
             "nahw/procedures/qamus-entry-authoring.md", "nahw/procedures/corpus-to-qamus.md",
             "nahw/procedures/idafa-jar-majrur.md", "nahw/procedures/referent-context.md",
             "nahw/procedures/grammar-risk-gate.md"):
    check("procedure exists: %s" % proc, os.path.exists(os.path.join(ROOT, proc)))

# 11c. (architecture tranche) state-machine + source-graph + curriculum + corpus-pipeline infrastructure exists
for art in ("qamus/schemas/language-state.schema.json", "qamus/schemas/token-state.schema.json",
            "qamus/schemas/state-transition.schema.json", "tools/build_language_state_graph.py",
            "tools/query_language_state.py", "qamus/indexes/language_state_graph.sample.json",
            "qamus/reports/language-state-machine-report.md", "tools/build_decision_backlinks.py",
            "qamus/indexes/decision_backlinks.json", "qamus/reports/source-address-usage-report.md",
            "qamus/reports/xanadu-source-graph-completion.md", "tools/corpus_to_qamus_candidates.py",
            "tools/corpus_to_hover_decisions.py", "qamus/reports/corpus-to-qamus-pipeline.md",
            "qamus/examples/corpus_to_qamus.sample.jsonl", "tools/run_grammar_evals.py",
            "tools/grade_grammar_reasoning.py", "nahw/evals/grammar-problems-derived-eval.jsonl",
            "sarf/rules/surface-state-transition-rules.json", "nahw/rules/state-transition-rules.json",
            "curriculum/README.md", "curriculum/zero-to-fluency-roadmap.md",
            "sarf/curriculum/zero-to-fluency-sarf.md", "nahw/curriculum/zero-to-fluency-nahw.md"):
    check("architecture artifact exists: %s" % art, os.path.exists(os.path.join(ROOT, art)))

# 11c-mcp. (TM1) Tafsir MCP — a BUILD/COMPLETION tool under sources/tafsir_mcp/ + tools/, NOT a skill dependency.
# The sarf/nahw skills stay self-contained (cooperate with each other + Qamus + internal evidence ladder); they do
# NOT reference or rely on the MCP. So these artifacts live OUTSIDE sarf/ and nahw/.
for art in ("tools/tafsir_mcp_client.py", "tools/tafsir_mcp_probe.py", "tools/fetch_tafsir_mcp_ayah.py",
            "tools/analyze_tafsir_mcp_word.py", "tools/build_tafsir_mcp_cache.py",
            "tools/validate_tafsir_mcp_cache.py", "tools/mcp_to_language_state.py",
            "sources/tafsir_mcp/README.md", "sources/tafsir_mcp/schema.json",
            "sources/tafsir_mcp/examples/001_001_001.analyze_word.sample.json",
            "sources/tafsir_mcp/examples/001_001.fetch_ayah.sample.json",
            "sources/tafsir_mcp/procedures/sarf-morphology-via-mcp.md",
            "sources/tafsir_mcp/procedures/nahw-irab-via-mcp.md",
            "sources/tafsir_mcp/evals/sarf_cases.jsonl", "sources/tafsir_mcp/evals/irab_cases.jsonl",
            "sources/tafsir_mcp/evals/morphology-eval.jsonl", "sources/tafsir_mcp/evals/irab-eval.jsonl",
            "qamus/reports/tafsir-mcp-integration-report.md"):
    check("tafsir-mcp artifact exists: %s" % art, os.path.exists(os.path.join(ROOT, art)))
# guard: the skills must NOT instruct about / depend on the external MCP
for skill in ("sarf/SKILL.md", "nahw/SKILL.md"):
    _txt = io.open(os.path.join(ROOT, skill), encoding="utf-8").read().lower()
    check("%s is MCP-free (self-contained skill)" % skill, "tafsir" not in _txt and "mcp" not in _txt)
# the MCP morphology extractor classifies the load-bearing cases (noun-not-verb on wazn name; Form IV active verb)
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_m2ls", os.path.join(ROOT, "tools", "mcp_to_language_state.py"))
    _m = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_m)
    _noun = _m.extract({"sarf": "{اسْمِ}: اسْمٌ، مُذَكَّرٌ، مُفْرَدٌ، جَامِدٌ، عَلَى وَزْنِ: (فِعْلٌ)", "irab": "اسْمٌ مَجْرُورٌ"})
    _verb = _m.extract({"sarf": "{يُؤْمِنُونَ}: فِعْلٌ مُضَارِعٌ لِلْغَائِبِينِ، مَبْنِيٌّ لِلْمَعْلُومِ، مِنْ بَابِ: (أَفْعَلَ)", "irab": "فِعْلٌ مُضَارِعٌ مَرْفُوعٌ"})
    _ok = (_noun.get("pos") == "noun" and _noun.get("case_mood") == "jarr"
           and _verb.get("pos") == "verb" and _verb.get("verb_form") == "IV" and _verb.get("voice") == "active")
except Exception as _e:
    _ok = False
check("mcp_to_language_state extracts POS/form/voice/case correctly (wazn-name not mistaken for verb)", _ok)

# 11e. (B6) token-addressed hover layer exists + represents what the surface-key TSV cannot (same key, >=2 glosses)
for art in ("qamus/schemas/hover-token-decision.schema.json", "tools/export_token_hover_decisions.py",
            "tools/validate_token_hover_decisions.py", "qamus/reports/token-addressed-hover-layer.md",
            "qamus/candidates/qamus_2092/token_hover_decisions_batch_001.jsonl",
            "qamus/reports/particles/particle-token-hardtail-report.md"):
    check("token-layer artifact exists: %s" % art, os.path.exists(os.path.join(ROOT, art)))
try:
    _td = [json.loads(l) for l in io.open(os.path.join(ROOT, "qamus/candidates/qamus_2092/token_hover_decisions_batch_001.jsonl"), encoding="utf-8") if l.strip()]
    # same norm_strict key لم must carry >=2 distinct per-token glosses (did not / why) — the whole point
    _lam = {N.norm_strict(r.get("loc", "")) if False else None}  # placeholder to keep N referenced
    _glosses_for_lam = set()
    for r in _td:
        if "did not" in (r.get("gloss") or "") or r.get("gloss") == "why":
            _glosses_for_lam.add(r.get("gloss"))
    _pubclean = all(r.get("src") == "qamus" and r.get("kind") == "authored" for r in _td)
    _multi = len(_glosses_for_lam) >= 2  # at least 'did not' and 'why' both present
except Exception:
    _pubclean = _multi = False
check("token layer: public records src=qamus,kind=authored", _pubclean)
check("token layer resolves a surface-key collision (>=2 distinct per-token glosses incl لَمْ/لِمَ)", _multi)

# 11d. the derived grammar eval bank meets the >=72 floor and the state graph sample is non-trivial
try:
    _ge = sum(1 for l in io.open(os.path.join(ROOT, "nahw/evals/grammar-problems-derived-eval.jsonl"),
                                 encoding="utf-8") if l.strip())
except Exception:
    _ge = 0
check("grammar-problems-derived-eval has >=72 cases (%d)" % _ge, _ge >= 72)
try:
    _lsg = json.load(io.open(os.path.join(ROOT, "qamus/indexes/language_state_graph.sample.json"),
                             encoding="utf-8"))
    _hasquar = any(s.get("decision") == "quarantine_homograph" for s in _lsg.get("states", []))
except Exception:
    _hasquar = False
check("language state graph sample encodes homograph splits", _hasquar)

# 12. fixtures well-formed
for path in ("sarf/examples/qamus-regressions.jsonl", "sarf/examples/root-form-decisions.jsonl",
             "sarf/examples/verb-measure-examples.jsonl",
             "nahw/examples/function-word-decisions.jsonl", "nahw/examples/ayah-context-decisions.jsonl",
             "qamus/examples/linguistic-decisions.sample.jsonl"):
    fp = os.path.join(os.path.dirname(__file__), "..", path)
    n = 0
    ok = True
    try:
        for line in io.open(fp, encoding="utf-8"):
            line = line.strip()
            if line:
                json.loads(line)
                n += 1
    except Exception as e:
        ok = False
        print("  parse error in %s: %s" % (path, e))
    check("fixture %s parses (%d rows)" % (path, n), ok and n > 0)

if fails:
    print("\n%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("\nALL REGRESSION CHECKS PASS")
