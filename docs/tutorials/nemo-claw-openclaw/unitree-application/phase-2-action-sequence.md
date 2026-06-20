# NemoClaw + OpenClaw + Unitree 応用編 Phase 2

## Safe Action Library and Sequence Execution

> **See also**: [Foundation Tutorial](../../unitree-go2-foundation/basics.md) — for building the
> Robot Bridge foundation packages used in this phase.

---

## 0. Phase 2の位置づけ

Phase 1では、NemoClaw sandbox内のOpenClawから、Robot Bridgeを経由してUnitree Go2のHigh-level APIを**1回だけ安全に呼び出す**ことを目標にした。

Phase 2では、そこから一段進めて、**短い動作シーケンスを安全に実行する**ことを目標にする。

Phase 1:

```text
OpenClaw
  ↓
unitree_bridge_client.py
  ↓ HTTP
Robot Bridge
  ↓
Unitree SDK2 High-level APIを1回呼ぶ
  ↓
Go2
```

Phase 2:

```text
OpenClaw
  ↓
自然言語から既存Actionを選ぶ
  ↓
dry-runで内容確認
  ↓
人間確認
  ↓
Robot BridgeがAction Library内の固定シーケンスを実行
  ↓
各step後にStopMove / status / log
  ↓
Go2
```

Phase 2の考え方は、**OpenClawに自由なロボット制御パラメータを作らせない**ことである。

OpenClawは、`vx`、`vyaw`、`duration` などを自由生成しない。  
OpenClawは、あらかじめRobot Bridge側で定義された安全Actionを選ぶだけにする。

---

## 1. Phase 2のゴール

Phase 2のゴールは以下。

```text
自然言語の指示
  ↓
OpenClawが安全Actionを選択
  ↓
dry-runで実行内容を説明
  ↓
人間が確認
  ↓
Robot Bridgeが固定済みAction Sequenceを実行
  ↓
必ずStopMoveして終了
```

例：

```text
Go2に軽く挨拶させて。
```

OpenClawは、自由に動作を作らず、既存Actionから以下を選ぶ。

```text
go2_greeting_demo
```

OpenClawがまずdry-runを実行する。

```bash
python unitree_action_client.py dry-run go2_greeting_demo
```

人間が確認した後だけ実行する。

```bash
python unitree_action_client.py run go2_greeting_demo --confirm
```

---

## 2. Phase 2の基本方針

Phase 2では、以下の原則を守る。

| 原則                             | 内容                                                     |
| -------------------------------- | -------------------------------------------------------- |
| OpenClawはSDKを直接呼ばない      | Unitree SDK2のscriptやimportをOpenClawから直接使わせない |
| OpenClawは速度値を自由生成しない | `vx`, `vy`, `vyaw`, `duration` はAction Library側で固定  |
| 実行前に必ずdry-run              | 物理動作前に、実行予定stepを人間に表示                   |
| 人間確認なしでmotion実行しない   | `--confirm` がない場合はBridge側で拒否                   |
| すべてのmove後にStopMove         | 各move step後、さらにfinallyでもStopMove                 |
| stopは常に最優先                 | action実行中でも停止命令を優先                           |
| 実行ログを残す                   | action名、step、時刻、結果、エラーを記録                 |
| G1はBonus扱い                    | Phase 2の主対象はGo2。G1はwave/shake程度に制限           |

---

## 3. 全体アーキテクチャ

```text
[User]
   |
   | Natural language
   v
[OpenClaw inside NemoClaw sandbox]
   |
   | exec: python unitree_action_client.py dry-run/run/list/stop
   v
[unitree_action_client.py]
   |
   | HTTP / JSON
   v
[Robot Bridge on Host PC]
   |
   | Action Library
   | Safety Supervisor
   | Logger
   | SDK Adapter
   v
[Unitree SDK2 / SDK2 Python]
   |
   v
[Unitree Go2]
```

---

## 4. Phase 2で追加する構成要素

Phase 1の成果物：

```text
unitree_nemoclaw_demo/
├── robot_bridge.py
├── unitree_bridge_client.py
├── unitree-robot-bridge.yaml
├── AGENTS_unitree_rules.md
└── README.md
```

Phase 2では、以下に拡張する。

```text
unitree_nemoclaw_demo/
├── bridge/
│   ├── robot_bridge.py
│   ├── action_library.py
│   ├── safety_supervisor.py
│   ├── unitree_sdk_adapter.py
│   └── logger.py
├── config/
│   ├── actions.go2.yaml
│   ├── actions.g1.yaml
│   └── safety_limits.yaml
├── openclaw/
│   ├── unitree_action_client.py
│   └── AGENTS_unitree_phase2.md
├── policy/
│   └── unitree-robot-bridge.yaml
└── README.md
```

---

## 5. Robot Bridge API設計

Phase 1のAPI：

```text
GET  /health
GET  /robot/status
POST /robot/stop
POST /robot/command
```

Phase 2では、Action実行用APIを追加する。

```text
GET  /health
GET  /robot/status
POST /robot/stop

GET  /actions
POST /actions/{action_name}/dry-run
POST /actions/{action_name}/execute

POST /sequence/dry-run
POST /sequence/execute

GET  /logs/recent
```

Phase 2でOpenClawに主に使わせるのは以下だけでよい。

```bash
python unitree_action_client.py list
python unitree_action_client.py status
python unitree_action_client.py stop
python unitree_action_client.py dry-run <action_name>
python unitree_action_client.py run <action_name> --confirm
```

---

## 6. Action Libraryの考え方

Phase 2の中心は `Action Library` である。

Action Libraryには、許可済みの短い動作だけをYAMLで定義する。

OpenClawはAction名だけを選ぶ。  
速度、時間、角速度、wait、StopMoveなどはBridge側に固定する。

### 6.1 `actions.go2.yaml` の例

```yaml
actions:
  go2_status_check:
    description: "Check Go2 status only. No physical motion."
    risk: read_only
    requires_confirmation: false
    steps:
      - type: status

  go2_stop:
    description: "Send StopMove to Go2."
    risk: low
    requires_confirmation: false
    steps:
      - type: stop

  go2_forward_short:
    description: "Move forward slowly for a short time, then stop."
    risk: low_motion
    requires_confirmation: true
    steps:
      - type: status
      - type: balance_stand
      - type: wait
        duration: 0.5
      - type: move
        vx: 0.12
        vy: 0.0
        vyaw: 0.0
        duration: 0.8
      - type: stop
      - type: wait
        duration: 0.3
      - type: status

  go2_turn_left_short:
    description: "Turn left slowly, then stop."
    risk: low_motion
    requires_confirmation: true
    steps:
      - type: status
      - type: move
        vx: 0.0
        vy: 0.0
        vyaw: 0.20
        duration: 0.7
      - type: stop
      - type: status

  go2_turn_right_short:
    description: "Turn right slowly, then stop."
    risk: low_motion
    requires_confirmation: true
    steps:
      - type: status
      - type: move
        vx: 0.0
        vy: 0.0
        vyaw: -0.20
        duration: 0.7
      - type: stop
      - type: status

  go2_greeting_demo:
    description: "Small greeting motion: stand, turn left, turn right, stop."
    risk: low_motion
    requires_confirmation: true
    steps:
      - type: status
      - type: balance_stand
      - type: wait
        duration: 0.8
      - type: move
        vx: 0.0
        vy: 0.0
        vyaw: 0.20
        duration: 0.6
      - type: stop
      - type: wait
        duration: 0.3
      - type: move
        vx: 0.0
        vy: 0.0
        vyaw: -0.20
        duration: 0.6
      - type: stop
      - type: status
```

---

## 7. Safety Limits

`config/safety_limits.yaml` を作る。

```yaml
limits:
  max_action_time: 5.0
  max_move_duration: 1.0
  max_move_steps_per_action: 2

  go2:
    max_vx: 0.20
    max_vy: 0.10
    max_vyaw: 0.30

  g1:
    max_vx: 0.05
    max_vy: 0.00
    max_vyaw: 0.10

rules:
  require_status_before_motion: true
  require_status_after_motion: true
  require_stop_after_each_move: true
  require_final_stop: true
  require_human_confirmation_for_motion: true
  reject_unknown_action: true
  reject_freeform_motion: true
```

---

## 8. Robot Bridge側の実装イメージ

### 8.1 Action Library Loader

```python
# bridge/action_library.py
import yaml
from pathlib import Path

class ActionLibrary:
    def __init__(self, yaml_path: str):
        self.yaml_path = Path(yaml_path)
        self.actions = self._load()

    def _load(self):
        with self.yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("actions", {})

    def list_actions(self):
        return [
            {
                "name": name,
                "description": action.get("description", ""),
                "risk": action.get("risk", "unknown"),
                "requires_confirmation": action.get("requires_confirmation", True),
            }
            for name, action in self.actions.items()
        ]

    def get_action(self, name: str):
        if name not in self.actions:
            raise KeyError(f"Unknown action: {name}")
        return self.actions[name]
```

---

### 8.2 Safety Supervisor

```python
# bridge/safety_supervisor.py
import time

class SafetySupervisor:
    def __init__(self, limits: dict):
        self.limits = limits

    def validate_action(self, action_name: str, action: dict, confirmed: bool):
        requires_confirmation = action.get("requires_confirmation", True)
        risk = action.get("risk", "unknown")

        if requires_confirmation and not confirmed:
            raise PermissionError(
                f"Action '{action_name}' requires human confirmation"
            )

        move_count = 0
        for step in action.get("steps", []):
            step_type = step.get("type")

            if step_type == "move":
                move_count += 1
                self._validate_move_step(step)

        max_move_steps = self.limits["limits"]["max_move_steps_per_action"]
        if move_count > max_move_steps:
            raise ValueError(
                f"Too many move steps: {move_count} > {max_move_steps}"
            )

    def _validate_move_step(self, step: dict):
        go2_limits = self.limits["limits"]["go2"]

        vx = abs(float(step.get("vx", 0.0)))
        vy = abs(float(step.get("vy", 0.0)))
        vyaw = abs(float(step.get("vyaw", 0.0)))
        duration = float(step.get("duration", 0.0))

        if vx > go2_limits["max_vx"]:
            raise ValueError("vx exceeds safety limit")
        if vy > go2_limits["max_vy"]:
            raise ValueError("vy exceeds safety limit")
        if vyaw > go2_limits["max_vyaw"]:
            raise ValueError("vyaw exceeds safety limit")
        if duration > self.limits["limits"]["max_move_duration"]:
            raise ValueError("move duration exceeds safety limit")
```

---

### 8.3 Unitree SDK Adapter

実機接続前はdry-run用のdummy adapterから始める。

```python
# bridge/unitree_sdk_adapter.py
import time

class UnitreeGo2Adapter:
    def __init__(self, dry_mode: bool = True):
        self.dry_mode = dry_mode

        if not dry_mode:
            # TODO: 実環境に合わせてUnitree SDK2 Pythonを初期化する
            # from unitree_sdk2py.go2.sport.sport_client import SportClient
            # self.sport_client = SportClient()
            # self.sport_client.SetTimeout(10.0)
            # self.sport_client.Init()
            pass

    def status(self):
        return {
            "robot": "go2",
            "connected": True,
            "mode": "sport",
            "safe_to_move": True,
            "dry_mode": self.dry_mode,
        }

    def stop(self):
        if self.dry_mode:
            return {"executed": "StopMove", "dry_mode": True}

        # self.sport_client.StopMove()
        return {"executed": "StopMove", "dry_mode": False}

    def balance_stand(self):
        if self.dry_mode:
            return {"executed": "BalanceStand", "dry_mode": True}

        # self.sport_client.BalanceStand()
        return {"executed": "BalanceStand", "dry_mode": False}

    def move(self, vx: float, vy: float, vyaw: float, duration: float):
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

            # self.sport_client.Move(vx, vy, vyaw)
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
```

---

### 8.4 Robot Bridge API

```python
# bridge/robot_bridge.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml
import time
from pathlib import Path

from action_library import ActionLibrary
from safety_supervisor import SafetySupervisor
from unitree_sdk_adapter import UnitreeGo2Adapter

app = FastAPI(title="Unitree Robot Bridge Phase 2")

ACTION_YAML = "../config/actions.go2.yaml"
LIMITS_YAML = "../config/safety_limits.yaml"

library = ActionLibrary(ACTION_YAML)

with open(LIMITS_YAML, "r", encoding="utf-8") as f:
    limits = yaml.safe_load(f)

supervisor = SafetySupervisor(limits)
adapter = UnitreeGo2Adapter(dry_mode=True)

class ExecuteRequest(BaseModel):
    confirmed: bool = False

@app.get("/health")
def health():
    return {"status": "ok", "phase": 2}

@app.get("/robot/status")
def robot_status():
    return adapter.status()

@app.post("/robot/stop")
def robot_stop():
    return adapter.stop()

@app.get("/actions")
def list_actions():
    return {"actions": library.list_actions()}

@app.post("/actions/{action_name}/dry-run")
def dry_run_action(action_name: str):
    try:
        action = library.get_action(action_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "action": action_name,
        "will_execute": False,
        "requires_confirmation": action.get("requires_confirmation", True),
        "risk": action.get("risk", "unknown"),
        "steps": action.get("steps", []),
    }

@app.post("/actions/{action_name}/execute")
def execute_action(action_name: str, req: ExecuteRequest):
    try:
        action = library.get_action(action_name)
        supervisor.validate_action(action_name, action, confirmed=req.confirmed)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    results = []
    start_time = time.time()

    try:
        for step in action.get("steps", []):
            step_type = step.get("type")

            if step_type == "status":
                results.append(adapter.status())

            elif step_type == "stop":
                results.append(adapter.stop())

            elif step_type == "balance_stand":
                results.append(adapter.balance_stand())

            elif step_type == "wait":
                duration = float(step.get("duration", 0.1))
                time.sleep(duration)
                results.append({"executed": "wait", "duration": duration})

            elif step_type == "move":
                result = adapter.move(
                    vx=float(step.get("vx", 0.0)),
                    vy=float(step.get("vy", 0.0)),
                    vyaw=float(step.get("vyaw", 0.0)),
                    duration=float(step.get("duration", 0.1)),
                )
                results.append(result)
                results.append(adapter.stop())

            else:
                raise ValueError(f"Unsupported step type: {step_type}")

            elapsed = time.time() - start_time
            if elapsed > limits["limits"]["max_action_time"]:
                raise TimeoutError("Action exceeded max_action_time")

    finally:
        final_stop = adapter.stop()
        results.append({"final_stop": final_stop})

    return {
        "ok": True,
        "action": action_name,
        "results": results,
        "auto_stop": True,
    }
```

---

## 9. OpenClaw側Client

Phase 2では、OpenClawから直接 `curl` させるより、専用client scriptを使う。

### 9.1 `unitree_action_client.py`

```python
# openclaw/unitree_action_client.py
import argparse
import requests
import json

BRIDGE_URL = "http://<HOST_IP>:50001"


def pretty(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def get(path):
    r = requests.get(f"{BRIDGE_URL}{path}", timeout=5)
    r.raise_for_status()
    pretty(r.json())


def post(path, payload=None):
    r = requests.post(f"{BRIDGE_URL}{path}", json=payload or {}, timeout=10)
    r.raise_for_status()
    pretty(r.json())


parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="cmd", required=True)

sub.add_parser("list")
sub.add_parser("status")
sub.add_parser("stop")

dry = sub.add_parser("dry-run")
dry.add_argument("action")

run = sub.add_parser("run")
run.add_argument("action")
run.add_argument("--confirm", action="store_true")

args = parser.parse_args()

if args.cmd == "list":
    get("/actions")
elif args.cmd == "status":
    get("/robot/status")
elif args.cmd == "stop":
    post("/robot/stop")
elif args.cmd == "dry-run":
    post(f"/actions/{args.action}/dry-run")
elif args.cmd == "run":
    post(f"/actions/{args.action}/execute", {"confirmed": args.confirm})
```

OpenClawから実行させるコマンド：

```bash
python unitree_action_client.py list
python unitree_action_client.py status
python unitree_action_client.py stop
python unitree_action_client.py dry-run go2_greeting_demo
python unitree_action_client.py run go2_greeting_demo --confirm
```

---

## 10. OpenClaw用 `AGENTS.md`

NemoClaw/OpenClaw workspace内に、以下のようなルールを置く。

### 10.1 `AGENTS_unitree_phase2.md`

```md
# Unitree Robot Control Rules - Phase 2

You are controlling a physical Unitree robot through a restricted Robot Bridge.

You must follow these rules strictly.

## Allowed interface

You may only control the robot through:

- python unitree_action_client.py list
- python unitree_action_client.py status
- python unitree_action_client.py stop
- python unitree_action_client.py dry-run <action_name>
- python unitree_action_client.py run <action_name> --confirm

## Prohibited operations

Never do the following:

1. Never call Unitree SDK scripts directly.
2. Never import Unitree SDK directly.
3. Never generate raw velocity, yaw, duration, joint, or motor commands.
4. Never create new motion actions by yourself.
5. Never run continuous motion.
6. Never execute flips, jumps, dances, handstands, running, or low-level control.
7. Never bypass Robot Bridge.
8. Never modify the Action Library unless explicitly asked by the developer.

## Motion execution workflow

For any physical motion action:

1. Check available actions with:
   python unitree_action_client.py list

2. Select the closest existing safe action.

3. Dry-run first:
   python unitree_action_client.py dry-run <action_name>

4. Explain the planned action to the user.

5. Ask for human confirmation.

6. Only after confirmation, execute:
   python unitree_action_client.py run <action_name> --confirm

7. If anything is unclear, run:
   python unitree_action_client.py stop

## Safety priority

Stopping the robot is always allowed and always has priority.

If the user asks for an unsafe action, refuse and offer one of:

- status
- stop
- go2_status_check
- go2_greeting_demo
- go2_forward_short
```

---

## 11. NemoClaw Network Policy

Phase 2でも、NemoClaw sandboxからRobot Bridgeだけに通信させる。

例：`policy/unitree-robot-bridge.yaml`

```yaml
preset:
  name: unitree-robot-bridge
  description: "Allow OpenClaw sandbox to call only the Unitree Robot Bridge API"

network_policies:
  unitree_robot_bridge:
    name: unitree_robot_bridge
    endpoints:
      - host: <HOST_IP>
        port: 50001
        protocol: rest
        enforcement: enforce
        rules:
          - allow: { method: GET, path: "/health" }
          - allow: { method: GET, path: "/robot/status" }
          - allow: { method: POST, path: "/robot/stop" }
          - allow: { method: GET, path: "/actions" }
          - allow: { method: POST, path: "/actions/*/dry-run" }
          - allow: { method: POST, path: "/actions/*/execute" }
          - allow: { method: GET, path: "/logs/recent" }
    binaries:
      - { path: /usr/bin/curl }
      - { path: /usr/bin/python3 }
```

適用前確認：

```bash
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml --dry-run
```

適用：

```bash
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml
```

確認：

```bash
nemoclaw my-assistant policy-list
nemoclaw my-assistant policy-explain
```

---

## 12. 実行手順

### 12.1 Host側でBridgeを起動

```bash
cd unitree_nemoclaw_demo/bridge
uvicorn robot_bridge:app --host 0.0.0.0 --port 50001
```

health確認：

```bash
curl http://<HOST_IP>:50001/health
```

期待値：

```json
{
  "status": "ok",
  "phase": 2
}
```

---

### 12.2 NemoClaw policyを適用

```bash
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml --dry-run
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml
```

---

### 12.3 sandboxに入る

```bash
nemoclaw my-assistant connect
```

---

### 12.4 OpenClaw用clientを配置

sandbox内で：

```bash
python unitree_action_client.py status
python unitree_action_client.py list
```

---

### 12.5 OpenClaw TUIを起動

```bash
openclaw tui
```

---

## 13. デモシナリオ

### Demo 1: Action一覧を表示

ユーザー：

```text
Go2で実行可能な安全actionを一覧表示してください。
```

OpenClawが実行：

```bash
python unitree_action_client.py list
```

期待される返答：

```text
実行可能なActionは以下です。

- go2_status_check: 状態確認のみ
- go2_stop: StopMove
- go2_forward_short: 短い前進
- go2_turn_left_short: 短い左旋回
- go2_turn_right_short: 短い右旋回
- go2_greeting_demo: 小さい挨拶動作
```

---

### Demo 2: Dry-runのみ

ユーザー：

```text
go2_greeting_demoの内容を確認して。まだ実行しないで。
```

OpenClawが実行：

```bash
python unitree_action_client.py dry-run go2_greeting_demo
```

期待される説明：

```text
go2_greeting_demoは以下の順で実行予定です。

1. status確認
2. BalanceStand
3. 0.8秒待機
4. 左に小さく旋回
5. StopMove
6. 0.3秒待機
7. 右に小さく旋回
8. StopMove
9. status確認

まだ実行していません。
```

---

### Demo 3: 人間確認後に実行

ユーザー：

```text
確認しました。go2_greeting_demoを実行してください。
```

OpenClawが実行：

```bash
python unitree_action_client.py run go2_greeting_demo --confirm
```

期待される結果：

```json
{
  "ok": true,
  "action": "go2_greeting_demo",
  "auto_stop": true
}
```

---

### Demo 4: 自然言語からAction選択

ユーザー：

```text
Go2に軽く挨拶させて。
```

OpenClawの望ましい動作：

```text
既存Actionの中では go2_greeting_demo が最も近いです。
まずdry-runします。
```

OpenClawが実行：

```bash
python unitree_action_client.py dry-run go2_greeting_demo
```

その後、ユーザー確認後に：

```bash
python unitree_action_client.py run go2_greeting_demo --confirm
```

---

### Demo 5: Stop優先

ユーザー：

```text
止めて。
```

OpenClawが実行：

```bash
python unitree_action_client.py stop
```

停止命令は確認不要にする。

---

## 14. G1 Bonus Demoの扱い

Phase 2の主対象はGo2。  
G1はBonus扱いにする。

G1で許可してよい候補：

```text
g1_status_check
g1_stop
g1_wave_hand
g1_shake_hand
```

G1ではPhase 2時点で以下を避ける。

```text
walk
run
turn while walking
squat sequence
recovery sequence
low-level joint control
```

G1は二足ロボットで転倒リスクが高いため、Phase 2では歩行系を入れない。  
面白さを出すなら、`wave hand` や `shake hand` のようなHigh-level non-locomotion actionに限定する。

---

## 15. Phase 2の成功条件

Phase 2は、以下が満たせれば完成。

```text
1. OpenClawから実行可能Action一覧を取得できる
2. OpenClawが自然言語から既存Actionを選べる
3. OpenClawが必ずdry-runを先に行う
4. 人間確認なしではmotion actionを実行しない
5. Robot BridgeがAction Libraryに定義されたstepだけを実行する
6. 各move後にStopMoveが必ず入る
7. action終了時にfinal StopMoveが必ず入る
8. stopは確認なしで常に実行できる
9. Safety Supervisorが速度・時間・step数を検証する
10. 実行ログが残る
11. NemoClaw policyでRobot Bridge以外への通信を許可しない
12. G1はBonusとしてwave/shake程度に限定する
```

---

## 16. Phase 2の完成イメージ

OpenClawとのやり取り例：

```text
User:
Go2に軽く挨拶させて。

OpenClaw:
既存Actionの中では go2_greeting_demo が該当します。
まずdry-runで内容を確認します。

[exec]
python unitree_action_client.py dry-run go2_greeting_demo

OpenClaw:
実行予定は以下です。
1. status確認
2. BalanceStand
3. 左に小さく旋回
4. StopMove
5. 右に小さく旋回
6. StopMove
7. status確認

この動作を実行してよろしいですか？

User:
はい、実行してください。

OpenClaw:
実行します。

[exec]
python unitree_action_client.py run go2_greeting_demo --confirm

OpenClaw:
実行完了しました。auto_stop=trueで終了しています。
```

---

## 17. Phase 3への接続

Phase 2では、まだ「固定Action Library」だけを使う。

Phase 3では、以下に進める。

```text
- ROS2 / Unitree ROS2連携
- Nav2 / SLAM / waypoint移動
- カメラ認識と物体検出
- G1 + Go2の複数ロボット統合
- Action Libraryの半自動生成
- Task Plannerとの接続
- VLMによる環境理解
- Human approval UI
- 実行ログからの安全評価
```

Phase 2の目的は、**ロボットを賢くすることではなく、安全に選べる行動の種類を増やすこと**である。

---

## 18. 参考情報

- NVIDIA NemoClaw Documentation  
  https://docs.nvidia.com/nemoclaw/

- NemoClaw Network Policy / Custom Policy  
  https://docs.nvidia.com/nemoclaw/latest/reference/network-policies.html

- NemoClaw Workspace Files  
  https://docs.nvidia.com/nemoclaw/latest/

- OpenClaw Tools / Exec Tool  
  https://docs.openclaw.ai/tools

- Unitree SDK2 Python  
  https://github.com/unitreerobotics/unitree_sdk2_python

- Unitree SDK2  
  https://github.com/unitreerobotics/unitree_sdk2
