"""Smoothed temperature control for fan and pump curves.

CPU package temperature moves faster than the coolant. The controller
follows a slowed temperature, ignores small moves, waits out short
spikes, then glides the duty toward the new curve point.
"""

import math


def duty_at(points, temp):
    pts = sorted((float(t), float(d)) for t, d in points)
    if not pts:
        return 0.0
    if temp <= pts[0][0]:
        return _clamp_duty(pts[0][1])
    if temp >= pts[-1][0]:
        return _clamp_duty(pts[-1][1])
    for (t0, d0), (t1, d1) in zip(pts, pts[1:]):
        if t0 <= temp <= t1:
            if t1 == t0:
                return _clamp_duty(d1)
            span = (temp - t0) / (t1 - t0)
            return _clamp_duty(d0 + span * (d1 - d0))
    return _clamp_duty(pts[-1][1])


def move_toward(current, target, max_step):
    if max_step < 0:
        max_step = 0.0
    if target > current:
        return min(target, current + max_step)
    return max(target, current - max_step)


def hold_if_slow(requested, applied, rpm, min_rpm):
    """Do not lower the duty while a measured pump is at or under its floor."""
    if rpm is None or min_rpm <= 0:
        return requested
    if rpm <= min_rpm and requested < applied:
        return applied
    return requested


class Thermal:
    def __init__(self, tau_s, deadband_c, hold_s, slew_pct_s):
        self.tau_s = float(tau_s)
        self.deadband_c = float(deadband_c)
        self.hold_s = float(hold_s)
        self.slew_pct_s = float(slew_pct_s)
        self.smoothed = None
        self.latched = None
        self.duty = None
        self.target = None
        self.pending = False
        self.pending_since = None
        self.last_t = None

    def step(self, temp, now, points):
        temp = float(temp)
        now = float(now)
        if self.smoothed is None:
            self.smoothed = temp
            self.latched = temp
            self.duty = duty_at(points, temp)
            self.target = self.duty
            self.last_t = now
            return self.duty

        dt = max(0.0, now - self.last_t)
        self.last_t = now
        alpha = 1.0 if self.tau_s <= 0 else 1.0 - math.exp(-dt / self.tau_s)
        self.smoothed += alpha * (temp - self.smoothed)

        if abs(self.smoothed - self.latched) < self.deadband_c:
            self.pending = False
        else:
            if not self.pending:
                self.pending = True
                self.pending_since = now
            if now - self.pending_since >= self.hold_s:
                self.target = duty_at(points, self.smoothed)
                self.latched = self.smoothed
                self.pending = False

        self.duty = move_toward(self.duty, self.target, self.slew_pct_s * dt)
        return self.duty


def _clamp_duty(value):
    return max(0.0, min(100.0, value))
