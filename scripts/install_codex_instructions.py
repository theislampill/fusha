#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install the Fusha sarf + nahw skills for Codex (~/.codex/skills/<name>/SKILL.md) + emit an AGENTS.fusha.md snippet.

Same self-contained copy as the Claude installer, into the Codex skills dir; also writes dist/codex/AGENTS.fusha.md,
an instruction block a repo's AGENTS.md can include so Codex consults the Fusha engine.

Usage:
  python scripts/install_codex_instructions.py --dry-run
  python scripts/install_codex_instructions.py [--target ~/.codex/skills]
"""
import argparse
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_SNIPPET = """<!-- BEGIN fusha-engine (generated) -->
## Fusha sarf/nahw engine

Before authoring or classifying any Arabic gloss/entry, consult the Fusha engine:
- morphology -> `fusha-sarf` (`sarf/SKILL.md` + `sarf/procedures/`)
- syntax/context -> `fusha-nahw` (`nahw/SKILL.md` + `nahw/procedures/`)

Rules: the engine is MCP-free (it consults *available source adapters* only as optional internal evidence, never a
dependency); the public gloss record stays `{src:"qamus",kind:"authored"}`; a grammar-affecting decision needs
correct reasoning (GrammarProblems gate), not a fluent-sounding answer; when uncertain, stay pending with a precise
blocker. Use it to pull/extend the Qamus, author hover glosses, generate Qamus candidates from a corpus, and teach
learners.
<!-- END fusha-engine -->
"""


def install(name, target_dir, dry):
    man = json.load(open(os.path.join(ROOT, "skills", name, "manifest.json"), encoding="utf-8"))
    dest = os.path.join(target_dir, "fusha-" + name)
    items = [inc.rstrip("/") for inc in man["includes"] if os.path.exists(os.path.join(ROOT, inc.rstrip("/")))]
    if not dry:
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        os.makedirs(dest, exist_ok=True)
        for inc in items:
            src = os.path.join(ROOT, inc)
            rel = inc.split("/", 1)[1] if "/" in inc else os.path.basename(inc)
            dst = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
        sm = os.path.join(dest, "SKILL.md")
        if os.path.exists(sm):
            t = open(sm, encoding="utf-8").read().replace("\nname: %s\n" % name, "\nname: fusha-%s\n" % name, 1)
            open(sm, "w", encoding="utf-8").write(t)
    return {"skill": "fusha-" + name, "dest": dest, "n_includes": len(items)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--target", default=os.path.expanduser("~/.codex/skills"))
    a = ap.parse_args()
    out = [install(n, a.target, a.dry_run) for n in ("sarf", "nahw")]
    # always (re)write the committed AGENTS snippet (not a user-home write)
    snip = os.path.join(ROOT, "dist", "codex", "AGENTS.fusha.md")
    os.makedirs(os.path.dirname(snip), exist_ok=True)
    open(snip, "w", encoding="utf-8").write(AGENTS_SNIPPET)
    print(json.dumps({"mode": "dry-run" if a.dry_run else "installed", "target": a.target, "skills": out,
                      "agents_snippet": os.path.relpath(snip, ROOT)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
