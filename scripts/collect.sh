#!/usr/bin/env bash
set -euo pipefail

CONDITION="$1"                  # none | fixed | random | mtu
PAD_TARGET="${2:-1000}"         # used by the fixed strategy
N="${N:-150}"                   # flows per class
MIN_PKTS="${MIN_PKTS:-108}"     # reject truncated flows, ≈0.5 a healthy flow
MAX_PKTS="${MAX_PKTS:-432}"     # reject oversized flows, ≈2x a healthy flow
# MIN_PKTS and MAX_PKTS figures were determined using the calibration
# process from Appendix C.
PROFILES=(narrow bimodal spread right_skew left_skew)
MAX_RETRY=5

case "$CONDITION" in
  none)   STRAT="" ;;
  fixed|random|mtu) STRAT="$CONDITION" ;;
  *) echo "unknown condition $CONDITION"; exit 1 ;;
esac

PAD_STRATEGY="$STRAT" PAD_TARGET="$PAD_TARGET" docker compose up -d --force-recreate

# grep without -q reads all input, so docker compose logs never receives
# SIGPIPE and pipefail cannot turn a found line into a failed check.
ready=0
for i in $(seq 1 60); do
  if docker compose logs --since 30s quic-server | grep "server listening" >/dev/null; then
    ready=1; break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo "STOP: server did not start for condition $CONDITION"; exit 1; }

NETID=$(docker network inspect quic-fp_br-quic -f '{{.Id}}')
BRIDGE="br-${NETID:0:12}"

mkdir -p data
cond_total=$(( N * ${#PROFILES[@]} ))
flows_done=0
for profile in "${PROFILES[@]}"; do
  outdir="data/${CONDITION}/${profile}"
  mkdir -p "$outdir"
  for i in $(seq 1 "$N"); do
    f=$(printf "%s/flow_%03d.pcap" "$outdir" "$i")
    err="${f%.pcap}.err"

    attempt=0
    kept=1
    while :; do
      attempt=$((attempt + 1))
      # tshark's error output goes to a file so the drop check below can read
      # it.
      tshark -i "$BRIDGE" -f "udp port 4433" -w "$f" 2> "$err" &
      TS=$!
      # dumpcap writes the capture-file header the instant the interface is
      # live, so the client starts the moment the file is not empty.
      ready_cap=0
      for _ in $(seq 1 200); do
        if [ -s "$f" ]; then ready_cap=1; break; fi
        sleep 0.02
      done
      rc=0; docker exec quic-client python /app/client.py "$profile" || rc=$?
      sleep 1
      kill "$TS" || true
      wait "$TS" || true
      # A missing or unreadable capture counts as zero packets and triggers a
      # retry instead of ending the collection under set -e.
      pkts=$(capinfos -M -c "$f" 2>/dev/null | awk '/Number of packets/ {print $NF}') || pkts=0
      # tshark reports losses as "N packets dropped from <interface>".
      dropbad=$(grep -icE '[1-9][0-9]* packets? dropped' "$err" || true)

      if [ "$ready_cap" -eq 1 ] && [ "$rc" -eq 0 ] \
         && [ "${pkts:-0}" -ge "$MIN_PKTS" ] && [ "${pkts:-0}" -le "$MAX_PKTS" ] \
         && [ "$dropbad" -eq 0 ]; then
        rm -f "$err"; break
      fi
      if [ "$attempt" -ge "$MAX_RETRY" ]; then
        echo "FAILED $f (rc=$rc pkts=${pkts:-0} ready=$ready_cap drops=$dropbad)"
        rm -f "$f" "$err"; kept=0; break
      fi
      rm -f "$f"
    done

    flows_done=$((flows_done + 1))
    if [ "$kept" -eq 1 ]; then
      echo "${CONDITION},${profile},${i},${pkts:-0}" >> data/packet_counts.csv
      printf "captured %s (packets=%s)  [%s %d/%d]\n" \
        "$f" "${pkts:-0}" "$CONDITION" "$flows_done" "$cond_total"
    fi
  done
done
