import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demo.generate_dashboard import render_dashboard
from vision.detector import analyze_dashboard, visual_recovery_score

TMP_DIR = os.path.join(os.path.dirname(__file__), "_tmp_vision")


class TestVisionDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_DIR, exist_ok=True)
        cls.healthy_path = render_dashboard("healthy", "healthy", os.path.join(TMP_DIR, "healthy.png"))
        cls.down_path = render_dashboard("down", "healthy", os.path.join(TMP_DIR, "down.png"))
        cls.warning_path = render_dashboard("warning", "healthy", os.path.join(TMP_DIR, "warning.png"))
        cls.both_down_path = render_dashboard("down", "down", os.path.join(TMP_DIR, "both_down.png"))

    def test_healthy_dashboard_detected_as_healthy(self):
        result = analyze_dashboard(self.healthy_path)
        self.assertEqual(result.overall_state, "healthy")
        self.assertGreater(result.overall_confidence, 0.5)

    def test_backend_down_detected(self):
        result = analyze_dashboard(self.down_path)
        self.assertEqual(result.overall_state, "down")
        chip_states = {c["name"]: c["state"] for c in result.chips}
        self.assertEqual(chip_states["backend_service"], "down")
        self.assertEqual(chip_states["database_service"], "healthy")

    def test_warning_state_detected(self):
        result = analyze_dashboard(self.warning_path)
        chip_states = {c["name"]: c["state"] for c in result.chips}
        self.assertEqual(chip_states["backend_service"], "warning")

    def test_both_services_down(self):
        result = analyze_dashboard(self.both_down_path)
        chip_states = {c["name"]: c["state"] for c in result.chips}
        self.assertEqual(chip_states["backend_service"], "down")
        self.assertEqual(chip_states["database_service"], "down")

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            analyze_dashboard(os.path.join(TMP_DIR, "does_not_exist.png"))

    def test_visual_recovery_score_detects_change(self):
        score = visual_recovery_score(self.down_path, self.healthy_path)
        self.assertGreater(score, 0.01)  # panels visibly differ

    def test_visual_recovery_score_no_change_for_identical_image(self):
        score = visual_recovery_score(self.healthy_path, self.healthy_path)
        self.assertEqual(score, 0.0)

    def test_opencv_version_is_recorded(self):
        result = analyze_dashboard(self.healthy_path)
        self.assertTrue(result.opencv_version)


if __name__ == "__main__":
    unittest.main()
