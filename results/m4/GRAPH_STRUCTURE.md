# M4 detector-graph structure comparison

| code | noise | detectors | mechanisms | edges | check deg max/mean | variable deg max/mean | 4-cycles | matchable |
|---|---|---:|---:|---:|---|---|---:|---|
| repetition_code | circuit_level | 8 | 21 | 34 | 5 / 4.25 | 2 / 1.62 | 0 | True |
| rotated_surface_code | code_capacity | 24 | 53 | 98 | 7 / 4.08 | 4 / 1.85 | 28 | True |
| rotated_surface_code | circuit_level | 24 | 219 | 564 | 48 / 23.50 | 4 / 2.58 | 1956 | True |
| rotated_surface_code | circuit_level | 120 | 1677 | 5004 | 80 / 41.70 | 4 / 2.98 | 26046 | True |
| hgp_rep3x3 | code_capacity | 12 | 39 | 80 | 8 / 6.67 | 4 / 2.05 | 30 | False |
| hgp_hamming7x7 | code_capacity | 42 | 174 | 480 | 14 / 11.43 | 8 / 2.76 | 576 | False |

Check-degree histograms (degree -> number of detectors):

- **repetition_code** (circuit_level): {'3': 2, '4': 2, '5': 4}
- **rotated_surface_code** (code_capacity): {'0': 4, '2': 2, '3': 2, '4': 8, '7': 8}
- **rotated_surface_code** (circuit_level): {'3': 2, '8': 2, '10': 4, '16': 2, '19': 2, '20': 2, '26': 2, '34': 2, '43': 2, '45': 2, '48': 2}
- **rotated_surface_code** (circuit_level): {'3': 4, '8': 2, '10': 4, '11': 4, '16': 2, '18': 2, '19': 6, '20': 4, '22': 10, '26': 6, '28': 12, '38': 2, '43': 2, '46': 2, '48': 2, '50': 2, '52': 4, '53': 2, '54': 2, '55': 2, '56': 8, '58': 2, '59': 2, '64': 8, '68': 10, '70': 4, '71': 2, '80': 8}
- **hgp_rep3x3** (code_capacity): {'6': 8, '8': 4}
- **hgp_hamming7x7** (code_capacity): {'10': 18, '12': 18, '14': 6}

`matchable` records whether a minimum-weight matching decoder applies at all (surface codes decompose into a degree-<=2 matching graph; HGP codes do not).
