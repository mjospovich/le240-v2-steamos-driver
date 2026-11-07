"""Cooler configuration. The window writes this file; the service reloads it."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .lights import MODE_BY_ID, format_color, parse_color

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "cooler.json"

DEFAULT_FAN = [[35, 40], [55, 45], [75, 50], [95, 55]]
DEFAULT_PUMP = [[40, 50], [60, 55], [80, 60], [100, 65]]


@dataclass
class Config:
    enabled: bool = True
    tau_s: float = 45
    deadband_c: float = 2
    hold_s: float = 8
    slew_pct_s: float = 8
    pump_min_rpm: int = 2500
    fan_curve: list = field(default_factory=lambda: [list(p) for p in DEFAULT_FAN])
    pump_curve: list = field(default_factory=lambda: [list(p) for p in DEFAULT_PUMP])
    roles: dict = field(default_factory=dict)
    fixed: dict = field(default_factory=dict)
    lights: dict = None

    def normalized(self):
        return Config(
            enabled=self.enabled is not False,
            tau_s=_clamp_float(self.tau_s, 0, 300),
            deadband_c=_clamp_float(self.deadband_c, 0, 20),
            hold_s=_clamp_float(self.hold_s, 0, 120),
            slew_pct_s=_clamp_float(self.slew_pct_s, 1, 100),
            pump_min_rpm=_clamp_int(self.pump_min_rpm, 0, 5000),
            fan_curve=_curve(self.fan_curve, DEFAULT_FAN),
            pump_curve=_curve(self.pump_curve, DEFAULT_PUMP),
            roles={str(k): v for k, v in dict(self.roles).items() if v in ("fan", "pump")},
            fixed=_fixed(self.fixed),
            lights=_lights(self.lights),
        )


def load():
    if not CONFIG_PATH.exists():
        cfg = Config()
        save(cfg)
        return cfg
    try:
        raw = json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return Config()
    if not isinstance(raw, dict):
        return Config()
    known = Config.__dataclass_fields__
    values = {key: raw[key] for key in known if key in raw}
    return Config(**values).normalized()


def save(cfg):
    cfg = cfg.normalized()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(cfg), indent=2) + "\n"
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(payload)
    tmp.replace(CONFIG_PATH)
    return cfg


def _fixed(value):
    out = {}
    if isinstance(value, dict):
        for key, duty in value.items():
            out[str(key)] = _clamp_float(duty, 0, 100)
    return out


def _curve(value, fallback):
    points = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                points.append([
                    round(_clamp_float(item[0], 0, 110), 1),
                    round(_clamp_float(item[1], 0, 100), 1),
                ])
    return points or [list(p) for p in fallback]


def _clamp_float(value, low, high):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


def _clamp_int(value, low, high):
    return int(_clamp_float(value, low, high))


def _lights(value):
    if not isinstance(value, dict):
        return None
    mode = str(value.get("mode", "static"))
    if mode not in MODE_BY_ID:
        mode = "static"
    red, green, blue = parse_color(value.get("color", "00c8be"))
    zone = str(value.get("zone", "all"))
    return {
        "mode": mode,
        "color": format_color(red, green, blue),
        "speed": int(_clamp_float(value.get("speed", 50), 0, 100)),
        "zone": zone,
    }
