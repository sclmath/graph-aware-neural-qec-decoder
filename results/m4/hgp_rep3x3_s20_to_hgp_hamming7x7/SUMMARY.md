# M4 transfer: hgp_rep3x3 -> hgp_hamming7x7

- source: hgp_rep3x3 code_capacity p=0.05
- target: hgp_hamming7x7 code_capacity p=0.05, 58 qubits, k=16
- test shots: 32768, strength fixed at 1.00

| decoder | logical errors | LER | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|
| bp | 13243 | 0.40414 | 0.6484 | 1503.5 |
| bp_gnn | 14896 | 0.45459 | 0.6135 | 1514.1 |
| bp_gnn_osd | 15451 | 0.47153 | 1.0000 | 1154.0 |
