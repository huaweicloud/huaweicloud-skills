# Verification Method

This skill's operations are verified by executing the real `hcloud ECS` commands against the
authenticated project and by reading back the instance state.

## Per-Operation Verification

| Operation | Verification |
| ----------- | -------------- |
| List instances | Run `ListServersDetails` — expect a JSON array of servers, or an empty list with no error |
| Show detail | Run `ShowServer --server_id={id}` — expect `server` object with `id`, `status`, `name` |
| Create | Run `CreateServers` (after user confirmation) — expect HTTP 200 + job/server_id; then `ShowServer` / `ListServersDetails` until `status=ACTIVE` (or `BUILD` then `ACTIVE`) |
| Start | Run `BatchStartServers` — expect job; verify `status=ACTIVE` via `ShowServer` |
| Stop | Run `BatchStopServers` — verify `status=SHUTOFF` via `ShowServer` |
| Reboot | Run `BatchRebootServers` — expect job; verify `status=ACTIVE` after reboot |
| Rename | Run `BatchUpdateServersName --dry_run=true` first, then with confirmation; verify `name` via `ShowServer` |
| Reinstall OS | Run `ReinstallServerWithCloudInit` / `ReinstallServerWithoutCloudInit` (after user confirmation, server stopped or `--os-reinstall.mode=withStopServer`) — expect success; verify `status` settles on `ACTIVE` and the credential (`key_name`) via `ShowServer` |
| Change OS | Run `ChangeServerOsWithCloudInit` / `ChangeServerOsWithoutCloudInit` (after user confirmation, with `--os-change.imageid`) — expect success; verify `image.id` equals the requested image and `status=ACTIVE` via `ShowServer` |
| Resize | Confirm the target is allowed with `ListResizeFlavors --instance_uuid={id}`, then run `ResizeServer` / `ResizePostPaidServer` / `BatchResizeServers` (after user confirmation) — expect success; verify `flavor.id` equals the requested `--resize.flavorRef` and `status=ACTIVE` via `ShowServer` |
| Delete | Run `DeleteServers` (after user confirmation) — expect job; verify instance gone from `ListServersDetails` |

> Change operations (reinstall OS / change OS / resize) are asynchronous: `ShowServer` may report a
> transitional state such as `RESIZE` or `BUILD` before settling. Re-read until stable. See
> `references/lifecycle-change-operations.md` for the verified operation and parameter names.

## Fallback Test (SDK)

If `hcloud` fails, the same operation can be executed with the `huaweicloudsdkecs` SDK:

```bash
python3 -c "
from huaweicloudsdkecs.v2 import *
from huaweicloudsdkcore.auth.credentials import BasicCredentials
import os
creds = BasicCredentials(os.environ['HUAWEICLOUD_SDK_AK'], os.environ['HUAWEICLOUD_SDK_SK'])
client = EcsClient.new_builder().with_credentials(creds).with_region(EcsRegion.value_of('cn-north-4')).build()
resp = client.list_servers_details(ListServersDetailsRequest(limit=5))
print(resp)
"
```

## Clean verification state

- Query operations are side-effect free — safe to run during acceptance.
- Mutating operations must be confirmed by the user first, executed, then verified by reading the
  instance state back, and cleaned up (delete created instances) at the end of the test cycle.