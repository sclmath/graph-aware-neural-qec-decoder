param(
    [Parameter(Mandatory = $true)][ValidateSet('A', 'B', 'C', 'D', 'F')][string]$Chain
)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$log = "results\logs\session3_chain$Chain.log"

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Invoke-RepetitionStudy([int]$offset) {
    # Independent seed for the T8 repetition d=3 OSD-CS study: reuse the M2 run
    # that was trained with the same seed shift (model + splits both differ from
    # the original study), and evaluate on that run's own test split.
    $run = "results\m2\m2_learned_basis_repetition_circuit_level_d3_s{0}__d3__circuit_level__p0p01" -f $offset
    $out = "results\t8\repetition_d3_seed{0}" -f $offset
    if (Test-Path (Join-Path $out 'STUDY.md')) { Write-Log "skip t8 repetition offset $offset (exists)"; return }
    if (-not (Test-Path (Join-Path $run 'model_state.pt'))) { Write-Log "missing checkpoint for offset $offset ($run)"; return }
    Write-Log "t8 repetition offset $offset start"
    & $py scripts\t8_osd_cs_study.py --config (Join-Path $run 'config.json') --checkpoint (Join-Path $run 'model_state.pt') --sweeps 0 4 --output-dir $out 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Write-Log "t8 repetition offset $offset exit=$LASTEXITCODE"
}

function Invoke-Probe([string]$p, [int]$offset) {
    $dir = "results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__$p"
    $out = "results\t8\d7_{0}_probe_s{1}" -f $p, $offset
    if (Test-Path (Join-Path $out 'STUDY.md')) { Write-Log "skip probe $p offset $offset (exists)"; return }
    Write-Log "probe $p offset $offset start"
    & $py scripts\t8_osd_cs_study.py --config (Join-Path $dir 'config.json') --checkpoint (Join-Path $dir 'model_state.pt') --sweeps 0 4 --test-shots 1024 --seed-offset $offset --output-dir $out 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Write-Log "probe $p offset $offset exit=$LASTEXITCODE"
}

function Invoke-T9([int]$offset, [string[]]$arms, [switch]$Merge) {
    $out = "results\t9\repetition_d3_seed{0}" -f $offset
    $extra = @()
    if ($Merge) { $extra += '--merge' }
    Write-Log "t9 repetition offset $offset arms=$($arms -join ',') merge=$Merge start"
    & $py scripts\t9_feature_ablation.py --config configs\m2_learned_basis_repetition_circuit_level_d3.json --output-dir $out --arms @arms --torch-threads 2 --seed-offset $offset @extra 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Write-Log "t9 repetition offset $offset exit=$LASTEXITCODE"
}

Write-Log "chain $Chain start (pid $PID)"
if ($Chain -eq 'A') {
    foreach ($p in 'p0p003', 'p0p005', 'p0p008') { Invoke-Probe $p 20 }
} elseif ($Chain -eq 'B') {
    Invoke-T9 10 @('all', 'no_variable_geometry', 'prior_only')
    Invoke-T9 20 @('all', 'no_variable_geometry', 'prior_only')
    foreach ($p in 'p0p003', 'p0p005', 'p0p008') { Invoke-Probe $p 10 }
} elseif ($Chain -eq 'C') {
    # Complete the remaining ablation arms for seeds 10/20 and merge them into
    # the ablation.json already written by chain B.
    foreach ($off in 10, 20) {
        Invoke-T9 $off @('no_check_features', 'no_check_geometry', 'no_edge_degree') -Merge
    }
} elseif ($Chain -eq 'F') {
    # T8 repetition d=3 study, independent seeds (needs the M2 headline seeds).
    foreach ($off in 10, 20) { Invoke-RepetitionStudy $off }
} else {
    # T6 residual noise-rate points, in value order (the grid skips finished
    # points itself, so this is resumable).  Budget 8 h: covers d=7 p=0.008 x2
    # seeds, d=5 p=0.01 x3 seeds and d=7 p=0.01 x3 seeds, and stops before the
    # low-value p=0.002 block.
    Write-Log "chain D: T6 residual grid, budget 480 min"
    & $py scripts\t6_surface_grid.py --budget-minutes 480 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Write-Log "chain D exit=$LASTEXITCODE"
}
Write-Log "chain $Chain finished"
