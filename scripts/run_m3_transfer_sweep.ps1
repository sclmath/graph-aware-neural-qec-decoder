$ErrorActionPreference = 'Stop'
Set-Location 'D:\work2026\BuChou\Projects_BuChou\01_graph_aware_neural_qec_decoder'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'results\m3\logs' | Out-Null

$d3cfg = 'configs\m3_learned_basis_repetition_circuit_level_d3.json'
$d3ckpt = 'results\m3\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt'
$d3common = @('-m','graph_qec.m3','--config',$d3cfg,'--checkpoint',$d3ckpt,'--output-dir','results\m3',
  '--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--timed-runs','1','--test-seeds','301','302','--test-shots','16384')

$jobs = @(
  @{ name='noise_p0p003'; extra=@('--target-physical-error-rate','0.003') },
  @{ name='noise_p0p005'; extra=@('--target-physical-error-rate','0.005') },
  @{ name='noise_p0p008'; extra=@('--target-physical-error-rate','0.008') },
  @{ name='noise_p0p020'; extra=@('--target-physical-error-rate','0.020') },
  @{ name='distance_d5';  extra=@('--target-distance','5','--target-rounds','5') }
)
foreach ($job in $jobs) {
  Start-Process -FilePath $py -ArgumentList ($d3common + $job.extra) -WorkingDirectory $PWD `
    -RedirectStandardOutput "results\m3\logs\$($job.name).out.log" `
    -RedirectStandardError  "results\m3\logs\$($job.name).err.log" -WindowStyle Hidden
}

$d5common = @('-m','graph_qec.m3','--config','configs\m2_learned_basis_repetition_circuit_level_d5.json',
  '--checkpoint','results\m2\m2_learned_basis_repetition_circuit_level_d5__d5__circuit_level__p0p01__train_only\model_state.pt',
  '--output-dir','results\m3','--tag','m2_learned_basis_repetition_circuit_level_d5_eval',
  '--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--timed-runs','1')
Start-Process -FilePath $py -ArgumentList $d5common -WorkingDirectory $PWD `
  -RedirectStandardOutput 'results\m3\logs\m2_d5_eval.out.log' `
  -RedirectStandardError  'results\m3\logs\m2_d5_eval.err.log' -WindowStyle Hidden

Write-Output "launched 6 background transfer jobs"
Get-Date -Format HH:mm:ss
