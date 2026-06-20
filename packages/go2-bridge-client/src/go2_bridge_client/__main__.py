"""Go2 Bridge Client — sandbox-side CLI for talking to the Robot Bridge server.

Usage:
    python -m go2_bridge_client <command> [args]

Commands:
    health                  Check bridge server health
    status                  Get robot status
    stop                    Send emergency stop to robot
    list                    List available actions
    dry-run <action>        Show action steps without executing
    run <action>            Execute an action (with confirmation check)
    missions                List available missions
    mission-dry-run <name>  Show mission steps without executing
    mission-run <name>      Execute a mission (with confirmation check)
    logs                    Show recent bridge log lines

Environment:
    BRIDGE_URL           Bridge server base URL (default: http://127.0.0.1:50001)
"""

import os
import sys
import json

import requests

BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:50001")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _get(path: str):
    r = requests.get(f"{BRIDGE_URL}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


def _post(path: str, body=None):
    r = requests.post(f"{BRIDGE_URL}{path}", json=body or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def _print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def cmd_health():
    """GET /health"""
    _print_json(_get("/health"))


def cmd_status():
    """GET /robot/status"""
    _print_json(_get("/robot/status"))


def cmd_stop():
    """POST /robot/stop"""
    _print_json(_post("/robot/stop"))


def cmd_list():
    """GET /actions"""
    data = _get("/actions")
    actions = data.get("actions", [])
    if not actions:
        print("No actions available.")
        return
    for a in actions:
        conf = "(confirm)" if a.get("requires_confirmation") else "(no confirm)"
        print(f"  {a['name']:<30s} [{a['risk']:<12s}] {conf}")
        print(f"    {a['description']}")


def cmd_dry_run(action_name: str):
    """POST /actions/{name}/dry-run"""
    data = _post(f"/actions/{action_name}/dry-run")
    print(f"Action: {data['name']}")
    print(f"  Description:  {data['description']}")
    print(f"  Risk:         {data['risk']}")
    print(f"  Confirmation: {data['requires_confirmation']}")
    print(f"  Steps:")
    for i, step in enumerate(data.get("steps", []), 1):
        print(f"    {i}. {step}")


def cmd_run(action_name: str, confirm: bool = False):
    """POST /actions/{name}/execute

    If --confirm not passed, first show a dry-run and ask the user.
    """
    if not confirm:
        # Show dry-run first
        dry = _post(f"/actions/{action_name}/dry-run")
        print(f"Action: {dry['name']}")
        print(f"  Description:  {dry['description']}")
        print(f"  Risk:         {dry['risk']}")
        print(f"  Confirmation: {dry['requires_confirmation']}")
        print("  Steps:")
        for i, step in enumerate(dry.get("steps", []), 1):
            print(f"    {i}. {step}")
        print()
        ans = input("Execute this action? Type 'yes' to confirm: ")
        if ans.strip().lower() != "yes":
            print("Aborted.")
            return
        confirm = True

    data = _post(
        f"/actions/{action_name}/execute",
        body={"confirmed": confirm},
    )
    _print_json(data)


def cmd_missions():
    """GET /missions"""
    data = _get("/missions")
    missions = data.get("missions", [])
    if not missions:
        print("No missions available.")
        return
    for m in missions:
        conf = "(confirm)" if m.get("requires_confirmation") else "(no confirm)"
        print(
            f"  {m['name']:<30s} [{m['risk']:<12s}] {conf}  max {m['max_duration_s']}s"
        )
        print(f"    {m['description']}")


def cmd_mission_dry_run(mission_name: str):
    """POST /missions/{name}/dry-run"""
    data = _post(f"/missions/{mission_name}/dry-run")
    print(f"Mission: {data['name']}")
    print(f"  Description:    {data['description']}")
    print(f"  Risk:           {data['risk']}")
    print(f"  Confirmation:   {data['requires_confirmation']}")
    print(f"  Max Duration:   {data['max_duration_s']}s")
    print(f"  Steps:")
    for i, step in enumerate(data.get("steps", []), 1):
        print(f"    {i}. {step}")


def cmd_mission_run(mission_name: str, confirm: bool = False):
    """POST /missions/{name}/execute

    If --confirm not passed, first show a dry-run and ask the user.
    """
    if not confirm:
        # Show dry-run first
        dry = _post(f"/missions/{mission_name}/dry-run")
        print(f"Mission: {dry['name']}")
        print(f"  Description:    {dry['description']}")
        print(f"  Risk:           {dry['risk']}")
        print(f"  Confirmation:   {dry['requires_confirmation']}")
        print(f"  Max Duration:   {dry['max_duration_s']}s")
        print("  Steps:")
        for i, step in enumerate(dry.get("steps", []), 1):
            print(f"    {i}. {step}")
        print()
        ans = input("Execute this mission? Type 'yes' to confirm: ")
        if ans.strip().lower() != "yes":
            print("Aborted.")
            return
        confirm = True

    data = _post(
        f"/missions/{mission_name}/execute",
        body={"confirmed": confirm},
    )
    _print_json(data)


def cmd_logs():
    """GET /logs/recent"""
    data = _get("/logs/recent")
    for line in data.get("lines", []):
        print(line)


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

USAGE = """Usage:
  python -m go2_bridge_client <command> [args]

Commands:
  health                     Check bridge server health
  status                     Get robot status
  stop                       Send emergency stop
  list                       List available actions
  dry-run <action>           Show action steps without executing
  run <action> [--confirm]   Execute action (--confirm skips interactive prompt)
  missions                   List available missions
  mission-dry-run <name>     Show mission steps without executing
  mission-run <name> [--confirm]  Execute mission (--confirm skips interactive prompt)
  logs                       Show recent bridge log lines"""


def main():
    args = sys.argv[1:]

    if not args:
        print(USAGE)
        sys.exit(1)

    cmd = args[0]

    if cmd == "health":
        cmd_health()
    elif cmd == "status":
        cmd_status()
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "list":
        cmd_list()
    elif cmd == "dry-run":
        if len(args) < 2:
            print("Usage: dry-run <action-name>")
            sys.exit(1)
        cmd_dry_run(args[1])
    elif cmd == "run":
        if len(args) < 2:
            print("Usage: run <action-name> [--confirm]")
            sys.exit(1)
        confirm = "--confirm" in args
        cmd_run(args[1], confirm)
    elif cmd == "missions":
        cmd_missions()
    elif cmd == "mission-dry-run":
        if len(args) < 2:
            print("Usage: mission-dry-run <mission-name>")
            sys.exit(1)
        cmd_mission_dry_run(args[1])
    elif cmd == "mission-run":
        if len(args) < 2:
            print("Usage: mission-run <mission-name> [--confirm]")
            sys.exit(1)
        confirm = "--confirm" in args
        cmd_mission_run(args[1], confirm)
    elif cmd == "logs":
        cmd_logs()
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
