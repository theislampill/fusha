#!/usr/bin/env python3
"""Shared source reader and deterministic builders for the qg ontology registry.

The live CSS is an external input to this public Fusha checkout.  This module
keeps the source boundary explicit while making the generated registry and
collision report reproducible from the CSS text plus the schema enum.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSS_PATH = ROOT / "qamus" / "registry" / "palette-source-snapshot.css"
SCHEMA_PATH = ROOT / "qamus" / "schemas" / "morphosyntax-token.schema.json"
REGISTRY_PATH = ROOT / "qamus" / "registry" / "qg-class-reconciliation.json"
MATRIX_PATH = ROOT / "qamus" / "registry" / "palette-collision-matrix.json"

LEGACY_ALIASES = {"qg-negative": "qg-negation"}
OWNER_NAMED_PAIRS = {
    tuple(sorted(pair))
    for pair in (
        ("qg-conjunction", "qg-particle"),
        ("qg-question", "qg-subject-pronoun"),
        ("qg-preposition", "qg-oath"),
        ("qg-negation", "qg-result-fa"),
    )
}

QG_KEY_CLASSES = {
    "qg-verb-stem", "qg-noun-stem", "qg-noun", "qg-adjective", "qg-proper-noun",
    "qg-preposition", "qg-relative", "qg-demonstrative", "qg-possessive-pronoun",
    "qg-object-pronoun", "qg-subject-pronoun", "qg-pronoun", "qg-referential-pronoun",
    "qg-article", "qg-conjunction", "qg-result-fa", "qg-negation", "qg-exception",
    "qg-particle", "qg-emphasis", "qg-alternative", "qg-conditional", "qg-ma-particle",
    "qg-future-particle", "qg-lam", "qg-question", "qg-vocative", "qg-oath", "qg-number",
}

LEGEND_CLASSES = {
    "qg-verb-stem", "qg-verb-prefix", "qg-noun-stem", "qg-adjective", "qg-proper-noun",
    "qg-number", "qg-article", "qg-preposition", "qg-conjunction", "qg-negation",
    "qg-relative", "qg-conditional", "qg-exception", "qg-emphasis", "qg-pronoun",
}

ROLE_BY_CLASS = {
    "qg-verb-stem": ["stem"],
    "qg-verb": ["stem"],
    "qg-verb-prefix": ["verb_prefix", "form_v_prefix", "imperfect_prefix"],
    "qg-noun-stem": ["stem"],
    "qg-noun": ["stem"],
    "qg-adjective": ["stem"],
    "qg-proper-noun": ["stem"],
    "qg-number": ["stem", "number"],
    "qg-article": ["definite_article"],
    "qg-preposition": ["preposition", "prefix_preposition"],
    "qg-oath": ["prefix_oath"],
    "qg-conjunction": ["conjunction_particle", "prefix_conjunction", "prefix_coordination_fa"],
    "qg-particle": [
        "particle", "prefix_particle", "conditional_particle", "subordinating_particle",
        "interrogative_particle", "time_adverb", "accusative_particle", "purpose_particle",
        "prefix_supplemental_fa", "prefix_interrogative_hamza", "prefix_equalization_hamza",
        "attention_particle", "preventive_ma",
    ],
    "qg-future-particle": ["particle"],
    "qg-question": ["interrogative_particle"],
    "qg-negation": ["negative_particle"],
    "qg-ma-particle": ["particle_ma"],
    "qg-lam": ["prefix_purpose_lam", "prefix_imperative_lam", "prefix_lam"],
    "qg-result": ["result_particle"],
    "qg-result-fa": ["prefix_resumption_fa", "prefix_result_fa", "prefix_cause_fa"],
    "qg-comitative": ["prefix_comitative_waw"],
    "qg-vocative": ["vocative_particle", "vocative_support"],
    "qg-relative": ["relative_particle", "relative_pronoun"],
    "qg-conditional": ["conditional_particle"],
    "qg-interrogative": ["interrogative_particle"],
    "qg-demonstrative": ["stem"],
    "qg-referential-pronoun": ["relative_pronoun", "subject_pronoun", "object_pronoun"],
    "qg-exception": ["exceptive_particle"],
    "qg-alternative": ["particle"],
    "qg-emphasis": ["particle"],
    "qg-subject-pronoun": ["subject_pronoun"],
    "qg-object-pronoun": ["object_pronoun"],
    "qg-possessive-pronoun": ["possessive_pronoun"],
    "qg-pronoun": ["subject_pronoun", "object_pronoun", "possessive_pronoun"],
    "qg-dual-suffix": ["dual_suffix"],
    "qg-plural-suffix": ["plural_suffix"],
    "qg-derivative-prefix": ["derivative_prefix"],
    "qg-case": ["case_ending"],
    "qg-relation": ["syntax.dependency", "syntax.attachment"],
    "qg-unknown": ["other"],
    "qg-segment": ["untyped fallback"],
}

SEMANTIC_FAMILY = {
    "qg-verb-stem": "lexical verb host",
    "qg-verb": "legacy broad verb host",
    "qg-verb-prefix": "verb prefix or inflectional marker",
    "qg-noun-stem": "lexical noun host",
    "qg-noun": "legacy broad noun host",
    "qg-adjective": "adjectival host",
    "qg-proper-noun": "proper-name host",
    "qg-number": "number host",
    "qg-article": "definiteness article",
    "qg-preposition": "preposition",
    "qg-oath": "oath preposition role",
    "qg-conjunction": "coordination/conjunction",
    "qg-particle": "function particle",
    "qg-future-particle": "future/aspect particle",
    "qg-question": "interrogative role",
    "qg-negation": "negation",
    "qg-negative": "legacy negation alias",
    "qg-ma-particle": "ma particle subtype",
    "qg-lam": "lam particle subtype",
    "qg-result": "result particle",
    "qg-result-fa": "result/resumption/cause fa",
    "qg-comitative": "comitative waw",
    "qg-vocative": "vocative",
    "qg-relative": "relative role",
    "qg-conditional": "conditional role",
    "qg-interrogative": "interrogative particle subtype",
    "qg-demonstrative": "demonstrative host",
    "qg-referential-pronoun": "referential pronoun",
    "qg-exception": "exception role",
    "qg-alternative": "alternative/disjunction role",
    "qg-emphasis": "emphasis role",
    "qg-subject-pronoun": "subject pronoun",
    "qg-object-pronoun": "object pronoun",
    "qg-possessive-pronoun": "possessive pronoun",
    "qg-pronoun": "legacy broad pronoun role",
    "qg-dual-suffix": "dual suffix",
    "qg-plural-suffix": "plural suffix",
    "qg-derivative-prefix": "derivational prefix",
    "qg-case": "case/ending internal role",
    "qg-relation": "dependency/relation internal role",
    "qg-unknown": "projection-status placeholder",
    "qg-segment": "generic live fallback",
}

EXCLUSIONS = {
    "qg-verb-prefix": ["lexical verb stem", "nominal derivative marker without a typed split"],
    "qg-verb-stem": ["prefix, suffix, case ending, or dependency relation"],
    "qg-verb": ["new precise morphology where qg-verb-stem or qg-verb-prefix is available"],
    "qg-noun-stem": ["article, suffix, case ending, or pronoun segment"],
    "qg-noun": ["new precise noun host where qg-noun-stem is available"],
    "qg-adjective": ["noun host, article, or case ending"],
    "qg-proper-noun": ["root assertion by color alone"],
    "qg-number": ["number suffix or case ending"],
    "qg-dual-suffix": ["case ending or generic segment fallback"],
    "qg-plural-suffix": ["case ending or generic segment fallback"],
    "qg-derivative-prefix": ["person/tense prefix without typed derivational evidence"],
    "qg-case": ["public renderer class until Q6-2 exposes it"],
    "qg-relation": ["colour-only claim about a dependency edge"],
    "qg-unknown": ["public qg class; use projection-status"],
    "qg-segment": ["canonical semantic class; do not infer a role from its color"],
}

THEME_INPUTS = {
    "light": {
        "mode": "light",
        "du_page_css": "hsl(205 30% 93%)",
        "du_panel_css": "hsl(205 40% 99%)",
        "du_text_css": "hsl(205 55% 14%)",
        "du_page_rgb": "#e8eef3",
        "du_panel_rgb": "#fbfdfd",
        "du_text_rgb": "#102737",
        "source_note": "URETHANE token defaults paired with wbw.css; wbw.css references these tokens but does not define them.",
    },
    "dark": {
        "mode": "dark",
        "du_page_css": "hsl(205 26% 9%)",
        "du_panel_css": "hsl(205 20% 14%)",
        "du_text_css": "hsl(205 28% 91%)",
        "du_page_rgb": "#11181d",
        "du_panel_rgb": "#1d252b",
        "du_text_rgb": "#e2e9ee",
        "source_note": "URETHANE dark token defaults paired with wbw.css; wbw.css references these tokens but does not define them.",
    },
}


def read_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_class_ids(schema: dict) -> list[str]:
    return list(schema["properties"]["display"]["properties"]["segments"]["items"]["properties"]["class"]["enum"])


def _block_after_match(text: str, match: re.Match[str]) -> str:
    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index]
    raise ValueError("unterminated CSS block")


def _find_block(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.S)
    if not match:
        raise ValueError(f"CSS block not found: {pattern}")
    return _block_after_match(text, match)


def parse_qg_variables(css_text: str) -> tuple[dict[str, str], dict[str, str]]:
    default = _find_block(
        css_text,
        r"\.qword,\s*\.qg-word,\s*#wbw-legend,\s*#qtip\s*\{",
    )
    light = _find_block(
        css_text,
        r"html\[data-du-mode=\"light\"\]\s+\.qword,.*?html\[data-du-mode=\"light\"\]\s+#qtip\s*\{",
    )
    pattern = re.compile(r"^\s*(--qg-[a-z0-9-]+-color)\s*:\s*([^;]+);", re.M)
    return dict(pattern.findall(default)), dict(pattern.findall(light))


def parse_renderer_tokens(css_text: str, live_classes: set[str]) -> dict[str, dict]:
    records = {class_id: {"colour_rules": [], "opacity_rules": []} for class_id in live_classes}
    rule_pattern = re.compile(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", re.S)
    color_pattern = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)")
    opacity_pattern = re.compile(r"(?:^|;)\s*opacity\s*:\s*([^;]+)")
    for match in rule_pattern.finditer(css_text):
        selectors = match.group("selectors")
        body = match.group("body")
        classes = set(re.findall(r"\.((?:qg)-[a-z0-9-]+)", selectors)) & live_classes
        if not classes:
            continue
        colors = color_pattern.findall(body)
        opacities = opacity_pattern.findall(body)
        for class_id in classes:
            if colors:
                records[class_id]["colour_rules"].append({"selector": selectors.strip(), "value": colors[-1].strip()})
            if opacities:
                records[class_id]["opacity_rules"].append({"selector": selectors.strip(), "value": opacities[-1].strip()})
    result = {}
    for class_id, record in records.items():
        if not record["colour_rules"]:
            raise ValueError(f"live qg class has no color selector: {class_id}")
        colour_rule = record["colour_rules"][-1]
        opacity_rule = record["opacity_rules"][-1] if record["opacity_rules"] else None
        opacity = float(opacity_rule["value"]) if opacity_rule else 1.0
        token_match = re.fullmatch(r"var\((--[a-z0-9-]+)\)", colour_rule["value"])
        result[class_id] = {
            "css_selector": f".{class_id}",
            "effective_selector": colour_rule["selector"],
            "css_value": colour_rule["value"],
            "custom_property": token_match.group(1) if token_match else None,
            "opacity": opacity,
            "opacity_selector": opacity_rule["selector"] if opacity_rule else None,
        }
    return result


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{6}", value):
        raise ValueError(f"expected six-digit hex RGB, got {value!r}")
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def _rgb_to_hex(rgb: tuple[float, float, float] | tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(value))) for value in rgb)


def _resolve_var(expression: str, variables: dict[str, str], theme: str, seen: set[str] | None = None) -> tuple[int, int, int] | None:
    expression = expression.strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", expression):
        return _hex_to_rgb(expression)
    match = re.fullmatch(r"var\((--[a-z0-9-]+)\)", expression)
    if not match:
        return None
    name = match.group(1)
    if seen is None:
        seen = set()
    if name in seen:
        return None
    seen.add(name)
    if name == "--du-text":
        return _hex_to_rgb(THEME_INPUTS[theme]["du_text_rgb"])
    value = variables.get(name)
    if value is None:
        return None
    return _resolve_var(value, variables, theme, seen)


def _theme_variables(default_vars: dict[str, str], light_vars: dict[str, str], theme: str) -> dict[str, str]:
    if theme == "dark":
        return dict(default_vars)
    result = dict(default_vars)
    result.update(light_vars)
    return result


def resolve_css_colours(
    variables: dict[str, str], renderer_tokens: dict[str, dict], theme: str
) -> dict[str, dict]:
    resolved = {}
    for class_id, token in renderer_tokens.items():
        rgb = _resolve_var(token["css_value"], variables, theme)
        resolved[class_id] = {
            "css_value": token["css_value"],
            "resolved_rgb": _rgb_to_hex(rgb) if rgb is not None else None,
            "rgb": list(rgb) if rgb is not None else None,
            "opacity": token["opacity"],
            "resolvable": rgb is not None,
        }
    return resolved


def _status_for(class_id: str, live_classes: set[str]) -> str:
    if class_id == "qg-negative":
        return "legacy-alias"
    if class_id == "qg-unknown":
        return "status-only"
    if class_id in {"qg-case", "qg-relation"}:
        return "internal-canonical"
    if class_id == "qg-segment":
        return "live-generic-fallback"
    if class_id in live_classes:
        return "public-canonical"
    return "canonical-uninstantiated"


def _typed_applicability(class_id: str) -> dict:
    family = SEMANTIC_FAMILY.get(class_id, "qg display role")
    roles = ROLE_BY_CLASS.get(class_id, ["typed display segment"])
    if class_id in {"qg-case", "qg-relation"}:
        fields = ["internal fact carrier", "projection-status"]
    elif class_id == "qg-unknown":
        fields = ["projection-status"]
    elif class_id == "qg-segment":
        fields = ["pending/status reason", "segment.role when available"]
    else:
        fields = ["display.segments[].class", "display.segments[].role", "display.segments[].label"]
    return {
        "semantic_family": family,
        "segment_roles_or_status_fields": roles,
        "typed_fields": fields,
    }


def _fallback(class_id: str, status: str) -> dict:
    if status in {"internal-canonical", "status-only", "canonical-uninstantiated", "legacy-alias"} and class_id != "qg-negative":
        return {
            "status": "REQUIRED-MISSING",
            "channels": [],
            "required": "projection-status or owner-approved internal text; no public colour output",
        }
    if class_id == "qg-negative":
        return {
            "status": "existing-alias-normalization",
            "channels": ["qg-negation text label", "projection-status if rejected"],
            "required": "normalize input to qg-negation and never emit qg-negative",
        }
    if class_id == "qg-segment":
        return {
            "status": "REQUIRED-MISSING",
            "channels": ["segment.label", "segment.role"],
            "required": "a nonempty semantic role label or explicit projection-status; generic SEG/segment is insufficient",
        }
    return {
        "status": "present",
        "conditional": True,
        "channels": ["segment.label", "segment.role", "hover breakdown text"],
        "renderer_support": {
            "grammar_key": class_id in QG_KEY_CLASSES,
            "legend_entry": class_id in LEGEND_CLASSES,
        },
        "condition": "the producer must project a nonempty learner-safe label or role; blank fields remain REQUIRED-MISSING",
    }


def _exclusions(class_id: str) -> list[str]:
    return EXCLUSIONS.get(class_id, ["a different semantic role or untyped fallback"])


def _colour_missing(theme: str, reason: str) -> dict:
    return {"css_value": None, "resolved_rgb": None, "rgb": None, "opacity": None, "missing": True, "reason": reason, "theme": theme}


def build_registry(css_text: str, schema: dict, css_source: str = "qamus/registry/palette-source-snapshot.css") -> dict:
    default_vars, light_vars = parse_qg_variables(css_text)
    live_classes = {name.removeprefix("--qg-").removesuffix("-color") for name in default_vars if name != "--qg-flat-word-color"}
    live_classes |= {name.removeprefix("--qg-").removesuffix("-color") for name in light_vars if name != "--qg-flat-word-color"}
    live_classes = {f"qg-{name}" for name in live_classes}
    schema_ids = schema_class_ids(schema)
    renderer_tokens = parse_renderer_tokens(css_text, live_classes)
    colours = {}
    for theme in ("dark", "light"):
        colours[theme] = resolve_css_colours(
            _theme_variables(default_vars, light_vars, theme), renderer_tokens, theme
        )

    all_ids = sorted(set(schema_ids) | live_classes)
    classes = []
    for class_id in all_ids:
        status = _status_for(class_id, live_classes)
        canonical_id = LEGACY_ALIASES.get(class_id, class_id)
        if class_id == "qg-unknown":
            semantic_id = "projection-status"
        elif class_id == "qg-segment":
            semantic_id = "qg-segment"
        else:
            semantic_id = canonical_id
        token = renderer_tokens.get(class_id)
        if token is None and class_id in LEGACY_ALIASES:
            target_token = renderer_tokens.get(LEGACY_ALIASES[class_id])
            renderer_token = {
                "css_selector": None,
                "effective_selector": None,
                "css_value": target_token["css_value"] if target_token else None,
                "custom_property": target_token["custom_property"] if target_token else None,
                "opacity": target_token["opacity"] if target_token else None,
                "emitted": False,
                "alias_target": LEGACY_ALIASES[class_id],
            }
        elif token is None:
            renderer_token = {
                "css_selector": None,
                "effective_selector": None,
                "css_value": None,
                "custom_property": None,
                "opacity": None,
                "emitted": False,
            }
        else:
            renderer_token = dict(token)
            renderer_token["emitted"] = True
        colour = {}
        for theme in ("dark", "light"):
            if class_id in colours[theme]:
                colour[theme] = dict(colours[theme][class_id])
                colour[theme]["theme"] = theme
                colour[theme]["source"] = css_source
            elif class_id in LEGACY_ALIASES and LEGACY_ALIASES[class_id] in colours[theme]:
                colour[theme] = dict(colours[theme][LEGACY_ALIASES[class_id]])
                colour[theme]["theme"] = theme
                colour[theme]["source"] = css_source
                colour[theme]["inherited_from"] = LEGACY_ALIASES[class_id]
            else:
                colour[theme] = _colour_missing(theme, "no live CSS variable or selector")
        row = {
            "class_id": class_id,
            "semantic_class_id": semantic_id,
            "canonical_class_id": canonical_id,
            "legacy_aliases": [alias for alias, target in LEGACY_ALIASES.items() if target == class_id],
            "schema_membership": (
                "schema-enum+live-css" if class_id in schema_ids and class_id in live_classes
                else "schema-enum" if class_id in schema_ids
                else "live-css-only"
            ),
            "public_internal_status": status,
            "renderer_token": renderer_token,
            "typed_applicability": _typed_applicability(class_id),
            "exclusions": _exclusions(class_id),
            "colour": colour,
            "non_colour_fallback": _fallback(class_id, status),
        }
        if class_id == "qg-unknown":
            row["status_entry"] = {
                "points_to": "projection-status",
                "reason": "Q6-2 boundary: qg-unknown is not a public qg class.",
            }
        if class_id == "qg-verb-prefix":
            row["required_ontology_change"] = {
                "status": "REQUIRED-OWNER-DECISION",
                "action": "SPLIT",
                "person_prefix_semantic": "person/tense inflectional prefix",
                "derivational_marker_semantic": "derivational marker",
                "migration_note": "Retain qg-verb-prefix in current CSS/data. Future source-addressed projection must map the two typed facts to owner-approved classes; this lane does not rename or recolour the live class.",
                "decision_made": False,
            }
        if class_id == "qg-negation":
            row["alias_policy"] = {
                "normalizes_to": "qg-negation",
                "evidence": [
                    "docs/parser/qamus-grammar-v1-class-map.md",
                    "docs/GLOSSARY.md",
                    "tools/validate_schema_coherence.py",
                ],
                "linguistic_distinction_found": False,
                "owner_decision_required": False,
            }
        if class_id == "qg-negative":
            row["alias_policy"] = {
                "normalizes_to": "qg-negation",
                "emitted": False,
                "linguistic_distinction_found": False,
            }
        classes.append(row)

    valid_final_ids = [
        row["class_id"]
        for row in classes
        if row["public_internal_status"] in {"public-canonical", "internal-canonical"}
    ]
    public_ids = [row["class_id"] for row in classes if row["public_internal_status"] == "public-canonical"]
    internal_ids = [row["class_id"] for row in classes if row["public_internal_status"] == "internal-canonical"]
    registry = {
        "registry_version": "qg-ontology-reconciliation-v1",
        "generated_by": "tools/build_qg_ontology_registry.py",
        "source_inputs": {
            "live_css": css_source,
            "live_css_sha256": hashlib.sha256(css_text.encode("utf-8")).hexdigest(),
            "schema": "qamus/schemas/morphosyntax-token.schema.json",
            "schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
            "class_map_reference": "docs/parser/qamus-grammar-v1-class-map.md",
            "alias_reference": "tools/validate_schema_coherence.py:QG_LEGACY_ALIASES",
        },
        "inventory": {
            "live_css_class_ids": sorted(live_classes),
            "schema_enum_ids": schema_ids,
            "schema_canonical_ids": [class_id for class_id in schema_ids if class_id not in LEGACY_ALIASES],
            "legacy_alias_ids": sorted(LEGACY_ALIASES),
            "union_row_count": len(classes),
            "live_css_class_count": len(live_classes),
            "schema_enum_count": len(schema_ids),
            "schema_canonical_count": len(schema_ids) - len(LEGACY_ALIASES),
            "valid_final_count": len(valid_final_ids),
            "valid_final_definition": "public-canonical plus internal-canonical ids; excludes qg-segment fallback, qg-unknown projection-status, and legacy aliases",
            "public_canonical_count": len(public_ids),
            "internal_canonical_count": len(internal_ids),
            "status_only_count": sum(row["public_internal_status"] == "status-only" for row in classes),
            "live_generic_fallback_count": sum(row["public_internal_status"] == "live-generic-fallback" for row in classes),
            "legacy_alias_count": len(LEGACY_ALIASES),
        },
        "theme_inputs": {
            theme: {
                "mode": values["mode"],
                "backgrounds": {
                    "page": {"css_value": values["du_page_css"], "resolved_rgb": values["du_page_rgb"]},
                    "panel": {"css_value": values["du_panel_css"], "resolved_rgb": values["du_panel_rgb"]},
                },
                "du_text": {"css_value": values["du_text_css"], "resolved_rgb": values["du_text_rgb"]},
                "source_note": values["source_note"],
            }
            for theme, values in THEME_INPUTS.items()
        },
        "classes": classes,
    }
    add_accessibility(registry)
    return registry


def _srgb_channel(value: float) -> float:
    value = value / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float] | list[float]) -> float:
    r, g, b = (_srgb_channel(float(value)) for value in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground: tuple[float, float, float], background: tuple[int, int, int], opacity: float = 1.0) -> float:
    composited = tuple(foreground[index] * opacity + background[index] * (1.0 - opacity) for index in range(3))
    fg_l = relative_luminance(composited)
    bg_l = relative_luminance(background)
    return (max(fg_l, bg_l) + 0.05) / (min(fg_l, bg_l) + 0.05)


def _rgb_list(hex_value: str) -> tuple[int, int, int]:
    return _hex_to_rgb(hex_value)


def add_accessibility(registry: dict) -> None:
    backgrounds = {
        theme: {
            kind: _rgb_list(registry["theme_inputs"][theme]["backgrounds"][kind]["resolved_rgb"])
            for kind in ("page", "panel")
        }
        for theme in ("dark", "light")
    }
    for row in registry["classes"]:
        checks = {}
        for theme in ("dark", "light"):
            colour = row["colour"][theme]
            if not colour.get("rgb"):
                checks[theme] = {"available": False, "page": None, "panel": None, "failures": ["REQUIRED-MISSING"]}
                continue
            foreground = tuple(colour["rgb"])
            opacity = colour.get("opacity") or 1.0
            theme_checks = {}
            failures = []
            for kind, background in backgrounds[theme].items():
                ratio = round(contrast_ratio(foreground, background, opacity), 2)
                theme_checks[kind] = {
                    "ratio": ratio,
                    "foreground_rgb": colour["resolved_rgb"],
                    "background_rgb": _rgb_to_hex(background),
                    "opacity": opacity,
                    "normal_text_floor": 4.5,
                    "normal_text_failure": ratio < 4.5,
                }
                if ratio < 4.5:
                    failures.append(kind)
            theme_checks["available"] = True
            theme_checks["failures"] = failures
            checks[theme] = theme_checks
        row["accessibility_floor"] = checks
    live_ids = set(registry["inventory"]["live_css_class_ids"])
    live_failures = [
        row["accessibility_floor"][theme][background]
        for row in registry["classes"]
        if row["class_id"] in live_ids
        for theme in ("dark", "light")
        for background in row["accessibility_floor"][theme].get("failures", [])
        if background in {"page", "panel"}
    ]
    missing_checks = [
        (row["class_id"], theme)
        for row in registry["classes"]
        for theme in ("dark", "light")
        if not row["accessibility_floor"][theme].get("available")
    ]
    registry["accessibility_floor"] = {
        "scope": "static CSS colours against page and panel backgrounds in both themes",
        "normal_text_threshold": 4.5,
        "computed_value_runtime_validation": "separate renderer-phase deliverable",
        "failure_count": len(live_failures),
        "required_missing_count": len(missing_checks),
        "required_missing_checks": [{"class_id": class_id, "theme": theme} for class_id, theme in missing_checks],
        "class_checks": "embedded per class under classes[].accessibility_floor",
    }


def _srgb_to_xyz(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    values = []
    for channel in rgb:
        normalized = channel / 255.0
        values.append(normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4)
    r, g, b = values
    return (
        (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047,
        (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000,
        (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883,
    )


def _lab_f(value: float) -> float:
    return value ** (1 / 3) if value > 0.008856 else (7.787 * value) + (16 / 116)


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    x, y, z = _srgb_to_xyz(rgb)
    fx, fy, fz = _lab_f(x), _lab_f(y), _lab_f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e_76(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    a = rgb_to_lab(first)
    b = rgb_to_lab(second)
    return math.sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


def build_collision_matrix(registry: dict) -> dict:
    live_ids = list(registry["inventory"]["live_css_class_ids"])
    themes = {}
    for theme in ("dark", "light"):
        pairs = []
        for class_a, class_b in itertools.combinations(live_ids, 2):
            row_a = next(row for row in registry["classes"] if row["class_id"] == class_a)
            row_b = next(row for row in registry["classes"] if row["class_id"] == class_b)
            colour_a = row_a["colour"][theme]
            colour_b = row_b["colour"][theme]
            rgb_a = tuple(colour_a["rgb"])
            rgb_b = tuple(colour_b["rgb"])
            exact = rgb_a == rgb_b
            delta = round(delta_e_76(rgb_a, rgb_b), 2)
            channel_distance = max(abs(rgb_a[index] - rgb_b[index]) for index in range(3))
            classification = "exact-RGB" if exact else ("near" if delta < 10 else "acceptable-distinct")
            named = tuple(sorted((class_a, class_b))) in OWNER_NAMED_PAIRS
            flagged = named or classification != "acceptable-distinct"
            if "qg-segment" in {class_a, class_b}:
                distinguisher = {
                    "status": "REQUIRED-MISSING",
                    "present": [],
                    "required": "a semantic role label or projection-status; qg-segment cannot distinguish this pair",
                }
            else:
                distinguisher = {
                    "status": "present",
                    "conditional": True,
                    "present": ["segment.label", "segment.role", "hover breakdown text"],
                    "required_if_blank": "REQUIRED-MISSING: producer must project a nonempty learner-safe role label",
                }
            pair = {
                "class_a": class_a,
                "class_b": class_b,
                "rgb_a": list(rgb_a),
                "rgb_b": list(rgb_b),
                "hex_a": colour_a["resolved_rgb"],
                "hex_b": colour_b["resolved_rgb"],
                "max_channel_distance": channel_distance,
                "delta_e_76": delta,
                "classification": classification,
                "flagged": flagged,
                "flag_reasons": (["owner-named-pair"] if named else []) + ([classification] if classification != "acceptable-distinct" else []),
                "non_colour_distinguisher": distinguisher,
            }
            pairs.append(pair)
        themes[theme] = {
            "pair_count": len(pairs),
            "pairs": pairs,
            "summary": {
                "exact_rgb_count": sum(pair["classification"] == "exact-RGB" for pair in pairs),
                "near_count": sum(pair["classification"] == "near" for pair in pairs),
                "acceptable_distinct_count": sum(pair["classification"] == "acceptable-distinct" for pair in pairs),
                "flagged_count": sum(pair["flagged"] for pair in pairs),
                "owner_named_pair_count": sum("owner-named-pair" in pair["flag_reasons"] for pair in pairs),
            },
        }
    flagged = [
        {"theme": theme, "class_a": pair["class_a"], "class_b": pair["class_b"], "classification": pair["classification"]}
        for theme, payload in themes.items()
        for pair in payload["pairs"]
        if pair["flagged"]
    ]
    contrast_failures = []
    live_ids = set(registry["inventory"]["live_css_class_ids"])
    for row in registry["classes"]:
        if row["class_id"] not in live_ids:
            continue
        for theme in ("dark", "light"):
            checks = row["accessibility_floor"][theme]
            for background in checks.get("failures", []):
                contrast_failures.append({"class_id": row["class_id"], "theme": theme, "background": background})
    return {
        "matrix_version": "qg-palette-collision-matrix-v1",
        "generated_by": "tools/build_qg_ontology_registry.py",
        "registry_source": "qamus/registry/qg-class-reconciliation.json",
        "registry_classes": sorted(live_ids),
        "owner_named_pairs": [list(pair) for pair in sorted(OWNER_NAMED_PAIRS)],
        "distance_method": "CIE76 delta-E in Lab derived from sRGB; exact-RGB is checked before delta-E",
        "near_threshold_delta_e": 10.0,
        "themes": themes,
        "flagged_pairs": flagged,
        "accessibility_floor": {
            "normal_text_threshold": 4.5,
            "failure_count": len(contrast_failures),
            "failures": contrast_failures,
            "computed_value_runtime_validation": "separate renderer-phase deliverable",
        },
    }


def dump_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _display(value) -> str:
    if isinstance(value, list):
        return ", ".join(value)
    if isinstance(value, dict):
        return "; ".join(f"{key}={_display(item)}" for key, item in value.items())
    return str(value)


def render_reconciliation_markdown(registry: dict) -> str:
    inv = registry["inventory"]
    lines = [
        "# QG class reconciliation",
        "",
        "Generated by `tools/build_qg_ontology_registry.py` from the live CSS input and the morphosyntax schema enum.",
        "",
        "## Inventory",
        "",
        f"- Live CSS class count: **{inv['live_css_class_count']}** (37 styled roles plus `qg-segment`).",
        f"- Schema enum count: **{inv['schema_enum_count']}** (40 canonical entries plus the `qg-negative` legacy alias).",
        f"- Reconciliation rows: **{inv['union_row_count']}**.",
        f"- Valid final ontology count: **{inv['valid_final_count']}** = {inv['public_canonical_count']} public canonical + {inv['internal_canonical_count']} internal canonical; the status-only, generic fallback, and alias rows are excluded.",
        "",
        "The count is derived from the row statuses rather than asserted as a separate source of truth.",
        "",
        "## Status policy",
        "",
        "- `qg-case` and `qg-relation` remain canonical but internal pending their owner-approved projection contract.",
        "- `qg-unknown` is not a public qg class; its registry row points to `projection-status`.",
        "- `qg-segment` is retained as a live generic-fallback row for reconciliation only and is not included in the valid final ontology count.",
        "- `qg-negative` normalizes to `qg-negation`; the alias is accepted only on input and is never newly emitted.",
        "",
        "## Reconciliation table",
        "",
        "| class id | semantic id | schema/live status | public/internal status | renderer token | dark CSS → RGB | light CSS → RGB | typed applicability | exclusions | non-colour fallback |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in registry["classes"]:
        colours = row["colour"]
        dark = f"{colours['dark']['css_value'] or 'MISSING'} → {colours['dark']['resolved_rgb'] or 'MISSING'}"
        light = f"{colours['light']['css_value'] or 'MISSING'} → {colours['light']['resolved_rgb'] or 'MISSING'}"
        token = row["renderer_token"].get("custom_property") or "MISSING"
        typed = row["typed_applicability"]["semantic_family"] + " [" + ", ".join(row["typed_applicability"]["segment_roles_or_status_fields"]) + "]"
        fallback = row["non_colour_fallback"]["status"]
        lines.append(
            "| `{class_id}` | `{semantic_class_id}` | `{schema_membership}` | `{public_internal_status}` | `{token}` | `{dark}` | `{light}` | {typed} | {exclusions} | `{fallback}` |".format(
                class_id=row["class_id"], semantic_class_id=row["semantic_class_id"],
                schema_membership=row["schema_membership"], public_internal_status=row["public_internal_status"],
                token=token, dark=dark, light=light, typed=typed,
                exclusions="; ".join(row["exclusions"]), fallback=fallback,
            )
        )
    lines.extend([
        "",
        "## Required ontology change: `qg-verb-prefix`",
        "",
        "The live class must split into a typed person/tense prefix versus a derivational marker. The current class, CSS, and data are intentionally not renamed here. The migration note requires a future source-addressed projector and an owner-approved target naming/colour decision; `decision_made` is `false`.",
        "",
        "## Alias evidence",
        "",
        "The existing class-map, glossary, and schema-coherence validator all describe `qg-negative` as a legacy alias for `qg-negation`. No linguistic distinction is recorded in those sources, so this lane normalizes the alias and does not create an owner-decision branch.",
        "",
        "## Static accessibility floor",
        "",
        f"The registry embeds page/panel ratios for every row with resolvable colours. The normal-text floor is 4.5:1; the machine-readable failure count is **{registry['accessibility_floor']['failure_count']}**. Computed-value browser/runtime validation remains a separate renderer-phase deliverable.",
        "",
        "## Source boundary",
        "",
        f"CSS input: `{registry['source_inputs']['live_css']}` (SHA-256 `{registry['source_inputs']['live_css_sha256']}`). Schema input: `{registry['source_inputs']['schema']}` (SHA-256 `{registry['source_inputs']['schema_sha256']}`).",
        "",
    ])
    return "\n".join(lines)


def render_collision_markdown(matrix: dict) -> str:
    lines = [
        "# QG palette collision matrix",
        "",
        "Generated by `tools/build_qg_ontology_registry.py` from the effective CSS colour tokens. All pairwise combinations are retained in the JSON; this document lists flagged pairs and the static accessibility failures.",
        "",
        "## Method and totals",
        "",
        f"- Class-pair distance: `{matrix['distance_method']}`.",
        f"- Near threshold: delta-E < {matrix['near_threshold_delta_e']}.",
        f"- Owner-named pairs: {', '.join('`' + a + '` / `' + b + '`' for a, b in matrix['owner_named_pairs'])}.",
        "",
        "| theme | all pairs | exact-RGB | near | acceptable-distinct | flagged | owner-named flagged |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for theme in ("dark", "light"):
        summary = matrix["themes"][theme]["summary"]
        lines.append(f"| {theme} | {matrix['themes'][theme]['pair_count']} | {summary['exact_rgb_count']} | {summary['near_count']} | {summary['acceptable_distinct_count']} | {summary['flagged_count']} | {summary['owner_named_pair_count']} |")
    lines.extend([
        "",
        "## Flagged pairs",
        "",
        "`present` means the current hover/segment label or role text is available as the non-colour channel, conditionally on the producer supplying a nonempty value; blank labels remain a required-missing projection defect. Any pair containing generic `qg-segment` is `REQUIRED-MISSING` because that fallback has no semantic distinguisher.",
        "",
        "| theme | pair | classification | ΔE76 | max channel distance | reason | non-colour distinguisher |",
        "|---|---|---|---:|---:|---|---|",
    ])
    for theme in ("dark", "light"):
        for pair in matrix["themes"][theme]["pairs"]:
            if not pair["flagged"]:
                continue
            reasons = ", ".join(pair["flag_reasons"])
            distinguisher = pair["non_colour_distinguisher"]["status"]
            lines.append(f"| {theme} | `{pair['class_a']}` / `{pair['class_b']}` | {pair['classification']} | {pair['delta_e_76']:.2f} | {pair['max_channel_distance']} | {reasons} | **{distinguisher}** |")
    lines.extend([
        "",
        "## Accessibility floor failures",
        "",
        f"Threshold: **4.5:1** for normal text. The static failure count is **{matrix['accessibility_floor']['failure_count']}**. These are CSS/token-snapshot calculations; computed-value runtime validation is not claimed.",
        "",
        "| class | theme | background | ratio |",
        "|---|---|---|---:|",
    ])
    failures = matrix["accessibility_floor"]["failures"]
    registry_by_id = {}
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8")) if REGISTRY_PATH.exists() else None
    if registry:
        registry_by_id = {row["class_id"]: row for row in registry["classes"]}
    for failure in failures:
        row = registry_by_id.get(failure["class_id"])
        ratio = row["accessibility_floor"][failure["theme"]][failure["background"]]["ratio"] if row else "n/a"
        lines.append(f"| `{failure['class_id']}` | {failure['theme']} | {failure['background']} | {ratio} |")
    if not failures:
        lines.append("| none | — | — | pass |")
    lines.extend([
        "",
        "## Exact nonclaims",
        "",
        "- No renderer CSS/JS was changed by this lane.",
        "- No collision recolouring, alias renaming, or `qg-verb-prefix` split was applied.",
        "- The matrix does not certify computed browser values, forced-colours behaviour, gradients, or public DOM readback.",
        "",
    ])
    return "\n".join(lines)
