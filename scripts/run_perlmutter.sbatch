#!/usr/bin/env bash
# SBATCH script for running the VMM benchmarks on Perlmutter (CPU)
# Usage: sbatch scripts/run_perlmutter.sbatch

# Request resources — adjust account/partition/constraint as needed for your allocation
# These settings are conservative; change --time, --account, and --constraint to match your allocation
# Example interactive allocation: salloc --nodes=1 --qos=interactive --time=00:30:00 --constraint=cpu --account=m3930
# Then run: sbatch scripts/run_perlmutter.sbatch
#
#SBATCH --job-name=vmm-bench
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --time=00:30:00
#SBATCH --account=m3930
#SBATCH --partition=cpu
#SBATCH --output=perlmutter-bench-%j.out

set -euo pipefail

echo "Starting VMM benchmark job on $(hostname)"
date

# Load modules (adjust based on your environment)
module purge
module load gcc
module load openblas
module load cmake
module load python

ROOT="$(pwd)"
BUILD_DIR="${ROOT}/build"

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "Configuring build in $BUILD_DIR"
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . -j 16

cd "$ROOT"

# Set sensible defaults for the runner
export OPENBLAS_NUM_THREADS=1
REPEATS=${REPEATS:-3}
THREADS=${THREADS:-"1,4,16,64"}
OUT=${OUT:-results-perlmutter.csv}

echo "Running collect_results.sh: REPEATS=$REPEATS THREADS=$THREADS OUT=$OUT"
REPEATS=$REPEATS THREADS="$THREADS" OUT="$OUT" BUILD_DIR="$BUILD_DIR" ./scripts/collect_results.sh

echo "Generating plots"
python3 scripts/plot_results.py --csv "$OUT" --outdir scripts/plots

echo "Done"
date
