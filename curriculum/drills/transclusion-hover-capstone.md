# Transclusion Hover Capstone

Goal: carry one visible qword from source to rendered span and back.

## Required answer fields

- entry id/code;
- source-card/source-photo locator;
- visible qword surface;
- qword denominator row;
- accepted crosswalk or packet status;
- sarf route;
- nahw route;
- qg class status;
- public/private projection;
- forward trace;
- reverse trace;
- final state.

## Capstone prompt

Given a qword row with a visible surface, accepted source-card text, accepted crosswalk, sarf `stem_entry_needed`,
and no rendered span selector, classify the row.

## Expected answer

The row is not closed. It has source identity but still needs a sarf stem entry packet and rendered-span edge. It
cannot be called rich-hover complete until the public projection, qg classes, forward trace, and reverse trace pass.
