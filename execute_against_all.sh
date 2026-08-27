#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

configs=(
    "petsc-configs/ci-clang-double-complex-0.toml"
    "petsc-configs/ci-clang-double-real-0.toml"
    "petsc-configs/ci-clang-double-real-1.toml"
    "petsc-configs/ci-macOS-single-complex-0.toml"
    "petsc-configs/ci-macOS-single-complex-1.toml"
    "petsc-configs/ci-macOS-single-real-0.toml"
    # "petsc-configs/ci-clang-single-complex-0.toml"
    # "petsc-configs/ci-clang-single-complex-1.toml"
    # "petsc-configs/ci-clang-single-real-0.toml"
    # "petsc-configs/ci-gcc-double-complex-0.toml"
    # "petsc-configs/ci-gcc-double-real-0.toml"
    # "petsc-configs/ci-gcc-double-real-1.toml"
    # "petsc-configs/ci-gcc-float128-real-0.toml"
    # "petsc-configs/ci-gcc-single-complex-0.toml"
    # "petsc-configs/ci-gcc-single-complex-1.toml"
    # "petsc-configs/ci-gcc-single-real-0.toml"
    # "petsc-configs/ci-nvcc-complex.toml"
    # "petsc-configs/ci-nvcc-real.toml"
)
command="${1:-}"
add="${2:-}"
echo $command
for config in "${configs[@]}"; do
    arch=$(basename "$config" .toml)
    echo "RUNNING $command against $arch"
    uv run petsc-ci-emu arch "$command" "$config" "$add"
done
