#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RM-21 schema-coherence lints (carrier-independent unification gate).

Five drift lints that keep the Qamus JSON schemas internally coherent WITHOUT
regenerating any committed data. All checks are description/enum/registry level.

  (a) gate-enum unification -- the certified-lemma `fanout_gate` enum and the
      binding/payload `binding_gate` / `payload_family` enums name ONE
      authorization concept. They are unified via a documented alias table
      (canonical named, migration note in the schema descriptions). This lint
      pins both spellings and proves the vocabulary stays closed over
      CANONICAL_GATE + GATE_ALIASES.
  (b) qg class-map 3-way drift -- morphosyntax `display.segments.class` enum
      (the SSOT) vs the class-map doc vs the CSS/DOM fixture. The class-map doc
      is GENERATED from the schema (`--emit-class-map`); the lint fails if the
      committed doc drifts, or if the CSS/DOM fixture uses a qg class that is
      not in the schema enum.
  (c) source_key semantic fork -- the binding schema's `source_key` const
      ("qamus") is the citation-CARRIER identity and is a different concept from
      the repo-wide page-ordinal `source_keys`. This lint requires the schema
      to carry a disambiguation description (document-disambiguate; no rename).
  (d) surface_norm normalizer pinning -- the canonical-hover-payload
      `surface_norm` description must name the normalizer (`_join_surface_key`)
      and every sample surface_norm must be a fixed point of it (round-trip).
  (e) cross-schema disjoint same-name field lint -- no NEW field name may be
      shared by two schemas with DISJOINT enum value spaces. The current,
      documented, context-local polysemous fields are captured in
      DISJOINT_FIELD_REGISTRY; a new disjoint same-name field turns this red.

Modes:
  (default)         run every lint on the real repo; exit non-zero on any error.
  --self-test       run every lint on the real repo AND run red-first mutation
                    proofs (each lint is forced red on a cloned copy); prints the
                    marker "schema coherence self-test OK" on success.
  --emit-class-map  print the regenerated class-map markdown to stdout.

Stdlib only; deterministic; no network; no live writes.
"""
import argparse
import copy
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(ROOT, "qamus", "schemas")
CSS_FIXTURE = os.path.join(ROOT, "docs", "parser", "index.html")
CLASS_MAP_DOC = os.path.join(ROOT, "docs", "parser", "qamus-grammar-v1-class-map.md")
PAYLOAD_SAMPLE = os.path.join(ROOT, "qamus", "examples", "canonical_hover_payload.sample.jsonl")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from validate_largelexicon_denominator_join import _join_surface_key  # noqa: E402

# ---------------------------------------------------------------------------
# (a) unified authorization gate vocabulary
# ---------------------------------------------------------------------------
# The single authorization concept. The binding/payload vocabulary is the
# canonical (split) spelling; the certified-lemma schema keeps the fused legacy
# spelling `lemma_pattern_pos` (it collapses certified lemma + certified pattern
# into one gate). The alias table declares the equivalence.
CANONICAL_GATE = ("source_address_exact", "certified_lemma", "certified_pattern", "function_context")
GATE_ALIASES = {"lemma_pattern_pos": ("certified_lemma", "certified_pattern")}
FANOUT_GATE_SPELLING = ("source_address_exact", "lemma_pattern_pos", "function_context")
SPLIT_GATE_SPELLING = CANONICAL_GATE

# ---------------------------------------------------------------------------
# (b) qg alias mapping (legacy -> canonical)
# ---------------------------------------------------------------------------
QG_LEGACY_ALIASES = {"qg-negative": "qg-negation"}

# ---------------------------------------------------------------------------
# (e) documented, context-local polysemous enum field names.
# These field names legitimately mean different things in different schemas and
# therefore carry DISJOINT enum value spaces. They are the RM-21 baseline; any
# NEW disjoint same-name field must be reconciled or added here with rationale.
# ---------------------------------------------------------------------------
DISJOINT_FIELD_REGISTRY = {
    "decision_status",   # lifecycle state (pending/resolved) vs repair adjudication verdict
    "evidence_class",    # lattice evidence tier vs morphology candidate class
    "gate",              # review/authorization gate; per-artifact vocabularies
    "kind",              # token kind vs state-transition kind
    "level",             # CEFR level vs pedagogy difficulty level
    "review_status",     # authored-gloss review vs exception review
    "scope",             # fact-ledger scope vs repair-impact scope
    "status",            # per-artifact lifecycle vocabularies
    "type",              # source-address node type vs typed-edge relation type
}


def _read_text(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def _load_schema_obj(name):
    return json.loads(_read_text(os.path.join(SCHEMA_DIR, name)))


class Repo(object):
    """A snapshot of the coherence inputs; clone()+mutate for red-first proofs."""

    def __init__(self, schemas, css_text, class_map_text, payload_surface_norms):
        self.schemas = schemas                      # basename -> schema dict
        self.css_text = css_text                    # CSS/DOM fixture text
        self.class_map_text = class_map_text        # committed class-map doc
        self.payload_surface_norms = payload_surface_norms  # list[str]

    @classmethod
    def load(cls):
        schemas = {}
        for fn in sorted(os.listdir(SCHEMA_DIR)):
            if fn.endswith(".schema.json"):
                schemas[fn] = _load_schema_obj(fn)
        surface_norms = []
        if os.path.exists(PAYLOAD_SAMPLE):
            for line in _read_text(PAYLOAD_SAMPLE).splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if isinstance(row.get("surface_norm"), str):
                    surface_norms.append(row["surface_norm"])
        return cls(schemas, _read_text(CSS_FIXTURE),
                   _read_text(CLASS_MAP_DOC) if os.path.exists(CLASS_MAP_DOC) else "",
                   surface_norms)

    def clone(self):
        return Repo(copy.deepcopy(self.schemas), self.css_text,
                    self.class_map_text, list(self.payload_surface_norms))


# ---------------------------------------------------------------------------
# enum extraction helpers
# ---------------------------------------------------------------------------
def _enum_at(schema, *path):
    node = schema
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if isinstance(node, dict):
        return node.get("enum")
    return None


def qg_schema_classes(repo):
    ms = repo.schemas.get("morphosyntax-token.schema.json", {})
    enum = _enum_at(ms, "properties", "display", "properties", "segments",
                    "items", "properties", "class")
    return list(enum or [])


def qg_css_classes(css_text):
    return sorted(set(re.findall(r"qg-[a-z0-9-]+", css_text)))


def _iter_enum_fields(schema):
    """Yield (field_name, frozenset(non-null enum values)) for every enum property."""

    def walk(node):
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                for fname, sub in props.items():
                    if isinstance(sub, dict) and isinstance(sub.get("enum"), list):
                        vals = frozenset(v for v in sub["enum"] if v is not None and v != "null")
                        if vals:
                            yield fname, vals
            for key, val in node.items():
                if key == "properties":
                    continue
                for item in walk(val):
                    yield item
        elif isinstance(node, list):
            for it in node:
                for item in walk(it):
                    yield item

    for item in walk(schema):
        yield item


# ---------------------------------------------------------------------------
# (b) class-map doc generation
# ---------------------------------------------------------------------------
def emit_class_map(repo):
    schema_classes = sorted(qg_schema_classes(repo))
    css = set(qg_css_classes(repo.css_text))
    lines = []
    lines.append("# Qamus Grammar V1 Class Map")
    lines.append("")
    lines.append("This is the canonical qg class reference for source-clean rich-hover/color projection.")
    lines.append("")
    lines.append("<!-- GENERATED from qamus/schemas/morphosyntax-token.schema.json by")
    lines.append("     tools/validate_schema_coherence.py --emit-class-map. Do NOT hand-edit the table;")
    lines.append("     add a class to the schema enum and regenerate. -->")
    lines.append("")
    lines.append("## Canonical classes (generated from the morphosyntax-token schema enum)")
    lines.append("")
    lines.append("| qg class | in CSS/DOM fixture | status |")
    lines.append("| --- | --- | --- |")
    for cls in schema_classes:
        in_css = "yes" if cls in css else "no"
        alias_of = QG_LEGACY_ALIASES.get(cls)
        status = ("legacy alias of `%s`" % alias_of) if alias_of else "canonical"
        lines.append("| `%s` | %s | %s |" % (cls, in_css, status))
    lines.append("")
    lines.append("## Alias policy")
    lines.append("")
    lines.append("`qg-negation` is canonical. `qg-negative` is a documented legacy alias only for validator")
    lines.append("migration and should not be newly emitted. Any other qg alias must be added to")
    lines.append("`QG_LEGACY_ALIASES` in `tools/validate_schema_coherence.py` and to the schema enum before it")
    lines.append("can appear in sarf, nahw, curriculum, or candidate rows.")
    lines.append("")
    lines.append("## Public boundary")
    lines.append("")
    lines.append("qg classes are display roles, not provenance. They must not encode source names, evidence")
    lines.append("labels, local paths, or review process text.")
    lines.append("")
    lines.append("**No internal parser / debug ids or parse hashes in any public field.** The public payload")
    lines.append("(gloss, learner text, `parse_key.summary`, qg class, data attributes) is grammar-facing only. It")
    lines.append("must never contain an internal parse id, node id, candidate id, decision id, or a **parse hash** --")
    lines.append("those are internal-only and live in the private evidence sidecar. `parse_key.summary` is compact")
    lines.append("learner ASCII (e.g. `V:I:PERF:ACT`, `P:bi`, `ART`), not a symbolic engine key. A learner-facing")
    lines.append("colour legend follows the same rule: grammar-role labels + swatches only, never a")
    lines.append("source/tool/process label or debug id. Enforced target: parse-hash public exposure stays **0**.")
    lines.append("Detectors: `tools/leak_sot.py` (forbidden names/paths, word-anchored),")
    lines.append("`tools/validate_public_private_boundary.py` (public-blob label scan); pedagogy:")
    lines.append("`curriculum/visual-grammar-legend.md`, `curriculum/dark-mode-accessibility-pedagogy.md`.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# lints -- each returns a list of error strings (empty == pass)
# ---------------------------------------------------------------------------
def lint_gate_unification(repo):
    errs = []
    cl = repo.schemas.get("certified-lemma.schema.json", {})
    bd = repo.schemas.get("canonical-hover-occurrence-binding.schema.json", {})
    pl = repo.schemas.get("canonical-hover-payload.schema.json", {})
    fanout = _enum_at(cl, "properties", "fanout_gate")
    binding = _enum_at(bd, "properties", "binding_gate")
    family = _enum_at(pl, "properties", "payload_family")
    if fanout is None:
        errs.append("(a) certified-lemma fanout_gate enum missing")
    elif set(fanout) != set(FANOUT_GATE_SPELLING):
        errs.append("(a) fanout_gate spelling drift: %s != %s" % (sorted(fanout), sorted(FANOUT_GATE_SPELLING)))
    if binding is None:
        errs.append("(a) binding_gate enum missing")
    elif set(binding) != set(SPLIT_GATE_SPELLING):
        errs.append("(a) binding_gate spelling drift: %s != %s" % (sorted(binding), sorted(SPLIT_GATE_SPELLING)))
    if family is None:
        errs.append("(a) payload_family enum missing")
    elif set(family) != set(SPLIT_GATE_SPELLING):
        errs.append("(a) payload_family spelling drift: %s != %s" % (sorted(family), sorted(SPLIT_GATE_SPELLING)))
    # vocabulary closure: every gate value is canonical or a declared alias.
    vocab = set(CANONICAL_GATE) | set(GATE_ALIASES)
    for name, enum in (("fanout_gate", fanout), ("binding_gate", binding), ("payload_family", family)):
        for val in (enum or []):
            if val not in vocab:
                errs.append("(a) %s value %r outside unified vocabulary (canonical+alias)" % (name, val))
    # alias targets must themselves be canonical.
    for alias, targets in GATE_ALIASES.items():
        for tgt in targets:
            if tgt not in CANONICAL_GATE:
                errs.append("(a) alias %r maps to non-canonical %r" % (alias, tgt))
    # the alias table + canonical name must be documented in a schema description.
    cl_desc = (_enum_field_desc(cl, "properties", "fanout_gate") or "")
    if "lemma_pattern_pos" not in cl_desc or "certified_lemma" not in cl_desc:
        errs.append("(a) certified-lemma fanout_gate description missing the alias table (lemma_pattern_pos -> certified_lemma/certified_pattern)")
    return errs


def _enum_field_desc(schema, *path):
    node = schema
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if isinstance(node, dict):
        return node.get("description")
    return None


def lint_qg_class_map(repo):
    errs = []
    schema_classes = set(qg_schema_classes(repo))
    if not schema_classes:
        errs.append("(b) morphosyntax display.segments.class enum missing/empty")
        return errs
    css_classes = set(qg_css_classes(repo.css_text))
    for cls in sorted(css_classes):
        if cls not in schema_classes:
            errs.append("(b) CSS/DOM fixture uses qg class %r not in the schema enum" % cls)
    # the committed doc must equal the generated doc (drift == red).
    generated = emit_class_map(repo)
    committed = repo.class_map_text.replace("\r\n", "\n")
    if committed != generated:
        errs.append("(b) class-map doc drifted from the schema-generated table (regenerate via --emit-class-map)")
    return errs


def lint_source_key_fork(repo):
    errs = []
    bd = repo.schemas.get("canonical-hover-occurrence-binding.schema.json", {})
    node = bd.get("properties", {}).get("source_key")
    if not isinstance(node, dict):
        errs.append("(c) binding schema source_key property missing")
        return errs
    if node.get("const") != "qamus":
        errs.append("(c) binding schema source_key const changed from 'qamus' (would invalidate rows)")
    desc = node.get("description") or ""
    if "source_keys" not in desc or "carrier" not in desc.lower():
        errs.append("(c) binding schema source_key missing disambiguation vs the page-ordinal `source_keys` (carrier identity note)")
    return errs


def lint_surface_norm_pinning(repo):
    errs = []
    pl = repo.schemas.get("canonical-hover-payload.schema.json", {})
    node = pl.get("properties", {}).get("surface_norm")
    if not isinstance(node, dict):
        errs.append("(d) payload schema surface_norm property missing")
        return errs
    desc = node.get("description") or ""
    if "_join_surface_key" not in desc:
        errs.append("(d) payload surface_norm description does not name the normalizer (_join_surface_key)")
    for val in repo.payload_surface_norms:
        if _join_surface_key(val) != val:
            errs.append("(d) surface_norm %r is not a fixed point of _join_surface_key (round-trip fail)" % val)
    return errs


def lint_cross_schema_disjoint_fields(repo):
    errs = []
    fields = {}  # name -> {schema_basename: frozenset}
    for name, schema in repo.schemas.items():
        for fname, vals in _iter_enum_fields(schema):
            fields.setdefault(fname, {})[name] = vals
    disjoint_names = set()
    for fname, per_schema in fields.items():
        entries = list(per_schema.items())
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                if entries[i][1].isdisjoint(entries[j][1]):
                    disjoint_names.add(fname)
    for fname in sorted(disjoint_names):
        if fname not in DISJOINT_FIELD_REGISTRY:
            errs.append("(e) NEW disjoint same-name enum field %r shared by >=2 schemas with no overlap "
                        "(reconcile the enums or register it with rationale)" % fname)
    return errs


ALL_LINTS = (
    ("gate-enum-unification", lint_gate_unification),
    ("qg-class-map-drift", lint_qg_class_map),
    ("source_key-semantic-fork", lint_source_key_fork),
    ("surface_norm-normalizer-pinning", lint_surface_norm_pinning),
    ("cross-schema-disjoint-field", lint_cross_schema_disjoint_fields),
)


def run_all(repo):
    all_errs = []
    for label, fn in ALL_LINTS:
        errs = fn(repo)
        for e in errs:
            all_errs.append((label, e))
    return all_errs


# ---------------------------------------------------------------------------
# red-first mutation proofs
# ---------------------------------------------------------------------------
def _proof(name, mutate, lint):
    repo = Repo.load().clone()
    mutate(repo)
    errs = lint(repo)
    ok = len(errs) > 0
    print(("  red-proof ok   " if ok else "  red-proof FAIL ") + name +
          ("" if ok else "  (lint did NOT go red)"))
    if ok:
        print("      -> %s" % errs[0])
    return ok


def _mut_gate(repo):
    enum = repo.schemas["certified-lemma.schema.json"]["properties"]["fanout_gate"]["enum"]
    repo.schemas["certified-lemma.schema.json"]["properties"]["fanout_gate"]["enum"] = \
        [("lemma_pattern" if v == "lemma_pattern_pos" else v) for v in enum]


def _mut_css(repo):
    repo.css_text = repo.css_text + "\n.qg-rogue-injected { color: red; }\n"


def _mut_doc(repo):
    repo.schemas["morphosyntax-token.schema.json"]["properties"]["display"]["properties"]["segments"] \
        ["items"]["properties"]["class"]["enum"].append("qg-zzz-injected")


def _mut_source_key(repo):
    repo.schemas["canonical-hover-occurrence-binding.schema.json"]["properties"]["source_key"].pop("description", None)


def _mut_surface_desc(repo):
    repo.schemas["canonical-hover-payload.schema.json"]["properties"]["surface_norm"].pop("description", None)


def _mut_surface_roundtrip(repo):
    repo.payload_surface_norms = list(repo.payload_surface_norms) + ["كِتَابـ "]  # tatweel+space -> not a fixed point


def _mut_disjoint_field(repo):
    repo.schemas["_synthetic_test.schema.json"] = {
        "type": "object",
        "properties": {"pos": {"type": "string", "enum": ["zzz_disjoint_only"]}},
    }


def self_test():
    print("== real-repo lints ==")
    repo = Repo.load()
    errs = run_all(repo)
    for label, e in errs:
        print("FAIL %s: %s" % (label, e))
    if errs:
        print("\nself-test FAIL: %d real-repo coherence error(s)" % len(errs))
        return 1
    print("  ok   all %d lints pass on the real repo" % len(ALL_LINTS))
    print("== red-first mutation proofs ==")
    proofs = [
        ("(a) mutate a gate enum value -> gate lint red", _mut_gate, lint_gate_unification),
        ("(b) add a CSS class -> qg drift lint red", _mut_css, lint_qg_class_map),
        ("(b) add a schema qg class w/o doc regen -> qg drift lint red", _mut_doc, lint_qg_class_map),
        ("(c) drop source_key disambiguation -> source_key lint red", _mut_source_key, lint_source_key_fork),
        ("(d) drop normalizer name -> surface_norm lint red", _mut_surface_desc, lint_surface_norm_pinning),
        ("(d) non-fixed-point surface_norm -> round-trip lint red", _mut_surface_roundtrip, lint_surface_norm_pinning),
        ("(e) new disjoint same-name field -> cross-schema lint red", _mut_disjoint_field, lint_cross_schema_disjoint_fields),
    ]
    all_ok = True
    for name, mut, lint in proofs:
        all_ok = _proof(name, mut, lint) and all_ok
    if not all_ok:
        print("\nself-test FAIL: a mutation did not turn its lint red")
        return 1
    print("\nschema coherence self-test OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="RM-21 schema-coherence lints")
    ap.add_argument("--self-test", action="store_true", help="run lints + red-first mutation proofs")
    ap.add_argument("--emit-class-map", action="store_true", help="print the regenerated class-map markdown")
    args = ap.parse_args(argv)
    if args.emit_class_map:
        sys.stdout.write(emit_class_map(Repo.load()))
        return 0
    if args.self_test:
        return self_test()
    errs = run_all(Repo.load())
    for label, e in errs:
        print("FAIL %s: %s" % (label, e))
    if errs:
        print("\n%d SCHEMA COHERENCE CHECK(S) FAILED" % len(errs))
        return 1
    print("ALL SCHEMA COHERENCE CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
