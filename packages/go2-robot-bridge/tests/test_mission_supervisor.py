"""Tests for mission_supervisor.py — MissionSupervisor validation and execution."""

import pytest
from go2_robot_bridge.action_library import ActionLibrary
from go2_robot_bridge.safety_supervisor import SafetySupervisor
from go2_robot_bridge.sdk_adapter import UnitreeGo2Adapter
from go2_robot_bridge.logger import Logger
from go2_robot_bridge.mission_library import MissionLibrary
from go2_robot_bridge.mission_supervisor import MissionSupervisor


class TestMissionSupervisor:
    @pytest.fixture
    def action_library(self):
        return ActionLibrary()

    @pytest.fixture
    def safety_supervisor(self):
        return SafetySupervisor()

    @pytest.fixture
    def adapter(self):
        return UnitreeGo2Adapter(dry_mode=True)

    @pytest.fixture
    def logger(self, tmp_path):
        return Logger(log_path=tmp_path / "test_mission.log")

    @pytest.fixture
    def mission_library(self):
        return MissionLibrary()

    @pytest.fixture
    def supervisor(self, action_library, safety_supervisor, adapter, logger):
        return MissionSupervisor(
            action_library=action_library,
            safety_supervisor=safety_supervisor,
            adapter=adapter,
            logger=logger,
        )

    # ------------------------------------------------------------------
    # Validation tests
    # ------------------------------------------------------------------

    def test_validate_read_only_no_confirm_passes(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_status_report")
        # Should not raise
        supervisor.validate_mission("go2_status_report", mission, confirmed=False)

    def test_validate_motion_without_confirm_raises(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_demo_patrol")
        with pytest.raises(PermissionError, match="human confirmation"):
            supervisor.validate_mission("go2_demo_patrol", mission, confirmed=False)

    def test_validate_motion_with_confirm_passes(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_demo_patrol")
        supervisor.validate_mission("go2_demo_patrol", mission, confirmed=True)
        # Should not raise

    # ------------------------------------------------------------------
    # Execution tests — read-only mission
    # ------------------------------------------------------------------

    def test_execute_read_only_mission(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_status_report")
        result = supervisor.execute_mission(
            "go2_status_report", mission, confirmed=False
        )
        assert result["name"] == "go2_status_report"
        assert result["status"] == "completed"
        assert result["duration_s"] >= 0
        assert "steps" in result
        assert "final_report" in result
        assert result["final_report"]["status"] == "completed"

    # ------------------------------------------------------------------
    # Execution tests — motion mission
    # ------------------------------------------------------------------

    def test_execute_motion_without_confirm_raises(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_demo_patrol")
        with pytest.raises(PermissionError, match="human confirmation"):
            supervisor.execute_mission("go2_demo_patrol", mission, confirmed=False)

    def test_execute_motion_with_confirm_succeeds(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_demo_patrol")
        result = supervisor.execute_mission("go2_demo_patrol", mission, confirmed=True)
        assert result["name"] == "go2_demo_patrol"
        assert result["status"] == "completed"
        assert len(result["steps"]) > 0
        assert "final_report" in result

    # ------------------------------------------------------------------
    # E-stop tests
    # ------------------------------------------------------------------

    def test_estop_interrupts_mission(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_demo_patrol")
        # Trigger E-stop before execution
        supervisor.trigger_estop()
        result = supervisor.execute_mission("go2_demo_patrol", mission, confirmed=True)
        assert result["status"] == "estop_interrupted"
        assert len(result["steps"]) == 0  # No steps executed

    def test_estop_flag_resets_between_missions(self, supervisor, mission_library):
        # First mission with E-stop
        mission = mission_library.get_mission("go2_status_report")
        supervisor.trigger_estop()
        result1 = supervisor.execute_mission(
            "go2_status_report", mission, confirmed=False
        )
        assert result1["status"] == "estop_interrupted"

        # Second mission should start fresh (estop reset)
        result2 = supervisor.execute_mission(
            "go2_status_report", mission, confirmed=False
        )
        assert result2["status"] == "completed"

    # ------------------------------------------------------------------
    # Max duration tests
    # ------------------------------------------------------------------

    def test_mission_with_short_max_duration_times_out(
        self, supervisor, mission_library
    ):
        """Give a zero max_duration and verify it times out before any step."""
        mission = mission_library.get_mission("go2_demo_patrol")
        # Override max_duration to 0 — first elapsed check always triggers timeout
        mission["max_duration"] = 0.0
        result = supervisor.execute_mission("go2_demo_patrol", mission, confirmed=True)
        assert result["status"] == "timeout"

    # ------------------------------------------------------------------
    # World state / perception tests
    # ------------------------------------------------------------------

    def test_world_state_initially_clean(self, supervisor):
        ws = supervisor.world_state
        assert ws["robot"] == "go2"
        assert ws["estop_triggered"] is False

    def test_perception_summary(self, supervisor):
        summary = supervisor.perception_summary()
        assert "robot_status" in summary
        assert "world_state" in summary

    def test_observe_returns_summary(self, supervisor):
        summary = supervisor.observe(duration=0.1)
        assert "robot_status" in summary
        assert "world_state" in summary
        assert summary["world_state"]["estop_triggered"] is False

    def test_observe_with_waypoint(self, supervisor):
        summary = supervisor.observe(duration=0.1, waypoint="wp_test")
        assert summary.get("waypoint") == "wp_test"

    # ------------------------------------------------------------------
    # Report tests
    # ------------------------------------------------------------------

    def test_final_report_contains_expected_fields(self, supervisor, mission_library):
        mission = mission_library.get_mission("go2_status_report")
        result = supervisor.execute_mission(
            "go2_status_report", mission, confirmed=False
        )
        report = result["final_report"]
        assert "mission" in report
        assert "status" in report
        assert "total_duration_s" in report
        assert "action_count" in report
        assert "observation_count" in report
        assert "estop_triggered" in report
        assert "robot_status" in report
