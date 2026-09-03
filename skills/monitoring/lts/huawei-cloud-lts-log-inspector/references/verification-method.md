# Verification Method

## Pre-Execution Verification

Before running any LTS command, verify:

1. **Credential check**: `hcloud configure list` shows a valid profile
2. **Region check**: LTS is available in the target region
3. **Permission check**: The caller has LTS read/transfer permissions

## Command Verification

### Query Commands (Read-Only)

Query commands are safe to execute without confirmation. Verify results by
checking the response structure:

```bash
# Verify ListLogGroups returns valid structure
hcloud LTS ListLogGroups --cli-region={region} | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Log groups: {len(d.get(\"log_groups\",[]))}')"
```

### Mutating Commands (Create/Delete)

Mutating commands require user confirmation before execution:

1. **CreateTransfer**: Display cost risk warning, wait for user confirmation
2. **DeleteTransfer**: Display transfer details, wait for user confirmation

## Output Verification

### Traffic Statistics Output

Verify TOP-N results contain expected fields:
- `resource_type` matches the requested type
- `topn` results are sorted by the requested field
- `statistics` array contains traffic data points

### Collection Status Output

Verify host status results:
- Each host has a `host_status` field
- Offline/error hosts are flagged in the anomaly checklist
- Access configs are cross-referenced with affected hosts

### Context Log Output

Verify context query results:
- `backwards_size` and `forwards_size` are within [0, 500]
- Log fragments are concise (not full log text)
- `line_num` from the target log is correctly used

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `Log group not found` | Invalid `group_id` | Query `ListLogGroups` to find valid IDs |
| `Log stream not found` | Invalid `stream_id` | Query `ListLogStream` with the group ID |
| `Time range exceeds 30 days` | `start_time`/`end_time` span > 30 days | Narrow the time window |
| `OBS bucket not found` | Invalid `obs_bucket_name` | Verify bucket exists in OBS |
| `Transfer already exists` | Duplicate transfer config | Use `ListTransfers` to check existing configs |
| `Transfer not found` | Invalid `log_transfer_id` | Use `ListTransfers` to find valid transfer IDs |
| `log_transfer_id wrong length` | ID format invalid | Transfer IDs are 36-character UUID format |
