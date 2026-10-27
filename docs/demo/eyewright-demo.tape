Output "docs/demo/eyewright-demo.mp4"
Set FontSize 18
Set Width 2560
Set Height 1440
Set Padding 28
Set Theme "Dracula"
Set Shell "bash"
Set TypingSpeed 12ms

# Hidden setup: PATH for the ttyd shell, and a fresh install line on camera.
Hide
Type "uv tool uninstall eyewright >/dev/null 2>&1; export PATH=$HOME/.local/bin:$PATH; clear"
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

# 1. It knows: one call, confident accept
Type `eyewright gate --config docs/demo/gate.json --state "412 tests pass; CI green; 4-line diff; 2 approvals." --question "Safe to merge?"`
Enter
Wait+Screen /"accept"/
Sleep 2500ms

# 2. It doesn't know: primary is unsure, so a second eye is consulted
Type `eyewright gate --config docs/demo/gate.json --state "Adds a retry loop around the API call; tests pass; no test for the retry path." --question "Safe to merge?"`
Enter
Wait+Screen /"review-no-signal"/
Sleep 2500ms

# 3. Any typed decision: not just yes/no
Type `eyewright ask --config docs/demo/gate.json --state "p95 latency = 480 ms; the budget is 200 ms." --question "Which action?" --choices '{"optimize":"optimize the hot path","review":"gather more data","ship":"ship anyway"}'`
Enter
Wait+Screen /"confidence"/
Sleep 2500ms

# Closer
Type `clear; echo; echo '  pip install eyewright'; echo '  github.com/eyewright/eyewright'; echo`
Enter
Sleep 2500ms
