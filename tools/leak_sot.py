#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""leak_sot — the single SOURCE OF TRUTH for public-boundary leak detection (P2 deliverable E).

Before P2 the repo had FIVE divergent leak detectors that drifted silently:
  - tools/fusha_check.py LEAK_RE (regex superset)
  - tools/validate_public_private_boundary.py FORBIDDEN_LABELS (tuple, whole-object substring; has c:\\, root.txt)
  - tools/validate_rich_hover_certification.py LEAK_TERMS (tuple, public_payload only — was MISSING tafsir + tanzil)
  - tools/validate_linguistic_decisions.py LEAK_RE (regex, gloss-only scope)
  - tools/validate_morphosyntax_token_metadata.py LEAK_RE (regex, no path patterns)

This module defines the canonical forbidden-token data ONCE and derives BOTH a compiled `LEAK_RE` (regex superset)
and a `FORBIDDEN_LABELS` tuple projection (for `json.dumps(obj).lower()` substring scans). `tools/fusha_check.py`
re-exports `LEAK_RE` from here, so everything that imports `FC.LEAK_RE` (every P1 + P2 validator) gets the SoT
transparently. New P2 emitters (governor justification, conflict reasons, suggestion explanations, learner hints)
scan via `scan()` before emit.

It does NOT rewrite the ~46 leak-bearing validators in the repo (refactor risk); it consolidates the 5 CORE detectors
and is the import target for new code. `tools/validate_source_boundary.py` runs a DIVERGENCE subset-test asserting the
union catches everything each historical detector caught (so drift is caught) and closes the cert tafsir/tanzil gap.

Stdlib only. No network, no writes. The public-boundary invariant is {src:qamus, kind:authored, lang:en}.
See parserplans/general-fusha-grammar-checker-p2/005-leak-detector-source-of-truth.md.
"""
import json
import re

# ---------------------------------------------------------------------------
# canonical forbidden-token data — defined ONCE
# ---------------------------------------------------------------------------
# Internal source / corpus NAMES (uncopyrightable facts may be taken from these, but their NAMES never go public).
SOURCE_NAMES = (
    "qac", "quran.com", "quran-com", "quran_com", "corpus.quran",
    "quranic arabic corpus", "quranic corpus", "quran-text", "tanzil", "mcp", "sunnah.com",
)
# External TRANSLATION brands (the real licensing risk for a public repo).
BRANDS = ("saheeh", "sahih international", "yusuf ali", "pickthall", "arberry", "shakir")
# Variable-suffix source families (tafsir / tafsīr-center / tafsirs; saheeh / saheehs).
SUFFIX_FAMILIES = ("tafsir", "saheeh")
# Internal-provenance labels (kept internal; stripped before publication).
PROVENANCE = ("informed_by", "external_informed_by", "photographed", "ocr", "source-photo", "source_photo")
# Secret file names that must never appear anywhere public.
SECRETS = ("root.txt",)
# Local / server path fragments that must never leak into a public field.
PATH_SUBSTRINGS = ("/srv/", "\\srv\\", "/static/", "c:\\", "/var/", "/tmp/", "/usr/", "/home/", "/opt/", "/etc/", "/mnt/", "/media/")

# ---------------------------------------------------------------------------
# regex superset (word-anchored names/brands + suffix families + path/drive/home/UNC patterns)
# ---------------------------------------------------------------------------
_NAME_ALT = "|".join(re.escape(n) for n in (SOURCE_NAMES + BRANDS + PROVENANCE + SECRETS))
# Word-anchored (\b) for the name/brand/provenance tokens so short ones (ocr/mcp/qac) never substring-match an
# ordinary word (democracy/mediocre/procreation). Hadith brands (sahih*/bukhari*) are forbidden too — the public
# artifact excludes Ṣaḥīḥayn/hadith. Dotted names are re.escape'd so 'quran.com' cannot over-match 'quranXcom'.
LEAK_RE = re.compile(
    r"\b(" + _NAME_ALT + r")\b"
    r"|\btafsir\w*|\bsaheeh\w*|\bsahih\w*|\bbukhari\w*|\byusuf[\s_-]*ali\b"
    r"|/static/|[A-Za-z]:[\\/]|/(?:home|root|users|srv|opt|etc|var|tmp|usr|mnt|media)/"
    r"|(?:^|[\s\"'(])~/|\\\\[A-Za-z0-9._-]+\\",
    re.I,
)

# ---------------------------------------------------------------------------
# tuple projection (for callers that substring-scan a serialized object, incl. field NAMES)
# ---------------------------------------------------------------------------
FORBIDDEN_LABELS = tuple(dict.fromkeys(  # de-duplicate, preserve order
    [s.lower() for s in (SOURCE_NAMES + BRANDS + SUFFIX_FAMILIES + PROVENANCE + SECRETS)]
    + list(PATH_SUBSTRINGS)
))

_REDACTED = "<redacted: leak tripwire>"


def scan(text):
    """Return the list of distinct forbidden tokens found in `text`, via the WORD-ANCHORED LEAK_RE (the single canonical
    matcher). is_leak(s) ⟺ bool(LEAK_RE.search(s)) by construction — the two projections never disagree, so a short
    token like 'ocr' never substring-matches an ordinary word (democracy/mediocre/procreation)."""
    if not text:
        return []
    hits = []
    for m in LEAK_RE.finditer(text):
        frag = (m.group(0) or "").strip().lower()
        if frag and frag not in hits:
            hits.append(frag)
    return hits


def is_leak(text):
    return bool(text) and LEAK_RE.search(text) is not None


def redact(s):
    """Redact a string that trips the tripwire (so untrusted text can never echo into a committed public field)."""
    return _REDACTED if (s and is_leak(s)) else s


def scan_obj(obj):
    """Scan a whole serialized object (catches forbidden field NAMES too — the public-private-boundary scope)."""
    return scan(json.dumps(obj, ensure_ascii=False))


# ---------------------------------------------------------------------------
# field-scope registry — which fields each validator scans (documentation; preserves INTENTIONAL narrow scopes)
# ---------------------------------------------------------------------------
FIELD_SCOPE_REGISTRY = {
    "fusha_check": {"scope": "issue.explanation/observed/expected via _redact", "projection": "regex"},
    "validate_fusha_text_check": {"scope": "diagnostic + suggestion + segment.gloss_contribution + normalization_op.note", "projection": "regex"},
    "validate_rich_hover_candidate": {"scope": "hover_title/token_gloss/contribution/parse_key/segments/card_address", "projection": "regex"},
    "validate_parser_check": {"scope": "issue.explanation/observed/expected + token.gloss/learner_explanation/parse_key + accepted hovers", "projection": "regex"},
    "validate_public_private_boundary": {"scope": "WHOLE serialized public object (catches field names)", "projection": "tuple"},
    "validate_rich_hover_certification": {"scope": "public_payload only (cert review scope)", "projection": "tuple"},
    "validate_linguistic_decisions": {"scope": "gloss_en_authored only (the shipped field) under public_export_allowed", "projection": "regex"},
    "validate_morphosyntax_token_metadata": {"scope": "public-facing metadata strings", "projection": "regex"},
    # P2 emitters — all scan via leak_sot.scan() before emit:
    "fusha_governor": {"scope": "governor_justification/reason fields", "projection": "regex"},
    "fusha_conflicts": {"scope": "reason_for_disagreement/next_action/evidence text", "projection": "regex"},
}

# ---------------------------------------------------------------------------
# historical detectors — used by validate_source_boundary.py for the DIVERGENCE subset-test
# (representative strings that each legacy detector caught; the SoT must catch all of them)
# ---------------------------------------------------------------------------
HISTORICAL_DETECTOR_SAMPLES = {
    "fusha_check.LEAK_RE": ["see qac tagset", "per tafsir center", "saheeh international", "yusuf ali", "/var/www/x", "~/secret"],
    "validate_public_private_boundary.FORBIDDEN_LABELS": ["informed_by here", "mcp tool", "c:\\users\\x", "root.txt", "/srv/app"],
    "validate_rich_hover_certification.LEAK_TERMS": ["informed_by", "source-photo", "/srv/x", "ocr dump"],
    "validate_linguistic_decisions.LEAK_RE": ["external_informed_by", "corpus.quran", "tanzil", "photographed", "/static/x"],
    "validate_morphosyntax_token_metadata.LEAK_RE": ["qac", "quranic arabic corpus", "tafsir", "mcp"],
    # the GAP this SoT closes: the cert validator's tuple did NOT contain tafsir or tanzil
    "cert_gap_closed": ["tafsir", "tanzil"],
    # hadith-brand boundary (the public artifact excludes Ṣaḥīḥayn/hadith): bare 'sahih' / Ṣaḥīḥayn / al-Bukhari
    "hadith_boundary": ["sahih al-bukhari", "Sahih Muslim", "bukhari", "sahihayn"],
}


def _self_test():
    failures = []
    # union catches every historical sample
    for det, samples in HISTORICAL_DETECTOR_SAMPLES.items():
        for s in samples:
            if not is_leak(s):
                failures.append("%s sample %r NOT caught by leak_sot (drift)" % (det, s))
    # clean strings stay clean — incl. ordinary English that CONTAINS a short forbidden trigram (ocr/mcp/qac) mid-word;
    # the word-anchored regex must NOT redact these (the substring-projection bug E/F).
    for clean in ("upon us", "at Badr", "the worlds", "it was said", "asks you", "and by the star",
                  "genitive after the preposition", "a coordinating waw",
                  "democracy", "mediocre", "procreation", "microcredit", "hypocrisy", "advocacy", "Muslim scholar"):
        if is_leak(clean):
            failures.append("clean string %r false-positives (substring projection drift)" % clean)
    # the two projections must agree: is_leak(s) ⟺ bool(LEAK_RE.search(s)) (define once, derive consistently)
    for s in ("ocr dump", "democracy", "see qac", "informed_by x", "tafsir center", "sahih al-bukhari", "upon us", "/var/x"):
        if is_leak(s) != bool(LEAK_RE.search(s)):
            failures.append("is_leak/LEAK_RE disagree on %r" % s)
    # tuple projection is a non-empty superset of the legacy two tuples' members
    for legacy in ("informed_by", "mcp", "qac", "quran.com", "tanzil", "tafsir", "ocr", "source-photo", "/srv/", "c:\\", "root.txt"):
        if legacy not in FORBIDDEN_LABELS:
            failures.append("FORBIDDEN_LABELS missing legacy member %r" % legacy)
    # redact round-trips
    if redact("see qac") != _REDACTED or redact("upon us") != "upon us":
        failures.append("redact() behaviour wrong")
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   leak_sot self-test: union catches all 5 legacy detectors' samples + closes the cert tafsir/tanzil gap; clean stays clean")
    return 0 if not failures else 1


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print("leak_sot: %d forbidden labels, LEAK_RE compiled. Use scan()/is_leak()/redact()." % len(FORBIDDEN_LABELS))
