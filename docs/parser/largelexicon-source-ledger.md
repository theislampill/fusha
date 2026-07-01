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

Committed artifacts are samples and reports. Full generated outputs belong under
`out/largelexicon/`, which is gitignored.

- `fusha/lexicon/largelexicon/lemma-source.sample.jsonl`
- `fusha/lexicon/largelexicon/form-source.sample.jsonl`
- `fusha/morphology/examples/largelexicon-stems.sample.jsonl`
- `qamus/reports/largelexicon-source-inventory.json`
- `qamus/examples/mode_a_all_qword/largelexicon-qamus-mode-a-worklist.sample.jsonl`
- `qamus/examples/largelexicon/hover-candidates.sample.jsonl`
- `qamus/examples/largelexicon/flywheel-artifacts.sample.jsonl`

Every row is source-clean and candidate-scoped. Empty-root entries must carry an
explicit no-root reason. Function tokens route through nahw. Form/root/POS rows
route through sarf. All visible qword rollout rows are support artifacts for the
Qamus executor; they are not live deployment claims.
