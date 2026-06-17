import unittest

from scripts.bu03_calibrate import CalibrationPoint, build_setdev_command, fit_calibration, group_points


class Bu03CalibrateTest(unittest.TestCase):
    def test_groups_points_by_actual_distance(self):
        points = [
            CalibrationPoint(actual_m=1.0, reported_m=1.2),
            CalibrationPoint(actual_m=1.0, reported_m=1.4),
            CalibrationPoint(actual_m=2.0, reported_m=2.2),
        ]

        grouped = group_points(points)

        self.assertEqual(len(grouped), 2)
        self.assertAlmostEqual(grouped[0].reported_m, 1.3)
        self.assertEqual(grouped[0].count, 2)

    def test_fits_linear_calibration(self):
        points = [
            CalibrationPoint(actual_m=1.0, reported_m=1.5),
            CalibrationPoint(actual_m=2.0, reported_m=2.5),
            CalibrationPoint(actual_m=3.0, reported_m=3.5),
        ]

        result = fit_calibration(points)

        self.assertAlmostEqual(result.para_a, 1.0)
        self.assertAlmostEqual(result.para_b_m, -0.5)
        self.assertAlmostEqual(result.para_b_mm, -500.0)

    def test_builds_setdev_command(self):
        result = fit_calibration(
            [
                CalibrationPoint(actual_m=1.0, reported_m=1.5),
                CalibrationPoint(actual_m=2.0, reported_m=2.5),
            ]
        )

        command = build_setdev_command(result, 10, 16336, 1, 0.018, 0.642, 0, 0)

        self.assertEqual(command, "AT+SETDEV=10,16336,1,0.018,0.642,1.0000,-500.00,0,0")


if __name__ == "__main__":
    unittest.main()
