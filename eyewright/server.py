"""eyewright serve - one local HTTP endpoint for decisions.

Endpoints:
  GET  /health
  POST /v1/gate   {"state": str, "question": str}                    -> {p_done, decision, trace}
  POST /v1/ask    {"state": str, "question": str, "choices"?: {...}} -> answer dict

Loopback-only by default (no auth on 127.0.0.1). Config is a JSON file with the
gate config (primary + consults); see examples/gate.json.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .decide import ask
from .gate import decide_gate


def make_handler(cfg):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"eyewright/{__version__}"

        def _send(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/health", "/"):
                self._send(200, {"status": "ok", "service": "eyewright", "version": __version__})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n).decode() or "{}")
            except Exception as e:
                self._send(400, {"error": f"bad json: {e}"})
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
                self._send(500, {"error": str(e)[:300]})

        def log_message(self, fmt, *args):
            print("[eyewright] " + fmt % args)

    return Handler


def serve(cfg, host="127.0.0.1", port=8090):
    httpd = ThreadingHTTPServer((host, port), make_handler(cfg))
    print(f"eyewright serving on http://{host}:{port}  (gate: /v1/gate, ask: /v1/ask)")
    httpd.serve_forever()