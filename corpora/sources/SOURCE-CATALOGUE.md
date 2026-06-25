# Source catalogue

A register of the language sources Fusha draws on, and **how each is accessed**. This is a
citation catalogue, not a data dump. It exists so every catalogued candidate can carry an
honest `access_method` provenance label without ever copying source content into this repo.

## Reading rules

- A source is listed here as a **named citation label** plus an access note. The label is what
  the pipeline records in `provenance.access_method`. It is never a machine path, an IP, a
  login, or a URL to copyrighted gloss text.
- **Reference vs. content.** Sources marked *reference-only* are consulted as evidence to
  inform an **authored** Qamus gloss. We may **name** them (`informed_by: ["…"]`); we **never**
  copy their gloss wording. The public hover artifact shows only `{src:'qamus',kind:'authored'}`.
- **Text fidelity.** Qurʾān and ḥadīth Arabic is read-only and preserved verbatim wherever it
  is tokenized. Nothing is reshaped or re-pointed.
- A source's **license / terms** column is a reminder to check before redistributing anything —
  this catalogue redistributes nothing; it points.

## How `access_method` should read

Good (citation label):
> `"Matn of al-Arbaʿīn al-Nawawiyyah, standard printed edition; Arabic matn transcribed locally"`
> `"Qurʾanic ʾāyah reference (surah:ayah), verified against a public Uthmani text"`

Bad (never do this):
> a file path, a server path, an IP, a credential, or pasted dictionary gloss text.

---

## A. Primary text sources (tokenized for catalogues)

| label | scope | what we take | access note | terms reminder |
|---|---|---|---|---|
| **Qurʾān (Uthmani text)** | the 114 sūrahs | surface forms + `surah:ayah` refs | reference by `surah:ayah`; Arabic verified against a public Uthmani text. Text never altered. | Qurʾān text is in the public domain; do not alter it. |
| **al-Arbaʿīn al-Nawawiyyah (the "Forty")** | ḥadīth 1–42 (incl. Ibn Rajab's additions) | surface matn vocabulary + per-ḥadīth ref | matn supplied locally via `--src`; record the named printed edition as the `access_method`. The pipeline does **not** scrape it. | Classical matn; the *transcription/edition* you cite may carry its own editorial rights — name the edition, do not redistribute it. |

## B. Reference sources (evidence only — name, never quote)

These inform **authored** glosses and root/sense decisions. Listed so `informed_by` labels are
consistent. **No gloss text from any of these is copied into Fusha.**

| label | used for | how consulted | hard limit |
|---|---|---|---|
| **Quran.com** | cross-checking refs, surface readings | manual lookup during authoring | reference-only; never copy translation/gloss text |
| **Quranic Arabic Corpus (QAC)** | morphology / root sanity-check | consulted to *confirm* radicals, not to import | reference-only; informs, does not populate |
| **Tanzil** | verifying the Uthmani Arabic of an ʾāyah | text-fidelity check | reference-only; Arabic must match, never re-pointed |
| **sunnah.com** | locating/confirming a ḥadīth's wording & numbering | manual lookup | reference-only; never copy translation/commentary |
| **Named Arabic dictionaries** (e.g. classical lexicons) | sense disambiguation, polysemy | consulted by a human author | reference-only; authored glosses are original prose |

## C. Internal Fusha artifacts (the spine)

| label | what | how built |
|---|---|---|
| **Existing Qamus index** | the 2,092-entry index (`qamus/indexes/existing_qamus_index.min.json`) | built read-only by `qamus/scripts/build_existing_qamus_index.py` from a local export of Qamus entries; carries `norm`/`norm_strict`/`bare`/`root`/`forms` per entry |
| **`tools/normalize_ar.py`** | the three match keys + harakah helpers | the single source of truth for normalization; all catalogue scripts import it |

---

## Per-source access-method strings (copy these into `--access-method`)

Fill the bracketed edition name with the actual source you used; keep it a citation, not a path.

```
nawawi40 : "al-Arbaʿīn al-Nawawiyyah, matn — [named printed edition]; Arabic transcribed locally"
quran    : "Qurʾān Uthmani text — [named public Uthmani source]; referenced by surah:ayah, unaltered"
```

## Provenance fields the pipeline writes

Every catalogue/candidate record carries:

```json
{
  "source_scope": ["nawawi40"],
  "access_method": "<one of the citation labels above>",
  "informed_by":   [],            // optional named references (QAC, Quran.com …) — NEVER quoted
  "extracted_by":  "nawawi40-catalogue/1"
}
```

If `access_method` is left unset, stage 1 records a loud placeholder
(`"UNSPECIFIED — record the source edition/dataset before publishing candidates"`) so the gap
is visible at review time and no candidate is published with unknown provenance.
