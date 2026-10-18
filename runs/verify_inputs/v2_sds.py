# Independent verifier, check 2: SDS miniSEED archive (and playback files) versus the 1656 SAC files.
# For every SAC file: locate its SDS day file by my own path rule, read it with obspy (no SDS Client),
# find the covering trace, compare samples exactly (np.array_equal) and the start time.
# Then check the reverse direction: every SDS sample belongs to some SAC window (no extra data),
# the SDS file set equals the expected set, records are time-ordered and STEIM2/512 bytes.
# Run: conda activate pyrtdd; python -I v2_sds.py
import glob, os, sys, struct
from collections import defaultdict, Counter
import numpy as np
import obspy
from obspy import UTCDateTime

ROOT='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev'
SAC=ROOT+'/reference/gwangyang_pnplus/waveforms_100km'
SDS=ROOT+'/inputs/sds'
PB=ROOT+'/inputs/playback'

sacfiles=sorted(glob.glob(SAC+'/*/*.sac'))
print('SAC files:',len(sacfiles))

def sds_path(net,sta,loc,cha,t):
    return f'{SDS}/{t.year}/{net}/{sta}/{cha}.D/{net}.{sta}.{loc}.{cha}.D.{t.year}.{t.julday:03d}'

sds_cache={}
def read_sds(p):
    if p not in sds_cache: sds_cache[p]=obspy.read(p,format='MSEED')
    return sds_cache[p]

nonint=0; maxabs=0; dtypes=Counter(); cross_midnight=0
res=[]   # (sacfile, ok_samples, start_diff_us, note)
windows=defaultdict(list)   # sds file -> list of (start, npts, sacfile)
for f in sacfiles:
    st=obspy.read(f,format='SAC'); tr=st[0]
    d=tr.data; dtypes[str(d.dtype)]+=1
    if not np.all(np.isfinite(d)) or not np.all(d==np.round(d)): nonint+=1
    maxabs=max(maxabs,float(np.abs(d).max()))
    net,sta,loc,cha=tr.stats.network,tr.stats.station,tr.stats.location,tr.stats.channel
    # file-name sanity: name encodes net.sta.cha
    b=os.path.basename(f).split('.')
    assert (b[1],b[2],b[3])==(net,sta,cha), f
    t0=tr.stats.starttime; t1=tr.stats.endtime
    if t0.julday!=t1.julday: cross_midnight+=1
    p=sds_path(net,sta,loc,cha,t0)
    windows[p].append((t0,tr.stats.npts,f))
    if not os.path.exists(p): res.append((f,False,None,'SDS file missing')); continue
    sds=read_sds(p).select(network=net,station=sta,location=loc,channel=cha)
    hit=None
    for s in sds:
        # covering trace: SAC window inside the SDS trace (half-sample tolerance at both ends)
        if s.stats.starttime-0.5*s.stats.delta<=t0 and s.stats.endtime+0.5*s.stats.delta>=t1 and s.stats.sampling_rate==tr.stats.sampling_rate:
            hit=s; break
    if hit is None: res.append((f,False,None,'no covering trace')); continue
    i0=int(round((t0-hit.stats.starttime)*hit.stats.sampling_rate))
    seg=hit.data[i0:i0+tr.stats.npts]
    # exact sample equality: SAC float32 whole numbers vs miniSEED int32
    eq=(len(seg)==tr.stats.npts) and np.array_equal(seg.astype(np.float64),d.astype(np.float64))
    t_seg=hit.stats.starttime+i0*hit.stats.delta
    dus=(t_seg-t0)*1e6
    res.append((f,eq,dus,'' if eq else 'samples differ'))

ok=sum(1 for r in res if r[1]); bad=[r for r in res if not r[1]]
dus=np.array([r[2] for r in res if r[2] is not None])
print(f'SAC dtypes {dict(dtypes)}; non-integer-valued or non-finite files: {nonint}; max |sample| = {maxabs:.0f} (2^24 = {2**24})')
print(f'SAC windows crossing midnight: {cross_midnight}')
print(f'SAC->SDS: samples identical for {ok}/{len(res)} files; failures {len(bad)}')
for r in bad[:20]: print('   FAIL',r)
nz=np.abs(dus)>0.5
print(f'start time (SDS sample time - SAC start) over all files: max |diff| = {np.abs(dus).max():.3f} us; files with |diff|>0.5 us: {nz.sum()}')
if nz.any():
    for r in res:
        if r[2] is not None and abs(r[2])>0.5: print(f'   {os.path.basename(r[0])}: {r[2]:+.3f} us')

# reverse direction: SDS content == union of SAC windows, no extra files
expected=set(windows)
actual=set(glob.glob(SDS+'/*/*/*/*.D/*'))
print(f'SDS files expected {len(expected)}, on disk {len(actual)}; missing {len(expected-actual)}, extra {len(actual-expected)}')
extra_samples=0; trace_count_mismatch=0; nslc_extra=0; total_sds_samples=0; total_union=0
for p in sorted(actual & expected):
    st=read_sds(p)
    ids={tr.id for tr in st}
    if len(ids)!=1: nslc_extra+=1; print('   >1 NSLC in',p,ids)
    # union of SAC windows (in sample index of 100 Hz relative to first window start)
    w=sorted(windows[p])
    sr=100.0
    base=w[0][0]
    iv=[]
    for t0,n,f in w:
        a=int(round((t0-base)*sr)); iv.append([a,a+n])   # [a, b) in samples
    iv.sort(); merged=[]
    for a,b in iv:
        if merged and a<=merged[-1][1]: merged[-1][1]=max(merged[-1][1],b)
        else: merged.append([a,b])
    u=sum(b-a for a,b in merged); total_union+=u
    n=sum(tr.stats.npts for tr in st); total_sds_samples+=n
    if len(st)!=len(merged): trace_count_mismatch+=1; print(f'   {os.path.basename(p)}: {len(st)} traces vs {len(merged)} SAC-union intervals')
    for tr in st:
        a=int(round((tr.stats.starttime-base)*sr)); b=a+tr.stats.npts
        cov=sum(max(0,min(b,y)-max(a,x)) for x,y in merged)
        extra_samples+=tr.stats.npts-cov
print(f'SDS samples total {total_sds_samples}; union of SAC windows {total_union}; SDS samples outside any SAC window: {extra_samples}; files with trace/interval count mismatch: {trace_count_mismatch}; files with >1 NSLC: {nslc_extra}')

# record-level checks: encoding, record length, time order (SeisComP's SDS reader assumes ordered records)
from obspy.io.mseed.util import get_record_information
enc=Counter(); rl=Counter(); unordered=0; qual=Counter(); b1001=0
for p in sorted(actual):
    size=os.path.getsize(p); off=0; last=None
    with open(p,'rb') as fh:
        while off<size:
            info=get_record_information(fh,offset=off)
            enc[info['encoding']]+=1; rl[info['record_length']]+=1; qual[info.get('data_quality_flags','?') if False else info.get('quality','?')]+=1
            t=info['starttime']
            if last is not None and t<last: unordered+=1
            last=t
            off+=info['record_length']
print(f'records: encodings {dict(enc)}; record lengths {dict(rl)}; quality {dict(qual)}; out-of-order record starts: {unordered}')

# playback files: same sample-exact check, per event file
print('== playback files')
pb_ok=0; pb_bad=0; pb_dus=[]; pb_extra=0
for ev in sorted(os.listdir(SAC)):
    pf=f'{PB}/{ev}.mseed'
    if not os.path.exists(pf): print('   missing',pf); continue
    pst=obspy.read(pf,format='MSEED')
    sacs=sorted(glob.glob(f'{SAC}/{ev}/*.sac'))
    pts=0
    for f in sacs:
        tr=obspy.read(f,format='SAC')[0]
        cand=pst.select(id=tr.id)
        hit=None
        for s in cand:
            if s.stats.starttime-0.005<=tr.stats.starttime and s.stats.endtime+0.005>=tr.stats.endtime: hit=s; break
        if hit is None: pb_bad+=1; print('   no covering playback trace',f); continue
        i0=int(round((tr.stats.starttime-hit.stats.starttime)*100))
        seg=hit.data[i0:i0+tr.stats.npts]
        if np.array_equal(seg.astype(np.float64),tr.data.astype(np.float64)): pb_ok+=1
        else: pb_bad+=1; print('   samples differ',f)
        pb_dus.append(((hit.stats.starttime+i0*hit.stats.delta)-tr.stats.starttime)*1e6)
    tot=sum(t.stats.npts for t in pst); sacn=sum(obspy.read(f,headonly=True)[0].stats.npts for f in sacs)
    ids_p={t.id for t in pst}; ids_s={obspy.read(f,headonly=True)[0].id for f in sacs}
    print(f'   {ev}: playback traces {len(pst)} samples {tot}; SAC files {len(sacs)} samples {sacn}; ids only in playback: {sorted(ids_p-ids_s)[:5]}{"..." if len(ids_p-ids_s)>5 else ""} ({len(ids_p-ids_s)})')
print(f'playback: identical {pb_ok}, failures {pb_bad}; max |start diff| {np.abs(pb_dus).max():.3f} us')
