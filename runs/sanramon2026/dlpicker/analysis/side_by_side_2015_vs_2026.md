| section | quantity | 2015 (step 12) | 2025-26 (step 14) |
|---|---|---|---|
| data | stations with data in the playback files | 217 | 226 |
| data | stations bound (main set) | 181 | 204 |
| data | main set by sensor | HN 145, HH 15, EP 9, EH 9, CN 2, DP 1 | HN 152, HH 34, EP 7, EH 7, DP 2, CN 2 |
| data | stations not bound (no usable 3-C sensor) | 36 | 22 |
| data | hn set (accelerometer at velocity-sensor stations) | 13 | 28 |
| data | main-set station-event records complete | 1789/3291 = 0.54 | 4625/4681 = 0.99 |
| data | station-hours (main set, all records) | 177.1 | 310.0 |
| reference | usable analyst P picks (weight 0-3) | 2422 | 3329 |
| reference |   P: no waveform / no 3-C sensor / 3-C triggered / 3-C complete | 694 / 411 / 471 / 846 | 1194 / 261 / 13 / 1861 |
| reference | usable analyst S picks (weight 0-3) | 163 | 229 |
| reference |   S: no waveform / no 3-C sensor / 3-C triggered / 3-C complete | 0 / 1 / 72 / 90 | 1 / 15 / 0 / 213 |
| phasenet_instance | P recall: all / with data / 3-C / complete | 0.31 / 0.43 / 0.56 / 0.82 | 0.48 / 0.75 / 0.85 / 0.86 |
| phasenet_instance | P precision / counting plausible | 0.73 / 0.91 | 0.72 / 0.92 |
| phasenet_instance | P median \|dt\| / p95 \|dt\| / mean dt (s) | 0.030 / 0.170 / -0.020 | 0.040 / 0.210 / -0.025 |
| phasenet_instance | S recall: 3-C / complete | 0.49 / 0.80 | 0.91 / 0.91 |
| phasenet_instance | S precision | 0.10 | 0.13 |
| phasenet_instance | pooled P+S F1 | 0.505 | 0.615 |
| phasenet_instance | P recall complete: no event within 120 s / nearest <= 15 s | 0.89 (493) / 0.56 (196) | 0.89 (858) / 0.64 (365) |
| phasenet_instance | overlap-test event P recall (complete) | 2/46 = 0.04 | 15/137 = 0.11 |
| phasenet_instance | false P picks per station-hour (noise span) | 1.08 (27 in 25.0 h) | 0.87 (49 in 56.0 h) |
| phasenet_instance | CPU s per station-hour / ms per window | 0.229 / 3.8 | 0.215 / 3.1 |
| phasenet_instance | P recall at hn stations: velocity / accelerometer | 0.87 / 0.80 (n 240) | 0.83 / 0.72 (n 411) |
| phasenet_instance | missed P at complete records: below minConf / no trigger / other window picked | 30 / 42 / 79 (of 156) | 33 / 55 / 159 (of 264) |
| phasenet_original | P recall: all / with data / 3-C / complete | 0.30 / 0.42 / 0.55 / 0.80 | 0.48 / 0.75 / 0.85 / 0.85 |
| phasenet_original | P precision / counting plausible | 0.64 / 0.82 | 0.67 / 0.84 |
| phasenet_original | P median \|dt\| / p95 \|dt\| / mean dt (s) | 0.028 / 0.186 / +0.042 | 0.033 / 0.230 / +0.046 |
| phasenet_original | S recall: 3-C / complete | 0.52 / 0.84 | 0.93 / 0.93 |
| phasenet_original | S precision | 0.08 | 0.10 |
| phasenet_original | pooled P+S F1 | 0.438 | 0.542 |
| phasenet_original | P recall complete: no event within 120 s / nearest <= 15 s | 0.88 (493) / 0.52 (196) | 0.88 (858) / 0.65 (365) |
| phasenet_original | overlap-test event P recall (complete) | 2/46 = 0.04 | 26/137 = 0.19 |
| phasenet_original | false P picks per station-hour (noise span) | 3.93 (98 in 25.0 h) | 3.89 (218 in 56.0 h) |
| phasenet_original | CPU s per station-hour / ms per window | 0.250 / 3.7 | 0.225 / 2.9 |
| phasenet_original | P recall at hn stations: velocity / accelerometer | 0.84 / 0.81 (n 240) | 0.83 / 0.75 (n 411) |
| phasenet_original | missed P at complete records: below minConf / no trigger / other window picked | 19 / 42 / 107 (of 172) | 38 / 55 / 162 (of 272) |
| phasenet_scedc | P recall: all / with data / 3-C / complete | 0.25 / 0.35 / 0.46 / 0.67 | 0.42 / 0.65 / 0.74 / 0.75 |
| phasenet_scedc | P precision / counting plausible | 0.74 / 0.84 | 0.75 / 0.85 |
| phasenet_scedc | P median \|dt\| / p95 \|dt\| / mean dt (s) | 0.032 / 0.250 / +0.034 | 0.047 / 0.320 / +0.054 |
| phasenet_scedc | S recall: 3-C / complete | 0.35 / 0.58 | 0.66 / 0.66 |
| phasenet_scedc | S precision | 0.13 | 0.17 |
| phasenet_scedc | pooled P+S F1 | 0.488 | 0.640 |
| phasenet_scedc | P recall complete: no event within 120 s / nearest <= 15 s | 0.74 (493) / 0.43 (196) | 0.74 (858) / 0.62 (365) |
| phasenet_scedc | overlap-test event P recall (complete) | 4/46 = 0.09 | 54/137 = 0.39 |
| phasenet_scedc | false P picks per station-hour (noise span) | 1.84 (46 in 25.0 h) | 2.91 (163 in 56.0 h) |
| phasenet_scedc | CPU s per station-hour / ms per window | 0.216 / 4.0 | 0.199 / 3.1 |
| phasenet_scedc | P recall at hn stations: velocity / accelerometer | 0.72 / 0.67 (n 240) | 0.76 / 0.60 (n 411) |
| phasenet_scedc | missed P at complete records: below minConf / no trigger / other window picked | 136 / 42 / 91 (of 275) | 286 / 55 / 107 (of 473) |
| eqtp_ncedc | P recall: all / with data / 3-C / complete | 0.25 / 0.36 / 0.47 / 0.62 | 0.41 / 0.65 / 0.74 / 0.74 |
| eqtp_ncedc | P precision / counting plausible | 0.75 / 0.83 | 0.70 / 0.77 |
| eqtp_ncedc | P median \|dt\| / p95 \|dt\| / mean dt (s) | 0.022 / 0.140 / +0.014 | 0.030 / 0.171 / +0.018 |
| eqtp_ncedc | S recall: 3-C / complete | 0.45 / 0.76 | 0.89 / 0.89 |
| eqtp_ncedc | S precision | 0.10 | 0.12 |
| eqtp_ncedc | pooled P+S F1 | 0.460 | 0.542 |
| eqtp_ncedc | P recall complete: no event within 120 s / nearest <= 15 s | 0.71 (493) / 0.47 (196) | 0.66 (858) / 0.78 (365) |
| eqtp_ncedc | overlap-test event P recall (complete) | 13/46 = 0.28 | 109/137 = 0.80 |
| eqtp_ncedc | false P picks per station-hour (noise span) | 1.28 (32 in 25.0 h) | 1.34 (75 in 56.0 h) |
| eqtp_ncedc | CPU s per station-hour / ms per window | 3.920 / 113.2 | 5.013 / 110.4 |
| eqtp_ncedc | P recall at hn stations: velocity / accelerometer | 0.65 / 0.68 (n 240) | 0.63 / 0.67 (n 411) |
| eqtp_ncedc | missed P at complete records: below minConf / no trigger / other window picked | 144 / 37 / 119 (of 320) | 334 / 47 / 82 (of 484) |
| ranking | best model by the fixed rule (pooled F1) | phasenet_instance 0.505, phasenet_scedc 0.488, eqtp_ncedc 0.460, phasenet_original 0.438 | phasenet_scedc 0.640, phasenet_instance 0.615, phasenet_original 0.542, eqtp_ncedc 0.542 |
| polarity (eqtp_ncedc) | threshold 0.5: coverage / agreement, all | 0.83 / 0.77 (n 575) | 0.88 / 0.87 (n 1065) |
| polarity (eqtp_ncedc) | threshold 0.5: agreement normal / inverted channels | 0.83 (n 524) / 0.21 (n 51) | 0.89 (n 1039) / 0.04 (n 26) |
| polarity (eqtp_ncedc) | threshold 0.5: agreement impulsive / emergent | 0.88 / 0.53 | 0.87 / 1.00 |
| polarity (eqtp_ncedc) | threshold 0.7: coverage / agreement, all | 0.62 / 0.83 (n 575) | 0.72 / 0.91 (n 1065) |
| polarity (eqtp_ncedc) | threshold 0.7: agreement normal / inverted channels | 0.90 (n 524) / 0.21 (n 51) | 0.93 (n 1039) / 0.06 (n 26) |
| polarity (eqtp_ncedc) | threshold 0.7: agreement impulsive / emergent | 0.91 / 0.56 | 0.91 / 1.00 |
| polarity reference check | analyst first motions on inverted channels same as similar rays | 0.32 (148 tests); control 0.70 (809) | 0.24 (147 tests); control 0.82 (595) |
