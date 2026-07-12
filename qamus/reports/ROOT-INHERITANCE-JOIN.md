# Root-inheritance + global lexeme join — transclusion lattice (T13)

**Branch:** `lattice-root-inherit` · **base:** origin/main `272b5e0` (T12 `fact-lattice-t12` already merged)
**Whitelist snapshot (read-only):** `rh_live_01_beta_whitelist.jsonl`, 34,318 rows, sha256 `18675606fda1bce3…` (snapshotted before instrumentation; another lane deploys mid-task — this sha differs from T12's `1c06d85a`).
**Entry axis:** `qamus/data/current/entries.jsonl` — all 2,092 lexemes (100 p / 947 v / 1,045 n).
**Corpus/verse marks + dagger-alef:** the join key is vendored **verbatim** from the deployed `services/qamus_wbw/normalize.py::norm` (do not reinvent — a divergent key would silently disagree with the live word-by-word lookup).

The lattice takes **certified roots** (qamus entry headword/usage.forms, and the certified rooted whitelist rows themselves) and projects them onto **rootless** occurrences by transclusion. **Candidate-generation only** — every projection stays `certification_state=candidate` until the 2-vote / review gate. **Pattern alone never certifies a root (DR-2, `sarf-pattern-never-certifies-root`): inheritance is only ever from an ATTESTED source.**

## New projectors (registered in `qamus/lattice/registered-projectors.json`)

| id | kind | rule keys (excerpt) |
|---|---|---|
| `sarf.root_inherit_transclusion.v1` | root_inheritance | pattern-never-certifies-root, root-entry-pages-transclusion, broken-plural-shares-root, certifiable-participle-host |
| `sarf.note_normalize.v1` | note_normalization | same-surface-rich-peers-transclusion, blank-beats-wrong-root |
| `sarf.suffix_fempl_segmentation.v1` | suffix_segmentation | root-radical-not-clitic, broken-plural-shares-root |

## P-ROOT-INHERIT — tiered inheritance (conservative auto set)

Match key = NFC, harakat/tanwin/annotation-stripped, alif-wasla + **dagger-alef → plain alif** (so `مُسَخَّرَٰتٍ` matches the entry form `مُسَخَّرَات`), hamza/alif-maqṣūra **preserved** (root-significant). A lexical head = a `STEM`/`TOK`/`*_stem`/proper-noun segment. Rootless = the morphline asserts no `root X Y Z`.

Inheritance sources, priority order (tiers = edge types):
- **tier-0** the qamus entry headword / usage.form the lexeme matches (the dictionary's own assertion — strongest);
- **tier-A** the same match confirmed by the row's own carrier `entry_id` (self-join). **NB:** `entry_id` alone is only an *example-context* link — `فَوْقَكُمُ` carries the `أخذ` entry's id — so a carrier is used **only when the surface is actually a form of that entry** (DR-2). Bare `entry_id` never asserts a root.
- **tier-B** a certified same-surface sibling; **tier-C** a certified same-stem sibling.

Guards (fail-closed): within-root ambiguity (قل→قول/قلل) → held; cross-source root conflict → never_auto_resolve; same-surface homograph → 2-vote; jāmid/contested category → held; **divine-name exclusion** (ٱللَّه/ٱلرَّحِيم tokens).

### Instrumentation (over the 34,318-row snapshot)

| Bucket | Rows |
|---|---:|
| Rootless rows (no `root` in morphline) | 24,171 |
| — rootless **function/no-stem** (particles, pronouns — legitimately rootless) | 19,116 |
| **Rootless lexical-head rows (target population)** | **5,055** |
| — divine-name excluded | 718 |
| — **AUTO inheritable** (tier0 1,484 · tierA 307 · tierB 610 · tierC 276) | **2,677** |
| — review-routed (homograph 222 · within-root 67 · cross-source-conflict 41) | 330 |
| — authoring-first (no attested source) | 1,330 |

**Acceleration:** of the 4,337 eligible (non-divine) rootless lexical-head rows, **2,677 (61.7%) auto-inheritable + 330 (7.6%) review-routed = 3,007 (69.3%) inheritable** by transclusion; only **1,330 (30.7%) need authoring**.

### Worked examples (candidate records verbatim — see `root-inheritance-instrumentation.json` → `worked_examples`)

- **36:70:4 الْكَافِرِينَ** → root **ك ف ر**, tier0, guard null. Evidence: entry form `الْكَافِرِينَ`/`كَافِرٌ`.
- **16:3:1 خَلَقَ** → root **خ ل ق**, tier0. (Also attested by same-surface + same-stem siblings.)
- **38:14:6 فَحَقَّ** → root **ح ق ق**, tier0 (TOK `حَقَّ` matches entry headword `حَقَّ`; the certified sibling `حَقَّتْ` 39:71:30 corroborates).
- **7:54:23 مُسَخَّرَٰتٍۭ** → root **س خ ر**, tier0-forms (dagger-alef normalized), **pattern مُفَعَّل / Form II derived participle** (POS read from the attested entry form shape).

## P-NOTE-NORMALIZE — deterministic per-class notes

Boilerplate set: *"visible piece accounted"*, *"no unsupported public source label"*, *"function/context contribution preserved"*. Replaced by per-role templates (ART → "definite article ال" / "definiteness marker"; PL ـين → "sound masculine plural suffix (accusative/genitive)" / "plural agreement"; etc.). A **STEM/TOK head requires the P-ROOT-INHERIT chain** ("`<pos>` from root X") — otherwise left for authoring. Over the snapshot: 27 boilerplate segments reachable, 7 replaced deterministically, 1 stem awaiting the root chain (the rest are tanwīn-noun/particle roles with no safe template — left untouched, never fabricated).

## P-SUFFIX-FEMPL — feminine-plural / dual segmentation (closes C5 gap O-2)

Single-token rootless rows whose surface ends in ـات (+ tanwīn variants) or dual/plural ـان/ـين, where the remainder is an attested stem → project STEM + PL-F/PL-DL. Guard: a trailing ـات that is a **radical ت** (`sarf-root-radical-not-clitic`) → 2-vote. Snapshot: **fem-plural 10 reachable (9 auto, 1 radical-ت guarded), dual/plural 27 auto** — 37 candidates where the O-2 tanwīn/niswa detector previously produced zero.

## GLOBAL BIDIRECTIONAL LEXEME JOIN (occurrence ↔ entry)

All 34,318 rows joined against all 2,092 entries in both directions with the vendored wbw content key + a deterministic de-proclitic pass (و/ف/ب/ك/ل/ت/س + ال, tagged as `derived` edges). Tiers become **typed edges** (headword/form/sense/derived). This subsumes P-ROOT-INHERIT tier-0/A as one index join.

### occurrence → entry

| Metric | Value |
|---|---:|
| Rows matching ≥1 entry lexeme | **20,413 / 34,318 (59.5%)** |
| Rooted rows matched | 7,259 |
| — coherent (entry confirms the row's root) | 5,008 |
| — **conflict (row root ≠ entry root)** → 2-vote/review | **464** |
| Rootless rows matched | 13,154 |
| — **inheritable auto (single unambiguous root)** | **5,201** |
| — inheritable multi-root → 2-vote | 148 |
| — matched to root-less/jāmid entries (linkage only) | 9,592 |
| Per-section rows matched | v 10,352 · n 7,971 · p 4,473 |

The **5,201 single-root inheritable pool is the superset of P-ROOT-INHERIT's tier-0** (as predicted): the join is the reachable ceiling under the deployed content key; P-ROOT-INHERIT's 2,677 is the fail-closed auto subset that also survives the stricter hamza-preserving key + guards. Honest coverage note: 59.5% (not a super-majority) because the 2,092-entry dictionary is a *selected* lexicon; deeper subject/object-clitic stripping (the full wbw oracle) would raise it but is out of scope for a deterministic candidate join.

### entry → occurrence

| Metric | Value |
|---|---:|
| Entries with ≥1 recognized occurrence | **1,740 / 2,092 (83.2%)** |
| Orphan entries (no occurrence) | 352 (n 157 · v 155 · p 40) |

### Edges (`lexeme-join-edges.jsonl`, source-address-graph shape)

24,391 typed edges — headword 10,050 · form 10,309 · derived 3,721 · sense 311. Relations: root_confirms 5,014 · root_inherit_candidate 5,529 · root_conflict 804 · linkage_only 13,044. Entry→occurrence lists in `entry-occurrence-edges.jsonl` (1,740 entries).

### Acceleration vs the rootless population & the N-CONS-01 incoherence set

- **Rootless population (~22,344 / measured 24,171):** the join recognizes 13,154 rootless rows as dictionary lexemes; **5,201 are single-root auto-inheritable** and 148 route to 2-vote — a deterministic transclusion path off the authoring critical path.
- **N-CONS-01 incoherence (4,001):** the join surfaces **464 rows (804 edges)** where a row's asserted root *disagrees* with the entry that attests the same surface — a concrete, machine-detected slice routed to 2-vote/review (`root_conflict` edges), never auto-resolved.

## Reproduce

```bash
python3 tools/lattice_projectors.py self-test            # 21 red-first checks
python3 -m unittest tools.test_lattice_projectors         # 13 unit tests
python3 tools/lattice_projectors.py inherit --whitelist <rh_live_01_beta_whitelist.jsonl> \
  --out-instrumentation qamus/reports/root-inheritance-instrumentation.json \
  --out-ledger qamus/lattice/root-inheritance-ledger.jsonl
python3 tools/lattice_projectors.py join --whitelist <rh_live_01_beta_whitelist.jsonl> \
  --out-instrumentation qamus/reports/lexeme-join-instrumentation.json \
  --out-edges qamus/lattice/lexeme-join-edges.jsonl \
  --out-entry-occurrences qamus/lattice/entry-occurrence-edges.jsonl
```
