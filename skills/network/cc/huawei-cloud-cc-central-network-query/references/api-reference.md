# API Reference

All API paths are verified from the Huawei Cloud SDK v3 source (`huaweicloudsdkcc.v3`) `_http_info` method `resource_path` values.

## Central Network Instance

| Operation | Method | Path | CLI Command |
|-----------|--------|------|-------------|
| List | GET | `/v3/{domain_id}/gcn/central-networks` | `hcloud CC ListCentralNetworks` |
| Show | GET | `/v3/{domain_id}/gcn/central-networks/{central_network_id}` | `hcloud CC ShowCentralNetwork` |

## Central Network Attachments

| Operation | Method | Path | CLI Command |
|-----------|--------|------|-------------|
| List | GET | `/v3/{domain_id}/gcn/central-network/{central_network_id}/attachments` | `hcloud CC ListCentralNetworkAttachments` |
| Show (ER Route Table) | GET | `/v3/{domain_id}/gcn/central-network/{central_network_id}/er-route-table-attachments/{er_route_table_attachment_id}` | `hcloud CC ShowCentralNetworkErRouteTableAttachment` |
| Show (GDGW) | GET | `/v3/{domain_id}/gcn/central-network/{central_network_id}/gdgw-attachments/{gdgw_attachment_id}` | `hcloud CC ShowCentralNetworkGdgwAttachment` |

## Central Network Connections

| Operation | Method | Path | CLI Command |
|-----------|--------|------|-------------|
| List | GET | `/v3/{domain_id}/gcn/central-network/{central_network_id}/connections` | `hcloud CC ListCentralNetworkConnections` |
| Show (via filter) | GET | `/v3/{domain_id}/gcn/central-network/{central_network_id}/connections` with `?id={connection_id}` | `hcloud CC ListCentralNetworkConnections --id.1={connection_id}` |

> **Note:** No dedicated `ShowCentralNetworkConnection` API exists. The connection detail is obtained by filtering the list result by ID, or from the `connections` array embedded in the `ShowCentralNetwork` response.

## SDK Information

- **Package:** `huaweicloudsdkcc`
- **Module:** `huaweicloudsdkcc.v3`
- **SDK Methods:**
  - `list_central_networks`
  - `show_central_network`
  - `list_central_network_attachments`
  - `show_central_network_er_route_table_attachment`
  - `show_central_network_gdgw_attachment`
  - `list_central_network_connections`
