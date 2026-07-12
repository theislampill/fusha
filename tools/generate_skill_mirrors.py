#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_skill_mirrors — the ONE deterministic source of every skill-mirror's bytes.

The authoritative skills are `sarf/SKILL.md` and `nahw/SKILL.md`. Every *mirror* of them (the claude.ai
Project-Knowledge pack copy, the Claude-Code `~/.claude/skills/fusha-<name>` install, the Codex
`~/.codex/skills/fusha-<name>` install) MUST be rebuildable byte-for-byte from that authoritative source by a
pure, deterministic transform — never hand-edited. This module IS that transform, so a stale local install is
*repaired by regeneration*, and `tools/check_skill_drift.py` imports these functions to assert byte-identity.

Two transforms, matching the shipped installers/pack builder exactly:
  * ``identity``          — the claude.ai pack copies the file verbatim (line-ending normalized). Keeps
                            frontmatter ``name: <skill>``. (scripts/build_claude_ai_project_pack.py)
  * ``frontmatter_name``  — the Claude/Codex installers rename the first ``name: <skill>`` frontmatter line to
                            ``name: fusha-<skill>`` and copy the rest verbatim.
                            (scripts/install_claude_skills.py, scripts/install_codex_instructions.py)

Determinism: content is line-ending-normalized (CRLF/CR -> LF) before any transform or hashing, so a Windows
autocrlf checkout and an LF checkout produce identical mirror bytes and shas. Stdlib only. No network. Writes
only under an explicit ``--emit <dir>`` target.

CLI:
  python tools/generate_skill_mirrors.py --print-shas          # canonical sha per (skill,transform)
  python tools/generate_skill_mirrors.py --emit DIR            # regenerate all mirrors under DIR
  python tools/generate_skill_mirrors.py --check DIR           # compare mirrors under DIR to canonical (exit!=0 on drift)
  python tools/generate_skill_mirrors.py --self-test
"""
import argparse
import hashlib
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = ("sarf", "nahw")
# (target label, transform name, relative mirror path template keyed by skill)
MIRROR_TARGETS = (
    ("claude_ai_pack", "identity", "pack/{skill}/SKILL.md"),
    ("claude_code_install", "frontmatter_name", "fusha-{skill}/SKILL.md"),
    ("local_codex_install", "frontmatter_name", "fusha-{skill}/SKILL.md"),
)


def norm_text(s):
    """Line-ending-normalized text (CRLF/CR -> LF). Accepts a str already-read or is fed by read_source()."""
    return s.replace("\r\n", "\n").replace("\r", "\n")


def read_source(skill, repo=REPO):
    return norm_text(open(os.path.join(repo, skill, "SKILL.md"), encoding="utf-8").read())


def transform(name, skill, text):
    """Pure deterministic transform. `text` must already be line-ending normalized."""
    if name == "identity":
        return text
    if name == "frontmatter_name":
        # exactly the installers' single-occurrence frontmatter rename
        return text.replace("\nname: %s\n" % skill, "\nname: fusha-%s\n" % skill, 1)
    raise ValueError("unknown transform: %s" % name)


def mirror_bytes(name, skill, text):
    return transform(name, skill, text).encode("utf-8")


def canonical_sha(name, skill, text):
    return hashlib.sha256(mirror_bytes(name, skill, text)).hexdigest()


def canonical_shas(repo=REPO):
    """{(skill, transform): sha256} for every distinct transform, computed from the live authoritative source."""
    out = {}
    for skill in SKILLS:
        text = read_source(skill, repo)
        for _label, tname, _tmpl in MIRROR_TARGETS:
            out[(skill, tname)] = canonical_sha(tname, skill, text)
    return out


def emit(dest, repo=REPO):
    written = []
    for skill in SKILLS:
        text = read_source(skill, repo)
        for _label, tname, tmpl in MIRROR_TARGETS:
            rel = tmpl.format(skill=skill)
            path = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(mirror_bytes(tname, skill, text))
            written.append(rel)
    return written


def check_dir(dest, repo=REPO):
    """Compare every mirror under `dest` to the canonical regeneration. Returns list of drift messages."""
    drifts = []
    for skill in SKILLS:
        text = read_source(skill, repo)
        for _label, tname, tmpl in MIRROR_TARGETS:
            rel = tmpl.format(skill=skill)
            path = os.path.join(dest, rel)
            want = mirror_bytes(tname, skill, text)
            if not os.path.exists(path):
                drifts.append("missing mirror %s (%s)" % (rel, _label))
                continue
            got = norm_text(open(path, encoding="utf-8").read()).encode("utf-8")
            if got != want:
                drifts.append("mirror drift %s (%s): sha %s != canonical %s"
                              % (rel, _label, hashlib.sha256(got).hexdigest()[:12],
                                 hashlib.sha256(want).hexdigest()[:12]))
    return drifts


def _self_test():
    import tempfile
    fails = []
    src = "---\nname: sarf\ndescription: x\n---\n\n# body\nline\n"
    src = norm_text(src)

    # 1) identity mirror is byte-identical to (normalized) source; keeps `name: sarf`
    ident = transform("identity", "sarf", src)
    if ident != src or "name: sarf\n" not in ident:
        fails.append("identity transform must be verbatim and keep name: sarf")

    # 2) frontmatter_name renames exactly once to fusha-sarf and changes nothing else
    inst = transform("frontmatter_name", "sarf", src)
    if "name: fusha-sarf\n" not in inst or "name: sarf\n" in inst:
        fails.append("frontmatter_name must rename name: sarf -> name: fusha-sarf")
    if inst.replace("name: fusha-sarf", "name: sarf", 1) != src:
        fails.append("frontmatter_name must change ONLY the name line")

    # 3) determinism: regen twice is byte-identical
    if mirror_bytes("frontmatter_name", "sarf", src) != mirror_bytes("frontmatter_name", "sarf", src):
        fails.append("transform is not deterministic")

    # 4) CRLF vs LF source produce identical mirror bytes (autocrlf safety)
    crlf = src.replace("\n", "\r\n")
    if mirror_bytes("identity", "sarf", norm_text(crlf)) != mirror_bytes("identity", "sarf", src):
        fails.append("CRLF source must normalize to identical mirror bytes")

    # 5) round-trip through the real emit/check_dir on the REAL sources: emit then check finds no drift;
    #    a hand-edit to an emitted mirror is caught (stale-install detection by regeneration).
    with tempfile.TemporaryDirectory() as d:
        emit(d, REPO)
        if check_dir(d, REPO):
            fails.append("freshly-emitted mirrors must have zero drift")
        # simulate a stale local Codex install: hand-edit one mirror
        victim = os.path.join(d, "fusha-sarf", "SKILL.md")
        with open(victim, "a", encoding="utf-8") as f:
            f.write("\nHAND EDIT (stale drift)\n")
        if not any("fusha-sarf" in x for x in check_dir(d, REPO)):
            fails.append("a hand-edited (stale) mirror must be caught as drift")

    # 6) unknown transform fails closed
    try:
        transform("nope", "sarf", src)
        fails.append("unknown transform must raise")
    except ValueError:
        pass

    for f in fails:
        print("FAIL " + f)
    if not fails:
        print("ok   generate_skill_mirrors self-test: identity + frontmatter_name transforms verbatim/exact, "
              "deterministic, CRLF-safe; emit/check round-trips; stale hand-edit caught; unknown transform fails closed")
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description="Deterministically (re)generate skill mirrors from the authoritative SKILL.md files.")
    ap.add_argument("--emit", metavar="DIR", help="regenerate all mirrors under DIR")
    ap.add_argument("--check", metavar="DIR", help="compare mirrors under DIR to canonical (exit!=0 on drift)")
    ap.add_argument("--print-shas", action="store_true", help="print canonical sha per (skill, transform)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.print_shas:
        for (skill, tname), s in sorted(canonical_shas().items()):
            print("%-6s %-16s %s" % (skill, tname, s))
        return 0
    if a.emit:
        for rel in emit(a.emit):
            print("emit", rel)
        return 0
    if a.check:
        drifts = check_dir(a.check)
        for x in drifts:
            print("DRIFT " + x)
        print("%d mirror(s) checked under %s, %d drift(s)" % (len(SKILLS) * len(MIRROR_TARGETS), a.check, len(drifts)))
        return 0 if not drifts else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
