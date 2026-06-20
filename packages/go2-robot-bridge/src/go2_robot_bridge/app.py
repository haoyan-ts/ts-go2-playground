"""FastAPI application for Robot Bridge — wires action library, safety supervisor,
SDK adapter, and logger into a REST API for sandbox-side clients.

FastAPI and Pydantic are imported lazily so that the core bridge modules
(action_library, safety_supervisor, sdk_adapter, logger) remain importable
without installing the optional 'server' dependency group.
"""

import time
from typing import Any, Dict


def _get_fastapi():
    """Lazy import of FastAPI + Pydantic (optional 'server' deps)."""
    global FastAPI, HTTPException, BaseModel  # type: ignore[name-defined]
    from fastapi import FastAPI as _FastAPI, HTTPException as _HTTPException
    from pydantic import BaseModel as _BaseModel

    FastAPI, HTTPException, BaseModel = _FastAPI, _HTTPException, _BaseModel


# ---------------------------------------------------------------------------
# Request / response models (defined after lazy import)
# ---------------------------------------------------------------------------


class ExecuteRequest:
    """Will be replaced by Pydantic model at app creation time."""

    confirmed: bool = False


class CommandRequest:
    """Will be replaced by Pydantic model at app creation time."""

    command: str = ""
    params: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Singletons (lazy init via create_app)
# ---------------------------------------------------------------------------

_action_library = None
_safety_supervisor = None
_adapter = None
_logger = None
_mission_library = None
_mission_supervisor = None


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    action_library: Any = None,
    safety_supervisor: Any = None,
    adapter: Any = None,
    logger: Any = None,
):
    """Build and wire the FastAPI app with the given (or default) modules."""
    global _action_library, _safety_supervisor, _adapter, _logger
    global _mission_library, _mission_supervisor
    global ExecuteRequest, CommandRequest

    # Lazy-import FastAPI + Pydantic (optional 'server' deps)
    _get_fastapi()

    # Redefine request models as proper Pydantic models
    class ExecuteRequest(BaseModel):  # type: ignore[name-defined]
        confirmed: bool = False

    class CommandRequest(BaseModel):  # type: ignore[name-defined]
        command: str
        params: Dict[str, Any] = {}

    # Resolve defaults
    from .action_library import ActionLibrary
    from .safety_supervisor import SafetySupervisor
    from .sdk_adapter import (
        AdapterCommandError,
        UnsupportedCommandError,
        create_go2_adapter_from_env,
    )
    from .logger import Logger
    from .mission_library import MissionLibrary
    from .mission_supervisor import MissionSupervisor

    _action_library = action_library or ActionLibrary()
    _safety_supervisor = safety_supervisor or SafetySupervisor()
    _adapter = adapter or create_go2_adapter_from_env()
    _logger = logger or Logger()
    _mission_library = MissionLibrary()
    _mission_supervisor = MissionSupervisor(
        action_library=_action_library,
        safety_supervisor=_safety_supervisor,
        adapter=_adapter,
        logger=_logger,
    )

    app = FastAPI(
        title="Go2 Robot Bridge",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "dry_mode": _adapter.dry_mode,
            "control_target": _adapter.control_target,
        }

    # -----------------------------------------------------------------------
    # Phase 1 routes — robot direct
    # -----------------------------------------------------------------------

    @app.get("/robot/status")
    async def robot_status():
        result = _adapter.status()
        _logger.log_event("status_queried", result)
        return result

    @app.post("/robot/stop")
    async def robot_stop():
        result = _adapter.stop()
        _logger.log_stop()
        return result

    @app.post("/robot/command")
    async def robot_command(req: CommandRequest):
        """Phase-1 style single-command dispatch.

        Supported commands: status, stop, balance_stand, stand_up,
        stand_down, hello, dance1, recovery_stand.
        """
        valid = {
            "status",
            "stop",
            "balance_stand",
            "stand_up",
            "stand_down",
            "hello",
            "dance1",
            "recovery_stand",
        }
        cmd = req.command
        if cmd not in valid:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command '{cmd}'. Allowed: {sorted(valid)}",
            )

        method = getattr(_adapter, cmd)
        try:
            result = method(**req.params)
        except UnsupportedCommandError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except AdapterCommandError as e:
            raise HTTPException(status_code=502, detail=str(e))
        _logger.log_event("command_executed", {"command": cmd, "result": result})
        return result

    # -----------------------------------------------------------------------
    # Phase 2 routes — action library
    # -----------------------------------------------------------------------

    @app.get("/actions")
    async def list_actions():
        actions = _action_library.list_actions()
        _logger.log_event("actions_listed", {"count": len(actions)})
        return {"actions": actions}

    @app.post("/actions/{name}/dry-run")
    async def action_dry_run(name: str):
        try:
            action = _action_library.get_action(name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown action: {name}")

        # Clamp any move-step velocities/durations for display
        steps = []
        for step in action.get("steps", []):
            if step.get("type") == "move":
                steps.append(_safety_supervisor.clamp_move_step(step))
            else:
                steps.append(step)

        return {
            "name": name,
            "description": action.get("description", ""),
            "risk": action.get("risk", "unknown"),
            "requires_confirmation": action.get("requires_confirmation", True),
            "steps": steps,
        }

    @app.post("/actions/{name}/execute")
    async def action_execute(name: str, req: ExecuteRequest):
        # 1. Lookup action
        try:
            action = _action_library.get_action(name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown action: {name}")

        # 2. Safety validate (confirmation, speed, duration, step count)
        try:
            _safety_supervisor.validate_action(name, action, req.confirmed)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # 3. Execute steps
        _logger.log_action_start(name)
        t0 = time.time()
        step_results = []

        try:
            for step in action.get("steps", []):
                step_type = step.get("type")
                result = _execute_step(step_type, step)
                step_results.append({"type": step_type, "result": result})
                _logger.log_step(step_type, result)
        except UnsupportedCommandError as e:
            _logger.log_action_error(name, str(e))
            _stop_after_error()
            raise HTTPException(status_code=501, detail=str(e))
        except AdapterCommandError as e:
            _logger.log_action_error(name, str(e))
            _stop_after_error()
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            _logger.log_action_error(name, str(e))
            _stop_after_error()
            raise HTTPException(
                status_code=500,
                detail=f"Action '{name}' failed at step '{step_type}': {e}",
            )

        elapsed = round(time.time() - t0, 3)
        _logger.log_action_complete(name, elapsed)

        return {
            "name": name,
            "status": "completed",
            "duration_s": elapsed,
            "steps": step_results,
        }

    # -----------------------------------------------------------------------
    # Phase 4 routes — mission library
    # -----------------------------------------------------------------------

    @app.get("/missions")
    async def list_missions():
        missions = _mission_library.list_missions()
        _logger.log_event("missions_listed", {"count": len(missions)})
        return {"missions": missions}

    @app.post("/missions/{name}/dry-run")
    async def mission_dry_run(name: str):
        try:
            mission = _mission_library.get_mission(name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown mission: {name}")

        # Return mission metadata + steps (no execution)
        steps = []
        for step in mission.get("steps", []):
            step_type = step.get("type")
            if step_type == "action":
                steps.append(
                    {
                        "type": "action",
                        "name": step.get("name"),
                    }
                )
            elif step_type == "observe":
                steps.append(
                    {
                        "type": "observe",
                        "duration": step.get("duration"),
                        "waypoint": step.get("waypoint"),
                    }
                )
            elif step_type == "report":
                steps.append({"type": "report"})
            else:
                steps.append({"type": step_type})

        return {
            "name": name,
            "description": mission.get("description", ""),
            "risk": mission.get("risk", "unknown"),
            "requires_confirmation": mission.get("requires_confirmation", True),
            "max_duration_s": mission.get("max_duration", 30.0),
            "steps": steps,
        }

    @app.post("/missions/{name}/execute")
    async def mission_execute(name: str, req: ExecuteRequest):
        # 1. Lookup mission
        try:
            mission = _mission_library.get_mission(name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown mission: {name}")

        # 2. Execute via mission supervisor
        try:
            result = _mission_supervisor.execute_mission(
                mission_name=name,
                mission=mission,
                confirmed=req.confirmed,
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except TimeoutError as e:
            raise HTTPException(status_code=408, detail=str(e))
        except UnsupportedCommandError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except AdapterCommandError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Mission '{name}' failed: {e}",
            )

        return result

    # -----------------------------------------------------------------------
    # Logs
    # -----------------------------------------------------------------------

    @app.get("/logs/recent")
    async def logs_recent(lines: int = 50):
        """Return the last N lines from the bridge log file."""
        log_file = _logger.log_path
        if not log_file.exists():
            return {"lines": []}

        with log_file.open("r", encoding="utf-8") as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:]
        return {"lines": [line.rstrip("\n") for line in recent]}

    return app


# ---------------------------------------------------------------------------
# Error handling helpers
# ---------------------------------------------------------------------------


def _stop_after_error() -> None:
    """Best-effort stop that preserves the original route error."""
    try:
        _adapter.stop()
    except Exception as stop_error:
        _logger.log_event("stop_after_error_failed", {"error": str(stop_error)})


# ---------------------------------------------------------------------------
# Step execution helper
# ---------------------------------------------------------------------------

def _execute_step(step_type: str, step: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a single action step to the SDK adapter."""
    if step_type == "status":
        return _adapter.status()
    elif step_type == "stop":
        return _adapter.stop()
    elif step_type == "balance_stand":
        return _adapter.balance_stand()
    elif step_type == "stand_up":
        return _adapter.stand_up()
    elif step_type == "stand_down":
        return _adapter.stand_down()
    elif step_type == "hello":
        return _adapter.hello()
    elif step_type == "dance1":
        return _adapter.dance1()
    elif step_type == "recovery_stand":
        return _adapter.recovery_stand()
    elif step_type == "move":
        clamped = _safety_supervisor.clamp_move_step(step)
        return _adapter.move(
            vx=clamped["vx"],
            vy=clamped["vy"],
            vyaw=clamped["vyaw"],
            duration=clamped["duration"],
        )
    elif step_type == "wait":
        duration = float(step.get("duration", 0.0))
        time.sleep(duration)
        return {"waited_s": duration}
    else:
        raise ValueError(f"Unknown step type: {step_type}")


# ---------------------------------------------------------------------------
# Default app instance (for uvicorn go2_robot_bridge.app:app)
# Lazy-created so the module can be imported without FastAPI installed.
# ---------------------------------------------------------------------------


def __getattr__(name: str):
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
