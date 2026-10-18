# vC1e_resid.py -- verifier scratch: independent observed-minus-grid residuals (PhaseNet+ picks - HypoDD dt.cc origin) vs kim1983 NLL grids
import glob, pandas as pd, numpy as np
from pyrtdd.hdd import NLLGrid
R='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/reference/gwangyang_pnplus'
G='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/nll_kim1983'
# hypoDD.reloc: id lat lon depth x y z ex ey ez yr mo dy hr mi sc ...
rel={}
for line in open(R+'/2.HypoDD/02.dt.cc/hypoDD.reloc'):
    f=line.split(); hid=int(f[0]); lat,lon,dep=map(float,f[1:4]); yr,mo,dy,hr,mi=map(int,f[10:15]); sc=float(f[15])
    rel[hid]=(lat,lon,dep,pd.Timestamp(year=yr,month=mo,day=dy,hour=hr,minute=mi,tz='UTC')+pd.Timedelta(seconds=sc))
# event.dat: date time(hhmmsscc) lat lon dep mag eh ez rms id -> map KMA id (YYYYMMDDhhmmss) via date+hhmmss
evd=[]
for line in open(R+'/2.HypoDD/00.ph2dt/event.dat'):
    f=line.split(); t=f[1].zfill(8); evd.append((pd.Timestamp(f[0]+'T'+t[:6],tz='UTC')+pd.Timedelta(seconds=int(t[6:])/100), int(f[-1])))
def hid_of(kma):
    k=pd.Timestamp(str(kma),tz='UTC'); dt,h=min((abs((t-k).total_seconds()),h) for t,h in evd)
    assert dt<10, (kma,dt); return h
idmap=None
st=pd.read_csv(G+'/stations_gridded.csv').set_index('Code')
ttt=NLLGrid(gridPath=G+'/time', gridModel='kim1983', maxSearchDistance=0.1)
rows=[]
for f in sorted(glob.glob(R+'/picks/*_picks.csv')):
    p=pd.read_csv(f)
    for x in p.itertuples():
        hid=hid_of(x.Event_ID); lat,lon,dep,ot=rel[hid]; s=st.loc[x.Station]
        tobs=(pd.Timestamp(x.Time)-ot).total_seconds()
        tg=ttt.compute(lat,lon,dep,s.Latitude,s.Longitude,s.Elevation_m,x.Phase)
        rows.append((x.Event_ID,x.Station,x.Phase,tobs,tg,tobs-tg))
d=pd.DataFrame(rows,columns=['ev','sta','ph','tobs','tgrid','res'])
print('picks:',len(d),d.ph.value_counts().to_dict(),'| events mapped:',d.ev.nunique())
for ph in 'PS':
    r=d[d.ph==ph].res; print(ph,'N=%d median %+.3f s IQR %+.3f..%+.3f; |res|>1 s: %d' % (len(r),r.median(),r.quantile(.25),r.quantile(.75),(r.abs()>1).sum()))
pp=d.pivot_table(index=['ev','sta'],columns='ph',values='tobs').dropna(); print('median tS/tP over %d pairs: %.4f' % (len(pp),(pp.S/pp.P).median()))
