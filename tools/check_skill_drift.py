#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_skill_drift — permanent, fail-closed drift sentinel for the sarf/nahw skills, their rule registry,
and their generated mirrors.

The authoritative skills are ``sarf/SKILL.md`` + ``nahw/SKILL.md``. Their normative rules are pinned in
``skills/registry/skill-rule-registry.json``; their mirrors (claude.ai pack, Claude-Code install, Codex install)
and duplicate copies are pinned in ``skills/registry/skill-mirror-map.json``. Every mirror MUST be rebuildable
byte-for-byte from the authoritative source by ``tools/generate_skill_mirrors.py`` — a stale local install is
REPAIRED BY REGENERATION, never hand-synced. This tool reconciles all of that and FAILS CLOSED on each drift
class below.

Drift classes (each proven catchable by ``--self-test`` with a red-first fixture):
  1  skill rule ADDED/REMOVED in the skill but registry not regenerated  (authoritative SKILL.md norm-sha != pin)
  2  registry rule absent from the authoritative skill                    (rule.source line unresolvable/blank)
  3  implemented rule (code cite) with no skill entry                     (code_implementation present, source MISSING)
  4  accepted rule with no executable test                               (status=accepted, permanent_tests MISSING)
  5  projector/consumer citing a STALE skill version                     (projector "path@<commit>" != last_accepted_commit)
  6  unknown / malformed / duplicate skill_rule_id                       (bad prefix, dup id, skill not in {sarf,nahw})
  7  authoritative-source vs generated-MIRROR drift (byte/hash)          (Claude-pack: regen != pinned mirror sha)
  8  local Codex install drift                                           (observed install sha != canonical regen)
  9  Claude-pack drift                                                   (pack target regen != pin)
  10 duplicate, independently-edited copies                             (>1 authoritative per skill; mirror copy != pin)

MODES (mirrors the established tools/validate_claude_ai_pack_drift.py contract):
  --self-test : runs on SYNTHETIC fixtures that must each trip their class, plus asserts the committed SSOTs hold
                their STRUCTURAL invariants (pins, ids, sources, mirror regen). Green by construction -> wire THIS
                into tools/check_regressions.py.
  --real      : reconciles the committed registry+skills+mirrors and reports ALL outstanding drift for humans,
                including known debt (accepted-rules-without-tests, stale local installs). Exit != 0 on any drift.
                NOT wired into the gate (would legitimately go red on the known 22/98 test-debt + stale installs).

Deterministic, stdlib only, no network, no writes.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from tools import generate_skill_mirrors as GM  # the ONE source of the mirror transforms

REGISTRY = os.path.join("skills", "registry", "skill-rule-registry.json")
MIRROR_MAP = os.path.join("skills", "registry", "skill-mirror-map.json")
VALID_SKILLS = ("sarf", "nahw")


def _norm_bytes_of(path):
    return open(path, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _sha(path):
    return hashlib.sha256(_norm_bytes_of(path)).hexdigest()


def _is_missing(v):
    return v == "MISSING" or v is None or v == [] or v == "" or \
        (isinstance(v, list) and all((x == "MISSING" or not x) for x in v))


# ------------------------------------------------------------------ drift-class checks (pure) --

def dc_skill_pin(mm, repo):
    """1: authoritative SKILL.md must match its pinned norm-sha (any rule add/remove/edit trips it)."""
    out = []
    for skill, meta in sorted(mm.get("authoritative_sources", {}).items()):
        p = os.path.join(repo, meta["path"])
        if not os.path.exists(p):
            out.append("authoritative source missing: %s" % meta["path"]); continue
        got = _sha(p)
        if got != meta["norm_sha256"]:
            out.append("skill-pin drift %s: file %s but registry pin %s (regenerate the registry)"
                       % (meta["path"], got[:12], meta["norm_sha256"][:12]))
    return out


def dc_registry_source(reg, repo):
    """2: every registry rule must point at a real, non-blank line in its authoritative skill."""
    out = []
    for r in reg["rules"]:
        s = r.get("source", "MISSING")
        rid = r.get("skill_rule_id", "?")
        if _is_missing(s) or ":" not in str(s):
            out.append("registry rule %s has no resolvable skill source (%r)" % (rid, s)); continue
        f, ln = str(s).rsplit(":", 1)
        fp = os.path.join(repo, f)
        if not os.path.exists(fp):
            out.append("registry rule %s cites missing skill file %s" % (rid, f)); continue
        try:
            n = int(ln)
        except ValueError:
            out.append("registry rule %s has non-numeric source line %r" % (rid, s)); continue
        lines = _norm_bytes_of(fp).decode("utf-8").split("\n")
        if n < 1 or n > len(lines) or not lines[n - 1].strip():
            out.append("registry rule %s source %s resolves to a blank/out-of-range line (rule absent from skill)"
                       % (rid, s))
    return out


def dc_implemented_without_skill(reg, repo):
    """3: a rule carrying a code implementation citation MUST also carry a resolvable skill entry."""
    out = []
    for r in reg["rules"]:
        if not _is_missing(r.get("code_implementation")) and _is_missing(r.get("source")):
            out.append("rule %s is implemented (code cite) but has no skill entry (source MISSING)"
                       % r.get("skill_rule_id", "?"))
    return out


def dc_accepted_without_test(reg):
    """4: an accepted rule with no permanent (executable) test is unprotected acceptance."""
    out = []
    for r in reg["rules"]:
        if r.get("status") == "accepted" and _is_missing(r.get("permanent_tests")):
            out.append("accepted rule %s has no permanent test (unprotected)" % r.get("skill_rule_id", "?"))
    return out


def dc_projector_stale(reg):
    """5: a projector/reviewer consumer that pins a skill commit must pin the rule's last_accepted_commit."""
    out = []
    for r in reg["rules"]:
        proj = r.get("projector_or_reviewer_consumer")
        if _is_missing(proj):
            continue
        cur = r.get("last_accepted_commit")
        items = proj if isinstance(proj, list) else [proj]
        for it in items:
            if isinstance(it, str) and "@" in it:
                cited = it.rsplit("@", 1)[1]
                if not _is_missing(cur) and cited != cur:
                    out.append("rule %s projector %r cites stale skill commit %s (current %s)"
                               % (r.get("skill_rule_id", "?"), it, cited, cur))
    return out


def dc_rule_id(reg):
    """6: skill_rule_id must be unique, non-empty, skill in {sarf,nahw}, and id prefixed by its skill."""
    out = []
    seen = set()
    for r in reg["rules"]:
        rid = r.get("skill_rule_id", "")
        sk = r.get("skill", "")
        if not rid:
            out.append("empty skill_rule_id"); continue
        if sk not in VALID_SKILLS:
            out.append("rule %s has unknown skill %r" % (rid, sk))
        if rid in seen:
            out.append("duplicate skill_rule_id %s" % rid)
        seen.add(rid)
        if sk in VALID_SKILLS and not rid.startswith(sk + "-"):
            out.append("malformed skill_rule_id %s (must be prefixed %s-)" % (rid, sk))
    return out


def dc_mirror_regen(mm, repo):
    """7+9: every pinned mirror sha must equal the canonical regeneration from the authoritative source; if a
    mirror file is materialized on disk (e.g. dist/claude-ai/pack/<skill>/SKILL.md), its bytes must match too."""
    out = []
    for m in mm.get("mirrors", []):
        skill, tname = m["skill"], m["transform"]
        text = GM.read_source(skill, repo)
        canon = GM.canonical_sha(tname, skill, text)
        if m["expected_norm_sha256"] != canon:
            out.append("mirror-pin drift %s/%s (%s): pinned %s != canonical %s"
                       % (m["target"], skill, tname, m["expected_norm_sha256"][:12], canon[:12]))
        if m["target"] == "claude_ai_pack":
            pack = os.path.join(repo, "dist", "claude-ai", "pack", skill, "SKILL.md")
            if os.path.exists(pack):
                got = hashlib.sha256(_norm_bytes_of(pack)).hexdigest()
                if got != canon:
                    out.append("materialized claude-ai pack %s/SKILL.md drift: %s != canonical %s"
                               % (skill, got[:12], canon[:12]))
    return out


def dc_stale_installs(mm, repo):
    """8: each recorded local install's observed sha must equal the canonical regeneration; if it does not, the
    install is stale and the FIX is regeneration (never hand-sync). Also verifies the recorded canonical is real."""
    out = []
    for s in mm.get("known_stale_installs", []):
        skill = s["skill"]
        canon = GM.canonical_sha("frontmatter_name", skill, GM.read_source(skill, repo))
        if s.get("canonical_sha256") != canon:
            out.append("recorded canonical for %s/%s is itself stale (%s != regen %s)"
                       % (s["target"], skill, str(s.get("canonical_sha256"))[:12], canon[:12]))
        if s.get("observed_sha256") != canon:
            out.append("stale %s %s: observed %s != canonical %s — FIX: regenerate via generate_skill_mirrors/installer"
                       % (s["target"], skill, str(s.get("observed_sha256"))[:12], canon[:12]))
    return out


def dc_duplicate_copies(mm, repo):
    """10: exactly one authoritative source per skill; any duplicate copy tagged 'generated-mirror' must match the
    authoritative pin (a mirror that diverges is an independently-edited copy)."""
    out = []
    auth = mm.get("authoritative_sources", {})
    # exactly one authoritative per skill (the map keys) with a matching-on-disk pin is enforced by dc_skill_pin;
    # here guard the duplicate ledger for independently-edited copies.
    pin = {sk: meta["norm_sha256"] for sk, meta in auth.items()}
    seen_auth = {}
    for d in mm.get("duplicate_copies", []):
        if d.get("role") == "authoritative":
            seen_auth.setdefault(d["skill"], []).append(d["sha256"])
    for sk, shas in seen_auth.items():
        if len(set(shas)) > 1:
            out.append("skill %s has >1 divergent authoritative copy: %s" % (sk, [x[:12] for x in shas]))
    for d in mm.get("duplicate_copies", []):
        if d.get("role") == "generated-mirror" and d.get("skill") in pin:
            if d["sha256"] != pin[d["skill"]]:
                out.append("generated-mirror copy %s diverges from authoritative %s (independently edited?)"
                           % (d.get("path"), d["skill"]))
    return out


# structural classes that MUST hold on the committed data (green in self-test); debt classes reported real-only
_STRUCTURAL = ("dc_skill_pin", "dc_registry_source", "dc_implemented_without_skill",
               "dc_projector_stale", "dc_rule_id", "dc_mirror_regen", "dc_duplicate_copies")
_DEBT = ("dc_accepted_without_test", "dc_stale_installs")


def _run_all(reg, mm, repo):
    """Return {class_name: [drift, ...]} for every class."""
    return {
        "dc_skill_pin": dc_skill_pin(mm, repo),
        "dc_registry_source": dc_registry_source(reg, repo),
        "dc_implemented_without_skill": dc_implemented_without_skill(reg, repo),
        "dc_accepted_without_test": dc_accepted_without_test(reg),
        "dc_projector_stale": dc_projector_stale(reg),
        "dc_rule_id": dc_rule_id(reg),
        "dc_mirror_regen": dc_mirror_regen(mm, repo),
        "dc_stale_installs": dc_stale_installs(mm, repo),
        "dc_duplicate_copies": dc_duplicate_copies(mm, repo),
    }


def _load(repo):
    reg = json.load(open(os.path.join(repo, REGISTRY), encoding="utf-8"))
    mm = json.load(open(os.path.join(repo, MIRROR_MAP), encoding="utf-8"))
    return reg, mm


# ------------------------------------------------------------------------------ self-test --

def _self_test():
    fails = []

    def expect(name, drifts, want):
        if want and not drifts:
            fails.append("%s: expected drift, got none" % name)
        if not want and drifts:
            fails.append("%s: expected clean, got %s" % (name, drifts))

    reg, mm = _load(REPO)

    # A) committed SSOTs hold every STRUCTURAL invariant (never the debt classes).
    real = _run_all(reg, mm, REPO)
    for cls in _STRUCTURAL:
        if real[cls]:
            fails.append("committed data violates structural class %s: %s" % (cls, real[cls][:2]))

    # B) red-first fixtures: each class trips on a synthetic input, and stays clean on a good one.
    with tempfile.TemporaryDirectory() as d:
        # build a minimal fake repo with sarf/nahw SKILL.md + a matching mirror map + registry
        for sk in VALID_SKILLS:
            os.makedirs(os.path.join(d, sk), exist_ok=True)
            open(os.path.join(d, sk, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(
                "---\nname: %s\ndescription: x\n---\n\n# %s\nrule alpha line\nrule beta line\n" % (sk, sk))
        good_mm = {
            "authoritative_sources": {sk: {"path": "%s/SKILL.md" % sk, "norm_sha256": _sha(os.path.join(d, sk, "SKILL.md"))}
                                      for sk in VALID_SKILLS},
            "mirrors": [{"target": t, "skill": sk, "transform": tr,
                         "expected_norm_sha256": GM.canonical_sha(tr, sk, GM.read_source(sk, d))}
                        for sk in VALID_SKILLS
                        for (t, tr) in (("claude_ai_pack", "identity"), ("local_codex_install", "frontmatter_name"))],
            "known_stale_installs": [], "duplicate_copies": [],
        }
        good_reg = {"rules": [
            {"skill_rule_id": "sarf-alpha", "skill": "sarf", "source": "sarf/SKILL.md:6", "status": "accepted",
             "code_implementation": ["tools/x.py:1"], "permanent_tests": ["sarf/evals/a.jsonl"],
             "projector_or_reviewer_consumer": "MISSING", "last_accepted_commit": "abc123"},
            {"skill_rule_id": "nahw-beta", "skill": "nahw", "source": "nahw/SKILL.md:7", "status": "candidate",
             "code_implementation": "MISSING", "permanent_tests": "MISSING",
             "projector_or_reviewer_consumer": "MISSING", "last_accepted_commit": "def456"},
        ]}

        # clean baseline: every class clean
        base = _run_all(good_reg, good_mm, d)
        for cls, drifts in base.items():
            expect("clean/" + cls, drifts, False)

        # 1 skill-pin: mutate a skill file after pinning
        open(os.path.join(d, "sarf", "SKILL.md"), "a", encoding="utf-8").write("EDIT\n")
        expect("1-skill-pin", dc_skill_pin(good_mm, d), True)
        expect("7-mirror-regen-after-edit", dc_mirror_regen(good_mm, d), True)  # pin now != regen
        # restore
        open(os.path.join(d, "sarf", "SKILL.md"), "w", encoding="utf-8", newline="\n").write(
            "---\nname: sarf\ndescription: x\n---\n\n# sarf\nrule alpha line\nrule beta line\n")

        # 2 registry-source unresolvable
        bad = {"rules": [dict(good_reg["rules"][0], source="sarf/SKILL.md:999")]}
        expect("2-registry-source", dc_registry_source(bad, d), True)

        # 3 implemented-without-skill
        bad = {"rules": [dict(good_reg["rules"][0], source="MISSING")]}
        expect("3-impl-no-skill", dc_implemented_without_skill(bad, d), True)

        # 4 accepted-without-test
        bad = {"rules": [dict(good_reg["rules"][0], permanent_tests="MISSING")]}
        expect("4-accepted-no-test", dc_accepted_without_test(bad), True)

        # 5 projector-stale
        bad = {"rules": [dict(good_reg["rules"][0],
                             projector_or_reviewer_consumer=["tools/proj.py@stale999"], last_accepted_commit="abc123")]}
        expect("5-projector-stale", dc_projector_stale(bad), True)

        # 6 unknown/malformed/dup id
        expect("6-bad-skill", dc_rule_id({"rules": [dict(good_reg["rules"][0], skill="zzz")]}), True)
        expect("6-bad-prefix", dc_rule_id({"rules": [dict(good_reg["rules"][0], skill_rule_id="wrong-alpha")]}), True)
        expect("6-dup-id", dc_rule_id({"rules": [good_reg["rules"][0], good_reg["rules"][0]]}), True)

        # 7/9 mirror-pin drift: corrupt a pinned mirror sha
        bad_mm = json.loads(json.dumps(good_mm))
        bad_mm["mirrors"][0]["expected_norm_sha256"] = "0" * 64
        expect("7-9-mirror-pin", dc_mirror_regen(bad_mm, d), True)
        # materialized-pack drift
        packp = os.path.join(d, "dist", "claude-ai", "pack", "sarf", "SKILL.md")
        os.makedirs(os.path.dirname(packp), exist_ok=True)
        open(packp, "w", encoding="utf-8", newline="\n").write("tampered pack\n")
        expect("9-materialized-pack", [x for x in dc_mirror_regen(good_mm, d) if "materialized" in x], True)

        # 8 stale local install
        bad_mm = json.loads(json.dumps(good_mm))
        bad_mm["known_stale_installs"] = [{"target": "local_codex_install", "skill": "sarf",
                                           "observed_sha256": "b" * 64,
                                           "canonical_sha256": GM.canonical_sha("frontmatter_name", "sarf", GM.read_source("sarf", d))}]
        expect("8-stale-install", dc_stale_installs(bad_mm, d), True)

        # 10 duplicate independently-edited copies
        bad_mm = json.loads(json.dumps(good_mm))
        bad_mm["duplicate_copies"] = [
            {"path": "a/sarf/SKILL.md", "role": "authoritative", "skill": "sarf", "sha256": "1" * 64},
            {"path": "b/sarf/SKILL.md", "role": "authoritative", "skill": "sarf", "sha256": "2" * 64},
            {"path": "c/sarf/SKILL.md", "role": "generated-mirror", "skill": "sarf", "sha256": "3" * 64},
        ]
        expect("10-dup-copies", dc_duplicate_copies(bad_mm, d), True)

    for f in fails:
        print("FAIL " + f)
    if not fails:
        print("ok   check_skill_drift self-test: committed registry+mirror-map hold every structural invariant; "
              "all 10 drift classes trip on red-first fixtures and stay clean on good ones")
    return 0 if not fails else 1


def _real():
    reg, mm = _load(REPO)
    res = _run_all(reg, mm, REPO)
    total = 0
    for cls in ("dc_skill_pin", "dc_registry_source", "dc_implemented_without_skill", "dc_rule_id",
                "dc_mirror_regen", "dc_duplicate_copies", "dc_projector_stale",
                "dc_accepted_without_test", "dc_stale_installs"):
        tag = "DEBT" if cls in _DEBT else "DRIFT"
        for msg in res[cls]:
            print("%s [%s] %s" % (tag, cls, msg))
            total += 1
    print("check_skill_drift --real: %d rule(s), %d mirror(s); %d finding(s) (%d structural, %d debt)"
          % (len(reg["rules"]), len(mm["mirrors"]), total,
             sum(len(res[c]) for c in _STRUCTURAL), sum(len(res[c]) for c in _DEBT)))
    return 0 if total == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="Permanent fail-closed drift sentinel for the sarf/nahw skills + mirrors.")
    ap.add_argument("--self-test", action="store_true", help="synthetic red-first fixtures + committed structural invariants (gate)")
    ap.add_argument("--real", action="store_true", help="reconcile committed data, report all outstanding drift/debt")
    a = ap.parse_args()
    if a.real:
        return _real()
    return _self_test()


if __name__ == "__main__":
    sys.exit(main())
