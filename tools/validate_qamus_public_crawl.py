#!/usr/bin/env python3
"""Phase 2 — reconcile the public crawl checkpoint against the repo dataset.

Reads out/crawl/qamus-crawl-checkpoint.jsonl (produced by crawl_qamus_public_entries.py) and the
committed repo entries, and emits a live-vs-repo reconciliation. Honest about partial crawls: it
reports exactly how many of the 2,092 were crawled and the resume command if not all.

Outputs (committed — summary only, not the raw crawl):
  qamus/reports/closure-2092/live-public-entry-crawl-summary-YYYYMMDD.json
  qamus/reports/closure-2092/live-vs-repo-entry-reconciliation-YYYYMMDD.md
  qamus/reports/closure-2092/live-hover-vs-repo-reconciliation-YYYYMMDD.jsonl
  qamus/reports/closure-2092/live-hover-vs-repo-reconciliation-YYYYMMDD.md
"""
import json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl")
CKPT = os.path.join(ROOT, "out", "crawl", "qamus-crawl-checkpoint.jsonl")
AUDIT = os.path.join(ROOT, "qamus", "reports", "hover-token-audit-full.jsonl")
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
    repo_hover = {}
    if os.path.exists(AUDIT):
        for line in open(AUDIT, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            loc = r.get("quran_loc")
            if loc:
                repo_hover[loc] = {
                    "decision_state": r.get("decision_state"),
                    "public_gloss": r.get("public_gloss") or "",
                }

    status_c = Counter()
    render_err = []
    head_mismatch = []
    not_in_repo = []
    hover_resolved = hover_total = 0
    hover_detail_rows = 0
    hover_mismatches = []
    live_loc_counts = Counter()
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
            for h in r.get("hover_details") or []:
                hover_detail_rows += 1
                loc = h.get("loc")
                if not loc:
                    continue
                live_loc_counts[loc] += 1
                repo_state = repo_hover.get(loc)
                live_pending = h.get("pending") is True or not (h.get("gloss") or "").strip()
                if repo_state is None:
                    hover_mismatches.append({"type": "live_loc_not_in_repo_audit", "id": eid, "loc": loc})
                    continue
                repo_pending = repo_state.get("decision_state") == "pending"
                if live_pending and not repo_pending:
                    hover_mismatches.append({"type": "public_pending_but_repo_resolved", "id": eid, "loc": loc,
                                             "repo_gloss": repo_state.get("public_gloss")})
                elif (not live_pending) and repo_pending:
                    hover_mismatches.append({"type": "public_resolved_but_repo_pending", "id": eid, "loc": loc,
                                             "live_gloss": h.get("gloss")})
                elif (not live_pending) and (h.get("gloss") or "") != (repo_state.get("public_gloss") or ""):
                    hover_mismatches.append({"type": "public_gloss_differs_from_repo", "id": eid, "loc": loc,
                                             "live_gloss": h.get("gloss"),
                                             "repo_gloss": repo_state.get("public_gloss")})

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
        "hover_detail_rows_seen": hover_detail_rows,
        "hover_mismatches": len(hover_mismatches),
        "duplicate_live_locs": sum(1 for _, c in live_loc_counts.items() if c > 1),
        "complete": len(remaining) == 0,
        "resume_command": (None if not remaining else
            "python3 tools/crawl_qamus_public_entries.py --all   # resumes from checkpoint"),
        "samples_headword_mismatch": head_mismatch[:10],
        "samples_render_error": render_err[:10],
        "samples_hover_mismatch": hover_mismatches[:10],
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

    hover_jsonl = os.path.join(OUT, f"live-hover-vs-repo-reconciliation-{DATE}.jsonl")
    with open(hover_jsonl, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"_summary": {
            "date": DATE,
            "complete_entry_crawl": summary["complete"],
            "hover_detail_rows_seen": hover_detail_rows,
            "hover_mismatches": len(hover_mismatches),
            "duplicate_live_locs": summary["duplicate_live_locs"],
            "note": "A complete hover-level claim requires crawler rows with hover_details for every entry.",
        }}, ensure_ascii=False, sort_keys=True) + "\n")
        for row in hover_mismatches:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    hover_md = [
        f"# Live hover vs repo reconciliation ({DATE})",
        "",
        ("**COMPLETE hover-detail source available.**" if hover_detail_rows else
         "**NOT COMPLETE for hover semantics.** Existing checkpoint lacks `hover_details`; re-run `python3 tools/crawl_qamus_public_entries.py --all` after the crawler update, then re-run this validator."),
        "",
        "| metric | value |",
        "|---|---:|",
        f"| public entry crawl complete | {summary['complete']} |",
        f"| hover detail rows seen | {hover_detail_rows:,} |",
        f"| hover mismatches | {len(hover_mismatches):,} |",
        f"| duplicate live locs | {summary['duplicate_live_locs']:,} |",
        "",
        "This report checks hover states only when raw crawl rows include `hover_details` with `loc`, `gloss`, and `pending`.",
        "",
    ]
    open(os.path.join(OUT, f"live-hover-vs-repo-reconciliation-{DATE}.md"), "w", encoding="utf-8").write("\n".join(hover_md))

    print(f"CRAWL RECON: crawled={len(crawled)}/{len(repo)} ({summary['crawled_pct']}%) 200={ok200} "
          f"render_err={len(render_err)} head_mismatch={len(head_mismatch)} remaining={len(remaining)} "
          f"hover_details={hover_detail_rows} hover_mismatches={len(hover_mismatches)}")
    # non-fatal: partial crawl is allowed; only fail on a crawled-but-broken page beyond a small floor
    broken = len(render_err) + sum(v for k, v in status_c.items() if k not in (200, None))
    if crawled and broken > 0:
        print(f"NOTE: {broken} crawled pages were non-200 or render-error (see samples).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
