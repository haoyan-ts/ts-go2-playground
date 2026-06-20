"""Action library — loads and queries fixed-safe-action YAML definitions."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ActionLibrary:
    """Loads a Go2 action YAML file and provides read-only queries.

    Actions are fixed, pre-defined, safe sequences. No new actions can be
    created at runtime — only the listed actions are available.
    """

    def __init__(self, yaml_path: Optional[str] = None):
        if yaml_path is None:
            yaml_path = str(
                Path(__file__).resolve().parent / "config" / "actions.go2.yaml"
            )
        self._yaml_path = Path(yaml_path)
        self._actions: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        with self._yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("actions", {})

    def list_actions(self) -> List[Dict[str, Any]]:
        """Return a list of available actions with metadata (no step data)."""
        return [
            {
                "name": name,
                "description": action.get("description", ""),
                "risk": action.get("risk", "unknown"),
                "requires_confirmation": action.get("requires_confirmation", True),
            }
            for name, action in self._actions.items()
        ]

    def get_action(self, name: str) -> Dict[str, Any]:
        """Return the full action definition including steps.

        Raises:
            KeyError: If the action name is not in the library.
        """
        if name not in self._actions:
            raise KeyError(f"Unknown action: {name}")
        return dict(self._actions[name])

    def action_names(self) -> List[str]:
        """Return list of action names."""
        return list(self._actions.keys())
