"""Mission library — loads and queries fixed-safe-mission YAML definitions.

Missions chain actions together with observation and reporting steps.
Each mission has a max duration and requires confirmation when it contains motion.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class MissionLibrary:
    """Loads a Go2 mission YAML file and provides read-only queries.

    Missions are pre-defined, safe sequences of actions + observations + reports.
    No new missions can be created at runtime.
    """

    def __init__(self, yaml_path: Optional[str] = None):
        if yaml_path is None:
            yaml_path = str(
                Path(__file__).resolve().parent / "config" / "missions.go2.yaml"
            )
        self._yaml_path = Path(yaml_path)
        self._missions: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        with self._yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("missions", {})

    def list_missions(self) -> List[Dict[str, Any]]:
        """Return a list of available missions with metadata (no step data)."""
        return [
            {
                "name": name,
                "description": mission.get("description", ""),
                "risk": mission.get("risk", "unknown"),
                "requires_confirmation": mission.get("requires_confirmation", True),
                "max_duration_s": mission.get("max_duration", 30.0),
                "step_count": len(mission.get("steps", [])),
            }
            for name, mission in self._missions.items()
        ]

    def get_mission(self, name: str) -> Dict[str, Any]:
        """Return the full mission definition including steps.

        Raises:
            KeyError: If the mission name is not in the library.
        """
        if name not in self._missions:
            raise KeyError(f"Unknown mission: {name}")
        return dict(self._missions[name])

    def mission_names(self) -> List[str]:
        """Return list of mission names."""
        return list(self._missions.keys())
