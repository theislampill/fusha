#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate RH-LIVE-00 source-triangulation readiness rows.

The rows are repo-only review artifacts. They can make a row ready for
exact-address two-vote review, but never live-applyable by themselves.
"""
import argparse
import io
import json
import os
import re
import tempfile


QURAN = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
ALLOWED_STATES = {
    "exact_address_two_vote_ready_not_applyable",
    "source_retry_required_not_certified",
}
ALLOWED_MCP_STATUS = {
    "queried_supports_segment_roles",
    "mcp_retry_required_token_expired",
}
ALLOWED_EVIDENCE_SCOPES = {"word_level", "phrase_context_level"}
CONTEXT_GLOSS_HINTS = {"they", "people", "he", "it", "them"}
FORBIDDEN_RAW_KEYS = {"irab", "sarf", "text", "raw", "raw_text", "source_text"}
FORBIDDEN_PUBLIC_LABELS = (
    "informed_by",
    "qac",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
)


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if line:
                yield lineno, json.loads(line)


def dump_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def err(errors, path, lineno, message):
    errors.append(f"{path}:{lineno}: {message}")


def public_leaks(public_preview):
    blob = json.dumps(public_preview, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in blob or "mcp" in blob]


def raw_key_leaks(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_RAW_KEYS:
                found.append(lowered)
            found.extend(raw_key_leaks(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(raw_key_leaks(child))
    return found


def validate_row(row, path, lineno, errors):
    quran_loc = str(row.get("quran_loc") or "")
    wbw_loc = str(row.get("wbw_loc") or "")
    if not QURAN.match(quran_loc):
        err(errors, path, lineno, "quran_loc must be quran:S:A:W")
    if not WBW.match(wbw_loc):
        err(errors, path, lineno, "wbw_loc must be wbw:S:A:W")
    if quran_loc and wbw_loc and wbw_loc != "wbw:" + quran_loc.split(":", 1)[1]:
        err(errors, path, lineno, "wbw_loc must match quran_loc")

    if row.get("readiness_id") != "rh-live-00-source:" + wbw_loc.replace(":", "_"):
        err(errors, path, lineno, "readiness_id must be derived from wbw_loc")
    if row.get("next_state") not in ALLOWED_STATES:
        err(errors, path, lineno, "next_state is not allowed")
    if row.get("certification_state_before") not in ("pending", "preview_only", "token_only_override"):
        err(errors, path, lineno, "certification_state_before is not allowed")
    if row.get("may_apply_live") is not False or row.get("live_mutation_allowed") is not False:
        err(errors, path, lineno, "rows must remain non-live and non-applyable")
    if row.get("public_exposable") is not False:
        err(errors, path, lineno, "public_exposable must be false")
    if row.get("owner_authorization_required") is not True:
        err(errors, path, lineno, "owner_authorization_required must be true")

    public_preview = row.get("public_preview") or {}
    if public_preview.get("src") != "qamus":
        err(errors, path, lineno, "public_preview.src must be qamus")
    if public_preview.get("kind") != "authored":
        err(errors, path, lineno, "public_preview.kind must be authored")
    if public_preview.get("lang") != "en":
        err(errors, path, lineno, "public_preview.lang must be en")
    if not public_preview.get("gloss"):
        err(errors, path, lineno, "public_preview.gloss is required")
    leaked = public_leaks(public_preview)
    if leaked:
        err(errors, path, lineno, "public_preview leaks forbidden label: " + ", ".join(sorted(set(leaked))))
    token_contribution = str(row.get("token_contribution_gloss") or "").strip()
    contextual_gloss = str(row.get("contextual_phrase_gloss") or public_preview.get("gloss") or "").strip()
    if not token_contribution:
        err(errors, path, lineno, "token_contribution_gloss is required")
    if not contextual_gloss:
        err(errors, path, lineno, "contextual_phrase_gloss is required")
    if contextual_gloss and public_preview.get("gloss") != contextual_gloss:
        err(errors, path, lineno, "public_preview.gloss must equal contextual_phrase_gloss for preview rows")
    context_differs = bool(token_contribution and contextual_gloss and token_contribution != contextual_gloss)
    hinted_context = bool(set(re.findall(r"[A-Za-z]+", contextual_gloss.lower())) & CONTEXT_GLOSS_HINTS)
    if context_differs:
        if row.get("adjacent_context_required") is not True:
            err(errors, path, lineno, "contextual gloss that differs from token contribution requires adjacent_context_required=true")
        locs = row.get("adjacent_context_locs")
        if not isinstance(locs, list) or not locs:
            err(errors, path, lineno, "contextual gloss that differs from token contribution requires adjacent_context_locs")
        if not row.get("contextual_gloss_certification_state"):
            err(errors, path, lineno, "contextual gloss that differs from token contribution requires contextual_gloss_certification_state")
        context_sources = [
            row.get("context_subject_source"),
            row.get("context_object_source"),
            row.get("context_governor_source"),
            row.get("context_attachment_source"),
        ]
        if not any(context_sources):
            err(errors, path, lineno, "contextual gloss that differs from token contribution requires a context_*_source field")

    boundary = row.get("public_boundary") or {}
    if boundary.get("src") != "qamus" or boundary.get("kind") != "authored" or boundary.get("lang") != "en":
        err(errors, path, lineno, "public_boundary must preserve qamus/authored/en")
    if boundary.get("status") != "source_clean_public_preview":
        err(errors, path, lineno, "public_boundary.status must be source_clean_public_preview")

    source = row.get("source_triangulation") or {}
    if source.get("internal_evidence_only") is not True:
        err(errors, path, lineno, "source_triangulation must be internal_evidence_only")
    scopes = set(source.get("evidence_scopes") or [])
    if not scopes or not scopes <= ALLOWED_EVIDENCE_SCOPES:
        err(errors, path, lineno, "source_triangulation.evidence_scopes must use allowed word/context scopes")
    if context_differs and "phrase_context_level" not in scopes:
        err(errors, path, lineno, "contextual gloss requires phrase_context_level evidence scope")
    mcp = source.get("tafsir_mcp_analyze_word") or {}
    if mcp.get("status") not in ALLOWED_MCP_STATUS:
        err(errors, path, lineno, "Tafsir MCP status is not allowed")
    if mcp.get("raw_text_stored") is not False:
        err(errors, path, lineno, "raw MCP text must not be stored")
    if mcp.get("aspects") != ["irab", "sarf"]:
        err(errors, path, lineno, "MCP aspects must be ['irab', 'sarf']")
    supports = mcp.get("supports")
    if not isinstance(supports, list):
        err(errors, path, lineno, "supports must be a list")
        supports = []

    if row.get("next_state") == "exact_address_two_vote_ready_not_applyable":
        if mcp.get("status") != "queried_supports_segment_roles":
            err(errors, path, lineno, "two-vote readiness requires queried supporting evidence")
        if not supports:
            err(errors, path, lineno, "two-vote readiness requires non-empty supports")
        if row.get("next_gate") != "exact_address_two_vote":
            err(errors, path, lineno, "supported rows must route to exact_address_two_vote")
        if context_differs:
            phrase = source.get("phrase_context_review") or {}
            if phrase.get("required") is not True:
                err(errors, path, lineno, "contextual gloss requires phrase_context_review.required=true")
            if phrase.get("status") not in ("queried_supports_adjacent_context", "queried_supports_adjacent_subject"):
                err(errors, path, lineno, "contextual gloss requires supporting phrase_context_review status")
            phrase_locs = phrase.get("adjacent_context_locs")
            if not isinstance(phrase_locs, list) or not set(row.get("adjacent_context_locs") or []) <= set(phrase_locs):
                err(errors, path, lineno, "phrase_context_review must include the adjacent context locs")
            if not phrase.get("supports"):
                err(errors, path, lineno, "phrase_context_review.supports must be non-empty")
    if row.get("next_state") == "source_retry_required_not_certified":
        if mcp.get("status") != "mcp_retry_required_token_expired":
            err(errors, path, lineno, "retry rows must record mcp_retry_required_token_expired")
        if supports:
            err(errors, path, lineno, "retry rows must not claim supports")
        if not str(row.get("next_gate") or "").startswith("source_retry_then_"):
            err(errors, path, lineno, "retry rows must route through source_retry_then_*")

    leaked_keys = sorted(set(raw_key_leaks(source)))
    if leaked_keys:
        err(errors, path, lineno, "source_triangulation stores raw/source text key(s): " + ", ".join(leaked_keys))


def validate_file(path):
    errors = []
    count = 0
    ready = 0
    retry = 0
    for lineno, row in iter_jsonl(path):
        count += 1
        validate_row(row, path, lineno, errors)
        if row.get("next_state") == "exact_address_two_vote_ready_not_applyable":
            ready += 1
        if row.get("next_state") == "source_retry_required_not_certified":
            retry += 1
    if count == 0:
        errors.append(f"{path}: no rows")
    if count and ready == 0:
        errors.append(f"{path}: expected at least one exact-address two-vote-ready row")
    return count, ready, retry, errors


def self_test():
    row = {
        "certification_state_before": "token_only_override",
        "live_mutation_allowed": False,
        "may_apply_live": False,
        "next_gate": "exact_address_two_vote",
        "next_state": "exact_address_two_vote_ready_not_applyable",
        "owner_authorization_required": True,
        "public_boundary": {"kind": "authored", "lang": "en", "src": "qamus", "status": "source_clean_public_preview"},
        "public_exposable": False,
        "public_preview": {"gloss": "ask you", "kind": "authored", "lang": "en", "src": "qamus"},
        "token_contribution_gloss": "ask you",
        "contextual_phrase_gloss": "ask you",
        "adjacent_context_required": False,
        "adjacent_context_locs": [],
        "context_subject_source": None,
        "context_object_source": None,
        "context_governor_source": None,
        "context_attachment_source": None,
        "contextual_gloss_certification_state": "word_level_only",
        "quran_loc": "quran:33:63:1",
        "readiness_id": "rh-live-00-source:wbw_33_63_1",
        "source_triangulation": {
            "evidence_scopes": ["word_level"],
            "internal_evidence_only": True,
            "tafsir_mcp_analyze_word": {
                "aspects": ["irab", "sarf"],
                "raw_text_stored": False,
                "status": "queried_supports_segment_roles",
                "supports": ["finite_imperfect_verb", "attached_object_pronoun"],
            },
        },
        "surface": "يَسْأَلُكَ",
        "wbw_loc": "wbw:33:63:1",
    }
    retry = dict(row)
    retry["quran_loc"] = "quran:22:18:14"
    retry["wbw_loc"] = "wbw:22:18:14"
    retry["readiness_id"] = "rh-live-00-source:wbw_22_18_14"
    retry["next_gate"] = "source_retry_then_exact_address_two_vote"
    retry["next_state"] = "source_retry_required_not_certified"
    retry["source_triangulation"] = {
        "evidence_scopes": ["word_level"],
        "internal_evidence_only": True,
        "tafsir_mcp_analyze_word": {
            "aspects": ["irab", "sarf"],
            "raw_text_stored": False,
            "status": "mcp_retry_required_token_expired",
            "supports": [],
        },
    }
    context_row = dict(row)
    context_row["public_preview"] = {"gloss": "the people ask you", "kind": "authored", "lang": "en", "src": "qamus"}
    context_row["token_contribution_gloss"] = "ask you"
    context_row["contextual_phrase_gloss"] = "the people ask you"
    context_row["adjacent_context_required"] = True
    context_row["adjacent_context_locs"] = ["quran:33:63:2", "wbw:33:63:2"]
    context_row["context_subject_source"] = "النَّاسُ at quran:33:63:2 / wbw:33:63:2"
    context_row["contextual_gloss_certification_state"] = "certified_not_applied_context_supported"
    context_row["source_triangulation"] = {
        "evidence_scopes": ["word_level", "phrase_context_level"],
        "internal_evidence_only": True,
        "phrase_context_review": {
            "adjacent_context_locs": ["quran:33:63:2", "wbw:33:63:2"],
            "raw_text_stored": False,
            "required": True,
            "status": "queried_supports_adjacent_subject",
            "supports": ["following_explicit_subject", "subject_not_attached_pronoun"],
        },
        "tafsir_mcp_analyze_word": row["source_triangulation"]["tafsir_mcp_analyze_word"],
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sample.jsonl")
        dump_jsonl(path, [row, retry, context_row])
        count, ready, retry_count, errors = validate_file(path)
        if errors or count != 3 or ready != 2 or retry_count != 1:
            raise SystemExit("self-test failed: " + "; ".join(errors))
        bad_context = dict(context_row)
        bad_context["adjacent_context_locs"] = []
        dump_jsonl(path, [bad_context])
        _, _, _, bad_errors = validate_file(path)
        if not any("requires adjacent_context_locs" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing adjacent context locs regression was not caught")
    print("RH-LIVE source-triangulation readiness self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.jsonl:
        parser.error("provide at least one JSONL file or --self-test")
    total = ready = retry = 0
    errors = []
    for path in args.jsonl:
        count, ready_count, retry_count, file_errors = validate_file(path)
        total += count
        ready += ready_count
        retry += retry_count
        errors.extend(file_errors)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"RH-LIVE source-triangulation readiness OK - rows={total} ready={ready} retry={retry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
