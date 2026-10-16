$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$log = 'results\logs\t8_d7_probes.log'
"[$(Get-Date -Format 'HH:mm:ss')] d=7 OSD-CS probes start" | Out-File -FilePath $log -Encoding utf8
foreach ($p in 'p0p003', 'p0p008') {
    $dir = "results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__$p"
    "[$(Get-Date -Format 'HH:mm:ss')] probe $p" | Out-File -FilePath $log -Append -Encoding utf8
    & $py scripts\t8_osd_cs_study.py --config (Join-Path $dir 'config.json') --checkpoint (Join-Path $dir 'model_state.pt') --sweeps 0 4 --test-shots 1024 --output-dir ("results\t8\d7_" + $p + "_probe") *>> $log
    "[$(Get-Date -Format 'HH:mm:ss')] $p exit=$LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
}
"[$(Get-Date -Format 'HH:mm:ss')] d=7 OSD-CS probes finished" | Out-File -FilePath $log -Append -Encoding utf8
