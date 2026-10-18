# Independent verifier: per-event Wadati slopes (S-P vs absolute P pick time; no origin time used at all)
# with a 3*MAD trimmed refit, to cross-check the pooled Vp/Vs estimate.
import csv
from datetime import datetime, timezone
import numpy as np
CAT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/rtdd_catalog'
def utc(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
pairs={}
for r in csv.DictReader(open(CAT+'/phase.csv')): pairs.setdefault((int(r['eventId']),r['stationCode']),{})[r['type']]=utc(r['isotime'])
sl=[]
for e in range(1,12):
    x=[];y=[]
    for (k,sc),v in pairs.items():
        if k==e and 'P' in v and 'S' in v:
            x.append(v['P'].timestamp()); y.append((v['S']-v['P']).total_seconds())
    x=np.array(x)-min(x); y=np.array(y); keep=np.ones(len(x),bool)
    for it in range(10):
        b=np.polyfit(x[keep],y[keep],1); r=y-np.polyval(b,x); mad=1.4826*np.median(np.abs(r[keep]-np.median(r[keep])))
        new=np.abs(r)<max(3*mad,0.05)
        if (new==keep).all(): break
        keep=new
    sl.append(1+b[0]); print(f'event {e:2d}: n={len(x):2d} kept {keep.sum():2d}  Vp/Vs = {1+b[0]:.4f}  origin implied by S-P=0: t_P(first)-{b[1]/b[0]:+.3f}... ')
print(f'median per-event Vp/Vs {np.median(sl):.4f}; mean {np.mean(sl):.4f}; range {min(sl):.3f}-{max(sl):.3f}')
