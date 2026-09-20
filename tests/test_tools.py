import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import tools


class TestToolAllowlist(unittest.TestCase):
    def test_only_two_actions_are_allowlisted(self):
        self.assertEqual(set(tools.ALLOWED_ACTIONS.keys()), {"restart_backend", "restart_database"})

    def test_read_only_tools_do_not_include_restart(self):
        self.assertNotIn("restart_backend", tools.TOOLS)
        self.assertNotIn("restart_database", tools.TOOLS)


class TestSimulatedCluster(unittest.TestCase):
    def setUp(self):
        self.cluster = tools.SimulatedCluster()

    def test_initial_state_running(self):
        info = self.cluster.inspect("visionnoc-backend")
        self.assertEqual(info["status"], "running")

    def test_stop_then_inspect_reflects_stopped(self):
        self.cluster.stop("visionnoc-backend")
        info = self.cluster.inspect("visionnoc-backend")
        self.assertEqual(info["status"], "stopped")
        self.assertFalse(self.cluster.http_healthy)

    def test_restart_increments_count_and_marks_running(self):
        self.cluster.stop("visionnoc-backend")
        self.cluster.restart("visionnoc-backend")
        info = self.cluster.inspect("visionnoc-backend")
        self.assertEqual(info["status"], "running")
        self.assertEqual(info["restart_count"], 1)
        self.assertTrue(self.cluster.http_healthy)

    def test_inspect_unknown_container(self):
        info = self.cluster.inspect("nonexistent")
        self.assertFalse(info["found"])


class TestToolFunctions(unittest.TestCase):
    def setUp(self):
        tools.CLUSTER = tools.SimulatedCluster()  # isolate module singleton per test

    def test_check_docker_container_simulated(self):
        out = tools.check_docker_container("visionnoc-backend")
        self.assertEqual(out["backend"], "simulated")
        self.assertEqual(out["status"], "running")

    def test_restart_backend_actually_changes_state(self):
        tools.CLUSTER.stop("visionnoc-backend")
        self.assertEqual(tools.check_docker_container("visionnoc-backend")["status"], "stopped")
        tools.restart_backend()
        self.assertEqual(tools.check_docker_container("visionnoc-backend")["status"], "running")

    def test_prometheus_reflects_container_state(self):
        tools.CLUSTER.stop("visionnoc-backend")
        metrics = tools.get_prometheus_metrics()
        backend_metric = next(m for m in metrics["result"] if m["metric"]["job"] == "visionnoc-backend")
        self.assertEqual(backend_metric["value"], 0)

    def test_verify_incident_never_fabricates_missing_signal(self):
        # no before/after image provided -> visual signal must be None, not True/False
        out = tools.verify_incident(container="visionnoc-backend")
        self.assertIsNone(out["signals"]["visual"])


if __name__ == "__main__":
    unittest.main()
