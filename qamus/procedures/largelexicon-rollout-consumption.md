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
python tools/fusha_largelexicon_cli.py gate-rh-live-candidates --input candidates.jsonl --accepted-out accepted.jsonl --held-out held.jsonl --report-out gate-report.json
python tools/validate_largelexicon_table_reader.py --self-test
```

Do not consume `morphology_candidates[0]` directly. The stable top-level fields
from `analyze-token` / `analyze-card` are the safety contract:

- `analysis_status`;
- `safety_gate`;
- `safe_for_public_hover`;
- `safe_for_qamus_executor_autopromote`;
- `routes`.

Rows with `lexical_collision_requires_context`, `pending_context`, `ambiguous`,
or `safe_for_qamus_executor_autopromote=false` are worklist/packet inputs, not
deployment rows. Collision packets are useful because they name the missing
sarf/nahw/source proof, but they do not close a qword visually.

For already-authored RH-LIVE candidate JSONL, do not reuse the arbitrary-token
`analyze-token` / `analyze-card` autopromote flag as the executor decision. Run
the source-addressed gate instead:

```powershell
python tools/validate_rh_live_source_addressed_candidates.py candidates.jsonl --accepted-out accepted.jsonl --held-out held.jsonl --report-out gate-report.json
```

That gate may set `safe_for_qamus_executor_autopromote=true` only for rows that
already carry Qamus source-address trace, exact quran/wbw locs, source-clean
`public_preview`, segment-concat exactness, supported qamus-grammar-v1 classes,
and no unresolved context/source-crosswalk flags. It must not alter the rule
that arbitrary parser CLI output is non-autopromotable.

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

## VN-00 Public False-Closure Gate

The VN-00 public visual closure run on 2026-07-03 promoted Plan 17 from an
audit report into an executor gate. A Qamus row is not complete merely because
it has a hover shell or a qg class. It must pass public readback for every
visible cited-card qword.

The executor must fail page completion when any visible qword is:

- draft-only, flat, uncolored, or missing rich hover;
- weaker than a solved same-surface or equivalent-function peer;
- hiding root/form/person/number on a finite verb, especially when the page
  entry itself supplies the root family, as v016 does for `ر أ ى`;
- hiding subject/object/possessive suffixes such as `تُمْ`, `نِي`, `هِمْ`,
  `كُمْ`, `هُۥ`, or `هَا`;
- hiding derivative prefixes, feminine markers, plural suffixes, or
  tanwin/case endings;
- using a generic token/host shell for particles such as `هَلْ`, `مَا`,
  `وَمَا`, `إِنَّكُم`, or `لَعَلَّهُمْ`;
- hiding article-plus-host structure in rows such as `وَٱلشَّمْسَ`,
  `وَٱلْقَمَرَ`, `ٱلْءَايَةَ`, and `ٱلْعَيْنِ`.

Transclusion is no longer optional acceleration for these families. A richer
same-surface peer must produce a replacement/append candidate or an exact
exception row. Packet/accounting rows, terminal rows, and selected-word
coverage are not public visual closure.
