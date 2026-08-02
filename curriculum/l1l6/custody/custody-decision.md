# L1–L6 curriculum source custody decision

Status: **private_source_custody_metadata_only** (controlling for every row in
`source-manifest.jsonl`).

## Source

Six archives (`Level1.zip` … `Level6.zip`), 232 files: 226 lesson exports +
6 level READMEs of the "Arabic for English Speakers" (`en-ar`) curriculum,
levels A1–C2, each file self-declaring a `https://kitabite.com/...` source URL.

## Publication-rights determination

- The Fusha repository contains **no** prior reference to kitabite.com and no
  record of a redistribution grant for this corpus.
- No licence file, terms grant, or owner authorization for **public**
  re-publication of the full lesson text was available to this lane.
- Attribution alone does not permit redistribution (PR-brief boundary).

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
