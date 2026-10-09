# Reference Notes

Supplement to SKILL.md: guardrails, environment, plugin sources, verification, troubleshooting, adding agents.

## Guardrails

- **Never claim integrated without running `status.sh` first.**
- States: `template + live` (active), `template only` (activates on restart), `live only` (**lost on restart** — warn user).
- **NEVER** echo `--api-key` in output/logs. Use flags or env vars only.
- OpenViking runs in bwrap sandbox — never start/stop on host directly.
- Every config modification creates `.bak.<timestamp>` backup (keep 5); restore on verification failure.
- No IAM policies needed — operates on local sandboxes only.
- KimiCode uses **session lifecycle hooks** (`config.toml [[hooks]]` → `$OV_SHARED_DIR/ov-kimi-hook.sh`) **plus** MCP (`mcp.json`). The dispatcher and `$OV_RUNTIME_DIR/py/` helpers are OV-owned deploy artifacts — never edit/remove them by hand; `unbind.sh` removes only byte-identical OV copies (`ov_common.py` is left untouched if it differs from the skill copy).
- Hook bypass: `OPENVIKING_BYPASS_SESSION=1` or `OPENVIKING_BYPASS_SESSION_PATTERNS=<comma,separated,patterns>` disables recall/capture for matching sessions (e.g. private repos).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OV_ENDPOINT` | `http://127.0.0.1:1933` | OpenViking server endpoint |
| `OV_LANG` | (unset → `zh`) | Override i18n (`zh`/`en`) |
| `OV_*` | see `lib/base.sh` | All paths and plugin versions overridable |
| `OPENVIKING_NPM_REGISTRIES` | (unset → built-in chain) | Space-separated npm registry URLs tried before built-ins (mirrors.huaweicloud.com → npmmirror → npmjs) |
| `OPENVIKING_GH_RAW_MIRRORS` | (unset → built-in chain) | Space-separated GitHub raw-file mirror base URLs replacing built-ins; direct raw.githubusercontent.com kept as final fallback |
| `OPENVIKING_GITHUB_API_MIRROR` | (unset → gh-proxy.com → api.github.com) | GitHub API base URL for plugin metadata (commit SHA + tree JSON); omit trailing slash; legacy `OPENVIKING_PLUGIN_API_URL` wins if both set |

## Sandbox Restart (Apply Template Changes)

```bash
BASE=http://127.0.0.1:8090/api/v1
curl -s -X POST $BASE/envs/<agent>/stop
curl -s -X POST $BASE/envs/<agent>/start   # poll until state=running
```

Full rebuild fallback: `stop → DELETE → POST /envs → deploy`.

## Plugin Sources

The skill ships **no plugin code** — plugins are installed on demand at integrate time via domestic-first mirrors. npm plugins: Huawei Cloud npm → npmmirror → npmjs (`OPENVIKING_NPM_REGISTRIES` overrides). Non-npm plugin files: health-checked GitHub proxy chain, default gh-proxy.com → ghfast.top → direct raw.githubusercontent.com (`OPENVIKING_GH_RAW_MIRRORS` overrides). Git metadata (commit SHA + recursive tree JSON): proxy-first chain, default gh-proxy.com → direct api.github.com (`OPENVIKING_GITHUB_API_MIRROR` / legacy `OPENVIKING_PLUGIN_API_URL` override). All downloads are byte-verified against the official GitHub tree blob SHA. 3-tier cache: sandbox `node_modules` → runtime cache (`/root/runtime/`) → online.

## Verification

| Check | Method |
|-------|--------|
| Server reachable | `curl -s http://127.0.0.1:1933/health` → `healthy` |
| MCP handshake | `verify_mcp.sh` → initialize → tools/list → health (needs `pip install --upgrade "mcp>=2.0"`) |
| Integration | `status.sh` shows `template + live` |
| Survives restart | New sandbox still reports `template + live` |
| Unbind clean | `status.sh` confirms not integrated; no residual config |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Server not reachable | `curl http://127.0.0.1:1933/health`; ensure sandbox running |
| MCP refused | Run `verify_mcp.sh`; check port 1933 |
| Auth error (401/403) | Pass `--api-key` matching server's `root_api_key` |
| Config lost after restart | Re-run `integrate.sh` for template-level persistence |
| Status "live only" | Re-run `integrate.sh` (will be lost on restart) |
| OpenClaw plugin not active | `openclaw plugins list`; ensure npm install + `plugins.allow` |
| recall returns 1 preference | `recallLimit`/`recallMaxContentChars` too small (see agent-configs.md) |
| OpenCode `--pure` | `integrate.sh` removes `--pure`; re-run if old |
| DSH `ERR_MODULE_NOT_FOUND` | `integrate.sh` copies `@deepseek-ai/*` into plugin `node_modules` |
| WorkSwarm no proactive recall | `integrate.sh` patches `interface_code.py`; re-run if old |

### Slow Agent Responses

Almost never caused by OV integration (MCP <0.1s). Diagnose: (1) **MCP latency** — agent logs for `mcp__openviking__*` calls; (2) **model API** — TTFB grows with context length, no local fix; (3) **one-time install** — hermes downloads tirith (~385s), openclaw npm install; (4) **CPU orphans** — `ps aux | sort -rk3 | head -5`.

## Adding a New Agent

One bash subclass `scripts/agents/<name>.sh` with exactly 4 functions, plus one Python CLI `scripts/py/agents/ov_<name>.py` (dispatch pattern, imports shared utils from `ov_common.py`). Missing bash methods fall back to `agent::default_<method>()` (warned by `registry_discover`).

1. **`agent_<name>_register()`** — `agent::set_meta name/display_name/sandbox_pattern/template_path/mechanism` + `registry_add "<name>"`. `name` MUST match filename and `registry_add`.
2. **`agent_<name>_integrate()`** — check template exists → idempotent already-check → `require_confirmation` → `dry_run_msg` → `backup_file` → inject → `ov_log_info` restart hint.
3. **`agent_<name>_unbind()`** — detect template/live OV markers → skip if none → confirm (RED) → remove → restart hint.
4. **`agent_<name>_status()`** — return `agent::report_status <name> <tpl_has> <live_has> <4 detail strings>`.

Key base helpers: `backup_file`, `has_ov_injection`, `find_sandbox`, `ov_safe_rm`, `ov_rollback_last_backup`, `ov_sync_template_to_sandbox`, `ov_deploy_plugin_cached`, `ov_plugin_provision`, `require_confirmation`, `dry_run_msg`, `agent::report_status`.