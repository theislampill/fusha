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
import json
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

# Per-target provenance (repo-relative script paths only -- never machine-absolute or production paths).
MIRROR_SOURCE_META = {
    "claude_ai_pack": {"generator": "scripts/build_claude_ai_project_pack.py"},
    "claude_code_install": {"generator": "scripts/install_claude_skills.py",
                            "regenerator": "tools/generate_skill_mirrors.py"},
    "local_codex_install": {"generator": "scripts/install_codex_instructions.py",
                            "regenerator": "tools/generate_skill_mirrors.py"},
}

# Materialized-mirror copies whose bytes must match the authoritative pin. Paths are ALWAYS repo-relative
# (never machine-absolute) so nothing production-specific is baked into the tracked map.
GENERATED_MIRROR_COPIES = (
    ("claude_ai_pack", "dist/claude-ai/pack/{skill}/SKILL.md"),
)

# Recorded empirical observations of the local skill installs (content hashes only -- NEVER a filesystem
# path). The install location is referenced ONLY by its non-production target label; the real absolute
# install path is resolved at runtime by the installer from an env/base and is deliberately NOT tracked
# here. The drift sentinel uses these to prove an install is stale (observed != canonical) so it is
# REPAIRED BY REGENERATION.
RECORDED_STALE_INSTALL_OBSERVATIONS = (
    # skill-release: the two local_codex_install mirrors were REGENERATED deterministically from the
    # authoritative SKILL.md sources, so each observed sha now equals its canonical regeneration (the
    # documented FIX for a stale install; prior stale shas preserved in git history + SKILL-CHANGELOG).
    {"target": "local_codex_install", "skill": "nahw",
     "observed_sha256": "a38547fa1b153c6b4b5f931ff9ee2da98cd360902c437487d518ad4f0624b31f"},
    {"target": "local_codex_install", "skill": "sarf",
     "observed_sha256": "95620923d7bdd4c58001b47b5bba44da774d8ae106b8b4f6855e2f04f11d8eee"},
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


def build_map(repo=REPO):
    """Deterministically build the skill-mirror map from the authoritative sources. Every path is
    repo-relative; no machine-absolute or production-specific literal is ever emitted. Install locations are
    referenced only by their non-production target label (the real absolute path is resolved at runtime by the
    installer, never tracked). Fully derivable from the authoritative SKILL.md bytes plus recorded install
    content-hash observations -- so the tracked map is regenerable, not hand-edited."""
    texts = {skill: read_source(skill, repo) for skill in SKILLS}
    auth = {skill: {"path": "%s/SKILL.md" % skill,
                    "norm_sha256": hashlib.sha256(texts[skill].encode("utf-8")).hexdigest()}
            for skill in SKILLS}
    mirrors = []
    for label, tname, _tmpl in MIRROR_TARGETS:
        for skill in SKILLS:
            entry = {"target": label, "skill": skill, "transform": tname,
                     "expected_norm_sha256": canonical_sha(tname, skill, texts[skill])}
            entry.update(MIRROR_SOURCE_META.get(label, {}))
            mirrors.append(entry)
    tname_by_label = {l: t for (l, t, _1) in MIRROR_TARGETS}
    duplicate_copies = []
    for label, tmpl in GENERATED_MIRROR_COPIES:
        for skill in SKILLS:
            duplicate_copies.append({"path": tmpl.format(skill=skill), "role": "generated-mirror",
                                     "skill": skill,
                                     "sha256": canonical_sha(tname_by_label[label], skill, texts[skill])})
    known_stale = []
    for obs in RECORDED_STALE_INSTALL_OBSERVATIONS:
        skill = obs["skill"]
        known_stale.append({"target": obs["target"], "skill": skill,
                            "observed_sha256": obs["observed_sha256"],
                            "canonical_sha256": canonical_sha("frontmatter_name", skill, texts[skill]),
                            "fix": "regenerate via scripts/install_codex_instructions.py (never hand-sync)"})
    return {
        "schema": "fusha/skill-mirror-map@1",
        "provenance": ("derived deterministically from the authoritative <skill>/SKILL.md sources by "
                       "tools/generate_skill_mirrors.py --emit-map; repo-relative paths only, no "
                       "machine-absolute or production-specific literals; install locations referenced by "
                       "non-production target label"),
        "authoritative_sources": auth,
        "mirrors": mirrors,
        "duplicate_copies": duplicate_copies,
        "known_stale_installs": known_stale,
    }


def map_json(repo=REPO):
    """Canonical deterministic JSON for the map (sorted keys, LF newlines, trailing newline)."""
    return json.dumps(build_map(repo), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def emit_map(path=None, repo=REPO):
    dest = path or os.path.join(repo, "skills", "registry", "skill-mirror-map.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(map_json(repo))
    return dest


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

    # 7) skill-mirror map is deterministic, repo-relative ONLY (no production/machine-absolute literal), and
    #    carries exactly the fields the drift sentinel reconciles; regenerated map matches the tracked file.
    mj1 = map_json(REPO)
    if map_json(REPO) != mj1:
        fails.append("map_json must be deterministic")
    _bs = chr(92)  # backslash, kept out of any contiguous production literal in this source
    _leak_needles = ("/srv", "srv/" + "dawah", "hermes-" + "workspace", "da" + "wah",
                     "C:" + _bs + "Users", "C:" + _bs + "workspace", "C:" + "/Users")
    for needle in _leak_needles:
        if needle in mj1:
            fails.append("map leaks production/machine literal %r" % needle)
    m = build_map(REPO)
    if set(m["authoritative_sources"]) != set(SKILLS):
        fails.append("map authoritative_sources must cover both skills")
    for _sk, meta in m["authoritative_sources"].items():
        if os.path.isabs(meta["path"]) or ":" in meta["path"]:
            fails.append("authoritative path must be repo-relative: %r" % meta["path"])
    for d in m["duplicate_copies"]:
        if os.path.isabs(d["path"]) or ":" in d["path"]:
            fails.append("duplicate_copies path must be repo-relative: %r" % d["path"])
    if len(m["mirrors"]) != len(SKILLS) * len(MIRROR_TARGETS):
        fails.append("map mirrors count wrong: %d" % len(m["mirrors"]))
    if len(m["known_stale_installs"]) != len(RECORDED_STALE_INSTALL_OBSERVATIONS):
        fails.append("map known_stale_installs count wrong")
    _tracked = os.path.join(REPO, "skills", "registry", "skill-mirror-map.json")
    if os.path.exists(_tracked):
        _cur = open(_tracked, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n")
        if _cur != mj1:
            fails.append("committed skill-mirror-map.json != regenerated map_json (stale/hand-edited)")

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
    ap.add_argument("--emit-map", metavar="PATH", nargs="?", const="",
                    help="(re)generate skills/registry/skill-mirror-map.json (repo-relative paths only)")
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
    if a.emit_map is not None:
        dest = emit_map(a.emit_map or None)
        print("emit-map", os.path.relpath(dest, REPO).replace(os.sep, "/"))
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
