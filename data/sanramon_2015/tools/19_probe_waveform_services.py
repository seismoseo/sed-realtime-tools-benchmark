# 19_probe_waveform_services.py -- small, logged probes made before writing download_waveforms.py
# (work package SR-B). Answers three questions with as few requests as possible:
#   1. does EarthScope (service.earthscope.org) hold data for the NCEDC networks we need
#      (NC, BK, NP, PB, BP)? -> fdsnws/availability/1/extent for 6 sample channels, 2015-10-13..12-01
#   2. how does NCEDC fdsnws/dataselect answer a small bulk POST (status, bytes, seconds,
#      record length, encoding, quality code, how far the records reach beyond the window)?
#   3. what does NCEDC answer for a channel that has no data (204 or 404)?
#   4. (after probe 1 showed that EarthScope retired fdsnws/availability) does the EarthScope
#      station service with matchtimeseries=true tell which channels EarthScope holds data for?
# Every request goes through sr_common.polite_request (one at a time, logged to
# logs/sanramon_requests.tsv). Raw answers are kept in reference/waveforms_probe/.
# Usage: python -I 19_probe_waveform_services.py [probe numbers, default 1 2 3]
#        (probes 1-3 were run first; probe 4 afterwards)

import io
import os
import sys

from obspy import read

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "19_probe_waveform_services"
OUT = os.path.join(C.REF, "waveforms_probe")
ES_AVAIL = "https://service.earthscope.org/fdsnws/availability/1/extent"
NC_DS = "https://service.ncedc.org/fdsnws/dataselect/1/query"

SAMPLE = ["NC CBR -- EHZ", "BK BKS 00 HHZ", "NP 1690 ER HNZ", "NC C029 01 HNZ", "BP CCRB 40 DP1",
          "NN EMB -- HHZ"]


def main(which):
    os.makedirs(OUT, exist_ok=True)
    if "4" in which:
        probe4()
    if "1" not in which:
        return
    # 1. EarthScope holdings
    body = "format=text\nmergequality=true\nmergesamplerate=true\n" + "\n".join(
        f"{s} 2015-10-13T00:00:00 2015-12-01T00:00:00" for s in SAMPLE) + "\n"
    r = C.polite_request(ES_AVAIL, TOOL, method="POST", data=body.encode(),
                         out_file=os.path.join(OUT, "earthscope_extent_sample.txt"),
                         headers={"Content-Type": "text/plain"}, timeout=120)
    print("EarthScope extent:", None if r is None else r.status_code)
    if r is not None:
        print(r.text[:3000])
    # 2. NCEDC dataselect, mainshock 72540765 (2015-10-19T23:21:17.68Z), window -10..+30 s
    lines = ["NC C029 01 HN?", "NC CBR -- EHZ", "BK BKS 00 HH?", "NP 1690 ER HN?", "BP CCRB 40 DP?"]
    body = "\n".join(f"{x} 2015-10-19T23:21:07.680000 2015-10-19T23:21:47.680000" for x in lines) + "\n"
    out = os.path.join(OUT, "ncedc_dataselect_72540765_sample.mseed")
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
    body = "NC CBR -- XXZ 2015-10-19T23:21:07.680000 2015-10-19T23:21:47.680000\n"
    r = C.polite_request(NC_DS, TOOL, method="POST", data=body.encode(),
                         headers={"Content-Type": "text/plain"}, timeout=120)
    print("NCEDC no-data answer:", None if r is None else r.status_code,
          None if r is None else r.text[:300])


def probe4():
    url = "https://service.earthscope.org/fdsnws/station/1/query"
    body = "level=channel\nformat=text\nmatchtimeseries=true\n" + "\n".join(
        f"{s} 2015-10-13T00:00:00 2015-12-01T00:00:00" for s in SAMPLE) + "\n"
    r = C.polite_request(url, TOOL, method="POST", data=body.encode(),
                         out_file=os.path.join(OUT, "earthscope_station_matchtimeseries_sample.txt"),
                         headers={"Content-Type": "text/plain"}, timeout=120)
    print("EarthScope station matchtimeseries:", None if r is None else r.status_code)
    if r is not None:
        print(r.text[:3000])


if __name__ == "__main__":
    main(sys.argv[1:] or ["1", "2", "3"])
