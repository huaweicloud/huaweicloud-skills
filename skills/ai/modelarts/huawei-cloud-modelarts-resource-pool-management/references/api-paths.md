# API Paths (from SDK Source)

> REST API paths for all 53 ModelArts resource pool operations, extracted from the Huawei Cloud SDK source code.

---

## 1. Resource Pool Management (11 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 1 | ListPools | GET | `/v2/{project_id}/pools` |
| 2 | ShowPool | GET | `/v2/{project_id}/pools/{pool_name}` |
| 3 | CreatePool | POST | `/v2/{project_id}/pools` |
| 4 | PatchPool | PATCH | `/v2/{project_id}/pools/{pool_name}` |
| 5 | DeletePool | DELETE | `/v2/{project_id}/pools/{pool_name}` |
| 6 | ShowPoolMonitor | GET | `/v2/{project_id}/pools/{pool_name}/monitor` |
| 7 | ShowPoolStatistics | GET | `/v2/{project_id}/pools/statistics` |
| 8 | ShowPoolRuntimeMetrics | GET | `/v2/{project_id}/pools/runtime-metrics` |
| 9 | ShowPoolNodeConfig | GET | `/v2/{project_id}/pools/{pool_name}/node-config` |
| 10 | CreateOrderId | POST | `/v2/{project_id}/pools/order-id` |
| 11 | ShowOrder | GET | `/v2/{project_id}/pools/orders/{order_name}` |

## 2. Pool Node Management (11 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 12 | ListPoolNodes | GET | `/v2/{project_id}/pools/{pool_name}/nodes` |
| 13 | ShowPoolNode | GET | `/v2/{project_id}/pools/{pool_name}/nodes/{node_name}` |
| 14 | BatchDeletePoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-delete` |
| 15 | BatchUpdatePoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-update` |
| 16 | BatchLockPoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-lock` |
| 17 | BatchUnlockPoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-unlock` |
| 18 | BatchRebootPoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-reboot` |
| 19 | BatchResetPoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-reset` |
| 20 | BatchResizePoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-resize` |
| 21 | BatchMigratePoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-migrate` |
| 22 | BatchBindPoolNodes | POST | `/v2/{project_id}/pools/{pool_name}/nodes/batch-bind` |

## 3. Node Pool Management (6 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 23 | ListNodePools | GET | `/v2/{project_id}/pools/{pool_name}/nodepools` |
| 24 | ShowNodePool | GET | `/v2/{project_id}/pools/{pool_name}/nodepools/{nodepool_name}` |
| 25 | CreateNodePool | POST | `/v2/{project_id}/pools/{pool_name}/nodepools` |
| 26 | PatchNodePool | PATCH | `/v2/{project_id}/pools/{pool_name}/nodepools/{nodepool_name}` |
| 27 | DeleteNodePool | DELETE | `/v2/{project_id}/pools/{pool_name}/nodepools/{nodepool_name}` |
| 28 | ListNodePoolNodes | GET | `/v2/{project_id}/pools/{pool_name}/nodepools/{nodepool_name}/nodes` |

## 4. Network Resources (6 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 29 | ListNetworks | GET | `/v2/{project_id}/networks` |
| 30 | ShowNetwork | GET | `/v2/{project_id}/networks/{network_name}` |
| 31 | CreateNetwork | POST | `/v2/{project_id}/networks` |
| 32 | PatchNetwork | PATCH | `/v2/{project_id}/networks/{network_name}` |
| 33 | DeleteNetwork | DELETE | `/v2/{project_id}/networks/{network_name}` |
| 34 | ShowNetworkAvailableIp | GET | `/v2/{project_id}/networks/{network_name}/available-ip` |

## 5. Tag Management (4 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 35 | ListPoolTags | GET | `/v2/{project_id}/pools/tags` |
| 36 | ShowPoolTags | GET | `/v2/{project_id}/pools/{pool_name}/tags` |
| 37 | BatchCreatePoolTags | POST | `/v2/{project_id}/pools/{pool_name}/tags/create` |
| 38 | BatchDeletePoolTags | POST | `/v2/{project_id}/pools/{pool_name}/tags/delete` |

## 6. Plugin Management (4 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 39 | ListPluginTemplates | GET | `/v2/{project_id}/plugintemplates` |
| 40 | ShowPluginTemplate | GET | `/v2/{project_id}/plugintemplates/{plugintemplate_name}` |
| 41 | ListPoolPlugins | GET | `/v2/{project_id}/pools/{pool_name}/plugins` |
| 42 | CreatePoolPlugin | POST | `/v2/{project_id}/pools/{pool_name}/plugins` |

## 7. Jobs & Workloads (3 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 43 | ListWorkloads | GET | `/v2/{project_id}/pools/{pool_name}/workloads` |
| 44 | ShowWorkloadStatistics | GET | `/v2/{project_id}/pools/{pool_name}/workloads/statistics` |
| 45 | ListJobs | GET | `/v2/{project_id}/jobs` |

## 8. Scheduled Events (2 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 46 | ListScheduledEvents | GET | `/v2/{project_id}/pools/{poolName}/scheduled-events` |
| 47 | AcceptScheduledEvent | POST | `/v2/{project_id}/pools/scheduled-events/{event_id}/accept` |

## 9. OS Configuration (2 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 48 | ShowOsConfig | GET | `/v2/{project_id}/os/configs` |
| 49 | ShowOsQuota | GET | `/v2/{project_id}/os/quotas` |

## 10. Resource Flavors & Events (4 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 50 | ListResourceFlavors | GET | `/v2/{project_id}/resource-flavors` |
| 51 | ListEvents | GET | `/v2/{project_id}/events` |
| 52 | ShowNodeConfigTemplate | GET | `/v2/{project_id}/node-config-templates/{nodeconfigtemplate_name}` |
| 53 | ShowPoolNodeConfigTemplate | GET | `/v2/{project_id}/pools/{pool_name}/node-config-templates` |
