# Source Ledger And Split Policy

`sources/source-artifact-ledger.json` is the canonical source ledger for the
parser/checker substrate. Later P4 release and evaluation work extends this
same ledger; it must not create a competing source ledger.

## Freshness Fields

Generated artifacts must carry:

- `generated_at`
- `generated_by`
- `source_head`
- `source_branch`
- `supersedes`
- `stale_after`
- `status`

An artifact is stale when the active checkout does not match its source head or
branch, when a newer artifact supersedes it, or when `stale_after` has passed.

## External Source Policy

External sources may be used as internal evidence and comparison data. They are
not public provenance for Qamus hovers.

Permitted evidence lanes include:

- Qur'an text/WBW source adapters
- Quranic Arabic Corpus style morphology or dependency evidence
- Quran.com or Quran Foundation style word data
- Tafsir MCP / Tafsir Center i'rab evidence when available
- UD Arabic treebanks for parser-shape research
- CAMeL Tools, CAMeL Morph, MADAMIRA, camelparser2, and Stanza as comparison
  systems or future evaluation references

Public Qamus fields must remain source-clean:

- `src=qamus`
- `kind=authored`
- `lang=en`
- no external source labels
- no MCP labels
- no local or server paths
- no copied external gloss prose

## Location Rule

Do not trust an external `S:A:W` word number by itself. Match Arabic surface in
the verse, require uniqueness, and emit a source-address crosswalk when the
display-local address and canonical Qur'an/WBW address differ.

## Split Policy

Evaluation splits must be named, source-ledgered, and non-overlapping by stable
row id. A model, rule set, or parser claim may cite a split only when:

- the split file exists;
- it records generation metadata and source head;
- the source ledger includes it;
- the metric report names the split;
- the model card or rule card states the claim boundary.

Smoke fixtures are allowed for P0.5/P1/P2 mechanics. They do not certify broad
coverage or arbitrary text.
