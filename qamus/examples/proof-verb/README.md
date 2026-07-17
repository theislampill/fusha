# PROOF-V real verb proof

This directory is the committed, candidate-mode proof packet for the one
surveyed reader occurrence `19:43:10`, whose source surface is preserved as
`فَٱتَّبِعْنِىٓ`.

Regenerate the packet from the read-only source files with:

```powershell
python tools/build_proofv_verb.py `
  --entries ..\data\entries.jsonl `
  --whitelist ..\data\rh_live_01_beta_whitelist.jsonl `
  --edges-dir ..\lanes\EDGES\full-artifacts `
  --output-dir qamus\examples\proof-verb
```

Run the bounded validator with:

```powershell
python tools/validate_proofv_verb.py --self-test
```

The packet intentionally contains no PNG. `render-proof.json` proves exact
payload/readback invariants and records that a browser screenshot was not run;
it does not claim a browser or font-rendering check. Direct target
entry/lexeme/card evidence and the exact Naḥw governor/object relation remain
typed source gaps routed to scholar packets. No learner gloss is promoted.
