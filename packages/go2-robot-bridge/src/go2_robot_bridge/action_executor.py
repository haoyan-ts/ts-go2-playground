"""Execution helpers for approved Robot Bridge action steps."""

import time
from typing import Any, Dict

from .controller_command import ControllerCommandEnvelope


def execute_bridge_step(
    step: Dict[str, Any],
    adapter: Any,
    safety_supervisor: Any,
) -> Dict[str, Any]:
    """Execute one approved action step through a control target."""
    step_type = step.get("type")

    if step_type == "status":
        return adapter.status()
    if step_type == "stop":
        return adapter.stop()
    if step_type == "posture":
        envelope = ControllerCommandEnvelope.posture(str(step.get("name", "")))
        return adapter.execute_controller_command(envelope)
    if step_type == "move":
        clamped = safety_supervisor.clamp_move_step(step)
        envelope = ControllerCommandEnvelope.move(
            vx=clamped["vx"],
            vy=clamped["vy"],
            vyaw=clamped["vyaw"],
            duration=clamped["duration"],
        )
        return adapter.execute_controller_command(envelope)
    if step_type == "wait":
        duration = float(step.get("duration", 0.0))
        time.sleep(duration)
        return {"waited_s": duration}

    raise ValueError(f"Unknown step type: {step_type}")
