#!/bin/bash
# Installs the board sensor module, the cooler service, and the menu entry.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="${SUDO_USER:-$USER}"
OWNER_HOME="$(getent passwd "$OWNER" | cut -d: -f6)"

printf 'blacklist nct6683\n' > /etc/modprobe.d/nct6683.conf
if [ ! -f "$ROOT/driver/nct6687d/nct6687.ko" ]; then
  "$ROOT/bin/build-module.sh"
fi
modprobe -r nct6683 || true
if ! grep -q '^nct6687 ' /proc/modules; then
  insmod "$ROOT/driver/nct6687d/nct6687.ko"
fi

sed "s|@ROOT@|$ROOT|g" "$ROOT/etc/le240.service" > /tmp/le240.service
sed "s|@ROOT@|$ROOT|g" "$ROOT/etc/le240-control.desktop" > /tmp/le240-control.desktop
install -D -m 0644 /tmp/le240.service /etc/systemd/system/le240.service
install -o "$OWNER" -g "$OWNER" -D -m 0644 /tmp/le240-control.desktop \
  "$OWNER_HOME/.local/share/applications/le240-control.desktop"
install -o "$OWNER" -g "$OWNER" -d "$OWNER_HOME/.local/bin"
ln -sfn "$ROOT/bin/le240-control" "$OWNER_HOME/.local/bin/le240-control"

systemctl daemon-reload
systemctl enable le240.service
systemctl reset-failed le240.service || true
systemctl restart le240.service
systemctl --no-pager --full status le240.service
