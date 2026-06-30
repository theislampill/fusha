#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_dataset_integrity — NON-FATAL drift reporter for the committed public Qamus dataset (blocked item P2-9).

`tools/validate_current_qamus_dataset.py` is the strict, fail-closed acceptance gate. It currently FAILs on a
PRE-EXISTING checksum mismatch: the working-tree `qamus/data/current/entries.jsonl` (sha a68245e…, 4 830 755 bytes)
does not match the sha recorded in `checksums.json` (61a53671…, 4 830 763 bytes). The drift is 8 bytes and is NOT a
CRLF artifact (`.gitattributes` forces `*.jsonl text eol=lf`; the file has 0 CR bytes) — it is owner-territory data
drift that needs an OWNER decision on which side is authoritative. See `qamus/reports/dataset-integrity-blocker.md`.

While that decision is open, the strict validator must NOT be a required CI gate (it would red-flag every run on a
condition this lane cannot resolve). This tool lets CI OBSERVE the drift without breaking it:
  * it re-runs the SAME sha256 reconciliation (each file in `checksums.json` vs its on-disk bytes),
  * prints the per-file match/mismatch list,
  * and ALWAYS exits 0 — except under `--strict`, which exits 1 if any file mismatches.

It NEVER edits, regenerates, or re-checksums anything (read-only). It does NOT vendor or emit dataset content — only
file names, byte counts, and hex digests — and every line it prints is leak-scanned via `tools/leak_sot.py`.

Stdlib only. No network. Deterministic. CLI: [--data-dir DIR] [--strict] | --self-test.
Style-matched to tools/fusha_checkpoint_coverage.py / tools/validate_public_runnability.py.
"""
import argparse
import hashlib
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_DATA = os.path.join(_REPO, "qamus", "data", "current")

# leak_sot is the single source of truth for public-boundary leak detection; import it the same way the
# other validators do (sibling module under tools/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leak_sot  # noqa: E402


def _sha256_file(path):
    """Streaming sha256 of a file's raw bytes (no normalization — matches the strict validator)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def reconcile(data_dir, checksums_name="checksums.json"):
    """Re-derive each listed file's sha256 and compare to the recorded value.

    Returns a dict with a per-file result list and rollups. PURE I/O + hashing — no mutation, no normalization.
    `checksums.json` keys are export-relative (`data/...`, `indexes/...`); the same path mapping the strict
    validator uses is applied so `data/` resolves under the data dir's sibling-rooted `qamus/{data,indexes}/current`.
    """
    cs_path = os.path.join(data_dir, checksums_name)
    checksums = json.load(open(cs_path, encoding="utf-8"))
    qamus_root = os.path.dirname(os.path.dirname(data_dir))  # .../qamus  (data_dir == .../qamus/data/current)
    results = []
    for rel, meta in sorted(checksums.items()):
        # map export-relative 'data/x' / 'indexes/x' -> qamus/{data,indexes}/current/x; otherwise resolve under data_dir
        if rel.startswith(("data/", "indexes/")):
            rel2 = rel.replace("data/", "data/current/", 1).replace("indexes/", "indexes/current/", 1)
            path = os.path.join(qamus_root, *rel2.split("/"))
        else:
            path = os.path.join(data_dir, *rel.split("/"))
        expected = meta.get("sha256")
        if not os.path.exists(path):
            results.append({"file": rel, "status": "missing", "expected": expected, "actual": None})
            continue
        actual = _sha256_file(path)
        results.append({
            "file": rel,
            "status": "match" if actual == expected else "mismatch",
            "expected": expected,
            "actual": actual,
            "bytes": os.path.getsize(path),
            "expected_bytes": meta.get("bytes"),
        })
    mismatches = [r for r in results if r["status"] != "match"]
    return {
        "data_dir": data_dir,
        "total": len(results),
        "matched": sum(1 for r in results if r["status"] == "match"),
        "mismatches": mismatches,
        "results": results,
    }


def render(rep):
    """Build the human report lines. Leak-scanned by the caller before printing."""
    lines = ["dataset-integrity reporter (NON-FATAL; observe-only)",
             "  files checked: %d  (matched %d / drifted %d)"
             % (rep["total"], rep["matched"], len(rep["mismatches"]))]
    if not rep["mismatches"]:
        lines.append("  all recorded checksums reconcile with on-disk bytes.")
    else:
        lines.append("  DRIFT (informational — exit stays 0 unless --strict):")
        for r in rep["mismatches"]:
            if r["status"] == "missing":
                lines.append("    MISSING  %s  (expected %s)" % (r["file"], (r["expected"] or "?")[:12]))
            else:
                lines.append("    MISMATCH %s  expected %s (%s b) != actual %s (%s b)"
                             % (r["file"], (r["expected"] or "?")[:12], r.get("expected_bytes"),
                                (r["actual"] or "?")[:12], r.get("bytes")))
        lines.append("  this is observe-only; resolution is OWNER-gated. "
                     "See qamus/reports/dataset-integrity-blocker.md.")
    return lines


def _emit(lines):
    """Print report lines after leak-scanning each (file names + hashes only; never dataset content)."""
    for ln in lines:
        hits = leak_sot.scan(ln)
        if hits:
            # defensive: a digest/name should never trip the tripwire, but never emit a leaking line.
            print("    <line withheld: leak tripwire %s>" % hits[:3])
        else:
            print(ln)


def _self_test():
    """Prove the reporter's LOGIC on SYNTHETIC files only (never touches the real, currently-mismatched dataset)."""
    import tempfile
    failures = []

    def _build(tmp, entries_bytes, record_matching):
        """Lay out a synthetic qamus/data/current with a checksums.json; record the MATCHING or a WRONG sha."""
        dc = os.path.join(tmp, "qamus", "data", "current")
        os.makedirs(dc, exist_ok=True)
        ep = os.path.join(dc, "entries.jsonl")
        with open(ep, "wb") as f:
            f.write(entries_bytes)
        real = hashlib.sha256(entries_bytes).hexdigest()
        recorded = real if record_matching else hashlib.sha256(entries_bytes + b"X").hexdigest()
        with open(os.path.join(dc, "checksums.json"), "w", encoding="utf-8") as f:
            json.dump({"data/entries.jsonl": {"bytes": len(entries_bytes), "sha256": recorded}}, f)
        return dc

    payload = b'{"id":"x","root":"abc"}\n'

    # (1) matching set -> 0 mismatches, exit 0 in BOTH modes
    with tempfile.TemporaryDirectory() as tmp:
        dc = _build(tmp, payload, record_matching=True)
        rep = reconcile(dc)
        if rep["mismatches"]:
            failures.append("matching set reported mismatches: %s" % rep["mismatches"])
        if _run_exit(dc, strict=False) != 0:
            failures.append("matching set: non-strict exit != 0")
        if _run_exit(dc, strict=True) != 0:
            failures.append("matching set: --strict exit != 0 (should pass when all match)")

    # (2) mismatched set -> reported, non-strict exit 0, --strict exit 1
    with tempfile.TemporaryDirectory() as tmp:
        dc = _build(tmp, payload, record_matching=False)
        rep = reconcile(dc)
        if len(rep["mismatches"]) != 1 or rep["mismatches"][0]["status"] != "mismatch":
            failures.append("mismatched set not reported as a single mismatch: %s" % rep["mismatches"])
        if _run_exit(dc, strict=False) != 0:
            failures.append("mismatched set: non-strict exit must be 0 (observe-only)")
        if _run_exit(dc, strict=True) != 1:
            failures.append("mismatched set: --strict exit must be 1")
        # the rendered DRIFT lines must be leak-clean (file names + digests only)
        for ln in render(rep):
            if leak_sot.scan(ln):
                failures.append("rendered line trips leak tripwire: %r" % ln)

    # (3) missing file -> reported as 'missing', counts as drift under --strict
    with tempfile.TemporaryDirectory() as tmp:
        dc = _build(tmp, payload, record_matching=True)
        os.remove(os.path.join(dc, "entries.jsonl"))
        rep = reconcile(dc)
        if not rep["mismatches"] or rep["mismatches"][0]["status"] != "missing":
            failures.append("missing file not reported as 'missing': %s" % rep["mismatches"])
        if _run_exit(dc, strict=False) != 0:
            failures.append("missing file: non-strict exit must be 0")
        if _run_exit(dc, strict=True) != 1:
            failures.append("missing file: --strict exit must be 1")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   report_dataset_integrity self-test: synthetic matching set exits 0 (both modes); "
              "mismatched + missing sets are reported, non-strict exits 0, --strict exits 1; lines leak-clean")
    return 0 if not failures else 1


def _run_exit(data_dir, strict):
    """Exit-code policy under test: ALWAYS 0, except --strict returns 1 on any non-match. (No printing.)"""
    rep = reconcile(data_dir)
    return 1 if (strict and rep["mismatches"]) else 0


def main():
    ap = argparse.ArgumentParser(
        description="Observe-only checksum-drift reporter for qamus/data/current (NON-FATAL; --strict to gate).")
    ap.add_argument("--data-dir", default=_DATA, help="dataset dir holding checksums.json (default: qamus/data/current)")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any file mismatches (default: always exit 0)")
    ap.add_argument("--self-test", action="store_true", help="prove the reporter logic on synthetic files; exit 0/1")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    rep = reconcile(a.data_dir)
    _emit(render(rep))
    if a.strict and rep["mismatches"]:
        return 1
    return 0  # observe-only: drift never breaks CI unless --strict


if __name__ == "__main__":
    sys.exit(main())
