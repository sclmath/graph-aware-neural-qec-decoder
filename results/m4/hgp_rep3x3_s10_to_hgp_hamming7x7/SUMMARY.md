# M4 transfer: hgp_rep3x3 -> hgp_hamming7x7

- source: hgp_rep3x3 code_capacity p=0.05
- target: hgp_hamming7x7 code_capacity p=0.05, 58 qubits, k=16
- test shots: 32768, strength fixed at 1.00

| decoder | logical errors | LER | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|
| bp | 13333 | 0.40689 | 0.6462 | 677.7 |
| bp_gnn | 13985 | 0.42679 | 0.6615 | 589.0 |
| bp_gnn_osd | 14593 | 0.44534 | 1.0000 | 1165.8 |
