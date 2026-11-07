# Sensor module

PWM control needs [nct6687d](https://github.com/Fred78290/nct6687d) (GPL-2.0). The in-tree `nct6683` driver exposes the NCT6686D with read-only PWM.

`bin/build-module.sh` clones that repository into `driver/nct6687d/` and builds `nct6687.ko` for the running kernel. The clone is not committed here; it is created on install.
