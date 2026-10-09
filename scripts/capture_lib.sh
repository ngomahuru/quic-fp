# Wait until dumpcap has opened the file and written its header, so the 
# capture is live before the client starts.
wait_capture_ready() {
  local f="$1" i
  for i in $(seq 1 200); do
    [ -s "$f" ] && return 0
    sleep 0.1
  done
  echo "capture did not start: $f"
  return 1
}

# Wait one second after the capture file has stopped growing, to make sure 
# that the flow has finished before stopping the capture.
wait_capture_settled() {
  local f="$1" prev=-1 cur quiet=0 i
  for i in $(seq 1 150); do
    cur=$(stat -c%s "$f" || echo 0)
    if [ "$cur" = "$prev" ]; then
      quiet=$((quiet + 1))
      [ "$quiet" -ge 5 ] && return 0
    else
      quiet=0
    fi
    prev=$cur
    sleep 0.2
  done
  echo "capture never settled after 30s: $f"
  return 1
}
