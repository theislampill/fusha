# Plan 15 Route Families

Goal: classify a parser/flywheel row before turning it into a hover, drill, or repair packet.

## Route families

| route | owner | learner explanation | public hover? |
|---|---|---|---|
| `parser_interface_ok` | parser | the local interface worked and no route gap was found | maybe, only after source gates |
| `lexicon_entry_needed` | sarf | the lemma/root/POS entry is missing | no |
| `stem_entry_needed` | sarf | the visible stem needs a trusted stem record | no |
| `pattern_rule_needed` | sarf | the pattern, derivative, or suffix rule is missing | no |
| `proper_name_no_root_needed` | sarf | this is a proper name/no-root token; do not invent a root | no |
| `governor_irab_fixture_needed` | nahw | the case/mood/attachment needs a justified governor | no |
| `particle_function_rule_needed` | nahw | a particle or cluster needs a contextual function rule | no |

## Exercise

Classify each row:

1. A visible participle-like word has `مـ` and plural suffix but no accepted pattern rule.
2. `أَمْ` is glossed "or" with no context function.
3. `آدَم` has no explicit proper-name/no-root route.
4. A row has `parser_interface_ok` but its source-crosswalk is still packet-only.

## Answer key

1. `pattern_rule_needed` or `stem_entry_needed`; not learner-visible as a finished hover.
2. `particle_function_rule_needed`.
3. `proper_name_no_root_needed`.
4. Not deployable; source-crosswalk packet must be accepted first.
