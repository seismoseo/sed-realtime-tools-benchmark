# San Ramon 2015 swarm benchmark (Calaveras fault, East Bay, California)

Second benchmark of the SeisComP / rtDD / DL-picker test. The largest event is Mw 3.6, NCSS id
72540765, 2015-10-19 23:21:17.68 UTC (https://earthquake.usgs.gov/earthquakes/eventpage/nc72540765/executive).
The full description, with every source, number and caveat, is in
**`docs/sanramon_inputs.md`** (from the project root).

| Folder | Contents |
|---|---|
| `reference/` | raw downloads as served: NCEDC catalog answers, LDEO DD catalog, QuakeML, StationXML pieces, documentation PDFs and pages. `PROVENANCE.md` lists each file with its source URL and md5. Waveforms (SR-B): `waveforms_raw/` holds every NCEDC/EarthScope dataselect answer as served, each with a `.json` manifest (request lines, HTTP status, bytes, seconds); `waveforms_probe/` holds the answers of the probe requests made before the download |
| `reference_tables/` | tidy tables made from the raw files: DD catalogs, NCSS catalog and picks, id matching, location differences, station channels, summary counts, validation results, `stats_*.json` |
| `inputs/` | what the next phases use: `rtdd_catalog/` (station/event/phase csv for scrtdd/pyrtdd), `stations.xml`, `velocity_model.{csv,md}`, `nll_con/` (NonLinLoc control files; grids in `nll_con/time/`), `dl_subset_events.csv`, `waveform_plan_*.csv`. Waveforms (SR-B, **`docs/sanramon_waveforms.md`**): `sds/` (SDS archive, cross-correlation windows of all 685 events, for rtDD `-I sdsarchive://`), `playback/<eventid>.mseed` (one time-sorted file per DL-picker test event) |
| `tools/` | the scripts that made everything, numbered in run order (env `pyrtdd`, `python -I <tool>`). Waveforms: `19_probe_waveform_services.py`, `download_waveforms.py`, `check_waveforms.py`, `check_waveforms_seiscomp.sh` |

The starting locations in `inputs/rtdd_catalog/event.csv` are the NCSS **routine** locations. The DD
catalogs are kept apart as references (`reference_tables/dd_catalog.csv` = NCEDC DD,
`reference_tables/ldeo_dd_catalog.csv` = LDEO NCAeqDD.v202112.1).
