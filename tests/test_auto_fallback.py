"""#4: ``engine="auto"`` falls back to the generative engine when the typed path
has no usable signal (a no-signal decision, or an exception).

No network: ``decide_gate`` and ``ask_generative`` are monkeypatched.

    uv run python tests/test_auto_fallback.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eyewright.decide as D  # noqa: E402
import eyewright.generative as Gen  # noqa: E402

CFG = {"generative": {"type": "ollama", "model": "x"}}


def stub_gen(cfg, state, question, choices=None, levels=None, kind=None):
    return {"kind": kind, "answer": "yes", "confidence": 0.5, "engine": "generative"}


def main():
    Gen.ask_generative = stub_gen

    # no usable typed signal -> fall back. `error-primary` is not in this set:
    # gate.py sets it and raises, so it is covered by the exception case below.
    for decision in ("none", "review-primary-unavailable"):
        D.decide_gate = lambda cfg, s, q, d=decision: (0.0, {"decision": d})
        out = D.ask(CFG, "s", "q", engine="auto")
        assert out.get("fallback") == "typed->generative", (decision, out)
        print(f"auto falls back on {decision}: ok")

    # a real typed signal is kept
    D.decide_gate = lambda cfg, s, q: (0.9, {"decision": "accept"})
    out = D.ask(CFG, "s", "q", engine="auto")
    assert "fallback" not in out and out["answer"] == "yes", out
    print("auto keeps typed signal: ok")

    # exception path (e.g. on_primary_unavailable = "error")
    def boom(cfg, s, q):
        raise RuntimeError("primary unavailable")

    D.decide_gate = boom
    out = D.ask(CFG, "s", "q", engine="auto")
    assert out.get("fallback") == "typed->generative", out
    assert out.get("typed_error"), out
    print("auto falls back on typed error: ok")

    print("ALL AUTO-FALLBACK TESTS PASSED")


if __name__ == "__main__":
    main()
