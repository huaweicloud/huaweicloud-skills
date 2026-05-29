# Verification Steps and Methods

## Prerequisite Verification

### 1. Verify Python3 and SDK

```bash
python3 --version  # Python3 >= 3.8
python3 -c "import huaweicloudsdkcore; print('SDK OK')"
```

### 2. Verify Credentials

```bash
# Environment variables
echo "AK set: $([ -n \"$HW_ACCESS_KEY\" ] && echo 'YES' || echo 'NO')"

# Or credentials file
cat /path/to/aksk.txt
```

## Functional Verification

```bash
# Environment variables
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

# Credentials file
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt

# Different service_type
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4

# Raw response
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --raw
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

echo "=== 1. Verify Python3 and SDK ==="
python3 --version
python3 -c "import huaweicloudsdkcore; print('SDK OK')"

echo "=== 2. Verify ShowStatistics API ==="
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /home/lj/aksk.txt

echo "=== All verifications passed ==="
```

## Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| Python3 version | >= 3.8 |
| huaweicloudsdkcore | Import successful |
| Credentials | Environment variables or credentials file provided |
| ShowStatistics API | Returns 200, total_request_count > 0 |
| Script output format | Table + Period |
| Token unit conversion | M tokens (thousand × 1000 = actual tokens) |
| service_type | Supports 1/2/4 |
