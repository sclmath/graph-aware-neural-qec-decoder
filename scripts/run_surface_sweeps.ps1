$py = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $py scripts\m4_surface_sweep.py --distances 3 --noise-models circuit_level --rates 0.003 0.005 0.008 --shots 8192 --output-dir results\m4 *>> results\logs\sweep_cl3.log
& $py scripts\m4_surface_sweep.py --distances 5 --noise-models circuit_level --rates 0.005 --shots 4096 --output-dir results\m4 *>> results\logs\sweep_cl5.log
"[$(Get-Date -Format HH:mm:ss)] sweeps done" | Out-File -FilePath results\logs\_sweeps_done.txt -Encoding utf8
