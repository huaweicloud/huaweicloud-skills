---
id: huawei-cloud-cce-alarm-correlation-engine
name: huawei-cloud-cce-alarm-correlation-engine
description: |
  Huawei Cloud AOM alarm correlation and alarm-rule management skill for CCE operations.
  Use this skill when the user wants to: (1) query AOM active and historical alarms, (2) analyze alarm deduplication, alarm storms, severity grouping, burst alarms, and chronic alarms, (3) inspect CCE cluster alarm health, (4) query, create, update, delete, enable, or disable AOM alarm rules, (5) query or create notification action rules, (6) batch configure or clean CCE recommended AOM alarm rules from the cloud-side CCE alarm template.
  Trigger: user mentions "alarm correlation", "AOM alarm", "alarm rule", "alarm storm", "alarm inspection", "notification rule", "告警关联", "AOM 告警", "告警规则", "告警风暴", "通知规则", or "CCE 告警".
tags: [cce, alarm-correlation, aom, observability, alarm-management]
---

# Huawei Cloud CCE Alarm Correlation Engine

## Overview

Correlate Huawei Cloud AOM active and historical alarms for CCE operations, then convert raw alarm streams into prioritized investigation leads. This skill also manages AOM alarm rules and notification action rules through a strict preview-and-confirm workflow.

**Architecture**: `python3 scripts/huawei-cloud.py` dispatcher -> local `hcloud` (KooCLI) -> AOM/CCE/IAM cloud service operations -> alarm query, alarm correlation, alarm-rule management, notification-rule management, and CCE alarm health inspection.

> **Execution Method**: All Huawei Cloud operations must go through the bundled Python dispatcher. The dispatcher invokes the local `hcloud` CLI. Direct SDK imports, hand-written API signing, curl IAM flows, openstack commands, or out-of-band cloud access paths are prohibited.

**Related Skills**:
- `huawei-cloud-cce-metric-analyzer` - CCE, AOM, and cloud-resource metric checks
- `huawei-cloud-cce-kubernetes-event-analyzer` - Kubernetes warning event analysis
- `huawei-cloud-cce-pod-failure-diagnoser` - Pod failure diagnosis
- `huawei-cloud-cce-node-failure-diagnoser` - Node failure diagnosis
- `huawei-cloud-cce-auto-remediation-runner` - Remediation preview and execution

**Capabilities**:
- Query active AOM alarms, historical AOM alarms, and merged active+historical views
- Analyze alarm deduplication, severity grouping, burst alarms, attention alarms, and chronic alarms
- Inspect CCE alarm health and produce risk items for follow-up diagnosis
- Query AOM alarm rules with optional `cluster_id` filtering
- Resolve the AOM Prometheus instance bound to a CCE cluster
- Create metric alarm rules and event alarm rules
- Create notification action rules from a user-provided SMN topic
- Batch configure CCE recommended alarm rules from the cloud-side CCE alarm template
- Batch clean CCE alarm rules matching the cloud-side CCE alarm template
- Update, delete, enable, and disable AOM alarm rules
- Query AOM action rules and mute rules

**Typical Use Cases**:
- "List AOM alarms for this CCE cluster"
- "Analyze active and historical alarms for alarm storms"
- "Show current alarm rules for cluster `<cluster_id>`"
- "Create CCE recommended alarm rules with this notification rule"
- "Clean CCE template alarm rules for this cluster"
- "Create a notification action rule using this SMN topic"
- "Disable this noisy alarm rule after I confirm"

## Prerequisites

### 1. Runtime Dependencies

- Python 3.8+ for the dispatcher and result processing
- hcloud (KooCLI) 7.2.2+ in `PATH`
- A local hcloud profile configured with `hcloud configure`
- Run environment checks before first use when available in the skill package

### 2. Credential Configuration

- Valid Huawei Cloud credentials via explicit tool parameters, local hcloud profile, or environment variable fallback
- Credential priority for hcloud calls is: explicit tool parameters > local hcloud profile > environment variables
- Tools that need `project_id` resolve it internally where possible: explicit `project_id` parameter first, then active hcloud profile/IAM project lookup for the target region, then environment fallback

**Security Rules**:
- Never expose AK/SK, tokens, or credential-derived secrets in code, commands, logs, or responses
- Never run `echo $HUAWEI_AK` or `echo $HUAWEI_SK`
- Never write credentials to files
- Prefer hcloud profile for normal use
- Use IAM users with least privilege

**Optional Environment Fallback**:

```bash
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_REGION=cn-north-4
export HUAWEI_PROJECT_ID=<project-id>
export HUAWEI_SECURITY_TOKEN=<security-token>
```

### 3. IAM Permission Requirements

| Permission | Purpose |
| ---------- | ------- |
| `aom:event:list` | Query active and historical AOM alarms |
| `aom:alarmRule:list` | Query AOM alarm rules |
| `aom:alarmRule:create` | Create AOM alarm rules |
| `aom:alarmRule:update` | Update, enable, or disable AOM alarm rules |
| `aom:alarmRule:delete` | Delete AOM alarm rules |
| `aom:actionRule:list` | Query AOM action/notification rules |
| `aom:actionRule:create` | Create AOM notification action rules |
| `aom:actionRule:delete` | Delete AOM notification action rules |
| `aom:muteRule:list` | Query AOM mute rules |
| `cce:cluster:get` | Resolve CCE cluster and AOM Prometheus binding |

**Permission Failure Handling**:

1. Show the failed operation and required permission.
2. Ask the user to grant the missing IAM permission.
3. Pause mutation work until the user confirms permissions are ready.

## Core Commands

All commands use the Python dispatcher script:

```bash
python3 scripts/huawei-cloud.py <action> <key=value>...
```

## KooCLI命令格式标准

This skill does not ask users to run raw `hcloud` commands directly. All cloud operations must use the dispatcher command format:

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value key=value
```

The dispatcher converts tool parameters into standard KooCLI calls:

```bash
hcloud <service> <operation> --cli-region=<region> --cli-output=json [--cli-jsonInput=<file>]
```

Follow these rules for every command:

- Use `key=value` parameters; quote values that contain spaces, `>`, `<`, `|`, JSON, or PromQL.
- Do not print or persist AK/SK, security tokens, or generated JSON input files.
- Use dispatcher preview output first for R2/R1/R0 tools; add `confirm=true` only after explicit user confirmation.
- Prefer hcloud profile credentials; explicit tool parameters override profile and environment fallback.
- See [CLI Installation Guide](references/cli-installation-guide.md) for setup and validation.

### 1. Alarm Query And Correlation

```bash
# Query active + historical alarms in a region
python3 scripts/huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4

# Query active + historical alarms for a cluster
python3 scripts/huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4 cluster_id=<cluster-id>

# Query current active alarms only
python3 scripts/huawei-cloud.py huawei_list_aom_current_alarms \
  region=cn-north-4 cluster_id=<cluster-id>

# Analyze deduplicated, burst, attention, and chronic alarm groups
python3 scripts/huawei-cloud.py huawei_analyze_aom_alarms \
  region=cn-north-4 cluster_id=<cluster-id>
```

> Do not conclude "no issue" from absence of active alarms alone. Always consider historical alarms when diagnosing a recent or recovered problem.

### 2. Alarm Rule Query

```bash
# Query all alarm rules in a region
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4

# Query alarm rules related to one CCE cluster
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# Resolve the cluster AOM Prometheus instance
python3 scripts/huawei-cloud.py huawei_resolve_cce_aom_prom_instance \
  region=cn-north-4 cluster_id=<cluster-id>
```

`huawei_list_aom_alarm_rules` supports cluster filtering by `cluster_id` only. Do not use `cluster_name` as a filter.

### 3. Notification Rules

```bash
# List existing action/notification rules
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules \
  region=cn-north-4

# Preview creating a notification action rule from an SMN topic
python3 scripts/huawei-cloud.py huawei_create_aom_notification_action_rule \
  region=cn-north-4 rule_name=auto-cluster-xxx \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn>

# Confirm creation
python3 scripts/huawei-cloud.py huawei_create_aom_notification_action_rule \
  region=cn-north-4 rule_name=auto-cluster-xxx \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn> \
  confirm=true
```

Never choose a notification rule automatically. If `bind_notification_rule_id` is missing for batch alarm creation, list available action rules and wait for explicit user selection, or ask the user to provide an SMN topic and create a notification rule first.

### 4. Alarm Rule Creation

```bash
# Preview creating a CCE template metric alarm rule
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  alarm_item=NodeCPUUsageHigherThanEightyPercent

# Confirm creating a CCE template metric alarm rule
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  alarm_item=NodeCPUUsageHigherThanEightyPercent \
  bind_notification_rule_id=<action-rule-id> \
  confirm=true

# Preview creating an event alarm rule
python3 scripts/huawei-cloud.py huawei_create_aom_event_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  event_name="<event-name>"

# Confirm creating an event alarm rule
python3 scripts/huawei-cloud.py huawei_create_aom_event_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  event_name="<event-name>" \
  bind_notification_rule_id=<action-rule-id> \
  confirm=true
```

Metric rules with `cluster_id` + `alarm_item` and event rules both use the same CCE template payload path and default naming as batch creation. Pass `rule_name` only when the user explicitly requests a custom name. Single-rule creation requires explicit `bind_notification_rule_id` during confirmed execution, same as batch CCE alarm rule configuration. Event alarm rule `event_name` should reference `references/cce-event-list.md`; metric `alarm_item` should use the CCE template alias or rule name.

### 5. CCE Template Alarm Rules

```bash
# Preview batch creating CCE recommended alarm rules
python3 scripts/huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  bind_notification_rule_id=<action-rule-id>

# Confirm batch creation
python3 scripts/huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  bind_notification_rule_id=<action-rule-id> confirm=true

# Preview cleanup of CCE template alarm rules for a cluster
python3 scripts/huawei-cloud.py huawei_cleanup_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# Confirm cleanup
python3 scripts/huawei-cloud.py huawei_cleanup_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  delete_auto_notification_rule=true confirm=true
```

`huawei_configure_cce_aom_alarm_rules` requires explicit `bind_notification_rule_id`. If not provided, do not return or choose `available_notification_rules` from this tool; call `huawei_list_aom_action_rules` separately and present choices to the user.

### 6. Alarm Rule Mutation

```bash
# Preview update
python3 scripts/huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule threshold=80

# Confirm update
python3 scripts/huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule threshold=80 confirm=true

# Preview delete
python3 scripts/huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule

# Confirm delete
python3 scripts/huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule confirm=true

# Preview disable or enable
python3 scripts/huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 rule_id=<rule-id>

python3 scripts/huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 rule_id=<rule-id>
```

### 7. Action And Mute Rule Visibility

```bash
# Query mute rules
python3 scripts/huawei-cloud.py huawei_list_aom_mute_rules \
  region=cn-north-4

# Preview deleting an action rule
python3 scripts/huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 rule_name=<rule-name>
```

### 8. Cluster Alarm Inspection

```bash
python3 scripts/huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 cluster_id=<cluster-id>
```

## Risk Levels

This skill includes read-only query tools and mutation tools. Mutation tools must be previewed first and must wait for explicit user confirmation before using `confirm=true`.

| Level | Meaning | Execution Guidance |
| ----- | ------- | ------------------ |
| R3 | No-risk read-only query or local analysis | May run automatically |
| R2 | Low-risk monitoring configuration change, such as creating alarm or notification configuration without deleting resources or increasing service capacity/cost | Preview first; execute only after explicit user confirmation |
| R1 | Risky monitoring change, such as updating or disabling a rule in a way that may reduce observability | Preview first; require explicit user confirmation and `confirm=true` |
| R0 | Critical monitoring protection removal, such as deleting alarm rules, action rules, or broad cleanup | Require explicit confirmation, impact review, and rollback plan before `confirm=true` |

| Tool | Operation Type | Risk Level | Description |
| ---- | -------------- | ---------- | ----------- |
| `huawei_list_aom_alarms` | Query | R3 | Query active + historical alarms, merged and deduplicated |
| `huawei_list_aom_current_alarms` | Query | R3 | Query current active alarms only |
| `huawei_analyze_aom_alarms` | Query + local analysis | R3 | Analyze alarm groups, bursts, attention alarms, and chronic alarms |
| `huawei_aom_alarm_inspection` | Query + local analysis | R3 | Inspect cluster alarm health |
| `huawei_list_aom_alarm_rules` | Query | R3 | Query AOM alarm rules; supports optional `cluster_id` |
| `huawei_resolve_cce_aom_prom_instance` | Query | R3 | Resolve the cluster AOM Prometheus instance |
| `huawei_list_aom_action_rules` | Query | R3 | Query action/notification rules |
| `huawei_list_aom_mute_rules` | Query | R3 | Query mute rules |
| `huawei_create_aom_alarm_rule` | Create | R2 | Create an AOM metric alarm rule |
| `huawei_create_aom_event_alarm_rule` | Create | R2 | Create an AOM event alarm rule |
| `huawei_create_aom_notification_action_rule` | Create | R2 | Create a notification action rule from a user-provided SMN topic |
| `huawei_configure_cce_aom_alarm_rules` | Batch create | R2 | Create CCE recommended alarm rules using an explicit existing notification action rule |
| `huawei_enable_aom_alarm_rule` | Enable | R2 | Enable an AOM alarm rule |
| `huawei_update_aom_alarm_rule` | Update | R1 | Update an AOM alarm rule |
| `huawei_disable_aom_alarm_rule` | Disable | R1 | Disable an AOM alarm rule |
| `huawei_delete_aom_alarm_rule` | Delete | R0 | Delete an AOM alarm rule |
| `huawei_cleanup_cce_aom_alarm_rules` | Batch delete | R0 | Delete CCE template alarm rules for the target cluster |
| `huawei_delete_aom_action_rule` | Delete | R0 | Delete a notification action rule |

## Parameter Reference

### Common Parameters

| Parameter | Required/Optional | Description | Default |
| --------- | ----------------- | ----------- | ------- |
| `region` | Required | Huawei Cloud region | `HUAWEI_REGION` |
| `cluster_id` | Tool-specific | CCE cluster ID; required for cluster-scoped operations | N/A |
| `ak` | Optional | Explicit AK; highest priority for hcloud calls | profile/env fallback |
| `sk` | Optional | Explicit SK; highest priority for hcloud calls | profile/env fallback |
| `project_id` | Optional | Explicit Project ID | hcloud/IAM/env fallback |
| `confirm` | Mutation only | Execute a previewed mutation when set to `true` | `false` |

### Alarm Query Parameters

| Tool | Required | Optional |
| ---- | -------- | -------- |
| `huawei_list_aom_alarms` | `region` | `cluster_id`, time-window/filter params |
| `huawei_list_aom_current_alarms` | `region` | `cluster_id`, filter params |
| `huawei_analyze_aom_alarms` | `region` | `cluster_id`, time-window/filter params |
| `huawei_aom_alarm_inspection` | `region`, `cluster_id` | filter params |

### Alarm Rule Parameters

| Tool | Required | Notes |
| ---- | -------- | ----- |
| `huawei_list_aom_alarm_rules` | `region` | Optional `cluster_id`; no `cluster_name` filtering |
| `huawei_create_aom_alarm_rule` | `region` | Template mode: `cluster_id`, `alarm_item`; manual mode: metric fields. Confirmed execution requires `bind_notification_rule_id` |
| `huawei_create_aom_event_alarm_rule` | `region`, `cluster_id`, `event_name` | R2; confirmed execution requires `bind_notification_rule_id`; optional `rule_name` overrides template naming |
| `huawei_create_aom_notification_action_rule` | `region`, `rule_name`, `notification_topic_urn`, `notification_topic_name` | R2; user must provide the topic |
| `huawei_configure_cce_aom_alarm_rules` | `region`, `cluster_id`, `bind_notification_rule_id` | R2; user must explicitly choose the notification rule |
| `huawei_cleanup_cce_aom_alarm_rules` | `region`, `cluster_id` | R0; optional `delete_auto_notification_rule=true` |
| `huawei_update_aom_alarm_rule` | `region`, `rule_name` | R1; update fields are tool-specific |
| `huawei_delete_aom_alarm_rule` | `region`, `rule_name` | R0 |
| `huawei_disable_aom_alarm_rule` | `region`, `rule_id` | R1 |
| `huawei_enable_aom_alarm_rule` | `region`, `rule_id` | R2 |

## Output Format

See [Output Schema](references/output-schema.md) for the complete JSON response structure.

**Key output fields**:
- `success`: command success status
- `error`: failure reason when `success=false`
- `preview`: mutation preview when `confirm=true` is not provided
- `requires_confirmation`: whether user confirmation is required
- `report`: alarm-correlation summary
- `issues`: inspection risk items
- `alarms`, `rules`, `action_rules`, `mute_rules`: queried resources

## Workflow

See [Workflow](references/workflow.md) for the detailed alarm-correlation flow.

Recommended workflow:

1. Read the alarm name, resource, time window, and severity level from the user.
2. Default to the last 1 hour unless the user gives a different incident window.
3. Query active + historical alarms with `huawei_list_aom_alarms`.
4. Analyze alarm groups with `huawei_analyze_aom_alarms`.
5. Query alarm rules, action rules, and mute rules when notification gaps or suppression are suspected.
6. Group findings by resource, namespace, node, workload, and alarm type.
7. Hand off to diagnosis skills for Pod, Node, Network, Storage, or Workload root cause analysis.

## Verification

Run read-only checks first:

```bash
python3 scripts/huawei-cloud.py huawei_list_aom_alarms region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules region=cn-north-4
```

For cluster-scoped checks:

```bash
python3 scripts/huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 cluster_id=<cluster-id>
```

Mutation verification:

1. Run the command without `confirm=true`.
2. Review `preview`, affected resources, and expected impact.
3. Wait for explicit user confirmation.
4. Re-run with `confirm=true`.
5. Verify with the corresponding list/query command.

## Best Practices

1. **Use active + historical alarms for diagnosis** - active-only views can miss recently recovered issues.
2. **Filter by `cluster_id`** - use exact cluster ID for cluster-scoped alarm rule and alarm analysis tasks.
3. **Preview every mutation** - never skip the preview step for R2/R1/R0 tools.
4. **Do not auto-select notification rules** - always wait for user selection of `bind_notification_rule_id`.
5. **Keep notification setup explicit** - create notification action rules only from a user-provided SMN topic.
6. **Separate analysis from remediation** - recommend remediation, then hand off to remediation skills.
7. **Protect observability** - avoid disabling or deleting rules unless impact is understood and confirmed.

## Notes

- Alarm diagnosis must consider both active and historical alarms; do not conclude the cluster is healthy only because there are no active alarms.
- R2/R1/R0 tools must use preview-first execution and wait for explicit user confirmation before applying changes.
- Do not automatically select notification rules, SMN topics, clusters, or templates for the user.
- Do not modify alarm resources outside the tools provided by this skill.
- Use `cluster_id` for cluster-scoped filtering; cluster names are not accepted by `huawei_list_aom_alarm_rules`.

## Troubleshooting

| Symptom | Likely Cause | Action |
| ------- | ------------ | ------ |
| hcloud command fails | Missing profile, region, or IAM permission | Check `hcloud configure list` and IAM policy |
| No active alarms | Issue may have recovered or only exists in history | Query active + historical alarms |
| Batch configure fails without notification rule | `bind_notification_rule_id` is missing | List action rules or create one from an SMN topic, then retry |
| Cluster alarm rule query returns too many rules | Missing `cluster_id` filter | Re-run with exact `cluster_id` |
| Project ID errors | Profile/project resolution failed | Provide `project_id` explicitly or fix hcloud profile |

## Limitations

- This skill does not modify CCE, ECS, ELB, EIP, VPC, security group, node, workload, or Kubernetes resources.
- This skill must not create, update, or delete mute rules.
- This skill must not use out-of-band cloud commands to modify alarm resources.
- This skill cannot safely infer a notification rule for the user.
- `huawei_list_aom_alarm_rules` filters by `cluster_id`, not cluster name.

## References

| Document | Use |
| -------- | --- |
| [Operation Guide](references/operation-guide.md) | Detailed parameters, output expectations, verification, diagnosis hand-off, and pitfalls |
| [Workflow](references/workflow.md) | Alarm correlation workflow |
| [Output Schema](references/output-schema.md) | Output JSON schema |
| [Risk Rules](references/risk-rules.md) | Risk boundaries and confirmation rules |
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud/KooCLI installation and profile checks |
| [IAM Policies](references/iam-policies.md) | Required AOM, CCE, and IAM permissions |
| [Verification Method](references/verification-method.md) | Functional and mutation verification checklist |
| [Acceptance Criteria](references/acceptance-criteria.md) | Skill acceptance criteria and test cases |
| [CCE Event List](references/cce-event-list.md) | CCE event names for event alarm rules |
| [Prometheus Metric Alarms](references/cce-prometheus-metric-alarms.md) | Prometheus metric alarm references |
