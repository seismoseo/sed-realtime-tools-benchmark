# Step 10: real-time chain test on Server A with two Gwangyang events (2026-10-17)

A SeisComP 7.4.0 real-time chain ran on Server A, with all messaging on the loopback interface:
scautopick with the DL picker → scmaster → scautoloc → scevent → scrtdd → SQLite database.

Two Gwangyang earthquakes were replayed through it:
- 20210827220322, ML 2.2, called event 3 here (its rtdd id);
- 20260202194119, ML 1.6, called event 9.

## Main results

- **The chain works end to end, after one scautoloc setting.**
  - In the first run (RT1) scautoloc threw away every DL pick. Its "dynamic pick threshold" compares each pick
    with itself and needs an SNR of at least 3, while the DL picker reports a confidence of at most 1.
  - With that check switched off (`autoloc.dynamicPickThresholdInterval = 0`), each replayed earthquake gave:
    - DL picks (methodID DL3C / SDL3C) in the database;
    - 3-4 scautoloc origins;
    - one scevent event (2021qzhi, 2026ciqc);
    - one or more scrtdd origins (author scrtdd@server-a, methodID RTDD).
  - All of this was read back from the database with scevtls, scxmldump and SQL.
- **The real-time picks are the offline picks.** scautopick in messaging mode produced step 09's offline picks,
  identical for every replayed event (RT1: event 3 only; RT2-RT5: both events): 112 and 85 picks, all with the
  same times (`<run>/results/picks_vs_offline.csv`).
- **scautoloc's starting locations are poor in depth; scrtdd repairs this.**
  - LOCSAT with iasp91 put the events 0.35-0.51 km away horizontally, 2.7-3.9 km too shallow and 0.7-0.8 s too
    early.
  - scrtdd moved them 2.8 and 3.9 km. The final RTDD origins lie **61 m (event 3) and 5.2 m (event 9)** from
    their S1 multi-event positions; S1 is the solution the reference catalog comes from. This is not a fully
    independent test, because S1 was computed with events 3 and 9 included (section 6).
  - The same holds against pyrtdd R1f (61 / 5 m), and against R1 and HypoDD dt.cc once each solution's own
    frame shift is removed (R1: 61 / 4 m; HypoDD: 55 / 9 m).
- **The real-time relocation is exactly the offline relocation of the same origin.** `scrtdd --ep` on the
  scautoloc origin taken from the database gives the same coordinates and time to every printed digit.
- **Most of the remaining difference comes from the S picks the chain loses.**
  - scautoloc never associates S picks, so scrtdd relocates with P only.
  - Adding the DL S picks offline gives 41 m and 1.2 m from S1. For event 3 this is 5 m from step 08's
    offline single-event result. Event 3 (ML 2.2) is the cluster's least consistent event in every step.
- **Real-time latency (paced replays).** Counted from the final scautoloc (LOCSAT) origin time, as first
  reported; in brackets, counted from S1's origin time on msrtsimul's own clock (section 4.5):
  - first DL P pick after 13-15 s (12-14 s). For event 9 the earliest pick in the window (13.3 s) is a noise pick
    at HCNA timed 20.1 s before the origin; the first pick of the earthquake itself was created after 15.3 s, and
    the first pick an origin used after 19.3 s (found by notebook 04's cross-checks, 2026-10-17);
  - first scautoloc origin and event after 38-41 s (37-40 s);
  - first relocated origin after 60-63 s (59-62 s) in RT3.
  - The LOCSAT origin times are 0.83 s (event 3) and 0.69 s (event 9) earlier than S1's, and the two clocks
    differ by 0.5 s (section 4.5). So the first numbers are about 1.2-1.3 s longer than the bracketed ones, not
    shorter.
  - The parts: the DL P pick needs ~17 s (step 09's "reliable" window), scautoloc waits ~14 s more for each
    pick's mb amplitude, and scrtdd waits 10 s (delayTime) and computes for 1-5 s.
  - RT5, with scautoloc's clock following creation times:
    - event 9: first relocated origin after 59 s (58 s), final one after 73 s (72 s);
    - event 3: the first relocation attempt, at about 60 s (59 s), failed (next bullet). Its first relocated
      origin came only after 233 s (231 s), when scautoloc finally released its last update.
- **A relocation can fail, deterministically.**
  - In RT5 scrtdd could not relocate event 3's 44-phase scautoloc origin (`Cannot relocate origin`). It sent
    nothing and recovered with the next update.
  - The cause is in libhdd: its residual down-weighting measures residuals from zero. The ~1-s origin-time
    error of the LOCSAT start, with a small spread, gave 222 of 234 double differences zero weight, and the
    first step left the travel-time grid.
  - The same origin fails identically offline. Switching the down-weighting off lets it finish, but 1.2 km from
    S1, so that is no fix.
  - Two of the twelve real-time relocation attempts started with more than 80 % of their double differences
    cut off; one of them failed.
- **No relocation loops.** scrtdd ignored its own origin each time scevent made it preferred: once by chance in
  RT3, and for both events in RT4, where scevent was set to prefer scrtdd's origins.
- **Network rule kept.**
  - The only listening socket was scmaster's 127.0.0.1:28180. SeedLink was not used, because it cannot be
    bound to localhost.
  - Every module was stopped by PID; `ss`, `pgrep -x` and `/proc` show nothing left (`<run>/network/`).

## 1. What ran, and how the data flowed

```
 inputs/playback/<kma_id>.mseed --scmssort -u -E--> <run>/data/<kma_id>_sorted.mseed
                                                         |
          feed "file":  scautopick -I file://<sorted.mseed> --playback      (whole file at full speed)
          feed "paced": msrtsimul -c -m historic -s 1 <sorted.mseed> | scautopick -I file://- --playback
                                                         |      (records released at their original pace)
                                                         v
   scautopick (plugin dlrtpicker: DL3C P / SDL3C S, model phasenet_original; bindings from the database)
        | PICK + AMPLITUDE messages (snr = model confidence, mb, MLv, mB)
        v
   scmaster  127.0.0.1:28180 (queue "production", dbstore -> <run>/db/seiscomp.sqlite, SQLite in WAL mode)
        |                          ^ every message is stored in the database by scmaster's dbstore
        v                          |
   scautoloc --playback (LOCSAT iasp91, local grid; only P picks with an mb amplitude can be used)
        | LOCATION (origins, author scautoloc@server-a, methodID LOCSAT)
        v
   scevent (creates the event, chooses the preferred origin)
        | EVENT (event updates: preferred origin)
        v
   scrtdd (profile gwangyang = run S1's settings; reference catalog = S1 without the replayed events;
           onlyPreferredOrigins, delayTime 10 s, acceptedOriginAuthors = scautoloc@server-a;
           waveforms of the catalog AND of the new event from sdsarchive://inputs/sds)
        | RELOCATION (origin, author scrtdd@server-a, methodID RTDD)
        v
   scevent (associates the relocated origin with the event; may or may not make it preferred)
```

No SeedLink server was started: SeisComP's seedlink always binds its listening socket to all interfaces
(`iosystem.cc:2788`, `inet_addr.sin_addr.s_addr = htonl(INADDR_ANY)`, no option), so it cannot be kept on
localhost (network rule). scautopick ran in its normal messaging mode instead (no `--offline`, no `--ep`) and read
the time-sorted miniSEED file as its record stream.

## 2. Runs

Each run is a fresh database with its own scmaster session. Two events are replayed one after the other into
the same running system: first 20210827220322 (ML 2.2, rtdd id 3), then 20260202194119 (ML 1.6, rtdd id 9).

| run | data feed | what differs | purpose |
|---|---|---|---|
| RT1_filefeed | file, full speed | scautoloc's dynamic pick threshold at its default (3600 s) | first attempt: **failed at scautoloc** (no origin; section 5) - kept as evidence |
| RT2_filefeed | file, full speed | `autoloc.dynamicPickThresholdInterval = 0` | **main run** |
| RT3_paced | msrtsimul, real-time pace | as RT2 | real-time latencies |
| RT4_filefeed_prefer_rtdd | file, full speed | as RT2, plus scevent prefers scrtdd's origins | tests the relocation-loop protection on purpose |
| RT5_paced_creationtime | msrtsimul, real-time pace | as RT3, plus scautoloc `--timing creationTime` | real-time latencies, with scautoloc's clock following the creation times of incoming picks and amplitudes |

## 3. Settings, and why they are what they are

Every run has its own folder `runs/gwangyang/realtime/<run>/`. Its `seiscomp_user/` folder is the
`SEISCOMP_LOCAL_CONFIG` of every program of the run, and its `home/` is their `HOME`. The user's `~/.seiscomp`
was never created; this was checked before and after every stage. Every option value is written to
`<run>/options/`:

- `<module>.config.json`: every key set anywhere in the configuration files, with file and line, plus the
  documented default of every key left unset;
- `run_options.json`: scrtdd's values as resolved by step 08's own resolver, the differences to S1, scautoloc's
  logged start-up configuration, the command line of every process, and the script versions (section 7);
- `scautopick.settings.json`: the same format as step 09's settings files.

| module | setting | value | why |
|---|---|---|---|
| scmaster | `interface.bind` | 127.0.0.1:28180 | loopback only, non-default port (default 0.0.0.0:18180); port checked free with `ss -ltnp` |
| scmaster | `interface.ssl.bind` | 127.0.0.1:-1 | SSL listener off |
| scmaster | `interface.acl`, `queues.production.acl` | 127.0.0.1 | local clients only |
| scmaster | `queues` | production | the second default queue (playback) is not needed |
| scmaster | groups | default + RELOCATION | scrtdd's output group (loop protection, singleevent.rst) |
| scmaster | dbstore | sqlite3, `<run>/db/seiscomp.sqlite` | the database of the run |
| database | schema, journal | share/db/sqlite3.sql; WAL | WAL so that readers (scevent, scrtdd) never wait for scmaster's writes: the SeisComP SQLite driver sets no busy timeout |
| database | content before the test | inventory_sc.xml (54 stations, 255 streams), bindings_config.xml (54 stations) | imported with `scdb -i` |
| scautopick | whole module configuration | step 09's `scautopick_phasenet_original.cfg`, unchanged | best model of step 09 (rule fixed before results); its `--dump-config` here equals step 09's for the module values and all 54 streams |
| scautopick | command line | `-H 127.0.0.1:28180/production --playback -I file://...` | normal messaging mode; `--playback` because otherwise scautopick asks for data from "now - 60 s" only (picker.cpp:416-423) |
| scautoloc | `--playback` | on | without it every pick older than 6 h is dropped (autoloc.cpp `_store`: "ignoring old pick") |
| scautoloc | `--timing` | pickTime (RT1-RT3: not on the command line, the default, scautoloc/app.h:82; RT4: `--timing pickTime`), creationTime (RT5: `--timing creationTime`) | which clock scautoloc follows in playback mode (see RT3); from `<run>/pids.json` |
| scautoloc | `autoloc.grid` | 245 points: 34.7-35.3 N, 127.43-128.03 E every 0.1 deg; depths 5, 10, 15, 20, 25 km; radius 0.1 deg; 1.0 deg; 8 picks | local nucleation grid |
| scautoloc | `autoloc.stationConfig` | the 54 KS stations, usage 1, nucleation <= 1.0 deg; `* * 0 0` | station list |
| scautoloc | `autoloc.minPhaseCount` | 8 (default 6) | ~40-50 stations per event |
| scautoloc | `autoloc.maxStationDistance` | 1.5 deg (default 180) | local network |
| scautoloc | `autoloc.maxRMS` / `autoloc.maxResidual` | 1.0 s / 1.5 s (default 3.5 s / 7 s) | local network; the smallest S-P time is ~1.9 s, so an S wave picked as P cannot pass as P |
| scautoloc | `autoloc.minPickSNR` | 0 (default 3) | the DL picker stores its 0-1 confidence as the pick's "snr" amplitude |
| scautoloc | `autoloc.dynamicPickThresholdInterval` | 0 (default 3600 s) | RT2 onwards; RT1 showed it rejects every DL pick (section 5) |
| scautoloc | locator | LOCSAT iasp91, default depth 10 km (defaults) | "LOCSAT is fine": scrtdd relocates afterwards |
| scevent | `connection.subscriptions` | default + RELOCATION | to receive scrtdd's origins |
| scevent | `eventAssociation.minimumDefiningPhases` | 8 (default 10) | same as scautoloc's minPhaseCount |
| scevent | `eventAssociation.priorities` / `authors` | RT4 only: AUTHOR first; scrtdd@server-a, scautoloc@server-a | makes scrtdd's origin preferred, to test the loop protection on purpose |
| scrtdd | profile `gwangyang` | step 08's template = run S1's settings | resolved values identical to S1's `run_options.json` except the catalog files |
| scrtdd | reference catalog | S1 positions of the 9 other events + their 590 picks; ids = rtdd_id + 100 | the replayed events are not in it; ids from 101 avoid scrtdd's step-1 id clash with id 1 (step 08) |
| scrtdd | `acceptedOriginAuthors` | scautoloc@server-a | loop protection 1 |
| scrtdd | `connection.primaryGroup` | RELOCATION | loop protection 2 |
| scrtdd | `onlyPreferredOrigins`, `delayTime`, `profileTimeAlive` | true, 10 s, -1 | template values |
| scrtdd | `plugins`, `ttt.NLLGrid.*` | tttnll, kim1983 grids, 0.1 m | in scrtdd.cfg instead of global.cfg, since only scrtdd needs them |
| scrtdd | `recordstream` (global.cfg) | sdsarchive://inputs/sds | waveforms of the catalog and of the new event |
| scrtdd | command line | `--dump-diagnostics` | writes the double-difference tables of each relocation |
| all | process priority | `nice -n 10` | Server A is shared |

## 4. Results

Numbers come from the databases: `<run>/db_dump/` holds `scevtls`, `scxmldump` and SQL read-outs, and
`<run>/results/` holds the tables made by `rt_analyze.py`. Positions are local east/north/up in meters about
35.0000 N 127.7286 E, as in steps 07-09. A positive dU means the solution is shallower than the one it is
compared with.

### 4.1 Picks: the real-time picks are the offline picks

| event | DL3C (P) picks | SDL3C (S) picks | step 09 offline picks, same model and file | matched within 0.5 s | time difference | amplitudes (snr / mb / MLv / mB) |
|---|---|---|---|---|---|---|
| 3 (ML 2.2) | 56 | 56 | 112 | 112 | 0 for all | 56 / 56 / 56 / 51 |
| 9 (ML 1.6) | 43 | 42 | 85 | 85 | 0 for all | 43 / 43 / 42 / 27 |

The pick sets are identical for every replayed event (RT1: event 3 only; RT2-RT5: both events): 112 and 85
picks, each with the same station, method and exact time as step 09's (`<run>/results/picks_vs_offline.csv`:
`n_identical_times` = `n_rt_picks` = `n_offline_step09` in every run, RT1 for event 3). So the paced feeds (RT3,
RT5) change no pick either. The independent verification also matched the channels
(`runs/verify_gwangyang_realtime/verify_picks_vs_step09.csv`). Four S picks were emitted twice, with the same time
and different publicIDs created 1 ms apart: HAMB, IMSB and YALB for event 3, and GKSA for event 9. Step 09's
offline output has the same duplicates (112 picks, 109 distinct). scautoloc ignores S picks, so they have no
effect here.

scautopick in messaging mode, reading its configuration and bindings from the database, produces the picks of
step 09's offline `--ep` run, identical for every replayed event. Its resolved settings (module values, plugin
settings, all 54 streams) are identical to step 09's (`RT2_filefeed/options/scautopick.settings.json`).

### 4.2 scautoloc origins and scevent events (RT2)

| event | scautoloc versions (number of P arrivals) | final scautoloc origin | depth | rms | gap | vs S1: horizontal / vertical / origin time |
|---|---|---|---|---|---|---|
| 3 | 4 (8, 28, 48, 55) | 35.00212 N 127.72800 E | 11.38 km | 0.153 s | 35 deg | 349 m / 2709 m too shallow / -0.83 s |
| 9 | 3 (10, 30, 37) | 35.00209 N 127.73007 E | 10.26 km | 0.160 s | 35 deg | 510 m / 3881 m too shallow / -0.69 s |

- scevent made one event per earthquake: 2021qzhi and 2026ciqc.
- No origin carries an S arrival (section 5, item 3). Of the 56 and 43 P picks made in the replayed files, the
  final origins use 55 and 37.
- The first versions were deeper (23.5 km and 18.6 km, from 8 and 10 picks). With more picks, LOCSAT with
  iasp91 settles 2.7-3.9 km too shallow and 0.83/0.69 s too early. This is what a generic global model gives
  for this crust.

### 4.3 scrtdd's real-time relocations

scrtdd waited for the event's preferred origin to stop changing for 10 s (delayTime). It then relocated that
origin in two steps against the 9-event catalog (9 neighbors in both steps) and sent the result to RELOCATION.

| event | P cross-correlations tried | with CC >= 0.7 | of these anti-correlated (CC <= -0.7) | S | final double-difference residual, median (weighted) | waveforms not available |
|---|---|---|---|---|---|---|
| 3 | 271 | 166 | 37 | 0 | 11.5 ms | 0 of 55 new + 271 catalog |
| 9 | 219 | 169 | 2 | 0 | 1.6 ms | 0 of 37 new + 2 catalog (the rest was still in memory) |

Final positions (RT2), and their differences from other solutions. "Abs." compares positions directly. "Rel."
compares each position after subtracting the centroid of the 9 reference events in the same solution (section 6).

| event | compared with | dE | dN | dU | horizontal | 3-D | origin time |
|---|---|---|---|---|---|---|---|
| 3 | scautoloc origin it started from | -314 | -239 | -2747 | 395 | 2775 | +827 ms |
| 3 | **S1** (scrtdd multi-event; same frame as the catalog) | -45.0 | -16.0 | -38.0 | 47.7 | **61.1** | -0.8 ms |
| 3 | pyrtdd R1f (filtered) abs. / rel. | -45.0 / -44.8 | -17.4 / -15.9 | -37.1 / -37.9 | 48.2 / 47.5 | 60.8 / 60.8 | -0.7 ms |
| 3 | pyrtdd R1 (stock) abs. / rel. | -141.5 / -38.1 | 53.8 / -9.4 | 433.7 / -46.2 | 151 / 39.2 | 459 / 60.6 | +1.8 ms |
| 3 | HypoDD 02.dt.cc abs. / rel. | -361 / -43.9 | 16.6 / -16.9 | -200 / -27.7 | 361 / 47.0 | 413 / 54.6 | -12.6 ms |
| 3 | SEa / SEm (step 08 offline single-event, PhaseNet+ P+S) | -20.2 / -30.3 | -21.2 / -18.2 | -2.0 / -14.8 | 29.3 / 35.3 | 29.3 / 38.3 | +3.2 / +1.7 ms |
| 9 | scautoloc origin it started from | -458 | -227 | -3886 | 511 | 3920 | +690 ms |
| 9 | **S1** | -1.5 | -1.0 | -4.9 | 1.8 | **5.2** | -0.9 ms |
| 9 | pyrtdd R1f abs. / rel. | -1.6 / -1.4 | -2.5 / -1.0 | -4.1 / -4.9 | 2.9 / 1.7 | 5.1 / 5.2 | -1.0 ms |
| 9 | pyrtdd R1 abs. / rel. | -101.1 / 2.3 | 61.7 / -1.5 | 483.1 / 3.1 | 118.5 / 2.7 | 497 / 4.2 | -4.5 ms |
| 9 | HypoDD 02.dt.cc abs. / rel. | -318.6 / -1.5 | 38.7 / 5.2 | -179.2 / -6.9 | 320.9 / 5.4 | 368 / 8.8 | -18.1 ms |
| 9 | SEa / SEm | -0.5 / -1.5 | -1.1 / -0.9 | -6.0 / -5.0 | 1.2 / 1.8 | 6.2 / 5.3 | -1.6 / -1.0 ms |

For scale: S1 itself lies 10.4 m (event 3) and 6.5 m (event 9) from HypoDD dt.cc ("rel."). The offline
single-event runs of step 08 lie 44.0 m (SEa) and 27.6 m (SEm) from S1 for event 3, and 1.5 m and 0.1 m for
event 9. HypoDD's bootstrap 95 % half-widths (E/N/U) are 16/6/26 m for event 3 and 3.2/3.9/6.5 m for event 9.

### 4.4 Offline cross-check: same origin, `scrtdd --ep`, P only and P+S

`rt_offline_check.py` took the scautoloc origin that scrtdd relocated in RT2 from RT2's database (a copy, md5
unchanged afterwards) and relocated it offline with the same profile and catalog.

- In `--ep` mode scrtdd switches messaging off (rtddtool.cpp:367-377).
- These runs happened while RT3 was live on the same port. RT3's scmaster log shows no client connection
  between 18:01:53 and 18:02:30 KST, when they ran, so nothing reached the live system.
- The "Disable messaging" line itself is printed before scrtdd opens its log file, so the
  `messaging_disabled_logged` column is False and proves nothing.

| event | variant | arrivals | vs real-time RTDD origin | vs S1 (3-D) | vs SEa (3-D) |
|---|---|---|---|---|---|
| 3 | P (as in real time) | 55 P | **0.00 m, 0.000 ms** | 61.1 m | 29.3 m |
| 3 | P+S (DL S picks added) | 55 P + 55 S (52 S kept: scrtdd dropped the 3 duplicated S picks) | 34.3 m | **40.9 m** | 5.4 m |
| 9 | P | 37 P | **0.00 m, 0.000 ms** | 5.2 m | 6.2 m |
| 9 | P+S | 37 P + 38 S (37 S kept: 1 duplicate dropped) | 4.3 m | **1.2 m** | 2.2 m |

- **The real-time relocation is exactly the offline relocation of the same origin.** Messaging, the database
  and the 10-s scheduling change nothing.
- **Most of the difference from the offline single-event results comes from the missing S picks.**
  - With the DL S picks added, event 9 moves to 1.2 m from S1, and event 3 to 5.4 m from SEa (which used
    PhaseNet+ P and S picks).
  - The remaining ~40 m of event 3 from S1 is the single-event behavior already seen in step 08 (SEa 44 m,
    SEm 28 m).
- In the chain as built, the S picks are made by scautopick and stored in the database, but they never reach
  scrtdd, because scautoloc does not associate S.

### 4.5 Processing delays from the creation times

**File feed (RT2; RT4 within 1-2 s).** The whole 9-minute file goes through scautopick in 11-16 s (wall time,
1 s of CPU), so these numbers are processing times, not real-time latencies (wall clock, UTC):

| event | first DL pick created | first scautoloc origin | event created | final scautoloc origin | RTDD origin | RTDD after the final origin |
|---|---|---|---|---|---|---|
| 3 | 08:49:15.23 | +6.2 s | +6.9 s | +16.4 s | +33.2 s | 16.8 s (10 s delayTime + 1.3 s wake-up + 5 s relocation) |
| 9 | 08:50:46.38 | +4.7 s | +5.6 s | +11.3 s | +24.2 s | 12.9 s (10 s + 1.3 s + 1 s) |

The first relocation took about 5 s, because scrtdd read the 271 catalog waveforms from the SDS archive. The
second took 1 s with the waveforms already in memory (`profileTimeAlive = -1`).

**Paced feed (real-time pace).** Two sets of latencies, both in `<run>/results/delays.csv`:

- First set, as first reported (`latency_*_after_origin_time_s`): counted from the **final scautoloc (LOCSAT)
  origin time**. Data time is mapped to wall time with the median of (wall time − record end time) over the
  records msrtsimul released, with a 5-95 % spread of 0.9 s.
- Second set (`latency_*_after_S1_origin_time_msrtsimul_clock_s`): counted from **S1's origin time**, on
  **msrtsimul's own clock**. msrtsimul starts its clock at the end time of the first record, cut to whole seconds,
  when it prints "Starting msrtsimul at"; data time T is then reached at wall time T + (start − that time).
- The LOCSAT origin times are 0.83 s (event 3) and 0.69 s (event 9) earlier than S1's
  (`final_scautoloc_origin_time_minus_S1_s`).
- msrtsimul hands each record over when its clock reaches the record's end time rounded down to a whole second,
  so 0-1 s early. The median offset of the first set therefore lies 0.50 s below msrtsimul's clock
  (`msrtsimul_clock_offset_minus_median_offset_s`).
- Together, the first set is 1.33 s (event 3) and 1.19 s (event 9) longer than the second, not shorter. The
  second set agrees with the independent check (`runs/verify_gwangyang_realtime/verify_latency.csv`) to 0.01 s.

First set, from the final scautoloc origin time:

| | RT3 event 3 | RT3 event 9 | RT5 event 3 | RT5 event 9 |
|---|---|---|---|---|
| first DL pick created (earliest pick in the window) | 15.1 s | 13.3 s* | 15.1 s | 13.3 s* |
| P picks, creation minus pick time (median / 90 %) | 17.0 / 18.4 s | 18.1 / 20.5 s | 17.0 / 18.4 s | 18.1 / 20.5 s |
| S picks, creation minus pick time (median / 90 %) | 24.4 / 28.5 s | 26.1 / 30.9 s | 24.4 / 28.5 s | 26.1 / 30.9 s |
| first scautoloc origin / event | 38.3 / 38.6 s | 40.4 / 40.7 s | 38.4 / 38.7 s | 40.5 / 40.8 s |
| first RTDD origin | **62.8 s** (from the 48-phase origin) | **60.5 s** (from the 30-phase origin) | **232.6 s** (from the 55-phase origin); the attempt on the 44-phase version before it failed | **58.8 s** (from the 23-phase origin) |
| last scautoloc update | 216.8 s (55 phases) | 268.7 s (37 phases) | 216.3 s (55 phases) | 60.3 s (37 phases) |
| last RTDD origin | 229.2 s | 280.6 s | 232.6 s | 73.1 s |
| 3-D distance of first / last RTDD origin from S1 | 70.4 / 61.1 m | 10.8 / 5.2 m | 61.1 m (one RTDD origin) | 9.1 / 5.2 m |

\* Event 9: this earliest pick is a noise pick at HCNA, timed 20.1 s before the origin. The first pick of the
earthquake itself was created after 15.3 s, the first pick used by an origin after 19.3 s.

Second set, the same times from S1's origin time on msrtsimul's clock (the pick rows map the pick time with
msrtsimul's clock too):

| | RT3 event 3 | RT3 event 9 | RT5 event 3 | RT5 event 9 |
|---|---|---|---|---|
| first DL pick created | 13.7 s | 12.1 s | 13.7 s | 12.1 s |
| P picks, creation minus pick time (median / 90 %) | 16.5 / 17.9 s | 17.6 / 20.0 s | 16.5 / 17.9 s | 17.6 / 20.0 s |
| S picks, creation minus pick time (median / 90 %) | 23.9 / 28.0 s | 25.6 / 30.4 s | 23.9 / 28.0 s | 25.6 / 30.4 s |
| first scautoloc origin / event | 37.0 / 37.3 s | 39.2 / 39.5 s | 37.1 / 37.4 s | 39.3 / 39.6 s |
| first RTDD origin | **61.5 s** | **59.3 s** | **231.3 s** | **57.6 s** |
| last scautoloc update | 215.4 s | 267.6 s | 215.0 s | 59.1 s |
| last RTDD origin | 227.9 s | 279.4 s | 231.3 s | 71.9 s |

The first-pick times and the median pick latencies of RT3 and RT5 agree to about 1 ms, although the runs were
independent (different start times and clock offsets): the paced feed and the picker are reproducible.

Where the time goes in the paced runs:

1. **The DL P pick needs 17-18 s** (16.5-17.6 s on msrtsimul's clock). Step 09's "reliable" setting needs a 30-s
   window centered on the trigger, so 15 s of data after the onset.
2. **scautoloc waits for each pick's mb amplitude**, before it can use the pick (autoloc.cpp: "Currently we
   require amplitudes to be present").
   - scautopick makes the mb amplitude a median 14.0 s after the pick; the mb window ends 20.5 s after its
     reference time.
   - So scautoloc can use a P pick about 31 s after the P onset. Adding the 3-7 s travel time to the nearest
     stations gives the first origin at 38-40 s (37-39 s from S1's origin time on msrtsimul's clock).
3. **scrtdd waits 10 s (delayTime) after the last change of the preferred origin** and then needs 1-5 s.
4. **In RT3, scautoloc published the last update 3-4 minutes late.**
   - After sending a version with N phases, scautoloc holds the next version back for 0.5 s × N, unless it has
     at least 20 more phases (`autoloc.publicationIntervalTimeSlope`, `publicationIntervalPickCount`;
     autoloc.cpp `_flush`).
   - In playback mode that interval is measured on scautoloc's own clock, which moves only when a new pick or
     snr/mb amplitude arrives. With `--timing pickTime` that clock is the latest pick TIME.
   - Example from RT3's log, after the 48-phase version of event 3: `next due: 2021-08-27 22:04:13.2`. The
     55-phase version was ready 4 s later but stayed queued until a pick later than 22:04:13 arrived. In the
     paced stream that happened 2.8 minutes later; in the file feed, the later picks of the file arrive within
     seconds.
   - RT5 uses `--timing creationTime`: the clock is then the creation time of the latest pick or amplitude,
     i.e. it follows the wall clock while objects arrive. This is still not quite live operation: without
     `--playback` the clock is `Time::UTC()` and pending updates are checked every 5 s
     (`autoloc.wakeupInterval`, app.h:104), but without `--playback` scautoloc ignores picks older than 6 h, so
     a historic replay cannot use that mode.
   - What RT5 showed: event 3's last update still came 2.8 minutes late. Event 9's came 14 s after the previous
     one, because picks and amplitudes kept arriving. `creationTime` helps only while objects keep coming in.

### 4.6 Relocation loops

- Loop protection 1: scrtdd relocates only origins whose author is `scautoloc@server-a` (`acceptedOriginAuthors`).
- Loop protection 2: scrtdd sends to its own group RELOCATION, which scevent also listens to.
- Protection 2 alone would not be enough. With `onlyPreferredOrigins` scrtdd reacts to every event update, and
  it has no other check on the origins it relocates (rtddtool.cpp:1566-1700). So if scevent made scrtdd's own
  origin preferred, only protection 1 stops scrtdd from relocating it again.

| run | scevent priorities | RTDD origin became preferred | what scrtdd did next | RTDD origins per relocated scautoloc origin |
|---|---|---|---|---|
| RT2 | default | no ("phaseCount too low": the RTDD origin uses 54 of 55 arrivals) | nothing (no event update) | 1 |
| RT3 | default | yes, once: the RTDD origin (48 arrivals) tied with the 48-arrival scautoloc origin and was newer | 10 s later: `Ingoring origin Origin/20261017085754.962006.483 whose author is not accepted` | 1 |
| RT4 | AUTHOR first (scrtdd@server-a, scautoloc@server-a) | yes, both events | `Ingoring origin ... whose author is not accepted`, 11 s after each | 1 |
| RT5 | default | event 3: no ("phaseCount too low"); event 9: yes, briefly (tie in phase count, newer) | event 9: a newer scautoloc version (37 phases) arrived 1.5 s later and became preferred, so scrtdd relocated that one 10 s later; it never met its own origin | 1 |

At the end of every run with the default priorities (RT2, RT3, RT5), both events had a LOCSAT origin as
their preferred origin. So anything that reads only preferred origins would not see the relocation. In RT4
both events ended with the RTDD origin preferred, and the loop protection held.

### 4.7 Network and processes

- Before each start, `ss -ltnp` showed nothing on port 28180 (`<run>/network/before_start.txt`), and no
  process of this user had a module name.
- After start and after each replay, the only listening socket of any process of the run was scmaster's
  `127.0.0.1:28180` (TCP; no UDP): `<run>/network/after_start.txt` and `after_replay_*.txt`.
- scmaster logged `Bound unencrypted to 127.0.0.1:28180`, and every client came from 127.0.0.1.
- `stop` sent SIGTERM to each recorded PID; every module ended within 0.2 s.
- Afterwards (`<run>/network/after_stop.json`): all recorded PIDs gone from `/proc`, `pgrep -x -u 1007`
  empty for scmaster, scevent, scautoloc, scrtdd, scautopick and seedlink, port 28180 free, `~/.seiscomp` absent.
  This holds for every run (RT1-RT5).
  - msrtsimul is a Python script; its process name is `python3.12`, so `pgrep -x msrtsimul` cannot see it. Its
    PID is recorded and checked like the others. It ends by itself at the end of the file, before `replay`
    returns.

### 4.8 Cost

| run | scautopick (CPU s, 2 files of ~9 min, 47-53 stations) | scrtdd (CPU s, whole run) | scautoloc | scevent | scmaster |
|---|---|---|---|---|---|
| RT2 | 1.02 + 0.83 | 5.66 | 0.76 | 0.03 | 0.60 |
| RT3 (paced) | 1.33 + 1.17 | 7.40 | 1.06 | 0.07 | 0.71 |
| RT4 | 1.05 + 0.78 | 5.23 | 0.78 | 0.03 | 0.60 |
| RT5 (paced) | 1.46 + 1.12 | 6.11 | 1.08 | 0.07 | 0.73 |

Peak memory was 26-37 MB for each module. Everything ran at `nice -n 10`.

## 5. Problems found, with the evidence

1. **scautoloc rejected every DL pick in the first run (RT1).**
   - What happened: 112 picks and 219 amplitudes reached the database, but scautoloc made no origin, so there
     was no event and no relocation.
   - Log: all 56 P picks were dropped by `_tooManyRecentPicks` (`RT1_filefeed/logs/scautoloc.log`).
     - 55 were dropped on its "XX" branch, e.g.
       `_tooManyRecentPicks: 20210827.220326.273096-KS.HADA..HGZ-A-P-DL3C-scautopick@server-a-Unset   XX pick SNR 0.75 < 3.00`.
     - 1 was dropped on its other branch: the pick SNR is lower than the weighted sum over the station's
       earlier picks.
   - Cause, from the source (scautoloc `autoloc.cpp`, `_tooManyRecentPicks`):
     - the new pick is already stored in the pick pool when it is tested, so it is compared with itself (dt = 0);
     - the old pick's SNR is raised to at least 3, which gives a threshold of 3 × (1 − 0/120) = 3;
     - the DL picker's "snr" is its confidence, at most 1, so the test can never pass.
   - Fix: `autoloc.dynamicPickThresholdInterval = 0`, which is the documented way to switch the check off
     (`if timeSpan <= 0 return false`). The check protects against bursts of noise picks at one station; it
     assumes STA/LTA ratios.
   - RT1 is kept unchanged as evidence (its database dump is in `RT1_filefeed/db_dump/`).
2. **scautoloc's default `minPickSNR` (3) would also reject every DL pick**, for the same reason: the "snr" is
   the 0-1 confidence (scdlrtpicker README, "What ends up on the pick"). This was seen in the source before the
   first run, so the setting was already 0 in RT1.
3. **scautoloc never uses S picks.**
   - Its associator knows only P-type phases: P, PcP, ScP, PP, SKP, PKKP, PKiKP and SKKP (`associator.cpp:41-51`).
   - The S picks (SDL3C) also carry no amplitude, so scautoloc keeps them "waiting for amplitude" for ever.
   - So every origin scrtdd receives has P arrivals only. The offline check (section 4.4) measures what the
     missing S arrivals cost.
4. **SeedLink cannot be bound to localhost** (`iosystem.cc:2788`, `INADDR_ANY`). It was therefore not used.
5. **scautoloc's playback clock delays origin updates (RT3, RT5).**
   - With `--playback`, scautoloc's clock moves only when a pick or an snr/mb amplitude arrives (section 4.5).
   - In RT3 (`--timing pickTime`), the 55-phase update of event 3 was ready by 08:57:43 UTC: its last mb
     amplitude was created then. It was published only at 09:00:28.
   - With `--timing creationTime` (RT5) the same happened: the 55-phase update of event 3 came 2.8 minutes
     after the 44-phase one. For event 9, where picks and amplitudes kept arriving, the last update came 14 s
     after the previous one.
   - Live operation (no `--playback`; the clock is the wall clock, checked every 5 s, `autoloc.wakeupInterval`)
     would not wait like this. It cannot be reproduced with historic data, because without `--playback`
     scautoloc drops picks older than 6 h.
6. **A real-time relocation failed in RT5, for a clear reason in libhdd's weighting.**
   - scrtdd tried event 3's 44-phase scautoloc origin (35.00163 N 127.72726 E, 12.45 km, origin time 0.93 s
     early). Its log:
     `Step 1 relocation successful, new location: lat 34.940071 lon 127.796724 depth -1.8103` (9.3 km away
     horizontally, 1.8 km above sea level: 18.4 km from S1 in 3-D), then `Insufficient number of neighbors`,
     `Failed to perform step 2 origin relocation`, `Cannot relocate origin Origin/20261017092026.794216.2361`.
     Nothing was sent.
   - The cause is in how libhdd down-weights residuals before each solve (solver.cpp:554-584):
     - each double difference gets the weight (1 − (r / (10·MAD/0.6745))²)², clipped at 0, where the factor 10
       comes from the profile's `solver.downWeightingByResidual = 10, 5`;
     - r is measured from zero, while the MAD is measured about the median.
   - Every double difference of a new event carries the error of its starting origin time. Here that is about
     1 s for all of them (median residual 1010 ms), with a small spread (MAD 56 ms). So 222 of the 234
     residuals lay beyond the cut-off of 832 ms. The first solve rested on 12 observations (summed weight 2.8)
     and jumped out of the travel-time grid (`TTT error: Requested location ... is out of grid boundaries`).
   - For the 55-phase versions of the same event (RT2, RT3, RT4 and later RT5), the median residual was 913 ms
     but the MAD 86 ms: the cut-off was 1281 ms, only 8 of 271 residuals were beyond it, and the relocation
     converged.
   - So success depends on the ratio of the starting origin-time error to the residual spread, which is not
     under control in real time. The table lists all 12 relocation attempts of RT2-RT5 (2 + 4 + 2 + 4), step 1,
     first iteration, with cut-off = 10·MAD/0.6745 (`<run>/results/scrtdd_step1_weighting.csv`):

     | run, input origin | double differences | median residual | MAD | cut-off | beyond cut-off | summed weight | result |
     |---|---|---|---|---|---|---|---|
     | RT2/RT3/RT4/RT5, event 3, 55 phases | 271 | 913 ms | 86 ms | 1281 ms | 8 | 70.2 | relocated, 61 m from S1 |
     | RT2/RT3/RT4/RT5, event 9, 37 phases | 219 | 879 ms | 119 ms | 1770 ms | 4 | 124.3 | relocated, 5 m |
     | RT3, event 3, 48 phases | 246 | 962 ms | 72 ms | 1065 ms | 43 | 17.9 | relocated, 70 m |
     | RT3, event 9, 30 phases | 193 | 947 ms | 76 ms | 1125 ms | 18 | 22.8 | relocated, 11 m |
     | RT5, event 9, 23 phases | 157 | 1029 ms | 65 ms | 964 ms | 126 | 1.7 | relocated, 9.1 m |
     | **RT5, event 3, 44 phases** | 234 | 1010 ms | 56 ms | 832 ms | **222** | **2.8** | **failed** |

     - Why the 23-phase case survived and the 44-phase case did not: in both, the first solve rested on a few
       observations.
       - In the 23-phase case its step was small (solution norm 0.65). The residual spread then widened (MAD
         65 → 421 ms), the cut-off rose with it, and the second iteration used nearly all the data and
         converged.
       - In the 44-phase case the first step (norm 3.3) put the event outside the travel-time grid. Every
         observation was then skipped, and there was no way back.
     - Offline diagnostic (`RT5_paced_creationtime/offline_check_failed/`):
       - The same origin with the same settings fails identically offline: step 1 at 34.940071 N 127.796724 E,
         depth −1.81 km, then `Cannot relocate origin`. So the failure is deterministic.
       - With the down-weighting switched off (`0, 0`) both steps finish (136 of 234 P cross-correlations
         ≥ 0.7), but the result lies 1.17 km from S1 (593 m horizontally, 1013 m deeper).
       - So the down-weighting is needed against outliers. The trouble is only that it is measured from zero
         while the starting origin carries a common ~1-s offset.
       - Possible remedies, none tested here: a starting origin with a better origin time (a local velocity
         model for scautoloc), a larger first factor, or residuals measured from their median (a libhdd change).
7. **With scevent's default priorities the relocated origin is rarely the preferred one.**
   - scevent ranks automatic origins by phase count, then by time. The RTDD origin often uses one arrival fewer
     than its input ("phaseCount too low"), and every later scautoloc version with more phases takes over again.
   - So anything that follows preferred origins (alerts, magnitudes, exports) would see the LOCSAT location.
   - RT4 shows the two-line fix (`eventAssociation.priorities` with AUTHOR first, `eventAssociation.authors`).
     With that fix the loop protection is what keeps scrtdd from relocating its own origins.
8. **scrtdd accepts anti-correlated waveforms** (|CC| >= 0.7). This was already noted in steps 07/08.
   - In RT2, 37 of the 166 cross-correlation lags used for event 3 had CC <= −0.7. For event 9 it was 2 of 169.
   - Event 3's final double-difference residuals (median 11.5 ms) are 7 times larger than event 9's (1.6 ms).

## 6. Caveats

- **Two events only.** Event 3 (ML 2.2) is the least consistent event of the cluster in every earlier step. It
  has the widest HypoDD bootstrap box (16/6/26 m) and the largest single-event offsets in step 08 (28-44 m).
  Event 9 (ML 1.6) is typical. Two events show that the chain works; they are not statistics.
- **"Real time" is simulated.**
  - The file feed (RT2, RT4) pushes 9 minutes of data through in about 15 s. Its creation times therefore show
    processing time, not real-time latency.
  - The paced feed (RT3, RT5) releases the 512-byte records at their original pace. msrtsimul hands each record
    over when its clock reaches the record's end time rounded down to a whole second, so 0-1 s early (5-95 %
    spread of wall time minus record end time: 0.9 s).
  - The latencies first reported are counted from the final LOCSAT origin time. They are 1.2-1.3 s longer, not
    shorter, than the same latencies counted from S1's origin time on msrtsimul's clock (section 4.5).
    - 0.69-0.83 s of this is the error of the LOCSAT origin time, so it is an error of the first set.
    - The other ~0.5 s is a choice of clock. A real station sends a record only when it is complete, so on
      msrtsimul's clock the chain gets its data on average 0.5 s earlier than it would from a real network with
      no transmission delay. Counted from S1's origin time, such a network would give values between the two
      sets, about 0.5 s above the second.
  - The real-time latencies depend on the DL picker's "reliable" settings from step 09. A P pick needs one 30-s
    window centered on the trigger, i.e. 15 s of data after it. S picks need windows ending 15-30 s after the P
    pick. Step 09 tested "fast" P settings with phasenet_instance. They gave P picks a median 1.3 s after
    the onset instead of 15.2 s, with about 4 times more false P picks. They were not tried here.
- **The reference catalog is S1**, a multi-event solution whose centroid is 317 m W, 34 m N and 171 m deeper than
  HypoDD's (step 08). A single-event relocation is anchored to that catalog, so "absolute" differences to HypoDD
  or to pyrtdd R1 mostly show the frame offset. The "catalog-relative" columns remove it.
- **The comparison with S1 is not fully independent.** The reference catalog has no rows for the replayed events,
  but its 9 positions are S1 multi-event positions, and S1 was inverted with events 3 and 9 included. So the
  agreement of the RTDD origins with S1 (61.1 m and 5.2 m) is not a fully independent test. That would need a
  catalog from a multi-event run without events 3 and 9 (leave-two-out); this was not done.
- **scautoloc is a P-only, teleseismic-minded locator.**
  - Its final versions are off by 0.3-0.5 km horizontally and 2.7-3.9 km in depth (LOCSAT iasp91). Its
    earliest versions, from 8-10 picks, are off by up to 9 km (depths 23.5 and 18.6 km).
  - scrtdd copes with this because the profile searches neighbors up to 10 km away
    (`singleEvent.maxNeighbourDistance = 10`, 5 ellipsoids). With scrtdd's default of 5 km, such start errors
    would leave fewer neighbors; this was not tested.
- **Log clocks.** SeisComP's log files use local time (KST = UTC+9). The database creation times are UTC.
- The SQLite database was switched to WAL mode before any program used it. Whether the default journal mode
  would cause "database is locked" errors in readers was not tested.

## 7. How to reproduce

All scripts are in `runs/gwangyang/realtime/scripts/`. Each is a dry run unless `--apply` is given, and each
logs to `logs/10_gwangyang_realtime_<run>_<stage>_*.log`.

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker
source install/env_seiscomp.sh                        # env seiscomp; core.plugins = dbsqlite3 is in etc/global.cfg
S=runs/gwangyang/realtime/scripts
R=RT2_filefeed                                         # any new run name
python $S/rt_chain.py prepare --run $R --apply         # configs, catalog, sorted data, SQLite database (~1 min)
#   options: --autoloc-timing creationTime (RT5), --prefer-rtdd (RT4)
python $S/rt_chain.py start   --run $R --apply         # scmaster (127.0.0.1:28180), scevent, scautoloc, scrtdd
python $S/rt_chain.py replay  --run $R --event 20210827220322 --apply                 # feed file (~1 min)
python $S/rt_chain.py replay  --run $R --event 20260202194119 --apply
#   --feed paced: msrtsimul at real-time pace, ~10 min per event (run it in the background)
python $S/rt_chain.py stop    --run $R --apply         # stops every process of the run by PID and proves it
python $S/rt_chain.py dump    --run $R --apply         # scevtls, scxmldump, SQL tables -> <run>/db_dump/
python $S/rt_options.py       --run $R --apply         # <run>/options/run_options.json
python $S/rt_offline_check.py --run $R --apply         # scrtdd --ep on the same origin: P only, and P+S
python $S/rt_offline_check.py --run RT5_paced_creationtime --origins Origin/20261017092026.794216.2361 \
    --variants P,P_nodw --tag _failed --apply          # the failed relocation: as in real time, and without down-weighting
conda activate pyrtdd                                  # (source ~/miniforge3/etc/profile.d/conda.sh first)
python -I runs/gwangyang/dlpicker/scripts/09_settings_json.py --variant phasenet_original_realtime \
    --cfg runs/gwangyang/realtime/$R/seiscomp_user/scautopick.cfg \
    --dump-config runs/gwangyang/realtime/$R/options/scautopick.dump-config.txt \
    --dump-settings runs/gwangyang/realtime/$R/options/scautopick.dump-settings.txt \
    --bound runs/gwangyang/dlpicker/config/stations_bound.csv --out runs/gwangyang/realtime/$R/options/scautopick.settings.json
python -I $S/rt_analyze.py --runs RT1_filefeed,RT2_filefeed,RT3_paced,RT4_filefeed_prefer_rtdd,RT5_paced_creationtime --apply
```

`rt_chain.py status --run $R` lists the run's processes and their listening sockets. `start` refuses to run if
port 28180 is taken or if any process with a module name already runs for this user. `stop` signals only
the PIDs recorded in `<run>/pids.json`, after checking `/proc/<pid>/comm`.

**Script versions.**

- From now on, the md5 of every driver script is recorded. Each `--apply` stage of `rt_chain.py` (prepare,
  start, replay, stop, dump, options) and of `rt_offline_check.py` appends to
  `<run>/options/script_provenance.json`:
  - the md5 of `rt_chain.py`, `rt_options.py`, `rt_offline_check.py` and `rt_analyze.py` on disk;
  - the md5 of the running script as loaded, the stage, the time and the command line.
  - A copy of the running script is kept as `<run>/options/scripts/<name>.<md5>.py`.
- `rt_options.py` copies that list into `run_options.json` (`script_provenance`). It also records the md5 of the
  four scripts on disk when it runs (`driver_scripts_on_disk_when_run_options_written`). `rt_analyze.py` writes its
  own md5 into `<run>/results/summary.json` (`rt_analyze_md5`).
- RT1-RT5 were made before this, so their script md5s were not recorded. Their `run_options.json` says so
  (`script_provenance`: "not recorded: run made before provenance recording; ...").
- The scripts on disk were edited after some runs:
  - `rt_chain.py` at 18:27 KST, during RT5. Only RT5's stop and dump started after that edit.
  - `rt_offline_check.py` at 18:37 KST, after its last `--apply` at 18:36.
  - So the exact versions behind RT1-RT4, RT5's prepare, start and replays, and the two offline checks are not
    kept (`run_options.json` → `script_provenance_known_from_file_times`).
- One known command-line difference between runs (`<run>/pids.json`; `run_options.json` →
  `scautoloc_timing_argument`):
  - RT1-RT3 ran scautoloc without `--timing`, so with its default pickTime (scautoloc/app.h:82);
  - RT4 passes `--timing pickTime` and RT5 `--timing creationTime`.
  - For RT4 this is the same behavior as RT1-RT3.

## 8. Files

Everything is under `runs/gwangyang/realtime/`:

- `scripts/rt_chain.py`: prepare, start, replay, stop, dump and status (env seiscomp).
- `scripts/rt_options.py`: `<run>/options/run_options.json`.
- `scripts/rt_offline_check.py`: `scrtdd --ep` on the real-time input origin, P only and P+S.
- `scripts/rt_analyze.py`: all result tables (env pyrtdd).
- `scripts/fill_rt5.py`: the one-off helper that filled the RT5 rows of this note from RT5's tables (copied here
  from the session scratchpad; not part of the chain).
- `<run>/seiscomp_user/*.cfg`: the configuration of the run, with comments explaining every set value.
- `<run>/config/`: the scautoloc grid and station list.
- `<run>/reference_catalog/`: the scrtdd catalog.
- `<run>/data/`: the sorted miniSEED files.
- `<run>/db/seiscomp.sqlite`: the database written by scmaster; `seiscomp_after_import.sqlite` is the state
  before the test.
- `<run>/logs/`: the logs of every module:
  - `scmaster.log`, `scevent.log`, `scautoloc.log` and `scautoloc_picklog*`, `scrtdd.log`;
  - `scautopick_<event>_<feed>.log` and `.time.txt`, `msrtsimul_<event>.stderr`.
- `<run>/work/scrtdd/singleevent_*/`: scrtdd's diagnostics for each relocation.
- `<run>/network/`: `ss` and `pgrep` records before start, after start, after each replay and after stop.
- `<run>/pids.json`, `<run>/replays.json`: processes, command lines, wall times.
- `<run>/options/`: option dumps (section 3); for runs made from now on also `script_provenance.json` and
  `scripts/<name>.<md5>.py` (section 7; RT1-RT5 have none).
- `<run>/db_dump/`: `scevtls.txt`, `event_<id>.xml` (scxmldump -E -P -A), `picks_all.xml`, `sql_*.csv`.
- `<run>/results/`:
  - `picks_vs_offline.csv`, `origins.csv`, `positions_vs_reference.csv`, `scrtdd_relocations.csv`;
  - `scrtdd_diagnostics_dd_counts.csv`, `scrtdd_step1_weighting.csv`, `delays.csv` (paced runs: both latency sets
    of section 4.5), `scxmldump_vs_sql.csv`, `summary.json` (with `rt_analyze_md5`).
- `RT2_filefeed/offline_check/`: `offline_check.csv` and `.json`, and per event `origin_P.xml`,
  `origin_PS.xml` and the scrtdd outputs.
- `RT5_paced_creationtime/offline_check_failed/`: the same for the origin whose relocation failed (variants P
  and P_nodw).
- `comparison/`: the tables for all runs together:
  - `positions_vs_reference_all_runs.csv`, `key_position_differences.csv`;
  - `delays_all_runs.csv`, `context_S1_vs_other_offline_solutions.csv`;
  - `summary_all_runs.json`, the key numbers per run and event.
- Driver logs: `logs/10_gwangyang_realtime_*.log`.
