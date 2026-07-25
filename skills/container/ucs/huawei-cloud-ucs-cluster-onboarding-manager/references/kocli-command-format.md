# KooCLI Command Format Standard

All operations use Huawei Cloud KooCLI (hcloud). Command format follows these standards:

## Basic Format

```bash
hcloud <Service> <Operation> --<param>=<value> --cli-region=<region>
```

- **Service**: UCS (Ubiquitous Cloud Native Service)
- **Operation**: API operation name, e.g., `ShowCluster`, `RegisterCluster`, `DeleteCluster`
- **Parameters**: Use `--<param>=<value>` format (KooCLI style), not `--<param> <value>`
- **Region**: Must specify `--cli-region` (e.g., `cn-north-4`)

## Common Command Examples

```bash
# Query operations (read-only)
hcloud UCS ShowClusterList --cli-region=cn-north-4
hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4

# Registration operations (write, requires confirmation)
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=<name> --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

# Deletion operations (write, requires confirmation)
hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

## Parameter Naming Rules

| Parameter Type | Naming Style | Example |
|----------------|-------------|---------|
| Cluster ID | `--clusterid` | `--clusterid=ucs-xxxx-xxxx` |
| Fleet Group ID | `--clustergroupid` | `--clustergroupid=xxxx` |
| Region | `--cli-region` | `--cli-region=cn-north-4` |
| K8s API Style | `--apiVersion` / `--kind` / `--metadata.*` / `--spec.*` | `--spec.category=self` |

> ⚠️ Note: Parameter names use camelCase (e.g., `--clusterid`), not snake_case (e.g., `--cluster_id`).
