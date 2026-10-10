# Table captions for the analysis output, shared by analyse_run.sh and
# rebuild.sh so the two print identical text and editing is done in one place.
#
# Prints a titled caption naming the source file, then the table.
# Numbers are rounded off to six significant figures for display only. The
# table files on disk keep the precision their scripts write, full for most
# tables and four decimals for dropcol.csv and residual_above_target.csv, and
# those files are what the reproduction verdict compares.
# Usage: caption "Title" "one-line description" path/to/table.csv
caption() {
  printf '\n=== %s: %s ===\n%s\n\n' "$(basename "$3")" "$1" "$2"
  python3 -c "
import sys, pandas as pd
pd.set_option('display.width', 250)
print(pd.read_csv(sys.argv[1]).to_string(index=False, float_format='%.6g'))
" "$3"
}

# Captions tables in the given directory.
# Usage: captions_for path/to/dir
# residual_above_target.csv is skipped when absent, since it is produced
# only by a full run, which reads the raw captures. A rebuild from the
# committed dataset has no captures and hence no residual table.
captions_for() {
  local d="$1"
  caption "Classifier accuracy under each padding condition" \
    "Weighted F1 averaged over 30 splits, with its standard deviation and the observed 2.5th and 97.5th percentiles. Establishes the classifier's accuracy with no defence applied, and how far each padding strategy pushes it towards 0.20, the score given by a pure guess across five equal classes." \
    "$d/f1_summary.csv"
  caption "Accuracy lost to each padding strategy, tested for significance" \
    "Fall in weighted F1 against the unpadded baseline, with corrected intervals and Holm-adjusted p values. This is the study's primary measurement, showing how much fingerprinting accuracy each PADDING strategy removes and whether the correction for overlapping splits establishes the drop as real and not an artefact of which flows landed in each test split." \
    "$d/comparison.csv"
  caption "Padding strategies compared with each other" \
    "Each pair compared directly, marked separable when the Holm-adjusted test finds a real difference, where a negative gap shows the first strategy removed less accuracy than the second. Decides whether the three strategies rank against each other or whether the gaps between them sit inside the noise." \
    "$d/pairwise.csv"
  caption "Accuracy for each traffic class" \
    "F1 for each traffic class under each condition, averaged over the 30 splits. Shows whether padding protects every class equally or leaves some identifiable while flattening the rest." \
    "$d/perclass_f1.csv"
  caption "How much the classifier relies on packet size" \
    "Weighted F1 of the classifier trained on all 16 features and of the classifier trained without the nine size features, the gap between them averaged over the 30 splits, and the spread of the per-split gaps. Links the accuracy fall to its cause, since a padding strategy erasing the size signal should also shrink the gap, in the same direction." \
    "$d/dropcol.csv"
  if [ -f "$d/residual_above_target.csv" ]; then
    caption "Packets above the padding target" \
      "Share of server packets of 200 bytes or more already larger than the fixed strategy's target, pooled over each class's flows. Explains why fixed padding leaves part of the size distribution intact, since padding never shrinks packets already above the target." \
      "$d/residual_above_target.csv"
  fi
}
