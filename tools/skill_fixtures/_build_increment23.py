#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic builder for the INCREMENT-23 (sarf@2.3 / nahw@2.3 candidate) rows + fixtures.

Window-1-measured flywheel input (2026-07-16): the WAVE-RECORD adjudicator catches + the C2-reviewerA
calibration deltas of the first live seeding window are distilled into 8 candidate @2.3 rules — 6 sarf
(surface-join root veto, closed-class rootless, cross-source root hold, root display-consistency,
per-segment gloss completeness, orthographic match symmetry) and 2 nahw (basmala-aware loc authority,
surface↔gloss single-wordlist binding). Companion to skill_rules.py + skill_rules_richseg.py +
skill_rules_increment21.py + skill_rules_increment22.py, kept SEPARATE so it does not collide with the
released @2 / candidate @2.1 / @2.2 fixtures; it merges alongside them at the @2.3 release.

Single source of two committed artifacts, emitted byte-deterministically (sorted keys, LF, trailing
newline) so re-running is a no-op:
  * qamus/skills/rule-registry-increment-23.jsonl        — candidate registry rows (schema-conformant)
  * tools/skill_fixtures/skill_fixtures_increment23.jsonl — red-first + branch-control fixtures

Every rule carries: source-addressed evidence, >=1 positive (red-first) example, a boundary/control
example that proves the corrected discriminator BRANCHES (non-constant), defeaters, an abstention
condition, a `projector` sketch keyed for the transclusion/projection lattice, and a provenance
`domain` tag (`norm` for the norm@1 contract clauses; else `root`/`addressing`/`binding`/`matching`).
Norm-domain rules also carry a `clause` (N-ROOT-03 / N-PED-01) on both the registry provenance and the
fixture rows.

Run:  python tools/skill_fixtures/_build_increment23.py            # write both files
      python tools/skill_fixtures/_build_increment23.py --check    # verify committed == regenerated
Stdlib only, deterministic, no network. RM-09: repo-relative evidence anchors only (no server paths, hosts, or IPs).
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REGISTRY_OUT = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-23.jsonl")
FIXTURES_OUT = os.path.join(HERE, "skill_fixtures_increment23.jsonl")

# Evidence anchors (all repo-relative so the addresses resolve; RM-09: no server paths, hosts, or IP literals).
WAVE = "impl-records/WINDOW-1-2026-07-16-WAVE-RECORD.md"
CALIB = "impl-records/calibration/C2-reviewerA.md"
NORM = "docs/qamus/RICH-HOVER-NORMALIZATION-CONTRACT.md"
SKEV = "impl-records/skill-evolution/INCREMENT-23-NOTES.md"


def q(loc):
    return "quran:" + loc


# Each rule: projector-lattice metadata + an ORDERED fixtures list. Fixture entries carry an explicit
# fixture_id + example_id (the Window-1 slugs are custom, not mechanically loc-derived) and, for the
# red-first ones, a `wrong` label. `domain` is emitted on the fixture rows only for norm-domain rules.
# readiness ∈ {projector_ready, review_gated}; domain ∈ {root, norm, addressing, binding, matching};
# clause = norm@1 id (only on norm-domain rules).
RULES = [
    # ================================ SARF @2.3 — root-certification gates ============================
    {
        "sid": "sarf-surface-join-never-certifies-root", "skill": "sarf", "rule": "surface_join",
        "fam": "root-certification-gate", "phen": "wrong-root-join-laundering", "domain": "root", "clause": None,
        "readiness": "projector_ready",
        "scope": ("A same-surface / same-consonant-skeleton join to an entry-form NEVER certifies a root "
                  "for an occurrence: the root must be confirmed per-occurrence by a surface-matched "
                  "certified مادة. Hollow (ajwaf), geminate (muḍaʿʿaf) and weak-final (nāqiṣ) skeletons "
                  "collide under the same surface, so an inherited entry root routinely mis-labels a "
                  "distinct occurrence (مال surface fits both م و ل and the ميل-family م ي ل; نُقِرُّ ق ر ر "
                  "collides with ن ق ر; يد ي د ي collides with أ ي د). This is the خُلِّفُوا precedent "
                  "generalized: shared skeleton ≠ shared مادة."),
        "ev": [q("6:152:3"), q("24:33:24"), q("22:5:27"), q("24:40:20"), WAVE, CALIB],
        "defeaters": ["a per-occurrence surface-matched certified مادة confirms the same root the join proposed (join agrees with evidence)",
                      "the occurrence is a strong triliteral whose three radicals appear contiguously in the surface AND match the entry مادة (no skeleton collision possible)"],
        "abst": "join proposes a root but no per-occurrence مادة present → stay candidate_root_uncertified; never certify from the join",
        "proj": {"condition": "occurrence root is inherited by surface/skeleton join from an entry-form and no per-occurrence surface-matched certified مادة confirms it",
                 "projection": "downgrade to candidate_root_uncertified; route per-occurrence confirmation; block join-inherited certification",
                 "guards": ["per-occurrence مادة required (surface-matched analyze_word)", "hollow/geminate/weak-final skeleton-collision flag", "strong-radical backstop is confirmation-not-certification"],
                 "scope": "root-match"},
        "rels": [("extends", "sarf-pattern-never-certifies-root", "registry",
                  "Strengthens the two-tier certification bar with a per-occurrence join veto; the join is an inference tier, not a certification tier.")],
        "fixtures": [
            {"fid": "inc23-sarf-surface-join-never-certifies-root-mal-pos",
             "eid": "INC23-SARF_SURFACE_JOIN_NEVER_CERTIFIES_ROOT-6_152_3", "red": True,
             "loc": "6:152:3", "surfaces": ["مال"],
             "case": {"join_root": "م ي ل", "occurrence_madda": "م و ل", "skeleton_collision": "ajwaf", "per_occurrence_madda_present": False},
             "correct": "candidate_root_uncertified", "wrong": "certify_join_root",
             "cite": "6:152:3 مال join inherited م ي ل from a ميل-family entry; the true occurrence مادة is م و ل (hollow collision) — join must not certify"},
            {"fid": "inc23-sarf-surface-join-never-certifies-root-nuqirr-pos",
             "eid": "INC23-SARF_SURFACE_JOIN_NEVER_CERTIFIES_ROOT-22_5_27", "red": True,
             "loc": "22:5:27", "surfaces": ["ونقر"],
             "case": {"join_root": "ن ق ر", "occurrence_madda": "ق ر ر", "skeleton_collision": "muda'af", "per_occurrence_madda_present": False},
             "correct": "candidate_root_uncertified", "wrong": "certify_join_root",
             "cite": "22:5:27 وَنُقِرُّ join said ن ق ر; true مادة is geminate ق ر ر — geminate/strong skeleton collision, no certification from join"},
            {"fid": "inc23-sarf-surface-join-never-certifies-root-yadahu-pos",
             "eid": "INC23-SARF_SURFACE_JOIN_NEVER_CERTIFIES_ROOT-24_40_20", "red": True,
             "loc": "24:40:20", "surfaces": ["يده"],
             "case": {"join_root": "أ ي د", "occurrence_madda": "ي د ي", "skeleton_collision": "naqis", "per_occurrence_madda_present": False},
             "correct": "candidate_root_uncertified", "wrong": "certify_join_root",
             "cite": "24:40:20 يده join said أ ي د; true مادة is weak-final ي د ي — nāqiṣ collision, join laundering refused"},
            {"fid": "inc23-sarf-surface-join-never-certifies-root-ctl",
             "eid": "INC23CTL-SARF_SURFACE_JOIN_NEVER_CERTIFIES_ROOT-16_3_1", "red": False,
             "loc": "16:3:1", "surfaces": ["خلق"],
             "case": {"join_root": "خ ل ق", "occurrence_madda": "خ ل ق", "skeleton_collision": "none_strong_triliteral", "per_occurrence_madda_present": True},
             "correct": "root_certified",
             "cite": "16:3:1 خَلَقَ strong triliteral with all three radicals contiguous AND a per-occurrence مادة خ ل ق agreeing with the join — certifies (rule branches)"},
        ],
    },
    {
        "sid": "sarf-closed-class-never-inherits-root", "skill": "sarf", "rule": "closed_class",
        "fam": "closed-class-rootless", "phen": "function-word-root-laundering", "domain": "root", "clause": None,
        "readiness": "projector_ready",
        "scope": ("A closed-class function word (particle حرف, pronoun ضمير, relative اسم موصول, "
                  "demonstrative اسم إشارة, interrogative اسم استفهام, and the mabnī particle-nouns) "
                  "NEVER inherits a content مادة by surface join: من must not carry م ن ن (from the منّ "
                  "entry), لا must not carry أ ل ل or ب غ ي, هم must not carry ه م م. Their ṣarf analysis "
                  "is حرف or اسم مبني with no مادة (rootless). The surface-join laundering that assigns "
                  "them a content root is a guaranteed reject and must be filtered pre-evidence."),
        "ev": [q("2:284:1"), WAVE, CALIB],
        "defeaters": ["the surface is a genuine content homograph of a function word confirmed content by per-occurrence مادة (e.g. مَنَّ the verb 'bestowed', not the particle من) — POS disambiguation first",
                      "the token is already labelled rootless with a typed no_root_reason=function-word (N-ROOT-02 conformant) — nothing to strip"],
        "abst": "surface is a function-word/content homograph and POS is unresolved → route POS disambiguation, do not certify either root",
        "proj": {"condition": "surface is a closed-class function word (particle/pronoun/relative/demonstrative/interrogative) AND a content root is asserted by join",
                 "projection": "strip the join-inherited root; label ر∅ حرف / اسم مبني rootless; reject the row from the root-evidence lane before MCP spend",
                 "guards": ["deterministic closed-class lexicon (finite list)", "join-provenance detection", "aya-position independence"],
                 "scope": "surface-match"},
        "rels": [("extends", "sarf-surface-join-never-certifies-root", "registry",
                  "The closed-class guard is the negative-space partner of the per-occurrence join veto: some surfaces must NEVER acquire a root at all."),
                 ("cites", "sarf-norm-typed-rootless-rationale", "registry",
                  "Supplies the closed-class membership that the typed rootless rationale (function-word) enumerates.")],
        "fixtures": [
            {"fid": "inc23-sarf-closed-class-never-inherits-root-min-pos",
             "eid": "INC23-SARF_CLOSED_CLASS_NEVER_INHERITS_ROOT-MIN", "red": True,
             "loc": "2:6:1", "surfaces": ["من"],
             "case": {"surface_class": "particle_min", "join_root": "م ن ن", "is_closed_class": True},
             "correct": "rootless_harf_no_madda", "wrong": "certify_content_root",
             "cite": "particle من carried candidate root م ن ن laundered from the منّ entry; closed-class حرف has no مادة"},
            {"fid": "inc23-sarf-closed-class-never-inherits-root-la-pos",
             "eid": "INC23-SARF_CLOSED_CLASS_NEVER_INHERITS_ROOT-LA", "red": True,
             "loc": "2:2:2", "surfaces": ["لا"],
             "case": {"surface_class": "negation_la", "join_root": "أ ل ل", "is_closed_class": True},
             "correct": "rootless_harf_no_madda", "wrong": "certify_content_root",
             "cite": "negation لا carried candidate root أ ل ل / ب غ ي by surface join; حرف نفي is rootless"},
            {"fid": "inc23-sarf-closed-class-never-inherits-root-hum-pos",
             "eid": "INC23-SARF_CLOSED_CLASS_NEVER_INHERITS_ROOT-HUM", "red": True,
             "loc": "2:5:6", "surfaces": ["هم"],
             "case": {"surface_class": "pronoun_hum", "join_root": "ه م م", "is_closed_class": True},
             "correct": "rootless_ism_mabni_no_madda", "wrong": "certify_content_root",
             "cite": "pronoun هم carried candidate root ه م م from the همّ entry; ضمير is اسم مبني with no مادة"},
            {"fid": "inc23-sarf-closed-class-never-inherits-root-ctl",
             "eid": "INC23CTL-SARF_CLOSED_CLASS_NEVER_INHERITS_ROOT-MANNA", "red": False,
             "loc": "2:231:20", "surfaces": ["منّ"],
             "case": {"surface_class": "content_verb_homograph", "join_root": "م ن ن", "is_closed_class": False},
             "correct": "root_certified",
             "cite": "content verb مَنَّ 'bestowed' is a genuine م ن ن occurrence, NOT the particle — POS disambiguation lets the root stand (rule branches)"},
        ],
    },
    {
        "sid": "sarf-same-occurrence-cross-source-root-held", "skill": "sarf", "rule": "root_conflict_held",
        "fam": "root-source-conflict", "phen": "cross-source-root-disagreement-same-occurrence", "domain": "root", "clause": None,
        "readiness": "projector_ready",
        "scope": ("When two certified sources give DIFFERENT roots for the SAME occurrence and both are "
                  "defensible classical positions (اسمه 19:7:5 — MCP مادة س م و vs candidate س م ي; "
                  "ملائكة أ ل ك vs م ل ك), the occurrence routes to held/owner. Neither root is "
                  "majority-voted, neither is silently chosen, and normalization is applied first so w/y "
                  "romanization never false-alarms a conflict. The row is recorded with both candidate "
                  "roots and an engine-diverse 2-vote / owner gate."),
        "ev": [q("19:7:5"), q("66:6:12"), WAVE, CALIB],
        "defeaters": ["the two roots are identical after w/y and hamza-seat normalization (false alarm) → certify the agreed root",
                      "only one certified source is present → single-source candidate, not a conflict (do not manufacture a hold)"],
        "abst": "sources disagree post-normalization and both are classical → hold, route 2-vote/owner; never majority-vote a root",
        "proj": {"condition": "two certified source roots for the same occurrence differ after orthography normalization and both are classically defensible",
                 "projection": "hold; emit both candidate roots; route engine-diverse 2-vote / owner decision",
                 "guards": ["w/y→و/ي and hamza-seat normalization before compare", "never majority-vote", "owner-gate on classical tie"],
                 "scope": "root-match"},
        "rels": [("extends", "sarf-cross-source-root-conflict-no-majority-vote", "registry",
                  "Extends the ملائكة cross-source veto to the اسمه سمو-vs-سمي case measured in Window-1's W2-T1 lane.")],
        "fixtures": [
            {"fid": "inc23-sarf-same-occurrence-cross-source-root-held-pos",
             "eid": "INC23-SARF_SAME_OCCURRENCE_CROSS_SOURCE_ROOT_HELD-19_7_5", "red": True,
             "loc": "19:7:5", "surfaces": ["اسمه"],
             "case": {"root_source_a": "سمو", "root_source_b": "سمي", "classically_defensible_both": True},
             "correct": "hold_two_vote_owner_gate", "wrong": "silently_choose_or_majority",
             "cite": "19:7:5 اسمه — MCP مادة سمو vs candidate سمي, both classical positions for اسم; route held/owner, never pick one"},
            {"fid": "inc23-sarf-same-occurrence-cross-source-root-held-malaika-pos",
             "eid": "INC23-SARF_SAME_OCCURRENCE_CROSS_SOURCE_ROOT_HELD-66_6_12", "red": True,
             "loc": "66:6:12", "surfaces": ["ملائكة"],
             "case": {"root_source_a": "ألك", "root_source_b": "ملك", "classically_defensible_both": True},
             "correct": "hold_two_vote_owner_gate", "wrong": "silently_choose_or_majority",
             "cite": "66:6:12 ملائكة — MCP مادة أ ل ك vs QAC م ل ك, both classical; the archetype cross-source hold, never majority-voted"},
            {"fid": "inc23-sarf-same-occurrence-cross-source-root-held-ctl",
             "eid": "INC23CTL-SARF_SAME_OCCURRENCE_CROSS_SOURCE_ROOT_HELD-19_7_5", "red": False,
             "loc": "19:7:5", "surfaces": ["اسمه"],
             "case": {"root_source_a": "سمو", "root_source_b": "s m w", "classically_defensible_both": True},
             "correct": "certify_agreed_root",
             "cite": "same occurrence where the second source is w/y-romanized s m w — agrees with سمو after normalization, no conflict; certify (rule branches)"},
        ],
    },
    {
        "sid": "sarf-root-display-consistency-invariant", "skill": "sarf", "rule": "display_consistency",
        "fam": "root-display-consistency", "phen": "translit-root-field-null-mismatch", "domain": "norm", "clause": "N-ROOT-03",
        "readiness": "review_gated",
        "scope": ("A root asserted in learner-facing morphline prose (e.g. 'root q-w-l') MUST be backed "
                  "by the structured root field, and a populated structured root field MUST surface in "
                  "the prose — the two are one fact rendered twice and may never disagree. A "
                  "transliteration in prose is NOT itself a root assertion of record: 523 Window-1 rows "
                  "asserted 'root q-w-l'-style translit while the structured field was null and the hover "
                  "showed no root. Repair maps translit→Arabic مادة and backfills the field only after "
                  "per-occurrence certification (translit is a display artifact, not evidence)."),
        "ev": [q("2:9:1"), WAVE, NORM],
        "defeaters": ["prose and structured field carry the same مادة after translit normalization (conformant)",
                      "the prose transliteration is inside a quoted lexical example, not a root assertion of record (no مادة claim)"],
        "abst": "translit-prose root present but field null and certification not yet done → flag inconsistency and route certification; do not silently promote translit to the field",
        "proj": {"condition": "morphline prose asserts a transliterated root while the structured root field is null (or vice-versa)",
                 "projection": "flag N-ROOT-03 display-inconsistency; route field backfill through per-occurrence certification (never auto-promote translit prose to a certified field)",
                 "guards": ["deterministic translit→Arabic مادة mapping", "structured-field ↔ prose agreement check", "translit is not a certification tier"],
                 "scope": "occurrence-match"},
        "rels": [("extends", "sarf-norm-root-hedge-ban", "registry",
                  "Adds the display-consistency partner to the hedge ban: a root claimed in prose must exist in the field, and a field root must show in prose.")],
        "fixtures": [
            {"fid": "inc23-sarf-root-display-consistency-invariant-pos",
             "eid": "INC23-SARF_ROOT_DISPLAY_CONSISTENCY_INVARIANT-QWL_NULL", "red": True,
             "loc": "2:9:1", "surfaces": ["يقول"],
             "case": {"morphline_translit_root": "q-w-l", "structured_root_field": None, "hover_shows_root": False},
             "correct": "flag_display_inconsistency", "wrong": "conform",
             "cite": "morphline asserts 'root q-w-l' but structured root field is null and the hover shows nothing — 523-row family; display inconsistency"},
            {"fid": "inc23-sarf-root-display-consistency-invariant-reverse-pos",
             "eid": "INC23-SARF_ROOT_DISPLAY_CONSISTENCY_INVARIANT-KFR_PROSE_SILENT", "red": True,
             "loc": "36:70:4", "surfaces": ["الكافرين"],
             "case": {"morphline_translit_root": None, "structured_root_field": "ك ف ر", "hover_shows_root": True, "prose_asserts_root": False},
             "correct": "flag_display_inconsistency", "wrong": "conform",
             "cite": "reverse direction: structured field ك ف ر is populated (hover renders) but the morphline prose still says 'no public root asserted' — the field↔prose invariant is bidirectional"},
            {"fid": "inc23-sarf-root-display-consistency-invariant-ctl",
             "eid": "INC23CTL-SARF_ROOT_DISPLAY_CONSISTENCY_INVARIANT-QWL_BACKED", "red": False,
             "loc": "2:9:1", "surfaces": ["يقول"],
             "case": {"morphline_translit_root": "q-w-l", "structured_root_field": "ق و ل", "hover_shows_root": True},
             "correct": "conform",
             "cite": "same row after backfill: prose 'root q-w-l' and structured field ق و ل agree and the hover renders the root — conformant (rule branches)"},
        ],
    },
    # ================================ NAHW @2.3 — addressing + binding ================================
    {
        "sid": "nahw-basmala-aware-loc-authority", "skill": "nahw", "rule": "basmala_addr",
        "fam": "loc-authority-convention", "phen": "basmala-blind-address-false-out-of-range", "domain": "addressing", "clause": None,
        "readiness": "projector_ready",
        "scope": ("Loc-authority / address-range validation MUST be basmala-convention aware. On ayah-1 "
                  "of every surah except 1 and 9, the whitelist counts the basmala as words 1–4 and the "
                  "ayah text begins at word +4 (87:1:1–4 are the basmala; رَبِّكَ=word3+4=87:1:7). "
                  "QAC-derived ayah_wordcount authority is basmala-blind, so a validator that applies the "
                  "raw count emits FALSE out-of-range verdicts (3 certified rows — 17:1:22, 87:1:7, "
                  "96:1:7 — were wrongly held in W1 until cap+4 was applied). Entry-example cards use "
                  "phrase-relative numbering; :100+ are fragment pseudo-locs and are exempt from the "
                  "ayah-range check."),
        "ev": [q("87:1:7"), q("96:1:7"), q("17:1:22"), q("18:55:2"), q("40:84:1"), WAVE],
        "defeaters": ["surah is 1 (basmala IS ayah 1) or 9 (no basmala) → no +4 offset",
                      "word-index exceeds even authority+4 → a genuine out-of-range address, correctly held (offset does not absolve real overflow)"],
        "abst": "ayah-1 loc on a basmala-carrying surah exceeds the raw count but not authority+4 → do not hold; certify addressing and continue",
        "proj": {"condition": "loc word-index on ayah-1 of a basmala-carrying surah (not 1 or 9) exceeds the basmala-blind ayah_wordcount authority",
                 "projection": "apply the +4 basmala band before the range verdict; do NOT hold as out-of-range when word-index ≤ authority+4",
                 "guards": ["surah∈{1,9} exemption", "cap+4 on ayah-1 of basmala-carrying surahs", "phrase-relative numbering for entry-example cards", ":100+ fragment pseudo-loc exemption"],
                 "scope": "construction-match"},
        "rels": [("extends", "ONH-B5", "registry",
                  "A positional/addressing convention gate feeding the certification lane; sits upstream of root and gloss checks.")],
        "fixtures": [
            {"fid": "inc23-nahw-basmala-aware-loc-authority-pos",
             "eid": "INC23-NAHW_BASMALA_AWARE_LOC_AUTHORITY-87_1_7", "red": True,
             "loc": "87:1:7", "surfaces": ["ربك"],
             "case": {"surah_has_basmala": True, "raw_ayah_wordcount": 5, "loc_word_index": 7, "within_authority_plus4": True},
             "correct": "certify_address_basmala_offset", "wrong": "hold_out_of_range",
             "cite": "87:1:7 رَبِّكَ = ayah-word3 + 4 basmala words; raw count 5 flags it out-of-range but cap+4 makes it valid"},
            {"fid": "inc23-nahw-basmala-aware-loc-authority-96-pos",
             "eid": "INC23-NAHW_BASMALA_AWARE_LOC_AUTHORITY-96_1_7", "red": True,
             "loc": "96:1:7", "surfaces": ["ربك"],
             "case": {"surah_has_basmala": True, "raw_ayah_wordcount": 3, "loc_word_index": 7, "within_authority_plus4": True},
             "correct": "certify_address_basmala_offset", "wrong": "hold_out_of_range",
             "cite": "96:1:7 رَبِّكَ = ayah-word3 + 4 basmala words; basmala-blind count 3 falsely rejects it — one of the 3 certified rows wrongly held in W1"},
            {"fid": "inc23-nahw-basmala-aware-loc-authority-overflow-ctl",
             "eid": "INC23CTL-NAHW_BASMALA_AWARE_LOC_AUTHORITY-87_1_20", "red": False,
             "loc": "87:1:20", "surfaces": ["<none>"],
             "case": {"surah_has_basmala": True, "raw_ayah_wordcount": 5, "loc_word_index": 20, "within_authority_plus4": False},
             "correct": "hold_out_of_range",
             "cite": "a fabricated 87:1:20 exceeds even authority+4 (5+4=9) — a genuine overflow; still correctly held (offset does not absolve it)"},
            {"fid": "inc23-nahw-basmala-aware-loc-authority-surah9-ctl",
             "eid": "INC23CTL-NAHW_BASMALA_AWARE_LOC_AUTHORITY-9_1_5", "red": False,
             "loc": "9:1:5", "surfaces": ["ورسوله"],
             "case": {"surah_has_basmala": False, "raw_ayah_wordcount": 8, "loc_word_index": 5, "within_authority_plus4": True},
             "correct": "certify_no_offset",
             "cite": "surah 9 carries NO basmala — the +4 offset must NOT apply; the raw authority governs directly (exemption defeater)"},
        ],
    },
    {
        "sid": "nahw-surface-gloss-single-wordlist-binding", "skill": "nahw", "rule": "surface_gloss_bind",
        "fam": "surface-gloss-binding", "phen": "surface-gloss-index-skew-binding-corruption", "domain": "binding", "clause": None,
        "readiness": "projector_ready",
        "scope": ("Every row's gloss MUST translate ITS OWN surface: surface and gloss must be resolved "
                  "from ONE word list under ONE indexing convention. Window-1 found 8 corrupt rows where "
                  "the surface was resolved with basmala-INCLUSIVE indexing while the gloss was resolved "
                  "basmala-BLIND at the same numeric index, smearing meanings across tokens (96:1:2 "
                  "ٱللَّهِ glossed 'the name'; 96:1:5 ٱقْرَأْ glossed 'He created'; 54:1:2/4/7 'the "
                  "moon'/'the Hour' smear; 57:1:6; 76:1:6 مِّنَ glossed 'who'). A gloss that describes a "
                  "different token than its surface is a binding defect, not a translation choice."),
        "ev": [q("96:1:2"), q("96:1:5"), q("54:1:2"), q("76:1:6"), q("57:1:6"), WAVE],
        "defeaters": ["gloss lexically corresponds to its own surface (agreement probe passes) — a valid translation, not a skew",
                      "surface and gloss were provably resolved from the same word list at the same convention (parity attested) → no defect even if the gloss is a debatable rendering"],
        "abst": "surface↔gloss lexical agreement cannot be probed (missing lexicon) → hold the row, do not publish an unverified binding",
        "proj": {"condition": "the gloss's lexical content matches a NEIGHBORING word list index rather than the row's own surface (off-by-basmala index skew)",
                 "projection": "flag surface↔gloss binding corruption; re-resolve gloss against the surface's own index; block publish until they agree",
                 "guards": ["single word-list resolution for surface and gloss", "surface↔gloss lexical-agreement probe", "basmala-index parity between the two fields"],
                 "scope": "occurrence-match"},
        "rels": [("extends", "nahw-basmala-aware-loc-authority", "registry",
                  "Consumes the basmala addressing convention: a mismatched basmala index is exactly what desynchronizes surface and gloss.")],
        "fixtures": [
            {"fid": "inc23-nahw-surface-gloss-single-wordlist-binding-allah-pos",
             "eid": "INC23-NAHW_SURFACE_GLOSS_SINGLE_WORDLIST_BINDING-96_1_2", "red": True,
             "loc": "96:1:2", "surfaces": ["الله"],
             "case": {"surface": "ٱللَّهِ", "gloss": "the name", "surface_index_basmala": "inclusive", "gloss_index_basmala": "blind"},
             "correct": "flag_binding_corruption", "wrong": "publish_row",
             "cite": "96:1:2 surface ٱللَّهِ (basmala-inclusive) glossed 'the name' resolved basmala-blind at the same index — gloss describes a neighbor"},
            {"fid": "inc23-nahw-surface-gloss-single-wordlist-binding-iqra-pos",
             "eid": "INC23-NAHW_SURFACE_GLOSS_SINGLE_WORDLIST_BINDING-96_1_5", "red": True,
             "loc": "96:1:5", "surfaces": ["اقرأ"],
             "case": {"surface": "ٱقْرَأْ", "gloss": "He created", "surface_index_basmala": "inclusive", "gloss_index_basmala": "blind"},
             "correct": "flag_binding_corruption", "wrong": "publish_row",
             "cite": "96:1:5 surface ٱقْرَأْ 'read!' glossed 'He created' (خلق) — the gloss belongs to a different token; index-skew smear"},
            {"fid": "inc23-nahw-surface-gloss-single-wordlist-binding-ctl",
             "eid": "INC23CTL-NAHW_SURFACE_GLOSS_SINGLE_WORDLIST_BINDING-96_1_1", "red": False,
             "loc": "96:1:1", "surfaces": ["اقرأ"],
             "case": {"surface": "ٱقْرَأْ", "gloss": "Read!", "surface_index_basmala": "inclusive", "gloss_index_basmala": "inclusive"},
             "correct": "publish_row",
             "cite": "96:1:1 surface and gloss both resolved from the same basmala-inclusive list — ٱقْرَأْ↔'Read!' agree; conformant (rule branches)"},
        ],
    },
    # ================================ SARF @2.3 — norm + matching =====================================
    {
        "sid": "sarf-every-segment-carries-gloss", "skill": "sarf", "rule": "segment_gloss",
        "fam": "segment-gloss-completeness", "phen": "empty-segment-gloss-npedleak", "domain": "norm", "clause": "N-PED-01",
        "readiness": "projector_ready",
        "scope": ("Every rendered segment MUST carry a non-empty gloss_contribution; a certified split "
                  "packet that adds segments with empty gloss is nonconformant. Window-1's C5-homograph "
                  "packet added 269 pronoun segments with empty gloss_contribution and the old seam "
                  "accepted them (N-PED-01 leak — the seam gate does not check segment glosses). "
                  "Closed-class pronoun suffixes have a DETERMINISTIC gloss table keyed by role and "
                  "suffix (ه=him/it, ها=her/it, هم=them, كم=you[pl], نا=us, ي=my, ك=you[sg]); "
                  "role-ambiguous suffix_pronoun rows stay pending rather than guess."),
        "ev": [q("96:1:1"), WAVE, NORM],
        "defeaters": ["the segment already carries a non-empty gloss_contribution (conformant)",
                      "the suffix is a role-ambiguous suffix_pronoun (subject-vs-object undetermined) → legitimately pending, not an empty-gloss defect"],
        "abst": "segment gloss empty and the suffix role is ambiguous → pending; never emit an empty gloss and never guess the role",
        "proj": {"condition": "a rendered segment (esp. a pronoun suffix from a split packet) has empty gloss_contribution",
                 "projection": "flag N-PED-01 empty-segment-gloss; fill from the deterministic suffix table where role is determinate; hold role-ambiguous suffixes",
                 "guards": ["segment-level gloss presence check (not row-level)", "deterministic closed-class suffix gloss table by role", "role-ambiguous suffix_pronoun → pending not guess"],
                 "scope": "surface-match"},
        "rels": [("extends", "sarf-completeness-claim-requires-asserted-facts", "registry",
                  "Closes the N-PED-01 seam gap the W1-G cycle patched (421 rows filled); segments, not rows, are the unit of gloss completeness.")],
        "fixtures": [
            {"fid": "inc23-sarf-every-segment-carries-gloss-hum-pos",
             "eid": "INC23-SARF_EVERY_SEGMENT_CARRIES_GLOSS-PRONOUN_HUM_EMPTY", "red": True,
             "loc": "40:84:1", "surfaces": ["هم"],
             "case": {"segment_type": "pronoun_suffix", "suffix": "هم", "role": "object_determinate", "gloss_contribution": ""},
             "correct": "fill_from_suffix_table", "wrong": "accept_empty_gloss",
             "cite": "a certified split added the object suffix هم with empty gloss_contribution; deterministic table → 'them', seam must not accept empty"},
            {"fid": "inc23-sarf-every-segment-carries-gloss-kum-pos",
             "eid": "INC23-SARF_EVERY_SEGMENT_CARRIES_GLOSS-PRONOUN_KUM_EMPTY", "red": True,
             "loc": "2:284:1", "surfaces": ["كم"],
             "case": {"segment_type": "pronoun_suffix", "suffix": "كم", "role": "genitive_possessive_determinate", "gloss_contribution": ""},
             "correct": "fill_from_suffix_table", "wrong": "accept_empty_gloss",
             "cite": "another packet split added the possessive suffix كم with empty gloss; deterministic table → 'your(pl.)/you(pl.)' by role — different table row, same defect"},
            {"fid": "inc23-sarf-every-segment-carries-gloss-ctl",
             "eid": "INC23CTL-SARF_EVERY_SEGMENT_CARRIES_GLOSS-ROLE_AMBIGUOUS", "red": False,
             "loc": "2:282:11", "surfaces": ["ه"],
             "case": {"segment_type": "suffix_pronoun", "suffix": "ه", "role": "ambiguous_subject_object", "gloss_contribution": ""},
             "correct": "hold_pending_role",
             "cite": "a role-ambiguous suffix_pronoun ه (subject-vs-object undetermined) legitimately stays pending — NOT an empty-gloss defect (rule branches)"},
        ],
    },
    {
        "sid": "sarf-orthographic-match-symmetry", "skill": "sarf", "rule": "match_symmetry",
        "fam": "orthographic-match-symmetry", "phen": "asymmetric-normalization-no-match", "domain": "matching", "clause": None,
        "readiness": "projector_ready",
        "scope": ("Corpus word matching MUST normalize BOTH the candidate surface and the corpus surface "
                  "with the SAME function before comparing, and MUST refuse a fold that would make two "
                  "DISTINCT raw words share a normalized key. Window-1 lost 50 candidates to asymmetric "
                  "matching — one side normalizer-stripped, the other raw (فحياكم vs فأحياكم failed to "
                  "match because only one side had its hamza folded). But naive both-sides folding is not "
                  "free: hamza/alif and ة/ه folds can collapse لا/إلا and distinct pairs into one key, so "
                  "an ambiguous fold (two distinct raw words mapping to the same key) must BLOCK the match "
                  "rather than resolve it arbitrarily."),
        "ev": [q("2:28:6"), WAVE, CALIB],
        "defeaters": ["both sides are already normalized by the same function and the keys are unambiguous → a clean match, no re-run needed",
                      "the two raw words are genuinely the same lexeme (the fold is meaning-preserving, e.g. optional-hamza spelling variants) → the shared key is correct, not ambiguous"],
        "abst": "a fold maps two distinct raw words to one key → block the match and route disambiguation; never arbitrarily pick one",
        "proj": {"condition": "candidate↔corpus match where one side is normalized and the other raw, OR a fold maps two distinct raw words to the same key",
                 "projection": "re-run the match with symmetric normalization; on an ambiguous fold, refuse the match and route disambiguation (never arbitrary pick)",
                 "guards": ["single shared normalizer applied to BOTH sides", "hamza-seat + alif + ة/ه aware folding", "ambiguous-fold detector (distinct raw words sharing a key → block)"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf-cross-source-root-conflict-no-majority-vote", "registry",
                  "Recovers the tranche-2 no_match backlog while guarding the لا/إلا collision the naive folder would introduce.")],
        "fixtures": [
            {"fid": "inc23-sarf-orthographic-match-symmetry-hamza-pos",
             "eid": "INC23-SARF_ORTHOGRAPHIC_MATCH_SYMMETRY-FAHYAKUM", "red": True,
             "loc": "2:28:6", "surfaces": ["فحياكم", "فأحياكم"],
             "case": {"candidate_side": "فحياكم", "corpus_side": "فأحياكم", "candidate_normalized": True, "corpus_normalized": False},
             "correct": "match_after_symmetric_normalization", "wrong": "no_match",
             "cite": "فحياكم (hamza-stripped) vs raw فأحياكم failed because only one side was folded; symmetric normalization matches them"},
            {"fid": "inc23-sarf-orthographic-match-symmetry-alif-pos",
             "eid": "INC23-SARF_ORTHOGRAPHIC_MATCH_SYMMETRY-SALAT", "red": True,
             "loc": "2:3:5", "surfaces": ["الصلوة", "الصلاة"],
             "case": {"candidate_side": "الصلوة", "corpus_side": "الصلاة", "candidate_normalized": False, "corpus_normalized": True},
             "correct": "match_after_symmetric_normalization", "wrong": "no_match",
             "cite": "الصلوة (raw alif-wāw orthography) vs corpus-normalized الصلاة failed on a one-sided ة/alif fold; symmetric normalization recovers the match — a distinct fold axis from hamza"},
            {"fid": "inc23-sarf-orthographic-match-symmetry-ctl",
             "eid": "INC23CTL-SARF_ORTHOGRAPHIC_MATCH_SYMMETRY-LA_ILLA", "red": False,
             "loc": "2:255:9", "surfaces": ["لا", "إلا"],
             "case": {"candidate_side": "لا", "corpus_side": "إلا", "candidate_normalized": True, "corpus_normalized": True},
             "correct": "block_ambiguous_fold", "wrong": "match_after_symmetric_normalization",
             "cite": "naive hamza/alif folding collapses distinct لا and إلا to one key — an ambiguous fold; must BLOCK, not match (rule branches)"},
        ],
    },
]


def build_registry_rows():
    rows = []
    for r in RULES:
        sid = r["sid"]
        sk = r["skill"]
        pos_ex = [f["eid"] for f in r["fixtures"] if f["red"]]
        ctl_ex = [f["eid"] for f in r["fixtures"] if not f["red"]]
        rels = [{"type": t, "target_id": tid, "target_kind": kind, "note": note}
                for (t, tid, kind, note) in r["rels"]]
        proj = {"readiness": r["readiness"]}
        proj.update(r["proj"])
        provenance = {
            "origin": "increment-23-window1-flywheel",
            "cycle": "2026-07-16",
            "source": SKEV,
            "projector_readiness": r["readiness"],
            "phenomenon": r["phen"],
            "domain": r["domain"],
        }
        if r["clause"] is not None:
            provenance["clause"] = r["clause"]
        row = {
            "skill_rule_id": sid,
            "skill": sk,
            "skill_version": sk + "@2.3",
            "status": "candidate",
            "fact_family": r["fam"],
            "scope": r["scope"],
            "evidence_addresses": r["ev"],
            "positive_examples": pos_ex,
            "negative_or_boundary_examples": ctl_ex,
            "defeaters": r["defeaters"],
            "abstention_condition": r["abst"],
            "gate": "@2.3-candidate:redfirst+window1-measured",
            "code_references": ["tools/skill_fixtures/skill_rules_increment23.py"],
            "test_references": ["tools/skill_fixtures/test_skill_fixtures_increment23.py"],
            "relationships": rels,
            "provenance": provenance,
            "projector": proj,
        }
        rows.append(row)
    return rows


def build_fixture_rows():
    fixtures = []
    for r in RULES:
        emit_domain = (r["domain"] == "norm")
        for f in r["fixtures"]:
            fx = {
                "fixture_id": f["fid"],
                "example_id": f["eid"],
                "rule_id": r["sid"],
                "rule": r["rule"],
                "skill_version": r["skill"] + "@2.3",
                "phenomenon": r["phen"],
                "canonical_locations": [f["loc"]],
                "surfaces": f.get("surfaces", []),
                "case": f["case"],
                "correct_label": f["correct"],
                "redfirst": f["red"],
                "citation": f["cite"],
            }
            if emit_domain:
                fx["domain"] = r["domain"]
            if "wrong" in f:
                fx["wrong_label"] = f["wrong"]
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
            drift.append("rule-registry-increment-23.jsonl")
        if _read(FIXTURES_OUT) != fx_body:
            drift.append("skill_fixtures_increment23.jsonl")
        if drift:
            print("DRIFT (regenerate via _build_increment23.py): " + ", ".join(drift))
            return 1
        print("increment-23 builder: committed artifacts match regeneration (%d rules, %d fixtures)"
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
