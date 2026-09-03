# IAM Policies for ModelArts Resource Pool Management

> Least-privilege IAM policies for the ModelArts resource pool management skill.

---

## Required Permissions

### Resource Pool Management

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:pool:list",
        "modelarts:pool:get",
        "modelarts:pool:create",
        "modelarts:pool:update",
        "modelarts:pool:delete"
      ],
      "Resource": "*"
    }
  ]
}
```

### BSS Pricing (for cost inquiry before chargeable operations)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:order:detail",
        "bss:order:list",
        "bss:measure:query"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Combined Policy (All Operations)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:pool:*",
        "bss:order:detail",
        "bss:order:list",
        "bss:measure:query"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Read-Only Policy

For query-only access (no write operations):

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:pool:list",
        "modelarts:pool:get"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Scoped Policy (Single Region)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:pool:list",
        "modelarts:pool:get",
        "modelarts:pool:create",
        "modelarts:pool:update",
        "modelarts:pool:delete"
      ],
      "Resource": [
        "arn:huawei:modelarts:cn-north-4:*:pool/*"
      ]
    }
  ]
}
```

---

## Permission to Operation Mapping

### modelarts:pool:list
- ListPools, ListPoolNodes, ListNodePools, ListNodePoolNodes
- ListNetworks, ListPoolTags, ListPluginTemplates, ListPoolPlugins
- ListWorkloads, ListJobs, ListScheduledEvents
- ListResourceFlavors, ListEvents

### modelarts:pool:get
- ShowPool, ShowPoolNode, ShowNodePool, ShowNetwork, ShowPoolTags
- ShowPluginTemplate, ShowPoolMonitor, ShowPoolStatistics, ShowPoolRuntimeMetrics
- ShowPoolNodeConfig, ShowNetworkAvailableIp, ShowWorkloadStatistics
- ShowOsConfig, ShowOsQuota, ShowNodeConfigTemplate, ShowPoolNodeConfigTemplate, ShowOrder

### modelarts:pool:create
- CreatePool, CreateNodePool, CreateNetwork, CreateOrderId
- BatchCreatePoolTags, CreatePoolPlugin

### modelarts:pool:update
- PatchPool, PatchNodePool, PatchNetwork
- BatchUpdatePoolNodes, BatchLockPoolNodes, BatchUnlockPoolNodes
- BatchRebootPoolNodes, BatchResetPoolNodes, BatchResizePoolNodes
- BatchMigratePoolNodes, BatchBindPoolNodes, AcceptScheduledEvent

### modelarts:pool:delete
- DeletePool, DeleteNodePool, DeleteNetwork
- BatchDeletePoolNodes, BatchDeletePoolTags

---

## Additional Dependencies

Resource pool creation with package-period billing may require BSS permissions for order processing:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:order:detail",
        "bss:order:list",
        "bss:measure:query"
      ],
      "Resource": "*"
    }
  ]
}
```
