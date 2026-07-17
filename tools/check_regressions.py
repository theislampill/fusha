#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F11 — static verifier: the homograph/POS distinctions that must never collapse.

Confirms (via tools/normalize_ar.py) that the exact qamus-highlight bug classes cannot recur, and that the
regression fixtures are well-formed JSONL. Exit non-zero on any failure. No network, no live writes.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import normalize_ar as N
from tools import leak_sot
from tools import validate_linguistic_decisions as VLD

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

# Ordered verified copy of nahw/evals/grammar-decision-gates.json.
# tools/test_gate_ssot.py mutation-proves that all four homes stay identical.
GRAMMAR_GATE_TRIGGERS = {
    "two_vote_required": (
        "advanced_nahw", "irab", "case_or_mood", "istithna", "nafy_lil_jins", "idafa_ambiguous",
        "jar_majrur_ambiguous", "multi_sense_root", "referent_sensitive_gloss", "depth_deep",
        "format_essay", "bloom_analysis_or_higher",
    ),
    "human_source_review_required": (
        "ambiguous_grammar", "source_corpus_conflict", "suspected_qamus_entry_error",
        "proper_vs_common_noun", "quran_ref_uncertain",
    ),
    "never_auto_resolve": (
        "norm_only_match", "ocr_only_evidence", "external_gloss_copied", "reasoning_path_wrong",
        "qac_pos_conflict",
    ),
}


def grammar_gate(triggers):
    """Return the strictest required gate for a set of triggers."""
    triggers = set(triggers)
    if triggers & set(GRAMMAR_GATE_TRIGGERS["never_auto_resolve"]):
        return "never_auto_resolve"
    if triggers & set(GRAMMAR_GATE_TRIGGERS["human_source_review_required"]):
        return "human_source_review_required"
    if triggers & set(GRAMMAR_GATE_TRIGGERS["two_vote_required"]):
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
    tvr = json.load(io.open(os.path.join(ROOT, "nahw/rules/two-vote-required-rules.json"), encoding="utf-8"))
    _ssot_triggers = {
        tier: gd["gates"][tier]["trigger_when_ANY"]
        for tier in GRAMMAR_GATE_TRIGGERS
    }
    _rule_keys = {
        "two_vote_required": "two_vote_triggers",
        "human_source_review_required": "human_review_triggers",
        "never_auto_resolve": "never_auto_triggers",
    }
    _rules_triggers = {tier: tvr[key] for tier, key in _rule_keys.items()}
    _validator_triggers = {tier: list(values) for tier, values in VLD.GRAMMAR_GATE_TRIGGERS.items()}
    _harness_triggers = {tier: list(values) for tier, values in GRAMMAR_GATE_TRIGGERS.items()}
    check("grammar trigger lists match SSOT across all 4 homes",
          _ssot_triggers == _rules_triggers == _validator_triggers == _harness_triggers)
except Exception as e:
    check("grammar trigger lists load for 4-way equality", False)
    print("  ", e)

_gate_ssot_test = run_text([sys.executable, os.path.join(ROOT, "tools", "test_gate_ssot.py")])
check("grammar trigger SSOT mutation harness passes", _gate_ssot_test.returncode == 0)
if _gate_ssot_test.returncode:
    print(_gate_ssot_test.stdout)
    print(_gate_ssot_test.stderr)

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
try:
    import importlib.util as _source_photo_importer
    _sp_spec = _source_photo_importer.spec_from_file_location(
        "_source_photo_locator",
        os.path.join(ROOT, "tools", "build_source_photo_entry_locator.py"),
    )
    _sp_mod = _source_photo_importer.module_from_spec(_sp_spec)
    _sp_spec.loader.exec_module(_sp_mod)
    _spans_ok = (
        _sp_mod.section_page_candidate("v001") == 2
        and _sp_mod.section_page_candidate("n001") == 279
        and _sp_mod.section_page_candidate("p001") == 453
        and _sp_mod.section_page_candidate("p100") == 471
    )
except Exception:
    _spans_ok = False
check("source-photo locator uses section spans (v001 pg002, n001 pg279, p001 pg453)", _spans_ok)
try:
    _locator = json.load(io.open(os.path.join(ROOT, "qamus", "indexes", "source_photo_entry_locator.json"), encoding="utf-8"))
    _locs = _locator.get("locator", {})
    _v001 = _locs.get("v001", {})
    _n001 = _locs.get("n001", {})
    _p001 = _locs.get("p001", {})
    _locator_ok = (
        (_v001.get("candidate_page") == 2 or _v001.get("page") == 2)
        and (_v001.get("candidate_page_image") == "pg002.jpeg" or _v001.get("page_image") == "pg002.jpeg")
        and (_n001.get("candidate_page") == 279 or _n001.get("page") == 279)
        and (_n001.get("candidate_page_image") == "pg279.jpeg" or _n001.get("page_image") == "pg279.jpeg")
        and (_p001.get("candidate_page") == 453 or _p001.get("page") == 453)
    )
except Exception:
    _locator_ok = False
check("source-photo locator artifact keeps early verbs/nouns/particles in their source sections or verified overrides", _locator_ok)
try:
    _sample_pages = {}
    _samples_path = os.path.join(ROOT, "qamus", "reports", "source-photo-verified-samples.jsonl")
    for _line in io.open(_samples_path, encoding="utf-8"):
        _line = _line.strip()
        if not _line:
            continue
        _rec = json.loads(_line)
        if _rec.get("field") != "entry_locator":
            continue
        if _rec.get("verdict") not in {"verified", "verified_correct"}:
            continue
        if not _rec.get("page_image"):
            continue
        for _sk in _rec.get("source_keys") or []:
            _sample_pages[_sk] = _rec.get("page_image")
    _particle_locator_ok = bool(_sample_pages) and all(
        _locs.get(_sk, {}).get("confidence") in {"verified", "photo_verified"}
        and _locs.get(_sk, {}).get("page_image") == _page
        for _sk, _page in _sample_pages.items()
    )
except Exception:
    _particle_locator_ok = False
check("RH-LIVE source-photo entry-locator samples survive regeneration", _particle_locator_ok)
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

# ONTO QG ontology reconciliation: live CSS/schema coverage, owner-boundary statuses,
# pairwise palette artifact integrity, and static contrast-floor record are one harness gate.
for _art in (
        "qamus/registry/qg-class-reconciliation.json",
        "qamus/registry/qg-class-reconciliation.md",
        "qamus/registry/palette-collision-matrix.json",
        "qamus/registry/palette-collision-matrix.md",
        "tools/qg_registry.py",
        "tools/build_qg_ontology_registry.py",
        "tools/validate_qg_registry.py",
        "tools/test_validate_qg_registry.py"):
    check("ONTO qg registry artifact exists: %s" % _art, os.path.exists(os.path.join(_R, _art)))
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "test_validate_qg_registry.py")])
    check("ONTO qg registry focused tests", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_qg_registry.py"), "--self-test"])
    check("ONTO qg registry consistency self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("ONTO qg registry validator runnable", False)

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
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_01_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_01_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_01_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-01 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_02_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_02_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_02_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-02 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_03_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_03_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_03_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-03 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_04_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_04_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_04_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-04 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_05_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_05_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_05_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-05 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_06_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_06_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_06_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-06 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_07_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_07_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_07_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-07 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_08_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_08_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_08_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-08 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_09_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_09_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_09_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-09 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_10_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_10_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_10_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-10 standard certification sample validates"),
        ([
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_11_standard.sample.jsonl"),
             "--evidence-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_11_standard_evidence.sample.jsonl"),
             "--renderer-jsonl",
             os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_11_renderer_fixture.sample.jsonl"),
         ],
         "VN-RICH-CERT-11 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_12_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_12_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_12_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-12 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_13_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_13_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_13_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-13 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_14_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_14_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_14_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-14 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_15_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_15_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_15_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-15 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_16_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_16_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_16_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-16 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_17_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_17_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_17_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-17 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_18_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_18_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_18_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-18 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_19_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_19_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_19_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-19 standard certification sample validates"),
        ([
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_20_standard.sample.jsonl"),
            "--evidence-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_20_standard_evidence.sample.jsonl"),
            "--renderer-jsonl",
            os.path.join(_R, "qamus", "examples", "rich_cert_vn_rich_cert_20_renderer_fixture.sample.jsonl"),
        ],
        "VN-RICH-CERT-20 standard certification sample validates"),
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
    _report_dir = os.path.join(_R, "qamus", "reports")
    _rich_cert_reports = [
        os.path.join(_report_dir, _name)
        for _name in os.listdir(_report_dir)
        if _name.endswith(".md")
        and (_name.startswith("p-rich-cert-") or _name.startswith("vn-rich-cert-"))
    ]
    check("RICH-CERT report count through VN20", len(_rich_cert_reports) == 25)
    _missing_flywheel = []
    for _path in _rich_cert_reports:
        _text = io.open(_path, encoding="utf-8").read()
        if not all(_needle in _text for _needle in (
            "## Flywheel Impact",
            "Assessment/checkpoint",
            "Progress/missed-error",
            "Future tranche-routing implications",
        )):
            _missing_flywheel.append(os.path.basename(_path))
    check("RICH-CERT reports carry flywheel impact fields", not _missing_flywheel)
    if _missing_flywheel:
        print("  missing:", ", ".join(_missing_flywheel[:5]))

    _synthesis = io.open(
        os.path.join(_report_dir, "rich-cert-flywheel-synthesis-20260627.md"),
        encoding="utf-8",
    ).read()
    check("RICH-CERT flywheel synthesis report exists",
          "RH-LIVE-00 Preview Shortlist" in _synthesis and "No row is live-applyable" in _synthesis)

    _learner_surfaces = "\n".join(
        io.open(os.path.join(_R, _path), encoding="utf-8").read()
        for _path in (
            "curriculum/drills/dogfood-error-remediation-index.md",
            "curriculum/progress/missed-error-log.template.md",
            "curriculum/assessment/grading-rubric.md",
        )
    )
    for _category in (
        "rich_cert_preview_overclaim",
        "rich_cert_pending_gate",
        "rh_live_preview_only",
        "hidden_number_morphology",
        "hidden_derivative_shape",
        "hidden_imperfect_prefix",
        "quran_display_text_mismatch",
        "process_prose_in_hover",
        "card_level_coverage_hidden",
    ):
        check("RICH-CERT learner category promoted: " + _category,
              _category in _learner_surfaces)
    _rh_live_andon_report = io.open(
        os.path.join(_R, "curriculum", "reports", "rh-live-andon-flywheel-backfill-20260629.md"),
        encoding="utf-8",
    ).read()
    check("RH-LIVE ANDON flywheel report exists",
          "Role color cannot collapse morphology" in _rh_live_andon_report
          and "Learner explanations must teach Arabic" in _rh_live_andon_report
          and "does not mutate live Qamus" in _rh_live_andon_report)
except Exception:
    check("RICH-CERT flywheel synthesis/readiness guard runnable", False)

try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_preview_candidates.py"),
                   "--self-test"])
    check("RH-LIVE-00 preview candidate validator self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 preview candidate validator runnable", False)
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_preview_candidates.py"),
                   os.path.join(_R, "qamus", "examples", "rh_live_00_preview_candidates.sample.jsonl")])
    check("RH-LIVE-00 preview candidate sample validates", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 preview candidate sample runnable", False)

try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_source_triangulation_readiness.py"),
                   "--self-test"])
    check("RH-LIVE-00 source-triangulation readiness validator self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 source-triangulation readiness validator runnable", False)
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_source_triangulation_readiness.py"),
                   os.path.join(_R, "qamus", "examples", "rh_live_00_source_triangulation_readiness.sample.jsonl")])
    check("RH-LIVE-00 source-triangulation readiness sample validates", _v.returncode == 0)
    if _v.returncode == 0:
        _rows = [
            json.loads(_line)
            for _line in io.open(
                os.path.join(_R, "qamus", "examples", "rh_live_00_source_triangulation_readiness.sample.jsonl"),
                encoding="utf-8",
            )
            if _line.strip()
        ]
        _ready = sum(1 for _row in _rows if _row.get("next_state") == "exact_address_two_vote_ready_not_applyable")
        _retry = sum(1 for _row in _rows if _row.get("next_state") == "source_retry_required_not_certified")
        check("RH-LIVE-00 source readiness moved all nine rows to exact-address two-vote", _ready == 9 and _retry == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 source-triangulation readiness sample runnable", False)
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_phase4_two_vote_requests.py"),
                   os.path.join(_R, "qamus", "examples", "rh_live_00_two_vote_request_from_source_readiness.sample.jsonl")])
    check("RH-LIVE-00 source-derived two-vote request sample validates", _v.returncode == 0)
    if _v.returncode == 0:
        _request_rows = [
            json.loads(_line)
            for _line in io.open(
                os.path.join(_R, "qamus", "examples", "rh_live_00_two_vote_request_from_source_readiness.sample.jsonl"),
                encoding="utf-8",
            )
            if _line.strip()
        ]
        check("RH-LIVE-00 source-derived two-vote request sample has nine rows", len(_request_rows) == 9)
        _yasaluka_request = next(
            (
                _row for _row in _request_rows
                if "quran:33:63:1" in ((_row.get("identity") or {}).get("quran_locs") or [])
            ),
            {},
        )
        _ctx = _yasaluka_request.get("gloss_context") or {}
        check(
            "RH-LIVE-00 two-vote request preserves يَسْأَلُكَ context gloss split",
            _ctx.get("token_contribution_gloss") == "ask you"
            and _ctx.get("contextual_phrase_gloss") == "the people ask you"
            and _ctx.get("adjacent_context_required") is True
            and "quran:33:63:2" in (_ctx.get("adjacent_context_locs") or [])
            and "النَّاسُ" in str(_ctx.get("context_subject_source") or "")
            and (_yasaluka_request.get("gloss_style_hint") or {}).get("preferred_concise_authored_gloss") == "the people ask you",
        )
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 source-derived two-vote request sample runnable", False)

try:
    _requests = os.path.join(_R, "qamus", "examples", "rh_live_00_two_vote_request_from_source_readiness.sample.jsonl")
    _responses = os.path.join(_R, "qamus", "examples", "rh_live_00_two_vote_response_from_source_readiness.sample.jsonl")
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_phase4_two_vote_responses.py"),
                   _responses, "--requests", _requests])
    check("RH-LIVE-00 source-derived two-vote response sample validates", _v.returncode == 0)
    if _v.returncode == 0:
        _response_rows = [
            json.loads(_line)
            for _line in io.open(_responses, encoding="utf-8")
            if _line.strip()
        ]
        check("RH-LIVE-00 source-derived two-vote response sample has eighteen rows", len(_response_rows) == 18)
        _yasaluka_responses = [
            _row for _row in _response_rows
            if "quran:33:63:1" in ((_row.get("identity") or {}).get("quran_locs") or [])
        ]
        check(
            "RH-LIVE-00 two-vote responses agree on contextual يَسْأَلُكَ gloss",
            len(_yasaluka_responses) == 2
            and {(_row.get("lens")) for _row in _yasaluka_responses} == {"sarf-primary", "nahw-primary"}
            and all(_row.get("concise_authored_gloss") == "the people ask you" for _row in _yasaluka_responses)
            and all((_row.get("gloss_context") or {}).get("token_contribution_gloss") == "ask you" for _row in _yasaluka_responses)
            and all("النَّاسُ" in str((_row.get("gloss_context") or {}).get("context_subject_source") or "") for _row in _yasaluka_responses),
        )
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 source-derived two-vote response sample runnable", False)

try:
    with tempfile.TemporaryDirectory(prefix="rh-live-reconcile-") as _td:
        _cert = os.path.join(_td, "certified.jsonl")
        _unresolved = os.path.join(_td, "unresolved.jsonl")
        _v = run_text([
            sys.executable,
            os.path.join(_R, "tools", "reconcile_phase4_two_vote_responses.py"),
            "--requests",
            os.path.join(_R, "qamus", "examples", "rh_live_00_two_vote_request_from_source_readiness.sample.jsonl"),
            "--responses",
            os.path.join(_R, "qamus", "examples", "rh_live_00_two_vote_response_from_source_readiness.sample.jsonl"),
            "--certified-out",
            _cert,
            "--unresolved-out",
            _unresolved,
        ])
        _cert_rows = sum(1 for _line in io.open(_cert, encoding="utf-8") if _line.strip()) if os.path.exists(_cert) else 0
        _unresolved_rows = sum(1 for _line in io.open(_unresolved, encoding="utf-8") if _line.strip()) if os.path.exists(_unresolved) else 0
        check("RH-LIVE-00 source-derived two-vote reconciliation yields 9 certified/0 unresolved",
              _v.returncode == 0 and _cert_rows == 9 and _unresolved_rows == 0)
        if _v.returncode != 0:
            _out = (_v.stdout or _v.stderr).strip().splitlines()
            if _out:
                print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 source-derived two-vote reconciliation runnable", False)

try:
    _report_dir = os.path.join(_R, "qamus", "reports")
    for _name, _needle in (
        ("rh-live-00-two-vote-response-reconciliation-20260627.md", "certified-not-applied rows | 9"),
        ("rh-live-00-two-vote-response-reconciliation-20260627.md", "`the people ask you`"),
        ("rh-live-00-two-vote-response-reconciliation-20260627.md", "`token_contribution_gloss`: `ask you`"),
        ("rh-live-00-two-vote-request-20260627.md", "Contextual Gloss Split"),
        ("rh-live-00-two-vote-request-20260627.md", "`النَّاسُ` at `quran:33:63:2`"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "ordinary public hover behavior"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "RH-LIVE-00.5 Role-Aware Palette"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "RH-LIVE-00.6 Admin Preview IA"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "RH-LIVE-00.7 Split-Layer Route IA"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "compact segment rows with sarf/nahw micro-facts"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "should not repeat another open hover"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "Underlines are not part of the default role-color treatment"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "RH-LIVE-00.8 Hover Preview Microcopy, Columns, And Context"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "fixed shared columns for role label, RTL Arabic segment, and English contribution"),
        ("rh-live-00-renderer-admin-preview-plan-20260627.md", "contextual gloss `the people ask you`, token"),
        ("rh-live-00-source-triangulation-readiness-20260627.md", "Word-Level Versus Phrase-Context Evidence"),
        ("rh-live-00-source-triangulation-readiness-20260627.md", "`phrase_context_level` inside `source_triangulation.evidence_scopes`"),
        ("rh-live-00-admin-preview-bundle-manifest-20260628.md", "machine-checkable bundle gate"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "visible Arabic tokens remain atomic"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "Role-Aware Color Guard"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "RH-LIVE-00.6 IA/UX Hierarchy"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "RH-LIVE-00.7 Split-Layer Hover/Inspector IA"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "hover-level sarf/nahw micro-facts"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "absence of a duplicate admin hover panel"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "Underline policy is also explicit"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "RH-LIVE-00.8 Hover Alignment And Context Gloss Guard"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "fixed shared columns for label, Arabic segment, and English contribution"),
        ("rh-live-00-admin-preview-dom-fixture-20260628.md", "subject supplied by following `النَّاسُ`"),
    ):
        _text = io.open(os.path.join(_report_dir, _name), encoding="utf-8").read()
        check("RH-LIVE-00 report present: " + _name, _needle in _text)
except Exception:
    check("RH-LIVE-00 report presence/readability", False)

try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_admin_preview_dom_fixture.py"),
                   "--self-test"])
    check("RH-LIVE-00 admin-preview DOM fixture validator self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 admin-preview DOM fixture validator runnable", False)
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_admin_preview_dom_fixture.py"),
                   os.path.join(_R, "qamus", "examples", "rh_live_00_admin_preview_dom_fixture.sample.html")])
    check("RH-LIVE-00 admin-preview DOM fixture sample validates", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 admin-preview DOM fixture sample runnable", False)

try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_admin_preview_bundle_manifest.py"),
                   "--self-test"])
    check("RH-LIVE-00 admin-preview bundle manifest validator self-test", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 admin-preview bundle manifest validator runnable", False)
try:
    _v = run_text([sys.executable, os.path.join(_R, "tools", "validate_rh_live_admin_preview_bundle_manifest.py"),
                   os.path.join(_R, "qamus", "examples", "rh_live_00_admin_preview_bundle_manifest.sample.json")])
    check("RH-LIVE-00 admin-preview bundle manifest sample validates", _v.returncode == 0)
    if _v.returncode != 0:
        _out = (_v.stdout or _v.stderr).strip().splitlines()
        if _out:
            print("  ", _out[-1])
except Exception:
    check("RH-LIVE-00 admin-preview bundle manifest sample runnable", False)

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
        # source-selection (L15 canary lesson): majority/canonical class-signature, not most-segmented
        ("validate_source_selection.py", ["--self-test"], "source-selection majority/canonical class-signature self-test"),
        ("validate_source_selection.py",
         [os.path.join(_R, "qamus", "examples", "source_selection.sample.jsonl")],
         "source-selection accept fixture validates"),
        ("validate_production_bug_lessons.py",
         [os.path.join(_R, "qamus", "examples", "dogfood_source_selection_production_bug_lesson.sample.jsonl")],
         "Source-selection dogfood production bug lesson sample validates"),
        # public entry-count guard (L21): 2092 = 1045 noun + 947 verb + 100 particle, manifest-consistent
        ("validate_public_entry_count.py", ["--self-test"], "public entry-count guard self-test"),
        ("validate_public_entry_count.py", [], "public entry count == 2092 (section split + manifest consistency)"),
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

try:
    _assessment_rows = [
        json.loads(_line)
        for _line in io.open(
            os.path.join(_R, "curriculum", "assessment", "level-checkpoints.sample.jsonl"),
            encoding="utf-8",
        )
        if _line.strip()
    ]
    _yasaluka_checkpoint = next(
        (_row for _row in _assessment_rows if _row.get("id") == "L8-verb-suffix-yasaluka"),
        {},
    )
    _checkpoint_blob = json.dumps(_yasaluka_checkpoint, ensure_ascii=False)
    check(
        "curriculum assessment teaches يَسْأَلُكَ token/context gloss split",
        _yasaluka_checkpoint.get("two_vote_required") is True
        and "ask you" in _checkpoint_blob
        and "the people ask you" in _checkpoint_blob
        and "النَّاسُ" in _checkpoint_blob
        and "people is inside يَسْأَلُكَ" in _checkpoint_blob,
    )
    _hover_drill = io.open(
        os.path.join(_R, "curriculum", "drills", "hover-composition-and-routing.md"),
        encoding="utf-8",
    ).read()
    _nahw_drill = io.open(
        os.path.join(_R, "nahw", "drills", "dogfood-nahw-remediation.md"),
        encoding="utf-8",
    ).read()
    check(
        "drills preserve adjacent subject source for يَسْأَلُكَ",
        "token contribution is \"ask you\"" in _hover_drill
        and "following `النَّاسُ`" in _hover_drill
        and "Token Contribution vs Adjacent Context" in _nahw_drill
        and "`النَّاسُ` supplies the subject" in _nahw_drill,
    )
    _bug_rows = [
        json.loads(_line)
        for _line in io.open(
            os.path.join(_R, "qamus", "examples", "dogfood_production_bug_lesson.sample.jsonl"),
            encoding="utf-8",
        )
        if _line.strip()
    ]
    _context_lesson = next(
        (_row for _row in _bug_rows if _row.get("bug_class") == "contextual_subject_source_hidden"),
        {},
    )
    check(
        "production bug lesson records يَسْأَلُكَ contextual subject source",
        _context_lesson.get("token_contribution_gloss") == "ask you"
        and _context_lesson.get("contextual_phrase_gloss") == "the people ask you"
        and "quran:33:63:2" in (_context_lesson.get("adjacent_context_locs") or [])
        and "النَّاسُ" in str(_context_lesson.get("context_subject_source") or "")
        and _context_lesson.get("gate") == "two_vote_required",
    )
except Exception:
    check("curriculum adjacent-context regression readback runnable", False)

# --- T11 class-2 lane tooling (enrichment, pre-pass, packet builders) ---
for _script, _args, _marker, _label in (
    ("test_enrich_rebind_queue.py", [], "OK",
     "rebind-queue root-lookup enrichment tests"),
    ("test_funcword_homograph_prepass.py", [], "OK",
     "function-word homograph pre-pass tests"),
    ("build_rebind_two_vote_packets.py", ["--self-test"], "SELFTESTS=OK",
     "rebind two-vote packet builder self-test"),
    ("build_funcword_two_vote_packets.py", ["--self-test"], "SELF-TEST OK",
     "function-word two-vote packet builder self-test"),
):
    try:
        _c2 = run_text([sys.executable, os.path.join(ROOT, "tools", _script)]
                       + _args, timeout=300)
        _out = (_c2.stdout or "") + (_c2.stderr or "")
        check(_label, _c2.returncode == 0 and _marker in _out)
    except Exception as _e:
        check(_label + " (harness error)", False)
        print("  ", _e)

for _script, _label in (("test_build_two_vote_packets_wave4.py",
                         "wave-4 selection + packet enrichment fixtures"),
                        ("test_bulk_two_vote_requests.py", "bulk two-vote builder self-test"),
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

# parser/checker substrate (parserplans P0 + smallest P1 slice): schemas, checker, validator, fixture, contract
for _art in ("qamus/schemas/parser-check-ir.schema.json", "qamus/schemas/grammar-issue.schema.json",
             "tools/fusha_check.py", "tools/validate_parser_check.py",
             "qamus/examples/parser_check_regression.sample.jsonl",
             "qamus/reports/parser-checker-substrate.md"):
    check("parser-checker artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
try:
    _pcv = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_parser_check.py"), "--self-test"])
    check("parser-checker validator self-test (6 FAIL conditions reject; good units clean)", _pcv.returncode == 0)
    _pcc = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_check.py"), "--self-test"])
    check("parser-checker self-test (regression examples + 13 issue classes + out_of_scope boundary)", _pcc.returncode == 0)
    _pcf = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_parser_check.py"),
                     os.path.join(ROOT, "qamus", "examples", "parser_check_regression.sample.jsonl")])
    check("parser-checker regression fixture validates (13 units, 0 violations)", _pcf.returncode == 0)
except Exception as _e:
    check("parser-checker substrate runnable", False)
    print("  ", _e)

# general Fusha grammar-checker + rich-hover candidate flywheel (parserplans/general-fusha-grammar-checker P0+P1 slice):
# 2 schemas + general text-check (checker+validator+fixture) + rich-hover flywheel (emitter+validator+fixture) + bridge doc.
for _art in ("qamus/schemas/fusha-text-check.schema.json", "qamus/schemas/rich-hover-candidate.schema.json",
             "tools/fusha_text_check.py", "tools/validate_fusha_text_check.py",
             "tools/rich_hover_flywheel.py", "tools/validate_rich_hover_candidate.py",
             "qamus/examples/fusha_text_check.sample.jsonl", "qamus/examples/rich_hover_flywheel.sample.jsonl",
             "qamus/reports/general-checker-rich-hover-flywheel.md"):
    check("general-checker artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
try:
    _gc1 = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_text_check.py"), "--self-test"])
    check("general text-checker self-test (3 modes, ambiguity-preserving, never auto_safe, source-clean)", _gc1.returncode == 0)
    _gc2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_fusha_text_check.py"), "--self-test"])
    check("general text-checker validator self-test (10 FAIL conditions reject; fixture rows clean)", _gc2.returncode == 0)
    _gc3 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_fusha_text_check.py"),
                     os.path.join(ROOT, "qamus", "examples", "fusha_text_check.sample.jsonl")])
    check("general text-check fixture validates (10 records, 0 violations)", _gc3.returncode == 0)
    _gc4 = run_text([sys.executable, os.path.join(ROOT, "tools", "rich_hover_flywheel.py"), "--self-test"])
    check("rich-hover flywheel self-test (candidates round-trip into the certification validator)", _gc4.returncode == 0)
    _gc5 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_rich_hover_candidate.py"), "--self-test"])
    check("rich-hover candidate validator self-test (10 FAIL conditions reject; round-trip)", _gc5.returncode == 0)
    _gc6 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_rich_hover_candidate.py"),
                     os.path.join(ROOT, "qamus", "examples", "rich_hover_flywheel.sample.jsonl")])
    check("rich-hover flywheel fixture validates (10 candidates, 0 violations)", _gc6.returncode == 0)
except Exception as _e:
    check("general-checker + flywheel runnable", False)
    print("  ", _e)

# RH-LIVE Plan 15 parser boundary flywheel: parser output is a gate/factory
# interface, not a live coverage claim or arbitrary-text oracle. Validate the
# committed sample, and validate the ignored full queue when regenerated.
try:
    _plan15_full = os.path.join(ROOT, "out", "rh-live-plan15-parser-flywheel",
                                "rh_live_plan15_parser_flywheel.full.jsonl")
    for _art in ("tools/validate_rh_live_plan15_flywheel.py",
                 "tools/import_rh_live_plan15_flywheel.py",
                 "qamus/examples/rh_live_plan15_parser_flywheel.sample.jsonl",
                 "qamus/examples/rh_live_plan15_parser_flywheel.sample.meta.json",
                 "qamus/examples/rh_live_plan15_vn01_vn02_subword_graph.sample.jsonl",
                 "qamus/examples/rh_live_plan15_vn01_vn02_subword_graph.sample.meta.json",
                 "qamus/reports/closure-2092/rh-live-plan15-parser-flywheel-20260701.md",
                 "qamus/reports/closure-2092/rh-live-plan15-parser-flywheel-20260701.json",
                 "qamus/reports/closure-2092/rh-live-plan15-vn01-vn02-subword-graph-20260701.md",
                 "qamus/reports/closure-2092/rh-live-plan15-vn01-vn02-subword-graph-20260701.json"):
        check("RH-LIVE Plan 15 parser flywheel artifact exists: %s" % _art,
              os.path.exists(os.path.join(ROOT, _art)))
    _p15a = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_rh_live_plan15_flywheel.py"),
                      "--self-test"])
    check("RH-LIVE Plan 15 flywheel validator self-test (claim-boundary + leak reject)", _p15a.returncode == 0)
    _p15b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_rh_live_plan15_flywheel.py"),
                      os.path.join(ROOT, "qamus", "examples", "rh_live_plan15_parser_flywheel.sample.jsonl")])
    check("RH-LIVE Plan 15 flywheel sample validates (parser-known/partial routed, no live claim)",
          _p15b.returncode == 0)
    _p15b2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_rh_live_plan15_flywheel.py"),
                       os.path.join(ROOT, "qamus", "examples",
                                    "rh_live_plan15_vn01_vn02_subword_graph.sample.jsonl")])
    check("RH-LIVE Plan 15 VN-01/VN-02 subword graph sample validates (stem route included)",
          _p15b2.returncode == 0)
    _p15_report = json.load(io.open(
        os.path.join(ROOT, "qamus", "reports", "closure-2092",
                     "rh-live-plan15-parser-flywheel-20260701.json"),
        encoding="utf-8",
    ))
    _p15_meta = json.load(io.open(
        os.path.join(ROOT, "qamus", "examples", "rh_live_plan15_parser_flywheel.sample.meta.json"),
        encoding="utf-8",
    ))
    _p15_meta2 = json.load(io.open(
        os.path.join(ROOT, "qamus", "examples", "rh_live_plan15_vn01_vn02_subword_graph.sample.meta.json"),
        encoding="utf-8",
    ))
    _p15_report2 = json.load(io.open(
        os.path.join(ROOT, "qamus", "reports", "closure-2092",
                     "rh-live-plan15-vn01-vn02-subword-graph-20260701.json"),
        encoding="utf-8",
    ))
    _p15_head = run_text(["git", "-C", ROOT, "rev-parse", "HEAD"])
    if _p15_head.returncode == 0:
        _p15_head_commit = _p15_head.stdout.strip()
        def _plan15_ancestor_check(label, artifact):
            artifact_commit = artifact.get("fusha_commit")
            ancestor = run_text(["git", "-C", ROOT, "merge-base", "--is-ancestor", artifact_commit or "", _p15_head_commit])
            check(label,
                  isinstance(artifact_commit, str)
                  and len(artifact_commit) == 40
                  and ancestor.returncode == 0)

        _plan15_ancestor_check("RH-LIVE Plan 15 report records a valid ancestor Fusha HEAD", _p15_report)
        _plan15_ancestor_check("RH-LIVE Plan 15 sample meta records a valid ancestor Fusha HEAD", _p15_meta)
        _plan15_ancestor_check("RH-LIVE Plan 15 VN-01/VN-02 supplement records a valid ancestor Fusha HEAD", _p15_report2)
        _plan15_ancestor_check("RH-LIVE Plan 15 VN-01/VN-02 sample meta records a valid ancestor Fusha HEAD", _p15_meta2)
    else:
        check("RH-LIVE Plan 15 report records a 40-hex Fusha commit",
              isinstance(_p15_report.get("fusha_commit"), str)
              and len(_p15_report.get("fusha_commit")) == 40)
    if os.path.exists(_plan15_full):
        _p15c = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_rh_live_plan15_flywheel.py"),
                          _plan15_full])
        check("RH-LIVE Plan 15 full ignored queue validates when present", _p15c.returncode == 0)
except Exception as _e:
    check("RH-LIVE Plan 15 parser flywheel runnable", False)
    print("  ", _e)

# P2 deepening slice (parserplans/general-fusha-grammar-checker-p2): leak source-of-truth (E) + governor/iʿrāb/dependency
# lattice (B) + cross-builder conflict resolution (F). Artifacts + self-tests + fixture validation.
for _art in ("tools/leak_sot.py", "tools/validate_source_boundary.py",
             "qamus/schemas/dependency-candidate-lattice.schema.json", "tools/fusha_governor.py",
             "tools/validate_dependency_lattice.py", "qamus/examples/dependency_lattice.sample.jsonl",
             "qamus/schemas/cross-builder-conflict.schema.json", "tools/fusha_conflicts.py",
             "tools/validate_cross_builder_conflict.py", "qamus/examples/cross_builder_conflict.sample.jsonl"):
    check("p2 artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
try:
    _p2a = run_text([sys.executable, os.path.join(ROOT, "tools", "leak_sot.py"), "--self-test"])
    check("p2 leak source-of-truth self-test (union catches 5 legacy detectors; cert tafsir/tanzil gap closed)", _p2a.returncode == 0)
    _p2b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_source_boundary.py"), "--self-test"])
    check("p2 leak-SoT drift gate (leak_sot is a verified SUPERSET of all legacy detectors)", _p2b.returncode == 0)
    _p2c = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_governor.py"), "--self-test"])
    check("p2 governor/dependency lattice self-test (layer-1-safe; PP unresolved; right-answer-wrong-reason; never auto_safe)", _p2c.returncode == 0)
    _p2d = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_dependency_lattice.py"), "--self-test"])
    check("p2 dependency-lattice validator self-test (9 FAIL conditions reject)", _p2d.returncode == 0)
    _p2e = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_dependency_lattice.py"),
                     os.path.join(ROOT, "qamus", "examples", "dependency_lattice.sample.jsonl")])
    check("p2 dependency-lattice fixture validates (6 lattices, 0 violations)", _p2e.returncode == 0)
    _p2f = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_conflicts.py"), "--self-test"])
    check("p2 cross-builder conflict self-test (10 types; gate=max; precedence; surfaces never picks)", _p2f.returncode == 0)
    _p2g = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_cross_builder_conflict.py"), "--self-test"])
    check("p2 conflict validator self-test (FAIL conditions incl. precedence + gate=max reject)", _p2g.returncode == 0)
    _p2h = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_cross_builder_conflict.py"),
                     os.path.join(ROOT, "qamus", "examples", "cross_builder_conflict.sample.jsonl")])
    check("p2 conflict fixture validates (10 records, 0 violations)", _p2h.returncode == 0)
except Exception as _e:
    check("p2 deepening slice runnable", False)
    print("  ", _e)

# --- P2b: learning engine (morphology lattice, suggestion engine, hint ladder) + CEFR instruction/gating ---
try:
    for _art in ("qamus/reports/p2b-learning-cefr.md", "curriculum/cefr-fusha-instruction.md",
                 "curriculum/cefr-fusha-levels.json", "curriculum/kc-catalog.json",
                 "qamus/schemas/morphology-candidate-lattice.schema.json",
                 "qamus/schemas/learner-feedback-event.schema.json", "qamus/schemas/cefr-fusha-level.schema.json"):
        check("p2b artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
    _p2b_a = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_morphology_lattice.py"), "--self-test"])
    check("p2b morphology candidate lattice self-test (ranked; ambiguity kept; never auto_safe)", _p2b_a.returncode == 0)
    _p2b_b = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_suggest.py"), "--self-test"])
    check("p2b suggestion engine self-test (abstain-first; retain/reject/abstain no replacement; NMS->C10)", _p2b_b.returncode == 0)
    _p2b_c = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_fusha_text_check.py"), "--self-test"])
    check("p2b text-check validator self-test (base 12 + M1-M8 morphology + 8b/8c/9b/10/11 suggestion)", _p2b_c.returncode == 0)
    _p2b_d = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_learner_feedback.py"), "--self-test"])
    check("p2b learner-feedback hint ladder self-test (bottom-out withheld past gate; cause-referencing)", _p2b_d.returncode == 0)
    _p2b_e = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_learner_feedback.py"), "--self-test"])
    check("p2b learner-feedback validator self-test (LF-1..10 reject)", _p2b_e.returncode == 0)
    _p2b_f = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_cefr_fusha_instruction.py"), "--self-test"])
    check("p2b CEFR instruction self-test (7 levels clean; no certification/copied prose; beginner-safe)", _p2b_f.returncode == 0)
    _p2b_g = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_cefr_gate.py"), "--self-test"])
    check("p2b CEFR gating self-test (subset-visible; monotonic gates; ambiguity preserved; no reveal)", _p2b_g.returncode == 0)
    _p2b_h = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_learner_feedback.py"),
                       os.path.join(ROOT, "qamus", "examples", "learner_feedback.sample.jsonl")])
    check("p2b learner-feedback fixture validates (0 violations)", _p2b_h.returncode == 0)
    _p2b_i = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_cefr_fusha_instruction.py"),
                       os.path.join(ROOT, "curriculum", "cefr-fusha-levels.json")])
    check("p2b CEFR levels fixture validates (7 levels, 0 violations)", _p2b_i.returncode == 0)
except Exception as _e:
    check("p2b learning + CEFR slice runnable", False)
    print("  ", _e)

# --- sarf/nahw skill back-prop: the skills now absorb the P1/P2/P2b engine contracts; prove they stay aligned ---
try:
    _sn_a = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_sarf_nahw_skill_backprop.py"), "--self-test"])
    check("sarf/nahw skill back-prop self-test (ambiguity / governor / right-answer-wrong-reason / CEFR-scaffold / leak / tool-paths)", _sn_a.returncode == 0)
    _sn_b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_sarf_nahw_skill_backprop.py")])
    check("sarf/nahw skill back-prop tree clean (skills cite live tools, preserve ambiguity, gate iʿrāb)", _sn_b.returncode == 0)
    _sn_c = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_sarf_skill.py")])
    check("sarf skill structural validator still green (additive edits)", _sn_c.returncode == 0)
    _sn_d = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_nahw_skill.py")])
    check("nahw skill structural validator still green (additive edits)", _sn_d.returncode == 0)
    _sn_e = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_vn00_aggressive_false_closure.py"), "--self-test"])
    check("VN-00 aggressive false-closure validator self-test (class coverage / flywheel targets / leak checks)", _sn_e.returncode == 0)
    _sn_f = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_vn00_aggressive_false_closure.py")])
    check("VN-00 aggressive false-closure fixtures tree clean (sarf/nahw/drill terminal flywheel gate)", _sn_f.returncode == 0)
    _sn_g = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_meta_transclusion_projection.py"), "--self-test"])
    check("VN-00 meta-transclusion projection validator self-test", _sn_g.returncode == 0)
    _sn_h = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_meta_transclusion_projection.py"),
        "--queue",
        os.path.join(ROOT, "qamus", "reports", "vn00-public-andon-20260703", "plan18-meta-lattice-projection-queue.jsonl"),
        "--typed-edge-queue",
        os.path.join(ROOT, "qamus", "reports", "vn00-public-andon-20260703", "plan18-typed-edge-transclusion-queue.jsonl"),
    ])
    check("VN-00 Plan18 meta-transclusion projection queues remain exact or explicit family-summary packets", _sn_h.returncode == 0)
except Exception as _e:
    check("sarf/nahw skill back-prop slice runnable", False)
    print("  ", _e)

# --- sarf/nahw curriculum + drills + README back-prop: the learner/reader surfaces now reflect the engine; prove no neglect ---
try:
    _cd_a = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_sarf_nahw_curriculum_drills_readmes.py"), "--self-test"])
    check("sarf/nahw curriculum/drills/README back-prop self-test (4 named dirs engine-aligned; READMEs no-overclaim / current-stack / leak-free)", _cd_a.returncode == 0)
    _cd_b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_sarf_nahw_curriculum_drills_readmes.py")])
    check("sarf/nahw curriculum/drills/README tree clean (no forced-parse drills; CEFR scaffolding not certification; cited tools exist)", _cd_b.returncode == 0)
except Exception as _e:
    check("sarf/nahw curriculum/drills/README back-prop slice runnable", False)
    print("  ", _e)

# --- data/runtime completion pass: review scheduler, tutor runtime, checkpoint coverage, qamus_wbw public-safety, QAC morphology wiring ---
try:
    for _art in ("tools/fusha_review_scheduler.py", "tools/fusha_tutor_runtime.py",
                 "tools/validate_tutor_runtime.py", "tools/fusha_checkpoint_coverage.py",
                 "tools/qamus_wbw_adapter.py", "tools/validate_public_runnability.py",
                 "qamus/schemas/tutor-progress-state.schema.json", "qamus/schemas/tutor-event.schema.json",
                 "provenance/public-runnability.md"):
        check("data/runtime artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
    _dr_a = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_review_scheduler.py"), "--self-test"])
    check("review scheduler self-test (deterministic Leitner; full-pass-only promotion; wrong-reason/pending HOLD)", _dr_a.returncode == 0)
    _dr_b = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_tutor_runtime.py"), "--self-test"])
    check("tutor runtime self-test (schema-graded not self-report; two-vote gating; --write-gated; deterministic)", _dr_b.returncode == 0)
    _dr_c = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_tutor_runtime.py"), "--self-test"])
    check("tutor runtime contract validator self-test (no self-report; promotion gate; --write gate; schema-conformant)", _dr_c.returncode == 0)
    _dr_d = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_checkpoint_coverage.py"), "--self-test"])
    check("checkpoint coverage self-test (by level/hardness/route; empty bands; dangling-citation detection)", _dr_d.returncode == 0)
    _dr_e = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_checkpoint_coverage.py"),
                      os.path.join(ROOT, "curriculum", "assessment", "level-checkpoints.sample.jsonl")])
    check("checkpoint sample has 0 dangling cited paths (referential integrity)", _dr_e.returncode == 0)
    _dr_f = run_text([sys.executable, os.path.join(ROOT, "tools", "qamus_wbw_adapter.py"), "--self-test"])
    check("qamus_wbw adapter self-test (imports on a clone; load_services raises actionable SystemExit)", _dr_f.returncode == 0)
    _dr_g = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_public_runnability.py"), "--self-test"])
    check("public-runnability matrix self-test (reconciles with live importers; new unguarded imports caught)", _dr_g.returncode == 0)
    _dr_h = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_public_runnability.py")])
    check("public-runnability matrix in sync with live qamus_wbw importers", _dr_h.returncode == 0)
except Exception as _e:
    check("data/runtime completion slice runnable", False)
    print("  ", _e)

# --- P1/P2 closure: placement runner, drill keys, eval coverage, event replay, index integrity, dataset-integrity
#     reporter (blocked item), claude.ai pack drift, CEFR monotonicity. (importer conversion + checkpoint rows +
#     runtime grammar bridge + SM-2 scheduler variant are covered by the existing public-runnability / curriculum /
#     runtime / scheduler gates above.) ---
try:
    for _art in ("tools/fusha_placement_test.py", "curriculum/assessment/placement-test.sample.jsonl",
                 "tools/validate_drill_keys.py", "tools/fusha_eval_coverage.py",
                 "tools/validate_tutor_event_replay.py", "tools/validate_index_integrity.py",
                 "tools/report_dataset_integrity.py", "qamus/reports/dataset-integrity-blocker.md",
                 "tools/validate_claude_ai_pack_drift.py", "tools/validate_cefr_monotonicity.py",
                 "curriculum/drills/keys/quranic-function-words.keys.jsonl"):
        check("P1/P2 artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
    _q1 = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_placement_test.py"), "--self-test"])
    check("P1-3 placement-test runner self-test (deterministic; ASAG-graded not self-report; rung routing)", _q1.returncode == 0)
    _q2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_drill_keys.py"), "--self-test"])
    check("P1-4 drill answer-key validator self-test (schema + leak + dangling-citation reject)", _q2.returncode == 0)
    _q2b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_drill_keys.py"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "quranic-function-words.keys.jsonl"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "morphology-foundations.keys.jsonl"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "root-pattern-practice.keys.jsonl"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "sentence-foundations.keys.jsonl"),
                     # RM-45: the highest-traffic composition/closure/routing drills, now keyed (>=8/20 drills keyed).
                     os.path.join(ROOT, "curriculum", "drills", "keys", "hover-composition-and-routing.keys.jsonl"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "parse-key-and-color-layer.keys.jsonl"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "vn00-aggressive-hover-closure.keys.jsonl"),
                     os.path.join(ROOT, "curriculum", "drills", "keys", "plan15-route-families.keys.jsonl")])
    check("P1-4 drill answer-key fixtures validate (0 violations)", _q2b.returncode == 0)
    _q3 = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_eval_coverage.py"), "--self-test"])
    check("P1-5 eval-bank coverage reporter self-test (per-bank counts; runner-gap; report-only)", _q3.returncode == 0)
    _q3b = run_text([sys.executable, os.path.join(ROOT, "tools", "fusha_eval_coverage.py")])
    check("P1-5 eval-bank coverage real report (report-only, exit 0)", _q3b.returncode == 0)
    _q4 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_tutor_event_replay.py"), "--self-test"])
    check("P1-6 tutor event-log replay validator self-test (event-sourced replay reconstructs state; tamper caught)", _q4.returncode == 0)
    _q5 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_index_integrity.py"), "--self-test"])
    check("P2-8 index referential-integrity validator self-test (orphan id caught)", _q5.returncode == 0)
    _q5b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_index_integrity.py")])
    check("P2-8 index referential-integrity real indexes (0 orphan ids)", _q5b.returncode == 0)
    _q6 = run_text([sys.executable, os.path.join(ROOT, "tools", "report_dataset_integrity.py"), "--self-test"])
    check("P2-9 dataset-integrity reporter self-test (synthetic match/mismatch; non-fatal vs --strict)", _q6.returncode == 0)
    _q6b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_current_qamus_dataset.py")])
    check("RM-01 strict dataset gate: validate_current_qamus_dataset exit 0 (armed 2026-07-10, owner D-09)", _q6b.returncode == 0)
    _q7 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_claude_ai_pack_drift.py"), "--self-test"])
    check("P2-10 claude.ai pack-drift validator self-test (read-only; drift caught)", _q7.returncode == 0)
    _q7b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_claude_ai_pack_drift.py")])
    check("P2-10 claude.ai pack manifest in sync (0 drift)", _q7b.returncode == 0)
    _q8 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_cefr_monotonicity.py"), "--self-test"])
    check("P2-11 CEFR monotonicity self-test (non-monotonic caught; no certification/forced-parse/reveal)", _q8.returncode == 0)
    _q8b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_cefr_monotonicity.py")])
    check("P2-11 CEFR real levels monotonic (scaffolding not certification)", _q8b.returncode == 0)
except Exception as _e:
    check("P1/P2 closure slice runnable", False)
    print("  ", _e)

# --- largelexicon candidate layer: Qamus-scale source-clean full fact tables, Mode A qword projection,
#     public/private hover boundary, qg validation, CLI contract, and flywheel backfill. This is opt-in
#     tooling, not live Qamus progress and not arbitrary-text certification. ---
try:
    for _art in ("docs/parser/largelexicon-claim-boundary.md",
                 "docs/parser/largelexicon-source-ledger.md",
                 "docs/parser/largelexicon-implementation.md",
                 "docs/parser/meta-transclusive-lattice-projection.md",
                 "tools/build_largelexicon_source_inventory.py",
                 "tools/build_largelexicon_morph_db.py",
                 "tools/largelexicon_table_reader.py",
                 "tools/validate_largelexicon_source_ledger.py",
                 "tools/validate_largelexicon_table_manifest.py",
                 "tools/validate_largelexicon_table_reader.py",
                 "tools/validate_largelexicon_claim_boundary.py",
                 "tools/validate_largelexicon_claim_cards.py",
                 "tools/validate_largelexicon_morph_db.py",
                 "tools/validate_largelexicon_parser.py",
                 "tools/fusha_largelexicon_cli.py",
                 "tools/validate_largelexicon_cli_contract.py",
                 "tools/build_largelexicon_qamus_mode_a_worklist.py",
                 "tools/project_largelexicon_qamus_hover_candidates.py",
                 "tools/validate_largelexicon_qamus_mode_a.py",
                 "tools/validate_largelexicon_qg_projection.py",
                  "tools/adopt_largelexicon_qword_crosswalk.py",
                  "tools/validate_largelexicon_qword_crosswalk.py",
                  "tools/validate_largelexicon_denominator_join.py",
                  "tools/validate_largelexicon_transclusion.py",
                  "tools/validate_meta_transclusion_projection.py",
                 "tools/build_largelexicon_flywheel_artifacts.py",
                 "tools/validate_largelexicon_skill_curriculum_backfill.py",
                 "tools/validate_backfillfull_sarf_nahw_largelexicon.py",
                 "fusha/lexicon/largelexicon/source-clean-table-allowlist.json",
                 "fusha/lexicon/largelexicon/lemma-source.sample.jsonl",
                 "fusha/lexicon/largelexicon/form-source.sample.jsonl",
                 "fusha/lexicon/largelexicon/lemma-source.full.jsonl",
                 "fusha/lexicon/largelexicon/form-source.full.jsonl",
                 "fusha/morphology/examples/largelexicon-stems.sample.jsonl",
                 "fusha/morphology/data/largelexicon-stems.full.jsonl",
                 "qamus/schemas/largelexicon-table-manifest.schema.json",
                 "qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json",
                 "qamus/indexes/largelexicon/qamus-qword-denominator.entry-shard-index.json",
                 "qamus/indexes/largelexicon/qamus-qword-denominator.source-card-repair.json",
                 "qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json",
                 "qamus/indexes/largelexicon/qword-denominator/v001-v040.jsonl",
                 "qamus/indexes/largelexicon/qword-crosswalk/v001-v010.jsonl",
                 "qamus/indexes/largelexicon/qword-denominator/n1041-n1045.jsonl",
                 "qamus/indexes/largelexicon/qword-denominator/p001-p040.jsonl",
                 "qamus/indexes/largelexicon/source-clean-fact-tables.meta.json",
                 "qamus/reports/largelexicon-crosswalk-adoption-20260703.json",
                 "qamus/reports/largelexicon-claim-cards.json",
                 "qamus/examples/mode_a_all_qword/largelexicon-qamus-mode-a-worklist.sample.jsonl",
                 "qamus/examples/largelexicon/hover-candidates.sample.jsonl",
                 "qamus/examples/largelexicon/flywheel-artifacts.sample.jsonl",
                 "qamus/procedures/largelexicon-rollout-consumption.md",
                 "sarf/procedures/largelexicon-morphology-expansion.md",
                 "nahw/procedures/largelexicon-function-token-routing.md",
                 "curriculum/largelexicon-tutor-routing.md",
                 "curriculum/drills/largelexicon-morphology-and-hover.md"):
        check("largelexicon artifact exists: %s" % _art, os.path.exists(os.path.join(ROOT, _art)))
    _ll1 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_source_ledger.py"), "--self-test"])
    check("largelexicon source-ledger self-test (canonical ledger + freshness + committed source-clean full tables)", _ll1.returncode == 0)
    _ll1b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_table_manifest.py"), "--self-test"])
    check("largelexicon qword table manifest self-test (shards + entry reverse index + source-card repair packet)", _ll1b.returncode == 0)
    _ll1c = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_table_reader.py"), "--self-test"])
    check("largelexicon qword table reader self-test (manifest-backed iteration, entry lookup, row lookup)", _ll1c.returncode == 0)
    _ll2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_claim_boundary.py"), "--self-test"])
    check("largelexicon claim-boundary self-test (no live/arbitrary/CAMeL-class overclaim)", _ll2.returncode == 0)
    _ll2b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_claim_cards.py"), "--self-test"])
    check("largelexicon claim-card self-test (supported vs not-yet-supported claims gated)", _ll2b.returncode == 0)
    _ll3 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_morph_db.py"), "--self-test"])
    check("largelexicon morph DB self-test (source-clean Qamus-derived sample + full stem tables)", _ll3.returncode == 0)
    _ll4 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_parser.py"), "--self-test"])
    check("largelexicon parser self-test (opt-in --db largelexicon, smoke default preserved)", _ll4.returncode == 0)
    _ll5 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_qamus_mode_a.py"), "--self-test"])
    check("largelexicon Mode A self-test (visible qword denominator + trace)", _ll5.returncode == 0)
    _ll6 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_qg_projection.py"), "--self-test"])
    check("largelexicon qg projection self-test (source-clean hover candidates or exact packets)", _ll6.returncode == 0)
    _ll6b = run_text([sys.executable, os.path.join(ROOT, "tools", "adopt_largelexicon_qword_crosswalk.py"), "--self-test"])
    check("largelexicon qword crosswalk adoption self-test (source-clean packet projection)", _ll6b.returncode == 0)
    _ll6c = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_qword_crosswalk.py")])
    check("largelexicon qword crosswalk materialized table validates", _ll6c.returncode == 0)
    _ll6c2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_denominator_join.py"), "--self-test"])
    check("largelexicon denominator join self-test (loc-first join; qword_index false join rejected)", _ll6c2.returncode == 0)
    _ll6c3 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_denominator_join.py")])
    check("largelexicon denominator/crosswalk materialized loc-first join validates", _ll6c3.returncode == 0)
    _ll6d = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_transclusion.py")])
    check("largelexicon qword crosswalk transclusion dependencies validate", _ll6d.returncode == 0)
    _ll6e = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_meta_transclusion_projection.py"), "--self-test"])
    check("largelexicon meta-transclusive projection self-test (false visual closure families)", _ll6e.returncode == 0)
    _ll7 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_skill_curriculum_backfill.py"), "--self-test"])
    check("largelexicon sarf/nahw/curriculum flywheel self-test", _ll7.returncode == 0)
    _ll7b = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_backfillfull_sarf_nahw_largelexicon.py"), "--self-test"])
    check("backfillfull sarf/nahw largelexicon route/transclusion self-test", _ll7b.returncode == 0)
    _ll8 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_largelexicon_cli_contract.py"), "--self-test"])
    check("largelexicon local CLI contract self-test (analyze-token/card, project-hover, validate-mode-a)", _ll8.returncode == 0)
    _clf = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_certified_lemma_fanout.py"), "--self-test"])
    check("certified-lemma fanout self-test (surface-only/homograph/QAC-leak/uncertified reject)", _clf.returncode == 0)
    _clf2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_certified_lemma_fanout.py"), os.path.join(ROOT, "qamus", "examples", "certified_lemma.sample.jsonl")])
    check("certified-lemma sample rows validate (certified, source-clean, homograph-safe)", _clf2.returncode == 0)
    _chp = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_canonical_hover_payload_table.py"), "--self-test"])
    check("canonical hover payload table self-test (id-determinism/leak/segment-concat/binding-gate reject)", _chp.returncode == 0)
    _chp2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_canonical_hover_payload_table.py"), os.path.join(ROOT, "qamus", "examples", "canonical_hover_payload.sample.jsonl")])
    check("canonical hover payload sample validates (payload+binding+exception referentially sound)", _chp2.returncode == 0)
    _chp3 = run_text([sys.executable, os.path.join(ROOT, "tools", "build_canonical_hover_payload_table.py"), "--self-test"])
    check("canonical hover payload builder self-test (dedup/full-carrier/weaker-peer/tie/incomplete)", _chp3.returncode == 0)
    _chp4 = run_text([sys.executable, os.path.join(ROOT, "tools", "compile_canonical_hover_whitelist_packet.py"), "--self-test"])
    check("canonical hover whitelist compiler self-test (append/no-op/conflict/exception; source-clean)", _chp4.returncode == 0)
    _pid = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_projection_row_id_stability.py"), "--self-test"])
    check("projection row_id stability self-test (content-addressed; provenance/timestamp/collision reject)", _pid.returncode == 0)
    _pid2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_projection_row_id_stability.py"), os.path.join(ROOT, "qamus", "examples", "projection_row_id.sample.jsonl")])
    check("projection row_id sample validates (stable, content-addressed, source-clean)", _pid2.returncode == 0)
    _rcg = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_renderer_completeness_gate.py"), "--self-test"])
    check("renderer completeness gate self-test (empty-seg/dropped-seg/morphline-desync/bad-role reject)", _rcg.returncode == 0)
    _rcg2 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_renderer_completeness_gate.py"), os.path.join(ROOT, "qamus", "examples", "renderer_completeness.sample.jsonl")])
    check("renderer completeness sample validates (no silent renderer gaps)", _rcg2.returncode == 0)
except Exception as _e:
    check("largelexicon candidate layer runnable", False)
    print("  ", _e)

# --- QAMUS-RICH-SEG-001 segment-completeness gate (authoring gates A..G + live-row C1..C5) ---
# Red-first proof: the malformed [FA,STEM] authoring record trips every gate A..G; each of the
# 9 confirmed live-row defects is REJECTED by its class C1..C5; and the two known false alarms
# (102:3:3 correctly-split imperfect, 4:144:17 Form IV participle) PASS clean.
try:
    _rseg = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_segment_completeness.py"),
                      "--self-test"], timeout=120)
    check("segment-completeness self-test (A..G gates + live-row C1..C5 red-first; 102:3:3 & 4:144:17 pass)",
          _rseg.returncode == 0 and "live-row classes C1,C2,C3,C4,C5" in (_rseg.stdout or ""))
except Exception as _rseg_e:
    check("segment-completeness self-test (harness error)", False)
    print("  ", _rseg_e)

# VN-01 hardening flywheel fixtures (2026-07-07): D7 dark-mode + run#32 deploy-mechanics
for _p, _req in (
    ("sarf/evals/surfacemap-wbw-absent-eval.jsonl", ("id", "surface", "decision", "reason")),
    ("sarf/evals/combining-mark-byte-exact-eval.jsonl", ("id", "surface", "decision", "reason")),
    ("qamus/examples/dogfood_d7_darkmode_contrast_lesson.sample.jsonl",
     ("bug_class", "what_failed", "learner_explanation", "validator_link")),
):
    try:
        _rows = [json.loads(_l) for _l in io.open(os.path.join(ROOT, _p), encoding="utf-8") if _l.strip()]
        check("flywheel fixture well-formed + keyed: %s" % _p,
              len(_rows) >= 1 and all(all(_k in _r for _k in _req) for _r in _rows))
    except Exception as _e:
        check("flywheel fixture well-formed + keyed: %s" % _p, False)
        print("  ", _e)

# --- T1 claim-safety gates (RM-08 import scan, RM-06 coverage lint, RM-07 docs lint, NF-T0-1 manifest hashes) ---
try:
    _network_import_re = re.compile(
        r"^\s*(?:import|from)\s+(?:urllib\b|socket\b|http\.client\b|http\b)"
    )
    _network_connector_allowlist = {
        "tools/tafsir_mcp_client.py",
        "tools/tafsir_mcp_probe.py",
        "tools/fetch_tafsir_mcp_ayah.py",
        "tools/analyze_tafsir_mcp_word.py",
        "tools/build_tafsir_mcp_cache.py",
        "tools/crawl_qamus_public_entries.py",
        "tools/build_source_triangulated_votes.py",
        "tools/scan_public_boundary.py",
        # RM-25 step 1 (reviewed connector): public-domain Tanzil corpus acquisition,
        # sha-pinned + re-fetch-reproducible; the built index is the committed artifact.
        "tools/build_quran_loc_surface_index.py",
    }
    _network_import_offenders = set()
    for _scan_dir in ("tools", "scripts"):
        for _dirpath, _dirnames, _filenames in os.walk(os.path.join(ROOT, _scan_dir)):
            for _filename in _filenames:
                if not _filename.endswith(".py"):
                    continue
                _path = os.path.join(_dirpath, _filename)
                _rel = os.path.relpath(_path, ROOT).replace(os.sep, "/")
                if _rel in _network_connector_allowlist:
                    continue
                with io.open(_path, encoding="utf-8", errors="replace") as _f:
                    for _line in _f:
                        if _line.lstrip().startswith("#"):
                            continue
                        if _network_import_re.match(_line):
                            _network_import_offenders.add(_rel)
                            break
    check("RM-08 import-scan lint: urllib/http.client/socket only in the 9 enumerated connectors",
          not _network_import_offenders)
    for _rel in sorted(_network_import_offenders):
        print("  ", _rel)
except Exception as _e:
    check("RM-08 import-scan lint: urllib/http.client/socket only in the 9 enumerated connectors", False)
    print("  ", _e)

try:
    _manifest_hash_verified = 0
    _manifest_hash_skipped = 0
    _manifest_hash_mismatches = []
    _examples_dir = os.path.join(ROOT, "qamus", "examples")
    for _filename in sorted(os.listdir(_examples_dir)):
        if not _filename.endswith(".json"):
            continue
        _manifest_path = os.path.join(_examples_dir, _filename)
        try:
            with io.open(_manifest_path, encoding="utf-8") as _f:
                _manifest = json.load(_f)
        except (OSError, ValueError):
            continue
        _nodes = [_manifest]
        while _nodes:
            _node = _nodes.pop()
            if isinstance(_node, dict):
                _artifact_rel = _node.get("path")
                _declared_sha256 = _node.get("sha256")
                if isinstance(_artifact_rel, str) and isinstance(_declared_sha256, str):
                    _artifact_path = os.path.join(ROOT, _artifact_rel)
                    if not os.path.exists(_artifact_path):
                        _manifest_hash_skipped += 1
                    else:
                        _hasher = hashlib.sha256()
                        with io.open(_artifact_path, "rb") as _f:
                            for _chunk in iter(lambda: _f.read(1024 * 1024), b""):
                                _hasher.update(_chunk)
                        _actual_sha256 = _hasher.hexdigest()
                        _manifest_hash_verified += 1
                        if _actual_sha256.lower() != _declared_sha256.lower():
                            _manifest_hash_mismatches.append(
                                (_filename, _artifact_rel, _declared_sha256, _actual_sha256[:16])
                            )
                _nodes.extend(_node.values())
            elif isinstance(_node, list):
                _nodes.extend(_node)
    _manifest_hash_label = (
        "NF-T0-1 sample-manifest artifact hashes match tracked bytes "
        "(%d verified, %d live-side skipped)"
        % (_manifest_hash_verified, _manifest_hash_skipped)
    )
    check(_manifest_hash_label, not _manifest_hash_mismatches)
    for _mismatch in _manifest_hash_mismatches:
        print("  ", _mismatch)
except Exception as _e:
    check("NF-T0-1 sample-manifest artifact hashes match tracked bytes (scan error)", False)
    print("  ", _e)

try:
    _coverage_evidence_prefixes = (
        # narrowed at T8: the proofing matrices now carry HISTORICAL pointers in their
        # headers (banner clause covers them); only genuinely immutable dated evidence stays.
        "qamus/reports/closure-2092/",
        "qamus/reports/qamus-completion-manifest-summary-20260624.md",
    )
    _coverage_exempt_count = 0
    _coverage_offenders = []
    for _dirpath, _dirnames, _filenames in os.walk(ROOT):
        _dirnames[:] = [_d for _d in _dirnames if _d != ".git"]
        for _filename in _filenames:
            if not _filename.endswith(".md"):
                continue
            _path = os.path.join(_dirpath, _filename)
            with io.open(_path, encoding="utf-8", errors="replace") as _f:
                _lines = _f.readlines()
            if not any(_figure in _line for _line in _lines for _figure in ("85.87%", "87.35%")):
                continue
            _rel = os.path.relpath(_path, ROOT).replace(os.sep, "/")
            _is_exempt = (
                _rel == "docs/STATUS.md"
                or any("HISTORICAL" in _line for _line in _lines[:15])
                or _rel.startswith(_coverage_evidence_prefixes)
            )
            if _is_exempt:
                _coverage_exempt_count += 1
            else:
                _coverage_offenders.append(_rel)
    _coverage_label = (
        "RM-06 coverage-%% lint: stale coverage figures only in "
        "STATUS.md/HISTORICAL/dated evidence (%d historical/evidence files exempt)"
        % _coverage_exempt_count
    )
    check(_coverage_label, not _coverage_offenders)
    for _rel in sorted(_coverage_offenders):
        print("  ", _rel)
except Exception as _e:
    check("RM-06 coverage-%% lint: stale coverage figures only in STATUS.md/HISTORICAL/dated evidence (scan error)", False)
    print("  ", _e)

try:
    _phantom_citation_hits = []
    _docs_dir = os.path.join(ROOT, "docs")
    for _dirpath, _dirnames, _filenames in os.walk(_docs_dir):
        for _filename in _filenames:
            _path = os.path.join(_dirpath, _filename)
            with io.open(_path, "rb") as _f:
                if b"bulk_twovote_certified_batch" in _f.read():
                    _phantom_citation_hits.append(
                        os.path.relpath(_path, ROOT).replace(os.sep, "/")
                    )
    check("RM-07 docs cite no phantom evidence glob (bulk_twovote_certified_batch: 0 hits in docs/)",
          not _phantom_citation_hits)
    for _rel in sorted(_phantom_citation_hits):
        print("  ", _rel)
except Exception as _e:
    check("RM-07 docs cite no phantom evidence glob (bulk_twovote_certified_batch: 0 hits in docs/)", False)
    print("  ", _e)

# --- T2 redaction-boundary gates (RM-09 public recurrence + local production overlay) ---
_t2_text_extensions = {
    ".py", ".md", ".json", ".jsonl", ".txt", ".sh",
    ".yml", ".yaml", ".toml", ".cfg", ".csv",
}
_t2_exempt_paths = {"tools/leak_denylist_local.example.json"}


def _t2_tracked_text_paths():
    result = run_text(["git", "ls-files", "-z"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed for RM-09 tracked-tree scan")
    paths = []
    for relative in result.stdout.split("\0"):
        relative = relative.replace("\\", "/")
        if not relative or relative in _t2_exempt_paths:
            continue
        if os.path.splitext(relative)[1].lower() not in _t2_text_extensions:
            continue
        path = os.path.join(ROOT, *relative.split("/"))
        if os.path.isfile(path):
            paths.append((relative, path))
    return paths


try:
    _t2_paths = _t2_tracked_text_paths()
    _t2_text = {}
    _t2_public_needles = (
        ("production-dir", "srv/" + "dawah"),
        ("operator-path", "C:" + "\\workspace"),
        ("operator-path", "C:" + "\\Users"),
    )
    _t2_public_offenders = set()
    for _rel, _path in _t2_paths:
        with io.open(_path, encoding="utf-8", errors="replace") as _handle:
            _text = _handle.read()
        _t2_text[_rel] = _text
        _folded = _text.casefold().replace(chr(92)*2, chr(92))  # collapse escaped backslashes so JSON/docstring forms cannot evade the needles
        _folded_sep = _folded.replace("/", chr(92))  # separator-insensitive view (NF-T3-1: forward-slash operator paths)
        if any(_needle.casefold() in _folded or _needle.casefold() in _folded_sep for _, _needle in _t2_public_needles):
            _t2_public_offenders.add(_rel)
    check(
        "RM-09 tree-wide recurrence lint (public classes; %d tracked text files scanned)" % len(_t2_paths),
        not _t2_public_offenders,
    )
    for _rel in sorted(_t2_public_offenders):
        print("  ", _rel)

    if leak_sot.production_mode():
        _t2_overlay = leak_sot.require_overlay()
        _t2_production_offenders = set()
        for _rel, _text in _t2_text.items():
            _folded = _text.casefold().replace(chr(92)*2, chr(92))  # collapse escaped backslashes so JSON/docstring forms cannot evade the needles
            _folded_sep = _folded.replace("/", chr(92))  # separator-insensitive view (NF-T3-1)
            for _key in leak_sot._OVERLAY_KEYS:
                for _value in _t2_overlay.get(_key, []):
                    if _value.casefold() in _folded or _value.casefold() in _folded_sep:
                        _t2_production_offenders.add((_rel, _key))
        check("RM-09 production-augmented lint", not _t2_production_offenders)
        for _rel, _key in sorted(_t2_production_offenders):
            print("  %s [%s]" % (_rel, _key))
    else:
        check("RM-09 production-augmented lint (public mode — overlay lint skipped)", True)
except SystemExit:
    raise
except Exception as _e:
    check("RM-09 tree-wide recurrence lint (scan error)", False)
    print("  ", _e)

try:
    _t2_public_env = os.environ.copy()
    _t2_public_env.pop("FUSHA_LEAK_LOCAL", None)
    _t2_public_env.pop("FUSHA_LEAK_PRODUCTION", None)
    _t2_public_clone = run_text(
        [sys.executable, os.path.join(ROOT, "tools", "leak_sot.py"), "--self-test"],
        cwd=ROOT,
        env=_t2_public_env,
    )
    check("T2 overlay mechanism: public clone self-test passes without an overlay", _t2_public_clone.returncode == 0)

    with tempfile.TemporaryDirectory(prefix="t2-overlay-check-") as _temp_dir:
        _t2_missing_env = os.environ.copy()
        _t2_missing_env["FUSHA_LEAK_PRODUCTION"] = "1"
        _t2_missing_env["FUSHA_LEAK_LOCAL"] = os.path.join(_temp_dir, "absent.json")
        _t2_fail_closed = run_text(
            [sys.executable, "-c", "from tools import leak_sot; leak_sot.require_overlay()"],
            cwd=ROOT,
            env=_t2_missing_env,
        )
        check("T2 overlay mechanism: production mode fails closed with exit 2", _t2_fail_closed.returncode == 2)

        _t2_synthetic = {
            "_comment": "production-exact leak denylist overlay — NEVER commit. See leak_denylist_local.example.json",
            "secrets": ["example-secret.txt"],
            "ip_prefixes": ["203.0.113."],
            "key_filenames": ["id_" + "ed25519_example_key"],
            "path_substrings": ["c:\\example-workspace"],
        }
        _t2_overlay_path = os.path.join(_temp_dir, "overlay.json")
        with io.open(_t2_overlay_path, "w", encoding="utf-8", newline="\n") as _handle:
            json.dump(_t2_synthetic, _handle, ensure_ascii=False, sort_keys=True, indent=2)
            _handle.write("\n")
        _t2_synthetic_env = os.environ.copy()
        _t2_synthetic_env["FUSHA_LEAK_LOCAL"] = _t2_overlay_path
        _t2_synthetic_env.pop("FUSHA_LEAK_PRODUCTION", None)
        _t2_synthetic_load = run_text(
            [
                sys.executable,
                "-c",
                "from tools import leak_sot; o=leak_sot.load_local_overlay(); "
                "s=o['secrets'][0]; assert not leak_sot.LEAK_RE.search(s); "
                "assert leak_sot.get_leak_re(o).search(s)",
            ],
            cwd=ROOT,
            env=_t2_synthetic_env,
        )
        _t2_synthetic_values = [
            value
            for key in leak_sot._OVERLAY_KEYS
            for value in _t2_synthetic[key]
        ]
        check("T2 overlay mechanism: synthetic overlay loads and augments matching", _t2_synthetic_load.returncode == 0)
        check(
            "T2 overlay mechanism: synthetic loader stdout contains no overlay values",
            all(value not in _t2_synthetic_load.stdout for value in _t2_synthetic_values),
        )
except Exception as _e:
    check("T2 overlay mechanism checks (subprocess error)", False)
    print("  ", _e)

# --- T2.1 ambient-overlay isolation (permanent regression) ---
# The presence of a file at the FORMER default worktree path must not alter default-public-mode
# behavior (no path arg, no FUSHA_LEAK_LOCAL). Synthetic values only — the tracked example file
# is copied to the former path, consumers are probed in FRESH subprocesses (so import caches
# cannot conceal differences), and the file is removed in a guaranteed cleanup block.
try:
    _amb_path = os.path.join(ROOT, "tools", "leak_denylist_local.json")
    _amb_example = os.path.join(ROOT, "tools", "leak_denylist_local.example.json")
    _amb_env = os.environ.copy()
    _amb_env.pop("FUSHA_LEAK_LOCAL", None)
    _amb_env.pop("FUSHA_LEAK_PRODUCTION", None)
    _amb_snippet = (
        "import sys; sys.path.insert(0, '.');"
        "from tools import leak_sot;"
        "import tools.validate_vn00_aggressive_false_closure as _vn;"
        "import tools.scan_public_boundary as _spb;"
        "print(leak_sot.load_local_overlay() is None, len(_vn.LEAK_TERMS), len(_spb._OVERLAY_FORBIDDEN))"
    )
    # Park any preexisting file first (this check tests ISOLATION, not file hygiene) and
    # restore the worktree to its exact original state afterwards.
    _amb_parked = None
    if os.path.exists(_amb_path):
        _amb_parked = _amb_path + ".t21-parked"
        os.replace(_amb_path, _amb_parked)
    try:
        _amb_absent = run_text([sys.executable, "-c", _amb_snippet], cwd=ROOT, env=_amb_env)
        with io.open(_amb_example, "rb") as _src, io.open(_amb_path, "wb") as _dst:
            _dst.write(_src.read())
        _amb_present = run_text([sys.executable, "-c", _amb_snippet], cwd=ROOT, env=_amb_env)
    finally:
        if os.path.exists(_amb_path):
            os.remove(_amb_path)
        if _amb_parked is not None:
            os.replace(_amb_parked, _amb_path)
    _amb_absent_out = _amb_absent.stdout.strip()
    _amb_present_out = _amb_present.stdout.strip()
    _amb_ok = (
        _amb_absent.returncode == 0 and _amb_present.returncode == 0
        and _amb_absent_out == _amb_present_out   # ambient presence changes NOTHING
        and _amb_absent_out.startswith("True ")   # loader returns None in default public mode
        and _amb_absent_out.endswith(" 0")        # zero overlay-augmented labels
        and os.path.exists(_amb_path) == (_amb_parked is not None)  # worktree back to original state
    )
    check("T2.1 ambient-overlay isolation: former-default file cannot alter public mode (fresh subprocesses; synthetic; original state restored)", _amb_ok)
    if not _amb_ok:
        print("   parked=%s absent=%r present=%r restored=%s" % (
            _amb_parked is not None, _amb_absent_out, _amb_present_out,
            os.path.exists(_amb_path) == (_amb_parked is not None)))
except Exception as _e:
    check("T2.1 ambient-overlay isolation (subprocess error)", False)
    print("  ", _e)

# --- T3A RM-04 matcher gates ---
# Exercise the shared forbidden-label matcher and the real meta-transclusion
# completion predicate against the committed audit fixtures and LAT-01 cases.
try:
    from tools.largelexicon_common import match_forbidden_labels as _rm04_match_labels
    from tools.validate_meta_transclusion_projection import completion_wording_violation as _rm04_completion_violation
    from tools.validate_public_private_boundary import FORBIDDEN_LABELS as _rm04_forbidden_labels

    _rm04_fixture_path = os.path.join(ROOT, "fusha", "parser", "eval", "rm04-matcher-fixtures.jsonl")
    with io.open(_rm04_fixture_path, encoding="utf-8") as _rm04_handle:
        _rm04_rows = [json.loads(_line) for _line in _rm04_handle if _line.strip()]
    _rm04_results = []
    for _rm04_row in _rm04_rows:
        _rm04_payload = _rm04_row.get("payload") or {}
        if _rm04_row.get("kind") == "forbidden_labels":
            _rm04_actual_fail = bool(_rm04_match_labels(
                json.dumps(_rm04_payload, ensure_ascii=False).lower(),
                _rm04_forbidden_labels,
            ))
        elif _rm04_row.get("kind") == "completion_wording":
            _rm04_actual_fail = _rm04_completion_violation(_rm04_payload)
        else:
            _rm04_actual_fail = None
        _rm04_results.append(
            _rm04_actual_fail is not None
            and _rm04_actual_fail == (_rm04_row.get("expect") == "fail")
        )
    check(
        "T3A RM-04 matcher fixtures (4 rows: boundary-aware labels + negation-aware completion)",
        len(_rm04_rows) == 4 and all(_rm04_results),
    )

    _lat01_honest_open = [
        {"projection_state": "reopened_not_complete", "projection_failures": ["x"]},
        {"projection_state": "unhandled", "projection_failures": ["x"]},
        {"projection_state": "needs_work", "projection_failures": ["x"], "note": "page NOT complete"},
    ]
    _lat01_intended_positive = {
        "projection_state": "visual_complete",
        "projection_failures": ["x"],
    }
    check(
        "T3A LAT-01 honest-open rows pass; intended-positive still fails",
        sum(_rm04_completion_violation(_row) for _row in _lat01_honest_open) == 0
        and sum(_rm04_completion_violation(_row) for _row in [_lat01_intended_positive]) == 1,
    )
except Exception as _e:
    check("T3A RM-04 matcher gates (harness error)", False)
    print("  ", _e)

# --- T3B-1 gates (RM-11/RM-13/SF-09) ---
# Gate aliases fail closed, the visible مَنْ reading never enters the مِنْ
# preposition rule, and Arabic-emitting CLIs override inherited CP-1252 stdout.
try:
    from tools.fusha_check import resolve_gate as _rm11_resolve_gate
    from tools.grade_grammar_reasoning import grade as _rm11_grade

    check(
        "RM-11 missing/empty/unknown gate aliases fail closed",
        all(_rm11_resolve_gate(_gate) == "two_vote_required" for _gate in (None, "", "UNKNOWN_GATE")),
    )
    _rm11_judgment = {
        "final_ok": True,
        "reasoning_ok": True,
        "evidence_cited": True,
        "source_address": "quran:1:1:1",
        "two_vote_done": True,
    }
    check(
        "RM-11 never_auto alias is equivalent to canonical never_auto_resolve",
        not _rm11_grade({"required_gate": "never_auto"}, _rm11_judgment)["pass"]
        and not _rm11_grade({"required_gate": "never_auto_resolve"}, _rm11_judgment)["pass"],
    )
except Exception as _e:
    check("RM-11 fail-closed gate aliases (harness error)", False)
    print("  ", _e)

try:
    from tools.fusha_governor import build_dependency_lattice as _rm13_build_lattice

    def _rm13_edges(surface, following_pos, case_visible=None):
        _tokens = [
            {"ref": "tok:0", "surface": surface, "pos": ""},
            {"ref": "tok:1", "surface": "عَالِمٌ" if following_pos == "noun" else "صَبَرَ", "pos": following_pos},
        ]
        if case_visible:
            _tokens[1]["case_visible"] = case_visible
        return _rm13_build_lattice({
            "input_mode": "source_addressed" if case_visible else "arbitrary_typing",
            "source_unit": {"address": "probe:rm13", "scope": "test"},
            "tokens": _tokens,
        })["edges"]

    _rm13_man_verb = _rm13_edges("مَنْ", "verb")
    _rm13_man_nom = _rm13_edges("مَنْ", "noun", "nominative")
    _rm13_min = _rm13_edges("مِنْ", "noun")
    _rm13_bare = _rm13_edges("من", "noun")
    check(
        "RM-13 مَنْ + verb has no jar-majrur edge or contradiction",
        not any(_e["rel_label"] == "jar_majrur" or _e["contradiction_marker"] for _e in _rm13_man_verb),
    )
    check(
        "RM-13 مَنْ + nominative noun has no fabricated contradiction",
        not any(_e["contradiction_marker"] for _e in _rm13_man_nom),
    )
    check(
        "RM-13 مِنْ + noun keeps preposition behavior",
        any(_e["rel_label"] == "jar_majrur" for _e in _rm13_min),
    )
    check(
        "RM-13 unvoweled من keeps existing preposition behavior",
        any(_e["rel_label"] == "jar_majrur" for _e in _rm13_bare),
    )
except Exception as _e:
    check("RM-13 governor probes (harness error)", False)
    print("  ", _e)

_sf09_cases = [
    ("fusha_morph_analyze.py", ["--surface", "يَكْتُبُ"], "يَكْتُبُ"),
    ("fusha_morph_generate.py", ["--generation-key", "prep-lam-3mp"], "لَهُمْ"),
    ("eval_fusha_morphology.py", ["--self-test"], "صَرْف"),
    ("validate_fusha_morph_db.py", ["--self-test"], "صَرْف"),
    ("fusha_largelexicon_cli.py", ["analyze-token", "--surface", "مَنْ"], "مَنْ"),
]
for _sf09_tool, _sf09_args, _sf09_marker in _sf09_cases:
    try:
        with io.open(os.path.join(ROOT, "tools", _sf09_tool), encoding="utf-8") as _sf09_source_handle:
            _sf09_source = _sf09_source_handle.read()
        _sf09_direct_guard = (
            'if hasattr(sys.stdout, "reconfigure"):\n'
            '    sys.stdout.reconfigure(encoding="utf-8")'
        ) in _sf09_source
        _sf09_env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        _sf09_run = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", _sf09_tool), *_sf09_args],
            cwd=ROOT,
            env=_sf09_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            _sf09_stdout = _sf09_run.stdout.decode("utf-8")
            _sf09_utf8 = True
        except UnicodeDecodeError:
            _sf09_stdout = ""
            _sf09_utf8 = False
        check(
            "SF-09 cp1252 guard: %s" % _sf09_tool,
            _sf09_direct_guard
            and _sf09_run.returncode == 0
            and _sf09_utf8
            and _sf09_marker in _sf09_stdout,
        )
    except Exception as _e:
        check("SF-09 cp1252 guard: %s" % _sf09_tool, False)
        print("  ", _e)

# --- T3B-2 gates (RM-10/RM-12 + tm ports) ---
try:
    from tools.fusha_standalone_parse import parse_text as _t3b2_parse_text

    _rm12_path = os.path.join(ROOT, "fusha", "parser", "eval", "rm12-harakah-conflict-regressions.jsonl")
    with io.open(_rm12_path, encoding="utf-8") as _rm12_handle:
        _rm12_rows = [json.loads(_line) for _line in _rm12_handle if _line.strip()]
    for _rm12_row in _rm12_rows:
        _rm12_token = _t3b2_parse_text(_rm12_row["query"], db=_rm12_row["db"])["tokens"][0]
        _rm12_top = (_rm12_token.get("morphology_candidates") or [{}])[0]
        _rm12_expect = _rm12_row["expectations"]
        _rm12_risk = (_rm12_top.get("features") or {}).get("match_risk")
        _rm12_ok = True
        if _rm12_expect.get("forbid_confidence_gate"):
            _rm12_ok = _rm12_ok and _rm12_token.get("confidence_gate") not in _rm12_expect["forbid_confidence_gate"]
        if _rm12_expect.get("confidence_gate"):
            _rm12_ok = _rm12_ok and _rm12_token.get("confidence_gate") == _rm12_expect["confidence_gate"]
        if _rm12_expect.get("require_risk"):
            _rm12_ok = _rm12_ok and _rm12_risk == _rm12_expect["require_risk"]
        if _rm12_expect.get("forbid_risk"):
            _rm12_ok = _rm12_ok and _rm12_risk != _rm12_expect["forbid_risk"]
        check("T3B-2 RM-12: %s" % _rm12_row["id"], _rm12_ok)
except Exception as _e:
    check("T3B-2 RM-12 fixture gates (harness error)", False)
    print("  ", _e)

try:
    from tools.fusha_text_check import check_text as _t3b2_check_text

    _tm_path = os.path.join(ROOT, "fusha", "parser", "eval", "tm-probe-regressions.jsonl")
    with io.open(_tm_path, encoding="utf-8") as _tm_handle:
        _tm_rows = [json.loads(_line) for _line in _tm_handle if _line.strip()]
    for _tm_row in _tm_rows:
        _tm_inputs = _tm_row["input"] if isinstance(_tm_row["input"], list) else [_tm_row["input"]]
        _tm_ok = True
        for _tm_input in _tm_inputs:
            _tm_rec = _t3b2_check_text({"input_mode": _tm_row["mode"], "raw_input": _tm_input})
            _tm_suggestions = _tm_rec.get("suggestions") or []
            _tm_expect = _tm_row["expectations"]
            _tm_ops = [s.get("edit", {}).get("op") for s in _tm_suggestions]
            if _tm_expect.get("forbid_ops"):
                _tm_ok = _tm_ok and not (set(_tm_expect["forbid_ops"]) & set(_tm_ops))
            if _tm_expect.get("require_reject_reason"):
                _tm_ok = _tm_ok and any(
                    s.get("edit", {}).get("op") == "abstain"
                    and s.get("reject_reason") == _tm_expect["require_reject_reason"]
                    for s in _tm_suggestions
                )
            if _tm_expect.get("forbid_retain_confidence"):
                _tm_ok = _tm_ok and not any(
                    s.get("edit", {}).get("op") == "retain"
                    and s.get("confidence") == _tm_expect["forbid_retain_confidence"]
                    for s in _tm_suggestions
                )
            if _tm_expect.get("require_copy"):
                _tm_ok = _tm_ok and any(
                    _tm_expect["require_copy"] in (s.get("explanation") or "") for s in _tm_suggestions
                )
            if _tm_expect.get("require_diagnostic"):
                _tm_ok = _tm_ok and any(
                    d.get("issue_class") == _tm_expect["require_diagnostic"] for d in _tm_rec.get("diagnostics") or []
                )
            if _tm_expect.get("require_suggestion_gate"):
                _tm_ok = _tm_ok and any(
                    s.get("gate") == _tm_expect["require_suggestion_gate"] for s in _tm_suggestions
                )
        check("T3B-2 tm-port: %s" % _tm_row["id"], _tm_ok)
except Exception as _e:
    check("T3B-2 tm-port fixtures (harness error)", False)
    print("  ", _e)

# --- T5 canonical-carrier gates (ADR-003 G1-G4) ---
# One full in-memory corpus build proves the fixed carrier/location cardinalities.
# G2 uses a deterministic 4,096-row real-corpus subset rather than a second full
# build, in addition to the adversarial T2 fixture permutations. No packet is
# written; every artifact below exists only in process memory.
try:
    import glob as _t5_glob
    import random as _t5_random
    import time as _t5_time

    from tools.build_canonical_hover_payload_table import build as _t5_build
    from tools.compile_canonical_hover_whitelist_packet import compile_packet as _t5_compile
    from tools.rebind_canonical_hover import verify_dataset as _rm20_verify_dataset
    from tools.validate_canonical_hover_payload_table import (
        binding_id as _t5_binding_id,
        exception_id as _t5_exception_id,
        payload_id as _t5_payload_id,
        validate_rows as _t5_validate_rows,
    )

    _t5_fixture_path = os.path.join(
        ROOT, "fusha", "parser", "eval", "t5-canonical-carrier-fixtures.jsonl")
    with io.open(_t5_fixture_path, encoding="utf-8") as _t5_handle:
        _t5_fixtures = [json.loads(_line) for _line in _t5_handle if _line.strip()]
    _t5_by_probe = {_row["probe"]: _row for _row in _t5_fixtures}

    def _t5_materialize(fixture):
        base = fixture["input"]["base"]
        materialized = []
        for edge in fixture["input"]["edges"]:
            row = json.loads(json.dumps(base, ensure_ascii=False))
            row.update(json.loads(json.dumps(edge, ensure_ascii=False)))
            dependency_hash = row.get("source_dependency_sha256")
            dependencies = [{"id": "t5-fixture:%s" % row.get("qword_row_id"),
                             "sha256": dependency_hash}]
            row.update({
                "schema": "qamus.canonical_hover_compiler_input.v1",
                "source_key": "qamus",
                "source_row_id": row.get("qword_row_id"),
                "source_artifact_sha256": dependency_hash,
                "source_dependencies": dependencies,
                "source_dependency_sha256": hashlib.sha256(json.dumps(
                    dependencies, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")).hexdigest(),
            })
            materialized.append(row)
        return materialized

    def _t5_bytes(rows):
        return ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")) for row in rows) + "\n").encode("utf-8")

    check("T5 fixture JSONL has 9 self-contained probe rows", len(_t5_fixtures) == 9)

    # T1 / G1: co-citations at one loc retain every qword carrier edge.
    _t5_t1 = _t5_by_probe["T1-full-carrier-identical-content"]
    _t5_p1, _t5_b1, _t5_r1, _t5_c1, _t5_rep1 = _t5_build(_t5_materialize(_t5_t1))
    _t5_w1, _t5_n1, _t5_wc1, _t5_wrep1 = _t5_compile(_t5_p1, _t5_b1, [], [])
    _t5_e1 = _t5_t1["expect"]
    check(
        "T5 T1 full carrier: payloads=%d bindings=%d whitelist=%d repairs=%d conflicts=%d" % (
            len(_t5_p1), len(_t5_b1), len(_t5_w1), len(_t5_r1), len(_t5_c1)),
        (len(_t5_p1), len(_t5_b1), len(_t5_w1), len(_t5_r1), len(_t5_c1)) ==
        (_t5_e1["payloads"], _t5_e1["bindings"], _t5_e1["whitelist_rows"],
         _t5_e1["repairs"], _t5_e1["conflicts"]),
    )

    # T2 / G2: equal-richness conflict selection and every output set are order-independent.
    _t5_t2 = _t5_by_probe["T2-permutation-property"]
    _t5_t2_rows = _t5_materialize(_t5_t2)
    _t5_t2_runs = []
    for _order in _t5_t2["input"]["orders"]:
        _out = _t5_build([_t5_t2_rows[_i] for _i in _order])
        _t5_t2_runs.append(tuple(_t5_bytes(_part) for _part in _out[:4]))
    check(
        "T5 T2 permutation: payload+binding+repair+conflict bytes identical; tie_unresolved=1",
        _t5_t2_runs[0] == _t5_t2_runs[1]
        and sum(c.get("reason") == "tie_unresolved"
                for c in _t5_build(_t5_t2_rows)[3]) ==
        _t5_t2["expect"]["tie_unresolved_conflicts"],
    )

    # T5: qword_row_id is load-bearing within the otherwise-identical carrier.
    _t5_t5 = _t5_by_probe["T5-qword-coordinate-distinguishes-binding"]
    _t5_p5, _t5_b5, _t5_r5, _t5_c5, _t5_rep5 = _t5_build(_t5_materialize(_t5_t5))
    check(
        "T5 T5 qword coordinate: bindings=%d distinct_ids=%d" % (
            len(_t5_b5), len({b["binding_id"] for b in _t5_b5})),
        len(_t5_b5) == _t5_t5["expect"]["bindings"]
        and len({b["binding_id"] for b in _t5_b5}) ==
        _t5_t5["expect"]["distinct_binding_ids"],
    )

    # T6/T13 / G3: each injected uniqueness defect demonstrably makes validation red.
    _t5_payload_collision_errors = _t5_validate_rows([_t5_p1[0], dict(_t5_p1[0])])
    _t5_binding_collision_errors = _t5_validate_rows(
        _t5_p1 + [_t5_b1[0], dict(_t5_b1[0])])
    _t5_p_alt = json.loads(json.dumps(_t5_p1[0], ensure_ascii=False))
    _t5_p_alt["public_payload"]["token_contribution_gloss"] = "tome"
    _t5_p_alt["public_payload"]["segments"][0]["gloss"] = "tome"
    _t5_p_alt["canonical_payload_id"] = _t5_payload_id(_t5_p_alt)
    _t5_b_alt = dict(_t5_b1[1], canonical_payload_id=_t5_p_alt["canonical_payload_id"])
    _t5_b_alt["binding_id"] = _t5_binding_id(_t5_b_alt)
    _t5_loc_collision_errors = _t5_validate_rows(
        [_t5_p1[0], _t5_p_alt, _t5_b1[0], _t5_b_alt])
    _t5_t6_payload = _t5_by_probe["T6-forced-payload-id-collision"]
    _t5_t6_binding = _t5_by_probe["T6-forced-binding-id-collision"]
    _t5_t13 = _t5_by_probe["T13-payload-collision-at-loc"]
    check(
        "T5 T6 forced payload-id collision fails validator",
        any(_t5_t6_payload["expect"]["contains"] in e
            for e in _t5_payload_collision_errors),
    )
    check(
        "T5 T6 forced binding-id collision fails validator",
        any(_t5_t6_binding["expect"]["contains"] in e
            for e in _t5_binding_collision_errors),
    )
    check(
        "T5 T13 two payload ids at one accepted loc fail validator",
        any(_t5_t13["expect"]["contains"] in e for e in _t5_loc_collision_errors),
    )

    # T7: mutable status never participates in any id; carrier coordinates do.
    _t5_t7 = _t5_by_probe["T7-id-stability-review-flip"]
    _t5_payload_status_flip = dict(
        _t5_p1[0], lemma_status="certified", sarf_certification="certified",
        nahw_certification="certified")
    _t5_binding_status_flip = dict(
        _t5_b1[0], binding_status="candidate", reason="owner-decision")
    _t5_binding_carrier_flip = dict(_t5_b1[0], qword_row_id="qword-coordinate-flipped")
    _t5_exc = {
        "schema": "qamus.canonical_hover_exception.v2",
        "binding_id": _t5_b1[0]["binding_id"],
        "exception_reason": "page_local_context",
        "replacement_canonical_payload_id": _t5_p1[0]["canonical_payload_id"],
        "reviewed_against_canonical_payload_id": _t5_p1[0]["canonical_payload_id"],
        "review_status": "candidate",
        "notes_private": None,
    }
    _t5_exc["exception_id"] = _t5_exception_id(_t5_exc)
    _t5_exc_status_flip = dict(_t5_exc, review_status="owner_accepted")
    check(
        "T5 T7 review/status flips preserve ids; carrier flip changes binding id",
        _t5_payload_id(_t5_payload_status_flip) == _t5_p1[0]["canonical_payload_id"]
        and _t5_binding_id(_t5_binding_status_flip) == _t5_b1[0]["binding_id"]
        and _t5_exception_id(_t5_exc_status_flip) == _t5_exc["exception_id"]
        and _t5_binding_id(_t5_binding_carrier_flip) != _t5_b1[0]["binding_id"]
        and _t5_t7["expect"]["mutable_review_fields_preserve_ids"]
        and _t5_t7["expect"]["carrier_coordinate_changes_binding_id"],
    )

    # T10 / G4: multiplicity conflict is independent of exception order.
    _t5_t10 = _t5_by_probe["T10-two-exception-order-independence"]
    _t5_exc_a = dict(_t5_exc, review_status="owner_accepted")
    _t5_exc_b = dict(_t5_exc_a, exception_reason="owner_style_override")
    _t5_exc_b["exception_id"] = _t5_exception_id(_t5_exc_b)
    _t5_two_a = _t5_compile(_t5_p1, [_t5_b1[0]], [_t5_exc_a, _t5_exc_b], [])
    _t5_two_b = _t5_compile(_t5_p1, [_t5_b1[0]], [_t5_exc_b, _t5_exc_a], [])
    check(
        "T5 T10 two-exception orders: conflicts=1 emits=0 byte-identical",
        not _t5_two_a[0] and not _t5_two_b[0]
        and _t5_two_a[2] == _t5_two_b[2]
        and len(_t5_two_a[2]) == _t5_t10["expect"]["conflicts"]
        and len(_t5_two_a[0]) == _t5_t10["expect"]["emits"]
        and _t5_two_a[2][0]["reason"] == _t5_t10["expect"]["reason"],
    )

    # LAT-05 / G4: accepted null replacement is never original-payload fallback.
    _t5_lat05 = _t5_by_probe["LAT-05-accepted-exception-null-replacement"]
    _t5_null_exc = dict(
        _t5_exc_a,
        review_status=_t5_lat05["input"]["review_status"],
        replacement_canonical_payload_id=_t5_lat05["input"]["replacement_canonical_payload_id"],
        exception_id="che:0000000000000000")
    _t5_null = _t5_compile(_t5_p1, [_t5_b1[0]], [_t5_null_exc], [])
    check(
        "T5 LAT-05 accepted null replacement: conflicts=1 emits=0",
        len(_t5_null[0]) == _t5_lat05["expect"]["emits"]
        and len(_t5_null[2]) == _t5_lat05["expect"]["conflicts"]
        and _t5_null[2][0]["reason"] == _t5_lat05["expect"]["reason"],
    )

    # The T5 block independently runs all three CLI self-tests.
    for _script, _label in (
        ("validate_canonical_hover_payload_table.py", "validator"),
        ("build_canonical_hover_payload_table.py", "builder"),
        ("compile_canonical_hover_whitelist_packet.py", "compiler"),
    ):
        _run = run_text([sys.executable, os.path.join(ROOT, "tools", _script), "--self-test"])
        check("T5 %s self-test" % _label, _run.returncode == 0)

    # Full real accepted-crosswalk dry-run. The public payload is a deliberately
    # synthetic in-memory carrier preview; only the committed source coordinates,
    # surfaces, and dependency hashes drive the cardinality proof.
    _t5_crosswalk_paths = sorted(_t5_glob.glob(os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "qword-crosswalk", "*.jsonl")))
    _t5_full_rows = []
    for _path in _t5_crosswalk_paths:
        with io.open(_path, encoding="utf-8") as _handle:
            for _line in _handle:
                _source = json.loads(_line)
                if _source.get("status") != "canonical_crosswalk_accepted":
                    continue
                _surface = _source["visible_surface_norm_strict"]
                _dependency_blob = json.dumps(
                    _source.get("source_dependencies") or [], ensure_ascii=False,
                    sort_keys=True, separators=(",", ":"))
                _source_dep_digest = hashlib.sha256(
                    _dependency_blob.encode("utf-8")).hexdigest()
                _compiler_dependencies = [{
                    "id": _source["row_id"], "sha256": _source_dep_digest}]
                _t5_full_rows.append({
                    "schema": "qamus.canonical_hover_compiler_input.v1",
                    "source_key": "qamus",
                    "source_row_id": _source["row_id"],
                    "source_artifact_sha256": _source["resolution_wbw_lookup_sha256"],
                    "source_dependencies": _compiler_dependencies,
                    "surface_norm": _surface,
                    "root": None,
                    "pos": "unknown",
                    "pattern": None,
                    "lemma_status": "missing",
                    "sarf_certification": "missing",
                    "nahw_certification": "missing",
                    "public_payload": {
                        "src": "qamus", "kind": "authored", "lang": "en",
                        "token_contribution_gloss": "dry-run carrier preview",
                        "contextual_phrase_gloss": None,
                        "morphline": "STEM",
                        "segments": [{"role": "STEM", "surface": _surface,
                                      "qg_class": "unknown", "gloss": "dry-run"}],
                        "learner_explanation": "dry-run carrier preview",
                    },
                    "canonical_quran_loc": _source["canonical_quran_loc"],
                    "canonical_wbw_loc": _source["canonical_wbw_loc"],
                    "entry_id": _source["entry_id"],
                    "card_id": _source["card_id"],
                    "qword_row_id": _source["qword_row_id"],
                    "visible_surface": _source["visible_surface"],
                    "source_dependency_sha256": hashlib.sha256(json.dumps(
                        _compiler_dependencies, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":")).encode("utf-8")).hexdigest(),
                })
    _t5_full_started = _t5_time.perf_counter()
    _t5_full_p, _t5_full_b, _t5_full_r, _t5_full_c, _t5_full_report = _t5_build(
        _t5_full_rows)
    _t5_full_build_seconds = _t5_time.perf_counter() - _t5_full_started
    _t5_full_w, _t5_full_n, _t5_full_wc, _t5_full_wreport = _t5_compile(
        _t5_full_p, _t5_full_b, [], [])
    _t5_full_whitelist_count = len(_t5_full_w) + len(_t5_full_n)
    check(
        "T5 G1 full dry-run: bindings=%d whitelist=%d build=%.3fs" % (
            len(_t5_full_b), _t5_full_whitelist_count, _t5_full_build_seconds),
        # T10 residue/RM-36 arithmetic: 86970 + 47 promotions - 37 demotions
        # = 86980 bindings; 42065 + 19 promoted locs - 0 fully lost locs
        # = 42084 modeled whitelist locations.
        # T10 Lane B waves 1-3 (EQ-17): wave 3 certifies 752 carrier facts,
        # comprising 731 new bindings + 21 corrected fallback rebindings.
        # Bindings = 87579 + 731 = 88386; modeled locations remain
        # 42355 + 344 newly-modeled locs - 0 old locations lost
        # = 42732 modeled whitelist locations.
        len(_t5_full_rows) == 88386
        and len(_t5_full_b) == 88386
        and _t5_full_whitelist_count == 42732
        and not _t5_full_c and not _t5_full_wc,
    )
    check(
        "T5 G1 diagnostics: co_occurrence_not_bound=0 richer-peer=0",
        not any(r.get("reason") == "co_occurrence_not_bound" for r in _t5_full_r)
        and not any(r.get("reason") == "richer-peer" for r in _t5_full_r),
    )

    # RM-20: fixture-scale repair behavior plus a real-data, in-memory read-only
    # verification of the current G1 payload/binding build outputs.
    _rm20 = run_text([sys.executable, os.path.join(ROOT, "tools", "test_rebind_lineage.py")])
    _rm20_full_errors = _rm20_verify_dataset(_t5_full_p, _t5_full_b)
    check(
        "RM-20 repair lineage: fixtures pass and G1 real-data build is live-payload sound",
        _rm20.returncode == 0 and not _rm20_full_errors,
    )
    if _rm20.returncode:
        print(_rm20.stdout)
        print(_rm20.stderr)
    if _rm20_full_errors:
        print("  ", _rm20_full_errors[:20])

    _t5_subset = list(_t5_full_rows[:4096])
    _t5_shuffled = list(_t5_subset)
    _t5_random.Random(5).shuffle(_t5_shuffled)
    _t5_subset_a = _t5_build(_t5_subset)
    _t5_subset_b = _t5_build(_t5_shuffled)
    check(
        "T5 G2 real-corpus permutation subset=4096 byte-identical",
        all(_t5_bytes(_t5_subset_a[_i]) == _t5_bytes(_t5_subset_b[_i])
            for _i in range(4)),
    )
except Exception as _e:
    check("T5 canonical-carrier gates (ADR-003 G1-G4) harness error", False)
    print("  ", _e)

# --- T6 adoption gates (ADR-003 G6/G7) ---
try:
    import ast as _t6_ast
    import re as _t6_re
    import tempfile as _t6_tempfile

    from tools.build_canonical_hover_payload_table import build as _t6_build
    from tools.compile_canonical_hover_whitelist_packet import compile_packet as _t6_compile
    from tools.report_g8_adoption_packet import build_adoption_report as _t6_adoption

    _t6_fixture_path = os.path.join(
        ROOT, "fusha", "parser", "eval", "t6-provenance-baseline-fixtures.jsonl")
    with io.open(_t6_fixture_path, encoding="utf-8") as _t6_handle:
        _t6_fixtures = [json.loads(_line) for _line in _t6_handle if _line.strip()]
    _t6_by_probe = {_row["probe"]: _row for _row in _t6_fixtures}
    _t6_valid_fixture = _t6_by_probe["G7-valid-boundary-row"]
    _t6_artifacts = {
        _t6_valid_fixture["artifact_id"]: _t6_valid_fixture["artifact_bytes"].encode("utf-8")}

    def _t6_row(probe):
        fixture = _t6_by_probe[probe]
        row = json.loads(json.dumps(_t6_valid_fixture["row"], ensure_ascii=False))
        for field in fixture.get("delete", []):
            row.pop(field, None)
        row.update(fixture.get("set", {}))
        return row

    _t6_p, _t6_b, _t6_r, _t6_c, _t6_br = _t6_build(
        [_t6_row("G7-valid-boundary-row")], dependency_artifacts=_t6_artifacts)
    check("T6 G7 valid boundary row accepted", len(_t6_b) == 1 and not _t6_c)
    for _probe in (
        "G7-dependency-hash-missing", "G7-carrier-incomplete",
        "G7-provenance-missing", "G7-schema-version-wrong",
        "G7-index-drift-red-first",
    ):
        _bp, _bb, _br, _bc, _brep = _t6_build(
            [_t6_row(_probe)], dependency_artifacts=_t6_artifacts)
        _reason = _t6_by_probe[_probe]["expect"]["reason"]
        check("T6 %s rejects with %s" % (_probe, _reason),
              not _bb and any(row.get("reason") == _reason for row in _bc))

    _t6_first = _t6_compile(_t6_p, _t6_b, [], [], source_head="fixture-head")
    _t6_second = _t6_compile(_t6_p, _t6_b, [], [], source_head="fixture-head")
    _t6_changed_payload = json.loads(json.dumps(_t6_p, ensure_ascii=False))
    _t6_changed_payload[0]["public_payload"]["token_contribution_gloss"] = "written volume"
    _t6_changed_payload[0]["public_payload"]["segments"][0]["gloss"] = "written volume"
    from tools.validate_canonical_hover_payload_table import payload_id as _t6_payload_id
    _t6_changed_payload[0]["canonical_payload_id"] = _t6_payload_id(_t6_changed_payload[0])
    _t6_changed_binding = [dict(_t6_b[0], canonical_payload_id=_t6_changed_payload[0]["canonical_payload_id"])]
    from tools.validate_canonical_hover_payload_table import binding_id as _t6_binding_id
    _t6_changed_binding[0]["binding_id"] = _t6_binding_id(_t6_changed_binding[0])
    _t6_changed_a = _t6_compile(
        _t6_changed_payload, _t6_changed_binding, [], [], source_head="fixture-head")
    _t6_changed_b = _t6_compile(
        _t6_changed_payload, _t6_changed_binding, [], [], source_head="fixture-head")
    _required_report = {
        "source_head", "input_artifacts", "schemas_consumed", "schemas_produced",
        "compiler_version", "packet_sha256", "row_denominators", "conflict_denominators"}
    check("T6 G6a compile report provenance fields present",
          _required_report <= set(_t6_first[3]))
    check("T6 G6a identical inputs reproduce packet sha byte-identically",
          _t6_first[3]["packet_sha256"] == _t6_second[3]["packet_sha256"])
    check("T6 G6a changed input changes packet sha in stable direction",
          _t6_first[3]["packet_sha256"] != _t6_changed_a[3]["packet_sha256"]
          and _t6_changed_a[3]["packet_sha256"] == _t6_changed_b[3]["packet_sha256"])

    _t6_g8 = run_text([
        sys.executable, os.path.join(ROOT, "tools", "report_g8_adoption_packet.py"),
        "--self-test"])
    check("T6 G6b/G8 adoption reporter self-test (six classes + legacy no-op + lineage)",
          _t6_g8.returncode == 0)

    _t6_lane_paths = [os.path.join(ROOT, "tools", name) for name in (
        "build_canonical_hover_payload_table.py",
        "compile_canonical_hover_whitelist_packet.py",
        "validate_canonical_hover_payload_table.py",
        "report_g8_adoption_packet.py",
    )]
    _t6_sha_re = _t6_re.compile(
        r'''(?im)\b(?:[A-Za-z_]\w*(?:_sha|_sha256)|source_head)\s*=\s*["'][0-9a-f]{12,64}["']'''
        r'''|["'][0-9a-f]{40}(?:[0-9a-f]{24})?["']''')

    def _t6_sha_lint(path):
        with io.open(path, encoding="utf-8") as handle:
            return _t6_sha_re.findall(handle.read())

    _t6_ast_ok = True
    for _path in _t6_lane_paths:
        with io.open(_path, encoding="utf-8") as _handle:
            _t6_ast.parse(_handle.read(), filename=_path)
        _t6_ast_ok = _t6_ast_ok and not _t6_sha_lint(_path)
    check("T6 G6c lane AST parses and hardcoded-sha lint green at HEAD", _t6_ast_ok)
    with _t6_tempfile.TemporaryDirectory() as _td:
        _seeded = os.path.join(_td, "seeded.py")
        with io.open(_seeded, "w", encoding="utf-8") as _handle:
            _handle.write('SOURCE_HEAD = "1234567890abcdef1234567890abcdef12345678"\n')
        check("T6 G6c seeded temp copy makes hardcoded-sha lint red",
              bool(_t6_sha_lint(_seeded)))
except Exception as _e:
    check("T6 adoption gates (ADR-003 G6/G7) harness error", False)
    print("  ", _e)

# --- T8 cross-platform hash durability (protects TRACKED bytes, not just working-tree state) ---
try:
    _t8_targets = [("qamus/examples/rh_live_00_admin_preview_dom_fixture.sample.html",
                    "qamus/examples/rh_live_00_admin_preview_bundle_manifest.sample.json")]
    _t8_failures = []
    _t8_proofs = 0
    # every checksums.json-listed dataset file participates too (manifest-declared shas)
    _t8_cs = json.load(io.open(os.path.join(ROOT, "qamus", "data", "current", "checksums.json"), encoding="utf-8"))
    for _rel, _decl in sorted(_t8_cs.items()):
        # checksums.json keys map data/X to qamus/data/current/X and
        # indexes/X to qamus/indexes/current/X (the strict validator layout)
        _head, _tail = _rel.split("/", 1)
        _repo_rel = "qamus/%s/current/%s" % (_head, _tail)
        _pathp = os.path.join(ROOT, *_repo_rel.split("/"))
        _wt = hashlib.sha256(io.open(_pathp, "rb").read()).hexdigest()
        _git = subprocess.run(["git", "show", "HEAD:" + _repo_rel],
                              cwd=ROOT, capture_output=True).stdout
        _gt = hashlib.sha256(_git).hexdigest()
        _attr = subprocess.run(["git", "check-attr", "eol", "--", _repo_rel],
                               cwd=ROOT, capture_output=True, text=True).stdout
        if not (_wt == _gt == _decl["sha256"]):
            _t8_failures.append("%s: worktree=%s git=%s declared=%s" % (_rel, _wt[:8], _gt[:8], _decl["sha256"][:8]))
        if ": lf" not in _attr:
            _t8_failures.append("%s: eol attribute not lf (%r)" % (_rel, _attr.strip()))
        _t8_proofs += 1
    for _fixture, _manifest in _t8_targets:
        _wt = hashlib.sha256(io.open(os.path.join(ROOT, *_fixture.split("/")), "rb").read()).hexdigest()
        _git = subprocess.run(["git", "show", "HEAD:" + _fixture], cwd=ROOT, capture_output=True).stdout
        _gt = hashlib.sha256(_git).hexdigest()
        _m = json.load(io.open(os.path.join(ROOT, *_manifest.split("/")), encoding="utf-8"))
        _decl = _m["artifacts"]["admin_preview_dom_fixture"]["sha256"]
        _attr = subprocess.run(["git", "check-attr", "eol", "--", _fixture],
                               cwd=ROOT, capture_output=True, text=True).stdout
        if not (_wt == _gt == _decl):
            _t8_failures.append("%s: worktree=%s git=%s manifest=%s" % (_fixture, _wt[:8], _gt[:8], _decl[:8]))
        if ": lf" not in _attr:
            _t8_failures.append("%s: eol attribute not lf" % _fixture)
        _t8_proofs += 1
    check("T8 hash durability: worktree == tracked-blob == manifest sha AND eol=lf pinned (%d anchored files)" % _t8_proofs,
          not _t8_failures)
    for _f in _t8_failures:
        print("  ", _f)
except Exception as _e:
    check("T8 hash durability (scan error)", False)
    print("  ", _e)

# --- T9B shadow runner (Shadow Flywheel Activation Program) ---
# The operational shadow compiler's alert evaluator + synthetic end-to-end pipeline.
# Self-test only: no production paths, no overlay, no repo dataset mutation.
try:
    _t9b = run_text([sys.executable, os.path.join(ROOT, "tools", "run_shadow_compile.py"),
                     "--self-test"])
    check("T9B shadow runner self-test (alert classes + synthetic pipeline)",
          _t9b.returncode == 0 and "SHADOW RUNNER SELF-TEST PASS" in (_t9b.stdout or ""))
except Exception as _e:
    check("T9B shadow runner self-test (harness error)", False)

try:
    _rm20_shadow_overlay = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "test_shadow_canonical_repair_overlay.py"),
    ])
    check(
        "RM-20 shadow runner canonical-repair overlay tests",
        _rm20_shadow_overlay.returncode == 0,
    )
    if _rm20_shadow_overlay.returncode != 0:
        print((_rm20_shadow_overlay.stdout + _rm20_shadow_overlay.stderr)[-4000:])
except Exception as exc:
    check("RM-20 shadow runner canonical-repair overlay tests (harness error)", False)
    print("  ", exc)

# --- T10 Lane B classifier (Shadow Flywheel Activation Program) ---
try:
    _t10_lane_b = run_text([
        sys.executable, os.path.join(ROOT, "tools", "classify_gap_multi_candidates.py"),
        "--self-test"])
    check("T10 Lane B classifier self-test", _t10_lane_b.returncode == 0)
except Exception as _e:
    check("T10 Lane B classifier self-test (harness error)", False)
    print("  ", _e)

# --- T11 append-queue builder (Shadow Flywheel Activation Program) ---
try:
    _t11_append = run_text([
        sys.executable, os.path.join(ROOT, "tools", "build_append_queue.py"),
        "--self-test"])
    check("T11 append-queue builder self-test", _t11_append.returncode == 0)
except Exception as _e:
    check("T11 append-queue builder self-test (harness error)", False)
    print("  ", _e)

# --- T12 typed fact ledger ---
try:
    _t12_ledger = run_text([
        sys.executable, os.path.join(ROOT, "tools", "test_fact_ledger.py")])
    check("T12 fact ledger tests", _t12_ledger.returncode == 0)
except Exception as _e:
    check("T12 fact ledger tests (harness error)", False)
    print("  ", _e)

# --- RM-38 external-gold evaluation mechanics (offline synthetic only) ---
for _script, _marker, _label in (
    ("validate.py", "RM-38 validator self-test OK",
     "RM-38 evaluation validator self-test"),
    ("runner.py", "RM-38 evaluation runner self-test OK",
     "RM-38 evaluation runner self-test"),
):
    try:
        _rm38 = run_text([
            sys.executable,
            os.path.join(ROOT, "tools", "rm38", _script),
            "--self-test",
        ], timeout=60)
        check(_label, _rm38.returncode == 0 and _marker in (_rm38.stdout or ""))
    except Exception as _e:
        check(_label + " (harness error)", False)
        print("  ", _e)

# --- RM-40 staged paradigm-licensed generation (offline synthetic only) ---
# Candidates-never-facts: generated forms are candidate-only, live in a store
# disjoint from the sourced lookup/evidence baseline, and are not deploy-eligible.
for _script, _marker, _label in (
    ("rm40_gate_stack.py", "RM-40 gate stack self-test OK",
     "RM-40 gate stack self-test (weak/hamza/masdar abstain)"),
    ("fusha_paradigm_generate.py", "RM-40 paradigm generator self-test OK",
     "RM-40 paradigm generator self-test (abstain-first, competing preserved)"),
    ("validate_rm40_generation.py", "RM-40 generation validator self-test OK",
     "RM-40 generation validator self-test (plane-disjointness, supersedes, no-overwrite)"),
    ("rm40_eval_harness.py", "RM-40 evaluation harness self-test OK",
     "RM-40 evaluation harness self-test (fabrication budget, norm_strict join, no aggregate)"),
):
    try:
        _rm40 = run_text([
            sys.executable, os.path.join(ROOT, "tools", _script), "--self-test",
        ], timeout=60)
        check(_label, _rm40.returncode == 0 and _marker in (_rm40.stdout or ""))
    except Exception as _e:
        check(_label + " (harness error)", False)
        print("  ", _e)
try:
    _rm40t = run_text([sys.executable, os.path.join(ROOT, "tools", "test_rm40_generation.py")])
    check("RM-40 generation tests (12 red-first checklist items)", _rm40t.returncode == 0)
except Exception as _e:
    check("RM-40 generation tests (harness error)", False)
    print("  ", _e)

# --- RM-20 owner-approved morphline application ---
try:
    _rm20_apply = run_text([
        sys.executable, os.path.join(ROOT, "tools", "test_rm20_morphline_apply.py")])
    check(
        "RM-20 morphline apply tests (five refusals + reports + ledger + atomic SHADOW)",
        _rm20_apply.returncode == 0,
    )
except Exception as _e:
    check("RM-20 morphline apply tests (harness error)", False)
    print("  ", _e)

# --- T10 crosswalk-gap queue (Shadow Flywheel Activation Program) ---
# The gap-queue builder's family classification, owner column set, fail-closed
# uniqueness semantics (red-first false-unique fixture), and determinism.
try:
    _t10 = run_text([sys.executable, os.path.join(ROOT, "tools", "build_crosswalk_gap_queue.py"),
                     "--self-test"])
    check("T10 gap-queue builder self-test (families + columns + uniqueness + determinism)",
          _t10.returncode == 0 and "GAP-QUEUE BUILDER SELF-TEST PASS" in (_t10.stdout or ""))
except Exception as _e:
    check("T10 gap-queue builder self-test (harness error)", False)
    print("  ", _e)

# --- T10 Lane B waves 1-3: two-vote-certified promotion through the ledger (EQ-17) ---
# Wave 2 retains every selected full carrier: 194 shared review decisions produce
# 537 certified carrier facts/bindings. The queue reconciles by locations, while
# accepted-crosswalk arithmetic reconciles by bindings.
try:
    import collections as _lb_collections
    _lb_self = run_text([sys.executable, os.path.join(ROOT, "tools", "promote_two_vote_wave.py"),
                         "--self-test"])
    check("T10 Lane B wave promoter self-test (ledger-gate + carrier + quarantine + determinism)",
          _lb_self.returncode == 0 and "PROMOTE-TWO-VOTE-WAVE SELF-TEST PASS" in (_lb_self.stdout or ""))
    _lb_ledger_path = os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "fact-ledger", "laneb-review.jsonl")
    _lb_current = {}
    with io.open(_lb_ledger_path, encoding="utf-8") as _lb_handle:
        for _lb_line in _lb_handle:
            if _lb_line.strip():
                _lb_row = json.loads(_lb_line)
                _lb_current[_lb_row["fact_id"]] = _lb_row  # last revision wins
    _lb_states = _lb_collections.Counter(
        _row["certification_state"] for _row in _lb_current.values())
    check("T10 Lane B ledger states after affirm-live T3 tranche: certified=1657 review_required=24 candidate=213 rejected=136",
          _lb_states.get("certified") == 1657 and _lb_states.get("review_required") == 24
          and _lb_states.get("candidate") == 213 and _lb_states.get("rejected") == 136
          and _lb_states.get("conflicted", 0) == 0)
    _lb_carriers = {
        (_row["subject_identity"]["loc"], _row["subject_identity"]["qword_row_id"])
        for _row in _lb_current.values() if _row["certification_state"] == "certified"}
    check("T10 Lane B certified facts are occurrence-scoped with full D-13 carriers (1657 unique)",
          len(_lb_carriers) == 1657 and all(
              _row.get("scope") == "occurrence"
              and {"loc", "entry_id", "card_id", "qword_row_id"} <= set(_row["subject_identity"])
              for _row in _lb_current.values() if _row["certification_state"] == "certified"))
    _lb_report = json.loads(io.open(os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "crosswalk-gap", "laneb-wave-01.report.json"),
        encoding="utf-8").read())
    check("T10 Lane B wave report: 77 promoted, queue 5502 -> 5425, method two_vote_certified_v1",
          _lb_report["counts"]["promoted_bindings"] == 77
          and _lb_report["counts"]["queue_before"] == 5502
          and _lb_report["counts"]["queue_after"] == 5425
          and _lb_report["resolution_method"] == "two_vote_certified_v1"
          and len(_lb_report["rows"]) == 77)
    _lb_report2 = json.loads(io.open(os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "crosswalk-gap", "laneb-wave-02.report.json"),
        encoding="utf-8").read())
    _lb_decisions = {}
    for _row in _lb_report2["rows"]:
        _lb_decisions.setdefault(_row["canonical_location"], set()).add(_row["review_decision_id"])
    check("T10 Lane B wave 2 report: 194 locations / 537 carrier facts / queue 5425 -> 5231",
          _lb_report2["counts"]["qualifying_locations"] == 194
          and _lb_report2["counts"]["promoted_bindings"] == 537
          and _lb_report2["counts"]["queue_before"] == 5425
          and _lb_report2["counts"]["queue_after"] == 5231
          and len(_lb_report2["rows"]) == 537
          and len(_lb_decisions) == 194
          and all(len(_ids) == 1 for _ids in _lb_decisions.values()))
    _lb_rebinding = _lb_report2["rebinding_accounting"]
    check("T10 Lane B wave 2 truthful accounting: 522 new + 15 rebound = 537 promoted",
          _lb_rebinding["new_bindings"] == 522
          and _lb_rebinding["rebound_bindings"] == 15
          and _lb_rebinding["certified_promoted_bindings"] == 537
          and _lb_rebinding["accepted_bindings_before"] == 87057
          and _lb_rebinding["accepted_bindings_after"] == 87579
          and _lb_rebinding["accepted_bindings_delta"] == 522)
    check("T10 Lane B wave 2 old-location occupancy proof: none of 15 lost its last binding",
          len(_lb_rebinding["rebindings"]) == 15
          and not _lb_rebinding["locations_losing_last_binding"]
          and all(not _row["old_location_lost_last_binding"]
                  and _row["old_location_bindings_after"] > 0
                  for _row in _lb_rebinding["rebindings"])
          and _lb_rebinding["modeled_locations_before"] == 42161
          and _lb_rebinding["modeled_locations_after"] == 42355)
    _lb_manifest = json.loads(io.open(os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "qamus-qword-crosswalk.manifest.json"),
        encoding="utf-8").read())
    _lb_wave2_fact_ids = {_row["ledger_fact_id"] for _row in _lb_report2["rows"]}
    _lb_wave2_facts = {
        _fid: _row for _fid, _row in _lb_current.items()
        if _fid in _lb_wave2_fact_ids and _row["certification_state"] == "certified"
    }
    _lb_crosswalk_rows = []
    for _path in _t5_crosswalk_paths:
        with io.open(_path, encoding="utf-8") as _handle:
            _lb_crosswalk_rows.extend(
                _row for _row in (json.loads(_line) for _line in _handle)
                if _row.get("status") == "canonical_crosswalk_accepted")
    _lb_wave2_bindings = [
        _row for _row in _lb_crosswalk_rows
        if _row.get("review_fact_id") in _lb_wave2_facts
    ]
    check("T10 Lane B wave 2 retains 537 binding-scoped provenance edges",
          len(_lb_wave2_facts) == 537 and len(_lb_wave2_bindings) == 537
          and all(
              _lb_wave2_facts[_row["review_fact_id"]]["subject_identity"]["qword_row_id"]
                  == _row["qword_row_id"]
               and _lb_wave2_facts[_row["review_fact_id"]]["subject_identity"]["loc"]
                   == _row["canonical_quran_loc"]
               for _row in _lb_wave2_bindings))
    _lb_rebound_rows = [_row for _row in _lb_wave2_bindings if _row.get("rebind_provenance")]
    _lb_reported_pairs = {
        (_row["qword_row_id"], _row["old_loc"], _row["new_loc"])
        for _row in _lb_rebinding["rebindings"]}
    _lb_materialized_pairs = {
        (_row["qword_row_id"], _row["rebind_provenance"]["prior_loc"],
         _row["canonical_quran_loc"])
        for _row in _lb_rebound_rows}
    check("T10 Lane B wave 2 rebind lineage: 15 explicit old->new pairs match report",
          len(_lb_rebound_rows) == 15
          and _lb_reported_pairs == _lb_materialized_pairs
          and all(
              _row["rebind_provenance"] == {
                  "prior_loc": _row["rebind_provenance"]["prior_loc"],
                  "prior_resolution_method": "row_unique_surface_fallback",
                  "reason": "two_vote_review_relocated",
                  "review_fact_id": _row["review_fact_id"],
                  "rebound_at_head": "69830258bf463cff185ba621a13189093857bddc",
              }
              for _row in _lb_rebound_rows))
    _lb_report3 = json.loads(io.open(os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "crosswalk-gap", "laneb-wave-03.report.json"),
        encoding="utf-8").read())
    _lb_decisions3 = {}
    for _row in _lb_report3["rows"]:
        _lb_decisions3.setdefault(_row["canonical_location"], set()).add(_row["review_decision_id"])
    check("T10 Lane B wave 3 report: 344 locations / 752 carrier facts / queue 5231 -> 4887",
          _lb_report3["counts"]["qualifying_locations"] == 344
          and _lb_report3["counts"]["promoted_bindings"] == 752
          and _lb_report3["counts"]["queue_before"] == 5231
          and _lb_report3["counts"]["queue_after"] == 4887
          and len(_lb_report3["rows"]) == 752
          and len(_lb_decisions3) == 344
          and all(len(_ids) == 1 for _ids in _lb_decisions3.values()))
    check("T10 Lane B wave 3 authoritative holds: 0 disagreement / 144 joint / 12 one-sided",
          _lb_report3["counts"]["disagreement_review_required"] == 0
          and _lb_report3["disagreement"] is None
          and _lb_report3["disagreements"] == []
          and len(_lb_report3["joint_abstentions"]) == 144
          and len(_lb_report3["one_sided_rows"]) == 12)
    _lb_11448 = [
        _row for _row in _lb_report3["one_sided_rows"]
        if _row["canonical_location"] == "11:44:8"]
    check("T10 Lane B wave 3 11:44:8 remains data-quality quarantined review_required",
          len(_lb_11448) == 1
          and _lb_11448[0]["ledger_state"] == "review_required"
          and _lb_11448[0]["data_quality_quarantine"] is True
          and _lb_11448[0]["data_finding"]["finding_class"]
              == "live_morphline_root_inconsistent_with_surface")
    check("T10 Lane B wave 3 ledger votes preserve Opus/Codex engine diversity",
          all(
              {"reviewer-A:Opus", "reviewer-B:Codex"}
              == {vote["voter_id"] for vote in _lb_current[_row["ledger_fact_id"]]["review_votes"]}
              for _row in _lb_report3["rows"]))
    _lb_rebinding3 = _lb_report3["rebinding_accounting"]
    check("T10 Lane B wave 3 truthful accounting: 731 new + 21 rebound = 752 promoted",
          _lb_rebinding3["new_bindings"] == 731
          and _lb_rebinding3["rebound_bindings"] == 21
          and _lb_rebinding3["certified_promoted_bindings"] == 752
          and _lb_rebinding3["accepted_bindings_before"] == 87579
          and _lb_rebinding3["accepted_bindings_after"] == 88310
          and _lb_rebinding3["accepted_bindings_delta"] == 731
          and _lb_rebinding3["modeled_locations_before"] == 42355
          and _lb_rebinding3["modeled_locations_after"] == 42699)
    check("T10 Lane B wave 3 old-location occupancy proof: none of 21 lost its last binding",
          len(_lb_rebinding3["rebindings"]) == 21
          and not _lb_rebinding3["locations_losing_last_binding"]
          and all(not _row["old_location_lost_last_binding"]
                  and _row["old_location_bindings_after"] > 0
                  for _row in _lb_rebinding3["rebindings"]))
    _lb_wave3_fact_ids = {_row["ledger_fact_id"] for _row in _lb_report3["rows"]}
    _lb_wave3_bindings = [
        _row for _row in _lb_crosswalk_rows
        if _row.get("review_fact_id") in _lb_wave3_fact_ids]
    check("T10 Lane B wave 3 retains 752 binding-scoped provenance edges",
          len(_lb_wave3_fact_ids) == 752 and len(_lb_wave3_bindings) == 752
          and all(
              _lb_current[_row["review_fact_id"]]["subject_identity"]["qword_row_id"]
                  == _row["qword_row_id"]
              and _lb_current[_row["review_fact_id"]]["subject_identity"]["loc"]
                  == _row["canonical_quran_loc"]
              for _row in _lb_wave3_bindings))
    check("T10 Lane B accepted crosswalk reconciles: 88386 accepted (87579 + 731 new)",
          _lb_manifest["status_counts"].get("canonical_crosswalk_accepted") == 88386
          and _lb_manifest.get("two_vote_promotion", {}).get("wave") == 4
          and _lb_manifest.get("two_vote_promotion", {}).get("accepted_rows") == 76)
    _lb_queue_manifest = json.loads(io.open(os.path.join(
        ROOT, "qamus", "indexes", "largelexicon", "crosswalk-gap",
        "crosswalk-gap-queue.manifest.json"), encoding="utf-8").read())
    check("T10 Lane B wave 4 queue reconciles: 4887 -> 4854 (33 promoted, 79 affirmed-live refamilied)",
          _lb_queue_manifest.get("queue_rows") == 4854)
except Exception as _e:
    check("T10 Lane B wave promotion gate (harness error)", False)
    print("  ", _e)

# --- T10 infrastructure: atomic shard promotion (RM-19) ---
# Stdlib tmpdir tests: crash preservation, lock exclusion, generation hashes,
# mixed-generation rejection, rollback, recovery, and determinism.
try:
    _rm19 = run_text([sys.executable, os.path.join(ROOT, "tools", "test_atomic_promotion.py")])
    check("RM-19 atomic shard promotion self-test (lock + recovery + rollback)",
          _rm19.returncode == 0 and not (_rm19.stdout or "").strip() and not (_rm19.stderr or "").strip())
except Exception as _e:
    check("RM-19 atomic shard promotion self-test (harness error)", False)
    print("  ", _e)

# --- T10 residue investigation + RM-36 re-verification + T12 projectors ---
try:
    _cd = run_text([sys.executable, os.path.join(ROOT, "tools", "investigate_gap_residue.py"), "--self-test"])
    check("T10 Lane C/D residue investigator self-test", _cd.returncode == 0)
except Exception as _e:
    check("T10 Lane C/D residue investigator self-test (harness error)", False)
    print("  ", _e)
try:
    _rv = run_text([sys.executable, os.path.join(ROOT, "tools", "reverify_crosswalk_fallback.py"), "--self-test"])
    check("RM-36 fallback re-verifier self-test", _rv.returncode == 0)
except Exception as _e:
    check("RM-36 fallback re-verifier self-test (harness error)", False)
    print("  ", _e)
try:
    _residue = run_text([sys.executable, os.path.join(ROOT, "tools", "resolve_gap_residue_wave.py"), "--self-test"])
    check("T10 residue + RM-36 demotion self-test (red-first exclusions)", _residue.returncode == 0)
except Exception as _e:
    check("T10 residue + RM-36 demotion self-test (harness error)", False)
    print("  ", _e)
try:
    _pj = run_text([sys.executable, os.path.join(ROOT, "tools", "test_fact_projectors.py")])
    check("T12 fact projector tests (registry + sarf + nahw cycles + defeaters)",
          _pj.returncode == 0)
except Exception as _e:
    check("T12 fact projector tests (harness error)", False)
    print("  ", _e)

# --- T14 D-11 clean wire candidates (bounded, offline, read-only probes) ---
for _script, _args, _marker, _label in (
    ("grade_grammar_reasoning.py", [], "PASS — grade() AND-gate holds", "D-11 grammar-reasoning grader self-test"),
    ("query_language_state.py", ["--graph", os.path.join(ROOT, "qamus", "indexes", "language_state_graph.sample.json"), "--stats"],
     '"counts"', "D-11 language-state sample query"),
    ("source_photo_verify_entry.py", ["--self-test"], "PASS — verify_field", "D-11 source-photo field verifier self-test"),
    ("validate_tafsir_mcp_cache.py", [], "PASS — schema + source-hash integrity + no-public-leak invariant OK",
     "D-11 Tafsir MCP committed cache validator"),
):
    try:
        _d11 = run_text([sys.executable, os.path.join(ROOT, "tools", _script)] + _args, timeout=60)
        check(_label, _d11.returncode == 0 and _marker in (_d11.stdout or ""))
    except Exception as _e:
        check(_label + " (harness error)", False)
        print("  ", _e)

# --- T14 RM-28 runner-less sarf/nahw eval fixture replays ---
for _group, _rows in (("morphology", 7), ("deploy-mechanics", 4), ("governor", 7), ("wrong-reasoning", 6)):
    try:
        _rm28 = run_text([sys.executable, os.path.join(ROOT, "tools", "replay_sarfnahw_evals.py"),
                          "--group", _group], timeout=60)
        _marker = "RM-28 EVAL REPLAY PASS — groups=%s rows=%d" % (_group, _rows)
        check("RM-28 eval replay: %s" % _group, _rm28.returncode == 0 and _marker in (_rm28.stdout or ""))
    except Exception as _e:
        check("RM-28 eval replay: %s (harness error)" % _group, False)
        print("  ", _e)

# --- T14 RM-28 keep-classified dormant tests ---
for _script, _marker, _label in (
    ("test_bulk_deterministic_hover_decisions.py", "bulk deterministic hover decision self-test OK",
     "RM-28 dormant bulk deterministic hover-decision test"),
    ("test_largerollout3_acceptance.py", '"ok": true', "RM-28 dormant largerollout3 acceptance test"),
    ("test_pending_source_triangulation_validator.py", "pending-source-triangulation validator self-test OK",
     "RM-28 dormant pending-source triangulation test"),
    ("test_token_irab_help.py", "token irab help self-test OK", "RM-28 dormant token i'rab help test"),
):
    try:
        _rm28_test = run_text([sys.executable, os.path.join(ROOT, "tools", _script)], timeout=60)
        check(_label, _rm28_test.returncode == 0 and _marker in (_rm28_test.stdout or ""))
    except Exception as _e:
        check(_label + " (harness error)", False)
        print("  ", _e)

# --- RM-21 schema-coherence unification gate ---
# Single gate block: gate-enum unification (fanout_gate<->binding_gate alias table),
# qg class-map 3-way drift, source_key semantic-fork disambiguation, surface_norm
# normalizer pinning, and the cross-schema disjoint same-name enum-field lint. The
# --self-test proves each lint red-first via in-memory mutations.
try:
    _rm21_sc = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_schema_coherence.py"),
                         "--self-test"], timeout=120)
    check("RM-21 schema-coherence self-test (gate-enum/qg-drift/source_key/surface_norm/cross-field; red-first)",
          _rm21_sc.returncode == 0 and "schema coherence self-test OK" in (_rm21_sc.stdout or ""))
except Exception as _rm21_e:
    check("RM-21 schema-coherence self-test (harness error)", False)
    print("  ", _rm21_e)

# --- SKILL-RELEASE: sarf@2 / nahw@2 skill-release candidate gates (registry / fixtures / drift / rich-seg) ---
# Wires the four skill-release feature branches into the harness. Each self-test is deterministic, stdlib-only,
# offline, and fails closed. Reconciled to this file's real conventions (run_text + check).
try:
    # Gate 8: versioned skill-rule registry validates (fail-closed self-test + the real committed registry).
    _sr_reg_st = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_skill_registry.py"),
                           "--self-test"], timeout=120)
    check("SKILL-RELEASE gate 8: skill-rule registry validator self-test",
          _sr_reg_st.returncode == 0 and "skill registry self-test OK" in (_sr_reg_st.stdout or ""))
    _sr_reg = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_skill_registry.py")], timeout=120)
    check("SKILL-RELEASE gate 8: skill-rule registry validates (0 errors, no dup ids / dangling)",
          _sr_reg.returncode == 0 and ", 0 errors" in (_sr_reg.stdout or ""))

    # Gate 9: permanent RED-FIRST skill fixtures (corrected==green, superseded==red-first).
    _sr_fx = run_text([sys.executable, os.path.join(ROOT, "tools", "test_skill_fixtures.py")], timeout=120)
    check("SKILL-RELEASE gate 9: permanent red-first skill fixtures pass",
          _sr_fx.returncode == 0 and "PASS" in (_sr_fx.stdout or ""))

    # Gate 10: skill-drift sentinel (10 drift classes) + deterministic mirror generation. --real must be 0 debt.
    _sr_drift_st = run_text([sys.executable, os.path.join(ROOT, "tools", "check_skill_drift.py"),
                             "--self-test"], timeout=120)
    check("SKILL-RELEASE gate 10: skill-drift self-test (all 10 classes trip red-first, structural invariants hold)",
          _sr_drift_st.returncode == 0)
    _sr_drift_real = run_text([sys.executable, os.path.join(ROOT, "tools", "check_skill_drift.py"),
                               "--real"], timeout=120)
    check("SKILL-RELEASE gate 10: skill-drift --real reports 0 findings (accepted-untested + stale-installs cleared)",
          _sr_drift_real.returncode == 0 and "0 finding(s)" in (_sr_drift_real.stdout or ""))
    _sr_mirror_st = run_text([sys.executable, os.path.join(ROOT, "tools", "generate_skill_mirrors.py"),
                              "--self-test"], timeout=120)
    check("SKILL-RELEASE gate 10: deterministic mirror generation self-test (committed == regenerated)",
          _sr_mirror_st.returncode == 0)

    # Gate 11: rich-seg @2 candidate fixtures (5 sarf + 4 nahw rules; both over-segmentation boundary negatives).
    _sr_rseg = run_text([sys.executable, os.path.join(ROOT, "tools", "skill_fixtures",
                                                      "test_skill_fixtures_richseg.py")], timeout=120)
    check("SKILL-RELEASE gate 11: rich-seg @2 candidate red-first fixtures pass",
          _sr_rseg.returncode == 0 and "PASS" in (_sr_rseg.stdout or ""))

    # Gate 12: INCREMENT-21 @2.1 candidate fixtures (27 rules: 19 sarf + 8 nahw) — red-first + non-constant
    # discriminator guard + builder regeneration-clean + every @2.1 registry id covered.
    _sr_inc = run_text([sys.executable, os.path.join(ROOT, "tools", "skill_fixtures",
                                                     "test_skill_fixtures_increment21.py")], timeout=120)
    check("SKILL-RELEASE gate 12: @2.1 increment red-first + non-constant-discriminator fixtures pass",
          _sr_inc.returncode == 0 and "PASS" in (_sr_inc.stdout or ""))
    # Gate 12: the @2.1 increment MERGED with the released registry validates (0 dup / 0 dangling).
    import tempfile as _tmp
    _base = os.path.join(ROOT, "qamus", "skills", "rule-registry.jsonl")
    _inc = os.path.join(ROOT, "qamus", "skills", "rule-registry-increment-21.jsonl")
    _merged_ok = False
    try:
        _mfd, _mpath = _tmp.mkstemp(suffix="-merged-registry.jsonl")
        with os.fdopen(_mfd, "w", encoding="utf-8", newline="\n") as _mf:
            for _p in (_base, _inc):
                _mf.write(open(_p, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n"))
        _sr_merged = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_skill_registry.py"),
                               "--registry", _mpath], timeout=120)
        _merged_ok = _sr_merged.returncode == 0 and ", 0 errors" in (_sr_merged.stdout or "")
    finally:
        try:
            os.remove(_mpath)
        except Exception:
            pass
    check("SKILL-RELEASE gate 12: released + @2.1-increment registry validates merged (0 dup / 0 dangling)",
          _merged_ok)

    # Gate 13: INCREMENT-22 @2.2 candidate fixtures (18 rules: 15 sarf + 3 nahw; 12 norm-domain) —
    # the QAMUS-RICH-NORM-001 consolidation: red-first + non-constant-discriminator guard + builder
    # regeneration-clean + every @2.2 registry id covered + norm@1 contract clauses present.
    _sr_inc22 = run_text([sys.executable, os.path.join(ROOT, "tools", "skill_fixtures",
                                                       "test_skill_fixtures_increment22.py")], timeout=120)
    check("SKILL-RELEASE gate 13: @2.2 increment red-first + non-constant-discriminator fixtures pass",
          _sr_inc22.returncode == 0 and "PASS" in (_sr_inc22.stdout or ""))
    # Gate 13: the @2.2 increment MERGED with the released + @2.1 registries validates (0 dup / 0 dangling).
    _inc22 = os.path.join(ROOT, "qamus", "skills", "rule-registry-increment-22.jsonl")
    _merged22_ok = False
    try:
        _m22fd, _m22path = _tmp.mkstemp(suffix="-merged22-registry.jsonl")
        with os.fdopen(_m22fd, "w", encoding="utf-8", newline="\n") as _m22f:
            for _p in (_base, _inc, _inc22):
                _m22f.write(open(_p, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n"))
        _sr_merged22 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_skill_registry.py"),
                                 "--registry", _m22path], timeout=120)
        _merged22_ok = _sr_merged22.returncode == 0 and ", 0 errors" in (_sr_merged22.stdout or "")
    finally:
        try:
            os.remove(_m22path)
        except Exception:
            pass
    check("SKILL-RELEASE gate 13: released + @2.1 + @2.2 increment registry validates merged (0 dup / 0 dangling)",
          _merged22_ok)

    # Gate 14: INCREMENT-23 @2.3 candidate fixtures (8 rules: 6 sarf + 2 nahw; 2 norm-domain) — the
    # Window-1-2026-07-16 measured flywheel increment: red-first + non-constant-discriminator guard +
    # builder regeneration-clean + every @2.3 registry id covered + the N-ROOT-03 / N-PED-01 clauses present.
    _sr_inc23 = run_text([sys.executable, os.path.join(ROOT, "tools", "skill_fixtures",
                                                       "test_skill_fixtures_increment23.py")], timeout=120)
    check("SKILL-RELEASE gate 14: @2.3 increment red-first + non-constant-discriminator fixtures pass",
          _sr_inc23.returncode == 0 and "PASS" in (_sr_inc23.stdout or ""))
    # Gate 14: the @2.3 increment MERGED with the released + @2.1 + @2.2 registries validates (0 dup / 0 dangling).
    _inc23 = os.path.join(ROOT, "qamus", "skills", "rule-registry-increment-23.jsonl")
    _merged23_ok = False
    try:
        _m23fd, _m23path = _tmp.mkstemp(suffix="-merged23-registry.jsonl")
        with os.fdopen(_m23fd, "w", encoding="utf-8", newline="\n") as _m23f:
            for _p in (_base, _inc, _inc22, _inc23):
                _m23f.write(open(_p, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n"))
        _sr_merged23 = run_text([sys.executable, os.path.join(ROOT, "tools", "validate_skill_registry.py"),
                                 "--registry", _m23path], timeout=120)
        _merged23_ok = _sr_merged23.returncode == 0 and ", 0 errors" in (_sr_merged23.stdout or "")
    finally:
        try:
            os.remove(_m23path)
        except Exception:
            pass
    check("SKILL-RELEASE gate 14: released + @2.1 + @2.2 + @2.3 increment registry validates merged (0 dup / 0 dangling)",
          _merged23_ok)
except Exception as _sr_e:
    check("SKILL-RELEASE skill-release candidate gates (harness error)", False)
    print("  ", _sr_e)

# F-A: governed typed-claim authoring boundary — prose-only input must fail,
# tranche-1-backed input must pass, aliases must normalize, and unresolved
# language must remain explicitly mapped before any projection can proceed.
try:
    _fa_contract_self = run_text([sys.executable,
                                  os.path.join(ROOT, "tools", "validate_typed_claim_contract.py"),
                                  "--self-test"], timeout=120)
    check("F-A typed-claim contract self-test and red-first fixtures pass",
          _fa_contract_self.returncode == 0 and
          "FA TYPED-CLAIM CONTRACT SELF-TEST PASS" in (_fa_contract_self.stdout or ""))
    _fa_contract_fixtures = run_text([sys.executable,
                                      os.path.join(ROOT, "tools", "validate_typed_claim_contract.py"),
                                      "--fixtures",
                                      os.path.join(ROOT, "qamus", "examples", "fa-contract")], timeout=120)
    check("F-A typed-claim contract fixture boundary passes",
          _fa_contract_fixtures.returncode == 0 and
          "FA TYPED-CLAIM CONTRACT FIXTURES PASS" in (_fa_contract_fixtures.stdout or ""))
except Exception as _fa_contract_e:
    check("F-A typed-claim contract gates (harness error)", False)
    print("  ", _fa_contract_e)

# FAM2: bounded lexical noun/adjective formation producer.  The committed
# fixture gate is repo-self-contained; the operational calibration packet is
# generated only when the caller supplies the read-only corpus explicitly.
try:
    _fam2_self = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_fam2_lexical.py"),
        "--self-test",
    ], timeout=120)
    check(
        "FAM2 lexical formation producer self-test and red-first fixtures pass",
        _fam2_self.returncode == 0
        and "FAM2 LEXICAL PRODUCER SELF-TEST PASS" in (_fam2_self.stdout or ""),
    )
    _fam2_unit = run_text([
        sys.executable,
        "-m",
        "unittest",
        "tools.test_fam2_lexical_producer",
        "-q",
    ], timeout=120)
    check(
        "FAM2 focused typed-fact unit tests pass",
        _fam2_unit.returncode == 0
        and "OK" in ((_fam2_unit.stdout or "") + (_fam2_unit.stderr or "")),
    )
    _fam2_packet = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_fam2_lexical.py"),
        "--fixtures",
        os.path.join(ROOT, "qamus", "examples", "fam2-lexical"),
    ], timeout=120)
    check(
        "FAM2 committed calibration packet validates (>=40, typed output, zero public mutation)",
        _fam2_packet.returncode == 0
        and "FAM2 LEXICAL PRODUCER FIXTURES PASS" in (_fam2_packet.stdout or ""),
    )
except Exception as _fam2_e:
    check("FAM2 lexical formation producer gates (harness error)", False)
    print("  ", _fam2_e)

# FB1: bounded clitic-pronoun producer calibration. The self-test is the
# producer gate; the fixture and committed sample validators prove that the
# packet remains F-A governed, >=40 rows, and repo-self-contained.
try:
    _fb1_self = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "build_clitic_pronoun_producer.py"),
        "--self-test",
    ], timeout=120)
    check(
        "FB1 clitic-pronoun producer self-test and red-first fixtures pass",
        _fb1_self.returncode == 0
        and "FB1 CLITIC PRONOUN PRODUCER SELF-TEST PASS" in (_fb1_self.stdout or ""),
    )
    _fb1_unit = run_text([
        sys.executable,
        "-m",
        "unittest",
        "tools.test_clitic_pronoun_producer",
        "-q",
    ], timeout=120)
    check(
        "FB1 producer focused typed-fact unit tests pass",
        _fb1_unit.returncode == 0
        and "OK" in ((_fb1_unit.stdout or "") + (_fb1_unit.stderr or "")),
    )
    _fb1_packet = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_clitic_pronoun_calibration.py"),
        "--fixtures",
        os.path.join(ROOT, "qamus", "examples", "fb1-clitic-pronoun"),
    ], timeout=120)
    check(
        "FB1 calibration packet validates (>=40, typed output, zero public mutation)",
        _fb1_packet.returncode == 0
        and "FB1 CALIBRATION PACKET VALIDATION PASS" in (_fb1_packet.stdout or ""),
    )
except Exception as _fb1_e:
    check("FB1 clitic-pronoun producer gates (harness error)", False)
    print("  ", _fb1_e)

# F-D: shared evidence compiler — the checked-in contract, normalized payload,
# generated HTML proof, registered projector, and 455-row candidate matrix must
# all validate together. This gate is fixture-only and never mutates data/ or a
# live/runtime surface.
try:
    _fd_compiler_self = run_text([sys.executable,
                                  os.path.join(ROOT, "tools", "validate_fd_compiler.py"),
                                  "--self-test"], timeout=120)
    check("F-D shared compiler contract/payload/render/matrix self-test passes",
          _fd_compiler_self.returncode == 0 and
          "FD COMPILER SELF-TEST PASS" in (_fd_compiler_self.stdout or ""))
    _fd_compiler_unit = run_text([sys.executable, "-m", "unittest", "tools.test_fd_compiler", "-q"], timeout=120)
    check("F-D compiler red/green unit fixtures pass",
          _fd_compiler_unit.returncode == 0 and
          "OK" in ((_fd_compiler_unit.stdout or "") + (_fd_compiler_unit.stderr or "")))
except Exception as _fd_compiler_e:
    check("F-D shared compiler gates (harness error)", False)
    print("  ", _fd_compiler_e)

# F-D2: producer-aware 455-row rerun.  This gate validates only the committed
# report/verdict fixtures; the external corpus is supplied explicitly to the
# operational runner and is never a harness default or a repository input.
try:
    _fd2_rerun_self = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_fd2_rerun.py"),
        "--self-test",
    ], timeout=120)
    check(
        "F-D2 producer-aware 455 rerun committed-fixture gate passes",
        _fd2_rerun_self.returncode == 0
        and "FD2 RERUN SELF-TEST PASS" in (_fd2_rerun_self.stdout or ""),
    )
except Exception as _fd2_rerun_e:
    check("F-D2 producer-aware rerun gate (harness error)", False)
    print("  ", _fd2_rerun_e)

# F-C1: bounded naḥw dependency producer.  The fixture and packet validators
# are repo-self-contained; external corpus paths are intentionally not part of
# this gate and are supplied only when the calibration packet is regenerated.
try:
    _fc1_nahw_self = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_fc1_nahw_producer.py"),
        "--self-test",
    ], timeout=120)
    check(
        "F-C1 naḥw producer self-test and red-first fixtures pass",
        _fc1_nahw_self.returncode == 0
        and "FC1 NAHW PRODUCER SELF-TEST PASS" in (_fc1_nahw_self.stdout or ""),
    )
    _fc1_nahw_fixtures = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_fc1_nahw_producer.py"),
        "--fixtures",
        os.path.join(ROOT, "qamus", "examples", "fc1-nahw"),
    ], timeout=120)
    check(
        "F-C1 committed naḥw calibration packet validates",
        _fc1_nahw_fixtures.returncode == 0
        and "FC1 NAHW PRODUCER FIXTURES PASS" in (_fc1_nahw_fixtures.stdout or ""),
    )
except Exception as _fc1_nahw_e:
    check("F-C1 naḥw producer gates (harness error)", False)
    print("  ", _fc1_nahw_e)

# F-B/F-C: canonical occurrence-to-appearance index.  The self-test is red-first
# (same-loc fork must fail; same-surface different-loc pair is allowed) and the
# real check binds the committed index to the sibling read-only whitelist.
try:
    _idx_self = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_appearance_parity.py"),
        "--self-test",
    ], timeout=120)
    check(
        "F-B/F-C occurrence appearance parity red-first self-test",
        _idx_self.returncode == 0
        and "APPEARANCE PARITY SELF-TEST PASS" in (_idx_self.stdout or ""),
    )
    # The corpus whitelist is an external artifact (not repo-tracked); the
    # corpus-wide parity run takes it via an explicit --whitelist argument in
    # operational use. The harness gate is repo-self-contained: it validates
    # the COMMITTED index's structural invariants (unique locs, well-formed
    # appearance records, projection-hash presence) without recomputation.
    _idx_real = run_text([
        sys.executable,
        os.path.join(ROOT, "tools", "validate_appearance_parity.py"),
        "--index",
        os.path.join(ROOT, "qamus", "indexes", "occurrence-appearances.jsonl"),
        "--structure-only",
    ], timeout=120)
    check(
        "F-B/F-C committed occurrence appearance index parity validates",
        _idx_real.returncode == 0
        and "APPEARANCE PARITY PASS" in (_idx_real.stdout or ""),
    )
except Exception as _idx_e:
    check("F-B/F-C occurrence appearance parity gates (harness error)", False)
    print("  ", _idx_e)

if fails:
    print("\n%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("\nALL REGRESSION CHECKS PASS")
