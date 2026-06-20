# How-to: NVIDIA Agent AI x Robotics向けGo2デモ実行手順

Version: 2026-06-20  
Scope: NemoClaw / OpenClaw + Unitree Go2 + Robot Bridge  
Goal: 展示デモを、最初の環境整備から最後の検証まで一通り再現できる状態にする。

---

## 0. デモの位置づけ

このhow-toは、NVIDIA展示会「Agent AI x Robotics」における出展デモの一つとして、OpenClaw agentからUnitree Go2を安全に操作する流れを準備するための手順書である。

このデモで見せること:

```text
自然言語指示
→ OpenClawが許可済みAction/Missionを選ぶ
→ dry-runで動作内容を説明
→ 人間が確認
→ Robot Bridgeが安全制限を強制
→ Go2が短い動作を実行
→ ログと結果を確認する
```

このデモで見せないこと:

- OpenClawからUnitree SDKを直接呼ぶこと
- LLMに自由な速度、時間、waypointを生成させること
- 長時間の自律移動
- low-level motor control
- 人間確認なしの物理motion実行

---

## 1. 全体構成

```text
[User]
  |
  | Natural language
  v
[OpenClaw inside NemoClaw sandbox]
  |
  | python -m go2_bridge_client ...
  v
[Go2 Bridge Client]
  |
  | HTTP / JSON
  v
[Robot Bridge on host PC]
  |
  | Action Library / Mission Library / Safety Supervisor
  v
[Unitree SDK2 Python]
  |
  v
[Unitree Go2]
```

展示で強調する設計原則は、**AgentにSDKを直接渡さず、Robot Bridgeを安全ゲートにする**ことである。

---

## 2. 事前に決めること

| Item                  | 推奨値                    |
| --------------------- | ------------------------- |
| NemoClaw sandbox name | `my-claw`                 |
| Bridge URL            | `http://127.0.0.1:50001`  |
| First run mode        | dry mode                  |
| Real robot target     | Unitree Go2               |
| OpenClawが使う操作面  | Action / Mission API only |
| Human confirmation    | required for motion       |

展示直前まではdry modeで手順を固め、実機接続は最後に切り替える。

---

## 3. Host PCの環境整備

### 3.1 OSとランタイム

推奨環境:

| Item              | Requirement                          |
| ----------------- | ------------------------------------ |
| OS                | Ubuntu 22.04+ or Windows WSL2 Ubuntu |
| Python            | 3.10 or 3.11                         |
| Package manager   | pixi                                 |
| Container runtime | Docker / Docker Desktop              |
| Memory            | 16 GB recommended                    |
| Disk              | 40 GB recommended                    |

確認:

```bash
python --version
docker --version
docker ps
pixi --version
```

Windowsで実施する場合も、NemoClaw / OpenClawと実機操作はWSL2 Ubuntu側で揃える方が切り分けしやすい。

### 3.2 API key

NemoClaw onboardingで使う推論providerのAPI keyを用意する。

例: NVIDIA endpoint

```bash
export NVIDIA_API_KEY="your_api_key_here"
```

例: OpenAI

```bash
export OPENAI_API_KEY="your_api_key_here"
```

API keyはGitに保存しない。

---

## 4. このrepoのセットアップ

repoを取得して、pixi環境を作る。

```bash
git clone <this-repo-url>
cd ts-go2-playground
pixi install
```

dry modeでRobot Bridgeを起動する。

```bash
pixi run bridge-server
```

別ターミナルでhealth checkを実行する。

```bash
pixi run python -m go2_bridge_client health
```

期待結果:

```json
{
  "status": "ok",
  "dry_mode": true
}
```

Action一覧を確認する。

```bash
pixi run python -m go2_bridge_client list
```

Mission一覧を確認する。

```bash
pixi run python -m go2_bridge_client missions
```

---

## 5. NemoClaw / OpenClawの準備

NemoClawをinstallし、OpenClaw sandboxを作る。

```bash
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

onboardingで選ぶ内容:

| Prompt         | Value                               |
| -------------- | ----------------------------------- |
| Agent          | OpenClaw                            |
| Provider       | NVIDIA Endpoints or chosen provider |
| Sandbox name   | `my-claw`                           |
| Web Search     | Off for first run                   |
| Messaging      | None for first run                  |
| Network policy | default first, then demo policy     |

状態確認:

```bash
nemoclaw list
nemoclaw my-claw status
nemoclaw my-claw doctor
```

dashboardを開く。

```bash
nemoclaw my-claw dashboard-url --quiet
```

OpenClaw TUIを起動する。

```bash
nemoclaw my-claw connect
openclaw tui
```

---

## 6. SandboxからBridgeを呼ぶ準備

OpenClaw sandboxからhost側Robot Bridgeだけを呼ぶ構成にする。

### 6.1 Client配置

展示では、sandbox内で次のCLIが使える状態にする。

```bash
python -m go2_bridge_client health
python -m go2_bridge_client list
python -m go2_bridge_client dry-run <action-name>
python -m go2_bridge_client run <action-name>
python -m go2_bridge_client missions
python -m go2_bridge_client mission-dry-run <mission-name>
python -m go2_bridge_client mission-run <mission-name>
python -m go2_bridge_client logs
```

repoをsandboxにmount / copyする方式は展示環境に合わせて決める。最小構成では、sandboxから`go2_bridge_client` packageを使えるようにし、`BRIDGE_URL`をhostのBridge URLに向ける。

```bash
export BRIDGE_URL="http://127.0.0.1:50001"
```

NemoClaw環境でhost loopbackの扱いが異なる場合は、sandboxから見えるhost addressに置き換える。

### 6.2 Network policy

展示では、sandboxからRobot Bridge以外へ不要な通信をさせない。

このrepoにはpolicy例がある。

```text
policy/unitree-robot-bridge.yaml
```

方針:

- allow: Robot Bridge HTTP API
- allow: DNS if required
- deny: other outbound
- deny: inbound

実際の適用コマンドはNemoClawのpolicy仕様に合わせて確認する。

---

## 7. OpenClawに渡す操作ルール

OpenClawには、次のルールを明示する。

```text
You are controlling a Unitree Go2 demo only through the Robot Bridge CLI.
Do not import or call Unitree SDK directly.
Do not create freeform robot motion parameters.
Use only listed actions or missions.
Always run dry-run before physical execution.
Ask for human confirmation before motion.
Use stop immediately if the user asks to stop or if output looks unsafe.
After execution, summarize logs and final status.
```

展示で使う自然言語prompt例:

```text
Go2に短い挨拶デモをさせて。まず実行内容を確認してから進めて。
```

```text
展示エリア向けの短いmissionをdry-runして、安全条件と実行手順を説明して。
```

```text
直近ログを確認して、実行結果と安全上の注意点をまとめて。
```

---

## 8. Dry modeでの展示リハーサル

Host側でBridgeを起動する。

```bash
pixi run bridge-server
```

Hostまたはsandbox側から確認する。

```bash
python -m go2_bridge_client health
python -m go2_bridge_client list
python -m go2_bridge_client missions
```

Action dry-run:

```bash
python -m go2_bridge_client dry-run <action-name>
```

Action execute:

```bash
python -m go2_bridge_client run <action-name>
```

Mission dry-run:

```bash
python -m go2_bridge_client mission-dry-run <mission-name>
```

Mission execute:

```bash
python -m go2_bridge_client mission-run <mission-name>
```

ログ確認:

```bash
python -m go2_bridge_client logs
```

dry modeの完了条件:

- [ ] Bridge health checkが通る。
- [ ] Action一覧が表示される。
- [ ] Mission一覧が表示される。
- [ ] dry-runでsteps、risk、confirmationが説明される。
- [ ] confirmationなしのmotion実行が拒否される。
- [ ] confirmationありの実行が完了する。
- [ ] logsで実行履歴を確認できる。
- [ ] OpenClawが結果を自然言語で説明できる。

---

## 9. 実機Go2に切り替える

実機切り替えは、dry modeの完了条件を満たしてから行う。

### 9.1 Unitree SDK2 Python

```bash
pixi run install-unitree-sdk
```

### 9.2 Network setup

代表的なGo2 network設定:

| Item        | Value             |
| ----------- | ----------------- |
| PC wired IP | `192.168.123.100` |
| Subnet mask | `255.255.255.0`   |
| Go2 IP      | `192.168.123.161` |

```bash
sudo ip addr add 192.168.123.100/24 dev eth0
sudo ip link set eth0 up
ping 192.168.123.161
```

### 9.3 Safety setup

実機実行前に確認する。

- [ ] Go2の周囲1.5m以上を空ける。
- [ ] 床面が平らで滑りにくい。
- [ ] ケーブル、人、机、展示物が近くにない。
- [ ] 操作者が物理停止手段または純正リモコンを持つ。
- [ ] 最初は`status`、`stop`、`balance_stand`だけを確認する。
- [ ] 初回motionは短距離・低速Actionだけを使う。

### 9.4 Real mode起動

現状の`pixi run bridge-server`はdry mode appを起動する。実機用には、`UnitreeGo2Adapter(dry_mode=False, network_interface="eth0")`を渡して`create_app()`する起動スクリプトを用意する。

展示準備タスク:

- [ ] real mode用Bridge起動コマンドを追加する。
- [ ] network interfaceを環境変数で指定できるようにする。
- [ ] 実機用手順をdry mode手順と分離する。

---

## 10. 展示本番の実行順

1. Host PC、Go2、network、NemoClaw sandboxを起動する。
2. `pixi run bridge-server`または実機用Bridgeを起動する。
3. OpenClaw dashboard / TUIを開く。
4. `health`、`status`、`list`、`missions`を確認する。
5. 来場者の自然言語指示を受ける。
6. OpenClawがActionまたはMissionを選ぶ。
7. OpenClawがdry-runを実行し、動作内容とriskを説明する。
8. 操作者が周囲安全を確認する。
9. 人間確認後にexecuteする。
10. 実行後、`status`と`logs`を確認する。
11. OpenClawが結果を説明する。
12. 必要なら`stop`を実行して終了状態に戻す。

---

## 11. 最終検証チェックリスト

展示前に、以下をすべて確認する。

### Repository

- [ ] `pixi install`が成功する。
- [ ] `pixi run bridge-server`が起動する。
- [ ] `pixi run python -m go2_bridge_client health`が成功する。
- [ ] `pixi run python -m go2_bridge_client list`がActionを返す。
- [ ] `pixi run python -m go2_bridge_client missions`がMissionを返す。

### OpenClaw

- [ ] `nemoclaw list`にsandboxが表示される。
- [ ] `nemoclaw my-claw doctor`にblocking failureがない。
- [ ] OpenClaw TUIまたはdashboardが使える。
- [ ] OpenClawからBridge clientを呼べる。
- [ ] OpenClawがSDK直接呼び出しを提案しない。

### Safety

- [ ] OpenClawが必ずdry-runを先に実行する。
- [ ] confirmationなしのmotion実行が拒否される。
- [ ] Safety Supervisorの速度・時間制限が有効である。
- [ ] move後にStopMoveが呼ばれる。
- [ ] stop commandがいつでも使える。

### Demo Story

- [ ] 30秒版の説明がある。
- [ ] 3分版の説明がある。
- [ ] dry mode fallbackがある。
- [ ] 実機が使えない場合の画面デモ手順がある。
- [ ] ログを見せながら安全設計を説明できる。

---

## 12. 残タスク

このhow-toを完全な展示運用手順にするため、次を実装または追記する。

- [ ] real mode用Bridge起動taskを`pixi.toml`に追加する。
- [ ] sandboxへのclient配置方法をNemoClawの実環境に合わせて確定する。
- [ ] NemoClaw network policyの適用コマンドを確認して追記する。
- [ ] OpenClaw用の展示ルールファイルを追加する。
- [ ] NVIDIA Skillsとして出す場合のSkill manifestを追加する。
- [ ] Hermesを展示対象に含めるか決める。
- [ ] Jetsonで実行する場合の差分手順を追加する。
