"""Resilience tests for the gate: retries + on_primary_unavailable policy.

No network: the decision-eye functions are monkeypatched.

    uv run python tests/test_resilience.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eyewright.gate as G  # noqa: E402


def cfg(policy, retries=1):
    return {
        "primary": {"name": "dead", "type": "systemone-http", "url": "http://127.0.0.1:9/x"},
        "consults": [{"name": "fake", "type": "systemone-ollama", "model": "fake"}],
        "on_primary_unavailable": policy,
        "retries": retries,
        "retry_backoff_s": 0,
    }


# 1. retry: primary fails twice, then succeeds -> accept
state = {"n": 0}


def flaky_http(url, key, s, q, model=None):
    state["n"] += 1
    if state["n"] <= 2:
        raise OSError("boom")
    return 0.9


G.systemone_http = flaky_http
p, t = G.decide_gate(cfg("fallback", retries=3), "s", "q")
assert p == 0.9 and t["decision"] == "accept", (p, t)
assert t.get("policy") == "fallback"
print("retry-then-accept ok")


def boom(*a, **k):
    raise OSError("down")


# 2. fallback: primary dead -> consults[0] stands in (marked)
G.systemone_http = boom
G.systemone_ollama = lambda entry, s, q: 0.95
p, t = G.decide_gate(cfg("fallback"), "s", "q")
assert t["decision"] == "accept" and t.get("primary_source") == "fake", t
assert "primary_error" in t
print("fallback ok (marked, not silent)")

# 3. review: primary dead -> review, do not substitute
G.systemone_ollama = lambda entry, s, q: 0.99
p, t = G.decide_gate(cfg("review"), "s", "q")
assert t["decision"] == "review-primary-unavailable" and p == 0.0, t
print("review policy ok")

# 4. error: primary dead -> raise
try:
    G.decide_gate(cfg("error"), "s", "q")
    raise AssertionError("expected RuntimeError")
except RuntimeError:
    print("error policy ok")

print("ALL RESILIENCE TESTS PASSED")