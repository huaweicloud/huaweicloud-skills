# Verification Method - MGC Cross-Region Migration

Verification has three tiers: installation, configuration, and functional. Run them in order before declaring a migration run successful.

## 1. Installation Verification

| Check | Command | Success Criterion |
|---|---|---|
| Terraform installed | `terraform version` | Prints a version `>= 1.5.0` |
| Python installed | `python3 --version` | Prints Python `>= 3.8` |
| `pexpect` present (only if VPN-bridge fallback is used) | `python3 -c "import pexpect"` | No `ModuleNotFoundError` |

## 2. Configuration Verification

| Check | Command | Success Criterion |
|---|---|---|
| Credentials present in tfvars | inspect `terraform.tfvars` for non-empty `access_key`/`secret_key` (do not print values) | Both fields are non-empty |
| Terraform plan resolves variables | `terraform plan` | Completes without "variable not set" prompts |
| Target image/region reachable | confirm `target_image_id` exists for `target_region` (via console or a read-only `ecs:cloudServerFlavors` check) | Image ID is valid for the region |

Never print `access_key`/`secret_key` values to the terminal or into chat as part of this verification.

## 3. Functional Verification

| Check | Command | Success Criterion |
|---|---|---|
| Migration task created | `cat out/migration_result.json` | Contains `migproject_id`, `task_id`, `source_sms_server_id`, `target_server_id` |
| Task reaches terminal state | poll task state per [runbook.md](runbook.md) | `task_state` is `MIGRATE_SUCCESS` (or accepted terminal state) |
| Network postcheck passes | `cat out/postcheck_network.json` | Target EIP bound, security-group connectivity confirmed |
| SSH/TCP-22 reachable | postcheck script result | `closed_or_timeout` is absent; connection succeeds |

If any functional check fails, follow [runbook.md](runbook.md) and [../SKILL.md](../SKILL.md#best-practices) for the matching error code or symptom before repeating verification.
