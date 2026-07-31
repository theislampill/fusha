#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_eval_coverage — REPORT (read-only) the coverage of the nahw/sarf eval banks (criticism: which banks are
exercised, which are dark).

The eval banks under nahw/evals/ and sarf/evals/ accreted over many tranches. Two runners are registered today
(tools/run_grammar_evals.py over one nahw bank; tools/run_sarf_evals.py over the sarf contract), and most banks are
still referenced only by builders/validators or not at all — a silent coverage gap. The honest response is to
MEASURE it, not to assume green. This tool:
  * discovers every eval artifact under nahw/evals/ and sarf/evals/ in BOTH forms: line-oriented *.jsonl banks and
    object-form *.json banks whose rows live in a cases[]/assertions[] array. Both forms are ROW-COUNTED — an
    object-form bank used to be surfaced but not counted, which understated the dark population;
  * reports per-bank row counts (valid rows / blank lines / malformed lines), total banks, total rows;
  * derives execution ONLY from an explicitly REGISTERED ENTRYPOINT (RUNNER_ENTRYPOINTS) that is actually
    invoked, never from source text, basenames, constants or comments. A bank `has_runner` when a registered
    runner returned a result for it (or, for a runner whose covered bank is a module-level constant, when that
    module and constant resolve). Adding a comment that mentions a bank or a contract can no longer manufacture
    coverage;
  * separates three different things, and names them differently on purpose:
      `has_runner`            — a registered entrypoint really produced a result for this bank (minimum invariant),
      `declared_disposition`  — what the contract SAYS (a declaration, never evidence),
      `has_behavioral_runner` — the RUNNER-LEVEL result succeeded (exit code 0, no global failures, a valid
                                result schema, the expected entrypoint, and a module resolved inside repo_root)
                                AND the per-bank result shows nonzero applicable rows, zero failures, a proven
                                invoked consumer whose observed call count equals the applicable rows, and decided
                                rows equal to applicable rows. A failed or invalid runner result makes every
                                derived coverage claim false. Anything short of that is a gap;
  * flags any bank that is empty (0 valid rows) or malformed (a non-blank line that is not valid JSON).

It is strictly READ-ONLY: it writes NO file (unlike run_grammar_evals.py, which writes a scoreboard). It authors
nothing. Wiring a runner for a dark bank is a separate authoring step. Deterministic (no clock/random; time, if ever
needed, is passed in). Leak-safe: the rendered report carries only relative paths + basenames + counts, never row
content, and is scanned through tools/leak_sot before it is printed.

Stdlib only; dry-run. CLI: [--root DIR] [--strict] [--strict-sarf] | --self-test.
  default        report-only; exit 1 only if a REAL bank is unreadable or empty (a malformed real bank also fails).
  --strict       additionally exit 1 if ANY bank has no invoked runner result (nahw banks included).
  --strict-sarf  DISPOSITION-COMPLETENESS gate for sarf/evals: every sarf bank must come back from an invoked
                 registered runner and carry a declared disposition. It is NOT a behavioural-coverage claim.

See parserplans/fusha-data-runtime-completion-pass (P1-5 eval-bank coverage reporter).
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.join(_HERE, "..")
EVAL_DIRS = ("nahw/evals", "sarf/evals")  # the two bank roots, in deterministic order
# Explicitly registered runner entrypoints. Nothing else counts as execution evidence.
#   invoked_contract_runner — import the module, call `callable`(root) and use the per-bank RESULT it returns.
#   declared_bank_constant  — import the module and resolve a module-level constant naming the bank it runs.
# Both require the module file to exist under the inspected root, so a synthetic root without the runner gets no
# coverage, and a comment mentioning a bank or a contract proves nothing.
RUNNER_ENTRYPOINTS = (
    {"module": "tools/run_sarf_evals.py", "import": "tools.run_sarf_evals", "kind": "invoked_contract_runner",
     "callable": "run_all"},
    {"module": "tools/run_grammar_evals.py", "import": "tools.run_grammar_evals", "kind": "declared_bank_constant",
     "attr": "EVAL"},
    # A2 (Burst A2 naḥw lane). Same architecture, its own result schema. Registered because the runner is
    # INVOKED and its per-bank rows carry decided-row and observed-consumer-call counts; nothing here is
    # inferred from a filename, a comment, a declared disposition or a failed run.
    {"module": "tools/run_nahw_evals.py", "import": "tools.run_nahw_evals", "kind": "invoked_contract_runner",
     "callable": "run_all", "result_schema": "qamus.nahw_eval_runner_contract.v1"},
)
# Entrypoints whose invoked result may establish BEHAVIOURAL coverage, each under its own result schema.
BEHAVIORAL_ENTRYPOINTS = ("tools/run_sarf_evals.py", "tools/run_nahw_evals.py")
# Object-form eval artifacts keep their rows under one of these array keys. A *.json under an eval dir that has
# NEITHER key is configuration (a gate SSOT, a matrix), not a bank, and is surfaced separately rather than counted.
ROW_KEYS = ("cases", "assertions")

# The registered entrypoints are imported as `tools.<module>`, so the repo root must be importable whether this
# file is run as a script (sys.path[0] == tools/) or imported as a module.
_ROOT_ABS = os.path.abspath(_REPO)
if _ROOT_ABS not in sys.path:
    sys.path.insert(0, _ROOT_ABS)

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


def discover_object_banks(repo_root=_REPO):
    """Return (banks, config) for the *.json artifacts under the eval dirs.

    An object-form artifact is a BANK when it carries a cases[]/assertions[] array; anything else under an eval dir
    is configuration (gate SSOT, matrix) and is reported separately instead of being counted as a dark bank."""
    banks, config = [], []
    for d in EVAL_DIRS:
        absdir = os.path.join(repo_root, d)
        if not os.path.isdir(absdir):
            continue
        for fn in sorted(os.listdir(absdir)):
            if not fn.endswith(".json"):
                continue
            rel = d + "/" + fn
            try:
                with open(os.path.join(absdir, fn), encoding="utf-8") as fh:
                    obj = json.load(fh)
            except (OSError, ValueError):
                config.append(rel)
                continue
            if isinstance(obj, dict) and any(isinstance(obj.get(k), list) for k in ROW_KEYS):
                banks.append(rel)
            else:
                config.append(rel)
    return sorted(banks), sorted(config)


def read_bank(path, form="jsonl"):
    """Count valid rows, blank lines, and malformed lines.

    jsonl  -> one JSON object per non-blank line.
    object -> the length of the cases[]/assertions[] array (this is what makes an object-form bank countable rather
              than merely 'surfaced'); a non-object row inside the array counts as malformed.
    Never raises on bad content; an OSError (unreadable file) propagates to the caller."""
    rows = 0
    blank = 0
    malformed = 0
    if form == "object":
        with open(path, encoding="utf-8") as fh:
            try:
                obj = json.load(fh)
            except ValueError:
                return {"rows": 0, "blank": 0, "malformed": 1}
        for key in ROW_KEYS:
            if isinstance(obj.get(key), list):
                for row in obj[key]:
                    if isinstance(row, dict):
                        rows += 1
                    else:
                        malformed += 1
        return {"rows": rows, "blank": blank, "malformed": malformed}
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


RESULT_SCHEMA_ID = "qamus.sarf_eval_runner_contract.v1"
RESULT_REQUIRED_KEYS = ("schema", "banks", "failures", "exit_code", "total_rows")

# ---------------------------------------------------------------------------
# A2 ownership allowlist (round 8) — the REPORTER's own copy, deliberately not imported from the runner
# ---------------------------------------------------------------------------
# ROUND-8 defect: this reporter took the runner's word for the bank path, the row count, the consumer, the
# declared disposition, the observed call count, the quarantine count and the unowned axes. A runner that
# reported seven items with any of those fields altered — a foreign bank, a duplicate item, a `1/1/1` claim
# against a 20-row artifact, a nonexistent consumer, a quarantined artifact relabelled implemented — was
# believed. The reporter now carries the allowlist ITSELF and re-derives every denominator, so a dishonest
# runner result is rejected rather than reproduced. Importing the map from the runner would defeat the point.
A2_ENTRYPOINT = "tools/run_nahw_evals.py"
A2_RESULT_SCHEMA = "qamus.nahw_eval_runner_contract.v1"
A2_OWNERSHIP = {
    "nahw/evals/public-boundary-scanner-eval.jsonl":
        ("tools/leak_sot.py:LEAK_RE.search", "implemented_and_consumed"),
    "nahw/evals/largelexicon-function-collision-safety.jsonl":
        ("tools/fusha_context_parser.py:collision_status", "implemented_and_consumed"),
    "nahw/evals/hover-context-eval.json":
        ("tools/fusha_nahw_particle_rules.py:resolve_particle_homograph", "fixture_only"),
    "nahw/evals/nahw-state-machine-eval.json":
        ("tools/fusha_nahw_particle_rules.py:resolve_particle_homograph", "fixture_only"),
    "nahw/evals/grammar-wrong-reasoning-cases.jsonl": (None, "fixture_only"),
    "nahw/evals/particle-function-eval.jsonl":
        ("tools/fusha_nahw_particle_rules.py:resolve_particle_homograph", "fixture_only"),
    "nahw/evals/irab-polysemy-eval.jsonl": (None, "fixture_only"),
}
# consumer id -> (module file that must exist under the reviewed root, attribute that must exist)
#
# ROUND-9 defect: the import name used to be written out by hand, and for the leak consumer it was the
# top-level key `leak_sot` — but tools/run_nahw_evals.py binds that consumer with
#     from tools.leak_sot import LEAK_RE
# so the key actually backing the INVOKED consumer is `tools.leak_sot`. Preloading sys.modules with a
# foreign `tools.leak_sot` therefore ran the real scan from another checkout while this check, looking at a
# key nobody had bound, still reported the consumer repository-local and raised no rejection.
#
# The import name is no longer written by hand at all. consumer_module_keys() DERIVES every key the file
# could be bound under from the file path itself, so this check can never again drift from the key the
# runner really imports.
A2_CONSUMER_MODULES = {
    "tools/leak_sot.py:LEAK_RE.search": ("tools/leak_sot.py", "LEAK_RE"),
    "tools/fusha_context_parser.py:collision_status":
        ("tools/fusha_context_parser.py", "collision_status"),
    "tools/fusha_nahw_particle_rules.py:resolve_particle_homograph":
        ("tools/fusha_nahw_particle_rules.py", "resolve_particle_homograph"),
}


def consumer_module_keys(rel):
    """Every sys.modules key `rel` could be bound under, derived from the path — never hand-written.

    `tools/leak_sot.py` -> ("tools.leak_sot", "leak_sot"): the dotted package path the runner imports, and
    the bare name a `tools/`-on-sys.path import produces. BOTH are checked, because either one can be the
    object the invoked consumer actually came from.
    """
    stem = rel[:-len(".py")] if rel.endswith(".py") else rel
    parts = [p for p in stem.split("/") if p]
    keys = [".".join(parts)]
    if len(parts) > 1:
        keys.append(parts[-1])
    return tuple(keys)
# Exact per-item field types. A string where an int belongs, or a metrics block that is not a mapping, is a
# malformed item and disqualifies the WHOLE result — not just that row.
A2_ITEM_TYPES = (("bank", str), ("rows", int), ("checked", int), ("failures", list),
                 ("disposition", str), ("metrics", dict))


def _int_field(value):
    """True for a real integer count. `True` is an int in Python; a boolean is not a count."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def consumer_module_resolves(consumer, repo_root):
    """The credited consumer must exist as a file under THIS root, and EVERY already-imported module it
    could be bound under must be the one from this root — a preloaded same-named module from another
    checkout is not evidence, whichever key it was installed at."""
    slot = A2_CONSUMER_MODULES.get(consumer)
    if slot is None:
        return False
    rel, attr = slot
    if not os.path.exists(os.path.join(repo_root, rel.replace("/", os.sep))):
        return False
    for key in consumer_module_keys(rel):
        mod = sys.modules.get(key)
        if mod is None:
            continue                     # not imported under this key: nothing to verify
        if not module_in_root(mod, repo_root):
            return False                 # the invoked consumer came from another checkout
        if not hasattr(mod, attr):
            return False
    return True


def a2_result_defects(rep, repo_root, discovered):
    """Validate an A2 runner result against the reporter's OWN allowlist and OWN row counts.

    `discovered` maps bank path -> the row count this reporter counted itself. Returns a list of defect
    strings; a non-empty list makes the entire result unusable (no has_runner, no behavioural credit).
    """
    defects = []
    if rep.get("ok") is not True:
        defects.append("result does not declare ok is True (got %r)" % rep.get("ok"))
    items = rep.get("banks")
    if not isinstance(items, list):
        return defects + ["result banks is not a list"]
    seen = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            defects.append("banks[%d] is not a mapping" % index)
            continue
        for field, kind in A2_ITEM_TYPES:
            value = item.get(field)
            if kind is int:
                if not _int_field(value):
                    defects.append("banks[%d].%s is not a non-negative integer (%r)" % (index, field, value))
            elif not isinstance(value, kind):
                defects.append("banks[%d].%s is not %s (%r)" % (index, field, kind.__name__, type(value).__name__))
        seen.append(item.get("bank"))
    if defects:
        return defects
    if len(set(seen)) != len(seen):
        defects.append("result carries duplicate items for %s"
                       % sorted({b for b in seen if seen.count(b) > 1}))
    if set(seen) != set(A2_OWNERSHIP):
        unknown = sorted(set(seen) - set(A2_OWNERSHIP))
        missing = sorted(set(A2_OWNERSHIP) - set(seen))
        defects.append("result artifact set is not the A2 allowlist (unknown %s; missing %s)" % (unknown, missing))
    if defects:
        return defects
    total = 0
    for item in items:
        rel = item["bank"]
        consumer, disposition = A2_OWNERSHIP[rel]
        real_rows = discovered.get(rel)
        if real_rows is None:
            defects.append("%s: the reporter could not count this artifact itself" % rel)
        elif item["rows"] != real_rows:
            defects.append("%s: runner claims %d rows; the reporter counted %d"
                           % (rel, item["rows"], real_rows))
        if item["disposition"] != disposition:
            defects.append("%s: runner declares disposition %r; the allowlist binds %r"
                           % (rel, item["disposition"], disposition))
        if item.get("behavioral_consumer") != consumer:
            defects.append("%s: runner names consumer %r; the allowlist binds %r"
                           % (rel, item.get("behavioral_consumer"), consumer))
        if consumer is not None and not consumer_module_resolves(consumer, repo_root):
            defects.append("%s: consumer %s does not resolve beneath the reviewed root" % (rel, consumer))
        calls = (item.get("metrics") or {}).get("consumer_calls")
        if not isinstance(calls, dict):
            defects.append("%s: metrics.consumer_calls is not a mapping" % rel)
        elif consumer is not None and not _int_field(calls.get(consumer)):
            defects.append("%s: no observed call count for %s" % (rel, consumer))
        if not _int_field((item.get("metrics") or {}).get("quarantined")):
            defects.append("%s: metrics.quarantined is not a count" % rel)
        total += item["rows"]
    if not defects and rep.get("total_rows") != total:
        defects.append("result total_rows %r != the sum of its item rows (%d)" % (rep.get("total_rows"), total))
    return defects


def result_is_usable(rep, ep, repo_root=None, discovered=None):
    """Runner-LEVEL success. A per-bank row that looks clean inside a failed run proves nothing.

    Round-4 defect: an invoked result with exit_code 1 and a schema error still produced behavioural coverage from
    otherwise clean per-bank rows.
    Round-8: for the A2 entrypoint, the result must additionally survive the reporter's own ownership,
    uniqueness, type and row-denominator validation."""
    if not isinstance(rep, dict):
        return False, "runner returned no result object"
    missing = [k for k in RESULT_REQUIRED_KEYS if k not in rep]
    if missing:
        return False, "runner result is missing %s" % missing
    expected_schema = ep.get("result_schema", RESULT_SCHEMA_ID)
    if rep.get("schema") != expected_schema:
        return False, "runner result schema is %r" % rep.get("schema")
    if rep.get("exit_code") != 0:
        return False, "runner exited %r" % rep.get("exit_code")
    if rep.get("failures"):
        return False, "runner reported %d global failure(s)" % len(rep["failures"])
    if not isinstance(rep.get("banks"), list) or not rep["banks"]:
        return False, "runner result carries no bank rows"
    if ep["module"] == A2_ENTRYPOINT:
        if expected_schema != A2_RESULT_SCHEMA:
            return False, "the A2 entrypoint is registered under the wrong result schema"
        defects = a2_result_defects(rep, repo_root if repo_root is not None else _REPO, discovered or {})
        if defects:
            return False, "A2 result rejected: %s" % defects[0]
    return True, ""


def module_in_root(mod, repo_root):
    """The imported entrypoint must be the one that lives under the inspected root, not a same-named module."""
    path = getattr(mod, "__file__", None)
    if not path:
        return False
    base = os.path.realpath(os.path.abspath(repo_root))
    real = os.path.realpath(path)
    return real == base or real.startswith(base + os.sep)


def runner_results(repo_root=_REPO, invoke=None, discovered=None, rejected=None):
    """{bank path -> result dict} from the REGISTERED entrypoints, by invoking them. Never a source-text scan.

    A result carries what the runner actually observed: rows, decided_rows, failure count, the declared disposition
    and the declared per-row consumer with its OBSERVED call count. `report()` derives coverage from these, so a
    declaration alone can never manufacture a behavioural runner."""
    out = {}
    for ep in RUNNER_ENTRYPOINTS:
        if not os.path.exists(os.path.join(repo_root, ep["module"].replace("/", os.sep))):
            continue  # the entrypoint is not present under this root: no execution, no coverage
        try:
            mod = __import__(ep["import"], fromlist=["*"])
        except Exception:  # noqa: BLE001  an unimportable runner provides no evidence
            continue
        if not module_in_root(mod, repo_root):
            continue  # a module resolved outside repo_root is not this repository's runner
        if ep["kind"] == "invoked_contract_runner":
            try:
                rep = (invoke or (lambda m, e, r: getattr(m, e["callable"])(r)))(mod, ep, repo_root)
            except Exception:  # noqa: BLE001  a runner that cannot run proves nothing
                continue
            ok, why = result_is_usable(rep, ep, repo_root, discovered or {})
            if not ok:
                # ROUND-8: an unusable result yields NEITHER has_runner NOR behavioural credit. It is recorded
                # so the reason stays visible, but it never becomes an execution claim.
                if rejected is not None:
                    rejected.append({"entrypoint": ep["module"], "reason": why})
                continue
            for item in (rep.get("banks") or []) if isinstance(rep, dict) else []:
                calls = (item.get("metrics") or {}).get("consumer_calls") or {}
                primary = item.get("behavioral_consumer")
                out[item["bank"]] = {
                    "entrypoint": ep["module"], "invoked": True,
                    "runner_ok": ok, "runner_status": why or "ok",
                    "rows": item.get("rows", 0), "decided_rows": item.get("checked", 0),
                    "failures": len(item.get("failures") or []),
                    "declared_disposition": item.get("disposition"),
                    "declared_consumer": primary,
                    "observed_consumer_calls": calls.get(primary, 0) if primary else 0,
                    # A2: quarantined rows and unowned axes stay VISIBLE instead of being folded into coverage
                    "quarantined_rows": (item.get("metrics") or {}).get("quarantined", 0),
                    "unowned_axes": (item.get("metrics") or {}).get("unowned_axes") or {},
                    "runner_bank": (item.get("metrics") or {}).get("runner_bank"),
                    # the reporter's OWN row count, carried alongside the runner's claim
                    "discovered_rows": (discovered or {}).get(item["bank"]),
                }
        elif ep["kind"] == "declared_bank_constant":
            value = getattr(mod, ep["attr"], None)
            if not isinstance(value, str) or not os.path.exists(value):
                continue
            rel = os.path.relpath(value, os.path.abspath(repo_root)).replace(os.sep, "/")
            out[rel] = {"entrypoint": ep["module"], "invoked": False, "rows": None, "decided_rows": 0,
                        "failures": 0, "declared_disposition": None, "declared_consumer": None,
                        "observed_consumer_calls": 0}
    return out


def behavioral_coverage(result, expected_entrypoint=BEHAVIORAL_ENTRYPOINTS, bank=None, repo_root=None):
    """True only when a SUCCESSFUL invoked result proves the bank's rows were decided by its declared consumer.

    ROUND-8: for the A2 entrypoint the consumer and the disposition are taken from the reporter's OWN
    allowlist, the denominator is the reporter's OWN row count, and a quarantined row or an unowned axis
    forfeits credit outright. Relabelling a fixture-only or quarantined artifact `implemented_and_consumed`
    therefore buys nothing.
    """
    allowed = (expected_entrypoint,) if isinstance(expected_entrypoint, str) else tuple(expected_entrypoint)
    if not result or not result.get("invoked"):
        return False
    if not result.get("runner_ok"):
        return False
    if result.get("entrypoint") not in allowed:
        return False
    if result.get("declared_disposition") != "implemented_and_consumed":
        return False
    rows = result.get("rows") or 0
    if rows <= 0 or result.get("failures"):
        return False
    consumer = result.get("declared_consumer")
    if not consumer:
        return False
    if result.get("entrypoint") == A2_ENTRYPOINT:
        if bank not in A2_OWNERSHIP:
            return False
        allow_consumer, allow_disposition = A2_OWNERSHIP[bank]
        if consumer != allow_consumer or allow_disposition != "implemented_and_consumed":
            return False
        if not consumer_module_resolves(consumer, repo_root if repo_root is not None else _REPO):
            return False
        discovered = result.get("discovered_rows")
        if discovered is None or discovered != rows:
            return False
        if result.get("quarantined_rows"):
            return False
        if result.get("unowned_axes"):
            return False
        # at least one real observed call per row; a consumer may legitimately be asked more than once
        return result.get("decided_rows") == rows and (result.get("observed_consumer_calls") or 0) >= rows
    return result.get("decided_rows") == rows and result.get("observed_consumer_calls") == rows


def report(repo_root=_REPO):
    """Build the coverage report structure. Pure read; never writes."""
    jsonl_banks = discover_banks(repo_root)
    object_banks, json_config = discover_object_banks(repo_root)
    banks = [(b, "jsonl") for b in jsonl_banks] + [(b, "object") for b in object_banks]
    banks.sort()
    # ROUND-8: discover every row count FIRST, from the artifacts themselves, so the runner's claimed
    # denominators can be compared against a number this reporter derived independently.
    counted, unreadable = {}, []
    for rel, form in banks:
        try:
            counted[rel] = read_bank(os.path.join(repo_root, rel.replace("/", os.sep)), form)
        except OSError as e:
            unreadable.append({"bank": rel, "error": type(e).__name__})
    discovered = {rel: c["rows"] for rel, c in counted.items()}
    rejected = []
    results = runner_results(repo_root, discovered=discovered, rejected=rejected)
    items = []
    for rel, form in banks:
        base = os.path.basename(rel)
        counts = counted.get(rel)
        if counts is None:
            continue
        items.append({
            "bank": rel,
            "basename": base,
            "form": form,
            "rows": counts["rows"],
            "blank": counts["blank"],
            "malformed": counts["malformed"],
            "has_runner": rel in results,
            # Declaration vs evidence, kept apart by name. `declared_disposition` is what the contract says;
            # `has_behavioral_runner` is what the invoked run actually demonstrated.
            "declared_disposition": (results.get(rel) or {}).get("declared_disposition"),
            "has_behavioral_runner": behavioral_coverage(results.get(rel), bank=rel, repo_root=repo_root),
            "runner_status": (results.get(rel) or {}).get("runner_status"),
            "decided_rows": (results.get(rel) or {}).get("decided_rows", 0),
            "quarantined_rows": (results.get(rel) or {}).get("quarantined_rows", 0),
            "unowned_axes": (results.get(rel) or {}).get("unowned_axes") or {},
            "disposition": (results.get(rel) or {}).get("declared_disposition"),
            "empty": counts["rows"] == 0,
        })
    total_rows = sum(i["rows"] for i in items)
    with_runner = [i["bank"] for i in items if i["has_runner"]]
    no_runner = [i["bank"] for i in items if not i["has_runner"]]
    behavioral = [i["bank"] for i in items if i["has_behavioral_runner"]]
    behavioral_rows = sum(i["rows"] for i in items if i["has_behavioral_runner"])
    empty = [i["bank"] for i in items if i["empty"]]
    malformed = [i["bank"] for i in items if i["malformed"]]
    by_disposition = {}
    for i in items:
        if i["disposition"]:
            by_disposition[i["disposition"]] = by_disposition.get(i["disposition"], 0) + 1
    return {
        "total_banks": len(banks),
        "banks_read": len(items),
        "total_rows": total_rows,
        "jsonl_banks": len(jsonl_banks),
        "object_banks": len(object_banks),
        "with_runner": with_runner,
        "with_behavioral_runner": behavioral,
        "behavioral_rows": behavioral_rows,
        "no_runner": no_runner,
        "empty_banks": empty,
        "malformed_banks": malformed,
        "unreadable_banks": unreadable,
        "rejected_runner_results": rejected,
        "json_config_artifacts": json_config,
        "by_disposition": by_disposition,
        "items": items,
    }


def render(rep):
    lines = ["eval-bank coverage report",
             "  banks discovered: %d (read %d) — %d jsonl + %d object-form (cases[]/assertions[])"
             % (rep["total_banks"], rep["banks_read"], rep["jsonl_banks"], rep["object_banks"]),
             "  total rows across banks: %d" % rep["total_rows"],
             "  banks an invoked registered runner EXECUTED: %d   banks with NO runner at all: %d"
             % (len(rep["with_runner"]), len(rep["no_runner"])),
             "  banks BEHAVIOURALLY covered (proven by the invoked run, not by a declaration): %d  (%d rows); "
             "all other rows remain gaps"
             % (len(rep.get("with_behavioral_runner") or []), rep.get("behavioral_rows", 0))]
    if rep.get("by_disposition"):
        lines.append("  DECLARED dispositions (a declaration is not evidence; see the behavioural line above): "
                     + ", ".join("%s=%d" % (k, rep["by_disposition"][k]) for k in sorted(rep["by_disposition"])))
    lines.append("  per bank:")
    for i in rep["items"]:
        tags = []
        if i["empty"]:
            tags.append("EMPTY")
        if i["malformed"]:
            tags.append("MALFORMED:%d" % i["malformed"])
        if i["blank"]:
            tags.append("blank:%d" % i["blank"])
        if i.get("declared_disposition"):
            tags.append("declared:" + i["declared_disposition"])
        if i.get("has_runner") and not i.get("has_behavioral_runner"):
            tags.append("run-not-decided")
        tag = ("  [" + ", ".join(tags) + "]") if tags else ""
        lines.append("    %-7s %-6s %4d rows  %s%s"
                     % ("RUNNER" if i["has_runner"] else "none", i["form"], i["rows"], i["bank"], tag))
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
    for r in rep.get("rejected_runner_results") or []:
        lines.append("    REJECTED runner result: %s — %s (no runner claim, no behavioural credit)"
                     % (r["entrypoint"], r["reason"]))
    if rep.get("json_config_artifacts"):
        lines.append("  .json artifacts under the eval dirs that are CONFIG, not banks (no cases[]/assertions[]): "
                     "%d — %s" % (len(rep["json_config_artifacts"]), ", ".join(rep["json_config_artifacts"])))
    lines.append("  note: report-only — a 'none' bank is a wiring gap, NOT a defect; wire a runner by AUTHORING "
                 "structural gates (style: tools/run_grammar_evals.py), never by mass-generating filler rows.")
    return "\n".join(lines)


def _safe_render(rep):
    """Render, then tripwire the rendered text through the leak SoT so a poisoned bank path/basename can never echo
    into a committed/printed public report. Returns (text, leak_hits)."""
    text = render(rep)
    return text, leak_sot.scan(text)


def _strict_sarf_rc(rep):
    """The exit code --strict-sarf would produce for this report (shared by the CLI and the adversarial probes)."""
    dark = [b for b in rep["no_runner"] if b.startswith("sarf/evals/")]
    undisposed = [i["bank"] for i in rep["items"]
                  if i["bank"].startswith("sarf/evals/") and not i["declared_disposition"]]
    return 1 if (dark or undisposed) else 0


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
        # an OBJECT-form bank (rows under cases[]) must be row-counted, not merely surfaced; a *.json with no
        # cases[]/assertions[] is CONFIG and must not be reported as a dark bank.
        write(d, "sarf/evals/object-eval.json", '{"schema":"x","cases":[{"id":"a"},{"id":"b"}]}\n')
        write(d, "sarf/evals/gates-config.json", '{"schema":"gates","two_vote_required":["irab"]}\n')
        rep = report(d)
        if rep["total_banks"] != 4:
            failures.append("expected 4 banks (3 jsonl + 1 object-form), got %d" % rep["total_banks"])
        rows_by_base = {i["basename"]: i["rows"] for i in rep["items"]}
        if rows_by_base.get("good-eval.jsonl") != 3:
            failures.append("good bank should have 3 rows, got %s" % rows_by_base.get("good-eval.jsonl"))
        if rows_by_base.get("object-eval.json") != 2:
            failures.append("object-form bank must be row-counted from cases[], got %s"
                            % rows_by_base.get("object-eval.json"))
        if "sarf/evals/gates-config.json" not in rep["json_config_artifacts"]:
            failures.append("a .json with no cases[]/assertions[] must be reported as CONFIG, not as a dark bank")
        if rep["total_rows"] != 3 + 1 + 2:
            failures.append("total rows must include object-form rows, got %d" % rep["total_rows"])
        if "nahw/evals/empty-eval.jsonl" not in rep["empty_banks"]:
            failures.append("empty bank not flagged EMPTY")
        if "sarf/evals/malformed-eval.jsonl" not in rep["malformed_banks"]:
            failures.append("malformed bank not flagged MALFORMED")
        # NO registered entrypoint exists under this synthetic root, so NOTHING may be classified as covered.
        if rep["with_runner"]:
            failures.append("a root with no registered runner reported runner coverage: %s" % rep["with_runner"])
        if rep["with_behavioral_runner"]:
            failures.append("a root with no registered runner reported BEHAVIOURAL coverage: %s"
                            % rep["with_behavioral_runner"])

        # ADVERSARIAL PROBE A (no runner): a contract may declare implemented_and_consumed, but with no invoked
        # runner result the bank is NOT covered and --strict-sarf must fail.
        write(d, "sarf/eval-runner-contract.json", json.dumps({
            "schema": "qamus.sarf_eval_runner_contract.v1",
            "banks": [{"path": "sarf/evals/object-eval.json", "disposition": "implemented_and_consumed"}],
        }))
        rep_a = report(d)
        row_a = next((i for i in rep_a["items"] if i["bank"] == "sarf/evals/object-eval.json"), None)
        if row_a is None or row_a["has_runner"] or row_a["has_behavioral_runner"]:
            failures.append("PROBE A: a declaration with no invoked runner manufactured coverage")
        if _strict_sarf_rc(rep_a) == 0:
            failures.append("PROBE A: --strict-sarf passed with no invoked runner result")

        # ADVERSARIAL PROBE C (failed / invalid runner result): a per-bank row that looks clean inside a FAILED run
        # must never become coverage, and neither must a result whose schema is wrong.
        _real = report(_REPO)
        _real_rows = {i["bank"]: i["rows"] for i in _real["items"]}
        _clean_bank = next((i["bank"] for i in _real["items"] if i["has_behavioral_runner"]), None)
        if _clean_bank is None:
            failures.append("PROBE C: expected at least one behaviourally covered bank in the real repo")
        else:
            for _label, _mut in (("failed exit", lambda r: dict(r, exit_code=1)),
                                 ("global failure", lambda r: dict(r, failures=["schema invalid"], exit_code=1)),
                                 ("invalid schema", lambda r: dict(r, schema="not.the.contract.schema"))):
                _rej = []
                _res = runner_results(_REPO, invoke=lambda m, e, root, _m=_mut: _m(
                    getattr(m, e["callable"])(root)), discovered=_real_rows, rejected=_rej)
                if any(behavioral_coverage(v, bank=b, repo_root=_REPO) for b, v in _res.items()):
                    failures.append("PROBE C: a %s runner result still produced behavioural coverage" % _label)
                # ROUND-8: an unusable result is not merely flagged, it yields no has_runner claim at all
                if any(v.get("invoked") for v in _res.values()):
                    failures.append("PROBE C: a %s runner result still produced a has_runner claim" % _label)
                if not _rej:
                    failures.append("PROBE C: a %s runner result was not recorded as rejected" % _label)
            # a module resolved outside repo_root is refused

            class _Outside(object):
                __file__ = os.path.join(os.path.dirname(os.path.abspath(os.sep)), "elsewhere", "run_sarf_evals.py")
            if module_in_root(_Outside(), _REPO):
                failures.append("PROBE C: a module outside repo_root was accepted as the runner")

        # ADVERSARIAL PROBE B (comment only): adding a file that merely MENTIONS the contract/bank in a comment
        # must not change anything, because execution is taken from an invoked result, not from source text.
        write(d, "tools/run_sarf_evals.py",
              "# mentions sarf/eval-runner-contract.json and sarf/evals/object-eval.json in a comment only\n")
        rep_b = report(d)
        row_b = next((i for i in rep_b["items"] if i["bank"] == "sarf/evals/object-eval.json"), None)
        if row_b is None or row_b["has_runner"] or row_b["has_behavioral_runner"]:
            failures.append("PROBE B: a comment mentioning the contract manufactured coverage")
        if _strict_sarf_rc(rep_b) == 0:
            failures.append("PROBE B: --strict-sarf passed on a comment-only runner")
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
    if not any(b.endswith("grammar-problems-derived-eval.jsonl") for b in real["with_runner"]):
        failures.append("grammar-problems-derived-eval.jsonl expected to be RUNNER-covered but was not")
    # every sarf bank must come back from an INVOKED registered runner; a new dark sarf bank fails here.
    dark_sarf = [b for b in real["no_runner"] if b.startswith("sarf/evals/")]
    if dark_sarf:
        failures.append("sarf banks without a runner: %s" % dark_sarf)
    # and every sarf bank must carry exactly one contract disposition
    undisposed = [i["bank"] for i in real["items"]
                  if i["bank"].startswith("sarf/evals/") and not i["declared_disposition"]]
    if undisposed:
        failures.append("sarf banks with no contract disposition: %s" % undisposed)
    if not any(i["form"] == "object" and i["rows"] > 0 for i in real["items"]):
        failures.append("no object-form bank was row-counted in the real repo")
    # a bank the runner merely RUNS must never be reported as behavioural coverage
    read_only = [i["bank"] for i in real["items"]
                 if i["has_runner"] and i["declared_disposition"] and not i["has_behavioral_runner"]]
    if not read_only:
        failures.append("expected at least one runner-executed bank that is NOT behaviourally covered")
    # has_runner is the MINIMUM invariant for behavioural coverage
    for i in real["items"]:
        if i["has_behavioral_runner"] and not i["has_runner"]:
            failures.append("%s claims behavioural coverage without an invoked runner result" % i["bank"])
    if real.get("behavioral_rows", 0) >= sum(i["rows"] for i in real["items"] if i["bank"].startswith("sarf/")):
        failures.append("behavioural coverage must be strictly smaller than the sarf row population")
    # ADVERSARIAL: nahw/evals and sarf/evals hold same-named banks. A basename match would credit the nahw copies to
    # the sarf runner, which never touches them. Contract coverage is full-path, so they must stay in the gap.
    for shared in ("nahw/evals/vn00-public-visual-andon.jsonl", "nahw/evals/vn00-aggressive-false-closure.jsonl"):
        row = next((i for i in real["items"] if i["bank"] == shared), None)
        if row is not None and (row["has_runner"] or row["declared_disposition"]):
            failures.append("%s was wrongly credited to another dir's runner by basename" % shared)

    # ---------------------------------------------------------------------------
    # ROUND-8 adversarial probes: a DISHONEST A2 runner result must buy nothing
    # ---------------------------------------------------------------------------
    # Every probe below returns a result that is structurally well-formed and superficially convincing. The
    # reporter must reject it from its OWN allowlist and its OWN row counts, and must FAIL CLOSED (never raise).
    _rows = {i["bank"]: i["rows"] for i in real["items"]}
    _PB = "nahw/evals/public-boundary-scanner-eval.jsonl"
    _HOVER = "nahw/evals/hover-context-eval.json"
    _STATE = "nahw/evals/nahw-state-machine-eval.json"

    def _find(rep, bank):
        return next(i for i in rep["banks"] if i["bank"] == bank)

    def _relabel(item, **kw):
        """Present `item` as a fully consumed artifact: implemented, all rows decided, all calls observed."""
        item.update(kw)
        item["disposition"] = "implemented_and_consumed"
        item["checked"] = item["rows"]
        item["metrics"] = dict(item["metrics"], quarantined=0, unowned_axes={},
                               consumer_calls={item["behavioral_consumer"]: item["rows"]})

    def _m_counter_only(rep):
        _find(rep, _PB)["metrics"]["consumer_calls"] = {"tools/leak_sot.py:LEAK_RE.search": 0}

    def _m_wrong_path(rep):
        _find(rep, _PB)["bank"] = "nahw/evals/not-a-real-bank.jsonl"

    def _m_foreign_bank(rep):
        rep["banks"].append(dict(_find(rep, _PB), bank="sarf/evals/false-clitic-split-eval.jsonl"))

    def _m_duplicate(rep):
        rep["banks"].append(dict(_find(rep, _PB)))

    def _m_row_denominator(rep):
        item = _find(rep, _HOVER)
        item["rows"] = 1
        _relabel(item)
        rep["total_rows"] = sum(i["rows"] for i in rep["banks"])

    def _m_bad_consumer(rep):
        item = _find(rep, _PB)
        item["behavioral_consumer"] = "tools/does_not_exist.py:invented"
        item["metrics"]["consumer_calls"] = {"tools/does_not_exist.py:invented": item["rows"]}

    def _m_quarantined_relabelled(rep):
        _relabel(_find(rep, _HOVER))

    def _m_unowned_relabelled(rep):
        _relabel(_find(rep, _STATE))

    def _m_wrong_schema(rep):
        rep["schema"] = "qamus.some_other_contract.v1"

    def _m_wrong_types(rep):
        _find(rep, _PB)["rows"] = "10"

    def _m_not_a_mapping(rep):
        rep["banks"].append("not-an-item")

    def _m_ok_false(rep):
        rep["ok"] = False

    _A2_PROBES = (
        ("counter-only (consumer never invoked)", _m_counter_only, False),
        ("wrong/unknown artifact path", _m_wrong_path, True),
        ("foreign-owned bank smuggled in", _m_foreign_bank, True),
        ("duplicate item for one artifact", _m_duplicate, True),
        ("1/1/1 claim against the real denominator", _m_row_denominator, True),
        ("nonexistent consumer", _m_bad_consumer, True),
        ("quarantined artifact relabelled implemented", _m_quarantined_relabelled, True),
        ("unowned-axis artifact relabelled implemented", _m_unowned_relabelled, True),
        ("wrong result schema", _m_wrong_schema, True),
        ("wrong field type (rows as a string)", _m_wrong_types, True),
        ("a bank item that is not a mapping", _m_not_a_mapping, True),
        ("result that does not declare ok", _m_ok_false, True),
    )

    def _mutating_invoke(mutate):
        def invoke(mod, ep, root):
            rep = getattr(mod, ep["callable"])(root)
            if ep["module"] != A2_ENTRYPOINT:
                return rep
            rep = dict(rep)
            rep["banks"] = [dict(i, metrics=dict(i.get("metrics") or {})) for i in rep["banks"]]
            mutate(rep)
            return rep
        return invoke

    for _label, _mutate, _whole_result in _A2_PROBES:
        _rejected = []
        try:
            _res = runner_results(_REPO, invoke=_mutating_invoke(_mutate), discovered=_rows,
                                  rejected=_rejected)
        except Exception as exc:  # noqa: BLE001  the reporter must fail closed, never raise
            failures.append("A2 PROBE %r raised %s instead of failing closed" % (_label, type(exc).__name__))
            continue
        _a2 = {b: v for b, v in _res.items() if v.get("entrypoint") == A2_ENTRYPOINT}
        if _whole_result:
            if any(behavioral_coverage(v, bank=b, repo_root=_REPO) for b, v in _a2.items()):
                failures.append("A2 PROBE %r still produced behavioural coverage" % _label)
            if _a2:
                failures.append("A2 PROBE %r still produced a has_runner claim for %d artifact(s)"
                                % (_label, len(_a2)))
            if not any(r["entrypoint"] == A2_ENTRYPOINT for r in _rejected):
                failures.append("A2 PROBE %r was not recorded as a rejected result" % _label)
        else:
            # a per-artifact defect leaves the rest of the result usable but forfeits that artifact's credit
            if behavioral_coverage(_a2.get(_PB), bank=_PB, repo_root=_REPO):
                failures.append("A2 PROBE %r credited an artifact whose consumer was never invoked" % _label)
        # the sarf entrypoint is untouched by an A2 defect
        if not any(v.get("entrypoint") == "tools/run_sarf_evals.py" for v in _res.values()):
            failures.append("A2 PROBE %r collaterally destroyed the sarf runner's own results" % _label)

    # A foreign / preloaded module of the same name is not this repository's consumer — under ANY key it
    # could be bound at.
    #
    # ROUND-9 regression. tools/run_nahw_evals.py binds the leak consumer with
    # `from tools.leak_sot import LEAK_RE`, so the key backing the invoked consumer is `tools.leak_sot`.
    # This check previously validated only the separate top-level key `leak_sot`, so preloading
    # `tools.leak_sot` with a foreign module ran the real scan from another checkout while coverage still
    # reported the consumer repository-local, credited its 10 rows and raised no rejection. Every derived
    # key is now probed, and the exact key the runner imports is asserted to be among them.
    _leak_consumer = "tools/leak_sot.py:LEAK_RE.search"
    _leak_keys = consumer_module_keys(A2_CONSUMER_MODULES[_leak_consumer][0])
    if "tools.leak_sot" not in _leak_keys:
        failures.append("the key tools/run_nahw_evals.py actually imports (tools.leak_sot) is not probed; "
                        "derived keys were %s" % (_leak_keys,))
    for _key in _leak_keys:

        class _ForeignConsumer(object):
            """Same-named module from another checkout, carrying the attribute the reporter looks for."""
            __file__ = os.path.join(os.sep, "elsewhere", "checkout", "tools", "leak_sot.py")
            LEAK_RE = re.compile(r"unused")

        _saved, _had = sys.modules.get(_key), _key in sys.modules
        try:
            sys.modules[_key] = _ForeignConsumer()
            if consumer_module_resolves(_leak_consumer, _REPO):
                failures.append("a preloaded same-named consumer module from another checkout was accepted "
                                "at sys.modules[%r]" % _key)
            # and it must cost the artifact its behavioural credit, not merely fail a helper
            _foreign_result = {
                "entrypoint": A2_ENTRYPOINT, "invoked": True, "runner_ok": True, "rows": 10,
                "decided_rows": 10, "failures": 0, "declared_disposition": "implemented_and_consumed",
                "declared_consumer": _leak_consumer, "observed_consumer_calls": 10,
                "quarantined_rows": 0, "unowned_axes": {}, "discovered_rows": 10,
            }
            if behavioral_coverage(_foreign_result, bank="nahw/evals/public-boundary-scanner-eval.jsonl",
                                   repo_root=_REPO):
                failures.append("an otherwise-perfect result was credited while its consumer was preloaded "
                                "from another checkout at sys.modules[%r]" % _key)
        finally:
            if _had:
                sys.modules[_key] = _saved
            else:
                sys.modules.pop(_key, None)
    if not consumer_module_resolves("tools/leak_sot.py:LEAK_RE.search", _REPO):
        failures.append("the real consumer module failed to resolve beneath the repository root")
    if consumer_module_resolves("tools/leak_sot.py:LEAK_RE.search", os.path.join(_REPO, "tools")):
        failures.append("a consumer resolved beneath a root that does not contain it")

    # the A2 allowlist must describe exactly the artifacts the real invoked runner returns
    _a2_real = {i["bank"] for i in real["items"]
                if (i.get("runner_status") is not None or i["bank"] in A2_OWNERSHIP)
                and i["bank"] in A2_OWNERSHIP}
    if _a2_real != set(A2_OWNERSHIP):
        failures.append("the A2 allowlist and the real result disagree: %s" % sorted(_a2_real ^ set(A2_OWNERSHIP)))
    for _bank, (_consumer, _disposition) in A2_OWNERSHIP.items():
        _row = next((i for i in real["items"] if i["bank"] == _bank), None)
        if _row is None:
            failures.append("A2 allowlist names %s, which is not a discovered bank" % _bank)
            continue
        if _row.get("declared_disposition") != _disposition:
            failures.append("%s declared %r; the allowlist binds %r"
                            % (_bank, _row.get("declared_disposition"), _disposition))
        if _disposition != "implemented_and_consumed" and _row["has_behavioral_runner"]:
            failures.append("%s is not implemented_and_consumed yet claims behavioural coverage" % _bank)

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_eval_coverage self-test: discovers nahw+sarf banks in BOTH forms (jsonl rows + object-form "
              "cases[]/assertions[]); per-bank row/blank/malformed counts; EMPTY + MALFORMED flagged; config .json "
              "separated from banks; execution taken ONLY from an invoked registered entrypoint (adversarial "
              "probes: a no-runner root and a comment-only runner both stay uncovered and fail --strict-sarf); "
              "declaration (declared_disposition) kept apart from evidence (has_behavioral_runner); has_runner is "
              "the minimum invariant; a failed/invalid/foreign runner result yields NO coverage; real repo all "
              "banks readable+non-empty+well-formed; report leak-clean; READ-ONLY (writes nothing); "
              "ROUND-8 — a DISHONEST A2 result buys nothing: counter-only, wrong path, foreign bank, "
              "duplicate item, 1/1/1 against the real denominator, nonexistent consumer, quarantined or "
              "unowned-axis artifact relabelled implemented, wrong schema, wrong field type, a non-mapping "
              "item and a result that does not declare ok are all rejected from the reporter's OWN allowlist "
              "and OWN row counts, fail closed rather than raising, leave the sarf runner intact, and a "
              "preloaded same-named consumer module from another checkout is refused; ROUND-9 — the "
              "import-root integrity check probes EVERY sys.modules key a consumer file could be bound "
              "under, derived from its path rather than hand-written, including the exact `tools.leak_sot` "
              "key tools/run_nahw_evals.py imports, and a foreign module at any of those keys costs the "
              "artifact both resolution and behavioural credit")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Report nahw/sarf eval-bank coverage (read-only; no generation).")
    ap.add_argument("--root", default=_REPO, help="repo root (default: parent of tools/)")
    ap.add_argument("--strict", action="store_true", help="also exit 1 if any bank has no dedicated runner")
    ap.add_argument("--strict-sarf", action="store_true", dest="strict_sarf",
                    help=("DISPOSITION-COMPLETENESS gate for sarf/evals: exit 1 if any sarf bank has no runner or "
                          "no contract disposition. This is NOT a behavioural-coverage gate."))
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
    if a.strict_sarf:
        # MINIMUM invariant: every sarf bank must have been produced by an invoked registered runner. This is a
        # disposition-completeness gate on top of that, never a behavioural-coverage claim.
        dark = [b for b in rep["no_runner"] if b.startswith("sarf/evals/")]
        undisposed = [i["bank"] for i in rep["items"]
                      if i["bank"].startswith("sarf/evals/") and not i["declared_disposition"]]
        if dark or undisposed:
            print("FAIL sarf coverage: no invoked runner result %s; no declared disposition %s"
                  % (dark, undisposed))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
