# Largelexicon Rollout Consumption

The Qamus executor may consume largelexicon artifacts as support inputs.

Allowed inputs:

- source inventory report;
- lemma/form/stem samples;
- allowlisted committed source-clean full fact tables:
  `fusha/lexicon/largelexicon/lemma-source.full.jsonl`,
  `fusha/lexicon/largelexicon/form-source.full.jsonl`,
  `fusha/morphology/data/largelexicon-stems.full.jsonl`, and
  `qamus/indexes/largelexicon/qamus-qword-denominator.full.jsonl`;
- all visible qword Mode A worklist rows;
- parser candidate outputs;
- flywheel/curriculum packets.

Use the local interface first, not ad hoc file spelunking:

```powershell
python tools/fusha_largelexicon_cli.py analyze-token --surface "..."
python tools/fusha_largelexicon_cli.py analyze-card --input card.jsonl
python tools/fusha_largelexicon_cli.py project-hover --input worklist.jsonl --out candidates.jsonl
python tools/fusha_largelexicon_cli.py validate-mode-a --input worklist.jsonl
```

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
- owner packet;
- scholar/i'rab packet;
- validator/schema/tool patch packet;
- unsafe/high-risk packet.

Do not treat selected-word closure as all visible qword closure. Do not treat
parser candidate output as live rich-hover deployment. Do not use raw QAC/MCP/API
payloads as public hover provenance; external source evidence remains private
and must project into source-clean Qamus-authored fields.
