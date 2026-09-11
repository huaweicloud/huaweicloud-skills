# KMS Usage Guide

KMS (Key Management Service) manages customer master keys (CMK). All management actions
are gated (R2/R1 preview + confirm). **Never decrypt inside the agent context.**

## Action reference

| huawei_* action | CLI command | Level |
| --------------- | ----------- | ----- |
| `huawei_list_kms_keys` | `hcloud KMS ListKeys --cli-region={region}` | R3 auto |
| `huawei_create_kms_key` | `hcloud KMS CreateKey --cli-region={region} --key_alias={alias}` | R2 confirm |
| `huawei_delete_kms_key` | `hcloud KMS DeleteKey --cli-region={region} --key_id={id} --pending_days={7..1096}` | R1 confirm, irreversible |
| `huawei_analyze_dew_rotation` (KMS side) | `hcloud KMS ShowKeyRotationStatus --cli-region={region} --key_id={id}` | R3 auto |

## Examples

List keys (metadata only):

```bash
hcloud KMS ListKeys --cli-region=cn-north-4 --key_state=2 --limit=50
```

Create a symmetric encryption key (R2 — confirm first):

```bash
hcloud KMS CreateKey --cli-region=cn-north-4 --key_alias=app-encryption-key \
  --key_description="Application data encryption" --key_spec=AES_256
```

Show key rotation status:

```bash
hcloud KMS ShowKeyRotationStatus --cli-region=cn-north-4 --key_id=CHANGE_ME_KEY_ID
```

Enable key rotation (not a huawei_* action — for reference):

```bash
hcloud KMS EnableKeyRotation --cli-region=cn-north-4 --key_id=CHANGE_ME_KEY_ID
```

## Key deletion — IRREVERSIBLE

```bash
hcloud KMS DeleteKey --cli-region=cn-north-4 --key_id=CHANGE_ME_KEY_ID --pending_days=7
```

- Schedules deletion after `--pending_days` (7-1096; typical 7-30 day window).
- Cancellable during the window: `hcloud KMS CancelKeyDeletion --cli-region=cn-north-4 --key_id={id}`
- **After the window passes, the key is permanently deleted and data encrypted with it is
  UNRECOVERABLE.** Always show this warning and require explicit confirmation (R1).

> Note: `hcloud KMS DeleteKey` maps to the *schedule-key-deletion* API
> (endpoint `POST /v1.0/{project_id}/kms/schedule-key-deletion`).

## Encrypt / decrypt policy

| Operation | Policy |
| --------- | ------ |
| `hcloud KMS ListKeys` | **ALLOWED** (metadata only) |
| `hcloud KMS ListKeyDetail` | **ALLOWED** (metadata only) |
| `hcloud KMS ShowKeyRotationStatus` | **ALLOWED** (metadata only) |
| `hcloud KMS CreateKey` | ALLOWED (R2 preview + confirm) |
| `hcloud KMS DeleteKey` (schedule deletion) | ALLOWED (R1 preview + confirm, irreversible warning) |
| `hcloud KMS EncryptData` | ALLOWED for approved automation only — prefer offline SDK encryption |
| `hcloud KMS DecryptData` | **BLOCKED** — use runtime injection / SDK in application runtime |
| `hcloud KMS CreateDatakey` (plaintext side) | **BLOCKED** in agent context — envelope encryption in application runtime |

Endpoint (verified): `POST /v1.0/{project_id}/kms/list-keys`,
`POST /v1.0/{project_id}/kms/create-key`,
`POST /v1.0/{project_id}/kms/schedule-key-deletion`,
`POST /v1.0/{project_id}/kms/get-key-rotation-status`.