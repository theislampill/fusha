# Qamus Hover Parse-Key And Color Layer

This guide turns the QAC grammar screenshot packs into a safe Fusha/Qamus design target.
The screenshots are excellent examples of colored token pieces, compact grammar tags, and
dependency arcs. They are not public provenance, not copied hover wording, and not an
authority that overrides sarf, nahw, i'rab, or local verse context.

## Mission

Every future rich hover should be able to answer three questions:

1. What is the authored Qamus gloss for this token?
2. How is the Arabic written token composed?
3. Which parse facts made that gloss safe, pending, or blocked?

The public best gloss remains concise and source-clean:

```json
{"src":"qamus","kind":"authored","lang":"en"}
```

The breakdown belongs in the separate morphosyntax layer described by
[`../qamus/reports/morphosyntax-token-contract.md`](../qamus/reports/morphosyntax-token-contract.md)
and validated by
[`../tools/validate_morphosyntax_token_metadata.py`](../tools/validate_morphosyntax_token_metadata.py).

## What The ZIP Packs Add

The three packs show a consistent pattern:

- Part 1: written-token segmentation, pronouns inside tokens, roots/forms, named-entity spans,
  idafa, sifa, badal, tamyiz, compound numbers, active/passive subjects, and kana structures.
- Part 2: governing particles, subjunctive/jussive mood, imperative/prohibition, PP attachment,
  hidden attachment, oath waw, coordination, relative clauses, and purpose lam.
- Part 3: condition/result, hal, maf'ul li-ajlih, maf'ul ma'ahu, hamza interrogation/equalization,
  inna and sisters, negative la/preventive ma, fa functions, vocatives, and exception structures.

The design lesson is not "copy the screenshots." The design lesson is: a learner needs
visible Arabic pieces, compact labels, a parse key, and a note when a token is too grammar-bound
for a one-word dictionary gloss.

## Parse-Key Shape

A parse key is a compact authored summary of the token's grammar. It should be stable enough
for validators, logs, and renderer tests.

Example:

```json
{
  "parse_key": {
    "key": "V:III:PERF:ACT:3MP+OBJ.2MS",
    "summary": "Form III perfect verb with plural subject and second-person masculine singular object suffix.",
    "components": [
      {"label": "V", "value": "Form III perfect active"},
      {"label": "SUBJ", "value": "3rd masculine plural"},
      {"label": "OBJ", "value": "2nd masculine singular"}
    ]
  }
}
```

Rules:

- `key` is ASCII and compact. Use it for tests and debugging.
- `summary` is authored Fusha prose, short enough for a tooltip.
- `components[]` are learner-facing parse rows. Keep them source-clean.
- Do not put QAC, Tafsir, Quran.com, screenshot names, OCR snippets, or `informed_by` labels
  in `parse_key`.

## Color Role Palette

Use stable role classes. Do not bind colors directly to source tags; bind them to Qamus roles.

| Role family | Class | Suggested visual treatment |
|---|---|---|
| stem verb | `qg-verb` | green accent |
| noun/common host | `qg-noun` | blue accent |
| proper name host | `qg-proper-noun` | blue plus name marker |
| pronoun segment | `qg-pronoun` | slate/indigo accent |
| preposition | `qg-preposition` | red accent |
| oath waw | `qg-oath` | red/orange accent |
| comitative waw | `qg-comitative` | orange accent |
| function particle | `qg-particle` | violet accent |
| result/cause fa | `qg-result` | magenta accent |
| definite article | `qg-article` | neutral small tag |
| relative pronoun | `qg-relative` | olive accent |
| vocative | `qg-vocative` | amber accent |
| exception | `qg-exception` | rose accent |
| case/ending | `qg-case` | small neutral mark |
| dependency/relation | `qg-relation` | thin connector or row label |

Color is an aid, not the only signal. The hover must also show text labels such as `V`, `N`,
`PRON`, `P`, `REL`, `VOC`, `OATH`, `COM`, `CAUS`, or `CASE`, so the UI remains usable for
color-blind learners and for screenshots/printouts.

## Hover Layout Target

A future rich Qamus hover should separate four layers:

1. Best gloss: one concise authored English contribution.
2. Arabic composition: colored Arabic segments in right-to-left order.
3. Parse key: compact components such as `P + N:gen + PRON.3ms`.
4. Learner note: one sentence only when needed to explain a blocker or construction.

Do not use the rich hover to translate the whole phrase when the token only contributes a
particle, preposition, suffix, or case relation. Phrase explanations belong in the learner
layer, not in the token's best gloss.

## Renderer Advice

The live renderer should eventually read scrubbed morphosyntax metadata, not infer color from
raw text:

```html
<span class="qg-token" dir="rtl" data-loc="97:1:2">
  <span class="qg-seg qg-verb" data-label="V">أَنزَلْ</span>
  <span class="qg-seg qg-pronoun" data-label="PRON">نَا</span>
  <span class="qg-seg qg-pronoun" data-label="PRON">هُ</span>
</span>
```

The hover body can render:

```text
We sent it down
V: Form IV perfect active
SUBJ: 1st person plural
OBJ: 3rd masculine singular
```

The HTML must not contain source names in public tooltip text or `data-tr`. Internal evidence
may stay in server-side/provenance records, but the public DOM should expose only scrubbed
role classes, labels, and authored Qamus text.

## Decision Rules

- If a token has attached `بـ`, `لـ`, `كـ`, oath/comitative `وـ`, function `فـ`, article, or
  suffix pronoun, the parse key must account for it before a rich hover is approved.
- If `ما`, `و`, `ف`, `ل`, `أ`, `لا`, `إلا`, or a governing particle is present, nahw must name
  the function before the parse key can be final.
- If a verb is finite, sarf must expose form, voice, person, number, and attached pronouns.
- If a PP, idafa, relative clause, conditional, hal, purpose accusative, vocative, or exception
  decides the wording, the parse key must record the relation or leave the row pending.
- If QAC concept metadata flags a person/place/people/plant/body-part/etc., use it for routing
  and curriculum grouping only. It is not a translation source.

## Drill Link

Use [`drills/parse-key-and-color-layer.md`](drills/parse-key-and-color-layer.md) after
[`drills/hover-composition-and-routing.md`](drills/hover-composition-and-routing.md). The first
drill teaches composition; the parse-key drill teaches how to turn composition into a renderer
contract.
