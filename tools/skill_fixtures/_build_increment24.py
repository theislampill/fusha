#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic builder for the INCREMENT-24 (sarf@2.4 / nahw@2.4 candidate) rows + fixtures.

P00-vertical-slice pilot dogfood input (2026-07-29): the first complete source-grounded particle
family — the p007 jarr clitic لِـ (entry b10a1ee04666, sense 2) on noun hosts, 12 canonical
occurrences taken discovery → evidence → independent two-vote → fact-level certification →
two-surface projection → live reverse-check — plus the two-vote canary run (tajarrud contract
lesson) and the particle-denominator calibration (S7 blanket-stripper precision 16.7%), distilled
into 9 candidate @2.4 rules: 5 sarf (لِ+kasra host routing, lexical-initial-lām guard,
pronoun-host guard, fused لِلَّهِ exact letter ownership, NFC span parity) and 4 nahw
(preposition-governs-majrūr governor, khabar-muqaddam two-notations-one-analysis, tajarrud mood
basis, lām typing by host POS). Companion to skill_rules.py + skill_rules_richseg.py +
skill_rules_increment21/22/23.py, kept SEPARATE so it does not collide with the released @2 /
candidate @2.1–@2.3 fixtures; it merges alongside them at the @2.4 release.

Single source of two committed artifacts, emitted byte-deterministically (sorted keys, LF,
trailing newline) so re-running is a no-op:
  * qamus/skills/rule-registry-increment-24.jsonl        — candidate registry rows (schema-conformant)
  * tools/skill_fixtures/skill_fixtures_increment24.jsonl — red-first + branch-control fixtures

Every rule carries: source-addressed evidence, >=1 positive (red-first) example, a
boundary/control example that proves the corrected discriminator BRANCHES (non-constant),
defeaters, an abstention condition, a `projector` sketch, and a provenance `domain` tag
(`segmentation` / `normalization` / `government` / `function`).

Run:  python tools/skill_fixtures/_build_increment24.py            # write both files
      python tools/skill_fixtures/_build_increment24.py --check    # verify committed == regenerated
Stdlib only, deterministic, no network. RM-09: repo-relative evidence anchors only (no server
paths, hosts, or IPs).
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REGISTRY_OUT = os.path.join(REPO, "qamus", "skills", "rule-registry-increment-24.jsonl")
FIXTURES_OUT = os.path.join(HERE, "skill_fixtures_increment24.jsonl")

# Evidence anchors (all repo-relative so the addresses resolve; RM-09: no server paths, hosts, or
# IP literals). The pilot packet itself lives outside this repo; SKEV summarizes it in-repo.
SKEV = "impl-records/skill-evolution/INCREMENT-24-NOTES.md"
CONTRACT = "docs/qamus/particle-projection-contract.md"
MATRIX = "qamus/lattice/particle-occurrence-matrix.jsonl"
PFREG = "qamus/skills/particle-function-registry.jsonl"


def q(loc):
    return "quran:" + loc


# NFC fixture surfaces: same base letters, combining marks in the two observed codepoint orders
# (repo matrix stores vowel-before-shadda; the live whitelist stores shadda-before-vowel; both are
# canonically equivalent — Unicode ccc reorders kasra/fatha(30-32) before shadda(33) under NFC).
_LAM_KASRA_SHADDA = "لِّ"   # lam + kasra + shadda
_LAM_SHADDA_KASRA = "لِّ"   # lam + shadda + kasra (NFC-equivalent to the above)
_NAS_FATHA_SHADDA = "نَّاسِ"  # host span with fatha-before-shadda
_NAS_SHADDA_FATHA = "نَّاسِ"  # host span with shadda-before-fatha
_HOST_WITH_ARTICLE_LAM = "لنَّاسِ"  # article lam folded into the host span

RULES = [
    # ================================ SARF @2.4 — لِ clitic/host segmentation ========================
    {
        "sid": "sarf-li-kasra-noun-host-clitic-carve", "skill": "sarf", "rule": "li_clitic_carve",
        "fam": "clitic-host-segmentation", "phen": "li-kasra-prefix-family-routing",
        "domain": "segmentation", "readiness": "projector_ready",
        "scope": ("A strict لِ+kasra prefix candidate is a jarr-clitic carve ONLY over a nominal "
                  "host; the surface shape alone never decides. A lexical initial lām that is the "
                  "host's root radical (لِبَاسٌ, wazn فِعَال, مادة ل ب س, iʿrāb has no jarr clause) "
                  "REJECTS the carve; a pronoun host (لِى) is a genuine jarr particle but belongs "
                  "to the pronoun-host family, outside the noun-host lane; a muḍāriʿ host "
                  "(لِيَغِيظَ, manṣūb بأن مضمرة) routes to the lām-taʿlīl rival for nahw typing. "
                  "The particle-denominator calibration measured the blanket لِ stripper stratum "
                  "(S7 lexical-initial-radical hosts) at 16.7% precision — host routing is the "
                  "fix, and the P00 pilot's 3 rejected false candidates prove the guard classes."),
        "ev": [q("2:34:3"), q("2:187:9"), q("48:29:42"), q("31:14:14"), MATRIX, SKEV],
        "defeaters": ["the host after the strip is an attested nominal and no lexical-lam/pronoun/verb guard fires → the carve stands as a candidate (per-occurrence evidence still required to certify)",
                      "the surface is a whole-word particle (لَا/لَنْ/لَدَى families) — no carve at all, route the whole-token reading"],
        "abst": "host POS unresolved (unvoweled/ambiguous) → keep every rival reading on the lattice; never force the carve",
        "proj": {"condition": "strict لِ+kasra prefix candidate on a token whose host is not yet classified",
                 "projection": "route by host: nominal → jarr-clitic carve candidate; lexical-initial-lām → reject; pronoun → pronoun-host family; muḍāriʿ → lām-taʿlīl rival",
                 "guards": ["host-POS classification before carve", "مادة-initial-radical check", "pronoun closed-class check", "rivals preserved on the candidate lattice"],
                 "scope": "surface-match"},
        "rels": [("extends", "sarf-root-radical-not-clitic", "registry",
                  "Generalizes the root-radical clitic veto to the لِ family with measured stratum precision and the pilot's three rejected false candidates."),
                 ("cites", "nahw-lam-prefix-typology", "registry",
                  "The verb-host branch hands the lām to nahw for taʿlīl/amr typing; sarf only segments.")],
        "fixtures": [
            {"fid": "inc24-sarf-li-kasra-noun-host-clitic-carve-libas-pos",
             "eid": "INC24-SARF_LI_KASRA_NOUN_HOST_CLITIC_CARVE-2_187_9", "red": True,
             "loc": "2:187:9", "surfaces": ["لباس"],
             "case": {"lexical_lam_root_initial": True, "host_pos": "noun", "prefix": "لِ"},
             "correct": "reject_carve_lexical_initial_lam", "wrong": "carve_jarr_clitic_noun_host",
             "cite": "2:187:9 لِبَاسٌ — the initial lām is the root radical of ل ب س (wazn فِعَال); the blanket stripper carved it as jarr+باس; carve rejected"},
            {"fid": "inc24-sarf-li-kasra-noun-host-clitic-carve-yaghiza-pos",
             "eid": "INC24-SARF_LI_KASRA_NOUN_HOST_CLITIC_CARVE-48_29_42", "red": True,
             "loc": "48:29:42", "surfaces": ["ليغيظ"],
             "case": {"lexical_lam_root_initial": False, "host_pos": "verb_mudari_mansub", "prefix": "لِ"},
             "correct": "route_lam_talil_rival", "wrong": "carve_jarr_clitic_noun_host",
             "cite": "48:29:42 لِيَغِيظَ — genuine particle, wrong family: the host is a muḍāriʿ manṣūb بأن مضمرة (lām-taʿlīl), not a noun in jarr"},
            {"fid": "inc24-sarf-li-kasra-noun-host-clitic-carve-li-pos",
             "eid": "INC24-SARF_LI_KASRA_NOUN_HOST_CLITIC_CARVE-31_14_14", "red": True,
             "loc": "31:14:14", "surfaces": ["لى"],
             "case": {"lexical_lam_root_initial": False, "host_pos": "pronoun", "prefix": "لِ"},
             "correct": "route_pronoun_host_outside_noun_family", "wrong": "carve_jarr_clitic_noun_host",
             "cite": "31:14:14 لِى — jarr lām + 1cs pronoun host; genuine preposition, but the pronoun-host family, never the noun-host lane"},
            {"fid": "inc24-sarf-li-kasra-noun-host-clitic-carve-ctl",
             "eid": "INC24CTL-SARF_LI_KASRA_NOUN_HOST_CLITIC_CARVE-2_34_3", "red": False,
             "loc": "2:34:3", "surfaces": ["للملائكة"],
             "case": {"lexical_lam_root_initial": False, "host_pos": "noun", "prefix": "لِ"},
             "correct": "carve_jarr_clitic_noun_host",
             "cite": "2:34:3 لِلْمَلَٰٓئِكَةِ — nominal host, no guard fires: the jarr-clitic carve candidate stands (rule branches)"},
        ],
    },
    {
        "sid": "sarf-lexical-initial-lam-madda-guard", "skill": "sarf", "rule": "lexical_lam_guard",
        "fam": "clitic-host-segmentation", "phen": "lexical-initial-lam-false-carve",
        "domain": "segmentation", "readiness": "projector_ready",
        "scope": ("When a candidate clitic lām is in fact the host's initial root radical (the "
                  "مادة begins with ل and the per-occurrence iʿrāb attests no jarr clause), the "
                  "carve is a false split and is rejected — لِبَاسٌ is one noun of مادة ل ب س, not "
                  "لِ + باس. The mirror case is REAL: a jarr lām can sit over a lexical-lām-initial "
                  "host (لِّلَّذِينَ), confirmed only when the per-occurrence iʿrāb attests the jarr "
                  "clause. Shape can never decide; the مادة + iʿrāb pair does."),
        "ev": [q("2:187:9"), q("10:26:1"), MATRIX, SKEV],
        "defeaters": ["the per-occurrence iʿrāb attests a jarr clause over the lexical-lām-initial host → the carve is confirmed (لِّلَّذِينَ)",
                      "the مادة does not begin with ل → this guard is silent; other guards may still apply"],
        "abst": "مادة unavailable for the host → hold the carve as unverified; never certify from surface shape",
        "proj": {"condition": "candidate clitic lām over a host whose مادة begins with ل",
                 "projection": "reject the carve unless the per-occurrence iʿrāb attests the jarr clause; record the lexical reading as the retained rival",
                 "guards": ["مادة-initial check", "per-occurrence iʿrāb jarr-clause confirmation", "rival retained on rejection"],
                 "scope": "root-match"},
        "rels": [("extends", "sarf-root-radical-not-clitic", "registry",
                  "Instantiates the radical-not-clitic veto for the lām letter with the iʿrāb-confirmation escape hatch.")],
        "fixtures": [
            {"fid": "inc24-sarf-lexical-initial-lam-madda-guard-pos",
             "eid": "INC24-SARF_LEXICAL_INITIAL_LAM_MADDA_GUARD-2_187_9", "red": True,
             "loc": "2:187:9", "surfaces": ["لباس"],
             "case": {"madda_initial": "ل", "irab_attests_jarr_clause": False},
             "correct": "reject_carve_root_radical_lam", "wrong": "carve_allowed_shape_only",
             "cite": "2:187:9 لِبَاسٌ — مادة ل ب س, iʿrāb shows a khabar noun with no jarr clause; the shape-only stripper allowed the carve"},
            {"fid": "inc24-sarf-lexical-initial-lam-madda-guard-alladhina-ctl",
             "eid": "INC24CTL-SARF_LEXICAL_INITIAL_LAM_MADDA_GUARD-10_26_1", "red": False,
             "loc": "10:26:1", "surfaces": ["للذين"],
             "case": {"madda_initial": "ل", "irab_attests_jarr_clause": True},
             "correct": "carve_confirmed_by_irab",
             "cite": "10:26:1 لِّلَّذِينَ — jarr lām over the lexical-lām-initial relative ٱلَّذِينَ; the per-occurrence iʿrāb attests the jarr clause, so the carve is confirmed (rule branches)"},
            {"fid": "inc24-sarf-lexical-initial-lam-madda-guard-nas-ctl",
             "eid": "INC24CTL-SARF_LEXICAL_INITIAL_LAM_MADDA_GUARD-24_35_44", "red": False,
             "loc": "24:35:44", "surfaces": ["للناس"],
             "case": {"madda_initial": "ن", "irab_attests_jarr_clause": True},
             "correct": "carve_allowed_lam_not_radical",
             "cite": "24:35:44 لِلنَّاسِ — host مادة ن و س does not begin with lām; the guard is silent and the carve proceeds on the ordinary path"},
        ],
    },
    {
        "sid": "sarf-li-pronoun-host-outside-noun-family", "skill": "sarf", "rule": "pronoun_host_guard",
        "fam": "clitic-host-segmentation", "phen": "pronoun-host-family-misclassification",
        "domain": "segmentation", "readiness": "projector_ready",
        "scope": ("لِ + pronoun (لِى, لَهُ family) is a genuine jarr preposition whose host is a "
                  "mabnī pronoun: BOTH pieces are rootless (حرف + ضمير — the MCP ṣarf for the "
                  "pilot's لِى reads (اللَّامُ): حَرْفٌ مَبْنِيٌّ), the row belongs to the "
                  "pronoun-host family, and no noun-host projection template, root field, or "
                  "noun-host reason key may be applied to it. A noun host whose muḍāf-ilayh is a "
                  "pronoun (لِقَوْمِهِۦ, لِقُلُوبِكُمْ) is still a NOUN host: the pronoun sits "
                  "inside the host phrase as muḍāf-ilayh, not as the governed host."),
        "ev": [q("31:14:14"), q("61:5:4"), q("33:53:48"), MATRIX, SKEV],
        "defeaters": ["the pronoun is muḍāf-ilayh inside a nominal host (لِقَوْمِهِۦ) → noun-host family; the guard reads the GOVERNED host, not any pronoun in the token",
                      "the token is a fused closed-class preposition+pronoun already on the function-word floor (فيها/عليكم) → affirm there, no family routing needed"],
        "abst": "governed-host class unresolved → hold family assignment; never default to the noun-host lane",
        "proj": {"condition": "jarr lām whose governed host is a mabnī pronoun",
                 "projection": "assign the pronoun-host family; mark both segments rootless (function_only_no_root); block noun-host templates and noun-host reason keys",
                 "guards": ["governed-host (not token-internal pronoun) classification", "typed rootless rationale on both segments", "family lanes kept disjoint"],
                 "scope": "surface-match"},
        "rels": [("cites", "nahw-fused-preposition-closed-class-floor", "registry",
                  "The fused jarr+pronoun inventory affirms on the function-word floor; this rule keeps its FAMILY disjoint from noun hosts."),
                 ("cites", "sarf-closed-class-never-inherits-root", "registry",
                  "Supplies the rootless typing for both segments of the pronoun-host row.")],
        "fixtures": [
            {"fid": "inc24-sarf-li-pronoun-host-outside-noun-family-pos",
             "eid": "INC24-SARF_LI_PRONOUN_HOST_OUTSIDE_NOUN_FAMILY-31_14_14", "red": True,
             "loc": "31:14:14", "surfaces": ["لى"],
             "case": {"host_class": "pronoun", "prefix": "لِ"},
             "correct": "jarr_pronoun_host_family_rootless", "wrong": "jarr_noun_host_family",
             "cite": "31:14:14 لِى — the governed host is the 1cs pronoun; the family classifier lumped it into the noun-host lane"},
            {"fid": "inc24-sarf-li-pronoun-host-outside-noun-family-ctl",
             "eid": "INC24CTL-SARF_LI_PRONOUN_HOST_OUTSIDE_NOUN_FAMILY-61_5_4", "red": False,
             "loc": "61:5:4", "surfaces": ["لقومه"],
             "case": {"host_class": "noun", "prefix": "لِ", "mudaf_ilayh": "pronoun"},
             "correct": "jarr_noun_host_family",
             "cite": "61:5:4 لِقَوْمِهِۦ — the governed host is the noun قوم; the ـهِ is muḍāf-ilayh inside the host phrase, so the row stays in the noun-host family (rule branches)"},
        ],
    },
    {
        "sid": "sarf-fused-lil-exact-letter-ownership", "skill": "sarf", "rule": "fused_lil_carve",
        "fam": "clitic-host-segmentation", "phen": "fused-lillahi-assimilated-article-carve-fork",
        "domain": "segmentation", "readiness": "projector_ready",
        "scope": ("The carve of لِ + ال-host is decided by the WRITTEN form, exactly once per "
                  "occurrence surface, with exact base-letter span ownership: in the fused rasm "
                  "لِلَّهِ (article alif elided, writing fused with the Name) the clitic owns "
                  "precisely its own lām+kasra and the fused writing of the Name owns the rest "
                  "(لِ ∣ لَّهِ); where the assimilated article's lām is written (لِلنَّاسِ، "
                  "لِلْمَلَٰٓئِكَةِ) it gets its own span (لِ ∣ ل ∣ host); a bare noun host carves "
                  "two spans (لِ ∣ غَيْرِ). Spans concatenate byte-exact; each base letter carries "
                  "its own trailing combining marks; the SAME surface must carve the SAME way at "
                  "every occurrence (the live plane carved للناس two different ways at its two "
                  "occurrences — the per-surface fork the projection contract kills)."),
        "ev": [q("12:31:24"), q("24:35:44"), q("2:187:63"), q("5:3:9"), CONTRACT, SKEV],
        "defeaters": ["the written form differs between occurrences of the same underlying phrase (rasm variation) → carve follows each occurrence's own written form; parity is per-surface, not per-phrase",
                      "the article is lexicalized/fossilized into the host entry (اللَّه، ٱلَّذِينَ) → no productive article span; the fusion note teaches it"],
        "abst": "written-form class (fused vs written-article) unestablished for the occurrence → hold the carve; never copy a carve from a different surface",
        "proj": {"condition": "لِ clitic over an ال-bearing host (fused or written assimilated article)",
                 "projection": "emit the written-form-keyed canonical carve with exact base-letter span ownership; one canonical carve per occurrence surface; rasm note where the alif is elided",
                 "guards": ["byte-exact span concatenation", "base-letter-count resplit (marks ride their base letter)", "per-surface carve parity (contract §1.1/§2.3)"],
                 "scope": "surface-match"},
        "rels": [("cites", "sarf-demonstrative-dagger-alef-normalize", "registry",
                  "Sibling orthography-aware carve rule; both keep normalization out of the public bytes."),
                 ("extends", "sarf-li-kasra-noun-host-clitic-carve", "registry",
                  "Specializes the noun-host carve for the ال-bearing and Name-fused hosts with letter-ownership discipline.")],
        "fixtures": [
            {"fid": "inc24-sarf-fused-lil-exact-letter-ownership-lillahi-pos",
             "eid": "INC24-SARF_FUSED_LIL_EXACT_LETTER_OWNERSHIP-12_31_24", "red": True,
             "loc": "12:31:24", "surfaces": ["لله"],
             "case": {"article_written": "elided_into_name_fusion", "prefix": "لِ"},
             "correct": "carve_clitic_lam_plus_fused_name", "wrong": "fold_article_into_host_per_page",
             "cite": "12:31:24 لِلَّهِ — fused rasm: the clitic owns its lām+kasra, the fused writing of the Name owns لَّهِ; live folded or carved per page"},
            {"fid": "inc24-sarf-fused-lil-exact-letter-ownership-linnas-pos",
             "eid": "INC24-SARF_FUSED_LIL_EXACT_LETTER_OWNERSHIP-24_35_44", "red": True,
             "loc": "24:35:44", "surfaces": ["للناس"],
             "case": {"article_written": "assimilated_visible", "prefix": "لِ"},
             "correct": "carve_clitic_article_host_three_spans", "wrong": "fold_article_into_host_per_page",
             "cite": "24:35:44 لِلنَّاسِ — written assimilated article gets its own span; live carved this SAME surface two different ways at 24:35:44 vs 2:187:63"},
            {"fid": "inc24-sarf-fused-lil-exact-letter-ownership-ctl",
             "eid": "INC24CTL-SARF_FUSED_LIL_EXACT_LETTER_OWNERSHIP-5_3_9", "red": False,
             "loc": "5:3:9", "surfaces": ["لغير"],
             "case": {"article_written": "none", "prefix": "لِ"},
             "correct": "carve_clitic_host_two_spans",
             "cite": "5:3:9 لِغَيْرِ — bare noun host, two spans; no article plane at all (rule branches)"},
        ],
    },
    {
        "sid": "sarf-nfc-normalize-before-span-parity", "skill": "sarf", "rule": "nfc_span_parity",
        "fam": "surface-normalization", "phen": "shadda-vowel-codepoint-order-false-fork",
        "domain": "normalization", "readiness": "projector_ready",
        "scope": ("Combining-mark codepoint ORDER is not a carve fork: the repo lattice stores "
                  "vowel-before-shadda while the live whitelist stores shadda-before-vowel — "
                  "canonically equivalent sequences (Unicode ccc reorders the vowels 30–32 before "
                  "shadda 33 under NFC). Any span/boundary parity comparison MUST NFC-normalize "
                  "BOTH sides first (comparison key only — public bytes are never mutated). A "
                  "difference that survives NFC is a TRUE carve fork and must be reported (the "
                  "live plane's folded-article لنَّاسِ vs the canonical carve). The pilot hit this "
                  "at 12:31:24, 24:35:44, 24:31:23."),
        "ev": [q("12:31:24"), q("24:35:44"), q("24:31:23"), q("2:187:63"), CONTRACT, SKEV],
        "defeaters": ["the two sides differ in base letters or span boundaries after NFC → a genuine fork; NFC never absolves a real carve difference",
                      "the difference is a matching-normalization concern (harakāt/annotation-mark stripping) → that is a different, lossier key; span parity uses NFC only"],
        "abst": "encoding of one side unknown/unverifiable → hold the parity verdict; never compare raw bytes across planes",
        "proj": {"condition": "span/boundary parity comparison between two planes whose surfaces may differ in combining-mark order",
                 "projection": "NFC-normalize both sides before comparison; report equivalence or a true fork; never mutate public bytes",
                 "guards": ["NFC on BOTH sides (symmetry)", "public-byte immutability", "post-NFC differences reported as true forks"],
                 "scope": "surface-match"},
        "rels": [("extends", "sarf-orthographic-match-symmetry", "registry",
                  "Adds the canonical-equivalence (mark-order) axis to symmetric normalization: NFC before span parity, distinct from the lossy ortho fold.")],
        "fixtures": [
            {"fid": "inc24-sarf-nfc-normalize-before-span-parity-lam-pos",
             "eid": "INC24-SARF_NFC_NORMALIZE_BEFORE_SPAN_PARITY-12_31_24", "red": True,
             "loc": "12:31:24", "surfaces": ["لله"],
             "case": {"side_a": _LAM_KASRA_SHADDA, "side_b": _LAM_SHADDA_KASRA},
             "correct": "boundary_equivalent_after_nfc", "wrong": "boundary_fork_reported",
             "cite": "12:31:24 — matrix stores lam+kasra+shadda, live stores lam+shadda+kasra; byte compare reported a boundary fork; NFC proves equivalence"},
            {"fid": "inc24-sarf-nfc-normalize-before-span-parity-nas-pos",
             "eid": "INC24-SARF_NFC_NORMALIZE_BEFORE_SPAN_PARITY-24_35_44", "red": True,
             "loc": "24:35:44", "surfaces": ["للناس"],
             "case": {"side_a": _NAS_FATHA_SHADDA, "side_b": _NAS_SHADDA_FATHA},
             "correct": "boundary_equivalent_after_nfc", "wrong": "boundary_fork_reported",
             "cite": "24:35:44 host span نَّاسِ — fatha/shadda order differs across planes; NFC-equivalent, not a fork"},
            {"fid": "inc24-sarf-nfc-normalize-before-span-parity-ctl",
             "eid": "INC24CTL-SARF_NFC_NORMALIZE_BEFORE_SPAN_PARITY-2_187_63", "red": False,
             "loc": "2:187:63", "surfaces": ["للناس"],
             "case": {"side_a": _HOST_WITH_ARTICLE_LAM, "side_b": _NAS_SHADDA_FATHA},
             "correct": "true_carve_fork",
             "cite": "2:187:63 — live folds the article lām into the host span (لنَّاسِ) where the canonical carve owns نَّاسِ; the difference survives NFC — a TRUE carve fork (rule branches)"},
        ],
    },
    # ================================ NAHW @2.4 — government + notation + mood basis =================
    {
        "sid": "nahw-preposition-governs-majrur-governor", "skill": "nahw", "rule": "jarr_governor",
        "fam": "governor-attachment", "phen": "governor-null-case-claim-rejection",
        "domain": "government", "readiness": "projector_ready",
        "scope": ("An iʿrāb jarr claim on a majrūr names the PREPOSITION ITSELF as governor "
                  "(relation preposition-governs-majrur) — always, including when the jarr-majrūr "
                  "phrase serves as fronted predicate. Government and attachment are DIFFERENT "
                  "planes: the mutaʿalliq/khabar question lives in the attachment field and is "
                  "never a reason to null the governor. The pilot's original convention emitted "
                  "governor:null on fronted-predicate rows (9:120:3, 4:11:5); the repo validator "
                  "rightly rejected the case claim, and both reviewers independently endorsed the "
                  "preposition-as-governor repair — naḥw-correct and validator-compatible."),
        "ev": [q("9:120:3"), q("4:11:5"), q("2:34:3"), SKEV, PFREG],
        "defeaters": ["the claimed case is not jarr / the token is not a majrūr → this rule is silent; the general governor ladder applies",
                      "the majrūr is governed by iḍāfa (muḍāf-ilayh), not a preposition → the governor is the muḍāf, not any preposition"],
        "abst": "governing element genuinely undecidable at the address → hold the case claim entirely; never emit case with a null governor",
        "proj": {"condition": "iʿrāb jarr claim on a preposition's majrūr with a null or attachment-derived governor",
                 "projection": "set governor = the preposition itself (preposition-governs-majrur); keep attachment in its own field; repair rather than emit null",
                 "guards": ["government/attachment plane separation", "validator-compatible governor spine", "fronted-predicate rows included"],
                 "scope": "construction-match"},
        "rels": [("cites", "nahw-lam-prefix-typology", "registry",
                  "Presupposes the lām is typed jarr; the governor convention then follows deterministically."),
                 ("extends", "nahw-mood-from-governor", "registry",
                  "Extends the governor-visibility discipline to the nominal jarr side: the visible governor of a majrūr is the preposition itself.")],
        "fixtures": [
            {"fid": "inc24-nahw-preposition-governs-majrur-governor-pos",
             "eid": "INC24-NAHW_PREPOSITION_GOVERNS_MAJRUR_GOVERNOR-9_120_3", "red": True,
             "loc": "9:120:3", "surfaces": ["لأهل"],
             "case": {"case_claim": "jarr_nominal", "governor": None, "attachment": "khabar_muqaddam"},
             "correct": "repair_set_preposition_governor", "wrong": "emit_null_governor_case_claim",
             "cite": "9:120:3 لِأَهْلِ — fronted-predicate row emitted with governor:null; the validator rejects a case claim with no governor; repair = the preposition itself"},
            {"fid": "inc24-nahw-preposition-governs-majrur-governor-411-pos",
             "eid": "INC24-NAHW_PREPOSITION_GOVERNS_MAJRUR_GOVERNOR-4_11_5", "red": True,
             "loc": "4:11:5", "surfaces": ["للذكر"],
             "case": {"case_claim": "jarr_nominal", "governor": None, "attachment": "khabar_muqaddam"},
             "correct": "repair_set_preposition_governor", "wrong": "emit_null_governor_case_claim",
             "cite": "4:11:5 لِلذَّكَرِ — the second khabar-muqaddam row re-voted after the governor-null defect; reviewer-B independently endorsed the preposition-as-governor correction"},
            {"fid": "inc24-nahw-preposition-governs-majrur-governor-ctl",
             "eid": "INC24CTL-NAHW_PREPOSITION_GOVERNS_MAJRUR_GOVERNOR-2_34_3", "red": False,
             "loc": "2:34:3", "surfaces": ["للملائكة"],
             "case": {"case_claim": "jarr_nominal", "governor": "preposition_itself", "attachment": "verb"},
             "correct": "accept_preposition_governor",
             "cite": "2:34:3 لِلْمَلَٰٓئِكَةِ — ordinary verb-attached jarr-majrūr with the preposition named as governor; accepted as-is (rule branches)"},
        ],
    },
    {
        "sid": "nahw-khabar-muqaddam-two-notations-one-analysis", "skill": "nahw",
        "rule": "khabar_muqaddam_notation",
        "fam": "attachment-notation", "phen": "notation-variant-false-disagreement",
        "domain": "government", "readiness": "projector_ready",
        "scope": ("For a jarr-majrūr (shibh al-jumla) serving as fronted predicate, the two "
                  "standard notations — 'khabar muqaddam' and 'mutaʿalliq to an elided fronted "
                  "khabar (mutaʿalliqan bi-maḥdhūf khabar muqaddam)' — are ONE analysis. Reviews, "
                  "projections, and agreement computation must map both to the single reason key "
                  "khabar-muqaddam-shibh-jumla; recording them as reviewer disagreement is a "
                  "notation artifact (two-vote canary 3 and the pilot's rows 9:120:3 / 4:11:5 all "
                  "reproduced it). A genuinely different attachment (ṣifa, ḥāl, verb attachment) "
                  "remains a real disagreement and routes normally."),
        "ev": [q("2:284:1"), q("9:120:3"), q("4:11:5"), SKEV, PFREG],
        "defeaters": ["the rival reading is a different attachment head (ṣifa/ḥāl/verb) → a genuine disagreement, not a notation variant",
                      "the construction is not a fronted-predicate shibh al-jumla → the equivalence class does not apply"],
        "abst": "attachment head genuinely contested between non-equivalent readings → route two-vote/scholar; never merge non-equivalent notations",
        "proj": {"condition": "two reviews of a fronted-predicate jarr-majrūr differ only between the khabar-muqaddam and mutaʿalliq-to-elided-khabar notations",
                 "projection": "map both to the shared reason key (khabar-muqaddam-shibh-jumla); compute agreement over the key, not the prose",
                 "guards": ["closed notation-equivalence set", "genuine-attachment-difference passthrough", "reason-key registry as the agreement vocabulary"],
                 "scope": "construction-match"},
        "rels": [("cites", "nahw-preposition-governs-majrur-governor", "registry",
                  "The attachment plane this rule normalizes is exactly the field the governor rule keeps separate from government.")],
        "fixtures": [
            {"fid": "inc24-nahw-khabar-muqaddam-two-notations-one-analysis-pos",
             "eid": "INC24-NAHW_KHABAR_MUQADDAM_TWO_NOTATIONS_ONE_ANALYSIS-2_284_1", "red": True,
             "loc": "2:284:1", "surfaces": ["لله"],
             "case": {"notation_a": "khabar_muqaddam", "notation_b": "mutaalliq_elided_fronted_khabar"},
             "correct": "one_analysis_shared_reason_key", "wrong": "textual_disagreement_recorded",
             "cite": "2:284:1 لِّلَّهِ (canary 3) — reviewer A wrote khabar muqaddam, reviewer B wrote mutaʿalliq to elided fronted khabar; exact-string agreement recorded a false disagreement"},
            {"fid": "inc24-nahw-khabar-muqaddam-two-notations-one-analysis-ctl",
             "eid": "INC24CTL-NAHW_KHABAR_MUQADDAM_TWO_NOTATIONS_ONE_ANALYSIS-SIFA", "red": False,
             "loc": "9:120:3", "surfaces": ["لأهل"],
             "case": {"notation_a": "khabar_muqaddam", "notation_b": "sifa_attachment"},
             "correct": "genuine_attachment_disagreement",
             "cite": "boundary: khabar-muqaddam vs a ṣifa attachment reading is a REAL disagreement — the equivalence set must not swallow it (rule branches)"},
        ],
    },
    {
        "sid": "nahw-mood-basis-tajarrud-governor-exemption", "skill": "nahw", "rule": "tajarrud_mood",
        "fam": "mood-basis", "phen": "tajarrud-raf-false-governor-requirement",
        "domain": "government", "readiness": "projector_ready",
        "scope": ("A muḍāriʿ marfūʿ by tajarrud — the ABSENCE of any nāṣib/jāzim operator "
                  "(li-tajarrudihi ʿan al-nāṣib wa-l-jāzim) — carries mood_basis=tajarrud and "
                  "requires NO overt governor. The 'case value + visible sign ⇒ governor required' "
                  "rule is a NOMINAL iʿrāb rule; applied to verbs it mislabels default-mood rafʿ "
                  "(two-vote canary 1, quran:2:91:23 تَقْتُلُونَ, sign thubūt al-nūn: BOTH "
                  "independent reviewers correctly recorded rafʿ-by-tajarrud and the validator "
                  "failed the artifact — a contract bug, not a vote bug). Nominal case claims keep "
                  "the full governor requirement."),
        "ev": [q("2:91:23"), q("2:173:23"), SKEV, PFREG],
        "defeaters": ["a nāṣib/jāzim IS visible in range → the mood is governed; tajarrud must not be claimed to dodge naming the governor",
                      "the claim is a nominal case → the governor requirement stands in full"],
        "abst": "operator presence undecidable at the address (ellipsis/qirāʾāt split) → named ambiguity, not a tajarrud default",
        "proj": {"condition": "verb-mood rafʿ claim whose basis is the absence of any nāṣib/jāzim",
                 "projection": "accept mood_basis=tajarrud without an overt governor; keep the governor requirement for governed moods and all nominal case claims",
                 "guards": ["claim-kind split (verb_mood vs nominal_case)", "operator-absence check before tajarrud", "reason key mudari3-raf3-tajarrud-thubut-nun"],
                 "scope": "construction-match"},
        "rels": [("extends", "nahw-mood-from-governor", "registry",
                  "Completes the mood ladder with the no-governor default case: rafʿ by tajarrud is a stated BASIS, not a missing governor."),
                 ("extends", "nahw-jazm-only-on-mudari", "registry",
                  "Sibling mood-domain invariant; both constrain what a well-formed verb-mood claim may assert.")],
        "fixtures": [
            {"fid": "inc24-nahw-mood-basis-tajarrud-governor-exemption-pos",
             "eid": "INC24-NAHW_MOOD_BASIS_TAJARRUD_GOVERNOR_EXEMPTION-2_91_23", "red": True,
             "loc": "2:91:23", "surfaces": ["تقتلون"],
             "case": {"claim_kind": "verb_mood", "mood_basis": "tajarrud", "governor": None, "sign": "thubut_al_nun"},
             "correct": "accept_mood_basis_tajarrud", "wrong": "reject_missing_governor",
             "cite": "2:91:23 تَقْتُلُونَ (canary 1) — rafʿ by tajarrud, sign thubūt al-nūn; both votes correct, validator rejected for a missing governor: the contract bug this rule fixes"},
            {"fid": "inc24-nahw-mood-basis-tajarrud-governor-exemption-inna-ctl",
             "eid": "INC24CTL-NAHW_MOOD_BASIS_TAJARRUD_GOVERNOR_EXEMPTION-2_173_23", "red": False,
             "loc": "2:173:23", "surfaces": ["الله"],
             "case": {"claim_kind": "nominal_case", "governor": "inna_2_173_22", "sign": "fatha"},
             "correct": "accept_governed_case",
             "cite": "2:173:23 ٱللَّهَ — ism of إِنَّ with its governor named (canary 4); nominal claims keep the governor requirement (rule branches)"},
            {"fid": "inc24-nahw-mood-basis-tajarrud-governor-exemption-null-ctl",
             "eid": "INC24CTL-NAHW_MOOD_BASIS_TAJARRUD_GOVERNOR_EXEMPTION-NOMINAL_NULL", "red": False,
             "loc": "9:120:3", "surfaces": ["لأهل"],
             "case": {"claim_kind": "nominal_case", "governor": None, "sign": "kasra"},
             "correct": "reject_missing_governor",
             "cite": "boundary: a nominal case claim with a null governor is STILL rejected — tajarrud never leaks into the nominal plane"},
        ],
    },
    {
        "sid": "nahw-lam-talil-vs-jarr-host-pos", "skill": "nahw", "rule": "lam_function_by_host",
        "fam": "particle-function", "phen": "lam-jarr-vs-talil-host-pos-disambiguation",
        "domain": "function", "readiness": "projector_ready",
        "scope": ("A token-initial لِ types by its HOST'S POS and mood before any gloss, family "
                  "assignment, or government claim: a nominal host ⇒ لام الجر (governs the host "
                  "into jarr); a muḍāriʿ manṣūb (بأن مضمرة) ⇒ لام التعليل (purpose; subjunctive "
                  "via the implied أن — NOT jarr, and no jarr reason key may attach); a muḍāriʿ "
                  "majzūm ⇒ لام الأمر (jussive). The pilot's rejected rival لِيَغِيظَ (48:29:42, "
                  "MCP: فعل مضارع منصوب بأن مضمرة) is the canonical taʿlīl catch retained on the "
                  "p007 lattice; لِدُلُوكِ (17:78:3) shows the temporal jarr reading over a noun."),
        "ev": [q("48:29:42"), q("17:78:3"), q("65:7:1"), MATRIX, PFREG],
        "defeaters": ["the lām carries fatḥa over a noun/pronoun in an emphasis frame → لام الابتداء/التوكيد, no government at all (a fourth type outside this rule's kasra scope)",
                      "the host POS is unresolved → hold; the lām type may not default to jarr"],
        "abst": "host POS/mood unresolved at the address → route particle_function_rule_needed; never default the lām to jarr",
        "proj": {"condition": "token-initial لِ whose host POS/mood is classified",
                 "projection": "type the lām (jarr / taʿlīl / amr) from the host; propagate the matching government (jarr sign vs subjunctive-by-implied-أن vs jussive); block cross-type reason keys",
                 "guards": ["host-POS gate before typing", "mood confirmation for the verb branches", "reason keys segregated per lām type"],
                 "scope": "construction-match"},
        "rels": [("extends", "nahw-lam-prefix-typology", "registry",
                  "Makes the lām-typology decision deterministic where the host POS/mood is known, with the pilot's measured rival catches as fixtures.")],
        "fixtures": [
            {"fid": "inc24-nahw-lam-talil-vs-jarr-host-pos-yaghiza-pos",
             "eid": "INC24-NAHW_LAM_TALIL_VS_JARR_HOST_POS-48_29_42", "red": True,
             "loc": "48:29:42", "surfaces": ["ليغيظ"],
             "case": {"host_pos": "verb_mudari_mansub", "lam_vowel": "kasra"},
             "correct": "lam_talil_an_mudmara_subjunctive", "wrong": "lam_jarr_governs_majrur",
             "cite": "48:29:42 لِيَغِيظَ — muḍāriʿ manṣūb بأن مضمرة: lām-taʿlīl, not jarr; the p007 lattice's blanket jarr candidate is the superseded reading"},
            {"fid": "inc24-nahw-lam-talil-vs-jarr-host-pos-yunfiq-pos",
             "eid": "INC24-NAHW_LAM_TALIL_VS_JARR_HOST_POS-65_7_1", "red": True,
             "loc": "65:7:1", "surfaces": ["لينفق"],
             "case": {"host_pos": "verb_mudari_majzum", "lam_vowel": "kasra"},
             "correct": "lam_amr_jussive", "wrong": "lam_jarr_governs_majrur",
             "cite": "65:7:1 لِيُنفِقْ — muḍāriʿ majzūm: lām al-amr governing jussive; a jarr reading over the verb is impossible"},
            {"fid": "inc24-nahw-lam-talil-vs-jarr-host-pos-ctl",
             "eid": "INC24CTL-NAHW_LAM_TALIL_VS_JARR_HOST_POS-17_78_3", "red": False,
             "loc": "17:78:3", "surfaces": ["لدلوك"],
             "case": {"host_pos": "noun", "lam_vowel": "kasra"},
             "correct": "lam_jarr_governs_majrur",
             "cite": "17:78:3 لِدُلُوكِ — nominal host: the temporal jarr lām governing دلوك in jarr (rule branches)"},
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
            "origin": "increment-24-p00-pilot-dogfood",
            "cycle": "2026-07-29",
            "source": SKEV,
            "projector_readiness": r["readiness"],
            "phenomenon": r["phen"],
            "domain": r["domain"],
        }
        row = {
            "skill_rule_id": sid,
            "skill": sk,
            "skill_version": sk + "@2.4",
            "status": "candidate",
            "fact_family": r["fam"],
            "scope": r["scope"],
            "evidence_addresses": r["ev"],
            "positive_examples": pos_ex,
            "negative_or_boundary_examples": ctl_ex,
            "defeaters": r["defeaters"],
            "abstention_condition": r["abst"],
            "gate": "@2.4-candidate:redfirst+p00-pilot-measured",
            "code_references": ["tools/skill_fixtures/skill_rules_increment24.py"],
            "test_references": ["tools/skill_fixtures/test_skill_fixtures_increment24.py"],
            "relationships": rels,
            "provenance": provenance,
            "projector": proj,
        }
        rows.append(row)
    return rows


def build_fixture_rows():
    fixtures = []
    for r in RULES:
        for f in r["fixtures"]:
            fx = {
                "fixture_id": f["fid"],
                "example_id": f["eid"],
                "rule_id": r["sid"],
                "rule": r["rule"],
                "skill_version": r["skill"] + "@2.4",
                "phenomenon": r["phen"],
                "domain": r["domain"],
                "canonical_locations": [f["loc"]],
                "surfaces": f.get("surfaces", []),
                "case": f["case"],
                "correct_label": f["correct"],
                "redfirst": f["red"],
                "citation": f["cite"],
            }
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
            drift.append("rule-registry-increment-24.jsonl")
        if _read(FIXTURES_OUT) != fx_body:
            drift.append("skill_fixtures_increment24.jsonl")
        if drift:
            print("DRIFT (regenerate via _build_increment24.py): " + ", ".join(drift))
            return 1
        print("increment-24 builder: committed artifacts match regeneration (%d rules, %d fixtures)"
              % (len(reg_rows), len(fx_rows)))
        return 0
    _dump(REGISTRY_OUT, reg_rows)
    _dump(FIXTURES_OUT, fx_rows)
    sarf = sum(1 for r in reg_rows if r["skill"] == "sarf")
    nahw = sum(1 for r in reg_rows if r["skill"] == "nahw")
    print("wrote %s (%d rules: %d sarf, %d nahw)"
          % (os.path.relpath(REGISTRY_OUT, REPO), len(reg_rows), sarf, nahw))
    print("wrote %s (%d fixtures)" % (os.path.relpath(FIXTURES_OUT, REPO), len(fx_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
