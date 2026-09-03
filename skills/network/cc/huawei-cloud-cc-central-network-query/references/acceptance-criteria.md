# Acceptance Criteria

## Must Pass

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-01 | `ListCentralNetworks` returns valid JSON with `central_networks` array | Execute with valid domain_id |
| AC-02 | `ShowCentralNetwork` returns detail with `id`, `name`, `state`, `planes`, `connections` fields | Execute with valid central_network_id |
| AC-03 | `ListCentralNetworkAttachments` returns `attachments` array with `attachment_instance_type` per entry | Execute with valid central_network_id |
| AC-04 | `ShowCentralNetworkErRouteTableAttachment` returns ER route table attachment detail | Execute with valid attachment_id of type ER_ROUTE_TABLE |
| AC-05 | `ShowCentralNetworkGdgwAttachment` returns GDGW attachment detail | Execute with valid attachment_id of type GDGW |
| AC-06 | `ListCentralNetworkConnections` returns `connections` array | Execute with valid central_network_id |
| AC-07 | `ListCentralNetworkConnections --id.1={id}` returns single connection | Execute with valid connection_id |
| AC-08 | All commands include `--cli-region` parameter | Review command syntax |
| AC-09 | No write operations in the skill | Grep for Create/Update/Delete — should be absent |
| AC-10 | IAM policy uses least privilege (only list + get) | Review iam-policies.md |

## Should Pass

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-11 | Pagination works with `--limit` and `--marker` | Test with limit=1 and follow marker |
| AC-12 | Filters work (name, state, type) | Test with various filter parameters |
| AC-13 | Error messages are informative for invalid IDs | Test with non-existent IDs |
