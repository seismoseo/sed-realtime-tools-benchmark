# San Ramon 2025-26 benchmark: waveforms and their checks

Written 2026-10-18. The waveforms were downloaded by `data/sanramon_2026/tools/download_waveforms.py` (a copy of the
2015 downloader; only paths, log names, user agent and mainshock id changed) and checked by `check_waveforms.py`,
`check_waveforms_seiscomp.sh` and `check_playback_sort.py` (copies of the 2015 checks). The checks only read the
data. Read together with `docs/sanramon_waveforms.md` (2015); the methods are the same.

## Short answer

- **Both sets are complete as far as the data centres hold data.** All 1,036 requests (NCEDC 927 cc + 104 dl,
  EarthScope 1 + 4 fallback) answered HTTP 200 at the first attempt; no retry, no failure; `DONE_cc` and `DONE_dl`
  written.
- **Cross-correlation archive (`inputs/sds/`):** 62,246 event windows (927 events × the channels of the sensors that
  picked each event, ≤ 60 km). **62,008 have data, 61,943 are complete in one piece.** The 238 windows without data
  are almost all one station outage (NC.CNI, 192 windows) and **a 2-minute NCEDC archive gap**
  (2026-02-09 22:04:55–22:06:54 UTC) that swallows event 75311457 (Md 1.47) at all NC, CE and NP stations.
- **Picks:** 31,634 of the 31,745 phase.csv picks on requested sensors (99.7 %) have data over rtDD's whole
  cross-correlation window on the components rtDD uses; that is **75.6 % of all phase.csv picks** (P 73 %, S 99.3 %);
  the rest are beyond 60 km by design (2015: 85 %; the 2025-26 picks reach farther).
- **Timing is consistent with the analyst picks:** AIC onset minus pick median +0.01 s, MAD 0.01 s; 94.5 % within
  0.05 s for SNR ≥ 5 (10,018 picks).
- **SeisComP reads the archive:** `scart --check` found no issue in 18,868 day files; the `sdsarchive` record stream
  returned every requested stream for the two test events (304 of 304, 452 of 452).
- **DL playback files (26 events):** every analyst pick of the subset on a planned sensor has data on its channel,
  except 2 P picks at NC.CNI (outage). Files hold the same records as `scmssort -E -u` would write, without
  duplicates; the order differs only by the end-time definition (max 23 ms), exactly as in 2015.
- **Two metadata problems to know:** BK.CMSB.00.HN? records at 200 Hz but `stations.xml` says 100 Hz until
  2026-03-13 (14 cc windows); BK.WEBR.00.HN? elevation 2.8 m from 2026-01-28 (see `sanramon2026_inputs.md` §4).

## 1. What was run

| Step | Tool (env pyrtdd, `python -I`) | Output | Log |
|---|---|---|---|
| probes before the download | `19_probe_waveform_services.py` (probes 1–4) | `reference/waveforms_probe/` | `logs/sanramon2026_19_probe_waveform_services.log` |
| download + build | `download_waveforms.py --set both` (04:24:50–05:09:26 UTC, 2,677 s) | `inputs/sds/`, `inputs/playback/`, `reference/waveforms_raw/` (each answer with a `.json` manifest), `reference_tables/waveform_requests_{cc,dl}.csv`, `waveform_sources_{cc,dl}.csv` | `logs/sanramon2026_waveforms_20261018.log`; every request also in `logs/sanramon2026_requests.tsv` |
| obspy read-back, day files, playback, pick coverage, AIC timing | `check_waveforms.py --workers 8` | `reference_tables/waveform_coverage_{cc,dl}.csv`, `waveform_pick_coverage.csv`, `waveform_dayfile_check.csv`, `waveform_missing_by_channel.csv`, `waveform_aic_vs_picks.csv`, `stats_20_waveforms.json` | `logs/sanramon2026_check_waveforms_20261018.log` |
| SeisComP readers | `check_waveforms_seiscomp.sh` (scart --check; scart -I sdsarchive:// for 75283011 and 75305736; scmssort -E -u) | `runs/sanramon2026_waveform_checks/` | `logs/sanramon2026_check_waveforms_seiscomp_20261018.log` |
| why scmssort differs | `check_playback_sort.py` (copy of `runs/sanramon/waveforms/check_playback_sort.py`) | `runs/sanramon2026_waveform_checks/playback_sort_check.csv` | `logs/sanramon2026_check_playback_sort.log` |
| gap probe after the download | `19_probe_waveform_services.py 5` | `reference/waveforms_probe/ncedc_dataselect_gap_75311457.mseed` | same as probes |

Not repeated from 2015: the band-selection SNR analysis (`runs/sanramon/waveforms/band_selection.py`).

## 2. The download

- **Probes (before):** EarthScope's availability service is still retired (`/fdsnws/availability/1/extent`: HTTP 404
  "This service has been retired"; `station?matchtimeseries=true`: 410). NCEDC dataselect answers a bulk POST with
  4096-byte Steim2 records (2015: the builder rewrites everything to 512-byte records anyway); a channel without
  data gives HTTP 204.
- **Plan** (`waveform_requests_*.csv`):
  - cc: 927 events, 62,246 request lines (one request per event, ≤ 500 lines), 692 distinct channels; window
    origin −10 s to +30 s; every component of every sensor carrying a pick of that event within 60 km.
  - dl: 26 events, 20,435 lines in 104 requests (≤ 240 lines), 806 distinct channels; origin −120 s to +120 s; every
    channel in `stations.xml` of every sensor within 80 km, picked or not.
- **Requests:** NCEDC cc 927 (604 MB, median 2.6 s, max 31 s), NCEDC dl 104 (587 MB, median 9.4 s); EarthScope
  fallback cc 1 request (313 joined lines, 1.0 MB), dl 4 requests (1,940 lines, 4.0 MB). At most 2 requests at a
  time, ≥ 0.5 s between starts. All 200, no retries.
- **EarthScope fallback:** 319 cc lines (94 channels, 78 events) and 2,062 dl lines (158 channels) had no NCEDC data.
  EarthScope returned data for **51 channels = the 17 NC C0xx/J0xx strong-motion sites (`.01.HN?`) still picked in
  2025-26** (C001, C006, C015, C021, C031, C033, C049, C055, C056, C062, C067, C071, C073, J020, J025, J032, J043):
  NCEDC serves none of their 2025-26 data. (2015: the cc set needed no fallback.)
- **SDS archive (`inputs/sds/`):** 18,868 day files for 692 channels, 318 MB (337 MB on disk), 621,361 records of 512
  bytes, 59,484 traces, 275.7 million samples. No overlapping traces, no foreign channel in a file, no trace outside
  its UTC day.
- **Raw answers kept:** `reference/waveforms_raw/` 2,078 files, 1.2 GB.
- **Sampling rates** in the data agree with `stations.xml` for every window except BK.CMSB.00.HN? (data 200 Hz, metadata
  100 Hz for all 14 windows, 2025-11-09 to 2026-03-02; the 200 Hz epoch starts only on 2026-03-13). Rates seen: BH
  40 Hz; CN, DP 500 Hz; EH, HH 100 Hz; EP, HN 100 or 200 Hz.

## 3. Cross-correlation set: coverage and gaps

| | windows | with data | complete, one piece |
|---|---:|---:|---:|
| all | 62,246 | 62,008 | 61,943 |
| HN | 21,570 | 21,549 | 21,527 |
| EH | 19,437 | 19,232 | 19,192 |
| HH | 16,830 | 16,821 | 16,818 |
| EP | 3,252 | 3,249 | 3,249 |
| DP | 629 | 629 | 629 |
| BH | 324 | 324 | 324 |
| CN | 204 | 204 | 204 |

By network (windows with data / windows): NC 28,784 / 29,004, BK 17,135 / 17,144, NP 10,026 / 10,032, CE 3,597 / 3,600,
PB 1,977 / 1,977, WR 489 / 489. 639 of the 692 channels are complete in every window; none is empty in all.

**Where data are missing** (`waveform_missing_by_channel.csv`, `waveform_coverage_cc.csv`):
- **NC.CNI EH? (16.8 km):** 64 of 594 windows without data and 11 partial per component, 2025-11-10 to 2026-02-25
  (station outages).
- **Event 75311457** (2026-02-09 22:05:12.11, Md 1.47, 'F', 21 P picks): no data on 33 of its 51 lines: all NC, CE and NP
  channels; BK and PB channels are fine. A 10-minute NCEDC request after the download (probe 5) shows that NC.CBR EHZ
  and NC.CSR HNZ both stop at 22:04:55 and resume at 22:06:54: **a 2-minute hole in the NCEDC archive**, not a
  download problem; EarthScope had nothing either.
- Otherwise single windows: BK.TESL (3 windows on 2026-02-05), NC.CAP, NC.CLCB, NC.CRPB, NC.CSL, NP.1863 (12 partial),
  NP.LVA4 (6 partial), NP.1786 (3 partial) — late starts and short records of triggered or intermittent stations.

**Pick coverage** ("rtDD components" = P on the sensor's vertical, S on both horizontals; window = rtDD's default
cross-correlation window plus margins, as in 2015):

| phase | type | picks in phase.csv | ≤ 60 km (requested) | data on picked channel | data on rtDD components | usable |
|---|---|---:|---:|---:|---:|---:|
| P | EH | 20,218 | 14,848 | 14,769 | 14,769 | 73 % |
| P | HH | 9,697 | 5,578 | 5,574 | 5,574 | 57 % |
| P | HN | 6,208 | 5,892 | 5,887 | 5,887 | 95 % |
| P | EP | 1,122 | 1,082 | 1,082 | 1,082 | 96 % |
| P | DP | 508 | 234 | 234 | 234 | 46 % |
| P | BH | 108 | 107 | 107 | 107 | 99 % |
| P | CN | 68 | 67 | 67 | 67 | 99 % |
| **P** | **all** | **37,929** | **27,808** | **27,720** | **27,720** | **73.1 %** |
| S | HN | 2,301 | 2,299 | 2,296 | 2,296 | 99.8 % |
| S | EH | 690 | 688 | 675 | 670 | 97 % |
| S | HH | 631 | 631 | 631 | 631 | 100 % |
| S | EP | 293 | 293 | 292 | 292 | 99.7 % |
| S | DP | 23 | 23 | 23 | 22 | 96 % |
| S | CN | 3 | 3 | 3 | 3 | 100 % |
| **S** | **all** | **3,941** | **3,937** | **3,920** | **3,914** | **99.3 %** |
| **all** | | **41,870** | **31,745** | **31,640** | **31,634** | **75.6 %** |

- Lost by design: picks beyond 60 km (10,121 P, 4 S). Many more distant HH/EH/DP picks than in 2015.
- Lost to gaps: 105 picks (88 P, 17 S): NC.CNI 81, event 75311457 19, others 5.
- S picks on sensors without two horizontals: 6 (NC.CLCB, CSL, CRH EHZ; BK.RB2B DP2), against 83 in 2015.

**Timing check** (`waveform_aic_vs_picks.csv`; analyst P picks, weight 0–1, ≤ 30 km, vertical channels; AIC in pick
−1.0…+0.5 s after a one-pass 1 Hz high-pass), AIC minus pick:

| subset | n | median | MAD | within 0.05 s | within 0.10 s |
|---|---:|---:|---:|---:|---:|
| all | 13,336 | +0.010 s | 0.010 s | 89.1 % | 94.3 % |
| SNR ≥ 5 | 10,018 | +0.010 s | 0.010 s | 94.5 % | 98.1 % |
| SNR ≥ 5, weight 0 | 6,586 | +0.008 s | 0.008 s | 96.8 % | 98.8 % |

Medians by channel type (SNR ≥ 5): BH +0.010, DP +0.010, EH +0.010, EP +0.005, HH +0.008, HN +0.010 s. No sign of a
clock or time-stamp offset in any network; the +0.01 s is the usual AIC-vs-first-break bias (2015: the same).

## 4. SeisComP's view (what scrtdd reads)

- `scart --check inputs/sds`: "Found issues in 0/18868 files".
- `scart -I sdsarchive://…/inputs/sds --test --print-streams` with the cc request lines:
  - 75283011 (Md 2.29, the overlap test event): 304 of 304 streams;
  - 75305736 (Mw 4.18): 452 of 452 streams.

## 5. DL-picker playback files (`inputs/playback/<id>.mseed`)

- **26 files, 518 MB** (675–780 channels each), 512-byte records, sorted by record end time (obspy's definition),
  no overlaps, no unrequested channel.
- **Request lines:** 20,435; 18,511 with data; 18,336 complete. Most lines without data are channels with no pick in
  that event, mainly triggered strong-motion recorders (HN: 12,423 of 14,136 lines with data). 10 channels never have
  data in these windows: CE.57254.10.HN? (22.9 km), NC.CMLP EHZ + HN? (35.1 km), NP.MOD.01.HH? (73.3 km).
  138 lines were filled from EarthScope (the NC C0xx/J0xx sites).
- **Analyst picks of the 26 events on planned sensors:** 2,402 (2,365 in phase.csv); 2,400 have data on the picked
  channel, 2,400 continuous data from pick −10 s to +10 s, 2,400 data on the components rtDD would correlate. The 2
  missing are P picks at NC.CNI (events 75283066, 75285161; outage).
- **`scmssort -E -u`:** the shell check reports "DIFFERENT" for all 26 files; `check_playback_sort.py` shows that
  scmssort writes exactly the same records (same multiset, no duplicates) and that the order differs only because
  the downloader sorts by the time of the last sample while scmssort sorts by last sample + one sample interval
  (26 of 26 each). Largest displacement 22.8 ms; harmless for `msrtsimul`. Pipe a file through `scmssort -E -u` once
  if strict SeisComP order is wanted.

## 6. Differences from 2015 that matter downstream

| | 2015 | 2025-26 |
|---|---|---|
| cc windows / complete | 42,083 / 42,037 | 62,246 / 61,943 |
| day files | 7,799 | 18,868 (one year of event days) |
| phase.csv picks with usable cc data | 85 % | 75.6 % (more picks beyond 60 km) |
| S picks lacking two horizontals | 83 | 6 |
| EarthScope fallback, cc | none | 17 NC C0xx/J0xx strong-motion sites (all their data) |
| known archive gap | none | NCEDC NC/CE/NP 2026-02-09 22:04:55–22:06:54 (event 75311457) |
| metadata/data mismatch | none | BK.CMSB.00.HN? 200 Hz data vs 100 Hz metadata before 2026-03-13 |
| AIC − pick (SNR ≥ 5) within 0.05 s | 97.8 % | 94.5 % |
