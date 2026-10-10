import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "runs/run_1"
dest = sys.argv[2] if len(sys.argv) > 2 else src
CONDS = ["none", "fixed", "random", "mtu"]

s = pd.read_csv(f"{src}/f1_summary.csv", index_col=0).loc[CONDS]
fig, ax = plt.subplots(figsize=(6, 4))
ax.errorbar(range(len(CONDS)), s["wf1_mean"].values,
            yerr=[(s["wf1_mean"] - s["wf1_pct_2_5"]).values,
                  (s["wf1_pct_97_5"] - s["wf1_mean"]).values],
            fmt="o", ms=6, capsize=5, lw=1.2, color="#1a1a1a")
ax.axhline(0.20, ls="--", lw=1, color="0.45")
ax.text(-0.45, 0.215, "chance, five classes", fontsize=9, color="0.35", ha="left")
ax.set_xticks(range(len(CONDS)), CONDS)
ax.set_xlim(-0.5, len(CONDS) - 0.5)
ax.set_ylim(0, 1.05)
ax.set_ylabel("weighted F1")
ax.set_xlabel("padding condition")
ax.set_title("Weighted F1 by condition\n"
             "bars span the 2.5th to 97.5th percentile of 30 splits", fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", lw=0.5, color="0.9")
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{dest}/f1_baseline.png", dpi=200)
plt.close(fig)

c = pd.read_csv(f"{src}/comparison.csv").set_index("strategy")
c = c.loc[[o for o in ["fixed", "random", "mtu"] if o in c.index]]
fig, ax = plt.subplots(figsize=(6, 4))
ax.errorbar(range(len(c)), c["mean_reduction"].values,
            yerr=[(c["mean_reduction"] - c["ci_low"]).values,
                  (c["ci_high"] - c["mean_reduction"]).values],
            fmt="o", ms=6, capsize=5, lw=1.2, color="#2a78d6")
ax.axhline(0, ls="--", lw=1, color="0.45")
ax.set_xticks(range(len(c)), c.index)
ax.set_xlim(-0.5, len(c) - 0.5)
ax.set_ylabel("reduction in weighted F1")
ax.set_xlabel("padding strategy")
ax.set_title("Accuracy reduction\nbars are the corrected 95% interval", fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", lw=0.5, color="0.9")
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{dest}/reduction.png", dpi=200)
plt.close(fig)
print(f"wrote {dest}/f1_baseline.png and {dest}/reduction.png")
