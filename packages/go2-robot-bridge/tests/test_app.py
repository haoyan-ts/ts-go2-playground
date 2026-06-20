"""Tests for Robot Bridge API target metadata."""

from fastapi.testclient import TestClient

from go2_robot_bridge.app import create_app


class FakeIsaacAdapter:
    dry_mode = False
    control_target = "isaac_sim"

    def status(self):
        return {
            "robot": "go2",
            "connected": True,
            "dry_mode": self.dry_mode,
            "control_target": self.control_target,
        }

    def stop(self):
        return {
            "executed": "StopMove",
            "dry_mode": self.dry_mode,
            "control_target": self.control_target,
        }


def test_health_includes_dry_mode_and_control_target():
    app = create_app(adapter=FakeIsaacAdapter())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dry_mode": False,
        "control_target": "isaac_sim",
    }


def test_robot_status_distinguishes_isaac_target():
    app = create_app(adapter=FakeIsaacAdapter())
    client = TestClient(app)

    response = client.get("/robot/status")

    assert response.status_code == 200
    assert response.json()["dry_mode"] is False
    assert response.json()["control_target"] == "isaac_sim"
