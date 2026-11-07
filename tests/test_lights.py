import unittest

from le240.lights import (
    format_color,
    parse_zones,
    parse_zone_state,
    speed_byte,
    speed_percent,
    zone_packet,
)


class LightTests(unittest.TestCase):
    def test_speed_is_inverted_for_the_controller(self):
        self.assertEqual(speed_byte(100), 0)
        self.assertEqual(speed_byte(0), 255)
        self.assertEqual(speed_byte(50), 128)
        self.assertEqual(speed_percent(128), 50)

    def test_present_channels_follow_the_bitmask(self):
        zones = parse_zones([1, 1, 0x50, 0x50, 0x1E, 0x1E, 5, 0x50], 0x0C, 0xCC)
        self.assertEqual([zone["id"] for zone in zones], [2, 3])
        self.assertTrue(all(zone["rgb"] for zone in zones))
        self.assertEqual(zones[0]["name"], "ARGB 1")

    def test_static_red_uses_rgb_order_when_the_channel_asks(self):
        packet = zone_packet(2, 0x01, 255, 0, 0, 128, rgb=True)
        self.assertEqual(packet[1], 0x10)
        self.assertEqual(packet[3:11], bytes([2, 1, 255, 0, 0, 128, 0xFF, 1]))

    def test_teal_stays_red_green_blue_when_the_channel_asks(self):
        packet = zone_packet(2, 0x01, 0x00, 0x84, 0x7F, 128, rgb=True)
        self.assertEqual(packet[5:8], bytes([0x00, 0x84, 0x7F]))
        report = bytes(4) + bytes([0x01, 0x00, 0x84, 0x7F, 128]) + bytes(55)
        self.assertEqual(parse_zone_state(report, rgb=True)["color"], "00847f")

    def test_grb_channels_swap_the_first_two_bytes(self):
        packet = zone_packet(2, 0x01, 255, 0, 16, 128, rgb=False)
        self.assertEqual(packet[5:8], bytes([0, 255, 16]))

    def test_zone_report_decodes_the_stored_color(self):
        report = bytes.fromhex("0000000201006a6e80ff01") + bytes(52)
        state = parse_zone_state(report, rgb=True)
        self.assertEqual(state["mode"], "static")
        self.assertEqual(state["color"], "006a6e")
        self.assertEqual(state["speed"], 50)
        self.assertEqual(format_color(0, 106, 110), "006a6e")


if __name__ == "__main__":
    unittest.main()
