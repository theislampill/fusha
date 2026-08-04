**Status: CANDIDATE. Outside `sarf/`/`nahw/` by design; nothing here is released or certified; promotion routes through the TP-CURR packets under Sol/owner control. Machine pack consumed by `tools/curriculum_unit_consumer.py`.**

# Reference — support-alif licensing for the a-form of nunation

Nunation is written as a doubled short-vowel mark. The a-form of that mark
normally needs a following support alif, written but never pronounced. This
table licenses that support alif from the exact declared final grapheme the
mark sits on — a spelling decision only, never a case, definiteness, governor,
or function claim.

An ordinary final consonant carrying the a-form mark takes the support alif.
Three exact final-grapheme environments block it instead: a word already
ending in the tied taa, a hamza already seated on an alif carrier, and the
variant final a-spelling. In each, the mark is carried directly with nothing
added.

The hamza exemption is narrow: it fires only when the hamza's declared seat
IS alif. A hamza seated anywhere else, or with no declared seat at all, does
not qualify and still takes the support alif like an ordinary consonant —
"the word ends in a hamza" is not by itself the licensed condition.

The table also carries one absolute boundary from the source lesson: nunation
and the definite article never co-occur on the same token. A construction
declaring both is a written contradiction, and the table refuses it outright
rather than choosing a winner. The support-alif question is specific to the
a-form; the other two nunation marks, and any final ending with no declared
tanwin evidence at all, simply have no construction in this table to match.

## Pack shape — how a licence becomes a consumer row

The registered `licensing_table` analyzer matches the declared `construction`
key against the table and emits `hidden_type` and `obligatory`.

- `construction` — the declared final-grapheme/mark configuration the licence
  is keyed on.
- `hidden.type` — `support_alif_written` or `support_alif_absent`.
- `hidden.value_class` — which exempt grapheme, or which non-exempt
  condition, produced that outcome.
- `obligatory` — true for every row here: each declared construction has
  exactly one licensed outcome.

A construction absent from the table — an unpointed ending, a non-a-form
mark, the article-plus-nunation contradiction, or any other untabulated
seat — is refused with `reject_reconstruction`: the table is closed, and no
outcome is ever inferred from resemblance to a licensed row.
