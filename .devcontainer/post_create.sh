#!/bin/bash

# This script assumes we are running in a Miniconda container where:
# - /opt/conda is the Miniconda or Miniforge installation directory
# - https://github.com/conda/conda is mounted at /workspaces/conda
# - https://github.com/conda/conda-classic-solver is mounted at
#   /workspaces/conda-classic-solver

set -euo pipefail

HERE=$(dirname $0)
BASE_CONDA=${BASE_CONDA:-/opt/conda}
SRC_CONDA=${SRC_CONDA:-/workspaces/conda}
SRC_CONDA_SPAWN=${SRC_CONDA_SPAWN:-/workspaces/conda-spawn}

if which apt-get > /dev/null; then
    echo "Installing system dependencies"
    apt-get update
    DEBIAN_FRONTEND=noninteractive xargs -a "$HERE/apt-deps.txt" apt-get install -y
fi


if [ ! -f "$SRC_CONDA/pyproject.toml" ]; then
    echo "https://github.com/conda/conda not found! Please clone or mount to $SRC_CONDA"
    exit 1
fi
if [ ! -f "$SRC_CONDA_SPAWN/pyproject.toml" ]; then
    echo "https://github.com/conda-incubator/conda-spawn not found! Please clone or mount to $SRC_CONDA_SPAWN"
    exit 1
fi
