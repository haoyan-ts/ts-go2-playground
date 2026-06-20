# Go2 Gesture Control Demo

WebカメラとMediaPipeを使ってUnitree Go2をジェスチャー操作するデモです。

## 動作環境

- Ubuntu 22.04
- Pixi
- Go2とPC間：有線LAN直接接続

## セットアップ

### 1. Pixiのインストール

Pixiを未導入の場合は公式手順でインストールしてください。

- https://pixi.sh/latest/

### 2. 依存ライブラリのインストール

プロジェクトルートで以下を実行します。

```bash
pixi install
```

最新の MediaPipe は Tasks API を使用するため、初回実行時に hand landmarker の
モデルファイルが `models/hand_landmarker.task` へ自動ダウンロードされます。

プロジェクトのソースコードは `src/` ディレクトリに配置されています。

### 3. unitree_sdk2_python のインストール

Go2へ実際にコマンド送信する場合のみ必要です。

```bash
pixi run install-unitree-sdk
```

### 4. ネットワーク設定

PCのイーサネットアダプタを以下の固定IPに設定します。

| 項目             | 値              |
| ---------------- | --------------- |
| IPアドレス       | 192.168.123.100 |
| サブネットマスク | 255.255.255.0   |
| ゲートウェイ     | （不要）        |

Go2のIPは `192.168.123.161` です。接続確認：

```bash
ping 192.168.123.161
```

## 実行方法

### Go2に接続して実行

```bash
pixi run run
```

`eth0` はお使いのイーサネットインターフェース名に合わせてください（`ip link` で確認）。

別のインターフェース名を使う場合は以下のように直接指定してください。

```bash
pixi run python -m src --interface <your_interface>
```

### カメラと認識だけテスト（Go2不要）

```bash
pixi run dry-run
```

`dry-run` では `unitree_sdk2_python` は不要です。別モデルを使う場合は
以下のように `--model` で `.task` ファイルを指定できます。

```bash
pixi run python -m src --dry-run --model path/to/hand_landmarker.task
```

## ジェスチャー一覧

| ジェスチャー          | Go2のアクション             |
| --------------------- | --------------------------- |
| パー（5本指を開く）   | StandUp（立ち上がり）       |
| グー（握り拳）        | StandDown（伏せ）           |
| サムズアップ          | Dance（ダンス）             |
| ピース（V字）         | Hello（お辞儀）             |
| 指差し（人差し指1本） | RecoveryStand（起き上がり） |

## 操作上の注意

- カメラとの距離は 50cm〜150cm 程度が認識精度のベストレンジです
- ジェスチャーは約0.5秒間保持するとコマンドが実行されます
- コマンド実行後は2秒のクールダウンがあります
- 終了は `q` キーを押してください
