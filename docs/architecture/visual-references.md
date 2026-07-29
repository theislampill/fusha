# Visual references — controlling roles, verbatim owner captions

**Status:** adopted 2026-07-29 (institutionalization lane D, handoff steer
§28: "Visual references are controlling, with precise roles"). This appendix
records the TWO reference images the programme steers by, the owner's
captions for them VERBATIM, the locked visual constraints, and the
font-loading verification requirement.

**Where the images live.** The images are **not committed** to this
repository: repo policy forbids binary images (`.gitignore` — "Never commit:
raw source images, OCR dumps, model weights…"; `.gitattributes` declares
text-only families; precedent commit `c45caf6` — the durable render
attestation is `render-proof.json`, never a PNG). They live in the **owner's
local re-anchor attachment bundle** ("Fable Re-anchor Attachment Bundle —
2026-07-28", manifest `00-README-ATTACHMENT-ORDER.md`), as items:

- `09-LIVE-V003-RICH-AT-REST-AND-HOVER-REFERENCE.png` — the "to them" hover
  screenshot (§A below);
- `08-CONCEPTUAL-META-TRANSCLUSIVE-LATTICE-SKETCH.png` — the wooden-lattice
  sketch (§B below).

Reference them by these filenames. If repo policy for binaries is ever
explicitly settled in favour of committing reference imagery, that is an
owner decision to record here first — do not commit the PNGs on the strength
of this appendix.

---

## A. Current "to them" hover screenshot
*(`09-LIVE-V003-RICH-AT-REST-AND-HOVER-REFERENCE.png`; owner text verbatim)*

> Treat it as a useful structural demonstration, but not as maximal target quality.
>
> It successfully demonstrates:
>
> * visible segmentation of لِ and هُم;
> * separate particle and pronoun components;
> * internal colours retained;
> * brief Ṣarf and Naḥw explanations;
> * a composition sentence.
>
> For target completion, the canonical payload must additionally support, where certified:
>
> * exact canonical occurrence ID;
> * explicit `p007` entry edge;
> * explicit p007 sense/function edge;
> * exact morpheme occurrence ID;
> * exact host;
> * exact governor;
> * governed expression;
> * attachment;
> * scope;
> * pronoun function and referent;
> * source/evidence reverse trace;
> * links to relevant entry and occurrence views;
> * rich plain-language explanation of why the analysis applies here;
> * unresolved alternatives where applicable.
>
> A badge reading `LAM` or a semantic preposition colour does not replace the p007 entry-and-sense transclusion edge.
>
> The current visual should therefore be captioned:
>
> > Product-direction reference and current-quality example; not proof of complete entry transclusion, complete Naḥw explanation, or maximal pedagogy.

**Role, restated:** a product-direction reference, NOT the maximal target.
The additionally-required payload support listed above is exactly what the
canonical payload plane carries
(`docs/qamus/website-handoff/WEBSITE-AGENT-HANDOFF-CONTRACT-2026-07-29.md`,
`qamus/examples/p007-li-pilot/transclusion-edges.jsonl`).

## B. Conceptual wooden-lattice sketch
*(`08-CONCEPTUAL-META-TRANSCLUSIVE-LATTICE-SKETCH.png`; owner text verbatim)*

> Treat the sketch as a conceptual architecture illustration, not as:
>
> * a literal UI;
> * a fixed colour palette;
> * a required geometric layout;
> * or a claim that Arabic morphology is spatially represented exactly this way.
>
> Its controlling meaning is:
>
> * morphological and syntactic layers are interwoven;
> * roots may be discontinuous;
> * derivational and inflectional facts cross lexical structure;
> * one token may participate in several entry and fact relationships;
> * a visible surface may encode fewer units than the abstract analysis;
> * shared and fused ownership cannot always be represented as a simple linear prefix–stem–suffix chain.
>
> Translate that meaning into:
>
> * schemas;
> * typed edges;
> * candidate interfaces;
> * primary and secondary ownership;
> * guards and defeaters;
> * fixtures;
> * exact reconstruction tests.
>
> Do not imitate the sketch’s colours as the production palette.

**Role, restated:** conceptual illustration only — never a UI, never a
palette. Its controlling meanings are already realized as machinery:
multi-entry participation → `qamus/examples/website-payloads/multi_entry_liqawmihi_61_5_4.payload.json`;
typed edges → `qamus/schemas/typed-edge.schema.json` and the particle edge
ontology; fused/shared ownership → Treatment C and the exact letter-ownership
spans in `qamus/examples/p007-li-pilot/locations.json`; exact reconstruction
tests → the segment-tiling invariant in `tools/validate_website_payload.py`.

## C. Locked visual constraints
*(owner text verbatim)*

> Preserve:
>
> * Kawkab Mono Qamus as the accepted Qamus font;
> * the established colour language;
> * rich morphological colours visible before hover;
> * internal colours remaining visible during hover/focus;
> * Treatment C for genuine fused/shared realization;
> * diacritic facts in hover where independently colouring marks is unsupported;
> * Arabic joining;
> * keyboard and screen-reader access;
> * light, dark, mobile, and desktop verification.

Repo anchors for these constraints: the `qg-*` class map
(`docs/parser/qamus-grammar-v1-class-map.md`), the pinned palette snapshot
(`qamus/registry/palette-source-snapshot.css`), the renderer-boundary rule
that classes are the interface and neither side invents colours
(`docs/qamus/website-handoff/HANDOFF-RECORD.md` §4), and the neutral
`qg-unresolved` rule (contract §10.2).

## D. Font-loading verification requirement
*(owner text verbatim)*

> A visual test must prove that the intended font actually loaded through:
>
> * `document.fonts.ready`;
> * `document.fonts.check(...)`;
> * computed font inspection;
> * or an equivalent deterministic check.
>
> A screenshot made with fallback typography is not authoritative visual evidence.

Implemented instances (the pattern any new visual proof must follow):
`tools/render_fd_sufaha.js` (throws unless
`document.fonts.check('32px "Kawkab Mono Qamus"')` passes),
`tools/render_proofn_sufaha.js`, `tools/render_proof_particle.js`,
`tools/fd_compiler.py` (visible `#font-proof` banner + `font_check` in
`render-proof.json`), and `tools/validate_fd_compiler.py` (validator requires
the `document.fonts.check` marker in compiled HTML). See also
`qamus/examples/fd/README.md`.
