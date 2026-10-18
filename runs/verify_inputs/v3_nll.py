# Independent verifier, check 4: NonLinLoc kim1983 grids (step C1).
#  (a) grid header station positions vs station.csv (forward TM projection with pyproj, own code)
#  (b) travel times from pyrtdd.hdd.NLLGrid and from my own reader of the .buf files, for 6 stations
#      x 4 source points (centroid, depth +-1 km, 1 km north) + 1 extra source below 15 km,
#      versus my own exact 1-D layered first-arrival solver (direct ray with Snell shooting +
#      head waves along every interface below source and receiver), WGS-84 geodesic distance.
#  (c) all 54 stations at the centroid (P and S), and the elevation effect (receiver at sea level).
#  (d) observed-minus-predicted residuals of all 763 picks with HypoDD dt.cc and HYPOINVERSE origins,
#      plus residuals against HYPOINVERSE's own S model (3.40/3.79/4.58 km/s) and a Wadati Vp/Vs.
# Run: conda activate pyrtdd; python -I v3_nll.py
import csv, glob, math, os
from datetime import datetime, timezone, timedelta
import numpy as np
from scipy.optimize import brentq
from pyproj import Geod, Transformer
import pyrtdd.hdd as h

ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
GRID=ROOT+'/inputs/nll_kim1983/time'
CAT=ROOT+'/inputs/rtdd_catalog'
REF=ROOT+'/reference/gwangyang_pnplus'
G=Geod(ellps='WGS84')
TOPS=[15.0,32.0]                # interfaces below the (upward-extended) top layer, km
VP=[5.98,6.38,7.95]; RATIO=1.73
VS=[v/RATIO for v in VP]
VS_HYPOINV=[3.40,3.79,4.58]      # HYPOINVERSE's separate S model (Gwangyang.prt, CRUST MODEL 2)

def rd(p): return list(csv.DictReader(open(p,newline='')))
def utc(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

# ---------------- my 1-D first-arrival solver ----------------
def layer_index(z):
    i=0
    for t in TOPS:
        if z>=t: i+=1
    return i
def thick_in_layers(za,zb):
    # thickness of each layer between depths za<zb (top layer extends to -inf)
    bounds=[-1e9]+TOPS+[1e9]
    return [max(0.0,min(zb,bounds[i+1])-max(za,bounds[i])) for i in range(len(TOPS)+1)]
def direct(X,zs,zr,v):
    za,zb=min(zs,zr),max(zs,zr)
    hh=thick_in_layers(za,zb)
    used=[(hi,vi) for hi,vi in zip(hh,v) if hi>0]
    if len(used)==1:
        hi,vi=used[0]; L=math.hypot(X,hi); return L/vi, math.atan2(X,hi)   # angle from vertical
    vmax=max(vi for _,vi in used)
    def xp(p): return sum(hi*p*vi/math.sqrt(1-(p*vi)**2) for hi,vi in used)-X
    p=brentq(xp,0.0,(1-1e-15)/vmax,xtol=1e-16,rtol=1e-15,maxiter=500)
    t=sum(hi/(vi*math.sqrt(1-(p*vi)**2)) for hi,vi in used)
    vs_=v[layer_index(zs)]
    return t, math.asin(min(1.0,p*vs_))
def head_waves(X,zs,zr,v):
    out=[]
    for k,zk in enumerate(TOPS, start=1):
        if zk<=max(zs,zr): continue
        vk=v[k]
        hs=thick_in_layers(zs,zk); hr=thick_in_layers(zr,zk)
        if any(v[i]>=vk for i in range(k) if hs[i]+hr[i]>0): continue
        p=1.0/vk
        xcrit=sum((hs[i]+hr[i])*p*v[i]/math.sqrt(1-(p*v[i])**2) for i in range(k))
        if X<xcrit: continue
        t=X*p+sum((hs[i]+hr[i])*math.sqrt(1/v[i]**2-p*p) for i in range(k))
        out.append((t,k))
    return out
def first_arrival(X,zs,zr,v):
    td,ang=direct(X,zs,zr,v)
    best=(td,'direct')
    for t,k in head_waves(X,zs,zr,v):
        if t<best[0]: best=(t,f'head@{TOPS[k-1]:g}')
    return best

# self-test of the solver: brute-force Fermat minimisation for a two-layer direct ray and a head wave
from scipy.optimize import minimize_scalar
def fermat_two_layer(X,zs,zr,v1,v2,zi):
    # ray from (0,zs) in layer 2 to (X,zr) in layer 1 crossing interface zi at horizontal position a
    f=lambda a: math.hypot(a,zs-zi)/v2+math.hypot(X-a,zi-zr)/v1
    r=minimize_scalar(f,bounds=(0,X),method='bounded',options={'xatol':1e-12}); return r.fun
tst=[]
for X in (5.0,30.0,80.0):
    a=direct(X,20.0,-0.3,VP)[0]; b=fermat_two_layer(X,20.0,-0.3,VP[0],VP[1],15.0)
    tst.append(abs(a-b))
print(f'solver self-test (2-layer direct vs Fermat): max diff {max(tst)*1e6:.3f} us')
# head-wave self-test: brute force over entry/exit points for the 15 km interface
def fermat_head(X,zs,zr,v1,v2,zi):
    f=lambda ab: math.hypot(ab[0],zi-zs)/v1+abs(ab[1]-ab[0])/v2+math.hypot(X-ab[1],zi-zr)/v1
    from scipy.optimize import minimize
    r=minimize(f,[X*0.3,X*0.7],method='Nelder-Mead',options={'xatol':1e-10,'fatol':1e-12,'maxiter':20000}); return r.fun
hw=[]
for X in (70.0,90.0):
    a=[t for t,k in head_waves(X,13.94,-0.1,VP) if k==1][0]; b=fermat_head(X,13.94,-0.1,VP[0],VP[1],15.0); hw.append(abs(a-b))
print(f'solver self-test (head wave vs Fermat): max diff {max(hw)*1e6:.3f} us')

# ---------------- stations ----------------
sta={r['stationCode']:dict(lat=float(r['latitude']),lon=float(r['longitude']),elev=float(r['elevation'])) for r in rd(CAT+'/station.csv')}

# (a) header positions
print('== (a) grid header station positions vs station.csv')
tm=Transformer.from_crs('EPSG:4326','+proj=tmerc +lat_0=35 +lon_0=127.7286 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m',always_xy=True)
maxh=0; maxz=0; worst=None; nhdr=0
for f in sorted(glob.glob(GRID+'/kim1983.*.*.time.hdr'))+sorted(glob.glob(GRID+'/kim1983.*.*.angle.hdr')):
    L=open(f).read().split('\n')
    nm,x,y,z=L[1].split()[0],*map(float,L[1].split()[1:4])
    s=sta[nm]; xe,yn=tm.transform(s['lon'],s['lat'])
    dh=math.hypot(xe-x*1000,yn-y*1000); dz=abs(-s['elev']-z*1000)
    nhdr+=1
    if dh>maxh: maxh=dh; worst=(os.path.basename(f),dh)
    maxz=max(maxz,dz)
    assert 'TRANS_MERC' in L[2] and 'LatOrig 35.000000' in L[2] and 'LongOrig 127.728600' in L[2], f
print(f'  {nhdr} headers; max horizontal |header - projected station| = {maxh*1000:.3f} mm ({worst[0]}); max |z - (-elev)| = {maxz*1000:.3f} mm')
codes_grids=sorted({os.path.basename(f).split('.')[2] for f in glob.glob(GRID+'/kim1983.P.*.time.hdr')})
codes_gridsS=sorted({os.path.basename(f).split('.')[2] for f in glob.glob(GRID+'/kim1983.S.*.time.hdr')})
print(f'  stations with P grids {len(codes_grids)}, S grids {len(codes_gridsS)}, equal to station.csv set: {set(codes_grids)==set(sta)==set(codes_gridsS)}')

# own .buf reader: 2-D grid, sheet 0, layout [iy][iz], bilinear interpolation
def load_grid(ph,code,kind='time'):
    hdr=open(f'{GRID}/kim1983.{ph}.{code}.{kind}.hdr').read().split()
    nx,ny,nz=map(int,hdr[:3]); x0,y0,z0,dx,dy,dz=map(float,hdr[3:9])
    a=np.fromfile(f'{GRID}/kim1983.{ph}.{code}.{kind}.buf',dtype='<f4')
    assert a.size%(ny*nz)==0
    return dict(a=a[:ny*nz].reshape(ny,nz),y0=y0,z0=z0,dy=dy,dz=dz,ny=ny,nz=nz,nsheets=a.size//(ny*nz))
def interp(gr,dist_km,depth_km):
    fy=(dist_km-gr['y0'])/gr['dy']; fz=(depth_km-gr['z0'])/gr['dz']
    iy=int(math.floor(fy)); iz=int(math.floor(fz)); ty=fy-iy; tz=fz-iz
    a=gr['a']
    return ((1-ty)*(1-tz)*a[iy,iz]+ty*(1-tz)*a[iy+1,iz]+(1-ty)*tz*a[iy,iz+1]+ty*tz*a[iy+1,iz+1])
def tm_dist_km(code,lat,lon):
    # distance in the grid's own projected plane (what NLL interpolates on)
    s=sta[code]; xs,ys=tm.transform(s['lon'],s['lat']); xe,ye=tm.transform(lon,lat)
    return math.hypot(xe-xs,ye-ys)/1000.0

ttt=h.NLLGrid(gridPath=GRID,gridModel='kim1983')   # default maxSearchDistance 0.1 m

# (b) 6 stations x source points
print('== (b) 6 stations x source points: pyrtdd / own reader / exact 1-D (ms differences)')
C=(34.999695,127.728889,13.942727)
lat1n=G.fwd(C[1],C[0],0.0,1000.0)[1]
SRC=[('centroid',C[0],C[1],C[2]),('depth-1km',C[0],C[1],C[2]-1),('depth+1km',C[0],C[1],C[2]+1),('1km north',lat1n,C[1],C[2]),('depth 16.5 km (layer 2)',C[0],C[1],16.5)]
SIX=['GWYB','BAU','JLSA','YKDB','KCH2','DUSB']
rows=[]
for code in SIX:
    s=sta[code]
    for ph,v in (('P',VP),('S',VS)):
        gr=load_grid(ph,code)
        for name,la,lo,z in SRC:
            X=G.inv(lo,la,s['lon'],s['lat'])[2]/1000
            t1d,branch=first_arrival(X,z,-s['elev']/1000,v)
            tpy=ttt.compute(la,lo,z,s['lat'],s['lon'],s['elev'],ph)
            town=interp(gr,tm_dist_km(code,la,lo),z)
            rows.append((code,ph,name,X,t1d,branch,tpy,town))
            print(f'  {code:5s} {ph} {name:24s} X={X:7.3f} km  1D={t1d:8.4f} s ({branch:8s})  pyrtdd-1D={1000*(tpy-t1d):+7.3f}  own-1D={1000*(town-t1d):+7.3f}  pyrtdd-own={1e6*(tpy-town):+8.3f} us')
d=np.array([r[6]-r[4] for r in rows]); d2=np.array([r[6]-r[7] for r in rows])
print(f'  max |pyrtdd - 1D| over {len(rows)} cases: {np.abs(d).max()*1000:.3f} ms; max |pyrtdd - own reader| {np.abs(d2).max()*1e6:.3f} us')

# (c) all 54 stations at the centroid, and the sea-level (HypoDD-style) receiver effect
print('== (c) all stations at the centroid')
allr=[]
for code,s in sorted(sta.items()):
    X=G.inv(C[1],C[0],s['lon'],s['lat'])[2]/1000
    for ph,v in (('P',VP),('S',VS)):
        t1d,br=first_arrival(X,C[2],-s['elev']/1000,v)
        t0,_=first_arrival(X,C[2],0.0,v)
        tpy=ttt.compute(C[0],C[1],C[2],s['lat'],s['lon'],s['elev'],ph)
        allr.append((code,ph,X,t1d,tpy,t1d-t0,br))
for ph in 'PS':
    dd=np.array([r[4]-r[3] for r in allr if r[1]==ph]); el=np.array([r[5] for r in allr if r[1]==ph])
    worst=max((r for r in allr if r[1]==ph),key=lambda r:abs(r[4]-r[3]))
    print(f'  {ph}: grid-1D min {dd.min()*1000:+.3f} max {dd.max()*1000:+.3f} mean {dd.mean()*1000:+.3f} ms (worst {worst[0]} at {worst[2]:.1f} km); elevation adds {el.min()*1000:.1f}-{el.max()*1000:.1f} ms')
nh=sum(1 for r in allr if r[1]=='P' and r[6]!='direct'); print(f'  P first arrival = head wave at {nh} of 54 stations; branches: {sorted(set((r[6]) for r in allr))}')
xs=[r[2] for r in allr if r[1]=='P' and r[6]=='direct']; xh=[r[2] for r in allr if r[1]=='P' and r[6]!='direct']
print(f'  P crossover lies between {max(xs):.2f} km (last direct) and {min(xh):.2f} km (first head)')

# (d) residuals of the picks
print('== (d) observed - predicted residuals of the 763 picks')
ph_rows=rd(CAT+'/phase.csv')
dtcc={int(r['rtdd_id']):r for r in rd(ROOT+'/reference_tables/hypodd_dtcc.csv')}
# HYPOINVERSE .sum (my own parse)
hyp={}
for i,line in enumerate(open(REF+'/1.HypoInv/kim1983/Gwangyang.sum')):
    if i==0: continue
    t=[x.strip() for x in line.split(',')]
    d=datetime.strptime(t[0],'%Y/%m/%d %H:%M').replace(tzinfo=timezone.utc)+timedelta(seconds=float(t[1]))
    hyp[int(t[15])-199999]=dict(ot=d,lat=float(t[2]),lon=float(t[3]),dep=float(t[4]))
# HypoDD reloc (my own parse) with origin on the .pha datum = reloc time - event.dat time + .pha time
reloc={}
for line in open(REF+'/2.HypoDD/02.dt.cc/hypoDD.reloc'):
    t=line.split()
    if not t: continue
    eid=int(t[0])-199999
    ot=datetime(int(t[10]),int(t[11]),int(t[12]),int(t[13]),int(t[14]),tzinfo=timezone.utc)+timedelta(seconds=float(t[15]))
    reloc[eid]=dict(ot=ot,lat=float(t[1]),lon=float(t[2]),dep=float(t[3]))
evdat={}
for line in open(REF+'/2.HypoDD/02.dt.cc/event.dat'):
    t=line.split(); hms=t[1].rjust(8,'0'); d=t[0]
    evdat[int(t[-1])-199999]=datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(hms[:2]),int(hms[2:4]),tzinfo=timezone.utc)+timedelta(milliseconds=10*int(hms[4:]))
evcsv={int(r['id']):utc(r['isotime']) for r in rd(CAT+'/event.csv')}
for e in reloc: reloc[e]['ot_pha']=reloc[e]['ot']-evdat[e]+evcsv[e]
def resid(loc,key,vS_model,use_grid=True):
    out={'P':[],'S':[]}; dist={'P':[],'S':[]}
    for r in ph_rows:
        e=int(r['eventId']); L=loc[e]; s=sta[r['stationCode']]
        obs=(utc(r['isotime'])-L[key]).total_seconds()
        if use_grid:
            pred=ttt.compute(L['lat'],L['lon'],L['dep'],s['lat'],s['lon'],s['elev'],r['type'])
        else:
            X=G.inv(L['lon'],L['lat'],s['lon'],s['lat'])[2]/1000
            pred=first_arrival(X,L['dep'],0.0,VP if r['type']=='P' else vS_model)[0]   # sea-level receivers like HYPOINVERSE
        out[r['type']].append(obs-pred); dist[r['type']].append(G.inv(L['lon'],L['lat'],s['lon'],s['lat'])[2]/1000)
    return {k:np.array(v) for k,v in out.items()},{k:np.array(v) for k,v in dist.items()}
def summ(tag,res,dist):
    for ph in 'PS':
        r=res[ph]; q=np.percentile(r,[25,50,75]); dd=dist[ph]
        bins=[(0,30),(30,60),(60,80),(80,110)]
        bs=' '.join(f'{a}-{b}km:{np.median(r[(dd>=a)&(dd<b)]):+.3f}' for a,b in bins if ((dd>=a)&(dd<b)).any())
        print(f'  {tag:52s} {ph}: N={len(r)} median {q[1]:+.3f} s IQR [{q[0]:+.3f},{q[2]:+.3f}]  by distance: {bs}')
r1,d1=resid(reloc,'ot_pha',VS); summ('grid (kim1983, Vp/Vs 1.73), HypoDD dt.cc loc/origin',r1,d1)
r2,d2=resid(hyp,'ot',VS); summ('grid (kim1983, Vp/Vs 1.73), HYPOINVERSE loc/origin',r2,d2)
r3,d3=resid(hyp,'ot',VS_HYPOINV,use_grid=False); summ('1-D, HYPOINVERSE P+S models, HYPOINVERSE loc, sea level',r3,d3)
# Wadati: tS - tP vs tP per event-station pair (origin-time free slope)
pairs={}
for r in ph_rows: pairs.setdefault((r['eventId'],r['stationCode']),{})[r['type']]=utc(r['isotime'])
x=[];y=[];ev=[]
for (e,sc),v in pairs.items():
    if 'P' in v and 'S' in v:
        x.append((v['P']-evcsv[int(e)]).total_seconds()); y.append((v['S']-v['P']).total_seconds()); ev.append(int(e))
x=np.array(x); y=np.array(y); ev=np.array(ev)
# per-event intercepts (origin-time errors) + common slope: least squares with event dummies
A=np.zeros((len(x),12)); A[:,0]=x
for i,e in enumerate(ev): A[i,e]=1.0
sol,*_=np.linalg.lstsq(A,y,rcond=None)
res=y-A@sol; keep=np.abs(res)<1.0
sol2,*_=np.linalg.lstsq(A[keep],y[keep],rcond=None)
print(f'  Wadati (S-P vs P, per-event intercepts): {len(x)} pairs, Vp/Vs = {1+sol[0]:.4f} (all), {1+sol2[0]:.4f} (after dropping |res|>1 s: {(~keep).sum()} pairs)')
