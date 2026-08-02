#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic learner-projection compiler: ONE canonical fact artifact yields
every explanation depth and every surface — visible colour ownership,
compact hover label, expanded sarf/nahw explanation, pattern-association
lesson pointer, common-error warning, transfer example, unresolved/rival
notice — WITHOUT the underlying fact changing and WITHOUT any view being
authored independently (every view is a pure function of the artifact;
the validator recomputes and byte-compares, so independent authoring or a
simplification that overwrites the fact is structurally impossible).

Depth tiers: beginner / intermediate / advanced / technical.

Demonstrated on the three flywheel families:
  ownership        — pilot facts token المَسْجِدُ (letter-ownership record)
  ma-ambiguity     — inc-ma function decisions (nafiya vs mawsula RETAIN
                     different learner explanations; the alternatives case
                     projects an unresolved notice)
  hidden-structure — inc-hidden licensing rows (reconstruction flagged as
                     analysis at every depth)

Output: curriculum/l1l6/projections/learner-projections.json
Deterministic; candidate plane; stdlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "curriculum" / "l1l6"

OWNER_WORDS = {"root": "root letter", "pattern_augment": "pattern letter",
               "clitic": "attached grammar word", "inflection": "verb-form letter"}


def _pack(inc):
    packs = sorted((BASE / "increments" / inc).glob("unit-v*.json"),
                   key=lambda p: int(p.stem.split("-v")[1]))
    return json.loads(packs[-1].read_text(encoding="utf-8"))


def _guards(inc):
    return json.loads((BASE / "increments" / inc / "guards.json")
                      .read_text(encoding="utf-8"))["guards"]


def project_ownership(token):
    """token = a pilot-facts token record (the canonical fact artifact)."""
    segs = []
    cur = None
    for letter in token["letters"]:
        if cur is None or cur["owner"] != letter["owner"]:
            cur = {"owner": letter["owner"], "letters": []}
            segs.append(cur)
        cur["letters"].append(letter["letter"])
    seg_desc = [("".join(s["letters"]), s["owner"]) for s in segs]
    root = token["analysis"]["root"]
    pat = token["analysis"]["pattern"]
    return {
        "fact_ref": "curriculum/l1l6/pilot/pilot-facts.json#%s" % token["token_id"],
        "family": "ownership",
        "surface": token["surface"],
        "colour_ownership": [{"letters": l, "colour_class": "seg.candidate.%s" %
                              ("pattern" if o == "pattern_augment" else o),
                              "owner": o} for l, o in seg_desc],
        "hover_label_compact": " + ".join("%s(%s)" % (l, o) for l, o in seg_desc),
        "views": {
            "beginner": "In %s, the letters %s carry the word's core meaning; %s come from the word shape or grammar." % (
                token["surface"],
                "".join(l["letter"] for l in token["letters"] if l["owner"] == "root"),
                " and ".join(sorted({OWNER_WORDS[o] + "s" for _, o in seg_desc if o != "root"}))),
            "intermediate": "%s = %s. The root is %s; the pattern %s adds its structural meaning; every other letter is grammar, not root." % (
                token["surface"],
                " + ".join("%s [%s]" % (l, OWNER_WORDS[o]) for l, o in seg_desc),
                root, pat),
            "advanced": "Letter ownership for %s: %s. Root %s in pattern %s (%s); case vowel is %s." % (
                token["surface"],
                "; ".join("%s=%s" % (l, o) for l, o in seg_desc),
                root, pat, token["analysis"]["wazn_class"],
                token["analysis"]["case_vowel"]["display"]),
            "technical": {"letters": token["letters"],
                          "analysis": token["analysis"]},
        },
        "expanded_sarf_explanation": "curriculum/l1l6/increments/inc-ownership/reference.md",
        "expanded_nahw_explanation": "curriculum/l1l6/increments/inc-nawasikh/reference.md (government of the carved clitic, where applicable)",
        "pattern_association_lesson": "curriculum/l1l6/increments/inc-ownership/staged-explanation.md",
        "common_error_warning": next(g["guard"] for g in _guards("inc-ownership")
                                     if g["id"] == "g-own-2"),
        "transfer_example_ref": "fixture own-pos-03 (مجلس — same rules, new root)",
        "unresolved_notice": None,
        "status": "candidate",
    }


def project_ma(fixture, pack):
    """fixture = an inc-ma fixture (the decision record is the artifact)."""
    exp = fixture["expected"]
    fn = None
    if exp.get("function"):
        fn = next(f for f in pack["functions"] if f["id"] == exp["function"])
    alts = exp.get("alternatives")
    return {
        "fact_ref": "curriculum/l1l6/increments/inc-ma/fixtures.jsonl#%s" % fixture["fixture_id"],
        "family": "ma-ambiguity",
        "surface": fixture["input"]["surface"],
        "colour_ownership": [{"letters": fixture["input"]["surface"],
                              "colour_class": "seg.candidate.particle-function",
                              "owner": "particle"}],
        "hover_label_compact": (fn["name"] if fn else
                                "unresolved: " + " / ".join(alts or ["insufficient context"])),
        "views": {
            "beginner": ("Here ما works as: %s." % fn["name"] if fn else
                         "This ما could be read more than one way here — scholars keep both readings, and so do we."),
            "intermediate": ("ما = %s, decided by: %s." % (
                fn["name"], ", ".join("%s=%s" % kv for kv in
                                      sorted(fixture["input"]["features"].items())))
                if fn else
                "Surviving readings: %s. The context features given (%s) do not separate them; no default exists." % (
                    ", ".join(alts or []),
                    ", ".join("%s=%s" % kv for kv in sorted(fixture["input"]["features"].items())) or "none")),
            "advanced": ("Function %s selected by discriminators %s; rival functions eliminated by their unmet discriminators." % (
                fn["id"], json.dumps(fn["discriminators"], ensure_ascii=False, sort_keys=True))
                if fn else
                "preserve_alternatives: %s all satisfy their discriminators; resolution requires additional per-occurrence evidence (og-3: no global reading)." % ", ".join(alts or [])),
            "technical": {"input": fixture["input"], "expected": exp},
        },
        "expanded_sarf_explanation": "curriculum/l1l6/increments/inc-ownership/reference.md (ما is rootless: no radicals to own)",
        "expanded_nahw_explanation": "curriculum/l1l6/increments/inc-ma/reference.md",
        "pattern_association_lesson": "curriculum/l1l6/increments/inc-ma/staged-explanation.md",
        "common_error_warning": next(g["guard"] for g in _guards("inc-ma")
                                     if g["id"] == "g-ma-3"),
        "transfer_example_ref": "fixture ma-adv-02 (shartiyya via the jussive pair)",
        "unresolved_notice": ("readings preserved: %s (attributed-unresolved pattern)"
                              % ", ".join(alts) if alts else None),
        "status": "candidate",
    }


def project_hidden(fixture, pack):
    exp = fixture["expected"]
    row = None
    if exp.get("decision") == "analyzed":
        row = next(r for r in pack["licensing_table"]
                   if r["construction"] == fixture["input"]["construction"])
    return {
        "fact_ref": "curriculum/l1l6/increments/inc-hidden/fixtures.jsonl#%s" % fixture["fixture_id"],
        "family": "hidden-structure",
        "surface": None,
        "colour_ownership": [],
        "hover_label_compact": (("hidden: %s" % row["hidden"]["type"]) if row
                                else "no reconstruction licensed"),
        "views": {
            "beginner": (("The grammar includes a hidden piece here (%s) — real, but written nowhere."
                          % row["hidden"]["type"]) if row else
                         "Nothing is hidden here; adding an 'understood word' would be inventing grammar."),
            "intermediate": (("Construction '%s' licenses a %s (%s)." % (
                row["construction"], row["hidden"]["type"],
                "obligatory" if row.get("obligatory") else "optional")) if row else
                "Construction '%s' licenses no reconstruction — the licensing table is closed." %
                fixture["input"]["construction"]),
            "advanced": ((json.dumps(row, ensure_ascii=False, sort_keys=True) +
                          " — flagged is_reconstruction; analysis-dependent licences carry attribution.")
                         if row else
                         "reject_reconstruction: parse-saving taqdir is forbidden (closed licensing inventory)."),
            "technical": {"input": fixture["input"], "expected": exp},
        },
        "expanded_sarf_explanation": "curriculum/l1l6/increments/inc-ownership/reference.md (hidden radicals are the sarf analogue)",
        "expanded_nahw_explanation": "curriculum/l1l6/increments/inc-hidden/reference.md",
        "pattern_association_lesson": "curriculum/l1l6/increments/inc-hidden/staged-explanation.md",
        "common_error_warning": next(g["guard"] for g in _guards("inc-hidden")
                                     if g["id"] == "g-hid-2"),
        "transfer_example_ref": "fixture hid-pos-02 (relative-clause 'a'id gap)",
        "unresolved_notice": ("analysis-dependent: attributed, never certified"
                              if exp.get("analysis_dependent") else None),
        "status": "candidate",
    }


def build():
    pilot = json.loads((BASE / "pilot" / "pilot-facts.json").read_text(encoding="utf-8"))
    ma_pack = _pack("inc-ma")
    hid_pack = _pack("inc-hidden")
    ma_fx = [json.loads(l) for l in (BASE / "increments" / "inc-ma" / "fixtures.jsonl")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    hid_fx = [json.loads(l) for l in (BASE / "increments" / "inc-hidden" / "fixtures.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
    projections = (
        [project_ownership(t) for t in pilot["tokens"]] +
        [project_ma(f, ma_pack) for f in ma_fx
         if f["fixture_id"] in ("ma-pos-01", "ma-pos-02", "ma-adv-01")] +
        [project_hidden(f, hid_pack) for f in hid_fx
         if f["fixture_id"] in ("hid-pos-01", "hid-adv-01", "hid-pos-03")]
    )
    return {
        "schema": "curriculum.l1l6_learner_projection_set.v1",
        "compiler": "tools/build_learner_projections.py",
        "contract": {
            "depths": ["beginner", "intermediate", "advanced", "technical"],
            "single_source_invariant": "every view is a pure function of its fact_ref artifact; colour, hover and all depths compile from ONE record; the validator recomputes byte-identically, so independent authoring or fact-overwriting simplification cannot survive CI",
            "fact_precedence": "an instructional simplification NEVER overwrites the underlying fact: the technical view embeds the artifact verbatim and every other view derives from it",
        },
        "projections": projections,
        "status": "candidate",
    }


def serialize(obj):
    return {str(BASE / "projections" / "learner-projections.json"):
            (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
             + "\n").encode("utf-8")}


def main(argv):
    check = "--check" in argv
    (BASE / "projections").mkdir(parents=True, exist_ok=True)
    files = serialize(build())
    for path, data in sorted(files.items()):
        p = Path(path)
        if check:
            if not p.exists() or p.read_bytes() != data:
                print("FAIL: %s differs from recompute" % p.name)
                return 1
        else:
            p.write_bytes(data)
            print("wrote %s (%d bytes)" % (p.relative_to(ROOT), len(data)))
    if check:
        print("OK: learner projections byte-identical to recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
