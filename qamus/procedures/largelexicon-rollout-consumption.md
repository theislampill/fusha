# Largelexicon Rollout Consumption

The Qamus executor may consume largelexicon artifacts as support inputs.

Allowed inputs:

- source inventory report;
- lemma/form/stem samples;
- allowlisted committed source-clean full fact tables:
  `fusha/lexicon/largelexicon/lemma-source.full.jsonl`,
  `fusha/lexicon/largelexicon/form-source.full.jsonl`,
  `fusha/morphology/data/largelexicon-stems.full.jsonl`, and
  `qamus/indexes/largelexicon/qamus-qword-denominator.manifest.json`
  with its shard directory and entry-shard index;
- qword denominator source-card repair packets such as
  `qamus/indexes/largelexicon/qamus-qword-denominator.source-card-repair.json`;
- all visible qword Mode A worklist rows;
- parser candidate outputs;
- flywheel/curriculum packets.

Use the local interface first, not ad hoc file spelunking:

```powershell
python tools/fusha_largelexicon_cli.py analyze-token --surface "..."
python tools/fusha_largelexicon_cli.py analyze-card --input card.jsonl
python tools/fusha_largelexicon_cli.py project-hover --input worklist.jsonl --out candidates.jsonl
python tools/fusha_largelexicon_cli.py validate-mode-a --input worklist.jsonl
python tools/validate_largelexicon_table_reader.py --self-test
```

For qword denominator reads, prefer `tools/largelexicon_table_reader.py`.
The table is a single logical Project-Xanadu-style graph surface even though it
is physically sharded. A row must remain traceable forward
entry/card/qword -> shard/payload/crosswalk and reverse row_id/entry -> shard
-> entry/card/source. Do not recreate a second qword denominator database.

Largerollout3 adds two required executor-adoption surfaces:

```powershell
python tools/build_qamus_source_card_repair_worklist.py
python tools/validate_qamus_source_card_repairs.py --self-test
python tools/build_largelexicon_qword_crosswalk.py
python tools/validate_largelexicon_qword_crosswalk.py --self-test
python tools/validate_largelexicon_transclusion.py --self-test
python tools/validate_largelexicon_executor_adoption.py --self-test
```

The crosswalk manifest is not a deployment queue. It is an all-visible-qword
status surface. Rows with missing canonical Qur'an/WBW locs are exact
`source_crosswalk_packet_ready` rows until Arabic-surface matching and
uniqueness checks produce an accepted crosswalk. The first source-card/example repair smoke case is
`n993 / 2a071cd0b50e / مَلْجَأ / pg443.jpeg / 42:47`; it must be source-card
repaired or exact-owner-packeted before any claim that all 2,092 entries have
qword rows.

Every executor-consumed row must preserve bidirectional transclusion:

- forward trace: entry/card/qword -> source-card/crosswalk -> sarf/nahw route -> public projection -> rendered span;
- reverse trace: rendered span -> public projection -> sarf/nahw route -> source-card/crosswalk -> qword/card/entry.

Rows without forward trace or reverse trace are repair packets, not closure evidence.

This is not live qamus progress; it is repo-side source-clean preparation for
later executor-controlled deployment and public readback.

All-visible-qword closure is stricter than selected-word closure. A selected
word may be complete while the page remains visually sparse. Existing
undersegmented hovers require a replacement lane with backup/readback; append
only cannot close them.

Executor-owned gates:

- live whitelist backup;
- append versus replacement decision;
- service reload/restart;
- public DOM/mobile readback;
- source/runtime parity;
- DUV/static assets;
- rollback;
- final tranche closure claims.

Largelexicon rows must resolve to one of:

- candidate for executor validation;
- no-op/already-covered;
- replacement-needed packet;
- source-address/crosswalk repair packet;
- source-card/example repair packet;
- owner packet;
- scholar/i'rab packet;
- validator/schema/tool patch packet;
- unsafe/high-risk packet.

Do not treat selected-word closure as all visible qword closure. Do not treat
parser candidate output as live rich-hover deployment. Do not use raw QAC/MCP/API
payloads as public hover provenance; external source evidence remains private
and must project into source-clean Qamus-authored fields.
