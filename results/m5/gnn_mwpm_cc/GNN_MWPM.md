# M5+: learned posterior fed to MWPM (rather than BP)

Checkpoint: `results\m4_surface_cc\m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05\model_state.pt`  
4096 test shots, reweight strength 1.00, per-shot matching graph rebuilt from the learned mechanism posteriors.

| decoder | logical errors | LER | s.e. | us/shot |
|---|---:|---:|---:|---:|
| mwpm (DEM prior) | 216 | 0.05273 | - | 0.3 |
| mwpm + GNN posteriors | 1282 | 0.31299 | 0.00725 | 384.9 |
| bp + GNN prior | 238 | 0.05811 | - | 12.8 |
