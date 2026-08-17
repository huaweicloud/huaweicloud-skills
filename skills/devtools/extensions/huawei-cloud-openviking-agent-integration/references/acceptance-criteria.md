# Acceptance Criteria

Criteria for a successful OpenViking agent integration or unbinding operation.

## Integration

- [ ] User authorization was explicitly obtained (interactive `confirm` prompt or documented `--yes` use)
- [ ] `integrate.sh` exits 0
- [ ] MCP server entry exists in the agent's config (`mcp.openviking` / `mcp_servers.openviking` / `mcp.servers` depending on agent)
- [ ] Agent-specific integration artifacts exist:
  - CodeArts: 4-section prompt in `agent.build.prompt` + `openviking-config.json`
  - OpenCode: enhanced prompt + `openviking-config.json`
  - OpenClaw: official `@openviking/openclaw-plugin` installed (npm, Huawei Cloud mirror) + `plugins.allow: ["openviking"]` + AGENTS.md
  - Hermes: `memory.provider: openviking` + MCP server block
  - JiuwenSwarm: `memory.engine: both` + `external.provider: openviking` + AGENTS.md
  - KimiCode: `mcp.json` entry + 4-section AGENTS.md + `openviking-config.json`
- [ ] Template-level write succeeded for template-persistence agents (OpenCode, Hermes, KimiCode, OpenClaw)
- [ ] `.bak.<timestamp>` backup created for every modified file
- [ ] `status.sh` reports `template + live`
- [ ] `verify_mcp.sh` completes the full MCP handshake and lists 13 tools
- [ ] Integration survives a sandbox restart (`status.sh` still reports `template + live`)

## Unbind

- [ ] User authorization was explicitly obtained
- [ ] `unbind.sh` exits 0
- [ ] OpenViking MCP entry removed from the agent's config
- [ ] Injected prompts/AGENTS.md blocks removed or neutralized
- [ ] Template re-injection block removed where previously injected
- [ ] `openviking-config.json` removed where owned by the skill
- [ ] `status.sh` confirms the agent is no longer integrated

## Reporting

- [ ] Summary lists which agents were changed and their resulting state
- [ ] Any partial state (`template only` / `live only`) was explicitly called out
- [ ] No credential or API key appeared in any output or log