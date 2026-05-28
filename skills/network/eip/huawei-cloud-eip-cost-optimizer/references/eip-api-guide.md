# EIP API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud Elastic Public IP (EIP) operations using Python SDK. All commands follow the standard format: `Python SDK <SERVICE> <Operation> --param=value --cli-region=<region>`.

## Authentication

### Method 1: Environment Variables

```bash
export HUAWEICLOUD_SDK_AK=<your-ak>
export HUAWEICLOUD_SDK_SK=<your-sk>
```

### Method 2: Python SDK Configuration

```bash
# Interactive configuration
Python SDK configure

# Verify configuration (safe - does not expose values)
Python SDK configure list
```

✅ **Correct**: Use `Python SDK configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HUAWEICLOUD_SDK_AK` to check credentials

## EIP Commands (v3 API)

### 1. List EIPs

```bash
Python SDK EIP ListPublicips/v3 --cli-region=cn-north-4
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
      "bandwidth": { "size": 5, "name": "bw-001" },
      "status": "ACTIVE",
      "binding_status": "BOUND",
      "associate_instance_type": "ECS",
      "create_time": "2026-04-15T10:30:00Z"
    },
    {
      "id": "eip-xxx2",
      "public_ip_address": "98.76.54.32",
      "bandwidth": { "size": 10, "name": "bw-002" },
      "status": "ACTIVE",
      "binding_status": "UNBOUND",
      "create_time": "2026-03-20T14:20:00Z"
    }
  ]
}
```

### 2. Show EIP Details

```bash
Python SDK EIP ShowPublicip/v3 --publicip_id=<eip-id> --cli-region=cn-north-4
```

**Parameters**:
- `--publicip_id` (required): EIP ID
- `--cli-region` (required): Region ID

### 3. Create EIP

```bash
Python SDK EIP CreatePublicip/v3 \
  --publicip.type=EIP \
  --publicip.bandwidth.name=bw-001 \
  --publicip.bandwidth.size=5 \
  --cli-region=cn-north-4
```

**Parameters**:
- `--publicip.type` (required): Always `EIP`
- `--publicip.bandwidth.name` (required): Bandwidth name
- `--publicip.bandwidth.size` (required): Bandwidth in Mbps
- `--cli-region` (required): Region ID

### 4. Delete EIP (Irreversible!)

```bash
Python SDK EIP DeletePublicip/v3 --publicip_id=<eip-id> --cli-region=cn-north-4
```

⚠️ **Warning**: This operation is irreversible. The public IP address will be reclaimed.

### 5. Update EIP Bandwidth

```bash
Python SDK EIP UpdatePublicip/v3 \
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
Python SDK EIP AssociatePublicip/v3 \
  --publicip_id=<eip-id> \
  --associate_instance_type=ECS \
  --associate_instance_id=<instance-id> \
  --cli-region=cn-north-4
```

### 7. Disassociate EIP from Resource

```bash
Python SDK EIP DisassociatePublicip/v3 \
  --publicip_id=<eip-id> \
  --cli-region=cn-north-4
```

## Tag Management Commands

### Create Tags

```bash
Python SDK EIP CreatePublicipTags/v3 \
  --publicip_id=<eip-id> \
  --tag.1.key=env \
  --tag.1.value=prod \
  --tag.2.key=team \
  --tag.2.value=devops \
  --cli-region=cn-north-4
```

### Delete Tags

```bash
Python SDK EIP DeletePublicipTags/v3 \
  --publicip_id=<eip-id> \
  --tag.1.key=env \
  --cli-region=cn-north-4
```

### List Tags

```bash
Python SDK EIP ShowPublicipTags/v3 \
  --publicip_id=<eip-id> \
  --cli-region=cn-north-4
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
| `ACTIVE` | Running normally |
| `DOWN` | Deactivated |
| `ERROR` | Error state |
| `FREEZED` | Frozen |
| `BIND_ERROR` | Bind failed |
| `ELB_DELETING` | ELB deleting |
| `BINDING` | Binding in progress |
| `UNBINDING` | Unbinding in progress |

## Binding Status Reference

| Binding Status | Description |
|---------------|-------------|
| `BOUND` | Bound to a resource |
| `UNBOUND` | Not bound (idle) |

## Cost Estimation Reference

⚠️ **Important**: Prices are for reference only. Actual costs may vary by region and billing mode.

### On-Demand Pricing (North China - Beijing 4)

| Bandwidth (Mbps) | Monthly Cost (CNY) |
|------------------|---------------------|
| 1 | ¥2.00 |
| 5 | ¥10.00 |
| 10 | ¥20.00 |
| 20 | ¥40.00 |
| 50 | ¥100.00 |

### Formula

```
Monthly Cost = Bandwidth (Mbps) × Unit Price (CNY/Mbps/Month)
```

Unit price varies by region, typically ¥2-4/Mbps/month.

## Best Practices

1. **Regular Cleanup**: Schedule weekly idle EIP scans
2. **Tag Governance**: Use consistent tags (env, team, project) for all EIPs
3. **Bandwidth Policy**: Set minimum bandwidth for idle EIPs
4. **Always Confirm Before Release**: Use `--interactive` mode in production

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidAccessKeyId` | Invalid AK/SK | Check credential configuration via `Python SDK configure list` |
| `EipNotFound` | EIP does not exist | Verify EIP ID is correct |
| `EipIsBound` | EIP is bound to a resource | Disassociate first, then release |
| `BandwidthOutOfRange` | Bandwidth out of range | Valid range: 1-2000 Mbps |
| `RequestLimitExceeded` | Too many requests | Add delay between requests |

## Related Documentation

- [Huawei Cloud EIP Documentation](https://support.huaweicloud.com/eip/index.html)
- [Python SDK Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)
