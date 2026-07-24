# Acceptance Criteria

## Overview

This document defines the acceptance criteria for the Huawei Cloud ECS Alert skill. All criteria must be met before the skill is considered production-ready.

## 1. Prerequisites

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 1.1 | hcloud CLI v7.2.2+ is installed | `hcloud --version` |
| 1.2 | Huawei Cloud credentials are configured (hcloud configure or env vars) | `hcloud IAM ListUsers` |
| 1.3 | Python 3.8+ is available | `python3 --version` |
| 1.4 | jq is installed for JSON parsing | `jq --version` |

## 2. Query Operations (Read-Only)

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 2.1 | `list_ecs.sh` returns ECS instance list in table format | `./scripts/list_ecs.sh` |
| 2.2 | `list_ecs.sh --format json` returns valid JSON | `./scripts/list_ecs.sh --format json \| jq .` |
| 2.3 | `list_ecs.sh --name <filter>` filters by instance name | `./scripts/list_ecs.sh --name ecs-test` |
| 2.4 | `list_alarms.sh` returns alarm rules list | `./scripts/list_alarms.sh` |
| 2.5 | `list_subscriptions.sh --topics` returns SMN topics | `./scripts/list_subscriptions.sh --topics` |
| 2.6 | `list_subscriptions.sh --subscriptions` returns SMN subscriptions | `./scripts/list_subscriptions.sh --subscriptions` |
| 2.7 | `batch_query_metrics.sh` returns metrics for specified ECS | `./scripts/batch_query_metrics.sh --ecs-ids <id> --metric cpu_util` |

## 3. Create Operations (Write - Requires User Confirmation)

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 3.1 | `create_alert_rules.sh --template web` creates alarm rules for web servers | Dry-run mode: `--dry-run` flag |
| 3.2 | `create_alert_rules.sh --template database` creates alarm rules for DB servers | Dry-run mode: `--dry-run` flag |
| 3.3 | `manage_notifications.sh --action create` creates SMN subscription | Create + verify + cleanup |
| 3.4 | `create_email_subscription.sh --email <addr>` creates email subscription | Create + verify + cleanup |
| 3.5 | All create operations prompt for user confirmation before execution | Manual review of script flow |

## 4. Update Operations (Write - Requires User Confirmation)

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 4.1 | `update_alarm_notifications.sh --action add` adds SMN topic to alarm | Dry-run or test environment |
| 4.2 | `update_alarm_notifications.sh --action remove` removes SMN topic from alarm | Dry-run or test environment |

## 5. Delete Operations (Write - Requires User Confirmation)

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 5.1 | `manage_notifications.sh --action delete` deletes SMN subscription | Create + delete + verify |
| 5.2 | Delete operation uses correct API: `BatchDeleteSubscriptions` | Code review |
| 5.3 | Delete operation prompts for user confirmation | Manual review of script flow |

## 6. Error Handling

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 6.1 | Missing hcloud CLI produces clear error message | `PATH=/tmp:$PATH ./scripts/list_ecs.sh` |
| 6.2 | Missing credentials produces guidance message | Unset env vars and run script |
| 6.3 | Invalid ECS ID produces API error without crash | `./scripts/batch_query_metrics.sh --ecs-ids invalid-id` |
| 6.4 | Network timeout handled gracefully | Simulate unreachable endpoint |
| 6.5 | All scripts support `--help` / `-h` flag | `./scripts/*.sh --help` |

## 7. Security

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 7.1 | No hardcoded AK/SK in any script | `grep -r 'AK\|SK' scripts/` (only env var refs) |
| 7.2 | Credentials loaded from env vars or hcloud config only | Code review |
| 7.3 | No credential values printed to stdout/stderr | `config.py` test mode uses masked output |
| 7.4 | Write operations require user confirmation | SKILL.md Parameter Confirmation section |
| 7.5 | Scripts use `set -e` for fail-fast behavior | Code review |

## 8. Compatibility

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 8.1 | Supports `HW_ACCESS_KEY` / `HW_SECRET_KEY` env vars | Set and run script |
| 8.2 | Supports `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` env vars | Set and run script |
| 8.3 | Falls back to hcloud CLI config when env vars not set | Unset env vars and run |
| 8.4 | Default region is `cn-north-4` when not specified | Unset region and run |
| 8.5 | Supports `HW_SECURITY_TOKEN` for temporary credentials | Set token and run |

## 9. Documentation

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 9.1 | SKILL.md contains `## Workflow` section | Check section exists |
| 9.2 | SKILL.md contains `## Core Commands` section | Check section exists |
| 9.3 | SKILL.md contains `## Reference Documents` section | Check section exists |
| 9.4 | SKILL.md contains `## Parameter Confirmation` section | Check section exists |
| 9.5 | `references/acceptance-criteria.md` exists | File exists |
| 9.6 | All scripts have `--help` documentation | Run `--help` on each script |
| 9.7 | SKILL.md frontmatter has `version` field | Check frontmatter |

## 10. Integration

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 10.1 | Skill triggers on "ECS alert", "create alert", "monitoring alert" etc. | Trigger keyword test |
| 10.2 | Skill refuses non-ECS alert requests | Send unrelated request |
| 10.3 | Skill guides credential setup when not configured | Run without credentials |
