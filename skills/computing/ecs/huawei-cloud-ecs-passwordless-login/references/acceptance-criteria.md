# Acceptance Criteria — huawei-cloud-ecs-passwordless-login

Criteria for a successful passwordless SSH configuration via COC.

## Authorization

- [ ] COC agency `ServiceAgencyForCOC` exists (created or already present)
- [ ] Agency trusts `op_svc_coc`
- [ ] All 4 required roles bound: IAM ReadOnlyAccess, RMS ReadOnlyAccess, DCS UserAccess, COCServiceAgencyPolicy
- [ ] HTTP 409 on CreateAgency handled gracefully (expected on repeat runs)
- [ ] IAM/agency commands pinned to a COC-supported region (`coc_region` = `cn-north-4` or `ap-southeast-3`)

## Key Generation

- [ ] **Ed25519** key pair generated in `<temp_dir>/` (`ssh-keygen -t ed25519`)
- [ ] Private key has 600 permissions
- [ ] Key comment set to `coc-temp-key` for later cleanup identification
- [ ] Fingerprint displayed to user; private key content never exposed
- [ ] Other key types (RSA, ECDSA, DSA) rejected as unsupported

## COC Script

- [ ] Script `coc_ssh_key_setup` exists (reused or newly created)
- [ ] Script is type `SHELL` with `PUBLIC_KEY` parameter
- [ ] Script risk level is `LOW`
- [ ] Script body base64-encoded correctly

## Script Execution

- [ ] All batch targets resolved to instance IDs (IPs via `COC ListResources`)
- [ ] Each target's **actual region confirmed** via `COC ListResources` (returned `region_id`, no region known in advance)
- [ ] Execution payload `target_instances[].region_id` set per-target to the confirmed ECS region; batch split into ≤10 hosts per `batch_index`
- [ ] COC script list/create/execute/poll/delete commands pinned to `coc_region`
- [ ] `ExecuteScript` returns a valid `execute_uuid`
- [ ] `GetScriptJobInfo` polling shows `SUCCESS` within 2 minutes
- [ ] Execution output contains `KEY_DEPLOYED_SUCCESSFULLY` for each target

## SSH Connectivity

- [ ] Non-root `ssh_user` supported: key deployed to `~<ssh_user>/.ssh/authorized_keys` (not just `/root`)
- [ ] Each target `ssh -i <temp_dir>/coc_ssh_key <ssh_user>@<EIP>` connects without password prompt
- [ ] Test command returns `SSH_OK` for every target
- [ ] SSH connection string provided to user for each target

## Security Cleanup

- [ ] Remote key removed from `authorized_keys` on **every** target (via SSH or COC fallback)
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
- [ ] SSH test fails on any target → keys preserved for debugging, cleanup NOT triggered for the whole batch
- [ ] Cleanup SSH fails → COC cleanup script fallback invoked (targeting only failed hosts)
- [ ] hcloud missing → user directed to cli-installation-guide.md
