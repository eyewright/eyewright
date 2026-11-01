# Demo

Two artefacts, **both generated from tapes** by
[VHS](https://github.com/charmbracelet/vhs), so they are reproducible: change a
line in a tape and re-render, instead of re-recording.

| file | what | size |
|---|---|---|
| `eyewright-demo.mp4` | full demo, two beats, 2560x1440, ~21 s | for applications / release asset |
| `eyewright-demo.gif` | four-beat teaser, 850x540, ~17 s, ~660 KB | for the README (GitHub does not render `<video>` in markdown) |

## Render

```powershell
pwsh -File docs/demo/render.ps1
```

Produces both files. The tapes:

- `eyewright-demo.tape` — the two-beat video.
- `eyewright-readme.tape` — the teaser. Four beats, narrow canvas, cropped to
  its content box afterwards (measured: 805x525 of 1100x560) so there is no dead
  terminal around it, and sized at 850 px so a README column shows it 1:1
  instead of downscaling 15 px text into mush.

## What it shows

The GIF cycles one beat per **decision kind**, on four different questions:

| # | question | verdict | why |
|---|---|---|---|
| 1 | agent loop: `Is the task done?` (all work merged) | `consensus-accept` **0.968** | primary unsure at `0.6663`; both consults fire and agree (`0.9938`, `0.9421`) |
| 2 | agent loop: `Is the task done?` (untested retry loop) | `review-low` **0.197** | primary is sure, so no consult is spent |
| 3 | `Is this migration safe?` (drops a live column) | `consensus-reject` **0.050** | both consults confident it is unsafe |
| 4 | `Safe to merge?` (deployed, no alerts) | `review-conflict` **0.626** | the consults disagree → the caller gathers evidence |

Accept → send back → refuse → escalate. That is the whole policy surface in one
loop. The video keeps the first two beats in full resolution.

The numbers are whatever the local models return on the render machine — the
tapes never print a canned result. They are stable across runs because the
models run at temperature 0.

## Config matches the bench

`docs/demo/gate.json` is the arrangement chosen by `docs/THREE-EYE.md` and
`docs/RESULTS.md` — **`laya-typed-decisions` primary, `tev1:4b` +
`laya-multilingual` consults**. Do not reorder the eyes for a punchier clip: a
more confident primary produces flashier numbers and a worse decision (see
`RESULTS.md` — `tev1:4b` is 0.657 accurate with Brier 0.049; the specialist is
0.766 with Brier 0.019).

The only demo-only difference from `examples/gate.json` is that it drops
`key_file`: the loopback `laya-serve` accepts requests without auth, so the demo
config is portable.

## Prerequisites

- **WSL** (Ubuntu) with `vhs`, `ttyd`, `ffmpeg` on PATH, and `uv` (the tapes run
  `uv tool install eyewright`).
- Local decision services reachable from WSL: **laya-serve `:8000`** (primary +
  `laya-multilingual`) and **Ollama `:11434`** (`tev1:4b`). Mirrored networking
  (`[wsl2] networkingMode=mirrored` in `%UserProfile%\.wslconfig`) makes
  `127.0.0.1` reach the Windows services.

## Notes

- States live in hidden shell variables (`S1`, `S2`, `Q`) so the commands on
  screen stay short enough not to wrap mid-word at teaser width.
- `Type` strings containing quotes use **backticks** in a tape.
- `~/.local/bin` is not on the ttyd shell PATH; both tapes add it in a hidden
  setup block.
- Re-render any time the CLI changes; both files are build artifacts.
