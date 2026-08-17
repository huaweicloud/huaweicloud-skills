# Troubleshooting

Common failure scenarios for the OpenViking agent integration skill.

| Problem | Solution |
|---------|----------|
| OpenViking server not reachable | Check: `curl http://127.0.0.1:1933/health`. Ensure the openviking sandbox is running. |
| MCP connection refused | Verify MCP endpoint: run `verify_mcp.sh`. Check that port 1933 is accessible. |
| Authentication error (401/403) | Provide `--api-key` matching the server's `root_api_key` config. In dev mode, no key is needed. |
| Agent not picking up MCP tools | Restart the agent session after integration. Config changes require a process restart. |
| **Config lost after restart** (OpenCode/Hermes/KimiCode) | Expected if config was only in the live sandbox. Re-run `integrate.sh --agent <name>` to add template-level persistence. |
| **Hermes: MCP tools not available after redeploy** | The `mcp` Python package is not in the template image. Hermes v0.19+ silently skips MCP discovery when `mcp` is missing (DEBUG-level log, invisible). Fix: `integrate.sh --agent hermes` now injects `pip install "mcp==1.29.0"` into `start.sh`. For existing installations missing this step, re-run `integrate.sh --agent hermes` to add it. |
| Status shows "live only" | Config will be lost on next restart. Run `integrate.sh --agent <name>` to fix. |
| OpenClaw plugin not activating | Check `openclaw plugins list` inside the gateway. Ensure npm install succeeded (check start.sh logs for "[openclaw] OpenViking plugin installed"). Verify `plugins.allow` includes "openviking". |
| **OpenClaw: template correct but live config missing endpoint** | `start.sh` has OpenViking injection but the running sandbox's gateway process lacks `OPENVIKING_BASE_URL`. Fix: `stop + start` via job-env-manager API (re-runs `start.sh`). If that doesn't work, use full rebuild via `stop → delete → create → deploy`. The `integrate.sh --agent openclaw --dry-run` command detects this automatically. |
| **OpenClaw: verifying live config from outside bwrap** | `exec` API creates a separate bwrap and cannot see the gateway's `/tmp/.openclaw`. Instead, check the gateway process env: `tr '\0' '\n' < /proc/$(pgrep -f openclaw-gateway \| head -1)/environ \| grep OPENVIKING`. Presence of `OPENVIKING_BASE_URL=http://...` confirms `start.sh` Step 5.4 ran successfully. |
| **recall returns only 1 preference** | Type quota defaults give `preferences` only 1 slot, and `maxChars` defaults to 6500 (events + entities fill the budget). Fix: ensure `openviking-config.json` has `recall.quotas.preferences: 10` and `recall.maxChars: 20000`. This skill sets these by default; if using an old config, re-run `integrate.sh --agent <name>` to update. See `agent-configs.md`. |
| **OpenCode: plugin registered but not active** (`--pure` flag) | `start.sh` launches opencode with `--pure` which means "run without external plugins", silently skipping the `@openviking/opencode-plugin`. Symptom: `opencode.json` has `plugin: ["@openviking/opencode-plugin"]` and node_modules exists, but no plugin logs, no MCP injection, no recall events. Fix: `integrate.sh` now removes `--pure` from the exec line so plugins load. If using an old integration, re-run `integrate.sh --agent opencode` or manually remove `--pure` from `start.sh`. |
| **OpenCode: sandbox fails to start after integration** (npm not found in bwrap) | The opencode sandbox's default `readablePaths` and `PATH` do not include `/usr/local/nodejs`. Without this, `npm` is not found inside the bwrap, and `set -euo pipefail` in `start.sh` causes the script to exit immediately. Fix: `integrate.sh` now (a) updates `env.yaml` to add `/usr/local/nodejs` to `readablePaths` and `PATH` to `extraEnv`, and (b) makes the npm install step non-fatal (`command -v npm` check + `if` wrapper) so opencode starts even if npm is unavailable. If using an old integration, re-run `integrate.sh --agent opencode` to apply the fix. |
| Config backup files | Each modification creates a `.bak.<timestamp>` backup. Clean up old backups periodically. |

## Slow Agent Responses (hermes / openclaw / any agent)

Slow responses are almost never caused by the OpenViking integration — its MCP calls are <0.1s. Diagnose in order:

1. **Check OpenViking MCP latency** (should be instant):
   ```bash
   grep "mcp__openviking__" <sandbox>/.hermes/logs/agent.log | tail   # hermes example
   ```
   All `mcp__openviking__*` tool calls complete in <0.1s → integration is fine.

2. **Check model API latency** (the real bottleneck):
   ```bash
   KEY=$(tr '\0' '\n' < /proc/$(pgrep -f openclaw-tui | head -1)/environ | grep '^JOB_ENV_MODEL_API_KEY=' | cut -d= -f2-)
   # (a) network: should be ~10-50ms
   curl -s -o /dev/null -w "connect=%{time_connect}s ttfb=%{time_starttransfer}s\n" \
     --max-time 30 https://tokenhub.developer.huaweicloud.com/v2/models
   # (b) inference TTFB: a 13-token "hi" request taking ~7s proves server-side latency
   curl -s --max-time 60 -X POST https://tokenhub.developer.huaweicloud.com/v2/chat/completions \
     -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
     -d '{"model":"glm-5.2","messages":[{"role":"user","content":"hi"}],"max_tokens":8,"stream":false}'
   ```

3. **Check per-call latency in agent logs** (hermes):
   ```bash
   grep "API call" <sandbox>/.hermes/logs/agent.log
   # API call #1: ... latency=7.2s cache=... (100%)
   ```
   Measured on tokenhub zai glm-5.2 (2026-08-14): 13 tokens in → 7.0s; 10.8k tokens in → 5.5s TTFB;
   hermes real turns: 15k in → 7.2s, 21k in → 20s, 26k in → 31.8s. Latency grows with context length —
   this is server-side model TTFB, no local fix. Options: switch model (`JOB_ENV_MODEL_DEFAULT`, e.g. `openpangu-2.0-flash`), shorter context, or accept it.

4. **One-time install overhead can look like a hang**:
   - hermes first `terminal` tool call downloads `tirith` (aarch64 threat DB) → single tool call took **384.9s**
     (`tirith not found — downloading latest release for aarch64-unknown-linux-gnu`). Only happens once per sandbox.
   - openclaw first boot runs `npm install` of the OpenViking plugin (Huawei Cloud mirror) — first message after boot is slower.

5. **Idle agent processes burning CPU** on the host can add jitter:
   ```bash
   ps aux | sort -rk3 | head -5   # look for leftover opencode/dsh processes at 40%+ CPU
   ```
   Example: an orphaned `opencode` (PID 69623, started from an interactive bash under devenvd) ran 1h27m
   at ~47% CPU with no session. Kill it if confirmed unused.

## Fixed Unbind Cleanup Issues

| Agent | Issue | Fix |
|-------|-------|-----|
| **CodeArts** | Unbind only removed `mcp.openviking` from sandbox JSON, not the OpenViking injection block in template `start.sh`. On restart, `start.sh` re-injected the config. | `unbind_codearts` now (1) detects and removes the injection block from template `start.sh`, (2) also removes `build.prompt` from sandbox config, (3) removes `openviking-config.json` from sandbox. |
| **Hermes** | Unbind removed the MCP injection block but missed the separate `# ── MCP SDK install` block in template `start.sh`, and didn't remove the `memory: provider: openviking` block from sandbox `config.yaml`. | `unbind_hermes` now (1) removes MCP SDK install block from template, (2) removes `memory:` provider block from sandbox `config.yaml`. |
| **KimiCode** | Unbind removed the MCP injection block (marker to `AGENTSMD`) but missed the separate `# Create openviking-config.json` block in template `start.sh`. | `unbind_kimicode` now (1) removes the `openviking-config.json` creation block from template, (2) removes `openviking-config.json` file from sandbox. |
