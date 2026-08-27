#!/usr/bin/env bash
set -euo pipefail

configs=(
    "petsc-configs/ci-clang-double-complex-0.toml"
    "petsc-configs/ci-clang-double-real-0.toml"
    "petsc-configs/ci-clang-double-real-1.toml"
    "petsc-configs/ci-clang-single-complex-0.toml"
    "petsc-configs/ci-clang-single-complex-1.toml"
    "petsc-configs/ci-clang-single-real-0.toml"
)
