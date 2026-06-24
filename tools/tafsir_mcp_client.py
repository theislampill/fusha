#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal MCP (streamable-HTTP, JSON-RPC 2.0) client for the Tafsir MCP — shared backbone for the connector tools.

Tafsir MCP (https://mcp.tafsir.net/mcp) is an INTERNAL Qur'an grammar/morphology evidence layer. Nothing it
returns ships to the public hover artifact. Stdlib only (urllib). Reusable: `with TafsirMCP() as m: m.call("analyze_word", {...})`.

Config (no secret committed):
    TAFSIR_MCP_URL    default https://mcp.tafsir.net/mcp
    TAFSIR_MCP_TOKEN  optional bearer token
    TAFSIR_MCP_TIMEOUT seconds (default 30)
"""
import json
import os
import urllib.request
import urllib.error

URL = os.environ.get("TAFSIR_MCP_URL", "https://mcp.tafsir.net/mcp")
TOKEN = os.environ.get("TAFSIR_MCP_TOKEN")
TIMEOUT = int(os.environ.get("TAFSIR_MCP_TIMEOUT", "30"))
PROTO = "2025-06-18"


class TafsirMCPError(RuntimeError):
    pass


class TafsirMCP:
    def __init__(self):
        self.session = None
        self._id = 0

    def _headers(self):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if TOKEN:
            h["Authorization"] = "Bearer " + TOKEN
        if self.session:
            h["Mcp-Session-Id"] = self.session
        return h

    def _post(self, body, expect_reply=True):
        req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                     headers=self._headers(), method="POST")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.session = sid
        raw = resp.read().decode("utf-8", "replace")
        if not expect_reply:
            return None
        if raw.strip().startswith("{"):
            return json.loads(raw)
        payload = None
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk:
                    try:
                        payload = json.loads(chunk)
                    except Exception:
                        pass
        if payload is None:
            raise TafsirMCPError("unparseable MCP response: %s" % raw[:300])
        return payload

    def _next(self):
        self._id += 1
        return self._id

    def __enter__(self):
        r = self._post({"jsonrpc": "2.0", "id": self._next(), "method": "initialize",
                        "params": {"protocolVersion": PROTO, "capabilities": {},
                                   "clientInfo": {"name": "fusha-tafsir", "version": "0.1"}}})
        if not r or "result" not in r:
            raise TafsirMCPError("initialize failed: %s" % json.dumps(r, ensure_ascii=False)[:300])
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_reply=False)
        except Exception:
            pass
        return self

    def __exit__(self, *a):
        return False

    def list_tools(self):
        r = self._post({"jsonrpc": "2.0", "id": self._next(), "method": "tools/list", "params": {}})
        return (r.get("result") or {}).get("tools", []) if r else []

    def call(self, name, arguments):
        """Call an MCP tool; return the parsed structured content (or text blocks joined)."""
        r = self._post({"jsonrpc": "2.0", "id": self._next(), "method": "tools/call",
                        "params": {"name": name, "arguments": arguments}})
        if not r:
            raise TafsirMCPError("no reply for %s" % name)
        if "error" in r:
            raise TafsirMCPError("%s error: %s" % (name, json.dumps(r["error"], ensure_ascii=False)))
        res = r.get("result") or {}
        if res.get("isError"):
            raise TafsirMCPError("%s isError: %s" % (name, json.dumps(res, ensure_ascii=False)[:300]))
        # prefer structuredContent; else parse text content blocks
        if "structuredContent" in res:
            return res["structuredContent"]
        out = []
        for c in res.get("content", []):
            if c.get("type") == "text":
                t = c.get("text", "")
                try:
                    out.append(json.loads(t))
                except Exception:
                    out.append(t)
        return out[0] if len(out) == 1 else out


if __name__ == "__main__":
    with TafsirMCP() as m:
        print(json.dumps([t.get("name") for t in m.list_tools()], ensure_ascii=False))
