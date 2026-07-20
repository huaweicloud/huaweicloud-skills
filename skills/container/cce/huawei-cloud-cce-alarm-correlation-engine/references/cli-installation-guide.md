# Huawei Cloud CCE Alarm Correlation Engine · CLI Installation Guide

## Overview

This skill executes Huawei Cloud operations through the local `hcloud` CLI, also known as KooCLI. The Python dispatcher is the only supported entry point:

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value
```

Do not bypass the dispatcher with direct SDK calls, curl requests, manual IAM signing, or unrelated cloud CLIs.

## Requirements

- Python 3.8+
- `hcloud` 7.2.2 or later in `PATH`
- A configured hcloud profile with access to the target Huawei Cloud account
- Network access to Huawei Cloud AOM, CCE, and IAM endpoints

## Install Or Verify hcloud

Check whether hcloud is available:

```bash
hcloud version
hcloud configure list
```

If hcloud is missing, install KooCLI from Huawei Cloud official documentation, then reopen the shell so `hcloud` is in `PATH`.

## Configure Credentials

Use hcloud profile credentials for normal operation:

```bash
hcloud configure
```

Credential priority used by this skill:

1. Explicit tool parameters, such as `ak=...`, `sk=...`, and `project_id=...`
2. Active hcloud profile
3. Environment variable fallback

Optional environment fallback:

```bash
export HUAWEI_AK=<ak>
export HUAWEI_SK=<sk>
export HUAWEI_REGION=cn-north-4
export HUAWEI_PROJECT_ID=<project-id>
export HUAWEI_SECURITY_TOKEN=<security-token>
```

Never print AK/SK or security token values in terminal output, logs, commits, or chat responses.

## Command Format

Always call the dispatcher:

```bash
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules region=cn-north-4 cluster_id=<cluster-id>
```

For mutation tools, preview first:

```bash
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> alarm_item=<template-alias>
```

Execute only after user confirmation:

```bash
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> alarm_item=<template-alias> \
  bind_notification_rule_id=<action-rule-id> confirm=true
```

## Validation

Run read-only checks:

```bash
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules region=cn-north-4
```

Expected result:

- `success=true`
- JSON output is parseable
- No credential values appear in output

