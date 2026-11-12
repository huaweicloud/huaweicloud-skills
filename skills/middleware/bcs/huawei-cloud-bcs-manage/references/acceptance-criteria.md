# Acceptance Criteria

## Read-Only Acceptance

| # | Criteria | Expected Result | Status |
|---|----------|----------------|--------|
| 1 | List instances | Prints count and per-instance id/name/status/version/service type/charging mode/cluster/created time | |
| 2 | Instance detail | Prints basic_info, channels, peer organizations, orderer and attached components | |
| 3 | Organization nodes | Prints org → node name / IP port / channels | |
| 4 | Channels | Prints channel name, consensus, create time, description, peer organizations | |
| 5 | Union members | Prints channel, invitor/invitee instance and tenant, invited organizations | |
| 6 | Invitation notifications | Prints channel, status, updated time, invitor, invitee organizations, read flag | |
| 7 | Specifications | Prints enterprise spec limits (peer/orderer/member max) | |
| 8 | Quotas | Prints quota/used/free/min/max per resource type | |
| 9 | Creation/deployment status | Prints component status (bcs/eip/sfs/obs/kafka/cce) | |
| 10 | Operation records | Prints operation id, instance name, type, status, time, description | |
| 11 | Alerts and statistics | `alerts` returns time-bounded alert data; `--statistics` returns aggregation | |
| 12 | Metrics | `metrics --scope=instance/entity/node` returns metric series; default instance metrics are the first five BCS metrics; the BCS metric API has no time-window field, so the server-side default window applies and `--time-range` is not transmitted | |
| 13 | Name resolution | `--name` resolves to a unique instance id; ambiguity is reported | |
| 14 | JSON output | Read `--json` emits exactly one structured payload on stdout | |
| 15 | Read-only isolation | Read subcommands never require `--confirm` and never call a create/update/delete SDK method | |

## Write Acceptance

| # | Criteria | Expected Result | Status |
|---|----------|----------------|--------|
| 16 | Certificate download | Writes a non-empty artifact to `--out`, mode `0600` | |
| 17 | SDK config download | Writes a non-empty artifact to `--out`, mode `0600` | |
| 18 | Create user certificate | Returns success and reports operation result | |
| 19 | Freeze/unfreeze certificate | Requires `--confirm`; reports result | |
| 20 | Create channels | Requires `--confirm`; follows operation_id | |
| 21 | Add peers | Requires `--confirm`; follows operation_id | |
| 22 | Remove peers | Requires `--confirm`; marked irreversible | |
| 23 | Remove organizations | Requires `--confirm`; marked irreversible | |
| 24 | Delete channel | Requires `--confirm`; marked irreversible | |
| 25 | Create instance | Requires `--confirm`; cost warning; prints blockchain_id/operation_id | |
| 26 | Update instance | Requires `--confirm`; follows operation_id; object-array `node_orgs` preview | |
| 27 | Delete instance | Requires `--confirm`; marked irreversible; deletion options honoured | |
| 28 | Invite members | Requires `--confirm`; body file mapped to SDK model | |
| 29 | Cancel invitation | Requires `--confirm` | |
| 30 | Handle notification | Requires `--confirm` | |
| 31 | Quit union | Requires `--confirm` | |
| 32 | Async reporting | Polls ListOpRecord until terminal status or `--timeout` | |
| 33 | JSON output | Write `--json` returns one block with `response` and `operation_record`; progress/preview on stderr | |

## Safety and Quality Acceptance

| # | Criteria | Expected Result | Status |
|---|----------|----------------|--------|
| 34 | Confirmation gate | Without `--confirm` no API mutation occurs and exit code is 2 | |
| 35 | Impact preview | Preview lists target ids, action and irreversibility | |
| 36 | Update-instance object contract | `{"node_orgs":[{"name":"org-2","node_count":2}],"is_delete_org":true}` produces a readable preview (`org-2(2 nodes)`, delete-org impact), rc=2, no traceback | |
| 37 | No auto-retry of destructive actions | Failed destructive operations are reported, not retried | |
| 38 | Sensitive artifacts | Certificates/SDK config written `0600`, warned as sensitive, never committed | |
| 39 | Empty download | 0-byte response → `ERROR[B01]`, empty file removed | |
| 40 | No hardcoded credentials | AK/SK read from environment only | |
| 41 | Supported regions | Unsupported region yields a clear `U02` error | |
| 42 | Missing credentials | Clear `C01` error, exit code 2 | |
| 43 | Error hygiene | SDK/body failures surface as `ERROR[...]` with exit 2 and no Python traceback | |
| 44 | Time-series bound | Alerts use `--time-range` plus `--max-points`; metric subcommands bound printed points via `--max-points` and use the BCS server-side default window | |
| 45 | Chaincode boundary documented | SKILL.md states chaincode has no OpenAPI and points to the console | |
| 46 | SDK install guidance | Prerequisites list `pip install huaweicloudsdkbcs` | |
| 47 | Quality reporting | Every run reports trace_id/status/cost silently | |