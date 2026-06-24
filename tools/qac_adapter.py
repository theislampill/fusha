#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QAC adapter — read per-word ROOT and PART-OF-SPEECH from a LOCAL TSV the user provides.

PROVENANCE (read provenance/source-boundaries.md §0–§3 before using this):
  * QAC (the Quranic Arabic Corpus) is **internal reference only**. It is used to
    CONFIRM a root or part-of-speech that we author ourselves.
  * A word's **root** and **POS** are uncopyrightable linguistic FACTS — we may
    consult them and may record an internal `informed_by:'qac'` breadcrumb.
  * **Nothing from QAC is shipped publicly.** No QAC text, no QAC glosses, and not
    the .tsv itself. This adapter ships; the DATA it reads does NOT. The user
    fetches the QAC corpus offline and points this adapter at their local copy.
  * This adapter returns FACTS (root / POS), never glosses. Glosses are authored
    by us and published as {src:'qamus', kind:'authored'} — see the source rules.

WHAT THIS IS:
  A stdlib-only ADAPTER INTERFACE over a local, tab-separated QAC export. The exact
  QAC distribution columns vary by release, so the adapter is column-name driven:
  you tell it which columns hold the location, the (normalized) word form, the root,
  and the POS. Defaults match the common `(location, form, tag, features)` shape
  where the root sits inside a `ROOT:xxx` field of the morphology features.

  No live-app dependency. No network. Pure stdlib. Reuses tools/normalize_ar.py only
  to key lookups by a strict, hamza-preserving form (so إيمان ≠ أيمان, etc.).

KEYING:
  Lookups are keyed by (ref, norm_strict(token)). `ref` is a `surah:ayah` string
  (word-level `surah:ayah:word` also works if your TSV carries it). We key on
  norm_strict — NOT norm — because norm() drops the hamza seat and would collapse
  scripture-distinct forms (see provenance/source-boundaries.md §5). If a row's
  location is finer than the query ref, the adapter matches on the ref PREFIX so a
  `2:255` query still finds words located at `2:255:1`, `2:255:2`, ...

TYPICAL USE (the data file is yours, never committed):
    from tools.qac_adapter import QacAdapter
    qac = QacAdapter.from_tsv("/path/you/own/qac_morphology.tsv")  # YOUR local file
    root = qac.get_root("2:255", "ٱللَّهُ")      # a FACT, e.g. "ا ل ه" — to CONFIRM ours
    pos  = qac.get_pos("2:255", "ٱللَّهُ")        # a FACT, e.g. "PN"
    # use `root`/`pos` to cross-check an authored entry; record informed_by:'qac'
    # INTERNALLY only; never emit QAC text or names into the public artifact.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tools.normalize_ar import norm_strict


def _root_from_features(features):
    """Pull a space-joined Arabic root out of a QAC morphology features string.

    QAC encodes the root inside the features column as `ROOT:ktb` (Buckwalter) or
    `ROOT:كتب` depending on the export. We return the letters separated by spaces to
    match the repo's `"ك ت ب"` convention. Returns "" if no ROOT field is present
    (function words and particles legitimately have no root)."""
    if not features:
        return ""
    for part in str(features).replace("\t", "|").split("|"):
        part = part.strip()
        if part.upper().startswith("ROOT:"):
            raw = part.split(":", 1)[1].strip()
            # already spaced? keep as-is; else space out the letters
            if " " in raw:
                return raw
            return " ".join(ch for ch in raw if not ch.isspace())
    return ""


def _ref_matches(query_ref, row_ref):
    """True if `row_ref` is the query ref or a finer location under it.

    `2:255` matches `2:255`, `2:255:1`, `2:255:7` (word index). Exact-or-prefix on
    the `:`-delimited location so a verse query reaches its words."""
    if not query_ref or not row_ref:
        return False
    if query_ref == row_ref:
        return True
    return row_ref.startswith(query_ref + ":")


class QacAdapter:
    """Read-only, in-memory index over a local QAC TSV. Facts only (root + POS).

    Construct via `QacAdapter.from_tsv(path, ...)`. Then call `get_root(ref, token)`
    and `get_pos(ref, token)`. Both key on (ref, norm_strict(token)) and return ""
    when there is no confident hit — callers should treat "" as "no QAC fact; keep
    your authored value and consider PENDING", never as a license to invent one.
    """

    def __init__(self, rows, location_col, form_col, pos_col, root_col=None,
                 features_col=None):
        # rows: list of dicts (DictReader rows). We build two lookups:
        #   by_key[(ref, norm_strict(form))] -> (root, pos)   (precise)
        #   by_ref[ref] -> list of (norm_strict(form), root, pos)  (prefix fallback)
        self._by_key = {}
        self._by_ref = {}
        for r in rows:
            ref = (r.get(location_col) or "").strip()
            form = (r.get(form_col) or "").strip()
            if not ref or not form:
                continue
            pos = (r.get(pos_col) or "").strip() if pos_col else ""
            if root_col and r.get(root_col):
                root = " ".join((r.get(root_col) or "").split())
            else:
                root = _root_from_features(r.get(features_col) if features_col else "")
            nf = norm_strict(form)
            self._by_key.setdefault((ref, nf), (root, pos))
            self._by_ref.setdefault(ref, []).append((nf, root, pos))

    # ---- construction -----------------------------------------------------
    @classmethod
    def from_tsv(cls, path, location_col="location", form_col="form",
                 pos_col="tag", root_col=None, features_col="features",
                 delimiter="\t"):
        """Load a local QAC TSV the USER provides (never bundled in this repo).

        Column names are configurable to fit your QAC export. Defaults assume a
        `location  form  tag  features` layout with the root inside `features`
        (`ROOT:...`). If your export has a dedicated root column, pass
        `root_col="root"`."""
        if not os.path.exists(path):
            raise FileNotFoundError(
                "QAC TSV not found: %r. QAC is fetched offline by you and is NOT "
                "shipped in this repo (see provenance/source-boundaries.md §0)." % path)
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            rows = list(reader)
        return cls.from_rows(rows, location_col, form_col, pos_col, root_col,
                             features_col)

    @classmethod
    def from_rows(cls, rows, location_col="location", form_col="form",
                  pos_col="tag", root_col=None, features_col="features"):
        """Build from already-parsed DictReader rows (used by tests + the demo)."""
        return cls(rows, location_col, form_col, pos_col, root_col, features_col)

    # ---- lookups (FACTS only) --------------------------------------------
    def _lookup(self, ref, norm_strict_token):
        nf = norm_strict(norm_strict_token) if norm_strict_token else ""
        if not nf:
            return ("", "")
        hit = self._by_key.get((ref, nf))
        if hit:
            return hit
        # prefix fallback: a verse-level ref reaching its word locations
        for row_ref, entries in self._by_ref.items():
            if _ref_matches(ref, row_ref) or _ref_matches(row_ref, ref):
                for cand_nf, root, pos in entries:
                    if cand_nf == nf:
                        return (root, pos)
        return ("", "")

    def get_root(self, ref, norm_strict_token):
        """Return the QAC ROOT (space-joined, e.g. "ك ت ب") for the word at `ref`,
        or "" if QAC has no confident hit. A FACT used to CONFIRM our authored root —
        never published, never a gloss."""
        return self._lookup(ref, norm_strict_token)[0]

    def get_pos(self, ref, norm_strict_token):
        """Return the QAC PART-OF-SPEECH tag (e.g. "PN", "V", "N") for the word at
        `ref`, or "" if QAC has no confident hit. A FACT used to CONFIRM our authored
        POS (e.g. to keep a verb gloss off a noun) — never published."""
        return self._lookup(ref, norm_strict_token)[1]

    def __len__(self):
        return len(self._by_key)


if __name__ == "__main__":
    import csv as _csv
    import io as _io

    # Tiny INLINE 3-row demo TSV. This is NOT QAC data — it is three hand-written
    # rows in the QAC-shaped layout, purely to exercise the parser. Real QAC is
    # fetched offline by the user and is never committed (source-boundaries §0).
    demo_tsv = (
        "location\tform\ttag\tfeatures\n"
        "2:255:1\tٱللَّهُ\tPN\tSTEM|POS:PN|LEM:{ll~ahu|ROOT:اله\n"
        "1:2:2\tٱلْحَمْدُ\tN\tSTEM|POS:N|LEM:Hamd|ROOT:حمد\n"
        "112:1:3\tٱللَّهُ\tPN\tSTEM|POS:PN|ROOT:اله\n"
    )
    rows = list(_csv.DictReader(_io.StringIO(demo_tsv), delimiter="\t"))
    qac = QacAdapter.from_rows(rows)

    # roots and POS are FACTS we read to CONFIRM authored content (never published)
    assert qac.get_root("2:255", "ٱللَّهُ") == "ا ل ه", qac.get_root("2:255", "ٱللَّهُ")
    assert qac.get_pos("2:255", "ٱللَّهُ") == "PN"
    assert qac.get_root("1:2:2", "ٱلْحَمْدُ") == "ح م د"
    assert qac.get_pos("1:2:2", "ٱلْحَمْدُ") == "N"
    # POS lets us keep a verb gloss off a noun: ٱلْحَمْدُ is N, not a verb.
    # A miss returns "" — meaning "no QAC fact"; the caller keeps PENDING, never invents.
    assert qac.get_root("9:9", "كَلِمَةٌ") == ""
    print("qac_adapter demo OK — parsed %d word rows (facts only, no QAC shipped)" % len(qac))
