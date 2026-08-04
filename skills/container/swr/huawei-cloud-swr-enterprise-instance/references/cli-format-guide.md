# KooCLI Command Format Guide

All CLI commands in this skill use the `hcloud` KooCLI format:

```bash
hcloud SWR <Operation> --param1=value1 --param2=value2 --cli-region=<region>
```

**Rules**:

- Use `--key=value` format for all parameters (dot notation supported for nested fields: `--metadata.public=true`)
- Always specify `--cli-region` explicitly
- Never expose AK/SK or security tokens in command output
- For write operations (Create/Update/Delete), confirm with the user before executing
- Use `--cli-output=json` for structured output parsing

### Known CLI Limitations: Same-Name Parameter Conflicts

Some SWR API operations define the same parameter name in both the request path and request body (e.g., `project_id`, `instance_id`). The hcloud CLI cannot distinguish between path and body parameters with the same name, causing errors when using `--key=value` CLI argument format.

**Affected Commands**:

| Command | Conflicting Parameter | Path Purpose | Body Purpose |
| ------- | -------------------- | ------------ | ------------ |
| `CreateInstance` | `project_id` | Auto-filled from credentials | VPC/subnet project ID |
| `CreateInstanceInternalEndpoint` | `project_id` | Auto-filled from credentials | VPC/subnet project ID |
| `CreateInstanceRegistry` | `instance_id` | Source instance ID | Target instance ID (for `swr-pro-internal` type) |

**Workaround**: Use `--cli-jsonInput` to pass parameters via a JSON file with `path` and `body` sections (required by hcloud to distinguish same-name parameters):

```bash
# Example: CreateInstance with --cli-jsonInput
cat > create_instance.json << 'EOF'
{
  "path": {
    "project_id": "<project-id>"
  },
  "body": {
    "name": "my-instance",
    "spec": "swr.ee.professional",
    "charge_mode": "postPaid",
    "vpc_id": "<vpc-id>",
    "subnet_id": "<subnet-id>",
    "enterprise_project_id": "0",
    "project_id": "<vpc-project-id>"
  }
}
EOF

hcloud SWR CreateInstance --cli-jsonInput=create_instance.json --cli-region=cn-north-4
```

```bash
# Example: CreateInstanceInternalEndpoint with --cli-jsonInput
cat > create_endpoint.json << 'EOF'
{
  "path": {
    "instance_id": "<instance-id>",
    "project_id": "<project-id>"
  },
  "body": {
    "vpc_id": "<vpc-id>",
    "subnet_id": "<subnet-id>",
    "project_id": "<vpc-project-id>"
  }
}
EOF

hcloud SWR CreateInstanceInternalEndpoint --cli-jsonInput=create_endpoint.json --cli-region=cn-north-4
```

```bash
# Example: CreateInstanceRegistry with --cli-jsonInput (for swr-pro-internal type)
cat > create_registry.json << 'EOF'
{
  "path": {
    "instance_id": "<source-instance-id>",
    "project_id": "<project-id>"
  },
  "body": {
    "name": "target-registry",
    "type": "swr-pro-internal",
    "url": "https://<target-instance>.cn-east-3.myhuaweicloud.com",
    "credential": {
      "type": "basic",
      "access_key": "<access-key>",
      "access_secret": "<access-secret>"
    },
    "insecure": false,
    "instance_id": "<target-instance-id>",
    "project_id": "<target-project-id>",
    "region_id": "cn-east-3"
  }
}
EOF

hcloud SWR CreateInstanceRegistry --cli-jsonInput=create_registry.json --cli-region=cn-north-4
```

