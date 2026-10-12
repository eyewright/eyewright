"""eyewright serve - one local HTTP endpoint for decisions.

Endpoints:
  GET  /health       liveness (always open)
  GET  /health/deep  dependency readiness (needs auth when a token is set)
  POST /v1/gate      {"state": str, "question": str}                    -> {p_done, decision, trace}
  POST /v1/ask       {"state": str, "question": str, "choices"?: {...}} -> answer dict

Loopback-only by default. Binding off-loopback **requires** a bearer token
(``--token`` / ``$EYEWRIGHT_TOKEN``); requests must then send
``Authorization: Bearer <token>``. Request bodies are capped. Add ``--cert`` /
``--key`` to serve HTTPS. The token is authentication, not encryption, so use TLS
(or an SSH/VPN tunnel) off-loopback.
"""

import hmac
import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .decide import ask
from .gate import decide_gate

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
DEFAULT_MAX_BODY = 1_000_000  # 1 MB


def _is_loopback(host):
    return host in LOOPBACK


def _dependency_checks(cfg):
    """Health URLs for the configured eyes (deduped by label)."""
    checks = {}
    for e in [cfg.get("primary") or {}] + list(cfg.get("consults") or []):
        name = e.get("name") or e.get("model") or e.get("type") or "eye"
        t = e.get("type")
        if t == "systemone-http" and e.get("url"):
            root = e["url"].split("/v1/")[0]
            checks[f"{name}"] = root + "/health"
        elif t == "systemone-ollama":
            checks[f"{name} (ollama)"] = "http://localhost:11434/api/tags"
        elif t == "openrouter-decisions":
            checks[f"{name} (openrouter)"] = "https://openrouter.ai/api/v1/models"
    return checks


def deep_health(cfg):
    deps = {}
    ok = True
    for name, url in _dependency_checks(cfg).items():
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                up = 200 <= r.status < 400
        except Exception:
            up = False
        deps[name] = {"url": url, "ok": up}
        ok = ok and up
    return {"status": "ok" if ok else "degraded", "service": "eyewright",
            "version": __version__, "dependencies": deps}


def make_handler(cfg, token=None, max_body=DEFAULT_MAX_BODY):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"eyewright/{__version__}"

        def _send(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            if not token:
                return True
            header = self.headers.get("Authorization", "")
            return hmac.compare_digest(header, "Bearer " + token)

        def do_GET(self):
            deep = "deep" in self.path
            if deep and not self._authorized():
                self._send(401, {"error": "unauthorized"})
                return
            if self.path.startswith("/health"):
                if deep:
                    self._send(200, deep_health(cfg))
                else:
                    self._send(200, {"status": "ok", "service": "eyewright", "version": __version__})
            elif self.path == "/":
                self._send(200, {"status": "ok", "service": "eyewright", "version": __version__})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._authorized():
                self._send(401, {"error": "unauthorized"})
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self._send(400, {"error": "bad content-length"})
                return
            if n < 0 or n > max_body:
                # drain a bounded amount so the client can read our 413 cleanly,
                # without ever holding the (oversize) body in memory
                remaining = min(n, 8 * 1024 * 1024) if n > 0 else 0
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                self._send(413, {"error": f"body too large (max {max_body} bytes)"})
                return
            try:
                raw = self.rfile.read(n) if n else b""
                body = json.loads(raw.decode() or "{}")
            except Exception:
                self._send(400, {"error": "invalid json"})
                return
            try:
                if self.path == "/v1/gate":
                    p, trace = decide_gate(cfg, body.get("state", ""), body.get("question", ""))
                    self._send(200, {"p_done": round(p, 4), "decision": trace.get("decision"), "trace": trace})
                elif self.path == "/v1/ask":
                    out = ask(cfg, body.get("state", ""), body.get("question", ""),
                              choices=body.get("choices"), levels=body.get("levels"),
                              engine=body.get("engine"))
                    self._send(200, out)
                else:
                    self._send(404, {"error": "not found"})
            except Exception as e:
                print(f"[eyewright] error handling {self.path}: {e}", file=sys.stderr)
                self._send(500, {"error": "internal error"})

        def log_message(self, fmt, *args):
            print("[eyewright] " + fmt % args)

    return Handler


def serve(cfg, host="127.0.0.1", port=8090, token=None, max_body=DEFAULT_MAX_BODY,
          cert=None, key=None):
    token = token or os.environ.get("EYEWRIGHT_TOKEN")
    if cert and not key:
        raise SystemExit("--cert requires --key")
    if not _is_loopback(host) and not token:
        raise SystemExit(
            f"refusing to bind {host} without a bearer token; pass --token or set EYEWRIGHT_TOKEN"
        )
    httpd = ThreadingHTTPServer((host, port), make_handler(cfg, token=token, max_body=max_body))
    if cert:
        import ssl

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert, keyfile=key)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    scheme = "https" if cert else "http"
    note = "  (token required)" if token else ""
    print(f"eyewright serving on {scheme}://{host}:{port}{note}  (gate: /v1/gate, ask: /v1/ask)")
    httpd.serve_forever()
