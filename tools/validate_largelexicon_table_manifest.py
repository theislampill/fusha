#!/usr/bin/env python3
"""Validate largelexicon sharded table manifests, indexes, and the target release.

Two independent gates live here:

* ``validate`` — the sharded @1 qword denominator manifest and its indexes;
* ``validate_target_release`` — the derived target-schema release. It re-validates
  every carried row against the UNCHANGED committed target schema rather than
  trusting the promoter's own accounting, and fails closed on mixed schema
  versions, stale release metadata, validation-red releases, surviving
  row-forbidden constants, and lossless-accounting breaks.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import promote_largelexicon_target_schema as promoter
import validate_largelexicon_rows as rows_validator
from largelexicon_common import (
    FORBIDDEN_PUBLIC_SUBSTRINGS,
    PUBLIC_BOUNDARY,
    match_forbidden_labels,
    public_boundary_errors,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.manifest.json"
ENTRY_INDEX = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.entry-shard-index.json"
SOURCE_REPAIR = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.source-card-repair.json"
LEGACY_MONOLITH = ROOT / "qamus" / "indexes" / "largelexicon" / "qamus-qword-denominator.full.jsonl"
MAX_SHARD_BYTES = 10 * 1024 * 1024
ROW_ID_RE = re.compile(r"^llx-qword-([0-9a-f]{12})-\d{2}-\d{2}-\d{3}$")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line.strip():
                yield line_no, json.loads(line)


def validate(manifest_path: Path = MANIFEST) -> list[str]:
    errors: list[str] = []
    if LEGACY_MONOLITH.exists():
        errors.append(f"{LEGACY_MONOLITH.relative_to(ROOT)} must be replaced by sharded manifest storage")
    if not manifest_path.exists():
        return errors + [f"missing qword denominator manifest: {manifest_path.relative_to(ROOT)}"]
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != "qamus/largelexicon-qword-denominator-manifest@1":
        errors.append("manifest schema mismatch")
    if manifest.get("table_schema") != "qamus/largelexicon-qword-denominator@1":
        errors.append("manifest table_schema mismatch")
    if manifest.get("public_boundary") != PUBLIC_BOUNDARY:
        errors.append("manifest public_boundary mismatch")
    if manifest.get("primary_key") != "row_id":
        errors.append("manifest primary_key must be row_id")
    if manifest.get("entry_index_path") != str(ENTRY_INDEX.relative_to(ROOT)).replace("\\", "/"):
        errors.append("manifest entry_index_path mismatch")
    if manifest.get("source_card_repair_path") != str(SOURCE_REPAIR.relative_to(ROOT)).replace("\\", "/"):
        errors.append("manifest source_card_repair_path mismatch")
    shards = manifest.get("shards") or []
    if not shards:
        errors.append("manifest must list at least one shard")
    if not ENTRY_INDEX.exists():
        errors.append(f"missing entry shard index: {ENTRY_INDEX.relative_to(ROOT)}")
        entry_index = {}
    else:
        entry_index = _read_json(ENTRY_INDEX)
        if entry_index.get("schema") != "qamus/largelexicon-qword-entry-shard-index@1":
            errors.append("entry shard index schema mismatch")
        if entry_index.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append("entry shard index public_boundary mismatch")
    if not SOURCE_REPAIR.exists():
        errors.append(f"missing source-card repair packet: {SOURCE_REPAIR.relative_to(ROOT)}")
        source_repair = {}
    else:
        source_repair = _read_json(SOURCE_REPAIR)
        if source_repair.get("schema") != "qamus/largelexicon-qword-source-card-repair-list@1":
            errors.append("source-card repair schema mismatch")
        if source_repair.get("public_boundary") != PUBLIC_BOUNDARY:
            errors.append("source-card repair public_boundary mismatch")

    seen_row_ids: set[str] = set()
    seen_entry_ids: set[str] = set()
    total_rows = 0
    shard_paths: set[str] = set()
    for shard in shards:
        rel = shard.get("path")
        if not rel:
            errors.append("shard missing path")
            continue
        if "\\" in rel:
            errors.append(f"{rel}: shard path must use POSIX separators")
        if rel in shard_paths:
            errors.append(f"{rel}: duplicate shard path")
        shard_paths.add(rel)
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: shard file missing")
            continue
        if path.stat().st_size > MAX_SHARD_BYTES:
            errors.append(f"{rel}: shard exceeds {MAX_SHARD_BYTES} bytes")
        actual_sha = _sha256_file(path)
        if shard.get("sha256") != actual_sha:
            errors.append(f"{rel}: sha256 mismatch")
        shard_rows = 0
        first_row_id = None
        last_row_id = None
        for line_no, row in _iter_jsonl(path):
            shard_rows += 1
            total_rows += 1
            label = f"{rel}:{line_no}"
            if row.get("schema") != manifest.get("table_schema"):
                errors.append(f"{label}: row schema mismatch")
            errors.extend(public_boundary_errors(row, label))
            if row.get("live_mutation_allowed") is not False:
                errors.append(f"{label}: live_mutation_allowed must be false")
            row_id = row.get("row_id")
            match = ROW_ID_RE.match(row_id or "")
            if not match:
                errors.append(f"{label}: invalid row_id {row_id!r}")
                continue
            entry_id = match.group(1)
            if row.get("entry_id") != entry_id:
                errors.append(f"{label}: row_id entry_id does not match row.entry_id")
            if row_id in seen_row_ids:
                errors.append(f"{label}: duplicate row_id {row_id}")
            seen_row_ids.add(row_id)
            seen_entry_ids.add(entry_id)
            first_row_id = first_row_id or row_id
            last_row_id = row_id
            entry_info = (entry_index.get("entries") or {}).get(entry_id)
            if not entry_info:
                errors.append(f"{label}: entry_id absent from entry shard index")
            elif entry_info.get("path") != rel:
                errors.append(f"{label}: entry shard index points to {entry_info.get('path')!r}")
        if shard.get("row_count") != shard_rows:
            errors.append(f"{rel}: row_count mismatch {shard.get('row_count')} != {shard_rows}")
        if shard_rows and shard.get("first_row_id") != first_row_id:
            errors.append(f"{rel}: first_row_id mismatch")
        if shard_rows and shard.get("last_row_id") != last_row_id:
            errors.append(f"{rel}: last_row_id mismatch")

    if manifest.get("row_count") != total_rows:
        errors.append(f"manifest row_count mismatch {manifest.get('row_count')} != {total_rows}")
    if manifest.get("row_count", 0) < 100000:
        errors.append("manifest row_count unexpectedly low")
    if manifest.get("qamus_entry_count") != 2092:
        errors.append(f"manifest qamus_entry_count expected 2092, got {manifest.get('qamus_entry_count')}")
    if manifest.get("entries_with_qword_rows") != len(seen_entry_ids):
        errors.append("manifest entries_with_qword_rows mismatch")
    repair_ids = {row.get("entry_id") for row in source_repair.get("repairs") or []}
    if set(manifest.get("entries_without_qword_rows") or []) != repair_ids:
        errors.append("source-card repair packet must cover entries_without_qword_rows exactly")
    for row in source_repair.get("repairs") or []:
        if row.get("live_mutation_allowed") is not False:
            errors.append(f"source-card repair {row.get('entry_id')}: live_mutation_allowed must be false")
        if row.get("entry_id") == "2a071cd0b50e":
            hint = row.get("repair_hint") or {}
            if hint.get("source_photo_page_image") != "pg443.jpeg" or hint.get("candidate_quran_ref") != "42:47":
                errors.append("n993 source-card repair must preserve pg443.jpeg / 42:47 hint")
    if ENTRY_INDEX.exists():
        entries = entry_index.get("entries") or {}
        if entry_index.get("entry_count") != len(entries):
            errors.append("entry shard index entry_count mismatch")
        if entry_index.get("qamus_entry_count") != manifest.get("qamus_entry_count"):
            errors.append("entry shard index qamus_entry_count mismatch")
        if entry_index.get("entries_without_qword_rows") != manifest.get("entries_without_qword_rows"):
            errors.append("entry shard index entries_without_qword_rows mismatch")
        if set(entries) != seen_entry_ids:
            errors.append("entry shard index entries do not match shard row entry_ids")
        indexed_paths = {info.get("path") for info in entries.values()}
        if indexed_paths - shard_paths:
            errors.append(f"entry shard index references unknown shard paths: {sorted(indexed_paths - shard_paths)}")
    return errors


def _read_jsonl_rows(path: Path) -> list[dict]:
    return [row for _line_no, row in _iter_jsonl(path)]


def _validate_ledger_custody(
    target_dir: Path, release: dict, expected: dict[str, list[dict]]
) -> list[str]:
    """Bind committed samples and full-ledger digests to the recomputed ledgers.

    The full ledgers are large regenerable outputs kept under gitignored ``out/``;
    what is tracked is a bounded deterministic sample plus the canonical digest of
    the complete ledger. This reconstructs the complete ledgers from the immutable
    source rows, compares the digests independently, and proves each committed
    sample is exactly the deterministic sample of that reconstruction.
    """

    errors: list[str] = []
    declared = release.get("ledgers") or {}
    if set(declared) != {"flagged", "quarantined"}:
        errors.append("release must declare custody for exactly the flagged and quarantined ledgers")
    for disposition in ("flagged", "quarantined"):
        rows = expected[disposition]
        entry = declared.get(disposition) or {}
        expected_entry = promoter.ledger_release_entry(disposition, rows)
        for field in sorted(expected_entry):
            if entry.get(field) != expected_entry[field]:
                errors.append(f"{disposition} ledger custody field {field!r} does not match the recomputation")

        full_path = ROOT / str(entry.get("full_output_path") or "")
        if "out/" not in str(entry.get("full_output_path") or ""):
            errors.append(f"{disposition} full ledger must live under the gitignored out/ tree")
        tracked = target_dir / f"{disposition}-identities.jsonl"
        if tracked.exists():
            errors.append(f"{tracked.relative_to(ROOT).as_posix()}: full ledger must not be committed")

        sample_path = target_dir / f"{disposition}-identities.sample.jsonl"
        meta_path = target_dir / f"{disposition}-identities.sample.meta.json"
        expected_sample = promoter.deterministic_sample(rows)
        if not sample_path.exists():
            errors.append(f"missing committed {disposition} sample: {sample_path.relative_to(ROOT).as_posix()}")
        else:
            actual_sample = _read_jsonl_rows(sample_path)
            if promoter.ledger_bytes(actual_sample) != promoter.ledger_bytes(expected_sample):
                errors.append(f"{disposition} committed sample is not the deterministic sample of the reconstruction")
            errors.extend(
                promoter.bind_ledger_records(
                    actual_sample,
                    {(row["family"], row["identity"]): row for row in rows},
                    label=f"{disposition} sample",
                )
            )
        if not meta_path.exists():
            errors.append(f"missing {disposition} sample sidecar")
        else:
            expected_meta = promoter.review_json(promoter.ledger_meta(rows, disposition, promoter.ledger_bytes(rows)))
            if meta_path.read_text(encoding="utf-8") != expected_meta:
                errors.append(f"{disposition} sample sidecar is stale or non-deterministic")

        # If the regenerated full ledger is present under out/, bind it too.
        if full_path.exists():
            actual_full = _read_jsonl_rows(full_path)
            if promoter.ledger_bytes(actual_full) != promoter.ledger_bytes(rows):
                errors.append(f"{disposition} full ledger under out/ does not match the reconstruction")
            errors.extend(
                promoter.bind_ledger_records(
                    actual_full,
                    {(row["family"], row["identity"]): row for row in rows},
                    label=f"{disposition} full ledger",
                )
            )
        for index, row in enumerate(rows):
            if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("source_row_sha256", ""))):
                errors.append(f"{disposition}[{index}]: source_row_sha256 is not a sha256 digest")
                break
    return errors


def validate_target_release(target_dir: Path | None = None) -> list[str]:
    """Independently re-validate the derived target-schema release. Fails closed."""

    target_dir = target_dir or promoter.TARGET_DIR
    errors: list[str] = []
    try:
        release = promoter.read_release(target_dir)
    except promoter.PromotionError as error:
        return [str(error)]

    errors.extend(promoter.release_blockers(release))

    # Recompute the complete expected ledgers from the immutable source rows. This
    # is the independent authority; committed samples and out/ ledgers are bound
    # to it rather than trusted.
    expected: dict[str, list[dict]] = {"flagged": [], "quarantined": []}
    for family in rows_validator.FAMILIES:
        identity_field = promoter.IDENTITY_FIELDS[family.name]
        for _source, carried, accounting in promoter.iter_family_dispositions(family):
            if carried is None:
                expected[accounting["disposition"]].append(
                    promoter.ledger_record(family.name, identity_field, accounting)
                )
    flagged, quarantined = expected["flagged"], expected["quarantined"]

    ledger_identities = Counter((row["family"], row["identity"]) for row in flagged + quarantined)
    for key, count in sorted(ledger_identities.items()):
        if count != 1:
            errors.append(f"{key[0]}/{key[1]}: identity appears {count} times across the disposition ledgers")

    errors.extend(_validate_ledger_custody(target_dir, release, expected))

    ledger_counts: Counter[tuple[str, str]] = Counter()
    for row in flagged + quarantined:
        ledger_counts[(str(row.get("family")), str(row.get("disposition")))] += 1

    for family in rows_validator.FAMILIES:
        item = (release.get("tables") or {}).get(family.name)
        if item is None:
            continue
        schema = rows_validator.read_json(ROOT / family.schema_path)
        target = schema["properties"]["schema"]["const"]
        digest = hashlib.sha256()
        carried_count = 0
        versions: Counter[str] = Counter()
        carried_identities: set[str] = set()
        identity_field = promoter.IDENTITY_FIELDS[family.name]
        source_count = 0
        for _source, carried, accounting in promoter.iter_family_dispositions(family):
            source_count += 1
            if carried is None:
                continue
            carried_count += 1
            carried_identities.add(str(accounting[identity_field]))
            versions[str(carried.get("schema"))] += 1
            digest.update(promoter.canonical_line(carried))
            row_errors = rows_validator.schema_errors(carried, schema)
            if row_errors:
                errors.append(
                    "%s/%s: carried row fails the unchanged target schema (%s)"
                    % (family.name, accounting[identity_field], row_errors[0]["defect_family"])
                )
            surviving = sorted(promoter.HOISTED_FIELDS.intersection(carried))
            if surviving:
                errors.append(
                    "%s/%s: row-forbidden constant survived migration: %s"
                    % (family.name, accounting[identity_field], ",".join(surviving))
                )
            leaks = match_forbidden_labels(
                promoter.canonical_text(carried).lower(), FORBIDDEN_PUBLIC_SUBSTRINGS
            )
            if leaks:
                errors.append(
                    "%s/%s: carried row leaks forbidden public labels: %s"
                    % (family.name, accounting[identity_field], ",".join(sorted(leaks)))
                )
        if len(versions) > 1:
            errors.append(f"{family.name}: carried rows mix schema versions {sorted(versions)}")
        if versions and next(iter(versions)) != target:
            errors.append(f"{family.name}: carried rows do not declare {target}")
        if carried_count != item.get("carried_row_count"):
            errors.append(
                "%s: released carried_row_count %s != recomputed %s"
                % (family.name, item.get("carried_row_count"), carried_count)
            )
        if digest.hexdigest() != item.get("carried_sha256"):
            errors.append(f"{family.name}: carried_sha256 drifted from the regenerated table")
        counts = item.get("disposition_counts") or {}
        if counts.get("carried") != carried_count:
            errors.append(f"{family.name}: disposition_counts carried disagrees with the regenerated table")
        for disposition in ("flagged", "quarantined"):
            if counts.get(disposition) != ledger_counts.get((family.name, disposition), 0):
                errors.append(
                    "%s: released %s count %s != ledger rows %s"
                    % (family.name, disposition, counts.get(disposition), ledger_counts.get((family.name, disposition), 0))
                )
        accounted = sum(counts.get(name, 0) for name in promoter.DISPOSITIONS)
        if accounted != source_count or item.get("source", {}).get("row_count") != source_count:
            errors.append(
                "%s: dispositions account for %s of %s source rows (silent drop)"
                % (family.name, accounted, source_count)
            )
        ledger_family_identities = {
            str(row.get("identity")) for row in flagged + quarantined if row.get("family") == family.name
        }
        overlap = sorted(carried_identities & ledger_family_identities)[:3]
        if overlap:
            errors.append(f"{family.name}: identities carried AND dispositioned elsewhere: {overlap}")

    losslessness = release.get("losslessness") or {}
    if losslessness.get("silent_drop_count") != 0:
        errors.append("release declares a non-zero silent drop count")
    if losslessness.get("accounted_row_count") != losslessness.get("source_row_count"):
        errors.append("release accounted_row_count does not equal source_row_count")
    return errors


def run_self_test() -> int:
    """Red-first fixtures: every fail-closed path must reject its bad release."""

    assertions = 0
    families = [family.name for family in rows_validator.FAMILIES]
    snapshot = {family.schema_path: "sha-" + family.name for family in rows_validator.FAMILIES}
    healthy = {
        "schema": promoter.RELEASE_SCHEMA,
        "baseline": {"source_sha256": dict(snapshot)},
        "losslessness": {"accounted_row_count": 5, "silent_drop_count": 0, "source_row_count": 5},
        "tables": {
            name: {
                "carried_row_count": 5,
                "provenance": {
                    "boundary_constants": {
                        field: {"coverage": "all_rows", "rows_present": 5, "rows_total": 5, "value": value}
                        for field, value in promoter.CANONICAL_BOUNDARY.items()
                    }
                },
                "target_row_schema": promoter.target_row_schema(
                    next(item for item in rows_validator.FAMILIES if item.name == name)
                ),
                "target_schema_sha256": "sha-" + name,
                "validation": {"pass_rows": 5, "violation_rows": 0},
            }
            for name in families
        },
    }
    assert promoter.release_blockers(healthy, snapshot=snapshot) == []
    assertions += 1

    for mutate, expected in (
        (lambda r: r["tables"][families[0]]["validation"].update({"violation_rows": 1}), "validation-red"),
        (lambda r: r["tables"][families[0]].update({"target_schema_sha256": "other"}), "target schema changed"),
        (lambda r: r["tables"][families[0]].update({"target_row_schema": "fusha/bogus@9"}), "released target row schema is stale"),
        (lambda r: r["tables"][families[0]]["provenance"].update({"boundary_constants": {}}), "declare all four safety constants"),
        (
            lambda r: r["tables"][families[0]]["provenance"]["boundary_constants"]["public_boundary"].update(
                {"value": {"kind": "imported", "lang": "en", "src": "external"}}
            ),
            "is not canonical",
        ),
        (lambda r: r["baseline"]["source_sha256"].update({families[0]: "drift"}), "changed since the release was built"),
        (lambda r: r.update({"schema": "qamus/other@1"}), "release schema is not"),
    ):
        broken = copy.deepcopy(healthy)
        mutate(broken)
        blockers = promoter.release_blockers(broken, snapshot=snapshot)
        assert any(expected in blocker for blocker in blockers), (expected, blockers)
        assertions += 1

    # a carried row that kept a row-forbidden safety constant must be caught
    carried = rows_validator.good_rows()["lemma-source"]
    assert not promoter.HOISTED_FIELDS.intersection(carried)
    laundered = dict(carried, public_boundary=dict(PUBLIC_BOUNDARY))
    assert sorted(promoter.HOISTED_FIELDS.intersection(laundered)) == ["public_boundary"]
    assertions += 1

    # a carried row leaking a forbidden public label must be caught
    leaked = dict(carried, gloss_hint="checked against qac")
    assert match_forbidden_labels(promoter.canonical_text(leaked).lower(), FORBIDDEN_PUBLIC_SUBSTRINGS) == ["qac"]
    assert match_forbidden_labels(promoter.canonical_text(carried).lower(), FORBIDDEN_PUBLIC_SUBSTRINGS) == []
    assertions += 1

    print(
        json.dumps(
            {"assertions": assertions, "ok": True, "schema": "qamus/largelexicon-table-manifest-self-test@1"},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def validate_generated_ledgers() -> list[str]:
    """Prove the GENERATED full ledgers under out/ match TARGET-RELEASE.json exactly.

    A consumer of the residue population must never read a row before this passes:
    the tracked artifacts are bounded samples, and the full ledgers are regenerated
    outputs whose only authority is the release digest.
    """

    errors: list[str] = []
    try:
        release = promoter.read_release()
    except promoter.PromotionError as error:
        return [str(error)]
    for disposition, entry in sorted((release.get("ledgers") or {}).items()):
        relative = str(entry.get("full_output_path") or "")
        if not relative.startswith("out/"):
            errors.append(f"{disposition}: full ledger path is not under the gitignored out/ tree")
            continue
        path = ROOT / relative
        if not path.exists():
            errors.append(
                f"{disposition}: generated ledger is absent — run "
                "`python tools/promote_largelexicon_target_schema.py --write` first"
            )
            continue
        digest = _sha256_file(path)
        if digest != entry.get("sha256"):
            errors.append(f"{disposition}: generated ledger sha256 disagrees with TARGET-RELEASE.json")
            continue
        rows = _read_jsonl_rows(path)
        if len(rows) != entry.get("row_count"):
            errors.append(f"{disposition}: generated ledger row count disagrees with the release")
        families = Counter(str(row.get("family")) for row in rows)
        if dict(sorted(families.items())) != entry.get("family_counts"):
            errors.append(f"{disposition}: generated ledger family counts disagree with the release")
    return errors


def validate_triage(triage_path: Path) -> list[str]:
    """Prove a triage output covers the generated residue exactly, once and terminally."""

    errors = validate_generated_ledgers()
    if errors:
        return errors
    release = promoter.read_release()
    expected: set[tuple[str, str]] = set()
    for disposition, entry in sorted((release.get("ledgers") or {}).items()):
        for row in _read_jsonl_rows(ROOT / str(entry["full_output_path"])):
            expected.add((str(row["family"]), str(row["identity"])))
    if not triage_path.exists():
        return [f"triage output is absent: {triage_path}"]
    if ROOT in triage_path.resolve().parents and not triage_path.resolve().is_relative_to((ROOT / "out").resolve()):
        errors.append("the FULL triage output must live under the gitignored out/ tree")
    seen: set[tuple[str, str]] = set()
    for line_no, row in _iter_jsonl(triage_path):
        key = (str(row.get("family")), str(row.get("identity")))
        if key in seen:
            errors.append(f"triage:{line_no}: duplicate triage row for {key[0]}/{key[1]}")
        seen.add(key)
        if key not in expected:
            errors.append(f"triage:{line_no}: {key[0]}/{key[1]} is not a residue identity")
        state = row.get("triage_state")
        if not state:
            errors.append(f"triage:{line_no}: no terminal triage state")
        elif state == "carried":
            errors.append(f"triage:{line_no}: carried is not a triage state; only the promoter assigns dispositions")
    missing = sorted(expected - seen)[:3]
    if missing:
        errors.append(f"triage output omits residue identities, e.g. {missing}")
    if len(seen) != len(expected):
        errors.append(f"triage output covers {len(seen)} of {len(expected)} residue identities")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sharded largelexicon qword denominator storage.")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--target-release",
        action="store_true",
        help="re-validate the derived target-schema release against the unchanged schemas",
    )
    parser.add_argument(
        "--validate-generated-ledgers",
        action="store_true",
        help="prove the regenerated full ledgers under out/ match TARGET-RELEASE.json",
    )
    parser.add_argument(
        "--validate-triage",
        metavar="PATH",
        help="prove a triage output covers the generated residue exactly",
    )
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.validate_triage:
        errors = validate_triage(Path(args.validate_triage))
    elif args.validate_generated_ledgers:
        errors = validate_generated_ledgers()
    else:
        errors = validate_target_release() if args.target_release else validate(Path(args.manifest))
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
