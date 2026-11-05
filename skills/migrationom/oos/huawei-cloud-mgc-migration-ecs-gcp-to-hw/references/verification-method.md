# Verification Method - MGC Cross-Region Migration

Verification has three tiers: installation, configuration, and functional. Run them in order before declaring a migration run (or a boot repair) successful.

## 1. Installation Verification

| Check | Command | Success Criterion |
|---|---|---|
| Terraform installed | `terraform version` | Prints a version `>= 1.5.0` |
| Python installed | `python3 --version` | Prints Python `>= 3.8` |

## 2. Configuration Verification

| Check | Command | Success Criterion |
|---|---|---|
| Credentials present in tfvars | inspect `terraform.tfvars` for non-empty `source_access_key`/`source_secret_key`/`destination_access_key`/`destination_secret_key` (do not print values) | All four fields are non-empty |
| Terraform plan resolves variables | `terraform plan` | Completes without "variable not set" prompts |
| Source batch matches destination | confirm `source_server_ids` maps to reachable destination ECS by fixed IP | Every source ID has a resolvable destination target |

Never print any access-key/secret-key values to the terminal or into chat as part of this verification.

## 3. Functional Verification

| Check | Command | Success Criterion |
|---|---|---|
| Migration tasks created | `cat out/migration_result.json` | `results[]` has one entry per source with `source_sms_server_id`, `task_id`, `target_vm_id` |
| All tasks reach terminal state | poll task state per [runbook.md](runbook.md) | Every `results[].task_state` is `MIGRATE_SUCCESS` (or accepted terminal state) |
| Resume/checkpoint consistency (if applicable) | `cat out/resume_checkpoint_latest.json` | Checkpoint reflects the same source set as the current run |
| Network postcheck passes | `cat out/postcheck_network.json` | Target EIP bound, security-group connectivity confirmed |
| SSH/TCP-22 reachable | postcheck script result | `closed_or_timeout` is absent; connection succeeds |
| Boot repair verification (only if `repair_boot_via_helper.py` was run) | reboot target, re-check console output and SSH | No GRUB/root-device panic; SSH accepts the reset password |

If any functional check fails, follow [runbook.md](runbook.md) and [../SKILL.md](../SKILL.md#best-practices) for the matching error code or symptom before repeating verification.
