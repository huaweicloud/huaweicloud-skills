# IAM Policies / Access Permissions

## Overview

This skill integrates OpenViking with coding agents running in bwrap sandboxes. It does not access Huawei Cloud services, so no Huawei Cloud IAM policies are required. The permissions below are the equivalent access controls for this environment.

## Minimum Required Permissions

| Resource | Permission | Reason |
|----------|-----------|--------|
| OpenViking server | Access to `http://127.0.0.1:1933` | MCP endpoint / health check |
| OpenViking server | `root_api_key` (if auth enabled) | `--api-key` for MCP handshake; dev mode needs none |
| Host filesystem | Read/write under `/root/template/<agent>/start.sh` | Template-level re-injection for persistence |
| Host filesystem | Read/write under `/root/job-envs/sandboxes/` | Live sandbox config files |
| Host filesystem | Execute `curl`, `python3`, `bash` | Script prerequisites |

## Authentication Modes

- **Dev mode (default)**: no API key needed — OpenViking server accepts anonymous access.
- **Auth enabled**: the server's `root_api_key` must be provided via `--api-key`. Never type the key into chat; pass it on the command line only.

## Security Rules

- **NEVER** expose AK/SK, API keys, or tokens in code, logs, or status output.
- **NEVER** let users input API keys directly in conversation.
- **ALWAYS** use command-line flags or environment variables for credentials.
- Every config modification creates a `.bak.<timestamp>` backup for rollback.