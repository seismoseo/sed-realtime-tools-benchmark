#!/usr/bin/env bash
# make_nll_grids_tm.sh -- build the NonLinLoc 2-D P and S travel-time/take-off-angle grids of the
# NCSS CON model for the San Ramon 2025-26 benchmark, TRANS TRANS_MERC (control files by 09_make_nll_inputs.py).
# Output: /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm/time/sanramon2026_con.{P,S}.mod.*, sanramon2026_con.{P,S}.<NET_STA_LOC>.{time,angle}.*
# For rtDD/scrtdd: NLLGrid table directory = /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm/time, model name = sanramon2026_con.
# Usage: bash make_nll_grids_tm.sh            (re-run safe: it starts from empty model/ and time/)
set -euo pipefail
NLL_BIN=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/NonLinLoc/bin
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm
LOG=/home/msseo/works/74.SeisComP_rtDD_DLpicker/logs/sanramon2026_nll_grids_tm.log
echo "== $(date '+%F %T') make_nll_grids_tm.sh start" >> "$LOG"
rm -f /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm/DONE
rm -rf /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm/model /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm/time
mkdir -p model time
for P in P S; do
  "$NLL_BIN/Vel2Grid" run/phase$P.run >> "$LOG" 2>&1
  "$NLL_BIN/Grid2Time" run/phase$P.run >> "$LOG" 2>&1
done
echo "== $(date '+%F %T') done: $(ls time/*.time.hdr | wc -l) time grids, $(ls time/*.angle.hdr | wc -l) angle grids" >> "$LOG"
touch /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/sanramon_2026/inputs/nll_con_tm/DONE
