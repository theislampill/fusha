# Corpus-grounded pilot (candidate) — canonical occurrences under repo authority

Two candidate instructional envelopes built **entirely from committed p007
pilot authority** — `qamus/examples/p007-li-pilot/` typed facts, projections,
reverse index and certification event trail. No new linguistic conclusion is
introduced anywhere.

| Requirement | Where |
|---|---|
| exact canonical occurrence | `quran:2:34:5` (لِءَادَمَ) and `quran:61:5:4` (لِقَوْمِهِۦ) |
| root vs affix ownership | clitic لِ = rootless jarr morpheme (repo fact); host-internal split **UNRESOLVED** — see next row |
| unresolved-state preservation | the real consumer (`tools/curriculum_unit_consumer.py`) runs on each token and **abstains `no_root_evidence`**: the repo certifies the carve, not the host's internal letters; the envelope records the abstention + the resolution path instead of guessing |
| Ṣarf and Naḥw facts | the occurrence's 4 typed facts + the particle-rootlessness fact, cited by `fact_id` with certification posture copied **verbatim** (never upgraded) |
| all authoritative appearances | the projection row's appearance list (5 and 4 rows), all carrying the single projection hash (`single_hash_parity: true`) |
| colour + hover from same facts | segments and hover cards read from the ONE `p00.two_surface_projection.v1` record; `segment_hover_parity` asserted |
| reverse trace | `entry-reverse-index.json` entry→occurrence listing confirmed |
| website-compatible candidate envelope | 61:5:4 references the EXISTING payload sample; 2:34:5 carries a shape-compatible `candidate_payload_shape` marked `deliverable: false` (payload production stays with the website-handoff lane) |
| one reusable lesson, second occurrence | inc-ownership rules (units u-s09/u-s01) applied to BOTH occurrences by the same pack — method transfer, no token-specific copying (og-2) |

Regenerate / verify:

```
python tools/build_curriculum_corpus_pilot.py          # write
python tools/build_curriculum_corpus_pilot.py --check  # byte-diff vs recompute
```

The curriculum validator recomputes these envelopes on every run; drift
between the p007 store, the consumer and the committed envelopes is red.
