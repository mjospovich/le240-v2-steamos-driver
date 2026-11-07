"""LE240 control window."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from .config import Config, load, save
from .curve import duty_at
from .hwmon import channels, connected, cpu_temp_c, find_chip
from .lights import apply_saved
from .lights_page import LightPage
from .plot import CurvePlot

STYLE = """
window { background-color: #14181b; color: #e7eeef; }
label { color: #e7eeef; }
.card {
  background-color: #1e2528;
  border: 1px solid rgba(231, 238, 239, 0.07);
  border-radius: 12px;
  padding: 16px;
}
.dim { color: #8ea0a2; font-size: 12px; }
.muted { color: #8ea0a2; }
button.suggested-action {
  background-color: #00c8be;
  color: #102022;
  border-radius: 8px;
  padding: 6px 16px;
}
button.suggested-action label { color: #102022; }
switch { background-color: #2c3538; border: 1px solid #3e494c; }
switch slider { background-color: #d5e0e1; border-radius: 99px; }
switch:checked { background-color: #00c8be; border-color: #00c8be; }
switch:checked slider { background-color: #f4f8f8; }
spinbutton button { background: transparent; color: #c5d4d4; }
spinbutton button:hover { color: #00c8be; }
stackswitcher > button {
  background-color: #1e2528;
  border-radius: 8px;
  padding: 6px 16px;
  margin-right: 8px;
  border: none;
  box-shadow: none;
}
stackswitcher > button label { color: #8ea0a2; }
stackswitcher > button:checked { background-color: #00c8be; }
stackswitcher > button:checked label { color: #102022; }
entry {
  background-color: #14181b;
  color: #e7eeef;
  border-radius: 8px;
  border: 1px solid #3e494c;
  padding: 4px 8px;
}
scale trough { background-color: #2c3538; min-height: 4px; border-radius: 99px; }
scale highlight { background-color: #00c8be; border-radius: 99px; }
scale slider { background-color: #d5e0e1; min-width: 14px; min-height: 14px; border-radius: 99px; }
"""


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="LE240")
        self._apply_style()
        self._cfg = load()
        self._ready = False
        self._rows = {}
        self._indexes = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for edge in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{edge}")(16)
        self.set_child(root)

        header = Gtk.Box(spacing=12)
        on_row, self._on = _switch("Enabled", self._cfg.enabled)
        self._on.connect("notify::active", self._on_toggle)
        title = Gtk.Label(label="LE240", xalign=0)
        self._status = Gtk.Label(xalign=1, hexpand=True)
        self._status.add_css_class("muted")
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self._on_save)
        header.append(on_row)
        header.append(title)
        header.append(self._status)
        header.append(apply_btn)
        root.append(header)

        pages = Gtk.Stack()
        pages.set_vhomogeneous(False)
        pages.set_hhomogeneous(True)
        pages.add_titled(_cooling(self), "cooling", "Cooling")
        self._lights = LightPage(self._cfg.lights)
        self._lights.on_changed = self._live_lights
        pages.add_titled(self._lights, "lighting", "Lighting")
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(pages)
        switcher.set_halign(Gtk.Align.START)
        root.append(switcher)
        root.append(pages)
        pages.connect("notify::visible-child", lambda *_args: self._fit())
        self.connect("map", lambda *_args: self._fit())

        self._ready = True
        GLib.timeout_add(1000, self._tick)
        if self._cfg.lights:
            apply_saved(self._cfg.lights)

    def _fit(self, *_args):
        self.set_resizable(False)
        GLib.idle_add(self._allow_resize)

    def _allow_resize(self):
        self.set_resizable(True)
        return False

    def _live_lights(self, lights):
        cfg = load()
        cfg.lights = lights
        save(cfg)
        apply_saved(lights)

    def _apply_style(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _tick(self):
        self._cfg = load()
        temp = cpu_temp_c()
        found = [channel for channel in channels(find_chip()) if connected(channel)]
        self._sync_headers(found)
        self._fan.set_live(temp)
        self._pump.set_live(temp)
        if temp is None:
            self._status.set_label("—")
        else:
            fan = duty_at(self._fan.points, temp)
            pump = duty_at(self._pump.points, temp)
            self._status.set_label(f"{temp:.0f}°C  ·  Fan {fan:.0f}%  ·  Pump {pump:.0f}%")
        return True

    def _sync_headers(self, found):
        indexes = tuple(channel["index"] for channel in found)
        if indexes != self._indexes:
            self._indexes = indexes
            while self._headers.get_first_child() is not None:
                self._headers.remove(self._headers.get_first_child())
            self._rows = {}
            for channel in found:
                self._rows[channel["index"]] = _header_row(self._headers, channel, self._cfg)
        for channel in found:
            row = self._rows[channel["index"]]
            rpm = "—" if channel["rpm"] is None else f"{channel['rpm']} rpm"
            if channel["pwm"] is None:
                detail = rpm
            else:
                detail = f"{rpm}  ·  {round(channel['pwm'] / 255 * 100)}%"
            row["label"].set_label(f"{channel['label']}    {detail}")

    def _on_toggle(self, switch, _pspec):
        if not self._ready:
            return
        cfg = load()
        cfg.enabled = bool(switch.get_active())
        save(cfg)

    def _on_save(self, _button):
        fixed = {}
        for index, row in self._rows.items():
            if row["fixed"].get_active():
                fixed[str(index)] = row["duty"].get_value()
        lights = self._lights.values() if self._lights.include else self._cfg.lights
        cfg = Config(
            enabled=self._on.get_active(),
            tau_s=self._tau.get_value(),
            deadband_c=self._band.get_value(),
            hold_s=self._hold.get_value(),
            slew_pct_s=self._slew.get_value(),
            pump_min_rpm=self._cfg.pump_min_rpm,
            fan_curve=[list(point) for point in self._fan.points],
            pump_curve=[list(point) for point in self._pump.points],
            roles=self._cfg.roles,
            fixed=fixed,
            lights=lights,
        )
        save(cfg)
        if lights:
            apply_saved(lights)
        self._status.set_label("Applied")


def _cooling(window):
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    page.set_margin_top(12)
    curves = Gtk.Box(spacing=12)
    window._fan = CurvePlot(window._cfg.fan_curve)
    window._pump = CurvePlot(window._cfg.pump_curve)
    curves.append(_card_widget(_plot("Fan", window._fan)))
    curves.append(_card_widget(_plot("Pump", window._pump)))
    page.append(curves)

    body = Gtk.Box(spacing=12)
    page.append(body)
    window._tau = _spin(0, 300, 5, window._cfg.tau_s)
    window._band = _spin(0, 20, 0.5, window._cfg.deadband_c)
    window._hold = _spin(0, 120, 1, window._cfg.hold_s)
    window._slew = _spin(1, 100, 1, window._cfg.slew_pct_s)
    settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    settings.append(_inline("Smoothing (s)", window._tau))
    settings.append(_inline("Hysteresis (°C)", window._band))
    settings.append(_inline("Delay (s)", window._hold))
    settings.append(_inline("Ramp (%/s)", window._slew))
    body.append(_card("Response", settings))

    window._headers = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    body.append(_card("Headers", window._headers))
    return page


def _plot(title, plot):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.append(Gtk.Label(label=title, xalign=0))
    box.append(plot)
    return box


def _header_row(parent, channel, cfg):
    row = Gtk.Box(spacing=8)
    label = Gtk.Label(xalign=0, hexpand=True)
    pinned = cfg.fixed.get(str(channel["index"]))
    switch = Gtk.Switch(active=pinned is not None, valign=Gtk.Align.CENTER)
    duty = _spin(0, 100, 1, 40 if pinned is None else pinned)
    row.append(label)
    row.append(Gtk.Label(label="Manual"))
    row.append(switch)
    row.append(duty)
    parent.append(row)
    return {"label": label, "fixed": switch, "duty": duty}


def _card(title, child):
    return _card_widget(_titled(title, child))


def _card_widget(child):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.add_css_class("card")
    box.set_hexpand(True)
    box.append(child)
    return box


def _titled(title, child):
    wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    heading = Gtk.Label(label=title, xalign=0)
    wrap.append(heading)
    wrap.append(child)
    return wrap


def _inline(text, widget):
    row = Gtk.Box(spacing=8)
    label = Gtk.Label(label=text, xalign=0, hexpand=True)
    widget.set_valign(Gtk.Align.CENTER)
    row.append(label)
    row.append(widget)
    return row


def _switch(text, active):
    row = Gtk.Box(spacing=8)
    switch = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
    row.append(switch)
    row.append(Gtk.Label(label=text))
    return row, switch


def _spin(low, high, step, value):
    spin = Gtk.SpinButton.new_with_range(low, high, step)
    spin.set_value(value)
    return spin


def main():
    app = Gtk.Application(application_id="local.le240.Control")
    app.connect("activate", lambda application: Window(application).present())
    app.run(None)


if __name__ == "__main__":
    main()
