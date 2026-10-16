# Extra seeds for the M2 flagship run (repetition d=3, circuit level, p=0.01).
# Mirrors scripts/t9_feature_ablation.py --seed-offset: training.seed and every
# split seed are shifted, the experiment sampling seed is untouched.
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$log = 'results\logs\m2_headline_seeds.log'

function Write-Log([string]$message) {
    "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message |
        Add-Content -Path $log -Encoding utf8
}

Write-Log "m2 headline seeds start (pid $PID)"
& $py scripts\m2_headline_multiseed.py --write-configs 2>&1 | Out-File -FilePath $log -Append -Encoding utf8

foreach ($offset in 10, 20) {
    $tag = "m2_learned_basis_repetition_circuit_level_d3_s$offset"
    $out = "results\m2\${tag}__d3__circuit_level__p0p01"
    if (Test-Path (Join-Path $out 'results.json')) { Write-Log "skip offset $offset (exists)"; continue }
    Write-Log "offset $offset start -> $out"
    & $py -m graph_qec.m2 --config ("configs\m2_headline_seed{0}.json" -f $offset) --output-dir results\m2 2>&1 |
        Out-File -FilePath $log -Append -Encoding utf8
    Write-Log "offset $offset exit=$LASTEXITCODE"
}
Write-Log "m2 headline seeds finished"
