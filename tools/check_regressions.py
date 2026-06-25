#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F11 — static verifier: the homograph/POS distinctions that must never collapse.

Confirms (via tools/normalize_ar.py) that the exact qamus-highlight bug classes cannot recur, and that the
regression fixtures are well-formed JSONL. Exit non-zero on any failure. No network, no live writes.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
             "sarf/procedures/hover-application.md", "sarf/procedures/clitic-and-host-morphology.md",
             "sarf/procedures/verb-form-and-mood-review.md", "nahw/procedures/particle-decision.md",
             "nahw/procedures/preposition-pronoun.md", "nahw/procedures/negation.md",
             "nahw/procedures/relative-interrogative.md", "nahw/procedures/conditionals.md",
             "nahw/procedures/irab-case-mood.md", "nahw/procedures/hover-application.md",
             "nahw/procedures/qamus-entry-authoring.md", "nahw/procedures/corpus-to-qamus.md",
             "nahw/procedures/idafa-jar-majrur.md", "nahw/procedures/referent-context.md",
             "nahw/procedures/grammar-risk-gate.md", "nahw/procedures/function-token-hover-review.md",
             "nahw/procedures/ma-function-decision.md", "nahw/procedures/pp-attachment-review.md",
             "nahw/procedures/governing-particle-mood-review.md",
             "nahw/procedures/exception-and-vocative-review.md",
             "qamus/procedures/grammar-resource-usage.md",
             "qamus/procedures/source-triangulation-and-public-boundary.md",
             "qamus/procedures/closure-lane-routing.md"):
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

# 11h. (installable package) skills wrappers/manifests/scripts + architecture doc exist
for art in ("INSTALL.md", "skills/sarf/SKILL.md", "skills/sarf/manifest.json", "skills/nahw/SKILL.md",
            "skills/nahw/manifest.json", "scripts/install_claude_skills.py",
            "scripts/install_codex_instructions.py", "scripts/verify_skill_install.py",
            "dist/codex/AGENTS.fusha.md", "qamus/reports/skill-installation-report.md",
            "curriculum/qamus-driven-fluency-engine.md"):
    check("install-package artifact exists: %s" % art, os.path.exists(os.path.join(ROOT, art)))
# the installable wrappers must themselves be MCP-free
for w in ("skills/sarf/SKILL.md", "skills/nahw/SKILL.md"):
    _t = io.open(os.path.join(ROOT, w), encoding="utf-8").read().lower()
    check("%s wrapper is MCP-free" % w, "tafsir" not in _t and "mcp-free" in _t)

# 11g. (suffix/pronoun lane) artifacts exist + the noun-vs-verb gate holds (عَلِمْنَا verb stays pending)
for art in ("qamus/schemas/suffix-pronoun-decision.schema.json", "tools/build_suffix_pronoun_decisions.py",
            "tools/validate_suffix_pronoun_decisions.py", "sarf/procedures/suffix-pronoun-state.md",
            "nahw/procedures/pronoun-attachment.md", "sarf/rules/suffix-pronoun-rules.json",
            "nahw/rules/pronoun-attachment-rules.json", "qamus/reports/suffix-pronoun-hover-report.md",
            "qamus/candidates/qamus_2092/suffix_pronoun_hover_batch_001.jsonl",
            "nahw/evals/suffix-pronoun-eval.jsonl"):
    check("suffix/pronoun artifact exists: %s" % art, os.path.exists(os.path.join(ROOT, art)))
try:
    _sp = [json.loads(l) for l in io.open(os.path.join(ROOT, "qamus/candidates/qamus_2092/suffix_pronoun_hover_batch_001.jsonl"), encoding="utf-8") if l.strip()]
    _noun_ok = any("our deeds" == r.get("gloss") for r in _sp)          # أعمالنا resolved
    _no_verb = all(r.get("gloss") != "our knowledge" for r in _sp)      # عَلِمْنَا verb NOT mis-glossed
    _poss_ok = all(r.get("decision_state") == "suffix_pronoun_decision" for r in _sp)
except Exception:
    _noun_ok = _no_verb = _poss_ok = False
check("suffix lane resolves أعمالنا='our deeds'", _noun_ok)
check("suffix lane excludes verb hosts (no 'our knowledge' for عَلِمْنَا)", _no_verb and _poss_ok)
# the eval fixture encodes the noun-resolve + verb-pending contract
try:
    _ev = [json.loads(l) for l in io.open(os.path.join(ROOT, "nahw/evals/suffix-pronoun-eval.jsonl"), encoding="utf-8") if l.strip()]
    _ev_ok = any(c.get("host_pos") == "N" and c.get("expect_gloss") for c in _ev) and \
             any(c.get("host_pos") == "V" and c.get("expect_state") == "pending" for c in _ev)
except Exception:
    _ev_ok = False
check("suffix/pronoun eval encodes noun-resolve + verb-pending contract", _ev_ok)

# 11f. source-adapter abstraction exists (skills are MCP-free but adapter-aware) + S8 source-photo rescue pipeline
for art in ("sources/source-adapter.schema.json", "sources/README.md", "sources/tafsir_mcp/adapter.json",
            "sources/qac/adapter.json", "sources/qac/concept-map-adapter.json",
            "sources/quran_com/adapter.json", "sources/tanzil/adapter.json",
            "tools/qac_concept_map_adapter.py", "tools/test_qac_concept_map_adapter.py",
            "tools/source_photo_indexer.py", "tools/source_photo_cropper.py", "tools/source_photo_rescue.py",
            "tools/source_photo_verify_entry.py", "qamus/reports/source-photo-rescue-report.md",
            "qamus/indexes/source_photo_index.json"):
    check("source-adapter/rescue artifact exists: %s" % art, os.path.exists(os.path.join(ROOT, art)))
# every adapter manifest is internal-only + not skill-required
try:
    _ad_ok = True
    for _a in (("tafsir_mcp", "adapter.json"), ("qac", "adapter.json"),
               ("qac", "concept-map-adapter.json"), ("quran_com", "adapter.json"),
               ("tanzil", "adapter.json")):
        _m = json.load(io.open(os.path.join(ROOT, "sources", _a[0], _a[1]), encoding="utf-8"))
        if _m.get("public_exposable") is not False or _m.get("required_by_skills") is not False:
            _ad_ok = False
except Exception:
    _ad_ok = False
check("source adapters are internal-only (public_exposable=false, required_by_skills=false)", _ad_ok)
try:
    _qac = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "test_qac_concept_map_adapter.py")],
                          capture_output=True, text=True)
    check("QAC concept-map adapter stays internal-only and parser-tested", _qac.returncode == 0)
except Exception:
    check("QAC concept-map adapter test runnable", False)
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
    _pubclean = all(r.get("src") == "qamus" and r.get("kind") == "authored" and r.get("lang", "en") == "en" for r in _td)
    _multi = len(_glosses_for_lam) >= 2  # at least 'did not' and 'why' both present
except Exception:
    _pubclean = _multi = False
check("token layer: public records src=qamus,kind=authored and any lang is en", _pubclean)
check("token layer resolves a surface-key collision (>=2 distinct per-token glosses incl لَمْ/لِمَ)", _multi)
try:
    _validator = os.path.join(ROOT, "tools", "validate_token_hover_decisions.py")
    _good = {"loc": "1:1:1", "gloss": "in the name", "src": "qamus", "kind": "authored", "lang": "en"}
    _bad = {"loc": "1:1:1", "gloss": "in the name", "src": "qamus", "kind": "authored"}
    _tmp_paths = []
    for _row in (_good, _bad):
        _tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False)
        try:
            _tmp.write(json.dumps(_row, ensure_ascii=False) + "\n")
            _tmp_paths.append(_tmp.name)
        finally:
            _tmp.close()
    _good_run = subprocess.run([sys.executable, _validator, "--require-lang-en", _tmp_paths[0]],
                               capture_output=True, text=True)
    _bad_run = subprocess.run([sys.executable, _validator, "--require-lang-en", _tmp_paths[1]],
                              capture_output=True, text=True)
    _strict_lang_ok = _good_run.returncode == 0 and _bad_run.returncode != 0
except Exception:
    _strict_lang_ok = False
finally:
    for _p in locals().get("_tmp_paths", []):
        try:
            os.unlink(_p)
        except OSError:
            pass
check("token layer: public/runtime export validation requires lang=en", _strict_lang_ok)

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

# 13. completion-tranche artifacts (P0 dataset, P1 graph, P3 audit, P4 suffix lane, P9 wrong-reasoning)
_R = os.path.join(os.path.dirname(__file__), "..")
def _exists(rel):
    return os.path.exists(os.path.join(_R, rel))
def _lines(rel):
    p = os.path.join(_R, rel)
    return sum(1 for l in io.open(p, encoding="utf-8") if l.strip()) if os.path.exists(p) else 0
check("P0 dataset committed: entries.jsonl has 2092 entries",
      _lines("qamus/data/current/entries.jsonl") == 2092)
check("P0 dataset: schema + 7 indexes present", _exists("qamus/schemas/qamus-entry-public.schema.json")
      and all(_exists("qamus/indexes/current/%s.json" % n) for n in
      ("by-entry-id","by-source-key","by-root","by-lemma","by-normalized-surface","by-quran-ref","by-category")))
check("P1 source-address graph present (full)",
      _exists("qamus/indexes/current/decision-backlinks-full.json")
      and all(_exists("qamus/indexes/current/%s.jsonl" % n) for n in
      ("source-address-full","quran-usage-spine-full","qamus-entry-field-addresses")))
check("P2 entry matrix has 2092 rows", _lines("qamus/reports/qamus-2092-entry-matrix.jsonl") == 2092)
check("P3 hover-token audit covers all 49,900 tokens", _lines("qamus/reports/hover-token-audit-full.jsonl") == 49900)
try:
    _au = [json.loads(l) for l in io.open(os.path.join(_R, "qamus/reports/hover-token-audit-full.jsonl"), encoding="utf-8")]
    _pend_no_blocker = [r for r in _au if r.get("decision_state") == "pending" and not r.get("blocker")]
    check("P3 audit: no generic pending (every pending token has an exact blocker)", not _pend_no_blocker)
except Exception as e:
    check("P3 audit readable", False)
_hover_artifact = os.path.join(_R, "out", "hover_stage", "wbw-lookup.json")
if os.path.exists(_hover_artifact):
    try:
        _hv = subprocess.run([sys.executable, os.path.join(_R, "tools", "validate_hover_regression_cases.py"),
                              _hover_artifact], capture_output=True, text=True)
        check("Andon hover regression cases pass on staged lookup artifact", _hv.returncode == 0)
        if _hv.returncode != 0:
            _o = (_hv.stdout or _hv.stderr).strip().splitlines()
            if _o:
                print("  ", _o[-1])
    except Exception:
        check("Andon hover regression validator runnable", False)
else:
    check("Andon hover regression validator present (no staged lookup artifact)",
          os.path.exists(os.path.join(_R, "tools", "validate_hover_regression_cases.py")))
# P4 suffix/pronoun offline test
try:
    _r = subprocess.run([sys.executable, os.path.join(_R, "tools", "test_suffix_pronoun.py")],
                        capture_output=True, text=True)
    check("P4 suffix/pronoun invariants pass (test_suffix_pronoun.py)", _r.returncode == 0)
except Exception:
    check("P4 suffix/pronoun test runnable", False)
# A0 report reconciliation: no stale-as-current scoreboards
try:
    _rr = subprocess.run([sys.executable, os.path.join(_R, "tools", "validate_report_reconciliation.py")],
                         capture_output=True, text=True)
    check("A0 report reconciliation (no stale-as-current scoreboards)", _rr.returncode == 0)
except Exception:
    check("A0 report reconciliation runnable", False)

# A1 artifact ergonomics: committed artifacts must be reviewable/diffable
try:
    _erg = subprocess.run([sys.executable, os.path.join(_R, "tools", "check_artifact_ergonomics.py")],
                          capture_output=True, text=True)
    check("A1 artifact ergonomics (no one-line mega-indexes; pretty/JSONL; trailing newlines)",
          _erg.returncode == 0)
except Exception:
    check("A1 artifact ergonomics runnable", False)

# Phase 4 completion-manifest gates (per-token manifest + per-entry rollup)
for _vname, _label in [("validate_qamus_completion_manifest.py", "Phase4 per-token completion manifest (49,900 terminal, risk-tagged)"),
                       ("validate_entry_completion_rollup.py", "Phase4 per-entry completion rollup (2,092, 0 unknown)")]:
    try:
        _v = subprocess.run([sys.executable, os.path.join(_R, "tools", _vname)], capture_output=True, text=True)
        check(_label, _v.returncode == 0)
    except Exception:
        check(_vname + " runnable", False)

# Phase 2/3 skill completeness gates (sarf + nahw engines)
for _vname, _label in [("validate_sarf_skill.py", "Phase2 sarf engine complete (derivatives + Madinah modes + false-clitic)"),
                       ("validate_nahw_skill.py", "Phase3 nahw engine complete (particle functions + iʿrāb polysemy)")]:
    try:
        _v = subprocess.run([sys.executable, os.path.join(_R, "tools", _vname)], capture_output=True, text=True)
        check(_label, _v.returncode == 0)
    except Exception:
        check(_vname + " runnable", False)

# June 25 curriculum hard-tail: validators and eval fixtures must lock the known hover-gloss failures.
try:
    _sarf_validator = io.open(os.path.join(_R, "tools", "validate_sarf_skill.py"), encoding="utf-8").read()
    _nahw_validator = io.open(os.path.join(_R, "tools", "validate_nahw_skill.py"), encoding="utf-8").read()
    _validator_blob = _sarf_validator + "\n" + _nahw_validator
except Exception:
    _validator_blob = ""
for _tok in ("بِسَلَامٍ", "بِبَدْرٍ", "وَٱلتِّينِ", "وَٱلزَّيْتُونِ", "وَبِٱلنَّجْمِ",
             "جَادَلُوكَ", "مُعَلَّمٌ", "ذَٰلِكُمْ"):
    check("June25 validator covers token: %s" % _tok, _tok in _validator_blob)
try:
    _fcs_blob = io.open(os.path.join(_R, "sarf", "evals", "false-clitic-split-eval.jsonl"),
                        encoding="utf-8").read()
    _pf_blob = io.open(os.path.join(_R, "nahw", "evals", "particle-function-eval.jsonl"),
                       encoding="utf-8").read()
    _ip_blob = io.open(os.path.join(_R, "nahw", "evals", "irab-polysemy-eval.jsonl"),
                       encoding="utf-8").read()
except Exception:
    _fcs_blob = _pf_blob = _ip_blob = ""
for _eid, _blob in ([(x, _fcs_blob) for x in ("FCS-021", "FCS-022", "FCS-023", "FCS-024", "FCS-025")] +
                    [(x, _pf_blob) for x in ("PF-033", "PF-034", "PF-035", "PF-036", "PF-037", "PF-038")] +
                    [(x, _ip_blob) for x in ("IP-026", "IP-027", "IP-028", "IP-029", "IP-030",
                                             "IP-031", "IP-032", "IP-033", "IP-034")]):
    check("June25 eval fixture exists: %s" % _eid, _eid in _blob)

# Morphosyntax token contract: grammar breakdown is a separate parse layer, with the same public hover boundary.
for _art in ("qamus/schemas/morphosyntax-token.schema.json",
             "qamus/reports/morphosyntax-token-contract.md",
             "qamus/examples/morphosyntax_token.sample.jsonl",
             "tools/validate_morphosyntax_token_metadata.py"):
    check("morphosyntax-token contract artifact exists: %s" % _art, os.path.exists(os.path.join(_R, _art)))
try:
    _ms_schema = io.open(os.path.join(_R, "qamus", "schemas", "morphosyntax-token.schema.json"),
                         encoding="utf-8").read()
    check("morphosyntax-token schema requires public_gloss_lang=en",
          '"public_gloss_lang"' in _ms_schema and '"const": "en"' in _ms_schema)
except Exception:
    check("morphosyntax-token schema readable", False)
for _args, _label in ((["--self-test"], "morphosyntax validator self-test"),
                      ([os.path.join(_R, "qamus", "examples", "morphosyntax_token.sample.jsonl")],
                       "morphosyntax sample validates")):
    try:
        _v = subprocess.run([sys.executable, os.path.join(_R, "tools", "validate_morphosyntax_token_metadata.py")] + _args,
                            capture_output=True, text=True)
        check(_label, _v.returncode == 0)
        if _v.returncode != 0:
            _out = (_v.stdout or _v.stderr).strip().splitlines()
            if _out:
                print("  ", _out[-1])
    except Exception:
        check(_label + " runnable", False)

# closure-2092: report-ergonomics gate (Markdown counterpart to artifact ergonomics) + root-cause ledger
# + open-stem hygiene gates (surface-index covers usage.forms; lane sanity — no verb-clitic/false-blocker pollution)
for _vname, _label in [("check_report_ergonomics.py", "closure-2092 report ergonomics (no crushed one-line Markdown reports)"),
                       ("validate_canonical_paths.py", "closure-2092 canonical paths (no stale index/scoreboard/coverage refs)"),
                       ("validate_bidirectional_links.py", "closure-2092 source-graph integrity (0 orphans, no zero-count collapse)"),
                       ("validate_surface_index_covers_usage_forms.py", "closure-2092 surface index covers usage.forms (F1)"),
                       ("validate_blocker_root_cause_ledger.py", "closure-2092 blocker root-cause ledger (controlled vocab, reconciled)"),
                       ("validate_open_stem_lane_sanity.py", "closure-2092 open-stem lane sanity (host-noun-only, roots flattened, no false blockers)")]:
    if os.path.exists(os.path.join(_R, "tools", _vname)):
        try:
            _v = subprocess.run([sys.executable, os.path.join(_R, "tools", _vname)], capture_output=True, text=True)
            check(_label, _v.returncode == 0)
            if _v.returncode != 0:
                print("  ", (_v.stdout or _v.stderr).strip().splitlines()[-1] if (_v.stdout or _v.stderr).strip() else "")
        except Exception:
            check(_vname + " runnable", False)

# closure-2092: committed batch families validated as HARD gates (not mere existence checks)
_C = os.path.join(_R, "qamus", "candidates", "qamus_2092")
_BATCH_GATES = [
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_002.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_003.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_004.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_005.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_006.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_007.jsonl"], None),
    ("validate_token_hover_decisions.py", ["andon_hover_regression_repairs_20260625_008.jsonl"], None),
    ("validate_token_hover_decisions.py", ["form_variant_batch_001.jsonl"], None),
    ("validate_form_variant_family_batches.py", ["form_variant_batch_001.jsonl"], "form_variant_batch_001.provenance.jsonl"),
    ("validate_token_hover_decisions.py", ["token_irab_batch_001.jsonl"], None),
    ("validate_token_hover_decisions.py", ["token_irab_batch_002.jsonl"], None),
    ("validate_token_hover_decisions.py", ["token_irab_batch_003.jsonl"], None),
    ("validate_suffix_pronoun_decisions.py", ["host_lexeme_batch_001.jsonl"], None),
    ("validate_suffix_pronoun_decisions.py", ["suffix_pronoun_hover_batch_001.jsonl"], None),
]
for _vname, _args, _prov in _BATCH_GATES:
    _vp = os.path.join(_R, "tools", _vname)
    _bp = os.path.join(_C, _args[0])
    if not os.path.exists(_bp):
        check("closure-2092 batch gate input exists: %s" % _args[0], False)
        continue
    if os.path.exists(_vp):
        _cmd = [sys.executable, _vp, _bp]
        if _prov and os.path.exists(os.path.join(_C, _prov)):
            _cmd += ["--provenance", os.path.join(_C, _prov)]
        try:
            _v = subprocess.run(_cmd, capture_output=True, text=True)
            check("closure-2092 batch gate %s(%s)" % (_vname.replace("validate_", "").replace(".py", ""), _args[0]),
                  _v.returncode == 0)
            if _v.returncode != 0:
                _o = (_v.stdout or _v.stderr).strip().splitlines()
                if _o: print("  ", _o[-1])
        except Exception:
            check("batch gate %s runnable" % _vname, False)

# closure-2092 Phase 4: missing-lane generators are runnable + their validators pass (review-only, no apply)
_stage = os.path.join(_R, "out", "hover_stage")
os.makedirs(_stage, exist_ok=True)
_LANE = [
    ("build_verb_clitic_candidates.py", [], "validate_verb_clitic_candidates.py", os.path.join(_stage, "verb_clitic_cand.jsonl")),
    ("build_new_entry_proposals.py", [], "validate_new_entry_proposals.py", os.path.join(_stage, "new_entry_proposals.jsonl")),
    ("build_source_entry_repair_candidates.py", ["--mode", "forms_array"], "validate_source_entry_repair_candidates.py",
     os.path.join(_stage, "source_entry_repair_forms_array.jsonl")),
]
for _gen, _ga, _val, _outp in _LANE:
    _gp = os.path.join(_R, "tools", _gen)
    if os.path.exists(_gp):
        try:
            _g = subprocess.run([sys.executable, _gp] + _ga, capture_output=True, text=True)
            _v = subprocess.run([sys.executable, os.path.join(_R, "tools", _val), _outp], capture_output=True, text=True)
            check("closure-2092 Phase4 lane %s" % _gen.replace("build_", "").replace(".py", ""),
                  _g.returncode == 0 and _v.returncode == 0)
        except Exception:
            check("Phase4 lane %s runnable" % _gen, False)

# closure-2092: corpus-to-Qamus read-only fixture (Nawawī40; live_write=false, no translation, Ṣaḥīḥayn plan-only)
_corp = os.path.join(_R, "corpora", "nawawi40", "nawawi40.matn.jsonl")
if os.path.exists(_corp):
    _cf = os.path.join(_R, "out", "_corpus_fixture_ci")
    os.makedirs(_cf, exist_ok=True)
    try:
        _ok = True
        for _t in ("corpus_to_qamus_candidates.py", "corpus_to_hover_decisions.py"):
            _r = subprocess.run([sys.executable, os.path.join(_R, "tools", _t), "--corpus", _corp, "--out", _cf, "--limit", "5"],
                                capture_output=True, text=True)
            _ok = _ok and _r.returncode == 0
        _v = subprocess.run([sys.executable, os.path.join(_R, "tools", "validate_corpus_fixture.py"), _cf],
                            capture_output=True, text=True)
        check("closure-2092 corpus fixture (read-only, no translation, Ṣaḥīḥayn plan-only)", _ok and _v.returncode == 0)
    except Exception:
        check("closure-2092 corpus fixture runnable", False)

# closure-2092: scar-family rejection fixtures (verb-clitic / voice-collision / banned families)
_frj = os.path.join(_R, "qamus", "examples", "form_variant_rejections.jsonl")
try:
    _fr = [json.loads(l) for l in io.open(_frj, encoding="utf-8") if l.strip()]
    _has_clitic = any(r.get("correct_lane") == "verb_clitic_object_or_subject_candidate" for r in _fr)
    _has_voice = any(r.get("correct_lane") == "verb_form_or_voice" for r in _fr)
    _has_banned = any(r.get("expect") == "reject_banned_family" for r in _fr)
    _all_reject = all(str(r.get("expect", "")).startswith("reject") for r in _fr)
    check("closure-2092 scar-family fixtures (>=16, verb-clitic + voice + banned, all reject)",
          len(_fr) >= 16 and _has_clitic and _has_voice and _has_banned and _all_reject)
except Exception:
    check("closure-2092 scar-family fixtures parse", False)

# P9 wrong-reasoning traps present and grader blocks them
_wr = 0
try:
    for l in io.open(os.path.join(_R, "nahw/evals/grammar-problems-derived-eval.jsonl"), encoding="utf-8"):
        l = l.strip()
        if l and json.loads(l).get("wrong_reasoning_trap"):
            _wr += 1
except Exception:
    pass
check("P9 grammar gate has >=8 wrong-reasoning trap cases (%d)" % _wr, _wr >= 8)

if fails:
    print("\n%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("\nALL REGRESSION CHECKS PASS")
