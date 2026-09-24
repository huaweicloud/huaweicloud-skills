---
name: huawei-cloud-ecs-passwordless-login
description: |
  Configure passwordless SSH login to Huawei Cloud ECS instances using COC (Cloud Operations Center). Automates IAM agency authorization, SSH key pair generation, COC script deployment to one or many target ECS instances (batch), SSH connection testing, and automatic security cleanup after 60 seconds (removing keys from both local and remote).
  触发词: 免密登录, COC SSH, ECS key login, SSH key deployment, passwordless SSH
---

# Huawei Cloud ECS Passwordless Login

## Overview

Configure passwordless SSH login to Huawei Cloud ECS using COC (Cloud Operations Center) with a 7-step automated workflow:

1. **IAM Authorization** — Create the `ServiceAgencyForCOC` agency for COC service and bind 4 required roles; skip entirely if agency already exists (HTTP 409)
2. **Key Generation** — Generate a local **Ed25519** SSH key pair
3. **Script Creation** — Create or reuse a parameterized COC script that deploys the public key
4. **Script Execution** — Execute the script on one or many target ECS instances via COC (batch; each target's region and resource_id are resolved via the COC CLI `ListResources`)
5. **SSH Test** — Verify passwordless SSH connection to every target ECS
6. **Persistent Connection** — Establish SSH ControlMaster so the agent can continue SSH access after keys are cleaned up
7. **Security Cleanup** — After 60 seconds, automatically remove keys from remote `authorized_keys`, delete the local key pair, and clean up the COC script

**Tool chain:** hcloud CLI (KooCLI) + local SSH tools. Deployment is handled through COC script execution only.

> **Region model**: COC is a **global-level service** supporting only `cn-north-4` (China site) and `ap-southeast-3` (International site). Target ECS instances may live in different regions (batch). Use `coc_region` for all COC/IAM API calls and for target resolution via `COC ListResources` — target resolution never needs the ECS region in advance; each target's actual region is returned by the `ListResources` response. See **Notes** for details.

## Prerequisites

- hcloud CLI (KooCLI) installed and authenticated with AK/SK — see [CLI Installation Guide](references/cli-installation-guide.md)
- IAM user with sufficient permissions to create agencies and operate COC — see [IAM Policies](references/iam-policies.md)
- SSH client and `ssh-keygen` available locally
- Target ECS instance ID(s) or elastic IP(s) as comma-separated lists (each ECS must be in `ACTIVE` state)
- **ECS pre-installed uniagent** — COC script execution depends on the uniagent agent pre-installed on ECS. Check uniagent status via `hcloud COC ListResources` command, inspect the `agent_state` field to confirm the agent is running properly

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

> All IAM calls in this step run against the **COC-supported region** (`coc_region`): `cn-north-4` (China) or `ap-southeast-3` (International).

1. **Get domain ID** — Call `KeystoneListAuthDomains` and extract the `id`.
2. **Create agency** — Call `CreateAgency` with name `ServiceAgencyForCOC` and trust domain `op_svc_coc`.
   - **HTTP 200** — New agency created. Record `agency.id`. Proceed to step 3.
   - **HTTP 409** — Agency already exists. **Skip the entire IAM phase (steps 3–4) and jump to Step 2 (Key Generation).**
3. **Find role IDs** — Call `KeystoneListPermissions` for each of the 4 roles: `IAM ReadOnlyAccess`, `RMS ReadOnlyAccess`, `DCS UserAccess`, `COCServiceAgencyPolicy`. If any role is not found, stop — the account may lack access.
4. **Bind roles** — Call `AssociateAgencyWithAllProjectsPermission` for each of the 4 role IDs.
   - **HTTP 200** — Bound successfully.
   - **HTTP 409** — Already bound, skip and continue.

### 2. Generate Local SSH Key Pair

Generate an **Ed25519** key pair. The comment `coc-temp-key` is the cleanup marker. **Only Ed25519 keys are supported — RSA, ECDSA, and DSA key types are NOT supported**; do not attempt to generate or deploy them, as they are incompatible with this skill.

Record the key fingerprint. **Never display the private key content.**

### 3. Create or Reuse COC Script

1. **Check existing** — Call `ListScripts --cli-region=<coc_region>` with `--name_like="coc_ssh_key_setup"`. If found, record `script_uuid` and skip step 2.
2. **Create new** — Write a JSON file with the script content, then call `CreateScript --cli-region=<coc_region> --cli-jsonInput=<file>`. Use `--cli-jsonInput` (not inline `--content`) to avoid shell quoting issues with special characters in the script body. Record the returned `script_uuid`.

### 4. Execute Script on Target ECS

Executes the deploy script across the batch of target ECS instances. COC supports **up to 200 hosts per execution and 10 hosts per batch** (`batch_index`/`rotation_strategy`); split targets into batches of ≤10 accordingly.

1. **Resolve targets & confirm regions** — For each entry in `ecs_instance_id` / `ecs_ip`, call `COC ListResources --cli-region=<coc_region> --provider=ecs --type=cloudservers` to resolve the entry to an ECS resource. **`ListResources` only requires `coc_region` — it does NOT need the ECS's region in advance**; the response returns each resource's `region_id` and `resource_id` (and its IPs in `properties.addresses`). Record a `(region_id, resource_id)` pair per target. Targets may span multiple ECS regions.
   - **By resource ID** — Pass `--resource_id_list.N="<instance_id>"` for an ID entry. The exact-match `resource_id` returned is the value to use in the COC execution payload.
   - **By IP** — Always pass `--ip_list.N="<EIP>"` for an IP entry. `--ip_list` matches exactly. For each returned resource, verify `properties.addresses[].addr` matches the queried `<EIP>` before recording the target:
     - **Exact match** — Record the `(region_id, resource_id)` pair and proceed.
     - **No match / no resource returned** — Report the mismatch and **skip / stop** for that entry. Do **not** silently fall back to a different IP, as the script would run against the wrong instance.
2. **Execute** — Write a JSON file with the public key embedded and all resolved target pairs grouped into batches, then call `ExecuteScript --cli-region=<coc_region> --cli-jsonInput=<file>`. Same pattern as Step 3 to avoid shell quoting issues with the public key content. Record `execute_uuid`.
3. **Poll** — Call `GetScriptJobInfo --cli-region=<coc_region>` every 5 seconds until terminal status. Note: the API redacts `param_value` in the response for security; verify deployment by testing SSH in Step 5.
   | Status | Action |
   |--------|--------|
   | `RUNNING` | Wait 5s, poll again |
   | `SUCCESS` | Proceed to Step 5 |
   | `FAILED` / `TIMEOUT` | Report per-target errors, stop |

   Max 2 minutes (24 polls).

### 5. Test SSH Connection

Test passwordless SSH using the generated key — **for every target ECS**:

- **All targets return `SSH_OK`** — Proceed to Step 6.
- **Any target fails** — Report the failing target(s). **Stop here.** Preserve keys for debugging. Do NOT trigger cleanup.

### 6. Establish Persistent SSH Connection

Set up SSH ControlMaster so the agent can continue accessing **every target ECS** after keys are removed in Step 7.

1. **Append SSH config** — For each target, add a `Host <EIP>` block to `~/.ssh/config` with `ControlMaster auto`, `ControlPath /tmp/coc_ssh_%r@%h:%p`, and `ControlPersist <persist_timeout>`.
2. **Start master** — For each target, run `ssh -N -f <ssh_user>@<EIP> -i <key>` to background a persistent master connection.
3. **Verify** — For each target, run `ssh <ssh_user>@<EIP> "echo SSH_MUX_OK"` without a key file. If `SSH_MUX_OK` is returned, multiplexing works.

SSH config and socket **do not need cleanup** — config entries are harmless, sockets auto-expire with `ControlPersist`.

### 7. Security Cleanup

**Mandatory.** Start a background timer that fires after `cleanup_delay` seconds (default: 60):

1. Remove `coc-temp-key` line from remote `~<ssh_user>/.ssh/authorized_keys` **on every target**
2. Delete the COC script via `DeleteScript --cli-region=<coc_region>`
3. Delete local key files from `<temp_dir>/`

**After cleanup**, the agent can still connect via `ssh <EIP>` to any target — ControlMaster bypasses key authentication.

**Fallback**: If remote key removal via SSH fails for any target, create and execute a one-shot COC script (as a batch, targeting only the failed hosts):

```bash
#!/bin/bash
set -e
HOME_DIR=$(eval echo ~$SSH_USER)
sed -i '/coc-temp-key/d' "$HOME_DIR/.ssh/authorized_keys"
echo "KEY_REMOVED"
```

Create and execute this script as a batch (only the failed hosts, using each host's resolved region) with the `SSH_USER` parameter set to `<ssh_user>`. Delete it immediately after execution completes.

## Core Commands

Placeholder values (see Parameters for per-OS resolution):

| Placeholder  | Linux / macOS | Windows     |
| ------------ | ------------- | ----------- |
| `<temp_dir>` | `/tmp`        | `$env:TEMP` |

```bash
# 1. Check/setup COC IAM authorization
# IAM is regional in hcloud; the agency must be created in the COC-supported region (coc_region)
hcloud IAM KeystoneListAuthDomains/v3 --cli-region=<coc_region>
hcloud IAM CreateAgency/v3 \
  --cli-region=<coc_region> \
  --agency.domain_id="<domain_id>" \
  --agency.name="ServiceAgencyForCOC" \
  --agency.trust_domain_name="op_svc_coc" \
  --agency.duration="FOREVER"
hcloud IAM KeystoneListPermissions/v3 \
  --cli-region=<coc_region> \
  --display_name="<role_name>"
hcloud IAM AssociateAgencyWithAllProjectsPermission/v3 \
  --cli-region=<coc_region> \
  --agency_id="<agency_id>" --domain_id="<domain_id>" --role_id="<role_id>"

# 2. Generate local SSH key pair (Ed25519 only)
ssh-keygen -t ed25519 -f <temp_dir>/coc_ssh_key -N "" -C "coc-temp-key"
ssh-keygen -lf <temp_dir>/coc_ssh_key  # record fingerprint

# 3. Check for existing COC script
# COC API calls always target the COC-supported region (coc_region)
hcloud COC ListScripts --cli-region=<coc_region> --limit=100 --name_like="coc_ssh_key_setup"
# If not found, create a JSON file and use --cli-jsonInput:
cat > <temp_dir>/coc_create.json << 'JSONEOF'
{
  "body": {
    "name": "coc_ssh_key_setup",
    "type": "SHELL",
    "description": "Deploy SSH public key for passwordless login",
    "content": "#!/bin/bash\nset -e\nHOME_DIR=$(eval echo ~$SSH_USER)\nmkdir -p \"$HOME_DIR/.ssh\" && chmod 700 \"$HOME_DIR/.ssh\"\necho $PUBLIC_KEY >> \"$HOME_DIR/.ssh/authorized_keys\"\nchmod 600 \"$HOME_DIR/.ssh/authorized_keys\"\necho KEY_DEPLOYED_SUCCESSFULLY",
    "properties": {
      "risk_level": "LOW",
      "version": "1.0.0"
    },
    "script_params": [
      {
        "param_name": "PUBLIC_KEY",
        "param_description": "SSH public key to deploy",
        "param_value": "",
        "sensitive": true
      },
      {
        "param_name": "SSH_USER",
        "param_description": "Target SSH username on the ECS",
        "param_value": "",
        "sensitive": false
      }
    ]
  }
}
JSONEOF
hcloud COC CreateScript --cli-region=<coc_region> --cli-jsonInput=<temp_dir>/coc_create.json

# 4. Resolve batch targets & confirm each region, then execute script
# ecs_instance_id / ecs_ip are comma-separated lists. Do NOT assume a single region;
# COC ListResources resolves each entry (IP or ID) WITHOUT needing the ECS region in advance,
# and returns each resource's region_id and resource_id. Always target the coc_region endpoint.
hcloud COC ListResources --cli-region=<coc_region> --provider=ecs --type=cloudservers --limit=100 \
  --resource_id_list.1="<instance_id>"                       # for an ID entry (exact match)
hcloud COC ListResources --cli-region=<coc_region> --provider=ecs --type=cloudservers --limit=100 \
  --ip_list.1="<EIP>"                                        # for an IP entry (exact list match)

# Always verify the returned resource's properties.addresses[].addr exactly equals <EIP>
# before recording the target; otherwise the script may run against the wrong instance.
# Extract per resource: region_id, resource_id, and properties.addresses[].addr
#   RESULT=$(hcloud COC ListResources ... --cli-json-filter="data[]")
# Record (region_id, resource_id) pair per target; group into batches of <=10 hosts each.
cat > <temp_dir>/coc_execute.json << 'JSONEOF'
{
  "path": {"script_uuid": "<script_uuid>"},
  "body": {
    "execute_batches": [
      {
        "batch_index": 1,
        "rotation_strategy": "CONTINUE",
        "target_instances": [
          {"region_id": "<target1_region>", "resource_id": "<target1_id>"},
          {"region_id": "<target2_region>", "resource_id": "<target2_id>"}
        ]
      },
      {
        "batch_index": 2,
        "rotation_strategy": "CONTINUE",
        "target_instances": [
          {"region_id": "<target3_region>", "resource_id": "<target3_id>"}
        ]
      }
    ],
    "execute_param": {
      "execute_user": "root",
      "success_rate": 100,
      "timeout": 120,
      "script_params": [{
        "param_name": "PUBLIC_KEY",
        "param_value": pubkey
      },
      {
        "param_name": "SSH_USER",
        "param_value": "<ssh_user>"
      }]
    }
  }
}
JSONEOF
hcloud COC ExecuteScript --cli-region=<coc_region> --cli-jsonInput=<temp_dir>/coc_execute.json

# Poll execution status (note: GetScriptJobInfo redacts param_value for security; check SSH directly to verify)
hcloud COC GetScriptJobInfo --cli-region=<coc_region> --execute_uuid=<execute_uuid>

# 5. Test SSH connection (repeat for every target EIP)
for eip in <EIP1> <EIP2> <EIP3>; do
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 -i <temp_dir>/coc_ssh_key <ssh_user>@$eip "echo SSH_OK"
done

# 6. Establish persistent SSH connection (ControlMaster multiplexing, one per target)
for eip in <EIP1> <EIP2> <EIP3>; do
  cat >> ~/.ssh/config << EOF

Host $eip
  User <ssh_user>
  ControlMaster auto
  ControlPath /tmp/coc_ssh_%r@%h:%p
  ControlPersist <persist_timeout>
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
EOF
  ssh -N -f <ssh_user>@$eip -i <temp_dir>/coc_ssh_key && echo "MASTER_CONNECTED $eip"
  ssh <ssh_user>@$eip "echo SSH_MUX_OK"  # verify multiplexing works
done

# 7. Security cleanup (background, survives parent shell exit via nohup + disown)
nohup bash -c '
sleep <cleanup_delay>
# Remove public key from every remote target
for eip in <EIP1> <EIP2> <EIP3>; do
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=5 -i <temp_dir>/coc_ssh_key <ssh_user>@$eip \
    "sed -i \"/coc-temp-key/d\" \$(eval echo ~<ssh_user>)/.ssh/authorized_keys" 2>/dev/null || true
done
# Delete COC script
hcloud COC DeleteScript --cli-region=<coc_region> --script_uuid="<script_uuid>" 2>/dev/null || true
# Delete local keys
rm -f <temp_dir>/coc_ssh_key <temp_dir>/coc_ssh_key.pub
echo "COC SSH keys cleaned up. Existing SSH sessions remain unaffected."
' > <temp_dir>/coc_cleanup.log 2>&1 &
disown
echo "Cleanup scheduled in <cleanup_delay>s (PID: $!, log: <temp_dir>/coc_cleanup.log)"
```

## Parameters

| Parameter         | Required    | Default      | Constraint                                                                                                                                                                                                                             |
| ----------------- | ----------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ecs_instance_id` | Conditional | None         | Comma-separated list of ECS instance UUIDs. Required if `ecs_ip` is not provided. May be mixed with `ecs_ip` entries — the full set is the batch                                                                                       |
| `ecs_ip`          | Conditional | None         | Comma-separated list of ECS elastic IPv4 addresses. Required if `ecs_instance_id` is not provided. May be mixed with `ecs_instance_id` entries                                                                                         |
| `ecs_region`      | No          | None         | **Removed from target resolution.** Target ECS regions are discovered via `COC ListResources` (which returns each resource's `region_id` without needing it in advance); this parameter is kept only as an optional hint and is **not required** |
| `coc_region`      | No          | `cn-north-4` | **COC service region**. COC is a **global-level** service — only `cn-north-4` (China site) and `ap-southeast-3` (International site) are supported. All COC/IAM API calls must target this region; it is independent of the ECS region |
| `ssh_user`        | No          | `root`       | SSH username on the target ECS. Root or non-root supported; key is deployed to the user's `~/.ssh/authorized_keys`                                                                                                                     |
| `cleanup_delay`   | No          | `60`         | Seconds to wait before automatic key cleanup (min 10, max 300)                                                                                                                                                                         |
| `persist_timeout` | No          | `3600`       | Seconds to keep ControlMaster alive after all sessions close (min 60, max 86400)                                                                                                                                                       |

## Output Format

At each step, report progress in a structured manner:

| Step                     | Output                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| 1. Authorization         | Agency status (created / already exists), roles bound count (4/4)           |
| 2. Key Generation        | Key fingerprint, key file paths                                             |
| 3. Script                | Script name, action (created / reused), script_uuid                         |
| 4. Execution             | execute_uuid, target count & per-batch status, final result per target      |
| 5. SSH Test              | Per-target connection result, SSH command string                            |
| 6. Persistent Connection | ControlMaster status, multiplex verification, SSH aliases (one per `<EIP>`) |
| 7. Cleanup               | Timer PID, countdown notification, cleanup confirmation                     |

## Verification

Verify the workflow step by step:

1. **Authorization** — `CreateAgency` returns 200 → all 4 roles bound (200 or 409 each); returns 409 → entire IAM phase skipped (agency already authorized from prior run)
2. **Key Generation** — Key pair files exist in `<temp_dir>/` with correct permissions
3. **Script** — `coc_ssh_key_setup` exists with `PUBLIC_KEY` parameter and valid `script_uuid`
4. **Execution** — `GetScriptJobInfo` shows `SUCCESS` for the batch within 2 minutes
5. **SSH Test** — each target connects without password prompt; all test commands return `SSH_OK`
6. **Persistent Connection** — SSH config appended, `ssh -N -f <ssh_user>@<EIP>` starts master, `ssh <ssh_user>@<EIP> "echo SSH_MUX_OK"` succeeds for each target
7. **Cleanup** — remote key removed on every target, COC script deleted, local key files deleted; `ssh <ssh_user>@<EIP>` still connects via ControlMaster

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
- COC script execution is limited to 200 hosts per execution and 10 hosts per batch — split a batch of targets into up to 10 hosts per `batch_index`
- Batch targets may span **multiple ECS regions** — always confirm each target's region via `COC ListResources` in Step 4 (which returns `region_id` without needing it in advance); never assume all targets share `ecs_region`
- Test SSH and run cleanup for **every** target in the batch; a single failed target aborts the run and preserves keys for debugging
- SSH config entries persist after cleanup as harmless dead entries; they can be removed later if desired

## Reference Documents

| Document                                                       | Description                                                |
| -------------------------------------------------------------- | ---------------------------------------------------------- |
| [CLI Installation Guide](references/cli-installation-guide.md) | Install and configure hcloud CLI and SSH tools             |
| [IAM Policies](references/iam-policies.md)                     | Required IAM permissions, agency setup, and error handling |
| [Verification Method](references/verification-method.md)       | Step-by-step verification per workflow step                |
| [Acceptance Criteria](references/acceptance-criteria.md)       | Full end-to-end acceptance checklist                       |

## Notes

- **COC script depends on uniagent** — COC script execution depends on the uniagent agent pre-installed on ECS. If uniagent is not installed or has abnormal status, COC script execution will fail. Check uniagent status with:
  ```bash
  hcloud COC ListResources --cli-region=<coc_region> --provider=ecs --type=cloudservers --limit=100
  ```
  Inspect the `agent_state` field in the response to ensure the agent is in a running state. If agent status is abnormal, fix uniagent issues before executing COC scripts.
- **Region model** — COC and ECS use different regions:
  - **COC is a global-level service**: it only supports `cn-north-4` (China site) and `ap-southeast-3` (International site). All COC/IAM API calls must target `coc_region`.
  - **ECS is region-scoped**: each target ECS resides in its own region, which may differ across the batch. Each target's region is confirmed in Step 4 via the ECS CLI, then passed as `region_id` per `target_instance` inside the COC execution payload; COC routes to it from the global endpoint.
  - COC/IAM/ECS calls pin their region explicitly with `--cli-region` so the CLI profile's default region does not cause misrouting:
    - COC + IAM calls → `--cli-region=<coc_region>`
    - ECS target resolution (`COC ListResources`) → `--cli-region=<coc_region>` (the global COC endpoint; does NOT need the ECS's region in advance — the response returns each resource's `region_id`)
    - SSH commands → use `<EIP>` and `<ssh_user>` directly (no region concept)
- The COC script is created via `--cli-jsonInput` with a JSON file, not inline `--content="..."` — inline quoting causes parsing errors with shell special characters in the script body
- The COC script is **parameterized** with `PUBLIC_KEY` — it persists across invocations and can deploy different keys
- If the COC script already exists from a previous run, it is **reused** rather than recreated
- The cleanup uses `nohup bash -c '...' &` + `disown` to survive parent shell exit; output is logged to `<temp_dir>/coc_cleanup.log` for verification. The old `(sleep N && ...) &` pattern loses stdout when the parent shell exits in non-interactive mode
- Private keys are stored in `<temp_dir>` and should never be committed to VCS
- The SSH key type is **fixed to Ed25519** (`ssh-keygen -t ed25519`). RSA, ECDSA, and DSA keys are **not supported** by this skill — do not generate or deploy them. If a pre-existing incompatible key is detected, regenerate with Ed25519
- The `sed` cleanup target `coc-temp-key` matches the key comment set during `ssh-keygen`
- After cleanup, use `ssh <EIP>` (no key file needed) — ControlMaster socket handles authentication
