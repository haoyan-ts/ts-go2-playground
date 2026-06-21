"""Adapters for Unitree Go2 control targets."""

import json
import logging
import os
import time
from typing import Any, Dict
from urllib import error, request
from urllib.parse import urljoin

from .controller_command import ControllerCommandEnvelope

logger = logging.getLogger(__name__)


class AdapterCommandError(RuntimeError):
    """Base error for adapter command failures."""


class UnsupportedCommandError(AdapterCommandError):
    """Raised when a control target does not support a command."""


class UnitreeGo2Adapter:
    """Adapter wrapping Unitree SDK2 SportClient calls.

    In dry mode, calls return structured dicts without touching real hardware.
    In real Go2 mode, calls import unitree_sdk2_python and use SportClient.
    """

    def __init__(self, dry_mode: bool = True, network_interface: str = "eth0"):
        self.dry_mode = dry_mode
        self.control_target = "dry" if dry_mode else "real_go2"
        self._network_interface = network_interface
        self._client = None

        if not dry_mode:
            self._init_real_client()

    def _init_real_client(self) -> None:
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            from unitree_sdk2py.go2.sport.sport_client import SportClient

            ChannelFactoryInitialize(0, self._network_interface)
            self._client = SportClient()
            self._client.SetTimeout(10.0)
            self._client.Init()
            logger.info("UnitreeGo2Adapter: real SDK client initialized")
        except Exception as e:
            logger.error("UnitreeGo2Adapter: failed to init real client: %s", e)
            raise

    def status(self) -> Dict[str, Any]:
        """Return robot status. Read-only, safe to call anytime."""
        return {
            "robot": "go2",
            "connected": self.dry_mode or self._client is not None,
            "mode": "sport",
            "safe_to_move": True,
            "dry_mode": self.dry_mode,
            "control_target": self.control_target,
        }

    def stop(self) -> Dict[str, Any]:
        """Stop the control target. Always safe."""
        if not self.dry_mode:
            self._client.StopMove()
        return self._result("StopMove")

    def execute_controller_command(
        self, envelope: ControllerCommandEnvelope
    ) -> Dict[str, Any]:
        """Execute a canonical Robot Bridge controller-level command."""
        if envelope.intent == "move":
            return self._execute_move(envelope)
        if envelope.intent == "posture":
            return self._execute_posture(envelope)
        raise UnsupportedCommandError(
            f"Unsupported controller intent '{envelope.intent}' for {self.control_target}"
        )

    def _execute_move(self, envelope: ControllerCommandEnvelope) -> Dict[str, Any]:
        params = envelope.params
        vx = float(params["vx"])
        vy = float(params["vy"])
        vyaw = float(params["vyaw"])
        duration = float(params["duration"])

        try:
            if not self.dry_mode:
                self._client.Move(vx, vy, vyaw)
            time.sleep(duration)
            return {
                "executed": "controller_command",
                "intent": "move",
                "controller": envelope.controller,
                "params": {
                    "vx": vx,
                    "vy": vy,
                    "vyaw": vyaw,
                    "duration": duration,
                },
                "dry_mode": self.dry_mode,
                "control_target": self.control_target,
            }
        finally:
            self.stop()

    def _execute_posture(self, envelope: ControllerCommandEnvelope) -> Dict[str, Any]:
        name = str(envelope.params["name"])
        sdk_method = {
            "balance_stand": "BalanceStand",
            "stand_up": "StandUp",
            "stand_down": "StandDown",
            "recovery_stand": "RecoveryStand",
        }.get(name)
        if sdk_method is None:
            raise UnsupportedCommandError(
                f"Unsupported posture '{name}' for {self.control_target}"
            )

        if not self.dry_mode:
            getattr(self._client, sdk_method)()

        return {
            "executed": "controller_command",
            "intent": "posture",
            "controller": envelope.controller,
            "params": {"name": name},
            "sdk_call": sdk_method,
            "dry_mode": self.dry_mode,
            "control_target": self.control_target,
        }

    def _result(self, executed: str) -> Dict[str, Any]:
        return {
            "executed": executed,
            "dry_mode": self.dry_mode,
            "control_target": self.control_target,
        }


class HttpControllerTargetAdapter:
    """HTTP adapter for simulator targets that consume controller envelopes."""

    dry_mode = False

    def __init__(
        self,
        base_url: str,
        control_target: str,
        display_name: str,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.control_target = control_target
        self.display_name = display_name
        self.timeout = timeout

    def status(self) -> Dict[str, Any]:
        return self._request_json("GET", "status")

    def stop(self) -> Dict[str, Any]:
        return self._request_json("POST", "stop")

    def execute_controller_command(
        self, envelope: ControllerCommandEnvelope
    ) -> Dict[str, Any]:
        return self._request_json(
            "POST",
            "controller-command",
            envelope.to_dict(),
        )

    def _request_json(
        self, method: str, path: str, payload: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(
            urljoin(self.base_url, path),
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            message = _read_error_body(exc)
            if exc.code in {400, 404, 405, 501}:
                raise UnsupportedCommandError(
                    f"{self.display_name} request '{path}' is unsupported: {message}"
                ) from exc
            raise AdapterCommandError(
                f"{self.display_name} request '{path}' failed with HTTP {exc.code}: {message}"
            ) from exc
        except error.URLError as exc:
            raise AdapterCommandError(
                f"{self.display_name} control server is unreachable: {exc.reason}"
            ) from exc

        if not response_body:
            result: Dict[str, Any] = {}
        else:
            parsed = json.loads(response_body)
            if not isinstance(parsed, dict):
                raise AdapterCommandError(
                    f"{self.display_name} request '{path}' returned non-object JSON"
                )
            result = parsed

        result.setdefault("control_target", self.control_target)
        result.setdefault("dry_mode", self.dry_mode)
        return result


class IsaacSimGo2Adapter(HttpControllerTargetAdapter):
    """HTTP adapter for a Go2 model running inside Isaac Sim."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        super().__init__(
            base_url=base_url,
            control_target="isaac_sim",
            display_name="Isaac Sim",
            timeout=timeout,
        )


class MuJoCoGo2Adapter(HttpControllerTargetAdapter):
    """HTTP adapter for a Go2 model running inside MuJoCo."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        super().__init__(
            base_url=base_url,
            control_target="mujoco",
            display_name="MuJoCo",
            timeout=timeout,
        )


def create_go2_adapter_from_env(
    environ: Dict[str, str] | None = None,
) -> UnitreeGo2Adapter | IsaacSimGo2Adapter | MuJoCoGo2Adapter:
    """Create the configured Go2 adapter from environment variables."""
    env = environ if environ is not None else os.environ
    target = env.get("BRIDGE_TARGET", "dry").strip().lower()

    if target == "dry":
        return UnitreeGo2Adapter(dry_mode=True)
    if target in {"real", "real_go2"}:
        network_interface = env.get("GO2_NETWORK_INTERFACE", "eth0")
        return UnitreeGo2Adapter(dry_mode=False, network_interface=network_interface)
    if target == "isaac_sim":
        base_url = env.get("ISAAC_SIM_URL")
        if not base_url:
            raise ValueError("ISAAC_SIM_URL is required when BRIDGE_TARGET=isaac_sim")
        return IsaacSimGo2Adapter(base_url=base_url)
    if target == "mujoco":
        base_url = env.get("MUJOCO_URL")
        if not base_url:
            raise ValueError("MUJOCO_URL is required when BRIDGE_TARGET=mujoco")
        return MuJoCoGo2Adapter(base_url=base_url)

    raise ValueError(
        "Invalid BRIDGE_TARGET "
        f"'{target}'. Expected one of: dry, real_go2, isaac_sim, mujoco."
    )


def _read_error_body(exc: error.HTTPError) -> str:
    raw = exc.read().decode("utf-8", errors="replace")
    if not raw:
        return str(exc.reason)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(parsed, dict):
        return str(parsed.get("detail") or parsed.get("error") or parsed)
    return str(parsed)