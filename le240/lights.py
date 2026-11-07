"""Addressable lighting through the motherboard LED controller."""

VID = 0x26CE
PID = 0x01A2
UNAVAILABLE = 0x1E

MODES = (
    ("off", "Off", 0x00, False, False),
    ("static", "Static", 0x01, True, False),
    ("breathing", "Breathing", 0x02, True, True),
    ("strobe", "Strobe", 0x03, True, True),
    ("spectrum", "Spectrum", 0x04, False, True),
    ("wave", "Wave", 0x07, False, True),
    ("rainbow", "Rainbow", 0x0E, False, True),
)
MODE_BY_ID = {item[0]: item for item in MODES}
MODE_BY_CODE = {item[2]: item for item in MODES}

ZONE_NAMES = {
    0: "RGB 1",
    1: "RGB 2",
    2: "ARGB 1",
    3: "ARGB 2",
    4: "Chipset",
    5: "I/O",
    6: "PCB",
    7: "ARGB 3",
}


def speed_byte(percent):
    percent = max(0.0, min(100.0, float(percent)))
    return int(round(255 - percent / 100.0 * 255))


def speed_percent(value):
    return int(round((255 - int(value)) / 255 * 100))


def parse_color(text):
    raw = str(text).strip().lstrip("#")
    if len(raw) != 6:
        return (0, 200, 190)
    try:
        return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return (0, 200, 190)


def format_color(red, green, blue):
    return f"{int(red) & 255:02x}{int(green) & 255:02x}{int(blue) & 255:02x}"


def zone_packet(zone, mode, red, green, blue, speed, rgb=True):
    first, second = (red, green) if rgb else (green, red)
    buf = bytearray(65)
    buf[1] = 0x10
    buf[3] = int(zone) & 255
    buf[4] = int(mode) & 255
    buf[5] = int(first) & 255
    buf[6] = int(second) & 255
    buf[7] = int(blue) & 255
    buf[8] = int(speed) & 255
    buf[9] = 0xFF
    buf[10] = 0x01
    return bytes(buf)


def commit_packet():
    buf = bytearray(65)
    buf[1] = 0x12
    return bytes(buf)


def header_packet(kind):
    buf = bytearray(65)
    buf[1] = 0x14
    buf[3] = int(kind) & 255
    return bytes(buf)


def read_zone_packet(zone):
    buf = bytearray(65)
    buf[1] = 0x11
    buf[3] = int(zone) & 255
    return bytes(buf)


def parse_zones(counts, present, swap):
    zones = []
    for index, count in enumerate(list(counts)[:8]):
        if count == UNAVAILABLE or not ((int(present) >> index) & 1):
            continue
        zones.append({
            "id": index,
            "name": ZONE_NAMES.get(index, f"Channel {index + 1}"),
            "leds": int(count),
            "rgb": bool((int(swap) >> index) & 1),
        })
    return zones


def parse_zone_state(report, rgb):
    mode_code = report[4]
    first, second, blue = report[5], report[6], report[7]
    red, green = (first, second) if rgb else (second, first)
    known = MODE_BY_CODE.get(mode_code)
    return {
        "mode": known[0] if known else "static",
        "color": format_color(red, green, blue),
        "speed": speed_percent(report[8]),
    }


class Controller:
    def __init__(self, dev):
        self.dev = dev

    @classmethod
    def open(cls):
        import hid
        return cls(hid.Device(vid=VID, pid=PID))

    def close(self):
        self.dev.close()

    def _xfer(self, packet):
        self.dev.write(packet)
        data = self.dev.read(64, timeout=500)
        return bytes(data) if data else b""

    def zones(self):
        counts = self._xfer(header_packet(0x02))
        present = self._xfer(header_packet(0x01))
        swap = self._xfer(header_packet(0x03))
        if len(counts) < 12 or len(present) < 5 or len(swap) < 5:
            return []
        return parse_zones(counts[4:12], present[4], swap[4])

    def state(self, zone):
        report = self._xfer(read_zone_packet(zone["id"]))
        if len(report) < 9:
            return None
        return parse_zone_state(report, zone["rgb"])

    def apply(self, mode_id, color, speed, zone_id):
        zones = self.zones()
        if str(zone_id) == "all":
            chosen = zones
        else:
            chosen = [zone for zone in zones if str(zone["id"]) == str(zone_id)]
        spec = MODE_BY_ID.get(str(mode_id))
        if not chosen or spec is None:
            return False
        red, green, blue = parse_color(color)
        encoded = speed_byte(speed)
        for zone in chosen:
            self._xfer(zone_packet(zone["id"], spec[2], red, green, blue, encoded, zone["rgb"]))
        try:
            self._xfer(commit_packet())
        except OSError:
            pass
        return True


def apply_saved(lights):
    if not lights:
        return False
    try:
        ctrl = Controller.open()
    except Exception:
        return False
    try:
        return ctrl.apply(lights.get("mode"), lights.get("color"), lights.get("speed", 50), lights.get("zone", "all"))
    except Exception:
        return False
    finally:
        ctrl.close()
