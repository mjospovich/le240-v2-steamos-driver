#!/bin/bash
# Builds nct6687 for this kernel. PWM on the NCT6686D is read-only in the
# in-tree nct6683 module, so speed control needs this one.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KVER="$(uname -r)"
SRC="$ROOT/driver/nct6687d"
KO="$SRC/nct6687.ko"

if [ ! -d "/lib/modules/$KVER/build" ]; then
  pacman-key --populate holo archlinux
  # Present in the keyring, but not marked trusted, so official package
  # signatures are rejected until it is locally signed.
  pacman-key --lsign-key 889B5EBDDD505A683621900DAF1D2199EF0A3CCF
  pacman -S --needed --noconfirm linux-neptune-72-headers base-devel
fi

if [ ! -f "$SRC/nct6687.c" ]; then
  rm -rf "$SRC"
  git clone --depth 1 https://github.com/Fred78290/nct6687d.git "$SRC"
fi

make -C "$SRC" clean
make -C "$SRC" KVER="$KVER"
test -f "$KO"
echo "Built $KO"
