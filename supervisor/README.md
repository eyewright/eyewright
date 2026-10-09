# svcwatch

Tiny keep-alive supervisor for local model services (`laya-serve`, optionally
`ollama`). Reads `services.json`, probes each health URL, starts missing services
detached, and restarts with backoff. Generic on purpose — ctxd's Model Router can
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
pwsh -File supervisor/install.ps1            # register + start now
pwsh -File supervisor/install.ps1 -Uninstall # remove
```

Registers a Task Scheduler task (`eyewright-svcwatch`) at logon. Not a Windows
service (no admin); if the task fails to register, `install.ps1` prints the
`schtasks` fallback.
