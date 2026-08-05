#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standing public-origin readback -> rendered_appearance_edge builder (§3a).

Read-only, throttled GET over the PUBLIC entry pages (same contract as
``tools/crawl_qamus_public_entries.py``: GET /e/<id> only, single-threaded,
identifying UA, default 0.4s delay — no login, no POST, no mutation, no
server internals).  For every vn-ledger selected-word row with an EXPECTED
canonical loc (ledger-resolved ``canonical_quran_loc``/``occurrence_id``, else
the Queue-A attach loc from ``qamus/lattice/crosswalk-attach-queue.jsonl``),
the row's ``rendered_span`` debt closes when that loc appears among the page's
rendered ``data-loc`` hover spans.

Outputs (candidate-mode, in-repo):
  * rendered-span edge rows — ``qamus.graph_edge.v1`` /
    ``rendered_appearance_edge`` (selected-word -> occurrence), evidence =
    public URL + ``public_dom_readback``, payload sha256 + crawl time in
    details;
  * a per-page readback manifest (payload hash + span census) — the standing
    artifact re-runs diff against, so public DOM drift is detected.

Rows without an expected loc cannot close rendered-span here — readback is not
their blocker (they wait on Queue A/B).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.crawl_qamus_public_entries import ERRMARK, extract_hover_details  # noqa: E402
from tools.build_typed_edge_crosswalk import (  # noqa: E402
    _selected_id_for_row,
    make_edge,
    occurrence_node,
)

DEFAULT_ORIGIN = "https://qamus.dawah.wiki/e/"
UA = "fusha-qamus-readonly-crawler/1.0 (+repo audit; contact owner)"
PRODUCER_ID = "public_readback_spans.v1"
PRODUCER_VERSION = "1"

VN00_SCOPE = {("v", n) for n in range(1, 48)} | {("n", n) for n in range(1, 46)}


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _source_identity(value):
    value = str(value or "").strip()
    prefix = value[:1].lower()
    digits = value[1:]
    if prefix in ("v", "n", "p") and digits.isdigit():
        return prefix, int(digits)
    return None


def vn00_entry_ids(entries):
    """The frozen VN-00 window: v001–v047 + n0001–n0045 (92 entries)."""

    selected = []
    for entry in entries:
        for source_key in entry.get("source_keys") or []:
            identity = _source_identity(source_key)
            if identity in VN00_SCOPE:
                selected.append(str(entry.get("id")))
                break
    return sorted(set(selected))


def _row_expected_loc(row, attach_by_row_key):
    canonical = str(row.get("canonical_quran_loc") or "").strip()
    if canonical.startswith("quran:"):
        return canonical.split(":", 1)[1], "ledger_canonical"
    loc = str(row.get("occurrence_id") or "").strip()
    if loc:
        return loc, "ledger_canonical"
    key = _row_key(row)
    attach = attach_by_row_key.get(key)
    if attach and attach.get("status") == "candidate" and len(attach.get("attach_locs") or []) == 1:
        return attach["attach_locs"][0], "sweep_attach"
    return None, None


def _row_key(row):
    return (
        str(row.get("entry_id") or ""),
        int(row.get("sense_index") or 1),
        int(row.get("usage_index") or 1),
        int(row.get("form_index") or 1),
    )


def fetch_page(entry_id, origin, timeout):
    url = origin + entry_id
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        return {"id": entry_id, "url": url, "status": exc.code, "error": f"http {exc.code}"}
    except Exception as exc:  # network failure is recorded, never fabricated
        return {"id": entry_id, "url": url, "status": 0,
                "error": type(exc).__name__ + ": " + str(exc)[:80]}
    text = body.decode("utf-8", "replace")
    return {
        "id": entry_id,
        "url": url,
        "status": status,
        "payload_sha256": hashlib.sha256(body).hexdigest(),
        "render_error": bool(ERRMARK.search(text)),
        "spans": extract_hover_details(text),
    }


def build_readback(pages, ledger_rows, attach_queue, *, crawled_at):
    """Join fetched pages against expected-loc ledger rows; emit edges + manifest."""

    attach_by_row_key = {}
    for item in attach_queue or []:
        key = (
            str(item.get("entry_id") or ""),
            int(item.get("sense_index") or 1) if item.get("sense_index") else 1,
            int(item.get("usage_index") or 1) if item.get("usage_index") else 1,
            int(item.get("form_index") or 1) if item.get("form_index") else 1,
        )
        attach_by_row_key.setdefault(key, item)
    # queue rows do not carry sense/usage/form indices today; fall back to a
    # selected_word_id join when present
    attach_by_selected = {
        str(item.get("selected_word_id") or ""): item for item in attach_queue or []
    }

    pages_by_id = {page["id"]: page for page in pages}
    spans_by_page = {
        page["id"]: {span["loc"]: span for span in page.get("spans") or []}
        for page in pages
    }
    edges = []
    misses = []
    stats = Counter({
        "pages": len(pages),
        "pages_http_200": sum(1 for page in pages if page.get("status") == 200),
        "pages_render_error": sum(1 for page in pages if page.get("render_error")),
        "spans_harvested": sum(len(page.get("spans") or []) for page in pages),
    })
    for row in ledger_rows or []:
        entry_id = str(row.get("entry_id") or "").strip()
        if entry_id not in pages_by_id:
            continue
        stats["ledger_rows_on_fetched_pages"] += 1
        selected_id = _selected_id_for_row(row)
        attach = attach_by_selected.get(selected_id)
        if attach is not None:
            attach_by_row_key.setdefault(_row_key(row), attach)
        expected_loc, basis = _row_expected_loc(row, attach_by_row_key)
        if not expected_loc:
            stats["rows_without_expected_loc"] += 1
            continue
        stats["rows_with_expected_loc"] += 1
        page = pages_by_id[entry_id]
        span = spans_by_page.get(entry_id, {}).get(expected_loc)
        if span is None:
            stats["rendered_span_missing"] += 1
            misses.append({"entry_id": entry_id, "source_key": row.get("source_key"),
                           "expected_loc": expected_loc, "basis": basis})
            continue
        status = "candidate" if span.get("pending") else "deterministic_exact"
        stats["rendered_span_closed"] += 1
        stats["rendered_span_closed_pending" if span.get("pending") else
              "rendered_span_closed_glossed"] += 1
        item = make_edge(
            "rendered_appearance_edge",
            selected_id,
            occurrence_node(expected_loc),
            status,
            evidence=[{"address": page["url"], "method": "public_dom_readback"}],
            guards=["public_origin_readback_only", "no_live_mutation"],
            details={
                "loc": expected_loc,
                "expected_loc_basis": basis,
                "entry_id": entry_id,
                "source_key": str(row.get("source_key") or ""),
                "pending": bool(span.get("pending")),
                "gloss_present": bool(span.get("gloss")),
                "payload_sha256": page.get("payload_sha256"),
                "crawled_at": crawled_at,
            },
            producer_id=PRODUCER_ID,
            producer_version=PRODUCER_VERSION,
        )
        edges.append(item)

    manifest = {
        "schema": "qamus.public_readback_manifest.v1",
        "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
        "crawled_at": crawled_at,
        "origin_note": "public entry pages only; GET-only, throttled, identifying UA",
        "summary": dict(sorted(stats.items())),
        "misses": misses,
        "pages": [
            {
                "id": page["id"],
                "url": page["url"],
                "status": page.get("status"),
                "payload_sha256": page.get("payload_sha256"),
                "render_error": bool(page.get("render_error")),
                "spans_total": len(page.get("spans") or []),
                "spans_pending": sum(1 for span in page.get("spans") or [] if span.get("pending")),
                "error": page.get("error"),
            }
            for page in sorted(pages, key=lambda item: item["id"])
        ],
        "candidate_only": True,
    }
    return edges, manifest


def self_test():
    body = (
        '<html><body>'
        '<span class="qword" data-loc="7:40:17" data-tr="the camel">x</span>'
        '<span class="qword qw-pending" data-loc="7:40:19" data-tr="">y</span>'
        '</body></html>'
    )
    page = {
        "id": "entry-jamal", "url": "https://qamus.dawah.wiki/e/entry-jamal",
        "status": 200, "payload_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "render_error": False, "spans": extract_hover_details(body),
    }
    rows = [
        {"entry_id": "entry-jamal", "source_key": "n704", "sense_index": 1,
         "usage_index": 1, "form_index": 1, "occurrence_id": "7:40:17"},
        {"entry_id": "entry-jamal", "source_key": "n704", "sense_index": 1,
         "usage_index": 1, "form_index": 2, "occurrence_id": "7:40:19"},
        {"entry_id": "entry-jamal", "source_key": "n704", "sense_index": 1,
         "usage_index": 1, "form_index": 3, "occurrence_id": "3:3:3"},  # miss
        {"entry_id": "entry-jamal", "source_key": "n704", "sense_index": 1,
         "usage_index": 1, "form_index": 4},  # no expected loc
    ]
    edges, manifest = build_readback([page], rows, [], crawled_at="fixture")
    by_form = {item["details"]["loc"]: item for item in edges}
    ok = (
        manifest["summary"]["rows_with_expected_loc"] == 3
        and manifest["summary"]["rendered_span_closed"] == 2
        and manifest["summary"]["rendered_span_missing"] == 1
        and manifest["summary"]["rows_without_expected_loc"] == 1
        and by_form["7:40:17"]["status"] == "deterministic_exact"
        and by_form["7:40:19"]["status"] == "candidate"  # pending span never closes as exact
        and manifest["misses"][0]["expected_loc"] == "3:3:3"
        and all(item["evidence"][0]["method"] == "public_dom_readback" for item in edges)
        and all(item["details"]["payload_sha256"] == page["payload_sha256"] for item in edges)
    )
    print("PUBLIC READBACK SELF-TEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", default=os.path.join(ROOT, "qamus", "data", "current", "entries.jsonl"))
    parser.add_argument("--ledger", default=os.path.join(ROOT, "qamus/reports/vn-ledger.jsonl"))
    parser.add_argument("--attach-queue",
                        default=os.path.join(ROOT, "qamus", "lattice", "crosswalk-attach-queue.jsonl"))
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--pages", help="file with one entry id per line (default: --vn00)")
    parser.add_argument("--vn00", action="store_true",
                        help="crawl the frozen VN-00 window (v001–v047 + n0001–n0045, 92 pages)")
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--out-edges", required=False)
    parser.add_argument("--out-manifest", required=False)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not (args.out_edges and args.out_manifest):
        parser.error("provide --out-edges and --out-manifest, or use --self-test")

    entries = _read_jsonl(args.entries)
    if args.pages:
        with open(args.pages, encoding="utf-8") as handle:
            page_ids = [line.strip() for line in handle if line.strip()]
    elif args.vn00:
        page_ids = vn00_entry_ids(entries)
    else:
        parser.error("provide --pages or --vn00")
    ledger_rows = _read_jsonl(args.ledger)
    attach_queue = _read_jsonl(args.attach_queue) if os.path.exists(args.attach_queue) else []

    crawled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages = []
    for index, entry_id in enumerate(page_ids, 1):
        pages.append(fetch_page(entry_id, args.origin, args.timeout))
        if index % 25 == 0:
            print(f"  ... fetched {index}/{len(page_ids)}", file=sys.stderr)
        time.sleep(args.delay)
    edges, manifest = build_readback(pages, ledger_rows, attach_queue, crawled_at=crawled_at)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_edges)), exist_ok=True)
    with open(args.out_edges, "w", encoding="utf-8", newline="\n") as handle:
        for item in edges:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    os.makedirs(os.path.dirname(os.path.abspath(args.out_manifest)), exist_ok=True)
    with open(args.out_manifest, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
