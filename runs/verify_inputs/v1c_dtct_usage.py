# Independent verifier: which catalog picks never enter dt.ct (ph2dt output), and does each dt.ct
# line reproduce the .pha travel times and the mean of the two pick weights?
import csv
from collections import Counter
REF='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/reference/gwangyang_pnplus/2.HypoDD/00.ph2dt'
CAT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/rtdd_catalog'
pha={}; cur=None
for line in open(REF+'/Gwangyang_mod.pha'):
    if line.startswith('#'): cur=int(line.split()[-1]); continue
    t=line.split(); pha[(cur,t[0],t[3])]=(float(t[1]),float(t[2]))
used=Counter(); nlines=0; bad_tt=0; bad_w=0; cur=None
for line in open(REF+'/dt.ct'):
    if line.startswith('#'):
        a,b=map(int,line.split()[1:3]); cur=(a,b); continue
    t=line.split(); sta,t1,t2,w,ph=t[0],float(t[1]),float(t[2]),float(t[3]),t[4]
    nlines+=1
    p1=pha[(cur[0],sta,ph)]; p2=pha[(cur[1],sta,ph)]
    if abs(p1[0]-t1)>1e-6 or abs(p2[0]-t2)>1e-6: bad_tt+=1
    if abs((p1[1]+p2[1])/2-w)>1e-3: bad_w+=1
    used[(cur[0],sta,ph)]+=1; used[(cur[1],sta,ph)]+=1
never=[k for k in pha if used[k]==0]
print(f'dt.ct lines {nlines}; travel-time mismatches vs .pha {bad_tt}; weight != mean of pick weights {bad_w}')
print(f'picks never in dt.ct: {len(never)}')
for k in sorted(never): print('   ',k[0]-199999,k[1],k[2])
ex={(int(r['eventId']),'KS'+r['stationCode'],r['type']):int(r['n_dtct']) for r in csv.DictReader(open(CAT+'/phase_extra.csv'))}
agree=all(ex[(k[0]-199999,k[1],k[2])]==used[k] for k in pha)
print('phase_extra.csv n_dtct equals my per-pick dt.ct count for all picks:',agree)
