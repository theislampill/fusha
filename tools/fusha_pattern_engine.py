#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small seed/pattern engine for the standalone parser MVP.

Blank beats wrong: roots are attached only from the repo seed lexicon or a
pinned conservative pattern tied to that lexicon. The engine is not a full
Arabic analyzer; it provides useful candidates and safe qg preview segments.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)

from tools import normalize_ar as N  # noqa: E402

LEXICON_PATH = os.path.join(_REPO, "fusha", "lexicon", "fusha-lemmas.jsonl")
LARGELEXICON_SAMPLE_PATH = os.path.join(_REPO, "fusha", "lexicon", "largelexicon", "lemma-source.sample.jsonl")
LARGELEXICON_FULL_PATH = os.path.join(_REPO, "fusha", "lexicon", "largelexicon", "lemma-source.full.jsonl")

FUNCTION_WORDS = {
    "ما": ("particle", "function-sensitive mā"),
    "وما": ("particle", "wāw plus function-sensitive mā"),
    "إنما": ("particle", "restriction particle cluster"),
    "انما": ("particle", "restriction particle cluster"),
    "لا": ("particle", "negation/prohibition particle; context decides"),
    "إلا": ("particle", "exceptive particle; context decides"),
    "الا": ("particle", "exceptive particle; context decides"),
    "لم": ("particle", "jussive negator"),
    "لما": ("particle", "context-sensitive lammā/limā"),
    "من": ("particle", "from/who/whom/conditional by voweling and context"),
}

PINNED_FORMS = {
    "يكفي": {"lemma": "كَفَى", "root": "ك ف ي", "pos": "verb", "verb_form": "I", "gloss_hint": "suffice"},
    "اهلك": {"lemma": "أَهْلَكَ", "root": "ه ل ك", "pos": "verb", "verb_form": "IV", "gloss_hint": "destroy"},
    "أهلك": {"lemma": "أَهْلَكَ", "root": "ه ل ك", "pos": "verb", "verb_form": "IV", "gloss_hint": "destroy"},
    "يسأل": {"lemma": "سَأَلَ", "root": "س أ ل", "pos": "verb", "verb_form": "I", "gloss_hint": "ask"},
    "يستغفر": {"lemma": "ٱسْتَغْفَرَ", "root": "غ ف ر", "pos": "verb", "verb_form": "X", "gloss_hint": "seek forgiveness"},
    "مستغفر": {"lemma": "مُسْتَغْفِر", "root": "غ ف ر", "pos": "participle", "verb_form": "X", "gloss_hint": "one seeking forgiveness"},
}

INNER_PRONOUNS = ("هما", "هم", "كم", "كن", "ها", "نا", "ه", "ك", "ي")


def _load_lexicon(path=LEXICON_PATH, db="smoke"):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                row.setdefault("evidence_class", "seed_lexicon")
                rows.append(row)
    if db == "largelexicon":
        large_path = LARGELEXICON_FULL_PATH if os.path.exists(LARGELEXICON_FULL_PATH) else LARGELEXICON_SAMPLE_PATH
        evidence_class = "largelexicon_full" if large_path == LARGELEXICON_FULL_PATH else "largelexicon_sample"
        with open(large_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                rows.append(
                    {
                        "lemma": row.get("lemma"),
                        "root": row.get("root"),
                        "pos": row.get("pos"),
                        "forms": row.get("forms") or [],
                        "pattern": None,
                        "features": {"entry_id": row.get("entry_id"), "source_status": row.get("source_status")},
                        "gloss_hint": row.get("gloss_hint"),
                        "qamus_entry_id": row.get("entry_id"),
                        "source_status": row.get("source_status"),
                        "evidence_class": evidence_class,
                    }
                )
    return rows


def _keys(s):
    return {s, N.norm_strict(s), N.bare(s)}


def _match_basis(surface, form):
    if not surface or not form:
        return None
    if surface == form:
        return "surface_exact_match"
    if N.norm_strict(surface) == N.norm_strict(form):
        return "norm_strict_match"
    if N.bare(surface) == N.bare(form):
        return "bare_match"
    return None


def _lexicon_match(surface, lexicon):
    best = None
    best_order = 999
    order = {"surface_exact_match": 0, "norm_strict_match": 1, "bare_match": 2}
    for row in lexicon:
        forms = set(row.get("forms") or [])
        forms.add(row.get("lemma", ""))
        for f in forms:
            basis = _match_basis(surface, f)
            if not basis:
                continue
            basis_order = order[basis]
            if basis_order < best_order:
                best = (row, basis)
                best_order = basis_order
                if basis_order == 0 and row.get("evidence_class") == "seed_lexicon":
                    return best
    return best or (None, None)


def _stem_segments(seg_candidate):
    return [s for s in seg_candidate.get("segments") or [] if s.get("role") == "stem"]


def _candidate_from_row(row, seg_ref, score=6.0, evidence=None, extra=None, match_basis=None):
    feats = dict(row.get("features") or {})
    if match_basis:
        feats["match_basis"] = match_basis
    if extra:
        feats.update(extra)
    return {
        "lemma": row.get("lemma"),
        "root": row.get("root"),
        "pos": row.get("pos"),
        "pattern": row.get("pattern"),
        "features": feats,
        "gloss_hint": row.get("gloss_hint"),
        "evidence_class": evidence or row.get("evidence_class") or "seed_lexicon",
        "confidence": "medium",
        "score": score,
        "rank": 0,
        "segment_candidate_ref": seg_ref,
    }


def _pinned_candidate(surface, seg_ref, extra=None):
    key_options = _keys(_analysis_host(surface))
    for key in key_options:
        if key in PINNED_FORMS:
            data = dict(PINNED_FORMS[key])
            feats = {"verb_form": data.get("verb_form")}
            if extra:
                feats.update(extra)
            return {
                "lemma": data.get("lemma"),
                "root": data.get("root"),
                "pos": data.get("pos"),
                "pattern": None,
                "features": feats,
                "gloss_hint": data.get("gloss_hint"),
                "evidence_class": "pinned_pattern",
                "confidence": "medium",
                "score": 5.0,
                "rank": 0,
                "segment_candidate_ref": seg_ref,
            }
    return None


def _analysis_host(surface):
    """Conservative internal host for pinned matching; never shown as display text."""
    bare = N.bare(surface)
    display = surface
    if bare.startswith("س") and len(bare) > 4:
        display = display[1:]
        bare = bare[1:]
    for pron in INNER_PRONOUNS:
        if bare.endswith(pron) and len(bare) - len(pron) >= 3:
            return display[:-len(pron)]
    return display


def _function_candidate(surface, seg_ref):
    for key in _keys(surface):
        if key in FUNCTION_WORDS:
            if key == "من" and N.shadda_on(surface, "ن"):
                continue
            if key in {"إلا", "الا"} and _has_tanwin(surface):
                continue
            pos, gloss = FUNCTION_WORDS[key]
            return {
                "lemma": surface,
                "root": None,
                "pos": pos,
                "pattern": None,
                "features": {"particle_function": "pending_context", "match_basis": "function_inventory_exact"},
                "gloss_hint": gloss,
                "evidence_class": "function_inventory",
                "confidence": "medium",
                "score": 6.5,
                "rank": 0,
                "segment_candidate_ref": seg_ref,
            }
    return None


def _has_tanwin(surface):
    return any(0x064B <= ord(ch) <= 0x064D for ch in surface or "")


def _row_score(row, basis):
    if (row.get("features") or {}).get("proper_name"):
        return 7.0
    return {
        "surface_exact_match": 6.0,
        "norm_strict_match": 5.5,
        "bare_match": 5.0,
    }.get(basis, 6.0)


def _suffix_extra(surface):
    bare = N.bare(surface)
    extra = {}
    if bare.endswith("ون"):
        extra["number"] = "masculine_plural"
    elif bare.endswith("ين"):
        extra["number"] = "masculine_plural_or_oblique"
    elif bare.endswith("ان"):
        extra["number"] = "dual_or_plural_candidate"
    return extra


def build_morphology(surface, segment_candidates, lexicon=None, db="smoke"):
    lexicon = lexicon if lexicon is not None else _load_lexicon(db=db)
    cands = []
    for i, seg_cand in enumerate(segment_candidates or []):
        stems = _stem_segments(seg_cand)
        if not stems:
            continue
        stem_surface = stems[-1].get("surface", "")
        segs = seg_cand.get("segments") or []
        whole_token_candidate = len(segs) == 1 and stem_surface == surface
        added = False
        f = _function_candidate(stem_surface, i) or _function_candidate(surface, i)
        if f:
            cands.append(f)
            added = True
        row, basis = _lexicon_match(stem_surface, lexicon)
        if row is None and whole_token_candidate:
            row, basis = _lexicon_match(surface, lexicon)
        extra = _suffix_extra(stem_surface)
        if row:
            cands.append(_candidate_from_row(row, i, score=_row_score(row, basis), extra=extra, match_basis=basis))
            added = True
        pinned = _pinned_candidate(stem_surface, i, extra=extra)
        if pinned:
            cands.append(pinned)
            added = True
        if added:
            continue
        pos = "unknown"
        if any(s.get("role") == "definite_article" for s in seg_cand.get("segments") or []):
            pos = "noun"
        cands.append({
            "lemma": None,
            "root": None,
            "pos": pos,
            "pattern": None,
            "features": extra,
            "gloss_hint": None,
            "evidence_class": "surface_candidate",
            "confidence": "low",
            "score": 1.0,
            "rank": 0,
            "segment_candidate_ref": i,
        })
    cands.sort(key=lambda c: (-c.get("score", 0), c.get("segment_candidate_ref", 0)))
    for idx, cand in enumerate(cands, 1):
        cand["rank"] = idx
    return cands


def _pronoun_gloss(surface):
    bare = N.bare(surface)
    return {
        "ه": "him/it",
        "ها": "her/it",
        "هم": "them",
        "هما": "both of them",
        "كم": "you all",
        "ك": "you",
        "نا": "us/our",
        "ي": "me/my",
    }.get(bare, "attached pronoun")


def _peel_inner_pronoun(surface):
    bare = N.bare(surface)
    for pron in INNER_PRONOUNS:
        if bare.endswith(pron) and len(bare) - len(pron) >= 3:
            return surface[:-len(pron)], surface[-len(pron):]
    return surface, None


def _verb_parts(stem, morph):
    bare = N.bare(stem)
    parts = []
    if bare.startswith("س") and len(bare) > 4:
        rest = stem[1:]
        rest_parts = _verb_parts(rest, morph)
        if rest_parts and "".join(p["surface"] for p in rest_parts) == rest:
            return [{"role": "future_particle", "surface": stem[:1], "class": "qg-particle",
                     "label": "FUT", "gloss_contribution": "will"}] + rest_parts
    if bare.startswith("ي") and len(bare) > 3:
        host, pron = _peel_inner_pronoun(stem)
        parts.append({"role": "verb_prefix", "surface": host[:1], "class": "qg-verb-prefix", "label": "PFX", "gloss_contribution": "imperfect marker"})
        parts.append({"role": "verb_stem", "surface": host[1:], "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")})
        if pron:
            parts.append({"role": "object_pronoun", "surface": pron, "class": "qg-object-pronoun",
                          "label": "OBJ", "gloss_contribution": _pronoun_gloss(pron)})
        return parts
    if bare.startswith("مست") and len(bare) > 5:
        pref = stem[:3]
        rest = stem[3:]
        if N.bare(rest).endswith("ين"):
            host = rest[:-2]
            suff = rest[-2:]
            return [
                {"role": "derivative_prefix", "surface": pref, "class": "qg-derivative-prefix", "label": "DER", "gloss_contribution": "Form X seeker/doer shape"},
                {"role": "adjective_stem", "surface": host, "class": "qg-adjective", "label": "AP", "gloss_contribution": morph.get("gloss_hint")},
                {"role": "plural_suffix", "surface": suff, "class": "qg-plural-suffix", "label": "PL", "gloss_contribution": "masculine plural/oblique ending"},
            ]
        return [
            {"role": "derivative_prefix", "surface": pref, "class": "qg-derivative-prefix", "label": "DER", "gloss_contribution": "derived-form prefix"},
            {"role": "adjective_stem", "surface": rest, "class": "qg-adjective", "label": "AP", "gloss_contribution": morph.get("gloss_hint")},
        ]
    if bare.endswith("نا") and len(bare) > 4:
        return [
            {"role": "verb_stem", "surface": stem[:-2], "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")},
            {"role": "subject_pronoun", "surface": stem[-2:], "class": "qg-subject-pronoun", "label": "SUBJ", "gloss_contribution": "we"},
        ]
    if (morph.get("pos") or "") == "verb":
        return [{"role": "verb_stem", "surface": stem, "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")}]
    return []


def preview_segments(surface, seg_candidate, morph):
    """Build qamus-grammar-v1 preview segments for a selected candidate."""
    out = []
    for seg in seg_candidate.get("segments") or []:
        role = seg.get("role")
        seg_surface = seg.get("surface", "")
        if role == "stem":
            vparts = _verb_parts(seg_surface, morph)
            if vparts:
                out.extend(vparts)
            else:
                cls = "qg-proper-noun" if morph.get("pos") == "proper_noun" else (
                    "qg-particle" if morph.get("pos") == "particle" else "qg-noun-stem"
                )
                label = "PART" if cls == "qg-particle" else "N"
                out.append({"role": "stem", "surface": seg_surface, "class": cls, "label": label,
                            "gloss_contribution": morph.get("gloss_hint")})
        elif role == "object_pronoun":
            out.append({"role": "object_pronoun", "surface": seg_surface, "class": "qg-object-pronoun",
                        "label": "OBJ", "gloss_contribution": _pronoun_gloss(seg_surface)})
        elif role == "prefix_particle":
            out.append({"role": "future_particle", "surface": seg_surface, "class": "qg-particle",
                        "label": "FUT", "gloss_contribution": "will"})
        else:
            out.append(dict(seg))
    if "".join(s["surface"] for s in out) != surface:
        return [dict(s) for s in seg_candidate.get("segments") or []]
    return out


def main():
    ap = argparse.ArgumentParser(description="Emit morphology candidates for one token.")
    ap.add_argument("surface")
    args = ap.parse_args()
    from tools.fusha_clitic_splitter import split_clitics  # noqa: E402
    segs = split_clitics(args.surface)
    print(json.dumps(build_morphology(args.surface, segs), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
