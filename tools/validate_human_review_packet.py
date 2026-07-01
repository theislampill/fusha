"""Validate owner/scholar review packet shape so ANDONs do not become vague piles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_mode_a import read_json


ALLOWED_ROLES = {"owner", "scholar_irab"}
ALLOWED_DECISIONS = {"accept", "reject", "revise", "defer_with_reason"}


def validate_packet(packet: dict) -> list[str]:
    errors: list[str] = []
    if packet.get("schema") != "qamus/human-review-packet@1":
        errors.append("schema must be qamus/human-review-packet@1")
    if packet.get("reviewer_role") not in ALLOWED_ROLES:
        errors.append("reviewer_role must be owner or scholar_irab")
    rows = packet.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("rows must be a non-empty array")
    elif len(rows) > int(packet.get("max_packet_size", 25)):
        errors.append("rows exceeds max_packet_size")
    for idx, row in enumerate(rows or []):
        for key in ["row_id", "entry_id", "card_id", "surface", "exact_question", "required_evidence", "on_accept", "on_reject"]:
            if not row.get(key):
                errors.append(f"rows[{idx}] missing {key}")
        decisions = row.get("allowed_decisions", [])
        if not set(decisions).issubset(ALLOWED_DECISIONS):
            errors.append(f"rows[{idx}] has unsupported allowed_decisions")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Qamus human review packet.")
    parser.add_argument("path", nargs="?", default="qamus/examples/mode_a_thin_slice/scholar-packet.sample.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    packet = read_json(Path(args.path))
    errors = validate_packet(packet)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "rows": len(packet["rows"])}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
