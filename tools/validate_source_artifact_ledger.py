"""Validate the canonical source/artifact ledger used by parser/Qamus work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fusha_mode_a import read_json
from validate_artifact_freshness import validate_freshness


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source-artifact ledger structure.")
    parser.add_argument("--path", default="sources/source-artifact-ledger.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    ledger = read_json(Path(args.path))
    errors = validate_freshness(ledger, args.path)
    if ledger.get("schema") != "fusha/source-artifact-ledger@1":
        errors.append("ledger schema must be fusha/source-artifact-ledger@1")
    artifacts = ledger.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("ledger must contain at least one artifact")
    else:
        seen = set()
        for index, artifact in enumerate(artifacts):
            artifact_id = artifact.get("artifact_id")
            if not artifact_id:
                errors.append(f"artifact[{index}] missing artifact_id")
                continue
            if artifact_id in seen:
                errors.append(f"duplicate artifact_id {artifact_id}")
            seen.add(artifact_id)
            if not artifact.get("path"):
                errors.append(f"artifact {artifact_id} missing path")
            if artifact.get("public_boundary") not in {"source_clean", "internal_only", "not_public"}:
                errors.append(f"artifact {artifact_id} has unsupported public_boundary")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "artifacts": len(artifacts)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
