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
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
INC_BASE = ROOT / "curriculum" / "l1l6" / "increments"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # so `python tools/curriculum_unit_consumer.py` can `from tools.X import Y`


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


# ---------------------------------------------------- letter-ownership carve
# The eval-bank-facing OPERATIONALIZATION of the `letter_ownership` capability:
# curriculum/l1l6/increments/inc-ownership own-r1..r5 (procedure.md/reference.md,
# unit-v2.json's own closed vocabulary), cu-nisba-attribution-suffix's affix layer
# (curriculum/l1l6/canonical/canonical-units.jsonl), and the p007 clitic/host carve
# for scripture occurrences (qamus/examples/p007-li-pilot). `analyze_ownership`
# above stays the PACK-DRIVEN fixture-harness path (unit-v1/v2.json + fixtures.jsonl,
# own-r1/own-r2 only). This function is the SAME capability family's wider
# production entry point -- mode dispatch (root_stem / the p007 clitic_host carve),
# the nisba mark override, and closed-vocabulary/hostile-input validation -- invoked
# directly by tools/run_sarf_evals.py's letter-ownership-carve bank adapter as its
# DECLARED behavioural consumer. It shares the pack's own owner-class and
# abstention vocabulary (unit-v2.json's `abstention_reasons`) so the two paths never
# diverge on what a shared rule means.
_OWN_CLITIC_INVENTORY = {"ال": "definite_article", "ب": "preposition", "س": "future_marker",
                         "ف": "conjunction", "ك": "preposition", "ل": "preposition", "و": "conjunction"}
_OWN_CLITIC_SINGLE = tuple(k for k in _OWN_CLITIC_INVENTORY if len(k) == 1)
_OWN_INFLECTION_PREFIXES = {"أ": "imperfect_1sg", "ت": "imperfect_2_or_3f",
                            "ن": "imperfect_1pl", "ي": "imperfect_3"}
# procedure.md step 3's closed template-letter vocabulary: "non-match template letter
# (م، ت، ا، ن، س، همزة وصل) -> pattern_augment". This is the ONLY set a non-radical letter
# may ever be licensed pattern_augment from. Every other non-radical, non-clitic,
# non-inflection letter is UNLICENSED and forces whole-token abstention -- never a guess.
# همزة وصل is the seated letter U+0671 (ٱ), not a bare hamza (ء): a bare hamza seat is a
# radical/root letter in its own right and is never licensed here by shape alone.
_OWN_PATTERN_AUGMENT_LETTERS = frozenset("متانسٱ")
_OWN_MODES = ("root_stem", "clitic_host")
_OWN_SUFFIX_KINDS = ("nisba",)
_OWN_TOKEN_KINDS = ("noun", "particle", "verb_imperfect")
# The candidate lane's closed evidence-basis vocabulary (sarf/README.md's evidence-ladder rung 1,
# "Qamus entry", and the rootless-particle special case): not new authority, just the two bases
# this lane's rows may cite for a radicals claim.
_OWN_EVIDENCE_BASES = ("qamus_entry_ladder", "rootless_particle_entry")


def _own_abstain(reason):
    return {"decision": "abstain", "reason": reason, "owners": []}


def _own_letters_reconstruct(letters, surface):
    """True iff `letters` is exactly the base-letter sequence of `surface` under the
    repository's own display-cluster contract (tools/fusha_text_check.py:_clusters -- one
    BASE letter plus its trailing combining marks per cluster), so this module and the
    segmenter never disagree on what a base letter is."""
    from tools.fusha_text_check import _clusters
    return letters == [c[0] for c in _clusters(surface)]


def _own_validate(token):
    """Closed-vocabulary / shape validation (malformed or contradictory evidence must never
    reach a claim). Every violation is rejected here, before a single letter is walked, so a
    hostile/garbage token can never surface as a root/pattern conclusion."""
    if token.get("mode") not in _OWN_MODES:
        return False
    letters = token.get("letters")
    if not (isinstance(letters, list) and letters
            and all(isinstance(ch, str) and len(ch) == 1 for ch in letters)):
        return False
    # surface is a REQUIRED bank field (exact reconstruction is an invariant, not an optional
    # extra): a missing/None/empty surface must abstain rather than be silently skipped.
    surface = token.get("surface")
    if (not isinstance(surface, str) or not surface
            or not _own_letters_reconstruct(letters, surface)):
        return False
    suffix_kind = token.get("suffix_kind")
    if suffix_kind is not None and suffix_kind not in _OWN_SUFFIX_KINDS:
        return False
    token_kind = token.get("token_kind")
    if token_kind is not None and token_kind not in _OWN_TOKEN_KINDS:
        return False
    evidence = token.get("root_evidence")
    if evidence is not None:
        if not isinstance(evidence, dict):
            return False
        radicals = evidence.get("radicals")
        if radicals is not None and not (isinstance(radicals, list)
                                         and all(isinstance(r, str) for r in radicals)):
            return False
        if evidence.get("basis") not in _OWN_EVIDENCE_BASES:
            return False
        hidden = evidence.get("hidden_positions")
        if hidden is not None and not (isinstance(hidden, list)
                                       and all(isinstance(h, str) for h in hidden)):
            return False
    layers = token.get("clitic_layers")
    if layers is not None and not (isinstance(layers, list)
                                   and all(isinstance(c, str) for c in layers)):
        return False
    return True


def _own_nisba_mark_claim(letters, peel_len, suffix_kind, surface):
    """cu-nisba-attribution-suffix: a DECLARED nisba suffix's final geminated yaa is
    affix-eligible at its OWN letter position only -- the preceding consonant's base-letter
    ownership (whatever the radical walk already decided) is never touched, because the
    canonical unit's claim is about the preceding KASRA MARK, not the consonant that carries
    it. The claim requires the mark evidence (a shadda on the final yaa, a kasra on the base
    letter immediately before it) to be VERIFIABLE on the supplied surface; an unpointed
    surface, or a declared suffix_kind the surface does not support, buys nothing (guard og-2,
    generalised past the root/pattern boundary). Returns (letter_index, mark_owner_records) or
    (None, None) when the claim is not licensed -- the caller ADDS the claim to that position's
    existing claim set (never replaces it), so a genuine double claim still surfaces (own-r4)."""
    n = len(letters)
    if suffix_kind != "nisba" or n < peel_len + 2 or letters[-1] != "ي" or not surface:
        return None, None
    from tools.normalize_ar import KASRA, haraka_on, shadda_on
    if not shadda_on(surface, "ي") or haraka_on(surface, letters[-2]) != KASRA:
        return None, None
    marks = [{"index": n - 2, "mark": "kasra", "owner": "affix"},
             {"index": n - 1, "mark": "shadda", "owner": "affix"}]
    return n - 1, marks


def analyze_ownership_carve(token):
    """The production per-letter/per-span ownership decision for the exact-letter-ownership
    family: curriculum/l1l6/increments/inc-ownership own-r1..r5, cu-nisba-attribution-suffix's
    affix layer, and the p007 clitic/host carve. This is the DECLARED behavioural consumer
    `tools/curriculum_unit_consumer.py:analyze_ownership_carve` that
    tools/run_sarf_evals.py:adapter_letter_ownership_carve invokes once per bank row; wrong
    behaviour here turns that bank RED (proven by tools/test_run_sarf_evals.py's consumer
    mutations).

    mode=root_stem   — peel a declared clitic layer, then walk every letter against
                        `root_evidence.radicals`: a match is `root`; a LICENSED template letter
                        (م ت ا ن س ٱ) that is not the expected radical is `pattern_augment`;
                        every other non-radical letter is UNLICENSED and stays unowned (forcing
                        whole-token abstention, never a guessed augment class); an imperfect
                        prefix is `inflection` only when declared verb_imperfect AND it is not
                        the expected radical (own-r3); a declared nisba suffix's final yaa is
                        `affix` only when the surface itself carries the shadda + preceding
                        kasra the claim depends on (cu-nisba-attribution-suffix) -- the
                        preceding consonant's own base-letter ownership is never altered by
                        that claim.
    mode=clitic_host — the p007 clitic-vs-host carve (`clitic_layers` names how many leading
                        letters THIS occurrence's OWN supplied evidence attests as clitic
                        layers; nothing is ever borrowed from a sibling row sharing the same
                        surface text).

    Both branches REQUIRE evidence before assigning anything; shape alone never decides (guard
    og-2). A letter left unowned, or claimed by more than one layer at once, forces whole-token
    abstention `pending_letter_ownership` (own-r4) -- never a root conclusion. An unconsumed
    radical with no declared `root_evidence.hidden_positions` fails closed as
    `radical_accounting_incomplete`, computed only AFTER every other ownership decision
    (including the nisba override) has been made. Malformed/contradictory input -- an
    unrecognised mode, `letters` that are not single base-letter strings reconstructing the
    supplied surface, an unrecognised suffix_kind/token_kind, or a root_evidence shape/basis
    outside the closed evidence-ladder vocabulary -- is rejected the same way, before any letter
    is walked. Every returned record is a CANDIDATE analysis: it never certifies, and it never
    carries a lexeme/sense/meaning/translation key.
    """
    if not _own_validate(token):
        return _own_abstain("pending_letter_ownership")
    letters = list(token["letters"])
    n = len(letters)
    if n < 2:
        return _own_abstain("false_stem_risk")
    mode = token.get("mode")
    token_kind = token.get("token_kind")
    suffix_kind = token.get("suffix_kind")
    surface = token.get("surface")

    if mode == "clitic_host":
        clitic_layers = token.get("clitic_layers")
        if not clitic_layers:
            return _own_abstain("pending_letter_ownership")
        k = len(clitic_layers)
        if n < k + 1:
            return _own_abstain("false_stem_risk")
        for j in range(k):
            if letters[j] != clitic_layers[j] or letters[j] not in _OWN_CLITIC_SINGLE:
                return _own_abstain("pending_letter_ownership")
        claims = [{"clitic"} for _ in range(k)] + [{"host"} for _ in range(n - k)]
        claim_idx, marks = _own_nisba_mark_claim(letters, k, suffix_kind, surface)
        if claim_idx is not None:
            claims[claim_idx].add("affix")
        if any(len(c) != 1 for c in claims):
            return _own_abstain("pending_letter_ownership")
        result = {"decision": "candidate_pending", "owners": [next(iter(c)) for c in claims]}
        if marks:
            result["mark_owners"] = marks
        return result

    # mode == root_stem: own-r1 peel, own-r2-v2/own-r3 root+inflection walk, own-r4 conflict
    # check, own-r5 hidden-radical accounting.
    peel_len = 0
    if token_kind != "particle":
        if letters[:2] == ["ا", "ل"]:
            if n - 2 < 2:
                return _own_abstain("false_stem_risk")
            peel_len = 2
        elif letters[0] in _OWN_CLITIC_SINGLE:
            if n - 1 < 2:
                return _own_abstain("false_stem_risk")
            peel_len = 1

    evidence = token.get("root_evidence")
    radicals = evidence.get("radicals") if isinstance(evidence, dict) else None
    if evidence is None or radicals is None:
        return _own_abstain("no_root_evidence")
    if not radicals:
        return _own_abstain("pending_letter_ownership" if token_kind == "particle" else "no_root_evidence")

    # Every letter (including any already peeled) is checked against the radical sequence, so a
    # letter that is BOTH clitic-shaped AND named as the next expected radical is recorded as a
    # genuine double claim (own-r4) rather than silently letting shape win (guard og-2).
    claims = [set() for _ in range(n)]
    for i in range(peel_len):
        claims[i].add("clitic")
    ri = 0
    for i in range(n):
        ch = letters[i]
        is_next_radical = ri < len(radicals) and ch == radicals[ri]
        if token_kind == "verb_imperfect" and i == peel_len and ch in _OWN_INFLECTION_PREFIXES \
                and not is_next_radical:
            claims[i].add("inflection")
            continue
        if is_next_radical:
            claims[i].add("root")
            ri += 1
        elif i >= peel_len and ch in _OWN_PATTERN_AUGMENT_LETTERS:
            claims[i].add("pattern_augment")

    # The nisba mark claim is ADDED, never substituted, so a position the walk already owned
    # (a genuine double claim) still surfaces via the len(c) != 1 check below; it never silently
    # overwrites -- and never touches -- the preceding consonant's own base-letter ownership.
    claim_idx, marks = _own_nisba_mark_claim(letters, peel_len, suffix_kind, surface)
    if claim_idx is not None:
        claims[claim_idx].add("affix")

    if any(len(c) != 1 for c in claims):
        return _own_abstain("pending_letter_ownership")

    # own-r5, computed AFTER every ownership decision above (including the nisba override):
    # an unconsumed radical with no declared hidden/weak-root position fails closed rather than
    # silently dropping it from the record. `hidden_positions` must name the EXACT multiset of
    # unconsumed radicals -- not merely the right COUNT of them -- so a contradictory declaration
    # (wrong letter, junk, a foreign letter, a duplicate, an empty string, or the right count with
    # the wrong identity) can never manufacture a licensed candidate for a radical it does not
    # actually account for. Counter (not set) so a genuine duplicate radical is never masked.
    hidden_radicals = radicals[ri:]
    if hidden_radicals:
        declared_hidden = evidence.get("hidden_positions") or []
        if Counter(declared_hidden) != Counter(hidden_radicals):
            return _own_abstain("radical_accounting_incomplete")

    result = {"decision": "candidate_pending", "owners": [next(iter(c)) for c in claims]}
    if hidden_radicals:
        result["hidden_radicals"] = hidden_radicals
    if marks:
        result["mark_owners"] = marks
    return result


# ----------------------------------------------------------- inc-derivatives
_VOWEL_MARK_NAMES = {"َ": "fatha", "ِ": "kasra", "ُ": "damma"}
_MARK_RE = None


def _surface_mark_groups(surface):
    """(base_letter, [attached marks]) per display cluster of surface -- the shared
    grouping both `_penult_surface_mark` and `_initial_surface_mark` read from, so the
    two never disagree on what a base letter or an attached mark is."""
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
    return groups


def _vowel_mark_at(groups, index):
    if not groups or not (-len(groups) <= index < len(groups)):
        return None
    for m in groups[index][1]:
        if m in _VOWEL_MARK_NAMES:
            return _VOWEL_MARK_NAMES[m]
    return None


def _penult_surface_mark(surface):
    """The short-vowel name actually WRITTEN on the penult base letter of
    surface, or None when the surface carries no vowel mark there. This is
    the only admissible source for a claimed penult surface mark: an
    unpointed surface can never evidence a vowel (Sol fix-request 1)."""
    groups = _surface_mark_groups(surface)
    if len(groups) < 2:
        return None
    return _vowel_mark_at(groups, -2)


def _initial_surface_mark(surface):
    """The short-vowel name actually WRITTEN on the FIRST base letter of surface, or
    None when the surface carries no vowel mark there. This is the licensed
    discriminator between the مَفْعَل place/time noun (fatha) and the مُـ participle
    (damma) once both templates co-survive on the same literal-radical letters (Sol
    repair: the penult vowel alone silently dropped the co-surviving mafal_place
    template and decided the collision from the wrong evidence)."""
    return _vowel_mark_at(_surface_mark_groups(surface), 0)


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
    radical_arity = unit.get("radical_arity", 3)
    survivors = []
    for t in unit["templates"]:
        if t["id"] == "mu_participle":
            # مُـ + a stem that is exactly the radicals (the derived-form
            # skeleton with gemination carried by harakat, not letters);
            # discriminated from مَفْعَل by the penult vowel (REQUIRED)
            if letters and letters[0] == "م" and letters[1:] == radicals:
                if len(radicals) != radical_arity:
                    # every current interface in this catalogue is written
                    # against a `radical_arity`-slot root (default 3); a
                    # non-matching radical count is refused here, not
                    # silently routed through a three-slot template (L5.M4.06)
                    return {"decision": "abstain",
                            "reason": "radical_arity_unsupported",
                            "declared_arity": radical_arity,
                            "supplied_radicals": radicals}
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
            if "mafal_place" in ids:
                # مَفْعَل (place/time noun) and the derived-form مُـ participle are
                # letter-identical whenever the radicals stand literally after the
                # initial مـ; the WRITTEN vowel on THAT initial مـ -- damma for the
                # participle, fatha for the place-noun -- is the licensed
                # discriminator between the two co-surviving readings (Sol repair:
                # the previous code decided the collision from the penult vowel
                # alone and silently dropped the co-surviving mafal_place
                # template; the penult vowel only ever decides voice WITHIN the
                # participle reading, never WHICH reading this token is). Missing,
                # unbound or mismatching written evidence abstains rather than
                # guessing either reading.
                initial_mark = _initial_surface_mark(inp["surface"])
                if initial_mark is None:
                    return {"decision": "abstain",
                            "reason": "initial_mim_mark_not_in_surface"}
                if initial_mark == "fatha":
                    mafal_t = next(t for t, _u in survivors if t["id"] == "mafal_place")
                    return {"decision": "candidate_pending",
                            "authority": "none_fixture_harness",
                            "class": mafal_t["class"], "template": mafal_t["id"]}
                if initial_mark != "damma":
                    return {"decision": "abstain",
                            "reason": "initial_mim_vowel_unlicensed"}
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
    if str(t.get("class") or "").startswith("shared_"):
        # a `shared_*` class is a ROUTING LABEL, not a resolved class (the row
        # is letter-identical to a row in a sibling pack): the discriminating
        # decision belongs to cu-adjective-class-discriminator, which this
        # batch does not author. The label must never be reachable as an
        # ordinary class -- it always abstains here instead.
        return {"decision": "abstain", "reason": "shared_row_class_undecided",
                "template": t["id"], "shared_with": t.get("shared_with") or []}
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
            # a function's OWN discriminators may all match while a declared
            # excluded_when companion value is ALSO present -- that function is
            # disqualified regardless (Sol repair: ela-r4's "the two superlative
            # constructions EXCLUDE the comparison complement" was stated but never
            # executed, so a surface carrying a comparison complement AND
            # definite-article evidence still resolved elative_comparative). This is
            # a general per-function exclusion, not an elative-specific branch: any
            # pack sharing this capability may declare it.
            for key, excluded in (fn.get("excluded_when") or {}).items():
                if feats.get(key) in excluded:
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

    # 9. analyze_ownership_carve (the eval-bank-facing production entry point, distinct from the
    # pack-driven analyze_ownership above): bounded red/green + mutation probes proving the
    # nisba mark override, the licensed pattern_augment set, and the own-r4 double-claim guard
    # are genuinely computed here, not merely echoed.
    _own_pos = {"mode": "root_stem", "letters": ["م", "ك", "ت", "ب"], "surface": "مكتب",
               "token_kind": "noun",
               "root_evidence": {"basis": "qamus_entry_ladder", "radicals": ["ك", "ت", "ب"]}}
    if analyze_ownership_carve(_own_pos) != {"decision": "candidate_pending",
                                             "owners": ["pattern_augment", "root", "root", "root"]}:
        failures.append("analyze_ownership_carve: positive mim/root case regressed")
    _own_unlicensed = {"mode": "root_stem", "letters": ["م", "ك", "ت", "و", "ب"], "surface": "مكتوب",
                       "token_kind": "noun",
                       "root_evidence": {"basis": "qamus_entry_ladder", "radicals": ["ك", "ت", "ب"]}}
    if analyze_ownership_carve(_own_unlicensed) != {"decision": "abstain",
                                                     "reason": "pending_letter_ownership", "owners": []}:
        failures.append("analyze_ownership_carve: an unlicensed internal letter (waw) must abstain, "
                        "never be guessed pattern_augment")
    _own_nisba = {"mode": "root_stem", "letters": ["م", "ص", "ر", "ي"], "surface": "مصرِيّ",
                 "token_kind": "noun", "suffix_kind": "nisba",
                 "root_evidence": {"basis": "qamus_entry_ladder", "radicals": ["م", "ص", "ر"]}}
    _own_nisba_rec = analyze_ownership_carve(_own_nisba)
    if _own_nisba_rec.get("owners") != ["root", "root", "root", "affix"]:
        failures.append("analyze_ownership_carve: nisba override must never swallow the preceding "
                        "consonant's own base-letter (root) ownership")
    if not _own_nisba_rec.get("mark_owners"):
        failures.append("analyze_ownership_carve: a licensed nisba claim must record separate mark "
                        "ownership (the kasra/shadda are mark-owned, not consonant-owned)")
    _own_nisba_bare = dict(_own_nisba, surface="مصري")  # no marks: the claim buys nothing unpointed
    if analyze_ownership_carve(_own_nisba_bare).get("decision") != "abstain":
        failures.append("analyze_ownership_carve: an unpointed surface must not buy an unverifiable "
                        "nisba mark claim (the position must stay unowned and the token abstain)")
    if analyze_ownership_carve({"mode": "bogus_mode", "letters": ["ب", "ت"]}) \
            .get("decision") != "abstain":
        failures.append("analyze_ownership_carve: an unrecognised mode must abstain, not decide")
    if analyze_ownership_carve({"mode": "root_stem", "letters": ["بت", "ك"], "token_kind": "noun",
                               "root_evidence": {"basis": "qamus_entry_ladder", "radicals": ["ب", "ك"]}}) \
            .get("decision") != "abstain":
        failures.append("analyze_ownership_carve: a multi-character 'letter' must abstain (malformed "
                        "shape), never decide")
    from tools import curriculum_unit_consumer as _self_mod
    _orig_carve = _self_mod.analyze_ownership_carve
    _self_mod.analyze_ownership_carve = lambda token: {"decision": "candidate_pending",
                                                        "owners": ["root"] * len(token.get("letters") or [])}
    try:
        if _self_mod.analyze_ownership_carve(_own_unlicensed)["owners"] == ["pattern_augment", "root",
                                                                            "root", "pattern_augment",
                                                                            "root"]:
            failures.append("analyze_ownership_carve: module-level rebind did not take effect "
                            "(self-test cannot prove genuine invocation)")
    finally:
        _self_mod.analyze_ownership_carve = _orig_carve

    # 10. radical-arity refusal (analyze_derivative's mu_participle branch): the recorded false
    # pass at 525ddc6 routed a four-radical root (مُدَحْرِج، radicals د ح ر ج) through the
    # three-slot mu_participle template as though it were a sound triliteral (L5.M4.06 — "every
    # current interface in the catalogue is written against a three-slot root"). Reproduced here
    # against the UNCHANGED inc-derivatives/unit-v4.json pack (proving the fix is a pure consumer
    # change, not a pack edit): a 2-radical and a 5-radical root reach the SAME abstention.
    _der_unit, _ = load("inc-derivatives", "unit-v4.json")
    _mudahrij = {"letters": list("مدحرج"), "surface": "مُدَحْرِج", "penult_vowel": "kasra",
                "penult_vowel_evidence": "surface_mark",
                "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("دحرج")}}
    _mudahrij_rec = analyze_derivative(_mudahrij, _der_unit)
    if _mudahrij_rec != {"decision": "abstain", "reason": "radical_arity_unsupported",
                         "declared_arity": 3, "supplied_radicals": list("دحرج")}:
        failures.append("analyze_derivative: the recorded four-radical mu_participle false pass "
                        "(مُدَحْرِج) is no longer refused: %r" % (_mudahrij_rec,))
    _two_rad = analyze_derivative({"letters": ["م", "ي", "د"],
                                   "root_evidence": {"basis": "qamus_entry_ladder", "radicals": ["ي", "د"]}},
                                  _der_unit)
    _five_rad = analyze_derivative({"letters": list("مخندرس"),
                                    "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("خندرس")}},
                                   _der_unit)
    if not (_two_rad.get("reason") == _five_rad.get("reason") == "radical_arity_unsupported"):
        failures.append("analyze_derivative: a 2-radical and a 5-radical mu_participle-shaped root "
                        "must reach the SAME radical_arity_unsupported abstention, got %r / %r"
                        % (_two_rad, _five_rad))
    _der_unit_arity4 = json.loads(json.dumps(_der_unit))
    _der_unit_arity4["radical_arity"] = 4
    if analyze_derivative(_mudahrij, _der_unit_arity4).get("decision") == "abstain":
        failures.append("analyze_derivative: radical_arity is not genuinely PACK-declared "
                        "(declaring radical_arity: 4 in the pack did not license the four-radical root)")

    # 11. shared-row refusal: a template whose declared class begins with shared_ must never
    # surface as a resolved class (cu-adjective-class-discriminator's abstention obligation).
    _qad_unit, _qad_fixtures = load("inc-quality-adjective-templates")
    _kabiir = {"letters": list("كبير"), "surface": "كبير",
              "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("كبر")}}
    _kabiir_rec = analyze_derivative(_kabiir, _qad_unit)
    if _kabiir_rec.get("decision") != "abstain" or _kabiir_rec.get("reason") != "shared_row_class_undecided":
        failures.append("analyze_derivative: a shared_-classed template survivor must abstain "
                        "shared_row_class_undecided, got %r" % (_kabiir_rec,))
    _qad_unit_unshared = json.loads(json.dumps(_qad_unit))
    for _t in _qad_unit_unshared["templates"]:
        if _t["id"] == "faiil":
            _t["class"] = "quality_adjective"  # PACK mutation: strip the shared_ prefix
    if analyze_derivative(_kabiir, _qad_unit_unshared).get("decision") != "candidate_pending":
        failures.append("analyze_derivative: the shared_row_class_undecided refusal is not "
                        "genuinely PACK-declared (stripping the shared_ prefix from the PACK's own "
                        "template class did not unblock the decision)")

    # 12. the three repaired sibling packs (inc-quality-adjective-templates,
    # inc-intensive-agent-templates, inc-broken-plural-template-inventory): the recorded false
    # passes at 525ddc6 (قوال/قويل over ق و ل, a literal uncontracted weak radical) must never
    # recur, and — because the shared_row refusal above is a consumer-level fix that applies
    # regardless of pack version — قوال/قويل abstain under BOTH the unrepaired unit-v1.json packs
    # (proving the consumer fix alone already closes the shared-row half of the defect) and the
    # repaired unit-v2.json packs (which add the weak-realization-gate DATA closing the remaining,
    # non-shared half: inc-intensive-agent-templates' OWN faaal row is not shared, so only the v2
    # pack's weak_realization_gate — not the shared_ check — refuses it).
    def _qawaal(radicals_letters=("ق", "و", "ل")):
        return {"letters": list("قوال"), "surface": "قوال",
                "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list(radicals_letters),
                                  "weak_position": "R2", "weak_radical": "و"}}

    def _qawiil(radicals_letters=("ق", "و", "ل")):
        return {"letters": list("قويل"), "surface": "قويل",
                "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list(radicals_letters),
                                  "weak_position": "R2", "weak_radical": "و"}}

    _int_unit_v1, _ = load("inc-intensive-agent-templates", "unit-v1.json")
    _int_unit_v2, _ = load("inc-intensive-agent-templates", "unit-v2.json")
    _qad_unit_v1, _ = load("inc-quality-adjective-templates", "unit-v1.json")
    _qad_unit_v2, _ = load("inc-quality-adjective-templates", "unit-v2.json")
    _bpl_unit_v1, _ = load("inc-broken-plural-template-inventory", "unit-v1.json")
    _bpl_unit_v2, _ = load("inc-broken-plural-template-inventory", "unit-v2.json")

    _int_v1_qawaal = analyze_derivative(_qawaal(), _int_unit_v1)
    if _int_v1_qawaal.get("decision") != "candidate_pending":
        failures.append("self-test drift: inc-intensive-agent-templates/unit-v1.json no longer "
                        "reproduces the recorded قوال false pass (%r) — the v1 defect set must stay "
                        "reproducible" % (_int_v1_qawaal,))
    for _label, _unit in (("inc-intensive-agent-templates v2", _int_unit_v2),
                          ("inc-quality-adjective-templates v1", _qad_unit_v1),
                          ("inc-quality-adjective-templates v2", _qad_unit_v2)):
        for _mk, _inp in (("قوال", _qawaal()), ("قويل", _qawiil())):
            _rec = analyze_derivative(_inp, _unit)
            if _rec.get("decision") != "abstain":
                failures.append("%s / %s must abstain (recorded false pass), got %r"
                                % (_label, _mk, _rec))
    # inc-broken-plural-template-inventory: قوال is masked by the pack's OWN declared
    # فعال/singular-homograph collision (ambiguous_template) regardless of the weak gate, so the
    # weak-gate-specific defect/repair is proven on مقاول (مفاعل template) instead.
    _muqaawil = {"letters": list("مقاول"), "surface": "مقاول",
                "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list("قول"),
                                  "weak_position": "R2", "weak_radical": "و"}}
    _bpl_v1_rec = analyze_derivative(_muqaawil, _bpl_unit_v1)
    if _bpl_v1_rec.get("decision") != "candidate_pending":
        failures.append("self-test drift: inc-broken-plural-template-inventory/unit-v1.json no "
                        "longer reproduces the literal-weak-radical false pass on مقاول (%r)"
                        % (_bpl_v1_rec,))
    _bpl_v2_rec = analyze_derivative(_muqaawil, _bpl_unit_v2)
    if _bpl_v2_rec.get("decision") != "abstain":
        failures.append("inc-broken-plural-template-inventory/unit-v2.json must abstain on مقاول "
                        "(weak-realization gate), got %r" % (_bpl_v2_rec,))

    # 13. the mafal_place/mu_participle collision: the WRITTEN initial مـ vowel decides
    # place-noun (fatha) vs participle (damma) BEFORE the penult vowel is ever consulted for
    # voice; the reproduced false positives (مجلس/منزل falsely active_participle, مكتب falsely
    # passive_participle) are refused against the UNCHANGED inc-derivatives/unit-v4.json pack.
    def _collision(letters_s, surface, radicals_letters, penult_vowel):
        return {"letters": list(letters_s), "surface": surface, "penult_vowel": penult_vowel,
                "penult_vowel_evidence": "surface_mark",
                "root_evidence": {"basis": "qamus_entry_ladder", "radicals": list(radicals_letters)}}

    _majlis = _collision("مجلس", "مَجْلِس", "جلس", "kasra")
    _majlis_rec = analyze_derivative(_majlis, _der_unit)
    if _majlis_rec != {"decision": "candidate_pending", "authority": "none_fixture_harness",
                       "class": "place_time_noun", "template": "mafal_place"}:
        failures.append("analyze_derivative: مجلس (fatha-initial place-noun, kasra penult) must "
                        "resolve place_time_noun via mafal_place, not the penult-vowel-driven "
                        "mu_participle false pass: got %r" % (_majlis_rec,))
    _maktab = _collision("مكتب", "مَكْتَب", "كتب", "fatha")
    _maktab_rec = analyze_derivative(_maktab, _der_unit)
    if _maktab_rec.get("class") != "place_time_noun" or _maktab_rec.get("template") != "mafal_place":
        failures.append("analyze_derivative: مكتب (fatha-initial place-noun, fatha penult) must "
                        "resolve place_time_noun, not the recorded passive_participle false pass: "
                        "got %r" % (_maktab_rec,))
    _mudarris = _collision("مدرس", "مُدَرِّس", "درس", "kasra")
    _mudarris_rec = analyze_derivative(_mudarris, _der_unit)
    if _mudarris_rec != {"decision": "candidate_pending", "authority": "none_fixture_harness",
                         "class": "active_participle", "template": "mu_participle"}:
        failures.append("analyze_derivative: مُدَرِّس (genuinely damma-initial) must still resolve "
                        "the mu_participle reading -- the initial-مـ discriminator must never "
                        "disturb a genuine participle: got %r" % (_mudarris_rec,))
    _no_initial_mark = _collision("مكتب", "مكْتَب", "كتب", "fatha")
    if analyze_derivative(_no_initial_mark, _der_unit) != {"decision": "abstain",
                                                           "reason": "initial_mim_mark_not_in_surface"}:
        failures.append("analyze_derivative: a verified penult mark with NO mark at all on the "
                        "initial مـ must abstain initial_mim_mark_not_in_surface, never guess "
                        "either co-surviving reading")
    _unlicensed_initial = _collision("مكتب", "مِكْتَب", "كتب", "fatha")
    if analyze_derivative(_unlicensed_initial, _der_unit) != {"decision": "abstain",
                                                              "reason": "initial_mim_vowel_unlicensed"}:
        failures.append("analyze_derivative: an initial-مـ vowel that is neither damma nor fatha "
                        "must abstain initial_mim_vowel_unlicensed")

    # 14. masdar_mimi is a genuinely PACK-declared rival in inc-mim-initial-noun-discriminator: a
    # bare-triliteral fatha/present feature set now preserves BOTH place_or_time_noun and
    # masdar_mimi (never a vote), and removing masdar_mimi from the in-memory pack collapses the
    # row back to a single survivor -- proving the collision is pack content, not hard-coded.
    _mim_unit, _ = load("inc-mim-initial-noun-discriminator")
    _mim_feats = {"features": {"prefix_vowel": "fatha", "source_form_class": "bare_triliteral",
                               "vocalization": "present"}}
    _mim_rec = analyze_discriminator_table(_mim_feats, _mim_unit)
    if _mim_rec.get("reason") != "preserve_alternatives" \
            or sorted(_mim_rec.get("alternatives") or []) != ["masdar_mimi", "place_or_time_noun"]:
        failures.append("analyze_discriminator_table: masdar_mimi is not preserved as a rival "
                        "alongside place_or_time_noun over a bare-triliteral fatha/present row: "
                        "got %r" % (_mim_rec,))
    _mim_unit_m = json.loads(json.dumps(_mim_unit))
    _mim_unit_m["functions"] = [f_ for f_ in _mim_unit_m["functions"] if f_["id"] != "masdar_mimi"]
    _mim_rec_m = analyze_discriminator_table(_mim_feats, _mim_unit_m)
    if _mim_rec_m.get("decision") != "candidate_pending" or _mim_rec_m.get("function") != "place_or_time_noun":
        failures.append("analyze_discriminator_table: removing masdar_mimi from the PACK did not "
                        "collapse the row back to a clean place_or_time_noun resolution "
                        "(masdar_mimi is not genuinely pack-declared)")

    # 15. ela-r4 in the fail-closed direction: a comparison complement combined with
    # definite-article superlative evidence must never resolve elative_comparative, via a
    # PACK-declared excluded_when clause -- removing that clause from the in-memory pack must
    # flip the decision back to the (contradicting) false pass, proving the exclusion is data,
    # not a hard-coded elative special case.
    _ela_unit, _ = load("inc-elative-template-discriminator")
    _ela_feats = {"features": {"comparison_complement": "min_phrase_present",
                               "definiteness_behaviour": "definite_article",
                               "entry_evidence": "adjectival_entry",
                               "feminine_counterpart_template": "fula"}}
    _ela_rec = analyze_discriminator_table(_ela_feats, _ela_unit)
    if _ela_rec != {"decision": "abstain", "reason": "insufficient_features"}:
        failures.append("analyze_discriminator_table: a comparison complement WITH definite-"
                        "article evidence must abstain insufficient_features (ela-r4), never "
                        "resolve elative_comparative: got %r" % (_ela_rec,))
    _ela_unit_m = json.loads(json.dumps(_ela_unit))
    for _f_ in _ela_unit_m["functions"]:
        if _f_["id"] == "elative_comparative":
            _f_.pop("excluded_when", None)
    _ela_rec_m = analyze_discriminator_table(_ela_feats, _ela_unit_m)
    if _ela_rec_m.get("function") != "elative_comparative":
        failures.append("analyze_discriminator_table: removing excluded_when from the PACK did "
                        "not restore the recorded false pass (the ela-r4 exclusion is not "
                        "genuinely pack-declared)")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("SELF-TEST PASS (probes 1-8: ownership v2 + derivatives v4 green, "
          "ownership-v1 / derivatives-v3 / derivatives-v2 defect sets pinned "
          "red, 4 pack mutations flip decisions, discovery + "
          "shared-capability dispatch, all latest packs green; "
          "probe 9, analyze_ownership_carve: licensed-augment/unlicensed-abstain, the nisba mark "
          "override never swallowing the carrier consonant, an unpointed surface buying "
          "no mark claim, malformed-mode/malformed-letter abstention, and a module-level "
          "rebind proof; probe 10, radical_arity_unsupported: the recorded مُدَحْرِج false pass "
          "refused against the UNCHANGED inc-derivatives/unit-v4.json pack, 2- and 5-radical "
          "roots reaching the same abstention, and a pack-declared radical_arity mutation "
          "licensing the four-radical root; probe 11, shared_row_class_undecided: a shared_-"
          "classed survivor abstains and a pack mutation stripping the prefix unblocks it; "
          "probe 12, the three repaired sibling packs (quality-adjective/intensive-agent/"
          "broken-plural): the recorded قوال/قويل/مقاول false passes stay reproducible under "
          "their unrepaired unit-v1.json packs and abstain under the repaired unit-v2.json packs; "
          "probe 13, the mafal_place/mu_participle collision resolved by the WRITTEN initial مـ "
          "vowel (reproduced false positives مجلس/منزل/مكتب refused, a genuine مُدَرِّس participle "
          "undisturbed, missing/unlicensed initial-مـ evidence abstains); probe 14, masdar_mimi as "
          "a genuinely pack-declared rival preserving alternatives over place_or_time_noun; "
          "probe 15, ela-r4's excluded_when exclusion as genuinely pack-declared data, not a "
          "hard-coded elative special case)")
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
