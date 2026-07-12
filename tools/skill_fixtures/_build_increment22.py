#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic builder for the INCREMENT-22 (sarf@2.2 / nahw@2.2 + norm rules) candidate rows + fixtures.

Consolidates the QAMUS-RICH-NORM-001 cycle: the rich-hover normative-defect ANDON (detector gaps
G1-G7), the norm@1 normalization contract (clauses N-ROOT / N-LANG / N-SEG / N-PED / N-CONS), the
global lexeme join + entry-root-inheritance lattice, and the C4/C5/W13 wave refinements.

Single source of two committed artifacts, emitted byte-deterministically (sorted keys, LF, trailing
newline) so re-running is a no-op:
  * qamus/skills/rule-registry-increment-22.jsonl        — candidate registry rows (schema-conformant)
  * tools/skill_fixtures/skill_fixtures_increment22.jsonl — red-first + branch-control fixtures

Every rule carries: source-addressed evidence, a positive (red-first) example, a boundary/control
example that proves the corrected discriminator BRANCHES (non-constant), defeaters, an abstention
condition, a `projector` sketch keyed for the transclusion/projection lattice, and a provenance
`domain` tag (`norm` for the norm@1 contract clauses / lexeme-join rules, else `sarf`/`nahw`).

Run:  python tools/skill_fixtures/_build_increment22.py            # write both files
      python tools/skill_fixtures/_build_increment22.py --check    # verify committed == regenerated
Stdlib only, deterministic, no network.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REGISTRY_OUT = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-22.jsonl")
FIXTURES_OUT = os.path.join(HERE, "skill_fixtures_increment22.jsonl")

# Evidence anchors (all committed in-repo so the addresses resolve).
ANDON = "impl-records/andon-rich-norm/QAMUS-RICH-NORM-001-TRACE.md"
NORM = "docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md"
JOIN = "qamus/reports/ROOT-INHERITANCE-JOIN.md"
SKEV = "impl-records/skill-evolution/INCREMENT-22-NOTES.md"


def q(loc):
    return "quran:" + loc


def _exid(prefix, sid, loc):
    return "%s-%s-%s" % (prefix, sid.upper().replace("-", "_"), loc.replace(":", "_"))


# Each rule: projector-lattice metadata + a positive (red-first) fixture + a branch control.
# proj.readiness ∈ {projector_ready, review_gated}. domain ∈ {norm, sarf, nahw}; clause = norm@1 id
# or ANDON gap / wave source.
RULES = [
    # ============================= SARF @2.2 — norm@1 contract clauses =============================
    {
        "sid": "sarf-norm-root-hedge-ban", "skill": "sarf", "rule": "root_hedge_ban",
        "fam": "root-hedge-ban", "phen": "content-segment-root-hedged", "domain": "norm", "clause": "N-ROOT-01",
        "scope": ("N-ROOT-01 (MUST): a row carrying a content segment (qg-verb-stem / qg-noun-stem / "
                  "qg-noun / qg-adjective / qg-verb / qg-proper-noun / generic qg-segment) MUST NOT "
                  "decline its root with hedge prose ('no public root asserted', 'function only no "
                  "root', 'no unsupported root added'). This catches the multi-segment hedge (فَحَقَّ = "
                  "FA+TOK) and the clean stem (خَلَقَ) that C2's single-segment gate skips."),
        "ev": [q("38:14:6"), q("16:3:1"), q("39:71:30"), NORM, ANDON],
        "defeaters": ["the row asserts a spaced-radical root (top-level root / morphline 'root ح ق ق' / segment sarf_note)",
                      "the row is a genuine function word carrying a typed rootless rationale (see N-ROOT-02)"],
        "abst": "root discoverable via an evidence tier but not yet authored → route to inheritance/authoring, never hedge",
        "readiness": "projector_ready",
        "proj": {"condition": "content-segment row where root is not asserted AND a hedge phrase is present",
                 "projection": "flag norm-nonconformant (N-ROOT-01); route to entry-root inheritance / authoring",
                 "guards": ["hedge blocklist is deterministic", "content-segment class membership"],
                 "scope": "surface-match"},
        "rels": [("extends", "sarf-pattern-never-certifies-root", "registry",
                  "The hedge ban is the positive-obligation partner to the two-tier certification bar.")],
        "pos": {"locs": ["38:14:6"], "surfaces": ["فحق"],
                "case": {"is_content_segment": True, "root_asserted": False, "hedge_present": True},
                "correct": "flag_root_hedge_violation", "wrong": "conform",
                "cite": "38:14:6 فَحَقَّ: FA+TOK (2 segments) hedges 'no public root asserted' though ح ق ق is the headword — C2's single-segment gate never sees it"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"is_content_segment": True, "root_asserted": True, "hedge_present": False},
                "correct": "conform",
                "cite": "39:71:30 حَقَّتْ asserts 'root ح ق ق' with STEM+SUBJ — the conformant target; the rule branches"},
    },
    {
        "sid": "sarf-norm-typed-rootless-rationale", "skill": "sarf", "rule": "typed_rootless_rationale",
        "fam": "typed-rootless-rationale", "phen": "rootless-without-typed-reason", "domain": "norm", "clause": "N-ROOT-02",
        "scope": ("N-ROOT-02 (SHOULD): a genuinely rootless row MUST carry an EXPLICIT TYPED rationale "
                  "from a closed vocabulary — function-word / proper-name / jamid-contested / pending — "
                  "in a dedicated field (no_root_reason / rootless_rationale). Never silent, never hedge "
                  "prose, never a free-text morphline standing in for the typed value."),
        "ev": [q("38:14:6"), q("36:70:5"), NORM],
        "defeaters": ["the row asserts a root (N-ROOT-02 is n/a)",
                      "the typed field carries one of the four closed-vocabulary values"],
        "abst": "rootless status genuinely uncertain → 'pending', never silent or hedge",
        "readiness": "review_gated",
        "proj": {"condition": "row asserts no root and carries no recognized typed-rationale field value",
                 "projection": "flag nonconformant; require a closed-vocabulary typed rationale (NEW field)",
                 "guards": ["closed-vocabulary enum", "hedge prose is not a typed value"],
                 "scope": "surface-match"},
        "rels": [("cites", "norm@1 N-ROOT-02 typed rootless rationale (RICH-HOVER-NORMALIZATION-CONTRACT.md)",
                  "external", "The typed-rationale field is the SHOULD complement to the N-ROOT-01 hedge ban.")],
        "pos": {"locs": ["38:14:6"], "surfaces": ["فحق"],
                "case": {"root_asserted": False, "typed_rationale": None},
                "correct": "flag_untyped_rootless", "wrong": "accept_silent_rootless",
                "cite": "38:14:6 فَحَقَّ declines its root with hedge prose and carries no typed rationale → nonconformant"},
        "ctl": {"locs": ["36:70:5"], "surfaces": ["ويحق"],
                "case": {"root_asserted": False, "typed_rationale": "function-word"},
                "correct": "conform_typed_rationale",
                "cite": "a legitimately rootless particle carrying the typed value 'function-word' conforms — the rule branches"},
    },
    {
        "sid": "sarf-norm-field-language-meta-ban", "skill": "sarf", "rule": "field_meta_ban",
        "fam": "field-language-meta-ban", "phen": "meta-language-or-label-leak", "domain": "norm", "clause": "N-LANG-01",
        "scope": ("N-LANG-01 (MUST): no rendered field (learner_explanation / gloss / sarf_note / "
                  "nahw_note / morphline) may carry internal validator/process meta-language ('no "
                  "unsupported public source label', 'visible piece accounted', 'preserved where "
                  "relevant', 'no public root asserted') — a SUPERSET of C4's three phrases — nor leaked "
                  "uppercase segment-label notation (FA:فَ, TOK:حَقَّ, ADJ:حَقِيقٌ) inside learner text."),
        "ev": [q("38:14:6"), q("36:70:8"), q("7:105:1"), NORM, ANDON],
        "defeaters": ["the field is clean English learner content with no meta-marker and no `\\b[A-Z]{1,6}:\\S` label leak"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "rendered field matches the meta-marker blocklist OR regex \\b[A-Z]{1,6}:\\S in learner_explanation",
                 "projection": "flag N-LANG-01 nonconformant; rewrite to clean English learner content",
                 "guards": ["case-insensitive blocklist (superset of C4)", "label-notation regex is validator-grade"],
                 "scope": "occurrence-match"},
        "rels": [("extends", "sarf-completeness-claim-requires-asserted-facts", "registry",
                  "Generalizes the C4 rendered-field honesty check to the full meta-language + label-leak blocklist.")],
        "pos": {"locs": ["38:14:6"], "surfaces": ["فحق"],
                "case": {"has_meta_marker": False, "has_label_notation": True},
                "correct": "flag_meta_language", "wrong": "conform_english_field",
                "cite": "38:14:6 learner text 'Visible pieces: FA:فَ + TOK:حَقَّ' leaks label notation — C4's 3-phrase filter misses it"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"has_meta_marker": False, "has_label_notation": False},
                "correct": "conform_english_field",
                "cite": "39:71:30 حَقَّتْ renders clean English notes — conformant; the rule branches"},
    },
    {
        "sid": "sarf-norm-english-led-rendered-fields", "skill": "sarf", "rule": "english_led",
        "fam": "english-led-fields", "phen": "arabic-prose-learner-dump", "domain": "norm", "clause": "N-LANG-02",
        "scope": ("N-LANG-02 (MUST): learner-facing fields MUST be English; learner_explanation MUST "
                  "NOT be an Arabic-prose dump. Flag when arabic_words>=6, OR (arabic_words>=4 AND "
                  "arabic_ratio>=0.6), OR (latin_words<3 AND arabic_words>=3). Short quoted Arabic "
                  "forms inside an English sentence stay clean."),
        "ev": [q("39:71:31"), NORM, ANDON],
        "defeaters": ["the field is substantive English with only short quoted Arabic forms (below the thresholds)"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "arabic_words>=6 OR (arabic_words>=4 and arabic_ratio>=0.6) OR (latin_words<3 and arabic_words>=3)",
                 "projection": "flag N-LANG-02 nonconformant; rewrite the learner field in English",
                 "guards": ["word-language counting is deterministic", "short quoted forms exempt"],
                 "scope": "occurrence-match"},
        "rels": [("cites", "norm@1 N-LANG-02 English-only rendered fields (RICH-HOVER-NORMALIZATION-CONTRACT.md)",
                  "external", "No released class inspects learner-text language balance.")],
        "pos": {"locs": ["39:71:31"], "surfaces": ["كلمة"],
                "case": {"arabic_words": 8, "latin_words": 1, "arabic_ratio": 0.9},
                "correct": "flag_arabic_dump", "wrong": "conform_english_led",
                "cite": "39:71:31 كَلِمَةُ dumps an Arabic iʿrāb string into the learner field (8 Arabic words, ratio 0.9)"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"arabic_words": 2, "latin_words": 12, "arabic_ratio": 0.14},
                "correct": "conform_english_led",
                "cite": "39:71:30 حَقَّتْ: English learner sentence with two short quoted forms — conformant; the rule branches"},
    },
    {
        "sid": "sarf-norm-gloss-contribution-present", "skill": "sarf", "rule": "gloss_present",
        "fam": "gloss-present", "phen": "blank-segment-gloss", "domain": "norm", "clause": "N-PED-01",
        "scope": ("N-PED-01 (MUST): every segment MUST carry a non-empty gloss_contribution — every "
                  "piece teaches. The released schema permits an empty gloss today; a blank "
                  "gloss_contribution on any segment is nonconforming."),
        "ev": [q("36:70:8"), NORM],
        "defeaters": ["every segment carries a non-empty gloss_contribution"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "any segment has a blank/empty gloss_contribution",
                 "projection": "flag N-PED-01 nonconformant; author the missing per-segment gloss",
                 "guards": ["per-segment non-empty check", "validator-grade"],
                 "scope": "surface-match"},
        "rels": [("cites", "norm@1 N-PED-01 gloss present (RICH-HOVER-NORMALIZATION-CONTRACT.md)",
                  "external", "Every segment must contribute a learner gloss.")],
        "pos": {"locs": ["36:70:8"], "surfaces": ["الكافرين"],
                "case": {"any_segment_blank_gloss": True},
                "correct": "flag_missing_gloss", "wrong": "conform_all_glossed",
                "cite": "a correctly-segmented row (ART+STEM+PL) with a blank gloss on a segment still fails N-PED-01"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"any_segment_blank_gloss": False},
                "correct": "conform_all_glossed",
                "cite": "39:71:30 حَقَّتْ glosses every segment (STEM + SUBJ) — conformant; the rule branches"},
    },
    {
        "sid": "sarf-norm-same-surface-root-coherence", "skill": "sarf", "rule": "same_surface_coherence",
        "fam": "same-surface-coherence", "phen": "same-surface-root-drift", "domain": "norm", "clause": "N-CONS-01",
        "scope": ("N-CONS-01 (MUST): within a diacritic-folded bare-surface group where >=1 content row "
                  "asserts a root, any content row that hedges/omits the root is nonconforming. The "
                  "producer had ح ق ق for حَقَّتْ (39:71:30) yet served فَحَقَّ (38:14:6) rootless 25 rows "
                  "away."),
        "ev": [q("39:71:30"), q("38:14:6"), q("36:70:5"), NORM, ANDON],
        "defeaters": ["no sibling in the same-surface group asserts a root (nothing to cohere with)",
                      "the divergence carries a recorded homograph rationale (a genuine two-reading surface)"],
        "abst": "same-surface conflict is a genuine homograph → record the homograph rationale, do not silently hedge",
        "readiness": "projector_ready",
        "proj": {"condition": "in a folded-bare-surface group with >=1 rooted content row, this content row hedges/omits the root",
                 "projection": "flag N-CONS-01 nonconformant; inherit the sibling's root or record a homograph rationale",
                 "guards": ["diacritic-folded grouping", "homograph-rationale escape hatch"],
                 "scope": "surface-match"},
        "rels": [("cites", "norm@1 N-CONS-01 same-surface root coherence (RICH-HOVER-NORMALIZATION-CONTRACT.md)",
                  "external", "Same-surface rows must have compatible analyses or a recorded homograph rationale.")],
        "pos": {"locs": ["38:14:6"], "surfaces": ["فحق"],
                "case": {"sibling_asserts_root": True, "this_row_hedges": True, "this_asserts_root": False},
                "correct": "flag_incoherent_sibling", "wrong": "no_cross_row_check",
                "cite": "38:14:6 فَحَقَّ hedges while sibling 39:71:30 حَقَّتْ asserts ح ق ق — incoherent"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"sibling_asserts_root": True, "this_asserts_root": True, "this_row_hedges": False},
                "correct": "coherent",
                "cite": "when both same-surface rows assert ح ق ق the group is coherent — the rule branches"},
    },
    {
        "sid": "sarf-entry-root-inheritance-tier0", "skill": "sarf", "rule": "entry_root_inherit",
        "fam": "entry-root-inheritance", "phen": "rootless-inheritable-from-entry", "domain": "norm", "clause": "N-CONS-02",
        "scope": ("N-CONS-02 / lexeme join: a rootless content row whose (dagger-alef-normalized) "
                  "surface matches a Qamus entry's headword or usage[].forms inherits that entry's root "
                  "as a CANDIDATE (tier-0). 16:3:1 خَلَقَ IS the headword of entry c8190204; 7:54:23 "
                  "مُسَخَّرَٰتٍ matches v198 usage.forms. Pattern alone never certifies — attested source "
                  "only — and the projection stays certification_state=candidate until the 2-vote."),
        "ev": [q("16:3:1"), q("7:54:23"), q("38:14:6"), JOIN, ANDON],
        "defeaters": ["the surface matches no entry headword/form → authoring-first (no fabricated inheritance)",
                      "the match is within-root ambiguous / homograph / cross-source-conflict → held for 2-vote"],
        "abst": "surface matches no attested entry form → authoring-first; never inherit from pattern shape",
        "readiness": "projector_ready",
        "proj": {"condition": "rootless content row; normalized surface == an entry headword/usage.form (attested source)",
                 "projection": "project the entry root as certification_state=candidate (tier-0 inheritance)",
                 "guards": ["attested-source only (never pattern)", "stays candidate until 2-vote", "divine-name exclusion"],
                 "scope": "root-match"},
        "rels": [("extends", "sarf-content-hold-absent-ownership-arm", "registry",
                  "The affirmative arm: an attested entry headword/form IS the ownership arm the HOLD rule waits for.")],
        "pos": {"locs": ["16:3:1"], "surfaces": ["خلق"],
                "case": {"surface_matches_entry_form": True, "attested_source": True},
                "correct": "inherit_candidate_root", "wrong": "served_rootless_no_inheritance",
                "cite": "16:3:1 خَلَقَ is the headword of entry c8190204 (خ ل ق) — inherit as candidate, no new authoring"},
        "ctl": {"locs": ["7:105:1"], "surfaces": ["حقيق"],
                "case": {"surface_matches_entry_form": False, "attested_source": False},
                "correct": "authoring_first",
                "cite": "a surface with no attested entry form routes to authoring-first — the rule branches, never fabricates"},
    },
    {
        "sid": "sarf-entry-id-context-only-not-root", "skill": "sarf", "rule": "entry_id_context_only",
        "fam": "entry-id-context-only", "phen": "bare-entry-id-mistaken-for-root", "domain": "norm", "clause": "JOIN-tierA",
        "scope": ("Lexeme-join correction: a row's carrier entry_id is an EXAMPLE-CONTEXT link, NOT a "
                  "root assertion — فَوْقَكُمُ carries the أخذ entry's id. The carrier certifies a root "
                  "ONLY when the surface is actually a form of that entry (tier-A self-join); a bare "
                  "entry_id NEVER asserts a root."),
        "ev": [q("16:3:1"), JOIN],
        "defeaters": ["the carried surface IS an attested form of the carrier entry → tier-A self-join is usable"],
        "abst": "carrier entry_id present but surface-is-a-form unverified → context-only, do not assert its root",
        "readiness": "projector_ready",
        "proj": {"condition": "a carrier entry_id is present but the row surface is NOT a form of that entry",
                 "projection": "PREVENT a root assertion from the bare id; keep it example-context only",
                 "guards": ["surface-is-a-form verification before tier-A use", "bare id is never a root"],
                 "scope": "root-match"},
        "rels": [("cites", "ROOT-INHERITANCE-JOIN.md tier-A entry_id-is-context-only correction",
                  "external", "The bare-entry_id-is-context-only correction that keeps tier-A honest.")],
        "pos": {"locs": ["16:3:1"], "surfaces": ["فوقكم"],
                "case": {"carrier_entry_id_present": True, "surface_is_form_of_entry": False},
                "correct": "context_only_no_root", "wrong": "assert_root_from_entry_id",
                "cite": "فَوْقَكُمُ carries the أخذ entry id as example-context — the id must NOT assert أخذ as its root"},
        "ctl": {"locs": ["16:3:1"], "surfaces": ["خلق"],
                "case": {"carrier_entry_id_present": True, "surface_is_form_of_entry": True},
                "correct": "carrier_usable_tierA",
                "cite": "when the surface IS a form of the carrier entry, tier-A self-join is usable — the rule branches"},
    },
    {
        "sid": "sarf-rooted-vs-entry-conflict-never-auto-resolve", "skill": "sarf", "rule": "root_entry_conflict",
        "fam": "root-entry-conflict", "phen": "row-entry-root-disagreement", "domain": "norm", "clause": "JOIN-conflict",
        "scope": ("Lexeme-join conflict: when a row's asserted root DISAGREES with the root of the "
                  "entry that attests the same surface (464 rows / 804 root_conflict edges in the join), "
                  "route to 2-vote/review and NEVER auto-resolve. An agreeing row/entry pair is "
                  "confirmed (root_confirms)."),
        "ev": [q("66:6:12"), JOIN],
        "defeaters": ["row root and entry root are equal after normalization → confirm (root_confirms)"],
        "abst": "row/entry roots disagree → 2-vote/review; never majority-vote or pick one automatically",
        "readiness": "projector_ready",
        "proj": {"condition": "row asserts root_a and the matched entry attests root_b and root_a != root_b",
                 "projection": "route engine-diverse 2-vote/review; block auto-resolution",
                 "guards": ["orthography normalization before compare", "never auto-resolve a conflict"],
                 "scope": "root-match"},
        "rels": [("extends", "sarf-cross-source-root-conflict-no-majority-vote", "registry",
                  "Extends the never-majority-vote conflict veto from two SOURCES to row-vs-entry.")],
        "pos": {"locs": ["66:6:12"], "surfaces": ["ملائكة"],
                "case": {"row_root": "ألك", "entry_root": "ملك"},
                "correct": "route_two_vote_never_auto", "wrong": "auto_resolve_pick_one",
                "cite": "a row asserting ألك against an entry attesting ملك for the same surface routes to 2-vote — never auto-resolved"},
        "ctl": {"locs": ["16:3:1"], "surfaces": ["خلق"],
                "case": {"row_root": "خلق", "entry_root": "خلق"},
                "correct": "confirm_coherent",
                "cite": "16:3:1 خَلَقَ: row root == entry root (خ ل ق) → confirm; the rule branches"},
    },
    # ============================= SARF @2.2 — ANDON detector gaps + C4/C5/W13 =====================
    {
        "sid": "sarf-root-in-madda-prose-recognized", "skill": "sarf", "rule": "madda_prose_root",
        "fam": "madda-prose-root", "phen": "root-in-madda-idiom-unparsed", "domain": "sarf", "clause": "G4",
        "scope": ("ANDON gap G4: a root carried in the Arabic lexicographic idiom مادة (كلم) / مادّة is "
                  "an ASSERTED root. The released `_ROOT_ARABIC_RE` recognized only the pattern `root "
                  "<radicals>` and read a row carrying its root in مادة-prose as rootless (39:71:31 "
                  "كَلِمَةُ carries 'مادة (كلم)')."),
        "ev": [q("39:71:31"), ANDON],
        "defeaters": ["no مادة idiom and no root field → genuinely rootless"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "a root appears in the مادة/مادّة (radicals) idiom (not the `root <radicals>` form)",
                 "projection": "recognize the root as ASSERTED; do not classify the row rootless",
                 "guards": ["مادة-idiom parse added to the root recognizer", "radicals extracted from the parenthetical"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf §5 root decision ladder (SKILL.md:105)",
                  "external", "Extends the root recognizer to the مادة lexicographic idiom.")],
        "pos": {"locs": ["39:71:31"], "surfaces": ["كلمة"],
                "case": {"madda_prose_present": True},
                "correct": "root_asserted_from_madda", "wrong": "rootless",
                "cite": "39:71:31 كَلِمَةُ carries 'مادة (كلم)' — an asserted root ك ل م the `root …` regex missed"},
        "ctl": {"locs": ["7:105:1"], "surfaces": ["حقيق"],
                "case": {"madda_prose_present": False, "root_field_present": False},
                "correct": "rootless",
                "cite": "a row with neither a مادة idiom nor a root field is genuinely rootless — the rule branches"},
    },
    {
        "sid": "sarf-sound-plural-suffix-swallow-detect", "skill": "sarf", "rule": "sound_plural_swallow",
        "fam": "sound-plural-suffix-swallow", "phen": "sound-plural-blob-swallow", "domain": "sarf", "clause": "G6/O-2",
        "scope": ("ANDON gap G6 / O-2: C5's enclitic vocabulary is PRONOUN-only, so a sound feminine/"
                  "masculine plural ـات / ـين (+ tanwīn) fused into a single blob (7:54:23 مُسَخَّرَٰتٍ) "
                  "is a suffix-swallow that escapes C5. Detect it and split STEM + PL-F/PL, INDEPENDENT "
                  "of the root check. GUARD: a trailing ت that is a ROOT RADICAL routes to 2-vote, not a "
                  "split (sarf-root-radical-not-clitic)."),
        "ev": [q("7:54:23"), q("36:70:8"), ANDON, JOIN],
        "defeaters": ["the plural suffix is already its own segment (ينَ split, as in الكافرين) → conformant",
                      "the trailing ـات ت is a root radical → the guard routes to 2-vote, no split"],
        "abst": "trailing ت radical-vs-suffix genuinely uncertain → 2-vote, never a blind split",
        "readiness": "projector_ready",
        "proj": {"condition": "single-blob token ending in a sound plural ـات/ـين (+tanwīn), suffix not segmented",
                 "projection": "flag a suffix-swallow; project STEM + PL-F/PL split (closes the O-2 gap)",
                 "guards": ["radical-ت guard routes to 2-vote", "independent of the root check"],
                 "scope": "construction-match"},
        "rels": [("extends", "sarf-root-radical-not-clitic", "registry",
                  "Adds the sound-plural suffix vocabulary C5 lacked, with the radical-ت homograph guard.")],
        "pos": {"locs": ["7:54:23"], "surfaces": ["مسخرت"],
                "case": {"ends_sound_plural": True, "single_blob": True, "trailing_ta_is_radical": False},
                "correct": "flag_plural_swallow", "wrong": "no_flag_pl_pronoun_only",
                "cite": "7:54:23 مُسَخَّرَٰتٍ swallows a sound-fem-plural ـٰتٍ into one TOK — C5's pronoun-only vocabulary misses it"},
        "ctl": {"locs": ["36:70:8"], "surfaces": ["الكافرين"],
                "case": {"ends_sound_plural": True, "single_blob": False},
                "correct": "conform_pl_segment",
                "cite": "36:70:8 الْكَافِرِينَ already splits PL ينَ — conformant; the rule branches"},
        "extra": [
            {"locs": ["2:3:8"], "surfaces": ["ابيات"],
             "case": {"ends_sound_plural": True, "single_blob": True, "trailing_ta_is_radical": True},
             "correct": "guard_two_vote_radical_ta", "wrong": "no_flag_pl_pronoun_only",
             "cite": "when the trailing ت is a ROOT RADICAL the guard routes to 2-vote, never a blind PL-F split"},
        ],
    },
    {
        "sid": "sarf-mu-pattern-taught-not-coloured", "skill": "sarf", "rule": "mu_pattern_taught",
        "fam": "mu-pattern-taught", "phen": "mu-pattern-named-not-peeled", "domain": "sarf", "clause": "C5/W1-A",
        "scope": ("C5 / W1-A pedagogy: the مُ- derivational pattern (مُفَعَّل / تَفَعَّل) is STEM-INTERNAL "
                  "for colour — never peeled as a separate coloured segment (per the DR-1 wazn-augment "
                  "boundary) — BUT when the entry attests the form the pattern MUST be NAMED in the "
                  "morphline (مُسَخَّر → 'Form II passive participle, wazn mufaʿʿal'). If unattested it is "
                  "held, never fabricated."),
        "ev": [q("7:54:23"), JOIN],
        "defeaters": ["the entry attests the derived form → name the pattern in the morphline (taught)",
                      "the مُ- token is not a derivational pattern at all → n/a"],
        "abst": "مُ-pattern present but the form is unattested → hold, do not name a fabricated wazn",
        "readiness": "projector_ready",
        "proj": {"condition": "token carries a مُ- derivational pattern AND the entry attests the derived form",
                 "projection": "NAME the pattern (wazn) in the morphline as taught; keep the مُ stem-internal (no coloured peel)",
                 "guards": ["entry-attestation required to name", "colour keeps the augment stem-internal (DR-1)"],
                 "scope": "construction-match"},
        "rels": [("extends", "sarf-form-v-vi-ta-is-wazn-augment", "registry",
                  "Colour partner: like the Form V/VI ت, the مُ- augment is stem-internal but must be NAMED when attested.")],
        "pos": {"locs": ["7:54:23"], "surfaces": ["مسخرت"],
                "case": {"mu_pattern": True, "entry_attests_form": True},
                "correct": "name_pattern_stem_internal", "wrong": "peel_or_silent_mu",
                "cite": "7:54:23 مُسَخَّرَٰتٍ: v198 attests مُسَخَّرَات → name 'Form II passive participle, wazn mufaʿʿal'; keep مُ stem-internal"},
        "ctl": {"locs": ["7:105:1"], "surfaces": ["حقيق"],
                "case": {"mu_pattern": True, "entry_attests_form": False},
                "correct": "hold_not_attested",
                "cite": "a مُ-shaped token whose form the entries do not attest is held, never named — the rule branches"},
    },
    {
        "sid": "sarf-honest-sentence-template", "skill": "sarf", "rule": "honest_template",
        "fam": "honest-sentence-template", "phen": "template-renders-unasserted-slots", "domain": "sarf", "clause": "C4/telemetry",
        "scope": ("C4 + measured-effect telemetry: the learner sentence renders from a TEMPLATE whose "
                  "slots emit ONLY facts the morphline actually asserts; if any slot fact is abstained "
                  "the honest-generic variant renders. Generalizes the completeness-claim rule; the "
                  "100%-agreement telemetry (ONH-B5 et al.) confirms the honest form is the measured "
                  "target."),
        "ev": [q("36:70:8"), q("2:40:3"), ANDON, SKEV],
        "defeaters": ["every template slot's fact is asserted by the morphline → the full template may render"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "the learner template has any slot whose fact the morphline does not assert",
                 "projection": "render the honest-generic variant (deterministic; no morphology authoring needed)",
                 "guards": ["render-time slot/field check", "no morphology work required for the honesty fix"],
                 "scope": "occurrence-match"},
        "rels": [("extends", "sarf-completeness-claim-requires-asserted-facts", "registry",
                  "Generalizes the single completeness sentence into a per-slot honest-template rule.")],
        "pos": {"locs": ["36:70:8"], "surfaces": ["الكافرين"],
                "case": {"all_slot_facts_asserted": False},
                "correct": "render_honest_generic", "wrong": "render_full_template",
                "cite": "a template with an unasserted slot must fall back to the honest-generic learner variant"},
        "ctl": {"locs": ["2:40:3"], "surfaces": ["اذكروا"],
                "case": {"all_slot_facts_asserted": True},
                "correct": "render_full_template",
                "cite": "once every slot fact is asserted the full template may render — the rule branches"},
    },
    {
        "sid": "sarf-loc-range-external-authority-prevalidation", "skill": "sarf", "rule": "loc_external_authority",
        "fam": "loc-external-authority", "phen": "local-index-circular-prevalidation", "domain": "sarf", "clause": "C5/W1-A",
        "scope": ("C5 / W1-A: a loc-range / address claim MUST be prevalidated against an EXTERNAL "
                  "authority (corpus/wbw oracle) — a local index validating itself is CIRCULAR. The "
                  "17:1:22 catch proved a local index confirmed an address the external authority "
                  "rejected. Local-only confirmation cannot prevalidate."),
        "ev": [q("17:1:22"), ANDON],
        "defeaters": ["an external authority (corpus/wbw oracle) confirms the address → emit"],
        "abst": "only a local index confirms the address → cannot prevalidate; do not emit on circular evidence",
        "readiness": "projector_ready",
        "proj": {"condition": "an address is confirmed only by a local index and not by an external authority",
                 "projection": "cannot prevalidate (circular); block the emit until an external authority confirms",
                 "guards": ["external authority is required", "local self-confirmation is circular"],
                 "scope": "loc-match"},
        "rels": [("extends", "sarf-loc-integrity-address-xcheck", "registry",
                  "Adds the anti-circularity rule: the cross-check authority must be EXTERNAL, not a local index.")],
        "pos": {"locs": ["17:1:22"], "surfaces": ["بصير"],
                "case": {"external_authority_confirms": False, "only_local_index": True},
                "correct": "cannot_prevalidate_local_circular", "wrong": "emit_from_local_index",
                "cite": "17:1:22 was self-confirmed by a local index yet rejected by the external authority — circular, blocked"},
        "ctl": {"locs": ["2:189:6"], "surfaces": ["مواقيت"],
                "case": {"external_authority_confirms": True, "only_local_index": False},
                "correct": "emit_prevalidated",
                "cite": "2:189:6 confirmed by the external corpus oracle → emit; the rule branches"},
    },
    {
        "sid": "sarf-demonstrative-dagger-alef-normalize", "skill": "sarf", "rule": "dagger_alef_normalize",
        "fam": "dagger-alef-normalization", "phen": "dagger-alef-match-miss", "domain": "sarf", "clause": "W13",
        "scope": ("W13: the demonstrative ذٰلِك / كَذٰلِك (and forms like مُسَخَّرَٰت) carries a superscript "
                  "dagger-alef (U+0670) that the match engine missed TWICE. Normalize dagger-alef → "
                  "plain alif before the wbw / entry-form match; a form that already matches without a "
                  "dagger-alef is untouched."),
        "ev": [q("2:2:1"), q("7:54:23"), JOIN],
        "defeaters": ["the surface has no dagger-alef → the plain match key already applies"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "the surface contains U+0670 (dagger-alef); fold it to plain alif before matching",
                 "projection": "match against the entry/wbw form after normalization (recovers ذٰلك / مُسَخَّرَٰت)",
                 "guards": ["fold U+0670 → ا only (hamza/alif-maqṣūra preserved)", "vendored wbw normalize key"],
                 "scope": "surface-match"},
        "rels": [("cites", "services/qamus_wbw/normalize.py::norm dagger-alef fold (ROOT-INHERITANCE-JOIN.md match key)",
                  "external", "The match key must fold the dagger-alef the demonstrative/derived forms carry.")],
        "pos": {"locs": ["2:2:1"], "surfaces": ["ذلك"],
                "case": {"has_dagger_alef": True, "normalized_matches": True},
                "correct": "match_after_normalization", "wrong": "engine_miss_no_match",
                "cite": "2:2:1 ذَٰلِكَ carries U+0670 — folding it to plain alif recovers the match the engine missed twice"},
        "ctl": {"locs": ["16:3:1"], "surfaces": ["خلق"],
                "case": {"has_dagger_alef": False, "normalized_matches": True},
                "correct": "match_plain",
                "cite": "16:3:1 خَلَقَ has no dagger-alef — the plain key already matches; the rule branches"},
    },
    # ============================= NAHW @2.2 — rendered-note discipline ============================
    {
        "sid": "nahw-norm-note-leads-english", "skill": "nahw", "rule": "note_leads_english",
        "fam": "note-leads-english", "phen": "note-opens-arabic-dump", "domain": "norm", "clause": "N-LANG-03",
        "scope": ("N-LANG-03 (SHOULD): a sarf_note / nahw_note MAY cite Arabic grammatical terms but "
                  "MUST lead with English; a note that opens as an Arabic-prose dump is nonconforming."),
        "ev": [q("39:71:31"), NORM],
        "defeaters": ["the note opens with a substantive English clause before any Arabic term"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "a sarf_note/nahw_note opens with sustained Arabic prose rather than English",
                 "projection": "flag N-LANG-03 nonconformant; lead the note with English, Arabic terms may follow",
                 "guards": ["leading-token language check", "advisory (SHOULD)"],
                 "scope": "occurrence-match"},
        "rels": [("cites", "norm@1 N-LANG-03 note-leads-English (RICH-HOVER-NORMALIZATION-CONTRACT.md)",
                  "external", "Grammatical notes may cite Arabic terms but must lead in English.")],
        "pos": {"locs": ["39:71:31"], "surfaces": ["كلمة"],
                "case": {"note_leads_arabic_dump": True},
                "correct": "flag_note_not_english_led", "wrong": "conform_english_led_note",
                "cite": "39:71:31 كَلِمَةُ opens its note 'اسم، مؤنث، مفرد …' — Arabic-led, nonconformant"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"note_leads_arabic_dump": False},
                "correct": "conform_english_led_note",
                "cite": "39:71:30 حَقَّتْ leads its note in English — conformant; the rule branches"},
    },
    {
        "sid": "nahw-irab-note-not-verbatim-source", "skill": "nahw", "rule": "irab_not_verbatim",
        "fam": "irab-not-verbatim", "phen": "verbatim-source-irab-pasted", "domain": "norm", "clause": "N-LANG-01",
        "scope": ("N-LANG-01/02 for the iʿrāb note: the nahw_note MUST NOT be the raw upstream-analyzer "
                  "Arabic iʿrāb string pasted VERBATIM into the learner field (39:71:31 كَلِمَةُ carried "
                  "'فاعل مرفوع وعلامة رفعه الضمة وهو مضاف'); render an English iʿrāb ('subject, "
                  "nominative; first term of an iḍāfa')."),
        "ev": [q("39:71:31"), NORM, ANDON],
        "defeaters": ["the nahw_note is an English iʿrāb (with at most short quoted Arabic terms)"],
        "abst": None,
        "readiness": "projector_ready",
        "proj": {"condition": "the nahw_note equals the raw-analyzer Arabic iʿrāb string verbatim (sustained Arabic prose)",
                 "projection": "flag N-LANG nonconformant; author an English iʿrāb note",
                 "guards": ["verbatim-Arabic detection is deterministic", "short quoted terms exempt"],
                 "scope": "occurrence-match"},
        "rels": [("cites", "norm@1 N-LANG-01/02 rendered-field discipline (RICH-HOVER-NORMALIZATION-CONTRACT.md)",
                  "external", "The raw analyzer iʿrāb is analysis input, not learner-rendered copy.")],
        "pos": {"locs": ["39:71:31"], "surfaces": ["كلمة"],
                "case": {"nahw_note_is_verbatim_source_arabic": True},
                "correct": "flag_verbatim_irab", "wrong": "conform_english_irab",
                "cite": "39:71:31 nahw_note 'فاعل مرفوع وعلامة رفعه الضمة وهو مضاف' is the raw analyzer string pasted verbatim"},
        "ctl": {"locs": ["39:71:30"], "surfaces": ["حقت"],
                "case": {"nahw_note_is_verbatim_mcp_arabic": False},
                "correct": "conform_english_irab",
                "cite": "39:71:30 renders an English iʿrāb note — conformant; the rule branches"},
    },
    {
        "sid": "nahw-mood-note-commits-or-named-ambiguity", "skill": "nahw", "rule": "mood_note_commit",
        "fam": "mood-note-commit", "phen": "mood-note-hedged-as-context", "domain": "norm", "clause": "N-PED-02",
        "scope": ("N-PED-02 for the mood note: when mood is knowable at the exact address the nahw_note "
                  "MUST commit it and MUST NOT hedge 'as (the) context requires'; when genuinely "
                  "unknowable it states a named ambiguity."),
        "ev": [q("17:12:16"), q("102:3:3"), NORM],
        "defeaters": ["mood is knowable and the note commits it (no hedge)",
                      "mood is genuinely qirāʾāt-split/unknowable → a named ambiguity is legal, not a hedge"],
        "abst": "mood genuinely unknowable at the address → named ambiguity, never the 'as context requires' hedge",
        "readiness": "projector_ready",
        "proj": {"condition": "mood is knowable at the address AND the note hedges 'as (the) context requires'",
                 "projection": "flag N-PED-02 nonconformant; commit the mood in the note",
                 "guards": ["knowability determined by the governor/final-vowel", "named-ambiguity escape hatch"],
                 "scope": "construction-match"},
        "rels": [("extends", "nahw-mood-from-governor", "registry",
                  "The rendered-note obligation partner to the mood-from-governor rule.")],
        "pos": {"locs": ["17:12:16"], "surfaces": ["ولتعلموا"],
                "case": {"mood_knowable": True, "note_hedges_as_context": True},
                "correct": "flag_uncommitted_mood_note", "wrong": "hedge_as_context_accepted",
                "cite": "17:12:16 mood is knowable (منصوب بأن مضمرة) yet the note hedges 'as context requires' → nonconformant"},
        "ctl": {"locs": ["102:3:3"], "surfaces": ["تعلمون"],
                "case": {"mood_knowable": True, "note_hedges_as_context": False},
                "correct": "commit_mood_note",
                "cite": "102:3:3 تَعْلَمُونَ: mood knowable (marfūʿ indicative) and the note commits it — the rule branches"},
    },
]


def build_registry_rows():
    rows = []
    for r in RULES:
        sid = r["sid"]
        sk = r["skill"]
        pos_ex = [_exid("INC22", sid, r["pos"]["locs"][0])]
        for i, f in enumerate(r.get("extra", [])):
            pos_ex.append(_exid("INC22X%d" % (i + 1), sid, f["locs"][0]))
        ctl_ex = _exid("INC22CTL", sid, r["ctl"]["locs"][0])
        rels = [{"type": t, "target_id": tid, "target_kind": kind, "note": note}
                for (t, tid, kind, note) in r["rels"]]
        proj = {"readiness": r["readiness"]}
        proj.update(r["proj"])
        row = {
            "skill_rule_id": sid,
            "skill": sk,
            "skill_version": sk + "@2.2",
            "status": "candidate",
            "fact_family": r["fam"],
            "scope": r["scope"],
            "evidence_addresses": r["ev"],
            "positive_examples": pos_ex,
            "negative_or_boundary_examples": [ctl_ex],
            "defeaters": r["defeaters"],
            "abstention_condition": r["abst"],
            "gate": "@2.2-candidate:redfirst+branch-proven",
            "code_references": ["tools/skill_fixtures/skill_rules_increment22.py"],
            "test_references": ["tools/skill_fixtures/test_skill_fixtures_increment22.py"],
            "relationships": rels,
            "provenance": {
                "origin": "increment-22-rich-norm-consolidation",
                "cycle": "2026-07-12",
                "source": SKEV,
                "projector_readiness": r["readiness"],
                "phenomenon": r["phen"],
                "domain": r["domain"],
                "clause": r["clause"],
            },
            "projector": proj,
        }
        rows.append(row)
    return rows


def build_fixture_rows():
    fixtures = []
    for r in RULES:
        sid = r["sid"]
        for kind, red in (("pos", True), ("ctl", False)):
            f = r[kind]
            ex = _exid("INC22" if red else "INC22CTL", sid, f["locs"][0])
            fx = {
                "fixture_id": ("inc22-%s-%s" % (sid, "pos" if red else "ctl")),
                "example_id": ex,
                "rule_id": sid,
                "rule": r["rule"],
                "skill_version": r["skill"] + "@2.2",
                "phenomenon": r["phen"],
                "domain": r["domain"],
                "canonical_locations": f["locs"],
                "surfaces": f.get("surfaces", []),
                "case": f["case"],
                "correct_label": f["correct"],
                "redfirst": red,
                "citation": f["cite"],
            }
            if red:
                fx["wrong_label"] = f["wrong"]
            fixtures.append(fx)
        for i, f in enumerate(r.get("extra", [])):
            ex = _exid("INC22X%d" % (i + 1), sid, f["locs"][0])
            fx = {
                "fixture_id": ("inc22-%s-x%d" % (sid, i + 1)),
                "example_id": ex,
                "rule_id": sid,
                "rule": r["rule"],
                "skill_version": r["skill"] + "@2.2",
                "phenomenon": r["phen"],
                "domain": r["domain"],
                "canonical_locations": f["locs"],
                "surfaces": f.get("surfaces", []),
                "case": f["case"],
                "correct_label": f["correct"],
                "redfirst": True,
                "citation": f["cite"],
                "wrong_label": f["wrong"],
            }
            fixtures.append(fx)
    return fixtures


def _dump(path, rows):
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return body


def _read(path):
    if not os.path.exists(path):
        return None
    return open(path, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify committed == regenerated (exit 1 on drift)")
    a = ap.parse_args()
    reg_rows = build_registry_rows()
    fx_rows = build_fixture_rows()
    reg_body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in reg_rows)
    fx_body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in fx_rows)
    if a.check:
        drift = []
        if _read(REGISTRY_OUT) != reg_body:
            drift.append("rule-registry-increment-22.jsonl")
        if _read(FIXTURES_OUT) != fx_body:
            drift.append("skill_fixtures_increment22.jsonl")
        if drift:
            print("DRIFT (regenerate via _build_increment22.py): " + ", ".join(drift))
            return 1
        print("increment-22 builder: committed artifacts match regeneration (%d rules, %d fixtures)"
              % (len(reg_rows), len(fx_rows)))
        return 0
    _dump(REGISTRY_OUT, reg_rows)
    _dump(FIXTURES_OUT, fx_rows)
    sarf = sum(1 for r in reg_rows if r["skill"] == "sarf")
    nahw = sum(1 for r in reg_rows if r["skill"] == "nahw")
    norm = sum(1 for r in reg_rows if r["provenance"]["domain"] == "norm")
    print("wrote %s (%d rules: %d sarf, %d nahw; %d norm-domain)"
          % (os.path.relpath(REGISTRY_OUT, REPO), len(reg_rows), sarf, nahw, norm))
    print("wrote %s (%d fixtures)" % (os.path.relpath(FIXTURES_OUT, REPO), len(fx_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
