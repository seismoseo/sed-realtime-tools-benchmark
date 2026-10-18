# Independent verifier, check 4 (part b): context for the pick residuals.
#  - HYPOINVERSE's own per-phase residuals from Gwangyang.arc (Y2000 archive columns, my own parser)
#  - robust Wadati Vp/Vs (S-P vs P with per-event intercepts, iterative 3*MAD trimming)
#  - take-off dips from pyrtdd.computeAll vs my 1-D ray at the 6 test stations (centroid source)
# Run: conda activate pyrtdd; python -I v3b_residuals.py
import csv, math
from datetime import datetime, timezone
import numpy as np
from pyproj import Geod
import pyrtdd.hdd as h

ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
REF=ROOT+'/reference/gwangyang_pnplus'
CAT=ROOT+'/inputs/rtdd_catalog'
G=Geod(ellps='WGS84')
def rd(p): return list(csv.DictReader(open(p,newline='')))
def utc(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

# HYPOINVERSE Y2000 phase lines: P residual cols 35-38 (F4.2), S seconds 42-46, S remark 47-48, S residual 51-54 (F4.2), distance 75-78 (F4.1)
P=[];S=[];Pd=[];Sd=[]
for line in open(REF+'/1.HypoInv/kim1983/Gwangyang.arc'):
    if len(line)<80 or line[0:2].isdigit() or line.startswith(' ') : continue
    rem=line[13:15]; srem=line[46:48]
    dist=int(line[74:78])/10.0 if line[74:78].strip() else np.nan
    if rem.strip().endswith('P'): P.append(int(line[34:38])/100.0); Pd.append(dist)
    if srem.strip().endswith('S'): S.append(int(line[50:54])/100.0); Sd.append(dist)
P=np.array(P);S=np.array(S);Pd=np.array(Pd);Sd=np.array(Sd)
for nm,r,d in (('P',P,Pd),('S',S,Sd)):
    q=np.percentile(r,[25,50,75])
    bins=[(0,30),(30,60),(60,80),(80,110)]
    bs=' '.join(f'{a}-{b}km:{np.median(r[(d>=a)&(d<b)]):+.2f}' for a,b in bins)
    print(f'HYPOINVERSE .arc residuals {nm}: N={len(r)} median {q[1]:+.3f} s IQR [{q[0]:+.2f},{q[2]:+.2f}]  {bs}')

# robust Wadati
ph=rd(CAT+'/phase.csv'); ev={int(r['id']):utc(r['isotime']) for r in rd(CAT+'/event.csv')}
pairs={}
for r in ph: pairs.setdefault((int(r['eventId']),r['stationCode']),{})[r['type']]=utc(r['isotime'])
x=[];y=[];e=[]
for (k,sc),v in pairs.items():
    if 'P' in v and 'S' in v:
        x.append((v['P']-ev[k]).total_seconds()); y.append((v['S']-v['P']).total_seconds()); e.append(k)
x=np.array(x);y=np.array(y);e=np.array(e)
A=np.zeros((len(x),12)); A[:,0]=x
for i,k in enumerate(e): A[i,k]=1
keep=np.ones(len(x),bool)
for it in range(10):
    sol,*_=np.linalg.lstsq(A[keep],y[keep],rcond=None)
    res=y-A@sol; mad=1.4826*np.median(np.abs(res[keep]-np.median(res[keep])))
    new=np.abs(res)<3*mad
    if (new==keep).all(): break
    keep=new
print(f'Wadati: {len(x)} P+S pairs; robust Vp/Vs = {1+sol[0]:.4f} using {keep.sum()} pairs (dropped {(~keep).sum()}; MAD*1.4826 = {mad:.3f} s)')
print('  per-event Wadati intercepts (S-P at catalog-origin P travel time 0), s:',' '.join(f'{c:+.3f}' for c in sol[1:]))
# fixed slope 0.73 (model Vp/Vs 1.73): S-P residual = (S-P) - 0.73*(P travel time)
rr=y-0.73*x
print(f'  S-P minus 0.73*tP (model Vp/Vs 1.73, catalog origins): median {np.median(rr[keep]):+.3f} s; by tP bins:',' '.join(f'{a}-{b}s:{np.median(rr[keep&(x>=a)&(x<b)]):+.3f}' for a,b in ((0,5),(5,10),(10,14),(14,20))))
ratio=[]
for (k,sc),v in pairs.items():
    if 'P' in v and 'S' in v: ratio.append((v['S']-ev[k]).total_seconds()/(v['P']-ev[k]).total_seconds())
print(f'median tS/tP with catalog (.pha) origins: {np.median(ratio):.4f} over {len(ratio)} pairs')

# take-off dips: pyrtdd computeAll vs my 1-D at the centroid
ttt=h.NLLGrid(gridPath=ROOT+'/inputs/nll_kim1983/time',gridModel='kim1983')
sta={r['stationCode']:r for r in rd(CAT+'/station.csv')}
C=(34.999695,127.728889,13.942727)
v1,v2=5.98,6.38
for code in ['GWYB','BAU','JLSA','YKDB','TOY2','SUCA','KCH2','DUSB']:
    s=sta[code]; la,lo,el=float(s['latitude']),float(s['longitude']),float(s['elevation'])
    X=G.inv(C[1],C[0],lo,la)[2]/1000; zr=-el/1000
    td=math.hypot(X,C[2]-zr)/v1; dip_d=180-math.degrees(math.atan2(X,C[2]-zr))
    th=X/v2+((15-C[2])+(15-zr))*math.sqrt(1/v1**2-1/v2**2); dip_h=math.degrees(math.asin(v1/v2))
    xcrit=((15-C[2])+(15-zr))*math.tan(math.asin(v1/v2))
    if X<xcrit: th=float('inf')
    first='direct' if td<=th else 'head'
    tt,az,dip,dtdd,dtdh=ttt.computeAll(C[0],C[1],C[2],la,lo,el,'P')
    ttS,azS,dipS,_,_=ttt.computeAll(C[0],C[1],C[2],la,lo,el,'S')
    print(f'      S grid dip {dipS:7.2f}')
    print(f'{code:5s} X={X:6.2f} km first={first:6s} 1-D dip={dip_d if first=="direct" else dip_h:7.2f} (direct {dip_d:6.2f}, head {dip_h:5.2f})  pyrtdd dip={dip:7.2f}  t_direct-t_head={1000*(td-th):+8.1f} ms')
# crossover distance for the centroid source, receiver at sea level and at 0.7 km elevation
from scipy.optimize import brentq
for zr in (0.0,-0.3,-0.7):
    f=lambda X: math.hypot(X,C[2]-zr)/v1-(X/v2+((15-C[2])+(15-zr))*math.sqrt(1/v1**2-1/v2**2))
    xc=((15-C[2])+(15-zr))*math.tan(math.asin(v1/v2))
    print(f'P crossover distance, source {C[2]:.3f} km, receiver depth {zr:+.1f} km: {brentq(f,xc+1e-6,200):.2f} km (critical distance {xc:.2f} km)')
