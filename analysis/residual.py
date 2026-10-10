import glob
import os
import subprocess

import pandas as pd

TARGET_WIRE = 1058   # 1000-byte target plus 58 bytes of AEAD tag, UDP, IPv4 and Ethernet


def wire_sizes(pcap):
    cmd = ["tshark", "-r", pcap, "-Y", "udp.srcport==4433", "-T", "fields", "-e", "frame.len"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.split()
    return [int(x) for x in out if x.isdigit()]


agg = {}
for pcap in sorted(glob.glob("data/*/*/flow_*.pcap")):
    _, condition, profile, _ = pcap.split(os.sep)
    data_pkts = [x for x in wire_sizes(pcap) if x >= 200]   # server packets only, so padded requests never enter, and bare acks skipped
    if not data_pkts:
        continue
    a = agg.setdefault((condition, profile), [0, 0])
    a[0] += sum(1 for x in data_pkts if x > TARGET_WIRE)
    a[1] += len(data_pkts)

if not agg:
    raise SystemExit("no captures found under data/, run this before data is cleared")

rows = [{"condition": c, "profile": p, "frac_above_target": round(above / total, 4)}
        for (c, p), (above, total) in sorted(agg.items())]
pd.DataFrame(rows).to_csv("output/residual_above_target.csv", index=False)
print(pd.DataFrame(rows).to_string(index=False))
