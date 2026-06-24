#!/usr/bin/env python3
"""SN2 — extract the verb-chart PDFs + verb-tables DOCX (structure + English only).

The fatwa-online.com (1995) verb charts embed Arabic in a NON-Unicode legacy
font: the Arabic glyphs are not text-extractable (they decode to mojibake), and
this tool DOES NOT OCR them. What it reliably extracts is the *paradigm
structure* — the English slot labels (past/present active+passive, command,
maṣdar, ism fāʿil, ism mafʿūl, negations), the form markers (I–XV), image counts,
and provenance. That structure is a *fact*; the canonical Arabic wazn patterns are
authored separately (``sarf/rules/verb-measures.json``) from standard morphology,
with these charts recorded only as an internal ``informed_by`` reference.

Full text dump -> git-ignored ``corpora/sarfnahw/out/pdf|docx/``.
Committed: ``pdf_catalogue.json`` + ``pdf_samples.jsonl`` (English labels only).
"""
import os
import re
import sys
import json
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_paths import corpus_dir, repo_root           # noqa: E402
import text_extract as T                                 # noqa: E402

OUT_PDF = os.path.join(repo_root(), "corpora", "sarfnahw", "out", "pdf")
OUT_DOCX = os.path.join(repo_root(), "corpora", "sarfnahw", "out", "docx")
OUT_DIR = os.path.join(repo_root(), "corpora", "sarfnahw")

# canonical paradigm slots (the schema the charts encode), matched on English
SLOTS = [
    ("past_active", r"\bhe\s+\w+ed\b|\bPast\b.*Known|\bhe wrote\b|\bhe taught\b|\bhe shook\b|\bhe rolled\b"),
    ("past_passive", r"It was \w+|Past.*Unknown|it was written"),
    ("present_active", r"he [Ii]s \w+ing|he is teaching|Present/Future.*Known"),
    ("present_passive", r"it is (being )?\w+|Present/Future.*Unknown"),
    ("negation_future", r"Negating.*Future|will\s+not\s+\w+"),
    ("negation_past", r"Negating.*Past|has not \w+"),
    ("imperative", r"Command|/Order|write!|teach!|shake!|roll!"),
    ("masdar", r"Verbal (idea|noun)|form of a noun"),
    ("ism_fa3il", r"Person who|does act|responsible for it"),
    ("ism_maf3ul", r"Person/thing|action intended|towards which"),
]
ROMAN = re.compile(r"^\s*(II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\s*$")
PROV = re.compile(r"fatwa-?online|efatwa|Hans|Wehr|First prepared|199[0-9]", re.I)


def is_clean_en(s):
    return bool(re.search(r"[A-Za-z]", s)) and not re.search(r"[^\x09-\x7e]", s)


def extract_pdf(path):
    import fitz
    doc = fitz.open(path)
    pages, imgs, full = doc.page_count, 0, []
    en_lines, forms, prov = set(), set(), set()
    arabic_unicode_chars = 0
    for pg in doc:
        imgs += len(pg.get_images())
        txt = pg.get_text("text")
        full.append(txt)
        arabic_unicode_chars += sum(1 for c in txt if T._AR.match(c))
        for ln in txt.splitlines():
            s = ln.strip()
            if not s:
                continue
            if ROMAN.match(s):
                forms.add(s)
            if PROV.search(s):
                prov.add(s)
            if is_clean_en(s) and len(re.findall(r"[A-Za-z]", s)) >= 3:
                en_lines.add(s)
    doc.close()
    slots = [name for name, pat in SLOTS
             if any(re.search(pat, ln, re.I) for ln in en_lines)]
    # Form I is shown as "To do (an action)" / a base paradigm rather than a roman numeral
    forms_present = sorted(forms, key=_roman_key)
    if any("To do" in ln for ln in en_lines) or "I" not in forms:
        forms_present = ["I"] + forms_present
    return {
        "pages": pages, "images": imgs,
        "arabic_unicode_chars": arabic_unicode_chars,
        "arabic_glyph_status": ("unicode_text" if arabic_unicode_chars > 30
                                else "legacy_font_not_unicode (not OCR'd; structure only)"),
        "paradigm_slots": slots,
        "form_markers": forms_present,
        "provenance_lines": sorted(prov),
        "english_label_count": len(en_lines),
        "english_labels": sorted(en_lines),
        "_full": "".join(full),
    }


def _roman_key(r):
    order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
             "XI", "XII", "XIII", "XIV", "XV"]
    return order.index(r) if r in order else 99


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def extract_docx(path):
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        xml = zf.read("word/document.xml")
        media = [n for n in names if n.startswith("word/media/")]
    root = ET.fromstring(xml)
    paras = []
    for p in root.iter(_W + "p"):
        txt = "".join(t.text or "" for t in p.iter(_W + "t")).strip()
        if txt:
            paras.append(txt)
    tables = sum(1 for _ in root.iter(_W + "tbl"))
    drawings = sum(1 for _ in root.iter(_W + "drawing")) or len(media)
    ar = sum(1 for ln in paras for c in ln if T._AR.match(c))
    return {
        "paragraphs": len(paras), "tables": tables,
        "image_files": len(media), "drawings": drawings,
        "arabic_unicode_chars": ar,
        "para_text": paras,
        "english_paras": [p for p in paras if is_clean_en(p)],
    }


def main():
    cdir = corpus_dir()
    os.makedirs(OUT_PDF, exist_ok=True)
    os.makedirs(OUT_DOCX, exist_ok=True)
    cat = {"schema": "fusha/pdf_catalogue@1", "pdfs": [], "docx": [],
           "totals": {"pdf_files": 0, "pdf_pages": 0, "pdf_images": 0, "docx_files": 0}}
    samples = []

    for fn in sorted(f for f in os.listdir(cdir) if f.lower().endswith(".pdf")):
        low = fn.lower()
        if "grammar" in low or "problem" in low:
            continue  # eval paper, not a verb chart — handled by the nahw eval-gate (GP0)
        path = os.path.join(cdir, fn)
        info = extract_pdf(path)
        stem = re.sub(r"[^a-z0-9]+", "-", fn.lower().rsplit(".", 1)[0]).strip("-")
        with open(os.path.join(OUT_PDF, stem + ".txt"), "w", encoding="utf-8") as f:
            f.write(info.pop("_full"))
        rec = {"file": fn, "topic": "verb_charts", "source_review_status": "needs_review",
               "raw_committed": False, **info,
               "full_output": "corpora/sarfnahw/out/pdf/%s.txt" % stem}
        cat["pdfs"].append(rec)
        cat["totals"]["pdf_files"] += 1
        cat["totals"]["pdf_pages"] += info["pages"]
        cat["totals"]["pdf_images"] += info["images"]
        samples.append({"file": fn, "paradigm_slots": info["paradigm_slots"],
                        "form_markers": info["form_markers"],
                        "sample_english_labels": info["english_labels"][:14]})

    for fn in sorted(f for f in os.listdir(cdir) if f.lower().endswith(".docx")):
        path = os.path.join(cdir, fn)
        info = extract_docx(path)
        stem = re.sub(r"[^a-z0-9]+", "-", fn.lower().rsplit(".", 1)[0]).strip("-")
        with open(os.path.join(OUT_DOCX, stem + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(info.pop("para_text")))
        eng = info.pop("english_paras")
        rec = {"file": fn, "topic": "verb_charts", "source_review_status": "needs_review",
               "raw_committed": False,
               "note": "verb tables embedded as images (0 Word tables); image content NOT OCR'd",
               **info, "full_output": "corpora/sarfnahw/out/docx/%s.txt" % stem}
        cat["docx"].append(rec)
        cat["totals"]["docx_files"] += 1
        samples.append({"file": fn, "english_paras_sample": eng[:10]})

    with open(os.path.join(OUT_DIR, "pdf_catalogue.json"), "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "pdf_samples.jsonl"), "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print("PDFs:", cat["totals"]["pdf_files"], "pages:", cat["totals"]["pdf_pages"],
          "images:", cat["totals"]["pdf_images"], "| DOCX:", cat["totals"]["docx_files"])
    for r in cat["pdfs"]:
        print(" -", r["file"], "| slots", len(r["paradigm_slots"]), r["paradigm_slots"],
              "| forms", r["form_markers"], "|", r["arabic_glyph_status"])
    for r in cat["docx"]:
        print(" -", r["file"], "| paras", r["paragraphs"], "| imgs", r["image_files"],
              "| arabic_unicode", r["arabic_unicode_chars"])


if __name__ == "__main__":
    main()
