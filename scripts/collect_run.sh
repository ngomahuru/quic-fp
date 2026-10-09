#!/usr/bin/env bash
# Usage: ./scripts/collect_run.sh [run-number]
#
# The driver does not delete captures, if folder data/ is not empty it stops, 
# so clearing a previous collection is always a deliberate act minimising 
# deletion mistakes. Leftover captures would silently mix two collections into 
# one dataset, contaminating the results.
set -euo pipefail
RUN="${1:-1}"
cd ~/quic-fp

existing=$(find data -name 'flow_*.pcap' | wc -l)
if [ "$existing" -gt 0 ]; then
  echo "STOP: data/ holds $existing captures from a previous collection."
  echo "  Archive anything worth keeping, then start again with:"
  echo "    rm -rf data/* && ./scripts/collect_run.sh $RUN"
  exit 1
fi

avail=$(df --output=avail -BG ~ | tail -1 | tr -dc '0-9')
[ "${avail:-0}" -ge 3 ] || { echo "STOP: only ${avail}G free, need at least 3G"; exit 1; }

# The request count is compiled into the client image, so the host file and the
# image disagree whenever the image was not rebuilt after an edit. The image is
# what generates the traffic, so the manifest records its value.
host_nreq=$(awk '/^N_REQ = /{print $3}' client/client.py)
img_nreq=$(docker exec quic-client awk '/^N_REQ = /{print $3}' /app/client.py)
[ "$host_nreq" = "$img_nreq" ] || {
  echo "STOP: client/client.py sets N_REQ=$host_nreq but the running image carries $img_nreq."
  echo "  Rebuild the client image before collecting."
  exit 1; }

N="${N:-150}"
GT=$(( N * 5 * 4 ))          # flows per class x five classes x four conditions

mkdir -p data "runs/run_${RUN}"
{
  echo "run=$RUN"
  echo "started=$(date -Is)"
  echo "host=$(uname -srm)"
  echo "project_commit=$(git rev-parse --short HEAD || echo uncommitted)"
  echo "aioquic_upstream=$(cat scripts/aioquic_upstream_commit.txt)"
  echo "aioquic_padding=$(cat scripts/aioquic_padding_commit.txt)"
  echo "base_image=$(cat scripts/base_image_digest.txt)"
  echo "flows_per_class=$N"
  echo "n_req=$img_nreq"
} > "runs/run_${RUN}_manifest.txt"

start=$(date +%s)
echo "=== RUN $RUN collection starting, target $GT flows ==="

N=$N ./scripts/collect.sh none
N=$N ./scripts/collect.sh fixed 1000
N=$N ./scripts/collect.sh random
N=$N ./scripts/collect.sh mtu

if [ -f data/packet_counts.csv ]; then
  cp data/packet_counts.csv "runs/run_${RUN}/packet_counts.csv"
else
  echo "WARNING: no packet_counts.csv, every flow failed"
fi

have=$(find data -name 'flow_*.pcap' | wc -l)
elapsed=$(( ($(date +%s) - start) / 60 ))
{
  echo "finished=$(date -Is)"
  echo "elapsed_minutes=$elapsed"
  echo "flows_captured=$have"
} >> "runs/run_${RUN}_manifest.txt"
echo "#############################################################"
echo "#  RUN $RUN COLLECTION COMPLETE  $(date)"
echo "#  captured $have / $GT flows in ${elapsed} minutes"
echo "#############################################################"
