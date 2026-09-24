# Verification Method — huawei-cloud-ecs-passwordless-login

Success verification criteria for each workflow step.

## Step 1: COC IAM Authorization

> All IAM checks here run against the COC-supported region (`coc_region`).

| Check | Method |
|--------|--------|
| Domain ID obtained | `hcloud IAM KeystoneListAuthDomains/v3 --cli-region=<coc_region>` returns valid JSON with `domains` array |
| Agency exists or created | `CreateAgency/v3 --cli-region=<coc_region>` returns 200 (created) or 409 (exists) |
| All 4 roles found | `KeystoneListPermissions/v3 --cli-region=<coc_region> --display_name="<role_name>"` returns a result for each: IAM ReadOnlyAccess, RMS ReadOnlyAccess, DCS UserAccess, COCServiceAgencyPolicy |
| All roles bound | `AssociateAgencyWithAllProjectsPermission/v3 --cli-region=<coc_region>` returns 200 or 409 for each of the 4 roles |

## Step 2: SSH Key Pair Generation

| Check | Method |
|--------|--------|
| Private key exists | `ls -la <temp_dir>/coc_ssh_key` shows file with 600 permissions (Ed25519, no passphrase) |
| Public key exists | `ls -la <temp_dir>/coc_ssh_key.pub` shows file |
| Fingerprint recorded | `ssh-keygen -lf <temp_dir>/coc_ssh_key` exits 0 and shows fingerprint |
| Ed25519 key type | `ssh-keygen -lf <temp_dir>/coc_ssh_key.pub` shows `SSH` or `ED25519` type (not RSA/ECDSA/DSA) |
| Private key never printed | Agent output does NOT contain private key content |

## Step 3: COC Script

| Check | Method |
|--------|--------|
| Script found or created | `ListScripts --cli-region=<coc_region> --name_like="coc_ssh_key_setup"` returns matching entry, or `CreateScript --cli-region=<coc_region>` returns 200 with `script_uuid` |
| Script has PUBLIC_KEY param | Script definition includes `PUBLIC_KEY` parameter |
| PUBLIC_KEY is sensitive | Script definition marks `PUBLIC_KEY.sensitive` as `true` (redacted from job responses/logs) |
| script_uuid stored | UUID is recorded for execution and cleanup |

## Step 4: Script Execution

| Check | Method |
|--------|--------|
| All IDs resolved | For each batch entry, `COC ListResources --cli-region=<coc_region> --provider=ecs --type=cloudservers` resolves the IP/ID to a matching resource (no ECS region needed in advance) |
| Region confirmed per target | Each target's actual `region_id` recorded from the `ListResources` response; mixed-region batches supported |
| Batch split correctly | Targets grouped into `execute_batches` of ≤10 hosts each; `region_id` set per target |
| Execution started | `ExecuteScript --cli-region=<coc_region>` returns 200 with `execute_uuid` |
| Execution status polled | `GetScriptJobInfo --cli-region=<coc_region> --execute_uuid="<uuid>"` called every 5s until terminal state |
| Execution succeeded | Final status is `SUCCESS`; per-target `KEY_DEPLOYED_SUCCESSFULLY` in output |

## Step 5: SSH Connection Test

| Check | Method |
|--------|--------|
| SSH connects without password (each target) | `ssh -i <temp_dir>/coc_ssh_key <ssh_user>@<EIP> "echo SSH_OK"` exits 0 for every EIP |
| SSH_OK returned | Each response contains `SSH_OK` |
| Connection string displayed | Agent shows user the SSH command for each target |

## Step 6: Security Cleanup

| Check | Method |
|--------|--------|
| 60s timer started | Agent announces cleanup countdown and PID |
| Remote key removed (each target) | `sed -i '/coc-temp-key/d' ~<ssh_user>/.ssh/authorized_keys` executed on every target |
| COC script deleted | `DeleteScript --cli-region=<coc_region> --script_uuid="<uuid>"` exits 0 |
| Local keys deleted | `<temp_dir>/coc_ssh_key` and `.pub` no longer exist |
| Fallback ready | If SSH removal fails, COC cleanup script is created and executed for the failed targets only |
| Existing sessions preserved | Agent confirms existing SSH sessions are NOT affected by authorization_keys change |
