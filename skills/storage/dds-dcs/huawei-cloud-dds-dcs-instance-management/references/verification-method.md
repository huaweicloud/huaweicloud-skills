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

## 5. Quality Reporting (CLI) Verification

```bash
# 5.1 CLI install (idempotent) + PATH export
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
command -v skill-quality-cli   # or ~/.local/bin/skill-quality-cli

# 5.2 Wrapper mode — hcloud command run + automatic quality report
skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management \
  -- hcloud DDS ListInstances --cli-region=cn-north-4 --limit=1

# 5.3 Manual single-step report (fire-and-forget; output/exit unchanged)
skill-quality-cli report --skill-name huawei-cloud-dds-dcs-instance-management --status success

# 5.4 E2E real delivery through the bundled carrier (must print [quality-report] OK trace_id=...)
printf '{"session_id":"verify-dds-dcs","trigger_type":"workflow"}' > /tmp/qcfg.json
SKILL_QUALITY_REPORT_VERBOSE=1 python3 scripts/cli/cli_entry.py --no-auto-upgrade \
  report --skill-name huawei-cloud-dds-dcs-instance-management --status success --json /tmp/qcfg.json 2>&1 | tail -1
```

Expected: step 5.4 prints `[quality-report] OK trace_id=<id>` (HTTP 200 from the quality endpoint);
steps 5.2/5.3 complete with their normal output/exit codes unchanged (reporting never blocks or
alters hcloud results).