# NemoClaw + OpenClaw Tutorial

Version: 2026-06-20  
Scope: **OpenClaw only**. Hermes is out of scope for this tutorial.

---

## 0. Tutorial Goal

This tutorial is designed as a three-phase learning path for beginners who want to use **NemoClaw with OpenClaw**.

| Phase | Level | Goal | Main Result |
|---|---|---|---|
| Phase 1 | 初級 | Install NemoClaw and start one OpenClaw sandbox | Browser/TUIでOpenClaw agentに話しかけられる |
| Phase 2 | 中級 | Operate the sandbox safely | ファイル操作、ログ確認、policy確認、snapshotができる |
| Phase 3 | 上級（高級） | Configure controlled real-world usage | custom policy、messaging、local inference、backup/rebuild方針を扱える |

This tutorial uses the sandbox name:

```bash
my-claw
```

You can replace it with your own name.

---

# Phase 1: 初級 — Install and Start OpenClaw

## 1.1 What You Learn

By the end of Phase 1, you should be able to:

- install NemoClaw;
- create one OpenClaw sandbox;
- open the OpenClaw dashboard in a browser;
- connect from the terminal;
- run the first prompt;
- check whether the sandbox is healthy.

---

## 1.2 Prerequisites

Recommended environment:

| Item | Requirement |
|---|---|
| OS | Linux, macOS, or Windows WSL2 |
| Runtime | Docker / Docker Desktop / Colima |
| Memory | 8 GB minimum, 16 GB recommended |
| Disk | 20 GB minimum, 40 GB recommended |
| API Key | OpenAI, NVIDIA, Anthropic, Gemini, or compatible endpoint |

Check Docker:

```bash
docker --version
docker ps
```

Check Node.js and npm if already installed:

```bash
node -v
npm -v
```

NemoClaw's installer can install required components in supported environments, but checking first makes troubleshooting easier.

---

## 1.3 Choose an Inference Provider

For the first run, use one hosted provider. Example options:

| Provider | Environment Variable |
|---|---|
| NVIDIA Endpoints | `NVIDIA_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| Other OpenAI-compatible endpoint | `COMPATIBLE_API_KEY` |
| Local Ollama | no cloud API key |

Example: OpenAI

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Example: NVIDIA Endpoints

```bash
export NVIDIA_API_KEY="your_api_key_here"
```

Do not commit API keys to Git.

---

## 1.4 Install NemoClaw and Onboard OpenClaw

Run:

```bash
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

The installer launches the onboarding wizard. During the wizard, choose:

| Prompt | Recommended Beginner Choice |
|---|---|
| Agent | OpenClaw default / OpenClaw guide path |
| Provider | OpenAI or NVIDIA Endpoints |
| Model | Default model shown by the wizard |
| Sandbox name | `my-claw` |
| Web Search | Off for the first run |
| Messaging channels | None for the first run |
| Network policy | Balanced / default |

If the installer does not automatically start onboarding, run:

```bash
nemoclaw onboard
```

---

## 1.5 Confirm the Sandbox Exists

After onboarding finishes:

```bash
nemoclaw list
```

Check status:

```bash
nemoclaw my-claw status
```

Run a focused health check:

```bash
nemoclaw my-claw doctor
```

If `doctor` reports warnings, read them before continuing. Some warnings may be non-fatal, but failed checks should be resolved before using the agent seriously.

---

## 1.6 Open the Browser Dashboard

Print the authenticated dashboard URL:

```bash
nemoclaw my-claw dashboard-url --quiet
```

Open the returned URL in your browser.

Important:

- Treat the dashboard URL like a password.
- Do not paste it into chat rooms.
- Do not save it in Git.
- Do not publish screenshots containing the tokenized URL.

---

## 1.7 Use OpenClaw from Terminal

Connect to the sandbox:

```bash
nemoclaw my-claw connect
```

Inside the sandbox, start OpenClaw TUI:

```bash
openclaw tui
```

To exit OpenClaw TUI, use the command shown by the TUI, usually:

```text
/exit
```

Then exit the sandbox shell:

```bash
exit
```

---

## 1.8 First Safe Prompts

Use simple prompts first.

```text
Hello. Briefly explain what you can do in this sandbox.
```

```text
Create a short Markdown file under /sandbox/workspace named hello-openclaw.md. Explain what NemoClaw and OpenClaw are in 5 bullet points.
```

```text
List the files in /sandbox/workspace and summarize what you created.
```

---

## 1.9 Phase 1 Completion Checklist

You can move to Phase 2 when all items are true:

- [ ] `nemoclaw list` shows `my-claw`.
- [ ] `nemoclaw my-claw status` runs successfully.
- [ ] `nemoclaw my-claw doctor` has no blocking failure.
- [ ] Browser dashboard opens.
- [ ] `nemoclaw my-claw connect` works.
- [ ] `openclaw tui` starts inside the sandbox.
- [ ] OpenClaw can create a file under `/sandbox/workspace`.

---

# Phase 2: 中級 — Daily Sandbox Operation

## 2.1 What You Learn

By the end of Phase 2, you should be able to:

- understand host vs sandbox boundaries;
- run commands inside the sandbox safely;
- use `/sandbox/workspace` for working files;
- inspect OpenClaw workspace files;
- monitor logs;
- use network policy presets carefully;
- create and restore snapshots.

---

## 2.2 Understand the Two Main File Areas

There are two important areas inside the sandbox.

| Path | Purpose |
|---|---|
| `/sandbox/workspace` | Your normal working files. Use this for documents, scripts, test files, outputs. |
| `/sandbox/.openclaw/workspace/` | OpenClaw agent workspace files: persona, user context, memory, behavior config. |

OpenClaw workspace files usually include:

| File | Purpose |
|---|---|
| `SOUL.md` | Agent persona and tone |
| `USER.md` | User context |
| `IDENTITY.md` | Agent identity |
| `AGENTS.md` | Behavior rules and workflow conventions |
| `MEMORY.md` | Curated long-term memory |
| `memory/` | Daily memory notes |

Beginner rule:

> Put normal task files in `/sandbox/workspace`. Do not edit `/sandbox/.openclaw/workspace/` until you have a snapshot.

---

## 2.3 Run Commands Inside the Sandbox

Use `nemoclaw <name> exec`, not raw `docker exec`.

Check current directory:

```bash
nemoclaw my-claw exec -- pwd
```

List sandbox root:

```bash
nemoclaw my-claw exec -- ls -la /sandbox
```

Create a tutorial folder:

```bash
nemoclaw my-claw exec -- mkdir -p /sandbox/workspace/tutorial
```

Create a file:

```bash
nemoclaw my-claw exec -- bash -lc 'echo "# NemoClaw Phase 2" > /sandbox/workspace/tutorial/README.md'
```

Read the file:

```bash
nemoclaw my-claw exec -- cat /sandbox/workspace/tutorial/README.md
```

---

## 2.4 Ask OpenClaw to Work in a Specific Folder

In the browser or TUI, use a prompt like this:

```text
Use /sandbox/workspace/tutorial as the working directory.
Create a file named task-plan.md.
The file should contain:
1. today's learning goal;
2. commands I used;
3. mistakes to avoid.
Do not modify files outside /sandbox/workspace/tutorial.
```

Then verify from host:

```bash
nemoclaw my-claw exec -- ls -la /sandbox/workspace/tutorial
nemoclaw my-claw exec -- cat /sandbox/workspace/tutorial/task-plan.md
```

---

## 2.5 Mount the Sandbox Filesystem on the Host

This is useful when you want to edit sandbox files with VS Code or another host editor.

Install SSHFS if needed.

Linux:

```bash
sudo apt-get install sshfs
```

macOS:

```bash
brew install macfuse sshfs
```

Mount the sandbox:

```bash
nemoclaw my-claw share mount
```

Expected result:

```text
Mounted /sandbox → ~/.nemoclaw/mounts/my-claw
```

Mount only the working folder to a custom path:

```bash
mkdir -p ~/my-claw-workspace
nemoclaw my-claw share mount /sandbox/workspace ~/my-claw-workspace
```

Check mount status:

```bash
nemoclaw my-claw share status
```

Unmount:

```bash
nemoclaw my-claw share unmount
```

---

## 2.6 Monitor Runtime Logs

Follow logs:

```bash
nemoclaw my-claw logs --follow
```

Use this when:

- the agent does not respond;
- the dashboard loads but no message returns;
- a tool call fails;
- network policy blocks a request;
- inference provider returns an error.

In another terminal, check health:

```bash
nemoclaw my-claw status
nemoclaw my-claw doctor
```

---

## 2.7 Use OpenShell TUI for Network Requests

Open the TUI on the host:

```bash
openshell term
```

Use it to:

- see blocked outbound requests;
- approve a one-off request;
- deny suspicious access;
- understand which process tried to access which host.

Rule:

> For one-off testing, approve in TUI. For repeated legitimate use, add a policy preset.

---

## 2.8 Inspect and Add Policy Presets

List current policy presets:

```bash
nemoclaw my-claw policy-list
```

Explain policy context:

```bash
nemoclaw my-claw policy-explain
```

Preview adding a preset:

```bash
nemoclaw my-claw policy-add pypi --dry-run
```

Apply PyPI access:

```bash
nemoclaw my-claw policy-add pypi --yes
```

Apply GitHub access:

```bash
nemoclaw my-claw policy-add github --yes
```

Remove a preset:

```bash
nemoclaw my-claw policy-remove pypi --yes
```

Common presets include:

| Preset | Use Case |
|---|---|
| `pypi` | Python package install |
| `npm` | npm/yarn package install |
| `github` | GitHub access |
| `huggingface` | model/download access |
| `brave` | Brave Search |
| `slack` | Slack integration |
| `telegram` | Telegram Bot API |

Only add the presets you actually need.

---

## 2.9 Test Package Installation Safely

Example with PyPI:

```bash
nemoclaw my-claw policy-add pypi --yes
nemoclaw my-claw exec -- python -m pip install requests
nemoclaw my-claw exec -- python - <<'PY'
import requests
print(requests.__version__)
PY
```

After the test, decide whether to keep or remove PyPI access:

```bash
nemoclaw my-claw policy-remove pypi --yes
```

---

## 2.10 Create a Snapshot Before Risky Changes

Create a named snapshot:

```bash
nemoclaw my-claw snapshot create --name before-policy-test
```

List snapshots:

```bash
nemoclaw my-claw snapshot list
```

Restore latest snapshot:

```bash
nemoclaw my-claw snapshot restore
```

Restore by name:

```bash
nemoclaw my-claw snapshot restore before-policy-test
```

Clone a snapshot into a new sandbox:

```bash
nemoclaw my-claw snapshot restore before-policy-test --to my-claw-clone
```

Use snapshots before:

- editing OpenClaw workspace files;
- adding custom policy;
- adding channels;
- changing model provider;
- upgrading or rebuilding.

---

## 2.11 Phase 2 Completion Checklist

You can move to Phase 3 when all items are true:

- [ ] You can create, read, and edit files in `/sandbox/workspace`.
- [ ] You understand the difference between `/sandbox/workspace` and `/sandbox/.openclaw/workspace/`.
- [ ] You can use `nemoclaw my-claw exec -- ...`.
- [ ] You can mount and unmount the sandbox filesystem.
- [ ] You can read logs with `logs --follow`.
- [ ] You can open `openshell term` and identify blocked requests.
- [ ] You can list, add, dry-run, and remove policy presets.
- [ ] You can create and restore a snapshot.

---

# Phase 3: 上級（高級） — Controlled Real-World Usage

## 3.1 What You Learn

By the end of Phase 3, you should be able to:

- switch or inspect inference routes;
- use local inference when appropriate;
- add messaging channels deliberately;
- create custom network policies;
- rebuild safely;
- apply a security posture before exposing the agent to real workflows.

---

## 3.2 Advanced Rule: Keep Three Sandboxes

For serious use, keep three sandbox types.

| Sandbox | Purpose | Example Name |
|---|---|---|
| Test | Break things freely | `my-claw-test` |
| Staging | Validate policy, channels, model changes | `my-claw-staging` |
| Main | Daily use | `my-claw-main` |

Clone from snapshot:

```bash
nemoclaw my-claw snapshot create --name clean-baseline
nemoclaw my-claw snapshot restore clean-baseline --to my-claw-test
```

Do risky changes in `my-claw-test` first.

---

## 3.3 Switch Inference Provider or Model

Check current status:

```bash
nemoclaw my-claw status
```

Switch provider/model intentionally:

```bash
nemoclaw inference set --provider <provider> --model <model> --sandbox my-claw
```

Example placeholders:

```bash
nemoclaw inference set --provider openai --model <openai-model-id> --sandbox my-claw
```

```bash
nemoclaw inference set --provider nvidia --model <nvidia-model-id> --sandbox my-claw
```

After switching:

```bash
nemoclaw my-claw status
nemoclaw my-claw doctor
```

Test inference inside the sandbox:

```bash
nemoclaw my-claw connect
openclaw agent --agent main -m "Test inference" --session-id debug
```

If inference fails:

```bash
nemoclaw my-claw logs --follow
```

---

## 3.4 Use Local Inference

Local inference is useful when:

- you want to reduce cloud dependency;
- you want data to stay closer to the host;
- you are testing offline workflows;
- you have enough local compute.

Typical choices:

| Local Backend | Difficulty | Notes |
|---|---|---|
| Ollama | Easier | Best first local inference path |
| vLLM | Advanced | Better for GPU servers |
| NVIDIA NIM | Advanced / Experimental in some paths | Requires suitable NVIDIA environment |

Example Ollama preparation:

```bash
ollama --version
ollama pull llama3.1:8b
ollama serve
```

Then run onboarding or switch inference using the local provider route offered by your NemoClaw installation.

Check local route health:

```bash
nemoclaw my-claw status
```

If local inference is unreachable, restart the local backend first, then retry.

---

## 3.5 Add Messaging Channels Carefully

Phase 1 skipped messaging. Add channels only after you understand logs and policy.

Supported channel examples include:

| Channel | Typical Use |
|---|---|
| Telegram | Personal bot access |
| Discord | Community/dev channel bot |
| Slack | Team workspace bot |
| WeChat | Experimental |
| WhatsApp | Experimental |

Dry-run first:

```bash
nemoclaw my-claw channels add telegram --dry-run
```

Add Telegram:

```bash
nemoclaw my-claw channels add telegram
```

Add Slack:

```bash
nemoclaw my-claw channels add slack
```

After adding a channel, check:

```bash
nemoclaw my-claw status
nemoclaw my-claw logs --follow
openshell term
```

Important rules:

- Add channels with host-side `nemoclaw <sandbox> channels ...` commands.
- Do not mutate channels from inside the sandbox with OpenClaw-specific channel commands.
- Use different bot/app tokens for different sandboxes.
- Do not connect the same production bot token to test and main sandboxes at the same time.

Stop a channel bridge:

```bash
nemoclaw my-claw channels stop telegram
```

Remove a channel:

```bash
nemoclaw my-claw channels remove telegram
```

---

## 3.6 Create a Custom Network Policy Preset

Use custom policy when a built-in preset is not enough.

Example: allow the agent to call a specific internal HTTPS API with Node.js only.

Create a file on the host:

```bash
mkdir -p ./presets
cat > ./presets/my-internal-api.yaml <<'YAML'
preset:
  name: my-internal-api
  description: "Internal service"
network_policies:
  my-internal-api:
    name: my-internal-api
    endpoints:
      - host: api.example.internal
        port: 443
        protocol: rest
        enforcement: enforce
        rules:
          - allow: { method: GET, path: "/**" }
    binaries:
      - { path: /usr/local/bin/node }
YAML
```

Preview:

```bash
nemoclaw my-claw policy-add --from-file ./presets/my-internal-api.yaml --dry-run
```

Apply:

```bash
nemoclaw my-claw policy-add --from-file ./presets/my-internal-api.yaml
```

Verify:

```bash
nemoclaw my-claw policy-list
nemoclaw my-claw policy-explain
```

Remove:

```bash
nemoclaw my-claw policy-remove my-internal-api --yes
```

Security rule:

> Never add broad wildcard egress just because something fails. Identify the exact host, port, method, path, and binary that need access.

---

## 3.7 Rebuild Safely

Use rebuild when you need to upgrade the sandbox to the current agent version while preserving workspace state.

Before rebuild:

```bash
nemoclaw my-claw snapshot create --name before-rebuild
nemoclaw my-claw status
nemoclaw my-claw doctor
```

Rebuild:

```bash
nemoclaw my-claw rebuild
```

Non-interactive rebuild:

```bash
nemoclaw my-claw rebuild --yes
```

After rebuild:

```bash
nemoclaw my-claw status
nemoclaw my-claw doctor
nemoclaw my-claw policy-list
```

---

## 3.8 Back Up All Running Sandboxes

Back up all registered running sandboxes:

```bash
nemoclaw backup-all
```

Use this before:

- major upgrades;
- moving environments;
- changing inference providers;
- changing messaging channels;
- changing policy presets.

---

## 3.9 Security Posture Checklist

Before using NemoClaw + OpenClaw for real work, confirm:

- [ ] One sandbox has one clear trust boundary.
- [ ] Dashboard URL is not shared.
- [ ] API keys are stored as host credentials, not in Git.
- [ ] Only needed policy presets are enabled.
- [ ] Custom policy entries are reviewed.
- [ ] Messaging tokens are unique per sandbox.
- [ ] Logs are checked after channel/model/policy changes.
- [ ] Snapshots exist before risky changes.
- [ ] You know how to remove a policy preset.
- [ ] You know how to destroy a test sandbox.

Destroy a test sandbox:

```bash
nemoclaw my-claw-test destroy
```

Destroy without prompt:

```bash
nemoclaw my-claw-test destroy --yes
```

---

## 3.10 Phase 3 Completion Checklist

You have completed the full tutorial when:

- [ ] You can run a stable OpenClaw sandbox.
- [ ] You can inspect and change model routing.
- [ ] You can use local inference or understand when not to use it.
- [ ] You can add and remove a messaging channel.
- [ ] You can write and apply a custom policy preset.
- [ ] You can rebuild safely.
- [ ] You can back up and restore state.
- [ ] You can explain your current trust boundary and network policy.

---

# Recommended Learning Order

Do not jump straight to Phase 3.

Recommended order:

1. Phase 1: get one sandbox running.
2. Phase 2: learn file, log, policy, snapshot basics.
3. Phase 3: add real integrations only after you can debug failures.

Minimum safe path:

```text
Install → Dashboard → TUI → /sandbox/workspace → exec → logs → policy-list → snapshot → policy-add → channels/local inference/custom policy
```

---

# Quick Command Reference

```bash
# list sandboxes
nemoclaw list

# status / health
nemoclaw my-claw status
nemoclaw my-claw doctor

# dashboard
nemoclaw my-claw dashboard-url --quiet

# connect
nemoclaw my-claw connect
openclaw tui

# exec inside sandbox
nemoclaw my-claw exec -- ls -la /sandbox

# logs
nemoclaw my-claw logs --follow

# network policy
nemoclaw my-claw policy-list
nemoclaw my-claw policy-explain
nemoclaw my-claw policy-add pypi --dry-run
nemoclaw my-claw policy-add pypi --yes
nemoclaw my-claw policy-remove pypi --yes

# OpenShell TUI
openshell term

# snapshots
nemoclaw my-claw snapshot create --name before-change
nemoclaw my-claw snapshot list
nemoclaw my-claw snapshot restore before-change

# file sharing
nemoclaw my-claw share mount
nemoclaw my-claw share status
nemoclaw my-claw share unmount

# inference
nemoclaw inference set --provider <provider> --model <model> --sandbox my-claw

# channels
nemoclaw my-claw channels add telegram --dry-run
nemoclaw my-claw channels add telegram
nemoclaw my-claw channels remove telegram

# rebuild / backup
nemoclaw my-claw rebuild
nemoclaw backup-all

# destroy test sandbox
nemoclaw my-claw-test destroy --yes
```

---

# Official References

- NVIDIA NemoClaw Quickstart with OpenClaw: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/quickstart
- NVIDIA NemoClaw Commands Reference: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/reference/commands
- NVIDIA NemoClaw Workspace Files: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/manage-sandboxes/workspace-files
- NVIDIA NemoClaw Network Policy: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/network-policy/customize-network-policy
- NVIDIA NemoClaw Monitoring: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/monitoring/monitor-sandbox-activity
- NVIDIA NemoClaw Security Best Practices: https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/security/best-practices
- NVIDIA NemoClaw Messaging Channels: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/manage-sandboxes/messaging-channels
- NVIDIA NemoClaw Local Inference: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/inference/use-local-inference
