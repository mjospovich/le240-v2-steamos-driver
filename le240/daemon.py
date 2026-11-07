"""Apply fan and pump curves. Reloads config/cooler.json."""

import argparse
import signal
import sys
import time

from .config import load
from .curve import Thermal, hold_if_slow
from .lights import apply_saved
from .hwmon import (
    channels, connected, cpu_temp_c, duty_to_pwm, find_chip, role_for, set_duty, set_mode,
)


def main():
    parser = argparse.ArgumentParser(description="LE240 V2 fan and pump controller")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    if args.preview:
        preview()
    else:
        run()


def preview():
    cfg = load()
    chip = find_chip()
    print(f"controller {chip or 'not loaded'}")
    temp = cpu_temp_c()
    print(f"cpu {temp:.1f}C" if temp is not None else "cpu none")
    for channel in channels(chip):
        print(
            f"header {channel['index']} {role_for(channel, cfg.roles)} "
            f"{channel['rpm']} rpm pwm {channel['pwm']} writable {channel['writable']}"
        )


def run():
    service = Service()
    signal.signal(signal.SIGTERM, service.stop)
    signal.signal(signal.SIGINT, service.stop)
    print("LE240 controller", flush=True)
    service.loop()


class Service:
    def __init__(self):
        self.thermals = {}
        self.applied = {}
        self.manual = set()
        self.idle = set()
        self.running = True
        self.active = False
        self.lights_key = None

    def stop(self, *_args):
        self.release()
        sys.exit(0)

    def loop(self):
        while self.running:
            cfg = load()
            self._sync_lights(cfg)
            time.sleep(1.0)
            if not cfg.enabled:
                if self.active:
                    self.release()
                    print("control off", flush=True)
                self.active = False
                continue
            self.active = True
            self._apply(cfg, time.monotonic())

    def _sync_lights(self, cfg):
        if not cfg.lights:
            return
        key = tuple(sorted(cfg.lights.items()))
        if key == self.lights_key:
            return
        if apply_saved(cfg.lights):
            self.lights_key = key

    def _apply(self, cfg, now):
        temp = cpu_temp_c()
        chip = find_chip()
        if temp is None or chip is None:
            return
        for channel in channels(chip):
            if not connected(channel):
                self._release_one(channel)
                continue
            self.idle.discard(channel["index"])
            role = role_for(channel, cfg.roles)
            points = cfg.pump_curve if role == "pump" else cfg.fan_curve
            thermal = self.thermals.setdefault(channel["index"], _thermal(cfg))
            thermal.tau_s = cfg.tau_s
            thermal.deadband_c = cfg.deadband_c
            thermal.hold_s = cfg.hold_s
            thermal.slew_pct_s = cfg.slew_pct_s
            pinned = cfg.fixed.get(str(channel["index"]))
            if pinned is not None:
                duty = float(pinned)
            else:
                duty = thermal.step(temp, now, points)
            if role == "pump":
                duty = hold_if_slow(duty, self.applied.get(channel["index"], duty), channel["rpm"], cfg.pump_min_rpm)
            if not channel["writable"]:
                continue
            self._write(channel, duty)

    def _write(self, channel, duty):
        index = channel["index"]
        if channel.get("enable") != 1:
            set_mode(channel, True)
        self.manual.add(index)
        want = duty_to_pwm(duty)
        current = channel.get("pwm")
        if channel.get("enable") == 1 and current is not None and abs(current - want) <= 1:
            self.applied[index] = duty
            return
        if set_duty(channel, duty):
            self.applied[index] = duty

    def _release_one(self, channel):
        index = channel["index"]
        if index in self.idle:
            return
        self.idle.add(index)
        if channel.get("enable") == 1 or index in self.manual:
            set_mode(channel, False)
        self.manual.discard(index)
        self.applied.pop(index, None)
        self.thermals.pop(index, None)

    def release(self):
        chip = find_chip()
        if chip is None:
            self.manual.clear()
            return
        by_index = {channel["index"]: channel for channel in channels(chip)}
        for index in list(self.manual):
            channel = by_index.get(index)
            if channel is not None:
                set_mode(channel, False)
        self.manual.clear()


def _thermal(cfg):
    return Thermal(cfg.tau_s, cfg.deadband_c, cfg.hold_s, cfg.slew_pct_s)
