$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot.Replace('\scripts', '')
$py = Join-Path $PWD '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'results\m3\logs' | Out-Null

$cfg = 'configs\m3_learned_basis_repetition_circuit_level_d3.json'
$ckpt = 'results\m3\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt'
$common = @('-m','graph_qec.m3','--config',$cfg,'--checkpoint',$ckpt,'--output-dir','results\m3',
  '--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--timed-runs','1','--test-seeds','301','302','--test-shots','16384')

# 1) 噪声外推（d=3）与跨码距迁移（d=3 -> d=5）
$jobs = @(
  @{ name='noise_p0p003'; extra=@('--target-physical-error-rate','0.003') },
  @{ name='noise_p0p005'; extra=@('--target-physical-error-rate','0.005') },
  @{ name='noise_p0p008'; extra=@('--target-physical-error-rate','0.008') },
  @{ name='noise_p0p020'; extra=@('--target-physical-error-rate','0.020') },
  @{ name='distance_d5';  extra=@('--target-distance','5','--target-rounds','5','--test-shots','8192','--test-seeds','301') }
)
foreach ($job in $jobs) {
  Start-Process -FilePath $py -ArgumentList ($common + $job.extra) -WorkingDirectory $PWD `
    -RedirectStandardOutput "results\m3\logs\$($job.name).out.log" `
    -RedirectStandardError  "results\m3\logs\$($job.name).err.log" -WindowStyle Hidden
}

# 2) repetition d=5 同分布评测（用 M2 保存的 d=5 checkpoint）
Start-Process -FilePath $py -ArgumentList @('-m','graph_qec.m3',
  '--config','configs\m2_learned_basis_repetition_circuit_level_d5.json',
  '--checkpoint','results\m2\m2_learned_basis_repetition_circuit_level_d5__d5__circuit_level__p0p01__train_only\model_state.pt',
  '--output-dir','results\m3','--tag','m2_d5_eval',
  '--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--timed-runs','1') -WorkingDirectory $PWD `
  -RedirectStandardOutput 'results\m3\logs\m2_d5_eval.out.log' `
  -RedirectStandardError  'results\m3\logs\m2_d5_eval.err.log' -WindowStyle Hidden

# 3) 先验强度重标定与失效归因
$base = @('scripts\m3_strength_recalibration.py','--config',$cfg,'--checkpoint',$ckpt,'--output-dir')
Start-Process -FilePath $py -ArgumentList ($base + @('results\m3\recal_lowp','--targets','0.003','0.005')) -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput 'results\m3\logs\recal_lowp.out.log' -RedirectStandardError 'results\m3\logs\recal_lowp.err.log'
Start-Process -FilePath $py -ArgumentList ($base + @('results\m3\recal_highp','--targets','0.008','0.02')) -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput 'results\m3\logs\recal_highp.out.log' -RedirectStandardError 'results\m3\logs\recal_highp.err.log'
Start-Process -FilePath $py -ArgumentList @('scripts\m3_failure_analysis.py','--config',$cfg,'--checkpoint',$ckpt,'--output','results\m3\failure_analysis.json','--markdown','results\m3\FAILURE_ANALYSIS.md') -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput 'results\m3\logs\failure.out.log' -RedirectStandardError 'results\m3\logs\failure.err.log'

Write-Output "launched 8 background M3 jobs"
Get-Date -Format HH:mm:ss