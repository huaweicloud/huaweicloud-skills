# Troubleshooting

This document provides solutions for common issues encountered when using the CES alarm automation skill.

## Installation Issues

### Issue 1: hcloud Command Not Found

**Symptom**: Running `hcloud version` returns "command not found"

**Solution**:

```bash
# Install KooCLI
curl -o hcloud_install.sh https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh

# Or install via pip
pip install hcloud

```

### Issue 2: KooCLI Version Too Low

**Symptom**: `hcloud version` returns version < 7.2.2

**Solution**:

```bash
# Upgrade KooCLI
pip install --upgrade hcloud

# Verify version
hcloud version

```

## Configuration Issues

### Issue 3: AK/SK Not Configured

**Symptom**: Commands return "Error: AK/SK not configured"

**Solution**:

```bash
# Configure credentials
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK>
hcloud configure set --cli-region=cn-north-4

# Verify configuration
hcloud configure list

```

### Issue 4: 403 Forbidden

**Symptom**: API calls return 403 Forbidden error

**Solution**:

1. Check IAM permissions - ensure CES FullAccess is granted
2. Verify AK/SK credentials are correct
3. Check region parameter matches the resource location

```bash
# Verify IAM permissions
hcloud IAM ListPermissions

# Check resource region
hcloud ECS ListServersDetails --cli-region=cn-north-4

```

## Alarm Creation Issues

### Issue 5: Alarm Creation Fails

**Symptom**: CreateAlarm API returns error

**Possible Causes**:

1. Invalid metric name
2. Threshold out of range (0-100 for CPU/Memory)
3. Missing required parameters
4. Insufficient permissions

**Solution**:

```bash
# Verify metric name
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=cn-north-4

# Check threshold value (should be 0-100 for percentage metrics)
# Use dry-run to validate parameters
./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001 --dry-run

```

### Issue 6: Duplicate Alarm Name

**Symptom**: "Alarm with this name already exists"

**Solution**:

- Use unique alarm names
- Add suffix or timestamp to alarm names
- Check existing alarms: `./scripts/list_alarms.sh`

## Monitoring Data Issues

### Issue 7: No Monitoring Data Returned

**Symptom**: ShowMetricData returns empty data

**Possible Causes**:

1. ECS instance is stopped
2. Metric collection interval (data has 5-minute delay)
3. Incorrect instance ID
4. Metric not enabled for the instance

**Solution**:

```bash
# Check ECS instance status
hcloud ECS ListServersDetails --cli-region=cn-north-4

# Verify instance ID is correct
./scripts/list_ecs.sh --output ids

# Wait 5-10 minutes and retry
./scripts/batch_query_metrics.sh --ecs-ids ecs-001 --metric cpu_util

```

### Issue 8: Metric Data Delay

**Symptom**: Monitoring data is 5-10 minutes behind real-time

**Solution**: This is normal behavior. CES metric data has inherent delay. Wait for next collection cycle.

## Notification Issues

### Issue 9: SMN Subscription Fails

**Symptom**: Subscribe API returns error

**Possible Causes**:

1. Invalid topic URN
2. Topic does not exist
3. Insufficient SMN permissions

**Solution**:

```bash
# List available topics
hcloud SMN ListTopics --cli-region=cn-north-4

# Verify topic URN format
# Correct format: urn:smn:region:account-id:topic-name

# Check SMN permissions
hcloud IAM ListAttachedGroupPolicies --group-id=<group-id>

```

### Issue 10: Notifications Not Received

**Symptom**: Alarm triggers but no notification received

**Solution**:

1. Verify subscription status is "Confirmed"
2. Check email spam folder
3. Verify phone number format for SMS
4. Test notification manually:

```bash
hcloud SMN PublishMessage --topic-urn=<topic-urn> --message="Test notification"

```

## Script Execution Issues

### Issue 11: Script Permission Denied

**Symptom**: Running script returns "Permission denied"

**Solution**:

```bash
# Add execute permission
chmod +x scripts/*.sh

# Or run with bash explicitly
bash scripts/list_ecs.sh

```

### Issue 12: Script Output Format Error

**Symptom**: Script output is not in expected format

**Solution**:

- Check `--output` parameter (table/json/ids)
- Verify jq is installed for JSON processing
- Check script has correct hcloud parameter format (--param=value)

## Parameter Format Issues

### Issue 13: hcloud Parameter Format Error

**Symptom**: Commands fail with parameter parsing errors

**Solution**: hcloud requires `--param=value` format (equals sign), not space separation.

```bash
# ✅ Correct
hcloud CES ListAlarms --region=cn-north-4

# ❌ Incorrect
hcloud CES ListAlarms --region cn-north-4

```

## References

- [Common Commands](common-commands.md)
- [CLI Installation Guide](cli-installation-guide.md)
- [IAM Policies](iam-policies.md)
- [Official CES Documentation](https://support.huaweicloud.com/ces/index.html)
