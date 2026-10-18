# Independent verifier, check 1: rtDD catalog (station.csv, event.csv, phase.csv)
# Compares the step-C2 catalog against the raw reference files (.pha, event.dat,
# used_stations_100km.csv, PhaseNet+ pick files, SAC file names) with my own parsers,
# then re-loads the triplet with pyrtdd.hdd.Catalog.
# Run: conda activate pyrtdd; python -I v1_catalog.py
import csv, glob, os, random, sys
from datetime import datetime, timedelta, timezone
import numpy as np

ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
REF=ROOT+'/reference/gwangyang_pnplus'
CAT=ROOT+'/inputs/rtdd_catalog'
DOC_HEADERS={'event.csv':'id,isotime,latitude,longitude,depth,magnitude',
             'station.csv':'latitude,longitude,elevation,networkCode,stationCode,locationCode',
             'phase.csv':'eventId,isotime,lowerUncertainty,upperUncertainty,type,networkCode,stationCode,locationCode,channelCode'}

def utc(s):
    # parse 'YYYY-MM-DDTHH:MM:SS.ffffffZ' to a datetime (microsecond exact)
    return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

def read_csv(p):
    with open(p,newline='') as f:
        return list(csv.DictReader(f))

problems=[]
def bad(msg):
    problems.append(msg); print('  PROBLEM:',msg)

# ---------- headers exactly as multievent.rst ----------
print('== 1a CSV headers vs multievent.rst')
rst=open('/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/seiscomp/src/extras/scrtdd/doc/base/multievent.rst').read()
for fn,h in DOC_HEADERS.items():
    assert h in rst, 'doc header not found in rst: '+h
    got=open(CAT+'/'+fn).readline().rstrip('\r\n')
    print(f'  {fn}: header {"OK" if got==h else "MISMATCH"}  got={got!r}')
    if got!=h: bad(f'{fn} header {got!r} != {h!r}')
for fn in DOC_HEADERS:
    raw=open(CAT+'/'+fn,'rb').read()
    print(f'  {fn}: CRLF={b"\r" in raw} BOM={raw[:3]==b"\xef\xbb\xbf"} trailing_newline={raw.endswith(b"\n")}')

# ---------- parse .pha (ph2dt input) myself ----------
print('== 1b .pha parse')
phafile=REF+'/2.HypoDD/00.ph2dt/Gwangyang_mod.pha'
pha_ev={}; pha_picks=[]; cur=None
for line in open(phafile):
    if line.startswith('#'):
        t=line[1:].split()
        yr,mo,dy,hr,mi=map(int,t[:5]); sc=float(t[5])
        lat,lon,dep,mag=float(t[6]),float(t[7]),float(t[8]),float(t[9])
        evid=int(t[13])
        # origin = date + seconds as integer centiseconds to avoid float drift
        cs=int(round(sc*100))
        ot=datetime(yr,mo,dy,hr,mi,tzinfo=timezone.utc)+timedelta(milliseconds=10*cs)
        pha_ev[evid]=dict(ot=ot,lat=lat,lon=lon,dep=dep,mag=mag)
        cur=evid
    elif line.strip():
        t=line.split()
        sta=t[0]; tt=t[1]; w=float(t[2]); ph=t[3]
        ms=int(round(float(tt)*1000))
        pha_picks.append(dict(evid=cur,netsta=sta,tt_ms=ms,w=w,ph=ph))
print(f'  {len(pha_ev)} events, {len(pha_picks)} picks, P={sum(p["ph"]=="P" for p in pha_picks)} S={sum(p["ph"]=="S" for p in pha_picks)}')
import hashlib
print('  md5 Gwangyang.pha == Gwangyang_mod.pha:',hashlib.md5(open(REF+'/2.HypoDD/00.ph2dt/Gwangyang.pha','rb').read()).hexdigest()==hashlib.md5(open(phafile,'rb').read()).hexdigest())
print('  ph2dt.inp phase file line:',[l.strip() for l in open(REF+'/2.HypoDD/00.ph2dt/ph2dt.inp')][4])

# ---------- event.dat ----------
print('== 1c event.dat (02.dt.cc)')
evdat={}
for line in open(REF+'/2.HypoDD/02.dt.cc/event.dat'):
    t=line.split()
    if not t: continue
    d=t[0]; hms=t[1].rjust(8,'0')
    evid=int(t[-1])
    ot=datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(hms[:2]),int(hms[2:4]),tzinfo=timezone.utc)+timedelta(milliseconds=10*int(hms[4:8]))
    evdat[evid]=dict(ot=ot,lat=float(t[2]),lon=float(t[3]),dep=float(t[4]),mag=float(t[5]))
print('  event.dat ids',sorted(evdat))
for a in ['00.ph2dt','01.dt.ct','02.dt.cc']:
    print('  md5',a,'event.dat',hashlib.md5(open(f'{REF}/2.HypoDD/{a}/event.dat','rb').read()).hexdigest())

# ---------- mapping rtDD id -> hypodd id, independently by origin time ----------
ev=read_csv(CAT+'/event.csv')
print('== 1d event.csv vs .pha headers and event.dat')
print(f'  event.csv rows: {len(ev)}; ids: {[r["id"] for r in ev]}')
rt2hd={}
for r in ev:
    t=utc(r['isotime'])
    # find the .pha event with the closest origin
    best=min(pha_ev,key=lambda k:abs((pha_ev[k]['ot']-t).total_seconds()))
    dt=(pha_ev[best]['ot']-t).total_seconds()
    rt2hd[int(r['id'])]=best
    e=pha_ev[best]; d=evdat[best]
    dpos=(abs(float(r['latitude'])-d['lat']),abs(float(r['longitude'])-d['lon']),abs(float(r['depth'])-d['dep']))
    dte=(d['ot']-t).total_seconds()
    flag='' if (abs(dt)<1e-6 and abs(dte)<1e-6 and max(dpos)<1e-9) else '  <-- differs'
    print(f'  rtdd {r["id"]:>2} -> hypodd {best}  t-pha={dt*1000:+.1f} ms  t-event.dat={dte*1000:+.1f} ms  dlat/dlon/ddep vs event.dat={dpos}  mag {r["magnitude"]} vs {d["mag"]}/{e["mag"]}{flag}')
    if abs(dt)>1e-6: bad(f'event {r["id"]} time differs from .pha by {dt}')
    if abs(dte)>1e-6: print(f'    NOTE: event {r["id"]} time differs from event.dat by {dte*1000:.1f} ms')
    if max(dpos)>1e-9: bad(f'event {r["id"]} position differs from event.dat {dpos}')
print('  rtdd->hypodd mapping is id+199999 for all:',all(v==k+199999 for k,v in rt2hd.items()))

# float32 artefact claim for event 200002
for k,e in pha_ev.items():
    hhmmsscc=int(e['ot'].strftime('%H%M%S'))*100+int(round(e['ot'].microsecond/1e4))
    f32=int(np.float32(hhmmsscc))
    if f32!=hhmmsscc: print(f'  float32({hhmmsscc}) = {f32}  (hypodd id {k})')

# KMA id check: event_id_map
print('== 1e event_id_map.csv')
em=read_csv(CAT+'/event_id_map.csv')
for r in em:
    kma=r['kma_id']; rid=int(r['rtdd_id']); hid=int(r['hypodd_id'])
    kt=datetime.strptime(kma,'%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    dt=(pha_ev[hid]['ot']-kt).total_seconds()
    ok=(hid==rt2hd[rid]) and (0<=dt<5)
    # pick file names correspond to kma ids; check the pick-file times relative to .pha origin
    pk=read_csv(f'{REF}/picks/{kma}_picks.csv')
    first=min(utc(p['Time']) for p in pk)
    print(f'  rtdd {rid:>2} kma {kma} hypodd {hid}  pha_origin-kma={dt:+.2f} s  first PN+ pick - pha origin={(first-pha_ev[hid]["ot"]).total_seconds():.2f} s  {"OK" if ok else "BAD"}')
    if not ok: bad(f'id map row {r}')
    kst=datetime.strptime(r['kma_origin_kst'],'%Y-%m-%dT%H:%M:%S')
    if (kst-kt.replace(tzinfo=None)).total_seconds()!=9*3600: bad('KST column not UTC+9 for '+kma)

# ---------- station.csv vs used_stations_100km.csv ----------
print('== 1f station.csv vs used_stations_100km.csv')
st=read_csv(CAT+'/station.csv'); us=read_csv(REF+'/station_table/used_stations_100km.csv')
usd={(r['Network'],r['Code']):r for r in us}
std={(r['networkCode'],r['stationCode']):r for r in st}
print(f'  station.csv {len(st)} rows, used_stations {len(us)} rows; same set: {set(usd)==set(std)}')
maxd=[0,0,0]
for k,r in std.items():
    u=usd[k]
    d=[abs(float(r['latitude'])-float(u['Latitude'])),abs(float(r['longitude'])-float(u['Longitude'])),abs(float(r['elevation'])-float(u['Elevation']))]
    maxd=[max(a,b) for a,b in zip(maxd,d)]
    if r['locationCode']!='': bad('non-empty location code '+str(k))
print('  max |dlat|, |dlon| (deg), |delev| (m):',maxd)
if max(maxd)>1e-9: bad('station coordinates differ')

# ---------- phase.csv vs .pha ----------
print('== 1g phase.csv vs .pha')
ph=read_csv(CAT+'/phase.csv')
print(f'  phase.csv rows {len(ph)}; P={sum(p["type"]=="P" for p in ph)} S={sum(p["type"]=="S" for p in ph)}; types={sorted(set(p["type"] for p in ph))}')
cnt_cat={}; cnt_pha={}
for p in ph: cnt_cat[(int(p['eventId']),p['type'])]=cnt_cat.get((int(p['eventId']),p['type']),0)+1
for p in pha_picks: cnt_pha[(p['evid']-199999,p['ph'])]=cnt_pha.get((p['evid']-199999,p['ph']),0)+1
print('  per-event (P,S) counts equal:',cnt_cat==cnt_pha)
for e in range(1,12): print(f'    ev {e:>2}: catalog P={cnt_cat.get((e,"P"),0):>3} S={cnt_cat.get((e,"S"),0):>3} | pha P={cnt_pha.get((e,"P"),0):>3} S={cnt_pha.get((e,"S"),0):>3}')
# absolute-time comparison for every pick, with a 25-pick random subsample reported
key=lambda e,n,s,t:(e,n+s,t)
catd={}
for p in ph:
    k=key(int(p['eventId']),p['networkCode'],p['stationCode'],p['type'])
    if k in catd: bad('duplicate catalog pick '+str(k))
    catd[k]=p
diffs=[]; missing=[]
for p in pha_picks:
    rid=p['evid']-199999
    k=(rid,p['netsta'],p['ph'])
    if k not in catd: missing.append(k); continue
    abs_t=pha_ev[p['evid']]['ot']+timedelta(milliseconds=p['tt_ms'])
    diffs.append(((utc(catd[k]['isotime'])-abs_t).total_seconds(),k))
print(f'  .pha picks missing in phase.csv: {len(missing)}; catalog picks not in .pha: {len(catd)-len(diffs)}')
dd=np.array([d for d,_ in diffs])
print(f'  all {len(dd)} picks: max |catalog - (pha origin + tt)| = {np.abs(dd).max()*1000:.6f} ms')
random.seed(620)
for d,k in random.sample(diffs,25):
    print(f'    random pick {k}: diff {d*1000:+.3f} ms')
if np.abs(dd).max()>0.001: bad('pick times differ by >1 ms')
# uncertainties blank, location codes blank
print('  uncertainties all blank:',all(p['lowerUncertainty']=='' and p['upperUncertainty']=='' for p in ph))
print('  phase station codes all in station.csv:',all((p['networkCode'],p['stationCode']) in std for p in ph))

# ---------- channelCode vs SAC files ----------
print('== 1h channelCode vs SAC files on disk')
kma_of={int(r['rtdd_id']):r['kma_id'] for r in em}
nok=0; nbad=0; sensors={}
for p in ph:
    kma=kma_of[int(p['eventId'])]
    f=f'{REF}/waveforms_100km/{kma}/{kma}.{p["networkCode"]}.{p["stationCode"]}.{p["channelCode"]}.sac'
    comp=p['channelCode'][2]
    want='Z' if p['type']=='P' else 'N'
    if os.path.exists(f) and comp==want: nok+=1
    else: nbad+=1; print('   missing/unexpected',f,p['type'])
    sensors.setdefault(p['stationCode'],set()).add(p['channelCode'][:2])
print(f'  channel files exist with Z for P / N for S: {nok} ok, {nbad} bad; stations with >1 sensor code: {[s for s,v in sensors.items() if len(v)>1]}')
# one sensor per station across all SAC files
allsac=glob.glob(REF+'/waveforms_100km/*/*.sac')
sens_sac={}
for f in allsac:
    b=os.path.basename(f).split('.')
    sens_sac.setdefault(b[2],set()).add(b[3][:2])
multi=[s for s,v in sens_sac.items() if len(v)>1]
print(f'  SAC files {len(allsac)}; stations {len(sens_sac)}; stations with >1 sensor in SAC set: {multi}')
from collections import Counter
print('  sensor counts per station:',Counter(next(iter(v)) for v in sens_sac.values()))
usens={r['Code']:r['Sensor'] for r in us}
print('  SAC sensor == used_stations Sensor column for all:',all(next(iter(sens_sac[s]))==usens[s] for s in sens_sac), [ (s,sens_sac[s],usens[s]) for s in sens_sac if next(iter(sens_sac[s]))!=usens[s]])

# ---------- PhaseNet+ picks vs .pha (count and truncation) ----------
print('== 1i PhaseNet+ pick files vs .pha')
pn=[]
for f in sorted(glob.glob(REF+'/picks/*_picks.csv')): pn+=read_csv(f)
print(f'  PhaseNet+ picks: {len(pn)}; P={sum(p["Phase"]=="P" for p in pn)} S={sum(p["Phase"]=="S" for p in pn)}')
kma2rt={v:k for k,v in kma_of.items()}
pnd={(kma2rt[p['Event_ID']],p['Network']+p['Station'],p['Phase']):utc(p['Time']) for p in pn}
print('  same pick keys as phase.csv:',set(pnd)==set(catd))
dpn=np.array([(utc(catd[k]['isotime'])-pnd[k]).total_seconds()*1000 for k in catd])
print(f'  catalog - PhaseNet+ (ms): min {dpn.min():.3f} max {dpn.max():.3f}; n<=-9.999: {(dpn<=-9.999).sum()}')
vals,c=np.unique(np.round(dpn,3),return_counts=True)
print('  distribution:',dict(zip(vals.tolist(),c.tolist())))

print('\nPROBLEMS:',len(problems))
for p in problems: print(' -',p)
