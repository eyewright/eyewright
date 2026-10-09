# Calibration pipeline: train inference for the LLM consults + holdout main/consults.
# Usage: pwsh -File run_calibration_pipeline.ps1
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$log = "calibration-$(Get-Date -Format yyyy-MM-dd).log"
$key = "C:\Users\kcpat\OneDrive\Documents\Default Project\model-lab\decision-bench\.laya-api-key"

function Log([string]$m) {
    $l = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Output $l
    Add-Content -Path $log -Value $l
}

$env:OPENROUTER_API_KEY = & python -c "import json,os;print(json.load(open(os.path.expanduser('~/.local/share/opencode/auth.json'),encoding='utf-8'))['openrouter']['key'])"

Log 'build train cases + fit/holdout split'
& uv run python build_train_cases.py *>> $log
Log "build exit=$LASTEXITCODE"

Log 'jev-1.13 on all 1800 train (native decisions, zdr)'
& uv run python run_generative_noul.py --engine openrouter-decisions --model typesafe/jev-1.13 `
    --cases cases-train.jsonl --out responses-train-jev-113.jsonl --zdr --workers 8 *>> $log
Log "jev-113 exit=$LASTEXITCODE"

Log 'laya-td on 600 holdout (native http)'
& uv run python run_native_noul.py --type http --url http://127.0.0.1:8000/v1/systemone `
    --key-file $key --cases cases-train-holdout.jsonl --out responses-holdout-laya-td.jsonl --workers 4 *>> $log
Log "laya exit=$LASTEXITCODE"

Log 'tev1:4b on 600 holdout (ollama)'
& uv run python run_native_noul.py --type ollama --model tev1:4b `
    --cases cases-train-holdout.jsonl --out responses-holdout-tev1.jsonl --workers 4 *>> $log
Log "tev1 exit=$LASTEXITCODE"

Log 'jev-router on all 1800 train (openrouter chat)'
& uv run python run_generative_noul.py --engine openrouter --model typesafe/jev-router `
    --cases cases-train.jsonl --out responses-train-jev-router.jsonl --workers 8 *>> $log
Log "router exit=$LASTEXITCODE"

Log 'gemma4:12b on all 1800 train (ollama)'
& uv run python run_generative_noul.py --engine ollama --model gemma4:12b `
    --cases cases-train.jsonl --out responses-train-gemma12b.jsonl --workers 4 *>> $log
Log "gemma exit=$LASTEXITCODE"

Log 'INFERENCE COMPLETE'