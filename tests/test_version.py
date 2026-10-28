"""Guard: the reported ``__version__`` matches the installed distribution.

Regression test for #1 (version drift).

    uv run python tests/test_version.py
"""

import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as dist_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eyewright  # noqa: E402


def main():
    try:
        dist = dist_version("eyewright")
    except PackageNotFoundError:
        # Running from a source checkout that was never installed. The check is
        # about installed metadata matching __version__, so there is nothing to
        # compare - skip rather than raise (a bare traceback here reads like a
        # broken test, not a missing install).
        print("version check skipped: eyewright is not installed in this environment")
        return 0
    assert eyewright.__version__ == dist, (eyewright.__version__, dist)
    print(f"version ok: __version__ == dist == {dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
