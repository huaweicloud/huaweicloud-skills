# Acceptance Criteria: Correct/Error Pattern Comparison

## CLI Command Patterns

### Service Name

**Correct:** Use uppercase `SWR`
```bash
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

**Error:** Use lowercase or mixed case
```bash
hcloud swr ListSyncRegions ...   # Wrong: service name must be uppercase
hcloud Swr ListSyncRegions ...   # Wrong: service name must be uppercase
```

### Operation Name

**Correct:** Use PascalCase
```bash
hcloud SWR CreateImageSyncRepo ...
hcloud SWR ListImageAutoSyncReposDetails ...
hcloud SWR CreateTrigger ...
```

**Error:** Use snake_case or lowercase
```bash
hcloud SWR create_image_sync_repo ...  # Wrong: must be PascalCase
hcloud SWR list_sync_regions ...       # Wrong: must be PascalCase
```

### Region Parameter

**Correct:** Include `--cli-region` in every command
```bash
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

**Error:** Omit region parameter
```bash
hcloud SWR ListSyncRegions  # Wrong: missing --cli-region
```

## Parameter Patterns

### Image Tag Array Parameters

**Correct:** Index starts from 1
```bash
hcloud SWR CreateManualImageSyncRepo --namespace=pancake --repository=my-app \
  --remoteRegionId=cn-east-3 --remoteNamespace=pancake \
  --imageTag.1=v1.0 --imageTag.2=v2.0 --override=false --cli-region=cn-north-4
```

**Error:** Index starts from 0 or missing index
```bash
--imageTag.0=v1.0  # Wrong: index starts from 1
--imageTag=v1.0    # Wrong: missing index
--imageTag=v1.0,v2.0  # Wrong: comma-separated not supported
```

### Sync Filter Parameter

**Correct:** Use `--filter` with both limit and offset
```bash
hcloud SWR ShowSyncJob --namespace=pancake --repository=my-app \
  --filter="limit::10|offset::0" --cli-region=cn-north-4
```

**Error:** Omit filter or use wrong format
```bash
hcloud SWR ShowSyncJob --namespace=pancake --repository=my-app  # Wrong: missing --filter
hcloud SWR ShowSyncJob --filter="10,0"  # Wrong: must use limit::N|offset::N format
```

### Trigger Condition Parameter

**Correct:** Use regex pattern for trigger condition
```bash
--trigger_type=all --condition=".*"     # Match all tags
--trigger_type=tag --condition="v.*"    # Match tags starting with v
```

**Error:** Use invalid regex or wrong type
```bash
--trigger_type=all --condition="*"      # Wrong: not valid regex, use .*
--trigger_type=invalid --condition=".*" # Wrong: type must be all or tag
```

## Security Standards

### Credential Handling

**Correct:** Use environment variables
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

**Error:** Hardcode credentials in commands or ask users for AK/SK
```bash
hcloud SWR ListSyncRegions --cli-region=cn-north-4 --ak=xxx --sk=xxx  # Wrong: never pass credentials as parameters
```

### Write Operation Confirmation

**Correct:** Prompt user confirmation before write operations
```
The following write operation will be executed:
  Command: hcloud SWR CreateImageSyncRepo --namespace=pancake --repository=openclaw-sandbox \
    --remoteRegionId=cn-east-3 --remoteNamespace=pancake --syncAuto=true --override=false
  Target: repository 'pancake/openclaw-sandbox' → 'cn-east-3/pancake'
  Change: Configure auto-sync (override=false)
Do you want to proceed? (yes/no)
```

**Error:** Execute write operations without confirmation
```bash
# Directly executing Create/Update/Delete without user confirmation is prohibited
hcloud SWR DeleteImageSyncRepo --namespace=pancake --repository=openclaw-sandbox \
  --remoteRegionId=cn-east-3 --remoteNamespace=pancake --cli-region=cn-north-4
```

## Output Format Standards

### JSON Output

**Correct:** Use `--cli-output=json` for programmatic processing
```bash
hcloud SWR ListImageAutoSyncReposDetails --namespace=pancake --repository=my-app \
  --cli-region=cn-north-4 --cli-output=json
```

**Error:** Parse human-readable table output
```bash
# Wrong: parsing table output is fragile and locale-dependent
hcloud SWR ListImageAutoSyncReposDetails --namespace=pancake --repository=my-app --cli-region=cn-north-4
```
