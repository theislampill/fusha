# Source Triangulation And Public Boundary

External sources are evidence for authoring, not public output. A row may enter
the fast path only when token identity, grammar contribution, and public payload
are all safe.

Before authoring:

1. Match by Arabic surface inside the verse, not raw location alone.
2. Require a unique surface or an explicit disambiguation note.
3. Confirm root/POS/form where the row depends on morphology.
4. Confirm visible proclitics, enclitics, prepositions, suffixes, and function
   particles are represented in the authored hover or routed to nahw.
5. Keep source labels, screenshots, OCR snippets, and `informed_by` out of the
   public payload.
6. For any public/runtime export record, require exactly
   `{src:"qamus",kind:"authored",lang:"en"}`. Legacy internal mirrors may omit
   `lang`, but export validation must not.

Reject or reroute when:

- sources agree on a host word but omit a visible clitic or preposition;
- the verse surface differs from the source surface;
- the row is a homograph, named span, PP attachment, clause-scope, condition,
  vocative, exception, or case/mood decision without sufficient grammar proof;
- the proposed hover is a phrase translation rather than the token's contextual
  contribution.

Use targeted readback after small append-only batches. Use a full public crawl
only for renderer/schema changes, milestone coverage claims, or any suspicious
targeted mismatch.
