# USGS aftershock forecast (OAF) for the 2025-26 San Ramon sequence

Downloaded 2026-10-18 from ComCat (no changes made):
- `nc75305736.json`: event GeoJSON of the mainshock, https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=nc75305736&format=geojson
  (M 4.2 (Mw 4.18), 2026-02-02 15:01:13 UTC, 4 km SE of San Ramon). Event page: https://earthquake.usgs.gov/earthquakes/eventpage/nc75305736/oaf/overview
- `oaf_forecast.json`, `oaf_forecast_data.json`: the 'oaf' product of that event (forecast issued 2026-10-12 15:01 UTC).

Key content:
- Reasenberg-Jones sequence-specific model: a -1.3, b 1.0, p 1.15, c 0.012 d, Mcat 2.25.
- Forecast region: a circle of 10 km radius around 37.7573 N, 121.9418 W.
- Observed since the mainshock: 4 events of M >= 3, none of M >= 4.
- Probability of at least one M 3+ in the month after 2026-10-12: 4 %.
- USGS note: "the sequence of events in San Ramon appears to be a swarm and a forecast based solely on aftershock
  processes can not capture all of the characteristics of the more complex behavior of a swarm."
