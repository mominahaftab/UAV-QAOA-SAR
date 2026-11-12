"""Integration tests for backend API routes.

Uses direct endpoint handlers to ensure zero thread-portal blocking on sandboxed Windows environments.
"""
from backend.api.v1.router import health_check
from backend.main import root


def test_root_endpoint():
    data = root()
    assert "UAV-QAOA-SAR" in data["message"]
    assert data["health_check"] == "/api/v1/health"


def test_health_endpoint():
    data = health_check()
    assert data == {"status": "ok", "service": "uav-qaoa-sar-backend"}
