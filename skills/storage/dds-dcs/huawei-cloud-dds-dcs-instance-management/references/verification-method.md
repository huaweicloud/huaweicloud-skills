# Verification Method

## 1. CLI Command Verification

Verify that each hcloud command produces valid output:

```bash
# Test DDS ListInstances
hcloud DDS ListInstances --cli-region=cn-north-4 --limit=1

# Test DCS ListInstances
hcloud DCS ListInstances --cli-region=cn-north-4 --limit=1

# Test DDS ListFlavors
hcloud DDS ListFlavors --cli-region=cn-north-4 --engine_name=DDS-Community
```

Expected: Returns valid JSON with instance/flavor data, not an error.

## 2. SDK Verification

Verify SDK imports and basic connectivity:

```bash
python3 -c "
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdds.v3 import DdsClient
print('SDK packages available ✓')
"
```

## 3. Mutating Operation Safety

Before executing any mutating operation:

1. Always confirm with the user
2. Use `--dry-run` or parameter validation first (when available)
3. Recommend creating a backup before destructive operations

## 4. End-to-End Test

Deployment analysis:

```bash
# Collect DDS deployment info (--mode prompts; answer `b` / use `echo b |` in CI)
hcloud DDS ListInstances --cli-region=cn-north-4 --datastore_type=DDS-Community
echo b | hcloud DDS ListInstances --cli-region=cn-north-4 --mode=ReplicaSet

# Collect DCS security info
hcloud DCS ListInstances --cli-region=cn-north-4
hcloud DCS ShowIpWhitelist --cli-region=cn-north-4 --instance_id={instance_id}
```