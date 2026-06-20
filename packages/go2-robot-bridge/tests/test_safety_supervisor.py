"""Tests for safety_supervisor.py — SafetySupervisor validation and clamping."""

import pytest
from go2_robot_bridge.safety_supervisor import SafetySupervisor


class TestSafetySupervisor:
    @pytest.fixture
    def supervisor(self):
        return SafetySupervisor()

    def test_validate_read_only_no_confirm(self, supervisor):
        """Read-only actions should pass without confirmation."""
        action = {
            "requires_confirmation": False,
            "risk": "read_only",
            "steps": [{"type": "status"}],
        }
        supervisor.validate_action("go2_status_check", action, confirmed=False)
        # Should not raise

    def test_validate_motion_without_confirm_raises(self, supervisor):
        """Motion actions require confirmation."""
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 0.5}
            ],
        }
        with pytest.raises(PermissionError, match="human confirmation"):
            supervisor.validate_action("go2_forward_short", action, confirmed=False)

    def test_validate_motion_with_confirm_passes(self, supervisor):
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 0.5}
            ],
        }
        supervisor.validate_action("go2_forward_short", action, confirmed=True)
        # Should not raise

    def test_validate_excessive_vx_raises(self, supervisor):
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.5, "vy": 0.0, "vyaw": 0.0, "duration": 0.5}
            ],
        }
        with pytest.raises(ValueError, match="vx"):
            supervisor.validate_action("fast_move", action, confirmed=True)

    def test_validate_excessive_vy_raises(self, supervisor):
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.0, "vy": 0.2, "vyaw": 0.0, "duration": 0.5}
            ],
        }
        with pytest.raises(ValueError, match="vy"):
            supervisor.validate_action("side_move", action, confirmed=True)

    def test_validate_excessive_vyaw_raises(self, supervisor):
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.0, "vy": 0.0, "vyaw": 0.5, "duration": 0.5}
            ],
        }
        with pytest.raises(ValueError, match="vyaw"):
            supervisor.validate_action("fast_turn", action, confirmed=True)

    def test_validate_excessive_duration_raises(self, supervisor):
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 2.0}
            ],
        }
        with pytest.raises(ValueError, match="duration"):
            supervisor.validate_action("long_move", action, confirmed=True)

    def test_validate_too_many_move_steps_raises(self, supervisor):
        action = {
            "requires_confirmation": True,
            "risk": "low_motion",
            "steps": [
                {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 0.3},
                {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 0.3},
                {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 0.3},
            ],
        }
        with pytest.raises(ValueError, match="move steps"):
            supervisor.validate_action("many_moves", action, confirmed=True)

    def test_clamp_move_step_reduces_vx(self, supervisor):
        clamped = supervisor.clamp_move_step(
            {"type": "move", "vx": 0.5, "vy": 0.0, "vyaw": 0.0, "duration": 0.5}
        )
        assert clamped["vx"] == 0.20  # clamped to max

    def test_clamp_move_step_reduces_duration(self, supervisor):
        clamped = supervisor.clamp_move_step(
            {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 2.0}
        )
        assert clamped["duration"] == 1.0  # clamped to max

    def test_clamp_move_step_preserves_other_keys(self, supervisor):
        clamped = supervisor.clamp_move_step(
            {"type": "move", "vx": 0.1, "vy": 0.0, "vyaw": 0.0, "duration": 0.5}
        )
        assert clamped["type"] == "move"
        assert clamped["vx"] == 0.1  # within limits, unchanged
