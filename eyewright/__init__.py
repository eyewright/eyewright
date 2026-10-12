"""eyewright - local decision core: the three-eye gate + one-call typed decisions."""

from importlib.metadata import PackageNotFoundError, version as _dist_version

from .decide import ask
from .gate import decide_gate, load_key, systemone_http, systemone_ollama  # noqa: F401

try:
    __version__ = _dist_version("eyewright")
except PackageNotFoundError:  # running from a source checkout that isn't installed
    __version__ = "0.0.0.dev0"