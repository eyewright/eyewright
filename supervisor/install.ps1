# Register/uninstall the eyewright tray at logon (per-user Startup folder, no admin).
#   pwsh -File supervisor/install.ps1 -Tray
#   pwsh -File supervisor/install.ps1 -Tray -Uninstall
#   pwsh -File supervisor/install.ps1            # svcwatch only, no tray
#
# The tray itself ships in the package (`pip install 'eyewright[tray]'`,
# `eyewright-tray`); this script only wires autostart for a source checkout and
# points it at the repo so `examples/gate.json` resolves.
param([switch]$Uninstall, [switch]$Tray)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here
$stateDir = Join-Path $env:LOCALAPPDATA 'eyewright'
$startup = [Environment]::GetFolderPath('Startup')
$cmdLauncher = Join-Path $startup 'eyewright-svcwatch.cmd'
$lnkLauncher = Join-Path $startup 'eyewright tray.lnk'

function Stop-FromPidFile($name) {
    $f = Join-Path $stateDir $name
    if (Test-Path $f) {
        $old = Get-Content $f -ErrorAction SilentlyContinue
        if ($old) { Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue }
        Remove-Item $f -ErrorAction SilentlyContinue
    }
}

if ($Uninstall) {
    Remove-Item $cmdLauncher, $lnkLauncher -ErrorAction SilentlyContinue
    Stop-FromPidFile 'tray.pid'
    Stop-FromPidFile 'svcwatch.pid'
    Write-Output "uninstalled (removed $cmdLauncher and $lnkLauncher)"
    return
}

# Prefer the venv's windowed entry point: it is a GUI-subsystem exe, so logon
# leaves no terminal behind. Fall back to the module form when the entry point
# is missing - `uv sync` cannot rewrite Scripts/*.exe while an MCP server is
# running from it.
$trayExe = Join-Path $repo '.venv\Scripts\eyewright-tray.exe'
$svcExe = Join-Path $repo '.venv\Scripts\eyewright-svcwatch.exe'
$py = Join-Path $repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path $trayExe)) {
    $trayExe = $py
    $trayArgs = '-m eyewright.tray'
    Write-Warning "no eyewright-tray.exe yet - using 'pythonw -m eyewright.tray' (run 'uv sync' with no MCP server running to get the windowed entry point)"
} else {
    $trayArgs = ''
}
if (-not (Test-Path $svcExe)) {
    $svcExe = $py
    $svcArgs = '-m eyewright.svcwatch'
} else {
    $svcArgs = ''
}

if ($Tray) {
    # One windowless process: tray + supervisor loop + Decide dialog.
    # A .lnk (not a .cmd) means no cmd.exe flash at logon.
    Stop-FromPidFile 'svcwatch.pid'
    Remove-Item $cmdLauncher -ErrorAction SilentlyContinue
    $sh = New-Object -ComObject WScript.Shell
    $l = $sh.CreateShortcut($lnkLauncher)
    $l.TargetPath = $trayExe
    $l.Arguments = $trayArgs
    $l.WorkingDirectory = $repo
    $l.Description = 'eyewright tray (supervisor + Decide)'
    $l.Save()
    Write-Output "installed startup shortcut: $lnkLauncher"
    Start-Process -FilePath $trayExe -ArgumentList $trayArgs -WorkingDirectory $repo -WindowStyle Hidden
    Write-Output "started eyewright tray now"
    return
}

$cmd = @(
    '@echo off',
    ('start "" "{0}" {1}' -f $svcExe, $svcArgs)
) -join "`r`n"
Set-Content -Path $cmdLauncher -Value $cmd -Encoding ASCII
Write-Output "installed startup launcher: $cmdLauncher"
Start-Process -FilePath $svcExe -ArgumentList $svcArgs -WorkingDirectory $repo -WindowStyle Hidden
Write-Output "started svcwatch now"
