# Demo video

`eyewright-demo.mp4` is **generated from a tape** by
[VHS](https://github.com/charmbracelet/vhs) — no screen recording, no human.

## Render

```powershell
pwsh -File docs/demo/render.ps1
```

Output: `docs/demo/eyewright-demo.mp4` (2560x1440, ~27 s).

## What it shows

The gate on an agent-loop step (`"Is the task done?"`), twice:

1. `uv tool install eyewright` — a real install from PyPI.
2. **The committee carries a wavering primary.** The primary eye is unsure
   (`primary: 0.6663`), so both consults fire; they agree at `0.9938` and
   `0.9421` → `consensus-accept`, `p_done 0.968`.
3. **It says no without wasting a consult.** Clearly incomplete work scores
   `0.197` → `review-low`, `consults: {}`.

Both outcomes are the product working as designed: it acts when the eyes agree
and sends work back when they don't. The numbers are whatever the local models
return on the render machine — the tape never prints a canned result.

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

## Prerequisites (this machine)

- **WSL** (Ubuntu) with `vhs`, `ttyd`, `ffmpeg` on PATH, and `uv` (the tape runs
  `uv tool install eyewright`).
- Local decision services reachable from WSL: **laya-serve `:8000`** (primary +
  `laya-multilingual`) and **Ollama `:11434`** (`tev1:4b`). Mirrored networking
  (`[wsl2] networkingMode=mirrored` in `%UserProfile%\.wslconfig`) makes
  `127.0.0.1` reach the Windows services.

## Notes

- `Type` strings containing quotes use **backticks** in the tape.
- `~/.local/bin` is not on the ttyd shell PATH; the tape adds it in a hidden
  setup block.
- The end card is a hidden cut: the command is typed and run inside `Hide`, so
  the video never shows a `printf` being typed.
- Re-render any time the CLI changes; the video is a build artifact.
