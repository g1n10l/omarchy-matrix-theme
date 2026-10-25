#!/bin/bash
set -euo pipefail
systemctl --user daemon-reload
systemctl --user restart owed.service
ready=false
for attempt in {1..50}; do
  if owe status >/dev/null 2>&1; then ready=true; break; fi
  sleep 0.2
done
if ! "$ready"; then
  echo 'Nie można połączyć się z owed. Sprawdź: journalctl --user -u owed.service -n 40' >&2
  exit 1
fi
owe reload-config
python3 "$HOME/.config/omarchy/themes/matrix/animation-source/daylight.py"
owe refresh
owe resume
owe always-animate on
owe render-restart
systemctl --user enable --now matrix-daylight.timer matrix-lamp-flicker.timer
systemctl --user restart matrix-daylight.timer matrix-lamp-flicker.timer
# Give the restarted renderer time to load the selected video.
for attempt in {1..50}; do
  state="$(owe render-status 2>/dev/null || true)"
  if printf '%s' "$state" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(not(d.get("ready") and d.get("outputs",0)>0 and not d.get("error")))' 2>/dev/null; then
    owe status
    owe render-status
    exit 0
  fi
  sleep 0.2
done
echo 'Odtwarzacz nie potwierdził gotowości. Sprawdź: owe render-status' >&2
exit 1
