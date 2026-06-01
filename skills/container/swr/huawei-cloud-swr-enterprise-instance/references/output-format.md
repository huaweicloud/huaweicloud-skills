# SWR Enterprise Instance — Output Format

## Instance List

Response format needs verification.

```json
{
  "instances": [
    {
      "id": "xxx-xxx-xxx",
      "name": "my-instance",
      "spec": "swr.ee.professional",
      "status": "Running",
      "charge_mode": "postPaid",
      "vpc_id": "xxx",
      "subnet_id": "xxx",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-05-01T00:00:00Z"
    }
  ]
}
```

## Instance Details

Response format needs verification.

```json
{
  "id": "xxx-xxx-xxx",
  "name": "my-instance",
  "spec": "swr.ee.professional",
  "status": "Running",
  "charge_mode": "postPaid",
  "description": "",
  "internal_endpoint": "xxx.cn-north-4.myhuaweicloud.com",
  "public_endpoint": "xxx.cn-north-4.myhuaweicloud.com"
}
```

## Namespace List

Response format needs verification.

```json
{
  "namespaces": [
    {
      "id": 1,
      "name": "group-dev",
      "metadata": {
        "public": "false",
        "auto_scan": "true",
        "prevent_vul": "true",
        "severity": "high"
      },
      "creation_time": "2026-01-01T00:00:00Z",
      "update_time": "2026-05-01T00:00:00Z",
      "repo_count": 5
    }
  ]
}
```

## Long-term Credential

Response format needs verification — returns credential info including authentication token.

## Internal Endpoint List

Response format needs verification.

```json
{
  "internal_endpoints": [
    {
      "id": "xxx",
      "vpc_id": "xxx",
      "subnet_id": "xxx",
      "endpoint": "xxx.cn-north-4.myhuaweicloud.com",
      "status": "Running"
    }
  ]
}
```

## Domain Name List

Response format needs verification.

```json
{
  "domain_names": [
    {
      "id": "xxx",
      "domain_name": "registry.example.com",
      "status": "Active",
      "certificate_id": "xxx"
    }
  ]
}
```