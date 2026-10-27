# Render the eyewright demo video from the tape, using VHS inside WSL.
# Prereqs: WSL (Ubuntu) with vhs + ttyd + ffmpeg on PATH, and the local
# decision services reachable from WSL (see docs/demo/README.md).
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$repoWsl = (wsl -e wslpath -a "$repo").Trim()

wsl -e bash -lc "cd '$repoWsl' && vhs docs/demo/eyewright-demo.tape"
Write-Host "wrote docs/demo/eyewright-demo.mp4"
