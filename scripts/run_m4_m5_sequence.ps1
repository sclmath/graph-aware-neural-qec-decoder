$ErrorActionPreference = 'Continue'
Set-Location 'D:\work2026\BuChou\Projects_BuChou\01_graph_aware_neural_qec_decoder'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'results\logs' | Out-Null

$surf_cc_ckpt = 'results\m4_surface_cc\m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05\model_state.pt'
$hgp_rep_ckpt = 'results\m4_hgp\m4_hgp_rep3x3_code_capacity_p0p05__d3__code_capacity__p0p05\model_state.pt'

$steps = @(
  @{ name = 'm4_surface_code_capacity'; args = @('-m','graph_qec.m2','--config','configs\m4_rotated_surface_code_code_capacity_d3.json','--output-dir','results\m4_surface_cc') },
  @{ name = 'm4_hgp_hamming';         args = @('-m','graph_qec.m4','--config','configs\m4_hgp_hamming7x7_code_capacity_p0p05.json','--output-dir','results\m4_hgp') },
  @{ name = 'surface_cc_d3_to_d5';    args = @('-m','graph_qec.m3','--config','configs\m4_rotated_surface_code_code_capacity_d3.json','--checkpoint',$surf_cc_ckpt,'--output-dir','results\m4_surface_cc','--target-distance','5','--target-rounds','5','--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--test-shots','8192','--test-seeds','301','302','--timed-runs','1') },
  @{ name = 'hgp_rep3_to_hamming';    args = @('scripts\m4_transfer.py','--source-config','configs\m4_hgp_rep3x3_code_capacity_p0p05.json','--target-config','configs\m4_hgp_hamming7x7_code_capacity_p0p05.json','--checkpoint',$hgp_rep_ckpt,'--output-dir','results\m4') },
  @{ name = 'm2_d5_eval_fixed';       args = @('-m','graph_qec.m3','--config','configs\m2_learned_basis_repetition_circuit_level_d5.json','--checkpoint','results\m2\m2_learned_basis_repetition_circuit_level_d5__d5__circuit_level__p0p01__train_only\model_state.pt','--output-dir','results\m3_fixed','--tag','m2_d5_eval_fixed','--decoders','mwpm','bp','bp_osd','bp_gnn','bp_gnn_osd','--timed-runs','1') },
  @{ name = 'surface_sweep';          args = @('scripts\m4_surface_sweep.py','--distances','3','5','--shots','16384') },
  @{ name = 'm5_quantization';        args = @('scripts\m5_quantization.py','--config','configs\m3_learned_basis_repetition_circuit_level_d3.json','--checkpoint','results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt') }
)
foreach ($step in $steps) {
  $log = "results\logs\$($step.name).log"
  "[$(Get-Date -Format HH:mm:ss)] START $($step.name)" | Out-File -FilePath $log -Encoding utf8
  & $py @($step.args) *>> $log
  "[$(Get-Date -Format HH:mm:ss)] DONE $($step.name) exit=$LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
}
"[$(Get-Date -Format HH:mm:ss)] ALL STEPS DONE" | Out-File -FilePath 'results\logs\_all_done.txt' -Encoding utf8
