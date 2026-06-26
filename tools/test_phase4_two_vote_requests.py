#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for Phase 4 exact-addressed two-vote request packets."""
import json
import tempfile
from pathlib import Path

import build_phase4_two_vote_requests as B
import validate_phase4_closure_tranche as T
import validate_phase4_two_vote_requests as V


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def main():
    rows = T.sample_rows()
    with tempfile.TemporaryDirectory(prefix="phase4-two-vote-") as td:
        root = Path(td)
        tranche = root / "tranche.jsonl"
        requests = root / "requests.jsonl"
        write_jsonl(tranche, rows)

        summary = B.build_requests(str(tranche), str(requests))
        assert summary["rows"] == 1, summary
        assert summary["source_tranche_rows"] == 2, summary
        assert summary["component_candidate_rows"] == 1, summary
        assert summary["auto_safe_rows"] == 0, summary
        assert summary["apply_allowed"] is False
        assert summary["live_mutation_allowed"] is False
        assert summary["closure_claim_allowed"] is False

        built = [json.loads(line) for line in requests.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(built) == 1
        req = built[0]
        assert req["phase"] == "phase4_two_vote_request"
        assert req["source_tranche_id"] == "phase4-tranche:queue_parse_c0ffee12"
        assert req["parse_id"] == "parse:c0ffee12"
        assert req["lane"] == "two_vote_required"
        assert req["required_gate"] == "two_vote_required"
        assert req["identity"]["quran_locs"] == ["quran:22:18:17"]
        assert req["identity"]["wbw_locs"] == ["wbw:22:18:17"]
        assert req["candidate_evidence"]["whole_token_candidates"] == []
        assert req["candidate_evidence"]["component_candidates"] == ["qamus:p:waw", "qamus:p:al", "qamus:n:tree"]
        assert req["candidate_evidence"]["component_candidates_can_certify"] is False
        assert req["candidate_evidence"]["component_candidate_joins"][0]["join_status"][0] == "source:rich_wbw_segment"
        assert req["vote_lenses"] == ["sarf-primary", "nahw-primary"]
        assert req["public_boundary"] == {
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        }
        assert req["apply_policy"]["apply_allowed"] is False
        assert req["apply_policy"]["live_mutation_allowed"] is False
        assert req["apply_policy"]["closure_claim_allowed"] is False
        assert "component_candidates" in req["cannot_certify_from"]

        assert V.validate(str(requests)) == (1, [])

        bad = dict(req)
        bad["required_gate"] = "auto_safe_after_preview"
        bad["candidate_evidence"] = dict(req["candidate_evidence"])
        bad["candidate_evidence"]["component_candidates_can_certify"] = True
        write_jsonl(requests, [bad])
        count, errors = V.validate(str(requests))
        assert count == 1
        assert any("required_gate must be two_vote_required" in err for err in errors), errors
        assert any("component_candidates_can_certify must be false" in err for err in errors), errors

    print("Phase 4 two-vote request self-test OK")


if __name__ == "__main__":
    main()
