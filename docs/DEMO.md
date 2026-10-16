# The 90-second eyewright demo

Recording script. Target **90 s**. Everything runs **locally** on the recorder's
machine. Numbers below are the shapes to show; **dry-run every command off-camera**
and keep the real output for the take.

## Pre-flight (once, off-camera)
- **Services up:** laya-serve `:8000` + Ollama `:11434`. Fastest: run one command
  with `--start-services`, or start the supervisor (`supervisor/svcwatch.py`).
- `uv sync --extra mcp` so the venv is ready.
- Terminal: 1080p, 16–18 pt font, dark theme, clean prompt, no scrollback noise.
- **Dry-run** each command; note the real `decision`/`confidence` values.
- Have the README bench table open as B-roll in case a live call is slow.

## Beats

**0:00 — the problem** (empty terminal, one line on screen)
> "Every agent loop has a *decide* step — 'is this done?' — and almost everyone
> hardcodes it as a magic number. It's the weakest part of the loop."

On screen: `if score > 0.7: accept  # the magic number`

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

## Post
- Trim to ≤ 90 s, add captions, 1080p.
- Upload; add the link to the README; use it in the launch post.
