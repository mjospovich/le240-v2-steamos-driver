# Hardware

## Cooler

DeepCool LE240 V2.

| Connection | Interface | Specification |
|---|---|---|
| Pump | 4-pin PWM, tachometer | 2500–3400 rpm, 3.48 W |
| Radiator fans | 4-pin PWM, tachometer | 500–2100 rpm |
| Lighting | 5 V addressable, 3-pin | pump 2.8 W, each fan 2.1 W |

Fan and pump speed are the motherboard header tachometers. Lighting is a motherboard addressable header.

## Fan controller

Tachometers and PWM come from an NCT6686D. The in-tree `nct6683` module exposes that chip with read-only PWM. The installer clones [nct6687d](https://github.com/Fred78290/nct6687d) (GPL-2.0) into `driver/nct6687d/`, builds it for the running kernel, blacklists `nct6683`, and loads `nct6687.ko`. That clone is not part of this repository; see `driver/README.md`.

`pwmN_enable` is `1` for manual duty and `2` for the firmware curve.

CPU package temperature is hwmon `k10temp`, `temp1_input`.

## Lighting controller

USB `26ce:01a2`, HID, 64-byte interrupt reports on the motherboard LED controller. The addressable headers are channel ids 2 and 3.
