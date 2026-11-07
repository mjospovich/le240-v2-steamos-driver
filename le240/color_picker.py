"""In-page color field. Hue, saturation, value, and hex."""

import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .lights import format_color, parse_color


class ColorPicker(Gtk.Box):
    def __init__(self, text):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.on_changed = None
        self._lock = False
        self.hue, self.sat, self.val = rgb_to_hsv(*parse_color(text))

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._field = Gtk.DrawingArea()
        self._field.set_size_request(168, 120)
        self._field.set_draw_func(self._draw_field)
        self._hue = Gtk.DrawingArea()
        self._hue.set_size_request(168, 14)
        self._hue.set_draw_func(self._draw_hue)
        column.append(self._field)
        column.append(self._hue)

        self._entry = Gtk.Entry()
        self._entry.set_max_length(7)
        self._entry.set_width_chars(7)
        self._entry.set_valign(Gtk.Align.START)
        self._write_entry()

        self.append(column)
        self.append(self._entry)
        self._bind(self._field, self._move_field)
        self._bind(self._hue, self._move_hue)
        self._entry.connect("changed", self._typed)

    def color(self):
        return format_color(*hsv_to_rgb(self.hue, self.sat, self.val))

    def _bind(self, area, move):
        drag = Gtk.GestureDrag()
        drag.set_button(1)
        origin = {"x": 0.0, "y": 0.0}

        def begin(_gesture, x, y):
            origin["x"], origin["y"] = x, y
            move(x, y)

        def update(_gesture, dx, dy):
            move(origin["x"] + dx, origin["y"] + dy)

        drag.connect("drag-begin", begin)
        drag.connect("drag-update", update)
        area.add_controller(drag)

    def _move_field(self, x, y):
        width = max(1, self._field.get_width())
        height = max(1, self._field.get_height())
        self.sat = _unit(x / width)
        self.val = _unit(1 - y / height)
        self._publish()

    def _move_hue(self, x, _y):
        self.hue = _unit(x / max(1, self._hue.get_width()))
        self._publish()

    def _typed(self, entry):
        if self._lock:
            return
        raw = entry.get_text().strip().lstrip("#")
        if len(raw) != 6:
            return
        try:
            red, green, blue = parse_color(raw)
        except ValueError:
            return
        if format_color(red, green, blue) != raw.lower():
            return
        self.hue, self.sat, self.val = rgb_to_hsv(red, green, blue)
        self._field.queue_draw()
        self._hue.queue_draw()
        self._emit()

    def _publish(self):
        self._field.queue_draw()
        self._hue.queue_draw()
        self._write_entry()
        self._emit()

    def _write_entry(self):
        self._lock = True
        self._entry.set_text(self.color().upper())
        self._lock = False

    def _emit(self):
        if self.on_changed:
            self.on_changed(self.color())

    def _draw_field(self, _area, cr, width, height, _data=None):
        step = 4
        y = 0
        while y < height:
            val = 1 - (y + step / 2) / height
            x = 0
            while x < width:
                red, green, blue = hsv_to_rgb(self.hue, (x + step / 2) / width, val)
                cr.set_source_rgb(red / 255, green / 255, blue / 255)
                cr.rectangle(x, y, step + 1, step + 1)
                cr.fill()
                x += step
            y += step
        mark(cr, self.sat * width, (1 - self.val) * height)

    def _draw_hue(self, _area, cr, width, height, _data=None):
        step = 3
        x = 0
        while x < width:
            red, green, blue = hsv_to_rgb((x + step / 2) / width, 1, 1)
            cr.set_source_rgb(red / 255, green / 255, blue / 255)
            cr.rectangle(x, 0, step + 1, height)
            cr.fill()
            x += step
        mark(cr, self.hue * width, height / 2, 5)


def mark(cr, x, y, radius=6):
    cr.set_source_rgb(0.08, 0.09, 0.1)
    cr.set_line_width(3)
    cr.arc(x, y, radius, 0, math.tau)
    cr.stroke()
    cr.set_source_rgb(0.96, 0.97, 0.97)
    cr.set_line_width(1.5)
    cr.arc(x, y, radius, 0, math.tau)
    cr.stroke()


def rgb_to_hsv(red, green, blue):
    r, g, b = red / 255, green / 255, blue / 255
    hi = max(r, g, b)
    lo = min(r, g, b)
    span = hi - lo
    if span == 0:
        hue = 0.0
    elif hi == r:
        hue = ((g - b) / span) % 6
    elif hi == g:
        hue = (b - r) / span + 2
    else:
        hue = (r - g) / span + 4
    hue /= 6
    sat = 0.0 if hi == 0 else span / hi
    return hue, sat, hi


def hsv_to_rgb(hue, sat, val):
    sector = (hue % 1) * 6
    index = int(sector)
    frac = sector - index
    peak = val
    fall = val * (1 - sat)
    rise = val * (1 - sat * frac)
    drop = val * (1 - sat * (1 - frac))
    table = (
        (peak, drop, fall),
        (rise, peak, fall),
        (fall, peak, drop),
        (fall, rise, peak),
        (drop, fall, peak),
        (peak, fall, rise),
    )
    red, green, blue = table[index % 6]
    return tuple(int(round(channel * 255)) for channel in (red, green, blue))


def _unit(value):
    return max(0.0, min(1.0, value))
