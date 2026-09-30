# Experiment Template Guide

## Overview

The `experiment.json` file is the machine-readable experiment template for CCE AZ power
outage fault injection. It defines the scenario, target AZ, target nodes, actions, rollback,
and monitoring configuration for Huawei Cloud.

## Schema Version

Current schema version: `1.0`

## Field Definitions

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | Yes | Template format version ("1.0") |
| `experiment_name` | string | Yes | Unique experiment name |
| `description` | string | No | Human-readable description |
| `platform` | string | Yes | Cloud platform ("huawei-cloud") |
| `region` | string | Yes | Huawei Cloud region (e.g., "cn-north-4") |
| `created_at` | string (ISO 8601) | Yes | Creation timestamp |
| `scenario` | object | Yes | Scenario definition |
| `cluster` | object | Yes | CCE cluster info |
| `az` | string | Yes | Target availability zone |
| `targets` | object | Yes | Target node selection |
| `actions` | object | Yes | Fault injection actions |
| `rollback` | object | Yes | Rollback/recovery action |
| `monitoring` | object | No | Monitoring configuration |
| `pods_to_reschedule` | array | No | Pods expected to be rescheduled |
| `safety` | object | Yes | Safety guardrails |

### scenario

| Field | Type | Description |
|---|---|---|
| `type` | string | Scenario type ("cce-az-power-outage") |
| `category` | string | Category ("az-power") |
| `huawei_api` | string | Huawei Cloud API name |
| `description` | string | Scenario description |

### cluster

| Field | Type | Description |
|---|---|---|
| `cluster_id` | string | CCE cluster ID |
| `cluster_name` | string | CCE cluster name |

### targets

| Field | Type | Description |
|---|---|---|
| `resource_type` | string | "huawei-cloud:cce:node" |
| `selection_mode` | string | "AZ" (select all nodes in AZ) |
| `az` | string | Target availability zone |
| `nodes` | array | Node list with name, instance_id, az, ready |
| `count` | integer | Number of target nodes |

### actions.shutdown

| Field | Type | Description |
|---|---|---|
| `action_id` | string | "huawei:ecs:stop-instances" |
| `api` | string | "ECS BatchStopServers" |
| `parameters.os_stop` | string | "SOFT" or "HARD" |
| `parameters.servers` | array | List of {id: instance_id} |
| `duration_seconds` | integer | Fault duration |

### rollback

| Field | Type | Description |
|---|---|---|
| `action_id` | string | "huawei:ecs:start-instances" |
| `api` | string | "ECS BatchStartServers" |
| `parameters.servers` | array | List of {id: instance_id} |
| `automatic` | boolean | Auto-rollback on failure (default: false) |

### monitoring

| Field | Type | Description |
|---|---|---|
| `enabled` | boolean | Enable monitoring |
| `node_status` | boolean | Monitor Node Ready/NotReady |
| `pod_rescheduling` | boolean | Monitor Pod rescheduling |
| `poll_interval_seconds` | integer | Polling interval (default: 10) |

### safety

| Field | Type | Description |
|---|---|---|
| `max_duration_seconds` | integer | Maximum experiment duration |
| `auto_rollback_on_failure` | boolean | Auto-rollback on failure |
| `require_confirmation` | boolean | Require user confirmation |
| `check_pdb` | boolean | Check PDB constraints |
| `check_cross_az_capacity` | boolean | Check cross-AZ capacity |

## Example

```json
{
  "schema_version": "1.0",
  "experiment_name": "cce-az-power-20260915-100000",
  "description": "CCE AZ power outage experiment — simulate AZ cn-north-4a power failure",
  "platform": "huawei-cloud",
  "region": "cn-north-4",
  "created_at": "2026-09-15T10:00:00+00:00",
  "scenario": {
    "type": "cce-az-power-outage",
    "category": "az-power",
    "huawei_api": "ECS.BatchStopServers",
    "description": "Simulate AZ cn-north-4a power outage by shutting down all CCE nodes"
  },
  "cluster": {
    "cluster_id": "ce3288bc-b01b-11f1-ab81-0255ac10026d",
    "cluster_name": "cce-prod"
  },
  "az": "cn-north-4a",
  "targets": {
    "resource_type": "huawei-cloud:cce:node",
    "selection_mode": "AZ",
    "az": "cn-north-4a",
    "nodes": [
      {"name": "node-1", "instance_id": "xxx-yyy", "az": "cn-north-4a", "ready": true},
      {"name": "node-2", "instance_id": "xxx-zzz", "az": "cn-north-4a", "ready": true}
    ],
    "count": 2
  },
  "actions": {
    "shutdown": {
      "action_id": "huawei:ecs:stop-instances",
      "api": "ECS BatchStopServers",
      "parameters": {
        "os_stop": "SOFT",
        "servers": [{"id": "xxx-yyy"}, {"id": "xxx-zzz"}]
      },
      "duration_seconds": 300
    }
  },
  "rollback": {
    "action_id": "huawei:ecs:start-instances",
    "api": "ECS BatchStartServers",
    "parameters": {
      "servers": [{"id": "xxx-yyy"}, {"id": "xxx-zzz"}]
    },
    "automatic": false
  },
  "monitoring": {
    "enabled": true,
    "node_status": true,
    "pod_rescheduling": true,
    "poll_interval_seconds": 10
  },
  "safety": {
    "max_duration_seconds": 300,
    "auto_rollback_on_failure": false,
    "require_confirmation": true,
    "check_pdb": true,
    "check_cross_az_capacity": true
  }
}
```
