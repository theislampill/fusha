#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a source-only Phase 4 owner authorization request.

The request bundles an apply-readiness manifest and a draft token-decision
ledger for owner review. It does not authorize apply, write live Qamus data,
rebuild WBW artifacts, restart services, sync mirrors, or claim hover closure.
"""
import argparse
import hashlib
import io
import json
import os


REQUIRED_BEFORE_LIVE_APPLY = (
    "owner explicitly authorizes exact request id and artifact hashes",
    "append-only token-decision ledger target is identified",
    "rollback backup or append-only revert path is identified",
    "WBW rebuild command and output path are owner-approved",
    "token-decision and public-boundary validators pass",
    "service health check passes after rebuild",
    "targeted public readback proves intended hovers",
    "public boundary scan reports zero leaks",
    "mirror mismatch is either reconciled or explicitly excluded from this apply",
)

FORBIDDEN_PUBLIC_LABELS = (
    "informed_by",
    "mcp",
    "qac",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
)


def read_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path, row):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(row, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def leak_labels(row):
    text = json.dumps(row, ensure_ascii=False).lower()
    return [label for label in FORBIDDEN_PUBLIC_LABELS if label in text]


def draft_summary(draft_ledger_jsonl):
    rows = list(iter_jsonl(draft_ledger_jsonl))
    return {
        "rows": rows,
        "row_count": len(rows),
        "decision_ids": [row.get("id") for row in rows if row.get("id")],
        "quran_locs": [((row.get("identity") or {}).get("quran_loc")) for row in rows if (row.get("identity") or {}).get("quran_loc")],
        "wbw_locs": [((row.get("identity") or {}).get("wbw_loc")) for row in rows if (row.get("identity") or {}).get("wbw_loc")],
    }


def sample_decision_rows(rows):
    samples = []
    for row in rows[:8]:
        samples.append({
            "id": row.get("id"),
            "identity": row.get("identity") or {},
            "token_decision": row.get("token_decision") or {},
            "safe_scope": row.get("safe_scope") or "unknown",
        })
    return samples


def authorization_requirements(request_id, manifest_json, manifest_sha, manifest, draft_ledger_jsonl, draft_sha, summary, has_exclusions):
    owner_statement = (
        "Authorize %s for listed draft token-decision rows only; "
        "apply_readiness_manifest sha256=%s; draft_token_decision_ledger sha256=%s"
    ) % (request_id, manifest_sha, draft_sha)
    if has_exclusions:
        owner_statement += "; excluded tranche rows remain blocked"
    return {
        "required_owner_statement": owner_statement,
        "must_reference_request_id": request_id,
        "must_reference_artifacts": [
            {
                "name": "apply_readiness_manifest",
                "artifact": os.path.basename(manifest_json),
                "sha256": manifest_sha,
                "id": manifest.get("id"),
            },
            {
                "name": "draft_token_decision_ledger",
                "artifact": os.path.basename(draft_ledger_jsonl),
                "sha256": draft_sha,
                "row_count": summary["row_count"],
            },
        ],
        "must_state_live_apply_scope": "listed_draft_token_decision_rows_only",
        "excluded_rows_remain_blocked": bool(has_exclusions),
    }


def build_request(manifest_json, draft_ledger_jsonl, out_json):
    manifest = read_json(manifest_json)
    summary = draft_summary(draft_ledger_jsonl)
    manifest_sha = sha256_file(manifest_json)
    draft_sha = sha256_file(draft_ledger_jsonl)
    if manifest.get("status") != "pre_apply_not_authorized":
        raise ValueError("apply-readiness manifest must be pre_apply_not_authorized")
    if not summary["rows"]:
        raise ValueError("draft token-decision ledger must contain at least one row")
    request_hash = hashlib.sha256((manifest_sha + draft_sha).encode("ascii")).hexdigest()
    request_id = "phase4-owner-authorization-request:%s" % request_hash[:16]
    request = {
        "id": request_id,
        "phase": "phase4_owner_authorization_request",
        "status": "owner_review_required_not_authorized",
        "generated_by": "tools/build_phase4_owner_authorization_request.py",
        "source_artifacts": {
            "apply_readiness_manifest": {
                "artifact": os.path.basename(manifest_json),
                "sha256": manifest_sha,
                "id": manifest.get("id"),
                "status": manifest.get("status"),
            },
            "draft_token_decision_ledger": {
                "artifact": os.path.basename(draft_ledger_jsonl),
                "sha256": draft_sha,
                "row_count": summary["row_count"],
                "decision_id_count": len(set(summary["decision_ids"])),
                "quran_loc_count": len(set(summary["quran_locs"])),
                "wbw_loc_count": len(set(summary["wbw_locs"])),
            },
        },
        "authorization_requirements": authorization_requirements(
            request_id,
            manifest_json,
            manifest_sha,
            manifest,
            draft_ledger_jsonl,
            draft_sha,
            summary,
            bool(manifest.get("excluded_tranche_rows")),
        ),
        "owner_authorization": {
            "required": True,
            "status": "not_provided",
            "authorized_by": None,
            "authorized_at": None,
            "authorized_scope": "none",
        },
        "apply_policy": {
            "source_only": True,
            "owner_authorization_required": True,
            "apply_allowed": False,
            "live_mutation_allowed": False,
            "wbw_rebuild_allowed": False,
            "service_restart_allowed": False,
            "mirror_sync_allowed": False,
            "closure_claim_allowed": False,
        },
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_source_names_public": False,
            "internal_provenance_public": False,
        },
        "required_before_live_apply": list(REQUIRED_BEFORE_LIVE_APPLY),
        "sample_decisions": sample_decision_rows(summary["rows"]),
    }
    if manifest.get("excluded_tranche_rows"):
        request["excluded_tranche_rows"] = manifest["excluded_tranche_rows"]
    leaks = leak_labels(request)
    if leaks:
        raise ValueError("request contains forbidden public/private label %r" % leaks[0])
    write_json(out_json, request)
    return request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-json", required=True)
    parser.add_argument("--draft-ledger-jsonl", required=True)
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()
    request = build_request(args.manifest_json, args.draft_ledger_jsonl, args.out_json)
    print(json.dumps({
        "request": args.out_json,
        "id": request["id"],
        "draft_rows": request["source_artifacts"]["draft_token_decision_ledger"]["row_count"],
        "status": request["status"],
        "apply_allowed": request["apply_policy"]["apply_allowed"],
        "live_mutation_allowed": request["apply_policy"]["live_mutation_allowed"],
    }, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS — Phase 4 owner authorization request built for review only")


if __name__ == "__main__":
    main()
