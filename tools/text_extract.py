"""Shared text helpers for the sarf/nahw corpus ingest (SN1/SN2).

Stdlib only. Strips note/PDF HTML while preserving Arabic text, transliteration,
and English gloss; records (but never copies) media references; classifies
script. No external dependency, no media bytes ever touched.
"""
import re
import html
import unicodedata

# Arabic block + supplement + extended-A + presentation forms.
_AR = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_SOUND = re.compile(r"\[sound:[^\]]*\]")
_IMG = re.compile(r"<img[^>]*?src\s*=\s*['\"]([^'\"]+)['\"][^>]*?>", re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t ]+")
_LATIN = re.compile(r"[A-Za-z]")


def media_refs(s):
    """Return media filenames referenced (img src + [sound:...]) — for the record only."""
    refs = []
    for m in _IMG.finditer(s or ""):
        refs.append(m.group(1))
    for m in re.finditer(r"\[sound:([^\]]+)\]", s or ""):
        refs.append(m.group(1))
    return refs


def strip_html(s):
    """HTML -> readable text. Drops <img>/[sound:] (kept separately as media_refs),
    converts <br>/<div>/<p> to spaces, unescapes entities, collapses whitespace."""
    if not s:
        return ""
    s = _SOUND.sub(" ", s)
    s = _IMG.sub(" ", s)
    s = re.sub(r"<\s*br\s*/?\s*>", " ", s, flags=re.I)
    s = re.sub(r"<\s*/?\s*(div|p|tr|td|table|li|ul|ol|span|b|i|u|strong|em|font|h[1-6])[^>]*>",
               " ", s, flags=re.I)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = s.replace("‌", "").replace("‎", "").replace("‏", "")
    s = _WS.sub(" ", s).strip()
    return s


def arabic_ratio(s):
    if not s:
        return 0.0
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    ar = sum(1 for c in letters if _AR.match(c))
    return ar / len(letters)


def has_arabic(s):
    return bool(_AR.search(s or ""))


def has_latin(s):
    return bool(_LATIN.search(s or ""))


def arabic_tokens(s):
    """Whitespace tokens that are mostly Arabic script (drops punctuation-only)."""
    out = []
    for t in (s or "").split():
        core = t.strip("().,،؛:!?\"'«»-—…ـ")
        if core and arabic_ratio(core) >= 0.5:
            out.append(core)
    return out


def looks_transliteration(s):
    """Heuristic: Latin text with translit diacritics or typical romanized-Arabic shape."""
    if not s or not has_latin(s) or has_arabic(s):
        return False
    if re.search(r"[āīūṣḍṭẓʿʾḥṯḏšġ’ʻ]", s):
        return True
    # apostrophe-marked ayn/hamza + short tokens
    return bool(re.search(r"[a-z]'[a-z]", s)) and len(s.split()) <= 8


_PUNCT = "().,،؛:!?\"'«»-—…ـ[]{}؟"


def strip_punct(t):
    return (t or "").strip(_PUNCT).strip()


def arabic_script_only(s):
    """Drop romanization/Latin tokens, keep only Arabic-script tokens (diacritics kept).

    AMAU fields mix translit + Arabic inline, e.g. ``( kutub-un كُتُبٌ) kitaab-un كِتَابٌ``
    -> ``كُتُبٌ كِتَابٌ``. Per-token: keep a token iff it contains Arabic script, after
    stripping any embedded Latin letters and wrapping punctuation.
    """
    out = []
    for tok in (s or "").split():
        core = "".join(ch for ch in tok if not ("a" <= ch.lower() <= "z"))
        core = strip_punct(core)
        if core and _AR.search(core):
            out.append(core)
    return " ".join(out).strip()


_MARKS = re.compile(r"[ً-ٰٕـ]")


def _letters(t):
    return _MARKS.sub("", t or "")


def is_sound_plural(t):
    """Reliable: a sound plural ends in ـُونَ/ـِينَ (masc) or ـَاتٌ (fem)."""
    s = _letters(t)
    return s.endswith("ون") or s.endswith("ين") or s.endswith("ات")


def split_vocab_forms(raw_field, ar_only):
    """For AMAU vocab cards, return (headword_singular, plural, extra_tokens, orientation).

    Orientation of the two forms:
      * "sound"  — one token is a sound plural (ون/ين/ات): morphologically CERTAIN.
      * "paren"  — neither is a sound plural; fall back to the deck's ``(plural) singular``
                   parenthesis convention. This is a HEURISTIC: broken↔broken pairs share
                   skeleton shapes (كِتَاب فِعَال-singular vs كُتُب فُعُل-plural — shape cannot
                   decide), and the deck is not perfectly consistent, so the singular/plural
                   LABEL here is not certified (the SN9 review flagged inverted cases).
      * "single"/"multi" for 1 or >2 tokens.
    """
    toks = [strip_punct(t) for t in ar_only.split()]
    toks = [t for t in toks if t]
    if not toks:
        return "", "", [], "none"
    if len(toks) == 1:
        return toks[0], "", [], "single"
    if len(toks) == 2:
        a, b = toks[0], toks[1]
        # sound-plural override (reliable, independent of paren order)
        if is_sound_plural(a) and not is_sound_plural(b):
            return b, a, [], "sound"
        if is_sound_plural(b) and not is_sound_plural(a):
            return a, b, [], "sound"
        # else: paren convention (plural first in parens) — heuristic, label uncertain
        has_paren = "(" in (raw_field or "")
        if has_paren:
            return b, a, [], "paren"
        return a, b, [], "paren"
    # >2 tokens
    return toks[-1], (toks[0] if "(" in (raw_field or "") else ""), toks[:-1], "multi"


def nfc(s):
    return unicodedata.normalize("NFC", s or "")
