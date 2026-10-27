Output "docs/demo/eyewright-demo.mp4"
Set FontSize 18
Set Width 2560
Set Height 1440
Set Padding 28
Set Theme "Dracula"
Set Shell "bash"
Set TypingSpeed 15ms

# Hidden setup: PATH for the ttyd shell, and a fresh install line on camera.
Hide
Type "uv tool uninstall eyewright >/dev/null 2>&1; export PATH=$HOME/.local/bin:$PATH; clear"
Enter
Sleep 500ms
Show

# Title
Type "clear; echo 'eyewright - typed decisions for agent loops'"
Enter
Sleep 2s

# Install
Type "uv tool install eyewright"
Enter
Sleep 4s

# Gate: accept / reject / review
Type `eyewright gate --config docs/demo/gate.json --state "login flow changed; unit tests pass, no integration test" --question "Is this safe to merge?"`
Enter
Wait+Screen /"decision"/
Sleep 3s

# One call, any typed decision
Type `eyewright ask --config docs/demo/gate.json --state "p95 latency = 480 ms; the budget is 200 ms" --question "Which action?" --choices '{"optimize":"optimize the hot path","review":"gather more data","ship":"ship anyway"}'`
Enter
Wait+Screen /"confidence"/
Sleep 3s

# Closer
Type "clear; echo 'pip install eyewright'; echo 'github.com/eyewright/eyewright'"
Enter
Sleep 3s
