# Register/uninstall the eyewright service supervisor to start at logon.
#   pwsh -File supervisor/install.ps1
#   pwsh -File supervisor/install.ps1 -Uninstall
#
# Uses the per-user Startup folder (no admin required). If you prefer a scheduled
# task, create it elevated:
#   schtasks /Create /TN eyewright-svcwatch /SC ONLOGON /RL LIMITED /F `
#     /TR "\"C:\path\pythonw.exe\" \"C:\path\supervisor\svcwatch.py\""
param([switch]$Uninstall, [switch]$Tray)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here 'svcwatch.py'
$trayScript = Join-Path $here 'tray.py'
$startup = [Environment]::GetFolderPath('Startup')
$cmdLauncher = Join-Path $startup 'eyewright-svcwatch.cmd'
$lnkLauncher = Join-Path $startup 'eyewright tray.lnk'

if ($Uninstall) {
    Remove-Item $cmdLauncher, $lnkLauncher -ErrorAction SilentlyContinue
    foreach ($pidFile in @((Join-Path $here 'svcwatch.pid'), (Join-Path $here 'tray.pid'))) {
        if (Test-Path $pidFile) {
            $old = Get-Content $pidFile -ErrorAction SilentlyContinue
            if ($old) { Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue }
        }
    }
    Write-Output "uninstalled (removed $cmdLauncher and $lnkLauncher)"
    return
}

$py = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python.exe).Source }

if ($Tray) {
    # One windowless process: tray + supervisor loop + Decide dialog.
    # A .lnk (not a .cmd) means no cmd.exe flash at logon.
    # Must use the project venv: pystray/pillow/eyewright live there, not in PATH python.
    # uv's venv pythonw is a copy of python.exe (console subsystem), so it opens a
    # terminal at logon. Prefer the base GUI pythonw; tray.py adds the venv's
    # site-packages to sys.path, so pystray/Pillow still resolve.
    $venvPy = Join-Path (Split-Path -Parent $here) '.venv\Scripts\pythonw.exe'
    $basePy = Get-ChildItem -Path (Join-Path $env:APPDATA 'uv\python\cpython-3.12-*\pythonw.exe') -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($basePy) { $py = $basePy.FullName } elseif (Test-Path $venvPy) { $py = $venvPy }
    Remove-Item $cmdLauncher -ErrorAction SilentlyContinue
    $svcPid = Join-Path $here 'svcwatch.pid'
    if (Test-Path $svcPid) {
        $old = Get-Content $svcPid -ErrorAction SilentlyContinue
        if ($old) { Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue }
        Remove-Item $svcPid -ErrorAction SilentlyContinue
    }
    $sh = New-Object -ComObject WScript.Shell
    $l = $sh.CreateShortcut($lnkLauncher)
    $l.TargetPath = $py
    $l.Arguments = '"' + $trayScript + '"'
    $l.WorkingDirectory = $here
    $l.Description = 'eyewright tray (supervisor + Decide)'
    $l.Save()
    Write-Output "installed startup shortcut: $lnkLauncher  (python: $py)"
    Start-Process -FilePath $py -ArgumentList @($trayScript) -WorkingDirectory $here -WindowStyle Hidden
    Write-Output "started eyewright tray now"
    return
}

$cmd = @(
    '@echo off',
    ('start "" "{0}" "{1}"' -f $py, $script)
) -join "`r`n"
Set-Content -Path $cmdLauncher -Value $cmd -Encoding ASCII
Write-Output "installed startup launcher: $cmdLauncher  (python: $py)"

# start it now (detached, no console)
Start-Process -FilePath $py -ArgumentList @($script) -WorkingDirectory $here -WindowStyle Hidden
Write-Output "started svcwatch now"