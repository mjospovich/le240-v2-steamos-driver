"""Draggable fan and pump curve."""

import math

TEMP_MIN = 20.0
TEMP_MAX = 100.0
DUTY_MIN = 0.0
DUTY_MAX = 100.0
MIN_POINTS = 2
MAX_POINTS = 8
_PAD = (36, 12, 16, 26)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
except ImportError:  # macOS / headless — helpers still testable without GTK
    Gtk = None


def normalize(points):
    cleaned = []
    for item in points or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            cleaned.append([_clamp(item[0], TEMP_MIN, TEMP_MAX), _clamp(item[1], DUTY_MIN, DUTY_MAX)])
    cleaned.sort(key=lambda point: point[0])
    separated = []
    for temp, duty in cleaned:
        if separated and temp <= separated[-1][0]:
            temp = min(TEMP_MAX, separated[-1][0] + 1)
        if separated and temp <= separated[-1][0]:
            continue
        separated.append([temp, duty])
    if len(separated) < MIN_POINTS:
        return [[35.0, 25.0], [75.0, 100.0]]
    return separated[:MAX_POINTS]


def move_point(points, index, temp, duty):
    pts = [list(point) for point in points]
    low = TEMP_MIN if index == 0 else pts[index - 1][0] + 1
    high = TEMP_MAX if index == len(pts) - 1 else pts[index + 1][0] - 1
    if low > high:
        low = high = pts[index][0]
    pts[index][0] = _clamp(temp, low, high)
    pts[index][1] = _clamp(duty, DUTY_MIN, DUTY_MAX)
    return pts


def add_point(points, temp, duty):
    if len(points) >= MAX_POINTS:
        return [list(point) for point in points]
    return normalize(list(points) + [[temp, duty]])


def remove_point(points, index):
    if len(points) <= MIN_POINTS or index < 0 or index >= len(points):
        return [list(point) for point in points]
    return [list(point) for i, point in enumerate(points) if i != index]


def hit_index(points, x, y, width, height, radius=14):
    found = None
    best = radius * radius
    for index, point in enumerate(points):
        px, py = to_pixel(point[0], point[1], width, height)
        dist = (px - x) ** 2 + (py - y) ** 2
        if dist <= best:
            found = index
            best = dist
    return found


def to_pixel(temp, duty, width, height):
    left, right, top, bottom = _PAD
    span_x = max(1.0, width - left - right)
    span_y = max(1.0, height - top - bottom)
    x = left + (temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN) * span_x
    y = top + (1.0 - (duty - DUTY_MIN) / (DUTY_MAX - DUTY_MIN)) * span_y
    return x, y


def from_pixel(x, y, width, height):
    left, right, top, bottom = _PAD
    span_x = max(1.0, width - left - right)
    span_y = max(1.0, height - top - bottom)
    temp = TEMP_MIN + (x - left) / span_x * (TEMP_MAX - TEMP_MIN)
    duty = DUTY_MAX - (y - top) / span_y * (DUTY_MAX - DUTY_MIN)
    return _clamp(temp, TEMP_MIN, TEMP_MAX), _clamp(duty, DUTY_MIN, DUTY_MAX)


def _clamp(value, low, high):
    return max(low, min(high, float(value)))


if Gtk is not None:

    class CurvePlot(Gtk.DrawingArea):
        def __init__(self, points):
            super().__init__()
            self.points = normalize(points)
            self.live = None
            self._drag = None
            self._origin = (0.0, 0.0)
            self.set_size_request(380, 210)
            self.set_hexpand(True)
            self.set_draw_func(self._draw)
            drag = Gtk.GestureDrag()
            drag.set_button(1)
            drag.connect("drag-begin", self._begin)
            drag.connect("drag-update", self._update)
            drag.connect("drag-end", self._end)
            right = Gtk.GestureClick()
            right.set_button(3)
            right.connect("pressed", self._remove)
            self.add_controller(drag)
            self.add_controller(right)

        def set_live(self, temp):
            self.live = temp
            self.queue_draw()

        def _begin(self, _gesture, x, y):
            self._origin = (x, y)
            self._drag = hit_index(self.points, x, y, self.get_width(), self.get_height())

        def _update(self, _gesture, dx, dy):
            if self._drag is None:
                return
            temp, duty = from_pixel(
                self._origin[0] + dx, self._origin[1] + dy, self.get_width(), self.get_height()
            )
            self.points = move_point(self.points, self._drag, temp, duty)
            self.queue_draw()

        def _end(self, _gesture, dx, dy):
            if self._drag is None and dx * dx + dy * dy < 16:
                temp, duty = from_pixel(
                    self._origin[0], self._origin[1], self.get_width(), self.get_height()
                )
                self.points = add_point(self.points, temp, duty)
                self.queue_draw()
            self._drag = None

        def _remove(self, _gesture, _n, x, y):
            index = hit_index(self.points, x, y, self.get_width(), self.get_height())
            if index is None:
                return
            self.points = remove_point(self.points, index)
            self.queue_draw()

        def _draw(self, _area, cr, width, height, _data=None):
            left, right, top, bottom = _PAD
            cr.set_source_rgb(0.078, 0.094, 0.106)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.08)
            cr.set_line_width(1)
            for duty in (0, 25, 50, 75, 100):
                _x, y = to_pixel(TEMP_MIN, duty, width, height)
                cr.move_to(left, y)
                cr.line_to(width - right, y)
                cr.stroke()
            for temp in (20, 40, 60, 80, 100):
                x, _y = to_pixel(temp, 0, width, height)
                cr.move_to(x, top)
                cr.line_to(x, height - bottom)
                cr.stroke()
            cr.set_source_rgb(0.56, 0.63, 0.64)
            cr.set_font_size(11)
            for temp in (20, 60, 100):
                x, y = to_pixel(temp, 0, width, height)
                cr.move_to(x - 8, height - 8)
                cr.show_text(f"{temp}")
            for duty, label in ((0, "0"), (100, "100")):
                _x, y = to_pixel(TEMP_MIN, duty, width, height)
                cr.move_to(4, y + 4)
                cr.show_text(label)
            if self.live is not None:
                x, _y = to_pixel(_clamp(self.live, TEMP_MIN, TEMP_MAX), 0, width, height)
                cr.set_source_rgba(0.0, 0.784, 0.745, 0.45)
                cr.set_dash([3, 3])
                cr.move_to(x, top)
                cr.line_to(x, height - bottom)
                cr.stroke()
                cr.set_dash([])
            cr.set_source_rgb(0.0, 0.784, 0.745)
            cr.set_line_width(2)
            for index, point in enumerate(self.points):
                x, y = to_pixel(point[0], point[1], width, height)
                if index == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()
            for point in self.points:
                x, y = to_pixel(point[0], point[1], width, height)
                cr.set_source_rgb(0.0, 0.784, 0.745)
                cr.arc(x, y, 6, 0, math.tau)
                cr.stroke()
                cr.set_source_rgb(0.83, 0.88, 0.88)
                cr.arc(x, y, 4, 0, math.tau)
                cr.fill()
