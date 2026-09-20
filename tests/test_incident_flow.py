import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demo.generate_dashboard import render_dashboard
from agent import agent as agent_ops
from agent import tools
from agent.models import Incident

TMP_DIR = os.path.join(os.path.dirname(__file__), "_tmp_flow")


class TestIncidentFlow(unittest.TestCase):
    def setUp(self):
        os.makedirs(TMP_DIR, exist_ok=True)
        tools.CLUSTER = tools.SimulatedCluster()  # fresh cluster per test

    def test_healthy_flow_resolves_with_no_action(self):
        img = render_dashboard("healthy", "healthy", os.path.join(TMP_DIR, "h.png"))
        incident = agent_ops.run_full_cycle(img, auto_approve=True)
        self.assertEqual(incident.status, "resolved")
        self.assertEqual(incident.decision["recommended_action"], "none")
        self.assertIsNone(incident.remediation_result)

    def test_incident_flow_without_approval_stops_at_awaiting_approval(self):
        tools.CLUSTER.stop("visionnoc-backend")
        img = tools.capture_dashboard("down", "healthy")["image_path"]
        incident = agent_ops.run_full_cycle(img, auto_approve=False)
        self.assertEqual(incident.status, "awaiting_approval")
        self.assertIsNone(incident.remediation_result)
        # container must NOT have been restarted just by running the cycle
        self.assertEqual(tools.CLUSTER.inspect("visionnoc-backend")["status"], "stopped")

    def test_full_incident_flow_with_approval_restarts_and_verifies(self):
        tools.CLUSTER.stop("visionnoc-backend")
        img = tools.capture_dashboard("down", "healthy")["image_path"]
        incident = agent_ops.run_full_cycle(img, auto_approve=True)
        self.assertEqual(incident.status, "resolved")
        self.assertEqual(tools.CLUSTER.inspect("visionnoc-backend")["status"], "running")
        self.assertTrue(incident.verification_result["overall_recovered"])
        tool_names = [t["tool"] for t in incident.tool_calls]
        self.assertIn("check_docker_container", tool_names)
        self.assertIn("restart_backend", tool_names)
        self.assertIn("verify_incident", tool_names)

    def test_act_before_approval_raises(self):
        tools.CLUSTER.stop("visionnoc-backend")
        img = tools.capture_dashboard("down", "healthy")["image_path"]
        incident = agent_ops.run_full_cycle(img, auto_approve=False)
        with self.assertRaises(ValueError):
            agent_ops.act(incident)  # must refuse: not approved yet

    def test_reject_prevents_remediation(self):
        tools.CLUSTER.stop("visionnoc-backend")
        img = tools.capture_dashboard("down", "healthy")["image_path"]
        incident = agent_ops.run_full_cycle(img, auto_approve=False)
        agent_ops.reject(incident, rejected_by="test")
        self.assertEqual(incident.status, "rejected")
        self.assertEqual(tools.CLUSTER.inspect("visionnoc-backend")["status"], "stopped")
        with self.assertRaises(ValueError):
            agent_ops.act(incident)

    def test_incident_ids_are_unique(self):
        i1 = Incident.new({"overall_state": "healthy"})
        i2 = Incident.new({"overall_state": "healthy"})
        self.assertNotEqual(i1.incident_id, i2.incident_id)

    def test_audit_trail_records_every_tool_call(self):
        tools.CLUSTER.stop("visionnoc-backend")
        img = tools.capture_dashboard("down", "healthy")["image_path"]
        incident = agent_ops.run_full_cycle(img, auto_approve=True)
        # investigate (4) + act (1) + verify (1) = 6 recorded tool calls
        self.assertEqual(len(incident.tool_calls), 6)
        for call in incident.tool_calls:
            self.assertIn("tool", call)
            self.assertIn("output", call)
            self.assertIn("timestamp", call)


if __name__ == "__main__":
    unittest.main()
