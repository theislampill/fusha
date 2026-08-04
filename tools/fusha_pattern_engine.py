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
                        "entry_id": row.get("entry_id"),
                        "risk_flags": list(row.get("risk_flags") or []),
                        "no_root_reason": row.get("no_root_reason"),
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


def _haraka_clusters(surface):
    """Return visible harakah signatures per base-letter cluster, reusing haraka_on for short vowels."""
    clusters = []
    for ch in surface or "":
        if 0x064B <= ord(ch) <= 0x0652 and clusters:
            clusters[-1] += ch
        elif not (ord(ch) == 0x0640 or ord(ch) == 0x0670 or 0x06D6 <= ord(ch) <= 0x06ED):
            clusters.append(ch)
    out = []
    for cluster in clusters:
        short = N.haraka_on(cluster, cluster[0])
        marks = {ch for ch in cluster[1:] if 0x064B <= ord(ch) <= 0x0652}
        if short:
            marks.add(short)
        out.append(frozenset(marks))
    return out


def _visible_haraka_conflict(surface, form):
    """Same strict skeleton, but at least one mutually visible harakah cluster disagrees."""
    if N.norm_strict(surface) != N.norm_strict(form):
        return False
    query_marks = _haraka_clusters(surface)
    form_marks = _haraka_clusters(form)
    if len(query_marks) != len(form_marks):
        return False
    return any(q and f and q != f for q, f in zip(query_marks, form_marks))


def _lexicon_match(surface, lexicon):
    """Match surface against the lexicon and expose the full competitor set.

    Competitors are entries whose form-set shares the query's norm_strict key;
    this is scoped to the ONE surface passed in (a single selected stem, or a
    single whole-token retry) and never unioned across other segmentation
    hypotheses, so a rejected split can never manufacture a competitor.
    """
    order = {"surface_exact_match": 0, "norm_strict_match": 1, "bare_match": 2}
    matches = []
    strict_key_rows = {}
    surface_key = N.norm_strict(surface)
    for row_index, row in enumerate(lexicon):
        forms = set(row.get("forms") or [])
        forms.add(row.get("lemma", ""))
        for f in sorted(forms):
            if f and N.norm_strict(f) == surface_key:
                strict_key_rows[row_index] = row
            basis = _match_basis(surface, f)
            if basis:
                matches.append((order[basis], row_index, row, basis, f))
    if not matches:
        return None, None, None, []
    _basis_order, _row_index, selected, basis, matched_form = min(matches, key=lambda item: (item[0], item[1]))
    harakah_conflict = _visible_haraka_conflict(surface, matched_form)
    competitors = []
    seen = set()
    for row_index in sorted(strict_key_rows):
        r = strict_key_rows[row_index]
        eid = r.get("entry_id")
        dedupe_key = eid if eid is not None else ("_row", row_index)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        competitors.append({"entry_id": eid, "pos": r.get("pos"), "root": r.get("root"), "lemma": r.get("lemma")})
    shared_key = len(strict_key_rows) > 1
    if harakah_conflict or shared_key:
        selected = dict(selected)
        selected["_match_risk"] = {
            "kind": "homograph_risk",
            "harakah_conflict": harakah_conflict,
            "shared_key_lemma_count": len(strict_key_rows),
            "matched_form": matched_form,
        }
    return selected, basis, matched_form, competitors


def _stem_segments(seg_candidate):
    return [s for s in seg_candidate.get("segments") or [] if s.get("role") == "stem"]


def _candidate_from_row(row, seg_ref, score=6.0, evidence=None, extra=None, match_basis=None,
                         matched_form=None, competitors=None):
    feats = dict(row.get("features") or {})
    if match_basis:
        feats["match_basis"] = match_basis
    match_risk = row.get("_match_risk")
    if match_risk:
        feats["match_risk"] = match_risk["kind"]
        feats["harakah_conflict"] = match_risk["harakah_conflict"]
        feats["shared_key_lemma_count"] = match_risk["shared_key_lemma_count"]
    risk_flags = row.get("risk_flags") or []
    if risk_flags:
        feats["source_risk_flags"] = list(risk_flags)

    lemma = row.get("lemma")
    root = row.get("root")
    gloss_hint = row.get("gloss_hint")
    identity_withheld = False
    # R2 compound_headword_bundle: a slash-joined lemma names more than one
    # headword; project the matched form, not the bundle, and drop its gloss.
    if lemma and "/" in lemma:
        feats["entry_identity_status"] = "unresolved_bundle_member"
        lemma = matched_form or lemma
        identity_withheld = True
    # R3 root_identity_unresolved: a slash-joined root is not one radical
    # sequence; surface it as an unresolved set (root=null), never pick a member.
    if root and "/" in root:
        feats["root_identity_status"] = "unresolved_root_set"
        root = None
        identity_withheld = True
    if identity_withheld:
        gloss_hint = None

    if extra:
        feats.update(extra)

    cand = {
        "lemma": lemma,
        "root": root,
        "pos": row.get("pos"),
        "pattern": row.get("pattern"),
        "features": feats,
        "gloss_hint": gloss_hint,
        "evidence_class": "homograph_risk" if match_risk else (evidence or row.get("evidence_class") or "seed_lexicon"),
        "confidence": "medium",
        "score": score,
        "rank": 0,
        "segment_candidate_ref": seg_ref,
    }
    if competitors and len(competitors) > 1:
        cand["collision"] = {
            "competing_entry_ids": [c.get("entry_id") for c in competitors if c.get("entry_id")],
            "competitors": competitors,
        }
    return cand


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


def _final_cluster_marks(surface):
    """The combining marks written on the LAST base-letter cluster of `surface` -- a read of what
    is actually on the page, never an inferred vowel."""
    marks = ""
    i = len(surface or "") - 1
    while i >= 0 and 0x064B <= ord(surface[i]) <= 0x0652:
        marks = surface[i] + marks
        i -= 1
    return marks


def _naa_role(stem_before_naa):
    """Written-vocalization-only subject/object discrimination for a verb stem's trailing نا.
    A sukūn on the stem's OWN final letter is the classic 1st-person-plural perfect subject
    suffix (خَلَقْنَا 'we created'); a fatḥa on that same letter is a 3ms perfect verb PLUS an
    attached object pronoun (خَلَقَنَا 'He created us') -- same bare letters, opposite function.
    Anything else (no mark, or a different vowel) is not decisive and must never be guessed from
    POS alone (Finding F6)."""
    marks = _final_cluster_marks(stem_before_naa)
    if "ْ" in marks:
        return "subject"
    if "َ" in marks:
        return "object"
    return "undetermined"


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
        row, basis, matched_form, competitors = _lexicon_match(stem_surface, lexicon)
        if row is None and whole_token_candidate:
            row, basis, matched_form, competitors = _lexicon_match(surface, lexicon)
        extra = _suffix_extra(stem_surface)
        if row:
            cands.append(_candidate_from_row(row, i, score=_row_score(row, basis), extra=extra, match_basis=basis,
                                              matched_form=matched_form, competitors=competitors))
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
    # On an equal evidence score, put the candidate carrying the stricter
    # source-declared Naḥw review obligation first. Downstream gates and
    # validators inspect the top candidate; a safer shape-only rival must not
    # hide an equally scored source risk merely because its segmentation ref
    # sorts earlier.
    cands.sort(key=lambda c: (
        -c.get("score", 0),
        0 if "requires_nahw_function" in set(
            (c.get("features") or {}).get("source_risk_flags") or []
        ) else 1,
        c.get("segment_candidate_ref", 0),
    ))
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
    # A trailing bare نا LOOKS like stem+"we", but قُرْءَانًا (tanwīn fatḥa + support alif) has the same bare
    # tail without being a pronoun at all. Only split when there is COMPATIBLE VERB EVIDENCE (morph.pos ==
    # "verb") AND the ending is not a tanwīn support alif in disguise (normalize_ar.ends_tanwin_alef).
    if (bare.endswith("نا") and len(bare) > 4
            and (morph.get("pos") or "") == "verb"
            and not N.ends_tanwin_alef(stem)):
        host, naa = stem[:-2], stem[-2:]
        naa_role = _naa_role(host)
        # POS alone never decides subject vs. object here (Finding F6): a sukūn-terminated host is
        # the 1p subject suffix (خَلَقْنَا "we created"); a fatḥa-terminated host is the SAME bare
        # letters as a 3ms verb plus an attached object pronoun (خَلَقَنَا "He created us"). When the
        # written vocalization is not decisive, the clitic's role stays undetermined rather than
        # guessed.
        if naa_role == "subject":
            return [
                {"role": "verb_stem", "surface": host, "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")},
                {"role": "subject_pronoun", "surface": naa, "class": "qg-subject-pronoun", "label": "SUBJ", "gloss_contribution": "we"},
            ]
        if naa_role == "object":
            return [
                {"role": "verb_stem", "surface": host, "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")},
                {"role": "object_pronoun", "surface": naa, "class": "qg-object-pronoun", "label": "OBJ", "gloss_contribution": "us"},
            ]
        return [
            {"role": "verb_stem", "surface": host, "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")},
            {"role": "clitic_undetermined", "surface": naa, "class": "qg-clitic-undetermined", "label": "UNDET", "gloss_contribution": None},
        ]
    if (morph.get("pos") or "") == "verb":
        return [{"role": "verb_stem", "surface": stem, "class": "qg-verb-stem", "label": "STEM", "gloss_contribution": morph.get("gloss_hint")}]
    return []


def preview_segments(surface, seg_candidate, morph):
    """Build qamus-grammar-v1 preview segments for a selected candidate."""
    out = []
    last_stem_surface = None
    for seg in seg_candidate.get("segments") or []:
        role = seg.get("role")
        seg_surface = seg.get("surface", "")
        if role == "stem":
            last_stem_surface = seg_surface
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
            # The checker's generic enclitic peeler may ALREADY have split a trailing نا off a verb stem
            # (e.g. bare أهلكنا, whose candidate outranked the unsplit reading after split_clitics' by-length
            # re-sort), so _verb_parts never saw the combined stem to relabel it. Apply the SAME compatible-
            # verb-evidence guard here (pos == "verb", and not a tanwīn support alif in disguise), and the
            # SAME written-vocalization discrimination as _verb_parts (Finding F6): POS alone never decides
            # subject vs. object for a trailing نا.
            if (N.bare(seg_surface) == "نا" and (morph.get("pos") or "") == "verb"
                    and last_stem_surface is not None
                    and not N.ends_tanwin_alef(last_stem_surface + seg_surface)):
                naa_role = _naa_role(last_stem_surface)
                if naa_role == "subject":
                    out.append({"role": "subject_pronoun", "surface": seg_surface, "class": "qg-subject-pronoun",
                                "label": "SUBJ", "gloss_contribution": "we"})
                elif naa_role == "object":
                    out.append({"role": "object_pronoun", "surface": seg_surface, "class": "qg-object-pronoun",
                                "label": "OBJ", "gloss_contribution": "us"})
                else:
                    out.append({"role": "clitic_undetermined", "surface": seg_surface, "class": "qg-clitic-undetermined",
                                "label": "UNDET", "gloss_contribution": None})
            else:
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


def _self_test():
    from tools.fusha_clitic_splitter import split_clitics

    conflict = build_morphology("يَعِدُ", split_clitics("يَعِدُ"), db="largelexicon")[0]
    control = build_morphology("يَعْدُ", split_clitics("يَعْدُ"), db="largelexicon")[0]
    shared_key_lexicon = [
        {"lemma": "كَتَبَ", "forms": ["كَتَبَ"], "pos": "verb"},
        {"lemma": "كُتُب", "forms": ["كُتُب"], "pos": "noun"},
    ]
    shared = build_morphology("كتب", split_clitics("كتب"), lexicon=shared_key_lexicon)[0]
    failures = []
    if (conflict.get("features") or {}).get("match_risk") != "homograph_risk":
        failures.append("P04 visible-harakah conflict was not quarantined")
    if conflict.get("evidence_class") != "homograph_risk":
        failures.append("P04 conflict retained a confident evidence class")
    if (control.get("features") or {}).get("match_risk") == "homograph_risk":
        failures.append("harakah-agreeing control was over-quarantined")
    if (shared.get("features") or {}).get("match_risk") != "homograph_risk":
        failures.append("same-key multiple-lemma rows were not quarantined")
    for failure in failures:
        print("FAIL " + failure)
    if not failures:
        print("ok   fusha_pattern_engine self-test: harakah conflicts and shared-key lemmas quarantine; agreeing control matches")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Emit morphology candidates for one token.")
    ap.add_argument("surface", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.surface:
        ap.error("need surface or --self-test")
    from tools.fusha_clitic_splitter import split_clitics  # noqa: E402
    segs = split_clitics(args.surface)
    print(json.dumps(build_morphology(args.surface, segs), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
