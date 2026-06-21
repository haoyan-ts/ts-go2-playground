"""Tests for sdk_adapter.py control target behavior."""

import io
from urllib.error import HTTPError

import pytest
from go2_robot_bridge.controller_command import ControllerCommandEnvelope
from go2_robot_bridge.sdk_adapter import (
    IsaacSimGo2Adapter,
    MuJoCoGo2Adapter,
    UnitreeGo2Adapter,
    UnsupportedCommandError,
    create_go2_adapter_from_env,
)


class TestUnitreeGo2AdapterDryMode:
    """All tests use dry_mode=True — no real hardware needed."""

    @pytest.fixture
    def adapter(self):
        return UnitreeGo2Adapter(dry_mode=True)

    def test_status_returns_expected_keys(self, adapter):
        result = adapter.status()
        assert result["robot"] == "go2"
        assert result["connected"] is True
        assert result["dry_mode"] is True
        assert "safe_to_move" in result

    def test_stop_returns_executed(self, adapter):
        result = adapter.stop()
        assert result["executed"] == "StopMove"
        assert result["dry_mode"] is True

    def test_posture_command_returns_controller_result(self, adapter):
        result = adapter.execute_controller_command(
            ControllerCommandEnvelope.posture("balance_stand")
        )
        assert result["executed"] == "controller_command"
        assert result["intent"] == "posture"
        assert result["params"] == {"name": "balance_stand"}
        assert result["sdk_call"] == "BalanceStand"
        assert result["dry_mode"] is True

    def test_move_command_returns_expected_shape(self, adapter):
        result = adapter.execute_controller_command(
            ControllerCommandEnvelope.move(vx=0.1, vy=0.0, vyaw=0.0, duration=0.1)
        )
        assert result["executed"] == "controller_command"
        assert result["intent"] == "move"
        assert result["params"]["vx"] == 0.1
        assert result["params"]["vy"] == 0.0
        assert result["params"]["vyaw"] == 0.0
        assert result["params"]["duration"] == 0.1
        assert result["dry_mode"] is True


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


class TestAdapterFactory:
    def test_default_target_is_dry(self):
        adapter = create_go2_adapter_from_env({})
        assert isinstance(adapter, UnitreeGo2Adapter)
        assert adapter.dry_mode is True
        assert adapter.control_target == "dry"

    def test_isaac_target_creates_isaac_adapter(self):
        adapter = create_go2_adapter_from_env(
            {
                "BRIDGE_TARGET": "isaac_sim",
                "ISAAC_SIM_URL": "http://127.0.0.1:51000",
            }
        )
        assert isinstance(adapter, IsaacSimGo2Adapter)
        assert adapter.dry_mode is False
        assert adapter.control_target == "isaac_sim"
        assert adapter.base_url == "http://127.0.0.1:51000/"

    def test_mujoco_target_creates_mujoco_adapter(self):
        adapter = create_go2_adapter_from_env(
            {
                "BRIDGE_TARGET": "mujoco",
                "MUJOCO_URL": "http://127.0.0.1:52000",
            }
        )
        assert isinstance(adapter, MuJoCoGo2Adapter)
        assert adapter.dry_mode is False
        assert adapter.control_target == "mujoco"
        assert adapter.base_url == "http://127.0.0.1:52000/"

    def test_invalid_target_fails_clearly(self):
        with pytest.raises(ValueError, match="Invalid BRIDGE_TARGET"):
            create_go2_adapter_from_env({"BRIDGE_TARGET": "simulator"})

    def test_isaac_target_requires_url(self):
        with pytest.raises(ValueError, match="ISAAC_SIM_URL"):
            create_go2_adapter_from_env({"BRIDGE_TARGET": "isaac_sim"})

    def test_mujoco_target_requires_url(self):
        with pytest.raises(ValueError, match="MUJOCO_URL"):
            create_go2_adapter_from_env({"BRIDGE_TARGET": "mujoco"})


class TestIsaacSimGo2Adapter:
    def test_status_uses_get_and_adds_compat_fields(self, monkeypatch):
        seen = {}

        def fake_urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["timeout"] = timeout
            return _FakeResponse(b'{"robot":"go2","connected":true}')

        monkeypatch.setattr(
            "go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen
        )
        adapter = IsaacSimGo2Adapter("http://sim.local:51000", timeout=3.0)

        result = adapter.status()

        assert seen == {
            "url": "http://sim.local:51000/status",
            "method": "GET",
            "timeout": 3.0,
        }
        assert result["robot"] == "go2"
        assert result["connected"] is True
        assert result["dry_mode"] is False
        assert result["control_target"] == "isaac_sim"

    def test_execute_posts_controller_command_envelope(self, monkeypatch):
        seen = {}

        def fake_urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["body"] = req.data.decode("utf-8")
            return _FakeResponse(b'{"executed":"controller_command"}')

        monkeypatch.setattr(
            "go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen
        )
        adapter = IsaacSimGo2Adapter("http://sim.local:51000")

        result = adapter.execute_controller_command(
            ControllerCommandEnvelope.move(vx=0.2, vy=0.0, vyaw=0.1, duration=0.5)
        )

        assert seen["url"] == "http://sim.local:51000/controller-command"
        assert seen["method"] == "POST"
        assert '"command_type": "controller_command"' in seen["body"]
        assert '"intent": "move"' in seen["body"]
        assert '"vx": 0.2' in seen["body"]
        assert '"duration": 0.5' in seen["body"]
        assert result["executed"] == "controller_command"
        assert result["control_target"] == "isaac_sim"

    def test_unsupported_controller_command_raises_clear_error(self, monkeypatch):
        def fake_urlopen(req, timeout):
            raise HTTPError(
                req.full_url,
                501,
                "Not Implemented",
                hdrs=None,
                fp=io.BytesIO(b'{"detail":"controller not implemented"}'),
            )

        monkeypatch.setattr(
            "go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen
        )
        adapter = IsaacSimGo2Adapter("http://sim.local:51000")

        with pytest.raises(UnsupportedCommandError, match="controller-command"):
            adapter.execute_controller_command(
                ControllerCommandEnvelope.posture("balance_stand")
            )


class TestMuJoCoGo2Adapter:
    def test_execute_posts_same_controller_command_shape(self, monkeypatch):
        seen = {}

        def fake_urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["body"] = req.data.decode("utf-8")
            return _FakeResponse(b'{"executed":"controller_command"}')

        monkeypatch.setattr(
            "go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen
        )
        adapter = MuJoCoGo2Adapter("http://mujoco.local:52000")

        result = adapter.execute_controller_command(
            ControllerCommandEnvelope.posture("balance_stand")
        )

        assert seen["url"] == "http://mujoco.local:52000/controller-command"
        assert seen["method"] == "POST"
        assert '"intent": "posture"' in seen["body"]
        assert '"name": "balance_stand"' in seen["body"]
        assert result["control_target"] == "mujoco"
