#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalogue the Arabic surface vocabulary of al-Arbaʿīn al-Nawawiyyah (the "Forty",
hadith 1–42 incl. Ibn Rajab's additions) — stage 1 of the catalogue-first pilot.

WHAT THIS DOES
  * Reads a LOCAL dump of the 40/42 hadith Arabic texts from --src (JSON or JSONL).
    It does NOT scrape, fetch, or embed any text inline. You point --src at a file
    you assembled separately; this script only reads it and records HOW it was obtained
    (the dump's own access-method note, echoed into every output record's provenance).
  * Tokenizes each hadith's Arabic, preserves the OBSERVED surface form verbatim
    (never altered — scripture/hadith text is read-only), and computes three match keys
    via tools/normalize_ar.py: norm (lenient recall), norm_strict (hamza-aware, the
    one that may certify), bare (enclitic detection).
  * Counts surface-form frequency and keeps the set of hadith refs each form appears in.

OUTPUTS (to --out)
  * nawawi40.raw_tokens.jsonl       — one record per OCCURRENCE (token in a hadith).
  * nawawi40.lexeme_candidates.jsonl — one record per distinct surface form, with
                                       frequency + the refs it occurs in. This file is
                                       the input to diff_against_qamus.py.

INPUT --src SCHEMA (either form is accepted)
  JSONL: one hadith object per line.
  JSON : a list of hadith objects, OR an object {"access_method": "...", "hadith": [ ... ]}.
  Each hadith object needs:
    {
      "ref":  "nawawi:1",          # stable ref; "nawawi:NN" recommended (1..42)
      "ar":   "<Arabic text>",     # the Arabic matn (surface, with or without tashkīl)
      "title": "...",              # optional human label
      "access_method": "..."       # optional per-hadith override of the dump-level note
    }
  A dump-level access_method note (how the Arabic was obtained, e.g. a named edition or
  a public dataset) SHOULD be present either as the top-level "access_method" key (JSON
  object form) or via --access-method. It is recorded — never a raw path, never a URL to
  copyrighted gloss text; just a citation label.

REUSABLE / stdlib-only. Requires tools/normalize_ar.py on the path.
NO network. NO live writes. Run:
  python qamus/scripts/catalogue_nawawi40.py \
      --src corpora/nawawi40/nawawi40.matn.jsonl \
      --out corpora/nawawi40/out
"""
import argparse
import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools import normalize_ar as N

SCRIPT_VERSION = "nawawi40-catalogue/1"

# Arabic letters + the harakāt/marks we must KEEP on the surface token so the
# normalize_ar harakah helpers can later disambiguate homographs (مَن vs مِن …).
# Range covers Arabic block letters (0621–064A), tashkīl (064B–0652), dagger-alef
# (0670), alef-wasla (0671), tatweel (0640), and Qurʾanic annotation marks (06D6–06ED).
_AR_TOKEN = re.compile(r"[ء-غـ-ٰٟٱۖ-ۭ]+")


def tokenize(text):
    """Yield Arabic surface tokens in order. Punctuation, Latin, digits split tokens.
    The surface form is returned verbatim (NFC only) — never stripped or reshaped."""
    import unicodedata
    for m in _AR_TOKEN.finditer(unicodedata.normalize("NFC", text or "")):
        tok = m.group(0)
        # drop a token that is ONLY marks/tatweel (no base letter)
        if any(0x0621 <= ord(c) <= 0x064A or c in ("ٰ", "ٱ") for c in tok):
            yield tok


def load_src(path, cli_access):
    """Read a JSON or JSONL dump. Returns (access_method, [hadith,...])."""
    raw = open(path, encoding="utf-8").read().strip()
    access = cli_access or ""
    hadith = []
    if not raw:
        return access, hadith
    # JSONL if the first non-space char starts a line-delimited object stream and it
    # is not a single top-level array/object spanning the whole file.
    looks_jsonl = raw[0] == "{" and "\n{" in raw
    if looks_jsonl:
        for ln in raw.splitlines():
            ln = ln.strip()
            if ln:
                hadith.append(json.loads(ln))
    else:
        doc = json.loads(raw)
        if isinstance(doc, dict):
            access = access or doc.get("access_method") or ""
            hadith = doc.get("hadith") or doc.get("ahadith") or doc.get("items") or []
        elif isinstance(doc, list):
            hadith = doc
        else:
            raise SystemExit("--src must be a JSON list/object or JSONL of hadith objects")
    return access, hadith


def main():
    ap = argparse.ArgumentParser(description="Catalogue Nawawī-40 surface vocabulary (catalogue-first).")
    ap.add_argument("--src", required=True, help="local JSON/JSONL dump of hadith 1..42 (NOT scraped here)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--access-method", default="",
                    help="citation label for how the Arabic was obtained (named edition / public dataset). "
                         "No raw paths, no copyrighted gloss URLs.")
    ap.add_argument("--corpus-id", default="nawawi40")
    a = ap.parse_args()

    access, hadith = load_src(a.src, a.access_method)
    if not hadith:
        raise SystemExit("no hadith found in --src")
    if not access:
        access = "UNSPECIFIED — record the source edition/dataset before publishing candidates"

    os.makedirs(a.out, exist_ok=True)
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_path = os.path.join(a.out, "%s.raw_tokens.jsonl" % a.corpus_id)
    lex_path = os.path.join(a.out, "%s.lexeme_candidates.jsonl" % a.corpus_id)

    # per-surface aggregation
    freq = collections.Counter()
    refs_for = collections.defaultdict(set)         # surface -> set(ref)
    norm_strict_for = {}                            # surface -> norm_strict (cache)

    n_tokens = 0
    with open(raw_path, "w", encoding="utf-8") as rf:
        for h in hadith:
            ref = h.get("ref") or h.get("id") or ("%s:?" % a.corpus_id)
            ar = h.get("ar") or h.get("matn") or h.get("text") or ""
            per_access = h.get("access_method") or access
            pos = 0
            for surface in tokenize(ar):
                pos += 1
                n_tokens += 1
                ns = norm_strict_for.get(surface)
                if ns is None:
                    ns = N.norm_strict(surface)
                    norm_strict_for[surface] = ns
                rec = {
                    "corpus": a.corpus_id,
                    "ref": ref,
                    "position": pos,
                    "surface_ar": surface,            # verbatim, never altered
                    "norm": N.norm(surface),
                    "norm_strict": ns,
                    "bare": N.bare(surface),
                    "ends_tanwin_alef": N.ends_tanwin_alef(surface),
                    "provenance": {
                        "source_scope": [a.corpus_id],
                        "access_method": per_access,
                        "extracted_by": SCRIPT_VERSION,
                        "generated": generated,
                    },
                }
                rf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                freq[surface] += 1
                refs_for[surface].add(ref)

    # lexeme candidates: one per distinct surface form
    n_lex = 0
    with open(lex_path, "w", encoding="utf-8") as lf:
        for surface, n in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])):
            ns = norm_strict_for[surface]
            rec = {
                "corpus": a.corpus_id,
                "surface_ar": surface,                # verbatim
                "norm": N.norm(surface),
                "norm_strict": ns,
                "bare": N.bare(surface),
                "frequency": n,
                "refs": sorted(refs_for[surface]),
                "ends_tanwin_alef": N.ends_tanwin_alef(surface),
                "provenance": {
                    "source_scope": [a.corpus_id],
                    "access_method": access,
                    "extracted_by": SCRIPT_VERSION,
                    "generated": generated,
                },
            }
            lf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_lex += 1

    print("hadith=%d tokens=%d distinct_surface=%d" % (len(hadith), n_tokens, n_lex))
    print("wrote %s" % raw_path)
    print("wrote %s" % lex_path)
    print("access_method recorded: %s" % access)


if __name__ == "__main__":
    main()
