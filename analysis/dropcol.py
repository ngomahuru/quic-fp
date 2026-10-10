import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

df = pd.read_csv("features/dataset.csv")
feat = [c for c in df.columns if c not in ("condition", "profile")]
SIZE = [f for f in feat if f.startswith("size_") or f in ("total_bytes", "bytes_per_sec")]
nosize = [f for f in feat if f not in SIZE]
seeds = [int(line) for line in open("scripts/seeds.txt") if line.strip()]
conds = ["none", "fixed", "random", "mtu"]
print(f"size block ({len(SIZE)}): {SIZE}")
print(f"retained ({len(nosize)}): {nosize}")


def fit_f1(cols, sub, s):
    X, y = sub[cols].values, sub["profile"].to_numpy()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30,
                                          random_state=s, stratify=y)
    m = RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                               random_state=s, n_jobs=-1).fit(Xtr, ytr)
    return f1_score(yte, m.predict(Xte), average="weighted")


rows, contrib = [], {}
for cnd in conds:
    sub = df[df["condition"] == cnd]
    full = [fit_f1(feat, sub, s) for s in seeds]
    nosz = [fit_f1(nosize, sub, s) for s in seeds]
    gaps = [a - b for a, b in zip(full, nosz)]
    contrib[cnd] = float(np.mean(gaps))
    rows.append({"condition": cnd,
                 "full_wf1": round(float(np.mean(full)), 4),
                 "nosize_wf1": round(float(np.mean(nosz)), 4),
                 "dropcol_size_contribution": round(contrib[cnd], 4),
                 "std": round(float(np.std(gaps, ddof=1)), 4)})
pd.DataFrame(rows).to_csv("output/dropcol.csv", index=False)
print(pd.DataFrame(rows).to_string(index=False))
print("\nfall in size-block contribution from none:")
for cnd in ["fixed", "random", "mtu"]:
    print(f"  none -> {cnd}: {contrib['none'] - contrib[cnd]:+.4f}")
