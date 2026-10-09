import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

df = pd.read_csv("features/dataset.csv")
feat = [c for c in df.columns if c not in ("condition", "profile")]
with open("scripts/seeds.txt") as fh:
    seeds = [int(s) for s in fh if s.strip()]
conds = [c for c in ["none", "fixed", "random", "mtu"] if c in set(df["condition"])]
classes = sorted(df["profile"].unique())

f1 = {c: [] for c in conds}
conf = {c: [] for c in conds}
perclass = {c: [] for c in conds}

for i, c in enumerate(conds, 1):
    print(f"[{i}/{len(conds)}] condition {c}, training {len(seeds)} seeds", flush=True)
    sub = df[df["condition"] == c]
    X = sub[feat].values
    y = sub["profile"].to_numpy()
    for s in seeds:
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30,
                                              random_state=s, stratify=y)
        clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                     random_state=s, n_jobs=-1).fit(Xtr, ytr)
        pred = clf.predict(Xte)
        f1[c].append(f1_score(yte, pred, average="weighted"))
        conf[c].append(confusion_matrix(yte, pred, labels=classes).tolist())
        rep = classification_report(yte, pred, labels=classes,
                                    output_dict=True, zero_division=0)
        perclass[c].append({k: rep[k]["f1-score"] for k in classes})

# Per-seed scores. stats.py reads this file, since the corrected test needs 
# the 30 paired values instead of the summary in f1_summary.csv, which loses 
# the pairing between conditions on the same split.
pd.DataFrame(f1, index=seeds).to_csv("output/f1_by_seed.csv")

with open("output/run_detail.json", "w") as fh:
    json.dump({"features": feat, "classes": classes,
               "conf": conf, "perclass": perclass}, fh)

# The last two columns are the 2.5th and 97.5th percentiles of the 30 split
# scores, so they describe the observed spread. They are NOT confidence
# intervals, they do not say anything about the true value and ignore the 
# overlap between splits. The corrected intervals are computed in stats.py.
summary = pd.DataFrame({c: [np.mean(f1[c]), np.std(f1[c], ddof=1),
                            np.percentile(f1[c], 2.5), np.percentile(f1[c], 97.5)]
                        for c in conds}, index=["wf1_mean", "wf1_std",
                                                "wf1_pct_2_5", "wf1_pct_97_5"]).T
summary.to_csv("output/f1_summary.csv", index_label="condition")
print(summary)
