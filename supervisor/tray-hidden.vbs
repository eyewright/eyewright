' Start the eyewright tray with no console window.
'
' A GUI-subsystem entry point is not enough: uv's launcher re-execs the venv's
' console-subsystem pythonw, which allocates a terminal. wscript is GUI-subsystem and
' window style 0 hides the console it creates, so the whole chain stays invisible.
'
' The tray is started detached (bWait = False); wscript exits immediately.

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

supervisor = fso.GetParentFolderName(WScript.ScriptFullName)
repo = fso.GetParentFolderName(supervisor)

' Run pythonw directly, not the eyewright-tray.exe trampoline: the trampoline starts
' pythonw itself without inheriting the hidden window, so the console comes back.
' Whoever creates the first console must be the process started with style 0.
exe = repo & "\.venv\Scripts\pythonw.exe"

sh.CurrentDirectory = repo
sh.Run """" & exe & """ -m eyewright.tray", 0, False
