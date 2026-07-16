# Canonical Occurrence-to-Appearance Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the canonical occurrence-to-appearance JSONL index, its parity validator, regression gate, and truthful closure report.

**Architecture:** The builder reads the sibling whitelist and entry store, groups all source evidence by canonical `loc`, hashes only the current analysis projection, and emits one deterministic record per location. The validator independently checks source duplicate hashes and artifact appearance/hash consistency; it never equates different locations merely because their normalized surfaces match.

**Tech Stack:** Python 3 standard library, JSONL, SHA-256, `unittest`, existing `tools/check_regressions.py` subprocess gate.

## Global Constraints

- Use the user-provided linked checkout only; preserve the no-push boundary.
- Commit messages use the `idx:` prefix.
- Read the sibling `data/rh_live_01_beta_whitelist.jsonl` as the reader surface; do not mutate it or `entries.jsonl`.
- Use one canonical record per `loc`; identical normalized surfaces at different `loc` values, including across ayahs, remain allowed.
- Projection hashes cover exactly `segments`, `glosses`, `morphline`, `root`, and `facts`.
- Entry-store ayah-only refs are not projected to every word without an entry-page source relationship; unresolved attribution is reported.
- JSONL is UTF-8, one object per line, sorted deterministically, with a trailing newline.

---

### Task 1: Red-first occurrence and parity tests

**Files:**
- Create: `tools/test_occurrence_appearance_index.py`

**Interfaces:**
- Consumes: `build_occurrence_appearance_index.projection_hash`, `build_occurrence_appearance_index.build_index`, and `validate_appearance_parity.validate_records`.
- Produces: executable red-first fixtures covering reader/entry appearances, hash changes, allowed same-surface different-location analyses, and rejected same-location forks.

- [ ] **Step 1: Write failing tests**

```python
def test_same_loc_divergent_projection_is_rejected():
    rows = [
        {"loc": "1:1:1", "surface": "أ", "segments": [{"surface": "أ", "gloss_contribution": "a"}], "morphline": "A", "root": None, "sarf_facts": None, "nahw_facts": None, "token_contribution_gloss": "a", "contextual_phrase_gloss": "a"},
        {"loc": "1:1:1", "surface": "أ", "segments": [{"surface": "أ", "gloss_contribution": "the"}], "morphline": "B", "root": None, "sarf_facts": None, "nahw_facts": None, "token_contribution_gloss": "the", "contextual_phrase_gloss": "the"},
    ]
    report = validate_records(build_index(rows, []), source_rows=rows)
    assert not report.ok
    assert "divergent" in " ".join(report.errors)

def test_same_surface_different_locations_are_allowed():
    rows = [row("39:63:3", "السَّمَاوَاتِ", "segmented"), row("22:18:9", "ٱلسَّمَٰوَٰتِ", "fused")]
    report = validate_records(build_index(rows, []), source_rows=rows)
    assert report.ok
```

- [ ] **Step 2: Run the focused tests and verify the expected missing-implementation failure**

Run: `python -m unittest tools.test_occurrence_appearance_index -v`

Expected: FAIL because the new builder and validator modules do not yet exist; no production implementation is written before this red check.

- [ ] **Step 3: Commit the design documents**

Run: `git add docs/superpowers/specs/2026-07-16-occurrence-appearance-index-design.md docs/superpowers/plans/2026-07-16-occurrence-appearance-index.md; git commit -m "idx: record occurrence appearance index design"`

### Task 2: Deterministic index builder

**Files:**
- Create: `tools/build_occurrence_appearance_index.py`
- Test: `tools/test_occurrence_appearance_index.py`

**Interfaces:**
- Produces `projection_payload(row) -> dict`, `projection_hash(row) -> str`, `build_index(whitelist_rows, entries) -> list[dict]`, and CLI options `--whitelist`, `--entries`, `--output`, `--self-test`.

- [ ] **Step 1: Implement the exact projection hash payload and source-key resolver**

Use sorted-key compact JSON encoded as UTF-8. Use direct IDs first, then `/e/<id>` URL paths, then numeric-normalized letter-plus-number source keys. Preserve explicit fixture `glosses`/`facts`; otherwise map current fields to the `token_contribution_gloss`/`contextual_phrase_gloss` and `sarf_facts`/`nahw_facts` pairs.

- [ ] **Step 2: Implement reader and entry-page appearance collection**

Create one `reader` appearance for every whitelist row. Add one `entry_example` appearance for each row with a real entry-page signal, resolving its entry ID when possible. Keep appearances deterministic and deduplicate only identical appearance objects.

- [ ] **Step 3: Implement conservative entry-store ref reconciliation**

Parse exact three-part refs directly. For two-part ayah refs, intersect the entry’s resolved source-key/ID with whitelist rows in that ayah; record unresolved refs when no exact entry-page row exists. Add sorted unique entry IDs to `entry_relationships`.

- [ ] **Step 4: Run the focused tests and verify green**

Run: `python -m unittest tools.test_occurrence_appearance_index -v`

Expected: all focused builder and parity tests PASS.

### Task 3: Validator and red-first self-test

**Files:**
- Create: `tools/validate_appearance_parity.py`
- Modify: `tools/test_occurrence_appearance_index.py`

**Interfaces:**
- Produces `validate_records(records, source_rows=None) -> ValidationReport`, `render_report(report) -> str`, and CLI options `--index`, `--whitelist`, `--self-test`.

- [ ] **Step 1: Validate artifact structure and inherited/explicit appearance hashes**

Reject malformed records, duplicate canonical records, non-hex 64-character hashes, count mismatches, unsupported `surface_kind` values, and explicit appearance hashes that differ from the parent record hash.

- [ ] **Step 2: Validate source duplicate analysis parity**

Group source rows by `loc`; permit repeated identical hashes and reject any location whose hashes differ. Separately compute normalized surface plus ayah groups only for a diagnostic allowed-count, never as a failure key.

- [ ] **Step 3: Add validator self-test fixtures**

The self-test must fail on a same-location fork and pass on the real corpus plus the same-surface/different-location pair. It must print stable `ok`/`FAIL` lines and return nonzero if any expected red-first behavior is missing.

- [ ] **Step 4: Run both self-test surfaces**

Run: `python tools/validate_appearance_parity.py --self-test` and `python -m unittest tools.test_occurrence_appearance_index -v`.

Expected: the synthetic fork is reported as an expected failure inside the self-test, while the self-test process and focused suite exit 0.

### Task 4: Artifact, harness, and report

**Files:**
- Create: `qamus/indexes/occurrence-appearances.jsonl`
- Create: `IDX-REPORT.md`
- Modify: `tools/check_regressions.py`

**Interfaces:**
- The committed artifact is regenerated by `tools/build_occurrence_appearance_index.py`.
- The regression gate invokes the validator self-test and the real artifact/source validation with `run_text` and `check`, matching existing harness conventions.

- [ ] **Step 1: Build the committed artifact from the sibling data inputs**

Run: `python tools/build_occurrence_appearance_index.py --whitelist ..\data\rh_live_01_beta_whitelist.jsonl --entries ..\data\entries.jsonl --output qamus\indexes\occurrence-appearances.jsonl`

Expected: one deterministic JSON object per whitelist `loc`, no mutation under `data/`.

- [ ] **Step 2: Wire the F-B/F-C gate**

Add one bounded gate block near the end of `tools/check_regressions.py` that checks the validator self-test marker and the real validator exit code/marker, with a harness-error branch that calls `check(..., False)`.

- [ ] **Step 3: Run the real validator and capture exact output**

Run: `python tools/validate_appearance_parity.py --index qamus\indexes\occurrence-appearances.jsonl --whitelist ..\data\rh_live_01_beta_whitelist.jsonl`

Expected: zero divergent same-`loc` analyses, zero artifact parity errors, and a stable report containing the measured occurrence/appearance counts and allowed same-surface pair.

- [ ] **Step 4: Write `IDX-REPORT.md` from captured output**

Include unique occurrences, total appearances, entry-relationship counts, the exact `39:63:3`/`22:18:9` different-location evidence, verbatim focused/self-test/real-validator/harness results, and exact nonclaims about linguistic correctness, browser impressions, and unresolved word-level emphasis.

### Task 5: Full verification and handoff

**Files:**
- Verify: all files above and the final git diff

- [ ] **Step 1: Run focused and artifact checks**

Run: `python -m unittest tools.test_occurrence_appearance_index -v`; `python tools/validate_appearance_parity.py --self-test`; `python tools/check_artifact_ergonomics.py`.

- [ ] **Step 2: Run the full regression harness**

Run: `python tools/check_regressions.py > idx-check-regressions-output.txt`; inspect the complete output and require exit code 0 plus the final line `ALL REGRESSION CHECKS PASS`.

- [ ] **Step 3: Verify reproducibility and whitespace**

Rebuild to a temporary output and byte-compare it to `qamus/indexes/occurrence-appearances.jsonl`; run `git diff --check`; inspect `git diff --stat` and staged paths.

- [ ] **Step 4: Commit implementation with the required prefix**

Run: `git add tools/build_occurrence_appearance_index.py tools/validate_appearance_parity.py tools/test_occurrence_appearance_index.py tools/check_regressions.py qamus/indexes/occurrence-appearances.jsonl IDX-REPORT.md; git commit -m "idx: add occurrence appearance index and parity gate"`

- [ ] **Step 5: Re-read commit state before handoff**

Run: `git status --short --branch; git log -2 --oneline; git show --stat --oneline HEAD`.

Expected: the branch is clean except for any explicitly documented generated harness output, no push occurred, and the final report matches the fresh verification evidence.
