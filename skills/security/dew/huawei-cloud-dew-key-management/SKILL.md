---
name: huawei-cloud-dew-key-management
description: >-
  Use when managing secrets, credentials, encryption keys, certificates, or any sensitive data on Huawei Cloud.
  Covers CSMS (Cloud Secret Management Service) for secret lifecycle management, KMS (Key Management Service)
  for encryption key management, rotation diagnosis, and KMS key usage auditing via CTS.
  Provides 10 huawei_* actions: huawei_list_csms_secrets, huawei_describe_csms_secret,
  huawei_list_csms_secret_versions, huawei_list_kms_keys, huawei_analyze_dew_rotation,
  huawei_analyze_dew_key_usage, huawei_create_kms_key, huawei_enable_csms_secret_rotation,
  huawei_update_csms_secret_version, huawei_delete_kms_key.
  Triggers include: secret, credential, API key, token, password, encrypt, decrypt, KMS, CSMS, DEW,
  certificate, CSR, rotation, 密钥, 凭据, 加密, 轮转, 数据加密.
  Activates for ANY task involving secrets or credentials — load this skill before touching secrets.
tags: [huawei-cloud dew kms csms secret encryption]
---

# Huawei Cloud DEW (Data Encryption Workshop)

**STOP - Do not answer from general knowledge.** Follow the procedure below.

Always run `hcloud <Service> <Operation> --help` before constructing commands to discover exact
parameter names and requirements.

## Overview

This skill provides AI Agent capabilities for Huawei Cloud DEW (Data Encryption Workshop / 数据加密服务),
which bundles two services:

| Service | Full name | Scope |
| ------- | --------- | ----- |
| CSMS | Cloud Secret Management Service | Secret lifecycle (metadata only — values are never fetched) |
| KMS | Key Management Service | Customer master keys (CMK), encryption key lifecycle |

It enables four capability groups through 10 `huawei_*` actions:

| Capability | Risk level | Actions |
| ---------- | ---------- | ------- |
| Query (read-only) | R3 — auto execute | `huawei_list_csms_secrets`, `huawei_describe_csms_secret`, `huawei_list_csms_secret_versions`, `huawei_list_kms_keys` |
| Diagnose (read-only) | R3 — auto execute | `huawei_analyze_dew_rotation`, `huawei_analyze_dew_key_usage` |
| Manage | R2 — preview + confirm | `huawei_create_kms_key`, `huawei_enable_csms_secret_rotation` |
| Manage | R1 — preview + confirm | `huawei_update_csms_secret_version`, `huawei_delete_kms_key` |

**Scope boundaries:**

- ✅ List/describe secrets and versions (metadata only — no secret values)
- ✅ List KMS keys, analyze rotation status, audit KMS key usage via CTS
- ✅ Create KMS keys, enable automatic rotation, manually rotate secret versions, delete KMS keys (with confirmation)
- ❌ NEVER read or fetch secret values (`DownloadSecretBlob`, `ShowSecretVersion` value, `DecryptData` plaintext) into agent context
- ❌ NEVER echo credentials (AK/SK, passwords, tokens) in the conversation

## Critical Warnings

| Trap | Why |
| ---- | --- |
| NEVER fetch secret values into agent context | Use `{{resolve:csms:secret-id:SecretString:key}}` runtime injection instead |
| NEVER echo credentials in conversation | AK/SK, passwords and tokens must never appear in agent output |
| KMS key deletion is irreversible | Deletion is scheduled with a 7-30 day (max 1096) pending window; once the window passes the key and all data encrypted with it are unrecoverable |
| Secret rotation requires automation | Manual rotation risks stale credentials; prefer automatic rotation with a rotation function |
| Cross-account KMS needs grants | KMS keys are regional; cross-region/cross-account use requires grant setup |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated.
   - Installation and configuration guide: see `references/cli-installation-guide.md`
   - Two supported authentication modes:
     - **AK/SK credentials**: environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`), or interactive setup via the hcloud configure wizard
     - **Local hcloud profile**: run "hcloud configure list"; it must show a valid profile with mode `AKSK` and a real `accessKeyId`
   - Verify authentication with "hcloud configure list"
2. **Region**: DEW is region-specific. Always pass `--cli-region={region}` (e.g. `cn-north-4`). `--project_id` is auto-filled from the profile when available.
3. **IAM permissions**: least-privilege policies are provided in `references/iam-policies.md`.
   - Query/diagnose: `csms:ListSecrets`, `csms:ShowSecret`, `csms:ListSecretVersions`, `kms:ListKeys`, `kms:ListKeyDetail`, `cts:ListTraces`
   - Manage: `kms:CreateKey`, `csms:UpdateSecret`, `csms:CreateSecretVersion`, `kms:ScheduleKeyDeletion` (+ `kms:CancelKeyDeletion`)
4. **CTS tracker** (for `huawei_analyze_dew_key_usage`): a system or management tracker must exist in the region. See `references/verification-method.md`.
5. **Rotation function** (for automatic rotation): an OBS/FuncGraph-based rotation function ARN is required by `huawei_enable_csms_secret_rotation` when enabling rotation on a secret that has none.

### Quality reporting environment variables

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `SKILL_QUALITY_ENDPOINT` | No | Report endpoint, default `https://skillsapi.developer.myhuaweicloud.com/api/quality/report` |
| `SKILL_QUALITY_NAME` | No | Skill name (auto-detected by default) |
| `SKILL_QUALITY_DISABLE` | No | Set to `1` to disable reporting (local debugging) |
| `SKILL_QUALITY_TIMEOUT` | No | Report timeout in seconds (default 3) |

## Workflow

```
1. Identify target → region, project_id, secret_name / key_id filters
2. Classify intent →
     - Query/Diagnose (R3): list / describe / analyze — execute automatically
     - Manage (R2/R1): create / enable rotation / rotate / delete — ALWAYS show preview and ask for explicit confirmation first
3. Execute → build the hcloud command from the verified templates below
4. Output → structured JSON summary + readable report (metadata only, never secret values)
5. Report quality → skill_quality_sdk.py reports status/error code/trace_id (see Quality Reporting)
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (`huawei_create_kms_key`, `huawei_enable_csms_secret_rotation`): show the full command, the resource to be created/updated, and ask "confirm?" before running.
- **R1 actions** (`huawei_update_csms_secret_version`, `huawei_delete_kms_key`): show the full
  command and side effects, and require explicit confirmation. For deletion, additionally print
  the irreversible-deletion warning (7-30 day pending window).

## Core Commands

### 1. Query (R3 — read-only, auto execute)

List all CSMS secrets (names and metadata, **no values**):

```bash
# Optional: --project_id={project_id} --limit={n} --marker={marker}
hcloud CSMS ListSecrets --cli-region={region}
```

Describe a CSMS secret (rotation config, KMS key, status):

```bash
# Optional: --project_id={project_id}
hcloud CSMS ShowSecret --cli-region={region} --secret_name={secret_name}
```

List versions and stages of a secret (no values):

```bash
# Optional: --project_id={project_id} --limit={n} --marker={marker}
hcloud CSMS ListSecretVersions --cli-region={region} --secret_name={secret_name}
```

List KMS keys:

```bash
# Optional: --project_id={project_id} --key_state={state} --key_spec={spec} --limit={n} --marker={marker}
hcloud KMS ListKeys --cli-region={region}
```

### 2. Diagnose (R3 — read-only, auto execute)

**`huawei_analyze_dew_rotation`** — rotation status analysis for all CSMS secrets:

```bash
# Step 1: list all secrets
# Optional: --project_id={project_id}
hcloud CSMS ListSecrets --cli-region={region}

# Step 2: for each secret, describe to read rotation config (auto_rotation, rotation_period, rotation_func_urn, status)
# Optional: --project_id={project_id}
hcloud CSMS ShowSecret --cli-region={region} --secret_name={secret_name}

# Step 3 (optional): for each secret's KMS key, check key rotation status
# Optional: --project_id={project_id}
hcloud KMS ShowKeyRotationStatus --cli-region={region} --key_id={key_id}
```

Output a table of secrets with rotation status (enabled/disabled, period, function ARN) and flag risks:
secrets without automatic rotation, rotation function missing, disabled KMS keys.

**`huawei_analyze_dew_key_usage`** — KMS key usage audit via CTS (Cloud Trace Service):

```bash
# Optional: --project_id={project_id} --service_type=KMS --resource_type={resource_type}
# Optional: --trace_name={trace_name} --from={start_ts} --to={end_ts} --limit={n} --next={next}
# 可选: --trace_type=data（数据事件）
hcloud CTS ListTraces --cli-region={region} --trace_type=system
```

Filter `service_type=KMS` traces to audit who used which key (encrypt/decrypt/delete), when, and from
where; flag anomalies (failed `kms:Decrypt` attempts, operations on deleted/disabled keys).

### 3. Manage (R2 — preview + confirm)

**`huawei_create_kms_key`** — create a customer master key:

```bash
# Optional: --key_description={description} --key_spec=AES_256（其他可选: RSA_2048, RSA_3072, RSA_4096, EC_P256, EC_P384, SECP256K1）
# Optional: --key_usage=ENCRYPT_DECRYPT（其他可选: SIGN_VERIFY）--project_id={project_id}
hcloud KMS CreateKey --cli-region={region} --key_alias={alias}
```

**`huawei_enable_csms_secret_rotation`** — enable automatic rotation for a secret:

```bash
# Optional: --rotation_period={days} --rotation_func_urn={urn} --description={description}
# Optional: --project_id={project_id}
hcloud CSMS UpdateSecret --cli-region={region} --secret_name={secret_name} --auto_rotation=true
```

> Note: KooCLI exposes rotation enablement through `CSMS UpdateSecret --auto_rotation=true`
> (there is no separate `EnableSecretRotation` operation in KooCLI 7.2.x — verified against
> `huaweicloudsdkcsms` 3.1.x, `UpdateSecretRequestBody.auto_rotation`).

### 4. Manage (R1 — preview + confirm)

**`huawei_update_csms_secret_version`** — manually rotate a secret version (immediate rotation):

```bash
# Optional: --project_id={project_id}
hcloud CSMS RotateSecret --cli-region={region} --secret_name={secret_name}
```

The rotation executes immediately: a new secret version is created with a randomly generated value in
the background and marked `SYSCURRENT`. **No secret value passes through the agent context.**

> Alternative for approved automation when a specific new value must be stored:
> `hcloud CSMS CreateSecretVersion --cli-region={region} --secret_name={secret_name} --secret_string={value}`
> The value must be supplied by the caller via stdin/env (e.g. `--secret_string="$(read -s ...)"`),
> never typed into the conversation history and never echoed back.

**`huawei_delete_kms_key`** — schedule KMS key deletion. **IRREVERSIBLE — read the warning first:**

```bash
# Optional: --project_id={project_id} --pending_days=7..1096（默认 7）
hcloud KMS DeleteKey --cli-region={region} --key_id={key_id} --pending_days=7
```

**WARNING (must be shown before execution):**

- The key is scheduled for deletion and enters a pending window of `--pending_days` (typical 7-30 days,
  API allows 7-1096).
- Inside the window the deletion can be cancelled: `hcloud KMS CancelKeyDeletion --cli-region={region} --key_id={key_id}`.
- **After the window passes, the key is permanently deleted and data encrypted with it is UNRECOVERABLE.**
- This action is R1: always show the key id, alias, and pending days, then require explicit confirmation.

## Blocked Operations (security policy)

The following operations are **BLOCKED** by this skill's policy — they would expose secret material.
Never run them; use the safe alternative instead:

| Blocked operation | Reason | Safe alternative |
| ----------------- | ------ | ---------------- |
| `CSMS DownloadSecretBlob` (blocked) | Downloads secret value blob | `{{resolve:csms:secret-id:SecretString:key}}` runtime injection in IaC/SDK at the consuming application |
| `CSMS ShowSecretVersion` (blocked — value field) | Returns version payload | Runtime injection; never render the `secret_string` field |
| `KMS DecryptData` (blocked) | Returns plaintext | Decrypt inside the application runtime, never in agent context |
| `KMS CreateDatakey` / `CreateDatakeyWithoutPlaintext` (blocked — plaintext side) | Data key material | Envelope encryption inside application runtime |

## Runtime Injection Pattern

For applications that must consume a secret value, use the MCP proxy **resolve mode** so the value is
injected at the runtime and never enters the agent context:

```text
{{resolve:csms:secret-id:SecretString:key}}
```

```bash
# Terraform / IaC — reference the secret by name; value is resolved at apply time
data "huaweicloud_csms_secret" "db" {
  secret_name = "prod-db-password"
}
# Use: data.huaweicloud_csms_secret.db.secret_string
```

```python
# SDK — fetch at runtime and consume immediately, never print or persist in agent context
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcsms.v1.region.csms_region import CsmsRegion
from huaweicloudsdkcsms.v1 import CsmsClient, ShowSecretVersionRequest

# Authenticate with AK/SK and project_id (or use the default credential chain)
credentials = BasicCredentials(ak, sk, project_id)
client = CsmsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(CsmsRegion.value_of("cn-north-4")) \
    .build()

# version_id="SYSCURRENT" returns the current active version of the secret
request = ShowSecretVersionRequest(secret_name="my-secret", version_id="SYSCURRENT")
secret_value = client.show_secret_version(request).version.secret_string
use(secret_value)
```

## Troubleshooting

| Error | Root cause → Fix |
| ----- | ---------------- |
| Secret not found | Wrong region/project → verify the secret name and region (`--cli-region`) |
| AccessDenied on CSMS | Missing IAM policy → add `csms:ShowSecret`/`csms:ListSecrets` + `kms:Decrypt` as needed (see `references/iam-policies.md`) |
| KMS key disabled | Key scheduled for deletion or manually disabled → `hcloud KMS EnableKey --cli-region={region} --key_id={id}` or create a new key |
| Rotation stuck | Rotation function (FUNC) error → check rotation function logs; verify `rotation_func_urn` |
| CTS returns no data | Tracker not enabled or wrong `--trace_type` → create a tracker; use `system` for KMS control-plane (management) events |
| ListKeys empty but keys exist | Wrong region/enterprise project → check `--cli-region`, `--enterprise_project_id` |

## Security Considerations

- MUST use runtime injection (`{{resolve:csms:...}}`). NEVER fetch secret values into agent context.
- MUST rotate credentials every 90 days (配置 rotation_period ≤ 90 days).
- MUST enable automatic rotation for CSMS secrets.
- MUST audit KMS key usage via CTS (`huawei_analyze_dew_key_usage`).
- SHOULD use customer-managed keys (CMK) for sensitive data.
- MUST NOT use default KMS keys for production workloads.
- MUST NOT echo AK/SK, passwords, tokens, or secret values in any output or report.

## KooCLI Command Format Standard

| Feature | Description | Example |
| ------- | ----------- | ------- |
| Service name | `CSMS`, `KMS`, `CTS` (as shown by `hcloud <service> --help`; metadata dirs are lowercase `csms`/`kms`/`cts`) | `hcloud CSMS ListSecrets --cli-region=cn-north-4` |
| Operation name | PascalCase | `ListSecrets`, `ShowSecret`, `UpdateSecret`, `RotateSecret`, `CreateKey`, `DeleteKey`, `ListTraces` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--secret_name=prod-db-password` |
| Indexed parameter | `--key.N=value` | `--event_subscriptions.1=urn:smn:...` |

## Parameter Confirmation

All parameters below were verified against `hcloud <Service> <Operation> --help` (KooCLI 7.2.12).

### CSMS

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| ListSecrets | `--limit` | int | No | `--limit=50` |
| ListSecrets | `--marker` | string | No | `--marker=<last_secret_name>` |
| ListSecrets | `--event_name` | string | No | `--event_name=my-event` |
| ShowSecret | `--secret_name` | string | **Yes** | `--secret_name=prod-db-password` |
| ListSecretVersions | `--secret_name` | string | **Yes** | `--secret_name=prod-db-password` |
| ListSecretVersions | `--limit` | int | No | `--limit=20` |
| UpdateSecret | `--secret_name` | string | **Yes** | `--secret_name=prod-db-password` |
| UpdateSecret | `--auto_rotation` | bool | **Yes (for rotation)** | `--auto_rotation=true` |
| UpdateSecret | `--rotation_period` | string | No | `--rotation_period=30d` |
| UpdateSecret | `--rotation_func_urn` | string | No | `--rotation_func_urn=urn:fss:cn-north-4:...` |
| UpdateSecret | `--description` | string | No | `--description="db password"` |
| RotateSecret | `--secret_name` | string | **Yes** | `--secret_name=prod-db-password` |

### KMS

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| ListKeys | `--key_state` | string | No | `--key_state=2` (enabled) |
| ListKeys | `--key_spec` | string | No | `--key_spec=AES_256` |
| ListKeys | `--limit` | int | No | `--limit=50` |
| CreateKey | `--key_alias` | string | **Yes** | `--key_alias=app-encryption-key` |
| CreateKey | `--key_description` | string | No | `--key_description="Application data encryption"` |
| CreateKey | `--key_spec` | string | No | `--key_spec=AES_256` (default) |
| CreateKey | `--key_usage` | string | No | `--key_usage=ENCRYPT_DECRYPT` (default) |
| DeleteKey | `--key_id` | string | **Yes** | `--key_id=CHANGE_ME_KEY_ID` |
| DeleteKey | `--pending_days` | string | **Yes** | `--pending_days=7` (7-1096) |
| ShowKeyRotationStatus | `--key_id` | string | **Yes** | `--key_id=CHANGE_ME_KEY_ID` |

### CTS

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| ListTraces | `--trace_type` | string | **Yes** | `--trace_type=system` (system=管理事件, data=数据事件) |
| ListTraces | `--service_type` | string | No | `--service_type=KMS` |
| ListTraces | `--trace_name` | string | No | `--trace_name=DeleteKey` |
| ListTraces | `--resource_type` | string | No | `--resource_type=cmk` |
| ListTraces | `--from` / `--to` | string | No | `--from=2026-08-01T00:00:00Z` |
| ListTraces | `--limit` | int | No | `--limit=50` |

Common to all operations: `--cli-region` (required), `--project_id` (required by API but auto-filled
from the authenticated profile when omitted).

## Quality Reporting

This Skill integrates [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for execution quality
reporting. Every run automatically reports trace_id, status (success/biz_fail/sys_fail/cancel),
error code, cost, and masked input/output to the operations console.

### Integration

- **Python entry point:** wrap main logic with `quality_context` context manager:

  ```python
  from skill_quality_sdk import quality_context, QualityError

  with quality_context(skill_name="huawei-cloud-dew-key-management", skill_version="1.0.0") as q:
      q.input = {"action": "huawei_list_kms_keys", "region": "cn-north-4"}
      result = run_action(action, params)  # your implementation
      q.output = result
  ```

- **CLI-only Skill:** the SDK is vendored in `scripts/` for future Python wrapper use.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|---------|
| U | User input | U01 missing param, U03 no data found |
| C | Configuration | C01 missing AK/SK/env, C02 hcloud not authenticated |
| N | Network | N01 timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 version mismatch |
| P | Platform | P01 scheduler error, P02 resource insufficient |

Reporting is non-blocking and fails silently — it never interrupts the Skill main flow.
Disable via `SKILL_QUALITY_DISABLE=1` for local testing.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for CSMS/KMS/CTS
- `references/cli-installation-guide.md` — hcloud CLI installation and AK/SK + profile authentication
- `references/csms-usage.md` — CSMS usage guide (actions, rotation, policy rules)
- `references/kms-usage.md` — KMS usage guide (create/list/rotate/delete, blocking rules)
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/verification-method.md` — Verification method and acceptance checks
- `references/acceptance-criteria.md` — Acceptance criteria for the 10 huawei_* actions
- DEW Docs: https://support.huaweicloud.com/dew/
- API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/DEW/doc