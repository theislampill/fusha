#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_eval_coverage — REPORT (read-only) the coverage of the nahw/sarf eval banks (criticism: which banks are
exercised, which are dark).

The eval banks under nahw/evals/ and sarf/evals/ accreted over many tranches, but only ONE has a dedicated runner
(tools/run_grammar_evals.py, which structurally gates grammar-problems-derived-eval.jsonl). Every other *.jsonl bank
is referenced only by builders/validators or not at all — a silent coverage gap. The honest response is to MEASURE
it, not to assume green. This tool:
  * discovers every *.jsonl bank under nahw/evals/ and sarf/evals/;
  * reports per-bank row counts (valid rows / blank lines / malformed lines), total banks, total rows;
  * classifies each bank as RUNNER (its basename is referenced by some tools/run_*.py) or NONE (the coverage gap),
    by scanning the run_*.py sources — basename match catches both the slash form ("evals/x.jsonl") and the
    os.path.join tuple form ("evals", "x.jsonl");
  * flags any bank that is empty (0 valid rows) or malformed (a non-blank line that is not valid JSON).

It is strictly READ-ONLY: it writes NO file (unlike run_grammar_evals.py, which writes a scoreboard). It authors
nothing. Wiring a runner for a dark bank is a separate authoring step. Deterministic (no clock/random; time, if ever
needed, is passed in). Leak-safe: the rendered report carries only relative paths + basenames + counts, never row
content, and is scanned through tools/leak_sot before it is printed.

Stdlib only; dry-run. CLI: [--root DIR] [--strict] | --self-test.
  default     report-only; exit 1 only if a REAL bank is unreadable or empty (a malformed real bank also fails).
  --strict    additionally exit 1 if any bank has NO runner (treats the coverage gap as a failure).

See parserplans/fusha-data-runtime-completion-pass (P1-5 eval-bank coverage reporter).
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.join(_HERE, "..")
EVAL_DIRS = ("nahw/evals", "sarf/evals")  # the two bank roots, in deterministic order

try:
    import leak_sot  # the single source-of-truth leak matcher (tools/ is on sys.path when run as a script)
except ImportError:  # pragma: no cover - import-path fallback when imported as a module
    sys.path.insert(0, _HERE)
    import leak_sot


def discover_banks(repo_root=_REPO):
    """Return the sorted list of relative *.jsonl bank paths under the eval dirs (deterministic; missing dir = skip)."""
    out = []
    for d in EVAL_DIRS:
        absdir = os.path.join(repo_root, d)
        if not os.path.isdir(absdir):
            continue
        for fn in os.listdir(absdir):
            if fn.endswith(".jsonl"):
                out.append((d + "/" + fn))
    return sorted(out)


def read_bank(path):
    """Count valid JSON rows, blank lines, and malformed (non-blank non-JSON) lines. Never raises on bad content;
    an OSError (unreadable file) propagates to the caller, which decides whether that is fatal."""
    rows = 0
    blank = 0
    malformed = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                blank += 1
                continue
            try:
                json.loads(line)
                rows += 1
            except (ValueError, json.JSONDecodeError):
                malformed += 1
    return {"rows": rows, "blank": blank, "malformed": malformed}


def runner_basenames(repo_root=_REPO):
    """Return the set of bank BASENAMES referenced by any tools/run_*.py source. Basename match (not full-path) so it
    catches both the literal slash form and the os.path.join("nahw","evals","x.jsonl") tuple form a runner may use."""
    tools_dir = os.path.join(repo_root, "tools")
    refs = set()
    if not os.path.isdir(tools_dir):
        return refs
    for fn in sorted(os.listdir(tools_dir)):
        if not (fn.startswith("run_") and fn.endswith(".py")):
            continue
        try:
            text = open(os.path.join(tools_dir, fn), encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        # collect every "<name>.jsonl" basename literal mentioned anywhere in the runner source
        for tok in text.replace('"', " ").replace("'", " ").replace("/", " ").replace("\\", " ").split():
            if tok.endswith(".jsonl"):
                refs.add(tok)
    return refs


def report(repo_root=_REPO):
    """Build the coverage report structure. Pure read; never writes."""
    banks = discover_banks(repo_root)
    runner_refs = runner_basenames(repo_root)
    items = []
    unreadable = []
    for rel in banks:
        absp = os.path.join(repo_root, rel.replace("/", os.sep))
        base = os.path.basename(rel)
        try:
            counts = read_bank(absp)
        except OSError as e:
            unreadable.append({"bank": rel, "error": type(e).__name__})
            continue
        items.append({
            "bank": rel,
            "basename": base,
            "rows": counts["rows"],
            "blank": counts["blank"],
            "malformed": counts["malformed"],
            "has_runner": base in runner_refs,
            "empty": counts["rows"] == 0,
        })
    total_rows = sum(i["rows"] for i in items)
    with_runner = [i["bank"] for i in items if i["has_runner"]]
    no_runner = [i["bank"] for i in items if not i["has_runner"]]
    empty = [i["bank"] for i in items if i["empty"]]
    malformed = [i["bank"] for i in items if i["malformed"]]
    # ALSO discover *.json (object-form) eval artifacts under the same dirs. This reporter row-counts only the
    # line-oriented *.jsonl banks, but the .json files are surfaced explicitly so they are NOT silently excluded.
    json_artifacts = []
    for d in EVAL_DIRS:
        ad = os.path.join(repo_root, d.replace("/", os.sep))
        if os.path.isdir(ad):
            for fn in sorted(os.listdir(ad)):
                if fn.endswith(".json"):
                    json_artifacts.append(d + "/" + fn)
    return {
        "total_banks": len(banks),
        "banks_read": len(items),
        "total_rows": total_rows,
        "with_runner": with_runner,
        "no_runner": no_runner,
        "empty_banks": empty,
        "malformed_banks": malformed,
        "unreadable_banks": unreadable,
        "json_artifacts": json_artifacts,
        "items": items,
    }


def render(rep):
    lines = ["eval-bank coverage report",
             "  banks discovered: %d (read %d)" % (rep["total_banks"], rep["banks_read"]),
             "  total rows across banks: %d" % rep["total_rows"],
             "  banks WITH a runner: %d   banks with NONE (coverage gap): %d"
             % (len(rep["with_runner"]), len(rep["no_runner"]))]
    lines.append("  per bank:")
    for i in rep["items"]:
        tags = []
        if i["empty"]:
            tags.append("EMPTY")
        if i["malformed"]:
            tags.append("MALFORMED:%d" % i["malformed"])
        if i["blank"]:
            tags.append("blank:%d" % i["blank"])
        tag = ("  [" + ", ".join(tags) + "]") if tags else ""
        lines.append("    %-7s %4d rows  %s%s"
                     % ("RUNNER" if i["has_runner"] else "none", i["rows"], i["bank"], tag))
    if rep["no_runner"]:
        lines.append("  coverage gap (no dedicated runner): " + ", ".join(rep["no_runner"]))
    else:
        lines.append("  coverage gap (no dedicated runner): none")
    for b in rep["empty_banks"]:
        lines.append("    EMPTY bank (0 valid rows): " + b)
    for b in rep["malformed_banks"]:
        lines.append("    MALFORMED bank (has a non-JSON line): " + b)
    for u in rep["unreadable_banks"]:
        lines.append("    UNREADABLE bank: %s (%s)" % (u["bank"], u["error"]))
    if rep.get("json_artifacts"):
        lines.append("  non-jsonl .json eval artifacts (object-form; surfaced but NOT row-counted by this reporter): "
                     "%d — %s" % (len(rep["json_artifacts"]), ", ".join(rep["json_artifacts"])))
    lines.append("  note: report-only — a 'none' bank is a wiring gap, NOT a defect; wire a runner by AUTHORING "
                 "structural gates (style: tools/run_grammar_evals.py), never by mass-generating filler rows.")
    return "\n".join(lines)


def _safe_render(rep):
    """Render, then tripwire the rendered text through the leak SoT so a poisoned bank path/basename can never echo
    into a committed/printed public report. Returns (text, leak_hits)."""
    text = render(rep)
    return text, leak_sot.scan(text)


def _self_test():
    import tempfile
    failures = []

    def write(d, rel, body):
        p = os.path.join(d, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)
        return p

    with tempfile.TemporaryDirectory() as d:
        # a good bank (3 rows + 1 blank), an EMPTY bank (only blanks), a MALFORMED bank (one bad line)
        write(d, "nahw/evals/good-eval.jsonl", '{"id":1}\n{"id":2}\n\n{"id":3}\n')
        write(d, "nahw/evals/empty-eval.jsonl", "\n   \n")
        write(d, "sarf/evals/malformed-eval.jsonl", '{"ok":1}\nnot json here\n')
        # a synthetic runner that references ONLY good-eval.jsonl (via the os.path.join tuple form, to prove
        # basename matching works regardless of slash-vs-tuple) -> good has a runner, the other two are the gap
        write(d, "tools/run_good.py",
              'EVAL = os.path.join(ROOT, "nahw", "evals", "good-eval.jsonl")\n')
        # a non-runner tool referencing a bank must NOT count as a runner (only run_*.py is scanned)
        write(d, "tools/validate_x.py", 'P = "sarf/evals/malformed-eval.jsonl"\n')

        rep = report(d)
        if rep["total_banks"] != 3:
            failures.append("expected 3 banks, got %d" % rep["total_banks"])
        rows_by_base = {i["basename"]: i["rows"] for i in rep["items"]}
        if rows_by_base.get("good-eval.jsonl") != 3:
            failures.append("good bank should have 3 rows, got %s" % rows_by_base.get("good-eval.jsonl"))
        if "nahw/evals/empty-eval.jsonl" not in rep["empty_banks"]:
            failures.append("empty bank not flagged EMPTY")
        if "sarf/evals/malformed-eval.jsonl" not in rep["malformed_banks"]:
            failures.append("malformed bank not flagged MALFORMED")
        # runner classification: good has a runner; the other two are the gap
        if "nahw/evals/good-eval.jsonl" not in rep["with_runner"]:
            failures.append("good bank (referenced by run_good.py via tuple form) not classified RUNNER")
        if "nahw/evals/empty-eval.jsonl" not in rep["no_runner"]:
            failures.append("empty bank should be in the no-runner coverage gap")
        # validate_x.py is NOT a run_*.py, so malformed bank must remain in the gap despite being referenced
        if "sarf/evals/malformed-eval.jsonl" not in rep["no_runner"]:
            failures.append("a non-run_*.py reference wrongly counted as a runner")
        # render must mention the gap and the EMPTY flag, and must be leak-clean
        text, hits = _safe_render(rep)
        if "coverage gap" not in text or "EMPTY" not in text:
            failures.append("render missing gap/EMPTY surfacing")
        if hits:
            failures.append("synthetic report tripped the leak SoT: %s" % hits)

    # REAL run: the live repo must be readable, every bank non-empty + well-formed, and the report leak-clean.
    real = report()
    if real["total_banks"] < 1:
        failures.append("real repo discovered 0 eval banks (path wrong?)")
    if real["unreadable_banks"]:
        failures.append("real repo has unreadable banks: %s" % real["unreadable_banks"])
    if real["empty_banks"]:
        failures.append("real repo has empty banks: %s" % real["empty_banks"])
    if real["malformed_banks"]:
        failures.append("real repo has malformed banks: %s" % real["malformed_banks"])
    rtext, rhits = _safe_render(real)
    if rhits:
        failures.append("real report tripped the leak SoT: %s" % rhits)
    # exactly one bank should currently carry a dedicated runner (grammar-problems-derived-eval.jsonl)
    if not any(b.endswith("grammar-problems-derived-eval.jsonl") for b in real["with_runner"]):
        failures.append("grammar-problems-derived-eval.jsonl expected to be RUNNER-covered but was not")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_eval_coverage self-test: discovers nahw+sarf banks; per-bank row/blank/malformed counts; "
              "EMPTY + MALFORMED flagged; runner-vs-none gap via run_*.py basename match (tuple form too); real repo "
              "all banks readable+non-empty+well-formed; report leak-clean; READ-ONLY (writes nothing)")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Report nahw/sarf eval-bank coverage (read-only; no generation).")
    ap.add_argument("--root", default=_REPO, help="repo root (default: parent of tools/)")
    ap.add_argument("--strict", action="store_true", help="also exit 1 if any bank has no dedicated runner")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    rep = report(a.root)
    text, hits = _safe_render(rep)
    if hits:  # never print a report that trips the leak tripwire
        print("FAIL eval-coverage report tripped the leak SoT: %s" % hits)
        return 1
    print(text)
    rc = 0
    # FAIL only on a genuinely broken REAL bank: unreadable, empty, or malformed.
    if rep["unreadable_banks"] or rep["empty_banks"] or rep["malformed_banks"]:
        rc = 1
    if a.strict and rep["no_runner"]:
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
