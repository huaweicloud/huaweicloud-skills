# Acceptance Criteria — huawei-cloud-ecs-passwordless-login

Criteria for a successful passwordless SSH configuration via COC.

## Authorization

- [ ] COC agency `ServiceAgencyForCOC` exists (created or already present)
- [ ] Agency trusts `op_svc_coc`
- [ ] All 4 required roles bound: IAM ReadOnlyAccess, RMS ReadOnlyAccess, DCS UserAccess, COCServiceAgencyPolicy
- [ ] HTTP 409 on CreateAgency handled gracefully (expected on repeat runs)

## Key Generation

- [ ] RSA 4096-bit key pair generated in `<temp_dir>/`
- [ ] Private key has 600 permissions
- [ ] Key comment set to `coc-temp-key` for later cleanup identification
- [ ] Fingerprint displayed to user; private key content never exposed

## COC Script

- [ ] Script `coc_ssh_key_setup` exists (reused or newly created)
- [ ] Script is type `SHELL` with `PUBLIC_KEY` parameter
- [ ] Script risk level is `LOW`
- [ ] Script body base64-encoded correctly

## Script Execution

- [ ] Target ECS instance identified by ID (resolved from IP if needed)
- [ ] `ExecuteScript` returns a valid `execute_uuid`
- [ ] `GetScriptJobInfo` polling shows `SUCCESS` within 2 minutes
- [ ] Execution output contains `KEY_DEPLOYED_SUCCESSFULLY`

## SSH Connectivity

- [ ] `ssh -i <temp_dir>/coc_ssh_key root@<EIP>` connects without password prompt
- [ ] Test command returns `SSH_OK`
- [ ] SSH connection string provided to user

## Security Cleanup

- [ ] Remote key removed from `authorized_keys` (via SSH or COC fallback)
- [ ] COC script deleted
- [ ] Local key pair files deleted
- [ ] Cleanup completes within the configured delay (default: 60s)
- [ ] Existing SSH sessions NOT affected — only new connections blocked
- [ ] If cleanup fails, fallback COC script handles remote key removal

## Error Cases

- [ ] 409 on CreateAgency → treated as success (agency exists)
- [ ] 409 on role binding → treated as success (role already bound)
- [ ] Script already exists → reused, no duplicate creation
- [ ] ECS IP not found → clear error with suggested troubleshooting
- [ ] SSH test fails → keys preserved for debugging, cleanup NOT triggered
- [ ] Cleanup SSH fails → COC cleanup script fallback invoked
- [ ] hcloud missing → user directed to cli-installation-guide.md
