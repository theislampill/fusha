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


def split_vocab_forms(raw_field, ar_only):
    """For AMAU vocab cards, return (headword_singular, plural, extra_tokens).

    Shape: ``( <plural>) <singular>`` — plural inside parens precedes the singular
    headword. Heuristic: if the raw field has a '(' and exactly two Arabic tokens,
    the FIRST clean token is the plural, the LAST is the singular headword.
    """
    toks = [strip_punct(t) for t in ar_only.split()]
    toks = [t for t in toks if t]
    if not toks:
        return "", "", []
    has_paren = "(" in (raw_field or "")
    if len(toks) == 2 and has_paren:
        return toks[1], toks[0], []
    if len(toks) == 1:
        return toks[0], "", []
    # >2 tokens: last is usually the headword; treat the rest as extra forms
    return toks[-1], (toks[0] if has_paren else ""), toks[:-1]


def nfc(s):
    return unicodedata.normalize("NFC", s or "")
