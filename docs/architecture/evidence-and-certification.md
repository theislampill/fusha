# Evidence and certification — the ladder, the MCP discipline, the rulings

Status: adopted 2026-07-29 (canonical architecture doc, precedence tier 4).
This doc consolidates the operational evidence rules and records the
2026-07-29 owner rulings verbatim. Binding sources it consolidates (it adds
no new policy): `docs/certification-authority.md` (fact-level layer),
`docs/certification-policy.md` (lemma fanout), 
`docs/certification-store-reconciliation.md` (store canonicity),
`qamus/schemas/two-vote-artifact.schema.json` +
`tools/validate_two_vote_artifacts.py`, `tools/certify_typed_fact.py`.

## 1. The evidence-mode ladder

Closed enum (`tools/typed_claim_contract.py` `EVIDENCE_MODES`, mirrored in
the schemas — no new values without a schema change):

`direct_source_attestation` · `cross_source_corroboration` ·
`deterministic_derivation_from_certified_facts` · `paired_form_inference` ·
`normalized_lexical_body` · `owner_or_scholar_adjudication` · `unresolved`

`unresolved` may never carry `certification.status: certified`. The
sufficiency ladder (`docs/certification-authority.md` §2) runs: single
canonical read-off → entry-store/corpus corroboration → external
triangulation → **two-vote (mandatory for any iʿrāb-bearing conclusion that
surfaces to a learner)** → owner/scholar adjudication. Rule of
non-substitution: "repetition of the same engine, the same source read twice,
or an English gloss match can never move a fact up this ladder."

Certification is **fact-level, never a row boolean**: per-fact evidence
modes, source addresses, derivation chains, defeaters, dependency indexes,
reconstructible bundles (the 8-element bundle of §3). Canaries proving it:
سُفَهَاء 11-fact packet (`qamus/examples/proof-noun-sufaha/`),
فَٱتَّبِعْنِي PROOF-V (`qamus/examples/proof-verb/` — "refusal is a feature of
the authority"), مَا PROOF-P (`qamus/examples/proof-particle/` — "a
derivation cannot outrank its weakest input").

**Transclude facts, not wording.** What certification licenses is the typed
fact at its source address. Public payload wording is authored fresh from the
fact (templates in `docs/qamus/particle-rich-hover-templates.md`); evidence
text, source names, and triangulation traces stay in the private evidence
plane. A template slot fills only from a certified or honestly-unresolved
fact; an unfillable slot forces the honest-generic variant, never a guess.

## 2. Tafsir MCP operational discipline

The Tafsir MCP is a **mandatory evidence source, and only an evidence
source** — see §4 ruling on reviewer independence.

- **Warm-up:** begin every session with `fetch_ayah(1,1)` and record it
  (`بسم الله الرحمن الرحيم`, word_count 4). First record of every committed
  MCP call file is the warm-up (`qamus/examples/p007-li-pilot/mcp-evidence.jsonl`,
  `votes-b-mcp-calls.jsonl`).
- **Surface-match, never index-trust:** accept a `word_no` only after the
  returned word (simple rasm) equals the matrix surface with
  diacritics/wasla/dagger-alif stripped — "index never trusted alone".
- **Verbatim capture:** every call recorded verbatim in the evidence plane;
  bounded retries (≤3); nulls recorded honestly (the pilot notes root and
  frequency returned null on every `analyze_word` call).

### Index hazard families (fixture-backed)

- **Basmala +4 offset** (rule `nahw-basmala-aware-loc-authority`,
  `tools/skill_fixtures/skill_rules_increment23.py` + increment23 fixtures):
  on a basmala-carrying surah's ayah 1 the basmala occupies words 1–4, so a
  word index within authority+4 is valid *with offset* (e.g. `87:1:7` =
  ayah-word 3 + 4). Beyond +4 is genuine overflow → hold. Surahs 1 and 9
  carry NO offset (surah 1's basmala is its own ayah; surah 9 has none —
  exemption defeater fixture `9:1:5`). Sibling rule: surface↔gloss basmala
  index parity disagreement = binding corruption, flag it.
- **يَٰٓأَيُّهَا family** (rule `nahw-ha-tanbih-not-pronoun`, increment21
  fixture `8:65:1`): the ها is حرف تنبيه, never a swallowed attached pronoun —
  a segmentation/offset lookalike hazard; the 2026-07-29 canary run queued a
  word-offset fixture family for يَٰٓأَيُّهَا verses.
- **WBW loc aliasing** (`qamus/examples/hazards/wbw-loc-aliasing.fixture.jsonl`):
  a live row keyed by a loc can hold a DIFFERENT token than the canonical
  index; required guard
  `tools/apply_surface_guard.require_surface_loc_double_match` — surface+loc
  double-match; loc alone never suffices.
- Also fixture-backed in `qamus/examples/hazards/`: live carve forks
  (`2:187:63`, `4:11:5`), diptote jarr sign = fatḥa (`2:34:5` لِءَادَمَ),
  and the لَـ allomorph family a strict لِ-filter misses.

## 3. Triangulation, two-vote, adjudication, revocation

**Triangulation** (ladder rung 3): external corroboration via the MCP and
named internal corpora; results stay private-side; canonical canaries are the
مِن/مَن, إِنْ/إِنَّ, عَلَىٰ triples of `docs/certification-policy.md` §3.
Machinery: `tools/build_pending_source_triangulation_table.py` and relatives.

**Two-vote v1.1** (`qamus.two_vote_artifact.v1.1`, validator
`tools/validate_two_vote_artifacts.py`): two independent reviewers (distinct
engines and reviewer ids) must agree on **conclusion + reason key** — never
on gloss text. v1.1 replaced free prose with governed vocabulary: closed
case/mood value and sign enums, `mood_basis` (`governed`/`tajarrud`/`default`
— tajarrud licenses only rafʿ, governor null valid), registry-keyed
`reason_key`/`function`/`attachment_key` from
`qamus/skills/reason-key-registry.jsonl`, `lexical_target`
(`clitic_entry`/`whole_token`), normalized segment surfaces winning in
comparison. Reviewer-B works from a sanitized rival-symmetric worklist and
its own MCP calls only. Historical unbacked claims reclassify to
`two_vote_claimed_unverified`; fabricating votes is a validator FAIL.

**Adjudication** (rung 5): owner/scholar packets via
`tools/build_phase4_gloss_adjudication_requests.py` →
`tools/reconcile_phase4_gloss_adjudication_responses.py` (certified-not-applied
rows), with scope recorded as "this occurrence only vs. rule-level". The
`qamus.adjudication_artifact.v1` schema is a named open item
(`docs/certification-authority.md` §8 Q2).

**Revocation** (`docs/certification-authority.md` §5,
`tools/certify_typed_fact.py`): source change → `review_required` +
mechanical flagging of dependents; cascade de-certification of derived facts;
defeater fires → `blocked`; no silent downgrade — history is reclassified,
never rewritten. Store canonicity: the typed-claim plane is canonical for
fact identity/status going forward; token-layer ledgers are frozen historical
evidence; a certified count must name its store and mapping status
(`docs/certification-store-reconciliation.md`).

## 4. Owner rulings, 2026-07-29 (handoff steer §20/§26 — recorded verbatim)

From the owner decision ledger (precedence tier 2), "Rate-limit handoff
rulings — 2026-07-29 (§20/§26 of the handoff steer, controlling)":

> - **Function-certification rung ANSWERED**: an exact, surface-matched
>   source statement of حرف جر MAY certify occurrence-level
>   contextual_function via direct_source_attestation (conditions: exact
>   occurrence matched, source explicitly states the function, no
>   contradiction, typed fact does not exceed the source). It does NOT
>   auto-certify governor/governed/attachment/case sign/scope/sense nuance —
>   those keep their own policies. (The direct-source-w1 260 function facts
>   become certifiable under this ruling.)
> - **Reason keys**: the 22 new keys register as CANDIDATE vocabulary;
>   promote per-key when documented + used by verified artifacts +
>   non-conflating + fixtures pass. No blanket promotion.
> - **Arbitration/scholar**: genuine disputes stay unresolved and
>   non-blocking; owner is never asked to guess.
> - **n225/n912 roots**: direct attestation = candidate root; certify only
>   after required corroboration/review; never hold unrelated work.

Standing structural rule restated (owner doctrine, 2026-07-29): **the MCP is
an evidence source, NOT reviewer-B.** Both vote lanes may consult it
independently; an MCP answer is never itself a vote, and the same engine read
twice never advances a fact (rule of non-substitution).

---
Verified against: commit 637d7da (origin/main, 2026-07-29). Artifacts:
`docs/certification-authority.md`, `docs/certification-policy.md`,
`docs/certification-store-reconciliation.md`,
`tools/typed_claim_contract.py`, `tools/certify_typed_fact.py`,
`tools/validate_two_vote_artifacts.py`,
`qamus/schemas/two-vote-artifact.schema.json`,
`qamus/skills/reason-key-registry.jsonl`,
`tools/skill_fixtures/skill_rules_increment23.py`,
`tools/skill_fixtures/skill_fixtures_increment21.jsonl`,
`qamus/examples/hazards/` (4 fixture files),
`qamus/examples/p007-li-pilot/{mcp-evidence.jsonl,votes-b-mcp-calls.jsonl,reviewer-b-worklist.json,two-vote-artifacts.v1_1.jsonl}`,
`qamus/examples/{proof-noun-sufaha,proof-verb,proof-particle}/`;
rulings transcribed from the owner decision ledger tail (2026-07-29);
`tools/check_regressions.py` ALL REGRESSION CHECKS PASS.
