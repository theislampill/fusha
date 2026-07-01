#!/usr/bin/env python3
"""Build a source-clean largelexicon Qamus Mode A support worklist sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from largelexicon_common import PUBLIC_BOUNDARY, iter_entries, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "qamus" / "examples" / "mode_a_all_qword" / "largelexicon-qamus-mode-a-worklist.sample.jsonl"


def build(limit: int, out: Path) -> dict:
    rows = []
    for entry in iter_entries():
        for usage_index, usage in enumerate(entry.get("usage") or [], start=1):
            for example_index, example in enumerate(usage.get("examples") or [], start=1):
                words = [word for word in (example.get("ar") or "").split() if word]
                for qword_index, surface in enumerate(words, start=1):
                    rows.append(
                        {
                            "schema": "qamus/largelexicon-mode-a-worklist-row@1",
                            "row_id": f"llx-{entry['id']}-{usage_index:02d}-{example_index:02d}-{qword_index:03d}",
                            "entry_id": entry["id"],
                            "source_keys": entry.get("source_keys") or [],
                            "card_id": f"{entry['id']}:u{usage_index}:e{example_index}",
                            "qword_index": qword_index,
                            "visible_surface": surface,
                            "card_text": example.get("ar"),
                            "quran_ref": example.get("ref"),
                            "canonical_quran_loc": None,
                            "canonical_wbw_loc": None,
                            "status": "needs_source_address_crosswalk",
                            "route": "qamus_executor_source_crosswalk",
                            "public_boundary": dict(PUBLIC_BOUNDARY),
                            "live_mutation_allowed": False,
                        }
                    )
                    if len(rows) >= limit:
                        write_jsonl(out, rows)
                        return {"rows": len(rows), "out": str(out.relative_to(ROOT))}
    write_jsonl(out, rows)
    return {"rows": len(rows), "out": str(out.relative_to(ROOT))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build largelexicon Qamus Mode A worklist sample.")
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    result = build(args.limit, Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
