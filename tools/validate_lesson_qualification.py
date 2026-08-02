#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the per-module lesson-qualification records produced by the
clean-room worker lanes (curriculum/l1l6/qualification/*.jsonl).

Named fail-closed checks:
- schema/id shape, one record per expected lesson, no duplicates
- every lesson of the registry covered exactly once across all files
  (--complete mode; per-file mode validates only what exists)
- closed vocabularies (proposition status, contribution_kind,
  capability_family, repository_destination)
- redundancy honesty: contribution_kind=redundant REQUIRES equivalence_basis
- learner-error honesty: lessons whose registry row counts >=1 mistake
  section MUST carry >=1 common_mistakes entry
- custody: no Arabic run over 4 words anywhere in any string; no
  server/absolute paths
- unit references resolve against units/instructional-units.jsonl

Usage:
  python tools/validate_lesson_qualification.py            # all files present
  python tools/validate_lesson_qualification.py --complete # + 226/226 gate
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"
QDIR = BASE / "qualification"

STATUSES = {"source-supported-not-executable", "pedagogical-simplification",
            "analysis-dependent", "school-dependent",
            "candidate-requiring-review",
            "contradicted-by-repository-authority",
            "unsafe-for-automatic-projection"}
KINDS = {"new_material", "expands_unit", "new_exceptions", "new_contrasts",
         "new_error_patterns", "new_sequencing", "new_paradigms",
         "redundant", "instructional_only"}
CAPS = {"letter_ownership", "template_classification", "discriminator_table",
        "pattern_consistency", "licensing_table", "instructional_only"}
DESTS = {"units", "increments", "misconceptions", "paradigm-units",
         "exercise-templates", "instructional-methods"}
AR_WORD_RE = re.compile(r"[؀-ۿ][؀-ۿـً-ْٰ]*")
# a RUN is Arabic words separated only by spaces/Arabic commas — English text
# between terms breaks the run (the custody rule is 4 CONSECUTIVE words; an
# inventory of single terms with English connectors is not prose)
AR_RUN_RE = re.compile(r"[؀-ۿ][؀-ۿـً-ْٰ]*(?:[\s،,]+[؀-ۿ][؀-ۿـً-ْٰ]*)*")
SERVER_RE = re.compile(r"(?:/srv/|/var/www|/home/[a-z]|[A-Za-z]:\\)")


def max_arabic_run(s):
    best = 0
    for m in AR_RUN_RE.finditer(s):
        best = max(best, len(AR_WORD_RE.findall(m.group(0))))
    return best
LESSON_RE = re.compile(r"^L[1-6]\.M\d+\.\d{2}$")


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def main(argv):
    errors = []
    lessons = {json.loads(l)["lesson_id"]: json.loads(l) for l in
               (BASE / "registry" / "lessons.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()}
    unit_ids = {json.loads(l)["unit_id"] for l in
                (BASE / "units" / "instructional-units.jsonl").read_text(encoding="utf-8").splitlines()
                if l.strip()}
    seen = {}
    files = sorted(QDIR.glob("L*.jsonl"))
    for f in files:
        try:
            rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        except ValueError as exc:
            errors.append("%s: unparseable (%s)" % (f.name, exc))
            continue
        for r in rows:
            lid = r.get("lesson_id")
            if not (isinstance(lid, str) and LESSON_RE.fullmatch(lid)):
                errors.append("%s: bad lesson_id %r" % (f.name, lid))
                continue
            if lid in seen:
                errors.append("%s: duplicate qualification for %s (also in %s)"
                              % (f.name, lid, seen[lid]))
            seen[lid] = f.name
            if lid not in lessons:
                errors.append("%s: %s not a registry lesson" % (f.name, lid))
                continue
            if not r.get("inspected"):
                errors.append("%s: %s not marked inspected" % (f.name, lid))
            for p in r.get("linguistic_propositions") or []:
                if p.get("status") not in STATUSES:
                    errors.append("%s: %s proposition status %r invalid"
                                  % (f.name, lid, p.get("status")))
            um = r.get("unit_mapping") or {}
            kind = um.get("contribution_kind")
            if kind not in KINDS:
                errors.append("%s: %s contribution_kind %r invalid"
                              % (f.name, lid, kind))
            if kind == "redundant" and not um.get("equivalence_basis"):
                errors.append("%s: %s redundant without equivalence_basis"
                              % (f.name, lid))
            for u in um.get("existing_units") or []:
                if u not in unit_ids:
                    errors.append("%s: %s cites unknown unit %r" % (f.name, lid, u))
            for pu in um.get("proposed_new_units") or []:
                if pu.get("capability_family") not in CAPS:
                    errors.append("%s: %s proposed unit capability %r invalid"
                                  % (f.name, lid, pu.get("capability_family")))
                if not str(pu.get("proposed_id", "")).startswith("cu-"):
                    errors.append("%s: %s proposed unit id %r must start cu-"
                                  % (f.name, lid, pu.get("proposed_id")))
            if r.get("repository_destination") not in DESTS:
                errors.append("%s: %s repository_destination %r invalid"
                              % (f.name, lid, r.get("repository_destination")))
            if (lessons[lid]["counts"]["common_mistakes_sections"] >= 1
                    and not (r.get("common_mistakes"))):
                errors.append("%s: %s has a source error section but no "
                              "common_mistakes entries" % (f.name, lid))
            for s in _walk_strings(r):
                if max_arabic_run(s) > 4:
                    errors.append("%s: %s Arabic run >4 consecutive words "
                                  "(custody): %r" % (f.name, lid, s[:60]))
                    break
                if SERVER_RE.search(s):
                    errors.append("%s: %s server/absolute path leak" % (f.name, lid))
                    break
    if "--complete" in argv:
        missing = sorted(set(lessons) - set(seen))
        for lid in missing:
            errors.append("complete: lesson %s has NO qualification record" % lid)
        print("coverage: %d/%d lessons qualified across %d files"
              % (len(seen), len(lessons), len(files)))
    for e in errors[:60]:
        print("FAIL " + e)
    if len(errors) > 60:
        print("... and %d more" % (len(errors) - 60))
    if errors:
        print("LESSON QUALIFICATION VALIDATION FAIL (%d)" % len(errors))
        return 1
    print("LESSON QUALIFICATION VALIDATION PASS (%d records, %d files)"
          % (len(seen), len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
