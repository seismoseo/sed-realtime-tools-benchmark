# 02_try_ldeo_dd_sites.py -- (2025-26 case) what LDEO offers for the period 2025-10-01..2026-10-18.
# Copied from the 2015 tool and adapted. In 2015 the LDEO base catalog NCAeqDD.v202112.1 (1984-2021)
# was the primary DD reference; it ends in 2021, so it holds none of the 2025-26 events. This tool
#   1. copies the CA bundle built by the 2015 run (certifi + the intermediate "InCommon Intermediate
#      CA - OVG2C" that nocaldd.ldeo.columbia.edu does not send; data/sanramon_2015/reference/ldeo/tls)
#      -- TLS verification stays ON;
#   2. fetches, with that bundle: the DD-RT front page https://nocaldd.ldeo.columbia.edu/ (as of today),
#      the base-catalog directory /catalog/ (is v202112.1 still the newest base catalog?), and the
#      file linked on the front page as "DD real-time catalog, Jan 2022 - present":
#      /catalog/NCAeqDDRT.v202201 (LDEO's own DD-RT solutions relative to the 1984-2021 base catalog,
#      geoid depths). It is kept as a SUPPLEMENTARY reference; the designated reference of this
#      benchmark is the NCEDC DD catalog (tool 03).
# Output: reference/ldeo/<name>, reference/ldeo/tls/*, reference/ldeo/probe_report.txt
# Re-run safe (files on disk are not fetched again). Every request -> logs/sanramon2026_requests.tsv.
# Usage: python -I 02_try_ldeo_dd_sites.py [--only] [--cafile PEM] [URL NAME ...]
#   extra URL/NAME pairs are fetched too (with --only: just those), using --cafile if given.

import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "02_try_ldeo_dd_sites"
OUT = os.path.join(C.REF, "ldeo")
TLS = os.path.join(OUT, "tls")
BUNDLE = os.path.join(TLS, "ca_bundle_certifi_plus_incommon_ovg2c.pem")
UA = {"User-Agent": "Mozilla/5.0"}

TLS2015 = os.path.join(C.SR2015, "reference", "ldeo", "tls")
LDEO = [     # with the CA bundle
    ("https://nocaldd.ldeo.columbia.edu/", "nocaldd_https_root_verified_20261018.html"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/", "nocaldd_catalog_dir_20261018.html"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/NCAeqDDRT.v202201", "NCAeqDDRT.v202201"),
]


def fetch(url, name, rep, verify=True, folder=OUT):
    path = os.path.join(folder, name)
    if os.path.exists(path) or os.path.exists(path + ".failed"):
        rep.append(f"skip (on disk{', failed before' if os.path.exists(path + '.failed') else ''}) {name}")
        return
    r = C.polite_request(url, TOOL, out_file=path, timeout=600, headers=UA,
                         ok_status=(200, 201, 202, 203), verify=verify)
    if r is None:
        rep.append(f"ERR  {url}  (no response; reason in logs/sanramon2026_requests.tsv)")
        with open(path + ".failed", "w") as f:
            f.write(f"{url}: no response (TLS or DNS error), see logs/sanramon2026_requests.tsv\n")
        return
    body = r.text if r.content and "html" in r.headers.get("content-type", "") else ""
    links = re.findall(r'href=["\']?([^"\' >]+)', body, flags=re.I)
    rep.append(f"{r.status_code} {len(r.content):>9d} B  {url} -> {r.url}  links={len(links)}")
    for lk in links[:40]:
        rep.append(f"      link: {lk}")


def copy_bundle(rep):
    """the 2015 run built the bundle from the certificates' AIA URLs; copy it (no new requests)"""
    os.makedirs(TLS, exist_ok=True)
    for fn in sorted(os.listdir(TLS2015)):
        dst = os.path.join(TLS, fn)
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(TLS2015, fn), dst)
            rep.append(f"copied {os.path.join(TLS2015, fn)} -> {dst}")


def main():
    a = sys.argv[1:]
    verify = True
    only = "--only" in a
    if only:
        a.remove("--only")
    if "--cafile" in a:
        i = a.index("--cafile")
        verify = a[i + 1]
        del a[i:i + 2]
    extra = [(a[i], a[i + 1]) for i in range(0, len(a) - 1, 2)]
    os.makedirs(OUT, exist_ok=True)
    rep = []
    if not only:
        copy_bundle(rep)
        for url, name in LDEO:
            fetch(url, name, rep, verify=BUNDLE)
    for url, name in extra:
        fetch(url, name, rep, verify=verify)
    txt = "\n".join(rep)
    print(txt)
    with open(os.path.join(OUT, "probe_report.txt"), "a") as f:
        f.write(txt + "\n")


if __name__ == "__main__":
    main()
