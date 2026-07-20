# Huawei Cloud CCE Alarm Correlation Engine · Acceptance Criteria

## Functional Acceptance

| ID | Acceptance Item | Pass Criteria |
| -- | --------------- | ------------- |
| AC-01 | Skill activation | Activates for AOM alarm, CCE alarm rule, notification rule, and alarm-correlation requests |
| AC-02 | Read-only alarm query | Lists active and historical AOM alarms with valid JSON output |
| AC-03 | Alarm rule query | Lists alarm rules and supports exact `cluster_id` filtering |
| AC-04 | Notification rule query | Lists AOM action/notification rules without modifying resources |
| AC-05 | Single metric rule creation | Creates a CCE template metric alarm rule after preview and confirmation |
| AC-06 | Single event rule creation | Creates a CCE template event alarm rule after preview and confirmation |
| AC-07 | Manual PromQL rule creation | Creates a PromQL metric rule using the template-compatible payload path |
| AC-08 | Batch rule creation | Creates CCE recommended alarm rules with explicit `bind_notification_rule_id` |
| AC-09 | Cleanup | Deletes only intended cluster-scoped CCE template alarm rules after R0 confirmation |

## Safety Acceptance

| ID | Acceptance Item | Pass Criteria |
| -- | --------------- | ------------- |
| SAF-01 | Credential safety | No AK/SK or security token is printed, committed, or written to skill files |
| SAF-02 | Preview-first mutations | R2/R1/R0 tools return preview output unless `confirm=true` is provided |
| SAF-03 | Explicit user choice | The skill never auto-selects notification rules, SMN topics, clusters, or templates for the user |
| SAF-04 | Scope control | The skill does not modify CCE, ECS, ELB, VPC, Kubernetes, or mute-rule resources |
| SAF-05 | Historical alarms | Diagnosis never concludes health from absence of active alarms alone |

## Documentation Acceptance

| ID | Acceptance Item | Pass Criteria |
| -- | --------------- | ------------- |
| DOC-01 | KooCLI command format | `SKILL.md` includes the KooCLI command format standard section |
| DOC-02 | CLI guide | `references/cli-installation-guide.md` exists and describes hcloud setup |
| DOC-03 | IAM policies | `references/iam-policies.md` exists and lists required permissions |
| DOC-04 | Verification method | `references/verification-method.md` exists and describes static/runtime checks |
| DOC-05 | Acceptance criteria | `references/acceptance-criteria.md` exists and defines pass criteria |
| DOC-06 | Main file size | `SKILL.md` remains under 500 lines |

## Test Cases

| ID | Scenario | Expected Result |
| -- | -------- | --------------- |
| TC-01 | Query AOM alarm rules by region | Returns valid JSON and `success=true` |
| TC-02 | Query AOM alarm rules by `cluster_id` | Returns only rules related to that cluster |
| TC-03 | Create CCE template metric alarm rule preview | Does not execute; returns confirmation requirement |
| TC-04 | Create CCE template metric alarm rule confirmed | Creates rule and list query verifies it |
| TC-05 | Create event alarm rule confirmed | Creates rule with CCE template naming |
| TC-06 | Create manual PromQL rule confirmed | Creates `monitor_type=promql` rule and binds notification rule |
| TC-07 | Missing `bind_notification_rule_id` during confirmed create | Fails with a clear error and does not auto-select a rule |
| TC-08 | Cleanup CCE template rules | Deletes only the target cluster rules after explicit R0 confirmation |

## Pass Condition

The skill passes acceptance when:

- All functional acceptance items required by the changed feature pass.
- All safety acceptance items pass.
- Static verification and at least one read-only runtime verification pass.
- Mutation test resources are cleaned up after verification when the user approves cleanup.

