# CSMS Usage Guide

CSMS (Cloud Secret Management Service) manages secrets. **This skill only touches metadata —
secret values are never fetched into agent context.**

## Action reference

| huawei_* action | CLI command | Level |
| --------------- | ----------- | ----- |
| `huawei_list_csms_secrets` | `hcloud CSMS ListSecrets --cli-region={region}` | R3 auto |
| `huawei_describe_csms_secret` | `hcloud CSMS ShowSecret --cli-region={region} --secret_name={name}` | R3 auto |
| `huawei_list_csms_secret_versions` | `hcloud CSMS ListSecretVersions --cli-region={region} --secret_name={name}` | R3 auto |
| `huawei_enable_csms_secret_rotation` | `hcloud CSMS UpdateSecret --cli-region={region} --secret_name={name} --auto_rotation=true --rotation_period=30d` | R2 confirm |
| `huawei_update_csms_secret_version` | `hcloud CSMS RotateSecret --cli-region={region} --secret_name={name}` | R1 confirm |

## Examples

List secrets (metadata only):

```bash
hcloud CSMS ListSecrets --cli-region=cn-north-4 --limit=50
```

Describe a secret (rotation config, KMS key, status — no value):

```bash
hcloud CSMS ShowSecret --cli-region=cn-north-4 --secret_name=prod-db-password
```

List versions and stages (no values):

```bash
hcloud CSMS ListSecretVersions --cli-region=cn-north-4 --secret_name=prod-db-password
```

Enable automatic rotation (R2 — confirm first):

```bash
hcloud CSMS UpdateSecret --cli-region=cn-north-4 --secret_name=prod-db-password \
  --auto_rotation=true --rotation_period=30d --rotation_func_urn=urn:fss:cn-north-4:xxx:function:default:rotate
```

Manually rotate the secret version immediately (R1 — confirm first; new value is generated
in the background, never passes through the agent):

```bash
hcloud CSMS RotateSecret --cli-region=cn-north-4 --secret_name=prod-db-password
```

Store a caller-supplied new value (approved automation only — read via stdin, never echo):

```bash
read -s -p "new secret value: " NEW_VALUE
hcloud CSMS CreateSecretVersion --cli-region=cn-north-4 --secret_name=prod-db-password \
  --secret_string="${NEW_VALUE}"
unset NEW_VALUE
```

## Runtime injection (consuming a value safely)

Never fetch values into the agent. Use the MCP proxy resolve pattern:

```text
{{resolve:csms:secret-id:SecretString:key}}
```

Terraform reference:

```hcl
data "huaweicloud_csms_secret" "db" {
  secret_name = "prod-db-password"
}
# Use: data.huaweicloud_csms_secret.db.secret_string
```

## Rotation

- Enable automatic rotation: `hcloud CSMS UpdateSecret --secret_name={name} --auto_rotation=true --rotation_period={days}` (R2)
- Rotation function ARN: provide a FuncGraph function that generates the new secret value
- Immediate manual rotation: `hcloud CSMS RotateSecret --secret_name={name}` (R1)
- Recommended `rotation_period`: ≤ 90 days

## Policy rules

| Operation | Policy |
| --------- | ------ |
| `hcloud CSMS ListSecrets` | **ALLOWED** (metadata only) |
| `hcloud CSMS ShowSecret` | **ALLOWED** (metadata only) |
| `hcloud CSMS ListSecretVersions` | **ALLOWED** (metadata only) |
| `hcloud CSMS UpdateSecret` | ALLOWED (R2 preview + confirm) |
| `hcloud CSMS RotateSecret` | ALLOWED (R1 preview + confirm) |
| `hcloud CSMS DownloadSecretBlob` | **BLOCKED** — use runtime injection |
| `hcloud CSMS ShowSecretVersion` (value field) | **BLOCKED** — never render secret values |
| `hcloud CSMS CreateSecretReference` / value-based reads | **BLOCKED** |

Endpoint (verified): `GET /v1/{project_id}/secrets`, `GET /v1/{project_id}/secrets/{secret_name}`,
`GET /v1/{project_id}/secrets/{secret_name}/versions`,
`PUT /v1/{project_id}/secrets/{secret_name}`,
`POST /v1/{project_id}/secrets/{secret_name}/rotate`.