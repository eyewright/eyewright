# Demo video

`eyewright-demo.mp4` is **generated from a tape** by
[VHS](https://github.com/charmbracelet/vhs) — no screen recording, no human.

## Render

```powershell
pwsh -File docs/demo/render.ps1
```

Output: `docs/demo/eyewright-demo.mp4` (2560x1440, ~29 s).

## What it shows

1. `uv tool install eyewright` — a real install from PyPI.
2. `eyewright gate` on a clean change → `p_done 0.9489 · accept`.
3. `eyewright gate` on an untested change → `review-no-signal`, with the second
   eye (`laya-td: 0.2211`) visible in `trace.consults`.
4. `eyewright ask --choices` → `optimize · 0.8137`.

The numbers are whatever the local models return on the render machine — the
tape never prints a canned result.

## Prerequisites (this machine)

- **WSL** (Ubuntu) with `vhs`, `ttyd`, `ffmpeg` on PATH, and `uv` (the tape runs
  `uv tool install eyewright`).
- Local decision services reachable from WSL: **Ollama `:11434`** with `tev1:4b`
  (the primary), and **laya-serve `:8000`** (the consulting eye). Mirrored
  networking (`[wsl2] networkingMode=mirrored` in `%UserProfile%\.wslconfig`)
  makes `127.0.0.1` reach the Windows services.

`docs/demo/gate.json` is a **portable** demo config: no `key_file` (loopback
`laya-serve` accepts requests without auth).

## Notes

- `Type` strings containing quotes use **backticks** in the tape.
- `~/.local/bin` is not on the ttyd shell PATH; the tape adds it in a hidden
  setup block.
- Re-render any time the CLI changes; the video is a build artifact.
