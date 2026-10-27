# Demo video

`eyewright-demo.mp4` is **generated from a tape** by
[VHS](https://github.com/charmbracelet/vhs) — no screen recording, no human.

## Render

```powershell
pwsh -File docs/demo/render.ps1
```

Output: `docs/demo/eyewright-demo.mp4`.

## Prerequisites (this machine)

- **WSL** (Ubuntu) with `vhs`, `ttyd`, `ffmpeg` on PATH.
- The local decision services reachable from WSL: `laya-serve :8000` and
  Ollama `:11434`. Mirrored networking (`[wsl2] networkingMode=mirrored` in
  `%UserProfile%\.wslconfig`) makes `127.0.0.1` reach the Windows services.
- `uv` in WSL (the tape runs `uv tool install eyewright`).

`docs/demo/gate.json` is a **portable** demo config (no `key_file`; the local
`laya-serve` accepts loopback without auth).

## Notes

- `Type` strings containing quotes use **backticks** in the tape.
- `~/.local/bin` is not on the ttyd shell PATH; the tape adds it in a hidden
  setup block.
- Re-render any time the CLI changes; the video is a build artifact.
