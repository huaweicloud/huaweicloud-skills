# Verification Method

## Pre-Deployment Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| CLI installed | `hcloud --version` | Version 7.0.0+ |
| Credentials configured | `hcloud configure list` | Valid AKSK profile |
| LTS available | `hcloud LTS ListLogGroups --cli-region={region} --project_id={pid}` | JSON response (list or empty) |
| Log groups list | `hcloud LTS ListLogGroups --cli-region={region} --project_id={pid}` | JSON with log_groups array |
| Log streams list | `hcloud LTS ListLogStreams --cli-region={region} --project_id={pid} --log_group_name={name}` | JSON with log_streams array |
| Transfers list | `hcloud LTS ListTransfers --cli-region={region} --project_id={pid}` | JSON with transfers array |
| Keyword alarms | `hcloud LTS ListKeywordsAlarmRules --cli-region={region} --project_id={pid}` | JSON with alarm rules |
| SQL alarms | `hcloud LTS ListSqlAlarmRules --cli-region={region} --project_id={pid}` | JSON with alarm rules |
| Log search | `hcloud LTS ListLogs --cli-region={region} --project_id={pid} --log_group_id={gid} --log_stream_id={sid} --start_time={st} --end_time={et} --keywords="" --limit=1` | JSON with log entries |

## Post-Operation Verification

After Create/Update/Delete operations, verify the change by re-querying the resource:

```bash
# After CreateLogGroup → ListLogGroups to confirm new group appears
# After UpdateLogGroup TTL → ListLogGroups to confirm TTL changed
# After DeleteLogStream → ListLogStreams to confirm stream is gone
```

## Test Script

```bash
bash scripts/test-cli-commands.sh
```
