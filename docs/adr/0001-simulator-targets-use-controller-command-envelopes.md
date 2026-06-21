# Simulator Targets Use Controller Command Envelopes

Robot Bridge keeps the agent-facing Action and Mission API, but simulator control targets consume a shared Controller Command Envelope rather than high-level SDK-style commands or actuator-level packets. This keeps Isaac Sim and MuJoCo aligned around controller-level intent for future RL policies or classical controllers, while leaving raw joint and torque control outside the Robot Bridge boundary.

**Consequences**

Isaac Sim command-like endpoints such as `/move`, `/balance_stand`, `/hello`, and `/dance1` should be removed during the simulator contract refactor rather than kept as compatibility shims, because the old contract has no external users. New simulator target work should use the shared controller-command contract, unsupported demo gestures should fail explicitly instead of being treated as successful no-ops, and the direct `/robot/command` route should be removed in favor of approved actions, missions, status, and stop routes.

Robot Bridge core owns construction of canonical Controller Command Envelopes from approved action steps. All control targets consume that internal envelope: real Go2 translates it to Unitree SDK2 calls, while simulator targets transport it to their controller sidecars.

The canonical action step vocabulary is `status`, `stop`, `posture`, `move`, and `wait`. SDK-style demo gestures such as `hello` and `dance1` are removed from the core command surface instead of being modeled as required simulator capabilities.

Posture commands are constrained by Robot Bridge rather than accepted as arbitrary controller-specific strings. The initial posture vocabulary is `balance_stand`, `stand_up`, `stand_down`, and `recovery_stand`, with future expansion requiring an explicit bridge-side change or configuration.

The bridge client CLI remains action- and mission-oriented. It may call health, status, stop, actions, missions, and logs, but must not reintroduce direct command dispatch to /robot/command.