# Huawei Cloud CCE Alarm Correlation Engine · IAM Policies

## Overview

This skill queries and manages AOM alarms, AOM alarm rules, AOM notification action rules, and CCE cluster metadata. The executing IAM user must have least-privilege permissions for the requested operation.

## Required Permissions

| Permission | Purpose | Risk Scope |
| ---------- | ------- | ---------- |
| `aom:event:list` | Query active and historical alarms | Read-only |
| `aom:alarmRule:list` | Query AOM alarm rules | Read-only |
| `aom:alarmRule:create` | Create metric and event alarm rules | R2 mutation |
| `aom:alarmRule:update` | Update, enable, or disable alarm rules | R1/R2 mutation |
| `aom:alarmRule:delete` | Delete alarm rules or clean CCE template rules | R0 mutation |
| `aom:actionRule:list` | Query notification action rules | Read-only |
| `aom:actionRule:create` | Create notification action rules from user-provided SMN topics | R2 mutation |
| `aom:actionRule:delete` | Delete notification action rules | R0 mutation |
| `aom:muteRule:list` | Query mute rules | Read-only |
| `cce:cluster:get` | Resolve CCE cluster metadata and AOM Prometheus binding | Read-only |
| `iam:projects:list` | Resolve project ID for the target region when not provided | Read-only |

## Recommended Policy Model

Use separate IAM policies for read-only inspection and mutation execution:

- Read-only operators: grant AOM list permissions, CCE cluster get, and IAM project list.
- Alarm administrators: add AOM alarm rule and action rule create/update/delete permissions.
- Avoid granting broad administrator permissions when the user only needs alarm inspection.

## Permission Failure Handling

When a command fails due to IAM permissions:

1. Report the failed tool and operation.
2. Identify the permission likely required from the table above.
3. Do not retry mutation tools repeatedly.
4. Ask the user to grant permission or switch to a profile with sufficient permissions.

## Security Requirements

- Do not expose AK/SK, security tokens, or profile secrets.
- Do not store credentials in this skill directory.
- Do not use permissions outside the listed operations to modify AOM, CCE, ECS, ELB, VPC, or Kubernetes resources.
- R2/R1/R0 operations must use preview-first execution and explicit user confirmation.

