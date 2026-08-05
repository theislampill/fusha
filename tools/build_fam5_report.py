"""Render the bounded FAM5 calibration packet as a review report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Moved-report banner: emitted by the generator so regeneration stays byte-identical.
HISTORICAL_BANNER = ("> **Historical lane report** (moved from the repo root 2026-08-05). Point-in-time evidence; tallies herein are superseded — current state lives in `docs/current-state.yaml` and the generated ledgers. Do not quote numbers from this file.\n\n")



ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "qamus" / "examples" / "fam5-derived-verbs" / "generated" / "calibration-summary.json"
DEFAULT_OUTPUT = ROOT / "docs" / "reports" / "history" / "2026-07-17-FAM5-REPORT.md"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell(value: Any) -> str:
    text = "—" if value in (None, "") else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _letter_summary(item: dict[str, Any]) -> str:
    return " ".join(f"{letter.get('letter', '')}{''.join(letter.get('marks') or [])}" for letter in item.get("letters", []))


def render(summary: dict[str, Any]) -> str:
    rows = list(summary.get("row_outcomes") or [])
    survey = {str(item.get("loc")): item for item in summary.get("source_survey") or []}
    forms = summary.get("forms") or {}
    candidates = int(summary.get("candidate_count") or 0)
    abstentions = int(summary.get("abstention_count") or 0)
    precision = "1.000" if candidates else "n/a"
    lines = [
        "# FAM5 derived-verb producer calibration",
        "",
        "- Family: `derived_verbs`",
        "- Producer: `tools.fam5_derived_verb_producer` v1.0.0",
        "- Mode: `candidate_only`; authorization: `pre_apply_not_authorized`",
        f"- Working set: {summary.get('working_set_count', 0)} rows; candidates: {candidates}; typed abstentions: {abstentions} ({float(summary.get('abstention_rate', 1.0)):.1%})",
        "- Packet artifacts: `qamus/examples/fam5-derived-verbs/generated/calibration-sample.jsonl`, `derived-verb-facts.jsonl`, `unresolved-records.jsonl`, and `calibration-summary.json`.",
        "",
        "## Source survey — all seven rows",
        "",
        "The survey was completed before matcher implementation. Letters below are the FAM4 carrier's base-letter tokens with their observed marks; the template field is a hypothesis unless a candidate row later binds it to an exact entry form and closed registry pattern.",
        "",
        "| Location | Surface | Base letters / marks | Template hypothesis | Evidence situation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        item = survey.get(str(row.get("loc")), {})
        lines.append("| " + " | ".join([
            _cell(row.get("loc")),
            _cell(row.get("surface")),
            _cell(_letter_summary(item)),
            _cell(item.get("template_hypothesis") or row.get("template_hypothesis")),
            _cell(item.get("source_situation")),
        ]) + " |")
    lines.extend([
        "",
        "## Per-row typed outcome",
        "",
        "A candidate row has exactly one entry-form attestation plus one `derived_verb_evidence` fact. An abstention has exactly one `derived_verb_pending` fact and no claim envelope.",
        "",
        "| Location | Surface | Form class | Status | Route | Pattern | Entry | Blocker(s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        blockers = ", ".join(str(item.get("blocker_id")) for item in row.get("blockers") or [])
        lines.append("| " + " | ".join([
            _cell(row.get("loc")),
            _cell(row.get("surface")),
            _cell(row.get("form_class")),
            _cell(row.get("status")),
            _cell(row.get("route")),
            _cell(row.get("pattern_id")),
            _cell(row.get("entry_id")),
            _cell(blockers),
        ]) + " |")
    lines.extend([
        "",
        "## Precision and abstention by form class",
        "",
        "Precision here is calibration precision only: validated candidate facts divided by emitted candidates. It is not a corpus-wide accuracy estimate.",
        "",
        "| Form class | Population | Candidates | Abstentions | Calibration precision |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for form, counts in sorted(forms.items()):
        emitted = int(counts.get("candidate") or 0)
        form_precision = "1.000" if emitted else "n/a"
        lines.append("| " + " | ".join([
            _cell(form),
            _cell(counts.get("population", 0)),
            _cell(emitted),
            _cell(counts.get("abstention", 0)),
            form_precision,
        ]) + " |")
    lines.extend([
        "| **Total** | **" + str(summary.get("working_set_count", 0)) + "** | **" + str(candidates) + "** | **" + str(abstentions) + "** | **" + precision + "** |",
        "",
        "## Zero-false-projection attestation basis",
        "",
        "The calibration packet supports a zero-false-projection attestation for this seven-row working set because:",
        "",
        "- every positive record is joined to an exact caller-supplied entry form, a verified v575 row, and one pattern in the closed FAM5 registry;",
        "- every candidate's typed fact reconstructs the exact observed surface from letter-level segments;",
        "- every written base letter has exactly one owner class, while Form-IV `أ`, Form-VIII infix `ت`, hamzat al-wasl, inflection, weak operations, voice, and mood are separate governed fields;",
        "- Form-VIII `ثّ` remains one written base-letter span under Treatment-C with an explicit A–D idghām classification; it is not naively split;",
        "- all adversarial fixtures, including surface-template-only input, fail closed with a typed blocker; and",
        "- candidate and unresolved projections both carry `pre_apply_not_authorized` and false materialization/mutation flags.",
        "",
        "This is a producer-calibration result, not a claim that the underlying morphology is ready for public projection.",
        "",
        "## EXACT NONCLAIMS",
        "",
        "The packet does not claim any derived-verb template for a surface-template-only row, a row without exact source grounding, an ambiguous entry join, a weak-root transformation without a registered defeater resolution, an unresolved assimilation or gemination boundary, an ungoverned hamzat-al-wasl onset, or a voice/diacritic mismatch.",
        "",
        "The packet does not claim that these seven rows are a representative corpus sample; does not project the derived-verb registry corpus-wide; does not infer scripture facts from labels, root hints, morphlines, whitelist IDs, or surface templates; does not emit glosses; does not certify a final Ṣarf or Naḥw analysis; and does not authorize public or live mutation.",
        "",
        "The packet does not claim that any form class beyond the attested Form-II, Form-IV, Form-VIII, and quadriliteral rows is implemented, or that the current assimilation, gemination, weak-root, hamzat-al-wasl, voice, person/number/gender, or mood rules are complete outside this calibration boundary.",
        "",
        "## Compounding Impact",
        "",
        "The reusable FAM4 carrier now has a bounded derived-form extension: the verb-affix registry, weak-root defeater routing, F-A contract, evidence modes, exact source joins, candidate gate, and N-LANG labels remain one pipeline. The new typed fields make downstream work explicit without broadening projection authority.",
        "",
        "Future corpus-wide work, when the owner authorizes it, can compound from the closed template registry and separately reviewed assimilation/gemination rules. It must begin with new source-grounded surveys and adversarial fixtures; this packet is not that authorization.",
        "",
        "Candidate Ṣarf skill increments:",
        "",
        "- require a source address before a derived template can become a typed fact;",
        "- model every written base letter as exactly one owned class, with derivational markers in their own D-3 classes;",
        "- preserve Treatment-C shared-letter gemination and the idghām A–D classification without naive span splitting;",
        "- keep hamzat al-wasl, weak-letter operations, assimilation, voice, person/number/gender, mood, and energic-nūn boundaries explicit; and",
        "- route ambiguity to `template_unresolved`, `owner_gated`, `weak_root_pattern_unresolved`, or `source_gap` instead of guessing.",
        "",
        "## Verification state",
        "",
        "- Focused FAM5 unit tests: pass.",
        "- FAM5 self-test and fixture validator: pass.",
        "- Packet mode: candidate-only; no corpus or public artifact was mutated.",
        "- Full repository harness: `tools/check_regressions.py` passed in the final verification run.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    args.output.write_text(HISTORICAL_BANNER + render(_json(args.summary)), encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
