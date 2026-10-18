# San Ramon 2015 benchmark: waveform checks (work package SR-B)

Written 2026-10-17 (KST). The waveforms were downloaded by `data/sanramon_2015/tools/download_waveforms.py`
(log `logs/sanramon_waveforms_20261017.log`, which ends with `DONE cc` and `DONE dl`). The checks below were run
afterwards. They only read the data; nothing was downloaded or changed.

## Short answer

- **The cross-correlation archive is complete and clean.**
  - Every one of the 42,083 requested event windows (685 events × the channels of the sensors picked in that
    event, ≤ 60 km) has data.
  - 42,037 windows (99.9 %) are complete and in one piece. The 46 others (16 events) are listed in section 3.
  - None of these gaps removes data that rtDD needs. Every pick whose sensor has the components rtDD
    correlates has data over rtDD's whole cross-correlation window (P on the vertical, S on both horizontals).
- **85 % of the picks in rtDD's `phase.csv` have waveforms** (21,921 of 25,684). The other 15 % are on
  stations farther than 60 km, which were not requested by design.
  - P: 83 % (18,788 of 22,545).
  - S: 99.8 % (3,133 of 3,139). 83 S picks are on vertical-only sensors, so rtDD's default S component (L2, both
    horizontals) cannot use them. That leaves **97 %** of S picks correlatable.
- **Timing is consistent with the analyst picks.** An automatic onset (AIC) on the downloaded data falls a median
  of +0.01 s from the analyst P pick (MAD 0.01 s; 97.8 % within 0.05 s; 6,665 picks with SNR ≥ 5).
- **SeisComP reads the archive.**
  - `scart --check` found no issues in any of the 7,799 day files.
  - SeisComP's `sdsarchive` record stream (what scrtdd uses) returned every requested stream for two test events
    (178 and 409 of 178 and 409 lines).
- **DL-picker playback files (26 events) are complete for every picked channel.**
  - They hold the same records as `scmssort -E -u` would write and contain no duplicates.
  - The record order differs from scmssort's only because the two programs define "record end time" differently.
    Records move by at most 22 ms (section 5).

## 1. What was run

| Check | Tool | Output |
|---|---|---|
| Read-back of every cc window with obspy's SDS client; day-file integrity; playback windows; pick coverage; AIC timing check | `data/sanramon_2015/tools/check_waveforms.py --workers 8` (env pyrtdd, about 2 min) | `reference_tables/waveform_coverage_{cc,dl}.csv`, `waveform_pick_coverage.csv`, `waveform_dayfile_check.csv`, `waveform_missing_by_channel.csv`, `waveform_aic_vs_picks.csv`, `stats_20_waveforms.json`; console `logs/sanramon_check_waveforms_20261017.log` |
| SeisComP's own readers: `scart --check`, `scart -I sdsarchive://` for events 72540760 and 72540765, `scmssort -E -u` on the playback files | `data/sanramon_2015/tools/check_waveforms_seiscomp.sh` | `runs/sanramon_waveform_checks/`; console `logs/sanramon_check_waveforms_seiscomp_20261017.log` |
| Why scmssort's output differs from the playback files | `runs/sanramon/waveforms/check_playback_sort.py` (new) | `runs/sanramon/waveforms/playback_sort_check.csv` |
| Pick coverage by phase and channel type; list of gaps | `runs/sanramon/waveforms/summarize_waveform_checks.py` (new) | `runs/sanramon/waveforms/pick_fraction_by_channel_type.csv`, `partial_windows_cc.csv`, `partial_windows_affecting_picks.csv`; `logs/11_sanramon_waveform_summary.log` |
| Signal-to-noise ratio by frequency in rtDD's windows (used to choose the cross-correlation band) | `runs/sanramon/waveforms/band_selection.py` (new) | `runs/sanramon/waveforms/band_snr_*.csv/json`; `logs/11_sanramon_band_selection.log` |

## 2. The download

- **One main run:** 2026-10-17 04:53:59 to 05:31:17 UTC (2,238 s).
- **Requests (all runs):**
  - NCEDC, cc set: 685 requests (683 in the main run; 2 were already on disk from a test), 576 MB.
  - NCEDC, dl set: 78 requests, 574 MB.
  - EarthScope, dl set only: 13 requests. 10 returned data (12.7 MB); 3 answered 204 (no data).
  - No request failed and none needed a retry. The cc set needed no EarthScope fallback: NCEDC answered every
    line.
- **SDS archive (`inputs/sds/`):**
  - 7,799 day files for 654 channels: the 652 planned channels plus the 3 wildcard components of NC.J053.01.HN?,
    which has no metadata.
  - 298.6 MB; 583,134 records of 512 bytes; 39,982 traces; 245.5 million samples.
  - No overlapping traces, no file holding a foreign channel, no trace outside its UTC day.
- **Sampling rates in the data agree with `stations.xml` for every window:**

  | Channel type | Rate |
  |---|---|
  | BH | 40 Hz |
  | CN, DP | 500 Hz |
  | EH, EP, HN | 100 or 200 Hz |
  | EL, HH | 100 Hz |

## 3. Cross-correlation set: coverage and gaps

**Request windows** (origin −10 s to +30 s; 685 events; 652 channels; all ≤ 60 km):

| | windows | with data | complete, one piece |
|---|---:|---:|---:|
| all | 42,083 | 42,083 | 42,037 |
| EH | 14,973 | 14,973 | 14,966 |
| HN | 11,363 | 11,363 | 11,329 |
| HH | 7,926 | 7,926 | 7,926 |
| EP | 5,638 | 5,638 | 5,636 |
| CN | 1,636 | 1,636 | 1,636 |
| DP | 439 | 439 | 439 |
| BH | 66 | 66 | 66 |
| EL | 42 | 42 | 42 |

By network: NC 24,998 windows, BK 11,712, NP 3,219, PB 2,154. All have data.

**The 46 windows that are not complete and in one piece** (`runs/sanramon/waveforms/partial_windows_cc.csv`):

- **Late start or early end of triggered strong-motion recorders** (HN):
  - NC C027/C028/C029.01, NC CUSLD.03, NP 1690/1844/1739, NC CSL.
  - Coverage 60–99 %; worst is event 72540750 at 79 % on 15 channels.
- **Short or broken EH/EP records:**
  - NC NCC: 3 pieces, and 63 % in one event.
  - NC CPI: 2 pieces.
  - NC JCH: 68 %.
  - NC CPM: 77 %.
  - NC CSPB, NC CCH1 EP1/EP3: 97–99 %.
- **NC.J053.01.HN?** (5 windows): counted as "3 pieces" only because the wildcard request returns three
  channels. Coverage is 100 %.

**Do these gaps matter?** Only 6 picks lack data over rtDD's cross-correlation window on a component that exists:

- 5 are J053 HNZ P picks. These are not in `phase.csv` (weight codes 6–8, no metadata).
- 1 is a P pick on NC.NRL ELN. That sensor has only E and N channels, so rtDD's P component "Z" does not exist
  there.

So for every pick in `phase.csv`, the gaps cost nothing.

**Pick coverage** (`pick_fraction_by_channel_type.csv`). "rtDD components" means the components rtDD cross-correlates:
P on the sensor's vertical (Z, or 1 for borehole sensors named 1/2/3), S on both horizontals (L2).

| phase | channel type | picks in phase.csv | ≤ 60 km (requested) | data on picked channel | data on rtDD components | fraction usable |
|---|---|---:|---:|---:|---:|---:|
| P | EH | 13,655 | 10,440 | 10,440 | 10,440 | 76 % |
| P | HH | 3,128 | 2,642 | 2,642 | 2,642 | 84 % |
| P | HN | 2,951 | 2,940 | 2,940 | 2,940 | 99.6 % |
| P | EP | 1,908 | 1,894 | 1,894 | 1,894 | 99.3 % |
| P | CN | 519 | 519 | 519 | 519 | 100 % |
| P | DP | 359 | 332 | 332 | 332 | 92 % |
| P | BH | 24 | 20 | 20 | 20 | 83 % |
| P | EL | 1 | 1 | 1 | 0 | 0 % |
| **P** | **all** | **22,545** | **18,788** | **18,788** | **18,787** | **83 %** |
| S | HN | 1,387 | 1,386 | 1,386 | 1,386 | 99.9 % |
| S | EH | 888 | 885 | 885 | 802 | 90 % (83 on vertical-only sensors) |
| S | EP | 555 | 555 | 555 | 555 | 100 % |
| S | HH | 160 | 158 | 158 | 158 | 99 % |
| S | CN | 127 | 127 | 127 | 127 | 100 % |
| S | EL | 20 | 20 | 20 | 20 | 100 % |
| S | BH | 2 | 2 | 2 | 2 | 100 % |
| **S** | **all** | **3,139** | **3,133** | **3,133** | **3,050** | **97 %** |
| **all** | | **25,684** | **21,921** | **21,921** | **21,837** | **85 %** |

All picks that were requested have data. The only losses are:
- by design: stations beyond 60 km (3,757 P picks and 6 S picks);
- vertical-only sensors for S (83 picks).

**Timing check** (`waveform_aic_vs_picks.csv`). Method:
- picks: analyst P picks of weight 0–1, at ≤ 30 km, on vertical channels (8,015 picks);
- AIC onset searched from 1.0 s before to 0.5 s after the pick, after a one-pass 1 Hz high-pass.

Result, AIC minus pick:

| subset | n | median | MAD | within 0.05 s |
|---|---:|---:|---:|---:|
| all | 8,015 | +0.010 s | 0.010 s | 95.5 % |
| SNR ≥ 5 | 6,665 | +0.010 s | 0.010 s | 97.8 % |
| SNR ≥ 5, weight 0 | 4,023 | +0.010 s | 0.010 s | 99.2 % |

The medians are similar for every channel type: +0.003 to +0.010 s for CN, DP, EH, EP, HH and HN; +0.025 s
for the 5 BH picks.

There is no sign of a clock or time-stamp offset in any network. The +0.01 s median is one 100 Hz sample. It is
the expected bias of an AIC picker against an analyst's first-break pick.

## 4. SeisComP's view (what scrtdd reads)

- **`scart --check`:** "Found issues in 0/7799 files".
- **Record-stream read** (`scart -I sdsarchive://... --test --print-streams` with the cc request lines):
  - event 72540760 (Md 2.32): 178 of 178 streams returned;
  - event 72540765 (Mw 3.6, the mainshock): 409 of 409 streams returned.

## 5. DL-picker playback files

- **Files:** 26 files in `inputs/playback/` (one per event of `dl_subset_events.csv`), 515 MB.
- **Contents:** 512-byte records with no overlaps and no unrequested channels.
- **What was requested** (as downloaded; `download_waveforms.py` uses `DL_MAX_KM = 80` and
  `DL_WIN = (−120, +120)` s):
  - every channel in `stations.xml` of every sensor within **80 km**;
  - window **origin −120 s to +120 s**.
  - Section 8 of `docs/sanramon_inputs.md` describes a plan of 120 km and −60 s to +120 s instead.
  - In all, 17,860 request lines, for 688 channels.
- **Coverage of the request lines:**
  - 13,189 lines have data and 8,479 are complete.
  - Most lines without data are channels with no pick in that event. Many of them belong to triggered
    strong-motion recorders (HN: 8,190 of 12,558 lines have data, 3,516 are complete).
  - 7 channels never have data in these windows: NC CAL, CPM, JSA and JSB EHZ; NC CSU1 EP1–3. They do have
    data in other events' cc windows.
- **Picked channels:**
  - all 1,901 picked-channel lines have data;
  - all 1,904 analyst picks of the 26 events on sensors of the plan have data on the picked channel;
  - 1,903 have continuous data from pick −10 s to pick +10 s;
  - 1,902 have data on the components rtDD would correlate.
- **`scmssort -E -u` comparison:**
  - The shell check reported "DIFFERENT" for all 26 files. `check_playback_sort.py` shows why.
  - scmssort writes the same records (same count, same multiset of bytes, no duplicates).
  - The order differs because of two definitions of "record end time":
    - the downloader sorted by obspy's end time, the time of the last sample (`file_sorted_by_last_sample`
      = True for 26 of 26 files);
    - scmssort sorts by SeisComP's end time, the last sample plus one sample interval
      (`scmssort_sorted_by_last_plus_dt` = True for 26 of 26).
  - Records of channels with different sampling rates therefore swap places. The largest displacement is
    22 ms.
  - This is harmless for `msrtsimul` playback. If strict SeisComP order is wanted, pipe each file through
    `scmssort -E -u` once.

## 6. Signal band in rtDD's cross-correlation windows

`runs/sanramon/waveforms/band_selection.py` measures the signal-to-noise ratio by frequency for every pick that has
rtDD components:
- 18,785 P picks (vertical) and 3,050 S picks (both horizontals);
- signal window = rtDD's default cross-correlation window;
- noise window = the same length, ending 1 s before P.

Median amplitude SNR in 1/3-octave bands:

| | 1 Hz | 1.6 Hz | 2 Hz | 4 Hz | 8 Hz | 12.5 Hz | 16 Hz | 20 Hz | 25 Hz |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P, all | 1.8 | 2.8 | 3.3 | 5.4 | 7.8 | 7.1 | 5.5 | 3.8 | 2.6 |
| P, M < 1 | 1.2 | 1.6 | 1.9 | 2.9 | 6.1 | 6.5 | 5.1 | 3.9 | 2.6 |
| P, 30–60 km | 1.5 | 2.2 | 2.8 | 4.2 | 6.6 | 4.3 | 3.1 | 2.3 | 1.6 |
| S, all | 4.0 | 7.9 | 10.9 | 29.9 | 31.4 | 12.3 | 5.8 | 2.8 | 1.6 |
| S, M < 1 | 2.0 | 2.8 | 4.2 | 16.2 | 19.3 | 7.2 | 3.1 | 1.7 | 1.2 |

The usable band is about 2–16 Hz:
- **P:** the median SNR reaches 3 at about 2 Hz (4–5 Hz for M < 1) and falls below 3–4 above 20 Hz.
- **S:** the median SNR is above 3 from 1 Hz to 16 Hz and drops quickly above 16 Hz.
- **BH channels:** the 40 Hz channels cannot carry anything above their 20 Hz Nyquist frequency.

This supports the 1.5–15 Hz band-pass of the cross-correlation runs. It is also the band Waldhauser & Schaff
(2008) used for the NCSN data of the LDEO reference catalog. See `docs/results/11_sanramon_relocation.md`.

Note: the windows are 1–1.5 s long, so bands below about 1 Hz are poorly resolved. The 0.63 Hz band is empty
because of the FFT spacing.
