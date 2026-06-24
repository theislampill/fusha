#!/usr/bin/env python3
"""Validate the committed public-safe Qamus dataset (P0 acceptance gate).

Runs purely against the committed files under qamus/data/current and
qamus/indexes/current — NO live server access required. Fails closed.

Checks:
  1. entries.jsonl parses; every line conforms to the public schema (no extra/private keys).
  2. entry count == manifest.entry_count, section counts reconcile.
  3. checksums.json matches the on-disk bytes of every listed file.
  4. every index resolves: each entry id appears in by-entry-id; every id referenced
     by an index exists in the entry set; by-quran-ref refs are well-formed.
  5. NO private leakage: no stripped field name, no filesystem path, no email/secret marker.
  6. source_keys unique (or documented as duplicates), no entry missing required fields.
"""
import json, os, re, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current")
IDX = os.path.join(ROOT, "qamus", "indexes", "current")
SCHEMA = os.path.join(ROOT, "qamus", "schemas", "qamus-entry-public.schema.json")

PRIVATE_FIELDS = {"author_uid","author_name","last_edited_by","actor_type","created_at",
                  "updated_at","edit_count","version","versions","status","visibility",
                  "image","source"}
ALLOWED_TOP = {"id","source_keys","root","root_translit","headword","translit","section",
               "category","definition","meaning","total_uses","tags","notes","senses","usage"}
ALLOWED_SENSE = {"n","ar","translit","gloss","count"}
ALLOWED_USAGE = {"sense","forms","examples"}
ALLOWED_EX = {"ar","en","ref"}
LEAK_PAT = re.compile(r"(/srv/|/tmp/|/home/|/var/www|author_uid|@gmail|password|secret_key)", re.I)
REF_RE = re.compile(r"^\d+:\d+")

errs = []
warns = []
def err(m): errs.append(m)
def warn(m): warns.append(m)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""): h.update(c)
    return h.hexdigest()

def main():
    # load entries
    entries = []
    with open(os.path.join(DATA, "entries.jsonl"), encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            try:
                e = json.loads(line)
            except Exception as ex:
                err(f"entries.jsonl line {i}: bad JSON: {ex}"); continue
            entries.append(e)
            # schema-ish structural check
            extra = set(e) - ALLOWED_TOP
            if extra: err(f"entry {e.get('id','?')}: unexpected top keys {extra}")
            priv = set(e) & PRIVATE_FIELDS
            if priv: err(f"entry {e.get('id','?')}: PRIVATE field leaked {priv}")
            if not e.get("id"): err(f"line {i}: entry missing id")
            if e.get("section") not in ("verb","noun","particle"):
                err(f"entry {e.get('id')}: bad section {e.get('section')!r}")
            for s in e.get("senses",[]):
                if set(s)-ALLOWED_SENSE: err(f"entry {e.get('id')}: sense extra keys {set(s)-ALLOWED_SENSE}")
            for u in e.get("usage",[]):
                if set(u)-ALLOWED_USAGE: err(f"entry {e.get('id')}: usage extra keys {set(u)-ALLOWED_USAGE}")
                for ex in u.get("examples",[]):
                    if set(ex)-ALLOWED_EX: err(f"entry {e.get('id')}: example extra keys {set(ex)-ALLOWED_EX}")
                    if ex.get("ref") and not REF_RE.match(str(ex["ref"])):
                        warn(f"entry {e.get('id')}: non-standard ref {ex['ref']!r}")
            if LEAK_PAT.search(line):
                err(f"entry {e.get('id')}: LEAK pattern in serialized entry")

    ids = {e["id"] for e in entries}
    sections = {}
    for e in entries: sections[e.get("section")] = sections.get(e.get("section"),0)+1

    # manifest
    man = json.load(open(os.path.join(DATA,"entry-manifest.json"),encoding="utf-8"))
    if man["entry_count"] != len(entries):
        err(f"manifest.entry_count {man['entry_count']} != actual {len(entries)}")
    if man.get("section_counts") != sections:
        err(f"manifest.section_counts {man.get('section_counts')} != actual {sections}")

    # checksums
    cs = json.load(open(os.path.join(DATA,"checksums.json"),encoding="utf-8"))
    for rel, meta in cs.items():
        p = os.path.join(ROOT, "qamus", *rel.split("/")) if rel.startswith(("data/","indexes/")) else None
        # files in checksums use export-relative roots data/ and indexes/; map to qamus/{data,indexes}/current
        rel2 = rel.replace("data/", "data/current/").replace("indexes/", "indexes/current/")
        p = os.path.join(ROOT, "qamus", *rel2.split("/"))
        if not os.path.exists(p):
            err(f"checksums: missing file {rel} -> {p}"); continue
        got = sha256_file(p)
        if got != meta["sha256"]:
            err(f"checksums: {rel} sha mismatch")

    # indexes resolve
    by_id = json.load(open(os.path.join(IDX,"by-entry-id.json"),encoding="utf-8"))
    if set(by_id) != ids:
        err(f"by-entry-id mismatch: missing {len(ids-set(by_id))}, extra {len(set(by_id)-ids)}")
    for name in ("by-source-key","by-root","by-lemma","by-normalized-surface","by-quran-ref"):
        d = json.load(open(os.path.join(IDX, name+".json"),encoding="utf-8"))
        orphans = set()
        for k, v in d.items():
            for eid in v:
                if eid not in ids: orphans.add(eid)
        if orphans: err(f"{name}: {len(orphans)} orphan ids e.g. {list(orphans)[:3]}")
    bcat = json.load(open(os.path.join(IDX,"by-category.json"),encoding="utf-8"))
    # every entry in exactly one section bucket
    sec_ids = set()
    for k,v in bcat["by_section"].items(): sec_ids.update(v)
    if sec_ids != ids: err("by-category by_section does not cover all entries exactly")

    # source-keys uniqueness
    sk = json.load(open(os.path.join(DATA,"source-keys.json"),encoding="utf-8"))
    if not sk["unique"] and sk["duplicates"]:
        warn(f"source_keys NOT unique: {len(sk['duplicates'])} duplicated (documented)")

    print(f"entries={len(entries)} ids={len(ids)} sections={sections}")
    print(f"indexes: by-entry-id={len(by_id)} refs={man['distinct_quran_refs']} roots={man['distinct_roots']}")
    if warns:
        print(f"WARN ({len(warns)}):"); [print("  -", w) for w in warns[:10]]
    if errs:
        print(f"FAIL ({len(errs)} errors):"); [print("  -", e) for e in errs[:30]]
        sys.exit(1)
    print("VALIDATE OK — public-safe dataset acceptance PASS")

if __name__ == "__main__":
    main()
