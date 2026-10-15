#!/usr/bin/env bash
# Rebuilds all reported tables and figures from the committed feature dataset,
# then compares the rebuilt tables against the committed originals.
#
# Version 1.1 adds the robustness table and the four confusion-count tables to
# the verdict, so eleven tables are compared in place of six.
#
# Writes only to venv/, output/, rebuild/ and features/dataset.csv. output/ and
# rebuild/ are cleared and recreated on every run, these four paths do not go in
# the archive, hence the unpacked package is left unchanged.
#
# All paths are relative, so this works anywhere the package was unpacked.
set -euo pipefail
cd "$(dirname "$0")/.."

cat <<'BANNER'

 =================================================================================
        Measuring the Effectiveness of QUIC PADDING Frames Against Machine
                           Learning Traffic Fingerprinting
 =================================================================================

 A QUIC client and server generate five classes of web traffic that carry the same
 number of packets and differ mainly in the size of each packet. Each class is
 collected four times, once unpadded and then under each of three QUIC PADDING
 strategies, MTU-Aligned, Random and Fixed. A Random Forest Classifier then
 attempts to identify each captured flow class, and the drop in its weighted F1 
 measures how much of the size signal each strategy removes.

 This package rebuilds all reported tables and figures from the included dataset, 
 reruns the robustness sweep, and compares eleven tables against the originals. It 
 takes a few minutes.

 This reproducibility package requires a freshly installed Ubuntu 24.04 and will
 not work on any other operating system. It installs any missing software, with
 your permission, using sudo.

 Inside the unpacked folder, the package writes to these four paths:

 +----------------------+--------------------------------------------+
 | PATH                 | CONTENTS                                   |
 +----------------------+--------------------------------------------+
 | venv/                | The Python libraries it installs, about    |
 |                      | 500 megabytes                              |
 +----------------------+--------------------------------------------+
 | output/              | Scratch space for the analysis scripts,    |
 |                      | cleared on every run                       |
 +----------------------+--------------------------------------------+
 | rebuild/run_1/       | The rebuilt tables and figures, compared   |
 |                      | against the originals                      |
 +----------------------+--------------------------------------------+
 | features/dataset.csv | A working copy of the dataset in           |
 |                      | runs/run_1/                                |
 +----------------------+--------------------------------------------+

 Remove all four when you are done with command:

    rm -rf rebuild output venv features/dataset.csv

BANNER

. /etc/os-release
[ "${ID:-}" = "ubuntu" ] && [ "${VERSION_ID:-}" = "24.04" ] || {
  echo "This package targets Ubuntu 24.04. Detected: ${PRETTY_NAME:-unknown}."
  echo "Stopping."
  exit 1; }

# Activate ./venv if present and no environment is already active. The folder
# exists on any run after the first.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f venv/bin/activate ]; then
  set +u; . venv/bin/activate; set -u
fi

echo "Checking prerequisites."
missing_pkgs=""
missing_py=""
blocked=0

command -v python3 >/dev/null || missing_pkgs="$missing_pkgs python3"
command -v sha256sum >/dev/null || missing_pkgs="$missing_pkgs coreutils"
[ -f venv/bin/activate ] || missing_pkgs="$missing_pkgs python3-venv python3-pip"

if command -v python3 >/dev/null; then
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' \
    || { echo "STOP: Python 3.12 or newer is required."; blocked=1; }
  for m in numpy pandas sklearn scipy statsmodels matplotlib; do
    python3 -c "import importlib.util as u, sys; sys.exit(0 if u.find_spec('$m') else 1)" \
      || missing_py="$missing_py $m"
  done
else
  missing_py=" numpy pandas sklearn scipy statsmodels matplotlib"
fi

for f in runs/dataset_manifest.txt runs/run_1/dataset.csv scripts/seeds.txt \
         scripts/caption.sh scripts/fig_run.py analysis/requirements.txt \
         analysis/evaluate.py analysis/stats.py analysis/figures.py \
         analysis/dropcol.py analysis/robustness.py features/extract.py \
         runs/run_1/robustness.csv runs/run_1/confusion_none_counts.csv \
         runs/run_1/confusion_fixed_counts.csv runs/run_1/confusion_random_counts.csv \
         runs/run_1/confusion_mtu_counts.csv; do
  [ -f "$f" ] || { echo "STOP: $f is missing, the package is incomplete."; blocked=1; }
done
[ "$blocked" -eq 0 ] || { echo; echo "Cannot continue."; exit 1; }

if [ -n "$missing_pkgs" ] || [ -n "$missing_py" ]; then
  echo
  echo "The following are missing:"
  [ -n "$missing_pkgs" ] && echo " system packages:$missing_pkgs"
  [ -n "$missing_py" ] && echo " python libraries:$missing_py"
  echo
  echo "Installing them changes this machine and needs your sudo password."
  printf "Install and continue? [yes/no]: "
  read -r reply
  case "$(printf '%s' "$reply" | tr '[:upper:]' '[:lower:]')" in
    y|yes) ;;
    *) echo "Nothing was installed. Stopping."; exit 1 ;;
  esac

  if [ -n "$missing_pkgs" ]; then
    echo
    echo "Installing system packages."
    sudo -v
    while sudo fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock >/dev/null 2>&1; do
      echo "Waiting for Ubuntu's automatic updater to finish."
      sleep 10
    done
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip coreutils
  fi

  echo
  echo "Building the Python environment."
  [ -d venv ] || python3 -m venv venv
  set +u; . venv/bin/activate; set -u
  pip install --upgrade pip
  pip install -r analysis/requirements.txt
fi

python3 -c "import numpy, pandas, sklearn, scipy, statsmodels, matplotlib" \
  || { echo "STOP: the analysis libraries are still unavailable."; exit 1; }
echo "Prerequisites satisfied."

if [ -f analysis/python_version.txt ]; then
  recorded=$(cat analysis/python_version.txt)
  running=$(python3 --version)
  [ "$recorded" = "$running" ] || {
    echo "NOTE: the analysis was recorded under $recorded, this machine runs $running."
    echo " The tables should still match. If one differs, look here first."; }
fi

rm -rf rebuild output
mkdir -p rebuild/run_1 output features

echo
echo "Verifying the included dataset."
sha256sum -c runs/dataset_manifest.txt

echo
echo "Rebuilding. This takes a few minutes."
cp runs/run_1/dataset.csv features/dataset.csv
python3 analysis/evaluate.py > /dev/null
python3 analysis/stats.py > /dev/null
python3 analysis/figures.py > /dev/null
python3 analysis/dropcol.py > /dev/null
cp output/comparison.csv output/pairwise.csv output/f1_summary.csv \
   output/f1_by_seed.csv output/perclass_f1.csv output/dropcol.csv rebuild/run_1/
cp output/confusion_*.png output/confusion_*_counts.csv rebuild/run_1/
python3 scripts/fig_run.py rebuild/run_1 rebuild/run_1 > /dev/null

# The captions come from scripts/caption.sh, the same file analyse_run.sh
# uses. Version 1.1 rewords them to name weighted F1 and F1 in place of
# accuracy, so their wording differs from the archived tables_readable.txt
# while every number stays the same. The residual table is absent, since it
# needs the raw captures.
. scripts/caption.sh
captions_for rebuild/run_1

# The robustness sweep reruns the comparison under three model variations.
# robustness.py exits with an error when a strategy fails to lower weighted F1,
# so it runs inside an if, which keeps set -e from stopping the script before
# the verdict prints.
echo
echo "=== Robustness Gate ==="
echo "Repeats the comparison under three variations, the study's forest on ten"
echo "seeds, the default forest on thirty seeds and gradient boosting on thirty"
echo "seeds. Passes only if every strategy lowers weighted F1 under all three."
echo
if ! python3 analysis/robustness.py | tee rebuild/run_1/robustness.txt; then
  echo " ROBUSTNESS GATE FAILED, see above"
fi
cp output/robustness.csv rebuild/run_1/

echo
echo "############ REPRODUCTION VERDICT ############"
fail=0
for t in comparison.csv pairwise.csv f1_summary.csv f1_by_seed.csv \
         dropcol.csv perclass_f1.csv robustness.csv \
         confusion_none_counts.csv confusion_fixed_counts.csv \
         confusion_random_counts.csv confusion_mtu_counts.csv; do
  # Numeric columns must agree within 1e-9, which allows for floating-point
  # differences between processors. Text columns must match exactly.
  if python3 - "$t" <<'PY'
import sys, numpy as np, pandas as pd
a = pd.read_csv(f"runs/run_1/{sys.argv[1]}")
b = pd.read_csv(f"rebuild/run_1/{sys.argv[1]}")
n = a.select_dtypes("number").columns
ok = (a.shape == b.shape and list(a.columns) == list(b.columns)
      and a.drop(columns=n).equals(b.drop(columns=n))
      and np.allclose(a[n], b[n], rtol=0, atol=1e-9))
sys.exit(0 if ok else 1)
PY
  then
    echo " MATCH $t"
  else
    echo " DIFFERS $t"
    fail=1
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "### ALL 11 TABLES REPRODUCE ###"
else
  echo "### SOME TABLES DIFFER, see above ###"
  echo " the usual cause is a library version resolving differently."
  echo " check with: pip freeze | diff - analysis/requirements.txt"
fi

cat <<'MSG'

 Figures should be compared manually. Matplotlib output can differ byte for byte
 between versions and platforms through font rendering alone, so a checksum would
 fail on figures looking identical. Open each pair side by side:

    runs/run_1/f1_baseline.png      rebuild/run_1/f1_baseline.png
    runs/run_1/reduction.png        rebuild/run_1/reduction.png
    runs/run_1/confusion_none.png   rebuild/run_1/confusion_none.png
    runs/run_1/confusion_fixed.png  rebuild/run_1/confusion_fixed.png
    runs/run_1/confusion_random.png rebuild/run_1/confusion_random.png
    runs/run_1/confusion_mtu.png    rebuild/run_1/confusion_mtu.png

 The confusion counts behind the four matrices are compared in the verdict above,
 so a MATCH there confirms the numbers each figure draws.

 The Wireshark screenshots in runs/run_1_figures/ cannot be rebuilt. They show a
 decrypted PADDING frame in the same packet as a real HTTP/3 response, which needs
 both the encrypted packet payloads and the TLS session keys. Neither is included,
 the captures are large and regenerable, and key material is kept out of the
 repository as a matter of practice, whatever it protects. The Wireshark
 screenshots can only be made by redoing the experiment according to the
 instructions in the dissertation.

 Rerun the rebuild at any time with:
    ./scripts/rebuild.sh

 Remove everything this run produced with:
    cd ~ && rm -rf /tmp/quic-fp-repro

### FINISHED ###

MSG
