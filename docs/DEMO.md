# The 90-second eyewright demo

> **The video is generated, not screen-recorded.** `docs/demo/eyewright-demo.mp4`
> comes from `docs/demo/eyewright-demo.tape` — re-render it with
> `docs/demo/render.ps1`. This file is the **beat script**: what each segment
> claims, and the commands behind it. Nothing here needs to be recorded by hand.

Beat script. The shipped demo is ~21 s and silent; the timings below describe a
longer cut if one is ever needed. Numbers are shapes to show, not fixtures —
re-run the commands for real output.

## Format (read first)
This is **one continuous screen recording — not screenshots.** You screen-record as
you do the actions; the `0:00 / 0:12 / …` below are **timestamps in the video**
(moments), not files. Record with the **terminal maximized** (OBS *Window Capture*
on the terminal window, or just a full-screen terminal; Windows Game Bar works too).

Everything happens in **one terminal** except two **optional** browser-tab beats
(the bench table at 1:00, the URL at 1:15) — skip those by narrating over the
terminal. You type exactly four things: nothing (0:00), command 1 (0:12),
command 2 (0:30), and `pip install` (1:15).

## Pre-flight (once, off-camera)
- **Services up:** laya-serve `:8000` + Ollama `:11434`. Fastest: run one command
  with `--start-services`, or start the supervisor (`supervisor/svcwatch.py`).
- `uv sync` so the venv is ready (default `runtime` group: mcp + tray deps).
- Terminal: 1080p, 16–18 pt font, dark theme, clean prompt, no scrollback noise.
- **Dry-run** each command; note the real `decision`/`confidence` values.
- Have the README bench table open as B-roll in case a live call is slow.

## Beats

**0:00 — the problem** (empty terminal — just talk; no action)
> "Every agent loop has a *decide* step — 'is this done?' — and almost everyone
> hardcodes it as a magic number. It's the weakest part of the loop."

(Optional: overlay the one line `if score > 0.7: accept  # the magic number` in
edit. Not required.)

**0:12 — the typed gate**
```powershell
uv run eyewright gate --state "The agent changed the login flow. Unit tests pass; no integration test was added." --question "Is this change safe to merge?"
```
> "eyewright replaces the magic number with a typed gate: **accept**, **reject**,
> or send it back for **review**."

On screen: the JSON result — `p_done`, `decision`, and the `trace.consults` block.

**0:30 — one call, any typed decision**
```powershell
uv run eyewright ask --state "p95 latency = 480 ms; the budget is 200 ms" --question "Which action?" --choices '{"optimize":"optimize the hot path","review":"gather more data","ship":"ship anyway"}'
```
> "Not just yes/no — choices and scales, one call."

**0:45 — it's a committee, not one model**
> "A local specialist is the main eye. When it's unsure, two more models consult;
> agreement is a decisive verdict, disagreement routes to review instead of a
> guess. All local — nothing leaves the machine."

On screen: the `trace.consults` block, or `docs/THREE-EYE.md`.

**1:00 — the bench card**
> "On a 600-decision benchmark, the local trio acts on 23.7% of decisions at
> 90.8% acted accuracy — and up to 34% when a local System-2 model is added."

On screen: the README screening table.

**1:15 — install + repo**
```powershell
pip install eyewright
```
> "Local-first by default, cloud consult optional. `pip install eyewright` — code
> and docs at github.com/eyewright/eyewright."

On screen: the install line + the repo URL.

## MCP (say it, don't demo the setup)
> "The same engine is an MCP server — `eyewright_gate` / `eyewright_ask` — so any
> harness can call it in-loop."

(Showing MCP on camera needs a harness; narrate it and keep the demo CLI-based.)

## Fallbacks
- **Slow gate:** paste the pre-captured JSON, or use `--engine auto` (generative fallback).
- **laya-serve down:** re-run with `--start-services`.
- **Any error on camera:** cut the take; re-record. Never narrate a number the screen doesn't show.

## Bonus (optional) — the tray, ~15 s (separate clip)
The tray is a **desktop UI**, so this needs **Display Capture** (or a separate
recording) — terminal Window Capture will not show it. Service must be running.

1. Cursor over the tray icon → tooltip / green "services healthy".
2. Click → the **Decide** window opens.
3. Drop a file (or type a question) → click **Decide**.
4. Result appears (decision + confidence).
5. Cut.

Optional narration: *"Or skip the terminal — click the tray icon, drop in a file,
get the same decision."*

Install: `pwsh -File supervisor/install.ps1 -Tray` · self-check:
`python supervisor/tray.py --check` · docs: `docs/TRAY-DECIDE-UI.md`.

## Post
- Trim to ≤ 90 s, add captions, 1080p.
- Upload; add the link to the README; use it in the launch post.
