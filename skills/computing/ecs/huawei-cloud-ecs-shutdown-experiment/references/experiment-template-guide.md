# Experiment Template Guide

## Overview

The `experiment.json` file is the machine-readable experiment template for ECS shutdown fault injection. It defines the scenario, targets, actions, rollback, and monitoring configuration for Huawei Cloud.

## Schema Version

Current schema version: `1.0`

## Field Definitions

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | Yes | Template format version (currently "1.0") |
| `experiment_name` | string | Yes | Unique experiment name |
| `description` | string | No | Human-readable description |
| `platform` | string | Yes | Cloud platform ("huawei-cloud") |
| `region` | string | Yes | Huawei Cloud region (e.g., "cn-north-4") |
| `created_at` | string (ISO 8601) | Yes | Creation timestamp |
| `scenario` | object | Yes | Scenario definition |
| `targets` | object | Yes | Target resource selection |
| `actions` | object | Yes | Fault injection actions |
| `rollback` | object | Yes | Rollback/recovery action |
| `monitoring` | object | No | Monitoring configuration |
| `stop_conditions` | array | No | Conditions to stop the experiment early |
| `safety` | object | Yes | Safety guardrails |

### scenario

| Field | Type | Description |
|---|---|---|
| `type` | string | Scenario type (e.g., "ecs-shutdown") |
| `category` | string | Scenario category (e.g., "resource-operation") |
| `huawei_api` | string | Huawei Cloud API name |

### targets

| Field | Type | Description |
|---|---|---|
| `resource_type` | string | Resource type identifier |
| `selection_mode` | string | "EXPLICIT" (manual) or "FILTER" (by criteria) |
| `instance_ids` | array | List of ECS instance IDs |
| `count` | integer | Number of target instances |

### actions

Each key in `actions` is an action name. Each action has:

| Field | Type | Description |
|---|---|---|
| `action_id` | string | Action identifier (e.g., "huawei:ecs:stop-instances") |
| `api` | string | Huawei Cloud API to call |
| `parameters` | object | API-specific parameters |
| `start_after` | integer | Delay in seconds before action starts |
| `duration_seconds` | integer | How long the fault lasts |

### rollback

| Field | Type | Description |
|---|---|---|
| `action_id` | string | Rollback action identifier |
| `api` | string | Huawei Cloud API for rollback |
| `parameters` | object | API parameters for rollback |
| `description` | string | Human-readable description |
| `automatic` | boolean | Whether rollback is automatic (default: false) |

### monitoring

| Field | Type | Description |
|---|---|---|
| `enabled` | boolean | Whether monitoring is configured |
| `source` | string | Monitoring source ("none", "ces", "custom") |
| `description` | string | Monitoring description |

### stop_conditions

Array of conditions that trigger early experiment termination. Each condition:

| Field | Type | Description |
|---|---|---|
| `type` | string | Condition type (e.g., "ces_alarm") |
| `alarm_id` | string | CES alarm rule ID |
| `description` | string | What this condition checks |

### safety

| Field | Type | Description |
|---|---|---|
| `max_duration_seconds` | integer | Maximum experiment duration |
| `auto_rollback_on_failure` | boolean | Auto-rollback on failure (default: true) |
| `require_confirmation` | boolean | Require user confirmation before execution |

## Example

```json
{
  "schema_version": "1.0",
  "experiment_name": "ecs-shutdown-experiment-20260908",
  "platform": "huawei-cloud",
  "region": "cn-north-4",
  "scenario": {
    "type": "ecs-shutdown",
    "huawei_api": "ECS.BatchStopServers",
  },
  "targets": {
    "resource_type": "huawei-cloud:ecs:instance",
    "instance_ids": ["i-xxx", "i-yyy"],
    "count": 2
  },
  "actions": {
    "shutdown": {
      "action_id": "huawei:ecs:stop-instances",
      "api": "ECS BatchStopServers",
      "duration_seconds": 300
    }
  },
  "rollback": {
    "action_id": "huawei:ecs:start-instances",
    "api": "ECS BatchStartServers",
    "automatic": false
  }
}
```
