# vT2_picks.py -- verifier scratch: independent parse of the step-T smoke picks.xml; counts + comparison with the ORIGINAL PhaseNet+ pick file
import sys, xml.etree.ElementTree as ET
import pandas as pd
xmlf, reff = sys.argv[1], sys.argv[2]
ns={'s':'http://geofon.gfz.de/ns/seiscomp-schema/0.14'}
root=ET.parse(xmlf).getroot()
rows=[]
for p in root.iter('{%s}pick' % ns['s']):
    t=p.find('s:time/s:value',ns).text; w=p.find('s:waveformID',ns)
    rows.append(dict(id=p.get('publicID'), time=pd.Timestamp(t), net=w.get('networkCode'), sta=w.get('stationCode'), cha=w.get('channelCode'),
                     method=p.find('s:methodID',ns).text, phase=p.find('s:phaseHint',ns).text))
sc=pd.DataFrame(rows)
print('total picks', len(sc)); print(sc.groupby(['method','phase']).size().to_string())
print('amplitudes in XML:', sum(1 for _ in root.iter('{%s}amplitude' % ns['s'])))
ref=pd.read_csv(reff); ref['Time']=pd.to_datetime(ref['Time'])
print('reference picks (original PhaseNet+ file):', len(ref), ref.Phase.value_counts().to_dict())
for ph,tol in (('P',0.5),('S',1.0)):
    r=ref[ref.Phase==ph]; s=sc[sc.phase==ph]; m=[]
    for x in r.itertuples():
        c=s[s.sta==x.Station]
        if len(c)==0: continue
        dt=(c.time-x.Time).dt.total_seconds(); i=dt.abs().idxmin()
        if abs(dt[i])<=tol: m.append((x.Station, x.Time, c.time[i], dt[i]))
    m=pd.DataFrame(m,columns=['sta','ref','sc','dts'])
    print(f'{ph}: ref picks {len(r)} at {r.Station.nunique()} stations; matched {len(m)} within {tol}s; |dt| median {m.dts.abs().median():.4f} max {m.dts.abs().max():.4f}; mean dt {m.dts.mean():+.4f}')
    print('   stations with ref pick but no SeisComP match:', sorted(set(r.Station)-set(m.sta)))
    if ph=='P':
        for st in ('BAU','BLLA','DUSB'):
            q=m[m.sta==st]
            print('   spot check', st, (q.iloc[0].ref.isoformat(), q.iloc[0].sc.isoformat(), round(q.iloc[0].dts,4)) if len(q) else 'no match')
