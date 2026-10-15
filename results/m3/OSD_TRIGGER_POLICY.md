# M3 OSD-0 trigger policy

Learned prior at strength 1.00; 32768 test shots; 464 non-converged shots.

| OSD trigger threshold k | OSD shots | OSD rate | logical errors | LER | syndrome consistency |
|---:|---:|---:|---:|---:|---:|
| 0 | 464 | 0.0142 | 407 | 0.01242 | 1.0000 |
| 1 | 232 | 0.0071 | 382 | 0.01166 | 0.9929 |
| 2 | 71 | 0.0022 | 341 | 0.01041 | 0.9880 |
| 3 | 4 | 0.0001 | 325 | 0.00992 | 0.9860 |
| 4 | 0 | 0.0000 | 323 | 0.00986 | 0.9858 |
| 6 | 0 | 0.0000 | 323 | 0.00986 | 0.9858 |
| 8 | 0 | 0.0000 | 323 | 0.00986 | 0.9858 |
| 12 | 0 | 0.0000 | 323 | 0.00986 | 0.9858 |
| never (0 on BP) | 0 | 0.0000 | 323 | 0.00986 | 0.9858 |

Outcome of OSD-0 by residual syndrome weight among non-converged shots:

| residual weight | shots | BP errors | OSD errors | rescued | broken |
|---|---:|---:|---:|---:|---:|
| 1 | 232 | 120 | 145 | 37 | 62 |
| 2 | 161 | 17 | 58 | 0 | 41 |
| 3 | 67 | 36 | 52 | 15 | 31 |
| 4 | 4 | 0 | 2 | 0 | 2 |
| 5+ | 0 | 0 | 0 | 0 | 0 |
