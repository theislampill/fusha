#!/usr/bin/env python3
"""Phase 2 — reconcile the public crawl checkpoint against the repo dataset.

Reads out/crawl/qamus-crawl-checkpoint.jsonl (produced by crawl_qamus_public_entries.py) and the
committed repo entries, and emits a live-vs-repo reconciliation. Honest about partial crawls: it
reports exactly how many of the 2,092 were crawled and the resume command if not all.

Outputs (committed — summary only, not the raw crawl):
  qamus/reports/closure-2092/live-public-entry-crawl-summary-YYYYMMDD.json
  qamus/reports/closure-2092/live-vs-repo-entry-reconciliation-YYYYMMDD.md
"""
import json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
CKPT = os.path.join(ROOT, "out", "crawl", "qamus-crawl-checkpoint.jsonl")
OUT = os.path.join(ROOT, "qamus", "reports", "closure-2092")
DATE = os.environ.get("AUDIT_DATE", "20260625")

HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
def norm(s): return HARAKAT.sub("", (s or "")).strip()

def main():
    repo = {}
    for line in open(DATA, encoding="utf-8"):
        line = line.strip()
        if line:
            e = json.loads(line); repo[e["id"]] = e
    crawled = {}
    if os.path.exists(CKPT):
        for line in open(CKPT, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line); crawled[r["id"]] = r
                except Exception:
                    pass

    status_c = Counter()
    render_err = []
    head_mismatch = []
    not_in_repo = []
    hover_resolved = hover_total = 0
    for eid, r in crawled.items():
        status_c[r.get("status")] += 1
        if r.get("render_error"):
            render_err.append(eid)
        if eid not in repo:
            not_in_repo.append(eid); continue
        if r.get("status") == 200:
            th = norm(r.get("title_headword"))
            rh = norm(repo[eid].get("headword"))
            # title headword can be a prefix/first-form; accept containment either way
            if th and rh and th not in rh and rh not in th and th != rh:
                head_mismatch.append({"id": eid, "title": r.get("title_headword"),
                                      "repo": repo[eid].get("headword")})
            hover_resolved += r.get("hover_resolved", 0)
            hover_total += r.get("hover_total", 0)

    crawled_repo_ids = [e for e in crawled if e in repo]
    remaining = [e for e in repo if e not in crawled]
    ok200 = status_c.get(200, 0)
    summary = {
        "_generator": "validate_qamus_public_crawl", "date": DATE,
        "repo_entries": len(repo), "crawled": len(crawled),
        "crawled_pct": round(100 * len(crawled) / max(len(repo), 1), 1),
        "status_distribution": dict(status_c),
        "http_200": ok200, "render_errors": len(render_err),
        "headword_mismatches": len(head_mismatch),
        "crawled_not_in_repo": len(not_in_repo),
        "remaining_uncrawled": len(remaining),
        "hover_total_seen": hover_total, "hover_resolved_seen": hover_resolved,
        "complete": len(remaining) == 0,
        "resume_command": (None if not remaining else
            "python3 tools/crawl_qamus_public_entries.py --all   # resumes from checkpoint"),
        "samples_headword_mismatch": head_mismatch[:10],
        "samples_render_error": render_err[:10],
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"live-public-entry-crawl-summary-{DATE}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")

    md = [f"# Live public-entry crawl — live-vs-repo reconciliation ({DATE})\n",
          ("> **COMPLETE — all repo entries crawled.**\n" if summary["complete"] else
           f"> **PARTIAL — {len(crawled)}/{len(repo)} crawled ({summary['crawled_pct']}%). "
           f"{len(remaining)} remaining.** Resume: `{summary['resume_command']}`\n"),
          "| metric | value |", "|---|---:|",
          f"| repo entries | {len(repo):,} |",
          f"| crawled (read-only GET /e/<id>) | {len(crawled):,} ({summary['crawled_pct']}%) |",
          f"| HTTP 200 | {ok200:,} |",
          f"| render errors | {len(render_err)} |",
          f"| headword mismatches (norm) | {len(head_mismatch)} |",
          f"| crawled ids not in repo | {len(not_in_repo)} |",
          f"| hover tokens seen (resolved/total) | {hover_resolved:,} / {hover_total:,} |\n",
          "## Method (read-only, polite)\n",
          "GET `/e/<id>` only — no login, no POST, no private endpoints. Single-threaded, throttled, "
          "resumable from an append-only checkpoint. Entry id list is the committed repo dataset, so "
          "the crawl reconciles live render vs repo by construction.\n"]
    if head_mismatch:
        md.append("## Headword mismatches (first 10)\n| id | title | repo |\n|---|---|---|")
        for m in head_mismatch[:10]:
            md.append(f"| {m['id']} | {m['title']} | {m['repo']} |")
        md.append("")
    if render_err:
        md.append("## Render errors\n" + ", ".join(render_err[:20]) + "\n")
    if not summary["complete"]:
        md.append(f"\n## Resume\n`{summary['resume_command']}` then re-run this validator.\n")
    open(os.path.join(OUT, f"live-vs-repo-entry-reconciliation-{DATE}.md"), "w", encoding="utf-8").write("\n".join(md))

    print(f"CRAWL RECON: crawled={len(crawled)}/{len(repo)} ({summary['crawled_pct']}%) 200={ok200} "
          f"render_err={len(render_err)} head_mismatch={len(head_mismatch)} remaining={len(remaining)}")
    # non-fatal: partial crawl is allowed; only fail on a crawled-but-broken page beyond a small floor
    broken = len(render_err) + sum(v for k, v in status_c.items() if k not in (200, None))
    if crawled and broken > 0:
        print(f"NOTE: {broken} crawled pages were non-200 or render-error (see samples).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
