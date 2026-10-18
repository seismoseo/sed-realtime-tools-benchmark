# Independent verifier: count picks whose residual against the NLL grid (HypoDD dt.cc location,
# origin on the .pha datum) exceeds 1 s, to compare with the step-C1 count (17 = 9 P + 8 S).
import csv
from datetime import datetime, timezone, timedelta
import pyrtdd.hdd as h
ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
def utc(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
ttt=h.NLLGrid(gridPath=ROOT+'/inputs/nll_kim1983/time',gridModel='kim1983')
sta={r['stationCode']:r for r in csv.DictReader(open(ROOT+'/inputs/rtdd_catalog/station.csv'))}
loc={int(r['rtdd_id']):r for r in csv.DictReader(open(ROOT+'/reference_tables/hypodd_dtcc.csv'))}
out=[]
for r in csv.DictReader(open(ROOT+'/inputs/rtdd_catalog/phase.csv')):
    e=int(r['eventId']); L=loc[e]; s=sta[r['stationCode']]
    obs=(utc(r['isotime'])-utc(L['origin_time_pha_datum'])).total_seconds()
    pred=ttt.compute(float(L['latitude']),float(L['longitude']),float(L['depth_km']),float(s['latitude']),float(s['longitude']),float(s['elevation']),r['type'])
    if abs(obs-pred)>1.0: out.append((e,r['stationCode'],r['type'],round(obs-pred,2)))
print(len(out),'picks off by >1 s:',sum(1 for o in out if o[2]=='P'),'P,',sum(1 for o in out if o[2]=='S'),'S')
for o in out: print('  ',o)
