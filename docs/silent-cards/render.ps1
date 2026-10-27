# Render docs/silent-cards/cards.html to 1600x900 PNGs with headless Chromium.
# No human, no screenshot tool: each card is a URL hash, one Chrome invocation.
# Prereqs: WSL with a headless Chrome (this uses Playwright's build; see
# docs/demo/README.md for the sibling VHS setup).
$ErrorActionPreference = "Stop"

$cards = @(
    "c1 01-gate-pr",
    "c2 02-any-decision",
    "c3 03-any-harness",
    "c4 04-tray",
    "c5 05-local-first",
    "c6 06-bench"
)

$dirWsl = (wsl -e wslpath -a "$PSScriptRoot").Trim()

$script = @"
set -e
C=`$HOME/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome
D="$dirWsl"
cd /tmp
while read -r id name; do
  "`$C" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1600,900 --virtual-time-budget=2000 \
    --screenshot="`$D/`$name.png" "file://`$D/cards.html#`$id" 2>/dev/null
  echo "  `$name.png"
done <<EOF
$($cards -join "`n")
EOF
"@ -replace "`r`n", "`n"

$tmp = Join-Path $env:TEMP "render-silent-cards.sh"
[System.IO.File]::WriteAllText($tmp, $script)
wsl -e bash (wsl -e wslpath -a $tmp).Trim()
Write-Host "wrote docs/silent-cards/*.png"
