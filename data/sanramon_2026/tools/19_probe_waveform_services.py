# 19_probe_waveform_services.py -- (2025-26 case; copied from the 2015 tool) small, logged probes
# made before running download_waveforms.py. Same questions as in 2015, for 2025-26 data; the
# sample channels are the 6 picked sensors of the mainshock nearest to it, one per network if
# possible (picks_ncss.csv), instead of the 2015 list:
#   1. does EarthScope (service.earthscope.org) hold data for the NCEDC networks we need?
#      -> fdsnws/availability/1/extent for the sample channels over the benchmark period
#   2. how does NCEDC fdsnws/dataselect answer a small bulk POST (status, bytes, seconds,
#      record length, encoding, quality code, how far the records reach beyond the window)?
#   3. what does NCEDC answer for a channel that has no data (204 or 404)?
#   4. (after probe 1 showed that EarthScope retired fdsnws/availability) does the EarthScope
#      station service with matchtimeseries=true tell which channels EarthScope holds data for?
#   5. (added after the download, 2025-26 case) event 75311457 (2026-02-09 22:05:12) had no NC/CE/NP
#      data at NCEDC or EarthScope: how long is the gap? NCEDC dataselect for NC CBR -- EHZ and
#      NC CSR 01 HNZ (12.8 and 3 km), 22:00-22:10 UTC; the answer's trace spans are printed.
# Every request goes through sr_common.polite_request (one at a time, logged to
# logs/sanramon2026_requests.tsv). Raw answers are kept in reference/waveforms_probe/.
# Usage: python -I 19_probe_waveform_services.py [probe numbers, default 1 2 3]
#        (probes 1-3 were run first; probe 4 afterwards)

import io
import os
import sys

import pandas as pd
from obspy import UTCDateTime, read

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "19_probe_waveform_services"
OUT = os.path.join(C.REF, "waveforms_probe")
ES_AVAIL = "https://service.earthscope.org/fdsnws/availability/1/extent"
NC_DS = "https://service.ncedc.org/fdsnws/dataselect/1/query"



def sample_channels():
    """6 picked channels of the mainshock, nearest first, preferring one per network"""
    pk = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                     dtype={"location": str})
    pk = pk[(pk.event_id == C.MAINSHOCK_ID) & (pk.phase == "P")].copy()
    pk["d"] = pk.epi_dist_km.astype(float)
    pk = pk.sort_values("d")
    first = pk.drop_duplicates("network")
    rest = pk[~pk.index.isin(first.index)]
    sel = pd.concat([first, rest]).head(6)
    return [f"{r.network} {r.station} {r.location or '--'} {r.channel}" for r in sel.itertuples()]


SAMPLE = None
T0, T1 = C.T0_STR, C.T1_STR


def probe5():
    lines = ["NC CBR -- EHZ", "NC CSR 01 HNZ"]
    body = "\n".join(f"{x} 2026-02-09T22:00:00 2026-02-09T22:10:00" for x in lines) + "\n"
    out = os.path.join(OUT, "ncedc_dataselect_gap_75311457.mseed")
    r = C.polite_request(NC_DS, TOOL, method="POST", data=body.encode(), out_file=out,
                         headers={"Content-Type": "text/plain"}, timeout=300)
    print("probe 5, NCEDC 2026-02-09 22:00-22:10:", None if r is None else r.status_code,
          None if r is None else len(r.content), "bytes")
    if r is not None and r.status_code == 200:
        for tr in read(io.BytesIO(r.content), format="MSEED").merge(method=-1).sort():
            print("  ", tr.id, tr.stats.starttime, tr.stats.endtime, tr.stats.npts)


def main(which):
    global SAMPLE
    if which == ["5"]:
        probe5()
        return
    SAMPLE = sample_channels()
    print("sample channels:", SAMPLE)
    os.makedirs(OUT, exist_ok=True)
    if "4" in which:
        probe4()
    if "1" not in which:
        return
    # 1. EarthScope holdings
    body = "format=text\nmergequality=true\nmergesamplerate=true\n" + "\n".join(
        f"{s} {T0} {T1}" for s in SAMPLE) + "\n"
    r = C.polite_request(ES_AVAIL, TOOL, method="POST", data=body.encode(),
                         out_file=os.path.join(OUT, "earthscope_extent_sample.txt"),
                         headers={"Content-Type": "text/plain"}, timeout=120)
    print("EarthScope extent:", None if r is None else r.status_code)
    if r is not None:
        print(r.text[:3000])
    # 2. NCEDC dataselect, mainshock, window -10..+30 s, sample sensors with all components
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    o = UTCDateTime(ev.loc[ev.event_id == C.MAINSHOCK_ID, "origin_time_utc"].iloc[0])
    w0, w1 = (o - 10).strftime("%Y-%m-%dT%H:%M:%S.%f"), (o + 30).strftime("%Y-%m-%dT%H:%M:%S.%f")
    lines = [x[:-1] + "?" for x in SAMPLE[:5]]
    body = "\n".join(f"{x} {w0} {w1}" for x in lines) + "\n"
    out = os.path.join(OUT, f"ncedc_dataselect_{C.MAINSHOCK_ID}_sample.mseed")
    r = C.polite_request(NC_DS, TOOL, method="POST", data=body.encode(), out_file=out,
                         headers={"Content-Type": "text/plain"}, timeout=300)
    print("NCEDC dataselect:", None if r is None else r.status_code,
          None if r is None else len(r.content), "bytes")
    if r is not None and r.status_code == 200:
        st = read(io.BytesIO(r.content), format="MSEED", details=True)
        for tr in st:
            m = tr.stats.mseed
            print(tr.id, tr.stats.starttime, tr.stats.endtime, tr.stats.sampling_rate, tr.stats.npts,
                  m.get("encoding"), m.get("record_length"), m.get("dataquality"), tr.data.dtype)
    # 3. no-data answer (a channel code that does not exist)
    n, st_, l_, _ = SAMPLE[0].split()
    body = f"{n} {st_} {l_} XXZ {w0} {w1}\n"
    r = C.polite_request(NC_DS, TOOL, method="POST", data=body.encode(),
                         headers={"Content-Type": "text/plain"}, timeout=120)
    print("NCEDC no-data answer:", None if r is None else r.status_code,
          None if r is None else r.text[:300])


def probe4():
    global SAMPLE
    SAMPLE = SAMPLE or sample_channels()
    url = "https://service.earthscope.org/fdsnws/station/1/query"
    body = "level=channel\nformat=text\nmatchtimeseries=true\n" + "\n".join(
        f"{s} {T0} {T1}" for s in SAMPLE) + "\n"
    r = C.polite_request(url, TOOL, method="POST", data=body.encode(),
                         out_file=os.path.join(OUT, "earthscope_station_matchtimeseries_sample.txt"),
                         headers={"Content-Type": "text/plain"}, timeout=120)
    print("EarthScope station matchtimeseries:", None if r is None else r.status_code)
    if r is not None:
        print(r.text[:3000])


if __name__ == "__main__":
    main(sys.argv[1:] or ["1", "2", "3", "4"])
