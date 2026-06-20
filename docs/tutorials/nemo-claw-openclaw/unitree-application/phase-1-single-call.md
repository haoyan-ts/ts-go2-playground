# 応用編 Phase 1: NemoClaw + OpenClaw から Unitree Go2 High-level制御を安全に呼び出す

対象: **NemoClaw + OpenClaw + Unitree Go2**  
対象外: Hermes、Low-level motor control、連続自律移動、G1本格歩行制御

> **See also**: [Foundation Tutorial](../../unitree-go2-foundation/basics.md) — for building the
> Robot Bridge foundation packages used in this phase.

---

## 0. Phase 1の目的

このPhaseの目的は、OpenClawに自然言語で指示し、Unitree Go2のHigh-level制御APIを**安全な範囲で1回だけ呼び出す**ことです。

最終的なデモ目標は次です。

```text
ユーザー: Go2を少しだけ前に出して。
OpenClaw: 実行前に確認します。0.10 m/sで0.5秒だけ前進し、終了後にStopMoveします。
ユーザー: 実行して。
OpenClaw: unitree_bridge_client.py を実行
Robot Bridge: Move(vx, vy, vyaw) → duration待機 → StopMove()
```

このPhaseでは、OpenClawにUnitree SDKを直接触らせません。  
OpenClawは、**Robot Bridge** という自作の安全APIサーバーだけを呼び出します。

---

## 1. 全体アーキテクチャ

```text
[User]
  |
  | Natural language
  v
[OpenClaw inside NemoClaw sandbox]
  |
  | exec tool: python unitree_bridge_client.py ...
  v
[unitree_bridge_client.py inside sandbox]
  |
  | HTTP / JSON
  v
[Robot Bridge on host PC]
  |
  | Unitree SDK2 Python / C++
  v
[Unitree Go2]
```

重要な考え方は、**LLMにロボットSDKを直接渡さない**ことです。

| 層                         | 役割                                           |
| -------------------------- | ---------------------------------------------- |
| OpenClaw                   | 自然言語を解釈し、許可済みコマンドを選ぶ       |
| NemoClaw / OpenShell       | sandbox化、network policy、ログ、通信制限      |
| `unitree_bridge_client.py` | OpenClawが実行する小さなHTTP client            |
| Robot Bridge               | コマンド検証、速度制限、時間制限、StopMove保証 |
| Unitree SDK2               | Go2のHigh-level APIを実際に呼ぶ                |
| Go2                        | 実機                                           |

---

## 2. Robot Bridgeとは？

**Robot Bridgeは自作プログラムです。**

NemoClawやOpenClawの標準機能ではありません。  
OpenClawとUnitree SDK2の間に置く、**安全ゲート兼APIサーバー**です。

Robot Bridgeの責務は以下です。

1. OpenClawから来たJSON commandを受け取る
2. 許可されたcommandか確認する
3. 速度・旋回速度・実行時間を制限する
4. 危険なmotionを拒否する
5. Unitree SDK2のHigh-level APIを呼ぶ
6. 例外が起きても最後に必ず `StopMove()` を呼ぶ
7. 実行ログを残す

OpenClaw側に任せてはいけないものは、Bridge側で強制します。

| 項目           | OpenClaw側 | Robot Bridge側       |
| -------------- | ---------- | -------------------- |
| 自然言語理解   | する       | しない               |
| command選択    | する       | 検証する             |
| 速度制限       | 参考程度   | 強制する             |
| 実行時間制限   | 参考程度   | 強制する             |
| StopMove保証   | 指示する   | `finally` で強制する |
| 危険motion禁止 | 指示する   | 拒否する             |
| SDK呼び出し    | しない     | する                 |

---

## 3. Phase 1で許可するGo2コマンド

Phase 1では、Go2に対して以下だけを許可します。

| command         | 目的           | SDK側の想定                         |
| --------------- | -------------- | ----------------------------------- |
| `status`        | 状態確認       | HighState取得、または接続状態確認   |
| `stop`          | 停止           | `StopMove()`                        |
| `balance_stand` | 安定立位       | `BalanceStand()`                    |
| `tiny_move`     | 小さい速度指令 | `Move(vx, vy, vyaw)` → `StopMove()` |

Phase 1では、以下を禁止します。

```text
FrontFlip
BackFlip
LeftFlip
FrontJump
FrontPounce
Dance1
Dance2
HandStand
FreeWalk
FreeJump
continuous move
trajectory follow
low-level motor control
```

---

## 4. Phase 1の安全制限

Robot Bridge側で以下を強制します。

```text
vx:       -0.20 ～ 0.20 m/s
vy:       -0.10 ～ 0.10 m/s
vyaw:     -0.30 ～ 0.30 rad/s
duration: 0.10 ～ 1.00 sec
```

推奨の初回デモ値:

```text
vx = 0.10 m/s
duration = 0.50 sec
vy = 0.0
vyaw = 0.0
```

安全方針:

1. 実行前に人間確認を必須にする
2. 最初はGo2を十分広い場所に置く
3. 周囲1.5m以内に人・机・ケーブルを置かない
4. 操作者は物理E-stopまたは純正リモコン停止手段を持つ
5. 初回は `status` → `stop` → `balance_stand` → `tiny_move` の順に行う
6. `tiny_move` 後は必ず `StopMove()` を呼ぶ
7. LLMが長時間移動を提案してもBridge側で拒否またはclampする

---

## 5. 成果物ディレクトリ

Phase 1では、以下のような構成を作ります。

```text
unitree_nemoclaw_phase1/
├── host/
│   ├── robot_bridge.py
│   ├── requirements.txt
│   └── README_host.md
├── sandbox/
│   ├── unitree_bridge_client.py
│   └── AGENTS_unitree_rules.md
├── policy/
│   └── unitree-robot-bridge.yaml
└── README.md
```

役割:

| ファイル                    | 置き場所           | 目的                             |
| --------------------------- | ------------------ | -------------------------------- |
| `robot_bridge.py`           | host PC            | Unitree SDK2を呼ぶFastAPI server |
| `requirements.txt`          | host PC            | FastAPI等の依存関係              |
| `unitree_bridge_client.py`  | NemoClaw sandbox   | OpenClawが実行するHTTP client    |
| `AGENTS_unitree_rules.md`   | NemoClaw workspace | OpenClawへの行動ルール           |
| `unitree-robot-bridge.yaml` | host PC            | NemoClaw network policy preset   |

---

## 6. Host側: Robot Bridgeを作る

### 6.1 `requirements.txt`

```txt
fastapi
uvicorn
pydantic
```

インストール:

```bash
pip install -r requirements.txt
```

---

### 6.2 `robot_bridge.py`

以下はPhase 1用の最小テンプレートです。  
最初はSDK呼び出し部分をコメントアウトした**dry-run**で疎通確認し、その後Unitree SDK2部分を有効化します。

```python
# robot_bridge.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import logging
from datetime import datetime

app = FastAPI(title="Unitree Robot Bridge - Phase 1")

logging.basicConfig(
    filename="robot_bridge.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ============================================================
# TODO: 実機接続時にUnitree SDK2の初期化を環境に合わせて有効化する
# ============================================================
# from unitree_sdk2py.core.channel import ChannelFactoryInitialize
# from unitree_sdk2py.go2.sport.sport_client import SportClient
#
# NETWORK_INTERFACE = "enp3s0"  # 実環境に合わせる
# ChannelFactoryInitialize(0, NETWORK_INTERFACE)
# sport_client = SportClient()
# sport_client.SetTimeout(10.0)
# sport_client.Init()

DRY_RUN = True

MAX_VX = 0.20
MAX_VY = 0.10
MAX_VYAW = 0.30
MAX_DURATION = 1.00
MIN_DURATION = 0.10


class RobotCommand(BaseModel):
    robot: str = "go2"
    command: str
    vx: float = 0.0
    vy: float = 0.0
    vyaw: float = 0.0
    duration: float = 0.5


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def log_event(event: str, payload: dict | None = None):
    logging.info({
        "time": datetime.now().isoformat(),
        "event": event,
        "payload": payload or {},
    })


def sdk_stop_move():
    if DRY_RUN:
        log_event("DRY_RUN_StopMove")
        return
    # sport_client.StopMove()


def sdk_balance_stand():
    if DRY_RUN:
        log_event("DRY_RUN_BalanceStand")
        return
    # sport_client.BalanceStand()


def sdk_move(vx: float, vy: float, vyaw: float):
    if DRY_RUN:
        log_event("DRY_RUN_Move", {"vx": vx, "vy": vy, "vyaw": vyaw})
        return
    # sport_client.Move(vx, vy, vyaw)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "unitree-robot-bridge",
        "phase": "1",
        "dry_run": DRY_RUN,
    }


@app.get("/robot/status")
def robot_status():
    # Phase 1ではまず接続状態の枠だけ返す。
    # 実機接続後、HighStateやbattery等の取得を追加する。
    return {
        "robot": "go2",
        "connected": not DRY_RUN,
        "dry_run": DRY_RUN,
        "safe_to_move": True,
        "allowed_commands": ["status", "stop", "balance_stand", "tiny_move"],
        "limits": {
            "vx": [-MAX_VX, MAX_VX],
            "vy": [-MAX_VY, MAX_VY],
            "vyaw": [-MAX_VYAW, MAX_VYAW],
            "duration": [MIN_DURATION, MAX_DURATION],
        },
    }


@app.post("/robot/stop")
def robot_stop():
    log_event("STOP_requested")
    sdk_stop_move()
    return {"ok": True, "executed": "StopMove", "dry_run": DRY_RUN}


@app.post("/robot/command")
def robot_command(cmd: RobotCommand):
    log_event("command_received", cmd.model_dump())

    if cmd.robot != "go2":
        raise HTTPException(status_code=400, detail="Only go2 is enabled in Phase 1")

    if cmd.command == "stop":
        sdk_stop_move()
        return {"ok": True, "executed": "StopMove", "dry_run": DRY_RUN}

    if cmd.command == "balance_stand":
        sdk_balance_stand()
        return {"ok": True, "executed": "BalanceStand", "dry_run": DRY_RUN}

    if cmd.command == "tiny_move":
        vx = clamp(cmd.vx, -MAX_VX, MAX_VX)
        vy = clamp(cmd.vy, -MAX_VY, MAX_VY)
        vyaw = clamp(cmd.vyaw, -MAX_VYAW, MAX_VYAW)
        duration = clamp(cmd.duration, MIN_DURATION, MAX_DURATION)

        try:
            log_event("tiny_move_start", {
                "vx": vx,
                "vy": vy,
                "vyaw": vyaw,
                "duration": duration,
            })
            sdk_move(vx, vy, vyaw)
            time.sleep(duration)
        finally:
            log_event("tiny_move_auto_stop")
            sdk_stop_move()

        return {
            "ok": True,
            "executed": "tiny_move",
            "vx": vx,
            "vy": vy,
            "vyaw": vyaw,
            "duration": duration,
            "auto_stop": True,
            "dry_run": DRY_RUN,
        }

    raise HTTPException(status_code=400, detail=f"Command not allowed in Phase 1: {cmd.command}")
```

---

### 6.3 Robot Bridgeを起動する

```bash
uvicorn robot_bridge:app --host 0.0.0.0 --port 50001
```

host PC上で確認:

```bash
curl http://127.0.0.1:50001/health
```

期待値:

```json
{
  "status": "ok",
  "service": "unitree-robot-bridge",
  "phase": "1",
  "dry_run": true
}
```

同じLAN内の別端末またはsandboxからアクセスするため、host PCのIPを確認します。

Linux例:

```bash
ip addr
```

macOS例:

```bash
ifconfig
```

Windows / WSL2例:

```powershell
ipconfig
```

以降では例として以下を使います。

```text
HOST_IP=192.168.1.50
ROBOT_BRIDGE_PORT=50001
```

---

## 7. NemoClaw側: Robot Bridgeだけ通信許可する

NemoClaw sandboxは、許可されたendpointだけへ通信できる設計にします。  
Phase 1では、OpenClawからRobot Bridge以外へロボット制御通信を出させません。

### 7.1 `unitree-robot-bridge.yaml` の例

> 注意: NemoClawのpolicy schemaはバージョンにより変わる可能性があります。以下は設計例です。実際の環境では、現在のNemoClaw docsと既存presetの書式に合わせて調整してください。

```yaml
preset:
  name: unitree-robot-bridge
  description: "Allow OpenClaw sandbox to call only the Unitree Robot Bridge"

network_policies:
  unitree_robot_bridge:
    name: unitree_robot_bridge
    endpoints:
      - host: "192.168.1.50"
        port: 50001
        protocol: rest
        enforcement: enforce
        rules:
          - allow:
              method: GET
              path: "/health"
          - allow:
              method: GET
              path: "/robot/status"
          - allow:
              method: POST
              path: "/robot/stop"
          - allow:
              method: POST
              path: "/robot/command"
    binaries:
      - path: /usr/bin/curl
      - path: /usr/bin/python3
```

`192.168.1.50` は実際のhost PC IPに変更します。

---

### 7.2 policyをdry-runする

```bash
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml --dry-run
```

問題なければ適用します。

```bash
nemoclaw my-assistant policy-add --from-file ./policy/unitree-robot-bridge.yaml
```

現在のpolicy確認:

```bash
nemoclaw my-assistant policy-list
nemoclaw my-assistant policy-explain
```

---

## 8. Sandbox側: OpenClawが呼ぶclient scriptを置く

OpenClawに長い`curl`を直接書かせるより、sandbox内に小さなclient scriptを置く方が安定します。

### 8.1 sandboxへ入る

```bash
nemoclaw my-assistant connect
```

---

### 8.2 `unitree_bridge_client.py`

```python
# unitree_bridge_client.py
import argparse
import json
import sys
import requests

BRIDGE_URL = "http://192.168.1.50:50001"  # host PC IPに変更


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def get(path: str):
    r = requests.get(f"{BRIDGE_URL}{path}", timeout=5)
    r.raise_for_status()
    print_json(r.json())


def post(path: str, payload: dict | None = None):
    r = requests.post(f"{BRIDGE_URL}{path}", json=payload or {}, timeout=5)
    r.raise_for_status()
    print_json(r.json())


def main():
    parser = argparse.ArgumentParser(description="Unitree Robot Bridge Client - Phase 1")
    parser.add_argument("command", choices=["health", "status", "stop", "balance_stand", "tiny_move"])
    parser.add_argument("--vx", type=float, default=0.0)
    parser.add_argument("--vy", type=float, default=0.0)
    parser.add_argument("--vyaw", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=0.5)
    args = parser.parse_args()

    try:
        if args.command == "health":
            get("/health")
            return

        if args.command == "status":
            get("/robot/status")
            return

        if args.command == "stop":
            post("/robot/stop")
            return

        if args.command == "balance_stand":
            post("/robot/command", {
                "robot": "go2",
                "command": "balance_stand",
            })
            return

        if args.command == "tiny_move":
            post("/robot/command", {
                "robot": "go2",
                "command": "tiny_move",
                "vx": args.vx,
                "vy": args.vy,
                "vyaw": args.vyaw,
                "duration": args.duration,
            })
            return

    except requests.RequestException as e:
        print_json({"ok": False, "error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### 8.3 sandbox内で疎通確認

```bash
python unitree_bridge_client.py health
python unitree_bridge_client.py status
python unitree_bridge_client.py stop
```

期待値:

```json
{
  "ok": true,
  "executed": "StopMove",
  "dry_run": true
}
```

`dry_run: true` のまま、まずOpenClawから呼び出せることを確認します。

---

## 9. OpenClaw側: AGENTS.mdにルールを書く

NemoClaw/OpenClawでは、OpenClawの行動ルールをworkspace fileとして管理します。  
Phase 1では、`AGENTS.md` にロボット制御ルールを明示します。

### 9.1 `AGENTS_unitree_rules.md`

````md
# Unitree Go2 Control Rules - Phase 1

You may control the Unitree Go2 only through the approved Robot Bridge client.

Allowed command forms:

```bash
python unitree_bridge_client.py health
python unitree_bridge_client.py status
python unitree_bridge_client.py stop
python unitree_bridge_client.py balance_stand
python unitree_bridge_client.py tiny_move --vx 0.10 --duration 0.5
```
````

Hard rules:

1. Never run Unitree SDK scripts directly.
2. Never import Unitree SDK directly.
3. Never send low-level motor commands.
4. Never execute flips, jumps, dances, handstands, continuous walking, or trajectory following.
5. Always ask for human confirmation before any physical motion.
6. Before motion, check status if it has not been checked in this session.
7. For tiny movement, use conservative defaults: `--vx 0.10 --duration 0.5`.
8. Never exceed `--vx 0.15` or `--duration 1.0` from OpenClaw side.
9. If the bridge response does not include `auto_stop: true`, immediately call `python unitree_bridge_client.py stop`.
10. If the user asks for unsafe motion, refuse and offer `status` or `stop` instead.

Recommended workflow:

1. Run `python unitree_bridge_client.py status`.
2. Explain the planned command.
3. Ask for explicit human confirmation.
4. Run the approved command.
5. Report the bridge response.

````

---

### 9.2 AGENTS.mdへ反映する

sandbox内で、OpenClaw workspaceの `AGENTS.md` に追記します。

例:

```bash
cat AGENTS_unitree_rules.md >> /sandbox/.openclaw/workspace/AGENTS.md
````

環境によってworkspace pathが異なる場合は、以下で確認します。

```bash
find /sandbox -name AGENTS.md 2>/dev/null
```

---

## 10. OpenClaw TUIから実行する

sandbox内でOpenClaw TUIを起動します。

```bash
openclaw tui
```

---

### Demo 1: Health check

OpenClawに入力:

```text
Robot Bridgeのhealth checkをしてください。Robot Bridge clientだけを使ってください。
```

OpenClawが実行すべきコマンド:

```bash
python unitree_bridge_client.py health
```

---

### Demo 2: Status only

OpenClawに入力:

```text
Go2の状態を確認してください。まだ動かさないでください。
```

OpenClawが実行すべきコマンド:

```bash
python unitree_bridge_client.py status
```

---

### Demo 3: Stop only

OpenClawに入力:

```text
Go2にStopMoveを送ってください。
```

OpenClawが実行すべきコマンド:

```bash
python unitree_bridge_client.py stop
```

---

### Demo 4: Tiny forward, dry-run

OpenClawに入力:

```text
Go2を0.10 m/sで0.5秒だけ前進させるdry-runをしてください。実行前に内容を説明してください。
```

OpenClawが説明すべき内容:

```text
実行予定:
python unitree_bridge_client.py tiny_move --vx 0.10 --duration 0.5
Bridge側でduration後にStopMoveされます。
```

人間が確認した後、OpenClawが実行:

```bash
python unitree_bridge_client.py tiny_move --vx 0.10 --duration 0.5
```

期待値:

```json
{
  "ok": true,
  "executed": "tiny_move",
  "vx": 0.1,
  "vy": 0.0,
  "vyaw": 0.0,
  "duration": 0.5,
  "auto_stop": true,
  "dry_run": true
}
```

---

## 11. 実機接続へ切り替える手順

ここまでは `DRY_RUN = True` で進めます。  
実機接続前に、以下を確認します。

```text
[ ] Go2の通信ネットワークが設定済み
[ ] Unitree SDK2 Pythonのサンプルがhost PC上で動作する
[ ] high-level control modeであることを確認済み
[ ] 純正リモコンまたはE-stop手段がある
[ ] 周囲が安全
[ ] Robot Bridgeの /robot/stop が実行できる
[ ] OpenClawから /robot/stop を呼べる
[ ] OpenClawから tiny_move dry-run が成功する
```

実機接続時は、`robot_bridge.py` の以下を変更します。

```python
DRY_RUN = False
```

そしてUnitree SDK2初期化部分を環境に合わせて有効化します。

```python
# from unitree_sdk2py.core.channel import ChannelFactoryInitialize
# from unitree_sdk2py.go2.sport.sport_client import SportClient
#
# NETWORK_INTERFACE = "enp3s0"
# ChannelFactoryInitialize(0, NETWORK_INTERFACE)
# sport_client = SportClient()
# sport_client.SetTimeout(10.0)
# sport_client.Init()
```

SDK初期化の正確なimport名・network interface名・サンプル実行方法は、利用しているUnitree SDK2 Pythonのバージョンに合わせて確認します。

---

## 12. 実機での最初の実行順

実機では、いきなり `tiny_move` しません。  
以下の順番で確認します。

### 12.1 Bridge health

```bash
python unitree_bridge_client.py health
```

### 12.2 Go2 status

```bash
python unitree_bridge_client.py status
```

### 12.3 StopMove

```bash
python unitree_bridge_client.py stop
```

### 12.4 BalanceStand

```bash
python unitree_bridge_client.py balance_stand
```

### 12.5 Tiny move

最初は0.05 m/s、0.3秒程度に落としてもよいです。

```bash
python unitree_bridge_client.py tiny_move --vx 0.05 --duration 0.3
```

問題なければ、Phase 1標準値にします。

```bash
python unitree_bridge_client.py tiny_move --vx 0.10 --duration 0.5
```

---

## 13. ログ確認

### 13.1 Robot Bridge log

host PCで確認します。

```bash
tail -f robot_bridge.log
```

確認したいイベント:

```text
command_received
tiny_move_start
tiny_move_auto_stop
DRY_RUN_StopMove または StopMove
```

---

### 13.2 NemoClaw / OpenClaw log

host側で確認します。

```bash
nemoclaw my-assistant logs --follow
```

確認したい内容:

```text
OpenClawがどのコマンドを実行したか
network policyで拒否された通信がないか
OpenShellが未許可通信を止めていないか
```

---

## 14. トラブルシュート

### 14.1 sandboxからBridgeに接続できない

sandbox内:

```bash
curl http://192.168.1.50:50001/health
```

確認項目:

```text
[ ] Robot Bridgeが --host 0.0.0.0 で起動している
[ ] HOST_IPが正しい
[ ] firewallがport 50001を塞いでいない
[ ] NemoClaw policyでHOST_IP:50001を許可している
[ ] OpenShell TUIで通信がブロックされていない
```

---

### 14.2 OpenClawが勝手に別コマンドを実行しようとする

対策:

1. `AGENTS.md` のルールをより強くする
2. `unitree_bridge_client.py` 以外を使わせない
3. NemoClaw network policyでRobot Bridge以外を許可しない
4. Robot Bridge側で未知commandを拒否する

Bridge側で拒否されるため、OpenClawが間違っても実機側に危険commandは通らない設計にします。

---

### 14.3 `tiny_move` 後に止まらない

これはPhase 1で最も危険な失敗です。

即時対応:

```bash
python unitree_bridge_client.py stop
```

または純正リモコン・E-stopで停止します。

設計確認:

```python
try:
    sdk_move(vx, vy, vyaw)
    time.sleep(duration)
finally:
    sdk_stop_move()
```

`finally` が入っていない実装はPhase 1では不可です。

---

## 15. Phase 1の成功条件

以下をすべて満たせばPhase 1完了です。

```text
[ ] Robot Bridgeがhost PC上で起動する
[ ] /health が返る
[ ] /robot/status が返る
[ ] /robot/stop が返る
[ ] /robot/command tiny_move がdry-runで成功する
[ ] NemoClaw sandboxからRobot BridgeへHTTPアクセスできる
[ ] OpenClawが unitree_bridge_client.py 経由でstatusを呼べる
[ ] OpenClawが unitree_bridge_client.py 経由でstopを呼べる
[ ] OpenClawが実行前確認を行う
[ ] OpenClawが tiny_move を1回だけ呼べる
[ ] Bridge側でduration後にStopMoveが保証される
[ ] Robot Bridge logに全commandが残る
[ ] NemoClaw/OpenClaw logで実行履歴を追える
```

---

## 16. Phase 1のデモ台本

### タイトル

```text
Natural Language to Safe Unitree High-level Command
```

### デモ流れ

1. Robot Bridgeを起動する
2. NemoClaw sandboxからhealth checkする
3. OpenClawを起動する
4. OpenClawに「Go2の状態を確認して」と依頼する
5. OpenClawに「Go2を停止して」と依頼する
6. OpenClawに「Go2を少しだけ前に出して」と依頼する
7. OpenClawが実行内容を説明し、人間確認を求める
8. 人間が承認する
9. OpenClawが `unitree_bridge_client.py tiny_move --vx 0.10 --duration 0.5` を実行する
10. Robot Bridgeが `Move()` → `StopMove()` を実行する
11. ログを表示する

### 見せ場

自然言語:

```text
Go2を少しだけ前に出して。
```

OpenClawの解釈:

```bash
python unitree_bridge_client.py tiny_move --vx 0.10 --duration 0.5
```

Robot Bridgeの安全実行:

```text
Move(0.10, 0.0, 0.0)
wait 0.5 sec
StopMove()
```

---

## 17. Phase 2への拡張案

Phase 1が成功したら、次は以下を検討します。

| Phase 2候補         | 内容                                          |
| ------------------- | --------------------------------------------- |
| richer status       | battery、mode、body height、error stateを取得 |
| command approval UI | 実行前承認をWeb UI化                          |
| skill化             | OpenClaw用の専用skill/pluginとして整理        |
| Go2 gesture demo    | short turn、look-like motion、sit/rise sit    |
| G1 bonus demo       | `WaveHand()` など歩行しないHigh-level motion  |
| ROS2 bridge         | Robot Bridgeの裏側をROS2 action/service化     |
| safety monitor      | battery/姿勢/距離/非常停止状態を監視          |

Phase 2でも、OpenClawからSDKを直接触らせない方針は維持します。

---

## 18. 参考資料

- NVIDIA NemoClaw Documentation  
  https://docs.nvidia.com/nemoclaw/

- NemoClaw Network Policies  
  https://docs.nvidia.com/nemoclaw/latest/reference/network-policies.html

- NemoClaw Workspace Files  
  https://docs.nvidia.com/nemoclaw/latest/workspace/workspace-files.html

- NemoClaw CLI Commands  
  https://docs.nvidia.com/nemoclaw/latest/reference/commands.html

- Unitree SDK2  
  https://github.com/unitreerobotics/unitree_sdk2

- Unitree SDK2 Python  
  https://github.com/unitreerobotics/unitree_sdk2_python

- Unitree Go2 Sport Client Header  
  https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/go2/sport/sport_client.hpp

- Unitree High-level Sports Service Interface  
  https://support.unitree.com/home/en/developer/sports_services

---

## 19. このPhaseの結論

Phase 1では、OpenClawにロボットを「自由に操作」させるのではありません。

OpenClawには、自然言語から安全な高レベルコマンドを選ばせるだけです。  
実際の安全制限・実行時間・StopMove保証・危険command拒否は、すべてRobot Bridge側で強制します。

最小構成は次です。

```text
OpenClaw
  ↓
unitree_bridge_client.py
  ↓ HTTP
Robot Bridge
  ↓ Unitree SDK2 High-level API
Go2
```

Phase 1の成功基準は、**自然言語からGo2の小さいHigh-level motionを1回だけ安全に呼び出せること**です。
