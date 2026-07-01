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
- `qamus/indexes/largelexicon/qamus-qword-denominator.full.jsonl`
- `qamus/indexes/largelexicon/source-clean-fact-tables.meta.json`
- `qamus/reports/largelexicon-source-inventory.json`
- `qamus/examples/mode_a_all_qword/largelexicon-qamus-mode-a-worklist.sample.jsonl`
- `qamus/examples/largelexicon/hover-candidates.sample.jsonl`
- `qamus/examples/largelexicon/flywheel-artifacts.sample.jsonl`

Every row is source-clean and candidate-scoped. Empty-root entries must carry an
explicit no-root reason. Function tokens route through nahw. Form/root/POS rows
route through sarf. All visible qword rollout rows are support artifacts for the
Qamus executor; they are not live deployment claims.

## Private Source Reuse Boundary

QAC, MCP/Tafsir, Quran.com/Quran Foundation, source photos, and other external
resources may inform private caches and review packets when their terms allow
it, but their raw rows, labels, prose, paths, or source names do not appear in
public hover fields or committed Qamus fact tables. The committed full tables in
this lane are generated from `qamus/data/current/entries.jsonl` and carry only
`src=qamus`, `kind=authored`, `lang=en`.
