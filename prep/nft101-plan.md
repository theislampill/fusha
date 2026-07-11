# NF-T10-1 correction preparation and dry-run report

## Scope and decision

Owner approval covers exactly one canonical field:

`entries.jsonl` entry `1c5f7c9c8e05` → `usage[2].examples[11].ref`: `4:46` → `4:64`.

This preparation does not apply that edit. The untracked `prep/nft101-apply.py` is the serialized later-apply path. It has no live-site operation and does not commit, push, deploy, or accept a crosswalk binding.

## Dependency trace

The example is card `1c5f7c9c8e05:u3:e12`. Its Arabic text has two qwords and deterministically emits these stable rows:

| qword row | surface | current ref | corrected ref | corrected candidate join |
|---|---|---:|---:|---|
| `llx-qword-1c5f7c9c8e05-03-12-001` | `ظَلَمُوا` | `4:46` | `4:64` | `4:64\|ظلموا` |
| `llx-qword-1c5f7c9c8e05-03-12-002` | `أَنْفُسَهُمْ` | `4:46` | `4:64` | `4:64\|أنفسهم` |

Both are in denominator shard `v001-v040.jsonl`. Their crosswalk rows are in `v011-v020.jsonl`. The row IDs, card ID, surfaces, and `card_text_sha256` stay unchanged; only `quran_ref` changes in the denominator/crosswalk rows, while the crosswalk denominator-row dependency hashes and containing manifest/generation hashes re-anchor.

The canonical edit also moves entry `1c5f7c9c8e05` from the `4:46` usage bucket to a new `4:64` bucket in `by-quran-ref.json`, changes its usage-address edge and Quran-usage-spine membership, and changes `usage_refs` in `existing_qamus_index.min.json`. The literal file set is in `prep/nft101-manifest.txt`.

## Apply sequence

Run only after wave-3 merges and only from a clean `prep-nft101` successor checkout. First confirm the pinned full hover-stage input is available; `build_full_source_address_graph.py` cannot be truthfully regenerated without it.

```powershell
python prep/test_nft101_apply.py
python prep/nft101-apply.py --hover-stage <PINNED_FULL_HOVER_STAGE_DIR> --built-at <OWNER_APPROVED_UTC_TIMESTAMP>
```

The apply command performs, in order:

1. Refuses any `entries.jsonl` SHA other than `a68245e93ce1a8b76858b672a449ff94475abf010e8102575e7c0285c540a78f`, any already-corrected target, or any changed target shape.
2. Snapshots every write target under `.git/nft101-rollback/`.
3. Edits only `usage[2].examples[11].ref`.
4. Rebuilds `by-quran-ref`, re-anchors `checksums.json`, and rebuilds `existing_qamus_index.min.json`.
5. Updates the two denominator rows and denominator manifest.
6. Updates the two still-pending crosswalk rows, their denominator dependency hashes, shard generation, and crosswalk manifest. It deliberately does not convert them to accepted bindings.
7. Updates only queue locations `4:64:9` and `4:64:10` from zero candidates to one candidate, preserving their existing corpus-location safety result and all other wave review state.
8. Re-anchors the embedded fact-table metadata and deterministic `RELEASE.json`.
9. Regenerates the source-address graph from the caller-supplied pinned hover stage.
10. Asserts the corrected ref resolves to the target example, both `4:64` joins find their expected row IDs, and the dataset/denominator/crosswalk validators pass.

The surgical queue/crosswalk update is intentional. Running the generic builders would reset accepted/reviewed wave overlays; running the historical Lane-C investigator would fail its hard-coded `10`-row baseline after these two rows narrow.

## One-command rollback

```powershell
python prep/nft101-apply.py --rollback
```

Rollback restores the pre-apply byte snapshot for every write target and deletes the snapshot only after restoration.

## Red-first evidence

`prep/test_nft101_apply.py` was run before the apply script existed and failed because the implementation was absent. After implementation it passes two behavioral fixtures:

- first application succeeds, second application raises `BaselineError`;
- a wrong baseline SHA raises `BaselineError` and leaves the fixture ref at `4:46`.

Observed command: `python prep/test_nft101_apply.py` → `Ran 2 tests ... OK`.

## Dry-run artifact effects

The core mutation/re-anchor path was executed in a disposable detached worktree at `149ecc4`; this checkout's data was not touched. Validators passed:

- `validate_current_qamus_dataset.py`: public-safe dataset acceptance PASS;
- `validate_largelexicon_table_manifest.py`: `ok: true`;
- `validate_largelexicon_qword_crosswalk.py`: `ok: true`.

At the current head, the deterministic core effects are:

- `entries.jsonl`: byte count remains `4,830,755`; SHA changes from `a68245e9…` to `b742fde5…`.
- `by-quran-ref.json`: `4:46` loses this entry but remains populated; new `4:64` gains this entry. Distinct ref count increases by one.
- denominator: 117,117 rows remain; exactly two rows change `quran_ref`.
- crosswalk: 117,117 rows remain; exactly two packet rows change `quran_ref` and denominator dependency hash. Their status remains `source_crosswalk_packet_ready`.
- queue: 5,231 rows remain; `no_qword_candidate` narrows `10 → 8`, and `unique_qword_candidate` expands `51 → 53`.
- release/fact-table metadata: row counts remain unchanged; input/logical hashes re-anchor.

The two queue rows narrow but do not close:

| location | before | after source correction | remaining blocker |
|---|---|---|---|
| `4:64:9` | no qword candidate; owner wrong-ref dependency | one candidate: `…-03-12-001` | `ayah_surface_unique=false`; indexed matching surface is at `4:64:12` |
| `4:64:10` | no qword candidate; owner wrong-ref dependency | one candidate: `…-03-12-002` | `ayah_surface_unique=false`; indexed matching surface is at `4:64:13` |

Therefore, of the five Lane-C `blocked_on_owner_dataset_correction` rows, exactly two re-evaluate and narrow (`4:64:9`, `4:64:10`). The other three (`2:274:1`, `12:37:1`, `48:15:1`) are unaffected. The historical Lane-C report remains frozen evidence; the durable queue carries the new current state.

Of the existing 63 RM-36 `unverifiable_divergent_ayah` rows, zero carry entry `1c5f7c9c8e05` and zero are in ayah `4:64`; none changes classification from this correction. The corrected crosswalk rows remain pending and have no `row_unique_surface_fallback` method, so they do not enter the RM-36 denominator. If a later, separately reviewed acceptance assigned that method, `4:64` is on RM-36's divergent-ayah list and those would be two new divergent rows, not changes to the existing 63.

## Stop conditions

Stop without writing if any of these occurs:

- wave-3 changes the canonical `entries.jsonl` SHA or target structure;
- either qword/crosswalk row is missing, duplicated, already accepted, or no longer cites `4:46`;
- either queue row is no longer the zero-candidate baseline (retrace instead of overwriting wave state);
- the pinned full hover-stage input is missing or unapproved;
- the corrected join yields anything other than one expected candidate per target location;
- any validator fails, any unexpected file changes, or the working tree contains overlapping user edits.
