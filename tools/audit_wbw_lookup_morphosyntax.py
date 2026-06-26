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


def audit_artifact(artifact):
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

    return issues


def _loc_sort_key(loc):
    try:
        return tuple(int(part) for part in str(loc).split(":"))
    except Exception:
        return (999, 999, 999, str(loc))


def summarize(issues):
    out = {"total": len(issues), "by_class": {}, "by_severity": {}}
    for row in issues:
        out["by_class"][row["class"]] = out["by_class"].get(row["class"], 0) + 1
        out["by_severity"][row["severity"]] = out["by_severity"].get(row["severity"], 0) + 1
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
        },
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_test():
    with tempfile.TemporaryDirectory() as td:
        artifact = Path(td) / "wbw-lookup.json"
        _sample_artifact(artifact)
        issues = audit_artifact(artifact)
        classes = {row["class"] for row in issues}
        assert "duplicate_definite_article" in classes, issues
        assert "waw_article_not_segmented" in classes, issues
        assert "ba_article_relation_omitted" in classes, issues
        assert "suffix_pending" in classes, issues
        assert not any(row["loc"] == "22:18:12" for row in issues), issues
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

    issues = audit_artifact(args.artifact)
    summary = summarize(issues)
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
