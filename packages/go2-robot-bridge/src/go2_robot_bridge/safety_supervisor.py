"""Safety supervisor — validates actions against configured limits."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .controller_command import ALLOWED_POSTURES


class SafetySupervisor:
    """Enforces safety limits on actions before execution.

    Validates step vocabulary, posture names, speed, duration, move-step count,
    confirmation requirements, and rejects unknown or freeform actions.
    """

    def __init__(
        self, limits: Optional[Dict[str, Any]] = None, limits_path: Optional[str] = None
    ):
        if limits is not None:
            self._limits = limits
        elif limits_path is not None:
            with open(limits_path, "r", encoding="utf-8") as f:
                self._limits = yaml.safe_load(f)
        else:
            default_path = (
                Path(__file__).resolve().parent / "config" / "safety_limits.yaml"
            )
            with default_path.open("r", encoding="utf-8") as f:
                self._limits = yaml.safe_load(f)

    def validate_action(
        self, action_name: str, action: Dict[str, Any], confirmed: bool
    ) -> None:
        """Validate an action before execution.

        Raises:
            PermissionError: If action requires confirmation but not confirmed.
            ValueError: If the step vocabulary, posture, speed, duration, or move
                step count exceeds bridge limits.
        """
        limits = self._limits["limits"]
        requires_confirmation = action.get("requires_confirmation", True)

        if requires_confirmation and not confirmed:
            raise PermissionError(
                f"Action '{action_name}' requires human confirmation. "
                f"Set confirmed=True to proceed."
            )

        allowed_step_types = {"status", "stop", "posture", "move", "wait"}
        move_count = 0
        for step in action.get("steps", []):
            step_type = step.get("type")
            if step_type not in allowed_step_types:
                raise ValueError(f"Unknown action step type: {step_type}")

            if step_type == "posture":
                self._validate_posture(step)

            if step_type == "move":
                move_count += 1
                self._validate_move_speeds(step, limits["go2"])
                self._validate_move_duration(step, limits["max_move_duration"])

        max_move_steps = limits["max_move_steps_per_action"]
        if move_count > max_move_steps:
            raise ValueError(
                f"Action '{action_name}' has {move_count} move steps, "
                f"max allowed is {max_move_steps}"
            )

    def _validate_posture(self, step: Dict[str, Any]) -> None:
        name = str(step.get("name", ""))
        if name not in ALLOWED_POSTURES:
            allowed = ", ".join(sorted(ALLOWED_POSTURES))
            raise ValueError(f"Unsupported posture '{name}'. Allowed: {allowed}")

    def _validate_move_speeds(
        self, step: Dict[str, Any], go2_limits: Dict[str, Any]
    ) -> None:
        vx = abs(float(step.get("vx", 0.0)))
        vy = abs(float(step.get("vy", 0.0)))
        vyaw = abs(float(step.get("vyaw", 0.0)))

        if vx > go2_limits["max_vx"]:
            raise ValueError(f"vx {vx} exceeds safety limit {go2_limits['max_vx']}")
        if vy > go2_limits["max_vy"]:
            raise ValueError(f"vy {vy} exceeds safety limit {go2_limits['max_vy']}")
        if vyaw > go2_limits["max_vyaw"]:
            raise ValueError(
                f"vyaw {vyaw} exceeds safety limit {go2_limits['max_vyaw']}"
            )

    def _validate_move_duration(
        self, step: Dict[str, Any], max_duration: float
    ) -> None:
        duration = float(step.get("duration", 0.0))
        if duration > max_duration:
            raise ValueError(
                f"Move duration {duration}s exceeds safety limit {max_duration}s"
            )

    def clamp_move_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Clamp a move step's velocities and duration to safety limits."""
        go2_limits = self._limits["limits"]["go2"]
        max_duration = self._limits["limits"]["max_move_duration"]

        clamped = dict(step)
        clamped["vx"] = max(
            -go2_limits["max_vx"], min(go2_limits["max_vx"], float(step.get("vx", 0.0)))
        )
        clamped["vy"] = max(
            -go2_limits["max_vy"], min(go2_limits["max_vy"], float(step.get("vy", 0.0)))
        )
        clamped["vyaw"] = max(
            -go2_limits["max_vyaw"],
            min(go2_limits["max_vyaw"], float(step.get("vyaw", 0.0))),
        )
        clamped["duration"] = min(max_duration, float(step.get("duration", 0.0)))
        return clamped
