# vA1b_py.sh -- verifier scratch: python-side SeisComP checks (numpy views, records from miniSEED) in a fresh login shell
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home ORT_DISABLE_TELEMETRY=1
cd $V/tmp
python -I -c 'import sys; print(sys.flags.isolated)' 
python - <<'PY'
import sys, numpy as np
import seiscomp.core as C, seiscomp.datamodel as DM, seiscomp.io as IO, seiscomp.math as M, seiscomp.seismology as S
print('python', sys.executable, sys.version.split()[0])
print('framework', C.FrameworkVersion().toString(), 'schema', f'{DM.Version.Major}.{DM.Version.Minor}')
a=C.DoubleArray(4)
for i in range(4): a.set(i, 1.5*i)
v=a.numpy(); print('numpy view', repr(v), v.dtype, 'numpy', np.__version__, np.__file__)
# read real miniSEED records from the smoke-test input (read only)
f='/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/smoke_dlpicker/input/20210827220322_sorted.mseed'
rs=IO.RecordStream.Open('file://'+f)
inp=IO.RecordInput(rs, C.Array.INT, C.Record.SAVE_RAW) if hasattr(IO,'RecordInput') else None
n=0; ids=set(); first=None
for rec in inp:
    n+=1; ids.add(rec.streamID())
    if first is None:
        first=rec; d=rec.data(); arr=d.numpy() if d is not None else None
        print('first rec', rec.streamID(), rec.startTime().iso(), rec.samplingFrequency(), 'nsamp', rec.sampleCount(), 'numpy', None if arr is None else (arr.dtype, arr[:5]))
print('records', n, 'streams', len(ids))
PY
echo "py exit=$?"
