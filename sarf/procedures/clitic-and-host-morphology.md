# Clitic And Host Morphology

Before accepting a host gloss, segment the written token into visible pieces:

- proclitics such as `و`, `ف`, `ب`, `ل`, `ك`, article `ال`;
- the host stem and its root/form/POS;
- suffix pronouns and inflectional endings;
- false-clitic traps such as tanwin-alif, long vowels, and lexical final letters.

An exact host match does not certify the whole written token. The public hover
must account for visible clitics when they affect the token contribution.
For rich-hover readiness, also emit a compact `parse_key.key` and one
`qamus-grammar-v1` display class per segment, following
[`../../curriculum/qamus-hover-parse-key-and-color.md`](../../curriculum/qamus-hover-parse-key-and-color.md).

Examples:

- `بِسَلَامٍ` cannot be only `peace`;
- `بِبَدْرٍ` cannot be only `Badr`;
- `جَادَلُوكَ` cannot be only `to argue/dispute`;
- `وَلْيَعْفُوا` cannot be only `pardon`.

If the clitic function is syntactic rather than purely morphological, sarf
records the segmentation and defers to nahw. Do not invent a color/parse-key
explanation for a segment whose function is still unknown; use an exact blocker
such as `particle_function_uncertified` or `preposition_role_uncertified`.
