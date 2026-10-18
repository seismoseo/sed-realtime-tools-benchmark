# 01_download_reference_docs.py -- download the documentation pages and papers that describe the
# NCSS routine catalog, the NCEDC double-difference (DD) catalog, the Hypoinverse archive format and
# the LDEO NCAeqDD catalog, so that every statement in docs/sanramon_inputs.md can be traced to a
# file on disk.
#
# Output: data/sanramon_2015/reference/docs/<name>   (raw bytes as served); the NCSS Hypoinverse
#         metadata zip is unpacked to reference/ncss_hypoinverse_metadata/
# Every request is logged in logs/sanramon_requests.tsv. Files already on disk are skipped
# (re-run safe). Run:  python -I 01_download_reference_docs.py [--extra URL NAME ...]

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "01_download_reference_docs"
OUT = os.path.join(C.REF, "docs")

DOCS = [
    # NCEDC catalog search form and its help page (field names, formats, notes on the DD catalog)
    ("https://ncedc.org/ncedc/catalog-search.html", "ncedc_catalog-search.html"),
    ("https://ncedc.org/ncedc/catalog-search-help.html", "ncedc_catalog-search-help.html"),
    # NCEDC: metadata for reproducing NCSS Hypoinverse locations (velocity models, station delays)
    ("https://ncedc.org/ncedc/catalog-reproducing-hypoinverse-locations.html",
     "ncedc_catalog-reproducing-hypoinverse-locations.html"),
    # NCEDC blog: DD locations now available (2014) and the 2015-10-07 depth-datum change
    ("https://ncedc.org/blog/2014/06/02/double-difference-locations-now-available.html",
     "ncedc_blog_2014-06-02_dd_locations.html"),
    ("https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html",
     "ncedc_blog_2015-10-07_depth_datum.html"),
    # Formats: Hypoinverse Y2000 archive + shadow records, readable catalog list format
    ("https://ncedc.org/pub/doc/ncsn/shadow2000.pdf", "ncedc_shadow2000.pdf"),
    ("https://ncedc.org/pub/doc/cat1/catlist.txt", "ncedc_catlist.txt"),
    # Waldhauser & Schaff (2008) and the NCAeqDD README (LDEO)
    ("http://www.ldeo.columbia.edu/~felixw/papers/Waldhauser_Schaff_JGR2008.pdf",
     "Waldhauser_Schaff_JGR2008.pdf"),
    ("https://www.ldeo.columbia.edu/~felixw/NCAeqDD/README", "NCAeqDD_README.txt"),
    # Hypoinverse-2000 manual (Klein 2002, USGS OFR 02-171) landing page
    ("https://pubs.usgs.gov/of/2002/0171/", "usgs_ofr02-171_landing.html"),
    # found on the pages above (first fetched with --extra on 2026-10-17, now part of the list)
    ("https://ncedc.org/pub/catalogs/ncsn/hypoinverse/", "ncedc_hypoinverse_dir_index.html"),
    ("https://pubs.usgs.gov/of/2002/0171/pdf/of02-171.pdf", "usgs_ofr02-171_hypoinverse2000_manual.pdf"),
    ("https://escweb.wr.usgs.gov/content/software/HYPOINVERSE/doc/hyp1.40.pdf", "hyp1.40_manual.pdf"),
    ("https://ncedc.org/pub/catalogs/ncsn/hypoinverse/hypoinv-standalone-20230210.zip",
     "hypoinv-standalone-20230210.zip"),
    ("https://ncedc.org/pub/catalogs/ncsn/hypoinverse/hypoinverse-standalone-filenames-descriptions.xlsx",
     "hypoinverse-standalone-filenames-descriptions.xlsx"),
]


def main():
    extra = sys.argv[1:]
    todo = list(DOCS)
    if extra and extra[0] == "--extra":
        pairs = extra[1:]
        todo += [(pairs[i], pairs[i + 1]) for i in range(0, len(pairs) - 1, 2)]
    os.makedirs(OUT, exist_ok=True)
    for url, name in todo:
        path = os.path.join(OUT, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"skip (on disk) {name}")
            continue
        r = C.polite_request(url, TOOL, out_file=path, timeout=120)
        st = r.status_code if r is not None else "ERR"
        n = len(r.content) if r is not None else 0
        print(f"{st} {n:>9d} B  {name}  <- {url}")
    # unpack the NCSS Hypoinverse metadata package into its own folder (plain text files)
    z = os.path.join(OUT, "hypoinv-standalone-20230210.zip")
    dest = os.path.join(C.REF, "ncss_hypoinverse_metadata")
    if os.path.exists(z) and not os.path.exists(dest):
        import zipfile
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():                       # refuse absolute or '..' member names
                assert not m.startswith("/") and ".." not in m.split("/"), m
            zf.extractall(dest)
        print(f"unpacked {z} -> {dest}")


if __name__ == "__main__":
    main()
