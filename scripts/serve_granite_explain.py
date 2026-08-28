#!/usr/bin/env python3
"""Athena sidecar — ontology explain, actions, alert FSM, watchlist, what-if.

  python scripts/serve_granite_explain.py
  # default http://127.0.0.1:8787  (ATHENA_BIND / ATHENA_PORT)
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from src.catalog import (  # noqa: E402
    load_watchlist,
    persist_watchlist_role,
    remove_watchlist_object,
    summary as watchlist_summary,
    upsert_watchlist_object,
)
from src.config import ALERTS_DIR  # noqa: E402
from src.object_layer import (  # noqa: E402
    append_action,
    expand_neighbors,
    get_alert_state,
    read_actions,
    update_alert_state,
)
from src.ontology_explain import (
    explain_graph_stream,
    explain_ontology_graph,
)
from src.whatif import run_whatif  # noqa: E402

HOST = os.environ.get("ATHENA_BIND", "127.0.0.1")
PORT = int(os.environ.get("ATHENA_PORT", "8787"))
SIDECAR_TOKEN = os.environ.get("ATHENA_SIDECAR_TOKEN", "")


def _read_investigation() -> dict:
    p = ALERTS_DIR / "investigation_latest.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        if not SIDECAR_TOKEN:
            return True
        got = self.headers.get("X-Athena-Token") or ""
        return got == SIDECAR_TOKEN

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("body must be an object")
        return payload

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)
        if path in ("/health", "/api/health"):
            from src.graph_qa import deepseek_api_key, groq_api_key, tavily_api_key

            self._json(
                200,
                {
                    "ok": True,
                    "service": "athena-sidecar",
                    "deepseek": bool(deepseek_api_key()),
                    "groq": bool(groq_api_key()),
                    "tavily": bool(tavily_api_key()),
                },
            )
            return
        if path in ("/investigation", "/api/investigation"):
            inv = _read_investigation()
            if not inv:
                self._json(404, {"error": "investigation_latest.json missing"})
                return
            self._json(200, inv)
            return
        if path in ("/neighbors", "/api/neighbors"):
            start = (q.get("id") or [""])[0]
            hops = int((q.get("hops") or ["2"])[0] or 2)
            inv = _read_investigation()
            if not inv or not start:
                self._json(400, {"error": "id required and investigation must exist"})
                return
            self._json(200, expand_neighbors(inv, start, hops))
            return
        if path in ("/actions", "/api/actions"):
            self._json(200, {"actions": read_actions()})
            return
        if path in ("/alert-state", "/api/alert-state"):
            norad = (q.get("norad") or [None])[0]
            if norad is None:
                self._json(200, get_alert_state())
                return
            self._json(200, get_alert_state(int(norad)))
            return
        if path in ("/watchlist", "/api/watchlist"):
            self._json(200, {"summary": watchlist_summary(), "objects": load_watchlist()["objects"]})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in (
            "/actions",
            "/api/actions",
            "/alert-state",
            "/api/alert-state",
            "/watchlist",
            "/api/watchlist",
            "/whatif",
            "/api/whatif",
        ) and not self._authorized():
            self._json(401, {"error": "unauthorized"})
            return
        try:
            payload = self._body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(400, {"error": str(exc)})
            return

        if path in ("/actions", "/api/actions"):
            try:
                rec = append_action(payload)
            except Exception as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, rec)
            return

        if path in ("/alert-state", "/api/alert-state"):
            try:
                rec = update_alert_state(
                    int(payload["norad"]),
                    str(payload.get("status") or "ACKNOWLEDGED"),
                    operator=str(payload.get("operator") or "local"),
                    note=str(payload.get("note") or ""),
                )
            except Exception as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, rec)
            return

        if path in ("/watchlist", "/api/watchlist"):
            try:
                if payload.get("role") and payload.get("norad_id") and not payload.get("name"):
                    obj = persist_watchlist_role(int(payload["norad_id"]), str(payload["role"]))
                else:
                    obj = upsert_watchlist_object(payload)
            except Exception as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, {"ok": True, "object": obj, "summary": watchlist_summary()})
            return

        if path in ("/whatif", "/api/whatif"):
            try:
                result = run_whatif(
                    int(payload.get("norad") or payload.get("norad_id") or 9001),
                    delta_km=float(payload.get("delta_km") or 4.5),
                )
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            self._json(200, result)
            return

        if path in ("/explain-stream", "/api/explain-stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self._cors()
            self.end_headers()
            try:
                for ev in explain_graph_stream(payload):
                    raw = ("data: " + json.dumps(ev, default=str) + "\n\n").encode("utf-8")
                    self.wfile.write(raw)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                raw = ("data: " + json.dumps({"error": str(exc)}) + "\n\n").encode("utf-8")
                try:
                    self.wfile.write(raw)
                    self.wfile.flush()
                except OSError:
                    pass
            return

        if path not in ("/explain", "/api/explain"):
            self._json(404, {"error": "not found"})
            return
        try:
            result = explain_ontology_graph(payload)
        except Exception as exc:
            self._json(500, {"error": str(exc)})
            return
        self._json(200, result)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)
        if not self._authorized():
            self._json(401, {"error": "unauthorized"})
            return
        if path not in ("/watchlist", "/api/watchlist"):
            self._json(404, {"error": "not found"})
            return
        norad = (q.get("norad") or [None])[0]
        if norad is None:
            self._json(400, {"error": "norad required"})
            return
        removed = remove_watchlist_object(int(norad))
        self._json(200, {"ok": removed, "summary": watchlist_summary()})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("athena-sidecar: " + (fmt % args) + "\n")


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Athena sidecar on http://{HOST}:{PORT}/api/health")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
