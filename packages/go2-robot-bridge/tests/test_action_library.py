"""Tests for action_library.py — ActionLibrary loading and queries."""

import pytest
from go2_robot_bridge.action_library import ActionLibrary


class TestActionLibrary:
    @pytest.fixture
    def library(self):
        return ActionLibrary()

    def test_list_actions_returns_all(self, library):
        actions = library.list_actions()
        names = {a["name"] for a in actions}
        expected = {
            "go2_status_check",
            "go2_stop",
            "go2_balance_stand",
            "go2_forward_short",
            "go2_turn_left_short",
            "go2_turn_right_short",
            "go2_greeting_demo",
        }
        assert names == expected

    def test_list_actions_has_metadata(self, library):
        for action in library.list_actions():
            assert "name" in action
            assert "description" in action
            assert "risk" in action
            assert "requires_confirmation" in action

    def test_get_action_returns_steps(self, library):
        action = library.get_action("go2_forward_short")
        assert "steps" in action
        assert len(action["steps"]) > 0

    def test_get_action_unknown_raises_keyerror(self, library):
        with pytest.raises(KeyError, match="Unknown action"):
            library.get_action("nonexistent_action")

    def test_get_action_read_only_has_no_confirmation(self, library):
        action = library.get_action("go2_status_check")
        assert action["requires_confirmation"] is False
        assert action["risk"] == "read_only"

    def test_get_action_motion_requires_confirmation(self, library):
        action = library.get_action("go2_forward_short")
        assert action["requires_confirmation"] is True
        assert action["risk"] == "low_motion"

    def test_action_names_returns_all(self, library):
        names = library.action_names()
        assert len(names) == 7
        assert "go2_stop" in names

    def test_get_action_returns_copy_not_reference(self, library):
        a1 = library.get_action("go2_stop")
        a2 = library.get_action("go2_stop")
        a1["steps"] = []
        assert len(a2["steps"]) > 0  # original not mutated
