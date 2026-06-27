#!/usr/bin/env python3
"""Build bounded review packets from full-corpus dogfood subagent lanes.

The six subagent lanes are read-only evidence. This tool deduplicates them by
exact hover slot (`wbw:S:A:W`) and produces compact review packets for the next
human/subagent pass. It does not author hovers, mutate live Qamus, rebuild WBW,
or claim coverage/correctness.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

import validate_full_corpus_dogfood_subagent_lanes as lane_validator


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "full_corpus_dogfood_subagent_lane.sample.jsonl")

QURAN_RE = re.compile(r"^quran:\d{1,3}:\d{1,3}:\d{1,3}$")
WBW_RE = re.compile(r"^wbw:\d{1,3}:\d{1,3}:\d{1,3}$")

CLASS_PRIORITY = {
    "known_defect": 1,
    "token_only_override": 2,
    "needs_sarf_review": 3,
    "needs_nahw_review": 4,
    "needs_renderer_segments": 5,
    "pending/blocker": 6,
    "string_correct_but_not_rich": 7,
    "populated_uncertified": 8,
    "rich_certified": 99,
}

LANE_TO_REVIEW = {
    "sarf-component-auditor": "sarf_component_review",
    "nahw-function-auditor": "nahw_function_review",
    "rich-renderer-auditor": "rich_renderer_review",
    "production-bug-detector": "production_bug_review",
    "qamus-entry-linkage-auditor": "entry_sense_linkage_review",
    "learner-explanation-auditor": "learner_explanation_review",
}

ISSUE_FAMILIES = {
    "suffix": "suffix_omitted",
    "object pronoun": "suffix_omitted",
    "attached object pronoun": "suffix_omitted",
    "conjunction": "conjunction_article_omitted",
    "article": "conjunction_article_omitted",
    "proclitic": "clitic_host_collapse",
    "preposition": "preposition_oath_host_only_hover",
    "oath": "preposition_oath_host_only_hover",
    "vocative": "vocative_collapse",
    "finite": "finite_verb_dictionary_gloss_leakage",
    "root gloss": "finite_verb_dictionary_gloss_leakage",
    "nominal": "nominal_pos_leakage",
    "pos leakage": "nominal_pos_leakage",
    "function": "function_preposition_flattening",
    "renderer": "missing_rich_renderer_segments",
    "segment": "missing_rich_renderer_segments",
    "entry_sense": "missing_exact_entry_sense_linkage",
    "entry sense": "missing_exact_entry_sense_linkage",
    "missing_exact_entry_sense_linkage": "missing_exact_entry_sense_linkage",
}

APPLY_POLICY = {
    "apply_allowed": False,
    "live_mutation_allowed": False,
    "coverage_claim_allowed": False,
    "identity": "quran:S:A:W plus wbw:S:A:W; parse key is not primary identity",
    "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
    "raw_surface_identity_allowed": False,
}


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit("%s:%d invalid JSON: %s" % (path, line_no, exc))


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def loc_sort_key(loc):
    text = str(loc or "").split(":", 1)[-1]
    out = []
    for part in text.split(":"):
        try:
            out.append(int(part))
        except Exception:
            out.append(9999)
    return tuple(out)


def packet_id(wbw_loc):
    return "dogfood-lane-packet:%s" % str(wbw_loc).replace(":", "_")


def lane_name(path):
    base = os.path.basename(path)
    return base[:-6] if base.endswith(".jsonl") else base


def input_paths(args):
    paths = []
    if args.lane_dir:
        paths.extend(
            os.path.join(args.lane_dir, name)
            for name in sorted(os.listdir(args.lane_dir))
            if name.endswith(".jsonl")
        )
    paths.extend(args.lane_jsonl or [])
    if not paths:
        paths = [SAMPLE]
    return paths


def normalize_lane_row(path, row):
    return {
        "lane": lane_name(path),
        "quran_loc": row.get("quran_loc"),
        "wbw_loc": row.get("wbw_loc"),
        "surface": row.get("surface"),
        "current_gloss": row.get("current_gloss"),
        "classification": row.get("classification"),
        "detected_issue": row.get("detected_issue"),
        "evidence_summary": row.get("evidence_summary"),
        "procedure_or_rule": row.get("procedure_or_rule"),
        "recommended_next_action": row.get("recommended_next_action"),
        "public_boundary_status": row.get("public_boundary_status"),
        "confidence": row.get("confidence"),
        "requires_two_vote": row.get("requires_two_vote"),
        "may_apply_live": row.get("may_apply_live"),
    }


def load_lane_rows(paths):
    rows = []
    for path in paths:
        result = lane_validator.validate_file(path, expect_min_rows=1)
        if result["errors"]:
            raise SystemExit("subagent lane validation failed for %s:\n- %s" % (path, "\n- ".join(result["errors"][:20])))
        for _line_no, row in read_jsonl(path):
            rows.append(normalize_lane_row(path, row))
    return rows


def primary_class(classes):
    return sorted(classes, key=lambda item: CLASS_PRIORITY.get(item, 500))[0]


def required_review_lanes(findings):
    out = []
    for finding in findings:
        mapped = LANE_TO_REVIEW.get(finding["lane"], "manual_review")
        if mapped not in out:
            out.append(mapped)
    return out


def issue_family(text):
    lower = str(text or "").lower()
    found = []
    for needle, family in ISSUE_FAMILIES.items():
        if needle in lower and family not in found:
            found.append(family)
    if found:
        return found
    slug = re.sub(r"[^a-z0-9]+", "_", lower).strip("_")
    return [slug[:80] or "unspecified_issue"]


def risk_level(primary_class, findings):
    if primary_class == "known_defect":
        return "critical"
    if primary_class in {"token_only_override", "needs_sarf_review", "needs_nahw_review"}:
        return "high"
    if primary_class in {"needs_renderer_segments", "pending/blocker", "string_correct_but_not_rich"}:
        return "medium"
    if any(row.get("requires_two_vote") for row in findings):
        return "medium"
    return "review"


def packet_for(wbw_loc, findings):
    quran_locs = sorted({row["quran_loc"] for row in findings}, key=loc_sort_key)
    surfaces = sorted({row["surface"] for row in findings if row.get("surface")})
    glosses = sorted({row["current_gloss"] for row in findings if row.get("current_gloss")})
    classes = [row["classification"] for row in findings]
    issue_counts = Counter(row["detected_issue"] for row in findings)
    primary = primary_class(set(classes))
    procedure_counts = Counter(row["procedure_or_rule"] for row in findings)
    families = Counter()
    for row in findings:
        for family in issue_family(row.get("detected_issue")):
            families[family] += 1
    return {
        "id": packet_id(wbw_loc),
        "audit_scope": "full_corpus_dogfood_subagent_lane_packet",
        "allowed_next_step": "review_only",
        "may_apply_live": False,
        "target": {
            "quran_locs": quran_locs,
            "wbw_loc": wbw_loc,
            "surface": surfaces[0] if surfaces else None,
            "current_gloss": glosses[0] if glosses else None,
        },
        "primary_classification": primary,
        "risk": risk_level(primary, findings),
        "classifications": dict(sorted(Counter(classes).items())),
        "issue_families": [
            {"issue_family": family, "count": count}
            for family, count in families.most_common(8)
        ],
        "procedure_gaps": [
            {"procedure_or_rule": procedure, "count": count}
            for procedure, count in procedure_counts.most_common(8)
        ],
        "required_review_lanes": required_review_lanes(findings),
        "requires_two_vote": any(bool(row["requires_two_vote"]) for row in findings),
        "top_detected_issues": [
            {"detected_issue": issue, "count": count}
            for issue, count in issue_counts.most_common(8)
        ],
        "lane_findings": sorted(findings, key=lambda row: (row["lane"], row["classification"], row["detected_issue"])),
        "review_contract": {
            "identity": "exact wbw:S:A:W and quran:S:A:W only",
            "raw_surface_identity_allowed": False,
            "parse_key_primary_identity": False,
            "review_must_reconcile_all_lane_findings": True,
            "public_boundary": "src=qamus, kind=authored, lang=en; no external provenance",
        },
        "recommended_next_action": "route bounded packet to required review lanes; no live apply without owner-gated plan",
        "apply_policy": APPLY_POLICY,
    }


def build_packets(lane_rows, include_class=None, include_issue=None, include_review_lane=None, max_rows=None):
    grouped = defaultdict(list)
    wanted = set(include_class or [])
    issue_terms = [str(term).lower() for term in (include_issue or [])]
    review_lanes = set(include_review_lane or [])
    for row in lane_rows:
        if wanted and row.get("classification") not in wanted:
            continue
        if issue_terms:
            haystack = " ".join([
                str(row.get("detected_issue") or ""),
                str(row.get("evidence_summary") or ""),
                str(row.get("procedure_or_rule") or ""),
            ]).lower()
            if not any(term in haystack for term in issue_terms):
                continue
        if review_lanes and LANE_TO_REVIEW.get(row.get("lane"), "manual_review") not in review_lanes:
            continue
        grouped[row["wbw_loc"]].append(row)
    packets = [packet_for(wbw, rows) for wbw, rows in grouped.items()]
    packets.sort(key=lambda row: (CLASS_PRIORITY.get(row["primary_classification"], 500), loc_sort_key(row["target"]["quran_locs"][0])))
    if max_rows is not None:
        packets = packets[:max_rows]
    return packets


def validate_packets(rows):
    errors = []
    if not rows:
        errors.append("zero lane packets")
        return errors
    seen = set()
    for idx, row in enumerate(rows, 1):
        if row.get("id") in seen:
            errors.append("row %d duplicate id %r" % (idx, row.get("id")))
        seen.add(row.get("id"))
        if row.get("audit_scope") != "full_corpus_dogfood_subagent_lane_packet":
            errors.append("row %d bad audit_scope" % idx)
        if row.get("allowed_next_step") != "review_only":
            errors.append("row %d allowed_next_step must be review_only" % idx)
        if row.get("may_apply_live") is not False:
            errors.append("row %d may_apply_live must be false" % idx)
        target = row.get("target") or {}
        if not WBW_RE.match(str(target.get("wbw_loc"))):
            errors.append("row %d bad target.wbw_loc" % idx)
        quran_locs = target.get("quran_locs") or []
        if not quran_locs:
            errors.append("row %d missing quran_locs" % idx)
        for loc in quran_locs:
            if not QURAN_RE.match(str(loc)):
                errors.append("row %d bad quran loc %r" % (idx, loc))
        policy = row.get("apply_policy") or {}
        if policy.get("apply_allowed") is not False or policy.get("live_mutation_allowed") is not False:
            errors.append("row %d apply policy permits mutation" % idx)
        contract = row.get("review_contract") or {}
        if contract.get("raw_surface_identity_allowed") is not False or contract.get("parse_key_primary_identity") is not False:
            errors.append("row %d identity contract is unsafe" % idx)
        if not row.get("required_review_lanes"):
            errors.append("row %d missing required_review_lanes" % idx)
        if not row.get("issue_families"):
            errors.append("row %d missing issue_families" % idx)
        if row.get("risk") not in {"critical", "high", "medium", "review"}:
            errors.append("row %d bad risk level" % idx)
        findings = row.get("lane_findings") or []
        if not findings:
            errors.append("row %d missing lane_findings" % idx)
        for finding in findings:
            if finding.get("may_apply_live") is not False:
                errors.append("row %d lane finding may_apply_live must be false" % idx)
            if finding.get("wbw_loc") != target.get("wbw_loc"):
                errors.append("row %d lane finding target mismatch" % idx)
            if not lane_validator._is_source_clean_boundary(finding.get("public_boundary_status")):
                errors.append("row %d unsafe public boundary in lane finding" % idx)
    return errors


def self_test():
    rows = [
        {
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "surface": "وَالشَّجَرُ",
            "current_gloss": "and + the trees",
            "classification": "needs_renderer_segments",
            "detected_issue": "rich display missing segment breakdown",
            "evidence_summary": "surface has conjunction, article, and host noun",
            "procedure_or_rule": "qamus/procedures/source-triangulation-and-public-boundary.md",
            "recommended_next_action": "route to renderer/rich-hover requirement queue",
            "public_boundary_status": "source_clean:qamus/authored/en",
            "confidence": "high",
            "requires_two_vote": True,
            "may_apply_live": False,
        },
        {
            "quran_loc": "quran:22:18:17",
            "wbw_loc": "wbw:22:18:17",
            "surface": "وَالشَّجَرُ",
            "current_gloss": "and + the trees",
            "classification": "needs_nahw_review",
            "detected_issue": "waw_fa_particle_function_uncertified",
            "evidence_summary": "waw function requires context gate",
            "procedure_or_rule": "nahw/procedures/particle-decision.md",
            "recommended_next_action": "route to nahw function review",
            "public_boundary_status": "clean:qamus/authored/en; no public provenance leak detected",
            "confidence": "medium",
            "requires_two_vote": True,
            "may_apply_live": False,
        },
        {
            "quran_loc": "quran:33:63:1",
            "wbw_loc": "wbw:33:63:1",
            "surface": "يَسْأَلُكَ",
            "current_gloss": "to ask, question",
            "classification": "known_defect",
            "detected_issue": "suffix omitted",
            "evidence_summary": "attached object pronoun is not represented",
            "procedure_or_rule": "sarf/procedures/clitic-and-host-morphology.md",
            "recommended_next_action": "route to production bug repair review",
            "public_boundary_status": "public-clean: src=qamus kind=authored lang=en; no public provenance leak",
            "confidence": "high",
            "requires_two_vote": True,
            "may_apply_live": False,
        },
    ]
    with tempfile.TemporaryDirectory(prefix="dogfood-lane-packets-") as td:
        lane1 = os.path.join(td, "rich-renderer-auditor.jsonl")
        lane2 = os.path.join(td, "nahw-function-auditor.jsonl")
        lane3 = os.path.join(td, "production-bug-detector.jsonl")
        write_jsonl(lane1, [rows[0]])
        write_jsonl(lane2, [rows[1]])
        write_jsonl(lane3, [rows[2]])
        lane_rows = load_lane_rows([lane1, lane2, lane3])
        packets = build_packets(lane_rows)
        errors = validate_packets(packets)
        if errors:
            raise SystemExit("packet self-test validation failed: %s" % errors)
        if len(packets) != 2:
            raise SystemExit("expected 2 packets, got %d" % len(packets))
        if packets[0]["target"]["wbw_loc"] != "wbw:33:63:1":
            raise SystemExit("known defect should sort first")
        if set(packets[1]["required_review_lanes"]) != {"nahw_function_review", "rich_renderer_review"}:
            raise SystemExit("merged packet did not preserve both review lanes")
        if packets[1]["risk"] != "high":
            raise SystemExit("needs_nahw_review packet should be high risk")
        bad = dict(packets[0])
        bad["may_apply_live"] = True
        if not validate_packets([bad]):
            raise SystemExit("unsafe packet unexpectedly passed")
    print("PASS - full-corpus dogfood lane-packet builder self-test")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-dir")
    parser.add_argument("--lane-jsonl", action="append")
    parser.add_argument("--include-class", action="append")
    parser.add_argument("--include-issue", action="append", help="Case-insensitive substring filter over issue/evidence/procedure")
    parser.add_argument("--review-lane", action="append", help="Filter by normalized review lane, e.g. sarf_component_review")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--out-jsonl")
    parser.add_argument("--validate-jsonl", help="Validate an already-built lane packet JSONL and exit")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.validate_jsonl:
        rows = [row for _line_no, row in read_jsonl(args.validate_jsonl)]
        errors = validate_packets(rows)
        if errors:
            raise SystemExit("lane packet validation failed:\n- %s" % "\n- ".join(errors[:40]))
        print(json.dumps({"ok": True, "packets": len(rows), "may_apply_live": False}, ensure_ascii=False, indent=2, sort_keys=True))
        return
    paths = input_paths(args)
    lane_rows = load_lane_rows(paths)
    packets = build_packets(
        lane_rows,
        include_class=args.include_class,
        include_issue=args.include_issue,
        include_review_lane=args.review_lane,
        max_rows=args.max_rows,
    )
    errors = validate_packets(packets)
    if errors:
        raise SystemExit("lane packet validation failed:\n- %s" % "\n- ".join(errors[:40]))
    if args.out_jsonl:
        write_jsonl(args.out_jsonl, packets)
    else:
        for packet in packets:
            print(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    summary = {
        "ok": True,
        "packets": len(packets),
        "lane_rows": len(lane_rows),
        "classifications": dict(sorted(Counter(packet["primary_classification"] for packet in packets).items())),
        "may_apply_live": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
