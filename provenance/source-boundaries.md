# Source boundaries — the exact rules

This is the enforceable companion to [`README.md`](README.md). Every rule here is
phrased so it can be checked, ideally by a test or a pre-commit hook. The numbered
sections are referenced from elsewhere in the repo (e.g. "see source-boundaries §4").

---

## §0. Named sources and their roles

These are the external references Fusha consults. **All of them are internal
evidence only.** None of their *text* is ever published; their *names* may appear
only as `informed_by` labels in internal schemas/scripts.

| Source | What we may take from it (as fact) | What we must NEVER take |
|---|---|---|
| **QAC** (Quranic Arabic Corpus) | per-word **root** and **part-of-speech** — uncopyrightable linguistic facts | its English glosses, its morphology prose, the `.tsv`/data file itself |
| **Tafsir MCP / Tafsir Center iʿrāb** | per-word **iʿrāb**, **sarf**, role labels, and source-address confirmation as internal evidence | any returned explanatory prose, tafsīr/translation text, or wording copied into a public hover |
| **Tanzil** | verse/word **boundaries**, `surah:ayah` numbering, the **unaltered** Qurʾanic text as primary scripture | any Tanzil-specific formatting bundles or derived annotations as our own |
| **Quran.com** | a place to *visually confirm* a verse and its reference while authoring | any translation, tafsīr, or word gloss text |
| **sunnah.com** | reference confirmation only, where a ḥadīth ref is needed | hadith translation text; and note the project scope excludes Ṣaḥīḥayn/hadith from the public hover artifact |

If a source is not in this table, treat it as "may not consult for publication"
until it is added here with an explicit role.

Internal evidence labels should be short, source-addressed breadcrumbs rather
than copied text. Use labels such as `tafsir-center:analyze_word:6:6:26:irab_sarf`
or `quran-com:visual-ref:6:6` to record that a fact was checked; never store the
returned wording as the public hover.

## §1. Evidence vs. publication (the hard wall)

1. A fact **learned** from an external source is not publishable merely because it
   is true. It becomes publishable only by being **re-authored** as our own
   original content.
2. **Roots and POS are facts** → may be confirmed against QAC and recorded with an
   internal `informed_by:'qac'` label.
3. **Glosses, definitions, notes, example selections, and translations are
   expression** → must be **written by us from scratch**. Never paste, never
   "lightly reword", never machine-translate someone else's gloss and call it ours.
4. There is **no** publication path that copies external expressive text. If you
   cannot author it yourself, it stays out (emit `PENDING`).

## §2. The `informed_by` label policy

`informed_by` exists to keep us **honest internally** about what we cross-checked.
It is allowed under tight constraints:

- **Allowed** in internal build schemas, validation scripts, and adapter outputs —
  e.g. a record may carry `{"root":"ك ت ب","informed_by":["qac"]}` to mean *"a QAC
  lookup agreed with the root we authored."*
- It labels **which corpus a FACT was checked against** — never carries any
  external **text**. `informed_by:'qac'` is a provenance breadcrumb, not a gloss.
- **MUST be stripped before publication.** It must not appear in any committed
  public data file that ships to readers, and it must **never** appear in the
  public hover artifact (see §3).
- It is **not** a license to publish. A record can be `informed_by:'qac'` and still
  only ship if *we* authored its gloss.

## §3. The public-hover invariant (testable)

The shipped word-by-word hover/gloss artifact obeys, for **every** published entry:

```
gloss.src   === 'qamus'        // always; never an external source name
gloss.kind  === 'authored'     // always; there is no public 'imported' kind
gloss.lang  === 'en'           // always for the English hover layer
'informed_by' not in gloss     // stripped before publication
```

- A word without a confident authored gloss is **`PENDING`** or omitted —
  **never** filled from an external gloss. *Prefer PENDING over a wrong gloss.*
- A provenance test should load the artifact and assert the three lines above hold
  for 100% of entries, with zero external source names anywhere in the payload.

## §4. Qurʾanic text is unaltered

- Qurʾanic text, where reproduced, is reproduced **exactly** — no normalization
  into the display text, no "cleaning", no substitution of letters or marks.
- The `tools/normalize_ar.py` keys (`norm`, `norm_strict`, `bare`) are **match
  keys only**; they are computed *alongside* the text for lookup and are **never**
  written back over the display/scripture text.
- Verse references use `surah:ayah` (e.g. `2:255`); word-level refs may extend to
  `surah:ayah:word` but never renumber the canonical text.

## §5. Matching discipline (so provenance can't be faked by a bad match)

A correct provenance chain is worthless if the word was matched to the wrong
entry. The following regressions are **mandatory** constraints on any tool that
attaches a root/sense/gloss to a Qurʾanic word — they are baked into
`tools/normalize_ar.py` and must be respected, not re-implemented:

- `norm()` drops hamza + harakāt, so it **must not, by itself, certify a
  root/sense**: `إِلَيْنَا` is **not** root `ل ي ن`; `إيمان ≠ أيمان`;
  `يَأْمُرُونَ ≠ يَمُرُّونَ`. Use `norm_strict()` or a QAC fact to certify.
- A **verb gloss must not land on a noun**: `رَسُولًا ≠ 'to send'`;
  `ٱبْن`/`بَنَات ≠ 'to build'`.
- A **proper name is not a verb**: `مُحَمَّد ≠ 'to praise'`;
  `صَٰلِحًا ≠` the Prophet Ṣāliḥ.
- **Short particles are diacritic-homographs** distinguished by the harakah on the
  **content** letter (which may sit after a و/ف proclitic), not the first letter:
  `مَن` (fatḥa, 'who') vs `مِن` (kasra, 'from', incl. `وَمِنَ`); `لِمَا` vs `لَمَّا`
  (shadda); `كُلّ` vs `كَلَّا`; `نِعْمَ` vs `نَعَمْ`; `أَنِّي` vs `أَنَّى`;
  `لَمْ` ('not') vs `لِمَ` ('why').
- **Same-root polysemes need context**: `ٱلْمُلْك ≠ 'angels'`;
  `أَنْهَٰر ≠ 'daytime'`; `يَقْدِرُ` in a rizq context = 'restricts', not 'is able'.
- When any of these is in doubt, **emit `PENDING`** rather than a wrong gloss.

Use the reusable helpers `norm`, `norm_strict`, `bare`, `haraka_on`, `shadda_on`,
`is_man_who` from `tools/normalize_ar.py`. Do not redefine them.

## §6. What may / may not be committed (pre-commit checklist)

Before committing to this **public** repo, confirm every item:

- [ ] No external corpus file is staged (`*.tsv` from QAC, Tanzil dumps,
      Quran.com/sunnah.com exports). These are user-fetched offline, never bundled.
- [ ] No external **gloss/definition/translation text** appears in any staged file.
- [ ] No raw OCR dump, scan, or image/binary of source material is staged.
- [ ] No secrets, credentials, IP addresses, or private/live server paths
      (e.g. no `/srv/...`, no `/tmp/ssh*`, no host IPs) appear anywhere.
- [ ] No live-app / systemd / deploy / service script is included.
- [ ] Any Qurʾanic text reproduced is **byte-for-byte unaltered**.
- [ ] `informed_by` labels (if present) are confined to **internal** schemas and
      are **not** in any public artifact.
- [ ] Every published gloss is `{src:'qamus', kind:'authored', lang:'en'}`; un-authored words
      are `PENDING`/omitted.

If any box is unchecked, the commit does not go in.

## §7. Why this is defensible

- We publish **our own expression** + **uncopyrightable facts** + **unaltered
  primary scripture**.
- We consult external corpora the way a scholar consults a reference shelf: to
  **check** our work, named internally as evidence, never reproduced.
- The public artifact is self-evidently ours: `{src:'qamus', kind:'authored', lang:'en'}`,
  with `PENDING` wherever our confidence runs out.
