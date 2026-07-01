# tools/ — reusable, stdlib-only Arabic-research helpers

Small, dependency-free Python modules that the rest of Fusha builds on. Every tool
here is:

- **stdlib only** — no `pip install`, no third-party packages;
- **no live-app dependency** — nothing imports a server, a service, or a deploy
  path; these run anywhere Python 3 runs;
- **read-only / offline** — they read files *you* provide and compute keys or facts;
  they never write to a live system and never reach the network;
- **provenance-aware** — they help you *confirm* your own authored content against
  internal evidence; they never produce publishable gloss text. See
  [`../provenance/source-boundaries.md`](../provenance/source-boundaries.md).

## Import convention

Tools live under `tools/` and are imported as a package from the **repo root**.
Scripts that sit elsewhere add the repo root to `sys.path` first:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # -> repo root
from tools.normalize_ar import norm, norm_strict, bare, haraka_on, shadda_on, is_man_who
from tools.qac_adapter import QacAdapter
```

Run a tool's self-check directly:

```bash
python tools/normalize_ar.py     # prints: normalize_ar self-check OK
python tools/qac_adapter.py      # parses an inline 3-row demo TSV; prints: ... demo OK
```

---

## `normalize_ar.py` — Arabic normalization + harakāt helpers

Three match keys, each for a different job. **Display/scripture text is never
altered** — these produce *keys alongside* the text, never replacements for it.

| Function | Job |
|---|---|
| `norm(s)` | Lenient recall key: strips tashkīl, dagger-alef→ا, **drops hamza seats**, folds ى→ي / ة→ه. Good for *finding candidates*; **never** enough on its own to certify a root/sense. |
| `norm_strict(s)` | Like `norm` but **keeps the hamza seat** (أ إ ؤ ئ ء), so `إيمان ≠ أيمان`, `أن ≠ إنّ`. **Prefer this** (or a QAC fact) for scripture-facing matching. |
| `bare(s)` | Strips only marks, keeps every base letter distinct (ة≠ه، أ≠ا، ى≠ي). For enclitic detection. |

Plus the harakāt helpers that distinguish short function-word homographs (which the
lenient key collapses). The vowel that disambiguates sits on the **content** letter,
which may follow a و/ف proclitic — reading the first letter is the classic bug
(`وَمِنَ` "and from" mis-glossed as "and whoever").

| Helper | Use |
|---|---|
| `haraka_on(tok, target)` | The short vowel on the first `target` base letter (`''` if none). NFC-robust cluster scan. |
| `shadda_on(tok, target)` | Whether the first `target` letter carries a shadda (`لَمَّا` yes, `لِمَا` no). |
| `is_man_who(tok)` | `مَن` 'who' (no kasra on mīm) vs `مِن` 'from' (kasra, incl. `وَمِنَ`) vs `مَنَّ` 'to bestow' (shadda on nūn). |
| `ends_tanwin_alef(raw)` | Token ends in ʾalif al-tanwīn (ـًا), e.g. `قُرْءَانًا` — looks like stem+نا but isn't. |

**Do not redefine these.** Import them. They encode hard-won regressions; a private
re-implementation will drift and re-introduce the bugs they fix (see
`../provenance/source-boundaries.md` §5 for the full regression list).

## `qac_adapter.py` — read QAC root + POS from a local TSV (facts only)

A stdlib-only adapter over a **local** Quranic Arabic Corpus export that **you fetch
offline** — the QAC data is **never bundled** in this repo. It exposes only
*facts* (root and part-of-speech), which are uncopyrightable, to help you **confirm**
content you authored. It never returns or publishes any QAC text or gloss.

```python
from tools.qac_adapter import QacAdapter

qac = QacAdapter.from_tsv("/path/you/own/qac_morphology.tsv")  # YOUR file, not in repo
root = qac.get_root("2:255", "ٱللَّهُ")   # -> "ا ل ه"  (a fact, to cross-check ours)
pos  = qac.get_pos("2:255", "ٱللَّهُ")    # -> "PN"      (keeps a verb gloss off a name)
```

- **Keying:** `(ref, norm_strict(token))`. `ref` is `surah:ayah` (word-level
  `surah:ayah:word` also works); a verse-level ref reaches its word locations by
  prefix. Keyed on `norm_strict` (not `norm`) so hamza-distinct forms don't collapse.
- **Column-driven:** QAC releases differ; `from_tsv(...)` takes column names
  (`location_col`, `form_col`, `pos_col`, `root_col`/`features_col`). Defaults assume
  `location  form  tag  features` with the root inside a `ROOT:...` feature.
- **A miss returns `""`** — meaning *"QAC has no confident fact here"*. Treat that as
  "keep your authored value and consider `PENDING`", never as a license to invent.
- **`informed_by` is internal only.** Record `informed_by:'qac'` in internal schemas
  when a QAC fact agreed with yours; strip it before publication. The public hover
  artifact is always `{src:'qamus', kind:'authored', lang:'en'}` — never a QAC name.

The module's `__main__` parses a tiny inline 3-row **demo** TSV (hand-written, not
QAC data) to show the parsing contract without needing the real corpus.

---

## Largelexicon candidate tooling — opt-in Qamus-scale parser/hover samples

The `largelexicon` tools are an offline bridge from the 2,092-entry Qamus index to
source-clean parser, hover, and curriculum artifacts. They are deliberately opt-in:
existing smoke fixtures remain the default parser path, while largelexicon callers pass
`--db largelexicon` or consume the generated sample JSONL files.

| Tool | Purpose |
|---|---|
| `build_largelexicon_source_inventory.py` | Summarize Qamus entries/forms and emit reviewable lemma/form samples. |
| `build_largelexicon_morph_db.py` | Build the opt-in stem sample consumed by morphology analyzers. |
| `validate_largelexicon_source_ledger.py` | Ensure generated artifacts are registered in the canonical source ledger. |
| `validate_largelexicon_claim_boundary.py` | Block overclaims such as live progress or certified arbitrary parsing. |
| `validate_largelexicon_morph_db.py` | Validate stem/lemma source shape, roots, POS, and public-boundary safety. |
| `validate_largelexicon_parser.py` | Prove the opt-in parser path recognizes seeded largelexicon forms. |
| `build_largelexicon_qamus_mode_a_worklist.py` | Emit fixture worklist rows for every visible qword denominator work. |
| `project_largelexicon_qamus_hover_candidates.py` | Project source-clean hover candidates or exact source-crosswalk packets. |
| `validate_largelexicon_qamus_mode_a.py` | Validate Mode A worklist shape, trace, and denominator accounting. |
| `validate_largelexicon_qg_projection.py` | Validate public/private projection, qg classes, leaks, and packet exactness. |
| `build_largelexicon_flywheel_artifacts.py` | Convert projected rows into sarf/nahw/curriculum/parser flywheel tasks. |
| `validate_largelexicon_skill_curriculum_backfill.py` | Check that sarf, nahw, curriculum, and drills learned from the new layer. |

These tools may use internal evidence fields and local source-address rows, but public
hover output remains `src=qamus`, `kind=authored`, `lang=en`. They never SSH, deploy,
append a whitelist, restart services, or copy external gloss text.

---

## Adding a new tool here

1. stdlib only; no live-app / network / deploy imports.
2. Read-only on data the user supplies; never bundle external corpus data.
3. If it touches Arabic, reuse `normalize_ar.py` — don't re-implement keys.
4. Facts may be `informed_by` an internal source; published expression must be
   ours and authored. Keep external text out of inputs *and* outputs.
5. Give it a `__main__` self-check that runs offline.
