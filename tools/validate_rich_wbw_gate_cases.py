#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Phase 2.9 rich-WBW gate cases.

This is a read-only closeout guard. It checks that grammar-sensitive rich WBW
component evidence stays separate from whole-token Qamus candidates and never
weakens a row into auto-safe propagation.
"""
import argparse
import io
import json
import os
import sys
import tempfile


DEFAULT_CASES = {
    "quran:22:18:13": {
        "surface": "وَٱلشَّمْسُ",
        "trigger": "function_particle",
        "roles": {"conjunction", "definite_article", "noun"},
        "component_roles": {"conjunction", "definite_article"},
    },
    "quran:22:18:14": {
        "surface": "وَٱلْقَمَرُ",
        "trigger": "function_particle",
        "roles": {"conjunction", "definite_article", "noun"},
        "component_roles": {"conjunction", "definite_article"},
    },
    "quran:22:18:15": {
        "surface": "وَٱلنُّجُومُ",
        "trigger": "function_particle",
        "roles": {"conjunction", "definite_article", "noun"},
        "component_roles": {"conjunction", "definite_article"},
    },
    "quran:22:18:16": {
        "surface": "وَٱلْجِبَالُ",
        "trigger": "function_particle",
        "roles": {"conjunction", "definite_article", "noun"},
        "component_roles": {"conjunction", "definite_article"},
    },
    "quran:22:18:17": {
        "surface": "وَٱلشَّجَرُ",
        "trigger": "function_particle",
        "roles": {"conjunction", "definite_article", "noun"},
        "component_roles": {"conjunction", "definite_article"},
    },
    "quran:2:178:22": {
        "surface": "بِٱلْمَعْرُوفِ",
        "trigger": "preposition",
        "roles": {"preposition", "definite_article", "noun"},
        "component_roles": {"preposition", "definite_article"},
    },
    "quran:2:21:1": {
        "surface": "يَٰٓأَيُّهَا",
        "trigger": "vocative",
        "roles": {"vocative_particle", "addressee_bridge"},
        "component_roles": {"vocative_particle", "addressee_bridge"},
    },
}

SUPPLEMENTAL_COMPONENT_ROLES = {"root"}


def read_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except Exception as exc:
                raise SystemExit("%s:%d: bad JSON: %s" % (path, line_no, exc))


def parse_obj(row):
    obj = row.get("parse") or row.get("parse_object") or row.get("canonical_parse_object") or {}
    if not isinstance(obj, dict):
        return {}
    return obj


def component_entries(row, obj):
    entries = row.get("component_candidate_entries")
    if entries is None:
        entries = obj.get("component_candidate_entries")
    if entries is None:
        entries = obj.get("qamus_component_candidates")
    return entries or []


def component_joins(row, obj):
    joins = row.get("component_candidate_join_statuses")
    if joins is None:
        joins = obj.get("component_candidate_join_statuses")
    if joins is None:
        joins = obj.get("component_candidate_joins")
    return joins or []


def seen_locs(row, obj):
    locs = row.get("seen_locs") or []
    quran_loc = obj.get("quran_loc") or row.get("quran_loc")
    if quran_loc:
        locs = list(locs) + [quran_loc]
    return set(locs)


def roles_from_segments(obj):
    return {
        seg.get("role")
        for seg in obj.get("token_internal_segments") or []
        if isinstance(seg, dict) and seg.get("role")
    }


def roles_from_component_joins(row, obj):
    roles = set()
    for join in component_joins(row, obj):
        if not isinstance(join, dict):
            continue
        role = join.get("role")
        if role:
            roles.add(role)
        for status in join.get("join_status") or []:
            if isinstance(status, str) and status.startswith("role:"):
                roles.add(status.split(":", 1)[1])
    return roles


def row_has_rich_components(row, obj):
    return bool(component_entries(row, obj) or component_joins(row, obj) or obj.get("qamus_component_candidates"))


def exact_review_rows_by_loc(path):
    by_loc = {}
    rows = []
    for _line_no, row in read_jsonl(path):
        rows.append(row)
        for loc in row.get("quran_locs") or []:
            by_loc.setdefault(loc, []).append(row)
    return by_loc, rows


def exact_parse_rows_by_loc(path):
    by_loc = {}
    rows = []
    for _line_no, row in read_jsonl(path):
        obj = parse_obj(row)
        rows.append((row, obj))
        for loc in seen_locs(row, obj):
            by_loc.setdefault(loc, []).append((row, obj))
    return by_loc, rows


def join_preserves_component_provenance(join, loc):
    if not isinstance(join, dict):
        return False
    statuses = set(join.get("join_status") or [])
    if not statuses:
        source = join.get("source")
        role = join.get("role")
        segment = join.get("segment_text")
        token_loc = join.get("token_loc")
        return source == "rich_wbw_segment" and bool(role) and bool(segment) and token_loc == loc
    return (
        "source:rich_wbw_segment" in statuses
        and any(str(status).startswith("role:") for status in statuses)
        and any(str(status).startswith("segment_text:") for status in statuses)
        and "token_loc:%s" % loc in statuses
    )


def validate(parse_keys, review_pack, cases=None):
    errors = []
    cases = cases or DEFAULT_CASES
    parse_by_loc, parse_rows = exact_parse_rows_by_loc(parse_keys)
    review_by_loc, review_rows = exact_review_rows_by_loc(review_pack)

    for row, obj in parse_rows:
        if not row_has_rich_components(row, obj):
            continue
        if row.get("family_class") == "propagation_safe":
            errors.append("%s has rich component evidence but family_class=propagation_safe" % row.get("id"))
        if obj.get("gate") == "auto_safe":
            errors.append("%s has rich component evidence but parse gate=auto_safe" % row.get("id"))
        for candidate in obj.get("qamus_entry_candidates") or []:
            if isinstance(candidate, dict) and candidate.get("source") == "rich_wbw_segment":
                errors.append("%s put rich segment evidence in qamus_entry_candidates" % row.get("id"))

    for row in review_rows:
        if not row.get("component_candidate_entries"):
            continue
        if row.get("lane") == "propagation_safe_candidate":
            errors.append("%s has component candidates but lane=propagation_safe_candidate" % row.get("id"))
        if row.get("required_gate") == "auto_safe_after_preview":
            errors.append("%s has component candidates but required_gate=auto_safe_after_preview" % row.get("id"))

    for loc, spec in sorted(cases.items()):
        parse_hits = parse_by_loc.get(loc) or []
        review_hits = review_by_loc.get(loc) or []
        if len(parse_hits) != 1:
            errors.append("%s expected exactly 1 parse row, found %d" % (loc, len(parse_hits)))
            continue
        if len(review_hits) != 1:
            errors.append("%s expected exactly 1 review-pack row, found %d" % (loc, len(review_hits)))
            continue
        parse_row, obj = parse_hits[0]
        review_row = review_hits[0]
        surface = obj.get("surface_raw") or parse_row.get("surface_raw") or review_row.get("surface_sample")
        if surface != spec["surface"]:
            errors.append("%s surface mismatch: %r != %r" % (loc, surface, spec["surface"]))
        if parse_row.get("family_class") != "two_vote_required":
            errors.append("%s parse family must be two_vote_required, got %r" % (loc, parse_row.get("family_class")))
        if obj.get("gate") != "two_vote_required":
            errors.append("%s parse gate must be two_vote_required, got %r" % (loc, obj.get("gate")))
        if review_row.get("lane") != "two_vote_required":
            errors.append("%s review lane must be two_vote_required, got %r" % (loc, review_row.get("lane")))
        if review_row.get("required_gate") != "two_vote_required":
            errors.append("%s review required_gate must be two_vote_required, got %r" % (loc, review_row.get("required_gate")))
        triggers = set(obj.get("grammar_triggers") or [])
        if spec["trigger"] not in triggers:
            errors.append("%s missing trigger %r in %r" % (loc, spec["trigger"], sorted(triggers)))
        roles = roles_from_segments(obj)
        missing_roles = spec["roles"] - roles
        if missing_roles:
            errors.append("%s missing segment roles %s" % (loc, sorted(missing_roles)))
        component_roles = roles_from_component_joins(review_row, obj)
        required_component_roles = spec.get("component_roles") or set()
        if not required_component_roles.issubset(component_roles):
            errors.append(
                "%s component candidate joins missing grammar-sensitive roles %s"
                % (loc, sorted(required_component_roles - component_roles))
            )
        unknown_component_roles = component_roles - spec["roles"] - SUPPLEMENTAL_COMPONENT_ROLES
        if unknown_component_roles:
            errors.append("%s component candidate joins contain unexpected roles %s" % (loc, sorted(unknown_component_roles)))
        if not row_has_rich_components(parse_row, obj):
            errors.append("%s parse row lacks rich component candidates" % loc)
        if not review_row.get("component_candidate_entries"):
            errors.append("%s review row lacks component_candidate_entries" % loc)
        joins = review_row.get("component_candidate_join_statuses") or []
        if not joins:
            errors.append("%s review row lacks component_candidate_join_statuses" % loc)
        for join in joins:
            if not join_preserves_component_provenance(join, loc):
                errors.append("%s component join lacks source/role/segment/token provenance: %r" % (loc, join))

    return errors


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def self_test():
    with tempfile.TemporaryDirectory(prefix="rich-wbw-gate-") as td:
        parse_keys = os.path.join(td, "parse-keys.jsonl")
        review_pack = os.path.join(td, "review-pack.jsonl")
        parse_rows = []
        review_rows = []
        for idx, (loc, spec) in enumerate(DEFAULT_CASES.items(), 1):
            pid = "parse:%024x" % idx
            roles = sorted(spec["roles"])
            segments = [
                {"segment_index": i, "role": role, "surface": role[:1]}
                for i, role in enumerate(roles)
            ]
            parse_rows.append({
                "id": pid,
                "family_class": "two_vote_required",
                "seen_locs": [loc],
                "component_candidate_entries": ["qamus:p:%s" % idx],
                "component_candidate_join_statuses": [
                    {
                        "entry": "qamus:p:%s" % idx,
                        "join_status": [
                            "source:rich_wbw_segment",
                            "role:%s" % role,
                            "segment_text:%s" % role,
                            "token_loc:%s" % loc,
                        ],
                    }
                    for role in roles
                ],
                "canonical_parse_object": {
                    "surface_raw": spec["surface"],
                    "gate": "two_vote_required",
                    "grammar_triggers": [spec["trigger"]],
                    "parse_confidence": "rich_metadata",
                    "qamus_entry_candidates": [{"entry_address": "qamus:p:whole", "source": "usage_form"}],
                    "qamus_component_candidates": [{"entry_address": "qamus:p:%s" % idx, "source": "rich_wbw_segment"}],
                    "token_internal_segments": segments,
                },
            })
            review_rows.append({
                "id": "queue:%s" % pid.replace(":", "_"),
                "parse_id": pid,
                "lane": "two_vote_required",
                "required_gate": "two_vote_required",
                "quran_locs": [loc],
                "surface_sample": spec["surface"],
                "component_candidate_entries": ["qamus:p:%s" % idx],
                "component_candidate_join_statuses": [
                    {
                        "entry": "qamus:p:%s" % idx,
                        "join_status": [
                            "source:rich_wbw_segment",
                            "role:%s" % role,
                            "segment_text:%s" % role,
                            "token_loc:%s" % loc,
                        ],
                    }
                    for role in roles
                ],
            })
        parse_rows.append({
            "id": "parse:badbadbadbadbadbadbadbad",
            "family_class": "propagation_safe",
            "seen_locs": ["quran:9:9:9"],
            "component_candidate_entries": ["qamus:p:bad"],
            "canonical_parse_object": {
                "surface_raw": "وَشَيْءٌ",
                "gate": "auto_safe",
                "grammar_triggers": ["function_particle"],
                "qamus_component_candidates": [{"entry_address": "qamus:p:bad", "source": "rich_wbw_segment"}],
                "token_internal_segments": [{"role": "conjunction", "surface": "وَ"}],
            },
        })
        write_jsonl(parse_keys, parse_rows)
        write_jsonl(review_pack, review_rows)
        errors = validate(parse_keys, review_pack)
        if not any("family_class=propagation_safe" in error for error in errors):
            print("SELF-TEST FAIL: rich component auto-safe leak was not detected")
            return 1
        if not any("parse gate=auto_safe" in error for error in errors):
            print("SELF-TEST FAIL: rich component parse gate leak was not detected")
            return 1
        parse_rows.pop()
        write_jsonl(parse_keys, parse_rows)
        errors = validate(parse_keys, review_pack)
        if errors:
            print("SELF-TEST FAIL: valid rich gate cases were rejected")
            for error in errors:
                print("  " + error)
            return 1
        compact_bad_rows = list(review_rows)
        compact_bad_rows[0] = dict(compact_bad_rows[0])
        first_roles = sorted(DEFAULT_CASES[compact_bad_rows[0]["quran_locs"][0]]["roles"])
        compact_bad_rows[0]["component_candidate_join_statuses"] = [
            {
                "entry": "qamus:p:compact",
                "source": "rich_wbw_segment",
                "role": role,
                "segment_text": role,
            }
            for role in first_roles
        ]
        write_jsonl(review_pack, compact_bad_rows)
        errors = validate(parse_keys, review_pack)
        if not any("token provenance" in error for error in errors):
            print("SELF-TEST FAIL: compact component join without token_loc was not rejected")
            return 1
        compact_good_rows = list(review_rows)
        compact_good_rows[0] = dict(compact_good_rows[0])
        first_loc = compact_good_rows[0]["quran_locs"][0]
        compact_good_rows[0]["component_candidate_join_statuses"] = [
            {
                "entry": "qamus:p:compact",
                "source": "rich_wbw_segment",
                "role": role,
                "segment_text": role,
                "token_loc": first_loc,
            }
            for role in first_roles
        ]
        write_jsonl(review_pack, compact_good_rows)
        errors = validate(parse_keys, review_pack)
        if errors:
            print("SELF-TEST FAIL: compact component join with token_loc was rejected")
            for error in errors:
                print("  " + error)
            return 1
    print("PASS — rich WBW gate-case validator self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parse-keys")
    parser.add_argument("--review-pack-jsonl")
    parser.add_argument("--shadow-dir")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    parse_keys = args.parse_keys
    if not parse_keys and args.shadow_dir:
        parse_keys = os.path.join(args.shadow_dir, "parse-keys.jsonl")
    if not parse_keys or not args.review_pack_jsonl:
        parser.error("--parse-keys or --shadow-dir, plus --review-pack-jsonl, are required")
    errors = validate(parse_keys, args.review_pack_jsonl)
    if errors:
        for error in errors:
            print("FAIL " + error)
        raise SystemExit(1)
    print("PASS — rich WBW gate cases checked: %d" % len(DEFAULT_CASES))


if __name__ == "__main__":
    main()
