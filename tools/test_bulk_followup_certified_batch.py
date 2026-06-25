#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for follow-up review conversion into certified hover decisions."""
import json
import tempfile
from pathlib import Path

import build_bulk_followup_certified_batch as B


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def request_row(loc):
    return {
        "loc": loc,
        "surface_ar": "يَتَّبِعُونَ",
        "key": "يتبعون",
        "qac": {"root": "تبع", "pos": "V"},
        "qamus_entry_candidate": {"id": "5d89e690256d", "headword": "ٱتَّبَعَ"},
        "suggested_lane": "form_variant",
        "risk": "medium",
    }


def review_row(loc, decision="approve", gloss="they follow"):
    return {
        "loc": loc,
        "decision": decision,
        "concise_authored_gloss": gloss,
        "reason_key": "compatible_synonym_normalized",
        "evidence_note": "The verb form and context support the selected gloss.",
        "selected_from": "merged",
        "confidence": "high",
        "agrees_with_nahw": True,
    }


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        requests = root / "requests.jsonl"
        reviews = root / "reviews.jsonl"
        out = root / "certified.jsonl"
        prov = root / "certified.provenance.jsonl"
        unresolved = root / "unresolved.jsonl"
        summary = root / "summary.json"
        write_jsonl(requests, [request_row("7:157:2"), request_row("7:158:2")])
        pending = review_row("7:158:2", decision="pending", gloss="")
        pending["reason_key"] = "still_polysemous"
        write_jsonl(reviews, [review_row("7:157:2"), pending])

        result = B.build_batch(
            str(requests),
            str(reviews),
            str(out),
            str(prov),
            str(unresolved),
            str(summary),
            batch_label="selftest",
            review_lens="arbiter",
            decision_state="bulk_followup_selftest",
        )
        assert result["certified_rows"] == 1, result
        assert result["unresolved_rows"] == 1, result
        public = read_jsonl(out)
        assert public == [{
            "decision_state": "bulk_followup_selftest",
            "gloss": "they follow",
            "key": "يتبعون",
            "kind": "authored",
            "lang": "en",
            "loc": "7:157:2",
            "src": "qamus",
            "state_id": "state:tok:7:157:2",
            "surface": "يَتَّبِعُونَ",
        }]
        provenance = read_jsonl(prov)
        assert provenance[0]["gate"] == "followup_review_required"
        assert provenance[0]["review_lens"] == "arbiter"
        assert provenance[0]["votes"] == 3

        bad = review_row("7:157:2", gloss="QAC says follow")
        errors = B.validate_review(bad, {"7:157:2": request_row("7:157:2")})
        assert any("public gloss leaks" in e for e in errors), errors

        disagrees = review_row("7:157:2")
        disagrees["agrees_with_nahw"] = False
        errors = B.validate_review(disagrees, {"7:157:2": request_row("7:157:2")}, True)
        assert any("must explicitly agree" in e for e in errors), errors

    print("bulk follow-up certified batch self-test OK")


if __name__ == "__main__":
    main()
