#!/usr/bin/env python3
"""Re-verify accepted row-unique fallback crosswalk rows against a pinned corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from normalize_ar import norm_strict  # noqa: E402
from validate_largelexicon_denominator_join import _join_surface_key  # noqa: E402

PASS = "pass"
DEMOTION = "demotion_candidate"
DIVERGENT = "unverifiable_divergent_ayah"
AYAH_MISSING = "ayah_not_indexed"
SURFACE_MISSING = "surface_not_in_indexed_ayah"
BUCKETS = (PASS, DEMOTION, DIVERGENT, AYAH_MISSING, SURFACE_MISSING)
BASELINE_SHA = "bf6d7fc9c9ae40704ad6d82be5becbd946267f1c"
CORPUS_SHA256 = "f2e079dcdce01148074a238e3937314cf02222298f91f83ed66dcbb599697ca7"
DEFAULT_MANIFEST = ROOT / "qamus" / "indexes" / "largelexicon" / "qword-crosswalk" / "GENERATION.json"
DEFAULT_OUTDIR = ROOT / "qamus" / "reports" / "rm36-fallback-reverification"
DIVERGENT_AYAHS = {
    "4:64", "12:37", "19:67", "2:214", "2:274",
    "3:152", "48:15", "92:3", "93:3", "98:1",
}


def classify_rows(
    rows: Iterable[dict[str, Any]],
    corpus_rows: Iterable[dict[str, str]],
    divergent_ayahs: set[str],
) -> dict[str, list[dict[str, Any]]]:
    corpus_by_ayah: dict[str, list[dict[str, str]]] = {}
    corpus_by_loc: dict[str, dict[str, str]] = {}
    for corpus_row in corpus_rows:
        loc = str(corpus_row["loc"])
        parts = loc.split(":")
        if len(parts) != 3:
            raise ValueError(f"invalid corpus loc: {loc!r}")
        normalized = {"loc": loc, "surface": str(corpus_row.get("surface") or "")}
        corpus_by_ayah.setdefault(":".join(parts[:2]), []).append(normalized)
        corpus_by_loc[loc] = normalized
    for ayah_rows in corpus_by_ayah.values():
        ayah_rows.sort(key=lambda row: _loc_sort_key(row["loc"]))

    results = {bucket: [] for bucket in BUCKETS}
    for row in rows:
        quran_ref = str(row.get("quran_ref") or _ayah_from_loc(row.get("canonical_quran_loc")))
        canonical_loc = str(row.get("canonical_quran_loc") or "")
        visible_surface = str(row.get("visible_surface") or "")
        row_key = _join_surface_key(visible_surface)
        ayah_rows = corpus_by_ayah.get(quran_ref)
        indexed_at_loc = corpus_by_loc.get(canonical_loc)
        indexed_surface = indexed_at_loc["surface"] if indexed_at_loc else None
        indexed_key = _join_surface_key(indexed_surface) if indexed_surface is not None else None
        if quran_ref in divergent_ayahs or ayah_rows is None:
            matching_positions = []
        else:
            matching_positions = [
                item["loc"] for item in ayah_rows
                if _join_surface_key(item["surface"]) == row_key
            ]
        record = {
            "bucket": None,
            "canonical_quran_loc": canonical_loc or None,
            "card_id": row.get("card_id"),
            "entry_id": row.get("entry_id"),
            "indexed_location_surface": indexed_surface,
            "indexed_location_surface_join_key": indexed_key,
            "matching_positions": matching_positions,
            "quran_ref": quran_ref,
            "qword_row_id": row.get("qword_row_id"),
            "row_id": row.get("row_id"),
            "row_surface_join_key": row_key,
            "schema": "fusha/rm36-fallback-reverification-failing-row@1",
            "visible_surface": visible_surface,
        }
        if quran_ref in divergent_ayahs:
            bucket = DIVERGENT
        elif ayah_rows is None:
            bucket = AYAH_MISSING
        elif not matching_positions:
            bucket = SURFACE_MISSING
        elif len(matching_positions) > 1:
            bucket = DEMOTION
        else:
            bucket = PASS
        record["bucket"] = bucket
        results[bucket].append(record)

    for bucket_rows in results.values():
        bucket_rows.sort(key=_record_sort_key)
    return results


def coverage_status(results: dict[str, list[dict[str, Any]]]) -> tuple[str, list[str]]:
    reasons = [bucket for bucket in BUCKETS if bucket != PASS and results.get(bucket)]
    return ("PARTIAL", reasons) if reasons else ("COMPLETE", [])


def build_report(
    *,
    total_accepted_rows: int,
    method_distribution: dict[str, int],
    results: dict[str, list[dict[str, Any]]],
    min_man_demonstration: dict[str, Any],
    runtime_seconds: float,
) -> dict[str, Any]:
    fallback_total = sum(len(results.get(bucket, [])) for bucket in BUCKETS)
    status, reasons = coverage_status(results)
    buckets = {}
    for bucket in BUCKETS:
        numerator = len(results.get(bucket, []))
        percent = round(100.0 * numerator / fallback_total, 6) if fallback_total else 0.0
        buckets[bucket] = {
            "denominator": fallback_total,
            "numerator": numerator,
            "percent": percent,
        }
    failures = [row for bucket in BUCKETS if bucket != PASS for row in results.get(bucket, [])]
    failures.sort(key=lambda row: (BUCKETS.index(row["bucket"]), _record_sort_key(row)))
    if reasons:
        coverage_claim = "PARTIAL: " + ", ".join(
            f"{bucket}={len(results[bucket])}" for bucket in reasons
        )
    else:
        coverage_claim = f"COMPLETE: all {fallback_total} fallback rows passed re-verification"
    return {
        "buckets": buckets,
        "coverage_claim": coverage_claim,
        "coverage_status": status,
        "fallback_rows_checked": fallback_total,
        "generated_by": "tools/reverify_crosswalk_fallback.py",
        "method_distribution": dict(sorted(method_distribution.items())),
        "min_man_demonstration": min_man_demonstration,
        "partial_reasons": reasons,
        "representative_failing_rows": failures[:10],
        "runtime_seconds": runtime_seconds,
        "schema": "fusha/rm36-fallback-reverification-report@1",
        "total_accepted_rows": total_accepted_rows,
    }


def demotion_stop_exceeded(results: dict[str, list[dict[str, Any]]]) -> bool:
    total = sum(len(results.get(bucket, [])) for bucket in BUCKETS)
    return bool(total and len(results.get(DEMOTION, [])) / total > 0.01)


def scan_crosswalks(manifest_path: Path) -> tuple[int, dict[str, int], list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shard_specs = manifest.get("shards")
    if not isinstance(shard_specs, list) or not shard_specs:
        raise ValueError("crosswalk manifest has no shards")
    if manifest.get("shard_count") != len(shard_specs):
        raise ValueError("crosswalk manifest shard_count mismatch")

    accepted_count = 0
    methods: dict[str, int] = {}
    fallback_rows: list[dict[str, Any]] = []
    rows_scanned = 0
    manifest_dir = manifest_path.resolve().parent
    for spec in shard_specs:
        rel = Path(str(spec.get("path") or ""))
        shard_path = (manifest_dir / rel).resolve()
        if shard_path.parent != manifest_dir:
            raise ValueError(f"crosswalk shard escapes manifest directory: {rel}")
        actual_sha = _sha256_file(shard_path)
        if actual_sha != spec.get("sha256"):
            raise ValueError(f"crosswalk shard sha256 mismatch: {rel}")
        shard_rows = 0
        with shard_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{rel}:{line_no}: crosswalk row is not an object")
                shard_rows += 1
                rows_scanned += 1
                if row.get("status") != "canonical_crosswalk_accepted":
                    continue
                accepted_count += 1
                method = row.get("resolution_method")
                method_label = str(method) if method is not None else "<missing>"
                methods[method_label] = methods.get(method_label, 0) + 1
                if method == "row_unique_surface_fallback":
                    fallback_rows.append(row)
        if shard_rows != spec.get("row_count"):
            raise ValueError(f"crosswalk shard row_count mismatch: {rel}")
    if rows_scanned != manifest.get("row_count"):
        raise ValueError("crosswalk manifest row_count mismatch")
    fallback_rows.sort(key=lambda row: (str(row.get("row_id") or ""), json.dumps(row, ensure_ascii=False, sort_keys=True)))
    return accepted_count, dict(sorted(methods.items())), fallback_rows, {
        "manifest_sha256": _sha256_file(manifest_path),
        "rows_scanned": rows_scanned,
        "shards_verified": len(shard_specs),
    }


def load_corpus(path: Path, expected_sha256: str | None = None) -> tuple[list[dict[str, str]], str]:
    actual_sha = _sha256_file(path)
    if expected_sha256 is not None and actual_sha != expected_sha256:
        raise ValueError(f"corpus sha256 mismatch: expected {expected_sha256}, got {actual_sha}")
    rows: list[dict[str, str]] = []
    seen_locs: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            loc = row.get("loc") if isinstance(row, dict) else None
            surface = row.get("surface") if isinstance(row, dict) else None
            if not isinstance(loc, str) or not isinstance(surface, str):
                raise ValueError(f"{path.name}:{line_no}: corpus row requires string loc and surface")
            _loc_sort_key(loc)
            if loc in seen_locs:
                raise ValueError(f"{path.name}:{line_no}: duplicate corpus loc {loc}")
            seen_locs.add(loc)
            rows.append({"loc": loc, "surface": surface})
    rows.sort(key=lambda row: _loc_sort_key(row["loc"]))
    return rows, actual_sha


def write_outputs(
    outdir: Path,
    report: dict[str, Any],
    failures: Iterable[dict[str, Any]],
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    ordered = list(failures)
    ordered.sort(key=lambda row: (BUCKETS.index(row["bucket"]), _record_sort_key(row)))
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered)
    (outdir / "failing-rows.jsonl").write_text(text, encoding="utf-8", newline="\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_min_man_demonstration(corpus_rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    wanted = {"24:35:18": "min", "24:35:39": "man"}
    found: dict[str, dict[str, str]] = {}
    for row in corpus_rows:
        label = wanted.get(row["loc"])
        if label:
            surface = row["surface"]
            found[label] = {
                "join_surface_key": _join_surface_key(surface),
                "loc": row["loc"],
                "norm_strict_key": norm_strict(surface),
                "surface": surface,
            }
    if set(found) != {"min", "man"}:
        raise ValueError("corpus lacks the required 24:35 مِن/مَن demonstration positions")
    return {
        "ayah": "24:35",
        "conclusion": "vowel-preserving join keys keep مِن and مَن distinct; norm_strict collapses them",
        "join_keys_collide": found["min"]["join_surface_key"] == found["man"]["join_surface_key"],
        "man": found["man"],
        "min": found["min"],
        "norm_strict_keys_collide": found["min"]["norm_strict_key"] == found["man"]["norm_strict_key"],
    }


def verify_baseline_inputs() -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ValueError(f"baseline SHA {BASELINE_SHA} is not an ancestor of HEAD")
    input_path = "qamus/indexes/largelexicon/qword-crosswalk"
    committed_diff = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_SHA, "HEAD", "--", input_path],
        cwd=ROOT,
        check=False,
    )
    working_diff = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", input_path],
        cwd=ROOT,
        check=False,
    )
    if committed_diff.returncode != 0 or working_diff.returncode != 0:
        raise ValueError("crosswalk inputs differ from the authoritative baseline")


def run(manifest_path: Path, corpus_path: Path, outdir: Path) -> int:
    started = time.monotonic()
    verify_baseline_inputs()

    accepted_count, methods, fallback_rows, scan_meta = scan_crosswalks(manifest_path)
    if not methods or set(methods) == {"<missing>"}:
        raise ValueError("STOP: accepted crosswalk rows carry no distinguishable resolution-method field")
    if not fallback_rows:
        raise ValueError("STOP: no row_unique_surface_fallback rows found")

    corpus_rows, corpus_sha = load_corpus(corpus_path, CORPUS_SHA256)
    results = classify_rows(fallback_rows, corpus_rows, DIVERGENT_AYAHS)
    demotion_count = len(results[DEMOTION])
    demotion_percent = 100.0 * demotion_count / len(fallback_rows)
    if demotion_stop_exceeded(results):
        stop_report = {
            "demotion_candidate_count": demotion_count,
            "demotion_candidate_percent": round(demotion_percent, 6),
            "fallback_rows_checked": len(fallback_rows),
            "stop_threshold_percent": 1.0,
        }
        print("STOP: demotion candidates exceed 1% of fallback rows", file=sys.stderr)
        print(json.dumps(stop_report, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        return 2

    demo = build_min_man_demonstration(corpus_rows)
    if demo["join_keys_collide"] or not demo["norm_strict_keys_collide"]:
        raise ValueError("24:35 min/man demonstration violates the required normalization contract")
    runtime_seconds = round(time.monotonic() - started, 3)
    report = build_report(
        total_accepted_rows=accepted_count,
        method_distribution=methods,
        results=results,
        min_man_demonstration=demo,
        runtime_seconds=runtime_seconds,
    )
    report["authoritative_baseline_sha"] = BASELINE_SHA
    report["corpus_input"] = {
        "filename": corpus_path.name,
        "row_count": len(corpus_rows),
        "sha256": corpus_sha,
    }
    report["crosswalk_input"] = {
        "manifest": "qamus/indexes/largelexicon/qword-crosswalk/GENERATION.json",
        **scan_meta,
    }
    report["known_divergent_ayahs"] = sorted(DIVERGENT_AYAHS, key=_loc_sort_key)
    report["stop_conditions"] = {
        "demotion_candidate_percent": round(demotion_percent, 6),
        "demotion_candidate_stop_exceeded": False,
        "demotion_candidate_stop_threshold_percent": 1.0,
        "resolution_method_field_distinguishable": True,
    }
    failures = [row for bucket in BUCKETS if bucket != PASS for row in results[bucket]]
    write_outputs(outdir, report, failures)
    print(json.dumps({
        "buckets": {bucket: len(results[bucket]) for bucket in BUCKETS},
        "coverage_status": report["coverage_status"],
        "fallback_rows_checked": len(fallback_rows),
        "runtime_seconds": runtime_seconds,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _ayah_from_loc(loc: Any) -> str:
    parts = str(loc or "").split(":")
    if len(parts) < 2:
        raise ValueError(f"row lacks a valid quran_ref/canonical_quran_loc: {loc!r}")
    return ":".join(parts[:2])


def _loc_sort_key(loc: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in loc.split(":"))
    except ValueError as exc:
        raise ValueError(f"invalid numeric loc: {loc!r}") from exc


def _record_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    loc = record.get("canonical_quran_loc")
    loc_key = _loc_sort_key(loc) if loc else (sys.maxsize,)
    return loc_key, str(record.get("row_id") or ""), json.dumps(record, ensure_ascii=False, sort_keys=True)


def self_test() -> int:
    corpus = [
        {"loc": "1:1:1", "surface": "مِن"},
        {"loc": "1:1:2", "surface": "مِن"},
        {"loc": "2:1:1", "surface": "مِن"},
        {"loc": "2:1:2", "surface": "مَن"},
        {"loc": "3:1:1", "surface": "كِتَابٌ"},
        {"loc": "4:64:1", "surface": "فَلَا"},
    ]
    rows = [
        {
            "row_id": "repeated",
            "quran_ref": "1:1",
            "canonical_quran_loc": "1:1:1",
            "visible_surface": "مِن",
        },
        {
            "row_id": "min",
            "quran_ref": "2:1",
            "canonical_quran_loc": "2:1:1",
            "visible_surface": "مِن",
        },
        {
            "row_id": "not-in-ayah",
            "quran_ref": "3:1",
            "canonical_quran_loc": "3:1:1",
            "visible_surface": "كُتُبٌ",
        },
        {
            "row_id": "divergent",
            "quran_ref": "4:64",
            "canonical_quran_loc": "4:64:1",
            "visible_surface": "فَلَا",
        },
        {
            "row_id": "ayah-missing",
            "quran_ref": "9:9",
            "canonical_quran_loc": "9:9:1",
            "visible_surface": "آيَةٌ",
        },
    ]

    results = classify_rows(rows, corpus, {"4:64"})
    assert [row["row_id"] for row in results[DEMOTION]] == ["repeated"]
    assert results[DEMOTION][0]["matching_positions"] == ["1:1:1", "1:1:2"]
    assert [row["row_id"] for row in results[PASS]] == ["min"]

    min_key = _join_surface_key("مِن")
    man_key = _join_surface_key("مَن")
    assert min_key != man_key
    assert norm_strict("مِن") == norm_strict("مَن")

    missing = results[SURFACE_MISSING]
    assert [row["row_id"] for row in missing] == ["not-in-ayah"]
    assert missing[0]["row_surface_join_key"] == _join_surface_key("كُتُبٌ")
    assert missing[0]["indexed_location_surface_join_key"] == _join_surface_key("كِتَابٌ")
    assert coverage_status(results)[0] == "PARTIAL"
    assert SURFACE_MISSING in coverage_status(results)[1]
    assert [row["row_id"] for row in results[DIVERGENT]] == ["divergent"]
    assert results[DIVERGENT][0]["matching_positions"] == []
    assert [row["row_id"] for row in results[AYAH_MISSING]] == ["ayah-missing"]

    reordered = classify_rows(reversed(rows), reversed(corpus), {"4:64"})
    assert results == reordered

    report = build_report(
        total_accepted_rows=8,
        method_distribution={"card_exact_subsequence": 3, "row_unique_surface_fallback": 5},
        results=results,
        min_man_demonstration={"join_keys_collide": False, "norm_strict_keys_collide": True},
        runtime_seconds=1.25,
    )
    assert report["coverage_status"] == "PARTIAL"
    assert report["fallback_rows_checked"] == 5
    assert report["buckets"][SURFACE_MISSING] == {"denominator": 5, "numerator": 1, "percent": 20.0}
    assert report["partial_reasons"] == [DEMOTION, DIVERGENT, AYAH_MISSING, SURFACE_MISSING]
    assert len(report["representative_failing_rows"]) <= 10
    assert report["runtime_seconds"] == 1.25
    assert demotion_stop_exceeded(results)

    one_of_101 = {bucket: [] for bucket in BUCKETS}
    one_of_101[DEMOTION] = [{"row_id": "one"}]
    one_of_101[PASS] = [{"row_id": str(index)} for index in range(100)]
    assert not demotion_stop_exceeded(one_of_101)

    assert _join_surface_key.__module__ == "validate_largelexicon_denominator_join"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        shard = temp / "fixture.jsonl"
        shard_rows = [
            {
                "row_id": "accepted-fallback",
                "status": "canonical_crosswalk_accepted",
                "resolution_method": "row_unique_surface_fallback",
            },
            {
                "row_id": "accepted-exact",
                "status": "canonical_crosswalk_accepted",
                "resolution_method": "card_exact_subsequence",
            },
            {"row_id": "unresolved", "status": "source_crosswalk_packet_ready"},
        ]
        shard.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in shard_rows),
            encoding="utf-8",
        )
        shard_sha = hashlib.sha256(shard.read_bytes()).hexdigest()
        manifest = temp / "GENERATION.json"
        manifest.write_text(
            json.dumps(
                {
                    "row_count": 3,
                    "shard_count": 1,
                    "shards": [{"path": shard.name, "row_count": 3, "sha256": shard_sha}],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        accepted_count, methods, fallback_rows, scan_meta = scan_crosswalks(manifest)
        assert accepted_count == 2
        assert methods == {"card_exact_subsequence": 1, "row_unique_surface_fallback": 1}
        assert [row["row_id"] for row in fallback_rows] == ["accepted-fallback"]
        assert scan_meta["rows_scanned"] == 3

        corpus_path = temp / "corpus.jsonl"
        corpus_path.write_text(
            '{"loc":"24:35:18","surface":"مِن"}\n'
            '{"loc":"24:35:39","surface":"مَن"}\n',
            encoding="utf-8",
        )
        corpus_sha = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
        loaded_corpus, actual_sha = load_corpus(corpus_path, corpus_sha)
        assert actual_sha == corpus_sha
        assert loaded_corpus[1]["surface"] == "مَن"
        demo = build_min_man_demonstration(loaded_corpus)
        assert not demo["join_keys_collide"]
        assert demo["norm_strict_keys_collide"]
        assert demo["min"]["join_surface_key"] == "مِن"
        assert demo["man"]["join_surface_key"] == "مَن"

        outdir = temp / "out"
        failures = [row for bucket in BUCKETS if bucket != PASS for row in results[bucket]]
        write_outputs(outdir, report, failures)
        assert json.loads((outdir / "report.json").read_text(encoding="utf-8")) == report
        failure_lines = (outdir / "failing-rows.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(failure_lines) == 4
        assert all(json.loads(line)["bucket"] != PASS for line in failure_lines)

    print("ok   reverify_crosswalk_fallback self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus", type=Path, help="local corpus loc-to-surface JSONL (SHA-256 pinned)")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.corpus is None:
        parser.error("--corpus is required outside --self-test")
    return run(args.manifest, args.corpus, args.outdir)


if __name__ == "__main__":
    raise SystemExit(main())
