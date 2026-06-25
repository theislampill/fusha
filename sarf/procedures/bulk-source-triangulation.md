# Procedure — bulk source-triangulation morphology gate

**Invoke when:** a pending-token table is being used to close qamus-highlight gaps in bulk.

**Input:** one row per token with `loc`, vocalized `surface`, `nk`, QAC root/POS, Qamus root entry, host entry,
homograph flag, function/proper flags, pending code, and proposed lane.

**Classify each row:**
1. **`auto_safe`** only when the row has QAC root + POS agreement, one applicable Qamus sense/form, no
   `norm_strict` collision, no homograph/proper/function-word flag, and no syntax-sensitive trigger. Emit an
   authored hover decision plus provenance sidecar.
2. **`two_vote_required`** when the form/root is plausible but the row depends on derived-form choice, voice,
   person, nominal-vs-verbal shape, possessive host handling, multi-sense root, or a key shared by different
   word/POS/person states. Emit a request row, not a decision.
3. **`owner_gated`** when a new Qamus entry, source photo, entry repair, or live index rebuild is needed.
   Produce a review packet with blank authored fields where human wording is required.
4. **`pending`** when the row lacks decisive root/POS/form evidence or carries an unresolved homograph,
   proper-noun, source, or grammar blocker.

**Forbidden shortcuts:** adding a surface form because `norm()` matches; putting a verb gloss on a noun or
nominal derivative; treating an index miss as a free reindex without checking POS and sense; copying any external
gloss text into a public artifact.

**Output fields:** `loc`, `surface`, `nk`, `qac_root`, `qac_pos`, `host_entry`, `root_entry`, `lane`,
`gate`, `reason`, `allowed_for_hover`, and `review_status`.

**Test:** validate the table and every emitted batch separately: source-triangulation validator, deterministic
hover validator, two-vote request validator, and artifact ergonomics. A clean table is not the same thing as a
certified gloss batch.
