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

`-Tray` starts the tray through `wscript.exe tray-hidden.vbs` with window style 0.
Neither the venv's `pythonw.exe` (a copy of `python.exe`, i.e. console subsystem)
nor `eyewright-tray.exe` is safe to start directly: the `gui-scripts` entry point
is a uv **trampoline** that re-execs `pythonw`, and the re-exec does not inherit a
hidden window, so the terminal comes back. Whoever creates the first console must
be the process started with style 0 — hence the `.vbs`.

Verify by window visibility, not by the process list: the console window still
exists, it is just hidden. From an interactive session, enumerate windows and
check `IsWindowVisible` for the `ConsoleWindowClass` owned by the tray's
`pythonw` — it should be `false` while the process keeps running.
