# Cooling

`le240.service` reads `config/cooler.json` once a second and writes PWM on connected headers.

## Headers

A header is shown while its tachometer reports a speed. The pump is the header whose name contains `pump`. Any other header at or above 2200 rpm is also treated as the pump. `roles` overrides that by header index, with values `fan` or `pump`.

Manual duty is `fixed`, a map of header index to percent. A header listed there holds that duty and does not follow a curve.

## Temperature

The curve input is an exponential average of CPU package temperature (`k10temp` `temp1_input`).

| Field | Default | Effect |
|---|---|---|
| `tau_s` | 45 | smoothing time constant, seconds |
| `deadband_c` | 2 | hysteresis band, °C |
| `hold_s` | 8 | time the average must stay outside the band before the target changes, seconds |
| `slew_pct_s` | 8 | maximum duty change, percent per second |

Shipped `config/cooler.json` uses a mild mid-duty fan and pump curve (about 40–55% fans, 50–65% pump). Edit it in the app or replace the points.

The first sample takes the curve immediately. Later samples smooth, hold, then slew.

## Pump

`pump_min_rpm` defaults to 2500, the bottom of the LE240 V2 pump range (2500–3400 rpm). Duty is not reduced while that header reads at or below the limit. A higher duty is still applied. A reading of 0 rpm is an absent tachometer.

## Curves

`fan_curve` and `pump_curve` are lists of `[°C, duty %]`, from two to eight points. Duty is linear between points and clamped to the end points outside the range. The graph in the window edits these lists.

## Firmware curve

`enabled` set to false, or stopping the service, writes `pwmN_enable` `2` on headers the service had set to manual. The firmware curve resumes.
