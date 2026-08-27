#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

source ./enabled_configs.sh

for config in "${configs[@]}"; do
    arch=$(basename "$config" .toml)
    echo "CONFIGURING $arch"
    uv run petsc-ci-emu arch configure "$config"
done
