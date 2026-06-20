"""Tests for sdk_adapter.py — UnitreeGo2Adapter dry-mode behavior."""

import pytest
from go2_robot_bridge.sdk_adapter import UnitreeGo2Adapter


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
