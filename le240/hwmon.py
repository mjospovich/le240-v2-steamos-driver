"""Board fan controller via the NCT668x hwmon device."""

from pathlib import Path

PUMP_RPM = 2200


def find_chip():
    root = Path("/sys/class/hwmon")
    if not root.exists():
        return None
    for device in root.glob("hwmon*"):
        name = _text(device / "name")
        if name and name.startswith("nct668"):
            return device
    return None


def channels(device):
    found = []
    if device is None:
        return found
    for index in range(1, 9):
        rpm_path = device / f"fan{index}_input"
        pwm_path = device / f"pwm{index}"
        if not rpm_path.exists() and not pwm_path.exists():
            continue
        enable = device / f"pwm{index}_enable"
        found.append({
            "index": index,
            "label": _text(device / f"fan{index}_label") or f"Header {index}",
            "rpm": _int(rpm_path),
            "pwm": _int(pwm_path),
            "pwm_path": pwm_path if pwm_path.exists() else None,
            "enable_path": enable if enable.exists() else None,
            "enable": _int(enable) if enable.exists() else None,
            "writable": _writable(pwm_path),
        })
    return found


def connected(channel):
    rpm = channel.get("rpm")
    return isinstance(rpm, int) and rpm > 0


def role_for(channel, roles):
    override = roles.get(str(channel["index"]))
    if override:
        return override
    if "pump" in (channel.get("label") or "").lower():
        return "pump"
    rpm = channel.get("rpm")
    if isinstance(rpm, int) and rpm >= PUMP_RPM:
        return "pump"
    return "fan"


def duty_to_pwm(percent):
    return int(round(max(0.0, min(100.0, float(percent))) / 100.0 * 255))


def set_mode(channel, manual):
    path = channel["enable_path"]
    if path is None:
        return False
    try:
        path.write_text("1\n" if manual else "2\n")
        return True
    except OSError:
        return False


def set_duty(channel, percent):
    path = channel["pwm_path"]
    if path is None:
        return False
    try:
        path.write_text(f"{duty_to_pwm(percent)}\n")
        return True
    except OSError:
        return False


def cpu_temp_c():
    root = Path("/sys/class/hwmon")
    if not root.exists():
        return None
    for device in root.glob("hwmon*"):
        if _text(device / "name") == "k10temp":
            raw = _int(device / "temp1_input")
            if raw is None:
                return None
            return raw / 1000.0
    return None


def _writable(path):
    try:
        return path.exists() and path.stat().st_mode & 0o222
    except OSError:
        return False


def _text(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _int(path):
    text = _text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None
