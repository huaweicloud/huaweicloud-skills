# Related Commands

Common commands for inspecting and managing OpenViking agent integration.

## OpenViking Server

| Command | Description |
|---------|-------------|
| `curl -s http://127.0.0.1:1933/health` | Server health check |
| `curl -s http://127.0.0.1:1933/mcp` | MCP endpoint (used by agents) |
| `scripts/verify_mcp.sh` | Full MCP protocol handshake verification |

## Status and Inspection

| Command | Description |
|---------|-------------|
| `scripts/status.sh` | Integration status for all agents |
| `scripts/status.sh --agent <name>` | Integration status for one agent |
| `ls /root/job-envs/sandboxes/` | List agent sandbox directories |
| `ls /root/template/<agent>/` | List template files for an agent |

## Integration Lifecycle

| Command | Description |
|---------|-------------|
| `scripts/integrate.sh --agent <name> [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]` | Integrate one agent |
| `scripts/integrate.sh --all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]` | Integrate all agents |
| `scripts/unbind.sh --agent <name> [--dry-run] [--yes]` | Unbind one agent |
| `scripts/unbind.sh --all [--dry-run] [--yes]` | Unbind all agents |
| `scripts/unset.sh` | Alias for `unbind.sh` (backward compatibility wrapper) |

## Inspection Examples

```bash
# Show an agent's config file
cat /root/job-envs/sandboxes/<sandbox>/.codeartsdoer/codearts_cli.json

# Show template start.sh for persistence checks
cat /root/template/opencode/start.sh

# List backup files created by the skill
ls -la /root/template/opencode/start.sh.bak.*
```

## Common Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OV_ENDPOINT` | `http://127.0.0.1:1933` | OpenViking server endpoint |

## OpenClaw Sandbox Restart (Apply Template Changes)

OpenClaw's `stop + start` recreates the bwrap process with `bash /workspace/process_dir/start.sh`,
so `start.sh` **is** re-run and template changes (e.g. OpenViking endpoint config) are applied.
A simple `stop + start` is sufficient:

```bash
BASE=http://127.0.0.1:8090/api/v1

# Simple restart: stop -> start (re-runs start.sh)
curl -s -X POST $BASE/envs/openclaw/stop
# Wait for stopped, then:
curl -s -X POST $BASE/envs/openclaw/start
# Poll until running:
for i in $(seq 1 60); do
  st=$(curl -s $BASE/envs/openclaw | jq -r .state)
  [ "$st" = "running" ] && break; [ "$st" = "error" ] && break
  sleep 2
done
```

If `stop + start` fails to apply changes (rare), use full rebuild as fallback:

```bash
# Full rebuild fallback: stop -> delete -> create -> deploy
curl -s -X POST $BASE/envs/openclaw/stop
# Wait for stopped, then:
curl -s -X DELETE $BASE/envs/openclaw
curl -s -X POST $BASE/envs -H 'Content-Type: application/json' -d '{"template":"openclaw"}'
curl -s -X POST $BASE/envs/openclaw/deploy
# Poll until running:
for i in $(seq 1 60); do
  st=$(curl -s $BASE/envs/openclaw | jq -r .state)
  [ "$st" = "running" ] && break; [ "$st" = "error" ] && break
  sleep 2
done
```

## OpenClaw Live Config Verification (from outside bwrap)

The `exec` API creates a separate bwrap instance that cannot see the gateway's `/tmp/.openclaw`.
To verify the live config from the host, check the gateway process environment:

```bash
# Check if start.sh Step 5.4 ran (endpoint config applied)
gw_pid=$(pgrep -f "openclaw-gateway" | head -1)
tr '\0' '\n' < /proc/$gw_pid/environ | grep OPENVIKING
# Expected output:
#   OPENVIKING_BASE_URL=http://127.0.0.1:1933
#   OPENVIKING_ENDPOINT=http://127.0.0.1:1933
#   OPENVIKING_API_KEY=
```

Or use the skill's built-in check:

```bash
scripts/integrate.sh --agent openclaw --dry-run
# Reports "OpenClaw live sandbox has OpenViking endpoint configured" (OK)
# Or warns with rebuild commands if config is missing
```