#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build reviewable rich-hover morphosyntax metadata candidates.

This generator is deliberately narrow. It emits metadata records for surface
composition that is visible in the written token, while leaving deeper case,
number, gender, and syntactic role unclaimed unless another lane certifies them.

It does not mutate live Qamus data or edit token decisions.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "out" / "hover_stage"

HARAKAT_RE = re.compile(
    "["
    "\u0610-\u061a"
    "\u064b-\u065f"
    "\u0670"
    "\u06d6-\u06dc"
    "\u06df-\u06e4"
    "\u06e7-\u06e8"
    "\u06ea-\u06ed"
    "]"
)

PUBLIC_BOUNDARY = {
    "public_gloss_src": "qamus",
    "public_gloss_kind": "authored",
    "public_gloss_lang": "en",
    "external_source_names_public": False,
}


def strip_marks(text):
    text = HARAKAT_RE.sub("", text or "")
    return (
        text.replace("ٱ", "ا")
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
    )


def is_mark(ch):
    return bool(HARAKAT_RE.match(ch))


def take_base_with_marks(text, index):
    if index >= len(text):
        return "", index
    end = index + 1
    while end < len(text) and is_mark(text[end]):
        end += 1
    return text[index:end], end


def take_article(text, index):
    if index >= len(text) or strip_marks(text[index]) != "ا":
        return "", index
    first, index = take_base_with_marks(text, index)
    if index >= len(text) or text[index] != "ل":
        return "", index
    lam, index = take_base_with_marks(text, index)
    return first + lam, index


def split_art_nominal(surface):
    article, index = take_article(surface, 0)
    if not article or index >= len(surface):
        return None
    return [
        {"role": "definite_article", "surface": article, "gloss_contribution": "the"},
        {"role": "stem", "surface": surface[index:], "gloss_contribution": None},
    ]


def split_conj_art_nominal(surface):
    conj, index = take_base_with_marks(surface, 0)
    if strip_marks(conj) != "و":
        return None
    article, index = take_article(surface, index)
    if not article or index >= len(surface):
        return None
    return [
        {"role": "prefix_conjunction", "surface": conj, "gloss_contribution": "and"},
        {"role": "definite_article", "surface": article, "gloss_contribution": "the"},
        {"role": "stem", "surface": surface[index:], "gloss_contribution": None},
    ]


def best_gloss(record):
    glosses = record.get("glosses") or []
    best = record.get("best", 0)
    if isinstance(best, int) and 0 <= best < len(glosses) and isinstance(glosses[best], dict):
        return (glosses[best].get("text") or "").strip()
    return ""


def strip_english_article(gloss):
    return re.sub(r"^\(?the\)?\s+", "", (gloss or "").strip(), flags=re.I).strip()


def load_qac_tokroots(path):
    out = {}
    if not path or not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        surah_ayah, surface, root, pos = parts[:4]
        out[(surah_ayah, strip_marks(surface))] = {"root": root or None, "pos": pos or None}
    return out


def loc_sort_key(loc):
    try:
        return tuple(int(part) for part in str(loc).split(":"))
    except Exception:
        return (999, 999, 999, str(loc))


def display_for(segments, pos):
    def qclass(role):
        if role == "definite_article":
            return "qg-article"
        if role == "prefix_conjunction":
            return "qg-particle"
        if role == "stem":
            return "qg-noun" if pos == "noun" else "qg-unknown"
        return "qg-unknown"

    def label(role):
        return {
            "definite_article": "ART",
            "prefix_conjunction": "CONJ",
            "stem": "STEM",
        }.get(role, "UNK")

    return {
        "palette": "qamus-grammar-v1",
        "segments": [
            {"segment_index": index, "role": segment["role"], "class": qclass(segment["role"]), "label": label(segment["role"])}
            for index, segment in enumerate(segments)
        ],
    }


def candidate_for_record(loc, record, qac, lanes):
    surface = record.get("ar") or ""
    norm = strip_marks(surface)
    surah_ayah = ":".join(str(loc).split(":")[:2])
    qac_row = qac.get((surah_ayah, norm), {})
    if qac_row.get("pos") != "N":
        return None
    if record.get("parse_key") or record.get("display") or record.get("segments"):
        return None

    lane = None
    segments = None
    if "conj_art_nominal" in lanes and norm.startswith("وال"):
        lane = "conj_art_nominal"
        segments = split_conj_art_nominal(surface)
    elif "art_nominal" in lanes and norm.startswith("ال"):
        lane = "art_nominal"
        segments = split_art_nominal(surface)
    if not segments:
        return None

    stem_gloss = strip_english_article(best_gloss(record)) or "host"
    segments[-1]["gloss_contribution"] = stem_gloss
    must_surface = [seg["gloss_contribution"] for seg in segments if seg.get("gloss_contribution")]
    key = "CONJ+ART+N:DEF" if lane == "conj_art_nominal" else "ART+N:DEF"
    summary = (
        "Visible conjunction plus definite noun; case/number/gender require separate certification."
        if lane == "conj_art_nominal"
        else "Visible definite noun; case/number/gender require separate certification."
    )
    components = []
    if lane == "conj_art_nominal":
        components.append({"label": "CONJ", "value": "and"})
    components.extend([
        {"label": "ART", "value": "the"},
        {"label": "N", "value": "definite noun; detailed inflection pending"},
    ])
    return {
        "loc": loc,
        "surface": surface,
        "lemma": None,
        "root": qac_row.get("root"),
        "pos": "noun",
        "morphology": {"state": "definite"},
        "segments": segments,
        "parse_key": {"key": key, "summary": summary, "components": components},
        "display": display_for(segments, "noun"),
        "syntax": {"dependency": "null", "linked_locs": []},
        "hover_contract": {
            "must_surface": must_surface,
            "must_not_surface": ["host only", "duplicate article"],
            "reason": "Visible article/conjunction pieces must be accounted for without splitting the Arabic word.",
        },
        "evidence": {
            "labels": ["qac:tokroots:%s:%s:coarse-pos-root" % (loc, norm)],
            "gate": "human_source_review_required",
            "reasoning": "Coarse QAC POS/root confirms a nominal host for the %s lane; this candidate does not certify deeper i'rab." % lane,
        },
        "public_boundary": dict(PUBLIC_BOUNDARY),
    }


def build_candidates(artifact, qac_path, lanes, limit=None):
    data = json.loads(Path(artifact).read_text(encoding="utf-8"))
    words = data.get("words") or {}
    qac = load_qac_tokroots(qac_path)
    rows = []
    for loc, record in sorted(words.items(), key=lambda item: loc_sort_key(item[0])):
        if not isinstance(record, dict):
            continue
        row = candidate_for_record(loc, record, qac, lanes)
        if row:
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def write_jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sample_artifact(path):
    data = {
        "words": {
            "22:18:13": {"ar": "وَٱلشَّمْسُ", "glosses": [{"text": "sun", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:14": {"ar": "وَٱلْقَمَرُ", "glosses": [{"text": "moon", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:12": {"ar": "ٱلْأَرْضِ", "glosses": [{"text": "earth, land", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:10": {"ar": "وَمَن", "glosses": [{"text": "and whoever", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
        }
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_qac(path):
    Path(path).write_text(
        "\n".join([
            "22:18\tوالشمس\tشمس\tN",
            "22:18\tوالقمر\tقمر\tN",
            "22:18\tالأرض\tأرض\tN",
            "22:18\tومن\t\tP",
            "",
        ]),
        encoding="utf-8",
    )


def self_test():
    with tempfile.TemporaryDirectory() as td:
        artifact = Path(td) / "wbw-lookup.json"
        qac = Path(td) / "qac-tokroots.tsv"
        sample_artifact(artifact)
        sample_qac(qac)
        rows = build_candidates(artifact, qac, {"art_nominal", "conj_art_nominal"})
        assert len(rows) == 3, rows
        by_loc = {row["loc"]: row for row in rows}
        assert by_loc["22:18:13"]["segments"][0]["role"] == "prefix_conjunction", by_loc["22:18:13"]
        assert by_loc["22:18:13"]["segments"][1]["role"] == "definite_article", by_loc["22:18:13"]
        assert by_loc["22:18:12"]["parse_key"]["key"] == "ART+N:DEF", by_loc["22:18:12"]
        assert "QAC" not in json.dumps(by_loc["22:18:13"]["parse_key"], ensure_ascii=False), by_loc["22:18:13"]
        assert by_loc["22:18:13"]["public_boundary"] == PUBLIC_BOUNDARY, by_loc["22:18:13"]
    print("build_rich_hover_morphosyntax_candidates self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build rich-hover morphosyntax metadata candidates.")
    parser.add_argument("artifact", nargs="?", default=str(STAGE / "wbw-lookup.json"))
    parser.add_argument("--qac-tokroots", default=str(STAGE / "qac-tokroots.tsv"))
    parser.add_argument("--out", help="write candidates to JSONL")
    parser.add_argument("--lane", action="append", choices=("art_nominal", "conj_art_nominal"), help="candidate lane; repeatable")
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    lanes = set(args.lane or ["art_nominal", "conj_art_nominal"])
    rows = build_candidates(args.artifact, args.qac_tokroots, lanes, args.max_records or None)
    summary = {"total": len(rows), "by_lane": {}}
    for row in rows:
        lane = "conj_art_nominal" if str(row.get("parse_key", {}).get("key", "")).startswith("CONJ+") else "art_nominal"
        summary["by_lane"][lane] = summary["by_lane"].get(lane, 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if args.out:
        write_jsonl(args.out, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
