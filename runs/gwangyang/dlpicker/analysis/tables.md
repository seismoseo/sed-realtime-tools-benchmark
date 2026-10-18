### T1 per model and phase

| model | phase | recall | recall_wo_ref_outliers | precision | precision_counting_plausible | F1 | median_abs_dt | MAD | p95_abs_dt | mean_dt |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | P | 326/360 = 0.91 | 0.93 | 326/412 = 0.79 | 0.90 | 0.845 | 0.030 | 0.015 | 0.109 | +0.040 |
| phasenet_original | P+S | 672/763 = 0.88 | 0.90 | 672/809 = 0.83 | 0.91 | 0.855 | 0.025 | 0.010 | 0.088 | +0.032 |
| phasenet_original | S | 346/403 = 0.86 | 0.87 | 346/397 = 0.87 | 0.93 | 0.865 | 0.025 | 0.010 | 0.060 | +0.024 |
| phasenet_instance | P | 303/360 = 0.84 | 0.86 | 303/360 = 0.84 | 0.90 | 0.842 | 0.020 | 0.015 | 0.080 | -0.019 |
| phasenet_instance | P+S | 608/763 = 0.80 | 0.81 | 608/692 = 0.88 | 0.92 | 0.836 | 0.045 | 0.025 | 0.140 | -0.046 |
| phasenet_instance | S | 305/403 = 0.76 | 0.77 | 305/332 = 0.92 | 0.95 | 0.830 | 0.065 | 0.020 | 0.164 | -0.072 |
| eqtransformer_stead | P | 265/360 = 0.74 | 0.76 | 265/292 = 0.91 | 0.92 | 0.813 | 0.030 | 0.020 | 0.074 | -0.021 |
| eqtransformer_stead | P+S | 527/763 = 0.69 | 0.71 | 527/584 = 0.90 | 0.92 | 0.782 | 0.035 | 0.020 | 0.090 | -0.029 |
| eqtransformer_stead | S | 262/403 = 0.65 | 0.66 | 262/292 = 0.90 | 0.92 | 0.754 | 0.040 | 0.025 | 0.104 | -0.037 |
| phasenet_stead | P | 239/360 = 0.66 | 0.68 | 239/265 = 0.90 | 0.97 | 0.765 | 0.020 | 0.015 | 0.075 | -0.015 |
| phasenet_stead | P+S | 483/763 = 0.63 | 0.65 | 483/527 = 0.92 | 0.97 | 0.749 | 0.020 | 0.015 | 0.074 | -0.021 |
| phasenet_stead | S | 244/403 = 0.61 | 0.62 | 244/262 = 0.93 | 0.97 | 0.734 | 0.025 | 0.010 | 0.070 | -0.028 |
| phasenet_instance_fast | P | 311/360 = 0.86 | 0.88 | 311/398 = 0.78 | 0.87 | 0.821 | 0.025 | 0.015 | 0.085 | -0.021 |
| phasenet_instance_fast | P+S | 623/763 = 0.82 | 0.83 | 623/736 = 0.85 | 0.91 | 0.831 | 0.045 | 0.025 | 0.140 | -0.045 |
| phasenet_instance_fast | S | 312/403 = 0.77 | 0.79 | 312/338 = 0.92 | 0.96 | 0.842 | 0.065 | 0.020 | 0.160 | -0.070 |

### T2 by_magnitude

| model | phase | ML<1.5 recall | ML<1.5 prec. | ML<1.5 p95|dt| | ML>=1.5 recall | ML>=1.5 prec. | ML>=1.5 p95|dt| |
|---|---|---|---|---|---|---|---|
| phasenet_original | P | 0.82 (100/122) | 0.64 | 0.137 | 0.95 (226/238) | 0.89 | 0.100 |
| phasenet_original | S | 0.76 (125/165) | 0.86 | 0.065 | 0.93 (221/238) | 0.88 | 0.060 |
| phasenet_instance | P | 0.65 (79/122) | 0.69 | 0.085 | 0.94 (224/238) | 0.91 | 0.076 |
| phasenet_instance | S | 0.55 (90/165) | 0.95 | 0.139 | 0.90 (215/238) | 0.91 | 0.171 |
| eqtransformer_stead | P | 0.49 (60/122) | 0.94 | 0.065 | 0.86 (205/238) | 0.90 | 0.075 |
| eqtransformer_stead | S | 0.38 (62/165) | 0.97 | 0.100 | 0.84 (200/238) | 0.88 | 0.105 |
| phasenet_stead | P | 0.43 (52/122) | 0.75 | 0.067 | 0.79 (187/238) | 0.95 | 0.075 |
| phasenet_stead | S | 0.39 (64/165) | 0.94 | 0.062 | 0.76 (180/238) | 0.93 | 0.076 |
| phasenet_instance_fast | P | 0.71 (87/122) | 0.56 | 0.088 | 0.94 (224/238) | 0.92 | 0.080 |
| phasenet_instance_fast | S | 0.61 (100/165) | 0.92 | 0.150 | 0.89 (212/238) | 0.93 | 0.162 |

### T2 by_distance

| model | phase | <30 km recall | <30 km prec. | <30 km p95|dt| | 30-60 km recall | 30-60 km prec. | 30-60 km p95|dt| | >60 km recall | >60 km prec. | >60 km p95|dt| |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | P | 0.95 (63/66) | 0.94 | 0.040 | 0.93 (114/123) | 0.88 | 0.106 | 0.87 (149/171) | 0.69 | 0.133 |
| phasenet_original | S | 0.96 (64/67) | 0.96 | 0.039 | 0.90 (121/134) | 0.95 | 0.055 | 0.80 (161/202) | 0.80 | 0.065 |
| phasenet_instance | P | 0.89 (59/66) | 0.91 | 0.045 | 0.80 (99/123) | 0.92 | 0.055 | 0.85 (145/171) | 0.78 | 0.118 |
| phasenet_instance | S | 0.90 (60/67) | 0.92 | 0.085 | 0.75 (101/134) | 0.94 | 0.110 | 0.71 (144/202) | 0.90 | 0.184 |
| eqtransformer_stead | P | 0.89 (59/66) | 0.88 | 0.060 | 0.71 (87/123) | 0.91 | 0.075 | 0.70 (119/171) | 0.92 | 0.093 |
| eqtransformer_stead | S | 0.90 (60/67) | 0.90 | 0.065 | 0.65 (87/134) | 0.91 | 0.090 | 0.57 (115/202) | 0.89 | 0.120 |
| phasenet_stead | P | 0.85 (56/66) | 0.92 | 0.026 | 0.70 (86/123) | 0.93 | 0.070 | 0.57 (97/171) | 0.87 | 0.086 |
| phasenet_stead | S | 0.85 (57/67) | 0.93 | 0.045 | 0.66 (89/134) | 0.97 | 0.065 | 0.49 (98/202) | 0.90 | 0.110 |
| phasenet_instance_fast | P | 0.88 (58/66) | 0.97 | 0.050 | 0.86 (106/123) | 0.88 | 0.080 | 0.86 (147/171) | 0.68 | 0.102 |
| phasenet_instance_fast | S | 0.84 (56/67) | 0.97 | 0.075 | 0.83 (111/134) | 0.95 | 0.115 | 0.72 (145/202) | 0.89 | 0.180 |

### T2 by_sensor

| model | phase | HH recall | HH prec. | HH p95|dt| | HG recall | HG prec. | HG p95|dt| | EL recall | EL prec. | EL p95|dt| |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | P | 0.89 (92/103) | 0.76 | 0.102 | 0.91 (201/221) | 0.79 | 0.110 | 0.92 (33/36) | 0.94 | 0.121 |
| phasenet_original | S | 0.82 (98/120) | 0.87 | 0.058 | 0.89 (218/244) | 0.88 | 0.060 | 0.77 (30/39) | 0.86 | 0.060 |
| phasenet_instance | P | 0.80 (82/103) | 0.83 | 0.065 | 0.85 (188/221) | 0.83 | 0.080 | 0.92 (33/36) | 0.97 | 0.081 |
| phasenet_instance | S | 0.67 (80/120) | 0.90 | 0.135 | 0.80 (196/244) | 0.92 | 0.166 | 0.74 (29/39) | 0.94 | 0.157 |
| eqtransformer_stead | P | 0.63 (65/103) | 0.87 | 0.063 | 0.77 (170/221) | 0.92 | 0.070 | 0.83 (30/36) | 0.91 | 0.156 |
| eqtransformer_stead | S | 0.56 (67/120) | 0.89 | 0.087 | 0.68 (167/244) | 0.91 | 0.103 | 0.72 (28/39) | 0.85 | 0.149 |
| phasenet_stead | P | 0.59 (61/103) | 0.92 | 0.055 | 0.69 (152/221) | 0.88 | 0.075 | 0.72 (26/36) | 0.96 | 0.105 |
| phasenet_stead | S | 0.53 (63/120) | 0.95 | 0.045 | 0.64 (157/244) | 0.93 | 0.070 | 0.62 (24/39) | 0.89 | 0.109 |
| phasenet_instance_fast | P | 0.79 (81/103) | 0.74 | 0.092 | 0.89 (196/221) | 0.79 | 0.080 | 0.94 (34/36) | 0.87 | 0.141 |
| phasenet_instance_fast | S | 0.69 (83/120) | 0.91 | 0.143 | 0.82 (201/244) | 0.93 | 0.160 | 0.72 (28/39) | 0.88 | 0.156 |

### T3 outside the event windows

| model | P_outside | S_outside | other_catalog_event | coincident | isolated | station_hours | P_per_station_hour | S_per_station_hour | isolated_P_per_station_hour |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | 69 | 23 | 8 | 16 | 68 | 49.4 | 1.26 | 0.45 | 1.07 |
| phasenet_instance | 39 | 5 | 9 | 9 | 26 | 49.4 | 0.63 | 0.08 | 0.51 |
| eqtransformer_stead | 2 | 0 | 0 | 0 | 2 | 47.2 | 0.04 | 0.00 | 0.04 |
| phasenet_stead | 7 | 2 | 3 | 0 | 6 | 49.4 | 0.08 | 0.04 | 0.08 |
| phasenet_instance_fast | 144 | 12 | 20 | 39 | 97 | 50.3 | 2.48 | 0.22 | 1.79 |

### T4 unmatched DL picks inside the windows, by class (all 11 events)

| variant | phase | near_duplicate | noise_or_other | phase_confusion | plausible_missed_by_reference | reference_outlier | timing_disagreement |
|---|---|---|---|---|---|---|---|
| phasenet_original | P | 16 | 12 | 13 | 43 | 2 | 0 |
| phasenet_original | S | 17 | 11 | 1 | 20 | 2 | 0 |
| phasenet_instance | P | 16 | 5 | 14 | 20 | 2 | 0 |
| phasenet_instance | S | 16 | 1 | 1 | 5 | 4 | 0 |
| eqtransformer_stead | P | 24 | 0 | 0 | 3 | 0 | 0 |
| eqtransformer_stead | S | 24 | 0 | 0 | 4 | 2 | 0 |
| phasenet_stead | P | 9 | 0 | 0 | 17 | 0 | 0 |
| phasenet_stead | S | 9 | 0 | 0 | 7 | 2 | 0 |
| phasenet_instance_fast | P | 10 | 15 | 26 | 32 | 3 | 1 |
| phasenet_instance_fast | S | 12 | 1 | 1 | 9 | 3 | 0 |

#### T4b event 20210828133922

| variant | phase | near_duplicate | noise_or_other | phase_confusion | plausible_missed_by_reference |
|---|---|---|---|---|---|
| eqtransformer_stead | P | 0 | 0 | 0 | 1 |
| phasenet_instance | P | 0 | 2 | 1 | 2 |
| phasenet_instance_fast | P | 1 | 3 | 7 | 5 |
| phasenet_instance_fast | S | 1 | 0 | 0 | 1 |
| phasenet_original | P | 0 | 0 | 1 | 10 |
| phasenet_original | S | 0 | 1 | 0 | 0 |
| phasenet_stead | P | 0 | 0 | 0 | 6 |

#### T4b event 20260203021535

| variant | phase | noise_or_other | phase_confusion | plausible_missed_by_reference |
|---|---|---|---|---|
| phasenet_instance | P | 0 | 2 | 0 |
| phasenet_instance_fast | P | 1 | 4 | 1 |
| phasenet_original | P | 0 | 0 | 1 |
| phasenet_original | S | 1 | 0 | 0 |
| phasenet_stead | P | 0 | 0 | 1 |

### T5 why reference picks were missed

| variant | phase | model_below_minConfidence | no_P_pick_so_no_S_picker | no_S_window_covering | no_detector_trigger | only_P_pick_is_on_this_S_wave | peak_vetoed_as_S | trigger_not_turned_into_picker | window_picked_other_time |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | P | 15 | 0 | 0 | 9 | 0 | 1 | 6 | 3 |
| phasenet_original | S | 1 | 51 | 0 | 0 | 0 | 0 | 0 | 5 |
| phasenet_instance | P | 35 | 0 | 0 | 9 | 0 | 0 | 6 | 7 |
| phasenet_instance | S | 10 | 81 | 0 | 0 | 1 | 0 | 0 | 6 |
| eqtransformer_stead | P | 83 | 0 | 0 | 6 | 0 | 1 | 5 | 0 |
| eqtransformer_stead | S | 0 | 139 | 0 | 0 | 0 | 0 | 0 | 2 |
| phasenet_stead | P | 106 | 0 | 0 | 9 | 0 | 0 | 6 | 0 |
| phasenet_stead | S | 1 | 155 | 0 | 0 | 0 | 0 | 0 | 3 |
| phasenet_instance_fast | P | 23 | 0 | 0 | 11 | 0 | 0 | 10 | 5 |
| phasenet_instance_fast | S | 19 | 59 | 1 | 0 | 5 | 0 | 0 | 7 |

### T6 cost (scautopick + plugin; ONNX Runtime single-threaded)

| model | station_hours | cpu_s | wall_s | cpu_s_per_station_hour | startup_cpu_s | triggers | P_windows | S_windows | ms_per_window | max_rss_MB |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | 71.0 | 9.57 | 8.59 | 0.135 | 0.03 | 2325 | 1818 | 1894 | 2.49 | 122 |
| phasenet_instance | 71.0 | 8.64 | 7.66 | 0.122 | 0.03 | 2325 | 1818 | 1576 | 2.45 | 121 |
| eqtransformer_stead | 71.0 | 24.08 | 23.08 | 0.339 | 0.03 | 2325 | 1513 | 1176 | 8.83 | 134 |
| phasenet_stead | 71.0 | 7.83 | 6.83 | 0.110 | 0.03 | 2325 | 1818 | 1080 | 2.59 | 120 |
| phasenet_instance_fast | 71.0 | 20.09 | 19.07 | 0.283 | 0.03 | 2325 | 11650 | 2075 | 1.44 | 122 |

### T6b SeisBench continuous classify() on the same data

| model | torch_threads | cpu_classify_s | wall_classify_s | station_hours | cpu_s_per_station_hour |
|---|---|---|---|---|---|
| phasenet_instance | 4 threads | 35.1 | 10.0 | 71.0 | 0.494 |
| eqtransformer_stead | 4 threads | 86.8 | 23.1 | 71.0 | 1.222 |
| phasenet_instance | 1 thread | 23.8 | 23.3 | 71.0 | 0.335 |
| eqtransformer_stead | 1 thread | 68.0 | 67.8 | 71.0 | 0.957 |

### T7 fast vs reliable (phasenet_instance P picks; dt = fast - reliable; fractions in whole samples)

| pairs | n | median_abs_dt | identical | within_2_samples | within_5_samples | p95_abs_dt | max_abs_dt | mean_dt |
|---|---|---|---|---|---|---|---|---|
| all paired | 346 | 0.020 | 0.21 | 0.71 | 0.92 | 0.070 | 0.190 | -0.0016 |
| inside the event windows | 321 | 0.010 | 0.22 | 0.73 | 0.92 | 0.070 | 0.190 | -0.0025 |

```
{
 "n_reliable_P": 399,
 "n_fast_P": 542,
 "n_paired": 346,
 "n_paired_in_window": 321,
 "dt_definition": "fast time - reliable time [s]; fractions counted in whole samples, n = round(dt * 100 Hz): identical |n| == 0, within 0.02 s |n| <= 2, within 0.05 s |n| <= 5",
 "identical_fraction": 0.2138728323699422,
 "within_2_samples_fraction": 0.7052023121387283,
 "within_5_samples_fraction": 0.9161849710982659,
 "in_window_identical_fraction": 0.22118380062305296,
 "in_window_within_2_samples_fraction": 0.7258566978193146,
 "in_window_within_5_samples_fraction": 0.9190031152647975,
 "dt_n_dt": 346,
 "dt_median_abs_dt_s": 0.019986000000000018,
 "dt_mad_dt_s": 0.019986000000000018,
 "dt_p95_abs_dt_s": 0.06999924999999996,
 "dt_mean_dt_s": -0.001560578034682083,
 "dt_median_dt_s": 0.0,
 "dt_max_abs_dt_s": 0.190013,
 "dt_in_window_n_dt": 321,
 "dt_in_window_median_abs_dt_s": 0.010009999999999963,
 "dt_in_window_mad_dt_s": 0.010009999999999963,
 "dt_in_window_p95_abs_dt_s": 0.069997,
 "dt_in_window_mean_dt_s": -0.0024921339563862945,
 "dt_in_window_median_dt_s": 0.0,
 "dt_in_window_max_abs_dt_s": 0.190013,
 "phasenet_instance_fast_pick_available_after_onset_s_median_in_window": 1.29,
 "phasenet_instance_fast_pick_available_after_onset_s_p90_in_window": 6.387999700000001,
 "phasenet_instance_fast_latency_rows_in_window": 398,
 "phasenet_instance_fast_accepted_attempt_counts_in_window": {
  "1": 310,
  "2": 38,
  "3": 11,
  "4": 12,
  "5": 9,
  "6": 9,
  "7": 6,
  "8": 3
 },
 "phasenet_instance_pick_available_after_onset_s_median_in_window": 15.1899955,
 "phasenet_instance_pick_available_after_onset_s_p90_in_window": 16.0160004,
 "phasenet_instance_latency_rows_in_window": 358,
 "phasenet_instance_accepted_attempt_counts_in_window": {
  "1": 358
 }
}
```

### T8 plugin vs SeisBench (same weights; dt = plugin - SeisBench; fractions in whole samples)

| model | phase | plugin_picks | seisbench_picks | pairs | median_abs_dt | within_2_samples | within_5_samples | identical | p95 | max | mean_dt_plugin_minus_SB | SB_recall | SB_precision | plugin_recall | plugin_precision | ref_only_SB | ref_only_plugin | ref_neither |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 399 | 415 | 352 | 0.010 | 0.83 | 0.94 | 0.32 | 0.060 | 0.27 | -0.0012 | 0.864 | 0.871 | 0.842 | 0.842 | 12 | 4 | 45 |
| phasenet_instance | S | 337 | 370 | 301 | 0.010 | 0.72 | 0.96 | 0.21 | 0.050 | 0.13 | +0.0016 | 0.797 | 0.955 | 0.757 | 0.919 | 32 | 16 | 66 |
| eqtransformer_stead | P | 294 | 294 | 266 | 0.020 | 0.66 | 0.94 | 0.21 | 0.060 | 0.15 | +0.0023 | 0.764 | 0.975 | 0.736 | 0.908 | 13 | 3 | 82 |
| eqtransformer_stead | S | 292 | 336 | 267 | 0.020 | 0.60 | 0.89 | 0.13 | 0.070 | 0.16 | -0.0052 | 0.749 | 0.938 | 0.650 | 0.897 | 41 | 1 | 100 |

weights phasenet_instance: same_weights=True; P: same-input max|diff| 5.4e-07, plugin-input max|diff| 4.0e-06, argmax shift [0, 0, 0, 0, 0, 0]; S: same-input max|diff| 6.3e-07, plugin-input max|diff| 1.4e-05, argmax shift [0, 0, 0, 0, 0, 0]; input diff 3.32e-05

weights eqtransformer_stead: same_weights=True; P: same-input max|diff| 8.6e-07, plugin-input max|diff| 9.8e-04, argmax shift [0, 0, 0, 0, 0, 0]; S: same-input max|diff| 4.2e-07, plugin-input max|diff| 2.6e-04, argmax shift [0, 0, 0, 0, 0, 0]; input diff 2.28e-01

### T9 relocation: metric (a) relative geometry RMS (m), own centroid removed; metric (b) centroid shift (m), solution centroid - reference centroid

| solution | reference | n_events | rms_3d_m | rms_east_m | rms_north_m | rms_up_m | max_3d_m | median_3d_m | spread_solution_rms_m | spread_reference_rms_m | centroid_shift_east_m | centroid_shift_north_m | centroid_shift_up_m | centroid_shift_3d_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all_at_centroid | hypodd_dtct | 11 | 69.1 | 55.1 | 14.6 | 39.0 | 101.9 | 61.7 | 0.0 | 69.1 | -0.0 | -22.7 | -71.9 | 75.4 |
| all_at_centroid | hypodd_dtcc | 11 | 50.4 | 46.5 | 13.9 | 13.5 | 97.2 | 41.4 | 0.0 | 50.4 | -0.1 | -0.0 | -1.1 | 1.1 |
| all_at_centroid | control_phasenet_plus | 11 | 74.5 | 52.1 | 14.2 | 51.3 | 116.9 | 62.3 | 0.0 | 74.5 | -1699.0 | -150.9 | -243.5 | 1722.9 |
| hypoinverse_start | hypodd_dtct | 11 | 569.5 | 149.3 | 69.7 | 545.2 | 994.6 | 528.0 | 584.9 | 69.1 | -0.7 | -23.1 | -71.9 | 75.5 |
| hypoinverse_start | hypodd_dtcc | 11 | 586.6 | 149.9 | 67.0 | 563.2 | 979.9 | 528.5 | 584.9 | 50.4 | -0.8 | -0.5 | -1.1 | 1.4 |
| hypoinverse_start | control_phasenet_plus | 11 | 570.3 | 154.1 | 63.0 | 545.5 | 1003.7 | 464.8 | 584.9 | 74.5 | -1699.6 | -151.3 | -243.5 | 1723.6 |
| hypodd_dtct | hypodd_dtcc | 11 | 51.3 | 28.3 | 17.2 | 39.2 | 94.3 | 29.1 | 69.1 | 50.4 | -0.1 | 22.7 | 70.8 | 74.4 |
| hypodd_dtct | control_phasenet_plus | 11 | 72.2 | 35.5 | 18.9 | 60.0 | 133.7 | 54.6 | 69.1 | 74.5 | -1698.9 | -128.2 | -171.6 | 1712.4 |
| control_phasenet_plus | hypodd_dtct | 11 | 72.2 | 35.5 | 18.9 | 60.0 | 133.7 | 54.6 | 74.5 | 69.1 | 1698.9 | 128.2 | 171.6 | 1712.4 |
| control_phasenet_plus | hypodd_dtcc | 11 | 52.7 | 17.0 | 8.6 | 49.2 | 110.2 | 44.3 | 74.5 | 50.4 | 1698.9 | 150.8 | 242.4 | 1722.7 |
| control_phasenet_plus_same_subset | hypodd_dtct | 11 | 72.4 | 35.9 | 16.7 | 60.6 | 150.0 | 48.2 | 75.5 | 69.1 | 402.2 | 279.4 | -145.7 | 510.9 |
| control_phasenet_plus_same_subset | hypodd_dtcc | 11 | 55.0 | 19.2 | 7.8 | 51.0 | 116.9 | 38.0 | 75.5 | 50.4 | 402.1 | 302.1 | -74.9 | 508.5 |
| control_phasenet_plus_same_subset | control_phasenet_plus | 11 | 15.2 | 7.1 | 4.6 | 12.7 | 22.7 | 11.5 | 75.5 | 74.5 | -1296.7 | 151.2 | -317.3 | 1343.5 |
| dl_phasenet_instance_window | hypodd_dtct | 11 | 127.2 | 79.2 | 31.0 | 94.6 | 212.9 | 96.0 | 121.9 | 69.1 | 263.6 | 135.8 | -258.6 | 393.4 |
| dl_phasenet_instance_window | hypodd_dtcc | 11 | 109.5 | 59.4 | 24.9 | 88.6 | 175.8 | 91.3 | 121.9 | 50.4 | 263.5 | 158.4 | -187.8 | 360.3 |
| dl_phasenet_instance_window | control_phasenet_plus | 11 | 84.0 | 54.0 | 22.4 | 60.3 | 162.4 | 59.0 | 121.9 | 74.5 | -1435.3 | 7.6 | -430.2 | 1498.4 |
| dl_phasenet_instance_window_tt | hypodd_dtct | 11 | 145.3 | 68.8 | 26.8 | 125.2 | 248.4 | 110.1 | 138.2 | 69.1 | -30.9 | -256.2 | 273.2 | 375.8 |
| dl_phasenet_instance_window_tt | hypodd_dtcc | 11 | 128.7 | 49.1 | 21.3 | 117.0 | 228.5 | 111.7 | 138.2 | 50.4 | -30.9 | -233.5 | 344.1 | 417.0 |
| dl_phasenet_instance_window_tt | control_phasenet_plus | 11 | 105.8 | 44.3 | 20.7 | 93.9 | 256.1 | 82.0 | 138.2 | 74.5 | -1729.8 | -384.4 | 101.7 | 1774.9 |
| dl_phasenet_stead_window | hypodd_dtct | 11 | 150.3 | 40.7 | 33.1 | 140.9 | 338.7 | 119.0 | 151.3 | 69.1 | -82.8 | -265.8 | -262.9 | 382.9 |
| dl_phasenet_stead_window | hypodd_dtcc | 11 | 141.2 | 22.7 | 24.7 | 137.2 | 271.3 | 109.7 | 151.3 | 50.4 | -82.8 | -243.2 | -192.1 | 320.7 |
| dl_phasenet_stead_window | control_phasenet_plus | 11 | 111.2 | 19.0 | 22.5 | 107.2 | 208.7 | 98.2 | 151.3 | 74.5 | -1781.7 | -394.0 | -434.5 | 1875.8 |
| dl_phasenet_stead_window_tt | hypodd_dtct | 11 | 150.3 | 40.7 | 33.1 | 140.9 | 338.7 | 119.0 | 151.3 | 69.1 | -82.8 | -265.8 | -262.9 | 382.9 |
| dl_phasenet_stead_window_tt | hypodd_dtcc | 11 | 141.2 | 22.7 | 24.7 | 137.2 | 271.3 | 109.7 | 151.3 | 50.4 | -82.8 | -243.2 | -192.1 | 320.7 |
| dl_phasenet_stead_window_tt | control_phasenet_plus | 11 | 111.2 | 19.0 | 22.5 | 107.2 | 208.7 | 98.2 | 151.3 | 74.5 | -1781.7 | -394.0 | -434.5 | 1875.8 |
| dl_eqtransformer_stead_window | hypodd_dtct | 11 | 128.7 | 50.7 | 37.1 | 112.3 | 203.6 | 104.1 | 141.6 | 69.1 | -173.2 | -183.3 | 343.6 | 426.2 |
| dl_eqtransformer_stead_window | hypodd_dtcc | 11 | 130.5 | 43.2 | 33.8 | 118.5 | 194.0 | 144.1 | 141.6 | 50.4 | -173.3 | -160.6 | 414.4 | 477.0 |
| dl_eqtransformer_stead_window | control_phasenet_plus | 11 | 102.8 | 44.5 | 33.5 | 86.5 | 178.6 | 81.8 | 141.6 | 74.5 | -1872.2 | -311.4 | 172.0 | 1905.7 |
| dl_eqtransformer_stead_window_tt | hypodd_dtct | 11 | 128.7 | 50.7 | 37.1 | 112.3 | 203.6 | 104.1 | 141.6 | 69.1 | -173.2 | -183.3 | 343.6 | 426.2 |
| dl_eqtransformer_stead_window_tt | hypodd_dtcc | 11 | 130.5 | 43.2 | 33.8 | 118.5 | 194.0 | 144.1 | 141.6 | 50.4 | -173.3 | -160.6 | 414.4 | 477.0 |
| dl_eqtransformer_stead_window_tt | control_phasenet_plus | 11 | 102.8 | 44.5 | 33.5 | 86.5 | 178.6 | 81.8 | 141.6 | 74.5 | -1872.2 | -311.4 | 172.0 | 1905.7 |
| dl_phasenet_original_window | hypodd_dtct | 11 | 89.3 | 35.3 | 21.5 | 79.2 | 155.8 | 59.8 | 96.9 | 69.1 | -0.2 | -72.6 | -137.0 | 155.1 |
| dl_phasenet_original_window | hypodd_dtcc | 11 | 81.8 | 18.9 | 9.9 | 78.9 | 154.1 | 68.7 | 96.9 | 50.4 | -0.3 | -50.0 | -66.2 | 83.0 |
| dl_phasenet_original_window | control_phasenet_plus | 11 | 49.1 | 16.4 | 8.0 | 45.6 | 71.0 | 47.9 | 96.9 | 74.5 | -1699.1 | -200.8 | -308.6 | 1738.6 |
| dl_phasenet_original_window_tt | hypodd_dtct | 11 | 90.4 | 35.7 | 20.1 | 80.5 | 159.8 | 58.0 | 96.6 | 69.1 | -65.0 | -31.9 | -14.3 | 73.8 |
| dl_phasenet_original_window_tt | hypodd_dtcc | 11 | 81.9 | 18.9 | 9.2 | 79.2 | 156.1 | 69.6 | 96.6 | 50.4 | -65.0 | -9.3 | 56.5 | 86.6 |
| dl_phasenet_original_window_tt | control_phasenet_plus | 11 | 47.4 | 16.1 | 7.9 | 43.8 | 68.3 | 49.7 | 96.6 | 74.5 | -1763.9 | -160.1 | -185.9 | 1780.9 |
| dl_phasenet_original_matched_only | hypodd_dtct | 11 | 86.9 | 37.0 | 18.5 | 76.4 | 157.9 | 55.4 | 89.2 | 69.1 | -22.6 | 22.3 | -33.8 | 46.3 |
| dl_phasenet_original_matched_only | hypodd_dtcc | 11 | 73.0 | 20.2 | 8.3 | 69.7 | 141.4 | 63.1 | 89.2 | 50.4 | -22.7 | 44.9 | 37.0 | 62.5 |
| dl_phasenet_original_matched_only | control_phasenet_plus | 11 | 38.2 | 16.0 | 7.9 | 33.8 | 62.6 | 33.4 | 89.2 | 74.5 | -1721.5 | -105.9 | -205.4 | 1737.0 |
| dl_phasenet_original_matched_only | control_phasenet_plus_same_subset | 11 | 39.7 | 12.1 | 9.0 | 36.8 | 83.9 | 29.8 | 89.2 | 75.5 | -424.8 | -257.1 | 111.9 | 509.0 |
| dl_phasenet_instance_window_tt | dl_phasenet_instance_window | 11 | 61.1 | 35.6 | 18.1 | 46.3 | 170.4 | 35.1 | 138.2 | 121.9 | -294.4 | -392.0 | 531.8 | 723.3 |
| dl_phasenet_stead_window_tt | dl_phasenet_stead_window | 11 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 151.3 | 151.3 | 0.0 | 0.0 | 0.0 | 0.0 |
| dl_eqtransformer_stead_window_tt | dl_eqtransformer_stead_window | 11 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 141.6 | 141.6 | 0.0 | 0.0 | 0.0 | 0.0 |
| dl_phasenet_original_window_tt | dl_phasenet_original_window | 11 | 5.4 | 2.2 | 2.0 | 4.5 | 11.1 | 4.0 | 96.6 | 96.9 | -64.7 | 40.7 | 122.7 | 144.6 |

### T9c relocation: centroid of each solution - its starting centroid (event_centroid_start.csv = HypoDD ISTART=1 centroid), m

| solution | relocator | n_events | shift_east_m | shift_north_m | shift_up_m | shift_horizontal_m | shift_3d_m |
|---|---|---|---|---|---|---|---|
| hypodd_dtct | HypoDD | 11 | 0.0 | 22.7 | 71.9 | 22.7 | 75.4 |
| hypodd_dtcc | HypoDD | 11 | 0.1 | 0.0 | 1.1 | 0.1 | 1.1 |
| control_phasenet_plus | pyrtdd | 11 | 1699.0 | 150.9 | 243.5 | 1705.6 | 1722.9 |
| dl_phasenet_instance_window | pyrtdd | 11 | 263.6 | 158.4 | -186.7 | 307.6 | 359.8 |
| dl_phasenet_instance_window_tt | pyrtdd | 11 | -30.9 | -233.5 | 345.2 | 235.6 | 417.9 |
| dl_phasenet_stead_window | pyrtdd | 11 | -82.7 | -243.2 | -191.0 | 256.8 | 320.1 |
| dl_phasenet_stead_window_tt | pyrtdd | 11 | -82.7 | -243.2 | -191.0 | 256.8 | 320.1 |
| dl_eqtransformer_stead_window | pyrtdd | 11 | -173.2 | -160.6 | 415.5 | 236.2 | 477.9 |
| dl_eqtransformer_stead_window_tt | pyrtdd | 11 | -173.2 | -160.6 | 415.5 | 236.2 | 477.9 |
| dl_phasenet_original_window | pyrtdd | 11 | -0.2 | -49.9 | -65.1 | 49.9 | 82.1 |
| dl_phasenet_original_window_tt | pyrtdd | 11 | -64.9 | -9.2 | 57.6 | 65.6 | 87.3 |
| dl_phasenet_original_matched_only | pyrtdd | 11 | -22.6 | 45.0 | 38.1 | 50.3 | 63.1 |
| control_phasenet_plus_same_subset | pyrtdd | 11 | 402.2 | 302.1 | -73.8 | 503.0 | 508.4 |

### T9b relocation inputs

| solution | P | S | not_matching_phasenet_plus | used_P | used_S | events_relocated | final_rms_median_s |
|---|---|---|---|---|---|---|---|
| control_phasenet_plus | 360 | 403 |  | 351 | 397 | 11 | 1.054 |
| dl_phasenet_instance_window | 344 | 316 | 65 | 337 | 315 | 11 | 1.500 |
| dl_phasenet_instance_window_tt | 325 | 315 | 46 | 325 | 315 | 11 | 0.286 |
| dl_phasenet_stead_window | 256 | 253 | 31 | 252 | 247 | 11 | 0.213 |
| dl_phasenet_stead_window_tt | 256 | 253 | 31 | 252 | 247 | 11 | 0.213 |
| dl_eqtransformer_stead_window | 268 | 268 | 29 | 267 | 267 | 11 | 0.225 |
| dl_eqtransformer_stead_window_tt | 268 | 268 | 29 | 267 | 267 | 11 | 0.225 |
| dl_phasenet_original_window | 391 | 379 | 113 | 380 | 369 | 11 | 1.271 |
| dl_phasenet_original_window_tt | 371 | 366 | 83 | 371 | 365 | 11 | 0.219 |
| dl_phasenet_original_matched_only | 326 | 346 |  | 325 | 341 | 11 | 0.216 |
| control_phasenet_plus_same_subset | 326 | 346 |  | 325 | 341 | 11 | 0.260 |

reference bootstrap 95% (median over events, m): {"hypodd_dtct": {"boot_ex95_m": 33.8, "boot_ey95_m": 16.5, "boot_ez95_m": 43.3}, "hypodd_dtcc": {"boot_ex95_m": 3.2, "boot_ey95_m": 2.2, "boot_ez95_m": 5.5}}
