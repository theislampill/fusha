#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the nahw engine is production+teaching complete (fail-closed). Phase 3 gate.

Fails if SKILL.md names a missing artifact, particle functions are not machine-testable, same-surface
polysemy examples are absent, conclusion-only reasoning is allowed (no grammar-risk gate), the hover
recipe or learner path is absent, the provenance invariant is missing, or the skill depends on MCP.

A2 added the behavioural half (was GAP-N5 — this validator was structural only):
  * every file in nahw/rules/ carries a TRUTHFUL consumption status, and a rules file that claims a
    consumer must actually be readable through it (a new unconsumed rules file now fails this gate);
  * the particle consumer is exercised on real homographs, positive AND negative;
  * the right-answer/wrong-reason property is asserted through structured evidence, not prose.
"""
import json, os, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
N = os.path.join(ROOT, "nahw")
errs = []
def need(rel, why):
    if not os.path.exists(os.path.join(N, rel)): errs.append(f"missing {rel} ({why})")
def read(rel):
    p = os.path.join(N, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

skill = read("SKILL.md")
if not skill: errs.append("nahw/SKILL.md missing")

for p in ["particle-decision","particle-function-decision","preposition-pronoun","negation",
          "relative-interrogative","conditionals","idafa-jar-majrur","irab-case-mood",
          "irab-teaching-diagnosis","referent-context","grammar-risk-gate","hover-application",
          "qamus-entry-authoring","corpus-to-qamus","pronoun-attachment","function-token-hover-review",
          "ma-function-decision","pp-attachment-review","governing-particle-mood-review",
          "exception-and-vocative-review"]:
    need(f"procedures/{p}.md", "required procedure")
for r in ["particle-functions","irab-teaching-map","learner-error-remediation","particles","idafa","jar-majrur"]:
    need(f"references/{r}.md", "required reference")
for e in ["particle-function-eval.jsonl","irab-polysemy-eval.jsonl","grammar-problems-derived-eval.jsonl"]:
    need(f"evals/{e}", "required eval")
need("drills/particle-disambiguation.md", "required drill")
need("drills/irab-case-mood.md", "required drill")

for token in ["particle-function-decision","irab-teaching-diagnosis","particle-function-eval",
              "irab-polysemy-eval","particle-functions","irab-teaching-map","learner-error-remediation",
              "function-token-hover-review","ma-function-decision","pp-attachment-review",
              "governing-particle-mood-review","exception-and-vocative-review","function_class",
              "attachment","composition"]:
    if token not in skill: errs.append(f"SKILL.md does not reference {token}")

# particle functions machine-testable: every row has functions[] + context_function + a loc
pf = os.path.join(N, "evals", "particle-function-eval.jsonl")
if os.path.exists(pf):
    rows = [json.loads(l) for l in open(pf, encoding="utf-8") if l.strip()]
    if len(rows) < 25: errs.append(f"particle-function-eval has {len(rows)} cases (need >=25)")
    particles = set()
    for r in rows:
        for k in ("functions", "context_function", "particle"):
            if k not in r: errs.append(f"PF row {r.get('id')} missing {k}")
        particles.add(r.get("particle"))
    for need_p in ["مَا","مَن","مِن","إِنْ","لَا","أَلَا","أَلَّا","فَمَا","أَمْ","كَلَّا","لِمَ",
                   "واو","فاء","أ","إِنَّمَا","إِلَّا"]:
        if need_p not in particles: errs.append(f"particle-function-eval missing particle {need_p}")
    blob = json.dumps(rows, ensure_ascii=False)
    if "negative_ma_like_laysa" not in blob:
        errs.append("particle-function-eval missing negative_ma_like_laysa case")
    rich_pf = {"PF-033", "PF-034", "PF-035", "PF-036", "PF-037", "PF-038"}
    rich_rows = {r.get("id"): r for r in rows if r.get("id") in rich_pf}
    for rid in sorted(rich_pf):
        r = rich_rows.get(rid)
        if not r:
            errs.append(f"particle-function-eval missing structured row {rid}")
            continue
        if "parse_requirement" not in r:
            errs.append(f"PF row {rid} missing parse_requirement")
    if rich_rows.get("PF-037", {}).get("expected_mood") != "subjunctive":
        errs.append("PF-037 must require subjunctive mood")

# iʿrāb-polysemy: required same-surface regressions present + each has a reading
ip = os.path.join(N, "evals", "irab-polysemy-eval.jsonl")
if os.path.exists(ip):
    rows = [json.loads(l) for l in open(ip, encoding="utf-8") if l.strip()]
    blob = json.dumps(rows, ensure_ascii=False)
    for surf in ["وَمَا","عَادٍ","أَلَّا","أَلَا","فَمَا","جِنَّةٍ","أُمَّةً","يَقْدِرُ","حَلِيمٌ",
                 "بِسَلَامٍ","بِبَدْرٍ","وَٱلتِّينِ","وَٱلزَّيْتُونِ","وَبِٱلنَّجْمِ",
                 "جَادَلُوكَ","مُعَلَّمٌ","ذَٰلِكُمْ"]:
        if surf not in blob: errs.append(f"irab-polysemy-eval missing regression {surf}")
    for r in rows:
        if "reading" not in r: errs.append(f"IP row {r.get('id')} missing reading")
    rich_ip = {"IP-026", "IP-027", "IP-028", "IP-029", "IP-030", "IP-031", "IP-032", "IP-033", "IP-034"}
    rich_rows = {r.get("id"): r for r in rows if r.get("id") in rich_ip}
    for rid in sorted(rich_ip):
        r = rich_rows.get(rid)
        if not r:
            errs.append(f"irab-polysemy-eval missing structured row {rid}")
            continue
        for k in ("composition", "attachment", "reject_host_only_gloss"):
            if k not in r:
                errs.append(f"IP row {rid} missing {k}")
        if r.get("reject_host_only_gloss") is not True:
            errs.append(f"IP row {rid} must reject host-only glosses")

# conclusion-only reasoning forbidden: grammar-risk-gate procedure + grade tool must exist
if "answer AND" not in read("procedures/grammar-risk-gate.md") and "reasoning" not in read("procedures/grammar-risk-gate.md"):
    errs.append("grammar-risk-gate procedure does not enforce answer+reasoning")
if not os.path.exists(os.path.join(ROOT, "tools", "grade_grammar_reasoning.py")):
    errs.append("grade_grammar_reasoning.py missing (right-answer/wrong-reasoning trap enforcement)")

# hover recipe + learner path + provenance invariant
if not read("procedures/hover-application.md"): errs.append("hover-application recipe missing")
if not os.path.exists(os.path.join(N, "curriculum", "zero-to-fluency-nahw.md")):
    errs.append("learner path (curriculum/zero-to-fluency-nahw.md) missing")
if "src" not in skill.lower(): errs.append("SKILL.md missing public provenance invariant")
low = skill.lower()
if ("mcp" in low) and ("mcp-free" not in low) and ("not a skill" not in low) and ("never" not in low) and ("adapter" not in low):
    errs.append("SKILL.md appears to DEPEND on MCP (must be MCP-free / adapter-generic)")

# ---------------------------------------------------------------------------
# A2 behavioural block — consumption honesty + a live consumer exercise
# ---------------------------------------------------------------------------
# Truthful status for every file in nahw/rules/. `consumed` names the module that reads it; `fixture_gated`
# means only a committed fixture exercises it; `documentary` means it is prose for humans. Adding a rules file
# without classifying it here is a FAIL — that is how GAP-N2 ("5 of 12 files have zero executable consumer")
# stops being able to recur silently.
# Truthful status for every file in nahw/rules/. `consumed` is reserved for a file a PRODUCTION decision or
# record-validation path reads AND whose mutation provably changes that path's result (the load-bearing probe
# below). Everything a test/validator reads only, or that no code reads, is downgraded. File existence, an
# import, a path reference or a self-reported status do NOT establish a consumer.
# Truthful status for every file in nahw/rules/. `consumed` is reserved for a file that a PRODUCTION
# record-validation path reads AND whose mutation provably changes THAT FILE'S OWN decision property (the
# distinct on/off probes below). A consumer that is a test, a parity check, or an A2 helper called only by
# tests is `fixture_gated`. File existence, an import, a path reference, a self-reported status and a
# structural row check do NOT establish a consumer.
#
# Deliberately conservative: funcword-homograph-prepass-rules.json HAS a real consumer
# (tools/funcword_homograph_prepass.py + 13 tests) and two-vote-required-rules.json has four-home SSOT parity
# (tools/test_gate_ssot.py), but A2 added no on/off probe for either, so A2 does not count them as proven
# production-consumed. Do not re-promote them without a probe.
RULES_CONSUMPTION = {
    # file: (status, consumer, distinct probe id or None)
    "context-sense-rules.json": ("consumed", "tools/validate_linguistic_decisions.py", "quarantine"),
    "funcword-homograph-prepass-rules.json": ("fixture_gated", "tools/test_funcword_homograph_prepass.py",
                                              None),
    "grammar-problems-gates.json": ("fixture_gated", "tools/fusha_nahw_gate_rules.py", None),
    "grammar-problems-issue-clusters.json": ("fixture_gated", "tools/check_regressions.py", None),
    "irab-safety-gates.json": ("fixture_gated", "tools/fusha_nahw_gate_rules.py", None),
    "negation-rules.json": ("fixture_gated", "tools/fusha_nahw_particle_rules.py", None),
    "particle-context-rules.json": ("consumed", "tools/validate_linguistic_decisions.py", "haraka_reading"),
    "preposition-pronoun-rules.json": ("consumed", "tools/validate_linguistic_decisions.py", "root_guard"),
    "pronoun-attachment-rules.json": ("fixture_gated", "tools/test_suffix_pronoun.py", None),
    "referent-guard-rules.json": ("consumed", "tools/validate_linguistic_decisions.py", "proper_noun"),
    "state-transition-rules.json": ("consumed", "tools/validate_linguistic_decisions.py",
                                    "forbidden_role"),
    "two-vote-required-rules.json": ("fixture_gated", "tools/test_gate_ssot.py", None),
}
# One DISTINCT probe per file claimed production-consumed. Each names the record the production validator must
# reject, the needle proving WHICH rule rejected it, and the mutation of THAT FILE ONLY that must make the
# rejection disappear. `isolated_from` lists probes whose rejection must SURVIVE this mutation, so two files
# can never share a single probe.
LOAD_BEARING_PROBES = {
    "haraka_reading": {
        "surface_ar": "لَمْ", "gloss": "why", "needle": "forbidden role collision lam_not_lima",
        "file": "particle-context-rules.json", "mutate": "particle_rule_lam",
        "property": "which reading the content-letter diacritic licenses",
        "isolated_from": ["quarantine", "proper_noun", "root_guard"]},
    "forbidden_role": {
        "surface_ar": "لَمْ", "gloss": "why", "needle": "forbidden role collision lam_not_lima",
        "file": "state-transition-rules.json", "mutate": "forbidden_transitions",
        "property": "which sibling role/gloss a resolved reading may never carry",
        "isolated_from": ["quarantine", "proper_noun", "root_guard"]},
    "quarantine": {
        "surface_ar": "ٱلْمُلْك", "gloss": "angels", "needle": "polyseme quarantine",
        "file": "context-sense-rules.json", "mutate": "polyseme_quarantines",
        "property": "which sibling sense is blocked from leaking onto a token",
        "isolated_from": ["haraka_reading", "forbidden_role", "proper_noun", "root_guard"]},
    "proper_noun": {
        "surface_ar": "مُحَمَّد", "gloss": "to praise", "needle": "referent guard",
        "file": "referent-guard-rules.json", "mutate": "referent_examples",
        "property": "which proper noun may never carry its homographic verb gloss",
        "isolated_from": ["haraka_reading", "forbidden_role", "quarantine", "root_guard"]},
    "root_guard": {
        "surface_ar": "إِلَيْنَا", "gloss": "to us", "root_ar": "ل ي ن", "needle": "hard guard",
        "file": "preposition-pronoun-rules.json", "mutate": "pp_hard_guard",
        "property": "which root a preposition+pronoun may never be assigned",
        "isolated_from": ["haraka_reading", "forbidden_role", "quarantine", "proper_noun"]},
}

_rules_dir = os.path.join(N, "rules")
_on_disk = sorted(f for f in os.listdir(_rules_dir) if f.endswith(".json"))
for _f in _on_disk:
    if _f not in RULES_CONSUMPTION:
        errs.append(f"nahw/rules/{_f} has no declared consumption status "
                    f"(classify it consumed | fixture_gated | documentary | candidate_only)")
for _f, (_status, _consumer, _probe) in RULES_CONSUMPTION.items():
    if _f not in _on_disk:
        errs.append(f"RULES_CONSUMPTION names nahw/rules/{_f}, which is not on disk")
    if _status not in ("consumed", "fixture_gated", "documentary", "candidate_only"):
        errs.append(f"nahw/rules/{_f}: untruthful status {_status!r}")
    if not os.path.exists(os.path.join(ROOT, _consumer)):
        errs.append(f"nahw/rules/{_f} names consumer {_consumer}, which does not exist")
    if _status == "consumed" and _probe is None and _f not in (
            "funcword-homograph-prepass-rules.json", "two-vote-required-rules.json"):
        errs.append(f"nahw/rules/{_f} claims consumed with no load-bearing probe")

try:
    from tools import fusha_nahw_context_rules as _CTX
    from tools import fusha_nahw_gate_rules as _GATE
    from tools import fusha_nahw_particle_rules as _PR
    from tools.grade_grammar_reasoning import grade_structured as _gs
except Exception as _e:                                             # pragma: no cover - import guard
    errs.append(f"nahw rule consumers are not importable: {_e}")
else:
    # BEHAVIOUR, not existence: the content-letter harakah must decide, and its absence must force pending
    for _surface, _want in (("مِنَ", "B"), ("وَمِنَ", "B"), ("مَن", "A"), ("لَمْ", "A"), ("لِمَ", "B"),
                            ("إِنَّ", "B"), ("أَنَّ", "A"), ("لَمَّا", "A")):
        _r = _PR.resolve_particle_homograph(_surface)
        if _r.get("branch") != _want or _r.get("decision") != "resolved":
            errs.append(f"particle consumer mis-resolved {_surface}: {_r.get('branch')}/{_r.get('decision')} "
                        f"(want {_want}/resolved)")
    for _surface in ("من", "لم", "لما", "ان"):
        if _PR.resolve_particle_homograph(_surface).get("decision") != "pending":
            errs.append(f"particle consumer resolved the undiacritized {_surface} instead of holding pending")
    # the forbidden-collision table must be enforced, not merely present
    if not _PR.forbidden_gloss_violations("مِنَ", "and whoever"):
        errs.append("state-transition forbidden_transitions are not enforced (مِن accepted a 'whoever' gloss)")
    # rivals must survive; no iʿrāb rule may be auto_safe
    if _CTX.context_sense_alternatives("يَقْدِرُ").get("decision") != "pending":
        errs.append("context-sense consumer auto-selected a contronym sense instead of preserving rivals")
    for _rid in _GATE.irab_rule_ids():
        if _GATE.irab_rule_gate(_rid) == "auto_safe":
            errs.append(f"irab-safety-gates#{_rid} resolved to auto_safe")
    if _GATE.validate_rule_files():
        errs.append("gate rule files are not SSOT-consistent: %s" % _GATE.validate_rule_files()[:3])
    # conclusion-only reasoning must be rejected from STRUCTURED evidence, not a caller boolean
    _case = {"id": "vns", "required_gate": "two_vote_required", "expected_conclusion": "genitive",
             "expected_reason_keys": ["lam-jarr-fused-majrur-kasra"]}
    # ROUND-8: the two-vote gate needs real vote artifacts and a repository-resolvable address; a boolean and
    # a made-up "quran:demo" address are no longer evidence.
    from tools.grade_grammar_reasoning import mint_fixture_vote as _mv, project_vote as _pv
    _va = _mv(0, reason_key="lam-jarr-fused-majrur-kasra", conclusion="genitive", case_mood="genitive",
              relation="preposition_governs_genitive", worklist_id="wl-vns-a",
              fact_type="case_assignment", vote_id="vote:vns:a")
    _vb = _mv(1, reason_key="lam-jarr-fused-majrur-kasra", conclusion="genitive", case_mood="genitive",
              relation="preposition_governs_genitive", worklist_id="wl-vns-b",
              fact_type="case_assignment", vote_id="vote:vns:b")
    _claim = dict(_pv(_va), two_vote_evidence=[_va, _vb])
    if _gs(_case, dict(_claim, reason_key="lam-jarr-fused-majrur-kasra",
                       governor={"governor_type": "preposition"}))["pass"] is not True:
        errs.append("grade_structured blocked an honest, fully-justified iʿrāb claim")
    if _gs(_case, dict(_claim, reason_key="lam-jarr-fused-majrur-kasra", governor=None,
                       reasoning_ok=True))["pass"]:
        errs.append("grade_structured accepted a case asserted with NO governor (right answer, wrong reason)")
    if _gs(_case, dict(_claim, reason_key="vns:expected",
                       governor={"governor_type": "preposition"}))["reason_defect"]             != "reason_key_unregistered":
        errs.append("grade_structured accepted an unregistered/fabricated reason key")

    # LOAD-BEARING PROBES: a file may claim `consumed` only if a PRODUCTION path both fires on it and stops
    # firing when the rule data is removed. File existence and imports prove nothing.
    from tools import validate_linguistic_decisions as _VLD
    _base = {"decision_id": "lingdec-000001", "source_address": "quran:2:247:6", "pos": "particle",
             "lemma_ar": "x", "decision": {"type": "authored_gloss", "pending_reason": None,
                                           "confidence": "high"}, "public_export_allowed": False}
    _MUTATORS = {
        "particle_rule_lam": (_PR, "PARTICLE_RULES_PATH",
                              lambda d: d.__setitem__("rules",
                                                      [r for r in d["rules"] if r["id"] != "lam_vs_lima"])),
        "forbidden_transitions": (_PR, "STATE_RULES_PATH",
                                  lambda d: d.__setitem__("forbidden_transitions", [])),
        "polyseme_quarantines": (_CTX, "CONTEXT_SENSE_PATH",
                                 lambda d: d["polyseme_quarantines"].__setitem__("entries", [])),
        "referent_examples": (_CTX, "REFERENT_GUARD_PATH",
                              lambda d: [r.pop("examples", None) for r in d.get("rules", [])]),
        "pp_hard_guard": (_CTX, "PREP_PRONOUN_PATH",
                          lambda d: [r.pop("hard_guard", None) for r in d.get("rules", [])]),
    }

    def _probe_record(pr):
        rec = dict(_base, surface_ar=pr["surface_ar"], root_ar=pr.get("root_ar"))
        rec["decision"] = dict(_base["decision"], gloss_en_authored=pr["gloss"])
        return rec

    def _fires(pid):
        pr = LOAD_BEARING_PROBES[pid]
        return [v for v in _VLD.invariant_violations(_probe_record(pr)) if pr["needle"] in v]

    # each `consumed` file must name a DISTINCT probe, and no two files may share one
    _claimed = [p for _f, (_st, _c, p) in RULES_CONSUMPTION.items() if _st == "consumed"]
    if len(set(_claimed)) != len(_claimed):
        errs.append("two files claim consumed through the same probe; each needs its own decision property")
    for _f, (_st, _c, _p) in RULES_CONSUMPTION.items():
        if _st == "consumed" and LOAD_BEARING_PROBES.get(_p, {}).get("file") != _f:
            errs.append(f"nahw/rules/{_f} claims probe {_p!r}, which is not bound to that file")

    for _pid, _pr in LOAD_BEARING_PROBES.items():
        if not _fires(_pid):
            errs.append(f"load-bearing probe {_pid}: the production validator did not fire on "
                        f"{_pr['surface_ar']!r}/{_pr['gloss']!r} - {_pr['file']} is NOT consumed")
            continue
        _mod, _attr, _mutate = _MUTATORS[_pr["mutate"]]
        _key = getattr(_mod, _attr)
        _saved = _mod._CACHE.get(_key)
        _data = json.loads(json.dumps(_mod._load(_key)))
        _mutate(_data)
        _mod._CACHE[_key] = _data
        try:
            _still = _fires(_pid)
            # ISOLATION: mutating THIS file must not silence any OTHER file's decision property
            _leaked = [q for q in _pr.get("isolated_from", []) if not _fires(q)]
        finally:
            if _saved is None:
                _mod._CACHE.pop(_key, None)
            else:
                _mod._CACHE[_key] = _saved
        if _still:
            errs.append(f"load-bearing probe {_pid}: the rejection survived removing {_pr['file']} data - "
                        f"the production path is hard-coded, not consuming that file")
        if _leaked:
            errs.append(f"load-bearing probe {_pid}: mutating {_pr['file']} also silenced {_leaked} - the "
                        f"probes are not distinct")

    # ---------------------------------------------------------------------------------------------------
    # DISTINCT load-bearing on/off probe: occurrence-specific contextual مَا relative-vs-negation
    # (particle-context-rules.json#maa_relative_vs_negation). The file already claims `consumed` above through
    # the UNRELATED haraka_reading probe (bound to lam_vs_lima); this proves the NEW rule is independently
    # load-bearing in a production path (fusha_nahw_particle_rules.maa_context_frame), rather than merely
    # riding on that file's already-established status. It does not relabel any fixture-gated rule.
    # ---------------------------------------------------------------------------------------------------
    _MAA_REL_EV = _PR.mint_fixture_observation("object_of_verb_then_prep", source_address="quran:2:284:10",
                                               quran_loc="2:284", word=10, surface="مَا", target_kind="token",
                                               target_value="maa_relative_vs_negation")
    _maa_on = _PR.maa_context_frame("مَا", evidence=_MAA_REL_EV, at="quran:2:284:10")
    if _maa_on.get("decision") != "candidate" or _maa_on.get("function_candidate") != "relative":
        errs.append("maa_relative_vs_negation probe: the production path did not fire on a unique frame "
                    "('object_of_verb_then_prep' -> relative) - the new rule is NOT consumed")
    else:
        _maa_key = _PR.PARTICLE_RULES_PATH
        _maa_saved = _PR._CACHE.get(_maa_key)
        _maa_data = json.loads(json.dumps(_PR._load(_maa_key)))
        _maa_rule = next((r for r in _maa_data.get("rules", []) if r.get("id") == "maa_relative_vs_negation"),
                         None)
        if _maa_rule is None:
            errs.append("maa_relative_vs_negation probe: the rule is missing from particle-context-rules.json")
        else:
            _maa_rule["frame_table"] = []
        _PR._CACHE[_maa_key] = _maa_data
        try:
            _maa_off = _PR.maa_context_frame("مَا", evidence=_MAA_REL_EV, at="quran:2:284:10")
            # ISOLATION: removing THIS rule's own data must not silence the unrelated haraka_reading probe
            _maa_isolated = _fires("haraka_reading")
        finally:
            if _maa_saved is None:
                _PR._CACHE.pop(_maa_key, None)
            else:
                _PR._CACHE[_maa_key] = _maa_saved
        if _maa_off.get("decision") == "candidate":
            errs.append("maa_relative_vs_negation probe: the candidate survived removing the rule's own "
                        "frame_table data - the production path is hard-coded, not consuming the rule file")
        if not _maa_isolated:
            errs.append("maa_relative_vs_negation probe: mutating the new rule's data also silenced the "
                        "unrelated haraka_reading probe - the probes are not distinct")

    # the helper inventories must AGREE EXACTLY with this authoritative file-level inventory
    for _mod in (_PR, _CTX, _GATE):
        for _path, _status in getattr(_mod, "FILE_CONSUMPTION", {}).items():
            _f = _path.rsplit("/", 1)[-1]
            _want = RULES_CONSUMPTION.get(_f, (None,))[0]
            if _status != _want:
                errs.append(f"{_mod.__name__} reports {_f} as {_status!r}; the authoritative inventory says "
                            f"{_want!r}")
    for _inv in (_PR.rule_status(), _CTX.rule_status(), _GATE.rule_status()):
        for _path, _rows in _inv.items():
            _f = _path.rsplit("/", 1)[-1]
            _want = RULES_CONSUMPTION.get(_f, (None,))[0]
            for _rid, _st in _rows.items():
                if _st not in ("consumed", "fixture_gated", "documentary", "candidate_only"):
                    errs.append(f"{_path}#{_rid}: untruthful status {_st!r}")
                elif _st == "consumed" and _want != "consumed":
                    errs.append(f"{_path}#{_rid} claims consumed but the file is {_want!r}")

if errs:
    print(f"FAIL — nahw skill incomplete ({len(errs)}):")
    for e in errs[:40]: print("  -", e)
    sys.exit(1)
_consumed = sum(1 for st, _c, _p in RULES_CONSUMPTION.values() if st == "consumed")
_fixture = sum(1 for st, _c, _p in RULES_CONSUMPTION.values() if st == "fixture_gated")
print("VALIDATE OK (PARTIAL) — nahw structural gates hold and %d/%d rules files are load-bearing in a "
      "production path (proven by %d on/off probes); %d are fixture-gated only. This is NOT completion: "
      "typed state/function and wrong-reason banks remain fixture-only "
      "(TP-NAHW-A2-TYPED-STATE-CONSUMER, TP-NAHW-A2-TYPED-WR-BANK)."
      % (_consumed, len(RULES_CONSUMPTION), len(LOAD_BEARING_PROBES), _fixture))

if __name__ == "__main__":
    pass
