# Verification & Acceptance Criteria

## Prerequisite Checks

| Check | Method |
|-------|--------|
| OpenViking server reachable | `curl -s http://127.0.0.1:1933/health` returns `healthy` |
| Agent sandboxes exist | `ls /root/job-envs/sandboxes/` shows agent dirs |
| Host tooling | `curl --version` and `python3 --version` succeed |

## Integration Verification

| Check | Method |
|-------|--------|
| Authorization honored | Without `--yes`, pauses at `confirm` prompt |
| Dry run makes no changes | `--dry-run` output ends with no file modification |
| MCP config written | Config file contains `openviking` entry (see `agent-configs.md`) |
| Template-level write | Template `start.sh` contains re-injection block (OpenCode, Hermes, KimiCode, OpenClaw) |
| Backup created | `.bak.<timestamp>` exists next to each modified file |
| Post-integration status | `status.sh` shows `template + live` |
| MCP handshake | `verify_mcp.sh` completes initialize → tools/list → health, lists 13 tools |
| Survives restart | New sandbox still reports `template + live` |

**Agent-specific checks**:
- **DeepSeek Harness**: `grep '@openviking/dsh-memory-plugin' <sandbox>/.dsh/profiles/web/package.json` + `node_modules/@openviking/dsh-memory-plugin/package.json` exists. Boot check: `dsh --profile web --port 0` starts and `--dump-config` composes `openviking-memory` group.
- **OpenClaw live endpoint**: `tr '\0' '\n' < /proc/$(pgrep -f openclaw-gateway \| head -1)/environ \| grep OPENVIKING`. If missing, rebuild via `stop + start`.

## Unbind Verification

| Check | Method |
|-------|--------|
| Authorization honored | Without `--yes`, pauses at `confirm` prompt |
| MCP config removed | `openviking` entry absent from config file |
| Template cleaned | Re-injection block removed from template `start.sh` |
| No residual config | `openviking-config.json` removed where owned by skill |
| Post-unbind status | `status.sh` confirms agent not integrated |

## End-to-End Acceptance

1. `integrate.sh --agent <name>` exits 0
2. `status.sh` reports `template + live`
3. `verify_mcp.sh` lists 13 OpenViking tools
4. Agent restart preserves integration
5. `unbind.sh --agent <name>` exits 0
6. `status.sh` confirms not integrated
7. No `.bak` restore needed (or restores successful)
8. No credential or API key appeared in any output
