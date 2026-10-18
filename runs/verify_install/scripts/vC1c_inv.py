# vC1c_inv.py -- verifier scratch: compare merged_inventory.xml station coordinates/elevations with used_stations_100km.csv
import pandas as pd
from obspy import read_inventory
from pyproj import Geod
R='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/reference'
inv=read_inventory(R+'/inventory/merged_inventory.xml')
st=pd.read_csv(R+'/gwangyang_pnplus/station_table/used_stations_100km.csv')
g=Geod(ellps='WGS84')
# station-level and channel-level coordinates (take the max over epochs/channels)
rows={}
for net in inv:
    for s in net:
        for c in s:
            rows.setdefault(s.code, []).append((c.latitude, c.longitude, c.elevation, s.latitude, s.longitude, s.elevation))
missing=[c for c in st.Code if c not in rows]
print('stations in CSV:', len(st), '| in inventory:', len(rows), '| CSV stations missing from inventory:', missing)
elevs=set(); off=[]
for s in st.itertuples():
    if s.Code not in rows: continue
    for la,lo,el,sla,slo,sel in rows[s.Code]:
        elevs.add(el)
    la,lo,el=rows[s.Code][0][:3]
    d=g.inv(s.Longitude,s.Latitude,lo,la)[2]
    if d>5: off.append((s.Code, round(d,1)))
print('distinct channel elevations in inventory:', sorted(elevs)[:5], '... n=', len(elevs))
print('stations >5 m off horizontally (first channel):', off)
