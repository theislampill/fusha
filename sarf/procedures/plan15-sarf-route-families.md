# Plan 15 Sarf Route Families

Use this procedure when Plan 15 or largelexicon flywheel rows need a morphology-owned terminal route.

## Routes

| route | sarf meaning | next action |
|---|---|---|
| `lexicon_entry_needed` | lemma/root/POS/form entry is absent or too weak | create a source-clean lexicon packet |
| `stem_entry_needed` | visible stem or feature bundle is absent | create a stem entry packet |
| `pattern_rule_needed` | wazn, form, derivative, participle, or suffix rule is absent | create a pattern-rule packet |
| `proper_name_no_root_needed` | token is a proper name/no-root and must not get a fake root | create explicit no-root/proper-name packet |

## Required fields

Every route packet needs:

- visible surface;
- qword denominator row id or source-addressed token id;
- source-card/source-crosswalk status;
- morphology hypothesis;
- missing table/rule;
- public-hover eligibility;
- private evidence references;
- next validator to run.

## Public boundary

Plan 15 sarf routes are internal flywheel objects. They can create candidate rows or packets, but they do not
publicly name external evidence. Public hovers remain source-clean Qamus-authored fields only.

## Examples

`ٱلْمُبْطِلُونَ` may expose article, derivative `مـ`, host, and masculine plural suffix. If the stem or participle
pattern is not accepted, route `stem_entry_needed` or `pattern_rule_needed`; do not publish a broad "falsifiers"
hover until the morphology and source address are stable.

`آدَم` should route `proper_name_no_root_needed` if the no-root/proper-name record is absent. Do not invent a root.

## Deferrals

- source identity missing -> source-card repair or source-crosswalk packet;
- function/preposition relation missing -> nahw route;
- governor/case/mood missing -> nahw/scholar route;
- renderer class missing -> qg/renderer packet.
