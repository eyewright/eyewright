"""Config-trust hardening (#13): URL allowlist + sensitive key-file rejection.

No network: the guards raise before any request is attempted.

    uv run python tests/test_security.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eyewright.gate as G  # noqa: E402


def raises_value_error(fn, needle):
    try:
        fn()
    except ValueError as e:
        assert needle in str(e), (needle, str(e))
        return
    raise AssertionError(f"expected ValueError containing {needle!r}")


def main():
    # 1. systemone-http: loopback allowed (connection error is fine), remote refused
    try:
        G.systemone_http("http://127.0.0.1:9/x", "", "s", "q", timeout=0.05)
    except ValueError:
        raise AssertionError("loopback should be allowed")
    except Exception:
        pass  # connection refused is expected

    raises_value_error(
        lambda: G.systemone_http("http://192.0.2.1:9/x", "", "s", "q", timeout=0.05),
        "non-loopback",
    )

    # 2. allow_remote opts in (no ValueError; the connection attempt fails instead)
    try:
        G.systemone_http("http://192.0.2.1:9/x", "", "s", "q", timeout=0.05, allow_remote=True)
    except ValueError:
        raise AssertionError("allow_remote should permit a remote host")
    except Exception:
        pass

    # 3. openrouter-decisions: only the OpenRouter host is allowed
    raises_value_error(
        lambda: G.openrouter_decisions(
            {"type": "openrouter-decisions", "model": "x", "url": "https://evil.example/x"},
            "s", "q", timeout=0.05,
        ),
        "non-OpenRouter",
    )

    # 4. sensitive credential files are never read as an API key
    raises_value_error(lambda: G.load_key("~/.ssh/id_rsa"), "sensitive")
    raises_value_error(lambda: G.load_key("~/.aws/credentials"), "sensitive")
    raises_value_error(lambda: G.load_key("~/.npmrc"), "sensitive")

    # 5. an ordinary key path is not rejected (missing file -> empty string)
    assert G.load_key("~/.laya-api-key-definitely-missing") == ""

    print("ALL SECURITY TESTS PASSED")


if __name__ == "__main__":
    main()
