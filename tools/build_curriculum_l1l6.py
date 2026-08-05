#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the L1-L6 curriculum custody manifest, registry, concept graph and
material-class census from the PRIVATE lesson corpus.

Custody boundary (controlling; see curriculum/l1l6/custody/custody-decision.md):
the six Level archives (source-site lesson exports) are PRIVATE SOURCE CUSTODY.
Public redistribution authority is NOT established, so this builder never
commits lesson prose. Committed fields are limited to: file hashes, structural
counts, titles, slugs, section-heading strings (short factual labels used as
concept identifiers), source URLs, and derived records authored here. Reading
passages, translations, vocabulary rows, quiz bodies, mistake explanations and
all other body prose stay in the private corpus; the build is reproducible
whenever that corpus is present.

Usage:
  python tools/build_curriculum_l1l6.py --source-dir <dir with Level1..Level6>
  python tools/build_curriculum_l1l6.py --source-dir <dir> --check   # byte-diff

Deterministic: same corpus -> byte-identical outputs (sorted walks, sorted
keys, LF newlines, NFC-normalized committed strings, no timestamps).
Stdlib only. Writes ONLY under curriculum/l1l6/{custody,registry,graph,eval-separation}.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import unicodedata

# Owner direction 2026-08-05 (curriculum/l1l6/custody/custody-decision.md,
# "the source site is not named publicly"): committed provenance URLs carry an
# opaque alias host with the original path preserved. Applied to EVERY http(s)
# URL at ingestion so the public tree never depends on the real host string.
ALIAS_HOST = "source-site.invalid"

def alias_url(url):
    m = re.match(r"^(https?://)[^/]+(/.*)?$", url or "")
    if not m:
        return url
    return m.group(1) + ALIAS_HOST + (m.group(2) or "")


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_BASE = os.path.join(REPO_ROOT, "curriculum", "l1l6")

SCHEMA_MANIFEST = "curriculum.l1l6_source_manifest.v1"
SCHEMA_LESSON = "curriculum.l1l6_lesson.v1"
SCHEMA_MODULE = "curriculum.l1l6_module.v1"
SCHEMA_LEVEL = "curriculum.l1l6_level.v1"
SCHEMA_CONCEPT = "curriculum.l1l6_concept.v1"
SCHEMA_EDGE = "curriculum.l1l6_concept_edge.v1"
SCHEMA_CLASSES = "curriculum.l1l6_material_classes.v1"

CUSTODY_STATUS = "private_source_custody_metadata_only"

FILename_RE = re.compile(r"^Level(\d)_Module(\d+)_Lesson(\d+)\.md$")
# Semantic matcher for learner-error sections. NEVER rely on one exact English
# spelling: the corpus uses "Common Mistakes", "Common Mistakes to Avoid",
# "Common Mistakes: \u2026", "Common Mistakes in \u2026", "Common Errors to Avoid" and
# "Common Confusion Points" (audit 2026-08-02: 205 lessons carry one).
MISTAKE_HEADING_RE = re.compile(r"^common (mistakes?|errors?|confusion)", re.I)
AR_RE = re.compile(r"[\u0600-\u06FF]")
AR_WORD_RE = re.compile(r"[\u0600-\u06FF][\u0600-\u06FF\u0640\u064B-\u0652\u0670]*")

# Section headings that are lesson apparatus, not linguistic concepts.
BOILERPLATE_HEADINGS = {
    "lesson objectives",
    "passage translation",
    "vocabulary",
    "new vocabulary",
    "key takeaways",
    "common mistakes",
    "common mistakes to avoid",
    "lesson quiz",
    "memorization tips",
    "pronunciation practice",
    "examples from the reading",
    "examples from the passage",
    "examples from the reading passage",
}
BOILERPLATE_PREFIXES = ("reading passage", "q")

# Ordered, first-match-wins domain classifier over the concept heading text
# (lowercased, Arabic kept). Deterministic by construction. The domain set is
# the 15-domain progression vocabulary required by the PR brief.
DOMAIN_RULES = [
    ("script_phonology", [
        "letter", "alphabet", "sound", "pronunciation", "fatha", "kasra",
        "damma", "sukun", "shadda", "madd", "hamza rules", "tanwin",
        "harakat", "vowel", "script", "writing", "orthograph", "ḍamma",
        "fatḥa", "sukūn", "long vowel",
    ]),
    ("roots_patterns", [
        "root", "pattern", "wazn", "جذر", "وزن", "trilateral", "radical",
        "template", "الجذر", "الوزن", "measure",
    ]),
    ("derivation", [
        "form ii", "form iii", "form iv", "form v", "form vi", "form vii",
        "form viii", "form ix", "form x", "derived", "derivation", "masdar",
        "maṣdar", "participle", "verbal noun", "مصدر", "اسم الفاعل",
        "اسم المفعول", "diminutive", "elative", "تفضيل", "instrument",
        "اسم الآلة", "place noun", "اسم المكان",
    ]),
    ("clitics_affixes", [
        "clitic", "affix", "prefix", "suffix", "attached pronoun",
        "الضمائر المتصلة", "definite article", "ال", "proclitic", "enclitic",
    ]),
    ("paradigms", [
        "conjugation", "paradigm", "chart", "تصريف", "past tense",
        "present tense", "imperative", "الأمر", "الماضي", "المضارع",
        "hollow", "defective", "assimilated", "doubled", "geminate",
        "weak verb", "quadriliteral", "passive voice", "المبني للمجهول",
        "plural", "dual", "جمع", "مثنى", "feminine", "masculine", "gender",
    ]),
    ("case_mood", [
        "case", "mood", "nominative", "accusative", "genitive", "jussive",
        "subjunctive", "indicative", "iʿrab", "irab", "إعراب", "الرفع",
        "النصب", "الجر", "الجزم", "declension", "indeclinab", "البناء",
        "diptote", "الممنوع من الصرف", "five nouns", "الأسماء الخمسة",
    ]),
    ("particles", [
        "particle", "preposition", "حرف", "حروف", "إن", "أن", "لم", "لن",
        "لا", "ما", "من", "إلى", "على", "interrogative", "استفهام",
        "conditional particle", "vocative", "النداء", "exception",
        "الاستثناء", "إلا", "oath", "القسم",
    ]),
    ("governance", [
        "govern", "abrogat", "kana", "inna", "كان", "إنَّ", "النواسخ",
        "sisters", "أخوات", "عمل", "امل", "jazm", "nasb operator",
    ]),
    ("hidden_structure", [
        "hidden", "implied", "elli", "ellipsis", "omitted", "تقدير",
        "محذوف", "مقدر", "estimated", "concealed", "مستتر",
    ]),
    ("ambiguity", [
        "ambigu", "rival", "multiple analyses", "disagree", "school",
        "kufan", "basran", "الكوفي", "البصري", "homograph", "distinguish",
        "differs from", "vs", "vs.", "vs ", "vsّ", "confus",
    ]),
    ("syntactic_relations", [
        "sentence", "clause", "subject", "predicate", "object", "مبتدأ",
        "خبر", "فاعل", "مفعول", "idafa", "iḍāfa", "الإضافة", "construct",
        "relative", "الموصول", "صلة", "adjective", "النعت", "صفة",
        "agreement", "apposition", "بدل", "توكيد", "حال", "تمييز",
        "المنادى", "circumstantial", "الجملة", "خبرية", "التعجب",
        "word order", "topic", "comment", "nominal sentence",
        "verbal sentence",
    ]),
    ("contextual_interpretation", [
        "context", "meaning in", "rhetoric", "بلاغة", "style", "genre",
        "metaphor", "المجاز", "الكناية", "التشبيه", "emphasis", "توكيد",
        "register",
    ]),
    ("quranic_classical", [
        "quran", "qurʾan", "quranic", "القرآن", "classical", "poetry",
        "poetic", "الشعر", "hadith", "الحديث", "tajwid", "التجويد",
        "surah", "ayah", "آية",
    ]),
    ("inflection", [
        "tense", "negation", "النفي", "future", "المستقبل", "person",
        "number", "voice", "transitiv", "التعدي",
    ]),
    ("morphology_general", []),  # fallback
]


def nfc(s):
    return unicodedata.normalize("NFC", s)


def slugify(s):
    s = nfc(s).strip().lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^0-9a-z\u0600-\u06FF]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:80] or "untitled"


def classify_domain(heading):
    h = nfc(heading).lower()
    tokens = set(re.split(r"[^0-9a-z؀-ۿ]+", h))
    for domain, needles in DOMAIN_RULES:
        for n in needles:
            if not n:
                continue
            # short Arabic needles only match as whole tokens, otherwise the
            # substring test over-captures (e.g. "ال" inside any al- word)
            if AR_RE.search(n) and len(n) <= 4:
                if n in tokens:
                    return domain
            elif n in h:
                return domain
    return "morphology_general"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_meta_line(lines, key):
    pat = re.compile(r"^- \*\*%s:\*\*\s*(.+)$" % re.escape(key))
    for ln in lines[:14]:
        m = pat.match(ln)
        if m:
            return m.group(1).strip()
    return None


def parse_lesson(path, fname):
    m = FILename_RE.match(fname)
    level_n, module_n, lesson_n = int(m.group(1)), int(m.group(2)), int(m.group(3))
    with io.open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    slug_raw = parse_meta_line(lines, "Slug") or ""
    slug = slug_raw.strip("`")
    source = parse_meta_line(lines, "Source") or ""
    curriculum = parse_meta_line(lines, "Curriculum") or ""
    module_line = parse_meta_line(lines, "Module") or ""

    headings = []
    sections = []  # ordered inventory of EVERY ##/### section (kind rows)
    quiz_started = False
    n_quiz = n_passages = n_mistake_sections = 0
    for ln in lines:
        hm = re.match(r"^(#{2,3})\s+(.*)$", ln)
        if not hm:
            continue
        htext = hm.group(2).strip()
        hlow = nfc(htext).lower()
        if hlow == "lesson quiz":
            quiz_started = True
            sections.append({"kind": "quiz_header"})
            continue
        if quiz_started and re.match(r"^q\d+$", hlow):
            n_quiz += 1
            sections.append({"kind": "quiz_question"})
            continue
        if hlow.startswith("reading passage"):
            n_passages += 1
            sections.append({"kind": "reading_passage"})
            continue
        if MISTAKE_HEADING_RE.match(hlow):
            n_mistake_sections += 1
            sections.append({"kind": "learner_error_section"})
            continue
        base = re.sub(r"\s*\(.*?\)\s*", " ", hlow).strip()
        if hlow in BOILERPLATE_HEADINGS or base in BOILERPLATE_HEADINGS:
            kind = ("passage_translation" if hlow == "passage translation" else
                    "vocabulary_support" if "vocabulary" in hlow else
                    "supporting_example_group" if hlow.startswith("examples from") else
                    "apparatus")
            sections.append({"kind": kind})
            continue
        if any(hlow.startswith(p) and hlow != p for p in ()) or quiz_started:
            sections.append({"kind": "apparatus"})
            continue
        headings.append(htext)
        sections.append({"kind": "concept", "heading": nfc(htext)})

    vocab_rows = 0
    in_table = False
    for ln in lines:
        if ln.startswith("|") and "---" not in ln:
            if in_table:
                vocab_rows += 1
            else:
                in_table = True  # header row
        elif ln.startswith("|") and "---" in ln:
            continue
        else:
            in_table = False

    words = len(text.split())
    ar_words = len(AR_WORD_RE.findall(text))
    norm_state = "nfc" if text == nfc(text) else "non_nfc_source"

    return {
        "level": level_n,
        "module": module_n,
        "lesson": lesson_n,
        "title": nfc(title),
        "slug": nfc(slug),
        "source_url": alias_url(nfc(source)),
        "curriculum": curriculum,
        "module_title": nfc(module_line),
        "concept_headings": [nfc(h) for h in headings],
        "sections": sections,
        "counts": {
            "words_total": words,
            "words_arabic": ar_words,
            "reading_passages": n_passages,
            "vocabulary_table_rows": vocab_rows,
            "quiz_questions": n_quiz,
            "common_mistakes_sections": n_mistake_sections,
        },
        "normalization_state": norm_state,
    }


def dump_review(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return path, data.encode("utf-8")


def dump_jsonl(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    buf = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    )
    return path, buf.encode("utf-8")


def build(source_dir):
    """Return {relpath: bytes} for every artifact."""
    manifest_rows = []
    lessons = []
    level_meta = {}

    for level_dir in sorted(os.listdir(source_dir)):
        lp = os.path.join(source_dir, level_dir)
        if not os.path.isdir(lp) or not re.match(r"^Level[1-6]$", level_dir):
            continue
        level_n = int(level_dir[-1])
        for fname in sorted(os.listdir(lp)):
            fpath = os.path.join(lp, fname)
            if fname == "README.md":
                with io.open(fpath, "r", encoding="utf-8") as f:
                    rl = f.read().split("\n")
                title = ""
                mods = les = 0
                src = ""
                for ln in rl:
                    if ln.startswith("Level %d —" % level_n):
                        title = nfc(ln.strip())
                    elif ln.startswith("Modules:"):
                        mods = int(ln.split(":")[1])
                    elif ln.startswith("Lessons:"):
                        les = int(ln.split(":")[1])
                    elif ln.startswith("Source:"):
                        src = ln.split(" ", 1)[1].strip()
                level_meta[level_n] = {
                    "level_id": "L%d" % level_n,
                    "title": title,
                    "declared_modules": mods,
                    "declared_lessons": les,
                    "source_url": alias_url(src),
                }
                manifest_rows.append({
                    "schema": SCHEMA_MANIFEST,
                    "file_id": "src-l%d-readme" % level_n,
                    "archive": "Level%d.zip" % level_n,
                    "path_in_archive": fname,
                    "sha256": sha256_file(fpath),
                    "kind": "level_readme",
                    "level": level_n, "module": None, "lesson": None,
                    "title": title, "slug": None,
                    "source_url": alias_url(src), "language": "en+ar",
                    "counts": None,
                    "custody_status": CUSTODY_STATUS,
                    "normalization_state": "nfc",
                })
                continue
            if not FILename_RE.match(fname):
                continue
            rec = parse_lesson(fpath, fname)
            lesson_id = "L%d.M%d.%02d" % (rec["level"], rec["module"], rec["lesson"])
            manifest_rows.append({
                "schema": SCHEMA_MANIFEST,
                "file_id": "src-" + lesson_id.lower().replace(".", "-"),
                "archive": "Level%d.zip" % rec["level"],
                "path_in_archive": fname,
                "sha256": sha256_file(fpath),
                "kind": "lesson",
                "level": rec["level"], "module": rec["module"], "lesson": rec["lesson"],
                "title": rec["title"], "slug": rec["slug"],
                "source_url": rec["source_url"], "language": "en+ar",
                "counts": rec["counts"],
                "custody_status": CUSTODY_STATUS,
                "normalization_state": rec["normalization_state"],
            })
            rec["lesson_id"] = lesson_id
            lessons.append(rec)

    lessons.sort(key=lambda r: (r["level"], r["module"], r["lesson"]))
    manifest_rows.sort(key=lambda r: (r["level"], r["module"] or 0, r["lesson"] or 0, r["file_id"]))

    # duplicate detection: identical content hashes
    by_hash = {}
    for r in manifest_rows:
        by_hash.setdefault(r["sha256"], []).append(r["file_id"])
    dupes = sorted([ids for ids in by_hash.values() if len(ids) > 1])
    for r in manifest_rows:
        r["duplicate_of"] = sorted(
            [i for i in by_hash[r["sha256"]] if i != r["file_id"]]
        )

    # ---- registry ----
    levels_out = []
    modules = {}
    for rec in lessons:
        key = (rec["level"], rec["module"])
        if key not in modules:
            mt = rec["module_title"]
            mt = re.sub(r"^\d+\s*—\s*", "", mt)
            modules[key] = {
                "schema": SCHEMA_MODULE,
                "module_id": "L%d.M%d" % key,
                "level_id": "L%d" % rec["level"],
                "ordinal": rec["module"],
                "title": nfc(mt),
                "lesson_ids": [],
            }
        modules[key]["lesson_ids"].append(rec["lesson_id"])
    for ln_, meta in sorted(level_meta.items()):
        actual = [r for r in lessons if r["level"] == ln_]
        levels_out.append({
            "schema": SCHEMA_LEVEL,
            "level_id": meta["level_id"],
            "ordinal": ln_,
            "title": meta["title"],
            "source_url": meta["source_url"],
            "declared_modules": meta["declared_modules"],
            "declared_lessons": meta["declared_lessons"],
            "actual_modules": len({r["module"] for r in actual}),
            "actual_lessons": len(actual),
            "declaration_matches_actual": (
                meta["declared_lessons"] == len(actual)
                and meta["declared_modules"] == len({r["module"] for r in actual})
            ),
        })

    lesson_rows = []
    for rec in lessons:
        lesson_rows.append({
            "schema": SCHEMA_LESSON,
            "lesson_id": rec["lesson_id"],
            "module_id": "L%d.M%d" % (rec["level"], rec["module"]),
            "level_id": "L%d" % rec["level"],
            "ordinal": rec["lesson"],
            "title": rec["title"],
            "slug": rec["slug"],
            "source_url": rec["source_url"],
            "source_file_id": "src-" + rec["lesson_id"].lower().replace(".", "-"),
            "counts": rec["counts"],
            "concept_ids": [
                "c-%s-%s" % (rec["lesson_id"].lower().replace(".", "-"), slugify(h))
                for h in rec["concept_headings"]
            ],
            "linguistic_authority": "none_curriculum_prose_is_uncertified",
        })

    # ---- section inventory (per lesson, ordered, EVERY section) ----
    section_rows = []
    for rec in lessons:
        for i, s in enumerate(rec["sections"]):
            row = {"schema": "curriculum.l1l6_section.v1",
                   "section_id": "%s#%02d" % (rec["lesson_id"], i),
                   "lesson_id": rec["lesson_id"], "ordinal": i,
                   "kind": s["kind"]}
            if "heading" in s:
                row["heading"] = s["heading"]
            section_rows.append(row)

    # ---- concept graph ----
    concept_rows = []
    seen_concept_ids = set()
    slug_first_lesson = {}
    for rec in lessons:
        for h in rec["concept_headings"]:
            cslug = slugify(h)
            cid = "c-%s-%s" % (rec["lesson_id"].lower().replace(".", "-"), cslug)
            if cid in seen_concept_ids:
                continue
            seen_concept_ids.add(cid)
            concept_rows.append({
                "schema": SCHEMA_CONCEPT,
                "concept_id": cid,
                "lesson_id": rec["lesson_id"],
                "heading": h,
                "concept_slug": cslug,
                "domain": classify_domain(h),
                "certification": "none_source_supported_only",
            })
            slug_first_lesson.setdefault(cslug, []).append(
                (rec["level"], rec["module"], rec["lesson"], cid)
            )

    edge_rows = []
    prev = None
    for rec in lessons:
        if prev is not None:
            edge_rows.append({
                "schema": SCHEMA_EDGE,
                "edge_id": "e-order-%s-%s" % (
                    prev["lesson_id"].lower().replace(".", "-"),
                    rec["lesson_id"].lower().replace(".", "-")),
                "kind": "curriculum_order_prerequisite",
                "from": prev["lesson_id"],
                "to": rec["lesson_id"],
                "basis": "source_curriculum_ordering",
            })
        prev = rec
    for cslug, occs in sorted(slug_first_lesson.items()):
        occs = sorted(occs)
        for a, b in zip(occs, occs[1:]):
            edge_rows.append({
                "schema": SCHEMA_EDGE,
                "edge_id": "e-revisit-%s-%s" % (a[3], b[3]),
                "kind": "concept_revisited",
                "from": a[3],
                "to": b[3],
                "basis": "identical_concept_slug_in_later_lesson",
            })
    edge_rows.sort(key=lambda e: e["edge_id"])

    # ---- material classes (exercise/eval separation census) ----
    tot = {
        "quiz_questions": sum(r["counts"]["quiz_questions"] for r in lesson_rows),
        "reading_passages": sum(r["counts"]["reading_passages"] for r in lesson_rows),
        "vocabulary_table_rows": sum(r["counts"]["vocabulary_table_rows"] for r in lesson_rows),
        "common_mistakes_sections": sum(r["counts"]["common_mistakes_sections"] for r in lesson_rows),
    }
    classes = {
        "schema": SCHEMA_CLASSES,
        "classes": {
            "answered_instructional_examples": {
                "population": "worked examples inside lesson grammar sections and reading passages (answer visible in source)",
                "count_proxy": {"reading_passages": tot["reading_passages"], "vocabulary_table_rows": tot["vocabulary_table_rows"]},
                "eligible_as_independent_eval": False,
                "reason": "answer-visible in instructional prose",
            },
            "worked_exercises": {
                "population": "common-mistakes contrast sets (wrong vs corrected forms shown)",
                "count_proxy": {"common_mistakes_sections": tot["common_mistakes_sections"]},
                "eligible_as_independent_eval": False,
                "reason": "answer-visible; usable as adversarial fixture SOURCE after restatement + review",
            },
            "development_fixtures": {
                "population": "pilot fixtures under curriculum/l1l6/pilot/ derived from lesson claims",
                "eligible_as_independent_eval": False,
                "reason": "used during development; regression role only",
            },
            "candidate_regression_tests": {
                "population": "restated mistake-pattern fixtures promoted via TP-CURR packets after review",
                "eligible_as_independent_eval": False,
                "reason": "candidate until owner/Sol review",
            },
            "questions_without_verified_answer_keys": {
                "population": "lesson quiz questions: the source publishes questions with NO answer key",
                "count": tot["quiz_questions"],
                "eligible_as_independent_eval": False,
                "reason": "no verified key; keys must NOT be manufactured without source or review evidence (TP-CURR-QUIZ-KEY-REVIEW)",
            },
            "genuinely_held_out_evaluation_material": {
                "population": "NONE in this corpus",
                "count": 0,
                "eligible_as_independent_eval": True,
                "reason": "every item in the corpus is answer-visible or keyless; honest held-out material must come from elsewhere",
            },
        },
        "leakage_rule": "an answer-visible exercise is never counted as an independent evaluation",
    }

    outputs = {}
    for path, data in [
        dump_jsonl(manifest_rows, os.path.join(OUT_BASE, "custody", "source-manifest.jsonl")),
        dump_review({
            "schema": SCHEMA_MANIFEST + ".meta",
            "generator": "tools/build_curriculum_l1l6.py",
            "row_count": len(manifest_rows),
            "lesson_files": sum(1 for r in manifest_rows if r["kind"] == "lesson"),
            "level_readmes": sum(1 for r in manifest_rows if r["kind"] == "level_readme"),
            "duplicate_content_groups": dupes,
            "custody_status": CUSTODY_STATUS,
            "custody_decision": "curriculum/l1l6/custody/custody-decision.md",
            "committed_fields_policy": "hashes, counts, titles, slugs, section-heading labels, source URLs only; no lesson prose",
        }, os.path.join(OUT_BASE, "custody", "source-manifest.meta.json")),
        dump_review({"schema": SCHEMA_LEVEL + ".table", "generator": "tools/build_curriculum_l1l6.py", "levels": levels_out},
                    os.path.join(OUT_BASE, "registry", "levels.json")),
        dump_jsonl([modules[k] for k in sorted(modules)], os.path.join(OUT_BASE, "registry", "modules.jsonl")),
        dump_jsonl(lesson_rows, os.path.join(OUT_BASE, "registry", "lessons.jsonl")),
        dump_review({
            "schema": SCHEMA_LESSON + ".meta",
            "generator": "tools/build_curriculum_l1l6.py",
            "lessons": len(lesson_rows),
            "modules": len(modules),
            "levels": len(levels_out),
            "concepts": len(concept_rows),
            "quiz_questions_total": tot["quiz_questions"],
        }, os.path.join(OUT_BASE, "registry", "lessons.meta.json")),
        dump_jsonl(section_rows, os.path.join(OUT_BASE, "registry", "section-inventory.jsonl")),
        dump_review({
            "schema": "curriculum.l1l6_section.v1.meta",
            "generator": "tools/build_curriculum_l1l6.py",
            "rows": len(section_rows),
            "kind_histogram": {
                k: sum(1 for r in section_rows if r["kind"] == k)
                for k in sorted({r["kind"] for r in section_rows})
            },
        }, os.path.join(OUT_BASE, "registry", "section-inventory.meta.json")),
        dump_jsonl(concept_rows, os.path.join(OUT_BASE, "graph", "concepts.jsonl")),
        dump_jsonl(edge_rows, os.path.join(OUT_BASE, "graph", "concept-edges.jsonl")),
        dump_review({
            "schema": SCHEMA_CONCEPT + ".meta",
            "generator": "tools/build_curriculum_l1l6.py",
            "concept_count": len(concept_rows),
            "edge_count": len(edge_rows),
            "edge_kinds": sorted({e["kind"] for e in edge_rows}),
            "domain_histogram": {
                d: sum(1 for c in concept_rows if c["domain"] == d)
                for d in sorted({c["domain"] for c in concept_rows})
            },
        }, os.path.join(OUT_BASE, "graph", "concepts.meta.json")),
        dump_review(classes, os.path.join(OUT_BASE, "eval-separation", "material-classes.json")),
    ]:
        outputs[path] = data
    return outputs


def main():
    global OUT_BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--check", action="store_true",
                    help="verify committed artifacts byte-match a regeneration")
    ap.add_argument("--out-dir", default=None,
                    help="write artifacts under this directory instead of "
                         "curriculum/l1l6 (CI fixture-corpus runs)")
    args = ap.parse_args()
    if args.out_dir:
        OUT_BASE = os.path.abspath(args.out_dir)
    if not os.path.isdir(args.source_dir):
        print("FAIL: source dir not found: %s" % args.source_dir)
        return 2
    outputs = build(args.source_dir)
    if args.check:
        bad = []
        for path, data in sorted(outputs.items()):
            if not os.path.exists(path):
                bad.append("MISSING %s" % os.path.relpath(path, REPO_ROOT))
                continue
            with open(path, "rb") as f:
                if f.read() != data:
                    bad.append("DIFFERS %s" % os.path.relpath(path, REPO_ROOT))
        if bad:
            print("FAIL: deterministic regeneration mismatch:")
            for b in bad:
                print("  " + b)
            return 1
        print("OK: %d artifacts byte-identical to regeneration" % len(outputs))
        return 0
    for path, data in sorted(outputs.items()):
        with open(path, "wb") as f:
            f.write(data)
        print("wrote %s (%d bytes)" % (os.path.relpath(path, REPO_ROOT), len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
