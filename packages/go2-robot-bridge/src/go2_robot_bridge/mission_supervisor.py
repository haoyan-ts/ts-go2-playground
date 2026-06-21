"""Mission supervisor — executes multi-step missions with observation and safety.

Missions chain library actions together with observation pauses and a final
report.  The supervisor enforces max_duration, honours E‑stop interrupts,
and delegates action‑step validation to the SafetySupervisor.
"""

import time
from typing import Any, Dict, List, Optional

from .action_library import ActionLibrary
from .safety_supervisor import SafetySupervisor
from .action_executor import execute_bridge_step
from .logger import Logger


class MissionSupervisor:
    """Executes missions, threading through safety checks and observation.

    A mission is a sequence of steps where each step is one of:
        - ``action``  — run a named action from the ActionLibrary
        - ``observe`` — pause and collect a perception snapshot
        - ``report``  — produce a final structured report (always last step)
    """

    def __init__(
        self,
        action_library: ActionLibrary,
        safety_supervisor: SafetySupervisor,
        adapter: Any,
        logger: Logger,
    ):
        self._action_library = action_library
        self._safety_supervisor = safety_supervisor
        self._adapter = adapter
        self._logger = logger

        # Internal mutable state
        self._estop: bool = False
        self._mission_start: float = 0.0

    # ------------------------------------------------------------------
    # Read-only state helpers
    # ------------------------------------------------------------------

    @property
    def world_state(self) -> Dict[str, Any]:
        """Snapshot of the supervisor's internal state (estop, etc.)."""
        return {
            "robot": "go2",
            "estop_triggered": self._estop,
        }

    def perception_summary(self) -> Dict[str, Any]:
        """Collect a perception snapshot (robot status + world state)."""
        status = self._adapter.status()
        return {
            "robot_status": status,
            "world_state": self.world_state,
        }

    # ------------------------------------------------------------------
    # E‑stop
    # ------------------------------------------------------------------

    def trigger_estop(self) -> None:
        """Immediately stop the robot and set the emergency-stop flag."""
        self._estop = True
        self._adapter.stop()
        self._logger.log_event("mission_estop_triggered", {})

    def reset_estop(self) -> None:
        """Clear the emergency-stop flag (e.g. before a new mission)."""
        self._estop = False

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(
        self, duration: float, waypoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pause for *duration* seconds and collect a perception summary.

        Args:
            duration: Seconds to wait.
            waypoint: Optional waypoint label for context.

        Returns:
            A dict with the observation summary.
        """
        time.sleep(duration)
        summary = self.perception_summary()
        if waypoint:
            summary["waypoint"] = waypoint
        self._logger.log_event("mission_observe", summary)
        return summary

    # ------------------------------------------------------------------
    # Mission validation
    # ------------------------------------------------------------------

    def validate_mission(
        self,
        mission_name: str,
        mission: Dict[str, Any],
        confirmed: bool,
    ) -> None:
        """Check that a mission is safe to execute.

        Raises:
            PermissionError: If confirmation is required but not given.
        """
        requires_confirmation = mission.get("requires_confirmation", True)
        if requires_confirmation and not confirmed:
            raise PermissionError(
                f"Mission '{mission_name}' requires human confirmation. "
                f"Set confirmed=True to proceed."
            )

    # ------------------------------------------------------------------
    # Mission execution
    # ------------------------------------------------------------------

    def execute_mission(
        self,
        mission_name: str,
        mission: Dict[str, Any],
        confirmed: bool,
    ) -> Dict[str, Any]:
        """Execute a single mission from start to finish.

        Args:
            mission_name: Human-readable mission identifier (for logging).
            mission: Full mission dict (from MissionLibrary).
            confirmed: Whether the user has confirmed execution.

        Returns:
            Dict with ``name``, ``status``, ``duration_s``, ``max_duration_s``,
            ``steps`` (list of per-step results), and ``final_report``.

        Raises:
            PermissionError: If confirmation is required but not given.
            TimeoutError: If the mission exceeds its max_duration.
        """
        # 1. Validate
        self.validate_mission(mission_name, mission, confirmed)

        max_duration = float(mission.get("max_duration", 30.0))

        # 2. Check for pre-existing E-stop before resetting
        was_estopped = self._estop
        self.reset_estop()

        if was_estopped:
            self._logger.log_event(
                "mission_interrupted",
                {"mission": mission_name, "reason": "pre_existing_estop"},
            )
            return {
                "name": mission_name,
                "status": "estop_interrupted",
                "duration_s": 0.0,
                "max_duration_s": max_duration,
                "steps": [],
                "final_report": self._build_report(
                    mission_name, [], "estop_interrupted"
                ),
            }

        self._logger.log_event("mission_start", {"mission": mission_name})
        self._mission_start = time.time()

        step_results: List[Dict[str, Any]] = []
        final_report: Optional[Dict[str, Any]] = None
        status = "completed"

        try:
            for step in mission.get("steps", []):
                # Check E‑stop before every step
                if self._estop:
                    status = "estop_interrupted"
                    self._logger.log_event(
                        "mission_interrupted",
                        {"mission": mission_name, "reason": "estop"},
                    )
                    break

                # Check max_duration before every step
                elapsed = time.time() - self._mission_start
                if elapsed >= max_duration:
                    status = "timeout"
                    self._logger.log_event(
                        "mission_timeout",
                        {
                            "mission": mission_name,
                            "elapsed_s": round(elapsed, 3),
                            "max_duration_s": max_duration,
                        },
                    )
                    break

                step_type = step.get("type", "unknown")

                if step_type == "action":
                    action_name = step.get("name", "")
                    result = self._execute_action_step(action_name)
                    step_results.append(
                        {"type": "action", "name": action_name, "result": result}
                    )

                elif step_type == "observe":
                    duration = float(step.get("duration", 1.0))
                    # Cap observation to remaining max_duration
                    remaining = max_duration - (time.time() - self._mission_start)
                    if duration > remaining:
                        duration = max(0.0, remaining)
                    waypoint = step.get("waypoint")
                    summary = self.observe(duration, waypoint=waypoint)
                    step_results.append(
                        {
                            "type": "observe",
                            "duration": duration,
                            "waypoint": waypoint,
                            "summary": summary,
                        }
                    )

                elif step_type == "report":
                    final_report = self._build_report(
                        mission_name, step_results, status
                    )
                    step_results.append({"type": "report", "report": final_report})
                    break  # report is always the last step

                else:
                    self._logger.log_event(
                        "mission_unknown_step",
                        {"mission": mission_name, "step_type": step_type},
                    )
                    step_results.append(
                        {"type": "unknown", "step_type": step_type, "result": "skipped"}
                    )

            # If we never hit a report step, build one now
            if final_report is None:
                final_report = self._build_report(mission_name, step_results, status)

        except Exception as exc:
            status = "error"
            self._adapter.stop()
            self._logger.log_event(
                "mission_error",
                {"mission": mission_name, "error": str(exc)},
            )
            final_report = self._build_report(mission_name, step_results, status)
            raise

        finally:
            total_elapsed = round(time.time() - self._mission_start, 3)
            self._logger.log_event(
                "mission_complete",
                {
                    "mission": mission_name,
                    "status": status,
                    "duration_s": total_elapsed,
                },
            )

        return {
            "name": mission_name,
            "status": status,
            "duration_s": round(time.time() - self._mission_start, 3),
            "max_duration_s": max_duration,
            "steps": step_results,
            "final_report": final_report,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_action_step(self, action_name: str) -> Dict[str, Any]:
        """Look up an action, validate it, and execute its steps.

        This is the mission-level equivalent of running a single action
        through the bridge — it uses the same ActionLibrary and adapter
        but does not go through HTTP routes.
        """
        action = self._action_library.get_action(action_name)

        # Safety validation for each constituent action
        # NOTE: we validate with confirmed=True because the mission-level
        # confirmation already happened.
        self._safety_supervisor.validate_action(action_name, action, confirmed=True)

        self._logger.log_event("mission_action_start", {"action": action_name})
        action_start = time.time()
        action_results: List[Dict[str, Any]] = []

        for sub_step in action.get("steps", []):
            sub_type = sub_step.get("type")
            result = self._dispatch_step(sub_type, sub_step)
            action_results.append({"type": sub_type, "result": result})
            self._logger.log_step(sub_type, result)

        action_elapsed = round(time.time() - action_start, 3)
        self._logger.log_event(
            "mission_action_complete",
            {"action": action_name, "duration_s": action_elapsed},
        )

        return {
            "action": action_name,
            "duration_s": action_elapsed,
            "steps": action_results,
        }

    def _dispatch_step(self, step_type: str, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action sub-step through the canonical bridge executor."""
        return execute_bridge_step(step, self._adapter, self._safety_supervisor)

    def _build_report(
        self,
        mission_name: str,
        step_results: List[Dict[str, Any]],
        status: str,
    ) -> Dict[str, Any]:
        """Build the final mission report."""
        elapsed = round(time.time() - self._mission_start, 3)
        action_steps = [s for s in step_results if s.get("type") == "action"]
        observe_steps = [s for s in step_results if s.get("type") == "observe"]

        return {
            "mission": mission_name,
            "status": status,
            "total_duration_s": elapsed,
            "action_count": len(action_steps),
            "observation_count": len(observe_steps),
            "estop_triggered": self._estop,
            "robot_status": self._adapter.status(),
        }
