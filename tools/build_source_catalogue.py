#!/usr/bin/env python3
"""SN0 — inventory the local sarf/nahw ingest corpus (APKG / PDF / DOCX).

Reads the corpus dir from ``SARFNAHW_CORPUS_DIR`` (see ``corpus_paths.py``) and
writes two *committed* artifacts (basenames + counts only — no raw paths, no
media, no copyrighted body text):

    corpora/sarfnahw/source_catalogue.json
    corpora/sarfnahw/SOURCE-CATALOGUE.md

Stdlib only except optional ``fitz`` (PyMuPDF) for PDF page counts; degrades to
``pypdf`` then to "unknown" if neither is present. APKG = zip(sqlite); DOCX =
zip(xml). No external file is mutated; raw sources are never copied into the repo.
"""
import os
import re
import io
import json
import zipfile
import sqlite3
import hashlib
import tempfile
import xml.etree.ElementTree as ET

from corpus_paths import corpus_dir, repo_root

OUT_DIR = os.path.join(repo_root(), "corpora", "sarfnahw")

TOPIC_HINTS = [
    ("verb_charts", ("verb-chart", "verb chart", "verb-table", "verb table", "conjugation")),
    ("vocabulary", ("vocab", "vocabulary", "comprehension")),
    ("nahw", ("nahw", "syntax", "i3rab", "iraab", "grammar", "sentence")),
    ("sarf", ("sarf", "morphology", "tasreef", "tasrif", "wazn", "pattern")),
    ("getting_used_to_arabic", ("getting-used-to-arabic", "getting used to arabic")),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_topic(name, extra=""):
    blob = (name + " " + extra).lower()
    hits = [topic for topic, keys in TOPIC_HINTS if any(k in blob for k in keys)]
    if not hits:
        return "mixed"
    if len(hits) == 1:
        return hits[0]
    return "mixed:" + "+".join(hits)


def pdf_pages(path):
    try:
        import fitz
        with fitz.open(path) as doc:
            n = doc.page_count
            txt = doc[0].get_text("text") if n else ""
            return n, ("text" if len(txt.strip()) > 20 else "image_or_sparse")
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        return len(r.pages), "unknown"
    except Exception:
        return None, "unknown"


def _open_apkg_db(zf):
    """Return (db_bytes, anki_filename, blocked_reason)."""
    names = zf.namelist()
    for cand in ("collection.anki21", "collection.anki2"):
        if cand in names:
            return zf.read(cand), cand, None
    if "collection.anki21b" in names:
        # zstd-compressed (newer Anki); needs the optional zstandard lib.
        try:
            import zstandard  # noqa: F401
            raw = zf.read("collection.anki21b")
            dctx = zstandard.ZstdDecompressor()
            return dctx.decompress(raw), "collection.anki21b", None
        except Exception as e:
            return None, "collection.anki21b", "zstd_decompress_failed:%s" % type(e).__name__
    return None, None, "no_collection_db_found"


def apkg_stats(path):
    out = {"notes": None, "cards": None, "models": None, "decks": None,
           "media": None, "db_file": None, "deck_names": [], "model_names": [],
           "blocked": None}
    try:
        with zipfile.ZipFile(path) as zf:
            db_bytes, dbfile, blocked = _open_apkg_db(zf)
            out["db_file"] = dbfile
            if blocked:
                out["blocked"] = blocked
            # media map (JSON: index -> original filename)
            if "media" in zf.namelist():
                try:
                    media = json.loads(zf.read("media").decode("utf-8") or "{}")
                    out["media"] = len(media)
                except Exception:
                    out["media"] = "unreadable"
            if db_bytes is None:
                return out
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp.write(db_bytes)
                tmppath = tmp.name
            try:
                con = sqlite3.connect(tmppath)
                cur = con.cursor()
                try:
                    out["notes"] = cur.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
                    out["cards"] = cur.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
                    row = cur.execute("SELECT models, decks FROM col LIMIT 1").fetchone()
                    if row:
                        try:
                            models = json.loads(row[0] or "{}")
                            out["models"] = len(models)
                            out["model_names"] = sorted({m.get("name", "") for m in models.values()})[:12]
                        except Exception:
                            pass
                        try:
                            decks = json.loads(row[1] or "{}")
                            out["decks"] = len(decks)
                            out["deck_names"] = sorted({d.get("name", "") for d in decks.values()
                                                        if d.get("name") and d.get("name") != "Default"})[:12]
                        except Exception:
                            pass
                except sqlite3.DatabaseError as e:
                    out["blocked"] = "sqlite:%s" % e
                finally:
                    con.close()
            finally:
                os.unlink(tmppath)
    except Exception as e:
        out["blocked"] = "%s:%s" % (type(e).__name__, e)
    return out


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_stats(path):
    out = {"paragraphs": None, "tables": None, "blocked": None}
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        out["paragraphs"] = sum(1 for _ in root.iter(_W + "p"))
        out["tables"] = sum(1 for _ in root.iter(_W + "tbl"))
    except Exception as e:
        out["blocked"] = "%s:%s" % (type(e).__name__, e)
    return out


def build():
    cdir = corpus_dir()
    if not os.path.isdir(cdir):
        raise SystemExit("corpus dir not found; set SARFNAHW_CORPUS_DIR (see tools/corpus_paths.py)")
    records = []
    for name in sorted(os.listdir(cdir)):
        path = os.path.join(cdir, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        rec = {
            "filename": name,
            "ext": ext,
            "size_bytes": os.path.getsize(path),
            "sha256": sha256_file(path),
            "kind": {"apkg": "anki_package", "pdf": "pdf", "docx": "docx"}.get(ext, ext),
            "raw_committed": False,
            "extraction_status": "pending",
            "source_review_status": "needs_review",
        }
        if ext == "pdf":
            n, kind = pdf_pages(path)
            rec["pages"] = n
            rec["pdf_text_kind"] = kind
            rec["topic"] = detect_topic(name)
            rec["safe_outputs"] = ["corpora/sarfnahw/pdf_catalogue.json",
                                   "corpora/sarfnahw/pdf_samples.jsonl"]
            rec["gitignored_full_output"] = "corpora/sarfnahw/out/pdf/"
        elif ext == "apkg":
            st = apkg_stats(path)
            rec.update({k: st[k] for k in ("notes", "cards", "models", "decks", "media", "db_file")})
            rec["topic"] = detect_topic(name, " ".join(st.get("deck_names", [])))
            rec["deck_names"] = st.get("deck_names", [])
            rec["model_names"] = st.get("model_names", [])
            if st.get("blocked"):
                rec["extraction_status"] = "blocked"
                rec["blocked_reason"] = st["blocked"]
            rec["safe_outputs"] = ["corpora/sarfnahw/apkg_catalogue.json",
                                   "corpora/sarfnahw/apkg_samples.jsonl"]
            rec["gitignored_full_output"] = "corpora/sarfnahw/out/apkg/"
        elif ext == "docx":
            st = docx_stats(path)
            rec.update(st)
            rec["topic"] = detect_topic(name)
            rec["safe_outputs"] = ["corpora/sarfnahw/pdf_catalogue.json (docx folded in)"]
            rec["gitignored_full_output"] = "corpora/sarfnahw/out/docx/"
            if st.get("blocked"):
                rec["extraction_status"] = "blocked"
                rec["blocked_reason"] = st["blocked"]
        else:
            rec["topic"] = "unknown"
        records.append(rec)

    summary = {
        "total_files": len(records),
        "by_ext": {},
        "apkg_notes_total": 0,
        "apkg_cards_total": 0,
        "apkg_media_total": 0,
        "pdf_pages_total": 0,
    }
    for r in records:
        summary["by_ext"][r["ext"]] = summary["by_ext"].get(r["ext"], 0) + 1
        if r["ext"] == "apkg":
            summary["apkg_notes_total"] += r.get("notes") or 0
            summary["apkg_cards_total"] += r.get("cards") or 0
            m = r.get("media")
            summary["apkg_media_total"] += m if isinstance(m, int) else 0
        if r["ext"] == "pdf":
            summary["pdf_pages_total"] += r.get("pages") or 0

    os.makedirs(OUT_DIR, exist_ok=True)
    doc = {"schema": "fusha/source_catalogue@1", "summary": summary, "files": records}
    with open(os.path.join(OUT_DIR, "source_catalogue.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    write_md(doc)
    print("WROTE source_catalogue.json + SOURCE-CATALOGUE.md  (%d files)" % len(records))
    print(json.dumps(summary, ensure_ascii=False))
    return doc


def write_md(doc):
    s = doc["summary"]
    lines = []
    lines.append("# Sarf/Nahw ingest corpus — SOURCE CATALOGUE (SN0)")
    lines.append("")
    lines.append("Local, uncommitted ingest corpus. **No raw APKG/PDF/DOCX, no media, no audio, no "
                 "copyrighted body text is committed** — only counts, checksums, and safe derived "
                 "samples. Raw files live in a git-ignored local dir (`SARFNAHW_CORPUS_DIR`).")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---:|")
    lines.append("| total files | %d |" % s["total_files"])
    for ext, n in sorted(s["by_ext"].items()):
        lines.append("| `.%s` files | %d |" % (ext, n))
    lines.append("| APKG notes (total) | %d |" % s["apkg_notes_total"])
    lines.append("| APKG cards (total) | %d |" % s["apkg_cards_total"])
    lines.append("| APKG media files (total, NOT committed) | %d |" % s["apkg_media_total"])
    lines.append("| PDF pages (total) | %d |" % s["pdf_pages_total"])
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("| file | type | size | detail | topic | extraction | source review | raw committed |")
    lines.append("|---|---|---:|---|---|---|---|---|")
    for r in doc["files"]:
        size = "%.2f MB" % (r["size_bytes"] / 1048576.0)
        if r["ext"] == "apkg":
            detail = "%s notes · %s cards · %s media" % (r.get("notes"), r.get("cards"), r.get("media"))
        elif r["ext"] == "pdf":
            detail = "%s pp · %s" % (r.get("pages"), r.get("pdf_text_kind"))
        elif r["ext"] == "docx":
            detail = "%s paras · %s tables" % (r.get("paragraphs"), r.get("tables"))
        else:
            detail = ""
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
            r["filename"], r["kind"], size, detail, r.get("topic", ""),
            r["extraction_status"], r["source_review_status"],
            "false" if not r["raw_committed"] else "true"))
    lines.append("")
    lines.append("## Acceptance (SN0)")
    lines.append("- All files in the ingest dir accounted for: **%d**." % s["total_files"])
    lines.append("- No raw large source file committed (gitignore blocks `*.apkg *.pdf *.docx *.zip` + media).")
    lines.append("- Catalogue committed; full extraction stays under git-ignored `corpora/sarfnahw/out/`.")
    lines.append("")
    lines.append("> Licensing: the AMAU decks and verb-chart PDFs are third-party teaching material; "
                 "their full text/media are **not** redistributed here. Internal linguistic *features* "
                 "(patterns, POS, root behaviour) are extracted for reuse; verbatim deck/chart content is not. "
                 "Each file is marked `source_review_status: needs_review` pending owner licensing confirmation.")
    with open(os.path.join(OUT_DIR, "SOURCE-CATALOGUE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    build()
