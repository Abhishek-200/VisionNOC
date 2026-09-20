"""
VisionNOC — store/db.py

SQLite-backed incident persistence (spec section 21 — SQLite is
explicitly acceptable for the MVP; there's no reason here to reach for
Postgres).
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager

from agent.models import Incident

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "visionnoc.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


class IncidentStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, incident: Incident) -> None:
        payload = json.dumps(incident.to_dict())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO incidents (incident_id, created_at, status, payload) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(incident_id) DO UPDATE SET status=excluded.status, payload=excluded.payload",
                (incident.incident_id, incident.created_at, incident.status, payload),
            )

    def get(self, incident_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM incidents WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit: int = 50) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(r[0]) for r in rows]
