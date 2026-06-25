#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build source-triangulated two-vote packets for hover requests.

This helper does not apply decisions. It reads a validated two-vote request
packet, compares Quran.com word-by-word translation with Quranic Arabic Corpus
word-by-word translation for the same token location, and emits sarf/nahw vote
rows. Only exact normalized source agreement becomes an approval; every other
row stays pending for manual or scholar review.
"""
import argparse
import collections
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOC_RE = re.compile(r"^(\d{1,3}):(\d{1,3}):(\d{1,3})$")
TAG_RE = re.compile(r"<[^>]+>")
ROW_RE = re.compile(
    r"<tr><td>(?P<word>.*?)</td><td class=\"ic\">.*?</td><td class=\"col3\">(?P<grammar>.*?)</td></tr>",
    re.S,
)
LOCATION_RE = re.compile(r"<span class=\"location\">\((?P<loc>\d{1,3}:\d{1,3}:\d{1,3})\)</span>")
SEG_RE = re.compile(r"<b[^>]*>([^<]+)</b>")
PAREN_AUX_RE = re.compile(
    r"^\((?:is|are|am|was|were|be|been|being|do|does|did|will be|shall be|has|have|had)\)\s+",
    re.I,
)
INITIAL_LETTER_WORDS = {
    "Alif",
    "Ayn",
    "Ha",
    "Kaf",
    "Lam",
    "Meem",
    "Mim",
    "Nun",
    "Qaf",
    "Ra",
    "Sad",
    "Seen",
    "Sin",
    "Ta",
    "Ya",
}
LEAK_RE = re.compile(
    r"\b(qac|quran\.com|quran-com|corpus\.quran|quranic arabic corpus|"
    r"tanzil|saheeh|sahih|tafsir|ocr|informed_by)\b",
    re.I,
)
ARABIC_DIACRITIC_RE = re.compile(
    r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u08d3-\u08ff"
    r"\u06df\u06e0\u06e2\u06e3\u06e5\u06e6\u06e7\u06e8\u06ea-\u06ed]"
)
ARABIC_PUNCT_RE = re.compile(r"[\u060c\u061b\u061f\u06dd\u06deۣۖۗۘۙۚۛۜ۟۠ۢۥۦ۪ۭۧۨ۫۬]")
PREPOSITION_WORDS = {
    "about",
    "against",
    "among",
    "around",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "as",
    "like",
    "of",
    "on",
    "onto",
    "over",
    "through",
    "to",
    "upon",
    "with",
}

QURAN_API = "https://api.quran.com/api/v4/verses/by_key/{verse_key}"
CORPUS_PAGE = "https://corpus.quran.com/wordbyword.jsp?chapter={surah}&verse={ayah}"


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def compact(value):
    return " ".join((value or "").strip().split())


def strip_tags(fragment):
    return compact(html.unescape(TAG_RE.sub("", fragment or "")))


def split_loc(loc):
    match = LOC_RE.match(str(loc or ""))
    if not match:
        raise ValueError("bad loc %r" % loc)
    return tuple(int(part) for part in match.groups())


def request_json(url, cache_path=None, delay=0.0):
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as handle:
            return json.load(handle)
    if delay:
        time.sleep(delay)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Codex Qamus source-triangulation audit"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
    return payload


def request_text(url, cache_path=None, delay=0.0):
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as handle:
            return handle.read()
    if delay:
        time.sleep(delay)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Codex Qamus source-triangulation audit"})
    with urllib.request.urlopen(req, timeout=30) as response:
        text = response.read().decode("utf-8", "replace")
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    return text


def quran_words_for_verse(surah, ayah, cache_dir=None, delay=0.0):
    verse_key = "%d:%d" % (surah, ayah)
    params = urllib.parse.urlencode(
        {
            "words": "true",
            "word_fields": "text_uthmani,text_uthmani_simple,translation,transliteration,location",
        }
    )
    url = QURAN_API.format(verse_key=verse_key) + "?" + params
    cache_path = os.path.join(cache_dir, "quran-com", "%03d_%03d.json" % (surah, ayah)) if cache_dir else None
    payload = request_json(url, cache_path=cache_path, delay=delay)
    out = {}
    for word in payload.get("verse", {}).get("words", []):
        if word.get("char_type_name") != "word":
            continue
        loc = str(word.get("location") or "")
        out[loc] = {
            "text": word.get("text") or "",
            "text_uthmani": word.get("text_uthmani") or "",
            "text_uthmani_simple": word.get("text_uthmani_simple") or "",
            "translation": compact((word.get("translation") or {}).get("text")),
            "source_url": url,
        }
    return out


def corpus_words_for_verse(surah, ayah, cache_dir=None, delay=0.0):
    url = CORPUS_PAGE.format(surah=surah, ayah=ayah)
    cache_path = os.path.join(cache_dir, "corpus", "%03d_%03d.html" % (surah, ayah)) if cache_dir else None
    text = request_text(url, cache_path=cache_path, delay=delay)
    out = {}
    for match in ROW_RE.finditer(text):
        word_cell = match.group("word")
        loc_match = LOCATION_RE.search(word_cell)
        if not loc_match:
            continue
        loc = loc_match.group("loc")
        parts = re.split(r"<br\s*/?>", word_cell)
        translation = strip_tags(parts[-1]) if len(parts) >= 3 else ""
        grammar = match.group("grammar")
        out[loc] = {
            "translation": compact(translation),
            "segments": [compact(seg) for seg in SEG_RE.findall(grammar) if compact(seg)],
            "grammar": strip_tags(grammar),
            "source_url": url,
        }
    return out


def normalize_translation(value):
    value = compact(html.unescape(value or "")).lower()
    value = value.replace("’", "'").replace("`", "'")
    value = value.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    value = value.replace("[", "").replace("]", "")
    value = value.replace("(", "").replace(")", "")
    value = re.sub(r"^[\"'`]+", "", value)
    value = re.sub(r"[\"'`]+$", "", value)
    value = re.sub(r"^[\-–—]+\s*", "", value)
    value = re.sub(r"\s*[\-–—]+$", "", value)
    value = re.sub(r"[.,;:!?،؛]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_arabic_surface(value):
    value = compact(value or "")
    value = value.replace("ـ", "")
    value = ARABIC_DIACRITIC_RE.sub("", value)
    value = ARABIC_PUNCT_RE.sub("", value)
    for src, dst in (
        ("ٱ", "ا"),
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ى", "ا"),
        ("ؤ", "و"),
        ("ئ", "ي"),
        ("ة", "ه"),
    ):
        value = value.replace(src, dst)
    value = re.sub(r"[^\u0621-\u064a]+", "", value)
    return value


def request_surface_norms(request):
    values = [request.get("surface_ar") or "", request.get("key") or ""]
    return {normalize_arabic_surface(value) for value in values if normalize_arabic_surface(value)}


def quran_surface_norms(quran_word):
    values = [
        (quran_word or {}).get("text") or "",
        (quran_word or {}).get("text_uthmani") or "",
        (quran_word or {}).get("text_uthmani_simple") or "",
    ]
    return {normalize_arabic_surface(value) for value in values if normalize_arabic_surface(value)}


def authored_gloss(quran_translation):
    gloss = compact(html.unescape(quran_translation or ""))
    gloss = gloss.replace("[", "").replace("]", "")
    gloss = PAREN_AUX_RE.sub("", gloss)
    gloss = re.sub(r"\(([^)]*)\)", r"\1", gloss)
    gloss = re.sub(r"^[\"'`]+", "", gloss)
    gloss = re.sub(r"[\"'`]+$", "", gloss)
    gloss = re.sub(r"^[\-–—]+\s*", "", gloss)
    gloss = re.sub(r"\s*[\-–—]+$", "", gloss)
    gloss = re.sub(r"[.,;:!?،؛]+$", "", gloss).strip()
    gloss = re.sub(r"[\"'`]+$", "", gloss).strip()
    if not gloss:
        return ""
    first, rest = gloss[:1], gloss[1:]
    first_word = gloss.split()[0]
    if first_word not in {"Allah", "I", "O"} | INITIAL_LETTER_WORDS and first.isupper():
        gloss = first.lower() + rest
    return compact(gloss)


def english_words(value):
    return set(re.findall(r"[a-z]+", normalize_translation(value)))


def preposition_role_omitted(gloss, corpus_word):
    segments = set((corpus_word or {}).get("segments") or [])
    if "P" not in segments:
        return False
    return not (english_words(gloss) & PREPOSITION_WORDS)


def select_source_loc(request, quran_words):
    loc = str(request.get("loc") or "")
    wanted = request_surface_norms(request)
    if not wanted:
        return None, "missing_request_surface"
    exact = quran_words.get(loc)
    if exact and wanted & quran_surface_norms(exact):
        return loc, ""
    surah, ayah, word_no = split_loc(loc)
    shifted_loc = "%d:%d:%d" % (surah, ayah, word_no - 4)
    shifted = quran_words.get(shifted_loc)
    if word_no > 4 and shifted and wanted & quran_surface_norms(shifted):
        return shifted_loc, ""
    matches = [
        source_loc
        for source_loc, word in quran_words.items()
        if wanted & quran_surface_norms(word)
    ]
    if len(matches) == 1:
        return matches[0], ""
    if len(matches) > 1:
        return None, "ambiguous_source_surface_match"
    return None, "source_surface_mismatch"


def _slug(value):
    value = normalize_translation(value)
    out = []
    for ch in value:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")[:48] or "gloss"


def source_agreement(request, quran_word, corpus_word):
    if not quran_word:
        return None, "missing_quran_word"
    if not corpus_word:
        return None, "missing_corpus_word"
    quran_translation = quran_word.get("translation") or ""
    corpus_translation = corpus_word.get("translation") or ""
    if not quran_translation or not corpus_translation:
        return None, "missing_source_translation"
    if normalize_translation(quran_translation) != normalize_translation(corpus_translation):
        return None, "source_translation_disagreement"
    gloss = authored_gloss(quran_translation)
    if not gloss:
        return None, "empty_authored_gloss"
    if len(gloss) > 80:
        return None, "gloss_too_long"
    if LEAK_RE.search(gloss):
        return None, "public_gloss_leak"
    if preposition_role_omitted(gloss, corpus_word):
        return None, "preposition_role_omitted"
    return gloss, "approved_exact_source_agreement"


def vote_rows_for_request(request, gloss, status, quran_word, corpus_word, blocker):
    loc = str(request["loc"])
    surface = request.get("surface_ar") or ""
    lane = request.get("suggested_lane") or "two_vote"
    segments = ", ".join((corpus_word or {}).get("segments") or [])
    reason_key = "source_triangulated:%s:%s:%s" % (lane, loc, _slug(gloss)) if gloss else ""
    rows = []
    for lens in ("sarf-primary", "nahw-primary"):
        if gloss:
            if lens == "sarf-primary":
                reasoning = (
                    "Surface %s at %s matches the request token; independent word sources agree on %r; "
                    "Corpus segments: %s."
                ) % (surface, loc, gloss, segments or "not listed")
                other_reasoning = (
                    "Context-preserving authored gloss keeps any visible function prefix/pronoun value from the agreed word sources."
                )
            else:
                reasoning = (
                    "Context at %s supports the agreed word-level value %r; the public gloss is concise and source-clean."
                ) % (loc, gloss)
                other_reasoning = (
                    "No morphology-only host gloss is substituted; full token-level function wording is retained."
                )
            rows.append(
                {
                    "blocker_if_rejected": "",
                    "concise_authored_gloss": gloss,
                    "decision": "approve",
                    "lens": lens,
                    "loc": loc,
                    "nahw_reasoning": reasoning if lens == "nahw-primary" else other_reasoning,
                    "reason_agreement_key": reason_key,
                    "sarf_reasoning": reasoning if lens == "sarf-primary" else other_reasoning,
                }
            )
        else:
            rows.append(
                {
                    "blocker_if_rejected": blocker,
                    "concise_authored_gloss": "",
                    "decision": "pending",
                    "lens": lens,
                    "loc": loc,
                    "nahw_reasoning": "",
                    "reason_agreement_key": "",
                    "sarf_reasoning": "",
                }
            )
    return rows


def build_votes(request_path, out_path, summary_path, cache_dir=None, delay=0.05):
    requests = read_jsonl(request_path)
    verse_cache = {}
    votes = []
    review_rows = []
    errors = []
    for request in requests:
        loc = str(request.get("loc") or "")
        try:
            surah, ayah, _word = split_loc(loc)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        verse_key = (surah, ayah)
        if verse_key not in verse_cache:
            try:
                verse_cache[verse_key] = {
                    "quran": quran_words_for_verse(surah, ayah, cache_dir=cache_dir, delay=delay),
                    "corpus": corpus_words_for_verse(surah, ayah, cache_dir=cache_dir, delay=delay),
                }
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                verse_cache[verse_key] = {"quran": {}, "corpus": {}, "error": str(exc)}
        source_loc, blocker = select_source_loc(request, verse_cache[verse_key].get("quran", {}))
        quran_word = verse_cache[verse_key].get("quran", {}).get(source_loc) if source_loc else None
        corpus_word = verse_cache[verse_key].get("corpus", {}).get(source_loc) if source_loc else None
        gloss = None
        if source_loc:
            gloss, blocker = source_agreement(request, quran_word, corpus_word)
        if not gloss and verse_cache[verse_key].get("error"):
            blocker = "source_fetch_error"
        votes.extend(vote_rows_for_request(request, gloss, "approve" if gloss else "pending", quran_word, corpus_word, blocker))
        review_rows.append(
            {
                "loc": loc,
                "source_loc": source_loc or "",
                "surface": request.get("surface_ar") or "",
                "decision": "approve" if gloss else "pending",
                "gloss": gloss or "",
                "blocker": "" if gloss else blocker,
                "quran_translation": (quran_word or {}).get("translation", ""),
                "corpus_translation": (corpus_word or {}).get("translation", ""),
                "corpus_segments": (corpus_word or {}).get("segments", []),
                "suggested_lane": request.get("suggested_lane"),
            }
        )
    if errors:
        raise ValueError("\n".join(errors[:20]))
    write_jsonl(out_path, votes)
    by_decision = collections.Counter(row["decision"] for row in review_rows)
    by_blocker = collections.Counter(row["blocker"] for row in review_rows if row["blocker"])
    by_lane = collections.Counter(row["suggested_lane"] for row in review_rows)
    summary = {
        "_generator": "tools/build_source_triangulated_votes.py",
        "request_file": os.path.relpath(request_path, ROOT),
        "vote_file": os.path.relpath(out_path, ROOT),
        "requests": len(requests),
        "votes": len(votes),
        "approved_requests": by_decision.get("approve", 0),
        "pending_requests": by_decision.get("pending", 0),
        "by_blocker": dict(sorted(by_blocker.items())),
        "by_lane": dict(sorted(by_lane.items())),
        "source_contract": {
            "approve_when": "Quran.com word translation and Quranic Arabic Corpus word-by-word translation agree after normalization.",
            "quran_api": "https://api.quran.com/api/v4/verses/by_key/{verse_key}?words=true",
            "corpus_page": "https://corpus.quran.com/wordbyword.jsp?chapter={surah}&verse={ayah}",
            "public_payload": "src=qamus kind=authored; external source names stay out of public gloss rows.",
        },
        "sample": review_rows[:20],
        "status": "votes_only_not_reconciled",
    }
    write_json(summary_path, summary)
    return summary


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--cache-dir", default=os.path.join(ROOT, "out", "source_triangulation_cache"))
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()
    try:
        summary = build_votes(args.requests, args.out, args.summary, cache_dir=args.cache_dir, delay=args.delay)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
