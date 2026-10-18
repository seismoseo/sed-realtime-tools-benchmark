# Independent verification findings for the Gwangyang runs (2026-10-17)

Each verifier recomputed the headline numbers with its own code. Verdicts and every finding are listed here verbatim;
the fixes are recorded in `docs/results/fixes_after_verification.md`.

## Relocations (pyrtdd, scrtdd) - notes 07 and 08

Verdict: **confirmed_with_issues** (15 of 21 checks confirmed).

### Checks not confirmed

- **refuted**: 08 section 4.5 and the scrtdd JSON open issue: single-event scrtdd SEa and pyrtdd R6tf differ by a median 10 m (max 17 m), and R6tf lies a median 7.9 m from its own reference catalog R1f
  - Evidence: With the current files, SEa vs R6tf is median 1.68 m, max 2.21 m, and SEm vs R6f is median 1.71 m, max 1.81 m. R6tf lies a median 1.74 m from R1f (event 3 43.5 m). The ~1.7 m is mostly the common S1-vs-R1f offset. scrtdd wrote comparison/single_event_scrtdd_vs_pyrtdd.csv at 16:42; pyrtdd re-ran R6f at 17:04 and R6tf at 17:12 with padded batch loading. The quoted numbers describe superseded pyrtdd runs (extra_single_event_cross_tool.csv).
- **refuted**: (f) agreement statistics: median 0, MAD 1 ms; within 2 ms 66% (all), 82% (without event 3), 84% (kept by HypoDD), 37% (rejected), P 76% / S 59-60%, R1 46%; within 5 ms 77 / 94 / 95 / 49%
  - Evidence: Medians, MADs and the 5-ms fractions reproduce: 77.6 / 93.7 / 95.4 / 49.7%. The 2-ms fractions do not. Both scripts compare float differences with <= 2.0 ms, but both data sets sit on a 1-ms grid. 135 of the 274 differences of exactly 2 ms fail that float test, so the reported 0.658 is neither the <= 1 ms fraction (0.599) nor the <= 2 ms fraction (0.716). On the 1-ms grid the values are 71.6, 88.8, 90.1 and 42.5%, P 79.0%, S 67.1%, and R1 53.7%. My float version reproduces the agents' numbers exactly (extra_f_within_fractions.csv).
- **refuted**: HypoDD's SVD pins (keeps fixed) the cluster centroid
  - Evidence: This is only true for 02.dt.cc, whose final cumulative centroid shift in hypoDD.log is 0.0 / -0.0 / -1.0 m and -6.3 ms. In 01.dt.ct the centroid moved -0.1 / +22.8 m and 71.9 m up, with +148.8 ms (hypoDD.log, iterations 7-12). The '0 / +23 / +71' scale row in both notes already shows this.
- **refuted**: 08: S1 (pure double difference) and S2 (default solver with absolute equations) give the same shape
  - Evidence: S2 vs S1 differs by 2.25 m horizontal and 3.33 m vertical RMS (max 4.2 / 6.1 m). That is comparable to the S1-vs-HypoDD difference (3.0 / 4.5 m) and to the bootstrap half-widths. S2 has 2 of 11 events inside the box against 5 for S1. S2 also changes the cross-correlation windows, so this is not a solver-only comparison.
- **unverifiable**: Station elevations (up to 0.061 s P / 0.106 s S on absolute times) cancel in the double differences
  - Evidence: No run used zero-elevation grids. The claim is physically plausible for a cluster about 150 m across, but it was not tested.
- **unverifiable**: 08: the S2 centroid is 0.73 km deeper because the best absolute fit with these grids is deeper than HypoDD's centroid
  - Evidence: R2 has the same absolute picks and absLocConstraint 0.3 but unfiltered cross-correlation, and it ended 0.42 km deeper, against 0.73 km for R2f/S2. So the absolute depth depends on the cross-correlation data and the damping, not only on an absolute fit. The 17 picks more than 1 s off and the ~0.27 s S-P deficit also dominate the absolute residuals.

### Issues

1. **major**: The single-event comparison between scrtdd and pyrtdd in docs/results/08_gwangyang_scrtdd.md (section 4.5, the open issue in the JSON) and in comparison/single_event_scrtdd_vs_pyrtdd.csv is stale. It gives median 10 m / max 17 m and 'R6tf 7.9 m from R1f'. These numbers come from pyrtdd's earlier R6f/R6tf runs, read at 16:42 and re-run at 17:04 and 17:12 with padded batch loading. The current files give SEa vs R6tf 1.68 / 2.21 m, SEm vs R6f 1.71 / 1.81 m, and R6tf vs R1f median 1.74 m. In other words, the two tools agree in single-event mode at the level of the S1-R1f catalog offset. The note's list of input differences does not explain a discrepancy that no longer exists.
   - Suggested fix: Re-run 'python -I scripts/scrtdd_compare.py --apply' (env pyrtdd). Then update 08 section 4.5, the open issue and summary.json: SEa vs R6tf and SEm vs R6f differ by about 1.7 m, mostly the common S1-R1f shift.
2. **major**: Both analysis scripts (analyze_pyrtdd_gwangyang.py:223 and scrtdd_compare.py:170) compute the 'fraction within 2 ms / 5 ms' of metric (f) as a float comparison (np.abs(diff_ms) <= 2.0) on values that lie on a 1-ms grid. About half of the exact-2-ms differences fail through rounding noise, so every reported 2-ms fraction is 3-10 points too low and matches neither definition (<= 1 ms or <= 2 ms). Reported vs correct: S1/R1f all 66% vs 71.6%; without event 3 82% vs 88.8%; kept by HypoDD 84% vs 90.1%; rejected 37% vs 42.5%; P 76% vs 79.0%; S 59-60% vs 67.1%; R1 46% vs 53.7%; all measured 59% vs 64.2%. The 5-ms fractions are off by at most about 1 point. The error is conservative and the conclusions stand, but the numbers in 07, 08 and both JSON summaries are wrong.
   - Suggested fix: Compare on the grid, for example np.abs(np.round(diff_ms)) <= 2, or add a tolerance (<= 2.0 + 1e-6). Regenerate xcorr_comparison.csv and xcorr_vs_reference.csv and update the tables. Corrected values are in runs/verify_gwangyang_reloc/extra_f_within_fractions.csv.
3. **minor**: Metric (c) changes by plus or minus one event with the HypoDD representation and with the rounding of the bootstrap half-widths. The two notes use different conventions: 07 uses lat/lon plus Z (0.1 m) with 0.1-m-rounded half-widths; 08 uses the 1-m DEPTH column. As a result they quote different numbers for practically identical solutions: R1f vertical 4.3 / 9.0 m in 07 vs 4.5 / 9.4 m in 08, and R2f 3 of 11 vs S2 2 of 11, although R2f and S2 differ by 0.15 m. R2f is 3 of 11 only with rounded ey95; event 8's ratio is 1.008 raw vs 0.998 rounded. R1 is 2 of 11 and R1fz 4 of 11 under other conventions.
   - Suggested fix: Use one convention in both scripts: HypoDD X/Y/Z (0.1 m) about the hypoDD.log centroid, with unrounded half-widths from bootstrap_errors.csv. Report the largest ratio of |d| to the half-width next to the count (it is 1.47 for S1/R1f).
4. **minor**: Both notes say HypoDD's SVD 'pins' or 'keeps fixed' the cluster centroid. That holds for 02.dt.cc (1.0 m), but the 01.dt.ct centroid moved 22.8 m N and 71.9 m up, with +148.8 ms (hypoDD.log). This matters when R0/S0 are compared with dt.ct.
   - Suggested fix: Restrict the statement to the dt.cc run and quote the dt.ct centroid movement from hypoDD.log.
5. **minor**: Some wording overstates the shape results. 08 says 'S1 and S2 give the same shape', but they are 2.25 / 3.33 m RMS apart (max 4.2 / 6.1 m), about as large as S1-vs-HypoDD, and S2 also changes the windows. 07 says 'the shape is settled after 2-3 iterations', but the shape still changes by 1.0-2.6 m RMS after iterations 2-3. 07 calls the damping-1.0 variant 'the same shape', but it is 0.56 / 1.49 m RMS (vertical max 4.3 m) from R1f.
   - Suggested fix: Quote the run-vs-run shape RMS values instead of 'same', and say the shape is within about 1 m after 5 iterations.
6. **minor**: The 08 table prints the CC-correlation column (P |CC| 0.76 / S 0.69, over all measured triplets) next to the 'pairs where both passed' columns. 07 reports signed CC over the both-passed subset (0.23). On the both-passed subset, P |CC| is 0.69 and signed P is 0.16.
   - Suggested fix: State the subset and the sign convention, or give both.
7. **minor**: 08 explains S2's 0.73 km deeper centroid as 'the best absolute fit with these grids'. That is not supported. R2, with the same absolute data and absLocConstraint 0.3, moved 0.42 km, so the absolute depth depends on the cross-correlation data and the damping drift. The absolute residuals are also dominated by the 17 picks more than 1 s off and by the ~0.27 s S-P deficit.
   - Suggested fix: Call this a hypothesis, or test it with an absolute-only location of the same picks, with and without the 17 outlier picks.
8. **minor**: Some open issues in 07 are now answered by 08's results. BW(4,5,20) acts like obspy bandpass(corners=4) causal: 2787 of 2801 lags are identical. scrtdd's single-event mode does cross-correlate with SeisComP's record stream: SEa event 1 has 399 of 478 step-2 double differences from cross-correlation, so libhdd's BatchLoader does not reject the traces there.
   - Suggested fix: Update 07's open-issues list with these answers.
9. **minor**: Two caveats are not stated. (1) The bootstrap box measures only HypoDD's own precision: init=solution, same data and settings, half-widths 1.7-4.8 m horizontal. One of the five 'inside' events is event 3, whose box is 16 / 6 / 26 m and whose reference cross-correlation used ±0.05 s and 1-40 Hz. (2) The leave-one-out background positions come from multi-event solutions that included the left-out event.
   - Suggested fix: Add 'the other 4 inside events are among the 10 well-constrained ones' alongside 5 of 11, and add a sentence on the leave-one-out background.

## DL picker - note 09

Verdict: **confirmed_with_issues** (12 of 13 checks confirmed).

### Checks not confirmed

- **refuted**: Mean plugin-minus-SeisBench offsets are within +-0.005 s, and the column dt_plugin_minus_seisbench_s is plugin minus SeisBench.
  - Evidence: The magnitude part holds; the sign does not. 09_compare_seisbench.py calls match(plugin, seisbench), which returns SeisBench minus plugin. In 483 of 497 non-zero pairs, step 09's column has the opposite sign to my plugin-minus-SeisBench value. Correct phasenet_instance means are P -0.0012 s and S +0.0016 s (reported as +0.0012 and -0.0016). The mean magnitudes are still within 0.005 s.

### Issues

1. **minor**: Sign error in the SeisBench comparison. In 09_compare_seisbench.py, match(plugin, seisbench) returns SeisBench minus plugin, but the column dt_plugin_minus_seisbench_s in compare_seisbench_pairs.csv and the means in compare_seisbench_summary.json are labelled plugin minus SeisBench. The reported phasenet_instance means (+0.0012 s P, -0.0016 s S) should read -0.0012 s and +0.0016 s. The '+-0.005 s' conclusion is unaffected.
   - Suggested fix: Negate dt (or swap the match arguments), relabel, and re-run 09_compare_seisbench.py; correct the sign in the notes, section 9.
2. **minor**: The 'within 0.02 s' fractions (P 80 %, S 63 %) are not well defined. Many pairs differ by exactly 2 samples plus a few microseconds, and floating-point rounding at the 0.020001 s cut moves them in or out. The same data give 79.5-83.0 % (P) and 63.1-72.1 % (S).
   - Suggested fix: Report differences in whole samples (round(dt*100)), or use a cut midway between samples (0.025 / 0.055 s) and say so.
3. **minor**: Missing caveat on the relocation control. The pyrtdd control (PhaseNet+ picks) moved its whole cluster 1.72 km from its start (E 1.70, N 0.15, U 0.24 km); the same-subset control moved 0.51 km; the main DL solution moved only 0.08 km. Step 09 does not mention this. Metric (a) removes each solution's centroid, so its numbers stand. But the 'effect of the picks alone' compares solutions sitting up to 1.7 km apart in absolute position. This is the known catalog-only drift (logs/07_gwangyang_pyrtdd_diag_centroid_drift.log).
   - Suggested fix: Report the centroid shift (metric b) next to metric (a). Alternatively, repeat the DL-vs-control comparison with an absolute-location constraint or larger damping, so that both solutions sit at the same place.
4. **minor**: Two wording points on the weight checks. On new windows, ONNX vs torch outputs differ by up to 1.2e-6, slightly above the notes' 'less than 1e-6' (still float32 rounding level, same argmax everywhere). And the statement that the plugin normalisation 'changes nothing (<= 1.4e-5)' holds for step 09's windows only: on HG windows with DC offsets of 1e5-1e6 counts and weak signals, float32 vs float64 demeaning changes the input by up to 0.6 % of the peak and the output by up to 3e-3. Neither affects any pick.
   - Suggested fix: Say 'about 1e-6 (float32 rounding)'. Add that low-amplitude windows with large DC offsets give output differences up to about 3e-3.
5. **minor**: Reading of the timing offset. In the waveform check, the weakest arrival (ML 1.1, MNDB P) has its visible onset at the phasenet_original pick, with the PhaseNet+ pick about 0.09 s earlier in the noise. Part of phasenet_original's +0.040 s mean P offset may therefore be early reference picks, not late DL picks. This fits the notes' 'agreement is not truth' caveat, but the offset should not be read as a DL bias.
   - Suggested fix: Note in section 2 that the sign of the DL-PhaseNet+ offset cannot be assigned to either picker without an independent check, for example the waveform zooms of this verification.

## Real-time chain - note 10

Verdict: **confirmed_with_issues** (11 of 12 checks confirmed).

### Checks not confirmed

- **refuted**: No new files in /tmp owned by msseo from this run besides scratch the run removed
  - Evidence: The shared harness scratchpad /tmp/claude-1007/-home-msseo/8b88ea45-810a-4779-8a4c-1abea6e4784a/scratchpad/ still holds three files from the real-time agent. (1) msr.err, 913,429 bytes, 17:52:21 KST. Its first line reads 'Starting msrtsimul at 2026-10-17 08:52:21 UTC'; it is an unpaced msrtsimul trial on the 20260202194119 file, run between RT2's stop (08:52:07) and RT3's start (08:53:55). It has the same size as RT3's msrtsimul_20260202194119.stderr. (2) fill_rt5.py, 3,381 bytes, 18:31. Its header says it fills the RT5 placeholders of docs/results/10_gwangyang_realtime.md. (3) __pycache__/fill_rt5.cpython-312.pyc. None was removed. The other files there (E_inset.png, crops/, proto/, sp_offset_after_edit.py, build_05_before_revision.py) belong to other agents.

### Issues

1. **minor**: The real-time agent left scratch files outside the project, in the shared harness scratchpad (/tmp/claude-1007/-home-msseo/8b88ea45-810a-4779-8a4c-1abea6e4784a/scratchpad): msr.err (913 KB unpaced msrtsimul trial, 08:52:21 UTC), fill_rt5.py, and __pycache__/fill_rt5.cpython-312.pyc. This breaks rule 1 ('write only inside the project') and the 'scratch removed' condition. fill_rt5.py also wrote the RT5 numbers into the notes, yet the script is not kept in the project.
   - Suggested fix: Copy fill_rt5.py into runs/gwangyang/realtime/scripts/ with a note that it filled the RT5 rows of the notes, then delete the three scratch files (the user's decision; I did not delete anything). Its numbers agree with my recomputation.
2. **minor**: The paced latencies are measured from the final scautoloc (LOCSAT) origin time, which is 0.83 s (event 3) and 0.69 s (event 9) earlier than the S1 origin time. The analysis also uses a median-release offset that sits about 0.5 s from msrtsimul's own clock. The notes say only 'from the origin time'. From S1's origin time with msrtsimul's clock, the latencies are about 1.2-1.3 s shorter: first DL pick 12.1-13.8 s, first origin 37.0-39.3 s, first RTDD 57.6-61.5 s, against the reported 13-15, 38-40 and 59-63 s. The bias makes the reported latencies longer than they are, not shorter.
   - Suggested fix: State in docs/results/10_gwangyang_realtime.md section 4.5 that the reference is the final scautoloc origin time. Alternatively, recompute against the S1 (or KMA) origin time and give both.
3. **minor**: The scripts were edited after the runs they drive, and no run records a script md5. rt_chain.py changed at 18:27 KST, while RT5 was running: RT1-RT3 ran scautoloc without '--timing' (the default is pickTime, so behaviour is the same), while RT4/RT5 pass it explicitly. rt_offline_check.py changed at 18:37, after its last --apply at 18:36. The scripts now on disk cannot be shown to be the exact versions that produced RT1-RT4 and the offline checks.
   - Suggested fix: Write each driver script's md5 (and a copy or diff) into <run>/options/run_options.json for every stage, and note the RT1-RT3 versus RT4-RT5 command-line difference in the notes.
4. **minor**: The reference catalog contains no rows for the replayed events, but its 9 positions are S1 multi-event positions. S1 was inverted with events 3 and 9 included. So the agreement of the RTDD origins with S1 (61.1 m and 5.2 m) is not a fully independent test.
   - Suggested fix: Add one sentence on this to the caveats. For an independent check, build the catalog from a multi-event run without events 3 and 9 (leave-two-out) and repeat one file-feed run.
5. **minor**: A wording point. The key numbers say the picks were identical to step 09 'in every run', but RT1 replayed only event 3, so it has no event-9 picks. The notes list RT1-RT4 as identical, while RT5 is identical too (112/85 picks, exact times).
   - Suggested fix: Write 'identical for every replayed event (RT1: event 3 only; RT2-RT5: both events)'.
