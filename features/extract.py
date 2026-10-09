import csv
import glob
import os
import subprocess
import sys

import numpy as np


def packets(pcap):
    cmd = ["tshark", "-r", pcap, "-Y", "udp.port==4433", "-T", "fields",
           "-e", "frame.time_epoch", "-e", "frame.len"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()
    times, sizes = [], []
    for line in out:
        parts = line.split("\t")
        if len(parts) == 2 and parts[0] and parts[1]:
            times.append(float(parts[0]))
            sizes.append(int(parts[1]))
    return times, sizes


def features(times, sizes):
    sizes = np.array(sizes, dtype=float)
    times = np.array(times, dtype=float)
    iat = np.diff(times) if len(times) > 1 else np.array([0.0])
    duration = (times[-1] - times[0]) if len(times) > 1 else 1e-9
    total = float(sizes.sum())
    return {
        "size_mean": sizes.mean(), "size_std": sizes.std(),
        "size_min": sizes.min(), "size_max": sizes.max(),
        "size_median": np.median(sizes),
        "size_p25": np.percentile(sizes, 25), "size_p75": np.percentile(sizes, 75),
        "iat_mean": iat.mean(), "iat_std": iat.std(),
        "iat_min": iat.min(), "iat_max": iat.max(), "iat_median": np.median(iat),
        "burst_ratio": float(np.mean(iat < 0.001)),
        "total_bytes": total,
        "bytes_per_sec": total / duration if duration > 0 else 0.0,
        "packet_count": float(len(sizes)),
    }


files = sorted(glob.glob("data/*/*/flow_*.pcap"))
if not files:
    sys.exit("no capture files found under data/, nothing to extract")

rows = []
for i, pcap in enumerate(files, 1):
    _, condition, profile, _ = pcap.split(os.sep)
    times, sizes = packets(pcap)
    if len(sizes) >= 2:
        row = features(times, sizes)
        row["condition"] = condition
        row["profile"] = profile
        rows.append(row)
    if i % 100 == 0 or i == len(files):
        print(f"{i}/{len(files)} pcaps", flush=True)

if not rows:
    sys.exit(f"read {len(files)} captures but none yielded 2 or more packets")
skipped = len(files) - len(rows)
if skipped:
    print(f"WARNING: {skipped} of {len(files)} captures skipped as too short", flush=True)

with open("features/dataset.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("wrote", len(rows), "rows")
