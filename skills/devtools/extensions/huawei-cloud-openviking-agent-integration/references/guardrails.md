# Guardrails

Safety and authorization rules for the OpenViking agent integration skill. These rules are mandatory — violations may corrupt agent configurations or expose credentials.

## 1. Authorization

- **Both integration and unbinding require explicit user authorization.** The scripts prompt for `confirm` before modifying any agent configuration.
- The user must type exactly `confirm` to proceed. Any other input aborts the operation.
- `--yes` / `-y` skips the prompt — allowed for automation only, never recommended for production.
- `--dry-run` shows what would happen without requiring authorization — use it first for unfamiliar targets.
- Never modify an agent configuration that the user did not ask to modify.

## 2. State Reporting

- **Never claim an agent is integrated without running `status.sh` first.** The status script is the single source of truth.
- Report the three states accurately:
  - `template + live` — fully integrated and active
  - `template only` — will activate on next restart
  - `live only` — will be **lost on restart**
- If status shows `live only`, explicitly warn the user that the integration is not persistent.

## 3. Configuration Changes

- All configuration changes must go through the skill scripts (`integrate.sh`, `unbind.sh`). Do not hand-edit `/root/template/<agent>/start.sh` or sandbox config files.
- Template-level persistence (dual-write) is required for agents whose `start.sh` recreates config from scratch: OpenCode, Hermes, KimiCode, OpenClaw.
- Verify template-level write succeeded; a live-only change is a partial integration, not success.

## 4. Credential Handling

- **NEVER** echo `--api-key` values to output, logs, or status messages.
- **NEVER** persist API keys in agent config beyond what the agent itself requires.
- When server auth is enabled, use the key the user provides; in dev mode, no key is needed — do not fabricate one.

## 5. Environment Safety

- The OpenViking server runs inside a bwrap sandbox. Never start or stop `openviking-server` on the host directly.
- Operations against the host filesystem are limited to template `start.sh` files under `/root/template/<agent>/` and sandbox workspace copies.
- If the OpenViking server is unreachable (`curl http://127.0.0.1:1933/health` fails), do not attempt integration — report the prerequisite failure.

## 6. Rollback

- Every config modification creates a `.bak.<timestamp>` backup. If a verification step fails, restore the backup and report the problem.
- If `verify_mcp.sh` fails during integration, remove the partial MCP configuration (or restore the backup) and report.