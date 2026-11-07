import unittest

from le240.curve import Thermal, duty_at, hold_if_slow
from le240.hwmon import connected, role_for
from le240.plot import add_point, hit_index, move_point, normalize, remove_point


POINTS = [(40, 20), (80, 100)]


class CurveTests(unittest.TestCase):
    def test_duty_interpolates(self):
        self.assertEqual(duty_at(POINTS, 40), 20)
        self.assertEqual(duty_at(POINTS, 60), 60)
        self.assertEqual(duty_at(POINTS, 90), 100)

    def test_short_spike_does_not_move_duty(self):
        thermal = Thermal(tau_s=0.001, deadband_c=1, hold_s=10, slew_pct_s=1000)
        first = thermal.step(40, 0, POINTS)
        during = thermal.step(70, 1, POINTS)
        self.assertEqual(during, first)
        self.assertEqual(thermal.step(40, 2, POINTS), first)

    def test_sustained_rise_slews_instead_of_jumping(self):
        thermal = Thermal(tau_s=0.001, deadband_c=1, hold_s=0, slew_pct_s=10)
        thermal.step(40, 0, POINTS)
        thermal.step(80, 1, POINTS)
        self.assertAlmostEqual(thermal.duty, 30, places=3)

    def test_deadband_ignores_one_degree(self):
        thermal = Thermal(tau_s=0.001, deadband_c=2, hold_s=0, slew_pct_s=100)
        first = thermal.step(50, 0, POINTS)
        later = thermal.step(51, 30, POINTS)
        self.assertEqual(later, first)

    def test_drag_keeps_points_in_order(self):
        points = [[30, 20], [50, 40], [80, 90]]
        moved = move_point(points, 1, 90, 10)
        self.assertEqual(moved[1], [79, 10])
        self.assertLess(moved[0][0], moved[1][0])
        self.assertLess(moved[1][0], moved[2][0])

    def test_click_adds_and_right_click_keeps_two(self):
        added = add_point([[30, 20], [80, 90]], 55, 40)
        self.assertEqual(len(added), 3)
        self.assertEqual(remove_point(added, 1)[1][0], 80)
        self.assertEqual(len(remove_point([[30, 20], [80, 90]], 0)), 2)

    def test_hit_finds_the_nearest_point(self):
        points = normalize([[20, 0], [100, 100]])
        width, height = 400, 220
        from le240.plot import to_pixel
        x, y = to_pixel(points[0][0], points[0][1], width, height)
        self.assertEqual(hit_index(points, x, y, width, height), 0)
        self.assertIsNone(hit_index(points, 200, 100, width, height))

    def test_pump_label_wins_over_a_slow_reading(self):
        pump = {"index": 2, "label": "Pump Fan", "rpm": 400}
        fan = {"index": 1, "label": "CPU Fan", "rpm": 2068}
        self.assertEqual(role_for(pump, {}), "pump")
        self.assertEqual(role_for(fan, {}), "fan")
        self.assertFalse(connected({"rpm": 0}))
        self.assertTrue(connected({"rpm": 444}))

    def test_pump_floor_holds_duty_when_slow(self):
        self.assertEqual(hold_if_slow(30, 50, 2400, 2500), 50)
        self.assertEqual(hold_if_slow(70, 50, 2400, 2500), 70)
        self.assertEqual(hold_if_slow(30, 50, 2800, 2500), 30)
        self.assertEqual(hold_if_slow(30, 50, 0, 2500), 50)


if __name__ == "__main__":
    unittest.main()
