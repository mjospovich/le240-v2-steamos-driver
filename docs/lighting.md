# Lighting

The radiator and pump LEDs use the motherboard addressable headers. The controller is USB `26ce:01a2`, a 64-byte HID device.

`lights` in `config/cooler.json` is omitted until the Lighting page is used. The service writes it when the object changes. The window also writes it as the color field moves.

| Field | Values |
|---|---|
| `mode` | `off`, `static`, `breathing`, `strobe`, `spectrum`, `wave`, `rainbow` |
| `color` | `rrggbb` |
| `speed` | 0–100. 100 is fastest |
| `zone` | `all`, or a channel id |

`all` writes every channel the controller reports as present. On the LE240 headers those ids are 2 and 3.

Color and speed are ignored by the modes that do not use them. Off, spectrum, wave, and rainbow ignore color. Off and static ignore speed.

## Report

Byte 0 of the host buffer is the report id `0x00`.

| Offset | Write `0x10` |
|---|---|
| 1 | `0x10` |
| 3 | channel id |
| 4 | mode code |
| 5–7 | red, green, blue when the channel order bit is set, otherwise green, red, blue |
| 8 | speed. 0 is fastest, 255 is slowest |
| 9 | `0xff` |
| 10 | `0x01` |

Mode codes: `0x00` off, `0x01` static, `0x02` breathing, `0x03` strobe, `0x04` spectrum, `0x07` wave, `0x0e` rainbow.

`0x12` stores the result in the controller.

`0x14` reads a header. Argument `0x02` is the LED counts, `0x01` is the presence mask, `0x03` is the color-order mask. Counts are eight bytes from offset 4, in channel order. A count of `0x1e`, or a clear presence bit, means that channel is absent. `0x11` with the channel id in byte 3 reads the current mode, color, and speed.
