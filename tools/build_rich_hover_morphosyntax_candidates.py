#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build reviewable rich-hover morphosyntax metadata candidates.

This generator is deliberately narrow. It emits metadata records for surface
composition that is visible in the written token, while leaving deeper case,
number, gender, and syntactic role unclaimed unless another lane certifies them.

It does not mutate live Qamus data or edit token decisions.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "out" / "hover_stage"

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

PUBLIC_BOUNDARY = {
    "public_gloss_src": "qamus",
    "public_gloss_kind": "authored",
    "public_gloss_lang": "en",
    "external_source_names_public": False,
}

SUFFIX_PRONOUNS = [
    ("كُمَا", {"person": "2", "gender": "common", "number": "dual", "gloss": "you two", "obj": "OBJ.2D"}),
    ("كُمْ", {"person": "2", "gender": "masculine", "number": "plural", "gloss": "you all", "obj": "OBJ.2MP"}),
    ("كُنَّ", {"person": "2", "gender": "feminine", "number": "plural", "gloss": "you all", "obj": "OBJ.2FP"}),
    ("هُمَا", {"person": "3", "gender": "common", "number": "dual", "gloss": "them both", "obj": "OBJ.3D"}),
    ("هُمْ", {"person": "3", "gender": "masculine", "number": "plural", "gloss": "them", "obj": "OBJ.3MP"}),
    ("هُنَّ", {"person": "3", "gender": "feminine", "number": "plural", "gloss": "them", "obj": "OBJ.3FP"}),
    ("هَا", {"person": "3", "gender": "feminine", "number": "singular", "gloss": "her/it", "obj": "OBJ.3FS"}),
    ("نِي", {"person": "1", "gender": "common", "number": "singular", "gloss": "me", "obj": "OBJ.1S"}),
    ("نَا", {"person": "1", "gender": "common", "number": "plural", "gloss": "us", "obj": "OBJ.1P"}),
    ("كَ", {"person": "2", "gender": "masculine", "number": "singular", "gloss": "you", "obj": "OBJ.2MS"}),
    ("كِ", {"person": "2", "gender": "feminine", "number": "singular", "gloss": "you", "obj": "OBJ.2FS"}),
    ("هُ", {"person": "3", "gender": "masculine", "number": "singular", "gloss": "him/it", "obj": "OBJ.3MS"}),
]

REVIEWED_OVERRIDES = {
    "4:28:6": {
        "parse_key": {
            "key": "REM+V:PERF:PASS:3MS",
            "summary": "Resumption particle plus passive perfect third-person masculine singular verb.",
            "components": [
                {"label": "REM", "value": "resumption / and"},
                {"label": "V", "value": "passive perfect verb"},
                {"label": "AGR", "value": "3rd masculine singular"},
            ],
        },
        "morphology": {"aspect": "perfect", "gender": "masculine", "number": "singular", "person": "3", "verb_form": "I", "voice": "passive"},
        "segments": [
            {"role": "prefix_particle", "surface": "وَ", "gloss_contribution": "and"},
            {"role": "stem", "surface": "خُلِقَ", "gloss_contribution": "was created"},
        ],
        "hover_contract": {
            "must_surface": ["and", "was created"],
            "must_not_surface": ["to make, create"],
            "reason": "The public hover must be token-shaped, not a lemma gloss.",
        },
        "evidence_label": "qac:wordmorphology:4:28:6:reviewed",
        "evidence_gate": "two_vote_required",
        "evidence_reasoning": "Reviewed grammar evidence treats the first segment as a particle and the host as a passive perfect verb.",
        "pos": "verb",
        "syntax": {"dependency": "resumption", "linked_locs": []},
    },
    "33:63:1": {
        "parse_key": {
            "key": "V:I:IMPF:ACT:3MS+OBJ.2MS",
            "summary": "Form I imperfect active third-person masculine singular verb with second-person masculine singular object suffix.",
            "components": [
                {"label": "PFX", "value": "imperfect prefix marking 3ms verb form"},
                {"label": "V", "value": "Form I imperfect active verb stem"},
                {"label": "OBJ", "value": "2nd masculine singular object pronoun"},
            ],
        },
        "morphology": {"aspect": "imperfect", "gender": "masculine", "mood": "indicative", "number": "singular", "person": "3", "verb_form": "I", "voice": "active"},
        "segments": [
            {"role": "verb_prefix", "surface": "يَ", "gloss_contribution": "3ms imperfect marker"},
            {"role": "stem", "surface": "سْـَٔلُ", "gloss_contribution": "ask"},
            {"role": "object_pronoun", "surface": "كَ", "gloss_contribution": "you", "person": "2", "number": "singular", "gender": "masculine", "case": "accusative"},
        ],
        "hover_contract": {
            "must_surface": ["ask", "you"],
            "must_not_surface": ["to ask, question", "ask only"],
            "reason": "The attached object pronoun must be visible in the hover and in the parse breakdown.",
        },
        "evidence_label": "qac:wordmorphology:33:63:1:reviewed",
        "evidence_gate": "two_vote_required",
        "evidence_reasoning": "Reviewed grammar evidence identifies the host as a 3ms imperfect verb and kaf as a 2ms object pronoun.",
        "pos": "verb",
        "syntax": {"dependency": "object", "linked_locs": ["33:63:2"]},
    },
}


def strip_marks(text):
    text = HARAKAT_RE.sub("", text or "")
    return (
        text.replace("ٱ", "ا")
        .replace("ـ", "")
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
    )


def qac_lookup(qac, surah_ayah, norm):
    row = qac.get((surah_ayah, norm))
    if row:
        return row
    variants = []
    if norm.startswith("يايها"):
        variants.append("ياايها" + norm[len("يايها"):])
    elif norm.startswith("ياايها"):
        variants.append("يايها" + norm[len("ياايها"):])
    for variant in variants:
        row = qac.get((surah_ayah, variant))
        if row:
            return row
    return {}


def is_mark(ch):
    return bool(HARAKAT_RE.match(ch))


def take_base_with_marks(text, index):
    if index >= len(text):
        return "", index
    end = index + 1
    while end < len(text) and is_mark(text[end]):
        end += 1
    return text[index:end], end


def take_article(text, index):
    if index >= len(text) or strip_marks(text[index]) != "ا":
        return "", index
    first, index = take_base_with_marks(text, index)
    if index >= len(text) or text[index] != "ل":
        return "", index
    lam, index = take_base_with_marks(text, index)
    return first + lam, index


def split_art_nominal(surface):
    article, index = take_article(surface, 0)
    if not article or index >= len(surface):
        return None
    return [
        {"role": "definite_article", "surface": article, "gloss_contribution": "the"},
        {"role": "stem", "surface": surface[index:], "gloss_contribution": None},
    ]


def split_conj_art_nominal(surface):
    conj, index = take_base_with_marks(surface, 0)
    if strip_marks(conj) != "و":
        return None
    article, index = take_article(surface, index)
    if not article or index >= len(surface):
        return None
    return [
        {"role": "prefix_conjunction", "surface": conj, "gloss_contribution": "and"},
        {"role": "definite_article", "surface": article, "gloss_contribution": "the"},
        {"role": "stem", "surface": surface[index:], "gloss_contribution": None},
    ]


def split_bare_nominal(surface):
    if not surface:
        return None
    return [{"role": "stem", "surface": surface, "gloss_contribution": None}]


def split_particle_verb(surface):
    particle, index = take_base_with_marks(surface, 0)
    bare = strip_marks(particle)
    if bare not in {"و", "ف"} or index >= len(surface):
        return None
    role = "prefix_conjunction" if bare == "و" else "prefix_particle"
    gloss = "and" if bare == "و" else "so/then"
    return [
        {"role": role, "surface": particle, "gloss_contribution": gloss},
        {"role": "stem", "surface": surface[index:], "gloss_contribution": None},
    ]


def split_vocative_ayyuhā(surface):
    norm = strip_marks(surface)
    if not norm.startswith(("ياايها", "يايها", "يأيها")):
        return None
    if "أَيُّ" in surface:
        idx = surface.index("أَيُّ")
    elif "أَي" in surface:
        idx = surface.index("أَي")
    else:
        return None
    ya = surface[:idx]
    rest = surface[idx:]
    h_index = rest.rfind("ه")
    if h_index > 0:
        support = rest[:h_index]
        attention = rest[h_index:]
    else:
        support = rest
        attention = ""
    if not ya or not support:
        return None
    rows = [
        {"role": "vocative_particle", "surface": ya, "gloss_contribution": "O"},
        {"role": "vocative_support", "surface": support, "gloss_contribution": "you"},
    ]
    if attention:
        rows.append({"role": "attention_particle", "surface": attention, "gloss_contribution": "attention marker"})
    return rows


def strip_for_suffix(text):
    return strip_marks(text).replace("ـ", "")


def find_suffix_pronoun(surface):
    bare_surface = strip_for_suffix(surface)
    for suffix, meta in SUFFIX_PRONOUNS:
        if bare_surface.endswith(strip_for_suffix(suffix)):
            suffix_len = len(suffix)
            return surface[-suffix_len:], meta
    return None, None


def split_verb_object_suffix(surface):
    suffix, meta = find_suffix_pronoun(surface)
    if not suffix or len(surface) <= len(suffix):
        return None
    before_suffix = surface[:-len(suffix)]
    particle_rows = []
    first, index = take_base_with_marks(before_suffix, 0)
    if strip_marks(first) in {"و", "ف"} and index < len(before_suffix):
        particle_rows.append({
            "role": "prefix_conjunction" if strip_marks(first) == "و" else "prefix_particle",
            "surface": first,
            "gloss_contribution": "and" if strip_marks(first) == "و" else "so/then",
        })
        before_suffix = before_suffix[index:]

    subject_rows = []
    if before_suffix.endswith("نَا"):
        subject_surface = "نَا"
        before_suffix = before_suffix[:-len(subject_surface)]
        subject_rows.append({
            "role": "subject_pronoun",
            "surface": subject_surface,
            "gloss_contribution": "We",
            "person": "1",
            "number": "plural",
            "gender": "common",
            "case": "nominative",
        })

    verb_rows = []
    first, index = take_base_with_marks(before_suffix, 0)
    if strip_marks(first) in {"ي", "ت", "أ", "ن"} and index < len(before_suffix):
        verb_rows.append({"role": "verb_prefix", "surface": first, "gloss_contribution": "imperfect marker"})
        before_suffix = before_suffix[index:]
    if not before_suffix:
        return None
    return particle_rows + verb_rows + [
        {"role": "stem", "surface": before_suffix, "gloss_contribution": None},
    ] + subject_rows + [{
        "role": "object_pronoun",
        "surface": suffix,
        "gloss_contribution": meta["gloss"],
        "person": meta["person"],
        "number": meta["number"],
        "gender": meta["gender"],
        "case": "accusative",
    }]


def best_gloss(record):
    glosses = record.get("glosses") or []
    best = record.get("best", 0)
    if isinstance(best, int) and 0 <= best < len(glosses) and isinstance(glosses[best], dict):
        return (glosses[best].get("text") or "").strip()
    return ""


def strip_english_article(gloss):
    return re.sub(r"^\(?the\)?\s+", "", (gloss or "").strip(), flags=re.I).strip()


def load_qac_tokroots(path):
    out = {}
    if not path or not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        surah_ayah, surface, root, pos = parts[:4]
        out[(surah_ayah, strip_marks(surface))] = {"root": root or None, "pos": pos or None}
    return out


def loc_sort_key(loc):
    try:
        return tuple(int(part) for part in str(loc).split(":"))
    except Exception:
        return (999, 999, 999, str(loc))


def display_for(segments, pos):
    def qclass(role):
        if role == "definite_article":
            return "qg-article"
        if role == "prefix_conjunction":
            return "qg-particle"
        if role == "prefix_particle":
            return "qg-particle"
        if role == "verb_prefix":
            return "qg-verb"
        if role in {"subject_pronoun", "object_pronoun", "possessive_pronoun"}:
            return "qg-pronoun"
        if role in {"vocative_particle", "vocative_support"}:
            return "qg-vocative"
        if role == "attention_particle":
            return "qg-particle"
        if role == "stem":
            return "qg-noun" if pos == "noun" else "qg-verb" if pos == "verb" else "qg-unknown"
        return "qg-unknown"

    def label(role):
        return {
            "definite_article": "ART",
            "prefix_conjunction": "CONJ",
            "prefix_particle": "PART",
            "verb_prefix": "PFX",
            "subject_pronoun": "PRON",
            "object_pronoun": "PRON",
            "vocative_particle": "VOC",
            "vocative_support": "VOC",
            "attention_particle": "ATTN",
            "stem": "STEM",
        }.get(role, "UNK")

    return {
        "palette": "qamus-grammar-v1",
        "segments": [
            {"segment_index": index, "role": segment["role"], "class": qclass(segment["role"]), "label": label(segment["role"])}
            for index, segment in enumerate(segments)
        ],
    }


def segments_join(segments):
    return "".join(segment.get("surface", "") for segment in segments)


def apply_reviewed_override(loc, row):
    override = REVIEWED_OVERRIDES.get(loc)
    if not override:
        return row
    surface = row["surface"]
    if segments_join(override["segments"]) != surface:
        return row
    out = dict(row)
    out["pos"] = override.get("pos", out.get("pos"))
    out["morphology"] = override.get("morphology", out.get("morphology") or {})
    out["segments"] = override["segments"]
    out["parse_key"] = override["parse_key"]
    out["display"] = display_for(out["segments"], out["pos"])
    out["syntax"] = override.get("syntax", out.get("syntax") or {"dependency": "null", "linked_locs": []})
    out["hover_contract"] = override["hover_contract"]
    out["evidence"] = {
        "labels": [override["evidence_label"]],
        "gate": override.get("evidence_gate", "two_vote_required"),
        "reasoning": override.get("evidence_reasoning"),
    }
    return out


def candidate_for_record(loc, record, qac, lanes):
    surface = record.get("ar") or ""
    norm = strip_marks(surface)
    surah_ayah = ":".join(str(loc).split(":")[:2])
    qac_row = qac_lookup(qac, surah_ayah, norm)
    if record.get("parse_key") or record.get("display") or record.get("segments"):
        return None

    lane = None
    segments = None
    pos = None
    if qac_row.get("pos") == "N" and "vocative_ayyuhā" in lanes and norm.startswith(("ياايها", "يايها")):
        lane = "vocative_ayyuhā"
        pos = "vocative_particle"
        segments = split_vocative_ayyuhā(surface)
    elif qac_row.get("pos") == "N" and "conj_art_nominal" in lanes and norm.startswith("وال"):
        lane = "conj_art_nominal"
        pos = "noun"
        segments = split_conj_art_nominal(surface)
    elif qac_row.get("pos") == "N" and "art_nominal" in lanes and norm.startswith("ال"):
        lane = "art_nominal"
        pos = "noun"
        segments = split_art_nominal(surface)
    elif qac_row.get("pos") == "N" and "bare_nominal" in lanes:
        lane = "bare_nominal"
        pos = "noun"
        segments = split_bare_nominal(surface)
    elif qac_row.get("pos") == "V" and "particle_verb" in lanes and norm[:1] in {"و", "ف"}:
        lane = "particle_verb"
        pos = "verb"
        segments = split_particle_verb(surface)
    elif qac_row.get("pos") == "V" and "verb_object_suffix" in lanes:
        lane = "verb_object_suffix"
        pos = "verb"
        segments = split_verb_object_suffix(surface)
    if not segments:
        return None
    if segments_join(segments) != surface:
        return None

    stem_gloss = strip_english_article(best_gloss(record)) or "host"
    for segment in reversed(segments):
        if segment.get("role") == "stem" and not segment.get("gloss_contribution"):
            segment["gloss_contribution"] = stem_gloss
            break
    must_surface = [seg["gloss_contribution"] for seg in segments if seg.get("gloss_contribution")]
    lane_key = {
        "conj_art_nominal": "CONJ+ART+N:DEF",
        "art_nominal": "ART+N:DEF",
        "bare_nominal": "N",
        "particle_verb": "PART+V",
        "verb_object_suffix": "V+OBJ",
        "vocative_ayyuhā": "VOC_PART+VOC_SUPPORT+ATTN",
    }[lane]
    lane_summary = {
        "conj_art_nominal": "Visible conjunction plus definite noun; case/number/gender require separate certification.",
        "art_nominal": "Visible definite noun; case/number/gender require separate certification.",
        "bare_nominal": "Visible nominal token; case/number/gender require separate certification.",
        "particle_verb": "Visible particle plus verb host; particle function and verb inflection require separate certification.",
        "verb_object_suffix": "Verb host plus attached object pronoun candidate; subject/object roles require review.",
        "vocative_ayyuhā": "Vocative expression token with yā, ayyu, and attention marker visible.",
    }[lane]
    component_by_role = {
        "prefix_conjunction": ("CONJ", "and"),
        "prefix_particle": ("PART", "particle"),
        "verb_prefix": ("PFX", "verb prefix"),
        "definite_article": ("ART", "the"),
        "stem": ("V" if pos == "verb" else "N", "host; detailed inflection pending"),
        "subject_pronoun": ("SUBJ", "attached subject pronoun"),
        "object_pronoun": ("OBJ", "attached object pronoun"),
        "vocative_particle": ("VOC", "O"),
        "vocative_support": ("VOC", "you"),
        "attention_particle": ("ATTN", "attention marker"),
    }
    components = [
        {"label": component_by_role.get(seg["role"], ("UNK", "component"))[0], "value": component_by_role.get(seg["role"], ("UNK", "component"))[1]}
        for seg in segments
    ]
    row = {
        "loc": loc,
        "surface": surface,
        "lemma": None,
        "root": qac_row.get("root"),
        "pos": pos,
        "morphology": {"state": "definite"} if lane in {"art_nominal", "conj_art_nominal"} else {},
        "segments": segments,
        "parse_key": {"key": lane_key, "summary": lane_summary, "components": components},
        "display": display_for(segments, pos),
        "syntax": {"dependency": "null", "linked_locs": []},
        "hover_contract": {
            "must_surface": must_surface,
            "must_not_surface": ["host only", "duplicate article"],
            "reason": "Visible article/conjunction pieces must be accounted for without splitting the Arabic word.",
        },
        "evidence": {
            "labels": ["qac:tokroots:%s:%s:coarse-pos-root" % (loc, norm)],
            "gate": "human_source_review_required",
            "reasoning": "Coarse QAC POS/root confirms a nominal host for the %s lane; this candidate does not certify deeper i'rab." % lane,
        },
        "public_boundary": dict(PUBLIC_BOUNDARY),
    }
    return apply_reviewed_override(loc, row)


def build_candidates(artifact, qac_path, lanes, limit=None):
    data = json.loads(Path(artifact).read_text(encoding="utf-8"))
    words = data.get("words") or {}
    qac = load_qac_tokroots(qac_path)
    rows = []
    for loc, record in sorted(words.items(), key=lambda item: loc_sort_key(item[0])):
        if not isinstance(record, dict):
            continue
        row = candidate_for_record(loc, record, qac, lanes)
        if row:
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def read_jsonl(path):
    if not path or not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def candidate_for_verb_clitic_row(row):
    loc = row.get("loc")
    surface = row.get("surface") or ""
    if not loc or not surface or row.get("qac_pos") != "V":
        return None
    segments = split_verb_object_suffix(surface)
    if not segments or segments_join(segments) != surface:
        return None
    for segment in segments:
        if segment.get("role") == "stem" and not segment.get("gloss_contribution"):
            segment["gloss_contribution"] = "verb stem"
    key_parts = []
    if segments and segments[0].get("role") == "prefix_particle" and strip_marks(segments[0].get("surface", "")) == "ف":
        key_parts.append("FA")
    key_parts.append("V")
    for segment in segments:
        if segment.get("role") == "subject_pronoun":
            key_parts.append("SUBJ.%s%s" % (segment.get("person"), "P" if segment.get("number") == "plural" else "S"))
        if segment.get("role") == "object_pronoun":
            suffix_meta = next((meta for suffix, meta in SUFFIX_PRONOUNS if strip_for_suffix(segment.get("surface", "")) == strip_for_suffix(suffix)), None)
            key_parts.append((suffix_meta or {}).get("obj", "OBJ"))
    return {
        "loc": loc,
        "surface": surface,
        "lemma": row.get("lemma_candidate"),
        "root": row.get("root"),
        "pos": "verb",
        "morphology": {},
        "segments": segments,
        "parse_key": {
            "key": "+".join(key_parts),
            "summary": "Verb with attached pronoun candidate; full form, voice, and syntax require review.",
            "components": [
                {"label": "V", "value": "verb host"},
                {"label": "PRON", "value": "attached pronoun segment(s)"},
            ],
        },
        "display": display_for(segments, "verb"),
        "syntax": {"dependency": "object", "linked_locs": [], "role": "verb"},
        "hover_contract": {
            "must_surface": [seg["gloss_contribution"] for seg in segments if seg.get("gloss_contribution")],
            "must_not_surface": ["stem recognized", "suffix/pronoun pending", "host only"],
            "reason": "Verb suffix pronouns must be visible before this token can leave pending.",
        },
        "evidence": {
            "labels": ["qamus:verb_clitic_candidate:%s" % loc],
            "gate": "two_vote_required",
            "reasoning": "Existing verb-clitic candidate row marks an attached object pronoun; this metadata candidate remains review-gated.",
        },
        "public_boundary": dict(PUBLIC_BOUNDARY),
    }


def build_all_candidates(artifact, qac_path, lanes, limit=None, verb_clitic_path=None):
    rows = build_candidates(artifact, qac_path, lanes, limit)
    seen = {row["loc"] for row in rows}
    if "verb_object_suffix" in lanes and (not limit or len(rows) < limit):
        for source_row in read_jsonl(verb_clitic_path):
            row = candidate_for_verb_clitic_row(source_row)
            if row and row["loc"] not in seen:
                rows.append(row)
                seen.add(row["loc"])
                if limit and len(rows) >= limit:
                    break
    return rows


def write_jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sample_artifact(path):
    data = {
        "words": {
            "4:28:6": {"ar": "وَخُلِقَ", "glosses": [{"text": "to make, create", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "4:28:8": {"ar": "ضَعِيفًا", "glosses": [{"text": "weak", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "33:63:1": {"ar": "يَسْـَٔلُكَ", "glosses": [{"text": "to ask, question", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "2:21:1": {"ar": "يَٰٓأَيُّهَا", "glosses": [{"text": "O you (who)", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:13": {"ar": "وَٱلشَّمْسُ", "glosses": [{"text": "sun", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:14": {"ar": "وَٱلْقَمَرُ", "glosses": [{"text": "moon", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:12": {"ar": "ٱلْأَرْضِ", "glosses": [{"text": "earth, land", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            "22:18:10": {"ar": "وَمَن", "glosses": [{"text": "and whoever", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
        }
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_qac(path):
    Path(path).write_text(
        "\n".join([
            "4:28\tوخلق\tخلق\tV",
            "4:28\tضعيفا\tضعف\tN",
            "33:63\tيسلك\tسأل\tV",
            "2:21\tياأيها\tأيي\tN",
            "22:18\tوالشمس\tشمس\tN",
            "22:18\tوالقمر\tقمر\tN",
            "22:18\tالأرض\tأرض\tN",
            "22:18\tومن\t\tP",
            "",
        ]),
        encoding="utf-8",
    )


def self_test():
    with tempfile.TemporaryDirectory() as td:
        artifact = Path(td) / "wbw-lookup.json"
        qac = Path(td) / "qac-tokroots.tsv"
        sample_artifact(artifact)
        sample_qac(qac)
        verb_clitic = Path(td) / "verb_clitic.jsonl"
        write_jsonl(verb_clitic, [{
            "loc": "26:139:2",
            "surface": "فَأَهْلَكْنَاهُمْ",
            "root": "هلك",
            "qac_pos": "V",
            "enclitic": "هم",
            "clitic_role": "object",
        }])
        rows = build_all_candidates(
            artifact,
            qac,
            {"art_nominal", "bare_nominal", "conj_art_nominal", "particle_verb", "verb_object_suffix", "vocative_ayyuhā"},
            verb_clitic_path=verb_clitic,
        )
        assert len(rows) == 8, rows
        by_loc = {row["loc"]: row for row in rows}
        assert by_loc["22:18:13"]["segments"][0]["role"] == "prefix_conjunction", by_loc["22:18:13"]
        assert by_loc["22:18:13"]["segments"][1]["role"] == "definite_article", by_loc["22:18:13"]
        assert by_loc["22:18:12"]["parse_key"]["key"] == "ART+N:DEF", by_loc["22:18:12"]
        assert by_loc["4:28:6"]["parse_key"]["key"] == "REM+V:PERF:PASS:3MS", by_loc["4:28:6"]
        assert by_loc["33:63:1"]["parse_key"]["key"] == "V:I:IMPF:ACT:3MS+OBJ.2MS", by_loc["33:63:1"]
        assert by_loc["33:63:1"]["segments"][0]["role"] == "verb_prefix", by_loc["33:63:1"]
        assert by_loc["33:63:1"]["segments"][-1]["role"] == "object_pronoun", by_loc["33:63:1"]
        assert by_loc["2:21:1"]["segments"][0]["role"] == "vocative_particle", by_loc["2:21:1"]
        assert by_loc["2:21:1"]["segments"][1]["surface"] == "أَيُّ", by_loc["2:21:1"]
        assert by_loc["2:21:1"]["segments"][2]["surface"] == "هَا", by_loc["2:21:1"]
        assert by_loc["26:139:2"]["segments"][-1]["role"] == "object_pronoun", by_loc["26:139:2"]
        assert all(segments_join(row["segments"]) == row["surface"] for row in rows), rows
        assert not any(is_mark(row["segments"][i]["surface"][0]) for row in rows for i in range(len(row["segments"]))), rows
        assert "QAC" not in json.dumps(by_loc["22:18:13"]["parse_key"], ensure_ascii=False), by_loc["22:18:13"]
        assert by_loc["22:18:13"]["public_boundary"] == PUBLIC_BOUNDARY, by_loc["22:18:13"]
    print("build_rich_hover_morphosyntax_candidates self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build rich-hover morphosyntax metadata candidates.")
    parser.add_argument("artifact", nargs="?", default=str(STAGE / "wbw-lookup.json"))
    parser.add_argument("--qac-tokroots", default=str(STAGE / "qac-tokroots.tsv"))
    parser.add_argument("--out", help="write candidates to JSONL")
    parser.add_argument(
        "--lane",
        action="append",
        choices=("art_nominal", "bare_nominal", "conj_art_nominal", "particle_verb", "verb_object_suffix", "vocative_ayyuhā"),
        help="candidate lane; repeatable",
    )
    parser.add_argument("--verb-clitic-candidates", default=str(STAGE / "verb_clitic_cand.jsonl"))
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    lanes = set(args.lane or ["art_nominal", "bare_nominal", "conj_art_nominal", "particle_verb", "verb_object_suffix", "vocative_ayyuhā"])
    rows = build_all_candidates(args.artifact, args.qac_tokroots, lanes, args.max_records or None, args.verb_clitic_candidates)
    summary = {"total": len(rows), "by_lane": {}}
    for row in rows:
        key = str(row.get("parse_key", {}).get("key", ""))
        if key.startswith("CONJ+ART+N"):
            lane = "conj_art_nominal"
        elif key.startswith("ART+N"):
            lane = "art_nominal"
        elif key == "N":
            lane = "bare_nominal"
        elif key.startswith("VOC"):
            lane = "vocative_ayyuhā"
        elif "OBJ" in key:
            lane = "verb_object_suffix"
        elif "+V" in key or key.endswith("V"):
            lane = "particle_verb"
        else:
            lane = "other"
        summary["by_lane"][lane] = summary["by_lane"].get(lane, 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if args.out:
        write_jsonl(args.out, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
