#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the RH-LIVE-00 static admin-preview DOM fixture.

This is not a browser smoke and not live app evidence. It is a repo-side guard
for the renderer contract that previously broke Arabic tokens: exact addressed
preview rows must expose role classes and parse-key rows while keeping the
visible Qur'anic token atomic, source-clean, and non-applyable.
"""
import argparse
import html.parser
import io
import os
import re
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "qamus", "examples", "rh_live_00_admin_preview_dom_fixture.sample.html")
EXPECTED_ROWS = {
    "wbw:33:63:1": ("quran:33:63:1", "يَسْأَلُكَ", "parse:36a0d0ceeef8ebe3bc89f45d"),
    "wbw:26:139:2": ("quran:26:139:2", "فَأَهْلَكْنَاهُمْ", "parse:b18c2b82bf5b26af9a4d7bad"),
    "wbw:22:18:13": ("quran:22:18:13", "وَٱلشَّمْسُ", "parse:3bb865fcc29d0a2d68e8880e"),
    "wbw:22:18:14": ("quran:22:18:14", "وَٱلْقَمَرُ", "parse:75719beef5a053262449dced"),
    "wbw:22:18:15": ("quran:22:18:15", "وَٱلنُّجُومُ", "parse:96f4f4e1c6c2327f09cfe6da"),
    "wbw:22:18:16": ("quran:22:18:16", "وَٱلْجِبَالُ", "parse:1a7abc3d798b942b370fcc14"),
    "wbw:22:18:17": ("quran:22:18:17", "وَٱلشَّجَرُ", "parse:2a41694fd7b48715aad6a9d3"),
    "wbw:3:123:4": ("quran:3:123:4", "بِبَدْرٍ", "parse:04f29c83d06ef13407a750b1"),
    "wbw:2:213:37": ("quran:2:213:37", "لِمَا", "parse:ae6f25c79ca4888cd052cc03"),
}
EXPECTED_MORPHLINE_NEEDLES = {
    "wbw:33:63:1": ("root س أ ل", "Form I", "imperfect active", "+OBJ 2ms"),
    "wbw:26:139:2": ("root ه ل ك", "Form IV", "perfect active", "+SUBJ 1p", "+OBJ 3mp"),
    "wbw:22:18:13": ("wāw + definite noun", "coordinated nominal"),
    "wbw:22:18:14": ("wāw + definite noun", "coordinated nominal"),
    "wbw:22:18:15": ("wāw + definite noun", "coordinated nominal"),
    "wbw:22:18:16": ("wāw + definite noun", "coordinated nominal"),
    "wbw:22:18:17": ("wāw + definite noun", "coordinated nominal"),
    "wbw:3:123:4": ("ḥarf + proper noun", "bāʾ governs Badr"),
    "wbw:2:213:37": ("lām + mā", "mā function context-sensitive"),
}
REQUIRED_PANELS = {
    "identity",
    "sarf",
    "nahw",
    "segments",
    "gates",
}
REQUIRED_OPEN_PANELS = set()
REQUIRED_COLLAPSED_PANELS = REQUIRED_PANELS - REQUIRED_OPEN_PANELS
REQUIRED_GATES = {
    "address",
    "public_boundary",
    "sarf",
    "nahw",
    "source_two_vote",
    "renderer",
    "owner",
    "live_apply",
}
ROLE_CLASS_REQUIREMENTS = {
    "verb_prefix": "qg-verb-prefix",
    "verb_stem": "qg-verb-stem",
    "subject_pronoun": "qg-subject-pronoun",
    "object_pronoun": "qg-object-pronoun",
    "prefix_result_fa": "qg-result-fa",
    "prefix_conjunction": "qg-conjunction",
    "prefix_preposition": "qg-preposition",
    "prefix_lam": "qg-lam",
    "particle_ma": "qg-ma-particle",
    "definite_article": "qg-article",
    "noun_stem": "qg-noun-stem",
    "proper_noun_stem": "qg-proper-noun",
}
GENERIC_ONLY_CLASSES = {
    "qg-verb",
    "qg-noun",
    "qg-particle",
    "qg-pronoun",
}
FORBIDDEN_PUBLIC_STRINGS = (
    "informed_by",
    "qac",
    "mcp",
    "quran.com",
    "quran_com",
    "ocr",
    "source-photo",
    "source_photo",
    "/srv/",
    "\\srv\\",
    "c:\\",
)
FORBIDDEN_TOKEN_CSS = (
    "inline-block",
    "display:flex",
    "display: flex",
    "display:grid",
    "display: grid",
    "gap:",
    "margin-inline",
    "padding-inline",
    "transform:",
)
REQUIRED_STATE_CHIPS = {
    "admin_preview",
    "certified_not_applied",
    "not_live",
    "owner_not_authorized",
}
REQUIRED_TABLE_LABELS = {
    "surface",
    "role",
    "class",
    "label",
    "gloss",
    "sarf",
    "nahw",
    "kind",
    "affects",
}
FORBIDDEN_LEARNER_CHIP_LABELS = {
    "verb prefix",
    "verb stem",
    "subject pronoun",
    "object pronoun",
    "prefix result fa",
    "prefix conjunction",
    "prefix preposition",
    "prefix lam",
    "definite article",
    "noun stem",
    "proper noun stem",
    "particle ma",
}
FORBIDDEN_HOVER_PROCESS_PHRASES = {
    "public rollout",
    "owner authorization",
    "owner-authorized",
    "live mutation",
    "live preview readback",
    "route smoke",
    "fixture-only",
    "fixture_only",
    "source/two-vote",
    "source_two_vote",
    "certified_not_applied",
    "live_mutation_allowed",
    "not authorized for live mutation",
}
CONTEXT_GLOSS_PRONOUN_HINTS = {"they", "people", "he", "it", "them"}


def css_block(text, selector):
    match = re.search(r"(?:^|[}\n])\s*" + re.escape(selector) + r"\s*\{([^}]*)\}", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def contains_forbidden_token_css(block):
    compact = re.sub(r"\s+", "", block.lower())
    return [
        needle for needle in FORBIDDEN_TOKEN_CSS
        if re.sub(r"\s+", "", needle.lower()) in compact
    ]


def has_class(attrs, name):
    classes = attrs.get("class", "").split()
    return name in classes


class FixtureParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.cards = []
        self.current_card = None
        self.current_word = None
        self.current_tooltip = None
        self.current_segment_row = None
        self.current_hover_breakdown_row = None
        self.current_learner = None
        self.current_learner_in_hover = False
        self.current_morphline = None
        self.current_token_contribution = None
        self.capture_parse_key = None
        self.capture_parse_key_in_hover = False
        self.current_hover_chip = None
        self.current_mini_status = None
        self.body_attrs = {}

    def in_class(self, name):
        return any(has_class(attrs, name) for _, attrs in self.stack)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append((tag, attrs))
        if tag == "body":
            self.body_attrs = attrs
        if tag == "section" and has_class(attrs, "rh-live-preview-card"):
            self.current_card = {
                "attrs": attrs,
                "words": [],
                "tooltip_rows": [],
                "parse_keys": [],
                "panels": set(),
                "open_panels": set(),
                "gates": {},
                "gate_chips": set(),
                "segment_rows": [],
                "segment_chips": set(),
                "state_chips": set(),
                "admin_header_count": 0,
                "header_surface": "",
                "hover_preview_count": 0,
                "admin_inspector_count": 0,
                "primary_preview_count": 0,
                "secondary_panels_count": 0,
                "table_wraps": 0,
                "hover_preview_panel_leaks": 0,
                "hover_preview_table_leaks": 0,
                "hover_status_labels": set(),
                "hover_gloss_count": 0,
                "hover_parse_keys": [],
                "hover_morphlines": [],
                "hover_context_gloss": "",
                "hover_token_contribution": "",
                "hover_segment_chip_texts": [],
                "hover_breakdown_rows": [],
                "hover_text": "",
                "learner_text": "",
                "hover_learner_text": "",
                "grammar_tags": set(),
            }
            self.cards.append(self.current_card)
        if self.current_card and tag == "article" and has_class(attrs, "qg-hover-preview"):
            self.current_card["hover_preview_count"] += 1
        if self.current_card and tag == "section" and has_class(attrs, "qg-admin-inspector"):
            self.current_card["admin_inspector_count"] += 1
        if self.current_card and tag == "header" and has_class(attrs, "qg-admin-header"):
            self.current_card["admin_header_count"] += 1
        if self.current_card and self.in_class("qg-hover-preview") and tag == "details" and has_class(attrs, "qg-panel"):
            self.current_card["hover_preview_panel_leaks"] += 1
        if self.current_card and self.in_class("qg-hover-preview") and tag == "table" and has_class(attrs, "qg-segment-table"):
            self.current_card["hover_preview_table_leaks"] += 1
        if self.current_card and self.in_class("qg-hover-preview") and tag == "div" and has_class(attrs, "qg-hover-gloss"):
            self.current_card["hover_gloss_count"] += 1
            self.current_card["hover_context_gloss"] = ""
        if self.current_card and self.in_class("qg-hover-preview") and tag == "div" and has_class(attrs, "qg-hover-token-contribution"):
            self.current_token_contribution = ""
        if self.current_card and self.in_class("qg-hover-preview") and tag == "div" and has_class(attrs, "qg-hover-morphline"):
            self.current_morphline = ""
        if self.current_card and tag == "div" and has_class(attrs, "qg-primary-preview"):
            self.current_card["primary_preview_count"] += 1
        if self.current_card and tag == "div" and has_class(attrs, "qg-secondary-panels"):
            self.current_card["secondary_panels_count"] += 1
        if self.current_card and tag == "div" and has_class(attrs, "qg-table-wrap"):
            self.current_card["table_wraps"] += 1
        if self.current_card and tag == "details" and has_class(attrs, "qg-panel"):
            panel = attrs.get("data-panel")
            if panel:
                self.current_card["panels"].add(panel)
                if "open" in attrs:
                    self.current_card["open_panels"].add(panel)
        if self.current_card and tag == "li" and has_class(attrs, "qg-gate-row"):
            gate = attrs.get("data-gate")
            if gate:
                self.current_card["gates"][gate] = attrs.get("data-state")
                if has_class(attrs, "qg-gate-chip"):
                    self.current_card["gate_chips"].add(gate)
        if self.current_card and tag == "tr" and has_class(attrs, "qg-segment-row"):
            self.current_segment_row = {
                "attrs": attrs,
                "text": "",
                "labels": set(),
            }
            self.current_card["segment_rows"].append(self.current_segment_row)
        if self.current_segment_row is not None and tag == "td":
            label = attrs.get("data-label")
            if label:
                self.current_segment_row["labels"].add(label)
        if self.current_card and tag == "span" and has_class(attrs, "qg-state-chip"):
            state_key = attrs.get("data-state-key")
            if state_key:
                self.current_card["state_chips"].add(state_key)
        if self.current_card and self.in_class("qg-hover-preview") and tag == "span" and has_class(attrs, "qg-mini-status"):
            self.current_mini_status = ""
        if self.current_card and tag == "span" and has_class(attrs, "qg-segment-chip"):
            role = attrs.get("data-role")
            if role:
                self.current_card["segment_chips"].add(role)
            if self.in_class("qg-hover-preview"):
                self.current_hover_chip = {"role": role, "text": ""}
        if self.current_card and tag == "p" and has_class(attrs, "qg-learner-explanation"):
            self.current_learner = ""
            self.current_learner_in_hover = self.in_class("qg-hover-preview")
        if self.current_card and tag == "span" and has_class(attrs, "qg-preview-tag"):
            tag_name = attrs.get("data-tag")
            if tag_name:
                self.current_card["grammar_tags"].add(tag_name)
        if self.current_card and tag == "span" and has_class(attrs, "qg-header-surface"):
            self.current_card["header_surface"] = ""
        if self.current_card and tag == "span" and has_class(attrs, "qg-word"):
            self.current_word = {
                "attrs": attrs,
                "segments": [],
                "raw_text": "",
            }
            self.current_card["words"].append(self.current_word)
        if self.current_card and tag == "div" and has_class(attrs, "qg-tooltip"):
            self.current_tooltip = {"rows": []}
        if self.current_card and tag == "li" and (has_class(attrs, "qg-breakdown-row") or has_class(attrs, "qg-hover-breakdown-row")):
            self.current_card["tooltip_rows"].append({"role": attrs.get("data-role"), "text": ""})
            if self.in_class("qg-hover-preview"):
                self.current_hover_breakdown_row = {
                    "role": attrs.get("data-role"),
                    "text": "",
                    "has_contribution": False,
                    "has_sarf": False,
                    "has_nahw": False,
                }
                self.current_card["hover_breakdown_rows"].append(self.current_hover_breakdown_row)
        if self.current_hover_breakdown_row is not None:
            if tag == "span" and has_class(attrs, "qg-hover-contribution"):
                self.current_hover_breakdown_row["has_contribution"] = True
            if tag == "span" and has_class(attrs, "qg-hover-sarf-note"):
                self.current_hover_breakdown_row["has_sarf"] = True
            if tag == "span" and has_class(attrs, "qg-hover-nahw-note"):
                self.current_hover_breakdown_row["has_nahw"] = True
        if self.current_card and tag == "code" and has_class(attrs, "qg-parse-key"):
            self.capture_parse_key = ""
            self.capture_parse_key_in_hover = self.in_class("qg-hover-preview")
        if self.current_word and tag == "span" and has_class(attrs, "qg-seg"):
            self.current_word["segments"].append({
                "attrs": attrs,
                "text": "",
            })

    def handle_endtag(self, tag):
        if self.capture_parse_key is not None and tag == "code":
            if self.current_card is not None:
                self.current_card["parse_keys"].append(self.capture_parse_key.strip())
                if self.capture_parse_key_in_hover:
                    self.current_card["hover_parse_keys"].append(self.capture_parse_key.strip())
            self.capture_parse_key = None
            self.capture_parse_key_in_hover = False
        if self.current_hover_chip is not None and tag == "span":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "span" and has_class(open_attrs, "qg-segment-chip"):
                if self.current_card is not None:
                    self.current_card["hover_segment_chip_texts"].append(self.current_hover_chip)
                self.current_hover_chip = None
        if self.current_mini_status is not None and tag == "span":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "span" and has_class(open_attrs, "qg-mini-status"):
                if self.current_card is not None:
                    self.current_card["hover_status_labels"].add(self.current_mini_status.strip().lower())
                self.current_mini_status = None
        if self.current_word and tag == "span":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "span" and has_class(open_attrs, "qg-word"):
                self.current_word = None
        if self.current_tooltip and tag == "div":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "div" and has_class(open_attrs, "qg-tooltip"):
                self.current_tooltip = None
        if self.current_segment_row and tag == "tr":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "tr" and has_class(open_attrs, "qg-segment-row"):
                self.current_segment_row = None
        if self.current_hover_breakdown_row is not None and tag == "li":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "li" and has_class(open_attrs, "qg-hover-breakdown-row"):
                self.current_hover_breakdown_row = None
        if self.current_learner is not None and tag == "p":
            if self.current_card is not None:
                self.current_card["learner_text"] += self.current_learner.strip()
                if self.current_learner_in_hover:
                    self.current_card["hover_learner_text"] += self.current_learner.strip()
            self.current_learner = None
            self.current_learner_in_hover = False
        if self.current_morphline is not None and tag == "div":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "div" and has_class(open_attrs, "qg-hover-morphline"):
                if self.current_card is not None:
                    self.current_card["hover_morphlines"].append(self.current_morphline.strip())
                self.current_morphline = None
        if self.current_token_contribution is not None and tag == "div":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "div" and has_class(open_attrs, "qg-hover-token-contribution"):
                if self.current_card is not None:
                    self.current_card["hover_token_contribution"] += self.current_token_contribution.strip()
                self.current_token_contribution = None
        if self.current_card and tag == "section":
            open_tag, open_attrs = self.stack[-1] if self.stack else (None, {})
            if open_tag == "section" and has_class(open_attrs, "rh-live-preview-card"):
                self.current_card = None
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.capture_parse_key is not None:
            self.capture_parse_key += data
        if self.current_word is not None:
            self.current_word["raw_text"] += data
            if self.current_word["segments"]:
                self.current_word["segments"][-1]["text"] += data
        if self.current_card and self.stack:
            open_tag, open_attrs = self.stack[-1]
            if open_tag == "span" and has_class(open_attrs, "qg-header-surface"):
                self.current_card["header_surface"] += data
        if self.current_card and self.in_class("qg-hover-preview"):
            self.current_card["hover_text"] += data
            if self.stack:
                open_tag, open_attrs = self.stack[-1]
                if open_tag == "div" and has_class(open_attrs, "qg-hover-gloss"):
                    self.current_card["hover_context_gloss"] += data
        if self.current_card and self.current_card["tooltip_rows"]:
            self.current_card["tooltip_rows"][-1]["text"] += data
        if self.current_hover_breakdown_row is not None:
            self.current_hover_breakdown_row["text"] += data
        if self.current_segment_row is not None:
            self.current_segment_row["text"] += data
        if self.current_learner is not None:
            self.current_learner += data
        if self.current_morphline is not None:
            self.current_morphline += data
        if self.current_token_contribution is not None:
            self.current_token_contribution += data
        if self.current_hover_chip is not None:
            self.current_hover_chip["text"] += data
        if self.current_mini_status is not None:
            self.current_mini_status += data


def add(errors, message):
    errors.append(message)


def visible_word_for(card):
    words = card["words"]
    return words[0] if words else None


def validate_css(text, errors):
    lower = re.sub(r"\s+", "", text.lower())
    qg_seg = css_block(text, ".qg-seg")
    if not qg_seg:
        add(errors, "fixture must define qg segment spans")
    for needle in contains_forbidden_token_css(qg_seg):
        add(errors, "qg segment CSS contains destructive token-layout CSS: %s" % needle)
    qg_seg_compact = re.sub(r"\s+", "", qg_seg.lower())
    for required in ("display:inline", "margin:0", "padding:0", "letter-spacing:0", "word-spacing:0"):
        if required not in qg_seg_compact:
            add(errors, "fixture qg segment CSS must include %s" % required)
    if ".qg-seg" not in text or "display: inline" not in text:
        add(errors, "fixture must define qg segment spans as display:inline")
    if "white-space: nowrap" not in text:
        add(errors, "fixture must require non-breaking Arabic token wrappers")
    if "line-height: 1.9" not in text and "line-height:1.9" not in lower:
        add(errors, "fixture must reserve vertical room for Arabic diacritics")
    if ".qg-hover-preview" not in text or ".qg-admin-inspector" not in text or ".qg-secondary-panels" not in text:
        add(errors, "fixture CSS must define the RH-LIVE IA hierarchy containers")
    if ".qg-hover-morphline" not in text:
        add(errors, "fixture CSS must define compact hover morphology line")
    if ".qg-hover-token-contribution" not in text:
        add(errors, "fixture CSS must define compact token-contribution line for contextual gloss splits")
    morphline_block = css_block(text, ".qg-hover-morphline")
    if morphline_block:
        morphline_compact = re.sub(r"\s+", "", morphline_block.lower())
        for required in ("font-size:.9rem", "line-height:1.4"):
            if required not in morphline_compact:
                add(errors, "qg hover morphline CSS must include %s" % required)
    breakdown_block = css_block(text, ".qg-hover-breakdown-row")
    breakdown_compact = re.sub(r"\s+", "", breakdown_block.lower())
    if "grid-template-columns:4rem7remminmax(0,1fr)" not in breakdown_compact:
        add(errors, "qg hover breakdown rows must use fixed shared columns: 4rem 7rem minmax(0, 1fr)")
    if "grid-template-columns:autoautominmax(0,1fr)" in re.sub(r"\s+", "", text.lower()):
        add(errors, "qg hover breakdown rows must not be overridden to auto-sized label/Arabic columns")
    breakdown_seg_block = css_block(text, ".qg-hover-breakdown-row .qg-seg")
    breakdown_seg_compact = re.sub(r"\s+", "", breakdown_seg_block.lower())
    for required in ("grid-column:2", "direction:rtl", "unicode-bidi:isolate", "justify-self:end", "text-align:end", "min-width:5rem"):
        if required not in breakdown_seg_compact:
            add(errors, "qg hover breakdown segment CSS must include %s" % required)
    if ".qg-gate-chip" not in text or ".qg-state-chip" not in text or ".qg-segment-chip" not in text:
        add(errors, "fixture CSS must define compact chip treatments")
    if "@media (max-width: 760px)" not in text or "content: attr(data-label)" not in text:
        add(errors, "fixture CSS must define mobile stacked segment-table behavior")
    for css_class in sorted(set(ROLE_CLASS_REQUIREMENTS.values())):
        if "." + css_class not in text:
            add(errors, "fixture CSS must define role-aware class %s" % css_class)
        block = css_block(text, "." + css_class)
        if block and "text-decoration" in block.lower():
            add(errors, "role-aware class %s must not use default underline decoration" % css_class)
    if ".qg-seg.is-active" not in text or ".qg-seg[data-certainty=\"pending\"]" not in text:
        add(errors, "fixture CSS must reserve underline only for active/selected or pending segment states")


def validate_fixture(path):
    text = io.open(path, encoding="utf-8").read()
    lower = text.lower()
    errors = []
    for label in FORBIDDEN_PUBLIC_STRINGS:
        if label in lower:
            add(errors, "fixture leaks forbidden public/internal label: %s" % label)
    validate_css(text, errors)

    parser = FixtureParser()
    parser.feed(text)
    body = parser.body_attrs
    if body.get("data-rh-live-stage") != "RH-LIVE-00.7":
        add(errors, "body must identify RH-LIVE-00.7 stage")
    if body.get("data-admin-only") != "true":
        add(errors, "body must be admin-only")
    if body.get("data-live-mutation-allowed") != "false":
        add(errors, "body must forbid live mutation")
    if len(parser.cards) != len(EXPECTED_ROWS):
        add(errors, "expected %d preview cards, found %d" % (len(EXPECTED_ROWS), len(parser.cards)))

    seen = set()
    for card in parser.cards:
        attrs = card["attrs"]
        wbw = attrs.get("data-wbw-loc")
        quran = attrs.get("data-quran-loc")
        seen.add(wbw)
        if wbw not in EXPECTED_ROWS:
            add(errors, "unexpected preview card wbw loc: %s" % wbw)
            continue
        expected_quran, expected_surface, expected_parse = EXPECTED_ROWS[wbw]
        if quran != expected_quran:
            add(errors, "%s quran loc mismatch" % wbw)
        for key, expected in (("data-src", "qamus"), ("data-kind", "authored"), ("data-lang", "en")):
            if attrs.get(key) != expected:
                add(errors, "%s %s must be %s" % (wbw, key, expected))
        for key in ("data-public-exposable", "data-may-apply-live", "data-live-renderer-claim"):
            if attrs.get(key) != "false":
                add(errors, "%s %s must be false" % (wbw, key))
        missing_panels = REQUIRED_PANELS - card["panels"]
        if missing_panels:
            add(errors, "%s missing enriched preview panels: %s" % (wbw, sorted(missing_panels)))
        if card["open_panels"] != REQUIRED_OPEN_PANELS:
            add(errors, "%s admin inspector panels must be collapsed by default: %s" % (wbw, sorted(card["open_panels"])))
        expanded_forbidden = card["open_panels"] & REQUIRED_COLLAPSED_PANELS
        if expanded_forbidden:
            add(errors, "%s debug panels must be collapsed by default: %s" % (wbw, sorted(expanded_forbidden)))
        if card["hover_preview_count"] != 1:
            add(errors, "%s must have one actual hover preview component" % wbw)
        if card["admin_inspector_count"] != 1:
            add(errors, "%s must have one secondary admin inspector" % wbw)
        if card["hover_preview_panel_leaks"] or card["hover_preview_table_leaks"]:
            add(errors, "%s actual hover preview must not contain debug panels or segment tables" % wbw)
        if card["admin_header_count"] != 1:
            add(errors, "%s must have one admin inspector header" % wbw)
        if card["primary_preview_count"] != 0 or "hover" in card["panels"]:
            add(errors, "%s admin inspector must not duplicate the actual hover preview" % wbw)
        if card["secondary_panels_count"] != 1:
            add(errors, "%s must have one secondary panel wrapper" % wbw)
        if card["hover_gloss_count"] != 1:
            add(errors, "%s actual hover preview must have one authored gloss" % wbw)
        context_gloss = " ".join(card["hover_context_gloss"].split())
        token_gloss = " ".join(card["hover_token_contribution"].split())
        if not context_gloss:
            add(errors, "%s actual hover preview missing contextual gloss text" % wbw)
        if len(card["hover_morphlines"]) != 1:
            add(errors, "%s actual hover preview must have one compact morphology/function line" % wbw)
        else:
            morphline = " ".join(card["hover_morphlines"][0].split())
            if not morphline:
                add(errors, "%s compact morphology/function line must not be empty" % wbw)
            for needle in EXPECTED_MORPHLINE_NEEDLES.get(wbw, ()):
                if needle not in morphline:
                    add(errors, "%s compact morphology/function line missing `%s`" % (wbw, needle))
        if wbw == "wbw:33:63:1":
            if context_gloss not in ("the people ask you", "they ask you"):
                add(errors, "%s contextual gloss must distinguish the phrase reading from token contribution" % wbw)
            if token_gloss != "token: ask you":
                add(errors, "%s token contribution line must say `token: ask you`" % wbw)
            if attrs.get("data-token-contribution-gloss") != "ask you":
                add(errors, "%s data-token-contribution-gloss must be ask you" % wbw)
            if attrs.get("data-contextual-phrase-gloss") not in ("the people ask you", "they ask you"):
                add(errors, "%s data-contextual-phrase-gloss must record the contextual phrase reading" % wbw)
            if attrs.get("data-adjacent-context-required") != "true":
                add(errors, "%s adjacent context must be required for contextual phrase gloss" % wbw)
            adjacent_locs = attrs.get("data-adjacent-context-locs", "")
            if "quran:33:63:2" not in adjacent_locs or "wbw:33:63:2" not in adjacent_locs:
                add(errors, "%s adjacent context locs must include following subject token" % wbw)
            subject_source = attrs.get("data-context-subject-source", "")
            if "النَّاسُ" not in subject_source or "quran:33:63:2" not in subject_source:
                add(errors, "%s contextual subject source must record النَّاسُ at quran:33:63:2" % wbw)
            if attrs.get("data-contextual-gloss-certification-state") != "certified_not_applied_context_supported":
                add(errors, "%s contextual gloss certification state must remain certified-not-applied context-supported" % wbw)
            hover_learner = card["hover_learner_text"]
            if "النَّاسُ" not in hover_learner or "Do not read" not in hover_learner or "attached pronoun" not in hover_learner:
                add(errors, "%s learner explanation must state where the subject comes from and avoid hiding it" % wbw)
        missing_mini_status = {"admin preview", "not live"} - card["hover_status_labels"]
        if missing_mini_status:
            add(errors, "%s actual hover preview missing mini status labels: %s" % (wbw, sorted(missing_mini_status)))
        missing_state_chips = REQUIRED_STATE_CHIPS - card["state_chips"]
        if missing_state_chips:
            add(errors, "%s missing preview state chips: %s" % (wbw, sorted(missing_state_chips)))
        missing_gates = REQUIRED_GATES - set(card["gates"])
        if missing_gates:
            add(errors, "%s missing gate rows: %s" % (wbw, sorted(missing_gates)))
        missing_gate_chips = REQUIRED_GATES - card["gate_chips"]
        if missing_gate_chips:
            add(errors, "%s gates must render as compact gate chips: %s" % (wbw, sorted(missing_gate_chips)))
        if card["gates"].get("owner") != "not_authorized":
            add(errors, "%s owner gate must stay not_authorized" % wbw)
        if card["gates"].get("live_apply") != "blocked":
            add(errors, "%s live apply gate must stay blocked" % wbw)
        if not card["hover_learner_text"]:
            add(errors, "%s actual hover preview missing learner explanation text" % wbw)
        hover_text = " ".join(card["hover_text"].lower().split())
        for phrase in sorted(FORBIDDEN_HOVER_PROCESS_PHRASES):
            if phrase in hover_text:
                add(errors, "%s actual hover preview leaks admin/process phrase `%s`" % (wbw, phrase))
        if not card["grammar_tags"]:
            add(errors, "%s must expose preview-only grammar tags" % wbw)

        word = visible_word_for(card)
        if not word:
            add(errors, "%s missing visible qg-word" % wbw)
            continue
        word_attrs = word["attrs"]
        if word_attrs.get("dir") != "rtl" or word_attrs.get("lang") != "ar":
            add(errors, "%s qg-word must be dir=rtl lang=ar" % wbw)
        if word_attrs.get("data-surface") != expected_surface:
            add(errors, "%s qg-word data-surface mismatch" % wbw)
        if word_attrs.get("data-parse-key") != expected_parse:
            add(errors, "%s qg-word parse key mismatch" % wbw)
        raw_text = word["raw_text"]
        segment_text = "".join(segment["text"] for segment in word["segments"])
        if raw_text != expected_surface:
            add(errors, "%s visible word textContent must equal exact surface" % wbw)
        if segment_text != expected_surface:
            add(errors, "%s visible segment concatenation must equal exact surface" % wbw)
        if " " in raw_text or "\n" in raw_text or "\t" in raw_text:
            add(errors, "%s visible Arabic token must not contain inserted whitespace" % wbw)
        if not word["segments"]:
            add(errors, "%s visible word must contain qg-seg spans" % wbw)
        visible_roles = {segment["attrs"].get("data-role") for segment in word["segments"]}
        if visible_roles - card["segment_chips"]:
            add(errors, "%s segment chips missing roles: %s" % (wbw, sorted(visible_roles - card["segment_chips"])))
        for segment in word["segments"]:
            classes = segment["attrs"].get("class", "").split()
            role = segment["attrs"].get("data-role")
            if "qg-seg" not in classes:
                add(errors, "%s segment missing qg-seg class" % wbw)
            if not role:
                add(errors, "%s segment missing data-role" % wbw)
                continue
            required_class = ROLE_CLASS_REQUIREMENTS.get(role)
            if required_class and required_class not in classes:
                add(errors, "%s role %s must use class %s" % (wbw, role, required_class))
            if required_class and not (set(classes) - GENERIC_ONLY_CLASSES - {"qg-seg"}):
                add(errors, "%s role %s has only broad POS classes" % (wbw, role))
        if expected_parse not in card["parse_keys"]:
            add(errors, "%s tooltip parse-key element missing expected key" % wbw)
        if expected_parse not in card["hover_parse_keys"]:
            add(errors, "%s actual hover preview parse-key element missing expected key" % wbw)
        tooltip_roles = {row["role"] for row in card["tooltip_rows"]}
        if visible_roles - tooltip_roles:
            add(errors, "%s tooltip breakdown missing roles: %s" % (wbw, sorted(visible_roles - tooltip_roles)))
        hover_row_roles = {row["role"] for row in card["hover_breakdown_rows"]}
        if visible_roles - hover_row_roles:
            add(errors, "%s actual hover breakdown missing roles: %s" % (wbw, sorted(visible_roles - hover_row_roles)))
        for row in card["hover_breakdown_rows"]:
            if not row["has_contribution"] or not row["has_sarf"] or not row["has_nahw"]:
                add(errors, "%s actual hover segment role %s must include contribution, sarf, and nahw micro-facts" % (wbw, row["role"]))
        hover_chip_roles = {chip["role"] for chip in card["hover_segment_chip_texts"]}
        if visible_roles - hover_chip_roles:
            add(errors, "%s actual hover segment chips missing roles: %s" % (wbw, sorted(visible_roles - hover_chip_roles)))
        for chip in card["hover_segment_chip_texts"]:
            label = " ".join(chip["text"].split())
            label_lower = label.lower()
            if "·" not in label:
                add(errors, "%s actual hover segment chip must use learner-readable `LABEL · contribution`: %s" % (wbw, label))
            if "_" in label:
                add(errors, "%s actual hover segment chip must not expose raw role names: %s" % (wbw, label))
            for forbidden in FORBIDDEN_LEARNER_CHIP_LABELS:
                if forbidden in label_lower:
                    add(errors, "%s actual hover segment chip uses raw/debug label `%s`: %s" % (wbw, forbidden, label))
        segment_table_roles = {row["attrs"].get("data-role") for row in card["segment_rows"]}
        if visible_roles - segment_table_roles:
            add(errors, "%s segment contribution table missing roles: %s" % (wbw, sorted(visible_roles - segment_table_roles)))
        if card["table_wraps"] < 1:
            add(errors, "%s segment table must be wrapped for mobile/overflow handling" % wbw)
        for row in card["segment_rows"]:
            row_attrs = row["attrs"]
            role = row_attrs.get("data-role")
            expected_class = ROLE_CLASS_REQUIREMENTS.get(role)
            if expected_class and row_attrs.get("data-display-class") != expected_class:
                add(errors, "%s table role %s data-display-class must be %s" % (wbw, role, expected_class))
            for field in ("data-gloss", "data-sarf", "data-nahw", "data-kind", "data-affects"):
                if not row_attrs.get(field):
                    add(errors, "%s table role %s missing %s" % (wbw, role, field))
            missing_labels = REQUIRED_TABLE_LABELS - row["labels"]
            if missing_labels:
                add(errors, "%s table role %s missing mobile data-labels: %s" % (wbw, role, sorted(missing_labels)))
    missing = set(EXPECTED_ROWS) - seen
    if missing:
        add(errors, "missing preview cards: %s" % sorted(missing))
    return errors


def write_text(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def self_test():
    errors = validate_fixture(SAMPLE)
    if errors:
        raise SystemExit("self-test failed: " + "; ".join(errors[:20]))
    text = io.open(SAMPLE, encoding="utf-8").read()
    bad = text.replace("data-surface=\"يَسْأَلُكَ\"", "data-surface=\"يَسْأَلُكَ\"", 1)
    bad = bad.replace("يَ</span><span class=\"qg-seg qg-verb-stem\"", "يَ </span><span class=\"qg-seg qg-verb-stem\"", 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("textContent must equal exact surface" in error or "must not contain inserted whitespace" in error for error in bad_errors):
            raise SystemExit("self-test failed: inserted Arabic spacing regression was not caught")
    bad = text.replace('class="qg-seg qg-verb-prefix" data-role="verb_prefix"', 'class="qg-seg qg-verb" data-role="verb_prefix"', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-role.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("role verb_prefix must use class qg-verb-prefix" in error for error in bad_errors):
            raise SystemExit("self-test failed: broad POS role-color regression was not caught")
    bad = text.replace('class="qg-hover-preview"', 'class="qg-hover-preview-removed"', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-ia.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("must have one actual hover preview component" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing actual hover preview hierarchy was not caught")
    bad = text.replace('<details class="qg-panel qg-sarf-panel" data-panel="sarf">', '<details class="qg-panel qg-sarf-panel" data-panel="sarf" open>', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-open-panel.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("debug panels must be collapsed by default" in error or "admin inspector panels must be collapsed by default" in error for error in bad_errors):
            raise SystemExit("self-test failed: expanded debug panel regression was not caught")
    bad = text.replace("PFX · imperfect", "verb_prefix", 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-chip-label.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("segment chip must not expose raw role names" in error for error in bad_errors):
            raise SystemExit("self-test failed: raw learner chip label regression was not caught")
    bad = text.replace('<article aria-label="Actual hover preview" class="qg-hover-preview">', '<article aria-label="Actual hover preview" class="qg-hover-preview"><table class="qg-segment-table"></table>', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-hover-debug.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("actual hover preview must not contain debug panels or segment tables" in error for error in bad_errors):
            raise SystemExit("self-test failed: hover/debug layer separation regression was not caught")
    bad = text.replace('<span class="qg-hover-sarf-note">', '<span class="qg-hover-sarf-note-removed">', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-hover-microfact.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("must include contribution, sarf, and nahw micro-facts" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing hover micro-fact regression was not caught")
    bad = text.replace('<div class="qg-hover-morphline">', '<div class="qg-hover-morphline-removed">', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-hover-morphline.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("actual hover preview must have one compact morphology/function line" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing hover morphline regression was not caught")
    bad = text.replace('data-context-subject-source="النَّاسُ at quran:33:63:2 / wbw:33:63:2"', 'data-context-subject-source=""', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-context-subject.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("contextual subject source must record" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing contextual subject source regression was not caught")
    bad = text.replace('<div class="qg-hover-gloss">the people ask you</div>', '<div class="qg-hover-gloss">ask you</div>', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-context-gloss.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("contextual gloss must distinguish" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing contextual gloss regression was not caught")
    bad = text.replace("grid-template-columns: 4rem 7rem minmax(0, 1fr);", "grid-template-columns: auto auto minmax(0, 1fr);", 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-hover-alignment.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("fixed shared columns" in error for error in bad_errors):
            raise SystemExit("self-test failed: hover breakdown alignment regression was not caught")
    bad = text.replace("This token contributes", "Public rollout still needs owner authorization. This token contributes", 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-hover-process-language.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("actual hover preview leaks admin/process phrase" in error for error in bad_errors):
            raise SystemExit("self-test failed: learner/process language regression was not caught")
    bad = text.replace('<details class="qg-panel qg-identity-panel" data-panel="identity">', '<details class="qg-panel qg-hover-panel" data-panel="hover"><div class="qg-primary-preview"></div></details><details class="qg-panel qg-identity-panel" data-panel="identity">', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-admin-duplicate-hover.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("admin inspector must not duplicate the actual hover preview" in error for error in bad_errors):
            raise SystemExit("self-test failed: duplicate admin hover preview regression was not caught")
    print("RH-LIVE admin-preview DOM fixture self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("html", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.html:
        parser.error("provide at least one HTML fixture or --self-test")
    all_errors = []
    for path in args.html:
        all_errors.extend("%s: %s" % (path, error) for error in validate_fixture(path))
    if all_errors:
        for error in all_errors:
            print(error)
        return 1
    print("RH-LIVE admin-preview DOM fixture OK - files=%d" % len(args.html))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
