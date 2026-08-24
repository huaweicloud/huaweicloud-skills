# Verification Method

Step-by-step verification for each workflow of the OpenViking agent integration skill.

## Prerequisite Checks

| Check | Method |
|-------|--------|
| OpenViking server reachable | `curl -s http://127.0.0.1:1933/health` returns `healthy` |
| Job environments exist | `ls /root/job-envs/sandboxes/` shows agent sandboxes |
| Host tooling | `curl --version` and `python3 --version` succeed |

## Task 1: Check Integration Status

| Check | Method |
|-------|--------|
| Script exits 0 | `scripts/status.sh` returns 0 |
| Server health shown | Output reports OpenViking server as healthy/unhealthy |
| Per-agent state accurate | State matches the actual config files checked by the script |

## Task 2: Verify MCP Endpoint

| Check | Method |
|-------|--------|
| Handshake succeeds | `scripts/verify_mcp.sh` completes initialize → notifications/initialized → tools/list → tools/call health |
| Tool list present | Output lists the expected 13 OpenViking tools |
| Errors reported | Any protocol failure is reported with the failing step name |

## Task 3/4: Integrate

| Check | Method |
|-------|--------|
| Authorization honored | Interactive run without `--yes` pauses at the `confirm` prompt |
| Dry run makes no changes | `--dry-run` output ends with no config file modification (compare `stat` timestamps) |
| MCP config written | Expected config file contains `openviking` MCP entry (see `agent-configs.md`) |
| Template-level write | Template `start.sh` contains the re-injection block (agents: OpenCode, Hermes, KimiCode, OpenClaw) |
| Backup created | `.bak.<timestamp>` file exists next to each modified config |
| Post-integration status | `status.sh` shows `template + live` (or documented partial state) |
| **DeepSeek Harness bundle check** | `grep '@openviking/dsh-memory-plugin' <sandbox>/.dsh/profiles/web/package.json` shows the dependency + `dsh.profile.bundles` entry, and `node_modules/@openviking/dsh-memory-plugin/package.json` exists. Boot check: `dsh --profile web --port 0` starts (`dsh web: http://127.0.0.1:<port>`) and `--dump-config` composes the `openviking-memory` group. |
| **OpenClaw live endpoint check** | Gateway process has `OPENVIKING_BASE_URL` in env: `tr '\0' '\n' < /proc/$(pgrep -f openclaw-gateway \| head -1)/environ \| grep OPENVIKING`. If missing, sandbox was restarted via `stop+start` without re-running `start.sh` — rebuild via Task 7 procedure. `integrate.sh --agent openclaw --dry-run` detects this automatically. |

## Task 5/6: Unbind

| Check | Method |
|-------|--------|
| Authorization honored | Interactive run without `--yes` pauses at the `confirm` prompt |
| MCP config removed | `openviking` entry absent from the agent's config file |
| Template cleaned | Re-injection block removed from template `start.sh` where previously injected |
| Post-unbind status | `status.sh` shows the agent as not integrated |
| No residual config | `openviking-config.json` removed where the script owns it |

## End-to-End Acceptance

1. `integrate.sh --agent <name>` completes with exit 0
2. `status.sh` reports `template + live` for that agent
3. `verify_mcp.sh` lists the 13 OpenViking tools
4. Agent restart (new sandbox) preserves the integration (`status.sh` still reports `template + live`)
5. `unbind.sh --agent <name>` completes with exit 0
6. `status.sh` confirms the agent is no longer integrated
7. No `.bak` restore was needed (or restores were successful)