#!/usr/bin/env bash
# Create (or update) the `spyglass-photometry` conda env inside the Ubuntu-24.04 WSL2
# distro. Miniforge is already installed at /opt/miniforge3 (from the Gonzalez-Sulser
# project); the existing `spyglass` and `spyglass-eeg` envs are NOT touched.
#
# Spyglass cannot be imported on native Windows Python (it forces the POSIX-only
# multiprocessing "fork" start method at import time), so the Spyglass side runs in
# Linux under WSL2. MySQL stays in its Docker Desktop container, reachable from WSL at
# 127.0.0.1:3307.
#
# Run inside the distro:
#   wsl -d Ubuntu-24.04 -- bash /mnt/c/Users/algab/CatalystNeuro/uchida-lab-to-nwb/spyglass/bootstrap_wsl.sh
set -euo pipefail

MINIFORGE=/opt/miniforge3
ENV_YAML=/mnt/c/Users/algab/CatalystNeuro/uchida-lab-to-nwb/spyglass/spyglass-photometry-env.yaml

source "${MINIFORGE}/etc/profile.d/conda.sh"

if conda env list | grep -qE '^\s*spyglass-photometry\s'; then
  echo "=== updating existing 'spyglass-photometry' env from ${ENV_YAML} ==="
  conda env update -n spyglass-photometry -f "${ENV_YAML}" --prune
else
  echo "=== creating 'spyglass-photometry' env from ${ENV_YAML} ==="
  conda env create -f "${ENV_YAML}"
fi

echo "=== versions ==="
conda run -n spyglass-photometry python -c "import importlib.metadata as m; \
print({p: m.version(p) for p in ('spyglass-neuro','datajoint','pynwb','hdmf','ndx-fiber-photometry','ndx-ophys-devices','ndx-pose','ndx-franklab-novela')})"

echo "=== BOOTSTRAP DONE ==="
