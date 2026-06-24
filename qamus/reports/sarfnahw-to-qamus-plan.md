# Sarf/Nahw → Qamus / hover-gloss plan (SN6)

How the ingested corpus + upgraded skills feed live Qamus and qamus-highlight. **Review-only — Fusha writes
nothing live.** Generator: [`qamus/scripts/make_sarfnahw_candidates.py`](../scripts/make_sarfnahw_candidates.py).
Candidates: `qamus/candidates/qamus_2092/sarfnahw_{hover_candidates,entry_repair_candidates,review_queue}.jsonl`.

## What was generated

| lane | file | count | note |
|---|---|---:|---|
| hover candidates | `sarfnahw_hover_candidates.jsonl` | 16 | verb-form + function-word authored glosses |
| — of which export-ready now | (flag `public_export_allowed`) | 13 | surface-stable, non-homograph, not already live |
| entry-repair candidates | `sarfnahw_entry_repair_candidates.jsonl` | 1 | POS/gloss-shape; **no mutation from Fusha** |
| review queue | `sarfnahw_review_queue.jsonl` | 26 | homograph/ambiguous (10) + plural-coverage ops (13) + … |

Dedup: every candidate is keyed on `norm_strict` and checked against the live authored batch
(`authored_gloss_batch_001.jsonl`) and the 2,092 index. Surfaces already live (قَالَ, أَنزَلَ, ءَامَنُوا…) are
dropped. Homograph surfaces (ذَكَر, مَا, مَن, لَمَّا…) are routed to the review queue, never auto-exported — the P5
lesson.

## The 13 export-ready hover candidates (form-aware, dominant-sense)

نَزَّلَ "sent down (gradually)" · أَخْرَجَ "brought forth" · تَذَكَّرَ "took heed" · اِتَّقَى "was mindful (of Allah)" ·
اِزْدَادُوا "they increased" · اِسْتَغْفِرُوا "seek forgiveness" · يَسْتَكْبِرُونَ "they act arrogantly" · إِنفَاق
"spending" (maṣdar) · كَافِرُونَ "disbelievers" (ism fāʿil) · مَخْلُوق "created (thing)" (ism mafʿūl) · مَدَّ
"extended" (geminate) · زَلْزَلَتِ "quaked" (quadriliteral) · أَقَامُوا "established" (hollow Form IV).

Each carries: a source address, the surface, the **public_record that would ship** (`{src:qamus,kind:authored,
lang:en,text}`), and INTERNAL evidence (`sarf_evidence` = the verb measure; `qamus_entries` = the matched root
entry; `informed_by:[qac,qamus]`). The evidence and any reference name **never** ship.

## Entry-repair lane (1)

`qamus:n259 كَظِيم` is filed as a Noun but glossed "to suppress (or choke with) anger" — a finite-verb gloss on a
صفة مشبهة. Proposed direction: reshape to a nominal/adjectival gloss ("one who restrains [his] anger"); **do not
change the root**. This is a repair *candidate* only — any entry change goes through the owner-gated
app-helper/DawahAgent path, never from Fusha. (The curator's noun glosses are otherwise clean — the S7/P6
noun-keying-style finding holds; the repair lane is correctly small, not inflated.)

## Plural-coverage opportunities (13)

The corpus gives 451 singular↔plural pairs. Where a singular is already a Qamus entry but its broken plural is not
indexed (كِتَاب→كُتُب, قَلَم→أَقْلَام…), the review queue flags adding the plural to the entry's `forms[]`/plural
field so the plural **token** resolves to the singular lemma — a real coverage lever, owner-gated.

## Hand-off to SN7

The 13 export-ready hover candidates are eligible for the established hover-only path — 2-vote certification →
`export_hover_decisions.py` → git-ignored server ref → `rebuild.sh` → live verify. Entry-repair + plural-coverage
require entry mutation and stay owner-gated (not applied from Fusha). If the live loop cannot be completed safely
this session, the candidates are terminally classified here, ready for the next rebuild.
