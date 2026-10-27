"""eyewright.ask - one call, any typed decision.

eyewright's second face: not just the three-eye "done" gate, but a single
callable for typed decisions:

  - noul (no choices):     the three-eye gate policy on a yes/no question
  - choice (choices dict): the primary decision model picks the option
  - score (levels list):   the primary decision model rates on the scale

Uniform answer: {"kind", "answer", "confidence", "probabilities"?, "trace"}.

Any program can call this in-process (``from eyewright import ask``); ``eyewright
serve`` exposes it over HTTP and ``eyewright mcp`` exposes it as MCP tools.
"""

import json
import urllib.request

from .gate import DEFAULT_TIMEOUT_S, _require_loopback, decide_gate, load_key

# decisions that mean the typed path produced no usable signal: `auto` may fall back
_NO_TYPED_SIGNAL = frozenset({"none", "review-primary-unavailable", "error-primary"})


def _post_json(url, payload, timeout=DEFAULT_TIMEOUT_S):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call_engine(entry, state, questions, timeout=DEFAULT_TIMEOUT_S):
    """One systemone call against a configured engine (an `entry` from the gate config)."""
    t = entry.get("type")
    if t == "systemone-http":
        _require_loopback(entry["url"], bool(entry.get("allow_remote")))
        payload = {"state": state, "questions": questions}
        if entry.get("model"):
            payload["model"] = entry["model"]
        req = urllib.request.Request(
            entry["url"], data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        key = load_key(entry.get("key_file") or "")
        if key:
            req.add_header("Authorization", "Bearer " + key)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    if t == "systemone-ollama":
        payload = {"model": entry["model"], "state": state, "questions": questions}
        return _post_json("http://localhost:11434/v1/systemone", payload, timeout=timeout)
    raise ValueError(f"unknown engine type {t!r}")


def ask(cfg, state, question, choices=None, levels=None, engine=None, qid="q"):
    """One decision. `choices` -> choice question; `levels` -> score; else yes/no (noul).

    engine:
      None / "typed" -> the decision models: noul runs the three-eye gate;
                        choice/score use the primary engine.
      "generative"   -> the local generative adjudicator (cfg["generative"]) answers
                        with a strict JSON contract; its confidence is the model's
                        own estimate (``"calibrated": false``).
      "auto"         -> typed first; fall back to the generative engine when the
                        typed path errors or has no signal (needs a generative block).
    """
    if choices:
        questions = {qid: {"type": "choice", "instructions": question, "criteria": choices}}
        kind = "choice"
    elif levels:
        questions = {qid: {"type": "score", "instructions": question, "criteria": levels}}
        kind = "score"
    else:
        questions = {qid: {"type": "noul", "instructions": question}}
        kind = "noul"

    if engine == "generative":
        from .generative import ask_generative

        return ask_generative(cfg, state, question, choices=choices, levels=levels, kind=kind)

    timeout = float(cfg.get("timeout_s", DEFAULT_TIMEOUT_S))
    if kind == "noul":
        try:
            p, trace = decide_gate(cfg, state, question)
        except Exception as e:  # e.g. on_primary_unavailable = "error"
            if engine == "auto" and cfg.get("generative"):
                from .generative import ask_generative

                fb = ask_generative(cfg, state, question, choices=choices, levels=levels, kind=kind)
                fb["fallback"] = "typed->generative"
                fb["typed_error"] = str(e)[:140]
                return fb
            raise
        out = {
            "kind": "noul",
            "answer": "yes" if p >= 0.5 else "no",
            "confidence": round(max(p, 1 - p), 4),
            "p_true": round(p, 4),
            "trace": trace,
        }
        if engine == "auto" and trace.get("decision") in _NO_TYPED_SIGNAL and cfg.get("generative"):
            from .generative import ask_generative

            fb = ask_generative(cfg, state, question, choices=choices, levels=levels, kind=kind)
            fb["fallback"] = "typed->generative"
            return fb
        return out

    entry = cfg.get("primary")
    if not entry:
        raise ValueError("config has no primary engine")
    try:
        resp = call_engine(entry, state, questions, timeout)
    except Exception as e:
        if engine == "auto" and cfg.get("generative"):
            from .generative import ask_generative

            fb = ask_generative(cfg, state, question, choices=choices, levels=levels, kind=kind)
            fb["fallback"] = "typed->generative"
            return fb
        return {"kind": kind, "answer": None, "confidence": None, "error": str(e)[:200]}
    ans = (resp.get("answers") or {}).get(qid) or {}
    probs = ans.get("probabilities") or {}
    if kind == "choice":
        answer = ans.get("choice") or (max(probs, key=probs.get) if probs else None)
        conf = ans.get("confidence")
        if conf is None and answer is not None:
            conf = probs.get(answer, 0.0)
    else:
        answer = ans.get("score")
        conf = ans.get("confidence")
    out = {
        "kind": kind,
        "answer": answer,
        "confidence": round(float(conf), 4) if conf is not None else None,
        "probabilities": {k: round(float(v), 4) for k, v in probs.items()},
        "model": resp.get("model"),
        "trace": {"engine": entry.get("name") or entry.get("model") or entry.get("type")},
    }
    if engine == "auto" and out.get("answer") is None and cfg.get("generative"):
        from .generative import ask_generative

        fb = ask_generative(cfg, state, question, choices=choices, levels=levels, kind=kind)
        fb["fallback"] = "typed->generative"
        return fb
    return out