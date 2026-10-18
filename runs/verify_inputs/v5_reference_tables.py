# Independent verifier, check 5: reference_tables/*.csv versus the raw HypoDD / HYPOINVERSE outputs.
#  - hypodd_dtcc.csv vs 02.dt.cc/hypoDD.reloc (every column), final_locations.csv and bootstrap_errors.csv
#  - hypodd_dtct.csv vs 01.dt.ct/hypoDD.reloc and its bootstrap_errors.csv
#  - hypoinverse_kim1983.csv vs 1.HypoInv/kim1983/Gwangyang.sum
#  - event id mapping (rtdd_id, kma_id, hypodd_id) vs event.dat order, .pha origins and KMA ids
#  - origin_time_pha_datum = reloc time - event.dat time + .pha time; east/north/up vs own centroid
# Run: conda activate pyrtdd; python -I v5_reference_tables.py
import csv, math
from datetime import datetime, timezone, timedelta
import numpy as np
from pyproj import Geod

ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
REF=ROOT+'/reference/gwangyang_pnplus'; RT=ROOT+'/reference_tables'
G=Geod(ellps='WGS84')
def rd(p): return list(csv.DictReader(open(p,newline='')))
def utc(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
bad=[]
def chk(cond,msg):
    if not cond: bad.append(msg); print('  MISMATCH',msg)

def parse_reloc(p):
    out={}
    for line in open(p):
        t=line.split()
        if not t: continue
        hid=int(t[0])
        ot=datetime(int(t[10]),int(t[11]),int(t[12]),int(t[13]),int(t[14]),tzinfo=timezone.utc)+timedelta(milliseconds=round(float(t[15])*1000))
        out[hid]=dict(lat=float(t[1]),lon=float(t[2]),dep=float(t[3]),x=float(t[4]),y=float(t[5]),z=float(t[6]),ex=float(t[7]),ey=float(t[8]),ez=float(t[9]),ot=ot,
                      mag=float(t[16]),nccp=int(t[17]),nccs=int(t[18]),nctp=int(t[19]),ncts=int(t[20]),rcc=float(t[21]),rct=float(t[22]),cid=int(t[23]))
    return out
def parse_evdat(p):
    out={}
    for line in open(p):
        t=line.split()
        if not t: continue
        d=t[0]; hms=t[1].rjust(8,'0')
        out[int(t[-1])]=datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(hms[:2]),int(hms[2:4]),tzinfo=timezone.utc)+timedelta(milliseconds=10*int(hms[4:]))
    return out
pha={}
for line in open(REF+'/2.HypoDD/00.ph2dt/Gwangyang.pha'):
    if line.startswith('#'):
        t=line[1:].split()
        pha[int(t[13])]=datetime(*map(int,t[:5]),tzinfo=timezone.utc)+timedelta(milliseconds=10*round(float(t[5])*100))

for tag,sub,tab,fin in (('dt.cc','02.dt.cc','hypodd_dtcc.csv','final_locations.csv'),('dt.ct','01.dt.ct','hypodd_dtct.csv',None)):
    print(f'== {tab} vs {sub}/hypoDD.reloc')
    rl=parse_reloc(f'{REF}/2.HypoDD/{sub}/hypoDD.reloc'); ed=parse_evdat(f'{REF}/2.HypoDD/{sub}/event.dat')
    T=rd(f'{RT}/{tab}')
    chk(len(T)==len(rl)==11,f'{tab} row count {len(T)} vs reloc {len(rl)}')
    boot={int(r['id']):r for r in csv.reader(open(f'{REF}/2.HypoDD/{sub}/bootstrap_errors.csv')) if False} if False else None
    braw=[l for l in open(f'{REF}/2.HypoDD/{sub}/bootstrap_errors.csv') if not l.startswith('#')]
    B={int(r['id']):r for r in csv.DictReader(braw)}
    lat=np.array([rl[k]['lat'] for k in sorted(rl)]); lon=np.array([rl[k]['lon'] for k in sorted(rl)]); dep=np.array([rl[k]['dep'] for k in sorted(rl)])
    cla,clo,cde=lat.mean(),lon.mean(),dep.mean()
    print(f'  my centroid of reloc positions: {cla:.6f} {clo:.6f} {cde:.4f}')
    maxenu=0
    for r in T:
        hid=int(r['hypodd_id']); e=rl[hid]
        for col,key in (('latitude','lat'),('longitude','lon'),('depth_km','dep'),('x_m','x'),('y_m','y'),('z_m','z'),('ex_m','ex'),('ey_m','ey'),('ez_m','ez'),('nccp','nccp'),('nccs','nccs'),('nctp','nctp'),('ncts','ncts')):
            chk(abs(float(r[col])-e[key])<1e-9,f'{tab} {hid} {col} {r[col]} vs {e[key]}')
        chk(abs(float(r['rcc_s'])-e['rcc'])<1e-9 and abs(float(r['rct_s'])-e['rct'])<1e-9,f'{tab} {hid} rms')
        chk(utc(r['origin_time'])==e['ot'],f'{tab} {hid} origin_time {r["origin_time"]} vs {e["ot"]}')
        dat=e['ot']-ed[hid]+pha[hid]
        chk(utc(r['origin_time_pha_datum'])==dat,f'{tab} {hid} origin_time_pha_datum {r["origin_time_pha_datum"]} vs {dat}')
        chk(int(r['rtdd_id'])==hid-199999,f'{tab} {hid} rtdd_id')
        kt=datetime.strptime(r['kma_id'],'%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        chk(0<=(pha[hid]-kt).total_seconds()<3,f'{tab} {hid} kma_id {r["kma_id"]} vs pha origin {pha[hid]}')
        # east/north/up relative to the table's own centroid columns
        az,baz,d=G.inv(float(r['centroid_lon']),float(r['centroid_lat']),e['lon'],e['lat'])
        east=d*math.sin(math.radians(az)); north=d*math.cos(math.radians(az)); up=-(e['dep']-float(r['centroid_depth_km']))*1000
        maxenu=max(maxenu,abs(east-float(r['east_m'])),abs(north-float(r['north_m'])),abs(up-float(r['up_m'])))
        b=B[hid]
        bx,by,bz=float(r['boot_ex95_m']),float(r['boot_ey95_m']),float(r['boot_ez95_m'])
        chk(abs(bx-round(float(b['ex95']),1))<0.051 and abs(by-round(float(b['ey95']),1))<0.051 and abs(bz-round(float(b['ez95']),1))<0.051,f'{tab} {hid} bootstrap {bx},{by},{bz} vs {b["ex95"]},{b["ey95"]},{b["ez95"]}')
        chk(int(r['n_boot'])==int(b['n_boot']),f'{tab} {hid} n_boot')
    print(f'  centroid columns used: {T[0]["centroid_lat"]} {T[0]["centroid_lon"]} {T[0]["centroid_depth_km"]}; max |east/north/up - mine| = {maxenu:.2f} m')
    if fin:
        F={r['event_id']:r for r in rd(f'{REF}/2.HypoDD/{sub}/{fin}')}
        for r in T:
            f=F[r['kma_id']]
            chk(abs(float(f['latitude'])-float(r['latitude']))<6e-6 and abs(float(f['longitude'])-float(r['longitude']))<6e-6 and abs(float(f['depth_km'])-float(r['depth_km']))<1e-9,f'final_locations position {r["kma_id"]}')
            chk(all(abs(float(f[a])-float(r[b]))<1e-9 for a,b in (('ex95_m','boot_ex95_m'),('ey95_m','boot_ey95_m'),('ez95_m','boot_ez95_m'))),f'final_locations errors {r["kma_id"]}')
            chk(f['cc_links']==r['cc_links'] and f['ct_links']==r['ct_links'] and f['under_constrained']==r['under_constrained'],f'final_locations links {r["kma_id"]}')
            chk(f['origin_time'][:19].replace(' ','T')==r['origin_time'][:19],f'final_locations origin {r["kma_id"]} {f["origin_time"]} vs {r["origin_time"]}')
            chk(abs(float(f['magnitude'])-float(r['kma_ml']))<1e-9,f'final_locations magnitude {r["kma_id"]}')
        # final_locations.csv order == hypoDD.reloc order == event.dat order?
        order_f=[r['event_id'] for r in rd(f'{REF}/2.HypoDD/{sub}/{fin}')]
        order_t=[r['kma_id'] for r in sorted(T,key=lambda r:int(r['hypodd_id']))]
        print('  final_locations.csv KMA-id order equals hypodd-id order of the table:',order_f==order_t)
        dl=max(abs(float(F[r['kma_id']]['latitude'])-float(r['latitude'])) for r in T); dlo=max(abs(float(F[r['kma_id']]['longitude'])-float(r['longitude'])) for r in T)
        print(f'  final_locations vs table: max |dlat| {dl:.1e} deg, |dlon| {dlo:.1e} deg (final_locations rounds to 5 decimals)')

print('== hypoinverse_kim1983.csv vs Gwangyang.sum')
H=rd(RT+'/hypoinverse_kim1983.csv')
S={}
for i,line in enumerate(open(REF+'/1.HypoInv/kim1983/Gwangyang.sum')):
    if i==0: continue
    t=[x.strip() for x in line.split(',')]
    S[int(t[15])]=t
for r in H:
    t=S[int(r['hypodd_id'])]
    ot=datetime.strptime(t[0],'%Y/%m/%d %H:%M').replace(tzinfo=timezone.utc)+timedelta(milliseconds=round(float(t[1])*1000))
    chk(utc(r['origin_time'])==ot,f'hypoinverse origin {r["hypodd_id"]}')
    for col,i in (('latitude',2),('longitude',3),('depth_km',4),('n_phases',8),('gap_deg',9),('dmin_km',10),('rms_s',11),('erh_km',12),('erz_km',13)):
        chk(abs(float(r[col])-float(t[i]))<1e-9,f'hypoinverse {r["hypodd_id"]} {col} {r[col]} vs {t[i]}')
    chk(r['quality']==t[14].strip()[:1],f'hypoinverse quality {r["hypodd_id"]}')
print(f'  rows {len(H)}, sum lines {len(S)}')

print('== event_id_map.csv (reference_tables) == inputs/rtdd_catalog/event_id_map.csv:',open(RT+'/event_id_map.csv').read()==open(ROOT+'/inputs/rtdd_catalog/event_id_map.csv').read())
print('\nMISMATCHES:',len(bad))
