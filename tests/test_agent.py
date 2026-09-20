import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.models import IncidentDecision
from agent.providers import decide_heuristic
from agent.policies import requires_human_approval, evidence_is_conflicting


class TestStructuredDecision(unittest.TestCase):
    def test_valid_decision_constructs(self):
        d = IncidentDecision(
            incident="backend_down", confidence=0.9, severity="high",
            evidence=["a"], probable_cause="x", recommended_action="restart_backend",
            requires_approval=True,
        )
        self.assertEqual(d.recommended_action, "restart_backend")

    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):
            IncidentDecision(
                incident="x", confidence=0.9, severity="high", evidence=["a"],
                probable_cause="x", recommended_action="rm -rf /",  # never allowed
                requires_approval=True,
            )

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            IncidentDecision(
                incident="x", confidence=1.5, severity="high", evidence=["a"],
                probable_cause="x", recommended_action="none", requires_approval=False,
            )

    def test_empty_evidence_rejected(self):
        with self.assertRaises(ValueError):
            IncidentDecision(
                incident="x", confidence=0.5, severity="low", evidence=[],
                probable_cause="x", recommended_action="none", requires_approval=False,
            )


class TestHeuristicProvider(unittest.TestCase):
    def test_healthy_evidence_yields_no_action(self):
        evidence = {
            "vision": {"overall_state": "healthy", "overall_confidence": 0.9},
            "docker": {"found": True, "status": "running"},
            "http": {"healthy": True},
        }
        out = decide_heuristic(evidence)
        self.assertEqual(out["recommended_action"], "none")
        self.assertFalse(out["requires_approval"])

    def test_down_with_stopped_container_recommends_restart(self):
        evidence = {
            "vision": {"overall_state": "down", "overall_confidence": 0.8},
            "docker": {"found": True, "status": "stopped"},
            "http": {"healthy": False},
        }
        out = decide_heuristic(evidence)
        self.assertEqual(out["recommended_action"], "restart_backend")
        self.assertTrue(out["requires_approval"])
        self.assertEqual(out["severity"], "high")

    def test_conflicting_evidence_does_not_recommend_action(self):
        # OpenCV says DOWN but Docker says RUNNING -> must not auto-remediate
        evidence = {
            "vision": {"overall_state": "down", "overall_confidence": 0.8},
            "docker": {"found": True, "status": "running"},
            "http": {"healthy": True},
        }
        out = decide_heuristic(evidence)
        self.assertEqual(out["recommended_action"], "none")
        self.assertEqual(out["incident"], "conflicting_evidence")

    def test_unknown_visual_state_does_not_act(self):
        evidence = {
            "vision": {"overall_state": "unknown", "overall_confidence": 0.1},
            "docker": {},
            "http": {},
        }
        out = decide_heuristic(evidence)
        self.assertEqual(out["recommended_action"], "none")


class TestPolicies(unittest.TestCase):
    def test_no_action_never_requires_approval(self):
        d = IncidentDecision(
            incident="none", confidence=0.9, severity="low", evidence=["ok"],
            probable_cause="n/a", recommended_action="none", requires_approval=False,
        )
        self.assertFalse(requires_human_approval(d))

    def test_restart_always_requires_approval(self):
        d = IncidentDecision(
            incident="backend_down", confidence=0.9, severity="high", evidence=["x"],
            probable_cause="y", recommended_action="restart_backend", requires_approval=True,
        )
        self.assertTrue(requires_human_approval(d))

    def test_conflicting_evidence_detection(self):
        self.assertTrue(evidence_is_conflicting("down", "running"))
        self.assertFalse(evidence_is_conflicting("down", "stopped"))
        self.assertFalse(evidence_is_conflicting("healthy", "running"))


if __name__ == "__main__":
    unittest.main()
