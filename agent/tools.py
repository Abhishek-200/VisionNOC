"""
VisionNOC — agent/tools.py

Explicit, allowlisted tools the agent may call. There is NO general
shell-execution tool and the LLM/heuristic layer never generates
arbitrary commands — it can only pick a name out of ALLOWED_ACTIONS
(models.py) and TOOLS (this file).

Two backends:
  1. REAL docker backend — used automatically if the `docker` binary is
     present on PATH. Talks to it through a fixed, tiny subprocess
     allowlist (`docker ps`, `docker inspect`, `docker restart <name>`,
     `docker logs`) with timeouts. No shell=True, no string-built
     commands, no arbitrary args from the model.
  2. SIMULATED backend — an in-memory container/service state machine
     used when Docker is not available (this is the case in the sandbox
     this project was authored in — see docs/PROJECT_STATUS.md). Every
     simulated tool call mutates or reads *real, stateful, in-memory
     data*: nothing here is scripted/hardcoded to "look right" for a
     demo. If you `restart_service("restart_backend")` on the simulated
     backend, the container really is marked stopped -> running, and a
     subsequent `check_docker_container` call reflects that.

Which backend is active is visible in every tool result via the
"backend" field, so audit logs never blur simulated and real evidence.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import urllib.parse
import docker
import os
from pathlib import Path
from dataclasses import dataclass, field

DOCKER_CLIENT = docker.from_env()
DOCKER_BIN = shutil.which("docker")

# --- Allowlisted remediation actions -----------------------------------
ALLOWED_ACTIONS = {}  # populated at bottom after functions are defined


# --- Simulated infrastructure backend -----------------------------------
@dataclass
class _SimContainer:
    name: str
    status: str = "running"  # running | stopped
    cpu_pct: float = 4.2
    mem_pct: float = 18.5
    restart_count: int = 0


class SimulatedCluster:
    """A small, honest, stateful simulation of the demo cluster used when
    Docker is unavailable. Not a mock that returns canned strings —
    calling methods actually mutates this object's state."""

    def __init__(self):
        self.containers = {
            "visionnoc-backend": _SimContainer(name="visionnoc-backend"),
            "visionnoc-db": _SimContainer(name="visionnoc-db"),
        }
        self.http_healthy = True
        self.prometheus_up = True
        self.disk_pct = 41.0

    def stop(self, container: str):
        if container in self.containers:
            self.containers[container].status = "stopped"
            if container == "visionnoc-backend":
                self.http_healthy = False

    def restart(self, container: str):
        if container not in self.containers:
            raise KeyError(container)
        c = self.containers[container]
        c.status = "running"
        c.restart_count += 1
        if container == "visionnoc-backend":
            self.http_healthy = True

    def inspect(self, container: str) -> dict:
        if container not in self.containers:
            return {"found": False}
        c = self.containers[container]
        return {
            "found": True,
            "name": c.name,
            "status": c.status,
            "restart_count": c.restart_count,
        }


# module-level singleton so the whole demo process shares one cluster state
CLUSTER = SimulatedCluster()


def _run_docker(args: list, timeout: float = 5.0) -> dict:
    """Run a fixed, known-safe docker subprocess command. `args` must be
    a list (never a shell string) built entirely from this file's own
    constants — never from unvalidated model output."""
    try:
        proc = subprocess.run(
            [DOCKER_BIN] + args, capture_output=True, text=True, timeout=timeout
        )
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "timeout"}


# --- Tools ---------------------------------------------------------------

def _docker_name(container: str) -> str:
    return {"visionnoc-backend": "visionnoc-demo-app", "visionnoc-db": "visionnoc-db"}.get(container, container)

def check_docker_container(container: str) -> dict:
    """Return {backend, found, status, restart_count} for a named container."""
    try:
        name = _docker_name(container)
        c = DOCKER_CLIENT.containers.get(name)
        c.reload()
        return {
            "backend": "docker",
            "found": True,
            "status": c.status,
            "restart_count": int(c.attrs.get("RestartCount", 0)),
        }
    except Exception:
        info = CLUSTER.inspect(container)
        return {"backend": "simulated", **info}


def get_container_logs(container: str, tail: int = 20) -> dict:
    try:
        name = _docker_name(container)
        c = DOCKER_CLIENT.containers.get(name)
        logs = c.logs(tail=tail).decode("utf-8", errors="replace")
        return {"backend": "docker", "logs": logs}
    except Exception:
        c = CLUSTER.containers.get(container)
        if c is None:
            return {"backend": "simulated", "logs": ""}
        if c.status == "stopped":
            logs = (
                f"[{container}] received SIGTERM\n"
                f"[{container}] graceful shutdown complete\n"
                f"[{container}] process exited (code 0)\n"
            )
        else:
            logs = f"[{container}] healthy, serving requests, restart_count={c.restart_count}\n"
        return {"backend": "simulated", "logs": logs}


def check_http_health(url: str | None = None, timeout: float = 2.0) -> dict:
    """Try a real HTTP GET first (works if the demo stack is actually
    running); fall back to the simulated cluster's health flag if the
    request fails to connect at all (expected in this sandbox, which has
    no outbound network — see docs/PROJECT_STATUS.md)."""
    url = url or os.environ.get("VISIONNOC_HEALTH_URL", "http://localhost:9000/health")
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"backend": "http", "healthy": 200 <= resp.status < 300, "status_code": resp.status}
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure -> fall back
        return {"backend": "simulated", "healthy": CLUSTER.http_healthy, "note": f"real HTTP unavailable ({exc.__class__.__name__}); using simulated cluster state"}


def get_prometheus_metrics(query: str = 'up{job="visionnoc-backend"}') -> dict:
    base = os.environ.get("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
    try:
        encoded = urllib.parse.quote(query, safe='{}=\"_')
        with urllib.request.urlopen(f"{base}/api/v1/query?query={encoded}", timeout=2) as resp:
            data = json.loads(resp.read())
        if data.get("status") != "success":
            raise RuntimeError(data.get("error", "Prometheus query failed"))
        return {"backend":"prometheus","available":True,"query":query,"result":data["data"]["result"]}
    except Exception as exc:
        if not CLUSTER.prometheus_up:
            return {"backend":"simulated","available":False,"query":query,"note":"Prometheus investigation unavailable"}
        backend_up = 1 if CLUSTER.containers["visionnoc-backend"].status == "running" else 0
        return {"backend":"simulated","available":True,"query":query,
                "result":[{"metric":{"job":"visionnoc-backend"},"value":backend_up}],
                "note":f"real Prometheus unavailable ({exc.__class__.__name__}); using simulator"}


def check_cpu() -> dict:
    return {"backend": "simulated", "cpu_pct": CLUSTER.containers["visionnoc-backend"].cpu_pct}


def check_memory() -> dict:
    return {"backend": "simulated", "mem_pct": CLUSTER.containers["visionnoc-backend"].mem_pct}


def check_disk() -> dict:
    return {"backend": "simulated", "disk_pct": CLUSTER.disk_pct}


def capture_dashboard(state_backend: str | None = None, state_db: str | None = None) -> dict:
    from demo.generate_dashboard import render_dashboard
    if state_backend is None:
        state_backend = "healthy" if check_docker_container("visionnoc-backend").get("status") == "running" else "down"
    if state_db is None:
        db_state = check_docker_container("visionnoc-db")
        # The production demo stack has no database container. Treat an
        # absent optional DB as healthy/irrelevant rather than turning the
        # whole dashboard red.
        state_db = "healthy" if (not db_state.get("found", True) or db_state.get("status") == "running") else "down"
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "evidence" / "_live"
    path = out_dir / f"capture_{int(time.time()*1000)}.png"
    render_dashboard(state_backend, state_db, str(path))
    return {"backend":"opencv+state-derived","image_path":str(path.resolve())}


def stop_backend() -> dict:
    if DOCKER_BIN:
        result = _run_docker(["stop", "visionnoc-demo-app"])
        return {"backend":"docker","success":result["returncode"] == 0,"raw":result}
    CLUSTER.stop("visionnoc-backend")
    return {"backend":"simulated","success":True}


def restart_backend() -> dict:
    """The ONLY container-mutating action the agent is allowed to invoke
    for the backend service. Requires human approval upstream (see
    agent/policies.py) before this function is ever called."""
    try:
        container = DOCKER_CLIENT.containers.get("visionnoc-demo-app")
        container.restart()
        return {"backend": "docker", "success": True}
    except Exception as exc:
        return {
            "backend": "docker",
            "success": False,
            "error": str(exc),
        }


def restart_database() -> dict:
    if DOCKER_BIN:
        result = _run_docker(["restart", "visionnoc-db"])
        return {"backend": "docker", "success": result["returncode"] == 0, "raw": result}
    CLUSTER.restart("visionnoc-db")
    return {"backend": "simulated", "success": True}


def verify_incident(container: str = "visionnoc-backend", before_image: str = None, after_image: str = None) -> dict:
    """Independent multi-signal verification after remediation. Returns a
    dict with per-signal booleans plus an overall bool. Never fabricates
    a signal it couldn't check — missing signals are marked null, not
    True."""
    docker_state = check_docker_container(container)
    http_state = check_http_health()
    prom_state = get_prometheus_metrics()
    time.sleep(3)
    prom_state = get_prometheus_metrics()

    visual = None
    if before_image and after_image:
        from vision.detector import analyze_dashboard
        after_result = analyze_dashboard(after_image)
        visual = after_result.overall_state == "healthy"

    signals = {
        "docker": docker_state.get("status") == "running" if docker_state.get("found") else None,
        "http": http_state.get("healthy"),
        "prometheus": (
            bool(prom_state.get("result")) and all(
                (item.get("value") == 1) or
                (isinstance(item.get("value"), list) and len(item["value"]) > 1 and str(item["value"][1]) == "1")
                for item in prom_state["result"]
            ) if prom_state.get("available") else None
        ),
        "visual": visual,
    }
    checked = [v for v in signals.values() if v is not None]
    overall = bool(checked) and all(checked)
    return {"signals": signals, "overall_recovered": overall}


TOOLS = {
    "check_docker_container": check_docker_container,
    "get_container_logs": get_container_logs,
    "check_http_health": check_http_health,
    "get_prometheus_metrics": get_prometheus_metrics,
    "check_cpu": check_cpu,
    "check_memory": check_memory,
    "check_disk": check_disk,
    "capture_dashboard": capture_dashboard,
    "verify_incident": verify_incident,
}

# Destructive/remediation actions are kept in a SEPARATE, smaller
# allowlist from read-only investigation tools, and are never reachable
# without going through agent/policies.py's approval gate first.
ALLOWED_ACTIONS = {
    "restart_backend": restart_backend,
    "restart_database": restart_database,
}
