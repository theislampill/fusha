#!/usr/bin/env python3
"""Export the complete, PUBLIC-SAFE Qamus dataset from the live entry store.

Reads the authoritative live Qamus entry JSON store (one file per entry) and emits a
reusable, queryable, redistribution-safe baseline of every current entry, plus indexes,
a manifest, source-key map, checksums, and a report.

PUBLIC-SAFE CONTRACT (enforced here, re-checked by validate_current_qamus_dataset.py):
  KEEP   id, source_keys, root, root_translit, headword(lemma), translit, section(pos),
         category, definition, meaning, total_uses, tags, notes(public info-notes),
         senses[{n,ar,translit,gloss,count}], usage[{sense,forms,examples[{ar,en,ref}]}]
  STRIP  author_uid, author_name, last_edited_by, actor_type, created_at, updated_at,
         edit_count, version, versions, status, visibility, image, source, and any
         field not in the keep-list (forward-safe: unknown fields are dropped, logged).

This script NEVER writes to the live site. It only reads entry JSON. Run it server-side
(where the store lives) and pull the sanitized output dir into the Fusha repo.

Usage:
  QAMUS_ENTRIES_DIR=/srv/dawah-ops/hermes-workspace/qamus-service/entries \
  python3 export_current_qamus_dataset.py --out /tmp/qamus_export

Reproducible: same store -> byte-identical output (sorted keys, fixed separators).
"""
import argparse, glob, hashlib, json, os, re, sys, unicodedata
from collections import defaultdict, Counter

SCHEMA_VERSION = "qamus-entry-public/1.0"

# ---- normalization (copied verbatim from live qamus_wbw/normalize.py so the
#      by-normalized-surface index joins exactly to the hover key) --------------
def norm_strict(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ىٰ", "ى")  # alef-maqsura+dagger -> maqsura
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0652:  # harakat/tanwin/shadda/sukun
            continue
        if o == 0x0670:            # dagger alef -> full alef
            out.append("ا"); continue
        if o == 0x0640:            # tatweel
            continue
        if 0x0653 <= o <= 0x0655:  # madda / hamza above-below combining
            continue
        if 0x06D6 <= o <= 0x06ED:  # Qur'anic annotation signs
            continue
        out.append(ch)
    s = "".join(out)
    s = s.replace("آ", "ا").replace("ٱ", "ا")  # madda/wasla -> alef
    s = s.replace("ى", "ي").replace("ة", "ه").replace(" ", "")
    return s

def norm_lenient(s):
    """norm() from live: also drops hamza seats; for content-word root grouping."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ىٰ", "ى")
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0652: continue
        if o == 0x0670: out.append("ا"); continue
        if o == 0x0640: continue
        if 0x0653 <= o <= 0x0655: continue
        if 0x06D6 <= o <= 0x06ED: continue
        out.append(ch)
    s = "".join(out)
    s = s.replace("آ", "ا").replace("ٱ", "ا")
    s = s.replace("أ", "").replace("إ", "").replace("ء", "")
    s = s.replace("ؤ", "و").replace("ئ", "ي")
    s = s.replace("ى", "ي").replace("ة", "ه").replace(" ", "")
    return s

# ---- public-safe projection ---------------------------------------------------
KEEP_TOP = ("id","source_keys","root","root_translit","headword","translit",
            "section","category","definition","meaning","total_uses","tags","notes")
STRIP_TOP = {"author_uid","author_name","last_edited_by","actor_type","created_at",
             "updated_at","edit_count","version","versions","status","visibility",
             "image","source"}

def clean_sense(s):
    return {"n": s.get("n"), "ar": s.get("ar",""), "translit": s.get("translit",""),
            "gloss": s.get("gloss",""), "count": s.get("count")}

def clean_usage(u):
    exs = []
    for ex in (u.get("examples") or []):
        exs.append({"ar": ex.get("ar",""), "en": ex.get("en",""), "ref": ex.get("ref","")})
    return {"sense": u.get("sense"), "forms": list(u.get("forms") or []), "examples": exs}

def project(d, dropped):
    out = {}
    for k in KEEP_TOP:
        if k in d:
            out[k] = d[k]
    out["senses"] = [clean_sense(s) for s in (d.get("senses") or [])]
    out["usage"] = [clean_usage(u) for u in (d.get("usage") or [])]
    for k in d:
        if k not in KEEP_TOP and k not in STRIP_TOP and k not in ("senses","usage"):
            dropped[k] += 1  # unknown -> dropped (forward-safe), logged
    return out

# ---- quran ref parsing for by-quran-ref ---------------------------------------
REF_RE = re.compile(r"^\s*(\d+):(\d+)")
def ref_sa(ref):
    m = REF_RE.match(str(ref or ""))
    return f"{int(m.group(1))}:{int(m.group(2))}" if m else None

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def jdump(obj, path, **kw):
    # reviewer-facing: pretty (indent=2, sort_keys, ensure_ascii=False, trailing newline) — A1 ergonomics
    kw.pop("indent", None)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2, **kw)
        f.write("\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", default=os.environ.get("QAMUS_ENTRIES_DIR",
                    "/srv/dawah-ops/hermes-workspace/qamus-service/entries"))
    ap.add_argument("--out", default=os.environ.get("QAMUS_EXPORT_OUT", "/tmp/qamus_export"))
    args = ap.parse_args()

    data_dir = os.path.join(args.out, "data")
    idx_dir = os.path.join(args.out, "indexes")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(idx_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(args.entries, "*.json")))
    if not files:
        print("FATAL: no entries found at", args.entries); sys.exit(2)

    entries = []
    dropped = Counter()
    by_entry_id = {}
    by_source_key = defaultdict(list)
    by_root = defaultdict(list)
    by_lemma = defaultdict(list)
    by_norm = defaultdict(list)
    by_quran_ref = defaultdict(list)
    by_category = defaultdict(list)
    by_section = defaultdict(list)
    leak_hits = []
    LEAK_PAT = re.compile(r"(/srv/|/tmp/|/home/|/var/www|author_uid|@gmail|@dawah|password|\bsid\b)", re.I)

    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        pub = project(d, dropped)
        eid = pub.get("id") or os.path.splitext(os.path.basename(f))[0]
        pub["id"] = eid
        entries.append(pub)
        # leak sweep on the projected public object only
        blob = json.dumps(pub, ensure_ascii=False)
        if LEAK_PAT.search(blob):
            leak_hits.append(eid)
        # indexes
        by_entry_id[eid] = {
            "headword": pub.get("headword",""), "root": pub.get("root",""),
            "section": pub.get("section",""), "category": pub.get("category",""),
            "source_keys": pub.get("source_keys",[]),
            "n_senses": len(pub.get("senses",[])),
            "n_examples": sum(len(u.get("examples",[])) for u in pub.get("usage",[])),
            "total_uses": pub.get("total_uses"),
        }
        for sk in pub.get("source_keys") or []:
            by_source_key[sk].append(eid)
        root = (pub.get("root") or "").strip()
        if root:
            by_root[root].append(eid)
        hw = (pub.get("headword") or "").strip()
        if hw:
            by_lemma[hw].append(eid)
            nk = norm_strict(hw)
            if nk:
                by_norm[nk].append(eid)
        sec = pub.get("section") or "?"
        by_section[sec].append(eid)
        cat = pub.get("category") or "?"
        by_category[cat].append(eid)
        seen_refs = set()
        for u in pub.get("usage") or []:
            for ex in u.get("examples") or []:
                sa = ref_sa(ex.get("ref"))
                if sa and sa not in seen_refs:
                    by_quran_ref[sa].append(eid); seen_refs.add(sa)

    entries.sort(key=lambda e: e["id"])

    # ---- data/current outputs ----
    full_path = os.path.join(data_dir, "entries.jsonl")
    with open(full_path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    min_path = os.path.join(data_dir, "entries.min.jsonl")
    with open(min_path, "w", encoding="utf-8") as f:
        for e in entries:
            m = {"id": e["id"], "headword": e.get("headword",""), "root": e.get("root",""),
                 "section": e.get("section",""), "translit": e.get("translit",""),
                 "gloss": e.get("definition",""),
                 "n_examples": sum(len(u.get("examples",[])) for u in e.get("usage",[]))}
            f.write(json.dumps(m, ensure_ascii=False, sort_keys=True) + "\n")

    # source-keys.json: map + uniqueness report
    dup_sk = {k: v for k, v in by_source_key.items() if len(v) > 1}
    src_keys_obj = {
        "source_key_to_entries": {k: sorted(v) for k, v in sorted(by_source_key.items())},
        "total_source_keys": len(by_source_key),
        "unique": len(dup_sk) == 0,
        "duplicates": {k: sorted(v) for k, v in sorted(dup_sk.items())},
        "entries_without_source_key": sorted(
            e["id"] for e in entries if not e.get("source_keys")),
    }
    jdump(src_keys_obj, os.path.join(data_dir, "source-keys.json"), indent=0)

    # indexes
    jdump(by_entry_id, os.path.join(idx_dir, "by-entry-id.json"))
    jdump({k: sorted(set(v)) for k,v in by_source_key.items()}, os.path.join(idx_dir, "by-source-key.json"))
    jdump({k: sorted(set(v)) for k,v in by_root.items()}, os.path.join(idx_dir, "by-root.json"))
    jdump({k: sorted(set(v)) for k,v in by_lemma.items()}, os.path.join(idx_dir, "by-lemma.json"))
    jdump({k: sorted(set(v)) for k,v in by_norm.items()}, os.path.join(idx_dir, "by-normalized-surface.json"))
    jdump({k: sorted(set(v)) for k,v in by_quran_ref.items()}, os.path.join(idx_dir, "by-quran-ref.json"))
    jdump({"by_category": {k: sorted(set(v)) for k,v in by_category.items()},
           "by_section": {k: sorted(set(v)) for k,v in by_section.items()}},
          os.path.join(idx_dir, "by-category.json"))

    # manifest
    n_examples = sum(b["n_examples"] for b in by_entry_id.values())
    manifest = {
        "schema": SCHEMA_VERSION,
        "generator": "tools/export_current_qamus_dataset.py",
        "entry_count": len(entries),
        "section_counts": {k: len(v) for k, v in sorted(by_section.items())},
        "category_count": len(by_category),
        "total_senses": sum(len(e.get("senses",[])) for e in entries),
        "total_usage_blocks": sum(len(e.get("usage",[])) for e in entries),
        "total_examples": n_examples,
        "distinct_quran_refs": len(by_quran_ref),
        "distinct_roots": len(by_root),
        "distinct_lemmas": len(by_lemma),
        "distinct_norm_surfaces": len(by_norm),
        "scope": {"status": "reviewed (all)", "visibility": "public (all)"},
        "dropped_unknown_fields": dict(dropped),
        "files": ["data/entries.jsonl","data/entries.min.jsonl","data/source-keys.json",
                  "indexes/by-entry-id.json","indexes/by-source-key.json","indexes/by-root.json",
                  "indexes/by-lemma.json","indexes/by-normalized-surface.json",
                  "indexes/by-quran-ref.json","indexes/by-category.json"],
    }
    jdump(manifest, os.path.join(data_dir, "entry-manifest.json"), indent=1)

    # checksums (over the produced files)
    checksums = {}
    for rel in manifest["files"] + ["data/entry-manifest.json"]:
        p = os.path.join(args.out, rel)
        if os.path.exists(p):
            checksums[rel] = {"sha256": sha256_file(p), "bytes": os.path.getsize(p)}
    jdump(checksums, os.path.join(data_dir, "checksums.json"), indent=1)

    print("EXPORT OK")
    print("entries:", len(entries), "examples:", n_examples,
          "refs:", len(by_quran_ref), "roots:", len(by_root))
    print("sections:", manifest["section_counts"])
    print("dropped unknown fields:", dict(dropped))
    print("source_keys unique:", src_keys_obj["unique"],
          "duplicates:", len(dup_sk), "no-key entries:", len(src_keys_obj["entries_without_source_key"]))
    print("LEAK HITS in public objects:", len(leak_hits), leak_hits[:5])
    if leak_hits:
        print("FATAL: leak detected in projected public data"); sys.exit(3)

if __name__ == "__main__":
    main()
