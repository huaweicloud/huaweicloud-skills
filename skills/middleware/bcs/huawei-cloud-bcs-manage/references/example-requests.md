# Example Requests

- "List all BCS instances in cn-north-4 and show their status and version." →
  `python3 scripts/bcs_manage.py list --region=cn-north-4`
- "Which channels does my chain `supply-chain` have?" →
  `python3 scripts/bcs_manage.py channels --region=cn-north-4 --name=supply-chain`
- "Show peer nodes grouped by organization." →
  `python3 scripts/bcs_manage.py nodes --region=cn-north-4 --blockchain-id=<id>`
- "Why did my instance creation fail? Show the latest operation records." →
  `python3 scripts/bcs_manage.py op-record --region=cn-north-4 --blockchain-id=<id>`
- "Any active alerts on this instance in the last hour?" →
  `python3 scripts/bcs_manage.py alerts --region=cn-north-4 --blockchain-id=<id> --type=active_alert --time-range=-1.-1.60`
- "Create a channel `channel-2` on this instance." →
  `python3 scripts/bcs_manage.py create-channels --region=cn-north-4 --blockchain-id=<id> --body-file=channels.json --confirm`
## Sample `list` output

```text
Total BCS instances: 1
ID        NAME    STATUS  VERSION  SERVICE_TYPE  CHARGING_MODE  CLUSTER_NAME  CREATED_TIME
--------  ------  ------  -------  ------------  -------------  ------------  ------------
b1...     chain1  normal  2.2      base          periodic       cce-cluster   2026-01-01
```
