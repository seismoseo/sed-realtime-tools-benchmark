# 07_publish_selection.py -- list the files of this project that go into the public GitHub repository
# seismoseo/sed-realtime-tools-benchmark (decided with the user on 2026-10-18).
#
# Published: code (install/, notebooks/, run and analysis scripts), notes (README, docs/), executed notebooks with
# their figures, and small result tables (CSV/JSON/TXT/MD, at most MAX_BYTES each), incl. the derived Gwangyang tables
# (picks, hand-pick comparison, HYPOINVERSE/HypoDD tables) and the public NCEDC-derived San Ramon tables.
# Not published: raw waveforms (KMA, NCEDC), StationXML/SeisComP XML, NonLinLoc grids, databases, binary caches,
# third-party software and build trees (software/), per-iteration dumps (processing/, work/), logs, scratch homes.
# Text files are passed through the "redact" clean filter (.gitattributes), which replaces server addresses.
#
# Usage: python -I install/07_publish_selection.py [--out FILE]   (prints the list; writes it with --out)
import argparse
import os

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
MAX_BYTES = 2_000_000
EXCLUDED_DIRS = {"software", "logs", "wfcache", "sds", "playback", "processing", "work", "time", "model", "home",
                 "seiscomp_home", "seiscomp_user", "db", "output", "__pycache__", ".ipynb_checkpoints", ".git",
                 "report_build_cache", "report_build_tmp"}
EXCLUDED_DIR_PREFIXES = ("nll_",)
PUBLISHED_EXT = {".py", ".sh", ".md", ".csv", ".json", ".txt", ".cfg", ".ipynb", ".png", ".pdf", ".in", ".run",
                 ".tsv", ".yml", ".yaml"}
ALWAYS = {".gitignore", ".gitattributes"}


def selected_files():
    out = []
    for dp, dn, fn in os.walk(PROJECT):
        dn[:] = sorted(d for d in dn
                       if d not in EXCLUDED_DIRS and not d.startswith(EXCLUDED_DIR_PREFIXES) and not d.startswith("."))
        rel_dir = os.path.relpath(dp, PROJECT)
        for f in sorted(fn):
            rel = os.path.normpath(os.path.join(rel_dir, f))
            path = os.path.join(PROJECT, rel)
            if any(w in rel.lower() for w in ("server-a", "server B")):
                continue    # file names that carry a server name cannot be redacted by the text filter; not published
            if rel in ALWAYS:
                out.append(rel)
                continue
            if os.path.splitext(f)[1].lower() not in PUBLISHED_EXT or os.path.islink(path):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size <= MAX_BYTES:
                out.append(rel)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()
    files = selected_files()
    text = "\n".join(files) + "\n"
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"{len(files)} files written to {args.out}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
