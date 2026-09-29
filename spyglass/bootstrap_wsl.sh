#!/usr/bin/env bash
# Create (or update) the `spyglass-photometry` conda env inside the Ubuntu-24.04 WSL2
# distro, from spyglass-photometry-env.yaml plus the post-install pins described in that
# file's header. Miniforge is expected at /opt/miniforge3.
#
# Spyglass cannot be imported on native Windows Python (it forces the POSIX-only
# multiprocessing "fork" start method at import time), so the Spyglass side runs in
# Linux under WSL2. MySQL stays in its Docker Desktop container, reachable from WSL at
# 127.0.0.1:3307.
#
# Run inside the distro (optional argument: env name, default spyglass-photometry):
#   wsl -d Ubuntu-24.04 -- bash /mnt/c/Users/algab/CatalystNeuro/uchida-lab-to-nwb/spyglass/bootstrap_wsl.sh
set -euo pipefail

MINIFORGE=/opt/miniforge3
ENV_YAML=/mnt/c/Users/algab/CatalystNeuro/uchida-lab-to-nwb/spyglass/spyglass-photometry-env.yaml
ENV_NAME="${1:-spyglass-photometry}"

source "${MINIFORGE}/etc/profile.d/conda.sh"

if conda env list | grep -qE "^\s*${ENV_NAME}\s"; then
  echo "=== updating existing '${ENV_NAME}' env from ${ENV_YAML} ==="
  conda env update -n "${ENV_NAME}" -f "${ENV_YAML}" --prune
else
  echo "=== creating '${ENV_NAME}' env from ${ENV_YAML} ==="
  conda env create -n "${ENV_NAME}" -f "${ENV_YAML}"
fi

# Pins pip can't resolve together with the yaml's packages (see the yaml header).
# Each step is a separate pip call on purpose: pip reports the known conflicts as
# warnings instead of refusing to install.
PIP="conda run -n ${ENV_NAME} python -m pip"

echo "=== ndx-pose (commit used by the converted files) + pynwb/hdmf ==="
${PIP} install \
  "ndx-pose @ git+https://github.com/rly/ndx-pose.git@b1f6980fa29bfe695e4b4ad26dd32b40ecddf779" \
  "pynwb==4.2.0" "hdmf==6.2.0"

echo "=== kachery-cloud, then re-pin pubnub for Spyglass ==="
${PIP} install kachery-cloud
${PIP} install "pubnub<6.4"

echo "=== versions ==="
conda run -n "${ENV_NAME}" python -c "import importlib.metadata as m; \
print({p: m.version(p) for p in ('spyglass-neuro','datajoint','pynwb','hdmf','ndx-fiber-photometry','ndx-ophys-devices','ndx-pose','ndx-franklab-novela','kachery-cloud','pubnub')})"

echo "=== BOOTSTRAP DONE ==="
