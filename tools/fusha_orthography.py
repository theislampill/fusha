#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusha_orthography — grapheme, connectivity, mark, and vocalization-state OBSERVATIONS.

Tranche-001 orthography/segmentation guards (cu-grapheme-inventory-and-confusables,
cu-orthographic-connectivity-classes, cu-short-vowel-diacritics-and-vocalization-state,
cu-nunation-support-orthography [orthographic part], cu-definite-article-assimilation,
plus carrier/radical and shadda/assimilation guards feeding u-s01/u-s06).

Everything here OBSERVES the written surface exactly as spelled. Nothing infers case,
mood, syntactic function, root identity, lemma, sense, or certification — where a
closed rule table lacks authority the caller gets an explicit unresolved/abstain
marker, never a guess. Stdlib + normalize_ar only; no network, no live writes.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _REPO)
from tools import normalize_ar as N  # noqa: E402,F401  (kept for API parity with the other checker modules)

# ---------------------------------------------------------------------------
# combining marks — NEVER a base letter, NEVER the primary ownership span of a cluster
# ---------------------------------------------------------------------------
SUKUN = "ْ"
SHADDA = "ّ"
SHORT_VOWELS = {"َ": "fatha", "ُ": "damma", "ِ": "kasra"}
TANWIN_MARKS = {"ً": "fathatan", "ٌ": "dammatan", "ٍ": "kasratan"}
_HARAKAT = set(chr(c) for c in range(0x064B, 0x0653))          # fathatan..sukun
_QURANIC_MARKS = set(chr(c) for c in range(0x06D6, 0x06ED + 1))
_DAGGER_ALIF = "ٰ"
_TATWEEL = "ـ"
# U+0653..U+065F: the rest of the Arabic combining-mark inventory used by the corpus -- maddah
# above (٬), combining hamza above/below (seat carried separately by the base letter), subscript
# alif, and the remaining Qur'anic vowel-sign variants. NEVER a base letter (F1).
_EXTENDED_COMBINING_MARKS = set(chr(c) for c in range(0x0653, 0x0660))
_COMBINING = _HARAKAT | _QURANIC_MARKS | {_DAGGER_ALIF} | _EXTENDED_COMBINING_MARKS


def grapheme_clusters(surface):
    """Split `surface` into EXACT grapheme clusters: one base letter + its trailing combining
    marks (harakāt, shadda, sukūn, tanwīn, dagger alif, Qurʾanic marks) and tatweel filler.
    Each cluster carries exact character spans into `surface`; concatenating cluster surfaces
    reconstructs `surface` exactly (asserted) — the reconstruction is never approximate."""
    clusters = []
    for i, ch in enumerate(surface or ""):
        if clusters and (ch in _COMBINING or ch == _TATWEEL):
            clusters[-1]["surface"] += ch
            clusters[-1]["end"] = i + 1
            if ch != _TATWEEL:
                clusters[-1]["marks"] += ch
        else:
            clusters.append({"base": ch, "marks": "", "surface": ch, "start": i, "end": i + 1})
    assert "".join(c["surface"] for c in clusters) == (surface or ""), \
        "grapheme clusters must reconstruct the surface exactly (%r)" % surface
    return clusters


def base_surface(surface):
    """Strip ONLY combining marks; keep EVERY base letter distinct. Unlike normalize_ar.bare(),
    this NEVER folds ٱ (alif waṣla) to ا — written/base separation must not normalize away
    identity. Hamza seats (أ إ ؤ ئ ء), tāʾ marbūṭa, alif maqṣūra stay distinct, same as bare()."""
    return "".join(c["base"] for c in grapheme_clusters(surface))


def written_surface(surface):
    """Identity function, named for symmetry with base_surface(): the written surface is the
    original exactly as spelled — never altered, never a display substitute."""
    return surface


# ---------------------------------------------------------------------------
# connectivity classes — visual joining behaviour ONLY, never a word/morpheme boundary
# ---------------------------------------------------------------------------
# Right-joining letters connect to the PREVIOUS letter but never to the NEXT one, so a visual
# run ends right after them even mid-word (e.g. the ا/د/ر/و family). This is purely a rendering
# fact about the Arabic joining script; it must never be read back as a segmentation boundary.
# ة (tāʾ marbūṭa), ى (alif maqṣūra) and ؤ (hamza on wāw) are DELIBERATELY excluded: the
# curriculum pack (inc-orthographic-connectivity-classes) explicitly abstains on all three
# pending a source-backed closed inventory (con-adv-01..03) rather than assuming they join like
# the visually-resembled letters ه/ا/و -- resemblance is not membership (R4). Do not add them
# back without that same source-backed authority.
_RIGHT_JOINING = set("اآأإٱدذرزو")
_NON_JOINING = set("ء")  # an isolated hamza joins neither side
# The closed set of base letters that join BOTH neighbours -- the remainder of the 28-letter
# Arabic alphabet plus ئ (hamza on yāʾ, which joins like yāʾ). Anything NOT in this closed
# inventory (nor combining/non-joining/right-joining above) is out-of-inventory and must fail
# closed rather than default to dual_joining (F1). ة، ى، ؤ fall through to 'unknown' here on
# purpose (see _RIGHT_JOINING above), never guessed as dual_joining either.
_DUAL_JOINING = set("بتثجحخسشصضطظعغفقكلمنهيئ")


def connectivity_class(base_char):
    """Classify one BASE letter's joining behaviour: 'transparent' (a combining mark — never
    breaks or carries the joining chain), 'non_joining', 'right_joining' (joins the previous
    letter only — ends a visual run), 'dual_joining' (joins both neighbours), or 'unknown' for
    a character outside the closed Arabic letter inventory this table has authority over — a
    fail-closed class, never guessed as dual_joining."""
    if base_char in _COMBINING or base_char == _TATWEEL:
        return "transparent"
    if base_char in _NON_JOINING:
        return "non_joining"
    if base_char in _RIGHT_JOINING:
        return "right_joining"
    if base_char in _DUAL_JOINING:
        return "dual_joining"
    return "unknown"


def visual_runs(surface):
    """Group grapheme clusters into VISUAL connectivity runs. A right_joining/non_joining letter
    ends its run. This is rendering-adjacent metadata ONLY: a run boundary here is NEVER a word
    or morpheme boundary — segmentation must never be derived from this function."""
    clusters = grapheme_clusters(surface)
    runs, current = [], []
    for idx, c in enumerate(clusters):
        current.append(idx)
        if connectivity_class(c["base"]) in ("right_joining", "non_joining"):
            runs.append({"cluster_indices": list(current), "ends_run": True})
            current = []
    if current:
        runs.append({"cluster_indices": list(current), "ends_run": False})
    return runs


# ---------------------------------------------------------------------------
# confusable-family metadata — NEVER letter/root/entry/sense equality
# ---------------------------------------------------------------------------
_DOT_FAMILY_GROUPS = (
    ("dotting_tooth_batyni", "بتثني"),
    ("dotting_jah_khah", "جحخ"),
    ("dotting_dal_dhal", "دذ"),
    ("dotting_ra_zay", "رز"),
    ("dotting_sin_shin", "سش"),
    ("dotting_sad_dad", "صض"),
    ("dotting_ta_za", "طظ"),
    ("dotting_ain_ghain", "عغ"),
    ("dotting_fa_qaf", "فق"),
)
_CHAR_TO_DOT_FAMILY = {ch: fam for fam, chars in _DOT_FAMILY_GROUPS for ch in chars}
_HAMZA_SEAT_FAMILY = "أإؤئء"


def confusable_family(base_char):
    """Return confusable-family METADATA ONLY for `base_char`: either the same rasm skeleton
    with a different dot pattern, or the same abstract hamza on a different seat letter. This is
    NEVER letter/root/entry/sense equality — members of a family remain different letters/words;
    the metadata only flags a shared skeleton a reader could visually confuse. Returns None for a
    letter with no such family (e.g. ك، و، ه، ل، م) or for a combining mark."""
    if base_char in _HAMZA_SEAT_FAMILY:
        return {"kind": "hamza_seat", "family": "hamza_seat", "members": sorted(_HAMZA_SEAT_FAMILY), "equality": None}
    fam = _CHAR_TO_DOT_FAMILY.get(base_char)
    if fam:
        members = sorted(ch for ch, f in _CHAR_TO_DOT_FAMILY.items() if f == fam)
        return {"kind": "dot_family", "family": fam, "members": members, "equality": None}
    return None


# ---------------------------------------------------------------------------
# vocalization state — observed marks only, nothing invented, no contextual function
# ---------------------------------------------------------------------------
def vocalization_state(surface):
    """Per-cluster OBSERVED vocalization: for each grapheme cluster, report the short vowel /
    sukūn / shadda / tanwīn marks actually WRITTEN on it — never inferred, never filled in for an
    unmarked cluster. The token-level state is 'unvoweled' (no cluster carries a vowel/sukūn/
    tanwīn mark), 'fully_voweled' (every cluster does), or 'partially_voweled' otherwise. This is
    what keeps مِنَ / مَن / من distinct: by what is actually written, never by contextual function."""
    clusters = grapheme_clusters(surface)
    per_cluster = []
    marked = 0
    for c in clusters:
        marks = c["marks"]
        observed = {
            "short_vowel": next((SHORT_VOWELS[m] for m in marks if m in SHORT_VOWELS), None),
            "sukun": SUKUN in marks,
            "shadda": SHADDA in marks,
            "tanwin": next((TANWIN_MARKS[m] for m in marks if m in TANWIN_MARKS), None),
        }
        if observed["short_vowel"] or observed["sukun"] or observed["shadda"] or observed["tanwin"]:
            marked += 1
        per_cluster.append({"base": c["base"], "start": c["start"], "end": c["end"], "observed": observed})
    if not clusters or marked == 0:
        state = "unvoweled"
    elif marked == len(clusters):
        state = "fully_voweled"
    else:
        state = "partially_voweled"
    return {"state": state, "clusters": per_cluster}


# ---------------------------------------------------------------------------
# definite-article candidate + assimilation observation (ال / ٱل, optionally after a leading
# وَ/فَ conjunction cluster) — candidate only, never a case/function/certification claim
# ---------------------------------------------------------------------------
_ARTICLE_ALIF_FORMS = ("ا", "ٱ")
_LEADING_CONJUNCTIONS = ("و", "ف")
# reviewed sun-letter (shamsiyya) class: the article's lām assimilates into these when a shadda
# is written on the following letter. Moon (qamariyya) letters never carry that shadda.
_SUN_LETTERS = set("تثدذرزسشصضطظلن")


def article_candidate(surface):
    """Detect a definite-article candidate (ال or ٱل) opening `surface`, optionally after a
    single leading وَ/فَ conjunction cluster. Returns None when the token does not open with one
    of the two accepted article spellings followed by a lām, when the article would leave no
    host letters at all (a bare "ال" or a conjunction+article with nothing after the lām is never
    a genuine article-plus-host token), or when a leading و/ف is followed by the AMBIGUOUS bare
    alif spelling: و/ف + bare ا + ل also opens a radical-initial فَاعِل-pattern stem (فَالِقُ،
    وَالِد، وَالٍ) that shares the identical shape, so shape alone cannot assert an article there
    (F3). Only the canonical ٱ (alif waṣla) spelling disambiguates a genuine article after a
    leading conjunction; a bare ا article is still accepted with NO leading conjunction, where
    that ambiguity does not arise. Candidate only — no case/function claim, and the article's
    written lām is always kept as part of the article segment."""
    clusters = grapheme_clusters(surface)
    i = 0
    conjunction = None
    if clusters and clusters[0]["base"] in _LEADING_CONJUNCTIONS and len(clusters) >= 3:
        conjunction = clusters[0]
        i = 1
    if i + 1 >= len(clusters):
        return None
    if clusters[i]["base"] not in _ARTICLE_ALIF_FORMS or clusters[i + 1]["base"] != "ل":
        return None
    if conjunction is not None and clusters[i]["base"] != "ٱ":
        return None
    host_clusters = clusters[i + 2:]
    if not host_clusters:
        return None
    article_surface = clusters[i]["surface"] + clusters[i + 1]["surface"]
    return {
        "conjunction": conjunction["surface"] if conjunction else None,
        "article_form": clusters[i]["base"],
        "article_surface": article_surface,
        "host_surface": "".join(c["surface"] for c in host_clusters),
        "article_start_cluster": i,
        "host_start_cluster": i + 2,
        "lam_ownership": "article",
    }


def assimilation_observation(surface):
    """Given a token opening with an article candidate, observe whether the host-INITIAL letter
    carries a WRITTEN shadda and belongs to the reviewed sun-letter class. Returns None when there
    is no article candidate. The article's lām stays article-owned in EITHER case (assimilated or
    not) — this never re-attributes it to the host, and never infers a doubled root / Form-II
    stem shape from the shadda; it only reports what is written."""
    art = article_candidate(surface)
    if art is None:
        return None
    clusters = grapheme_clusters(surface)
    host_start = art["host_start_cluster"]
    if host_start >= len(clusters):
        return dict(art, host_initial_letter=None, host_initial_is_sun_letter_class=False,
                    host_initial_shadda_observed=False, assimilation_observed=False)
    host0 = clusters[host_start]
    is_sun_letter = host0["base"] in _SUN_LETTERS
    has_shadda = SHADDA in host0["marks"]
    return dict(art, host_initial_letter=host0["base"], host_initial_is_sun_letter_class=is_sun_letter,
                host_initial_shadda_observed=has_shadda, assimilation_observed=bool(is_sun_letter and has_shadda))


# ---------------------------------------------------------------------------
# tanwīn + support-alif observation — spelling only, no case/function inference
# ---------------------------------------------------------------------------
def tanwin_observation(surface):
    """Observe a WRITTEN tanwīn mark on the final cluster, and whether it is carried with a
    support alif (ـًا, e.g. قُرْءَانًا — the mark sits on the cluster BEFORE a bare trailing alif)
    versus a bare final letter (e.g. رَحْمَةً — tanwīn fatḥa directly on tāʾ marbūṭa, no support
    alif). No case or grammatical function is inferred; this is a spelling observation only."""
    clusters = grapheme_clusters(surface)
    if not clusters:
        return {"has_tanwin": False, "tanwin_mark": None, "has_support_alif": False}
    last = clusters[-1]
    direct_mark = next((TANWIN_MARKS[m] for m in last["marks"] if m in TANWIN_MARKS), None)
    if direct_mark is not None:
        return {"has_tanwin": True, "tanwin_mark": direct_mark, "tanwin_cluster_index": len(clusters) - 1,
                "has_support_alif": False, "support_alif_cluster_index": None}
    if len(clusters) >= 2 and last["marks"] == "" and last["base"] in ("ا", "ى"):
        prev = clusters[-2]
        prev_mark = next((TANWIN_MARKS[m] for m in prev["marks"] if m in TANWIN_MARKS), None)
        if prev_mark == "fathatan":
            # ا is a bare SUPPORT alif carrying no vowel of its own (قُرْءَانًا); ى (alif maqṣūra)
            # is the direct spelling of the fatḥatān itself (هُدًى، فَتًى، مُصَلًّى) -- the mark is
            # physically written on the PRECEDING consonant either way, but only the ا case is a
            # separate support letter (F2).
            return {"has_tanwin": True, "tanwin_mark": prev_mark, "tanwin_cluster_index": len(clusters) - 2,
                    "has_support_alif": last["base"] == "ا",
                    "support_alif_cluster_index": (len(clusters) - 1) if last["base"] == "ا" else None}
    return {"has_tanwin": False, "tanwin_mark": None, "has_support_alif": False}


def article_tanwin_conflict(surface):
    """A definite-article-marked token cannot ALSO carry tanwīn (tanwīn marks indefiniteness).
    When a closed rule table finds both written on the same token, that is a genuine orthographic
    contradiction: report it explicitly and abstain rather than silently preferring one reading."""
    art = article_candidate(surface)
    tanwin = tanwin_observation(surface)
    if art is not None and tanwin.get("has_tanwin"):
        return {"conflict": "article_and_tanwin", "status": "abstain", "article": art, "tanwin": tanwin}
    return None


# ---------------------------------------------------------------------------
# long-vowel carrier vs. consonantal radical — abstain when the closed rule table lacks authority
# ---------------------------------------------------------------------------
_LONG_VOWEL_CARRIER_LETTERS = set("اوي")


def carrier_or_radical(surface, cluster_index):
    """For an ا/و/ي cluster, decide long-vowel-carrier vs. consonantal-radical ONLY when a closed
    rule table has authority: a WRITTEN shadda or short vowel on that SAME cluster settles it as a
    radical (a doubled/vowelled consonant is never a mere vowel carrier). Otherwise — a bare,
    unmarked instance with no supporting evidence — return 'unresolved'. Never guessed."""
    clusters = grapheme_clusters(surface)
    if cluster_index < 0 or cluster_index >= len(clusters):
        return {"status": "unresolved", "reason": "index_out_of_range"}
    c = clusters[cluster_index]
    if c["base"] not in _LONG_VOWEL_CARRIER_LETTERS:
        return {"status": "unresolved", "reason": "not_a_carrier_letter_class"}
    if SHADDA in c["marks"]:
        return {"status": "radical", "reason": "written_shadda_on_the_letter_itself"}
    if any(m in SHORT_VOWELS for m in c["marks"]):
        return {"status": "radical", "reason": "written_short_vowel_on_the_letter_itself"}
    return {"status": "unresolved", "reason": "insufficient_written_evidence"}


# ---------------------------------------------------------------------------
# aggregate — the structured observation record a checker token can attach
# ---------------------------------------------------------------------------
def analyze_orthography(surface):
    """Structured grapheme/connectivity/mark/vocalization-state observations for one written
    token surface. Every field is an OBSERVATION of the written form; nothing is invented, and
    nothing certifies root, entry, sense, case, mood, or function."""
    clusters = grapheme_clusters(surface)
    return {
        "written_surface": written_surface(surface),
        "base_surface": base_surface(surface),
        "grapheme_clusters": [
            {"base": c["base"], "surface": c["surface"], "start": c["start"], "end": c["end"],
             "connectivity_class": connectivity_class(c["base"]),
             "confusable_family": confusable_family(c["base"])}
            for c in clusters
        ],
        "visual_runs": visual_runs(surface),
        "vocalization": vocalization_state(surface),
        "article": article_candidate(surface),
        "assimilation": assimilation_observation(surface),
        "tanwin": tanwin_observation(surface),
        "conflicts": [c for c in [article_tanwin_conflict(surface)] if c],
    }


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def _self_test():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    for surface in ("ٱلشَّمْسَ", "ٱلْقَمَرَ", "وَٱلْأُنثَىٰ", "قُرْءَانًا", "رَحْمَةً"):
        clusters = grapheme_clusters(surface)
        check("".join(c["surface"] for c in clusters) == surface, "grapheme_clusters must rebuild %r exactly" % surface)

    shams = assimilation_observation("ٱلشَّمْسَ")
    check(shams and shams["assimilation_observed"] is True, "ٱلشَّمْسَ must observe assimilation")
    qamar = assimilation_observation("ٱلْقَمَرَ")
    check(qamar and qamar["assimilation_observed"] is False, "ٱلْقَمَرَ must not invent assimilation")
    check(qamar and qamar["host_initial_shadda_observed"] is False, "ٱلْقَمَرَ must not invent a shadda")

    art_wa = article_candidate("وَٱلْأُنثَىٰ")
    check(art_wa is not None, "وَٱلْأُنثَىٰ must expose an article candidate after the waw")
    if art_wa:
        rebuilt = (art_wa["conjunction"] or "") + art_wa["article_surface"] + art_wa["host_surface"]
        check(rebuilt == "وَٱلْأُنثَىٰ", "وَٱلْأُنثَىٰ article candidate must reconstruct byte-exact")

    quran_tanwin = tanwin_observation("قُرْءَانًا")
    check(quran_tanwin["has_tanwin"] and quran_tanwin["has_support_alif"], "قُرْءَانًا must observe tanwīn + support alif")
    rahma_tanwin = tanwin_observation("رَحْمَةً")
    check(rahma_tanwin["has_tanwin"] and not rahma_tanwin["has_support_alif"], "رَحْمَةً must observe tanwīn with NO support alif")

    conflict = article_tanwin_conflict("الكتابً")
    check(conflict is not None and conflict["status"] == "abstain", "an article+tanwin token must abstain, not resolve")

    vs_min = vocalization_state("من")["clusters"]
    vs_mina = vocalization_state("مِنَ")["clusters"]
    vs_man = vocalization_state("مَن")["clusters"]
    check(vs_min[0]["observed"]["short_vowel"] is None, "bare من must show no observed vowel on م")
    check(vs_mina[0]["observed"]["short_vowel"] == "kasra", "مِنَ must observe kasra on م")
    check(vs_man[0]["observed"]["short_vowel"] == "fatha", "مَن must observe fatha on م")

    fams = {confusable_family(ch)["family"] for ch in "بتثني"}
    check(len(fams) == 1, "بتثني must share one dot-family id")
    check(base_surface("ٱلشَّمْسَ").startswith("ٱ"), "base_surface must not fold ٱ to ا")
    check(confusable_family("أ")["kind"] == "hamza_seat" and confusable_family("ء")["kind"] == "hamza_seat",
          "hamza seats must share a family without being promoted/equated")

    runs = visual_runs("دار")
    check(len(runs) >= 2, "a right-joining letter must end a visual run mid-word")
    check(base_surface("دار") == "دار", "a visual run boundary must never split the word surface")

    unresolved = carrier_or_radical("نور", 1)
    check(unresolved["status"] == "unresolved", "a bare, unmarked carrier letter must stay unresolved")
    radical = carrier_or_radical("وّ", 0)
    check(radical["status"] == "radical", "a written shadda on the carrier letter settles it as a radical")

    single = grapheme_clusters("بَ")
    check(len(single) == 1 and single[0]["base"] == "ب", "a combining mark must never become its own base cluster")

    for f in failures:
        print("FAIL " + f)
    if not failures:
        print("ok   fusha_orthography self-test: grapheme/connectivity/mark/vocalization observations hold")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description="Structured orthography observations for one written token.")
    ap.add_argument("surface", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.surface:
        ap.error("need surface or --self-test")
    print(json.dumps(analyze_orthography(args.surface), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
