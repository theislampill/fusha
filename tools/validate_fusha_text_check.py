#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_fusha_text_check — conformance gate for general text-check records (fusha/text-check@1).

Validates each record against qamus/schemas/fusha-text-check.schema.json, then enforces the required FAIL conditions
(parserplans/general-fusha-grammar-checker/{004,019,020}). A record FAILS if:

  1. arbitrary/corpus output claims source-address certainty (a token carries a loc, OR a diagnostic/token gate is
     auto_safe, OR an arbitrary/corpus token's parse_confidence is certified/two_vote).
  2. the original text is not preserved (source_boundary.original_preserved != true, or raw_input empty/missing).
  3. normalization operations are not tracked (harakāt / orthographic variant present in raw_input but no normalization_ops).
  4. a clitic segmentation is asserted as certain without evidence (arbitrary/corpus token decision_status=resolved).
  5. ambiguity is dropped for unvoweled text (an unvoweled Arabic token, len>=2, with no segment_candidates AND no
     ambiguous_unvoweled_token diagnostic).
  6. a public-facing field leaks a source name / MCP/QAC/Tafsir label / translation brand / local path (FC.LEAK_RE).
  7. a diagnostic lacks severity / gate / route(lane+procedure).
  8. a suggestion lacks confidence / gate.
  9. an iʿrāb/governor-sensitive diagnostic is auto_safe without governor reasoning.
 10. a source_addressed-mode token is resolved but lacks an exact S:A:W address (or ANY token carries a non-S:A:W loc).
 11. an enum-constrained field (gate/severity/issue_class/decision_status) carries a value outside the schema enum
     (these live behind a $ref, so the mini schema-validator does not catch them — this closes that bypass).
 12. a segment_candidate's segments do not concatenate to the token surface exactly.

CLI:
  python3 tools/validate_fusha_text_check.py <records.jsonl>
  python3 tools/validate_fusha_text_check.py --self-test
Stdlib only; reuses the repo mini schema-validator + fusha_check.LEAK_RE. Exit non-zero on any violation.
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools.validate_linguistic_decisions import validate_schema  # noqa: E402
from tools import fusha_check as FC  # noqa: E402
from tools import fusha_text_check as TC  # noqa: E402

SCHEMA = os.path.join(_REPO, "qamus", "schemas", "fusha-text-check.schema.json")
_SCHEMA = json.load(open(SCHEMA, encoding="utf-8"))
_GATES = set(_SCHEMA["$defs"]["diagnostic"]["properties"]["gate"]["enum"])
_SEVERITIES = set(_SCHEMA["$defs"]["diagnostic"]["properties"]["severity"]["enum"])
_ISSUE_CLASSES = set(_SCHEMA["$defs"]["diagnostic"]["properties"]["issue_class"]["enum"])
_DECISION_STATUS = set(_SCHEMA["$defs"]["analysisToken"]["properties"]["decision_status"]["enum"])
_LANES = {"sarf", "nahw", "curriculum", "validator", "owner_review", "scholar_irab_review"}
_NONCERT_MODES = {"arbitrary_typing", "corpus_backed"}
_ARBITRARY_CONF = {"surface_only", "candidate", "unknown"}
_CERTAIN_CONF = {"certified", "two_vote"}
_LOC_RE = re.compile(r"^\d{1,3}:\d{1,3}:\d{1,3}$")
# iʿrāb/governor-sensitive classes that may never be auto_safe (FAIL 9) — SHARED single source of truth with the
# rich-hover candidate validator (FC.IRAB_SENSITIVE_ISSUE_CLASSES), so the two validators cannot drift.
_IRAB_SENSITIVE = FC.IRAB_SENSITIVE_ISSUE_CLASSES

# P2b A: the morphology candidate lattice $defs (the slot is loose `additionalProperties:true`, so validate each
# candidate/container explicitly — the mini schema-validator does not resolve $ref).
_MORPH_SCHEMA = json.load(open(os.path.join(_REPO, "qamus", "schemas", "morphology-candidate-lattice.schema.json"), encoding="utf-8"))
_MORPH_CAND = _MORPH_SCHEMA["$defs"]["candidate"]
_MORPH_LAT = _MORPH_SCHEMA["$defs"]["lattice"]
_MORPH_FEATURE_KEYS = set(_MORPH_CAND["properties"]["features"]["properties"].keys())
# P2b C: the (extended) suggestion $def — behind a $ref, so validate each suggestion explicitly.
_SUGG_SCHEMA = _SCHEMA["$defs"]["suggestion"]
_TOK_RE = re.compile(r"^tok:\d+$")
_STRUCTURAL_OPS = {"insert", "delete", "replace", "merge", "split"}
_NONAPPLY_OPS = {"retain", "reject", "abstain", "none"}


def _has_harakat(s):
    return any(0x064B <= ord(c) <= 0x0652 for c in (s or ""))


def _public_strings(rec):
    """Every reader-reachable string WE emit (not the user's raw_input). These are scanned for provenance leaks."""
    for d in rec.get("diagnostics") or []:
        yield "diagnostic.explanation", d.get("explanation", "") or ""
        yield "diagnostic.observed", d.get("observed", "") or ""
        yield "diagnostic.expected", d.get("expected", "") or ""
    for s in rec.get("suggestions") or []:
        yield "suggestion.explanation", s.get("explanation", "") or ""
        yield "suggestion.replacement", (s.get("edit") or {}).get("replacement") or ""
    for t in rec.get("analysis_tokens") or []:
        for c in t.get("segment_candidates") or []:
            for seg in c.get("segments") or []:
                yield "segment.gloss_contribution", seg.get("gloss_contribution") or ""
    for op in rec.get("normalization_ops") or []:
        yield "normalization_op.note", op.get("note") or ""


def validate_record(rec, schema):
    errors = []
    rid = rec.get("document_id") or rec.get("input_mode") or "?"
    for e in validate_schema(rec, schema):
        errors.append(("schema", "%s: %s" % (rid, e)))
    mode = rec.get("input_mode")
    tokens = rec.get("analysis_tokens") or []
    diags = rec.get("diagnostics") or []

    # FAIL 2: original preserved
    sb = rec.get("source_boundary") or {}
    if sb.get("original_preserved") is not True or not (rec.get("raw_input") or ""):
        errors.append(("2", "%s: original text not preserved (raw_input/source_boundary)" % rid))
    if sb.get("quran_text_altered") is True or sb.get("external_text_copied") is True:
        errors.append(("2", "%s: source_boundary asserts altered/copied text" % rid))

    # FAIL 3: normalization op-trail present when norm_strict would actually transform the raw input. Uses the SAME
    # predicate as the checker (TC.needs_normalization) so the two cannot drift; hamza seats are kept and need no op.
    raw = rec.get("raw_input") or ""
    if TC.needs_normalization(raw) and not (rec.get("normalization_ops") or []):
        errors.append(("3", "%s: raw_input carries a transforming variant but normalization_ops is empty" % rid))

    # FAIL 11: enum-constrained fields that live behind a $ref (so validate_schema does NOT check them) must still be
    # in-enum — else an invented gate/severity/issue_class/decision_status bypasses both gates (schema-soundness hole).
    for d in diags:
        if d.get("gate") not in _GATES:
            errors.append(("11", "%s: diagnostic %s gate %r not in the 4-tier set" % (rid, d.get("issue_class"), d.get("gate"))))
        if d.get("severity") not in _SEVERITIES:
            errors.append(("11", "%s: diagnostic severity %r invalid" % (rid, d.get("severity"))))
        if d.get("issue_class") not in _ISSUE_CLASSES:
            errors.append(("11", "%s: diagnostic issue_class %r invalid" % (rid, d.get("issue_class"))))
    for g in rec.get("gates") or []:
        if g not in _GATES:
            errors.append(("11", "%s: gates[] value %r not in the 4-tier set" % (rid, g)))
    for s in rec.get("suggestions") or []:
        if s.get("gate") not in _GATES:
            errors.append(("11", "%s: suggestion gate %r not in the 4-tier set" % (rid, s.get("gate"))))
    for t in tokens:
        if t.get("decision_status") not in _DECISION_STATUS:
            errors.append(("11", "%s: token %r decision_status %r invalid" % (rid, t.get("surface"), t.get("decision_status"))))

    # FAIL 12: every segment_candidate's segments must concatenate to the token surface exactly (the renderer invariant,
    # enforced at production time by the checker and by the rich-hover validator; mirror it here for external records).
    for t in tokens:
        surf = t.get("surface") or ""
        for c in t.get("segment_candidates") or []:
            if "".join(seg.get("surface", "") for seg in c.get("segments") or []) != surf:
                errors.append(("12", "%s: a segment_candidate of token %r does not concatenate to the surface" % (rid, surf)))

    # FAIL M1-M8: morphology candidate lattice (P2b A). Disambiguation is RANKING (score + rank, never a boolean);
    # ambiguity is preserved (a >1-candidate token stays pending); never auto_safe for unvoweled/homograph; source-clean.
    _morph_modes = mode in _NONCERT_MODES
    n_seg_by_idx = {t.get("index"): len(t.get("segment_candidates") or []) for t in tokens}
    for t in tokens:
        surf = t.get("surface") or ""
        mc = t.get("morphology_candidates") or []
        n_seg = n_seg_by_idx.get(t.get("index"), 0)
        # M8: an arbitrary/corpus Arabic token must carry a non-empty lattice
        if _morph_modes and TC._is_arabic(surf) and not mc:
            errors.append(("M8", "%s: Arabic token %r has an empty morphology lattice" % (rid, surf)))
        for c in mc:
            for e in validate_schema(c, _MORPH_CAND):
                errors.append(("schema", "%s: morphology candidate of %r: %s" % (rid, surf, e)))
            # M1: no boolean correctness flag (disambiguation is ranking, never a forced 'correct')
            if "correct" in c or "is_correct" in c:
                errors.append(("M1", "%s: morphology candidate carries a boolean correct flag" % rid))
            # M2: score AND rank both present and numeric/int (two distinct fields)
            if not (isinstance(c.get("score"), (int, float)) and not isinstance(c.get("score"), bool)
                    and isinstance(c.get("rank"), int) and not isinstance(c.get("rank"), bool)):
                errors.append(("M2", "%s: morphology candidate must carry a numeric score AND an integer rank" % rid))
            # M4: gate on the 4-tier; unvoweled/homograph candidate never auto_safe
            if c.get("gate") not in _GATES:
                errors.append(("M4", "%s: morphology candidate gate %r off the 4-tier" % (rid, c.get("gate"))))
            if c.get("evidence_class") in ("unvoweled_competing", "homograph_split") and c.get("gate") == "auto_safe":
                errors.append(("M4", "%s: an unvoweled/homograph morphology candidate is auto_safe" % rid))
            # M5: segment_candidate_ref must index a real segment_candidates row (the lattice never rebuilds a segmentation)
            ref = c.get("segment_candidate_ref")
            if not isinstance(ref, int) or isinstance(ref, bool) or ref < 0 or ref >= n_seg:
                errors.append(("M5", "%s: morphology candidate segment_candidate_ref %r does not index a segment_candidates row" % (rid, ref)))
            # M6: features keys closed
            if set((c.get("features") or {}).keys()) - _MORPH_FEATURE_KEYS:
                errors.append(("M6", "%s: morphology candidate features has an off-set key" % rid))
            # M7: ambiguity_reason leak
            if FC.LEAK_RE.search(c.get("ambiguity_reason") or ""):
                errors.append(("M7", "%s: morphology candidate ambiguity_reason leaks an internal source name / path" % rid))
        # M3: a token with >1 candidate must be pending + surface_only|candidate (ambiguity preserved, never collapsed)
        if len(mc) > 1 and (t.get("decision_status") != "pending" or t.get("parse_confidence") not in ("surface_only", "candidate")):
            errors.append(("M3", "%s: token %r has >1 morphology candidate but is not pending/surface_only|candidate" % (rid, surf)))
    # doc-wide containers validate against the lattice $def
    for lat in rec.get("morphology_candidates") or []:
        for e in validate_schema(lat, _MORPH_LAT):
            errors.append(("schema", "%s: morphology lattice container: %s" % (rid, e)))

    # FAIL 10 (all modes): any non-null loc must be an exact S:A:W — a fabricated address must never pass, regardless
    # of mode or decision_status (the schema's loc field carries no pattern because it is behind a $ref).
    for t in tokens:
        loc = t.get("loc")
        if loc is not None and not _LOC_RE.match(str(loc)):
            errors.append(("10", "%s: token %r loc %r is not an exact S:A:W" % (rid, t.get("surface"), loc)))

    # FAIL 1/4: certainty discipline by mode
    if mode in _NONCERT_MODES:
        for d in diags:
            if d.get("gate") == "auto_safe":
                errors.append(("1", "%s: %s diagnostic %s gate=auto_safe (arbitrary/corpus may never be auto_safe)" % (rid, mode, d.get("issue_class"))))
        for g in rec.get("gates") or []:
            if g == "auto_safe":
                errors.append(("1", "%s: %s top-level gates[] contains auto_safe (document-level certainty in a non-addressed mode)" % (rid, mode)))
        for s in rec.get("suggestions") or []:
            if s.get("gate") == "auto_safe":
                errors.append(("1", "%s: %s suggestion gate=auto_safe (arbitrary/corpus may never be auto_safe)" % (rid, mode)))
        for t in tokens:
            if t.get("loc"):
                errors.append(("1", "%s: %s token %r carries a source loc (no source-address certainty in this mode)" % (rid, mode, t.get("surface"))))
            if t.get("parse_confidence") in _CERTAIN_CONF:
                errors.append(("1", "%s: %s token %r parse_confidence=%s (too certain for non-addressed mode)" % (rid, mode, t.get("surface"), t.get("parse_confidence"))))
            if t.get("parse_confidence") not in _ARBITRARY_CONF:
                errors.append(("1", "%s: %s token %r parse_confidence=%r not in %s" % (rid, mode, t.get("surface"), t.get("parse_confidence"), sorted(_ARBITRARY_CONF))))
            # FAIL 4: an arbitrary/corpus token may never be 'resolved' (asserts certainty without an address)
            if t.get("decision_status") not in ("pending", "blocked", "unknown"):
                errors.append(("4", "%s: %s token %r decision_status=%r without a source address (asserted certain)" % (rid, mode, t.get("surface"), t.get("decision_status"))))
    elif mode == "source_addressed":
        for t in tokens:
            # FAIL 10: a resolved source-addressed token must carry an exact S:A:W (covered generally above, kept explicit)
            if t.get("decision_status") == "resolved" and not _LOC_RE.match(str(t.get("loc") or "")):
                errors.append(("10", "%s: source_addressed resolved token %r lacks an exact S:A:W (loc=%r)" % (rid, t.get("surface"), t.get("loc"))))
            # FAIL 1 (F22): a certified/two_vote confidence requires a resolved status + exact loc
            if t.get("parse_confidence") in _CERTAIN_CONF and (t.get("decision_status") != "resolved" or not _LOC_RE.match(str(t.get("loc") or ""))):
                errors.append(("1", "%s: token %r parse_confidence=%s without resolved status + exact loc" % (rid, t.get("surface"), t.get("parse_confidence"))))

    # FAIL 5: ambiguity preserved for unvoweled tokens — arabic-ness is RE-DERIVED from the surface (never trusts the
    # self-reported is_arabic flag, which an external record could lie about to collapse ambiguity).
    diag_targets_unv = {d.get("target") for d in diags if d.get("issue_class") == "ambiguous_unvoweled_token"}
    for t in tokens:
        surf = t.get("surface") or ""
        bare = "".join(c for c in surf if not (0x064B <= ord(c) <= 0x0655 or ord(c) in (0x0640, 0x0670)))
        surf_is_arabic = TC._is_arabic(surf)
        if "is_arabic" in t and bool(t.get("is_arabic")) != surf_is_arabic:
            errors.append(("5", "%s: token %r is_arabic flag disagrees with the surface" % (rid, surf)))
        if surf_is_arabic and not _has_harakat(surf) and len(bare) >= 2:
            tgt = "tok:%d" % t.get("index", -1)
            if not (t.get("segment_candidates")) and tgt not in diag_targets_unv:
                errors.append(("5", "%s: unvoweled token %r drops ambiguity (no segment_candidates, no ambiguous_unvoweled_token)" % (rid, surf)))

    # FAIL 6: public-facing leak
    for label, s in _public_strings(rec):
        if FC.LEAK_RE.search(s or ""):
            errors.append(("6", "%s: %s leaks an internal source name / path" % (rid, label)))

    # FAIL 7: diagnostics carry severity + gate + route
    for d in diags:
        rt = d.get("route") or {}
        if not d.get("severity") or not d.get("gate") or rt.get("lane") not in _LANES or not (rt.get("procedure") or "").strip():
            errors.append(("7", "%s: diagnostic %s lacks severity/gate/route" % (rid, d.get("issue_class"))))
        # FAIL 9: iʿrāb/governor-sensitive diagnostic may not be auto_safe
        if d.get("issue_class") in _IRAB_SENSITIVE and d.get("gate") == "auto_safe":
            errors.append(("9", "%s: iʿrāb-sensitive diagnostic %s is auto_safe without governor reasoning" % (rid, d.get("issue_class"))))

    # FAIL 8: suggestions carry confidence + gate
    for s in rec.get("suggestions") or []:
        if not s.get("confidence") or not s.get("gate"):
            errors.append(("8", "%s: suggestion lacks confidence/gate" % rid))
        # FAIL 9 (suggestion side): an iʿrāb-sensitive correction may not be auto_safe
        if s.get("gate") == "auto_safe" and (s.get("edit") or {}).get("op") in ("replace", "merge", "split"):
            errors.append(("9", "%s: a structural correction is auto_safe (needs governor reasoning / review)" % rid))

    # FAIL 8b/8c/9b/10/11 (P2b C): the extended suggestion contract. Validate each suggestion explicitly against the
    # $def (behind a $ref, so the mini-validator does not), then the abstention/iʿrāb/NMS/orphan invariants.
    diag_ids = {"%s@%s" % (d.get("issue_class"), d.get("target")) for d in diags}
    applicable_targets = []
    for s in rec.get("suggestions") or []:
        for e in validate_schema(s, _SUGG_SCHEMA):
            errors.append(("schema", "%s: suggestion: %s" % (rid, e)))
        edit = s.get("edit") or {}
        op = edit.get("op")
        # FAIL 8b: reject / abstain / none must carry a reject_reason (unsafe/abstained ⇒ a stated reason)
        if op in ("reject", "abstain", "none") and not s.get("reject_reason"):
            errors.append(("8b", "%s: a %s suggestion lacks a reject_reason" % (rid, op)))
        # FAIL 8c: retain / reject / abstain / none must NOT carry a replacement (no applied edit)
        if op in _NONAPPLY_OPS and edit.get("replacement") is not None:
            errors.append(("8c", "%s: a %s suggestion carries a replacement (must be null)" % (rid, op)))
        # FAIL 9b: an iʿrāb-sensitive suggestion (by originating diagnostic) may never be auto_safe
        did = s.get("diagnostic_id") or ""
        issue_cls = did.split("@", 1)[0] if "@" in did else None
        if issue_cls in _IRAB_SENSITIVE and s.get("gate") == "auto_safe":
            errors.append(("9b", "%s: an iʿrāb-sensitive suggestion is auto_safe without governor reasoning" % rid))
        # FAIL 10: edit.target must be tok:N
        if not _TOK_RE.match(str(edit.get("target") or "")):
            errors.append(("10", "%s: suggestion edit.target %r is not tok:N" % (rid, edit.get("target"))))
        if op in _STRUCTURAL_OPS:
            applicable_targets.append(edit.get("target"))
        # FAIL 11: a non-retain suggestion needs a diagnostic_id resolving to an in-record diagnostic (no orphan corrections)
        if op != "retain" and (not did or did not in diag_ids):
            errors.append(("11", "%s: %s suggestion diagnostic_id %r does not resolve to an in-record diagnostic" % (rid, op, did)))
    # FAIL 10: NMS invariant — at most one APPLICABLE (structural) suggestion per target (overlap must be NMS-suppressed)
    if len(applicable_targets) != len(set(applicable_targets)):
        errors.append(("10", "%s: two applicable suggestions share a target (NMS overlap not suppressed)" % rid))

    # dry-run invariant
    if (rec.get("checker_summary") or {}).get("live_writes") != 0:
        errors.append(("1", "%s: checker_summary.live_writes != 0" % rid))
    return errors


def validate_file(path):
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    n, all_errors = 0, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            all_errors.extend(validate_record(json.loads(line), schema))
    return n, all_errors


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def _bad_records():
    """One deliberately-malformed record per FAIL condition -> (condition, record)."""
    base = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "وبالكتابِ مفيدٌ"})
    out = []

    b = json.loads(json.dumps(base)); b["analysis_tokens"][0]["loc"] = "1:1:1"
    out.append(("1", b))

    b = json.loads(json.dumps(base)); b["source_boundary"]["original_preserved"] = False
    out.append(("2", b))

    b = json.loads(json.dumps(base)); b["normalization_ops"] = []  # raw has harakāt -> must have ops
    out.append(("3", b))

    b = json.loads(json.dumps(base)); b["analysis_tokens"][0]["decision_status"] = "resolved"
    out.append(("4", b))

    # FAIL 5: an unvoweled token with no candidates + no ambiguity diagnostic
    b = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "علم نور"})
    for t in b["analysis_tokens"]:
        t["segment_candidates"] = []
    b["diagnostics"] = [d for d in b["diagnostics"] if d["issue_class"] != "ambiguous_unvoweled_token"]
    out.append(("5", b))

    b = json.loads(json.dumps(base)); b["diagnostics"][0]["explanation"] = "see the QAC tagset"  # leak
    out.append(("6", b))

    b = json.loads(json.dumps(base)); b["diagnostics"][0]["gate"] = ""  # missing gate
    out.append(("7", b))

    b = json.loads(json.dumps(base))
    b["suggestions"] = [{"edit": {"op": "replace", "target": "tok:0", "replacement": "x"}, "explanation": None,
                         "confidence": "high", "gate": "auto_safe", "safe_to_show_inline": True, "needs_review": False}]
    out.append(("9", b))

    b = json.loads(json.dumps(base))
    b["suggestions"] = [{"edit": {"op": "insert", "target": "tok:0", "replacement": "x"}, "explanation": None,
                         "confidence": "", "gate": "", "safe_to_show_inline": False, "needs_review": True}]
    out.append(("8", b))

    # FAIL 10: source_addressed resolved token with a non-S:A:W loc
    b = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "كتابٌ"})
    b["input_mode"] = "source_addressed"
    b["analysis_tokens"][0]["decision_status"] = "resolved"
    b["analysis_tokens"][0]["loc"] = "not-an-address"
    out.append(("10", b))

    # FAIL 11: an invented gate value (behind the $ref, so validate_schema does not catch it)
    b = json.loads(json.dumps(base)); b["diagnostics"][0]["gate"] = "auto_publish_now"
    out.append(("11", b))

    # FAIL 12: a segment_candidate whose segments do not concatenate to the surface
    b = json.loads(json.dumps(base))
    b["analysis_tokens"][0]["segment_candidates"][0]["segments"][0]["surface"] = "XXX"
    out.append(("12", b))

    # --- P2b A: morphology candidate lattice bad-records (base2 = 'علم نور' has >1 candidate per token) ---
    base2 = TC.check_text({"input_mode": "arbitrary_typing", "raw_input": "علم نور"})
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["morphology_candidates"][0]["correct"] = True
    out.append(("M1", b))
    b = json.loads(json.dumps(base2)); del b["analysis_tokens"][0]["morphology_candidates"][0]["score"]
    out.append(("M2", b))
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["decision_status"] = "resolved"
    out.append(("M3", b))
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["morphology_candidates"][0]["gate"] = "auto_safe"
    out.append(("M4", b))
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["morphology_candidates"][0]["segment_candidate_ref"] = 99
    out.append(("M5", b))
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["morphology_candidates"][0]["features"]["banana"] = "x"
    out.append(("M6", b))
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["morphology_candidates"][0]["ambiguity_reason"] = "see the QAC tagset"
    out.append(("M7", b))
    b = json.loads(json.dumps(base2)); b["analysis_tokens"][0]["morphology_candidates"] = []
    out.append(("M8", b))

    # --- P2b C: suggestion bad-records. base carries a real possible_clitic_segmentation@tok:0 diagnostic, so a split
    # suggestion's diagnostic_id resolves; we replace suggestions[] with one canonical good suggestion and mutate it. ---
    good_sugg = {"diagnostic_id": "possible_clitic_segmentation@tok:0",
                 "edit": {"op": "split", "target": "tok:0", "replacement": "و بالكتاب",
                          "target_span": {"start": 0, "end": 5, "unit": "char"}, "source_locus": None},
                 "explanation": "A suggested split for review.", "confidence": "medium", "gate": "two_vote_required",
                 "safe_to_show_inline": False, "needs_review": True, "reject_reason": None, "nms_group": None,
                 "learner_level_min": None, "learner_level_max": None, "route_to": None}

    def _with_sugg(*mutate):
        bb = json.loads(json.dumps(base))
        s = json.loads(json.dumps(good_sugg))
        for m in mutate:
            m(s)
        bb["suggestions"] = [s]
        return bb

    # 8b: abstain with no reject_reason
    out.append(("8b", _with_sugg(lambda s: s["edit"].update(op="abstain", replacement=None),
                                 lambda s: s.update(reject_reason=None))))
    # 8c: retain with a replacement
    out.append(("8c", _with_sugg(lambda s: s["edit"].update(op="retain", replacement="x"),
                                 lambda s: s.update(diagnostic_id=None))))
    # 9b: an iʿrāb-sensitive suggestion that is auto_safe (non-structural reject, so the legacy FAIL 9 won't catch it)
    out.append(("9b", _with_sugg(lambda s: s["edit"].update(op="reject", replacement=None),
                                 lambda s: s.update(diagnostic_id="weak_irab_reasoning@tok:0", gate="auto_safe",
                                                    reject_reason="governor_not_justified"))))
    # 10: edit.target not tok:N
    out.append(("10", _with_sugg(lambda s: s["edit"].update(target="3:1:1"))))
    # 11: a non-retain suggestion whose diagnostic_id does not resolve
    out.append(("11", _with_sugg(lambda s: s.update(diagnostic_id="possible_particle_function@tok:99"))))
    # 10 (NMS): two applicable suggestions sharing a target
    b = json.loads(json.dumps(base)); b["suggestions"] = [json.loads(json.dumps(good_sugg)), json.loads(json.dumps(good_sugg))]
    out.append(("10", b))
    return out


def _self_test():
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    failures = []
    # good: the checker's own fixture rows validate clean
    for req in TC.regression_requests():
        rec = TC.check_text(req)
        errs = validate_record(rec, schema)
        if errs:
            failures.append("good record %s should validate clean but: %s" % (req["name"], errs[:2]))
    # bad: each trips its condition
    for cond, rec in _bad_records():
        conds = {c for c, _ in validate_record(rec, schema)}
        if cond not in conds:
            failures.append("bad record should trip FAIL %s but tripped %s" % (cond, sorted(conds)))
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_fusha_text_check self-test: fixture rows clean; all base 12 + M1-M8 morphology + 8b/8c/9b/10/11 suggestion FAIL conditions reject")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Validate general Fusha text-check records.")
    ap.add_argument("path", nargs="?", help="records JSONL")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.path:
        ap.error("need a path or --self-test")
    n, errors = validate_file(a.path)
    for cond, msg in errors:
        print("FAIL [cond %s] %s" % (cond, msg))
    print("checked %d record(s), %d violation(s)" % (n, len(errors)))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
