# svcwatch

Tiny keep-alive supervisor for local model services (`laya-serve`, optionally
`ollama`). Reads `services.json`, probes each health URL, starts missing services
detached, and restarts with backoff. Generic on purpose — an agent control plane's Model Router can
adopt the same descriptor later.

```powershell
uv run python supervisor/svcwatch.py --status   # probe once
uv run python supervisor/svcwatch.py --once     # start anything that's down, exit
uv run python supervisor/svcwatch.py            # watch (default)
```

- Descriptor: `services.json` — `cmd`, `cwd`, `env`, `health`,
  `restart.backoff_s` / `restart.startup_grace_s`, `log`.
- Logs: `logs/svcwatch.log`, `logs/<service>.log`.
- Single instance: `svcwatch.pid` guards watch mode.
- **`laya-serve` ships `LAYA_DEFAULT_MODEL=typed-decisions`** — the package default
  is `english`, which silently gives a non-specialist decision eye.

## Autostart at logon

```powershell
pwsh -File supervisor/install.ps1            # headless svcwatch launcher
pwsh -File supervisor/install.ps1 -Tray      # tray + supervisor + Decide dialog
pwsh -File supervisor/install.ps1 -Uninstall # remove
```

Both branches write a per-user **Startup folder** entry (no admin); `-Tray` writes
`eyewright tray.lnk` instead of a `.cmd` so no `cmd.exe` flashes.

The tray must be launched with a **GUI-subsystem** `pythonw.exe`. `uv` builds the
venv's `Scripts\pythonw.exe` as a copy of `python.exe` (console subsystem), which
opens a terminal at logon. `install.ps1 -Tray` prefers the base uv `pythonw`
(`%APPDATA%\uv\python\cpython-3.12-windows-x86_64-none\pythonw.exe`), and
`tray.py` adds the venv's `Lib\site-packages` to `sys.path` so pystray/Pillow
still import.

Check a launcher before trusting it: PE subsystem `2` = GUI, `3` = console
(optional header +0x44).
