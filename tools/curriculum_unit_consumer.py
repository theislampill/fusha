#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NON-AUTHORITATIVE fixture/development harness for the L1-L6 candidate
instructional machine units.

AUTHORITY BANNER (Sol architecture checkpoint): this module is NOT a
linguistic decision engine. It never resolves root, letter ownership,
pattern, particle function, mood, governor, hidden structure, contextual
meaning or occurrence analysis. Every non-abstention outcome is a
CANDIDATE PROPOSAL (decision: candidate_pending) awaiting the authoritative
current-main producers/lattices and the certification engine; occurrence-
bound resolution additionally requires the Sol adapter envelope (exact
occurrence, governor, reason key, rivals, review posture). Outputs feed
fixtures, review bundles and presentation templates - nothing downstream
may treat them as facts.

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
def _surface_letters(surface):
    import re as _re
    return [ch for ch in _re.sub("[\u064b-\u0652\u0670\u06d6-\u06ed]", "", surface)]


def analyze_ownership(inp, unit):
    letters = list(inp["letters"])
    # fail-closed surface accounting (Sol repair 3): supplied letters must be
    # exactly the NFC bare letters of the written surface
    if inp.get("surface") is not None and _surface_letters(inp["surface"]) != letters:
        return {"decision": "abstain", "reason": "surface_letter_mismatch"}
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
    if "own-r2-v2" in rule_ids:
        declared_hidden = set((inp.get("root_evidence") or {}).get("hidden_positions", []))
        consumed = sum(1 for o in owners if o == "root")
        radicals_n = len((inp.get("root_evidence") or {}).get("radicals", []))
        if consumed + len(declared_hidden) != radicals_n:
            # four radicals over a three-radical surface (or any unconsumed
            # radical without a declared weak/hidden position) fails closed
            return {"decision": "abstain",
                    "reason": "radical_accounting_incomplete"}
    return {"decision": "candidate_pending", "authority": "none_fixture_harness", "owners": owners}


# ----------------------------------------------------------- inc-derivatives
_VOWEL_MARK_NAMES = {"َ": "fatha", "ِ": "kasra", "ُ": "damma"}
_MARK_RE = None


def _penult_surface_mark(surface):
    """The short-vowel name actually WRITTEN on the penult base letter of
    surface, or None when the surface carries no vowel mark there. This is
    the only admissible source for a claimed penult surface mark: an
    unpointed surface can never evidence a vowel (Sol fix-request 1)."""
    global _MARK_RE
    import re as _re
    if _MARK_RE is None:
        _MARK_RE = _re.compile("[ً-ْٰۖ-ۭ]")
    groups = []  # (base_letter, [attached marks])
    for ch in surface:
        if _MARK_RE.match(ch):
            if groups:
                groups[-1][1].append(ch)
        else:
            groups.append((ch, []))
    if len(groups) < 2:
        return None
    for m in groups[-2][1]:
        if m in _VOWEL_MARK_NAMES:
            return _VOWEL_MARK_NAMES[m]
    return None


def _match_template(shape, letters, radicals, subs):
    """None if the template does not match; otherwise the (possibly empty)
    list of weak substitutions actually EXERCISED, each {slot, radical,
    letter}. `subs` must already be the slot table licensed for THIS template
    — a substitution licensed for one template never licenses another (Sol
    fix-request 1: the global table produced the مقئول/تقئيل false passes)."""
    if "..." in shape:
        return None  # handled by the mu/mafal special-case below
    if len(shape) != len(letters):
        return None
    used = []
    j = 0
    for slot, letter in zip(shape, letters):
        if slot in ("R1", "R2", "R3"):
            if j >= len(radicals):
                return None
            radical = radicals[j]
            if letter != radical:
                if letter not in (subs.get(slot, {}) or {}).get(radical, []):
                    return None
                used.append({"slot": slot, "radical": radical, "letter": letter})
            j += 1
        elif slot != letter:
            return None
    return used if j == len(radicals) else None


def _template_subs(unit, template_id):
    """Template-scoped substitution licence, derived from whichever
    declaration shape the pack carries:

    - weak_realizations.by_template (v4): the unified table — per template,
      slot and radical, which altered letters are licensed AND whether the
      weak radical may stand literally;
    - weak_substitutions.by_template (v3): substitutions only;
    - flat weak_substitutions (the recorded v2 defect): global semantics,
      kept so the defect run stays honestly reproducible.
    """
    real = (unit.get("weak_realizations") or {}).get("by_template")
    if real is not None:
        out = {}
        for slot, per_radical in (real.get(template_id) or {}).items():
            out[slot] = {rad: list(rule.get("substituted") or [])
                         for rad, rule in per_radical.items()}
        return out
    decl = unit.get("weak_substitutions") or {}
    if "by_template" in decl:
        return decl["by_template"].get(template_id, {})
    return decl


def _weak_gate(unit, template_id, radicals, used_subs, ev):
    """Fail closed on EVERY weak radical of the matched template, whether it
    surfaces altered or literally (Sol round 3).

    v3 gated only SUBSTITUTED realizations, so a hollow root whose weak
    radical stood literally in a Form-I template passed as though the root
    were sound — the uncontracted hollow shapes are non-words, not
    classifications. A weak radical now requires BOTH:

      (a) the exact bound declaration (weak_position + weak_radical), and
      (b) a realization the pack licenses FOR THAT TEMPLATE — an altered
          letter from its `substituted` list, or `literal_licensed` when the
          weak radical may stand unchanged there.

    Nothing is licensed by default: an undeclared realization abstains
    rather than being assumed regular. Returns an abstention dict, or None
    when every weak radical passes.
    """
    weak_letters = set(unit.get("weak_radicals") or [])
    if not weak_letters:
        return None
    lic = ((unit.get("weak_realizations") or {})
           .get("by_template", {}).get(template_id) or {})
    subs_slots = {u["slot"] for u in used_subs}
    for k, radical in enumerate(radicals):
        if radical not in weak_letters:
            continue
        slot = "R%d" % (k + 1)
        if ev.get("weak_position") != slot or ev.get("weak_radical") != radical:
            return {"decision": "abstain", "reason": "weak_declaration_unbound",
                    "unbound_slot": slot, "weak_radical": radical,
                    "template": template_id}
        if slot in subs_slots:
            continue  # altered realization, already matched against the licence
        if not ((lic.get(slot) or {}).get(radical) or {}).get("literal_licensed"):
            return {"decision": "abstain",
                    "reason": "weak_realization_unlicensed",
                    "unlicensed_slot": slot, "weak_radical": radical,
                    "template": template_id,
                    "note": "the pack licenses no literal realization of this "
                            "weak radical in this template (an uncontracted "
                            "hollow/weak shape is not a classification)"}
    return None


def analyze_derivative(inp, unit):
    ev = inp.get("root_evidence")
    if ev is None:
        return {"decision": "abstain", "reason": "no_root_evidence"}
    if inp.get("surface") is not None and _surface_letters(inp["surface"]) != list(inp["letters"]):
        return {"decision": "abstain", "reason": "surface_letter_mismatch"}
    radicals = list(ev.get("radicals", []))
    letters = list(inp["letters"])
    if unit.get("weak_realization_gate"):
        # evidence self-consistency first: a weak declaration that the root
        # does not bear is contradictory evidence, never a harmless extra
        wp, wr = ev.get("weak_position"), ev.get("weak_radical")
        if wp is not None or wr is not None:
            idx = {"R1": 0, "R2": 1, "R3": 2}.get(wp)
            if (idx is None or idx >= len(radicals) or radicals[idx] != wr
                    or wr not in set(unit.get("weak_radicals") or [])):
                return {"decision": "abstain",
                        "reason": "weak_declaration_contradicts_root",
                        "declared": {"weak_position": wp, "weak_radical": wr},
                        "radicals": radicals}
    survivors = []
    for t in unit["templates"]:
        if t["id"] == "mu_participle":
            # مُـ + a stem that is exactly the radicals (the derived-form
            # skeleton with gemination carried by harakat, not letters);
            # discriminated from مَفْعَل by the penult vowel (REQUIRED)
            if (letters and letters[0] == "م" and len(letters) >= 4
                    and letters[1:] == radicals):
                survivors.append((t, []))
            continue
        used = _match_template(t["shape"], letters, radicals,
                               _template_subs(unit, t["id"]))
        if used is not None:
            survivors.append((t, used))

    def weak_declaration_bound(required_slot, required_radical):
        return (ev.get("weak_position") == required_slot
                and ev.get("weak_radical") == required_radical)

    def weak_check(template_id, used_subs):
        """v4 unified gate (declared realization, literal or altered); v3
        and earlier keep the substitution-only requirement so their recorded
        defect sets stay reproducible."""
        if unit.get("weak_realization_gate"):
            return _weak_gate(unit, template_id, radicals, used_subs, ev)
        if unit.get("require_weak_declaration"):
            for u_ in used_subs:
                if not weak_declaration_bound(u_["slot"], u_["radical"]):
                    return {"decision": "abstain",
                            "reason": "weak_declaration_unbound"}
        return None

    ids = sorted(t["id"] for t, _u in survivors)
    if ids == ["mafal_place", "mu_participle"] or ids == ["mu_participle"]:
        pv = inp.get("penult_vowel")
        if pv is None:
            return {"decision": "abstain", "reason": "penult_vowel_unknown"}
        if inp.get("penult_vowel_evidence") != "surface_mark":
            # a caller-asserted vowel with no surface-mark binding cannot
            # decide voice (Sol repair 3): evidence must be bound
            return {"decision": "abstain",
                    "reason": "penult_vowel_evidence_unbound"}
        if unit.get("penult_mark_verification"):
            # the claimed mark must be VERIFIABLE on the written surface: an
            # unpointed surface evidences nothing; a differing written mark
            # refutes the claim (Sol fix-request 1)
            written = (None if inp.get("surface") is None
                       else _penult_surface_mark(inp["surface"]))
            if written is None:
                return {"decision": "abstain",
                        "reason": "penult_mark_not_in_surface"}
            if written != pv:
                return {"decision": "abstain",
                        "reason": "penult_mark_mismatch"}
        if unit.get("weak_realization_gate"):
            # voice over a weak root needs the declared realization licensed
            # for THIS template, not merely a bound declaration
            blocked = _weak_gate(unit, "mu_participle", radicals, [], ev)
            if blocked:
                return blocked
        elif unit.get("require_weak_declaration"):
            # voice on a weak-radical root additionally needs the exact weak
            # declaration (position + radical) bound in the evidence
            for k, radical in enumerate(radicals):
                if radical in ("و", "ي") and not weak_declaration_bound(
                        "R%d" % (k + 1), radical):
                    return {"decision": "abstain",
                            "reason": "weak_declaration_unbound"}
        t = next(t for t, _u in survivors if t["id"] == "mu_participle")
        return {"decision": "candidate_pending", "authority": "none_fixture_harness", "class": t["split"][pv], "template": t["id"]}
    if not survivors:
        return {"decision": "abstain", "reason": "no_template"}
    if len(survivors) > 1:
        return {"decision": "abstain", "reason": "ambiguous_template"}
    t, used = survivors[0]
    blocked = weak_check(t["id"], used)
    if blocked:
        return blocked
    return {"decision": "candidate_pending", "authority": "none_fixture_harness", "class": t["class"], "template": t["id"]}


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
    by_id = {f["id"]: f for f in unit["functions"]}
    if len(survivors) == 1 and by_id[survivors[0]].get("school_attribution"):
        # a school-attributed reading never solo-resolves (Sol repair 4):
        # it stays an attributed rival pending scholar/adapter review
        return {"decision": "abstain", "reason": "school_dependent_attributed",
                "attributed_function": survivors[0],
                "school_attribution": by_id[survivors[0]]["school_attribution"]}
    if len(survivors) > 1:
        return {"decision": "abstain", "reason": "preserve_alternatives",
                "alternatives": survivors}
    return {"decision": "candidate_pending", "authority": "none_fixture_harness", "function": survivors[0], "occurrence_binding": (inp.get("envelope") and "supplied") or "none_generic_candidate: occurrence resolution requires the Sol adapter envelope (occurrence_id, surface, governor, reason_key, complete rivals, review posture)"}


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
        return {"decision": "consistent_candidate", "authority": "none_fixture_harness", "family": family}
    return {"decision": "violation_candidate", "authority": "none_fixture_harness", "family": family}


# --------------------------------------------------------------- inc-hidden
def analyze_hidden(inp, unit):
    matches = [row for row in unit["licensing_table"]
               if row["construction"] == inp.get("construction")]
    if not matches:
        return {"decision": "abstain", "reason": "reject_reconstruction"}
    if len(matches) > 1:
        # first-match collapse is forbidden (Sol repair 4): rival licensed
        # analyses are preserved, never silently ordered away
        return {"decision": "abstain", "reason": "alternatives_preserved",
                "alternatives": sorted(m["hidden"]["type"] for m in matches)}
    row = matches[0]
    out = {"decision": "candidate_pending",
           "authority": "none_fixture_harness",
           "hidden_type": row["hidden"]["type"],
           "obligatory": row.get("obligatory", False)}
    if "analysis-dependent" in (row.get("note") or ""):
        out["analysis_dependent"] = True
    if row.get("school_attribution"):
        out["school_attribution"] = row["school_attribution"]
    return out


# ------------------------------------------ capability: pedagogical_projection
def analyze_pedagogy(inp, unit):
    """Data-driven teaching-artifact compiler: the pack's projection_contract
    declares required inputs and emitted fields (each mapped from an input
    key, with an optional per-field template prefix). Missing required
    evidence -> abstain (never invent teaching content); the underlying fact
    reference is carried verbatim so learner simplification can never
    overwrite it. Mutating the contract changes the emitted artifact."""
    contract = unit["projection_contract"]
    data = inp.get("data") or {}
    missing = [k for k in contract.get("required", []) if not data.get(k)]
    if missing:
        return {"decision": "abstain", "reason": "missing_pedagogical_inputs",
                "missing": sorted(missing)}
    fields = {}
    for emit in contract.get("emits", []):
        src = data.get(emit["from"])
        if src is None:
            continue
        if isinstance(src, list):
            src = "; ".join(str(x) for x in src)
        fields[emit["field"]] = (emit.get("prefix", "") + str(src))
    if not data.get("fact_ref"):
        return {"decision": "abstain", "reason": "missing_pedagogical_inputs",
                "missing": ["fact_ref"]}
    return {"decision": "candidate_projected",
            "authority": "none_presentation_template",
            "fact_ref": data["fact_ref"], "fields": fields}


# Registered CAPABILITY interfaces. Dispatch is by the unit pack's declared
# `capability` field, never by increment name — a new increment that reuses a
# registered capability needs ZERO consumer edits (declarative addition).
CAPABILITIES = {
    "letter_ownership": analyze_ownership,
    "template_classification": analyze_derivative,
    "discriminator_table": analyze_discriminator_table,
    "pattern_consistency": analyze_nawasikh,
    "licensing_table": analyze_hidden,
    "pedagogical_projection": analyze_pedagogy,
}


def analyzer_for(unit):
    cap = unit.get("capability")
    if cap not in CAPABILITIES:
        raise KeyError("unit pack declares unregistered capability %r" % cap)
    return CAPABILITIES[cap]


def _subset_match(expected, actual):
    """Every expected key must appear in actual with an equal value; nested
    dicts match as subsets recursively (a fixture may pin one emitted field
    without enumerating the whole artifact)."""
    for k, v in expected.items():
        av = actual.get(k)
        if isinstance(v, dict) and isinstance(av, dict):
            if not _subset_match(v, av):
                return False
        elif av != v:
            return False
    return True


def run(inc, unit_file=None):
    unit, fixtures = load(inc, unit_file)
    if unit.get("harness_disabled"):
        return {"schema": "curriculum.l1l6_consumer_run.v1", "increment": inc,
                "unit_file": unit_file or latest_unit(inc),
                "unit_version": unit.get("version"),
                "consumer": "tools/curriculum_unit_consumer.py",
                "harness_disabled": True,
                "disabled_reason": unit.get("disabled_reason"),
                "fixtures": 0, "mismatches": 0, "results": [],
                "status": "candidate_disabled_pending_adapter"}
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
    # 2b. derivatives v4 green; the v3 AND v2 defect sets are pinned red
    # forever, so no recorded false pass can be papered over:
    #   v2 (Sol round 2): مقئول/تقئيل under the global substitution table,
    #       unverified/false penult marks, missing weak declarations
    #   v3 (Sol round 3): LITERAL weak realizations in form-I templates
    #       (قاول/مقوول/مبيوع) and a weak declaration contradicting the root
    rec4 = run("inc-derivatives", "unit-v4.json")
    if rec4["mismatches"] != 0:
        failures.append("derivatives v4 should be green, got %d mismatches"
                        % rec4["mismatches"])
    v3_defects = ["der-adv-08", "der-adv-09", "der-adv-10", "der-adv-11"]
    v2_defects = ["der-abs-02", "der-adv-03", "der-adv-04", "der-adv-05",
                  "der-adv-06", "der-adv-07"] + v3_defects
    for pack, want in (("unit-v3.json", v3_defects), ("unit-v2.json", v2_defects)):
        rec = run("inc-derivatives", pack)
        bad = sorted(r["fixture_id"] for r in rec["results"] if not r["match"])
        if bad != want:
            failures.append("derivatives %s defect set drifted: %r" % (pack, bad))
        for r in rec["results"]:
            # the recorded false passes must still be FALSE PASSES under the
            # defective pack (a defect that became an abstention would prove
            # the gate moved, not that the pack was repaired)
            if r["fixture_id"] in ("der-adv-03", "der-adv-04", "der-adv-08",
                                   "der-adv-09", "der-adv-10", "der-adv-11") \
                    and r["fixture_id"] in bad \
                    and r["actual"].get("decision") != "candidate_pending":
                failures.append("%s under %s is no longer the recorded false "
                                "pass" % (r["fixture_id"], pack))
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
    if a1 == a2 or a2.get("decision") != "candidate_pending":
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
    print("SELF-TEST PASS (10 probes: ownership v2 + derivatives v4 green, "
          "ownership-v1 / derivatives-v3 / derivatives-v2 defect sets pinned "
          "red, 4 pack mutations flip decisions, discovery + "
          "shared-capability dispatch, all latest packs green)")
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
