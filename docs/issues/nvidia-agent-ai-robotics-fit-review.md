# 課題: NVIDIA Agent AI x Robotics展示向けGo2デモ準備レビュー

作成日: 2026-06-20

## 背景

NVIDIAの展示会テーマは「Agent AI x Robotics」。その中で、このrepoをNemoClaw / OpenClawなどのAgent toolを用いたロボット学習・開発デモの一つとして出展することを検討している。

参考情報:

- NemoClaw: https://github.com/NVIDIA/NemoClaw
- QuickStart with OpenClaw: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/quickstart
- QuickStart with Hermes: https://docs.nvidia.com/nemoclaw/latest/user-guide/hermes/get-started/quickstart
- Jetson troubleshooting: https://docs.nvidia.com/nemoclaw/latest/user-guide/hermes/reference/troubleshooting#installer-fails-on-nvidia-jetson
- NVIDIA Skills: https://build.nvidia.com/skills

## レビュー結論

このrepoは、NVIDIAの「Agent AI x Robotics」展示に出展するデモの一つとして条件付きでふさわしい。

特に、ロボット学習そのものを主役にするよりも、NemoClaw / OpenClawを使ったAgentによる安全なロボット開発・操作デモとして出す方が、このrepoの現状に合っている。

推奨する出展デモの位置づけ:

> NVIDIA展示会「Agent AI x Robotics」における出展デモの一つ。NemoClaw / OpenClawを用いて、自然言語AgentがUnitree Go2を安全API経由で操作するロボット開発デモ。LLMにSDKを直接触らせず、dry-run、人間確認、Safety Supervisor、Mission Supervisorを通してAgentic Roboticsの安全設計を見せる。

## 適合している点

- `README.md`でUnitree Go2向けのRobot Bridge、gesture demo、sandbox-side clientが整理されている。
- `docs/tutorials/nemo-claw-openclaw/basics.md`にNemoClaw + OpenClawの導入チュートリアルがある。
- `docs/tutorials/nemo-claw-openclaw/unitree-application/`に、OpenClawからGo2を安全に扱う段階的な構成がある。
- `packages/go2-robot-bridge/src/go2_robot_bridge/app.py`にFastAPIのRobot Bridgeがあり、`/actions`、`/missions`、dry-run、execute、logsなど展示向きのAPIがある。
- `packages/go2-bridge-client/src/go2_bridge_client/__main__.py`にsandbox側CLIがあり、OpenClawからHTTP経由でBridgeを叩く構成になっている。
- `policy/unitree-robot-bridge.yaml`でsandboxからRobot Bridgeだけに通信を絞る思想が入っている。

## 展示ストーリー案

```text
ユーザーが自然言語で指示
→ OpenClawが許可済みAction/Missionを選ぶ
→ dry-runで内容を説明
→ 人間が確認
→ Robot Bridgeが安全制限を強制
→ Unitree Go2が短い動作を実行
→ ログと結果をOpenClawが説明
```

## 不足・リスク

1. Hermes対応が薄い
   - 既存チュートリアルはOpenClaw中心で、Hermes QuickStartとの接続はまだ弱い。

2. NVIDIA Skillsとの統合が未整理
   - `build.nvidia.com/skills`向けのAgent Skill形式、manifest、呼び出し例、パッケージ化方針がまだ明確ではない。

3. Jetson対応が未検証
   - READMEはUbuntu 22.04+とdry modeを前提にしており、Jetson troubleshootingを踏まえた手順、依存関係、known issuesが不足している。

4. ロボット学習を前面に出すには弱い
   - 現状は学習・訓練・シミュレーション・データ収集・モデル改善よりも、Agentによる安全なロボット制御/開発支援に寄っている。
   - 出展デモの説明でrobot learningを前面に出す場合は、Isaac Sim、データ収集、policy評価、模倣学習/RLなどの文脈追加が必要。

5. 安全面の実装整理が必要
   - ドキュメントではPhase 1で`Dance1`などを禁止しているが、実装側の直通コマンドには`dance1`が含まれている。
   - 展示ではOpenClawに直通`/robot/command`を使わせず、Action Library / Mission Library経由に限定する方が安全。

## 対応タスク

- [ ] 展示名・説明を「robot learning」ではなく「Agentic robot control / safe robotics development / OpenClaw tool-use demo」に寄せる。
- [ ] OpenClawから呼べる操作面をAction Library / Mission Library経由に限定する。
- [ ] `/robot/command`の展示時公開範囲を見直し、危険または派手なmotionを直通許可しない。
- [ ] NVIDIA Skills向けのSkill定義、manifest、実行例を追加するか、対象外であることを明記する。
- [ ] Hermes連携を展示対象に含めるか判断し、含める場合はQuickStartとの差分手順を書く。
- [ ] Jetsonでのインストール・実行手順とtroubleshootingを追加する。
- [ ] Robot learning展示に寄せる場合は、学習/評価/シミュレーションの追加ストーリーを設計する。

## 完了条件

- 展示向けREADMEまたはチュートリアルに、上記の正確な位置づけが反映されている。
- OpenClawが呼び出すAPI/CLIが安全なAction/Mission経由に限定されている。
- dry-run、人間確認、Safety Supervisor、Mission Supervisor、ログ確認までの一連のデモ手順が再現可能である。
- Jetson、Hermes、NVIDIA Skillsを展示対象に含めるかどうかが明記されている。
