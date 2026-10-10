#!/usr/bin/env bash
# Usage: ./scripts/analyse_run.sh [run-number]
# Extracts features, runs the analysis and size-reliance measures, archives 
# the run, prints the archived tables with captions, then runs the 
# robustness gate. Archiving happens before the captions and the gate, 
# hence a failure at either still leaves every table on disk for diagnosis.
set -uo pipefail
RUN="${1:-1}"
cd ~/quic-fp

# Every script and input the driver needs is checked before any step runs,
# since a missing item would otherwise surface only when the driver reaches
# it, after the long steps before it.
missing=0
for f in evaluate stats figures dropcol residual robustness; do
  [ -f "analysis/$f.py" ] || { echo "MISSING: analysis/$f.py"; missing=1; }
done
[ -f features/extract.py ] || { echo "MISSING: features/extract.py"; missing=1; }
[ -f scripts/caption.sh ]  || { echo "MISSING: scripts/caption.sh"; missing=1; }
[ -f scripts/seeds.txt ]   || { echo "MISSING: scripts/seeds.txt"; missing=1; }
[ "$missing" -eq 0 ] || { echo "STOP: create the missing items before running"; exit 1; }

# Raw captures must be present. residual.py reads them directly.
caps=$(find data -name 'flow_*.pcap' | wc -l)
[ "$caps" -gt 0 ] || { echo "STOP: no captures under data/, nothing to analyse"; exit 1; }
echo "found $caps captures under data/"

source analysis/venv/bin/activate
set -e

dest="runs/run_${RUN}"
mkdir -p "$dest"

printf '\n=== RUN %s Feature Extraction ===\n\n' "$RUN"
python3 features/extract.py

# Every analysis script prints its own tables, and the same tables are 
# printed again with captions during archiving. Only lines appearing
# nowhere else are shown here, the training progress, the correction
# factor, the feature split behind the size-block measure and the falls in
# size-block contribution. The rest goes to output/, scratch space
# overwritten by the next run.
printf '\n=== RUN %s Analysis ===\n\n' "$RUN"
python3 analysis/evaluate.py \
  | grep --line-buffered -vE '^(none|fixed|random|mtu)[[:space:]]|^[[:space:]]+wf1_mean'
python3 analysis/stats.py > output/stats.log
grep '^correction factor' output/stats.log || true
python3 analysis/figures.py
python3 analysis/dropcol.py > output/dropcol.log
grep -E '^(size block|retained|fall in size-block|  none ->)' output/dropcol.log || true
python3 analysis/residual.py > output/residual.log

printf '\n=== RUN %s Archiving ===\n' "$RUN"
cp output/comparison.csv output/pairwise.csv output/f1_summary.csv \
   output/f1_by_seed.csv output/perclass_f1.csv output/dropcol.csv \
   output/residual_above_target.csv features/dataset.csv "$dest/"
cp output/confusion_*.png output/confusion_*_counts.csv "$dest/"
cp "runs/run_${RUN}_manifest.txt" "$dest/manifest.txt" || true

# Reads from $dest and not output/, so the tables printed and the tables
# archived are the same files.
. scripts/caption.sh
captions_for "$dest" | tee "$dest/tables_readable.txt"

printf '\n=== RUN %s Verification ===\n' "$RUN"
set +e
fail=0

printf '\n=== Robustness Gate ===\nRepeats the accuracy comparison between the unpadded baseline and the three padding strategies under three variations. The first is the forest used in the study on ten seeds instead of thirty, testing whether the finding depends on the seed count. The second is the default scikit-learn forest of 100 trees at leaf size one, smaller and deeper than the forest used in the study. The third is a gradient boosting classifier, which learns by correcting its own errors instead of averaging independent trees. Passes only if every strategy still lowers accuracy under all three variations.\n\n'
python3 analysis/robustness.py    | tee "$dest/robustness.txt"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail=1
cp output/robustness.csv "$dest/"

printf '\n'
echo "archived run $RUN into $dest"
ls -1 "$dest"
printf '\n'
if [ "$fail" -ne 0 ]; then
  echo "### RUN $RUN VERIFICATION FAILED, see the messages above ###"
  exit 1
fi
echo "### RUN $RUN VERIFIED AND ARCHIVED ###"
