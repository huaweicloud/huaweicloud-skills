# API Specification

## Huawei Cloud Service Endpoints

### Flexus L Service
- **Endpoint**: `https://hcss.{region}.myhuaweicloud.com/v1/light-instances` (e.g. `https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances`)
- **Method**: POST
- **Purpose**: Create Flexus L instance
- **Note**: The endpoint is region-specific; the `{region}` placeholder must be replaced with the target region.

### IAM Service
- **CLI**: `hcloud IAM KeystoneListProjects --cli-region=<region> [--name=<region>]`
- **Purpose**: Get Project ID / domain ID
- **Note**: IAM is a global service. In AK/SK mode, KooCLI auto-resolves the account (domain) ID with valid credentials, so no `--cli-domain-id` is needed for this command.

### RMS Service
- **CLI**: `hcloud RMS ListAllResources --cli-region=cn-north-4 --cli-domain-id=<domain_id> [--region_id=<region>] [--type=hcss.l-instance] [--limit=200]`
- **Purpose**: Query resource information
- **Note**: RMS is a global service with a unified endpoint. Always call it with the unified `cn-north-4` region and pass `--cli-domain-id`; to query resources of a specific region (e.g. cn-east-3/cn-south-1/cn-southwest-2), pass the target region via the `--region_id` parameter.

### COC Service
- **Endpoint**: `https://coc.myhuaweicloud.com/v1/job/scripts/{script_uuid}` (ExecuteScript)
- **Method**: POST
- **Purpose**: Remote script execution
- **Note**: COC is a global service with a unified endpoint. The SDK client must always be built with the `cn-north-4` region. Each target instance's region is carried in the request body via `ExecuteResourceInstance.region_id` (COC supports all regions listed in its official "约束与限制" doc, including cn-north-4/cn-east-3/cn-south-1/cn-southwest-2).

## Flexus L Instance Specifications

| Name | Resource ID | CPU | Memory |
|------|-------------|-----|--------|
| small | hf.small.1.linux | 1 Core | 2GB |
| medium | hf.medium.1.linux | 2 Core | 4GB |
| large | hf.large.1.linux | 4 Core | 8GB |
| xlarge | hf.xlarge.1.linux | 8 Core | 16GB |
| 2xlarge | hf.2xlarge.1.linux | 16 Core | 32GB |

## COC Script Execution Status

| Status | Description |
|--------|-------------|
| PROCESSING | Running |
| FINISHED | Completed |
| ABNORMAL | Abnormal |

## Security Group Rules

The following ports need to be opened:
- **5173**: JiuwenSwarm Web service port
- **22**: SSH remote access port

## API Authentication

Two mechanisms are used:

1. **KooCLI (hcloud)** — used for IAM (project/domain ID queries) and RMS (resource queries). Set environment variables `HUAWEICLOUD_SDK_AK` and `HUAWEICLOUD_SDK_SK` (plus `HUAWEICLOUD_SDK_SECURITY_TOKEN` for STS temporary credentials); KooCLI reads them and handles request signing automatically. Credentials never appear on the command line.
2. **Huawei Cloud Python SDK** — used for COC script execution and status queries. The SDK reads the same environment variables and handles request signing automatically.
