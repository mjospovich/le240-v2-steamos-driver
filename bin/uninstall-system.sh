#!/bin/bash
# Removes the cooler service and the sensor module autoload.
# Leaves this directory in place. Fan curves return to the BIOS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="${SUDO_USER:-$USER}"
OWNER_HOME="$(getent passwd "$OWNER" | cut -d: -f6)"

systemctl disable --now le240.service || true
rm -f /etc/systemd/system/le240.service
rm -f /etc/modules-load.d/nct6683.conf
rm -f /etc/modprobe.d/nct6683.conf
systemctl daemon-reload
modprobe -r nct6687 || true
modprobe -r nct6683 || true

rm -f "$OWNER_HOME/.local/share/applications/le240-control.desktop"
LINK="$OWNER_HOME/.local/bin/le240-control"
if [ -L "$LINK" ] && [ "$(readlink -f "$LINK")" = "$ROOT/bin/le240-control" ]; then
  rm -f "$LINK"
fi

echo "Removed the LE240 service, module blacklist, menu entry, and launcher."
