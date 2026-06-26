#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Qamus public/private provenance boundary objects.

This is the reusable Phase 2 gate for the public hover boundary used by
decision-linkage, hover-edit-intent, repair-impact-preview, and live-shadow
manifest artifacts. It does not inspect or mutate live Qamus.
"""
import argparse
import io
import json
import os
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "qamus", "schemas", "public-private-boundary.schema.json")
SAMPLE_PATH = os.path.join(ROOT, "qamus", "examples", "public_private_boundary.sample.json")

import sys
sys.path.insert(0, ROOT)
from tools.validate_linguistic_decisions import validate_schema  # noqa: E402

FORBIDDEN_LABELS = (
    "informed_by",
    "mcp",
    "qac",
    "quran.com",
    "quran_com",
    "corpus.quran",
    "tanzil",
    "tafsir",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "c:\\",
    "root.txt",
)
EXPECTED = {
    "src": "qamus",
    "kind": "authored",
    "lang": "en",
    "external_source_names_public": False,
    "internal_provenance_public": False,
}


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def validate_boundary(row):
    errors = []
    if not isinstance(row, dict):
        return ["boundary must be a JSON object"]
    schema_errors = validate_schema(SCHEMA_PATH, row)
    errors.extend(schema_errors)
    for key, value in EXPECTED.items():
        if row.get(key) != value:
            errors.append("%s must be %r" % (key, value))
    for field in ("public_fields", "private_fields"):
        value = row.get(field) or []
        if value and not isinstance(value, list):
            errors.append("%s must be an array when present" % field)
            continue
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                errors.append("%s[%d] must be a nonempty string" % (field, index))
    public_blob = json.dumps({
        "src": row.get("src"),
        "kind": row.get("kind"),
        "lang": row.get("lang"),
        "public_fields": row.get("public_fields") or [],
        "external_source_names_public": row.get("external_source_names_public"),
        "internal_provenance_public": row.get("internal_provenance_public"),
    }, ensure_ascii=False).lower()
    for label in FORBIDDEN_LABELS:
        if label in public_blob:
            errors.append("public boundary leaks forbidden label %r" % label)
    return errors


def self_test():
    with tempfile.TemporaryDirectory(prefix="public-private-boundary-") as td:
        good = read_json(SAMPLE_PATH)
        good_path = os.path.join(td, "good.json")
        write_json(good_path, good)
        errors = validate_boundary(read_json(good_path))
        if errors:
            print("SELF-TEST FAIL good:", errors)
            return 1

        bad_lang = dict(good)
        bad_lang["lang"] = "ar"
        errors = validate_boundary(bad_lang)
        if not any("lang" in err for err in errors):
            print("SELF-TEST FAIL lang:", errors)
            return 1

        bad_public = dict(good)
        bad_public["public_fields"] = list(good["public_fields"]) + ["informed_by"]
        errors = validate_boundary(bad_public)
        if not any("forbidden label" in err for err in errors):
            print("SELF-TEST FAIL public leak:", errors)
            return 1

        bad_private_flag = dict(good)
        bad_private_flag["internal_provenance_public"] = True
        errors = validate_boundary(bad_private_flag)
        if not any("internal_provenance_public" in err for err in errors):
            print("SELF-TEST FAIL private flag:", errors)
            return 1
    print("PASS — public/private boundary validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate Qamus public/private boundary JSON.")
    parser.add_argument("path", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.path:
        parser.error("path is required unless --self-test is used")
    errors = validate_boundary(read_json(args.path))
    if errors:
        print("FAIL:")
        for err in errors[:80]:
            print("  - " + err)
        raise SystemExit(1)
    print("PASS — public/private boundary is qamus-authored and provenance-clean")


if __name__ == "__main__":
    main()
