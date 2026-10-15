# M3 OSD-0 trigger policy

Learned prior at strength 1.00; 4096 test shots; 1294 non-converged shots.

| OSD trigger threshold k | OSD shots | OSD rate | logical errors | LER | syndrome consistency |
|---:|---:|---:|---:|---:|---:|
| 0 | 1294 | 0.3159 | 274 | 0.06689 | 1.0000 |
| 1 | 994 | 0.2427 | 258 | 0.06299 | 0.9268 |
| 2 | 228 | 0.0557 | 228 | 0.05566 | 0.7397 |
| 3 | 131 | 0.0320 | 211 | 0.05151 | 0.7161 |
| 4 | 19 | 0.0046 | 205 | 0.05005 | 0.6887 |
| 6 | 0 | 0.0000 | 207 | 0.05054 | 0.6841 |
| 8 | 0 | 0.0000 | 207 | 0.05054 | 0.6841 |
| 12 | 0 | 0.0000 | 207 | 0.05054 | 0.6841 |
| never (0 on BP) | 0 | 0.0000 | 207 | 0.05054 | 0.6841 |

Outcome of OSD-0 by residual syndrome weight among non-converged shots:

| residual weight | shots | BP errors | OSD errors | rescued | broken |
|---|---:|---:|---:|---:|---:|
| 1 | 300 | 150 | 166 | 115 | 131 |
| 2 | 766 | 8 | 38 | 0 | 30 |
| 3 | 97 | 39 | 56 | 33 | 50 |
| 4 | 112 | 3 | 9 | 0 | 6 |
| 5+ | 19 | 7 | 5 | 6 | 4 |
