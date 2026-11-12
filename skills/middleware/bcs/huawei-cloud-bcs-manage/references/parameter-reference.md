# Parameter Reference

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--region` | No (default `cn-north-4`) | BCS region: `cn-north-1`, `cn-north-4`, `cn-south-1`, `cn-east-2` | `--region=cn-north-4` |
| `--json` | No | Read: one structured JSON payload on stdout. Write: one `{"response", "operation_record"}` block on stdout, progress on stderr | `--json` |
| `--confirm` | Yes for every write | Execute the mutation; without it only the preview is printed | `--confirm` |
| `--blockchain-id` | Yes for instance-scoped commands | BCS instance id | `--blockchain-id=2e8a...` |
| `--name` | Read-only alternative to `--blockchain-id` | Instance name, resolved to its id | `--name=my-chain` |
| `--no-detail` | No | `list` only: skip per-instance detail enrichment (faster) | `--no-detail` |
| `--workers` | No (default 4) | `list` only: concurrent detail lookups, capped at 10 | `--workers=4` |
| `--type` | No | Alert type (`active_alert` / `history_alert`) or metric entity type (`org` / `plugin`) | `--type=active_alert` |
| `--time-range` | No (default `-1.-1.60` for alerts) | `alerts`/`events`/`events-statistic` query window. For metric subcommands it is accepted but NOT sent (server default window applies, a WARNING is printed) | `--time-range=-1.-1.60` |
| `--statistics` | No | `alerts` only: return aggregated alert statistics | `--statistics` |
| `--step` | No | Alert statistics step in milliseconds | `--step=60000` |
| `--search` | No | Fuzzy keyword match for alerts | `--search=peer` |
| `--order-by` / `--order` | No | Alert sort fields / direction | `--order-by=occur_time --order=desc` |
| `--scope` | No (default `instance`) | `metrics`: `instance` (whole instance), `entity` (org/plugin), `node` (single peer/orderer) | `--scope=node` |
| `--metric-names` | No | Comma-separated metric names for instance scope; default first five BCS metrics | `--metric-names=cpuUsage` |
| `--entity-name` | Yes for node scope; optional for entity scope | Organization/plugin entity name | `--entity-name=org1` |
| `--instance-name` | No | Node (pod) name for node scope | `--instance-name=peer-0` |
| `--max-points` | No (default 10) | Print only the latest N data points per metric | `--max-points=20` |
| `--org-name` | Yes for certificate operations | `order` or `peer` organization name | `--org-name=org-1` |
| `--user-name` | Yes for certificate operations | 4-24 lowercase letters/digits, starts with a letter | `--user-name=user01` |
| `--cert-type` | Yes for `download-cert` | Certificate category required by the BCS API | `--cert-type={cert_type}` |
| `--security-mode` | No (default `true`) | `true`=system-managed cert, `false`=user-managed | `--security-mode=true` |
| `--channel-id` | Yes for channel removal/deletion | Channel **name** as returned by instance detail | `--channel-id=channel-1` |
| `--peers` | Yes for `remove-peers` | Number of peers to remove | `--peers=1` |
| `--org-names` | Yes for `remove-orgs` | Comma-separated organization names | `--org-names=org-1,org-2` |
| `--delete-storage` | No | Delete instance: also delete EVS storage | `--delete-storage` |
| `--delete-obs` | No | Delete instance: also delete OBS buckets | `--delete-obs` |
| `--delete-resource` | No | Delete instance: also delete underlying CCE resources | `--delete-resource` |
| `--delete-ief` | No | Delete instance: also delete IEF edge resources | `--delete-ief` |
| `--body-file` | Yes for body-based operations | JSON body file (local path) | `--body-file=channels.json` |
| `--out` | No | Output file for downloaded artifacts | `--out=./cert.zip` |
| `--timeout` | No (default 60) | Seconds to poll ListOpRecord for completion | `--timeout=180` |
| `--no-wait` | No | Do not poll ListOpRecord | `--no-wait` |

`scripts/bcs_manage.py` uses `--region`; KooCLI uses `--cli-region`. See
[Prerequisites](../SKILL.md#prerequisites) for the SDK/KooCLI distinction.