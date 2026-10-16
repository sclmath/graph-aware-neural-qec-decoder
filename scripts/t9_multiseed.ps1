$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$cfg = 'results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json'
$log = 'results\logs\t9_multiseed.log'
"[$(Get-Date -Format 'HH:mm:ss')] T9 multi-seed confirmation start" | Out-File -FilePath $log -Encoding utf8
foreach ($offset in 10, 20) {
    "[$(Get-Date -Format 'HH:mm:ss')] seed offset $offset" | Out-File -FilePath $log -Append -Encoding utf8
    & $py scripts\t9_feature_ablation.py --config $cfg --output-dir ("results\t9\surface_d3_seed{0}" -f $offset) --arms all no_variable_geometry --torch-threads 3 --seed-offset $offset *>> $log
    "[$(Get-Date -Format 'HH:mm:ss')] offset $offset exit=$LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
}
"[$(Get-Date -Format 'HH:mm:ss')] T9 multi-seed confirmation finished" | Out-File -FilePath $log -Append -Encoding utf8
