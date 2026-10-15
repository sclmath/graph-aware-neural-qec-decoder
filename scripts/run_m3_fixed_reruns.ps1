$ErrorActionPreference = 'Stop'
Set-Location 'D:\work2026\BuChou\Projects_BuChou\01_graph_aware_neural_qec_decoder'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'results\m3_fixed\logs' | Out-Null

$cfg = 'configs\m3_learned_basis_repetition_circuit_level_d3.json'
$ckpt = 'results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt'
$common = @('-m','graph_qec.m3','--config',$cfg,'--checkpoint',$ckpt,'--output-dir','results\m3_fixed',
  '--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--timed-runs','1','--test-seeds','301','302','--test-shots','16384')

$jobs = @(
  @{ name='noise_p0p003'; extra=@('--target-physical-error-rate','0.003') },
  @{ name='noise_p0p005'; extra=@('--target-physical-error-rate','0.005') },
  @{ name='noise_p0p008'; extra=@('--target-physical-error-rate','0.008') },
  @{ name='noise_p0p020'; extra=@('--target-physical-error-rate','0.020') },
  @{ name='distance_d5';  extra=@('--target-distance','5','--target-rounds','5','--test-shots','8192','--test-seeds','301') }
)
foreach ($job in $jobs) {
  Start-Process -FilePath $py -ArgumentList ($common + $job.extra) -WorkingDirectory $PWD `
    -RedirectStandardOutput "results\m3_fixed\logs\$($job.name).out.log" `
    -RedirectStandardError  "results\m3_fixed\logs\$($job.name).err.log" -WindowStyle Hidden
}
$base = @('scripts\m3_strength_recalibration.py','--config',$cfg,'--checkpoint',$ckpt,'--output-dir')
Start-Process -FilePath $py -ArgumentList ($base + @('results\m3_fixed\recal_lowp','--targets','0.003','0.005')) -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput 'results\m3_fixed\logs\recal_lowp.out.log' -RedirectStandardError 'results\m3_fixed\logs\recal_lowp.err.log'
Start-Process -FilePath $py -ArgumentList ($base + @('results\m3_fixed\recal_highp','--targets','0.008','0.02')) -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput 'results\m3_fixed\logs\recal_highp.out.log' -RedirectStandardError 'results\m3_fixed\logs\recal_highp.err.log'
Start-Process -FilePath $py -ArgumentList @('scripts\m3_failure_analysis.py','--config',$cfg,'--checkpoint',$ckpt,'--output','results\m3_fixed\failure_analysis.json','--markdown','results\m3_fixed\FAILURE_ANALYSIS.md') -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput 'results\m3_fixed\logs\failure.out.log' -RedirectStandardError 'results\m3_fixed\logs\failure.err.log'
Write-Output "launched 8 corrected re-runs"
Get-Date -Format HH:mm:ss
