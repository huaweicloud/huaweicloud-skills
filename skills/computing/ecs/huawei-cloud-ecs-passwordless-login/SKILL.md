---
name: huawei-cloud-ecs-passwordless-login
description: |
  Configure passwordless SSH login to Huawei Cloud ECS instances using COC (Cloud Operations Center). Automates IAM agency authorization, SSH key pair generation, COC script deployment to the target ECS, SSH connection testing, and automatic security cleanup after 60 seconds (removing keys from both local and remote).
  触发词: 免密登录, COC SSH, ECS key login, SSH key deployment, passwordless SSH
---

# Huawei Cloud ECS Passwordless Login

## Overview

Configure passwordless SSH login to Huawei Cloud ECS using COC (Cloud Operations Center) with a 7-step automated workflow:

1. **IAM Authorization** — Create the `ServiceAgencyForCOC` agency for COC service and bind 4 required roles; skip entirely if agency already exists (HTTP 409)
2. **Key Generation** — Generate a local RSA 4096-bit SSH key pair
3. **Script Creation** — Create or reuse a parameterized COC script that deploys the public key
4. **Script Execution** — Execute the script on the target ECS via COC
5. **SSH Test** — Verify passwordless SSH connection to the target ECS
6. **Persistent Connection** — Establish SSH ControlMaster so the agent can continue SSH access after keys are cleaned up
7. **Security Cleanup** — After 60 seconds, automatically remove keys from remote `authorized_keys`, delete the local key pair, and clean up the COC script

**Tool chain:** hcloud CLI (KooCLI) + local SSH tools. Deployment is handled through COC script execution only.

## Prerequisites

- hcloud CLI (KooCLI) installed and authenticated with AK/SK — see [CLI Installation Guide](references/cli-installation-guide.md)
- IAM user with sufficient permissions to create agencies and operate COC — see [IAM Policies](references/iam-policies.md)
- SSH client and `ssh-keygen` available locally
- Target ECS instance ID or elastic IP (the ECS must be in `ACTIVE` state)

### Security

- Never expose private key content in conversation or output
- Never log or persist private keys beyond the 60s window
- Cleanup is mandatory — if SSH test succeeds, keys MUST be removed within `cleanup_delay` seconds
- Removing the public key from `authorized_keys` only blocks **new** SSH connections; existing sessions are NOT interrupted
- If SSH test fails, preserve keys for debugging and do NOT trigger cleanup

## Workflow

Execute the numbered steps below in order. See **Core Commands** section for the exact command syntax to use at each step.

### 1. IAM Authorization

**One-time per-account setup.** Authorize COC to operate on your ECS instances.

1. **Get domain ID** — Call `KeystoneListAuthDomains` and extract the `id`.
2. **Create agency** — Call `CreateAgency` with name `ServiceAgencyForCOC` and trust domain `op_svc_coc`.
   - **HTTP 200** — New agency created. Record `agency.id`. Proceed to step 3.
   - **HTTP 409** — Agency already exists. **Skip the entire IAM phase (steps 3–4) and jump to Step 2 (Key Generation).**
3. **Find role IDs** — Call `KeystoneListPermissions` for each of the 4 roles: `IAM ReadOnlyAccess`, `RMS ReadOnlyAccess`, `DCS UserAccess`, `COCServiceAgencyPolicy`. If any role is not found, stop — the account may lack access.
4. **Bind roles** — Call `AssociateAgencyWithAllProjectsPermission` for each of the 4 role IDs.
   - **HTTP 200** — Bound successfully.
   - **HTTP 409** — Already bound, skip and continue.

### 2. Generate Local SSH Key Pair

Generate an RSA 4096-bit key pair. The comment `coc-temp-key` is the cleanup marker.

Record the key fingerprint. **Never display the private key content.**

### 3. Create or Reuse COC Script

1. **Check existing** — Call `ListScripts` with `--name_like="coc_ssh_key_setup"`. If found, record `script_uuid` and skip step 2.
2. **Create new** — Write a JSON file with the script content, then call `CreateScript --cli-jsonInput=<file>`. Use `--cli-jsonInput` (not inline `--content`) to avoid shell quoting issues with special characters in the script body. Record the returned `script_uuid`.

### 4. Execute Script on Target ECS

1. **Resolve instance** — If only an ECS IP was provided, call `NovaListServersDetails` to find the instance ID.
2. **Execute** — Write a JSON file with the public key embedded, then call `ExecuteScript --cli-jsonInput=<file>`. Same pattern as Step 3 to avoid shell quoting issues with the public key content. Record `execute_uuid`.
3. **Poll** — Call `GetScriptJobInfo` every 5 seconds until terminal status. Note: the API redacts `param_value` in the response for security; verify deployment by testing SSH in Step 5.
   | Status | Action |
   |--------|--------|
   | `RUNNING` | Wait 5s, poll again |
   | `SUCCESS` | Proceed to Step 5 |
   | `FAILED` / `TIMEOUT` | Report error, stop |

   Max 2 minutes (24 polls).

### 5. Test SSH Connection

Test passwordless SSH using the generated key.

- **`SSH_OK` returned** — Proceed to Step 6.
- **Connection fails** — Report error. **Stop here.** Preserve keys for debugging. Do NOT trigger cleanup.

### 6. Establish Persistent SSH Connection

Set up SSH ControlMaster so the agent can continue accessing the ECS after keys are removed in Step 7.

1. **Append SSH config** — Add a `Host <EIP>` block to `~/.ssh/config` with `ControlMaster auto`, `ControlPath /tmp/coc_ssh_%r@%h:%p`, and `ControlPersist <persist_timeout>`.
2. **Start master** — Run `ssh -N -f <EIP> -i <key>` to background a persistent master connection.
3. **Verify** — Run `ssh <EIP> "echo SSH_MUX_OK"` without a key file. If `SSH_MUX_OK` is returned, multiplexing works.

SSH config and socket **do not need cleanup** — config entries are harmless, sockets auto-expire with `ControlPersist`.

### 7. Security Cleanup

**Mandatory.** Start a background timer that fires after `cleanup_delay` seconds (default: 60):

1. Remove `coc-temp-key` line from remote `/root/.ssh/authorized_keys`
2. Delete the COC script via `DeleteScript`
3. Delete local key files from `<temp_dir>/`

**After cleanup**, the agent can still connect via `ssh <EIP>` — ControlMaster bypasses key authentication.

**Fallback**: If remote key removal via SSH fails, create and execute a one-shot COC script:

```bash
#!/bin/bash
set -e
sed -i '/coc-temp-key/d' /root/.ssh/authorized_keys
echo "KEY_REMOVED"
```

Create and execute this script with no parameters. Delete it immediately after execution completes.

## Core Commands

Placeholder values (see Parameters for per-OS resolution):

| Placeholder | Linux / macOS | Windows |
|-------------|---------------|---------|
| `<hcloud>` | `hcloud` | `hcloud` |
| `<temp_dir>` | `/tmp` | `$env:TEMP` |

```bash
# 1. Check/setup COC IAM authorization
<hcloud> IAM KeystoneListAuthDomains/v3
<hcloud> IAM CreateAgency/v3 \
  --agency.domain_id="<domain_id>" \
  --agency.name="ServiceAgencyForCOC" \
  --agency.trust_domain_name="op_svc_coc" \
  --agency.duration="FOREVER"
<hcloud> IAM KeystoneListPermissions/v3 \
  --display_name="<role_name>"
<hcloud> IAM AssociateAgencyWithAllProjectsPermission/v3 \
  --agency_id="<agency_id>" --domain_id="<domain_id>" --role_id="<role_id>"

# 2. Generate local SSH key pair
ssh-keygen -t rsa -b 4096 -f <temp_dir>/coc_ssh_key -N "" -C "coc-temp-key"
ssh-keygen -lf <temp_dir>/coc_ssh_key  # record fingerprint

# 3. Check for existing COC script
<hcloud> COC ListScripts --limit=100 --name_like="coc_ssh_key_setup"
# If not found, create a JSON file and use --cli-jsonInput:
cat > <temp_dir>/coc_create.json << 'JSONEOF'
{
  "body": {
    "name": "coc_ssh_key_setup",
    "type": "SHELL",
    "description": "Deploy SSH public key for passwordless login",
    "content": "#!/bin/bash\nset -e\nmkdir -p /root/.ssh && chmod 700 /root/.ssh\necho $PUBLIC_KEY >> /root/.ssh/authorized_keys\nchmod 600 /root/.ssh/authorized_keys\necho KEY_DEPLOYED_SUCCESSFULLY",
    "properties": {
      "risk_level": "LOW",
      "version": "1.0.0"
    },
    "script_params": [
      {
        "param_name": "PUBLIC_KEY",
        "param_description": "SSH public key to deploy",
        "param_value": "",
        "sensitive": false
      }
    ]
  }
}
JSONEOF
<hcloud> COC CreateScript --cli-jsonInput=<temp_dir>/coc_create.json

# 4. Execute script on target ECS, replace with actual value
cat > <temp_dir>/coc_execute.json << 'JSONEOF'
{
  "path": {"script_uuid": "<script_uuid>"},
  "body": {
    "execute_batches": [{
      "batch_index": 1,
      "rotation_strategy": "CONTINUE",
      "target_instances": [{
        "region_id": "<region>",
        "resource_id": "<instance_id>"
      }]
    }],
    "execute_param": {
      "execute_user": "root",
      "success_rate": 100,
      "timeout": 120,
      "script_params": [{
        "param_name": "PUBLIC_KEY",
        "param_value": pubkey
      }]
    }
  }
}
JSONEOF
<hcloud> COC ExecuteScript --cli-jsonInput=<temp_dir>/coc_execute.json

# Poll execution status (note: GetScriptJobInfo redacts param_value for security; check SSH directly to verify)
<hcloud> COC GetScriptJobInfo --execute_uuid=<execute_uuid>

# 5. Test SSH connection
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ConnectTimeout=10 -i <temp_dir>/coc_ssh_key root@<EIP> "echo SSH_OK"

# 6. Establish persistent SSH connection (ControlMaster multiplexing)
cat >> ~/.ssh/config << 'EOF'

Host <EIP>
  User <ssh_user>
  ControlMaster auto
  ControlPath /tmp/coc_ssh_%r@%h:%p
  ControlPersist <persist_timeout>
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
EOF
ssh -N -f <EIP> -i <temp_dir>/coc_ssh_key && echo "MASTER_CONNECTED"
ssh <EIP> "echo SSH_MUX_OK"  # verify multiplexing works

# 7. Security cleanup (background, survives parent shell exit via nohup + disown)
nohup bash -c '
sleep <cleanup_delay>
# Remove public key from remote
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ConnectTimeout=5 -i <temp_dir>/coc_ssh_key root@<EIP> \
  "sed -i \"/coc-temp-key/d\" /root/.ssh/authorized_keys" 2>/dev/null || true
# Delete COC script
<hcloud> COC DeleteScript --script_uuid="<script_uuid>" 2>/dev/null || true
# Delete local keys
rm -f <temp_dir>/coc_ssh_key <temp_dir>/coc_ssh_key.pub
echo "COC SSH keys cleaned up. Existing SSH sessions remain unaffected."
' > <temp_dir>/coc_cleanup.log 2>&1 &
disown
echo "Cleanup scheduled in <cleanup_delay>s (PID: $!, log: <temp_dir>/coc_cleanup.log)"
```

## Parameters

| Parameter | Required | Default | Constraint |
|-----------|----------|---------|------------|
| `ecs_instance_id` | Conditional | None | ECS instance UUID; required if `ecs_ip` is not provided |
| `ecs_ip` | Conditional | None | ECS elastic IPv4 address; required if `ecs_instance_id` is not provided |
| `region` | Yes | `cn-north-4` | Region where the ECS and COC reside. Must match the ECS's region |
| `ssh_user` | No | `root` | SSH username on the target ECS |
| `cleanup_delay` | No | `60` | Seconds to wait before automatic key cleanup (min 10, max 300) |
| `persist_timeout` | No | `3600` | Seconds to keep ControlMaster alive after all sessions close (min 60, max 86400) |

## Output Format

At each step, report progress in a structured manner:

| Step | Output |
|------|--------|
| 1. Authorization | Agency status (created / already exists), roles bound count (4/4) |
| 2. Key Generation | Key fingerprint, key file paths |
| 3. Script | Script name, action (created / reused), script_uuid |
| 4. Execution | execute_uuid, polling status, final result |
| 5. SSH Test | Connection result, SSH command string |
| 6. Persistent Connection | ControlMaster status, multiplex verification, SSH alias `<EIP>` |
| 7. Cleanup | Timer PID, countdown notification, cleanup confirmation |

## Verification

Verify the workflow step by step:

1. **Authorization** — `CreateAgency` returns 200 → all 4 roles bound (200 or 409 each); returns 409 → entire IAM phase skipped (agency already authorized from prior run)
2. **Key Generation** — Key pair files exist in `<temp_dir>/` with correct permissions
3. **Script** — `coc_ssh_key_setup` exists with `PUBLIC_KEY` parameter and valid `script_uuid`
4. **Execution** — `GetScriptJobInfo` shows `SUCCESS` within 2 minutes
5. **SSH Test** — `ssh` connects without password prompt; test command returns `SSH_OK`
6. **Persistent Connection** — SSH config appended, `ssh -N -f <EIP>` starts master, `ssh <EIP> "echo SSH_MUX_OK"` succeeds
7. **Cleanup** — Remote key removed, COC script deleted, local key files deleted; `ssh <EIP>` still connects via ControlMaster

See [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md) for detailed checklists.

## Best Practices

- IAM authorization is a **one-time per-account** setup — if `CreateAgency` returns 409, the entire IAM phase (agency + role binding) is already complete and should be skipped entirely
- Use the `--name_like` filter in `ListScripts` to avoid creating duplicate scripts
- Always test the SSH connection before starting the cleanup timer
- If SSH fails, keep keys on disk for debugging — do NOT clean up automatically
- The cleanup timer runs in a background subshell; killing the process before cleanup completes leaves keys in place
- After key cleanup, the agent can still SSH via `ssh <EIP>` — ControlMaster bypasses key authentication
- Use `-o UserKnownHostsFile=/dev/null` to avoid polluting the local `known_hosts` file
- The SSH key comment `coc-temp-key` is the marker used by `sed` for cleanup — do not change it
- COC script execution is limited to 200 hosts per execution and 10 hosts per batch
- SSH config entries persist after cleanup as harmless dead entries; they can be removed later if desired

## Reference Documents

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | Install and configure hcloud CLI and SSH tools |
| [IAM Policies](references/iam-policies.md) | Required IAM permissions, agency setup, and error handling |
| [Verification Method](references/verification-method.md) | Step-by-step verification per workflow step |
| [Acceptance Criteria](references/acceptance-criteria.md) | Full end-to-end acceptance checklist |

## Notes

- All `hcloud` commands use the default region from the CLI profile (no `--cli-region`). Ensure your profile is configured with the correct region where your ECS and COC reside.
- The COC script is created via `--cli-jsonInput` with a JSON file, not inline `--content="..."` — inline quoting causes parsing errors with shell special characters in the script body
- The COC script is **parameterized** with `PUBLIC_KEY` — it persists across invocations and can deploy different keys
- If the COC script already exists from a previous run, it is **reused** rather than recreated
- The cleanup uses `nohup bash -c '...' &` + `disown` to survive parent shell exit; output is logged to `<temp_dir>/coc_cleanup.log` for verification. The old `(sleep N && ...) &` pattern loses stdout when the parent shell exits in non-interactive mode
- Private keys are stored in `<temp_dir>` and should never be committed to VCS
- The `sed` cleanup target `coc-temp-key` matches the key comment set during `ssh-keygen`
- After cleanup, use `ssh <EIP>` (no key file needed) — ControlMaster socket handles authentication
- The SSH config entry is appended to `~/.ssh/config` as a simple `Host` block
- ControlMaster socket is stored at `/tmp/coc_ssh_%r@%h:%p` and auto-cleaned when the master process exits
