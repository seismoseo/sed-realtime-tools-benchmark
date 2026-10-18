# vB_pytest_wrapper.py -- verifier scratch: run pyrtdd's pytest suite in-process and report where pyrtdd was imported from
import sys, pytest
rc = pytest.main(sys.argv[1:])
m = sys.modules.get('pyrtdd'); e = sys.modules.get('pyrtdd.hdd.hdd_ext')
print('VERIFY pyrtdd imported from:', getattr(m, '__file__', None))
print('VERIFY hdd_ext imported from:', getattr(e, '__file__', None))
sys.exit(int(rc))
