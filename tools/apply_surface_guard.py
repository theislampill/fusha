#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surface+loc double-match guard for every apply/promotion lane.

CONTRACT (owner steer §7, VN-UNLOCK-PROOF-2026-07-29 §3.3 + §7 caveat 3):
any lane that mutates — or stages a mutation of — a live row addressed by a
Quran loc MUST call :func:`require_surface_loc_double_match` and stop when
``ok`` is False. Loc-keyed matching alone is proven unsafe: the live wbw
plane aliases at least three locs (17:15:5, 20:14:11, 33:18:7) where the
live row holds a DIFFERENT token than the canonical index, so a loc-only
apply would patch the wrong token.

Committed hazard fixture: ``qamus/examples/hazards/wbw-loc-aliasing.fixture.jsonl``.
Regression gate: HAZARD section of ``tools/check_regressions.py``
(``tools/test_hazard_fixtures.py``).

The guard requires BOTH:
* exact loc equality between the claim and the live row; and
* a shared surface key (NFC-normalized exact form, or the bare letter
  skeleton with ḥarakāt / Quranic annotation marks / dagger alif / tatweel
  stripped and ٱ folded to ا) between the claimed surface and the live
  surface.

It REFUSES (never "best-efforts") when the live row is missing or carries no
verifiable surface: an unverified live surface is exactly the state in which
the 20:14:11 / 33:18:7 aliasing rows would be mispatched.
"""

from __future__ import annotations

from collections import namedtuple
import unicodedata

GuardResult = namedtuple("GuardResult", "ok reason")

_STRIP_ALEF_WASLA = "ٱ"


def _bare(surface):
    """Bare letter skeleton: strip 064B-0652, 06D6-06ED, 0670, 0640; fold ٱ->ا."""

    out = []
    for char in unicodedata.normalize("NFC", surface or ""):
        code = ord(char)
        if 0x064B <= code <= 0x0652 or 0x06D6 <= code <= 0x06ED or code in (0x0670, 0x0640):
            continue
        out.append("ا" if char == _STRIP_ALEF_WASLA else char)
    return "".join(out)


def surface_keys(surface):
    """Return the comparison keys for a surface: NFC exact + bare skeleton."""

    if not surface or not str(surface).strip():
        return set()
    normalized = unicodedata.normalize("NFC", str(surface).strip())
    keys = {normalized}
    bare = _bare(normalized)
    if bare:
        keys.add(bare)
    return keys


def require_surface_loc_double_match(claim_loc, claim_surface, live_row):
    """Surface+loc double-match verdict for one staged apply.

    ``live_row`` is the live-plane row the lane resolved for ``claim_loc``
    (any mapping with ``loc`` and ``surface`` keys), or None when no live row
    could be read. Returns ``GuardResult(ok, reason)``; a lane must not apply
    unless ``ok`` is True.
    """

    claim_loc = str(claim_loc or "").strip()
    if not claim_loc:
        return GuardResult(False, "refused: empty claim loc")
    claim_keys = surface_keys(claim_surface)
    if not claim_keys:
        return GuardResult(False, "refused: empty claim surface")
    if not isinstance(live_row, dict):
        return GuardResult(False, "refused: no_live_row for loc %s" % claim_loc)
    live_loc = str(live_row.get("loc") or "").strip()
    if live_loc != claim_loc:
        return GuardResult(
            False, "refused: loc_mismatch (claim %s vs live %s)" % (claim_loc, live_loc or "<none>")
        )
    live_keys = surface_keys(live_row.get("surface"))
    if not live_keys:
        return GuardResult(
            False,
            "refused: live_surface_unverified at %s — loc-only matching is the "
            "wbw-loc-aliasing hazard (VN-UNLOCK-PROOF-2026-07-29 §3.3)" % claim_loc,
        )
    if not (claim_keys & live_keys):
        return GuardResult(
            False,
            "refused: surface_mismatch_wbw_loc_aliasing at %s — live token differs "
            "from the claimed token; a loc-keyed apply would mispatch" % claim_loc,
        )
    return GuardResult(True, "surface+loc double-match verified at %s" % claim_loc)


def self_test():
    checks = [
        ("aliased live token refused",
         not require_surface_loc_double_match("17:15:5", "لِنَفْسِهِ", {"loc": "17:15:5", "surface": "نَبْعَثَ"}).ok),
        ("unverified live surface refused",
         not require_surface_loc_double_match("20:14:11", "لِذِكْرِي", {"loc": "20:14:11", "surface": None}).ok),
        ("missing live row refused",
         not require_surface_loc_double_match("33:18:7", "لِإِخْوَانِهِمْ", None).ok),
        ("loc mismatch refused",
         not require_surface_loc_double_match("2:187:64", "لِلنَّاسِ", {"loc": "2:187:63", "surface": "لِلنَّاسِ"}).ok),
        ("genuine double-match accepted",
         require_surface_loc_double_match("2:187:63", "لِلنَّاسِ", {"loc": "2:187:63", "surface": "لِلنَّاسِ"}).ok),
        ("annotation-mark variant accepted (skeleton key)",
         require_surface_loc_double_match("17:15:5", "لِنَفْسِهِ", {"loc": "17:15:5", "surface": "لِنَفْسِهِۦ"}).ok),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(("ok   " if passed else "FAIL ") + name)
    if failed:
        print("APPLY SURFACE GUARD SELF-TEST FAIL")
        return 1
    print("APPLY SURFACE GUARD SELF-TEST PASS")
    return 0


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(self_test())
