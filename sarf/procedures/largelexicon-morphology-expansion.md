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
4. Never invent a root for a resemblance.
5. Keep visible segments concatenating to the surface.
6. Keep public rows source-clean: never copy external gloss text, and include no
   external source names, MCP labels, local paths, or process prose.

Output states are candidate states. A largelexicon row can accelerate Qamus
rollout and tutoring, but it is not live Qamus progress and not arbitrary-text
certification.
