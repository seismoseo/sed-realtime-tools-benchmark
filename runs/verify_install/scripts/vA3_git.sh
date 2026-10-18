# vA3_git.sh -- verifier scratch: read-only git checks (no index refresh: --no-optional-locks)
source /home/msseo/miniforge3/etc/profile.d/conda.sh; conda activate /home/msseo/miniforge3/envs/seiscomp
S=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/seiscomp
for d in $S $S/src/base/common $S/src/base/main $S/src/base/seedlink $S/src/base/extras $S/src/extras/scrtdd $S/src/extras/scdlrtpicker; do
  echo "== $d"
  g="git --no-optional-locks -C $d"
  echo "  remote: $($g remote get-url origin 2>&1)"
  echo "  HEAD:   $($g rev-parse HEAD 2>&1)"
  echo "  tags at HEAD: $($g tag --points-at HEAD 2>&1 | tr '\n' ' ')"
  echo "  describe: $($g describe --tags --always 2>&1)"
  echo "  shallow: $($g rev-parse --is-shallow-repository 2>&1); branch: $($g rev-parse --abbrev-ref HEAD 2>&1)"
  echo "  status (tracked changes):"; $g status --porcelain --untracked-files=no 2>&1 | head -10 | sed 's/^/    /'
  echo "  untracked (top 8):"; $g status --porcelain --untracked-files=normal 2>&1 | grep '^??' | head -8 | sed 's/^/    /'
done
ls $S/src/base $S/src/extras
