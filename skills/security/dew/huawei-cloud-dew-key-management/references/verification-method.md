# Verification Method — huawei-cloud-dew-key-management

This document describes how to verify the skill end-to-end after installation.

## 1. Prerequisite checks

```bash
# hcloud installed and authenticated
hcloud --version
hcloud configure list          # profile must show a real accessKeyId

# DEW/CTS services reachable via CLI
hcloud CSMS --help > /dev/null && echo "CSMS OK"
hcloud KMS --help > /dev/null && echo "KMS OK"
hcloud CTS --help > /dev/null && echo "CTS OK"
```

## 2. Read-only verification (R3 — safe to run against any project)

```bash
REGION=cn-north-4

# 1) List secrets (metadata only)
hcloud CSMS ListSecrets --cli-region=$REGION --limit=10

# 2) Describe a secret (pick a secret name from step 1; metadata only)
hcloud CSMS ShowSecret --cli-region=$REGION --secret_name={secret_name}

# 3) List versions (no values)
hcloud CSMS ListSecretVersions --cli-region=$REGION --secret_name={secret_name} --limit=10

# 4) List KMS keys
hcloud KMS ListKeys --cli-region=$REGION --limit=10

# 5) Rotation analysis
hcloud CSMS ListSecrets --cli-region=$REGION

# 6) Key usage audit (requires CTS tracker; system traces = management events)
hcloud CTS ListTraces --cli-region=$REGION --trace_type=system --service_type=KMS --limit=10
```

**Pass criteria:** commands return JSON metadata; no secret value appears in any output;
exit code 0.

## 3. Write-operation verification (R2/R1 — requires explicit confirmation and a sandbox project)

Use a **dedicated sandbox project/account**; never run against production.

1. **huawei_create_kms_key (R2)**

   ```bash
   hcloud KMS CreateKey --cli-region=$REGION --key_alias=skill-verify-key \
     --key_description="huawei-cloud-dew-key-management skill verification"
   ```

   Verify: key appears in `hcloud KMS ListKeys`.

2. **huawei_enable_csms_secret_rotation (R2)** — on a test secret with a rotation function ARN:

   ```bash
   hcloud CSMS UpdateSecret --cli-region=$REGION --secret_name={test_secret} \
     --auto_rotation=true --rotation_period=30d
   ```

   Verify: `hcloud CSMS ShowSecret` shows `auto_rotation: true`.

3. **huawei_update_csms_secret_version (R1)**

   ```bash
   hcloud CSMS RotateSecret --cli-region=$REGION --secret_name={test_secret}
   ```

   Verify: a new version appears in `ListSecretVersions` with stage `SYSCURRENT`.

4. **huawei_delete_kms_key (R1, irreversible)**

   ```bash
   hcloud KMS DeleteKey --cli-region=$REGION --key_id={verify_key_id} --pending_days=7
   ```

   Verify: key enters `pending deletion` state; then cancel during the window:

   ```bash
   hcloud KMS CancelKeyDeletion --cli-region=$REGION --key_id={verify_key_id}
   ```

   Confirm the key is back to enabled and **clean up all test resources** afterwards.

## 4. Negative checks

- `hcloud CSMS DownloadSecretBlob ...` and `hcloud KMS DecryptData ...` must be **blocked**
  by the action policy (verify the agent refuses / the MCP safety policy rejects the call).
- Management commands without user confirmation must not execute (R1/R2 gate).
- `--help` parameter names must match the SKILL.md tables (KooCLI 7.2.12 baseline).