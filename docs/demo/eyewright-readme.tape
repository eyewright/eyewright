Output "docs/demo/eyewright-readme.mp4"
Set FontSize 15
Set Width 1100
Set Height 560
Set Padding 24
Set Theme "Dracula"
Set Shell "bash"
Set TypingSpeed 10ms

# README teaser: four beats, one per decision kind, so the loop shows
# accept -> send back -> refuse -> escalate. Cropped to the content box after
# render (see render.ps1). States and questions live in variables so the
# commands on screen stay short enough not to wrap at this width.
Hide
Type "uv tool uninstall eyewright >/dev/null 2>&1; export PATH=$HOME/.local/bin:$PATH; Q='Is the task done?'; S1='Done: all requested changes are implemented, tests pass, and the PR is merged.'; S2='Adds a retry loop around the API call; tests pass; no test for the retry path.'; S3='Drops a column that three services still read; the backfill has not run.'; Q3='Is this migration safe?'; S4='Merged and deployed to staging; tests green; no alerts in 24h.'; Q4='Safe to merge?'; clear; echo; echo '  eyewright - typed decisions from small local models'; echo"
Enter
Sleep 600ms
Show
Sleep 300ms

# 1. accept: the committee carries a wavering primary (0.67 -> both agree)
Type "uv tool install eyewright"
Enter
Sleep 2500ms

Type `eyewright gate --config docs/demo/gate.json --state "$S1" --question "$Q"`
Enter
Wait+Screen /"p_done"/
Sleep 2200ms

# 2. send back: clearly incomplete, no consult spent
Type `eyewright gate --config docs/demo/gate.json --state "$S2" --question "$Q"`
Enter
Wait+Screen /"p_done"/
Sleep 2000ms

# 3. refuse: both consults confident that it is unsafe
Type `eyewright gate --config docs/demo/gate.json --state "$S3" --question "$Q3"`
Enter
Wait+Screen /"p_done"/
Sleep 2200ms

# 4. escalate: the consults disagree, so the caller gathers evidence
Type `eyewright gate --config docs/demo/gate.json --state "$S4" --question "$Q4"`
Enter
Wait+Screen /"p_done"/
Sleep 3500ms
