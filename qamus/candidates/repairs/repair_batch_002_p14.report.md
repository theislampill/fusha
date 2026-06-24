# Qamus entry-repair batch 002 — P14 (certified payload, owner-gated apply)

The repair class chosen for the best chance of certified application: the **POS/gloss-shape** defect surfaced by
SN6/SN9 — `qamus:n259` (كَظِيم, root ك ظ م) is glossed with a finite **"to …" verb** ("to suppress (or choke with)
anger or distress") although the surface كَظِيم is a **صفة مشبهة** (intensive adjective, فَعِيل). Its gloss SHAPE
must be adjectival/nominal.

## The repair (certified payload)

| field | value |
|---|---|
| source address | `qamus:n259#root=ك ظ م` |
| field path | `senses[0].gloss` (+ `definition`) |
| current | "to suppress (or choke with) anger or distress" |
| proposed | "forbearing; (one) restraining his grief/anger" |
| sarf evidence | صفة مشبهة on ك ظ م (فَعِيل); gloss-shape must be adjectival, not a finite verb (`masdar-participle-gates#verb_on_nominal`). QAC root ك ظ م agrees. Qurʾānic: 12:84 (Yaʿqūb كَظِيمٌ "suppressing his grief"), 16:58. |
| GrammarProblems gate | `human_source_review_required` (an entry source-field change → owner-gated) |

## Why it is NOT self-applied (terminal: `candidate_payload_ready`)

A **live Qamus entry mutation** requires the certified payload **+ app-helper dry-run + backup + DawahAgent/app-
helper apply**, which is **owner-gated** — Fusha does not self-drive entry mutations (the hard boundary). The
payload is certified and ready; the apply is handed off.

## Live-hover note

The defect surfaces in hover at 16:58:9 ("to suppress…" on كَظِيمٌ); 12:84:12 is pending. A hover-only `fusha`
override was **deliberately not used** here because the correct, consistent fix is at the **source** (the entry
gloss), which then propagates to every occurrence — a partial hover override would fix only the pending slot and
leave the primary mismatch, creating inconsistency. The entry repair is the right single fix, pending owner apply.

## Other repair classes (status)

- `needs_source_photo_review` (147, P11) + `source_data_issue` (57 hover tokens) — require the photographed Qamus
  corpus / OCR locator, which is owner-gated; terminally classified pending source review.
- `needs_quran_ref_verification` (10 entries, P11) — bad/range refs; owner verifies refs.
- The held-back 19 verb roots and count/source-key issues remain owner-gated (source crops needed).

P14 acceptance: one repair class **processed to a certified payload + terminally classified**; no invented data;
no live mutation without certification.
