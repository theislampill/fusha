#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic CANDIDATE consumer for the L1-L6 instructional machine units.

This is the executable half of the curriculum backprop path: it LOADS an
increment's machine unit pack (curriculum/l1l6/increments/<inc>/unit-vN.json)
at runtime and DECIDES fixtures with it — the rules live in the data, not in
this module. Mutating a unit pack changes decisions (proven by --self-test),
so a repaired unit genuinely repairs the consumer's behaviour: that is the
recorded flywheel loop under curriculum/l1l6/loop/.

Hard boundaries:
- CANDIDATE plane only: emits analyses/abstentions/review flags; never
  writes entries, senses, certified facts, or anything live.
- Evidence-consuming, never evidence-inventing: roots, harakat, context
  features and observed case markings arrive as declared inputs; a missing
  input is an abstention, never a guess.
- Scripture/text is never altered or "corrected": inconsistencies become
  violation_candidate review flags.

Usage:
  python tools/curriculum_unit_consumer.py --increment inc-ownership \
      [--unit unit-v2.json] [--record OUT.json]
  python tools/curriculum_unit_consumer.py --all         # every increment, latest unit
  python tools/curriculum_unit_consumer.py --self-test   # red-first mutations

Exit 0 iff every fixture's actual == expected (or --record given, which
writes the result artifact and still reports the mismatch count in it).
Stdlib only; deterministic: same packs + fixtures -> byte-identical records.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
INC_BASE = ROOT / "curriculum" / "l1l6" / "increments"


def discover_increments():
    """Directory discovery — the consumer is NOT hard-coded to any increment
    list. An increment is any increments/<name>/ dir containing unit-v*.json;
    the latest pack is the highest version number."""
    found = {}
    for d in sorted(p for p in INC_BASE.iterdir() if p.is_dir()):
        packs = sorted(d.glob("unit-v*.json"),
                       key=lambda p: int(p.stem.split("-v")[1]))
        if packs:
            found[d.name] = packs[-1].name
    return found


def latest_unit(inc):
    return discover_increments()[inc]


def load(inc, unit_file=None):
    unit = json.loads((INC_BASE / inc / (unit_file or latest_unit(inc)))
                      .read_text(encoding="utf-8"))
    fixtures = [json.loads(l) for l in
                (INC_BASE / inc / "fixtures.jsonl").read_text(encoding="utf-8").splitlines()
                if l.strip()]
    return unit, fixtures


# ------------------------------------------------------------- inc-ownership
def analyze_ownership(inp, unit):
    letters = list(inp["letters"])
    n = len(letters)
    owners = [None] * n
    i = 0
    # peel the definite article when the inventory licenses it and a stem of
    # >=2 letters survives (own-r1: conservative peel, no false stems)
    if (n >= 4 and letters[0] == "ا" and letters[1] == "ل"
            and "ال" in unit.get("clitic_inventory", {})):
        owners[0] = owners[1] = "clitic"
        i = 2
    rest = n - i
    version = unit.get("version")
    rule_ids = {r["id"] for r in unit.get("rules", [])}
    if "own-r2-v1" in rule_ids:
        # v1 shape-only path (recorded defect)
        j = i
        if letters[j] == "م" and rest - 1 >= 3:
            owners[j] = "pattern_augment"
            for k in range(j + 1, j + 4):
                owners[k] = "root"
        elif (inp.get("token_kind") == "verb_imperfect"
              and letters[j] in unit.get("inflection_prefixes", {}) and rest - 1 == 3):
            owners[j] = "inflection"
            for k in range(j + 1, j + 4):
                owners[k] = "root"
    elif "own-r2-v2" in rule_ids:
        ev = inp.get("root_evidence")
        if ev is None:
            return {"decision": "abstain", "reason": "no_root_evidence"}
        radicals = list(ev.get("radicals", []))
        j = 0
        for k in range(i, n):
            letter = letters[k]
            if j < len(radicals) and letter == radicals[j]:
                owners[k] = "root"
                j += 1
            elif k == i and letter == "م" and j < len(radicals):
                owners[k] = "pattern_augment"
            elif (inp.get("token_kind") == "verb_imperfect"
                  and letter in unit.get("inflection_prefixes", {})
                  and not (j < len(radicals) and letter == radicals[j])):
                owners[k] = "inflection"
    if any(o is None for o in owners):
        return {"decision": "abstain", "reason": "pending_letter_ownership"}
    return {"decision": "analyzed", "owners": owners}


# ----------------------------------------------------------- inc-derivatives
def _match_template(shape, letters, radicals):
    if "..." in shape:
        return False  # handled by the mu/mafal special-case below
    if len(shape) != len(letters):
        return False
    j = 0
    for slot, letter in zip(shape, letters):
        if slot in ("R1", "R2", "R3"):
            if j >= len(radicals) or letter != radicals[j]:
                return False
            j += 1
        elif slot != letter:
            return False
    return j == len(radicals)


def analyze_derivative(inp, unit):
    ev = inp.get("root_evidence")
    if ev is None:
        return {"decision": "abstain", "reason": "no_root_evidence"}
    radicals = list(ev.get("radicals", []))
    letters = list(inp["letters"])
    survivors = []
    for t in unit["templates"]:
        if t["id"] == "mu_participle":
            # مُـ + a stem that is exactly the radicals (the derived-form
            # skeleton with gemination carried by harakat, not letters);
            # discriminated from مَفْعَل by the penult vowel (REQUIRED)
            if (letters and letters[0] == "م" and len(letters) >= 4
                    and letters[1:] == radicals):
                survivors.append(t)
            continue
        if _match_template(t["shape"], letters, radicals):
            survivors.append(t)
    ids = sorted(t["id"] for t in survivors)
    if ids == ["mafal_place", "mu_participle"] or ids == ["mu_participle"]:
        pv = inp.get("penult_vowel")
        if pv is None:
            return {"decision": "abstain", "reason": "penult_vowel_unknown"}
        t = next(t for t in survivors if t["id"] == "mu_participle")
        return {"decision": "analyzed", "class": t["split"][pv], "template": t["id"]}
    if not survivors:
        return {"decision": "abstain", "reason": "no_template"}
    if len(survivors) > 1:
        return {"decision": "abstain", "reason": "ambiguous_template"}
    t = survivors[0]
    return {"decision": "analyzed", "class": t["class"], "template": t["id"]}


# ------------------------------------------- capability: discriminator_table
def analyze_discriminator_table(inp, unit):
    feats = inp.get("features") or {}
    survivors = []
    for fn in unit["functions"]:
        ok = True
        for key, allowed in fn["discriminators"].items():
            if feats.get(key) not in allowed:
                ok = False
                break
        if ok:
            survivors.append(fn["id"])
    survivors.sort()
    if not survivors:
        return {"decision": "abstain", "reason": "insufficient_features"}
    if len(survivors) > 1:
        return {"decision": "abstain", "reason": "preserve_alternatives",
                "alternatives": survivors}
    return {"decision": "analyzed", "function": survivors[0]}


# ------------------------------------------------------------- inc-nawasikh
def analyze_nawasikh(inp, unit):
    if (inp.get("features") or {}).get("lightened_non_governing"):
        return {"decision": "abstain", "reason": "non_governing_use"}
    family = None
    for fam, spec in unit["families"].items():
        if inp.get("abrogator") in spec["members"]:
            family = fam
            spec_ = spec
            break
    if family is None:
        return {"decision": "abstain", "reason": "out_of_regime"}
    ism, khabar = inp.get("ism_marking"), inp.get("khabar_marking")
    if ism in (None, "unknown") or khabar in (None, "unknown"):
        return {"decision": "abstain", "reason": "marking_unknown"}
    if ism == spec_["ism"] and khabar == spec_["khabar"]:
        return {"decision": "consistent", "family": family}
    return {"decision": "violation_candidate", "family": family}


# --------------------------------------------------------------- inc-hidden
def analyze_hidden(inp, unit):
    for row in unit["licensing_table"]:
        if row["construction"] == inp.get("construction"):
            out = {"decision": "analyzed", "hidden_type": row["hidden"]["type"],
                   "obligatory": row.get("obligatory", False)}
            if "analysis-dependent" in (row.get("note") or ""):
                out["analysis_dependent"] = True
            return out
    return {"decision": "abstain", "reason": "reject_reconstruction"}


# Registered CAPABILITY interfaces. Dispatch is by the unit pack's declared
# `capability` field, never by increment name — a new increment that reuses a
# registered capability needs ZERO consumer edits (declarative addition).
CAPABILITIES = {
    "letter_ownership": analyze_ownership,
    "template_classification": analyze_derivative,
    "discriminator_table": analyze_discriminator_table,
    "pattern_consistency": analyze_nawasikh,
    "licensing_table": analyze_hidden,
}


def analyzer_for(unit):
    cap = unit.get("capability")
    if cap not in CAPABILITIES:
        raise KeyError("unit pack declares unregistered capability %r" % cap)
    return CAPABILITIES[cap]


def _subset_match(expected, actual):
    """Every expected key must appear in actual with an equal value."""
    for k, v in expected.items():
        if actual.get(k) != v:
            return False
    return True


def run(inc, unit_file=None):
    unit, fixtures = load(inc, unit_file)
    analyzer = analyzer_for(unit)
    results = []
    mismatches = 0
    for fx in fixtures:
        actual = analyzer(fx["input"], unit)
        ok = _subset_match(fx["expected"], actual)
        mismatches += 0 if ok else 1
        results.append({"fixture_id": fx["fixture_id"], "class": fx["class"],
                        "expected": fx["expected"], "actual": actual,
                        "match": ok})
    return {
        "schema": "curriculum.l1l6_consumer_run.v1",
        "increment": inc,
        "unit_file": unit_file or latest_unit(inc),
        "unit_version": unit.get("version"),
        "consumer": "tools/curriculum_unit_consumer.py",
        "fixtures": len(results),
        "mismatches": mismatches,
        "results": results,
        "status": "candidate",
    }


def self_test():
    """The packs must be GENUINELY consumed: mutating pack content flips
    decisions; and the recorded v1 defect must really fail its fixtures."""
    failures = []

    # 1. ownership v2 baseline green
    rec = run("inc-ownership", "unit-v2.json")
    if rec["mismatches"] != 0:
        failures.append("ownership v2 should be green, got %d mismatches"
                        % rec["mismatches"])
    # 2. ownership v1 must fail exactly its recorded defect fixtures
    rec1 = run("inc-ownership", "unit-v1.json")
    bad = sorted(r["fixture_id"] for r in rec1["results"] if not r["match"])
    if bad != ["own-abs-01", "own-adv-01"]:
        failures.append("ownership v1 defect set drifted: %r" % bad)
    # 3. pack mutation flips a decision (rules are read from the pack)
    unit, fixtures = load("inc-ownership", "unit-v2.json")
    unit_m = json.loads(json.dumps(unit))
    unit_m["rules"] = [r for r in unit_m["rules"] if r["id"] != "own-r2-v2"]
    fx = next(f for f in fixtures if f["fixture_id"] == "own-pos-01")
    if analyze_ownership(fx["input"], unit_m) == analyze_ownership(fx["input"], unit):
        failures.append("removing own-r2-v2 from the PACK did not change the decision "
                        "(consumer not actually reading the pack)")
    # 4. ma: removing a function from the pack must change the alternatives row
    unit, fixtures = load("inc-ma")
    fx = next(f for f in fixtures if f["fixture_id"] == "ma-adv-01")
    unit_m = json.loads(json.dumps(unit))
    unit_m["functions"] = [f_ for f_ in unit_m["functions"] if f_["id"] != "nafiya"]
    a1, a2 = analyze_discriminator_table(fx["input"], unit), analyze_discriminator_table(fx["input"], unit_m)
    if a1 == a2 or a2.get("decision") != "analyzed":
        failures.append("ma pack mutation did not collapse alternatives as expected")
    # 5. nawasikh: swapping the inna pattern in the pack must flip consistency
    unit, fixtures = load("inc-nawasikh")
    fx = next(f for f in fixtures if f["fixture_id"] == "naw-pos-01")
    unit_m = json.loads(json.dumps(unit))
    unit_m["families"]["inna"]["ism"] = "raf3"
    unit_m["families"]["inna"]["khabar"] = "nasb"
    if analyze_nawasikh(fx["input"], unit_m).get("decision") != "violation_candidate":
        failures.append("nawasikh pack mutation did not flip the verdict")
    # 6. hidden: removing a licence row must reject the reconstruction
    unit, fixtures = load("inc-hidden")
    fx = next(f for f in fixtures if f["fixture_id"] == "hid-pos-01")
    unit_m = json.loads(json.dumps(unit))
    unit_m["licensing_table"] = [r for r in unit_m["licensing_table"]
                                 if r["construction"] != "imperative_verb"]
    if analyze_hidden(fx["input"], unit_m).get("reason") != "reject_reconstruction":
        failures.append("hidden pack mutation did not revoke the licence")
    # 7. all DISCOVERED latest packs green (directory discovery, no list)
    discovered = discover_increments()
    if len(discovered) < 5:
        failures.append("discovery found only %d increments" % len(discovered))
    for inc in sorted(discovered):
        rec = run(inc)
        if rec["mismatches"] != 0:
            failures.append("%s latest pack has %d mismatches" % (inc, rec["mismatches"]))

    # 8. capability dispatch: every discovered pack declares a REGISTERED
    # capability, and at least two increments share one capability (proving
    # dispatch is capability-keyed, not increment-keyed)
    caps = []
    for inc in sorted(discover_increments()):
        u, _ = load(inc)
        try:
            analyzer_for(u)
        except KeyError as exc:
            failures.append(str(exc))
        caps.append(u.get("capability"))
    if len(set(caps)) >= len(caps):
        failures.append("no capability is shared by two increments — declarative "
                        "reuse unproven (add an increment reusing a capability)")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("SELF-TEST PASS (7 probes: v2 green, v1 defect pinned, 4 pack "
          "mutations flip decisions, all latest packs green)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    incs = sorted(discover_increments()) if "--all" in argv else None
    if incs is None:
        if "--increment" not in argv:
            print("usage: --increment inc-X [--unit unit-vN.json] [--record OUT] "
                  "| --all | --self-test")
            return 2
        incs = [argv[argv.index("--increment") + 1]]
    unit_file = (argv[argv.index("--unit") + 1] if "--unit" in argv else None)
    record_path = (argv[argv.index("--record") + 1] if "--record" in argv else None)
    total_mism = 0
    for inc in incs:
        rec = run(inc, unit_file if len(incs) == 1 else None)
        total_mism += rec["mismatches"]
        print("%s %s: %d fixtures, %d mismatches"
              % (inc, rec["unit_file"], rec["fixtures"], rec["mismatches"]))
        if record_path and len(incs) == 1:
            Path(record_path).write_bytes(
                (json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True)
                 + "\n").encode("utf-8"))
            print("recorded -> %s" % record_path)
    if record_path and len(incs) == 1:
        return 0  # the record IS the outcome (used for the v1 defect run)
    return 0 if total_mism == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
