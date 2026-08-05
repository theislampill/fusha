# PROOF-N noun proof for سُفَهَاءُ

## Status

Pre-approved by the owner §10 execution brief. This is a candidate-only,
deploy-shaped proof lane; it does not authorize whitelist, renderer, live,
publication, deployment, or scholarly mutation.

## Goal

Prove the real end-to-end noun path for `السُّفَهَاءُ` at `quran:2:13:12`
from the actual page-context card and selected occurrence through the
documented lexical entry, certified 11-fact packet, shared F-D compiler,
rich projections, every indexed appearance, declared readback target, and
reverse trace. The lexical entry is `1ffcc554ec44`; the whitelist/page-context
entry `c59a0161fac8` is retained as a separate edge.

## Architecture

`tools/proofn_noun_sufaha.py` is the single fixture generator. It reads only
the explicitly supplied entries, whitelist, canary evidence, EDGES repair
artifacts, and the repository occurrence-appearance index. It invokes the
existing `tools.fd_compiler` contract/payload path and the FAM2 lexical
producer; it never writes the read-only inputs and never hand-authors HTML.

The generator emits a candidate `qamus.graph_edge.v1` stream containing the
page-context edge, actual card/example bridge, display-local/canonical
crosswalk, lexical form/sense/root/lexeme edges, explicit projection-input
and certified-fact-attachment edges, shared compiler projections, candidate
appearance edges, and reverse entry/card/source trace. It also emits a
manifest whose addresses make the chain independently walkable.

The generated payload has exact at-rest spans for article, lexical body, and
the final nominative mark; compact and expanded views share one payload ID;
Ṣarf and Naḥw use the public labels `Ṣarf — how this piece forms the word`
and `Naḥw — what this piece does here`; rich hover data is fact-bound; and the
final `ُ` is explicitly a Naḥw overlay, never plural-forming. The unresolved
جامد/مشتق classification remains an internal tension record and never changes
the 11 certified fact statuses.

## Validation boundary

The proofn validator runs the ten existing typed-graph checks on the
self-contained fixture, then proofn-specific checks for actual identity,
11/11 certified facts, candidate status, edge-chain closure, exact spans,
payload parity, reverse reciprocity, all indexed appearances, N-LANG
cleanliness, public/private separation, and `pre_apply_not_authorized`.
The repository harness invokes the fixture gate. A Playwright render witness
is committed as `render-proof.json`; any screenshot is local-only and no PNG
is tracked. The report says `declared_not_measured` for public readback because
this lane performs no live deployment.

## Done when

The generator, fixture tests, validator, harness hook, generated artifacts
under `qamus/examples/proof-noun-sufaha/`, `PROOFN-MANIFEST.json`, and
`docs/reports/history/2026-07-17-PROOFN-REPORT.md` are committed; all focused and full harness checks pass;
`git diff --check` is clean; no read-only input or live surface changed; and
the branch has a local `proofn:` commit with no push.
