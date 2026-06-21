# TODO

## Simulator Control Target Refactor Follow-Ups

- [ ] Install or add the missing FastAPI test dependency so `fastapi.testclient.TestClient` works again. Current failure: Starlette requires `httpx2`.
- [ ] Fix the Windows pytest temp/cache permission issue so the full bridge test suite can run without manual workarounds.
- [ ] Re-run the full bridge test suite after those environment issues are fixed:
  ```bash
  pixi run pytest packages/go2-robot-bridge/tests
  ```
- [ ] Add or update app-level API tests for the breaking `/robot/command` removal.
- [ ] Add app-level API tests proving action execution now routes `posture` and `move` through `ControllerCommandEnvelope`.
- [ ] Define the simulator sidecar contract in a dedicated doc, including `/status`, `/stop`, `/controller-command`, expected response fields, and error behavior.
- [ ] Implement or scaffold the Isaac Sim sidecar `/controller-command` endpoint, removing old `/move`, `/balance_stand`, `/hello`, and `/dance1` assumptions.
- [ ] Implement or scaffold the MuJoCo sidecar `/controller-command` endpoint using the same envelope contract.
- [ ] Decide whether the older NemoClaw/OpenClaw phase tutorial docs should be rewritten to the new action/mission-only bridge API or explicitly labeled as legacy examples.
- [ ] If those older tutorials remain active, replace their `/robot/command` examples with action or mission calls.
- [ ] Consider adding target capability reporting later, so simulator targets can report supported controller intents and posture names.
- [ ] Consider moving allowed posture vocabulary to configuration if posture expansion becomes frequent.