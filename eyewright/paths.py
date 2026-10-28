"""Where eyewright keeps user-writable state.

A published install cannot write inside ``site-packages``, so the tray's pid and
logs - and the default configs - live in one directory:

    $EYEWRIGHT_HOME
    %LOCALAPPDATA%\\eyewright        (Windows, default)
    ~/.local/share/eyewright         (elsewhere, default)
"""

import os
from pathlib import Path

_CHECKOUT = Path(__file__).resolve().parents[1]


def home() -> Path:
    """The user-writable state directory (created by whoever writes to it)."""
    root = os.environ.get("EYEWRIGHT_HOME")
    if root:
        return Path(os.path.expanduser(os.path.expandvars(root)))
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / "eyewright"


def file(env_var: str, name: str, checkout_rel: str) -> Path:
    """Resolve a config file: explicit env var, user dir, then a source checkout.

    The checkout fallback makes a git clone work with no setup, and is skipped
    silently when eyewright is installed (there is no repo beside site-packages).
    """
    explicit = os.environ.get(env_var)
    if explicit:
        return Path(os.path.expanduser(os.path.expandvars(explicit)))
    user = home() / name
    if user.exists():
        return user
    checkout = _CHECKOUT / checkout_rel
    return checkout if checkout.exists() else user
