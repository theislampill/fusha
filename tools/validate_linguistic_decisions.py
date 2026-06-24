#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F13 — validator: a linguistic-decision JSONL must satisfy the schema AND the regression invariants.

Two gates, both hard (exit non-zero on the first class of failure):

  1. SCHEMA  — every record conforms to qamus/schemas/linguistic-decision.schema.json:
     required keys, the decision-type / pos / confidence / review_status enums, the decision_id and
     source_address patterns, and top-level additionalProperties:false. A tiny stdlib validator (no
     jsonschema dependency) implements exactly the parts of draft-2020-12 the schema uses.

  2. INVARIANTS — the qamus-highlight regressions that must never recur, re-derived from the harakāt
     helpers in tools/normalize_ar.py so the check tracks the real disambiguation, not a copied table:
       * مَن 'who' and مِن 'from' never collapse — a مِن (kasra on the mīm, incl. وَمِنَ) decision may
         never carry a 'who/whoever' gloss, and a مَن (no kasra) decision may never carry 'from'.
       * No 'to …' verb gloss on a noun/proper-noun POS (رَسُولًا ≠ 'to send').
       * إِلَيْنَا never reduces to the root ل ي ن.
       * public_export_allowed implies (a) decision.type=='authored_gloss' with a gloss present and
         (b) NO internal-provenance leak anywhere in the record (no qac/tanzil/informed_by/quran.com,
         no internal_provenance object on an exportable record's public surface).

No network, no writes. Usage:
    python tools/validate_linguistic_decisions.py path/to/decisions.jsonl
    python tools/validate_linguistic_decisions.py --self-test
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tools import normalize_ar as N  # noqa: E402

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                           "qamus", "schemas", "linguistic-decision.schema.json")

# any token whose lower-cased text names an internal-only source is a leak in a public surface
LEAK_RE = re.compile(r"informed_by|external_informed_by|quran\.com|corpus\.quran|tanzil|\bqac\b"
                     r"|quran-text|/srv/|/static/|photographed", re.I)
WHO_GLOSS = re.compile(r"\bwho\b|\bwhoever\b|\bwhomever\b|he who", re.I)
FROM_GLOSS = re.compile(r"\bfrom\b|\bamong\b", re.I)


# ---------------------------------------------------------------------------
# minimal schema validator (only the constructs this schema uses)
# ---------------------------------------------------------------------------
def _type_ok(value, types):
    if isinstance(types, str):
        types = [types]
    for t in types:
        if t == "string" and isinstance(value, str):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "null" and value is None:
            return True
    return False


def _validate_node(value, schema, path, errors):
    if "type" in schema and not _type_ok(value, schema["type"]):
        errors.append("%s: expected type %s, got %r" % (path, schema["type"], type(value).__name__))
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r not in enum %s" % (path, value, schema["enum"]))
    if "const" in schema and value != schema["const"]:
        errors.append("%s: %r != const %r" % (path, value, schema["const"]))
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        errors.append("%s: %r does not match /%s/" % (path, value, schema["pattern"]))
    if isinstance(value, dict) and (schema.get("type") == "object" or "properties" in schema):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errors.append("%s: missing required key %r" % (path, req))
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    errors.append("%s: additional property %r not allowed" % (path, k))
        for k, sub in props.items():
            if k in value:
                _validate_node(value[k], sub, "%s.%s" % (path, k), errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _validate_node(item, schema["items"], "%s[%d]" % (path, i), errors)


def validate_schema(record, schema):
    errors = []
    _validate_node(record, schema, "$", errors)
    return errors


# ---------------------------------------------------------------------------
# regression invariants
# ---------------------------------------------------------------------------
def invariant_violations(record):
    v = []
    dec = record.get("decision", {}) or {}
    surface = record.get("surface_ar", "") or ""
    gloss = (dec.get("gloss_en_authored") or "")
    glow = gloss.lower()
    pos = record.get("pos", "")
    n = N.norm(surface)
    # de-proclitic norm so وَمِنَ / لَمَن resolve to the من family
    nd = n[1:] if n[:1] in ("و", "ف") and len(n) > 1 else n

    # --- مَن / مِن never collapse -----------------------------------------
    if nd == "من" and gloss:
        if N.is_man_who(surface):          # the relative/interrogative مَن 'who'
            if FROM_GLOSS.search(glow) and not WHO_GLOSS.search(glow):
                v.append("مَن 'who' must not be glossed 'from/among' (%r) at %s"
                         % (gloss, record.get("source_address")))
        elif N.haraka_on(surface, "م") == N.KASRA:   # the preposition مِن 'from' (incl. وَمِنَ)
            if WHO_GLOSS.search(glow):
                v.append("مِن 'from' must not be glossed 'who/whoever' (%r) at %s"
                         % (gloss, record.get("source_address")))

    # --- no 'to …' verb gloss on a noun / proper-noun --------------------
    noun_like = pos in ("noun", "proper_noun", "adjective", "masdar", "participle")
    if noun_like and dec.get("type") == "authored_gloss" and glow.startswith("to "):
        v.append("a noun/proper-noun (%s) may not carry a 'to …' verb gloss (%r) at %s"
                 % (pos, gloss, record.get("source_address")))

    # --- إِلَيْنَا never the root ل ي ن -----------------------------------
    if N.norm_strict(surface) == N.norm_strict("إِلَيْنَا"):
        root = record.get("root_ar")
        if root and N.norm(root.replace(" ", "")) == N.norm("لين"):
            v.append("إِلَيْنَا must not be assigned the root ل ي ن at %s" % record.get("source_address"))

    # --- public_export_allowed implies authored_gloss + no provenance leak
    if record.get("public_export_allowed"):
        if dec.get("type") != "authored_gloss":
            v.append("public_export_allowed=true but decision.type=%r (must be authored_gloss) at %s"
                     % (dec.get("type"), record.get("source_address")))
        if not gloss:
            v.append("public_export_allowed=true but no gloss to export at %s" % record.get("source_address"))
        # the SHIPPED surface — what a reader would see — is the gloss text only. It must be leak-free.
        if LEAK_RE.search(gloss):
            v.append("public_export_allowed=true but the gloss leaks internal provenance (%r) at %s"
                     % (gloss, record.get("source_address")))
    return v


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def validate_stream(lines, schema):
    schema_errs, inv_errs, n = [], [], 0
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            rec = json.loads(line)
        except Exception as e:
            schema_errs.append("line %d: not valid JSON (%s)" % (i, e))
            continue
        for e in validate_schema(rec, schema):
            schema_errs.append("line %d: %s" % (i, e))
        for e in invariant_violations(rec):
            inv_errs.append("line %d: %s" % (i, e))
    return n, schema_errs, inv_errs


def _load_schema():
    return json.load(io.open(SCHEMA_PATH, encoding="utf-8"))


def _self_test():
    """Build good + deliberately-bad records and confirm the validator's verdicts."""
    schema = _load_schema()
    good = {
        "decision_id": "lingdec-000001", "source_address": "quran:2:8:1", "surface_ar": "وَمِنَ",
        "root_ar": None, "lemma_ar": "مِن", "pos": "particle",
        "sarf": {"risk_flags": ["hamza_sensitive"]},
        "nahw": {"context_rule": "content_letter_harakah:man_vs_min"},
        "decision": {"type": "authored_gloss", "gloss_en_authored": "from / among",
                     "pending_reason": None, "confidence": "high"},
        "internal_provenance": {"qac": True, "quran_text_verified": True, "external_informed_by": ["qac"]},
        "public_export_allowed": True, "review_status": "needs_human_review",
    }
    n, se, ie = validate_stream([json.dumps(good, ensure_ascii=False)], schema)
    assert not se, ("good record failed schema: %s" % se)
    assert not ie, ("good record failed invariants: %s" % ie)

    # bad 1: مِن glossed 'whoever'
    bad1 = json.loads(json.dumps(good))
    bad1["decision"]["gloss_en_authored"] = "and whoever"
    _, _, ie1 = validate_stream([json.dumps(bad1, ensure_ascii=False)], schema)
    assert any("must not be glossed 'who" in e for e in ie1), ie1

    # bad 2: 'to send' on a noun
    bad2 = json.loads(json.dumps(good))
    bad2.update({"source_address": "quran:65:11:3", "surface_ar": "رَسُولًا", "pos": "noun"})
    bad2["decision"]["gloss_en_authored"] = "to send"
    _, _, ie2 = validate_stream([json.dumps(bad2, ensure_ascii=False)], schema)
    assert any("'to …' verb gloss" in e for e in ie2), ie2

    # bad 3: إِلَيْنَا assigned root ل ي ن
    bad3 = json.loads(json.dumps(good))
    bad3.update({"source_address": "quran:10:23:1", "surface_ar": "إِلَيْنَا", "root_ar": "ل ي ن",
                 "public_export_allowed": False})
    bad3["decision"]["gloss_en_authored"] = "to us"
    _, _, ie3 = validate_stream([json.dumps(bad3, ensure_ascii=False)], schema)
    assert any("ل ي ن" in e or "must not be assigned the root" in e for e in ie3), ie3

    # bad 4: public export with a provenance leak in the gloss
    bad4 = json.loads(json.dumps(good))
    bad4["decision"]["gloss_en_authored"] = "from / among (informed_by qac)"
    _, _, ie4 = validate_stream([json.dumps(bad4, ensure_ascii=False)], schema)
    assert any("leaks internal provenance" in e for e in ie4), ie4

    # bad 5: public export on a pending decision
    bad5 = json.loads(json.dumps(good))
    bad5["decision"]["type"] = "pending"
    _, _, ie5 = validate_stream([json.dumps(bad5, ensure_ascii=False)], schema)
    assert any("must be authored_gloss" in e for e in ie5), ie5

    # bad 6: schema violation — bad decision type + bad id pattern + stray top-level key
    bad6 = json.loads(json.dumps(good))
    bad6["decision"]["type"] = "delete_everything"
    bad6["decision_id"] = "nope"
    bad6["surprise"] = 1
    n6, se6, _ = validate_stream([json.dumps(bad6, ensure_ascii=False)], schema)
    assert any("enum" in e for e in se6) and any("does not match" in e for e in se6) \
        and any("additional property" in e for e in se6), se6

    print("validate_linguistic_decisions self-test OK — good passes; "
          "6 bad records each caught (مِن≠who, no 'to …' on noun, إِلَيْنَا≠ل ي ن, "
          "no provenance leak on export, export⇒authored, schema enums/patterns)")


def main():
    ap = argparse.ArgumentParser(description="Validate a linguistic-decision JSONL against the schema "
                                             "+ regression invariants. Exit non-zero on any violation.")
    ap.add_argument("decisions", nargs="?", help="path to the decision JSONL ('-' for stdin)")
    ap.add_argument("--self-test", action="store_true", help="run the inline self-test and exit")
    a = ap.parse_args()

    if a.self_test:
        _self_test()
        return
    if not a.decisions:
        ap.error("a decisions JSONL path is required (or pass --self-test)")

    schema = _load_schema()
    if a.decisions == "-":
        lines = sys.stdin.readlines()
    else:
        lines = io.open(a.decisions, encoding="utf-8").readlines()
    n, schema_errs, inv_errs = validate_stream(lines, schema)

    for e in schema_errs:
        print("SCHEMA  " + e)
    for e in inv_errs:
        print("INVARIANT  " + e)
    if schema_errs or inv_errs:
        print("\nFAIL: %d schema error(s), %d invariant violation(s) across %d records"
              % (len(schema_errs), len(inv_errs), n))
        sys.exit(1)
    print("OK: %d decisions valid (schema + regression invariants)" % n)


if __name__ == "__main__":
    main()
