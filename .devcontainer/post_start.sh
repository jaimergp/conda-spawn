#!/bin/bash

# This script assumes we are running in a Miniconda container where:
# - /opt/conda is the Miniconda or Miniforge installation directory
# - https://github.com/conda/conda is mounted at /workspaces/conda
# - https://github.com/conda/conda-spawn is mounted at
#   /workspaces/conda-spawn

set -euo pipefail

BASE_CONDA=${BASE_CONDA:-/opt/conda}
SRC_CONDA=${SRC_CONDA:-/workspaces/conda}
SRC_CONDA_SPAWN=${SRC_CONDA_SPAWN:-/workspaces/conda-spawn}

echo "Installing conda-spawn in dev mode..."
"$BASE_CONDA/bin/python" -m pip install -e "$SRC_CONDA_SPAWN"
