"""Lighting page."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from .color_picker import ColorPicker
from .lights import MODES, Controller

FALLBACK = (
    {"id": 2, "name": "ARGB 1"},
    {"id": 3, "name": "ARGB 2"},
)


class LightPage(Gtk.Box):
    def __init__(self, saved):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.include = saved is not None
        self.on_changed = None
        self._pending = 0
        zones, current = _probe()
        initial = saved or current or {"mode": "static", "color": "00c8be", "speed": 50, "zone": "all"}
        if current is not None:
            self.include = True

        self._mode = Gtk.ComboBoxText()
        for mode_id, label, _code, _color, _speed in MODES:
            self._mode.append(mode_id, label)
        self._mode.set_active_id(initial.get("mode", "static"))

        self._color = ColorPicker(initial.get("color", "00c8be"))
        self._color.on_changed = self._schedule

        self._speed = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self._speed.set_draw_value(True)
        self._speed.set_value_pos(Gtk.PositionType.RIGHT)
        self._speed.set_hexpand(True)
        self._speed.set_value(initial.get("speed", 50))

        self._zone = Gtk.ComboBoxText()
        self._zone.append("all", "All")
        for zone in zones or FALLBACK:
            self._zone.append(str(zone["id"]), zone["name"])
        zone_id = str(initial.get("zone", "all"))
        if not self._zone.set_active_id(zone_id):
            self._zone.set_active(0)

        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        form.append(_row("Mode", self._mode))
        self._color_row = _row("Color", self._color, expand=False)
        self._speed_row = _row("Speed", self._speed)
        form.append(self._color_row)
        form.append(self._speed_row)
        form.append(_row("Channel", self._zone))

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_hexpand(True)
        card.append(form)
        self.append(card)
        self.set_margin_top(12)
        self.set_valign(Gtk.Align.START)

        self._ready = False
        self._mode.connect("changed", self._refresh)
        self._refresh()
        self._ready = True
        self._mode.connect("changed", self._schedule)
        self._speed.connect("value-changed", self._schedule)
        self._zone.connect("changed", self._schedule)

    def values(self):
        return {
            "mode": self._mode.get_active_id() or "static",
            "color": self._color.color(),
            "speed": int(self._speed.get_value()),
            "zone": self._zone.get_active_id() or "all",
        }

    def _schedule(self, *_args):
        if not self._ready:
            return
        self.include = True
        if self._pending:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(80, self._flush)

    def _flush(self):
        self._pending = 0
        if self.on_changed:
            self.on_changed(self.values())
        return False

    def _refresh(self, *_args):
        spec = next(item for item in MODES if item[0] == (self._mode.get_active_id() or "static"))
        self._color_row.set_visible(spec[3])
        self._speed_row.set_visible(spec[4])


def _probe():
    try:
        ctrl = Controller.open()
    except Exception:
        return [], None
    try:
        zones = ctrl.zones()
        state = ctrl.state(zones[0]) if zones else None
        if state is not None:
            state["zone"] = "all"
        return zones, state
    except Exception:
        return [], None
    finally:
        ctrl.close()


def _row(text, widget, expand=True):
    row = Gtk.Box(spacing=12)
    label = Gtk.Label(label=text, xalign=0)
    label.set_size_request(90, -1)
    widget.set_valign(Gtk.Align.CENTER)
    widget.set_hexpand(expand)
    row.append(label)
    row.append(widget)
    return row
