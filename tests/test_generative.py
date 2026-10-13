"""Unit tests for the generative-engine helpers (#21): ``_extract_json`` /
``_normalize_noul``. No network.

    uv run python tests/test_generative.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eyewright.generative import _extract_json as X  # noqa: E402
from eyewright.generative import _normalize_noul as N  # noqa: E402


def main():
    # _extract_json: first object; tolerant of prose and stray braces
    assert X('prose {"answer": true, "confidence": 0.9} trailing }') == {
        "answer": True, "confidence": 0.9}
    assert X('{"a": 1}{"b": 2}') == {"a": 1}
    assert X('reason } weird {"answer": "yes"}') == {"answer": "yes"}
    assert X('{"nested": {"x": 1}} after') == {"nested": {"x": 1}}
    assert X("no object here") is None
    assert X("") is None

    # _normalize_noul: canonical yes/no across string/bool/number; unknown -> (v, False)
    for v in ("yes", "y", "true", "t", "1", True, 1):
        assert N(v) == ("yes", True), (v, N(v))
    for v in ("no", "n", "false", "f", "0", False, 0):
        assert N(v) == ("no", True), (v, N(v))
    assert N("TRUE") == ("yes", True) and N("False") == ("no", True)
    assert N("maybe") == ("maybe", False)
    assert N(None) == (None, False)

    print("ALL GENERATIVE TESTS PASSED")


if __name__ == "__main__":
    main()
