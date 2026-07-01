# Largelexicon Source Ledger

The canonical source ledger remains `sources/source-artifact-ledger.json`.
Largelexicon extends that ledger; it does not create a competing provenance
system.

## Sources

| Source | Use | Public output |
| --- | --- | --- |
| `qamus/data/current/entries.jsonl` | Qamus-authored entry, sense, usage, and form inventory | allowed only as authored Qamus candidate data |
| `qamus/data/current/entries.min.jsonl` | compact count/cross-check surface | internal count evidence |
| external NLP/reference systems | architecture comparison or internal evidence only | never public wording or source labels |
| Tafsir MCP / QAC / Quran.com-style sources | optional internal sarf/nahw/i'rab/source-address checks | never public provenance |

## Generated Artifacts

Committed artifacts are source-clean samples, reports, and the explicitly
allowlisted Qamus-derived full fact tables. Raw external acquisition caches
remain private/out-of-repo. A full generated table is committable only if it is
listed in `fusha/lexicon/largelexicon/source-clean-table-allowlist.json` and
`tools/validate_largelexicon_source_ledger.py --self-test` passes.

- `fusha/lexicon/largelexicon/lemma-source.sample.jsonl`
- `fusha/lexicon/largelexicon/form-source.sample.jsonl`
- `fusha/lexicon/largelexicon/lemma-source.full.jsonl`
- `fusha/lexicon/largelexicon/form-source.full.jsonl`
- `fusha/morphology/examples/largelexicon-stems.sample.jsonl`
- `fusha/morphology/data/largelexicon-stems.full.jsonl`
- `qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json`
- `qamus/indexes/largelexicon/qamus-qword-denominator.entry-shard-index.json`
- `qamus/indexes/largelexicon/qamus-qword-denominator.source-card-repair.json`
- `qamus/indexes/largelexicon/qword-denominator/*.jsonl`
- `qamus/indexes/largelexicon/qamus-qword-crosswalk.manifest.json`
- `qamus/indexes/largelexicon/qword-crosswalk/*.jsonl`
- `qamus/repairs/source-card-examples/source-card-repair-worklist.jsonl`
- `qamus/repairs/source-card-examples/source-card-repair-worklist.meta.json`
- `qamus/indexes/largelexicon/source-clean-fact-tables.meta.json`
- `qamus/reports/largelexicon-source-inventory.json`
- `qamus/examples/mode_a_all_qword/largelexicon-qamus-mode-a-worklist.sample.jsonl`
- `qamus/examples/largelexicon/hover-candidates.sample.jsonl`
- `qamus/examples/largelexicon/flywheel-artifacts.sample.jsonl`

Every row is source-clean and candidate-scoped. Empty-root entries must carry an
explicit no-root reason. Function tokens route through nahw. Form/root/POS rows
route through sarf. All visible qword rollout rows are support artifacts for the
Qamus executor; they are not live deployment claims.

## Sharded Qword Denominator

The all-visible-qword denominator is one logical table, stored as addressable
JSONL shards behind `qamus-qword-denominator.manifest.json`. Consumers should
use `tools/largelexicon_table_reader.py` or the manifest, not hard-code shard
filenames. The manifest preserves forward edges from entry/card/qword to source
handles and reverse edges from `row_id`/entry back to the shard. Each shard has
a SHA-256 and row count; the entry-shard index lets an executor jump directly to
one entry without scanning 117,117 rows.

The manifest distinguishes the 2,092-entry Qamus target from entries that have
tokenizable example rows in `qamus/data/current/entries.jsonl`. If an entry is
present in Qamus but has no usage examples to tokenize, it appears in
`qamus-qword-denominator.source-card-repair.json`. Current known repair:
`n993` / `مَلْجَأ` has a source-card hint for `pg443.jpeg` and `42:47`, because
the source card shows Qur'anic usage while the current entry export has
`examples: []`.

## Source-Card Repair And Crosswalk Tables

`tools/build_qamus_source_card_repair_worklist.py` projects source-card repair
rows into `qamus/repairs/source-card-examples/` for owner/source confirmation.
The worklist is not a hover payload and not live progress; it preserves the
entry/source-card edge that must be repaired before the affected entry can join
the all-visible-qword denominator.

`tools/build_largelexicon_qword_crosswalk.py` turns every denominator qword into
a crosswalk-status row. Rows with both canonical Qur'an and WBW addresses may
eventually become accepted crosswalks. Rows without those addresses remain
`source_crosswalk_packet_ready`; they are explicit work packets, not deployable
rich-hover rows. This preserves the bidirectional path:

`entry/card/qword -> crosswalk status -> repair packet/candidate`

and the reverse path:

`crosswalk row -> qword_row_id -> entry/card/source dependencies`.

## Private Source Reuse Boundary

QAC, MCP/Tafsir, Quran.com/Quran Foundation, source photos, and other external
resources may inform private caches and review packets when their terms allow
it, but their raw rows, labels, prose, paths, or source names do not appear in
public hover fields or committed Qamus fact tables. The committed full tables in
this lane are generated from `qamus/data/current/entries.jsonl` and carry only
`src=qamus`, `kind=authored`, `lang=en`.
