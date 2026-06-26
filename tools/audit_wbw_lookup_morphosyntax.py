#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit a deployed qamus-highlight wbw lookup artifact for visible composition.

This is an offline checker. It reads a `wbw-lookup.json` artifact and reports
records where the visible tooltip can hide or duplicate function-bearing pieces:

- duplicate definite article: `data-pre="the"` plus gloss text starting "the"
- `و` + `ال` surfaces whose pre-channel does not expose both "and" and "the"
- `ب` + `ال` surfaces whose tooltip does not expose a bāʾ relation
- suffix pendings that need a pronoun-aware lane, not a vague gap

It does not consult live Qamus and does not mutate artifacts.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

SAFE_QG_CLASSES = {
    "qg-article",
    "qg-case",
    "qg-comitative",
    "qg-exception",
    "qg-negative",
    "qg-noun",
    "qg-oath",
    "qg-particle",
    "qg-preposition",
    "qg-pronoun",
    "qg-proper-noun",
    "qg-relation",
    "qg-relative",
    "qg-result",
    "qg-unknown",
    "qg-verb",
    "qg-vocative",
}

PUBLIC_SOURCE_LEAK_RE = re.compile(r"\b(QAC|MCP|Quran\.com|corpus\.quran|tafsir[-_ ]?center)\b", re.I)


def strip_marks(text):
    text = HARAKAT_RE.sub("", text or "")
    return (
        text.replace("ٱ", "ا")
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
    )


def best_gloss(record):
    glosses = record.get("glosses") or []
    best = record.get("best", 0)
    if isinstance(best, int) and 0 <= best < len(glosses) and isinstance(glosses[best], dict):
        return (glosses[best].get("text") or "").strip()
    return ""


def words(text):
    return re.findall(r"[a-z]+", (text or "").lower())


def pre_words(record):
    return words(record.get("pre") or "")


def starts_with_article(gloss):
    return bool(re.match(r"^\(?the\)?\s+", (gloss or "").strip(), re.I))


def has_definite_article(surface):
    stripped = strip_marks(surface)
    return any(stripped.startswith(prefix) for prefix in ("وال", "فال", "بال", "كال", "ولل", "فلل", "لل", "ال"))


def starts_waw_article(surface):
    return strip_marks(surface).startswith("وال")


def starts_article(surface):
    return strip_marks(surface).startswith("ال")


def starts_ba_article(surface):
    return strip_marks(surface).startswith("بال")


def starts_fa_article(surface):
    return strip_marks(surface).startswith("فال")


def issue(loc, record, issue_class, severity, reason):
    return {
        "loc": loc,
        "class": issue_class,
        "severity": severity,
        "ar": record.get("ar", ""),
        "pre": record.get("pre", ""),
        "suf": record.get("suf", ""),
        "gloss": best_gloss(record),
        "reason": reason,
    }


def _segment_weight(text):
    return max(1, len(strip_marks(text)))


def _has_complete_rich_metadata(record):
    return bool(record.get("parse_key") and record.get("display") and record.get("segments"))


def _rich_metadata_issues(loc, record):
    issues = []
    has_parse = bool(record.get("parse_key"))
    has_display = bool(record.get("display"))
    has_segments = bool(record.get("segments"))
    if not (has_parse or has_display or has_segments):
        return issues

    if not (has_parse and has_display and has_segments):
        issues.append(
            issue(
                loc,
                record,
                "rich_metadata_incomplete",
                "error",
                "Rich hover metadata must carry parse_key, display, and segments together.",
            )
        )

    segments = record.get("segments") or []
    display_segments = (record.get("display") or {}).get("segments") or []
    if segments and display_segments and len(segments) != len(display_segments):
        issues.append(
            issue(
                loc,
                record,
                "rich_display_segment_count_mismatch",
                "error",
                "display.segments must align one-for-one with grammar segments.",
            )
        )

    if segments:
        surface_weight = _segment_weight(record.get("ar", ""))
        segment_weight = sum(_segment_weight(seg.get("surface", "")) for seg in segments if isinstance(seg, dict))
        if surface_weight != segment_weight:
            issues.append(
                issue(
                    loc,
                    record,
                    "rich_kawkab_segment_width_mismatch",
                    "error",
                    "Segment surfaces do not add up to the atomic Arabic token, so Kawkab gradient stops will drift.",
                )
            )

    for seg in display_segments:
        qg_class = seg.get("class") if isinstance(seg, dict) else None
        if qg_class and qg_class not in SAFE_QG_CLASSES:
            issues.append(
                issue(
                    loc,
                    record,
                    "rich_display_class_unsafe",
                    "error",
                    "display.segments contains a class outside the scrubbed qamus grammar palette.",
                )
            )

    public_payload = json.dumps(
        {
            "parse_key": record.get("parse_key"),
            "display": record.get("display"),
            "segments": record.get("segments"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if PUBLIC_SOURCE_LEAK_RE.search(public_payload):
        issues.append(
            issue(
                loc,
                record,
                "rich_public_source_label_leak",
                "error",
                "Public rich-hover metadata must not expose QAC/MCP/source labels.",
            )
        )

    return issues


def _candidate_lane_for_missing_rich(record):
    surface = record.get("ar", "")
    if starts_waw_article(surface):
        return "candidate_conj_art_nominal"
    if starts_fa_article(surface):
        return "candidate_fa_art_nominal"
    if starts_ba_article(surface):
        return "candidate_ba_art_nominal"
    if starts_article(surface):
        return "candidate_art_nominal"
    if record.get("suf"):
        return "candidate_suffix_or_pronoun"
    if record.get("pre"):
        return "candidate_prefix_or_function_piece"
    return None


def _rich_coverage(records):
    coverage = {
        "total_records": 0,
        "with_parse_key": 0,
        "with_display": 0,
        "with_segments": 0,
        "rich_complete": 0,
        "rich_partial": 0,
        "rich_missing": 0,
        "kawkab_aligned_complete": 0,
        "kawkab_misaligned_complete": 0,
        "missing_candidate_lanes": {},
    }
    for record in records.values():
        if not isinstance(record, dict):
            continue
        coverage["total_records"] += 1
        has_parse = bool(record.get("parse_key"))
        has_display = bool(record.get("display"))
        has_segments = bool(record.get("segments"))
        if has_parse:
            coverage["with_parse_key"] += 1
        if has_display:
            coverage["with_display"] += 1
        if has_segments:
            coverage["with_segments"] += 1

        if has_parse and has_display and has_segments:
            coverage["rich_complete"] += 1
            surface_weight = _segment_weight(record.get("ar", ""))
            segment_weight = sum(
                _segment_weight(seg.get("surface", ""))
                for seg in (record.get("segments") or [])
                if isinstance(seg, dict)
            )
            if surface_weight == segment_weight:
                coverage["kawkab_aligned_complete"] += 1
            else:
                coverage["kawkab_misaligned_complete"] += 1
        elif has_parse or has_display or has_segments:
            coverage["rich_partial"] += 1
        else:
            coverage["rich_missing"] += 1
            lane = _candidate_lane_for_missing_rich(record)
            if lane:
                coverage["missing_candidate_lanes"][lane] = coverage["missing_candidate_lanes"].get(lane, 0) + 1

    total = coverage["total_records"] or 1
    coverage["rich_complete_percent"] = round((coverage["rich_complete"] / total) * 100, 4)
    return coverage


def analyze_artifact(artifact):
    data = json.loads(Path(artifact).read_text(encoding="utf-8"))
    records = data.get("words") or {}
    pending = data.get("pending") or {}
    issues = []

    for loc, record in sorted(records.items(), key=lambda item: _loc_sort_key(item[0])):
        if not isinstance(record, dict):
            continue
        surface = record.get("ar", "")
        gloss = best_gloss(record)
        pwords = pre_words(record)
        glow = gloss.lower()

        issues.extend(_rich_metadata_issues(loc, record))

        if "the" in pwords and starts_with_article(gloss):
            issues.append(
                issue(
                    loc,
                    record,
                    "duplicate_definite_article",
                    "error",
                    "Tooltip will render the article twice: pre contains 'the' and gloss starts with 'the'.",
                )
            )

        if starts_waw_article(surface) and not ({"and", "the"} <= set(pwords)):
            if not glow.startswith("and the "):
                issues.append(
                    issue(
                        loc,
                        record,
                        "waw_article_not_segmented",
                        "warn",
                        "Surface begins with waw + definite article, but the pre-channel does not expose both pieces.",
                    )
                )

        if starts_fa_article(surface) and not ("the" in pwords and ("so" in pwords or "then" in pwords)):
            if not glow.startswith(("so the ", "then the ")):
                issues.append(
                    issue(
                        loc,
                        record,
                        "fa_article_not_segmented",
                        "warn",
                        "Surface begins with fa + definite article, but the tooltip does not expose both pieces.",
                    )
                )

        if starts_ba_article(surface):
            has_relation = any(w in pwords for w in ("with", "by", "in", "at", "because", "through"))
            gloss_has_relation = glow.startswith(("with ", "by ", "in ", "at ", "because ", "through "))
            if not (has_relation or gloss_has_relation):
                issues.append(
                    issue(
                        loc,
                        record,
                        "ba_article_relation_omitted",
                        "warn",
                        "Surface begins with bāʾ + definite article, but the tooltip does not expose the bāʾ relation.",
                    )
                )

        if has_definite_article(surface) and "the" not in pwords and not starts_with_article(gloss):
            issues.append(
                issue(
                    loc,
                    record,
                    "article_not_visible",
                    "info",
                    "Surface contains a definite article, but neither pre-channel nor gloss text surfaces 'the'.",
                )
            )

    for loc, code in sorted(pending.items(), key=lambda item: _loc_sort_key(item[0])):
        if code == "suffix":
            issues.append(
                {
                    "loc": loc,
                    "class": "suffix_pending",
                    "severity": "info",
                    "ar": "",
                    "pre": "",
                    "suf": "",
                    "gloss": "",
                    "reason": "Pending suffix/pronoun row needs the pronoun-aware sarf+nahw lane.",
                }
            )

    return issues, _rich_coverage(records)


def audit_artifact(artifact):
    issues, _coverage = analyze_artifact(artifact)
    return issues


def _loc_sort_key(loc):
    try:
        return tuple(int(part) for part in str(loc).split(":"))
    except Exception:
        return (999, 999, 999, str(loc))


def summarize(issues, coverage=None):
    out = {"total": len(issues), "by_class": {}, "by_severity": {}}
    for row in issues:
        out["by_class"][row["class"]] = out["by_class"].get(row["class"], 0) + 1
        out["by_severity"][row["severity"]] = out["by_severity"].get(row["severity"], 0) + 1
    if coverage is not None:
        out["rich_metadata"] = coverage
    return out


def should_fail(issues, fail_on):
    if fail_on == "none":
        return False
    severity_rank = {"error": 1, "warn": 2, "info": 3}
    threshold = severity_rank[fail_on]
    return any(severity_rank[row["severity"]] <= threshold for row in issues)


def write_jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _sample_artifact(path):
    data = {
        "_meta": {"schema": "wbw.schema.json"},
        "pending": {"26:139:2": "suffix"},
        "words": {
            "2:13:12": {
                "loc": "2:13:12",
                "ar": "ٱلسُّفَهَاءُ",
                "pre": "the",
                "glosses": [{"text": "the foolish ones", "src": "qamus", "kind": "authored", "lang": "en"}],
                "best": 0,
            },
            "22:18:13": {
                "loc": "22:18:13",
                "ar": "وَٱلشَّمْسُ",
                "pre": "and",
                "glosses": [{"text": "sun", "src": "qamus", "kind": "authored", "lang": "en"}],
                "best": 0,
            },
            "22:29:7": {
                "loc": "22:29:7",
                "ar": "بِٱلْبَيْتِ",
                "glosses": [{"text": "Sacred House", "src": "qamus", "kind": "authored", "lang": "en"}],
                "best": 0,
            },
            "22:18:12": {
                "loc": "22:18:12",
                "ar": "ٱلْأَرْضِ",
                "pre": "the",
                "glosses": [{"text": "earth, land", "src": "qamus", "kind": "authored", "lang": "en"}],
                "best": 0,
            },
            "33:63:1": {
                "loc": "33:63:1",
                "ar": "يَسْأَلُكَ",
                "parse_key": {"key": "V:I:IMPF:ACT:3MS+OBJ.2MS"},
                "display": {
                    "segments": [
                        {"class": "qg-verb", "label": "PFX"},
                        {"class": "qg-verb", "label": "STEM"},
                        {"class": "qg-pronoun", "label": "PRON"},
                    ]
                },
                "segments": [
                    {"surface": "يَ"},
                    {"surface": "سْأَلُ"},
                    {"surface": "كَ"},
                ],
                "glosses": [{"text": "ask you", "src": "qamus", "kind": "authored", "lang": "en"}],
                "best": 0,
            },
            "99:1:2": {
                "loc": "99:1:2",
                "ar": "زُلْزِلَتِ",
                "parse_key": {"key": "V:PASS:PERF"},
                "display": {"segments": [{"class": "qg-verb", "label": "V"}]},
                "segments": [{"surface": "زُلْزِلَ"}],
                "glosses": [{"text": "was shaken", "src": "qamus", "kind": "authored", "lang": "en"}],
                "best": 0,
            },
        },
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_test():
    with tempfile.TemporaryDirectory() as td:
        artifact = Path(td) / "wbw-lookup.json"
        _sample_artifact(artifact)
        issues, coverage = analyze_artifact(artifact)
        classes = {row["class"] for row in issues}
        assert "duplicate_definite_article" in classes, issues
        assert "waw_article_not_segmented" in classes, issues
        assert "ba_article_relation_omitted" in classes, issues
        assert "rich_kawkab_segment_width_mismatch" in classes, issues
        assert "suffix_pending" in classes, issues
        assert not any(row["loc"] == "22:18:12" for row in issues), issues
        assert coverage["rich_complete"] == 2, coverage
        assert coverage["kawkab_aligned_complete"] == 1, coverage
        assert coverage["kawkab_misaligned_complete"] == 1, coverage
        assert coverage["missing_candidate_lanes"]["candidate_conj_art_nominal"] == 1, coverage
        assert coverage["missing_candidate_lanes"]["candidate_ba_art_nominal"] == 1, coverage
        assert not should_fail(issues, "none")
        assert should_fail(issues, "error")
    print("audit_wbw_lookup_morphosyntax self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit qamus-highlight wbw lookup morphosyntax visibility.")
    parser.add_argument("artifact", nargs="?", help="path to wbw-lookup.json")
    parser.add_argument("--jsonl-out", help="write issue rows to JSONL")
    parser.add_argument("--summary-json", help="write summary JSON")
    parser.add_argument(
        "--fail-on",
        choices=("none", "error", "warn", "info"),
        default="error",
        help="exit non-zero when this severity or stricter is present (default: error)",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    if not args.artifact:
        parser.error("artifact path required, or pass --self-test")

    issues, coverage = analyze_artifact(args.artifact)
    summary = summarize(issues, coverage)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if args.jsonl_out:
        write_jsonl(args.jsonl_out, issues)
    if args.summary_json:
        Path(args.summary_json).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if should_fail(issues, args.fail_on):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
