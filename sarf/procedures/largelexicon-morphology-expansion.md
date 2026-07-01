# Largelexicon Morphology Expansion

Use this procedure when turning Qamus-authored entries into parser morphology
candidates.

1. Start from `qamus/data/current/entries.jsonl`; do not infer from live Qamus.
2. Preserve every listed form as a candidate form, not a certified paradigm.
3. Route by sarf:
   - rooted verbs: form-sensitive verb candidates;
   - nouns: nominal candidates;
   - proper names: explicit `proper_name_no_root`;
   - no-root nouns: explicit `qamus_entry_no_root_recorded`;
   - particles: defer function to nahw.
4. Preserve visible morphology inside the written token:
   - attached `بـ`, `لـ`, `كـ`, `سـ`, `فـ`, and `وـ` remain visible segments;
   - finite verb prefixes and subject endings stay visible;
   - object/possessive suffix pronouns stay visible and route to nahw for
     attachment/function;
   - derivative prefixes such as participial `مـ` and plural/dual suffixes
     remain visible when the surface supports them.
5. Never invent a root for a resemblance.
6. Keep visible segments concatenating to the surface.
7. Use `generation_key` for every generated stem row so the dependency-free
   generator can round-trip a known candidate.
8. Keep public rows source-clean: never copy external gloss text, and include no
   external source names, MCP labels, local paths, or process prose.

Output states are candidate states. A largelexicon row can accelerate Qamus
rollout and tutoring, but it is not live Qamus progress and not arbitrary-text
certification.

Required validator loop:

```powershell
python tools/build_largelexicon_source_inventory.py --sample-size 120 --commit-full
python tools/build_largelexicon_morph_db.py --sample-size 480 --commit-full
python tools/validate_largelexicon_morph_db.py --self-test
python tools/validate_largelexicon_parser.py --self-test
```
