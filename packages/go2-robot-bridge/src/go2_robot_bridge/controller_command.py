"""Controller-level command contract for Go2 control targets."""

from dataclasses import dataclass, field
from typing import Any, Mapping


ALLOWED_POSTURES = frozenset(
    {
        "balance_stand",
        "stand_up",
        "stand_down",
        "recovery_stand",
    }
)


@dataclass(frozen=True)
class ControllerCommandEnvelope:
    """Canonical target-facing controller command built by Robot Bridge."""

    intent: str
    params: Mapping[str, Any]
    controller: str = "default"
    command_type: str = field(default="controller_command", init=False)

    @classmethod
    def move(
        cls,
        vx: float,
        vy: float,
        vyaw: float,
        duration: float,
        controller: str = "default",
    ) -> "ControllerCommandEnvelope":
        return cls(
            controller=controller,
            intent="move",
            params={
                "vx": vx,
                "vy": vy,
                "vyaw": vyaw,
                "duration": duration,
            },
        )

    @classmethod
    def posture(
        cls, name: str, controller: str = "default"
    ) -> "ControllerCommandEnvelope":
        if name not in ALLOWED_POSTURES:
            allowed = ", ".join(sorted(ALLOWED_POSTURES))
            raise ValueError(f"Unsupported posture '{name}'. Allowed: {allowed}")
        return cls(
            controller=controller,
            intent="posture",
            params={"name": name},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_type": self.command_type,
            "controller": self.controller,
            "intent": self.intent,
            "params": dict(self.params),
        }