# Fusha Parser Claim Boundary

The current Fusha parser/checker work is a dependency-free smoke substrate for Qamus Mode A and learner-facing parser development.

It is not live Qamus progress, not arbitrary-text certification, not a trained dependency parser, and not equivalent to CAMeL Tools, MADAMIRA, or Stanza.

Allowed claims require matching validators:

- Mode A fixture mechanics: `tools/validate_qamus_mode_a_adoption.py --self-test`
- morphology smoke substrate: `tools/validate_fusha_morph_db.py --self-test` and `tools/eval_fusha_morphology.py --self-test`
- rule-ranked parser baseline: `tools/validate_fusha_parser_baseline.py --self-test`
- eval/model-card/source-ledger gates: `tools/validate_fusha_evaluation.py --self-test`
- public wording: `tools/validate_parser_claims.py --self-test`

Stronger claims require new source-ledger review, split manifests, metrics, model cards, and owner authorization.
