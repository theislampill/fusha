#!/usr/bin/env python3
"""Fail-closed checks for known Qamus hover regressions.

This reads a built ``wbw-lookup.json`` artifact and checks source-addressed
tokens that previously leaked host-only, root-family, or pending glosses.
The script is public-safe: it contains only Qamus-authored expectations and
does not embed external source text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CASES = [
    {
        "loc": "95:1:5",
        "surface": "وَٱلتِّينِ",
        "must": ["by", "fig"],
        "must_not": ["to know"],
        "why": "oath waw must not collapse to a host-only fruit gloss",
    },
    {
        "loc": "95:1:6",
        "surface": "وَٱلزَّيْتُونِ",
        "must": ["by", "olive"],
        "must_not": ["to know"],
        "why": "coordinated oath item still needs the oath relation",
    },
    {
        "loc": "95:2:1",
        "surface": "وَطُورِ",
        "must": ["by", "Mount"],
        "must_not": ["to know"],
        "why": "oath continuation must not render as a plain noun phrase",
    },
    {
        "loc": "95:3:1",
        "surface": "وَهَٰذَا",
        "must": ["by", "this"],
        "must_not": ["to know"],
        "why": "oath continuation must keep the qasam function",
    },
    {
        "loc": "16:16:2",
        "surface": "وَبِالنَّجْمِ",
        "must": ["by", "star"],
        "must_not": ["pending", "not yet", "to know"],
        "why": "waw + instrumental ba plus majrur host must not remain pending",
    },
    {
        "loc": "6:13:9",
        "surface": "ٱلْعَلِيمُ",
        "must": ["All-Knowing"],
        "must_not": ["also to teach", "to learn"],
        "why": "divine-name form cannot inherit a broad root-family gloss",
    },
    {
        "loc": "44:14:2",
        "surface": "مُعَلَّمٌ",
        "must": ["taught"],
        "must_not": ["also to teach", "to learn"],
        "why": "passive participle needs a form-aware gloss",
    },
    {
        "loc": "2:54:16",
        "surface": "ذَٰلِكُمْ",
        "must": ["that"],
        "must_not": ["for, belongs", "certainly/surely"],
        "why": "demonstrative must not inherit the neighboring lam/pronoun hover",
    },
    {
        "loc": "12:32:2",
        "surface": "فَذَٰلِكُنَّ",
        "must": ["so", "that"],
        "must_not": ["for, belongs", "certainly/surely"],
        "why": "fa plus demonstrative token must preserve the prefix contribution",
    },
    {
        "loc": "12:37:3",
        "surface": "عَلَّمَنِي",
        "must": ["taught", "me"],
        "must_not": ["also to teach", "to learn", "pending"],
        "why": "Form II verb with object suffix needs a form-aware suffix-preserving hover",
    },
    {
        "loc": "2:3:3",
        "surface": "بِٱلْغَيْبِ",
        "must": ["in", "unseen"],
        "must_not": ["absent, hidden, unseen, or unknown"],
        "why": "attached ba plus majrur host must not collapse to a host-only definition",
    },
    {
        "loc": "2:102:21",
        "surface": "بِبَابِلَ",
        "must": ["in", "Babylon"],
        "must_not": ["pending"],
        "why": "locative ba plus proper place must not collapse to host-only proper noun",
    },
    {
        "loc": "1:2:1",
        "surface": "ٱلْحَمْدُ",
        "must": ["praise"],
        "must_not": ["to praise", "to be praised"],
        "why": "masdar/noun form must not inherit an infinitive root-family gloss",
    },
    {
        "loc": "17:79:12",
        "surface": "مَّحْمُودًا",
        "must": ["praised"],
        "must_not": ["to praise", "to be praised"],
        "why": "passive participle/adjective must not inherit an infinitive root-family gloss",
    },
    {
        "loc": "35:15:10",
        "surface": "ٱلْحَمِيدُ",
        "must": ["Praiseworthy"],
        "must_not": ["to praise", "to be praised"],
        "why": "divine-name/adjectival form must not inherit an infinitive root-family gloss",
    },
    {
        "loc": "7:157:8",
        "surface": "مَكْتُوبًا",
        "must": ["written"],
        "must_not": ["to write", "to decree"],
        "why": "passive participle must not inherit an infinitive root-family gloss",
    },
    {
        "loc": "104:6:3",
        "surface": "ٱلْمُوقَدَةُ",
        "must": ["kindled"],
        "must_not": ["to kindle"],
        "why": "passive participle/adjective must not inherit an infinitive root-family gloss",
    },
    {
        "loc": "2:10:9",
        "surface": "أَلِيمٌ",
        "must": ["painful"],
        "must_not": ["to be in pain"],
        "why": "adjectival form must not inherit a verb-state gloss",
    },
    {
        "loc": "10:48:4",
        "surface": "ٱلْوَعْدُ",
        "must": ["promise"],
        "must_not": ["to promise"],
        "why": "noun/masdar form must not inherit an infinitive verb gloss",
    },
]


def best_text(rec: dict | None) -> str:
    if not rec:
        return ""
    glosses = rec.get("glosses") or []
    best = rec.get("best", 0)
    if isinstance(best, int) and 0 <= best < len(glosses):
        return str(glosses[best].get("text") or "")
    if glosses:
        return str(glosses[0].get("text") or "")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", help="Path to built wbw-lookup.json")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable result")
    args = parser.parse_args()

    artifact = Path(args.artifact)
    data = json.loads(artifact.read_text(encoding="utf-8"))
    words = data.get("words") or {}
    pending = data.get("pending") or {}

    failures = []
    for case in CASES:
        loc = case["loc"]
        rec = words.get(loc)
        text = best_text(rec)
        pending_reason = pending.get(loc)
        haystack = " ".join(
            part for part in [text, str(rec.get("pre") if rec else ""), str(pending_reason or "")] if part
        )
        low = haystack.lower()
        missing = [needle for needle in case["must"] if needle.lower() not in low]
        forbidden = [needle for needle in case["must_not"] if needle.lower() in low]
        if not rec or pending_reason or missing or forbidden:
            failures.append(
                {
                    "loc": loc,
                    "surface": case["surface"],
                    "actual": haystack,
                    "missing": missing,
                    "forbidden": forbidden,
                    "pending": pending_reason,
                    "why": case["why"],
                }
            )

    result = {
        "artifact": str(artifact),
        "checked": len(CASES),
        "failures": failures,
        "ok": not failures,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif failures:
        for failure in failures:
            print(
                "FAIL {loc} {surface}: {actual!r}; missing={missing}; forbidden={forbidden}; "
                "pending={pending}; why={why}".format(**failure)
            )
    else:
        print(f"OK hover regression cases checked={len(CASES)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
