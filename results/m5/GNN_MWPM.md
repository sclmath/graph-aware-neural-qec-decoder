# M5+: learned posterior fed to MWPM (rather than BP)

Checkpoint: `results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\model_state.pt`  
2048 test shots, reweight strength 1.00, per-shot matching graph rebuilt from the learned mechanism posteriors.

| decoder | logical errors | LER | s.e. | us/shot |
|---|---:|---:|---:|---:|
| mwpm (DEM prior) | 28 | 0.01367 | - | 0.3 |
| mwpm + GNN posteriors | 1853 | 0.90479 | 0.00649 | 1625.2 |
| bp + GNN prior | 55 | 0.02686 | - | 89.4 |
