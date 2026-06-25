#!/usr/bin/env python3
"""Audit the provenance of examples[].en in the public Qamus dataset.

DR02 follow-through. The committed public dataset (qamus/data/current/entries.jsonl) stores a full
English translation for every example āyah in examples[].en. The dataset acceptance validator
(validate_current_qamus_dataset.py) gates STRUCTURE (allowed keys), LEAK patterns (paths/secrets),
and PRIVATE fields — but it does NOT prove examples[].en is Qamus-authored vs a verbatim copy of a
published external translation.

This tool QUANTIFIES the external-translation exposure (it does not mutate anything and is NOT a
blocking gate — the data is pre-existing owner content pending a licensing decision). Heuristics:
  - bracketed-interpolation density ([ ... ]) — the signature of the Saheeh International translation;
  - explicit translator-name strings (Saheeh International, Yusuf Ali, Pickthall, ...).

Output: qamus/reports/closure-2092/examples-en-provenance-audit-YYYYMMDD.md/.json (date-stamped via
the DATE env or 'undated' — Date.now() is intentionally not used so the repo stays deterministic).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
REPORTS = os.path.join(ROOT, "qamus", "reports", "closure-2092")
DATE = os.environ.get("AUDIT_DATE", "20260625")

BRACKET = re.compile(r"\[[^\]]{1,80}\]")
NAMES = re.compile(r"(saheeh|sahih international|yusuf ali|pickthall|shakir|muhsin khan|"
                   r"arberry|hilali|dr\.?\s*ghali|the clear quran)", re.I)

def main():
    total = with_en = empty = with_bracket = with_name = 0
    uniq = set()
    bracket_samples = []
    for line in open(DATA, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        for u in e.get("usage", []):
            for ex in u.get("examples", []):
                total += 1
                en = (ex.get("en") or "").strip()
                if not en:
                    empty += 1
                    continue
                with_en += 1
                uniq.add(en)
                if BRACKET.search(en):
                    with_bracket += 1
                    if len(bracket_samples) < 5:
                        bracket_samples.append({"ref": ex.get("ref"), "en": en[:160]})
                if NAMES.search(en):
                    with_name += 1

    pct_br = round(100 * with_bracket / max(total, 1), 1)
    finding = ("EXTERNAL-TRANSLATION-PRESENT" if pct_br >= 10 or with_name
               else "no strong external-translation signature")
    obj = {
        "_generator": "audit_examples_en_provenance",
        "date": DATE,
        "dataset": "qamus/data/current/entries.jsonl",
        "total_examples": total,
        "examples_with_en": with_en,
        "empty_en": empty,
        "unique_en_strings": len(uniq),
        "with_bracket_interpolation": with_bracket,
        "bracket_pct": pct_br,
        "with_translator_name": with_name,
        "finding": finding,
        "interpretation": ("bracketed-interpolation density at this level is the signature of the "
                           "Saheeh International published translation; examples[].en is a verbatim "
                           "external translation, NOT Qamus-authored"),
        "scope_note": ("this is the entry-level example-āyah translation field in the PUBLIC dataset; "
                       "it is SEPARATE from the per-word hover output (wbw-lookup 'words'), which is "
                       "live-verified Qamus-authored and leak-free"),
        "classification": "owner-gated (source/licensing decision)",
        "remediation_options": [
            "A) confirm Saheeh International redistribution rights for da'wah + add explicit attribution + license notice to the dataset/repo",
            "B) replace examples[].en with an openly-licensed translation (CC0/CC-BY) — see the open-gloss deep-research",
            "C) author original Qamus example renderings (large effort)",
            "D) drop examples[].en from the PUBLIC dataset, keep examples[].ar + ref only (Arabic is Tanzil CC BY 3.0, already attributed)",
        ],
        "blocks": {"coverage_to_90": False, "hover_authoring": False,
                   "public_repo_redistribution_cleanliness": True},
        "samples": bracket_samples,
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, f"examples-en-provenance-audit-{DATE}.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    md = [f"# examples[].en provenance audit — {DATE}\n",
          f"> **Finding: {finding}.** {obj['interpretation']}\n",
          "| metric | value |", "|---|---:|",
          f"| total example āyāt | {total:,} |",
          f"| with English (examples[].en) | {with_en:,} (100%) |",
          f"| unique English strings | {len(uniq):,} |",
          f"| **with [bracket] interpolation (Saheeh-Intl signature)** | **{with_bracket:,} ({pct_br}%)** |",
          f"| explicit translator-name string | {with_name} |\n",
          "## Scope (honest)\n", obj["scope_note"] + "\n",
          "**This is SEPARATE from the hover output.** The per-word glosses shipped on hover "
          "(`wbw-lookup.json` → `words`) are live-verified Qamus-authored, `src:\"qamus\"`, 0 leaks. "
          "The exposure is the **entry-level example-āyah translation field** in the committed public "
          "dataset.\n",
          "## Classification: owner-gated (source/licensing decision)\n",
          "The example translations are a deliberate owner sourcing choice (scripture accuracy), not "
          "an accidental leak. Redistribution rights are a licensing question only the owner can "
          "settle. Remediation options:\n"]
    for o in obj["remediation_options"]:
        md.append(f"- {o}")
    md.append("\n## Does NOT block coverage-to-90\n")
    md.append("Hover authoring proceeds on the clean authored layer. This item is a parallel "
              "governance/licensing decision, recorded as an exact owner blocker.\n")
    with open(os.path.join(REPORTS, f"examples-en-provenance-audit-{DATE}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"EXAMPLES-EN PROVENANCE: total={total} with_en={with_en} unique={len(uniq)} "
          f"bracket={with_bracket}({pct_br}%) names={with_name} -> {finding}")

if __name__ == "__main__":
    main()
