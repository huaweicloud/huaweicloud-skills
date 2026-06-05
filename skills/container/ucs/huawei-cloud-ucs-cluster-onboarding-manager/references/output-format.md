# UCS Cluster Onboarding Manager — Output Format

## ShowCluster (Verified)

```json
{
  "kind": "Cluster",
  "apiVersion": "v1",
  "metadata": {
    "name": "test1",
    "uid": "b1c1e9b6-65e6-11ee-8d84-0255ac1000d3",
    "creationTimestamp": "2023-10-08T14:26:39Z",
    "annotations": {
      "vpcId": ""
    }
  },
  "spec": {
    "syncMode": "Push",
    "manageType": "discrete",
    "apiEndpoint": "https://kubernetes.default.svc.cluster.local",
    "provider": "huaweicloud",
    "type": "baremetal",
    "category": "onpremise",
    "country": "CN",
    "city": "110000",
    "IsDownloadedCert": false
  },
  "status": {
    "phase": "Failed",
    "conditions": [
      {
        "type": "Ready",
        "status": "False",
        "reason": "Failed",
        "message": "currently no agents available"
      }
    ]
  }
}
```

**Key Fields**:
- `metadata.uid`: UCS-assigned cluster UUID (k8s format)
- `metadata.name`: Cluster display name
- `spec.category`: Cluster category (`onpremise`, `CCE`, etc.)
- `spec.provider`: Cluster provider (`huaweicloud`, `self_managed`, etc.)
- `spec.manageType`: `grouped` or `discrete`
- `status.phase`: Cluster phase (`Failed`, `Available`, etc.)
- `status.conditions[].type`: Condition types (`Ready`, `Cluster`)

## ShowClusterList (Verified)

```json
{
  "items": [
    {
      "kind": "Cluster",
      "apiVersion": "v1",
      "metadata": {
        "name": "test1",
        "uid": "b1c1e9b6-65e6-11ee-8d84-0255ac1000d3",
        "creationTimestamp": "2023-10-08T14:26:39Z"
      },
      "spec": {
        "category": "onpremise",
        "provider": "huaweicloud",
        "manageType": "discrete"
      },
      "status": {
        "phase": "Failed"
      }
    }
  ],
  "total": 1
}
```

**Key Fields**:
- `items[]`: Array of cluster objects (k8s-style)
- `total`: Total number of clusters
- Each item has `metadata.name`, `metadata.uid`, `spec.*`, `status.phase`

## ShowQuota (Verified)

```json
{
  "quotas": {
    "resources": [
      {
        "type": "cluster",
        "quota": 50,
        "used": 1,
        "unit": "",
        "min": 20,
        "max": 100
      },
      {
        "type": "clustergroup",
        "quota": 50,
        "used": 0,
        "unit": "",
        "min": 20,
        "max": 100
      },
      {
        "type": "rule",
        "quota": 50,
        "used": 0,
        "unit": "",
        "min": 20,
        "max": 100
      },
      {
        "type": "federation",
        "quota": 1,
        "used": 0,
        "unit": "",
        "min": 1,
        "max": 50
      }
    ]
  }
}
```

**Key Fields**:
- `type`: Resource type (`cluster`, `clustergroup`, `rule`, `federation`)
- `quota`: Current quota limit
- `used`: Current usage count
- `min`/`max`: Quota adjustment range