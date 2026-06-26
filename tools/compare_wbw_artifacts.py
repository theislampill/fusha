#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare two WBW lookup artifacts without reconciling them."""
import argparse
import hashlib
import io
import json
import os
import sys
import tempfile


def sha256(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_records(obj):
    if isinstance(obj, dict) and isinstance(obj.get("words"), dict):
        for loc, row in obj["words"].items():
            yield loc, row
        return
    if isinstance(obj, dict) and isinstance(obj.get("records"), list):
        for row in obj["records"]:
            loc = row.get("loc") or row.get("quran_loc")
            if loc:
                yield loc, row
        return
    if isinstance(obj, dict) and isinstance(obj.get("verses"), dict):
        for ayah, words in obj["verses"].items():
            if isinstance(words, list):
                for i, row in enumerate(words, 1):
                    yield "%s:%d" % (ayah, i), row
            elif isinstance(words, dict):
                for k, row in words.items():
                    loc = str(k) if str(k).count(":") == 2 else "%s:%s" % (ayah, k)
                    yield loc, row


def rich_count(records):
    return sum(1 for _loc, row in records.items() if isinstance(row, dict) and (row.get("parse_key") or row.get("display") or row.get("segments")))


def metadata(obj):
    if isinstance(obj, dict):
        for key in ("_meta", "meta"):
            if isinstance(obj.get(key), dict):
                return obj[key]
    return {}


def meta_value(obj, key):
    meta = metadata(obj)
    return meta.get(key) if isinstance(meta, dict) else None


def compare(live_path, mirror_path):
    live = load(live_path)
    mirror = load(mirror_path)
    live_records = dict(iter_records(live))
    mirror_records = dict(iter_records(mirror))
    live_locs = set(live_records)
    mirror_locs = set(mirror_records)
    common = live_locs & mirror_locs
    changed = sorted(loc for loc in common if live_records[loc] != mirror_records[loc])
    result = {
        "live": {
            "path": live_path,
            "sha256": sha256(live_path),
            "size": os.path.getsize(live_path),
            "source_sha": meta_value(live, "source_sha") or live.get("source_sha"),
            "built_at": meta_value(live, "built_at") or live.get("built_at"),
            "coverage": meta_value(live, "coverage") or meta_value(live, "coverage_counts"),
            "records": len(live_records),
            "rich_records": rich_count(live_records),
        },
        "mirror": {
            "path": mirror_path,
            "sha256": sha256(mirror_path),
            "size": os.path.getsize(mirror_path),
            "source_sha": meta_value(mirror, "source_sha") or mirror.get("source_sha"),
            "built_at": meta_value(mirror, "built_at") or mirror.get("built_at"),
            "coverage": meta_value(mirror, "coverage") or meta_value(mirror, "coverage_counts"),
            "records": len(mirror_records),
            "rich_records": rich_count(mirror_records),
        },
        "added_in_live": len(live_locs - mirror_locs),
        "removed_from_live": len(mirror_locs - live_locs),
        "changed_common_token_locs": len(changed),
        "changed_samples": changed[:20],
    }
    if result["added_in_live"] == result["removed_from_live"] == result["changed_common_token_locs"] == 0:
        if result["live"]["sha256"] == result["mirror"]["sha256"]:
            result["classification"] = "content-and-metadata-identical"
        else:
            result["classification"] = "content-equivalent-or-near-equivalent; metadata/source-hash divergent; not safe for mutation until separately reconciled"
    else:
        result["classification"] = "content-divergent; manual review required"
    return result


def self_test():
    with tempfile.TemporaryDirectory(prefix="wbw-compare-") as td:
        a = os.path.join(td, "a.json")
        b = os.path.join(td, "b.json")
        with io.open(a, "w", encoding="utf-8") as handle:
            json.dump({"_meta": {"source_sha": "a", "coverage": {"resolved": 1}}, "words": {"1:1:1": {"gloss": "one"}}}, handle)
        with io.open(b, "w", encoding="utf-8") as handle:
            json.dump({"_meta": {"source_sha": "b", "coverage": {"resolved": 1}}, "words": {"1:1:1": {"gloss": "one"}}}, handle)
        same_rows = compare(a, b)
        if same_rows["changed_common_token_locs"] != 0 or "metadata/source-hash divergent" not in same_rows["classification"]:
            print("SELF-TEST FAIL: metadata-only divergence not classified")
            return 1
        if same_rows["live"]["source_sha"] != "a" or same_rows["live"]["coverage"] != {"resolved": 1}:
            print("SELF-TEST FAIL: _meta source/coverage not read")
            return 1
        with io.open(b, "w", encoding="utf-8") as handle:
            json.dump({"_meta": {"source_sha": "b"}, "words": {"1:1:1": {"gloss": "two"}}}, handle)
        changed = compare(a, b)
        if changed["changed_common_token_locs"] != 1:
            print("SELF-TEST FAIL: changed token row not detected")
            return 1
    print("PASS — WBW artifact compare self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("live", nargs="?")
    parser.add_argument("mirror", nargs="?")
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.live or not args.mirror:
        parser.error("live and mirror artifact paths are required unless --self-test is used")
    result = compare(args.live, args.mirror)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
    print(text)
    if result["classification"].startswith("content-divergent"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
