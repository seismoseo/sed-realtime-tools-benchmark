# Independent verifier, check 3: inputs/stations.xml
#  - StationXML schema validation (obspy's bundled XSD)
#  - every SAC channel/event window covered by a channel epoch? (my own window test)
#  - for uncovered channels: does merged_inventory.xml have anything that would cover them?
#  - azimuth/dip/sample rate/coordinates equal merged_inventory.xml for the same epoch (all channels, 5 printed)
#  - overlapping epochs per channel; station-vs-channel coordinates; coordinates vs station.csv
#  - pyrtdd NLLGrid lookup with the stations.xml coordinates (10 m = scrtdd plugin default, and 0.1 m)
# Run: conda activate pyrtdd; python -I v4_stationxml.py
import csv, glob, os, random, math
from collections import defaultdict
import numpy as np
import obspy
from obspy import read_inventory, UTCDateTime
from obspy.io.stationxml.core import validate_stationxml
from pyproj import Geod
import pyrtdd.hdd as h

ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
SX=ROOT+'/inputs/stations.xml'; MI=ROOT+'/reference/inventory/merged_inventory.xml'
SAC=ROOT+'/reference/gwangyang_pnplus/waveforms_100km'
G=Geod(ellps='WGS84')

ok,err=validate_stationxml(SX)
print('schema valid:',ok, err[:3] if err else '')
inv=read_inventory(SX); mi=read_inventory(MI)
nsta=sum(len(n.stations) for n in inv); ncha=sum(len(s.channels) for n in inv for s in n.stations)
print(f'stations.xml: {nsta} station epochs, {len(set(s.code for n in inv for s in n.stations))} station codes, {ncha} channel epochs')
print(f'merged_inventory.xml: {len(set(s.code for n in mi for s in n.stations))} station codes, {sum(len(s.channels) for n in mi for s in n.stations)} channel epochs')

def epochs(inventory,net,sta,loc,cha):
    out=[]
    for n in inventory.select(network=net,station=sta,location=loc if loc else '',channel=cha):
        for s in n.stations:
            for c in s.channels:
                if c.location_code==loc and c.code==cha: out.append((s,c))
    return out

# SAC windows per channel
win=defaultdict(list)
for f in sorted(glob.glob(SAC+'/*/*.sac')):
    tr=obspy.read(f,headonly=True)[0]
    win[(tr.stats.network,tr.stats.station,tr.stats.location,tr.stats.channel)].append((tr.stats.starttime,tr.stats.endtime,os.path.basename(os.path.dirname(f))))
print(f'SAC channels: {len(win)}, SAC files: {sum(len(v) for v in win.values())}')
covered=[];uncovered=[];partial=[];files_ok=0;files_bad=0
for k,ws in sorted(win.items()):
    ep=epochs(inv,*k)
    nok=0
    for t0,t1,ev in ws:
        hit=[c for s,c in ep if c.start_date<=t0 and (c.end_date is None or c.end_date>=t1)]
        if len(hit)==1: nok+=1
        elif len(hit)>1: print('   several epochs cover',k,ev)
    files_ok+=nok; files_bad+=len(ws)-nok
    if nok==len(ws): covered.append(k)
    elif nok==0: uncovered.append(k)
    else: partial.append(k)
print(f'channels fully covered {len(covered)}, partially {len(partial)}, not at all {len(uncovered)}; SAC files covered {files_ok}, not covered {files_bad}')
for k in uncovered+partial:
    m=epochs(mi,*k)
    cov=[(str(c.start_date)[:10],str(c.end_date)[:10] if c.end_date else 'open') for s,c in m]
    ws=win[k]
    could=[ev for t0,t1,ev in ws if any(c.start_date<=t0 and (c.end_date is None or c.end_date>=t1) for s,c in m)]
    other=sorted({c.code for n in mi.select(station=k[1]) for s in n.stations for c in s.channels})
    print(f'   uncovered {".".join(k)}: merged_inventory epochs of this code {cov if cov else "none"}; windows coverable from merged_inventory: {len(could)}; codes at station in merged_inventory: {other}')

# az/dip/sr/coords: compare each stations.xml channel epoch with the same epoch in merged_inventory
diffs=0; checked=0; examples=[]
for n in inv:
    for s in n.stations:
        for c in s.channels:
            m=[mc for ms,mc in epochs(mi,n.code,s.code,c.location_code,c.code) if mc.start_date==c.start_date and mc.end_date==c.end_date]
            if len(m)!=1: diffs+=1; print('   no unique merged epoch for',s.code,c.code,c.start_date); continue
            mc=m[0]; checked+=1
            fields=[(c.azimuth,mc.azimuth),(c.dip,mc.dip),(c.sample_rate,mc.sample_rate),(c.latitude,mc.latitude),(c.longitude,mc.longitude),(c.elevation,mc.elevation),(c.depth,mc.depth)]
            if any(a!=b for a,b in fields) or c.azimuth is None or c.dip is None: diffs+=1; print('   DIFF',s.code,c.code,fields)
            same_resp=(c.response.instrument_sensitivity.value==mc.response.instrument_sensitivity.value) if c.response and mc.response else None
            if same_resp is False: diffs+=1; print('   sensitivity differs',s.code,c.code)
            examples.append((s.code,c.code,str(c.start_date)[:10],c.azimuth,mc.azimuth,c.dip,mc.dip,c.sample_rate))
print(f'channel epochs compared with merged_inventory: {checked}; differences: {diffs}')
random.seed(620)
for e in random.sample(examples,5): print(f'   {e[0]}.{e[1]} epoch {e[2]}: azimuth {e[3]} vs {e[4]}, dip {e[5]} vs {e[6]}, sample rate {e[7]}')
print('   distinct (azimuth,dip) pairs in stations.xml:',sorted({(e[3],e[5]) for e in examples}))
print('   channels missing azimuth or dip:',sum(1 for e in examples if e[3] is None or e[5] is None))

# overlapping epochs
ov=0
for n in inv:
    for s in n.stations:
        byc=defaultdict(list)
        for c in s.channels: byc[(c.location_code,c.code)].append(c)
        for k,cs in byc.items():
            cs=sorted(cs,key=lambda c:c.start_date)
            for a,b in zip(cs,cs[1:]):
                if a.end_date is None or a.end_date>b.start_date: ov+=1; print('   overlap',s.code,k,a.start_date,a.end_date,b.start_date)
print('overlapping channel epochs:',ov)

# coordinates vs station.csv and NLLGrid lookups
st={r['stationCode']:r for r in csv.DictReader(open(ROOT+'/inputs/rtdd_catalog/station.csv'))}
ttt10=h.NLLGrid(gridPath=ROOT+'/inputs/nll_kim1983/time',gridModel='kim1983',maxSearchDistance=10.0)
codes=sorted({s.code for n in inv for s in n.stations})
dh=[];de=[];found=0;found_lalo=0;tested=0;stacoord_vs_chan=0
for code in codes:
    s=[s for n in inv for s in n.stations if s.code==code][0]
    for c in s.channels:
        if (c.latitude,c.longitude,c.elevation)!=(s.latitude,s.longitude,s.elevation): stacoord_vs_chan+=1
    r=st[code]
    d=G.inv(s.longitude,s.latitude,float(r['longitude']),float(r['latitude']))[2]
    dh.append((d,code)); de.append(s.elevation-float(r['elevation']))
    tested+=1
    try: ttt10.compute(34.9997,127.7289,13.94,s.latitude,s.longitude,s.elevation,'P'); found+=1
    except Exception as e: pass
    try: ttt10.compute(34.9997,127.7289,13.94,s.latitude,s.longitude,float(r['elevation']),'P'); found_lalo+=1
    except Exception as e: pass
dh.sort(reverse=True)
print(f'stations.xml station elevations: min {min(s.elevation for n in inv for s in n.stations)} max {max(s.elevation for n in inv for s in n.stations)} m')
print(f'horizontal offset stations.xml vs station.csv: >1 m at {sum(1 for d,_ in dh if d>1)} stations: {[(c,round(d,1)) for d,c in dh if d>1]}')
print(f'channel coordinates differing from their station element: {stacoord_vs_chan}')
print(f'NLLGrid P lookups (10 m tolerance) with stations.xml lat/lon/elev: {found}/{tested}; with stations.xml lat/lon + station.csv elevation: {found_lalo}/{tested}')
missing_sta=sorted(set(st)-set(codes)); print('stations in station.csv but not in stations.xml:',missing_sta)
