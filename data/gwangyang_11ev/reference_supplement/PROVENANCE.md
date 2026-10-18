# Provenance of data/gwangyang_11ev/reference_supplement (read-only copies)

Copied 2026-10-17 11:58 KST from server B (<server-B>) with `rsync -a` (read-only on server B; nothing
there was changed). These files are not in `../reference/` but are needed to document how the
reference run was made (`docs/reference_run_settings.md` quotes them by file:line).
`../reference/` itself is left untouched.

| local file | server B source | md5 |
|---|---|---|
| pipeline_code_extra/clusters/gwangyang.py | /home/msseo/works/10.Earthquake_cycle_project/pipeline/clusters/gwangyang.py (the Gwangyang cluster configuration used by the run) | 2917dbbcaeaf0ac5287104c8f521f213 |
| pipeline_code_extra/clusters/_base.py | .../pipeline/clusters/_base.py | 3c68a02ac593b2fb49679a2aa5ee7584 |
| pipeline_code_extra/cli/run_pipeline.py | .../pipeline/cli/run_pipeline.py (command line used for the run; `--picker phasenet_plus`) | b6ad7d727476fcb185fc54ebd7a49009 |
| pipeline_code_extra/cli/bootstrap.py | .../pipeline/cli/bootstrap.py (bootstrap error command) | ba2b543f7f1e9307f7c03f25da671e29 |
| kma_catalog/event_catalog.csv | /home/msseo/works/10.Earthquake_cycle_project/Gwangyang_sequence/event_catalog/event_catalog.csv (KMA catalog, times in KST, UTF-8 with BOM, CRLF line ends) | 04581d47c5e74c7a0c280f912ff2f35b |

The `config.py`, `README.md` and `core/*.py` copies in `../reference/pipeline_code/` were checked
against server B on the same day: all md5 sums are identical, so they are the code that made the run.

## Added 2026-10-17 13:47 KST by install/06_gwangyang_prep.sh (step Prep, stage master)

Copied from server B with `rsync -a` (read-only on server B; nothing there was changed). The local copy is made
read-only (mode 444).

| local file | server B source | md5 |
|---|---|---|
| inventory/KS_KG_metadata_1.0.2.xml | /home/msseo/works/27.Haenam_sequence/data/stations/responses/master/KS_KG_metadata_1.0.2.xml (the user's canonical KMA master StationXML, networks KS and KG; 147853379 bytes, modified on server B 2026-06-14 18:02:18 KST) | 687bf07ddca65c76e0855de6d3c2673d |

- The path that `../reference/inventory/merged_inventory.xml` cites as its "master XML" source,
  /home/msseo/works/73.Gwangyang_sequence/data/stations/responses/master/KS_KG_metadata_1.0.2.xml, is a symbolic link to the file above on server B
  (md5 687bf07ddca65c76e0855de6d3c2673d, checked by ssh on the same day).
- Used for: the metadata of the 21 SAC channels (7 stations: CGWB, CHRB, YALB, YKDB, YNDB HH; HADA HG;
  KWJU HH) that merged_inventory.xml lacks, when building `../inputs/stations_rtdd.xml`.

## Added 2026-10-17 (KST) for notebook 05_gwangyang_sp_offset (the S-P offset study)

Purpose: establish the exact time reference of the user's hand-pick tables (`manual_vs_phasenet/*.csv`, made on server B
2026-04-22 by `Gwangyang_sequence/10.Compare_manual_ML_picks.ipynb`). Copied from server B (<server-B>) with `rsync -a`,
read only; nothing on server B was changed. All 31 copies were compared with `md5sum` on server B: all identical.
Local folder: `manual_picks_provenance/`. Server B root: `/home/msseo/works/10.Earthquake_cycle_project/Gwangyang_sequence/`.

| local file | server B source | md5 |
|---|---|---|
| notebooks/10.Compare_manual_ML_picks.ipynb | 10.Compare_manual_ML_picks.ipynb (reads `a`/`t0` of `manual_picks/<ev>/*Z.sac` -> Manual_*, of `waveforms_100km/<ev>/*Z.sac` -> PhaseNet_*) | e63269cde67945c5ccab1036a4b56a49 |
| notebooks/9.Input_P_and_S_picks_to_three_components.ipynb | same name (copies a hand pick to all 3 components of a station) | bd6087f917f5e166ccec8dd272ed63b9 |
| notebooks/5.Modify_origin_time_to_HypoInv_time.ipynb | same name (sets the SAC reference time to the earlier HYPOINVERSE origin) | 6b9ee6095ec09772dd55906052e62aa5 |
| notebooks/02.ML_picking_for_all_events.ipynb | same name (SeisBench PhaseNet picking, 2026-04-22) | see md5 list below |
| ml_picks_20260422/<event>_picks.csv (11 files) | picks/<event>_picks.csv (absolute times of the tables' PhaseNet column, SeisBench PhaseNet, NOT PhaseNet+) | see md5 list below |
| sac_spotcheck/manual_picks/<event>/<event>.KS.GWYB.HHZ.sac (11 files) + 20210827220322 GWYB HHN/HHE, BAU ELZ, KWJ2 HHZ | manual_picks/<event>/... (the hand-pick SAC files) | see md5 list below |
| sac_spotcheck/waveforms_100km_serverB/20210827220322/20210827220322.KS.GWYB.HHZ.sac | waveforms_100km/20210827220322/... (server B copy, source of the tables' PhaseNet column) | b85c595ba1b521cd0475e81bb2a2d2d6 |

Findings (details and checks in notebook 05, section 1.1):
- The tables' values are SAC header `a` (P) / `t0` (S) in seconds after the files' own reference time (`nz*`). On server B the
  `manual_picks` files and the `waveforms_100km` files share one reference time per event: the origin of an EARLIER
  HYPOINVERSE run (`5.Modify_origin_time_to_HypoInv_time.ipynb`), e.g. 2021-08-27T22:03:23.170 for event 20210827220322.
  Four events carry a 1 ms float-truncation of that origin (16:14:18.839, 02:49:47.509, 08:47:59.929, 02:15:35.729
  instead of .84/.51/.93/.73); the headers are self-consistent, so absolute time = header reference + table value.
- Header picks = table values exactly (16/16 files). Reference from the absolute April picks (11 events, 1021 picks)
  agrees with the headers within 3.1 microseconds.
- The local copy `reference/gwangyang_pnplus/waveforms_100km/` has the same samples but was re-referenced on 2026-05-28 to
  the pnplus HYPOINVERSE origin, 20-181 ms later; it must NOT be used to convert the tables.
- The tables' "PhaseNet" columns are the 2026-04-22 SeisBench PhaseNet picks, not the PhaseNet+ reference picks.

Derived file (written by notebook 05, cell 1.1): `../reference_tables/picks_manual_utc.csv` = 697 hand picks (338 P,
359 S) in absolute UTC, with the reference time, the table value and the source table of every pick.

md5 of all copied files (local = server B):
```
3cdf1669aaf3b843103ec7a3327d6322  manual_picks_provenance/ml_picks_20260422/20210720161418_picks.csv
321d6c66323d4bc1643b3ce377f29715  manual_picks_provenance/ml_picks_20260422/20210827002315_picks.csv
3beb85f968a0841e367867632c83fe9c  manual_picks_provenance/ml_picks_20260422/20210827220322_picks.csv
374a89d12dbd0cac1b1d320ec0524901  manual_picks_provenance/ml_picks_20260422/20210828133410_picks.csv
55b9086804f5675cd8aae07040509792  manual_picks_provenance/ml_picks_20260422/20210828133922_picks.csv
22164b967ec7b100ead56028138737dc  manual_picks_provenance/ml_picks_20260422/20210828234556_picks.csv
c5c54dc3c14448de35c26f1111710022  manual_picks_provenance/ml_picks_20260422/20260101024947_picks.csv
f84026ae9aca696a6ffa848f52407cda  manual_picks_provenance/ml_picks_20260422/20260101084800_picks.csv
533a523ac923aec9f49615ac235b8153  manual_picks_provenance/ml_picks_20260422/20260202194119_picks.csv
41dc0291e2d433c11931b5088e58fe6d  manual_picks_provenance/ml_picks_20260422/20260203021535_picks.csv
7da1cdfb94b19d0ad8a0aec36dc6e187  manual_picks_provenance/ml_picks_20260422/20260204054406_picks.csv
116068c37d451ceddd40d1d5a708cbd2  manual_picks_provenance/notebooks/02.ML_picking_for_all_events.ipynb
e63269cde67945c5ccab1036a4b56a49  manual_picks_provenance/notebooks/10.Compare_manual_ML_picks.ipynb
6b9ee6095ec09772dd55906052e62aa5  manual_picks_provenance/notebooks/5.Modify_origin_time_to_HypoInv_time.ipynb
bd6087f917f5e166ccec8dd272ed63b9  manual_picks_provenance/notebooks/9.Input_P_and_S_picks_to_three_components.ipynb
4d50ad708233edd4903522c1a459680a  manual_picks_provenance/sac_spotcheck/manual_picks/20210720161418/20210720161418.KS.GWYB.HHZ.sac
26dc6fde3d2673ea257f92e5a8397532  manual_picks_provenance/sac_spotcheck/manual_picks/20210827002315/20210827002315.KS.GWYB.HHZ.sac
66f581e4c46e034cf2db9277f15c54ae  manual_picks_provenance/sac_spotcheck/manual_picks/20210827220322/20210827220322.KS.BAU.ELZ.sac
5da5ccbfb7d27f42e6f03b49aa095b44  manual_picks_provenance/sac_spotcheck/manual_picks/20210827220322/20210827220322.KS.GWYB.HHE.sac
96640b747999cb66751ee8a03829fdcc  manual_picks_provenance/sac_spotcheck/manual_picks/20210827220322/20210827220322.KS.GWYB.HHN.sac
b1c603965e5301e39c1a558168a617bb  manual_picks_provenance/sac_spotcheck/manual_picks/20210827220322/20210827220322.KS.GWYB.HHZ.sac
ca8c68a8a5a4639e79910c267899870e  manual_picks_provenance/sac_spotcheck/manual_picks/20210827220322/20210827220322.KS.KWJ2.HHZ.sac
62cc79fd1af9a33d66b2c4e4f07e1ce5  manual_picks_provenance/sac_spotcheck/manual_picks/20210828133410/20210828133410.KS.GWYB.HHZ.sac
9f135e25d10542928ae3ca8b9c85d5b0  manual_picks_provenance/sac_spotcheck/manual_picks/20210828133922/20210828133922.KS.GWYB.HHZ.sac
fb57108b569610af8c1189f87572357f  manual_picks_provenance/sac_spotcheck/manual_picks/20210828234556/20210828234556.KS.GWYB.HHZ.sac
5979b12f7781d9f86754a2d476e796d0  manual_picks_provenance/sac_spotcheck/manual_picks/20260101024947/20260101024947.KS.GWYB.HHZ.sac
75f654e4f5e68d46cad73291816a296c  manual_picks_provenance/sac_spotcheck/manual_picks/20260101084800/20260101084800.KS.GWYB.HHZ.sac
c9969f3486a4c69b6750ca114392fe16  manual_picks_provenance/sac_spotcheck/manual_picks/20260202194119/20260202194119.KS.GWYB.HHZ.sac
9ee49419eed4b900f3f847a0355b2e55  manual_picks_provenance/sac_spotcheck/manual_picks/20260203021535/20260203021535.KS.GWYB.HHZ.sac
41ec0ad7c6923b81372408641c8041d9  manual_picks_provenance/sac_spotcheck/manual_picks/20260204054406/20260204054406.KS.GWYB.HHZ.sac
b85c595ba1b521cd0475e81bb2a2d2d6  manual_picks_provenance/sac_spotcheck/waveforms_100km_serverB/20210827220322/20210827220322.KS.GWYB.HHZ.sac
```
