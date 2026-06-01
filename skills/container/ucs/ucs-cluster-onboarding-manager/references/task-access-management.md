# Task: Access Management

## Overview

UCS access management covers obtaining cluster kubeconfig, accessing cluster information, and managing federation kubeconfig for multi-cluster operations. This task covers creating kubeconfig, viewing access information, and downloading federation configurations.

## Operations Catalog

| Operation                   | Method | Description              | Key Parameters                    |
| --------------------------- | ------ | ------------------------ | --------------------------------- |
| `ShowClusterAccessInfo`     | GET    | 获取集群接入信息         | `--clusterid`, `--region` (optional), `--vpcendpoint` (optional) |
| `CreateClusterKubeconfig`   | POST   | 创建集群kubeconfig       | `--clusterid`                     |
| `CreateClusterConf`         | POST   | 创建集群配置             | `--clusterid`                     |
| `DownloadFederationKubeconfig` | GET | 下载联邦kubeconfig    | `--clustergroupid` (REQUIRED), `--duration` (REQUIRED) |

## Workflows

### W1: View Cluster Access Information

```bash
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

With optional parameters for specific access details:

```bash
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --region=cn-north-4 --vpcendpoint=true --cli-region=cn-north-4
```

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ShowClusterList pattern]:

The exact response format for `ShowClusterAccessInfo` has not been verified. Based on the verified k8s-style pattern from `ShowClusterList`, access info may be returned as a structured object rather than a flat JSON object. The likely fields include:

- API server endpoint address (public and/or private)
- Access type (`Public`, `Private`, `Both`)
- Intranet endpoint (for CCE clusters)

**Key Fields** (expected, format to be verified):
- API server endpoint: Cluster API server public endpoint
- Access type: Network access type (`Public`, `Private`, `Both`)
- Intranet endpoint: Internal network endpoint (available for CCE clusters)

**Use Cases**:
- Verify cluster connectivity before deploying applications
- Determine which endpoint to use (public vs private) based on network setup
- Troubleshoot access issues by checking endpoint availability

### W2: Create Cluster Kubeconfig

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Response**: Returns a Kubernetes kubeconfig YAML content. Save this to a file for kubectl access:

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4 > cluster-kubeconfig.yaml

kubectl --kubeconfig=cluster-kubeconfig.yaml get nodes
```

**Kubeconfig Security**:
- ⚠️ **Never store kubeconfig in public repositories or CI logs**
- ⚠️ **Kubeconfig tokens have expiration periods** — regenerate when access fails
- ✅ **Store kubeconfig in secure, encrypted storage** (e.g., secrets management tools)
- ✅ **Restrict file permissions**: `chmod 600 cluster-kubeconfig.yaml`

### W3: Create Cluster Configuration

```bash
hcloud UCS CreateClusterConf --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Use Cases**:
- Alternative to `CreateClusterKubeconfig` for obtaining cluster access details
- Provides configuration information for integration with other tools

### W4: Download Federation Kubeconfig

⚠️ **Note**: `DownloadFederationKubeconfig` requires both `--clustergroupid` and `--duration` as mandatory parameters. The `--clustergroupid` specifies which fleet group's federation kubeconfig to download, and `--duration` specifies the validity period.

```bash
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required): Fleet group ID for the federation kubeconfig
- `--duration` (required): Kubeconfig validity duration in seconds
- `--cli-region` (required): Region ID

**Response**: Returns a federation kubeconfig YAML that provides unified kubectl access to all UCS-managed clusters in the fleet group.

**Federation Kubeconfig Features**:
- Contains context entries for each registered cluster in the fleet group
- Enables cross-cluster operations via kubectl
- Supports workload distribution across multiple clusters

**Usage**:

```bash
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4 > federation-kubeconfig.yaml

kubectl --kubeconfig=federation-kubeconfig.yaml config get-contexts

kubectl --kubeconfig=federation-kubeconfig.yaml config use-context <context-name>

kubectl --kubeconfig=federation-kubeconfig.yaml get nodes --all-contexts
```

**Federation Requirements**:
- At least one cluster must be registered and in `Available` status in the fleet group
- All clusters must have valid API server connectivity
- Kubeconfig tokens may expire — regenerate periodically

### W5: Validate Kubeconfig Access

After obtaining kubeconfig, verify access works:

```bash
kubectl --kubeconfig=cluster-kubeconfig.yaml cluster-info

kubectl --kubeconfig=federation-kubeconfig.yaml cluster-info

kubectl --kubeconfig=cluster-kubeconfig.yaml get nodes
```

Expected: Returns cluster information and node list without errors.

## Common Scenarios

### S1: Obtain Kubeconfig for New Cluster

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=my-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

kubectl --kubeconfig=<saved-kubeconfig> cluster-info
```

### S2: Refresh Expired Kubeconfig

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4
```

### S3: Multi-Cluster Operations with Federation Kubeconfig

```bash
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4 > federation.yaml

kubectl --kubeconfig=federation.yaml config get-contexts

kubectl --kubeconfig=federation.yaml --context=<cluster-context> get pods -A

for ctx in $(kubectl --kubeconfig=federation.yaml config get-contexts -o name); do
  echo "=== $ctx ==="
  kubectl --kubeconfig=federation.yaml --context=$ctx get nodes
done
```

### S4: Secure Kubeconfig Storage for CI/CD

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4 > ci-kubeconfig.yaml

chmod 600 ci-kubeconfig.yaml
```