# dr04 reattempt — authoring readiness (lane-by-lane)

Verified at HEAD `a0f596b`.

| root cause | raw | post-hygiene | generator | validator | gate | contributes 90 | GO/NO-GO |
|---|---:|---:|---|---|---|---|---|
| `missing_form_variant_on_existing_entry` | 3461 | 3032 | build_form_variant_candidates.py | form_variant_family_batches.py | 2-vote | yes | GO |
| `forms_array_missing_surface` | 633 | 158 | build_source_entry_repair_candidates.py | source_entry_repair_candidates.py | 2-vote | yes | GO |
| `host_lexeme_possessive_candidate` | 1210 | 255 | build_host_lexeme_candidates.py | suffix_pronoun_decisions.py | 2-vote | yes | GO |
| `verb_clitic_object_or_subject_candidate` | 0 | 822 | build_verb_clitic_candidates.py | verb_clitic_candidates.py | 2-vote | yes | GO (new lane) |
| `function_word_not_form_work` | 0 | 550 | build_token_irab_decisions.py | token_irab_decisions.py | 2-vote | partial | GO (token) |
| `missing_qamus_entry_candidate` | 473 | 326 | build_new_entry_proposals.py | new_entry_proposals.py | owner | yes(if approved) | NO-GO (owner) |
| `quran_refs_missing_or_incomplete` | 394 | 72 | build_source_entry_repair_candidates.py | source_entry_repair_candidates.py | source | weak | NO-GO (source) |
| `source_photo_visual_needed` | 49 | 4 | build_source_entry_repair_candidates.py | source_entry_repair_candidates.py | source | no | NO-GO (source) |
| `verb_form_or_voice` | 148 | 148 | build_token_irab_decisions.py | token_irab_decisions.py | 2-vote | yes(per-loc) | GO (per-loc) |
| `content_homograph` | 82 | 82 | build_token_irab_decisions.py | token_irab_decisions.py | 2-vote | yes(per-loc) | GO (per-loc) |
| `genuinely_ambiguous_pending` | 148 | 148 | - | - | scholar | no | pending by design |

All generators + validators now exist (verb-clitic / new-entry / source-entry-repair built this tranche). GO lanes are 2-vote, generator+validator-ready; NO-GO lanes are owner/source/scholar-gated.
