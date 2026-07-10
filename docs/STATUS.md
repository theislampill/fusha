# STATUS — live coverage (single source of truth)

**Glossed coverage** (`coverage_glossed = glossed_word_locs / total_word_locs`) is **98.72% (49,261 / 49,902)**.

The artifact was **built 2026-07-07** and **verified current 2026-07-10** via the `wbw_status` currency check (exit 0). This was a currency check of the built artifact, **not** a fresh 2026-07-10 measurement.

**Measurement surface:** the deployed wbw lookup artifact meta (`qamus_wbw/build.py` `meta["coverage"]["glossed"]`) — live-side. This number cannot be recomputed from this repo alone.

**Per-window rich-span regression gates:** VN-00 frozen at 100.00% (12,775/12,775); VN-01 frozen at 100.00% (14,052/14,052); VN-02 frozen at 100.00% (12,185/12,185). VN-03 measured 69.38% (7,431/10,711), not started.

**Truth rule:** any other coverage number in this repo is historical; files carrying old figures must have a HISTORICAL banner.

Distinct metrics must never be conflated: glossed coverage ≠ per-window rich-span coverage ≠ whitelist-row share (34,322 rows = 68.8% of the ≤49,902 loc ceiling).
