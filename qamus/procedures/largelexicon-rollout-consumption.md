# Largelexicon Rollout Consumption

The Qamus executor may consume largelexicon artifacts as support inputs.

Allowed inputs:

- source inventory report;
- lemma/form/stem samples or full generated outputs under `out/`;
- all visible qword Mode A worklist rows;
- parser candidate outputs;
- flywheel/curriculum packets.

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
parser candidate output as live rich-hover deployment.
