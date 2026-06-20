"""Adapters for Unitree Go2 control targets."""

import json
import os
import time
import logging
from typing import Any, Dict
from urllib import error, request
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class AdapterCommandError(RuntimeError):
    """Base error for adapter command failures."""


class UnsupportedCommandError(AdapterCommandError):
    """Raised when a control target does not support a command."""


class UnitreeGo2Adapter:
    """Adapter wrapping Unitree SDK2 SportClient calls.

    In dry_mode, all calls return structured dicts without touching real hardware.
    In real mode, imports unitree_sdk2_python and calls the SportClient directly.
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
        if self.dry_mode:
            return {
                "robot": "go2",
                "connected": True,
                "mode": "sport",
                "safe_to_move": True,
                "dry_mode": True,
                "control_target": self.control_target,
            }

        return {
            "robot": "go2",
            "connected": self._client is not None,
            "mode": "sport",
            "safe_to_move": True,
            "dry_mode": False,
            "control_target": self.control_target,
        }

    def stop(self) -> Dict[str, Any]:
        """Send StopMove to Go2. Always safe."""
        if self.dry_mode:
            return self._result("StopMove")

        self._client.StopMove()
        return self._result("StopMove")

    def balance_stand(self) -> Dict[str, Any]:
        """Put Go2 into balance stand mode."""
        if self.dry_mode:
            return self._result("BalanceStand")

        self._client.BalanceStand()
        return self._result("BalanceStand")

    def move(
        self, vx: float, vy: float, vyaw: float, duration: float
    ) -> Dict[str, Any]:
        """Move Go2 with given velocities for a duration. Always stops after moving.

        Args:
            vx: Forward velocity (m/s).
            vy: Lateral velocity (m/s).
            vyaw: Yaw angular velocity (rad/s).
            duration: Movement duration in seconds.
        """
        try:
            if self.dry_mode:
                time.sleep(duration)
                return {
                    "executed": "Move",
                    "vx": vx,
                    "vy": vy,
                    "vyaw": vyaw,
                    "duration": duration,
                    "dry_mode": True,
                    "control_target": self.control_target,
                }

            self._client.Move(vx, vy, vyaw)
            time.sleep(duration)
            return {
                "executed": "Move",
                "vx": vx,
                "vy": vy,
                "vyaw": vyaw,
                "duration": duration,
                "dry_mode": False,
                "control_target": self.control_target,
            }
        finally:
            self.stop()

    def stand_up(self) -> Dict[str, Any]:
        """Make Go2 stand up."""
        if self.dry_mode:
            return self._result("StandUp")

        self._client.StandUp()
        return self._result("StandUp")

    def stand_down(self) -> Dict[str, Any]:
        """Make Go2 stand down."""
        if self.dry_mode:
            return self._result("StandDown")

        self._client.StandDown()
        return self._result("StandDown")

    def hello(self) -> Dict[str, Any]:
        """Make Go2 perform hello gesture."""
        if self.dry_mode:
            return self._result("Hello")

        self._client.Hello()
        return self._result("Hello")

    def dance1(self) -> Dict[str, Any]:
        """Make Go2 perform dance1."""
        if self.dry_mode:
            return self._result("Dance1")

        self._client.Dance1()
        return self._result("Dance1")

    def recovery_stand(self) -> Dict[str, Any]:
        """Make Go2 perform recovery stand."""
        if self.dry_mode:
            return self._result("RecoveryStand")

        self._client.RecoveryStand()
        return self._result("RecoveryStand")

    def _result(self, executed: str) -> Dict[str, Any]:
        return {
            "executed": executed,
            "dry_mode": self.dry_mode,
            "control_target": self.control_target,
        }


class IsaacSimGo2Adapter:
    """HTTP adapter for a Go2 model running inside Isaac Sim."""

    control_target = "isaac_sim"
    dry_mode = False

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def status(self) -> Dict[str, Any]:
        """Return Isaac Sim Go2 status."""
        return self._request_json("GET", "status")

    def stop(self) -> Dict[str, Any]:
        """Send stop to Isaac Sim Go2."""
        return self._request_json("POST", "stop")

    def balance_stand(self) -> Dict[str, Any]:
        """Put Isaac Sim Go2 into balance stand mode."""
        return self._request_json("POST", "balance_stand")

    def move(
        self, vx: float, vy: float, vyaw: float, duration: float
    ) -> Dict[str, Any]:
        """Move Isaac Sim Go2 with given velocities for a duration."""
        return self._request_json(
            "POST",
            "move",
            {"vx": vx, "vy": vy, "vyaw": vyaw, "duration": duration},
        )

    def stand_up(self) -> Dict[str, Any]:
        """Make Isaac Sim Go2 stand up."""
        return self._request_json("POST", "stand_up")

    def stand_down(self) -> Dict[str, Any]:
        """Make Isaac Sim Go2 stand down."""
        return self._request_json("POST", "stand_down")

    def hello(self) -> Dict[str, Any]:
        """Make Isaac Sim Go2 perform hello gesture."""
        return self._request_json("POST", "hello")

    def dance1(self) -> Dict[str, Any]:
        """Make Isaac Sim Go2 perform dance1."""
        return self._request_json("POST", "dance1")

    def recovery_stand(self) -> Dict[str, Any]:
        """Make Isaac Sim Go2 perform recovery stand."""
        return self._request_json("POST", "recovery_stand")

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
                    f"Isaac Sim command '{path}' is unsupported: {message}"
                ) from exc
            raise AdapterCommandError(
                f"Isaac Sim command '{path}' failed with HTTP {exc.code}: {message}"
            ) from exc
        except error.URLError as exc:
            raise AdapterCommandError(
                f"Isaac Sim control server is unreachable: {exc.reason}"
            ) from exc

        if not response_body:
            result: Dict[str, Any] = {}
        else:
            parsed = json.loads(response_body)
            if not isinstance(parsed, dict):
                raise AdapterCommandError(
                    f"Isaac Sim command '{path}' returned non-object JSON"
                )
            result = parsed

        result.setdefault("control_target", self.control_target)
        result.setdefault("dry_mode", self.dry_mode)
        return result


def create_go2_adapter_from_env(
    environ: Dict[str, str] | None = None,
) -> UnitreeGo2Adapter | IsaacSimGo2Adapter:
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
            raise ValueError(
                "ISAAC_SIM_URL is required when BRIDGE_TARGET=isaac_sim"
            )
        return IsaacSimGo2Adapter(base_url=base_url)

    raise ValueError(
        "Invalid BRIDGE_TARGET "
        f"'{target}'. Expected one of: dry, real_go2, isaac_sim."
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
