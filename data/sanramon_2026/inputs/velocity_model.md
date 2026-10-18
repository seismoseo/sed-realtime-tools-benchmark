# Velocity model for the San Ramon 2025-26 benchmark

Short version: the NCSS's own routine model for this area is still **CON (Concord–Calaveras)**, the same model
as in the 2015 benchmark. We use it exactly as in 2015, with one number changed: the model top now sits
**0.32 km** above sea level (the median NCSS datum of the 2025-26 events; 2015: 0.29 km). The top velocity is
extended up to 3 km above sea level, and S velocities come from Vs = Vp / 1.73. The model is in
`velocity_model.csv`; the NonLinLoc grids built from it are in `nll_con_tm/time/` (model name `sanramon2026_con`).
Made by `tools/07_velocity_model.py`; numbers in `../reference_tables/stats_07.json`.

## 1. Does the NCSS use CON for these earthquakes?

Yes, for 918 of the 927 benchmark events exclusively, and for at least 90 % of the travel time in 924.

* **Processing version.** All 927 NCSS solutions carry "NC 06" in columns 165–168 of the Hypoinverse summary
  line (2015: "NC 05"). Version 06 is the configuration that NCEDC published as
  `hypoinv-standalone-20230210.zip` (`cal5-1.41.hyp`: `VER 'NC' '06'`; model set-up `multmod5a.hyp`; the
  switch-over is logged in its `README.hypoinverse-VER5toVER6`, 2019-09-24). That package is still the newest
  one on https://ncedc.org/pub/catalogs/ncsn/hypoinverse/ (directory listing fetched 2026-10-18, identical to
  2026-10-17). So the 2025-26 events were located with exactly the model files we read, not with older ones as
  in 2015.
* **Which regional model.** Hypoinverse picks the model(s) from the epicentre (hyp1.40.pdf pp. 13–15): inside
  the inner circle of any node, that node's model is used alone; otherwise the models of up to the first three
  outer circles that contain the epicentre are mixed with cosine-taper weights, normalised to 1, and the default
  model fills any shortfall. `tools/07_velocity_model.py` applies this rule to every benchmark event's final
  NCSS epicentre with the nodes of `multmod5a.hyp` (`reference_tables/ncss_model_weights.csv`):

  | CON weight | events |
  |---|---:|
  | 1.0 (CON only) | 918 |
  | 0.86–0.93 (rest HAY, Hayward model) | 7 |
  | 0.66 (rest HAY): 75342697, 37.693 N −121.990 | 1 |
  | 0.37 (HAY 0.63): 75434697, 37.701 N −122.014 (outside the box by NCSS location; in the box by DD) | 1 |

  The relevant CON nodes are the circles at 37°48.2'N 121°56.4'W and 37°43.0'N 121°53.2'W (7.5 km inner radius,
  7 km transition). The HAY nodes are at least 10.6 km away. No other model touches any event.
* **Model label.** As in 2015, NCEDC leaves the crust-model field (cols 111–113) blank, so the assignment rests
  on the region geometry above.

**Decision: CON for all events**, as in 2015. For the two HAY-blended events at the south-west edge the NCSS
travel times are partly HAY; a single 1-D model cannot reproduce that, and it does not matter for double
differences.

## 2. The CON model itself (unchanged since 2015)

| Depth below NCSS model surface (km) | Vp (km/s) |
|---:|---:|
| 0.00 | 2.50 |
| 2.00 | 4.70 |
| 12.00 | 5.77 |
| 24.00 | 6.12 |
| 26.00 | 7.95 (half-space) |

Linear between the points; constant below 26 km. Sources: NCEDC `shadow2000.pdf` Table 8 (row CON), and the
2023 package's `cor.crt` (title `CONCORD-CALAVERAS`, identical points; `multmod5a.hyp` loads model 9 from
`con.crt`, which the zip contains under the name `cor.crt`; see `../../sanramon_2015/inputs/velocity_model.md`
section 2). The NCSS also applies model station delays (`con5.del`); we do not, as in 2015.

## 3. Depth reference (datum)

NCSS geoid depth = model depth − datum, the datum being the mean elevation of the 5 nearest stations (columns
171–174). For the 927 benchmark events the datum ranges from 167 to 473 m, median **319 m** (most common values
296 m: 147 events, 424 m: 81, 423 m: 62). We put the model surface at **0.32 km above sea level** and shift
every point by −0.32 km. One fixed shift for all events: for an event whose own datum differs, the model is up
to 0.15 km off from where Hypoinverse had it.

## 4. Above the model surface

The first value (2.50 km/s) is kept constant from −0.32 km up to −3.0 km, the grid top, so that stations above
the model surface sit in the model (as in 2015). Hypoinverse instead puts all stations on the model surface.

## 5. S velocities

| Source | What it says |
|---|---|
| NCSS, `multmod5a.hyp`, `psm 9 1.708 0.208` | for CON: S travel time = 1.708 × P travel time + 0.208 s (HAY: `psm 26 1.726 0.137`) |
| Waldhauser & Schaff (2008), para. 33 | S model = P model / 1.73 |
| 2015 picks (442 events) | Wadati median 1.735; beyond 10 km 1.765 |
| **2025-26 picks, all stations** (527 events, `tools/14_vpvs_wadati.py`) | Wadati median **1.60** (IQR 1.45–1.68); pooled fit S−P = 0.680·Ptt + 0.53 s |
| **2025-26 picks, stations beyond 10 km** (273 events) | Wadati median **1.776** (IQR 1.70–1.86); pooled fit S−P = 0.772·Ptt + 0.07 s |

The all-station number is not a Vp/Vs of the crust. The 2025-26 picks hold many more S picks at stations within
10 km (909 of 3,935 S–P pairs; 646 within 5 km, against 279 in 2015), and those carry a large extra S delay: the
ratio tS/tP (with NCSS origin times) has a median of 2.15 within 5 km, against 1.79–1.80 at 10–40 km. A
station-dependent delay of that kind tilts the Wadati line. Without the near stations, the 2025-26 picks give
1.77–1.78, close to 2015 (1.76–1.77).

**Choice: Vs = Vp / 1.73 at every depth, as in 2015.** With it, the median S−P residual is +0.32 s over all
pairs and +0.26 s beyond 10 km (2015: about +0.2–0.3 s). These offsets are nearly the same for all events at a
station and cancel in double differences; they appear in rtDD's absolute-residual terms. A model-sensitivity
test with Vp/Vs 1.77–1.78 is a natural option.

## 6. Files

* `velocity_model.csv`: same columns as in 2015 (`top_km` below sea level, `vp_km_s`, `vs_km_s`,
  `vp_grad_per_km`, `vs_grad_per_km`, `top_km_below_model_surface`, `note`). Row 1 = constant extension above
  the model surface; last row = half-space. **The velocity is linear between rows (gradients), not constant.**
* `nll_con_tm/run/Vel2Grid.in`: the same model as NonLinLoc `LAYER` lines.
* `../reference_tables/ncss_con_ttgen_table.csv`: the NCSS TTGEN travel-time table of CON (from `cor.crt`), used
  to check our ray code and the grids.
* `../reference_tables/ncss_model_weights.csv`: Hypoinverse model weights per benchmark event.
