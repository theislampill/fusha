"""Build the F-D handoff report from generated artifacts and the harness capture."""

from __future__ import annotations

import json
from pathlib import Path

# Moved-report banner: emitted by the generator so regeneration stays byte-identical.
HISTORICAL_BANNER = ("> **Historical lane report** (moved from the repo root 2026-08-05). Point-in-time evidence; tallies herein are superseded — current state lives in `docs/current-state.yaml` and the generated ledgers. Do not quote numbers from this file.\n\n")



ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> str:
    report = _json(ROOT / "qamus/reports/calibration-455/fd-455-report.json")
    payload = _json(ROOT / "qamus" / "examples" / "fd" / "sufaha-normalized-public-payload.json")
    parity = _json(ROOT / "qamus" / "examples" / "fd" / "sufaha-parity-fixture.json")
    render = _json(ROOT / "qamus" / "examples" / "fd" / "render-proof.json")
    harness = (ROOT / "qamus/reports/calibration-455/fd-check-regressions-output.txt").read_text(encoding="utf-8-sig").rstrip()

    checklist = [
        ("canonical identity", "payload.canonical_identity; quran 2:13:12, wbw:2:13:12, exact surface, lexical entry, card ID"),
        ("at-rest rich projection", "payload.at_rest_spans; [0,2] article, [2,11] lexical body, [11,12] case mark"),
        ("rich Ṣarf explanation", "payload.rich_explanations.sarf and the lexical-body component.sarf"),
        ("rich Naḥw explanation", "payload.rich_explanations.nahw and the case-ending component.nahw"),
        ("سَفِيه/سُفَهَاء comparison", "payload.comparison.singular and payload.comparison.plural"),
        ("root س ف ه", "payload.comparison.root and root fact binding"),
        ("فَعِيل", "payload.comparison.singular.pattern"),
        ("فُعَلَاء", "payload.comparison.plural.pattern"),
        ("retained radicals", "payload.comparison.retained_radicals = س, ف, ه"),
        ("removed ي", "payload.comparison.removed and paired_y_removal derivation chain"),
        ("introduced ا+ء", "payload.comparison.introduced and plural_introduced_letters fact"),
        ("lexical body vs final ُ", "at-rest spans and payload.comparison.plural.span_note"),
        ("ḍammah is nominative", "case-ending component.nahw: final ُ is nominative because it is the subject of آمَنَ"),
        ("exact governor relation", "governor_relation fact and the phrase subject of آمَنَ in the كما clause"),
        ("accessible non-colour equivalents", "[ART], [LEX], [CASE:NOM], [UNRESOLVED], labels, and status text"),
        ("Kawkab Mono Qamus proof", "render-proof.json font_check=true plus visible document.fonts.check assertion"),
        ("exact reconstruction", "parity.reconstructed_surface equals السُّفَهَاءُ and exact_reconstruction_passed=true"),
        ("repeated-appearance parity", "parity.same_payload_consumption and family members 2:13:12 / 2:282:40; no inferred page trace"),
        ("entry↔occurrence reciprocity", "parity.entry_reciprocity occurrence_to_entry=true and entry_to_occurrence=true"),
        ("provenance and projector IDs", "payload.provenance and generated HTML evidence footer"),
        ("jām id/mushtaq tension", "payload.unresolved_tension status=unresolved; attached without changing certified facts"),
        ("live mutation boundary", "payload, parity, report, verdicts, HTML, and render proof carry live_mutation_allowed=false"),
    ]

    lines = [
        "# FD-REPORT",
        "",
        "F-D compiler dry-run handoff for the pre-approved execution-order step 4 lane.",
        "",
        "## What was built",
        "",
        "- Extended `qamus.typed_claim_contract.v1` with the owner-mandated evidence modes, exact source evidence, derivation chains, dependencies, contradiction records, and unresolved tension records.",
        "- Added the registered `fd.shared_candidate_projection.v1` shared compiler in `tools/fd_compiler.py`.",
        "- Generated the contract, normalized payload, parity fixture, compact/expanded HTML card, local Kawkab font asset, real Playwright render proof, and screenshot under `qamus/examples/fd/`.",
        "- Compiled all 455 v575 `verified` rows in candidate mode into `fd-455-verdicts.jsonl` and `fd-455-report.json`.",
        "- Wired the contract/payload/render/matrix validator and unit fixtures into `tools/check_regressions.py`.",
        "",
        "The two HTML views consume one embedded normalized payload. The read-only corpus and live/runtime surfaces were not modified.",
        "",
        "## 22-point Ṣufahāʾ checklist",
        "",
        "| # | Owner point | Witness |",
        "|---:|---|---|",
    ]
    for index, (point, witness) in enumerate(checklist, 1):
        lines.append(f"| {index} | {point} | {witness} |")
    lines.extend([
        "",
        "## 455-row metrics",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ])
    for key, value in report["metrics"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "Rows may appear in multiple metric columns. Primary blocker assignment is recorded in `fd-455-verdicts.jsonl`; the report’s primary counts cover all 455 rows. `repeated page appearances covered` is zero because no page/render trace was available and no count was inferred from row or segment counts.",
        "",
        "## Verbatim harness output",
        "",
        "The following fenced block is the captured stdout/stderr of `python tools/check_regressions.py`, preserved verbatim in [fd-check-regressions-output.txt](fd-check-regressions-output.txt):",
        "",
        "```text",
        harness,
        "```",
        "",
        "## EXACT NONCLAIMS",
        "",
        "- No scholarly re-certification was performed.",
        "- No live effect occurred.",
        "- This is fixture/dry-run only; no corpus, whitelist, renderer runtime, deployment, publication, push, or live mutation was authorized or performed.",
        "",
        "## Render evidence",
        "",
        f"Playwright render proof: `font_check={render['font_check']}`, `exact_reconstruction={render['exact_reconstruction']}`, `compact_present={render['compact_present']}`, `expanded_present={render['expanded_present']}`, `same_payload_identity={render['same_payload_identity']}`, `live_mutation_allowed={render['live_mutation_allowed']}`.",
        "",
        "The generated screenshot is `qamus/examples/fd/sufaha-card.png`; no screenshot was fabricated.",
        "",
        "## Reproducibility boundary",
        "",
        "Regenerate with the command in `qamus/examples/fd/README.md`. The compiler reads the supplied lane inputs and read-only corpus, emits deterministic artifacts, and fails closed on contract, span, entry, parity, or render-proof drift.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    _output = ROOT / "docs" / "reports" / "history" / "2026-07-16-FD-REPORT.md"
    _output.write_text(HISTORICAL_BANNER + build_report(), encoding="utf-8", newline="\n")
    print(f"{_output.relative_to(ROOT)} generated")
