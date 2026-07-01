#!/usr/bin/env python3
"""Build largelexicon source inventory and committed sample artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import (
    LEXICON_DIR,
    MORPH_EXAMPLE_DIR,
    REPORT_DIR,
    entry_to_lemma,
    inventory,
    iter_entries,
    stem_rows_for_entry,
    write_json,
    write_jsonl,
)


def build(sample_size: int, out_dir: Path | None = None) -> dict:
    entries = iter_entries()
    lemmas = [entry_to_lemma(entry) for entry in entries]
    stems = [stem for entry in entries for stem in stem_rows_for_entry(entry)]
    sample_lemmas = lemmas[:sample_size]
    sample_forms = []
    for lemma in sample_lemmas:
        for form in lemma.get("forms", []):
            sample_forms.append(
                {
                    "schema": "fusha/largelexicon/form-source@1",
                    "entry_id": lemma["entry_id"],
                    "source_keys": lemma["source_keys"],
                    "surface": form,
                    "lemma": lemma["lemma"],
                    "root": lemma["root"],
                    "no_root_reason": lemma["no_root_reason"],
                    "pos": lemma["pos"],
                    "source_status": lemma["source_status"],
                    "public_boundary": lemma["public_boundary"],
                }
            )

    inv = inventory(entries)
    inv["sample_size"] = sample_size
    inv["sample_counts"] = {
        "lemma_source_rows": len(sample_lemmas),
        "form_source_rows": len(sample_forms),
        "stem_source_rows": min(len(stems), sample_size * 4),
    }
    inv["full_counts"] = {
        "lemma_source_rows": len(lemmas),
        "stem_source_rows": len(stems),
    }

    write_json(REPORT_DIR / "largelexicon-source-inventory.json", inv)
    write_jsonl(LEXICON_DIR / "lemma-source.sample.jsonl", sample_lemmas)
    write_jsonl(LEXICON_DIR / "form-source.sample.jsonl", sample_forms)
    write_jsonl(MORPH_EXAMPLE_DIR / "largelexicon-stems.sample.jsonl", stems[: sample_size * 4])

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(out_dir / "largelexicon-lemma-source.full.jsonl", lemmas)
        write_jsonl(out_dir / "largelexicon-stems.full.jsonl", stems)
        write_json(out_dir / "largelexicon-source-inventory.full.json", inv)

    return inv


def main() -> int:
    parser = argparse.ArgumentParser(description="Build largelexicon source inventory from Qamus data.")
    parser.add_argument("--sample-size", type=int, default=80)
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    result = build(args.sample_size, Path(args.out_dir) if args.out_dir else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
