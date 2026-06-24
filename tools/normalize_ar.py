"""Fusha — reusable Arabic normalization + harakāt helpers (stdlib only, no app dependency).

Three normalization keys, each for a different job (never for display — display text is never altered):
  * norm()        — lenient match key: strips tashkīl, maps dagger-alef→ā, DROPS hamza seats. For recall.
  * norm_strict() — keeps the hamza seat (أ إ ؤ ئ ء), so إلا/لا، أن/إنّ، إيمان/أيمان stay distinct. For
                    scripture-facing matching. PREFER THIS (or QAC) over norm() to certify a root/sense.
  * bare()        — strips only marks, keeps every base letter distinct (ة≠ه، أ≠ا، ى≠ي). For enclitic detection.

Plus the harakāt helpers that proved load-bearing in qamus-highlight: short Arabic function words are
homographs that norm() collapses (مَن/مِن، لِمَا/لَمَّا، كُلّ/كَلَّا، نِعْمَ/نَعَمْ، أَنِّي/أَنَّى). The ONLY thing that
distinguishes them is a harakah on the CONTENT letter — which may sit AFTER a و/ف proclitic, so reading
the FIRST letter's vowel is wrong (that bug glossed وَمِنَ "and from" as "and whoever"). Read the content letter.
"""
import unicodedata

KASRA, FATHA, DAMMA, SHADDA = "ِ", "َ", "ُ", "ّ"


def norm(s):
    """Lenient match key: strips tashkīl/tatweel/Qur'anic marks, dagger-alef→ا, DROPS hamza seats, folds
    ى→ي، ة→ه. Recall only — NEVER enough on its own to certify a root, sense, or hover gloss."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).replace("ىٰ", "ى")
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0652:
            continue
        if o == 0x0670:
            out.append("ا")
            continue
        if o == 0x0640 or 0x0653 <= o <= 0x0655 or 0x06D6 <= o <= 0x06ED:
            continue
        out.append(ch)
    s = "".join(out)
    s = s.replace("آ", "ا").replace("ٱ", "ا")
    s = s.replace("أ", "").replace("إ", "").replace("ء", "")
    s = s.replace("ؤ", "و").replace("ئ", "ي").replace("ى", "ي").replace("ة", "ه").replace(" ", "")
    return s


def norm_strict(s):
    """Like norm() but KEEPS the hamza seat (أ إ ؤ ئ ء). Use for scripture-facing exact matching."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).replace("ىٰ", "ى")
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0652:
            continue
        if o == 0x0670:
            out.append("ا")
            continue
        if o == 0x0640 or 0x0653 <= o <= 0x0655 or 0x06D6 <= o <= 0x06ED:
            continue
        out.append(ch)
    s = "".join(out)
    return s.replace("آ", "ا").replace("ٱ", "ا").replace("ى", "ي").replace("ة", "ه").replace(" ", "")


def bare(s):
    """Strip ONLY marks/dagger-alef/tatweel, keeping every base letter distinct (ة≠ه، أ≠ا، ى≠ي)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).replace("ىٰ", "ى")
    out = []
    for ch in s:
        o = ord(ch)
        if 0x064B <= o <= 0x0655 or o == 0x0670 or o == 0x0640 or 0x06D6 <= o <= 0x06ED:
            continue
        out.append(ch)
    return "".join(out).replace("ٱ", "ا")


def haraka_on(tok, target):
    """The short vowel (fatḥa/ḍamma/kasra) on the first `target` base letter, or '' — read the CONTENT
    letter's vowel (the م of من، the ل of لما), which may sit AFTER a و/ف proclitic; checking the first
    letter is WRONG. Scans the whole harakāt cluster so it is robust to NFC mark ordering (fatḥa↔shadda)."""
    s = unicodedata.normalize("NFC", tok or "")
    for i, ch in enumerate(s):
        if ch == target:
            j = i + 1
            while j < len(s) and 0x064B <= ord(s[j]) <= 0x0652:   # any harakah/tanwīn/shadda/sukūn
                if s[j] in (KASRA, FATHA, DAMMA):
                    return s[j]
                j += 1
            return ""
    return ""


def shadda_on(tok, target):
    """True if the first `target` letter carries a shadda anywhere in its harakāt cluster (لَمَّا 'when' has
    it; لِمَا/لَمَا do not). Cluster-scan, NFC-robust."""
    s = unicodedata.normalize("NFC", tok or "")
    for i, ch in enumerate(s):
        if ch == target:
            j = i + 1
            while j < len(s) and 0x064B <= ord(s[j]) <= 0x0652:
                if s[j] == SHADDA:
                    return True
                j += 1
            return False
    return False


def is_man_who(tok):
    """True if a من-family token is the relative/interrogative مَن 'who' (mīm has NO kasra) and NOT the
    preposition مِن 'from' (kasra on mīm, incl. وَمِنَ) nor the verb مَنَّ 'to bestow' (shadda on nūn)."""
    return haraka_on(tok, "م") != KASRA and not shadda_on(tok, "ن")


def ends_tanwin_alef(raw):
    """True if the token ends in ʾalif al-tanwīn (ـًا), e.g. قُرْءَانًا — which LOOKS like stem+نا but is not."""
    s = unicodedata.normalize("NFC", raw or "")
    if not s.endswith("ا"):
        return False
    i = len(s) - 2
    while i >= 0 and (0x06D6 <= ord(s[i]) <= 0x06ED or ord(s[i]) == 0x0640):
        i -= 1
    return i >= 0 and 0x064B <= ord(s[i]) <= 0x064D


if __name__ == "__main__":
    # self-check: the homograph distinctions that must never collapse
    assert norm_strict("إِلَيْنَا") != norm_strict("لين"), "إلينا must not look like ل ي ن"
    assert is_man_who("مَنْ") and not is_man_who("مِنْ") and not is_man_who("وَمِنَ"), "مَن/مِن/وَمِنَ"
    assert is_man_who("مَنِ") and not is_man_who("مَنَّ"), "liaison مَنِ is who; verb مَنَّ is not"
    assert not shadda_on("لِمَا", "م") and shadda_on("لَمَّا", "م"), "لِمَا vs لَمَّا"
    assert haraka_on("كُلًّا", "ك") == DAMMA and haraka_on("كَلَّا", "ك") == FATHA, "كُلّ vs كَلَّا"
    print("normalize_ar self-check OK")
