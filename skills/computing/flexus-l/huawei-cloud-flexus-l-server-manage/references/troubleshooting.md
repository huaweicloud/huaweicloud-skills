# Troubleshooting Guide

## Common Errors

### 1. Authentication Errors

| Error | Cause | Solution |
| ------- | ------- | ---------- |
| `401 Unauthorized` | Invalid AK/SK | Verify AK/SK is correct and active |
| `APIGW.0301` | Signature verification failed | Check SK is correct |
| `APIGW.0303` | Token expired | Regenerate AK/SK |

### 2. Permission Errors

| Error | Cause | Solution |
| ------- | ------- | ---------- |
| `403 Forbidden` | Insufficient permissions | Add required IAM policies |
| `APIGW.0101` | API not found | Check service is enabled in region |

### 3. Resource Errors

| Error | Cause | Solution |
| ------- | ------- | ---------- |
| `BSS.0501` | Resource not found | Verify resource ID is correct |
| `BSS.0502` | Resource state invalid | Check resource status |
| `400 Bad Request` | Invalid parameters | Check spec/image compatibility |

### 4. Network Errors

| Error | Cause | Solution |
| ------- | ------- | ---------- |
| `DNS resolution failed` | Cannot resolve API endpoint | Check network/DNS settings |
| `Connection timeout` | Network unreachable | Check firewall/proxy settings |
| `SSL certificate error` | Certificate verification failed | Update CA certificates |

## Diagnostic Steps

### Step 1: Verify AK/SK

```bash
# Test with IAM API to get project ID
python scripts/flexus_lifecycle.py get-project-id \
  --ak <AK> --sk <SK> --region cn-north-4
```

### Step 2: Test Network

```bash
# Test API endpoint connectivity
curl -v https://hcss.cn-north-4.myhuaweicloud.com
curl -v https://iam.myhuaweicloud.com
```

### Step 3: Dry Run

```bash
# Preview operation without executing
python scripts/flexus_lifecycle.py create-instance \
  --ak <AK> --sk <SK> \
  --dry-run
```

## FAQ

**Q: Why does creation fail with "spec not available"?**
A: Spec codes vary by region and image. Check the official documentation for supported combinations.

**Q: Why can't I renew my instance?**
A: Ensure the instance is in active status and you have BSS Administrator permission.

**Q: How to handle "insufficient balance" error?**
A: Top up your Huawei Cloud account or bind a payment method.

**Q: Why does DNS resolution fail?**
A: The server may not be able to access Huawei Cloud API. Check network settings or use a proxy.
