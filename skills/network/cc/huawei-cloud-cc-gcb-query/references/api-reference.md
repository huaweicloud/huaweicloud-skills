# API Reference

All APIs are verified from hcloud CLI debug mode (real HTTP request URLs).

## Endpoint

```
cc.myhuaweicloud.com
```

## 1. Show Global Connection Bandwidth

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/v3/{domain_id}/gcb/gcbandwidths/{id}` |
| CLI Command | `hcloud CC ShowGlobalConnectionBandwidth` |

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `domain_id` | string | Yes | Account ID |
| `id` | string | Yes | GCB instance ID (32–36 chars) |

## 2. List Global Connection Bandwidths

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/v3/{domain_id}/gcb/gcbandwidths` |
| CLI Command | `hcloud CC ListGlobalConnectionBandwidths` |

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `domain_id` | string | Yes | Account ID |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | integer | No | Page size (1–2000) |
| `marker` | string | No | Pagination marker |
| `admin_state` | array&lt;string&gt; | No | Status filter: `NORMAL`, `FREEZED` |
| `binding_service` | array&lt;string&gt; | No | Service type filter: `CC`, `GEIP`, `GCN`, `GSN` |
| `charge_mode` | array&lt;string&gt; | No | Charge mode filter: `bwd`, `95`, `95avr` |
| `id` | array&lt;string&gt; | No | GCB ID filter |
| `instance_id` | array&lt;string&gt; | No | Bound instance ID filter |
| `instance_type` | array&lt;string&gt; | No | Bound instance type filter: `CC`, `GEIP`, `GCN`, `GSN` |
| `name` | array&lt;string&gt; | No | Name filter |
| `type` | array&lt;string&gt; | No | Bandwidth type filter: `TrsArea`, `Area`, `SubArea`, `Region` |
| `enterprise_project_id` | array&lt;string&gt; | No | Enterprise project ID filter |

## 3. List Global Connection Bandwidth Configs

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/v3/{domain_id}/gcb/configs` |
| CLI Command | `hcloud CC ListGlobalConnectionBandwidthConfigs` |

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `domain_id` | string | Yes | Account ID |

## 4. List Support Binding Connection Bandwidths

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/v3/{domain_id}/gcb/gcbandwidths/support-bindings` |
| CLI Command | `hcloud CC ListSupportBindingConnectionBandwidths` |

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `domain_id` | string | Yes | Account ID |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `binding_service` | string | Yes | Target service type: `CC`, `GEIP`, `GCN`, `GSN` |
| `limit` | integer | No | Page size (1–2000) |
| `marker` | string | No | Pagination marker |
| `local_area` | string | No | Local access point (use with `remote_area`) |
| `remote_area` | string | No | Remote access point (use with `local_area`) |
| `enterprise_project_id` | array&lt;string&gt; | No | Enterprise project ID filter |
