$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$log = 'results\logs\t18_rerun.log'
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] T18 baseline rerun start" | Out-File -FilePath $log -Encoding utf8

& $py -m graph_qec.m1 --config `
    configs\m1_repetition_circuit_level.json configs\m1_repetition_circuit_level_p0p001.json `
    configs\m1_repetition_circuit_level_p0p002.json configs\m1_repetition_code_capacity.json `
    configs\m1_repetition_code_capacity_p0p001.json configs\m1_repetition_code_capacity_p0p002.json `
    --output-dir results\m1 *>> $log
"[$(Get-Date -Format 'HH:mm:ss')] M1 done" | Out-File -FilePath $log -Append -Encoding utf8

& $py scripts\m4_surface_sweep.py --distances 3 --noise-models circuit_level `
    --rates 0.003 0.005 0.008 --shots 8192 --output-dir results\m4 *>> $log
"[$(Get-Date -Format 'HH:mm:ss')] sweep d3 circuit-level done" | Out-File -FilePath $log -Append -Encoding utf8

& $py scripts\m4_surface_sweep.py --distances 3 5 --noise-models code_capacity `
    --rates 0.01 0.02 0.05 --shots 16384 --output-dir results\m4 *>> $log
"[$(Get-Date -Format 'HH:mm:ss')] sweep code-capacity done" | Out-File -FilePath $log -Append -Encoding utf8

& $py scripts\m4_surface_sweep.py --distances 5 --noise-models circuit_level `
    --rates 0.005 --shots 4096 --output-dir results\m4 *>> $log
"[$(Get-Date -Format 'HH:mm:ss')] T18 baseline rerun finished" | Out-File -FilePath $log -Append -Encoding utf8
