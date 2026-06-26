#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a read-only full-corpus Qamus hover dogfood audit from shadow graph artifacts.

This is not a closure/apply tool. It audits every token row in a shadow graph and
classifies populated hovers separately from morphosyntax-certified rich hovers.
If a live `wbw-lookup.json` is supplied, it is used read-only to recover the
current visible gloss and rich-renderer payload for populated rows.
"""

import argparse
import collections
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR = os.path.join(ROOT, "tools", "validate_full_corpus_hover_dogfood_audit.py")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
FORBIDDEN_OUT_BITS = (
    "qamus-service/entries",
    "qamus-service\\entries",
    "qamus_wbw/build",
    "qamus_wbw\\build",
    "public_html",
    "/var/www",
    "\\www\\",
)

PUBLIC_SOURCE_LEAK_RE = re.compile(r"\b(QAC|MCP|Quran\.com|corpus\.quran|tafsir[-_ ]?center|informed_by|OCR|source[_-]photo)\b", re.I)

GENERIC_HOST_WORDS = {
    "sun",
    "moon",
    "stars",
    "mountains",
    "trees",
    "badr",
    "peace",
    "ask",
    "question",
    "foolish",
    "ones",
}

FUNCTION_WORDS = {
    "and",
    "the",
    "with",
    "by",
    "in",
    "at",
    "for",
    "to",
    "from",
    "of",
    "o",
    "not",
    "whether",
    "when",
    "so",
    "then",
}

ROLE_PROCEDURES = {
    "prefix_conjunction": ["nahw/procedures/particle-decision.md"],
    "conjunction": ["nahw/procedures/particle-decision.md"],
    "resumption_particle": ["nahw/procedures/particle-decision.md"],
    "result_particle": ["nahw/procedures/governing-particle-mood-review.md"],
    "prefix_cause_fa": ["nahw/procedures/governing-particle-mood-review.md"],
    "prefix_oath": ["nahw/procedures/pp-attachment-review.md"],
    "prefix_preposition": ["nahw/procedures/preposition-pronoun.md", "nahw/procedures/pp-attachment-review.md"],
    "preposition": ["nahw/procedures/preposition-pronoun.md"],
    "vocative_particle": ["nahw/procedures/exception-and-vocative-review.md"],
    "addressee_bridge": ["nahw/procedures/exception-and-vocative-review.md"],
    "object_pronoun": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/pronoun-attachment.md"],
    "possessive_pronoun": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/pronoun-attachment.md"],
    "subject_pronoun": ["sarf/procedures/clitic-and-host-morphology.md", "nahw/procedures/pronoun-attachment.md"],
    "imperfect_prefix": ["sarf/procedures/verb-form-and-mood-review.md"],
    "verb_stem": ["sarf/procedures/verb-form.md"],
    "verb": ["sarf/procedures/verb-form.md"],
    "definite_article": ["sarf/procedures/clitic-and-host-morphology.md"],
    "relative_particle": ["nahw/procedures/relative-interrogative.md"],
    "subordinating_particle": ["nahw/procedures/governing-particle-mood-review.md"],
}


def load_json(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path, required=True):
    if not os.path.exists(path):
        if required:
            raise SystemExit("missing required artifact: %s" % path)
        return []
    rows = []
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise SystemExit("%s:%d invalid JSON: %s" % (path, line_no, exc))
    return rows


def dump_json(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def dump_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def loc_tail(quran_loc):
    return str(quran_loc).split(":", 1)[1]


def quran_from_loc(loc):
    text = str(loc or "")
    return text if text.startswith("quran:") else "quran:%s" % text


def wbw_from_quran(quran_loc):
    return "wbw:%s" % loc_tail(quran_loc)


def rel(shadow_dir, name):
    path = os.path.join(shadow_dir, name)
    if not os.path.exists(path):
        raise SystemExit("missing shadow artifact %s" % path)
    return path


def ensure_safe_out_dir(out_dir):
    out_abs = os.path.abspath(out_dir)
    lowered = out_abs.lower().replace("\\", "/")
    if any(bit.lower().replace("\\", "/") in lowered for bit in FORBIDDEN_OUT_BITS):
        raise SystemExit("refusing likely live/runtime/public output path: %s" % out_dir)
    os.makedirs(out_abs, exist_ok=True)


def best_gloss(record):
    if not isinstance(record, dict):
        return None
    glosses = record.get("glosses") or []
    best = record.get("best", 0)
    if isinstance(best, int) and 0 <= best < len(glosses) and isinstance(glosses[best], dict):
        return (glosses[best].get("text") or "").strip() or None
    if glosses and isinstance(glosses[0], dict):
        return (glosses[0].get("text") or "").strip() or None
    return None


def public_boundary_from_record(record):
    leak = False
    if isinstance(record, dict):
        public_blob = json.dumps({
            "glosses": record.get("glosses"),
            "parse_key": record.get("parse_key"),
            "display": record.get("display"),
            "segments": record.get("segments"),
        }, ensure_ascii=False, sort_keys=True)
        leak = bool(PUBLIC_SOURCE_LEAK_RE.search(public_blob))
    return {
        "src": "qamus",
        "kind": "authored",
        "lang": "en",
        "internal_provenance_public": False,
        "external_source_names_public": False,
        "public_leak_detected": leak,
    }


def has_complete_rich_record(record):
    if not isinstance(record, dict):
        return False
    return bool(record.get("parse_key") and record.get("display") and record.get("segments"))


def normalize_segment(segment):
    if not isinstance(segment, dict):
        return {"role": "unknown", "surface": None}
    return {
        "role": segment.get("role") or segment.get("label") or "unknown",
        "surface": segment.get("surface") if "surface" in segment else segment.get("text"),
    }


def text_words(text):
    return set(re.findall(r"[a-z]+", (text or "").lower()))


def contains_any(text, words):
    seen = text_words(text)
    return bool(seen.intersection(words))


def detect_defects(surface, gloss, parse_obj, segments):
    detectors = []
    roles = {seg.get("role") for seg in segments if isinstance(seg, dict)}
    gloss_lower = (gloss or "").lower()
    sarf_pos = parse_obj.get("pos")
    proclitics = parse_obj.get("proclitics") or []
    suffix_pronouns = parse_obj.get("suffix_pronouns") or []
    enclitics = parse_obj.get("enclitics") or []
    particle_function = parse_obj.get("particle_function")

    if suffix_pronouns or any((item or {}).get("role") and "pronoun" in str((item or {}).get("role")) for item in enclitics):
        if not contains_any(gloss_lower, {"you", "him", "her", "them", "us", "me", "your", "his", "their", "our", "my"}):
            detectors.append("suffix_omitted")

    has_conj = bool({"prefix_conjunction", "conjunction", "resumption_particle"}.intersection(roles))
    has_article = "definite_article" in roles or any((item or {}).get("role") == "definite_article" for item in proclitics)
    if has_conj and has_article and not (contains_any(gloss_lower, {"and", "then", "so"}) and "the" in text_words(gloss_lower)):
        detectors.append("conjunction_article_omitted")

    if {"vocative_particle", "addressee_bridge"}.intersection(roles) and "o" not in text_words(gloss_lower):
        detectors.append("vocative_collapse")

    preposition_roles = {"prefix_preposition", "preposition", "prefix_oath", "prefix_comitative_waw", "prefix_cause_fa"}
    if preposition_roles.intersection(roles) or particle_function in {"preposition", "oath", "comitative", "cause"}:
        if not contains_any(gloss_lower, {"with", "by", "in", "at", "because", "through", "for", "to", "from", "of"}):
            detectors.append("preposition_oath_host_only_hover")

    if "the + the" in gloss_lower or re.search(r"\bthe\s+the\b", gloss_lower):
        detectors.append("article_duplication")

    if sarf_pos == "verb" and (gloss_lower.startswith("to ") or "," in gloss_lower or ";" in gloss_lower):
        detectors.append("finite_verb_dictionary_root_gloss_leakage")

    if sarf_pos in {"noun", "adjective", "proper_noun"} and gloss_lower.startswith("to "):
        detectors.append("nominal_pos_leakage")

    if (particle_function or preposition_roles.intersection(roles) or {"particle", "relative_particle", "subordinating_particle"}.intersection(roles)) and gloss:
        if not contains_any(gloss_lower, FUNCTION_WORDS):
            detectors.append("function_preposition_flattening")

    if len(segments) > 1 and gloss:
        host_only = text_words(gloss_lower).issubset(GENERIC_HOST_WORDS)
        function_roles = roles.intersection({"prefix_conjunction", "conjunction", "definite_article", "prefix_preposition", "object_pronoun", "possessive_pronoun"})
        if host_only and function_roles:
            detectors.append("clitic_host_collapse")

    if parse_obj.get("gate") == "two_vote_required" and parse_obj.get("decision_status") == "resolved":
        if parse_obj.get("grammar_triggers") and parse_obj.get("parse_confidence") in {"surface_only", "rich_metadata", "candidate", "unknown"}:
            detectors.append("surface_family_requires_token_only_override")

    return sorted(set(detectors))


def procedures_for(parse_obj, segments, detectors):
    procedures = set()
    for segment in segments:
        for procedure in ROLE_PROCEDURES.get(segment.get("role"), []):
            procedures.add(procedure)
    pos = parse_obj.get("pos")
    if pos == "verb":
        procedures.add("sarf/procedures/verb-form.md")
    if parse_obj.get("suffix_pronouns") or parse_obj.get("enclitics"):
        procedures.add("sarf/procedures/clitic-and-host-morphology.md")
        procedures.add("nahw/procedures/pronoun-attachment.md")
    if parse_obj.get("particle_function") == "ambiguous_ma" or "ma_function" in (parse_obj.get("grammar_triggers") or []):
        procedures.add("nahw/procedures/ma-function-decision.md")
    if "pp_attachment" in (parse_obj.get("grammar_triggers") or []):
        procedures.add("nahw/procedures/pp-attachment-review.md")
    if "vocative_collapse" in detectors:
        procedures.add("nahw/procedures/exception-and-vocative-review.md")
    if "nominal_pos_leakage" in detectors:
        procedures.add("sarf/procedures/masdar-participle.md")
    if not procedures:
        procedures.add("qamus/procedures/source-triangulation-and-public-boundary.md")
    return sorted(procedures)


def routes_for(dogfood_class, detectors):
    routes = set()
    if dogfood_class in {"known_defect", "token_only_override"}:
        routes.add("repair_candidate")
    if dogfood_class in {"pending/blocker", "populated_uncertified"}:
        routes.add("blocker_queue_row")
    if dogfood_class in {"known_defect", "needs_sarf_review", "needs_nahw_review", "token_only_override"} or detectors:
        routes.add("production_bug_lesson")
        routes.add("drill_regression_fixture")
    if dogfood_class in {"known_defect", "needs_sarf_review", "needs_nahw_review", "pending/blocker"} or detectors:
        routes.add("sarf_nahw_procedure_improvement")
    if dogfood_class in {"needs_renderer_segments", "string_correct_but_not_rich"}:
        routes.add("renderer_rich_hover_requirement")
    return sorted(routes)


def learner_breakdown(segments, parse_obj, gloss):
    if not segments:
        return None
    if parse_obj.get("gate") in {"never_auto", "human_review_required"}:
        return None
    pieces = []
    for segment in segments:
        role = segment.get("role") or "unknown"
        surf = segment.get("surface") or ""
        if role in {"prefix_conjunction", "conjunction", "resumption_particle"}:
            meaning = "and / connector"
        elif role == "definite_article":
            meaning = "the"
        elif "pronoun" in role:
            meaning = "attached pronoun"
        elif "verb" in role:
            meaning = "verb piece"
        elif "preposition" in role:
            meaning = "preposition"
        elif "vocative" in role:
            meaning = "vocative"
        elif role in {"noun", "stem"}:
            meaning = "host/stem"
        else:
            meaning = role.replace("_", " ")
        pieces.append("%s — %s — %s" % (surf, role.upper(), meaning))
    return "; ".join(pieces) if pieces else None


def classify_row(presence, gloss, rich_rendered, parse_row, parse_obj, detectors):
    family_class = (parse_row or {}).get("family_class")
    gate = parse_obj.get("gate")
    confidence = parse_obj.get("parse_confidence")
    status = parse_obj.get("decision_status")
    blocker = parse_obj.get("blocker")
    triggers = set(parse_obj.get("grammar_triggers") or [])

    if presence != "populated" or status == "pending":
        return "pending/blocker"
    if detectors:
        return "known_defect"
    if blocker:
        return "pending/blocker"
    if family_class == "token_only_required":
        return "token_only_override"
    if rich_rendered and gate == "auto_safe" and confidence == "certified" and family_class == "propagation_safe":
        return "rich_certified"
    if not rich_rendered and gate == "auto_safe" and confidence == "certified":
        return "string_correct_but_not_rich"
    if not rich_rendered and gloss:
        return "populated_uncertified"
    if {"suffix_pronoun", "preposition"}.intersection(triggers):
        return "needs_sarf_review"
    if triggers or gate in {"two_vote_required", "human_review_required", "never_auto"}:
        return "needs_nahw_review"
    if parse_obj.get("token_internal_segments") and not rich_rendered:
        return "needs_renderer_segments"
    return "populated_uncertified"


def blocker_for_class(dogfood_class, detectors, parse_obj, rich_rendered):
    if dogfood_class == "rich_certified":
        return None
    if dogfood_class == "string_correct_but_not_rich":
        return "visible hover may be text-correct, but rich renderer/learner breakdown is absent"
    if dogfood_class == "needs_renderer_segments":
        return "parse has segments but public rich renderer metadata is absent"
    if dogfood_class == "pending/blocker":
        return parse_obj.get("blocker") or "token remains missing/pending or grammar-gated"
    if detectors:
        return "production bug detectors: %s" % ", ".join(detectors)
    if dogfood_class == "needs_sarf_review":
        return "sarf evidence is incomplete or grammar-sensitive"
    if dogfood_class == "needs_nahw_review":
        return "nahw/context evidence is incomplete or grammar-sensitive"
    if dogfood_class == "token_only_override":
        return "parse family requires token-only review before propagation"
    return "populated hover is not rich-certified"


def build_row(token, hover, parse_row, decisions, wbw_record, validated_code_head, report_head):
    quran_loc = token.get("id") or quran_from_loc(token.get("loc"))
    wbw_loc = wbw_from_quran(quran_loc)
    parse_obj = (parse_row or {}).get("canonical_parse_object") or {}
    segments = [normalize_segment(seg) for seg in (parse_obj.get("token_internal_segments") or [])]
    record_segments = [normalize_segment(seg) for seg in ((wbw_record or {}).get("segments") or [])]
    if not segments and record_segments:
        segments = record_segments
    gloss = best_gloss(wbw_record)
    if not gloss and decisions:
        gloss = decisions[-1].get("gloss")
    has_record = bool((token or {}).get("has_wbw_record")) or wbw_record is not None or bool((hover or {}).get("has_wbw_record"))
    status = (token or {}).get("status") or (hover or {}).get("status") or parse_obj.get("decision_status")
    if gloss:
        presence = "populated"
    elif status == "pending" or parse_obj.get("blocker"):
        presence = "pending"
    else:
        presence = "missing" if not has_record else "pending"
    rich_rendered = bool(segments and (has_complete_rich_record(wbw_record) or parse_obj.get("parse_confidence") == "certified"))
    detectors = detect_defects(parse_obj.get("surface_raw") or token.get("surface"), gloss, parse_obj, segments)
    dogfood_class = classify_row(presence, gloss, rich_rendered, parse_row, parse_obj, detectors)
    procedures = procedures_for(parse_obj, segments, detectors)
    routes = routes_for(dogfood_class, detectors)
    boundary = public_boundary_from_record(wbw_record)
    breakdown = learner_breakdown(segments, parse_obj, gloss)
    blocker = blocker_for_class(dogfood_class, detectors, parse_obj, rich_rendered)
    parse_gate = parse_obj.get("gate")
    cert_mode = dogfood_class
    return {
        "id": "dogfood:%s" % wbw_loc,
        "audit_scope": "full_corpus_hover_dogfood",
        "quran_loc": quran_loc,
        "wbw_loc": wbw_loc,
        "surface": parse_obj.get("surface_raw") or token.get("surface") or (wbw_record or {}).get("ar"),
        "current_visible_gloss": gloss,
        "hover_presence": presence,
        "rich_rendered": rich_rendered,
        "dogfood_class": dogfood_class,
        "status": status,
        "token_internal_segments": segments,
        "sarf": {
            "root": parse_obj.get("root"),
            "pos": parse_obj.get("pos"),
            "verb_form": parse_obj.get("verb_form"),
            "voice": parse_obj.get("voice"),
            "aspect": parse_obj.get("aspect"),
            "mood": parse_obj.get("mood"),
            "person": parse_obj.get("person"),
            "number": parse_obj.get("number"),
            "gender": parse_obj.get("gender"),
            "case": parse_obj.get("case"),
            "state": parse_obj.get("state"),
            "derivative_type": parse_obj.get("derivative_type"),
            "proclitics": parse_obj.get("proclitics") or [],
            "enclitics": parse_obj.get("enclitics") or [],
            "suffix_pronouns": parse_obj.get("suffix_pronouns") or [],
        },
        "nahw": {
            "particle_function": parse_obj.get("particle_function"),
            "governor": parse_obj.get("governor"),
            "attachment": parse_obj.get("attachment"),
            "dependency_roles": parse_obj.get("dependency_roles") or [],
            "referent_class": parse_obj.get("referent_class"),
            "blocker": (token or {}).get("blocker") or parse_obj.get("blocker"),
        },
        "entry_linkage": {
            "parse_id": (parse_row or {}).get("id"),
            "parse_family_class": (parse_row or {}).get("family_class"),
            "parse_family_size": (parse_row or {}).get("family_size") or 0,
            "parse_gate": parse_gate,
            "parse_confidence": parse_obj.get("parse_confidence"),
            "whole_token_candidates": (parse_row or {}).get("candidate_entries") or [],
            "component_candidate_entries": (parse_row or {}).get("component_candidate_entries") or [],
            "resolved_qamus_entry_id": parse_obj.get("resolved_qamus_entry_id"),
            "resolved_sense_id": parse_obj.get("resolved_sense_id"),
            "no_entry_function_token_rationale": "function-token requires nahw classification" if (parse_obj.get("pos") == "particle" and not parse_obj.get("resolved_qamus_entry_id")) else None,
            "decision_ids": [row.get("id") for row in decisions],
        },
        "procedures": procedures,
        "public_boundary": boundary,
        "certification": {
            "mode": cert_mode,
            "string_populated_only": dogfood_class in {"populated_uncertified", "string_correct_but_not_rich"},
            "rich_certified": dogfood_class == "rich_certified",
            "propagation_allowed": bool((parse_row or {}).get("propagation_allowed")) and dogfood_class == "rich_certified",
            "requires_two_vote": parse_gate in {"two_vote_required", "human_review_required", "never_auto"} or bool(detectors),
            "validated_code_head": validated_code_head,
            "report_head": report_head,
        },
        "learner_breakdown": breakdown if dogfood_class == "rich_certified" else None,
        "learner_breakdown_blocker": None if dogfood_class == "rich_certified" else blocker,
        "detectors": detectors,
        "routes": routes,
        "source": "read_only_shadow_graph",
    }


def index_shadow(shadow_dir):
    tokens = load_jsonl(rel(shadow_dir, "token-index.jsonl"))
    hover_rows = load_jsonl(rel(shadow_dir, "hover-index.jsonl"))
    parse_rows = load_jsonl(rel(shadow_dir, "parse-keys.jsonl"))
    decisions = load_jsonl(rel(shadow_dir, "decision-index.jsonl"), required=False)
    parse_by_token = {}
    for row in parse_rows:
        for loc in row.get("seen_locs") or []:
            parse_by_token[loc] = row
    hovers_by_id = {row.get("id"): row for row in hover_rows if row.get("id")}
    decisions_by_quran = collections.defaultdict(list)
    for row in decisions:
        quran = row.get("quran_loc")
        if quran:
            decisions_by_quran[quran].append(row)
    return tokens, hovers_by_id, parse_by_token, decisions_by_quran


def load_wbw_records(path):
    data = load_json(path, default={}) or {}
    records = {}
    for loc, record in (data.get("words") or {}).items():
        if isinstance(record, dict):
            records[quran_from_loc(loc)] = record
    return records


def build_audit(shadow_dir, out_dir, wbw_json=None, validated_code_head=None, report_head=None, limit=None):
    ensure_safe_out_dir(out_dir)
    tokens, hovers_by_id, parse_by_token, decisions_by_quran = index_shadow(shadow_dir)
    wbw_records = load_wbw_records(wbw_json) if wbw_json else {}
    rows = []
    class_counts = collections.Counter()
    detector_counts = collections.Counter()
    route_counts = collections.Counter()
    presence_counts = collections.Counter()
    rich_rendered_count = 0
    public_leak_count = 0
    for token in tokens:
        quran_loc = token.get("id")
        if not QURAN_RE.match(str(quran_loc)):
            continue
        hover = hovers_by_id.get(wbw_from_quran(quran_loc))
        parse_row = parse_by_token.get(quran_loc) or {}
        decisions = decisions_by_quran.get(quran_loc, [])
        wbw_record = wbw_records.get(quran_loc)
        row = build_row(token, hover, parse_row, decisions, wbw_record, validated_code_head, report_head)
        rows.append(row)
        class_counts[row["dogfood_class"]] += 1
        detector_counts.update(row["detectors"])
        route_counts.update(row["routes"])
        presence_counts[row["hover_presence"]] += 1
        rich_rendered_count += 1 if row["rich_rendered"] else 0
        public_leak_count += 1 if row["public_boundary"]["public_leak_detected"] else 0
        if limit and len(rows) >= limit:
            break
    if not rows:
        raise SystemExit("refusing to write vacuous dogfood audit: no token rows")

    out_jsonl = os.path.join(out_dir, "full-corpus-hover-dogfood-audit.jsonl")
    out_meta = os.path.join(out_dir, "full-corpus-hover-dogfood-audit.meta.json")
    out_md = os.path.join(out_dir, "full-corpus-hover-dogfood-audit.md")
    dump_jsonl(out_jsonl, rows)
    meta = {
        "builder": "tools/build_full_corpus_hover_dogfood_audit.py",
        "audit_scope": "full_corpus_hover_dogfood",
        "read_only": True,
        "live_mutation_allowed": False,
        "shadow_dir": os.path.abspath(shadow_dir),
        "wbw_json": os.path.abspath(wbw_json) if wbw_json else None,
        "validated_code_head": validated_code_head,
        "report_head": report_head,
        "rows": len(rows),
        "dogfood_class_counts": dict(sorted(class_counts.items())),
        "hover_presence_counts": dict(sorted(presence_counts.items())),
        "rich_rendered_count": rich_rendered_count,
        "detector_counts": dict(sorted(detector_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "public_leak_count": public_leak_count,
        "note": "Populated hover text is not dogfood completion; rich_certified is a stricter row class.",
    }
    dump_json(out_meta, meta)
    write_markdown(out_md, meta)
    return out_jsonl, out_meta, out_md, meta


def write_markdown(path, meta):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Full-Corpus Hover Dogfood Audit\n\n")
        handle.write("Generated by `tools/build_full_corpus_hover_dogfood_audit.py`.\n\n")
        handle.write("This is read-only. It does not mutate live Qamus, rebuild WBW, restart services, or claim hover closure progress.\n\n")
        handle.write("- rows: `%s`\n" % meta["rows"])
        handle.write("- rich rendered rows: `%s`\n" % meta["rich_rendered_count"])
        handle.write("- public leak count: `%s`\n" % meta["public_leak_count"])
        handle.write("- validated code head: `%s`\n" % (meta.get("validated_code_head") or "unrecorded"))
        handle.write("- report head: `%s`\n\n" % (meta.get("report_head") or "unrecorded"))
        handle.write("## Dogfood Classes\n\n")
        for key, value in meta["dogfood_class_counts"].items():
            handle.write("- `%s`: `%s`\n" % (key, value))
        handle.write("\n## Detectors\n\n")
        if meta["detector_counts"]:
            for key, value in meta["detector_counts"].items():
                handle.write("- `%s`: `%s`\n" % (key, value))
        else:
            handle.write("- none\n")
        handle.write("\n## Routes\n\n")
        if meta["route_counts"]:
            for key, value in meta["route_counts"].items():
                handle.write("- `%s`: `%s`\n" % (key, value))
        else:
            handle.write("- none\n")


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        shadow = os.path.join(tmp, "shadow")
        out = os.path.join(tmp, "out")
        os.makedirs(shadow)
        token_rows = [
            {"id": "quran:4:28:7", "loc": "4:28:7", "surface": "ٱلْإِنسَانُ", "parse_id": "parse:111111111111111111111111", "parse_key": "parse:111111111111111111111111", "status": "resolved", "blocker": None, "has_wbw_record": True},
            {"id": "quran:33:63:1", "loc": "33:63:1", "surface": "يَسْأَلُكَ", "parse_id": "parse:222222222222222222222222", "parse_key": "parse:222222222222222222222222", "status": "resolved", "blocker": None, "has_wbw_record": True},
            {"id": "quran:22:18:13", "loc": "22:18:13", "surface": "وَٱلشَّمْسُ", "parse_id": "parse:444444444444444444444444", "parse_key": "parse:444444444444444444444444", "status": "resolved", "blocker": None, "has_wbw_record": True},
            {"id": "quran:86:14:1", "loc": "86:14:1", "surface": "وَمَا", "parse_id": "parse:333333333333333333333333", "parse_key": "parse:333333333333333333333333", "status": "pending", "blocker": "ma_function_ambiguous", "has_wbw_record": False},
        ]
        hover_rows = [
            {"id": "wbw:4:28:7", "loc": "4:28:7", "surface": "ٱلْإِنسَانُ", "status": "resolved", "has_wbw_record": True},
            {"id": "wbw:33:63:1", "loc": "33:63:1", "surface": "يَسْأَلُكَ", "status": "resolved", "has_wbw_record": True},
            {"id": "wbw:22:18:13", "loc": "22:18:13", "surface": "وَٱلشَّمْسُ", "status": "resolved", "has_wbw_record": True},
            {"id": "wbw:86:14:1", "loc": "86:14:1", "surface": "وَمَا", "status": "pending", "has_wbw_record": False},
        ]
        parse_rows = []
        for row in load_jsonl(os.path.join(ROOT, "qamus", "examples", "full_corpus_hover_dogfood_audit.sample.jsonl")):
            parse_id = row["entry_linkage"]["parse_id"]
            parse_rows.append({
                "id": parse_id,
                "canonical_parse_object": {
                    "parse_key_version": "self-test",
                    "quran_loc": row["quran_loc"],
                    "surface_raw": row["surface"],
                    "norm_strict": row["surface"],
                    "bare": row["surface"],
                    "root": row["sarf"]["root"],
                    "lemma": None,
                    "pos": row["sarf"]["pos"],
                    "qamus_entry_candidates": [{"entry_address": entry} for entry in row["entry_linkage"]["whole_token_candidates"]],
                    "qamus_component_candidates": [{"entry_address": entry, "source": "rich_wbw_segment", "role": "object_pronoun", "segment_text": "كَ", "token_loc": row["quran_loc"]} for entry in row["entry_linkage"]["component_candidate_entries"]],
                    "resolved_qamus_entry_id": row["entry_linkage"]["resolved_qamus_entry_id"],
                    "resolved_sense_id": row["entry_linkage"]["resolved_sense_id"],
                    "proclitics": row["sarf"]["proclitics"],
                    "enclitics": row["sarf"]["enclitics"],
                    "suffix_pronouns": row["sarf"]["suffix_pronouns"],
                    "token_internal_segments": row["token_internal_segments"],
                    "verb_form": row["sarf"]["verb_form"],
                    "voice": row["sarf"]["voice"],
                    "aspect": row["sarf"]["aspect"],
                    "mood": row["sarf"]["mood"],
                    "person": row["sarf"]["person"],
                    "number": row["sarf"]["number"],
                    "gender": row["sarf"]["gender"],
                    "case": row["sarf"]["case"],
                    "state": row["sarf"]["state"],
                    "derivative_type": row["sarf"]["derivative_type"],
                    "particle_function": row["nahw"]["particle_function"],
                    "governor": row["nahw"]["governor"],
                    "attachment": row["nahw"]["attachment"],
                    "referent_class": row["nahw"]["referent_class"],
                    "dependency_roles": row["nahw"]["dependency_roles"],
                    "grammar_triggers": ["suffix_pronoun"] if row["quran_loc"] == "quran:33:63:1" else (["ma_function"] if row["quran_loc"] == "quran:86:14:1" else []),
                    "gate": row["entry_linkage"]["parse_gate"],
                    "decision_status": row["status"],
                    "blocker": row["nahw"]["blocker"],
                    "evidence_version": {"fixture": "full-corpus-dogfood"},
                    "parse_confidence": row["entry_linkage"]["parse_confidence"],
                },
                "seen_locs": [row["quran_loc"]],
                "family_size": 1,
                "candidate_entries": row["entry_linkage"]["whole_token_candidates"],
                "component_candidate_entries": row["entry_linkage"]["component_candidate_entries"],
                "component_candidate_join_statuses": [],
                "blockers": [row["nahw"]["blocker"]] if row["nahw"]["blocker"] else [],
                "gates": [row["entry_linkage"]["parse_gate"]],
                "confidences": [row["entry_linkage"]["parse_confidence"]],
                "family_class": row["entry_linkage"]["parse_family_class"],
                "propagation_allowed": row["entry_linkage"]["parse_family_class"] == "propagation_safe",
                "runtime_parse_key": None,
            })
        parse_rows.append({
            "id": "parse:444444444444444444444444",
            "canonical_parse_object": {
                "parse_key_version": "self-test",
                "quran_loc": "quran:22:18:13",
                "surface_raw": "وَٱلشَّمْسُ",
                "norm_strict": "وَٱلشَّمْسُ",
                "bare": "شمس",
                "root": "ش م س",
                "lemma": None,
                "pos": "noun",
                "qamus_entry_candidates": [{"entry_address": "qamus:n:sun"}],
                "qamus_component_candidates": [],
                "resolved_qamus_entry_id": "qamus:n:sun",
                "resolved_sense_id": 1,
                "proclitics": [{"role": "conjunction", "surface": "وَ"}, {"role": "definite_article", "surface": "ٱلْ"}],
                "enclitics": [],
                "suffix_pronouns": [],
                "token_internal_segments": [{"role": "conjunction", "surface": "وَ"}, {"role": "definite_article", "surface": "ٱلْ"}, {"role": "noun", "surface": "شَّمْسُ"}],
                "verb_form": None,
                "voice": None,
                "aspect": None,
                "mood": None,
                "person": None,
                "number": "singular",
                "gender": "feminine",
                "case": "nominative",
                "state": "definite",
                "derivative_type": None,
                "particle_function": "conjunction",
                "governor": None,
                "attachment": None,
                "referent_class": None,
                "dependency_roles": [],
                "grammar_triggers": ["prefix_conjunction", "definite_article"],
                "gate": "human_review_required",
                "decision_status": "resolved",
                "blocker": None,
                "evidence_version": {"fixture": "full-corpus-dogfood"},
                "parse_confidence": "candidate",
            },
            "seen_locs": ["quran:22:18:13"],
            "family_size": 1,
            "candidate_entries": ["qamus:n:sun"],
            "component_candidate_entries": [],
            "component_candidate_join_statuses": [],
            "blockers": [],
            "gates": ["human_review_required"],
            "confidences": ["candidate"],
            "family_class": "human_review_required",
            "propagation_allowed": False,
            "runtime_parse_key": None,
        })
        decision_rows = [
            {"id": "decision:token-4-28-7", "quran_loc": "quran:4:28:7", "wbw_loc": "wbw:4:28:7", "parse_id": "parse:111111111111111111111111", "gloss": "the human being"},
            {"id": "decision:token-33-63-1", "quran_loc": "quran:33:63:1", "wbw_loc": "wbw:33:63:1", "parse_id": "parse:222222222222222222222222", "gloss": "to ask, question"},
            {"id": "decision:token-22-18-13", "quran_loc": "quran:22:18:13", "wbw_loc": "wbw:22:18:13", "parse_id": "parse:444444444444444444444444", "gloss": "and + the sun"},
        ]
        wbw = {
            "words": {
                "4:28:7": {"ar": "ٱلْإِنسَانُ", "glosses": [{"text": "the human being", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0, "parse_key": {"key": "ART+N"}, "display": {"palette": "qamus-grammar-v1"}, "segments": [{"role": "definite_article", "surface": "ٱلْ"}, {"role": "noun", "surface": "إِنسَانُ"}]},
                "33:63:1": {"ar": "يَسْأَلُكَ", "glosses": [{"text": "to ask, question", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0, "parse_key": {"key": "V:I:IMPF:ACT:3MS+OBJ.2MS"}, "display": {"palette": "qamus-grammar-v1"}, "segments": [{"role": "imperfect_prefix", "surface": "يَ"}, {"role": "verb_stem", "surface": "سْأَلُ"}, {"role": "object_pronoun", "surface": "كَ"}]},
                "22:18:13": {"ar": "وَٱلشَّمْسُ", "glosses": [{"text": "and + the sun", "src": "qamus", "kind": "authored", "lang": "en"}], "best": 0},
            }
        }
        dump_jsonl(os.path.join(shadow, "token-index.jsonl"), token_rows)
        dump_jsonl(os.path.join(shadow, "hover-index.jsonl"), hover_rows)
        dump_jsonl(os.path.join(shadow, "parse-keys.jsonl"), parse_rows)
        dump_jsonl(os.path.join(shadow, "decision-index.jsonl"), decision_rows)
        dump_json(os.path.join(shadow, "wbw-lookup.json"), wbw)
        out_jsonl, _out_meta, _out_md, meta = build_audit(shadow, out, wbw_json=os.path.join(shadow, "wbw-lookup.json"), validated_code_head="self-test-head", report_head="self-test-report")
        result = subprocess.run([sys.executable, VALIDATOR, out_jsonl, "--expect-min-rows", "4"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise SystemExit(result.stdout + result.stderr)
        if meta["dogfood_class_counts"].get("known_defect") != 1:
            raise SystemExit("expected one known_defect row")
        if meta["dogfood_class_counts"].get("rich_certified") != 1:
            raise SystemExit("expected one rich_certified row")
        if meta["dogfood_class_counts"].get("pending/blocker") != 1:
            raise SystemExit("expected one pending/blocker row")
        if meta["dogfood_class_counts"].get("populated_uncertified") != 1:
            raise SystemExit("expected one populated_uncertified row")
        if meta["route_counts"].get("blocker_queue_row", 0) < 2:
            raise SystemExit("expected populated_uncertified rows to route to blocker queue")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-dir", help="Phase 1/2 live shadow graph output directory")
    parser.add_argument("--out-dir", help="Output directory for dogfood audit artifacts")
    parser.add_argument("--wbw-json", help="Optional read-only wbw-lookup.json for current visible gloss/rich payload")
    parser.add_argument("--validated-code-head", default=None)
    parser.add_argument("--report-head", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.shadow_dir or not args.out_dir:
        raise SystemExit("--shadow-dir and --out-dir are required")
    out_jsonl, out_meta, out_md, meta = build_audit(
        args.shadow_dir,
        args.out_dir,
        wbw_json=args.wbw_json,
        validated_code_head=args.validated_code_head,
        report_head=args.report_head,
        limit=args.limit,
    )
    print("wrote %s" % out_jsonl)
    print("wrote %s" % out_meta)
    print("wrote %s" % out_md)
    print(json.dumps({"rows": meta["rows"], "classes": meta["dogfood_class_counts"], "public_leak_count": meta["public_leak_count"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
