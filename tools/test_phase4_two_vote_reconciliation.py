#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for exact-addressed Phase 4 two-vote response reconciliation."""
import json
import tempfile
from pathlib import Path

import build_phase4_two_vote_requests as B
import reconcile_phase4_two_vote_responses as R
import validate_phase4_closure_tranche as T
import validate_phase4_two_vote_responses as V


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def response(request, lens, decision="approve", gloss="and + the trees", reason=None):
    if reason is None:
        reason = request.get("agreement_key_hint", "")
    return {
        "id": "%s:%s" % (request["id"].replace("phase4-two-vote:", "phase4-two-vote-response:"), lens),
        "phase": "phase4_two_vote_response",
        "source_request_id": request["id"],
        "parse_id": request["parse_id"],
        "lens": lens,
        "decision": decision,
        "identity": request["identity"],
        "concise_authored_gloss": gloss if decision == "approve" else "",
        "sarf_reasoning": "Visible conjunction/article/host composition is preserved.",
        "nahw_reasoning": "The prefixed waw is a grammar-bearing function piece in context.",
        "reason_agreement_key": reason if decision == "approve" else "",
        "blocker_if_rejected": "" if decision == "approve" else "needs further grammar review",
        "safe_scope_after_vote": "token_only",
        "public_boundary": request["public_boundary"],
        "component_candidates_used_as_certification": False,
    }


def main():
    with tempfile.TemporaryDirectory(prefix="phase4-two-vote-reconcile-") as td:
        root = Path(td)
        tranche = root / "tranche.jsonl"
        requests_path = root / "requests.jsonl"
        responses_path = root / "responses.jsonl"
        certified_path = root / "certified.jsonl"
        unresolved_path = root / "unresolved.jsonl"

        rows = T.sample_rows()
        write_jsonl(tranche, rows)
        B.build_requests(str(tranche), str(requests_path))
        request = [json.loads(line) for line in requests_path.read_text(encoding="utf-8").splitlines()][0]

        responses = [
            response(request, "sarf-primary"),
            response(request, "nahw-primary"),
        ]
        write_jsonl(responses_path, responses)
        assert V.validate(str(responses_path), request_path=str(requests_path)) == (2, [])

        summary = R.reconcile_files(
            str(requests_path),
            str(responses_path),
            str(certified_path),
            str(unresolved_path),
        )
        assert summary["requests"] == 1, summary
        assert summary["responses"] == 2, summary
        assert summary["certified_rows"] == 1, summary
        assert summary["unresolved_rows"] == 0, summary
        certified = [json.loads(line) for line in certified_path.read_text(encoding="utf-8").splitlines()]
        assert certified[0]["phase"] == "phase4_two_vote_reconciled"
        assert certified[0]["source_request_id"] == request["id"]
        assert certified[0]["identity"]["quran_locs"] == ["quran:22:18:17"]
        assert certified[0]["public_hover"] == {
            "gloss": "and + the trees",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
        }
        assert certified[0]["apply_policy"]["apply_allowed"] is False
        assert certified[0]["component_candidates_used_as_certification"] is False

        responses = [
            response(request, "sarf-primary", gloss="and + the trees"),
            response(request, "nahw-primary", gloss="and the trees"),
        ]
        write_jsonl(responses_path, responses)
        count, errors = V.validate(str(responses_path), request_path=str(requests_path))
        assert count == 2
        assert any("approved concise_authored_gloss must match request gloss_style_hint" in err for err in errors), errors

        no_hint_request = dict(request)
        no_hint_request["gloss_style_hint"] = {
            "preferred_concise_authored_gloss": "",
            "required_when_approving": False,
            "style": "none",
            "source": "request_builder_review_contract",
            "certifies_decision": False,
        }
        write_jsonl(requests_path, [no_hint_request])
        responses = [
            response(no_hint_request, "sarf-primary", gloss="and + the trees"),
            response(no_hint_request, "nahw-primary", gloss="and the trees"),
        ]
        write_jsonl(responses_path, responses)
        summary = R.reconcile_files(
            str(requests_path),
            str(responses_path),
            str(certified_path),
            str(unresolved_path),
        )
        assert summary["certified_rows"] == 0, summary
        assert summary["unresolved_rows"] == 1, summary
        unresolved = [json.loads(line) for line in unresolved_path.read_text(encoding="utf-8").splitlines()]
        assert unresolved[0]["unresolved_reason"] == "vote_disagreement"
        assert unresolved[0]["identity"]["wbw_locs"] == ["wbw:22:18:17"]

        write_jsonl(requests_path, [request])
        bad = response(request, "sarf-primary", gloss="QAC says and + the trees")
        write_jsonl(responses_path, [bad])
        count, errors = V.validate(str(responses_path), request_path=str(requests_path))
        assert count == 1
        assert any("public gloss leaks" in err for err in errors), errors

    print("Phase 4 two-vote reconciliation self-test OK")


if __name__ == "__main__":
    main()
