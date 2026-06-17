import unittest

from collector.bu03_collector import parse_distance_line


class ParseDistanceLineTest(unittest.TestCase):
    def test_parses_meter_distance_with_ids(self):
        sample = parse_distance_line("TAG:T01 ANCHOR:A01 DIST:1.234m")

        self.assertIsNotNone(sample)
        self.assertEqual(sample.tag_id, "T01")
        self.assertEqual(sample.anchor_id, "A01")
        self.assertAlmostEqual(sample.reported_distance_m, 1.234)

    def test_parses_bu03_unitless_distance_as_meters(self):
        sample = parse_distance_line("distance: 4.915494")

        self.assertIsNotNone(sample)
        self.assertAlmostEqual(sample.reported_distance_m, 4.915494)

    def test_parses_centimeters_with_defaults(self):
        sample = parse_distance_line("range=245 cm", default_tag_id="T01", default_anchor_id="A02")

        self.assertIsNotNone(sample)
        self.assertEqual(sample.tag_id, "T01")
        self.assertEqual(sample.anchor_id, "A02")
        self.assertAlmostEqual(sample.reported_distance_m, 2.45)

    def test_parses_millimeters(self):
        sample = parse_distance_line("rng: 1876mm")

        self.assertIsNotNone(sample)
        self.assertAlmostEqual(sample.reported_distance_m, 1.876)

    def test_ignores_unknown_line(self):
        self.assertIsNone(parse_distance_line("OK"))


if __name__ == "__main__":
    unittest.main()
