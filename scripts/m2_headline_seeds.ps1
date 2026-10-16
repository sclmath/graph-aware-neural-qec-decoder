# Seed-offset runs for an M2/M4 config, so the flagship tables get error bars.
# Pair with scripts/m2_headline_multiseed.py (--write-configs / --aggregate).
param(
    [Parameter(Mandatory = $true)][string]$BaseConfig,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int[]]$Offsets = @(10, 20)
)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$log = 'results\logs\m2_seed_runs.log'

function Write-Log([string]$message) {
    "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message |
        Add-Content -Path $log -Encoding utf8
}

$base = (Get-Content $BaseConfig -Raw -Encoding UTF8 | ConvertFrom-Json).name
Write-Log "m2 seed runs start (pid $PID) base=$base out=$OutDir"

foreach ($offset in $Offsets) {
    $name = "{0}_s{1}" -f $base, $offset
    $existing = Get-ChildItem -Path $OutDir -Directory -Filter "${name}__*" -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'results.json') }
    if ($existing) { Write-Log "skip $name (exists: $($existing[0].Name))"; continue }

    $config = "configs\{0}.json" -f $name
    if (-not (Test-Path $config)) { Write-Log "missing config $config (run --write-configs first)"; continue }
    Write-Log "$name start"
    & $py -m graph_qec.m2 --config $config --output-dir $OutDir 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Write-Log "$name exit=$LASTEXITCODE"
}
Write-Log "m2 seed runs finished"
