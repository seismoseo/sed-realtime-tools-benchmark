# sr_common.py -- shared helpers for the San Ramon 2015 benchmark tools (data/sanramon_2015/tools/).
#
# What is in here
#   * project paths (one place)
#   * polite_request(): one HTTP request with retries + exponential back-off; every attempt is
#     appended to logs/sanramon_requests.tsv (UTC time, tool, method, URL, form fields, HTTP status,
#     bytes, seconds, output file, note). Requests are made one at a time (never in parallel) and at
#     least MIN_GAP_S apart, so we stay far below the "at most 2 concurrent requests" rule.
#   * strip_html_pre(): NCEDC catalog-search2.pl wraps its text output in HTML; this returns the
#     text inside the <pre> block(s).
#
# The tools import this file with an explicit sys.path entry (they are run with "python -I", which
# drops the script directory from sys.path on purpose).

import datetime as _dt
import html as _html
import os
import re
import time

import requests

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
SR = os.path.join(PROJECT, "data", "sanramon_2015")
REF = os.path.join(SR, "reference")
INP = os.path.join(SR, "inputs")
TOOLS = os.path.join(SR, "tools")
TAB = os.path.join(SR, "reference_tables")
DOCS = os.path.join(PROJECT, "docs")
LOGS = os.path.join(PROJECT, "logs")
REQ_LOG = os.path.join(LOGS, "sanramon_requests.tsv")

USER_AGENT = "SanRamon2015-rtDD-benchmark (python-requests; research use, slow sequential requests)"
MIN_GAP_S = 1.0          # minimum pause between two requests
MAX_TRIES = 5            # attempts per request
BACKOFF_S = 4.0          # wait 4, 8, 16, 32 s between attempts
_last_request_end = [0.0]


def _log(row):
    os.makedirs(LOGS, exist_ok=True)
    new = not os.path.exists(REQ_LOG)
    with open(REQ_LOG, "a") as f:
        if new:
            f.write("utc_time\ttool\tmethod\turl\tform_or_params\tstatus\tbytes\tseconds\tout_file\tattempt\tnote\n")
        f.write("\t".join(str(x).replace("\t", " ").replace("\n", " ") for x in row) + "\n")


def polite_request(url, tool, method="GET", data=None, params=None, out_file=None,
                   timeout=300, ok_status=(200,), headers=None, allow_redirects=True,
                   verify=True):
    """Do one HTTP request with retries. Returns the requests.Response of the last attempt
    (status may be != 200, e.g. 204 'no data' from FDSN services), or None if no response.
    Writes body to out_file when status is in ok_status. 'verify' is passed to requests
    (True, or the path of a CA bundle); TLS verification is never switched off."""
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    form = data if data is not None else params
    form_s = "&".join(f"{k}={v}" for k, v in form.items()) if isinstance(form, dict) else (
        "" if form is None else f"<{len(form)} bytes body>")
    resp = None
    for attempt in range(1, MAX_TRIES + 1):
        gap = time.time() - _last_request_end[0]
        if gap < MIN_GAP_S:
            time.sleep(MIN_GAP_S - gap)
        t0 = time.time()
        status, nbytes, note = "ERR", 0, ""
        ssl_failure = False
        try:
            resp = requests.request(method, url, data=data, params=params, headers=h,
                                    timeout=timeout, allow_redirects=allow_redirects,
                                    verify=verify)
            status, nbytes = resp.status_code, len(resp.content)
            if resp.history:
                note = "redirected:" + "->".join(str(r.status_code) for r in resp.history) + "->" + resp.url
        except requests.exceptions.SSLError as e:
            note = f"{type(e).__name__}: {e}"[:300]
            resp = None
            ssl_failure = True  # a certificate problem does not go away by retrying
        except requests.RequestException as e:
            note = f"{type(e).__name__}: {e}"[:300]
            resp = None
            if "NameResolutionError" in str(e) or "Name or service not known" in str(e):
                ssl_failure = True  # unknown host name: retrying will not help either
        dt = time.time() - t0
        _last_request_end[0] = time.time()
        wrote = ""
        if resp is not None and resp.status_code in ok_status and out_file:
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            with open(out_file, "wb") as f:
                f.write(resp.content)
            wrote = out_file
        _log([_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), tool, method,
              resp.url if resp is not None else url, form_s, status, nbytes, f"{dt:.2f}", wrote,
              attempt, note])
        # done: success, or a definite answer that retrying will not change (4xx, 204 no data)
        if resp is not None and (resp.status_code in ok_status or resp.status_code == 204
                                 or 400 <= resp.status_code < 500):
            return resp
        if ssl_failure:
            return None
        if attempt < MAX_TRIES:
            time.sleep(BACKOFF_S * 2 ** (attempt - 1))
    return resp


def strip_html_pre(text):
    """Return the content of all <pre>...</pre> blocks (HTML entities decoded), or '' if none."""
    blocks = re.findall(r"<pre[^>]*>(.*?)</pre>", text, flags=re.S | re.I)
    out = "\n".join(blocks)
    out = re.sub(r"<[^>]+>", "", out)  # remove any inline tags
    return _html.unescape(out)
