# Version 1.1 prints weighted F1 in place of accuracy and F1. The calculation,
# the printed layout and output/robustness.csv are unchanged from v1.0.
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

df = pd.read_csv("features/dataset.csv")
feat = [c for c in df.columns if c not in ("condition", "profile")]
conds = [c for c in ["none", "fixed", "random", "mtu"] if c in set(df["condition"])]
allseeds = [int(s) for s in open("scripts/seeds.txt") if s.strip()]


def run(seeds, make):
    out = {}
    for c in conds:
        sub = df[df["condition"] == c]
        X, y = sub[feat].values, sub["profile"].to_numpy()
        sc = []
        for s in seeds:
            Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30,
                                                  random_state=s, stratify=y)
            sc.append(f1_score(yte, make(s).fit(Xtr, ytr).predict(Xte),
                               average="weighted"))
        out[c] = float(np.mean(sc))
    return out


variations = [
    ("RF 200 leaf2, 10 seeds", allseeds[:10],
     lambda s: RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                      random_state=s, n_jobs=-1)),
    ("RF 100 leaf1, 30 seeds", allseeds,
     lambda s: RandomForestClassifier(n_estimators=100, min_samples_leaf=1,
                                      random_state=s, n_jobs=-1)),
    ("HistGB, 30 seeds", allseeds,
     lambda s: HistGradientBoostingClassifier(random_state=s)),
]

rows, failed = [], []
for name, seeds, make in variations:
    f1 = run(seeds, make)
    red = {c: f1["none"] - f1[c] for c in conds if c != "none"}
    order = sorted(red, key=red.get, reverse=True)
    signs_ok = all(v > 0 for v in red.values())
    print(f"=== {name} ===")
    print("  mean weighted F1     " + "   ".join(f"{c}={f1[c]:.3f}" for c in conds))
    print("  drop in weighted F1  " + "   ".join(f"{c}={red[c]:+.3f}" for c in order))
    print(f"  order {order}  all_positive={signs_ok}")
    if not signs_ok:
        failed.append(name)
    rows.append({"variation": name, **{f"wf1_{c}": round(f1[c], 4) for c in conds},
                 "order": "|".join(order), "all_positive": signs_ok})

pd.DataFrame(rows).to_csv("output/robustness.csv", index=False)
print("\nwrote output/robustness.csv")
if failed:
    print(f"ROBUSTNESS FAIL: a strategy did not lower weighted F1 under {failed}")
    sys.exit(1)
print("ROBUSTNESS OK: every strategy lowers weighted F1 under every variation")
