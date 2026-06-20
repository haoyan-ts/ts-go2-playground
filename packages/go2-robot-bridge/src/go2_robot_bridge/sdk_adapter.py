"""SDK adapter for Unitree Go2 — supports dry-mode (no real hardware) and real mode."""

import time
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class UnitreeGo2Adapter:
    """Adapter wrapping Unitree SDK2 SportClient calls.

    In dry_mode, all calls return structured dicts without touching real hardware.
    In real mode, imports unitree_sdk2_python and calls the SportClient directly.
    """

    def __init__(self, dry_mode: bool = True, network_interface: str = "eth0"):
        self.dry_mode = dry_mode
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
            }

        # Real mode: return basic status info
        return {
            "robot": "go2",
            "connected": self._client is not None,
            "mode": "sport",
            "safe_to_move": True,
            "dry_mode": False,
        }

    def stop(self) -> Dict[str, Any]:
        """Send StopMove to Go2. Always safe."""
        if self.dry_mode:
            return {"executed": "StopMove", "dry_mode": True}

        self._client.StopMove()
        return {"executed": "StopMove", "dry_mode": False}

    def balance_stand(self) -> Dict[str, Any]:
        """Put Go2 into balance stand mode."""
        if self.dry_mode:
            return {"executed": "BalanceStand", "dry_mode": True}

        self._client.BalanceStand()
        return {"executed": "BalanceStand", "dry_mode": False}

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
            }
        finally:
            self.stop()

    def stand_up(self) -> Dict[str, Any]:
        """Make Go2 stand up."""
        if self.dry_mode:
            return {"executed": "StandUp", "dry_mode": True}

        self._client.StandUp()
        return {"executed": "StandUp", "dry_mode": False}

    def stand_down(self) -> Dict[str, Any]:
        """Make Go2 stand down."""
        if self.dry_mode:
            return {"executed": "StandDown", "dry_mode": True}

        self._client.StandDown()
        return {"executed": "StandDown", "dry_mode": False}

    def hello(self) -> Dict[str, Any]:
        """Make Go2 perform hello gesture."""
        if self.dry_mode:
            return {"executed": "Hello", "dry_mode": True}

        self._client.Hello()
        return {"executed": "Hello", "dry_mode": False}

    def dance1(self) -> Dict[str, Any]:
        """Make Go2 perform dance1."""
        if self.dry_mode:
            return {"executed": "Dance1", "dry_mode": True}

        self._client.Dance1()
        return {"executed": "Dance1", "dry_mode": False}

    def recovery_stand(self) -> Dict[str, Any]:
        """Make Go2 perform recovery stand."""
        if self.dry_mode:
            return {"executed": "RecoveryStand", "dry_mode": True}

        self._client.RecoveryStand()
        return {"executed": "RecoveryStand", "dry_mode": False}
