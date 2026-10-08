"""The Oracle: the three-eye decision gate over cheap local decision models.

Canonical policy implementation. Consumed by the orbit repo
(``from oracle.gate import decide_gate``) and validated by ``bench/``
(THREE-EYE.md, GATE-ANALYSIS.md).

Policy per question:
  - primary (third eye) = laya-typed-decisions, usually via systemone-http
  - p >= accept -> accept; p < consult -> review-low
  - uncertain band [consult, accept) -> both consults answer
      * >= 2 confident (max(p, 1-p) >= high) and same direction -> consensus
      * exactly 1 confident, another consult within delta of main -> review-conflict
      * otherwise -> review-weak / review-no-signal

Decisions: accept | consensus-accept | consensus-reject | review-low |
review-conflict | review-weak | review-no-signal | none. Returns (p_done, trace).
"""

import json
import urllib.request
from pathlib import Path


def _post_json(url, payload, timeout=1800):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def load_key(path):
    """Read an API key file; relative paths resolve against the cwd."""
    if not path:
        return ""
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def systemone_ollama(stage, state, question):
    payload = {
        "model": stage["model"],
        "state": state,
        "questions": {"done": {"type": "noul", "instructions": question}},
    }
    resp = _post_json("http://localhost:11434/v1/systemone", payload)
    return float(resp["answers"]["done"]["noul"])


def systemone_http(url, key, state, question, model=None):
    payload = {
        "state": state,
        "questions": {"done": {"type": "noul", "instructions": question}},
    }
    if model:
        payload["model"] = model
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    if key:
        req.add_header("Authorization", "Bearer " + key)
    with urllib.request.urlopen(req, timeout=1800) as r:
        resp = json.loads(r.read().decode())
    return float(resp["answers"]["done"]["noul"])


def decide_gate(cfg, state, question):
    """Three-eye gate. Primary first; in the uncertain band, consult the others.
    Trust a consensus of >=2 confident consults; otherwise review (retry/gather evidence).

    Decisions: accept | consensus | review-low | review-conflict | review-weak |
    review-no-signal | none. Returns (p_done, trace).
    """
    accept = float(cfg.get("accept_threshold", 0.75))
    consult = float(cfg.get("consult_threshold", 0.55))
    high = float(cfg.get("high_confidence", 0.9))
    delta = float(cfg.get("match_delta", 0.05))
    trace = {"consults": {}}

    def ask(entry):
        t = entry.get("type")
        if t == "systemone-http":
            key = load_key(entry.get("key_file") or "")
            return systemone_http(entry["url"], key, state, question, entry.get("model"))
        if t == "systemone-ollama":
            return systemone_ollama(entry, state, question)
        raise ValueError("unknown consult type")

    p1 = None
    try:
        p1 = ask(cfg.get("primary") or {})
    except Exception as e:
        trace["primary_error"] = str(e)[:140]
    if p1 is None:
        cons = cfg.get("consults") or []
        if cons:
            try:
                p1 = ask(cons[0])
                trace["primary_source"] = cons[0].get("name", "consult0")
            except Exception as e:
                trace["primary_error2"] = str(e)[:140]
    if p1 is None:
        trace["decision"] = "none"
        return 0.0, trace
    trace["primary"] = round(p1, 4)

    if p1 >= accept:
        trace["decision"] = "accept"
        return p1, trace
    if p1 < consult:
        trace["decision"] = "review-low"
        return p1, trace

    ps = []
    for c in (cfg.get("consults") or []):
        name = c.get("name") or c.get("model") or "consult"
        if trace.get("primary_source") == name:
            continue
        try:
            p = ask(c)
        except Exception as e:
            p = None
            trace["consults"][name + "_error"] = str(e)[:80]
        trace["consults"][name] = None if p is None else round(p, 4)
        if p is not None:
            ps.append((name, p))

    confident = [(n, p) for n, p in ps if max(p, 1 - p) >= high]
    if len(confident) >= 2:
        directions = {p >= 0.5 for _, p in confident}
        if len(directions) == 1:
            avg = sum(p for _, p in confident) / len(confident)
            trace["decision"] = "consensus-accept" if avg >= 0.5 else "consensus-reject"
            return avg, trace
        trace["decision"] = "review-conflict"
        return p1, trace
    if len(confident) == 1:
        cn, _ = confident[0]
        others = [(n, p) for n, p in ps if n != cn]
        if any(abs(p - p1) <= delta for _, p in others):
            trace["decision"] = "review-conflict"
        else:
            trace["decision"] = "review-weak"
        return p1, trace
    trace["decision"] = "review-no-signal"
    return p1, trace