# Footprint outside the project folder

Everything this project created or changed outside `/home/msseo/works/74.SeisComP_rtDD_DLpicker`, as
checked on 2026-10-17 (about 13:40 KST). Nothing here affects other users. None of it needs to be removed;
the commands below are only for the case that you want the state from before.

| What | Where | Made by | Size | Needed? |
|---|---|---|---|---|
| Two conda environments | `~/miniforge3/envs/seiscomp`, `~/miniforge3/envs/pyrtdd` | `install/00_create_conda_envs.sh` | a few GB | **yes** (SeisComP build/runtime, pyrtdd) |
| Jupyter kernel "pyrtdd" | `~/.local/share/jupyter/kernels/pyrtdd` | `00_create_conda_envs.sh` | 1 kB | yes, for the notebooks |
| Conda package downloads (195 new entries; the cache already held 1580 older ones) | `~/.local/share/mamba/pkgs` (20 GB in total) | creating the two environments | part of 20 GB | no (normal download cache) |
| Two stale lines | `~/.conda/environments.txt`: `/home/msseo/.local/share/mamba/envs/seiscomp` and `.../pyrtdd` | my first environment attempt landed in `~/.local/share/mamba/envs` (because `~/.bashrc` sets `MAMBA_ROOT_PREFIX` there); those two folders were deleted and the environments recreated in `~/miniforge3/envs` | 2 lines | no (conda ignores folders that no longer exist) |
| Podman pause process + user D-Bus | PIDs 1505192 (`catatonit -P`), 1505210/1505211 (`dbus-broker`), started 11:23:31 | my one-off `podman info` check of whether containers could be used (they were not needed) | ~0 CPU, few MB | no |
| Empty podman storage | `~/.local/share/containers` (128 kB; no images, no containers) | same `podman info` | 128 kB | no |
| pytest temporary folder | `/tmp/pytest-of-msseo` | pyrtdd's test suite | small | no |
| Empty folder | `/tmp/tmpi89asmtx_kernels` | the Jupyter kernel registration | 0 | no |
| Font list cache | `~/.cache/matplotlib/fontlist-v3.11.0.json` | matplotlib, first use in env pyrtdd | 110 kB | no (normal cache) |
| pip self-check stamp | `~/.cache/pip/selfcheck/` | pip during the pyrtdd install | < 1 kB | no |

Removed again (created by our test runs, deleted on 2026-10-17):
- `/tmp/.ses` (51 bytes, a session stamp written by ONNX Runtime's telemetry client at 12:34:39);
- the ONNX Runtime telemetry queue inside the project (`runs/seiscomp_home/.cache/Microsoft/...`, 7
  queued records with OS, process name, CPU model, ONNX Runtime version and a random device id; no
  waveforms, picks or file names; still queued, i.e. not sent). Telemetry is now switched off in
  `install/env_seiscomp.sh` (`ORT_DISABLE_TELEMETRY=1`).

Not touched: `~/.seiscomp` (never created), all other conda environments (their `conda-meta/history`
dates are unchanged), server B (read-only copies only).

## Optional clean-up commands (run them yourself if you want)

```bash
# podman pause process and its empty storage (only if you do not use podman on Server A)
podman system migrate          # stops the pause process cleanly; or: kill 1505192
rm -rf ~/.local/share/containers

# the two stale lines in ~/.conda/environments.txt
sed -i '\#^/home/msseo/.local/share/mamba/envs/\(seiscomp\|pyrtdd\)$#d' ~/.conda/environments.txt

# temporary files
rm -rf /tmp/pytest-of-msseo /tmp/tmpi89asmtx_kernels

# conda download cache (affects all environments' cache, not the environments themselves)
mamba clean --all --dry-run    # look first, then without --dry-run
```

The user D-Bus processes (1505210/1505211) are left alone on purpose: other processes of yours may
already talk to them; they end when your last login session ends.
