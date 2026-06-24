#!/usr/bin/env python3
"""SN1 — extract AMAU / Anki .apkg decks into normalized JSONL.

Read-only. Opens each .apkg (a zip of a SQLite ``collection.anki2[1]`` + numbered
media), parses notes/cards/models/decks, strips HTML while preserving Arabic /
transliteration / English gloss, records (never copies) media references, and
classifies every note for downstream sarf/nahw/Qamus use.

Full per-deck extraction -> git-ignored ``corpora/sarfnahw/out/apkg/`` .
Committed safe artifacts:
    corpora/sarfnahw/apkg_catalogue.json   (per-deck summary, NO body text)
    corpora/sarfnahw/apkg_samples.jsonl    (a few single-word vocab samples/deck)

No media bytes are read. No full deck is committed.
"""
import os
import re
import sys
import json
import zipfile
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_paths import corpus_dir, repo_root           # noqa: E402
import text_extract as T                                 # noqa: E402
import normalize_ar as N                                 # noqa: E402

OUT_FULL = os.path.join(repo_root(), "corpora", "sarfnahw", "out", "apkg")
OUT_DIR = os.path.join(repo_root(), "corpora", "sarfnahw")

PARTICLES = set("من في على إلى عن مع لا ما هل قد لقد إن أن إنّ أنّ لم لن لما كان "
                "الذي التي الذين هذا هذه ذلك تلك و ف ب ل ك حتى ثم أو بل لكن إذا "
                "إذ عند بعد قبل بين تحت فوق".split())
SARF_HINT = re.compile(r"(pattern|wazn|measure|form\s+(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b|"
                       r"conjugat|masdar|maṣdar|participle|active|passive|imperative|"
                       r"past tense|present tense|root|derived|plural|broken plural|dual)",
                       re.I)
NAHW_HINT = re.compile(r"(particle|preposition|pronoun|i'?raab|i‘rab|case|mood|jar|majrur|"
                       r"idafa|iḍāfa|genitive|nominal sentence|verbal sentence|negation|"
                       r"conditional|relative|demonstrative|interrogative)", re.I)


def _open_db(zf):
    names = zf.namelist()
    for cand in ("collection.anki21", "collection.anki2"):
        if cand in names:
            return zf.read(cand), cand
    if "collection.anki21b" in names:
        try:
            import zstandard
            return zstandard.ZstdDecompressor().decompress(zf.read("collection.anki21b")), "collection.anki21b"
        except Exception:
            return None, "collection.anki21b"
    return None, None


def parse_deck(path, deck_kind="mixed"):
    """Yield normalized note dicts; also return meta (field/model/deck names)."""
    notes, meta = [], {"models": [], "decks": [], "fields": set(), "blocked": None, "db_file": None}
    with zipfile.ZipFile(path) as zf:
        db_bytes, dbfile = _open_db(zf)
        meta["db_file"] = dbfile
        if db_bytes is None:
            meta["blocked"] = "no_readable_db (%s)" % dbfile
            return notes, meta
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp.write(db_bytes)
            tmppath = tmp.name
    try:
        con = sqlite3.connect(tmppath)
        cur = con.cursor()
        row = cur.execute("SELECT models, decks FROM col LIMIT 1").fetchone()
        models = json.loads(row[0] or "{}")
        decks = json.loads(row[1] or "{}")
        meta["models"] = sorted({m.get("name", "") for m in models.values()})
        meta["decks"] = sorted({d.get("name", "") for d in decks.values()
                                if d.get("name") and d.get("name") != "Default"})
        mid_fields = {mid: [f["name"] for f in m.get("flds", [])] for mid, m in models.items()}
        mid_name = {mid: m.get("name", "") for mid, m in models.items()}
        did_name = {did: d.get("name", "") for did, d in decks.items()}
        nid_did = {}
        for nid, did in cur.execute("SELECT nid, did FROM cards"):
            nid_did.setdefault(nid, did)
        for nid, guid, mid, flds, tags in cur.execute("SELECT id, guid, mid, flds, tags FROM notes"):
            fnames = mid_fields.get(str(mid)) or mid_fields.get(mid) or []
            values = flds.split("\x1f")
            raw = {}
            for i, v in enumerate(values):
                key = fnames[i] if i < len(fnames) else "field_%d" % i
                raw[key] = v
            note = normalize_note(raw, mid_name.get(str(mid), mid_name.get(mid, "")),
                                  did_name.get(nid_did.get(nid), ""), str(guid), tags, deck_kind)
            for k in raw:
                meta["fields"].add(k)
            notes.append(note)
        con.close()
    finally:
        os.unlink(tmppath)
    meta["fields"] = sorted(meta["fields"])
    return notes, meta


def normalize_note(raw, model, deck, guid, tags, deck_kind="mixed"):
    media = []
    fields = {}
    for k, v in raw.items():
        media += T.media_refs(v)
        fields[k] = T.strip_html(v)
    # the raw Arabic field (translit + script mixed); the English field is the gloss
    ar_field, ar_raw, ar_score = None, "", 0.0
    for k, v in fields.items():
        sc = T.arabic_ratio(v) * (len(v) ** 0.5)
        if T.has_arabic(v) and sc > ar_score:
            ar_field, ar_raw, ar_score = k, v, sc
    gloss = (fields.get("English") or fields.get("english") or "").strip()
    if not gloss:  # fall back to the most-Latin non-Arabic field
        best = -1
        for k, v in fields.items():
            if k == ar_field or not v or T.has_arabic(v):
                continue
            ll = len(re.findall(r"[A-Za-z]+", v))
            if ll > best:
                gloss, best = v, ll
    gender = (fields.get("Gender") or fields.get("gender") or "").strip().lower()
    gender = {"m": "m", "f": "f", "male": "m", "female": "f"}.get(gender, gender)

    ar_only = T.arabic_script_only(ar_raw)
    headword, plural, extra = T.split_vocab_forms(ar_raw, ar_only)
    toks = [t for t in (T.strip_punct(x) for x in ar_only.split()) if t]
    note = {
        "deck": deck, "model": model, "guid": guid, "deck_kind": deck_kind,
        "arabic_raw": ar_raw, "arabic": ar_only, "arabic_field": ar_field,
        "headword": headword, "plural": plural, "gender": gender,
        "headword_norm_strict": N.norm_strict(headword) if headword else "",
        "headword_bare": N.bare(headword) if headword else "",
        "plural_bare": N.bare(plural) if plural else "",
        "translit": "",
        "gloss_en": gloss,
        "tokens": toks, "arabic_token_count": len(toks),
        "tags": [t for t in (tags or "").split() if t],
        "media_refs": media, "media_count": len(media),
        "fields": fields,
    }
    note["class"], note["uses"] = classify(note)
    return note


def classify(note):
    blob = " ".join([note.get("gloss_en", ""), " ".join(note.get("tags", [])),
                     note.get("deck", ""), note.get("model", "")])
    atc = note["arabic_token_count"]
    kind = note.get("deck_kind", "mixed")
    is_sarf = bool(SARF_HINT.search(blob)) or bool(note.get("plural"))
    first = note["tokens"][0] if note["tokens"] else ""
    is_nahw = bool(NAHW_HINT.search(blob)) or T.strip_punct(first) in PARTICLES
    uses = []
    if not note.get("arabic"):
        return "uncertain", []
    if kind == "vocab":
        # vocab decks: a lexeme (often singular+plural pair) — a Qamus/hover candidate
        if atc <= 2:
            primary = "vocabulary_candidate"
            uses += ["qamus_candidate", "hover_gloss_candidate"]
            if note.get("plural"):
                uses.append("sarf_drill")  # broken-plural evidence
        else:
            primary = "phrase_vocabulary"
            uses.append("nahw_drill")
    else:  # GUTA / lesson sentences (MSA)
        if atc == 1:
            primary = "vocabulary_candidate"
            uses += ["qamus_candidate", "hover_gloss_candidate"]
        elif atc <= 3 and is_nahw:
            primary = "function_construction"
            uses += ["nahw_drill", "hover_gloss_candidate"]
        else:
            primary = "nahw_drill"  # sentence-level syntax material
    if is_sarf and "sarf_drill" not in uses and primary != "sarf_drill":
        uses.append("sarf_drill")
    if is_nahw and "nahw_drill" not in uses and primary != "nahw_drill":
        uses.append("nahw_drill")
    return primary, sorted(set(uses))


def safe_samples(notes, k=4):
    """A few single-lexeme vocab samples (headword + short gloss) — structural doc only."""
    out = []
    for n in notes:
        if n.get("headword") and n.get("gloss_en") and n["arabic_token_count"] <= 2 and len(out) < k:
            out.append({
                "deck_kind": n.get("deck_kind", ""),
                "headword": n["headword"][:24],
                "plural": (n.get("plural") or "")[:24],
                "gender": n.get("gender", ""),
                "norm_strict": n["headword_norm_strict"],
                "gloss_en": n["gloss_en"][:50],
                "class": n["class"],
                "uses": n["uses"],
            })
    return out


def main():
    cdir = corpus_dir()
    os.makedirs(OUT_FULL, exist_ok=True)
    catalogue = {"schema": "fusha/apkg_catalogue@1", "decks": [],
                 "totals": {"files": 0, "notes": 0, "media_refs": 0, "by_class": {}}}
    samples = []
    files = sorted(f for f in os.listdir(cdir) if f.lower().endswith(".apkg"))
    for fn in files:
        path = os.path.join(cdir, fn)
        deck_kind = "vocab" if "vocab" in fn.lower() else "guta"
        notes, meta = parse_deck(path, deck_kind)
        stem = re.sub(r"[^a-z0-9]+", "-", fn.lower().rsplit(".", 1)[0]).strip("-")
        if notes:
            with open(os.path.join(OUT_FULL, stem + ".jsonl"), "w", encoding="utf-8") as f:
                for n in notes:
                    f.write(json.dumps(n, ensure_ascii=False) + "\n")
        hist = {}
        media_refs = 0
        for n in notes:
            hist[n["class"]] = hist.get(n["class"], 0) + 1
            media_refs += n["media_count"]
        deck_rec = {
            "file": fn, "deck_kind": deck_kind, "db_file": meta["db_file"], "blocked": meta["blocked"],
            "notes": len(notes), "model_names": meta["models"], "deck_names": meta["decks"],
            "field_names": meta["fields"], "media_refs": media_refs,
            "single_token": sum(1 for n in notes if n["arabic_token_count"] == 1),
            "multi_token": sum(1 for n in notes if n["arabic_token_count"] >= 2),
            "no_arabic": sum(1 for n in notes if n["arabic_token_count"] == 0),
            "with_plural": sum(1 for n in notes if n.get("plural")),
            "with_gender": sum(1 for n in notes if n.get("gender") in ("m", "f")),
            "with_gloss": sum(1 for n in notes if n["gloss_en"]),
            "by_class": hist,
            "full_output": "corpora/sarfnahw/out/apkg/%s.jsonl" % stem,
        }
        catalogue["decks"].append(deck_rec)
        catalogue["totals"]["files"] += 1
        catalogue["totals"]["notes"] += len(notes)
        catalogue["totals"]["media_refs"] += media_refs
        for c, n in hist.items():
            catalogue["totals"]["by_class"][c] = catalogue["totals"]["by_class"].get(c, 0) + n
        samples += safe_samples(notes)

    with open(os.path.join(OUT_DIR, "apkg_catalogue.json"), "w", encoding="utf-8") as f:
        json.dump(catalogue, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "apkg_samples.jsonl"), "w", encoding="utf-8") as f:
        for s in samples[:48]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print("APKG decks:", catalogue["totals"]["files"], "notes:", catalogue["totals"]["notes"],
          "media_refs:", catalogue["totals"]["media_refs"])
    print("by_class:", json.dumps(catalogue["totals"]["by_class"], ensure_ascii=False))
    for d in catalogue["decks"]:
        print(" -", d["file"], "| notes", d["notes"], "| models", d["model_names"],
              "| fields", d["field_names"], "| blocked", d["blocked"])


if __name__ == "__main__":
    main()
