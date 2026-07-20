# Huawei Cloud CCE Alarm Correlation Engine · Verification Method

## Static Verification

Run from the repository root:

```bash
python3 -m py_compile \
  releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/scripts/huawei_cloud/aom.py \
  releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/scripts/huawei_cloud/dispatcher.py
```

Check Markdown and references:

```bash
test -f releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/references/cli-installation-guide.md
test -f releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/references/iam-policies.md
test -f releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/references/verification-method.md
test -f releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/references/acceptance-criteria.md
```

## Read-Only Runtime Verification

Use read-only tools first:

```bash
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_alarms region=cn-north-4
```

Expected result:

- `success=true`
- JSON output is valid
- No credentials are printed
- Results include `hcloud_command` or equivalent execution metadata when applicable

## Cluster-Scoped Verification

For a known CCE cluster:

```bash
python3 scripts/huawei-cloud.py huawei_resolve_cce_aom_prom_instance \
  region=cn-north-4 cluster_id=<cluster-id>

python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>
```

Expected result:

- Cluster-scoped queries only return rules related to the target `cluster_id`.
- `cluster_name` is not accepted by `huawei_list_aom_alarm_rules`.

## Mutation Verification

For R2/R1/R0 tools:

1. Run without `confirm=true`.
2. Confirm the output is preview-only and includes risk/confirmation information.
3. Wait for explicit user confirmation.
4. Run with `confirm=true`.
5. Verify the result with the matching list/query tool.

Example single-rule creation verification:

```bash
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> alarm_item=<template-alias>

python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> alarm_item=<template-alias> \
  bind_notification_rule_id=<action-rule-id> confirm=true

python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>
```

## Regression Checks

After code changes:

- Read-only tools still work with hcloud profile credentials.
- Project ID can be resolved when omitted.
- Batch and single CCE template rule creation use the same template payload behavior.
- Manual PromQL rule creation succeeds or returns a clear API error without leaking generated JSON payloads.
- Cleanup tools delete only the intended cluster-scoped CCE alarm rules.

