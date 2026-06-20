"""Tests for mission_library.py — MissionLibrary loading and queries."""

import pytest
from go2_robot_bridge.mission_library import MissionLibrary


class TestMissionLibrary:
    @pytest.fixture
    def library(self):
        return MissionLibrary()

    def test_list_missions_returns_all(self, library):
        missions = library.list_missions()
        names = {m["name"] for m in missions}
        expected = {
            "go2_demo_patrol",
            "go2_inspection_walk",
            "go2_status_report",
        }
        assert names == expected

    def test_list_missions_has_metadata(self, library):
        for mission in library.list_missions():
            assert "name" in mission
            assert "description" in mission
            assert "risk" in mission
            assert "requires_confirmation" in mission
            assert "max_duration_s" in mission
            assert "step_count" in mission

    def test_get_mission_returns_steps(self, library):
        mission = library.get_mission("go2_demo_patrol")
        assert "steps" in mission
        assert len(mission["steps"]) > 0

    def test_get_mission_unknown_raises_keyerror(self, library):
        with pytest.raises(KeyError, match="Unknown mission"):
            library.get_mission("nonexistent_mission")

    def test_get_mission_read_only_has_no_confirmation(self, library):
        mission = library.get_mission("go2_status_report")
        assert mission["requires_confirmation"] is False
        assert mission["risk"] == "read_only"

    def test_get_mission_motion_requires_confirmation(self, library):
        mission = library.get_mission("go2_demo_patrol")
        assert mission["requires_confirmation"] is True
        assert mission["risk"] == "low_motion"

    def test_get_mission_has_max_duration(self, library):
        mission = library.get_mission("go2_demo_patrol")
        assert "max_duration" in mission
        assert mission["max_duration"] > 0

    def test_get_mission_has_world_state_for_inspection(self, library):
        mission = library.get_mission("go2_inspection_walk")
        assert "world_state" in mission
        assert "waypoints" in mission["world_state"]
        assert len(mission["world_state"]["waypoints"]) >= 2
