# Verification Method — huawei-cloud-ecs-passwordless-login

Success verification criteria for each workflow step.

## Step 1: COC IAM Authorization

| Check | Method |
|--------|--------|
| Domain ID obtained | `hcloud IAM KeystoneListAuthDomains/v3` returns valid JSON with `domains` array |
| Agency exists or created | `CreateAgency/v3` returns 200 (created) or 409 (exists) |
| All 4 roles found | `KeystoneListPermissions/v3 --display_name="<role_name>"` returns a result for each: IAM ReadOnlyAccess, RMS ReadOnlyAccess, DCS UserAccess, COCServiceAgencyPolicy |
| All roles bound | `AssociateAgencyWithAllProjectsPermission/v3` returns 200 or 409 for each of the 4 roles |

## Step 2: SSH Key Pair Generation

| Check | Method |
|--------|--------|
| Private key exists | `ls -la <temp_dir>/coc_ssh_key` shows file with 600 permissions |
| Public key exists | `ls -la <temp_dir>/coc_ssh_key.pub` shows file |
| Fingerprint recorded | `ssh-keygen -lf <temp_dir>/coc_ssh_key` exits 0 and shows fingerprint |
| Private key never printed | Agent output does NOT contain private key content |

## Step 3: COC Script

| Check | Method |
|--------|--------|
| Script found or created | `ListScripts --name_like="coc_ssh_key_setup"` returns matching entry, or `CreateScript` returns 200 with `script_uuid` |
| Script has PUBLIC_KEY param | Script definition includes `PUBLIC_KEY` parameter |
| script_uuid stored | UUID is recorded for execution and cleanup |

## Step 4: Script Execution

| Check | Method |
|--------|--------|
| ECS ID resolved | If IP was provided, `NovaListServersDetails --ip="<EIP>"` finds matching instance |
| Execution started | `ExecuteScript` returns 200 with `execute_uuid` |
| Execution status polled | `GetScriptJobInfo --execute_uuid="<uuid>"` called every 5s until terminal state |
| Execution succeeded | Final status is `SUCCESS`; KEY_DEPLOYED_SUCCESSFULLY in output |

## Step 5: SSH Connection Test

| Check | Method |
|--------|--------|
| SSH connects without password | `ssh -i <temp_dir>/coc_ssh_key root@<EIP> "echo SSH_OK"` exits 0 |
| SSH_OK returned | Response contains `SSH_OK` |
| Connection string displayed | Agent shows user the SSH command |

## Step 6: Security Cleanup

| Check | Method |
|--------|--------|
| 60s timer started | Agent announces cleanup countdown and PID |
| Remote key removed | `sed -i '/coc-temp-key/d' /root/.ssh/authorized_keys` executed on target |
| COC script deleted | `DeleteScript --script_uuid="<uuid>"` exits 0 |
| Local keys deleted | `<temp_dir>/coc_ssh_key` and `.pub` no longer exist |
| Fallback ready | If SSH removal fails, COC cleanup script is created and executed |
| Existing sessions preserved | Agent confirms existing SSH sessions are NOT affected by authorization_keys change |
