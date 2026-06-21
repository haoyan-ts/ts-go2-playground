# Go2 Playground

Umbrella monorepo for **Unitree Go2** development — gesture control demo, Robot Bridge
foundation (safe REST API for Go2), and sandbox-side client.

## Packages

| Package                                                            | Description                                                                                   |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| [`packages/go2-gesture-control/`](./packages/go2-gesture-control/) | Webcam + MediaPipe gesture control demo for Go2                                               |
| [`packages/go2-robot-bridge/`](./packages/go2-robot-bridge/)       | Host-side FastAPI server — action library, safety supervisor, mission supervisor, SDK adapter |
| [`packages/go2-bridge-client/`](./packages/go2-bridge-client/)     | Sandbox-side CLI to talk to the Robot Bridge (no SDK dependency)                              |

## Quick Start

### Prerequisites

- [pixi](https://pixi.sh/latest/) package manager
- Python 3.10 or 3.11
- Ubuntu 22.04+ (for real Go2 control; dry mode works on any OS)

### Install

```bash
pixi install
```

### Run the bridge server (dry mode — no robot needed)

```bash
pixi run bridge-server
```

Open a second terminal:

```bash
pixi run python -m go2_bridge_client health
```

### Install Unitree SDK (for real Go2)

```bash
pixi run install-unitree-sdk
```

### Network setup (for real Go2)

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

### Run the bridge server for simulator targets

Robot Bridge can target Go2 models inside Isaac Sim or MuJoCo without exposing simulator APIs to agents or sandbox clients. Start the simulator-side HTTP control server first, then run one of:

```bash
pixi run bridge-server-isaac
pixi run bridge-server-mujoco
```

The default Isaac Sim control URL is `http://127.0.0.1:51000`; override it with `ISAAC_SIM_URL`. The default MuJoCo control URL is `http://127.0.0.1:52000`; override it with `MUJOCO_URL`. Simulator sidecars expose `/status`, `/stop`, and `/controller-command`; Robot Bridge still listens on `127.0.0.1:50001` and returns both `dry_mode` and `control_target` in health/status responses.

### Run gesture demo (dry mode)

```bash
pixi run dry-run
```

## Pixi Tasks

| Task                           | Purpose                                                       |
| ------------------------------ | ------------------------------------------------------------- |
| `pixi run bridge-server`       | Start the Robot Bridge FastAPI server on `127.0.0.1:50001`    |
| `pixi run bridge-server-isaac` | Start Robot Bridge with `BRIDGE_TARGET=isaac_sim`             |
| `pixi run bridge-server-mujoco` | Start Robot Bridge with `BRIDGE_TARGET=mujoco`                |
| `pixi run bridge-client`       | Run the sandbox client (requires subcommand)                  |
| `pixi run dry-run`             | Gesture control demo in dry mode (camera + MediaPipe, no Go2) |
| `pixi run run`                 | Gesture control demo with real Go2                            |
| `pixi run install-unitree-sdk` | Install Unitree SDK2 Python from GitHub                       |

## Documentation

| Document                                                                                                             | Content                                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [`docs/tutorials/unitree-go2-foundation/basics.md`](./docs/tutorials/unitree-go2-foundation/basics.md)               | **Foundation Tutorial** (English, Go2-only) — 3-phase learning path: SDK install, action library & safety, missions & supervision |
| [`docs/tutorials/nemo-claw-openclaw/basics.md`](./docs/tutorials/nemo-claw-openclaw/basics.md)                       | NemoClaw + OpenClaw basics                                                                                                        |
| [`docs/tutorials/nemo-claw-openclaw/demo-how-to.md`](./docs/tutorials/nemo-claw-openclaw/demo-how-to.md)             | **Demo How-to** — NVIDIA Agent AI x Robotics向けGo2デモを環境整備から最終検証まで通す手順                                         |
| [`docs/tutorials/nemo-claw-openclaw/unitree-application/`](./docs/tutorials/nemo-claw-openclaw/unitree-application/) | OpenClaw application layer phases (builds on the foundation packages)                                                             |

See [`docs/README.md`](./docs/README.md) for the full documentation index.
