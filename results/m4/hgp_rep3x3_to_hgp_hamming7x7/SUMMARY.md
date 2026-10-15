# M4 transfer: hgp_rep3x3 -> hgp_hamming7x7

- source: hgp_rep3x3 code_capacity p=0.05
- target: hgp_hamming7x7 code_capacity p=0.05, 58 qubits, k=16
- test shots: 32768, strength fixed at 1.00

| decoder | logical errors | LER | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|
| bp | 12939 | 0.39487 | 0.6555 | 693.4 |
| bp_gnn | 11458 | 0.34967 | 0.7636 | 487.7 |
| bp_gnn_osd | 12029 | 0.36710 | 1.0000 | 644.5 |
