#!/usr/bin/env python3
"""Phase 2 — read-only, throttled crawl of the PUBLIC Qamus entry pages.

Strictly read-only: GET /e/<id> only, no login, no POST, no private endpoints, no mutation.
Polite: single-threaded, throttled (--delay), short timeout, identifying User-Agent.
Resumable: appends each result to a checkpoint JSONL; re-running skips already-crawled ids.

Entry id list comes from the committed repo dataset (qamus/data/current/entries.jsonl), so the crawl
is a live-vs-repo reconciliation by construction: every repo entry SHOULD render at /e/<id>.

Usage:
  python3 tools/crawl_qamus_public_entries.py --limit 100        # bounded sample
  python3 tools/crawl_qamus_public_entries.py --all              # full 2,092 (resumes)
  python3 tools/crawl_qamus_public_entries.py --all --delay 0.4  # gentler

Outputs (under out/crawl/, git-ignored raw):
  out/crawl/qamus-crawl-checkpoint.jsonl   (append-only, one row per crawled id; resume source)
Stamp the committed summary/reconciliation separately via validate_qamus_public_crawl.py.
"""
import argparse, html, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
OUTDIR = os.path.join(ROOT, "out", "crawl")
CKPT = os.path.join(OUTDIR, "qamus-crawl-checkpoint.jsonl")
BASE = "https://qamus.dawah.wiki/e/"
UA = "fusha-qamus-readonly-crawler/1.0 (+repo audit; contact owner)"

TITLE = re.compile(r"<title>(.*?)</title>", re.S)
QWORD = re.compile(r'class="qword(?: qw-pending)?"')
QPEND = re.compile(r'class="qword qw-pending"')
DLOC = re.compile(r'data-loc="(\d+:\d+:\d+)"')
ERRMARK = re.compile(r"(Traceback \(most recent call last\)|Internal Server Error|500 - )", re.I)
QSPAN = re.compile(r'<span\b[^>]*class="[^"]*\bqword\b[^"]*"[^>]*>', re.I)
ATTR = re.compile(r'([a-zA-Z0-9_-]+)="([^"]*)"')

def extract_hover_details(body):
    rows = []
    for match in QSPAN.finditer(body):
        tag = match.group(0)
        attrs = {k: html.unescape(v) for k, v in ATTR.findall(tag)}
        loc = attrs.get("data-loc")
        if not loc:
            continue
        classes = attrs.get("class", "")
        rows.append({
            "loc": loc,
            "gloss": attrs.get("data-tr", ""),
            "pending": "qw-pending" in classes.split(),
        })
    return rows

def load_repo():
    repo = {}
    for line in open(DATA, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        repo[e["id"]] = {"headword": e.get("headword", ""), "section": e.get("section", ""),
                         "total_uses": e.get("total_uses")}
    return repo

def done_ids(require_hover_details=False):
    s = set()
    if os.path.exists(CKPT):
        for line in open(CKPT, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if require_hover_details and "hover_details" not in row:
                    continue
                s.add(row["id"])
            except Exception:
                pass
    return s

def fetch(eid, timeout):
    url = BASE + eid
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            status = r.getcode()
    except urllib.error.HTTPError as ex:
        return {"id": eid, "url": url, "status": ex.code, "error": f"http {ex.code}",
                "ms": round((time.monotonic() - t0) * 1000)}
    except Exception as ex:
        return {"id": eid, "url": url, "status": 0, "error": type(ex).__name__ + ": " + str(ex)[:80],
                "ms": round((time.monotonic() - t0) * 1000)}
    title = TITLE.search(body)
    head = ""
    if title:
        head = re.sub(r"\s*&middot;\s*Qamus\s*$", "", title.group(1)).replace("&middot;", "").strip()
    qtot = len(QWORD.findall(body))
    qpend = len(QPEND.findall(body))
    locs = DLOC.findall(body)
    hover_details = extract_hover_details(body)
    return {"id": eid, "url": url, "status": status, "bytes": len(body),
            "title_headword": head, "hover_total": qtot, "hover_pending": qpend,
            "hover_resolved": qtot - qpend, "data_loc_count": len(locs),
            "hover_details": hover_details,
            "distinct_ayat": len({":".join(l.split(":")[:2]) for l in locs}),
            "render_error": bool(ERRMARK.search(body)),
            "ms": round((time.monotonic() - t0) * 1000)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max entries this run (0 = no cap)")
    ap.add_argument("--all", action="store_true", help="crawl the full repo set")
    ap.add_argument("--refresh-hover-details", action="store_true",
                    help="recrawl entries whose checkpoint row lacks hover_details")
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between requests (throttle)")
    ap.add_argument("--timeout", type=float, default=15.0)
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    repo = load_repo()
    done = done_ids(require_hover_details=a.refresh_hover_details)
    todo = [eid for eid in repo if eid not in done]
    if not a.all and a.limit == 0:
        a.limit = 50  # safe default for a bounded run
    if a.limit:
        todo = todo[:a.limit]
    print(f"repo entries={len(repo)} already_done={len(done)} this_run={len(todo)} delay={a.delay}s")
    ok = err = 0
    with open(CKPT, "a", encoding="utf-8") as ck:
        for i, eid in enumerate(todo, 1):
            res = fetch(eid, a.timeout)
            res["repo_headword"] = repo[eid]["headword"]
            res["repo_section"] = repo[eid]["section"]
            ck.write(json.dumps(res, ensure_ascii=False, sort_keys=True) + "\n")
            ck.flush()
            if res.get("status") == 200 and not res.get("render_error"):
                ok += 1
            else:
                err += 1
                print(f"  !! {eid} status={res.get('status')} err={res.get('error') or 'render_error'}")
            if i % 100 == 0:
                print(f"  ... {i}/{len(todo)} ok={ok} err={err}")
            time.sleep(a.delay)
    total_done = len(done) + len(todo)
    print(f"RUN DONE this_run_ok={ok} this_run_err={err} cumulative_crawled={total_done}/{len(repo)}")

if __name__ == "__main__":
    main()
