#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for two-vote reconciliation into certified/unresolved packets."""
import json
import tempfile
from pathlib import Path

import reconcile_bulk_two_vote_results as R


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def request_row(loc, surface="يَتَّبِعُونَ"):
    return {
        "loc": loc,
        "surface_ar": surface,
        "key": "يتبعون",
        "ayah_context": "ٱلَّذِينَ يَتَّبِعُونَ ٱلرَّسُولَ",
        "qac": {"root": "تبع", "pos": "V"},
        "qamus_entry_candidate": {"id": "5d89e690256d", "headword": "ٱتَّبَعَ"},
        "suggested_lane": "form_variant",
        "gate": "two_vote",
        "risk": "medium",
        "vote_lenses": ["sarf-primary", "nahw-primary"],
        "public_boundary": {
            "src": "qamus",
            "kind": "authored",
            "external_text_allowed": False,
            "external_source_names_public_allowed": False,
        },
    }


def vote(loc, lens, gloss="they follow", decision="approve", reason_key="form-viii-follow"):
    return {
        "loc": loc,
        "lens": lens,
        "decision": decision,
        "concise_authored_gloss": gloss,
        "sarf_reasoning": "Form VIII verb; QAC POS agrees with the Qamus candidate.",
        "nahw_reasoning": "Verbal predicate in context; no particle changes the sense here.",
        "reason_agreement_key": reason_key,
        "reviewer_id": "selftest-%s" % lens,
        "blocker_if_rejected": "" if decision == "approve" else "sense still unresolved",
    }


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        requests = root / "requests.jsonl"
        votes = root / "votes.jsonl"
        out = root / "certified.jsonl"
        prov = root / "certified.provenance.jsonl"
        unresolved = root / "unresolved.jsonl"
        summary = root / "summary.json"
        write_jsonl(requests, [
            request_row("7:157:2"),
            request_row("7:158:2"),
            request_row("7:159:2"),
            request_row("7:160:2"),
        ])
        write_jsonl(votes, [
            vote("7:157:2", "sarf-primary"),
            vote("7:157:2", "nahw-primary"),
            vote("7:158:2", "sarf-primary", gloss="they follow"),
            vote("7:158:2", "nahw-primary", gloss="they obey"),
            vote("7:159:2", "sarf-primary"),
            vote("7:160:2", "sarf-primary", decision="pending"),
            vote("7:160:2", "nahw-primary", decision="pending"),
        ])

        result = R.reconcile_files(str(requests), [str(votes)], str(out), str(prov), str(unresolved), str(summary))
        assert result["certified_rows"] == 1, result
        assert result["unresolved_rows"] == 3, result

        public_row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
        assert public_row == {
            "loc": "7:157:2",
            "gloss": "they follow",
            "surface": "يَتَّبِعُونَ",
            "key": "يتبعون",
            "state_id": "state:tok:7:157:2",
            "src": "qamus",
            "kind": "authored",
            "lang": "en",
            "decision_state": "bulk_two_vote_certified",
        }
        prov_row = json.loads(prov.read_text(encoding="utf-8").splitlines()[0])
        assert prov_row["votes"] == 2
        assert prov_row["gate"] == "two_vote_required"
        assert prov_row["reason_agreement_key"] == "form-viii-follow"
        unresolved_rows = [json.loads(line) for line in unresolved.read_text(encoding="utf-8").splitlines()]
        assert {row["unresolved_reason"] for row in unresolved_rows} == {
            "vote_disagreement",
            "missing_vote",
            "both_votes_pending",
        }

        leak = vote("7:157:2", "sarf-primary", gloss="qac says they follow")
        assert any("public gloss leaks" in e for e in R.validate_vote(leak, {"7:157:2": request_row("7:157:2")}))

        write_jsonl(votes, [
            vote("7:157:2", "sarf-primary", reason_key="form-viii-follow"),
            vote("7:157:2", "nahw-primary", reason_key="context-verb-follow"),
            vote("7:158:2", "sarf-primary", gloss="they follow", reason_key="form-viii-follow"),
            vote("7:158:2", "nahw-primary", gloss="they obey", reason_key="context-obey"),
        ])
        result = R.reconcile_files(
            str(requests),
            [str(votes)],
            str(out),
            str(prov),
            str(unresolved),
            str(summary),
            allow_same_gloss_reason_reconcile=True,
        )
        assert result["certified_rows"] == 1, result
        prov_row = json.loads(prov.read_text(encoding="utf-8").splitlines()[0])
        assert prov_row["reconciliation_mode"] == "same_gloss_independent_approval"
        assert prov_row["original_reason_keys"] == {
            "sarf-primary": "form-viii-follow",
            "nahw-primary": "context-verb-follow",
        }

    print("bulk two-vote reconciliation self-test OK")


if __name__ == "__main__":
    main()
