# 02_try_ldeo_dd_sites.py -- reach the LDEO double-difference catalog site that NCEDC points to
# ("obtain current, geoid referenced DD solutions from https://nocaldd.ldeo.columbia.edu") and
# download the current DD base catalog for the San Ramon comparison.
#
# What happens (2026-10-17):
#   1. probes, once each, with a browser-like User-Agent: https://nocaldd.ldeo.columbia.edu (TLS
#      error: the server omits its intermediate certificate), http://nocaldd... (meta refresh to
#      https://nocal.ldeo.columbia.edu, which does not resolve), the DD-RT page and ~felixw/NCAeqDD/.
#   2. builds a CA bundle = certifi + the missing intermediate "InCommon Intermediate CA - OVG2C"
#      + its cross-signed issuer, fetched from the URLs written in the certificates themselves
#      (Authority Information Access), exactly what a browser does. Verification stays ON.
#   3. with that bundle: the site front page, /catalog/ page, README, stats.txt and the catalog
#      NCAeqDD.v202112.1.gz (1984-2021, geoid depths, 26 MB).
# Output: reference/ldeo/<name>, reference/ldeo/tls/*, reference/ldeo/probe_report.txt
# Re-run safe (files on disk are not fetched again). Every request -> logs/sanramon_requests.tsv.
# Usage: python -I 02_try_ldeo_dd_sites.py [--only] [--cafile PEM] [URL NAME ...]
#   extra URL/NAME pairs are fetched too (with --only: just those), using --cafile if given.

import os
import re
import subprocess
import sys

import certifi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "02_try_ldeo_dd_sites"
OUT = os.path.join(C.REF, "ldeo")
TLS = os.path.join(OUT, "tls")
BUNDLE = os.path.join(TLS, "ca_bundle_certifi_plus_incommon_ovg2c.pem")
UA = {"User-Agent": "Mozilla/5.0"}

PROBES = [   # step 1, default certificate store
    ("https://nocaldd.ldeo.columbia.edu", "nocaldd_https_root.html"),
    ("http://nocaldd.ldeo.columbia.edu/", "nocaldd_http_root.html"),
    ("https://nocal.ldeo.columbia.edu", "nocal_https_root.html"),
    ("http://ddrt.ldeo.columbia.edu/DDRT/index.html", "ddrt_index.html"),
    ("https://www.ldeo.columbia.edu/~felixw/NCAeqDD/", "felixw_NCAeqDD_dir.html"),
]
AIA = [      # step 2, URLs from the certificates' Authority Information Access fields
    ("http://repository.emsign.com/certs/EEEMIncommonOVG2C.crt", "EEEMIncommonOVG2C.crt"),
    ("http://repository.emsign.com/certs/EMIncommonOVG2C.p7c", "EMIncommonOVG2C.p7c"),
]
LDEO = [     # step 3, with the CA bundle
    ("https://nocaldd.ldeo.columbia.edu/", "nocaldd_https_root_verified.html"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/", "nocaldd_catalog_dir.html"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/search.html", "nocaldd_catalog_search.html"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/README", "NCAeqDD.v202112.1_README.txt"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/stats.txt", "NCAeqDD.v202112.1_stats.txt"),
    ("https://nocaldd.ldeo.columbia.edu/catalog/NCAeqDD.v202112.1.gz", "NCAeqDD.v202112.1.gz"),
]


def fetch(url, name, rep, verify=True, folder=OUT):
    path = os.path.join(folder, name)
    if os.path.exists(path) or os.path.exists(path + ".failed"):
        rep.append(f"skip (on disk{', failed before' if os.path.exists(path + '.failed') else ''}) {name}")
        return
    r = C.polite_request(url, TOOL, out_file=path, timeout=600, headers=UA,
                         ok_status=(200, 201, 202, 203), verify=verify)
    if r is None:
        rep.append(f"ERR  {url}  (no response; reason in logs/sanramon_requests.tsv)")
        with open(path + ".failed", "w") as f:
            f.write(f"{url}: no response (TLS or DNS error), see logs/sanramon_requests.tsv\n")
        return
    body = r.text if r.content and "html" in r.headers.get("content-type", "") else ""
    links = re.findall(r'href=["\']?([^"\' >]+)', body, flags=re.I)
    rep.append(f"{r.status_code} {len(r.content):>9d} B  {url} -> {r.url}  links={len(links)}")
    for lk in links[:40]:
        rep.append(f"      link: {lk}")


def build_bundle(rep):
    os.makedirs(TLS, exist_ok=True)
    for url, name in AIA:
        fetch(url, name, rep, folder=TLS)
    if not os.path.exists(BUNDLE):
        a = os.path.join(TLS, "EEEMIncommonOVG2C.pem")
        b = os.path.join(TLS, "EMIncommonOVG2C_p7c.pem")
        subprocess.run(["openssl", "x509", "-inform", "DER", "-in",
                        os.path.join(TLS, "EEEMIncommonOVG2C.crt"), "-out", a], check=True)
        subprocess.run(["openssl", "pkcs7", "-inform", "DER", "-in",
                        os.path.join(TLS, "EMIncommonOVG2C.p7c"), "-print_certs", "-out", b],
                       check=True)
        with open(BUNDLE, "w") as f:
            for p in (certifi.where(), a, b):
                f.write(open(p).read())
        rep.append(f"built {BUNDLE}")


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
        for url, name in PROBES:
            fetch(url, name, rep)
        build_bundle(rep)
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
