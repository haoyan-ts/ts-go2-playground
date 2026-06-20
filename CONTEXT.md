# Go2 Playground

Go2 Playground is a safe control context for Unitree Go2 demos. It keeps agent-facing tools behind Robot Bridge while allowing the actual execution target to be dry, physical, or simulated.

## Language

**Robot Bridge**:
The controlled API boundary for Go2 commands, actions, missions, safety checks, and logs. Agents and sandbox clients call Robot Bridge instead of robot SDKs or simulator APIs directly.
_Avoid_: direct SDK access, raw robot access

**Control Target**:
The execution destination behind Robot Bridge. A control target can be dry, a physical Go2, or an Isaac Sim Go2 while preserving the same agent-facing API.
_Avoid_: mode, backend, environment

**Dry Target**:
A control target that returns structured responses without moving hardware or a simulator. It is for setup checks, tutorials, and safe command rehearsals.
_Avoid_: fake robot, simulation

**Real Go2 Target**:
A control target that sends approved commands to a physical Unitree Go2 through Unitree SDK2.
_Avoid_: real mode, hardware mode

**Isaac Sim Target**:
A control target that forwards approved Go2 commands from Robot Bridge to a Go2 model running inside Isaac Sim.
_Avoid_: dry mode, simulator mode

**Action**:
A named, approved sequence of low-level Go2 steps exposed by Robot Bridge.
_Avoid_: script, macro

**Mission**:
A named, approved workflow that can combine actions, observation pauses, and a final report.
_Avoid_: task, scenario

**Safety Supervisor**:
The Robot Bridge component that validates confirmation requirements and movement limits before commands reach a control target.
_Avoid_: guard, validator
