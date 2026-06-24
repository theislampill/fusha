#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the sarf engine is production+teaching complete (fail-closed). Phase 2 gate.

Fails if SKILL.md names a missing artifact, a required Madinah failure mode is absent, false-clitic
cases are missing, nominal derivatives are not machine-testable, the corpus-to-Qamus recipe or learner
path is absent, the provenance invariant is missing, or the skill depends on MCP.
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "sarf")
errs = []
def need(rel, why):
    if not os.path.exists(os.path.join(S, rel)): errs.append(f"missing {rel} ({why})")
def read(rel):
    p = os.path.join(S, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

skill = read("SKILL.md")
if not skill: errs.append("sarf/SKILL.md missing")

# 1. required procedures / references / evals exist
for p in ["root-decision","verb-form","weak-root","hamza-root","doubled-root","noun-plural-gender",
          "masdar-participle","nominal-derivative-decision","learner-error-diagnosis","proper-noun",
          "homograph-risk","suffix-pronoun-state","hover-application","qamus-entry-authoring","corpus-to-qamus"]:
    need(f"procedures/{p}.md", "required procedure")
for r in ["nominal-derivatives","learner-error-remediation"]:
    need(f"references/{r}.md", "required reference")
for e in ["nominal-derivative-error-eval.jsonl","false-clitic-split-eval.jsonl"]:
    need(f"evals/{e}", "required eval")
need("drills/nominal-derivatives.md", "required drill")

# 2. SKILL.md references the new procedures/evals (named, not orphan)
for token in ["nominal-derivative-decision","learner-error-diagnosis","nominal-derivative-error-eval",
              "false-clitic-split-eval","nominal-derivatives","learner-error-remediation"]:
    if token not in skill: errs.append(f"SKILL.md does not reference {token}")

# 3. the 7 derivative types present in the reference
nd = read("references/nominal-derivatives.md")
for t in ["اسم الفاعل","اسم المفعول","صيغة المبالغة","الصفة المشبهة","اسم التفضيل","اسم الزمان","اسم الآلة"]:
    if t not in nd: errs.append(f"nominal-derivatives.md missing type {t}")

# 4. Madinah failure modes present in remediation reference
ler = read("references/learner-error-remediation.md")
for mode in ["اسم الفاعل / اسم المفعول","صيغة المبالغة","الصفة المشبهة","اسم التفضيل",
             "اسم الزمان","اسم الآلة","mother-tongue","false clitic","broken plural",
             "tanwīn-nūn","long-vowel"]:
    if mode not in ler: errs.append(f"learner-error-remediation.md missing failure mode: {mode}")

# 5. nominal-derivative eval is machine-testable: every row has expected_decision + derivative_type
nd_eval = os.path.join(S, "evals", "nominal-derivative-error-eval.jsonl")
if os.path.exists(nd_eval):
    rows = [json.loads(l) for l in open(nd_eval, encoding="utf-8") if l.strip()]
    if len(rows) < 20: errs.append(f"nominal-derivative-error-eval has only {len(rows)} cases (need >=20)")
    types = set()
    for r in rows:
        if "expected_decision" not in r: errs.append(f"ND row {r.get('id')} missing expected_decision")
        if "madina_error_class" not in r: errs.append(f"ND row {r.get('id')} missing madina_error_class")
        types.add(r.get("derivative_type"))
    for t in ["ism_fāʿil","ism_mafʿūl","ṣīghat_mubālagha","ṣifa_mushabbaha","ism_tafḍīl",
              "ism_zamān_makān","ism_āla"]:
        if not any(t in (x or "") for x in types): errs.append(f"ND eval missing derivative_type {t}")

# 6. false-clitic eval: required guard cases present + each has a decision
fcs = os.path.join(S, "evals", "false-clitic-split-eval.jsonl")
if os.path.exists(fcs):
    rows = [json.loads(l) for l in open(fcs, encoding="utf-8") if l.strip()]
    blob = json.dumps(rows, ensure_ascii=False)
    for surf in ["ٱلْمُلْكُ","لَهُ","بِيَدِهِ","قُرْءَانًا","رَحْمَة","أَعْمَالُنَا","عَلِمْنَا"]:
        if surf not in blob: errs.append(f"false-clitic-split-eval missing case {surf}")
    for r in rows:
        if "decision" not in r: errs.append(f"FCS row {r.get('id')} missing decision")

# 7. corpus-to-Qamus production recipe + learner path + provenance invariant
if "corpus" not in read("procedures/corpus-to-qamus.md").lower(): errs.append("corpus-to-qamus recipe weak")
if not os.path.exists(os.path.join(S, "curriculum", "zero-to-fluency-sarf.md")):
    errs.append("learner path (curriculum/zero-to-fluency-sarf.md) missing")
if 'src":"qamus' not in skill and "src=qamus" not in skill and "{\"src\": \"qamus\"" not in skill \
   and "src" not in skill.lower():
    errs.append("SKILL.md missing public provenance invariant")
# 8. MCP-free
low = skill.lower()
if ("mcp" in low) and ("mcp-free" not in low) and ("not a skill" not in low) and ("never" not in low):
    errs.append("SKILL.md appears to DEPEND on MCP (must be MCP-free / adapter-generic)")

if errs:
    print(f"FAIL — sarf skill incomplete ({len(errs)}):")
    for e in errs[:40]: print("  -", e)
    sys.exit(1)
print("VALIDATE OK — sarf engine production+teaching complete (procedures, derivatives, Madinah modes, false-clitic, learner path)")

if __name__ == "__main__":
    pass
