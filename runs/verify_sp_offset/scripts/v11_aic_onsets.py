# verify (independent of any pick): where does horizontal S energy start relative to the kim1983 model S time?
# AIC (Maeda 1985) onset on the 5-20 Hz causal-filtered N and E components (variance of both summed),
# window [max(P + 0.55*SPmodel, Smodel - 1.0 s), Smodel + 1.0 s], aligned on the hand P pick.
import glob, os
import numpy as np, pandas as pd
from obspy import read
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
WF = f"{P}/data/gwangyang_11ev/reference/gwangyang_pnplus/waveforms_100km"
A = pd.read_csv(f"{P}/runs/verify_sp_offset/my_sp_pairs_all.csv", dtype={"ev": str})
PK = pd.read_csv(f"{P}/runs/verify_sp_offset/my_picks_with_residuals.csv", dtype={"ev": str})
H = A[(A.src == "hand") & ~A.excl]
hp = PK[PK.src == "hand"].set_index(["ev", "sta", "phase"]).ts
def aic(x):
    n = len(x); out = np.full(n, np.inf)
    for k in range(10, n - 10):
        v1 = np.var(x[:k], axis=0).sum(); v2 = np.var(x[k:], axis=0).sum()
        out[k] = k * np.log(v1) + (n - k - 1) * np.log(v2)
    return out
rows = []
for r in H.itertuples():
    fs = sorted(glob.glob(f"{WF}/{r.ev}/{r.ev}.KS.{r.sta}.*.sac"))
    st = read(fs[0]) if False else None
    from obspy import Stream
    st = Stream()
    for f in fs:
        st += read(f)
    st.detrend("demean"); st.detrend("linear"); st.taper(0.05)
    st.filter("bandpass", freqmin=5.0, freqmax=20.0, corners=4, zerophase=False)
    n = [t for t in st if t.stats.channel[-1] == "N"]; e = [t for t in st if t.stats.channel[-1] == "E"]
    if not n or not e:
        continue
    n, e = n[0], e[0]
    tp = hp[(r.ev, r.sta, "P")]; ts_pick = hp[(r.ev, r.sta, "S")]
    s_model = tp + r.sp_mod
    w0 = max(tp + 0.55 * r.sp_mod, s_model - 1.0); w1 = s_model + 1.0
    t = n.times("timestamp")
    m = (t >= w0) & (t <= w1)
    te = e.times("timestamp"); me = (te >= w0) & (te <= w1)
    k = min(m.sum(), me.sum())
    x = np.column_stack([n.data[m][:k], e.data[me][:k]]).astype(float)
    a = aic(x)
    on = t[m][:k][int(np.argmin(a))]
    rows.append(dict(ev=r.ev, sta=r.sta, dist=r.dist, onset_minus_model=on - s_model, onset_minus_hand=on - ts_pick,
                     hand_minus_model=ts_pick - s_model, win_before=s_model - w0))
R = pd.DataFrame(rows)
R.to_csv(f"{P}/runs/verify_sp_offset/aic_onsets.csv", index=False)
print("pairs:", len(R))
print("AIC onset - model S: median %+.3f, IQR %+.3f..%+.3f" % (R.onset_minus_model.median(), R.onset_minus_model.quantile(.25), R.onset_minus_model.quantile(.75)))
print("AIC onset - hand S pick: median %+.3f, IQR %+.3f..%+.3f; |diff|<=0.05 s: %.0f%%" % (R.onset_minus_hand.median(), R.onset_minus_hand.quantile(.25), R.onset_minus_hand.quantile(.75), 100*(R.onset_minus_hand.abs()<=0.05).mean()))
print("hand S - model S (same pairs): median %+.3f" % R.hand_minus_model.median())
print("fraction of AIC onsets before the model S time: %.0f%%" % (100 * (R.onset_minus_model < 0).mean()))
for lo, hi in ((0, 30), (30, 60), (60, 70), (70, 101)):
    g = R[(R.dist >= lo) & (R.dist < hi)]
    print(f"  {lo}-{hi} km: n {len(g)}, AIC-model median {g.onset_minus_model.median():+.3f}, AIC-hand median {g.onset_minus_hand.median():+.3f}, hand-model {g.hand_minus_model.median():+.3f}")
