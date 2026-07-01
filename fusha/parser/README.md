# Fusha Parser Baseline

Status: transparent rule-ranked smoke baseline.

This directory implements P2/P4 groundwork for qamustyping2. It is not a trained dependency parser and not an arbitrary-text grammar checker. It consumes the repo-authored smoke morphology substrate and emits ranked candidates, abstention state, dependency/i'rab candidate rows, and evidence reports.

The `largelexicon` opt-in path now consumes committed Qamus-derived
source-clean full fact tables. This upgrades corpus coverage for Qamus/Qur'an
authoring support, but it does not by itself create a trained statistical
disambiguator or certified dependency/i'rab parser.

## Tools

```powershell
python tools\validate_fusha_parser_baseline.py --self-test
python tools\validate_fusha_evaluation.py --self-test
python tools\validate_parser_claims.py --self-test
python tools\validate_largelexicon_parser.py --self-test
python tools\validate_largelexicon_cli_contract.py --self-test
```

Optional statistical or neural layers are deliberately not implemented here. They need source-ledger approval, frozen splits, model cards, and metrics before any stronger claim.
