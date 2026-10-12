"""Guard: the reported ``__version__`` matches the installed distribution.

Regression test for #1 (version drift).

    uv run python tests/test_version.py
"""

import sys
from importlib.metadata import version as dist_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eyewright  # noqa: E402


def main():
    dist = dist_version("eyewright")
    assert eyewright.__version__ == dist, (eyewright.__version__, dist)
    print(f"version ok: __version__ == dist == {dist}")


if __name__ == "__main__":
    main()
