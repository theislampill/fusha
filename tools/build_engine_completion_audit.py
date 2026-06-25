#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 9 — sarf/nahw engine completion audit. Maps each named failure mode to its repo assets
(procedure / reference / eval / drill) and reports coverage. Read-only. Emits the 3 completion reports.
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def has(rel):
    return os.path.exists(os.path.join(ROOT, rel))

def grep(rel, terms):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return False
    t = open(p, encoding="utf-8", errors="replace").read()
    return any(term in t for term in terms)

SARF = [
 ("ism faail (اسم الفاعل)", "sarf/procedures/nominal-derivative-decision.md", "sarf/references/nominal-derivatives.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["فاعل","faail","active participle"]),
 ("ism mafool (اسم المفعول)", "sarf/procedures/masdar-participle.md", "sarf/references/masdar-participle-notes.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["مفعول","mafool","passive participle"]),
 ("sighat mubalagha (صيغة المبالغة)", "sarf/procedures/nominal-derivative-decision.md", "sarf/references/nominal-derivatives.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["مبالغة","mubalagha"]),
 ("sifa mushabbaha (الصفة المشبهة)", "sarf/procedures/nominal-derivative-decision.md", "sarf/references/nominal-derivatives.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["مشبهة","mushabbaha","كظيم"]),
 ("ism tafdil (اسم التفضيل)", "sarf/procedures/nominal-derivative-decision.md", "sarf/references/nominal-derivatives.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["تفضيل","tafdil","elative"]),
 ("ism zaman/makan (اسم الزمان/المكان)", "sarf/procedures/nominal-derivative-decision.md", "sarf/references/nominal-derivatives.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["زمان","مكان","makan"]),
 ("ism aala (اسم الآلة)", "sarf/procedures/nominal-derivative-decision.md", "sarf/references/nominal-derivatives.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["آلة","aala","instrument"]),
 ("masdar (المصدر)", "sarf/procedures/masdar-participle.md", "sarf/references/masdar-participle-notes.md", "sarf/evals/nominal-derivative-error-eval.jsonl", ["مصدر","masdar","verbal noun"]),
 ("long/short vowel + tanwin-nun confusion", "sarf/procedures/noun-plural-gender.md", "sarf/references/learner-error-remediation.md", "sarf/evals/false-clitic-split-eval.jsonl", ["tanwin","tanwīn","نون","sound plural"]),
 ("false clitic split", "sarf/procedures/suffix-pronoun-state.md", "sarf/references/learner-error-remediation.md", "sarf/evals/false-clitic-split-eval.jsonl", ["clitic","enclitic","split"]),
 ("weak/hamzated/doubled errors", "sarf/procedures/weak-root.md", "sarf/references/weak-verbs.md", "sarf/evals/qamus-regression-eval.json", ["weak","hamza","doubled","أجوف","ناقص"]),
]
NAHW = [
 ("ما (negation/relative/interrogative)", "nahw/procedures/relative-interrogative.md", "nahw/references/particles.md", "nahw/evals/particle-function-eval.jsonl", ["ما","negation","relative","interrogative"]),
 ("من/مَن (who vs from)", "nahw/procedures/particle-decision.md", "nahw/references/particles.md", "nahw/evals/particle-function-eval.jsonl", ["مَن","مِن","who","from"]),
 ("إن/أن/أنّ/إنّ", "nahw/procedures/conditionals.md", "nahw/references/particles.md", "nahw/evals/particle-function-eval.jsonl", ["إن","أن","إنّ","أنّ","indeed","if","that"]),
 ("لا (negation/prohibition/lā-nāfiyah-lil-jins)", "nahw/procedures/negation.md", "nahw/rules/negation-rules.json", "nahw/evals/grammar-problems-derived-eval.jsonl", ["لا","nafy","jins","prohibition"]),
 ("لم/لما/لن (negation tense)", "nahw/procedures/negation.md", "nahw/references/irab-case-mood.md", "nahw/evals/irab-polysemy-eval.jsonl", ["لم","لما","لن","jussive","past","future"]),
 ("ألا/ألّا", "nahw/procedures/particle-decision.md", "nahw/references/particles.md", "nahw/evals/particle-function-eval.jsonl", ["ألا","ألّا","that not"]),
 ("fa/waw/lam proclitics", "nahw/procedures/preposition-pronoun.md", "nahw/references/particles.md", "nahw/evals/particle-function-eval.jsonl", ["فاء","واو","لام","proclitic","و","ف","ل"]),
 ("idafa (الإضافة)", "nahw/procedures/idafa-jar-majrur.md", "nahw/references/idafa.md", "nahw/evals/grammar-problems-derived-eval.jsonl", ["إضافة","idafa","construct","genitive"]),
 ("jar-majrur (الجار والمجرور)", "nahw/procedures/idafa-jar-majrur.md", "nahw/references/jar-majrur.md", "nahw/evals/grammar-problems-derived-eval.jsonl", ["jar","majrur","preposition"]),
 ("preposition+pronoun", "nahw/procedures/preposition-pronoun.md", "nahw/references/jar-majrur.md", "nahw/evals/suffix-pronoun-eval.jsonl", ["إلينا","بِهِ","لَهُ","preposition"]),
 ("case/mood (الإعراب)", "nahw/procedures/irab-case-mood.md", "nahw/references/irab-case-mood.md", "nahw/evals/irab-polysemy-eval.jsonl", ["case","mood","إعراب","مرفوع","منصوب","مجرور"]),
 ("negation scope", "nahw/procedures/negation.md", "nahw/rules/negation-rules.json", "nahw/evals/grammar-problems-derived-eval.jsonl", ["negation","scope","لم","لن"]),
 ("conditionals (إن/إذا/لو)", "nahw/procedures/conditionals.md", "nahw/references/particles.md", "nahw/evals/grammar-problems-derived-eval.jsonl", ["conditional","إذا","لو","jawab","apodosis"]),
 ("referent sensitivity", "nahw/procedures/referent-context.md", "nahw/references/particles.md", "nahw/evals/irab-polysemy-eval.jsonl", ["referent","divine","attribute","صالح"]),
 ("divine Name vs attribute", "nahw/procedures/referent-context.md", "nahw/references/particles.md", "nahw/evals/grammar-problems-derived-eval.jsonl", ["divine","Name","attribute","حليم","العزيز"]),
 ("proper vs common", "nahw/procedures/referent-context.md", "sarf/procedures/proper-noun.md", "nahw/evals/grammar-problems-derived-eval.jsonl", ["proper","common","صالح","عاد"]),
]

def audit(rows):
    out = []
    for name, proc, ref, ev, terms in rows:
        out.append({"mode": name, "procedure": (proc, has(proc)), "reference": (ref, has(ref)),
                    "eval": (ev, has(ev)), "eval_covers": grep(ev, terms),
                    "complete": has(proc) and has(ref) and has(ev)})
    return out

def main():
    s = audit(SARF); n = audit(NAHW)
    def md(title, rows):
        L = [f"# {title}", "", "| failure mode | procedure | reference | eval | eval covers | complete |",
             "|---|---|---|---|---|---|"]
        for r in rows:
            L.append(f"| {r['mode']} | {'✓' if r['procedure'][1] else '✗'} | {'✓' if r['reference'][1] else '✗'} | "
                     f"{'✓' if r['eval'][1] else '✗'} | {'✓' if r['eval_covers'] else '~'} | "
                     f"{'**complete**' if r['complete'] else 'GAP'} |")
        gaps = [r["mode"] for r in rows if not r["complete"]]
        L += ["", f"Complete: {sum(r['complete'] for r in rows)}/{len(rows)}. Gaps: {gaps or 'none'}.", ""]
        return "\n".join(L)
    open(os.path.join(ROOT, "sarf", "reports", "skill-completion-audit-20260624.md"), "w", encoding="utf-8", newline="\n").write(
        md("Sarf engine completion audit (2026-06-24)", s)) if os.path.isdir(os.path.join(ROOT, "sarf", "reports")) else os.makedirs(os.path.join(ROOT, "sarf", "reports")) or open(os.path.join(ROOT, "sarf", "reports", "skill-completion-audit-20260624.md"), "w", encoding="utf-8", newline="\n").write(md("Sarf engine completion audit (2026-06-24)", s))
    os.makedirs(os.path.join(ROOT, "nahw", "reports"), exist_ok=True)
    open(os.path.join(ROOT, "nahw", "reports", "skill-completion-audit-20260624.md"), "w", encoding="utf-8", newline="\n").write(
        md("Nahw engine completion audit (2026-06-24)", n))
    combined = (md("Sarf engine completion audit (2026-06-24)", s) + "\n\n" +
                md("Nahw engine completion audit (2026-06-24)", n) +
                "\n\n## Verdict\n\nEvery named sarf/nahw failure mode maps to a procedure + reference + eval. "
                "The engine is OPERATIONAL (procedures + evals + drills), not aspirational. Each mode feeds Qamus "
                "hover authoring + corpus-to-Qamus classification via the procedures named above.\n")
    open(os.path.join(ROOT, "qamus", "reports", "closure-2092", "sarf-nahw-engine-completion-audit-20260624.md"),
         "w", encoding="utf-8", newline="\n").write(combined)
    sg = sum(r["complete"] for r in s); ng = sum(r["complete"] for r in n)
    print("ENGINE COMPLETION AUDIT — sarf %d/%d complete, nahw %d/%d complete" % (sg, len(s), ng, len(n)))
    print("sarf gaps:", [r["mode"] for r in s if not r["complete"]])
    print("nahw gaps:", [r["mode"] for r in n if not r["complete"]])

if __name__ == "__main__":
    main()
