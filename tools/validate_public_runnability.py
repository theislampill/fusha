#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_public_runnability — keep provenance/public-runnability.md honest about the private qamus_wbw dependency.

It re-derives the LIVE set of `qamus_wbw` importers by scanning the repo, then reconciles them against the
machine-readable block embedded in provenance/public-runnability.md. It FAILs if:
  * a live importer is missing from the matrix (a public clone would break silently / undocumented);
  * the matrix lists a path that is no longer an importer (stale entry);
  * an importer's class is wrong — an UNGUARDED module-top-level `from qamus_wbw import …` must be recorded as
    `maintainer_only_unguarded`, a guarded/lazy one as `maintainer_only_guarded` (POKA-YOKE: a new unguarded
    importer cannot sneak in unrecorded);
  * the shared adapter (tools/qamus_wbw_adapter.py) or the public-runnable proof file is missing.

Stdlib only. CLI: [matrix.md] | --self-test. See parserplans/fusha-data-runtime-completion-pass/008 (P0-E).
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_MATRIX = os.path.join(_REPO, "provenance", "public-runnability.md")
_BLOCK = re.compile(r"<!--\s*runnability-matrix:\s*(\{.*?\})\s*-->", re.S)
_TOP = re.compile(r"^(?:from|import)\s+qamus_wbw\b")
_INDENT = re.compile(r"^\s+(?:from|import)\s+qamus_wbw\b")
_ANY = re.compile(r"\b(?:from|import)\s+qamus_wbw\b")
# the adapter is the seam (it imports qamus_wbw on purpose, lazily) and this validator mentions the name in code;
# neither is a builder/exporter importer to be listed in the matrix.
_EXCLUDE = {"tools/qamus_wbw_adapter.py", "tools/validate_public_runnability.py"}


def scan_importers(repo_root):
    """Return {rel_path: 'maintainer_only_unguarded'|'maintainer_only_guarded'} for every file that imports qamus_wbw."""
    out = {}
    for dirpath, dirs, files in os.walk(repo_root):
        # skip VCS, caches, sibling worktrees, AND generated/output/vendor dirs — `out/`, `dist/`, `build/` can hold a
        # LOCAL COPY of the private qamus_wbw package (the maintainer's build output); those are not authored repo
        # source and must never be flagged as unrecorded importers (the authored importers live in tools/ + qamus/scripts/).
        dirs[:] = [d for d in dirs
                   if d not in (".git", "__pycache__", "_worktrees", "node_modules", "out", "dist", "build", ".idea", ".venv")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), repo_root).replace("\\", "/")
            if rel in _EXCLUDE:
                continue
            try:
                lines = open(os.path.join(dirpath, fn), encoding="utf-8").read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            if not any(_ANY.search(ln) for ln in lines):
                continue
            toplevel = any(_TOP.match(ln) for ln in lines)
            out[rel] = "maintainer_only_unguarded" if toplevel else "maintainer_only_guarded"
    return out


def parse_matrix(matrix_path):
    text = open(matrix_path, encoding="utf-8").read()
    m = _BLOCK.search(text)
    if not m:
        raise ValueError("no runnability-matrix machine block in %s" % matrix_path)
    return json.loads(m.group(1))


def validate(repo_root=_REPO, matrix_path=_MATRIX):
    errs = []
    try:
        matrix = parse_matrix(matrix_path)
    except (ValueError, json.JSONDecodeError) as e:
        return ["matrix unparseable: %s" % e]
    declared = matrix.get("importers", {})
    live = scan_importers(repo_root)

    for rel, cls in sorted(live.items()):
        if rel not in declared:
            errs.append("live qamus_wbw importer NOT in the matrix: %s (%s)" % (rel, cls))
        elif declared[rel] != cls:
            errs.append("matrix misclassifies %s: declared %r but live is %r" % (rel, declared[rel], cls))
    for rel in sorted(declared):
        if rel not in live:
            errs.append("matrix lists a stale (non-importer) path: %s" % rel)

    for key in ("shared_adapter", "public_runnable_proof"):
        p = matrix.get(key)
        if not p or not os.path.exists(os.path.join(repo_root, p)):
            errs.append("matrix %s points at a missing file: %r" % (key, p))
    return errs


def _self_test():
    import tempfile
    failures = []

    def write(d, rel, body):
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)

    with tempfile.TemporaryDirectory() as d:
        write(d, "tools/qamus_wbw_adapter.py", "x=1\n")
        write(d, "tools/test_token_irab_help.py", "x=1\n")
        write(d, "b_unguarded.py", "import os\nfrom qamus_wbw import expand as X\n")
        write(d, "b_guarded.py", "def f():\n    from qamus_wbw import expand as X\n    return X\n")
        good_block = {"shared_adapter": "tools/qamus_wbw_adapter.py",
                      "public_runnable_proof": "tools/test_token_irab_help.py",
                      "importers": {"b_unguarded.py": "maintainer_only_unguarded",
                                    "b_guarded.py": "maintainer_only_guarded"}}
        mpath = os.path.join(d, "matrix.md")
        open(mpath, "w", encoding="utf-8").write("doc\n<!-- runnability-matrix: %s -->\n" % json.dumps(good_block))
        if validate(d, mpath):
            failures.append("a correct matrix should pass: %s" % validate(d, mpath))

        # add a NEW unguarded importer not in the matrix -> must fail (the poka-yoke)
        write(d, "b_new.py", "from qamus_wbw import normalize as N\n")
        if not any("NOT in the matrix" in e for e in validate(d, mpath)):
            failures.append("a new unrecorded unguarded importer was not caught")

        # misclassification: declare the unguarded one as guarded -> must fail
        bad_block = json.loads(json.dumps(good_block))
        bad_block["importers"]["b_unguarded.py"] = "maintainer_only_guarded"
        bad_block["importers"]["b_new.py"] = "maintainer_only_unguarded"
        open(mpath, "w", encoding="utf-8").write("<!-- runnability-matrix: %s -->\n" % json.dumps(bad_block))
        if not any("misclassifies" in e for e in validate(d, mpath)):
            failures.append("a misclassified importer was not caught")

    # the REAL repo matrix must currently reconcile
    real = validate()
    if real:
        failures.append("real repo matrix is out of sync: %s" % real[:4])

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   validate_public_runnability self-test: matrix reconciles with live importers; new/unrecorded + "
              "misclassified unguarded importers are caught; real repo matrix in sync")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Reconcile the public-runnability matrix with live qamus_wbw importers.")
    ap.add_argument("matrix", nargs="?", default=_MATRIX)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    errs = validate(matrix_path=a.matrix)
    for e in errs:
        print("FAIL " + e)
    print("public-runnability matrix: %d violation(s)" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
