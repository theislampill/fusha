#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge dogfood review rows into validated shadow review-pack rows.

This is a read-only adapter between two existing repo-only stages:

1. full-corpus dogfood review packets, keyed by exact quran/wbw token address;
2. shadow review packs consumed by Phase 4 dry-run planning.

It does not author hovers, mutate live Qamus, rebuild WBW, sync mirrors, or
claim closure. It also keeps whole-token candidates separate from component
candidate evidence so rich segment hits cannot weaken grammar gates.
"""

import argparse
import io
import json
import os
import re
import tempfile

import validate_shadow_review_pack as review_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOGFOOD_REVIEW_PACK = os.path.join(
    ROOT,
    "qamus",
    "examples",
    "full_corpus_dogfood_review_pack.sample.jsonl",
)

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")
PARSE_RE = re.compile(r"^parse:[0-9a-f]+$")

FUNCTION_DETECTORS = {
    "function_preposition_flattening",
    "preposition_oath_host_only_hover",
    "conjunction_article_omitted",
    "vocative_collapse",
}
SARF_DETECTORS = {
    "suffix_omitted",
    "clitic_host_collapse",
    "finite_verb_dictionary_root_gloss_leakage",
    "nominal_pos_leakage",
    "article_duplication",
}

APPLY_POLICY = {
    "live_mutation_allowed": False,
    "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
    "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
    "detector_maturity": review_validator.DETECTOR_MATURITY,
}


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except Exception as exc:
                raise SystemExit("%s:%d invalid JSON: %s" % (path, line_no, exc))


def write_jsonl(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def emit_jsonl(rows):
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))


def unique(items):
    out = []
    seen = set()
    for item in items or []:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def qamus_entries(items):
    return [item for item in unique(items or []) if isinstance(item, str) and item.startswith("qamus:")]


def target(row):
    obj = row.get("target") or {}
    quran_loc = obj.get("quran_loc")
    wbw_loc = obj.get("wbw_loc")
    if not QURAN_RE.match(str(quran_loc)):
        raise ValueError("bad quran loc %r" % quran_loc)
    if not WBW_RE.match(str(wbw_loc)):
        raise ValueError("bad wbw loc %r" % wbw_loc)
    return obj


def parse_obj(row):
    obj = row.get("parse") or {}
    parse_id = obj.get("parse_id")
    if not PARSE_RE.match(str(parse_id)):
        raise ValueError("bad parse id %r" % parse_id)
    return obj


def grammar(row):
    return row.get("grammar") or {}


def sarf(row):
    return grammar(row).get("sarf") or {}


def nahw(row):
    return grammar(row).get("nahw") or {}


def segments(row):
    return grammar(row).get("token_internal_segments") or []


def detectors(row):
    return set(row.get("detectors") or [])


def grammar_triggers(row):
    triggers = []
    det = detectors(row)
    if det.intersection(FUNCTION_DETECTORS):
        triggers.append("function_particle")
    if det.intersection(SARF_DETECTORS):
        triggers.append("sarf_component")
    if "suffix_omitted" in det:
        triggers.append("suffix_pronoun")
    if "finite_verb_dictionary_root_gloss_leakage" in det:
        triggers.append("finite_verb")
    if row.get("dogfood_class") == "token_only_override":
        triggers.append("token_only_override")
    particle_function = nahw(row).get("particle_function")
    if particle_function:
        if str(particle_function).startswith("ambiguous"):
            triggers.append("ma_function")
        else:
            triggers.append(str(particle_function))
    return unique(triggers)


def lane_and_gate(row):
    parse = parse_obj(row)
    dogfood_class = row.get("dogfood_class")
    parse_gate = parse.get("parse_gate")
    family_class = parse.get("parse_family_class")
    component_candidates = qamus_entries((row.get("entry_linkage") or {}).get("component_candidate_entries") or [])

    if family_class == "quarantine_collision":
        return "quarantine_collision", "human_review_required", "token_only_until_collision_resolved"
    if dogfood_class == "pending/blocker":
        if parse_gate == "never_auto":
            return "never_auto", "never_auto", "quarantine"
        return "human_review_required", "human_review_required", "blocker_queue_review"
    if dogfood_class == "token_only_override":
        return "token_only_required", "two_vote_required", "token_only_review"
    if dogfood_class in {"needs_sarf_review", "needs_nahw_review", "populated_uncertified", "string_correct_but_not_rich"}:
        return "human_review_required", "human_review_required", "manual_review"
    if not parse.get("parse_id") or parse.get("parse_confidence") in {None, "surface_only", "unknown"}:
        return "unknown_parse", "human_review_required", "parse_enrichment_review"
    if parse_gate == "two_vote_required" or component_candidates:
        return "two_vote_required", "two_vote_required", "token_or_family_after_votes"
    if parse_gate == "never_auto":
        return "never_auto", "never_auto", "quarantine"
    if parse_gate == "auto_safe":
        return "propagation_safe_candidate", "auto_safe_after_preview", "parse_key_family_readonly_preview"
    return "human_review_required", "human_review_required", "manual_review"


def recommended_action(lane):
    if lane == "two_vote_required":
        return "build two-vote review packet with dogfood evidence and source-addressed reasoning"
    if lane == "token_only_required":
        return "prepare exact-address token-only certification packet; do not propagate by surface or parse family"
    if lane == "quarantine_collision":
        return "quarantine until candidate collision is resolved by exact-token nahw/sarf review"
    if lane == "never_auto":
        return "do not propagate; preserve blocker or route to owner/scholar review before any token decision"
    if lane == "unknown_parse":
        return "enrich parse with sarf/nahw evidence before any hover certification"
    if lane == "propagation_safe_candidate":
        return "preview exact token family before any append-only propagation"
    if lane == "missing_entry":
        return "route to owner entry review before any hover decision"
    return "route to human review with exact quran/wbw address and dogfood evidence"


def gate_reasons(row, lane):
    parse = parse_obj(row)
    reasons = []
    for trigger in grammar_triggers(row):
        reasons.append("grammar_trigger:%s" % trigger)
    blocker = row.get("blocker") or nahw(row).get("blocker") or parse.get("blocker")
    if blocker:
        reasons.append("blocker:%s" % blocker)
    if lane == "quarantine_collision":
        reasons.append("candidate_collision")
    parse_confidence = parse.get("parse_confidence")
    if parse_confidence:
        reasons.append("parse_confidence:%s" % parse_confidence)
    parse_gate = parse.get("parse_gate")
    if parse_gate:
        reasons.append("parse_gate:%s" % parse_gate)
    if lane == "two_vote_required":
        reasons.append("requires_independent_reason_agreement")
    if lane == "propagation_safe_candidate":
        reasons.append("requires_pre_apply_family_preview")
    return unique(reasons or ["parse_gate:human_review_required"])


def whole_candidate_joins(candidates):
    return [
        {
            "entry": entry,
            "join_status": ["candidate:dogfood_review_whole_token"],
        }
        for entry in candidates
    ]


def component_status(entry, seg, quran_loc):
    role = seg.get("role") or "component_candidate"
    surface = seg.get("surface") or ""
    return {
        "entry": entry,
        "join_status": [
            "source:rich_wbw_segment",
            "role:%s" % role,
            "segment_text:%s" % surface,
            "token_loc:%s" % quran_loc,
        ],
    }


def component_candidate_joins(row, component_candidates, quran_loc):
    segs = segments(row)
    if not component_candidates:
        return []
    if len(component_candidates) == len(segs):
        return [
            component_status(entry, seg, quran_loc)
            for entry, seg in zip(component_candidates, segs)
        ]
    joins = []
    # The dogfood row may know a component entry before it knows a perfect
    # entry-to-segment alignment. Preserve it as component evidence anyway, but
    # keep it out of whole-token candidates and auto-safe propagation.
    fallback = segs[-1] if segs else {"role": "component_candidate", "surface": target(row).get("surface") or ""}
    for entry in component_candidates:
        matched = None
        lower = entry.lower()
        for seg in segs:
            role = str(seg.get("role") or "").lower()
            surface = str(seg.get("surface") or "")
            if ("kaf" in lower and "pronoun" in role) or ("waw" in lower and "conjunction" in role) or ("al" in lower and "article" in role):
                matched = seg
                break
            if surface and surface in entry:
                matched = seg
                break
        joins.append(component_status(entry, matched or fallback, quran_loc))
    return joins


def parse_payload(row):
    s = sarf(row)
    n = nahw(row)
    parse = parse_obj(row)
    return {
        "gate": parse.get("parse_gate"),
        "blocker": row.get("blocker") or n.get("blocker"),
        "decision_status": "pending" if row.get("dogfood_class") == "pending/blocker" else "resolved",
        "parse_confidence": parse.get("parse_confidence") or "unknown",
        "pos": s.get("pos") or "unknown",
        "root": s.get("root"),
        "lemma": None,
        "particle_function": n.get("particle_function"),
        "grammar_triggers": grammar_triggers(row),
    }


def build_row(row):
    tgt = target(row)
    parse = parse_obj(row)
    lane, required_gate, scope = lane_and_gate(row)
    linkage = row.get("entry_linkage") or {}
    whole_candidates = qamus_entries(linkage.get("whole_token_candidates") or [])
    component_candidates = qamus_entries(linkage.get("component_candidate_entries") or [])
    if lane == "missing_entry":
        whole_candidates = []
    if lane == "propagation_safe_candidate" and component_candidates:
        # Component evidence may route review but cannot certify a whole token.
        lane, required_gate, scope = "two_vote_required", "two_vote_required", "token_or_family_after_votes"

    resolved = 0 if row.get("dogfood_class") == "pending/blocker" else 1
    unresolved = 1 - resolved
    out = {
        "id": "queue:%s" % parse["parse_id"].replace(":", "_"),
        "parse_id": parse["parse_id"],
        "lane": lane,
        "scope": scope,
        "recommended_action": recommended_action(lane),
        "required_gate": required_gate,
        "gate_reasons": gate_reasons(row, lane),
        "family_size": 1,
        "resolved_token_count": resolved,
        "unresolved_token_count": unresolved,
        "surface_sample": tgt.get("surface") or "",
        "quran_locs": [tgt["quran_loc"]],
        "wbw_locs": [tgt["wbw_loc"]],
        "token_sample": [tgt["quran_loc"]],
        "candidate_entries": whole_candidates,
        "candidate_join_statuses": whole_candidate_joins(whole_candidates),
        "parse": parse_payload(row),
        "apply_policy": APPLY_POLICY,
    }
    if component_candidates:
        out["component_candidate_entries"] = component_candidates
        out["component_candidate_join_statuses"] = component_candidate_joins(row, component_candidates, tgt["quran_loc"])
    return out


def build(rows, max_rows=None, lanes=None):
    selected = []
    wanted = set(lanes or [])
    for row in rows:
        out = build_row(row)
        if wanted and out["lane"] not in wanted:
            continue
        selected.append(out)
    if max_rows is not None:
        selected = selected[:max_rows]
    return selected


def validate_output(rows):
    with tempfile.TemporaryDirectory(prefix="dogfood-shadow-review-") as td:
        path = os.path.join(td, "review.jsonl")
        write_jsonl(path, rows)
        return review_validator.validate(path)


def self_test():
    rows = [row for _line, row in iter_jsonl(DEFAULT_DOGFOOD_REVIEW_PACK)]
    out = build(rows)
    count, errors = validate_output(out)
    if count != 2 or errors:
        print("SELF-TEST FAIL validation:", errors)
        return 1
    by_loc = {row["wbw_locs"][0]: row for row in out}
    ask = by_loc.get("wbw:33:63:1")
    if not ask or ask["lane"] != "two_vote_required":
        print("SELF-TEST FAIL: يَسْأَلُكَ did not route to two_vote_required")
        return 1
    if ask.get("candidate_entries") != ["qamus:5935ecfb1ec5"]:
        print("SELF-TEST FAIL: whole-token candidate was not preserved")
        return 1
    if ask.get("component_candidate_entries") != ["qamus:p:kaf"]:
        print("SELF-TEST FAIL: component candidate was not preserved separately")
        return 1
    statuses = ask.get("component_candidate_join_statuses") or []
    if not statuses or not any("source:rich_wbw_segment" in row.get("join_status", []) for row in statuses):
        print("SELF-TEST FAIL: component provenance missing")
        return 1
    if ask["required_gate"] != "two_vote_required":
        print("SELF-TEST FAIL: component evidence weakened gate")
        return 1
    ma = by_loc.get("wbw:86:14:1")
    if not ma or ma["lane"] != "quarantine_collision":
        print("SELF-TEST FAIL: ambiguous وَمَا did not remain quarantined")
        return 1
    if ma["resolved_token_count"] != 0 or ma["unresolved_token_count"] != 1:
        print("SELF-TEST FAIL: pending/blocker reconciliation wrong")
        return 1
    if any(row["lane"] == "propagation_safe_candidate" for row in out):
        print("SELF-TEST FAIL: dogfood sample created propagation_safe_candidate")
        return 1
    print("PASS — dogfood review to shadow review-pack bridge self-test")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dogfood_review_pack_jsonl", nargs="?", default=DEFAULT_DOGFOOD_REVIEW_PACK)
    parser.add_argument("--out-jsonl")
    parser.add_argument("--lane", action="append", help="include only a resulting shadow-review lane; may be repeated")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    rows = [row for _line, row in iter_jsonl(args.dogfood_review_pack_jsonl)]
    out = build(rows, max_rows=args.max_rows, lanes=args.lane)
    count, errors = validate_output(out)
    if errors:
        raise SystemExit("shadow review bridge validation failed:\n- %s" % "\n- ".join(errors[:20]))
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, out)
    else:
        emit_jsonl(out)
    print(json.dumps({
        "rows": count,
        "lanes": sorted({row["lane"] for row in out}),
        "live_mutation_allowed": False,
        "component_candidates_can_certify": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    print("PASS — dogfood review rows bridged to shadow review pack")


if __name__ == "__main__":
    main()
