#!/usr/bin/env python3
"""Red-first certification-consumer tests for the curriculum corpus pilot.

The pilot is a downstream consumer of the authoritative typed-fact store.  It
must reject an invalid trail and must observe the store's real revocation
semantics without inventing a second state machine.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_curriculum_corpus_pilot as pilot  # noqa: E402
from certify_typed_fact import TypedFactCertificationStore  # noqa: E402


SOURCE_STORE = (
    ROOT / "qamus" / "examples" / "p007-li-pilot" / "certification"
)
TARGET_A = "quran:2:34:5"
TARGET_B = "quran:61:5:4"
TARGET_A_FACT = "fact:p00slice:2_34_5:seg"


def _copy_store(root: Path) -> Path:
    target = root / "certification"
    shutil.copytree(SOURCE_STORE, target)
    return target


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_authoritative_revoke_is_targeted() -> None:
    with tempfile.TemporaryDirectory() as td:
        store_dir = _copy_store(Path(td))
        store = TypedFactCertificationStore(store_dir)
        store.revoke(
            TARGET_A_FACT,
            actor="test:curriculum-corpus-pilot",
            timestamp="2026-08-02T00:00:00Z",
            reason="targeted downstream invalidation canary",
        )
        envelopes = pilot.build(certification_dir=store_dir)
        _assert(envelopes[TARGET_A].get("withheld") is True,
                "revoked target remained learner-visible")
        _assert(envelopes[TARGET_B].get("withheld") is False,
                "unrelated occurrence was incorrectly withheld")
        state = (envelopes[TARGET_A].get("blocking_dependencies") or {}).get(
            TARGET_A_FACT, {})
        _assert(state.get("effective_status") == "review_required",
                "builder did not consume authoritative revoke status")


def test_illegal_transition_invalidates_the_trail() -> None:
    with tempfile.TemporaryDirectory() as td:
        store_dir = _copy_store(Path(td))
        store = TypedFactCertificationStore(store_dir)
        # A hash-valid but illegal certified -> certified transition must be
        # rejected by validate_trail(), not accepted by last-event-wins.
        store._append_event({  # noqa: SLF001 - deliberate adversarial fixture
            "event_type": "transition",
            "fact_id": TARGET_A_FACT,
            "from_status": "certified",
            "to_status": "certified",
            "actor": "test:curriculum-corpus-pilot",
            "timestamp": "2026-08-02T00:00:00Z",
            "reason": "illegal transition canary",
            "evidence_bundle_ref": None,
        })
        envelopes = pilot.build(certification_dir=store_dir)
        _assert(all(e.get("withheld") for e in envelopes.values()),
                "invalid transition trail did not fail closed")
        _assert(all(
            e.get("certification_dependency", {}).get("trail_valid") is False
            for e in envelopes.values()
        ), "invalid transition trail was presented as valid")


def test_broken_hash_chain_invalidates_the_trail() -> None:
    with tempfile.TemporaryDirectory() as td:
        store_dir = _copy_store(Path(td))
        events_path = store_dir / "events.jsonl"
        rows = events_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(rows[0])
        first["actor"] = "test:tampered-actor"
        rows[0] = json.dumps(first, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"))
        events_path.write_text("\n".join(rows) + "\n", encoding="utf-8",
                               newline="\n")
        envelopes = pilot.build(certification_dir=store_dir)
        _assert(all(e.get("withheld") for e in envelopes.values()),
                "broken hash chain did not fail closed")
        errors = next(iter(envelopes.values()))[
            "certification_dependency"]["trail_errors"]
        _assert(any("hash chain broken" in error for error in errors),
                "broken-chain reason was not preserved")


def test_unrelated_valid_event_isolation() -> None:
    with tempfile.TemporaryDirectory() as td:
        store_dir = _copy_store(Path(td))
        before = pilot.build(certification_dir=store_dir)
        store = TypedFactCertificationStore(store_dir)
        unrelated = next(
            fact_id for fact_id, status in store.status_by_id().items()
            if status == "certified"
            and fact_id not in {
                dep
                for envelope in before.values()
                for dep in envelope["certification_dependency"][
                    "depends_on_fact_ids"]
            }
        )
        store.revoke(
            unrelated,
            actor="test:curriculum-corpus-pilot",
            timestamp="2026-08-02T00:00:00Z",
            reason="unrelated-event isolation canary",
        )
        after = pilot.build(certification_dir=store_dir)
        _assert(all(not e.get("withheld") for e in after.values()),
                "unrelated revocation changed pilot availability")
        for target in pilot.TARGETS:
            _assert(
                before[target]["certification_dependency"]["effective_states"]
                == after[target]["certification_dependency"]["effective_states"],
                "unrelated event changed a pilot dependency state",
            )


def main() -> int:
    tests = [
        test_authoritative_revoke_is_targeted,
        test_illegal_transition_invalidates_the_trail,
        test_broken_hash_chain_invalidates_the_trail,
        test_unrelated_valid_event_isolation,
    ]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures.append((test.__name__, exc))
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    if failures:
        print("%d CURRICULUM CERTIFICATION TEST(S) FAILED" % len(failures))
        return 1
    print("CURRICULUM CERTIFICATION TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
