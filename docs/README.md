# Documentation Index

Project documentation for the Go2 Playground umbrella monorepo.

## Packages

| Package                                                             | Description                                                                                   |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| [`packages/go2-gesture-control/`](../packages/go2-gesture-control/) | Webcam + MediaPipe gesture control demo for Go2                                               |
| [`packages/go2-robot-bridge/`](../packages/go2-robot-bridge/)       | Host-side FastAPI server — action library, safety supervisor, mission supervisor, SDK adapter |
| [`packages/go2-bridge-client/`](../packages/go2-bridge-client/)     | Sandbox-side CLI to talk to the Robot Bridge (no SDK dependency)                              |

## Tutorials

### Unitree Go2 Foundation (English, Go2-only)

Foundation tutorial for building and using the Robot Bridge packages from scratch.

| Document                                                                                     | Content                                                                                                                                                         |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`tutorials/unitree-go2-foundation/basics.md`](./tutorials/unitree-go2-foundation/basics.md) | **Foundation Tutorial** — 3-phase learning path: SDK install & first connection (Phase 1), action library & safety (Phase 2), missions & supervision (Phase 3). |

### NemoClaw / OpenClaw

Tutorials for using NemoClaw with OpenClaw.

| Document                                                                                       | Content                                                                                                                     |
| ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| [`tutorials/nemo-claw-openclaw/basics.md`](./tutorials/nemo-claw-openclaw/basics.md)           | NemoClaw + OpenClaw basic tutorial (Phase 1–3). Covers install, sandbox operation, and custom configuration.                |
| [`tutorials/nemo-claw-openclaw/demo-how-to.md`](./tutorials/nemo-claw-openclaw/demo-how-to.md) | **Demo How-to** — end-to-end NVIDIA Agent AI x Robotics Go2 demo setup, rehearsal, real-robot switch, and final validation. |

#### Unitree Application (OpenClaw layer)

OpenClaw application phases for Go2 control, built on top of the foundation packages.

| Document                                                                                                                                                           | Content                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| [`tutorials/nemo-claw-openclaw/unitree-application/phase-1-single-call.md`](./tutorials/nemo-claw-openclaw/unitree-application/phase-1-single-call.md)             | **Phase 1** — Single safe SDK call through Robot Bridge.                        |
| [`tutorials/nemo-claw-openclaw/unitree-application/phase-2-action-sequence.md`](./tutorials/nemo-claw-openclaw/unitree-application/phase-2-action-sequence.md)     | **Phase 2** — Safe Action Library with dry-run → confirm → execute.             |
| [`tutorials/nemo-claw-openclaw/unitree-application/phase-3-mission-execution.md`](./tutorials/nemo-claw-openclaw/unitree-application/phase-3-mission-execution.md) | **Phase 3** — Mission Library + Mission Supervisor for context-aware execution. |
