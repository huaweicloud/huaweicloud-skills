# IAM Policies

## Summary

This skill does **not** require any Huawei Cloud IAM credentials or policies.

## Reason

The skill is a **local / SSH operational tool** that translates natural-language
requests into `npu-smi` / `ascend-dmi` commands. It runs directly on an Ascend
server (local mode) or reaches the server over SSH (remote mode). It performs
no Huawei Cloud API calls, so it never needs:

- AK/SK (Access Key / Secret Key)
- IAM tokens or session credentials
- Any Huawei Cloud IAM policy, agency, or role

## Permissions Needed

- **None.** No IAM policy, agency, or role needs to be attached to the agent
  runtime for this skill to work.

## Access Required on the Target Host

The execution target (local shell or SSH host) requires:

| Requirement | Detail |
|-------------|--------|
| `npu-smi` | CANN installed and on `PATH` (`.bashrc` / `LD_LIBRARY_PATH`) |
| `ascend-dmi` | Only for FLOPS tests |
| SSH access | Remote mode only: reachable host, running `sshd`, password authentication enabled |
| Shell command rights | Ability to run `npu-smi` / `ascend-dmi` on the target |

These are host-level OS/CANN permissions, not Huawei Cloud IAM permissions.

## Security Notes

- The skill never calls any Huawei Cloud REST/OpenAPI endpoint and never
  connects to any cloud database.
- No cloud resources are created, modified, or deleted.
- No `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` or other Huawei Cloud
  credentials are read, transmitted, or logged.
- SSH passwords are passed only via the `--password` argument and held in
  memory for the session only; they are never printed or logged.
```