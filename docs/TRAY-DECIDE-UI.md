# Tray + Decide UI

**Status:** proposal — not implemented (2026-10-15).
**Goal:** keep eyewright one click away — a notification-tray icon that shows service
health and opens a small "Decide" window (files / folders / text) that calls the gate
or the generative engine.

## What already exists

- `supervisor/svcwatch.py` — headless keep-alive for the local model services
  (`services.json`; health probe, detached restart with backoff, logs, single
  instance). Started at logon by `supervisor/install.ps1`, which writes a Startup
  `.cmd` that runs `pythonw.exe supervisor/svcwatch.py` (**windowless** — no console,
  no terminal).
- Four faces: Python `ask()`, CLI `eyewright ask|gate|serve|mcp`, HTTP `serve`
  (`:8090`, `POST /v1/ask`, `POST /v1/gate`), MCP (`eyewright_gate`, `eyewright_ask`).
- `examples/gate.json`: primary `laya-td` (typed-decisions), consults `tev1:4b` +
  `laya-multilingual`, and a `generative` block pinned to **`gemma4:12b`** (Ollama).

## Problem

There is no persistent, human-facing surface. svcwatch is invisible; decisions are
reached through a harness or a terminal. We want to *call* eyewright from the desktop:
click/right-click a tray icon, pick "Decide", drop in files/folders or type a
question, and get an answer.

## Proposal: `eyewright tray`

One windowless process (`pythonw.exe`) that:

1. **Runs the supervisor loop** in a background thread (same as svcwatch), or is a
   thin client of a separately-started svcwatch — see Open questions.
2. **Shows a tray icon** (`pystray` + `Pillow`): green = all services healthy,
   grey = one down. Menu: *Status · Start services · Open log · Decide… · Quit*.
3. **Opens a "Decide" window** (Tkinter) on *Decide…*:
   - **Add files…** (multi-select) and **Add folder…**; entries listed with a remove
     button.
   - a **Text** box for free text.
   - **Question** (default: a generic judgment prompt), optional **choices**, and an
     **engine** selector: `auto` (default) / `typed` / `generative`.
   - **Decide** → builds `state`, calls eyewright, renders answer + confidence +
     engine + trace, plus a **Copy** button.
4. **Calls eyewright over HTTP** (least coupling): the tray targets a running
   `eyewright serve` on `127.0.0.1:8090`, then
   `POST /v1/ask {"state","question","choices"?,"engine"?}`.
   Fallback: in-process `from eyewright import ask` when run in the same venv.

### Building `state`

Deterministic and boring:

```text
<free text>

--- file: notes/plan.md ---
<utf-8 contents, truncated at N chars>

--- folder: some/path (12 entries) ---
- a.py
- b.md
...
```

Rules: text-only (skip/undecodable binaries), cap total size (~1–2 MB) and per-file
size, announce truncation inline. `state` is exactly what the model sees.

## Engines — what "use gemma4" means

- `typed` — the calibrated committee. Best for yes/no, choose-one, rate-on-scale,
  where the frozen-holdout numbers apply.
- `generative` — `gemma4:12b` with a strict JSON contract. Flexible free-form;
  confidence is the model's own and **not calibrated**.
- `auto` — typed first, gemma4 fallback.

gemma4 is already the generative / System-2 eye, so the tray only has to select the
engine and report which one answered. Default `auto`; allow forcing `typed` for
high-trust calls.

## Autostart without the console flash

`install.ps1` writes a `.cmd`; a `.cmd` at logon runs through `cmd.exe`, which can
flash a console window. Replace it with a shortcut that has no `cmd.exe`:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\eyewright tray.lnk
    ->  pythonw.exe "…\supervisor\tray.py"
```

(or a hidden scheduled task). The tray is `pythonw`, so it stays windowless.

## Gotchas

- **Threading (the main wrinkle).** pystray runs its menu callbacks on its own
  thread; Tk wants the main thread and a running event loop. Calling Tk directly from
  a pystray callback hangs or crashes. Options:
  (a) Tk owns the main thread, pystray callbacks push onto a `queue.Queue` the Tk
  loop drains; (b) run the dialog as a short-lived subprocess; (c) use a non-Tk
  dialog. Prefer (a).
- **Input size / binaries.** Cap and text-only as above; files can be huge.
- **Latency.** A 12B call takes seconds; run it off the UI thread, show progress,
  disable the button while in flight.
- **Service health.** Decisions fail if services are down; the tray should reflect
  svcwatch state and offer "Start services" instead of failing silently.
- **Deterministic first.** For arithmetic/exact checks, call the check — eyewright is
  for judgment, not computation.
- **Trust / egress.** Gate configs are trusted input (`key_file`, `url`). The local
  default sends nothing off-box; a configured `openrouter-decisions` eye sends
  `state`/`question` to the cloud. The UI should say which engine (and whether it is
  local) produced the answer.

## Open questions

- Does the tray own the supervisor loop, or stay a thin client of a separate
  svcwatch? (Thin is simpler; one process to start is nicer.)
- Where to keep recent decisions — nowhere, a local JSONL, or a vault note?
- A hotkey to open Decide without the tray?
- Show the committee trace by default, or behind a disclosure?
