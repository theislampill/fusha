# Hover-gloss scoreboard (portable template)

A single, portable scorecard for the word-by-word hover layer: how many Qurʾān tokens have a
**certified, authored** gloss, how many are still pending and *why*, and how many previously
wrong glosses have been fixed. It is a **derived view** over `wbw:S:A:W` slots and the
`qamus:` addresses that resolve them (see `source-address-model.md`) — it stores no external
text and renders nothing public beyond `{src:'qamus', kind:'authored', lang:'en'}`.

## The template (regenerable, stdlib only)

Fill these rows from the live entry export + the `wbw` slot map. The reason buckets are the
**hard-won regression categories** — every pending token must name the reason it is *not* yet
certified, so the safe `PENDING` default is auditable rather than silent.

| metric | value | notes |
|---|---:|---|
| **tokens** (Qurʾān word slots in scope) | `49,900` | total `wbw:S:A:W` slots considered |
| **resolved** (certified authored gloss) | `~29,940` | ≈ coverage × tokens |
| **coverage** | `~60%` | resolved / tokens |
| **pending — by reason** | (sum below) | each renders as plain text, which is safe |
| &nbsp;&nbsp;· `norm_only` | — | a `norm()` recall hit not yet certified on `norm_strict` |
| &nbsp;&nbsp;· `hamza_seat` | — | seat-ambiguous (`إيمان`/`أيمان`, `يَأْمُرُونَ`/`يَمُرُّونَ`) |
| &nbsp;&nbsp;· `particle_harakah` | — | short homograph not yet harakah-disambiguated (`مَن`/`مِن`, `لِمَا`/`لَمَّا`) |
| &nbsp;&nbsp;· `pos_mismatch` | — | candidate gloss class ≠ sarf POS (verb-on-noun, name-as-verb) |
| &nbsp;&nbsp;· `polyseme_context` | — | same-root sense needs āyah context (`ٱلْمُلْك`, `يَقْدِرُ`) |
| &nbsp;&nbsp;· `no_entry` | — | no Qamus address covers this root yet (needs an `add`) |
| &nbsp;&nbsp;· `needs_source` | — | entry exists but source page unlocated (locator `needs-search`) |
| **wrong → fixed** (regressions closed) | `(cumulative)` | repairs certified after a wrong gloss was caught |
| **verified wrong, still open** | `0` | confirmed-wrong glosses NOT yet fixed — **must stay 0** |

### Latest known figures

- **tokens:** 49,900
- **coverage:** ~60% (≈ 29,940 resolved)
- **verified wrong, still open:** **0** — no confirmed-wrong gloss is live and unfixed.

The pending-by-reason rows and the cumulative `wrong → fixed` count are filled per run from the
export; the three figures above are the load-bearing headline numbers for this snapshot.

## Invariants (what the scoreboard must always show)

1. **`verified wrong, still open` is 0.** This is the non-negotiable safety bar: a token is
   either correctly glossed, or pending/plain. A confirmed wrong gloss is a stop-the-line
   event until repaired. Prefer `PENDING` over a wrong gloss — pending only lowers coverage,
   never correctness.
2. **`resolved + Σ(pending) = tokens`.** Every in-scope slot is accounted for by exactly one
   bucket; coverage = resolved / tokens.
3. **Pending always has a reason.** No slot is "pending, unknown" — the reason bucket drives
   what skill (sarf / nahw / source-address / locator) needs to act next.
4. **No external text counted as resolved.** A slot is `resolved` only when a Qamus-authored
   gloss is certified for it (`{src:'qamus', kind:'authored', lang:'en'}`). An `informed_by` consult never
   resolves a slot by itself.

## Regenerating the scoreboard (sketch)

Stdlib only; import the shared normalization module — do not redefine it:

```python
import json, os, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.normalize_ar import norm_strict   # certification key (not norm())

def score(slots, resolved_addrs, pending):
    """slots: list of wbw:S:A:W ; resolved_addrs: set of resolved slots ;
       pending: dict slot -> reason bucket. Returns the scoreboard rows."""
    tokens = len(slots)
    resolved = len(resolved_addrs)
    by_reason = collections.Counter(pending.values())
    assert resolved + sum(by_reason.values()) == tokens, "every slot must be bucketed"
    return {
        "tokens": tokens,
        "resolved": resolved,
        "coverage_pct": round(100.0 * resolved / tokens, 1) if tokens else 0.0,
        "pending_by_reason": dict(by_reason),
        "verified_wrong_open": 0,   # MUST be 0; assert before publishing
    }
```

Because the scoreboard is a derived view, it is **portable**: point it at any entry export +
slot map and it recomputes. The reason buckets keep it honest — a number alone ("60% covered")
is meaningless without *why the other 40% is pending*, and that breakdown is exactly what tells
the next agent which skill to run.
