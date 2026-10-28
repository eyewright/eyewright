Output "docs/demo/eyewright-demo.mp4"
Set FontSize 18
Set Width 2560
Set Height 1440
Set Padding 28
Set Theme "Dracula"
Set Shell "bash"
Set TypingSpeed 12ms

# Hidden setup: PATH for the ttyd shell, a fresh install line on camera, and the
# two states as variables so the commands on screen stay short enough not to wrap
# (the README GIF renders at ~1100 px).
Hide
Type "uv tool uninstall eyewright >/dev/null 2>&1; export PATH=$HOME/.local/bin:$PATH; S1='Done: all requested changes are implemented, tests pass, and the PR is merged.'; S2='Adds a retry loop around the API call; tests pass; no test for the retry path.'; Q='Is the task done?'; clear"
Enter
Sleep 500ms
Show

# Title
Type `clear; echo; echo '  eyewright - typed decisions from small local models'; echo`
Enter
Sleep 2s

# Install
Type "uv tool install eyewright"
Enter
Sleep 4s

# 1. The committee carries a wavering primary: 0.67 -> two more eyes agree -> accept.
Type `eyewright gate --config docs/demo/gate.json --state "Done: all requested changes are implemented, tests pass, and the PR is merged." --question "Is the task done?"`
Enter
Wait+Screen /"consensus-accept"/
Sleep 5s

# 2. Clearly not done: the primary is sure, so no consult is wasted.
Type `eyewright gate --config docs/demo/gate.json --state "Adds a retry loop around the API call; tests pass; no test for the retry path." --question "Is the task done?"`
Enter
Wait+Screen /"review-low"/
Sleep 4s

# Closer: one clean cut to the end card, not a long command typed on camera.
Hide
Type `clear; printf '\n%.0s' {1..18}; echo '  pip install eyewright'; echo '  github.com/eyewright/eyewright'; echo; echo '  local-first - typed decisions - CLI + MCP'`
Enter
Sleep 800ms
Show
Sleep 3500ms
