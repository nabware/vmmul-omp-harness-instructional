#!/usr/bin/env bash
# Simple runner to execute the benchmark binaries and produce a CSV of results.
# Usage:
#   REPEATS=1 THREADS="1,4,16,64" OUT=results.csv ./scripts/collect_results.sh

set -euo pipefail

REPEATS=${REPEATS:-1}
THREADS=${THREADS:-"1,4,16,64"}
OUT=${OUT:-results.csv}
BUILD_DIR=${BUILD_DIR:-build}

echo "# impl,threads,trial,N,seconds,mflops" > "$OUT"

run_and_parse() {
  local impl="$1"
  local threads="$2"
  local trial="$3"
  local binpath="$BUILD_DIR/$impl"

  if [ ! -x "$binpath" ]; then
    echo "Warning: $binpath not found or not executable" >&2
    return
  fi

  # Ensure BLAS single-threaded for fair comparison unless user overrides
  export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}

  # For OpenMP binary, set OMP_NUM_THREADS
  if [[ "$impl" == "benchmark-openmp" ]]; then
    export OMP_NUM_THREADS="$threads"
  else
    export OMP_NUM_THREADS=1
  fi

  # Run the benchmark, capture stdout
  local out
  out=$(cd "$BUILD_DIR" && ./"$impl")

  # Parse lines like: N=16384  time=0.171885 s  MFLOP/s=3123.44
  echo "$out" | awk -v impl="$impl" -v threads="$threads" -v trial="$trial" '
    /^N=/ {
      # split by spaces
      for(i=1;i<=NF;i++) {
        if ($i ~ /^N=/) { split($i,a,"="); N=a[2]; }
        if ($i ~ /^time=/) { split($i,b,"="); time=b[2]; }
        if ($i ~ /^MFLOP\/s=/) { split($i,c,"="); mflop=c[2]; }
      }
      if (N!="" && time!="" && mflop!="") {
        printf("%s,%s,%s,%s,%s,%s\n", impl, threads, trial, N, time, mflop);
      }
    }' >> "$OUT"
}

echo "Running benchmarks (REPEATS=$REPEATS) -> $OUT"

IMPLS=(benchmark-basic benchmark-vectorized benchmark-blas benchmark-openmp)

for impl in "${IMPLS[@]}"; do
  if [[ "$impl" == "benchmark-openmp" ]]; then
    # loop thread list
    IFS=',' read -r -a tarr <<< "$THREADS"
    for trial in $(seq 1 $REPEATS); do
      for t in "${tarr[@]}"; do
        echo "Running $impl (threads=$t) trial $trial..."
        run_and_parse "$impl" "$t" "$trial"
      done
    done
  else
    for trial in $(seq 1 $REPEATS); do
      echo "Running $impl (threads=1) trial $trial..."
      run_and_parse "$impl" 1 "$trial"
    done
  fi
done

echo "Done. Results saved to $OUT"
