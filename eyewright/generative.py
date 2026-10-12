"""eyewright generative engine - a general-model adjudicator behind ``ask``.

The typed engines (the laya/tev1 committee) answer the System One shape inside
their training distribution. This engine covers questions outside it: a local
generative model is asked with a strict JSON contract

    {"answer": <"yes"|"no"|option key|level index>, "confidence": 0.0-1.0, "reason": "..."}

Confidence is the model's own estimate -> **not calibrated yet**. Ticket path D
(decide-engine shootout) covers post-hoc calibration; until then the result
carries ``"calibrated": false`` so callers can treat it accordingly.

Engine config (inside the gate config):

    "generative": {"type": "ollama", "model": "gemma4:12b",
                   "options": {"temperature": 0, "num_predict": 200},
                   "think": false}
"""

import json

from .decide import _post_json


def _ollama_chat(model, messages, options=None, fmt="json", think=None, timeout=1800):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": fmt,
        "options": {"temperature": 0, **(options or {})},
    }
    if think is not None:
        payload["think"] = bool(think)
    resp = _post_json("http://localhost:11434/api/chat", payload, timeout=timeout)
    return (resp.get("message") or {}).get("content", "") or ""


def _extract_json(text):
    """Return the first JSON object embedded in ``text`` (tolerant of prose).

    ``raw_decode`` from the first ``{`` so trailing text or a second object cannot
    swallow the parse (a greedy regex used to; see #3).
    """
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except ValueError:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except ValueError:
                        return None
        return None


def _prompt(state, question, choices, levels):
    if choices:
        opts = "\n".join(f"- {k}: {v}" for k, v in choices.items())
        answer_rule = "exactly one of these option keys: " + ", ".join(choices)
    elif levels:
        opts = "\n".join(f"- {i}: {v}" for i, v in enumerate(levels))
        answer_rule = "the 0-based index of the best level"
    else:
        opts = "(none)"
        answer_rule = '"yes" or "no"'
    return (
        "You are a decision engine. Answer with a single JSON object and nothing else:\n"
        '{"answer": <answer>, "confidence": <0.0-1.0>, "reason": "<one short sentence>"}\n\n'
        f'Rules: "answer" must be {answer_rule}. "confidence" is your estimated\n'
        "probability that the answer is correct. Base the answer only on the state.\n\n"
        f"STATE:\n{state}\n\nQUESTION:\n{question}\n\nOPTIONS:\n{opts}"
    )


_YES = {"yes", "y", "true", "t", "1"}
_NO = {"no", "n", "false", "f", "0"}


def _normalize_noul(answer):
    """Map a model's yes/no answer to canonical ``"yes"``/``"no"``.

    Returns ``(value, ok)``. ``ok`` is False when the answer is unrecognized, so
    the caller sees the raw value instead of a silent guess (see #2). Handles the
    JSON boolean and numeric forms as well as the string forms.
    """
    if isinstance(answer, bool):
        return ("yes" if answer else "no"), True
    if isinstance(answer, (int, float)):
        if answer == 1:
            return "yes", True
        if answer == 0:
            return "no", True
    if isinstance(answer, str):
        a = answer.strip().lower()
        if a in _YES:
            return "yes", True
        if a in _NO:
            return "no", True
    return answer, False


def ask_generative(cfg, state, question, choices=None, levels=None, kind=None):
    """One decision from the configured generative model (raw, uncalibrated)."""
    g = cfg.get("generative") or {}
    if not g:
        raise ValueError("config has no 'generative' block")
    kind = kind or ("choice" if choices else "score" if levels else "noul")
    model = g.get("model") or "gemma4:12b"
    content = _ollama_chat(
        model,
        [{"role": "user", "content": _prompt(state, question, choices, levels)}],
        options=g.get("options"),
        fmt=g.get("format", "json"),
        think=g.get("think"),
    )
    obj = _extract_json(content) or {}
    answer = obj.get("answer")
    conf = obj.get("confidence")

    normalized = None
    if kind == "noul":
        answer, normalized = _normalize_noul(answer)
    if kind == "choice" and choices:
        if isinstance(answer, str):
            match = next((k for k in choices if k.lower() == answer.strip().lower()), None)
            if match is None:
                match = next((k for k in choices if k.lower() in answer.lower()), None)
            answer = match
    if kind == "score":
        try:
            answer = int(answer)
        except (TypeError, ValueError):
            pass
    try:
        conf = round(float(conf), 4) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    out = {
        "kind": kind,
        "answer": answer,
        "confidence": conf,
        "reason": obj.get("reason"),
        "model": model,
        "calibrated": False,
        "engine": "generative",
        "raw": content[:600],
    }
    if kind == "noul":
        out["normalized"] = normalized
    return out