# Qurʾānic-anchor comparative evaluation plan

**Status:** research program (owner-adopted 2026-07-10). Companion to
`docs/QURANIC-ANCHOR-AND-FLYWHEEL.md` (the charter; epistemic levels defined there apply
here). Purpose: convert the project's central comparative thesis into falsifiable
experiments with defined metrics, controls, and failure conditions. Nothing in this plan
is claimed as already demonstrated; running it is future work gated by owner
prioritization, corpus licensing, and (for H7) a new representation layer.

General rules for every hypothesis:
- every rate reports numerator and denominator;
- abstention is a first-class outcome, never folded into error;
- per-corpus results are stratified (genre, period, vocalization status) before pooling;
- negative and null results are recorded with the same prominence as positive ones;
- religious texts are handled under the project's source-boundary and provenance rules;
  licensing of comparison corpora is resolved before ingestion (D-01-class questions are
  never converted into engineering defaults).

## H1 — Anchor integrity

*Prediction:* the Qurʾānic anchor scores higher than alternative seed corpora on source
integrity, before any annotation effort is counted.

Per corpus, measure:
- canonical source-address completeness (share of tokens with a stable `work:division:
  token` identity agreed across editions);
- token-identity stability (agreement of tokenization across at least two independent
  digitizations; churn rate under re-digitization);
- textual-version stability (variant density between accepted editions; for the Qurʾān,
  scoped to one riwāya per the charter §7 — qirāʾāt enter as explicit variants);
- vocalization coverage (share of tokens with full authoritative diacritization);
- provenance completeness (share of ingested facts whose exact source location resolves);
- proportion of lattice facts tied to exact source locations vs approximate ones.

## H2 — Inherited-analysis density

*Prediction:* the Qurʾān carries an unmatched density of independent, reviewable analysis.

Measure per corpus (sampled per token and per construction):
- independent lexical sources per token/construction;
- ṣarf analyses per token; naḥw analyses per construction;
- rhetorical/exegetical references per āyah-equivalent unit;
- proportion of occurrences with ≥2 reviewable competing analyses;
- disagreement density and adjudication density (how often sources disagree AND the
  disagreement is itself documented/adjudicated in the tradition).

## H3 — Flywheel yield

*Prediction:* review effort invested in the anchor compounds; equivalent effort on
alternatives compounds less.

Over sequential review waves (the project's VN-style windows), measure:
- certified facts produced per human review hour;
- share of later occurrences resolved from earlier certified facts (transclusion hits);
- projection precision (sampled adjudication) and projection abstention rate;
- unresolved-exception rate per wave;
- correction-propagation coverage (when a fact is repaired, what share of dependents are
  found and updated automatically — the full-carrier binding layer is the instrument);
- time saved per wave relative to independent row-by-row review (the project's own
  waves provide the longitudinal Qurʾānic series; alternative-corpus series are run under
  H6 controls).

## H4 — Ambiguity preservation

*Prediction:* lattice preservation beats early single-parse collapse, most strongly where
structured repetition provides controlled comparisons.

Compare the lattice system against an early-single-parse baseline (same inputs, collapse
at first ranking) on:
- candidate recall (is the correct analysis present in the retained set);
- final parse accuracy after contextual scoring;
- calibration (confidence vs adjudicated correctness);
- abstention quality (share of abstentions that were genuinely undecidable);
- retained valid alternatives (adjudicated-legitimate readings kept, not pruned);
- recovery rate when the initially leading candidate is adjudicated wrong.

## H5 — Cross-corpus transfer

*Prediction:* a Qurʾān-seeded engine transfers efficiently outward; provenance and
ambiguity discipline survive the transfer.

After Qurʾānic seeding, on held-out corpora — the Nawawī Forty, selected Ṣaḥīḥayn
portions, selected Classical prose, selected poetry, later scholarly prose — measure:
- reusable rule/fact coverage (share of tokens resolvable from Qurʾān-derived assets);
- new-vocabulary and new-construction rates;
- exception rate; human review time per certified fact;
- source-address/provenance degradation (does addressing precision survive corpora with
  weaker canonical structure);
- downstream parser and tutor performance on the new corpus.

## H6 — Comparative seed-corpus advantage (the central controlled experiment)

*Prediction:* the Qurʾānic conjunction retains its advantage after controls — the
advantage is intrinsic to the conjunction, not to accumulated historical effort.

Design constraints (mandatory):
- equal-sized seed corpora and equal review budgets (hours, reviewer expertise tiers);
- control for annotation effort (do NOT compare the fully developed Qurʾānic Qamus
  against an unannotated alternative and call the difference intrinsic);
- control for source availability, vocalization status, tokenization quality, genre,
  historical period, and evaluation budget;
- pre-registered metrics: H1/H2 integrity+density scores at seed time, H3 flywheel yield
  over N waves, H4 ambiguity metrics, H5 transfer metrics;
- candidate comparison seeds (subject to licensing/methodology review): a poetry dīwān
  corpus, a fully vocalized ḥadīth selection, a classical prose work with dense
  commentary tradition, and a non-religious canonical text of comparable size.

*Failure condition (stated plainly):* if an alternative seed sustains equal-fidelity
flywheel behavior under equal budgets, H6 is falsified as stated; the charter records it.

## H7 — Literary and rhetorical signature (requires a NEW representation layer)

*Prediction (preserved, not yet evaluable):* under a sufficient literary representation,
arbitrary Fusha composition classifies into the recognised categories (the sixteen poetic
metres, sajʿ forms, ordinary prose), while Qurʾānic composition yields a signature that
resists such reduction without loss or distortion.

The current ṣarf/naḥw lattice CANNOT establish literary-category irreducibility. Required
additional representations before any H7 run:
- prosody and the sixteen poetic metres (ʿarūḍ scansion over vocalized text);
- rhyme and cadence; sajʿ structures; fāṣila/āyah-boundary behavior;
- phonological patterning; rhetorical figures (badīʿ/bayān inventories);
- discourse organization; clause-boundary behavior;
- long-range recurrence; semantic and syntactic parallelism.

Evaluation shape: train/tune the classifier layer on representative labeled Fusha corpora
(poetry, sajʿ, oratory, epistles, ordinary prose), then measure (a) classification
stability on held-out human compositions, (b) the Qurʾān's fit/misfit under the same
classifier with distortion metrics, (c) ablations to identify which representational
features drive any separation. Until this layer exists and has been evaluated against
representative corpora, project documents do not claim that "arbitrary Fusha texts
consistently fall into known literary categories" or that the Qurʾān alone falls outside
them. The proposition is a planned hypothesis — not a discarded one.

## Reporting

Each hypothesis, when run, produces: a pre-registered design note; machine-readable
results with denominators; a human summary classifying every conclusion under the
charter's four epistemic levels; and an explicit statement of what was and was not
controlled. Results feed the charter's §4 (observed) or amend §5 (hypotheses), never
silently.
