### R1 analyst picks (weight 0-3) of the 26 events by tier

| phase | no_data | no_3c_sensor | 3c_incomplete | 3c_complete | total |
|---|---|---|---|---|---|
| P | 694 | 411 | 471 | 846 | 2422 |
| S | 0 | 1 | 72 | 90 | 163 |

### R2 analyst P picks by the analyst's channel type and tier

| ch_type | 3c_complete | 3c_incomplete | no_3c_sensor | no_data |
|---|---|---|---|---|
| BH | 0 | 0 | 0 | 2 |
| CN | 26 | 0 | 3 | 0 |
| DP | 15 | 0 | 10 | 19 |
| EH | 385 | 5 | 398 | 533 |
| EP | 129 | 0 | 0 | 5 |
| HH | 186 | 0 | 0 | 135 |
| HN | 105 | 466 | 0 | 0 |

prediction check (analyst minus ray1d CON): {"P": {"n": 2240, "median_s": -0.10709658550000001, "p01_s": -1.07412200678, "p99_s": 1.0143196973500015, "frac_within_pred_tol": 0.9709821428571429}, "S": {"n": 150, "median_s": 0.1462413325, "p01_s": -0.6776385355100001, "p99_s": 1.10860974764, "frac_within_pred_tol": 0.9733333333333334}}

### T1 per model and phase (main binding set; _hn = accelerometer binding set, 13 stations)

| model | phase | recall_all | recall_with_data | recall_3C | recall_3C_complete | precision | precision_counting_plausible | F1 | median_abs_dt | MAD | p95_abs_dt | mean_dt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 743/2422 = 0.31 | 0.43 | 743/1317 = 0.56 | 690/846 = 0.82 | 959/1318 = 0.73 | 0.91 | 0.635 | 0.030 | 0.020 | 0.170 | -0.020 |
| phasenet_instance | S | 79/163 = 0.48 | 0.48 | 79/162 = 0.49 | 72/90 = 0.80 | 100/970 = 0.10 | 0.71 | 0.170 | 0.050 | 0.030 | 0.130 | -0.041 |
| phasenet_instance | P+S | 822/2585 = 0.32 | 0.43 | 822/1479 = 0.56 | 762/936 = 0.81 | 1059/2288 = 0.46 | 0.83 | 0.505 | 0.030 | 0.022 | 0.160 | -0.022 |
| phasenet_original | P | 728/2422 = 0.30 | 0.42 | 728/1317 = 0.55 | 674/846 = 0.80 | 948/1490 = 0.64 | 0.82 | 0.592 | 0.028 | 0.020 | 0.186 | +0.042 |
| phasenet_original | S | 84/163 = 0.52 | 0.52 | 84/162 = 0.52 | 76/90 = 0.84 | 105/1399 = 0.08 | 0.63 | 0.131 | 0.035 | 0.025 | 0.170 | +0.054 |
| phasenet_original | P+S | 812/2585 = 0.31 | 0.43 | 812/1479 = 0.55 | 750/936 = 0.80 | 1053/2889 = 0.36 | 0.73 | 0.438 | 0.030 | 0.020 | 0.180 | +0.043 |
| phasenet_scedc | P | 610/2422 = 0.25 | 0.35 | 610/1317 = 0.46 | 571/846 = 0.67 | 754/1025 = 0.74 | 0.84 | 0.568 | 0.032 | 0.033 | 0.250 | +0.034 |
| phasenet_scedc | S | 56/163 = 0.34 | 0.34 | 56/162 = 0.35 | 52/90 = 0.58 | 71/527 = 0.13 | 0.64 | 0.194 | 0.040 | 0.036 | 0.170 | +0.030 |
| phasenet_scedc | P+S | 666/2585 = 0.26 | 0.35 | 666/1479 = 0.45 | 623/936 = 0.67 | 825/1552 = 0.53 | 0.77 | 0.488 | 0.032 | 0.035 | 0.247 | +0.034 |
| eqtp_ncedc | P | 617/2422 = 0.25 | 0.36 | 617/1317 = 0.47 | 526/846 = 0.62 | 716/960 = 0.75 | 0.83 | 0.576 | 0.022 | 0.027 | 0.140 | +0.014 |
| eqtp_ncedc | S | 73/163 = 0.45 | 0.45 | 73/162 = 0.45 | 68/90 = 0.76 | 83/805 = 0.10 | 0.58 | 0.168 | 0.030 | 0.040 | 0.173 | +0.004 |
| eqtp_ncedc | P+S | 690/2585 = 0.27 | 0.36 | 690/1479 = 0.47 | 594/936 = 0.63 | 799/1765 = 0.45 | 0.72 | 0.460 | 0.028 | 0.028 | 0.140 | +0.013 |
| phasenet_instance_hn | P | 192/2422 = 0.08 | 0.11 | 192/1317 = 0.15 | 192/846 = 0.23 | 223/253 = 0.88 | 0.95 | 0.250 | 0.032 | 0.020 | 0.154 | -0.025 |
| phasenet_instance_hn | S | 24/163 = 0.15 | 0.15 | 24/162 = 0.15 | 24/90 = 0.27 | 30/210 = 0.14 | 0.80 | 0.145 | 0.060 | 0.040 | 0.137 | -0.054 |
| phasenet_instance_hn | P+S | 216/2585 = 0.08 | 0.11 | 216/1479 = 0.15 | 216/936 = 0.23 | 253/463 = 0.55 | 0.88 | 0.231 | 0.032 | 0.020 | 0.152 | -0.028 |
| phasenet_original_hn | P | 194/2422 = 0.08 | 0.11 | 194/1317 = 0.15 | 194/846 = 0.23 | 226/272 = 0.83 | 0.92 | 0.250 | 0.020 | 0.020 | 0.168 | +0.029 |
| phasenet_original_hn | S | 32/163 = 0.20 | 0.20 | 32/162 = 0.20 | 32/90 = 0.36 | 38/267 = 0.14 | 0.73 | 0.165 | 0.030 | 0.030 | 0.154 | +0.028 |
| phasenet_original_hn | P+S | 226/2585 = 0.09 | 0.12 | 226/1479 = 0.15 | 226/936 = 0.24 | 264/539 = 0.49 | 0.82 | 0.233 | 0.020 | 0.024 | 0.161 | +0.029 |
| phasenet_scedc_hn | P | 161/2422 = 0.07 | 0.09 | 161/1317 = 0.12 | 161/846 = 0.19 | 189/207 = 0.91 | 0.95 | 0.216 | 0.030 | 0.030 | 0.168 | +0.034 |
| phasenet_scedc_hn | S | 18/163 = 0.11 | 0.11 | 18/162 = 0.11 | 18/90 = 0.20 | 20/114 = 0.18 | 0.68 | 0.136 | 0.030 | 0.030 | 0.128 | -0.007 |
| phasenet_scedc_hn | P+S | 179/2585 = 0.07 | 0.09 | 179/1479 = 0.12 | 179/936 = 0.19 | 209/321 = 0.65 | 0.85 | 0.204 | 0.030 | 0.030 | 0.171 | +0.030 |
| eqtp_ncedc_hn | P | 163/2422 = 0.07 | 0.09 | 163/1317 = 0.12 | 163/846 = 0.19 | 184/217 = 0.85 | 0.88 | 0.216 | 0.022 | 0.022 | 0.110 | +0.004 |
| eqtp_ncedc_hn | S | 21/163 = 0.13 | 0.13 | 21/162 = 0.13 | 21/90 = 0.23 | 26/193 = 0.13 | 0.64 | 0.132 | 0.050 | 0.060 | 0.180 | +0.014 |
| eqtp_ncedc_hn | P+S | 184/2585 = 0.07 | 0.10 | 184/1479 = 0.12 | 184/936 = 0.20 | 210/410 = 0.51 | 0.77 | 0.200 | 0.025 | 0.025 | 0.118 | +0.005 |

### T2a P recall at complete records, by the bound sensor type

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| CN | 32 | 28/32 = 0.88 | 29/32 = 0.91 | 28/32 = 0.88 | 26/32 = 0.81 |
| DP | 7 | 7/7 = 1.00 | 7/7 = 1.00 | 5/7 = 0.71 | 7/7 = 1.00 |
| EH | 151 | 134/151 = 0.89 | 128/151 = 0.85 | 122/151 = 0.81 | 114/151 = 0.76 |
| EP | 125 | 93/125 = 0.74 | 93/125 = 0.74 | 89/125 = 0.71 | 75/125 = 0.60 |
| HH | 188 | 159/188 = 0.85 | 150/188 = 0.80 | 127/188 = 0.68 | 92/188 = 0.49 |
| HN | 343 | 269/343 = 0.78 | 267/343 = 0.78 | 200/343 = 0.58 | 212/343 = 0.62 |

### T2b P recall at 3-C stations (complete + triggered records), by bound sensor

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| CN | 32 | 28/32 = 0.88 | 29/32 = 0.91 | 28/32 = 0.88 | 26/32 = 0.81 |
| DP | 7 | 7/7 = 1.00 | 7/7 = 1.00 | 5/7 = 0.71 | 7/7 = 1.00 |
| EH | 151 | 134/151 = 0.89 | 128/151 = 0.85 | 122/151 = 0.81 | 114/151 = 0.76 |
| EP | 125 | 93/125 = 0.74 | 93/125 = 0.74 | 89/125 = 0.71 | 75/125 = 0.60 |
| HH | 188 | 159/188 = 0.85 | 150/188 = 0.80 | 127/188 = 0.68 | 92/188 = 0.49 |
| HN | 814 | 322/814 = 0.40 | 321/814 = 0.39 | 239/814 = 0.29 | 303/814 = 0.37 |

### T2c P precision by bound sensor (DL picks in window)

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| CN | 0.82 (38) | 0.85 (39) | 0.91 (33) | 0.83 (35) |
| DP | 0.60 (15) | 0.60 (15) | 0.86 (7) | 0.62 (13) |
| EH | 0.78 (192) | 0.79 (183) | 0.80 (172) | 0.74 (170) |
| EP | 0.82 (130) | 0.73 (146) | 0.82 (125) | 0.88 (95) |
| HH | 0.79 (235) | 0.70 (253) | 0.80 (183) | 0.69 (162) |
| HN | 0.67 (708) | 0.56 (854) | 0.66 (505) | 0.74 (485) |

### T2d P recall over picks WITH DATA, by the analyst's channel type

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| BH | 0 |  |  |  |  |
| CN | 29 | 22/29 = 0.76 | 23/29 = 0.79 | 20/29 = 0.69 | 21/29 = 0.72 |
| DP | 25 | 13/25 = 0.52 | 13/25 = 0.52 | 13/25 = 0.52 | 13/25 = 0.52 |
| EH | 788 | 311/788 = 0.39 | 305/788 = 0.39 | 263/788 = 0.33 | 255/788 = 0.32 |
| EP | 129 | 97/129 = 0.75 | 97/129 = 0.75 | 91/129 = 0.71 | 78/129 = 0.60 |
| HH | 186 | 157/186 = 0.84 | 148/186 = 0.80 | 125/186 = 0.67 | 92/186 = 0.49 |
| HN | 571 | 143/571 = 0.25 | 142/571 = 0.25 | 98/571 = 0.17 | 158/571 = 0.28 |

### T3a P recall at complete records by epicentral distance

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0-20 km | 256 | 210/256 = 0.82 | 214/256 = 0.84 | 190/256 = 0.74 | 188/256 = 0.73 |
| 20-40 km | 300 | 251/300 = 0.84 | 243/300 = 0.81 | 198/300 = 0.66 | 191/300 = 0.64 |
| 40-60 km | 230 | 178/230 = 0.77 | 168/230 = 0.73 | 140/230 = 0.61 | 118/230 = 0.51 |
| 60-80 km | 60 | 51/60 = 0.85 | 49/60 = 0.82 | 43/60 = 0.72 | 29/60 = 0.48 |
| >80 km | 0 |  |  |  |  |

### T3b P precision by distance

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| 0-20 km | 0.91 (298) | 0.86 (327) | 0.88 (279) | 0.86 (279) |
| 20-40 km | 0.73 (471) | 0.62 (541) | 0.72 (351) | 0.74 (375) |
| 40-60 km | 0.66 (424) | 0.55 (490) | 0.66 (310) | 0.70 (234) |
| 60-80 km | 0.52 (125) | 0.48 (132) | 0.61 (85) | 0.50 (72) |
| >80 km |  (0) |  (0) |  (0) |  (0) |

### T3c S recall at complete records by distance

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0-20 km | 77 | 65/77 = 0.84 | 65/77 = 0.84 | 45/77 = 0.58 | 60/77 = 0.78 |
| 20-40 km | 11 | 6/11 = 0.55 | 9/11 = 0.82 | 6/11 = 0.55 | 7/11 = 0.64 |
| 40-60 km | 0 |  |  |  |  |
| 60-80 km | 2 | 1/2 = 0.50 | 2/2 = 1.00 | 1/2 = 0.50 | 1/2 = 0.50 |
| >80 km | 0 |  |  |  |  |

### T4a P recall at complete records by magnitude

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| M0.5-1.0 | 39 | 28/39 = 0.72 | 32/39 = 0.82 | 21/39 = 0.54 | 21/39 = 0.54 |
| M1.0-1.5 | 62 | 40/62 = 0.65 | 44/62 = 0.71 | 32/62 = 0.52 | 26/62 = 0.42 |
| M1.5-2.0 | 89 | 79/89 = 0.89 | 77/89 = 0.87 | 64/89 = 0.72 | 47/89 = 0.53 |
| M2.0-2.5 | 173 | 101/173 = 0.58 | 106/173 = 0.61 | 82/173 = 0.47 | 84/173 = 0.49 |
| M2.5-3.0 | 178 | 159/178 = 0.89 | 142/178 = 0.80 | 128/178 = 0.72 | 107/178 = 0.60 |
| M3.0-3.6 | 305 | 283/305 = 0.93 | 273/305 = 0.90 | 244/305 = 0.80 | 241/305 = 0.79 |

### T4b S recall at complete records by magnitude

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| M0.5-1.0 | 16 | 15/16 = 0.94 | 16/16 = 1.00 | 8/16 = 0.50 | 13/16 = 0.81 |
| M1.0-1.5 | 16 | 10/16 = 0.62 | 13/16 = 0.81 | 8/16 = 0.50 | 8/16 = 0.50 |
| M1.5-2.0 | 17 | 15/17 = 0.88 | 16/17 = 0.94 | 11/17 = 0.65 | 15/17 = 0.88 |
| M2.0-2.5 | 12 | 7/12 = 0.58 | 10/12 = 0.83 | 7/12 = 0.58 | 8/12 = 0.67 |
| M2.5-3.0 | 11 | 8/11 = 0.73 | 6/11 = 0.55 | 5/11 = 0.45 | 10/11 = 0.91 |
| M3.0-3.6 | 18 | 17/18 = 0.94 | 15/18 = 0.83 | 13/18 = 0.72 | 14/18 = 0.78 |

### T4c P precision by magnitude

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| M0.5-1.0 | 0.61 (46) | 0.44 (73) | 0.53 (40) | 0.64 (33) |
| M1.0-1.5 | 0.74 (54) | 0.59 (74) | 0.65 (49) | 0.84 (31) |
| M1.5-2.0 | 0.70 (122) | 0.62 (136) | 0.76 (90) | 0.80 (60) |
| M2.0-2.5 | 0.69 (297) | 0.61 (337) | 0.68 (232) | 0.71 (207) |
| M2.5-3.0 | 0.61 (303) | 0.51 (351) | 0.67 (227) | 0.70 (187) |
| M3.0-3.6 | 0.84 (496) | 0.78 (519) | 0.83 (387) | 0.78 (442) |

### T5a P recall at complete records by time to the nearest other catalog event

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| none within 120 s | 493 | 440/493 = 0.89 | 435/493 = 0.88 | 366/493 = 0.74 | 348/493 = 0.71 |
| nearest 60-120 s | 47 | 38/47 = 0.81 | 40/47 = 0.85 | 33/47 = 0.70 | 19/47 = 0.40 |
| nearest 15-60 s | 110 | 102/110 = 0.93 | 98/110 = 0.89 | 87/110 = 0.79 | 67/110 = 0.61 |
| nearest <= 15 s | 196 | 110/196 = 0.56 | 101/196 = 0.52 | 85/196 = 0.43 | 92/196 = 0.47 |

### T5b S recall at complete records by time to the nearest other catalog event

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| none within 120 s | 54 | 50/54 = 0.93 | 53/54 = 0.98 | 38/54 = 0.70 | 48/54 = 0.89 |
| nearest 60-120 s | 6 | 4/6 = 0.67 | 5/6 = 0.83 | 3/6 = 0.50 | 4/6 = 0.67 |
| nearest 15-60 s | 4 | 4/4 = 1.00 | 1/4 = 0.25 | 2/4 = 0.50 | 3/4 = 0.75 |
| nearest <= 15 s | 26 | 14/26 = 0.54 | 17/26 = 0.65 | 9/26 = 0.35 | 13/26 = 0.50 |

### T6a P recall at 3-C stations by analyst weight code

| group | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0 | 282 | 224/282 = 0.79 | 222/282 = 0.79 | 215/282 = 0.76 | 208/282 = 0.74 |
| 1 | 336 | 195/336 = 0.58 | 194/336 = 0.58 | 167/336 = 0.50 | 179/336 = 0.53 |
| 2 | 568 | 277/568 = 0.49 | 268/568 = 0.47 | 203/568 = 0.36 | 208/568 = 0.37 |
| 3 | 131 | 47/131 = 0.36 | 44/131 = 0.34 | 25/131 = 0.19 | 22/131 = 0.17 |

### T6b P median |dt| / p95 |dt| (s) by analyst weight code

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| 0 | 0.022 / 0.062 | 0.020 / 0.090 | 0.020 / 0.120 | 0.020 / 0.087 |
| 1 | 0.020 / 0.117 | 0.029 / 0.130 | 0.030 / 0.190 | 0.020 / 0.120 |
| 2 | 0.050 / 0.193 | 0.038 / 0.240 | 0.058 / 0.320 | 0.037 / 0.188 |
| 3 | 0.060 / 0.392 | 0.084 / 0.457 | 0.080 / 0.459 | 0.060 / 0.453 |

### T6c S median |dt| / p95 |dt| (s) by analyst weight code

| group | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|
| 0 |  /  |  /  |  /  |  /  |
| 1 | 0.050 / 0.130 | 0.030 / 0.143 | 0.030 / 0.212 | 0.030 / 0.141 |
| 2 | 0.040 / 0.126 | 0.040 / 0.257 | 0.070 / 0.165 | 0.040 / 0.183 |
| 3 |  /  |  /  |  /  |  /  |

### T7 velocity sensor vs accelerometer at the same 13 stations

| model | sensor | phase | recall_all_records | recall_complete | precision | median_abs_dt | p95_abs_dt | mean_dt |
|---|---|---|---|---|---|---|---|---|
| eqtp_ncedc | main (velocity sensor) | P | 155/240 = 0.65 | 155/240 = 0.65 | 175/218 = 0.80 | 0.020 | 0.113 | +0.019 |
| eqtp_ncedc | main (velocity sensor) | S | 32/41 = 0.78 | 32/41 = 0.78 | 38/207 = 0.18 | 0.030 | 0.163 | -0.019 |
| eqtp_ncedc | hn (accelerometer) | P | 163/240 = 0.68 | 163/240 = 0.68 | 184/217 = 0.85 | 0.022 | 0.110 | +0.004 |
| eqtp_ncedc | hn (accelerometer) | S | 21/41 = 0.51 | 21/41 = 0.51 | 26/193 = 0.13 | 0.050 | 0.180 | +0.014 |
| phasenet_original | main (velocity sensor) | P | 202/240 = 0.84 | 202/240 = 0.84 | 228/275 = 0.83 | 0.020 | 0.138 | +0.032 |
| phasenet_original | main (velocity sensor) | S | 34/41 = 0.83 | 34/41 = 0.83 | 41/267 = 0.15 | 0.035 | 0.170 | +0.050 |
| phasenet_original | hn (accelerometer) | P | 194/240 = 0.81 | 194/240 = 0.81 | 226/272 = 0.83 | 0.020 | 0.168 | +0.029 |
| phasenet_original | hn (accelerometer) | S | 32/41 = 0.78 | 32/41 = 0.78 | 38/267 = 0.14 | 0.030 | 0.154 | +0.028 |
| phasenet_scedc | main (velocity sensor) | P | 173/240 = 0.72 | 173/240 = 0.72 | 194/217 = 0.89 | 0.020 | 0.118 | +0.009 |
| phasenet_scedc | main (velocity sensor) | S | 21/41 = 0.51 | 21/41 = 0.51 | 23/116 = 0.20 | 0.040 | 0.110 | +0.015 |
| phasenet_scedc | hn (accelerometer) | P | 161/240 = 0.67 | 161/240 = 0.67 | 189/207 = 0.91 | 0.030 | 0.168 | +0.034 |
| phasenet_scedc | hn (accelerometer) | S | 18/41 = 0.44 | 18/41 = 0.44 | 20/114 = 0.18 | 0.030 | 0.128 | -0.007 |
| phasenet_instance | main (velocity sensor) | P | 208/240 = 0.87 | 208/240 = 0.87 | 233/266 = 0.88 | 0.029 | 0.157 | -0.023 |
| phasenet_instance | main (velocity sensor) | S | 34/41 = 0.83 | 34/41 = 0.83 | 40/222 = 0.18 | 0.040 | 0.130 | -0.035 |
| phasenet_instance | hn (accelerometer) | P | 192/240 = 0.80 | 192/240 = 0.80 | 223/253 = 0.88 | 0.032 | 0.154 | -0.025 |
| phasenet_instance | hn (accelerometer) | S | 24/41 = 0.59 | 24/41 = 0.59 | 30/210 = 0.14 | 0.060 | 0.137 | -0.054 |

### T8 missed analyst picks at 3c_complete records, by reason

| variant | phase | model_below_minConfidence | no_P_pick_so_no_S_picker | no_S_window_covering | no_detector_trigger | peak_vetoed_as_S | trigger_not_turned_into_picker | window_picked_other_time |
|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 30 | 0 | 0 | 42 | 1 | 4 | 79 |
| phasenet_instance | S | 3 | 4 | 1 | 0 | 0 | 0 | 10 |
| phasenet_original | P | 19 | 0 | 0 | 42 | 0 | 4 | 107 |
| phasenet_original | S | 0 | 6 | 1 | 0 | 0 | 0 | 7 |
| phasenet_scedc | P | 136 | 0 | 0 | 42 | 2 | 4 | 91 |
| phasenet_scedc | S | 21 | 10 | 1 | 0 | 0 | 0 | 6 |
| eqtp_ncedc | P | 144 | 0 | 0 | 37 | 2 | 18 | 119 |
| eqtp_ncedc | S | 1 | 7 | 0 | 0 | 0 | 0 | 14 |

### T8 missed analyst picks at 3c_incomplete records, by reason

| variant | phase | model_below_minConfidence | no_P_pick_so_no_S_picker | no_S_window_covering | no_detector_trigger | record_starts_too_late | trigger_not_turned_into_picker | window_picked_other_time |
|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 2 | 0 | 0 | 2 | 410 | 2 | 2 |
| phasenet_instance | S | 0 | 64 | 0 | 0 | 0 | 0 | 1 |
| phasenet_original | P | 1 | 0 | 0 | 2 | 410 | 2 | 2 |
| phasenet_original | S | 0 | 64 | 0 | 0 | 0 | 0 | 0 |
| phasenet_scedc | P | 18 | 0 | 0 | 2 | 410 | 2 | 0 |
| phasenet_scedc | S | 1 | 65 | 0 | 0 | 0 | 0 | 2 |
| eqtp_ncedc | P | 10 | 0 | 0 | 2 | 342 | 4 | 22 |
| eqtp_ncedc | S | 0 | 59 | 8 | 0 | 0 | 0 | 0 |

### T8c P misses below minConfidence at complete records: best model value in the covering windows

| variant | (0.0, 0.1] | (0.1, 0.2] | (0.2, 0.3] | (0.3, 0.4] |
|---|---|---|---|---|
| eqtp_ncedc | 81 | 20 | 17 | 15 |
| phasenet_instance | 5 | 9 | 12 | 4 |
| phasenet_original | 3 | 5 | 8 | 3 |
| phasenet_scedc | 35 | 26 | 39 | 36 |

### T9 unmatched DL picks inside the event windows, by class

| variant | phase | near_duplicate | noise_or_other | phase_confusion | plausible_no_analyst_pick | plausible_other_event_arrival | reference_outlier | timing_disagreement |
|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 32 | 58 | 12 | 207 | 37 | 2 | 11 |
| phasenet_instance | S | 30 | 245 | 4 | 474 | 117 | 0 | 0 |
| phasenet_original | P | 31 | 187 | 30 | 219 | 55 | 2 | 18 |
| phasenet_original | S | 54 | 459 | 2 | 623 | 156 | 0 | 0 |
| phasenet_scedc | P | 33 | 91 | 26 | 88 | 15 | 2 | 16 |
| phasenet_scedc | S | 17 | 146 | 29 | 214 | 50 | 0 | 0 |
| eqtp_ncedc | P | 109 | 35 | 4 | 70 | 12 | 1 | 13 |
| eqtp_ncedc | S | 105 | 211 | 23 | 350 | 33 | 0 | 0 |

### T10 DL picks outside the event windows

| model | phase | outside_window | other_catalog_event | in_common_noise_span | station_hours | false_per_station_hour | HH | HN | EH | EP |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 200 | 56 | 27 (8 coincident) | 25.0 | 1.08 | 2.05 | 0.58 | 1.54 | 1.23 |
| phasenet_instance | S | 96 | 77 | 4 (2 coincident) | 25.0 | 0.16 | 0.19 | 0.00 | 0.00 | 0.92 |
| phasenet_original | P | 364 | 74 | 98 (42 coincident) | 25.0 | 3.93 | 5.59 | 3.41 | 3.08 | 4.00 |
| phasenet_original | S | 225 | 122 | 46 (26 coincident) | 25.0 | 1.84 | 1.86 | 1.75 | 1.85 | 2.16 |
| phasenet_scedc | P | 236 | 48 | 46 (2 coincident) | 25.0 | 1.84 | 3.54 | 1.50 | 0.62 | 1.23 |
| phasenet_scedc | S | 65 | 37 | 8 (0 coincident) | 25.0 | 0.32 | 0.19 | 0.33 | 0.00 | 0.62 |
| eqtp_ncedc | P | 182 | 53 | 32 (5 coincident) | 25.0 | 1.28 | 3.17 | 0.58 | 1.54 | 0.92 |
| eqtp_ncedc | S | 52 | 38 | 9 (1 coincident) | 25.0 | 0.36 | 0.93 | 0.17 | 0.31 | 0.31 |

### T11 cost (whole scautopick process, /usr/bin/time; 26 runs per variant)

| model | cpu_s | station_hours | cpu_s_per_station_hour | triggers | P_windows | S_windows | ms_per_window | peak_MB | startup_probe_cpu_s |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | 40.6 | 177.1 | 0.229 | 5114 | 4033 | 6036 | 3.8 | 304 | 0.10 |
| phasenet_original | 44.2 | 177.1 | 0.250 | 5114 | 4033 | 7313 | 3.7 | 308 | 0.09 |
| phasenet_scedc | 38.3 | 177.1 | 0.216 | 5114 | 4033 | 4958 | 4.0 | 260 | 0.10 |
| eqtp_ncedc | 694.2 | 177.1 | 3.920 | 5114 | 2259 | 3852 | 113.2 | 364 | 0.10 |

### T12 eqtp_ncedc: P polarity vs analyst first motion (matched P picks with analyst U/D)

analyst first motions: 1951 in total, 1120 at 3-C stations, 575 matched; stations with >= 3 comparisons: 49; of those always opposite: [('BK.MHDL', 8, 'Inverted'), ('BK.SBRN', 6, 'Inverted'), ('NP.1804', 3, 'Direct')]

| group | n | coverage_0p5 | agree_0p5 | agree_raw_counts_0p5 | coverage_0p7 | agree_0p7 | agree_raw_counts_0p7 |
|---|---|---|---|---|---|---|---|
| all | 575 | 0.83 | 0.77 | 0.83 | 0.62 | 0.83 | 0.89 |
| onset_I | 384 | 0.87 | 0.88 | 0.92 | 0.72 | 0.91 | 0.95 |
| onset_E | 191 | 0.73 | 0.53 | 0.61 | 0.41 | 0.56 | 0.70 |
| weight_0 | 208 | 0.90 | 0.91 | 0.94 | 0.80 | 0.93 | 0.95 |
| weight_1 | 176 | 0.84 | 0.84 | 0.88 | 0.62 | 0.89 | 0.94 |
| weight_2 | 191 | 0.73 | 0.53 | 0.61 | 0.41 | 0.56 | 0.70 |
| same_channel | 413 | 0.83 | 0.76 | 0.82 | 0.62 | 0.82 | 0.89 |
| other_channel | 162 | 0.82 | 0.82 | 0.85 | 0.62 | 0.87 | 0.90 |
| direct_sense | 524 | 0.83 | 0.83 | 0.83 | 0.61 | 0.90 | 0.90 |
| inverted_sense | 51 | 0.82 | 0.21 | 0.79 | 0.67 | 0.21 | 0.79 |
| dist_0-20 km | 217 | 0.88 | 0.82 | 0.87 | 0.74 | 0.86 | 0.91 |
| dist_20-40 km | 211 | 0.80 | 0.88 | 0.88 | 0.59 | 0.93 | 0.93 |
| dist_40-60 km | 123 | 0.79 | 0.52 | 0.66 | 0.49 | 0.58 | 0.77 |
| dist_60-80 km | 24 | 0.83 | 0.75 | 0.80 | 0.46 | 0.82 | 0.91 |
| mag_M0.5-1.0 | 17 | 0.94 | 0.75 | 0.94 | 0.82 | 0.79 | 0.93 |
| mag_M1.0-1.5 | 24 | 0.83 | 0.85 | 0.85 | 0.62 | 0.87 | 0.93 |
| mag_M1.5-2.0 | 45 | 0.82 | 0.89 | 0.95 | 0.64 | 0.93 | 0.97 |
| mag_M2.0-2.5 | 83 | 0.77 | 0.84 | 0.83 | 0.64 | 0.85 | 0.83 |
| mag_M2.5-3.0 | 120 | 0.76 | 0.68 | 0.70 | 0.53 | 0.75 | 0.80 |
| mag_M3.0-3.6 | 286 | 0.86 | 0.77 | 0.84 | 0.63 | 0.85 | 0.92 |
| bound_CN | 25 | 0.84 | 0.38 | 0.81 | 0.72 | 0.39 | 0.83 |
| bound_DP | 5 | 0.80 | 1.00 | 1.00 | 0.80 | 1.00 | 1.00 |
| bound_EH | 105 | 0.90 | 0.86 | 0.86 | 0.68 | 0.93 | 0.93 |
| bound_EP | 68 | 0.85 | 0.62 | 0.88 | 0.71 | 0.62 | 0.90 |
| bound_HH | 90 | 0.79 | 0.93 | 0.93 | 0.64 | 0.97 | 0.97 |
| bound_HN | 282 | 0.80 | 0.76 | 0.76 | 0.56 | 0.85 | 0.85 |

### T12 eqtp_ncedc_hn: P polarity vs analyst first motion (matched P picks with analyst U/D)

analyst first motions: 1951 in total, 1120 at 3-C stations, 156 matched; stations with >= 3 comparisons: 12; of those always opposite: []

| group | n | coverage_0p5 | agree_0p5 | agree_raw_counts_0p5 | coverage_0p7 | agree_0p7 | agree_raw_counts_0p7 |
|---|---|---|---|---|---|---|---|
| all | 156 | 0.84 | 0.94 | 0.95 | 0.72 | 0.95 | 0.96 |
| onset_I | 133 | 0.89 | 0.95 | 0.95 | 0.79 | 0.95 | 0.95 |
| onset_E | 23 | 0.52 | 0.83 | 0.92 | 0.35 | 0.88 | 1.00 |
| weight_0 | 95 | 0.93 | 0.94 | 0.94 | 0.82 | 0.94 | 0.94 |
| weight_1 | 38 | 0.82 | 0.97 | 0.97 | 0.71 | 1.00 | 1.00 |
| weight_2 | 23 | 0.52 | 0.83 | 0.92 | 0.35 | 0.88 | 1.00 |
| same_channel | 9 | 0.67 | 0.83 | 1.00 | 0.67 | 0.83 | 1.00 |
| other_channel | 147 | 0.85 | 0.94 | 0.94 | 0.73 | 0.95 | 0.95 |
| direct_sense | 154 | 0.84 | 0.95 | 0.95 | 0.73 | 0.96 | 0.96 |
| inverted_sense | 2 | 0.50 | 0.00 | 1.00 | 0.50 | 0.00 | 1.00 |
| dist_0-20 km | 66 | 0.91 | 0.95 | 0.95 | 0.73 | 0.96 | 0.96 |
| dist_20-40 km | 83 | 0.81 | 0.97 | 0.97 | 0.73 | 0.98 | 0.98 |
| dist_40-60 km | 6 | 0.50 | 0.33 | 0.33 | 0.50 | 0.33 | 0.33 |
| dist_60-80 km | 1 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| mag_M0.5-1.0 | 7 | 0.71 | 0.60 | 0.60 | 0.57 | 0.75 | 0.75 |
| mag_M1.0-1.5 | 12 | 0.67 | 0.88 | 0.88 | 0.50 | 0.83 | 0.83 |
| mag_M1.5-2.0 | 19 | 0.79 | 1.00 | 1.00 | 0.68 | 1.00 | 1.00 |
| mag_M2.0-2.5 | 30 | 0.83 | 1.00 | 1.00 | 0.70 | 1.00 | 1.00 |
| mag_M2.5-3.0 | 37 | 0.84 | 0.94 | 0.94 | 0.65 | 0.96 | 0.96 |
| mag_M3.0-3.6 | 51 | 0.92 | 0.94 | 0.96 | 0.88 | 0.93 | 0.96 |
| bound_CN | 5 | 0.80 | 1.00 | 1.00 | 0.80 | 1.00 | 1.00 |
| bound_HN | 151 | 0.84 | 0.94 | 0.94 | 0.72 | 0.94 | 0.95 |

### T13 analyst first motions on inverted channels vs similar rays on direct channels

neighbours: same event, direct channel, |daz| <= 10.0, |dtakeoff| <= 10.0, >= 2, majority >= 70 %; inverted-channel picks 941, tested 148, same as neighbours 0.32; control (direct channels) 809 tests, 0.70

| network | station | channel | dip | gain | n_tests | frac_same_as_direct_neighbours |
|---|---|---|---|---|---|---|
| BK | MHDL | EP1 | -90.0 | -57462000.0 | 50 | 0.12 |
| BK | OXMT | EP1 | -90.0 | -57462000.0 | 44 | 0.30 |
| BK | SBRN | EP1 | -90.0 | -57462000.0 | 16 | 0.50 |
| BK | SM2B | CN1 | -90.0 | -4279080.0 | 4 | 0.25 |
| BK | VALB | EP1 | -90.0 | -2097150000.0 | 12 | 0.58 |
| NN | LUL | EHZ | -90.0 | -408204375480.0 | 4 | 0.50 |

### T14 SeisBench EQTP('ncedc') v1 vs the plugin, events ['72540765', '72542520', '72541095', '72545170', '72537850']

same weights: True (max |ONNX - torch| on identical input: 2.0e-05); plugin normalisation changes outputs by <= 0.41; P peak shifts [-1, 0, 0, 0, 1, 0, 0, -1] samples; same polarity in 8/8 windows; SeisBench classify CPU 231.2 s for 40.54 station-hours (5.70 per station-hour, 1 thread)

| phase | method | picks | recall_3C | recall_complete | recall_triggered | precision | median_abs_dt | polarity_coverage | polarity_agree |
|---|---|---|---|---|---|---|---|---|---|
| P | plugin | 329 | 158/380 = 0.42 | 0.58 | 0.19 | 0.78 | 0.030 | 0.82 | 0.76 |
| P | seisbench | 678 | 321/380 = 0.84 | 0.82 | 0.88 | 0.74 | 0.032 | 0.85 | 0.82 |
| S | plugin | 249 | 12/27 = 0.44 | 0.67 | 0.27 | 0.06 | 0.030 |  |  |
| S | seisbench | 779 | 25/27 = 0.93 | 0.92 | 0.93 | 0.05 | 0.048 |  |  |

### T15 the plugin's own eqtp_ncedc windows re-run with SeisBench's normalisation

| windows | n | reach_0p4_plugin_norm | reach_0p4_seisbench_norm | median_P_plugin_norm | median_P_seisbench_norm | n_100Hz | reach_100Hz_plugin | reach_100Hz_seisbench |
|---|---|---|---|---|---|---|---|---|
| missed | 154 | 2 | 13 | 0.015 | 0.014 | 118 | 0 | 8 |
| matched | 617 | 614 | 604 | 0.956 | 0.956 | 393 | 392 | 384 |

reproduction check (logged best P vs recomputed, 100 Hz windows): max |diff| 0.0050

P: 278 plugin-SeisBench pairs; median |dt| 0.020 s; within 0.02 s 0.54; within 0.05 s 0.83; p95 0.130; mean -0.008; max 0.44; polarity both set 166, agree 0.93
   analyst picks found only by SeisBench / only by the plugin / neither: 168 / 5 / 54; only-SeisBench by tier | plugin reason: {'3c_incomplete | record_starts_too_late': 100, '3c_complete | window_picked_other_time': 43, '3c_incomplete | window_picked_other_time': 7, '3c_complete | no_detector_trigger': 6, '3c_complete | trigger_not_turned_into_picker': 6, '3c_complete | model_below_minConfidence': 3, '3c_incomplete | trigger_not_turned_into_picker': 2, '3c_incomplete | model_below_minConfidence': 1}

S: 199 plugin-SeisBench pairs; median |dt| 0.020 s; within 0.02 s 0.52; within 0.05 s 0.82; p95 0.111; mean +0.007; max 0.59
   analyst picks found only by SeisBench / only by the plugin / neither: 13 / 0 / 2; only-SeisBench by tier | plugin reason: {'3c_incomplete | no_P_pick_so_no_S_picker': 10, '3c_complete | window_picked_other_time': 2, '3c_complete | no_P_pick_so_no_S_picker': 1}
