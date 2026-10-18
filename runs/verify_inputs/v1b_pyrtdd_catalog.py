# Independent verifier, check 1 (part b): load the rtDD CSV triplet with pyrtdd's C++ reader
# and compare counts and values against my own CSV parse (both event.csv and event_centroid_start.csv).
# Also shows what happens with 14-digit KMA ids (32-bit unsigned event id).
# Run: conda activate pyrtdd; python -I v1b_pyrtdd_catalog.py
import csv, os, tempfile, shutil
from datetime import datetime, timezone, timedelta
import pyrtdd.hdd as h

CAT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/rtdd_catalog'
SCR='/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_inputs'

def utc(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
def rd(p): return list(csv.DictReader(open(p,newline='')))
def as_dt(t):
    # pyrtdd returns times as datetime (naive or aware) or as float seconds; normalise to aware datetime
    if isinstance(t,datetime): return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    if isinstance(t,timedelta): return datetime(1970,1,1,tzinfo=timezone.utc)+t   # pyrtdd: time since Unix epoch
    return datetime.fromtimestamp(float(t),tz=timezone.utc)

for evfile in ('event.csv','event_centroid_start.csv'):
    c=h.Catalog(CAT+'/station.csv',CAT+'/'+evfile,CAT+'/phase.csv')
    evs=c.getEvents(); phs=c.getPhases(); sts=c.getStations()
    nph=sum(len(v) for v in phs.values())
    nP=sum(1 for v in phs.values() for p in v if p.type=='P'); nS=sum(1 for v in phs.values() for p in v if p.type=='S')
    print(f'== pyrtdd Catalog({evfile}): events={len(evs)} phases={nph} (P={nP} S={nS}) stations={len(sts)}')
    sample=next(iter(evs.values()))
    print('   type of Event.time:',type(sample.time).__name__, sample.time)
    # compare values
    mism=0
    for r in rd(CAT+'/'+evfile):
        e=evs[int(r['id'])]
        dt=abs((as_dt(e.time)-utc(r['isotime'])).total_seconds())
        if dt>1e-6 or abs(e.latitude-float(r['latitude']))>1e-12 or abs(e.longitude-float(r['longitude']))>1e-12 or abs(e.depth-float(r['depth']))>1e-12: mism+=1; print('   event mismatch',r)
    rows=rd(CAT+'/phase.csv')
    lookup={}
    for eid,v in phs.items():
        for p in v: lookup[(p.eventId,p.networkCode,p.stationCode,p.type)]=p
    for r in rows:
        p=lookup.get((int(r['eventId']),r['networkCode'],r['stationCode'],r['type']))
        if p is None: mism+=1; print('   missing phase',r); continue
        if abs((as_dt(p.time)-utc(r['isotime'])).total_seconds())>1e-6 or p.channelCode!=r['channelCode'] or p.locationCode!=r['locationCode']: mism+=1; print('   phase mismatch',r)
    st=rd(CAT+'/station.csv')
    for r in st:
        sid=f"{r['networkCode']}.{r['stationCode']}.{r['locationCode']}"
        s=sts[sid]
        if abs(s.latitude-float(r['latitude']))>1e-12 or abs(s.longitude-float(r['longitude']))>1e-12 or abs(s.elevation-float(r['elevation']))>1e-12: mism+=1; print('   station mismatch',r)
    print(f'   value mismatches: {mism} (checked {len(evs)} events, {len(rows)} phases, {len(st)} stations)')

# 14-digit KMA ids: write a 1-event copy with the KMA id and see what pyrtdd stores
tmp=tempfile.mkdtemp(dir=SCR)
ev=rd(CAT+'/event.csv')[0]
with open(tmp+'/event.csv','w') as f:
    f.write('id,isotime,latitude,longitude,depth,magnitude\n')
    f.write(f"20210720161418,{ev['isotime']},{ev['latitude']},{ev['longitude']},{ev['depth']},{ev['magnitude']}\n")
with open(tmp+'/phase.csv','w') as f:
    f.write('eventId,isotime,lowerUncertainty,upperUncertainty,type,networkCode,stationCode,locationCode,channelCode\n')
    r=rd(CAT+'/phase.csv')[0]
    f.write(f"20210720161418,{r['isotime']},,,{r['type']},{r['networkCode']},{r['stationCode']},,{r['channelCode']}\n")
c=h.Catalog(CAT+'/station.csv',tmp+'/event.csv',tmp+'/phase.csv')
print('== 14-digit id test: stored ids',list(c.getEvents().keys()),' 20210720161418 mod 2**32 =',20210720161418%2**32)
shutil.rmtree(tmp)
