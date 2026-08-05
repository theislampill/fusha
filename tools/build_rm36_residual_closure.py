#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
# Moved from qamus/reports/rm36-residual-closure/ to tools/ on 2026-08-05: code does
# not live in the evidence tree. The emitted artifacts stay in the report directory.
REPO_ROOT = HERE.parent
REPORT_DIR = REPO_ROOT / "qamus/reports/rm36-residual-closure"
TOOLS = REPO_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from normalize_ar import norm_strict  # noqa: E402
from validate_largelexicon_denominator_join import _join_surface_key  # noqa: E402


FAILING_PATH = REPO_ROOT / "qamus/reports/rm36-fallback-reverification/failing-rows.jsonl"
DEMOTION_PATH = REPO_ROOT / "qamus/reports/rm36-fallback-reverification/demotion-wave.report.json"
PRIOR_REPORT_PATH = REPO_ROOT / "qamus/reports/rm36-fallback-reverification/residual-reclassification.report.json"
INDEX_PATH = REPO_ROOT / "qamus/indexes/quran-loc-surface/index.jsonl"
INDEX_MANIFEST_PATH = REPO_ROOT / "qamus/indexes/quran-loc-surface/index.manifest.json"
CROSSWALK_DIR = REPO_ROOT / "qamus/indexes/largelexicon/qword-crosswalk"
REPORT_PATH = REPORT_DIR / "rm36-residual-closure.report.json"
RESIDUAL_PATH = REPORT_DIR / "residual-closure.jsonl"
MANIFEST_PATH = REPORT_DIR / "rm36-residual-closure.manifest.json"
# The proposed check_regressions hunk and the dir-local .gitattributes that kept its
# bytes unnormalized were dropped on 2026-08-05: the hunk was never applied and the
# report directory now holds evidence only.

SCHEMA_ROW = "fusha/rm36-residual-closure-row@1"
SCHEMA_REPORT = "fusha/rm36-residual-closure-report@1"
SCHEMA_MANIFEST = "fusha/rm36-residual-closure-manifest@1"
GENERATOR = "tools/build_rm36_residual_closure.py"
BASELINE_HEAD = "949b3212034dfc361352aa280c0c8ddbe3560417"
PR53_MERGE_COMMIT = "cce73d4"
PR53_DATA_COMMIT = "d70efb2f13df26acc6ecf77f9826d1a3e4975643"
PR53_QWORD_ROW_IDS = {
    "llx-qword-1c5f7c9c8e05-03-12-001",
    "llx-qword-1c5f7c9c8e05-03-12-002",
}
PR53_CROSSWALK_ROW_IDS = {f"llx-crosswalk-{row_id}" for row_id in PR53_QWORD_ROW_IDS}
FRAGMENT_ARTIFACT_REFS = {"2:214", "2:274", "3:152", "12:37", "48:15"}
SURFACE_DRIFT_REFS = {"92:3", "93:3"}
WBW_SLICE_ARTIFACT_REFS = {"7:98", "70:24", "98:1", "114:2"}
TERMINAL_ORDER = {
    "closed_verified": 0,
    "closed_by_correction": 1,
    "demoted": 2,
    "exception": 3,
}


def complete_terminal_counts(counts: Counter[str]) -> dict[str, int]:
    return {terminal_class: counts.get(terminal_class, 0) for terminal_class in sorted(TERMINAL_ORDER)}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return (
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    ).encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def index_rows(
    rows: Iterable[dict[str, str]],
) -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
    by_loc: dict[str, str] = {}
    by_ayah: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        loc = row["loc"]
        if loc in by_loc:
            raise ValueError(f"duplicate full-index loc: {loc}")
        by_loc[loc] = row["surface"]
        by_ayah[ayah_from_loc(loc)].append(row)
    for ayah_rows in by_ayah.values():
        ayah_rows.sort(key=lambda item: loc_sort_key(item["loc"]))
    return by_loc, dict(by_ayah)


def ayah_from_loc(loc: str) -> str:
    return ":".join(loc.split(":")[:2])


def loc_sort_key(loc: str) -> tuple[int, ...]:
    return tuple(int(part) for part in loc.split(":"))


def base_letters(surface: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", surface)
        if not unicodedata.combining(char) and not ("\u06d6" <= char <= "\u06ed")
    )


def replace_chars(value: str, replacements: dict[str, str]) -> str:
    return "".join(replacements.get(char, char) for char in value)


def surface_delta(visible: str, indexed: str | None) -> str:
    if indexed is None:
        return "indexed_location_absent"
    visible_base = base_letters(visible)
    indexed_base = base_letters(indexed)
    if visible_base == indexed_base:
        return "combining_marks_only"
    if replace_chars(visible_base, {"ة": "ه"}) == replace_chars(indexed_base, {"ة": "ه"}):
        return "taa_marbuta_haa_rasm_variant"
    if replace_chars(visible_base, {"ى": "ي"}) == replace_chars(indexed_base, {"ى": "ي"}):
        return "alif_maqsura_yaa_rasm_variant"
    if replace_chars(visible_base, {"ٱ": "ا"}) == replace_chars(indexed_base, {"ٱ": "ا"}):
        return "wasla_alif_rasm_variant"
    if norm_strict(visible) == norm_strict(indexed):
        return "uthmani_dagger_alif_or_equivalent_rasm"
    return "consonantal_or_suffix_difference"


def exact_matches(
    row: dict[str, Any],
    index_by_loc: dict[str, str],
    index_by_ayah: dict[str, list[dict[str, str]]],
) -> tuple[str | None, list[str]]:
    loc = str(row["canonical_quran_loc"])
    row_key = _join_surface_key(str(row["visible_surface"]))
    indexed = index_by_loc.get(loc)
    matches = [
        item["loc"]
        for item in index_by_ayah.get(ayah_from_loc(loc), [])
        if _join_surface_key(item["surface"]) == row_key
    ]
    return indexed, matches


def classify_row(
    row: dict[str, Any],
    index_by_loc: dict[str, str],
    index_by_ayah: dict[str, list[dict[str, str]]],
    demoted_row_ids: set[str],
    correction_row_ids: set[str],
    packet_ref: str,
) -> dict[str, Any]:
    row_id = str(row["row_id"])
    indexed, matches = exact_matches(row, index_by_loc, index_by_ayah)
    visible = str(row["visible_surface"])
    exact_at_loc = indexed is not None and _join_surface_key(indexed) == _join_surface_key(visible)
    result: dict[str, Any] = {
        "canonical_quran_loc": row.get("canonical_quran_loc"),
        "card_id": row.get("card_id"),
        "correction": None,
        "demotion": None,
        "entry_id": row.get("entry_id"),
        "evidence": {
            "full_index": "qamus/indexes/quran-loc-surface/index.jsonl",
            "indexed_location_surface": indexed,
            "indexed_location_surface_join_key": _join_surface_key(indexed) if indexed is not None else None,
            "matching_positions_in_ayah": matches,
            "packet_ref": packet_ref,
            "visible_surface_join_key": _join_surface_key(visible),
        },
        "exception": None,
        "prior_bucket": row.get("bucket") or row.get("prior_bucket"),
        "prior_classification": row.get("classification"),
        "quran_ref": row.get("quran_ref"),
        "qword_row_id": row.get("qword_row_id"),
        "row_id": row_id,
        "schema": SCHEMA_ROW,
        "terminal_class": None,
        "visible_surface": visible,
    }

    if row_id in demoted_row_ids:
        result["terminal_class"] = "demoted"
        result["demotion"] = {
            "report": "qamus/reports/rm36-fallback-reverification/demotion-wave.report.json",
            "wave": "rm36-demotion-01",
        }
        return result

    if exact_at_loc:
        if row_id in correction_row_ids:
            result["terminal_class"] = "closed_by_correction"
            result["correction"] = {
                "data_commit": PR53_DATA_COMMIT,
                "merge_commit": PR53_MERGE_COMMIT,
                "pull_request": 53,
            }
        else:
            result["terminal_class"] = "closed_verified"
        return result

    exact_pair = {"indexed": indexed, "visible": visible}
    classification = row.get("classification")
    quran_ref = str(row.get("quran_ref"))
    if quran_ref == "98:1":
        exception = {
            "cause": "wbw_slice_reference_artifact",
            "concrete_reason": (
                "the example-relative WBW slice at 98:1 has a literal ellipsis and its locs do not align "
                "with the full-Quran index; the full index also prepends the basmala"
            ),
            "exact_pair": exact_pair,
            "manifest_ref": "qamus/indexes/quran-loc-surface/index.manifest.json#consistency_proof",
            "owner_gated_data_fix": False,
            "packet_ref": packet_ref,
            "wbw_slice_reference": "98:1",
        }
    elif classification == "normalization_correction" or quran_ref in SURFACE_DRIFT_REFS:
        exception = {
            "cause": "vowel_preserving_surface_drift",
            "concrete_reason": (
                "the row and full-index loc remain consonantally related but differ under the required "
                "vowel-preserving join"
            ),
            "exact_pair": exact_pair,
            "owner_gated_data_fix": False,
            "packet_ref": packet_ref,
            "surface_delta": surface_delta(visible, indexed),
        }
    elif classification == "permanent_exception_candidate":
        exception = {
            "cause": "owner_gated_source_card_surface_fix",
            "concrete_reason": (
                "the accepted row points at a loc whose full-index surface is a different token, and the "
                "visible suffix is not an exact vowel-preserving match elsewhere in the ayah"
            ),
            "exact_pair": exact_pair,
            "owner_gated_data_fix": True,
            "packet_ref": packet_ref,
            "surface_delta": surface_delta(visible, indexed),
        }
    else:
        exception = {
            "cause": "example_fragment_relative_index_artifact",
            "concrete_reason": (
                "the row_unique_surface fallback treated an example-fragment word index as an absolute "
                "ayah word index; the full-Quran loc-surface join disagrees"
            ),
            "exact_pair": exact_pair,
            "owner_gated_data_fix": True,
            "packet_ref": packet_ref,
            "surface_delta": surface_delta(visible, indexed),
        }
    result["terminal_class"] = "exception"
    result["exception"] = exception
    return result


def crosswalk_packet_refs(wanted_row_ids: set[str]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    refs: dict[str, str] = {}
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(CROSSWALK_DIR.glob("*.jsonl"), key=lambda item: item.as_posix()):
        relative = path.relative_to(REPO_ROOT).as_posix()
        for row in load_jsonl(path):
            row_id = str(row.get("row_id", ""))
            if row_id in wanted_row_ids:
                refs[row_id] = f"{relative}#row_id={row_id}"
                rows[row_id] = row
    missing = sorted(wanted_row_ids - refs.keys())
    if missing:
        raise ValueError(f"crosswalk rows not found for packet refs: {missing[:5]}")
    return refs, rows


def build() -> tuple[bytes, bytes, bytes, bytes, dict[str, Any]]:
    failing_rows = load_jsonl(FAILING_PATH)
    if len(failing_rows) != 479 or len({row["row_id"] for row in failing_rows}) != 479:
        raise ValueError("current failing-row identity set must contain 479 unique rows")
    demotion_report = load_json(DEMOTION_PATH)
    demoted_row_ids = {row["row_id"] for row in demotion_report["demotions"]}
    if len(demoted_row_ids) != 37:
        raise ValueError("lane-a2 demotion report must contain 37 unique row IDs")
    active_row_ids = {row["row_id"] for row in failing_rows} - demoted_row_ids
    if len(active_row_ids) != 442:
        raise ValueError("current non-PASS/non-terminal residual set must contain exactly 442 rows")

    index_manifest = load_json(INDEX_MANIFEST_PATH)
    if index_manifest["counts"]["words"] != 77881:
        raise ValueError("full-Quran index manifest word count must be 77,881")
    if sha256_file(INDEX_PATH) != index_manifest["artifact_sha256"]:
        raise ValueError("full-Quran index hash does not match its manifest")
    index_by_loc, index_by_ayah = index_rows(load_jsonl(INDEX_PATH))
    packet_refs, crosswalk_rows = crosswalk_packet_refs({row["row_id"] for row in failing_rows})

    correction_refs, correction_rows = crosswalk_packet_refs(PR53_CROSSWALK_ROW_IDS)
    for row_id, correction_row in correction_rows.items():
        if correction_row.get("quran_ref") != "4:64":
            raise ValueError(f"PR #53 correction did not land at 4:64 for {row_id}")

    terminal_rows = [
        classify_row(
            row,
            index_by_loc,
            index_by_ayah,
            demoted_row_ids,
            PR53_CROSSWALK_ROW_IDS,
            packet_refs[row["row_id"]],
        )
        for row in failing_rows
    ]
    terminal_rows.sort(key=lambda row: (TERMINAL_ORDER[row["terminal_class"]], row["row_id"]))
    if any(row["terminal_class"] not in TERMINAL_ORDER for row in terminal_rows):
        raise ValueError("every output row must have exactly one terminal class")

    disposition_counter = Counter(row["terminal_class"] for row in terminal_rows)
    disposition_counts = complete_terminal_counts(disposition_counter)
    expected_dispositions = {
        "closed_by_correction": 0,
        "closed_verified": 36,
        "demoted": 37,
        "exception": 406,
    }
    if disposition_counts != expected_dispositions:
        raise ValueError(f"unexpected terminal dispositions: {disposition_counts}")
    active_rows = [row for row in terminal_rows if row["row_id"] in active_row_ids]
    exception_counts = Counter(
        row["exception"]["cause"] for row in active_rows if row["terminal_class"] == "exception"
    )
    expected_exceptions = {
        "example_fragment_relative_index_artifact": 13,
        "owner_gated_source_card_surface_fix": 1,
        "vowel_preserving_surface_drift": 385,
        "wbw_slice_reference_artifact": 7,
    }
    if dict(sorted(exception_counts.items())) != dict(sorted(expected_exceptions.items())):
        raise ValueError(f"unexpected exception causes: {dict(exception_counts)}")

    residual_bytes = jsonl_bytes(terminal_rows)
    owner_gated_defects = [
        {
            "canonical_quran_loc": row["canonical_quran_loc"],
            "cause": row["exception"]["cause"],
            "exact_pair": row["exception"]["exact_pair"],
            "matching_positions_in_ayah": row["evidence"]["matching_positions_in_ayah"],
            "packet_ref": row["exception"]["packet_ref"],
            "row_id": row["row_id"],
        }
        for row in active_rows
        if row["terminal_class"] == "exception" and row["exception"]["owner_gated_data_fix"]
    ]
    report = {
        "baseline_head": BASELINE_HEAD,
        "correction_pr_53": {
            "active_residual_intersection": len(active_row_ids & PR53_CROSSWALK_ROW_IDS),
            "corrected_ref": {"from": "4:46", "to": "4:64"},
            "data_commit": PR53_DATA_COMMIT,
            "merge_commit": PR53_MERGE_COMMIT,
            "pull_request": 53,
            "rows": [
                {
                    "packet_ref": correction_refs[row_id],
                    "quran_ref": correction_rows[row_id]["quran_ref"],
                    "qword_row_id": correction_rows[row_id]["qword_row_id"],
                    "row_id": row_id,
                }
                for row_id in sorted(correction_rows)
            ],
            "verification": (
                "landed and current; the corrected rows are not members of the 442 active RM-36 residual IDs"
            ),
        },
        "disposition_counts": disposition_counts,
        "exception_cause_counts": dict(sorted(exception_counts.items())),
        "generated_by": GENERATOR,
        "inputs": {
            "demotion_report": {
                "path": DEMOTION_PATH.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_file(DEMOTION_PATH),
            },
            "full_quran_index": {
                "path": INDEX_PATH.relative_to(REPO_ROOT).as_posix(),
                "row_count": len(index_by_loc),
                "sha256": sha256_file(INDEX_PATH),
            },
            "full_quran_index_manifest": {
                "path": INDEX_MANIFEST_PATH.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_file(INDEX_MANIFEST_PATH),
            },
            "prior_failing_rows": {
                "path": FAILING_PATH.relative_to(REPO_ROOT).as_posix(),
                "row_count": len(failing_rows),
                "sha256": sha256_file(FAILING_PATH),
            },
            "prior_residual_report": {
                "path": PRIOR_REPORT_PATH.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_file(PRIOR_REPORT_PATH),
            },
        },
        "method": {
            "closure_rule": "canonical_quran_loc plus vowel-preserving exact surface join",
            "exception_rule": "no generic unverifiable state; exact pair and concrete cause required",
            "normalizer": "tools.validate_largelexicon_denominator_join._join_surface_key",
        },
        "new_owner_gated_canonical_data_defects": owner_gated_defects,
        "new_owner_gated_canonical_data_defects_count": len(owner_gated_defects),
        "output": {
            "residual_artifact": RESIDUAL_PATH.relative_to(REPO_ROOT).as_posix(),
            "residual_artifact_row_count": len(terminal_rows),
            "residual_artifact_sha256": sha256_bytes(residual_bytes),
        },
        "schema": SCHEMA_REPORT,
        "scope": {
            "active_closed_by_correction": disposition_counts["closed_by_correction"],
            "active_closed_verified": disposition_counts["closed_verified"],
            "active_explicit_exceptions": disposition_counts["exception"],
            "current_failing_rows": len(failing_rows),
            "exact_current_non_pass_non_terminal_rows": len(active_row_ids),
            "prior_terminal_demotions": len(demoted_row_ids),
        },
        "status": "TERMINAL",
    }
    report_bytes = pretty_json_bytes(report)
    manifest = {
        "generated_by": GENERATOR,
        "inputs": {
            path.relative_to(REPO_ROOT).as_posix(): sha256_file(path)
            for path in [
                FAILING_PATH,
                DEMOTION_PATH,
                PRIOR_REPORT_PATH,
                INDEX_PATH,
                INDEX_MANIFEST_PATH,
            ]
        },
        "outputs": {
            REPORT_PATH.relative_to(REPO_ROOT).as_posix(): {
                "bytes": len(report_bytes),
                "sha256": sha256_bytes(report_bytes),
            },
            RESIDUAL_PATH.relative_to(REPO_ROOT).as_posix(): {
                "bytes": len(residual_bytes),
                "row_count": len(terminal_rows),
                "sha256": sha256_bytes(residual_bytes),
            },
        },
        "schema": SCHEMA_MANIFEST,
    }
    manifest_bytes = pretty_json_bytes(manifest)
    summary = {
        "disposition_counts": disposition_counts,
        "exception_cause_counts": dict(sorted(exception_counts.items())),
        "new_owner_gated_canonical_data_defects_count": len(owner_gated_defects),
    }
    return report_bytes, residual_bytes, manifest_bytes, summary


def write_if_changed(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def run(check: bool) -> int:
    report_bytes, residual_bytes, manifest_bytes, summary = build()
    outputs = {
        REPORT_PATH: report_bytes,
        RESIDUAL_PATH: residual_bytes,
        MANIFEST_PATH: manifest_bytes,
    }
    if check:
        mismatches = [path for path, data in outputs.items() if not path.exists() or path.read_bytes() != data]
        if mismatches:
            for path in mismatches:
                print(f"mismatch {path.relative_to(REPO_ROOT).as_posix()}")
            return 1
    else:
        for path, data in outputs.items():
            write_if_changed(path, data)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Close every current RM-36 residual row deterministically")
    parser.add_argument("--check", action="store_true", help="verify generated bytes without writing")
    args = parser.parse_args()
    return run(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
