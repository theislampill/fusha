#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert a Tafsir MCP analyze_word response into STRUCTURED token-state evidence (for the language state machine).

The MCP returns rich Arabic prose (sarf + irab). This extracts conservative, machine-checkable signals — POS,
tense, voice, verb-form I-X, number/person, case/mood, root — by keyword-matching the analysis. A field is set
ONLY when a clear marker is present (else null), so downstream gates never over-trust a guess.

Output conforms to the evidence sub-object the sarf/nahw decision carries. INTERNAL only — never public.

Usage: python tools/mcp_to_language_state.py <cache_record.json>   (or pipe an analyze_word response on stdin)
"""
import json
import sys


def _has(text, *needles):
    return any(n in text for n in needles)


def extract(resp):
    sarf = resp.get("sarf") or ""
    irab = resp.get("irab") or ""
    both = sarf + " " + irab
    ev = {
        "word": resp.get("word"), "root": resp.get("root"),
        "pos": None, "tense": None, "voice": None, "verb_form": None,
        "number": None, "person": None, "case_mood": None,
        "definite": None, "mcp_meaning_present": bool(resp.get("meaning")),
    }
    # POS — classify on the LEADING classification token (after the first ':'), NOT anywhere in the prose.
    # (The wazn pattern name "(فِعْلٌ)" is a NOUN pattern, so a naive whole-string scan mislabels nouns as verbs.)
    head = sarf.split(":", 1)[1].split("،", 1)[0] if ":" in sarf else sarf[:24]
    if _has(head, "فِعْل", "فعل"):
        ev["pos"] = "verb"
    elif _has(head, "حَرْف", "حرف"):
        ev["pos"] = "particle"
    elif _has(head, "اسْم", "اِسْم", "اسم"):
        ev["pos"] = "noun"
    # tense (verbs)
    if _has(both, "مُضَارِع", "مضارع"):
        ev["tense"] = "imperfect"
    elif _has(both, "مَاضٍ", "ماض", "الْمَاضِي"):
        ev["tense"] = "perfect"
    elif _has(both, "أَمْر", "الأمر"):
        ev["tense"] = "imperative"
    # voice
    if _has(both, "لِلْمَجْهُول", "للمجهول", "مَبْنِيٌّ لِلْمَجْهُول"):
        ev["voice"] = "passive"
    elif _has(both, "لِلْمَعْلُوم", "للمعلوم"):
        ev["voice"] = "active"
    # verb form (wazn / باب)
    forms = [("X", ("اِسْتَفْعَلَ", "استفعل")), ("IV", ("أَفْعَلَ", "أفعل", "إفعال")),
             ("II", ("فَعَّلَ", "فعّل", "تَفْعِيل")), ("III", ("فَاعَلَ", "فاعل", "مُفَاعَلَة")),
             ("VI", ("تَفَاعَلَ", "تفاعل")), ("V", ("تَفَعَّلَ", "تفعّل")),
             ("VIII", ("اِفْتَعَلَ", "افتعل")), ("VII", ("اِنْفَعَلَ", "انفعل")),
             ("IX", ("اِفْعَلَّ", "افعلّ"))]
    for code, needles in forms:
        if _has(both, *needles):
            ev["verb_form"] = code
            break
    if ev["verb_form"] is None and ev["pos"] == "verb" and _has(both, "ثُلَاثِيٌّ مُجَرَّد", "ثلاثي مجرد", "مُجَرَّد"):
        ev["verb_form"] = "I"
    # number / person
    if _has(both, "الْغَائِبِين", "للغائبين", "جَمْعِ الْغَائِبِين"):
        ev["person"], ev["number"] = "3", "plural"
    elif _has(both, "الْمُتَكَلِّمِين", "المتكلمين", "نَا الْفَاعِلِين"):
        ev["person"], ev["number"] = "1", "plural"
    if _has(both, "جَمْع", "جمع"):
        ev["number"] = ev["number"] or "plural"
    elif _has(both, "مُثَنّى", "مثنى"):
        ev["number"] = "dual"
    elif _has(both, "مُفْرَد", "مفرد"):
        ev["number"] = ev["number"] or "singular"
    # case / mood
    if _has(irab, "مَرْفُوع", "مرفوع"):
        ev["case_mood"] = "rafʿ"
    elif _has(irab, "مَنْصُوب", "منصوب"):
        ev["case_mood"] = "naṣb"
    elif _has(irab, "مَجْرُور", "مجرور"):
        ev["case_mood"] = "jarr"
    elif _has(irab, "مَجْزُوم", "مجزوم"):
        ev["case_mood"] = "jazm"
    # definiteness
    if _has(both, "مَعْرِفَة", "بِأَلْ", "مُعَرَّف"):
        ev["definite"] = True
    elif _has(both, "نَكِرَة", "تَنْوِين"):
        ev["definite"] = False
    return ev


def main():
    if len(sys.argv) > 1:
        rec = json.load(open(sys.argv[1], encoding="utf-8"))
        resp = rec.get("response", rec)
    else:
        resp = json.load(sys.stdin)
    print(json.dumps(extract(resp), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
