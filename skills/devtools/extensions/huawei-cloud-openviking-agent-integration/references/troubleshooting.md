# Troubleshooting

Common failure scenarios for the OpenViking agent integration skill.

| Problem | Solution |
|---------|----------|
| OpenViking server not reachable | `curl http://127.0.0.1:1933/health`; ensure openviking sandbox is running. |
| MCP connection refused | Run `verify_mcp.sh`; check port 1933 is accessible. |
| Authentication error (401/403) | Provide `--api-key` matching server's `root_api_key` (dev mode needs none). |
| Agent not picking up MCP tools | Restart the agent session after integration. |
| Config lost after restart | Re-run `integrate.sh --agent <name>` to add template-level persistence. |
| Hermes: memory not recalling after redeploy | Confirm provider block in template `start.sh` + sandbox config; ensure server healthy. |
| Status shows "live only" | Run `integrate.sh --agent <name>` to fix (will be lost on restart). |
| OpenClaw plugin not activating | Check `openclaw plugins list`; ensure npm install succeeded and `plugins.allow` includes "openviking". |
| OpenClaw: live config missing endpoint | `stop + start` via job-env-manager API; or full rebuild via `stop → delete → create → deploy`. |
| OpenClaw: verifying live config from outside bwrap | Check gateway process env: `tr '\0' '\n' < /proc/$(pgrep -f openclaw-gateway)/environ \| grep OPENVIKING`. |
| recall returns only 1 preference | Ensure `openviking-config.json` has `recall.quotas.preferences: 10` + `recall.maxChars: 20000`; re-run `integrate.sh` if old config. |
| OpenCode: plugin registered but not active (`--pure`) | `integrate.sh` removes `--pure` from exec line; re-run if old integration. |
| OpenCode: sandbox fails to start (npm not found) | `integrate.sh` adds `/usr/local/nodejs` to `readablePaths` + makes npm install non-fatal; re-run if old integration. |
| DeepSeek Harness: `ERR_MODULE_NOT_FOUND` for `@deepseek-ai/*` | `integrate.sh` copies (not symlinks) all `@deepseek-ai/*` packages into plugin's `node_modules`; runs on integrate + every boot. |
| WorkSwarm: not proactively calling memory (code mode) | `integrate.sh` patches `interface_code.py` to add recall call; re-run if old integration. |
| WorkSwarm: prefetch silently fails (top_k vs limit) | `integrate.sh` patches `openviking_memory_provider.py` to use `"limit"`; re-run if old integration. |
| WorkSwarm: prefetch returns 0 results (wrong account) | Config defaults `account: ${OPENVIKING_ACCOUNT:-default}`; override with env var if needed. |
| Config backup files | Each modification creates `.bak.<timestamp>` backup; clean up periodically. |

## Slow Agent Responses

Slow responses are almost never caused by OpenViking integration (MCP calls <0.1s). Diagnose in order:

1. **OpenViking MCP latency** — check agent logs for `mcp__openviking__*` calls; all should be <0.1s.
2. **Model API latency** (the real bottleneck) — measure TTFB against the model endpoint; server-side TTFB grows with context length (e.g. glm-5.2: 13 tokens → 7s, 26k context → 31.8s). No local fix; switch model or shorten context.
3. **Per-call latency** — grep `"API call"` in agent logs for measured latency.
4. **One-time install overhead** — hermes downloads `tirith` once (~385s); openclaw runs `npm install` on first boot. Only happens once per sandbox.
5. **Idle processes burning CPU** — `ps aux | sort -rk3 | head -5`; kill orphaned agent processes.

## Fixed Unbind Cleanup Issues

| Agent | Issue | Fix |
|-------|-------|-----|
| CodeArts | Unbind missed injection block in template `start.sh`; restart re-injected config. | Now removes injection block from template + `build.prompt` + `openviking-config.json` from sandbox. |
| Hermes | Unbind left `mcp_servers`/MCP SDK residue from legacy approach. | Now removes official provider block + legacy MCP/SDK blocks + `memory: provider: openviking` from sandbox config. |
| KimiCode | Unbind missed `# Create openviking-config.json` block in template. | Now removes config creation block from template + `openviking-config.json` from sandbox. |
