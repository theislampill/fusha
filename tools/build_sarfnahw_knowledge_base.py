#!/usr/bin/env python3
"""SN3 — normalize the APKG + PDF extraction into a deduped sarf/nahw concept base.

Reads git-ignored extraction (``corpora/sarfnahw/out/apkg/*.jsonl``) + the authored
``sarf/rules/verb-measures.json`` and emits *concepts* (reusable patterns, not a
deck dump):

    corpora/sarfnahw/knowledge_base.json
    corpora/sarfnahw/knowledge_base.summary.md

Each concept points to its source (file/card/page) and carries a review_status.
Examples per concept are BOUNDED — the full vocabulary stays git-ignored; only
linguistic features (plural patterns, gender, function-word inventory, verb
measures) are committed.
"""
import os
import re
import sys
import glob
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_paths import repo_root                       # noqa: E402
import normalize_ar as N                                 # noqa: E402

ROOT = repo_root()
OUT_APKG = os.path.join(ROOT, "corpora", "sarfnahw", "out", "apkg")
OUT_DIR = os.path.join(ROOT, "corpora", "sarfnahw")
VERB_MEASURES = os.path.join(ROOT, "sarf", "rules", "verb-measures.json")
MAX_EX = 8

# function-word inventories (bare keys), for nahw concepts
PREPOSITIONS = "من في على إلى عن مع عند قبل بعد أمام خلف فوق تحت بين وراء حول لدى منذ حتى ك ل ب".split()
PRONOUNS = ("أنا نحن أنت أنتم أنتما أنتن هو هي هما هم هن إياك إياه "
            "هذا هذه ذلك تلك هؤلاء أولئك الذي التي الذين").split()
PARTICLES = "لا ما هل قد لقد إن أن لم لن لكن بل أو ثم إذا إذ نعم بلى لو لولا كي".split()
FUNC = {}
for w in PREPOSITIONS:
    FUNC[N.bare(w)] = "preposition"
for w in PRONOUNS:
    FUNC.setdefault(N.bare(w), "pronoun")
for w in PARTICLES:
    FUNC.setdefault(N.bare(w), "particle")


_WEAK = set("اويىءأإؤئةًٌٍَُِّْٰ")
NUMBER_GLOSS = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|"
                          r"hundred|thousand|i\s*/\s*we|that|those|this|these)\b", re.I)


def _consonants(bare):
    return [c for c in (bare or "") if c not in _WEAK]


def _is_plural_pair(sg_bare, pl_bare, gloss):
    """Reject non-noun 'pairs' (pronouns, demonstratives, numbers) and forms that
    don't share a root — only real singular↔plural morphology survives."""
    if not sg_bare or not pl_bare or sg_bare == pl_bare:
        return False
    if sg_bare in FUNC or pl_bare in FUNC:
        return False
    if gloss and NUMBER_GLOSS.search(gloss):
        return False
    cs, cp = set(_consonants(sg_bare)), set(_consonants(pl_bare))
    return len(cs & cp) >= 2


def classify_plural(sg_bare, pl_bare):
    if not pl_bare:
        return None
    if pl_bare.endswith("ون") or pl_bare.endswith("ين"):
        return ("sound_masculine_plural", "جمع مذكر سالم")
    if pl_bare.endswith("ات"):
        return ("sound_feminine_plural", "جمع مؤنث سالم")
    # normalize hamza seats to plain alif for WAZN-shape matching only (not storage)
    shape = re.sub(r"[أإآ]", "ا", pl_bare)
    if re.match(r"^ا.+ا.$", shape):          # أَفْعَال: أقلام أوراق أشجار أقمار
        return ("broken_plural_afʿaal", "وزن أَفْعَال")
    if re.match(r"^..ا.$", shape):           # فِعَال / فُعَال: رجال كبار
        return ("broken_plural_fiʿaal", "وزن فِعَال")
    if re.match(r"^...$", shape):            # فُعُل: كتب
        return ("broken_plural_fuʿul", "وزن فُعُل")
    if re.match(r"^..و.$", shape):           # فُعُول: بيوت علوم
        return ("broken_plural_fuʿuul", "وزن فُعُول")
    return ("broken_plural_other", "جمع تكسير (نمط آخر)")


def load_apkg_notes():
    notes = []
    for p in sorted(glob.glob(os.path.join(OUT_APKG, "*.jsonl"))):
        src = os.path.basename(p)
        for ln in open(p, encoding="utf-8"):
            n = json.loads(ln)
            n["_src"] = src
            notes.append(n)
    return notes


def verb_measure_concepts():
    out = []
    try:
        vm = json.load(open(VERB_MEASURES, encoding="utf-8"))
    except Exception:
        return out
    for f in vm.get("forms", []):
        out.append({
            "concept_id": "sarf:verb-measure:%s" % f["form"],
            "domain": "sarf", "topic": "verb_measure",
            "arabic_label": f["wazn"], "english_label": "Form %s" % f["form"],
            "rule_summary": f["sense"],
            "examples": [{"surface_ar": ex, "source_ref": "sarf/rules/verb-measures.json"}
                         for ex in f.get("quran_examples", [])[:MAX_EX]],
            "qamus_relevance": ["derived-form sense selection", "active/passive wording",
                                "maṣdar/participle gloss shape", "hover-gloss disambiguation"],
            "review_status": "curated",
        })
    for key, label in (("quadriliteral", "Quadriliteral فَعْلَلَ"), ("geminate", "Geminate مضاعف")):
        seg = vm.get(key, {})
        out.append({
            "concept_id": "sarf:verb-class:%s" % key,
            "domain": "sarf", "topic": "verb_class",
            "arabic_label": (seg.get("base", {}) or {}).get("wazn", label),
            "english_label": label, "rule_summary": seg.get("note", ""),
            "examples": [{"surface_ar": ex, "source_ref": "sarf/rules/verb-measures.json"}
                         for ex in seg.get("quran_examples", [])[:MAX_EX]],
            "qamus_relevance": ["root recovery", "norm() hazard"], "review_status": "curated",
        })
    return out


def weak_verb_concepts():
    classes = [
        ("hamzated", "المهموز", "أَخَذَ", "a radical is hamza; norm() drops the seat — use norm_strict"),
        ("doubled", "المضاعف", "رَدَّ", "C2=C3 merged under shadda; expand before counting radicals"),
        ("assimilated", "المثال", "وَجَدَ", "C1 و drops in the muḍāriʿ (يَجِدُ); و→ت in Form VIII"),
        ("hollow", "الأجوف", "قَالَ", "C2 (و/ي) → long alif in the past; medial dropped in IV/VIII/X"),
        ("defective", "الناقص", "دَعَا", "C3 (و/ي) alternates ا/ى/و/ي; last radical hidden"),
    ]
    out = []
    for key, ar, model, summ in classes:
        out.append({
            "concept_id": "sarf:weak-verb:%s" % key, "domain": "sarf", "topic": "verb_class",
            "arabic_label": ar, "english_label": key.replace("_", " ").title() + " verb",
            "rule_summary": summ,
            "examples": [{"surface_ar": model, "source_ref": "sarf/references/weak-verbs.md"}],
            "qamus_relevance": ["root recovery", "pending reason when root uncertain"],
            "review_status": "curated",
        })
    return out


def build():
    notes = load_apkg_notes()
    concepts = []
    concepts += verb_measure_concepts()
    concepts += weak_verb_concepts()

    # --- plural-pattern concepts from vocab pairs ---
    plural_buckets = collections.defaultdict(lambda: {"ar": "", "examples": [], "srcs": set()})
    gender_count = collections.Counter()
    seen_pairs = set()
    for n in notes:
        if n.get("gender") in ("m", "f"):
            gender_count[n["gender"]] += 1
        hw, pl = n.get("headword"), n.get("plural")
        if not hw or not pl:
            continue
        hb, pb = N.bare(hw), N.bare(pl)
        if not _is_plural_pair(hb, pb, n.get("gloss_en", "")):
            continue
        key = (hb, pb)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        cls = classify_plural(hb, pb)
        if not cls:
            continue
        cid, arlabel = cls
        b = plural_buckets[cid]
        b["ar"] = arlabel
        b["srcs"].add(n["_src"])
        if len(b["examples"]) < MAX_EX:
            b["examples"].append({"singular_ar": hw, "plural_ar": pl,
                                  "gender": n.get("gender", ""),
                                  "gloss_en": (n.get("gloss_en") or "")[:40],
                                  "source_ref": "apkg:%s" % n["_src"]})
    plural_total = len(seen_pairs)
    for cid, b in sorted(plural_buckets.items()):
        concepts.append({
            "concept_id": "sarf:plural:%s" % cid, "domain": "sarf", "topic": "plural_pattern",
            "arabic_label": b["ar"], "english_label": cid.replace("_", " "),
            "rule_summary": "Singular→plural pattern attested in the vocab corpus (%d source decks)." % len(b["srcs"]),
            "examples": b["examples"],
            "qamus_relevance": ["plural form matching", "entry plural field", "surface-form resolution"],
            "review_status": "needs_review",
        })

    # --- gender concept ---
    concepts.append({
        "concept_id": "sarf:noun-gender", "domain": "sarf", "topic": "gender",
        "arabic_label": "المذكر / المؤنث", "english_label": "noun gender",
        "rule_summary": "Corpus vocab carries explicit gender: %d masculine, %d feminine nouns tagged." % (
            gender_count["m"], gender_count["f"]),
        "examples": [], "qamus_relevance": ["agreement", "ism fāʿil/mafʿūl form choice"],
        "review_status": "needs_review",
    })

    # --- nahw function-word concepts ---
    func_buckets = collections.defaultdict(lambda: {"items": {}, "srcs": set()})
    for n in notes:
        if n.get("arabic_token_count") != 1:
            continue
        hw = n.get("headword")
        if not hw:
            continue
        cat = FUNC.get(N.bare(hw))
        if not cat:
            continue
        b = func_buckets[cat]
        b["srcs"].add(n["_src"])
        gl = (n.get("gloss_en") or "").strip()
        if hw not in b["items"] and gl:
            b["items"][hw] = gl[:40]
    for cat, b in sorted(func_buckets.items()):
        items = list(b["items"].items())
        concepts.append({
            "concept_id": "nahw:function-word:%s" % cat, "domain": "nahw", "topic": cat,
            "arabic_label": {"preposition": "حروف الجر", "pronoun": "الضمائر",
                             "particle": "الحروف / الأدوات"}.get(cat, cat),
            "english_label": "%s inventory (corpus-attested)" % cat,
            "rule_summary": "%d distinct %ss attested with English glosses; feed nahw hover/function-word "
                            "decisions (harakāt-guarded)." % (len(items), cat),
            "examples": [{"surface_ar": w, "gloss_en": g, "source_ref": "apkg-vocab"}
                         for w, g in items[:MAX_EX]],
            "qamus_relevance": ["function-word hover gloss", "particle disambiguation",
                                "preposition+pronoun rendering"],
            "review_status": "needs_review",
        })

    doc = {
        "schema": "fusha/sarfnahw_knowledge_base@1",
        "totals": {
            "concepts": len(concepts),
            "by_domain": dict(collections.Counter(c["domain"] for c in concepts)),
            "by_topic": dict(collections.Counter(c["topic"] for c in concepts)),
            "apkg_notes_scanned": len(notes),
            "distinct_plural_pairs": plural_total,
            "gender_tagged": dict(gender_count),
        },
        "concepts": concepts,
    }
    with open(os.path.join(OUT_DIR, "knowledge_base.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    write_summary(doc)
    print("KB concepts:", len(concepts), "| by_topic:",
          json.dumps(doc["totals"]["by_topic"], ensure_ascii=False))
    print("plural pairs:", plural_total, "| gender:", dict(gender_count),
          "| notes scanned:", len(notes))
    return doc


def write_summary(doc):
    t = doc["totals"]
    L = ["# Sarf/Nahw knowledge base — summary (SN3)", "",
         "Normalized, deduped concept base distilled from the APKG vocab decks + verb-chart structure.",
         "Concepts carry source refs + review status; the full vocabulary stays git-ignored under "
         "`corpora/sarfnahw/out/`. Only linguistic *features* are committed.", "",
         "| metric | value |", "|---|---:|",
         "| concepts | %d |" % t["concepts"],
         "| APKG notes scanned | %d |" % t["apkg_notes_scanned"],
         "| distinct singular→plural pairs | %d |" % t["distinct_plural_pairs"],
         "| gender-tagged nouns (m/f) | %d / %d |" % (t["gender_tagged"].get("m", 0),
                                                      t["gender_tagged"].get("f", 0)),
         ""]
    L.append("## Concepts by topic")
    L.append("")
    L.append("| topic | n |")
    L.append("|---|---:|")
    for topic, n in sorted(t["by_topic"].items(), key=lambda x: -x[1]):
        L.append("| %s | %d |" % (topic, n))
    L.append("")
    L.append("## Concept index")
    L.append("")
    L.append("| concept_id | label | examples | review |")
    L.append("|---|---|---:|---|")
    for c in doc["concepts"]:
        L.append("| `%s` | %s — %s | %d | %s |" % (
            c["concept_id"], c["arabic_label"], c["english_label"],
            len(c["examples"]), c["review_status"]))
    L.append("")
    L.append("> `needs_review` concepts are corpus-derived (vocab pairs, function words) pending linguist/owner "
             "sign-off; `curated` concepts are the authored verb measures/classes. Feeds SN4/SN5 skills and SN6 "
             "candidate generation.")
    with open(os.path.join(OUT_DIR, "knowledge_base.summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    build()
