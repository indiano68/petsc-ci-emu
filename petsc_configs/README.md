# CI PETSc configurations

These files are an extraction of every distinct `./configure` invocation that
`.github/workflows/main.yml` can produce, one flag per line. They are a
record of the CI's build surface, meant for diffing and for reproducing a CI
build locally against a PETSc checkout on Linux — they are **not** adapted
for any other platform. For macOS-adapted configs, see
`petsc-configures/configs/` instead.

## Naming

- `arch-packages.conf` — the `main` job's "Configure vanilla PETSc with
  external packages" step (main.yml, "Configure vanilla PETSc with external
  packages"), used to build MUMPS/f2cblaslapack once and cache them as
  `PETSC_ARCH=arch-packages`.
- `ci-<compiler>-<precision>-<type>-<int64>.conf` — one entry per surviving
  `(compiler, PRECISION, TYPE, INT64)` combination in the `main` job's
  "Build and test with PETSc and SLEPc" step's nested loop
  (`compiler ∈ {gcc, clang}`, `PRECISION ∈ {single, double, float128}`,
  `TYPE ∈ {real, complex}`, `INT64 ∈ {0, 1}`), skipping the combinations the
  workflow itself skips. 13 files: 7 for gcc, 6 for clang (clang never runs
  the `float128` precision).
- `nvcc-real.conf` / `nvcc-complex.conf` — the `nvcc` (self-hosted CUDA) job's
  two configure invocations.

## Usage

Each file is a flat list of `./configure` arguments, one per line:

```sh
PETSC_ARCH=arch-ci ./configure $(tr '\n' ' ' < config/ci-gcc-double-real-0.conf)
```

## Caveats

- Paths are literal, assuming a sibling checkout layout matching the CI:
  `PETSC_DIR=~/Workspace/LIP6-SWE/repos/petsc` and this repo checked out at
  `~/Workspace/LIP6-SWE/repos/hpddm-dev`. Adjust `--download-hpddm=`,
  `--with-mumps-lib=`, `--with-f2cblaslapack-dir=`, and `LDFLAGS=` if your
  checkout lives elsewhere.
- System library paths (`/usr/lib/x86_64-linux-gnu/*`, `mpicc.openmpi`, etc.)
  are Debian/Ubuntu-specific — these configs are extracted as-is from the
  `ubuntu-24.04` runner and won't resolve on macOS or other distros.
- The two `nvcc-*.conf` files contain a `${LOGIN}` placeholder standing in
  for the `${{ secrets.LOGIN }}` GitHub Actions secret (the self-hosted
  runner's login), which cannot be resolved outside the workflow.
- `arch-packages.conf` intentionally pins
  `--download-f2cblaslapack=https://joliv.et/petsc/pkg/f2cblaslapack-3.8.0.q2.tar.gz`
  rather than letting PETSc fetch it from upstream (worked around a
  downstream f2cblaslapack availability issue).
