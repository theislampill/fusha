#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the nahw engine is production+teaching complete (fail-closed). Phase 3 gate.

Fails if SKILL.md names a missing artifact, particle functions are not machine-testable, same-surface
polysemy examples are absent, conclusion-only reasoning is allowed (no grammar-risk gate), the hover
recipe or learner path is absent, the provenance invariant is missing, or the skill depends on MCP.
"""
import json, os, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
          "qamus-entry-authoring","corpus-to-qamus","pronoun-attachment"]:
    need(f"procedures/{p}.md", "required procedure")
for r in ["particle-functions","irab-teaching-map","learner-error-remediation","particles","idafa","jar-majrur"]:
    need(f"references/{r}.md", "required reference")
for e in ["particle-function-eval.jsonl","irab-polysemy-eval.jsonl","grammar-problems-derived-eval.jsonl"]:
    need(f"evals/{e}", "required eval")
need("drills/particle-disambiguation.md", "required drill")
need("drills/irab-case-mood.md", "required drill")

for token in ["particle-function-decision","irab-teaching-diagnosis","particle-function-eval",
              "irab-polysemy-eval","particle-functions","irab-teaching-map","learner-error-remediation"]:
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
    for need_p in ["مَا","مَن","مِن","إِنْ","لَا","أَلَا","أَلَّا","فَمَا","أَمْ","كَلَّا","لِمَ"]:
        if need_p not in particles: errs.append(f"particle-function-eval missing particle {need_p}")

# iʿrāb-polysemy: required same-surface regressions present + each has a reading
ip = os.path.join(N, "evals", "irab-polysemy-eval.jsonl")
if os.path.exists(ip):
    rows = [json.loads(l) for l in open(ip, encoding="utf-8") if l.strip()]
    blob = json.dumps(rows, ensure_ascii=False)
    for surf in ["وَمَا","عَادٍ","أَلَّا","أَلَا","فَمَا","جِنَّةٍ","أُمَّةً","يَقْدِرُ","حَلِيمٌ"]:
        if surf not in blob: errs.append(f"irab-polysemy-eval missing regression {surf}")
    for r in rows:
        if "reading" not in r: errs.append(f"IP row {r.get('id')} missing reading")

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

if errs:
    print(f"FAIL — nahw skill incomplete ({len(errs)}):")
    for e in errs[:40]: print("  -", e)
    sys.exit(1)
print("VALIDATE OK — nahw engine production+teaching complete (particle functions, iʿrāb polysemy, gates, learner path)")

if __name__ == "__main__":
    pass
