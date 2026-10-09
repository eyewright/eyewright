# Register/uninstall the eyewright service supervisor to start at logon.
#   pwsh -File supervisor/install.ps1
#   pwsh -File supervisor/install.ps1 -Uninstall
#
# Uses the per-user Startup folder (no admin required). If you prefer a scheduled
# task, create it elevated:
#   schtasks /Create /TN eyewright-svcwatch /SC ONLOGON /RL LIMITED /F `
#     /TR "\"C:\path\pythonw.exe\" \"C:\path\supervisor\svcwatch.py\""
param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here 'svcwatch.py'
$startup = [Environment]::GetFolderPath('Startup')
$launcher = Join-Path $startup 'eyewright-svcwatch.cmd'

if ($Uninstall) {
    Remove-Item $launcher -ErrorAction SilentlyContinue
    $pidFile = Join-Path $here 'svcwatch.pid'
    if (Test-Path $pidFile) {
        $old = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($old) { Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue }
    }
    Write-Output "uninstalled (removed $launcher)"
    return
}

$py = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python.exe).Source }

$cmd = @(
    '@echo off',
    ('start "" "{0}" "{1}"' -f $py, $script)
) -join "`r`n"
Set-Content -Path $launcher -Value $cmd -Encoding ASCII
Write-Output "installed startup launcher: $launcher  (python: $py)"

# start it now (detached, no console)
Start-Process -FilePath $py -ArgumentList @($script) -WorkingDirectory $here -WindowStyle Hidden
Write-Output "started svcwatch now"