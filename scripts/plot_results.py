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

def plot_mflops(data, Ns, outdir):
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

    ax.set_xscale('log', base=2)
    ax.set_xlabel('Problem size N (log2)')
    ax.set_ylabel('MFLOP/s (median across trials)')
    ax.set_title('VMM Benchmark: MFLOP/s vs N')
    ax.grid(True, which='both', ls='--', alpha=0.4)
    ax.legend(fontsize='small')
    fig.tight_layout()
    outpath = os.path.join(outdir, 'mflops.png')
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
        plot_mflops(data, Ns, args.outdir)
        plot_speedup_openmp(data, Ns, args.outdir)
    except Exception:
        # fallback: show ASCII summary
        ascii_summary(data, Ns)
        print('\n(Install matplotlib to produce PNG files)')
        sys.exit(0)

if __name__ == '__main__':
    main()
