# Render the demo video + the README GIF from the two tapes, using VHS in WSL.
# Prereqs: WSL (Ubuntu) with vhs + ttyd + ffmpeg on PATH, and the local decision
# services reachable from WSL (see docs/demo/README.md).
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$repoWsl = (wsl -e wslpath -a "$repo").Trim()

$sh = @'
set -e
export PATH="$HOME/.local/bin:$PATH"
cd REPO
vhs docs/demo/eyewright-demo.tape
vhs docs/demo/eyewright-readme.tape
# The teaser is cropped to its content box (measured: 805x525 of 1100x560) so it
# reads as a tight strip, and sized at 850 px so a README column shows it 1:1
# instead of downscaling the text into mush. Palette-reduced; ~660 KB at 17 s.
ffmpeg -y -v error -i docs/demo/eyewright-readme.mp4 \
  -vf "crop=850:540:0:10,fps=12,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
  -loop 0 docs/demo/eyewright-demo.gif
rm -f docs/demo/eyewright-readme.mp4
'@ -replace 'REPO', $repoWsl -replace "`r`n", "`n"

$tmp = Join-Path $env:TEMP "render-eyewright-demo.sh"
[System.IO.File]::WriteAllText($tmp, $sh)
wsl -e bash (wsl -e wslpath -a $tmp).Trim()

Write-Host "wrote docs/demo/eyewright-demo.mp4 + docs/demo/eyewright-demo.gif"
