### R1 analyst picks (weight 0-3) of the 26 events by tier

| phase | no_data | no_3c_sensor | 3c_incomplete | 3c_complete | total |
|---|---|---|---|---|---|
| P | 1194 | 261 | 13 | 1861 | 3329 |
| S | 1 | 15 | 0 | 213 | 229 |

### R2 analyst P picks by the analyst's channel type and tier

| ch_type | 3c_complete | 3c_incomplete | no_3c_sensor | no_data |
|---|---|---|---|---|
| BH | 5 | 0 | 0 | 0 |
| CN | 10 | 0 | 0 | 1 |
| DP | 12 | 0 | 7 | 73 |
| EH | 635 | 0 | 245 | 504 |
| EP | 85 | 0 | 0 | 2 |
| HH | 412 | 0 | 0 | 548 |
| HN | 702 | 13 | 9 | 66 |

prediction check (analyst minus ray1d CON): {"P": {"n": 3121, "median_s": -0.12162716, "p01_s": -0.9818436662000001, "p99_s": 1.0246539294000008, "frac_within_pred_tol": 0.9772508811278436}, "S": {"n": 220, "median_s": 0.263053152, "p01_s": -0.71209886818, "p99_s": 1.3977820381100003, "frac_within_pred_tol": 0.9227272727272727}}

### T1 per model and phase (main binding set; _hn = accelerometer binding set, 28 stations)

| model | phase | recall_all | recall_with_data | recall_3C | recall_3C_complete | precision | precision_counting_plausible | F1 | median_abs_dt | MAD | p95_abs_dt | mean_dt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 1600/3329 = 0.48 | 0.75 | 1600/1874 = 0.85 | 1597/1861 = 0.86 | 1775/2456 = 0.72 | 0.92 | 0.783 | 0.040 | 0.027 | 0.210 | -0.025 |
| phasenet_instance | S | 194/229 = 0.85 | 0.85 | 194/213 = 0.91 | 194/213 = 0.91 | 221/1709 = 0.13 | 0.75 | 0.227 | 0.070 | 0.062 | 0.356 | -0.017 |
| phasenet_instance | P+S | 1794/3558 = 0.50 | 0.76 | 1794/2087 = 0.86 | 1791/2074 = 0.86 | 1996/4165 = 0.48 | 0.85 | 0.615 | 0.040 | 0.029 | 0.220 | -0.024 |
| phasenet_original | P | 1592/3329 = 0.48 | 0.75 | 1592/1874 = 0.85 | 1589/1861 = 0.85 | 1763/2641 = 0.67 | 0.84 | 0.748 | 0.033 | 0.028 | 0.230 | +0.046 |
| phasenet_original | S | 198/229 = 0.86 | 0.87 | 198/213 = 0.93 | 198/213 = 0.93 | 233/2398 = 0.10 | 0.64 | 0.176 | 0.077 | 0.052 | 0.391 | +0.084 |
| phasenet_original | P+S | 1790/3558 = 0.50 | 0.76 | 1790/2087 = 0.86 | 1787/2074 = 0.86 | 1996/5039 = 0.40 | 0.74 | 0.542 | 0.040 | 0.030 | 0.240 | +0.051 |
| phasenet_scedc | P | 1389/3329 = 0.42 | 0.65 | 1389/1874 = 0.74 | 1388/1861 = 0.75 | 1462/1954 = 0.75 | 0.85 | 0.745 | 0.047 | 0.050 | 0.320 | +0.054 |
| phasenet_scedc | S | 141/229 = 0.62 | 0.62 | 141/213 = 0.66 | 141/213 = 0.66 | 155/891 = 0.17 | 0.70 | 0.276 | 0.090 | 0.081 | 0.420 | +0.106 |
| phasenet_scedc | P+S | 1530/3558 = 0.43 | 0.65 | 1530/2087 = 0.73 | 1529/2074 = 0.74 | 1617/2845 = 0.57 | 0.80 | 0.640 | 0.050 | 0.050 | 0.320 | +0.059 |
| eqtp_ncedc | P | 1378/3329 = 0.41 | 0.65 | 1378/1874 = 0.74 | 1377/1861 = 0.74 | 1413/2030 = 0.70 | 0.77 | 0.715 | 0.030 | 0.030 | 0.171 | +0.018 |
| eqtp_ncedc | S | 189/229 = 0.83 | 0.83 | 189/213 = 0.89 | 189/213 = 0.89 | 207/1794 = 0.12 | 0.54 | 0.204 | 0.060 | 0.060 | 0.382 | +0.043 |
| eqtp_ncedc | P+S | 1567/3558 = 0.44 | 0.66 | 1567/2087 = 0.75 | 1566/2074 = 0.76 | 1620/3824 = 0.42 | 0.66 | 0.542 | 0.030 | 0.030 | 0.190 | +0.021 |
| phasenet_instance_hn | P | 295/3329 = 0.09 | 0.14 | 282/1874 = 0.15 | 282/1861 = 0.15 | 327/400 = 0.82 | 0.91 | 0.254 | 0.030 | 0.030 | 0.218 | -0.011 |
| phasenet_instance_hn | S | 72/229 = 0.31 | 0.32 | 61/213 = 0.29 | 61/213 = 0.29 | 81/302 = 0.27 | 0.78 | 0.277 | 0.077 | 0.067 | 0.471 | +0.015 |
| phasenet_instance_hn | P+S | 367/3558 = 0.10 | 0.16 | 343/2087 = 0.16 | 343/2074 = 0.17 | 408/702 = 0.58 | 0.85 | 0.256 | 0.037 | 0.030 | 0.240 | -0.006 |
| phasenet_original_hn | P | 309/3329 = 0.09 | 0.14 | 291/1874 = 0.16 | 291/1861 = 0.16 | 341/432 = 0.79 | 0.86 | 0.260 | 0.040 | 0.030 | 0.328 | +0.059 |
| phasenet_original_hn | S | 77/229 = 0.34 | 0.34 | 64/213 = 0.30 | 64/213 = 0.30 | 87/394 = 0.22 | 0.70 | 0.255 | 0.070 | 0.050 | 0.391 | +0.111 |
| phasenet_original_hn | P+S | 386/3558 = 0.11 | 0.16 | 355/2087 = 0.17 | 355/2074 = 0.17 | 428/826 = 0.52 | 0.79 | 0.256 | 0.041 | 0.033 | 0.340 | +0.070 |
| phasenet_scedc_hn | P | 246/3329 = 0.07 | 0.12 | 231/1874 = 0.12 | 231/1861 = 0.12 | 258/311 = 0.83 | 0.88 | 0.215 | 0.051 | 0.053 | 0.347 | +0.066 |
| phasenet_scedc_hn | S | 44/229 = 0.19 | 0.19 | 38/213 = 0.18 | 38/213 = 0.18 | 49/142 = 0.35 | 0.73 | 0.235 | 0.115 | 0.085 | 0.493 | +0.142 |
| phasenet_scedc_hn | P+S | 290/3558 = 0.08 | 0.12 | 269/2087 = 0.13 | 269/2074 = 0.13 | 307/453 = 0.68 | 0.83 | 0.217 | 0.058 | 0.060 | 0.361 | +0.077 |
| eqtp_ncedc_hn | P | 276/3329 = 0.08 | 0.13 | 260/1874 = 0.14 | 260/1861 = 0.14 | 278/378 = 0.74 | 0.75 | 0.233 | 0.023 | 0.022 | 0.200 | +0.030 |
| eqtp_ncedc_hn | S | 72/229 = 0.31 | 0.32 | 60/213 = 0.28 | 60/213 = 0.28 | 73/327 = 0.22 | 0.61 | 0.249 | 0.061 | 0.068 | 0.428 | +0.079 |
| eqtp_ncedc_hn | P+S | 348/3558 = 0.10 | 0.15 | 320/2087 = 0.15 | 320/2074 = 0.15 | 351/705 = 0.50 | 0.69 | 0.234 | 0.030 | 0.033 | 0.243 | +0.040 |

### T2a P recall at complete records, by the bound sensor type

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| CN | 11 | 10/11 = 0.91 | 10/11 = 0.91 | 7/11 = 0.64 | 10/11 = 0.91 |
| DP | 11 | 10/11 = 0.91 | 10/11 = 0.91 | 11/11 = 1.00 | 10/11 = 0.91 |
| EH | 107 | 95/107 = 0.89 | 95/107 = 0.89 | 96/107 = 0.90 | 92/107 = 0.86 |
| EP | 86 | 78/86 = 0.91 | 73/86 = 0.85 | 56/86 = 0.65 | 63/86 = 0.73 |
| HH | 422 | 366/422 = 0.87 | 367/422 = 0.87 | 331/422 = 0.78 | 231/422 = 0.55 |
| HN | 1224 | 1038/1224 = 0.85 | 1034/1224 = 0.84 | 887/1224 = 0.72 | 971/1224 = 0.79 |

### T2b P recall at 3-C stations (complete + triggered records), by bound sensor

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| CN | 11 | 10/11 = 0.91 | 10/11 = 0.91 | 7/11 = 0.64 | 10/11 = 0.91 |
| DP | 11 | 10/11 = 0.91 | 10/11 = 0.91 | 11/11 = 1.00 | 10/11 = 0.91 |
| EH | 107 | 95/107 = 0.89 | 95/107 = 0.89 | 96/107 = 0.90 | 92/107 = 0.86 |
| EP | 86 | 78/86 = 0.91 | 73/86 = 0.85 | 56/86 = 0.65 | 63/86 = 0.73 |
| HH | 422 | 366/422 = 0.87 | 367/422 = 0.87 | 331/422 = 0.78 | 231/422 = 0.55 |
| HN | 1237 | 1041/1237 = 0.84 | 1037/1237 = 0.84 | 888/1237 = 0.72 | 972/1237 = 0.79 |

### T2c P precision by bound sensor (DL picks in window)

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| CN | 0.80 (15) | 0.71 (17) | 0.80 (10) | 0.71 (14) |
| DP | 0.42 (26) | 0.44 (25) | 0.50 (24) | 0.48 (21) |
| EH | 0.73 (138) | 0.72 (143) | 0.85 (118) | 0.67 (137) |
| EP | 0.74 (115) | 0.69 (117) | 0.73 (78) | 0.71 (91) |
| HH | 0.79 (505) | 0.76 (514) | 0.82 (417) | 0.69 (348) |
| HN | 0.70 (1657) | 0.64 (1825) | 0.72 (1307) | 0.70 (1419) |

### T2d P recall over picks WITH DATA, by the analyst's channel type

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| BH | 5 | 5/5 = 1.00 | 5/5 = 1.00 | 3/5 = 0.60 | 1/5 = 0.20 |
| CN | 10 | 10/10 = 1.00 | 10/10 = 1.00 | 7/10 = 0.70 | 9/10 = 0.90 |
| DP | 19 | 10/19 = 0.53 | 10/19 = 0.53 | 11/19 = 0.58 | 11/19 = 0.58 |
| EH | 880 | 544/880 = 0.62 | 545/880 = 0.62 | 494/880 = 0.56 | 487/880 = 0.55 |
| EP | 85 | 77/85 = 0.91 | 72/85 = 0.85 | 55/85 = 0.65 | 62/85 = 0.73 |
| HH | 412 | 360/412 = 0.87 | 360/412 = 0.87 | 326/412 = 0.79 | 227/412 = 0.55 |
| HN | 724 | 594/724 = 0.82 | 590/724 = 0.81 | 493/724 = 0.68 | 581/724 = 0.80 |

### T3a P recall at complete records by epicentral distance

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0-20 km | 349 | 312/349 = 0.89 | 314/349 = 0.90 | 283/349 = 0.81 | 284/349 = 0.81 |
| 20-40 km | 765 | 648/765 = 0.85 | 649/765 = 0.85 | 558/765 = 0.73 | 578/765 = 0.76 |
| 40-60 km | 509 | 430/509 = 0.84 | 418/509 = 0.82 | 355/509 = 0.70 | 368/509 = 0.72 |
| 60-80 km | 238 | 207/238 = 0.87 | 208/238 = 0.87 | 192/238 = 0.81 | 147/238 = 0.62 |
| >80 km | 0 |  |  |  |  |

### T3b P precision by distance

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| 0-20 km | 0.85 (402) | 0.79 (440) | 0.82 (353) | 0.77 (376) |
| 20-40 km | 0.75 (962) | 0.69 (1054) | 0.77 (768) | 0.69 (858) |
| 40-60 km | 0.66 (734) | 0.61 (772) | 0.73 (528) | 0.69 (557) |
| 60-80 km | 0.63 (358) | 0.58 (375) | 0.65 (305) | 0.63 (239) |
| >80 km |  (0) |  (0) |  (0) |  (0) |

### T3c S recall at complete records by distance

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0-20 km | 121 | 105/121 = 0.87 | 108/121 = 0.89 | 71/121 = 0.59 | 103/121 = 0.85 |
| 20-40 km | 77 | 74/77 = 0.96 | 75/77 = 0.97 | 59/77 = 0.77 | 72/77 = 0.94 |
| 40-60 km | 15 | 15/15 = 1.00 | 15/15 = 1.00 | 11/15 = 0.73 | 14/15 = 0.93 |
| 60-80 km | 0 |  |  |  |  |
| >80 km | 0 |  |  |  |  |

### T4a P recall at complete records by magnitude

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| M0.5-1.0 | 60 | 37/60 = 0.62 | 41/60 = 0.68 | 20/60 = 0.33 | 18/60 = 0.30 |
| M1.0-1.5 | 79 | 64/79 = 0.81 | 65/79 = 0.82 | 49/79 = 0.62 | 31/79 = 0.39 |
| M1.5-2.0 | 134 | 103/134 = 0.77 | 102/134 = 0.76 | 74/134 = 0.55 | 53/134 = 0.40 |
| M2.0-2.5 | 401 | 254/401 = 0.63 | 259/401 = 0.65 | 244/401 = 0.61 | 276/401 = 0.69 |
| M2.5-3.0 | 411 | 385/411 = 0.94 | 373/411 = 0.91 | 312/411 = 0.76 | 293/411 = 0.71 |
| M3.0-4.18 | 776 | 754/776 = 0.97 | 749/776 = 0.97 | 689/776 = 0.89 | 706/776 = 0.91 |

### T4b S recall at complete records by magnitude

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| M0.5-1.0 | 12 | 8/12 = 0.67 | 11/12 = 0.92 | 4/12 = 0.33 | 9/12 = 0.75 |
| M1.0-1.5 | 8 | 7/8 = 0.88 | 8/8 = 1.00 | 5/8 = 0.62 | 7/8 = 0.88 |
| M1.5-2.0 | 12 | 9/12 = 0.75 | 10/12 = 0.83 | 7/12 = 0.58 | 10/12 = 0.83 |
| M2.0-2.5 | 33 | 28/33 = 0.85 | 28/33 = 0.85 | 23/33 = 0.70 | 25/33 = 0.76 |
| M2.5-3.0 | 53 | 51/53 = 0.96 | 51/53 = 0.96 | 36/53 = 0.68 | 49/53 = 0.92 |
| M3.0-4.18 | 95 | 91/95 = 0.96 | 90/95 = 0.95 | 66/95 = 0.69 | 89/95 = 0.94 |

### T4c P precision by magnitude

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| M0.5-1.0 | 0.69 (54) | 0.44 (93) | 0.38 (53) | 0.44 (41) |
| M1.0-1.5 | 0.56 (114) | 0.42 (154) | 0.49 (101) | 0.53 (59) |
| M1.5-2.0 | 0.48 (215) | 0.40 (253) | 0.48 (154) | 0.50 (106) |
| M2.0-2.5 | 0.67 (598) | 0.63 (619) | 0.72 (413) | 0.68 (453) |
| M2.5-3.0 | 0.68 (605) | 0.64 (628) | 0.71 (462) | 0.70 (418) |
| M3.0-4.18 | 0.87 (870) | 0.86 (894) | 0.90 (771) | 0.74 (953) |

### T5a P recall at complete records by time to the nearest other catalog event

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| none within 120 s | 858 | 762/858 = 0.89 | 754/858 = 0.88 | 635/858 = 0.74 | 569/858 = 0.66 |
| nearest 60-120 s | 395 | 374/395 = 0.95 | 371/395 = 0.94 | 326/395 = 0.83 | 327/395 = 0.83 |
| nearest 15-60 s | 243 | 229/243 = 0.94 | 227/243 = 0.93 | 201/243 = 0.83 | 196/243 = 0.81 |
| nearest <= 15 s | 365 | 232/365 = 0.64 | 237/365 = 0.65 | 226/365 = 0.62 | 285/365 = 0.78 |

### T5b S recall at complete records by time to the nearest other catalog event

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| none within 120 s | 125 | 116/125 = 0.93 | 120/125 = 0.96 | 85/125 = 0.68 | 113/125 = 0.90 |
| nearest 60-120 s | 49 | 47/49 = 0.96 | 48/49 = 0.98 | 32/49 = 0.65 | 44/49 = 0.90 |
| nearest 15-60 s | 25 | 25/25 = 1.00 | 25/25 = 1.00 | 22/25 = 0.88 | 24/25 = 0.96 |
| nearest <= 15 s | 14 | 6/14 = 0.43 | 5/14 = 0.36 | 2/14 = 0.14 | 8/14 = 0.57 |

### T6a P recall at 3-C stations by analyst weight code

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0 | 499 | 466/499 = 0.93 | 469/499 = 0.94 | 457/499 = 0.92 | 457/499 = 0.92 |
| 1 | 768 | 684/768 = 0.89 | 695/768 = 0.90 | 619/768 = 0.81 | 611/768 = 0.80 |
| 2 | 480 | 374/480 = 0.78 | 363/480 = 0.76 | 273/480 = 0.57 | 274/480 = 0.57 |
| 3 | 127 | 76/127 = 0.60 | 65/127 = 0.51 | 40/127 = 0.32 | 36/127 = 0.28 |

### T6b P median |dt| / p95 |dt| (s) by analyst weight code

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| 0 | 0.030 / 0.098 | 0.021 / 0.090 | 0.030 / 0.260 | 0.020 / 0.085 |
| 1 | 0.032 / 0.170 | 0.030 / 0.167 | 0.048 / 0.280 | 0.030 / 0.140 |
| 2 | 0.050 / 0.290 | 0.070 / 0.283 | 0.110 / 0.380 | 0.060 / 0.295 |
| 3 | 0.084 / 0.333 | 0.140 / 0.448 | 0.150 / 0.411 | 0.085 / 0.412 |

### T6c S median |dt| / p95 |dt| (s) by analyst weight code

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| 0 |  /  |  /  |  /  |  /  |
| 1 | 0.062 / 0.206 | 0.053 / 0.200 | 0.070 / 0.260 | 0.050 / 0.218 |
| 2 | 0.080 / 0.545 | 0.120 / 0.698 | 0.125 / 0.700 | 0.091 / 0.623 |
| 3 | 0.010 / 0.019 | 0.110 / 0.110 | 0.125 / 0.166 | 0.065 / 0.088 |

### T7 velocity sensor vs accelerometer at the same 28 stations

| model | sensor | phase | recall_all_records | recall_complete | precision | median_abs_dt | p95_abs_dt | mean_dt |
|---|---|---|---|---|---|---|---|---|
| eqtp_ncedc | main (velocity sensor) | P | 259/411 = 0.63 | 259/392 = 0.66 | 265/375 = 0.71 | 0.030 | 0.161 | +0.032 |
| eqtp_ncedc | main (velocity sensor) | S | 68/93 = 0.73 | 68/78 = 0.87 | 70/326 = 0.21 | 0.090 | 0.358 | +0.024 |
| eqtp_ncedc | hn (accelerometer) | P | 276/411 = 0.67 | 260/392 = 0.66 | 278/378 = 0.74 | 0.023 | 0.200 | +0.030 |
| eqtp_ncedc | hn (accelerometer) | S | 72/93 = 0.77 | 60/78 = 0.77 | 73/327 = 0.22 | 0.061 | 0.428 | +0.079 |
| phasenet_original | main (velocity sensor) | P | 341/411 = 0.83 | 341/392 = 0.87 | 369/471 = 0.78 | 0.030 | 0.210 | +0.043 |
| phasenet_original | main (velocity sensor) | S | 72/93 = 0.77 | 72/78 = 0.92 | 81/429 = 0.19 | 0.072 | 0.361 | +0.062 |
| phasenet_original | hn (accelerometer) | P | 309/411 = 0.75 | 291/392 = 0.74 | 341/432 = 0.79 | 0.040 | 0.328 | +0.059 |
| phasenet_original | hn (accelerometer) | S | 77/93 = 0.83 | 64/78 = 0.82 | 87/394 = 0.22 | 0.070 | 0.391 | +0.111 |
| phasenet_scedc | main (velocity sensor) | P | 313/411 = 0.76 | 313/392 = 0.80 | 323/388 = 0.83 | 0.029 | 0.260 | +0.010 |
| phasenet_scedc | main (velocity sensor) | S | 50/93 = 0.54 | 50/78 = 0.64 | 53/184 = 0.29 | 0.060 | 0.263 | +0.078 |
| phasenet_scedc | hn (accelerometer) | P | 246/411 = 0.60 | 231/392 = 0.59 | 258/311 = 0.83 | 0.051 | 0.347 | +0.066 |
| phasenet_scedc | hn (accelerometer) | S | 44/93 = 0.47 | 38/78 = 0.49 | 49/142 = 0.35 | 0.115 | 0.493 | +0.142 |
| phasenet_instance | main (velocity sensor) | P | 340/411 = 0.83 | 340/392 = 0.87 | 372/453 = 0.82 | 0.030 | 0.191 | -0.022 |
| phasenet_instance | main (velocity sensor) | S | 68/93 = 0.73 | 68/78 = 0.87 | 74/352 = 0.21 | 0.068 | 0.307 | -0.038 |
| phasenet_instance | hn (accelerometer) | P | 295/411 = 0.72 | 282/392 = 0.72 | 327/400 = 0.82 | 0.030 | 0.218 | -0.011 |
| phasenet_instance | hn (accelerometer) | S | 72/93 = 0.77 | 61/78 = 0.78 | 81/302 = 0.27 | 0.077 | 0.471 | +0.015 |

### T8 missed analyst picks at 3c_complete records, by reason

| variant | phase | model_below_minConfidence | no_P_pick_so_no_S_picker | no_S_window_covering | no_detector_trigger | only_P_pick_is_on_this_S_wave | peak_vetoed_as_S | trigger_not_turned_into_picker | window_picked_other_time |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 33 | 0 | 0 | 55 | 0 | 1 | 16 | 159 |
| phasenet_instance | S | 2 | 14 | 0 | 0 | 0 | 0 | 0 | 3 |
| phasenet_original | P | 38 | 0 | 0 | 55 | 0 | 1 | 16 | 162 |
| phasenet_original | S | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 5 |
| phasenet_scedc | P | 286 | 0 | 0 | 55 | 0 | 9 | 16 | 107 |
| phasenet_scedc | S | 38 | 18 | 1 | 0 | 1 | 0 | 0 | 14 |
| eqtp_ncedc | P | 334 | 0 | 0 | 47 | 0 | 7 | 14 | 82 |
| eqtp_ncedc | S | 1 | 13 | 1 | 0 | 0 | 0 | 0 | 9 |

### T8 missed analyst picks at 3c_incomplete records, by reason

| variant | phase | model_below_minConfidence | no_detector_trigger | record_starts_too_late |
|---|---|---|---|---|
| phasenet_instance | P | 0 | 1 | 9 |
| phasenet_original | P | 0 | 1 | 9 |
| phasenet_scedc | P | 2 | 1 | 9 |
| eqtp_ncedc | P | 0 | 2 | 10 |

### T8c P misses below minConfidence at complete records: best model value in the covering windows

| variant | (0.0, 0.1] | (0.1, 0.2] | (0.2, 0.3] | (0.3, 0.4] |
|---|---|---|---|---|
| eqtp_ncedc | 202 | 51 | 33 | 27 |
| phasenet_instance | 9 | 3 | 4 | 17 |
| phasenet_original | 1 | 8 | 14 | 15 |
| phasenet_scedc | 65 | 84 | 69 | 68 |

### T9 unmatched DL picks inside the event windows, by class

| variant | phase | near_duplicate | noise_or_other | phase_confusion | plausible_no_analyst_pick | plausible_other_event_arrival | reference_outlier | timing_disagreement |
|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 70 | 104 | 5 | 454 | 12 | 10 | 26 |
| phasenet_instance | S | 66 | 353 | 1 | 975 | 93 | 0 | 0 |
| phasenet_original | P | 81 | 287 | 21 | 423 | 19 | 12 | 35 |
| phasenet_original | S | 113 | 751 | 10 | 1163 | 128 | 0 | 0 |
| phasenet_scedc | P | 66 | 162 | 26 | 188 | 8 | 2 | 40 |
| phasenet_scedc | S | 33 | 181 | 50 | 427 | 45 | 0 | 0 |
| eqtp_ncedc | P | 344 | 103 | 1 | 147 | 1 | 4 | 17 |
| eqtp_ncedc | S | 327 | 446 | 57 | 668 | 89 | 0 | 0 |

### T10 DL picks outside the event windows

| model | phase | outside_window | other_catalog_event | in_common_noise_span | station_hours | false_per_station_hour | HH | HN | EH | EP |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 479 | 245 | 49 (17 coincident) | 56.0 | 0.87 | 0.73 | 0.83 | 1.93 | 1.35 |
| phasenet_instance | S | 243 | 201 | 11 (5 coincident) | 56.0 | 0.20 | 0.31 | 0.19 | 0.00 | 0.00 |
| phasenet_original | P | 883 | 299 | 218 (183 coincident) | 56.0 | 3.89 | 2.28 | 4.12 | 3.86 | 7.22 |
| phasenet_original | S | 578 | 334 | 129 (106 coincident) | 56.0 | 2.30 | 1.35 | 2.41 | 1.93 | 4.51 |
| phasenet_scedc | P | 546 | 164 | 163 (125 coincident) | 56.0 | 2.91 | 2.18 | 3.12 | 4.34 | 1.35 |
| phasenet_scedc | S | 181 | 89 | 52 (36 coincident) | 56.0 | 0.93 | 0.21 | 1.10 | 1.45 | 0.45 |
| eqtp_ncedc | P | 210 | 38 | 75 (24 coincident) | 56.0 | 1.34 | 1.87 | 1.32 | 0.48 | 0.45 |
| eqtp_ncedc | S | 68 | 32 | 27 (8 coincident) | 56.0 | 0.48 | 0.31 | 0.56 | 0.00 | 0.45 |

### T11 cost (whole scautopick process, /usr/bin/time; 26 runs per variant)

| model | cpu_s | station_hours | cpu_s_per_station_hour | triggers | P_windows | S_windows | ms_per_window | peak_MB | startup_probe_cpu_s |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | 66.8 | 310.0 | 0.215 | 10505 | 8464 | 11637 | 3.1 | 336 | 0.16 |
| phasenet_original | 69.7 | 310.0 | 0.225 | 10505 | 8464 | 13871 | 2.9 | 340 | 0.16 |
| phasenet_scedc | 61.6 | 310.0 | 0.199 | 10505 | 8464 | 9870 | 3.1 | 318 | 0.16 |
| eqtp_ncedc | 1554.3 | 310.0 | 5.013 | 10505 | 5432 | 8607 | 110.4 | 481 | 0.16 |

### T12 eqtp_ncedc: P polarity vs analyst first motion (matched P picks with analyst U/D)

analyst first motions: 1700 in total, 1267 at 3-C stations, 1065 matched; stations with >= 3 comparisons: 114; of those always opposite: [('BK.MHDL', 7, 'Inverted'), ('BK.OHLN', 4, 'Inverted'), ('BK.OXMT', 4, 'Inverted'), ('BK.SBRN', 8, 'Inverted'), ('NC.JMGB', 6, 'Direct'), ('NC.NGVB', 3, 'Direct')]

| group | n | coverage_0p5 | agree_0p5 | agree_raw_counts_0p5 | coverage_0p7 | agree_0p7 | agree_raw_counts_0p7 |
|---|---|---|---|---|---|---|---|
| all | 1065 | 0.88 | 0.87 | 0.89 | 0.72 | 0.91 | 0.93 |
| onset_I | 1061 | 0.88 | 0.87 | 0.89 | 0.72 | 0.91 | 0.93 |
| onset_E | 4 | 0.75 | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 |
| weight_0 | 457 | 0.93 | 0.94 | 0.95 | 0.84 | 0.95 | 0.96 |
| weight_1 | 607 | 0.84 | 0.81 | 0.84 | 0.63 | 0.87 | 0.89 |
| weight_3 | 1 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 |
| same_channel | 705 | 0.88 | 0.86 | 0.89 | 0.72 | 0.90 | 0.93 |
| other_channel | 360 | 0.87 | 0.89 | 0.89 | 0.72 | 0.92 | 0.92 |
| direct_sense | 1039 | 0.88 | 0.89 | 0.89 | 0.72 | 0.93 | 0.93 |
| inverted_sense | 26 | 0.88 | 0.04 | 0.96 | 0.62 | 0.06 | 0.94 |
| dist_0-20 km | 264 | 0.91 | 0.93 | 0.93 | 0.80 | 0.95 | 0.95 |
| dist_20-40 km | 440 | 0.88 | 0.90 | 0.90 | 0.72 | 0.93 | 0.93 |
| dist_40-60 km | 263 | 0.87 | 0.79 | 0.88 | 0.70 | 0.84 | 0.91 |
| dist_60-80 km | 98 | 0.84 | 0.74 | 0.74 | 0.57 | 0.88 | 0.88 |
| mag_M0.5-1.0 | 16 | 0.62 | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 |
| mag_M1.0-1.5 | 24 | 0.75 | 0.94 | 0.94 | 0.54 | 0.92 | 0.92 |
| mag_M1.5-2.0 | 46 | 0.78 | 0.89 | 0.89 | 0.59 | 0.93 | 0.93 |
| mag_M2.0-2.5 | 208 | 0.83 | 0.84 | 0.85 | 0.64 | 0.90 | 0.90 |
| mag_M2.5-3.0 | 202 | 0.84 | 0.87 | 0.88 | 0.67 | 0.92 | 0.93 |
| mag_M3.0-4.18 | 569 | 0.93 | 0.87 | 0.90 | 0.79 | 0.91 | 0.94 |
| bound_CN | 6 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| bound_DP | 9 | 1.00 | 0.89 | 0.89 | 1.00 | 0.89 | 0.89 |
| bound_EH | 76 | 1.00 | 0.95 | 0.95 | 0.89 | 0.94 | 0.94 |
| bound_EP | 46 | 0.87 | 0.40 | 0.93 | 0.65 | 0.43 | 0.90 |
| bound_HH | 193 | 0.82 | 0.85 | 0.85 | 0.64 | 0.94 | 0.94 |
| bound_HN | 735 | 0.88 | 0.89 | 0.89 | 0.72 | 0.92 | 0.92 |

### T12 eqtp_ncedc_hn: P polarity vs analyst first motion (matched P picks with analyst U/D)

analyst first motions: 1700 in total, 1267 at 3-C stations, 237 matched; stations with >= 3 comparisons: 20; of those always opposite: []

| group | n | coverage_0p5 | agree_0p5 | agree_raw_counts_0p5 | coverage_0p7 | agree_0p7 | agree_raw_counts_0p7 |
|---|---|---|---|---|---|---|---|
| all | 237 | 0.86 | 0.91 | 0.91 | 0.73 | 0.94 | 0.94 |
| onset_I | 237 | 0.86 | 0.91 | 0.91 | 0.73 | 0.94 | 0.94 |
| weight_0 | 117 | 0.89 | 0.94 | 0.94 | 0.81 | 0.95 | 0.95 |
| weight_1 | 119 | 0.84 | 0.87 | 0.87 | 0.66 | 0.94 | 0.94 |
| weight_2 | 1 | 1.00 | 1.00 | 1.00 | 0.00 |  |  |
| same_channel | 10 | 0.90 | 0.89 | 0.89 | 0.80 | 0.88 | 0.88 |
| other_channel | 227 | 0.86 | 0.91 | 0.91 | 0.73 | 0.95 | 0.95 |
| direct_sense | 237 | 0.86 | 0.91 | 0.91 | 0.73 | 0.94 | 0.94 |
| dist_0-20 km | 79 | 0.82 | 0.91 | 0.91 | 0.73 | 0.90 | 0.90 |
| dist_20-40 km | 116 | 0.88 | 0.96 | 0.96 | 0.77 | 0.98 | 0.98 |
| dist_40-60 km | 18 | 0.94 | 0.76 | 0.76 | 0.56 | 1.00 | 1.00 |
| dist_60-80 km | 24 | 0.88 | 0.76 | 0.76 | 0.71 | 0.88 | 0.88 |
| mag_M0.5-1.0 | 10 | 0.60 | 0.83 | 0.83 | 0.40 | 0.75 | 0.75 |
| mag_M1.0-1.5 | 15 | 0.60 | 0.89 | 0.89 | 0.53 | 0.88 | 0.88 |
| mag_M1.5-2.0 | 25 | 0.88 | 0.95 | 0.95 | 0.68 | 0.94 | 0.94 |
| mag_M2.0-2.5 | 52 | 0.83 | 0.88 | 0.88 | 0.63 | 0.94 | 0.94 |
| mag_M2.5-3.0 | 43 | 0.93 | 0.95 | 0.95 | 0.86 | 0.97 | 0.97 |
| mag_M3.0-4.18 | 92 | 0.92 | 0.89 | 0.89 | 0.82 | 0.95 | 0.95 |
| bound_HN | 237 | 0.86 | 0.91 | 0.91 | 0.73 | 0.94 | 0.94 |

### T13 analyst first motions on inverted channels vs similar rays on direct channels

neighbours: same event, direct channel, |daz| <= 10.0, |dtakeoff| <= 10.0, >= 2, majority >= 70 %; inverted-channel picks 313, tested 147, same as neighbours 0.24; control (direct channels) 595 tests, 0.82

analyst ('J') picks only: inverted-channel picks 275, tested 129, same as neighbours 0.24; control 574 tests, 0.83; picks without an open epoch: 7

| network | station | channel | dip | gain | n_tests | frac_same_as_direct_neighbours |
|---|---|---|---|---|---|---|
| BK | MHDL | EP1 | -90.0 | -57462000.0 | 43 | 0.12 |
| BK | OHLN | EP1 | -90.0 | -57462000.0 | 33 | 0.24 |
| BK | OXMT | EP1 | -90.0 | -57462000.0 | 29 | 0.07 |
| BK | PETB | EP1 | 90.0 | 1650460000.0 | 4 | 0.75 |
| BK | SBRN | EP1 | -90.0 | -57462000.0 | 19 | 0.37 |
| BK | SM2B | DP1 | 90.0 | 2687700000.0 | 6 | 0.67 |

### T14 SeisBench EQTP('ncedc') v1 vs the plugin, events ['75305736', '75283011', '75285161', '75283271', '75282561']

same weights: True (max |ONNX - torch| on identical input: 5.2e-06); plugin normalisation changes outputs by <= 0.16; P peak shifts [-1, 0, -1, -1, -1, 0, -1, 0] samples; same polarity in 8/8 windows; SeisBench classify CPU 348.1 s for 59.49 station-hours (5.85 per station-hour, 1 thread)

| phase | method | picks | recall_3C | recall_complete | recall_triggered | precision | median_abs_dt | polarity_coverage | polarity_agree |
|---|---|---|---|---|---|---|---|---|---|
| P | plugin | 620 | 398/511 = 0.78 | 0.79 | 0.00 | 0.73 | 0.030 | 0.91 | 0.81 |
| P | seisbench | 627 | 416/511 = 0.81 | 0.82 | 0.00 | 0.88 | 0.039 | 0.92 | 0.84 |
| S | plugin | 537 | 56/66 = 0.85 | 0.85 |  | 0.14 | 0.080 |  |  |
| S | seisbench | 745 | 58/66 = 0.88 | 0.88 |  | 0.13 | 0.080 |  |  |

### T15 the plugin's own eqtp_ncedc windows re-run with SeisBench's normalisation

| windows | n | reach_0p4_plugin_norm | reach_0p4_seisbench_norm | median_P_plugin_norm | median_P_seisbench_norm | n_100Hz | reach_100Hz_plugin | reach_100Hz_seisbench |
|---|---|---|---|---|---|---|---|---|
| missed | 334 | 0 | 22 | 0.014 | 0.012 | 323 | 0 | 22 |
| matched | 1378 | 1374 | 1339 | 0.955 | 0.954 | 1225 | 1222 | 1189 |

reproduction check (logged best P vs recomputed, 100 Hz windows): max |diff| 0.0050

P: 459 plugin-SeisBench pairs; median |dt| 0.015 s; within 0.02 s 0.66; within 0.05 s 0.88; p95 0.080; mean +0.008; max 0.24; polarity both set 348, agree 0.94
   analyst picks found only by SeisBench / only by the plugin / neither: 25 / 7 / 88; only-SeisBench by tier | plugin reason: {'3c_complete | window_picked_other_time': 12, '3c_complete | model_below_minConfidence': 10, '3c_complete | no_detector_trigger': 2, '3c_complete | peak_vetoed_as_S': 1}

S: 372 plugin-SeisBench pairs; median |dt| 0.020 s; within 0.02 s 0.53; within 0.05 s 0.81; p95 0.110; mean -0.002; max 0.96
   analyst picks found only by SeisBench / only by the plugin / neither: 4 / 2 / 6; only-SeisBench by tier | plugin reason: {'3c_complete | no_P_pick_so_no_S_picker': 2, '3c_complete | window_picked_other_time': 2}
