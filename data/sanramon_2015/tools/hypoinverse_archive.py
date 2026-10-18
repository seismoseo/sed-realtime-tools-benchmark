# hypoinverse_archive.py -- reader for Hypoinverse-2000 "Y2000" archive files (summary line +
# station/phase lines + terminator line per event), as served by NCEDC with format=ncphraw, and
# for single Y2000 summary lines (format=ddraw / ncraw).
#
# Column positions (1-based, inclusive) follow the "Y2000 hypoinverse summary format" and the
# "Y2000 (station) archive format" tables of
#   Klein (2002) USGS OFR 02-171, https://pubs.usgs.gov/of/2002/0171/  (station cols 1-113)
#   Klein, Hypoinverse manual v1.40 (2014), hyp1.40.pdf, pp. 111-115    (adds station cols 114-120)
#   NCEDC shadow2000.pdf (Klein, rev. 2006), "STATION ARCHIVE FORMAT Y2000"
# All three agree for the columns used here. Fortran Fw.d fields are written without a decimal
# point: '3901' in an F5.2 field means 39.01 (a '.' in the field, if present, wins).
# Python slices below are [start-1:end] of the 1-based columns given in the comments.

import datetime as dt


def ff(s, ndec):
    """Fortran Fw.d field -> float (None if blank)."""
    s = s.strip()
    if not s:
        return None
    if "." in s:
        return float(s)
    return int(s) / 10 ** ndec


def fi(s):
    s = s.strip()
    return int(s) if s else None


def parse_summary(line):
    """Y2000 summary (header) line -> dict. Columns per OFR 02-171 / hyp1.40 p.111."""
    L = line.rstrip("\n").ljust(179)
    lat = fi(L[16:18]) + ff(L[19:23], 2) / 60.0          # 17-18 deg, 20-23 min (F4.2)
    if L[18] == "S":                                      # 19 'S' for south
        lat = -lat
    lon = fi(L[23:26]) + ff(L[27:31], 2) / 60.0          # 24-26 deg, 28-31 min (F4.2)
    if L[26] != "E":                                      # 27 'E' for east, blank = west
        lon = -lon
    t = dt.datetime(int(L[0:4]), int(L[4:6]), int(L[6:8]), int(L[8:10]), int(L[10:12]))
    t = t + dt.timedelta(seconds=ff(L[12:16], 2))         # 13-16 origin seconds (F4.2)
    d = dict(
        origin_time=t, latitude=lat, longitude=lon,
        depth_km=ff(L[31:36], 2),                         # 32-36 reported depth (F5.2)
        amp_mag=ff(L[36:39], 2),                          # 37-39
        n_ps_wt01=fi(L[39:42]),                           # 40-42 P&S times with weight > 0.1
        gap_deg=fi(L[42:45]),                             # 43-45
        dmin_km=ff(L[45:48], 0),                          # 46-48
        rms_s=ff(L[48:52], 2),                            # 49-52
        err1_az=fi(L[52:55]), err1_dip=fi(L[55:57]), err1_km=ff(L[57:61], 2),   # 53-61
        err2_az=fi(L[61:64]), err2_dip=fi(L[64:66]), err2_km=ff(L[66:70], 2),   # 62-70
        coda_mag=ff(L[70:73], 2),                         # 71-73
        region=L[73:76].strip(),                          # 74-76
        err3_km=ff(L[76:80], 2),                          # 77-80
        remark_analyst=L[80].strip(), remark_program=L[81].strip(),   # 81, 82
        n_s_wt01=fi(L[82:85]),                            # 83-85
        erh_km=ff(L[85:89], 2), erz_km=ff(L[89:93], 2),   # 86-89, 90-93
        n_first_motions=fi(L[93:96]),                     # 94-96
        crust_model=L[110:113].strip(),                   # 111-113 3-letter crust/delay model
        authority=L[113].strip(),                         # 114
        n_valid_ps=fi(L[118:121]),                        # 119-121 readings with assigned weight > 0
        event_id=fi(L[136:146]),                          # 137-146 (I10)
        pref_mag_type=L[146].strip(),                     # 147
        pref_mag=ff(L[147:150], 2),                       # 148-150
        version=L[162].strip(), review_version=L[163].strip(),   # 163, 164
        domain=L[164:166].strip(), proc_version=L[166:168].strip(),   # 165-166, 167-168
        depth_type=L[168].strip(),                        # 169 M model depth, G geoid depth
        crust_type=L[169].strip(),                        # 170 T = CRT gradient model
        depth_datum_m=fi(L[170:174]),                     # 171-174 datum (m above geoid)
        geoid_depth_km=ff(L[174:179], 2),                 # 175-179
    )
    return d


def parse_phase(line, base_event_id=None):
    """Y2000 station archive line -> dict (raw fields; picks are built by phase_picks())."""
    L = line.rstrip("\n").ljust(120)
    base = L[17:29]                                       # 18-29 yyyymmddhhmm
    d = dict(
        station=L[0:5].strip(),                           # 1-5
        network=L[5:7].strip(),                           # 6-7
        comp1=L[8].strip(),                               # 9 one-letter component
        channel=L[9:12].strip(),                          # 10-12 3-letter (SEED) component
        p_remark=L[13:15].strip(),                        # 14-15 e.g. IP, EP
        p_first_motion=L[15].strip(),                     # 16
        p_weight_code=fi(L[16]),                          # 17
        base_minute=base,
        p_sec=ff(L[29:34], 2),                            # 30-34 F5.2
        p_residual=ff(L[34:38], 2),                       # 35-38 F4.2
        p_weight_used=ff(L[38:41], 2),                    # 39-41 F3.2
        s_sec=ff(L[41:46], 2),                            # 42-46 F5.2
        s_remark=L[46:48].strip(),                        # 47-48 e.g. ES, IS
        s_weight_code=fi(L[49]),                          # 50
        s_residual=ff(L[50:54], 2),                       # 51-54 F4.2
        amplitude=ff(L[54:61], 2),                        # 55-61 F7.2
        amp_units=fi(L[61:63]),                           # 62-63
        s_weight_used=ff(L[63:66], 2),                    # 64-66 F3.2
        p_delay=ff(L[66:70], 2), s_delay=ff(L[70:74], 2),  # 67-70, 71-74
        epi_dist_km=ff(L[74:78], 1),                      # 75-78 F4.1
        takeoff_deg=ff(L[78:81], 0),                      # 79-81 emergence angle at source
        coda_dur_s=ff(L[87:91], 0),                       # 88-91
        azimuth_deg=ff(L[91:94], 0),                      # 92-94
        data_source=L[108].strip(),                       # 109
        location_raw=L[111:113],                          # 112-113 (NCSN writes '--' for blank)
        alt_component=L[115:118].strip(),                 # 116-118
    )
    loc = d["location_raw"].strip()
    d["location"] = "" if loc in ("", "--") else loc
    d["has_p_field"] = L[29:34].strip() != ""
    d["has_s_field"] = L[41:46].strip() != ""
    return d


def minute_base(s):
    return dt.datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), int(s[10:12]))


def phase_picks(ph):
    """Split one station line into 0, 1 or 2 picks (P from cols 14-41, S from cols 42-66)."""
    out = []
    if not ph["base_minute"].strip():
        return out
    b = minute_base(ph["base_minute"])
    if ph["has_p_field"]:
        out.append(dict(phase="P", time=b + dt.timedelta(seconds=ph["p_sec"]),
                        onset=ph["p_remark"][:1], remark=ph["p_remark"],
                        first_motion=ph["p_first_motion"], weight_code=ph["p_weight_code"],
                        residual=ph["p_residual"], weight_used=ph["p_weight_used"]))
    if ph["has_s_field"]:
        out.append(dict(phase="S", time=b + dt.timedelta(seconds=ph["s_sec"]),
                        onset=ph["s_remark"][:1], remark=ph["s_remark"], first_motion="",
                        weight_code=ph["s_weight_code"], residual=ph["s_residual"],
                        weight_used=ph["s_weight_used"]))
    return out


def read_archive(text):
    """Split an archive text into events: list of (summary_dict, [phase_dicts], terminator_id).
    A summary line starts with a 4-digit year; a terminator has a blank station field and the
    event id in cols 63-72; everything else between them is a station line."""
    events = []
    cur = None
    for raw in text.splitlines():
        if not raw.strip() or raw.startswith("$"):
            continue
        if raw[:4].isdigit() and len(raw.rstrip()) >= 140:
            cur = [parse_summary(raw), [], None]
            events.append(cur)
            continue
        if cur is None:
            continue
        if raw[:5].strip() == "":
            cur[2] = fi(raw[62:72])                       # terminator: id in cols 63-72
            cur = None
            continue
        cur[1].append(parse_phase(raw))
    return events
