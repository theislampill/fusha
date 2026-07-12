#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the deterministic T11 review queue for accepted, undeployed locations.

This is a classification/reporting tool only.  It never authors content, marks a
row deployable, or writes a whitelist.
"""
import argparse
import collections
import copy
import glob
import hashlib
import io
import json
import os
import re
import sys
import time


ROW_SCHEMA = "qamus.append_queue_row.v1"
MANIFEST_SCHEMA = "qamus.append_queue_manifest.v1"
EXPECTED_BASELINE_SHA256 = "972263b5472478b8805c39e107ecf5d6f8096acace8756d15a08967cddf90515"
EXPECTED_QUEUE_ROWS = 13251
PLACEHOLDER_MARKERS = (
    "dry-run carrier preview", "dry run carrier preview", "placeholder",
    "todo", "tbd", "pending gloss",
)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def is_generation_deploy_eligible(row):
    """Live-deploy discriminator gate (RM-40): fail-closed on generated forms.

    The sarf projection branch already stamps ``generation_used: False`` on the
    sourced-baseline signal (see the classifier below). This guard is the
    belt-and-suspenders enforcement for any downstream whitelist/merge step: a
    row is deploy-eligible ONLY if it is a materialized, sourced (non-generated)
    baseline fact. A ``generation_used: true`` row is refused even if it somehow
    reaches ``materialized`` in the ledger — paradigm-generated candidates can
    never enter the live hover surface.
    """
    return (
        row.get("generation_used", False) is False
        and row.get("certification_state") == "materialized"
        and row.get("source") == "qamus_current_authored"
    )


def read_jsonl(path):
    with io.open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError("malformed JSONL %s:%d: %s" %
                                     (path, line_number, exc)) from exc


def sha256_file(path):
    digest = hashlib.sha256()
    with io.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def location_key(loc):
    if not isinstance(loc, str) or not re.fullmatch(r"[1-9]\d*:[1-9]\d*:[1-9]\d*", loc):
        return (sys.maxsize, sys.maxsize, sys.maxsize, str(loc))
    return tuple(int(part) for part in loc.split(":"))


def usable_text(value):
    if not isinstance(value, str) or not value.strip():
        return False
    folded = " ".join(value.casefold().split())
    return not any(marker in folded for marker in PLACEHOLDER_MARKERS)


def norm_strict(value):
    from tools.normalize_ar import norm_strict as normalize
    return normalize(value or "")


def carrier(binding):
    return {key: binding.get(key) for key in
            ("entry_id", "card_id", "qword_row_id", "row_id")}


def entry_has_content(entry):
    if any(usable_text(entry.get(field)) for field in ("definition", "meaning")):
        return True
    if any(usable_text(sense.get("gloss")) for sense in entry.get("senses") or []):
        return True
    for usage in entry.get("usage") or []:
        if any(usable_text(example.get("en")) for example in usage.get("examples") or []):
            return True
    return False


def exact_example_source(binding, entry):
    """Return an exact, authored, source-addressed example or None."""
    boundary = binding.get("public_boundary") or {}
    if boundary != {"kind": "authored", "lang": "en", "src": "qamus"}:
        return None
    usage_index = binding.get("usage_index")
    example_index = binding.get("example_index")
    if not isinstance(usage_index, int) or not isinstance(example_index, int):
        return None
    usages = entry.get("usage") or []
    if not (1 <= usage_index <= len(usages)):
        return None
    examples = usages[usage_index - 1].get("examples") or []
    if not (1 <= example_index <= len(examples)):
        return None
    example = examples[example_index - 1]
    if (example.get("ref") != binding.get("quran_ref") or
            not usable_text(example.get("ar")) or not usable_text(example.get("en"))):
        return None
    address = "entry:%s/usage/%d/examples/%d" % (
        entry.get("id"), usage_index, example_index)
    return {
        "address": address,
        "entry_id": entry.get("id"),
        "fields": ["ar", "en", "ref"],
        "kind": "exact_authored_example",
        "path": "qamus/data/current/entries.jsonl",
    }


def matching_sense_sources(entry, surface):
    target = norm_strict(surface)
    sources = []
    for index, sense in enumerate(entry.get("senses") or [], 1):
        candidates = [part.strip() for part in str(sense.get("ar") or "").split("/")]
        if target and target in {norm_strict(part) for part in candidates} and usable_text(sense.get("gloss")):
            sources.append({
                "address": "entry:%s/senses/%d" % (entry.get("id"), index),
                "entry_id": entry.get("id"),
                "fields": ["ar", "gloss"],
                "kind": "authored_sense",
                "path": "qamus/data/current/entries.jsonl",
            })
    return sources


def matching_form_sources(entry, surface):
    target = norm_strict(surface)
    sources = []
    for usage_index, usage in enumerate(entry.get("usage") or [], 1):
        forms = usage.get("forms") or []
        matches = [form for form in forms if target and norm_strict(form) == target]
        sense_number = usage.get("sense")
        senses = entry.get("senses") or []
        gloss_ok = (isinstance(sense_number, int) and 1 <= sense_number <= len(senses)
                    and usable_text(senses[sense_number - 1].get("gloss")))
        if matches and gloss_ok:
            sources.append({
                "address": "entry:%s/usage/%d/forms" % (entry.get("id"), usage_index),
                "entry_id": entry.get("id"),
                "fields": ["forms", "sense"],
                "kind": "documented_surface_form",
                "path": "qamus/data/current/entries.jsonl",
            })
    return sources


def classify_location(loc, bindings, entries_by_id):
    """Return (primary_class, evidence, content_sources, competing_analyses)."""
    row_ids = [row.get("row_id") for row in bindings]
    carrier_keys = [json.dumps(carrier(row), sort_keys=True) for row in bindings]
    if (location_key(loc)[0] == sys.maxsize or not bindings or None in row_ids or
            len(set(row_ids)) != len(row_ids) or len(set(carrier_keys)) != len(carrier_keys)):
        return ("invalid_or_duplicate", {
            "signal": "malformed_location_or_duplicate_binding_artifact",
            "binding_rows": len(bindings), "unique_row_ids": len(set(row_ids)),
        }, [], [])

    found = [(binding, entries_by_id.get(binding.get("entry_id"))) for binding in bindings]
    missing = sorted({binding.get("entry_id") for binding, entry in found if entry is None})
    empty = sorted({entry.get("id") for _binding, entry in found
                    if entry is not None and not entry_has_content(entry)})
    if missing or empty:
        return ("insufficient_evidence", {
            "signal": "entry_lookup_missing_or_authored_content_empty",
            "missing_entry_ids": missing, "empty_content_entry_ids": empty,
        }, [], [])

    analyses = sorted({(entry.get("root") or "", entry.get("section") or "")
                       for _binding, entry in found})
    if len(analyses) > 1:
        competing = [{"root": root, "section": section} for root, section in analyses]
        return ("competing_analyses", {
            "signal": "bound_entries_disagree_on_root_or_section",
            "analysis_count": len(competing),
        }, [], competing)

    exact_sources = []
    for binding, entry in found:
        source = exact_example_source(binding, entry)
        if source is None:
            exact_sources = []
            break
        exact_sources.append(source)
    if exact_sources:
        return ("exact_certified_transclusion", {
            "signal": "every_binding_has_exact_authored_entry_example",
            "exact_source_count": len(exact_sources),
            "candidate_only": True,
        }, sorted(exact_sources, key=lambda item: item["address"]), [])

    surfaces = [binding.get("resolved_surface") or binding.get("visible_surface") or ""
                for binding, _entry in found]
    sections = {entry.get("section") for _binding, entry in found}

    # Generic existing-content matching is deliberately limited to non-projection
    # sections. Verb and particle matches are labeled by their more precise,
    # candidate-only documented-form signals below.
    if not sections.intersection({"verb", "particle"}):
        sense_sources = []
        for (binding, entry), surface in zip(found, surfaces):
            sense_sources.extend(matching_sense_sources(entry, surface))
        if sense_sources:
            return ("existing_content_needs_binding", {
                "signal": "exact_surface_matches_authored_entry_sense_without_exact_occurrence",
                "matched_source_count": len(sense_sources),
                "candidate_only": True,
            }, sorted(sense_sources, key=lambda item: item["address"]), [])

    form_sources = []
    for (binding, entry), surface in zip(found, surfaces):
        form_sources.extend(matching_form_sources(entry, surface))
    if sections == {"verb"} and form_sources:
        return ("sarf_projection_candidate", {
            "signal": "verb_section_exact_norm_strict_match_in_documented_usage_forms",
            "matched_source_count": len(form_sources),
            "generation_used": False, "candidate_only": True,
        }, sorted(form_sources, key=lambda item: item["address"]), [])
    if sections == {"particle"} and form_sources:
        return ("nahw_projection_candidate", {
            "signal": "particle_section_exact_norm_strict_match_in_documented_usage_forms",
            "matched_source_count": len(form_sources),
            "role_certified": False, "candidate_only": True,
        }, sorted(form_sources, key=lambda item: item["address"]), [])

    return ("independent_authoring_required", {
        "signal": "no_exact_example_surface_sense_or_documented_projection_form_match",
        "candidate_only": True,
    }, [], [])


def row_dependency_hashes(bindings, entries_sha=None, by_entry_id_sha=None):
    hashes = {}
    for binding in bindings:
        hashes["binding:%s" % binding.get("row_id")] = stable_hash(binding)
        for dependency in binding.get("source_dependencies") or []:
            if dependency.get("id") and dependency.get("sha256"):
                hashes["source:%s" % dependency["id"]] = dependency["sha256"]
    if entries_sha:
        hashes["qamus/data/current/entries.jsonl"] = entries_sha
    if by_entry_id_sha:
        hashes["qamus/indexes/current/by-entry-id.json"] = by_entry_id_sha
    return {key: hashes[key] for key in sorted(hashes)}


def build_rows(bindings, entries_by_id, entries_sha=None, by_entry_id_sha=None,
               selected_locations=None):
    grouped = collections.defaultdict(list)
    for binding in bindings:
        loc = binding.get("canonical_wbw_loc")
        if isinstance(loc, str) and loc.startswith("wbw:"):
            loc = loc[4:]
        if selected_locations is None or loc in selected_locations:
            grouped[loc].append(binding)
    rows = []
    for loc in sorted(grouped, key=location_key):
        loc_bindings = sorted(grouped[loc], key=lambda row: (
            str(row.get("entry_id")), str(row.get("card_id")),
            str(row.get("qword_row_id")), str(row.get("row_id"))))
        primary, evidence, sources, competing = classify_location(
            loc, loc_bindings, entries_by_id)
        rows.append({
            "schema": ROW_SCHEMA,
            "canonical_location": loc,
            "bound_carriers": [carrier(binding) for binding in loc_bindings],
            "binding_count": len(loc_bindings),
            "primary_class": primary,
            "class_evidence": evidence,
            "content_sources": sources,
            "dependency_hashes": row_dependency_hashes(
                loc_bindings, entries_sha, by_entry_id_sha),
            "competing_analyses": competing,
            "review_state": "pending",
            "review_votes": [],
            "certified": False,
            "blocker_or_exception": None,
            "resolution_commit": None,
        })
    return rows


def reconcile_count(accepted_count, valid_live_count, morphline_count, actual_count,
                    expected_count=None):
    derived = accepted_count - valid_live_count - morphline_count
    if derived != actual_count:
        raise ValueError("count reconciliation failed: %d - %d - %d = %d, rows=%d" %
                         (accepted_count, valid_live_count, morphline_count, derived,
                          actual_count))
    if expected_count is not None and actual_count != expected_count:
        raise ValueError("append count STOP: expected %d, actual %d; arithmetic %d - %d - %d" %
                         (expected_count, actual_count, accepted_count,
                          valid_live_count, morphline_count))
    return derived


def baseline_payload_ok(row):
    from tools import compile_canonical_hover_whitelist_packet as compiler
    content = compiler.public_content(row)
    return (bool(row.get("segments") or []) and bool(content.get("morphline")) and
            bool(content.get("public_gloss")) and
            bool(content.get("learner_explanation")))


def build_queue(repo_root, baseline_path, crosswalk_glob=None, entries_path=None,
                current_indexes_glob=None, expected_rows=EXPECTED_QUEUE_ROWS,
                expected_baseline_sha=EXPECTED_BASELINE_SHA256):
    """Return a hash-pinned manifest and one deterministic row per append location."""
    started = time.monotonic()
    from tools import compile_canonical_hover_whitelist_packet as compiler

    baseline_sha = sha256_file(baseline_path)
    if expected_baseline_sha and baseline_sha != expected_baseline_sha:
        raise ValueError("baseline SHA256 STOP: expected %s, actual %s" %
                         (expected_baseline_sha, baseline_sha))

    crosswalk_pattern = crosswalk_glob or os.path.join(
        repo_root, "qamus", "indexes", "largelexicon", "qword-crosswalk", "*.jsonl")
    crosswalk_files = sorted(glob.glob(crosswalk_pattern))
    if not crosswalk_files:
        raise ValueError("no crosswalk inputs matched %s" % crosswalk_pattern)
    accepted = []
    accepted_locations = set()
    for path in crosswalk_files:
        for row in read_jsonl(path):
            if row.get("status") != "canonical_crosswalk_accepted":
                continue
            loc = row.get("canonical_wbw_loc")
            if isinstance(loc, str) and loc.startswith("wbw:"):
                loc = loc[4:]
            row = dict(row)
            row["canonical_wbw_loc"] = loc
            accepted.append(row)
            accepted_locations.add(loc)

    valid_live_locations = set()
    morphline_family = set()
    live_locations = set()
    other_failed_payloads = []
    baseline_rows = 0
    for live in read_jsonl(baseline_path):
        baseline_rows += 1
        loc = compiler.canonical_public_loc(live)
        if not loc:
            continue
        live_locations.add(loc)
        if loc not in accepted_locations:
            continue
        if baseline_payload_ok(live):
            valid_live_locations.add(loc)
        else:
            content = compiler.public_content(live)
            if (bool(live.get("segments") or []) and bool(content.get("public_gloss")) and
                    bool(content.get("learner_explanation")) and
                    not bool(content.get("morphline"))):
                morphline_family.add(loc)
            else:
                other_failed_payloads.append(loc)
    if other_failed_payloads:
        raise ValueError("baseline payload STOP: %d accepted live locations fail outside "
                         "the morphline family (examples %s)" %
                         (len(other_failed_payloads), sorted(other_failed_payloads,
                                                             key=location_key)[:5]))

    selected_locations = accepted_locations - valid_live_locations - morphline_family
    reconcile_count(len(accepted_locations), len(valid_live_locations),
                    len(morphline_family), len(selected_locations), expected_rows)

    entries_path = entries_path or os.path.join(
        repo_root, "qamus", "data", "current", "entries.jsonl")
    entries_by_id = {}
    for entry in read_jsonl(entries_path):
        entry_id = entry.get("id")
        if not entry_id or entry_id in entries_by_id:
            raise ValueError("entries dataset invalid/duplicate id: %r" % entry_id)
        entries_by_id[entry_id] = entry

    indexes_pattern = current_indexes_glob or os.path.join(
        repo_root, "qamus", "indexes", "current", "*.json")
    index_files = sorted(glob.glob(indexes_pattern))
    by_entry_path = next((path for path in index_files
                          if os.path.basename(path) == "by-entry-id.json"), None)
    if by_entry_path is None:
        raise ValueError("current index STOP: by-entry-id.json missing")
    with io.open(by_entry_path, encoding="utf-8") as handle:
        by_entry_id = json.load(handle)

    selected_bindings = [row for row in accepted
                         if row.get("canonical_wbw_loc") in selected_locations]
    bound_entry_ids = {row.get("entry_id") for row in selected_bindings}
    missing_entries = sorted(entry_id for entry_id in bound_entry_ids
                             if entry_id not in entries_by_id or entry_id not in by_entry_id)
    lookup_failure_rate = (len(missing_entries) / len(bound_entry_ids)
                           if bound_entry_ids else 0.0)
    if lookup_failure_rate > 0.01:
        raise ValueError("entry lookup STOP: %d/%d (%.4f%%) bound entry ids missing" %
                         (len(missing_entries), len(bound_entry_ids),
                          lookup_failure_rate * 100))

    entries_sha = sha256_file(entries_path)
    by_entry_id_sha = sha256_file(by_entry_path)
    queue = build_rows(selected_bindings, entries_by_id, entries_sha,
                       by_entry_id_sha, selected_locations)
    reconcile_count(len(accepted_locations), len(valid_live_locations),
                    len(morphline_family), len(queue), expected_rows)

    class_counts = collections.Counter(row["primary_class"] for row in queue)
    class_examples = collections.defaultdict(list)
    for row in queue:
        examples = class_examples[row["primary_class"]]
        if len(examples) < 5:
            examples.append(row["canonical_location"])

    elapsed = time.monotonic() - started
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "artifact_schema_classification": "new_artifact_schema_only",
        "queue_schema": ROW_SCHEMA,
        "queue_rows": len(queue),
        "class_counts": dict(sorted(class_counts.items())),
        "class_examples": {key: value for key, value in sorted(class_examples.items())},
        "derivation": {
            "accepted_locations": len(accepted_locations),
            "valid_live_locations": len(valid_live_locations),
            "morphline_family_locations": len(morphline_family),
            "arithmetic": "%d - %d - %d = %d" % (
                len(accepted_locations), len(valid_live_locations),
                len(morphline_family), len(queue)),
        },
        "classification_signals": {
            "exact_certified_transclusion": (
                "every accepted binding points by 1-based usage/example address to an entry-stored "
                "example with the same ayah ref, non-placeholder Arabic and English, and the binding's "
                "public_boundary is exactly qamus/authored/en; candidate label only"),
            "existing_content_needs_binding": (
                "non-verb/non-particle exact norm_strict surface match to an authored sense gloss, "
                "without an exact occurrence example"),
            "sarf_projection_candidate": (
                "verb section plus exact norm_strict occurrence-surface match in usage.forms tied to "
                "an authored sense; no forms generated; candidate label only"),
            "nahw_projection_candidate": (
                "particle section plus exact norm_strict occurrence-surface match in usage.forms tied "
                "to an authored sense; role remains uncertified; candidate label only"),
            "construction_template_candidate": (
                "not implemented: current entries expose no structured construction/template field; "
                "free prose is not mined"),
            "independent_authoring_required": (
                "no exact example, exact authored sense, or documented section-specific form match"),
            "competing_analyses": "bound entries expose more than one (root, section) pair",
            "insufficient_evidence": "entry lookup missing or all authored content empty/placeholder",
            "invalid_or_duplicate": "malformed canonical location or duplicate binding artifact",
        },
        "safety_invariants": {
            "all_rows_certified_false": True,
            "all_rows_pending": True,
            "blocked_class_emitted": False,
            "content_generation_used": False,
            "whitelist_written": False,
        },
        "lookup_evidence": {
            "bound_entry_ids": len(bound_entry_ids),
            "missing_entry_ids": missing_entries,
            "failure_rate": lookup_failure_rate,
        },
        "red_first": {
            "placeholder_trap": "FAIL before implementation: NameError classify_location is not defined",
            "required_result": "insufficient_evidence_or_independent_authoring_required_never_1_or_2",
        },
        "input_hashes": {
            "baseline": {"sha256": baseline_sha, "rows": baseline_rows},
            "entries": {"path": "qamus/data/current/entries.jsonl", "sha256": entries_sha},
            "current_indexes": {os.path.basename(path): sha256_file(path)
                                for path in index_files},
            "qword_crosswalk": {os.path.basename(path): sha256_file(path)
                                for path in crosswalk_files},
        },
        "runtime_limit_seconds": 600,
        "rollback": "git revert (analysis artifact; no consumer at creation time)",
        "generator": "python tools/build_append_queue.py --baseline <path>",
    }
    if elapsed >= 600:
        raise ValueError("runtime STOP: %.3fs exceeds 600s" % elapsed)
    return manifest, queue


def write_outputs(outdir, manifest, queue):
    os.makedirs(outdir, exist_ok=True)
    queue_path = os.path.join(outdir, "append-queue.jsonl")
    with io.open(queue_path, "w", encoding="utf-8", newline="\n") as handle:
        for row in queue:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    final_manifest = dict(manifest)
    final_manifest["queue_sha256"] = sha256_file(queue_path)
    manifest_path = os.path.join(outdir, "append-queue.manifest.json")
    with io.open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(final_manifest, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    return queue_path, manifest_path, final_manifest


def _self_test():
    """Synthetic red/green contract tests kept beside the single authorized tool."""
    failures = []

    def check(name, condition):
        print(("ok   " if condition else "FAIL ") + name)
        if not condition:
            failures.append(name)

    def binding(loc="1:1:1", entry_id="e1", section="noun", root="r"):
        return {
            "canonical_wbw_loc": loc,
            "card_id": "%s:u1:e1" % entry_id,
            "entry_id": entry_id,
            "example_index": 1,
            "public_boundary": {"kind": "authored", "lang": "en", "src": "qamus"},
            "quran_ref": ":".join(loc.split(":")[:2]),
            "qword_row_id": "q-%s" % entry_id,
            "resolved_surface": "كَتَبَ",
            "row_id": "cw-%s" % entry_id,
            "source_dependencies": [{"id": "card-%s" % entry_id, "sha256": "aa"}],
            "status": "canonical_crosswalk_accepted",
            "usage_index": 1,
            "_fixture_section": section,
            "_fixture_root": root,
        }

    def entry(entry_id="e1", section="noun", root="r", sense_ar="كَتَبَ",
              gloss="wrote", forms=None, example_en="authored rendering"):
        return {
            "id": entry_id,
            "section": section,
            "root": root,
            "definition": gloss,
            "meaning": gloss,
            "senses": ([{"ar": sense_ar, "gloss": gloss, "n": 1}] if sense_ar else []),
            "usage": [{"sense": 1, "forms": forms or [sense_ar], "examples": [{
                "ar": "كَتَبَ ٱللَّهُ", "en": example_en, "ref": "1:1"}]}],
        }

    # RED-FIRST MUST run first: placeholder-only content may never become class 1/2.
    placeholder = entry(gloss="dry-run carrier preview", example_en="dry-run carrier preview")
    got = classify_location("1:1:1", [binding()], {"e1": placeholder})
    check("RED-FIRST placeholder-only trap stays non-content",
          got[0] in {"insufficient_evidence", "independent_authoring_required"})

    exact = classify_location("1:1:1", [binding()], {"e1": entry()})
    check("exact certified transclusion fixture", exact[0] == "exact_certified_transclusion")

    needs_binding_entry = entry()
    needs_binding_entry["usage"][0]["examples"] = []
    existing = classify_location("1:1:1", [binding()], {"e1": needs_binding_entry})
    check("existing content needs binding fixture", existing[0] == "existing_content_needs_binding")

    sarf_entry = entry(section="verb", sense_ar="كَتَبَ", forms=["يَكْتُبُ"])
    sarf_entry["usage"][0]["examples"] = []
    sarf_binding = binding(section="verb"); sarf_binding["resolved_surface"] = "يَكْتُبُ"
    sarf = classify_location("1:1:1", [sarf_binding], {"e1": sarf_entry})
    check("sarf projection fixture", sarf[0] == "sarf_projection_candidate")

    nahw_entry = entry(section="particle", sense_ar="لَا", forms=["لَا"])
    nahw_entry["usage"][0]["examples"] = []
    nahw_binding = binding(section="particle", root=""); nahw_binding["resolved_surface"] = "لَا"
    nahw = classify_location("1:1:1", [nahw_binding], {"e1": nahw_entry})
    check("nahw projection fixture", nahw[0] == "nahw_projection_candidate")

    empty = entry(sense_ar="", gloss=""); empty["usage"] = []
    independent_entry = entry(sense_ar="غَيْر", gloss="documented other surface")
    independent_entry["usage"][0]["forms"] = ["غَيْر"]
    independent_entry["usage"][0]["examples"] = []
    independent = classify_location("1:1:1", [binding()], {"e1": independent_entry})
    check("independent authoring fixture", independent[0] == "independent_authoring_required")
    insufficient = classify_location("1:1:1", [binding()], {"e1": empty})
    check("insufficient evidence fixture", insufficient[0] == "insufficient_evidence")

    b2 = binding(entry_id="e2", section="verb", root="x")
    competing = classify_location("1:1:1", [binding(), b2], {
        "e1": entry(), "e2": entry(entry_id="e2", section="verb", root="x")})
    check("competing analyses fixture", competing[0] == "competing_analyses")

    invalid = classify_location("bad", [binding(loc="bad")], {"e1": entry()})
    check("invalid location fixture", invalid[0] == "invalid_or_duplicate")
    duplicate = classify_location("1:1:1", [binding(), copy.deepcopy(binding())], {"e1": entry()})
    check("duplicate binding fixture", duplicate[0] == "invalid_or_duplicate")

    rows_a = build_rows([binding(), b2], {"e1": entry(), "e2": entry(entry_id="e2")})
    rows_b = build_rows([b2, binding()], {"e2": entry(entry_id="e2"), "e1": entry()})
    check("determinism under input reordering", rows_a == rows_b)
    check("count reconciliation accepts exact count", reconcile_count(10, 3, 2, 5) == 5)
    try:
        reconcile_count(10, 3, 2, 4)
    except ValueError:
        count_failed = True
    else:
        count_failed = False
    check("count reconciliation stops on mismatch", count_failed)

    if failures:
        raise SystemExit("FAIL - %d append queue self-test(s): %s" %
                         (len(failures), ", ".join(failures)))
    print("PASS - append queue self-test (%d checks)" % 13)


def main():
    parser = argparse.ArgumentParser(
        description="Build the deterministic, pending-only T11 append candidate queue")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--baseline", help="deployed whitelist JSONL (hash-pinned)")
    parser.add_argument("--outdir", default=os.path.join(
        REPO, "qamus", "indexes", "largelexicon", "append-queue"))
    args = parser.parse_args()
    if args.self_test:
        _self_test()
        return
    if not args.baseline:
        parser.error("--baseline is required unless --self-test")
    manifest, queue = build_queue(REPO, args.baseline)
    queue_path, manifest_path, final_manifest = write_outputs(
        args.outdir, manifest, queue)
    print("wrote %d rows to %s" % (len(queue), queue_path))
    print("manifest %s" % manifest_path)
    print("arithmetic %s" % final_manifest["derivation"]["arithmetic"])
    print("class_counts %s" % json.dumps(
        final_manifest["class_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
