"""The Oracle - local decision core: the three-eye gate + one-call typed decisions."""

from .decide import ask
from .gate import decide_gate, load_key, systemone_http, systemone_ollama  # noqa: F401

__version__ = "0.3.0"