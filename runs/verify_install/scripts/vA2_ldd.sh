# vA2_ldd.sh -- verifier scratch: ldd audit of EVERY ELF file under SEISCOMP_ROOT, (a) with the env of a fresh login + env_seiscomp.sh, (b) LD_LIBRARY_PATH unset
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home
R=$SEISCOMP_ROOT/lib/; E=$CONDA_PREFIX/lib/
out=$V/logs/A2_ldd; mkdir -p $out
# list ELF files (skip the bundled onnxruntime dir's own files are included too)
find $SEISCOMP_ROOT -type f \( -perm -u+x -o -name '*.so*' \) -print0 | xargs -0 file -N | grep -E 'ELF 64-bit' | cut -d: -f1 | sort > $out/elf_files.txt
echo "ELF files: $(wc -l < $out/elf_files.txt)"
for mode in env noLD; do
  : > $out/summary_$mode.txt
  while read -r f; do
    if [ $mode = env ]; then res=$(ldd "$f" 2>&1); else res=$(env -u LD_LIBRARY_PATH ldd "$f" 2>&1); fi
    echo "$res" | awk -v F="$f" -v R="$R" -v E="$E" '
      /not found/ {print "NOTFOUND " F " " $1; next}
      $2=="=>" && $3 ~ /^\// {
        if (index($3,R)==1 || index($3,E)==1) next
        if ($1 ~ /^(libc|libm|libpthread|libdl|librt|libutil|ld-linux-x86-64|libresolv|libanl|libnsl|libBrokenLocale|libmvec)[.]so/) next
        print "OUTSIDE " F " " $1 " => " $3 }' >> $out/summary_$mode.txt
  done < $out/elf_files.txt
  echo "mode=$mode: not-found lines: $(grep -c ^NOTFOUND $out/summary_$mode.txt), outside-conda/SC non-glibc lines: $(grep -c ^OUTSIDE $out/summary_$mode.txt)"
  grep -E '^(NOTFOUND|OUTSIDE)' $out/summary_$mode.txt | awk '{print $1, $3, $4, $5}' | sort | uniq -c | sort -rn | head -20
done
echo "--- RPATH/RUNPATH kinds over all ELF files:"
while read -r f; do readelf -d "$f" 2>/dev/null | grep -oE '\((RPATH|RUNPATH)\)' | head -1 || true; done < $out/elf_files.txt | sort | uniq -c
echo "--- files without RPATH/RUNPATH:"
while read -r f; do readelf -d "$f" 2>/dev/null | grep -qE '\((RPATH|RUNPATH)\)' || echo "  $f"; done < $out/elf_files.txt | head -30
echo "--- sample RPATH values:"
for t in bin/scautopick bin/scrtdd share/plugins/dlrtpicker.so share/plugins/tttnll.so lib/libhdd.so lib/libseiscomp_core.so lib/python/seiscomp/_core.so; do echo "  $t: $(readelf -d $SEISCOMP_ROOT/$t | grep -E 'RPATH|RUNPATH' | sed 's/^.*\[//; s/\]$//')"; done
