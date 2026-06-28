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
REQUIRED_PANELS = {
    "identity",
    "sarf",
    "nahw",
    "segments",
    "learner",
    "gates",
}
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


def css_block(text, selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", text, flags=re.IGNORECASE)
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
        self.current_learner = None
        self.capture_parse_key = None
        self.body_attrs = {}

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
                "header_count": 0,
                "header_surface": "",
                "primary_preview_count": 0,
                "secondary_panels_count": 0,
                "table_wraps": 0,
                "learner_text": "",
                "grammar_tags": set(),
            }
            self.cards.append(self.current_card)
        if self.current_card and tag == "header" and has_class(attrs, "qg-card-header"):
            self.current_card["header_count"] += 1
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
        if self.current_card and tag == "span" and has_class(attrs, "qg-segment-chip"):
            role = attrs.get("data-role")
            if role:
                self.current_card["segment_chips"].add(role)
        if self.current_card and tag == "p" and has_class(attrs, "qg-learner-explanation"):
            self.current_learner = ""
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
        if self.current_card and tag == "li" and has_class(attrs, "qg-breakdown-row"):
            self.current_card["tooltip_rows"].append({"role": attrs.get("data-role"), "text": ""})
        if self.current_card and tag == "code" and has_class(attrs, "qg-parse-key"):
            self.capture_parse_key = ""
        if self.current_word and tag == "span" and has_class(attrs, "qg-seg"):
            self.current_word["segments"].append({
                "attrs": attrs,
                "text": "",
            })

    def handle_endtag(self, tag):
        if self.capture_parse_key is not None and tag == "code":
            if self.current_card is not None:
                self.current_card["parse_keys"].append(self.capture_parse_key.strip())
            self.capture_parse_key = None
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
        if self.current_learner is not None and tag == "p":
            if self.current_card is not None:
                self.current_card["learner_text"] += self.current_learner.strip()
            self.current_learner = None
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
        if self.current_card and self.current_card["tooltip_rows"]:
            self.current_card["tooltip_rows"][-1]["text"] += data
        if self.current_segment_row is not None:
            self.current_segment_row["text"] += data
        if self.current_learner is not None:
            self.current_learner += data


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
    if ".qg-card-header" not in text or ".qg-primary-preview" not in text or ".qg-secondary-panels" not in text:
        add(errors, "fixture CSS must define the RH-LIVE IA hierarchy containers")
    if ".qg-gate-chip" not in text or ".qg-state-chip" not in text or ".qg-segment-chip" not in text:
        add(errors, "fixture CSS must define compact chip treatments")
    if "@media (max-width: 760px)" not in text or "content: attr(data-label)" not in text:
        add(errors, "fixture CSS must define mobile stacked segment-table behavior")
    for css_class in sorted(set(ROLE_CLASS_REQUIREMENTS.values())):
        if "." + css_class not in text:
            add(errors, "fixture CSS must define role-aware class %s" % css_class)


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
    if body.get("data-rh-live-stage") != "RH-LIVE-00.5":
        add(errors, "body must identify RH-LIVE-00.5 stage")
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
        if card["open_panels"]:
            add(errors, "%s secondary panels must be collapsed by default: %s" % (wbw, sorted(card["open_panels"])))
        if card["header_count"] != 1:
            add(errors, "%s must have one header row" % wbw)
        if card["primary_preview_count"] != 1:
            add(errors, "%s must have one primary hover preview" % wbw)
        if card["secondary_panels_count"] != 1:
            add(errors, "%s must have one secondary panel wrapper" % wbw)
        missing_state_chips = REQUIRED_STATE_CHIPS - card["state_chips"]
        if missing_state_chips:
            add(errors, "%s missing preview state chips: %s" % (wbw, sorted(missing_state_chips)))
        if card["header_surface"].strip() != expected_surface:
            add(errors, "%s header Arabic token must equal exact surface" % wbw)
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
        if not card["learner_text"]:
            add(errors, "%s missing learner explanation text" % wbw)
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
        tooltip_roles = {row["role"] for row in card["tooltip_rows"]}
        if visible_roles - tooltip_roles:
            add(errors, "%s tooltip breakdown missing roles: %s" % (wbw, sorted(visible_roles - tooltip_roles)))
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
    bad = text.replace('class="qg-primary-preview"', 'class="qg-primary-preview-removed"', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-ia.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("must have one primary hover preview" in error for error in bad_errors):
            raise SystemExit("self-test failed: missing primary preview hierarchy was not caught")
    bad = text.replace('<details class="qg-panel qg-sarf-panel" data-panel="sarf">', '<details class="qg-panel qg-sarf-panel" data-panel="sarf" open>', 1)
    with tempfile.TemporaryDirectory(prefix="rh-live-dom-fixture-") as tmp:
        bad_path = os.path.join(tmp, "bad-open-panel.html")
        write_text(bad_path, bad)
        bad_errors = validate_fixture(bad_path)
        if not any("secondary panels must be collapsed by default" in error for error in bad_errors):
            raise SystemExit("self-test failed: expanded secondary panel regression was not caught")
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
