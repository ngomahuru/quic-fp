from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

f1 = pd.read_csv("output/f1_by_seed.csv", index_col=0)
for c in ["none", "fixed", "random", "mtu"]:
    if c not in f1.columns:
        raise SystemExit(f"condition {c} missing from f1_by_seed.csv")

base = f1["none"].values
J = len(base)                                     # resampling rounds, J in Nadeau and Bengio
TEST_RATIO, TRAIN_RATIO = 0.30, 0.70
correction = 1.0 / J + TEST_RATIO / TRAIN_RATIO   # variance inflation factor, Nadeau and Bengio; n_test/n_train expressed as proportions, since the splits are proportional
dfree = J - 1
tcrit = stats.t.ppf(0.975, dfree)


def corrected(d):
    """Mean, corrected standard error, t and two-sided p for per-seed differences."""
    mean_d = float(d.mean())
    se = float(np.sqrt(d.var(ddof=1) * correction))
    if se == 0:
        raise SystemExit("per-seed differences have zero variance, corrected test undefined")
    t_stat = mean_d / se
    return mean_d, se, t_stat, float(2 * stats.t.sf(abs(t_stat), dfree))


rows, pv = [], []
for s in ["fixed", "random", "mtu"]:
    d = base - f1[s].values                       # per-seed reduction in weighted F1
    mean_d, se, t_stat, p = corrected(d)
    rows.append({"strategy": s, "mean_wf1": float(f1[s].mean()),
                 "mean_reduction": mean_d,
                 "ci_low": mean_d - tcrit * se, "ci_high": mean_d + tcrit * se,
                 "t": t_stat, "p_raw": p})
    pv.append(p)
rej, p_holm, _, _ = multipletests(pv, alpha=0.05, method="holm")
for r, ph, x in zip(rows, p_holm, rej):
    r["p_holm"] = ph
    r["significant"] = bool(x)
t = pd.DataFrame(rows).sort_values("mean_reduction", ascending=False)
t.to_csv("output/comparison.csv", index=False)
print(f"correction factor {correction:.4f}  (naive 1/J {1 / J:.4f})")
print(t.to_string(index=False))

# Pairwise corrected test between strategies. Each strategy's per-seed
# reduction shares the same seed and the same baseline, so the difference of
# two reductions is a paired per-seed quantity taking the same correction.
# Holm controls the three comparisons as one family, and a pair counts as
# separable only when its Holm-adjusted p value is below 0.05. reduction_gap >
# 0 means strategy a reduced accuracy MORE than b.
prows, ppv = [], []
for a, b in combinations(["fixed", "random", "mtu"], 2):
    d = f1[b].values - f1[a].values
    mean_d, se, t_stat, p = corrected(d)
    prows.append({"pair": f"{a} vs {b}", "reduction_gap": mean_d,
                  "ci_low": mean_d - tcrit * se, "ci_high": mean_d + tcrit * se,
                  "t": t_stat, "p_raw": p})
    ppv.append(p)
prej, pp_holm, _, _ = multipletests(ppv, alpha=0.05, method="holm")
for r, ph, x in zip(prows, pp_holm, prej):
    r["p_holm"] = ph
    r["separable"] = bool(x)
pt = pd.DataFrame(prows).sort_values("reduction_gap", key=abs, ascending=False)
pt.to_csv("output/pairwise.csv", index=False)
print("\npairwise corrected comparison of reductions")
print(pt.to_string(index=False))
