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
- pilot_parity          letter partition = facts; letters[] AND
                        surface_bare_letters bound to the exact WRITTEN
                        surface (mutually consistent but wrong fails); hover
                        case vowel verified against the written final mark;
                        projection.json byte-equals recompilation from
                        pilot-facts.json; fixtures have positive+adversarial
                        incl. the rootless-particle and
                        shared-root-distinct-lexeme guards
- packet_presence       the 8 TP-CURR packets exist (deep validation is
                        tools/validate_task_packets.py, run on these paths)
- ma_payload_binding    payload-backed bridge rows preserve the committed
                        payload's exact surface/appearances/binding
- drill_candidates      semantic validation of every drill record + honest
                        counts (0 runtime-integrated, answer-visible)
- sol_ledgers           repair ledger / conformance matrix / adapter
                        manifest: current review identities, closed
                        ownership vocabulary only, no false closure

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
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

import kc_catalog

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
    r"(?:/var/www|/srv/|/home/[a-z]|/etc/|/Users/|\\\\[A-Za-z0-9]|[A-Za-z]:\\\\|[A-Za-z]:\\)")
# Windows paths written with FORWARD slashes evaded the scan above (Sol
# round 3): a drive letter is a single letter before the colon, so the
# lookbehind excludes URL schemes (https:/...), and forward-slash UNC must
# be followed by a host segment and a further slash, which excludes both
# "http://" (colon lookbehind) and arithmetic like "a // b".
WIN_FWD_PATH_RE = re.compile(
    r"(?:(?<![A-Za-z])[A-Za-z]:/|(?<![A-Za-z:])//[A-Za-z0-9][A-Za-z0-9._-]*/)")
IP_ADDR_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
AR_WORD_RE = re.compile(r"[؀-ۿ][؀-ۿـً-ْٰ]*")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PROSE_RUN_LIMIT = 12  # >= this many consecutive Arabic words on a line = prose
PILOT_HARAKAT_RE = re.compile("[ً-ْٰۖ-ۭـ]")
VOWEL_MARK_NAMES = {"َ": "fatha", "ِ": "kasra", "ُ": "damma"}
# the owner's closed ownership-split vocabulary (Sol checkpoint): the ONLY
# admissible state terms for the repair ledger and conformance matrix
OWNERSHIP_VOCAB = frozenset({
    "fable_branch_repair", "sol_adapter_required", "shared_integration_gate",
    "linguistic_review_blocked", "owner_or_scholar_blocked"})
NON_CLOSURE_STATUS_VOCAB = frozenset({
    "repaired_awaiting_sol_reverification",
    "integrated_awaiting_final_verification",
})
# review identity of the Sol fix-request round this branch repairs
# (github.com/theislampill/fusha/pull/136#issuecomment-5158892104)
R2_REVIEWED_HEAD = "eb51278c626ebe9b65b5a3e1be3a3895783e1233"
R2_REVIEW_TREE = "fd574a6f483995e5fce5a94368ea0b5fc7d37d14"
# round 3: the head Sol reviewed, and the main Sol reported clean alongside it
R3_REVIEWED_HEAD = "ce4c93e61a2e852f895d9b7e726675c0a2a40999"
R3_MAIN = "fc4a2607414a52fdd24089c8ec8f115a8f565479"


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
    ctx["consumer_bindings"] = _jsonl(
        BASE / "links" / "consumer-operationalization-bindings.jsonl")
    ctx["units"] = _jsonl(BASE / "units" / "instructional-units.jsonl")
    ctx["unit_deps"] = _jsonl(BASE / "units" / "unit-dependencies.jsonl")
    ctx["facts"] = json.loads((BASE / "pilot" / "pilot-facts.json").read_text(encoding="utf-8"))
    ctx["fixtures"] = _jsonl(BASE / "pilot" / "fixtures.jsonl")
    proj = BASE / "pilot" / "projection.json"
    ctx["projection_bytes"] = proj.read_bytes() if proj.exists() else None
    ctx["drills"] = _jsonl(BASE / "drills-candidates" / "drill-candidates.jsonl")
    ctx["drills_meta"] = json.loads(
        (BASE / "drills-candidates" / "drill-candidates.meta.json").read_text(encoding="utf-8"))
    ctx["repair_ledger"] = json.loads(
        (BASE / "reports" / "sol-review-repair-ledger.json").read_text(encoding="utf-8"))
    ctx["conformance"] = json.loads(
        (BASE / "reports" / "architecture-conformance-matrix.json").read_text(encoding="utf-8"))
    ctx["adapters"] = json.loads(
        (BASE / "reports" / "sol-adapter-manifest.json").read_text(encoding="utf-8"))
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
        if rid == "xs-04":
            derivation_rows = len(_jsonl(
                ROOT / "sarf" / "evals" / "derivational-template-carve-eval.jsonl"
            ))
            recorded = (r.get("consumer_evidence_counts") or {}).get(
                "derivational_template_carve_rows"
            )
            if recorded != derivation_rows:
                errors.append(
                    "crosswalk_evidence: xs-04 derivational row count %r != %d"
                    % (recorded, derivation_rows)
                )


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
        if WIN_FWD_PATH_RE.search(text):
            errors.append("leakage_scan: %s contains a forward-slash Windows "
                          "drive or UNC path" % rel)
        if IP_ADDR_RE.search(text):
            errors.append("leakage_scan: %s contains an IP address" % rel)
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
        # qualification records use the CONSECUTIVE-run custody rule (owned by
        # tools/validate_lesson_qualification.py, also gated in CI): their
        # strings legally contain many single Arabic terms with English
        # connectors, which the per-string total would misread as prose
        if "/qualification/" in rel:
            run_re = re.compile(
                r"[؀-ۿ][؀-ۿـً-ْٰ]*(?:[\s،,]+[؀-ۿ][؀-ۿـً-ْٰ]*)*")
            for unit in units:
                for m in run_re.finditer(unit):
                    if len(AR_WORD_RE.findall(m.group(0))) > 4:
                        errors.append("leakage_scan: %s Arabic run >4 "
                                      "consecutive words" % rel)
                        break
                else:
                    continue
                break
            continue
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


def _final_surface_vowel(surface):
    """The short-vowel name written on the LAST base letter of surface, or
    None when it carries no vowel mark (tanwin marks are not folded)."""
    groups = []
    for ch in surface:
        if PILOT_HARAKAT_RE.match(ch):
            if groups:
                groups[-1][1].append(ch)
        else:
            groups.append((ch, []))
    if not groups:
        return None
    for m in groups[-1][1]:
        if m in VOWEL_MARK_NAMES:
            return VOWEL_MARK_NAMES[m]
    return None


def check_pilot_parity(ctx, errors):
    facts = ctx["facts"]
    for tok in facts.get("tokens", []):
        tid = tok.get("token_id")
        letters = tok.get("letters", [])
        bare = tok.get("surface_bare_letters", [])
        if [l["letter"] for l in letters] != bare:
            errors.append("pilot_parity: %s letters[] disagrees with "
                          "surface_bare_letters" % tid)
        # WRITTEN-SURFACE binding (Sol fix-request round 2, finding 2):
        # mutual letters[]/surface_bare_letters consistency is not enough —
        # both must equal the bare letters of the exact written surface, and
        # a hover-claimed final case vowel must be the mark actually written
        # on the surface's final letter (or "none" when unpointed there)
        surface = tok.get("surface") or ""
        written_bare = [ch for ch in PILOT_HARAKAT_RE.sub("", surface)]
        if written_bare != bare:
            errors.append("pilot_parity: %s surface_bare_letters/letters[] "
                          "disagree with the WRITTEN surface (mutually "
                          "consistent but wrong fails too)" % tid)
        case = tok.get("analysis", {}).get("case_vowel") or {}
        claimed = str(case.get("value") or "").split("_")[0]
        if claimed:
            written_final = _final_surface_vowel(surface) or "none"
            if claimed != written_final:
                errors.append("pilot_parity: %s hover case vowel claims %r "
                              "but the written surface's final mark is %r "
                              "(false hover mark)" % (tid, claimed,
                                                      written_final))
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
    # generic loops: every manifest row recomputes live through the runner,
    # byte-matches its committed record, pins its defect count, ends green
    # with zero regressions, and claims no improvement class without consumer
    # evidence
    man_p = BASE / "loop" / "loops-manifest.json"
    if not man_p.exists():
        errors.append("flywheel_loop: loops-manifest.json missing")
        return
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import curriculum_flywheel_runner as runner
    except Exception as exc:  # noqa: BLE001
        errors.append("flywheel_loop: runner unimportable (%s)" % exc)
        return
    finally:
        if str(ROOT / "tools") in sys.path:
            sys.path.remove(str(ROOT / "tools"))
    manifest = json.loads(man_p.read_text(encoding="utf-8"))
    if len(manifest.get("loops", [])) < 4:
        errors.append("flywheel_loop: manifest has <4 loops (3 diverse families "
                      "+ ownership required)")
    families = {row.get("family", "") for row in manifest.get("loops", [])}
    if len(families) < 4:
        errors.append("flywheel_loop: loop families not diverse (need 4 distinct)")
    for row in manifest.get("loops", []):
        rec = runner.run_loop(row["loop"], row["increment"],
                              row["baseline_pack"], row["repaired_pack"])
        p = BASE / "loop" / row["loop"] / "loop-record.json"
        want = (json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n").encode("utf-8")
        if not p.exists() or p.read_bytes() != want:
            errors.append("flywheel_loop: %s record stale vs live recompute"
                          % row["loop"])
        if rec["run1"]["mismatches"] != row["expected_run1_mismatches"]:
            errors.append("flywheel_loop: %s defect count drifted (%d != %d)"
                          % (row["loop"], rec["run1"]["mismatches"],
                             row["expected_run1_mismatches"]))
        if rec["run2"]["mismatches"] != 0 or rec["regressions"]:
            errors.append("flywheel_loop: %s repair not green/regressed" % row["loop"])
        if ("fixture_harness_improvement" in rec["improvement_classes_verified"]
                and not rec["improvements"]):
            errors.append("flywheel_loop: %s claims harness improvement without "
                          "consumer evidence" % row["loop"])


def _canonical_loc_surface():
    idx = {}
    p = ROOT / "qamus" / "indexes" / "quran-loc-surface" / "index.jsonl"
    if p.exists():
        with p.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                idx[r["loc"]] = r["surface"]
    return idx


def check_corpus_pilot(ctx, errors):
    """Envelopes recompute byte-identically from p007 authority via the real
    builder+consumer, preserve the unresolved host-ownership state, bind
    every declared span to the exact written canonical surface, mint no
    certification, and PROVE fail-closed withholding under a synthetic
    revocation (live canary, Sol fix-request round 2, finding 5)."""
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
    canonical_idx = _canonical_loc_surface()
    import unicodedata as _ud
    dep_fids = set()
    for name in ("envelope-2-34-5.json", "envelope-61-5-4.json"):
        p = d / name
        if not p.exists():
            continue
        env = json.loads(p.read_text(encoding="utf-8"))
        if env.get("status") != "candidate" or env.get("withheld"):
            errors.append("corpus_pilot: %s not a live candidate envelope "
                          "(withheld or drifted status with all-valid "
                          "dependencies)" % name)
            continue
        dep_fids.update(env.get("certification_dependency", {})
                        .get("depends_on_fact_ids") or [])
        host = env.get("letter_ownership", {}).get("host", {})
        if host.get("consumer_verdict", {}).get("reason") != "no_root_evidence":
            errors.append("corpus_pilot: %s lost the preserved unresolved "
                          "host-ownership abstention" % name)
        ch = env.get("colour_and_hover", {})
        if not env.get("appearances", {}).get("single_hash_parity"):
            errors.append("corpus_pilot: %s appearance hash parity not true" % name)
        # WRITTEN-SURFACE binding (Sol fix-request round 2, finding 2): the
        # segment surfaces must concatenate to the exact envelope surface,
        # and the envelope surface must equal the canonical loc surface
        segs = ch.get("segments", [])
        if "".join(s.get("surface", "") for s in segs) != env.get("surface"):
            errors.append("corpus_pilot: %s segment surfaces do not "
                          "concatenate to the written surface" % name)
        # the envelope must DECLARE its canonical-surface binding accurately:
        # equality where the index agrees, an explicit reported divergence
        # (with ownership) where main's own artifacts encode it differently
        loc = (env.get("occurrence_id") or "").replace("quran:", "")
        canonical = canonical_idx.get(loc)
        csb = env.get("canonical_surface_binding") or {}
        verified = (canonical is not None
                    and _ud.normalize("NFC", canonical)
                    == _ud.normalize("NFC", env.get("surface") or ""))
        if csb.get("canonical_surface") != canonical \
                or bool(csb.get("verified")) != verified:
            errors.append("corpus_pilot: %s canonical-surface binding "
                          "misdeclared against the committed index" % name)
        if not verified and not (csb.get("divergence") or {}).get("ownership"):
            errors.append("corpus_pilot: %s diverges from the canonical loc "
                          "surface without a reported, owned divergence "
                          "(silent equality claim)" % name)
        # CANDIDATE span alignment (claim narrowed, Sol fix-request round 2,
        # finding 13): every hover binding must carry its aligned segment's
        # fact ids; uncovered segments must be REPORTED; and the envelope
        # must declare that this is alignment, not authoritative same-fact
        # identity
        if "candidate" not in (ch.get("alignment_basis") or "").lower() \
                or "sol" not in (ch.get("alignment_basis") or "").lower():
            errors.append("corpus_pilot: %s missing/overclaiming alignment "
                          "basis (must declare candidate alignment + Sol "
                          "adapter ownership of same-fact identity)" % name)
        seg_binds = {b["surface"]: set(b["fact_ids"])
                     for b in ch.get("segment_fact_bindings", [])}
        if not seg_binds:
            errors.append("corpus_pilot: %s missing segment fact bindings" % name)
        for hb in ch.get("hover_fact_bindings", []):
            segf = seg_binds.get(hb["component_surface"])
            if segf is None or not hb.get("traces_to_segment_facts")                     or not set(hb["fact_ids"]) <= segf or not hb["fact_ids"]:
                errors.append("corpus_pilot: %s hover component %r does not "
                              "carry its aligned segment's fact ids" %
                              (name, hb.get("component_surface")))
        claimed_cov = set(ch.get("covered_segments", []))
        actual_cov = {hb["component_surface"]
                      for hb in ch.get("hover_fact_bindings", [])
                      if hb.get("traces_to_segment_facts")}
        if claimed_cov != actual_cov:
            errors.append("corpus_pilot: %s covered-segment claim drifts from "
                          "hover bindings" % name)
        if set(ch.get("uncovered_segments", [])) !=                 set(seg_binds) - claimed_cov:
            errors.append("corpus_pilot: %s uncovered segments misreported" % name)
        cd = env.get("certification_dependency", {})
        if not cd.get("effective_states") or not cd.get("invalidation_rule"):
            errors.append("corpus_pilot: %s missing effective-certification "
                          "dependency block" % name)
        if cd.get("trail_valid") is not True or cd.get("trail_errors") != []:
            errors.append("corpus_pilot: %s did not consume a valid "
                          "authoritative certification trail" % name)
        if "TypedFactCertificationStore" not in (cd.get("basis") or ""):
            errors.append("corpus_pilot: %s uses a private certification "
                          "fold instead of the authoritative store" % name)
        for f in env.get("repository_authority", {}).get("typed_facts", []):
            if f.get("certification_status_verbatim") not in ("candidate", "certified"):
                errors.append("corpus_pilot: %s fact %s odd certification %r"
                              % (name, f.get("fact_id"),
                                 f.get("certification_status_verbatim")))
    # LIVE WITHHOLDING CANARY (Sol integration): copy the authoritative store,
    # call its real revoke() API for one occurrence-specific dependency, and
    # require only the affected envelope to withhold.  This proves both
    # invalidation and unrelated-occurrence isolation without synthetic
    # transition strings or a private state machine.
    if dep_fids:
        target = "quran:2:34:5"
        fact_id = "fact:p00slice:2_34_5:seg"
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            import build_curriculum_corpus_pilot as builder
            from certify_typed_fact import TypedFactCertificationStore
            with tempfile.TemporaryDirectory() as td:
                store_dir = Path(td) / "certification"
                shutil.copytree(
                    ROOT / "qamus" / "examples" / "p007-li-pilot" /
                    "certification", store_dir)
                TypedFactCertificationStore(store_dir).revoke(
                    fact_id,
                    actor="validator:curriculum-l1l6",
                    timestamp="2026-08-02T00:00:00Z",
                    reason="targeted downstream invalidation canary",
                )
                revoked = builder.build(certification_dir=store_dir)
        except Exception as exc:  # noqa: BLE001
            errors.append("corpus_pilot: withholding canary crashed (%s)" % exc)
            revoked = {}
        finally:
            if str(ROOT / "tools") in sys.path:
                sys.path.remove(str(ROOT / "tools"))
        for target, env in sorted(revoked.items()):
            affected = target == "quran:2:34:5"
            if affected and (not env.get("withheld")
                             or env.get("status") !=
                             "withheld_invalid_dependency"):
                errors.append("corpus_pilot: withholding canary FAILED — %s "
                              "did not withhold under authoritative revoke"
                              % target)
                continue
            if not affected and env.get("withheld"):
                errors.append("corpus_pilot: withholding canary FAILED — %s "
                              "was affected by an unrelated revocation" % target)
                continue
            if not affected:
                continue
            for banned in ("colour_and_hover", "website_envelope",
                           "appearances", "letter_ownership", "sarf_facts",
                           "nahw_facts", "reusable_lesson"):
                if banned in env:
                    errors.append("corpus_pilot: withholding canary FAILED — "
                                  "%s still emits %s while withheld"
                                  % (target, banned))
            if not env.get("withheld_artifact_classes"):
                errors.append("corpus_pilot: %s withheld form does not name "
                              "its withheld artifact classes" % target)


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
    "candidate_fixture_harness_exercised", "backpropagated", "review_blocked",
    "not_applicable_with_reason"})

CONSUMER_BINDING_SCHEMA = "curriculum.l1l6_consumer_operationalization_binding.v1"
# The current closed set of consumer planes a binding row may name.  Ṣarf and
# Naḥw remain distinct analytical destinations; neither may borrow the tutor's
# runtime evidence fields.
CONSUMER_PLANES = frozenset({
    "tutor_runtime", "nahw_analytical", "sarf_analytical",
})
_WORKER_HEAD_ANCESTOR_CACHE = {}


def _worker_head_is_ancestor(sha):
    """A binding's worker_head must be a REAL, resolvable commit that is an ancestor of the assembled HEAD —
    never a hard-coded, potentially-dangling pair. Memoized: only a handful of distinct heads appear across the
    manifest."""
    if sha in _WORKER_HEAD_ANCESTOR_CACHE:
        return _WORKER_HEAD_ANCESTOR_CACHE[sha]
    ok = False
    if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha):
        try:
            subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"], cwd=ROOT,
                           check=True, capture_output=True)
            subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=ROOT,
                           check=True, capture_output=True)
            ok = True
        except subprocess.CalledProcessError:
            ok = False
    _WORKER_HEAD_ANCESTOR_CACHE[sha] = ok
    return ok


REAL_CONTRIBUTION_STATUSES = {
    "operationalized_real_consumer",
    "already_operational_consumer_reverified",
}
TRAIN_B_EXPECTED_UNITS = {
    "operationalized_real_consumer": {
        "cu-bound-fa-function-discrimination",
        "cu-fa-function-and-mood-licensing",
    },
    "already_operational_consumer_reverified": {
        "cu-badal-vs-atf-bayan",
        "cu-clitic-pronoun-role-discriminator",
        "cu-la-negative-vs-prohibitive-discriminator",
        "cu-preposition-sense-discriminators",
        "cu-tanazu-governor-selection",
    },
    "pending_authoring": {
        "cu-badal-typology-discriminator",
        "cu-hal-licensing-conditions",
        "cu-ighra-tahdhir-licensing",
        "cu-ishtighal-fronted-noun-case",
        "cu-verb-particle-selection-licensing",
    },
}
TRAIN_C_EXPECTED_LESSONS = {
    "L1.M4.05", "L2.M5.01", "L4.M2.01",
    "L4.M2.04", "L4.M2.05", "L4.M5.04",
}
TRAIN_C_EXPECTED_UNITS = {
    "cu-attributive-agreement-licensing",
    "cu-atf-case-following",
    "cu-atf-particle-discriminator",
    "cu-badal-typology-discriminator",
    "cu-lakin-coordinator-vs-abrogator",
    "cu-waw-function-discriminator",
}
TRAIN_C_EXPECTED_KCS = {
    "kc-attributive-follower-licensing",
    "kc-badal-apposition-typology",
    "kc-coordination-particle-case-following",
    "kc-waw-function-accompaniment",
}
# Per-tranche exact binding-id set (F7). A bare `tranche_[0-9]{3}[a-d]?` regex match on
# consumer_train let ANY row under an undeclared tranche name validate, and let extra/duplicate
# rows under an ALREADY-declared tranche pass unnoticed once the old exact row-count guard was
# removed. Each tranche declares its own closed binding-id set here; a later slice adds its OWN
# entry rather than growing one global magic total that would block unrelated future slices.
TRANCHE_EXPECTED_BINDING_IDS = {
    "tranche_001a": frozenset({"l1l6-tranche-001a-foundational-orthography-analysis"}),
    "tranche_001b": frozenset({
        "l1l6-tranche-001b-foundational-script-runtime",
        "l1l6-tranche-001b-weak-root-voice-runtime",
        "l1l6-tranche-001b-derivation-template-runtime",
        "l1l6-tranche-001b-ma-context-runtime",
    }),
    "tranche_002a": frozenset({
        "l1l6-tranche-002a-template-classification-analysis",
    }),
}
# test_paths must name an actual test file, never a production/consumer module (F8).
_TEST_PATH_BASENAME_RE = re.compile(r"^test_.*\.py$")
# F8 residual: the basename check above proves nothing about CONTENT -- a production module could
# simply be renamed test_fake.py. Require real test structure: a unittest.TestCase, at least one
# `def test_` method, or one of this repo's own existing non-unittest self-test entrypoints (several
# tools here ship a red-first `_self_test()`/`self_test()` function or a `--self-test` CLI flag
# instead of a unittest.TestCase; both count, since both are genuine, already-used test-runner
# entrypoints -- but a bare renamed production file matches neither).
_TEST_CONTENT_RE = re.compile(
    r"unittest\.TestCase|^\s*def\s+test_\w|def\s+_?self_test\s*\(|--self-test", re.MULTILINE)


def _test_path_has_real_test_structure(text):
    """True when `text` (a candidate test_paths file's source) shows real test structure. Never
    derived from the filename alone (F8) -- a file merely NAMED like a test must fail this."""
    return bool(_TEST_CONTENT_RE.search(text or ""))


def check_consumer_operationalization_bindings(ctx, errors):
    """Validate exact B/C consumer proof without promoting candidate drills."""
    rows = ctx["consumer_bindings"]
    lesson_ids = {row["lesson_id"] for row in ctx["lessons"]}
    canonical_unit_ids = {
        row["unit_id"] for row in
        _jsonl(BASE / "canonical" / "canonical-units.jsonl")
    }
    runtime_rows = [
        row for path in sorted((ROOT / "curriculum" / "drills" / "keys")
                               .glob("*.jsonl"))
        for row in _jsonl(path)
    ]
    runtime_ids = {row["id"] for row in runtime_rows}
    kc_ids = {row["kc_id"] for row in kc_catalog.load_kc_catalog(ROOT)}
    candidate_rows = {
        row["drill_id"]: row for row in ctx["drills"]
    }
    seen_bindings, bound_runtime_ids, bound_candidate_ids = set(), set(), set()

    for row in rows:
        binding_id = row.get("binding_id")
        if binding_id in seen_bindings:
            errors.append("consumer_bindings: duplicate binding_id %r" % binding_id)
        seen_bindings.add(binding_id)
        if row.get("schema") != CONSUMER_BINDING_SCHEMA:
            errors.append("consumer_bindings: %s wrong schema" % binding_id)
        train = row.get("consumer_train")
        if train not in ("train_b", "train_c") and not re.fullmatch(
                r"tranche_[0-9]{3}[a-d]?", str(train)):
            errors.append("consumer_bindings: %s unapproved train %r" %
                          (binding_id, train))
        if not _worker_head_is_ancestor(row.get("worker_head")):
            errors.append("consumer_bindings: %s worker_head is not a real ancestor commit of HEAD" %
                          binding_id)
        plane = row.get("consumer_plane")
        if plane not in CONSUMER_PLANES:
            errors.append("consumer_bindings: %s consumer_plane %r outside the closed set %s" %
                          (binding_id, plane, sorted(CONSUMER_PLANES)))
        if row.get("binding_status") == "explicit":
            if plane == "tutor_runtime":
                if not row.get("runtime_item_ids") or not row.get("knowledge_component_ids"):
                    errors.append("consumer_bindings: %s explicit tutor_runtime row needs "
                                  "runtime_item_ids AND knowledge_component_ids" % binding_id)
            elif plane in {"nahw_analytical", "sarf_analytical"}:
                if (row.get("runtime_item_ids")
                        or row.get("knowledge_component_ids")
                        or row.get("candidate_drill_ids")):
                    errors.append("consumer_bindings: %s explicit %s row must carry no "
                                  "tutor runtime evidence" % (binding_id, plane))
        if row.get("public_projection_eligible") is not False:
            errors.append("consumer_bindings: %s public eligibility overclaim" %
                          binding_id)
        if row.get("candidate_status_preserved") is not True:
            errors.append("consumer_bindings: %s candidate boundary missing" %
                          binding_id)
        if "certified" in str(row.get("certification_posture", "")).lower():
            errors.append("consumer_bindings: %s certification overclaim" %
                          binding_id)
        for lesson_id in row.get("lesson_ids", []):
            if lesson_id not in lesson_ids:
                errors.append("consumer_bindings: %s unknown lesson %s" %
                              (binding_id, lesson_id))
        for unit_id in row.get("unit_ids", []):
            if unit_id not in canonical_unit_ids:
                errors.append("consumer_bindings: %s unknown unit %s" %
                              (binding_id, unit_id))

        status = row.get("binding_status")
        contribution = row.get("contribution_status")
        if status == "explicit":
            if contribution not in REAL_CONTRIBUTION_STATUSES:
                errors.append("consumer_bindings: %s explicit but not real" %
                              binding_id)
            for key in ("consumer_paths", "consumer_symbols", "test_paths"):
                if not row.get(key):
                    errors.append("consumer_bindings: %s missing %s" %
                                  (binding_id, key))
            for key in ("consumer_paths", "test_paths"):
                for path in row.get(key, []):
                    if not (ROOT / path).exists():
                        errors.append("consumer_bindings: %s missing path %s" %
                                      (binding_id, path))
            for path in row.get("test_paths", []):
                if not _TEST_PATH_BASENAME_RE.match(Path(path).name):
                    errors.append(
                        "consumer_bindings: %s test_paths entry %s is not a test file "
                        "(a production/consumer module cannot be counted as a test)" %
                        (binding_id, path))
                    continue
                full = ROOT / path
                if full.exists() and full.is_file():
                    try:
                        text = full.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        text = ""
                    if not _test_path_has_real_test_structure(text):
                        errors.append(
                            "consumer_bindings: %s test_paths entry %s is named like a test but "
                            "has no real test structure (no unittest.TestCase, def test_, or "
                            "self-test entrypoint) -- a production file merely renamed cannot be "
                            "counted as a test" % (binding_id, path))
        elif status == "pending_authoring":
            if contribution != "pending_authoring":
                errors.append("consumer_bindings: %s pending status mismatch" %
                              binding_id)
            if any(row.get(key) for key in (
                    "consumer_paths", "consumer_symbols", "test_paths",
                    "runtime_item_ids", "knowledge_component_ids",
                    "candidate_drill_ids")):
                errors.append("consumer_bindings: %s pending row claims a consumer" %
                              binding_id)
            for path in row.get("proposed_destination_paths", []):
                if not (ROOT / path).exists():
                    errors.append("consumer_bindings: %s missing proposed path %s" %
                                  (binding_id, path))
        else:
            errors.append("consumer_bindings: %s unknown binding status %r" %
                          (binding_id, status))

        for runtime_id in row.get("runtime_item_ids", []):
            if runtime_id not in runtime_ids:
                errors.append("consumer_bindings: %s missing runtime item %s" %
                              (binding_id, runtime_id))
            if runtime_id in bound_runtime_ids:
                errors.append("consumer_bindings: duplicate runtime item %s" %
                              runtime_id)
            bound_runtime_ids.add(runtime_id)
        for kc_id in row.get("knowledge_component_ids", []):
            if kc_id not in kc_ids:
                errors.append("consumer_bindings: %s missing KC %s" %
                              (binding_id, kc_id))
        for candidate_id in row.get("candidate_drill_ids", []):
            candidate = candidate_rows.get(candidate_id)
            if candidate is None:
                errors.append("consumer_bindings: %s missing candidate drill %s" %
                              (binding_id, candidate_id))
            elif candidate.get("status") != "candidate_not_runtime_integrated":
                errors.append("consumer_bindings: %s candidate %s was promoted" %
                              (binding_id, candidate_id))
            if candidate_id in bound_candidate_ids:
                errors.append("consumer_bindings: duplicate candidate drill %s" %
                              candidate_id)
            bound_candidate_ids.add(candidate_id)

    # F7: every tranche_NNN[a-d] train present must match a REGISTERED, exact binding-id set --
    # an unregistered tranche name, or a drift (a missing, extra, or duplicate row) from a
    # registered one, fails closed. This is scoped per tranche, so a later slice's registration
    # never has to touch (or risk drifting) an earlier slice's expected set.
    tranche_trains = sorted({
        row.get("consumer_train") for row in rows
        if re.fullmatch(r"tranche_[0-9]{3}[a-d]?", str(row.get("consumer_train")))
    })
    for train in tranche_trains:
        expected = TRANCHE_EXPECTED_BINDING_IDS.get(train)
        if expected is None:
            errors.append(
                "consumer_bindings: %s has no registered expected binding-id set "
                "(add an entry to TRANCHE_EXPECTED_BINDING_IDS)" % train)
            continue
        actual = {row["binding_id"] for row in rows if row.get("consumer_train") == train}
        if actual != expected:
            errors.append(
                "consumer_bindings: %s binding-id set drift: expected %s, got %s" %
                (train, sorted(expected), sorted(actual)))

    train_b = [row for row in rows if row.get("consumer_train") == "train_b"]
    train_c = [row for row in rows if row.get("consumer_train") == "train_c"]
    b_counts = {
        status: sum(row.get("contribution_status") == status for row in train_b)
        for status in REAL_CONTRIBUTION_STATUSES | {"pending_authoring"}
    }
    if b_counts != {
            "operationalized_real_consumer": 2,
            "already_operational_consumer_reverified": 5,
            "pending_authoring": 5}:
        errors.append("consumer_bindings: Train B posture counts drift %r" % b_counts)
    for status, expected_units in TRAIN_B_EXPECTED_UNITS.items():
        actual_units = {
            unit_id for row in train_b
            if row.get("contribution_status") == status
            for unit_id in row.get("unit_ids", [])
        }
        if actual_units != expected_units:
            errors.append("consumer_bindings: Train B %s units drift" % status)
    if len(train_c) != 4 or any(row.get("consumer_plane") != "tutor_runtime"
                                for row in train_c):
        errors.append("consumer_bindings: Train C runtime grouping drift")
    c_lessons = {lesson_id for row in train_c
                 for lesson_id in row.get("lesson_ids", [])}
    c_units = {unit_id for row in train_c for unit_id in row.get("unit_ids", [])}
    c_kcs = {kc_id for row in train_c
             for kc_id in row.get("knowledge_component_ids", [])}
    if c_lessons != TRAIN_C_EXPECTED_LESSONS:
        errors.append("consumer_bindings: Train C lesson set drift")
    if c_units != TRAIN_C_EXPECTED_UNITS:
        errors.append("consumer_bindings: Train C unit set drift")
    if c_kcs != TRAIN_C_EXPECTED_KCS:
        errors.append("consumer_bindings: Train C KC set drift")
    train_c_runtime_ids = {
        item for row in train_c for item in row.get("runtime_item_ids", [])
    }
    train_c_candidate_ids = {
        item for row in train_c for item in row.get("candidate_drill_ids", [])
    }
    if len(train_c_runtime_ids) != 27 or len(train_c_candidate_ids) != 27:
        errors.append("consumer_bindings: Train C runtime/candidate counts %d/%d != 27/27"
                      % (len(train_c_runtime_ids), len(train_c_candidate_ids)))
    if bound_runtime_ids & bound_candidate_ids:
        errors.append("consumer_bindings: candidate and runtime identities overlap")


def check_runtime_truth_consistency(readiness, derived_runtime, drill_meta,
                                    errors):
    """Validate generated consumer counts against their committed sources."""
    runtime = readiness.get("ordinary_tutor_runtime") or {}
    for key in (
            "drill_key_rows", "emittable_knowledge_components",
            "emittable_kc_ids", "indirectly_linked_lessons",
            "explicit_lesson_bindings", "explicit_canonical_unit_bindings"):
        if runtime.get(key) != derived_runtime.get(key):
            errors.append(
                "absorption: ordinary runtime %s %r != derived %r"
                % (key, runtime.get(key), derived_runtime.get(key))
            )
    if readiness.get("lessons_mapped_to_tutor_drills") != derived_runtime.get(
            "explicit_lesson_bindings"):
        errors.append(
            "absorption: explicit tutor lesson count %r != derived %r"
            % (readiness.get("lessons_mapped_to_tutor_drills"),
               derived_runtime.get("explicit_lesson_bindings"))
        )
    if readiness.get(
            "lessons_indirectly_linked_to_runtime_tutor_drills"
            ) != derived_runtime.get("indirectly_linked_lessons"):
        errors.append(
            "absorption: indirect tutor lesson count %r != derived %r"
            % (readiness.get(
                "lessons_indirectly_linked_to_runtime_tutor_drills"),
               derived_runtime.get("indirectly_linked_lessons"))
        )
    candidate = readiness.get("candidate_drill_packets") or {}
    for key in ("rows", "runtime_integrated"):
        if candidate.get(key) != drill_meta.get(key):
            errors.append(
                "absorption: candidate drill %s %r != derived %r"
                % (key, candidate.get(key), drill_meta.get(key))
            )
    if candidate.get("runtime_integrated") != 0:
        errors.append(
            "absorption: candidate drill packets must remain runtime_integrated=0"
        )
    if runtime.get("candidate_drill_specs_promoted", 0) != 0:
        errors.append("absorption: candidate drill specifications were promoted")


OPERATIONALIZATION_CLOSURE_DIMENSIONS = frozenset({
    "machine_execution",
    "runtime_misconceptions",
    "error_fixtures",
    "consumer_bindings",
    "occurrence_grounding",
})


def derive_operationalization_closure(unit_rows, lesson_unit_rows, errors):
    """Independently derive effective unit and lesson closure for validation."""
    closed_units = set()
    for row in unit_rows:
        unit_id = row.get("unit_id")
        dimensions = row.get("closure_dimensions") or {}
        dimension_names = set(dimensions)
        has_complete_dimensions = (
            dimension_names == OPERATIONALIZATION_CLOSURE_DIMENSIONS
        )
        expected_closed = has_complete_dimensions and all(
            dimensions[name].get("satisfied") is True
            for name in OPERATIONALIZATION_CLOSURE_DIMENSIONS
        )
        declared_closed = row.get("fully_operationalized") is True
        if declared_closed != expected_closed:
            errors.append(
                "absorption: unit %s declared closure %r != independent %r"
                % (unit_id, declared_closed, expected_closed)
            )
        if declared_closed and not has_complete_dimensions:
            errors.append(
                "absorption: unit %s closed without all closure dimensions"
                % unit_id
            )
            continue
        if not expected_closed:
            continue
        occurrence_parked = (
            dimensions["occurrence_grounding"].get("disposition") == "parked"
        )
        expected_prefix = (
            "all_non_occurrence_dimensions_satisfied_"
            "occurrence_grounding_parked:sha256:"
            if occurrence_parked
            else "all_required_dimensions_satisfied:sha256:"
        )
        if not str(row.get("fully_operationalized_basis", "")).startswith(
            expected_prefix
        ):
            errors.append(
                "absorption: unit %s closure basis does not match dimensions"
                % unit_id
            )
            continue
        closed_units.add(unit_id)

    closed_lessons = set()
    for row in lesson_unit_rows:
        lesson_id = row.get("lesson_id")
        unit_ids = set(row.get("units") or [])
        if unit_ids and unit_ids.issubset(closed_units):
            closed_lessons.add(lesson_id)
    return closed_units, closed_lessons


def check_absorption(ctx, errors):
    """Full-curriculum gates: 226 controlling rows, closed states, no empty
    next actions, zero unclassified sections, live recompute parity, queue
    rows carry real consumers + canaries."""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import build_curriculum_absorption as ab
        ab_ctx = ab.load()
        derived_runtime = ab.ordinary_tutor_runtime_truth(ab_ctx)
        files = ab.serialize(*ab.build(ab_ctx))
        drill_meta = json.loads(
            (BASE / "drills-candidates" / "drill-candidates.meta.json")
            .read_text(encoding="utf-8")
        )
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
    unit_rows = _jsonl(BASE / "canonical" / "unit-dispositions.jsonl")
    lesson_unit_rows = _jsonl(BASE / "canonical" / "lesson-unit-map.jsonl")
    _, independently_closed_lessons = derive_operationalization_closure(
        unit_rows, lesson_unit_rows, errors
    )
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
    ready_p = BASE / "reports" / "full-curriculum-readiness.json"
    if ready_p.exists():
        ready = json.loads(ready_p.read_text(encoding="utf-8"))
        check_runtime_truth_consistency(
            ready, derived_runtime, drill_meta, errors
        )
        ledger_closed_lesson_ids = {
            row["lesson_id"]
            for row in ledger
            if (row.get("consumer_operationalization") or {}).get(
                "fully_operationalized"
            ) is True
        }
        if ledger_closed_lesson_ids != independently_closed_lessons:
            errors.append(
                "absorption: ledger closed lessons %r != independent %r"
                % (
                    sorted(ledger_closed_lesson_ids),
                    sorted(independently_closed_lessons),
                )
            )
        independently_partial_lessons = {
            row["lesson_id"]
            for row in ledger
            if row["lesson_id"] not in independently_closed_lessons
            and bool(
                (row.get("consumer_operationalization") or {}).get(
                    "real_binding_ids"
                )
            )
        }
        if ready.get("lessons_fully_operationalized") != len(
            independently_closed_lessons
        ):
            errors.append(
                "absorption: fully operationalized lesson count %r != independent %d"
                % (
                    ready.get("lessons_fully_operationalized"),
                    len(independently_closed_lessons),
                )
            )
        if ready.get("lessons_partially_operationalized") != len(
            independently_partial_lessons
        ):
            errors.append(
                "absorption: partially operationalized lesson count %r != independent %d"
                % (
                    ready.get("lessons_partially_operationalized"),
                    len(independently_partial_lessons),
                )
            )
        if independently_closed_lessons and ready.get(
            "lessons_fully_operationalized_basis"
        ) != "all_mapped_canonical_units_fully_operationalized":
            errors.append(
                "absorption: fully operationalized lesson basis is not computed"
            )
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


def check_generated_planes(ctx, errors):
    """Capability matrix, occurrence bridge, learner projections and
    promotion bundles: live recompute byte-parity (stale = red), plus the
    single-source projection invariant and the every-increment-bundled
    floor."""
    for mod_name, label in (("build_capability_matrix", "capability matrix"),
                            ("build_curriculum_occurrence_bridge", "occurrence bridge"),
                            ("build_learner_projections", "learner projections"),
                            ("build_promotion_bundles", "promotion bundles")):
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            mod = __import__(mod_name)
            if mod_name == "build_curriculum_occurrence_bridge":
                files = mod.serialize(*mod.build())
            else:
                files = mod.serialize(mod.build())
        except Exception as exc:  # noqa: BLE001
            errors.append("generated_planes: %s recompute failed (%s)" % (label, exc))
            continue
        finally:
            if str(ROOT / "tools") in sys.path:
                sys.path.remove(str(ROOT / "tools"))
        for path, data in sorted(files.items()):
            p = Path(path)
            if not p.exists() or p.read_bytes() != data:
                errors.append("generated_planes: %s stale (%s)" % (label, p.name))
    # Sol repair 9: bundle registry rows must cover the CURRENT-MAIN
    # rule-registry field set field-for-field (no abbreviated shapes)
    main_row_p = ROOT / "qamus" / "skills" / "rule-registry.jsonl"
    if main_row_p.exists():
        with main_row_p.open(encoding="utf-8") as f:
            main_keys = set(json.loads(f.readline()).keys())
        for bp in sorted((BASE / "promotion").glob("*.bundle.json")):
            b = json.loads(bp.read_text(encoding="utf-8"))
            for row in b.get("candidate_registry_rows", []):
                missing = main_keys - set(row)
                if missing:
                    errors.append("generated_planes: %s registry row %s missing "
                                  "main-schema fields %s" % (bp.name,
                                  row.get("skill_rule_id"), sorted(missing)))
                if row.get("status") != "candidate":
                    errors.append("generated_planes: %s registry row not "
                                  "candidate" % bp.name)
    # every discovered increment must have a bundle
    for inc in discovered_increments():
        if not (BASE / "promotion" / ("%s.bundle.json" % inc)).exists():
            errors.append("generated_planes: increment %s has no promotion bundle" % inc)
    # projection single-source invariant: every projection carries fact_ref
    # and a technical view (the verbatim artifact) — no independent authoring
    pp = BASE / "projections" / "learner-projections.json"
    if pp.exists():
        obj = json.loads(pp.read_text(encoding="utf-8"))
        for pr in obj.get("projections", []):
            if not pr.get("fact_ref") or "technical" not in pr.get("views", {}):
                errors.append("generated_planes: projection missing fact_ref/"
                              "technical view (single-source invariant)")
                break
        # occurrence bridge wildcard gate
    ob = BASE / "reports" / "pvn-readiness.json"
    if ob.exists():
        if not json.loads(ob.read_text(encoding="utf-8")).get("wildcard_free"):
            errors.append("generated_planes: P/V/N links contain wildcards")


def check_freeze_planes(ctx, errors):
    """Freeze-round gates: unit dispositions + V/N grounding + misconception
    assets + unit projections recompute byte-identically; 166/166 closed
    dispositions; machine states are pack-backed; blockers carry causes;
    misconceptions fully routed."""
    for mod_name, label in (("build_unit_dispositions", "unit dispositions"),
                            ("build_vn_grounding", "vn grounding"),
                            ("build_misconception_assets", "misconception assets"),
                            ("build_pedagogy_projections", "unit projections")):
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            mod = __import__(mod_name)
            files = mod.serialize(*mod.build())
        except Exception as exc:  # noqa: BLE001
            errors.append("freeze_planes: %s recompute failed (%s)" % (label, exc))
            continue
        finally:
            if str(ROOT / "tools") in sys.path:
                sys.path.remove(str(ROOT / "tools"))
        for path, data in sorted(files.items()):
            p = Path(path)
            if not p.exists() or p.read_bytes() != data:
                errors.append("freeze_planes: %s stale (%s)" % (label, p.name))
    disp_p = BASE / "canonical" / "unit-dispositions.jsonl"
    if not disp_p.exists():
        return
    disp = _jsonl(disp_p)
    canon = _jsonl(BASE / "canonical" / "canonical-units.jsonl")
    if len(disp) != len(canon):
        errors.append("freeze_planes: %d dispositions != %d canonical units"
                      % (len(disp), len(canon)))
    incs = set(discovered_increments())
    for r in disp:
        if not r.get("strongest_state"):
            errors.append("freeze_planes: %s no strongest_state" % r["unit_id"])
        if "candidate_pack_harnessed" in r.get("states", []):
            if not r.get("machine_increments") or \
                    not set(r["machine_increments"]) <= incs:
                errors.append("freeze_planes: %s claims a machine consumer "
                              "without a discovered pack (invented claim)"
                              % r["unit_id"])
        for b in r.get("blockers", []):
            if not b.get("cause"):
                errors.append("freeze_planes: %s blocker without exact cause"
                              % r["unit_id"])
    reg = _jsonl(BASE / "misconceptions" / "misconception-registry.jsonl")
    unroutable = sum(1 for c in reg if not c.get("unit_routable")
                     and not c.get("routing_note"))
    if unroutable:
        errors.append("freeze_planes: %d misconception clusters unroutable "
                      "without a routing note" % unroutable)
    # SEMANTIC identity gate for V/N grounding: a byte-recompute cannot catch
    # a deterministic wrong binding, so every resolved sub-entry's exemplar
    # must NFC-equal one of the bound entry's own headword variants
    grow_p = BASE / "canonical" / "vn-grounding.jsonl"
    entries_p = ROOT / "qamus" / "data" / "current" / "entries.jsonl"
    if grow_p.exists() and entries_p.exists():
        import unicodedata as _ud
        heads = {}
        with entries_p.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                heads[r["id"]] = [
                    _ud.normalize("NFC", piece.strip()) for piece in
                    re.split(r"\s*/\s*", r.get("headword") or "") if piece]
        # universal fail-closed witness gate (Sol repair 1): every claimed
        # occurrence witness must be re-verifiable in the appearance universe
        # as an appearance of the SAME entry with selected:true and the exact
        # recorded surface; context appearances can never pass
        universe_idx = {}
        uni_p = ROOT / "qamus" / "lattice" / "example-ayah-universe.jsonl"
        if uni_p.exists():
            with uni_p.open(encoding="utf-8") as f:
                for line in f:
                    u = json.loads(line)
                    universe_idx[u["appearance_id"]] = u
        canonical_idx = _canonical_loc_surface()
        for row in _jsonl(grow_p):
            for sub in row.get("resolved", []):
                hw = _ud.normalize("NFC", sub["candidate_headword"])
                if hw not in heads.get(sub["entry_id"], []):
                    errors.append(
                        "freeze_planes: vn-grounding %s binds %r to entry %s "
                        "whose headword variants do not contain it (identity "
                        "violation)" % (row["unit_id"],
                                        sub["candidate_headword"],
                                        sub["entry_id"]))
                for w in sub.get("selected_witnesses", []):
                    u = universe_idx.get(w.get("appearance_id"))
                    if u is None:
                        errors.append("freeze_planes: vn-grounding %s witness "
                                      "%r not in the appearance universe"
                                      % (row["unit_id"], w.get("appearance_id")))
                        continue
                    if (u["entry_id"] != sub["entry_id"]
                            or not u.get("selected")
                            or "quran:" + (u.get("canonical_loc") or "")
                                != w.get("occurrence_id")
                            or u.get("displayed_surface") != w.get("surface")):
                        errors.append(
                            "freeze_planes: vn-grounding %s witness %s fails "
                            "same-entry/selected/surface re-verification "
                            "(context appearances never become entry "
                            "occurrences)" % (row["unit_id"],
                                              w.get("appearance_id")))
                    # CANONICAL-SURFACE re-verification (Sol fix-request
                    # round 2, finding 3): a witness may claim to ground a
                    # canonical occurrence ONLY when its card surface
                    # NFC-equals the canonical loc surface; diverging
                    # witnesses must be labelled card_display_only
                    loc = (w.get("occurrence_id") or "").replace("quran:", "")
                    canonical = canonical_idx.get(loc)
                    verified = (canonical is not None
                                and _ud.normalize("NFC", canonical)
                                == _ud.normalize("NFC", w.get("surface") or ""))
                    if bool(w.get("canonical_surface_verified")) != verified:
                        errors.append(
                            "freeze_planes: vn-grounding %s witness %s "
                            "canonical_surface verification flag is FALSE "
                            "for the committed canonical index (card "
                            "orthography must not claim canonical equality)"
                            % (row["unit_id"], w.get("appearance_id")))
                    want_scope = ("canonical_occurrence" if verified
                                  else "card_display_only")
                    if w.get("witness_scope") != want_scope:
                        errors.append(
                            "freeze_planes: vn-grounding %s witness %s scope "
                            "%r != required %r (canonical_surface gate)"
                            % (row["unit_id"], w.get("appearance_id"),
                               w.get("witness_scope"), want_scope))
                    if w.get("canonical_surface") != canonical:
                        errors.append(
                            "freeze_planes: vn-grounding %s witness %s "
                            "records a canonical_surface differing from the "
                            "index" % (row["unit_id"], w.get("appearance_id")))


def check_ma_payload_binding(ctx, errors):
    """Sol fix-request round 2, finding 4: payload-backed bridge rows (the
    two مَا canaries) must preserve the committed payload's EXACT surface,
    appearances and binding — degradation to surface:null / zero appearances
    is red. Every payload_binding is re-verified against the payload file."""
    bridge_p = BASE / "reports" / "occurrence-bridge.jsonl"
    if not bridge_p.exists():
        errors.append("ma_payload_binding: occurrence-bridge.jsonl missing")
        return
    rows = _jsonl(bridge_p)
    ma_occ_rows = [r for r in rows
                   if r.get("increment") == "inc-ma" and r.get("occurrence_id")]
    if len(ma_occ_rows) < 2:
        errors.append("ma_payload_binding: the two ma payload canary rows "
                      "are missing from the bridge")
    for r in rows:
        pb = r.get("payload_binding")
        if r in ma_occ_rows and not pb:
            errors.append("ma_payload_binding: %s lost its payload binding"
                          % r.get("bridge_id"))
            continue
        if not pb:
            continue
        pf = ROOT / pb.get("payload_file", "")
        if not pf.exists():
            errors.append("ma_payload_binding: %s cites missing payload %s"
                          % (r.get("bridge_id"), pb.get("payload_file")))
            continue
        pl = json.loads(pf.read_text(encoding="utf-8"))
        apps = pl["reverse_links"]["occurrence_to_appearances"]
        if r.get("surface") != pl["projection"]["surface"]:
            errors.append("ma_payload_binding: %s surface %r != payload "
                          "surface (degraded/drifted)" % (r.get("bridge_id"),
                                                          r.get("surface")))
        if pb.get("projection_hash") != pl["projection_hash"] \
                or pb.get("artifact_id") != pl["artifact_id"]:
            errors.append("ma_payload_binding: %s binding identity differs "
                          "from the payload" % r.get("bridge_id"))
        got = r.get("appearances", {})
        if got.get("rows") != apps or got.get("count") != len(apps) \
                or not got.get("count"):
            errors.append("ma_payload_binding: %s appearances degraded from "
                          "the payload's reverse links" % r.get("bridge_id"))
        if not r.get("required_nahw_facts"):
            errors.append("ma_payload_binding: %s lost the payload's "
                          "required-fact evidence refs" % r.get("bridge_id"))


def check_drill_candidates(ctx, errors):
    """Sol fix-request round 2, finding 8: SEMANTIC validation of every
    drill-candidate record (regeneration identity alone is insufficient) +
    the honest counts (0 runtime-integrated, answer-visible packets)."""
    rows = ctx["drills"]
    meta = ctx["drills_meta"]
    reg_ids = {c["misconception_id"] for c in
               _jsonl(BASE / "misconceptions" / "misconception-registry.jsonl")}
    canon_ids = {u["unit_id"] for u in
                 _jsonl(BASE / "canonical" / "canonical-units.jsonl")}
    caps = {"letter_ownership", "template_classification",
            "discriminator_table", "pattern_consistency", "licensing_table",
            "pedagogical_projection"} | set(discovered_increments())
    if meta.get("rows") != len(rows):
        errors.append("drill_candidates: meta rows %r != %d records"
                      % (meta.get("rows"), len(rows)))
    if meta.get("runtime_integrated") != 0:
        errors.append("drill_candidates: runtime_integrated must be 0 (the "
                      "honest count) — nothing here is tutor-runnable")
    if meta.get("answer_visibility") != "answer_visible_candidate_packets":
        errors.append("drill_candidates: meta must declare answer-visible "
                      "candidate packets")
    linked = sorted(canon_ids & {u for r in rows
                                 for u in r.get("unit_links", [])})
    if meta.get("canonical_units_with_candidates") != len(linked) \
            or meta.get("canonical_units_total") != len(canon_ids):
        errors.append("drill_candidates: units-with-candidates counts drift "
                      "from the records (%r/%r vs %d/%d)"
                      % (meta.get("canonical_units_with_candidates"),
                         meta.get("canonical_units_total"),
                         len(linked), len(canon_ids)))
    seen = set()
    required = ("prompt_specification", "expected_rubric", "explanation",
                "answer_leakage_posture", "abstention_behaviour",
                "intended_runtime_consumer", "adapter_requirement",
                "prerequisites", "difficulty_band")
    for r in rows:
        did = r.get("drill_id")
        if not (isinstance(did, str) and did.startswith("dr-")):
            errors.append("drill_candidates: bad drill_id %r" % did)
        if did in seen:
            errors.append("drill_candidates: duplicate drill_id %r" % did)
        seen.add(did)
        if r.get("status") != "candidate_not_runtime_integrated":
            errors.append("drill_candidates: %s status %r claims more than "
                          "candidacy" % (did, r.get("status")))
        if r.get("misconception_link") not in reg_ids:
            errors.append("drill_candidates: %s misconception_link %r "
                          "unresolved" % (did, r.get("misconception_link")))
        for u in r.get("unit_links", []):
            if u not in canon_ids:
                errors.append("drill_candidates: %s unit_link %r not a "
                              "canonical unit" % (did, u))
        for c in r.get("capability_link", []):
            if c not in caps:
                errors.append("drill_candidates: %s capability_link %r "
                              "unknown" % (did, c))
        for k in required:
            if not r.get(k):
                errors.append("drill_candidates: %s missing %s" % (did, k))
        if "NEVER usable as independent assessment" not in \
                (r.get("answer_leakage_posture") or ""):
            errors.append("drill_candidates: %s answer-visibility posture "
                          "weakened" % did)
        if "Sol" not in (r.get("adapter_requirement") or ""):
            errors.append("drill_candidates: %s adapter requirement lost "
                          "Sol ownership" % did)


def check_sol_ledgers(ctx, errors):
    """Sol fix-request round 2, finding 10: the repair ledger, conformance
    matrix and adapter manifest carry current review identities and ONLY the
    owner's closed ownership-split vocabulary; no false closure claims."""
    led = ctx["repair_ledger"]
    if led.get("reviewed_head") != R2_REVIEWED_HEAD:
        errors.append("sol_ledgers: repair ledger reviewed_head %r is not "
                      "the current reviewed head" % led.get("reviewed_head"))
    if (led.get("review_identity") or {}).get("review_tree") != R2_REVIEW_TREE:
        errors.append("sol_ledgers: repair ledger review_tree drifted")
    if "5158892104" not in json.dumps(led.get("review_identity", {})):
        errors.append("sol_ledgers: repair ledger not bound to the fix-"
                      "request comment")
    if not led.get("rows"):
        errors.append("sol_ledgers: repair ledger has no rows")
    if set(led.get("status_vocabulary") or []) != NON_CLOSURE_STATUS_VOCAB:
        errors.append("sol_ledgers: non-closure status vocabulary drifted")
    r3 = led.get("round_3") or {}
    if r3.get("reviewed_head") != R3_REVIEWED_HEAD:
        errors.append("sol_ledgers: round-3 reviewed_head %r is not the head "
                      "Sol reviewed" % r3.get("reviewed_head"))
    if r3.get("main_at_repair") != R3_MAIN:
        errors.append("sol_ledgers: round-3 main_at_repair drifted from the "
                      "main Sol reported")
    if len(r3.get("rows") or []) < 2:
        errors.append("sol_ledgers: round-3 must carry both named repairs")
    for r in list(led.get("rows", [])) + list(r3.get("rows") or []):
        if r.get("ownership") not in OWNERSHIP_VOCAB:
            errors.append("sol_ledgers: ledger row %r ownership %r outside "
                          "the owner's closed vocabulary"
                          % (r.get("finding", "?")[:40], r.get("ownership")))
        # Closed non-closure vocabulary: branch repairs await Sol
        # re-verification; integration work may be implemented while still
        # awaiting the final exact-tree review/harness. Neither state claims
        # merge readiness or linguistic certification.
        if r.get("status") not in NON_CLOSURE_STATUS_VOCAB:
            errors.append("sol_ledgers: ledger row %r status %r — closure "
                          "is Sol's call, rows may only await re-review"
                          % (r.get("finding", "?")[:40], r.get("status")))
        for k in ("finding", "repair", "acceptance", "red_canary"):
            if not r.get(k):
                errors.append("sol_ledgers: ledger row missing %s" % k)
    conf = ctx["conformance"]
    for r in conf.get("rows", []):
        if r.get("state") not in OWNERSHIP_VOCAB:
            errors.append("sol_ledgers: conformance row %r state %r outside "
                          "the owner's closed vocabulary"
                          % (r.get("subsystem"), r.get("state")))
        if "remaining_dependency" not in r:
            errors.append("sol_ledgers: conformance row %r lacks "
                          "remaining_dependency" % r.get("subsystem"))
    adp = ctx["adapters"]
    adapters = adp.get("adapters", [])
    if len(adapters) < 6:
        errors.append("sol_ledgers: adapter manifest has %d < 6 adapters"
                      % len(adapters))
    if adp.get("owner") != "sol":
        errors.append("sol_ledgers: adapter manifest must declare owner sol")
    for a in adapters:
        if not str(a.get("id", "")).startswith("adp-"):
            errors.append("sol_ledgers: adapter id %r malformed" % a.get("id"))
        for k in ("contract", "direction", "canaries", "acceptance"):
            if not a.get(k):
                errors.append("sol_ledgers: adapter %s missing %s"
                              % (a.get("id"), k))

    # Exact combined-tree consistency. Once the canonical certification
    # adapter is present, the historical R3-3 merge obligation must be
    # recorded as implemented (but still awaiting final verification), and
    # the conformance/summary surfaces may not reopen it as future work.
    by_id = {a.get("id"): a for a in adapters}
    cert_integrated = (by_id.get("adp-typed-fact-certification") or {}).get(
        "integration_status") == "implemented_in_sol_integration"
    if cert_integrated:
        r3_rows = [r for r in r3.get("rows", [])
                   if str(r.get("finding", "")).startswith("R3-3.")]
        if len(r3_rows) != 1 or r3_rows[0].get("status") != \
                "integrated_awaiting_final_verification":
            errors.append("sol_ledgers: integration resolution for R3-3 is "
                          "not recorded on the combined tree")
        elif any(s in json.dumps(r3_rows[0], ensure_ascii=False)
                 for s in ("NOT performed", "AT MERGE",
                           "reported_awaiting_merge_sequencing")):
            errors.append("sol_ledgers: integration resolution for R3-3 "
                          "still describes completed work as pending")

        conf_by_name = {r.get("subsystem"): r
                        for r in conf.get("rows", [])}
        p007_row = conf_by_name.get(
            "p007-derived planes (merge sequencing)") or {}
        if p007_row.get("remaining_dependency") != "none" or any(
                s in json.dumps(p007_row, ensure_ascii=False)
                for s in ("AT MERGE", "reported, not silently absorbed")):
            errors.append("sol_ledgers: integration resolution for p007 "
                          "derived planes is stale in the conformance matrix")
        learner_row = conf_by_name.get("Learner projections") or {}
        if learner_row.get("remaining_dependency") != "none":
            errors.append("sol_ledgers: integration resolution for the typed-"
                          "fact learner dependency is stale")
        if "sol_owned_not_touched" in led or not led.get(
                "sol_owned_integration_summary"):
            errors.append("sol_ledgers: integration resolution summary still "
                          "claims Sol-owned adapters were untouched")


ALL_CHECKS = (
    check_manifest_shape, check_registry_consistency, check_graph_integrity,
    check_nfc, check_crosswalk_evidence, check_ledger_qualification,
    check_links_candidacy, check_material_classes, check_leakage,
    check_no_certification, check_pilot_parity, check_packet_presence,
    check_units_semantic, check_increments, check_flywheel_loop,
    check_corpus_pilot, check_precise_links,
    check_consumer_operationalization_bindings, check_absorption,
    check_generated_planes, check_freeze_planes, check_ma_payload_binding,
    check_drill_candidates, check_sol_ledgers,
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
    # public-boundary canaries (Sol fix-request round 2, finding 12)
    mut("windows_drive_leak", "leakage_scan",
        lambda c: c["files"].update({"curriculum/l1l6/z1.md":
                                     "dump at C:" + "\\" + "secret"}))
    mut("unc_path_leak", "leakage_scan",
        lambda c: c["files"].update({"curriculum/l1l6/z2.md":
                                     "share " + "\\\\" + "srv1" + "\\" + "d"}))
    mut("macos_users_leak", "leakage_scan",
        lambda c: c["files"].update({"curriculum/l1l6/z3.md":
                                     "copy of /Users" + "/alice/notes"}))
    mut("ip_address_leak", "leakage_scan",
        lambda c: c["files"].update({"curriculum/l1l6/z4.md":
                                     "host 10.20.30.40 responded"}))
    # forward-slash Windows paths (Sol round 3): these evaded every scan.
    # The canary deliberately uses a neutral drive and directory: main's
    # RM-09 recurrence lint folds separators before matching its operator-
    # path needles, so a canary spelling a real operator path would trip
    # THAT gate on the merge tree (it did — this wording is the repair).
    mut("windows_drive_forward_slash_leak", "forward-slash Windows",
        lambda c: c["files"].update({"curriculum/l1l6/z5.md":
                                     "built in E:/opt/private-corpus/levels"}))
    mut("unc_forward_slash_leak", "forward-slash Windows",
        lambda c: c["files"].update({"curriculum/l1l6/z6.md":
                                     "corpus at //fileserver/share/levels"}))
    # and the benign forms must stay quiet (a scan that flags every URL is
    # not a boundary gate, it is noise)
    quiet = copy.deepcopy(base)
    quiet["files"].update({"curriculum/l1l6/z7.md":
                           "see https://example.org/a/b and a // b, ratio 3/4"})
    mutations.append(("forward_slash_no_false_positive",
                      not any("forward-slash" in e
                              for e in run_checks(quiet, ALL_CHECKS))))
    # written-surface binding canaries (finding 2)
    mut("wrong_letters_mutually_consistent", "WRITTEN surface",
        lambda c: (c["facts"]["tokens"][0]["letters"][3].update(letter="ص"),
                   c["facts"]["tokens"][0]["surface_bare_letters"]
                   .__setitem__(3, "ص")))
    mut("false_final_hover_mark", "false hover mark",
        lambda c: c["facts"]["tokens"][0]["analysis"]["case_vowel"]
        .update(value="kasra_forged_claim"))
    # drill-record semantic canaries (finding 8)
    mut("drill_runtime_claim", "drill_candidates",
        lambda c: c["drills_meta"].update(runtime_integrated=1))
    mut("drill_status_overclaim", "claims more than candidacy",
        lambda c: c["drills"][0].update(status="runtime_integrated"))
    mut("drill_unroutable", "unresolved",
        lambda c: c["drills"][0].update(misconception_link="mc-x999"))
    # ledger/matrix closed-vocabulary canaries (finding 10)
    mut("conformance_invented_state", "closed vocabulary",
        lambda c: c["conformance"]["rows"][0].update(state="fully_conformant"))
    mut("ledger_false_closure", "closure is Sol",
        lambda c: c["repair_ledger"]["rows"][0].update(status="complete"))
    mut("adapter_owner_drift", "owner sol",
        lambda c: c["adapters"].update(owner="fable"))
    mut("obsolete_merge_sequencing_status", "closure is Sol",
        lambda c: c["repair_ledger"]["round_3"]["rows"][0].update(
            status="reported_awaiting_merge_sequencing"))
    # Exact-tree integration truth: once the Sol adapters are present, the
    # shared merge-sequencing row and its conformance counterpart may not
    # continue describing regeneration as future work.
    mut("integrated_r3_reopened", "integration resolution",
        lambda c: c["repair_ledger"]["round_3"]["rows"][2].update(
            status="reported_awaiting_merge_sequencing"))
    mut("integrated_matrix_reopened", "integration resolution",
        lambda c: next(
            r for r in c["conformance"]["rows"]
            if r["subsystem"] == "p007-derived planes (merge sequencing)"
        ).update(remaining_dependency="regenerate AT MERGE"))
    mut("integrated_adapter_summary_reverted", "integration resolution",
        lambda c: c["repair_ledger"].update(
            sol_owned_not_touched="all Sol adapters remain untouched"))
    mut("family_unit_uncovered", "ledger_qualification",
        lambda c: [c["families"].__setitem__(i, dict(r, family="u-s01"))
                   for i, r in enumerate(c["families"]) if r["family"] == "u-n12"])
    # consumer-binding provenance canaries (Bounded Mechanical Findings 1/3/6): a fabricated/dangling worker_head
    # must never pass as real runtime evidence, a closed-vocabulary plane violation must be caught, and an
    # explicit tutor_runtime row that drops its runtime/KC evidence (or an explicit nahw_analytical row that
    # invents some) must both fail closed — restoring the top-level no-false-runtime-evidence assertion this
    # manifest's own check exists to make.
    mut("consumer_binding_worker_head_not_ancestor", "worker_head",
        lambda c: c["consumer_bindings"][0].update(worker_head="f" * 40))
    mut("consumer_binding_plane_outside_closed_set", "consumer_plane",
        lambda c: c["consumer_bindings"][0].update(consumer_plane="public_website"))
    mut("consumer_binding_tutor_row_missing_runtime_evidence", "runtime_item_ids AND knowledge_component_ids",
        lambda c: next(r for r in c["consumer_bindings"]
                       if r["consumer_plane"] == "tutor_runtime").update(runtime_item_ids=[]))
    mut("consumer_binding_analytical_row_claims_runtime_evidence", "must carry no tutor runtime evidence",
        lambda c: next(r for r in c["consumer_bindings"]
                       if r["consumer_plane"] == "nahw_analytical").update(
                           knowledge_component_ids=["kc-attributive-follower-licensing"]))
    # F7/F8 (adversarial orthography review): a per-tranche binding-id set must be pinned (not
    # just an "approved train" regex), and a non-test file must never count as a test.
    mut("tranche_duplicate_binding_id_escapes_pinning", "binding-id set drift",
        lambda c: c["consumer_bindings"].append(dict(
            next(r for r in c["consumer_bindings"] if r["consumer_train"] == "tranche_001a"),
            binding_id="l1l6-tranche-001a-duplicate-row")))
    mut("tranche_unregistered_train_name_validates_unchecked", "no registered expected binding-id set",
        lambda c: c["consumer_bindings"].append(dict(
            next(r for r in c["consumer_bindings"] if r["consumer_train"] == "tranche_001a"),
            binding_id="l1l6-tranche-002a-unregistered", consumer_train="tranche_002a",
            lesson_ids=[], unit_ids=[])))
    mut("consumer_module_counted_as_test_path", "is not a test file",
        lambda c: next(r for r in c["consumer_bindings"]
                       if r["consumer_train"] == "tranche_001a").update(
                           test_paths=list(next(r for r in c["consumer_bindings"]
                                                 if r["consumer_train"] == "tranche_001a")["test_paths"])
                           + ["tools/curriculum_unit_consumer.py"]))
    # F8 hostile probe (round-trip: no fake file is ever committed, the real file's bytes are
    # restored in a `finally` before this function returns): a production module RENAMED to a
    # test_*.py basename must still pass the cheap name check, so the check must catch it on
    # CONTENT instead. Temporarily overwrite the real file tools/test_paths already cites
    # (tools/test_fusha_orthography.py) with production-shaped source carrying no test structure,
    # run the real check against it, then restore the original bytes.
    p_t = ROOT / "tools" / "test_fusha_orthography.py"
    if p_t.exists():
        raw_t = p_t.read_bytes()
        try:
            p_t.write_bytes(
                b"#!/usr/bin/env python3\n"
                b"def compute_something(x):\n"
                b"    return x + 1\n"
            )
            errs5 = []
            check_consumer_operationalization_bindings(copy.deepcopy(base), errs5)
        finally:
            p_t.write_bytes(raw_t)
        ok5 = any("has no real test structure" in e for e in errs5)
        mutations.append(("test_path_named_test_but_no_test_structure", ok5))
        if not ok5:
            print("  test_path_named_test_but_no_test_structure did NOT trip on a production "
                  "file merely renamed to a test_*.py basename; errors=%r" % errs5[:3])
    # In-memory probe on the content-check helper itself, independent of any real file: a genuine
    # unittest.TestCase and this repo's own non-unittest self-test entrypoints must both still be
    # accepted (the content check must not become so strict it rejects real, already-used test
    # styles), while renamed production source is rejected.
    ok6 = (
        not _test_path_has_real_test_structure(
            "#!/usr/bin/env python3\ndef compute_something(x):\n    return x + 1\n")
        and _test_path_has_real_test_structure(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n")
        and _test_path_has_real_test_structure("def _self_test():\n    return 0\n")
    )
    mutations.append(("test_path_content_helper_accepts_real_rejects_renamed", ok6))
    if not ok6:
        print("  test_path_content_helper_accepts_real_rejects_renamed: helper misclassified "
              "at least one of the renamed-production/unittest/self-test probes")
    # Sol witness canaries: a context-only appearance injected as a witness
    # must trip the same-entry/selected re-verification gate (file-level
    # mutation: checked via a temp-modified copy of the grounding rows)
    # implemented as a direct check call on mutated rows:
    import copy as _copy
    base_errs = []
    check_freeze_planes(_copy.deepcopy(base), base_errs)
    canary_rows = None
    p_g = BASE / "canonical" / "vn-grounding.jsonl"
    if p_g.exists():
        raw = p_g.read_bytes()
        rows_ = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
        touched = False
        for r in rows_:
            for sub in r.get("resolved", []):
                if "n904" in sub.get("source_keys", []):
                    sub["selected_witnesses"] = list(sub["selected_witnesses"]) + [{
                        "occurrence_id": "quran:12:43:6",
                        "appearance_id": "CONTEXT:FAKE",
                        "surface": "بقرات", "selected": True,
                        "relation": "entry_selected_word"}]
                    touched = True
        if touched:
            tmp = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                          for r in rows_).encode("utf-8")
            p_g.write_bytes(tmp)
            errs2 = []
            try:
                check_freeze_planes(_copy.deepcopy(base), errs2)
            finally:
                p_g.write_bytes(raw)
            ok = any("witness" in e for e in errs2)
            mutations.append(("context_witness_canary_12_43_6", ok))
            if not ok:
                print("  context-witness canary did NOT trip the gate")

    # card_display_only witness upgraded to a canonical claim must trip the
    # canonical-surface gate (Sol fix-request round 2, finding 3)
    if p_g.exists():
        raw = p_g.read_bytes()
        rows_ = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
        touched = False
        for r in rows_:
            for sub in r.get("resolved", []):
                for w in sub.get("selected_witnesses", []):
                    if not touched and not w.get("canonical_surface_verified"):
                        w["canonical_surface_verified"] = True
                        touched = True
        if touched:
            p_g.write_bytes("".join(
                json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                for r in rows_).encode("utf-8"))
            errs3 = []
            try:
                check_freeze_planes(_copy.deepcopy(base), errs3)
            finally:
                p_g.write_bytes(raw)
            ok = any("canonical_surface" in e for e in errs3)
            mutations.append(("card_display_witness_upgrade_canary", ok))
            if not ok:
                print("  card-display upgrade canary did NOT trip the gate")

    # ma payload degradation (surface null / zero appearances) must trip the
    # payload-binding gate (Sol fix-request round 2, finding 4)
    p_b = BASE / "reports" / "occurrence-bridge.jsonl"
    if p_b.exists():
        raw = p_b.read_bytes()
        rows_ = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
        touched = False
        for r in rows_:
            if r.get("increment") == "inc-ma" and r.get("occurrence_id") \
                    and not touched:
                r["surface"] = None
                r["appearances"] = {"rows": [], "count": 0}
                touched = True
        if touched:
            p_b.write_bytes("".join(
                json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                for r in rows_).encode("utf-8"))
            errs4 = []
            try:
                check_ma_payload_binding(_copy.deepcopy(base), errs4)
            finally:
                p_b.write_bytes(raw)
            ok = any("ma_payload_binding" in e for e in errs4)
            mutations.append(("ma_payload_degradation_canary", ok))
            if not ok:
                print("  ma payload degradation canary did NOT trip the gate")

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
