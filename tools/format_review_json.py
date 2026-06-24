#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reviewer-facing JSON formatting helpers + CLI (artifact ergonomics, A1).

Reviewer-facing JSON must be: indent=2, sort_keys=True, ensure_ascii=False, trailing newline.
Large row-record artifacts should be JSONL (one record per line) so each row diffs independently.

Library:
  dump_review(obj, path)        write pretty reviewer JSON (indent=2, sort_keys, ensure_ascii=False, \n)
  dump_min(obj, path)           write compact .min.json (single line, for machine/checksum use)
  dump_jsonl(rows, path)        write one JSON record per line (sorted keys, ensure_ascii=False)
  dict_to_jsonl(d, key_field, path, meta=None)
                                turn {k: v} into JSONL rows {key_field: k, **v}; optional .meta.json sidecar

CLI:
  python3 tools/format_review_json.py pretty  <file.json> [file.json ...]
  python3 tools/format_review_json.py to-jsonl <file.json> <key_field> [--wrapper KEY]
"""
import argparse, json, os, sys

def dump_review(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")

def dump_min(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        f.write("\n")

def dump_jsonl(rows, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

def dict_to_jsonl(d, key_field, path, meta=None):
    rows = []
    for k in sorted(d):
        v = d[k]
        row = {key_field: k}
        if isinstance(v, dict):
            row.update(v)
        else:
            row["value"] = v
        rows.append(row)
    dump_jsonl(rows, path)
    if meta is not None:
        dump_review(meta, os.path.splitext(path)[0] + ".meta.json")
    return len(rows)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pretty"); p.add_argument("files", nargs="+")
    j = sub.add_parser("to-jsonl"); j.add_argument("file"); j.add_argument("key_field"); j.add_argument("--wrapper")
    a = ap.parse_args()
    if a.cmd == "pretty":
        for fp in a.files:
            obj = json.load(open(fp, encoding="utf-8"))
            dump_review(obj, fp)
            print("pretty:", fp)
    elif a.cmd == "to-jsonl":
        obj = json.load(open(a.file, encoding="utf-8"))
        body = obj[a.wrapper] if a.wrapper else obj
        meta = {k: v for k, v in obj.items() if k != a.wrapper} if a.wrapper else None
        out = os.path.splitext(a.file)[0] + ".jsonl"
        n = dict_to_jsonl(body, a.key_field, out, meta)
        print("jsonl:", out, n, "rows; meta sidecar written" if meta else "")

if __name__ == "__main__":
    main()
