#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import statistics


def parse_csv_times(csv_file: str) -> list[float]:
    times = []
    with open(csv_file, 'r') as f:
        content = f.read()
        delimiter = ',' if ',' in content else '\t'
        f.seek(0)
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if len(row) >= 3:
                try:
                    times.append(float(row[2]) / 1000.0)  # us -> ms
                except ValueError:
                    continue
    return times


def compute_percentiles(values: list[float], ps: list[float]) -> dict[float, float]:
    if not values:
        return {p: float('nan') for p in ps}
    sorted_vals = sorted(values)
    results = {}
    for p in ps:
        k = (len(sorted_vals) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        if f == c:
            results[p] = sorted_vals[int(k)]
        else:
            d0 = sorted_vals[f] * (c - k)
            d1 = sorted_vals[c] * (k - f)
            results[p] = d0 + d1
    return results


def main():
    ap = argparse.ArgumentParser(description="Compute latency percentiles for benchmark CSVs")
    ap.add_argument("benchmark_directory", help="Directory with h2_*.csv and h3_*.csv")
    ap.add_argument("--ps", default="50,90,95,99", help="Comma-separated percentiles (default: 50,90,95,99)")
    args = ap.parse_args()

    ps = [float(x) for x in args.ps.split(',') if x]

    files = [f for f in os.listdir(args.benchmark_directory) if f.endswith('.csv')]
    if not files:
        print("No CSV files found")
        sys.exit(1)

    print("condition,protocol," + ",".join([f"p{int(p)}_ms" for p in ps]))
    for f in sorted(files):
        path = os.path.join(args.benchmark_directory, f)
        values = parse_csv_times(path)
        perc = compute_percentiles(values, ps)
        if f.startswith('h2_'):
            proto = 'h2'
            cond = f[len('h2_'):-4]
        elif f.startswith('h3_'):
            proto = 'h3'
            cond = f[len('h3_'):-4]
        else:
            proto = 'unknown'
            cond = f[:-4]
        row = [cond, proto] + [f"{perc[p]:.2f}" if perc[p] == perc[p] else "" for p in ps]
        print(",".join(row))


if __name__ == "__main__":
    main()


