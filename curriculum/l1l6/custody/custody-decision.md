# L1–L6 curriculum source custody decision

Status: **private_source_custody_metadata_only** (controlling for every row in
`source-manifest.jsonl`).

## Owner amendment — 2026-08-05: the source site is not named publicly

By owner direction, this public repository no longer names the source site.
Every `source_url` in this subtree uses the opaque alias host
`source-site.invalid` with the original path preserved unchanged, so the
mapping is bijective: alias URL ↔ real URL differ only in the host. The real
host, and therefore every exact source URL required by the §6A ruling's
provenance fields, is recorded in the owner's private custody records (the
same private workspace that holds the archives). The custody flags below were
renamed to the `SOURCE_SITE_*` prefix under the same direction (the prior
prefix named the site; the mapping is recorded in private custody records);
their values and semantics are unchanged. This amendment satisfies the ruling's
exact-source requirement by reference to private custody rather than by
public naming; it authorizes nothing new.

## Source

Six archives (`Level1.zip` … `Level6.zip`), 232 files: 226 lesson exports +
6 level READMEs of the "Arabic for English Speakers" (`en-ar`) curriculum,
levels A1–C2, each file self-declaring a `https://source-site.invalid/...` source URL.

## Publication-rights determination

**Controlling owner ruling** (owner §6A, 2026-07-29, recorded in the private
continuation archive as `TP-EXTERNAL-CURRICULUM-MAP-001`):

```text
SOURCE_SITE_FULL_CONTENT_REUSE_LICENSE: NOT_VERIFIED_BY_THIS_PROGRAMME
SOURCE_SITE_CURRICULUM_ABSORPTION: FUTURE_CLEAN_ROOM_TOPIC_AND_COVERAGE_ANALYSIS_ONLY
SOURCE_SITE_CONTENT_COPYING: NOT_AUTHORIZED
```

Never reproduce or closely paraphrase lesson prose, exercises, answer keys,
stories, distinctive examples, or non-public sequencing. Technically
accessible ≠ licensed; attribution alone does not permit redistribution.
This subtree is exactly the ruling's *permitted* objective: topic/coverage
metadata inventory + crosswalk + independently authored materials.

Required public-metadata provenance fields (per the ruling):

- **exact source**: `https://source-site.invalid/level/level-{1..6}` and per-lesson
  URLs recorded in the manifest;
- **capture date**: archives dated 2026-08-02 (owner-supplied exports);
- **public-accessibility status**: the recorded URLs are public pages; the
  archive files are an owner-supplied export, treated as non-public;
- **licensing status**: NOT_VERIFIED (see ruling above);
- **metadata-vs-content classification**: everything committed here is
  metadata (hashes, counts, titles/slugs/topic-heading labels, URLs) or
  independently authored derivation; zero content class;
- **no-copying declaration**: no lesson prose, exercise text, story text,
  distinctive example, or answer key is reproduced or closely paraphrased in
  this repository.

**Therefore the full lesson corpus is NOT committed.** Basis recorded without
private information: authority not established in-repo or in-lane at build
time. If the owner later records publication authority (they control the
source relationship), flipping custody is a bounded follow-up: commit the
corpus beside the manifest and set `custody_status` accordingly — no other
artifact changes shape.

## What IS committed (permitted metadata)

- per-file SHA-256, archive name, structural counts (words, passages,
  vocabulary rows, quiz questions, mistake sections);
- titles, slugs, source URLs (public addresses of public pages);
- section-heading strings — short factual labels reused as concept
  identifiers, not lesson prose;
- independently authored derived structures (registry, concept graph,
  crosswalks, claim ledger, packets, pilot) written from understanding, never
  paraphrase-laundered source text.

## What is NOT committed

Reading passages, translations, vocabulary glosses, quiz bodies,
common-mistake explanations, objectives prose — all body text. No bounded
excerpts are committed in this PR (none proved necessary; single Arabic words
under analysis in the pilot are linguistic objects, not prose excerpts).

## Reproducibility

`python tools/build_curriculum_l1l6.py --source-dir <dir with Level1..Level6>`
regenerates every generated artifact byte-identically when the private corpus
is present; `--check` diffs. The private corpus custody location is the
owner's workspace (recorded there, not here).
