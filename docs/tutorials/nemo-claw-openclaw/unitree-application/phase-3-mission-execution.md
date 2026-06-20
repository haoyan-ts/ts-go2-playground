# NemoClaw / OpenClaw × Unitree 応用編 Phase 3

## Phase 3: Context-Aware Mission Execution with Safety Supervisor

このドキュメントは、NemoClaw / OpenClaw を用いて Unitree Go2 / G1 を制御する応用編チュートリアルの Phase 3 です。

Phase 1 では、OpenClaw から Robot Bridge 経由で Unitree SDK2 の High-level API を 1 回だけ呼び出しました。

Phase 2 では、Robot Bridge 側に Safe Action Library を置き、短い Action Sequence を dry-run → 人間確認 → 実行する構成にしました。

Phase 3 では、さらに上位の **Mission Library** を導入し、OpenClaw が自然言語指示から安全な Mission を選び、Mission Supervisor が実行・監視・中断・結果報告を行う構成にします。

---

## 0. Phase 3 の位置づけ

```text
Phase 1:
Natural language → single SDK high-level call

Phase 2:
Natural language → fixed safe action sequence

Phase 3:
Natural language → safe mission selection → observe / execute / monitor / report
```

Phase 3 の目的は、ロボットを自由に自律化することではありません。

目的は、**許可済み Mission の中から OpenClaw が適切なものを選び、Robot Bridge / Mission Supervisor が安全に実行する** ことです。

---

## 1. Phase 3 のゴール

Phase 3 の最小ゴールは次の通りです。

```text
ユーザー:
Go2で展示エリアを軽く巡回して、最後に状態を報告して。

OpenClaw:
許可済みMissionから go2_demo_patrol を選択

Robot Bridge:
Mission Libraryを読み込み、各stepをSafety Supervisor経由で実行

Go2:
短距離Missionを実行

OpenClaw:
実行結果・状態・ログ要約を報告
```

Phase 3 で重要な設計原則は次の通りです。

```text
OpenClaw は Mission を選ぶだけ。
速度、時間、Waypoint、StopMove、Timeout、安全判定は Robot Bridge / Mission Supervisor 側で管理する。
```

---

## 2. 全体アーキテクチャ

```text
[OpenClaw inside NemoClaw sandbox]
        |
        | unitree_mission_client.py
        v
[Robot Bridge / Mission Supervisor]
        |
        ├── Mission Library
        ├── Action Library
        ├── Safety Supervisor
        ├── World State
        ├── Perception Summary
        ├── Unitree SDK Adapter
        └── Logger
        |
        v
[Unitree SDK2 / ROS2 Adapter]
        |
        v
[Go2 / G1]
```

### 各コンポーネントの役割

| コンポーネント | 役割 |
|---|---|
| OpenClaw | 自然言語指示を解釈し、許可済み Mission を選ぶ |
| NemoClaw | OpenClaw sandbox、network policy、ログ、権限制御を担当 |
| unitree_mission_client.py | OpenClaw から Robot Bridge を呼ぶための限定 client |
| Robot Bridge | OpenClaw と Unitree SDK2 の間の安全 API サーバー |
| Mission Supervisor | Mission 実行、監視、中断、完了管理 |
| Mission Library | 許可済み Mission 定義 |
| Action Library | Phase 2 で作った短い安全 Action 群 |
| World State | demo zone、waypoint、robot 状態など |
| Safety Supervisor | 速度、時間、エリア、E-stop、異常時 StopMove を管理 |
| Logger | 実行履歴、失敗理由、最終状態を保存 |

---

## 3. Phase 3 で追加する概念

### 3.1 Mission Library

Phase 2 の Action Library は、短い動作単位でした。

例：

```text
go2_forward_short
go2_turn_left_short
go2_greeting_demo
```

Phase 3 の Mission Library は、それらを組み合わせた上位タスクです。

例：

```text
go2_demo_patrol
go2_inspection_walk
g1_welcome_guest
```

OpenClaw は自由に Mission を作りません。

OpenClaw は、既存の Mission Library から選択するだけです。

---

### 3.2 World State

Phase 3 では、Robot Bridge 側に簡単な環境情報を持たせます。

例：

```yaml
world:
  zones:
    demo_zone:
      description: "Safe indoor demo area"
      allowed_robots: ["go2"]
      max_speed: 0.2

  waypoints:
    home:
      x: 0.0
      y: 0.0
      yaw: 0.0

    demo_A:
      x: 0.8
      y: 0.0
      yaw: 0.0

    inspection_A:
      x: 1.0
      y: 0.5
      yaw: 1.57
```

Phase 3 の最小版では、SLAM / Nav2 を必須にしません。

最初は、**事前登録した waypoint に対して、固定的な短距離 Mission を実行する** 方が安全です。

---

### 3.3 Perception Summary

OpenClaw にカメラ画像や LiDAR データを直接処理させるのではなく、Robot Bridge 側で要約した観測情報だけを渡します。

例：

```json
{
  "robot": "go2",
  "location": "demo_A",
  "battery": 78,
  "obstacle_front": false,
  "human_nearby": true,
  "safe_to_move": true,
  "last_action": "arrived_demo_A"
}
```

OpenClaw はこの情報を見て説明します。

```text
現在 demo_A に到着しています。
前方障害物はありません。
近くに人がいるため、低速 Mission のまま実行します。
```

ただし、実際の中断判断は OpenClaw ではなく、Mission Supervisor / Safety Supervisor 側で行います。

---

## 4. Mission Library の例

`config/missions.go2.yaml` を作成します。

```yaml
missions:
  go2_demo_patrol:
    description: "Go2 performs a short demo patrol between predefined waypoints."
    robot: go2
    risk: supervised_motion
    requires_confirmation: true
    max_duration: 20.0
    allowed_area: demo_zone
    steps:
      - type: status
      - type: balance_stand
      - type: move_to_waypoint
        waypoint: demo_A
      - type: observe
        duration: 2.0
      - type: turn_left_short
      - type: move_to_waypoint
        waypoint: home
      - type: stop
      - type: report

  go2_inspection_walk:
    description: "Go2 moves to a predefined inspection point and reports status."
    robot: go2
    risk: supervised_motion
    requires_confirmation: true
    max_duration: 30.0
    allowed_area: demo_zone
    steps:
      - type: status
      - type: balance_stand
      - type: move_to_waypoint
        waypoint: inspection_A
      - type: observe
        duration: 3.0
      - type: status
      - type: move_to_waypoint
        waypoint: home
      - type: stop
      - type: report

  go2_status_report:
    description: "Read-only mission. Check Go2 status and summarize it."
    robot: go2
    risk: read_only
    requires_confirmation: false
    max_duration: 5.0
    steps:
      - type: status
      - type: report
```

---

## 5. G1 Mission の扱い

Phase 3 でも、G1 は主役にしません。

G1 は歩行 Mission ではなく、**Gesture Mission** に限定します。

`config/missions.g1.yaml` の例：

```yaml
missions:
  g1_welcome_guest:
    description: "G1 performs a non-walking welcome gesture."
    robot: g1
    risk: gesture_only
    requires_confirmation: true
    max_duration: 10.0
    steps:
      - type: status
      - type: wave_hand
      - type: speak
        text: "Welcome to the demo."
      - type: stop
      - type: report

  g1_greeting_demo:
    description: "G1 performs a short greeting gesture only."
    robot: g1
    risk: gesture_only
    requires_confirmation: true
    max_duration: 10.0
    steps:
      - type: status
      - type: wave_hand
      - type: stop
      - type: report
```

Phase 3 での G1 のルール：

```text
1. G1 は歩行 Mission を実行しない
2. G1 は gesture_only Mission のみ許可
3. WaveHand / ShakeHand / Speak などに限定
4. 人間確認なしでは実行しない
5. 異常時は即 Stop
```

---

## 6. Robot Bridge API 拡張

Phase 2 の API：

```text
GET  /actions
POST /actions/{action_name}/dry-run
POST /actions/{action_name}/execute
POST /robot/stop
GET  /logs/recent
```

Phase 3 では、Mission 用 API を追加します。

```text
GET  /missions
POST /missions/{mission_name}/dry-run
POST /missions/{mission_name}/execute
GET  /mission/status
POST /mission/cancel
GET  /world/status
GET  /robots/status
POST /robot/stop
GET  /logs/recent
```

OpenClaw は HTTP API を直接叩かず、`unitree_mission_client.py` だけを使います。

---

## 7. OpenClaw 側 client

`openclaw/unitree_mission_client.py` を用意します。

### 使用コマンド

```bash
python unitree_mission_client.py list
python unitree_mission_client.py dry-run go2_demo_patrol
python unitree_mission_client.py run go2_demo_patrol --confirm
python unitree_mission_client.py status
python unitree_mission_client.py cancel
python unitree_mission_client.py stop
```

### client の最小仕様

```python
# unitree_mission_client.py
import argparse
import requests

BRIDGE_URL = "http://<HOST_IP>:50001"


def get(path):
    r = requests.get(f"{BRIDGE_URL}{path}", timeout=5)
    r.raise_for_status()
    print(r.json())


def post(path, payload=None):
    r = requests.post(f"{BRIDGE_URL}{path}", json=payload or {}, timeout=10)
    r.raise_for_status()
    print(r.json())


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=["list", "dry-run", "run", "status", "cancel", "stop", "world"])
parser.add_argument("name", nargs="?")
parser.add_argument("--confirm", action="store_true")
args = parser.parse_args()


if args.command == "list":
    get("/missions")
elif args.command == "dry-run":
    if not args.name:
        raise SystemExit("mission name is required")
    post(f"/missions/{args.name}/dry-run")
elif args.command == "run":
    if not args.name:
        raise SystemExit("mission name is required")
    post(f"/missions/{args.name}/execute", {"confirmed": args.confirm})
elif args.command == "status":
    get("/mission/status")
elif args.command == "cancel":
    post("/mission/cancel")
elif args.command == "stop":
    post("/robot/stop")
elif args.command == "world":
    get("/world/status")
```

---

## 8. Mission Supervisor の実装イメージ

Mission Supervisor は、Mission の step を順番に実行し、安全条件を常に確認します。

### 基本ループ

```python
def execute_mission(mission, confirmed: bool):
    if mission.requires_confirmation and not confirmed:
        raise PermissionError("Human confirmation required")

    check_mission_is_allowed(mission)
    check_world_state_or_raise(mission)
    check_robot_status_or_raise(mission.robot)

    start_time = time.time()
    mission_state = "running"

    try:
        for step in mission.steps:
            if time.time() - start_time > mission.max_duration:
                raise TimeoutError("Mission timeout")

            if emergency_stop_requested():
                raise RuntimeError("Emergency stop requested")

            if not safety_supervisor.is_safe_to_continue(mission, step):
                raise RuntimeError("Safety supervisor blocked mission")

            execute_step(step)

            if step["type"] in ["move", "move_to_waypoint", "turn_left_short", "turn_right_short"]:
                sdk_adapter.stop_move(mission.robot)

        mission_state = "completed"

    except Exception as e:
        mission_state = "aborted"
        mission_error = str(e)
        sdk_adapter.stop_move(mission.robot)
        raise

    finally:
        sdk_adapter.stop_move(mission.robot)
        logger.log_mission_result(
            mission=mission.name,
            state=mission_state,
            duration=time.time() - start_time,
        )
```

### 重要な点

```text
1. Mission開始前に robot status を確認する
2. Mission開始前に world state を確認する
3. 各 motion step 後に StopMove を入れる
4. Mission全体にも timeout を入れる
5. 例外時は必ず StopMove を呼ぶ
6. 実行ログを残す
```

---

## 9. Safety Supervisor ルール

Phase 3 の Safety Supervisor では、最低限以下を管理します。

```yaml
safety_limits:
  global:
    max_mission_duration: 30.0
    max_motion_step_duration: 1.5
    max_consecutive_motion_steps: 2
    require_stop_after_motion: true
    require_status_before_mission: true
    require_status_after_mission: true

  go2:
    max_speed: 0.2
    max_yaw_rate: 0.3
    allowed_zones:
      - demo_zone

  g1:
    allowed_mission_risk:
      - gesture_only
    walking_allowed: false
```

### 禁止事項

```text
- OpenClaw による自由軌道生成
- OpenClaw による Unitree SDK 直接 import
- OpenClaw による新規 Mission 生成
- Go2 の flip / jump / dance / handstand
- G1 の自由歩行 Mission
- Low-level motor control
- 画像認識結果のみでの自動実行
- 外部Web情報に基づく Mission 変更
```

---

## 10. OpenClaw 用 AGENTS.md

OpenClaw の workspace に Phase 3 用ルールを置きます。

例：`openclaw/AGENTS_unitree_phase3.md`

```md
# Unitree Phase 3 Rules

You may control Unitree robots only through unitree_mission_client.py.

Allowed commands:

- python unitree_mission_client.py list
- python unitree_mission_client.py dry-run <mission_name>
- python unitree_mission_client.py run <mission_name> --confirm
- python unitree_mission_client.py status
- python unitree_mission_client.py cancel
- python unitree_mission_client.py stop
- python unitree_mission_client.py world

Rules:

1. Never call Unitree SDK directly.
2. Never create new motion parameters.
3. Never create new missions during runtime.
4. Only choose from the existing Mission Library.
5. Always dry-run before mission execution.
6. Always ask for human confirmation before physical motion.
7. Always stop or cancel if the instruction is unclear.
8. Never execute flips, jumps, running, handstand, dance, or low-level motor control.
9. For G1, only gesture missions are allowed in Phase 3.
10. If the Mission Supervisor reports unsafe state, do not continue the mission.
11. If a user asks for an unsafe mission, refuse and offer status, stop, or a safe dry-run instead.
12. After a mission, summarize the result, final robot state, and any safety events.
```

---

## 11. NemoClaw Network Policy

Phase 3 でも、NemoClaw sandbox からの通信先は Robot Bridge のみに限定します。

例：`policy/unitree-robot-bridge.yaml`

```yaml
preset:
  name: unitree-robot-bridge
  description: "Allow OpenClaw sandbox to call only the Unitree Robot Bridge"

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
          - allow: { method: GET, path: "/missions" }
          - allow: { method: POST, path: "/missions/*/dry-run" }
          - allow: { method: POST, path: "/missions/*/execute" }
          - allow: { method: GET, path: "/mission/status" }
          - allow: { method: POST, path: "/mission/cancel" }
          - allow: { method: GET, path: "/world/status" }
          - allow: { method: GET, path: "/robots/status" }
          - allow: { method: POST, path: "/robot/stop" }
          - allow: { method: GET, path: "/logs/recent" }
    binaries:
      - { path: /usr/bin/python3 }
      - { path: /usr/bin/curl }
```

適用例：

```bash
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml --dry-run
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml
```

---

## 12. Phase 3 のディレクトリ構成

```text
unitree_nemoclaw_demo/
├── bridge/
│   ├── robot_bridge.py
│   ├── mission_supervisor.py
│   ├── action_library.py
│   ├── mission_library.py
│   ├── safety_supervisor.py
│   ├── world_state.py
│   ├── perception_summary.py
│   ├── unitree_sdk_adapter.py
│   └── logger.py
├── config/
│   ├── actions.go2.yaml
│   ├── actions.g1.yaml
│   ├── missions.go2.yaml
│   ├── missions.g1.yaml
│   ├── world.demo.yaml
│   └── safety_limits.yaml
├── openclaw/
│   ├── unitree_mission_client.py
│   └── AGENTS_unitree_phase3.md
├── policy/
│   └── unitree-robot-bridge.yaml
└── README.md
```

---

## 13. Demo 1: Mission 一覧を表示

ユーザー：

```text
Go2で実行できるMissionを教えて。
```

OpenClaw が実行：

```bash
python unitree_mission_client.py list
```

OpenClaw の返答例：

```text
実行可能なMissionは以下です。

1. go2_demo_patrol
   展示エリア内の短い巡回Missionです。

2. go2_inspection_walk
   事前登録された点検ポイントへ移動し、状態を確認して戻ります。

3. go2_status_report
   読み取り専用の状態確認Missionです。
```

---

## 14. Demo 2: Mission の dry-run

ユーザー：

```text
go2_demo_patrolの内容を確認して。まだ実行しないで。
```

OpenClaw が実行：

```bash
python unitree_mission_client.py dry-run go2_demo_patrol
```

Bridge の返答例：

```json
{
  "mission": "go2_demo_patrol",
  "will_execute": false,
  "requires_confirmation": true,
  "max_duration": 20.0,
  "steps": [
    "status",
    "balance_stand",
    "move_to_waypoint: demo_A",
    "observe: 2.0s",
    "turn_left_short",
    "move_to_waypoint: home",
    "stop",
    "report"
  ],
  "safety": {
    "area": "demo_zone",
    "max_speed": 0.2,
    "stop_after_each_motion": true
  }
}
```

---

## 15. Demo 3: 自然言語から Mission 選択

ユーザー：

```text
Go2に展示エリアを軽く巡回させて、最後に報告して。
```

OpenClaw の判断：

```text
該当する許可済みMissionは go2_demo_patrol です。
まずdry-runで内容を確認します。
```

OpenClaw が実行：

```bash
python unitree_mission_client.py dry-run go2_demo_patrol
```

人間確認後：

```text
確認しました。実行してください。
```

OpenClaw が実行：

```bash
python unitree_mission_client.py run go2_demo_patrol --confirm
```

---

## 16. Demo 4: 異常時の中断

Mission 実行中に、Safety Supervisor が次のような状態を検出したとします。

```json
{
  "obstacle_front": true,
  "safe_to_move": false
}
```

Mission Supervisor は即座に中断します。

```text
StopMove
mission_state = aborted
reason = obstacle_detected
```

OpenClaw の報告例：

```text
Missionは中断されました。
理由は前方障害物検出です。
Go2はStopMove済みです。
現在位置はdemo_A付近です。
```

重要なのは、**中断判断を OpenClaw に任せない**ことです。

中断判断は Mission Supervisor / Safety Supervisor 側で行います。

---

## 17. Final Demo 案: G1 受付 + Go2 巡回

Phase 3 の完成デモとして、次の構成が面白いです。

```text
1. ユーザー:
   デモを開始して。

2. OpenClaw:
   実行可能Missionを確認。

3. G1:
   g1_welcome_guest
   手を振る / 挨拶する。

4. Go2:
   go2_demo_patrol
   home → demo_A → observe → turn → home。

5. OpenClaw:
   Mission結果、最終状態、バッテリー、安全イベントを報告。
```

このデモの価値は、単にロボットを動かすことではありません。

価値は次の点にあります。

```text
自然言語
  ↓
AI Agent
  ↓
Mission選択
  ↓
dry-run
  ↓
人間確認
  ↓
安全監督付き実行
  ↓
状態報告
```

---

## 18. Phase 3 の成功条件

Phase 3 は、以下ができれば完成です。

```text
1. OpenClawがMission一覧を取得できる
2. OpenClawが自然言語から既存Missionを選べる
3. 必ずdry-runを実行する
4. 人間確認なしではMissionを実行しない
5. Mission Supervisorが各stepを管理する
6. 実行中にstatus / cancel / stopが使える
7. 異常時はBridge側で即StopMoveする
8. 実行後にOpenClawが結果レポートを作る
9. Go2は短距離Missionまで
10. G1はgesture Missionまで
11. NemoClaw policyでRobot Bridge以外への通信を禁止する
```

---

## 19. Phase 3 でやらないこと

| やらないこと | 理由 |
|---|---|
| OpenClaw に自由な軌道生成をさせる | 物理安全上危険 |
| OpenClaw に Unitree SDK を直接 import させる | Robot Bridge の意味がなくなる |
| OpenClaw に新規 Mission を実行時生成させる | 安全検証されていない |
| G1 に自由歩行 Mission をさせる | 転倒リスクが高い |
| 画像認識結果だけで自動実行 | 誤認識リスクがある |
| 外部Web情報で Mission を変更する | prompt injection リスクがある |
| Low-level motor control | Phase 3 の範囲外 |

---

## 20. まとめ

Phase 3 は、以下の構成で進めます。

```text
Mission Library
+ World State
+ Perception Summary
+ Safety Supervisor
+ Mission Supervisor
+ Result Report
```

主役は Go2 です。

G1 は Bonus として、受付・挨拶・手振りなどの gesture Mission に限定します。

Phase 3 の最小デモは：

```text
Go2に展示エリアを軽く巡回させて、結果を報告して。
```

最終デモは：

```text
G1が来場者に挨拶し、Go2が短い巡回Missionを行い、OpenClawが実行結果を報告する。
```

この構成により、Phase 1〜3 は次のように接続されます。

```text
Phase 1: High-level API を1回安全に呼ぶ
Phase 2: 安全Action Libraryから短いSequenceを実行する
Phase 3: Mission Libraryから状況認識つきMissionを監督実行する
```
