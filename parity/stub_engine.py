"""Replay engine for the parity harness: a local `systemone-http` stub.

Both implementations call this over real HTTP, so request shape, JSON parsing,
timeouts and error handling are all exercised. The script maps a model name to
a list of steps; steps are consumed in order and the last one repeats.

Step forms:
    0.9                                  -> {"answers": {<qid>: {"noul": 0.9}}}
    {"noul": 0.9}                        -> explicit
    {"choice": "b", "probabilities": {}} -> choice answer
    {"score": 3, "confidence": 0.7}      -> score answer
    {"error": 500}                       -> HTTP error status
    {"sleep": 1.5}                       -> delay before responding
    {"raw": {...}}                       -> literal response body

Usage: stub_engine.py <script.json> <transcript.jsonl>
Prints `PORT <n>` on stdout once listening.
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Script:
    def __init__(self, steps, transcript):
        self.steps = steps
        self.transcript = Path(transcript)
        self.counts = {}
        self.lock = threading.Lock()

    def next_step(self, model):
        with self.lock:
            i = self.counts.get(model, 0)
            self.counts[model] = i + 1
            with self.transcript.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"model": model}) + "\n")
        steps = self.steps.get(model) or self.steps.get("*") or [0.5]
        return steps[min(i, len(steps) - 1)]


def answer_for(questions, step):
    answers = {}
    for qid, q in (questions or {}).items():
        kind = (q or {}).get("type")
        if kind == "choice":
            answers[qid] = {
                "choice": step.get("choice"),
                "probabilities": step.get("probabilities") or {},
                "confidence": step.get("confidence"),
            }
        elif kind == "score":
            answers[qid] = {
                "score": step.get("score"),
                "confidence": step.get("confidence"),
            }
        else:
            answers[qid] = {"noul": step.get("noul", 0.5)}
    return answers


def main():
    script_path, transcript = sys.argv[1], sys.argv[2]
    script = Script(json.loads(Path(script_path).read_text(encoding="utf-8")), transcript)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/health"):
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            model = body.get("model") or "default"
            step = script.next_step(model)
            if isinstance(step, (int, float)):
                step = {"noul": float(step)}
            if "sleep" in step:
                time.sleep(float(step["sleep"]))
            if "error" in step:
                self._send(int(step["error"]), {"error": "stub"})
                return
            if "raw" in step:
                self._send(200, step["raw"])
                return
            self._send(200, {
                "answers": answer_for(body.get("questions"), step),
                "model": model,
            })

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(f"PORT {httpd.server_address[1]}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
