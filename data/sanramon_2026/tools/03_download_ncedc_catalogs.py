# 03_download_ncedc_catalogs.py -- download the NCEDC double-difference (DD) catalog and the NCSS
# routine catalog + phase picks for the San Ramon 2025-26 sequence (copied from the 2015 tool and
# parametrised: period and boxes come from sr_common.py).
#
# Service: POST https://ncedc.org/cgi-bin/catalog-search2.pl (the form behind
#          https://ncedc.org/ncedc/catalog-search.html). The answer is HTML with the text in <pre>.
# Two boxes (sr_common.BOX / WIDE):
#   box  = the benchmark box  lat 37.70..37.80, lon -122.01..-121.89
#   wide = box + 0.05 deg (about 5 km) margin, lat 37.65..37.85, lon -122.06..-121.84, so that
#          events whose routine (NCSS) and DD locations fall on different sides of the box edge can
#          still be matched by event id.
# Period sr_common.T0_STR .. T1_STR = 2025/10/01 00:00 - 2026/10/18 00:00 UTC (end excluded), all
# magnitudes (minmag -5, maxmag 10, and the "include events with no magnitude" box ticked), depth
# -10..100 km (geoid depths can be < 0), event type E (earthquakes). Dates are sent as
# 'YYYY/MM/DD,hh:mm:ss' (with slashes; the form rejects other forms). Phase files (ncphraw) are
# requested one week at a time.
# Difference from 2015: format ddjson is no longer requested (in 2015 it did not return JSON but
# built a "cross-section set" on the NCEDC site).
#
# Output: reference/ncedc_catalog/raw/<fmt>_<box>_<start>_<end>.html  (the raw answer)
#         reference/ncedc_catalog/txt/<fmt>_<box>_<start>_<end>.txt   (text inside <pre>)
# Re-run safe: requests whose .html already exists are skipped. All requests are logged in
# logs/sanramon2026_requests.tsv. Usage: python -I 03_download_ncedc_catalogs.py [--dry-run] [--only fmt[_box],...]

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "03_download_ncedc_catalogs"
URL = "https://ncedc.org/cgi-bin/catalog-search2.pl"
OUT = os.path.join(C.REF, "ncedc_catalog")

BOXES = {k: dict(minlat=f"{b['lat0']:.2f}", maxlat=f"{b['lat1']:.2f}", minlon=f"{b['lon0']:.2f}",
                 maxlon=f"{b['lon1']:.2f}") for k, b in (("box", C.BOX), ("wide", C.WIDE))}
T0, T1 = dt.datetime.fromisoformat(C.T0_STR), dt.datetime.fromisoformat(C.T1_STR)
COMMON = dict(minmag="-5", maxmag="10", mindepth="-10", maxdepth="100", etype="E",
              no_mag="no_mag", keywds="", outputloc="web", searchlimit="500000")


def tstr(t):
    return t.strftime("%Y/%m/%d,%H:%M:%S")


def requests_list():
    reqs = []
    # DD catalog: every text format, benchmark box; csv also for the wide box
    for fmt in ("ddcsv", "ddread", "ddraw"):
        reqs.append((fmt, "box", T0, T1))
    reqs.append(("ddcsv", "wide", T0, T1))
    # NCSS routine catalog (one line per event)
    for fmt, box in (("nccsv", "box"), ("nccsv", "wide"), ("ncread", "box"), ("ncraw", "wide")):
        reqs.append((fmt, box, T0, T1))
    # NCSS catalog + phases (Hypoinverse archive), wide box, one week per request
    t = T0
    while t < T1:
        t2 = min(t + dt.timedelta(days=7), T1)
        reqs.append(("ncphraw", "wide", t, t2))
        t = t2
    return reqs


def main():
    dry = "--dry-run" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "txt"), exist_ok=True)
    for fmt, box, t0, t1 in requests_list():
        tag = f"{fmt}_{box}_{t0:%Y%m%d}_{t1:%Y%m%d}"
        if only and f"{fmt}_{box}" not in only and fmt not in only:
            continue
        raw = os.path.join(OUT, "raw", tag + ".html")
        txt = os.path.join(OUT, "txt", tag + ".txt")
        form = dict(format=fmt, mintime=tstr(t0), maxtime=tstr(t1), **BOXES[box], **COMMON)
        if os.path.exists(raw) and os.path.getsize(raw) > 0:
            print(f"skip (on disk) {tag}")
        elif dry:
            print(f"would POST {URL} {form}")
            continue
        else:
            r = C.polite_request(URL, TOOL, method="POST", data=form, out_file=raw, timeout=600)
            if r is None or r.status_code != 200:
                print(f"FAILED {tag}: {None if r is None else r.status_code}")
                continue
        with open(raw, encoding="latin-1") as f:
            body = f.read()
        text = C.strip_html_pre(body)
        with open(txt, "w") as f:
            f.write(text)
        nlines = len([ln for ln in text.splitlines() if ln.strip()])
        flag = ""
        low = body.lower()
        if "limit" in low and ("exceed" in low or "truncat" in low or "abort" in low):
            flag = "  !! answer mentions a line limit - check for truncation"
        print(f"{tag}: {len(body):>9d} B html, {nlines:>7d} non-empty text lines{flag}")


if __name__ == "__main__":
    main()
