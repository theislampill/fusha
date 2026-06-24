#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F11 — static verifier: the homograph/POS distinctions that must never collapse.

Confirms (via tools/normalize_ar.py) that the exact qamus-highlight bug classes cannot recur, and that the
regression fixtures are well-formed JSONL. Exit non-zero on any failure. No network, no live writes.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import normalize_ar as N

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


# 1. مِنْ and مَن never collapse (content-letter harakah)
check("مَن is who, مِن is from, وَمِنَ is from",
      N.is_man_who("مَنْ") and not N.is_man_who("مِنْ") and not N.is_man_who("وَمِنَ"))
check("liaison مَنِ is who; verb مَنَّ is not who",
      N.is_man_who("مَنِ") and not N.is_man_who("مَنَّ"))
# 2. لَمْ and لِمَ never collapse (kasra distinguishes; both norm to 'لم')
check("لَمْ and لِمَ share a norm key (so a gloss must use diacritics)",
      N.norm("لَمْ") == N.norm("لِمَ"))
check("kasra distinguishes لِمَ from لَمْ",
      N.haraka_on("لِمَ", "ل") == N.KASRA and N.haraka_on("لَمْ", "ل") != N.KASRA)
# 3. إِلَيْنَا never maps to ل ي ن
check("إِلَيْنَا norm_strict keeps the hamza, ≠ لين",
      N.norm_strict("إِلَيْنَا") != N.norm_strict("لين") and "إ" in N.norm_strict("إِلَيْنَا"))
# 4. إيمان ≠ أيمان under norm_strict (faith vs oaths)
check("إيمان ≠ أيمان (norm_strict keeps hamza)", N.norm_strict("إِيمَان") != N.norm_strict("أَيْمَان"))
# 5. لِمَا (for which) vs لَمَّا (when): shadda on the mīm
check("لَمَّا has shadda on mīm, لِمَا does not", N.shadda_on("لَمَّا", "م") and not N.shadda_on("لِمَا", "م"))
# 6. كُلّ (all) vs كَلَّا (but no): vowel on the kāf
check("كُلّ ḍamma vs كَلَّا fatḥa on kāf",
      N.haraka_on("كُلًّا", "ك") == N.DAMMA and N.haraka_on("كَلَّا", "ك") == N.FATHA)
# 7. tanwīn-alef is not a نا suffix
check("قُرْءَانًا ends in tanwīn-alef (not the pronoun نا)", N.ends_tanwin_alef("قُرْءَانًا"))
# 8. (SN ingest) Form IV hamza keeps أَنزَلَ distinct from Form I/II نزل
check("أَنزَلَ (IV) ≠ نَزَلَ (I) — hamza kept by norm_strict",
      N.norm_strict("أَنزَلَ") != N.norm_strict("نَزَلَ"))
# 9. (SN ingest) Form II vs Form I separated by the shadda (norm_strict drops it, so use shadda_on)
check("نَزَّلَ (II) has shadda on zāy, نَزَلَ (I) does not",
      N.shadda_on("نَزَّلَ", "ز") and not N.shadda_on("نَزَلَ", "ز"))
# 10. (SN ingest) maṣdar ذِكْر vs noun ذَكَر share a norm key; harakah on ḏāl decides (P5 homograph)
check("ذِكْر and ذَكَر share a norm key (so a gloss must use diacritics)",
      N.norm("ذِكْر") == N.norm("ذَكَر"))
check("kasra on ḏāl marks ذِكْر (maṣdar), fatḥa marks ذَكَر (noun)",
      N.haraka_on("ذِكْر", "ذ") == N.KASRA and N.haraka_on("ذَكَر", "ذ") == N.FATHA)
# 11. fixtures well-formed
for path in ("sarf/examples/qamus-regressions.jsonl", "sarf/examples/root-form-decisions.jsonl",
             "sarf/examples/verb-measure-examples.jsonl",
             "nahw/examples/function-word-decisions.jsonl", "nahw/examples/ayah-context-decisions.jsonl",
             "qamus/examples/linguistic-decisions.sample.jsonl"):
    fp = os.path.join(os.path.dirname(__file__), "..", path)
    n = 0
    ok = True
    try:
        for line in io.open(fp, encoding="utf-8"):
            line = line.strip()
            if line:
                json.loads(line)
                n += 1
    except Exception as e:
        ok = False
        print("  parse error in %s: %s" % (path, e))
    check("fixture %s parses (%d rows)" % (path, n), ok and n > 0)

if fails:
    print("\n%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("\nALL REGRESSION CHECKS PASS")
