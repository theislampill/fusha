from __future__ import annotations

import re


_DIRECT_POS = {
    "ADJ": "adjective", "ADJECTIVE": "adjective",
    "N": "noun", "NOUN": "noun", "NOUN_PLACE": "noun", "NOUN_TIME": "noun",
    "PN": "proper_noun", "PROPN": "proper_noun", "PROPER_NOUN": "proper_noun",
    "V": "verb", "VERB": "verb",
    "P": "preposition", "PREP": "preposition", "PREPOSITION": "preposition",
    "PART": "particle", "PARTICLE": "particle",
    "ACT_PART": "participle", "PASS_PART": "participle", "PARTICIPLE": "participle",
    "VN": "masdar", "MASDAR": "masdar", "VERBAL_NOUN": "masdar",
}

_RELATIONS = {
    "object_of_preposition": "prep_object",
    "prep_object": "prep_object",
    "genitive_complement": "idafa_complement",
    "idafa_complement": "idafa_complement",
    "root": "root",
    "subject": "subject",
    "object": "object",
}


def coarse_pos(tag: object, *, source: str) -> str | None:
    if tag is None:
        return None
    key = re.sub(r"[^A-Z0-9]+", "_", str(tag).upper()).strip("_")
    if key in _DIRECT_POS:
        return _DIRECT_POS[key]
    if key.startswith("NOUN") or key.startswith("N_"):
        return "noun"
    if key.startswith("VERB") or key.startswith("V_"):
        return "verb"
    if "PARTICIPLE" in key:
        return "participle"
    if "ADJ" in key:
        return "adjective"
    return None


def relation_label(label: object) -> str | None:
    if label is None:
        return None
    key = re.sub(r"[^a-z0-9]+", "_", str(label).lower()).strip("_")
    return _RELATIONS.get(key)


def segment_boundaries(segments: list[object], whole_surface: str) -> tuple[int, ...]:
    surfaces = [str(item.get("surface", "")) if isinstance(item, dict) else str(item) for item in segments]
    if not surfaces:
        surfaces = [whole_surface]
    offsets = []
    cursor = 0
    for surface in surfaces[:-1]:
        cursor += len(surface)
        offsets.append(cursor)
    return tuple(offsets)
