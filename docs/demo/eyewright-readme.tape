Output "docs/demo/eyewright-readme.mp4"
Set FontSize 15
Set Width 1100
Set Height 560
Set Padding 24
Set Theme "Dracula"
Set Shell "bash"
Set TypingSpeed 5ms

# README teaser: one beat only. Cropped to the content box after render (see
# render.ps1) so it reads as a tight strip instead of a mostly-empty terminal.
# The state lives in a variable so the command does not wrap at this width.
Hide
Type "uv tool uninstall eyewright >/dev/null 2>&1; export PATH=$HOME/.local/bin:$PATH; S1='Done: all requested changes are implemented, tests pass, and the PR is merged.'; Q='Is the task done?'; clear; echo; echo '  eyewright - typed decisions from small local models'; echo"
Enter
Sleep 600ms
Show
Sleep 300ms

Type "uv tool install eyewright"
Enter
Sleep 2500ms

Type `eyewright gate --config docs/demo/gate.json --state "$S1" --question "$Q"`
Enter
Wait+Screen /"consensus-accept"/
Sleep 4500ms
