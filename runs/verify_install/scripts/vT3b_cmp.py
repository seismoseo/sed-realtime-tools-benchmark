# vT3b_cmp.py -- verifier scratch: compare two scautopick SCML outputs pick-by-pick (time, stream, method, phase, comments), ignoring publicID/creationTime
import sys, xml.etree.ElementTree as ET
def load(f):
    ns='{http://geofon.gfz.de/ns/seiscomp-schema/0.14}'
    out=[]
    for p in ET.parse(f).getroot().iter(ns+'pick'):
        w=p.find(ns+'waveformID')
        com=tuple(sorted((c.find(ns+'id').text, c.find(ns+'text').text) for c in p.findall(ns+'comment') if c.find(ns+'id').text!='RefPickID'))
        out.append((p.find(ns+'time/'+ns+'value').text, w.get('networkCode'), w.get('stationCode'), w.get('locationCode'), w.get('channelCode'), p.find(ns+'methodID').text, p.find(ns+'phaseHint').text, com))
    return sorted(out)
a, b = load(sys.argv[1]), load(sys.argv[2])
print('picks:', len(a), 'vs', len(b), '| identical (time, stream, method, phase, confidence comments):', a == b)
if a != b:
    sa, sb = set(a), set(b); print('only in first:', len(sa-sb), 'only in second:', len(sb-sa)); [print('  <', x) for x in sorted(sa-sb)[:5]]; [print('  >', x) for x in sorted(sb-sa)[:5]]
