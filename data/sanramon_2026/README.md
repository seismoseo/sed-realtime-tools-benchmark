# San Ramon 2025-26 sequence benchmark (Calaveras fault, East Bay, California)

Third benchmark of the SeisComP / rtDD / DL-picker test, prepared exactly like the 2015 San Ramon swarm
benchmark (`../sanramon_2015/`), with only the period, box, swarm centre and paths changed. The largest event
is Mw 4.18, NCSS id 75305736, 2026-02-02 15:01:13.64 UTC
(https://earthquake.usgs.gov/earthquakes/eventpage/nc75305736/executive).
The full description, with every source, number, difference from 2015 and caveat, is in
**`docs/sanramon2026_inputs.md`**; the waveform checks are in **`docs/sanramon2026_waveforms.md`**
(both from the project root).

Benchmark: NCSS events from 2025-10-01 00:00 to 2026-10-18 00:00 UTC (end excluded) whose routine or NCEDC
double-difference location lies in lat 37.70-37.80, lon -122.01..-121.89.

| Folder | Contents |
|---|---|
| `reference/` | raw downloads as served: NCEDC catalog answers (`ncedc_catalog/`), LDEO pages and the LDEO real-time DD catalog `NCAeqDDRT.v202201` (`ldeo/`), QuakeML (`fdsn_event/`), StationXML pieces (`stationxml/`), documentation (`docs/`, mostly copied from the 2015 download of 2026-10-17), the NCSS Hypoinverse set-up (`ncss_hypoinverse_metadata/`), waveform answers (`waveforms_raw/`, each with a `.json` manifest) and probes (`waveforms_probe/`). `usgs_oaf/` (USGS aftershock forecast of the mainshock) was placed there before this work package and is described by its own `PROVENANCE.md`. `PROVENANCE.md` lists every file with its source URL and md5 |
| `reference_tables/` | tidy tables made from the raw files: `dd_catalog.csv` (NCEDC DD, the designated reference), `ldeo_ddrt_catalog.csv` (LDEO DD-RT, supplementary), `ncss_catalog.csv`, `picks_ncss.csv`, `event_id_map.csv`, `event_matching.csv`, `location_differences.csv`, `dd_version_comparison.csv`, `ncss_model_weights.csv`, `station_channels.csv`, `summary_counts.csv`, `comparison_with_2015.csv`, `stations_2015_vs_2026.csv`, NonLinLoc and waveform check tables, `stats_*.json` |
| `inputs/` | what the next phases use: `rtdd_catalog/` (station/event/phase csv for scrtdd/pyrtdd, plus `phase_extra.csv`), `stations.xml`, `velocity_model.{csv,md}`, `nll_con_tm/` (NonLinLoc TRANS_MERC control files; grids in `nll_con_tm/time/`, model name `sanramon2026_con`), `dl_subset_events.csv`, `waveform_plan_*.csv`, `sds/` (SDS archive, cross-correlation windows of all events, for rtDD `-I sdsarchive://`), `playback/<eventid>.mseed` (one time-sorted file per DL-picker test event) |
| `tools/` | the scripts that made everything, numbered in run order (env `pyrtdd`, `python -I <tool>`), copied from `../sanramon_2015/tools/` and parametrised in `tools/sr_common.py` (period, boxes, centre, mainshock, model name, log file). New: `21_compare_with_2015.py` |

The starting locations in `inputs/rtdd_catalog/event.csv` are the NCSS **routine** locations. The DD catalogs
are kept apart as references. Every HTTP request is logged in `logs/sanramon2026_requests.tsv`.
