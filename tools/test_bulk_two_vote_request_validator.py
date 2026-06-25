#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for bulk two-vote request packet validation."""
import json
import os
import tempfile
from pathlib import Path

import validate_bulk_two_vote_requests as V


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def table_row(loc="7:157:2"):
    return {
        "loc": loc,
        "surface_ar": "يَتَّبِعُونَ",
        "strict_nk": "يتبعون",
        "nk": "يتبعون",
        "qac_root": "تبع",
        "qac_pos": "V",
        "qamus_entry_candidate": "5d89e690256d",
        "qamus_entry_headword": "ٱتَّبَعَ",
        "qamus_entry_match_type": "root_match",
        "pos_agreement": "agree",
        "suggested_lane": "form_variant",
        "risk": "medium",
        "gate": "two_vote",
        "public_payload_allowed": "yes",
        "blocker_if_not_resolved": "missing_form_variant_on_existing_entry: requires form_variant with two_vote gate",
    }


def request_row(loc="7:157:2"):
    return {
        "loc": loc,
        "surface_ar": "يَتَّبِعُونَ",
        "key": "يتبعون",
        "ayah_context": "ٱلَّذِينَ يَتَّبِعُونَ ٱلرَّسُولَ",
        "qac": {"root": "تبع", "pos": "V"},
        "qamus_entry_candidate": {
            "id": "5d89e690256d",
            "headword": "ٱتَّبَعَ",
            "match_type": "root_match",
            "pos_agreement": "agree",
        },
        "suggested_lane": "form_variant",
        "gate": "two_vote",
        "risk": "medium",
        "sarf_procedure": "procedures/verb-form.md",
        "nahw_procedure": None,
        "known_blocker": "missing_form_variant_on_existing_entry: requires form_variant with two_vote gate",
        "vote_lenses": ["sarf-primary", "nahw-primary"],
        "requested_output": {
            "decision": "approve | reject | pending",
            "concise_authored_gloss": "",
            "sarf_reasoning": "",
            "nahw_reasoning": "",
            "reason_agreement_key": "",
            "blocker_if_rejected": "",
        },
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
    }


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        table = root / "table.jsonl"
        requests = root / "requests.jsonl"
        write_jsonl(table, [table_row()])
        write_jsonl(requests, [request_row()])
        assert V.validate_files(str(requests), table_path=str(table)) == []

        chunks_dir = root / "requests_chunks"
        chunks_dir.mkdir()
        chunk = chunks_dir / "chunk_001.jsonl"
        write_jsonl(chunk, [request_row()])
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "rows": 1,
            "source_table": os.path.relpath(str(table), V.ROOT),
            "source_table_sha256": V.sha256_file(str(table)),
            "request_file": os.path.relpath(str(requests), V.ROOT),
            "request_file_sha256": V.sha256_file(str(requests)),
            "chunks": [os.path.relpath(str(chunk), V.ROOT)],
            "chunk_sha256": {os.path.relpath(str(chunk), V.ROOT): V.sha256_file(str(chunk))},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        assert V.validate_files(
            str(requests), table_path=str(table), manifest_path=str(manifest),
            require_checksums=True
        ) == []

        stale_manifest = json.loads(manifest.read_text(encoding="utf-8"))
        stale_manifest["request_file_sha256"] = "0" * 64
        manifest.write_text(json.dumps(stale_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        assert any("request_file_sha256" in e for e in V.validate_files(
            str(requests), table_path=str(table), manifest_path=str(manifest),
            require_checksums=True
        ))

        legacy_manifest = {
            "rows": 1,
            "source_table": os.path.relpath(str(table), V.ROOT),
            "request_file": os.path.relpath(str(requests), V.ROOT),
            "chunks": [],
        }
        manifest.write_text(json.dumps(legacy_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        assert V.validate_files(str(requests), table_path=str(table), manifest_path=str(manifest)) == []
        assert any("missing source_table_sha256" in e for e in V.validate_files(
            str(requests), table_path=str(table), manifest_path=str(manifest),
            require_checksums=True
        ))

        bad_gate = request_row()
        bad_gate["gate"] = "auto_rule"
        write_jsonl(requests, [bad_gate])
        assert any("gate must be two_vote" in e for e in V.validate_files(str(requests), table_path=str(table)))

        bad_boundary = request_row()
        bad_boundary["public_boundary"]["external_source_names_public_allowed"] = True
        write_jsonl(requests, [bad_boundary])
        assert any("external source names" in e for e in V.validate_files(str(requests), table_path=str(table)))

        legacy_boundary = request_row()
        del legacy_boundary["public_boundary"]["lang"]
        write_jsonl(requests, [legacy_boundary])
        assert V.validate_files(str(requests), table_path=str(table)) == []
        assert any("public_boundary.lang must be en" in e
                   for e in V.validate_files(str(requests), table_path=str(table), require_lang_en=True))

        bad_lang = request_row()
        bad_lang["public_boundary"]["lang"] = "ar"
        write_jsonl(requests, [bad_lang])
        assert any("public_boundary.lang must be en" in e
                   for e in V.validate_files(str(requests), table_path=str(table)))

        bad_parity = request_row()
        bad_parity["qac"]["pos"] = "N"
        write_jsonl(requests, [bad_parity])
        assert any("qac parity" in e for e in V.validate_files(str(requests), table_path=str(table)))

    print("bulk two-vote request validator self-test OK")


if __name__ == "__main__":
    main()
