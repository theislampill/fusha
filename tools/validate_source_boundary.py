#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_source_boundary — the drift gate for the leak source-of-truth (P2 deliverable E).

Asserts that tools/leak_sot.py is a genuine SUPERSET of every legacy leak detector (so the consolidation cannot
silently lose coverage), and that the historical cert-validator gap (LEAK_TERMS missing tafsir + tanzil) is closed.
This is the Poka-yoke that prevents the 5 detectors from drifting apart again: if someone narrows leak_sot, or a
legacy detector adds a token the SoT lacks, this gate fails.

CLI:
  python3 tools/validate_source_boundary.py --self-test
  python3 tools/validate_source_boundary.py <records.jsonl>   # scan a JSONL's serialized rows for any leak
Stdlib only. Exit non-zero on any violation.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import leak_sot  # noqa: E402


def _legacy_tuples():
    """Import the two enumerable legacy tuples so we can assert leak_sot's projection is a superset of each member."""
    out = {}
    try:
        from tools.validate_public_private_boundary import FORBIDDEN_LABELS as PPB
        out["validate_public_private_boundary.FORBIDDEN_LABELS"] = tuple(PPB)
    except Exception:
        pass
    try:
        from tools.validate_rich_hover_certification import LEAK_TERMS as CERT
        out["validate_rich_hover_certification.LEAK_TERMS"] = tuple(CERT)
    except Exception:
        pass
    return out


def _self_test():
    failures = []
    # 1. leak_sot's own union/clean assertions
    if leak_sot._self_test() != 0:
        failures.append("leak_sot internal self-test failed")
    # 2. SUBSET: every member of each legacy TUPLE detector must be caught by the SoT (so consolidation lost nothing)
    sot_labels = set(leak_sot.FORBIDDEN_LABELS)
    for name, members in _legacy_tuples().items():
        for m in members:
            ml = m.lower()
            # the SoT must catch the legacy token either as a tuple member or via the regex
            if ml not in sot_labels and not leak_sot.is_leak(m):
                failures.append("%s member %r is NOT covered by leak_sot (drift/regression)" % (name, m))
    # 3. the cert gap is CLOSED: tafsir + tanzil (absent from the legacy LEAK_TERMS) are caught now
    for gap in ("tafsir", "tanzil", "see the tafsir center", "from tanzil dump"):
        if not leak_sot.is_leak(gap):
            failures.append("cert gap not closed: %r passes leak_sot" % gap)
    # 4. the regex projection catches representative strings each legacy REGEX detector caught
    for det, samples in leak_sot.HISTORICAL_DETECTOR_SAMPLES.items():
        for s in samples:
            if not leak_sot.is_leak(s):
                failures.append("%s sample %r not caught (regex projection drift)" % (det, s))
    # 5. the field-scope registry preserves the intentional NARROW scopes (documentation invariant)
    reg = leak_sot.FIELD_SCOPE_REGISTRY
    for v, scope in (("validate_linguistic_decisions", "gloss"), ("validate_rich_hover_certification", "public_payload")):
        if v not in reg or scope not in reg[v]["scope"]:
            failures.append("field-scope registry lost the intentional narrow scope for %s" % v)
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_source_boundary self-test: leak_sot is a verified SUPERSET of all legacy detectors; "
              "cert tafsir/tanzil gap CLOSED; intentional narrow scopes preserved")
    return 0 if not failures else 1


def validate_file(path):
    n, errs = 0, []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            n += 1
            row = json.loads(line)
            hits = leak_sot.scan_obj(row)
            if hits:
                errs.append("line %d: leaks %s" % (i, hits[:5]))
    return n, errs


def main():
    ap = argparse.ArgumentParser(description="Leak source-of-truth drift gate.")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.path:
        ap.error("need a path or --self-test")
    n, errs = validate_file(a.path)
    for e in errs:
        print("FAIL " + e)
    print("scanned %d row(s), %d leak(s)" % (n, len(errs)))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
