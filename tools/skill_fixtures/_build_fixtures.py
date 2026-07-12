# -*- coding: utf-8 -*-
"""Emit the permanent skill-fixtures JSONL (gate 9). Each row cites example_id + rule_id and carries a
deterministic `case` for tools/skill_fixtures/skill_rules.py. redfirst=True rows fail against the superseded
rule and pass against the corrected rule."""
import io, json, os

OUT = os.path.join(os.path.dirname(__file__), "skill_fixtures.jsonl")

F = []


def add(fixture_id, phenomenon, rule, example_id, rule_id, locs, surfaces, case,
        correct_label, wrong_label, citation, redfirst=True):
    F.append({
        "fixture_id": fixture_id,
        "phenomenon": phenomenon,
        "rule": rule,
        "example_id": example_id,
        "rule_id": rule_id,
        "canonical_locations": locs,
        "surfaces": surfaces,
        "redfirst": redfirst,
        "correct_label": correct_label,
        "wrong_label": wrong_label,
        "citation": citation,
        "case": case,
    })


# 1. adjacent-token ownership misbinding
add("adjacency-not-ownership-1-7-4", "adjacency-not-ownership", "adjacency_ownership",
    "OEB-ADJ-1_7_4", "so-adjacency-not-ownership", ["1:7:4"], ["عَلَيْهِمْ"],
    {"target_root": None, "carrier_root": "غ ض ب", "surface_in_carrier_forms": False,
     "carrier_is_adjacent_word_root": True},
    "unowned", "owned",
    "adjacency binds nothing: carrier غ ض ب is the root of the ADJACENT word ٱلْمَغْضُوب, not of the ḥarf-jarr+ḍamīr target")

# 2. affirm_live as a valid disposition
add("affirm-live-prep-pron-lka", "affirm-live", "affirm_live",
    "OEB-AFFIRM-2_128_9", "so-affirm-live-valid-outcome", ["2:128:9"], ["لَّكَ"],
    {"root_overlap": False, "surface_in_forms": False, "schema_can_express_affirm_live": True},
    "affirm_live", "blocked_no_decision",
    "lām al-jarr + kāf: no carrier owns it; affirm_live must be a first-class outcome, not blocked as 'no decision'")
add("affirm-live-relative-man", "affirm-live", "affirm_live",
    "OEB-AFFIRM-2_142_17", "so-affirm-live-valid-outcome", ["2:142:17"], ["مَن"],
    {"root_overlap": False, "surface_in_forms": False, "schema_can_express_affirm_live": True},
    "affirm_live", "blocked_no_decision",
    "man = ism mawṣūl, indeclinable, no lexical root; zero root-overlap with any aligning carrier")

# 3. root-less noun ownership boundary
add("rootless-noun-convention-3-191-7", "rootless-noun-convention", "rootless_noun_ownership",
    "OEB-NOUNCONV-3_191_7", "so-rootless-noun-ownership-convention", ["3:191:7"], ["جُنُوبِهِمْ"],
    {"root_field": "", "headword_skeleton": "ج ن ب", "target_self_root": "ج ن ب", "surface_in_own_forms": True},
    "owned_noun_entry", "ownership_suspect",
    "blank root FIELD is a noun-entry data convention (994/2092); janb owns the surface by headword-skeleton + own forms")

# 4. function-word vs content-root routing
add("funcroute-ahl-false-hal", "function-word-routing", "funcword_routing",
    "OEB-FUNCROUTE-ahl-vs-hal", "so-funcword-never-content-root-competition", ["2:109:4", "3:75:2"], ["أَهْلِ"],
    {"surface": "أَهْلِ", "candidate_particle": "hal", "contains_divine_name": False},
    "content_lane", "function_lane_interrogative",
    "أَهْل (اهل, 3 letters) is a content noun, not the interrogative هَل (هل, 2 letters); false-positive segmentation")
add("funcroute-lillahi-preposition", "function-word-routing", "funcword_routing",
    "OEB-LILLAHI-preposition-normalize", "so-funcword-never-content-root-competition", ["2:22:20", "22:31:2"], ["لِلَّهِ"],
    {"surface": "لِلَّهِ", "candidate_particle": "", "contains_divine_name": True},
    "preposition", "lam_family_reclassify",
    "SSOT taxonomy assigns the fused lillāh divine-name token to category 'preposition' (lām al-jarr), not lam_family")

# 5. harakah conflict (šadda distinction must never collapse)
add("diacritic-homograph-in-vs-inna", "diacritic-homograph", "in_conditional",
    "OEB-HOMOGRAPH-in-vs-inna", "so-preserve-hamza-and-harakah-distinctions", ["2:24:1", "6:25:28"], ["إِنْ", "إِنَّ"],
    {"surface": "إِنْ", "has_shadda": False},
    "in_conditional_or_nafiya", "inna_tawkid",
    "إِنْ (no šadda) is conditional/nāfiya, NOT إِنَّ the emphatic; harakah/šadda distinguishes — never norm() alone")

# 6. مِنْ vs مَنْ
add("diacritic-homograph-man-vs-min", "diacritic-homograph", "man_vs_min",
    "OEB-HOMOGRAPH-man-vs-min", "so-diacritic-homograph-predisambiguation-gate",
    ["2:62:8", "2:256:10"], ["مَن", "مَنْ"],
    {"surface": "مَن", "haraka_on_mim": "fatha"},
    "pronoun_who_relative", "preposition_from",
    "مَن (fatḥa) is the pronoun who/whoever; the surface-diacritic gate must split it from مِن (kasra, 'from')")

# 8. أنْ المخففة vs conditional/maṣdariyya overgeneralization
add("sublexeme-an-masdariyya-vs-anna", "diacritic-homograph", "an_sublexeme",
    "OEB-SUBLEXEME-an-vs-anna", "so-diacritic-homograph-predisambiguation-gate", ["4:27:3", "2:266:3"], ["أَنْ", "أَنَّ"],
    {"surface": "أَنْ", "has_shadda": False},
    "an_masdariyya", "anna_tawkid",
    "أَنْ al-maṣdariyya (subjunctive subordinator) is a distinct sub-lexeme from أَنَّ al-tawkīd; needs its own taxonomy slot (ONH-B1 gap)")
add("certified-retain-both-in-86-4", "certified-retain-both", "retain_both",
    "OEB-CERTIFIEDTIE-POS-86_4_1", "so-morphline-alternatives-stay-alternatives", ["86:4:1"], ["إِن"],
    {"certified": True, "licensed_readings": ["nafiya", "mukhaffafa_min_al_thaqila"]},
    "retain_both", "majority_vote_single",
    "إِنْ nāfiya vs mukhaffafa min al-thaqīla: a certified disagreement is retain_both — both readings carried, never majority-voted")

# 9. لا/ما function alternatives — family label is not a resolution (ONH-B4)
add("ma-family-subfunc-pos-mawsul", "ma-lam-family-subfunction", "ma_family_subfunction",
    "OEB-SUBFUNC-POS-80_23_4", "ONH-B4", ["80:23:4"], ["مَا"],
    {"sub_function": "relative", "object_of_transitive_verb": True},
    "resolved:relative", "ma_family",
    "مَا at 80:23:4 is mafʿūl bih of يَقْضِ = اسم موصول; ma_family is a ROUTING bucket requiring a per-occurrence sub-function")

# 14. THE 5:116:33 fixture — relative مَا NOT negation
add("test_ma_family_relative_not_negation", "ma-family-relative-vs-negation", "ma_neg_vs_rel",
    "ex-live-ma-5116-33", "ONH-B1", ["5:116:33"], ["مَا"],
    {"object_of_transitive_verb": True, "followed_by_pos": "prep"},
    "qg-ma-particle", "qg-negation",
    "5:116:33 «تَعْلَمُ مَا فِى نَفْسِى»: مَا is object of تَعْلَمُ + followed by prep فِى = relative 'what'; NOT negation. "
    "Decisive sibling 5:116:38 already 'what'. cite impl-records/live-content-fixes/NF-LIVE-MA-5116-33.md")
# negation control — proves the corrected rule does NOT over-swing (same āyah مَا يَكُونُ pattern)
add("ma-negation-control-before-verb", "ma-family-relative-vs-negation", "ma_neg_vs_rel",
    "ex-live-ma-5116-33", "ONH-B1", ["5:116"], ["مَا"],
    {"object_of_transitive_verb": False, "followed_by_pos": "verb"},
    "qg-negation", "qg-negation",
    "control: مَا directly negating a following verb (مَا يَكُونُ) stays negation — corrected rule must not over-correct",
    redfirst=False)

# 7. الله split suppression
add("allah-family-split-suppression-lillah", "affirm-live", "allah_split",
    "OEB-LILLAHI-preposition-normalize", "so-allah-family-split-suppression", ["2:22:20"], ["لِلَّهِ"],
    {"surface": "لِلَّهِ", "segmentation": ["لِ", "اللَّه"]},
    "prep_plus_divine_name", "pronoun_stem_lahu",
    "لِلَّهِ = لِ (lām al-jarr) + divine name اللَّه (root ء ل ه); never ال+له, never the pronoun stem لَه (lahu)")

# 10. qg-lam blocked for insufficient exemplars
add("governor-locality-qglam-exact-shape", "governor-locality", "qglam_floor",
    "OEB-GOVLOCALITY-qglam-shape", "so-qglam-purpose-lam-blocked-floor", ["5:6:56"], ["لِيُطَهِّرَكُمْ"],
    {"segment_class_shape": ["qg-lam"], "exemplar_count": 1, "floor": 10, "broaden_pool": True},
    "blocked_insufficient_convention_exemplars", "unblocked",
    "the floor is measured over the EXACT segment_class_shape ['qg-lam'] (n=1, floor=10); broadening the pool to any purpose-lām is invalid")

# 11. morphline no-placeholder
add("morphline-approved-lam-relative", "morphline-authoring", "morphline_placeholder",
    "OEB-MORPHLINE-approved-lam-relative", "so-morphline-authored-not-mechanical", ["12:42:2"], ["لِلَّذِى"],
    {"authored_value": "lām al-jarr (no root) prefixed to & governing masc-sing relative pronoun ٱلَّذِى → 'to the one who'",
     "superseded_value": ""},
    "authored_valid", "invalid_placeholder",
    "an authored morphline is linguistic content; the pre-fix EMPTY morphline (placeholder) fails closed")

# 12. case/maḥall abstention
add("mabni-neg-man-assigned-ending", "mabni-fi-mahall", "mabni_mahall",
    "OEB-MABNI-NEG-2_143_21", "ONH-D2", ["2:143:21"], ["مَن"],
    {"correct_analysis_obj": {"mabni": True, "mabni_on": "sukun", "fi_mahall": "nasb",
                              "reasoning": "relative noun, mafʿūl bih of لنعلم", "assigned_irab_ending": None},
     "wrong_analysis_obj": {"mabni": True, "assigned_irab_ending": "manṣūb bi-l-fatḥa",
                            "fi_mahall": None, "reasoning": None}},
    "valid_fi_mahall_abstention", "invalid_assigned_ending_on_mabni",
    "a mabnī token NEVER takes an assigned iʿrābī ending; record mabni_on + fi_maḥall + reasoning at the gate")
add("idafa-fimahall-neg-alayha", "idafa-mabni-fi-mahall", "mabni_mahall",
    "OEB-IDAFA-NEG-86_4_5", "ONH-6T5", ["86:4:5"], ["عَلَيْهَا"],
    {"correct_analysis_obj": {"mabni": True, "mabni_on": "sukun", "fi_mahall": "jarr",
                              "reasoning": "ḍamīr هَا mabnī fī maḥall jarr after عَلَى", "assigned_irab_ending": None},
     "wrong_analysis_obj": {"mabni": True, "assigned_irab_ending": "majrūr bi-l-kasra",
                            "fi_mahall": None, "reasoning": None}},
    "valid_fi_mahall_abstention", "invalid_assigned_ending_on_mabni",
    "the mabnī pronoun هَا takes fi_maḥall jarr (position), never an assigned genitive kasra ending")

# 13. source-address reference fidelity
_AYAH = {
    "11:101": "وما ظلمناهم ولكن ظلموا أنفسهم",
    "4:46": "من الذين هادوا يحرفون الكلم عن مواضعه",
    "4:64": "ولو أنهم إذ ظلموا أنفسهم جاءوك",
}
add("reffid-pos-11-101-contains-phrase", "source-address-ref-fidelity", "source_ref_fidelity",
    "OEB-REFFID-POS-11_101", "so-source-address-ref-fidelity", ["11:101"], ["ظَلَمُوا أَنفُسَهُمْ"],
    {"ar_phrase": "ظَلَمُوا أَنفُسَهُمْ", "named_ref": "11:101", "ayah_index": _AYAH},
    "admissible", "admissible",
    "verify-before-trust: 11:101 GENUINELY CONTAINS «ظلموا أنفسهم» — admissible as evidence", redfirst=False)
add("reffid-neg-4-46-wrong-ref", "source-address-ref-fidelity", "source_ref_fidelity",
    "OEB-REFFID-NEG-4_46", "so-source-address-ref-fidelity", ["4:46"], ["ظَلَمُوا أَنفُسَهُمْ"],
    {"ar_phrase": "ظَلَمُوا أَنفُسَهُمْ", "named_ref": "4:46", "ayah_index": _AYAH},
    "inadmissible_quarantine", "admissible",
    "verify-before-trust FAILS: 4:46 does NOT contain «ظلموا أنفسهم» (the phrase is at 4:64) — quarantine, never self-edit the ref byte")

# 15. correction/supersedes propagation
add("dependent-binding-reeval-neg-tombstone", "dependent-binding-reeval", "supersede_propagation",
    "OEB-BINDINGREEVAL-NEG-2_31_3", "so-supersede-not-delete", ["2:31:3"], ["ٱلْأَسْمَآءَ"],
    {"mode": "supersede", "tombstoned_id": "payload-sky-heavens-contaminated",
     "dependent_bindings": [{"binding": "hover-2:31:3", "points_at": "payload-sky-heavens-contaminated"}]},
    "conflict_reeval_required", "silent_delete",
    "on supersede, EVERY dependent binding at the tombstoned payload must be enumerated + re-evaluated (blast-radius sweep); delete-in-place is invalid")

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    for row in F:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
print("wrote", len(F), "fixtures ->", OUT)
