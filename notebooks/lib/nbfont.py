"""Helvetica for publication-ready matplotlib figures.

Why this module exists. The notebooks previously carried an inline loader pointing at
`/home/msseo/Download/Helvetica` (singular) -- a path that does not exist, so the
`os.path.isdir` guard silently failed and every figure rendered in DejaVu Sans.

The real download is `/home/msseo/Downloads/Helvetica/helvetica.ttf` and it contains
only a REGULAR face. matplotlib does not synthesise bold or italic, so bold titles fell
back silently too. `build_helvetica_family()` therefore assembles a complete four-weight
family once, into a private font directory:

    regular      <- the user's helvetica.ttf
    bold/italic  <- URW NimbusSans (the metric-compatible Helvetica clone shipped with
                    the system), rewritten with family='Helvetica' and correct OS/2
                    weight and fsSelection bits so matplotlib can tell the faces apart

Nothing system-wide is modified. `use_helvetica()` registers the family and sets
rcParams, including a custom mathtext fontset so `$\\Delta\\sigma$`-style labels match
the surrounding text instead of reverting to DejaVu.
"""
import os
import pathlib

from matplotlib import font_manager as fm
import matplotlib.pyplot as plt

FONT_DIR = pathlib.Path.home() / ".local/share/fonts/helvetica-family"
USER_HELVETICA = pathlib.Path.home() / "Downloads/Helvetica/helvetica.ttf"
NIMBUS = "/usr/share/fonts/urw-base35/NimbusSans-{}.otf"

# The regular face comes from NimbusSans, not the user's helvetica.ttf: that file
# carries only 266 glyphs and NO Greek, so tau/sigma/Delta/lambda/mu rendered as
# missing-glyph boxes in axis labels. NimbusSans is URW's metric-compatible Helvetica
# clone (888 glyphs, letterforms visually indistinguishable -- verified side by side),
# so using it throughout keeps one consistent face across all four weights AND makes
# the maths render. USER_HELVETICA is kept as the fallback if NimbusSans is absent.
_REGULAR_SRC = (NIMBUS.format("Regular") if os.path.exists(NIMBUS.format("Regular"))
                else str(USER_HELVETICA))
SRC_REGULAR = pathlib.Path(_REGULAR_SRC)

# (source, output name, subfamily, usWeightClass, bold, italic)
_FACES = [
    (_REGULAR_SRC, "Helvetica-Regular.otf", "Regular", 400, False, False),
    (NIMBUS.format("Bold"), "Helvetica-Bold.otf", "Bold", 700, True, False),
    (NIMBUS.format("Italic"), "Helvetica-Italic.otf", "Italic", 400, False, True),
    (NIMBUS.format("BoldItalic"), "Helvetica-BoldItalic.otf", "Bold Italic", 700,
     True, True),
]


def _set_name(font, name_id, value):
    for rec in font["name"].names:
        if rec.nameID == name_id:
            rec.string = (value.encode("utf-16-be") if rec.platformID == 3
                          else value.encode("latin-1"))


def build_helvetica_family(force=False):
    "Assemble the 4-weight family in FONT_DIR. Idempotent; returns True if usable."
    have = [FONT_DIR / f[1] for f in _FACES]
    if not force and all(p.exists() for p in have):
        return True
    if not SRC_REGULAR.exists():
        return False
    from fontTools.ttLib import TTFont
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for src, outname, sub, wght, is_bold, is_ital in _FACES:
        if not os.path.exists(src):
            continue
        f = TTFont(src)
        full = "Helvetica" if sub == "Regular" else f"Helvetica {sub}"
        ps = "Helvetica" if sub == "Regular" else "Helvetica-" + sub.replace(" ", "")
        _set_name(f, 1, "Helvetica")
        _set_name(f, 2, sub)
        _set_name(f, 4, full)
        _set_name(f, 6, ps)
        _set_name(f, 16, "Helvetica")
        _set_name(f, 17, sub)
        os2 = f["OS/2"]
        os2.usWeightClass = wght
        fs = os2.fsSelection & ~(1 | (1 << 5) | (1 << 6))
        if is_ital:
            fs |= 1
        if is_bold:
            fs |= (1 << 5)
        if not is_bold and not is_ital:
            fs |= (1 << 6)
        os2.fsSelection = fs
        ms = f["head"].macStyle & ~3
        if is_bold:
            ms |= 1
        if is_ital:
            ms |= 2
        f["head"].macStyle = ms
        f.save(FONT_DIR / outname)
    return (FONT_DIR / _FACES[0][1]).exists()


def use_helvetica(verbose=False):
    """Register Helvetica and set rcParams. Falls back to DejaVu without raising.

    Returns the resolved font family name actually in use.
    """
    ok = build_helvetica_family()
    if ok:
        for f in fm.findSystemFonts([str(FONT_DIR)]):
            fm.fontManager.addfont(f)
    have = {e.name for e in fm.fontManager.ttflist}
    fam = ["Helvetica", "Nimbus Sans", "DejaVu Sans"]
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": fam,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Helvetica",
        "mathtext.it": "Helvetica:italic",
        "mathtext.bf": "Helvetica:bold",
        "mathtext.sf": "Helvetica",
        "mathtext.default": "regular",
        "axes.unicode_minus": False,
        "legend.framealpha": 1.0,
        "legend.facecolor": "white",
        "pdf.fonttype": 42,          # embed TrueType so vector output stays editable
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })
    resolved = "Helvetica" if "Helvetica" in have else (
        "Nimbus Sans" if "Nimbus Sans" in have else "DejaVu Sans")
    if verbose:
        n = len([e for e in fm.fontManager.ttflist if e.name == "Helvetica"])
        print(f"font family in use: {resolved} ({n} faces registered)")
    return resolved
