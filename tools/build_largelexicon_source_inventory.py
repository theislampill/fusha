#!/usr/bin/env python3
"""Build largelexicon source inventory and committed sample artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import (
    ALLOWLIST,
    FORM_FULL,
    FORM_SAMPLE,
    FULL_TABLE_META,
    LEMMA_FULL,
    LEMMA_SAMPLE,
    STEM_FULL,
    STEM_SAMPLE,
    REPORT_DIR,
    entry_to_lemma,
    form_rows_for_lemmas,
    full_table_allowlist,
    inventory,
    iter_entries,
    qword_denominator_rows,
    stem_rows_for_entry,
    write_json,
    write_jsonl,
    write_qword_denominator_shards,
)


def build(sample_size: int, out_dir: Path | None = None, commit_full: bool = False) -> dict:
    entries = iter_entries()
    lemmas = [entry_to_lemma(entry) for entry in entries]
    stems = [stem for entry in entries for stem in stem_rows_for_entry(entry)]
    sample_lemmas = lemmas[:sample_size]
    sample_forms = form_rows_for_lemmas(sample_lemmas)
    full_forms = form_rows_for_lemmas(lemmas)
    qword_rows = qword_denominator_rows(entries)

    inv = inventory(entries)
    inv["sample_size"] = sample_size
    inv["sample_counts"] = {
        "lemma_source_rows": len(sample_lemmas),
        "form_source_rows": len(sample_forms),
        "stem_source_rows": min(len(stems), sample_size * 4),
    }
    inv["full_counts"] = {
        "lemma_source_rows": len(lemmas),
        "form_source_rows": len(full_forms),
        "stem_source_rows": len(stems),
        "qword_denominator_rows": len(qword_rows),
    }
    inv["commit_full_requested"] = commit_full
    inv["source_clean_table_allowlist"] = str(ALLOWLIST.relative_to(Path(__file__).resolve().parents[1]))

    write_json(REPORT_DIR / "largelexicon-source-inventory.json", inv)
    write_jsonl(LEMMA_SAMPLE, sample_lemmas)
    write_jsonl(FORM_SAMPLE, sample_forms)
    write_jsonl(STEM_SAMPLE, stems[: sample_size * 4])

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(out_dir / "largelexicon-lemma-source.full.jsonl", lemmas)
        write_jsonl(out_dir / "largelexicon-form-source.full.jsonl", full_forms)
        write_jsonl(out_dir / "largelexicon-stems.full.jsonl", stems)
        write_jsonl(out_dir / "largelexicon-qword-denominator.full.jsonl", qword_rows)
        write_json(out_dir / "largelexicon-source-inventory.full.json", inv)
    if commit_full:
        allowlist = full_table_allowlist()
        write_json(ALLOWLIST, allowlist)
        write_jsonl(LEMMA_FULL, lemmas)
        write_jsonl(FORM_FULL, full_forms)
        write_jsonl(STEM_FULL, stems)
        qword_manifest = write_qword_denominator_shards(qword_rows, all_entries=entries)
        from build_largelexicon_qword_crosswalk import build as build_qword_crosswalk

        qword_crosswalk_manifest = build_qword_crosswalk()
        write_json(
            FULL_TABLE_META,
            {
                "schema": "fusha/largelexicon/source-clean-fact-tables-meta@1",
                **{key: inv[key] for key in ["generated_at", "generated_by", "source_head", "source_branch", "supersedes", "stale_after", "status"]},
                "allowlist": str(ALLOWLIST.relative_to(Path(__file__).resolve().parents[1])),
                "tables": allowlist["tables"],
                "counts": inv["full_counts"],
                "qword_denominator_manifest": qword_manifest,
                "qword_crosswalk_manifest": qword_crosswalk_manifest,
                "claim": "committed Qamus-authored source-clean facts; no raw external payloads; no live Qamus progress",
                "public_boundary": inv["public_boundary"],
                "freshness": {key: inv[key] for key in ["generated_at", "generated_by", "source_head", "source_branch", "supersedes", "stale_after", "status"]},
            },
        )

    return inv


def main() -> int:
    parser = argparse.ArgumentParser(description="Build largelexicon source inventory from Qamus data.")
    parser.add_argument("--sample-size", type=int, default=80)
    parser.add_argument("--out-dir")
    parser.add_argument("--commit-full", action="store_true", help="Write allowlisted source-clean full fact tables into git paths.")
    args = parser.parse_args()
    result = build(args.sample_size, Path(args.out_dir) if args.out_dir else None, args.commit_full)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
