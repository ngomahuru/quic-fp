import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

detail = json.load(open("output/run_detail.json"))
classes = detail["classes"]
conds = list(detail["conf"].keys())

TITLES = {"none": "No Padding", "fixed": "Fixed-Size",
          "random": "Random-Size", "mtu": "MTU-Aligned"}

for c in conds:
    cm = np.mean(np.array(detail["conf"][c]), axis=0)
    pd.DataFrame(cm, index=classes, columns=classes).to_csv(
        f"output/confusion_{c}_counts.csv")
    cm = cm / cm.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots()
    im = ax.imshow(cm, vmin=0, vmax=1)
    ax.set_xticks(range(len(classes)), classes, rotation=45, ha="right")
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title(TITLES.get(c, c))
    fig.colorbar(im, ax=ax, label="Share of true class")
    fig.tight_layout()
    fig.savefig(f"output/confusion_{c}.png", dpi=150)
    plt.close(fig)

pd.DataFrame([{"condition": c,
               **{k: np.mean([r[k] for r in detail["perclass"][c]]) for k in classes}}
              for c in conds]).to_csv("output/perclass_f1.csv", index=False)
print("wrote confusion figures, confusion counts, and per-class scores")
