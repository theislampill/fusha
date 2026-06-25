#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 candidate generator — per-loc decision REQUESTS for same-surface polysemy (iʿrāb-resolvable).

For each PENDING token whose norm_strict key collides (>1 distinct QAC root, OR >1 Qamus entry, OR a
known function-word homograph), emit a decision-request with the āyah context + the COMPETING senses
so a /fusha-sarf + /fusha-nahw verifier (with iʿrāb) can pick the context-correct gloss per loc — or
exact-block. Auto-applies NOTHING.

Output row: loc, surface, key, ayah_text, prev/next tokens, qac_root, qac_pos, competing[{entry_id,
headword,root,section,glosses}], function_word (bool), pending_code.

Env: QAMUS_WBW_SERVICES, QAMUS_WBW_ARTIFACT, QAMUS_DATASET.
"""
import argparse, json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TABLE = os.path.join(ROOT, "qamus", "reports", "closure-2092", "pending-source-triangulation-table.jsonl")

def load_qamus_wbw():
    sys.path.insert(0, os.environ.get("QAMUS_WBW_SERVICES", "services"))
    try:
        from qamus_wbw import expand as X
        from qamus_wbw import normalize as N
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "ERROR: qamus_wbw services are unavailable. Set QAMUS_WBW_SERVICES, "
            "QAMUS_WBW_ARTIFACT, and QAMUS_DATASET, or use --from with the "
            "triangulation-table request mode."
        ) from exc
    return X, N

# closed-class function words whose surface key famously collides (content-letter harakah decides)
FUNCTION_HOMOGRAPHS = {"ما","وما","فما","ان","وان","فان","لم","لما","من","ومن","فمن","ام","او","لو","ولو",
                       "ال","بل","قد","ها","ذا","اذ","اذا","لا","ولا","فلا","انا","انّ","لن","كل","كلا"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=os.environ.get("QAMUS_WBW_ARTIFACT"))
    ap.add_argument("--dataset", default=os.environ.get("QAMUS_DATASET", "/tmp/entries.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=400)
    ap.add_argument("--from", dest="from_table", default=None,
                    help="triangulation table request mode; emits unresolved irab/function rows")
    a = ap.parse_args()

    if a.from_table:
        rows = []
        for line in open(a.from_table, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("suggested_lane") != "token_irab":
                continue
            if r.get("gate") != "two_vote":
                continue
            rows.append({
                "loc": r.get("loc"),
                "surface": r.get("surface_ar") or "",
                "key": r.get("strict_nk") or r.get("nk") or "",
                "ayah_text": r.get("ayah_context") or "",
                "qac_root": r.get("qac_root"),
                "qac_pos": r.get("qac_pos"),
                "function_word": bool(r.get("function_word")),
                "competing": [],
                "pending_code": r.get("blocker") or r.get("root_cause") or "",
                "gate": "two_vote",
                "sarf_procedure": r.get("sarf_procedure"),
                "nahw_procedure": r.get("nahw_procedure"),
                "known_blocker": r.get("blocker_if_not_resolved") or "",
                "requested_output": {
                    "decision": "approve | reject | pending",
                    "concise_authored_gloss": "",
                    "sarf_reasoning": "",
                    "nahw_reasoning": "",
                    "reason_agreement_key": "",
                    "blocker_if_rejected": "",
                },
            })
        rows = rows[:a.max]
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(json.dumps({"requests": len(rows), "mode": "triangulation_table", "gate": "two_vote"},
                         ensure_ascii=False))
        return

    X, N = load_qamus_wbw()
    if not a.artifact:
        raise SystemExit("ERROR: --artifact or QAMUS_WBW_ARTIFACT is required outside --from mode")
    d = json.load(open(a.artifact, encoding="utf-8"))
    verses, words, pending = d["verses"], d["words"], d.get("pending", {})
    X._load_qac_roots(); qpos = X._QAC_CACHE.get("pos", {}); qroot = X._QAC_CACHE.get("root", {})

    # dataset: norm_strict key -> list of competing entries (headword or form match)
    by_key = collections.defaultdict(list)
    for line in open(a.dataset, encoding="utf-8"):
        e = json.loads(line)
        glosses = [s.get("gloss") for s in e.get("senses", []) if s.get("gloss")] or [e.get("definition")]
        rec = {"entry_id": e["id"], "headword": e.get("headword"), "root": e.get("root"),
               "section": e.get("section"), "glosses": glosses[:4]}
        hk = N.norm_strict(e.get("headword", ""))
        if hk: by_key[hk].append((rec, "headword"))
        seen = {hk}
        for u in e.get("usage", []):
            for fstr in (u.get("forms") or []):
                for t in re.findall(r"[؀-ۿ]+", fstr):
                    k = N.norm_strict(t)
                    if k and k not in seen: by_key[k].append((rec, "form")); seen.add(k)

    # corpus key -> distinct QAC roots (collision probe)
    key_roots = collections.defaultdict(set)
    for ref, toks in verses.items():
        for tok in toks:
            k = N.norm_strict(tok)
            r = qroot.get((ref, k))
            if r: key_roots[k].add(r)

    rows = []
    for ref, toks in verses.items():
        for i, tok in enumerate(toks):
            loc = "%s:%d" % (ref, i + 1)
            if loc in words:
                continue
            key = N.norm_strict(tok)
            entries = [r for r, _ in {id(x[0]): x for x in by_key.get(key, [])}.values()]
            is_fn = key in FUNCTION_HOMOGRAPHS
            multi_root = len(key_roots.get(key, set())) > 1
            multi_entry = len({e["entry_id"] for e in entries}) > 1
            if not (is_fn or multi_root or multi_entry):
                continue  # not a polysemy/homograph case
            rows.append({
                "loc": loc, "surface": tok, "key": key,
                "ayah_text": " ".join(toks),
                "prev": toks[i-1] if i > 0 else None, "next": toks[i+1] if i+1 < len(toks) else None,
                "qac_root": qroot.get((ref, key)), "qac_pos": qpos.get((ref, key)),
                "function_word": is_fn,
                "competing": [{k: e[k] for k in ("entry_id","headword","root","section","glosses")}
                              for e in entries][:4],
                "pending_code": pending.get(loc, "untagged"),
            })
    # diversity: cap per key so every polysemy class is represented (not all-of-one-key), then cap total
    freq = collections.Counter(r["key"] for r in rows)
    per_key = max(20, a.max // max(1, len(freq)) * 2)
    by_k = collections.defaultdict(list)
    for r in rows: by_k[r["key"]].append(r)
    sel = []
    for k in sorted(by_k, key=lambda k: -freq[k]):
        sel.extend(by_k[k][:per_key])
    rows = sel[:a.max]
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"requests": len(rows), "distinct_keys": len(set(r["key"] for r in rows)),
                      "function_word": sum(1 for r in rows if r["function_word"]),
                      "with_competing_entries": sum(1 for r in rows if r["competing"])},
                     ensure_ascii=False))

if __name__ == "__main__":
    main()
