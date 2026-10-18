# vC1b_tt.py -- verifier scratch: independent 1-D first-arrival times (direct + head wave on the 15 km interface, WGS-84 geodesic
# distance) from the cluster centroid vs the Gwangyang kim1983 NLL grids read through pyrtdd.hdd.NLLGrid
import math, sys
import pandas as pd
from pyproj import Geod
from pyrtdd.hdd import NLLGrid
D='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/nll_kim1983'
st=pd.read_csv(D+'/stations_gridded.csv')
clat, clon, cdep = 35.0000, 127.7286, 13.94
g=Geod(ellps='WGS84')
ttt=NLLGrid(gridPath=D+'/time', gridModel='kim1983', maxSearchDistance=0.1)
V={'P':(5.98,6.38),'S':(5.98/1.73,6.38/1.73)}
rows=[]
for s in st.itertuples():
    _,_,dist=g.inv(clon,clat,s.Longitude,s.Latitude); X=dist/1000.0; e=s.Elevation_m/1000.0
    for ph,(v1,v2) in V.items():
        tdir=math.hypot(X, cdep+e)/v1
        k=math.sqrt(1/v1**2-1/v2**2)
        # head wave exists beyond the critical offsets of both legs
        ic=math.asin(v1/v2); xcrit=(15-cdep)*math.tan(ic)+(15+e)*math.tan(ic)
        thead=X/v2+((15-cdep)+(15+e))*k if X>xcrit else float('inf')
        t1d=min(tdir,thead)
        tg=ttt.compute(clat,clon,cdep,s.Latitude,s.Longitude,s.Elevation_m,ph)
        rows.append((s.Code,ph,X,t1d,tg,tg-t1d,'head' if thead<tdir else 'direct'))
df=pd.DataFrame(rows,columns=['sta','ph','X_km','t1d','tgrid','diff','branch'])
print('n station-phases:',len(df))
for ph in 'PS':
    d=df[df.ph==ph]; print(ph,'max|grid-1D| = %.4f s at %s (%.1f km); mean %.4f s; branches %s' % (d['diff'].abs().max(), d.loc[d['diff'].abs().idxmax(),'sta'], d.loc[d['diff'].abs().idxmax(),'X_km'], d['diff'].mean(), d.branch.value_counts().to_dict()))
print(df.sort_values('X_km').iloc[[0,1,2,-2,-1]].to_string(index=False))
