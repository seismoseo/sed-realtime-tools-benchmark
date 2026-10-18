# Fixes after the independent verification of the Gwangyang runs (2026-10-17)

The findings are in `docs/results/verification_findings_gwangyang.md` (19 issues; 2 major). This file says, for
each one, what was changed (file, old value → new value) or why nothing was needed.

**What was re-run.** Only cheap analysis steps: the pyrtdd and scrtdd comparisons, the drift table (from the
relocated catalogs on disk), the DL-picker comparison stages and its catalog-only relocations (byte-identical
catalogs), and the real-time tabulation. No relocation of notes 07/08, no scautopick or SeisBench picking run and
no real-time replay was repeated. No setting was changed; only computations and wording.

**Pre-fix state.** A copy of every note, script and result table as it was before these fixes is in the session
scratchpad (`fixes_before/before.tar`), outside the project; it was used only to diff old against new values.

## Headline numbers that changed

| note | quantity | old | new |
|---|---|---|---|
| 07 | R1f shape against HypoDD dt.cc, H / V RMS (max) | 3.0 / 4.3 m (5.7 / 9.0) | 3.1 / 4.3 m (5.8 / 9.0) |
| 07 | R1f inside the dt.cc bootstrap box | 5/11 | 5/11, largest ratio 1.47 (event 9) |
| 07 | R1 (stock) inside the box | 3/11 | 2/11, largest ratio 3.11 |
| 07 | R1f cross-correlation, within 2 / 5 ms (all pairs where both passed) | 66 / 77 % | 71.6 / 77.6 % |
| 07 | R1f, within 2 ms without event 3 / P / S | 82 / 76 / 59 % | 88.8 / 79.0 / 67.1 % |
| 07 | R1f, all 2801 measured triplets within 2 / 5 ms | 59 / 70 % | 64.2 / 70.0 % |
| 08 | S1 shape against dt.cc, H / V RMS (max), 3-D max | 3.0 / 4.5 m (5.7 / 9.6), 9.7 m | 3.1 / 4.3 m (5.7 / 9.2), 9.4 m |
| 08 | S1 inter-event distances r / RMS | 0.997 / 5.3 m | 0.997 / 5.2 m |
| 08 | S1 within 2 ms, P / S | 76 / 60 % | 79.0 / 67.1 % |
| 08 | S1 within 2 / 5 ms, pairs HypoDD kept / rejected | 84 / 95 %, 37 / 49 % | 90.1 / 95.4 %, 42.5 / 49.7 % |
| 08 | single event, SEa vs pyrtdd R6tf, median / max | 10 / 17 m | 1.68 / 2.21 m (0.13 / 1.07 m after removing the S1 − R1f catalog offset) |
| 08 | single event, SEm vs R6f, median / max | 7.9 / 17.6 m | 1.72 / 1.81 m (0.10 / 0.16 m after removing the offset) |
| 08 | R6tf against its own catalog R1f, median | 7.9 m | 1.74 m |
| 09 | plugin minus SeisBench, mean dt (phasenet_instance P / S) | +0.0012 / −0.0016 s | −0.0012 / +0.0016 s |
| 09 | plugin vs SeisBench within 0.02 s, phasenet_instance P / S | 80 / 63 % | 83 / 72 % (within 2 samples) |
| 09 | plugin vs SeisBench within 0.05 s, all four rows | 87-94 % | 89-96 % (within 5 samples) |
| 09 | fast vs reliable P picks within 0.05 s | 91 % | 92 % (within 5 samples) |
| 09 | centroid moved from the start (new metric b): PhaseNet+ control / main DL solution | not reported | 1723 m / 82 m |
| 10 | paced latencies (RT3): first DL pick / first origin and event / first RTDD | 13-15 / 38-40 / 60-63 s "from the origin time" | 13-15 / 38-41 / 60-63 s from the final LOCSAT origin time; 12-14 / 37-40 / 59-62 s from S1's origin time on msrtsimul's clock |
| 10 | RT5 event 9: first / last RTDD; event 3: first RTDD | 59 / 73 s; 233 s | unchanged, plus 58 / 72 s; 231 s from S1's origin time on msrtsimul's clock |

## Relocations (pyrtdd, scrtdd): notes 07 and 08

### Scripts changed (all re-run only as analysis)

- `runs/gwangyang/pyrtdd/analyze_pyrtdd_gwangyang.py`:
  - one HypoDD convention (issue 3): HypoDD positions = `hypoDD.reloc` X/Y/Z (0.1 m) added to the
    "Cluster centroid at" point of `hypoDD.log`; bootstrap half-widths unrounded from `<branch>/bootstrap_errors.csv`;
  - largest ratio |d| / half-width per run (`c_max_ratio`, `c_max_ratio_event`) and per event (`boot95_max_ratio`);
  - 2/5-ms fractions on the 1-ms grid, `np.abs(np.round(diff_ms)) <= 2` (issue 2), with `dt_diff_grid_dev_max_ms`
    as a check (3e-12 ms);
  - |CC| correlation next to the signed one (`cc_abs_pearson_r`, `f_cc_abs_pearson_r`; issue 6);
  - `analysis_summary.json` records the convention, the `hypoDD.log` centroid and its final centroid shift.
- `runs/gwangyang/pyrtdd/diag_centroid_drift.py`: new `--metrics-only` mode (recomputes the table from the 27
  relocated catalogs on disk; nothing is relocated) and new columns `shape_vs_base_*` (shape difference from the
  base run's own 20-iteration, damping-0.01 result; issue 5) and `c_max_ratio`.
- `runs/gwangyang/pyrtdd/print_note_tables.py` (new): prints every table of note 07 sections 4-9 from the result
  files (last output `runs/gwangyang/pyrtdd/note07_tables.md`). The tables in sections 4, 6 and 8 of note 07 were
  pasted from it; sections 5, 7 and 9 were checked against it.
- `runs/gwangyang/scrtdd/scripts/scrtdd_compare.py`:
  - the same HypoDD convention, largest ratio, grid fractions (issues 2, 3);
  - CC correlation, signed and |CC|, on the pairs where both passed (issue 6);
  - new `comparison/run_vs_run.csv` (scrtdd runs against each other; issue 5);
  - new `comparison/single_event_context.csv`: each single-event run against its own reference catalog, and the
    scrtdd-pyrtdd single-event difference with the S1 − R1f catalog offset removed (issue 1);
  - step-2 cross-correlation counts per single-event run in `comparison/single_event_vs_S1.csv` (issue 8);
  - `comparison/summary.json` also records the convention and the modification time of every pyrtdd input.
- `runs/gwangyang/scrtdd/scripts/scrtdd_note_tables.py` (new): prints the tables of note 08 section 4 from
  `comparison/` (last output `comparison/note08_tables.md`); every table row in note 08 section 4 is verbatim
  from it.

Commands (env pyrtdd, `nice -n 10 python -I`, CPU only):

```bash
cd runs/gwangyang/pyrtdd
python -I analyze_pyrtdd_gwangyang.py --apply              # log: logs/07_gwangyang_pyrtdd_analysis_after_verification_20261017.log
python -I diag_centroid_drift.py --apply --metrics-only    # same log
python -I print_note_tables.py > note07_tables.md
cd ../scrtdd
python -I scripts/scrtdd_compare.py --apply                # logs/08_gwangyang_scrtdd_compare_apply_2026-10-17T2138.log and ...T2140.log (current)
python -I scripts/scrtdd_note_tables.py > comparison/note08_tables.md
```

**What stayed the same.** Byte-identical after the re-runs: pyrtdd `residual_stats.csv`; scrtdd
`final_dd_residuals_by_event.csv`, `options_by_run.csv`, `options_scrtdd_vs_pyrtdd.csv`,
`scrtdd_vs_pyrtdd_{summary,per_event}.csv`, `single_event_vs_S1_summary.csv`, `xcorr_scrtdd_vs_pyrtdd.csv` and all
`xcorr_triplets_*.csv`. In the other tables only the expected columns changed: horizontal (a), (b) and (d) against
HypoDD (representation), (c), and the 2/5-ms fractions. Vertical (a) and origin times (e) did not change, nor did
the drift table's centroid movements and wall times. Run-vs-run metrics changed only in the box column.

### Issue 1 (major): stale single-event comparison scrtdd vs pyrtdd

- Re-ran `scrtdd_compare.py --apply` on the current files (21:38 and 21:40 KST).
- `comparison/single_event_scrtdd_vs_pyrtdd.csv`: SEa vs R6tf median / max 9.99 / 17.38 m → 1.68 / 2.21 m;
  SEm vs R6f 7.88 / 17.64 m → 1.72 / 1.81 m (the file now also lists R6p and R6tp, which did not exist at 16:42).
- New `comparison/single_event_context.csv`: R6tf against R1f median 7.9 m → 1.74 m; S1 against R1f median 1.70 m
  (mostly 1.5 m south, 0.8 m up); with that offset removed event by event, SEa vs R6tf 0.13 / 1.07 m and SEm vs
  R6f 0.10 / 0.16 m.
- Note 08: "Main results" gained a bullet with these numbers; section 4.5's comparison paragraph was rewritten
  (table from `scrtdd_note_tables.py`; the list of input differences now says they change the result by about
  0.1 m; the old numbers and their cause are stated); the open issue "This difference was not investigated
  further here" was removed; the caveat about the 16:42 read was updated.
- `comparison/summary.json` regenerated (`single_event_scrtdd_vs_pyrtdd`, new `single_event_context`, pyrtdd
  input modification times).

### Issue 2 (major): "within 2 ms / 5 ms" compared floats on a 1-ms grid

- Both scripts now count on the grid (`|round(diff_ms)| <= 2 / 5`). The largest distance of any difference from
  the grid is 3e-12 ms (pyrtdd) and 0 (scrtdd, written to 4 decimals).
- Regenerated `runs/gwangyang/pyrtdd/xcorr_comparison.csv`, `summary_metrics.csv` (f columns) and
  `runs/gwangyang/scrtdd/comparison/xcorr_vs_reference.csv`, `summary.json`.
- Note 07 section 8 (within 2 / 5 ms): R1 0.46 / 0.69 → 53.7 / 70.1 %; R1f 0.66 / 0.77 → 71.6 / 77.6 %;
  R1fz 0.67 / 0.77 → 72.1 / 77.2 %; R2 0.49 / 0.73 → 59.1 / 74.5 %; R2f 0.65 / 0.80 → 72.1 / 80.5 %;
  R4 0.46 / 0.69 → 53.7 / 70.2 %; R4f 0.66 / 0.77 → 71.7 / 77.7 %. Subsets: R1 without event 3
  0.54 / 0.80 → 63.3 / 80.9 %; R1 event-3 pairs 0.08 / 0.20 → 10.5 / 21.6 %; R1f without event 3
  0.82 / 0.94 → 88.8 / 93.7 %; R1f event-3 pairs 0.07 / 0.18 → 9.8 / 19.6 %; R1f P 0.76 / 0.81 → 79.0 / 81.1 %;
  R1f S 0.59 / 0.75 → 67.1 / 75.5 %; R1fz without event 3 0.83 / 0.94 → 89.8 / 93.8 %; R2f without event 3
  0.79 / 0.95 → 87.4 / 95.2 %. Text: "82-83 % within 2 ms" → "87-90 %"; "59 % / 70 %" over all measured
  triplets → 64.2 / 70.0 %. Fractions are now given in percent.
- Note 08 section 4.4 (P / S within 2 ms; within 5 ms): S1 76 / 60 → 79.0 / 67.1 %, 81 / 75 → 81.1 / 75.5 %;
  S2 75 / 58 → 79.0 / 67.7 %, 82 / 79 → 82.0 / 79.5 %; S2sc 80 / 57 → 84.8 / 66.4 %, 86 / 78 → 87.1 / 78.6 %;
  R1f 76 / 59 → 79.0 / 67.1 %, 81 / 75 → 81.1 / 75.5 %; R1 46 / 45 → 54.7 / 53.0 %, 69 / 69 → 70.4 / 70.0 %.
  Kept by HypoDD 84 / 95 → 90.1 / 95.4 %; rejected 37 / 49 → 42.5 / 49.7 % (95th percentiles 5 and 356 ms
  unchanged). New rows: all pairs 71.6 / 77.6 %, all measured 64.2 / 70.0 %.
- Both notes explain the grid counting and how much the old float test understated the fractions.
- The verifier's corrected values (`runs/verify_gwangyang_reloc/extra_f_within_fractions.csv`) are reproduced
  exactly.

### Issue 3: one convention for metric (c)

- Both scripts use HypoDD X/Y/Z (0.1 m) about the `hypoDD.log` centroid with unrounded half-widths, and report the
  largest |d| / half-width next to the count.
- Note 07 (against dt.cc): R1 3/11 → 2/11 (ratio 3.11); R2f 3/11 → 2/11 (2.37); R3b 3/11 → 2/11; R4 4/11 → 3/11;
  R1f, R1fz, R1fw, R3bf, R4f 5/11 and R6f, R6tf 7/11 unchanged (ratios 1.38-1.77). Horizontal shape (a) changed
  by up to 0.35 m: R1f 3.0 / 5.7 → 3.1 / 5.8 m; R1 max 8.9 → 8.8 m; dt.ct-for-scale max 59.0 → 59.3 m. Drift
  table: R1 at 20 and 40 iterations 3 → 2; R1f at 2 iterations 5 → 4. The per-event R1f table now shows
  unrounded half-widths and the ratio (event 1 dE −2.6 → −2.9 m, event 4 dE +1.2 → +0.8 m, and similar).
- Note 08 (against dt.cc): S1 H 3.0 / 5.7 → 3.1 / 5.7 m, V 4.5 / 9.6 → 4.3 / 9.2 m, 3-D max 9.7 → 9.4 m,
  inter-event RMS 5.3 → 5.2 m, 5/11 (ratio 1.47, event 9); S1h V 4.6 / 9.9 → 4.4 / 9.6 m; S2 2/11 unchanged
  (2.35); pyrtdd R1f row V 4.5 / 9.4 → 4.3 / 9.0 m; pyrtdd R1 row 3/11 → 2/11. The per-event S1 table now matches
  note 07's convention (event 9 is the largest ratio, 1.47; the six outside events miss by 0.25-1.8 m, ratios
  1.18-1.47).
- Both notes describe the convention and what it changed (07 section 4; 08 section 3 and caveats).

### Issue 4: "HypoDD's SVD pins the centroid"

- Restricted to the dt.cc run (final cumulative shift 0.0 m east, 0.0 m north, 1.0 m up, −6.3 ms) and the dt.ct
  movement quoted (22.8 m north, 71.9 m up, +148.8 ms; `hypoDD.log`, "mean centroid (origin) shift"). Note 07:
  short answer, section 3 "Centroid", section 4 (new bullet "Absolute frames differ"), section 6. Note 08: section
  4.2 ("keeps the cluster centroid fixed at the HYPOINVERSE centroid" → the restricted statement).
- The verifier's line "z −1.0" is in HypoDD's z-down frame, i.e. 1.0 m up.

### Issue 5: "same shape" wording

- Note 08 section 4.2: "S1 and S2 give the same shape" → S2 differs from S1 by 2.25 / 3.33 m RMS (largest
  4.2 / 6.1 m), as large as S1's difference from HypoDD; 2/11 inside against 5/11; S2 also changes the windows
  (new `run_vs_run.csv` and table).
- Note 07 section 6: "The shape is settled after 2-3 iterations" → R1f shape still 2.4 / 2.6 m from its final
  shape after 2 iterations, 1.0 / 1.7 m after 3, within about 1 m after 5 (0.2 / 0.7 m RMS, largest 1.6 m
  vertically); R1 1.5 / 2.7 m after 5 iterations; R0 2.7 / 7.6 m after 10. "with the same shape" for damping
  0.1 / 1.0 → R1f 0.5 / 0.7 m and 0.6 / 1.5 m RMS (vertical largest 4.3 m), R1 1.4 / 2.7 m and 1.8 / 4.2 m.
  Short answer of note 07 updated accordingly. Section 11's damping-1.0 catalog line: shape against dt.cc
  "2.9 / 3.7 m instead of 3.0 / 4.3 m" → "3.0 / 3.7 m instead of 3.1 / 4.3 m", plus "0.6 / 1.5 m RMS from R1f's
  own shape".
- The new numbers agree with the verifier's `extra_drift_shape_vs_final.csv`.

### Issue 6: CC-correlation column

- Note 08 section 4.4: the single column "CC correlation P (|CC|) / S" (0.76 / 0.69, all measured triplets, P with
  |CC|, S signed) → two column sets with the subset and sign stated: pairs where both passed, P signed / P |CC| / S
  = 0.16 / 0.69 / 0.58; all measured = 0.38 / 0.76 / 0.69 (S1). A paragraph explains why P's signed value is low
  (anti-correlated matches).
- Note 07 section 8: the column is now "CC r signed / abs" over the "in both" subset: R1f 0.23 → 0.23 / 0.65,
  R1f P 0.16 / 0.69, S 0.58 / 0.58, without event 3 0.55 / 0.83. The bullet "the CC values themselves correlate
  poorly (r 0.2-0.6)" now says that with |CC| the correlation is clearly better.

### Issue 7: S2's 0.73 km deeper centroid

- Note 08 section 4.2: "The best absolute fit with these grids ... is deeper" → called a hypothesis; the counter
  evidence is given (pyrtdd R2, same absolute picks and absoluteLocationConstraint 0.3, ended 0.42 km deeper;
  the absolute residuals are dominated by the 17 picks more than 1 s off and the ~0.27 s S−P deficit), and the test
  that would settle it (absolute-only location with and without the 17 outliers) is named as not run. No new run
  was made: it would be a new setting, not a correction.

### Issue 8: open issues in note 07 answered by note 08

- Note 07 section 1a: new bullet "Answered in step 08": `BW(4,5,20)` behaves like the causal ObsPy
  `bandpass(corners=4)`; S1 and R1f give the same lag for 2787 of 2801 phase pairs.
- Note 07 section 1b "For scrtdd": "Whether SeisComP's record stream returns traces that contain the window is
  untested" → answered: SEa used cross-correlation for 286-577 of 348-650 step-2 double differences per event
  (event 1: 399 of 478); SEm's counts equal R6f's for 10 of 11 events (new columns `step2_dd_from_xcorr`,
  `step2_dd_total` in `comparison/single_event_vs_S1.csv`).

### Issue 9: missing caveats

- Bootstrap box = HypoDD's own precision (1000 resamples from its own solution, same data and settings); event 3's
  box is 16 / 6 / 26 m; the other four inside events (2, 5, 7, 8) are among the ten well-constrained ones. Added
  to note 07 (short answer, section 10) and note 08 (main results, section 6).
- Leave-one-out background positions come from multi-event solutions that included the left-out event. Added to
  note 07 (section 7, section 10) and note 08 (section 6).

### Checks marked "unverifiable" (no separate issue number)

- Station elevations cancel in double differences: reworded in note 07 section 10 and note 08 section 6 as
  expected but not tested (no run with the stations at 0 m).
- S2's deeper centroid: see issue 7.

### Also corrected while checking

- Note 07 section 9: R6p final catalog RMS 24.0 → 23.9 ms (the file says 23.9485 ms; an old transcription slip).
- Note 07: R1's centroid "215 m west" → 214 m (the new convention; the table says −214 m).
- Notes 07 and 08: British spellings (centre, metre(s), labelled, neighbour) → American English; code identifiers
  were left as they are.

## DL picker: note 09

Done by a helper agent and checked here (signs, fractions and the centroid table were recomputed from the
files). Commands (cwd `runs/gwangyang/dlpicker`): `bash scripts/09_dlpicker.sh --apply --stage compare`,
`... --stage seisbench_compare` (new stage), `... --stage reloc` (twice), then
`python -I scripts/09_tables_md.py --run-dir $PWD > analysis/tables.md` (env pyrtdd). The pick, seisbench and
seisbench1 stages were not re-run. Logged in `logs/09_gwangyang_dlpicker_20261017.log` (21:37-21:42).

Byte-identical after the re-runs: all 33 relocated catalogs and `positions.csv`, `compare_per_event.csv`;
`dl_picks_all.csv`, `reference_vs_dl.csv`, `summary_by_model.csv` and every other analysis table except the
fast-vs-reliable ones; `compare_seisbench_vs_reference.csv` and all SeisBench picks. Only expected columns
changed elsewhere; the relocation `settings.json` and processing logs differ only in a memory address and
timestamps (a second, scratch-only run was identical after masking them).

### Issue 1: sign error in the SeisBench comparison

- `scripts/09_compare_seisbench.py`: the stored dt is negated, so `dt_plugin_minus_seisbench_s` really is plugin
  minus SeisBench (column name kept); header fixed; `sb_dt_s` documented as SeisBench − PhaseNet+ (already
  correct). New driver stage `seisbench_compare` in `scripts/09_dlpicker.sh`.
- `seisbench/compare_seisbench_pairs.csv`, `compare_seisbench_summary.json` regenerated. Mean dt:
  phasenet_instance P +0.0012 → −0.0012 s, S −0.0016 → +0.0016 s; eqtransformer_stead P −0.0023 → +0.0023 s,
  S +0.0052 → −0.0052 s.
- Note 09 section 9: new "mean dt" column; "The mean offsets are within ±0.005 s" → the four signed values, "about
  half a sample (0.005 s) or less, with both signs" (|−0.0052| was already 0.0052 s, so the old "±0.005" held only
  after rounding); a bullet records the correction.

### Issue 2: "within 0.02 s" not well defined

- `09_compare_seisbench.py` and `09_compare.py` (fast vs reliable) count in whole samples, n = round(dt × 100):
  identical n = 0, within 0.02 s |n| ≤ 2, within 0.05 s |n| ≤ 5; per-pair `dt_samples` columns. Note 09 section 1
  says so.
- Note 09 section 9, plugin vs SeisBench (within 2 samples; within 5 samples): phasenet_instance P 80 → 83 %,
  94 → 94 %; S 63 → 72 %, 94 → 96 %; eqtransformer_stead P 60 → 66 %, 93 → 94 %; S 52 → 60 %, 87 → 89 %.
  Identical unchanged (32 / 21 / 21 / 13 %). "Result in brief": "87-94 % within 0.05 s" → "89-96 %".
- Note 09 section 8 (fast minus reliable, in the windows): "91 % within 0.05 s" → 92 % within 5 samples; new
  "73 % within 2 samples"; 22 % identical and mean −0.002 s (sign checked: fast − reliable) unchanged.
  Section 11: "without changing pick times" → "with almost the same pick times (92 % within 0.05 s)".

### Issue 3: centroid shift next to metric (a) for the DL relocations

- `scripts/09_reloc.py`: pairwise centroid shifts (`centroid_shift_*` columns of `reloc/compare_pairs.csv`) and
  each solution's centroid movement from its start (new `reloc/centroid_shift_from_start.csv`, also in
  `reloc_summary.json`).
- Note 09 section 10: metric (b) defined; new column "cluster centroid moved from its start": HypoDD dt.ct 75 m,
  dt.cc 1.1 m, PhaseNet+ control 1723 m (E 1699, N 151, U 244), same-subset control 508 m, main DL solution
  82 m, matched-only 63 m, other models 320-478 m; new row for the same-subset control; pairwise: main DL vs
  control 1739 m, matched-only vs same-subset control 509 m. New caveat (section 10 and Caveats): the solutions
  sit up to 1.7 km apart; this is the known catalog-only drift (note 07 section 6,
  `logs/07_gwangyang_pyrtdd_diag_centroid_drift.log`); metric (a) stands, but a catalog-only solution's absolute
  position is not meaningful. No run with another damping or an absolute constraint was added (that would be a
  new setting). No metric-(a) number changed.

### Issue 4: wording on the weight checks

- Note 09 section 9 and "Result in brief": "differ by less than 1e-6" / "at most 5-9 × 10⁻⁷" → "about 1e-6, float32
  rounding": at most 6 × 10⁻⁷ (PhaseNet) and 9 × 10⁻⁷ (EQTransformer) on step 09's six windows, up to
  1.2 × 10⁻⁶ on the verifier's 15 other windows (`runs/verify_gwangyang_dl/out/seisbench/weights_onnx_check.json`),
  same highest sample everywhere.
- "Changes nothing (≤ 1.4 × 10⁻⁵)" limited to step 09's six windows; added: on HG windows with DC offsets of
  10⁵-10⁶ counts and weak signals, float32 vs float64 demeaning changes the input by up to 0.6 % of its peak and the
  output by up to about 3 × 10⁻³; no pick is affected (no peak within 3 × 10⁻³ of the thresholds). The DC offsets
  and peaks were read from the verifier's `runs/verify_gwangyang_dl/seisbench/phasenet_instance_weight_test_windows.npz`
  (cited; no project script writes them).

### Issue 5: sign of the DL-minus-PhaseNet+ timing offset

- Note 09 section 2: new bullet "These offsets do not say which picker is off", with the verifier's MNDB P example
  (ML 1.1 event 20260203021535: first energy at the phasenet_original pick, PhaseNet+ about 0.09 s earlier in the
  noise) and, for balance, its phasenet_instance S example (S picks 0.05-0.075 s ahead of the visible onset);
  cites `runs/verify_gwangyang_dl/notebooks/v09_waveform_examples.ipynb` and its figure. Four examples cannot settle
  the averages.

### Also changed in note 09

- British spellings (centred, normalise, uncatalogued, metres) → American English.
- `scripts/09_tables_md.py` prints the changed tables (fast vs reliable, SeisBench comparison with mean dt,
  relocation with centroid columns); `analysis/tables.md` regenerated (tables T1-T6b byte-identical).

## Real-time chain: note 10

Done by a helper agent and checked here (the diff of the note and the new latency table against the verifier's
`runs/verify_gwangyang_realtime/verify_latency.csv`). No real-time stage, replay, `rt_offline_check.py --apply`
or network port was used. Re-run: `rt_analyze.py --apply` (env pyrtdd; `logs/10_gwangyang_realtime_analyze_20261017T213910.log`)
and `rt_options.py --apply` for the five runs (SeisComP environment, `/usr/bin/timeout 300`, `python -B`;
`logs/10_gwangyang_realtime_options_20261017T214328.log`), plus dry runs of every edited driver stage.

Byte-identical after the re-run, in all five runs: `picks_vs_offline.csv`, `origins.csv`,
`positions_vs_reference.csv`, `scrtdd_relocations.csv`, `scrtdd_diagnostics_dd_counts.csv`,
`scrtdd_step1_weighting.csv`, `scxmldump_vs_sql.csv`; `delays.csv` of RT1, RT2 and RT4; and
`comparison/positions_vs_reference_all_runs.csv`, `key_position_differences.csv`,
`context_S1_vs_other_offline_solutions.csv`. The paced runs' `delays.csv`, `delays_all_runs.csv`, the
`summary.json` files and every `run_options.json` only gained new columns or keys (and a new `generated` time).
The fixes of notes 07/08 did not touch any input of `rt_analyze.py` (S1, R1, R1f, SEa, SEm, reference tables),
so no second re-run was needed.

### Issue 1: scratch files outside the project

- `runs/gwangyang/realtime/scripts/fill_rt5.py` is in the project (copied before these fixes, with one header
  line saying it filled the RT5 rows of note 10). Note 10 section 8 now lists it.
- The three files the real-time agent left in the shared session scratchpad (`msr.err`, `fill_rt5.py`,
  `__pycache__/fill_rt5.cpython-312.pyc`) were **not deleted**: the verifier left that to the user, and these
  fixes write only inside the project. The scratchpad copy of `fill_rt5.py` differs from the project copy only by
  the added header line.

### Issue 2: latency reference time

- `runs/gwangyang/realtime/scripts/rt_analyze.py`: new function `msrtsimul_clock()` (msrtsimul's own clock:
  start at the end time of the first record cut to whole seconds, read with obspy `get_record_information`) and
  24 new columns in `delays.csv`, among them `latency_*_after_S1_origin_time_msrtsimul_clock_s`,
  `final_scautoloc_origin_time_minus_S1_s` (−0.828 / −0.691 s) and
  `msrtsimul_clock_offset_minus_median_offset_s` (0.498 / 0.503 s). The old columns are unchanged.
- Note 10 says that the first-reported latencies are counted from the final scautoloc (LOCSAT) origin time, and
  gives the second set next to them: main results (13-15 s (12-14 s), 38-41 s (37-40 s), 60-63 s (59-62 s);
  RT5 59 s (58 s), 73 s (72 s), about 60 s (59 s), 233 s (231 s)), section 4.5 (new table "Second set"),
  section 6 (the first set is 1.2-1.3 s longer, not shorter: 0.69-0.83 s LOCSAT origin-time error plus about
  0.5 s from the clock definition). The second set agrees with the verifier's values to 0.01 s.
- "First scautoloc origin and event after 38-40 s" → 38-41 s: the events were created at 40.7 and 40.8 s on the
  first clock (rounding correction).
- "The pick latencies of RT3 and RT5 agree to about 1 ms" → "the first-pick times and the median pick latencies";
  one 90 % value differs by 13 ms.

### Issue 3: script versions not recorded

- Going forward: `rt_chain.py` (every `--apply` stage except status) and `rt_offline_check.py` append the md5 of
  `rt_chain.py`, `rt_options.py`, `rt_offline_check.py` and `rt_analyze.py`, the running script's md5, stage, time
  and command line to `<run>/options/script_provenance.json`, and keep a copy as
  `<run>/options/scripts/<name>.<md5>.py`. `rt_options.py` copies that list into `run_options.json`
  (`script_provenance`) and records the scripts on disk when it runs; `rt_analyze.py` writes its own md5 into
  `<run>/results/summary.json` (`rt_analyze_md5`). Checked with dry runs of every stage; no stage was applied, so
  no `script_provenance.json` exists yet.
- For RT1-RT5, `run_options.json` now says "not recorded" and lists what is known from file times
  (`script_provenance_known_from_file_times`): `rt_chain.py` was edited at 18:27 KST during RT5 (only RT5's stop and
  dump ran after it), `rt_offline_check.py` at 18:37 KST after its last `--apply` at 18:36. The exact versions
  behind RT1-RT4, RT5's prepare, start and replays, and the two offline checks cannot be recovered.
- The command-line difference is stated in note 10 (section 3 table and section 7 "Script versions") and in
  `run_options.json` (`scautoloc_timing_argument`): RT1-RT3 ran scautoloc without `--timing` (default pickTime),
  RT4 with `--timing pickTime` and RT5 with `--timing creationTime`; RT4 therefore behaves like RT1-RT3 (checked in
  each `<run>/pids.json`).

### Issue 4: S1 positions in the reference catalog

- Note 10 main results and section 6: new caveat that the reference catalog's 9 positions are S1 multi-event
  positions from an inversion that included events 3 and 9, so the agreement with S1 (61.1 m and 5.2 m) is not a
  fully independent test; a leave-two-out catalog would be needed and was not built (it would need a new
  multi-event run and new replays).

### Issue 5: "identical in every run"

- Note 10 main results and section 4.1: → "identical for every replayed event (RT1: event 3 only; RT2-RT5: both
  events)", and RT5 is now listed as identical too (checked in every run's `picks_vs_offline.csv`: RT1 112/112/112
  for event 3; RT2-RT5 112/112 and 85/85, largest time difference 0). The channels are cited from the verifier's
  `verify_picks_vs_step09.csv`, because `rt_analyze.py` matches station, method and time only.

### Also changed in note 10

- British spellings (centred, metres, behaviour, neighbours) → American English.

### Left as they are

- "scautopick makes the mb amplitude a median 14.0 s after the pick" and "the mb window ends 20.5 s after its
  reference time" (section 4.5) are not written by any project script. A scratch check from the run's
  `db_dump/sql_*.csv` gives 14.01 s (RT3) and 14.02 s (RT5); the statements were left unchanged.

## Files changed

Notes: `docs/results/07_gwangyang_pyrtdd.md`, `08_gwangyang_scrtdd.md`, `09_gwangyang_dlpicker.md`,
`10_gwangyang_realtime.md`, and this file.

Scripts (edited): `runs/gwangyang/pyrtdd/analyze_pyrtdd_gwangyang.py`, `runs/gwangyang/pyrtdd/diag_centroid_drift.py`,
`runs/gwangyang/scrtdd/scripts/scrtdd_compare.py`, `runs/gwangyang/dlpicker/scripts/{09_compare_seisbench.py,
09_compare.py, 09_reloc.py, 09_dlpicker.sh, 09_tables_md.py}`, `runs/gwangyang/realtime/scripts/{rt_analyze.py,
rt_chain.py, rt_offline_check.py, rt_options.py}`.

Scripts (new): `runs/gwangyang/pyrtdd/print_note_tables.py`, `runs/gwangyang/scrtdd/scripts/scrtdd_note_tables.py`.

Results (regenerated): `runs/gwangyang/pyrtdd/{summary_metrics, per_event_vs_reference, run_vs_run_metrics,
per_event_run_vs_run, xcorr_comparison, positions_enu}.csv`, `analysis_summary.json`, `note07_tables.md`,
`diag_centroid_drift/diag_centroid_drift.csv`; `runs/gwangyang/scrtdd/comparison/` (metrics, per-event, positions,
xcorr, single-event tables, `summary.json`, `compare_console.txt`; new `run_vs_run.csv`, `single_event_context.csv`,
`note08_tables.md`); `runs/gwangyang/dlpicker/analysis/{fast_vs_reliable.csv, summary.json, tables.md}`,
`seisbench/compare_seisbench_{pairs.csv, summary.json}`, `reloc/{compare_pairs.csv, reloc_summary.json}` (new
`reloc/centroid_shift_from_start.csv`; relocated catalogs rewritten byte-identically);
`runs/gwangyang/realtime/{RT3_paced, RT5_paced_creationtime}/results/delays.csv`, `RT*/results/summary.json`,
`RT*/options/run_options.json`, `comparison/{delays_all_runs.csv, summary_all_runs.json}`.

Logs (new): `logs/07_gwangyang_pyrtdd_analysis_after_verification_20261017.log`,
`logs/08_gwangyang_scrtdd_compare_apply_2026-10-17T2138.log`, `...T2140.log`, appended runs in
`logs/09_gwangyang_dlpicker_20261017.log`, `logs/10_gwangyang_realtime_analyze_20261017T213910.log`,
`logs/10_gwangyang_realtime_options_20261017T214328.log` and dry-run logs of the edited real-time drivers.

- note 07 section 1a and check_filter_reaches_libhdd.py: the sign-flip filter case is not diagnostic (negating both traces leaves CC unchanged); reworded 2026-10-17 after notebook 02's cross-checks. The conclusion rests on the band-pass, low-pass and zeroing cases and on R1f matching scrtdd S1.
- note 09 section 7: 'SeisBench 1 thread = 2.7 times the plugin' corrected to 2.8 (23.83 / 8.64 = 2.76), found by notebook 03's cross-checks.
- note 10: event 9's 'first DL pick 13.3 s' is a noise pick at HCNA timed 20.1 s before the origin; the earthquake's own first pick was created after 15.3 s and the first pick used by an origin after 19.3 s (found by notebook 04's cross-checks). Text and table footnote corrected.
- note 11 (San Ramon relocation), corrected after notebook 06's 108-number cross-check (103 matched):
  - the absLocConstraint-0 "4.1–4.5 km upward drift" is the offset from LDEO's centroid; measured from the NCSS start the drift is 4.5–4.9 km;
  - "median-offset variant changes rtDD numbers by ≤ 10 m" holds against LDEO (≤ 9.3 m), not against NCEDC DD (up to 19.7 m);
  - P1's log counts 173,001 accepted P correlations vs 173,002 in its cache (one coefficient at exactly 0.700000);
  - event 72544210: 9 lags differ (8 by 1 ms), not only the NC.CBR S lag; its S1 position is S35°E of P1, not due south;
  - added: one P correlation flips sign between pyrtdd and scrtdd (BK.BDM);
  - "moves the cluster to where the biased CON-grid times fit best" reworded: rtDD's own per-event absolute RMS rises slightly (235 → 243–247 ms), so the better-fit reading is not confirmed.
- note 12 (San Ramon DL picker), corrected after notebook 07's 47-statement cross-check (43 matched): eqtp_ncedc best value ≤ 0.1 in 92 (not 81) cases; CPU ratio 16-18x (not 16x for all PhaseNet models); 'none within 120 s' holds 16 (not 15) events; DP precision 0.60 is over 15 DL picks (7 is the analyst-pick count); the EH+HN stations' HN records are mostly continuous (385 of 399 complete), not triggered; of the 1502 'triggered' records 47 have a gap and 13 start at the file start.
- note 13: 'automatic-only events relocated about as well as analyst events' reworded to 'only somewhat farther' (local horizontal 172 vs 137 m), as notebook 08 found.
