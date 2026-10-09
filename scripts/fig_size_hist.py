import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("runs/phase8_sizes.csv")
df = df[df["frame_len"] >= 200]

for other, colour in [("fixed", "#e69f00"), ("random", "#009e73"), ("mtu", "#7b61a8")]:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, cond, c in zip(axes, ["none", other], ["#0072b2", colour]):
        d = df[df["condition"] == cond]["frame_len"]
        ax.hist(d, bins=range(200, 1500, 25), color=c)
        ax.set_title(f"{cond}  (n={len(d)})", fontsize=10)
        ax.set_xlabel("on-wire packet size, bytes")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("packet count")
    fig.tight_layout()
    fig.savefig(f"runs/size_hist_{other}.png", dpi=200)
    plt.close(fig)
    print(f"wrote runs/size_hist_{other}.png  (none against {other})")
