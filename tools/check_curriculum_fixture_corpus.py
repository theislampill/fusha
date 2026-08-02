#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic-regeneration gate against the AUTHORIZED fixture corpus.

The real L1-L6 corpus is private (custody boundary), so CI proves builder
determinism + extraction semantics on the committed clean-room fixture corpus
(curriculum/l1l6/testdata/fixture-corpus — synthetic lessons authored for
this repo, zero kitabite content):

1. build twice into two temp dirs -> every artifact byte-identical
   (determinism);
2. the combined output digest must equal the pinned digest in
   curriculum/l1l6/testdata/expected-digest.json (semantic drift is red;
   an INTENDED extractor change re-pins with --repin and shows up in diff);
3. semantic assertions: the variant learner-error heading counts as a
   mistake section (not a concept) and the repeated concept slug produces a
   concept_revisited edge.

Usage: python tools/check_curriculum_fixture_corpus.py [--repin]
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "curriculum" / "l1l6" / "testdata" / "fixture-corpus"
PIN = ROOT / "curriculum" / "l1l6" / "testdata" / "expected-digest.json"


def build_into(tmp):
    rc = subprocess.call([sys.executable,
                          str(ROOT / "tools" / "build_curriculum_l1l6.py"),
                          "--source-dir", str(CORPUS), "--out-dir", str(tmp)],
                         stdout=subprocess.DEVNULL)
    if rc != 0:
        raise SystemExit("builder failed on the fixture corpus")
    files = {}
    for p in sorted(Path(tmp).rglob("*")):
        if p.is_file():
            files[str(p.relative_to(tmp)).replace("\\", "/")] = p.read_bytes()
    return files


def main(argv):
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        fa, fb = build_into(a), build_into(b)
    if fa.keys() != fb.keys() or any(fa[k] != fb[k] for k in fa):
        print("FAIL: two builds over the fixture corpus differ (nondeterminism)")
        return 1
    digest = hashlib.sha256()
    for k in sorted(fa):
        digest.update(k.encode("utf-8"))
        digest.update(fa[k])
    hexd = digest.hexdigest()
    if "--repin" in argv:
        PIN.write_bytes((json.dumps({
            "schema": "curriculum.l1l6_fixture_digest.v1",
            "combined_sha256": hexd,
            "files": sorted(fa),
            "note": "pinned output digest of the builder over the clean-room fixture corpus; re-pin ONLY with an intended extractor change",
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print("re-pinned %s" % hexd)
        return 0
    if not PIN.exists():
        print("FAIL: pin file missing (run --repin once and commit)")
        return 1
    pinned = json.loads(PIN.read_text(encoding="utf-8"))["combined_sha256"]
    if pinned != hexd:
        print("FAIL: fixture-corpus digest %s != pinned %s (extractor drift)"
              % (hexd[:16], pinned[:16]))
        return 1

    # semantic assertions on one build
    lessons = [json.loads(l) for l in
               fa["registry/lessons.jsonl"].decode("utf-8").splitlines() if l.strip()]
    l2 = next(l for l in lessons if l["lesson_id"] == "L1.M1.02")
    if l2["counts"]["common_mistakes_sections"] != 1:
        print("FAIL: variant heading not counted as a mistake section")
        return 1
    concepts = fa["graph/concepts.jsonl"].decode("utf-8")
    if "common-errors-to-avoid" in concepts:
        print("FAIL: variant learner-error heading leaked into concepts")
        return 1
    edges = fa["graph/concept-edges.jsonl"].decode("utf-8")
    if '"kind": "concept_revisited"' not in edges:
        print("FAIL: repeated concept slug produced no revisit edge")
        return 1
    print("FIXTURE CORPUS OK: deterministic, digest pinned (%s), semantics hold"
          % hexd[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
