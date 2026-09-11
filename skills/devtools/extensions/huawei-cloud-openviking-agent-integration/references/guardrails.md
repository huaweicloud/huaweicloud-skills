# Guardrails (Supplement)

Details beyond what SKILL.md's Authorization & Safety section covers.

## State Reporting

- **Never claim an agent is integrated without running `status.sh` first.**
- Three states: `template + live` (active), `template only` (activates on restart), `live only` (**lost on restart** — explicitly warn user).
- Template-level persistence (dual-write) required for agents whose `start.sh` recreates config: OpenCode, Hermes, KimiCode, OpenClaw.
- A live-only change is a **partial integration, not success** — verify template-level write succeeded.

## Credential Handling

- **NEVER** echo `--api-key` in output, logs, or status. Use command-line flags or env vars only.
- **NEVER** persist API keys in agent config beyond what the agent itself requires.
- Dev mode (default): no key needed. Auth enabled: pass server's `root_api_key` via `--api-key`.

## Environment Safety

- OpenViking server runs inside a bwrap sandbox — never start/stop it on the host directly.
- Host filesystem operations limited to template `start.sh` under `/root/template/<agent>/` and sandbox workspace copies.
- If server unreachable, do not attempt integration — report the prerequisite failure.

## Rollback

- Every config modification creates a `.bak.<timestamp>` backup.
- If verification fails, restore the backup and report.
- If `verify_mcp.sh` fails during integration, remove partial MCP config (or restore backup) and report.

## Access Permissions

No Huawei Cloud IAM policies required — this skill operates on local bwrap sandboxes only.

| Resource | Permission | Reason |
|----------|-----------|--------|
| OpenViking server | Access to `http://127.0.0.1:1933` | MCP endpoint / health check |
| OpenViking server | `root_api_key` (if auth enabled) | `--api-key` for MCP handshake |
| Host filesystem | R/W `/root/template/<agent>/start.sh` | Template re-injection |
| Host filesystem | R/W `/root/job-envs/sandboxes/` | Live sandbox config |
| Host filesystem | Execute `curl`, `python3`, `bash` | Script prerequisites |
