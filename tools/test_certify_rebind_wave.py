#!/usr/bin/env python3
"""Focused regression tests for the T11 rebind certification writer."""

from __future__ import annotations

import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import certify_rebind_wave as cert  # noqa: E402
from tools import fact_ledger  # noqa: E402


SOURCE_DIR = cert.resolve_source_dir()


def main() -> int:
    data = cert.validate_inputs(SOURCE_DIR)
    assert len(data["packets"]) == 1_248
    assert len(data["certified_packet_ids"]) == 1_173
    assert len(data["disagreements"]) == 75
    assert Counter(row["verdict"] for row in data["audit"].values()) == Counter({
        "ownership_supported": 1_153,
        "ownership_suspect": 7,
        "underivable": 7,
        "not_applicable": 6,
    })
    canonical_data = cert.validate_inputs(cert.QUEUE_DIR)
    assert canonical_data["certified_packet_ids"] == data["certified_packet_ids"]

    with tempfile.TemporaryDirectory(prefix="test-rebind-cert-") as temp:
        bundle = cert.build_bundle(SOURCE_DIR, Path(temp) / "bundle")
        ledger_dir = Path(temp) / "ledger-readback"
        ledger_dir.mkdir()
        shutil.copyfile(bundle["ledger"], ledger_dir / fact_ledger.LEDGER_NAME)
        store = fact_ledger.FactLedgerStore(ledger_dir)
        assert store.validate_all() == []

        history = store.query(current_only=False)
        current = store.query(current_only=True)
        assert len(history) == 3_669
        assert Counter(row["certification_state"] for row in history) == Counter({
            "candidate": 1_248,
            "review_required": 1_248,
            "certified": 1_173,
        })
        assert Counter(row["certification_state"] for row in current) == Counter({
            "certified": 1_173,
            "review_required": 75,
        })
        assert sum(bool(row["exceptions"]) for row in current) == 14
        assert Counter(
            row["exceptions"][0]["disposition"]
            for row in current if row["exceptions"]
        ) == Counter({
            "benign_rootless_convention": 7,
            "documented_underivable_particle": 7,
        })
        assert all(row["certification_state"] != "materialized" for row in current)
        assert all(row["materialization_targets"] == [] for row in current)
        assert all(
            {vote["voter_id"] for vote in row["review_votes"]}
            == {"reviewer-A:Opus", "reviewer-B:Codex"}
            for row in current
        )

    print("certify_rebind_wave tests OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
