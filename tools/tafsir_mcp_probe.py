#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe the Tafsir MCP (https://mcp.tafsir.net/mcp) — report AVAILABLE + tool list, or the EXACT blocker.

Tafsir MCP is an INTERNAL Qur'an grammar/morphology evidence layer (irab = إعراب القرآن; markaz_irab = مركز تفسير;
analyze_word; fetch_ayah). It is NEVER a public data source — nothing it returns ships to the public hover artifact.

This probe speaks MCP streamable-HTTP (JSON-RPC 2.0): initialize -> (session) -> notifications/initialized ->
tools/list. It does NOT fabricate success: if the endpoint is unreachable, returns an error, or requires auth,
it prints the exact failure so the MCP lane is honestly marked blocked.

Config (no secret committed):
    TAFSIR_MCP_URL   default https://mcp.tafsir.net/mcp
    TAFSIR_MCP_TOKEN optional bearer token (if the server requires auth)
Stdlib only (urllib) so it runs anywhere; honors a short timeout.
"""
import json
import os
import sys
import urllib.request
import urllib.error

URL = os.environ.get("TAFSIR_MCP_URL", "https://mcp.tafsir.net/mcp")
TOKEN = os.environ.get("TAFSIR_MCP_TOKEN")
TIMEOUT = int(os.environ.get("TAFSIR_MCP_TIMEOUT", "20"))
PROTO = "2025-06-18"


def _headers(session=None):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if TOKEN:
        h["Authorization"] = "Bearer " + TOKEN
    if session:
        h["Mcp-Session-Id"] = session
    return h


def _rpc(method, params, rpc_id=None, session=None, notify=False):
    body = {"jsonrpc": "2.0", "method": method}
    if not notify:
        body["id"] = rpc_id
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers=_headers(session), method="POST")
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    sid = resp.headers.get("Mcp-Session-Id")
    raw = resp.read().decode("utf-8", "replace")
    # streamable HTTP may return SSE framing (event:/data:) or plain JSON
    payload = None
    if raw.strip().startswith("{"):
        payload = json.loads(raw)
    else:
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk:
                    try:
                        payload = json.loads(chunk)
                    except Exception:
                        pass
    return resp.status, sid, payload, raw[:400]


def main():
    result = {"url": URL, "available": False, "blocker": None, "protocol": PROTO,
              "server": None, "tools": [], "auth_required": bool(TOKEN)}
    try:
        status, sid, payload, raw = _rpc("initialize", {
            "protocolVersion": PROTO, "capabilities": {},
            "clientInfo": {"name": "fusha-tafsir-probe", "version": "0.1"}}, rpc_id=1)
        if payload and "result" in payload:
            result["server"] = (payload["result"].get("serverInfo") or {})
            # send initialized notification, then list tools
            try:
                _rpc("notifications/initialized", None, session=sid, notify=True)
            except Exception:
                pass
            st2, sid2, p2, raw2 = _rpc("tools/list", {}, rpc_id=2, session=sid)
            if p2 and "result" in p2:
                result["tools"] = [t.get("name") for t in (p2["result"].get("tools") or [])]
                result["available"] = True
            else:
                result["blocker"] = "initialize OK but tools/list failed: %s" % (raw2,)
        elif payload and "error" in payload:
            result["blocker"] = "JSON-RPC error: %s" % json.dumps(payload["error"], ensure_ascii=False)
        else:
            result["blocker"] = "HTTP %s, unparseable response: %s" % (status, raw)
    except urllib.error.HTTPError as e:
        result["blocker"] = "HTTPError %s %s: %s" % (e.code, e.reason, (e.read()[:200].decode("utf-8", "replace")))
        if e.code in (401, 403):
            result["blocker"] += " (auth required — set TAFSIR_MCP_TOKEN)"
    except urllib.error.URLError as e:
        result["blocker"] = "URLError: %s" % e.reason
    except Exception as e:
        result["blocker"] = "%s: %s" % (type(e).__name__, e)

    print(json.dumps(result, ensure_ascii=False, indent=1))
    sys.exit(0 if result["available"] else 3)


if __name__ == "__main__":
    main()
