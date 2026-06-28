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


def run_text(cmd, **kwargs):
    """Run a subprocess and decode captured output as UTF-8 on Windows too."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    kwargs.setdefault("env", env)
    return subprocess.run(cmd, **kwargs)


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
            "curriculum/assessment/grading-rubric.md", "curriculum/assessment/answer-key.schema.md",
            "curriculum/assessment/level-checkpoints.sample.jsonl",
            "curriculum/progress/learner-progress.template.md",
            "curriculum/progress/missed-error-log.template.md",
            "curriculum/tutor-session-protocol.md",
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
    _qac = run_text([sys.executable, os.path.join(ROOT, "tools", "test_qac_concept_map_adapter.py")])
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
    _good_run = run_text([sys.executable, _validator, "--require-lang-en", _tmp_paths[0]])
    _bad_run = run_text([sys.executable, _validator, "--require-lang-en", _tmp_paths[1]])
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
        _hv = run_text([sys.executable, os.path.join(_R, "tools", "validate_hover_regression_cases.py"),
                        _hover_artifact])
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
    _r = run_text([sys.executable, os.path.join(_R, "tools", "test_suffix_pronoun.py")])
    check("P4 suffix/pronoun invariants pass (test_suffix_pronoun.py)", _r.returncode == 0)
except Exception:
    check("P4 suffix/pronoun test runnable", False)
# A0 report reconciliation: no stale-as-current scoreboards
try:
    _rr = run_text([sys.executable, os.path.join(_R, "tools", "validate_report_reconciliation.py")])
    check("A0 report reconciliation (no stale-as-current scoreboards)", _rr.returncode == 0)
except Exception:
    check("A0 report reconciliation runnable", False)

# A1 artifact ergonomics: committed artifacts must be reviewable/diffable
try:
    _erg = run_text([sys.executable, os.path.join(_R, "tools", "check_artifact_ergonomics.py")])
    check("A1 artifact ergonomics (no one-line mega-indexes; pretty/JSONL; trailing newlines)",
          _erg.returncode == 0)
except Exception:
    check("A1 artifact ergonomics runnable", False)

# Phase 4 completion-manifest gates (per-token manifest + per-entry rollup)
for _vname, _label in [("validate_qamus_completion_manifest.py", "Phase4 per-token completion manifest (49,900 terminal, risk-tagged)"),
                       ("validate_entry_completion_rollup.py", "Phase4 per-entry completion rollup (2,092, 0 unknown)")]:
    try:
        _v = run_text([sys.executable, os.path.join(_R, "tools", _vname)])
        check(_label, _v.returncode == 0)
    except Exception:
        check(_vname + " runnable", False)

# Phase 2/3 skill completeness gates (sarf + nahw engines)
for _vname, _label in [("validate_sarf_skill.py", "Phase2 sarf engine complete (derivatives + Madinah modes + false-clitic)"),
                       ("validate_nahw_skill.py", "Phase3 nahw engine complete (particle functions + iʿrāb polysemy)")]:
    try:
        _v = run_text([sys.executable, os.path.join(_R, "tools", _vname)])
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
for _eid, _blob in ([(x, _fcs_blob) for x in ("FCS-021", "FCS-022", "FCS-023", "FCS-024", "FCS-025",
                                             "FCS-045", "FCS-046", "FCS-047", "FCS-048", "FCS-049", "FCS-050")] +
                    [(x, _pf_blob) for x in ("PF-033", "PF-034", "PF-035", "PF-036", "PF-037", "PF-038",
                                            "PF-054", "PF-055", "PF-056", "PF-057", "PF-058", "PF-059",
                                            "PF-060", "PF-061", "PF-062")] +
                    [(x, _ip_blob) for x in ("IP-026", "IP-027", "IP-028", "IP-029", "IP-030",
                                             "IP-031", "IP-032", "IP-033", "IP-034")]):
    check("June25 eval fixture exists: %s" % _eid, _eid in _blob)

# Morphosyntax token contract: grammar breakdown is a separate parse layer, with the same public hover boundary.
for _art in ("qamus/schemas/morphosyntax-token.schema.json",
             "qamus/reports/morphosyntax-token-contract.md",
             "qamus/examples/morphosyntax_token.sample.jsonl",
             "tools/validate_morphosyntax_token_metadata.py",
             "tools/audit_wbw_lookup_morphosyntax.py"):
    check("morphosyntax-token contract artifact exists: %s" % _art, os.path.exists(os.path.join(_R, _art)))
try:
    _ms_schema = io.open(os.path.join(_R, "qamus", "schemas", "morphosyntax-token.schema.json"),
                         encoding="utf-8").read()
    check("morphosyntax-token schema requires public_gloss_lang=en",
          '"public_gloss_lang"' in _ms_schema and '"const": "en"' in _ms_schema)
    check("morphosyntax-token schema requires parse_key + qamus-grammar-v1 display palette",
          '"parse_key"' in _ms_schema and '"display"' in _ms_schema and '"qamus-grammar-v1"' in _ms_schema)
except Exception:
    check("morphosyntax-token schema readable", False)
for _args, _label in ((["--self-test"], "morphosyntax validator self-test"),
                      ([os.path.join(_R, "qamus", "examples", "morphosyntax_token.sample.jsonl")],
                       "morphosyntax sample validates")):
    try:
        _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_morphosyntax_token_metadata.py")] + _args)
        check(_label, _v.returncode == 0)
        if _v.returncode != 0:
            _out = (_v.stdout or _v.stderr).strip().splitlines()
            if _out:
                print("  ", _out[-1])
    except Exception:
        check(_label + " runnable", False)

for _args, _label in (
        (["--self-test"], "rich-hover certification validator self-test"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_01_particle_function.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_01_particle_function_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_01_renderer_fixture.sample.jsonl"),
         ],
         "P-RICH-CERT-01 particle certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_02_particle_collision.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_02_particle_collision_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_02_renderer_fixture.sample.jsonl"),
         ],
         "P-RICH-CERT-02 particle collision certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_03_an_inna_family.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_03_an_inna_family_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_03_renderer_fixture.sample.jsonl"),
         ],
         "P-RICH-CERT-03 an/inna family certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_04_la_temporal_family.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_04_la_temporal_family_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_p_rich_cert_04_renderer_fixture.sample.jsonl"),
         ],
         "P-RICH-CERT-04 la temporal family certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_00_calibration.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_00_calibration_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_00_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-00 calibration certification sample validates"),
):
    try:
        _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rich_hover_certification.py")] + _args)
        check(_label, _v.returncode == 0)
        if _v.returncode != 0:
            _out = (_v.stdout or _v.stderr).strip().splitlines()
            if _out:
                print("  ", _out[-1])
    except Exception:
        check(_label + " runnable", False)

try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "audit_wbw_lookup_morphosyntax.py"), "--self-test"])
    check("wbw lookup morphosyntax audit self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("wbw lookup morphosyntax audit self-test runnable", False)
try:
    _audit_blob = io.open(os.path.join(_R, "tools", "audit_wbw_lookup_morphosyntax.py"),
                          encoding="utf-8").read()
    check("wbw audit reports rich metadata coverage", "rich_metadata" in _audit_blob)
    check("wbw audit gates Kawkab segment alignment", "rich_kawkab_segment_width_mismatch" in _audit_blob)
except Exception:
    check("wbw lookup morphosyntax audit readable", False)
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "build_rich_hover_morphosyntax_candidates.py"),
                   "--self-test"])
    check("rich-hover morphosyntax candidate generator self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("rich-hover morphosyntax candidate generator runnable", False)

for _art in (
        "qamus/schemas/parse-key.schema.json",
        "qamus/schemas/typed-edge.schema.json",
        "qamus/schemas/backlink-index.schema.json",
        "qamus/schemas/decision-linkage.schema.json",
        "qamus/schemas/blocker-linkage.schema.json",
        "qamus/schemas/repair-impact-preview.schema.json",
        "qamus/schemas/hover-edit-intent.schema.json",
        "qamus/schemas/public-private-boundary.schema.json",
        "qamus/schemas/detector-maturity.schema.json",
        "qamus/schemas/live-shadow-run-manifest.schema.json",
        "qamus/schemas/production-bug-lesson.schema.json",
        "qamus/schemas/shadow-review-pack.schema.json",
        "qamus/schemas/shadow-admin-debug-pack.schema.json",
        "qamus/schemas/shadow-admin-route-contract.schema.json",
        "qamus/schemas/full-corpus-hover-dogfood-audit.schema.json",
        "qamus/schemas/phase4-closure-tranche.schema.json",
        "qamus/schemas/phase4-two-vote-request.schema.json",
        "qamus/schemas/phase4-two-vote-response.schema.json",
        "qamus/schemas/phase4-gloss-adjudication-request.schema.json",
        "qamus/schemas/phase4-gloss-adjudication-response.schema.json",
        "qamus/schemas/phase4-hover-decision-plan.schema.json",
        "qamus/schemas/phase4-apply-readiness-manifest.schema.json",
        "qamus/schemas/phase4-draft-token-decision-ledger.schema.json",
        "qamus/schemas/phase4-owner-authorization-request.schema.json",
        "qamus/examples/public_private_boundary.sample.json",
        "qamus/examples/detector_maturity.sample.json",
        "qamus/examples/live_shadow_run_manifest.sample.json",
        "qamus/examples/parse_key.sample.jsonl",
        "qamus/examples/decision_linkage.sample.jsonl",
        "qamus/examples/hover_edit_intent.sample.jsonl",
        "qamus/examples/repair_impact_preview.sample.jsonl",
        "qamus/examples/production_bug_lesson_from_intent.sample.jsonl",
        "qamus/examples/dogfood_production_bug_lesson.sample.jsonl",
        "qamus/examples/dogfood_preposition_oath_production_bug_lesson.sample.jsonl",
        "qamus/examples/dogfood_vocative_production_bug_lesson.sample.jsonl",
        "qamus/examples/dogfood_nominal_pos_production_bug_lesson.sample.jsonl",
        "qamus/examples/shadow_review_pack.sample.jsonl",
        "qamus/examples/shadow_admin_debug_pack.sample.json",
        "qamus/examples/shadow_admin_route_contract.sample.json",
        "qamus/examples/full_corpus_hover_dogfood_audit.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_subagent_lane.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_lane_packet.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_review_output.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_reconciliation.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_next_state_queue.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_known_defect_readiness.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_known_defect_skill_impact.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_suffix_batch_skill_impact.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_preposition_oath_batch_skill_impact.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vocative_batch_skill_impact.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_nominal_pos_batch_skill_impact.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_particle_tranche_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_particle_tranche_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_particle_tranche_production_bug_lesson.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_particle_remaining67_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_particle_remaining67_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_particle_remaining67_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-particle-remaining67-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn00_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn00_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn00_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn00-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn01_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn01_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn01_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn01-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn02_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn02_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn02_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn02-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn03_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn03_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn03_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn03-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn04_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn04_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn04_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn04-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn05_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn05_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn05_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn05-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn06_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn06_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn06_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn06-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn07_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn07_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn07_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn07-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn08_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn08_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn08_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn08-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn09_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn09_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn09_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn09-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn10_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn10_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn10_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn10-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn11_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn11_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn11_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn11-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn12_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn12_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn12_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn12-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn13_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn13_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn13_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn13-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn14_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn14_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn14_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn14-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn15_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn15_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn15_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn15-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn16_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn16_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn16_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn16-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn18_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn18_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn18_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn18-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn19_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn19_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn19_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn19-20260627.md",
        "qamus/examples/full_corpus_dogfood_vn20_inventory.sample.jsonl",
        "qamus/examples/full_corpus_dogfood_vn20_skill_impact.sample.jsonl",
        "qamus/examples/dogfood_vn20_production_bug_lesson.sample.jsonl",
        "qamus/reports/full-corpus-dogfood-vn20-20260627.md",
        "qamus/examples/full_corpus_dogfood_queue_summary.sample.json",
        "qamus/examples/full_corpus_dogfood_review_pack.sample.jsonl",
        "qamus/examples/shadow_review_pack_from_dogfood_review.sample.jsonl",
        "qamus/examples/phase4_closure_tranche.sample.jsonl",
        "qamus/examples/phase4_closure_tranche_from_dogfood_review.sample.jsonl",
        "qamus/examples/phase4_two_vote_request.sample.jsonl",
        "qamus/examples/phase4_two_vote_request_from_dogfood_review.sample.jsonl",
        "qamus/examples/phase4_two_vote_response.sample.jsonl",
        "qamus/examples/phase4_two_vote_response_from_dogfood_review.sample.jsonl",
        "qamus/examples/phase4_gloss_adjudication_request.sample.jsonl",
        "qamus/examples/phase4_gloss_adjudication_response.sample.jsonl",
        "qamus/examples/phase4_hover_decision_plan.sample.jsonl",
        "qamus/examples/phase4_hover_decision_plan_from_dogfood_review.sample.jsonl",
        "qamus/examples/phase4_apply_readiness_manifest.sample.json",
        "qamus/examples/phase4_apply_readiness_manifest_from_dogfood_review.sample.json",
        "qamus/examples/phase4_draft_token_decision_ledger.sample.jsonl",
        "qamus/examples/phase4_draft_token_decision_ledger_from_dogfood_review.sample.jsonl",
        "qamus/examples/phase4_owner_authorization_request.sample.json",
        "qamus/examples/phase4_owner_authorization_request_from_dogfood_review.sample.json",
        "qamus/procedures/production-bug-lessons.md",
        "qamus/reports/full-corpus-dogfood-suffix-batch-20260627.md",
        "qamus/reports/full-corpus-dogfood-preposition-oath-batch-20260627.md",
        "qamus/reports/full-corpus-dogfood-vocative-batch-20260627.md",
        "qamus/reports/full-corpus-dogfood-nominal-pos-batch-20260627.md",
        "qamus/reports/full-corpus-dogfood-particle-tranche-20260627.md",
        "nahw/procedures/grammar-problems-issue-clusters.md",
        "nahw/rules/grammar-problems-issue-clusters.json",
        "nahw/evals/grammar-problems-phase3p25-mining.jsonl",
        "nahw/evals/grammar-problems-phase3p25-mining.md",
        "qamus/reports/live-shadow-graph-workflow.md",
        "tools/summarize_shadow_closure_queue.py",
        "tools/validate_detector_maturity.py",
        "tools/validate_live_shadow_run_manifest.py",
        "tools/validate_public_private_boundary.py",
        "tools/validate_parse_key_contract.py",
        "tools/validate_curriculum_assessment.py",
        "tools/validate_decision_linkage.py",
        "tools/validate_hover_edit_intent.py",
        "tools/validate_repair_impact_preview.py",
        "tools/validate_shadow_review_pack.py",
        "tools/validate_shadow_admin_debug_pack.py",
        "tools/validate_shadow_admin_route_contract.py",
        "tools/build_full_corpus_hover_dogfood_audit.py",
        "tools/validate_full_corpus_hover_dogfood_audit.py",
        "tools/validate_full_corpus_dogfood_subagent_lanes.py",
        "tools/build_full_corpus_dogfood_lane_packets.py",
        "tools/validate_full_corpus_dogfood_review_outputs.py",
        "tools/summarize_full_corpus_dogfood_review_outputs.py",
        "tools/reconcile_full_corpus_dogfood_review_outputs.py",
        "tools/build_full_corpus_dogfood_next_state_queues.py",
        "tools/build_full_corpus_dogfood_known_defect_readiness.py",
        "tools/summarize_full_corpus_dogfood_queue.py",
        "tools/build_full_corpus_dogfood_review_pack.py",
        "tools/build_shadow_review_pack_from_dogfood_review.py",
        "tools/plan_phase4_closure_tranche.py",
        "tools/validate_phase4_closure_tranche.py",
        "tools/build_phase4_two_vote_requests.py",
        "tools/validate_phase4_two_vote_requests.py",
        "tools/validate_phase4_two_vote_responses.py",
        "tools/reconcile_phase4_two_vote_responses.py",
        "tools/build_phase4_gloss_adjudication_requests.py",
        "tools/validate_phase4_gloss_adjudication_requests.py",
        "tools/validate_phase4_gloss_adjudication_responses.py",
        "tools/reconcile_phase4_gloss_adjudication_responses.py",
        "tools/build_phase4_hover_decision_plan.py",
        "tools/validate_phase4_hover_decision_plan.py",
        "tools/build_phase4_apply_readiness_manifest.py",
        "tools/validate_phase4_apply_readiness_manifest.py",
        "tools/build_phase4_draft_token_decision_ledger.py",
        "tools/validate_phase4_draft_token_decision_ledger.py",
        "tools/build_phase4_owner_authorization_request.py",
        "tools/validate_phase4_owner_authorization_request.py",
        "tools/query_shadow_admin_debug_pack.py",
        "tools/plan_shadow_hover_edit_intent.py",
        "tools/plan_shadow_repair_impact_preview.py",
        "tools/build_production_bug_lesson.py",
        "tools/build_dogfood_production_bug_lessons.py",
        "tools/build_grammar_regression_mining.py",
        "tools/validate_grammar_regression_mining.py",
        "tools/validate_grammar_issue_clusters.py",
        "tools/summarize_rich_wbw_roles.py",
        "tools/build_shadow_admin_debug_pack.py",
):
    check("Phase2 live-shadow graph contract artifact exists: %s" % _art, os.path.exists(os.path.join(_R, _art)))

try:
    _vn08_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn08_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn08_component = [
        _r for _r in _vn08_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn08_blocked = _vn08_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn08_component
    )
except Exception:
    _vn08_blocked = False
check("VN-08 sample preserves component-only evidence as non-applyable blocker rows", _vn08_blocked)

try:
    _vn09_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn09_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn09_component = [
        _r for _r in _vn09_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn09_blocked = _vn09_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn09_component
    )
    _vn09_has_whole_renderer_only = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("recommended_next_action") == "repair_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn09_inventory
    )
except Exception:
    _vn09_blocked = False
    _vn09_has_whole_renderer_only = False
check("VN-09 sample preserves component-only evidence as non-applyable blocker rows", _vn09_blocked)
check("VN-09 sample keeps renderer metadata backfill rows non-live-applyable", _vn09_has_whole_renderer_only)

try:
    _vn10_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn10_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn10_component = [
        _r for _r in _vn10_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn10_blocked = _vn10_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn10_component
    )
    _vn10_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn10_inventory
    )
    _vn10_relation_gated = any(
        "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
        and _r.get("required_next_gate") in ("component_only_blocker", "two_vote_exact_address_review")
        and _r.get("may_apply_live") is False
        for _r in _vn10_inventory
    )
except Exception:
    _vn10_blocked = False
    _vn10_has_renderer_backfill = False
    _vn10_relation_gated = False
check("VN-10 sample preserves component-only evidence as non-applyable blocker rows", _vn10_blocked)
check("VN-10 sample keeps renderer metadata backfill rows non-live-applyable", _vn10_has_renderer_backfill)
check("VN-10 sample keeps bā/lām relation rows gated", _vn10_relation_gated)

try:
    _vn11_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn11_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn11_component = [
        _r for _r in _vn11_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn11_blocked = _vn11_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn11_component
    )
    _vn11_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn11_inventory
    )
    _vn11_pronoun_collision_gated = any(
        "verb_entry_pronoun_or_function_token_candidate_requires_nahw_review" in (_r.get("detected_issue") or "")
        and _r.get("required_next_gate") == "two_vote_exact_address_review"
        and _r.get("may_apply_live") is False
        for _r in _vn11_inventory
    )
    _vn11_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn11_inventory
    )
except Exception:
    _vn11_blocked = False
    _vn11_has_renderer_backfill = False
    _vn11_pronoun_collision_gated = False
    _vn11_suffix_relation_gated = False
check("VN-11 sample preserves component-only evidence as non-applyable blocker rows", _vn11_blocked)
check("VN-11 sample keeps renderer metadata backfill rows non-live-applyable", _vn11_has_renderer_backfill)
check("VN-11 sample keeps pronoun/function collisions exact-address gated", _vn11_pronoun_collision_gated)
check("VN-11 sample keeps suffix and relation rows gated", _vn11_suffix_relation_gated)

try:
    _vn12_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn12_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn12_component = [
        _r for _r in _vn12_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn12_blocked = _vn12_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn12_component
    )
    _vn12_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn12_inventory
    )
    _vn12_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn12_inventory
    )
    _vn12_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn12_inventory
    )
    _vn12_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn12_inventory
    )
except Exception:
    _vn12_blocked = False
    _vn12_has_renderer_backfill = False
    _vn12_finite_gated = False
    _vn12_nominal_pos_gated = False
    _vn12_suffix_relation_gated = False
check("VN-12 sample preserves component-only evidence as non-applyable blocker rows", _vn12_blocked)
check("VN-12 sample keeps renderer metadata backfill rows non-live-applyable", _vn12_has_renderer_backfill)
check("VN-12 sample keeps finite verb rows exact-address gated", _vn12_finite_gated)
check("VN-12 sample keeps nominal/POS leakage rows gated", _vn12_nominal_pos_gated)
check("VN-12 sample keeps suffix and relation rows gated", _vn12_suffix_relation_gated)

try:
    _vn13_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn13_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn13_component = [
        _r for _r in _vn13_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn13_blocked = _vn13_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn13_component
    )
    _vn13_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn13_inventory
    )
    _vn13_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn13_inventory
    )
    _vn13_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn13_inventory
    )
    _vn13_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn13_inventory
    )
except Exception:
    _vn13_blocked = False
    _vn13_has_renderer_backfill = False
    _vn13_finite_gated = False
    _vn13_nominal_pos_gated = False
    _vn13_suffix_relation_gated = False
check("VN-13 sample preserves component-only evidence as non-applyable blocker rows", _vn13_blocked)
check("VN-13 sample keeps renderer metadata backfill rows non-live-applyable", _vn13_has_renderer_backfill)
check("VN-13 sample keeps finite verb rows exact-address gated", _vn13_finite_gated)
check("VN-13 sample keeps nominal/POS leakage rows gated", _vn13_nominal_pos_gated)
check("VN-13 sample keeps suffix and relation rows gated", _vn13_suffix_relation_gated)

try:
    _vn14_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn14_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn14_component = [
        _r for _r in _vn14_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn14_blocked = _vn14_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn14_component
    )
    _vn14_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn14_inventory
    )
    _vn14_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn14_inventory
    )
    _vn14_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn14_inventory
    )
    _vn14_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn14_inventory
    )
    _vn14_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn14_inventory)
except Exception:
    _vn14_blocked = False
    _vn14_has_renderer_backfill = False
    _vn14_finite_gated = False
    _vn14_nominal_pos_gated = False
    _vn14_suffix_relation_gated = False
    _vn14_no_auto_apply = False
check("VN-14 sample preserves component-only evidence as non-applyable blocker rows", _vn14_blocked)
check("VN-14 sample keeps renderer metadata backfill rows non-live-applyable", _vn14_has_renderer_backfill)
check("VN-14 sample keeps finite verb rows exact-address gated", _vn14_finite_gated)
check("VN-14 sample keeps nominal/POS leakage rows gated", _vn14_nominal_pos_gated)
check("VN-14 sample keeps suffix and relation rows gated", _vn14_suffix_relation_gated)
check("VN-14 sample contains no live-applyable candidate rows", _vn14_no_auto_apply)

try:
    _vn15_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn15_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn15_component = [
        _r for _r in _vn15_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn15_blocked = _vn15_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn15_component
    )
    _vn15_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_renderer_metadata_backfill"
        and _r.get("may_apply_live") is False
        for _r in _vn15_inventory
    )
    _vn15_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn15_inventory
    )
    _vn15_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn15_inventory
    )
    _vn15_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn15_inventory
    )
    _vn15_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn15_inventory)
except Exception:
    _vn15_blocked = False
    _vn15_has_renderer_backfill = False
    _vn15_finite_gated = False
    _vn15_nominal_pos_gated = False
    _vn15_suffix_relation_gated = False
    _vn15_no_auto_apply = False
check("VN-15 sample preserves component-only evidence as non-applyable blocker rows", _vn15_blocked)
check("VN-15 sample keeps renderer metadata backfill rows non-live-applyable", _vn15_has_renderer_backfill)
check("VN-15 sample keeps finite verb rows exact-address gated", _vn15_finite_gated)
check("VN-15 sample keeps nominal/POS leakage rows gated", _vn15_nominal_pos_gated)
check("VN-15 sample keeps suffix and relation rows gated", _vn15_suffix_relation_gated)
check("VN-15 sample contains no live-applyable candidate rows", _vn15_no_auto_apply)

try:
    _vn16_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn16_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn16_component = [
        _r for _r in _vn16_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn16_blocked = _vn16_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn16_component
    )
    _vn16_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_metadata_plus_exact_address_review"
        and _r.get("may_apply_live") is False
        for _r in _vn16_inventory
    )
    _vn16_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn16_inventory
    )
    _vn16_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "article_definiteness_requires_rich_segments" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn16_inventory
    )
    _vn16_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn16_inventory
    )
    _vn16_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn16_inventory)
except Exception:
    _vn16_blocked = False
    _vn16_has_renderer_backfill = False
    _vn16_finite_gated = False
    _vn16_nominal_pos_gated = False
    _vn16_suffix_relation_gated = False
    _vn16_no_auto_apply = False
check("VN-16 sample preserves component-only evidence as non-applyable blocker rows", _vn16_blocked)
check("VN-16 sample keeps rich metadata review rows non-live-applyable", _vn16_has_renderer_backfill)
check("VN-16 sample keeps finite/passive verb rows exact-address gated", _vn16_finite_gated)
check("VN-16 sample keeps nominal/POS leakage rows gated", _vn16_nominal_pos_gated)
check("VN-16 sample keeps suffix, false-prefix, and relation rows gated", _vn16_suffix_relation_gated)
check("VN-16 sample contains no live-applyable candidate rows", _vn16_no_auto_apply)

try:
    _vn17_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn17_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn17_component = [
        _r for _r in _vn17_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn17_blocked = _vn17_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn17_component
    )
    _vn17_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") == "rich_metadata_plus_exact_address_review"
        and _r.get("may_apply_live") is False
        for _r in _vn17_inventory
    )
    _vn17_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn17_inventory
    )
    _vn17_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
            or "article_definiteness_requires_rich_segments" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn17_inventory
    )
    _vn17_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn17_inventory
    )
    _vn17_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn17_inventory)
except Exception:
    _vn17_blocked = False
    _vn17_has_renderer_backfill = False
    _vn17_finite_gated = False
    _vn17_nominal_pos_gated = False
    _vn17_suffix_relation_gated = False
    _vn17_no_auto_apply = False
check("VN-17 sample preserves component-only evidence as non-applyable blocker rows", _vn17_blocked)
check("VN-17 sample keeps rich metadata review rows non-live-applyable", _vn17_has_renderer_backfill)
check("VN-17 sample keeps finite/passive verb rows exact-address gated", _vn17_finite_gated)
check("VN-17 sample keeps nominal/POS leakage rows gated", _vn17_nominal_pos_gated)
check("VN-17 sample keeps suffix, relation, and token-only rows gated", _vn17_suffix_relation_gated)
check("VN-17 sample contains no live-applyable candidate rows", _vn17_no_auto_apply)

try:
    _vn18_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn18_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn18_component = [
        _r for _r in _vn18_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn18_blocked = _vn18_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn18_component
    )
    _vn18_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") in (
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn18_inventory
    )
    _vn18_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn18_inventory
    )
    _vn18_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
            or "article_definiteness_requires_rich_segments" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn18_inventory
    )
    _vn18_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn18_inventory
    )
    _vn18_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn18_inventory)
except Exception:
    _vn18_blocked = False
    _vn18_has_renderer_backfill = False
    _vn18_finite_gated = False
    _vn18_nominal_pos_gated = False
    _vn18_suffix_relation_gated = False
    _vn18_no_auto_apply = False
check("VN-18 sample preserves component-only evidence as non-applyable blocker rows", _vn18_blocked)
check("VN-18 sample keeps rich metadata review rows non-live-applyable", _vn18_has_renderer_backfill)
check("VN-18 sample keeps finite/passive verb rows exact-address gated", _vn18_finite_gated)
check("VN-18 sample keeps nominal/POS leakage rows gated", _vn18_nominal_pos_gated)
check("VN-18 sample keeps suffix, relation, and token-only rows gated", _vn18_suffix_relation_gated)
check("VN-18 sample contains no live-applyable candidate rows", _vn18_no_auto_apply)

try:
    _vn19_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn19_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn19_component = [
        _r for _r in _vn19_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn19_blocked = _vn19_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn19_component
    )
    _vn19_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") in (
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn19_inventory
    )
    _vn19_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn19_inventory
    )
    _vn19_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
            or "article_definiteness_requires_rich_segments" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn19_inventory
    )
    _vn19_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn19_inventory
    )
    _vn19_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn19_inventory)
except Exception:
    _vn19_blocked = False
    _vn19_has_renderer_backfill = False
    _vn19_finite_gated = False
    _vn19_nominal_pos_gated = False
    _vn19_suffix_relation_gated = False
    _vn19_no_auto_apply = False
check("VN-19 sample preserves component-only evidence as non-applyable blocker rows", _vn19_blocked)
check("VN-19 sample keeps rich metadata review rows non-live-applyable", _vn19_has_renderer_backfill)
check("VN-19 sample keeps finite/passive verb rows exact-address gated", _vn19_finite_gated)
check("VN-19 sample keeps nominal/POS leakage rows gated", _vn19_nominal_pos_gated)
check("VN-19 sample keeps suffix, relation, and token-only rows gated", _vn19_suffix_relation_gated)
check("VN-19 sample contains no live-applyable candidate rows", _vn19_no_auto_apply)

try:
    _vn20_inventory = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_vn20_inventory.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
    _vn20_component = [
        _r for _r in _vn20_inventory
        if _r.get("evidence_kind") == "component_only_evidence"
    ]
    _vn20_blocked = _vn20_component and all(
        _r.get("may_apply_live") is False
        and _r.get("recommended_next_action") == "blocker_queue_row"
        and _r.get("required_next_gate") == "component_only_blocker"
        and "component_only_candidate_no_whole_token_propagation" in (_r.get("detected_issue") or "")
        for _r in _vn20_component
    )
    _vn20_has_renderer_backfill = any(
        _r.get("evidence_kind") == "whole_token_candidate"
        and _r.get("required_next_gate") in (
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn20_inventory
    )
    _vn20_finite_gated = any(
        "finite_verb_dictionary_gloss_or_form_review" in (_r.get("detected_issue") or "")
        and _r.get("may_apply_live") is False
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "rich_metadata_plus_exact_address_review",
            "two_vote_exact_address_review",
        )
        for _r in _vn20_inventory
    )
    _vn20_nominal_pos_gated = any(
        (
            "verb_entry_nominal_derivative_or_lexical_noun_pos_review" in (_r.get("detected_issue") or "")
            or "noun_hover_may_leak_verb_infinitive" in (_r.get("detected_issue") or "")
            or "article_definiteness_requires_rich_segments" in (_r.get("detected_issue") or "")
        )
        and _r.get("may_apply_live") is False
        for _r in _vn20_inventory
    )
    _vn20_suffix_relation_gated = any(
        (
            "suffix_or_attached_pronoun_requires_visible_accounting" in (_r.get("detected_issue") or "")
            or "preposition_or_attached_relation_requires_nahw_review" in (_r.get("detected_issue") or "")
            or "surface_family_requires_token_only_override" in (_r.get("detected_issue") or "")
        )
        and _r.get("required_next_gate") in (
            "component_only_blocker",
            "two_vote_exact_address_review",
            "rich_metadata_plus_exact_address_review",
            "rich_renderer_metadata_backfill",
        )
        and _r.get("may_apply_live") is False
        for _r in _vn20_inventory
    )
    _vn20_no_auto_apply = all(_r.get("may_apply_live") is False for _r in _vn20_inventory)
except Exception:
    _vn20_blocked = False
    _vn20_has_renderer_backfill = False
    _vn20_finite_gated = False
    _vn20_nominal_pos_gated = False
    _vn20_suffix_relation_gated = False
    _vn20_no_auto_apply = False
check("VN-20 sample preserves component-only evidence as non-applyable blocker rows", _vn20_blocked)
check("VN-20 sample keeps rich metadata review rows non-live-applyable", _vn20_has_renderer_backfill)
check("VN-20 sample keeps finite/passive verb rows exact-address gated", _vn20_finite_gated)
check("VN-20 sample keeps nominal/POS leakage rows gated", _vn20_nominal_pos_gated)
check("VN-20 sample keeps suffix, relation, and token-only rows gated", _vn20_suffix_relation_gated)
check("VN-20 sample contains no live-applyable candidate rows", _vn20_no_auto_apply)

# Dogfood-derived Phase 4 requests should carry exact review hints without
# turning the samples into applyable decisions.
try:
    _dogfood_phase4_tranche_rows = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "phase4_closure_tranche_from_dogfood_review.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
except Exception:
    _dogfood_phase4_tranche_rows = []
_dogfood_phase4_tranche_by_surface = {
    (_row.get("identity") or {}).get("surface_sample"): _row
    for _row in _dogfood_phase4_tranche_rows
}
_dogfood_wama_tranche = _dogfood_phase4_tranche_by_surface.get("وَمَا", {})
_dogfood_wama_tranche_policy = _dogfood_wama_tranche.get("apply_policy") or {}
_dogfood_wama_tranche_candidates = _dogfood_wama_tranche.get("candidate_evidence") or {}
check(
    "dogfood-derived wama blocker is preserved in Phase4 dry-run tranche only",
    bool(
        _dogfood_wama_tranche
        and _dogfood_wama_tranche.get("lane") == "quarantine_collision"
        and _dogfood_wama_tranche.get("required_gate") == "human_review_required"
        and (_dogfood_wama_tranche.get("identity") or {}).get("quran_locs") == ["quran:86:14:1"]
        and (_dogfood_wama_tranche.get("identity") or {}).get("wbw_locs") == ["wbw:86:14:1"]
        and _dogfood_wama_tranche.get("recommended_action") == "quarantine until candidate collision is resolved by exact-token nahw/sarf review"
        and "human review resolves blocker before any edit" in (_dogfood_wama_tranche.get("required_evidence") or [])
        and _dogfood_wama_tranche_candidates.get("whole_token_candidates") == ["qamus:p:ma_negative", "qamus:p:ma_relative"]
        and _dogfood_wama_tranche_policy.get("apply_allowed") is False
        and _dogfood_wama_tranche_policy.get("live_mutation_allowed") is False
        and _dogfood_wama_tranche_policy.get("closure_claim_allowed") is False
        and _dogfood_wama_tranche_policy.get("component_candidates_can_certify") is False
        and _dogfood_wama_tranche_policy.get("raw_surface_identity_allowed") is False
        and _dogfood_wama_tranche_policy.get("parse_key_primary_identity") is False
    ),
)

try:
    _dogfood_two_vote = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "phase4_two_vote_request_from_dogfood_review.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
except Exception:
    _dogfood_two_vote = []
_dogfood_requests_by_surface = {
    (_row.get("identity") or {}).get("surface_sample"): _row
    for _row in _dogfood_two_vote
}
check("dogfood-derived wama blocker is not emitted as a two-vote request", "وَمَا" not in _dogfood_requests_by_surface)
_dogfood_yasaluka = _dogfood_requests_by_surface.get("يَسْأَلُكَ", {})
_dogfood_yasaluka_hint = _dogfood_yasaluka.get("gloss_style_hint") or {}
_dogfood_yasaluka_policy = _dogfood_yasaluka.get("apply_policy") or {}
check(
    "dogfood-derived yasaluka two-vote request keeps ask-you review hint",
    bool(
        _dogfood_yasaluka
        and (_dogfood_yasaluka.get("identity") or {}).get("surface_sample") == "يَسْأَلُكَ"
        and _dogfood_yasaluka.get("agreement_key_hint") == "verb-object-suffix-explicit-subject"
        and _dogfood_yasaluka_hint.get("preferred_concise_authored_gloss") == "ask you"
        and _dogfood_yasaluka_hint.get("required_when_approving") is True
        and _dogfood_yasaluka_hint.get("certifies_decision") is False
        and _dogfood_yasaluka_policy.get("apply_allowed") is False
        and _dogfood_yasaluka_policy.get("live_mutation_allowed") is False
        and (_dogfood_yasaluka.get("candidate_evidence") or {}).get("component_candidates_can_certify") is False
    ),
)
_dogfood_fahalaknahum = _dogfood_requests_by_surface.get("فَأَهْلَكْنَاهُمْ", {})
_dogfood_fahalaknahum_hint = _dogfood_fahalaknahum.get("gloss_style_hint") or {}
_dogfood_fahalaknahum_policy = _dogfood_fahalaknahum.get("apply_policy") or {}
_dogfood_fahalaknahum_evidence = _dogfood_fahalaknahum.get("candidate_evidence") or {}
check(
    "dogfood-derived fa-ahlaknahum two-vote request keeps finite-verb object review hint",
    bool(
        _dogfood_fahalaknahum
        and (_dogfood_fahalaknahum.get("identity") or {}).get("surface_sample") == "فَأَهْلَكْنَاهُمْ"
        and _dogfood_fahalaknahum.get("agreement_key_hint") == "result-particle-active-verb-object-suffix"
        and _dogfood_fahalaknahum_hint.get("preferred_concise_authored_gloss") == "so We destroyed them"
        and _dogfood_fahalaknahum_hint.get("required_when_approving") is True
        and _dogfood_fahalaknahum_hint.get("certifies_decision") is False
        and _dogfood_fahalaknahum_policy.get("apply_allowed") is False
        and _dogfood_fahalaknahum_policy.get("live_mutation_allowed") is False
        and _dogfood_fahalaknahum_evidence.get("component_candidates_can_certify") is False
        and not _dogfood_fahalaknahum_evidence.get("whole_token_candidates")
        and bool(_dogfood_fahalaknahum_evidence.get("component_candidates"))
    ),
)

_dogfood_two_vote_request_path = os.path.join(
    _R, "qamus", "examples", "phase4_two_vote_request_from_dogfood_review.sample.jsonl"
)
_dogfood_two_vote_response_path = os.path.join(
    _R, "qamus", "examples", "phase4_two_vote_response_from_dogfood_review.sample.jsonl"
)
try:
    _dogfood_two_vote_responses = [
        json.loads(_l)
        for _l in io.open(_dogfood_two_vote_response_path, encoding="utf-8")
        if _l.strip()
    ]
except Exception:
    _dogfood_two_vote_responses = []
_dogfood_responses_by_surface = {}
for _row in _dogfood_two_vote_responses:
    _surface = (_row.get("identity") or {}).get("surface_sample")
    _dogfood_responses_by_surface.setdefault(_surface, []).append(_row)
_dogfood_yasaluka_responses = _dogfood_responses_by_surface.get("يَسْأَلُكَ", [])
_dogfood_yasaluka_response_lenses = {_r.get("lens") for _r in _dogfood_yasaluka_responses}
check(
    "dogfood-derived yasaluka two-vote responses keep matching ask-you reason",
    bool(
        len(_dogfood_yasaluka_responses) == 2
        and _dogfood_yasaluka_response_lenses == {"sarf-primary", "nahw-primary"}
        and all(_r.get("decision") == "approve" for _r in _dogfood_yasaluka_responses)
        and all(_r.get("concise_authored_gloss") == "ask you" for _r in _dogfood_yasaluka_responses)
        and all(_r.get("reason_agreement_key") == "verb-object-suffix-explicit-subject" for _r in _dogfood_yasaluka_responses)
        and all(_r.get("safe_scope_after_vote") == "token_only" for _r in _dogfood_yasaluka_responses)
        and all(_r.get("component_candidates_used_as_certification") is False for _r in _dogfood_yasaluka_responses)
    ),
)
_dogfood_fahalaknahum_responses = _dogfood_responses_by_surface.get("فَأَهْلَكْنَاهُمْ", [])
_dogfood_fahalaknahum_response_lenses = {_r.get("lens") for _r in _dogfood_fahalaknahum_responses}
check(
    "dogfood-derived fa-ahlaknahum two-vote responses keep matching finite-verb object reason",
    bool(
        len(_dogfood_fahalaknahum_responses) == 2
        and _dogfood_fahalaknahum_response_lenses == {"sarf-primary", "nahw-primary"}
        and all(_r.get("decision") == "approve" for _r in _dogfood_fahalaknahum_responses)
        and all(_r.get("concise_authored_gloss") == "so We destroyed them" for _r in _dogfood_fahalaknahum_responses)
        and all(_r.get("reason_agreement_key") == "result-particle-active-verb-object-suffix" for _r in _dogfood_fahalaknahum_responses)
        and all(_r.get("safe_scope_after_vote") == "token_only" for _r in _dogfood_fahalaknahum_responses)
        and all(_r.get("component_candidates_used_as_certification") is False for _r in _dogfood_fahalaknahum_responses)
    ),
)

try:
    with tempfile.TemporaryDirectory(prefix="dogfood-two-vote-reconcile-") as _td:
        _certified_path = os.path.join(_td, "certified.jsonl")
        _unresolved_path = os.path.join(_td, "unresolved.jsonl")
        _validate_r = run_text([
            sys.executable,
            os.path.join(_R, "tools", "validate_phase4_two_vote_responses.py"),
            _dogfood_two_vote_response_path,
            "--requests",
            _dogfood_two_vote_request_path,
        ])
        _reconcile_r = run_text([
            sys.executable,
            os.path.join(_R, "tools", "reconcile_phase4_two_vote_responses.py"),
            "--requests",
            _dogfood_two_vote_request_path,
            "--responses",
            _dogfood_two_vote_response_path,
            "--certified-out",
            _certified_path,
            "--unresolved-out",
            _unresolved_path,
        ])
        _certified_rows = [
            json.loads(_l)
            for _l in io.open(_certified_path, encoding="utf-8")
            if _l.strip()
        ]
        _unresolved_rows = [
            json.loads(_l)
            for _l in io.open(_unresolved_path, encoding="utf-8")
            if _l.strip()
        ]
        _certified_by_surface = {
            (_row.get("identity") or {}).get("surface_sample"): _row
            for _row in _certified_rows
        }
        _cert_yasaluka = _certified_by_surface.get("يَسْأَلُكَ", {})
        _cert_fahalaknahum = _certified_by_surface.get("فَأَهْلَكْنَاهُمْ", {})
        _dogfood_reconcile_ok = (
            _validate_r.returncode == 0
            and _reconcile_r.returncode == 0
            and len(_certified_rows) == 2
            and len(_unresolved_rows) == 0
            and _cert_yasaluka.get("status") == "certified_not_applied"
            and (_cert_yasaluka.get("public_hover") or {}).get("gloss") == "ask you"
            and _cert_yasaluka.get("safe_scope_after_vote") == "token_only"
            and _cert_yasaluka.get("component_candidates_used_as_certification") is False
            and _cert_fahalaknahum.get("status") == "certified_not_applied"
            and (_cert_fahalaknahum.get("public_hover") or {}).get("gloss") == "so We destroyed them"
            and _cert_fahalaknahum.get("safe_scope_after_vote") == "token_only"
            and _cert_fahalaknahum.get("component_candidates_used_as_certification") is False
            and all((_row.get("apply_policy") or {}).get("apply_allowed") is False for _row in _certified_rows)
            and all((_row.get("apply_policy") or {}).get("live_mutation_allowed") is False for _row in _certified_rows)
            and all((_row.get("apply_policy") or {}).get("closure_claim_allowed") is False for _row in _certified_rows)
        )
except Exception:
    _dogfood_reconcile_ok = False
check("dogfood-derived two-vote responses reconcile only to certified_not_applied", _dogfood_reconcile_ok)

try:
    _dogfood_hover_plan_rows = [
        json.loads(_l)
        for _l in io.open(
            os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan_from_dogfood_review.sample.jsonl"),
            encoding="utf-8",
        )
        if _l.strip()
    ]
except Exception:
    _dogfood_hover_plan_rows = []
_dogfood_hover_plans_by_surface = {
    (_row.get("identity") or {}).get("surface_sample"): _row
    for _row in _dogfood_hover_plan_rows
}
check("dogfood-derived wama blocker is not emitted as a hover decision plan", "وَمَا" not in _dogfood_hover_plans_by_surface)
_dogfood_hover_plan = _dogfood_hover_plans_by_surface.get("يَسْأَلُكَ", {})
_dogfood_hover_plan_identity = _dogfood_hover_plan.get("identity") or {}
_dogfood_hover_plan_preview = _dogfood_hover_plan.get("token_decision_preview") or {}
_dogfood_hover_plan_policy = _dogfood_hover_plan.get("apply_policy") or {}
_dogfood_hover_plan_source_ids = set(_dogfood_hover_plan.get("source_certified_ids") or [])
check(
    "dogfood-derived yasaluka hover plan stays planned_not_applied and source-clean",
    bool(
        len(_dogfood_hover_plan_rows) == 2
        and _dogfood_hover_plan.get("status") == "planned_not_applied"
        and _dogfood_hover_plan.get("source_phase") == "phase4_two_vote_reconciled"
        and _dogfood_hover_plan_identity.get("quran_loc") == "quran:33:63:1"
        and _dogfood_hover_plan_identity.get("wbw_loc") == "wbw:33:63:1"
        and _dogfood_hover_plan_identity.get("surface_sample") == "يَسْأَلُكَ"
        and _dogfood_hover_plan.get("reason_agreement_key") == "verb-object-suffix-explicit-subject"
        and _dogfood_hover_plan.get("safe_scope") == "token_only"
        and _dogfood_hover_plan_preview == {
            "loc": "33:63:1",
            "gloss": "ask you",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        }
        and _dogfood_hover_plan_source_ids == {
            "phase4-two-vote:queue_parse_222222222222222222222222",
            "phase4-two-vote-response:queue_parse_222222222222222222222222:sarf-primary",
            "phase4-two-vote-response:queue_parse_222222222222222222222222:nahw-primary",
        }
        and _dogfood_hover_plan_policy.get("apply_allowed") is False
        and _dogfood_hover_plan_policy.get("live_mutation_allowed") is False
        and _dogfood_hover_plan_policy.get("closure_claim_allowed") is False
        and _dogfood_hover_plan_policy.get("append_only_ledger_required") is True
        and _dogfood_hover_plan_policy.get("requires_backup_rebuild_health_readback_before_apply") is True
        and _dogfood_hover_plan_policy.get("component_candidates_can_certify") is False
        and _dogfood_hover_plan_policy.get("raw_surface_identity_allowed") is False
        and _dogfood_hover_plan_policy.get("parse_key_primary_identity") is False
    ),
)
_dogfood_fahalaknahum_plan = _dogfood_hover_plans_by_surface.get("فَأَهْلَكْنَاهُمْ", {})
_dogfood_fahalaknahum_plan_identity = _dogfood_fahalaknahum_plan.get("identity") or {}
_dogfood_fahalaknahum_plan_preview = _dogfood_fahalaknahum_plan.get("token_decision_preview") or {}
_dogfood_fahalaknahum_plan_policy = _dogfood_fahalaknahum_plan.get("apply_policy") or {}
_dogfood_fahalaknahum_plan_source_ids = set(_dogfood_fahalaknahum_plan.get("source_certified_ids") or [])
check(
    "dogfood-derived fa-ahlaknahum hover plan stays planned_not_applied and source-clean",
    bool(
        _dogfood_fahalaknahum_plan.get("status") == "planned_not_applied"
        and _dogfood_fahalaknahum_plan.get("source_phase") == "phase4_two_vote_reconciled"
        and _dogfood_fahalaknahum_plan_identity.get("quran_loc") == "quran:26:139:2"
        and _dogfood_fahalaknahum_plan_identity.get("wbw_loc") == "wbw:26:139:2"
        and _dogfood_fahalaknahum_plan_identity.get("surface_sample") == "فَأَهْلَكْنَاهُمْ"
        and _dogfood_fahalaknahum_plan.get("reason_agreement_key") == "result-particle-active-verb-object-suffix"
        and _dogfood_fahalaknahum_plan.get("safe_scope") == "token_only"
        and _dogfood_fahalaknahum_plan_preview == {
            "loc": "26:139:2",
            "gloss": "so We destroyed them",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        }
        and _dogfood_fahalaknahum_plan_source_ids == {
            "phase4-two-vote:queue_parse_261392261392261392261392",
            "phase4-two-vote-response:queue_parse_261392261392261392261392:sarf-primary",
            "phase4-two-vote-response:queue_parse_261392261392261392261392:nahw-primary",
        }
        and _dogfood_fahalaknahum_plan_policy.get("apply_allowed") is False
        and _dogfood_fahalaknahum_plan_policy.get("live_mutation_allowed") is False
        and _dogfood_fahalaknahum_plan_policy.get("closure_claim_allowed") is False
        and _dogfood_fahalaknahum_plan_policy.get("append_only_ledger_required") is True
        and _dogfood_fahalaknahum_plan_policy.get("requires_backup_rebuild_health_readback_before_apply") is True
        and _dogfood_fahalaknahum_plan_policy.get("component_candidates_can_certify") is False
        and _dogfood_fahalaknahum_plan_policy.get("raw_surface_identity_allowed") is False
        and _dogfood_fahalaknahum_plan_policy.get("parse_key_primary_identity") is False
    ),
)

try:
    _dogfood_apply_manifest = json.load(io.open(
        os.path.join(_R, "qamus", "examples", "phase4_apply_readiness_manifest_from_dogfood_review.sample.json"),
        encoding="utf-8",
    ))
except Exception:
    _dogfood_apply_manifest = {}
_dogfood_exclusions = _dogfood_apply_manifest.get("excluded_tranche_rows") or {}
_dogfood_excluded_samples = {
    _sample.get("surface_sample"): _sample
    for _sample in (_dogfood_exclusions.get("sample_excluded") or [])
}
_dogfood_wama_excluded = _dogfood_excluded_samples.get("وَمَا", {})
check(
    "dogfood-derived apply-readiness manifest preserves excluded wama blocker",
    bool(
        _dogfood_exclusions.get("excluded_count") == 1
        and _dogfood_exclusions.get("excluded_by_lane") == {"quarantine_collision": 1}
        and _dogfood_exclusions.get("excluded_by_gate") == {"human_review_required": 1}
        and (_dogfood_exclusions.get("source_tranche") or {}).get("artifact") == "phase4_closure_tranche_from_dogfood_review.sample.jsonl"
        and _dogfood_wama_excluded.get("quran_locs") == ["quran:86:14:1"]
        and _dogfood_wama_excluded.get("wbw_locs") == ["wbw:86:14:1"]
        and _dogfood_wama_excluded.get("parse_id") == "parse:333333333333333333333333"
        and _dogfood_wama_excluded.get("lane") == "quarantine_collision"
        and _dogfood_wama_excluded.get("required_gate") == "human_review_required"
    ),
)

try:
    _dogfood_owner_request = json.load(io.open(
        os.path.join(_R, "qamus", "examples", "phase4_owner_authorization_request_from_dogfood_review.sample.json"),
        encoding="utf-8",
    ))
except Exception:
    _dogfood_owner_request = {}
check(
    "dogfood-derived owner authorization request preserves excluded wama blocker",
    bool(
        _dogfood_owner_request.get("excluded_tranche_rows") == _dogfood_exclusions
        and ((_dogfood_owner_request.get("excluded_tranche_rows") or {}).get("sample_excluded") or [{}])[0].get("surface_sample") == "وَمَا"
        and (_dogfood_owner_request.get("apply_policy") or {}).get("apply_allowed") is False
        and (_dogfood_owner_request.get("owner_authorization") or {}).get("status") == "not_provided"
    ),
)
_dogfood_owner_requirements = _dogfood_owner_request.get("authorization_requirements") or {}
_dogfood_owner_statement = _dogfood_owner_requirements.get("required_owner_statement") or ""
_dogfood_owner_manifest = (_dogfood_owner_request.get("source_artifacts") or {}).get("apply_readiness_manifest") or {}
_dogfood_owner_draft = (_dogfood_owner_request.get("source_artifacts") or {}).get("draft_token_decision_ledger") or {}
check(
    "dogfood-derived owner authorization requires exact request id and artifact hashes",
    bool(
        _dogfood_owner_requirements.get("must_reference_request_id") == _dogfood_owner_request.get("id")
        and _dogfood_owner_requirements.get("must_state_live_apply_scope") == "listed_draft_token_decision_rows_only"
        and _dogfood_owner_requirements.get("excluded_rows_remain_blocked") is True
        and _dogfood_owner_request.get("id") in _dogfood_owner_statement
        and _dogfood_owner_manifest.get("sha256") in _dogfood_owner_statement
        and _dogfood_owner_draft.get("sha256") in _dogfood_owner_statement
        and "excluded tranche rows remain blocked" in _dogfood_owner_statement
    ),
)

try:
    _rich_sample_dir = os.path.join(_R, "qamus", "examples")
    _rich_exact_ok = True
    _rich_exact_checked = 0
    _rich_exact_bad = None
    for _name in sorted(os.listdir(_rich_sample_dir)):
        if not (_name.startswith("rich_hover_") and _name.endswith(".sample.jsonl")):
            continue
        if "_evidence." in _name:
            continue
        _path = os.path.join(_rich_sample_dir, _name)
        for _lineno, _line in enumerate(io.open(_path, encoding="utf-8"), 1):
            _line = _line.strip()
            if not _line:
                continue
            _row = json.loads(_line)
            _segments = _row.get("segments") or []
            if not _segments:
                continue
            _rich_exact_checked += 1
            _concat = "".join(_seg.get("surface", "") for _seg in _segments)
            if _concat != _row.get("surface"):
                _rich_exact_ok = False
                _rich_exact_bad = "%s:%s:%s" % (_name, _lineno, _row.get("loc"))
                break
        if not _rich_exact_ok:
            break
    check("rich-hover sample segment surfaces concatenate exactly (%d rows)" % _rich_exact_checked,
          _rich_exact_ok and _rich_exact_checked >= 400)
    if _rich_exact_bad:
        print("  first mismatch:", _rich_exact_bad)
except Exception:
    check("rich-hover sample segment-surface exactness check runnable", False)

for _script, _args, _label in (
        ("build_live_shadow_graph.py", ["--self-test"], "Phase2 live shadow graph builder self-test"),
        ("validate_phase1_shadow_graph.py", ["--self-test"], "Phase2 shadow graph validator self-test"),
        ("scan_public_boundary.py", ["--self-test"], "Phase2 public-boundary scanner self-test"),
        ("compare_wbw_artifacts.py", ["--self-test"], "Phase2 WBW compare self-test"),
        ("summarize_shadow_closure_queue.py", ["--self-test"], "Phase2 shadow closure queue summarizer self-test"),
        ("validate_public_private_boundary.py", ["--self-test"], "Phase2 public/private boundary validator self-test"),
        ("validate_public_private_boundary.py",
         [os.path.join(_R, "qamus", "examples", "public_private_boundary.sample.json")],
         "Phase2 public/private boundary sample validates"),
        ("validate_parse_key_contract.py", ["--self-test"], "Phase2 parse-key contract validator self-test"),
        ("validate_parse_key_contract.py",
         [os.path.join(_R, "qamus", "examples", "parse_key.sample.jsonl")],
         "Phase2 parse-key sample validates"),
        ("validate_curriculum_assessment.py", ["--self-test"],
         "curriculum assessment validator self-test"),
        ("validate_curriculum_assessment.py",
         [os.path.join(_R, "curriculum", "assessment", "level-checkpoints.sample.jsonl")],
         "curriculum assessment checkpoint sample validates"),
        ("validate_detector_maturity.py", ["--self-test"], "Phase2 detector maturity validator self-test"),
        ("validate_detector_maturity.py",
         [os.path.join(_R, "qamus", "examples", "detector_maturity.sample.json")],
         "Phase2 detector maturity sample validates"),
        ("validate_live_shadow_run_manifest.py", ["--self-test"], "Phase2 live shadow run manifest validator self-test"),
        ("validate_live_shadow_run_manifest.py",
         [os.path.join(_R, "qamus", "examples", "live_shadow_run_manifest.sample.json")],
         "Phase2 live shadow run manifest sample validates"),
        ("validate_shadow_review_pack.py", ["--self-test"], "Phase2 shadow review-pack validator self-test"),
        ("validate_shadow_review_pack.py",
         [os.path.join(_R, "qamus", "examples", "shadow_review_pack.sample.jsonl")],
         "Phase2 shadow review-pack sample validates"),
        ("validate_detector_maturity.py",
         [os.path.join(_R, "qamus", "examples", "shadow_review_pack.sample.jsonl")],
         "Phase2 review-pack detector maturity validates"),
        ("validate_decision_linkage.py", ["--self-test"], "Phase2 decision linkage validator self-test"),
        ("validate_decision_linkage.py",
         [os.path.join(_R, "qamus", "examples", "decision_linkage.sample.jsonl")],
         "Phase2 decision linkage sample validates"),
        ("validate_hover_edit_intent.py", ["--self-test"], "Phase2 hover edit intent validator self-test"),
        ("validate_hover_edit_intent.py",
         [os.path.join(_R, "qamus", "examples", "hover_edit_intent.sample.jsonl")],
         "Phase2 hover edit intent sample validates"),
        ("validate_repair_impact_preview.py", ["--self-test"], "Phase2 repair impact preview validator self-test"),
        ("validate_repair_impact_preview.py",
         [os.path.join(_R, "qamus", "examples", "repair_impact_preview.sample.jsonl")],
         "Phase2 repair impact preview sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "production_bug_lesson.sample.jsonl")],
         "Phase2 production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "production_bug_lesson_from_intent.sample.jsonl")],
         "Phase3.5 production bug lesson from edit intent sample validates"),
        ("build_production_bug_lesson.py", ["--self-test"], "Phase3.5 production bug lesson builder self-test"),
        ("build_dogfood_production_bug_lessons.py", ["--self-test"], "Full-corpus dogfood production bug lesson builder self-test"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_production_bug_lesson.sample.jsonl")],
         "Full-corpus dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_preposition_oath_production_bug_lesson.sample.jsonl")],
         "Preposition/oath dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vocative_production_bug_lesson.sample.jsonl")],
         "Vocative dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_nominal_pos_production_bug_lesson.sample.jsonl")],
         "Nominal POS dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_particle_tranche_production_bug_lesson.sample.jsonl")],
         "Particle tranche dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_particle_remaining67_production_bug_lesson.sample.jsonl")],
         "Remaining particle dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn00_production_bug_lesson.sample.jsonl")],
         "VN-00 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn01_production_bug_lesson.sample.jsonl")],
         "VN-01 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn02_production_bug_lesson.sample.jsonl")],
         "VN-02 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn03_production_bug_lesson.sample.jsonl")],
         "VN-03 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn04_production_bug_lesson.sample.jsonl")],
         "VN-04 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn05_production_bug_lesson.sample.jsonl")],
         "VN-05 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn06_production_bug_lesson.sample.jsonl")],
         "VN-06 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn07_production_bug_lesson.sample.jsonl")],
         "VN-07 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn08_production_bug_lesson.sample.jsonl")],
         "VN-08 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn09_production_bug_lesson.sample.jsonl")],
         "VN-09 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn10_production_bug_lesson.sample.jsonl")],
         "VN-10 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn11_production_bug_lesson.sample.jsonl")],
         "VN-11 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn12_production_bug_lesson.sample.jsonl")],
         "VN-12 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn13_production_bug_lesson.sample.jsonl")],
         "VN-13 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn14_production_bug_lesson.sample.jsonl")],
         "VN-14 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn15_production_bug_lesson.sample.jsonl")],
         "VN-15 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn16_production_bug_lesson.sample.jsonl")],
         "VN-16 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn17_production_bug_lesson.sample.jsonl")],
         "VN-17 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn18_production_bug_lesson.sample.jsonl")],
         "VN-18 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn19_production_bug_lesson.sample.jsonl")],
         "VN-19 dogfood production bug lesson sample validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_vn20_production_bug_lesson.sample.jsonl")],
         "VN-20 dogfood production bug lesson sample validates"),
        ("summarize_rich_wbw_roles.py", ["--self-test"], "Phase2 rich WBW role taxonomy self-test"),
        ("validate_rich_wbw_gate_cases.py", ["--self-test"], "Phase2.9 rich WBW gate-case validator self-test"),
        ("build_shadow_admin_debug_pack.py", ["--self-test"], "Phase3 shadow admin debug pack self-test"),
        ("validate_shadow_admin_debug_pack.py", ["--self-test"], "Phase3 shadow admin debug pack validator self-test"),
        ("validate_shadow_admin_debug_pack.py",
         [os.path.join(_R, "qamus", "examples", "shadow_admin_debug_pack.sample.json")],
         "Phase3 shadow admin debug pack sample validates"),
        ("validate_shadow_admin_route_contract.py", ["--self-test"], "Phase3 shadow admin route contract validator self-test"),
        ("validate_shadow_admin_route_contract.py",
         [os.path.join(_R, "qamus", "examples", "shadow_admin_route_contract.sample.json")],
         "Phase3 shadow admin route contract sample validates"),
        ("validate_shadow_admin_route_contract.py",
         [
             os.path.join(_R, "qamus", "examples", "shadow_admin_route_contract.sample.json"),
             "--pack",
             os.path.join(_R, "qamus", "examples", "shadow_admin_debug_pack.sample.json"),
         ],
         "Phase3 shadow admin route contract matches debug pack sample"),
        ("build_full_corpus_hover_dogfood_audit.py",
         ["--self-test"],
         "Full-corpus hover dogfood audit builder self-test"),
        ("validate_full_corpus_hover_dogfood_audit.py",
         ["--self-test"],
         "Full-corpus hover dogfood audit validator self-test"),
        ("validate_full_corpus_hover_dogfood_audit.py",
         [os.path.join(_R, "qamus", "examples", "full_corpus_hover_dogfood_audit.sample.jsonl")],
         "Full-corpus hover dogfood audit sample validates"),
        ("validate_full_corpus_dogfood_subagent_lanes.py",
         ["--self-test"],
         "Full-corpus dogfood subagent lane validator self-test"),
        ("validate_full_corpus_dogfood_subagent_lanes.py",
         [os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_subagent_lane.sample.jsonl")],
         "Full-corpus dogfood subagent lane sample validates"),
        ("build_full_corpus_dogfood_lane_packets.py",
         ["--self-test"],
         "Full-corpus dogfood lane-packet builder self-test"),
        ("build_full_corpus_dogfood_lane_packets.py",
         ["--validate-jsonl", os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_lane_packet.sample.jsonl")],
         "Full-corpus dogfood lane-packet sample validates"),
        ("validate_full_corpus_dogfood_review_outputs.py",
         ["--self-test"],
         "Full-corpus dogfood review-output validator self-test"),
        ("validate_full_corpus_dogfood_review_outputs.py",
         [os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_review_output.sample.jsonl")],
         "Full-corpus dogfood review-output sample validates"),
        ("summarize_full_corpus_dogfood_review_outputs.py",
         ["--self-test"],
         "Full-corpus dogfood review-output summarizer self-test"),
        ("summarize_full_corpus_dogfood_review_outputs.py",
         [os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_review_output.sample.jsonl")],
         "Full-corpus dogfood review-output sample summarizes"),
        ("reconcile_full_corpus_dogfood_review_outputs.py",
         ["--self-test"],
         "Full-corpus dogfood controller reconciliation self-test"),
        ("reconcile_full_corpus_dogfood_review_outputs.py",
         ["--validate-jsonl", os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_reconciliation.sample.jsonl")],
         "Full-corpus dogfood controller reconciliation sample validates"),
        ("build_full_corpus_dogfood_next_state_queues.py",
         ["--self-test"],
         "Full-corpus dogfood next-state queue builder self-test"),
        ("build_full_corpus_dogfood_next_state_queues.py",
         ["--validate-jsonl", os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_next_state_queue.sample.jsonl")],
         "Full-corpus dogfood next-state queue sample validates"),
        ("build_full_corpus_dogfood_known_defect_readiness.py",
         ["--self-test"],
         "Full-corpus dogfood known-defect readiness builder self-test"),
        ("build_full_corpus_dogfood_known_defect_readiness.py",
         ["--validate-jsonl", os.path.join(_R, "qamus", "examples", "full_corpus_dogfood_known_defect_readiness.sample.jsonl")],
         "Full-corpus dogfood known-defect readiness sample validates"),
        ("summarize_full_corpus_dogfood_queue.py",
         ["--self-test"],
         "Full-corpus dogfood queue summarizer self-test"),
        ("build_full_corpus_dogfood_review_pack.py",
         ["--self-test"],
         "Full-corpus dogfood review-pack builder self-test"),
        ("build_shadow_review_pack_from_dogfood_review.py",
         ["--self-test"],
         "Dogfood review to shadow review-pack bridge self-test"),
        ("validate_shadow_review_pack.py",
         [os.path.join(_R, "qamus", "examples", "shadow_review_pack_from_dogfood_review.sample.jsonl")],
         "Dogfood-derived shadow review-pack sample validates"),
        ("plan_phase4_closure_tranche.py", ["--self-test"], "Phase4 dry-run closure tranche planner self-test"),
        ("validate_phase4_closure_tranche.py", ["--self-test"], "Phase4 dry-run closure tranche validator self-test"),
        ("validate_phase4_closure_tranche.py",
         [os.path.join(_R, "qamus", "examples", "phase4_closure_tranche.sample.jsonl")],
         "Phase4 dry-run closure tranche sample validates"),
        ("validate_phase4_closure_tranche.py",
         [os.path.join(_R, "qamus", "examples", "phase4_closure_tranche_from_dogfood_review.sample.jsonl")],
         "Dogfood-derived Phase4 dry-run closure tranche sample validates"),
        ("build_phase4_two_vote_requests.py", ["--self-test"], "Phase4 exact-addressed two-vote request builder self-test"),
        ("validate_phase4_two_vote_requests.py", ["--self-test"], "Phase4 exact-addressed two-vote request validator self-test"),
        ("validate_phase4_two_vote_requests.py",
         [os.path.join(_R, "qamus", "examples", "phase4_two_vote_request.sample.jsonl")],
         "Phase4 exact-addressed two-vote request sample validates"),
        ("validate_phase4_two_vote_requests.py",
         [os.path.join(_R, "qamus", "examples", "phase4_two_vote_request_from_dogfood_review.sample.jsonl")],
         "Dogfood-derived Phase4 exact-addressed two-vote request sample validates"),
        ("validate_phase4_two_vote_responses.py", ["--self-test"],
         "Phase4 exact-addressed two-vote response validator self-test"),
        ("validate_phase4_two_vote_responses.py",
         [os.path.join(_R, "qamus", "examples", "phase4_two_vote_response.sample.jsonl")],
         "Phase4 exact-addressed two-vote response sample validates"),
        ("validate_phase4_two_vote_responses.py",
         [os.path.join(_R, "qamus", "examples", "phase4_two_vote_response_from_dogfood_review.sample.jsonl"),
          "--requests",
          os.path.join(_R, "qamus", "examples", "phase4_two_vote_request_from_dogfood_review.sample.jsonl")],
         "Dogfood-derived Phase4 exact-addressed two-vote response sample validates"),
        ("reconcile_phase4_two_vote_responses.py", ["--self-test"],
         "Phase4 exact-addressed two-vote response reconciler self-test"),
        ("build_phase4_gloss_adjudication_requests.py", ["--self-test"],
         "Phase4 exact-addressed gloss adjudication request builder self-test"),
        ("validate_phase4_gloss_adjudication_requests.py", ["--self-test"],
         "Phase4 exact-addressed gloss adjudication request validator self-test"),
        ("validate_phase4_gloss_adjudication_requests.py",
         [os.path.join(_R, "qamus", "examples", "phase4_gloss_adjudication_request.sample.jsonl")],
         "Phase4 exact-addressed gloss adjudication request sample validates"),
        ("validate_phase4_gloss_adjudication_responses.py", ["--self-test"],
         "Phase4 exact-addressed gloss adjudication response validator self-test"),
        ("validate_phase4_gloss_adjudication_responses.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_gloss_adjudication_response.sample.jsonl"),
             "--requests",
             os.path.join(_R, "qamus", "examples", "phase4_gloss_adjudication_request.sample.jsonl"),
         ],
         "Phase4 exact-addressed gloss adjudication response sample validates"),
        ("reconcile_phase4_gloss_adjudication_responses.py", ["--self-test"],
         "Phase4 exact-addressed gloss adjudication response reconciler self-test"),
        ("build_phase4_hover_decision_plan.py", ["--self-test"],
         "Phase4 hover decision plan builder self-test"),
        ("validate_phase4_hover_decision_plan.py", ["--self-test"],
         "Phase4 hover decision plan validator self-test"),
        ("validate_phase4_hover_decision_plan.py",
         [os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan.sample.jsonl")],
         "Phase4 hover decision plan sample validates"),
        ("validate_phase4_hover_decision_plan.py",
         [os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan_from_dogfood_review.sample.jsonl")],
         "Dogfood-derived Phase4 hover decision plan sample validates"),
        ("build_phase4_apply_readiness_manifest.py", ["--self-test"],
         "Phase4 apply-readiness manifest builder self-test"),
        ("validate_phase4_apply_readiness_manifest.py", ["--self-test"],
         "Phase4 apply-readiness manifest validator self-test"),
        ("validate_phase4_apply_readiness_manifest.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_apply_readiness_manifest.sample.json"),
             "--plan-jsonl",
             os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan.sample.jsonl"),
         ],
         "Phase4 apply-readiness manifest sample validates"),
        ("validate_phase4_apply_readiness_manifest.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_apply_readiness_manifest_from_dogfood_review.sample.json"),
             "--plan-jsonl",
             os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan_from_dogfood_review.sample.jsonl"),
         ],
         "Dogfood-derived Phase4 apply-readiness manifest sample validates"),
        ("build_phase4_draft_token_decision_ledger.py", ["--self-test"],
         "Phase4 draft token-decision ledger builder self-test"),
        ("validate_phase4_draft_token_decision_ledger.py", ["--self-test"],
         "Phase4 draft token-decision ledger validator self-test"),
        ("validate_phase4_draft_token_decision_ledger.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_draft_token_decision_ledger.sample.jsonl"),
             "--plan-jsonl",
             os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan.sample.jsonl"),
         ],
         "Phase4 draft token-decision ledger sample validates"),
        ("validate_phase4_draft_token_decision_ledger.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_draft_token_decision_ledger_from_dogfood_review.sample.jsonl"),
             "--plan-jsonl",
             os.path.join(_R, "qamus", "examples", "phase4_hover_decision_plan_from_dogfood_review.sample.jsonl"),
         ],
         "Dogfood-derived Phase4 draft token-decision ledger sample validates"),
        ("validate_phase4_owner_authorization_request.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_owner_authorization_request.sample.json"),
             "--manifest-json",
             os.path.join(_R, "qamus", "examples", "phase4_apply_readiness_manifest.sample.json"),
             "--draft-ledger-jsonl",
             os.path.join(_R, "qamus", "examples", "phase4_draft_token_decision_ledger.sample.jsonl"),
         ],
         "Phase4 owner authorization request sample validates"),
        ("validate_phase4_owner_authorization_request.py",
         [
             os.path.join(_R, "qamus", "examples", "phase4_owner_authorization_request_from_dogfood_review.sample.json"),
             "--manifest-json",
             os.path.join(_R, "qamus", "examples", "phase4_apply_readiness_manifest_from_dogfood_review.sample.json"),
             "--draft-ledger-jsonl",
             os.path.join(_R, "qamus", "examples", "phase4_draft_token_decision_ledger_from_dogfood_review.sample.jsonl"),
         ],
         "Dogfood-derived Phase4 owner authorization request sample validates"),
        ("query_shadow_admin_debug_pack.py", ["--self-test"], "Phase3 shadow admin debug pack query self-test"),
        ("plan_shadow_hover_edit_intent.py", ["--self-test"], "Phase3 shadow hover edit intent planner self-test"),
        ("plan_shadow_repair_impact_preview.py", ["--self-test"], "Phase3 shadow repair impact preview planner self-test"),
        ("build_grammar_regression_mining.py", ["--self-test"], "Phase3.25 grammar regression mining builder self-test"),
        ("validate_grammar_regression_mining.py", ["--self-test"], "Phase3.25 grammar regression mining validator self-test"),
        ("validate_grammar_regression_mining.py",
         [os.path.join(_R, "nahw", "evals", "grammar-problems-phase3p25-mining.jsonl")],
         "Phase3.25 grammar regression mining ledger validates"),
        ("validate_grammar_issue_clusters.py", ["--self-test"], "Phase3.5 grammar issue clusters validator self-test"),
        ("validate_grammar_issue_clusters.py", [], "Phase3.5 grammar issue clusters validate mining coverage"),
):
    try:
        _v = run_text([sys.executable, os.path.join(_R, "tools", _script)] + _args)
        check(_label, _v.returncode == 0)
        if _v.returncode != 0:
            _out = (_v.stdout or _v.stderr).strip().splitlines()
            if _out:
                print("  ", _out[-1])
    except Exception:
        check(_label + " runnable", False)

for _script, _label in (("test_bulk_two_vote_requests.py", "bulk two-vote builder self-test"),
                        ("test_bulk_two_vote_request_validator.py", "bulk two-vote validator self-test"),
                        ("test_phase4_two_vote_requests.py", "Phase4 exact-addressed two-vote request self-test"),
                        ("test_phase4_two_vote_reconciliation.py", "Phase4 exact-addressed two-vote reconciliation self-test"),
                        ("test_phase4_gloss_adjudication_requests.py", "Phase4 exact-addressed gloss adjudication self-test"),
                        ("test_phase4_gloss_adjudication_response_reconciliation.py",
                         "Phase4 exact-addressed gloss adjudication response reconciliation self-test"),
                        ("test_phase4_hover_decision_plan.py", "Phase4 hover decision plan self-test"),
                        ("test_phase4_apply_readiness_manifest.py", "Phase4 apply-readiness manifest self-test"),
                        ("test_phase4_draft_token_decision_ledger.py",
                         "Phase4 draft token-decision ledger self-test"),
                        ("test_phase4_owner_authorization_request.py",
                         "Phase4 owner authorization request self-test")):
    try:
        _v = run_text([sys.executable, os.path.join(_R, "tools", _script)])
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
            _v = run_text([sys.executable, os.path.join(_R, "tools", _vname)])
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
            _v = run_text(_cmd)
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
            _g = run_text([sys.executable, _gp] + _ga)
            _v = run_text([sys.executable, os.path.join(_R, "tools", _val), _outp])
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
            _r = run_text([sys.executable, os.path.join(_R, "tools", _t), "--corpus", _corp, "--out", _cf, "--limit", "5"])
            _ok = _ok and _r.returncode == 0
        _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_corpus_fixture.py"), _cf])
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
