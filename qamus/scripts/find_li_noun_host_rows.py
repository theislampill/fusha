#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_li_noun_host_rows — dependent-row discovery query for the p007 noun-host لِـ family.

This is the committed query the FULL-POPULATION lane runs to find the rows analogous to the
P00-vertical-slice pilot family (jarr clitic لِـ on noun hosts, 12 occurrences certified
end-to-end). It scans `qamus/lattice/particle-occurrence-matrix.jsonl` for p007 candidate edges,
keeps the strict لِ+kasra clitic-prefix candidates, and PRE-ROUTES each row through the pilot's
guard classes (@2.4 candidate skill rules) so the evidence lane spends MCP calls only where they
can certify:

  * `noun_host_candidate`     — nominal-looking host, no guard fires: the certified-template
                                ceiling class (each row STILL needs per-occurrence host evidence;
                                the pilot's 3 rejected rivals prove why).
  * `pronoun_host`            — host is a mabnī pronoun (لِى family): genuine jarr, DIFFERENT
                                family (sarf-li-pronoun-host-outside-noun-family).
  * `lexical_lam_risk`        — host begins with lām after the strip OR the un-stripped surface
                                is a known lexical-initial-lām word (لِبَاسٌ class): route the
                                مادة check FIRST (sarf-lexical-initial-lam-madda-guard).
  * `verb_host_rival_risk`    — the matrix's own function candidates include a taʿlīl/amr
                                reading, or the host shape is a known muḍāriʿ-initial pattern:
                                route nahw-lam-talil-vs-jarr-host-pos before any jarr claim.

Output: JSONL worklist rows {matrix_id, occurrence_id, surface, host_visible, route, flags,
appearance_count} + a stderr-free summary. Deterministic, stdlib only, read-only.

Run:  python qamus/scripts/find_li_noun_host_rows.py                       # summary only
      python qamus/scripts/find_li_noun_host_rows.py --out worklist.jsonl  # write the worklist
      python qamus/scripts/find_li_noun_host_rows.py --self-test           # embedded fixtures
"""
import argparse
import io
import json
import os
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MATRIX = os.path.join(REPO, "qamus", "lattice", "particle-occurrence-matrix.jsonl")

KASRA = "ِ"
LAM = "ل"

# Closed-class pronoun hosts of لِ (visible-host forms as the matrix records them, bare skeleton).
PRONOUN_HOSTS = {"ي", "ى", "ه", "ها", "هم", "هن", "هما", "كم", "كن", "كما", "ك", "نا"}

# Known lexical-initial-lām skeletons measured in the pilot/calibration (the لِبَاس class): the
# candidate "clitic" lām is the first ROOT radical. Bare skeletons compared post-normalization.
LEXICAL_LAM_SKELETONS = {"باس", "باسا", "سان", "سانا"}  # لباس، لسان families after a (wrong) strip

# muḍāriʿ prefixes a stripped host would start with if the lām is taʿlīl/amr over a verb.
VERB_PREFIXES = ("ي", "ت", "ن", "أ")


def _bare(s):
    """Strip harakāt/annotation marks + dagger alif; keep base letters (incl. hamza seats)."""
    out = []
    for ch in unicodedata.normalize("NFC", s or ""):
        o = ord(ch)
        if 0x064B <= o <= 0x0652 or 0x06D6 <= o <= 0x06ED or o in (0x0670, 0x0640):
            continue
        out.append("ا" if ch == "ٱ" else ch)
    return "".join(out)


def classify(row):
    """Return (route, flags) for a p007 clitic-prefix candidate row (pilot guard pre-routing)."""
    flags = []
    surface = unicodedata.normalize("NFC", row.get("surface") or "")
    host = row.get("host_visible") or ""
    bare_host = _bare(host)
    bare_surface = _bare(surface)

    if not surface.startswith(LAM):
        return None, flags  # not a لِ candidate at all
    strict_li = surface.startswith(LAM + KASRA) or surface.startswith(LAM + "ّ") \
        or (len(surface) > 1 and surface[1] == KASRA)
    if not strict_li:
        flags.append("non_kasra_lam_needs_diacritic_check")

    # pronoun-host family
    if bare_host in PRONOUN_HOSTS:
        return "pronoun_host", flags

    # lexical-initial-lām risk: the whole surface is a known lexical word, or the stripped host
    # itself begins with lām (article? second radical? مادة check decides).
    stripped = bare_surface[1:]
    if stripped in LEXICAL_LAM_SKELETONS or bare_surface in {"لباس", "لسان"}:
        flags.append("known_lexical_lam_skeleton")
        return "lexical_lam_risk", flags
    if bare_host.startswith("ل") and not bare_host.startswith("لل") and bare_host not in ("له",):
        # host records its own leading lām that is NOT an assimilated-article pair
        flags.append("host_leading_lam_madda_check_required")
        return "lexical_lam_risk", flags

    # verb-host rival risk: the matrix's own function candidates, or a bare verb-prefix shape
    funcs = " ".join(row.get("function_candidates") or [])
    if "تعليل" in funcs or "amr" in funcs or "لام الأمر" in funcs:
        return "verb_host_rival_risk", flags
    if len(bare_host) >= 3 and bare_host[0] in VERB_PREFIXES and not row.get("host_is_nominal"):
        flags.append("host_shape_could_be_mudari")
        return "verb_host_rival_risk", flags

    return "noun_host_candidate", flags


def scan(matrix_path):
    rows = []
    with io.open(matrix_path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            row = json.loads(ln)
            if row.get("particle_source_key") != "p007":
                continue
            if row.get("clitic_or_free_candidate") != "clitic":
                continue
            if row.get("match_kind") != "clitic":
                continue
            route, flags = classify(row)
            if route is None:
                continue
            rows.append({
                "matrix_id": row.get("matrix_id"),
                "occurrence_id": row.get("occurrence_id"),
                "surface": row.get("surface"),
                "host_visible": row.get("host_visible"),
                "candidate_entry": row.get("candidate_entry"),
                "appearance_count": row.get("appearance_count"),
                "certified": row.get("certified"),
                "route": route,
                "flags": flags,
                "guard_rules": {
                    "pronoun_host": "sarf-li-pronoun-host-outside-noun-family",
                    "lexical_lam_risk": "sarf-lexical-initial-lam-madda-guard",
                    "verb_host_rival_risk": "nahw-lam-talil-vs-jarr-host-pos",
                    "noun_host_candidate": "sarf-li-kasra-noun-host-clitic-carve",
                }[route],
            })
    rows.sort(key=lambda r: (r["route"], r["matrix_id"] or ""))
    return rows


def self_test():
    fx = [
        ({"particle_source_key": "p007", "surface": "لِبَاسٌ", "host_visible": "باس",
          "function_candidates": []}, "lexical_lam_risk"),
        ({"particle_source_key": "p007", "surface": "لِى", "host_visible": "ي",
          "function_candidates": []}, "pronoun_host"),
        ({"particle_source_key": "p007", "surface": "لِيَغِيظَ", "host_visible": "يغيظ",
          "function_candidates": []}, "verb_host_rival_risk"),
        ({"particle_source_key": "p007", "surface": "لِلنَّاسِ", "host_visible": "الناس",
          "function_candidates": ["jarr/lām li-/la-"]}, "noun_host_candidate"),
        ({"particle_source_key": "p007", "surface": "لِغَيْرِ", "host_visible": "غير",
          "function_candidates": []}, "noun_host_candidate"),
        ({"particle_source_key": "p007", "surface": "لِقَوْمِهِ", "host_visible": "قومه",
          "function_candidates": []}, "noun_host_candidate"),
    ]
    fails = []
    for row, want in fx:
        got, _flags = classify(row)
        tag = "ok  " if got == want else "FAIL"
        print("%s %-12s -> %-24s (want %s)" % (tag, row["surface"], got, want))
        if got != want:
            fails.append(row["surface"])
    if fails:
        print("SELF-TEST FAIL: %s" % ", ".join(fails))
        return 1
    print("find_li_noun_host_rows self-test OK (%d fixtures)" % len(fx))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", default=MATRIX)
    ap.add_argument("--out", help="write the routed worklist JSONL here")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    rows = scan(a.matrix)
    from collections import Counter
    counts = Counter(r["route"] for r in rows)
    apps = Counter()
    for r in rows:
        apps[r["route"]] += r.get("appearance_count") or 0
    n_strict = sum(1 for r in rows if "non_kasra_lam_needs_diacritic_check" not in r["flags"])
    print("p007 clitic لِ candidates routed: %d rows (%d strict لِ+kasra; %d flagged for a "
          "diacritic check first)" % (len(rows), n_strict, len(rows) - n_strict))
    for route in sorted(counts):
        print("  %-24s %5d rows  %6d appearances" % (route, counts[route], apps[route]))
    print("NOTE: noun_host_candidate is the certified-template CEILING class — every row still "
          "needs per-occurrence host evidence before certification (pilot §9).")
    if a.out:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
