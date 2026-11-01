# Screening pipeline (same protocol as the three-eye gate proxy).
# Runs the 2026-10-09 roster sequentially, then the comparison.
# Usage: pwsh -File run_screening.ps1
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$log = "screening-$(Get-Date -Format yyyy-MM-dd).log"

function Log([string]$m) {
    $l = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Output $l
    Add-Content -Path $log -Value $l
}

if (-not $env:OPENROUTER_API_KEY) { throw 'set OPENROUTER_API_KEY before running this pipeline' }

Log 'run: typesafe/jev-router (openrouter, 8 workers)'
& uv run python run_generative_noul.py --engine openrouter --model typesafe/jev-router `
    --out responses-jev-router.jsonl --workers 8 *>> $log
Log "jev-router exit=$LASTEXITCODE"

Log 'run: jevify-gemma4-26b-a4b (ollama)'
& uv run python run_generative_noul.py --engine ollama --model jevify-gemma4-26b-a4b:latest `
    --out responses-jevify-gemma.jsonl *>> $log
Log "jevify exit=$LASTEXITCODE"

Log 'run: gemma4:12b (ollama)'
& uv run python run_generative_noul.py --engine ollama --model gemma4:12b `
    --out responses-gemma12b.jsonl *>> $log
Log "gemma exit=$LASTEXITCODE"

Log 'compare -> SCREENING-2026-10-09.md'
& uv run python compare_consults.py `
    --extra "jev-router=responses-jev-router.jsonl" `
    --extra "jevify-gemma=responses-jevify-gemma.jsonl" `
    --extra "gemma4:12b=responses-gemma12b.jsonl" `
    --out SCREENING-2026-10-09.md *>> $log
Log "compare exit=$LASTEXITCODE"
Log 'SCREENING COMPLETE'