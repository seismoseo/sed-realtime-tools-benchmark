# make two redirected copies of the builder (all outputs into my scratch); variant 'nodl' points DL_PICKS to a missing file
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
V = f"{P}/runs/verify_sp_offset/rerun"
src = open(f"{P}/notebooks/build_05_gwangyang_sp_offset.py").read()
for tag, dl in (("full", None), ("nodl", f"{V}/nodl/does_not_exist_dl_picks_all.csv")):
    s = src
    reps = [
        ('OUT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks/05_gwangyang_sp_offset.ipynb"', f'OUT = "{V}/{tag}/05_rerun_{tag}.ipynb"'),
        ('WORK = f"{PROJECT}/runs/gwangyang/sp_offset"', f'WORK = "{V}/{tag}/work"'),
        ('FIG_DIR = f"{PROJECT}/notebooks/figures"', f'FIG_DIR = "{V}/{tag}/figures"'),
        ('HAND_PICKS_UTC = f"{DATA}/reference_tables/picks_manual_utc.csv"', f'HAND_PICKS_UTC = "{V}/{tag}/picks_manual_utc.csv"'),
    ]
    if dl:
        reps.append(('DL_PICKS = f"{PROJECT}/runs/gwangyang/dlpicker/analysis/dl_picks_all.csv"', f'DL_PICKS = "{dl}"'))
    for a, b in reps:
        assert s.count(a) == 1, (tag, a, s.count(a))
        s = s.replace(a, b)
    open(f"{V}/build_{tag}.py", "w").write(s)
    print("wrote", f"{V}/build_{tag}.py")
