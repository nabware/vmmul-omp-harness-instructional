#!/usr/bin/env python3
"""
Simple plotting helper for the VMM benchmark results CSV produced by
scripts/collect_results.sh

Usage:
  python3 scripts/plot_results.py --csv results.csv --outdir scripts/plots

Produces two PNG files in the output directory:
  - mflops.png      : MFLOP/s vs N for each implementation/thread combo
  - speedup_openmp.png : Speedup vs threads for benchmark-openmp (largest N)

The script prefers matplotlib; if it's not available it will print a short
ASCII summary and exit with a non-zero status.
"""
import argparse
import csv
import math
import os
import sys
from collections import defaultdict

def read_results(path):
    rows = []
    with open(path, newline='') as f:
        reader = csv.reader(line for line in f if not line.lstrip().startswith('#'))
        for r in reader:
            if len(r) < 6:
                continue
            impl, threads, trial, N, seconds, mflops = r[:6]
            try:
                rows.append({
                    'impl': impl.strip(),
                    'threads': int(threads),
                    'trial': int(trial),
                    'N': int(N),
                    'seconds': float(seconds),
                    'mflops': float(mflops),
                })
            except ValueError:
                # skip malformed lines
                continue
    return rows

def median(lst):
    s = sorted(lst)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return s[mid]
    return 0.5 * (s[mid-1] + s[mid])

def prepare_series(rows):
    # Build mapping: (impl,threads) -> N -> list of mflops
    data = defaultdict(lambda: defaultdict(list))
    Ns = set()
    for r in rows:
        key = (r['impl'], r['threads'])
        data[key][r['N']].append(r['mflops'])
        Ns.add(r['N'])
    return data, sorted(Ns)

# def plot_mflops(data, Ns, outdir):
def plot_mflops_basic_vectorized_blas(data, Ns, outdir):
    """
    Chart 1: MFLOP/s vs N for benchmark-basic, benchmark-vectorized, benchmark-blas (t=1)
    """
    import matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8,5))
    impls = ["benchmark-basic", "benchmark-vectorized", "benchmark-blas"]
    colors = ["#1f77b4", "#e377c2", "#ff7f0e"]
    for impl, color in zip(impls, colors):
        key = (impl, 1)
        nmap = data.get(key, {})
        xs = []
        ys = []
        for N in Ns:
            med = median(nmap.get(N, []))
            if med is None:
                continue
            xs.append(N)
            ys.append(med)
        if xs:
            ax.plot(xs, ys, marker='o', label=impl.replace("benchmark-", "").capitalize(), color=color)
    ax.set_xlabel('Problem size N')
    ax.set_ylabel('MFLOP/s')
    ax.set_title('MFLOP/s: Basic, Vectorized, BLAS')
    ax.grid(True, ls='--', alpha=0.4)
    ax.legend()
    fig.tight_layout()
    outpath = os.path.join(outdir, 'mflops_basic_vectorized_blas.png')
    fig.savefig(outpath)
    print('Wrote', outpath)

def plot_speedup_openmp_vs_n(data, Ns, outdir):
    """
    Chart 2: Speedup vs N for OpenMP at 1,4,16,64 threads
    """
    import matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8,5))
    thread_list = [1,4,16,64]
    for t in thread_list:
        key = ("benchmark-openmp", t)
        nmap = data.get(key, {})
        xs = []
        ys = []
        for N in Ns:
            base = median(data.get(("benchmark-openmp", 1), {}).get(N, []))
            val = median(nmap.get(N, []))
            if base and val:
                xs.append(N)
                ys.append(val/base)
        if xs:
            ax.plot(xs, ys, marker='o', label=f"threads={t}")
    ax.set_xlabel('Problem size N')
    ax.set_ylabel('Speedup vs threads=1')
    ax.set_title('OpenMP Speedup vs N (static scheduling)')
    ax.grid(True, ls='--', alpha=0.4)
    ax.legend()
    fig.tight_layout()
    outpath = os.path.join(outdir, 'speedup_openmp_vs_n.png')
    fig.savefig(outpath)
    print('Wrote', outpath)

def plot_mflops_best_openmp_vs_blas(data, Ns, outdir):
    """
    Chart 3: MFLOP/s vs N for best OpenMP config and serial BLAS
    """
    import matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8,5))
    # Best OpenMP: for each N, pick max MFLOP/s among thread counts
    best_omp = []
    blas = []
    for N in Ns:
        best = None
        for t in [1,4,16,64]:
            val = median(data.get(("benchmark-openmp", t), {}).get(N, []))
            if val is not None:
                if best is None or val > best:
                    best = val
        best_omp.append(best if best is not None else float('nan'))
        blas_val = median(data.get(("benchmark-blas", 1), {}).get(N, []))
        blas.append(blas_val if blas_val is not None else float('nan'))
    ax.plot(Ns, best_omp, marker='o', label='Best OpenMP (threads=16)', color='#2ca02c')
    ax.plot(Ns, blas, marker='o', label='BLAS (serial)', color='#ff7f0e')
    ax.set_xlabel('Problem size N')
    ax.set_ylabel('MFLOP/s')
    ax.set_title('Best OpenMP vs BLAS (MFLOP/s)')
    ax.grid(True, ls='--', alpha=0.4)
    ax.legend()
    fig.tight_layout()
    outpath = os.path.join(outdir, 'mflops_best_openmp_vs_blas.png')
    fig.savefig(outpath)
    print('Wrote', outpath)
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        print('matplotlib not available; cannot create PNG plots.', file=sys.stderr)
        raise

    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8,5))

    for (impl, threads), nmap in sorted(data.items()):
        xs = []
        ys = []
        for N in Ns:
            med = median(nmap.get(N, []))
            if med is None:
                continue
            xs.append(N)
            ys.append(med)
        if not xs:
            continue
        label = f"{impl} (t={threads})"
        ax.plot(xs, ys, marker='o', label=label)

    ax.set_xscale('linear')
    ax.set_xlabel('Problem size N')
    ax.set_ylabel('MFLOP/s')
    ax.set_title('VMM Benchmark: MFLOP/s vs N')
    ax.grid(True, which='both', ls='--', alpha=0.4)
    ax.legend(fontsize='small')
    fig.tight_layout()
    outpath = os.path.join(outdir, 'mflops_abs.png')
    fig.savefig(outpath)
    print('Wrote', outpath)

def plot_speedup_openmp(data, Ns, outdir):
    # Focus on benchmark-openmp rows
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print('matplotlib not available; cannot create PNG plots.', file=sys.stderr)
        raise

    # choose largest N present
    if not Ns:
        print('No data to plot speedup', file=sys.stderr)
        return
    Nmax = max(Ns)

    # Collect median mflops for benchmark-openmp at Nmax for each thread count
    tmap = {}
    for (impl, threads), nmap in data.items():
        if impl != 'benchmark-openmp':
            continue
        med = median(nmap.get(Nmax, []))
        if med is not None:
            tmap[threads] = med

    if not tmap:
        print('No benchmark-openmp data found for N=', Nmax, file=sys.stderr)
        return

    threads = sorted(tmap.keys())
    base = tmap.get(1, None)
    if base is None:
        # if thread 1 not present, pick smallest thread count as baseline
        base = tmap[threads[0]]

    speedups = [tmap[t] / base for t in threads]

    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(threads, speedups, marker='o')
    ax.set_xlabel('Threads')
    ax.set_ylabel('Speedup (relative to threads={})'.format(1 if 1 in tmap else threads[0]))
    ax.set_title(f'OpenMP speedup (N={Nmax})')
    ax.grid(True, ls='--', alpha=0.4)
    fig.tight_layout()
    outpath = os.path.join(outdir, 'speedup_openmp.png')
    fig.savefig(outpath)
    print('Wrote', outpath)

def ascii_summary(data, Ns):
    # print a compact table if no plotting library
    print('\nSummary: median MFLOP/s per (impl,threads, N)')
    keys = sorted(data.keys())
    for impl, threads in keys:
        print(f'\n{impl} (t={threads})')
        nmap = data[(impl,threads)]
        for N in sorted(nmap.keys()):
            print(f'  N={N}: median={median(nmap[N]):.2f} MFLOP/s')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default='results.csv', help='CSV file to read (default: results.csv)')
    p.add_argument('--outdir', default='scripts/plots', help='Output directory for PNGs')
    args = p.parse_args()

    if not os.path.exists(args.csv):
        print('CSV file not found:', args.csv, file=sys.stderr)
        sys.exit(2)

    rows = read_results(args.csv)
    if not rows:
        print('No valid data found in', args.csv, file=sys.stderr)
        sys.exit(3)

    data, Ns = prepare_series(rows)

    try:
        plot_mflops_basic_vectorized_blas(data, Ns, args.outdir)
        plot_speedup_openmp_vs_n(data, Ns, args.outdir)
        plot_mflops_best_openmp_vs_blas(data, Ns, args.outdir)
    except Exception:
        # fallback: show ASCII summary
        ascii_summary(data, Ns)
        print('\n(Install matplotlib to produce PNG files)')
        sys.exit(0)

if __name__ == '__main__':
    main()
