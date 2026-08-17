# IAM Policies / Access Permissions

## Overview

This skill switches OpenViking's embedding model via the job-env-manager REST API. It does not access Huawei Cloud services, so no Huawei Cloud IAM policies are required. The permissions below are the equivalent access controls for this environment.

## Minimum Required Permissions

| Resource | Permission | Reason |
|----------|-----------|--------|
| job-env-manager | REST API `http://127.0.0.1:8090` | Query env state, `exec` API for in-sandbox commands |
| OpenViking sandbox | Read/write `ov.conf`, `vectordb/context` | Modify embedding config, rebuild index |
| llama-server sandbox | Access `http://127.0.0.1:${LLAMA_PORT}/v1/embeddings` | Validate target embedding endpoint, measure dimension |
| OpenViking server | Access `http://127.0.0.1:1933/health` | Health verification after restart |
| Host | Execute `curl`, `python3`, `kill` | Script prerequisites |

## Authentication

- **Dev mode (default)**: no API key needed — job-env-manager accepts anonymous access on the host loopback.
- If the environment requires an API key, it must come from environment variables — never hardcode it and never ask the user to type it in chat.

## Security Rules

- **NEVER** run `openviking-server` directly on the host — always use the `exec` API.
- **NEVER** use `stop`/`start` for restart — `start.sh` overwrites `ov.conf` with TokenHub credentials.
- **NEVER** delete vectordb data unless the dimension actually changed.
- Always back up `ov.conf` to `ov.conf.bak` before modifying; rollback on failed verification.