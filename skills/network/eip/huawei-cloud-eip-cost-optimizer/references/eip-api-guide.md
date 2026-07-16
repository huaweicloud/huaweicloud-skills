# EIP API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud Elastic Public IP (EIP) operations using hcloud CLI (KooCLI). All commands follow the standard format: `hcloud <Service> <Operation> --param=value --cli-region=<region>`.

## Authentication

### Method 1: Environment Variables

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
export HW_REGION_NAME=cn-north-4
```

### Method 2: hcloud CLI Configuration

```bash
# Interactive configuration (enter credentials via prompts, not command-line arguments)
hcloud configure

# Verify configuration (safe - does not expose values)
hcloud configure list
```

✅ **Correct**: Use `hcloud configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HW_ACCESS_KEY` to check credentials

## EIP Commands (v2 API)

### 1. List EIPs

```bash
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Response Example**:

```json
{
  "publicips": [
    {
      "id": "eip-xxx1",
      "public_ip_address": "123.45.67.89",
      "bandwidth_id": "bw-xxx1",
      "bandwidth_name": "bw-001",
      "bandwidth_share_type": "PER",
      "bandwidth_size": 5,
      "status": "DOWN",
      "tenant_id": "xxx",
      "create_time": "2026-04-15 10:30:00",
      "ip_version": 4,
      "enterprise_project_id": "0"
    }
  ]
}
```

**Note**: API returns `bandwidth_*` fields at top level (not nested in `bandwidth` object). `status` values: `ACTIVE` (bound), `DOWN` (unbound/idle), `ERROR`.

### 2. Show EIP Details

```bash
hcloud EIP ShowPublicip/v2 --publicip_id=<eip-id> --cli-region=cn-north-4
```

**Parameters**:
- `--publicip_id` (required): EIP ID
- `--cli-region` (required): Region ID

**Response Example**:

```json
{
  "publicip": {
    "id": "eip-xxx1",
    "public_ip_address": "123.45.67.89",
    "bandwidth_id": "bw-xxx1",
    "bandwidth_name": "bw-001",
    "bandwidth_share_type": "PER",
    "bandwidth_size": 5,
    "status": "DOWN",
    "create_time": "2026-04-15 10:30:00"
  }
}
```

### 3. Create EIP

```bash
hcloud EIP CreatePublicip/v2 \
  --publicip.type=5_bgp \
  --publicip.bandwidth.name=bw-001 \
  --publicip.bandwidth.size=5 \
  --cli-region=cn-north-4
```

**Parameters**:
- `--publicip.type` (required): EIP type, e.g. `5_bgp` (dynamic BGP)
- `--publicip.bandwidth.name` (required): Bandwidth name
- `--publicip.bandwidth.size` (required): Bandwidth in Mbps
- `--cli-region` (required): Region ID

### 4. Delete EIP (Irreversible!)

```bash
hcloud EIP DeletePublicip/v2 --publicip_id=<eip-id> --cli-region=cn-north-4
```

⚠️ **Warning**: This operation is irreversible. The public IP address will be reclaimed.

### 5. Update EIP Bandwidth

```bash
hcloud EIP UpdatePublicip/v2 \
  --publicip_id=<eip-id> \
  --publicip.bandwidth.size=10 \
  --cli-region=cn-north-4
```

**Parameters**:
- `--publicip_id` (required): EIP ID
- `--publicip.bandwidth.size` (required): New bandwidth in Mbps
- `--cli-region` (required): Region ID

### 6. Associate EIP to Resource

```bash
hcloud EIP AssociatePublicip/v2 \
  --publicip_id=<eip-id> \
  --associate_instance_type=ECS \
  --associate_instance_id=<instance-id> \
  --cli-region=cn-north-4
```

### 7. Disassociate EIP from Resource

```bash
hcloud EIP DisassociatePublicip/v2 \
  --publicip_id=<eip-id> \
  --cli-region=cn-north-4
```

## IAM Commands

### List Projects (for multi-region discovery)

```bash
hcloud IAM KeystoneListProjects --cli-region=cn-north-4
```

**Response Example**:

```json
{
  "projects": [
    {
      "id": "0xxx",
      "name": "cn-north-4",
      "enabled": true
    }
  ]
}
```

## Common Region IDs

| Region Name | Region ID |
|-------------|-----------|
| North China - Beijing 4 | `cn-north-4` |
| North China - Beijing 1 | `cn-north-1` |
| East China - Shanghai 1 | `cn-east-3` |
| South China - Guangzhou | `cn-south-1` |
| Asia Pacific - Hong Kong | `ap-southeast-1` |
| Asia Pacific - Singapore | `ap-southeast-2` |
| Europe - Paris | `eu-west-0` |

## EIP Status Reference

| Status | Description |
|--------|-------------|
| `ACTIVE` | Bound to a resource |
| `DOWN` | Unbound (idle) |
| `ERROR` | Error state |
| `FREEZED` | Frozen |
| `BIND_ERROR` | Bind failed |
| `BINDING` | Binding in progress |
| `UNBINDING` | Unbinding in progress |

## Cost Estimation Reference

⚠️ **Important**: Prices are for reference only. Actual costs may vary by region and billing mode.

### On-Demand Pricing (North China - Beijing 4)

| Item | Price |
|------|-------|
| Bandwidth fee | ≈ ¥3/Mbps/month |
| IP retain fee (unbound) | ≈ ¥0.02/hour |

### Formula

```
Monthly Cost = Bandwidth (Mbps) × ¥3/Mbps/month + IP Retain Fee
IP Retain Fee = 0.02 CNY/hour × 720 hours/month (for unbound EIPs)
```

**Note**: API does not return `charge_mode` field. Scripts use bandwidth billing model for all estimates.

## Best Practices

1. **Regular Cleanup**: Schedule weekly idle EIP scans via `monitor_idle_eips.sh --setup-cron`
2. **Tag Governance**: Use consistent tags (env, team, project) for all EIPs
3. **Bandwidth Policy**: Set minimum bandwidth for idle EIPs
4. **Always Confirm Before Release**: This skill is READ-ONLY — release must be done manually in console

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidAccessKeyId` | Invalid AK/SK | Check credential configuration via `hcloud configure list` |
| `VPC.0501` | EIP does not exist | Verify EIP ID is correct |
| `VPC.0503` | EIP is bound to a resource | Disassociate first, then release |
| `VPC.0504` | Bandwidth out of range | Valid range: 1-2000 Mbps |
| `429` | Too many requests | Add delay between API calls |

## Related Documentation

- [Huawei Cloud EIP Documentation](https://support.huaweicloud.com/eip/index.html)
- [KooCLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)
