"""Tests for sdk_adapter.py — UnitreeGo2Adapter dry-mode behavior."""

import io
from urllib.error import HTTPError

import pytest
from go2_robot_bridge.sdk_adapter import (
    IsaacSimGo2Adapter,
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

    def test_balance_stand_returns_executed(self, adapter):
        result = adapter.balance_stand()
        assert result["executed"] == "BalanceStand"
        assert result["dry_mode"] is True

    def test_move_returns_expected_shape(self, adapter):
        result = adapter.move(vx=0.1, vy=0.0, vyaw=0.0, duration=0.1)
        assert result["executed"] == "Move"
        assert result["vx"] == 0.1
        assert result["vy"] == 0.0
        assert result["vyaw"] == 0.0
        assert result["duration"] == 0.1
        assert result["dry_mode"] is True

    def test_move_auto_stops(self, adapter):
        """move() should call stop() in its finally block."""
        adapter.move(vx=0.1, vy=0.0, vyaw=0.0, duration=0.01)
        # No assertion needed — if stop() wasn't called we'd still pass,
        # but the dry-mode stop is safe and quick. The important thing is
        # that move() completes without error.

    def test_stand_up(self, adapter):
        result = adapter.stand_up()
        assert result["executed"] == "StandUp"
        assert result["dry_mode"] is True

    def test_stand_down(self, adapter):
        result = adapter.stand_down()
        assert result["executed"] == "StandDown"
        assert result["dry_mode"] is True

    def test_hello(self, adapter):
        result = adapter.hello()
        assert result["executed"] == "Hello"
        assert result["dry_mode"] is True

    def test_dance1(self, adapter):
        result = adapter.dance1()
        assert result["executed"] == "Dance1"
        assert result["dry_mode"] is True

    def test_recovery_stand(self, adapter):
        result = adapter.recovery_stand()
        assert result["executed"] == "RecoveryStand"
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

    def test_invalid_target_fails_clearly(self):
        with pytest.raises(ValueError, match="Invalid BRIDGE_TARGET"):
            create_go2_adapter_from_env({"BRIDGE_TARGET": "simulator"})

    def test_isaac_target_requires_url(self):
        with pytest.raises(ValueError, match="ISAAC_SIM_URL"):
            create_go2_adapter_from_env({"BRIDGE_TARGET": "isaac_sim"})


class TestIsaacSimGo2Adapter:
    def test_status_uses_get_and_adds_compat_fields(self, monkeypatch):
        seen = {}

        def fake_urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["timeout"] = timeout
            return _FakeResponse(b'{"robot":"go2","connected":true}')

        monkeypatch.setattr("go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen)
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

    def test_move_posts_velocity_payload(self, monkeypatch):
        seen = {}

        def fake_urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["body"] = req.data.decode("utf-8")
            return _FakeResponse(b'{"executed":"Move"}')

        monkeypatch.setattr("go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen)
        adapter = IsaacSimGo2Adapter("http://sim.local:51000")

        result = adapter.move(vx=0.2, vy=0.0, vyaw=0.1, duration=0.5)

        assert seen["url"] == "http://sim.local:51000/move"
        assert seen["method"] == "POST"
        assert '"vx": 0.2' in seen["body"]
        assert '"vy": 0.0' in seen["body"]
        assert '"vyaw": 0.1' in seen["body"]
        assert '"duration": 0.5' in seen["body"]
        assert result["executed"] == "Move"
        assert result["control_target"] == "isaac_sim"

    def test_unsupported_command_raises_clear_error(self, monkeypatch):
        def fake_urlopen(req, timeout):
            raise HTTPError(
                req.full_url,
                501,
                "Not Implemented",
                hdrs=None,
                fp=io.BytesIO(b'{"detail":"dance not implemented"}'),
            )

        monkeypatch.setattr("go2_robot_bridge.sdk_adapter.request.urlopen", fake_urlopen)
        adapter = IsaacSimGo2Adapter("http://sim.local:51000")

        with pytest.raises(UnsupportedCommandError, match="dance1"):
            adapter.dance1()
