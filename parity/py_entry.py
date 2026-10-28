"""Run the untouched Python CLI as a subprocess (the package has no __main__)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eyewright.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
