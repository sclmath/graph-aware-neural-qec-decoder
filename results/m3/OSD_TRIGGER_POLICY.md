# M3 OSD-0 trigger policy

Learned prior at strength 1.00; 32768 test shots; 288 non-converged shots.

| OSD trigger threshold k | OSD shots | OSD rate | logical errors | LER | syndrome consistency |
|---:|---:|---:|---:|---:|---:|
| 0 | 288 | 0.0088 | 333 | 0.01016 | 1.0000 |
| 1 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| 2 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| 3 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| 4 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| 6 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| 8 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| 12 | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |
| never (0 on BP) | 0 | 0.0000 | 312 | 0.00952 | 0.9912 |

Outcome of OSD-0 by residual syndrome weight among non-converged shots:

| residual weight | shots | BP errors | OSD errors | rescued | broken |
|---|---:|---:|---:|---:|---:|
| 1 | 288 | 154 | 175 | 67 | 88 |
| 2 | 0 | 0 | 0 | 0 | 0 |
| 3 | 0 | 0 | 0 | 0 | 0 |
| 4 | 0 | 0 | 0 | 0 | 0 |
| 5+ | 0 | 0 | 0 | 0 | 0 |
