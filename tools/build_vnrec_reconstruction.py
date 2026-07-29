#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the LOST VNREC artifacts as clearly-marked reconstructions.

Per SERVER-CORPORA-CUSTODY-PLAN-2026-07-29 (P0 discrepancy + Fable addendum):
``vnrec-authoritative-membership.json`` and ``vnrec-conflicts.jsonl`` — cited
by ``impl-records/VNREC-RECONCILIATION-2026-07-17.md`` and the VN readiness v2
program — exist nowhere (never persisted or already lost).  This generator
rebuilds what IS deterministically recoverable from committed repo inputs:

* membership — from ``tools/build_vn_readiness_v2.py`` ``PLAN_WINDOWS`` +
  ``FROZEN_SCOPE_TEXT`` (the ratified CLOSED-FROZEN VN-00/01/02 window
  contracts) joined against the 2,092 committed entry source keys;
* conflicts (PARTIAL) — the claim-divergence rows still preserved in
  ``vn-ledger.jsonl`` (every row carries ``vn_tranche = null`` plus the
  balanced-partition ``proposal_vn_tranche`` claim, which diverges from the
  documented/plan window for the same source key).

Both outputs are stamped ``"reconstruction": true, "original_lost": true``.
They are NOT the originals: the original conflicts file's 164 staging-history
dual-claim rows depended on the rollout staging snapshots, which are not repo
artifacts — that family is recorded here as unrecoverable, count 0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.build_vn_readiness_v2 import (  # noqa: E402
    FROZEN_LABELS,
    FROZEN_SCOPE_TEXT,
    PLAN_WINDOWS,
)

RECONSTRUCTION_STAMP = {
    "reconstruction": True,
    "original_lost": True,
    "reconstruction_date": "2026-07-28",
    "reconstruction_note": (
        "Rebuilt from committed repo inputs after the originals were found missing "
        "on every surveyed host (SERVER-CORPORA-CUSTODY-PLAN-2026-07-29 §1 Area 2 "
        "discrepancy + addendum). NOT the original artifact; never cite it as such."
    ),
}

# The ratified CLOSED-FROZEN windows, as numeric ranges (mirrors FROZEN_SCOPE_TEXT).
FROZEN_WINDOWS = {
    "VN-00": {"v": (1, 47), "n": (1, 45)},
    "VN-01": {"v": (48, 94), "n": (46, 90)},
    "VN-02": {"v": (95, 141), "n": (91, 135)},
}

_SOURCE_KEY_RE = re.compile(r"^([vnp])0*(\d+)$", re.IGNORECASE)


def _identity(source_key):
    match = _SOURCE_KEY_RE.fullmatch(str(source_key or "").strip())
    if not match:
        return None
    return match.group(1).lower(), int(match.group(2))


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _window_label(identity):
    prefix, number = identity
    if prefix == "p":
        return "unplanned_particles"
    for label, window in FROZEN_WINDOWS.items():
        bounds = window.get(prefix)
        if bounds and bounds[0] <= number <= bounds[1]:
            return label
    for label, window in PLAN_WINDOWS.items():
        bounds = window.get(prefix)
        if bounds and bounds[0] <= number <= bounds[1]:
            return label
    return "unassigned"


def _range_keys(prefix, bounds, present):
    width = 4 if prefix == "n" else 3
    keys = []
    for number in range(bounds[0], bounds[1] + 1):
        if (prefix, number) in present:
            keys.append(f"{prefix}{number:0{width}d}")
    return keys


def build_membership(entries):
    present = {}
    for entry in entries:
        for source_key in entry.get("source_keys") or []:
            identity = _identity(source_key)
            if identity is not None:
                present[identity] = str(entry.get("id"))
    vn = {}
    for label in FROZEN_LABELS:
        window = FROZEN_WINDOWS[label]
        keys = sorted(
            _range_keys("v", window["v"], present) + _range_keys("n", window["n"], present)
        )
        vn[label] = {
            "historical_status": "reconstructed_closed_frozen_window_contract",
            "authoritative_sets": [{
                "set_id": f"reconstructed-{label.lower()}-window",
                "kind": "documented_window_contract",
                "source_keys": keys,
                "count": len(keys),
                "evidence": [
                    {
                        "artifact": "tools/build_vn_readiness_v2.py",
                        "locator": f"FROZEN_SCOPE_TEXT[{label!r}] = {FROZEN_SCOPE_TEXT[label]!r}",
                        "claim": "ratified CLOSED-FROZEN window contract (in-repo mirror)",
                    },
                    {
                        "artifact": "impl-records/VNREC-RECONCILIATION-2026-07-17.md",
                        "locator": "Recovered authoritative scope (private custody; not in this repo)",
                        "claim": "original recorded contract — cited, not reproduced",
                    },
                ],
            }],
        }
    for label in sorted(PLAN_WINDOWS):
        window = PLAN_WINDOWS[label]
        parts = []
        count = 0
        for prefix in ("v", "n"):
            bounds = window.get(prefix)
            if bounds:
                keys = _range_keys(prefix, bounds, present)
                count += len(keys)
                width = 4 if prefix == "n" else 3
                parts.append(f"{prefix}{bounds[0]:0{width}d}–{prefix}{bounds[1]:0{width}d}")
        vn[label] = {
            "historical_status": "planning_baseline_window",
            "authoritative_sets": [],
            "future_definition_only": {
                "source_key_range": " + ".join(parts),
                "count": count,
                "status_note": window.get("status_note", ""),
            },
        }
    membership = {
        "schema": "vnrec-authoritative-membership@1",
        **RECONSTRUCTION_STAMP,
        "read_only_recovery": True,
        "reconstructed_from": [
            "tools/build_vn_readiness_v2.py::PLAN_WINDOWS + FROZEN_SCOPE_TEXT",
            "qamus/data/current/entries.jsonl (source_keys)",
        ],
        "corpus": {
            "entries": len(entries),
            "unique_source_key_identities": len(present),
        },
        "staging_metadata": {
            "available": False,
            "note": (
                "vn00 rollout staging snapshots are server-side artifacts, not repo "
                "inputs; the original membership's staging namespace (final_source_key_"
                "count=1302 per v2 evidence strings) is NOT reconstructible here."
            ),
        },
        "vn": vn,
        "candidate_only": True,
    }
    return membership, present


def build_conflicts(ledger_rows):
    """PARTIAL conflicts reconstruction from the preserved ledger claims."""

    proposals = defaultdict(set)
    null_tranche_rows = 0
    for row in ledger_rows:
        source_key = str(row.get("source_key") or "").strip()
        if not source_key:
            continue
        if row.get("vn_tranche") is None:
            null_tranche_rows += 1
        proposal = row.get("proposal_vn_tranche")
        if proposal:
            proposals[source_key].add(proposal)
    conflicts = []
    for source_key in sorted(proposals):
        identity = _identity(source_key)
        if identity is None:
            continue
        window = _window_label(identity)
        claim_set = sorted(proposals[source_key])
        divergent = (
            window not in ("unplanned_particles", "unassigned")
            and set(claim_set) != {window}
        )
        if len(claim_set) > 1 or divergent:
            conflicts.append({
                "schema": "vnrec-conflict-reconstruction@1",
                **{key: RECONSTRUCTION_STAMP[key] for key in ("reconstruction", "original_lost")},
                "source_key": source_key,
                "conflict_kind": (
                    "multi_proposal_claim" if len(claim_set) > 1
                    else "window_vs_balanced_proposal_divergence"
                ),
                "documented_or_plan_window": window,
                "preserved_ledger_claims": claim_set,
                "evidence": [
                    f"vn-ledger.jsonl:source_key={source_key}:proposal_vn_tranche",
                    "tools/build_vn_readiness_v2.py:FROZEN_SCOPE_TEXT/PLAN_WINDOWS",
                ],
                "note": (
                    "preserved-claim divergence only; NOT one of the original 164 "
                    "staging-history dual-claim rows (unrecoverable, see meta)"
                ),
            })
    meta = {
        "schema": "vnrec-conflicts-reconstruction.meta@1",
        **RECONSTRUCTION_STAMP,
        "partial": True,
        "reconstructed_from": [
            "vn-ledger.jsonl (7,740 rows; vn_tranche=null throughout, preserved "
            "proposal_vn_tranche claims)",
            "tools/build_vn_readiness_v2.py::PLAN_WINDOWS + FROZEN_SCOPE_TEXT",
        ],
        "null_tranche_rows": null_tranche_rows,
        "rows": len(conflicts),
        "conflict_kind_counts": {
            kind: sum(1 for row in conflicts if row["conflict_kind"] == kind)
            for kind in sorted({row["conflict_kind"] for row in conflicts})
        },
        "original_dual_claim_family": {
            "description": (
                "the original vnrec-conflicts.jsonl recorded 164 dual-claim rows "
                "between documented CLOSED-FROZEN window contracts and the vn00 "
                "rollout staging-history snapshots"
            ),
            "recovered_row_count": 0,
            "recoverable_from_repo": False,
            "reason": "staging snapshots are server-side inputs, absent from this repo",
        },
        "candidate_only": True,
    }
    return conflicts, meta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", default=os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl"))
    parser.add_argument("--ledger", default=os.path.join(ROOT, "vn-ledger.jsonl"))
    parser.add_argument("--output-dir", default=os.path.join(ROOT, "qamus", "reports", "vnrec"))
    args = parser.parse_args(argv)

    entries = _read_jsonl(args.entries)
    ledger_rows = _read_jsonl(args.ledger)
    membership, present = build_membership(entries)
    conflicts, meta = build_conflicts(ledger_rows)

    os.makedirs(args.output_dir, exist_ok=True)
    membership_path = os.path.join(args.output_dir, "vnrec-authoritative-membership.reconstruction.json")
    with open(membership_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(membership, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    conflicts_path = os.path.join(args.output_dir, "vnrec-conflicts.partial-reconstruction.jsonl")
    with open(conflicts_path, "w", encoding="utf-8", newline="\n") as handle:
        for row in conflicts:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    meta_path = os.path.join(args.output_dir, "vnrec-conflicts.partial-reconstruction.meta.json")
    with open(meta_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    summary = {
        "membership_windows": {
            label: membership["vn"][label]["authoritative_sets"][0]["count"]
            for label in FROZEN_LABELS
        },
        "unique_source_key_identities": len(present),
        "conflict_rows": len(conflicts),
        "reconstruction": True,
        "original_lost": True,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
