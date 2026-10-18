# Velocity model for the San Ramon 2015 benchmark

Short version: we use the NCSS's own routine model for this area, **CON (Concord–Calaveras)**. It is a
1-D P model in which velocity changes linearly with depth between five points. We shift it so that its
top sits 0.29 km above sea level, extend the top velocity up to 3 km above sea level (to reach the
stations), and get S velocities from Vs = Vp / 1.73. The model is in `velocity_model.csv`, and NonLinLoc
2-D grids built from it are in `nll_con/time/`.

## 1. Which model the NCSS used for these earthquakes

The NCSS locates earthquakes with Hypoinverse-2000. It uses about 30 regional 1-D models and picks the
model from the epicentre. These are the "multiple crustal models" of the Hypoinverse manual
(Klein, hyp1.40.pdf, pp. 13–17).

* Set-up file: `multmod5a.hyp`, in the NCEDC package `hypoinv-standalone-20230210.zip`
  (https://ncedc.org/pub/catalogs/ncsn/hypoinverse/hypoinv-standalone-20230210.zip, linked from
  https://ncedc.org/ncedc/catalog-reproducing-hypoinverse-locations.html; local copy in
  `reference/ncss_hypoinverse_metadata/`).
* Region definition there: model 9 = `concord-calaveras`, `crt 9 './hypoinverse/models/con.crt'`. Its
  region is six circles (`nod` lines). One of them is centred at 37°48.2'N 121°56.4'W, with a 7.5 km
  inner radius and a 7 km wide transition ring.
* Check against our events (`tools/07_velocity_model.py`, `reference_tables/stats_07.json`): **684 of
  the 685 benchmark events lie inside a CON inner circle**, where CON gets full weight. The remaining
  event lies in a CON transition ring and also touches the outer ring of the HAY (Hayward) model. No
  event is near any other model.
* The archive summary lines do not show which model was used: NCEDC leaves columns 111–113 blank. The
  QuakeML only says `methodID = HYP2000_m2g`. So the CON assignment above comes from the region
  geometry, not from a model label in the data.

## 2. The CON model itself

| Depth below NCSS model surface (km) | Vp (km/s) |
|---:|---:|
| 0.00 | 2.50 |
| 2.00 | 4.70 |
| 12.00 | 5.77 |
| 24.00 | 6.12 |
| 26.00 | 7.95 (half-space) |

Velocity changes linearly between the points. Below 26 km the velocity is constant (the half-space).
Sources that give the same numbers:

1. NCEDC `shadow2000.pdf` (Klein, revised 2006), **Table 8, "Depth-Velocity points for models with
   linear gradients in layers", row CON**, p. 25. The same table credits the model to "Klein pers. comm.
   (1991), VELEST". https://ncedc.org/pub/doc/ncsn/shadow2000.pdf (local:
   `reference/docs/ncedc_shadow2000.pdf`).
2. The travel-time table file in the 2023 package. The zip has no `con.crt`. It does have `cor.crt`,
   whose title line reads `CONCORD-CALAVERAS    5  0.1290`, and whose depths (0, 2, 12, 24, 26) and
   velocities (2.50, 4.70, 5.77, 6.12, 7.95) are identical to Table 8. We take it to be the CON table
   under another file name (a likely reason: "CON" is a reserved file name on Windows).
3. The NCEDC blog of 2015-10-07 (`reference/docs/ncedc_blog_2015-10-07_depth_datum.html`) says that "the
   fundamental location algorithm and multiple crustal models used in the NCSS are unchanged" when
   depths were moved to the geoid. The point values have been the same from 2006 (Table 8) to 2023
   (`cor.crt`), so this model was in use in October 2015.

The NCSS also applies **station delays** that belong to each model (`con5.del`; the 2015 blog
says the 4th revision was in use then). We do **not** use them: the NonLinLoc grids hold pure model
travel times. rtDD works on differences between events, so a constant delay at one station cancels.

## 3. Depth reference (datum)

Hypoinverse puts all stations on the flat top of the model. The depth below that surface is the
"model depth". Since 2015-10-07 the NCSS reports geoid depth = model depth − datum, where the datum is
the average elevation of the 5 nearest stations (blog of 2015-10-07; hyp1.40 p. 25). The archive
summary line gives the datum in columns 171–174. For the 685 benchmark events it ranges from 120 to
421 m, with a median of **290 m**: values 290–291 m for 246 events, 399–400 m for 142, 278–279 m for 91.

For NonLinLoc and rtDD, depths and station elevations must refer to sea level. We therefore put the
model surface at **0.29 km above sea level** (depth −0.29 km) and shift every point by −0.29 km. This
is a single fixed shift, so for events whose own datum differs (0.12–0.42 km) the model is placed up
to 0.17 km off from where Hypoinverse had it.

## 4. Above the model surface

The stations that get grids (within 120 km) sit at up to 1.25 km elevation (BK.MHC, Mount Hamilton;
`rtdd_catalog/station.csv`). The model has no velocity
above its surface, so the first value (2.50 km/s) is kept constant from −0.29 km up to −3.0 km, the
grid top. Hypoinverse ignores station elevation and leaves this effect to the station delays.

## 5. S velocities

| Source | What it says |
|---|---|
| NCSS, `multmod5a.hyp`, `psm 9 1.708 0.208` | for CON: S travel time = 1.708 × P travel time + 0.208 s (fit by F. Klein, 8/2010, 354 readings) |
| NCSS, `cal5-1.41.hyp` `POS 1.78`; `multmod5a.hyp` `POS 1.778` | default P/S ratio for models without their own relation |
| Waldhauser & Schaff (2008), JGR 113, B08311, para. 33, p. 13 | "S-velocity model … obtained by scaling the P model by a factor of 1.73" (stated for their 3-D Parkfield test; the 1-D catalog paragraph, para. 15, p. 6, gives no ratio) |
| Our picks (San Ramon, 442 events with ≥ 3 S–P pairs) | Wadati slope (S−P against P arrival time, independent of origin time): median Vp/Vs **1.735**, interquartile range 1.68–1.79; a pooled fit with NCSS origin times gives S−P = 0.715·Ptt + 0.28 s |

**Choice: Vs = Vp / 1.73 at every depth.** The data show a move-out ratio of about 1.73, the same as the
DD reference. The extra ~0.2–0.3 s S delay found by NCSS and in our fit is a near-station effect. In
double differences it is almost the same for every event at a given station, so it cancels. If rtDD's
absolute-residual equations are switched on, the S residuals will carry this offset.

## 6. What Waldhauser & Schaff used for the DD catalog

Para. 15, p. 6: "1-D layered velocity models are used to locally predict travel times … The models are
chosen from a compilation of 39 local models used by the NCSN … [Oppenheimer et al., 1993]. … We
resample the velocity-depth function of each model to generate models with 28 layers of constant
velocity." So the DD reference was computed with the same family of NCSS regional models, turned into
28 homogeneous layers. For this area that means CON or its predecessor. The paper does not list the
model or the depth reference for San Ramon. The 2015 events in the NCEDC DD catalog come from the
real-time DD-RT system (Waldhauser 2009). The LDEO v202112.1 catalog re-ran the base relocation with
geoid depths.

## 7. Files

* `velocity_model.csv`: columns `top_km` (top of the segment, km below sea level), `vp_km_s`,
  `vs_km_s` (velocity at that top), `vp_grad_per_km`, `vs_grad_per_km` (linear increase to the next
  row), `top_km_below_model_surface` (original NCSS depth), `note`. Row 1 is the constant extension
  above the model surface. The last row is the half-space. **The velocity is not constant between
  rows.** Use the gradients, or resample the model, if a tool needs homogeneous layers.
* `nll_con/run/Vel2Grid.in`: the same model as NonLinLoc `LAYER` lines (top, Vp, gradient, Vs,
  gradient). The grids built from it are in `nll_con/time/` (TRANS AZIMUTHAL_EQUIDIST, as asked)
  and `nll_con_tm/time/` (TRANS_MERC, which keeps true distances to < 7 m;
  see `docs/sanramon_inputs.md` section 7).
* Checks, with NonLinLoc always the later one:
  * against an independent ray calculation (`tools/ray1d.py`): 0–14 ms (P) and 0–24 ms (S);
  * against the NCSS TTGEN table (P, surface station): mean +10 ms, max 18.5 ms.
* `../reference_tables/ncss_con_ttgen_table.csv`: the NCSS travel-time table of CON, decoded from
  `cor.crt` (source depth below the model surface 0–40 km × distance 0–135 km, receiver on the model
  surface). We use it to check our own ray code and the NonLinLoc grids.

## 8. Alternatives considered

Because the documented NCSS model was found, no published substitute was needed. The fallbacks named
in the task were the Calaveras-fault model of Waldhauser & Ellsworth (2000, BSSA 90(6)) and Gil7
(Dreger & Romanowicz 1994). Either could be used for a model-sensitivity test.
