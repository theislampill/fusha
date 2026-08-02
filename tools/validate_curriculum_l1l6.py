#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone validator for the L1-L6 curriculum substrate (curriculum/l1l6/).

Named, fail-closed checks over the committed artifacts (NO private corpus
needed; manifest reproducibility against the corpus is the builder's
--check mode, optionally invoked here via --source-dir):

- manifest_shape        stable IDs, sha256 format, custody constant, counts
- registry_consistency  levels/modules/lessons cross-tallies + manifest joins
- graph_integrity       unique IDs, resolvable endpoints, acyclic prereq graph
- nfc_normalization     every committed string is NFC
- crosswalk_evidence    closed repo_state vocab; every cited repo path exists;
                        packet references resolve
- ledger_qualification  closed status vocab; guard<->claim reciprocity; ZERO
                        repository-certified rows in this subtree
- links_candidacy       every P/V/N link row is status candidate; p-key format
- material_classes      quiz census matches registry; held-out class empty
- leakage_scan          no server/absolute paths, no informed_by, no long
                        Arabic prose runs (source-prose heuristic), in ANY
                        subtree file
- no_certification      no artifact claims certified state anywhere
- pilot_parity          letter partition = facts; every letter owned exactly
                        once; projection.json byte-equals recompilation from
                        pilot-facts.json (facts -> segments -> hover, one
                        source); fixtures have positive+adversarial incl. the
                        rootless-particle and shared-root-distinct-lexeme
                        guards
- packet_presence       the 8 TP-CURR packets exist (deep validation is
                        tools/validate_task_packets.py, run on these paths)

Usage:
    python tools/validate_curriculum_l1l6.py                # all checks
    python tools/validate_curriculum_l1l6.py --pilot-only
    python tools/validate_curriculum_l1l6.py --write-pilot-projection
    python tools/validate_curriculum_l1l6.py --source-dir DIR   # + builder --check
    python tools/validate_curriculum_l1l6.py --self-test    # red-first mutations

Stdlib only; read-only except --write-pilot-projection (pilot/projection.json).
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

LEDGER_STATUSES = frozenset({
    "repository-certified", "source-supported-not-executable",
    "pedagogical-simplification", "analysis-dependent", "school-dependent",
    "candidate-requiring-review", "contradicted-by-repository-authority",
    "unsafe-for-automatic-projection",
})
CROSSWALK_STATES = frozenset({
    "executable_and_genuinely_consumed", "fixture_only", "documentary",
    "candidate", "missing", "contradicted", "unsafe_to_generalize",
})
OWNER_CLASSES = frozenset({"root", "pattern_augment", "clitic", "inflection"})
COLOUR_BY_OWNER = {
    "root": "seg.candidate.root",
    "pattern_augment": "seg.candidate.pattern",
    "clitic": "seg.candidate.clitic",
    "inflection": "seg.candidate.inflection",
}
PACKET_IDS = (
    "TP-CURR-ROOTPATTERN-PROMOTION", "TP-CURR-DERIVATIVE-LESSONS",
    "TP-CURR-MISTAKES-TO-FIXTURES", "TP-CURR-GOVERNANCE-FIXTURES",
    "TP-CURR-PARTICLE-FUNCTION-INVENTORY", "TP-CURR-HIDDEN-STRUCTURE",
    "TP-CURR-TUTOR-METHOD-ROUTING", "TP-CURR-QUIZ-KEY-REVIEW",
)
SERVER_PATH_RE = re.compile(
    r"(?:/var/www|/srv/|/home/[a-z]|/etc/|[A-Za-z]:\\\\|[A-Za-z]:\\)")
AR_WORD_RE = re.compile(r"[؀-ۿ][؀-ۿـً-ْٰ]*")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PROSE_RUN_LIMIT = 12  # >= this many consecutive Arabic words on a line = prose


def _jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_context():
    """Load every artifact into one dict; missing files -> hard error."""
    ctx = {}
    ctx["manifest"] = _jsonl(BASE / "custody" / "source-manifest.jsonl")
    ctx["levels"] = json.loads((BASE / "registry" / "levels.json").read_text(encoding="utf-8"))["levels"]
    ctx["modules"] = _jsonl(BASE / "registry" / "modules.jsonl")
    ctx["lessons"] = _jsonl(BASE / "registry" / "lessons.jsonl")
    ctx["concepts"] = _jsonl(BASE / "graph" / "concepts.jsonl")
    ctx["edges"] = _jsonl(BASE / "graph" / "concept-edges.jsonl")
    ctx["classes"] = json.loads((BASE / "eval-separation" / "material-classes.json").read_text(encoding="utf-8"))
    ctx["xwalk"] = (_jsonl(BASE / "crosswalk" / "sarf-crosswalk.jsonl")
                    + _jsonl(BASE / "crosswalk" / "nahw-crosswalk.jsonl"))
    ctx["ledger"] = _jsonl(BASE / "ledger" / "claim-ledger.jsonl")
    ctx["families"] = _jsonl(BASE / "ledger" / "claim-families.jsonl")
    ctx["guards"] = _jsonl(BASE / "ledger" / "overgeneralization-guards.jsonl")
    ctx["links"] = _jsonl(BASE / "links" / "pvn-candidate-links.jsonl")
    ctx["units"] = _jsonl(BASE / "units" / "instructional-units.jsonl")
    ctx["unit_deps"] = _jsonl(BASE / "units" / "unit-dependencies.jsonl")
    ctx["facts"] = json.loads((BASE / "pilot" / "pilot-facts.json").read_text(encoding="utf-8"))
    ctx["fixtures"] = _jsonl(BASE / "pilot" / "fixtures.jsonl")
    proj = BASE / "pilot" / "projection.json"
    ctx["projection_bytes"] = proj.read_bytes() if proj.exists() else None
    # every subtree file's text, for the leakage scan
    ctx["files"] = {
        str(p.relative_to(ROOT)).replace("\\", "/"): p.read_text(encoding="utf-8")
        for p in sorted(BASE.rglob("*")) if p.is_file()
    }
    return ctx


# ---------------------------------------------------------------- projection
def derive_projection(facts):
    """Facts -> (segments, hover), both from the SAME record. Deterministic."""
    tokens_out = []
    for tok in facts["tokens"]:
        segments = []
        cur = None
        for letter in tok["letters"]:
            owner = letter["owner"]
            if cur is None or cur["owner"] != owner:
                cur = {"colour_class": COLOUR_BY_OWNER[owner],
                       "letters": [], "owner": owner}
                segments.append(cur)
            cur["letters"].append(letter["letter"])
        hover = []
        for i, seg in enumerate(segments):
            details = [l["owner_detail"] for l in tok["letters"]
                       if l["owner"] == seg["owner"]]
            hover.append({
                "explanation_key": "%s:%s" % (seg["owner"], "+".join(sorted(set(details)))),
                "letters": seg["letters"],
                "segment_index": i,
            })
        case = tok["analysis"].get("case_vowel") or {}
        if case.get("display") == "hover_only":
            hover.append({"explanation_key": "case_vowel:%s" % case.get("value"),
                          "letters": [], "segment_index": None})
        tokens_out.append({"hover": hover, "segments": segments,
                           "surface": tok["surface"], "token_id": tok["token_id"]})
    return {"schema": "curriculum.l1l6_pilot_projection.v1",
            "compiled_from": "curriculum/l1l6/pilot/pilot-facts.json",
            "compiler": "tools/validate_curriculum_l1l6.py derive_projection",
            "status": "candidate", "tokens": tokens_out}


def projection_bytes(facts):
    return (json.dumps(derive_projection(facts), ensure_ascii=False, indent=2,
                       sort_keys=True) + "\n").encode("utf-8")


# ------------------------------------------------------------------- checks
def check_manifest_shape(ctx, errors):
    seen = set()
    for r in ctx["manifest"]:
        fid = r.get("file_id")
        if fid in seen:
            errors.append("manifest_shape: duplicate file_id %r" % fid)
        seen.add(fid)
        if not SHA_RE.match(r.get("sha256") or ""):
            errors.append("manifest_shape: %s bad sha256" % fid)
        if r.get("custody_status") != "private_source_custody_metadata_only":
            errors.append("manifest_shape: %s custody_status drifted" % fid)
        if r.get("kind") == "lesson" and not isinstance(r.get("counts"), dict):
            errors.append("manifest_shape: %s lesson missing counts" % fid)


def check_registry_consistency(ctx, errors):
    lesson_ids = {l["lesson_id"] for l in ctx["lessons"]}
    manifest_ids = {m["file_id"] for m in ctx["manifest"]}
    concept_ids = {c["concept_id"] for c in ctx["concepts"]}
    for lv in ctx["levels"]:
        actual = sum(1 for l in ctx["lessons"] if l["level_id"] == lv["level_id"])
        if actual != lv["actual_lessons"]:
            errors.append("registry_consistency: %s actual_lessons %d != rows %d"
                          % (lv["level_id"], lv["actual_lessons"], actual))
        if not lv.get("declaration_matches_actual"):
            errors.append("registry_consistency: %s declaration mismatch recorded"
                          % lv["level_id"])
    for m in ctx["modules"]:
        for lid in m["lesson_ids"]:
            if lid not in lesson_ids:
                errors.append("registry_consistency: module %s cites missing lesson %s"
                              % (m["module_id"], lid))
    for l in ctx["lessons"]:
        if l["source_file_id"] not in manifest_ids:
            errors.append("registry_consistency: %s source_file_id unresolved" % l["lesson_id"])
        for cid in l["concept_ids"]:
            if cid not in concept_ids:
                errors.append("registry_consistency: %s cites missing concept %s"
                              % (l["lesson_id"], cid))


def check_graph_integrity(ctx, errors):
    concept_ids = {c["concept_id"] for c in ctx["concepts"]}
    lesson_ids = {l["lesson_id"] for l in ctx["lessons"]}
    nodes = concept_ids | lesson_ids
    if len(concept_ids) != len(ctx["concepts"]):
        errors.append("graph_integrity: duplicate concept_id")
    seen_edges = set()
    adj = {}
    for e in ctx["edges"]:
        eid = e.get("edge_id")
        if eid in seen_edges:
            errors.append("graph_integrity: duplicate edge_id %r" % eid)
        seen_edges.add(eid)
        if e["from"] not in nodes or e["to"] not in nodes:
            errors.append("graph_integrity: edge %s has unresolved endpoint" % eid)
            continue
        adj.setdefault(e["from"], []).append(e["to"])
    state = {}

    def dfs(n):
        state[n] = 1
        for m in adj.get(n, ()):  # iterative would be safer; depth is bounded
            if state.get(m) == 1:
                return True
            if state.get(m) is None and dfs(m):
                return True
        state[n] = 2
        return False

    sys.setrecursionlimit(10000)
    for n in list(adj):
        if state.get(n) is None and dfs(n):
            errors.append("graph_integrity: prerequisite cycle reachable from %s" % n)
            break


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(k)
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def check_nfc(ctx, errors):
    for name in ("manifest", "modules", "lessons", "concepts", "edges",
                 "ledger", "guards", "links", "xwalk", "facts", "fixtures"):
        for s in _walk_strings(ctx[name]):
            if unicodedata.normalize("NFC", s) != s:
                errors.append("nfc_normalization: non-NFC string in %s: %r"
                              % (name, s[:40]))
                return


def check_crosswalk_evidence(ctx, errors):
    packet_dirs = (BASE / "packets", ROOT / "qamus" / "task-packets")
    seen = set()
    for r in ctx["xwalk"]:
        rid = r.get("row_id")
        if rid in seen:
            errors.append("crosswalk_evidence: duplicate row_id %r" % rid)
        seen.add(rid)
        if r.get("repo_state") not in CROSSWALK_STATES:
            errors.append("crosswalk_evidence: %s repo_state %r not in closed vocab"
                          % (rid, r.get("repo_state")))
        for p in r.get("repo_evidence") or []:
            if not (ROOT / p).exists():
                errors.append("crosswalk_evidence: %s cites missing path %s" % (rid, p))
        bp = r.get("backprop_packet")
        if bp and not any((d / (bp + ".json")).exists() for d in packet_dirs):
            errors.append("crosswalk_evidence: %s cites missing packet %s" % (rid, bp))


def check_ledger_qualification(ctx, errors):
    claim_ids = set()
    for c in ctx["ledger"]:
        cid = c.get("claim_id")
        if cid in claim_ids:
            errors.append("ledger_qualification: duplicate claim_id %r" % cid)
        claim_ids.add(cid)
        if c.get("status") not in LEDGER_STATUSES:
            errors.append("ledger_qualification: %s status %r not in closed vocab"
                          % (cid, c.get("status")))
        if c.get("status") == "repository-certified":
            errors.append("ledger_qualification: %s claims repository-certified — "
                          "this subtree may not assert certification" % cid)
    for g in ctx["guards"]:
        for cid in g.get("ledger_claims") or []:
            if cid not in claim_ids:
                errors.append("ledger_qualification: guard %s cites missing claim %s"
                              % (g.get("guard_id"), cid))
    # source-locator fidelity: every claim's lesson_id must resolve to a real
    # registry lesson (no wildcards) and its manifest_file_id to a real
    # manifest row; "corpus-wide" is the only allowed non-lesson scope
    lesson_ids = {l["lesson_id"] for l in ctx["lessons"]}
    manifest_ids = {m["file_id"] for m in ctx["manifest"]}
    for c in ctx["ledger"]:
        ref = c.get("source_ref") or {}
        lid = ref.get("lesson_id")
        if lid != "corpus-wide" and lid not in lesson_ids:
            errors.append("ledger_qualification: %s source_ref lesson_id %r "
                          "does not resolve (wildcards forbidden)"
                          % (c.get("claim_id"), lid))
        fid = ref.get("manifest_file_id")
        if fid is not None and fid not in manifest_ids:
            errors.append("ledger_qualification: %s manifest_file_id %r "
                          "unresolved" % (c.get("claim_id"), fid))
    # claim families: same closed vocabulary, unit-resolvable family field,
    # resolvable lesson_refs, zero certification
    unit_ids = {u["unit_id"] for u in ctx["units"]}
    seen_cf = set()
    for c in ctx["families"]:
        cid = c.get("claim_id")
        if cid in seen_cf:
            errors.append("ledger_qualification: duplicate family claim_id %r" % cid)
        seen_cf.add(cid)
        if c.get("status") not in LEDGER_STATUSES:
            errors.append("ledger_qualification: %s status %r not in closed vocab"
                          % (cid, c.get("status")))
        if c.get("status") == "repository-certified":
            errors.append("ledger_qualification: %s claims repository-certified" % cid)
        if c.get("family") not in unit_ids:
            errors.append("ledger_qualification: %s family %r is not an "
                          "instructional unit" % (cid, c.get("family")))
        for lid in (c.get("source_scope") or {}).get("lesson_refs") or []:
            if lid not in lesson_ids:
                errors.append("ledger_qualification: %s lesson_ref %r unresolved"
                              % (cid, lid))
    # every unit must have a claim family (the substantive-extraction floor)
    covered = {c.get("family") for c in ctx["families"]}
    for uid in sorted(unit_ids - covered):
        errors.append("ledger_qualification: unit %s has no claim family" % uid)


def check_links_candidacy(ctx, errors):
    for r in ctx["links"]:
        if r.get("status") != "candidate":
            errors.append("links_candidacy: %s status %r != candidate"
                          % (r.get("link_id"), r.get("status")))
        if r.get("target_kind") == "p_entry":
            for t in r.get("targets") or []:
                if not re.fullmatch(r"p(0\d\d|100)", t):
                    errors.append("links_candidacy: %s bad p-key %r"
                                  % (r.get("link_id"), t))


def check_material_classes(ctx, errors):
    quiz_total = sum(l["counts"]["quiz_questions"] for l in ctx["lessons"])
    declared = ctx["classes"]["classes"]["questions_without_verified_answer_keys"]["count"]
    if quiz_total != declared:
        errors.append("material_classes: quiz census %d != registry total %d"
                      % (declared, quiz_total))
    held = ctx["classes"]["classes"]["genuinely_held_out_evaluation_material"]
    if held.get("count") != 0:
        errors.append("material_classes: held-out count must be 0 (none exists "
                      "in this corpus); nonzero requires new evidence")


def check_leakage(ctx, errors):
    for rel, text in ctx["files"].items():
        if SERVER_PATH_RE.search(text):
            errors.append("leakage_scan: %s contains a server/absolute path" % rel)
        if "informed_by" in text and "packets" not in rel:
            errors.append("leakage_scan: %s leaks informed_by" % rel)
        # prose heuristic: for JSON artifacts the unit is a string VALUE (a
        # JSONL line aggregates many short metadata fields); for prose files
        # the unit is a line
        if rel.endswith((".json", ".jsonl")):
            units = []
            try:
                if rel.endswith(".jsonl"):
                    for ln in text.splitlines():
                        if ln.strip():
                            units.extend(_walk_strings(json.loads(ln)))
                else:
                    units = list(_walk_strings(json.loads(text)))
            except ValueError:
                units = text.splitlines()
        else:
            units = text.splitlines()
        for unit in units:
            if len(AR_WORD_RE.findall(unit)) >= PROSE_RUN_LIMIT:
                errors.append("leakage_scan: %s has a %d+-word Arabic prose run "
                              "(source-prose heuristic)" % (rel, PROSE_RUN_LIMIT))
                break


def check_no_certification(ctx, errors):
    for rel, text in ctx["files"].items():
        if '"status": "certified"' in text or "'status': 'certified'" in text:
            errors.append("no_certification: %s declares a certified status" % rel)
    if ctx["facts"].get("status") != "candidate":
        errors.append("no_certification: pilot facts status must be candidate")


def check_pilot_parity(ctx, errors):
    facts = ctx["facts"]
    for tok in facts.get("tokens", []):
        tid = tok.get("token_id")
        letters = tok.get("letters", [])
        bare = tok.get("surface_bare_letters", [])
        if [l["letter"] for l in letters] != bare:
            errors.append("pilot_parity: %s letters[] disagrees with "
                          "surface_bare_letters" % tid)
        for l in letters:
            if l.get("owner") not in OWNER_CLASSES:
                errors.append("pilot_parity: %s letter %r owner %r invalid"
                              % (tid, l.get("letter"), l.get("owner")))
        if len({l["index"] for l in letters}) != len(letters):
            errors.append("pilot_parity: %s duplicate letter index (a letter "
                          "owned twice)" % tid)
    if ctx["projection_bytes"] is None:
        errors.append("pilot_parity: pilot/projection.json missing "
                      "(--write-pilot-projection)")
    elif ctx["projection_bytes"] != projection_bytes(facts):
        errors.append("pilot_parity: projection.json differs from a "
                      "recompilation of pilot-facts.json — facts and "
                      "projections have diverged")
    classes = {f.get("class") for f in ctx["fixtures"]}
    if not {"positive", "adversarial"} <= classes:
        errors.append("pilot_parity: fixtures need >=1 positive and >=1 adversarial")
    if not any(f.get("expected", {}).get("root") is None for f in ctx["fixtures"]):
        errors.append("pilot_parity: rootless-particle adversarial fixture missing")
    if not any("distinct_lexeme_from" in f.get("expected", {}) for f in ctx["fixtures"]):
        errors.append("pilot_parity: shared-root-distinct-lexeme fixture missing")
    for b in facts.get("boundary_records", []):
        for w in b.get("words", []):
            if not w.get("distinct_lexeme") or w.get("gloss_scope") != "none_committed":
                errors.append("pilot_parity: boundary record %s word %s must stay "
                              "distinct_lexeme + none_committed (og-1)"
                              % (b.get("record_id"), w.get("surface")))


UNIT_REQUIRED_FIELDS = (
    "concept", "instructional_level", "recognition_criteria",
    "formation_or_decision_procedure", "positive_conditions",
    "negative_conditions", "exceptions", "contrasts",
    "common_learner_errors", "worked_analysis_stages",
    "required_evidence", "skill_surface", "rich_hover_component",
    "corpus_pvn_application", "backprop_destination", "concept_node_query",
    "explanation_ladder", "abstention_conditions", "transfer_fixtures",
    "promotion_state",
)


def check_units_semantic(ctx, errors):
    unit_ids = set()
    lesson_ids = {l["lesson_id"] for l in ctx["lessons"]}
    domain_counts = {}
    for c in ctx["concepts"]:
        domain_counts[c["domain"]] = domain_counts.get(c["domain"], 0) + 1
    for u in ctx["units"]:
        uid = u.get("unit_id")
        if uid in unit_ids:
            errors.append("units_semantic: duplicate unit_id %r" % uid)
        unit_ids.add(uid)
        if u.get("status") != "candidate":
            errors.append("units_semantic: %s status must be candidate" % uid)
        for f in UNIT_REQUIRED_FIELDS:
            v = u.get(f)
            if v is None or v == [] or v == "" or v == {}:
                errors.append("units_semantic: %s missing/empty field %r" % (uid, f))
        for lid in u.get("lesson_refs") or []:
            if lid not in lesson_ids:
                errors.append("units_semantic: %s lesson_ref %r unresolved" % (uid, lid))
        for path_field in ("skill_surface", "backprop_destination"):
            p = u.get(path_field)
            if isinstance(p, str) and p and not (ROOT / p).exists():
                # increments dirs may be added in the same PR; require existence
                errors.append("units_semantic: %s %s path %r missing" % (uid, path_field, p))
        cq = u.get("concept_node_query") or {}
        have = domain_counts.get(cq.get("domain"), 0)
        if have < cq.get("min_nodes", 0):
            errors.append("units_semantic: %s concept query domain %r has %d nodes "
                          "< declared minimum %d" % (uid, cq.get("domain"), have,
                                                     cq.get("min_nodes", 0)))
    # dependency edges resolve + acyclic
    adj = {}
    for d in ctx["unit_deps"]:
        if d["from"] not in unit_ids or d["to"] not in unit_ids:
            errors.append("units_semantic: dep %s endpoint unresolved" % d.get("edge_id"))
            continue
        adj.setdefault(d["from"], []).append(d["to"])
    state = {}

    def dfs(n):
        state[n] = 1
        for m in adj.get(n, ()):
            if state.get(m) == 1 or (state.get(m) is None and dfs(m)):
                return True
        state[n] = 2
        return False

    for n in list(adj):
        if state.get(n) is None and dfs(n):
            errors.append("units_semantic: unit dependency cycle reachable from %s" % n)
            break
    # every prerequisite_units entry must have a matching dep edge
    edge_pairs = {(d["from"], d["to"]) for d in ctx["unit_deps"]}
    for u in ctx["units"]:
        for p in u.get("prerequisite_units") or []:
            if (p, u["unit_id"]) not in edge_pairs:
                errors.append("units_semantic: %s prerequisite %s lacks a dep edge"
                              % (u["unit_id"], p))


def check_packet_presence(ctx, errors):
    for pid in PACKET_IDS:
        if not (BASE / "packets" / (pid + ".json")).exists():
            errors.append("packet_presence: %s.json missing" % pid)


def discovered_increments():
    """Discovery-based, never a hard-coded list (mirrors the consumer)."""
    inc_dir = BASE / "increments"
    if not inc_dir.exists():
        return []
    return sorted(p.name for p in inc_dir.iterdir()
                  if p.is_dir() and list(p.glob("unit-v*.json")))


INCREMENT_FILES = ("reference.md", "procedure.md", "staged-explanation.md",
                   "fixtures.jsonl", "hover-fields.json", "guards.json",
                   "unit-v1.json")
MIN_INCREMENTS = 6


def check_increments(ctx, errors):
    incs = discovered_increments()
    if len(incs) < MIN_INCREMENTS:
        errors.append("increments: discovery found %d < %d increments"
                      % (len(incs), MIN_INCREMENTS))
    for inc in incs:
        d = BASE / "increments" / inc
        for f in INCREMENT_FILES:
            if not (d / f).exists():
                errors.append("increments: %s missing %s" % (inc, f))
        fx_path = d / "fixtures.jsonl"
        if fx_path.exists():
            rows = _jsonl(fx_path)
            classes = {r.get("class") for r in rows}
            if not {"positive", "adversarial"} <= classes:
                errors.append("increments: %s fixtures need positive + adversarial"
                              % inc)
            if not any(r.get("class") == "abstention"
                       or r.get("expected", {}).get("decision") == "abstain"
                       for r in rows):
                errors.append("increments: %s has no abstention case" % inc)
            for r in rows:
                if r.get("status") != "candidate":
                    errors.append("increments: %s fixture %s not candidate"
                                  % (inc, r.get("fixture_id")))
        for jf in ("unit-v1.json", "unit-v2.json", "hover-fields.json",
                   "guards.json"):
            p = d / jf
            if p.exists():
                obj = json.loads(p.read_text(encoding="utf-8"))
                if obj.get("status") != "candidate":
                    errors.append("increments: %s/%s status must be candidate"
                                  % (inc, jf))


def check_flywheel_loop(ctx, errors):
    """The recorded loop must recompute byte-identically from the committed
    packs via the real consumer, and its failure set must match the record."""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import curriculum_unit_consumer as consumer
    except Exception as exc:  # noqa: BLE001
        errors.append("flywheel_loop: consumer unimportable (%s)" % exc)
        return
    finally:
        if str(ROOT / "tools") in sys.path:
            sys.path.remove(str(ROOT / "tools"))
    for run_file, unit_file, want_mism in (
            ("run-1-ownership-v1.json", "unit-v1.json", 2),
            ("run-2-ownership-v2.json", "unit-v2.json", 0)):
        p = BASE / "loop" / run_file
        if not p.exists():
            errors.append("flywheel_loop: %s missing" % run_file)
            continue
        rec = consumer.run("inc-ownership", unit_file)
        want = (json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n").encode("utf-8")
        if p.read_bytes() != want:
            errors.append("flywheel_loop: %s differs from a live recompute — "
                          "packs/consumer/record have drifted" % run_file)
        if rec["mismatches"] != want_mism:
            errors.append("flywheel_loop: %s expected %d mismatches, got %d"
                          % (run_file, want_mism, rec["mismatches"]))
    fr = BASE / "loop" / "failure-record.json"
    if not fr.exists():
        errors.append("flywheel_loop: failure-record.json missing")
    else:
        rec1 = json.loads((BASE / "loop" / "run-1-ownership-v1.json")
                          .read_text(encoding="utf-8"))
        failed = sorted(r["fixture_id"] for r in rec1["results"] if not r["match"])
        recorded = sorted(f["fixture_id"]
                          for f in json.loads(fr.read_text(encoding="utf-8"))["failures"])
        if failed != recorded:
            errors.append("flywheel_loop: failure-record fixtures %r != run-1 "
                          "failures %r" % (recorded, failed))
    if not (BASE / "loop" / "repair-note.md").exists():
        errors.append("flywheel_loop: repair-note.md missing")


def check_corpus_pilot(ctx, errors):
    """Envelopes recompute byte-identically from p007 authority via the real
    builder+consumer, preserve the unresolved host-ownership state, and mint
    no certification."""
    d = BASE / "corpus-pilot"
    if not (d / "README.md").exists():
        errors.append("corpus_pilot: README.md missing")
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import build_curriculum_corpus_pilot as builder
        files = builder.serialize(builder.build())
    except Exception as exc:  # noqa: BLE001
        errors.append("corpus_pilot: recompute failed (%s)" % exc)
        return
    finally:
        if str(ROOT / "tools") in sys.path:
            sys.path.remove(str(ROOT / "tools"))
    for path, data in sorted(files.items()):
        p = Path(path)
        if not p.exists():
            errors.append("corpus_pilot: %s missing" % p.name)
        elif p.read_bytes() != data:
            errors.append("corpus_pilot: %s differs from recompute (p007 "
                          "store / consumer / envelope drift)" % p.name)
    for name in ("envelope-2-34-5.json", "envelope-61-5-4.json"):
        p = d / name
        if not p.exists():
            continue
        env = json.loads(p.read_text(encoding="utf-8"))
        if env.get("status") != "candidate":
            errors.append("corpus_pilot: %s not candidate" % name)
        host = env.get("letter_ownership", {}).get("host", {})
        if host.get("consumer_verdict", {}).get("reason") != "no_root_evidence":
            errors.append("corpus_pilot: %s lost the preserved unresolved "
                          "host-ownership abstention" % name)
        ch = env.get("colour_and_hover", {})
        if not (ch.get("segment_hover_parity") and
                env.get("appearances", {}).get("single_hash_parity")):
            errors.append("corpus_pilot: %s parity flags not true" % name)
        for f in env.get("repository_authority", {}).get("typed_facts", []):
            if f.get("certification_status_verbatim") not in ("candidate", "certified"):
                errors.append("corpus_pilot: %s fact %s odd certification %r"
                              % (name, f.get("fact_id"),
                                 f.get("certification_status_verbatim")))


def check_precise_links(ctx, errors):
    p = BASE / "links" / "pvn-precise-links.jsonl"
    if not p.exists():
        errors.append("precise_links: file missing")
        return
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import build_curriculum_pvn_links as linkbuilder
        files = linkbuilder.serialize(linkbuilder.build())
    except Exception as exc:  # noqa: BLE001
        errors.append("precise_links: recompute failed (%s)" % exc)
        return
    finally:
        if str(ROOT / "tools") in sys.path:
            sys.path.remove(str(ROOT / "tools"))
    for path, data in sorted(files.items()):
        fp = Path(path)
        if not fp.exists() or fp.read_bytes() != data:
            errors.append("precise_links: %s differs from recompute" % fp.name)
    unit_ids = {u["unit_id"] for u in ctx["units"]}
    hover_keys = {}
    for inc in discovered_increments():
        hp = BASE / "increments" / inc / "hover-fields.json"
        if hp.exists():
            hover_keys[inc] = {f["key"] for f in
                               json.loads(hp.read_text(encoding="utf-8"))["fields"]}
    for r in _jsonl(p):
        lid = r.get("link_id")
        if r.get("status") != "candidate":
            errors.append("precise_links: %s not candidate" % lid)
        if not re.fullmatch(r"[0-9a-f]{12}", r.get("entry_id") or ""):
            errors.append("precise_links: %s entry_id not a store id" % lid)
        occ = r.get("occurrence_id")
        if occ is not None and not re.fullmatch(r"quran:\d+:\d+:\d+", occ):
            errors.append("precise_links: %s bad occurrence_id %r" % (lid, occ))
        if r.get("unit_ref") not in unit_ids:
            errors.append("precise_links: %s unit_ref unresolved" % lid)
        inc = r.get("increment")
        if inc in hover_keys and r.get("expected_hover_component") not in hover_keys[inc]:
            errors.append("precise_links: %s hover component %r not declared by %s"
                          % (lid, r.get("expected_hover_component"), inc))
        ev = r.get("promotion_evidence") or {}
        if not ev.get("needed_for_promotion"):
            errors.append("precise_links: %s missing promotion-evidence requirement" % lid)


ABSORPTION_STATES = frozenset({
    "metadata_only", "structurally_parsed", "semantically_qualified",
    "unitized", "skill_mapped", "fixture_mapped", "occurrence_grounded",
    "consumer_exercised", "backpropagated", "review_blocked",
    "not_applicable_with_reason"})


def check_absorption(ctx, errors):
    """Full-curriculum gates: 226 controlling rows, closed states, no empty
    next actions, zero unclassified sections, live recompute parity, queue
    rows carry real consumers + canaries."""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import build_curriculum_absorption as ab
        files = ab.serialize(*ab.build(ab.load()))
    except Exception as exc:  # noqa: BLE001
        errors.append("absorption: recompute failed (%s)" % exc)
        return
    finally:
        if str(ROOT / "tools") in sys.path:
            sys.path.remove(str(ROOT / "tools"))
    for path, data in sorted(files.items()):
        p = Path(path)
        if not p.exists():
            errors.append("absorption: %s missing (stale generation)" % p.name)
        elif p.read_bytes() != data:
            errors.append("absorption: %s differs from recompute (stale)" % p.name)
    led_p = BASE / "reports" / "absorption-ledger.jsonl"
    if not led_p.exists():
        return
    ledger = _jsonl(led_p)
    lesson_ids = {l["lesson_id"] for l in ctx["lessons"]}
    led_ids = {r["lesson_id"] for r in ledger}
    if len(ledger) != len(lesson_ids):
        errors.append("absorption: %d ledger rows != %d lessons"
                      % (len(ledger), len(lesson_ids)))
    for missing in sorted(lesson_ids - led_ids):
        errors.append("absorption: lesson %s has no ledger row (orphan)" % missing)
    for extra in sorted(led_ids - lesson_ids):
        errors.append("absorption: ledger row %s cites no source lesson" % extra)
    for r in ledger:
        if r.get("absorption_state") not in ABSORPTION_STATES:
            errors.append("absorption: %s state %r outside closed vocabulary"
                          % (r["lesson_id"], r.get("absorption_state")))
        if not r.get("next_action") and r.get("absorption_state") not in (
                "backpropagated", "not_applicable_with_reason"):
            errors.append("absorption: %s empty next_action" % r["lesson_id"])
    comp_p = BASE / "reports" / "section-completeness.json"
    if comp_p.exists():
        comp = json.loads(comp_p.read_text(encoding="utf-8"))
        if comp.get("unclassified", 1) != 0:
            errors.append("absorption: %d unclassified sections"
                          % comp.get("unclassified"))
        inv = _jsonl(BASE / "registry" / "section-inventory.jsonl")
        if comp.get("total_substantive_sections") != len(inv):
            errors.append("absorption: completeness total %s != inventory %d"
                          % (comp.get("total_substantive_sections"), len(inv)))
    qdir = BASE / "reports" / "queues"
    for qf in sorted(qdir.glob("q-*.jsonl")):
        for r in _jsonl(qf):
            if not r.get("target_consumer"):
                errors.append("absorption: queue row %s lacks a real consumer"
                              % r.get("row_id"))
            can = r.get("canaries") or {}
            if not (can.get("positive") and can.get("adversarial")):
                errors.append("absorption: queue row %s lacks canaries"
                              % r.get("row_id"))
            if not r.get("abstention_requirement"):
                errors.append("absorption: queue row %s lacks abstention req"
                              % r.get("row_id"))


ALL_CHECKS = (
    check_manifest_shape, check_registry_consistency, check_graph_integrity,
    check_nfc, check_crosswalk_evidence, check_ledger_qualification,
    check_links_candidacy, check_material_classes, check_leakage,
    check_no_certification, check_pilot_parity, check_packet_presence,
    check_units_semantic, check_increments, check_flywheel_loop,
    check_corpus_pilot, check_precise_links, check_absorption,
)
PILOT_CHECKS = (check_pilot_parity, check_no_certification)


def run_checks(ctx, checks):
    errors = []
    for c in checks:
        c(ctx, errors)
    return errors


# ---------------------------------------------------------------- self-test
def self_test():
    """Red-first: every named mutation must trip its named check."""
    base = load_context()
    if run_checks(base, ALL_CHECKS):
        print("self-test PRECONDITION FAIL: baseline is not green:")
        for e in run_checks(base, ALL_CHECKS):
            print("  " + e)
        return 1
    mutations = []

    def mut(name, needle, fn):
        c = copy.deepcopy(base)
        fn(c)
        errs = run_checks(c, ALL_CHECKS)
        ok = any(needle in e for e in errs)
        mutations.append((name, ok))
        if not ok:
            print("  mutation %s did NOT trip %r; errors=%r" % (name, needle, errs[:3]))

    mut("flip_letter_owner", "pilot_parity",
        lambda c: c["facts"]["tokens"][0]["letters"][2].update(owner="root"))
    mut("delete_projection", "pilot_parity",
        lambda c: c.update(projection_bytes=b"{}"))
    mut("certified_ledger_row", "ledger_qualification",
        lambda c: c["ledger"][0].update(status="repository-certified"))
    mut("resolved_link", "links_candidacy",
        lambda c: c["links"][0].update(status="resolved"))
    mut("dangling_edge", "graph_integrity",
        lambda c: c["edges"].append({"edge_id": "e-x", "kind": "curriculum_order_prerequisite",
                                     "from": "L1.M1.01", "to": "L9.M9.99"}))
    mut("cycle", "graph_integrity",
        lambda c: c["edges"].append({"edge_id": "e-cycle", "kind": "curriculum_order_prerequisite",
                                     "from": c["lessons"][-1]["lesson_id"],
                                     "to": c["lessons"][0]["lesson_id"]}))
    mut("server_path_leak", "leakage_scan",
        lambda c: c["files"].update({"curriculum/l1l6/x.md": "see /srv/secret"}))
    mut("arabic_prose_leak", "leakage_scan",
        lambda c: c["files"].update({"curriculum/l1l6/y.md":
                                     " ".join(["كلمة"] * PROSE_RUN_LIMIT)}))
    mut("dead_evidence_path", "crosswalk_evidence",
        lambda c: c["xwalk"][0].update(repo_evidence=["no/such/file.py"]))
    mut("quiz_census_drift", "material_classes",
        lambda c: c["classes"]["classes"]["questions_without_verified_answer_keys"].update(count=1))
    mut("non_nfc_string", "nfc_normalization",
        lambda c: c["concepts"][0].update(heading="أbad"))  # NFD-style seq
    mut("double_ownership_index", "pilot_parity",
        lambda c: c["facts"]["tokens"][0]["letters"][1].update(index=0))
    mut("bad_sha", "manifest_shape",
        lambda c: c["manifest"][0].update(sha256="zz"))
    mut("nonzero_heldout", "material_classes",
        lambda c: c["classes"]["classes"]["genuinely_held_out_evaluation_material"].update(count=5))
    mut("wildcard_source_ref", "ledger_qualification",
        lambda c: c["ledger"][0]["source_ref"].update(lesson_id="L6.M1.*"))
    mut("unit_dep_cycle", "units_semantic",
        lambda c: c["unit_deps"].append({"edge_id": "ud-x", "from": c["units"][-1]["unit_id"],
                                         "to": c["units"][0]["unit_id"],
                                         "kind": "capability_prerequisite"}
                                        ) if c["units"][0]["unit_id"] == "u-s01" else None)
    mut("unit_empty_field", "units_semantic",
        lambda c: c["units"][0].update(recognition_criteria=[]))
    mut("unit_overclaimed_population", "units_semantic",
        lambda c: c["units"][0]["concept_node_query"].update(min_nodes=99999))
    mut("family_certified_claim", "ledger_qualification",
        lambda c: c["families"][0].update(status="repository-certified"))
    mut("family_unit_uncovered", "ledger_qualification",
        lambda c: [c["families"].__setitem__(i, dict(r, family="u-s01"))
                   for i, r in enumerate(c["families"]) if r["family"] == "u-n12"])

    failed = [n for n, ok in mutations if not ok]
    print("self-test: %d/%d mutations tripped their checks"
          % (len(mutations) - len(failed), len(mutations)))
    if failed:
        print("SELF-TEST FAIL: " + ", ".join(failed))
        return 1
    print("SELF-TEST PASS")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--write-pilot-projection" in argv:
        facts = json.loads((BASE / "pilot" / "pilot-facts.json").read_text(encoding="utf-8"))
        out = BASE / "pilot" / "projection.json"
        out.write_bytes(projection_bytes(facts))
        print("wrote %s" % out.relative_to(ROOT))
        return 0
    ctx = load_context()
    checks = PILOT_CHECKS if "--pilot-only" in argv else ALL_CHECKS
    errors = run_checks(ctx, checks)
    if "--source-dir" in argv:
        src = argv[argv.index("--source-dir") + 1]
        rc = subprocess.call([sys.executable, str(ROOT / "tools" / "build_curriculum_l1l6.py"),
                              "--source-dir", src, "--check"])
        if rc != 0:
            errors.append("deterministic_regeneration: builder --check failed")
    for e in errors:
        print("FAIL " + e)
    if errors:
        print("CURRICULUM L1L6 VALIDATION FAIL (%d)" % len(errors))
        return 1
    print("CURRICULUM L1L6 VALIDATION PASS (%d checks)" % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
