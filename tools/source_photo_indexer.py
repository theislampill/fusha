#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inventory the existing photographed Qamus corpus and map page coverage. READ-ONLY. No image bytes committed.

The corpus is a local, owner-provided photo set (env QAMUS_SOURCE_PHOTOS, e.g. C:\\workspace\\ai\\in\\qamus). This
indexes every image + parses the frontmatter page manifests to record which dictionary pages are covered, so the
rescue pipeline can decide per entry: photo PRESENT (visual-review) vs ABSENT (needs new photo) — instead of
blindly demanding 240 retakes. Writes qamus/indexes/source_photo_index.json (counts + page coverage; NO raw paths
beyond the corpus-relative folder/file names, which are not secret).
"""
import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.environ.get("QAMUS_SOURCE_PHOTOS")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--out", default=os.path.join(ROOT, "qamus", "indexes", "source_photo_index.json"))
    a = ap.parse_args()
    if not a.corpus or not os.path.isdir(a.corpus):
        ap.error("--corpus/QAMUS_SOURCE_PHOTOS must be an existing directory")

    images, folders = [], {}
    for dirpath, _, files in os.walk(a.corpus):
        rel = os.path.relpath(dirpath, a.corpus)
        c = 0
        for fn in files:
            if fn.lower().endswith(IMG_EXT):
                images.append(os.path.join(rel, fn).replace("\\", "/"))
                c += 1
        if c:
            folders[rel] = c

    # parse frontmatter page manifests for page coverage
    pages_present, pages_expected, pages_missing = set(), set(), set()
    manifests = []
    for mf in glob.glob(os.path.join(a.corpus, "**", "*manifest*.json"), recursive=True) + \
            glob.glob(os.path.join(a.corpus, "**", "frontmatter*remap*.json"), recursive=True):
        try:
            m = json.load(open(mf, encoding="utf-8"))
        except Exception:
            continue
        manifests.append(os.path.basename(mf))
        for k, dest in (("present_pages", pages_present), ("expected_pages", pages_expected),
                        ("missing_pages", pages_missing)):
            v = m.get(k)
            if isinstance(v, list):
                dest.update(str(x) for x in v)
            elif isinstance(v, dict):
                dest.update(str(x) for x in v)
    # page-numbered standalone files (pgNNN)
    import re
    pg_files = set()
    for img in images:
        mt = re.search(r"pg0*(\d{1,4})", img)
        if mt:
            pg_files.add(int(mt.group(1)))

    out = {
        "schema": "fusha/source-photo-index@1",
        "corpus_dir": os.path.basename(os.path.normpath(a.corpus)),
        "total_images": len(images),
        "folders": dict(sorted(folders.items(), key=lambda kv: -kv[1])),
        "manifests_parsed": manifests,
        "pages_present_from_manifests": sorted(pages_present, key=lambda x: (len(x), x)),
        "pages_expected_from_manifests": sorted(pages_expected, key=lambda x: (len(x), x)),
        "pages_missing_from_manifests": sorted(pages_missing, key=lambda x: (len(x), x)),
        "page_numbered_files": sorted(pg_files),
        "coverage_note": "corpus has %d images across %d folders; %d distinct page-numbers seen in filenames"
                         % (len(images), len(folders), len(pg_files)),
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"total_images": len(images), "folders": len(folders), "manifests": len(manifests),
                      "pages_present": len(pages_present), "pages_missing": len(pages_missing),
                      "page_numbered_files": len(pg_files)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
