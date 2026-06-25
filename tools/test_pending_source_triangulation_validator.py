#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for the pending-source-triangulation table validator."""
import json
import tempfile
from pathlib import Path

import validate_pending_source_triangulation_table as V


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    good = {
        "loc": "1:2:3",
        "surface_ar": "ٱلْحَمْدُ",
        "nk": "الحمد",
        "strict_nk": "الحمد",
        "blocker": "stem_base_unknown",
        "root_cause": "missing_form_variant_on_existing_entry",
        "qac_root": "حمد",
        "qac_pos": "N",
        "qamus_entry_candidate": "abc123",
        "qamus_entry_match_type": "root_match",
        "qac_evidence": "available",
        "quran_adapter_evidence": "available",
        "pos_agreement": "agree",
        "sarf_procedure": "procedures/noun-plural-gender.md",
        "nahw_procedure": None,
        "suggested_lane": "form_variant",
        "deterministic_resolvable": False,
        "deterministic_reason": "",
        "proposed_gloss": None,
        "risk": "medium",
        "gate": "two_vote",
        "public_payload_allowed": "yes",
        "public_provenance_clean": True,
        "blocker_if_not_resolved": "missing_form_variant_on_existing_entry: needs form_variant 2-vote",
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        table = root / "table.jsonl"
        audit = root / "audit.jsonl"
        write_jsonl(table, [good])
        write_jsonl(audit, [{"quran_loc": "1:2:3", "decision_state": "pending"}])
        assert V.validate_files(str(table), str(audit)) == []

        bad_auto = dict(good)
        bad_auto.update({
            "deterministic_resolvable": True,
            "gate": "auto_rule",
            "suggested_lane": "auto_resolve_deterministic",
            "proposed_gloss": "QAC says praise",
            "pos_agreement": "mismatch",
        })
        write_jsonl(table, [bad_auto])
        errors = V.validate_files(str(table), str(audit))
        assert any("POS mismatch" in e for e in errors), errors
        assert any("external source name" in e for e in errors), errors

        no_qac_auto = dict(good)
        no_qac_auto.update({
            "deterministic_resolvable": True,
            "gate": "auto_rule",
            "suggested_lane": "auto_resolve_deterministic",
            "proposed_gloss": "praise",
            "deterministic_reason": "single sense, POS-agree, no homograph",
            "qac_root": None,
            "qac_evidence": "unavailable",
        })
        write_jsonl(table, [no_qac_auto])
        errors = V.validate_files(str(table), str(audit))
        assert any("lacks available QAC root evidence" in e for e in errors), errors

        construct_auto = dict(good)
        construct_auto.update({
            "deterministic_resolvable": True,
            "gate": "auto_rule",
            "suggested_lane": "auto_resolve_deterministic",
            "strict_nk": "ذات",
            "qamus_entry_headword": "ذُو",
            "proposed_gloss": "the one having",
            "deterministic_reason": "single sense, POS-agree, no homograph",
        })
        write_jsonl(table, [construct_auto])
        errors = V.validate_files(str(table), str(audit))
        assert any("construct row cannot be deterministic" in e for e in errors), errors

        missing = dict(good)
        missing["loc"] = "1:2:4"
        write_jsonl(table, [missing])
        errors = V.validate_files(str(table), str(audit))
        assert any("missing table row" in e for e in errors), errors
        assert any("extra table row" in e for e in errors), errors

    print("pending-source-triangulation validator self-test OK")


if __name__ == "__main__":
    main()
