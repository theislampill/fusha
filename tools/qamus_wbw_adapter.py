#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qamus_wbw_adapter — the single PUBLIC-SAFE entry point to the maintainer's private `qamus_wbw` services.

`qamus_wbw` is the live word-by-word services package (expand / normalize / QAC caches). It is the MAINTAINER's
local package — it is NOT shipped in this public repo (a public clone has no `services/qamus_wbw`). Several builder
/ exporter tools genuinely need it, but importing it at module top level makes those files crash at import on a
public clone with a bare `ModuleNotFoundError` and no guidance.

This adapter is the honest seam:
  * `available()` -> bool, never raises, never pollutes sys.path permanently. Use it to skip/branch.
  * `load_services()` -> (expand, normalize). On a public clone it raises a clear, ACTIONABLE `SystemExit` that
    names the env var to set and points at the runnability matrix — never a bare ModuleNotFoundError.

It is a SIGNPOST, not a stub: it does NOT fake `qamus_wbw` behavior (that would fabricate data). Tools should call
`load_services()` lazily (inside `main`/first use), so `--help` and offline modes still run on a public clone.

This is the **sktime soft-dependency pattern** (deep-research wfns8dglb, 3-0): defer the optional import INSIDE the
consuming method (never at module top level), validate presence at use time via a dedicated check utility
(`available()`), and surface an informative error instead of letting a raw `ImportError` escape.

Stdlib only. CLI: --self-test (proves it imports on a clone, available() is False here, load_services() raises a
clear error). See provenance/public-runnability.md + parserplans/fusha-data-runtime-completion-pass/008 (P0-E).
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_ENV = "QAMUS_WBW_SERVICES"
_GUIDANCE = (
    "qamus_wbw services are unavailable. This tool needs the maintainer's private `qamus_wbw` package, which is "
    "NOT shipped in this public repo. To run it, fetch the services locally and set %s to the directory that "
    "contains the `qamus_wbw` package (also set QAMUS_WBW_ARTIFACT / QAMUS_DATASET if the tool asks). See "
    "provenance/public-runnability.md for which tools run offline vs. need this package."
)


def services_dir(env=DEFAULT_ENV):
    return os.environ.get(env, "services")


def available(env=DEFAULT_ENV):
    """True if `qamus_wbw` is importable from the configured services dir. Never raises; restores sys.path."""
    import importlib.util
    saved = list(sys.path)
    sd = services_dir(env)
    try:
        if sd and sd not in sys.path:
            sys.path.insert(0, sd)
        try:
            return importlib.util.find_spec("qamus_wbw") is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            return False
    finally:
        sys.path[:] = saved


def load_services(env=DEFAULT_ENV):
    """Return (expand, normalize) from the private qamus_wbw package, or raise an actionable SystemExit.

    Call this LAZILY (inside main / first use), never at module top level, so offline modes keep working."""
    sd = services_dir(env)
    if sd and sd not in sys.path:
        sys.path.insert(0, sd)
    try:
        from qamus_wbw import expand, normalize  # noqa: E402  (intentional lazy, guarded import)
        return expand, normalize
    except ModuleNotFoundError as exc:
        raise SystemExit("ERROR: " + (_GUIDANCE % env)) from exc


def _self_test():
    failures = []
    # 1. this module imports fine on a public clone (no top-level qamus_wbw import) — proven by reaching here.
    # 2. available() is False here (no services) and does NOT raise.
    try:
        if available() is not False:
            failures.append("available() should be False on a public clone with no services")
    except Exception as e:  # noqa: BLE001
        failures.append("available() raised: %r" % e)
    # 3. available() did not permanently pollute sys.path
    before = list(sys.path)
    available()
    if sys.path != before:
        failures.append("available() mutated sys.path")
    # 4. load_services() raises a clear SystemExit (NOT a bare ModuleNotFoundError) with guidance.
    try:
        load_services(env="__FUSHA_NO_SUCH_ENV__")
        failures.append("load_services() did not raise when services are absent")
    except SystemExit as se:
        msg = str(se)
        if "qamus_wbw services are unavailable" not in msg or "public-runnability.md" not in msg:
            failures.append("load_services() error is not the actionable guidance: %r" % msg[:80])
    except ModuleNotFoundError:
        failures.append("load_services() leaked a bare ModuleNotFoundError instead of an actionable SystemExit")
    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   qamus_wbw_adapter self-test: imports on a clone; available() False+non-raising+path-clean; "
              "load_services() raises actionable SystemExit (no bare ModuleNotFoundError)")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Public-safe loader for the private qamus_wbw services (signpost, not stub).")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--check", action="store_true", help="print whether qamus_wbw is available, then exit 0")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.check:
        print("qamus_wbw available: %s (services dir: %r)" % (available(), services_dir()))
        return 0
    ap.error("need --self-test or --check (this module is a library imported by builder/exporter tools)")


if __name__ == "__main__":
    sys.exit(main())
